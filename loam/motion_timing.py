"""What a move costs the machine — the one place both worlds ask.

The score planner (`loam.score._Solver`) and the rig that renders the plan
(`formlab/rig.py`, which the harness plays back as a bake) each had their
own idea of how long an arm takes to reposition. The planner charged
`|index difference| * travel_s`, a per-actuator constant with no geometry in
it; the rig moved `teeth(dx)` teeth of the rack at a click each, or slewed.
Those two numbers were not close. A bars reposition of eight teeth was
planned at 25 ms and rendered in whatever the planner had left it — 59 ms,
one click spanning the whole 0.39 m. The planner was writing cheques the
machine could only cash by teleporting.

So the timing lives here, in plain Python with no dependencies, and both
sides import it. `formlab` loads this file by path rather than importing
`loam` (see the note in `formlab/rig.py`): the package's `__init__` pulls the
whole synth stack, and `rig`/`clearance`/`layout_search` are numpy-only so
that Blender can run them.

Two vocabularies, two speeds (`docs/motion-design.md`):

* **Stepped** (mallet, hammer). A move is `teeth(dx)` teeth of the rack.
  The hammer clicks: unhurried that is `CLICK_S` a tooth. Hurried, clicks come no faster than
  `CLICK_MIN_S` and each spans at most `CLICK_TEETH_MAX` teeth — that cap is
  the physical floor, and it is what the planner must respect. Without it
  "one click, sixteen teeth, 24 ms of motion" is a legal plan, which is 32
  m/s of carriage. A mallet travels contact to contact instead (below).
* **Servo** (pick, rake). A short move wants `SLEW_S` of lead whatever its
  length — an S-curve needs its ramps — and a long one is limited by the
  carriage's top speed `SERVO_V_MAX`, which is also its floor.

`WORLD_SCALE` is the other half of the fix: the score's positions are in its
own units and `tools/build_clockwork.py` multiplies them by three to place
the instrument in the room, so a planner reasoning about metres of rail has
to multiply too.

**Contact to contact** (mallet; the hinged hammer joins at M5,
docs/goals/the-players.md). The head rides its rebound off the bar, so the
carriage is free at the contact itself (`t_head_free`) and arrives at the next
contact's x by the time the head lands, x' = x'' = 0 at both ends
(`arrive_lead` = 0). The unit of a stepped travel is the 3 g step
(`step_period`): one 3-4-5 a tooth over `STEP_MOVE` of the period, a dwell on
the detent for the rest. What a travel wants unhurried is a step a tooth and
then the cocked hold and the downstroke over a still carriage
(`contact_travel_s` + `still_s`). The rig decides the regime from the window
the stroke leaves it (`travel_regime`, the ONE rule the planner's want and
`formlab.rig` share): stepped where the window holds every step, else one
3-4-5 freewheel over the whole window; a counted *hurried* travel when even
that passes 3 g or 1.0 head extent a frame (`hurried`). Below
`contact_floor_s`, the 3-4-5 law at the hurried ceilings (5 g, `HURRIED_RHO`
head extents a frame), the contact is refused.
"""

import math

# The rack's pitch is the pinion's: 16 teeth on a 0.12 m pitch radius.
PITCH = 2 * math.pi * .12 / 16      # 47 mm a tooth
CLICK_S = .09                       # a click, unhurried
CLICK_MIN_S = .04                   # ...and the fastest one can come
CLICK_TEETH_MAX = 4                 # ...spanning at most this many teeth
SLEW_S = .4                         # a servo slew's lead for a short move
SERVO_V_MAX = 3.0                    # m/s: the fastest a servo carriage runs
WORLD_SCALE = 3.0                   # score position units -> rig metres

# Wind-up before the contact, per arm kind. A mallet throws its downstroke
# over this much at least (and its carriage keeps travelling under it); a hinged
# hammer flips its head instead of its arm and wants the least (formlab/rig.py,
# HAMMER).
APPROACH_S = dict(pick=.12, rake=.12, mallet=.14, hammer=.08)
STEPPED_KINDS = ('mallet', 'hammer')

# Contact to contact (M1). The smooth law is 3-4-5: peak |x''| = A345 d/T^2,
# peak |x'| = V345 d/T. A ratchet carriage runs at <= 3 g and <= 1.0 head extent
# E a frame unhurried, <= 5 g and <= HURRIED_RHO E a frame when hurried (rules
# 3 and 4; rulers 1 and 19). E is the head's extent along the rail: the wound
# head is a ball of r 0.06 (formlab/linkage.py mallet_tool), and the M5 hinge
# pins along the rail, so its arc never widens it.
CONTACT_KINDS = ('mallet',)
G = 9.80665
FPS = 30
A345 = 10/math.sqrt(3)              # 5.7735
V345 = 15/8                         # 1.875
HEAD_E = dict(mallet=.12, hammer=2*.045*1.02)
FREE_G, FREE_RHO = 3.0, 1.0         # unhurried freewheel ceilings
HURRIED_G, HURRIED_RHO = 5.0, 1.5   # a counted hurried travel's ceilings
# A stepped tooth: a 3-4-5 over STEP_MOVE of its period at <= FREE_G, then a
# dwell on the detent (formlab/stroke.py imports STEP_MOVE). The rig stretches
# the period to fill a longer window, up to P_MAX a tooth, and never below
# step_period.
STEP_MOVE = 0.6
P_MAX = 0.2
# An unhurried contact-to-contact travel leaves the carriage still for at
# least this long before the contact: the stroke's cocked hold (formlab/stroke.py
# HOLD, 0.12) and its longest downstroke from rest (T_down 0.15 lengthened
# toward 0.25 as the prep grows). The carriage must have arrived before the
# hold starts (ruler 21), so a want with less than this could never step.
STILL_S = 0.37


def stepped(kind):
    """Does this arm kind click along a rack, or slew?"""
    return kind in STEPPED_KINDS


def approach_s(kind):
    """The wind-up an arm of this kind takes before the contact."""
    return APPROACH_S.get(kind, .12)


def teeth(dx):
    """Teeth of the rack a move of `dx` metres crosses (at least one)."""
    return max(1, int(math.floor(abs(dx) / PITCH + .5)))


def clicks(dx, T):
    """How many clicks a stepped travel of `dx` gets in `T` seconds: one a
    tooth when there is room, else as many as `CLICK_MIN_S` allows. Mirrors
    `formlab.rig.clicks`; `ratchet` divides the window this way."""
    return min(teeth(dx), max(1, int(math.floor(T / CLICK_MIN_S))))


def stepped_travel_s(dx):
    """The unhurried stepped travel: a click a tooth at `CLICK_S`."""
    return teeth(dx) * CLICK_S if abs(dx) > 0 else 0.0


def stepped_floor_s(dx):
    """The fastest a stepped travel can physically be: clicks at
    `CLICK_MIN_S`, each spanning no more than `CLICK_TEETH_MAX` teeth."""
    if abs(dx) <= 0:
        return 0.0
    return math.ceil(teeth(dx) / CLICK_TEETH_MAX) * CLICK_MIN_S


def servo_travel_s(dx):
    """The unhurried servo travel: `SLEW_S` of lead, or longer if the
    distance needs it at the carriage's top speed."""
    return max(SLEW_S, abs(dx) / SERVO_V_MAX) if abs(dx) > 0 else 0.0


def servo_floor_s(dx):
    """A servo has no ratchet to coarsen: its floor is its top speed."""
    return abs(dx) / SERVO_V_MAX


def contact_to_contact(kind):
    """Does this arm's carriage travel contact to contact under a head that
    rides its rebound (free at the contact, arriving at the next one)?"""
    return kind in CONTACT_KINDS


def arrive_lead(kind, approach_s):
    """How long before the contact the carriage stands at the contact's x:
    the whole wind-up for an arm that strikes from a still carriage, nothing
    for one that travels contact to contact. The planner's occupancy and the
    rig's (`formlab.rig.Rig._segments`) both switch from the crossed interval
    to the played one here."""
    return 0.0 if contact_to_contact(kind) else approach_s


def still_s(kind, approach_s):
    """How long an unhurried travel leaves the carriage still before the
    contact: the wind-up for every arm; for a contact-to-contact one at least
    STILL_S (the stroke's cocked hold and its longest downstroke), so a want
    that is met leaves a window travel_regime calls 'step'."""
    return max(approach_s, STILL_S) if contact_to_contact(kind) else approach_s


def smooth_s(kind, dx, g, rho):
    """The least time of a 3-4-5 travel over `dx` metres at a peak of `g` and
    `rho` head extents a frame."""
    d = abs(dx)
    if d <= 0:
        return 0.0
    return max(math.sqrt(A345 * d / (g * G)), V345 * d / (FPS * rho * HEAD_E[kind]))


def step_period(dx):
    """The shortest stepped tooth period of a travel over `dx` metres: a
    3-4-5 over one tooth (|dx| / teeth) at FREE_G, which is STEP_MOVE of the
    period (about 0.160 s on the bars and the bells)."""
    d = abs(dx) / teeth(dx)
    return math.sqrt(A345 * d / (FREE_G * G)) / STEP_MOVE


def contact_travel_s(dx):
    """The unhurried contact-to-contact travel: tooth by tooth on the detent,
    `step_period` a tooth (the planner adds the stroke over a still
    carriage, `still_s`)."""
    return teeth(dx) * step_period(dx) if abs(dx) > 0 else 0.0


def travel_regime(dx, window):
    """How a contact-to-contact carriage crosses `dx` metres in a free
    `window` (seconds the stroke leaves it: contact to contact in a tempo
    gap, the carriage's earliest start `go` to the cocked hold's start when
    there is one): 'step' when the window holds a step_period a tooth, else
    'freewheel' (one 3-4-5 over the whole window), or 'still' for no travel.
    The planner's want and formlab.rig both decide by this."""
    if abs(dx) <= 0:
        return 'still'
    return 'step' if window >= contact_travel_s(dx) - 1e-9 else 'freewheel'


def stepped_period(dx, window):
    """A stepped travel's tooth period in `window`: the room a tooth, at most
    P_MAX, never below step_period (call it only where travel_regime says
    'step')."""
    return max(step_period(dx), min(window / teeth(dx), P_MAX))


def contact_floor_s(kind, dx):
    """The least window a contact-to-contact travel can be given: the 3-4-5
    law at the hurried ceilings."""
    return smooth_s(kind, dx, HURRIED_G, HURRIED_RHO)


def hurried(kind, dx, window):
    """The notation's hurried travel (docs/goals/the-players.md): its least
    smooth time at 3 g and 1.0 E a frame exceeds its contact-to-contact
    window. Only contact-to-contact kinds are judged."""
    return contact_to_contact(kind) and smooth_s(kind, dx, FREE_G, FREE_RHO) > window + 1e-9


# Homing (ruler 22): a contact-to-contact arm sweeps its whole reach in its
# first rest and lands on its home detent: x home -> lo -> hi -> home tooth by
# tooth at step_period, then (at a still x) an elbow sweep and a shoulder
# sweep, each three single-channel legs (elbow e0 -> e0 - .425 span ->
# e0 + .425 span -> e0; shoulder 0 -> -3 deg -> -3 deg + .85 span -> 0). The
# arms of one mechanism home one after another from HOME_T0; a sweep is only
# made when it ends HOME_GAP before the first travel of any arm of its
# mechanism and is clear of every sibling (loam.score._Solver.home), so it
# never costs a note. HOME_T0 is a quarter second in: the bells pair needs
# 18.46 s of the 20.72 s before bells_arm0 first leaves (its first note at
# 23.571 s, 14 steps and STILL_S before it).
#
# HOME_JOINT_S is each joint sweep's whole window (its three legs). The planner
# has no arm geometry, so it is one value a kind, sized for the worst arm: the
# tip must stay <= 0.5 SERVO_V_MAX with each leg a rest-to-rest 3-4-5 given
# the sweep's time in proportion to its joint amplitude (peak 1.875 x the mean
# speed). The tip paths on today's layouts (r = l2 for the elbow, |wrist - root|
# for the shoulder): elbow 0.97-1.28 m (bars_arm0 the longest), shoulder
# 0.50-0.66 m (bells_arm1), so >= 1.60 s and >= 0.83 s.
HOME_T0 = 0.25
HOME_GAP = 2.0
HOME_JOINT_S = dict(elbow=1.65, shoulder=0.9)
HOME_JOINTS = ('elbow', 'shoulder')


def home_legs(x_home, x_lo, x_hi, x_joint=None):
    """A homing sweep as (t0, t1, what, a, b) legs from 0: what 'x' moves
    the carriage from a to b tooth by tooth at step_period (teeth(b - a) steps
    of step_period(b - a) each); what 'elbow' / 'shoulder' is that joint's
    whole sweep (HOME_JOINT_S) at the still x a == b. The joint sweeps happen
    where the x path first stands on `x_joint` (the rig picks it from the
    layout: home, or a reach end away from another mechanism); None means at
    home, after the x legs. Any coordinate whose differences are metres will do
    (the planner's axis x WORLD_SCALE, the rig's world x): the times depend only
    on the distances, and the total does not depend on x_joint."""
    out, t = [], 0.0
    xj = x_home if x_joint is None else x_joint
    done = False
    def joints(x):
        nonlocal t
        for j in HOME_JOINTS:
            out.append((t, t + HOME_JOINT_S[j], j, x, x))
            t += HOME_JOINT_S[j]
    for a, b in ((x_home, x_lo), (x_lo, x_hi), (x_hi, x_home)):
        if abs(b - a) <= 1e-12:
            continue
        T = contact_travel_s(b - a)
        out.append((t, t + T, 'x', a, b))
        t += T
        if not done and x_joint is not None and abs(b - xj) <= 1e-9:
            joints(b); done = True
    if out and not done:
        joints(x_home)
    return out


def travel_s(kind, dx):
    """What a move of `dx` metres wants, given the arm's vocabulary."""
    if contact_to_contact(kind):
        return contact_travel_s(dx)
    return stepped_travel_s(dx) if stepped(kind) else servo_travel_s(dx)


def floor_s(kind, dx):
    """The least time a move of `dx` metres can take. A travel planned
    shorter than this is not a hurried machine, it is no machine at all."""
    if contact_to_contact(kind):
        return contact_floor_s(kind, dx)
    return stepped_floor_s(dx) if stepped(kind) else servo_floor_s(dx)

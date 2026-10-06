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
  carriage's top speed `SERVO_V_MAX`, which is also its floor. An unhurried
  one sets off up to `SLEW_SLACK_S` sooner when the arm is free (`slew_lead`);
  an announced rake roll's crossing sooner still, so it has crossed by the
  apex hold (`announce_lead`).

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
SLEW_SLACK_S = .25                  # PLAYERS M2: an unhurried servo slew leaves up to this much earlier (slew_lead)
SERVO_V_MAX = 3.0                    # m/s: the fastest a servo carriage runs
# PLAYERS M2 round 3: the servo carriage's acceleration ceiling, the goal's rule ("a servo carriage moves at <= SERVO_V_MAX
# and <= 3 g"; ruler 14 holds the rake's to it). A poised pick travel ends at its poise wherever its S-curve keeps both
# (servo_fast_s); the pick travels the score leaves no such choice (the M7 run's 39 ms hops) are the goal's known exception
SERVO_A_MAX_G = 3.0
SERVO_RAMP = .3                     # the servo S-curve's ramp share at each end (formlab/servo.py SCURVE_RAMP is this one)
# the kinds whose carriage is ONE servo S-curve a travel, leaving at the score's go and arriving between servo_fast_s
# after it and the score's arrive (formlab/servo.py): the planner bounds where such a carriage is in between instead of
# charging it the whole crossed interval (servo_span); OCC_DT is the step that bound is held constant over
SERVO_PROFILED = ('pick',)
OCC_DT = .01
# m (world): the margin formlab.rig._schedules keeps over a mechanism's arm_clearance (its PAD). The interval model never
# came within it; a servo-profiled plan can (harp_arm1's 43.93 travel passed harp_arm2's 44.29 at 0.2787 m), so the
# planner carries it for those arms and the rig, which only asserts the plan, still pushes nothing
OCC_PAD = .01
# PLAYERS M2 round 3 (A24), the slew cap's rake clause: an ANNOUNCED roll (the comb rises to an apex, holds it still for
# RAKE_HOLD_S, D5/D7, and runs up into its first string over RAKE_RUNUP_S) whose carriage crosses the rail under the
# backswing must have crossed by the hold's start, so slew_lead charges it announce_lead(dx) = rake_cross_s(dx) + hold +
# run-up before the contact. RAKE_CROSS_V is that crossing's mean speed, from the least-rho backswing designs (tools/
# rake_design.py, the carriage arriving with the head): ruler 14's rho reaches 1.0 at 0.406 s over the home crossing
# (0.663 m: 1.63 m/s) and at 0.524 s over the return (1.05 m: 2.00 m/s); the slower one, rounded down, holds both
# under it (the return's 0.656 s: least rho 0.78; designed at RHO_D 0.92, a 1.43 g peak). Round 2's fixed 0.8 s lead
# left the return 0.52 s and its carriage ran on under the hold at up to 1.3 m/s
ANNOUNCE_KINDS = ('rake',)
RAKE_CROSS_V = 1.6                  # m/s: an announced crossing's mean carriage speed (rake_cross_s)
RAKE_HOLD_S = .10                   # s: the apex hold (formlab/rake.py HOLD_MIN is this one; D5: >= 0.1 s)
RAKE_RUNUP_S = .25                  # s: the run-up from the apex into the first string (tools/rake_design.py RU_LO, RU_LO_B)
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


def slew_lead(kind, dx, want, room, arrive_s=None):
    """How long before `arrive` (the instant it stands on the contact's x)
    an UNHURRIED arm leaves: `want` is its travel's unhurried lead and `room`
    the time from when it came free to arrive, room >= want (a hurried arm
    is charged all of room and leaves the moment it is free). A servo that
    has to move (dx > 0) leaves up to SLEW_SLACK_S earlier than its want,
    and never before it is free: the slew is the same S-curve, only started
    sooner, so the arm is seen to set off for the next string rather than
    wait and then dart (PLAYERS M2, the goal's t_move = max(free_at, t -
    approach - min(idle, travel + 0.25 s))). An announced kind (the rake;
    `arrive_s` its arrive_lead, the contact less arrive) leaves at least
    announce_lead(dx) before the contact when the room holds it, so the
    crossing ends by the apex hold's start (A24); with less room it leaves
    the moment it is free, as before. Every other arm leaves at its
    want: a contact-to-contact carriage already owns the whole window from
    its last contact, and a still servo (dx = 0) keeps the M0 rule (t_move
    = arrive - travel), so only a real reposition gains the slack."""
    if dx > 0 and not stepped(kind):
        lead = want + SLEW_SLACK_S
        if announced(kind) and arrive_s is not None:
            lead = max(lead, announce_lead(dx) - arrive_s)
        return min(room, lead)
    return want


def announced(kind):
    """Does an arm of this kind announce a roll (a backswing to an apex it
    holds, then the run-up), its crossing charged by announce_lead?"""
    return kind in ANNOUNCE_KINDS


def rake_cross_s(dx):
    """An announced crossing of |dx| metres at RAKE_CROSS_V mean speed: the
    least the backswing's designed carriage needs under ruler 14's rho."""
    return abs(dx) / RAKE_CROSS_V


def announce_lead(dx):
    """How long before its first string an announced roll's carriage leaves
    to cross |dx| metres: the crossing, then the apex hold over a still
    carriage, then the run-up (formlab/rake.py announce)."""
    return rake_cross_s(dx) + RAKE_HOLD_S + RAKE_RUNUP_S


def servo_floor_s(dx):
    """A servo has no ratchet to coarsen: its floor is its top speed."""
    return abs(dx) / SERVO_V_MAX


def servo_s(u):
    """The servo's unit S-curve, 0 -> 1 over u in [0, 1]: w^3 - w^4/2 ramps
    on SERVO_RAMP at each end, a cruise between (formlab.rig.scurve and
    formlab/servo.py scurve_pieces are this law)."""
    u = min(max(u, 0.0), 1.0); r = SERVO_RAMP
    if u < r:
        w = u / r; s = r * (w**3 - w**4 / 2)
    elif u <= 1 - r:
        s = r / 2 + (u - r)
    else:
        w = (1 - u) / r; s = (1 - r) - r * (w**3 - w**4 / 2)
    return s / (1 - r)


def servo_fast_s(dx):
    """The least time the servo S-curve crosses |dx| metres: its peak speed
    (1/(1 - r) of the mean) within SERVO_V_MAX, its peak |x''| (1.5/(r (1 -
    r)) |dx|/T^2) within SERVO_A_MAX_G, and never under servo_floor_s. A
    poised pick travel ends at its poise when its window holds this
    (formlab/servo.py); the planner bounds a pick carriage by it."""
    d = abs(dx)
    if d <= 0:
        return 0.0
    r = SERVO_RAMP
    return max(servo_floor_s(d), d / ((1 - r) * SERVO_V_MAX),
               math.sqrt(1.5 * d / (r * (1 - r) * SERVO_A_MAX_G * G)))


def servo_profiled(kind):
    """Is this arm's carriage one servo S-curve a travel (SERVO_PROFILED)?"""
    return kind in SERVO_PROFILED


def servo_span(xa, xb, t0, t_fast, t_arr, ta, tb):
    """Where a servo-profiled carriage can be over [ta, tb] (inside its
    travel [t0, t_arr]): it leaves xa at t0 on the S-curve and lands on xb
    somewhere in [t_fast, t_arr], so at each instant it is between the
    curve that lands at t_arr (the slowest) and the one at t_fast; being
    monotone, over [ta, tb] it is between the slow one's position at ta and
    the fast one's at tb. The (lo, hi) of that, in xa's units."""
    def at(t, t1):
        return xa + (xb - xa) * (servo_s((t - t0) / (t1 - t0)) if t1 > t0 else 1.0)
    a, b = at(ta, t_arr), at(tb, t_fast)
    return (min(a, b), max(a, b))


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


# A servo arm's homing (PLAYERS M2, T5: the rake; the harps' is M7, A15). A
# servo has no detent to count teeth on: each x leg is one rest-to-rest 3-4-5
# peaking at <= HOME_SERVO_V (V345 x its mean speed), its time rounded UP to
# HOME_SERVO_DT, so the planner (axis x WORLD_SCALE) and the rig (the contacts'
# world x) draw the same legs whatever their last bits. Then, at home, the two
# joint windows: a servo's whole arm follows its head, so formlab/rake.py
# carries the head (y, h) through designed poses inside them, and the windows
# are sized for those poses' chords at the same peak (the rake: elbow 2.630 m,
# shoulder 1.229 m -> >= 4.48 s and >= 2.09 s; ruler 22 home allows 1.5 m/s;
# tools/rake_design.py --homing keeps the poses' chords inside these windows).
HOME_SERVO_KINDS = ('rake',)
HOME_SERVO_V = 1.1                  # m/s: a servo homing leg's peak tool speed
HOME_SERVO_DT = 0.1                 # s: an x leg's time is a whole number of these
HOME_SERVO_JOINT_S = dict(elbow=4.5, shoulder=2.1)


def servo_homes(kind):
    """Does a servo arm of this kind sweep its reach in its first rest?"""
    return kind in HOME_SERVO_KINDS


def homes(kind):
    """Does an arm of this kind get a homing sweep (a `home` cue)?"""
    return contact_to_contact(kind) or servo_homes(kind)


def servo_home_legs(x_home, x_lo, x_hi):
    """A servo's homing sweep as (t0, t1, what, a, b) legs from 0, the shape
    home_legs gives: 'x' legs home -> lo -> hi -> home (each one 3-4-5,
    HOME_SERVO_V peak, HOME_SERVO_DT steps), then the 'elbow' and 'shoulder'
    windows (HOME_SERVO_JOINT_S) at home, a == b. Only distances count, so any
    coordinate in metres will do (as home_legs). The 1e-6 guard keeps a leg
    whose ideal time is a whole number of steps from gaining one on a last bit."""
    out, t = [], 0.0
    for a, b in ((x_home, x_lo), (x_lo, x_hi), (x_hi, x_home)):
        if abs(b - a) <= 1e-12:
            continue
        T = math.ceil(V345 * abs(b - a) / HOME_SERVO_V / HOME_SERVO_DT - 1e-6) * HOME_SERVO_DT
        out.append((t, t + T, 'x', a, b))
        t += T
    if out:
        for j in HOME_JOINTS:
            out.append((t, t + HOME_SERVO_JOINT_S[j], j, x_home, x_home))
            t += HOME_SERVO_JOINT_S[j]
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


# The rake's roll (PLAYERS M2, Q1 and docs/goals/the-players.md A13). A sweep
# is ONE event whose strings sound in order along the comb's path, at onsets
# that follow the path rather than a fixed spacing: ev['onsets'], offsets from
# ev['t'], one a string, onsets[0] = 0 (the roll's first onset stays at the
# scored time) and onsets[-1] = spread_s * (n - 1), the roll's whole length.
# That last identity keeps every consumer that only needs the roll's END (the
# planner's t_last, the rig's window, ruler 25's ledger) right with spread_s
# alone; every consumer that needs a string's own time asks `string_times`.
# 0.541 s is the shortest roll that meets every ruler-14 bound on the interim
# comb with a 5 % margin (ρ <= 1.0 at E ~ 0.128 m, the speed ratio, the
# carriage's 3 g and its 0.0146 m of rail overtravel past the outer strings,
# which caps it at 0.639 m/s there); the 0.26 s default needs M9's hand.
RAKE_ROLL_S = 0.541                 # s: first string to last, both directions
# ...and the onsets of an UP roll (rake00 -> rake04, x rising) as fractions of
# it: the SLSQP optimum at 0.541 s (0, 0.191, 0.328, 0.413, 0.541 s), slow off
# the outer strings and fast across the middle. Fractions, so RAKE_ROLL_S is
# retuned in one place; a DOWN roll is the mirror (rake_onsets).
RAKE_ONSET_FRACTIONS = (0.0, 191/541, 328/541, 413/541, 1.0)


def rake_onsets(up=True, T=RAKE_ROLL_S):
    """A roll's onsets, offsets from its first string's time: T times
    RAKE_ONSET_FRACTIONS going up; going down the mirror, T (1 - f) read
    backwards, so the path the comb crosses fast is the same middle."""
    f = RAKE_ONSET_FRACTIONS
    return [T * u for u in f] if up else [T * (1.0 - u) for u in f[::-1]]


def string_times(ev):
    """Each string's absolute contact time in a score event: t + onsets[k]
    when the event carries its own onsets (a rake roll, from M2), else
    t + k * spread_s (uniform; a single string's is just t). The one rule
    every per-string-time consumer reads (the bake, the declared structure,
    the motion and bake rulers, the harness's ScoreDoc.string_times)."""
    t = float(ev['t']); n = len(ev.get('strings') or ())
    on = ev.get('onsets')
    if on is not None:
        if len(on) != n:
            raise ValueError(f"event {ev.get('i')}: {len(on)} onsets for {n} strings")
        return [t + float(o) for o in on]
    sp = float(ev.get('spread_s', 0))
    return [t + k * sp for k in range(n)]

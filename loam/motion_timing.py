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
  Unhurried that is `CLICK_S` a tooth. Hurried, clicks come no faster than
  `CLICK_MIN_S` and each spans at most `CLICK_TEETH_MAX` teeth — that cap is
  the physical floor, and it is what the planner must respect. Without it
  "one click, sixteen teeth, 24 ms of motion" is a legal plan, which is 32
  m/s of carriage.
* **Servo** (pick, rake). A short move wants `SLEW_S` of lead whatever its
  length — an S-curve needs its ramps — and a long one is limited by the
  carriage's top speed `SERVO_V_MAX`, which is also its floor.

`WORLD_SCALE` is the other half of the fix: the score's positions are in its
own units and `tools/build_clockwork.py` multiplies them by three to place
the instrument in the room, so a planner reasoning about metres of rail has
to multiply too.
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

# Wind-up before the contact, per arm kind. A mallet lifts and cocks, so it
# wants the most; a hinged hammer flips its head instead of its arm and wants
# the least (formlab/rig.py, HAMMER).
APPROACH_S = dict(pick=.12, rake=.12, mallet=.14, hammer=.08)
STEPPED_KINDS = ('mallet', 'hammer')


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


def travel_s(kind, dx):
    """What a move of `dx` metres wants, given the arm's vocabulary."""
    return stepped_travel_s(dx) if stepped(kind) else servo_travel_s(dx)


def floor_s(kind, dx):
    """The least time a move of `dx` metres can take. A travel planned
    shorter than this is not a hurried machine, it is no machine at all."""
    return stepped_floor_s(dx) if stepped(kind) else servo_floor_s(dx)

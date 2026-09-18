#!/usr/bin/env python3
"""The planner's arm-clearance rule: two arms of one mechanism are real
objects that keep `arm_clearance` apart along the axis at every moment —
hovering, travelling, playing. Its travel rule: what a reposition costs
comes from the arm's motion vocabulary over the world distance it has to
cross (loam/motion_timing.py), not from a per-actuator constant. Also the
neck fan that puts the string spacing the model uses into the score."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
import numpy as np
from loam.score import Mechanism, _Solver
from loam import motion_timing as mt

fails = []
def check(name, cond, detail=""):
    print(f"  {'PASS' if cond else 'FAIL'} {name}: {detail}")
    if not cond: fails.append(name)

# 8 strings, 0.1 apart, two arms reaching everything.
m = Mechanism.build("h", "plucked", "steel", [50+2*i for i in range(8)], arms=2, overlap=8, span=0.7,
        approach_s=0.1, recover_s=0.05, travel_s=0.02)
for a in m.actuators: a.reach = [s.id for s in m.strings]
m.actuators[0].home = "h01"; m.actuators[1].home = "h06"
xs = [m.axis_pos(s.id) for s in m.strings]
check("axis positions evenly spaced", np.allclose(np.diff(xs), 0.1), str(np.round(xs, 3)))

# Without clearance the old point-arm planning stands: arm0 may sweep through arm1's hover.
m.arm_clearance = 0.0
s = _Solver(m)
p = s.plan(1.0, ["h07"])
check("no clearance: nearest free arm takes it", p is not None and p[0].id == "h_arm1", str(p and p[1]))
s.commit(1.0, ["h07"], *p)
# arm1 is still recovering at 1.02, so arm0 comes over and lands one string away from it.
p = s.plan(1.02, ["h06"])
check("no clearance: arm0 plays right next to arm1", p is not None and p[0].id == "h_arm0", str(p and p[1]))

# With clearance = 2.5 strings, the same asks are shaped by the other arm's body.
m.arm_clearance = 0.25
s = _Solver(m)
p = s.plan(1.0, ["h07"]); s.commit(1.0, ["h07"], *p)
check("arm1 (hovering at h06) takes h07", p[0].id == "h_arm1")
p = s.plan(1.02, ["h06"])
check("h06 next to arm1's hover (h07) is refused while arm1 is busy", p is None, str(p))
p = s.plan(2.0, ["h06"])
check("arm1 itself may step to h06 once free", p is not None and p[0].id == "h_arm1", str(p and p[1]))
p = s.plan(2.0, ["h04"])
check("h04 is 0.3 from h07: arm0 may take it", p is not None and p[0].id == "h_arm0", str(p and p[1]))
s.commit(2.0, ["h04"], *p)
# arm1 now wants h02: its path h07 -> h02 crosses arm0 hovering at h04.
p = s.plan(3.0, ["h02"])
check("arm1 cannot cross arm0 to reach h02; arm0 (0.2 away) takes it", p is not None and p[0].id == "h_arm0", str(p and p[1]))
s.commit(3.0, ["h02"], *p)
# During arm0's move (t_move..t) arm1 must not enter the swept interval [h02, h04].
tm = p[1]["t_move"]
lo, hi = s._range_at("h_arm0", 0.5*(tm+3.0))
check("moving arm owns the interval it crosses", np.isclose(lo, m.axis_pos("h02")) and np.isclose(hi, m.axis_pos("h04")), f"{lo:.2f}..{hi:.2f}")
lo, hi = s._range_at("h_arm0", 3.5)
check("after the move it hovers over the destination", np.isclose(lo, hi) and np.isclose(lo, m.axis_pos("h02")), f"{lo:.2f}")
# A simultaneous move by arm1 into h05 (0.1 from h04, arm0's from-string) overlaps in time: refused;
# h06 (0.2 from h04) is fine only once arm0 has left... the sweep charges the whole interval, so
# h06 vs [h02,h04] = 0.2 < 0.25 while overlapping in time, but after arm0 has arrived it is 0.4 away.
p = s.plan(3.0, ["h05"])
check("no arm may play next to a sweeping arm", p is None, str(p))
p = s.plan(2.95, ["h06"])
check("h06 while arm0 still sweeps h02..h04 is refused (0.2 < 0.25)", p is None, str(p))
p = s.plan(3.3, ["h06"])
check("h06 after arm0 has settled at h02 (0.4 away) is allowed", p is not None and p[0].id == "h_arm1", str(p and p[1]))

# options() counts only feasible arms under both rules.
check("options honour clearance", s.options(3.0, ["h05"]) == 0 and s.options(3.3, ["h06"]) == 1)

# ---- what a reposition costs -------------------------------------------------
# A mallet mechanism whose neighbouring bars are 12 teeth of the rack apart
# (0.566 m in the world). The vocabulary wants a click a tooth — 1.08 s — and
# the ratchet cannot cross it in less than ceil(12/4) clicks at CLICK_MIN_S.
# The old planner charged |index diff| x travel_s and would have said 0.02 s.
step_u = 12*mt.PITCH/mt.WORLD_SCALE
mm = Mechanism.build("m", "struck", "rosewood", [60, 62, 64, 65], arms=1, span=3*step_u,
        arm_kind="mallet", approach_s=0.1, recover_s=0.05, travel_s=0.02)
mm.actuators[0].home = "m00"
arm = mm.actuators[0]
check("neighbouring bars are 12 teeth apart", mt.teeth(_Solver(mm).span_m("m00", "m01")) == 12,
      f"{_Solver(mm).span_m('m00', 'm01'):.3f} m")

def after_m00(t, sid="m01"):
    """Plan `sid` at t with the arm having just played m00 at 0."""
    sv = _Solver(mm); sv.commit(0.0, ["m00"], arm, dict(t_move=-0.1, t_free=0.05, travel_s=0.0, from_string="m00"))
    return sv.plan(t, [sid])

p = after_m00(0.05 + 1.08 + 0.1)          # the whole unhurried want, and then some
check("an unhurried mallet clicks a tooth at a time", p is not None and np.isclose(p[1]["travel_s"], 12*mt.CLICK_S),
      str(p and round(p[1]["travel_s"], 4)))
p = after_m00(0.05 + 0.3 + 0.1)           # the plan's case: 12 teeth, 0.3 s of window
check("a 12-tooth reposition in 0.3 s is re-timed, not charged 0.02 s",
      p is not None and np.isclose(p[1]["travel_s"], 0.3) and np.isclose(p[1]["t_move"], 0.05),
      str(p and {k: round(v, 4) for k, v in p[1].items() if k in ("t_move", "travel_s")}))
p = after_m00(0.05 + 0.1 + 0.1)           # under ceil(12/4) clicks at CLICK_MIN_S
check("and refused below the ratchet's own floor (0.1 s < 0.12 s)", p is None, str(p))
# A servo arm has no ratchet to coarsen: its floor is the carriage's top rate.
ss = Mechanism.build("s", "plucked", "steel", [60, 62], arms=1, span=mt.SERVO_V_MAX/mt.WORLD_SCALE,
        approach_s=0.1, recover_s=0.05, travel_s=0.02)   # the two strings a second's travel apart
ss.actuators[0].home = "s00"
sv = _Solver(ss); sv.commit(0.0, ["s00"], ss.actuators[0], dict(t_move=-0.1, t_free=0.05, travel_s=0.0, from_string="s00"))
check("a servo slew of V_MAX metres needs its second",
      sv.plan(0.05 + 0.99 + 0.1, ["s01"]) is None and sv.plan(0.05 + 1.01 + 0.1, ["s01"]) is not None,
      f"{sv.span_m('s00', 's01'):.2f} m at {mt.SERVO_V_MAX:g} m/s")

# The fan: log-spaced by length with the treble compressed; positions monotone and inside the width.
h = Mechanism.build("harp", "plucked", "steel", [50, 52, 53, 55, 57, 59, 60, 62], span=1.6, length_max=0.6)
before = [h.axis_pos(s.id) for s in h.strings]
h.fan(width=0.34, power=0.7, rise=(-0.4, 0.1))
after = [h.axis_pos(s.id) for s in h.strings]
check("fan keeps order", all(np.diff(after) > 0), str(np.round(after, 3)))
check("fan spans width x built extent", np.isclose(after[-1]-after[0], 0.34*(before[-1]-before[0])), f"{after[-1]-after[0]:.3f}")
check("treble end compressed (power < 1)", after[1]-after[0] > after[-1]-after[-2])
ys = [s.pos[1] for s in h.strings]
check("feet climb the soundboard", np.isclose(ys[0], -0.4) and np.isclose(ys[-1], 0.1) and all(np.diff(ys) > 0), str(np.round(ys, 3)))
check("fanned flag set", h.fanned)
g = Mechanism.build("harp", "plucked", "steel", [50, 52, 53, 55, 57, 59, 60, 62], span=1.6, length_max=0.6)
g.fan(width=0.5, by="index")
gx = [g.axis_pos(s.id) for s in g.strings]
check("index fan is uniform", np.allclose(np.diff(gx), 0.8/7), str(np.round(gx, 3)))

print("SCORE PLAN: " + ("PASS" if not fails else "FAIL " + str(fails)))
sys.exit(1 if fails else 0)

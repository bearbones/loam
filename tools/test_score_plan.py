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
# (0.566 m in the world). A mallet travels contact to contact
# (motion_timing.contact_to_contact): its head rides the rebound, so the
# carriage is free at the contact itself and arrives as the head lands. It
# wants a 3 g step a tooth (motion_timing.step_period, 0.160 s) and then the
# cocked hold and the downstroke over a still carriage (still_s, STILL_S
# 0.37): 12 x 0.160 + 0.37 s. Short of that it freewheels over the whole
# window, and it is refused only below the 3-4-5 law at 5 g and HURRIED_RHO
# head extents a frame (0.258 s here). The head's own rule is unchanged: its
# next stroke may not begin before t_free.
step_u = 12*mt.PITCH/mt.WORLD_SCALE
mm = Mechanism.build("m", "struck", "rosewood", [60, 62, 64, 65], arms=1, span=3*step_u,
        arm_kind="mallet", approach_s=0.1, recover_s=0.05, travel_s=0.02)
mm.actuators[0].home = "m00"
arm = mm.actuators[0]
d12 = _Solver(mm).span_m("m00", "m01")
check("neighbouring bars are 12 teeth apart", mt.teeth(d12) == 12, f"{d12:.3f} m")
flr = mt.floor_s("mallet", d12)
check("the mallet floor is the 3-4-5 law at the hurried ceilings",
      np.isclose(flr, max(np.sqrt(mt.A345*d12/(mt.HURRIED_G*mt.G)), mt.V345*d12/(mt.FPS*mt.HURRIED_RHO*mt.HEAD_E["mallet"]))),
      f"{flr:.4f} s")

def after_m00(t, sid="m01"):
    """Plan `sid` at t with the arm having just played m00 at 0."""
    sv = _Solver(mm); sv.commit(0.0, ["m00"], arm, dict(t_move=-0.1, t_free=0.05, t_head_free=0.0,
                                                         travel_s=0.0, from_string="m00"))
    return sv.plan(t, [sid])

sp = mt.step_period(d12)
check("a step is a 3-4-5 over one tooth at 3 g, STEP_MOVE of its period",
      np.isclose(sp, np.sqrt(mt.A345*(d12/12)/(mt.FREE_G*mt.G))/mt.STEP_MOVE) and 0.155 < sp < 0.165, f"{sp:.4f} s")
check("the unhurried travel is a step_period a tooth",
      np.isclose(mt.contact_travel_s(d12), 12*sp) and mt.contact_travel_s(0.0) == 0.0)
check("one regime rule: a window that holds every step steps, else it freewheels",
      mt.travel_regime(d12, 12*sp) == "step" and mt.travel_regime(d12, 12*sp-0.01) == "freewheel"
      and mt.travel_regime(0.0, 1.0) == "still")
check("a stepped period stretches to P_MAX and never below step_period",
      np.isclose(mt.stepped_period(d12, 12*sp), sp) and np.isclose(mt.stepped_period(d12, 10.0), mt.P_MAX))
check("hurried: the 3 g / 1.0 E freewheel does not fit the window",
      mt.hurried("mallet", d12, 0.3) and not mt.hurried("mallet", d12, 0.5) and not mt.hurried("pick", d12, 0.1))
want = mt.contact_travel_s(d12) + mt.still_s("mallet", arm.approach_s)
check("the still lead holds the cocked hold and the longest downstroke", np.isclose(want-12*sp, 0.37), f"{want:.4f} s")
p = after_m00(want + 0.2)                  # the whole unhurried want, and then some
check("an unhurried mallet steps a tooth at a time, then strokes over a still carriage",
      p is not None and np.isclose(p[1]["travel_s"], want) and np.isclose(p[1]["t_move"], 0.2),
      str(p and {k: round(v, 4) for k, v in p[1].items() if k in ("t_move", "travel_s")}))
check("a mallet's carriage is free at its contact, its head at t_free",
      p is not None and np.isclose(p[1]["t_head_free"], want + 0.2) and np.isclose(p[1]["t_free"], want + 0.25),
      str(p and {k: round(v, 4) for k, v in p[1].items() if k in ("t_head_free", "t_free")}))
p = after_m00(0.3)                         # 12 teeth in 0.3 s, contact to contact
check("a 12-tooth travel in a 0.3 s window leaves at the contact, inside the head's recover",
      p is not None and np.isclose(p[1]["travel_s"], 0.3) and np.isclose(p[1]["t_move"], 0.0),
      str(p and {k: round(v, 4) for k, v in p[1].items() if k in ("t_move", "travel_s")}))
p = after_m00(flr - 0.005)                 # head is free (0.253 - 0.1 >= 0.05), carriage is not
check("and refused below the 3-4-5 floor though the head is free", p is None, str(p))
p = after_m00(0.14, "m00")                 # the same bar again: the head rule still binds
check("a repeat before t_free + approach is refused (head rule)", p is None, str(p))
p = after_m00(0.16, "m00")
check("a repeat after it is played, the carriage free from the contact",
      p is not None and np.isclose(p[1]["t_move"], 0.0), str(p and round(p[1]["t_move"], 4)))
# Homing (ruler 22): x home -> lo -> hi -> home tooth by tooth, then the joint
# sweeps; the planner charges the whole window, wherever the rig puts the joints.
legs = mt.home_legs(0.0, -2*d12, d12)
xs = [g for g in legs if g[2] == "x"]
check("homing x legs run tooth by tooth at step_period",
      [round(g[1]-g[0], 9) for g in xs] == [round(mt.contact_travel_s(g[4]-g[3]), 9) for g in xs]
      and [(g[3], g[4]) for g in xs] == [(0.0, -2*d12), (-2*d12, d12), (d12, 0.0)])
check("then an elbow and a shoulder sweep at home, HOME_JOINT_S each",
      [g[2] for g in legs[3:]] == ["elbow", "shoulder"] and all(g[3] == g[4] == 0.0 for g in legs[3:])
      and np.isclose(legs[-1][1], sum(mt.contact_travel_s(g[4]-g[3]) for g in xs)+sum(mt.HOME_JOINT_S.values())))
alt = mt.home_legs(0.0, -2*d12, d12, x_joint=-2*d12)
check("joints at a reach end: same window, joints where x first stands there",
      np.isclose(alt[-1][1], legs[-1][1]) and [g[2] for g in alt] == ["x", "elbow", "shoulder", "x", "x"]
      and all(g[3] == -2*d12 for g in alt[1:3]))
check("contiguous legs from 0", np.isclose(legs[0][0], 0.0) and all(np.isclose(u[1], v[0]) for u, v in zip(legs, legs[1:])))
# A servo arm has no ratchet to coarsen: its floor is the carriage's top rate.
ss = Mechanism.build("s", "plucked", "steel", [60, 62], arms=1, span=mt.SERVO_V_MAX/mt.WORLD_SCALE,
        approach_s=0.1, recover_s=0.05, travel_s=0.02)   # the two strings a second's travel apart
ss.actuators[0].home = "s00"
sv = _Solver(ss); sv.commit(0.0, ["s00"], ss.actuators[0], dict(t_move=-0.1, t_free=0.05, travel_s=0.0, from_string="s00"))
check("a servo slew of V_MAX metres needs its second",
      sv.plan(0.05 + 0.99 + 0.1, ["s01"]) is None and sv.plan(0.05 + 1.01 + 0.1, ["s01"]) is not None,
      f"{sv.span_m('s00', 's01'):.2f} m at {mt.SERVO_V_MAX:g} m/s")
# The latest start of a carriage that does not move (dx = 0, e.g. strings that
# share a coordinate, priced by the per-index floor): only a contact-to-contact
# arm (the mallet, M1) gives up its late start to the travel it charges; every
# other kind keeps the floor-bounded latest start it had (arrive - floor = arrive).
def latest_still(mech, act, t_hit, sid):
    sv = _Solver(mech); sv.commit(0.0, [sid], act, dict(t_move=-0.1, t_free=0.05, t_head_free=0.0, travel_s=0.0,
                                                        from_string=sid))
    got = {}; push = sv._push
    def spy(a, t0, t_hi, t_arrive, *rest):
        got.update(t0=t0, t_hi=t_hi, arrive=t_arrive); return push(a, t0, t_hi, t_arrive, *rest)
    sv._push = spy; sv.travel = lambda a, f, t: 0.3      # a per-index floor on a shared coordinate
    sv._feasible(act, t_hit, [sid], 0.0)
    return got
g = latest_still(ss, ss.actuators[0], 2.0, "s00")
check("a still servo arm keeps its latest start at arrive (the M0 rule)",
      g and np.isclose(g["t_hi"], g["arrive"]) and np.isclose(g["t0"], g["arrive"]-0.3), str(g))
g = latest_still(mm, arm, 2.0, "m00")
check("a still mallet carriage starts no later than arrive - its charged travel",
      g and np.isclose(g["t_hi"], g["t0"]) and np.isclose(g["arrive"]-g["t_hi"], 0.3+mt.still_s("mallet", arm.approach_s)), str(g))

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

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
# An arm crossing the rail is charged the whole interval it crosses unless its
# carriage is servo-profiled (motion_timing.SERVO_PROFILED, the pick: PLAYERS M2
# round 3): then only where its one S-curve can be, OCC_DT step by step, plus the
# rig's pad. The scenario runs twice: as every unprofiled kind plans (the
# interval rule) and as the pick does (the law), whose plans are then held to the
# clearance on the true S-curves, whichever end of [t_fast, arrive] each lands at.
def true_gap(A, B, t0, t1, n=2001):
    """The least gap between two travels (xa, xb, t_move, t_fast, t_arr) over [t0, t1], each anywhere between
    its fastest and slowest S-curve (servo_s is monotone, so those bound every landing in between)."""
    tt = np.linspace(t0, t1, n)
    def band(mv):
        xa, xb, tm, tf, ta = mv
        c = [np.array([xa+(xb-xa)*mt.servo_s((t-tm)/(T-tm)) for t in tt]) for T in (tf, ta)]
        return np.minimum(*c), np.maximum(*c)
    (alo, ahi), (blo, bhi) = band(A), band(B)
    return float(np.maximum(alo-bhi, blo-ahi).min())
def clearance_scenario():
    m.arm_clearance = 0.25
    s = _Solver(m); r = {}
    p = s.plan(1.0, ["h07"]); s.commit(1.0, ["h07"], *p); r["take h07"] = p[0].id
    r["h06 busy"] = s.plan(1.02, ["h06"])
    p = s.plan(2.0, ["h06"]); r["step h06"] = p and p[0].id
    p = s.plan(2.0, ["h04"]); r["take h04"] = p and p[0].id
    s.commit(2.0, ["h04"], *p)
    # arm1 now wants h02: its path h07 -> h02 crosses arm0 hovering at h04.
    p = s.plan(3.0, ["h02"]); r["take h02"] = p and p[0].id
    s.commit(3.0, ["h02"], *p)
    tm = p[1]["t_move"]; r["move0"] = s.moves["h_arm0"][-1]
    r["mid"] = s._range_at("h_arm0", 0.5*(tm+3.0)); r["after"] = s._range_at("h_arm0", 3.5)
    # A simultaneous move by arm1 into h05 (0.1 from h04, arm0's from-string) overlaps in time; h06 (0.2 from
    # h04) is fine only once arm0 has left: the interval rule charges [h02, h04] throughout, 0.2 < 0.25
    r["h05"] = s.plan(3.0, ["h05"]); r["h06 sweeping"] = s.plan(2.95, ["h06"]); r["h06 settled"] = s.plan(3.3, ["h06"])
    r["options"] = (s.options(3.0, ["h05"]), s.options(3.3, ["h06"])); r["solver"] = s
    return r
was = mt.SERVO_PROFILED
try:
    mt.SERVO_PROFILED = (); u = clearance_scenario()          # the interval rule (every unprofiled kind)
finally:
    mt.SERVO_PROFILED = was
w = clearance_scenario()                                      # the pick, servo-profiled
for tag, r in (("interval", u), ("pick law", w)):
    check(f"[{tag}] arm1 (hovering at h06) takes h07", r["take h07"] == "h_arm1")
    check(f"[{tag}] h06 next to arm1's hover (h07) is refused while arm1 is busy", r["h06 busy"] is None, str(r["h06 busy"]))
    check(f"[{tag}] arm1 itself may step to h06 once free", r["step h06"] == "h_arm1")
    check(f"[{tag}] h04 is 0.3 from h07: arm0 may take it", r["take h04"] == "h_arm0")
    check(f"[{tag}] arm1 cannot cross arm0 to reach h02; arm0 (0.2 away) takes it", r["take h02"] == "h_arm0")
    check(f"[{tag}] after the move it hovers over the destination", np.isclose(*r["after"]) and np.isclose(r["after"][0], m.axis_pos("h02")))
    check(f"[{tag}] h06 after arm0 has settled at h02 (0.4 away) is allowed", r["h06 settled"] is not None and r["h06 settled"][0].id == "h_arm1")
lo, hi = u["mid"]
check("[interval] a moving arm owns the interval it crosses", np.isclose(lo, m.axis_pos("h02")) and np.isclose(hi, m.axis_pos("h04"))
      and u["move0"][6] is None, f"{lo:.2f}..{hi:.2f}")
check("[interval] no arm may play next to a sweeping arm", u["h05"] is None, str(u["h05"]))
check("[interval] h06 while arm0 still sweeps h02..h04 is refused (0.2 < 0.25)", u["h06 sweeping"] is None, str(u["h06 sweeping"]))
check("[interval] options honour clearance", u["options"] == (0, 1), str(u["options"]))
mv0 = w["move0"]; law0 = mv0[6]; lo, hi = w["mid"]
check("[pick law] a moving pick owns only where its S-curve can be, inside the interval it crosses",
      law0 is not None and m.axis_pos("h02") <= lo <= hi <= m.axis_pos("h04") and hi-lo < 0.5*(m.axis_pos("h04")-m.axis_pos("h02")),
      f"{lo:.3f}..{hi:.3f} of {m.axis_pos('h02'):.2f}..{m.axis_pos('h04'):.2f}")
W = 0.25 + mt.OCC_PAD/mt.WORLD_SCALE
for key, t in (("h05", 3.0), ("h06 sweeping", 2.95)):
    p_ = w[key]; ok = p_ is not None
    if ok:
        sv_ = w["solver"]; sv_.at["h_arm1"] = "h07"; sid = "h05" if key == "h05" else "h06"
        t_arr = t - mt.arrive_lead("pick", 0.1); law1 = sv_._law(p_[0], [sid], p_[1]["t_move"], t_arr)
        A = (law0[0], law0[1], mv0[0], law0[2], mv0[1]); B = (law1[0], law1[1], p_[1]["t_move"], law1[2], t_arr)
        g_ = true_gap(A, B, p_[1]["t_move"], mv0[1])
    check(f"[pick law] {sid if ok else key} at {t}: planned while arm0 crosses, and the true S-curves keep clearance + the rig's pad",
          ok and g_ >= W - 1e-9, f"t_move {p_[1]['t_move']:.4f}, least gap {g_:.4f} >= {W:.4f}" if ok else str(p_))
check("[pick law] options count it", w["options"] == (1, 1), str(w["options"]))
m.arm_clearance = 0.25
s = w["solver"]

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
# A servo kind (the rake, PLAYERS M2) homes the same shape on one 3-4-5 a leg:
# each x leg peaks <= HOME_SERVO_V on whole HOME_SERVO_DT steps, then the two
# joint windows; a harp (A15, M7's) and a still kind get no sweep at all.
sl = mt.servo_home_legs(0.0, -0.5, 0.3)
sx = [g for g in sl if g[2] == "x"]
check("servo homing: x legs home -> lo -> hi -> home on whole HOME_SERVO_DT steps",
      [(g[3], g[4]) for g in sx] == [(0.0, -0.5), (-0.5, 0.3), (0.3, 0.0)]
      and all(np.isclose((g[1]-g[0])/mt.HOME_SERVO_DT, round((g[1]-g[0])/mt.HOME_SERVO_DT)) for g in sx)
      and all(mt.V345*abs(g[4]-g[3])/(g[1]-g[0]) <= mt.HOME_SERVO_V*(1+1e-9) for g in sx),
      str([round(g[1]-g[0], 6) for g in sx]))
check("...then the elbow and shoulder windows at home, HOME_SERVO_JOINT_S each, contiguous from 0",
      [g[2] for g in sl[3:]] == ["elbow", "shoulder"] and all(g[3] == g[4] == 0.0 for g in sl[3:])
      and [round(g[1]-g[0], 9) for g in sl[3:]] == [mt.HOME_SERVO_JOINT_S[j] for j in ("elbow", "shoulder")]
      and np.isclose(sl[0][0], 0.0) and all(np.isclose(u[1], v[0]) for u, v in zip(sl, sl[1:])),
      str([(g[2], round(g[0], 3), round(g[1], 3)) for g in sl]))
check("only the rake homes among the servo kinds (harps are M7's, A15); stepped kinds (mallet, hammer) home on the rack",
      mt.homes("rake") and mt.servo_homes("rake") and mt.homes("mallet") and mt.homes("hammer")
      and not mt.homes("pick") and not mt.servo_homes("mallet") and not mt.servo_homes("hammer"),
      str({k: mt.homes(k) for k in ("rake", "mallet", "pick", "hammer")}))
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

# ---- the unhurried slew (PLAYERS M2, motion_timing.slew_lead) ----------------
# A servo that repositions sets off up to SLEW_SLACK_S before its want, never
# before it is free: t_move = max(free_at, arrive - travel - SLEW_SLACK_S). A
# short move (0.3 m: SLEW_S of travel) from s00, played at 0 and free at 0.05.
sh = Mechanism.build("s", "plucked", "steel", [60, 62], arms=1, span=0.3/mt.WORLD_SCALE,
        approach_s=0.1, recover_s=0.05, travel_s=0.02)
sh.actuators[0].home = "s00"
def slew_after_s00(t, mech=sh, sid="s01"):
    sv = _Solver(mech); act = mech.actuators[0]
    sv.commit(0.0, ["s00"], act, dict(t_move=-0.1, t_free=0.05, t_head_free=0.05, travel_s=0.0, from_string="s00"))
    return sv.plan(t, [sid])
tr_s = mt.servo_travel_s(_Solver(sh).span_m("s00", "s01"))
check("a short servo move wants SLEW_S", np.isclose(tr_s, mt.SLEW_S), f"{tr_s:.3f} s")
t_hit = 0.05 + tr_s + mt.SLEW_SLACK_S + 0.1 + 0.5        # idle >= travel + slack, with 0.5 s to spare
p = slew_after_s00(t_hit)
check("an idle servo slew leaves SLEW_SLACK_S before its want (dx > 0)",
      p is not None and np.isclose(p[1]["t_move"], t_hit - 0.1 - tr_s - mt.SLEW_SLACK_S)
      and np.isclose(p[1]["travel_s"], tr_s + mt.SLEW_SLACK_S),
      str(p and {k: round(v, 4) for k, v in p[1].items() if k in ("t_move", "travel_s")}))
t_hit = 0.05 + tr_s + 0.1 + 0.1                          # idle 0.5 s: room for the want, not the slack
p = slew_after_s00(t_hit)
check("...and with idle < travel + SLEW_SLACK_S it leaves the moment it is free",
      p is not None and np.isclose(p[1]["t_move"], 0.05) and np.isclose(p[1]["travel_s"], tr_s + 0.1),
      str(p and {k: round(v, 4) for k, v in p[1].items() if k in ("t_move", "travel_s")}))
t_hit = 0.05 + 0.3 + 0.1                                 # idle 0.3 < want: hurried, unchanged
p = slew_after_s00(t_hit)
check("a hurried servo slew is charged from free_at as before",
      p is not None and np.isclose(p[1]["t_move"], 0.05) and np.isclose(p[1]["travel_s"], 0.3),
      str(p and {k: round(v, 4) for k, v in p[1].items() if k in ("t_move", "travel_s")}))
check("slew_lead: only a servo that moves gains the slack",
      np.isclose(mt.slew_lead("pick", 0.3, 0.4, 9.0), 0.4 + mt.SLEW_SLACK_S)
      and np.isclose(mt.slew_lead("rake", 0.3, 0.4, 0.5), 0.5)
      and mt.slew_lead("pick", 0.0, 0.4, 9.0) == 0.4
      and mt.slew_lead("mallet", 0.3, 0.4, 9.0) == 0.4 and mt.slew_lead("hammer", 0.3, 0.4, 9.0) == 0.4)
want_m = mt.contact_travel_s(d12) + mt.still_s("mallet", arm.approach_s)
p = after_m00(want_m + 1.0)                              # a second to spare: still no slack for a mallet
check("mallets are unchanged: an idle mallet still leaves at arrive - want",
      p is not None and np.isclose(p[1]["t_move"], 1.0) and np.isclose(p[1]["travel_s"], want_m),
      str(p and {k: round(v, 4) for k, v in p[1].items() if k in ("t_move", "travel_s")}))
g = latest_still(sh, sh.actuators[0], 2.0, "s00")       # dx = 0 with a second idle: the M0 rule stands
check("a still servo arm gains no slack: t0 = arrive - travel (the M0 rule, under M2)",
      g and np.isclose(g["t0"], g["arrive"]-0.3) and np.isclose(g["t_hi"], g["arrive"]), str(g))

# ---- an announced rake crossing (PLAYERS M2 round 3, A24: motion_timing.announce_lead) ----
# The rake's announced roll holds its apex still (D7) for RAKE_HOLD_S and runs up
# over RAKE_RUNUP_S, so a carriage that crosses the rail under the backswing must
# have crossed by the hold: it leaves announce_lead(dx) = dx / RAKE_CROSS_V + hold
# + run-up before the contact, never before it is free. Round 2 charged a fixed
# 0.8 s (want 0.4 + slack 0.25 + approach 0.15) and the 1.05 m return ran on
# under the hold at up to 1.41 m/s.
arr_rk = mt.arrive_lead("rake", 0.15)
check("slew_lead keeps its M2 form: no arrive_s, or a kind that announces nothing",
      np.isclose(mt.slew_lead("pick", 0.3, 0.4, 9.0), 0.4 + mt.SLEW_SLACK_S)
      and mt.slew_lead("pick", 0.3, 0.4, 9.0, 0.09) == mt.slew_lead("pick", 0.3, 0.4, 9.0)
      and mt.slew_lead("rake", 1.05, 0.4, 9.0) == 0.4 + mt.SLEW_SLACK_S and not mt.announced("pick"))
check("an announced crossing leaves announce_lead(dx) before the contact: the crossing, the hold, the run-up",
      mt.announced("rake") and np.isclose(mt.slew_lead("rake", 1.05, 0.4, 9.0, arr_rk), mt.announce_lead(1.05) - arr_rk)
      and np.isclose(mt.announce_lead(1.05), 1.05/mt.RAKE_CROSS_V + mt.RAKE_HOLD_S + mt.RAKE_RUNUP_S)
      and np.isclose(mt.announce_lead(2.0) - mt.announce_lead(1.0), 1.0/mt.RAKE_CROSS_V),
      f"1.05 m: {mt.slew_lead('rake', 1.05, 0.4, 9.0, arr_rk):.5f} s before arrive ({mt.announce_lead(1.05):.5f} s before the contact)")
check("...a short crossing keeps its M2 lead (announce_lead under want + slack), and none leaves before it is free",
      np.isclose(mt.slew_lead("rake", 0.3, 0.4, 9.0, arr_rk), 0.4 + mt.SLEW_SLACK_S)
      and mt.slew_lead("rake", 1.05, 0.4, 0.7, arr_rk) == 0.7 and mt.slew_lead("rake", 0.0, 0.4, 9.0, arr_rk) == 0.4)
rr = Mechanism.build("s", "raked", "bronze", [60, 62], arms=1, span=1.05/mt.WORLD_SCALE, arm_kind="rake",
        approach_s=0.15, recover_s=0.05, travel_s=0.02)   # two strings 1.05 m apart: the return's crossing
rr.actuators[0].home = "s00"
dx_r = _Solver(rr).span_m("s00", "s01")
p = slew_after_s00(5.0, mech=rr)
check("the planner: an idle rake crossing leaves announce_lead(dx) before its contact",
      p is not None and np.isclose(p[1]["t_move"], 5.0 - mt.announce_lead(dx_r))
      and np.isclose(p[1]["travel_s"], mt.announce_lead(dx_r) - arr_rk),
      str(p and {k: round(v, 5) for k, v in p[1].items() if k in ("t_move", "travel_s")}) + f", dx {dx_r:.3f} m")
t_hit = 0.05 + arr_rk + mt.announce_lead(dx_r) - arr_rk - 0.1   # free 0.1 s too late for the whole lead
p = slew_after_s00(t_hit, mech=rr)
check("...and with less room it leaves the moment it is free",
      p is not None and np.isclose(p[1]["t_move"], 0.05), str(p and {k: round(v, 5) for k, v in p[1].items() if k == "t_move"}))

# ---- servo-profiled occupancy (PLAYERS M2 round 3: motion_timing.servo_span, OCC_DT, OCC_PAD) ----
# A pick carriage is one S-curve a travel, leaving at t_move and landing in
# [t_move + servo_fast_s, arrive]: the planner charges it only where that can be,
# step by OCC_DT step, not the whole crossed interval (harp_arm2's 44.29 travel
# waited 0.29 s on harp_arm1's under the interval model, and its poise slid).
f = mt.servo_fast_s(0.1088)
r_ = mt.SERVO_RAMP
check("servo_fast_s keeps the carriage's limits: peak speed <= SERVO_V_MAX, peak |x''| <= SERVO_A_MAX_G, >= the floor",
      0.1088/((1-r_)*f) <= mt.SERVO_V_MAX*(1+1e-9) and 1.5*0.1088/(r_*(1-r_)*f**2) <= mt.SERVO_A_MAX_G*mt.G*(1+1e-9)
      and f >= mt.servo_floor_s(0.1088) and mt.servo_fast_s(0.0) == 0.0,
      f"0.1088 m: {f:.4f} s (the M7 hop's score window is 0.0386 s)")
us = np.linspace(0, 1, 201); sv = [mt.servo_s(u) for u in us]
check("servo_s: 0 -> 1, monotone", sv[0] == 0.0 and np.isclose(sv[-1], 1.0) and all(np.diff(sv) >= -1e-15))
lo_, hi_ = mt.servo_span(0.0, 0.4, 0.0, 0.5, 0.6, 0.0, 0.6)
sp_ = [mt.servo_span(0.0, 0.4, 0.0, 0.5, 0.6, a_, a_+0.01) for a_ in np.arange(0.0, 0.6, 0.01)]
check("servo_span: the whole travel spans the crossed interval; a step spans the slow curve's start to the fast one's end",
      np.isclose(lo_, 0.0) and np.isclose(hi_, 0.4) and all(0.0 <= a_ <= b_ <= 0.4+1e-12 for a_, b_ in sp_)
      and np.isclose(sp_[10][0], 0.4*mt.servo_s(0.1/0.6)) and np.isclose(sp_[10][1], 0.4*mt.servo_s(0.11/0.5)))
check("_Solver._moving: no law, the whole interval; a law, servo_span over the OCC_DT step that holds t",
      _Solver._moving(0.0, 0.6, (0.0, 0.4), None, 0.123) == (0.0, 0.4)
      and np.allclose(_Solver._moving(0.0, 0.6, (0.0, 0.4), (0.0, 0.4, 0.5), 0.123), mt.servo_span(0.0, 0.4, 0.0, 0.5, 0.6, 0.12, 0.13))
      and np.allclose(_Solver._steps(0.0, 0.05, (0.0, 0.4, 0.05)), [0.01, 0.02, 0.03, 0.04]) and _Solver._steps(0.0, 0.05, None) == [])
# two pick arms on 0.1-spaced strings, arm1 crossing h03 -> h07 over [0, 0.6]; arm0 follows h01 -> h04
mo = Mechanism.build("h", "plucked", "steel", [50+2*i for i in range(8)], arms=2, overlap=8, span=0.7,
        approach_s=0.1, recover_s=0.05, travel_s=0.02)
for a in mo.actuators: a.reach = [s_.id for s_ in mo.strings]
mo.actuators[0].home = "h01"; mo.actuators[1].home = "h06"; mo.arm_clearance = 0.25
a0, a1 = mo.actuators
def follow():
    sv_ = _Solver(mo); sv_.at[a1.id] = "h03"
    law = sv_._law(a1, ["h07"], 0.0, 0.6); x3, x7 = mo.axis_pos("h03"), mo.axis_pos("h07")
    sv_.moves[a1.id].append((0.0, 0.6, 0.7, (x3, x7), (x7, x7), x7, law)); sv_.at[a1.id] = "h07"; sv_.at[a0.id] = "h01"
    return sv_, law, sv_._push(a0, 0.0, 0.7, 1.0, 1.0, ["h04"])
sv_, law1, t_law = follow()
was = mt.SERVO_PROFILED
try:
    mt.SERVO_PROFILED = (); _, law_none, t_int = follow()
finally:
    mt.SERVO_PROFILED = was
# the true carriages: each lands anywhere in [its t_fast, its arrive]; arm0 must clear arm1 + the pad for every pair
sv_.at[a0.id] = "h01"; law0 = sv_._law(a0, ["h04"], t_law, 1.0) if t_law is not None else None
gap = true_gap((law1[0], law1[1], 0.0, law1[2], 0.6), (law0[0], law0[1], t_law, law0[2], 1.0), t_law, 1.0) if law0 else -1.0
check("the planner's law lets a follower leave while the leader still crosses, and keeps the clearance and the rig's pad",
      law_none is None and t_int is not None and t_law is not None and t_law < t_int - 0.1
      and gap >= mo.arm_clearance + mt.OCC_PAD/mt.WORLD_SCALE - 1e-9,
      f"interval model leaves at {t_int}, the law at {t_law:.4f}; least gap {gap:.4f} >= {mo.arm_clearance + mt.OCC_PAD/mt.WORLD_SCALE:.4f}")
check("the follower's start is a step of the leader's law (a _push candidate) or its earliest",
      t_law is not None and any(np.isclose(t_law, c_) for c_ in [0.0] + [b_ + 1e-9 for b_ in _Solver._steps(0.0, 0.6, law1)]))
# OCC_PAD: the rig asserts the plan with PAD over the clearance, so a servo-profiled plan carries it too
sv2 = _Solver(mo); sv2.at[a1.id] = "h03"; sv2.at[a0.id] = "h00"; x3 = mo.axis_pos("h03")
sv2.moves[a1.id].append((-1.0, -0.5, -0.4, (x3, x3), (x3, x3), x3, None))
gap3 = x3 - mo.axis_pos("h00"); mo.arm_clearance = gap3 - 0.5*mt.OCC_PAD/mt.WORLD_SCALE
ok_pick = sv2._separated(a0, 0.0, 0.1, 0.2, ["h00"])
try:
    mt.SERVO_PROFILED = (); ok_plain = sv2._separated(a0, 0.0, 0.1, 0.2, ["h00"])
finally:
    mt.SERVO_PROFILED = was
mo.arm_clearance = 0.25
from formlab import rig as _rig
check("OCC_PAD: a servo-profiled arm keeps the rig's pad over the clearance (formlab.rig.PAD is it); others keep the bare clearance",
      not ok_pick and ok_plain and _rig.PAD == mt.OCC_PAD, f"gap {gap3:.4f} vs clearance + half the pad: pick {ok_pick}, unprofiled {ok_plain}")

# ---- the rake's roll (PLAYERS M2, Q1 / A13: motion_timing.rake_onsets, string_times) ----
# A roll's onsets follow the comb's path: offsets from t, from 0 to RAKE_ROLL_S,
# the down roll the mirror of the up one; the event stores them, and every
# per-string time is read through string_times (t + k spread_s without them).
up, down = mt.rake_onsets(True), mt.rake_onsets(False)
check("a roll runs RAKE_ROLL_S from its scored time, rising, down the mirror of up",
      up[0] == down[0] == 0.0 and up[-1] == down[-1] == mt.RAKE_ROLL_S
      and all(np.diff(up) > 0) and np.allclose(down, [mt.RAKE_ROLL_S-u for u in up[::-1]])
      and np.allclose(up, [0, .191, .328, .413, .541]), f"up {np.round(up, 3)}, down {np.round(down, 3)}")
check("string_times: a roll at its onsets, else t + k spread_s",
      mt.string_times(dict(t=2.0, strings=list("abcde"), spread_s=up[-1]/4, onsets=up)) == [2.0+o for o in up]
      and mt.string_times(dict(t=2.0, strings=list("abc"), spread_s=0.018)) == [2.0+k*0.018 for k in range(3)]
      and mt.string_times(dict(t=2.0, strings=["a"])) == [2.0])
from loam import Take, SR
from loam.score import Score, Instrument
rk = Mechanism.build("rake", "raked", "bronze", [50, 57, 62, 65, 69], arms=1, span=0.5, arm_kind="rake",
        approach_s=0.15, recover_s=0.10, travel_s=0.0)
roll = Score(Take(3.0, 1), "roll", instrument=Instrument("roll", [rk]))
ids = [st.id for st in rk.strings]
ev = roll.rake("rake", 1.0, ids, spread_s=up[-1]/4, onsets=up, dur=0.5)
check("Score.rake stores the roll's onsets; the plan prices its end (t_free = t + T + recover)",
      ev["onsets"] == up and ev["actuator"] == "rake_arm0" and np.isclose(ev["t_free"], 1.0+mt.RAKE_ROLL_S+0.10)
      and abs(ev["dur"]-(0.5+mt.RAKE_ROLL_S)) < 2/SR, f"t_free {ev['t_free']:.4f}, dur {ev['dur']:.4f}")
try:
    roll.rake("rake", 2.5, ids, spread_s=0.018, onsets=up, dur=0.5); broke = False
except AssertionError:
    broke = True
check("...and refuses onsets that do not end at spread_s * (n - 1)", broke)

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

# ---- fingered planner (PLAYERS M6b: Mechanism.hands, window_lo, finger, look-ahead, yielding) ----
fh = Mechanism.build("fh", "plucked", "steel", [50+2*i for i in range(10)], arms=2, overlap=4, span=0.9,
        approach_s=0.20, recover_s=0.15, travel_s=0.02, hands=4)
fh.arm_clearance = 0.05
sv_fh = _Solver(fh)
# A 4-note sixteenth run on fh00..fh03 (0.1786 s apart < 0.20 + 0.15 = 0.35 s):
# impossible for a point arm, played in one window fh00 by digits 0, 1, 2, 3.
run_evs = []
for k, sid in enumerate(("fh02", "fh01", "fh03", "fh00")):
    t_k = 1.0 + k * (60.0 / 84.0 / 4.0)
    res = sv_fh.plan(t_k, [sid])
    if res is not None:
        a_k, pl_k = res
        ev_k = dict(t=t_k, strings=[sid], **pl_k)
        sv_fh.commit(t_k, [sid], a_k, ev_k)
        run_evs.append(ev_k)
check("fingered 4-digit hand plays a 4-note sixteenth run in one window via look-ahead",
      len(run_evs) == 4 and all(e["window_lo"] == "fh00" for e in run_evs)
      and [e["finger"] for e in run_evs] == [2, 1, 3, 0],
      str([(e["strings"][0], e.get("window_lo"), e.get("finger")) for e in run_evs]))

# Splay to 4 gaps (fh00..fh04) covers up to 4 distinct strings when one inner string is skipped.
sv_sp = _Solver(fh)
sp_evs = []
for k, sid in enumerate(("fh00", "fh01", "fh02", "fh04")):
    t_k = 1.0 + k * 0.18
    res = sv_sp.plan(t_k, [sid])
    if res is not None:
        a_k, pl_k = res
        ev_k = dict(t=t_k, strings=[sid], **pl_k)
        sv_sp.commit(t_k, [sid], a_k, ev_k)
        sp_evs.append(ev_k)
check("4-digit hand splays across 4 gaps (fh00..fh04) when at most 4 strings are played",
      len(sp_evs) == 4 and all(e["window_lo"] == "fh00" for e in sp_evs)
      and [e["finger"] for e in sp_evs] == [0, 1, 2, 3],
      str([(e["strings"][0], e.get("window_lo"), e.get("finger")) for e in sp_evs]))

# Sibling yielding: arm0 (home fy03) plays fy03 at 1.0 s and rests on fy03..fy06;
# at 2.0 s arm1 (home fy08, reach fy04..fy09) needs fy05, and arm0 yields its resting window to fy00..fy03.
fy = Mechanism.build("fy", "plucked", "steel", [50+2*i for i in range(10)], arms=2, overlap=4, span=0.9,
        approach_s=0.20, recover_s=0.15, travel_s=0.02, hands=4)
fy.actuators[0].reach = [f"fy{i:02d}" for i in range(7)]
fy.actuators[0].home = "fy03"
fy.actuators[1].reach = [f"fy{i:02d}" for i in range(4, 10)]
fy.actuators[1].home = "fy08"
fy.arm_clearance = 0.05
sv_fy = _Solver(fy)
a0, p0 = sv_fy.plan(1.0, ["fy03"])
ev0 = dict(t=1.0, strings=["fy03"], **p0)
sv_fy.commit(1.0, ["fy03"], a0, ev0)
w0_before = ev0["window_lo"]
f_y = sv_fy._feasible(fy.actuators[1], 2.0, ["fy05"], 0.0)
check("sibling yielding: idle arm0 shifts its resting window (fy03 -> fy00) so arm1 can take fy05",
      w0_before == "fy03" and f_y is not None and isinstance(f_y[6], tuple)
      and f_y[6][0] == "fy_arm0" and f_y[6][1] == "fy00",
      f"w0_before={w0_before}, yield={f_y and f_y[6][:2]}")

# Scratch plan on The Chamber + The Clockwork Chamber with hands= on harp (4) and bars (2):
# verifies M6b gate (Ruler 25 Go thresholds, finalize() idempotence, Rig._segments parity).
from loam.rhythm import euclid, rotate, scale_notes
from loam import ruler
harp_m6 = Mechanism.build("harp", "plucked", "steel", scale_notes(50, "dorian", 3)[:16],
        arms=3, overlap=4, span=1.6, pos=[0.0, 0.0, 0.0],
        approach_s=0.20, recover_s=0.15, travel_s=0.02,
        pick_default=0.18, restrike_s=0.06, hands=4)
harp_m6.fan(width=0.34, power=1.0, by="index", smooth=2,
        rise=((0.66 - 2.05) / 3, (0.66 + 1.64 - 2.05) / 3))
harp_m6.arm_clearance = 0.05
rake_m6 = Mechanism.build("rake", "raked", "bronze", [50, 57, 62, 65, 69],
        arms=1, span=0.5, pos=[-1.4, 0.2, 0.3], arm_kind="rake",
        approach_s=0.15, recover_s=0.10, travel_s=0.0,
        pick_default=0.28, restrike_s=0.10)
rake_m6.fan(width=0.70, power=1.0, rise=((0.66 - 2.65) / 3, (0.66 + 1.36 - 2.65) / 3))
bars_m6 = Mechanism.build("bars", "struck", "rosewood", scale_notes(62, "dorian", 2)[:8],
        arms=2, overlap=2, span=0.9, pos=[1.5, -0.1, 0.4],
        arm_kind="mallet", approach_s=0.08, recover_s=0.04,
        travel_s=0.025, restrike_s=0.05, length_max=0.35, hands=2)
bars_m6.arm_clearance = 0.09
inst_m6 = Instrument("the chamber", [harp_m6, rake_m6, bars_m6])
sc_m6 = Score(Take(1.0, 0xC4A), "The Chamber", bpm=84.0, seed=0xC4A, instrument=inst_m6)
sc_m6._synth = lambda m_, s_, a_, pk_, d_, sd_: (np.zeros(1), (s_ and m_.string(s_).pick_default if pk_ is None else pk_) if m_.kind in ("plucked", "raked") else None, 0.1)
sc_m6._mix = lambda m_, t_, ch_: None
BEAT = 60.0 / 84.0
BAR = 4 * BEAT
def beat_t(bar, b=0.0): return bar * BAR + b * BEAT
H_m6 = [f"harp{i:02d}" for i in range(16)]
R_m6 = [f"rake{i:02d}" for i in range(5)]
B_m6 = [f"bars{i:02d}" for i in range(8)]
rng_m6 = np.random.default_rng(0xC4A)
intended_m6 = as_written_m6 = sub_m6 = drop_m6 = 0
def ask_pluck_m6(mech, t_, sid, amp, voice, alt=None, **kw):
    global intended_m6, as_written_m6, sub_m6, drop_m6
    intended_m6 += 1
    if sc_m6.can_play(mech, t_, sid) is not None:
        as_written_m6 += 1
        return sc_m6.pluck(mech, t_, sid, amp=amp, voice=voice, **kw)
    if alt is not None and sc_m6.can_play(mech, t_, alt) is not None:
        sub_m6 += 1
        return sc_m6.pluck(mech, t_, alt, amp=amp, voice=voice, **kw)
    drop_m6 += 1
    return None
def ask_rake_m6(t_, up=True, amp=0.8, voice="rake"):
    global intended_m6, as_written_m6, drop_m6
    ids_ = R_m6 if up else R_m6[::-1]
    on_ = mt.rake_onsets(up)
    spread_ = on_[-1] / (len(ids_) - 1)
    intended_m6 += 1
    if sc_m6.can_play("rake", t_, strings=ids_, spread_s=spread_) is None:
        drop_m6 += 1
        return None
    as_written_m6 += 1
    return sc_m6.rake("rake", t_, ids_, amp=amp, spread_s=spread_, onsets=on_, voice=voice, dur=2.6)
def pick_for_m6(amp): return float(np.clip(0.26 - 0.12 * amp, 0.10, 0.30))

for bar in range(0, 8):
    ask_pluck_m6("harp", beat_t(bar, 0), H_m6[0], 0.9, "ground", pick=0.14)
    ask_pluck_m6("harp", beat_t(bar, 2), H_m6[4], 0.7, "ground", pick=0.18)
    if bar >= 4:
        for k_, si in enumerate([12, 13, 14, 15]):
            ask_pluck_m6("harp", beat_t(bar, 3.0 + 0.25 * k_), H_m6[si],
                         0.45 + 0.08 * k_, "run", alt=H_m6[min(si + 1, 15)], pick=0.22)
    if bar >= 2:
        a_ = 0.6 + 0.1 * (bar % 2)
        ask_pluck_m6("harp", beat_t(bar, 1), H_m6[7], a_, "answer", alt=H_m6[6], pick=pick_for_m6(a_))
        ask_pluck_m6("harp", beat_t(bar, 3), H_m6[9 if bar % 2 else 11], a_, "answer", alt=H_m6[10], pick=pick_for_m6(a_))
ask_rake_m6(beat_t(7, 2), up=True, amp=0.9)
bass_pat = euclid(3, 8)
mel_pat = rotate(euclid(5, 8), 1)
bass_seq = [0, 2, 4]
motif = [7, 9, 11, 9, 12, 11, 9, 7, 8, 11, 13, 11]
mi = bi = 0
for bar in range(8, 16):
    for step in range(8):
        t_ = beat_t(bar, step * 0.5)
        if bass_pat[step]:
            si = bass_seq[bi % 3] + (3 if bar % 4 == 3 else 0)
            ask_pluck_m6("harp", t_, H_m6[si], 0.85, "bass", alt=H_m6[si + 1], pick=0.13)
            bi += 1
        if mel_pat[step]:
            si = motif[mi % len(motif)]
            a_ = 0.55 + 0.2 * (step == 0) + 0.1 * rng_m6.random()
            ask_pluck_m6("harp", t_, H_m6[si], a_, "line", alt=H_m6[si - 1], pick=pick_for_m6(a_))
            mi += 1
    if bar in (12, 14):
        ask_rake_m6(beat_t(bar), up=bar == 12, amp=0.85)
tune = [0, 2, 4, 5, 4, 2, 0, 3]
thin = rotate(euclid(3, 8), 2)
for bar in range(16, 24):
    for step in range(8):
        t_ = beat_t(bar, step * 0.5)
        if bass_pat[step]:
            si = bass_seq[(step // 3) % 3]
            ask_pluck_m6("harp", t_, H_m6[si], 0.8, "bass", alt=H_m6[si + 1], pick=0.13)
        if thin[step] and bar % 2 == 0:
            si = 9 + (step * 2) % 5
            ask_pluck_m6("harp", t_, H_m6[si], 0.5, "line", alt=H_m6[si + 1], pick=0.2)
        bi_ = min(tune[step] + (1 if bar % 4 == 2 else 0), 7)
        if bar % 4 != 3:
            ask_pluck_m6("bars", t_, B_m6[bi_], 0.6 + 0.25 * (step % 4 == 0), "mallets", alt=B_m6[max(bi_ - 1, 0)])
    if bar % 4 == 3:
        for k_ in range(8):
            ask_pluck_m6("bars", beat_t(bar, 0.5 * k_), B_m6[k_], 0.5 + 0.05 * k_, "run", alt=B_m6[min(k_ + 1, 7)])
    ask_rake_m6(beat_t(bar, 0), up=True, amp=0.75)
    ask_rake_m6(beat_t(bar, 2), up=False, amp=0.65)
ask_rake_m6(beat_t(24), up=False, amp=0.8)
ask_pluck_m6("harp", beat_t(24), H_m6[0], 0.9, "ground", pick=0.14)
for bar, (b0, b1) in zip((25, 26), ((0, 4), (7, 3))):
    ask_pluck_m6("bars", beat_t(bar, 0), B_m6[b0], 0.7, "mallets")
    ask_pluck_m6("bars", beat_t(bar, 2), B_m6[b1], 0.55, "mallets")
    ask_pluck_m6("harp", beat_t(bar, 1), H_m6[14 - (bar - 25) * 2], 0.5, "answer", pick=0.22)
ask_rake_m6(beat_t(27, 0), up=True, amp=0.85)
for si in (0, 7, 14):
    ask_pluck_m6("harp", beat_t(27, 2), H_m6[si], 0.95, "chord", pick=0.12)

st1 = sc_m6.finalize()
chk1 = ruler.plan_consistent(sc_m6.events)
snap1 = [dict(e) for e in sc_m6.events]
st2 = sc_m6.finalize()
check("M6b scratch plan (Ruler 25 Go): 237/239 >= 228 as written, 0 <= 6 drops, 2/241 refusals, plan_consistent ok",
      intended_m6 == 239 and as_written_m6 == 237 and sub_m6 == 2 and drop_m6 == 0
      and len(sc_m6.events) == 239 and st1["refused"] == 2 and chk1["ok"] and not sc_m6.conflicts,
      f"as_written={as_written_m6}/{intended_m6}, sub={sub_m6}, drop={drop_m6}, refused={st1['refused']}/{st1['asked']}, conflicts={len(sc_m6.conflicts)}")
check("M6b finalize() is idempotent (clockwork round-trip preserves finger, window_lo, t_move)",
      st2["reassigned"] == 0 and all(
          e.get(k) == old.get(k)
          for e, old in zip(sc_m6.events, snap1)
          for k in ("t", "strings", "onsets", "actuator", "t_move", "t_free", "t_head_free", "pick", "finger", "window_lo")
      ))

# Check Rig._segments parity on the M6b scratch plan against layout.json
import json as _json
lay_m6 = _json.loads(open(os.path.join(os.path.dirname(__file__), "..", "render/form-study/layout.json")).read())
lay_m6["mechanisms"]["harp"]["arm_clearance_m"] = harp_m6.arm_clearance * mt.WORLD_SCALE
doc_m6 = dict(total_s=86.0, instrument=inst_m6.to_dict(), events=sc_m6.events, cues=sc_m6.cues)
rig_m6 = _rig.Rig(doc_m6, lay_m6)
harp_moves = sum(1 for aid in ("harp_arm0", "harp_arm1", "harp_arm2") for s_ in rig_m6.sched[aid] if s_["moving"])
bars_hurried = sum(1 for aid in ("bars_arm0", "bars_arm1") for s_ in rig_m6.sched[aid]
                   if s_["moving"] and mt.hurried("mallet", abs(s_["xb"] - s_["xa"]), s_["arrive"] - s_["go"]))
check("M6b Rig._segments mirrors fingered _Solver: 0 pushed starts, harp moves <= 50, bars hurried <= 6",
      rig_m6.pushed == [] and harp_moves <= 50 and bars_hurried == 0,
      f"pushed={rig_m6.pushed}, harp_moves={harp_moves}, bars_hurried={bars_hurried}")

print("SCORE PLAN: " + ("PASS" if not fails else "FAIL " + str(fails)))
sys.exit(1 if fails else 0)

"""Ruler for the pick's servo stroke as the Rig plays it (PLAYERS M2, "servo
anticipation"; formlab/servo.py driven by formlab/rig.py).

    python3 tools/test_servo.py                       # both built assets
    python3 tools/test_servo.py LAYOUT.json SCORE.json

formlab/servo.py plans a pick arm's path in closed form, on the surface
formlab/stroke.py gives a mallet. This holds it and the Rig to the contract:

  - the S-curve as declared polynomial pieces is rig.scurve exactly, C2, with
    the closed-form peaks SCURVE_V / SCURVE_A / SCURVE_J the declared jerk uses;
  - the declared functions (v_in, t_down, prep) and their bounds: a phrase
    action is never under ruler 4's pluck approach floor (2.5 frames);
  - Rig.stroke plans every pick arm (a ServoStroke, no issues), path_at is
    its p(t), and Rig.declared is its own: native, no rings, the servo prep,
    each channel covering (-inf, inf), laws from servo.LAWS (all in
    segments.LAWS), tags from segments.TAGS, a head hold's kind from
    segments.HOLD_KINDS, every moving segment's declared jerk bounding the
    sampled one;
  - each contact: reached at the scored time and point, a declared 'contact'
    knot whose dv is v+ - v- exactly (-v_in n in, +V_REL n out); C2 at every
    'smooth' knot;
  - a poised stroke: the poise is a declared head hold [t - POISE[0], t -
    POISE[1]] at H_APEX ending at t_apex, the carriage at rest on the contact
    from the poise on (never the score's arrive: PLAYERS M2 round 3), and the
    TOOL still over it (D7: |v| <= STILL_V on a 1 ms grid); a phrase stroke:
    no hold, |a| >= 0.5 g at its apex, T_down in T_DOWN;
  - every pick travel within the servo carriage's limits (SERVO_V_MAX at its
    peak, motion_timing.SERVO_A_MAX_G), unless the score leaves it none: a
    hurried travel run over exactly the score's [go, arrive] (the M7 run's
    39 ms hops); the distribution is printed;
  - the carriage on the contact from the score's arrive to the contact (the
    action may start before arrive, on the head alone), and never moving
    while the pick is within OFF_STRING of the string plane;
  - repeat (ruler 22): two notes with the same (IOI, a', next IOI, next a')
    move the head relative to the carriage identically;
  - the rail key hashes servo.py and every servo constant.

The rake (T5, formlab/rake.py) is held to the same surface and its own plan:
  - its closed forms (the clamped sweep cubic, the rail run, the exact head
    jerk) and its library (formlab/rake_pieces.json: y and h share knots,
    every backswing names a run-up, the homing poses, the fingerprint fits);
  - Rig.stroke plans it (a RakeStroke, no issues: no piece fell back), path_at
    is its p(t), Rig.declared is its own (native, no rings, no prep), laws
    from rake.LAWS, every hermite and 3-4-5 head segment declares its h and
    hy boundary data, the declared jerk bounds the sampled one;
  - every string reached at its own onset (motion_timing.string_times) on
    the string plane, C2 at every smooth knot, the comb never behind the
    string plane, x inside the rail (A19: reach_x -+ rake.OVER), the homing
    sweep's legs land, every pendulum turn at one end is the same path;
  - the plan reads no arm cfg (another root and links plan the same stroke),
    and the rail plan's cfg reaches it (evaluate_arm, the search's accept
    rule, takes the path);
  - the shared M2 definitions: D1 follow-through >= 0.2 m at every exit, D2
    entry >= 0.7 v_sweep over the last frame, D3 |a| <= 10 g off the rolls,
    D4 frame turns <= 30 deg near them, D5 every announced roll's backswing
    >= 0.5 s and poise hold >= rake.HOLD_MIN; and round 3's: D7 every
    announced apex hold holds the tool still, D9 from every exit's turn (D1's
    t_rev) to the comb's rest the in-plane coordinate along the release never
    gives back more than RETURN_TOL, with h rising or holding. The sense is
    ruler 24's, row for row (A27, the lead's L4): along +t_out (string plane)
    after an up exit and at every rest that is not a listed phrase end; along
    -t_out after a DOWN exit at a listed end, where D1's follow-through runs
    down the strings and 24's upward release must climb back. Both numbers
    are printed per rest; the literal +t_out one there is info;
  - the rail key hashes rake.py, rake_pieces.json and every rake constant,
    and REACH_FRAC (the search's accept rule).
"""
import json, math, sys
from pathlib import Path
import numpy as np
ROOT = Path(__file__).resolve().parents[1]
for p in (str(ROOT), str(ROOT/'tools')):
    if p not in sys.path: sys.path.insert(0, p)
from formlab import rig as R
from formlab import servo as SV
from formlab import rake as RK
from formlab import segments as SEG
from formlab import layout_search as LS
from formlab.rig import Rig

FRAME = 1/30          # the film's frame (tools/players/core.FPS)
G = 9.81
TOL_P = 1e-9          # m: a contact reached, a channel's join continuous
TOL_C2 = 1e-6         # relative: v and a continuous at a 'smooth' knot
REPEAT_N = 241        # samples a repeat window is compared on
SLIVER_S = 1e-3       # s: the shortest finite rake segment (a tag cut on, or well off, a piece knot)
OFF_STRING = .02      # m: the pick is at least this far off the string plane whenever the carriage moves (no sideways drag)
# PLAYERS M2 round 3, the shared definitions D7 and D9 (docs/motion-design.md; the rulers track holds them in 14 / 22 / 24)
STILL_V = .020        # m/s: D7, the tool's |v| over every pick poise and announced rake apex hold (a still hold reads 0)
STILL_DT = 1e-3       # s: D7's sample step, both ends included
RETURN_TOL = 1e-6     # m: D9, a rest's give-back along its release (ruler 24's h tolerance, r_strings.RETURN_TOL)
REL_ANG = 45.0        # deg: ruler 24's 'upward' (r_strings.REL_ANG): why a down exit's listed release is judged along -t_out
RAKE_ENDS = (68.57, 77.14)  # s: the goal's listed rake phrase ends (r_strings.RAKE_ENDS): 24 wants an upward release there
END_TOL = .015        # s: a roll is a listed end within this (r_strings.TIME_TOL: the goal quotes times to 2 decimals)
MT = SV.motion_timing

failures = []
def check(ok, msg):
    print(('  PASS ' if ok else '  FAIL ')+msg)
    if not ok: failures.append(msg)

def scurve_unit():
    """The declared S-curve pieces against rig.scurve and the closed-form peaks."""
    T = .7; P0 = np.array([.1, 1.2, -.3]); P1 = np.array([.45, 1.1, -.25]); D = P1-P0
    s = SV.ScurveSeg(2.0, 2.0+T, P0, P1, 'travel')
    tt = np.linspace(2.0, 2.0+T, 1401)
    ref = np.array([P0+D*R.scurve((t-2.0)/T) for t in tt])
    err = float(np.abs(s.point(tt)-ref).max())
    check(err < 1e-12, f'ScurveSeg is rig.scurve on all three axes (worst {err:.1e} m)')
    cuts = (2.0+SV.SCURVE_RAMP*T, 2.0+T-SV.SCURVE_RAMP*T); jump = 0.0
    for c in cuts:
        for d in (0, 1, 2):
            for k in range(3):
                a = [g for g in s.pieces[k] if abs(g.t1-c) < 1e-12][0]; b = [g for g in s.pieces[k] if abs(g.t0-c) < 1e-12][0]
                jump = max(jump, abs(float(a.ev(np.array([c]), d)[0])-float(b.ev(np.array([c]), d)[0])))
    ends = max(float(np.abs(s.point(np.array([t]), d)).max()) for t in (2.0, 2.0+T) for d in (1, 2))
    check(jump < 1e-9 and ends < 1e-12, f'C2 at the ramp ends (worst jump {jump:.1e}), rest to rest (|v|, |a| {ends:.1e} at the ends)')
    L = float(np.linalg.norm(D)); u = np.linspace(2.0, 2.0+T, 20001)
    pk = [float(np.linalg.norm(s.point(u, d), axis=-1).max()) for d in (1, 2, 3)]
    want = [SV.SCURVE_V*L/T, SV.SCURVE_A*L/T**2, SV.SCURVE_J*L/T**3]
    check(all(abs(a-b) <= 2e-3*b for a, b in zip(pk, want)),
          f'peaks |v| {pk[0]:.4f} |a| {pk[1]:.3f} |j| {pk[2]:.2f} are SCURVE_V/A/J L/T^n ({want[0]:.4f}, {want[1]:.3f}, {want[2]:.2f})')

def functions():
    """The declared functions and the bounds they promise."""
    ok = SV.t_down(math.inf) == SV.POISE[1] and SV.t_down(2.0) == SV.POISE[1]
    ok &= all(2.5*FRAME <= SV.t_down(i) <= SV.T_DOWN[1] for i in np.linspace(.05, .999, 200))
    check(ok and SV.T_DOWN[0] >= 2.5*FRAME, f't_down: poised {SV.POISE[1]} s; a phrase in [{SV.T_DOWN[0]}, {SV.T_DOWN[1]}] '
          f'(ruler 4: a pluck approach >= 2.5 frames = {2.5*FRAME:.4f} s)')
    check(SV.prep(None, math.inf) == SV.H_APEX and SV.prep(.3, .5) <= SV.H_PHRASE and SV.prep(0.0, 2.0) == SV.prep(1.0, 2.0),
          f'prep: poised H_APEX {SV.H_APEX} m whatever a\'; a phrase <= H_PHRASE {SV.H_PHRASE} m')
    check(SV.v_in(None) == SV.v_in(1.0) and SV.v_in(0.0) < SV.v_in(1.0) and SV.v_in(0.0) > 0,
          f'v_in rises with a\': {SV.v_in(0.0)} .. {SV.v_in(1.0)} m/s')
    check(set(SV.LAWS) <= set(SEG.LAWS) and {'hover', 'poise'} <= set(SEG.HOLD_KINDS),
          'servo.LAWS are segments.LAWS; its hold kinds are segments.HOLD_KINDS')

def rail_key():
    check('servo.py' in LS.GEOMETRY_SOURCES, 'the rail key hashes formlab/servo.py')
    consts = LS.motion_constants()
    names = {k for k in dir(SV) if k.isupper() and isinstance(getattr(SV, k), (int, float, dict, list, tuple))}
    check({'servo.'+k for k in names} <= set(consts) and abs(consts['SCURVE_RAMP']-SV.SCURVE_RAMP) == 0,
          f'motion_constants() carries every servo constant, prefixed ({len(names)}), and rig.SCURVE_RAMP is servo\'s')

def _close(a, b, tol): return float(np.max(np.abs(np.asarray(a)-np.asarray(b)))) <= tol

def contract(rig, aid):
    st = rig.stroke(aid); D = rig.declared(aid); N = st.notes; n = st.n
    check(isinstance(st, SV.ServoStroke) and not st.issues, f'{aid}: a ServoStroke with no issues ({len(st.issues)}'
          +''.join(f"; {i['what']} at {i['t']:.3f} s" for i in st.issues[:4])+')')
    check(D.native and D.rings == [] and all(abs(D.prep(x.a_raw, x.ioi)-x.h) <= 1e-12 for x in N),
          f'{aid}: declared natively, no rings, with servo.prep the apex every note was planned to')
    ok = True; msg = []
    for ch in ('head', 'carriage'):
        cs = sorted([g for g in D.segments if g.extra.get('channel') == ch], key=lambda g: g.t0)
        ok &= cs[0].t0 == -np.inf and cs[-1].t1 == np.inf and all(a.t1 == b.t0 and b.t1 > b.t0 for a, b in zip(cs, cs[1:]))
        msg.append(f'{ch} {len(cs)}')
    check(ok, f'{aid}: each channel covers (-inf, inf) with no hole and no overlap ({", ".join(msg)} segments)')
    laws = {g.law for g in D.segments}; tags = {g.tag for g in D.segments}
    holds = {g.extra.get('hold') for g in D.segments if g.extra['channel'] == 'head' and g.law == 'hold'}
    herm = all(all(k in g.extra for k in ('p0', 'v0', 'a0', 'p1', 'v1', 'a1')) for g in D.segments if g.law == 'quintic hermite')
    check(laws <= set(SV.LAWS) and tags <= set(SEG.TAGS) and holds <= set(SEG.HOLD_KINDS) and herm,
          f'{aid}: laws {sorted(laws)}, tags {sorted(tags)}, holds {sorted(holds)}; every hermite carries p0..a1')
    # the declared jerk bounds the sampled one, segment by segment
    worst = 0.0
    for g in st.head.segs+st.carriage.segs:
        if g.law == 'hold' or not math.isfinite(g.t1-g.t0): continue
        u = np.linspace(g.t0, g.t1, 401)[1:-1]
        j = np.abs(st.h(u, 3)) if g.channel == 'head' else np.linalg.norm(st.car(u, 3), axis=-1)
        worst = max(worst, float(j.max())/max(g.extra['jerk'], 1e-12))
    check(worst <= 1.0+1e-6, f'{aid}: every moving segment\'s declared jerk bounds its sampled jerk (worst ratio {worst:.6f})')
    # path_at is the stroke
    tt = np.linspace(-1.0, float(rig.score['total_s']), 997)
    err = max(float(np.abs(rig.path_at(aid, float(t))-st.p(float(t))).max()) for t in tt)
    check(err == 0.0, f'{aid}: path_at is the servo stroke\'s p(t) (worst {err:.1e} m)')
    # the contacts
    sched = rig.sched[aid]; ck = [k for k in st.knots if k.kind == 'contact']
    reach = max(float(np.abs(st.p(s['hit'])-np.asarray(s['first'])).max()) for s in sched)
    tm = all(k.t == s['hit'] for k, s in zip(ck, sched)) and len(ck) == len(sched)
    dv = max(float(np.abs(st.v(k.t, +1)-st.v(k.t, -1)-k.dv).max()) for k in ck)
    vio = max(float(np.abs(st.v(x.t, -1)+x.v_in*n).max()+np.abs(st.v(x.t, +1)-SV.V_REL*n).max()) for x in N)
    check(reach <= TOL_P and tm and dv <= 1e-9 and vio <= 1e-9,
          f'{aid}: each contact reached at its scored time and point ({reach:.1e} m), a contact knot with dv = v+ - v- '
          f'({dv:.1e}), in at -v_in n and out at +V_REL n ({vio:.1e})')
    jumps = [0.0, 0.0, 0.0]
    for k in st.knots:
        if k.kind != 'smooth': continue
        for d, f in enumerate((st.p, st.v, st.a)):
            l, r = f(k.t, -1), f(k.t, +1)
            jumps[d] = max(jumps[d], float(np.abs(l-r).max())/(1.0 if d == 0 else 1.0+float(np.abs(l).max())))
    check(jumps[0] <= TOL_P and max(jumps[1:]) <= TOL_C2,
          f'{aid}: C2 at every smooth knot (p {jumps[0]:.1e} m, v and a {max(jumps[1:]):.1e} relative)')
    # poised and phrase strokes
    pz = [x for x in N if x.style == 'poised']; ph = [x for x in N if x.style == 'phrase']; bad = []
    for x in pz:
        g = st.head.segs[int(st.head.index(np.array([x.t-SV.POISE[0]+1e-9]))[0])]
        if not (g.law == 'hold' and g.extra.get('hold') == 'poise' and abs(g.t0-(x.t-SV.POISE[0])) <= 1e-12
                and abs(g.t1-x.t_apex) <= 1e-12 and abs(x.t_apex-(x.t-SV.POISE[1])) <= 1e-12 and abs(float(g.c[0])-SV.H_APEX) <= 1e-12):
            bad.append(('poise', x.t))
        tb = x.travel_window[1] if x.travel is not None else -math.inf
        if not tb <= x.hold[0]+1e-12: bad.append(('travel', x.t))
    check(not bad, f'{aid}: every poised stroke ({len(pz)}) poises at H_APEX over [t - {SV.POISE[0]}, t - {SV.POISE[1]}] = t_apex, '
          f'its travel done by the poise {bad[:3]}')
    # D7: the poise holds the TOOL still, the carriage with it (round 2's CAR_MIN let harp_arm1's 45.0 and harp_arm2's
    # 44.29 slide through theirs at 561 and 1098 mm/s under a held head; the head alone read still)
    d7 = sorted((still_v(st, *x.hold), x.t) for x in pz)
    check(not d7 or d7[-1][0] <= STILL_V, f'{aid}: D7 every poise ({len(d7)}) holds the tool still: max |v| '
          f'{d7[-1][0]*1e3 if d7 else 0:.3f} mm/s (<= {STILL_V*1e3:g} mm/s, {STILL_DT*1e3:g} ms grid)'
          +''.join(f'; {t:.3f} s {v*1e3:.1f} mm/s' for v, t in d7 if v > STILL_V)[:240])
    cap(st, aid)
    bad = []
    for x in ph:
        g0 = st.head.segs[int(st.head.index(np.array([x.t-1e-9]))[0])]
        holds = [g for g in st.head.segs if g.law == 'hold' and g.t0 < x.t and g.t1 > x.t-x.ioi]
        aa = abs(float(st.h(np.array([x.t_apex]), 2)[0]))
        if holds or aa < .5*G or not (SV.T_DOWN[0] <= x.T_down <= SV.T_DOWN[1]) or g0.tag != 'stroke': bad.append(x.t)
    check(not bad, f'{aid}: every phrase stroke ({len(ph)}) is continuous (no hold), turns at >= 0.5 g at its apex, '
          f'acts over T_DOWN {bad[:3]}')
    # the carriage stands on the contact from the score's arrive (the head alone acts before it)
    worst = 0.0; early = 0
    for x, s in zip(N, sched):
        u = np.linspace(x.arrive, x.t, 31)
        worst = max(worst, float(np.abs(st.car(u)-np.asarray(s['first'])).max()))
        early += int(x.t-x.T_down < x.arrive-1e-12)
    check(worst <= TOL_P, f'{aid}: the carriage is on the contact from arrive to the contact (worst {worst:.1e} m); '
          f'{early} actions start before arrive, on the head alone')
    low = min((float(st.h(np.linspace(g.t0, g.t1, 401)[1:-1]).min()), g.t0) for g in st.carriage.segs if g.law == 'scurve')
    check(low[0] >= OFF_STRING, f'{aid}: the carriage moves only with the pick off the strings (lowest {low[0]*1e3:.1f} mm '
          f'above the plane, travel at {low[1]:.3f} s; >= {OFF_STRING*1e3:.0f} mm)')
    # repeat: the head relative to the carriage is a function of (IOI, a', next IOI, next a')
    groups = {}
    for i, x in enumerate(N):
        nx = N[i+1] if i+1 < len(N) else None
        key = (round(x.ioi, 6), x.a, round(nx.ioi, 6) if nx else None, nx.a if nx else None)
        groups.setdefault(key, []).append(x)
    worst = 0.0; pairs = 0
    for key, xs in groups.items():
        if len(xs) < 2: continue
        x0 = xs[0]
        lo = -min(x0.L, x0.ioi if math.isfinite(x0.ioi) else x0.L); hi = min(x0.ioi_next, SV.T_REL) if math.isfinite(x0.ioi_next) else SV.T_REL
        u = np.linspace(lo, hi, REPEAT_N)
        ref = st.p(x0.t+u)-st.car(x0.t+u)
        for x in xs[1:]:
            worst = max(worst, float(np.abs(st.p(x.t+u)-st.car(x.t+u)-ref).max())); pairs += 1
    check(worst <= 1e-9, f'{aid}: repeat: the head relative to the carriage is the same for the same '
          f"(IOI, a', next IOI, next a') ({pairs} pairs, worst {worst:.1e} m)")

def still_v(st, t0, t1):
    """D7: the tool's largest |v| over [t0, t1], the closed form every STILL_DT, both ends included."""
    t = np.unique(np.r_[np.arange(t0, t1, STILL_DT), t1])
    return float(np.linalg.norm(st.v(t), axis=-1).max())

def cap(st, aid):
    """The servo carriage's limits on every pick travel (the goal's 'Plausible': a servo carriage at <= SERVO_V_MAX
    and <= 3 g, motion_timing.SERVO_A_MAX_G): its S-curve's closed-form peaks, along x (the rail) and in 3-D (the
    arm's y/z with it). A travel over them must be one the score leaves no choice: hurried, over exactly [go, arrive]."""
    amax = MT.SERVO_A_MAX_G*MT.G; rows = []; bad = []; forced = []
    for x in st.notes:
        if x.travel is None: continue
        tr = st.travels[x.travel]; T = tr['t1']-tr['t0']; D = np.asarray(tr['P1'])-np.asarray(tr['P0'])
        L, dx = float(np.linalg.norm(D)), abs(float(D[0]))
        a, v = SV.SCURVE_A*L/T**2, SV.SCURVE_V*L/T; rows.append((SV.SCURVE_A*dx/T**2/MT.G, a/MT.G, x.style, x.hurried))
        if a <= amax*(1+1e-9) and v <= MT.SERVO_V_MAX*(1+1e-9): continue
        scored = abs(tr['t0']-x.go) <= 1e-9 and abs(tr['t1']-x.arrive) <= 1e-9
        (forced if x.hurried and scored else bad).append((round(x.t, 3), round(a/MT.G, 2), round(v, 3)))
    ax = np.array([r[0] for r in rows]); a3 = np.array([r[1] for r in rows])
    by = lambda st_, hu: [r[1] for r in rows if r[2] == st_ and r[3] == hu]
    dist = '; '.join(f'{s_}{" hurried" if hu else ""} {len(by(s_, hu))} max {max(by(s_, hu)):.3f} g' for s_ in ('poised', 'phrase')
                     for hu in (False, True) if by(s_, hu))
    check(not bad, f'{aid}: every travel the stroke times keeps the servo carriage\'s limits (<= {MT.SERVO_V_MAX:g} m/s, '
          f'<= {MT.SERVO_A_MAX_G:g} g): {len(rows)} travels, peak |x\'\'| max {ax.max():.3f} g p90 {np.percentile(ax, 90):.3f} '
          f'median {np.median(ax):.3f}, 3-D {dist}'+(f'; over: {bad[:4]}' if bad else '')
          +(f'; {len(forced)} hurried over the score\'s own [go, arrive] (the score\'s, not the stroke\'s: worst '
            f'{max(f[1] for f in forced):.2f} g, {max(f[2] for f in forced):.2f} m/s)' if forced else ''))

# ---- the rake (PLAYERS M2, T5: formlab/rake.py) -------------------------------------------------
JERK_SAMPLES = 200001   # samples the exact head jerk is checked against
def rake_unit():
    """formlab/rake.py's closed forms and its library."""
    f = lambda u: 1+2*u-u*u+.5*u**3; fv = lambda u: 2-2*u+1.5*u*u; fa = lambda u: -2+3*u
    u = np.array([0, .2, .5, .7, 1.1]); S = RK.clamped(u, f(u), fv(0.0), fv(1.1))
    err = max(float(np.abs(S[:, 0]-f(u)).max()), float(np.abs(S[:, 1]-fv(u)).max()), float(np.abs(S[:, 2]-fa(u)).max()))
    check(err < 1e-12, f'rake.clamped is exact on a cubic (knot states p, v, a: worst {err:.1e})')
    x0, v0, a0, stop = -4.725, -.639, 25.59, -4.7396
    D, pk = RK.run_d(x0, v0, a0, stop); c = R.stroke.law_hermite(x0, v0, a0, stop, 0.0, 0.0, D); tau = np.linspace(0, D, 4001)
    v = R.stroke._horner(R.stroke._dcoef(c, 1), tau); a = R.stroke._horner(R.stroke._dcoef(c, 2), tau)
    check(RK.RUN_D[0] <= D < RK.RUN_D[1] and np.all(v*np.sign(v0) >= -1e-9) and abs(float(np.abs(a).max())-pk) <= 1e-6*pk,
          f'rake.run_d: a run-out of {D:.4f} s never runs back past its stop, peak |x\'\'| {pk/G:.3f} g')
    rng = np.random.default_rng(5); T = .3; n = np.array([0.0, .6, -.8]); worst = 0.0
    for _ in range(5):
        ch = R.stroke.law_hermite(*rng.normal(size=6), T); cy = R.stroke.law_hermite(*rng.normal(size=6), T)
        t = np.linspace(0, T, JERK_SAMPLES); h3 = R.stroke._horner(R.stroke._dcoef(ch, 3), t); y3 = R.stroke._horner(R.stroke._dcoef(cy, 3), t)
        dense = float(np.sqrt((h3*n[0])**2+(h3*n[1]+y3)**2+(h3*n[2])**2).max()); ex = RK.head_jerk(ch, cy, T, n)
        worst = max(worst, abs(ex-dense)/dense)
    check(worst <= 1e-6, f'rake.head_jerk is the exact peak |p\'\'\'| of h n + (0, h_y, 0) (worst {worst:.1e} relative to {JERK_SAMPLES} samples)')
    lib = RK.library()
    ok = lib is not None and all(pc['y']['K'] == pc['h']['K'] for pc in lib['pieces'].values()) \
        and all(pc.get('next', next(iter(lib['pieces']))) in lib['pieces'] for pc in lib['pieces'].values()) \
        and set(lib.get('homing', {})) == set(R.motion_timing.HOME_JOINTS)
    check(ok, f'the library ({RK.LIB}): {len(lib["pieces"]) if lib else 0} pieces, y and h on one knot set, every backswing '
          f'names its run-up, homing poses for {sorted(lib["homing"]) if lib else []}')
    check(set(RK.LAWS) <= set(SEG.LAWS) and {'hover', 'poise', 'park'} <= set(SEG.HOLD_KINDS),
          'rake.LAWS are segments.LAWS; its hold kinds are segments.HOLD_KINDS')

def rake_rail_key():
    check({'rake.py', 'rake_pieces.json'} <= set(LS.GEOMETRY_SOURCES), 'the rail key hashes formlab/rake.py and rake_pieces.json')
    consts = LS.motion_constants()
    names = {k for k in dir(RK) if k.isupper() and isinstance(getattr(RK, k), (int, float, dict, list, tuple))}
    check({'rake.'+k for k in names} <= set(consts), f'motion_constants() carries every rake constant, prefixed ({len(names)})')

def rake_contract(rig, aid):
    st = rig.stroke(aid); D = rig.declared(aid); N = st.notes; g = RK.Geometry(st.arm)
    check(isinstance(st, RK.RakeStroke) and isinstance(st, SV.ServoStroke) and not st.issues,
          f'{aid}: a RakeStroke with no issues ({len(st.issues)}'+''.join(f"; {i['what']} at {i['t']:.3f} s" for i in st.issues[:4])+')')
    check(D.native and D.rings == [] and D.prep is None and st.prep is None,
          f'{aid}: declared natively, no rings, no prep function (its apex follows the gap\'s kind)')
    ok = True; msg = []
    for ch in ('head', 'carriage'):
        cs = sorted([s for s in D.segments if s.extra.get('channel') == ch], key=lambda s: s.t0)
        ok &= cs[0].t0 == -np.inf and cs[-1].t1 == np.inf and all(a.t1 == b.t0 and b.t1 > b.t0 for a, b in zip(cs, cs[1:]))
        msg.append(f'{ch} {len(cs)}')
    check(ok, f'{aid}: each channel covers (-inf, inf) with no hole and no overlap ({", ".join(msg)} segments)')
    laws = {s.law for s in D.segments}; tags = {s.tag for s in D.segments}
    holds = {s.extra.get('hold') for s in D.segments if s.extra['channel'] == 'head' and s.law == 'hold'}
    keys = {'quintic hermite': ('p0', 'v0', 'a0', 'p1', 'v1', 'a1'), '3-4-5': ('p0', 'p1')}
    data = all(all(k in s.extra for k in keys[s.law]) and (s.extra['channel'] == 'carriage' or all(k in s.extra['hy'] for k in keys[s.law]))
               for s in D.segments if s.law in keys)
    homes = sum(1 for s in D.segments if s.tag == 'home')
    check(laws <= set(RK.LAWS) and tags <= set(SEG.TAGS) and holds <= set(SEG.HOLD_KINDS) and data and homes,
          f'{aid}: laws {sorted(laws)}, tags {sorted(tags)}, holds {sorted(holds)}; every hermite and 3-4-5 declares its '
          f'boundary data (the head\'s h and hy); {homes} homing legs declared')
    worst = 0.0
    for s in st.head.segs+st.carriage.segs:
        if s.law == 'hold' or not math.isfinite(s.t1-s.t0): continue
        u = np.linspace(s.t0, s.t1, 401)[1:-1]
        j = np.linalg.norm(st.j(u)-st.car(u, 3), axis=-1) if s.channel == 'head' else np.linalg.norm(st.car(u, 3), axis=-1)
        worst = max(worst, float(j.max())/max(s.extra['jerk'], 1e-12))
    check(worst <= 1.0+1e-9, f'{aid}: every moving segment\'s declared jerk bounds its sampled jerk (worst ratio {worst:.6f})')
    # no sliver: a tag cut a few us off a piece's knot leaves a segment whose boundary data
    # ruler 6c rebuilds ill-conditioned (the ghost's 'ghost' cut sat 3.2 us past a knot)
    short = min((s for s in st.head.segs+st.carriage.segs if math.isfinite(s.t1-s.t0)), key=lambda s: s.t1-s.t0)
    check(short.t1-short.t0 >= SLIVER_S, f'{aid}: every finite segment lasts >= {SLIVER_S*1e3:g} ms '
          f'(shortest {(short.t1-short.t0)*1e3:.3f} ms, {short.channel} {short.tag} at {short.t0:.3f} s)')
    tt = np.linspace(-1.0, float(rig.score['total_s']), 997)
    err = max(float(np.abs(rig.path_at(aid, float(t))-st.p(float(t))).max()) for t in tt)
    check(err == 0.0, f'{aid}: path_at is the rake stroke\'s p(t) (worst {err:.1e} m)')
    worst = 0.0
    for s in rig.sched[aid]:
        e = s['event']
        for sid, t in zip(e['strings'], R.motion_timing.string_times(e)):
            worst = max(worst, float(np.abs(st.p(t)-rig.contact(sid, e.get('pick'))).max()))
    check(worst <= TOL_P, f'{aid}: every string of every roll reached at its own onset on its contact (worst {worst:.1e} m)')
    jumps = [0.0, 0.0, 0.0]
    for k in st.knots:
        for d, f in enumerate((st.p, st.v, st.a)):
            l, r = f(k.t, -1), f(k.t, +1)
            jumps[d] = max(jumps[d], float(np.abs(l-r).max())/(1.0 if d == 0 else 1.0+float(np.abs(l).max())))
    check(not [k for k in st.knots if k.kind != 'smooth'] and jumps[0] <= TOL_P and max(jumps[1:]) <= TOL_C2,
          f'{aid}: every knot smooth, C2 ({len(st.knots)} knots: p {jumps[0]:.1e} m, v and a {max(jumps[1:]):.1e} relative)')
    u = np.arange(-1.0, float(rig.score['total_s']), 1e-4); h = st.h(u); x = st.x(u)
    ends = [st.x(np.array([s.t0, s.t1]))[0] for s in st.carriage.segs if math.isfinite(s.t0) and math.isfinite(s.t1)]
    lo, hi = min(float(x.min()), min(ends)), max(float(x.max()), max(ends)); rlo, rhi = g.reach
    check(float(h.min()) >= -1e-9 and g.x_lo <= lo and hi <= g.x_hi,
          f'{aid}: the comb never behind the string plane (h >= {float(h.min()):.1e} m); x in [{lo:.6f}, {hi:.6f}], the rail '
          f'reach_x -+ OVER {RK.OVER*1e3:.4f} mm (runs {(rlo-lo)*1e3:.4f} / {(hi-rhi)*1e3:.4f} mm past reach_x)')
    hm = rig.homes(aid); land = [0.0]
    if hm: land = [float(np.abs(st.p(hm[0][1])-(np.asarray(st.arm.home)+np.asarray(st.arm.hover))).max())]
    check(bool(hm) and land[0] <= TOL_P, f'{aid}: the homing sweep ({len(hm[0][4]) if hm else 0} legs) lands on the hover over home ({land[0]:.1e} m)')
    worst = 0.0; turns = {}
    for k, x_ in enumerate(N[:-1]):
        if x_.leave == 'turn': turns.setdefault(x_.up, []).append(x_)
    for up, xs in turns.items():
        T_ = xs[0].gap_next; uu = np.linspace(0, T_, REPEAT_N); ref = st.p(xs[0].t_end+uu)-st.car(xs[0].t_end+uu)
        for x_ in xs[1:]: worst = max(worst, float(np.abs(st.p(x_.t_end+uu)-st.car(x_.t_end+uu)-ref).max()))
    check(turns and worst <= 1e-9, f'{aid}: every pendulum turn at one end is one path relative to the carriage '
          f'({sum(len(v) for v in turns.values())} turns, worst {worst:.1e} m)')
    # the pieces read no arm cfg (tools/rake_design.py designs them in tool space): the plan under another
    # root and other links is the same stroke, so the rail plan can choose them after the motion
    cfg = rig.geometry['arms'][aid]; old = dict(cfg); total = float(rig.score['total_s'])
    try:
        cfg.update(root_y=float(cfg['root_y'])+.37, root_z=float(cfg['root_z'])-.21, l1=float(cfg['l1'])+.2, l2=float(cfg['l2'])+.1)
        alt = RK.plan_rake(rig._rake_input(aid))
    finally:
        cfg.clear(); cfg.update(old)
    uu = np.arange(-1.0, total, 1e-2); dev = float(np.abs(alt.p(uu)-st.p(uu)).max())
    check(dev == 0.0 and not alt.issues, f'{aid}: the plan reads no arm cfg (root +0.37 / -0.21 m, links +0.2 / +0.1 m: '
          f'the same stroke, worst {dev:.1e} m, {len(alt.issues)} issues)')
    # ...and the rail plan's cfg reaches it: evaluate_arm (the search's accept rule: REACH_FRAC, the links' bend,
    # self, strings and scene margins) accepts the path at the search's 30 Hz
    hz = 30; times = np.arange(-hz, int(total*hz)+1)/hz; mid = cfg['mid']
    plane_z = float(np.mean([s_['a'][2] for s_ in rig.geometry['strings'].values() if s_['mid'] == mid]))
    ev = LS.evaluate_arm(rig, aid, {k: cfg[k] for k in LS.CFG_KEYS if k in cfg and k not in ('o1', 'o2', 'pinion')}, times,
                         boxes=LS.scene_boxes(rig.geometry), string_plane_z=plane_z)
    u2 = np.arange(-1.0, total, 2e-3); L = float(cfg['l1'])+float(cfg['l2'])
    dist = max(float(np.linalg.norm(P['wrist']-P['root'])) for P in (rig.pose(aid, float(t)) for t in u2))
    got = 'drops it' if ev is None else f'worst margin {ev["worst"]*1e3:.1f} mm'
    check(ev is not None and ev['worst'] >= 0, f'{aid}: the rail plan\'s cfg (root y {float(cfg["root_y"]):.2f} z {float(cfg["root_z"]):.2f}, '
          f'l1 {float(cfg["l1"]):.2f} l2 {float(cfg["l2"]):.2f}) accepts the path: evaluate_arm at {hz} Hz {got}; '
          f'|wrist - root| <= {dist/L:.4f} (l1 + l2) on a 2 ms grid (REACH_FRAC {LS.REACH_FRAC:g})')
    rake_defs(rig, aid, st)

# the shared M2 definitions (docs/motion-design.md, 'The rake'), on the tool point p(t) (the stroke's closed form)
D1_FT = 0.20          # m: D1, the follow-through along the exit tangent before it turns back, at every exit
D2_E = 0.70           # D2: the last frame before a hit covers this share of v_sweep / 30 along the entry tangent
D3_G = 10.0           # g: D3, the tool's |a| outside +-D3_PAD of every roll
D3_PAD = 0.01         # s
D4_DEG = 30.0         # deg: D4, consecutive 30 fps steps (both >= D4_LIM v_sweep / 30) within D4_T of a roll
D4_LIM = 0.25
D4_T = 0.25           # s
D5_CLEAR = 0.8        # s: D5, a roll this long after the last contact is announced (not a pendulum turn, not the ghost)...
D5_BS = 0.5           # s: ...by a backswing at least this long, then a declared head 'poise' hold of rake.HOLD_MIN, then the run-up
G = 9.81

def rake_defs(rig, aid, st):
    N = st.notes; P = lambda t: st.p(np.atleast_1d(np.asarray(t, float)))
    unit = lambda v: v/np.linalg.norm(v); total = float(rig.score['total_s'])
    def v_sweep(k):
        e = rig.sched[aid][k]['event']; Q = np.array([rig.contact(sid, e.get('pick')) for sid in e['strings']], float)
        return float(np.linalg.norm(np.diff(Q, axis=0), axis=1).sum()/(N[k].t_end-N[k].t))
    FT, E, TU = [], [], []
    for k, x in enumerate(N):
        vs = v_sweep(k); te = x.t_end; u = unit(st.v(np.array([te]), +1)[0]); t1 = N[k+1].t if k+1 < len(N) else te+2.0
        t = np.arange(te, min(t1, te+2.0), 1e-4); vt = st.v(t)@u
        kr = int(np.argmax(vt[1:] <= 0))+1 if (vt[1:] <= 0).any() else len(t)-1
        FT.append(float(((P(t[:kr+1])-P(te))@u).max()))
        ui = unit(st.v(np.array([x.t]), -1)[0]); E.append(float((P(x.t)-P(x.t-FRAME))[0]@ui/FRAME/vs))
        tf = np.arange(math.ceil((x.t-D4_T)/FRAME-1e-9), math.floor((te+D4_T)/FRAME+1e-9)+1)*FRAME
        Dp = np.diff(P(tf), axis=0); Ln = np.linalg.norm(Dp, axis=1); ok = (Ln[:-1] >= D4_LIM*vs*FRAME) & (Ln[1:] >= D4_LIM*vs*FRAME)
        c = (Dp[:-1]*Dp[1:]).sum(1)/np.maximum(Ln[:-1]*Ln[1:], 1e-12)
        TU.append(float(np.degrees(np.arccos(np.clip(c[ok], -1, 1))).max()) if ok.any() else 0.0)
    check(min(FT) >= D1_FT, f'{aid}: D1 every exit follows through >= {D1_FT} m along its tangent before it turns back '
          f'(min {min(FT):.3f} m over {len(FT)} rolls)')
    check(min(E) >= D2_E, f'{aid}: D2 every hit\'s last frame covers >= {D2_E} v_sweep along the entry tangent (min {min(E):.3f})')
    tt = np.arange(-1.0, total, 1e-3); m = np.ones(len(tt), bool)
    for x in N: m &= ~((tt >= x.t-D3_PAD) & (tt <= x.t_end+D3_PAD))
    a = np.linalg.norm(st.a(tt[m]), axis=1)/G
    check(float(a.max()) <= D3_G, f'{aid}: D3 the tool\'s |a| <= {D3_G:g} g outside +-{D3_PAD*1e3:g} ms of every roll '
          f'(max {float(a.max()):.2f} g at {float(tt[m][int(a.argmax())]):.3f} s, 1 ms grid)')
    check(max(TU) <= D4_DEG, f'{aid}: D4 frame steps within {D4_T} s of a roll turn <= {D4_DEG:g} deg (max {max(TU):.1f})')
    segs = sorted(st.head.segs, key=lambda s_: s_.t0); poise = [s_ for s_ in segs if s_.law == 'hold' and s_.extra.get('hold') == 'poise']
    bad = []; n5 = 0; lo = [math.inf, math.inf]
    for k, x in enumerate(N):
        clear = x.t-(N[k-1].t_end if k else -math.inf)
        if clear < D5_CLEAR or x.enter in ('turn', 'ghost'): continue
        n5 += 1; h = [s_ for s_ in poise if x.t_apex is not None and abs(s_.t1-x.t_apex) <= 1e-9]
        if not h: bad.append(x.t); continue
        j = segs.index(h[0])-1
        while j >= 0 and segs[j].law != 'hold': j -= 1
        bs = h[0].t0-segs[j].t1 if j >= 0 else 0.0; ho = h[0].t1-h[0].t0
        lo = [min(lo[0], bs), min(lo[1], ho)]
        if bs < D5_BS-1e-9 or ho < RK.HOLD_MIN-1e-9 or not h[0].t1 < x.t: bad.append(x.t)
    check(n5 and not bad, f'{aid}: D5 every roll {D5_CLEAR} s clear of the last ({n5}) is announced: a backswing >= {D5_BS} s '
          f'(min {lo[0]:.3f}), a declared head poise >= {RK.HOLD_MIN} s (min {lo[1]:.3f}), the run-up'+(f'; not at {bad}' if bad else ''))
    short = [s_ for s_ in poise if s_.t1-s_.t0 < RK.HOLD_MIN-1e-9]
    check(not short, f'{aid}: every poise hold lasts >= rake.HOLD_MIN {RK.HOLD_MIN} s ({len(poise)} holds'
          +(f'; {len(short)} short' if short else '')+')')
    # D7: every announced apex hold holds the TOOL still (round 2's 34.29 return ran its carriage on under it at up to
    # 1.41 m/s: the score's 0.8 s lead left the crossing 0.52 s; A24's announce_lead charges it)
    d7 = sorted((still_v(st, s_.t0, s_.t1), s_.t1) for s_ in poise)
    check(d7 and d7[-1][0] <= STILL_V, f'{aid}: D7 every announced apex hold ({len(d7)}) holds the tool still: max |v| '
          f'{d7[-1][0]*1e3 if d7 else 0:.3f} mm/s (<= {STILL_V*1e3:g} mm/s)'+''.join(f'; {t:.3f} s {v*1e3:.1f} mm/s' for v, t in d7 if v > STILL_V))
    d9(rig, aid, st)

def d9(rig, aid, st):
    """D9 (A27; the sense is the lead's L4): from each exit's turn (D1's t_rev) to the rest the comb never gives back
    more than RETURN_TOL of its running maximum along its release, and h rises or holds (D6). Round 2's park_hi
    settled 64 mm back down the strings and release_hi rocked 72 mm. u is t_out less its share of the string plane's
    normal (the lift is h's, not a give-back), as ruler 24 takes it (r_strings._give_back). The sense is 24's, row
    for row (r_strings._rake_end / _rake_rests): +u after an up exit and at every rest that is not a listed phrase
    end; -u after a DOWN exit at a listed end (RAKE_ENDS), where D1 runs the follow-through >= 0.2 m down the strings
    and 24's upward release must climb back: any displacement d it accepts has u.d <= cos(angle(u, +y) - REL_ANG) |d|
    (-0.533 |d| at 68.57), so the literal +u sense cannot hold there with D1 and 24. The +u number is printed beside
    every rest; at such an end it is info, never judged. A rest is a rest (D7): the comb is still where the hold
    starts (|v| <= STILL_V), so a chain still sinking into its hold fails though its give-back so far is small (24's
    '24 rest' judges the same chains, chosen by the same structure: every park, release and fallback note).
    -> [(t, leave, sense, judged, literal +u, h give-back)]"""
    N = st.notes; nrm = np.asarray(rig.clearance(aid), float); nrm = nrm/np.linalg.norm(nrm)
    hs = sorted(st.head.segs, key=lambda s_: s_.t0); cs = sorted(st.carriage.segs, key=lambda s_: s_.t0)
    held = lambda segs, t: next((s_.t0 for s_ in segs if s_.law == 'hold' and s_.t0 >= t-1e-9), math.inf)
    rows = []; bad = []; why = []
    for x in N:
        if not x.leave.startswith(('park', 'release', 'fallback')): continue
        te = x.t_end; v0 = st.v(np.array([te]), +1)[0]; t_out = v0/np.linalg.norm(v0)
        u = t_out-(t_out@nrm)*nrm; u /= np.linalg.norm(u); t_rest = max(held(hs, te), held(cs, te))
        t = np.unique(np.r_[np.arange(te, t_rest, 1e-4), t_rest]); vt = st.v(t)@t_out
        kr = int(np.argmax(vt[1:] <= 0))+1 if (vt[1:] <= 0).any() else len(t)-1
        c = st.p(t[kr:])@u                                  # from the turn: its running maximum starts there
        lit = float((np.maximum.accumulate(c)-c).max()); rel = float((c-np.minimum.accumulate(c)).max())
        sense = -1 if t_out[1] <= 0 and any(abs(x.t-T) <= END_TOL for T in RAKE_ENDS) else +1
        gb = rel if sense < 0 else lit
        h = st.h(t[kr:]); hgb = float((np.maximum.accumulate(h)-h).max())
        vr = float(np.linalg.norm(st.v(np.array([t_rest]), -1)[0]))    # D7 where the hold starts: arrived, not passing
        rows.append((x.t, x.leave, sense, gb, lit, hgb))
        if sense < 0:
            best = math.cos(math.radians(max(0.0, math.degrees(math.acos(float(np.clip(u[1], -1, 1))))-REL_ANG)))
            why.append(f'{x.t:.2f}: a down exit at a listed end, judged along -u (24\'s upward release does at best '
                       f'{best:+.3f} m per m along +u)')
        if gb > RETURN_TOL or hgb > RETURN_TOL or vr > STILL_V:
            bad.append(f'{x.t:.2f} {x.leave} gives back {gb*1e3:.3f} mm along {"+-"[sense < 0]}u (h {hgb*1e3:.3f} mm), '
                       f'|v| {vr*1e3:.1f} mm/s at its rest {t_rest:.4f}')
    check(rows and not bad, f'{aid}: D9 every rest ({len(rows)}) gives back <= {RETURN_TOL:g} m along its release from the turn '
          f'on, h rising or holding, and is still at its hold (|v| <= {STILL_V*1e3:g} mm/s): '+', '.join(f'{t:.2f} {lv} {"+-"[s < 0]}u {g*1e3:.3f} mm (+u {l*1e3:.3f} mm'
                                                 +(', info' if s < 0 else '')+')' for t, lv, s, g, l, _ in rows)
          +''.join(f'; {w}' for w in why)+(f'; {"; ".join(bad)}' if bad else ''))
    return rows

def run(layout_path, score_path):
    print(f'== {layout_path.name} / {score_path.name}')
    layout = json.loads(layout_path.read_text()); score = json.loads(score_path.read_text())
    rig = Rig(score, layout)
    picks = [a for a in rig.plans if rig.plans[a] and rig.acts[a]['kind'] == 'pick']
    planned = [a for a in picks if rig.stroke(a) is not None]
    multi = [a for a in picks if any(len(s['event']['strings']) > 1 for s in rig.sched[a])]
    check(sorted(planned) == sorted(set(picks)-set(multi)) and planned,
          f'Rig.stroke plans every single-string pick arm ({", ".join(planned)}); a sweep keeps today\'s ({len(multi)})')
    for aid in planned: contract(rig, aid)
    rakes = [a for a in rig.plans if rig.plans[a] and rig.acts[a]['kind'] == 'rake']
    check(rakes and all(rig.stroke(a) is not None for a in rakes), f'Rig.stroke plans every rake arm ({", ".join(rakes)})')
    for aid in rakes: rake_contract(rig, aid)
    # REACH_FRAC is the search's accept rule (the rake's pieces read no arm: the search chooses its root and
    # links to reach them), so retuning it changes what the search accepts and must replan the rail
    mech = next(m for m in score['instrument']['mechanisms'] if any(a['id'] in rakes for a in m['actuators']))
    key = lambda: LS._mech_key(score, layout, mech, 30, .08, {})
    base, was = key(), LS.REACH_FRAC
    try:
        LS.REACH_FRAC = was-.005; tuned = key()
    finally:
        LS.REACH_FRAC = was
    check(tuned != base and key() == base, f'tuning layout_search.REACH_FRAC, the search\'s accept rule ({was} -> {was-.005:.3f}), changes the rake\'s rail key')
    # TIE_TOL decides which near-equal options plan_arms' tie-break (the links' strobe, ruler 1) chooses among, so
    # retuning it can move a rail too (round 3's rake: -0.90 over -1.35 on a 1-ulp flip)
    was = LS.TIE_TOL
    try:
        LS.TIE_TOL = was*10; tuned = key()
    finally:
        LS.TIE_TOL = was
    check(tuned != base and key() == base, f'tuning layout_search.TIE_TOL, the plan\'s tie tolerance ({was:g} -> {was*10:g}), changes the rake\'s rail key')

if __name__ == '__main__':
    scurve_unit(); functions(); rail_key(); rake_unit(); rake_rail_key()
    if len(sys.argv) > 2: pairs = [(Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve())]
    else: pairs = [(ROOT/'harness/assets/clockwork.json', ROOT/'render/chamber/score.json'),
                   (ROOT/'harness/assets/clockwork_expanded.json', ROOT/'render/clockwork/score.json')]
    for lp, sp in pairs: run(lp, sp)
    print('SERVO: '+('FAIL' if failures else 'PASS'))
    sys.exit(1 if failures else 0)

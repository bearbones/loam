#!/usr/bin/env python3
"""Design the rake's pieces (PLAYERS M2, T5) and write formlab/rake_pieces.json,
the library formlab/rake.py plays. Offline and scipy (SLSQP): the planner
itself stays numpy-only and only reads the result.

    python3 tools/rake_design.py                      # design every piece (staged, cold: minutes on 2 threads)
    python3 tools/rake_design.py --warm FILE.json     # the final stage only, from those z vectors (by piece name)
    python3 tools/rake_design.py --check              # does the library still fit both assets? (no solve)
    python3 tools/rake_design.py --homing             # check HOMING on every rail the search can accept; write it in
    python3 tools/rake_design.py --homing-search      # ...or search for homing poses (minutes; prints them)

A piece is a piecewise quintic hermite on [0, D] in the head's (y, h) (and in
the carriage x where it crosses under the head): each component has interior
knots whose (p, v, a) states are free, its ends are the live states it joins
(a sweep's entry or exit, a rest), and outside its own interval a fixed closed
form supplies it (the carriage's rail run-out/run-up quintics). Every sampled
signal is LINEAR in the knot states, so the design keeps basis matrices and
hands SLSQP exact Jacobians.

The pieces live in TOOL space and read no arm: no root, no link length, no
reach cut (the motion comes first and the rail plan, formlab/layout_search,
then chooses the rake's root and links so the arm reaches what the comb does;
its REACH_FRAC is that search's accept rule, not a design input here). The
constraints are physical and the shared M2 definitions (docs/motion-design.md,
'The rake'), with margin:
  D1 follow-through  from every exit the comb runs on along the exit tangent
                     >= FT_MIN before it turns back, decelerating along it at
                     <= 3 g (FT_G) while it drops away along n;
  D2 entry           the last frame before a hit covers >= E_MIN v_sweep along
                     the entry tangent, and the last RI_T s >= RI_DES (a run-in);
  D3 tool |a|        <= AMAX everywhere (the objective is the peak: about 5 g);
  D4 frame turns     within D4_T of a sweep, consecutive frame chords (every
                     D4_PH phase, the sweep's own frames joined on) turn
                     <= D4_DEG unless one is under 0.25 v_sweep / FPS;
  the comb's rho     (ruler 14: chord / (2 r + |chord . tool capsule|) per
                     frame; instantaneous here, on a 1-4 ms grid, at RHO_D);
  the carriage       |x''| <= AXMAX and x in [x_lo, x_hi] (formlab.rake.OVER
                     past the outer strings: A19);
  the strings        h >= 0 (never through the plane outside a sweep), the
                     comb clear of the end string from TC after an exit /
                     before an entry (H_CLEAR) and >= 5 mm off every string
                     from FAR_S (H_FAR), y inside the strings' span (Y_MIN, Y_MAX);
  ruler 3 and 5      strict rise and fall of h about the piece's apex (secant
                     signs at 1e-6 m/s: EPS_H); the pendulum's speed floor.
The objective is the peak tip |a| (staged: mean |a|^2 without D3 and D4, then
constrained, then the peak). The backswings home_up and return_up (rest ->
apex, the carriage crossing under the head) are designed pieces like the
rest; the one 3-4-5 backswing is formlab/rake.py's park -> apex at the same
end (BACKSWING_S). The homing poses (HOMING) are tool space as well, chosen
against every rail the search can accept rather than one (ruler 22 home reads
the arm's joint spans). What each piece is for, and its numbers:
docs/motion-design.md, 'The rake'."""
import argparse, json, math, os, sys, time
os.environ.setdefault('OMP_NUM_THREADS', '2')
from pathlib import Path
import numpy as np
from scipy.optimize import minimize
from scipy.interpolate import CubicSpline

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT/'tools'))
from formlab import rake as RK, clearance as CL, layout_search as LS
from formlab.rig import Rig
from players import core, r_strings

AID = 'rake_arm0'                 # the one rake arm on both assets
MT = RK.motion_timing             # the score's timing (the announce clause: the run-up, the hold, the crossing's window)
FPS = MT.FPS                      # ruler 14 reads rho per frame; D2 and D4 read frames
G = 9.81                          # the rulers' g
RHO_D = 0.92                      # design rho on the 1-4 ms grid (ruler 14 reads frames; <= 1.0)
RHO_GHOST = 0.92                  # ...on the binding 67.14 -> 68.57 ghost
AXMAX = 0.95*3*G                  # m/s^2: carriage |x''| in a designed travel (ruler 14: 3 g, 5 % margin)
AMAX = 0.95*10*G                  # m/s^2: D3, the tool's |a| anywhere in a piece (<= 10 g, 5 % margin)
FT_MIN, FT_DES = 0.20, 0.21       # m: D1, the follow-through along the exit tangent before it turns back; designed with 10 mm margin
FT_T = 0.20                       # s: ...reached by this long after the exit, the tangential speed >= FT_VEPS up to it (the brief: ~0.2 s)
FT_T_GHOST = 0.15                 # s: ...on the ghost, whose carriage leaves 0.1 s after the exit and pulls against the rake00 tangent
FT_VEPS = 0.02                    # m/s: the tangential speed's floor over [0, FT_T] (D1 reads v . t_out <= 0 as the turn back)
FT_G = 0.95*3*G                   # m/s^2: ...decelerating along the exit tangent at <= 3 g there (the brief), 5 % margin
E_MIN, E_DES = 0.70, 0.75         # D2: the last frame before a hit covers this share of v_sweep / FPS along the entry tangent (designed)
RI_T, RI_DES = 0.20, 0.21         # s, m: the run-in: the comb's travel along the entry tangent over the last RI_T s (designed >= RI_DES)
# D4: within 0.25 s of a sweep, consecutive frame steps (both >= 0.25 v_sweep / FPS) turn <= 30 deg. Designed on the frame
# chords themselves (from D4_PH frame phases; the sweep's own last frames turn up to 19 deg): |a x b|^2 <= sin^2(D4_DEG)
# |a|^2 |b|^2 + (D4_L0 lim)^4 and a . b >= -(D4_L0 lim)^2, the L0 terms freeing the short steps D4 skips (at two steps of
# exactly lim the bound is 28 deg)
D4_DEG = 27.0                     # deg: the design turn between frame steps (30, 3 deg margin)
D4_L0 = 0.35                      # x lim: the short-step relaxation
D4_PH = 6                         # frame phases designed (the score's hits fall at any phase of the 30 fps clock)
D4_T = 0.25                       # s: the window after an exit / before an entry (D4's)
Y_MIN, Y_MAX = 0.70, 2.58         # m: the tool's y range: 40 mm inside the rake strings' span (rake00's lower anchor at y 0.66,
                                  # rake04's upper end at 2.62; past them the frame and the necks' bridges and pins stand)
EPS_H = 2e-4                      # m/s: h' >= EPS_H w(t) rising, <= -EPS_H w(t) falling (ruler 3 reads secant signs at 1e-6 m/s)
# the comb (capsule r 30 mm, r_strings.TOOL_R) against an end string (wire r <= 6 mm) with the carriage on the overtravel (OVER):
H_CLEAR = 0.034                   # m: clear (>= 0, ruler 23) when h >= this: hypot(OVER, h) >= 30 + 6 mm
H_FAR = 0.042                     # m: >= 5 mm off ANY string when h >= this (the comb straight over one: h >= 30 + 6 + 5 mm)
TC = 0.035                        # s: the comb clears the end string this long after an exit / before an entry (H_CLEAR)...
FAR_S = 0.10                      # s: ...and every string by 5 mm from this long (H_FAR): 'away from the sweeps'
FLOOR_RAMP = 0.006                # s: each floor ramps in over this (a step would pin one sample)
SCALE = np.array([1.0, 3.0, 30.0])# the free (p, v, a) states' scale in z (SLSQP's variables are O(1))
Z_BOUND = ((-8, -4, -6), (8, 4, 6))   # z bounds per state (x SCALE: |p| <= 8 m, |v| <= 12 m/s, |a| <= 180 m/s^2)
PEAK_BOUND = 500.0                # m/s^2: the peak variable's upper bound
W_JERK = 2e-6                     # the objective's mean |p'''|^2 weight (keeps free knots from ringing)
ITERS = (500, 500, 2000)          # SLSQP iterations per stage (acc, acc + constraints, peak)
VIOL_MAX = 1e-6                   # a designed piece's worst limit violation (scaled units: rho 1e-7, x, y, h 1e-8 m) accepted
RESTARTS = 4                      # final-stage re-runs from where SLSQP stopped while the design violates by > VIOL_GOAL
VIOL_GOAL = 1e-8                  # ...the violation a restart aims under
LINE_TOL = 1e-4                   # m: a backswing's head stays this close to its (y, h) chord (ruler 22 judges its progress along
                                  # the chord from wherever the carriage's travel starts: a straight head cannot overshoot it)
# the pieces' lengths and heights (s, m) (docs/motion-design.md 'The rake')
# run-ups from the apex hold: into rake00 (announce; after the return: both the score's RAKE_RUNUP_S, which its announce_lead
# charges; round 2's 0.18 s return run-up launched at 6.6 g), into rake04
RU_LO, RU_LO_B, RU_HI = MT.RAKE_RUNUP_S, MT.RAKE_RUNUP_S, 0.22
H_A0, H_A0B, H_A4 = 0.32, 0.25, 0.30          # their apex h (ruler 3: dh >= 0.25 h(t_apex) from the park)
PARK_D = 0.45                                 # follow-through to a park
H_P = 0.15                                    # park h (<= 0.75 apex: ruler 3's wind-up rises from it)
REL_D, REL_Y_LO, REL_H = 0.70, 1.40, 0.15     # the phrase-end release after a down roll: up the strings to (1.40, 0.15)
# ...after an up roll (the last roll: home follows): rest up the strings where the follow-through ends (y free, at least yP;
# in-plane monotone, D9, so it climbs on to Y_MAX: round 2's, bounded only at its end, ran to 2.579, rocked 72 mm back to 2.507
# and up again to 2.56, two ~180 deg turns; at 2.46 the first design rose to Y_MAX and sagged 0.12 m to rest, ruler 24's angle
# 36 deg), h below the hover (H0 = 0.22) so the end travel home only rises (D6)
REL4 = dict(yP=2.56, hP=0.20, D=0.70)
BS_HOME, BS_RETURN = 0.50, 0.90               # backswings (the head's): home -> the first apex; the return across the rail
                                              # (park_hi -> rake00: 1.7 m of head over the carriage's 1.08 m crossing, which
                                              # runs in the score's window, Frame.cross: 0.45 s home, 0.656 s on the return;
                                              # the head leaves 0.05 / 0.24 s before the carriage's go, D5)
LOOP_VMIN = dict(hi=0.7, lo=0.5)              # m/s: the pendulum turn's speed floor (ruler 5)
# ruler 5 reads a turn under 0.15 of its own peak speed for over a frame as a rest. The hi turn peaks at 4.1-4.2 m/s (0.15 of
# it 0.63): at 0.6 it sat at 0.142-0.146 of its peak and passed only while that stretch stayed under a frame. The merge's
# sweep (formlab.rake.SWEEP_TUCK) moved it: from cold it stopped at the iteration limit (6.09 g), and a quarter of the way on
# read 54 ms under at every hi apex (ruler 5 FAIL); 0.7 converges and keeps it 0.165 (the lo turn reads 0.156 at 0.5)
APEX_RANGE = dict(turn=(0.3, 0.6), ghost=(0.5, -0.05))   # s: where a turn's / the ghost's apex is searched (ghost: to D - 0.05)
FT_V = 2.4                        # m/s: the ghost's speed floor from the rake00 exit to the carriage's go, where formlab.rake cuts
                                  # 'ghost' (ruler 14 reads the follow-through's arc to that cut: >= 0.2 m; 0.1 s x 2.4 = 0.24)
# The homing poses (y, h), carried through the score's 'elbow' and 'shoulder' windows at home on straight 3-4-5 chords
# (formlab.rake). Ruler 22 home asks the sweep for >= 0.8 of the shoulder's and the elbow's IK spans, which are the ARM's:
# so the poses are chosen in tool space against every rail the search can accept (--homing-search: differential evolution
# over HOME_Y x HOME_H; --homing checks and writes them), each inside that rail's own |wrist - root| range of the rest of
# the motion by HOME_ENV (the homing never decides a rail), the chords inside the windows at HOME_SERVO_V. The first
# poses, (0.75, 0.25), (2.30, 0.15) | (1.60, 0.50), swept 1.09 / 0.86 on the first rail and 0.12 of the shoulder on others.
HOMING = dict(elbow=[(2.565, 0.155), (2.375, 0.44), (0.885, 0.395)], shoulder=[(0.775, 0.19), (1.61, 0.225)])
HOME_SWEEP = 0.80                 # ruler 22 home: shoulder and elbow swept / their IK span (mirrored, not set here)
HOME_ENV = 0.010                  # m: the homing's |wrist - root| this far inside each rail's range over the rest of the motion
HOME_Y, HOME_H = (Y_MIN, Y_MAX), (0.06, 0.65)   # m: the poses' range (h: over H_FAR with margin, under the pendulum's apex)


# ---- the frame -------------------------------------------------------------------------------
class Frame:
    """The live geometry formlab.rake plans in, from the asset's Rig: the
    rail, the comb (rho) and the representative rolls. No arm cfg: the comb's
    capsule hangs off the raked kind's fixed wrist (layout_search.WRIST_SERVO,
    every candidate's), so its rho is the same whatever rail the search picks."""
    def __init__(s, asset):
        paths = core.ASSETS[asset]
        s.layout = json.loads(Path(paths['manifest']).read_text()); score = json.loads(Path(paths['score']).read_text())
        lib = RK.plan_rake; RK.plan_rake = lambda arm, **k: None          # the Rig plans every arm at load: not this one
        try: s.rig = Rig(score, s.layout)
        finally: RK.plan_rake = lib
        s.arm = s.rig._rake_input(AID); s.g = RK.Geometry(s.arm)
        s.rolls = [RK._roll(s.g, r) for r in sorted(s.arm.rolls, key=lambda r: r.t)]
        s.Z0 = s.g.zc
        s.OFF = np.asarray(CL.shank_path([0, .07, 0], CL.tool_mount(LS.WRIST_SERVO, [0, 0, 0]), count=25)[12], float)
        s.E0 = 2*r_strings.TOOL_R
        s.X_LO, s.X_HI = s.g.x_lo, s.g.x_hi
        # the carriage's crossing under each designed backswing: from the score's go (the slew cap's announce clause sizes it
        # from the crossing's distance, motion_timing.announce_lead, A24) to the apex hold's start, which the run-up and the
        # hold put RAKE_RUNUP_S + RAKE_HOLD_S before the first string: the first roll (home_up) and the first up -> up long
        # gap (return_up, park_hi -> rake00). Read from the score as the ghost's window is, so the two cannot drift apart
        hold = MT.RAKE_RUNUP_S+MT.RAKE_HOLD_S; R0 = s.rolls[0]; s.cross = dict(home_up=R0['t']-hold-R0['r'].go)
        Rr = next((R for P_, R in zip(s.rolls, s.rolls[1:]) if P_['up'] and R['up']), None)
        if Rr is not None: s.cross['return_up'] = Rr['t']-hold-Rr['r'].go
        up = next(R for R in s.rolls if R['up']); dn = next(R for R in s.rolls if not R['up'])
        st = lambda R, k: {'x': tuple(R['X'][k]), 'y': tuple(R['Y'][k])}
        s.E = dict(up0=st(up, 0), up1=st(up, -1), dn0=st(dn, 0), dn1=st(dn, -1), D0=up['D_in'], D4=up['D_out'],
                   c_ro4=RK._st.law_hermite(*up['X'][-1], s.X_HI, 0, 0, up['D_out']),
                   c_ro0=RK._st.law_hermite(*dn['X'][-1], s.X_LO, 0, 0, dn['D_out']),
                   c_ru4=RK._st.law_hermite(s.X_HI, 0, 0, *dn['X'][0], dn['D_in']),
                   c_ru0=RK._st.law_hermite(s.X_LO, 0, 0, *up['X'][0], up['D_in']))
        assert dn['D_out'] == up['D_in'] and dn['D_in'] == up['D_out'], 'a down roll is no mirror of an up roll'
        s.YS = [float(up['Y'][0][0]), float(up['Y'][-1][0])]     # rake00's and rake04's contact y (guides only)
        # the sweep's tangent (an up roll's; a down roll's is its negative) and ruler 14's v_sweep (D2)
        v = np.array([up['X'][0][1], up['Y'][0][1], 0.0]); s.U = v/np.linalg.norm(v)
        P = np.asarray(up['r'].points, float); s.V_SW = float(np.linalg.norm(np.diff(P, axis=0), axis=1).sum()/(up['t_end']-up['t']))
        s.sweeps = {True: up, False: dn}
        # the short gaps the score plays: the pendulum turns (same end) and the ghost (down -> down)
        s.turn_gap = s.ghost = None
        for P_, R in zip(s.rolls, s.rolls[1:]):
            gap = R['t']-P_['t_end']
            if gap > 1.0: continue
            if P_['up'] != R['up'] and s.turn_gap is None: s.turn_gap = gap
            if not P_['up'] and not R['up'] and s.ghost is None:
                s.ghost = dict(gap=gap, go=max(P_['r'].t_free, R['r'].go)-P_['t_end'], arr=R['t']-s.arm.approach-P_['t_end'])

    def fingerprint(s): return s.g.fingerprint(s.arm, s.rolls)

    def u(s, up): return s.U if up else -s.U

    def sweep(s, up, tau, d=0):
        """A roll's sweep (x, y, z - z_c) at tau s from its first string, (n, 3)."""
        R = s.sweeps[up]; K = R['ts']-R['ts'][0]; tau = np.atleast_1d(np.asarray(tau, float))
        x = RK._pw_eval(K, RK._pw(K, R['X']), tau, d); y = RK._pw_eval(K, RK._pw(K, R['Y']), tau, d)
        h = RK._pw_eval(K, RK._pw(K, R['H']), tau, d)
        return np.c_[x, y, -h]


# ---- the designer (piecewise quintic hermites, SLSQP) ---------------------------------------------
def peval(c, tau, d=0):
    c = np.asarray(c, float)
    for _ in range(d): c = c[1:]*np.arange(1, len(c)) if len(c) > 1 else np.zeros(1)
    out = np.zeros_like(np.asarray(tau, float))
    for k in range(len(c)-1, -1, -1): out = out*tau+c[k]
    return out


def herm_coefs(K, S):
    T = np.diff(K); p0, v0, a0 = S[:-1].T; p1, v1, a1 = S[1:].T; d = p1-p0
    c3 = (20*d-(8*v1+12*v0)*T-(3*a0-a1)*T*T)/(2*T**3)
    c4 = (-30*d+(14*v1+16*v0)*T+(3*a0-2*a1)*T*T)/(2*T**4)
    c5 = (12*d-6*(v1+v0)*T+(a1-a0)*T*T)/(2*T**5)
    return np.c_[p0, v0, a0/2, c3, c4, c5]


def pw_eval(K, C, ts, d):
    j = np.clip(np.searchsorted(K, ts, side='right')-1, 0, len(K)-2); tau = ts-K[j]; c = C[j]
    for _ in range(d): c = c[:, 1:]*np.arange(1, c.shape[1])[None, :]
    out = np.zeros_like(ts)
    for k in range(c.shape[1]-1, -1, -1): out = out*tau+c[:, k]
    return out


class Comp:
    """One component (x, y or h) of a piece: designed on [ta, tb] through free
    interior knot states between fixed (or p-free) end states; `outside`
    supplies it beyond; `guide` seeds a cold design."""
    def __init__(s, ta, tb, bc0, bc1, knots, guide=None, outside=None, lock=(), free_p0=False, free_p1=False):
        s.ta = ta; s.tb = tb; s.bc0 = np.array(bc0, float); s.bc1 = np.array(bc1, float)
        s.free_p0 = free_p0; s.free_p1 = free_p1; s.nends = int(free_p0)+int(free_p1)
        s.K = np.r_[ta, np.asarray(knots, float), tb]; s.guide = guide; s.outside = outside
        s.lock = dict(lock); s.free = [i for i in range(len(knots)) if i not in s.lock]


def fixed_comp(fn):
    """A component given entirely by the closed form fn (no free knots)."""
    return Comp(1e9, 1e9+1, (0, 0, 0), (0, 0, 0), [], None, fn)


class Design:
    """One piece's SLSQP problem. Keywords (constraint families, all off by default):
    rho, amax, axmax, xb, hmin(t), ymin, t_ap/ap_eps/ap_w (strict apex), vmin, vfloor,
    mono [(comps, weights)], line (p0, chord) (a backswing's straight head), and the
    shared M2 definitions: ft (D1: u, t, d, g) and entry (D2: u, e, ri, v_sw)."""
    def __init__(s, F, comps, t0, t1, **kw):
        s.F = F; s.c = comps; s.t0 = t0; s.t1 = t1
        s.__dict__.update(dict(hmin=None, t_ap=None, rho=None, vmin=None, axmax=None, xb=(F.X_LO, F.X_HI),
                               wj=W_JERK, dt=4e-3, dense=(), amax=AMAX, objective='peak', ap_pad=.01, ap_eps=0.0, ap_w=None,
                               ymin=Y_MIN, ymax=Y_MAX, mono=None, vfloor=None, ft=None, entry=None, line=None, yend=None,
                               d4=None))
        s.__dict__.update(kw)
        ts = [np.arange(t0, t1, s.dt)]
        for a, b in s.dense: ts.append(np.arange(max(a, t0), min(b, t1), 1e-3))
        ts = np.unique(np.r_[np.concatenate(ts), t1]); s.ts = ts[(ts > t0+1e-9) & (ts < t1-1e-9)]
        s.B = {k: s._basis(k, s.ts) for k in s.c}
        # the probes: exact instants D1 and D2 read (the piece's ends, the follow-through's end, a frame
        # and the run-in before the hit), with a basis of their own (t0 and t1 included)
        pr = [t0, t1]
        if s.ft is not None: pr.append(t0+s.ft['t'])
        if s.entry is not None: pr += [t1-1.0/FPS, max(t0, t1-RI_T)]
        s.pr = np.array(pr, float); s.PB = {k: s._basis(k, s.pr) for k in s.c}
        if s.d4 is not None:     # D4's frame points: step starts every 1/(FPS D4_PH) s; outside the piece the sweep it joins
            h_ = 1.0/FPS; st = []
            if s.d4.get('exit') is not None: st.append(np.arange(t0-2*h_+h_/D4_PH, min(t0+D4_T, t1)-2*h_+1e-9, h_/D4_PH))
            if s.d4.get('entry') is not None: st.append(np.arange(max(t0, t1-D4_T), t1-1e-9, h_/D4_PH))
            st = np.unique(np.round(np.concatenate(st), 9)); pts = np.unique(np.round(np.r_[st, st+h_, st+2*h_], 9))
            s.d4i = [np.searchsorted(pts, np.round(st+k*h_, 9)) for k in range(3)]
            s.d4in = (pts >= t0) & (pts <= t1); s.FB = {k: s._basis(k, pts[s.d4in]) for k in s.c}
            T_sw = float(F.sweeps[True]['ts'][-1]-F.sweeps[True]['ts'][0]); s.d4fix = np.zeros((len(pts), 3))
            m = pts < t0
            if m.any(): s.d4fix[m] = F.sweep(s.d4['exit'], T_sw+pts[m]-t0)
            m = pts > t1
            if m.any(): s.d4fix[m] = F.sweep(s.d4['entry'], pts[m]-t1)
            s.d4lim = 0.25*F.V_SW/FPS

    def _states_k(s, k, zk):
        c = s.c[k]; S = np.zeros((len(c.K), 3)); S[0] = c.bc0; S[-1] = c.bc1
        for i, st in c.lock.items(): S[i+1] = st
        for j, i in enumerate(c.free): S[i+1] = zk[3*j:3*j+3]*SCALE
        o = 3*len(c.free)
        if c.free_p0: S[0, 0] = zk[o]; o += 1
        if c.free_p1: S[-1, 0] = zk[o]
        return S

    def _sig_k(s, k, zk, ts, d):
        c = s.c[k]; m = (ts >= c.ta) & (ts <= c.tb); v = np.zeros_like(ts)
        if m.any(): v[m] = pw_eval(c.K, herm_coefs(c.K, s._states_k(k, zk)), ts[m], d)
        if (~m).any(): v[~m] = c.outside(ts[~m], d)
        return v

    def _basis(s, k, ts):
        """d -> (offset (ns,), M (ns, nz_k)) with signal = offset + M @ z_k."""
        nk = 3*len(s.c[k].free)+s.c[k].nends; out = {}
        for d in range(4):
            b0 = s._sig_k(k, np.zeros(nk), ts, d); M = np.zeros((len(ts), nk))
            for j in range(nk):
                e = np.zeros(nk); e[j] = 1.0; M[:, j] = s._sig_k(k, e, ts, d)-b0
            out[d] = (b0, M)
        return out

    def _split(s, z):
        out = {}; o = 0
        for k, c in s.c.items():
            n = 3*len(c.free)+c.nends; out[k] = (o, z[o:o+n]); o += n
        return out

    def nz(s): return sum(3*len(c.free)+c.nends for c in s.c.values())+1

    def signals(s, z, ts=None):
        sp = s._split(z)
        if ts is None: return {k: [s.B[k][d][0]+s.B[k][d][1]@sp[k][1] for d in range(4)] for k in s.c}, z[-1]
        ts = np.asarray(ts, float)
        return {k: [s._sig_k(k, sp[k][1], ts, d) for d in range(4)] for k in s.c}, z[-1]

    def states(s, z):
        sp = s._split(z); return {k: s._states_k(k, sp[k][1]) for k in s.c}, z[-1]

    def _J(s, k, d, z, B=None):
        B = s.B if B is None else B; sp = s._split(z); o, zk = sp[k]
        J = np.zeros((B[k][d][1].shape[0], len(z))); J[:, o:o+len(zk)] = B[k][d][1]; return J

    def _probe(s, z):
        """The tool point (x, y, -h) at the probes, (np, 3), and its Jacobian per axis."""
        sp = s._split(z); P = np.stack([s.PB[k][0][0]+s.PB[k][0][1]@sp[k][1] for k in ('x', 'y', 'h')], axis=1)
        P[:, 2] *= -1
        J = [s._J('x', 0, z, s.PB), s._J('y', 0, z, s.PB), -s._J('h', 0, z, s.PB)]
        return P, J

    def _rho(s, V):
        OFF = s.F.OFF; E0 = s.F.E0
        sp = np.linalg.norm(V, axis=1); q = V@OFF; den = E0*sp+np.abs(q)
        rho = sp*sp/(FPS*np.maximum(den, 1e-12))
        g = (2*V*den[:, None]-(sp*sp)[:, None]*(E0*V/np.maximum(sp, 1e-12)[:, None]+np.sign(q)[:, None]*OFF[None, :])) \
            / (FPS*np.maximum(den, 1e-12)**2)[:, None]
        return rho, g

    def cons_all(s, z):
        sig, peak = s.signals(z); x, y, h = sig['x'], sig['y'], sig['h']
        V = np.c_[x[1], y[1], -h[1]]; A = np.c_[x[2], y[2], -h[2]]
        JV = [s._J('x', 1, z), s._J('y', 1, z), -s._J('h', 1, z)]; JA = [s._J('x', 2, z), s._J('y', 2, z), -s._J('h', 2, z)]
        F = []; Jl = []; fam = []; npk = np.zeros(len(z)); npk[-1] = 1.0
        a2 = (A*A).sum(1); Ja2 = 2*sum(A[:, i:i+1]*JA[i] for i in range(3))
        if s.objective == 'peak': fam.append('peak'); F.append((peak*peak-a2)/1e3); Jl.append((2*peak*npk[None, :]-Ja2)/1e3)
        if s.amax is not None: fam.append('amax'); F.append((s.amax**2-a2)/1e3); Jl.append(-Ja2/1e3)
        rho, g = s._rho(V); Jrho = sum(g[:, i:i+1]*JV[i] for i in range(3))
        if s.objective == 'rho': fam.append('rho'); F.append((peak-rho)*10); Jl.append((npk[None, :]-Jrho)*10)
        elif s.rho is not None: fam.append('rho'); F.append((s.rho-rho)*10); Jl.append(-Jrho*10)
        if s.mono is not None:   # sync legs: v . chord >= 0 per channel (head: (y, z); carriage: x)
            for comps_, vec in s.mono:
                v = sum(sig[k][1]*w for k, w in zip(comps_, vec)); Jm = sum(s._J(k, 1, z)*w for k, w in zip(comps_, vec))
                fam.append('mono'); F.append(v*10); Jl.append(Jm*10)
        if s.line is not None:   # the head on its chord: |(y - y0) dz - (z - z0) dy| <= LINE_TOL (z = -h)
            (y0, h0), (dy, dz) = s.line; cr = (y[0]-y0)*dz-(-(h[0]-h0))*dy; Jc = dz*s._J('y', 0, z)+dy*s._J('h', 0, z)
            fam.append('line'); F.append(np.r_[LINE_TOL-cr, LINE_TOL+cr]*1e3); Jl.append(np.r_[-Jc, Jc]*1e3)
        if s.ymin is not None: fam.append('ymin'); F.append((y[0]-s.ymin)*100); Jl.append(100*s._J('y', 0, z))
        if s.ymax is not None: fam.append('ymax'); F.append((s.ymax-y[0])*100); Jl.append(-100*s._J('y', 0, z))
        if s.hmin is not None: fam.append('hmin'); F.append((h[0]-s.hmin(s.ts))*100); Jl.append(100*s._J('h', 0, z))
        if s.t_ap is not None:
            m1 = (s.ts < s.t_ap-s.ap_pad); m2 = (s.ts > s.t_ap+s.ap_pad); Jh1 = s._J('h', 1, z)
            w = s.ap_w(s.ts) if s.ap_w is not None else np.ones(len(s.ts))
            fam.append('strict'); F.append(np.r_[h[1][m1]-s.ap_eps*w[m1], -h[1][m2]-s.ap_eps*w[m2]]); Jl.append(np.r_[Jh1[m1], -Jh1[m2]])
        if s.d4 is not None:     # D4 on the frame chords a, b (in lim): sin form and same-sense, both freed when short
            sp = s._split(z); P = s.d4fix.copy(); n_in = int(s.d4in.sum()); JP = []
            for i, k in enumerate(('x', 'y', 'h')):
                sg = -1.0 if k == 'h' else 1.0
                P[s.d4in, i] = sg*(s.FB[k][0][0]+s.FB[k][0][1]@sp[k][1])
                J = np.zeros((len(P), len(z))); J[s.d4in] = sg*s._J(k, 0, z, s.FB); JP.append(J)
            i0, i1, i2 = s.d4i; L = s.d4lim; a = (P[i1]-P[i0])/L; b = (P[i2]-P[i1])/L
            Ja = [(J[i1]-J[i0])/L for J in JP]; Jb = [(J[i2]-J[i1])/L for J in JP]
            aa = (a*a).sum(1); bb = (b*b).sum(1); ab = (a*b).sum(1)
            daa = 2*sum(a[:, i:i+1]*Ja[i] for i in range(3)); dbb = 2*sum(b[:, i:i+1]*Jb[i] for i in range(3))
            dab = sum(b[:, i:i+1]*Ja[i]+a[:, i:i+1]*Jb[i] for i in range(3)); S2 = math.sin(math.radians(D4_DEG))**2
            f1 = (S2-1)*aa*bb+ab*ab+D4_L0**4; J1 = (S2-1)*(bb[:, None]*daa+aa[:, None]*dbb)+2*ab[:, None]*dab
            fam.append('d4'); F.append(np.r_[f1/10, ab+D4_L0**2]); Jl.append(np.vstack([J1/10, dab]))
        if s.vmin is not None: fam.append('vmin'); F.append((V*V).sum(1)-s.vmin**2); Jl.append(2*sum(V[:, i:i+1]*JV[i] for i in range(3)))
        if s.vfloor is not None:   # (t_a, t_b, v): |v| >= v on [t_a, t_b] only (a follow-through up to a cut)
            ta, tb, vf = s.vfloor; m = (s.ts >= ta) & (s.ts <= tb)
            fam.append('vfloor'); F.append(((V*V).sum(1)-vf**2)[m]); Jl.append((2*sum(V[:, i:i+1]*JV[i] for i in range(3)))[m])
        if s.ft is not None or s.entry is not None: P, JP = s._probe(z)
        if s.ft is not None:     # D1: v . u >= FT_VEPS and a . u >= -g on [0, t]; (p(t) - p(0)) . u >= d
            u = s.ft['u']; m = s.ts <= s.t0+s.ft['t']+1e-12
            vu = V@u; Jvu = sum(u[i]*JV[i] for i in range(3)); au = A@u; Jau = sum(u[i]*JA[i] for i in range(3))
            fam.append('ft_v'); F.append((vu-FT_VEPS)[m]*10); Jl.append(Jvu[m]*10)
            fam.append('ft_g'); F.append((au+s.ft['g'])[m]/10); Jl.append(Jau[m]/10)
            dp = (P[2]-P[0])@u; Jd = sum(u[i]*(JP[i][2]-JP[i][0]) for i in range(3))
            fam.append('ft_d'); F.append(np.array([dp-s.ft['d']])*100); Jl.append(Jd[None, :]*100)
        if s.entry is not None:  # D2: (p(D) - p(D - 1/FPS)) . u FPS >= e v_sw; (p(D) - p(D - RI_T)) . u >= ri
            u = s.entry['u']; i1 = len(s.pr)-2; i2 = len(s.pr)-1
            e = (P[1]-P[i1])@u*FPS/s.entry['v_sw']; Je = sum(u[i]*(JP[i][1]-JP[i][i1]) for i in range(3))*FPS/s.entry['v_sw']
            ri = (P[1]-P[i2])@u; Jr = sum(u[i]*(JP[i][1]-JP[i][i2]) for i in range(3))
            fam.append('entry'); F.append(np.array([e-s.entry['e'], ri-s.entry['ri']])*10); Jl.append(np.vstack([Je, Jr])*10)
        if s.yend is not None:   # a free end's y no lower than this
            Jy = s._J('y', 0, z, s.PB)[1]; yy = s.PB['y'][0][0][1]+s.PB['y'][0][1][1]@s._split(z)['y'][1]
            fam.append('yend'); F.append(np.array([yy-s.yend])*100); Jl.append(Jy[None, :]*100)
        if s.c['x'].free:
            cx = s.c['x']; mx = (s.ts >= cx.ta) & (s.ts <= cx.tb)
            Jx0 = s._J('x', 0, z)[mx]; Jx2 = s._J('x', 2, z)[mx]; x0 = x[0][mx]; x2 = x[2][mx]
            if s.axmax is not None: fam.append('axmax'); F.append((s.axmax-np.abs(x2))/10); Jl.append(-(np.sign(x2)[:, None]*Jx2)/10)
            fam.append('x_lo'); F.append((x0-s.xb[0])*100); Jl.append(100*Jx0); fam.append('x_hi'); F.append((s.xb[1]-x0)*100); Jl.append(-100*Jx0)
        s.fam = [(nm, len(f)) for nm, f in zip(fam, F)]
        return np.concatenate(F), np.vstack(Jl)

    def worst(s, z=None):
        """{family: its least constraint value (scaled; < 0 violated)} at z."""
        c = s.cons_all(s.z if z is None else z)[0]; out = {}; o = 0
        for nm, n in s.fam:
            if n: out[nm] = min(out.get(nm, np.inf), float(c[o:o+n].min()))
            o += n
        return out

    def f_obj(s, z):
        sig, peak = s.signals(z); g = np.zeros(len(z)); ns = len(s.ts); J2 = 0.0
        for k in s.c:
            j = sig[k][3]; J2 += (j*j).mean(); o, zk = s._split(z)[k]; g[o:o+len(zk)] += s.wj*2*(j@s.B[k][3][1])/ns
        if s.objective in ('peak', 'rho'):
            g[-1] += 1.0/10 if s.objective == 'peak' else 1.0
            return (peak/10 if s.objective == 'peak' else peak)+s.wj*J2, g
        A2 = 0.0
        for k in s.c:
            a = sig[k][2]; A2 += (a*a).mean(); o, zk = s._split(z)[k]; g[o:o+len(zk)] += 2*(a@s.B[k][2][1])/ns/100
        return A2/100+s.wj*J2, g

    def z0(s):
        z = []
        for k, c in s.c.items():
            for i in c.free: z.extend(np.array([c.guide(c.K[i+1], d) for d in range(3)], float)/SCALE)
            if c.free_p0: z.append(float(c.guide(c.ta, 0)))
            if c.free_p1: z.append(float(c.guide(c.tb, 0)))
        return np.r_[np.array(z, float), 50.0]

    def solve(s, z0=None, iters=300):
        z0 = s.z0() if z0 is None else np.array(z0, float)
        if len(z0) != s.nz(): raise ValueError(f'warm z has {len(z0)} values, the piece {s.nz()}')
        sig, _ = s.signals(z0)
        if s.objective == 'peak':
            A = np.c_[sig['x'][2], sig['y'][2], sig['h'][2]]; z0[-1] = float(np.sqrt((A*A).sum(1)).max())*1.05
        if s.objective == 'rho':
            V = np.c_[sig['x'][1], sig['y'][1], -sig['h'][1]]; z0[-1] = float(s._rho(V)[0].max())*1.05
        f0 = max(abs(s.f_obj(z0)[0]), 1e-9); lo = []; hi = []
        for c in s.c.values():
            for _ in c.free: lo += list(Z_BOUND[0]); hi += list(Z_BOUND[1])
            lo += [-8]*c.nends; hi += [8]*c.nends
        bounds = list(zip(lo+[0], hi+[PEAK_BOUND]))
        z0 = np.clip(z0, [b[0] for b in bounds], [b[1] for b in bounds])
        fun = lambda z: tuple(np.array(v)/f0 if i == 1 else v/f0 for i, v in enumerate(s.f_obj(z)))
        r = minimize(fun, z0, jac=True, method='SLSQP', bounds=bounds,
                     constraints=[dict(type='ineq', fun=lambda z: s.cons_all(z)[0], jac=lambda z: s.cons_all(z)[1])],
                     options=dict(maxiter=iters, ftol=1e-10))
        s.res = r; s.z = r.x; c = s.cons_all(r.x)[0]; s.viol = float(-min(c.min(), 0))
        return r


def guide_spline(points, bc0=None, bc1=None):
    t = np.array([p[0] for p in points], float); v = np.array([p[1] for p in points], float)
    cs = CubicSpline(t, v, bc_type=((1, bc0) if bc0 is not None else (2, 0.0), (1, bc1) if bc1 is not None else (2, 0.0)))
    return lambda tt, d=0: cs(tt, d)


def xfix_fn(parts):
    """parts: [(t0, t1, coefs or const)] covering the piece -> f(t, d)."""
    def f(t, d):
        t = np.asarray(t, float); out = np.zeros_like(t)
        for a, b, c in parts:
            m = (t >= a-1e-12) & (t <= b+1e-12)
            if np.ndim(c) == 0: out[m] = c if d == 0 else 0.0
            else: out[m] = peval(c, t[m]-a, d)
        return out
    return f


# ---- the pieces --------------------------------------------------------------------------------
class Piece:
    """A designed piece: its components, length, constraint keywords and stages."""
    def __init__(s, name, comps, D, kw, stages, meta=None):
        s.name = name; s.comps = comps; s.D = D; s.kw = kw; s.stages = stages; s.meta = dict(meta or {})


def staged(t_ap=None, rho=RHO_D, vmin=None, extra=None):
    a = dict(objective='acc', amax=None, d4=None); b = dict(objective='acc', t_ap=t_ap, rho=rho, vmin=vmin)
    c = dict(objective='peak', t_ap=t_ap, rho=rho, vmin=vmin)
    if extra: b.update(extra); c.update(extra)
    return [a, b, c]


def ft_spec(F, up, t=FT_T):
    """D1 on the exit of an up (rake04) or down (rake00) roll."""
    return dict(u=F.u(up), t=t, d=FT_DES, g=FT_G)


def entry_spec(F, up):
    """D2 on the entry of an up (rake00) or down (rake04) roll."""
    return dict(u=F.u(up), e=E_DES, ri=RI_DES, v_sw=F.V_SW)


def ap_weight(D, t_ap, pad=0.01, ramp=0.03):
    """1 away from the piece's ends and its apex window; ramps as (distance/ramp)^2 into the ends,
    where a C2 join to a sweep or a rest forces h' -> 0 as tau^2."""
    def w(t):
        t = np.asarray(t, float)
        return np.clip(t/ramp, 0, 1)**2*np.clip((D-t)/ramp, 0, 1)**2*np.clip((np.abs(t-t_ap)-pad)/0.02, 0, 1)**2
    return w


def clear_floor(D, exit_=False, entry=False):
    """The comb's h floor over a piece: from a sweep's end (exit_) or up to its start (entry), 0 for TC,
    then H_CLEAR, then H_FAR from FAR_S; H_FAR throughout a piece between rests."""
    def side(u):
        return H_CLEAR*np.clip((u-TC)/FLOOR_RAMP, 0, 1)+(H_FAR-H_CLEAR)*np.clip((u-FAR_S)/FLOOR_RAMP, 0, 1)
    def f(t):
        t = np.asarray(t, float); out = np.full_like(t, H_FAR)
        if exit_: out = np.minimum(out, side(t))
        if entry: out = np.minimum(out, side(D-t))
        return out
    return f


def strict(P, eps=EPS_H):
    """The piece with the strict-monotony margin about its apex (ruler 3)."""
    t_ap = P.stages[-1].get('t_ap'); kw = dict(P.kw)
    if eps: kw.update(ap_eps=eps, ap_w=ap_weight(P.meta.get('D_head', P.D), t_ap if t_ap is not None else -1, kw.get('ap_pad', .01)))
    P.kw = kw; P.meta.update(eps=eps); return P


def piece_runup(F, name, end, D, hA):
    """From rest at the apex (y free, h = hA) into the first string over D, running in along its tangent (D2)."""
    E = F.E; up = end == 0; ent = E['up0'] if up else E['dn0']
    Dx = E['D0'] if up else E['D4']; xs = F.X_LO if up else F.X_HI; cx = E['c_ru0'] if up else E['c_ru4']
    xf = xfix_fn([(0, D-Dx, xs), (D-Dx, D, cx)]); y1 = ent['y'][0]; s_ = 1.0 if up else -1.0
    yA = y1-s_*0.40
    gy = guide_spline([(0, yA), (0.5*D, yA+s_*0.08), (D, y1)], 0.0, ent['y'][1])
    gh = guide_spline([(0, hA), (0.5*D, 0.6*hA), (D-0.04, 0.05), (D, 0.0)], 0.0, 0.0)
    kn = [k*D/0.22 for k in [0.03, 0.06, 0.09, 0.12, 0.15]]+[D-k for k in (0.045, 0.025, 0.013, 0.006)]
    comps = {'x': fixed_comp(xf), 'y': Comp(0, D, (yA, 0, 0), ent['y'], kn, gy, free_p0=True),
             'h': Comp(0, D, (hA, 0, 0), (0, 0, 0), kn, gh)}
    return Piece(name, comps, D, dict(dt=2e-3, dense=[(D-0.06, D)], ap_pad=0.004, hmin=clear_floor(D, entry=True),
                                      entry=entry_spec(F, up), d4=dict(entry=up)), staged(t_ap=0.0))


def rest_mono(F, up):
    """D9 as a design constraint: the in-plane coordinate along the exit tangent (x, y) . u never gives back, so a rest
    after a sweep lies where its follow-through ends (round 2's park_hi settled 64 mm back down the strings, release_hi
    rocked 72 mm)."""
    u = F.u(up); return [(('x', 'y'), (float(u[0]), float(u[1])))]


def piece_follow(F, name, end, D=PARK_D, hP=H_P):
    """From the last string on along its tangent (D1), to rest at a park (y free, h = hP) where the follow-through
    ends: in-plane monotone (D9, rest_mono), so at the top the rest is the Y cap."""
    E = F.E; up = end == 4; ex = E['up1'] if up else E['dn1']; s_ = 1.0 if up else -1.0
    Dx = E['D4'] if up else E['D0']; xs = F.X_HI if up else F.X_LO; cx = E['c_ro4'] if up else E['c_ro0']
    xf = xfix_fn([(0, Dx, cx), (Dx, D, xs)]); y0 = ex['y'][0]; yG = y0+s_*0.30
    gy = guide_spline([(0, y0), (0.05, y0+s_*0.13), (0.12, y0+s_*0.23), (0.2, y0+s_*0.28), (D, yG)], ex['y'][1], 0.0)
    gh = guide_spline([(0, 0), (0.05, 0.04), (0.15, 0.6*hP), (D, hP)], 0.0, 0.0)
    kn = [k for k in [0.006, 0.012, 0.02, 0.03, 0.045, 0.065, 0.09, 0.13, 0.18, 0.25, 0.33, 0.4] if k < D-0.02]
    comps = {'x': fixed_comp(xf), 'y': Comp(0, D, ex['y'], (yG, 0, 0), kn, gy, free_p1=True),
             'h': Comp(0, D, (0, 0, 0), (hP, 0, 0), kn, gh)}
    return Piece(name, comps, D, dict(dt=3e-3, dense=[(0, 0.08)], hmin=clear_floor(D, exit_=True), ft=ft_spec(F, up), d4=dict(exit=up),
                                      mono=rest_mono(F, up)),
                 staged(t_ap=D))


def piece_loop(F, name, end, gap, vmin):
    """The pendulum's turn at an end: exit -> entry, never stopping (D1 out, D2 back in)."""
    E = F.E; top = end == 4; s_ = 1.0 if top else -1.0
    ex = E['up1'] if top else E['dn1']; en = E['dn0'] if top else E['up0']
    Dx = E['D4'] if top else E['D0']; xs = F.X_HI if top else F.X_LO
    cro = E['c_ro4'] if top else E['c_ro0']; cru = E['c_ru4'] if top else E['c_ru0']
    xf = xfix_fn([(0, Dx, cro), (Dx, gap-Dx, xs), (gap-Dx, gap, cru)]); y0 = ex['y'][0]
    gy = guide_spline([(0, y0), (0.05, y0+s_*0.13), (0.12, y0+s_*0.23), (0.2, y0+s_*0.29), (0.3, y0+s_*0.33), (0.45, y0+s_*0.36),
                       (0.6, y0+s_*0.33), (gap-0.2, y0+s_*0.27), (gap-0.1, y0+s_*0.17), (gap, y0)], ex['y'][1], en['y'][1])
    gh = guide_spline([(0, 0), (0.05, 0.04), (0.12, 0.10), (0.25, 0.25), (0.44, 0.35), (0.6, 0.25), (gap-0.12, 0.10),
                       (gap-0.05, 0.04), (gap, 0)], 0, 0)
    kn = [0.006, 0.012, 0.02, 0.03, 0.045, 0.065, 0.09, 0.13, 0.18, 0.25, 0.33, 0.41]
    kn = sorted(set(round(k, 6) for k in kn+[gap-k for k in kn[::-1]] if 0 < k < gap))
    comps = {'x': fixed_comp(xf), 'y': Comp(0, gap, ex['y'], en['y'], kn, gy), 'h': Comp(0, gap, (0, 0, 0), (0, 0, 0), kn, gh)}
    return Piece(name, comps, gap, dict(dt=3e-3, dense=[(0, 0.08), (gap-0.08, gap)], hmin=clear_floor(gap, True, True),
                                        ft=ft_spec(F, top), entry=entry_spec(F, not top), d4=dict(exit=top, entry=not top)),
                 staged(t_ap=gap/2, vmin=vmin), dict(apex=APEX_RANGE['turn']))


def piece_ghost(F, name, gap, go, arr, rho, nx=6):
    """down -> down: the rake00 exit (D1) -> the rake04 entry (D2), the carriage X_LO -> X_HI on [go, arr]."""
    E = F.E; ex = E['dn1']; en = E['dn0']; D0 = E['D0']; D4 = E['D4']; X_LO, X_HI = F.X_LO, F.X_HI
    xf = xfix_fn([(0, D0, E['c_ro0']), (D0, go, X_LO), (arr, gap-D4, X_HI), (gap-D4, gap, E['c_ru4'])])
    def xg(t, d=0, r=0.25):
        T = arr-go; L = X_HI-X_LO; u = np.clip((np.asarray(t, float)-go)/T, 0, 1); w1 = u/r; w2 = (1-u)/r
        if d == 0:
            s = np.where(u < r, r*(w1**3-w1**4/2), np.where(u <= 1-r, r/2+(u-r), (1-r)-r*(w2**3-w2**4/2)))/(1-r); return X_LO+L*s
        if d == 1:
            s = np.where(u < r, 3*w1**2-2*w1**3, np.where(u <= 1-r, 1.0, 3*w2**2-2*w2**3))/(1-r); return L*s/T
        s = np.where(u < r, (6*w1-6*w1**2)/r, np.where(u <= 1-r, 0.0, -(6*w2-6*w2**2)/r))/(1-r); return L*s/T**2
    kx = list(np.linspace(go, arr, nx+2)[1:-1])
    tap = 0.62
    gy = guide_spline([(0, F.YS[0]), (0.08, 0.98), (0.16, 0.95), (0.3, 1.25), (0.5, 1.95), (tap, 2.42), (gap-0.12, 2.38),
                       (gap, F.YS[-1])], ex['y'][1], en['y'][1])
    gh = guide_spline([(0, 0), (0.05, 0.04), (0.15, 0.09), (0.3, 0.15), (0.5, 0.2), (tap, 0.22), (gap-0.1, 0.08), (gap, 0)], 0, 0)
    kh = [k*gap/0.8876 for k in [0.015, 0.04, 0.07, 0.1, 0.14, 0.2, 0.27, 0.35, 0.43, 0.51, 0.59, 0.66, 0.72, 0.77, 0.81,
                                 0.84, 0.86, 0.875]]
    # formlab.rake cuts the 'ghost' tag at go: a knot there, or the cut splits a hermite 3 us from its knot
    # (a sliver whose boundary data ruler 6c rebuilds 4e-6 off its declared jerk)
    i = int(np.argmin(np.abs(np.asarray(kh)-go))); kh[i] = go
    comps = {'x': Comp(go, arr, (X_LO, 0, 0), (X_HI, 0, 0), kx, xg, xf),
             'y': Comp(0, gap, ex['y'], en['y'], kh, gy), 'h': Comp(0, gap, (0, 0, 0), (0, 0, 0), kh, gh)}
    lo, hi = APEX_RANGE['ghost']
    return Piece(name, comps, gap, dict(hmin=clear_floor(gap, True, True), axmax=AXMAX, dense=[(0, 0.08), (gap-0.07, gap)], dt=2e-3,
                                        ft=ft_spec(F, False, FT_T_GHOST), entry=entry_spec(F, False), d4=dict(exit=False, entry=False)),
                 staged(t_ap=tap, rho=rho, extra=dict(vfloor=(0.0, go, FT_V))), dict(apex=(lo, gap+hi), go=go, arr=arr))


def piece_backswing(F, name, D, p0, p1, x0, x1, Dc=None, tail=0.0, nk=8):
    """Rest -> rest: the head (y, h) from p0 to p1 along its chord, rising in h
    throughout (the wind-up); the carriage from x0 to x1 over its last Dc s
    (the head may leave before the carriage's go), monotone. tail = 0: the
    carriage arrives with the head (a ruler 22 sync leg, 'travel'); tail > 0:
    it runs on that long under the head's apex hold ('poise', the head at rest
    at p1). Round 2's return did (0.10 s, its 0.8 s lead left 0.52 s for
    1.08 m); D7 holds the apex still now and the score's announce_lead gives
    the crossing its window, so both backswings pass 0. The library's D is
    the head's."""
    kn = list(np.linspace(0, D, nk+2)[1:-1]); Dx = D+tail
    def g345(a, b, t0=0.0, t1=D):
        def f(t, d=0):
            T = t1-t0; u = np.clip((np.asarray(t, float)-t0)/T, 0, 1)
            return (a if d == 0 else 0)+(b-a)*[10*u**3-15*u**4+6*u**5, (30*u**2-60*u**3+30*u**4)/T, (60*u-180*u**2+120*u**3)/T**2][d]
        return f
    def const(v): return lambda t, d: np.full_like(np.asarray(t, float), v if d == 0 else 0.0)
    moves = abs(x1-x0) > 1e-12
    c0 = D-(Dc if Dc is not None else D)
    if moves:
        kx = list(np.linspace(c0, Dx, nk+2)[1:-1])
        cx = Comp(c0, Dx, (x0, 0, 0), (x1, 0, 0), kx, g345(x0, x1, c0, Dx), const(x0))
    else: cx = fixed_comp(const(x0))
    comps = {'x': cx, 'y': Comp(0, D, (p0[0], 0, 0), (p1[0], 0, 0), kn, g345(p0[0], p1[0]), const(p1[0])),
             'h': Comp(0, D, (p0[1], 0, 0), (p1[1], 0, 0), kn, g345(p0[1], p1[1]), const(p1[1]))}
    xb = (min(x0, x1), max(x0, x1)) if moves else (F.X_LO, F.X_HI)
    dy = p1[0]-p0[0]; dz = -(p1[1]-p0[1]); n_ = np.hypot(dy, dz)
    mono = [(('y', 'h'), (dy/n_, -dz/n_))]+([(('x',), (np.sign(x1-x0),))] if moves else [])
    return Piece(name, comps, Dx, dict(dt=2e-3, axmax=AXMAX, xb=xb, ap_pad=0.004, mono=mono, hmin=clear_floor(Dx),
                                       line=((p0[0], p0[1]), (dy/n_, dz/n_))), staged(t_ap=D), dict(c0=c0, D_head=D))


def piece_release_lo(F, name, yP=REL_Y_LO, hP=REL_H, D=REL_D):
    """After a down roll (the rake00 exit, -y): on along the tangent (D1), then turn and rise to rest at
    a park UP the strings (ruler 24's release, <= 45 deg off +y), h rising throughout (D6). Not in-plane
    monotone (D9): the exit tangent u = (-0.221, -0.975) runs down the strings, and every displacement
    ruler 24 accepts from the turn (within 45 deg of +y) has u . d <= cos(122.2 deg) |d| = -0.533 |d|, so
    no release meets both (this one gives back 618 mm); reported, not designed around (PLAYERS M2 round 3)."""
    E = F.E; ex = E['dn1']; Dx = E['D0']; xf = xfix_fn([(0, Dx, E['c_ro0']), (Dx, D, F.X_LO)]); y0 = ex['y'][0]
    gy = guide_spline([(0, y0), (0.05, y0-0.13), (0.12, y0-0.22), (0.22, y0-0.26), (0.4, 0.5*(y0+yP)-0.1), (D, yP)], ex['y'][1], 0.0)
    gh = guide_spline([(0, 0), (0.05, 0.04), (0.2, 0.6*hP), (D, hP)], 0.0, 0.0)
    kn = [k for k in [0.006, 0.012, 0.02, 0.03, 0.045, 0.065, 0.09, 0.13, 0.18, 0.25, 0.33, 0.42, 0.52, 0.62] if k < D-0.03]
    comps = {'x': fixed_comp(xf), 'y': Comp(0, D, ex['y'], (yP, 0, 0), kn, gy), 'h': Comp(0, D, (0, 0, 0), (hP, 0, 0), kn, gh)}
    return Piece(name, comps, D, dict(dt=3e-3, dense=[(0, 0.08)], hmin=clear_floor(D, exit_=True), ft=ft_spec(F, False), d4=dict(exit=False)),
                 staged(t_ap=D))


def piece_release_hi(F, name, yP, hP, D):
    """After an up roll (the rake04 exit) at a phrase end: on up the strings along the tangent (D1),
    to rest at the top of the lift (y >= yP, hP), h rising throughout (D6; ruler 24), in-plane monotone (D9)."""
    E = F.E; ex = E['up1']; Dx = E['D4']; xf = xfix_fn([(0, Dx, E['c_ro4']), (Dx, D, F.X_HI)]); y0 = ex['y'][0]
    gy = guide_spline([(0, y0), (0.05, y0+0.13), (0.12, y0+0.21), (0.2, y0+0.27), (D, yP+0.05)], ex['y'][1], 0.0)
    gh = guide_spline([(0, 0), (0.05, 0.04), (0.15, 0.10), (0.35, 0.8*hP), (D, hP)], 0.0, 0.0)
    kn = [k for k in [0.006, 0.012, 0.02, 0.03, 0.045, 0.065, 0.09, 0.13, 0.18, 0.24, 0.31, 0.39, 0.48, 0.58] if k < D-0.03]
    comps = {'x': fixed_comp(xf), 'y': Comp(0, D, ex['y'], (yP+0.05, 0, 0), kn, gy, free_p1=True),
             'h': Comp(0, D, (0, 0, 0), (hP, 0, 0), kn, gh)}
    return Piece(name, comps, D, dict(dt=3e-3, dense=[(0, 0.08)], hmin=clear_floor(D, exit_=True), ft=ft_spec(F, True), yend=yP,
                                      d4=dict(exit=True), mono=rest_mono(F, True)),
                 staged(t_ap=D))


# ---- solving and the library -----------------------------------------------------------------
def solve(F, P, warm=None, log=print):
    """The piece's staged design (cold), or its final stage from `warm` z. The
    result is the best of SLSQP's stop, RESTARTS re-runs from it and the warm
    z itself, judged on the LIMITS (every constraint family but the peak
    variable's epigraph, which only prices the objective)."""
    t0 = time.time(); z = None if warm is None else np.array(warm, float)
    stages = P.stages if warm is None else P.stages[-1:]; iters = ITERS if warm is None else ITERS[-1:]
    for st, it in zip(stages, iters):
        d = Design(F, P.comps, 0, P.D, **{**P.kw, **st}); d.solve(z0=z, iters=it); z = d.z
    def lim(z): return max(0.0, -min([v for k, v in d.worst(z).items() if k != 'peak'], default=0.0))
    best = [(lim(d.z), d.z.copy(), str(d.res.message))]; nit = int(d.res.nit)
    if warm is not None and len(warm) == d.nz(): best.append((lim(np.array(warm, float)), np.array(warm, float), 'warm start kept'))
    for i in range(RESTARTS):
        b = min(best, key=lambda c: c[0])
        if b[0] <= VIOL_GOAL: break
        z = b[1]
        if i % 2 and len(P.stages) > 1:   # every other restart re-enters through the constrained acc stage (SLSQP stalls on the epigraph)
            e = Design(F, P.comps, 0, P.D, **{**P.kw, **P.stages[-2]}); e.solve(z0=z, iters=ITERS[-1]); nit += int(e.res.nit); z = e.z
        d.solve(z0=z, iters=ITERS[-1]); nit += int(d.res.nit); best.append((lim(d.z), d.z.copy(), str(d.res.message)))
    viol, d.z, msg = min(best, key=lambda c: c[0]); d.viol = viol
    d.P = P; d.info = dict(msg=msg, nit=nit, secs=round(time.time()-t0, 1), viol=viol)
    w = {k: v for k, v in d.worst().items() if v < 0}
    log(f'  {P.name:<12} {msg} ({nit} it, {d.info["secs"]} s), limits violated by {viol:.2e} {w if w else ""}')
    if viol > VIOL_MAX: raise SystemExit(f'{P.name}: the design violates its limits by {viol:.2e} (> {VIOL_MAX:g}): {w}')
    return d


def state(d, k, t):
    s, _ = d.signals(d.z, np.array([float(t)])); return tuple(float(s[k][i][0]) for i in range(3))


def frame_turns(P, lim, phases=12):
    """D4 on a sampled path P(t) (t -> (n, 3)) over [a, b]: the largest angle (deg) between consecutive
    1/FPS steps both >= lim long, over `phases` frame phases."""
    def worst(a, b):
        out = 0.0
        for ph in np.arange(phases)/phases/FPS:
            tf = np.arange(a+ph, b+1e-12, 1/FPS); Q = np.diff(P(tf), axis=0); L = np.linalg.norm(Q, axis=1)
            ok = (L[:-1] >= lim) & (L[1:] >= lim)
            if ok.any():
                c = (Q[:-1]*Q[1:]).sum(1)/np.maximum(L[:-1]*L[1:], 1e-12)
                out = max(out, float(np.degrees(np.arccos(np.clip(c[ok], -1, 1))).max()))
        return out
    return worst


def measure(F, d, n=4001):
    """The designed piece on a fine grid: peak tip |a| (g), max instantaneous rho, min speed, the x, y and h
    ranges; on an exit D1 (FT, its turn-back time, the peak tangential deceleration); on an entry D2 (E, RI);
    D4 (the largest frame turn within 0.25 s of the sweep, sweep frames included, over 12 frame phases)."""
    D = d.P.D; ts = np.linspace(0, D, n); sig, _ = d.signals(d.z, ts); x, y, h = sig['x'], sig['y'], sig['h']
    V = np.c_[x[1], y[1], -h[1]]; A = np.c_[x[2], y[2], -h[2]]
    out = dict(a_g=float(np.linalg.norm(A, axis=1).max()/G), rho=float(d._rho(V)[0].max()), v_min=float(np.linalg.norm(V, axis=1).min()),
               x=(float(x[0].min()), float(x[0].max())), y=(float(y[0].min()), float(y[0].max())),
               h=(float(h[0].min()), float(h[0].max())))
    def piece_p(t):
        s, _ = d.signals(d.z, np.atleast_1d(t)); return np.c_[s['x'][0], s['y'][0], -s['h'][0]]
    T_sw = float(F.sweeps[True]['ts'][-1]-F.sweeps[True]['ts'][0]); lim = 0.25*F.V_SW/FPS
    if d.ft is not None:
        u = d.ft['u']; up = bool(u[1] > 0); vu = V@u; k = int(np.argmax(vu[1:] <= 0))+1 if (vu[1:] <= 0).any() else n-1
        disp = (np.c_[x[0], y[0], -h[0]]-np.array([x[0][0], y[0][0], -h[0][0]]))@u
        m = ts <= min(ts[k], d.ft['t'])
        def P_ex(t):
            t = np.atleast_1d(t); return np.where((t < 0)[:, None], F.sweep(up, T_sw+np.minimum(t, 0)), piece_p(np.clip(t, 0, D)))
        out.update(FT=float(disp[:k+1].max()), t_rev=float(ts[k]), ft_decel_g=float(-(A[m]@u).min()/G),
                   turn_exit=frame_turns(P_ex, lim)(-T_sw, min(0.25, D)))
    if d.entry is not None:
        u = d.entry['u']; up = bool(u[1] > 0); P_ = lambda t: piece_p(np.atleast_1d(t))
        p1 = P_(D)[0]; out.update(E=float((p1-P_(D-1/FPS)[0])@u*FPS/F.V_SW), RI=float((p1-P_(max(0.0, D-RI_T))[0])@u))
        def P_en(t):
            t = np.atleast_1d(t); return np.where((t > D)[:, None], F.sweep(up, np.maximum(t, D)-D), piece_p(np.clip(t, 0, D)))
        out['turn_entry'] = frame_turns(P_en, lim)(max(0.0, D-0.25), D+T_sw)
    return out


def design(F, warm=None, log=print, only=None):
    """Every piece formlab.rake plays, in dependency order (an apex or a park
    feeds the backswings that end or start there) -> the library dict."""
    W = warm or {}; out = {}
    def go(P, key):
        if only and P.name not in only and key not in only: return None
        out[P.name] = solve(F, P, W.get(key, {}).get('z'), log); return out[P.name]
    ru_lo = go(strict(piece_runup(F, 'runup_lo', 0, RU_LO, H_A0)), 'runup0')
    ru_lo_b = go(strict(piece_runup(F, 'runup_lo_b', 0, RU_LO_B, H_A0B)), 'runup0b')
    go(strict(piece_runup(F, 'runup_hi', 4, RU_HI, H_A4)), 'runup4')
    park_hi = go(strict(piece_follow(F, 'park_hi', 4)), 'follow4')
    go(strict(piece_follow(F, 'park_lo', 0)), 'follow0')
    go(strict(piece_release_lo(F, 'release_lo')), 'release0')
    go(strict(piece_release_hi(F, 'release_hi', **REL4)), 'release4')
    go(strict(piece_loop(F, 'turn_hi', 4, F.turn_gap, LOOP_VMIN['hi'])), 'loop4')
    go(strict(piece_loop(F, 'turn_lo', 0, F.turn_gap, LOOP_VMIN['lo'])), 'loop0')
    gh = F.ghost
    if warm is None or 'ghost' not in W:   # cold: the plain ghost first, then the strict one from it (the study's order)
        if not only or 'ghost_down' in only or 'ghost' in only:
            plain = solve(F, piece_ghost(F, 'ghost_plain', gh['gap'], gh['go'], gh['arr'], RHO_GHOST), None, log)
            W = dict(W, ghost=dict(z=list(plain.z)))
    go(strict(piece_ghost(F, 'ghost_down', gh['gap'], gh['go'], gh['arr'], RHO_GHOST)), 'ghost')
    if ru_lo is not None and park_hi is not None and ru_lo_b is not None:
        A0 = (state(ru_lo, 'y', 0)[0], H_A0); A0B = (state(ru_lo_b, 'y', 0)[0], H_A0B); P4 = (state(park_hi, 'y', PARK_D)[0], H_P)
        # the carriage's share of a backswing: the score's window, from its go to the apex hold's start (Frame.cross; A24)
        go(strict(piece_backswing(F, 'home_up', max(BS_HOME, F.cross['home_up']), F.g.rest, A0, F.g.xh, F.X_LO, F.cross['home_up'])), 'home_up')
        go(strict(piece_backswing(F, 'return_up', max(BS_RETURN, F.cross['return_up']), P4, A0B, F.X_HI, F.X_LO, F.cross['return_up'])),
           'return_up')
    nxt = dict(home_up='runup_lo', return_up='runup_lo_b')
    lib = dict(version=1, fingerprint=F.fingerprint(), homing=HOMING, pieces={})
    for name, d in out.items():
        St, _ = d.states(d.z); P = d.P
        assert np.array_equal(d.c['y'].K, d.c['h'].K), f'{name}: y and h knots differ'
        pc = dict(D=float(P.meta.get('D_head', P.D)), y=dict(K=d.c['y'].K.tolist(), S=np.asarray(St['y']).tolist()),
                  h=dict(K=d.c['h'].K.tolist(), S=np.asarray(St['h']).tolist()), info=d.info, measured=measure(F, d))
        if d.c['x'].free: pc['x'] = dict(K=d.c['x'].K.tolist(), S=np.asarray(St['x']).tolist())
        if 'apex' in P.meta: pc['apex'] = list(P.meta['apex'])
        if name in nxt: pc['next'] = nxt[name]
        lib['pieces'][name] = pc
    return lib


def check(lib, assets=('chamber', 'expanded')):
    """Does the library's fingerprint match each asset's live geometry? -> [(asset, key, diff)] over LIB_TOL."""
    bad = []
    for a in assets:
        F = Frame(a); live = F.fingerprint()
        for k, v in live.items():
            dv = RK._diff(v, lib['fingerprint'].get(k, math.inf))
            if dv > RK.LIB_TOL: bad.append((a, k, dv))
    return bad


# ---- the homing poses (ruler 22 home over every rail the search can accept) -----------------------
def arm_joints(cfg, tips):
    """Rig.pose's IK for tool points `tips` (N, 3) on a rail cfg (root above the tip, bend 'back') ->
    (shoulder, elbow, |wrist - root|) as tools/players/r_motion.joint_series reads them."""
    root = np.c_[tips[:, 0], np.full(len(tips), cfg['root_y']), np.full(len(tips), cfg['root_z'])]
    wrist = tips+np.asarray(cfg['wrist_offset'], float); delta = wrist-root; dist = np.linalg.norm(delta, axis=1)
    l1, l2 = float(cfg['l1']), float(cfg['l2']); d = np.clip(dist, abs(l1-l2)+1e-5, l1+l2-1e-5); dirn = delta/dist[:, None]
    along = (l1*l1-l2*l2+d*d)/(2*d); hint = np.array([0, 0, -1.0]); bend = hint-dirn*(dirn@hint)[:, None]
    bn = np.linalg.norm(bend, axis=1); bend = np.where(bn[:, None] < np.sqrt(1e-5), hint, bend/np.maximum(bn, 1e-12)[:, None])
    elbow = root+dirn*along[:, None]+bend*np.sqrt(np.maximum(0, l1*l1-along*along))[:, None]
    u = elbow-root; f = wrist-elbow
    cosel = -(u*f).sum(1)/(np.linalg.norm(u, axis=1)*np.linalg.norm(f, axis=1))
    return np.unwrap(np.arctan2(u[:, 1], u[:, 2])), np.arccos(np.clip(cosel, -1, 1)), dist


def homing_rails(asset, log=print):
    """The rails the search can give the rake: layout_search.candidates that evaluate_arm accepts on this
    motion with worst >= 0 (the root y 2.75 rows fold the links through each other, -56 mm and worse),
    each with its joint spans over ruler 16's points (r_motion._span_points: the reach strings at u
    0.05-0.95, contact and hover; the shoulder's taken about its circular mean, as ruler 22 does) and the
    |wrist - root| range of the motion after the homing -> (rails, (x_home, z_c, rest))."""
    paths = core.ASSETS[asset]; lay = json.loads(Path(paths['manifest']).read_text()); sc = json.loads(Path(paths['score']).read_text())
    rig = Rig(sc, lay); act = rig.acts[AID]; mid = lay['arms'][AID]['mid']; arm = rig._rake_input(AID); g = RK.Geometry(arm)
    mech = next(m for m in sc['instrument']['mechanisms'] if m['id'] == mid)
    pz = float(np.mean([s['a'][2] for s in lay['strings'].values() if s['mid'] == mid]))
    times = np.arange(-30, int(float(sc['total_s'])*30)+1)/30; boxes = LS.scene_boxes(lay); lift = rig.hover(AID); pts = []
    for sid in act.get('reach', [act['home']]):
        a, b = (np.asarray(lay['strings'][sid][k], float) for k in ('a', 'b'))
        for u in np.linspace(.05, .95, 19): pts += [a*(1-u)+b*u, a*(1-u)+b*u+lift]
    pts = np.array(pts); t_h = max(leg[1] for leg in arm.homing)
    path = np.array([rig.path_at(AID, float(t)) for t in np.arange(t_h, float(sc['total_s']), 0.01)])
    rails = []
    for cfg in LS.candidates(mech, lay):
        ev = LS.evaluate_arm(rig, AID, cfg, times, boxes=boxes, string_plane_z=pz)
        if ev is None or ev['worst'] < 0: continue
        sh, el, _ = arm_joints(cfg, pts); ref = math.atan2(np.sin(sh).mean(), np.cos(sh).mean())
        sh = ref+np.angle(np.exp(1j*(sh-ref))); d = arm_joints(cfg, path)[2]
        rails.append(dict(cfg=cfg, span=(float(np.ptp(sh)), float(np.ptp(el))), dlo=float(d.min()), dhi=float(d.max()), worst=ev['worst']))
        log(f"  rail y {cfg['root_y']:.2f} z {cfg['root_z']:+.3f} l {cfg['l1']:.2f}: worst {ev['worst']*1e3:.1f} mm")
    return rails, (g.xh, g.zc, g.rest)


def homing_eval(rails, frame, poses):
    """The homing through `poses` (dict elbow=[(y, h)...], shoulder=[...]) from and back to the rest:
    -> (least swept share over every rail and joint, least envelope margin (m), chords per window (m))."""
    xh, zc, rest = frame; el = [rest]+[tuple(p) for p in poses['elbow']]; sh = [el[-1]]+[tuple(p) for p in poses['shoulder']]+[rest]
    seq = el+sh[1:]; u = np.linspace(0, 1, 41)
    tips = np.vstack([np.c_[np.full(41, xh), A[0]+(B[0]-A[0])*u, zc-(A[1]+(B[1]-A[1])*u)] for A, B in zip(seq, seq[1:])])
    ch = lambda q: sum(math.hypot(B[0]-A[0], B[1]-A[1]) for A, B in zip(q, q[1:]))
    share, env = math.inf, math.inf
    for r in rails:
        s, e, d = arm_joints(r['cfg'], tips)
        share = min(share, float(np.ptp(s))/r['span'][0], float(np.ptp(e))/r['span'][1])
        env = min(env, r['dhi']-float(d.max()), float(d.min())-max(r['dlo'], .30))
    return share, env, dict(elbow=ch(el), shoulder=ch(sh))


def homing_budget():
    """m: a window's chord at HOME_SERVO_V peak (3-4-5: peak = V345 mean)."""
    mt = RK.motion_timing; return {w: mt.HOME_SERVO_V*T/mt.V345 for w, T in mt.HOME_SERVO_JOINT_S.items()}


def homing_search(rails, frame, ne=3, ns=2, seed=1, log=print):
    """Differential evolution over ne elbow and ns shoulder poses: the least swept share, the envelope
    (>= HOME_ENV) and the chord budgets as penalties -> HOMING-shaped dict."""
    from scipy.optimize import differential_evolution
    B = homing_budget()
    def unpack(z): p = [(float(z[2*i]), float(z[2*i+1])) for i in range(ne+ns)]; return dict(elbow=p[:ne], shoulder=p[ne:])
    def f(z):
        share, env, ch = homing_eval(rails, frame, unpack(z))
        return -share+10*sum(max(0.0, ch[w]-B[w]) for w in B)+10*max(0.0, HOME_ENV-env)
    r = differential_evolution(f, [HOME_Y, HOME_H]*(ne+ns), seed=seed, maxiter=300, popsize=25, tol=1e-6, polish=True)
    return unpack(r.x)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    ap.add_argument('--asset', default='chamber'); ap.add_argument('--warm'); ap.add_argument('--check', action='store_true')
    ap.add_argument('--out', default=str(ROOT/'formlab'/RK.LIB))
    ap.add_argument('--homing', action='store_true')         # check HOMING on every acceptable rail, then write it into --out
    ap.add_argument('--homing-search', action='store_true')  # ...or search for poses (prints them; HOMING is set by hand)
    a = ap.parse_args()
    if a.homing or a.homing_search:
        rails, frame = homing_rails(a.asset); B = homing_budget()
        poses = homing_search(rails, frame) if a.homing_search else HOMING
        share, env, ch = homing_eval(rails, frame, poses)
        print(f'{len(rails)} rails: least swept share {share:.3f} (ruler 22: {HOME_SWEEP}), envelope {env*1e3:.1f} mm (>= {HOME_ENV*1e3:.0f}), '
              f'chords elbow {ch["elbow"]:.3f} / {B["elbow"]:.3f} m, shoulder {ch["shoulder"]:.3f} / {B["shoulder"]:.3f} m')
        if a.homing_search: print('poses', json.dumps(poses)); return
        if share < HOME_SWEEP or env < HOME_ENV or any(ch[w] > B[w]+1e-9 for w in B): raise SystemExit('HOMING misses: not written')
        lib = json.loads(Path(a.out).read_text()); lib['homing'] = HOMING
        Path(a.out).write_text(json.dumps(lib, indent=0)+'\n'); print('wrote the homing poses into', a.out); return
    if a.check:
        bad = check(json.loads(Path(a.out).read_text()))
        for b in bad: print('  MISMATCH', *b)
        print('library fits both assets' if not bad else f'{len(bad)} mismatches'); sys.exit(1 if bad else 0)
    F = Frame(a.asset)
    print(f'rail [{F.X_LO:.9f}, {F.X_HI:.9f}]  runs D0 {F.E["D0"]:.4f} D4 {F.E["D4"]:.4f}  turn gap {F.turn_gap:.12f}  ghost {F.ghost}')
    lib = design(F, json.loads(Path(a.warm).read_text()) if a.warm else None)
    other = [b for b in check(lib, [x for x in ('chamber', 'expanded') if x != a.asset])]
    if other: raise SystemExit(f'the other asset does not fit this design: {other}')
    Path(a.out).write_text(json.dumps(lib, indent=0)+'\n'); print('wrote', a.out)


if __name__ == '__main__':
    main()

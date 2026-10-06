"""The rake's stroke (PLAYERS M2, T5): the comb's whole path as declared
segments on the servo's two channels, planned from plain data the Rig hands
over. numpy only, no import of formlab.rig (the rig imports this), so
Blender can run it. The surface is formlab/servo.py's ServoStroke:

    p(t) = (x(t), y_c, z_c) + h(t) n + (0, h_y(t), 0)

* 'carriage' x(t): the carriage on its leadscrew; y_c, z_c are the home
  contact's and constant (the comb crosses the strings on the head's h_y).
* 'head' (h, h_y): h along n, the clearance's unit vector ((0, 0, -1): the
  comb comes at the string plane from behind), and h_y across the strings.

A roll (one score event: the five strings rake00 -> rake04 'up', or back
'down', at motion_timing.rake_onsets) is a SWEEP: four quintic hermites a
channel through the five contacts at their own times with h = 0 (the comb in
the string plane), entering and leaving at SWEEP_V_END, their knot states the
C2 clamped cubic's but for the knot before the x_hi contact, whose velocity
turns onto the chord into that contact (SWEEP_TUCK: the outer string's eyelet).
The comb never stops at a string: the carriage runs out into the rail's
overtravel past the last string (A19) and runs up out of it into the next
sweep, each the quintic of least peak |x''| (run_d), and between rolls the
head flies DESIGNED pieces: piecewise quintic hermites in (y, h) (and in x
where the carriage crosses under them) solved offline by tools/rake_design.py
in tool space, against physical limits and the shared M2 definitions (the
follow-through on along the exit tangent, the run-in along the entry tangent,
the tool's |a|, the comb's rho, carriage g, strict rise and fall about an
apex, the comb clear of the strings) and kept in formlab/rake_pieces.json, the
library, with the geometry they were solved for (its fingerprint: a mismatch
is an issue and a plain fallback, never a silent reuse). They depend on no
arm cfg (no root, links or reach cut): the rail plan (formlab/layout_search)
chooses the rake's root and links after them, so the arm reaches what the
comb does. Their interior knot states are the library's; their ends are this
plan's live states, so every join is C2 to the last bit.

  first roll   the announcement from home: the designed backswing home_up
               (a library piece, quintic hermites in (y, h) and x, not a
               3-4-5: 'wind-up'; the carriage home -> the rail end under it
               from the score's go, 'travel'), the apex hold ('poise',
               HOLD_MIN), the run-up ('stroke'); the head leaves before the
               carriage;
  long gap     the exit piece (a park; a release up the strings at a phrase
               end, ruler 24), held; then, at the same end, a 3-4-5 backswing
               (BACKSWING_S: the one 3-4-5 backswing) to the next run-up's
               apex, the hold, the run-up; to the OTHER end, the designed
               return backswing return_up (a library piece like home_up) that
               carries the carriage across under it from the score's go to
               the apex hold's start ('travel': the score's announce_lead
               charges the crossing, motion_timing, A24), so the hold is
               still;
  short gap    the pendulum: at the same end a teardrop turn that never stops
               ('follow-through', then 'stroke' from its apex); to the other
               end (down -> down) the ghost pass: the comb swings out while the
               carriage crosses under it in [t_free, t - approach];
  the end      the last release, held to the score's last onset, then home
               with it (END_S, 3-4-5 'travel').

The homing sweep (the score's cue, motion_timing.servo_home_legs): x home ->
lo -> hi -> home as 3-4-5 'home' legs (travel ids home-x0..2), then in the
'elbow' and 'shoulder' windows the head through the library's homing poses,
3-4-5 'home' legs (extra joint) timed by chord length (equal peak speed).
Ruler 22 reads every one as a sync target. The poses are tool space too:
chosen (tools/rake_design.py --homing) so that every rail the search can
accept sweeps >= 0.8 of its shoulder's and elbow's spans (ruler 22 home),
inside that rail's own reach over the rest of the motion.

`plan_rake(RakeIn) -> RakeStroke` is the whole interface. A rake declares
no prep function (RakeStroke.prep is None): its apex follows the gap's kind
(the pendulum turn's, an announcement's), not (a', IOI) alone."""
import json, math
from dataclasses import dataclass, field
from pathlib import Path
import numpy as np
try:
    from . import stroke as _st
    from . import servo as _sv
    from . import clearance as _cl
except ImportError:
    import stroke as _st
    import servo as _sv
    import clearance as _cl

motion_timing = _st.motion_timing

LAWS = ('quintic hermite', '3-4-5', 'hold')    # the rake's vocabulary (all in segments.LAWS)
SWEEP_V_END = (0.639, 2.814)    # m/s: (x', y') at both ends of an UP sweep (the A13 roll's optimum with RAKE_ONSET_FRACTIONS); down: negated
# the knot before the x_hi contact turns its (x', y') onto the chord into (or out of) that contact, and this share of the way on
# toward the end slope; speed and a kept (still C2: a knot state is shared by both its spans). The end slope (77 deg) is steeper
# than the contact line (48 deg): the x_lo end leaves above the line, but into (or out of) the x_hi contact the clamped cubic (its
# knot at 40 deg) tucks under it, toward the strings' feet, where the outer, shortest string's eyelet sits (its contact 168 mm
# above its foot at pick 0.28): 18.5 mm of tool clearance against tools/test_eyelets' 20. On the chord (0) it reads 23.0 mm, the
# carriage's |x''| 2.90 g in the sweep (ruler 14: 3; the cubic's 2.87), speed ratio 1.155 (1.2), |a| 3.99 g. A share on toward
# the end slope buys clearance with the carriage's x'' (its x' falls while the contacts' x are fixed): 0.1 reads 24.7 mm at
# 3.00 g, a quarter 27.0 mm at 3.21 g, which ruler 14 fails. The turned v under the kept a shimmies the xy path: 5 curvature
# reversals a roll (the cubic's 3), at most 5.7 mm lateral and 7.4 deg a frame, inside D3/D4, so a is kept, not turned with v
SWEEP_TUCK = 0.0
RUN_D = (0.02, 0.12, 1e-4)      # s: the run-out/run-up durations searched (np.arange): the least peak |x''| that never runs back past its stop
RUN_SAMPLES = 801               # samples a run-out candidate's |x''| and monotony are judged on
RAIL_SPARE = 1e-6               # m: the carriage stops this short of the overtravel, so A19 (tools/test_gantry.py) is never a float coin toss
# m: how far the carriage may run past reach_x: the rail head's inner face (rail_over + head_inset) less the pin heads (default_layers
# pin_x, what test_gantry's probe measures) and the gantry's margin, less RAIL_SPARE (0.0146 m less 1 um today)
OVER = _cl.GANTRY['rail_over']+_cl.GANTRY['head_inset']-_cl.default_layers()['pin_x']-_cl.GANTRY['margin']-RAIL_SPARE
# s: a roll after this long free of rake contact is announced (ruler 14's ANNOUNCE_GAP mirrors it), and an unplanned roll's head
# (fallback) leaves its rest no earlier than this before its first string. No longer the announced carriage's lead (round 2's
# 0.8 s left the return 0.52 s and its carriage ran on under the apex hold): the score charges a crossing
# motion_timing.announce_lead from its distance, and the designed backswings carry the carriage from that go to the hold
ANNOUNCE_S = 0.8
BACKSWING_S = 0.5               # s: the 3-4-5 backswing park -> apex at the same end (ruler 3: W >= 6 frames; D5: >= 0.5 s); home_up and return_up are designed
HOLD_MIN = motion_timing.RAKE_HOLD_S  # s: an announced roll's head holds its apex this long ('poise') before the run-up (D5: >= 0.1 s)
END_S = 0.8                     # s: the comb's return home from its last release, with the score's last onset
FALLBACK_S = 1.0                # s: an unplanned release (no library) comes to rest at home over this
APEX_GRID = 1e-3                # s: ruler 3's sample step inside a declared segment (r_motion._grid)
APEX_SNAP = 1e-5                # s: a 'stroke' cut this close to a grid sample goes ON it (stroke_cut: ruler 3's sub-us still interval)
APEX_SCAN = 2001                # samples the designed h' is scanned on for its apex before bisecting
APEX_BISECT = 60                # bisections of that apex
GAP_TOL = 1e-6                  # s: a designed piece fits a gap (or a window) this close to the one it was solved for
LIB = 'rake_pieces.json'        # the designed pieces (tools/rake_design.py), beside this file
LIB_TOL = 1e-9                  # the library's fingerprint against the live geometry (m, m/s, m/s^2, s)
JERK_PAD = 1e-9                 # relative: a declared jerk sits this far above its exact peak (ruler 6c samples the closed form)


# ---- the plan's inputs and records --------------------------------------------------------------
@dataclass
class RollIn:
    """One scored roll (a rake event), as the Rig knows it."""
    t: float                    # its first string's contact (the event's t)
    times: list                 # each string's contact time, first to last (motion_timing.string_times)
    points: list                # each string's contact point (x, y, z), in the roll's order
    a: object                   # a' (core.Contact.a; Rig._a_norm), None = 1.0
    go: float                   # the score's t_move: the carriage's earliest start toward it
    t_free: float               # the score's t_free: the strings are free again (the last contact + recover)
    event: int = -1             # score event index
    amp: float = 1.0


@dataclass
class RakeIn:
    """One rake arm's plan inputs (Rig._rake_input)."""
    rolls: list                 # [RollIn], any order
    home: tuple                 # the home string's contact (x, y, z): the carriage's rest, y_c and z_c
    hover: tuple                # Rig.clearance(aid): the comb's rest offset from a contact ((0, 0, -0.22))
    reach: list                 # the reach strings' contacts: the rail window (x) the overtravel is measured from
    homing: list = field(default_factory=list)   # [(t0, t1, what, a, b)]: Rig.homes(aid)[0][4] (servo_home_legs)
    t_return: float = -math.inf # the score's last onset: the comb goes home with it
    approach: float = .15       # the actuator's approach_s: the carriage stands still on the rail end this long before a roll
    recover: float = .10        # the actuator's recover_s: the strings are free this long after a roll's last contact
    kind: str = 'rake'
    name: str = ''              # for issue labels only


@dataclass
class RakeNote:
    i: int; t: float; event: int; up: bool; t_end: float; t_free: float; go: float; a: object; amp: float
    ioi: float = math.inf; gap: float = math.inf; ioi_next: float = math.inf; gap_next: float = math.inf
    enter: str = ''             # how the head comes into the roll: home, announce, return, turn, ghost, fallback
    leave: str = ''             # ...and leaves it: park, release, turn, ghost, fallback
    t_apex: float = None; h_apex: float = None; t_w: float = None; hold: tuple = None
    run: tuple = None           # the carriage's (run-up, run-out) durations


class RakeStroke(_sv.ServoStroke):
    """A rake arm's planned stroke: a ServoStroke (the channels, knots, notes,
    travels, issues and the closed-form point) that declares no prep."""
    prep = None


# ---- closed forms ---------------------------------------------------------------------------
def clamped(u, f, s0, s1):
    """The C2 cubic spline through (u_k, f_k) with end slopes s0 and s1, as
    (p, v, a) at each knot (rows): the second derivatives M solve the
    clamped tridiagonal system."""
    u = np.asarray(u, float); f = np.asarray(f, float); n = len(u)-1; h = np.diff(u); d = np.diff(f)/h
    A = np.zeros((n+1, n+1)); r = np.zeros(n+1)
    A[0, 0], A[0, 1], r[0] = 2*h[0], h[0], 6*(d[0]-s0)
    for k in range(1, n):
        A[k, k-1], A[k, k], A[k, k+1], r[k] = h[k-1], 2*(h[k-1]+h[k]), h[k], 6*(d[k]-d[k-1])
    A[n, n-1], A[n, n], r[n] = h[n-1], 2*h[n-1], 6*(s1-d[n-1])
    M = np.linalg.solve(A, r)
    return np.c_[f, np.r_[d-h*(2*M[:-1]+M[1:])/6, s1], M]


_run_cache = {}
def run_d(p, v, a, stop):
    """The run-out from (p, v, a) to rest at `stop` (a run-up is the time
    reverse of one from (p, -v, a)): (D, peak |x''|), D in RUN_D the least
    peak among the durations whose x never runs back past the stop (the
    quintic's v' sampled at RUN_SAMPLES, every D at once); None when none is
    monotone."""
    key = (float(p), float(v), float(a), float(stop))
    if key not in _run_cache:
        D = np.arange(*RUN_D)[:, None]; tau = np.linspace(0.0, 1.0, RUN_SAMPLES)[None, :]*D; d = stop-p
        c3 = (20*d-12*v*D-3*a*D*D)/(2*D**3); c4 = (-30*d+16*v*D+3*a*D*D)/(2*D**4); c5 = (12*d-6*v*D-a*D*D)/(2*D**5)
        vel = v+tau*(a+tau*(3*c3+tau*(4*c4+tau*5*c5))); acc = a+tau*(6*c3+tau*(12*c4+tau*20*c5))
        ok = np.all(vel*np.sign(v) >= -1e-9, axis=1); pk = np.where(ok, np.abs(acc).max(axis=1), np.inf)
        k = int(np.argmin(pk)); _run_cache[key] = (float(D[k, 0]), float(pk[k])) if ok.any() else None
    return _run_cache[key]


def head_jerk(c, cy, T, n):
    """Exact peak |p'''| on [0, T] of a head segment: h''' n + (0, h_y''', 0),
    each component a quadratic in tau, so |p'''|^2 is a quartic whose maximum
    sits at an end or at a real root of its cubic derivative."""
    q = _st._dcoef(c, 3)[:3]; qy = _st._dcoef(cy, 3)[:3]
    comps = [n[0]*q, n[1]*q+qy, n[2]*q]
    P = np.zeros(5)
    for a in comps: P += np.convolve(a, a)
    dP = np.polynomial.polynomial.polyder(P)
    cand = [0.0, T]
    if np.any(np.abs(dP) > 0):
        for r in np.roots(dP[::-1]):
            if abs(r.imag) <= 1e-9*max(1.0, abs(r.real)) and 0 < r.real < T: cand.append(float(r.real))
    return math.sqrt(max(0.0, max(float(np.polynomial.polynomial.polyval(t, P)) for t in cand)))


def _pw(K, S):
    """Coefficient rows of the piecewise quintic hermite through knot states S at K."""
    return np.array([_st.law_hermite(*S[i], *S[i+1], K[i+1]-K[i]) for i in range(len(K)-1)])


def _pw_eval(K, C, t, d=0):
    t = np.atleast_1d(np.asarray(t, float)); j = np.clip(np.searchsorted(K, t, 'right')-1, 0, len(K)-2)
    out = np.zeros_like(t)
    for u in np.unique(j):
        m = j == u; out[m] = _st._horner(_st._dcoef(C[u], d), t[m]-K[u])
    return out


def apex(K, S, lo, hi):
    """A designed h's apex in (lo, hi) of piece time: its last + to - change
    of h', scanned and bisected on the closed form."""
    K = np.asarray(K, float); C = _pw(K, np.asarray(S, float))
    ts = np.linspace(lo, hi, APEX_SCAN); hv = _pw_eval(K, C, ts, 1)
    k = int(np.nonzero((hv[:-1] > 0) & (hv[1:] <= 0))[0][-1]); a, b = ts[k], ts[k+1]
    for _ in range(APEX_BISECT):
        m = .5*(a+b)
        if _pw_eval(K, C, m, 1)[0] > 0: a = m
        else: b = m
    return .5*(a+b)


# ---- the library ------------------------------------------------------------------------------
_lib_cache = {}
def library(path=None, reload=False):
    """The designed pieces (tools/rake_design.py), or None when there are none."""
    p = Path(path) if path else Path(__file__).resolve().parent/LIB
    if reload or str(p) not in _lib_cache:
        try: _lib_cache[str(p)] = json.loads(p.read_text())
        except (OSError, ValueError): _lib_cache[str(p)] = None
    return _lib_cache[str(p)]


class Geometry:
    """The rake's frame from plain data: n, y_c, z_c, the rest, the rail."""
    def __init__(self, arm):
        hv = np.asarray(arm.hover, float); self.H0 = float(np.linalg.norm(hv)); self.n = hv/self.H0
        if abs(self.n[0]) > 1e-12 or abs(self.n[2]) < .5: raise ValueError(f'{arm.name}: a rake comes at its strings along y-z, mostly z')
        hm = np.asarray(arm.home, float); self.xh, self.yc, self.zc = (float(v) for v in hm)
        xs = [float(p[0]) for p in arm.reach]
        self.reach = (min(xs), max(xs)); self.x_lo = self.reach[0]-OVER; self.x_hi = self.reach[1]+OVER
        self.rest = self.yh(hm+hv)

    def yh(self, p):
        """(y, h) of a point: h along n from z (z = z_c + h n_z), y less h's own y share (y = y_c + h_y)."""
        h = (float(p[2])-self.zc)/self.n[2]; return (float(p[1])-h*self.n[1], h)

    def chord(self, A, B):
        """|p(B) - p(A)| for two head points (y, h) at one x."""
        dh = B[1]-A[1]; return float(np.linalg.norm(dh*self.n+np.array([0.0, B[0]-A[0], 0.0])))

    def fingerprint(self, arm, rolls):
        """What the library must have been solved for: the frame, the rail, and
        one up and one down roll's contacts, times and sweep end states. No arm
        cfg (root, links, the search's reach cut): the pieces are designed in
        tool space and depend on none, so a rail replan never invalidates them."""
        fp = dict(n=self.n.tolist(), H0=self.H0, home=[self.xh, self.yc, self.zc], x_lo=self.x_lo, x_hi=self.x_hi,
                  approach=float(arm.approach), recover=float(arm.recover))
        for R in rolls: fp.setdefault('up' if R['up'] else 'down', self.roll_fp(R))
        return fp

    @staticmethod
    def roll_fp(R):
        """A roll's share of the fingerprint: its contacts, onsets, sweep knot states and rail runs."""
        return dict(points=np.asarray(R['r'].points, float).tolist(), onsets=(R['ts']-R['ts'][0]).tolist(),
                    X=R['X'].tolist(), Y=R['Y'].tolist(), H=R['H'].tolist(), D_in=R['D_in'], D_out=R['D_out'])


def _diff(a, b):
    """The largest difference between two nested lists/dicts of numbers (inf on a shape or key mismatch)."""
    if isinstance(a, dict):
        if not isinstance(b, dict) or set(a) != set(b): return math.inf
        return max([_diff(a[k], b[k]) for k in a], default=0.0)
    if isinstance(a, (list, tuple, np.ndarray)):
        a = np.asarray(a, float); b = np.asarray(b, float)
        return float(np.abs(a-b).max()) if a.shape == b.shape and a.size else (0.0 if a.shape == b.shape else math.inf)
    return abs(float(a)-float(b))


def _roll(g, r):
    """A roll's sweep: the clamped cubics' knot states (x, y, h), the x_hi end's inner knot on its chord (SWEEP_TUCK), its ends and rail runs."""
    P = np.asarray(r.points, float); ts = np.asarray(r.times, float); u = ts-ts[0]
    up = bool(P[-1, 0] > P[0, 0]); sg = 1.0 if up else -1.0
    yh = np.array([g.yh(p) for p in P])
    X = clamped(u, P[:, 0], sg*SWEEP_V_END[0], sg*SWEEP_V_END[0])
    Y = clamped(u, yh[:, 0], sg*SWEEP_V_END[1], sg*SWEEP_V_END[1]); H = clamped(u, yh[:, 1], 0.0, 0.0)
    # SWEEP_TUCK: the x_hi end e (an up roll's last contact, a down roll's first) and its inner knot k. The chord runs knot j
    # -> j+1 in time (j = min(k, e)) and the end slope is the travel's too, so both directions are the comb's own
    k, e = (len(P)-2, len(P)-1) if up else (1, 0); j = min(k, e)
    tc = math.atan2(Y[j+1, 0]-Y[j, 0], X[j+1, 0]-X[j, 0]); te = math.atan2(Y[e, 1], X[e, 1])
    th = tc+SWEEP_TUCK*math.remainder(te-tc, 2*math.pi); sp = math.hypot(X[k, 1], Y[k, 1])
    X[k, 1], Y[k, 1] = sp*math.cos(th), sp*math.sin(th)
    start, stop = (g.x_lo, g.x_hi) if up else (g.x_hi, g.x_lo)
    din = run_d(X[0, 0], -X[0, 1], X[0, 2], start); dout = run_d(*X[-1], stop)
    return dict(r=r, up=up, ts=ts, t=float(ts[0]), t_end=float(ts[-1]), X=X, Y=Y, H=H, start=start, stop=stop,
                D_in=din[0] if din else None, D_out=dout[0] if dout else None)


# ---- the builder ------------------------------------------------------------------------------
class _Build:
    """Both channels appended in time order from (-inf): each segment starts
    where its channel last ended, so the channel tiles exactly."""
    def __init__(s, g, arm, lib):
        s.g = g; s.arm = arm; s.lib = lib; s.head = []; s.car = []; s.issues = []; s.travels = []
        s.th = s.tc = -math.inf; s.P = g.rest; s.x = g.xh

    def issue(s, t, what, **kw): s.issues.append(dict(t=float(t), aid=s.arm.name, what=what, **kw))

    # -- head
    def _h(s, t1, law, ch, cy, tag, ev, extra):
        s.head.append(_st.Seg(s.th, t1, ch, law, tag, 'head', ev, extra, cy=cy, cz=None)); s.th = t1

    def h_hold(s, t1, kind, ev=-1):
        if t1 > s.th:
            y, h = s.P; s._h(t1, 'hold', _st.law_hold(h), _st.law_hold(y-s.g.yc), 'hold', ev,
                             dict(hold=kind, p0=h, hy=dict(p0=y-s.g.yc)))

    def h_herm(s, t1, by0, bh0, by1, bh1, tag, ev, **ex):
        T = t1-s.th; yc = s.g.yc
        y0 = (by0[0]-yc, by0[1], by0[2]); y1 = (by1[0]-yc, by1[1], by1[2])
        ex.update(p0=bh0[0], v0=bh0[1], a0=bh0[2], p1=bh1[0], v1=bh1[1], a1=bh1[2],
                  hy=dict(p0=y0[0], v0=y0[1], a0=y0[2], p1=y1[0], v1=y1[1], a1=y1[2]))
        s._h(t1, 'quintic hermite', _st.law_hermite(*bh0, *bh1, T), _st.law_hermite(*y0, *y1, T), tag, ev, ex)
        s.P = (float(by1[0]), float(bh1[0]))

    def h_345(s, t1, P1, tag, ev, **ex):
        T = t1-s.th; (y0, h0), (y1, h1) = s.P, P1; yc = s.g.yc
        ex.update(p0=h0, p1=h1, hy=dict(p0=y0-yc, p1=y1-yc))
        s._h(t1, '3-4-5', _st.law_345(h0, h1, T), _st.law_345(y0-yc, y1-yc, T), tag, ev, ex); s.P = (float(y1), float(h1))

    # -- carriage
    def _c(s, t1, law, c, tag, ev, extra):
        s.car.append(_st.Seg(s.tc, t1, c, law, tag, 'carriage', ev, extra, cy=_st.law_hold(s.g.yc), cz=_st.law_hold(s.g.zc)))
        s.tc = t1

    def c_hold(s, t1, ev=-1):
        if t1 > s.tc: s._c(t1, 'hold', _st.law_hold(s.x), 'hold', ev, dict(p0=s.x))

    def c_herm(s, t1, b0, b1, tag, ev, **ex):
        ex.update(p0=b0[0], v0=b0[1], a0=b0[2], p1=b1[0], v1=b1[1], a1=b1[2])
        s._c(t1, 'quintic hermite', _st.law_hermite(*b0, *b1, t1-s.tc), tag, ev, ex); s.x = float(b1[0])

    def c_345(s, t1, x1, tag, ev, **ex):
        t0 = s.tc; x0 = s.x; ex.update(p0=x0, p1=x1)
        s._c(t1, '3-4-5', _st.law_345(x0, x1, t1-t0), tag, ev, ex); s.x = float(x1)
        if 'travel' in ex: s.travels.append(dict(id=ex['travel'], t0=t0, t1=t1, x0=x0, x1=float(x1), tag=tag, event=ev))

    # -- the library's pieces
    def piece(s, name):
        return (s.lib or {}).get('pieces', {}).get(name)

    def h_piece(s, name, t1, b0, b1, cuts):
        """The designed head piece `name` from the head's end to t1: the
        library's interior knot states between the live ends b0, b1 ((y, h)
        states (p, v, a)), tagged by `cuts` [(t, tag, event)] in piece time,
        the first at 0; t = 'apex' cuts at the piece's apex, onto ruler 3's grid
        when within APEX_SNAP of a sample of it (the containing segment's
        start + n APEX_GRID). Returns the cuts' absolute times."""
        pc = s.piece(name); t0 = s.th; K = np.asarray(pc['y']['K'], float)
        Sy = np.array(pc['y']['S'], float); Sh = np.array(pc['h']['S'], float)
        err = max(_diff(Sy[0], b0[0]), _diff(Sh[0], b0[1]), _diff(Sy[-1], b1[0]), _diff(Sh[-1], b1[1]))
        if err > LIB_TOL: s.issue(t0, 'designed piece ends off the live states', piece=name, err=err)
        Sy[0], Sh[0], Sy[-1], Sh[-1] = b0[0], b0[1], b1[0], b1[1]
        ts = [t0]+[t0+k for k in K[1:-1]]+[t1]
        ca = []
        for c, tag, ev in cuts:
            if c == 'apex':
                ap = apex(K, Sh, *pc['apex']); i = int(np.searchsorted(K, ap, 'right'))-1
                g = ts[i]+round((t0+ap-ts[i])/APEX_GRID)*APEX_GRID
                ca.append((g if abs(g-(t0+ap)) <= APEX_SNAP else t0+ap, tag, ev))
            else: ca.append((t0+c, tag, ev))
        for i in range(len(ts)-1):
            a, b = ts[i], ts[i+1]; T = b-a; cy = _st.law_hermite(*Sy[i], *Sy[i+1], T); ch = _st.law_hermite(*Sh[i], *Sh[i+1], T)
            edges = [a]+[c[0] for c in ca[1:] if a+1e-9 < c[0] < b-1e-9]+[b]
            st = [(Sy[i], Sh[i])]+[(tuple(float(_st._horner(_st._dcoef(cy, d), np.array([e-a]))[0]) for d in range(3)),
                                    tuple(float(_st._horner(_st._dcoef(ch, d), np.array([e-a]))[0]) for d in range(3)))
                                   for e in edges[1:-1]]+[(Sy[i+1], Sh[i+1])]
            for k in range(len(edges)-1):
                _, tag, ev = [c for c in ca if c[0] <= edges[k]+1e-9][-1]
                s.h_herm(edges[k+1], st[k][0], st[k][1], st[k+1][0], st[k+1][1], tag, ev)
        return [c[0] for c in ca]

    def c_piece(s, name, t_off, b0, b1, tag, ev, travel):
        """The designed carriage x of piece `name` at piece time t_off, from the
        carriage's end (its first knot) to its last knot, between the live ends."""
        pc = s.piece(name)['x']; K = np.asarray(pc['K'], float); S = np.array(pc['S'], float)
        err = max(_diff(S[0], b0), _diff(S[-1], b1))
        if err > LIB_TOL: s.issue(t_off, 'designed carriage ends off the live states', piece=name, err=err)
        S[0], S[-1] = b0, b1; t0 = s.tc
        for i in range(len(K)-1): s.c_herm(t_off+K[i+1], S[i], S[i+1], tag, ev, travel=travel)
        s.travels.append(dict(id=travel, t0=t0, t1=s.tc, x0=float(b0[0]), x1=float(b1[0]), tag=tag, event=ev))

    def fits(s, name, D, t=None):
        pc = s.piece(name)
        ok = pc is not None and abs(float(pc['D'])-D) <= GAP_TOL
        if not ok and t is not None: s.issue(t, 'no designed piece fits', piece=name, want=float(D), have=None if pc is None else float(pc['D']))
        return ok


# ---- the plan ---------------------------------------------------------------------------------
def plan_rake(arm, jerk=True, lib=None):
    """Plan one rake arm's stroke from plain data (RakeIn) -> RakeStroke.
    `jerk` is accepted for stroke.plan's signature: the declared jerks are
    exact closed forms, always filled. `lib` overrides the library (a dict,
    tools/rake_design.py's)."""
    if arm.kind != 'rake': raise ValueError(f'no rake stroke for kind {arm.kind!r}')
    g = Geometry(arm); lib = library() if lib is None else lib
    rolls = [_roll(g, r) for r in sorted(arm.rolls, key=lambda r: r.t)]
    B = _Build(g, arm, lib)
    for R in rolls:
        if R['D_in'] is None or R['D_out'] is None: raise ValueError(f'{arm.name}: no monotone rail run at {R["t"]:.3f} s')
    # the library was solved for this frame, rail and these rolls, or it is not used at all
    if lib is None: B.issue(0.0, 'no designed pieces (formlab/rake_pieces.json): every gap falls back')
    else:
        fp = lib.get('fingerprint', {}); live = g.fingerprint(arm, rolls)
        for k, v in live.items():
            if k in ('up', 'down'): continue
            if _diff(v, fp.get(k, math.inf)) > LIB_TOL: B.issue(0.0, 'library fingerprint', key=k); B.lib = None
        for R in rolls:
            f = fp.get('up' if R['up'] else 'down')
            R['fit'] = bool(B.lib) and f is not None and _diff(g.roll_fp(R), f) <= LIB_TOL
            if B.lib and not R['fit']: B.issue(R['t'], 'roll unlike the designed one', event=R['r'].event)
    for R in rolls: R.setdefault('fit', False)
    n = len(rolls)
    gaps = [math.inf]+[rolls[k]['t']-rolls[k-1]['t_end'] for k in range(1, n)]

    # what each gap is: turn / ghost (a designed short piece of its length), long, or fallback
    def kind(k):
        if k == 0: return 'home'
        P, R = rolls[k-1], rolls[k]; gap = gaps[k]
        if not (P['fit'] and R['fit']): return 'fallback'
        same = P['up'] != R['up']
        if same and B.fits('turn_hi' if P['up'] else 'turn_lo', gap): return 'turn'
        if not same and not P['up'] and B.fits('ghost_down', gap): return 'ghost'
        return 'long'
    kinds = [kind(k) for k in range(n)]

    def exit_name(k):
        """The piece that leaves roll k into a long gap (or the end): a release
        up the strings when it ends a phrase (the gap before it was short) or
        the piece; else a park."""
        R = rolls[k]; rel = k == n-1 or kinds[k] in ('turn', 'ghost')
        return ('release_' if rel else 'park_')+('hi' if R['up'] else 'lo')

    def ent(R): return (tuple(R['Y'][0]), tuple(R['H'][0]))
    def ext(R): return (tuple(R['Y'][-1]), tuple(R['H'][-1]))
    def rest(P): return ((P[0], 0.0, 0.0), (P[1], 0.0, 0.0))
    def piece_end(name): pc = B.piece(name); return (pc['y']['S'][-1][0], pc['h']['S'][-1][0])
    def piece_start(name): pc = B.piece(name); return (pc['y']['S'][0][0], pc['h']['S'][0][0])

    def run_up(R, ev):
        B.c_hold(R['t']-R['D_in'], ev)
        B.c_herm(R['t'], (R['start'], 0.0, 0.0), tuple(R['X'][0]), 'stroke', ev)

    def run_out(R, ev):
        B.c_herm(R['t_end']+R['D_out'], tuple(R['X'][-1]), (R['stop'], 0.0, 0.0), 'follow-through', ev)

    def lead(ru, bs=None):
        """How long before its first string an announced roll's head leaves its
        rest: the backswing (the library's `bs` piece, or BACKSWING_S), the apex
        hold (HOLD_MIN), the run-up `ru`."""
        return (float(B.piece(bs)['D']) if bs is not None else BACKSWING_S)+HOLD_MIN+float(B.piece(ru)['D'])

    def car_go(ru, bs):
        """...and how long before it the carriage leaves under a designed backswing (its x starts into the piece)."""
        return lead(ru, bs)-float(B.piece(bs)['x']['K'][0])

    def announce(R, ru, bs=None, x_tag='travel'):
        """The backswing from the head's rest to the run-up's apex (the
        library's `bs` piece, home_up or return_up, the carriage crossing under
        it from the score's go to the hold; else a 3-4-5 over BACKSWING_S), the
        apex hold (HOLD_MIN, over a still carriage: D7), the run-up `ru`."""
        ev = R['r'].event; t = R['t']; D_ru = float(B.piece(ru)['D']); A = piece_start(ru)
        tB0 = t-lead(ru, bs); t_hold = t-D_ru-HOLD_MIN
        past = float(B.piece(bs)['x']['K'][-1])-float(B.piece(bs)['D']) if bs is not None and 'x' in B.piece(bs) else 0.0
        if past > GAP_TOL: B.issue(t, 'carriage crossing under the apex hold', event=ev, past=past)
        B.h_hold(tB0, 'hover' if B.P == g.rest else 'park', -1)
        if bs is not None:
            B.c_hold(t-car_go(ru, bs), -1)
            B.h_piece(bs, t_hold, rest(B.P), rest(A), [(0.0, 'wind-up', ev)])
            B.c_piece(bs, tB0, (B.x, 0.0, 0.0), (R['start'], 0.0, 0.0), x_tag, ev, f'e{ev}')
        else: B.h_345(t_hold, A, 'wind-up', ev)
        t_apex = t-D_ru; R['hold'] = (B.th, t_apex); R['t_w'] = tB0
        B.h_hold(t_apex, 'poise', ev)
        B.h_piece(ru, t, rest(A), ent(R), [(0.0, 'stroke', ev)])
        R['t_apex'], R['h_apex'] = t_apex, A[1]
        run_up(R, ev)

    def fallback(R, P=None):
        """No designed piece fits (an issue; never on the assets): the head one
        quintic hermite from where it is (P's exit, or at rest from
        t - ANNOUNCE_S) into the entry; the carriage runs out of P, crosses to
        the rail end on a 3-4-5 'travel' where it must, and runs up."""
        ev = R['r'].event; B.issue(R['t'], 'fallback gap', event=ev)
        if P is None:
            B.h_hold(max(B.th, R['t']-ANNOUNCE_S), 'hover' if B.P == g.rest else 'park')
            B.h_herm(R['t'], *rest(B.P), *ent(R), 'stroke', ev)
        else:
            B.h_herm(R['t'], *ext(P), *ent(R), 'follow-through', ev); run_out(P, P['r'].event)
        if abs(B.x-R['start']) > 1e-12:
            t0 = max(B.tc, R['r'].go); t1 = R['t']-R['D_in']
            if t1 <= t0: raise ValueError(f'{arm.name}: no room to cross to the rail end before {R["t"]:.3f} s')
            B.c_hold(t0); B.c_345(t1, R['start'], 'travel', ev, travel=f'e{ev}')
        R['t_apex'] = B.head[-1].t0; R['h_apex'] = None
        run_up(R, ev)

    # -- rest, then the homing sweep (the score's cue)
    legs = list(arm.homing or [])
    poses = (B.lib or {}).get('homing')
    if legs and poses is None: B.issue(legs[0][0], 'no designed homing poses: the head holds through the joint windows')
    wins = [w for w in legs if w[2] != 'x']
    for k, (t0, t1, what, a, b) in enumerate(legs):
        if what == 'x':
            B.c_hold(t0); B.c_345(t1, b, 'home', -1, travel=f'home-x{k}')
            continue
        B.h_hold(t0, 'hover'); B.c_hold(t1)
        if poses is None: B.h_hold(t1, 'hover'); continue
        pts = [B.P]+[tuple(p) for p in poses[what]]+([g.rest] if (t0, t1, what, a, b) == wins[-1] else [])
        L = np.cumsum([0.0]+[g.chord(A, C) for A, C in zip(pts, pts[1:])])
        for j in range(1, len(pts)):
            tb = t1 if j == len(pts)-1 else t0+(t1-t0)*L[j]/L[-1]
            B.h_345(tb, pts[j], 'home', -1, joint=what, leg=j-1)
    B.c_hold(B.th if B.th > B.tc else B.tc); B.h_hold(B.tc, 'hover')

    # -- the rolls
    for k, R in enumerate(rolls):
        ev = R['r'].event; R['enter'] = kinds[k]
        if k == 0:
            nx = B.piece('home_up')['next'] if B.piece('home_up') else None
            if R['fit'] and R['up'] and nx and B.piece(nx) and abs(B.x-g.xh) <= 1e-12 and B.P == g.rest \
                    and R['t']-lead(nx, 'home_up') >= max(B.th, B.tc)-1e-9 and R['t']-car_go(nx, 'home_up') >= R['r'].go-GAP_TOL:
                announce(R, nx, 'home_up')
            else: R['enter'] = 'fallback'; fallback(R)
        else:
            P = rolls[k-1]; pev = P['r'].event; kd = kinds[k]
            if kd == 'turn':
                name = 'turn_hi' if P['up'] else 'turn_lo'
                cuts = B.h_piece(name, R['t'], ext(P), ent(R), [(0.0, 'follow-through', pev), ('apex', 'stroke', ev)])
                R['t_apex'] = cuts[-1]; R['t_w'] = P['t_end']
                run_out(P, pev); run_up(R, ev); P['leave'] = 'turn'
            elif kd == 'ghost':
                pc = B.piece('ghost_down'); go, arr = pc['x']['K'][0], pc['x']['K'][-1]
                if abs(P['t_end']+go-P['r'].t_free) > GAP_TOL or abs(R['t']-arm.approach-(P['t_end']+arr)) > GAP_TOL:
                    B.issue(P['t_end'], 'ghost window unlike the designed one', event=ev)
                cuts = B.h_piece('ghost_down', R['t'], ext(P), ent(R),
                                 [(0.0, 'follow-through', pev), (go, 'ghost', ev), ('apex', 'stroke', ev)])
                R['t_apex'] = cuts[-1]; R['t_w'] = P['t_end']
                run_out(P, pev); B.c_hold(P['t_end']+go)
                B.c_piece('ghost_down', P['t_end'], (P['stop'], 0.0, 0.0), (R['start'], 0.0, 0.0), 'ghost', ev, f'e{ev}')
                run_up(R, ev); P['leave'] = 'ghost'
            elif kd == 'long':
                xn = exit_name(k-1); D = float(B.piece(xn)['D']) if B.piece(xn) else math.inf
                same = P['up'] != R['up']
                # to the other end only the return (park_hi -> rake00) is designed: its backswing carries the carriage
                ret = 'return_up' if not same and R['up'] and xn == 'park_hi' and B.piece('return_up') else None
                ru = B.piece(ret)['next'] if ret else ('runup_lo' if R['up'] else 'runup_hi')
                ok = B.piece(xn) is not None and B.piece(ru) is not None and (same or ret is not None) \
                    and P['t_end']+D <= R['t']-lead(ru, ret)+1e-9
                if ok and ret: ok = R['r'].go <= R['t']-car_go(ru, ret)+GAP_TOL
                if not ok: R['enter'] = 'fallback'; P['leave'] = 'fallback'; fallback(R, P)
                else:
                    B.h_piece(xn, P['t_end']+D, ext(P), rest(piece_end(xn)), [(0.0, 'follow-through', pev)])
                    run_out(P, pev); P['leave'] = xn.split('_')[0]
                    if ret: R['enter'] = 'return'; announce(R, ru, ret)
                    else: R['enter'] = 'announce'; announce(R, ru)
            else: R['enter'] = 'fallback'; P['leave'] = 'fallback'; fallback(R, P)
        # the sweep: four quintic hermites a channel through the sweep's knot states (_roll)
        ts = R['ts']
        for j in range(len(ts)-1):
            t1 = float(ts[j+1]) if j < len(ts)-2 else R['t_end']
            B.h_herm(t1, tuple(R['Y'][j]), tuple(R['H'][j]), tuple(R['Y'][j+1]), tuple(R['H'][j+1]), 'sweep', ev)
            B.c_herm(t1, tuple(R['X'][j]), tuple(R['X'][j+1]), 'sweep', ev)

    # -- the last release, held to the score's last onset, then home with it
    if rolls:
        R = rolls[-1]; ev = R['r'].event; xn = exit_name(n-1)
        if R['fit'] and B.piece(xn) is not None:
            B.h_piece(xn, R['t_end']+float(B.piece(xn)['D']), ext(R), rest(piece_end(xn)), [(0.0, 'follow-through', ev)])
            R['leave'] = 'release'
        else:
            B.issue(R['t_end'], 'fallback release', event=ev); R['leave'] = 'fallback'
            B.h_herm(R['t_end']+FALLBACK_S, *ext(R), *rest(g.rest), 'follow-through', ev)
        run_out(R, ev)
        t_ret = max(float(arm.t_return), B.th, B.tc)
        B.h_hold(t_ret, 'park'); B.c_hold(t_ret)
        B.h_345(t_ret+END_S, g.rest, 'travel', -1); B.c_345(t_ret+END_S, g.xh, 'travel', -1, travel='end')
    B.h_hold(math.inf, 'hover'); B.c_hold(math.inf)

    # the declared jerks: each moving segment's exact peak (head: the quartic |p'''|^2; carriage: |x'''|)
    for sg in B.head:
        sg.extra['jerk'] = 0.0 if sg.law == 'hold' else head_jerk(sg.c, sg.cy, sg.T, g.n)*(1+JERK_PAD)
    for sg in B.car:
        sg.extra['jerk'] = 0.0 if sg.law == 'hold' else _sv._hermite_jerk(sg.c, sg.T)*(1+JERK_PAD)
    knots = sorted([_st.Knot(b.t0, 'smooth', None, b.event) for ch in (B.head, B.car) for b in ch[1:]], key=lambda k: k.t)
    notes = []
    for k, R in enumerate(rolls):
        r = R['r']; nx = rolls[k+1] if k+1 < n else None
        notes.append(RakeNote(i=k, t=R['t'], event=r.event, up=R['up'], t_end=R['t_end'], t_free=float(r.t_free), go=float(r.go),
                              a=r.a, amp=float(r.amp), ioi=R['t']-rolls[k-1]['t'] if k else math.inf, gap=gaps[k],
                              ioi_next=nx['t']-R['t'] if nx else math.inf, gap_next=gaps[k+1] if nx else math.inf,
                              enter=R.get('enter', ''), leave=R.get('leave', ''), t_apex=R.get('t_apex'), h_apex=R.get('h_apex'),
                              t_w=R.get('t_w'), hold=R.get('hold'), run=(R['D_in'], R['D_out'])))
    for x in notes:
        if x.t_apex is not None and x.h_apex is None:
            sg = B.head[int(np.searchsorted([s_.t0 for s_ in B.head], x.t_apex, 'right'))-1]
            x.h_apex = float(_st._horner(sg.c, np.array([x.t_apex-sg.t0]))[0])
    return RakeStroke(arm, g.n, B.head, B.car, knots, notes, B.travels, B.issues)

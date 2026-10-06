"""The servo stroke (PLAYERS M2, "servo anticipation"): a pick arm's scored
path as declared segments on two channels, planned from plain data the Rig
hands over. numpy only, no import of formlab.rig (the rig imports this), so
Blender can run it. The surface is formlab/stroke.py's ArmStroke (Channels,
p/v/a/j, segments, knots, notes, issues, rest_point), so the rulers and the
bake read a servo as they read a mallet.

    p(t) = (x(t), y_c(t), z_c(t)) + h(t) n + (0, h_y(t), h_z(t))

* `x(t)` ('carriage'): the carriage on its leadscrew, on the servo S-curve
  ('scurve', SCURVE_RAMP each end: rest to rest, C2, peak/mean speed 1.4286)
  from contact to contact; y_c/z_c, the contact's y and z, ride the same
  normalised law (the cy/cz slots stroke.py fills for the mallet).
* `h(t)` ('head'): the tool's height above the contact along the unit
  clearance n = Rig.clearance(aid)/|.| ((0, 0, -1) for a plucked string: the
  tool comes at the string plane from behind). 'quintic hermite' segments and
  'hold's, joined C2 except at a contact.
* `h_y/h_z`: a head segment's optional cy/cz (None = 0). A pick leaves them
  None; the rake (formlab/rake.py, T5) may not.

The S-curve is no single polynomial, so a 'scurve' travel is ONE declared
segment (ScurveSeg: one law, one closed-form jerk, the rulers' breakpoints at
its ramp ends) evaluated as its three polynomial pieces (ramp, cruise, ramp).

The stroke (docs/goals/the-players.md M2, the design brief section 2.2):
* POISED (gap >= POISED_GAP): the head rises from the hover to H_APEX over
  [t - RISE_LEAD, t - POISE[0]] while the carriage travels from the score's
  go (or the rise, if later) to the poise, both arriving together (a ruler
  22 sync target), wherever its S-curve fits the servo's limits there
  (motion_timing.servo_fast_s: SERVO_V_MAX at its peak, SERVO_A_MAX_G, the
  floor); the poise is the tool's stillness (D7), so a window that cannot is
  an issue, never a quiet run on to the score's arrive (a move of the
  contact's y/z alone, which the score does not schedule, rides the last
  release: see the carriage below); the poise,
  a declared head 'hold' (extra hold='poise') ending at t_apex = t - POISE[1]
  (A4); the action, a quintic hermite from rest at the apex to the contact at
  v_in; the contact; the release back to the hover over T_REL, held there.
* PHRASE (gap < POISED_GAP): continuous, no hold: the head leaves the last
  contact at V_REL and rises straight to its apex (min(H_PHRASE,
  PHRASE_RISE_V W)), turning there at A_TURN_G (ruler 5: |a| >= 0.5 g through
  the turn), then the action over T_down = clamp(T_DOWN_K IOI, T_DOWN); the
  carriage travels over the score's whole window [go, arrive] (a move of the
  contact's y/z alone, which the score does not schedule: from the last
  contact's t_free, never while the pick is in the string).
* The contact is a declared impulse (Knot 'contact'): the pick meets the
  string at -v_in n and leaves it at +V_REL n, dv = (v_in + V_REL) n. Why
  that and not a rebound: a pick does not bounce off a string (nothing
  elastic sends it back); the string is drawn and slips off, and the servo
  withdraws at its own commanded speed. V_REL > 0 because v+ = 0 would be the
  head stopping dead at the string, the very flaw this milestone removes; a
  constant V_REL (not e v_in) because then nothing after a contact depends on
  its a', which ruler 22's repeat needs (below). e = V_REL/v_in is 0.25-0.35.
* Only the carriage is bound by the score's `arrive` (motion_timing.
  arrive_lead): the action starts before it, on the head alone.
* Repeat (ruler 22): the head law is a function of (IOI, a', next IOI,
  next a') alone, never of dx, the idle time or the previous string; the
  head relative to the carriage therefore repeats exactly.

`plan_pick(PickIn) -> ServoStroke` is the whole interface; `prep(a, ioi)`,
`v_in(a)` and `t_down(ioi)` are the declared functions."""
import math
from dataclasses import dataclass, field
import numpy as np
try:
    from . import stroke as _st
except ImportError:
    import stroke as _st

motion_timing = _st.motion_timing
G = _st.G

# ---- the tunables (every one hashed into the rail key, layout_search.motion_constants 'servo.') ----
SCURVE_RAMP = motion_timing.SERVO_RAMP   # the S-curve's ramp share at each end (rig.scurve re-exports it; the planner's occupancy rides it): peak/mean speed 1/(1-r) = 1.4286
POISED_GAP = 1.0            # s: a contact this long after the last one is poised (rise, poise, action); shorter: a phrase stroke
RISE_LEAD = .74             # s: a poised rise (and its travel) starts this long before the contact: approach 0.09 + T1's capped slew 0.65
POISE = (.25, .15)          # s before the contact: the poise [t - .25, t - .15], a declared head hold of 0.1 s ending at t_apex (A4; the rake's HOLD_MIN)
H_APEX = .32                # m: a poised apex above the contact (the hover 0.22 + 0.10; ruler 3's dh >= 0.25 h(t_apex) needs >= 0.2933)
H_PHRASE = .22              # m: a phrase apex: the hover
PHRASE_RISE_V = 1.2         # m/s: a phrase apex is at most this x its rise time W (the IOI 0.18 run rises 0.113 m in 94 ms, not 0.22 at 9 g)
T_DOWN_K = .40              # a phrase action lasts this x IOI, clamped to T_DOWN (ruler 4's struck band is 0.35-0.45 IOI)
T_DOWN = (.085, .15)        # s: its bounds: ruler 4's pluck approach >= 2.5 frames (83.3 ms) with margin; a poised action's length
A_TURN_G = 1.0              # g: a phrase apex turns at this (ruler 5: |a| >= 0.5 g throughout the slow turn, with margin)
V_IN = (2.0, .8)            # m/s: v_in = V_IN[0] + V_IN[1] a' (a' None = 1): the pick drives through the string
V_REL = .7                  # m/s: the withdrawal right after the pluck (a commanded speed, a'-free: see the docstring)
T_REL = .25                 # s: a poised release from the string to the hover (RISE_LEAD + T_REL <= POISED_GAP: it ends before the rise)
MONO_SAMPLES = 257          # samples a head segment's monotony (a rise rises, an action falls) is checked on
SCURVE_J = 6/(SCURVE_RAMP**2*(1-SCURVE_RAMP))     # peak |s'''| of the unit S-curve over unit time (95.24)
SCURVE_A = 1.5/(SCURVE_RAMP*(1-SCURVE_RAMP))      # peak |s''| (7.143)
SCURVE_V = 1/(1-SCURVE_RAMP)                      # peak |s'| (1.4286)

assert RISE_LEAD+T_REL <= POISED_GAP+1e-12, 'a poised release ends before the next rise'
assert T_DOWN[1] == POISE[1], 'the longest phrase action is the poised one'

LAWS = ('scurve', 'quintic hermite', 'hold')


# ---- the declared functions -----------------------------------------------------------------
def v_in(a):
    """The action's speed at the contact (m/s), from a' in [0, 1] (None = 1)."""
    return V_IN[0]+V_IN[1]*_st.a_or_one(a)


def t_down(ioi):
    """A stroke's action time (s): POISE[1] when poised, else clamp(T_DOWN_K IOI, T_DOWN)."""
    if ioi is None or not math.isfinite(ioi) or ioi >= POISED_GAP-1e-9: return POISE[1]
    return min(max(T_DOWN_K*ioi, T_DOWN[0]), T_DOWN[1])


def prep(a, ioi):
    """The declared apex height h(a', IOI) above the contact (m): H_APEX when
    poised (IOI inf for a first note), else min(H_PHRASE, PHRASE_RISE_V (IOI -
    t_down(IOI))). This is the function Rig.declared(aid).prep returns for a
    pick (a' does not raise a pick: v_in carries it)."""
    if ioi is None or not math.isfinite(ioi) or ioi >= POISED_GAP-1e-9: return H_APEX
    return min(H_PHRASE, PHRASE_RISE_V*(ioi-t_down(ioi)))


def yz_s(L, H0):
    """How long a y/z-only reposition (another pick point on the same
    string) takes riding a poised release: it lands with the head on the hover
    on the release's own end jerk ((60 H0 - 24 V_REL T_REL) / T_REL^3 against
    the S-curve's SCURVE_J L / T^3), so the two channels settle together at
    any in-position band (ruler 22 reads 1 um: a 0.56 mm chord over the whole
    0.2 s would come within it 7.7 ms before the head), and never under
    motion_timing.servo_fast_s(L). Under 3.7 mm the match runs under ruler
    15's 2.5 frames (harp_arm1's 0.75 mm in 49.8 ms): a floor there lowers
    the carriage's end jerk under the head's, so it enters the 1 um band
    first and every such target's arrival skew in ruler 22's gated sync row
    moves (2.0 ms at 0.56 mm): left as a known issue (M9's row)."""
    j = abs(60*H0-24*V_REL*T_REL)/T_REL**3
    return max(motion_timing.servo_fast_s(L), (SCURVE_J*L/j)**(1/3))


# ---- the S-curve as declared segments ---------------------------------------------------------
def _c8(p):
    c = np.zeros(8); cc = np.asarray(p.coef, float); c[:len(cc)] = cc; return c


def scurve_pieces(T):
    """The unit S-curve s(tau) on [0, T] (rig.scurve: 0 -> 1, s' and s'' zero at
    both ends) as three polynomials, 8 coefficients each in the piece's own
    local time: the ramp up on [0, rT], the cruise on [rT, (1 - r)T], the ramp
    down on [(1 - r)T, T]; ramp(w) = w^3 - w^4/2, k = r/(1 - r)."""
    r = SCURVE_RAMP; k = r/(1-r); R = r*T; P = np.polynomial.Polynomial
    ramp = P([0.0, 0.0, 0.0, 1.0, -.5])
    up = k*ramp(P([0.0, 1/R]))                         # k ramp(tau/R)
    cruise = P([.5*k, 1/((1-r)*T)])                    # (0.5 r + (u - r))/(1 - r), u = r + tau/T
    down = 1-k*ramp(P([1.0, -1/R]))                    # 1 - k ramp((1 - u)/r), u = 1 - r + tau/T
    return _c8(up), _c8(cruise), _c8(down)


class ScurveSeg(_st.Seg):
    """A carriage travel on the S-curve from P0 to P1 (x, y_c, z_c): ONE declared
    segment, law 'scurve', evaluated as its three polynomial pieces per axis
    (`pieces[k]`, k = 0 x, 1 y_c, 2 z_c). `c` holds no polynomial (NaN): use ev()."""
    __slots__ = ('P0', 'P1', 'pieces')

    def __init__(self, t0, t1, P0, P1, tag, event=-1, extra=None):
        super().__init__(t0, t1, np.full(8, np.nan), 'scurve', tag, 'carriage', event, extra)
        self.P0 = np.asarray(P0, float); self.P1 = np.asarray(P1, float)
        T = self.t1-self.t0; R = SCURVE_RAMP*T; D = self.P1-self.P0
        cuts = (self.t0, self.t0+R, self.t1-R, self.t1); S = scurve_pieces(T)
        def piece(j, k):
            c = S[j]*D[k]; c[0] += self.P0[k]
            return _st.Seg(cuts[j], cuts[j+1], c, 'scurve', tag, 'carriage', event)
        self.pieces = tuple(tuple(piece(j, k) for j in range(3)) for k in range(3))

    def point(self, t, d=0):
        """(..., 3): the carriage point's d-th derivative at t in [t0, t1]."""
        t = np.asarray(t, float); out = np.zeros(t.shape+(3,))
        for k in range(3):
            for j, g in enumerate(self.pieces[k]):
                m = (t >= g.t0) & ((t < g.t1) if j < 2 else (t <= g.t1))
                if np.any(m): out[..., k][m] = g.ev(t[m], d)
        return out

    def ev(self, t, d=0): return self.point(t, d)[..., 0]


class _Axis:
    """One carriage coordinate (x, y_c or z_c) over the declared segments: a
    stroke.Channel on their polynomial pieces (a 'scurve' travel is three).
    `segs` are the DECLARED segments (one a travel), what index/at/joins see."""
    def __init__(self, name, segs, k):
        self.name = name; self.segs = list(segs); self.k = k
        pieces = []
        for s in self.segs:
            if isinstance(s, ScurveSeg): pieces.extend(s.pieces[k])
            else: pieces.append(_st.Seg(s.t0, s.t1, (s.c, s.cy, s.cz)[k], s.law, s.tag, s.channel, s.event))
        self._ch = _st.Channel(name, pieces)
        self.t0 = np.array([s.t0 for s in self.segs]); self.t1 = np.array([s.t1 for s in self.segs])

    def ev(self, t, d=0, side=+1): return self._ch.ev(t, d, side)

    def index(self, t, side=+1):
        i = np.searchsorted(self.t0, t, side='right' if side > 0 else 'left')-1
        return np.clip(i, 0, len(self.t0)-1)

    def joins(self): return [s.t0 for s in self.segs[1:]]

    def at(self, t, side=+1): return self.segs[int(self.index(np.asarray([t], float), side)[0])]


# ---- the plan's inputs and records --------------------------------------------------------------
@dataclass
class PickIn:
    """One pick arm's plan inputs (Rig._servo_input)."""
    hits: list                  # [stroke.HitIn]: t, point (the contact), a', go (the score's t_move), event, amp
    home: tuple                 # the home string's contact (x, y, z): the carriage's rest before the first travel
    hover: tuple                # Rig.clearance(aid): the tool's rest offset from a contact ((0, 0, -0.22) plucked)
    arrive_lead: float          # motion_timing.arrive_lead: the carriage stands on a contact this long before it
    recover: float = 0.0        # the actuator's recover_s: the string is free this long after a contact (the score's t_free)
    homing: list = field(default_factory=list)   # none drawn for a pick at M2 (harp homing is M7, A15)
    kind: str = 'pick'
    name: str = ''              # for issue labels only


@dataclass
class PickNote:
    i: int; t: float; x: float; y: float; z: float; a: float; a_raw: object; amp: float; event: int; go: float; arrive: float
    ioi: float = math.inf; gap: float = math.inf; ioi_next: float = math.inf
    style: str = ''; kind: str = 'pluck'; v_in: float = 0.0; v_out: float = V_REL; e: float = None; dv: tuple = None
    h: float = 0.0; T_down: float = None; t_apex: float = None; t_w: float = None; W: float = None; L: float = None; dh: float = None
    hold: tuple = None; rise: tuple = None; release: tuple = None
    travel: int = None; travel_window: tuple = None; travel_v: float = 0.0; travel_a: float = 0.0; hurried: bool = False


class ServoStroke:
    """One servo arm's planned stroke: the `head` and `carriage` channels (plus
    the y_c/z_c blends and any head h_y/h_z), knots, per-note records, travels,
    issues, and the closed-form point and its derivatives."""
    jerk_declared = True        # declared at plan time (closed forms): stroke.declare_jerk leaves it

    def __init__(self, arm, n, head, car, knots, notes, travels, issues):
        self.arm = arm; self.n = np.asarray(n, float)
        self.head = _st.Channel('head', head)
        self.carriage = _Axis('carriage', car, 0); self.yc = _Axis('yc', car, 1); self.zc = _Axis('zc', car, 2)
        side = any(s.cy is not None or s.cz is not None for s in head)
        if side:
            def z8(c): return np.zeros(8) if c is None else c
            hs = [_st.Seg(s.t0, s.t1, z8(s.cy), s.law, s.tag, 'head', s.event) for s in head]
            zs = [_st.Seg(s.t0, s.t1, z8(s.cz), s.law, s.tag, 'head', s.event) for s in head]
            self.hy = _st.Channel('hy', hs); self.hz = _st.Channel('hz', zs)
        else: self.hy = self.hz = None
        self.knots = knots; self.notes = notes; self.travels = travels; self.issues = issues

    def segments(self, channel=None):
        out = []
        for ch in (self.head, self.carriage):
            if channel in (None, ch.name): out.extend(ch.segs)
        return out

    def h(self, t, d=0, side=+1): return self.head.ev(t, d, side)

    def x(self, t, d=0, side=+1): return self.carriage.ev(t, d, side)

    def car(self, t, d=0, side=+1):
        """(..., 3) the carriage point (x, y_c, z_c) or its d-th derivative."""
        return np.stack([self.carriage.ev(t, d, side), self.yc.ev(t, d, side), self.zc.ev(t, d, side)], -1)

    def _d(self, t, d, side):
        out = self.car(t, d, side)+np.asarray(self.head.ev(t, d, side))[..., None]*self.n
        if self.hy is not None:
            out = out+np.stack([np.zeros_like(np.asarray(self.hy.ev(t, d, side), float)), self.hy.ev(t, d, side), self.hz.ev(t, d, side)], -1)
        return out

    def p(self, t, side=+1):
        """The scored tool point(s) at t: (..., 3)."""
        return self._d(t, 0, side)

    def v(self, t, side=+1): return self._d(t, 1, side)

    def a(self, t, side=+1): return self._d(t, 2, side)

    def j(self, t, side=+1): return self._d(t, 3, side)

    def rest_point(self):
        """Where the path rests before the first note (the hover above home)."""
        return self.p(-1e9)

    def prep(self, a, ioi): return prep(a, ioi)

    # -- what a stepped carriage has and a servo has not (the Rig asks every stroke)
    def carriage_x(self, t): return self.carriage.ev(t)

    def detent(self, t): return 0.0 if np.ndim(t) == 0 else np.zeros(np.shape(t))

    def pawl_ride(self, t): return 0.0 if np.ndim(t) == 0 else np.zeros(np.shape(t))

    def ride_times(self, levels=None): return np.zeros(0)

    def clicks(self): return []

    def click_times(self): return []


# ---- the plan ---------------------------------------------------------------------------------
def _hermite_jerk(c, T):
    """Exact peak |h'''| of a quintic on [0, T]: h''' is a quadratic (ends and vertex)."""
    q = _st._dcoef(c, 3); cand = [0.0, T]
    if abs(q[2]) > 0:
        tv = -q[1]/(2*q[2])
        if 0 < tv < T: cand.append(tv)
    return max(abs(float(q[0]+q[1]*u+q[2]*u*u)) for u in cand)


def _monotone(s, sign):
    tau = np.linspace(0.0, s.T, MONO_SAMPLES); h = _st._horner(s.c, tau)
    return bool(np.all(sign*np.diff(h) > 0))


def plan_pick(arm, jerk=True):
    """Plan one pick arm's stroke from plain data (PickIn) -> ServoStroke.
    `jerk` is accepted for stroke.plan's signature: the declared jerks are
    closed forms, always filled."""
    if arm.kind != 'pick': raise ValueError(f'no pick stroke for kind {arm.kind!r}')
    hits = sorted(arm.hits, key=lambda h: h.t)
    hv = np.asarray(arm.hover, float); H0 = float(np.linalg.norm(hv)); n = hv/H0
    issues = []                                  # ArmStroke's record: dict(t, aid, what, **detail)
    def issue(t, what, **kw): issues.append(dict(t=float(t), aid=arm.name, what=what, **kw))
    notes = []
    for i, h in enumerate(hits):
        ioi = h.t-hits[i-1].t if i else math.inf
        poised = ioi >= POISED_GAP-1e-9; Td = t_down(ioi); hA = prep(h.a, ioi); vi = v_in(h.a)
        p = tuple(float(v) for v in h.point)
        nt = PickNote(i=i, t=float(h.t), x=p[0], y=p[1], z=p[2], a=_st.a_or_one(h.a), a_raw=h.a, amp=float(h.amp),
                      event=int(h.event), go=float(h.go), arrive=float(h.t)-float(arm.arrive_lead), ioi=ioi, gap=ioi,
                      style='poised' if poised else 'phrase', v_in=vi, e=V_REL/vi, dv=tuple(float(v) for v in (vi+V_REL)*n),
                      h=hA, T_down=Td, t_apex=float(h.t)-Td)
        if poised:
            nt.t_w = nt.t-RISE_LEAD; nt.rise = (nt.t_w, nt.t-POISE[0]); nt.hold = (nt.t-POISE[0], nt.t_apex)
            nt.W = nt.rise[1]-nt.rise[0]; nt.dh = hA-H0
        else:
            nt.t_w = nt.t-ioi; nt.rise = (nt.t_w, nt.t_apex); nt.W = nt.t_apex-nt.t_w; nt.dh = hA
        nt.L = nt.t-nt.t_w
        if i: notes[-1].ioi_next = ioi
        notes.append(nt)

    # the head: cursor-built (stroke._Builder.H), C2 at every join but a contact
    b = _st._Builder(); g_turn = -A_TURN_G*G     # the first poised rise's hover hold starts at -inf
    for k, nt in enumerate(notes):
        ev = nt.event; nxt = notes[k+1] if k+1 < len(notes) else None
        if nt.style == 'poised':
            b.H(nt.rise[0], 'hold', 'hold', ev, (H0,), hold='hover')
            b.H(nt.rise[1], 'quintic hermite', 'wind-up', ev, (H0, 0.0, 0.0, nt.h, 0.0, 0.0), style='poised')
            b.H(nt.t_apex, 'hold', 'hold', ev, (nt.h,), hold='poise')
            b.H(nt.t, 'quintic hermite', 'stroke', ev, (nt.h, 0.0, 0.0, 0.0, -nt.v_in, 0.0), style='poised', v_in=nt.v_in)
        else:
            # the last contact's withdrawal rises straight to this apex and turns there
            b.H(nt.t_apex, 'quintic hermite', 'wind-up', ev, (0.0, V_REL, 0.0, nt.h, 0.0, g_turn), style='phrase')
            b.H(nt.t, 'quintic hermite', 'stroke', ev, (nt.h, 0.0, g_turn, 0.0, -nt.v_in, 0.0), style='phrase', v_in=nt.v_in)
        if nxt is None or nxt.style == 'poised':
            nt.release = (nt.t, nt.t+T_REL)
            b.H(nt.release[1], 'quintic hermite', 'release', ev, (0.0, V_REL, 0.0, H0, 0.0, 0.0))
    b.H(math.inf, 'hold', 'hold', -1, (H0,), hold='hover')
    head = b.head
    for s in head:
        if s.law != 'quintic hermite': continue
        sign = -1 if s.tag == 'stroke' else +1
        if not _monotone(s, sign): issue(s.t1, f'head {s.tag} not monotone', t0=s.t0)

    # the carriage: hold, S-curve travel, hold ..., on the score's windows
    car = []; P = np.asarray(arm.home, float); tc = -math.inf; travels = []
    def hold_to(t1, ev):
        nonlocal tc
        if t1 > tc+1e-12:
            car.append(_st.Seg(tc, t1, _st.law_hold(P[0]), 'hold', 'hold', 'carriage', ev, cy=_st.law_hold(P[1]), cz=_st.law_hold(P[2])))
            tc = t1
    for j, nt in enumerate(notes):
        Q = np.array([nt.x, nt.y, nt.z])
        if np.max(np.abs(Q-P)) <= 1e-12: continue
        # the score schedules x alone (go = arrive when x stays): a move of the
        # contact's y/z only (another pick point on the same string, 0.6-78 mm)
        # leaves once the string is free (the last contact's t + recover_s:
        # never sideways while the pick is still in the string). A phrase's
        # runs to the score's arrive. A poised one rides the last contact's
        # release and lands with the head on the hover (yz_s: on the release's
        # end jerk), so the rise and the poise are the head's alone: reposition,
        # then prepare. Run under the rise into the poise instead, the two
        # channels would leave and arrive together in time but not in ruler
        # 22's in-position reading: a carriage chord under ~1.13 cm on the
        # S-curve is 1 um from its start 4.2-21 ms after the head's 0.10 m rise
        # is (A6; measured 0.56-11.5 mm on harp_arm1/2), whatever law it rides.
        # Round 2 ran it under the hover into the rise instead, ending where a
        # head hold ends: D8 reads that as a carriage late into the hold (the
        # hover's 0.08-9.0 s), and five of the thirteen left during the release
        # and arrived 79-430 ms after the head.
        # A scored poised travel ends at the poise wherever the S-curve can
        # (motion_timing.servo_fast_s: peak speed, SERVO_A_MAX_G, the floor):
        # the poise is the tool's stillness (D7). PLAYERS M2 round 3 retired
        # the fixed CAR_MIN 0.20 s: POISE (.25, .15) left harp_arm1's 45.0 and
        # harp_arm2's 44.29 0.197 s from the go, so both ran on to the arrive
        # through the poise at 561 and 1098 mm/s. The planner's occupancy
        # (loam.score._Solver._law) assumes the carriage leaves at the go and
        # lands no sooner than servo_fast_s after it: both are issues here.
        scored = nt.arrive-nt.go > 1e-6
        free = notes[j-1].t+float(arm.recover) if j else -math.inf
        if nt.style == 'poised' and scored:
            # need: the S-curve's least time over the 3-D chord (its peak speed and |a| ride L, as yz_s and
            # tools/test_servo.py's cap judge it; the x alone reads up to 1.92x short of L on the harps)
            ta = max(nt.go, nt.rise[0]); need = motion_timing.servo_fast_s(float(np.linalg.norm(Q-P)))
            tb = nt.hold[0] if nt.hold[0]-ta >= need-1e-12 else nt.arrive
            if tb > nt.hold[0]+1e-12: issue(nt.t, 'poise under a moving carriage', window=nt.hold[0]-ta, need=need)
            if ta > nt.go+1e-9: issue(nt.t, "travel leaves after the score's go", go=nt.go, ta=ta)
        elif nt.style == 'poised' and j and notes[j-1].release is not None:
            tb = notes[j-1].release[1]; ta = max(tc, free, tb-yz_s(float(np.linalg.norm(Q-P)), H0))
        elif nt.style == 'poised':
            tb = nt.rise[0]
            lead = motion_timing.travel_s(arm.kind, float(np.linalg.norm(Q-P)))+motion_timing.SLEW_SLACK_S
            ta = max(tc, free, tb-lead)
        else:
            ta, tb = (nt.go, nt.arrive) if scored else (max(tc, free), nt.arrive)
        if ta < tc-1e-12 or not tb > ta+1e-6 or tb > nt.arrive+1e-9:
            issue(nt.t, 'travel has no window', ta=ta, tb=tb, after=tc)
            ta = max(tc, min(ta, tb-1e-3))
        hold_to(ta, nt.event)
        D = Q-P; T = tb-ta; L = float(np.linalg.norm(D)); k = len(travels)
        # the score's want is by dx alone, so a y/z-only move has none (x stays, go
        # = arrive); x within the 1e-12 "no move" above is float noise (6.9e-18 m
        # on harp_arm1 at 37.55 s), not a 0.4 s slew to flag a 0.28 s window hurried
        want = motion_timing.travel_s(arm.kind, float(D[0]) if abs(D[0]) > 1e-12 else 0.0)
        s = ScurveSeg(ta, tb, P, Q, 'travel', nt.event,
                      dict(travel=k, p0=float(P[0]), p1=float(Q[0]), D=[float(v) for v in D], go=nt.go, arrive=nt.arrive,
                           hurried=bool(T < want-1e-9), jerk=SCURVE_J*L/T**3))
        car.append(s); tc = tb; P = Q
        nt.travel = k; nt.travel_window = (ta, tb); nt.travel_v = SCURVE_V*L/T; nt.travel_a = SCURVE_A*L/T**2; nt.hurried = s.extra['hurried']
        travels.append(dict(k=k, t0=ta, t1=tb, P0=s.P0, P1=s.P1, event=nt.event, style=nt.style, hurried=nt.hurried))
    hold_to(math.inf, -1)
    for s in car:
        if s.law == 'hold': s.extra['jerk'] = 0.0
    for s in head:
        s.extra['jerk'] = _hermite_jerk(s.c, s.T) if s.law == 'quintic hermite' else 0.0

    # knots: each contact an impulse (v- = -v_in n, v+ = +V_REL n), smooth at every other join
    knots = [_st.Knot(nt.t, 'contact', np.array(nt.dv), nt.event, dict(v_in=nt.v_in, v_out=V_REL, e=nt.e)) for nt in notes]
    ct = np.array([nt.t for nt in notes])
    for t in sorted({s.t0 for s in head[1:]} | {s.t0 for s in car[1:]}):
        if ct.size and np.min(np.abs(ct-t)) <= 1e-9: continue
        knots.append(_st.Knot(t, 'smooth'))
    knots.sort(key=lambda k: (k.t, k.kind))
    return ServoStroke(arm, n, head, car, knots, notes, travels, issues)

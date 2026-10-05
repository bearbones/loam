"""The mallet stroke (PLAYERS M1, "mallets ride the bounce"): a mallet arm's
scored path as declared, closed-form polynomial segments on two scalar
channels, planned from plain data the Rig hands over. numpy only, no import
of formlab.rig (the rig imports this), so Blender can run it.

    p(t) = (x(t), y_c(t) + h(t), z_c(t) + sigma*Z(h(t)))

* `h(t)` ('head'): the head's height above the contact along +y.
* `x(t)` ('carriage'): the carriage on its rack. y_c/z_c are the contact's y
  and z, blended between consecutive contacts on the same normalised law as x
  (every mallet contact shares y and z today, so they are constants there).
* `Z(h) = (rho/k^2)(sqrt(1 + (k h/rho)^2) - 1)`: the arc the M5 hinge will
  make. Vertical at the contact (Z'(0) = 0, radius rho there), slope 1/k tall,
  leaning to the arm's own side (sigma = sign(root_z - z_c)).

Every segment is a polynomial of degree <= 7 in local time (8 coefficients,
lowest power first, Horner), under one of four laws: '3-4-5' (rest to rest),
'quintic hermite' (general p, v, a at both ends), 'ballistic' (constant
acceleration) and 'hold'. Every join is C2; the velocity jumps only at a
contact, by the declared impulse dv = (0, (1 + e) v_in, 0). The detent ring is
a ring on the carriage, not path.

The phases (docs/goals/the-players.md, M1; the build spec's section 1):
tempo gaps (IOI <= FLOAT_IOI) are a rebound-led ballistic float straight to
the next apex and a thrown quintic downstroke; longer gaps are a bounce loop
whose rise (contact to apex) RESTS or FLOWS, never hitches (ruler 8 '8
rise'): a rest is an APEX CATCH (`_top_catch`: the arm takes the head while it
still rises and brings it, never reversing, C2, to rest where the free bounce
would have turned) and holds it still >= REST_MIN; a flow rises throughout
with every speed valley >= FLOW_K, never past the apex. At gaps < HOLD_GAP a
Dahl loop: the rebound floats at the e and a_f `dahl_float` picks and hands
over still rising, C2, to one quintic wind-up flowing into the downstroke. At
gaps >= HOLD_GAP the rebound floats at E_LOOP into a flowing rise to a park, a
coasting one (an ease, a constant speed, a stop timed to arrive with the
carriage), or an apex catch, a rest low and a 3-4-5 up, chosen by one rule
(`_least`): the least peak of the tool's speed in the world (the carriage's x
and the head's arc, one vector) from the contact + RISE_SKIP to the hold
start; of the shapes within PEAK_TIE of that peak, a rest if there is one;
then the least COORD_P-norm of that speed from the contact to the hold start.
`_rise_alone` applies it on the head's arc speed where no carriage moves
under the rise (a park, an 'S2 step' whose steps come after the rise, the
same for every shape, the coda's raise), `_coordinate` on the world speed
under a freewheel, of the shapes that leave the head no wait (LOW_WAIT).
Under a stepped traverse that fits only from go (the tolls, `_under`) the
float hands over to a coast that climbs under the steps and stops at the
prep with the last landing; its float's (e, a_f) come off `dahl_float`'s
grid by the same rule (coasts only), of the coasts at >= UNDER_K x STILL_V,
ruler 8's still line. Then the cocked HOLD and a downstroke from rest. The
first note comes from the hover after the homing sweep; the last rides one
bounce loop into a raise to H_END, chosen the same way.

The carriage travels contact to contact under the head, never before the
score's `go` (t_move), arrived by the contact (tempo) or by the cocked hold:
stepped tooth by tooth (a 3-4-5 over STEP_MOVE of the period, a dwell on the
detent) where `motion_timing.travel_regime` says the window holds it, else
one freewheel with a click a tooth where x crosses mid-tooth: a 3-4-5 or a
glide (a 3-4-5's halves about a cruise): a contact travel's whichever has
the least COORD_P-norm of the tool's speed over its window
(`_Planner._contact_glide`, over the head already planned to the contact). A
hold note's freewheel and rise are coordinated (`_Planner._coordinate`): the
carriage leaves under the rising head and both arrive together, or the head
parks first, shape and glide chosen by the rule above. After a contact the
head is never left waiting below its park while the carriage moves (ruler 8
'8 low rest': still, LOW_REV under the park, for over a frame; 0 waits on
every mallet arm), and ruler 22 times a channel's start only from rest.

`plan(ArmIn) -> ArmStroke` is the whole interface; `prep(a, ioi)` and
`v_in(a)` are the declared prep and strike-speed functions."""
import math
import sys
import importlib.util as _ilu
from dataclasses import dataclass, field
from pathlib import Path
import numpy as np


def _load_motion_timing():
    """loam/motion_timing.py by path (importing `loam` pulls the synth stack),
    shared through sys.modules so every formlab module that asks gets one
    instance."""
    m = sys.modules.get('loam_motion_timing')
    if m is not None and hasattr(m, 'travel_regime'):
        return m
    spec = _ilu.spec_from_file_location('loam_motion_timing', Path(__file__).resolve().parents[1]/'loam'/'motion_timing.py')
    m = _ilu.module_from_spec(spec); spec.loader.exec_module(m)
    sys.modules['loam_motion_timing'] = m
    return m


motion_timing = _load_motion_timing()
_PITCH = motion_timing.PITCH
_V345 = motion_timing.V345
_A345_HALF = motion_timing.A345/2      # a 3-4-5 over 2 Th covering 2 d peaks at A345 (2 d)/(2 Th)^2 = this x d/Th^2
_FPS = motion_timing.FPS

# ---- the tunables (every one hashed into the rail key, layout_search.motion_constants) ----
G = 9.81                    # the rulers' g (tools/players/core.G); bounds in g are judged with it
# motion_timing.G (9.80665) is the planner's: it prices t_move, step periods and the hurried ceilings. Both
# stay. Changing the planner's would move the score's t_move; changing this one would move the stroke's bounds
# off the rulers'. The 0.03 % difference errs strict: a 3 g step priced at 9.80665 runs at <= 3 x 9.81 measured.
# strike speed: v_in(a') = V0 + V1 sqrt(a')  (2.50 .. 3.76 m/s; ruler 7 ratio >= 1.5, ruler 1/11 cap the top)
V0, V1 = 2.5, 1.26
# prep: h(a', IOI) = (H0 + H1 a') g(IOI), capped at H_MAX; g = sqrt(IOI/IOI_REF) up to IOI_REF, then a
# monotone cubic Hermite in log IOI (slope-matched at IOI_REF, flat at IOI_LONG) up to G_LONG
H0, H1 = 0.15, 0.125
IOI_REF, IOI_LONG, G_LONG = 0.357, 1.2, 2.0
H_MAX = 0.50
FLOAT_IOI = 0.6             # a rebound-led float straight to the next apex at IOI <= this; a bounce loop above
# the tempo float: T_down on a grid, cost (e - E_AIM)^2 + (T_down/IOI - TD_AIM)^2, penalties holding e, a_f and s
E_LO, E_HI, E_AIM = 0.3, 0.8, 0.55
AF_LO_G, AF_HI_G = 0.5, 1.5
TD_FAST_IOI = 0.5           # IOI <= this: T_down in TD_FAST x IOI; above: TD_SLOW seconds
TD_FAST = (0.35, 0.45)
TD_SLOW = (0.125, 0.25)
TD_AIM = 0.40
S_MIN = 0.25                # s = g T_down^2 / (2 h) >= this (rule 4: the downstroke is driven, not dropped)
# every rise keeps ruler 8's '8 rise' (tools/players/r_strike.py) with margin: from each contact to the next
# apex the head either FLOWS (one gesture: the float hands over, still rising, to a driven quintic whose speed
# may sag but never below FLOW_K of the lesser of its peaks before and after) or RESTS (is caught at the top of
# its flight without reversing, or dips genuinely low, and is still for at least REST_MIN before a wind-up from rest)
STILL_V = 0.05              # m/s: still (ruler 8's HITCH_V; 1.7 mm a frame)
REST_MIN = 0.25             # s: a rest's stillness (ruler 8's REST_MIN; the catch's tail and the wind-up's start add 33-131 ms)
FLOW_K = 0.6                # a flowing rise's least speed / the lesser of its peaks before and after (ruler 8's HITCH_K 0.5 + 0.1)
FLOAT_MIN = 0.02            # s: a float handed over to a driven rise lasts at least this (ruler 8 judges it from t + 5 ms)
FLOW_N = 24                 # handover times (and, where free, wind-up ends) a flowing rise is searched on
FLOW_SAMPLES = 64           # samples a Dahl rise's speed is judged on (a hold loop's: every COORD_DT)
EASE_MIN = 0.02             # s: a coasting rise's ease (from the float's -a_f to a = 0) lasts at least this (jerk <= a_f/EASE_MIN)
RISE_SKIP = 0.005           # s: ruler 8 judges a rise (and a float) from the contact + this (r_strike.FLOAT_SKIP)
PEAK_TIE = 0.01             # m/s: of rises whose peak world speeds are this close (0.3 mm a frame) a rest wins (the head
                            # waits low through a long gap, not parked high; the goal's tie, A11), then the lesser COORD_P-
                            # norm; else the lesser peak (ruler 1). One rule where no carriage moves and under a freewheel
# the bounce loop
E_LOOP, AF_LOOP_G = 0.45, 1.0
# a rest's APEX CATCH (goal A11, ruler 8's '8 catch'; _top_catch): the float hands over, still rising, D before
# its free apex to one quintic hermite (in the quartic family, c5 = 0) that brings the head to rest, never
# reversing, where the free bounce would have turned. Its shortest member rests exactly on the ballistic apex at a
# peak brake of 1.077 a_f; it is lengthened (resting a little above the apex) to TOP_MIN_T and to TOP_BRAKE_G
TOP_SHARE = 0.45            # D = this x (t_f - RISE_SKIP): the catch begins at this x ruler 8's launch speed v(t + 5 ms)
                            # (its CATCH_SHARE 0.5, with margin: the free flight carries 81 % of the height, >= 3/4 at 0.5)
TOP_MIN_T = 2/30            # s: the catch lasts at least two frames (a' = 0's shortest member is 1.88 frames: +0.6 mm)
TOP_BRAKE_G = 1.4           # the catch brakes no harder than this (ruler 8's 1.5 g, with margin; 1.077 a_f passes it above 1.3 g)
CATCH_K, CATCH_MIN, CATCH_MAX = 1.3, 0.08, 0.25   # the low catch (_low): clamp(CATCH_K sqrt(2 dip/a_f)) s
H_LOW_PREP = 0.6            # a rest is at most this x the prep high (ruler 3's dh >= 0.25 h over a wind-up from rest, with margin)
H_LOW_UNDER = 0.5           # where no rise fits before the hold (_low, an issue: none on the assets) the head is caught LOW, at
                            # this x the float's apex (a dip >= ruler 8's 1 cm HITCH_REV: a new up-run, no hitch)
# the toll under the loop (_Planner._under; goal Tolls 5, A11): a stepped traverse that fits only from go leaves under
# the bounce loop and the head COASTS up under its steps, arriving at the prep with the last landing. Its float takes
# dahl_float's (e, a_f) grid; a coast climbs at >= UNDER_K x STILL_V, ruler 8's still line ('8 low rest': a head under
# STILL_V, below its park while the carriage moves, is waiting). At the loop's e 0.45 under 1 g the bars' 4 s tolls
# coast at 0.029-0.048 m/s, under that line; at e 0.31 under 1.48 g 0.059-0.068
UNDER_K = 1.1
# the Dahl loop (FLOAT_IOI < IOI, gap < HOLD_GAP): one flowing rise. The rebound floats at -a_f and hands over,
# still rising, at t_w to one quintic wind-up to (h, 0, A_TOP) flowing into the least legal downstroke. (e, a_f,
# t_w) is the grid point (e E_LO..E_HI by DAHL_E_STEP and a_f AF_LO_G..AF_HI_G by DAHL_AF_STEP, each one step
# inside ruler 8's bands; t_w on FLOW_N points from FLOAT_MIN to the float's apex) whose whole rise, contact to
# apex, flows with the least peak head speed on the arc (PEAK_TIE, then the least COORD_P-norm). The handover
# comes by DAHL_RISE_BY of the IOI: ruler 21 reads an accent's rise at the declared wind-up's start. (The old
# floor on the wind-up's own rise, DAHL_DH 0.30 h, served ruler 3's dh over a wind-up that left a still apex;
# the rise now runs from the contact, dh = h, and the floor is gone.)
DAHL_TD_RAMP = True         # a Dahl downstroke's T_down: the h ramp (True) or the least legal (False)
DAHL_E_STEP, DAHL_AF_STEP = 0.01, 0.02   # the (e, a_f g) grid's steps
DAHL_RISE_BY = 0.5          # x IOI: the latest handover (ruler 21's accent rise starts by t_prev + 0.5 IOI; at the bound)
# the downstroke from rest (or from a Dahl wind-up): T_DOWN_LONG, lengthened toward T_DOWN_MAX as the prep
# grows from TD_H0 to TD_H1, and further (TD_STEP at a time) until h falls strictly, s >= S_MIN and |a| <= A_MAX_G
T_DOWN_LONG, T_DOWN_MAX = 0.15, 0.25
TD_H0, TD_H1, TD_STEP = 0.275, 0.50, 0.005
A_END_G = -4.0              # thrown: the head still accelerates down at the contact
A_TOP_G = -0.5              # a Dahl wind-up flows into the downstroke at this
A_MAX_G = 10.0              # tool acceleration bound off +-A_MAX_GUARD of a contact (rule 3)
A_MAX_GUARD = 0.010
HOLD_GAP = 0.8              # gaps at least this long park and hold before the downstroke
HOLD = 0.12                 # the cocked hold (>= 3 frames)
W_RISE = 0.30               # a wind-up from rest to the park, shortened toward W_MIN when that lets the traverse run alone
W_MIN = 6/30+0.01
W_RATE = 0.6                # m/s: a wind-up from rest lasts max(W_RISE, rise / W_RATE) where there is room (ruler 1); it
                            # ENDS where the head must be parked (the hold, or the traverse it parks over) and the head
                            # rests low before it
# a hold note's rise is chosen, and a freewheel to its hold coordinated with it (_Planner._coordinate): of the
# allowed shapes (a flowing rise, a coasting rise whose stop arrives with the carriage, or an apex catch, a rest and
# a wind-up from rest; each parked before the carriage leaves or arriving with it), sampled every COORD_DT on a
# COORD_N grid of start times, the least peak of the tool's world speed from the contact + RISE_SKIP, a rest within
# PEAK_TIE, then the least COORD_P-norm over the gap; the carriage leaves under a moving head only where the head
# moves at >= COORD_MOVING m/s (ruler 22 times starts from rest), never while it waits below the park (LOW_WAIT)
COORD_P, COORD_DT, COORD_N, COORD_MOVING = 8, 0.002, 25, 0.02
# ...of the shapes ruler 8 allows too: '8 low rest' (A11) reads a head still (|h'| < STILL_V) more than LOW_REV below
# its park while the carriage moves (|x'| > X_MOVING) for over a frame as one left waiting (r_strike's HITCH_REV and
# X_MOVING). A wind-up from rest leaving WITH the carriage waits so (bars_arm0 57.143: 79 ms, its 3-4-5 still under
# STILL_V while the carriage's passes X_MOVING); a coordinated shape holds that state at most LOW_WAIT, half a frame
# (margin over the ruler's 1/240 s sampling and numeric slopes)
LOW_REV, X_MOVING, LOW_WAIT = 0.01, 0.01, 0.5/30
# ...and its freewheel may GLIDE: a 3-4-5's accelerating half, a cruise over this share of the travel, the
# decelerating half (the halves at <= FREE_G); 0 is the plain 3-4-5. A contact travel's freewheel takes the share
# whose tool speed has the least COORD_P-norm over its window, every COORD_DT (_Planner._contact_glide); a hold
# note's is coordinated with its rise (_Planner._coordinate). A share whose halves would pass FREE_G is skipped
GLIDE = (0.0, 0.2, 0.4, 0.6)
# rule 7: a reposition's channels come within ARRIVE_POS of their end (and leave their start, where both start
# from rest) within ARRIVE_SKEW of each other (half of ruler 22's SKEW_MAX, 1/240 s, between continuously bisected
# in-position instants)
ARRIVE_POS, ARRIVE_SKEW = 1e-6, 1/480
# the first note: rest at the hover, an anticipatory dip below it, wind up to the prep, park, traverse under the parked head, hold, strike
SETTLE_S, FIRST_RISE_S = 0.4, 0.7   # the first rise lasts at least FIRST_RISE_S (more where its wind-up wants W_RATE)
FIRST_DIP, FIRST_DIP_FRAC, FIRST_FLOOR = 0.15, 0.35, 0.05   # the first note's anticipatory dip: (h - hover) x FIRST_DIP below the hover, over FIRST_DIP_FRAC of the rise
# after the last note: one bounce loop, a raise to H_END (>= 1.5 x the tempo apex), the park
H_END, END_RAISE_S = 0.42, 0.6
# the arc and the declared virtual pin, per kind (one value for every arm of the kind)
ARC = {'mallet': dict(rho=0.16, k=1.2)}
R_PIN = 0.40
# the detent ring on a stepped landing (a damped sine in the travel's direction, amp OVERSHOOT x PITCH),
# faded by a 3-4-5 from RING_FADE of the dwell to its end, so it is spent before the next step moves.
# formlab.rig re-exports OVERSHOOT, RING_HZ and RING_TAU (its hammer ratchet rings the same).
OVERSHOOT = .10
RING_HZ = 14.0
RING_TAU = .09
RING_FADE = 0.5
# the pawl: it drops into each tooth below PAWL_RIDE teeth/s and rides the rack above;
# pawl_ride(t) is a smoothstep of the tooth rate over PAWL_RIDE_BAND
PAWL_RIDE = 15.0
PAWL_RIDE_BAND = (12.0, 18.0)
RIDE_ROWS = tuple(k/8 for k in range(9))   # bake rows where the tooth rate crosses these fractions of the band
# homing joint sweeps (ruler 22 home): elbow e0 -> e0 - HOME_COVER/2 span -> e0 + HOME_COVER/2 span -> e0;
# shoulder 0 -> -HOME_DROP_DEG -> -HOME_DROP_DEG + HOME_COVER span -> 0; each leg a 3-4-5 given the sweep
# window's time in proportion to its joint amplitude. HOME_SPAN_GUESS stands in when the caller has no span.
HOME_COVER = 0.85
HOME_DROP_DEG = 3.0
HOME_NEAR = 0.3             # sweep the joints at home unless home is this close (x) to another mechanism's reach
HOME_SPAN_GUESS = dict(elbow=1.0, shoulder=0.6)
JERK_SAMPLES = 1024         # dense analytic evaluation of each segment's declared peak jerk


# ---- laws: 8 coefficients in local time, lowest power first ---------------------------------
LAWS = ('3-4-5', 'quintic hermite', 'ballistic', 'hold')


def law_hold(p):
    c = np.zeros(8); c[0] = p; return c


def law_ballistic(p0, v0, a):
    c = np.zeros(8); c[0], c[1], c[2] = p0, v0, a/2; return c


def law_hermite(p0, v0, a0, p1, v1, a1, T):
    """The quintic with (p, v, a) given at both ends of [0, T]."""
    c = np.zeros(8); c[0], c[1], c[2] = p0, v0, a0/2
    T2, T3 = T*T, T*T*T
    c[3] = (20*(p1-p0)-(8*v1+12*v0)*T-(3*a0-a1)*T2)/(2*T3)
    c[4] = (30*(p0-p1)+(14*v1+16*v0)*T+(3*a0-2*a1)*T2)/(2*T3*T)
    c[5] = (12*(p1-p0)-6*(v1+v0)*T-(a0-a1)*T2)/(2*T3*T2)
    return c


def law_345(p0, p1, T):
    """Rest to rest: p0 + (p1 - p0)(10u^3 - 15u^4 + 6u^5), u = tau/T."""
    c = np.zeros(8); D = p1-p0; c[0] = p0
    c[3], c[4], c[5] = 10*D/T**3, -15*D/T**4, 6*D/T**5
    return c


def s345(u):
    u = np.clip(u, 0.0, 1.0); return u*u*u*(10-15*u+6*u*u)


def _dcoef(c, d):
    """The d-th derivative's coefficients (still 8, lowest first)."""
    c = np.asarray(c, float)
    for _ in range(d):
        c = np.append(c[1:]*np.arange(1, len(c)), 0.0)
    return c


def _horner(c, tau):
    out = np.zeros_like(tau)+c[7]
    for k in range(6, -1, -1):
        out = out*tau+c[k]
    return out


# ---- segments and channels ---------------------------------------------------------------
class Seg:
    """One polynomial piece on one channel over [t0, t1). `c` is in local time
    tau = t - ref (ref = t0, or t1 for a piece that starts at -inf; such a
    piece and one that ends at +inf must be constant). `extra` carries the
    declared fields (channel, jerk, pin/axis, regime/travel/hurried, joint,
    hold, the hermite's p0..a1)."""
    __slots__ = ('t0', 't1', 'c', 'law', 'tag', 'channel', 'event', 'extra', 'cy', 'cz')

    def __init__(self, t0, t1, c, law, tag, channel, event=-1, extra=None, cy=None, cz=None):
        self.t0 = float(t0); self.t1 = float(t1); self.c = np.asarray(c, float); self.law = law; self.tag = tag
        self.channel = channel; self.event = int(event); self.extra = dict(extra or {}); self.extra['channel'] = channel
        self.cy = cy; self.cz = cz
        if not (np.isfinite(self.t0) and np.isfinite(self.t1)) and np.any(self.c[1:] != 0):
            raise ValueError(f'{channel} {tag}: an unbounded segment must be constant')

    @property
    def ref(self):
        return self.t0 if np.isfinite(self.t0) else (self.t1 if np.isfinite(self.t1) else 0.0)

    @property
    def T(self): return self.t1-self.t0

    def ev(self, t, d=0):
        t = np.asarray(t, float); return _horner(_dcoef(self.c, d), t-self.ref)

    def __repr__(self):
        return f'Seg({self.channel}:{self.tag} {self.law} [{self.t0:.4f}, {self.t1:.4f}) ev={self.event})'


class Channel:
    """A scalar channel: contiguous segments covering (-inf, +inf), no hole and
    no overlap. ev(t, d, side): side +1 is the right limit (a knot belongs to
    the segment it starts), -1 the left."""
    def __init__(self, name, segs, coef='c'):
        self.name = name; self.segs = list(segs)
        if not self.segs or self.segs[0].t0 != -np.inf or self.segs[-1].t1 != np.inf:
            raise ValueError(f'{name}: must cover (-inf, +inf)')
        for a, b in zip(self.segs, self.segs[1:]):
            if a.t1 != b.t0 or not a.t1 > a.t0:
                raise ValueError(f'{name}: hole/overlap between {a} and {b}')
        self.t0 = np.array([s.t0 for s in self.segs]); self.t1 = np.array([s.t1 for s in self.segs])
        self.ref = np.array([s.ref for s in self.segs])
        C = np.array([getattr(s, coef) for s in self.segs], float)
        self.D = [C]
        for _ in range(4):
            prev = self.D[-1]; nxt = np.zeros_like(prev); nxt[:, :-1] = prev[:, 1:]*np.arange(1, 8); self.D.append(nxt)

    def index(self, t, side=+1):
        i = np.searchsorted(self.t0, t, side='right' if side > 0 else 'left')-1
        return np.clip(i, 0, len(self.t0)-1)

    def ev(self, t, d=0, side=+1):
        scalar = np.ndim(t) == 0
        t = np.atleast_1d(np.asarray(t, float)); i = self.index(t, side); tau = t-self.ref[i]
        Cd = self.D[d][i]; out = np.zeros_like(tau)+Cd[:, 7]
        for k in range(6, -1, -1):
            out = out*tau+Cd[:, k]
        return float(out[0]) if scalar else out

    def joins(self): return [s.t0 for s in self.segs[1:]]

    def at(self, t, side=+1): return self.segs[int(self.index(np.asarray([t], float), side)[0])]


@dataclass
class Knot:
    t: float
    kind: str                       # 'contact' | 'click' | 'detent' | 'smooth'
    dv: object = None               # 3-vector at an impulse
    event: int = -1
    extra: dict = field(default_factory=dict)


# ---- the declared functions -----------------------------------------------------------------
def a_or_one(a):
    return 1.0 if a is None else float(a)


def v_in(a):
    """The downstroke's speed at the contact (m/s), from a' in [0, 1]."""
    return V0+V1*math.sqrt(max(a_or_one(a), 0.0))


def prep_gain(ioi):
    """g(IOI): sqrt(IOI/IOI_REF) up to IOI_REF (faster is lower), then a cubic
    Hermite in log IOI from 1 (slope matched) to G_LONG (flat) at IOI_LONG,
    monotone; G_LONG for a first note (IOI = inf)."""
    if ioi is None or not math.isfinite(ioi) or ioi >= IOI_LONG:
        return G_LONG
    if ioi <= IOI_REF:
        return math.sqrt(max(ioi, 0.0)/IOI_REF)
    L = math.log(IOI_LONG/IOI_REF); u = math.log(ioi/IOI_REF)/L
    m0 = 0.5*L
    h00 = 2*u**3-3*u**2+1; h10 = u**3-2*u**2+u; h01 = -2*u**3+3*u**2
    return h00*1.0+h10*m0+h01*G_LONG


def prep(a, ioi):
    """The declared prep height h(a', IOI) above the contact (m): IOI is the gap
    to the note being prepped (inf for a first note), a' None counts as 1.0.
    This is the function Rig.declared(aid).prep returns."""
    return min((H0+H1*a_or_one(a))*prep_gain(ioi), H_MAX)


def amp_ranges(events):
    """{voice: (least amp, greatest amp)} over every score event, the voice
    e['voice'] else e['mech']: what a' is normalised over."""
    rng = {}
    for e in events:
        v = e.get('voice', e.get('mech')); a = float(e.get('amp', 1.0))
        lo, hi = rng.get(v, (a, a)); rng[v] = (min(lo, a), max(hi, a))
    return rng


def a_prime(e, rng):
    """One event's a' in [0, 1] given amp_ranges(...) of its score; None when
    its voice has a single amp."""
    lo, hi = rng[e.get('voice', e.get('mech'))]
    return None if hi-lo < 1e-9 else (float(e.get('amp', 1.0))-lo)/(hi-lo)


def a_norm(events):
    """a' per event exactly as tools/players/core.Subject.a_norm (and
    Rig._a_norm, which shares amp_ranges/a_prime): the amp normalised over
    every score event of the same voice (e['voice'], else e['mech']); None
    when that voice has a single amp. layout_search's rail key hashes it."""
    rng = amp_ranges(events)
    return [a_prime(e, rng) for e in events]


def arc(kind='mallet'):
    """(rho, k) of the arc map for an arm kind."""
    p = ARC[kind]; return float(p['rho']), float(p['k'])


def arc_Z(h, rho, k, d=0):
    """Z(h) and its h-derivatives (unsigned; the path takes sigma*Z)."""
    h = np.asarray(h, float); q = np.sqrt(1+(k*h/rho)**2)
    if d == 0: return (rho/k**2)*(q-1)
    if d == 1: return (h/rho)/q
    if d == 2: return (1/rho)/q**3
    if d == 3: return -3*k*k*h/(rho**3*q**5)
    raise ValueError(d)


def pawl_state(rate):
    return 'drop' if rate < PAWL_RIDE else 'ride'


def smoothstep(u):
    u = np.clip(u, 0.0, 1.0); return u*u*(3-2*u)


def ring_detent(tau, sign):
    """The detent ring's undamped-by-fade value tau seconds after a landing."""
    return sign*OVERSHOOT*_PITCH*np.exp(-tau/RING_TAU)*np.sin(2*np.pi*RING_HZ*tau)


# ---- homing joint sweeps (pure data; the Rig turns them into joint angles at pose time) --------
def joint_points(joint, span):
    """The sweep's joint offsets (rad, from the home pose's angle) at its four corners."""
    if joint == 'elbow':
        a = HOME_COVER/2*span; return [0.0, -a, a, 0.0]
    if joint == 'shoulder':
        d = math.radians(HOME_DROP_DEG); return [0.0, -d, -d+HOME_COVER*span, 0.0]
    raise ValueError(joint)


def joint_legs(joint, t0, t1, span):
    """The joint sweep over [t0, t1] as three legs dict(t0, t1, q0, q1, frac):
    q in radians from the home angle, each leg a 3-4-5 given time in proportion
    to its amplitude (equal peak joint speed), `frac` its share of the window."""
    q = joint_points(joint, span); amp = [abs(b-a) for a, b in zip(q, q[1:])]
    tot = sum(amp) or 1.0; out = []; t = t0
    for k, (a, b, m) in enumerate(zip(q, q[1:], amp)):
        tb = t1 if k == 2 else t+(t1-t0)*m/tot
        out.append(dict(t0=t, t1=tb, q0=a, q1=b, frac=m/tot, leg=k)); t = tb
    return out


def joint_site(x_home, x_lo, x_hi, others, near=HOME_NEAR):
    """Where the joint sweeps happen (the build spec's section 4): None (at
    home) unless home is within `near` in x of another mechanism's reach
    window (`others`: [(lo, hi)]); then whichever end of the arm's own x path
    (x_lo, x_hi) is farther from those windows."""
    def dist(x, w): return max(w[0]-x, x-w[1], 0.0)
    close = [w for w in others if dist(x_home, w) <= near]
    if not close:
        return None
    return max((x_lo, x_hi), key=lambda x: min(dist(x, w) for w in close))


# ---- the plan's inputs ------------------------------------------------------------------------
@dataclass
class HitIn:
    """One scored contact, as the Rig knows it."""
    t: float                    # the contact (the sound)
    point: tuple                # contact (x, y, z)
    a: object                   # a' in [0, 1] (core.Contact.a; a_norm above), None = 1.0
    go: float                   # the score's t_move: the carriage's earliest start toward this contact
    event: int = -1             # score event index
    amp: float = 1.0


@dataclass
class ArmIn:
    """One mallet arm's plan inputs."""
    hits: list                  # [HitIn], any order
    home: tuple                 # the home string's contact (x, y, z)
    hover: float                # the rest height above it (Rig.hover's y: 0.22)
    sigma: float                # sign(root_z - z_c): the arc's side
    homing: list = field(default_factory=list)   # [(t0, t1, what, a, b)] from Rig.homes(...)[k][4]
    joint_spans: dict = None    # {'elbow': rad, 'shoulder': rad} (ruler 16's IK spans), None: HOME_SPAN_GUESS
    kind: str = 'mallet'
    name: str = ''              # for issue labels only


@dataclass
class Note:
    i: int; t: float; x: float; y: float; z: float; a: float; a_raw: object; amp: float; event: int; go: float
    ioi: float = math.inf; gap: float = math.inf; ioi_next: float = math.inf
    v_in: float = 0.0; h: float = 0.0; e: float = None; a_f: float = None; T_down: float = None
    t_apex: float = None; kind: str = ''; style: str = ''; regime: str = 'still'; hurried: bool = False
    travel: int = None; travel_window: tuple = None; rise: tuple = None; hold: tuple = None
    h_low: float = None; float_apex: float = None


# ---- the plan ---------------------------------------------------------------------------------
class ArmStroke:
    """One mallet arm's planned stroke: two channels (`head` h(t), `carriage`
    x(t), plus the y_c/z_c blends), knots, per-note records, travels, issues,
    and the closed-form point and its derivatives."""
    def __init__(self, arm, head, car, knots, notes, travels, landings, joints, issues, rho, k):
        self.arm = arm; self.sigma = float(arm.sigma); self.rho = rho; self.k = k
        self.head = Channel('head', head); self.carriage = Channel('carriage', car)
        self.yc = Channel('yc', car, 'cy'); self.zc = Channel('zc', car, 'cz')
        self.knots = knots; self.notes = notes; self.travels = travels; self.issues = issues
        self.joints = joints        # {'elbow': [legs], 'shoulder': [legs]}
        L = sorted(landings)
        self._land = np.array([l[0] for l in L]) if L else np.zeros(0)
        self._fade0 = np.array([l[1] for l in L]) if L else np.zeros(0)
        self._fade1 = np.array([l[2] for l in L]) if L else np.zeros(0)
        self._lsign = np.array([l[3] for l in L]) if L else np.zeros(0)

    # -- channels and the point
    def segments(self, channel=None):
        out = []
        for ch in (self.head, self.carriage):
            if channel in (None, ch.name): out.extend(ch.segs)
        return out

    def Z(self, h, d=0): return arc_Z(h, self.rho, self.k, d)

    def h(self, t, d=0, side=+1): return self.head.ev(t, d, side)

    def x(self, t, d=0, side=+1): return self.carriage.ev(t, d, side)

    def p(self, t, side=+1):
        """The ring-free scored head point(s) at t: (..., 3)."""
        h = self.head.ev(t, 0, side)
        return np.stack([self.carriage.ev(t, 0, side), self.yc.ev(t, 0, side)+h,
                         self.zc.ev(t, 0, side)+self.sigma*self.Z(h)], -1)

    def v(self, t, side=+1):
        h, h1 = self.head.ev(t, 0, side), self.head.ev(t, 1, side)
        return np.stack([self.carriage.ev(t, 1, side), self.yc.ev(t, 1, side)+h1,
                         self.zc.ev(t, 1, side)+self.sigma*self.Z(h, 1)*h1], -1)

    def a(self, t, side=+1):
        h, h1, h2 = (self.head.ev(t, d, side) for d in (0, 1, 2))
        return np.stack([self.carriage.ev(t, 2, side), self.yc.ev(t, 2, side)+h2,
                         self.zc.ev(t, 2, side)+self.sigma*(self.Z(h, 2)*h1*h1+self.Z(h, 1)*h2)], -1)

    def j(self, t, side=+1):
        h, h1, h2, h3 = (self.head.ev(t, d, side) for d in (0, 1, 2, 3))
        return np.stack([self.carriage.ev(t, 3, side), self.yc.ev(t, 3, side)+h3,
                         self.zc.ev(t, 3, side)+self.sigma*(self.Z(h, 3)*h1**3+3*self.Z(h, 2)*h1*h2+self.Z(h, 1)*h3)], -1)

    def rest_point(self):
        """Where the path rests before the first note (the hover above home, on
        the arc). API for checks (the M1 handoff's stroke_check / contract)."""
        return self.p(-1e9)

    # -- the carriage's rings and pawl
    def detent(self, t):
        """The detent ring on the carriage (m along x) at t: a damped sine from
        each stepped landing in the travel's direction, faded to zero before
        the next step moves. Zero away from stepped travels."""
        scalar = np.ndim(t) == 0; t = np.atleast_1d(np.asarray(t, float)); out = np.zeros_like(t)
        if self._land.size:
            i = np.searchsorted(self._land, t, side='right')-1; ok = (i >= 0)
            i = np.clip(i, 0, None); ok &= t < self._fade1[i]
            if ok.any():
                tau = t[ok]-self._land[i[ok]]
                fade = 1.0-s345((t[ok]-self._fade0[i[ok]])/(self._fade1[i[ok]]-self._fade0[i[ok]]))
                out[ok] = ring_detent(tau, self._lsign[i[ok]])*fade
        return float(out[0]) if scalar else out

    def carriage_x(self, t): return self.carriage.ev(t)+self.detent(t)

    def pawl_ride(self, t):
        """In [0, 1]: a smoothstep of the scored tooth rate |x'|/PITCH over
        PAWL_RIDE_BAND, on freewheel travels only. A stepped (or homing) travel
        stops on every detent, so its pawl always has the dwell to fall into the
        gullet: it drops each tooth, whatever the step's peak rate."""
        scalar = np.ndim(t) == 0; t = np.atleast_1d(np.asarray(t, float))
        rate = np.abs(self.carriage.ev(t, 1))/_PITCH; lo, hi = PAWL_RIDE_BAND
        free = self._freewheel[self.carriage.index(t)]
        out = np.where(free, smoothstep((rate-lo)/(hi-lo)), 0.0)
        return float(out[0]) if scalar else out

    @property
    def _freewheel(self):
        f = getattr(self, '_fw', None)
        if f is None:
            f = self._fw = np.array([g.extra.get('regime') == 'freewheel' for g in self.carriage.segs])
        return f

    def ride_times(self, levels=RIDE_ROWS):
        """The instants the tooth rate crosses each of `levels` (fractions of
        PAWL_RIDE_BAND): pawl_ride is a smoothstep of the rate, so rows there let a
        bake's straight lines between rows follow it."""
        lo, hi = PAWL_RIDE_BAND; out = []
        for g in self.carriage.segs:
            if g.extra.get('regime') != 'freewheel' or not (np.isfinite(g.t0) and np.isfinite(g.t1)): continue
            dc = _dcoef(g.c, 1); ts = np.linspace(0.0, g.t1-g.t0, 257)
            for u in levels:
                f = np.abs(_horner(dc, ts))/_PITCH-(lo+(hi-lo)*u)
                for k in np.nonzero(np.sign(f[:-1])*np.sign(f[1:]) < 0)[0]:
                    a, b = ts[k], ts[k+1]; fa = f[k]
                    for _ in range(60):
                        m = .5*(a+b); fm = abs(float(_horner(dc, np.array([m]))[0]))/_PITCH-(lo+(hi-lo)*u)
                        if np.sign(fm) == np.sign(fa): a, fa = m, fm
                        else: b = m
                    out.append(g.t0+.5*(a+b))
        return np.array(sorted(out))

    def clicks(self):
        """[dict(t, pawl, step, k, n, regime, travel)] a tooth: freewheel clicks at
        the mid-tooth crossing, stepped and homing clicks at the landing (the
        audio)."""
        out = []
        for kn in self.knots:
            if kn.kind != 'click': continue
            stepped = 't_end' in kn.extra
            out.append(dict(t=float(kn.extra['t_end'] if stepped else kn.t), pawl=kn.extra['pawl'], step=int(stepped),
                            k=kn.extra['k'], n=kn.extra['n'], regime=kn.extra['regime'], travel=kn.extra['travel']))
        out.sort(key=lambda c: c['t'])
        return out

    def click_times(self): return [(c['t'], 1.0) for c in self.clicks()]



def _arc_ok(rho, k):
    return rho > 0 and k > 0


class _Builder:
    """Cursor-built channels: every segment starts where the last one ended
    (the same float), so each channel is contiguous by construction and a
    segment's duration is the float difference its coefficients were solved for."""
    def __init__(self):
        self.head = []; self.car = []; self.th = -np.inf; self.tc = -np.inf
        self.hval = None; self.xval = None; self.yval = None; self.zval = None

    @staticmethod
    def _coef(law, args, T):
        if law == 'hold': return law_hold(*args)
        if law == '3-4-5': return law_345(args[0], args[1], T)
        if law == 'quintic hermite': return law_hermite(*args, T)
        if law == 'ballistic': return law_ballistic(*args)
        raise ValueError(law)

    def H(self, t1, law, tag, event, args, **extra):
        """Head segment from the cursor to t1."""
        t0 = self.th
        if not t1 > t0:
            if t1 > t0-1e-9: return None          # nothing to add
            raise ValueError(f'head {tag}: t1 {t1} before the cursor {t0}')
        c = self._coef(law, args, t1-t0 if np.isfinite(t0) else 1.0)
        # the law's boundary data, declared beside the coefficients: the declared jerk is the
        # law's closed form on these (law_coef), and ruler 6c rebuilds it from them on its own
        if law == 'quintic hermite':
            extra.update(p0=args[0], v0=args[1], a0=args[2], p1=args[3], v1=args[4], a1=args[5])
        elif law == 'ballistic':
            extra.update(p0=args[0], v0=args[1], a=args[2])
        elif law == '3-4-5':
            extra.update(p0=args[0], p1=args[1])
        s = Seg(t0, t1, c, law, tag, 'head', event, extra); self.head.append(s); self.th = t1
        self.hval = float(s.ev(t1)) if np.isfinite(t1) else float(c[0])
        return s

    def C(self, t1, law, tag, event, args, yz0, yz1, x0=None, x1=None, **extra):
        """Carriage segment from the cursor to t1 (x by `law`, y_c/z_c blended
        on x's normalised law from yz0 at x0 to yz1 at x1)."""
        t0 = self.tc
        if not t1 > t0:
            if t1 > t0-1e-9: return None
            raise ValueError(f'carriage {tag}: t1 {t1} before the cursor {t0}')
        T = t1-t0 if np.isfinite(t0) else 1.0
        c = self._coef(law, args, T)
        if x0 is None or abs(x1-x0) <= 1e-12:
            if law == 'hold' or (abs(yz1[0]-yz0[0]) <= 1e-12 and abs(yz1[1]-yz0[1]) <= 1e-12):
                cy, cz = law_hold(yz1[0] if law != 'hold' else yz0[0]), law_hold(yz1[1] if law != 'hold' else yz0[1])
            else:
                cy, cz = law_345(yz0[0], yz1[0], T), law_345(yz0[1], yz1[1], T)
        else:
            ry = (yz1[0]-yz0[0])/(x1-x0); rz = (yz1[1]-yz0[1])/(x1-x0)
            cy = c*ry; cy[0] += yz0[0]-x0*ry
            cz = c*rz; cz[0] += yz0[1]-x0*rz
        s = Seg(t0, t1, c, law, tag, 'carriage', event, extra, cy=cy, cz=cz); self.car.append(s); self.tc = t1
        return s


def _down_ok(h, v, a0, Td, rho, k, a_end):
    """Is a downstroke from (h, 0, a0) to (0, -v, a_end) over Td legal: h strictly
    falling, s >= S_MIN, |a| (on the arc) <= A_MAX_G off A_MAX_GUARD of the contact."""
    if G*Td*Td/(2*h) < S_MIN-1e-12: return False
    c = law_hermite(h, 0.0, a0, 0.0, -v, a_end, Td); tau = np.linspace(0, Td, 401)[1:]
    hd = _horner(_dcoef(c, 1), tau)
    if np.any(hd >= 0): return False
    m = tau <= Td-A_MAX_GUARD
    hh = _horner(c, tau[m]); h1 = hd[m]; h2 = _horner(_dcoef(c, 2), tau[m])
    az = arc_Z(hh, rho, k, 2)*h1*h1+arc_Z(hh, rho, k, 1)*h2
    return bool(np.all(np.hypot(h2, az) <= A_MAX_G*G+1e-9))


def t_down_long(h, v, a0, rho, k, ramp=True):
    """T_down for a downstroke from rest (a0 = 0) or a Dahl wind-up (a0 = A_TOP):
    T_DOWN_LONG lengthened toward T_DOWN_MAX as h grows (ramp), and further
    until legal (h strictly falling, s >= S_MIN, |a| <= A_MAX_G off the contact).
    ramp=False: the least legal T_down from T_DOWN_LONG. Returns (T_down, ok)."""
    nom = T_DOWN_LONG+(T_DOWN_MAX-T_DOWN_LONG)*min(max((h-TD_H0)/(TD_H1-TD_H0), 0.0), 1.0)*bool(ramp)
    Td = nom
    while Td <= T_DOWN_MAX+1e-12:
        if _down_ok(h, v, a0, Td, rho, k, A_END_G*G): return Td, True
        Td += TD_STEP
    return nom, False


def _inpos(D, T):
    """How long before its end (or after its start) a 3-4-5 over T covering D is
    within ARRIVE_POS of its end (start): D (10 w^3 - 15 w^4 + 6 w^5) = ARRIVE_POS,
    w = tau/T, by Newton from the cubic term (arrays)."""
    D = np.maximum(np.abs(np.asarray(D, float)), 1e-12); T = np.asarray(T, float)
    w = np.minimum(np.cbrt(ARRIVE_POS/(10*D)), .5)
    for _ in range(4):
        f = D*w**3*(10-15*w+6*w*w)-ARRIVE_POS; df = D*w*w*(30-60*w+30*w*w)
        w = np.clip(w-f/np.maximum(df, 1e-30), 0.0, .5)
    return w*T


def _valley(V):
    """Ruler 8's '8 rise' valley on sampled upward speeds V (candidates along axis 0): the least V over the
    lesser of the greatest V before and after it, where that lesser peak passes STILL_V (1 elsewhere: a speed
    that only falls, or only climbs, has no valley)."""
    pre = np.maximum.accumulate(V, -1); post = np.flip(np.maximum.accumulate(np.flip(V, -1), -1), -1)
    den = np.minimum(pre, post)
    return np.min(np.where(den > STILL_V, V/np.maximum(den, 1e-12), 1.0), -1)


def _wind_coef(p0, v0, a0, p1, a1, R):
    """(c3, c4, c5) of the quintic from (p0, v0, a0) to (p1, 0, a1) over R (law_hermite's, on arrays)."""
    R2, R3 = R*R, R*R*R
    return ((20*(p1-p0)-12*v0*R-(3*a0-a1)*R2)/(2*R3), (30*(p0-p1)+16*v0*R+(3*a0-2*a1)*R2)/(2*R3*R),
            (12*(p1-p0)-6*v0*R-(a0-a1)*R2)/(2*R3*R2))


def _flow(ts, v0, af, tw, r1, h, a1=0.0):
    """Flowing rises on the grid ts (s after the contact), one candidate a row (v0, af, tw, r1 broadcast to
    1-D arrays): the float (0, v0, -af) to tw, a quintic wind-up from there to (h, 0, a1) at r1, parked at h
    after. Returns (H, V, ok, (c3, c4, c5, hw, vw)): ok where the rise FLOWS, the float still rising at the
    handover (> STILL_V), the wind-up rising over its open span and coming to h from below (a1 = 0: its end
    jerk positive) and never past it, and every valley of the speed from RISE_SKIP keeping FLOW_K."""
    v0, af, tw, r1 = (np.ravel(x) for x in np.broadcast_arrays(*(np.asarray(x, float) for x in (v0, af, tw, r1))))
    vw = v0-af*tw; hw = tw*(v0-.5*af*tw); R = np.maximum(r1-tw, 1e-6)
    c3, c4, c5 = _wind_coef(hw, vw, -af, h, a1, R)
    t = ts[None, :]; tau = t-tw[:, None]; fl = t < tw[:, None]; wd = ~fl & (t < r1[:, None])
    col = lambda x: x[:, None]
    Vw = col(vw)+tau*(-col(af)+tau*(3*col(c3)+tau*(4*col(c4)+tau*5*col(c5))))
    H = np.where(fl, t*(col(v0)-.5*col(af)*t),
                 np.where(wd, col(hw)+tau*(col(vw)+tau*(-.5*col(af)+tau*(col(c3)+tau*(col(c4)+tau*col(c5))))), h))
    V = np.where(fl, col(v0)-col(af)*t, np.where(wd, Vw, 0.0))
    ok = (vw > STILL_V) & (r1 > tw+1e-6) & np.all(~wd | (Vw > 0), 1) & np.all(H <= h+1e-9, 1)
    ok &= _valley(V[:, ts >= RISE_SKIP]) >= FLOW_K
    if a1 == 0: ok &= 6*c3+24*c4*R+60*c5*R*R > 0
    return H, V, ok, (c3, c4, c5, hw, vw)


def _top_catch(v0, af):
    """A rest's apex catch (A11): (t_c, h_c, v_c, t_r, h_r), times after the contact. The float (0, v0, -a_f)
    hands over, still rising, D = TOP_SHARE (t_f - RISE_SKIP) before its free apex t_f = v0/a_f, at (h_c, v_c,
    -a_f) = (h_1 - a_f D^2/2, a_f D, -a_f), to one quintic hermite to (h_r, 0, 0) over T = t_r - t_c, taken in
    its quartic family (c5 = 0): a(s) = -(1 - s)(a_f + b s), s = tau/T, b = 6 (v_c/T - a_f/2), h_r = h_c +
    v_c T/2 - a_f T^2/12; a <= 0 (never reversing, no bob) for T <= 3 v_c/a_f, C2 at both joins. Its shortest
    member, b = sqrt3 a_f (T = D/(1/2 + sqrt3/6) = 1.268 D), rests exactly at the free apex h_1 = v0^2/(2 a_f)
    (the speed integral gives v_c = a_f T (1/2 + sqrt3/6), the distance exactly v_c^2/(2 a_f)) at a peak brake
    (a_f + b)^2/(4 b) = 1.077 a_f (s = 0.211); T is lengthened to TOP_MIN_T, and to where that peak comes to
    TOP_BRAKE_G (never below a_f, where the catch starts), resting a little above h_1."""
    tf = v0/af; D = TOP_SHARE*(tf-RISE_SKIP); vc = af*D; hc = v0*v0/(2*af)-.5*af*D*D
    T = max(D/(.5+math.sqrt(3)/6), TOP_MIN_T); B = TOP_BRAKE_G*G
    if (.5+1/math.sqrt(3))*af > B:
        b = max(2*B-af+2*math.sqrt(max(B*(B-af), 0.0)), af); T = max(T, vc/(.5*af+b/6))
    T = min(T, 3*vc/af)
    return tf-D, hc, vc, tf-D+T, hc+vc*T/2-af*T*T/12


def _coast_fit(v0, af, tw, T, h, jc, Zh):
    """Coasting rises that arrive with a carriage (arrays tw, jc; v0, af scalars or arrays broadcast with them):
    the float hands over at tw to a constant-jerk ease to a = 0 at the coast speed v_m, a coast at v_m, and the
    stop: a 3-4-5's decelerating half (the quintic (p, v_m, 0) to (h, 0, 0) over T_s covering 8/15 v_m T_s, end
    jerk 8 v_m / T_s^2) whose in-position lead is the carriage's (end jerk jc on the arc, Zh = |dp/dh| at h), all
    ending at T. The ease (te >= EASE_MIN, v_m >= COORD_MOVING) is found on a scan then bisected. The speed never
    rises: no valley. Returns (te, tc, Ts, ok)."""
    tw, jc, v0, af = (np.ravel(x) for x in np.broadcast_arrays(*(np.asarray(x, float) for x in (tw, jc, v0, af))))
    vw = v0-af*tw; hw = tw*(v0-.5*af*tw); te_hi = 2*(vw-COORD_MOVING)/af
    col = lambda x: x[:, None]

    def fit(te):
        vm = np.maximum(col(vw)-.5*col(af)*te, 1e-9); hm = col(hw)+col(vw)*te-col(af)*te*te/3; Ts = np.sqrt(8*vm*Zh/col(jc))
        tc = (h-hm-8/15*vm*Ts)/vm
        return col(tw)+te+tc+Ts-T, tc, Ts
    E = EASE_MIN+np.linspace(0.0, 1.0, 33)[None, :]*col(te_hi-EASE_MIN)
    r, tc, _ = fit(E)
    good = (r[:, :-1] <= 0) & (r[:, 1:] > 0) & (tc[:, 1:] >= 0)
    ok = good.any(1) & (te_hi > EASE_MIN)
    k = np.argmax(good, 1); n = np.arange(tw.size)
    lo, hi = E[n, k], E[n, np.minimum(k+1, E.shape[1]-1)]
    for _ in range(48):
        m = .5*(lo+hi); rm = fit(m[:, None])[0][:, 0]
        lo = np.where(rm <= 0, m, lo); hi = np.where(rm <= 0, hi, m)
    te = .5*(lo+hi); _, tc, Ts = fit(te[:, None])
    tc, Ts = tc[:, 0], Ts[:, 0]
    return te, np.maximum(tc, 0.0), Ts, ok & (tc >= -1e-9)


def _coast(ts, v0, af, tw, te, tc, Ts, h):
    """Coasting rises (_coast_fit) on the grid ts (s after the contact), one a row (v0, af scalars or rows).
    Returns (H, V)."""
    tw, te, tc, Ts, v0, af = (np.ravel(x) for x in np.broadcast_arrays(*(np.asarray(x, float) for x in (tw, te, tc, Ts, v0, af))))
    col = lambda x: x[:, None]; t = ts[None, :]
    vw = v0-af*tw; hw = tw*(v0-.5*af*tw); vm = vw-.5*af*te; hm = hw+vw*te-af*te*te/3; ps = hm+vm*tc
    t1, t2, t3 = tw+te, tw+te+tc, tw+te+tc+Ts
    s = t-col(tw); c = t-col(t1); u = np.clip((t-col(t2))/col(Ts), 0.0, 1.0)
    c3, c4, c5 = _wind_coef(ps, vm, 0.0, h, 0.0, Ts)
    q = u*col(Ts); a = col(af)
    Hs = col(ps)+q*(col(vm)+q*q*(col(c3)+q*(col(c4)+q*col(c5))))
    Vs = col(vm)+q*q*(3*col(c3)+q*(4*col(c4)+q*5*col(c5)))
    H = np.where(t < col(tw), t*(col(v0)-.5*a*t),
                 np.where(t < col(t1), col(hw)+s*(col(vw)+s*(-.5*a+s*a/(6*col(te)))),
                          np.where(t < col(t2), col(hm)+c*col(vm), np.where(t < col(t3), Hs, h))))
    V = np.where(t < col(tw), col(v0)-a*t,
                 np.where(t < col(t1), col(vw)-a*s+a*s*s/(2*col(te)),
                          np.where(t < col(t2), col(vm), np.where(t < col(t3), Vs, 0.0))))
    return H, V


def _rest(ts, v0, af, r0, r1, h):
    """Rests on the grid ts (s after the contact), one candidate a row: the float, the apex catch (_top_catch),
    still at h_r to r0, a 3-4-5 wind-up from rest to h at r1, parked at h after. Returns (H, V)."""
    r0, r1 = (np.ravel(x) for x in np.broadcast_arrays(np.asarray(r0, float), np.asarray(r1, float)))
    tc, hc, vc, tr, hr = _top_catch(v0, af); c3, c4, _ = _wind_coef(hc, vc, -af, hr, 0.0, tr-tc); t = ts[None, :]
    s = t-tc; u = np.clip((t-r0[:, None])/(r1-r0)[:, None], 0.0, 1.0); D = h-hr
    H = np.where(t < tc, t*(v0-.5*af*t), np.where(t < tr, hc+s*(vc+s*(-.5*af+s*(c3+s*c4))), hr+D*s345(u)))
    V = np.where(t < tc, v0-af*t, np.where(t < tr, vc+s*(-af+s*(3*c3+s*4*c4)), D/(r1-r0)[:, None]*30*u*u*(1-u)**2))
    return np.broadcast_to(H, (r0.size, ts.size)), np.broadcast_to(V, (r0.size, ts.size))


def _arc_speed(H, V, rho, k):
    return np.abs(V)*np.sqrt(1+arc_Z(H, rho, k, 1)**2)


def _run(b):
    """Per row of the boolean array b, the longest run of True (samples): the run ending at each sample is its
    index less the last False's at or before it."""
    b = np.atleast_2d(b); i = np.arange(b.shape[-1])
    return (i-np.maximum.accumulate(np.where(b, -1, i), axis=-1)).max(-1) if b.shape[-1] else np.zeros(b.shape[0], int)


def _least(peak, norm, ok, prefer=None):
    """The candidate (index) of least peak, peaks within PEAK_TIE of it equal: of those the `prefer`red if any
    is among them, then the least norm."""
    if not np.any(ok): return None
    pk = np.where(ok, peak, np.inf); tie = ok & (pk <= pk.min()+PEAK_TIE)
    if prefer is not None and np.any(tie & prefer): tie &= prefer
    return int(np.argmin(np.where(tie, norm, np.inf)))


def dahl_float(vp, h, Td, ioi, rho, k):
    """A Dahl loop's rise, one flowing gesture from the contact to the apex: the
    rebound e·vp floats at -a_f and hands over at t_w, still rising, to ONE
    quintic wind-up from (h_w, v_w, -a_f) to the prep (h, 0, A_TOP) over
    R = ioi - Td - t_w, flowing into the downstroke. (e, a_f, t_w) is the grid
    point (e and a_f one step inside ruler 8's bands; t_w on FLOW_N points from
    FLOAT_MIN to the float's apex and by DAHL_RISE_BY x IOI) whose rise flows
    (_flow: rising throughout, never past h, every speed valley >= FLOW_K) with
    the least peak head speed on the arc from the contact + RISE_SKIP, peaks
    within PEAK_TIE equal and the least COORD_P-norm of the rise's speed between
    them. Measured on chamber/expanded (arc speed from the contact +
    RISE_SKIP; valley of h' as _valley reads it; steps on the 30 fps grid,
    k/30): a' = 1 (h 0.459 m, IOI 0.714) e 0.50, a_f 0.52 g, t_w 68 ms (91 mm
    up), R 0.414 s, peak 1.49 m/s (the wind-up's, at 248 ms; the launch
    1.48), least valley 0.88, steps 3-46 mm a frame (the float handed over
    early, the wind-up carrying the rise; the old float to the apex at e
    0.69, a_f 0.84 g peaked 2.08 and dipped to -0.02); a' 0.12-0.17 (h
    0.277-0.285 m) e 0.31, a_f 0.62-0.64 g, t_w 20 ms (17 mm up), R 0.54 s,
    peak 0.90 m/s, the launch itself (old 1.08-1.13), then a sag to
    0.52-0.55 at 133-140 ms and the wind-up's own peak 0.70-0.73 at
    333-342 ms; valley 0.82-0.83, steps 3-28 mm a frame. e sits on the grid's
    lower bound there (E_LO + DAHL_E_STEP): the least rebound is the least
    peak. Returns (e, a_f, t_w, R, ok);
    ok False: nothing on the grid flows, the least peak with R > 0 regardless
    (R is the true one; the caller records the issue)."""
    E = np.arange(E_LO+DAHL_E_STEP, E_HI-DAHL_E_STEP+1e-9, DAHL_E_STEP)
    A = np.arange(AF_LO_G+DAHL_AF_STEP, AF_HI_G-DAHL_AF_STEP+1e-9, DAHL_AF_STEP)*G
    T = ioi-Td; ts = np.linspace(RISE_SKIP, T, FLOW_SAMPLES+1); a1 = A_TOP_G*G
    U = np.linspace(0.0, 1.0, FLOW_N); rows = []
    for e in E:                                 # a row of the grid at a time (bounded memory)
        af, u = (m.ravel() for m in np.meshgrid(A, U, indexing='ij'))
        v0 = e*vp; tw_hi = np.minimum(np.minimum(v0/af, DAHL_RISE_BY*ioi), T-1e-3)
        tw = FLOAT_MIN+u*(tw_hi-FLOAT_MIN); pos = tw_hi > FLOAT_MIN
        H, V, ok, _ = _flow(ts, v0, af, tw, T, h, a1)
        sp = _arc_speed(H, V, rho, k)
        rows.append((np.full_like(af, e), af, tw, sp.max(1), np.mean(sp**COORD_P, 1)**(1/COORD_P), ok & pos, pos))
    e, af, tw, peak, norm, ok, pos = (np.concatenate(c) for c in zip(*rows))
    j = _least(peak, norm, ok); feasible = j is not None
    if not feasible: j = _least(peak, norm, pos)
    e, af, tw = float(e[j]), float(af[j]), float(tw[j])
    return e, af, tw, T-tw, feasible


def _glide(D, T, gl):
    """A glide over T covering D, its cruise `gl` of T: (Th, Tc, Vp, d, acc), each half a half 3-4-5 over Th
    covering d to the cruise speed Vp, and acc the halves' peak |x''| (gl = 0: the plain 3-4-5, acc A345 |D|/T^2)."""
    Th = .5*(1-gl)*T; Tc = gl*T; Vp = D/(2*Th/_V345+Tc); d = Vp*Th/_V345
    return Th, Tc, Vp, d, abs(_A345_HALF*d/Th**2)


def _glide_v(tau, T, D, gl):
    """x' of that glide at tau (array) from its start (0 outside [0, T])."""
    Th, Tc, Vp, _, _ = _glide(D, T, gl); tau = np.asarray(tau, float)
    def ds(u):
        u = np.clip(u, 0.0, 1.0); return 30*u*u*(1-u)**2
    return np.where(tau < Th+Tc, np.where(tau < Th, Vp/_V345*ds(tau/(2*Th)), Vp), Vp/_V345*ds((tau-Tc)/(2*Th)))


def _level(cu, dx, yz0, yz1, who):
    """(dy/dx, dz/dx) of a contact pair, raising unless level: the head's start and in-position instants a
    coordinated move times are its own channel's (ruler 22 sync); a sloped pair moves the head's y/z with the
    carriage, which nothing there times: fail loudly, not quietly."""
    ry, rz = (yz1[0]-yz0[0])/dx, (yz1[1]-yz0[1])/dx
    if abs(ry) > 1e-12 or abs(rz) > 1e-12:
        raise ValueError(f'{who}: sloped contact pair at t={cu.t:.3f} (dy/dx {ry:.3g}, dz/dx {rz:.3g}); '
                         'every mallet contact shares y and z today, and the coordinated shapes assume it')
    return ry, rz


def _freewheel_least(dx):
    """A freewheel's least unhurried time (3 g, 1.0 E a frame)."""
    return motion_timing.smooth_s('mallet', dx, motion_timing.FREE_G, motion_timing.FREE_RHO)


class _Planner:
    def __init__(self, arm, jerk=True):
        self.arm = arm; self.jerk = jerk; self.B = _Builder(); self.knots = []; self.travels = []; self.landings = []
        self.issues = []; self.joints = {}
        self.rho, self.k = arc(arm.kind)
        if not _arc_ok(self.rho, self.k): raise ValueError('bad arc')

    def issue(self, t, what, **kw):
        self.issues.append(dict(t=float(t), aid=self.arm.name, what=what, **kw))

    # ---- the carriage --------------------------------------------------------------------
    def hold_x(self, t1, x, yz, tag='hold', event=-1, **extra):
        self.B.C(t1, 'hold', tag, event, (x,), yz, yz, **extra)

    def travel(self, x0, yz0, x1, yz1, ta, tb, regime, event, period=None, tag='travel',
               reg_label=None, glide=0.0, **extra):
        """The carriage from x0 at ta to x1 at tb: 'step' (period a tooth: a 3-4-5
        over STEP_MOVE of it and a dwell, a click knot at each step's start with
        t_end = the landing, a detent knot at the landing) or 'freewheel' (one
        3-4-5, a click per tooth where x crosses mid-tooth). Returns the travel id.

        `hurried` is judged on the window the travel actually runs, [ta, tb]
        (not the score's go-to-contact window, which a hold or a first note
        shortens): a freewheel whose 3-4-5 at 3 g and 1.0 E a frame needs more
        than tb - ta (motion_timing.hurried); a stepped travel never (each tooth
        is a 3 g step). A freewheel shorter than the 3-4-5 at the hurried
        ceilings (motion_timing.contact_floor_s) is an issue."""
        B = self.B; tid = len(self.travels); n = motion_timing.teeth(x1-x0); D = x1-x0
        label = reg_label or regime
        hurried = regime == 'freewheel' and motion_timing.hurried('mallet', D, tb-ta)
        if regime == 'freewheel' and tb-ta < motion_timing.contact_floor_s('mallet', D)-1e-9:
            self.issue(tb, 'freewheel below the hurried ceilings', window=tb-ta,
                       floor=motion_timing.contact_floor_s('mallet', D))
        rec = dict(id=tid, t0=ta, t1=tb, x0=x0, x1=x1, teeth=n, regime=label, hurried=bool(hurried), event=event,
                   clicks=[], period=period, window=extra.get('window'))
        self.hold_x(ta, x0, yz0)
        info = dict(regime=label, travel=tid, hurried=bool(hurried))
        if regime == 'step':
            d = D/n; sign = 1.0 if D > 0 else -1.0
            per = (tb-ta)/n; Tm = motion_timing.STEP_MOVE*per; rec['period'] = per; rec['Tm'] = Tm
            for kk in range(n):
                s0 = B.tc; xa = x0+kk*d; xb = x0+(kk+1)*d if kk < n-1 else x1
                ya = [yz0[j]+(yz1[j]-yz0[j])*kk/n for j in (0, 1)]; yb = [yz0[j]+(yz1[j]-yz0[j])*(kk+1)/n for j in (0, 1)]
                land = ta+kk*per+Tm if kk < n-1 else tb-(per-Tm)
                end = ta+(kk+1)*per if kk < n-1 else tb
                g = B.C(land, '3-4-5', tag, event, (xa, xb), ya, yb, xa, xb, step=kk, **info, **extra)
                B.C(end, 'hold', tag, event, (xb,), yb, yb, **info, **extra)
                self.knots.append(Knot(s0, 'click', None, event, dict(k=kk, n=n, regime=label, pawl='drop', travel=tid,
                                                                       t_end=g.t1)))
                dwell = end-g.t1
                # the detent ring starts here along the travel's sign, fading out over fade
                self.knots.append(Knot(g.t1, 'detent', np.zeros(3), event, dict(k=kk, n=n, travel=tid, sign=sign,
                                                                                fade=(g.t1+RING_FADE*dwell, end))))
                self.landings.append((g.t1, g.t1+RING_FADE*dwell, end, sign))
                rec['clicks'].append(g.t1)
        else:
            if glide > 0:
                # the glide: a 3-4-5's accelerating half to its peak speed, a cruise ('ballistic' at a = 0) over
                # `glide` of the window, the decelerating half (C2 at both joins: a = 0 at a 3-4-5's peak speed)
                Th, Tc, Vp, d, _ = _glide(D, tb-ta, glide)
                xa, xb = x0+d, x1-d; ta1, ta2 = ta+Th, tb-Th
                gs = [B.C(ta1, 'quintic hermite', tag, event, (x0, 0.0, 0.0, xa, Vp, 0.0), yz0, yz1, x0, x1, glide=glide, **info, **extra),
                      B.C(ta2, 'ballistic', tag, event, (xa, Vp, 0.0), yz0, yz1, x0, x1, glide=glide, **info, **extra),
                      B.C(tb, 'quintic hermite', tag, event, (xb, Vp, 0.0, x1, 0.0, 0.0), yz0, yz1, x0, x1, glide=glide, **info, **extra)]
                for g, a in zip((gs[0], gs[2]), ((x0, 0.0, 0.0, xa, Vp, 0.0), (xb, Vp, 0.0, x1, 0.0, 0.0))):
                    g.extra.update(p0=a[0], v0=a[1], a0=a[2], p1=a[3], v1=a[4], a1=a[5])
                gs[1].extra.update(p0=xa, v0=Vp, a=0.0)
            else:
                g = B.C(tb, '3-4-5', tag, event, (x0, x1), yz0, yz1, x0, x1, **info, **extra); gs = [g]
                c = g.c; T = g.T
            def xs(t):
                g = gs[min(sum(t >= q.t1 for q in gs[:-1]), len(gs)-1)]
                return float(g.ev(t)), abs(float(g.ev(t, 1)))
            for kk in range(n):
                # a click a tooth where x crosses mid-tooth (x is monotone over the travel)
                target = (kk+.5)/n; lo, hi = 0.0, 1.0
                if glide > 0:
                    lo, hi = ta, tb
                    for _ in range(64):
                        mid = .5*(lo+hi)
                        if (xs(mid)[0]-x0)/D < target: lo = mid
                        else: hi = mid
                    tk = hi; rate = xs(tk)[1]/_PITCH
                else:
                    for _ in range(64):
                        mid = .5*(lo+hi)
                        if s345(mid) < target: lo = mid
                        else: hi = mid
                    tk = g.t0+hi*T; rate = abs(float(_horner(_dcoef(c, 1), np.array([hi*T]))[0]))/_PITCH
                self.knots.append(Knot(tk, 'click', None, event, dict(k=kk, n=n, regime=label, pawl=pawl_state(rate),
                                                                       travel=tid, rate=rate)))
                rec['clicks'].append(tk)
            rec['glide'] = glide
        self.travels.append(rec)
        return tid

    # ---- the plan --------------------------------------------------------------------------------
    def run(self):
        arm = self.arm; B = self.B
        hits = sorted(arm.hits, key=lambda h: float(h.t))
        if not hits: raise ValueError('no hits')
        N = []
        for i, hh in enumerate(hits):
            x, y, z = (float(v) for v in hh.point)
            N.append(Note(i=i, t=float(hh.t), x=x, y=y, z=z, a=a_or_one(hh.a), a_raw=hh.a, amp=float(hh.amp),
                          event=int(hh.event), go=float(hh.go)))
        for p, c in zip(N, N[1:]):
            c.ioi = c.t-p.t; c.gap = c.ioi; p.ioi_next = c.ioi
        for n in N:
            n.v_in = v_in(n.a); n.h = prep(n.a, n.ioi)
        self.N = N
        hx, hy, hz = (float(v) for v in arm.home); hov = float(arm.hover)
        # ---- the rest and the homing sweep
        legs = sorted(arm.homing or [], key=lambda g: g[0])
        home_end = legs[-1][1] if legs else -np.inf
        head_joint = []
        tid_home = None
        for (t0, t1, what, a, b) in legs:
            if what == 'x':
                self.hold_x(t0, B.xval if B.xval is not None else hx, (hy, hz))
                tid = self._home_steps(a, b, t0, t1, (hy, hz))
                B.xval = b
            else:
                x = B.xval if B.xval is not None else a
                self.hold_x(t0, x, (hy, hz))
                self.hold_x(t1, x, (hy, hz))
                span = (arm.joint_spans or {}).get(what)
                assumed = span is None
                if assumed: span = HOME_SPAN_GUESS[what]
                jl = joint_legs(what, t0, t1, span)
                self.joints.setdefault(what, []).extend(jl)
                head_joint.extend((g, what, assumed) for g in jl)
        x_now = B.xval if B.xval is not None else hx
        if legs and abs(x_now-hx) > 1e-9:
            self.issue(home_end, 'homing does not end at home', x=x_now, home=hx)
        # ---- the first note
        n0 = N[0]
        Td0, ok = t_down_long(n0.h, n0.v_in, 0.0, self.rho, self.k)
        if not ok: self.issue(n0.t, 'downstroke infeasible', h=n0.h)
        t_he = n0.t-Td0; t_hs = t_he-HOLD
        go = max(n0.go, home_end)
        dx = n0.x-x_now
        regime = motion_timing.travel_regime(dx, t_hs-go) if abs(dx) > 1e-9 else 'still'
        n0.regime = regime
        if regime == 'step':
            per = motion_timing.stepped_period(dx, t_hs-go); Ttr = motion_timing.teeth(dx)*per; ta = t_hs-Ttr
        elif regime == 'freewheel':
            ta = go; Ttr = t_hs-go
            self.issue(n0.t, 'first travel freewheels (no room to step)', window=t_hs-go)
        else:
            ta = t_hs; Ttr = 0.0
        # the first rise (dip and wind-up) lasts FIRST_RISE_S, or longer where the wind-up
        # from the dip's floor to the prep wants it at W_RATE, as the room after homing allows
        hl0 = max(hov-FIRST_DIP*max(n0.h-hov, 0.0), FIRST_FLOOR)
        T_rise = max(FIRST_RISE_S, min((n0.h-hl0)/(W_RATE*(1-FIRST_DIP_FRAC)), ta-SETTLE_S-home_end))
        t_rs = ta-T_rise; t_ss = t_rs-SETTLE_S
        if t_ss < home_end:
            self.issue(n0.t, 'no room for the first settle after homing', need=home_end-t_ss)
        # head: rest at the hover (joint legs drawn on it), settle, wind up, park, cocked hold, strike
        for g, what, assumed in head_joint:
            B.H(g['t0'], 'hold', 'hold', -1, (hov,), hold='park')
            B.H(g['t1'], '3-4-5', 'home', -1, (hov, hov), joint=what, leg=g['leg'], q0=g['q0'], q1=g['q1'],
                jerk_rad=60*abs(g['q1']-g['q0'])/(g['t1']-g['t0'])**3, span_assumed=assumed)
        # rest at the hover (settling from t_ss); the anticipation: a dip below the
        # hover, then the wind-up to the prep, ending as the traverse leaves at ta;
        # the carriage then carries the parked head across, and the hold follows
        t_dip = t_rs+FIRST_DIP_FRAC*(ta-t_rs)
        B.H(t_rs, 'hold', 'hold', -1, (hov,), hold='park')
        B.H(t_dip, '3-4-5', 'wind-up', n0.event, (hov, hl0), dip=True)     # the anticipation: down, not a rise
        B.H(ta, '3-4-5', 'wind-up', n0.event, (hl0, n0.h))
        B.H(t_hs, 'hold', 'hold', n0.event, (n0.h,), hold='park')
        B.H(t_he, 'hold', 'hold', n0.event, (n0.h,), hold='cocked')
        s = B.H(n0.t, 'quintic hermite', 'stroke', n0.event, (n0.h, 0.0, 0.0, 0.0, -n0.v_in, A_END_G*G))
        self._pin(s, n0)
        n0.T_down = Td0; n0.t_apex = t_he; n0.kind = 'first'; n0.hold = (t_hs, t_he); n0.rise = (t_dip, ta)
        n0.style = 'S2 '+regime if regime != 'still' else 'park'
        if regime != 'still':
            tid = self.travel(x_now, (hy, hz), n0.x, (n0.y, n0.z), ta, t_hs, regime, n0.event, window=(go, t_hs))
            n0.travel = tid; n0.travel_window = (ta, t_hs); n0.hurried = self.travels[tid]['hurried']
        self.hold_x(n0.t, n0.x, (n0.y, n0.z), event=n0.event)
        # ---- between notes
        for pv, cu in zip(N, N[1:]):
            self._gap(pv, cu)
        # ---- after the last note: the float, a raise to H_END (flowing, or after a rest), the park
        nl = N[-1]; e = E_LOOP; af = AF_LOOP_G*G; v0 = e*nl.v_in
        nl.e, nl.a_f, nl.float_apex = e, af, v0*v0/(2*af)
        t_end = nl.t+_top_catch(v0, af)[3]+REST_MIN+END_RAISE_S
        shape = self._rise_alone(nl, nl, v0, af, t_end, t_end, H_END, rest_s=END_RAISE_S)
        self._build_rise(nl, nl, shape, v0, af, H_END, None, None, tag='raise')
        B.H(np.inf, 'hold', 'hold', nl.event, (H_END,), hold='park')
        self.hold_x(np.inf, nl.x, (nl.y, nl.z))
        # ---- knots, jerk, the result
        for n in N:
            self.knots.append(Knot(n.t, 'contact', np.array([0.0, (1+n.e)*n.v_in, 0.0]), n.event,
                                   dict(v_in=n.v_in, e=n.e)))
        st = ArmStroke(arm, B.head, B.car, None, N, self.travels, self.landings, self.joints, self.issues, self.rho, self.k)
        imp = sorted(k.t for k in self.knots if k.kind in ('contact', 'detent'))
        imp = np.array(imp) if imp else np.zeros(0)
        joins = sorted(set(st.head.joins()) | set(st.carriage.joins()))
        for t in joins:
            if imp.size and np.min(np.abs(imp-t)) <= 1e-9: continue
            self.knots.append(Knot(t, 'smooth'))
        self.knots.sort(key=lambda kn: (kn.t, kn.kind))
        st.knots = self.knots
        if self.jerk: _declare_jerk(st)
        return st

    def _pin(self, seg, n):
        seg.extra['pin'] = [n.x, n.y, n.z+self.arm.sigma*R_PIN]
        seg.extra['axis'] = [1.0, 0.0, 0.0]

    def _home_steps(self, a, b, t0, t1, yz):
        """A homing x leg tooth by tooth: teeth(b - a) periods of (t1 - t0)/n."""
        if abs(b-a) <= 1e-12:
            self.hold_x(t1, a, yz); return None
        return self.travel(a, yz, b, yz, t0, t1, 'step', -1, tag='home', reg_label='home')

    def _gap(self, pv, cu):
        """The head and the carriage from contact pv to contact cu, by the gap:
          * IOI <= FLOAT_IOI (tempo): the float straight to the next apex, a
            thrown downstroke, the carriage contact to contact
            (_contact_travel);
          * gap < HOLD_GAP: the Dahl loop (dahl_float), one flowing rise into
            the downstroke, the carriage contact to contact;
          * gap >= HOLD_GAP: the bounce loop before a hold, the float at E_LOOP
            into a rise to the park, the cocked hold, a downstroke from rest.
            The carriage, by its regime on go -> hold start: 'still' (park:
            _rise_alone); a stepped traverse that fits after the head parks
            ('S2 step': _rise_alone, the steps under the parked head); one
            that fits only from go, the toll under the loop ('step under the
            loop': _under, the float handing over to a coast that climbs
            under the steps and stops at the prep with the last landing; its
            float its own, e 0.31 under 1.48 g, the coast 0.068 m/s for
            3.85 s on bars_arm0 at 71.43 s, 0.059 for 4.16 s on bars_arm1 at
            68.21, 0.19 for 2.28 s on the bells at 68.57 and 74.29; head and
            carriage in position within 0.14 ms); a freewheel
            (_coordinate). A go after the hold start is an issue ('go after the
            hold start').
        """
        B = self.B; t0, t1 = pv.t, cu.t; ioi = t1-t0; vp = pv.v_in; h = cu.h
        dx = cu.x-pv.x; moving = abs(dx) > 1e-9
        go = max(cu.go, t0)
        hold = cu.gap >= HOLD_GAP-1e-9
        # the notation's hurried (the score's go-to-contact window): it picks S1 below; the travel's
        # declared flag is judged on the window it actually runs (travel())
        hur_n = bool(moving and motion_timing.hurried('mallet', dx, t1-cu.go))
        yz0, yz1 = (pv.y, pv.z), (cu.y, cu.z)
        if ioi <= FLOAT_IOI+1e-9:
            # ---- tempo: the rebound-led float straight to the next apex, the thrown downstroke
            best = None
            grid = np.linspace(*TD_FAST, 41)*ioi if ioi <= TD_FAST_IOI+1e-12 else np.linspace(*TD_SLOW, 26)
            for Td in grid:
                tf = ioi-Td; af = 2*h/tf**2; e = 2*h/(tf*vp); s = G*Td*Td/(2*h)
                pen = (max(0, E_LO-e)+max(0, e-E_HI)+max(0, AF_LO_G*G-af)/G+max(0, af-AF_HI_G*G)/G+max(0, S_MIN-s))
                cost = 100*pen+(e-E_AIM)**2+(Td/ioi-TD_AIM)**2
                if best is None or cost < best[0]: best = (cost, Td, tf, af, e, pen)
            _, Td, tf, af, e, pen = best
            if pen > 0: self.issue(t1, 'tempo float infeasible', e=e, af_g=af/G, T_down=Td)
            pv.e, pv.a_f, pv.float_apex = e, af, h
            cu.T_down = Td; cu.t_apex = t1-Td; cu.kind = 'tempo'; cu.style = 'float'
            B.H(t0+tf, 'ballistic', 'float', pv.event, (0.0, e*vp, -af))
            s = B.H(t1, 'quintic hermite', 'stroke', cu.event, (h, 0.0, -af, 0.0, -cu.v_in, A_END_G*G))
            self._pin(s, cu)
            self._contact_travel(pv, cu, go, t1, moving, yz0, yz1)
            return
        if not hold:
            # ---- the Dahl loop: one flowing rise (dahl_float): the rebound floats and hands over, still
            # rising, to one quintic wind-up to (h, 0, A_TOP) flowing into the downstroke
            Td, ok = t_down_long(h, cu.v_in, A_TOP_G*G, self.rho, self.k, DAHL_TD_RAMP)
            if not ok: self.issue(t1, 'downstroke infeasible', h=h)
            e, af, tw, R, ok = dahl_float(vp, h, Td, ioi, self.rho, self.k)
            if not ok: self.issue(t1, 'Dahl loop out of bounds', e=e, af_g=af/G, t_w=tw, R=R)
            v0 = e*vp; vw = v0-af*tw; hw = tw*(v0-.5*af*tw)
            pv.e, pv.a_f, pv.float_apex = e, af, v0*v0/(2*af); cu.h_low = hw
            cu.T_down = Td; cu.t_apex = t1-Td; cu.kind = 'loop'; cu.style = 'Dahl'
            B.H(t0+tw, 'ballistic', 'float', pv.event, (0.0, v0, -af))
            B.H(t1-Td, 'quintic hermite', 'wind-up', cu.event, (hw, vw, -af, h, 0.0, A_TOP_G*G))
            s = B.H(t1, 'quintic hermite', 'stroke', cu.event, (h, 0.0, A_TOP_G*G, 0.0, -cu.v_in, A_END_G*G))
            self._pin(s, cu)
            cu.rise = (t0+tw, t1-Td)
            self._contact_travel(pv, cu, go, t1, moving, yz0, yz1)
            return
        # ---- the bounce loop before a hold: the float, a rise (flowing, or after a rest) to the park, the
        # traverse, the cocked hold, the downstroke from rest
        e = E_LOOP; af = AF_LOOP_G*G; v0 = e*vp; h1 = v0*v0/(2*af)
        pv.e, pv.a_f, pv.float_apex = e, af, h1
        Td, ok = t_down_long(h, cu.v_in, 0.0, self.rho, self.k)
        if not ok: self.issue(t1, 'downstroke infeasible', h=h)
        t_he = t1-Td; t_hs = t_he-HOLD
        t_c = t0+_top_catch(v0, af)[3]          # a rest's apex catch ends here (the head still)
        cu.T_down = Td; cu.t_apex = t_he; cu.kind = 'loop+hold'; cu.hold = (t_hs, t_he)
        n = motion_timing.teeth(dx) if moving else 0
        under = False
        if moving and go < t_hs-1e-9 and motion_timing.travel_regime(dx, t_hs-go) == 'step':
            # a stepped traverse that cannot wait for a wind-up leaves under the bounce loop (below)
            under = t_hs-max(go, t_c+W_MIN) < n*motion_timing.step_period(dx)-1e-9
        if moving and go > t_hs-1e-9:
            # the schedule's go leaves no window before the hold: the head rises as for a still note, the
            # carriage runs go -> contact through the hold (ruler 21 sees it; recorded, not hidden)
            self.issue(t1, 'go after the hold start', go=go, hold_start=t_hs)
            self._build_rise(pv, cu, self._rise_alone(pv, cu, v0, af, t_hs, t_hs, h), v0, af, h, t_hs, t_he)
            cu.style = 'late go'
            self._contact_travel(pv, cu, go, t1, moving, yz0, yz1)
            return
        # The regime is the shared rule on the window the plan gives the carriage
        # (go to the hold). Where the traverse and the head's wind-up overlap they
        # are one coordinated move: they arrive together, at the traverse's last
        # landing (a stepped traverse then dwells on its detent until the hold).
        regime = motion_timing.travel_regime(dx, t_hs-go) if moving else 'still'
        cu.regime = regime
        ta = None; glide = 0.0
        # Every hold-note rise ENDS where the head must be parked: at the hold
        # ('park'), as the traverse it parks over leaves ('S2'), or with the
        # traverse's arrival ('under the loop'). Before that the head flows up
        # from the contact, or is caught at its apex, rests (>= REST_MIN) and
        # winds up from rest (_rise_alone); under a stepped traverse that
        # leaves under the loop it coasts up under the steps (_under). A
        # freewheel's rise is coordinated with it instead (_coordinate).
        if regime == 'still':
            shape = self._rise_alone(pv, cu, v0, af, t_hs, t_hs, h); cu.style = 'park'
        elif regime == 'step' and not under:
            # the head rises to the park as the carriage leaves; the carriage steps under it
            room = t_hs-max(go, t_c+W_MIN)
            per = motion_timing.stepped_period(dx, room); ta = t_hs-n*per
            shape = self._rise_alone(pv, cu, v0, af, ta, t_hs, h); cu.style = 'S2 step'
        elif regime == 'step':
            # the toll under the loop: the traverse fills its window from go, and the float hands
            # over, still rising, to a coast that climbs under the steps and stops at the prep with
            # the last landing (_under: its float's own e and a_f)
            ta, shape, e, af = self._under(pv, cu, dx, go, t_hs, h, yz0, yz1)
            v0 = e*vp; pv.e, pv.a_f, pv.float_apex = e, af, v0*v0/(2*af)
            cu.style = 'step under the loop'
        else:
            ta, shape, cu.style, glide = self._coordinate(pv, cu, dx, go, v0, af, t_hs, h, yz0, yz1)
        self._build_rise(pv, cu, shape, v0, af, h, t_hs, t_he)
        if regime != 'still':
            tid = self.travel(pv.x, yz0, cu.x, yz1, ta, t_hs, regime, cu.event, glide=glide, window=(go, t_hs))
            cu.travel = tid; cu.travel_window = (ta, t_hs); cu.hurried = self.travels[tid]['hurried']
        self.hold_x(t1, cu.x, yz1, event=cu.event)

    def _build_rise(self, pv, cu, shape, v0, af, h, t_hs, t_he, tag='wind-up'):
        """The head from the contact to the park (or, t_hs None, a coda's raise and park): ('flow', t_w, r1),
        the float to t_w and a quintic wind-up to (h, 0, 0) at r1; ('coast', t_w, t_e, t_s, r1), the float to
        t_w, the ease to t_e, the coast to t_s and the stop at r1 (_coast_fit); ('rest', r0, r1), the float handed
        over to the apex catch ('catch', _top_catch), still to r0, a 3-4-5 wind-up from rest to r1; ('low', h_l,
        t_c, r0, r1), the float to its apex, a catch down to h_l at t_c, still to r0, a 3-4-5 wind-up. Then the
        park and cocked hold and the downstroke from rest."""
        B = self.B; t0 = pv.t; kind = shape[0]
        if kind in ('flow', 'coast'):
            tw, r1 = shape[1], shape[-1]; tau = tw-t0; vw = v0-af*tau; hw = tau*(v0-.5*af*tau)
            B.H(tw, 'ballistic', 'float', pv.event, (0.0, v0, -af))
            if kind == 'flow':
                B.H(r1, 'quintic hermite', tag, cu.event, (hw, vw, -af, h, 0.0, 0.0))
            else:
                _, _, te, ts, _ = shape; T = te-tw; vm = vw-.5*af*T; hm = hw+vw*T-af*T*T/3
                B.H(te, 'quintic hermite', tag, cu.event, (hw, vw, -af, hm, vm, 0.0))   # the ease (constant jerk)
                if ts > te+1e-9: B.H(ts, 'ballistic', tag, cu.event, (hm, vm, 0.0))   # the coast
                B.H(r1, 'quintic hermite', tag, cu.event, (hm+vm*max(ts-te, 0.0), vm, 0.0, h, 0.0, 0.0))   # the stop
            lo, rise = hw, (tw, r1)
        else:
            if kind == 'rest':
                # the float hands over, still rising, to the apex catch: ruler 8 judges the float to the
                # handover and the 'catch' on its own ('8 catch'), its rest against the free apex
                _, r0, r1 = shape; tc, hc, vc, tr, hl = _top_catch(v0, af)
                B.H(t0+tc, 'ballistic', 'float', pv.event, (0.0, v0, -af))
                B.H(t0+tr, 'quintic hermite', 'catch', pv.event, (hc, vc, -af, hl, 0.0, 0.0))
            else:
                _, hl, tc, r0, r1 = shape; tf = v0/af
                B.H(t0+tf, 'ballistic', 'float', pv.event, (0.0, v0, -af))
                B.H(tc, 'quintic hermite', 'rebound', pv.event, (v0*v0/(2*af), 0.0, -af, hl, 0.0, 0.0))
            if r0 > B.th+1e-12: B.H(r0, 'hold', 'hold', cu.event, (hl,), hold='park')
            B.H(r1, '3-4-5', tag, cu.event, (hl, h))
            lo, rise = hl, (r0, r1)
        if t_hs is None: return             # the coda: the last note's own record stays its approach's
        cu.h_low, cu.rise = lo, rise
        B.H(t_hs, 'hold', 'hold', cu.event, (h,), hold='park')
        B.H(t_he, 'hold', 'hold', cu.event, (h,), hold='cocked')
        s = B.H(cu.t, 'quintic hermite', 'stroke', cu.event, (h, 0.0, 0.0, 0.0, -cu.v_in, A_END_G*G))
        self._pin(s, cu)

    def _rise_alone(self, pv, cu, v0, af, r1, t_hs, h, rest_s=None):
        """A hold note's rise with no carriage moving under it, ending (parked) by r1: of the flowing rises
        (_flow: the float handed over on FLOW_N times, a wind-up ending on FLOW_N times up to r1) and the rest
        (the apex catch, still >= REST_MIN, a 3-4-5 wind-up from rest of _w_room or what is left, >= W_MIN, ending
        at r1; its rest at most H_LOW_PREP x h), the least peak head speed on the arc from the contact +
        RISE_SKIP (within PEAK_TIE the rest, else the least COORD_P-norm to t_hs). With no carriage moving that
        speed on the arc IS the tool's world speed _coordinate chooses by (x' = 0: its norm() vector reduces to
        |h'| sqrt(1 + Z'(h)^2)), so both choose by one rule. (An 'S2 step' carriage steps only after r1, under
        the parked head, the same steps for every candidate; at 0.89-0.92 m/s it stays under every rise's launch,
        1.30-1.64 m/s, so the arc speed and the world speed pick alike there too.)
        `rest_s`: a fixed wind-up length from rest (the coda's END_RAISE_S, its end then free). No shape: the
        catch low (_low) and an issue."""
        t0 = pv.t; tf = v0/af; T = r1-t0
        ts = np.arange(0.0, t_hs-t0, COORD_DT)
        tw = np.linspace(FLOAT_MIN, tf, FLOW_N+1)[:-1]
        R1 = np.linspace(min(tf, T), T, FLOW_N)
        TW, RR = (m.ravel() for m in np.meshgrid(tw, R1, indexing='ij'))
        H, V, ok, _ = _flow(ts, v0, af, TW, RR, h)
        sp = _arc_speed(H, V, self.rho, self.k); m = ts >= RISE_SKIP
        peak = sp[:, m].max(1); norm = np.mean(sp**COORD_P, 1)**(1/COORD_P)
        shapes = [('flow', t0+a, t0+b) for a, b in zip(TW, RR)]
        tr, hr = _top_catch(v0, af)[3:]
        W = rest_s if rest_s is not None else min(self._w_room(h, hr), T-tr-REST_MIN)
        r0 = tr+REST_MIN if rest_s is not None else T-W
        if W >= W_MIN-1e-9 and r0 >= tr+REST_MIN-1e-9 and hr <= H_LOW_PREP*h+1e-12:
            Hr, Vr = _rest(ts, v0, af, r0, r0+W, h); spr = _arc_speed(Hr, Vr, self.rho, self.k)
            peak = np.append(peak, spr[:, m].max(1)); norm = np.append(norm, np.mean(spr**COORD_P, 1)**(1/COORD_P))
            ok = np.append(ok, True); shapes.append(('rest', t0+r0, t0+r0+W))
        # a rest whose peak ties a flow's (both the float's launch, mostly) is kept: the head waits low through
        # a long gap as the first note waits at the hover, not parked high for its whole length
        j = _least(peak, norm, ok, np.array([q[0] == 'rest' for q in shapes]))
        if j is not None: return shapes[j]
        self.issue(cu.t, 'no room for a rise before the hold', avail=T)
        return self._low(t0, v0, af, h, r1)

    @staticmethod
    def _low(t0, v0, af, h, r1):
        """The low catch, where no rise fits (an issue): the float to its apex, caught down to H_LOW_UNDER of it
        (at most H_LOW_PREP x h) over clamp(CATCH_K sqrt(2 dip / a_f)) s, a wind-up from there arriving by r1."""
        tf = v0/af; h1 = v0*v0/(2*af); hl = min(H_LOW_UNDER*h1, H_LOW_PREP*h)
        tl = t0+tf+min(max(CATCH_K*math.sqrt(2*(h1-hl)/af), CATCH_MIN), CATCH_MAX)
        return ('low', hl, tl, tl, max(r1, tl+1e-6))

    @staticmethod
    def _w_room(h, hl):
        """A wind-up from rest at h_low to the prep h, where the gap has room: at least W_RISE, at W_RATE."""
        return max(W_RISE, (h-hl)/W_RATE)

    def _coordinate(self, pv, cu, dx, go, v0, af, t_hs, h, yz0, yz1):
        """A hold note's rise and freewheel, coordinated: of the shapes the
        rulers allow, the goal's choice (Rest or flow, A11): whichever moves
        the head slower at its peak, its speed in the world (the vector sum of
        the carriage's x and the head's arc, sampled every COORD_DT) from the
        contact + RISE_SKIP to the hold; peaks within PEAK_TIE tie and a tie
        rests, under a moving carriage too; then the least COORD_P-norm over
        the gap (_least, as _rise_alone). Measured: of the 11 hold notes whose
        flow or coast had tied a rest on the head's own arc speed, 4 tie in
        the world too and rest, on the apex catch (bars_arm0 53.214 and
        64.643 'S2 freewheel', 57.143 'S1 freewheel', at the float's launch,
        1.415-1.636 m/s; bars_arm1 59.643 'S2 freewheel', a forced late go,
        at the freewheel's own 2.969; their 8-norm 0.1-27 % higher); 7 coasts
        under the loop beat every rest in the world, the rest's wind-up
        riding the freewheel (bars_arm1 55.357, 58.214, 66.786 by 0.04-0.49
        m/s; bells_arm0's four by 0.011, just past PEAK_TIE), and stay. Of
        the shapes ruler 8 allows: none where the head waits ('8 low rest':
        still, LOW_REV below the park, while the carriage moves, over
        LOW_WAIT). A wind-up from rest leaving WITH the carriage waits so
        (57.143: 79 ms, the head's 3-4-5 under STILL_V while the carriage's
        passes X_MOVING), so 57.143's carriage leaves 97 ms into its 1.36 s
        wind-up, the head at 0.038 m/s and past STILL_V before the carriage
        passes X_MOVING. The float is fixed;
        the carriage is one 3-4-5 (or glide) leaving at or after go and given at
        least its least unhurried time (or the whole window when even that is
        short). The head either FLOWS (_flow: the float hands over on FLOW_N
        times to a quintic wind-up) or RESTS (the apex catch, still >= REST_MIN, a
        3-4-5 wind-up from rest >= W_MIN; the rest at most H_LOW_PREP x h).
        The carriage never moves while the head waits below the park
        (LOW_WAIT), and leaves under a moving head only where it moves at >=
        COORD_MOVING, or with a wind-up from rest, both from rest (ruler 22
        times a channel's start only from rest). The shapes:
          * together: both arrive at the hold, in position within ARRIVE_SKEW
            (rule 7). Flowing (a one-piece wind-up, or a coasting rise whose
            stop is fitted to the carriage's arrival, _coast_fit): the carriage
            leaves anywhere the head rises, during the float ('freewheel under
            the loop') or after the handover ('S1 freewheel'). Resting: the
            carriage leaves as the wind-up from rest does (both from rest, in
            position within ARRIVE_SKEW) or after it ('S1 freewheel'), where
            the head does not wait (LOW_WAIT).
          * park first ('S2 freewheel'): the head's rise ends at r1 and parks;
            the carriage leaves at max(go, r1) under the parked head.
        A contact pair at different y or z (the carriage would move the head's
        y/z too, untimed here) raises. Returns (ta, shape for _build_rise,
        style, glide share)."""
        t0 = pv.t; sig = float(self.arm.sigma); tf = v0/af
        need = _freewheel_least(dx); Tc_min = min(need, t_hs-go); hurried = motion_timing.hurried('mallet', dx, t_hs-go)
        ts = np.arange(t0, t_hs, COORD_DT); rel = ts-t0
        ry, rz = _level(cu, dx, yz0, yz1, '_coordinate')
        Zh = math.sqrt(1+float(arc_Z(h, self.rho, self.k, 1))**2)

        def ds(u):
            u = np.clip(u, 0.0, 1.0); return 30*u*u*(1-u)**2

        live = rel >= RISE_SKIP

        def norm(ta, gl, H, V):
            """(COORD_P-norm, peak from the contact + RISE_SKIP) of the tool's world speed for carriage [ta, t_hs]
            gliding `gl` of it, head (H, V) rows: one vector, the carriage's x and the head's arc together; and
            whether the head waits (ruler 8 '8 low rest': still, LOW_REV below the park, under a moving carriage,
            over LOW_WAIT)."""
            ta, gl = np.asarray(ta, float)[:, None], np.asarray(gl, float)[:, None]
            vx = _glide_v(ts-ta, t_hs-ta, dx, gl)
            vy = vx*ry+V; vz = vx*rz+sig*arc_Z(H, self.rho, self.k, 1)*V
            sp = np.sqrt(vx*vx+vy*vy+vz*vz)
            waits = _run(live & (np.abs(V) < STILL_V) & (H < h-LOW_REV) & (np.abs(vx) > X_MOVING))*COORD_DT > LOW_WAIT
            return np.mean(sp**COORD_P, axis=-1)**(1/COORD_P), sp[:, live].max(-1), waits

        def glides(A):
            """Per GLIDE share, the share for each carriage start in A (nan where its accelerating half would pass
            FREE_G; the plain 3-4-5, share 0, is always allowed: Tc_min holds it). A hurried travel (even go -> hold
            is short of its least unhurried time) does not glide."""
            for gl in (GLIDE if not hurried else (0.0,)):
                yield np.where((gl == 0) | (_glide(dx, t_hs-A, gl)[4] <= motion_timing.FREE_G*G+1e-9), gl, np.nan)

        def lead(A, gl):
            """The carriage's in-position lead at its end (= its start's, by symmetry)."""
            Th, _, _, d, _ = _glide(abs(dx), t_hs-A, gl)
            return _inpos(2*d, 2*Th)

        cand = []          # (norm, world peak, ta, shape, style, glide)

        def add(A, H, V, ok, shape, style, sync=None):
            A, ok = A[ok], np.flatnonzero(ok)
            if not A.size: return
            for gl in glides(A):
                good = np.isfinite(gl)
                if sync is not None: good &= sync(A, gl, ok)
                if not good.any(): continue
                v, pk, wt = norm(A[good], gl[good], H[ok[good]], V[ok[good]])
                for x, p, a, k, g in zip(v[~wt], pk[~wt], A[good][~wt], ok[good][~wt], gl[good][~wt]):
                    cand.append((float(x), float(p), float(a), shape(k), style(a, k), float(g)))

        ta_hi = t_hs-Tc_min; tw = np.linspace(FLOAT_MIN, tf, FLOW_N+1)[:-1]
        TA = np.linspace(go, max(ta_hi, go), COORD_N)
        # -- flowing, together: the wind-up ends at the hold with the carriage
        if ta_hi >= go-1e-9:
            H, V, okf, (c3, c4, c5, hw, vw) = _flow(rel, v0, af, tw, t_hs-t0, h)
            R = t_hs-t0-tw; jend = 6*c3+24*c4*R+60*c5*R*R
            sh = np.cbrt(6*ARRIVE_POS/(np.maximum(jend, 1e-30)*Zh))       # the head's in-position lead
            A, J = (m.ravel() for m in np.meshgrid(TA, np.arange(tw.size), indexing='ij'))
            u = A-t0-tw[J]                                                 # the head's speed as the carriage leaves
            vh = np.where(u < 0, v0-af*(A-t0), vw[J]+u*(-af+u*(3*c3[J]+u*(4*c4[J]+u*5*c5[J]))))
            ok = okf[J] & (vh >= COORD_MOVING)
            add(A, H[J], V[J], ok, lambda k, J=J: ('flow', t0+tw[J[k]], t_hs),
                lambda a, k, J=J: 'freewheel under the loop' if a < t0+tw[J[k]]-1e-9 else 'S1 freewheel',
                lambda A_, gl, k, J=J: np.abs(lead(A_, gl)-sh[J[k]]) <= ARRIVE_SKEW)
        # -- coasting, together: the float eases to a coast and a 3-4-5 half stops the head with the carriage,
        # the stop's length solved so the two come in position at once (a one-piece wind-up sags below FLOW_K
        # over a long freewheel, or comes in too gently for ruler 22: its lead >> the carriage's 2-6 ms)
        if ta_hi >= go-1e-9:
            A, J = (m.ravel() for m in np.meshgrid(TA, np.arange(tw.size), indexing='ij'))
            for gl in glides(A):
                g = np.isfinite(gl)
                if not g.any(): continue
                Ag, Jg, gg = A[g], J[g], gl[g]
                te, tc, Ts, ok = _coast_fit(v0, af, tw[Jg], t_hs-t0, h, 6*ARRIVE_POS/lead(Ag, gg)**3, Zh)
                H, V = _coast(rel, v0, af, tw[Jg], te, tc, Ts, h)
                i = np.clip(np.round((Ag-t0)/COORD_DT).astype(int), 0, rel.size-1)
                ok &= V[np.arange(Ag.size), i] >= COORD_MOVING     # the head moving as the carriage leaves
                if not ok.any(): continue
                v, pk, wt = norm(Ag[ok], gg[ok], H[ok], V[ok])
                for x, p, a, k, q in zip(v[~wt], pk[~wt], Ag[ok][~wt], np.flatnonzero(ok)[~wt], gg[ok][~wt]):
                    w = t0+tw[Jg[k]]
                    cand.append((float(x), float(p), float(a), ('coast', w, w+te[k], t_hs-Ts[k], t_hs),
                                 'freewheel under the loop' if a < w-1e-9 else 'S1 freewheel', float(q)))
        # -- flowing, park first: the rise ends at r1, the carriage leaves under the parked head
        if ta_hi >= t0+tf-1e-9:
            R1 = np.linspace(t0+tf, ta_hi, FLOW_N)
            TW, RR = (m.ravel() for m in np.meshgrid(tw, R1-t0, indexing='ij'))
            H, V, okf, _ = _flow(rel, v0, af, TW, RR, h)
            A = np.maximum(go, t0+RR); okf &= t_hs-A >= Tc_min-1e-9
            add(A, H, V, okf, lambda k: ('flow', t0+TW[k], t0+RR[k]), lambda a, k: 'S2 freewheel')
        # -- resting: the apex catch, still >= REST_MIN, a wind-up from rest
        tr, hr = _top_catch(v0, af)[3:]; r0_lo = t0+tr+REST_MIN
        if hr <= H_LOW_PREP*h+1e-12:
            Dh = (h-hr)*Zh                                                       # the head's 3D approach to the park
            Dh0 = (h-hr)*math.sqrt(1+float(arc_Z(hr, self.rho, self.k, 1))**2)  # ...and its departure from rest
            r0_hi = t_hs-W_MIN
            if r0_hi >= r0_lo-1e-9 and ta_hi >= max(go, r0_lo)-1e-9:
                R0 = np.linspace(r0_lo, r0_hi, COORD_N)
                A, R = (m.ravel() for m in np.meshgrid(TA, R0, indexing='ij'))
                # the carriage leaves after the wind-up from rest has, under a moving head, or with it
                uu = np.clip((A-R)/(t_hs-R), 0.0, 1.0); vh = (h-hr)/(t_hs-R)*ds(uu)
                both = np.concatenate([TA[(TA >= r0_lo-1e-9) & (TA <= r0_hi+1e-9)], R0[(R0 >= go-1e-9) & (R0 <= ta_hi+1e-9)]])
                A = np.concatenate([A, both]); R = np.concatenate([R, both])
                ok = np.concatenate([(A[:uu.size] > R[:uu.size]+1e-9) & (vh >= COORD_MOVING), np.ones(both.size, bool)])
                H, V = _rest(rel, v0, af, R-t0, t_hs-t0, h)

                def sync(A_, gl, k, R=R):
                    tl = lead(A_, gl); W = t_hs-R[k]
                    s = np.abs(tl-_inpos(Dh, W)) <= ARRIVE_SKEW
                    return s & ((A_ > R[k]+1e-9) | (np.abs(tl-_inpos(Dh0, W)) <= ARRIVE_SKEW))
                add(A, H, V, ok, lambda k, R=R: ('rest', R[k], t_hs), lambda a, k: 'S1 freewheel', sync)
            # park first
            if ta_hi >= r0_lo+W_MIN-1e-9:
                R1 = np.linspace(r0_lo+W_MIN, ta_hi, COORD_N)
                W = np.minimum(self._w_room(h, hr), R1-r0_lo); R0 = R1-W; A = np.maximum(go, R1)
                H, V = _rest(rel, v0, af, R0-t0, R1-t0, h)
                add(A, H, V, t_hs-A >= Tc_min-1e-9, lambda k, R0=R0, R1=R1: ('rest', R0[k], R1[k]), lambda a, k: 'S2 freewheel')
        if not cand:
            # no shape fits (a hurried window): the carriage takes go -> hold, the head rises alone to the hold
            self.issue(cu.t, 'no coordinated hold freewheel', go=go, hold_start=t_hs)
            return go, self._rise_alone(pv, cu, v0, af, t_hs, t_hs, h), 'freewheel under the loop', 0.0
        # the goal's choice (Rest or flow, A11): the least peak of the world speed, a rest on a tie (PEAK_TIE),
        # then the least COORD_P-norm, exactly as _rise_alone chooses where no carriage moves
        nm, pk, ta, shape, style, gl = zip(*cand)
        j = _least(np.array(pk), np.array(nm), np.ones(len(cand), bool), np.array([s[0] == 'rest' for s in shape]))
        return ta[j], shape[j], style[j], gl[j]

    def _under(self, pv, cu, dx, go, t_hs, h, yz0, yz1):
        """The toll under the loop (goal Tolls 5, A11): a stepped traverse that
        fits only from go fills its window from there (stepped_period: the
        steps leave at ta = t_hs - n per), and the head climbs while it steps.
        The float hands over, still rising, C2, to a COASTING rise (_coast_fit:
        an ease from -a_f to a = 0, a constant speed v_m, a stop) whose stop
        puts the head at the prep in position within ARRIVE_SKEW of the
        carriage's LAST landing, t_arr = t_hs - (1 - STEP_MOVE) per (rule 7,
        ruler 22: the stop's end jerk is the last step's, 6 ARRIVE_POS/lead^3),
        then the park to t_hs. The head never waits under the steps (ruler 8
        '8 low rest': still, LOW_REV below its park, while the carriage
        moves): the coast climbs at v_m >= UNDER_K x STILL_V, and only the
        stop's last 7.5-10.2 ms, within 0.23 mm of the prep, pass under
        STILL_V.
        That decides the float: a 4 s toll at the loop's e 0.45 under 1 g
        leaves the bars' coast 0.029-0.048 m/s, so the float takes
        dahl_float's grid (e and a_f one step inside ruler 8's bands, t_w on
        FLOW_N points from FLOAT_MIN to its apex) and the goal's choice: the
        least peak of the tool's world speed (the steps' x' and the head's arc
        together) from the contact + RISE_SKIP, PEAK_TIE equal, then the least
        COORD_P-norm. The least rebound is the least peak and the highest
        coast: measured e 0.31 under 1.48 g on every toll, the coast
        0.059-0.068 m/s on the bars (the rise 3.9-4.3 s), 0.19 on the bells
        (2.4 s).
        Rows of e are searched upward until the float's launch alone (its
        speed at the first live sample, a floor under every peak of the row)
        passes the best peak + PEAK_TIE. No coast at UNDER_K: the fastest that
        fits and an issue; none at all: the low catch (_low) and an issue.
        Returns (ta, shape, e, a_f)."""
        t0 = pv.t; vp = pv.v_in; n = motion_timing.teeth(dx); M = motion_timing.STEP_MOVE
        _level(cu, dx, yz0, yz1, '_under')
        per = motion_timing.stepped_period(dx, t_hs-go); ta = t_hs-n*per; t_arr = t_hs-(1-M)*per
        d = abs(dx)/n; Tm = M*per
        jc = 6*ARRIVE_POS/float(_inpos(d, Tm))**3        # the last step's in-position lead, the stop's to match
        Zh = math.sqrt(1+float(arc_Z(h, self.rho, self.k, 1))**2)
        ts = np.arange(t0, t_hs, COORD_DT); rel = ts-t0; live = rel >= RISE_SKIP
        k = np.floor((ts-ta)/per); u = np.clip((ts-ta-k*per)/Tm, 0.0, 1.0)
        vx = np.where((k >= 0) & (k < n), d/Tm*30*u*u*(1-u)**2, 0.0)[None, :]     # the steps' |x'| (3-4-5s)
        E = np.arange(E_LO+DAHL_E_STEP, E_HI-DAHL_E_STEP+1e-9, DAHL_E_STEP)
        A = np.arange(AF_LO_G+DAHL_AF_STEP, AF_HI_G-DAHL_AF_STEP+1e-9, DAHL_AF_STEP)*G
        U = np.arange(FLOW_N)/FLOW_N; t_lb = rel[live][0] if rel[live][0] < FLOAT_MIN else 0.0
        best = np.inf; rows = []
        for e in E:
            v0 = e*vp
            if v0-A.max()*t_lb > best+PEAK_TIE: break
            af, uu = (m.ravel() for m in np.meshgrid(A, U, indexing='ij')); tf = v0/af
            tw = FLOAT_MIN+uu*(tf-FLOAT_MIN)
            te, tc, Ts, ok = _coast_fit(v0, af, tw, t_arr-t0, h, jc, Zh)
            ok &= tf > FLOAT_MIN; vm = v0-af*tw-.5*af*te
            pk = np.full(af.size, np.inf); nm = np.full(af.size, np.inf)
            for c in np.array_split(np.flatnonzero(ok), max(1, int(np.ceil(ok.sum()/256)))):
                if not c.size: continue
                H, V = _coast(rel, v0, af[c], tw[c], te[c], tc[c], Ts[c], h)
                sp = np.sqrt(vx*vx+V*V*(1+arc_Z(H, self.rho, self.k, 1)**2))
                pk[c] = sp[:, live].max(1); nm[c] = np.mean(sp**COORD_P, 1)**(1/COORD_P)
            fast = ok & (vm >= UNDER_K*STILL_V)
            if fast.any(): best = min(best, float(pk[fast].min()))
            rows.append((np.full(af.size, e), af, tw, te, tc, Ts, vm, pk, nm, ok, fast))
        e, af, tw, te, tc, Ts, vm, pk, nm, ok, fast = (np.concatenate(c) for c in zip(*rows))
        j = _least(pk, nm, fast)
        if j is None:
            j = int(np.argmax(np.where(ok, vm, -np.inf))) if ok.any() else None
            self.issue(cu.t, 'coast under the loop too slow' if j is not None else 'no coast under the loop',
                       v_m=float(vm[j]) if j is not None else None, need=UNDER_K*STILL_V)
        if j is None:
            return ta, self._low(t0, E_LOOP*vp, AF_LOOP_G*G, h, t_arr), E_LOOP, AF_LOOP_G*G
        w = t0+tw[j]
        return ta, ('coast', w, w+te[j], t_arr-Ts[j], t_arr), float(e[j]), float(af[j])

    def _contact_travel(self, pv, cu, go, t1, moving, yz0, yz1):
        """A travel with no hold: contact (or go) to contact, stepped or one
        freewheel from go that glides as _contact_glide picks."""
        if not moving:
            cu.regime = 'still'; self.hold_x(t1, cu.x, yz1, event=cu.event); return
        dx = cu.x-pv.x; regime = motion_timing.travel_regime(dx, t1-go); cu.regime = regime; glide = 0.0
        if regime == 'step':
            n = motion_timing.teeth(dx); per = motion_timing.stepped_period(dx, t1-go); ta = t1-n*per
        else:
            ta = go; glide = self._contact_glide(dx, ta, t1, yz0, yz1)
        tid = self.travel(pv.x, yz0, cu.x, yz1, ta, t1, regime, cu.event, glide=glide, window=(go, t1))
        cu.travel = tid; cu.travel_window = (ta, t1); cu.hurried = self.travels[tid]['hurried']

    def _contact_glide(self, dx, ta, tb, yz0, yz1):
        """A contact travel's freewheel law: of the GLIDE shares whose halves
        hold FREE_G (0, the plain 3-4-5, always), the one whose tool speed has
        the least COORD_P-norm over the whole travel window [ta, tb], sampled
        every COORD_DT. The tool speed is the vector sum of the carriage (x and
        its y_c/z_c blend) and the head on its arc, as already planned to the
        contact (the float or the Dahl loop, the downstroke): the honest
        speed, strike included, not ruler 1's gated mask. x' = x'' = 0 at both
        contacts whatever the share (the halves start and end at rest)."""
        T = tb-ta; ts = np.arange(ta, tb, COORD_DT); hh = np.zeros_like(ts); h1 = np.zeros_like(ts)
        for s in self.B.head:
            if s.t1 > ta and s.t0 < tb:
                m = (ts >= s.t0) & (ts < s.t1); hh[m] = s.ev(ts[m]); h1[m] = s.ev(ts[m], 1)
        ry, rz = (yz1[0]-yz0[0])/dx, (yz1[1]-yz0[1])/dx; hz = float(self.arm.sigma)*arc_Z(hh, self.rho, self.k, 1)*h1
        best = None
        for gl in GLIDE:
            if gl > 0 and _glide(dx, T, gl)[4] > motion_timing.FREE_G*G+1e-9: continue
            vx = _glide_v(ts-ta, T, dx, gl)
            v = float(np.mean((vx*vx+(vx*ry+h1)**2+(vx*rz+hz)**2)**(COORD_P/2))**(1/COORD_P))
            if best is None or v < best[0]: best = (v, gl)
        return best[1]


def _seg_peak(fn, t0, t1):
    """max |fn| over [t0, t1] by dense sampling, refined about the best sample."""
    ts = np.linspace(t0, t1, JERK_SAMPLES+1); v = np.abs(fn(ts)); k = int(np.argmax(v)); best = float(v[k])
    lo, hi = ts[max(k-1, 0)], ts[min(k+1, len(ts)-1)]
    for _ in range(40):
        m1 = lo+(hi-lo)/3; m2 = hi-(hi-lo)/3
        if abs(float(fn(np.array([m1]))[0])) < abs(float(fn(np.array([m2]))[0])): lo = m1
        else: hi = m2
    return max(best, abs(float(fn(np.array([.5*(lo+hi)]))[0])))


def declare_jerk(st):
    """Fill extra['jerk'] on a plan made with jerk=False (idempotent): the dense
    peak search is most of a plan's cost, and only the declared contract reads it."""
    if not getattr(st, 'jerk_declared', False): _declare_jerk(st)
    return st


def law_coef(law, extra, T):
    """A head segment's h(tau) rebuilt from its LAW and its declared boundary
    data alone (extra p0..a1 for a 'quintic hermite', p0/v0/a for a
    'ballistic', p0/p1 for a '3-4-5', p0 for a 'hold'), never from the
    segment's coefficients: the closed form its declared jerk is taken on."""
    if law == 'quintic hermite':
        return law_hermite(*(float(extra[k]) for k in ('p0', 'v0', 'a0', 'p1', 'v1', 'a1')), T)
    if law == 'ballistic': return law_ballistic(float(extra['p0']), float(extra['v0']), float(extra['a']))
    if law == '3-4-5': return law_345(float(extra['p0']), float(extra['p1']), T)
    if law == 'hold': return law_hold(float(extra.get('p0', 0.0)))
    raise ValueError(law)


def head_jerk(c, T, rho, k):
    """Peak |p'''| over [0, T] of the head's y-z path (h, sigma Z(h)) for
    h(tau) = coefficients c (lowest power first)."""
    def J(tau):
        h, h1, h2, h3 = (_horner(_dcoef(c, d), tau) for d in (0, 1, 2, 3))
        jz = arc_Z(h, rho, k, 3)*h1**3+3*arc_Z(h, rho, k, 2)*h1*h2+arc_Z(h, rho, k, 1)*h3
        return np.hypot(h3, jz)
    return _seg_peak(J, 0.0, T)


def _declare_jerk(st):
    """extra['jerk']: each segment's peak |p'''| on its channel's own 3D path,
    from the law's closed form on the segment's declared boundary data (the
    carriage: 60|D|/T^3 for a '3-4-5', a glide's pieces' peak |x'''| from
    law_coef, times the y_c/z_c blend; the head: the
    y-z path through the arc of law_coef(law, extra, T))."""
    st.jerk_declared = True
    rho, k = st.rho, st.k
    for s in st.carriage.segs:
        if s.law == 'hold' or not np.isfinite(s.T):
            s.extra['jerk'] = 0.0; continue
        D = float(s.ev(s.t1)-s.c[0]); scale = 1.0
        if s.cy is not None:
            cy3 = _dcoef(s.cy, 3); cz3 = _dcoef(s.cz, 3); cx3 = _dcoef(s.c, 3)
            if np.any(cx3 != 0):
                ry = np.max(np.abs(cy3))/np.max(np.abs(cx3)); rz = np.max(np.abs(cz3))/np.max(np.abs(cx3))
                scale = math.sqrt(1+ry*ry+rz*rz)
        if s.law == '3-4-5':
            s.extra['jerk'] = 60*abs(D)/s.T**3*scale
        elif s.law in ('quintic hermite', 'ballistic'):
            # a glide's halves and cruise: the peak |x'''| of law_coef on the declared boundary data
            c3 = _dcoef(law_coef(s.law, s.extra, s.T), 3)
            s.extra['jerk'] = _seg_peak(lambda tau, c3=c3: _horner(c3, tau), 0.0, s.T)*scale if np.any(c3 != 0) else 0.0
        else:
            raise ValueError(f'carriage {s.tag}: no closed-form jerk for law {s.law!r}')
    for s in st.head.segs:
        if s.tag == 'home':
            s.extra['jerk'] = None          # the joint legs' tip path is FK of the cfg: the Rig declares it
            continue
        if s.law == 'hold' or not np.isfinite(s.T):
            s.extra['jerk'] = 0.0; continue
        s.extra['jerk'] = head_jerk(law_coef(s.law, s.extra, s.T), s.T, rho, k)


def plan(arm, jerk=True):
    """Plan one mallet arm's stroke from plain data (ArmIn) -> ArmStroke.
    jerk=False leaves extra['jerk'] undeclared until declare_jerk(st)."""
    if arm.kind not in ARC: raise ValueError(f'no stroke for kind {arm.kind!r}')
    assert HOLD+T_DOWN_MAX <= motion_timing.STILL_S+1e-12, 'the planner leaves STILL_S for the hold and the longest downstroke'
    return _Planner(arm, jerk).run()

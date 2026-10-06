"""The measuring core of tools/test_players.py (docs/goals/the-players.md,
"Acceptance"): one Subject per asset, holding the rig, the score, the layout
and the declared structure, and the helpers every ruler module shares.

A ruler module (tools/players/r_*.py) exports RULERS = {n: fn}, where
fn(subject) returns a list of Result. A Result's `passed` is True or False
against the goal's target, or None when the ruler has nothing to measure on
that scope yet (the part or the declaration does not exist), or INFO for a
number the goal reports without judging it (or judges only at a later
milestone). --gate fails on n/a in a gated scope and ignores INFO.
"""
import functools, json, math, sys
from dataclasses import dataclass, field
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path: sys.path.insert(0, str(ROOT))
from formlab import rig as R
from formlab.rig import Rig
from formlab import segments as SEG

FPS = 30            # the film's frame rate: frames are t_k = k/FPS
HZ = 120            # the rulers' sampling rate for "every sample" checks
G = 9.81
H = 1e-5            # one-sided derivative step on the rig (s)
INFO = 'info'       # Result.passed for a reported, unjudged number
STILL_V = .02       # m/s: D7 (PLAYERS A26) a declared head hold (an announce apex, a pick's poise) is still when the tool
                    # point's |v| stays at or under this through it: 0.67 mm a frame, a pause the eye reads as one. A
                    # declared hold over a carriage still crossing under it (round 2: 561-1324 mm/s) reads as motion
STILL_DT = 1e-3     # s: D7 samples the closed form this often through a hold (1 kHz, ruler 15's rate)

ASSETS = {
    'chamber': dict(manifest=ROOT/'harness/assets/clockwork.json', score=ROOT/'render/chamber/score.json',
                    camera=ROOT/'render/film/camera.json'),
    'expanded': dict(manifest=ROOT/'harness/assets/clockwork_expanded.json', score=ROOT/'render/clockwork/score.json',
                     camera=None),
}

@dataclass
class Result:
    n: int                 # ruler number in the goal's Acceptance table
    name: str              # the measure, short ("strobe", "e", "corners 6b"...)
    scope: str             # an arm id, an arm kind, or 'all'
    value: dict            # the measured numbers (JSON-able)
    passed: object = None  # True / False against the target; None = n/a; INFO = reported only
    note: str = ''

@dataclass
class Contact:
    """One scored contact as the rulers see it. `t` is the sound: a blow's
    impact, a pluck's onset (today's poke; from M7 the slip-off), a sweep's
    first string. `point` is the contact point c, `normal` the outward normal
    n the tool approaches along (h(t) = (p - c)·n is the height above it)."""
    aid: str
    i: int                 # index on the arm (0..)
    event: dict
    sched: dict            # Rig.sched entry
    kind: str              # 'blow' | 'pluck' | 'sweep' | 'hammer'
    t: float
    t_end: float           # last string's time (sweeps), = t otherwise
    point: np.ndarray
    normal: np.ndarray
    amp: float
    a: object              # amp normalised per voice in [0, 1], or None if the voice has one amp
    ioi: float             # t - previous contact's t on this arm (inf for the first)
    gap: float             # t - previous contact's t_end (inf for the first)
    ioi_next: float        # next contact's t - t (inf for the last)

def deriv(f, t, side=+1, order=1, h=H):
    """One-sided 5-point finite difference of a vector function f at t:
    side=+1 looks forward (the right limit), side=-1 backward (the left)."""
    p = [np.asarray(f(t+side*k*h), float) for k in range(5)]
    if order == 1:
        return side*(-25*p[0]+48*p[1]-36*p[2]+16*p[3]-3*p[4])/(12*h)
    if order == 2:
        return (35*p[0]-104*p[1]+114*p[2]-56*p[3]+11*p[4])/(12*h*h)
    raise ValueError(order)

def frames(total):
    return np.arange(0, int(math.floor(total*FPS))+1)/FPS

def spearman(x, y):
    x = np.asarray(x, float); y = np.asarray(y, float)
    if len(x) < 3 or np.ptp(x) == 0 or np.ptp(y) == 0: return float('nan')
    rx = _rank(x); ry = _rank(y)
    return float(np.corrcoef(rx, ry)[0, 1])

def _rank(v):
    order = np.argsort(v, kind='mergesort'); ranks = np.empty(len(v)); ranks[order] = np.arange(len(v))
    for val in np.unique(v):                      # average ties
        m = v == val
        if m.sum() > 1: ranks[m] = ranks[m].mean()
    return ranks

class Subject:
    """One asset, measured."""
    def __init__(self, asset):
        cfg = ASSETS[asset]
        self.asset = asset
        self.manifest_path = cfg['manifest']; self.score_path = cfg['score']; self.camera_path = cfg['camera']
        self.layout = json.loads(self.manifest_path.read_text())
        self.score = json.loads(self.score_path.read_text())
        self.rig = Rig(self.score, self.layout)
        self.total = float(self.score['total_s'])
        self.arms = {aid: self.rig.acts[aid]['kind'] for aid in self.rig.plans if self.rig.plans[aid]}
        self.t_frames = frames(self.total)
        self.t_hz = np.arange(0, int(self.total*HZ)+1)/HZ
        self._amp_range = self._voice_amps()

    # ---- arms -------------------------------------------------------------
    def kind(self, aid): return self.arms[aid]
    def arms_of(self, *kinds): return [a for a, k in self.arms.items() if k in kinds]
    def cfg(self, aid): return self.layout['arms'][aid]
    def mech(self, aid): return self.rig.mech_of[aid]

    # ---- motion -----------------------------------------------------------
    def tip(self, aid, t): return self.rig.tip_at(aid, t)          # what renders (with rings)
    def path(self, aid, t): return self.rig.path_at(aid, t)        # the scored path alone
    def contact_point(self, aid, t):
        """The point that touches the instrument: the felt for a hinged hammer, the tip otherwise."""
        return self.rig.pose(aid, t)['felt']

    @functools.lru_cache(maxsize=None)
    def poses(self, aid, grid='frames'):
        """Rig.poses on a named grid: 'frames' (30 fps) or 'hz' (120 Hz)."""
        times = self.t_frames if grid == 'frames' else self.t_hz
        return self.rig.poses(aid, times)

    def fn(self, aid, which='path'):
        """t -> point for one arm: 'path' (scored, no rings), 'tip' (as rendered), 'felt' (the contact face)."""
        return dict(path=lambda u: self.path(aid, u), tip=lambda u: self.tip(aid, u),
                    felt=lambda u: self.contact_point(aid, u))[which]

    def vel(self, aid, t, side=+1, which='path'): return deriv(self.fn(aid, which), t, side, 1)
    def acc(self, aid, t, side=+1, which='path'): return deriv(self.fn(aid, which), t, side, 2)

    # ---- declared structure ----------------------------------------------
    @functools.lru_cache(maxsize=None)
    def declared(self, aid): return SEG.declared(self.rig, aid)

    def stroke(self, aid):
        """An arm's planned stroke when its rig declares one: a mallet's
        (formlab/stroke.py ArmStroke: the head and carriage channels, per-note
        records, travels; PLAYERS M1) and, once its declaration is native, a
        pick's or the rake's (formlab/servo.py ServoStroke, PLAYERS M2: the
        same surface, .head/.carriage/.yc/.zc, p/v/a/j, notes); None for any
        other arm or a rig that plans none."""
        if not hasattr(self.rig, 'stroke'): return None
        if self.kind(aid) == 'mallet': return self.rig.stroke(aid)
        return self.rig.stroke(aid) if self.declared(aid).native else None

    def impulse_knots(self, aid):
        return [k for k in self.declared(aid).knots if k.kind in SEG.IMPULSES]

    def click_intervals(self, aid):
        """[(t, t_end)] of the declared clicks that MOVE the path: a ratchet
        click's or a stepped/homing tooth's step (they carry `t_end`). A
        freewheel tooth's click (PLAYERS M1, DESIGN 7.9) carries no `t_end`:
        it is the pawl's sound as the carriage glides past, not a path
        impulse, so it has no interval."""
        return [(k.t, k.extra['t_end']) for k in self.declared(aid).knots if k.kind == 'click' and 't_end' in k.extra]

    def impulse_frame(self, aid, k):
        """Is frame k (the interval (t_{k-1}, t_k]) an impulse frame for this arm?"""
        t0, t1 = (k-1)/FPS, k/FPS
        if any(t0 < kn.t <= t1 for kn in self.impulse_knots(aid)): return True
        return any(a < t1 and b > t0 for a, b in self.click_intervals(aid))

    # ---- contacts ---------------------------------------------------------
    def _voice_amps(self):
        rng = {}
        for e in self.score['events']:
            v = e.get('voice', e.get('mech')); a = float(e.get('amp', 1.0))
            lo, hi = rng.get(v, (a, a)); rng[v] = (min(lo, a), max(hi, a))
        return rng

    def a_norm(self, e):
        lo, hi = self._amp_range[e.get('voice', e.get('mech'))]
        return None if hi-lo < 1e-9 else (float(e.get('amp', 1.0))-lo)/(hi-lo)

    @functools.lru_cache(maxsize=None)
    def contacts(self, aid):
        rig = self.rig; out = []
        struck = self.layout['strings'][rig.acts[aid]['home']]['struck']
        kind_arm = rig.acts[aid]['kind']
        lift = rig.clearance(aid); n = lift/np.linalg.norm(lift)
        sched = rig.sched[aid]
        for i, s in enumerate(sched):
            e = s['event']; ids = e['strings']
            # a sweep: strings at distinct times (motion_timing.string_times: a rake roll's onsets, else
            # t + k spread, so spread > 0 exactly as before)
            ts = R.motion_timing.string_times(e); sweep = len(ids) > 1 and max(ts) > min(ts)
            kind = 'hammer' if kind_arm == 'hammer' else 'blow' if struck else 'sweep' if sweep else 'pluck'
            out.append(Contact(aid=aid, i=i, event=e, sched=s, kind=kind, t=float(s['hit']), t_end=float(s['end']),
                               point=np.asarray(s['first'], float), normal=n, amp=float(e.get('amp', 1.0)),
                               a=self.a_norm(e), ioi=math.inf, gap=math.inf, ioi_next=math.inf))
        for i in range(1, len(out)):
            out[i].ioi = out[i].t-out[i-1].t; out[i].gap = out[i].t-out[i-1].t_end
            out[i-1].ioi_next = out[i].ioi
        return tuple(out)

    def all_contacts(self, *kinds):
        return [c for aid in self.arms for c in self.contacts(aid) if not kinds or c.kind in kinds]

    # ---- camera -----------------------------------------------------------
    @functools.lru_cache(maxsize=None)
    def camera(self):
        """The film camera per frame (render/film/camera.json, exported from
        harness/film_director.gd by harness/dev/export_camera.gd), or None."""
        if self.camera_path is None or not Path(self.camera_path).exists(): return None
        return json.loads(Path(self.camera_path).read_text())

def still(S, aid, t0, t1):
    """D7 (PLAYERS A26): the tool point's |v| through a declared hold [t0, t1]
    on the closed form (the arm's stroke .v, every STILL_DT, one-sided inward
    at both ends) -> dict(v_max, t_v, still_ms: the time spent at |v| <=
    STILL_V, drift: |p(t1) - p(t0)|, ok: v_max <= STILL_V), or None when the
    arm plans no stroke or the hold is empty."""
    st = S.stroke(aid)
    if st is None or not t1 > t0: return None
    n = max(int(math.ceil((t1-t0)/STILL_DT-1e-9)), 1); ts = t0+(t1-t0)*np.arange(n+1)/n
    V = np.concatenate([np.asarray(st.v(ts[:-1], +1), float).reshape(-1, 3), np.asarray(st.v(ts[-1:], -1), float).reshape(-1, 3)])
    sp = np.linalg.norm(V, axis=1); k = int(np.argmax(sp)); lo = sp <= STILL_V
    P = np.asarray(st.p(np.array([t0, t1])), float).reshape(-1, 3)
    return dict(v_max=float(sp[k]), t_v=float(ts[k]), still_ms=float(np.diff(ts)[lo[:-1] & lo[1:]].sum()*1e3),
                drift=float(np.linalg.norm(P[1]-P[0])), ok=bool(sp[k] <= STILL_V))

def stat(x):
    """p50 / p95 / max of a sample, JSON-able (empty -> None)."""
    x = np.asarray(x, float)
    if x.size == 0: return None
    return dict(p50=float(np.percentile(x, 50)), p95=float(np.percentile(x, 95)), max=float(x.max()), n=int(x.size))

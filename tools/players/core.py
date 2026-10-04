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

    def impulse_knots(self, aid):
        return [k for k in self.declared(aid).knots if k.kind in SEG.IMPULSES]

    def click_intervals(self, aid):
        return [(k.t, k.extra['t_end']) for k in self.declared(aid).knots if k.kind == 'click']

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
            sweep = len(ids) > 1 and s['spread'] > 0
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

def stat(x):
    """p50 / p95 / max of a sample, JSON-able (empty -> None)."""
    x = np.asarray(x, float)
    if x.size == 0: return None
    return dict(p50=float(np.percentile(x, 50)), p95=float(np.percentile(x, 95)), max=float(x.max()), n=int(x.size))

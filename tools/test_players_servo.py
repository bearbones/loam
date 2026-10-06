"""The generalised rulers on a synthetic native servo (PLAYERS M2, track T2).

    python3 tools/test_players_servo.py

Until formlab/servo.py (the picks) and formlab/rake.py land, no servo arm
declares itself, so the rows M2 opens to servos (r_machine._native, the
servo branches of ruler 6c, '3 lead (IOI >= 0.25 s)') have nothing native to
measure on the built assets. This builds one by hand, to the lead's
ServoStroke contract: on the chamber's harp_arm1 (manifest and geometry as
built) a synthetic score of seven plucks, played by a stroke made of
formlab.stroke Seg/Channel pieces and declared the way Rig.declared declares
a mallet (native=True, every channel join a smooth knot, each contact an
impulse knot with its dv):

  - carriage: (x, y_c, z_c) on the servo S-curve ('scurve', r = SCURVE_RAMP,
    cut into its rising ramp, cruise and falling ramp: three segments a move,
    each its own polynomial; the contact's y/z blend in cy/cz on the same law);
  - head: p = carriage + h n + (0, hy, hz), n = clearance/|clearance|; a poised
    stroke (gap >= 1 s) rises hover -> apex over [t - 0.74, t - 0.20] with the
    carriage, holds (the poise) to t - 0.15, acts ('quintic hermite') into the
    contact at v_in, rebounds with e = 0.3 (contact knot dv = (1 + e) v_in n)
    and releases to the hover; a phrase stroke releases straight up to its
    apex and turns there without a hold (T_down = clamp(0.4 IOI, 0.08, 0.15));
  - home: in the first rest, x legs home -> lo -> hi -> home (S-curve, 'home'),
    then the elbow and the shoulder swept in joint space at home (Rig._fk on
    the IK frame of the home rest, stroke.joint_legs over rig.joint_spans), as
    the mallet's homing turns them;
  - every head hermite declares its jerk (the peak |h''' n + (0, hy''', 0)| of
    its own polynomials, as stroke.declare_jerk does), the carriage pieces do
    not (their bound is the ruler's S-curve closed form).

The rig is the real Rig on that score with the arm's stroke, path_at and
declared() swapped for the synthetic ones (tip_at and pose read path_at, as
they do for a servo). Each generalised row runs on it and must PASS, and on a
deliberately broken variant its row must FAIL:

  3 lead     a poised stroke with a 0.41 s lead (< 0.415 s at gap >= 1 s); the
             good plan's 0.18 s-IOI pluck fails only '3 preparation'
  6a / 6b    a corner: an action that leaves its poise at -0.5 m/s
  6c         a carriage built on r = 0.15 but declared 'scurve' (jerk 3.3x the
             closed form); a vector head whose hy moves undeclared; a declared
             jerk below its closed form
  22 sync    a head that arrives 15 ms before its carriage
  22 repeat  an apex that grows with the distance travelled
  22 home    a sweep that lands 1 mm off the home rest
The good plan is also run with no travel id on its carriage pieces (sync
groups contiguous pieces itself) and with a declared vector head (6c's vector
branch).
"""
import json, math, sys, time
from pathlib import Path
from types import SimpleNamespace
import numpy as np
ROOT = Path(__file__).resolve().parents[1]
for p in (str(ROOT), str(ROOT/'tools')):
    if p not in sys.path: sys.path.insert(0, p)
from formlab import rig as R
from formlab import stroke as ST
from formlab import segments as SEG
from formlab.rig import Rig
from players import core
from players import r_motion as RM
from players import r_machine as RMa

AID = 'harp_arm1'                              # the chamber's middle harp arm: its geometry and spans as built
LAYOUT = ROOT/'harness/assets/clockwork.json'  # the chamber manifest (core.ASSETS['chamber'])
SCORE = ROOT/'render/chamber/score.json'      # its instrument; the events are this file's
PICK = .18                                     # the harp's pick point (songs/chamber.py)
HOVER = .22                                    # |clearance| for plucked strings (Rig.clearance)
APEX = .32                                     # a poised stroke's apex (brief 2.2: >= 0.2933 for dh >= 0.25 h)
RISE, POISE, ACT = .74, .20, .15               # a poised stroke: rise from t - RISE, poise from t - POISE, act from t - ACT
V_IN, E = 2.5, .3                              # contact speed (m/s) and rebound coefficient (dv = (1 + e) v_in n)
RELEASE = .25                                  # s: a poised stroke's release, contact -> hover
A_APEX = -5.0                                  # m/s^2: a phrase stroke's acceleration through its apex turn (C2 there)
V_HOME = 1.3                                   # m/s: the homing legs' peak tool speed (<= 0.5 SERVO_V_MAX = 1.5)
HOME_T0 = .5                                   # s: the homing sweep starts here, in the first rest
JERK_N = 20001                                 # samples a head hermite's declared jerk is taken over (the vertex to ~1e-9)
EVENTS = [(20.0, 'harp05'), (21.5, 'harp08'), (23.0, 'harp06'), (24.5, 'harp08'),
          (26.0, 'harp05'), (26.5, 'harp05'), (26.68, 'harp05')]   # gaps 1.5 s (poised), then IOI 0.5 and 0.18 (phrase)
TOTAL = 29.0                                   # s: the synthetic score's length (the last release ends by 26.93)

failures = []
def check(ok, msg):
    print(('  PASS ' if ok else '  FAIL ')+msg)
    if not ok: failures.append(msg)

def pad8(q):
    c = np.zeros(8); co = np.asarray(q.coef if hasattr(q, 'coef') else q, float); c[:len(co)] = co; return c

def scurve_pieces(r):
    """The servo S-curve s(u) (formlab.rig.scurve) as its three polynomial pieces in u: (u0, u1, s)."""
    P = np.polynomial.Polynomial; k = 1/(1-r)
    up = P([0, 0, 0, k/r**2, -k/(2*r**3)])                     # r ramp(u/r)/(1 - r), ramp(w) = w^3 - w^4/2
    cruise = P([-r/2*k, k])                                     # (r/2 + u - r)/(1 - r)
    w = P([1/r, -1/r])                                          # (1 - u)/r
    down = 1-(r*k)*(w**3-w**4/2)
    return [(0.0, r, up), (r, 1-r, cruise), (1-r, 1.0, down)]

class _Off:
    """A head segment's cy or cz as a Channel piece (None = no offset: zeros)."""
    def __init__(self, g, coef):
        self.t0, self.t1, self.ref = g.t0, g.t1, g.ref
        c = getattr(g, coef); self.c = np.zeros(8) if c is None else np.asarray(c, float)

class Plan:
    """A ServoStroke built by hand: head and carriage Seg lists filled in time order."""
    def __init__(self, rig, aid, r=RM.SCURVE_R, travel_ids=True):
        self.rig = rig; self.aid = aid; self.r = r; self.travel_ids = travel_ids
        n = np.asarray(rig.clearance(aid), float); self.n = n/np.linalg.norm(n)
        self.c = np.asarray(rig.contact(rig.acts[aid]['home'], PICK), float); self.home_c = self.c.copy()
        self.head, self.car, self.knots, self.legs = [], [], [], []
        self.th = self.tc = -np.inf; self.h = (HOVER, 0.0, 0.0); self.y = (0.0, 0.0, 0.0); self.tid = 0
        self.frame = None

    # ---- carriage
    def c_hold(self, t1, tag='hold'):
        self.car.append(ST.Seg(self.tc, t1, ST.law_hold(self.c[0]), 'hold', tag, 'carriage',
                               cy=ST.law_hold(self.c[1]), cz=ST.law_hold(self.c[2])))
        self.tc = t1

    def c_move(self, t0, t1, target, tag='travel', ev=-1, r=None):
        """An S-curve move of the carriage point to `target` over [t0, t1], as its three pieces."""
        if t0 > self.tc: self.c_hold(t0)
        r = self.r if r is None else r; p0 = self.c.copy(); D = np.asarray(target, float)-p0; Tm = t1-t0
        u = np.polynomial.Polynomial([0.0, 1/Tm])
        for ua, ub, s in scurve_pieces(r):
            q = s(u+ua)
            co = [pad8(p0[k]+D[k]*q) for k in range(3)]
            extra = dict(travel=self.tid) if self.travel_ids else {}
            self.car.append(ST.Seg(t0+ua*Tm, t1 if ub == 1.0 else t0+ub*Tm, co[0], 'scurve', tag, 'carriage', ev, extra, cy=co[1], cz=co[2]))
        self.tid += 1; self.c = np.asarray(target, float); self.tc = t1

    # ---- head
    def h_hold(self, t1, tag='hold', ev=-1):
        cy = ST.law_hold(self.y[0]) if self.y[0] != 0 else None
        self.head.append(ST.Seg(self.th, t1, ST.law_hold(self.h[0]), 'hold', tag, 'head', ev, {}, cy=cy))
        self.th = t1; self.h = (self.h[0], 0.0, 0.0); self.y = (self.y[0], 0.0, 0.0)

    def h_herm(self, t1, p1, v1=0.0, a1=0.0, tag='wind-up', ev=-1, y1=None, declare_y=True, v0=None):
        """A quintic Hermite of h (and hy when it moves or is off zero) from the current state to (p1, v1, a1)."""
        T = t1-self.th; p0, w0, a0 = self.h
        if v0 is not None: w0 = v0                   # a corner, on purpose
        extra = dict(p0=p0, v0=w0, a0=a0, p1=p1, v1=v1, a1=a1)
        cy = None
        if y1 is not None or self.y[0] != 0:
            y1 = (self.y[0], 0.0, 0.0) if y1 is None else y1
            cy = ST.law_hermite(*self.y, *y1, T)
            if declare_y: extra['hy'] = dict(p0=self.y[0], v0=self.y[1], a0=self.y[2], p1=y1[0], v1=y1[1], a1=y1[2])
            self.y = tuple(y1)
        self.head.append(ST.Seg(self.th, t1, ST.law_hermite(p0, w0, a0, p1, v1, a1, T), 'quintic hermite', tag, 'head', ev, extra, cy=cy))
        self.th = t1; self.h = (p1, v1, a1)

    def contact(self, t, ev):
        dv = (1+E)*V_IN*self.n
        self.knots.append(ST.Knot(t, 'contact', dv, ev, dict(e=E, v_in=V_IN)))
        self.h = (0.0, E*V_IN, 0.0)

    # ---- the plan
    def home(self, rig, aid, x_off=0.0):
        """x legs home -> lo -> hi -> home, then the elbow and shoulder sweeps at home."""
        reach = rig.acts[aid]['reach']; home = self.c.copy()
        lo = np.asarray(rig.contact(reach[0], PICK), float); hi = np.asarray(rig.contact(reach[-1], PICK), float)
        t = HOME_T0
        for k, tgt in enumerate((lo, hi, home+[x_off, 0, 0])):
            T = 1/(1-self.r)*float(np.linalg.norm(tgt-self.c))/V_HOME
            self.c_move(t, t+T, tgt, tag='home'); t += T
        self.h_hold(t)
        cfg = rig.geometry['arms'][aid]; base = self.c+np.asarray(rig.hover(aid), float)
        root, elbow, wrist, _ = R.ik(cfg, base[None]); u_ = (elbow-root)[0]; f = (wrist-elbow)[0]
        sh0 = float(np.arctan2(u_[1], u_[2])); fa0 = float(np.arctan2(f[1], f[2]))
        e0 = float(R.joint_series(root, elbow, wrist)['elbow'][0])
        self.frame = fr = dict(base=base, root=root[0], sh0=sh0, fa0=fa0, e0=e0, sgn=1.0 if R._wrap(fa0-sh0) >= 0 else -1.0,
                               l1=float(cfg['l1']), l2=float(cfg['l2']), wo=Rig.wrist_offset(cfg), r_sh=float(np.linalg.norm(wrist[0]-root[0])))
        spans = dict(zip(('shoulder', 'elbow'), rig.joint_spans(aid)))
        for joint in ('elbow', 'shoulder'):
            q = ST.joint_points(joint, spans[joint]); rad = fr['l2'] if joint == 'elbow' else fr['r_sh']
            T = 1.875*rad*sum(abs(b-a) for a, b in zip(q, q[1:]))/V_HOME      # every leg peaks at V_HOME (3-4-5: 1.875 D/T)
            for g in ST.joint_legs(joint, t, t+T, spans[joint]):
                self.legs.append(dict(g, joint=joint, frame=fr, span=spans[joint], radius=rad))
            self.h_hold(t+T, tag='home'); t += T
        self.c_hold(t)
        return t

    def poised(self, t, sid, ev, rise=RISE, poise=POISE, apex=APEX, skew=0.0, corner=None, y=None, declare_y=True):
        tgt = np.asarray(self.rig.contact(sid, PICK), float)
        self.h_hold(t-rise)
        if np.linalg.norm(tgt-self.c) > 1e-12: self.c_move(t-rise, t-poise, tgt, ev=ev)
        self.h_herm(t-poise-skew, apex, tag='wind-up', ev=ev, y1=None if y is None else (y, 0.0, 0.0), declare_y=declare_y)
        self.h_hold(t-ACT, ev=ev)
        self.c_hold(t+RELEASE)
        self.h_herm(t, 0.0, -V_IN, 0.0, tag='stroke', ev=ev, v0=corner, y1=None if y is None else (0.0, 0.0, 0.0), declare_y=declare_y)
        self.contact(t, ev)

    def release(self, t):
        self.h_herm(t+RELEASE, HOVER, tag='release')

    def phrase(self, t_prev, t, ev, apex=HOVER):
        T_down = min(max(.4*(t-t_prev), .08), .15)
        self.h_herm(t-T_down, apex, 0.0, A_APEX, tag='release')
        self.h_herm(t, 0.0, -V_IN, 0.0, tag='stroke', ev=ev)
        self.contact(t, ev)

    def finish(self):
        self.h_hold(np.inf); self.c_hold(np.inf)

def declare_jerk(g, n, vector=True):
    """A head hermite's declared jerk: the peak of its own |h''' n + (0, hy''', 0)| (h only when not `vector`)."""
    tau = np.linspace(0.0, g.T, JERK_N); h3 = ST._horner(ST._dcoef(g.c, 3), tau)
    y3 = ST._horner(ST._dcoef(g.cy, 3), tau) if (vector and g.cy is not None) else 0*tau
    J = np.sqrt((h3*n[0])**2+(h3*n[1]+y3)**2+(h3*n[2])**2)
    return float(J.max())

class FakeServo:
    """formlab/servo.py's ServoStroke surface (the lead's contract), over a Plan."""
    def __init__(self, plan, aid, vector_jerk=True):
        self.n = plan.n; self.arm = dict(aid=aid, synthetic=True); self.issues = []
        for g in plan.head:
            if g.law == 'quintic hermite': g.extra['jerk'] = declare_jerk(g, self.n, vector_jerk)
        self.head = ST.Channel('head', plan.head); self.carriage = ST.Channel('carriage', plan.car)
        self.yc = ST.Channel('yc', plan.car, 'cy'); self.zc = ST.Channel('zc', plan.car, 'cz')
        self.hy = ST.Channel('hy', [_Off(g, 'cy') for g in plan.head]); self.hz = ST.Channel('hz', [_Off(g, 'cz') for g in plan.head])
        self.knots = list(plan.knots); self._home = plan.home_c.copy()
        self.notes = [SimpleNamespace(i=k, t=kn.t, event=kn.event, style='synthetic') for k, kn in enumerate(plan.knots)]

    def _d(self, t, d, side):
        h = np.asarray(self.head.ev(t, d, side))[..., None]
        car = np.stack([self.carriage.ev(t, d, side), self.yc.ev(t, d, side), self.zc.ev(t, d, side)], -1)
        hy = np.asarray(self.hy.ev(t, d, side)); off = np.stack([0*hy, hy, np.asarray(self.hz.ev(t, d, side))], -1)
        return car+h*self.n+off

    def p(self, t, side=+1): return self._d(t, 0, side)
    def v(self, t, side=+1): return self._d(t, 1, side)
    def a(self, t, side=+1): return self._d(t, 2, side)
    def j(self, t, side=+1): return self._d(t, 3, side)
    def segments(self, channel=None):
        return [g for ch in (self.head, self.carriage) if channel in (None, ch.name) for g in ch.segs]
    def rest_point(self): return self._home+HOVER*self.n

def declared(st, legs):
    """Rig.declared's construction (the mallet's, PLAYERS M1) for the synthetic stroke."""
    def ext(d): return {k: (list(v) if isinstance(v, (list, tuple, np.ndarray)) else v) for k, v in d.items()}
    segs = [SEG.Segment(g.t0, g.t1, g.law, g.tag, g.event, ext(g.extra))
            for g in st.head.segs+st.carriage.segs if not (g.channel == 'head' and g.tag == 'home')]
    for g in legs:
        segs.append(SEG.Segment(g['t0'], g['t1'], '3-4-5', 'home', -1, dict(
            channel='head', joint=g['joint'], leg=g['leg'], q0=g['q0'], q1=g['q1'], span=g['span'], jerk=Rig._leg_jerk(g, g['radius']))))
    segs.sort(key=lambda g: (g.t0, g.extra['channel']))
    knots = [SEG.Knot(k.t, k.kind, None if k.dv is None else np.asarray(k.dv, float).copy(), k.event, dict(k.extra)) for k in st.knots]
    imp = np.array(sorted(k.t for k in knots if k.kind in SEG.IMPULSES))
    joins = set()
    for ch in ('head', 'carriage'):
        cs = [g for g in segs if g.extra['channel'] == ch]; joins.update(g.t0 for g in cs[1:])
    for t in sorted(joins):
        if imp.size and np.min(np.abs(imp-t)) <= 1e-9: continue
        knots.append(SEG.Knot(t, 'smooth'))
    knots.sort(key=lambda k: (k.t, k.kind))
    return SEG.Declared(segs, knots, [], None, native=True)

def events():
    out = []; prev = None
    for i, (t, sid) in enumerate(EVENTS):
        poised = prev is None or t-prev >= 1.0
        out.append(dict(i=i, t=t, mech='harp', voice='ground', strings=[sid], midis=[60.0], amp=.7, pick=PICK, dur=1.0,
                        spread_s=0.0, actuator=AID, t_move=t-(RISE if poised else .09), t_free=t+.05, t_head_free=t+.05))
        prev = t
    return out

def build(rig, **kw):
    """The plan, with the broken variants' switches: rise (3 lead), corner (6a/6b), r (6c), skew (22 sync),
    dx_apex (22 repeat), home_off (22 home), y / declare_y / vector_jerk (6c's vector head), travel_ids."""
    pl = Plan(rig, AID, r=kw.get('r', RM.SCURVE_R), travel_ids=kw.get('travel_ids', True))
    pl.home(rig, AID, x_off=kw.get('home_off', 0.0))
    prev = None
    for i, (t, sid) in enumerate(EVENTS):
        if prev is None or t-prev >= 1.0:
            tgt = np.asarray(rig.contact(sid, PICK), float); dx = abs(float(tgt[0]-pl.c[0]))
            pl.poised(t, sid, i, rise=kw.get('rise', {}).get(i, RISE), apex=APEX+kw.get('dx_apex', 0.0)*dx,
                      skew=kw.get('skew', {}).get(i, 0.0), corner=kw.get('corner', {}).get(i),
                      y=kw.get('y', {}).get(i), declare_y=kw.get('declare_y', True))
            nxt = EVENTS[i+1][0] if i+1 < len(EVENTS) else None
            if nxt is None or nxt-t >= 1.0: pl.release(t)
        else:
            pl.phrase(prev, t, i)
            if i+1 == len(EVENTS) or EVENTS[i+1][0]-t >= 1.0: pl.release(t)
        prev = t
    pl.finish()
    return pl

def subject(**kw):
    layout = json.loads(LAYOUT.read_text()); base = json.loads(SCORE.read_text())
    sc = dict(base, events=events(), total_s=TOTAL, cues=[])
    S = core.Subject.__new__(core.Subject)
    S.asset = 'chamber'; S.manifest_path = LAYOUT; S.score_path = SCORE; S.camera_path = None
    S.layout = layout; S.score = sc; S.rig = rig = Rig(sc, layout); S.total = TOTAL
    S.arms = {aid: rig.acts[aid]['kind'] for aid in rig.plans if rig.plans[aid]}
    S.t_frames = core.frames(TOTAL); S.t_hz = np.arange(0, int(TOTAL*core.HZ)+1)/core.HZ; S._amp_range = S._voice_amps()
    pl = build(rig, **kw); st = FakeServo(pl, AID, kw.get('vector_jerk', True)); dec = declared(st, pl.legs)
    o_stroke, o_path, o_decl = rig.stroke, rig.path_at, rig.declared
    legs = pl.legs; starts = np.array([g['t0'] for g in legs])
    def path_at(aid, t):
        if aid != AID: return o_path(aid, t)
        if legs and legs[0]['t0'] < t < legs[-1]['t1']:
            g = legs[int(np.searchsorted(starts, t, 'right'))-1]
            q = g['q0']+(g['q1']-g['q0'])*float(ST.s345((t-g['t0'])/(g['t1']-g['t0'])))
            return Rig._fk(g['frame'], g['joint'], q)
        return np.asarray(st.p(float(t)), float)
    rig.stroke = lambda aid: st if aid == AID else o_stroke(aid)
    rig.path_at = path_at
    rig.declared = lambda aid: dec if aid == AID else o_decl(aid)
    return S, pl, st

def rows(S, which):
    out = {}
    for fn in which:
        for r in fn(S):
            if r.scope == AID: out[r.name] = r
    return out

def show(tag, rs):
    for name, r in rs.items():
        mark = 'n/a ' if r.passed is None else 'info' if r.passed == core.INFO else 'PASS' if r.passed else 'FAIL'
        keep = {k: v for k, v in r.value.items() if k in ('n', 'fail', 'left_out', 'knots', 'fail_dv', 'fail_da', 'count', 'max_dv',
                                                          'segments', 'worst_ratio', 'worst_seg', 'bound', 'undeclared', 'na',
                                                          'declared_below_closed', 'ok', 'skew_arrive_ms', 'by_kind', 'groups',
                                                          'rms_mm', 'over_1mm', 'x_swept_frac', 'joint_swept_frac', 'v_peak',
                                                          'land_m', 'home_segments', 'laws', 'not_allowed')}
        print(f'    [{tag}] {mark} {name:<26s} {json.dumps(keep, default=float)[:260]}')

def main():
    t0 = time.time()
    # ---- the S-curve the ruler's closed form is for
    r = RM.SCURVE_R; u = np.linspace(0, 1, 200001)
    pieces = scurve_pieces(r); s = np.empty_like(u); s3 = np.empty_like(u)
    for ua, ub, q in pieces:
        m = (u >= ua) & (u <= ub); s[m] = q(u[m]); s3[m] = q.deriv(3)(u[m])
    ref = np.array([R.scurve(x) for x in u[::50]])
    check(np.abs(s[::50]-ref).max() < 1e-12 and abs(np.abs(s3).max()-RM.SCURVE_J) < 1e-9*RM.SCURVE_J
          and abs(RM.SCURVE_J-6/(r*r*(1-r))) < 1e-12 and abs(RM.SCURVE_J-95.238095238) < 1e-6,
          f'the S-curve pieces are rig.scurve (r = {r}) to {np.abs(s[::50]-ref).max():.1e}; peak |s\'\'\'| {np.abs(s3).max():.6f} '
          f'= 6/(r^2(1 - r)) = SCURVE_J {RM.SCURVE_J:.6f}; peak s\' {np.abs(np.gradient(s, u)).max():.4f} = 1/(1 - r) {1/(1-r):.4f}')
    # each piece's own s''' (its polynomial, not the ramp formula) on its overlap with [ua, ub], ends included:
    # a range that only touches a piece at a point takes nothing from it (the knot belongs to the next piece)
    ok = True; worst = 0.0
    for ua, ub in ((0, r), (r, 1-r), (1-r, 1), (0, 1), (.1, .2), (.25, .5), (.8, .95), (.2, .9)):
        num = 0.0
        for pa, pb, q in pieces:
            a, b = max(ua, pa), min(ub, pb)
            if b-a > 1e-9: num = max(num, float(np.abs(q.deriv(3)(np.linspace(a, b, 2001))).max()))
        worst = max(worst, abs(RM._scurve_peak(ua, ub)-num)); ok &= abs(RM._scurve_peak(ua, ub)-num) < 1e-9*RM.SCURVE_J
    check(ok, f'r_motion._scurve_peak matches each piece\'s own max |s\'\'\'| on ramps, cruise, whole moves and sub-ranges (to {worst:.1e})')

    # ---- the good plan: every generalised row passes (but '3 preparation' on its one 0.18 s IOI)
    S, pl, st = subject()
    check(RMa._native(S, AID) and S.stroke(AID) is st and not RMa._mallet(S, AID),
          f'{AID} reads as a native servo (r_machine._native, core.Subject.stroke), not as a mallet')
    good = rows(S, (RM.r3_preparation, RM.r6_smoothness, RMa.precision)); show('good', good)
    g3 = good['3 preparation'].value['fail']
    check(good['3 lead (IOI >= 0.25 s)'].passed is True and good['3 lead (IOI >= 0.25 s)'].value['left_out'] == 1
          and good['3 preparation'].passed is False and g3['windup'] == 1 and g3['depth'] == g3['lead'] == g3['lead415'] == 0,
          '3: the 0.18 s IOI pluck (W = 0.10 s < 4 frames) fails 3 preparation only; 3 lead leaves it out and passes')
    for name in ('6a smooth knots', '6a impulse knots', '6b corners', '6c jerk', '6c laws', 'sync', 'repeat', 'home'):
        check(good[name].passed is True, f'good plan: {name} passes')
    j = good['6c jerk'].value
    check(j['bound'].get('closed', 0) >= 3*4 and j['by_channel']['carriage']['segments'] > 0 and not j['undeclared'] and not j['na'],
          f'6c judges the carriage S-curve pieces on the closed form ({j["bound"]}), worst {j["worst_ratio"]} on {j["worst_seg"]}')
    sy = good['sync'].value
    check(sy['by_kind'].get('travel->hold', {}).get('n') == 5 and sy['by_kind'].get('home', {}).get('n') == 9,
          f'22 sync: the 5 slews into a poise and the 9 home legs (3 x, 6 joint) are its targets ({sy["by_kind"]}), '
          f'arrival skew {sy["skew_arrive_ms"]}')
    rp = good['repeat'].value
    check(rp['groups'] == 1 and rp['strokes'] == 2 and rp['rms_mm']['max'] < 1e-6,
          f'22 repeat: harp08 at 21.5 s and 24.5 s (from harp05 and harp06, to harp06 and harp05) repeat to {rp["rms_mm"]["max"]:.2e} mm '
          'with the whole carriage point taken out')
    # the mallet's x-only reading would see the harp's y blend as head motion
    mem = [c for c in S.contacts(AID) if c.event['strings'] == ['harp08']]
    heads = RMa._decl_segments(S, AID, 'head'); paths = []
    for c in mem:
        nxt = S.contacts(AID)[c.i+1]; a, b = RMa._repeat_window_m(heads, c, nxt, S.total)
        uu = np.linspace(a, b, 64); P = RMa._mallet_path(S, AID, uu); P[:, 0] = float(S.rig.path_at(AID, c.t)[0]); paths.append(P)
    xonly = float(np.sqrt(np.mean(np.sum((paths[0]-paths[1])**2, axis=1))))
    check(xonly > 1e-3, f'(the mallet\'s x-only carriage would read {xonly*1e3:.1f} mm on the same pair: the harp\'s y_c blend)')
    hm = good['home'].value
    check(hm['x_swept_frac'] >= .9 and min(hm['joint_swept_frac'].values()) >= .8 and hm['land_m'] <= 1e-9,
          f'22 home: x {hm["x_swept_frac"]}, joints {hm["joint_swept_frac"]}, v_peak {hm["v_peak"]} m/s, lands {hm["land_m"]:.1e} m')

    # ---- no travel ids: sync groups the contiguous S-curve pieces itself
    S2, _, _ = subject(travel_ids=False)
    nt = rows(S2, (RMa.precision,))['sync']
    check(nt.passed is True and nt.value['n'] == sy['n'] and nt.value['by_kind'] == sy['by_kind'],
          f'no travel id on the carriage pieces: sync finds the same {nt.value["n"]} targets and passes')

    # ---- a declared vector head (the rake's (y, z) form): 6c's vector branch, declared jerk >= the vector closed form
    S3, _, _ = subject(y={2: .12})
    v3 = rows(S3, (RM.r6_smoothness,)); show('vector', v3)
    check(v3['6c jerk'].passed is True and v3['6c jerk'].value['declared_below_closed'] == 0,
          'a vector head declared in extra[\'hy\'] (0.12 m over the rise, back in the action) passes 6c on its vector closed form')

    # ---- broken variants: each row must FAIL
    def broken(tag, fns, name, **kw):
        Sb, _, _ = subject(**kw); rb = rows(Sb, fns); show(tag, {k: v for k, v in rb.items() if k == name or k.startswith(name)})
        return rb[name]
    b = broken('lead', (RM.r3_preparation,), '3 lead (IOI >= 0.25 s)', rise={3: .41})
    f3 = b.value['fail']
    check(b.passed is False and f3['lead415'] == 1 and f3['windup'] == f3['depth'] == f3['lead'] == 0,
          '3 lead: a 0.41 s lead at gap 1.5 s (W = 0.21 s, 6.3 frames) fails on L < 415 ms alone')
    b = broken('corner', (RM.r6_smoothness,), '6a smooth knots', corner={1: -.5})
    check(b.passed is False and b.value['fail_dv'] >= 1, f'6a: an action leaving its poise at -0.5 m/s fails (|dv| {b.value["max_dv"]} m/s)')
    Sb, _, _ = subject(corner={1: -.5}); b6 = rows(Sb, (RM.r6_smoothness,))['6b corners']
    check(b6.passed is False and b6.value['count'] >= 1, f'6b: the same corner is counted ({b6.value["count"]}, |dv| {b6.value["max_dv"]} m/s)')
    b = broken('jerk', (RM.r6_smoothness,), '6c jerk', r=.15)
    check(b.passed is False and b.value['by_channel']['carriage']['fail'] > 0,
          f'6c: a carriage built on r = 0.15, declared scurve, fails (worst ratio {b.value["worst_ratio"]}, '
          f'{6/(.15**2*.85)/RM.SCURVE_J:.2f}x the closed form at its ramps)')
    b = broken('vector undeclared', (RM.r6_smoothness,), '6c jerk', y={2: .12}, declare_y=False, vector_jerk=False)
    check(b.passed is False and b.value['by_channel']['head']['fail'] > 0,
          f'6c: the same vector head with hy undeclared (held to h\'s bound) fails (worst ratio {b.value["worst_ratio"]} on {b.value["worst_seg"]})')
    b = broken('below', (RM.r6_smoothness,), '6c jerk', y={2: .12}, vector_jerk=False)
    check(b.passed is False and b.value['declared_below_closed'] > 0,
          f'6c: hy declared but the jerk declared on h alone is below the vector closed form ({b.value["declared_below_closed"]} segments)')
    b = broken('skew', (RMa.precision,), 'sync', skew={2: .015})
    worst = [f for f in b.value.get('failing', []) if f['what'] == 'travel->hold']
    check(b.passed is False and worst and worst[0]['skew_ms'][1] > 1e3/240,
          f'22 sync: a head arriving 15 ms before its carriage fails (arrival skew {worst[0]["skew_ms"][1] if worst else None} ms)')
    b = broken('repeat', (RMa.precision,), 'repeat', dx_apex=.2)
    check(b.passed is False and b.value['over_1mm'] == 1, f'22 repeat: an apex that grows 0.2 m per m travelled fails ({b.value["rms_mm"]["max"]:.2f} mm)')
    b = broken('home', (RMa.precision,), 'home', home_off=1e-3)
    check(b.passed is False and abs(b.value['land_m']-1e-3) < 1e-6, f'22 home: a sweep landing 1 mm off the home rest fails (land {b.value["land_m"]:.4f} m)')
    print(f'SERVO RULERS: {"FAIL" if failures else "PASS"} ({time.time()-t0:.0f} s)')
    return 1 if failures else 0

if __name__ == '__main__':
    sys.exit(main())

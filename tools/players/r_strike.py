"""Rulers 7 (impact), 8 (rebound and float), 10 (hammer arc), 11 (contact
frame), 19 (ratchet) and 21 (intent) of docs/goals/the-players.md
("Acceptance"): the struck heads — the bars and bells mallets (kind 'mallet')
and the expanded asset's hinged hammer (kind 'hammer', blocks_arm0) — and the
ratchet carriage that carries them.

Channels. The contact face is the felt (Rig.pose 'felt': the tip for a
mallet, the hinged head's face for the hammer). `rendered` is what the film
shows: Rig.tip_at (the scored path plus the recoil bus, whose `bounce` term is
today's only rebound) plus the head offset, which is exactly
core.Subject.contact_point without the IK. `scored` is Rig.path_at plus the
head offset with the hammer's check bounce left out (segments declares it a
ring, channel 'head'): the path without rings, ruler 3's channel for
h(t) = (p - c_i)·n_i, n the contact's normal (+y for a struck head). The
ratchet carriage (19) is root.x: rendered = Rig.tip_at x (the detent ring
included), scored = Rig.path_at x.

Per contact, shared by 7, 8, 10 and 21 and cached on the Subject (`strokes`):

  t_apex   ruler 3's: the start of the last interval before t_i with dh/dt < 0
           on the scored face (a 1 ms scan back from t_i, refined to 20 us; a
           plateau's apex is where the descent leaves it). T_down = t_i - t_apex.
  W        the wind-up: the maximal interval before t_apex with dh/dt > 0; its
           start is where "the rise begins" (21, accents).
  hold     how long the scored face stays within 1 mm of where it is at
           t_apex, around t_apex, between the previous contact and t_i.
  v-, v+   one-sided 5-point derivatives of the rendered face at t_i (H = 1e-5 s).
  float    the upstroke on the rendered face from t_i + 5 ms to t_up, the
           first time after that the face stops rising (v·n <= 0; 1 ms scan,
           bisected to 1 us); h_up = h(t_up) is the float's apex.

Ruler 19 splits each carriage travel by regime: STEPPED when its window
gives every tooth >= STEP_FRAMES frames (the film can show the steps),
FREEWHEEL otherwise. Ruler 8's float time is judged at IOI_next <= FLOAT_IOI.

Definitions where the goal leaves a choice are stated at each ruler below.
"""
import math
import numpy as np
from players import core
from players.core import Result, deriv, spearman, FPS, G, H
from formlab import rig as R

KINDS = ('mallet', 'hammer')
DT = 1e-3            # s: scan step
FINE = 50            # refinement points per scan step (20 us)
TOL = 1e-9           # m: h "changes" over a scan step when it moves more than this
HOLD_R = 1e-3        # m: a hold keeps the face within this of its apex position
FLOAT_SKIP = .005    # s: the float is judged from t_i + 5 ms (ruler 8)
# The head's extent along x, E(head, x) = 2r + |seg·x|: the mallet's wound
# head is a sphere r 0.06 (formlab/linkage.py mallet_tool; arm_capsules has no
# capsule for it), the hammer's felt is arm_capsules' 'head' ball, r head_r*1.02.
E_HEAD = dict(mallet=2*.06, hammer=2*R.HAMMER['head_r']*1.02)
ACCENT_JUMP = .15    # an accent: amp above the arm's previous note by at least this (the tune's 0.85 over 0.6)
HOLD_GAP = .8        # s: ruler 21's holds belong after gaps at least this long
A_STOP = 3*G         # ratchet carriage ceiling (rule 3), and 5 g for a counted hurried travel
A_HURRIED = 5*G
# Rule 4's allowed laws, under the names the declared vocabulary may use for
# them (r_motion.ALLOWED_LAWS spells some differently). 'linear' and 'hold'
# are not here: a freewheel must start and end at rest (x' = x'' = 0).
SMOOTH_LAWS = ('3-4-5', '4-5-6-7', 'cycloidal', 'modified sine', 'modified trapezoid', 'scurve', 'servo S-curve',
               'quintic', 'septic', 'quintic hermite', 'septic hermite', 'ballistic')
STEP_FRAMES = 3      # a travel is STEPPED when each tooth can take >= 3 frames of its window (Q4), else FREEWHEEL
DETENT_TOL = .1*R.PITCH   # m: "on the detent" = within the pawl's play, 0.1 tooth (4.7 mm; R.OVERSHOOT*PITCH today)
PAWL_RIDE = 15.0     # teeth/s: below this the pawl drops into every tooth, above it rides the tips
FLOAT_IOI = 1.0      # s: ruler 8's float leads to the next apex at IOI <= 1 s; above it is a free bounce loop
# Ruler 19's hurried-travel ceiling "<= today's count until M8": today's count
# (the 6c326b5 motion), measured by this ruler at M0 and frozen here.
TODAY_HURRIED = {'chamber': {'bars_arm0': 12, 'bars_arm1': 2},
                 'expanded': {'bars_arm0': 12, 'bars_arm1': 2, 'bells_arm0': 0, 'bells_arm1': 0, 'blocks_arm0': 16}}
HURRIED_END = 6

# ---- helpers ------------------------------------------------------------------

def _f(x, nd=4):
    """A JSON-able rounded float (None for nan/inf/None)."""
    if x is None: return None
    x = float(x)
    return None if not math.isfinite(x) else round(x, nd)

def _st(x, nd=4):
    """min / p50 / max (and n) of a sample, rounded; None if empty."""
    x = np.asarray([v for v in x if v is not None and math.isfinite(v)], float)
    if x.size == 0: return None
    return dict(min=_f(x.min(), nd), p50=_f(np.median(x), nd), max=_f(x.max(), nd), n=int(x.size))

def _rho(x, y, nd=4):
    """Spearman on values rounded to 10^-nd, so float noise cannot rank."""
    r = spearman(np.round(np.asarray(x, float), nd), np.round(np.asarray(y, float), nd))
    return None if not math.isfinite(r) else round(r, 3)

def struck_arms(S): return [a for a in S.arms if S.kind(a) in KINDS]

def _head_angle_noring(rig, aid, t):
    """Rig.head_angle without the check's bounce, which segments._rings_today
    declares a ring ('check', channel 'head'): rest on the check, the cocked
    flip over the strike, 0 through the contact, the quintic lay-back over the
    release. Mirrors formlab/rig.py head_angle branch for branch (and
    r_motion.point_fn, so ruler 3's apex and this module's agree)."""
    if not rig.hammer(aid): return 0.0
    rest = rig.rest_angle(aid); c = R.HAMMER['cock']
    for s in rig.sched[aid]:
        if t < s['go']: return rest
        if t < s['hit']:
            if s['moving'] and t < s['approach']: return rest
            start = s['approach'] if s['moving'] else max(s['tm'], s['approach'])
            u = min(max((t-start)/max(s['hit']-start, 1e-6), 0.0), 1.0)
            return rest*R.cocked(u, c)
        if t <= s['end']: return 0.0
        if t < s['t_free']:
            return rest*R.quintic((t-s['end'])/max(s['t_free']-s['end'], 1e-6))
    return rest

def face_fn(S, aid, rendered=True):
    """t -> the contact face. rendered: Rig.tip_at + head offset at
    Rig.head_angle (= Rig.pose 'felt', rings and check bounce included);
    scored: Rig.path_at + head offset at the ring-free head angle (no rings)."""
    rig = S.rig
    if not rig.hammer(aid): return (lambda t: rig.tip_at(aid, t)) if rendered else (lambda t: rig.path_at(aid, t))
    sign = rig.flip_sign(aid)
    if rendered: return lambda t: rig.tip_at(aid, t)+R.head_offset(rig.head_angle(aid, t), sign)
    return lambda t: rig.path_at(aid, t)+R.head_offset(_head_angle_noring(rig, aid, t), sign)

def _latest_extreme(h, a, b, want_max):
    """On [a, b] at FINE points per DT: the latest time where h is within TOL
    of its max (min) — a plateau's edge where the motion leaves it."""
    ts = np.linspace(a, b, max(3, int(round((b-a)/DT*FINE))+1))
    hs = np.array([h(t) for t in ts])
    ext = hs.max() if want_max else hs.min()
    ok = hs >= ext-TOL if want_max else hs <= ext+TOL
    k = int(np.nonzero(ok)[0][-1]); return float(ts[k]), float(hs[k])

def _apex_before(h, t_i, t_lo):
    """Ruler 3's t_apex: the start of the last interval before t_i with dh/dt < 0."""
    t, ht = t_i, h(t_i); moved = False
    while True:
        tp = max(t-DT, t_lo); hp = h(tp)
        if hp <= ht+TOL: break
        t, ht, moved = tp, hp, True
        if tp <= t_lo: return t, ht
    if not moved: return t_i, h(t_i)
    return _latest_extreme(h, tp, min(t_i, t+DT), True)

def _rise_start(h, t_apex, t_lo):
    """The start of the wind-up W: the maximal interval before t_apex with dh/dt > 0."""
    t, ht = t_apex, h(t_apex); moved = False
    while True:
        tp = max(t-DT, t_lo); hp = h(tp)
        if hp >= ht-TOL: break
        t, ht, moved = tp, hp, True
        if tp <= t_lo: return t
    if not moved: return t_apex
    return _latest_extreme(h, tp, min(t_apex, t+DT), False)[0]

def _hold(f, t0, lo, hi):
    """The time around t0 that f stays within HOLD_R of f(t0), inside [lo, hi]
    (10 ms strides, then 1 ms, so a long park costs little)."""
    p0 = f(t0); a = b = t0
    for step in (10*DT, DT):
        while a-step > lo and np.linalg.norm(f(a-step)-p0) <= HOLD_R: a -= step
        while b+step < hi and np.linalg.norm(f(b+step)-p0) <= HOLD_R: b += step
    return b-a

def _float(f, n, t_i, t_hi):
    """The upstroke after a contact on channel f: samples of v·n and a·n from
    t_i + 5 ms until the face stops rising, and the turning time t_up."""
    vn = lambda t: float(deriv(f, t, +1, 1)@n)
    t = t_i+FLOAT_SKIP; ts, vs, accs = [], [], []
    turned = False
    while t < t_hi:
        v = vn(t)
        if v <= 0: turned = True; break
        ts.append(t); vs.append(v); accs.append(float(deriv(f, t, +1, 2)@n)); t += DT
    if not ts: t_up = min(t_i+FLOAT_SKIP, t_hi)
    elif not turned: t_up = t_hi
    else:
        lo, hi = ts[-1], t
        for _ in range(10):
            mid = .5*(lo+hi)
            if vn(mid) > 0: lo = mid
            else: hi = mid
        t_up = hi
    return dict(t=np.array(ts), v=np.array(vs), a=np.array(accs), t_up=t_up, turned=turned)

def _elbow_deg(p):
    a = p['root']-p['elbow']; b = p['wrist']-p['elbow']
    return math.degrees(math.acos(np.clip(a@b/(np.linalg.norm(a)*np.linalg.norm(b)), -1, 1)))

def _pin(S, aid, t):
    """The pin the head swings about: the hammer's hinge (tool frame + head_l
    up, as formlab.clearance places it); a mallet has no hinge today, so the
    wrist pin, where the M5 hinge goes (Rig.wrist_offset)."""
    rig = S.rig; p = rig.path_at(aid, t)
    if rig.hammer(aid): return p+np.array([0, R.HAMMER['head_l'], 0])
    return p+rig.wrist_offset(S.cfg(aid))

def strokes(S, aid):
    """Per contact of a struck arm: everything 7, 8, 10 and 21 measure."""
    cache = S.__dict__.setdefault('_r_strike', {})
    if aid in cache: return cache[aid]
    rig = S.rig; cs = S.contacts(aid); out = []
    rend = face_fn(S, aid, True); scored = face_fn(S, aid, False)
    for i, c in enumerate(cs):
        n = c.normal; cp = c.point
        hs = lambda t, cp=cp, n=n: float((scored(t)-cp)@n)
        hr = lambda t, cp=cp, n=n: float((rend(t)-cp)@n)
        t_lo = cs[i-1].t_end if i else c.t-60.0
        t_hi = cs[i+1].t if i+1 < len(cs) else c.t+10.0
        t_apex, h_apex = _apex_before(hs, c.t, t_lo)
        t_rise = _rise_start(hs, t_apex, t_lo)
        hold = _hold(scored, t_apex, t_lo, c.t)
        vm = deriv(rend, c.t, -1); vp = deriv(rend, c.t, +1)
        vin_n = float(vm@n)
        fl = _float(rend, n, c.t, t_hi)
        # 10b: the head's world path over [t_apex, t_i]
        sag = side = None; chord = 0.0
        if c.t-t_apex > 1e-6:
            ts = np.linspace(t_apex, c.t, 101); P = np.array([scored(t) for t in ts])
            ch = P[-1]-P[0]; chord = float(np.linalg.norm(ch))
            if chord > 1e-9:
                u = ch/chord; rel = P-P[0]; perp = rel-np.outer(rel@u, u)
                d = np.linalg.norm(perp, axis=1); k = int(np.argmax(d)); sag = float(d[k])/chord
                if d[k] > 1e-6:
                    pin = _pin(S, aid, ts[k]); proj = P[0]+(rel[k]@u)*u
                    side = 1 if (pin-proj)@perp[k] < 0 else -1      # +1: concave toward the pin (an arc about it)
                else: side = 0
        pa = rig.pose(aid, t_apex); pi = rig.pose(aid, c.t)
        out.append(dict(
            c=c, t=c.t, t_apex=t_apex, h_apex=h_apex, T_down=c.t-t_apex, t_rise=t_rise, hold=hold,
            v_minus=vm, v_plus=vp, v_in=-vin_n, vmag=float(np.linalg.norm(vm)),
            e=(-float(vp@n)/vin_n) if vin_n < 0 else None,
            ang_in=(math.degrees(math.acos(np.clip(-vm@n/np.linalg.norm(vm), -1, 1))) if np.linalg.norm(vm) > 1e-9 else None),
            float=fl, t_up=fl['t_up'], h_up=hr(fl['t_up']),
            phi=abs(math.degrees(rig.head_angle(aid, t_apex)-rig.head_angle(aid, c.t))),
            sag=sag, chord=chord, side=side, elbow=abs(_elbow_deg(pa)-_elbow_deg(pi))))
    cache[aid] = out
    return out

def _none(n, name, aid, note):
    return Result(n, name, aid, {}, None, note)

def _vacuous(n, name, aid, note, **value):
    """The arm has nothing of this kind to measure, and never will on this
    score (no accent at tempo on the bells, no IOI > 1 s...): the target holds
    vacuously. Not n/a, which is for what does not exist YET — the gate fails
    n/a in scope, and must not fail on what the music never asks for."""
    return Result(n, name, aid, dict(n=0, **value), True, note)

# ---- 7 impact -----------------------------------------------------------------

def r7(S):
    """v_in = -v(t_i-)·n of the rendered face, one-sided at 1e-5 s. Per arm
    every v_in in 1.5-4.0 m/s (mallets) / 1.5-3.0 (hammer); dynamics:
    Spearman(v_in, a') >= 0.9 and v_in(a' max)/v_in(a' min) >= 1.5, the means
    over the arm's contacts at its own largest and smallest a'; an arm whose a'
    is constant (or None) is held to CV(v_in) <= 5 % instead."""
    out = []
    for aid in struck_arms(S):
        st = strokes(S, aid)
        if not st: out.append(_none(7, '7 speed', aid, 'no contacts')); continue
        lo, hi = (1.5, 3.0) if S.kind(aid) == 'hammer' else (1.5, 4.0)
        v = np.array([s['v_in'] for s in st])
        val = dict(v_in=_st(v, 3), out_of_range=int(np.sum((v < lo) | (v > hi))))
        if S.kind(aid) == 'hammer': val['abs_v'] = _st([s['vmag'] for s in st], 3)
        out.append(Result(7, '7 speed', aid, val, bool(np.all((v >= lo) & (v <= hi))),
                          f'target {lo}-{hi} m/s'+('; abs_v is |v| (the head swings across n)' if S.kind(aid) == 'hammer' else '')))
        a = [s['c'].a for s in st]
        have = [(s['v_in'], ai) for s, ai in zip(st, a) if ai is not None]
        if len(have) >= 2 and np.ptp([x[1] for x in have]) > 1e-9:
            va, aa = np.array([x[0] for x in have]), np.round(np.array([x[1] for x in have]), 6)
            rho = _rho(va, aa) if len(have) >= 3 else None
            ratio = float(va[aa == aa.max()].mean()/max(va[aa == aa.min()].mean(), 1e-12))
            ok = rho is not None and rho >= .9 and ratio >= 1.5
            note = '' if rho is not None else "fewer than 3 notes with a'" if len(have) < 3 else "v_in constant: no rank against a'"
            out.append(Result(7, '7 dynamics', aid, dict(rho=rho, ratio=_f(ratio, 3), n=len(have)), ok, note))
        else:
            cv = float(np.std(v)/max(np.mean(v), 1e-12))
            out.append(Result(7, '7 dynamics', aid, dict(cv=_f(cv, 4), n=len(v)), cv <= .05, "flat-amp arm: CV <= 5 %"))
    return out

# ---- 8 rebound and float -------------------------------------------------------

def r8(S):
    """e = -(v+·n)/(v-·n) on the rendered face. The float is the upstroke on
    the rendered face over [t_i + 5 ms, t_up] (t_up: where it stops rising):
    upward speed non-increasing and a·n in [-1.5 g, -0.5 g] at every 1 ms
    sample; an empty upstroke (nothing rises) fails. Float time: t_up - t_i >=
    0.5·(IOI - T_down) with IOI and T_down the NEXT note's (the float leads to
    it). IOI > 1 s (and the last note): the first apex h(t_up) =
    (e·v_in)^2/(2·a_float) +- 10 %, a_float the mean deceleration over the
    float. Apex vs the declared prep function h(a', IOI) +- 1 cm (and the
    park at h after a bounce loop) needs Declared.prep: n/a until declared."""
    out = []
    for aid in struck_arms(S):
        st = strokes(S, aid)
        if not st: out.append(_none(8, '8 e', aid, 'no contacts')); continue
        e = [s['e'] for s in st]
        ok = all(x is not None and .3 <= x <= .8 for x in e)
        out.append(Result(8, '8 e', aid, dict(e=_st(e, 3)), ok, 'target 0.3-0.8'))
        # the float
        bad = 0; amin, amax, gain, empty = [], [], [], 0
        for s in st:
            fl = s['float']
            if fl['v'].size == 0: bad += 1; empty += 1; continue
            g = float(np.max(np.diff(fl['v']))) if fl['v'].size > 1 else 0.0
            a = fl['a']/G
            amin.append(float(a.min())); amax.append(float(a.max())); gain.append(max(g, 0.0))
            if g > 1e-6 or a.min() < -1.5 or a.max() > -.5: bad += 1
        out.append(Result(8, '8 float', aid, dict(bad=bad, n=len(st), no_rise=empty, a_min_g=_f(min(amin) if amin else None, 1),
                                                  a_max_g=_f(max(amax) if amax else None, 1),
                                                  speed_gain=_f(max(gain) if gain else None, 3),
                                                  rise_ms=_st([(s['t_up']-s['t'])*1e3 for s in st], 1)),
                          bad == 0, 'speed non-increasing, a.n in [-1.5 g, -0.5 g] on [t+5 ms, t_up]'))
        # the float's duration against the next note's window. Judged where
        # the float leads to the next note's apex (IOI <= 1 s). Above 1 s the
        # goal makes the first apex ballistic ((e v_in)^2 / 2 a_float, the
        # bounce rule below), which at e <= 0.8, v_in <= 4 m/s and a_float >=
        # 0.5 g comes within 0.65 s: it cannot fill half of a 2-9 s window, so
        # those ratios are reported (ioi_gt1) and not judged.
        ratios, long_ = [], []
        for i, s in enumerate(st[:-1]):
            nxt = st[i+1]; ioi = s['c'].ioi_next; need = .5*(ioi-nxt['T_down'])
            r = (s['t_up']-s['t'])/need if need > 0 else math.inf
            (ratios if ioi <= FLOAT_IOI+1e-9 else long_).append(r)
        if ratios:
            r = np.array(ratios)
            out.append(Result(8, '8 float time', aid, dict(ratio=_st(r, 3), short=int(np.sum(r < 1)), ioi_gt1=_st(long_, 3)),
                              bool(np.all(r >= 1)),
                              '(t_up - t_i) / 0.5(IOI - T_down) of the next note, IOI <= 1 s; target >= 1'))
        else: out.append(_vacuous(8, '8 float time', aid, 'no next note within IOI <= 1 s (a free bounce loop instead)',
                                  ioi_gt1=_st(long_, 3)))
        # the bounce loop after IOI > 1 s
        loose = [s for s in st if s["c"].ioi_next > FLOAT_IOI+1e-9]
        rr = []
        for s in loose:
            fl = s['float']
            if fl['v'].size == 0 or s['e'] is None: rr.append(math.inf); continue
            span = s['t_up']-fl['t'][0]
            a_fl = (fl['v'][0]-float(deriv(face_fn(S, aid), s['t_up'], -1)@s['c'].normal))/span if span > 0 else 0.0
            pred = (s['e']*s['v_in'])**2/(2*a_fl) if a_fl > 0 else 0.0
            rr.append(s['h_up']/pred if pred > 1e-6 else math.inf)      # no rebound: nothing to predict
        if loose:
            ok = all(abs(x-1) <= .1 for x in rr)
            fin = [x for x in rr if math.isfinite(x)]
            out.append(Result(8, '8 bounce apex', aid, dict(n=len(loose), measured_over_ballistic=_st(fin, 2),
                                                           undefined=len(rr)-len(fin),
                                                           apex_m=_st([s['h_up'] for s in loose], 3)), ok,
                              'IOI > 1 s: first apex = (e v_in)^2/(2 a_float) +- 10 %'))
        else: out.append(_vacuous(8, '8 bounce apex', aid, 'no contact followed by IOI > 1 s'))
        # apex against the declared prep function
        prep = S.declared(aid).prep
        tight = [s for s in st[:-1] if s["c"].ioi_next <= FLOAT_IOI+1e-9]
        val = dict(apex_m=_st([s['h_up'] for s in tight], 3), park_m=_st([st[i+1]['h_apex'] for i, s in enumerate(st[:-1]) if s["c"].ioi_next > FLOAT_IOI+1e-9], 3))
        if prep is None:
            out.append(Result(8, '8 apex vs h', aid, val, None, 'prep function h(a\', IOI) not declared (Declared.prep is None)'))
        else:
            err = []
            for i, s in enumerate(st[:-1]):
                nx = st[i+1]; a1 = nx['c'].a if nx['c'].a is not None else 1.0
                want = float(prep(a1, s['c'].ioi_next))
                err.append(abs((s['h_up'] if s["c"].ioi_next <= FLOAT_IOI+1e-9 else nx['h_apex'])-want))
            val['err_m'] = _st(err, 4)
            out.append(Result(8, '8 apex vs h', aid, val, (not err) or max(err) <= .01, 'apex (IOI <= 1 s) or park (IOI > 1 s) = h +- 1 cm'))
    return out

# ---- 10 hammer arc -------------------------------------------------------------

def r10(S):
    """Per stroke [t_apex, t_i]: (a) the shaft's rotation |phi(t_apex) - phi(t_i)|
    — phi is Rig.head_angle (the hammer's hinged head; a mallet's shaft is
    rigid today, so 0) — >= 20 deg, >= 35 deg when the note's IOI >= 0.7 s (the
    hammer >= 20 deg); (b) the scored face's path: sagitta/chord >= 0.05 and
    concave toward the pin (the arc about it: the bulge points away from the
    pin; the pin is the hammer's hinge, or for a mallet the wrist pin, where
    the M5 hinge goes); (c) the angle between v(t_i-) of the rendered face and
    -n <= 20 deg; (d) the change of the elbow's interior angle (Rig.pose) from
    t_apex to t_i >= 5 deg."""
    out = []
    for aid in struck_arms(S):
        st = strokes(S, aid)
        if not st:
            for nm in ('10a rotation', '10b arc', '10c normal', '10d elbow'): out.append(_none(10, nm, aid, 'no contacts'))
            continue
        ham = S.kind(aid) == 'hammer'
        need = [20.0 if ham or s['c'].ioi < .7 else 35.0 for s in st]
        phi = [s['phi'] for s in st]
        out.append(Result(10, '10a rotation', aid, dict(deg=_st(phi, 1), short=int(sum(p < q for p, q in zip(phi, need)))),
                          all(p >= q for p, q in zip(phi, need)),
                          'no hinge: the shaft is rigid (0 deg)' if not ham else 'hinged head (Rig.head_angle)'))
        sag = [s['sag'] if s['sag'] is not None else 0.0 for s in st]
        toward = sum(1 for s in st if s['side'] == 1)
        out.append(Result(10, '10b arc', aid, dict(sagitta_chord=_st(sag, 4), toward_pin=toward, n=len(st),
                                                   chord_m=_st([s['chord'] for s in st], 3)),
                          all(x >= .05 for x in sag) and toward == len(st), 'sagitta/chord >= 0.05, concave toward the pin'))
        ang = [s['ang_in'] for s in st]
        out.append(Result(10, '10c normal', aid, dict(deg=_st(ang, 1)), all(a is not None and a <= 20 for a in ang),
                          'angle of v(t_i-) to -n'))
        el = [s['elbow'] for s in st]
        span = S.poses(aid, 'frames')
        ea = [_elbow_deg(dict(root=r, elbow=e, wrist=w)) for r, e, w in zip(span['root'], span['elbow'], span['wrist'])]
        out.append(Result(10, '10d elbow', aid, dict(deg=_st(el, 2), piece_span_deg=_f(max(ea)-min(ea), 1)),
                          all(x >= 5 for x in el), 'interior-angle change t_apex -> t_i; piece_span over the 30 fps frames'))
    return out

# ---- 11 contact frame ----------------------------------------------------------

def r11(S):
    """|p(round(30 t)/30) - c| of the rendered face for every struck contact
    (round half up, as the film's frame index); median <= 25 mm, p90 <= 55,
    max <= 75."""
    out = []
    for aid in struck_arms(S):
        cs = S.contacts(aid)
        if not cs: out.append(_none(11, '11 contact frame', aid, 'no contacts')); continue
        f = face_fn(S, aid, True)
        d = np.array([np.linalg.norm(f(math.floor(c.t*FPS+.5)/FPS)-c.point) for c in cs])*1e3
        med, p90, mx = float(np.median(d)), float(np.percentile(d, 90)), float(d.max())
        out.append(Result(11, '11 contact frame', aid, dict(median_mm=_f(med, 1), p90_mm=_f(p90, 1), max_mm=_f(mx, 1), n=len(d)),
                          med <= 25 and p90 <= 55 and mx <= 75))
    return out

# ---- 19 ratchet ----------------------------------------------------------------

def _carriage_x(S, aid, rendered=True):
    """t -> the carriage's x. rendered: Rig.pose root x (with the rings the
    tip carries). scored: its law without rings, Rig.path_at x — the carriage x
    IS the tool x today (rig.py:409); once Rig.pose stops forcing that, this
    must read the carriage's own scored x."""
    rig = S.rig
    if rendered: return lambda t: float(rig.pose(aid, t)['root'][0])
    return lambda t: float(rig.path_at(aid, t)[0])

def _peak_acc(S, aid, t0, t1, knots):
    """max |x''| of the carriage's law (scored x: rings are ruler 20's) on a
    1 ms grid in (t0, t1), one-sided forward stencils, skipping any whose 4H
    span holds a declared knot (an impulse there is declared, not an
    acceleration)."""
    if t1-t0 <= 2*DT: return 0.0
    f = _carriage_x(S, aid, False); best = 0.0
    for t in np.arange(t0+DT/2, t1-4*H, DT):
        j = np.searchsorted(knots, t, side='right')
        if j < len(knots) and knots[j] <= t+4*H+1e-12: continue
        best = max(best, abs(float(deriv(f, t, +1, 2))))
    return best

def _hurried_pairs(S, aid):
    """The notation's hurried travels, per consecutive contact pair (i-1, i)
    whose carriage moves d = |x_i - x_{i-1}| >= 1 mm (contact x): hurried when
    the 3-4-5 law's minimum time at 3 g and 1.0 E a frame,
    max(sqrt(5.7735 d / 3 g), 1.875 d / (30 E)), exceeds the window t_i -
    t_{i-1}; E = the head's extent along x. Returns ({i: (d, window, T_min)}
    for the hurried, number of moving pairs)."""
    cs = S.contacts(aid); E = E_HEAD[S.kind(aid)]; hur = {}; moves = 0
    for i in range(1, len(cs)):
        d = abs(float(cs[i].point[0]-cs[i-1].point[0])); w = cs[i].t-cs[i-1].t
        if d < 1e-3: continue
        moves += 1
        tmin = max(math.sqrt(5.7735*d/(3*G)), 1.875*d/(FPS*E))
        if tmin > w: hur[i] = (d, w, tmin)
    return hur, moves

def _travels(S, aid):
    """The arm's declared travel segments that move the carriage (|dx| >= 1 mm
    on the scored path), each with its click knots, its contact-to-contact
    window (from the contact before it, or the piece's start, to the contact
    after it, or the piece's end) and its regime: 'stepped' when each tooth
    can take >= STEP_FRAMES frames of that window, 'freewheel' otherwise
    (ruler 19: "Stepped travel (each step can take >= 3 frames)"; Q4). The
    regime is the music's (contact times and places), not the law the rig
    chose: a fast travel the rig steps is a freewheel travel with the wrong
    law."""
    rig = S.rig; d = S.declared(aid); cs = S.contacts(aid)
    clicks = sorted(k.t for k in d.knots if k.kind == 'click')
    hur, _ = _hurried_pairs(S, aid)
    out = []
    for sg in d.segments:
        if sg.tag != 'travel' or not math.isfinite(sg.t1) or sg.t1-sg.t0 < 1e-6: continue
        x0 = float(rig.path_at(aid, sg.t0)[0]); x1 = float(rig.path_at(aid, sg.t1)[0])
        if abs(x1-x0) < 1e-3: continue
        ks = [t for t in clicks if sg.t0-1e-9 <= t < sg.t1-1e-9]
        prev = [c for c in cs if c.t <= sg.t0+1e-9]; nxt = [c for c in cs if c.t >= sg.t1-1e-9]
        prev = prev[-1] if prev else None; nxt = nxt[0] if nxt else None
        lo = prev.t if prev else 0.0; hi = nxt.t if nxt else max(S.total, sg.t1)
        teeth = max(1, int(math.floor(abs(x1-x0)/R.PITCH+.5)))
        window = max(hi-lo, sg.t1-sg.t0)
        out.append(dict(t0=sg.t0, t1=sg.t1, law=sg.law, dx=x1-x0, x0=x0, clicks=ks, teeth=teeth, window=window,
                        prev=prev, nxt=nxt, regime='stepped' if window/teeth >= STEP_FRAMES/FPS-1e-9 else 'freewheel',
                        hurried=prev is not None and nxt is not None and nxt.i == prev.i+1 and nxt.i in hur))
    return out

def _tpc(travels):
    """Teeth per click over the travels' clicks: mean (per click) and max."""
    v = [tv['teeth']/max(1, len(tv['clicks'])) for tv in travels for _ in range(max(1, len(tv['clicks'])))]
    return dict(mean=_f(np.mean(v), 2), max=_f(np.max(v), 2)) if v else None

def r19(S):
    """Ratchet arms (mallet, hammer). Travels are the declared 'travel'
    segments that move the carriage; each is STEPPED or FREEWHEEL by the time
    its contact-to-contact window leaves a tooth (>= 3 frames: stepped), and is
    held to that regime's targets whatever law the rig gave it.
    Stepped: the per-frame carriage |dx| (Rig.pose root x, the 30 fps frames
    overlapping the travel) <= 1 tooth (PITCH, 47 mm), and every step's detent
    dwell >= 0.5, a step being a declared click's period (the whole travel if
    it declares no clicks) and its dwell the share of it the carriage's law
    (scored x: the blow's recoil bus is ruler 20's) spends within 0.1 tooth
    (the pawl's play) of the step's detent, its x at the period's end.
    Freewheel: a smooth law (SMOOTH_LAWS), peak |x''| <= 3 g (5 g on a
    counted hurried travel), x' = x'' = 0 at the bounding contacts (1e-3 m/s,
    0.05 m/s^2, one-sided toward the travel), monotone, one declared click
    per tooth; all on the carriage's law (scored x). Pawl: on freewheel
    travels, each click's declared pawl state (Knot.extra['pawl'], 'drop' or
    'ride') against the tooth rate |x'|/PITCH there (drop below 15 teeth/s,
    ride above); n/a while no click declares one. Hurried: _hurried_pairs;
    each one's peak carriage |x''| over its window <= 5 g and rho = max
    per-frame carriage |dx| / E over its frames <= 1.5; the count <= today's
    (frozen in TODAY_HURRIED) until M8, <= 6 at the end."""
    out = []; totals = {}
    for aid in struck_arms(S):
        kind = S.kind(aid); E = E_HEAD[kind]; rig = S.rig
        d = S.declared(aid); knots = np.array(sorted(k.t for k in d.knots))
        trav = _travels(S, aid)
        fr = S.poses(aid, 'frames'); tf = fr['t']; xr = fr['root'][:, 0]
        cs_x = _carriage_x(S, aid, False)
        cs = S.contacts(aid)
        # -- stepped
        stepped = [tv for tv in trav if tv['regime'] == 'stepped']
        if stepped:
            dwell, short, fdx, peak = [], 0, [], 0.0
            for tv in stepped:
                starts = tv['clicks'] or [tv['t0']]
                ends = starts[1:]+[tv['t1']]
                for a, b in zip(starts, ends):
                    if b-a < STEP_FRAMES/FPS-1e-9: short += 1
                    det = float(rig.path_at(aid, b-1e-9)[0])
                    ts = np.arange(a, b, DT)
                    dwell.append(float(np.mean([abs(cs_x(t)-det) <= DETENT_TOL+1e-9 for t in ts])) if len(ts) else 0.0)
                k = np.nonzero((tf > tv['t0']) & (tf-1/FPS < tv['t1']))[0]
                k = k[k > 0]
                fdx.extend(np.abs(xr[k]-xr[k-1]).tolist())
                peak = max(peak, _peak_acc(S, aid, tv['t0'], tv['t1'], knots))
            fdx = np.array(fdx); dw = np.array(dwell)
            out.append(Result(19, '19 stepped', aid, dict(
                travels=len(stepped), steps=len(dw), teeth_per_click=_tpc(stepped),
                frame_dx_m=_f(fdx.max() if fdx.size else 0.0, 4), frames_over_tooth=int(np.sum(fdx > R.PITCH+1e-9)),
                dwell=_st(dw, 2), steps_dwell_lt_half=int(np.sum(dw < .5)), steps_under_3_frames=short,
                peak_acc_g=_f(peak/G, 1), laws=sorted({tv['law'] for tv in stepped})),
                bool((fdx.size == 0 or fdx.max() <= R.PITCH+1e-9) and np.all(dw >= .5)),
                'travels whose window leaves >= 3 frames a tooth: <= 1 tooth (47 mm) a frame; dwell (within 0.1 tooth '
                'of the detent) >= 0.5 of every step'))
        else: out.append(_vacuous(19, '19 stepped', aid, 'no travel here leaves >= 3 frames a tooth'))
        # -- freewheel
        free = [tv for tv in trav if tv['regime'] == 'freewheel']
        if free:
            bad, peaks, ends, n_law, n_g, n_end, n_mono, n_click = 0, [], [], 0, 0, 0, 0, 0
            for tv in free:
                pk = _peak_acc(S, aid, tv['t0'], tv['t1'], knots); peaks.append(pk/G)
                e_bad = False
                for c, side in ((tv['prev'], +1), (tv['nxt'], -1)):
                    if c is None: continue
                    v = abs(float(deriv(cs_x, c.t, side, 1))); a = abs(float(deriv(cs_x, c.t, side, 2)))
                    ends.append(v); e_bad |= v > 1e-3 or a > .05
                xs = np.array([cs_x(t) for t in np.r_[np.arange(tv['t0'], tv['t1'], DT), tv['t1']]])
                mono = bool(np.all(np.diff(xs)*np.sign(tv['dx']) >= -1e-9))
                law_ok = tv['law'] in SMOOTH_LAWS; g_ok = pk <= (A_HURRIED if tv['hurried'] else A_STOP)
                click_ok = len(tv['clicks']) == tv['teeth']
                n_law += not law_ok; n_g += not g_ok; n_end += e_bad; n_mono += not mono; n_click += not click_ok
                bad += not (law_ok and g_ok and not e_bad and mono and click_ok)
            out.append(Result(19, '19 freewheel', aid, dict(
                travels=len(free), bad=bad, hurried=sum(tv['hurried'] for tv in free), laws=sorted({tv['law'] for tv in free}),
                not_smooth=n_law, over_g=n_g, ends_moving=n_end, non_monotone=n_mono, click_per_tooth_misses=n_click,
                teeth_per_click=_tpc(free), peak_g=_st(peaks, 1), end_speed=_st(ends, 4)), bad == 0,
                'travels whose window leaves < 3 frames a tooth: a smooth law, <= 3 g (5 g hurried), '
                "x' = x'' = 0 at contacts, monotone, a click per tooth"))
        else: out.append(_vacuous(19, '19 freewheel', aid, 'no travel here leaves < 3 frames a tooth'))
        # -- pawl (freewheel travels)
        fk = [k for k in d.knots if k.kind == 'click' and any(tv['t0']-1e-9 <= k.t < tv['t1']-1e-9 for tv in free)]
        if not free: out.append(_vacuous(19, '19 pawl', aid, 'no freewheel travel'))
        elif not any('pawl' in k.extra for k in fk):
            out.append(_none(19, '19 pawl', aid, 'no pawl state declared (the 6c326b5 rig has no pawl ride/drop: '
                                                 'its clicks are the carriage itself stepping)'))
        else:
            miss = 0
            for k in fk:
                rate = abs(float(deriv(cs_x, k.t, +1, 1)))/R.PITCH
                miss += k.extra.get('pawl') != ('drop' if rate < PAWL_RIDE else 'ride')
            out.append(Result(19, '19 pawl', aid, dict(clicks=len(fk), misses=miss), miss == 0,
                              'drops into every tooth below 15 teeth/s, rides the tips above'))
        # -- hurried
        hur, moves = _hurried_pairs(S, aid)
        rows = []
        for i in sorted(hur):
            a, b = cs[i-1].t, cs[i].t
            pk = _peak_acc(S, aid, a, b, knots)
            k = np.nonzero((tf > a) & (tf-1/FPS < b))[0]; k = k[k > 0]
            rho = float(np.max(np.abs(xr[k]-xr[k-1]))/E) if k.size else 0.0
            rows.append((cs[i].t, pk/G, rho))
        # the 6c326b5 rig's own sense of hurried, for the record: a travel
        # given less than motion_timing.travel_s (a click a tooth at CLICK_S)
        under_want = sum(1 for s in rig.sched[aid] if s['moving'] and s['approach']-s['go'] < s['want']-1e-9)
        today = TODAY_HURRIED.get(S.asset, {}).get(aid)
        cnt = len(rows); ceiling = today if today is not None else HURRIED_END
        ok = cnt <= ceiling and all(g <= 5 and r <= 1.5 for _, g, r in rows)
        totals.setdefault(kind, [0, 0]); totals[kind][0] += cnt; totals[kind][1] += ceiling
        out.append(Result(19, '19 hurried', aid, dict(
            count=cnt, today=today, moves=moves, at=[_f(t, 3) for t, _, _ in rows][:8],
            peak_g=_f(max([g for _, g, _ in rows], default=0.0), 1), rho=_f(max([r for _, _, r in rows], default=0.0), 2),
            under_want=under_want, E=_f(E, 4)), ok,
            f'count <= {ceiling} (today\'s; <= {HURRIED_END} at the end), each <= 5 g and rho <= 1.5'))
    for kind, (cnt, ceil) in totals.items():
        out.append(Result(19, '19 hurried total', kind, dict(count=cnt, today=ceil, end_ok=cnt <= HURRIED_END), cnt <= ceil,
                          f'sum over {kind} arms; <= {HURRIED_END} at the end'))
    return out

# ---- 21 intent -----------------------------------------------------------------

def r21(S):
    """The apex before note i is h(t_apex) on the scored face (ruler 3's apex,
    relative to c_i along n). (1) Spearman(apex, a' of note i) >= 0.9 per arm
    (vacuous when fewer than 3 notes carry a' or a' does not vary). (2) Height against tempo: among
    notes with equal a', no faster note (shorter IOI_i) is prepared more than
    1 mm higher than a slower one. (3) Holds: a hold of >= 3 frames at the
    apex after every gap >= 0.8 s (phrase starts, tolls, bells) and after no
    shorter gap. (4) Accents at tempo — IOI_i < 0.8 s (the notes (3) allows
    no hold before, in the flow) and amp >= the arm's previous amp + 0.15
    (the tune's beat-1/3 0.85 over 0.6; the runs' 0.05 steps are no accents)
    — begin their rise (the wind-up W_i's start) by t_{i-1} + 0.5·IOI_i."""
    out = []
    for aid in struck_arms(S):
        st = strokes(S, aid)
        if not st:
            for nm in ("21 height vs a'", '21 height vs tempo', '21 holds', '21 accents'): out.append(_none(21, nm, aid, 'no contacts'))
            continue
        h = np.array([s['h_apex'] for s in st]); a = [s['c'].a for s in st]
        have = [(x, ai) for x, ai in zip(h, a) if ai is not None]
        if len(have) >= 3 and np.ptp([y for _, y in have]) > 1e-9:
            rho = _rho([x for x, _ in have], [y for _, y in have])
            note = '' if rho is not None else "apex height constant: no rank against a'"
            out.append(Result(21, "21 height vs a'", aid, dict(rho=rho, apex_m=_st(h, 3), n=len(have)),
                              rho is not None and rho >= .9, note))
        else:
            out.append(_vacuous(21, "21 height vs a'", aid, "fewer than 3 notes with a', or a' constant on this arm", apex_m=_st(h, 3)))
        # height against tempo at equal a'
        groups = {}
        for s in st:
            key = round(s['c'].a, 6) if s['c'].a is not None else None
            groups.setdefault(key, []).append((s['c'].ioi, s['h_apex']))
        viol = 0; worst = 0.0; pairs = 0
        for g in groups.values():
            for i1, h1 in g:
                for i2, h2 in g:
                    if i1 < i2-1e-6:
                        pairs += 1
                        if h1 > h2+1e-3: viol += 1; worst = max(worst, h1-h2)
        out.append(Result(21, '21 height vs tempo', aid, dict(violations=viol, pairs=pairs, worst_m=_f(worst, 4)), viol == 0,
                          'flat: heights do not vary at all' if np.ptp(h) < 1e-3 else ''))
        # holds
        long_ = [s for s in st if s['c'].gap >= HOLD_GAP]; short_ = [s for s in st if s['c'].gap < HOLD_GAP]
        held = [s for s in st if s['hold'] >= 3/FPS-1e-9]
        missing = sum(1 for s in long_ if s['hold'] < 3/FPS-1e-9); at_tempo = sum(1 for s in short_ if s['hold'] >= 3/FPS-1e-9)
        out.append(Result(21, '21 holds', aid, dict(holds=len(held), at=[_f(s['t'], 2) for s in held][:6], long_gaps=len(long_),
                                                    missing=missing, at_short_gap=at_tempo, hold_ms=_st([s['hold']*1e3 for s in st], 0)),
                          missing == 0 and at_tempo == 0, '>= 3 frames within 1 mm of the apex, after every gap >= 0.8 s and no other'))
        # accents at tempo
        acc = []
        for i in range(1, len(st)):
            c, p = st[i]['c'], st[i-1]['c']
            if c.ioi < HOLD_GAP and c.amp >= p.amp+ACCENT_JUMP-1e-9:
                acc.append((st[i]['t_rise']-p.t)/c.ioi)
        if acc:
            r = np.array(acc)
            out.append(Result(21, '21 accents', aid, dict(n=len(r), late=int(np.sum(r > .5)), rise_at=_st(r, 3)), bool(np.all(r <= .5)),
                              'rise start - t_{i-1}, in IOIs; target <= 0.5'))
        else: out.append(_vacuous(21, '21 accents', aid, 'no accent at tempo on this arm'))
    return out

RULERS = {7: r7, 8: r8, 10: r10, 11: r11, 19: r19, 21: r21}

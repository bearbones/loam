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

The mallets (kind 'mallet', PLAYERS M1) declare their own stroke
(formlab/stroke.py through Rig.declared; DESIGN §7), and every mallet branch
below keys on the kind — the hinged hammer keeps the M0 reading, number for
number, until M5:
  apex     t_apex, h(t_apex) and the rise start t_w are r_motion.prep's (ruler
           3's, the declared apex hold skipped), so 3, 4, 8, 9, 10 and 21 share
           one apex and one wind-up (§7.1).
  hold     the declared head-channel 'hold' run ending at t_apex (+-2 ms),
           still in 3D within 1 mm (the time _hold measures, bounded to that
           run); 0 where none is declared (§7.6).
  8        the rebound-led float rule at IOI_next <= stroke.FLOAT_IOI (0.6 s),
           the bounce loop above it (§7.2).
  10b      in the plane perpendicular to the declared pin axis (y-z), against
           the declared `pin` of the note's 'stroke' segment (§7.3).
  19       travels are the declared carriage 'travel' segments grouped by
           extra['travel'], their regime extra['regime'] (§7.5).
  21       Spearman within IOI classes; accents from the declared wind-up (§7.6).

Definitions where the goal leaves a choice are stated at each ruler below.
"""
import math
import numpy as np
from players import core
from players.core import Result, deriv, spearman, FPS, G, H
from formlab import rig as R
from formlab import stroke as ST       # the mallet's declared stroke (numpy-only); ST.motion_timing is loam/motion_timing

KINDS = ('mallet', 'hammer')
DT = 1e-3            # s: scan step
FINE = 50            # refinement points per scan step (20 us)
TOL = 1e-9           # m: h "changes" over a scan step when it moves more than this
HOLD_R = 1e-3        # m: a hold keeps the face within this of its apex position
FLOAT_SKIP = .005    # s: the float is judged from t_i + 5 ms (ruler 8)
V_TURN = 1e-6        # m/s: the face "stops rising" at v.n <= this (a still rest's 5-point v is +-1e-13, not 0)
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
assert PAWL_RIDE == ST.PAWL_RIDE, 'ruler 19 and formlab.stroke disagree on PAWL_RIDE'
FLOAT_IOI = 1.0      # s: ruler 8's float leads to the next apex at IOI <= 1 s; above it is a free bounce loop
# Per kind (DESIGN §7.2): the mallet's rebound-led float reaches the next apex
# only at IOI <= 0.6 s (a ballistic float at >= 0.5 g ending at the next
# downstroke rises >= 0.28 m past IOI 0.59 s); above it the bounce loop. The
# hammer keeps the M0 value until M5.
FLOAT_IOI_KIND = dict(mallet=ST.FLOAT_IOI, hammer=FLOAT_IOI)
APEX_TOL = 2e-3      # s: a declared hold "ends at t_apex" within this (ruler 3's, r_motion)
IOI_CLASS = .05      # ruler 21: IOIs within 5 % are one tempo class
# Ruler 19's hurried-travel ceiling "<= today's count until M8": today's count
# (the 6c326b5 motion), measured by this ruler at M0 and frozen here.
TODAY_HURRIED = {'chamber': {'bars_arm0': 12, 'bars_arm1': 2},
                 'expanded': {'bars_arm0': 12, 'bars_arm1': 2, 'bells_arm0': 0, 'bells_arm1': 0, 'blocks_arm0': 16}}
HURRIED_END = 6
# Ruler 8's '8 rise' (the lead's M1 amendment after review WF-E): a mallet's
# rise, from each contact to the next note's t_apex (and the coda after the
# last), never hitches. On the scored face h(t) at RISE_DT, split into up-runs
# and down-runs with HITCH_REV hysteresis (a bob smaller than that does not end
# a run). Inside an up-run the upward speed may sag but never below HITCH_K of
# the lesser of its peaks before and after (a valley lower than that reads as
# up-pause-up), unless the valley holds a still stretch (|h'| < HITCH_V) of at
# least REST_MIN: a deliberate rest (a park), not a hitch.
RISE_DT = 1/240
HITCH_V = .05        # m/s: still (1.7 mm a 30 fps frame)
HITCH_REV = .01      # m: a reversal this deep ends a run (the catch's 1 mm bob does not)
HITCH_K = .5
REST_MIN = .25       # s: 7.5 frames
assert (REST_MIN, HITCH_V, FLOAT_SKIP) == (ST.REST_MIN, ST.STILL_V, ST.RISE_SKIP), \
    "ruler 8 and formlab.stroke disagree on REST_MIN / HITCH_V (STILL_V) / FLOAT_SKIP (RISE_SKIP)"
# Ruler 8's handover and catch (M1 A2, A11). A float judged only up to its
# declared end is one that hands over, still rising, to a DRIVEN segment: a
# rise (DRIVEN_RISE: the Dahl up-stroke, a flow, a coast, the coda's raise) or
# a CATCH (the arm takes the head at the top of its flight and brings it to
# rest). Any other declared end while rising is no handover: the float is
# judged to where the face turns. A catch begins once the float has shed
# CATCH_SHARE of its launch speed (the free flight carries >= 3/4 of the
# height), never reverses (upward speed non-increasing and >= 0), brakes no
# harder than the float band's 1.5 g, ends still, and rests at the ballistic
# apex (e v_in)^2 / (2 a_float) +- 10 % ('8 bounce apex', a_float the float's
# own mean deceleration to the catch). The shape decides, not the tag: a
# driven rise that brings the head to still (|h'| < HITCH_V for over a frame)
# more than HITCH_REV below the park it rises to (the next t_apex, or the
# coda's end) has caught it, and is judged as a catch ending there.
DRIVEN_RISE = ('wind-up', 'raise')
CATCH_TAG = 'catch'
CATCH_SHARE = .5
# '8 low rest' (M1 A11): a rebounding head never rests below its park while its
# carriage moves. Inside each rise window, a still head (|h'| < HITCH_V) more
# than HITCH_REV below the window's end height (the park the rise ends at)
# while the scored carriage moves (|x'| > X_MOVING) for longer than one frame
# is a head left waiting under a moving carriage. A head parked at the prep
# while the carriage positions under it (the first note, park-first holds) is
# ready, not waiting, and is allowed. A stepped carriage dwells between its
# steps (x' = 0) without having stopped travelling: a pause of at most DWELL_MAX
# with motion on both sides still counts as moving, so a wait is measured
# whole, not one step move at a time.
X_MOVING = .01       # m/s: 0.3 mm a frame
DWELL_MAX = ST.motion_timing.P_MAX   # s: the longest a step period lasts, so the longest dwell
assert (HITCH_REV, X_MOVING) == (ST.LOW_REV, ST.X_MOVING), \
    "ruler 8 and formlab.stroke disagree on HITCH_REV (LOW_REV) / X_MOVING"

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
    t_i + 5 ms until the face stops rising (v.n <= V_TURN), and the turning time t_up."""
    vn = lambda t: float(deriv(f, t, +1, 1)@n)
    t = t_i+FLOAT_SKIP; ts, vs, accs = [], [], []
    turned = False
    while t < t_hi:
        v = vn(t)
        if v <= V_TURN: turned = True; break
        ts.append(t); vs.append(v); accs.append(float(deriv(f, t, +1, 2)@n)); t += DT
    if not ts: t_up = min(t_i+FLOAT_SKIP, t_hi)
    elif not turned: t_up = t_hi
    else:
        lo, hi = ts[-1], t
        for _ in range(10):
            mid = .5*(lo+hi)
            if vn(mid) > V_TURN: lo = mid
            else: hi = mid
        t_up = hi
    return dict(t=np.array(ts), v=np.array(vs), a=np.array(accs), t_up=t_up, turned=turned)

def _up_runs(h):
    """[(i0, i1)] of the up-runs of the sampled h (from a low to the next high),
    with HITCH_REV hysteresis: a run ends once h comes HITCH_REV back from it."""
    runs = []; up = None; lo = hi = 0
    for i in range(1, len(h)):
        if up is None:
            if h[i] >= h[lo]+HITCH_REV: up = True; hi = i
            elif h[i] <= h[hi]-HITCH_REV: up = False; lo = i
            else:
                if h[i] < h[lo]: lo = i
                if h[i] > h[hi]: hi = i
        elif up:
            if h[i] > h[hi]: hi = i
            elif h[i] <= h[hi]-HITCH_REV: runs.append((lo, hi)); up = False; lo = i
        else:
            if h[i] < h[lo]: lo = i
            elif h[i] >= h[lo]+HITCH_REV: up = True; hi = i
    if up: runs.append((lo, hi))
    return runs

def _hitches(hf, a, b):
    """Ruler 8's '8 rise' on [a, b]: the hitches of h(t) (dicts t, ms, ratio, v,
    h) and the least valley ratio met. See HITCH_K."""
    ts = np.arange(a, b, RISE_DT)
    if len(ts) < 5: return [], 1.0
    h = np.array([hf(t) for t in ts]); v = np.gradient(h, ts)
    out = []; worst = 1.0
    for i0, i1 in _up_runs(h):
        if i1-i0 < 3: continue
        vr = v[i0:i1+1]
        pre = np.maximum.accumulate(vr); post = np.maximum.accumulate(vr[::-1])[::-1]
        den = np.minimum(pre, post)
        ratio = np.where(den > HITCH_V, vr/np.maximum(den, 1e-12), 1.0)
        worst = min(worst, float(ratio.min()))
        bad = ratio < HITCH_K
        k = 0
        while k < len(bad):
            if not bad[k]: k += 1; continue
            m = k
            while m+1 < len(bad) and bad[m+1]: m += 1
            # the valley [k, m]: a deliberate rest if it holds REST_MIN of stillness
            still = np.abs(vr[k:m+1]) < HITCH_V; run = best = 0
            for s in still:
                run = run+1 if s else 0; best = max(best, run)
            if best*RISE_DT < REST_MIN-1e-9:
                j = k+int(np.argmin(ratio[k:m+1]))
                out.append(dict(t=round(float(ts[i0+j]), 3), ms=round((m-k+1)*RISE_DT*1e3, 1),
                                ratio=round(float(ratio[j]), 3), v=round(float(vr[j]), 3), h=round(float(h[i0+j]), 4)))
            k = m+1
    return out, worst

def _float_end(heads, t_i):
    """(end, next) of the declared head 'float' leaving the contact t_i: its end
    time and the head segment that starts there (None if none), or None."""
    g = next((g for g in heads if g.tag == 'float' and abs(g.t0-t_i) <= 1e-6), None)
    if g is None: return None
    return g.t1, next((h for h in heads if h is not g and abs(h.t0-g.t1) <= 1e-9), None)

def _stops_short(h, t0, t1):
    """Where a rise handed over at t0 first comes to still (|h'| < HITCH_V for
    over a frame, at RISE_DT) more than HITCH_REV below its park h(t1): the
    start of that still stretch, or None if it reaches the park first."""
    if t1-t0 < 2*RISE_DT: return None
    ts = np.arange(t0, t1, RISE_DT); hh = np.array([h(t) for t in ts])
    still = (np.abs(np.gradient(hh, ts)) < HITCH_V) & (hh < h(t1)-HITCH_REV)
    k = 0
    while k < len(still):
        if not still[k]: k += 1; continue
        m = k
        while m+1 < len(still) and still[m+1]: m += 1
        if (m-k+1)*RISE_DT > 1/FPS+1e-9: return float(ts[k])
        k = m+1
    return None

def _elbow_deg(p):
    a = p['root']-p['elbow']; b = p['wrist']-p['elbow']
    return math.degrees(math.acos(np.clip(a@b/(np.linalg.norm(a)*np.linalg.norm(b)), -1, 1)))

def _pin(S, aid, t):
    """The pin the head swings about: the hammer's hinge (tool frame + head_l
    up, as formlab.clearance places it). A mallet declares its own virtual pin
    on each 'stroke' segment (_declared_pin, M1); this wrist-pin reading (the
    wrist sits straight above the head, so a true arc about the declared pin
    bulges AWAY from it and reads side -1) is kept only for a mallet that
    declares none (a rig before M1)."""
    rig = S.rig; p = rig.path_at(aid, t)
    if rig.hammer(aid): return p+np.array([0, R.HAMMER['head_l'], 0])
    return p+rig.wrist_offset(S.cfg(aid))

def _mallet(S, aid):
    """The M1 branch: a rigid mallet whose rig declares its own stroke."""
    return S.kind(aid) == 'mallet' and S.declared(aid).native

def _head_segments(S, aid):
    """A declaring mallet's head-channel segments in time order."""
    return sorted((g for g in S.declared(aid).segments if g.extra.get('channel') == 'head'), key=lambda g: g.t0)

def _run_before(heads, t, tags, tol=APEX_TOL):
    """The contiguous run of head segments with tag in `tags` whose last one
    ends at t (+- tol): (start of the run, its segments), or (None, [])."""
    j = next((k for k, g in enumerate(heads) if g.tag in tags and abs(g.t1-t) <= tol), None)
    if j is None: return None, []
    run = [heads[j]]
    while j > 0 and heads[j-1].tag in tags and abs(heads[j-1].t1-heads[j].t0) <= 1e-9:
        j -= 1; run.insert(0, heads[j])
    return run[0].t0, run

def _declared_pin(heads, t_i):
    """(pin, axis) of the declared 'stroke' segment ending at the contact t_i, or (None, None)."""
    g = next((g for g in heads if g.tag == 'stroke' and abs(g.t1-t_i) <= 1e-6 and 'pin' in g.extra), None)
    if g is None: return None, None
    a = np.asarray(g.extra.get('axis', (1.0, 0.0, 0.0)), float)
    return np.asarray(g.extra['pin'], float), a/np.linalg.norm(a)

def _arc_10b(P, pin=None, axis=None, pin_fn=None, ts=None):
    """Ruler 10b on a sampled path P (t_apex .. t_i): sagitta/chord and the side
    the bulge points relative to the pin (+1: away from it, an arc about it).
    With `axis`, P and the pin are first projected onto the plane
    perpendicular to it (the mallet's y-z: the carriage's x is the arc's
    axis, and an x still moving under the downstroke is not curvature)."""
    if axis is not None:
        P = P-np.outer(P@axis, axis); pin = pin-(pin@axis)*axis
    ch = P[-1]-P[0]; chord = float(np.linalg.norm(ch)); sag = side = None
    if chord > 1e-9:
        u = ch/chord; rel = P-P[0]; perp = rel-np.outer(rel@u, u)
        d = np.linalg.norm(perp, axis=1); k = int(np.argmax(d)); sag = float(d[k])/chord
        if d[k] > 1e-6:
            pk = pin if pin is not None else pin_fn(ts[k]); proj = P[0]+(rel[k]@u)*u
            side = 1 if (pk-proj)@perp[k] < 0 else -1      # +1: concave toward the pin (an arc about it)
        else: side = 0
    return sag, side, chord

def strokes(S, aid):
    """Per contact of a struck arm: everything 7, 8, 10 and 21 measure."""
    cache = S.__dict__.setdefault('_r_strike', {})
    if aid in cache: return cache[aid]
    rig = S.rig; cs = S.contacts(aid); out = []
    rend = face_fn(S, aid, True); scored = face_fn(S, aid, False)
    mal = _mallet(S, aid)
    if mal:
        # one apex and one wind-up with rulers 3, 4 and 9 (DESIGN §7.1): r_motion.prep's
        from players import r_motion as RM
        prep = {r['c'].i: r for r in RM.prep(S, aid)}; heads = _head_segments(S, aid)
    for i, c in enumerate(cs):
        n = c.normal; cp = c.point
        hs = lambda t, cp=cp, n=n: float((scored(t)-cp)@n)
        hr = lambda t, cp=cp, n=n: float((rend(t)-cp)@n)
        t_lo = cs[i-1].t_end if i else c.t-60.0
        t_hi = cs[i+1].t if i+1 < len(cs) else c.t+10.0
        extra = {}
        if mal:
            pr = prep[c.i]; t_apex, h_apex, t_rise = float(pr['t_apex']), float(pr['h_apex']), float(pr['t_w'])
            # 21 holds: the declared head 'hold' run ending at t_apex, still in 3D within 1 mm
            h0, _ = _run_before(heads, t_apex, ('hold',))
            hold = _hold(scored, t_apex, max(h0, t_lo), c.t) if h0 is not None else 0.0
            # 21 accents: the declared wind-up ending at t_apex, or at the hold run that does
            w0, _ = _run_before(heads, t_apex if h0 is None else h0, ('wind-up',))
            extra = dict(hold_declared=(t_apex-h0) if h0 is not None else 0.0, t_windup=w0)
            pin, axis = _declared_pin(heads, c.t)
        else:
            t_apex, h_apex = _apex_before(hs, c.t, t_lo)
            t_rise = _rise_start(hs, t_apex, t_lo)
            hold = _hold(scored, t_apex, t_lo, c.t)
        vm = deriv(rend, c.t, -1); vp = deriv(rend, c.t, +1)
        vin_n = float(vm@n)
        # ruler 8's float (a mallet): it ends where the declared head 'float' hands over, still
        # rising, to a driven rise (a Dahl up-stroke: its rise starts during the float) or to a
        # catch (A11); a float whose declared end leads anywhere else is judged to its turn
        fe = _float_end(heads, c.t) if mal else None
        t_fe, nx = fe if fe is not None else (None, None)
        rising = bool(t_fe is not None and t_fe < t_hi and float(deriv(rend, t_fe, -1)@n) > 1e-3)
        handed = rising and nx is not None and nx.tag in DRIVEN_RISE
        caught = rising and nx is not None and nx.tag == CATCH_TAG
        t_c1 = nx.t1 if caught else None
        if handed:
            # a driven rise that stops the head short of its park has caught it, whatever its tag
            t_park = float(prep[cs[i+1].i]['t_apex']) if i+1 < len(cs) else \
                max((g.t1 for g in heads if math.isfinite(g.t1)), default=t_hi)
            t_c1 = _stops_short(hr, t_fe, t_park)
            if t_c1 is not None: handed, caught = False, True
        fl = _float(rend, n, c.t, t_fe if (handed or caught) else t_hi)
        if handed: extra['handed'] = True
        if caught:
            ts = np.arange(t_fe, t_c1, DT); ts = np.append(ts, t_c1) if ts[-1] < t_c1-1e-9 else ts
            extra['catch'] = dict(t0=t_fe, t1=t_c1, h_rest=hr(t_c1), tag=nx.tag,
                                  v=np.array([float(deriv(rend, t, +1 if t < t_c1 else -1, 1)@n) for t in ts]),
                                  a=np.array([float(deriv(rend, t, +1 if t < t_c1 else -1, 2)@n) for t in ts]))
        # 10b: the head's world path over [t_apex, t_i] (a mallet's in the plane
        # perpendicular to its declared pin axis, against that pin)
        sag = side = None; chord = 0.0
        if c.t-t_apex > 1e-6:
            ts = np.linspace(t_apex, c.t, 101); P = np.array([scored(t) for t in ts])
            if not mal: sag, side, chord = _arc_10b(P, pin_fn=lambda t: _pin(S, aid, t), ts=ts)
            elif pin is not None: sag, side, chord = _arc_10b(P, pin, axis)
            else: sag, side, chord = _arc_10b(P, pin_fn=lambda t: _pin(S, aid, t), ts=ts)   # no declared pin
        pa = rig.pose(aid, t_apex); pi = rig.pose(aid, c.t)
        out.append(dict(extra,
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
    park at h after a bounce loop) needs Declared.prep: n/a until declared.
    The float/bounce split is FLOAT_IOI_KIND (DESIGN §7.2): 0.6 s for a
    mallet (the bounce loop above it: its first apex ballistic, then the
    stroke's apex at h), 1 s for the hammer as at M0."""
    out = []
    for aid in struck_arms(S):
        FLOAT_IOI = FLOAT_IOI_KIND[S.kind(aid)]; fi = f'{FLOAT_IOI:g}'
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
                              f'(t_up - t_i) / 0.5(IOI - T_down) of the next note, IOI <= {fi} s; target >= 1'))
        else: out.append(_vacuous(8, '8 float time', aid, f'no next note within IOI <= {fi} s (a free bounce loop instead)',
                                  ioi_gt1=_st(long_, 3)))
        # the bounce loop after IOI > 1 s
        loose = [s for s in st if s["c"].ioi_next > FLOAT_IOI+1e-9]
        rr = []
        for s in loose:
            fl = s['float']
            if fl['v'].size == 0 or s['e'] is None: rr.append(math.inf); continue
            span = s['t_up']-fl['t'][0]
            a_fl = (fl['v'][0]-float(deriv(face_fn(S, aid), s['t_up'], -1)@s['c'].normal))/span if span > 0 else 0.0
            if s.get('handed'):
                # a float handed over while rising (a Dahl up-stroke) has no free apex: the height
                # it has reached at the handover is the ballistic one, v0 T - a_float T^2 / 2
                T = s['t_up']-s['t']; v0 = s['e']*s['v_in']
                pred = v0*T-a_fl*T*T/2 if a_fl > 0 else 0.0
            else: pred = (s['e']*s['v_in'])**2/(2*a_fl) if a_fl > 0 else 0.0
            # a caught float rests where the free flight would have turned (A11)
            h = s['catch']['h_rest'] if 'catch' in s else s['h_up']
            rr.append(h/pred if pred > 1e-6 else math.inf)      # no rebound: nothing to predict
        if loose:
            ok = all(abs(x-1) <= .1 for x in rr)
            fin = [x for x in rr if math.isfinite(x)]
            handed = sum(bool(s.get('handed')) for s in loose); caught = sum('catch' in s for s in loose)
            out.append(Result(8, '8 bounce apex', aid, dict(n=len(loose), measured_over_ballistic=_st(fin, 2),
                                                           undefined=len(rr)-len(fin), handed=handed, caught=caught,
                                                           apex_m=_st([s['catch']['h_rest'] if 'catch' in s else s['h_up'] for s in loose], 3)), ok,
                              f'IOI > {fi} s: first apex = (e v_in)^2/(2 a_float) +- 10 %'
                              +('; a float handed over while rising (Dahl up-stroke): its height at the handover = v0 T - a_float T^2/2 +- 10 %' if handed else '')
                              +('; a caught float: its rest height against the apex (A11)' if caught else '')))
        else: out.append(_vacuous(8, '8 bounce apex', aid, f'no contact followed by IOI > {fi} s'))
        out.append(_catch(aid, st))
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
            out.append(Result(8, '8 apex vs h', aid, val, (not err) or max(err) <= .01, f'apex (IOI <= {fi} s) or park (IOI > {fi} s) = h +- 1 cm'))
        out.append(_rise(S, aid, st))
        out.append(_low_rest(S, aid, st))
    return out

def _catch(aid, st):
    """Ruler 8's '8 catch' (A11): every float handed over, still rising, to a
    declared 'catch'. On [t_catch, t_rest] of the rendered face at 1 ms (both
    ends one-sided): it begins once the float has shed CATCH_SHARE of its
    launch speed (v(t_catch) <= CATCH_SHARE v(t_i + 5 ms)), never reverses
    (v.n >= 0 and non-increasing: a.n <= 0), brakes no harder than -1.5 g and
    ends still (|v.n| < HITCH_V). Its rest height is '8 bounce apex''s. A
    driven rise that stops the head short of its park (_stops_short) is
    judged here too, ending where it stops ('undeclared')."""
    cs = [s for s in st if 'catch' in s]
    if not cs: return _vacuous(8, '8 catch', aid, 'no float handed over to a catch')
    bad = []; share, amin, amax, vmin, vend = [], [], [], [], []
    for s in cs:
        k = s['catch']; v, a = k['v'], k['a']/G
        v_launch = float(s['float']['v'][0]) if s['float']['v'].size else math.inf
        r = v[0]/v_launch; share.append(r); amin.append(float(a.min())); amax.append(float(a.max()))
        vmin.append(float(v.min())); vend.append(abs(float(v[-1])))
        why = [w for w, f in (('early', r > CATCH_SHARE+1e-9), ('reverses', v.min() < -1e-3),
                              ('pushes up', a.max() > 1e-3), ('brakes > 1.5 g', a.min() < -1.5),
                              ('not still', abs(v[-1]) >= HITCH_V)) if f]
        if why: bad.append((round(s['t'], 3), why))
    return Result(8, '8 catch', aid, dict(n=len(cs), undeclared=sum(s['catch']['tag'] != CATCH_TAG for s in cs),
                                          bad=len(bad), at=bad[:8], v_share=_st(share, 3),
                                          a_min_g=_f(min(amin), 2), a_max_g=_f(max(amax), 3),
                                          v_min=_f(min(vmin), 4), v_end=_f(max(vend), 4),
                                          ms=_st([(s['catch']['t1']-s['catch']['t0'])*1e3 for s in cs], 1)), not bad,
                  f'a float caught at the top of its flight: begins at <= {CATCH_SHARE:g} of the launch speed, never '
                  f'reverses, a.n in [-1.5 g, 0], ends still; rests at the ballistic apex (8 bounce apex)')

def _low_rest(S, aid, st):
    """Ruler 8's '8 low rest' (A11): inside each of '8 rise''s windows after a
    contact (each contact + 5 ms to the next t_apex, and the coda), no
    stretch longer than one frame where the scored face is still (|h'| <
    HITCH_V), more than HITCH_REV below the window's end height (the park),
    while the scored carriage travels (|x'| > X_MOVING, its step dwells
    included: _travelling), at RISE_DT."""
    if not _mallet(S, aid): return _none(8, '8 low rest', aid, 'the hinged hammer keeps the M0 reading until M5')
    scored = face_fn(S, aid, False); cx = _carriage_x(S, aid, False); heads = _head_segments(S, aid)
    end = max((g.t1 for g in heads if math.isfinite(g.t1)), default=st[-1]['t']+10.0)
    # after each rebound only: the first note's rest at the hover is no rebound (the homing
    # sweeps run under it at the start, a machine's own start-up)
    wins = [(a['t']+FLOAT_SKIP, b['t_apex'], b['c']) for a, b in zip(st, st[1:])]
    wins.append((st[-1]['t']+FLOAT_SKIP, end, st[-1]['c']))
    found = []; worst = 0.0
    for a, b, c in wins:
        ts = np.arange(a, b, RISE_DT)
        if len(ts) < 5: continue
        h = np.array([float((scored(t)-c.point)@c.normal) for t in ts]); x = np.array([cx(t) for t in ts])
        low = (np.abs(np.gradient(h, ts)) < HITCH_V) & (h < h[-1]-HITCH_REV) & _travelling(np.abs(np.gradient(x, ts)) > X_MOVING)
        k = 0
        while k < len(low):
            if not low[k]: k += 1; continue
            m = k
            while m+1 < len(low) and low[m+1]: m += 1
            d = (m-k+1)*RISE_DT; worst = max(worst, d)
            if d > 1/FPS+1e-9: found.append((round(float(ts[k]), 3), round(d*1e3, 1), round(float(h[k]), 4)))
            k = m+1
    return Result(8, '8 low rest', aid, dict(rises=len(wins), waits=len(found), longest_ms=round(worst*1e3, 1), at=found[:8]),
                  not found, f'no still head (|dh/dt| < {HITCH_V:g} m/s) more than {HITCH_REV*1e3:g} mm below its park while '
                  f'the carriage moves (|dx/dt| > {X_MOVING:g} m/s) for over one frame')

def _travelling(mv):
    """The moving mask with each pause of at most DWELL_MAX between moving
    samples filled in: a stepped carriage between two steps still travels."""
    out = mv.copy(); idx = np.flatnonzero(mv)
    for a, b in zip(idx, idx[1:]):
        if 1 < b-a <= DWELL_MAX/RISE_DT+1e-9: out[a+1:b] = True
    return out

def _rise(S, aid, st):
    """Ruler 8's '8 rise' (HITCH_K): every rise of a declaring mallet, each
    contact (+ FLOAT_SKIP) to the next note's t_apex, the first note's from
    its rest and the coda after the last contact, on the scored face."""
    if not _mallet(S, aid): return _none(8, '8 rise', aid, 'the hinged hammer keeps the M0 reading until M5')
    scored = face_fn(S, aid, False); heads = _head_segments(S, aid)
    def hf(c): return lambda t, cp=c.point, n=c.normal: float((scored(t)-cp)@n)
    end = max((g.t1 for g in heads if math.isfinite(g.t1)), default=st[-1]['t']+10.0)
    wins = [(max(st[0]['t']-30.0, 0.0), st[0]['t_apex'], st[0]['c'])]
    wins += [(a['t']+FLOAT_SKIP, b['t_apex'], b['c']) for a, b in zip(st, st[1:])]
    wins.append((st[-1]['t']+FLOAT_SKIP, end, st[-1]['c']))
    hits = []; worst = 1.0
    for a, b, c in wins:
        hh, w = _hitches(hf(c), a, b); hits += hh; worst = min(worst, w)
    return Result(8, '8 rise', aid, dict(rises=len(wins), hitches=len(hits), worst_ratio=round(worst, 3),
                                         at=[(x['t'], x['ms'], x['ratio']) for x in hits[:8]]), not hits,
                  f'no hitch: inside an up-run ({HITCH_REV*1e3:g} mm hysteresis) the upward speed stays >= {HITCH_K:g} x the '
                  f'lesser of its peaks before and after, unless the valley holds a still stretch (|dh/dt| < {HITCH_V:g} m/s) '
                  f'of >= {REST_MIN:g} s (a deliberate rest)')

# ---- 10 hammer arc -------------------------------------------------------------

def r10(S):
    """Per stroke [t_apex, t_i]: (a) the shaft's rotation |phi(t_apex) - phi(t_i)|
    — phi is Rig.head_angle (the hammer's hinged head; a mallet's shaft is
    rigid today, so 0) — >= 20 deg, >= 35 deg when the note's IOI >= 0.7 s (the
    hammer >= 20 deg); (b) the scored face's path: sagitta/chord >= 0.05 and
    concave toward the pin (the arc about it: the bulge points away from the
    pin; the pin is the hammer's hinge; a mallet's is the virtual pin its
    'stroke' segment declares (extra['pin'], contact + sigma R_PIN z, where the
    M5 hinge goes), and its path and pin are measured in the plane
    perpendicular to the declared axis (x: y-z), DESIGN §7.3); (c) the angle between v(t_i-) of the rendered face and
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
                          all(x >= .05 for x in sag) and toward == len(st), 'sagitta/chord >= 0.05, concave toward the pin'
                          +("; y-z plane (perpendicular to the declared pin axis), against the declared pin" if _mallet(S, aid) else '')))
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

def _travels_declared(S, aid):
    """A declaring mallet's travels (DESIGN §7.5): its carriage 'travel'
    segments grouped by extra['travel'] (a stepped travel's per-tooth steps
    and dwells are one travel), those that move the carriage |dx| >= 1 mm on
    the scored x (Rig.path_at: ring-free), each with its click knots (those
    whose extra['travel'] is its id), its declared regime ('step' ->
    'stepped', 'freewheel'), and its free window: from the carriage's
    earliest start — the next note's sched `go` (= the score's t_move), the
    contact before it, the end of the homing legs — to the travel's end (the
    contact, or the hold it must reach first). `fits` is
    motion_timing.travel_regime's test, the planner's own: the window holds
    teeth(dx) step_periods (info). `earliest` is the same start read off
    the score alone — the next note's t_move, the contact before, the end of
    either channel's homing legs — against which '19 regime' checks the
    stroke's declared window (extra['window']). `hurried` is the notation's
    (_hurried_pairs), as for every ratchet arm."""
    rig = S.rig; d = S.declared(aid); cs = S.contacts(aid); MT = ST.motion_timing
    car = sorted((g for g in d.segments if g.extra.get('channel') == 'carriage'), key=lambda g: g.t0)
    home_ends = [g.t1 for g in car if g.tag == 'home' and math.isfinite(g.t1)]
    home_all = [g.t1 for g in d.segments if g.tag == 'home' and math.isfinite(g.t1)]   # either channel's homing legs
    groups = {}
    for g in car:
        if g.tag == 'travel' and g.extra.get('travel') is not None: groups.setdefault(g.extra['travel'], []).append(g)
    clicks = {}
    for k in d.knots:
        if k.kind == 'click' and k.extra.get('travel') is not None: clicks.setdefault(k.extra['travel'], []).append(k)
    hur, _ = _hurried_pairs(S, aid)
    out = []
    for tid, gs in sorted(groups.items()):
        t0 = min(g.t0 for g in gs); t1 = max(g.t1 for g in gs)
        if not (math.isfinite(t0) and math.isfinite(t1)) or t1-t0 < 1e-6: continue
        x0 = float(rig.path_at(aid, t0)[0]); x1 = float(rig.path_at(aid, t1)[0])
        if abs(x1-x0) < 1e-3: continue
        regs = {g.extra.get('regime') for g in gs}
        reg = regs.pop() if len(regs) == 1 else None
        ks = sorted(clicks.get(tid, []), key=lambda k: k.t)
        prev = [c for c in cs if c.t <= t0+1e-9]; nxt = [c for c in cs if c.t >= t1-1e-9]
        prev = prev[-1] if prev else None; nxt = nxt[0] if nxt else None
        lo = prev.t if prev else 0.0; hi = nxt.t if nxt else max(S.total, t1)
        go = max([float(nxt.sched['go']) if nxt else t0]+([prev.t] if prev else [])+[h for h in home_ends if h <= t0+1e-9])
        free = t1-go; need = MT.contact_travel_s(x1-x0)
        tm = float(nxt.event.get('t_move', nxt.sched['go'])) if nxt else t0
        earliest = max([tm]+([prev.t] if prev else [])+[h for h in home_all if h <= t0+1e-9])
        out.append(dict(t0=t0, t1=t1, tid=tid, law=next((g.law for g in gs if g.law != 'hold'), 'hold'),
                        laws=sorted({g.law for g in gs}), dx=x1-x0, x0=x0, clicks=[k.t for k in ks], click_knots=ks,
                        teeth=MT.teeth(x1-x0), window=max(hi-lo, t1-t0), free=free, need=need, fits=free >= need-1e-9,
                        prev=prev, nxt=nxt, regime={'step': 'stepped', 'freewheel': 'freewheel'}.get(reg, reg),
                        declared_hurried=bool(gs[0].extra.get('hurried')),
                        window_declared=gs[0].extra.get('window'), earliest=earliest,
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
        if _mallet(S, aid):
            rs, cnt, ceiling = _r19_mallet(S, aid)
            out.extend(rs); totals.setdefault(kind, [0, 0]); totals[kind][0] += cnt; totals[kind][1] += ceiling
            continue
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

def _hurried_rows(S, aid, knots, tf, xr, E):
    """Per hurried contact pair: (t_i, peak |x''| in g, rho) — ruler 19's hurried
    judgement, shared by both readings."""
    cs = S.contacts(aid); hur, moves = _hurried_pairs(S, aid); rows = []
    for i in sorted(hur):
        a, b = cs[i-1].t, cs[i].t
        pk = _peak_acc(S, aid, a, b, knots)
        k = np.nonzero((tf > a) & (tf-1/FPS < b))[0]; k = k[k > 0]
        rho = float(np.max(np.abs(xr[k]-xr[k-1]))/E) if k.size else 0.0
        rows.append((cs[i].t, pk/G, rho))
    return rows, moves

def _r19_mallet(S, aid):
    """Ruler 19 on a declaring mallet (DESIGN §7.5). Travels: _travels_declared.
    regime (the lead's decision (g)): the declared regime is
    motion_timing.travel_regime(dx, w1 - w0) on the declared window (w0, w1),
    and that window is checked on its own: t_move <= w0 <= the carriage's
    earliest start read off the score, w1 = the contact or the start of its
    declared cocked hold; a step travel lies inside it, a freewheel starts no
    sooner than t_move and has arrived by w1. stepped: the per-frame carriage |dx| (Rig.pose root
    x = Rig.carriage_x, its detent ring included) <= 1 tooth, every step's
    dwell >= 0.5 (a step = a click knot's period, from its click to the next
    or the travel's end; dwell = the share of it the scored x spends within
    0.1 tooth of the step's detent), and teeth(dx) clicks. freewheel: a smooth
    law, peak |x''| <= 3 g (5 g on a counted hurried travel), x' = x'' = 0 at
    the bounding contacts and at the travel's own ends, monotone, teeth(dx)
    clicks; all on the scored x. pawl: a freewheel click's declared state
    against the scored tooth rate |x'|/PITCH at its knot (drop below
    PAWL_RIDE, ride at or above), a stepped click 'drop' (it dwells on the
    detent, decision (d)); Rig.pawl_ride 0 across stepped travels and the
    smoothstep of the rate across freewheels. hurried: as for every ratchet arm."""
    rig = S.rig; kind = S.kind(aid); E = E_HEAD[kind]; out = []
    d = S.declared(aid); knots = np.array(sorted(k.t for k in d.knots))
    trav = _travels_declared(S, aid)
    fr = S.poses(aid, 'frames'); tf = fr['t']; xr = fr['root'][:, 0]
    cs_x = _carriage_x(S, aid, False)
    # -- regime (DESIGN §7.5 as amended by the lead's decision (g)): the declared regime equals
    # motion_timing.travel_regime(dx, w1 - w0) on the stroke's declared window (w0, w1), and the window is
    # checked on its own, against the score and the head: w0 >= the score's t_move of the note the travel
    # serves and no later than the carriage's earliest start (max(t_move, the contact before, the homing's
    # end): the window is not shortened); w1 is that note's contact, or the start of its declared cocked
    # 'hold' (a head 'hold' segment, extra['hold'] == 'cocked', starting at w1 and running into the 'stroke'
    # that ends at the contact). A stepped travel lies inside the window; a freewheel never starts before
    # t_move and has arrived by w1.
    heads = sorted((g for g in d.segments if g.extra.get('channel') == 'head'), key=lambda g: g.t0)
    MT = ST.motion_timing; rows = []
    for tv in trav:
        nxt = tv['nxt']; wd = tv['window_declared']; why = []
        if nxt is None: why.append('no contact after the travel')
        if not wd or len(wd) != 2: why.append('no declared window')
        if why: rows.append(dict(tv=tv, ok=False, why=why)); continue
        w0, w1 = float(wd[0]), float(wd[1])
        tm = float(nxt.event['t_move']) if 't_move' in nxt.event else float(nxt.sched['go'])
        if w0 < tm-1e-9: why.append('w0 before t_move')
        if w0 > tv['earliest']+1e-9: why.append('w0 after the earliest start')
        end = 'contact' if abs(w1-nxt.t) <= 1e-9 else None
        if end is None:
            j = next((k for k, g in enumerate(heads) if abs(g.t0-w1) <= 1e-9 and g.t1 > g.t0), None)
            if (j is not None and heads[j].tag == 'hold' and heads[j].extra.get('hold') == 'cocked' and j+1 < len(heads)
                    and heads[j+1].tag == 'stroke' and abs(heads[j+1].t1-nxt.t) <= 1e-9 and abs(heads[j].t1-heads[j+1].t0) <= 1e-12):
                end = 'cocked hold'
            else: why.append('w1 is neither the contact nor its cocked hold\'s start')
        rule = MT.travel_regime(tv['dx'], w1-w0)
        want = {'step': 'stepped', 'freewheel': 'freewheel'}.get(rule, rule)
        if tv['regime'] not in ('stepped', 'freewheel'): why.append('undeclared regime')
        elif tv['regime'] != want: why.append(f'regime {tv["regime"]} but the rule says {want}')
        if tv['regime'] == 'stepped' and not (tv['t0'] >= w0-1e-9 and tv['t1'] <= w1+1e-9): why.append('step travel outside its window')
        if tv['regime'] == 'freewheel' and not (tv['t0'] >= tm-1e-9 and tv['t1'] <= w1+1e-9):
            why.append('freewheel before t_move or after w1')
        rows.append(dict(tv=tv, ok=not why, why=why, w=w1-w0, need=tv['need'], end=end, early=w0-tm))
    bad = [r for r in rows if not r['ok']]
    out.append(Result(19, '19 regime', aid, dict(
        travels=len(trav), stepped=sum(tv['regime'] == 'stepped' for tv in trav),
        freewheel=sum(tv['regime'] == 'freewheel' for tv in trav), bad=len(bad),
        windows_to=dict(contact=sum(r.get('end') == 'contact' for r in rows), hold=sum(r.get('end') == 'cocked hold' for r in rows)),
        window_over_need=_st([r['w']/r['need'] for r in rows if r.get('need') and 'w' in r], 3),
        w0_after_t_move_s=_st([r['early'] for r in rows if 'early' in r], 3),
        failing=[dict(t1=_f(r['tv']['t1'], 3), regime=r['tv']['regime'], why=r['why'],
                      window_s=_f(r.get('w'), 3), need_s=_f(r.get('need'), 3)) for r in bad][:6]),
        not bad,
        'regime == motion_timing.travel_regime(dx, w1 - w0) on the declared window; the window on its own: '
        't_move <= w0 <= the earliest start (t_move, the contact before, the homing\'s end), w1 = the contact or its '
        'cocked hold\'s start; a step travel inside it, a freewheel not before t_move and arrived by w1'))
    # -- stepped
    stepped = [tv for tv in trav if tv['regime'] == 'stepped']
    if stepped:
        dwell, short, fdx, peak, miss = [], 0, [], 0.0, 0
        for tv in stepped:
            starts = tv['clicks'] or [tv['t0']]
            ends = starts[1:]+[tv['t1']]
            miss += len(tv['clicks']) != tv['teeth']
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
            travels=len(stepped), steps=len(dw), teeth_per_click=_tpc(stepped), click_count_misses=miss,
            frame_dx_m=_f(fdx.max() if fdx.size else 0.0, 4), frames_over_tooth=int(np.sum(fdx > R.PITCH+1e-9)),
            dwell=_st(dw, 2), steps_dwell_lt_half=int(np.sum(dw < .5)), steps_under_3_frames=short,
            peak_acc_g=_f(peak/G, 1), laws=sorted({l for tv in stepped for l in tv['laws']})),
            bool((fdx.size == 0 or fdx.max() <= R.PITCH+1e-9) and np.all(dw >= .5) and miss == 0),
            'declared step travels: <= 1 tooth (47 mm) a frame; dwell (within 0.1 tooth of the detent) >= 0.5 of every '
            'step; teeth(dx) clicks'))
    else: out.append(_vacuous(19, '19 stepped', aid, 'no declared step travel on this arm'))
    # -- freewheel
    free = [tv for tv in trav if tv['regime'] == 'freewheel']
    if free:
        bad, peaks, ends, n_law, n_g, n_end, n_mono, n_click = 0, [], [], 0, 0, 0, 0, 0
        for tv in free:
            pk = _peak_acc(S, aid, tv['t0'], tv['t1'], knots); peaks.append(pk/G)
            e_bad = False
            for t, side in [(c.t, sd) for c, sd in ((tv['prev'], +1), (tv['nxt'], -1)) if c is not None]+[(tv['t0'], +1), (tv['t1'], -1)]:
                v = abs(float(deriv(cs_x, t, side, 1))); a = abs(float(deriv(cs_x, t, side, 2)))
                ends.append(v); e_bad |= v > 1e-3 or a > .05
            xs = np.array([cs_x(t) for t in np.r_[np.arange(tv['t0'], tv['t1'], DT), tv['t1']]])
            mono = bool(np.all(np.diff(xs)*np.sign(tv['dx']) >= -1e-9))
            law_ok = all(l in SMOOTH_LAWS for l in tv['laws']); g_ok = pk <= (A_HURRIED if tv['hurried'] else A_STOP)
            click_ok = len(tv['clicks']) == tv['teeth']
            n_law += not law_ok; n_g += not g_ok; n_end += e_bad; n_mono += not mono; n_click += not click_ok
            bad += not (law_ok and g_ok and not e_bad and mono and click_ok)
        out.append(Result(19, '19 freewheel', aid, dict(
            travels=len(free), bad=bad, hurried=sum(tv['hurried'] for tv in free), laws=sorted({l for tv in free for l in tv['laws']}),
            not_smooth=n_law, over_g=n_g, ends_moving=n_end, non_monotone=n_mono, click_per_tooth_misses=n_click,
            teeth_per_click=_tpc(free), peak_g=_st(peaks, 2), end_speed=_st(ends, 4)), bad == 0,
            "declared freewheel travels: a smooth law, <= 3 g (5 g hurried), x' = x'' = 0 at the contacts and the "
            'travel\'s ends, monotone, a click per tooth'))
    else: out.append(_vacuous(19, '19 freewheel', aid, 'no declared freewheel travel on this arm'))
    # -- pawl: every travel click, and the ride between them. A freewheel click's
    # declared state against the scored tooth rate |x'|/PITCH at its knot (the
    # mid-tooth crossing, the carriage moving): drop below PAWL_RIDE, ride at or
    # above. A stepped click is judged by its regime, not by the rate at its knot
    # (the step's start, where the rate is 0): every step lands and dwells on its
    # detent (19 stepped holds the dwell), so the pawl drops into each tooth
    # whatever the step's peak rate (the lead's decision (d)); its label must be
    # 'drop'. The ride itself (Rig.pawl_ride) is checked across every travel,
    # every 1/240 s and at each click: exactly 0 on a stepped travel; on a
    # freewheel the smoothstep of the scored tooth rate over PAWL_RIDE_BAND,
    # and > 0 somewhere in every freewheel whose peak rate passes the band's foot.
    fk = [(k, tv) for tv in trav for k in tv['click_knots']]
    if not fk: out.append(_vacuous(19, '19 pawl', aid, 'no travel clicks'))
    else:
        miss = {'stepped': 0, 'freewheel': 0}; undecl = 0; rides = 0; margin = []; step_peak = []
        lo, hi = ST.PAWL_RIDE_BAND
        for k, tv in fk:
            reg = tv['regime']
            if reg == 'freewheel':
                rate = abs(float(deriv(cs_x, k.t, +1, 1)))/R.PITCH
                want = 'drop' if rate < PAWL_RIDE else 'ride'; margin.append(abs(rate-PAWL_RIDE))
            else:
                want = 'drop'
            rides += want == 'ride'
            if k.extra.get('pawl') not in ('drop', 'ride'): undecl += 1
            elif k.extra['pawl'] != want: miss[reg] = miss.get(reg, 0)+1
        ride_off = {'stepped': 0, 'freewheel': 0}; ride_err = 0.0; dead = 0
        for tv in trav:
            ts = np.r_[np.arange(tv['t0'], tv['t1'], 1/240), tv['t1'], tv['clicks']]
            ride = np.array([rig.pawl_ride(aid, float(t)) for t in ts])
            rate = np.array([abs(float(S.stroke(aid).x(float(t), 1)))/R.PITCH for t in ts])
            if tv['regime'] == 'stepped':
                step_peak.append(float(rate.max()))
                ride_off['stepped'] += int(np.sum(ride != 0.0))
            else:
                u = np.clip((rate-lo)/(hi-lo), 0, 1); want_r = u*u*(3-2*u)
                e = np.abs(ride-want_r); ride_err = max(ride_err, float(e.max()))
                ride_off['freewheel'] += int(np.sum(e > 1e-9))
                dead += bool(rate.max() > lo+1e-6 and ride.max() <= 0.0)
        # ...and the homing x legs: stepped tooth by tooth, the pawl drops each tooth
        ride_off['home'] = 0
        for g in d.segments:
            if g.extra.get('channel') != 'carriage' or g.tag != 'home' or not math.isfinite(g.t1-g.t0): continue
            ts = np.r_[np.arange(g.t0, g.t1, 1/240), g.t1]
            ride_off['home'] += int(sum(rig.pawl_ride(aid, float(t)) != 0.0 for t in ts))
        ok = sum(miss.values()) == 0 and undecl == 0 and sum(ride_off.values()) == 0 and dead == 0
        out.append(Result(19, '19 pawl', aid, dict(clicks=len(fk), rides=rides, misses=sum(miss.values()), misses_by_regime=miss,
                                                   undeclared=undecl, rate_margin=_st(margin, 2),
                                                   stepped_peak_rate=_st(step_peak, 2), ride_off=ride_off,
                                                   ride_err=_f(ride_err, 9), freewheel_never_riding=dead),
                          ok,
                          'freewheel click: drops below 15 teeth/s, rides at or above (scored |x\'|/PITCH at the knot); stepped '
                          'click: drops (each step dwells on its detent); Rig.pawl_ride exactly 0 across stepped and homing travels and the '
                          'smoothstep of the tooth rate over PAWL_RIDE_BAND across freewheels (every 1/240 s and at each click)'))
    # -- hurried
    rows, moves = _hurried_rows(S, aid, knots, tf, xr, E)
    today = TODAY_HURRIED.get(S.asset, {}).get(aid)
    cnt = len(rows); ceiling = today if today is not None else HURRIED_END
    ok = cnt <= ceiling and all(g <= 5 and r <= 1.5 for _, g, r in rows)
    decl = sum(tv['declared_hurried'] for tv in trav)
    out.append(Result(19, '19 hurried', aid, dict(
        count=cnt, today=today, moves=moves, at=[_f(t, 3) for t, _, _ in rows][:8],
        peak_g=_f(max([g for _, g, _ in rows], default=0.0), 2), rho=_f(max([r for _, _, r in rows], default=0.0), 2),
        declared_hurried=decl, E=_f(E, 4)), ok,
        f'count <= {ceiling} (today\'s; <= {HURRIED_END} at the end), each <= 5 g and rho <= 1.5'))
    return out, cnt, ceiling

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
    — begin their rise (the wind-up W_i's start) by t_{i-1} + 0.5·IOI_i.
    A declaring mallet (DESIGN §7.6): (1) is computed within IOI classes —
    notes whose IOI_i lie within 5 % of the class's shortest, classes with >= 3
    notes and >= 2 distinct a' — and is the minimum over them (with no such
    class, pooled over the arm as every other arm is); (3) a hold is the declared head-channel 'hold' run ending
    at t_apex, still in 3D within 1 mm (strokes()); (4) the rise starts at the
    declared 'wind-up' that ends at t_apex (or at that hold run) when there is
    one, else at ruler 3's t_w."""
    out = []
    for aid in struck_arms(S):
        st = strokes(S, aid)
        if not st:
            for nm in ("21 height vs a'", '21 height vs tempo', '21 holds', '21 accents'): out.append(_none(21, nm, aid, 'no contacts'))
            continue
        mal = _mallet(S, aid)
        h = np.array([s['h_apex'] for s in st]); a = [s['c'].a for s in st]
        have = [(x, ai) for x, ai in zip(h, a) if ai is not None]
        if mal:
            out.append(_height_vs_a_classes(st, aid))
        elif len(have) >= 3 and np.ptp([y for _, y in have]) > 1e-9:
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
        hv = dict(holds=len(held), at=[_f(s['t'], 2) for s in held][:6], long_gaps=len(long_),
                  missing=missing, at_short_gap=at_tempo, hold_ms=_st([s['hold']*1e3 for s in st], 0))
        if mal: hv['declared_ms'] = _st([s['hold_declared']*1e3 for s in st if s['hold_declared'] > 0], 0)
        out.append(Result(21, '21 holds', aid, hv,
                          missing == 0 and at_tempo == 0, '>= 3 frames within 1 mm of the apex, after every gap >= 0.8 s and no other'
                          +('; a hold is a declared head-channel hold run ending at t_apex, still in 3D' if mal else '')))
        # accents at tempo
        acc = []
        for i in range(1, len(st)):
            c, p = st[i]['c'], st[i-1]['c']
            if c.ioi < HOLD_GAP and c.amp >= p.amp+ACCENT_JUMP-1e-9:
                t_r = st[i]['t_windup'] if mal and st[i].get('t_windup') is not None else st[i]['t_rise']
                acc.append((t_r-p.t)/c.ioi)
        if acc:
            r = np.array(acc)
            out.append(Result(21, '21 accents', aid, dict(n=len(r), late=int(np.sum(r > .5)), rise_at=_st(r, 3)), bool(np.all(r <= .5)),
                              'rise start - t_{i-1}, in IOIs; target <= 0.5'
                              +('; the rise starts at the declared wind-up ending at t_apex (or its hold), else ruler 3\'s t_w' if mal else '')))
        else: out.append(_vacuous(21, '21 accents', aid, 'no accent at tempo on this arm'))
    return out

def _ioi_classes(notes):
    """Tempo classes: notes sorted by IOI, each class every note within
    IOI_CLASS of the class's shortest IOI (the first note's IOI = inf is its own)."""
    out = []
    for s in sorted(notes, key=lambda s: s['c'].ioi):
        i = s['c'].ioi
        if out and math.isfinite(i) and math.isfinite(out[-1][0]) and i <= out[-1][0]*(1+IOI_CLASS)+1e-12: out[-1][1].append(s)
        else: out.append((i, [s]))
    return out

def _height_vs_a_classes(st, aid):
    """21 (1) on a declaring mallet: Spearman(apex, a') within IOI classes,
    the minimum over the classes that can rank (>= 3 notes with a', >= 2
    distinct a')."""
    rows = []
    for ioi, mem in _ioi_classes([s for s in st if s['c'].a is not None]):
        av = np.round([s['c'].a for s in mem], 6)
        if len(mem) < 3 or len(np.unique(av)) < 2: continue
        rows.append((ioi, len(mem), _rho([s['h_apex'] for s in mem], av)))
    h = [s['h_apex'] for s in st]
    if not rows:
        # no class can rank: the pooled rule every other arm is held to (M0's), so an arm with
        # no qualifying class is still measured; vacuous only where M0's rule was (< 3 notes with a', or a' constant)
        have = [(s['h_apex'], s['c'].a) for s in st if s['c'].a is not None]
        if len(have) >= 3 and np.ptp([y for _, y in have]) > 1e-9:
            rho = _rho([x for x, _ in have], [y for _, y in have])
            return Result(21, "21 height vs a'", aid, dict(rho=rho, classes=0, pooled=True, apex_m=_st(h, 3), n=len(have)),
                          rho is not None and rho >= .9,
                          "no IOI class with >= 3 notes and >= 2 distinct a': pooled over the arm (the M0 rule)"
                          + ('' if rho is not None else "; apex height constant: no rank against a'"))
        return _vacuous(21, "21 height vs a'", aid, "no IOI class with >= 3 notes and >= 2 distinct a', and fewer than 3 notes "
                        "with a' or a' constant on this arm", apex_m=_st(h, 3))
    worst = min(rows, key=lambda r: -2 if r[2] is None else r[2])
    rho = worst[2]
    return Result(21, "21 height vs a'", aid, dict(rho=rho, classes=len(rows), worst_ioi=_f(worst[0], 3), worst_n=worst[1],
                                                   per_class=[[_f(i, 3), n, r] for i, n, r in rows][:8], apex_m=_st(h, 3),
                                                   n=sum(r[1] for r in rows)),
                  rho is not None and rho >= .9,
                  "within IOI classes (IOIs within 5 %; >= 3 notes, >= 2 distinct a'); rho = the least over the classes"
                  + ('' if rho is not None else "; apex height constant within a class: no rank against a'"))

RULERS = {7: r7, 8: r8, 10: r10, 11: r11, 19: r19, 21: r21}

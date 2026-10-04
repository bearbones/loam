"""Rulers 12 (pluck), 13 (place, plant, slide, raise), 14 (strum), 23 (no
penetration) and 24 (phrase ends) of docs/goals/the-players.md ("Acceptance").

The string players (kind 'pick': the harp arms; kind 'rake') and every player's
phrase-end release. Today (6c326b5) a harp arm has no digits: its one plectrum
is the "pad", Rig.tip_at its contact point, so the pluck rulers measure the
plectrum where the goal says digit and report n/a only for what needs digits
(MCP, groups, planting, knuckle line). The rake carries the same plectrum
(tools/build_forms.py gives every non-struck arm linkage.pick_tool).

Definitions where the goal leaves a choice:

  pad, n_hat   The pad is the tool tip (Rig.tip_at). d_rel = |p(t-) - c| with
               p(t-) = p(t - 1e-12 s) + 1e-12 s * v(t-) (the left limit; below
               1e-9 m it is reported as 0); n_hat = (p(t-) - c)/d_rel when
               d_rel > 1 um, else the approach direction v(t-)/|v(t-)| (today:
               +z, into the string plane). Polarisation = asin(|n_hat . z|).
  t_place      Ruler 12's literal one: scanning back from t- in 1 ms steps,
               bisected to 10 ns, the start of the last interval on which the
               pad stays within 0.5 mm of the segment c..c + d_rel n_hat.
               Exactness is judged at the DECLARED placing and slip (a 'place'
               knot, a 'slip' knot's extra d_rel / n); today neither is
               declared, so the contact itself (t) is both.
  string       The harness draws the string (harness/performance.gd:588-610,
               harness/shaders/wire_string.gdshader): the sum over every hit on
               it with 0 <= tau <= 5 s of its shape clip's frame int(tau*rate),
               gain amp*0.035, bent along d*(cross_axis, 0, 1) of the string's
               link basis, cross_axis 0.35; nothing of a hit before its t. Read
               here from score.json + shapes.f32 (Godot is not run). 'string':
               |drawn - (p - c)| at the pick point through [t_place, t-] and,
               at t, the free clip's first shape against p(t-) - c. 'deflection':
               the drawn direction at the release frame k = ceil(30 t) against
               n_hat (19.3 deg along it, 160.7 against).
  waits        A slide wait is a gap (previous t_end to next t) >= 1 s that does
               not follow a listed phrase end; it is sampled from the previous
               note's t_free to the next t_place. "At the string" = the pad within
               0.5 mm of the axis of the previous or next note's string.
  groups       Inside a hand: n/a (no digits). Across hands: the final chord's
               three landings (t_place), spread against one bake row (1/240 s).
  raise        t_close = the phrase end's contact t; t_raise_end = the next
               motion start (first later declared segment tagged travel,
               wind-up, stroke, fall, place, home, ghost or slide) or t_close +
               1.5 s. T_raise = the end of the release chain (the last
               non-hold segment from t_end up to the next motion) - t_end. The
               frame line is the played string's top (its neck bridge).
               "Toward the arm" is the goal's literal delta . z < 0 (every harp
               rail stands at z < 0). The last note's dur is how long it
               sounds: its ring (score.json `dur`, the synth's t60 x 1.1)
               cut short by the player's next contact or the piece's end
               (`_sounding`). The ring alone is one value per material, which
               would leave both Spearman rulers undefined.
  strum        v_sweep = L_path/(t_end - t_hit), L_path the polyline through the
               swept contact points; entry = |v(t_hit-)|/v_sweep. Corners are
               counted at every declared knot of the sweep event from its
               stroke start to t_free. E for rho is the arm_capsules tool
               capsule (tip -> swan-neck apex, r 0.03); rho with the 0.19 m pick
               tool extent of the provisional table is reported beside it.
  carriage     The rake's carriage limit is 6 m/s until the arm carries a hand
               (manifest arm 'hand'), SERVO_V_MAX after; 3 g throughout.
  no pen.      Struck heads: the core sphere (mallet r 0.06, formlab/linkage.py
               mallet_tool; hammer r HAMMER head_r about the arm_capsules ball
               centre) against the bars (box w x 0.11 x length under the a-b
               line), blocks (the same box plus the 4 mm proud slit) and bells
               (the crown, r 0.12 x 0.045) as tools/build_clockwork.py builds
               them. Strings: capsules a-b, r = the drawn gauge
               0.0035*2^((64-midi)/18) (performance.gd:251, test_eyelets.py).
               The tool is the arm_capsules 'tool' capsule. Exempt: the played
               string during its stick [t_place, t] (the contact instant
               today), and the swept strings during a sweep's [t_hit, t_end].
               Samples: the 120 Hz grid plus every contact instant.
  phrase ends  The goal's lists, matched to scored contacts within 15 ms.
               "arm0 between tolls (5.71-20 s)" = arm0's contacts at 5.71 <= t
               < 20. Mallets: the held raise is the highest height held for 3
               frames before the next motion, against 1.5 x the arm's tempo
               apex (median per-stroke apex, 45.71-68.57 s, IOI <= 0.5 s); the
               lift-and-park needs a later rise > 1 cm. Rake: "upward" = the
               release displacement within 45 deg of +y with follow-through >=
               0.2 m. Hammer: "slowly" = T >= 0.3 s (the raise's floor) to
               within 1 deg of rest, with no reversal. Park time = the end of
               an arm's last non-hold segment; frames are k = ceil(30 t).
"""
import math
import numpy as np
from players import core
from players.core import Result, deriv, FPS, HZ, G
from formlab import rig as R
from formlab import clearance as CL
from formlab.layout import BAR

TOL_RAY = 5e-4       # m: ruler 12's "within 0.5 mm of the ray"
EXACT = 1e-9         # m: "exact to 1e-9 on the rig"
LEFT = 1e-12         # s: t- is evaluated this far before the slip
TIME_TOL = .015      # s: the goal quotes times to 2 decimals
TOOL_R = .03         # arm_capsules 'tool' radius
BAKE_HZ = 240        # formlab/bake.py's row rate: "1 bake row" = 1/240 s
PICK_D = .19         # the provisional table's pick-tool extent (reported beside rho)
HEAD_R = .06         # formlab/linkage.py mallet_tool head_r
BLADE = dict(h=.07, t=.007)                  # linkage.pick_tool blade_h, blade_t
GAIN = .035          # performance.gd: gain = amp*0.035
CROSS_AXIS = .35     # wire_string.gdshader cross_axis
NEXT_TAGS = ('travel', 'wind-up', 'stroke', 'fall', 'place', 'home', 'ghost', 'slide')

# The goal's lists ("Harp hands" gestures, "Phrase ends and the ending").
RUNS = [(13.57, 14.11), (16.43, 16.96), (19.29, 19.82), (22.14, 22.68)]
HARP_ENDS = [(14.11, None), (16.96, None), (19.82, None), (22.68, None), (65.0, 'harp_arm2'),
             (72.14, None), (75.0, None), (78.57, None)]
HARP_TOLLS = ('harp_arm0', 5.71, 20.0)
FINAL_CHORD = 78.57
MALLET_ENDS = (56.79, 68.21, 75.71)
RAKE_ENDS = (68.57, 77.14)
TEMPO = (45.71, 68.57)
ENDING = (78.57, 86.0)

# ---- small helpers --------------------------------------------------------------

def _memo(S, key, build):
    store = S.__dict__.setdefault('_r_strings', {})
    if key not in store: store[key] = build()
    return store[key]

def _r(v, nd=4):
    v = float(v)
    return float(f'{v:.{nd}g}') if math.isfinite(v) else None

def _st(x, scale=1.0, nd=4):
    """min / p50 / max / n of a sample, scaled; None when empty."""
    x = np.asarray(x, float)*scale
    if x.size == 0: return None
    return dict(min=_r(x.min(), nd), p50=_r(np.median(x), nd), max=_r(x.max(), nd), n=int(x.size))

def _unit(v):
    v = np.asarray(v, float); n = np.linalg.norm(v)
    return v/n if n > 0 else v

def _deg(a, b):
    a = _unit(a); b = _unit(b)
    return math.degrees(math.acos(float(np.clip(a@b, -1.0, 1.0))))

def _pt_seg(P, A, B):
    """Distance from points P (..., 3) to the segment A-B."""
    P = np.asarray(P, float); d = B-A; dd = float(d@d)
    if dd < 1e-24: return np.linalg.norm(P-A, axis=-1)
    u = np.clip(((P-A)@d)/dd, 0.0, 1.0)
    return np.linalg.norm(P-(A+u[..., None]*d), axis=-1)

def _back(pred, t_in, t_lo, step=1e-3):
    """Start of the contiguous interval ending at t_in on which pred holds:
    sampled back every `step`, then bisected to 10 ns. t_in if pred(t_in) fails."""
    if not pred(t_in): return t_in
    b = t_in
    while b-step > t_lo and pred(b-step): b -= step
    a = max(b-step, t_lo)
    if pred(a): return a
    while b-a > 1e-8:
        m = .5*(a+b)
        if pred(m): b = m
        else: a = m
    return b

def wire_radius(midi):
    """performance.gd:251's drawn gauge (tools/test_eyelets.py wire_radius)."""
    return .0035*2**((64.0-float(midi))/18.0)

def _frame(t): return int(math.ceil(t*FPS-1e-9))

def _segs(S, aid):
    return _memo(S, ('segs', aid), lambda: sorted(S.declared(aid).segments, key=lambda s: s.t0))

def _knot_times(S, aid):
    return _memo(S, ('knots', aid), lambda: np.array(sorted({round(k.t, 12) for k in S.declared(aid).knots})))

def _next_motion(S, aid, t):
    """The next motion's start after t: the first later declared segment that
    begins a note (NEXT_TAGS), or inf."""
    for s in _segs(S, aid):
        if s.t0 > t+1e-9 and s.tag in NEXT_TAGS and s.t1 > s.t0: return float(s.t0)
    return math.inf

def _park(S, aid, t_from, t_next):
    """End of the release chain after t_from: the last non-hold segment that
    starts at or after t_from and ends by t_next (t_from if there is none)."""
    end = t_from
    for s in _segs(S, aid):
        if s.t0 >= t_from-1e-9 and math.isfinite(s.t1) and s.t1 <= t_next+1e-9 and s.tag != 'hold' \
                and s.tag not in NEXT_TAGS:
            end = max(end, float(s.t1))
    return end

def _last_motion_end(S, aid):
    ends = [float(s.t1) for s in _segs(S, aid) if s.tag != 'hold' and math.isfinite(s.t1)]
    return max(ends) if ends else None

def _ev(c): return int(c.event.get('i', c.i))

def _stroke_start(S, aid, c):
    for s in _segs(S, aid):
        if s.event == _ev(c) and s.tag == 'stroke': return float(s.t0)
    return c.t

def _string_top(S, sid):
    s = S.layout['strings'][sid]
    if 'neck' in s: return float(s['neck']['bridge'][1])
    return max(float(s['a'][1]), float(s['b'][1]))

def _tool_off(S, aid):
    """The arm_capsules 'tool' capsule's far end relative to the tip."""
    cfg = S.cfg(aid)
    return CL.shank_path([0, .07, 0], CL.tool_mount(R.Rig.wrist_offset(cfg), cfg['o2']), count=25)[12]

def _at(S, kinds, T, aid=None):
    out = []
    for a in S.arms:
        if S.kind(a) not in kinds or (aid and a != aid): continue
        out += [c for c in S.contacts(a) if abs(c.t-T) <= TIME_TOL]
    return out

def _dedupe(cs):
    seen = {}
    for c in cs: seen[(c.aid, c.i)] = c
    return sorted(seen.values(), key=lambda c: (c.t, c.aid))

def harp_ends(S):
    """The goal's listed harp phrase ends, as scored contacts."""
    cs = []
    for T, aid in HARP_ENDS: cs += _at(S, ('pick',), T, aid)
    a0, lo, hi = HARP_TOLLS
    if a0 in S.arms: cs += [c for c in S.contacts(a0) if lo-TIME_TOL <= c.t < hi-TIME_TOL]
    return _dedupe(cs)

def _sounding(S, c):
    """How long a phrase's last note sounds: its ring, cut by the arm's next contact or the end."""
    nxt = c.t+c.ioi_next if math.isfinite(c.ioi_next) else S.total
    return float(min(float(c.event.get('dur', 0.0)), nxt-c.t_end))

def _rank_corr(T, dur):
    """(rho, why): Spearman on times rounded to 1 ms (float noise must not rank),
    or None with the reason it cannot be judged (fewer than 3 phrase ends, or
    last notes that all sound alike) — reported as info, not gated."""
    T = np.round(np.asarray(T, float), 3); dur = np.round(np.asarray(dur, float), 3)
    if len(T) < 3: return None, f'{len(T)} phrase end(s): too few to rank'
    if np.ptp(dur) == 0: return None, f'the last notes all sound {dur[0]:.3g} s: the rank correlation is undefined'
    if np.ptp(T) == 0: return 0.0, 'release time is constant: it ignores how long the note sounds'
    return core.spearman(T, dur), ''

# ---- the pluck (12, 13, 23) ----------------------------------------------------------

def _shapes(S):
    """{clip id: (rate_hz, frames x nodes array)} from score.json + shapes.f32, or None."""
    def build():
        sh = S.score.get('shapes')
        if not sh: return None
        path = S.score_path.parent/sh['file']
        if not path.exists(): return None
        data = np.fromfile(path, '<f4')
        return {c['id']: (float(c['rate_hz']), data[c['offset']:c['offset']+c['nodes']*c['frames']].reshape(c['frames'], c['nodes']))
                for c in sh['clips']}
    return _memo(S, 'shapes', build)

def _catmull(vals, u):
    """wire_string.gdshader node_value: Catmull-Rom between the clip's nodes."""
    n = len(vals); k = min(max(u, 0.0), 1.0)*(n-1); i = int(math.floor(k)); j = min(i+1, n-1); f = k-i
    p0, p1, p2, p3 = vals[max(i-1, 0)], vals[i], vals[j], vals[min(j+1, n-1)]
    return .5*((2*p1)+(-p0+p2)*f+(2*p0-5*p1+4*p2-p3)*f*f+(-p0+3*p1-3*p2+p3)*f*f*f)

def _hits(S):
    """performance.gd's `hits`: per string, (t, event) for every event that
    names it, a sweep's k-th string at t + k*spread."""
    def build():
        out = {}
        for e in S.score['events']:
            sp = float(e.get('spread_s', 0))
            for k, sid in enumerate(e.get('strings', [])): out.setdefault(sid, []).append((float(e['t'])+k*sp, e))
        return out
    return _memo(S, 'hits', build)

def _drawn(S, sid, T, u):
    """The string's drawn displacement d at time T and node fraction u, as
    performance.gd sums it (every hit with 0 <= tau <= 5 s, frame int(tau*rate)
    of its shape clip, gain amp*0.035) and wire_string.gdshader bends it (local
    (cross_axis, 0, 1)*d). None when the score carries no clips."""
    shapes = _shapes(S)
    if not shapes: return None
    total = 0.0
    for th, e in _hits(S).get(sid, ()):
        tau = T-th
        if tau < 0 or tau > 5 or e.get('shape') is None or e['shape'] not in shapes: continue
        rate, clip = shapes[e['shape']]; fi = int(tau*rate)
        if fi >= len(clip): continue
        total += float(e['amp'])*GAIN*float(_catmull(clip[fi], u))
    return total

def _pluck(S, aid, c):
    f = S.fn(aid, 'tip'); t = c.t; cpt = c.point
    cs = S.contacts(aid); prev_end = cs[c.i-1].t_end if c.i > 0 else -math.inf
    vm = deriv(f, t, -1); vp = deriv(f, t, +1)
    # p(t-): the left limit, f(t - LEFT) with its first-order term put back
    pm = np.asarray(f(t-LEFT), float)+LEFT*vm; d = pm-cpt; d_rel = float(np.linalg.norm(d))
    if d_rel > 1e-6: n = d/d_rel
    elif np.linalg.norm(vm) > 1e-9: n = _unit(vm)
    else: n = -c.normal
    kn = [k for k in S.declared(aid).knots if k.event == _ev(c)]
    place = next((k for k in kn if k.kind == 'place'), None); slip = next((k for k in kn if k.kind == 'slip'), None)
    t_place_decl = float(place.t) if place else t
    d_decl = float(slip.extra.get('d_rel', 0.0)) if slip else 0.0
    n_decl = np.asarray(slip.extra.get('n', n), float) if slip else n
    err_place = float(np.linalg.norm(np.asarray(f(t_place_decl))-cpt))
    err_slip = float(np.linalg.norm(pm-(cpt+d_decl*n_decl)))
    lo = max(prev_end, t-2.0)
    tip_end = cpt+d_rel*n
    t_place = _back(lambda u: _pt_seg(f(u), cpt, tip_end) <= TOL_RAY, t-LEFT, lo)
    t_cm = _back(lambda u: np.linalg.norm(np.asarray(f(u))-cpt) <= .01, t-LEFT, lo)
    v_place = float(np.linalg.norm(deriv(f, t_place, -1)))
    # The drawn string at the contact point (u = the event's pick along a->b),
    # as a world vector d*(cross_axis*x + z) of the string's link basis.
    e = c.event; sid = e['strings'][0]; s = S.layout['strings'][sid]
    u_pick = float(e.get('pick', s['pick']))
    bx, by, bz = CL.link_basis(np.asarray(s['a'], float)[None], np.asarray(s['b'], float)[None])
    axis = CROSS_AXIS*bx[0]+bz[0]
    jump = stick_gap = defl = d_frame = None
    if _drawn(S, sid, t, u_pick) is not None:
        # string vs pad: through the stick (pad - c against the drawn string) and
        # at the slip, where the free string's first drawn shape (tau = 0) must
        # continue from the pad's p(t-) - c = d_rel*n_hat
        su = np.linspace(t_place, t-LEFT, 5) if t-t_place > 2*LEFT else np.array([t-LEFT])
        stick_gap = max(float(np.linalg.norm(_drawn(S, sid, u, u_pick)*axis-(np.asarray(f(u), float)-cpt))) for u in su)
        jump = float(np.linalg.norm(_drawn(S, sid, t, u_pick)*axis-d))
        # the release frame: the film frame whose interval (t_{k-1}, t_k] holds t
        k = _frame(t); d_frame = _drawn(S, sid, k/FPS, u_pick)
        defl = _deg(axis*np.sign(d_frame), n) if abs(d_frame) > 1e-12 else None
    return dict(i=c.i, t=t, sid=sid, n=n, d_rel=d_rel, vm=vm, vp=vp, err_place=err_place, err_slip=err_slip,
                t_place=t_place, stick=t-t_place, dwell=t-t_cm, v_place=v_place,
                polar=math.degrees(math.asin(min(1.0, abs(float(n[2]))))),
                dv=float(np.linalg.norm(vp-vm)), vn=float(vm@n), v_out=float(np.linalg.norm(vp)),
                release=float(c.sched['t_free'])-c.t_end, jump=jump, stick_gap=stick_gap, d_frame=d_frame, defl=defl)

def _plucks(S, aid):
    return _memo(S, ('plucks', aid), lambda: [_pluck(S, aid, c) for c in S.contacts(aid) if c.kind == 'pluck'])

def pluck(S):
    out = []
    for aid in S.arms_of('pick'):
        P = _plucks(S, aid)
        if not P:
            out.append(Result(12, 'pluck', aid, dict(plucks=0), None, 'no plucks on this arm')); continue
        g = lambda k: np.array([p[k] for p in P], float)
        stick = g('stick'); drel = g('d_rel'); pol = g('polar'); dv = g('dv'); vn = g('vn')
        ex = max(g('err_place').max(), g('err_slip').max())
        out.append(Result(12, '12 exact', aid, dict(place_err_m=_r(g('err_place').max()), slip_err_m=_r(g('err_slip').max()),
                                                     n=len(P)), bool(ex <= EXACT),
                          'no declared place/slip knots: the contact t is both (tip_at(t) vs the contact)'))
        out.append(Result(12, '12 stick', aid, dict(stick_ms=_st(stick, 1e3)), bool(stick.min() >= .056),
                          'no stick: the pad crosses the 0.5 mm tolerance at the approach speed' if stick.max() < .002 else ''))
        drel = np.where(drel < EXACT, 0.0, drel)          # below the rig's 1e-9 m: zero
        out.append(Result(12, '12 d_rel', aid, dict(d_rel_mm=_st(drel, 1e3)), bool(((drel >= .012) & (drel <= .030)).all()),
                          'the pad stops at the string: no load' if drel.max() < 1e-4 else ''))
        out.append(Result(12, '12 polarisation', aid, dict(deg=_st(pol)), bool(((pol >= 7) & (pol <= 43)).all()),
                          'n_hat = the approach direction (no load)' if drel.max() < 1e-6 else ''))
        out.append(Result(12, '12 slip velocity', aid, dict(dv=_st(dv), vn_in=_st(vn), v_out=_st(g('v_out'))),
                          bool((dv <= .05).all() and ((vn >= .2) & (vn <= 2.0)).all()),
                          'v(t-) along n_hat -> v(t+); a dead stop is |dv| = |v(t-)|'))
        out.append(Result(12, '12 closing', aid, dict(release_ms=_st(g('release'), 1e3)), None,
                          'n/a: no digits, no MCP (the tool retracts on a quintic instead)'))
        Q = [p for p in P if p['jump'] is not None]
        if Q:
            jump = np.array([p['jump'] for p in Q]); gap = np.array([p['stick_gap'] for p in Q])
            out.append(Result(12, '12 string', aid, dict(slip_jump_mm=_st(jump, 1e3), stick_gap_mm=_st(gap, 1e3), n=len(Q)),
                              bool((jump <= TOL_RAY).all() and (gap <= TOL_RAY).all()),
                              'drawn string (performance.gd hits, wire_string.gdshader bend) vs the pad: during '
                              '[t_place, t-] and at t, where the free clip starts at amp*35 mm x shape while the pad '
                              'is at p(t-) = c + d_rel n_hat; the clip (free string) starts at t'))
            Df = [p for p in Q if p['defl'] is not None]; defl = np.array([p['defl'] for p in Df])
            out.append(Result(12, '12 deflection', aid, dict(deg=_st(defl), along_n=int((defl < 90).sum()),
                                                             against_n=int((defl >= 90).sum()), cross_axis=CROSS_AXIS),
                              bool(len(Df) == len(Q) and (defl <= 5).all()),
                              'the drawn deflection at the release frame (k = ceil(30 t), clip frame int(120 tau)) is '
                              '+-(0.35 x + z) of the string basis: 19.3 deg off n_hat when it swings along it, 160.7 '
                              'against; Godot not run'))
        else:
            out.append(Result(12, '12 string', aid, {}, None, 'no shape clips in this score'))
    return out

# ---- place, plant, slide, raise (13) -------------------------------------------------

def _raise(S, aid, c):
    f = S.fn(aid, 'tip')
    t_next = _next_motion(S, aid, c.t_end)
    t1 = min(t_next, c.t+1.5, S.total)
    p0 = np.asarray(f(c.t), float); p1 = np.asarray(f(t1), float); D = p1-p0
    horiz = math.hypot(D[0], D[2])
    lean = math.degrees(math.atan2(horiz, D[1])) if horiz > 1e-9 or abs(D[1]) > 1e-9 else 0.0
    need = max(0.0, min(.4, _string_top(S, c.event['strings'][-1])-p0[1]))
    T = _park(S, aid, c.t_end, t_next)-c.t_end
    return dict(aid=aid, t=c.t, rise=float(D[1]), need=need, lean=lean, toward=bool(D[2] < 0),
                T=T, hold=max(0.0, t1-(c.t_end+T)), y_end=float(p1[1]), t_start=c.t_end, dur=_sounding(S, c),
                ok=bool(D[1] >= need-1e-9 and 15 <= lean <= 35 and D[2] < 0 and .3 <= T <= 1.5))

def _raises(S):
    return _memo(S, 'raises', lambda: [_raise(S, c.aid, c) for c in harp_ends(S)])

def _raise_result(n, name, aid, rs, note):
    g = lambda k: np.array([r[k] for r in rs], float)
    return Result(n, name, aid, dict(n=len(rs), rise_m=_st(g('rise')), need_m=_r(g('need').min()), lean_deg=_st(g('lean')),
                                     toward_arm=bool(all(r['toward'] for r in rs)), T_s=_st(g('T')), hold_s=_st(g('hold'))),
                  bool(all(r['ok'] for r in rs)), note)

def place(S):
    out = []; ends = {(c.aid, c.i) for c in harp_ends(S)}
    for aid in S.arms_of('pick'):
        P = _plucks(S, aid); cs = S.contacts(aid)
        if P:
            v = np.array([p['v_place'] for p in P]); dw = np.array([p['dwell'] for p in P])
            out.append(Result(13, '13 place', aid, dict(v_place=_st(v), dwell_1cm_ms=_st(dw, 1e3)), bool((v <= .2).all()),
                              'the tool lands at the approach speed; the dwell is its time within 1 cm before t'))
        out.append(Result(13, '13 place group', aid, {}, None, 'n/a: no digits (one plectrum cannot place a group)'))
        out.append(Result(13, '13 place order', aid, {}, None, 'n/a: no digits'))
        byi = {p['i']: p for p in P}; lag = []
        for lo, hi in RUNS:
            run = [c for c in cs if lo-TIME_TOL <= c.t <= hi+TIME_TOL and c.kind == 'pluck']
            lag += [byi[b.i]['t_place']-a.t for a, b in zip(run, run[1:]) if b.i in byi]
        if lag:
            lag = np.array(lag)
            out.append(Result(13, '13 place run', aid, dict(lag_ms=_st(lag, 1e3)), bool((lag <= 1/FPS).all()),
                              't_place - previous slip (today the previous contact) in the listed runs'))
        out.append(Result(13, '13 plant', aid, {}, None, 'n/a: no digits to plant'))
        # slide: waits >= 1 s inside a phrase
        Pz = S.poses(aid, 'hz'); th = Pz['t']; tip = Pz['tip']; waits = []
        for a, b in zip(cs, cs[1:]):
            if b.t-a.t_end < 1.0 or (aid, a.i) in ends: continue
            # the wait proper: from the previous gesture's end (its release, t_free) to t_place
            t1 = byi[b.i]['t_place'] if b.i in byi else b.t
            m = (th >= float(a.sched['t_free'])) & (th < t1)
            if not m.any(): continue
            dist = np.full(m.sum(), np.inf)
            for sid in set(a.event['strings'])|set(b.event['strings']):
                s = S.layout['strings'][sid]
                dist = np.minimum(dist, _pt_seg(tip[m], np.asarray(s['a'], float), np.asarray(s['b'], float)))
            at = dist <= TOL_RAY
            waits.append(dict(len=b.t-a.t_end, at=at.sum()/HZ, y=float(np.ptp(tip[m][at, 1])) if at.any() else 0.0,
                              off=float(np.median(dist))))
        if waits:
            y = np.array([w['y'] for w in waits])
            out.append(Result(13, '13 slide', aid, dict(waits=len(waits), longest_s=_r(max(w['len'] for w in waits)),
                                                        at_string_s=_r(sum(w['at'] for w in waits)), slide_m=_st(y),
                                                        off_string_mm=_st([w['off'] for w in waits], 1e3)),
                              bool(((y >= .10) & (y <= .15)).all()),
                              'the tool hovers off the string through every wait' if y.max() == 0 else ''))
        rs = [r for r in _raises(S) if r['aid'] == aid]
        if rs:
            out.append(_raise_result(13, '13 raise', aid, rs,
                                     'digits-clear and knuckle-line drift n/a (no digits); today the tool retracts along -z'))
    # a group placed across hands: the final chord, "placed together" (one plectrum a hand today)
    fc = [(aid, p) for aid in S.arms_of('pick') for p in _plucks(S, aid) if abs(p['t']-FINAL_CHORD) <= TIME_TOL]
    if len(fc) >= 2:
        tp = np.array([p['t_place'] for _, p in fc])
        out.append(Result(13, '13 place group', 'pick', dict(group='final chord', hands=len(fc), spread_ms=_r(np.ptp(tp)*1e3)),
                          bool(np.ptp(tp) <= 1/BAKE_HZ+1e-12), 'the final chord\'s landings (t_place) across the three hands, '
                          'against one bake row (1/240 s)'))
    rs = _raises(S)
    if rs:
        rho, why = _rank_corr([r['T'] for r in rs], [r['dur'] for r in rs])
        out.append(Result(13, '13 raise spearman', 'pick', dict(rho=_r(rho) if rho is not None else None, n=len(rs),
                                                                dur_s=sorted({_r(r['dur']) for r in rs}),
                                                                T_s=sorted({_r(r['T']) for r in rs})),
                          core.INFO if rho is None else bool(rho >= .8), why))
    chord = [r for r in rs if abs(r['t']-FINAL_CHORD) <= TIME_TOL]
    if len(chord) >= 2:
        skew = (max(r['t_start'] for r in chord)-min(r['t_start'] for r in chord))*FPS
        spread = max(r['y_end'] for r in chord)-min(r['y_end'] for r in chord)
        out.append(Result(13, '13 final chord', 'pick', dict(hands=len(chord), start_skew_frames=_r(skew), end_spread_cm=_r(spread*100)),
                          bool(skew <= 1+1e-9 and spread <= .01), 'raise starts (t_end) and the heights at t_raise_end'))
    return out

# ---- strum (14) --------------------------------------------------------------------

def _follow(f, t_end, thr, t_stop, dt=1e-3):
    """Arc length from t_end until |v| <= thr (or t_stop)."""
    if np.linalg.norm(deriv(f, t_end, +1)) <= thr: return 0.0
    s = 0.0; u = t_end; p = np.asarray(f(u))
    while u < t_stop:
        u2 = min(u+dt, t_stop); p2 = np.asarray(f(u2)); s += float(np.linalg.norm(p2-p))
        if np.linalg.norm(deriv(f, u2, +1)) <= thr: break
        u, p = u2, p2
    return s

def _sweep(S, aid, c):
    f = S.fn(aid, 'path'); e = c.event; ids = e['strings']
    pts = [S.rig.contact(sid, e.get('pick')) for sid in ids]
    L = float(sum(np.linalg.norm(b-a) for a, b in zip(pts, pts[1:]))); T = c.t_end-c.t
    v_sw = L/T if T > 0 else math.inf
    vm = deriv(f, c.t, -1); vp = deriv(f, c.t, +1)
    ts = np.linspace(c.t, c.t_end, max(int(T/5e-4), 2), endpoint=False)
    sp = np.array([np.linalg.norm(deriv(f, u, +1)) for u in ts])
    t_next = _next_motion(S, aid, c.t_end)
    ft = _follow(f, c.t_end, .1*v_sw, min(t_next, c.t_end+2.0, S.total))
    t0 = _stroke_start(S, aid, c); t_free = float(c.sched['t_free'])
    corners = dict(before=0, entry=0, inner=0, exit=0, after=0); worst_ang = worst_dv = 0.0
    for tk in _knot_times(S, aid):
        if tk < t0-1e-9 or tk > t_free+1e-9: continue
        a, b = deriv(f, tk, -1), deriv(f, tk, +1); na, nb = np.linalg.norm(a), np.linalg.norm(b)
        ang = _deg(a, b) if na > 1e-6 and nb > 1e-6 else 0.0; dsp = abs(nb-na)
        worst_ang = max(worst_ang, ang); worst_dv = max(worst_dv, dsp)
        if ang > 2 or dsp > .05:
            where = 'before' if tk < c.t-1e-9 else 'entry' if tk <= c.t+1e-9 else 'inner' if tk < c.t_end-1e-9 \
                else 'exit' if tk <= c.t_end+1e-9 else 'after'
            corners[where] += 1
    return dict(t=c.t, L=L, v_sw=v_sw, v_in=float(np.linalg.norm(vm)), v_out=float(np.linalg.norm(vp)),
                entry=float(np.linalg.norm(vm))/v_sw, ratio=float(sp.max()/max(sp.min(), 1e-12)), vmax=float(sp.max()),
                vmin=float(sp.min()), follow=ft, corners=corners, ang=worst_ang, dsp=worst_dv, t0=t0, t_free=t_free)

def _sweeps(S, aid):
    return _memo(S, ('sweeps', aid), lambda: [_sweep(S, aid, c) for c in S.contacts(aid) if c.kind == 'sweep'])

def _carriage(S, aid):
    fx = lambda u: np.array([S.rig.pose(aid, u)['root'][0]])
    knots = _knot_times(S, aid); vmax = amax = 0.0; t_v = t_a = None
    for s in _segs(S, aid):
        if s.tag == 'hold' or not math.isfinite(s.t1) or s.t1-s.t0 < 1e-6: continue
        ts = np.arange(s.t0, s.t1, 1e-3)
        xs = np.array([fx(u)[0] for u in np.append(ts, s.t1)])
        v = np.abs(np.diff(xs))/np.diff(np.append(ts, s.t1))
        k = int(np.argmax(v))
        if v[k] > vmax: vmax, t_v = float(v[k]), float(ts[k])
        for u in ts:
            j = np.searchsorted(knots, u-1e-9)
            if j < len(knots) and knots[j] <= u+5e-5: continue
            a = abs(float(deriv(fx, u, +1, 2)[0]))
            if a > amax: amax, t_a = a, float(u)
    steps = [abs(float(deriv(fx, tk, +1)[0]-deriv(fx, tk, -1)[0])) for tk in knots if math.isfinite(tk)]
    return dict(vmax=vmax, t_v=t_v, amax=amax, t_a=t_a, step=max(steps) if steps else 0.0)

def strum(S):
    out = []
    for aid in S.arms_of('rake'):
        W = _sweeps(S, aid)
        if not W:
            out.append(Result(14, 'strum', aid, dict(sweeps=0), None, 'no sweeps on this arm')); continue
        g = lambda k: np.array([w[k] for w in W], float)
        ent = g('entry'); ft = g('follow'); rat = g('ratio')
        out.append(Result(14, '14 entry', aid, dict(ratio=_st(ent), v_in=_st(g('v_in')), v_out=_st(g('v_out')),
                                                    v_sweep=_st(g('v_sw'))), bool(ent.min() >= .7),
                          '|v(t_hit-)| / (L_path/(t_end-t_hit)); v_out = |v(t_hit+)|'))
        out.append(Result(14, '14 follow-through', aid, dict(m=_st(ft)), bool(ft.min() >= .2),
                          'the sweep stops dead at its last string' if ft.max() == 0 else ''))
        tot = {k: sum(w['corners'][k] for w in W) for k in W[0]['corners']}
        out.append(Result(14, '14 corners', aid, dict(count=sum(tot.values()), **tot, max_deg=_r(g('ang').max()),
                                                      max_dspeed=_r(g('dsp').max())), sum(tot.values()) == 0,
                          'declared knots from each sweep\'s stroke start to t_free'))
        out.append(Result(14, '14 speed ratio', aid, dict(ratio=_st(rat), vmax=_r(g('vmax').max()), vmin=_r(g('vmin').min())),
                          bool(rat.max() <= 1.2), 'max/min |v| along [t_hit, t_end]'))
        P = S.poses(aid, 'frames'); tip = P['tip']; th = P['t']; off = _tool_off(S, aid)
        dp = np.diff(tip, axis=0); mag = np.linalg.norm(dp, axis=1)
        dhat = dp/np.where(mag > 1e-12, mag, 1)[:, None]
        rho = mag/(2*TOOL_R+np.abs(dhat@off)); k = int(np.argmax(rho))
        insweep = np.zeros(len(rho), bool)
        for w in W: insweep |= (th[1:] > w['t0']) & (th[:-1] < w['t_free'])
        out.append(Result(14, '14 rho', aid, dict(max=_r(rho[k]), t=_r(th[k+1]), frames_over_1=int((rho > 1).sum()),
                                                  sweep_max=_r(rho[insweep].max()) if insweep.any() else None,
                                                  max_at_019=_r((mag/PICK_D).max())),
                          bool(rho.max() <= 1.0), 'E = the arm_capsules tool capsule (2r + |seg.d|), every frame'))
        lim = R.SERVO_V_MAX if S.cfg(aid).get('hand') else 6.0
        cr = _carriage(S, aid)
        out.append(Result(14, '14 carriage', aid, dict(v_max=_r(cr['vmax']), t_v=_r(cr['t_v']), a_max_g=_r(cr['amax']/G),
                                                       t_a=_r(cr['t_a']), dv_step=_r(cr['step']), v_limit=lim),
                          bool(cr['vmax'] <= lim and cr['amax'] <= 3*G and cr['step'] <= .05),
                          'a_max inside segments; dv_step = the largest velocity step at a knot (unbounded acceleration)'))
    return out

# ---- no penetration (23) -------------------------------------------------------------

def _sd_box(P, c, half):
    q = np.abs(P-c)-half
    return np.linalg.norm(np.maximum(q, 0.0), axis=-1)+np.minimum(q.max(axis=-1), 0.0)

def _sd_cyl(P, c, R_, half_h):
    d = P-c; q = np.stack([np.hypot(d[..., 0], d[..., 2])-R_, np.abs(d[..., 1])-half_h], -1)
    return np.linalg.norm(np.maximum(q, 0.0), axis=-1)+np.minimum(q.max(axis=-1), 0.0)

def _struck_elements(S, mid):
    """[(sid, sd(P))] for the instrument's bars, blocks or bells as
    tools/build_clockwork.py builds them (the a-b line is the top surface)."""
    mech = next((m for m in S.score['instrument']['mechanisms'] if m['id'] == mid), None)
    if mech is None: return []
    n = len(mech['strings']); w = min(.24, float(mech['span'])*3/n*.7); mat = mech.get('material', '')
    out = []
    for sid, s in S.layout['strings'].items():
        if s['mid'] != mid or not s['struck']: continue
        a = np.asarray(s['a'], float); b = np.asarray(s['b'], float); c = (a+b)/2; L = float(np.linalg.norm(b-a))
        if mat == 'glass':
            out.append((sid, lambda P, c=c: _sd_cyl(P, c+[0, -.0225, 0], .12, .0225)))
        else:
            half = np.array([w/2, BAR['thick']/2, L/2]); fns = [lambda P, c=c, h=half: _sd_box(P, c+[0, -BAR['thick']/2, 0], h)]
            if mat == 'wood':
                fns.append(lambda P, c=c: _sd_box(P, c+[0, .001, .07], np.array([.095, .003, .009])))
            out.append((sid, lambda P, fs=fns: np.min([fn(P) for fn in fs], axis=0)))
    return out

def _head_centres(S, aid, tip, felt):
    if S.kind(aid) == 'hammer':
        head = S.cfg(aid).get('head') or {}
        L = float(head.get('length', R.HAMMER['head_l'])); hr = R.HAMMER['head_r']
        hinge = tip+[0, L, 0]; dirs = (felt-hinge)/L
        return felt-dirs*hr, hr
    return tip+[0, HEAD_R, 0], HEAD_R

def _heads(S, aid):
    els = _struck_elements(S, S.mech(aid))
    if not els: return Result(23, '23 head', aid, {}, None, 'no struck elements found for this instrument')
    P = S.poses(aid, 'hz'); times = list(P['t']); tip = list(P['tip']); felt = list(P['felt'])
    for c in S.contacts(aid):
        q = S.rig.pose(aid, c.t); times.append(c.t); tip.append(q['tip']); felt.append(q['felt'])
    times = np.array(times); centre, r = _head_centres(S, aid, np.array(tip), np.array(felt))
    best = (math.inf, None, None)
    for sid, fn in els:
        sd = fn(centre)-r; k = int(np.argmin(sd))
        if sd[k] < best[0]: best = (float(sd[k]), float(times[k]), sid)
    return Result(23, '23 head', aid, dict(min_mm=_r(best[0]*1e3), t=_r(best[1], 6), element=best[2], samples=len(times)),
                  bool(best[0] >= -EXACT), 'core sphere vs every bar/block/bell, 120 Hz + every contact instant')

def _tool_strings(S, aid):
    strings = {sid: s for sid, s in S.layout['strings'].items() if s['mid'] == S.mech(aid) and not s['struck']}
    if not strings: return [Result(23, '23 tool', aid, {}, None, 'no strings on this instrument')]
    sids = list(strings); A = np.array([strings[s]['a'] for s in sids], float); B = np.array([strings[s]['b'] for s in sids], float)
    rs = np.array([wire_radius(strings[s]['midi']) for s in sids])
    cs = S.contacts(aid); byi = {p['i']: p for p in _plucks(S, aid)}
    P = S.poses(aid, 'hz'); times = np.concatenate([P['t'], [c.t for c in cs]])
    tip = np.concatenate([P['tip'], np.array([S.tip(aid, c.t) for c in cs]).reshape(-1, 3)])
    off = _tool_off(S, aid)
    sd = CL.segment_distance(tip[:, None, :], (tip+off)[:, None, :], A[None], B[None])-TOOL_R-rs[None]
    exempt = np.zeros(sd.shape, bool); near = np.zeros(sd.shape, bool)
    col = {s: j for j, s in enumerate(sids)}
    for c in cs:
        js = [col[s] for s in c.event['strings'] if s in col]
        t0 = byi[c.i]['t_place'] if c.i in byi else c.t
        m = (times >= t0-1e-12) & (times <= c.t_end+1e-12)
        for j in js: exempt[m, j] = True
        m2 = (times >= c.t-.25) & (times <= c.t_end+.25)
        for j in js: near[m2, j] = True
    live = np.where(exempt, np.inf, sd)
    k, j = np.unravel_index(int(np.argmin(live)), live.shape)
    played = np.where(near, live, np.inf); other = np.where(near, np.inf, live)
    inside = 0
    for c in cs:
        m = (times >= c.t-.25) & (times <= c.t_end+.25); js = [col[s] for s in c.event['strings'] if s in col]
        if m.any() and js and (played[m][:, js] < 0).any(): inside += 1
    res = [Result(23, '23 tool', aid, dict(min_mm=_r(live[k, j]*1e3), t=_r(times[k], 6), string=sids[j],
                                           played_min_mm=_r(played.min()*1e3), other_min_mm=_r(other.min()*1e3),
                                           contacts_inside=inside, contacts=len(cs)),
                  bool(live[k, j] >= 0),
                  'arm_capsules tool capsule (r 30 mm) vs every string; exempt: the played string during its stick, '
                  'the swept strings during [t_hit, t_end]')]
    # the plectrum's own blade at each contact instant (the clearance.report exemption hides this)
    sd_b = []; ov = []
    hb = np.linspace(0, BLADE['h'], 15); hts = BLADE['t']/2*(.35+.65*hb/BLADE['h'])
    for c in cs:
        e = c.event; sp = float(c.sched['spread'])
        for k2, sid in enumerate(e['strings']):
            if sid not in col: continue
            tc = c.t+k2*sp if len(e['strings']) > 1 and sp > 0 else c.t
            p = np.asarray(S.tip(aid, tc), float); s = strings[sid]; a = np.asarray(s['a'], float); b = np.asarray(s['b'], float)
            r_s = wire_radius(s['midi'])
            d = _pt_seg(p+hb[:, None]*[0, 1, 0], a, b)-hts-r_s
            sd_b.append(float(d.min())); ov.append(float((d < 0).mean()*BLADE['h']))
    if sd_b:
        sd_b = np.array(sd_b)
        res.append(Result(23, '23 blade', aid, dict(min_mm=_r(sd_b.min()*1e3), inside=int((sd_b < 0).sum()), contacts=len(sd_b),
                                                    overlap_mm=_st(ov, 1e3)),
                          bool((sd_b >= 0).all()),
                          'the 7 mm plectrum blade (linkage.pick_tool) vs the played string at each contact instant; '
                          'the string runs inside it (clearance.report never tests the tool)'))
    return res

def penetration(S):
    out = []
    for aid in S.arms:
        k = S.kind(aid)
        if k in ('mallet', 'hammer'): out.append(_heads(S, aid))
        elif k in ('pick', 'rake'): out += _tool_strings(S, aid)
    return out

# ---- phrase ends (24) ----------------------------------------------------------------

def _apex_tempo(S, aid):
    f = S.fn(aid, 'path'); cs = S.contacts(aid); ap = []
    for a, b in zip(cs, cs[1:]):
        if not (TEMPO[0]-TIME_TOL <= b.t <= TEMPO[1]+TIME_TOL) or b.ioi > .5: continue
        ts = np.arange(a.t_end, b.t, 1/HZ)
        if len(ts): ap.append(max(float((np.asarray(f(u))-b.point)@b.normal) for u in ts))
    if not ap:
        for a, b in zip(cs, cs[1:]):
            ts = np.arange(a.t_end, b.t, 1/HZ)
            if len(ts): ap.append(max(float((np.asarray(f(u))-b.point)@b.normal) for u in ts))
    return float(np.median(ap)) if ap else None

def _next_strike(S, aid, t):
    """The next note's own start after t (its stroke, wind-up, fall or place),
    or inf: the travel between phrases belongs to this phrase end's window."""
    for s in _segs(S, aid):
        if s.t0 > t+1e-9 and s.tag in ('stroke', 'wind-up', 'fall', 'place') and s.t1 > s.t0: return float(s.t0)
    return math.inf

def _mallet_end(S, aid, c, apex):
    f = S.fn(aid, 'path'); t_next = _next_strike(S, aid, c.t_end); t_stop = min(t_next, S.total)
    ts = np.arange(c.t_end, t_stop, 1/HZ)
    h = np.array([float((np.asarray(f(u))-c.point)@c.normal) for u in ts]); w = int(round(3*HZ/FPS))
    if len(h) > w:
        win = np.lib.stride_tricks.sliding_window_view(h, w+1).min(axis=1); k = int(np.argmax(win)); held = float(win[k])
        lift = float(h[k+w:].max()-held)
    else: held = float(h.min()) if len(h) else 0.0; lift = 0.0; k = 0
    need = 1.5*apex if apex is not None else math.nan
    T = _park(S, aid, c.t_end, t_next)-c.t_end
    return dict(aid=aid, t=c.t, held=held, need=need, lift=lift, T=T, dur=_sounding(S, c),
                ok=bool(apex is not None and held >= need and len(h) > w and lift > .01))

def _rake_end(S, aid, c):
    f = S.fn(aid, 'path'); t_next = _next_motion(S, aid, c.t_end); t1 = min(t_next, c.t_end+1.5, S.total)
    D = np.asarray(f(t1))-np.asarray(f(c.t_end)); ang = math.degrees(math.atan2(math.hypot(D[0], D[2]), D[1]))
    sw = next((w for w in _sweeps(S, aid) if abs(w['t']-c.t) < 1e-9), None)
    ft = sw['follow'] if sw else 0.0; T = _park(S, aid, c.t_end, t_next)-c.t_end
    return dict(aid=aid, t=c.t, rise=float(D[1]), ang=ang, follow=ft, T=T, dur=_sounding(S, c),
                ok=bool(ft >= .2 and D[1] > 0 and ang <= 45))

def _hammer_end(S, aid, c):
    rest = S.rig.rest_angle(aid); t_next = _next_motion(S, aid, c.t_end); t1 = min(t_next, c.t_end+2.0, S.total)
    ts = np.arange(c.t_end, t1, 1e-3); th = np.array([S.rig.head_angle(aid, u) for u in ts])
    off = np.nonzero(np.abs(th-rest) > math.radians(1))[0]
    T = float(ts[off[-1]]+1e-3-c.t_end) if len(off) else 0.0
    d = np.diff(th); d = d[np.abs(d) > 1e-9]; rev = int((np.sign(d[1:]) != np.sign(d[:-1])).sum()) if len(d) > 1 else 0
    return dict(aid=aid, t=c.t, T=T, reversals=rev, dur=_sounding(S, c), ok=bool(T >= .3 and rev == 0))

def phrase_ends(S):
    out = []; per_kind = {}
    for aid in S.arms_of('pick'):
        rs = [r for r in _raises(S) if r['aid'] == aid]
        if rs:
            out.append(_raise_result(24, '24 release', aid, rs, 'the harp raise; today the tool retracts 0.22 m along -z and holds'))
            per_kind.setdefault('pick', []).extend(rs)
    for aid in S.arms_of('mallet'):
        cs = _dedupe([c for T in MALLET_ENDS for c in _at(S, ('mallet',), T, aid)])
        if not cs: continue
        apex = _apex_tempo(S, aid); rs = [_mallet_end(S, aid, c, apex) for c in cs]
        g = lambda k: np.array([r[k] for r in rs], float)
        out.append(Result(24, '24 release', aid, dict(n=len(rs), held_m=_st(g('held')), need_m=_r(rs[0]['need']),
                                                      tempo_apex_m=_r(apex) if apex is not None else None,
                                                      lift_m=_st(g('lift')), T_s=_st(g('T'))),
                          bool(all(r['ok'] for r in rs)),
                          'held raise (3 frames) vs 1.5 x tempo apex, then a lift; today the head returns to hover'))
        per_kind.setdefault('mallet', []).extend(rs)
    for aid in S.arms_of('rake'):
        cs = _dedupe([c for T in RAKE_ENDS for c in _at(S, ('rake',), T, aid)])
        if not cs: continue
        rs = [_rake_end(S, aid, c) for c in cs]; g = lambda k: np.array([r[k] for r in rs], float)
        out.append(Result(24, '24 release', aid, dict(n=len(rs), follow_m=_st(g('follow')), rise_m=_st(g('rise')),
                                                      angle_deg=_st(g('ang')), T_s=_st(g('T'))),
                          bool(all(r['ok'] for r in rs)), 'follow-through then an upward release (<= 45 deg from +y)'))
        per_kind.setdefault('rake', []).extend(rs)
    for aid in S.arms_of('hammer'):
        cs = S.contacts(aid)
        if not cs: continue
        r = _hammer_end(S, aid, cs[-1])
        out.append(Result(24, '24 release', aid, dict(n=1, t=_r(r['t']), T_s=_r(r['T']), reversals=r['reversals']),
                          r['ok'], 'the check back to rest after the last blow (slow: >= 0.3 s, monotone)'))
        per_kind.setdefault('hammer', []).append(r)
    for kind, rs in per_kind.items():
        rho, why = _rank_corr([r['T'] for r in rs], [r['dur'] for r in rs])
        out.append(Result(24, '24 spearman', kind, dict(rho=_r(rho) if rho is not None else None, n=len(rs),
                                                        dur_s=sorted({_r(r['dur']) for r in rs}), T_s=sorted({_r(r['T']) for r in rs})),
                          core.INFO if rho is None else bool(rho >= .8), why))
    out.append(_ending(S))
    return out

def _ending(S):
    chord = [r for r in _raises(S) if abs(r['t']-FINAL_CHORD) <= TIME_TOL]
    if not chord: return Result(24, '24 ending', 'all', {}, None, 'no final chord found at 78.57 s')
    skew = (max(r['t_start'] for r in chord)-min(r['t_start'] for r in chord))*FPS
    spread = max(r['y_end'] for r in chord)-min(r['y_end'] for r in chord)
    harp_end = max(r['t_start']+r['T'] for r in chord); hf = _frame(harp_end)
    parks = {aid: _last_motion_end(S, aid) for aid in S.arms if S.kind(aid) != 'pick'}
    frames = {aid: _frame(t) for aid, t in parks.items() if t is not None}
    sync = [frames[a] for a in frames if S.kind(a) in ('mallet', 'rake')]
    late = max((abs(fr-hf) for fr in frames.values()), default=0)
    ok = skew <= 1+1e-9 and spread <= .01 and (not sync or max(sync) == min(sync)) and late <= 1
    return Result(24, '24 ending', 'all', dict(harp_hands=len(chord), start_skew_frames=_r(skew), end_spread_cm=_r(spread*100),
                                               harp_end_frame=hf, park_frames=frames, worst_offset_s=_r(late/FPS)),
                  bool(ok), 'harp raise starts/heights; mallets+rake park in one frame; every release ends with the harp raise')

RULERS = {12: pluck, 13: place, 14: strum, 23: penetration, 24: phrase_ends}

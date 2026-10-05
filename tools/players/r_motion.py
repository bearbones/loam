"""Rulers 1, 3, 4, 5, 6, 9, 15 and 16 of docs/goals/the-players.md
("Acceptance"): the players' own motion, measured on the rig.

     1  strobe                  per-frame displacement against the part's own extent
     3  preparation             wind-up and lead before each contact
     4  action                  the closing phase
     5  no rest in a phrase     slow stretches must be turning points
     6  smoothness              6a knots, 6b corners, 6c jerk class, laws
     9  gravity scale           s = g/a per stroke
    15  proximal -> distal      peak order, shares, tip and carriage limits, phases
    16  joint use and limits    coverage, untagged path, reversals, limits

Signals. Three, each named where it is used:
  rendered  what the film shows: Rig.pose / tip_at, rings and all (rulers 1, 15)
  scored    the contact point without rings: Rig.path_at, plus for a hinged
            hammer the felt face at the head angle WITHOUT its check bounce (a
            declared ring, segments._rings_today) — `point_fn` (rulers 3, 4, 5, 9)
  path      Rig.path_at itself, the tool frame the declared segments describe
            (rulers 6 and 16's path; for the hammer the hinge is its own DOF)

Definitions where the goal leaves a choice (each also in its Result's note):
  1   Parts and extents mirror ruler 2 (r_screen.bodies): pick and rake tool =
      arm_capsules 'tool' (contact to the swan neck's apex, r 0.03); the mallet
      = its wound head, a sphere r 0.06 seated on the contact
      (linkage.mallet_tool; arm_capsules' generic 'tool' is the neck, r 0.03,
      and has no head); hammer = arm_capsules 'head' (the felt ball); wrist =
      bosses r 0.05 at the wrist pin and wrist+o2; elbow = bosses at elbow,
      elbow+o1, elbow+o2. E(part, d) = spread of the body points along d + 2r,
      the mean of the two frames'. Links: R.|dtheta| at the far end with R the
      link length, against max(link width 0.062 = arm_capsules' bar diameter,
      E_head along the end's swing direction). A hurried travel is a stepped
      arm's travel whose 3-4-5 minimum time max(sqrt(5.774 dx/3g), 1.875 dx /
      (E_head,x . 30/s)) exceeds its contact-to-contact window t_i - t_{i-1}
      (ruler 19's definition in r_strike.py; the first travel has none).
      A mallet that declares its carriage (PLAYERS M1) names its hurried
      travels (extra['hurried'] on its carriage 'travel' segments, the same
      rule in motion_timing.hurried); their windows run contact to contact.
      Impulse frames: frames holding an impulse knot or touching a click's
      move [t, t_end]; a freewheel tooth's click has no t_end (DESIGN 7.9).
      Mallet tool (the lead's amendment of the cell, decision (f)): the
      gated p95 is p95_gated, over active frames that are neither impulse
      frames, nor hurried, nor in a strike window [t_apex_i, t_i + 50 ms]
      (t_apex from `prep`), nor, while BRISK_UNTIL_M8 (the lead's explicit
      policy, built as 'hurried' is), in a BRISK travel: a contact travel at
      tempo whose 3-4-5 time at 3 g and 0.5 E_x a frame exceeds its IOI. The
      plan's travel together with the float cannot hold 0.5 E a frame there
      (no 3-4-5 over the IOI does today; the glide the plan picks seldom does),
      so the whole gap (previous contact's t_end -> contact), head included,
      leaves the gate until M8's splay changes replace these leaps (`brisk`);
      their count per arm may not grow past today's (TODAY_BRISK, the row
      '1 brisk'). BRISK_UNTIL_M8 = False gates those frames as written. The
      max rule holds on every frame. With active
      frames but none left after the gating, p95_gated is n/a (the gate
      reads no sample), not a pass; gated_share is the share of the active
      frames the gate kept. Info:
      p95_active as written; p95_noimpulse = p95 over active frames that are
      neither impulse frames nor hurried; p95_off also leaves out the frames
      within +-50 ms of a contact (DESIGN 7.8). Every other kind and part
      is gated on p95_active as written.
  3,4 h(t) on the scored signal, sampled every 1 ms plus every declared knot,
      segment end and law-internal joint, then each phase edge refined to
      10 us (coarse-to-fine on the secant signs) and snapped onto a breakpoint
      within 10 us. A stretch is still when |dh/dt| <= 1e-6 m/s. A rise that
      comes to rest at a breakpoint (a one-sided dh/dt <= 1e-4 m/s there, e.g.
      a release's end flowing into the strike's lift) ends W there: dh/dt > 0
      must hold throughout W. Arms with no contacts: n/a. Plucks: t_place does not exist yet, so t_i = t (today's
      poke reaches the string at t) and c_i = the contact point. Hand-offs:
      consecutive contacts of one mallet mechanism on different holders with
      the mechanism's IOI <= 0.6 s; the incoming wind-up must start at or
      before the outgoing holder's hit. Ruler 4 applies the pluck rule
      (approach >= 2.5 frames) to the rake's sweeps. A declared apex hold
      (DESIGN 7.1: a run of head-channel 'hold' segments ending at t_apex
      +-2 ms, a mallet's park and cocked hold) is skipped: W is the rise
      before it, L and the depth run from that rise's start. `prep` is the
      one apex and wind-up finder rulers 3, 4, 5, 8, 9, 10 and 21 share.
  5   On the scored signal at ~1 ms (the grid ends exactly on both contacts).
      The principal axis is the gap's first principal component. The
      "declared holds after gaps >= 0.8 s" exemption is read as ruler 21
      states such a hold: a declared hold at the apex, i.e. a 'hold' segment
      ending at the next contact's t_apex (+-2 ms), which must cover the slow
      stretch but for pieces of at most a frame (its own ease in and out).
      Today's rests end where the strike's wind-up begins, below the apex, so
      they are not exempt; `exempt_lenient` counts what any declared hold in
      such a gap would excuse. The rake pendulum is 45.71-67.14 s on either asset.
  6   6a and 6c on the path signal. 6a: one judgement per knot time
      (segments._today declares coincident smooth knots at a travel's end and
      the strike's start); a time with an impulse knot (contact, slip, detent)
      is judged as that impulse, any other (smooth, click, place) against
      |dv| <= 1e-3 m/s and |da| <= 0.05 a_peak, a_peak the larger of the
      adjoining segments' peaks, plus the stencil's rounding floor
      (_da_noise: 1e-3 m/s^2 + 2 x 26.7 eps (|p| + |v| t)/h^2, which a 28 m/s
      linear sweep at t ~ 50 s needs; two linear neighbours have a_peak 0).
      6b on the RENDERED contact point (rule 4: velocity jumps only at a
      declared impulse; its "what goes" names the |sine| bounce): the path
      is analytic between the points where path_at switches branch (the
      declared knots, the segment ends and the laws' internal joints:
      cocked's COCK_AT, the S-curve's ramps, the ratchet ring's fade), and
      the rings add their own corners (ring_corners: the |damped sine| zero
      crossings of the stepped mallet's recoil bounce and the hammer's
      check). 6b takes the one-sided 5-point dv at every one of those and
      counts |dv| > 0.02 m/s more than 20 us from an IMPULSE knot — a smooth
      knot does not excuse a corner. A 20 us dense scan of the rendered point
      (bars_arm0 47-48.5 s, blocks_arm0 24-25.6 s, bells_arm0 23.3-24.5 s)
      found no corner off that list. `off_knots` is the row's literal wording
      (more than 20 us from any declared knot); `at_knots_0.1` is the scratch
      baseline's count (path, every knot time, |dv| > 0.1 m/s: 476 on the
      chamber = the cell's 474 + harp_arm0's first pluck, whose strike starts
      at -0.09 s and lands at 0, at or before the bake's first sample).
      6c: a from central differences (+-0.1 ms) every 1 ms inside the
      segment; pairs straddling a declared knot are left to 6a. C_j h/T^3 is
      the law's closed-form max |jerk|: 3-4-5 60|D|/T^3; S-curve
      6/(r^2(1-r))|D|/T^3; linear 0; 'quintic+sine' and 'quintic+cocked' as
      max_u |Q q'''(u) + L s'''(u)|/T^3 with Q, L recovered from the path at
      u = 0, 0.5 (or COCK_AT) and 1; the ratchet has none (n clicks with a
      detent velocity step and a decaying ring): n/a. Allowed laws: the
      goal's list; 'linear' counts as ballistic with a = 0, 'hold' as no
      motion. A mallet that declares its channels (DESIGN 7.4) is judged per
      channel, holds included: a 'carriage' segment on the ring-free
      carriage point (x, y_c, z_c), a 'head' segment on path - carriage,
      each against min(declared extra['jerk'], this ruler's own closed form)
      (m/s^3, the channel's own 3D path). The closed form is rebuilt here from
      the segment's law and boundary data (ballistic p0 v0 a, 3-4-5 p0 p1,
      Hermite p0..a1; _law_h), mapped through the head's arc Z(h) for a head
      segment, scaled by |p1 - p0|/|x1 - x0| for a carriage glide's hermite
      halves and ballistic cruise (the y_c/z_c blend, as 60|D|/T^3 carries it
      for a carriage 3-4-5), and maximised on a dense grid (_closed_jerk); a declared jerk
      below that closed form fails outright (`declared_below_closed`), so a
      declaration can tighten the bound but never loosen it. Without boundary
      data, the closed forms 3-4-5 60|D|/T^3 and hold 0; a ballistic or
      quintic Hermite segment with neither fails.
  9   Struck heads (mallet, hammer: the strokes gravity acts along) are
      judged; a stroke is the downstroke (the goal's "h <= 2g T_down^2"):
      d = h(t_apex), T = T_down, both from ruler 3/4, so s = g T^2 / 2d.
      `s_stroke_segment` (INFO) spans the whole declared 'stroke' segment
      (wind-up and drop, net 0.22 m in 80 ms on the bars), which is not the
      stroke gravity would drive. Plucks and sweeps: the same number as INFO.
  15  Strokes are the declared 'stroke' segments run on through the 'sweep'
      that follows (a strum's stroke is the sweep), sampled every 1 ms on
      Rig.pose.  `piece_120hz_dps` (info) is each link's peak angular speed
      over the piece at 120 Hz (the cell's "upper link faster than
      forearm"). Joints: carriage x (root x), shoulder = upper link angle in
      the y-z plane, elbow = forearm angle minus shoulder angle (its rate is
      the interior angle's); the tool does not rotate (the parallelogram
      holds it), so the shoulder's lever is wrist - root and the elbow's
      wrist - elbow. Share_j = integral |J_j dq_j| / sum. Tip acceleration:
      second differences of the rendered contact point on the 1 kHz grid,
      outside [t - 10 ms, t_end + 10 ms] of every contact and outside click
      intervals; p99 over the declared moving segments (+-3 ms), the 10 g
      limit and the max over every sample. Carriage (INFO: row 15 sets no
      carriage limit; `within_rule` is the rules' "servo carriage <=
      SERVO_V_MAX and <= 3 g"): servo arms' root x on the same grid (the
      ratchet carriage is ruler 19's). Phases: the declared segments other
      than holds.
  16  Joint values from Rig.pose at 120 Hz plus every contact. Spans by
      Rig.pose's IK (root above the tip, no rail sag) over every reachable
      point of the arm's reach: plucked strings at picks 0.05-0.95, struck
      bars at 0.2-0.8 of their length, each at the contact and at Rig.hover
      above it; points where Rig.pose's bend hint is parallel to root->wrist
      (its IK degenerates: harp_arm1 has 2) are left out, and the shoulder is
      wrapped about its circular mean. |U q_j| is the union of the [min, max]
      of each run of samples outside 'home' segments (none today, so it is
      the range). Phrases split at gaps >= 1.5 s and run from the first
      contact's `go` to the last one's `t_free`. Elbow
      coverage is on the interior angle. C_j can exceed 1 where the motion
      leaves the {contact, hover} envelope (the cocked lift). Untagged path:
      path length in segments whose tag is not in segments.TAGS, or in time
      no segment covers.

Helpers core does not have (written here): point_fn (the ring-free contact
point, incl. the hammer's felt), bodies/extent (the parts' extents, mirrored
from r_screen), hurried (the notation's hurried travels), joint angles and the
IK span, the breakpoint list of today's laws, ring_corners (the rendered
rings' |sine| corners), _da_noise (the one-sided stencil's rounding floor).
"""
import functools, math, sys
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from players.core import FPS, G, H, INFO, Result, deriv
from formlab import rig as R
from formlab import segments as SEG
from formlab.clearance import DEFAULT_SPEC, arm_capsules, default_layers, drive_kind

FRAME = 1.0/FPS
STEP = 1e-3          # s: the rulers' fine sampling step
HC = 1e-4            # s: central-difference half step for v and a at a sample
MERGE = 1e-7         # s: grid times closer than this are one time
STILL = 1e-6         # m/s: |dh/dt| at or below this is no motion
MALLET_R = .06       # linkage.mallet_tool's wound head
BOSS_R = DEFAULT_SPEC['boss_r']
LINK_W = max(DEFAULT_SPEC['width'], DEFAULT_SPEC['depth'])   # arm_capsules' bar diameter
STRUCK = ('mallet', 'hammer')
PHRASE_IOI = .6      # ruler 5's "in a phrase", also the hand-off window
RAKE_PENDULUM = (45.71, 67.14)
ALLOWED_LAWS = {'3-4-5', 'quintic', '4-5-6-7', 'cycloidal', 'modified sine', 'modified trapezoid', 'scurve',
                'servo S-curve', 'quintic hermite', 'septic hermite', 'ballistic', 'linear', 'hold'}
A345 = 10/math.sqrt(3)   # 3-4-5: peak |s''| (s = 10u^3 - 15u^4 + 6u^5)
V345 = 1.875             # 3-4-5: peak |s'|

# ---- small utilities --------------------------------------------------------
def _mm(x, scale=1.0, nd=4):
    """min / p50 / max (and n) of a sample, scaled and rounded; None if empty."""
    x = np.asarray(x, float)*scale
    x = x[np.isfinite(x)]
    if x.size == 0: return None
    return dict(min=round(float(x.min()), nd), p50=round(float(np.median(x)), nd), max=round(float(x.max()), nd), n=int(x.size))

def _r(x, nd=4):
    return None if x is None or not math.isfinite(float(x)) else round(float(x), nd)

def _norm(v): return np.linalg.norm(v, axis=-1)

# ---- signals ----------------------------------------------------------------
def _head_angle_noring(rig, aid, t):
    """Rig.head_angle without the check's bounce (a declared ring): rest on the
    check, the cocked flip over the strike, 0 through the contact, the
    quintic lay-back over the release. Mirrors formlab/rig.py head_angle."""
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

@functools.lru_cache(maxsize=None)
def point_fn(S, aid):
    """t -> the scored contact point (no rings)."""
    rig = S.rig
    if not rig.hammer(aid): return lambda t: rig.path_at(aid, t)
    sign = rig.flip_sign(aid)
    return lambda t: rig.path_at(aid, t)+R.head_offset(_head_angle_noring(rig, aid, t), sign)

def path_fn(S, aid):
    return lambda t: S.rig.path_at(aid, t)

def rendered_fn(S, aid):
    """t -> the rendered contact point (Rig.pose 'felt'), without the IK."""
    rig = S.rig
    if not rig.hammer(aid): return lambda t: rig.tip_at(aid, t)
    sign = rig.flip_sign(aid)
    return lambda t: rig.tip_at(aid, t)+R.head_offset(rig.head_angle(aid, t), sign)

# ---- declared structure -------------------------------------------------------
def _finite_segments(S, aid):
    return [sg for sg in S.declared(aid).segments if math.isfinite(sg.t0) and math.isfinite(sg.t1) and sg.t1 > sg.t0]

@functools.lru_cache(maxsize=None)
def breakpoints(S, aid):
    """Every time at which the declared path may switch its law: the knots, the
    segment ends, and the joints inside today's laws (the cocked drop's
    COCK_AT, the S-curve's ramp ends, each ratchet click's ring fade). Only
    today's ratchet click (a `t_end`, on a declaration that is not native)
    has that ring fade, at 0.7 of its period. A native declaration's stepped
    tooth (PLAYERS M1) rings on its detent knot with a C2 fade, and a
    freewheel tooth's click (no `t_end`, DESIGN 7.9) is sound on a smooth
    glide: both add nothing but their own knot times."""
    D = S.declared(aid); ts = {k.t for k in D.knots}
    for sg in _finite_segments(S, aid):
        ts.update((sg.t0, sg.t1)); T = sg.t1-sg.t0
        if sg.law == 'quintic+cocked': ts.add(sg.t0+R.COCK_AT*T)
        elif sg.law == 'scurve': ts.update((sg.t0+R.SCURVE_RAMP*T, sg.t1-R.SCURVE_RAMP*T))
    for k in D.knots:
        if k.kind == 'click' and 't_end' in k.extra and not D.native:
            per = (k.extra['t_end']-k.t)/R.CLICK_MOVE
            ts.add(k.t+.7*per)
    return np.array(sorted(t for t in ts if math.isfinite(t)))

def _knot_times(S, aid, kinds=None):
    return np.array(sorted(k.t for k in S.declared(aid).knots if kinds is None or k.kind in kinds))

def _near(sorted_ts, t, tol):
    if len(sorted_ts) == 0: return False
    i = np.searchsorted(sorted_ts, t)
    return any(abs(sorted_ts[j]-t) <= tol for j in (i-1, i) if 0 <= j < len(sorted_ts))

def _grid(S, aid, t_lo, t_hi):
    """Sample times over [t_lo, t_hi]: every STEP inside moving segments, the
    ends and middle of holds, and every breakpoint."""
    ts = [t_lo, t_hi]
    for sg in S.declared(aid).segments:
        a = max(sg.t0, t_lo); b = min(sg.t1, t_hi)
        if b <= a: continue
        if sg.law == 'hold': ts += [a, .5*(a+b), b]
        else: ts.extend(np.arange(a, b, STEP)); ts.append(b)
    bp = breakpoints(S, aid)
    ts.extend(bp[(bp >= t_lo) & (bp <= t_hi)])
    ts = np.sort(np.asarray(ts, float)); ts = ts[(ts >= t_lo) & (ts <= t_hi)]
    return ts[np.r_[True, np.diff(ts) > MERGE]]

# ---- per-segment samples (rulers 6 and 16) ------------------------------------
@functools.lru_cache(maxsize=None)
def seg_samples(S, aid):
    """Each declared moving segment sampled every STEP on the path signal:
    p, and v, a by central differences over +-HC. A sample whose stencil
    straddles a knot or segment end is invalid (it would difference across a
    corner); `pair_ok` marks consecutive valid samples with no knot between."""
    f = path_fn(S, aid); knots = _knot_times(S, aid)
    ends = np.array(sorted({t for sg in _finite_segments(S, aid) for t in (sg.t0, sg.t1)}))
    stops = np.union1d(knots, ends)
    out = []
    for sg in _finite_segments(S, aid):
        if sg.law == 'hold':
            out.append(dict(seg=sg, hold=True)); continue
        T = sg.t1-sg.t0
        taus = np.arange(sg.t0+STEP/2, sg.t1, STEP)
        if taus.size == 0: taus = np.array([.5*(sg.t0+sg.t1)])
        P0 = np.array([f(t) for t in taus]); Pm = np.array([f(t-HC) for t in taus]); Pp = np.array([f(t+HC) for t in taus])
        v = (Pp-Pm)/(2*HC); a = (Pp-2*P0+Pm)/(HC*HC)
        i = np.searchsorted(stops, taus)
        lo = stops[np.clip(i-1, 0, len(stops)-1)] if len(stops) else np.full(len(taus), -np.inf)
        hi = stops[np.clip(i, 0, len(stops)-1)] if len(stops) else np.full(len(taus), np.inf)
        valid = (np.abs(taus-lo) > HC*1.01) & (np.abs(hi-taus) > HC*1.01)
        kin = np.searchsorted(knots, taus) if len(knots) else np.zeros(len(taus), int)
        pair_ok = valid[:-1] & valid[1:] & (kin[:-1] == kin[1:])
        pend = [f(sg.t0), f(sg.t1)]
        length = float(_norm(np.diff(np.vstack([pend[0], P0, pend[1]]), axis=0)).sum())
        out.append(dict(seg=sg, hold=False, t=taus, p=P0, v=v, a=a, valid=valid, pair_ok=pair_ok,
                        p0=np.asarray(pend[0]), p1=np.asarray(pend[1]), length=length,
                        a_peak=float(_norm(a[valid]).max()) if valid.any() else 0.0))
    return out

def _carriage_pts(st, t):
    """A mallet's carriage channel as a 3D point, ring-free: (x, y_c, z_c) —
    the scored x plus the contacts' y/z blend (no detent ring)."""
    return np.stack([st.carriage.ev(t), st.yc.ev(t), st.zc.ev(t)], -1)

@functools.lru_cache(maxsize=None)
def chan_samples(S, aid):
    """A mallet's declared segments (holds included) each sampled every STEP
    on its OWN channel's signal (DESIGN 7.4): a 'carriage' segment on the
    ring-free carriage point (x, y_c, z_c); a 'head' segment on Rig.path_at
    minus that carriage point (the head's y-z path through the arc map; FK
    of the live cfg inside a homing joint leg). v, a by central differences
    over +-HC. A stencil straddling one of the channel's own segment ends or
    an impulse knot is invalid; `pair_ok` marks consecutive valid samples
    with no such stop between (another channel's joins and the freewheel
    clicks are no corner on this signal)."""
    st = S.stroke(aid); rig = S.rig
    segs = _finite_segments(S, aid); imp = _knot_times(S, aid, SEG.IMPULSES)
    stops = {ch: np.union1d(np.array(sorted({t for sg in segs if sg.extra.get('channel') == ch for t in (sg.t0, sg.t1)})), imp)
             for ch in SEG.CHANNELS}
    def car(t): return _carriage_pts(st, t)
    def head(t, fk):
        P = np.array([rig.path_at(aid, float(u)) for u in t]) if fk else st.p(t)
        return P-car(t)
    out = []
    for sg in segs:
        ch = sg.extra.get('channel')
        fn = car if ch == 'carriage' else (lambda t, fk=(sg.tag == 'home'): head(t, fk))
        taus = np.arange(sg.t0+STEP/2, sg.t1, STEP)
        if taus.size == 0: taus = np.array([.5*(sg.t0+sg.t1)])
        P0 = fn(taus); Pm = fn(taus-HC); Pp = fn(taus+HC)
        a = (Pp-2*P0+Pm)/(HC*HC)
        stp = stops.get(ch, imp)
        i = np.searchsorted(stp, taus)
        lo = stp[np.clip(i-1, 0, len(stp)-1)]; hi = stp[np.clip(i, 0, len(stp)-1)]
        valid = (np.abs(taus-lo) > HC*1.01) & (np.abs(hi-taus) > HC*1.01)
        pair_ok = valid[:-1] & valid[1:] & (i[:-1] == i[1:])
        pend = fn(np.array([sg.t0, sg.t1]))
        out.append(dict(seg=sg, channel=ch, hold=sg.law == 'hold', t=taus, a=a, pair_ok=pair_ok, p0=pend[0], p1=pend[1]))
    return out

def _law_h(law, e, T):
    """A head segment's h(tau) (a carriage glide piece's x(tau)) on [0, T] as a
    numpy Polynomial, rebuilt by THIS ruler from the segment's law and its declared boundary data (never its
    coefficients): 'quintic hermite' the quintic through (p0, v0, a0) and
    (p1, v1, a1), solved here; 'ballistic' p0 + v0 tau + a tau^2/2; '3-4-5'
    p0 + (p1 - p0)(10u^3 - 15u^4 + 6u^5). None when the data is not declared."""
    P = np.polynomial.Polynomial
    try:
        if law == 'quintic hermite':
            row = lambda t, d: [math.factorial(n)/math.factorial(n-d)*t**(n-d) if n >= d else 0.0 for n in range(6)]
            A = np.array([row(0.0, 0), row(0.0, 1), row(0.0, 2), row(T, 0), row(T, 1), row(T, 2)])
            return P(np.linalg.solve(A, [float(e[k]) for k in ('p0', 'v0', 'a0', 'p1', 'v1', 'a1')]))
        if law == 'ballistic': return P([float(e['p0']), float(e['v0']), .5*float(e['a'])])
        if law == '3-4-5':
            D = float(e['p1'])-float(e['p0'])
            return P([float(e['p0']), 0, 0, 10*D/T**3, -15*D/T**4, 6*D/T**5])
    except KeyError:
        return None
    return None

def _arc_derivs(h, rho, k):
    """The first three h-derivatives of the declared arc Z(h) = (rho/k^2)(sqrt(1 + (k h/rho)^2) - 1)."""
    q = np.sqrt(1+(k*h/rho)**2)
    return (h/rho)/q, (1/rho)/q**3, -3*k*k*h/(rho**3*q**5)

def _peak(J, T):
    """max J(tau) over [0, T] (J >= 0): a dense grid, refined about its best sample."""
    ts = np.linspace(0.0, T, 4097); v = J(ts); i = int(np.argmax(v)); best = float(v[i])
    lo, hi = ts[max(i-1, 0)], ts[min(i+1, len(ts)-1)]
    for _ in range(50):
        m1 = lo+(hi-lo)/3; m2 = hi-(hi-lo)/3
        if J(m1) < J(m2): lo = m1
        else: hi = m2
    return max(best, float(J(.5*(lo+hi))))

def _closed_jerk(S, aid, x):
    """The closed-form peak |p'''| of a mallet segment on its own channel signal,
    from its law and declared boundary data alone: carriage '3-4-5' 60|D|/T^3
    (D the channel's 3D end-to-end move: the y_c/z_c blend rides x's law); a
    carriage glide's 'quintic hermite' halves and 'ballistic' cruise: the peak
    |x'''| of _law_h on their declared x boundary data, times |p1 - p0|/|x1 - x0|
    for the blend (as 60|D|/T^3 carries it for the 3-4-5), so a glide piece's
    bound is never its declaration alone; head: the y-z path (h, sigma Z(h))
    of _law_h; each peak on a dense grid refined about the best sample
    (_peak); 'hold' 0. None where there is none (a homing joint leg's FK path)."""
    sg = x['seg']; T = sg.t1-sg.t0
    if sg.law == 'hold': return 0.0
    if x['channel'] == 'carriage':
        D = float(np.linalg.norm(x['p1']-x['p0']))
        if sg.law == '3-4-5': return 60*D/T**3
        xp = _law_h(sg.law, sg.extra, T)
        if xp is None: return None
        dx = abs(float(x['p1'][0]-x['p0'][0])); d3 = xp.deriv(3)
        return _peak(lambda tau: np.abs(d3(tau)), T)*(D/dx if dx > 1e-12 else 1.0)
    if sg.tag == 'home': return None
    hp = _law_h(sg.law, sg.extra, T)
    if hp is None: return None
    rho, k = R.stroke.arc(S.kind(aid)); d1, d2, d3 = hp.deriv(1), hp.deriv(2), hp.deriv(3)
    def J(tau):
        h, h1, h2, h3 = hp(tau), d1(tau), d2(tau), d3(tau); z1, z2, z3 = _arc_derivs(h, rho, k)
        return np.hypot(h3, z3*h1**3+3*z2*h1*h2+z1*h3)
    return _peak(J, T)

def _declared_jerk(x, closed=None):
    """(bound m/s^3 or None, why) for a mallet's channel sample: the smaller of
    the segment's declared extra['jerk'] and the ruler's own closed form on its
    law and boundary data (`closed`, _closed_jerk), so the bound is never the
    declaration alone and a curve whose shape leaves its law fails; a declared
    jerk with no closed form here (a homing joint leg) is used as declared;
    no declared jerk: the closed form ('3-4-5' 60|D|/T^3, 'hold' 0); a
    'ballistic' or 'quintic hermite' segment without a declared jerk has no
    bound (a fail, DESIGN 7.4)."""
    sg = x['seg']; j = sg.extra.get('jerk'); T = sg.t1-sg.t0
    if j is not None:
        return (min(float(j), closed), 'closed form') if closed is not None else (float(j), 'declared')
    if sg.law == '3-4-5': return 60*float(np.linalg.norm(x['p1']-x['p0']))/T**3, 'closed'
    if sg.law == 'hold': return 0.0, 'closed'
    if sg.law in ('ballistic', 'quintic hermite'): return None, 'undeclared'
    return None, 'na'

# ---- the parts (ruler 1) -------------------------------------------------------
def _caps(S, aid, P):
    cfg = S.cfg(aid)
    return arm_capsules(P, cfg['o1'], cfg['o2'], cfg.get('layers', default_layers(DEFAULT_SPEC)), DEFAULT_SPEC,
                        cfg.get('pinion', 'back'), drive_kind(cfg))[0]

def bodies(S, aid, P):
    """part -> (tracked point (N,3), body points (N,m,3), radius). Mirrors
    tools/players/r_screen.py bodies(): ruler 2 is ruler 1 on the screen."""
    kind = S.kind(aid); cfg = S.cfg(aid); felt = P['felt']
    o1 = np.asarray(cfg['o1'], float); o2 = np.asarray(cfg['o2'], float)
    if kind == 'mallet':
        tool = ((felt+[0, MALLET_R, 0])[:, None, :], MALLET_R)
    else:
        caps = _caps(S, aid, P)
        # arm_capsules adds 'head' only when some head angle is non-zero
        a, b, r = caps.get('head', caps['tool']) if kind == 'hammer' else caps['tool']
        tool = (np.stack([a, b], 1), float(r))
    wrist, elbow = P['wrist'], P['elbow']
    return dict(tool=(felt,)+tool,
                wrist=(wrist, np.stack([wrist, wrist+o2], 1), BOSS_R),
                elbow=(elbow, np.stack([elbow, elbow+o1, elbow+o2], 1), BOSS_R))

def extent(body, r, dhat):
    """E(part, d) per sample: the spread of the body points along d plus 2r."""
    s = np.einsum('nmi,ni->nm', body, dhat)
    return s.max(1)-s.min(1)+2*r

@functools.lru_cache(maxsize=None)
def head_extent_x(S, aid):
    P = S.poses(aid, 'frames'); _, body, r = bodies(S, aid, P)['tool']
    return float(extent(body[:1], r, np.array([[1.0, 0, 0]]))[0])

@functools.lru_cache(maxsize=None)
def hurried(S, aid):
    """The notation's hurried travels of a stepped (ratchet) arm:
    (go, approach, dx, T_min, window) for each travel whose 3-4-5 minimum time
    at 3 g and 1.0 E_head a frame exceeds its contact-to-contact window
    (t_i - t_{i-1}, the move d = contact x change): ruler 19's definition in
    r_strike.py, so the two rulers count the same travels.

    A mallet that declares its carriage (PLAYERS M1) names its hurried
    travels itself (motion_timing.hurried, the same 3 g and 1.0 E a frame
    rule): its carriage 'travel' segments with extra['hurried'], grouped by
    extra['travel'], each (t0, t1) the declared travel window (contact to
    contact; the sched's go..approach no longer bounds the move)."""
    if not S.rig.stepped(aid): return ()
    st = S.stroke(aid)
    if st is not None: return _declared_hurried(S, aid, st)
    E = head_extent_x(S, aid); out = []; C = S.contacts(aid)
    for c in C[1:]:
        s = c.sched; dx = abs(float(c.point[0]-C[c.i-1].point[0]))
        if dx < 1e-3: continue
        T_min = max(math.sqrt(A345*dx/(3*G)), V345*dx/(E*FPS))
        if T_min > c.ioi: out.append((float(s['go']), float(s['approach']), dx, T_min, c.ioi))
    return tuple(out)

# Ruler 1's 'brisk' travels, the lead's explicit policy for a mallet tool's gated p95 until M8: True leaves them
# out of the gate (and holds their count to TODAY_BRISK); False gates their frames as written
BRISK_UNTIL_M8 = True
BRISK_RHO = 0.5      # E a frame: a 'brisk' travel's least smooth time is taken at 3 g and this (ruler 1, mallet)
# ...and the brisk count may not grow until M8 (row '1 brisk'): today's per asset and arm, counted on the frozen
# scores (brisk reads only the contacts, so the plan cannot change it); an arm not listed is allowed none
TODAY_BRISK = {'chamber': {'bars_arm0': 16, 'bars_arm1': 20},
               'expanded': {'bars_arm0': 16, 'bars_arm1': 20, 'bells_arm0': 0, 'bells_arm1': 0}}

@functools.lru_cache(maxsize=None)
def brisk(S, aid):
    """The 'brisk' travels of a mallet, ruler 1's explicit policy until M8
    (BRISK_UNTIL_M8; the same construction as `hurried`): (t0, t1, dx, T_min,
    ioi) for each contact travel at tempo, previous contact's t_end ->
    contact, whose 3-4-5 time at 3 g and BRISK_RHO E_x a frame,
    max(sqrt(A345 dx / 3 g), V345 dx / (BRISK_RHO E_x 30/s)), exceeds its
    IOI. The plan's travel together with the float cannot hold 0.5 E a frame
    there (no 3-4-5 over the IOI does today; the glide the plan picks seldom
    does): the whole gap, head included, leaves the gated p95 until M8's
    splay changes replace these leaps (and the count is held to TODAY_BRISK)."""
    if S.kind(aid) != 'mallet': return ()
    E = head_extent_x(S, aid); C = S.contacts(aid); out = []
    for c in C[1:]:
        dx = abs(float(c.point[0]-C[c.i-1].point[0]))
        if dx < 1e-3: continue
        T_min = max(math.sqrt(A345*dx/(3*G)), V345*dx/(BRISK_RHO*E*FPS))
        if T_min > c.ioi: out.append((float(C[c.i-1].t_end), float(c.t), dx, T_min, float(c.ioi)))
    return tuple(out)

def _declared_hurried(S, aid, st):
    E = head_extent_x(S, aid); by = {}
    for sg in _finite_segments(S, aid):
        if sg.extra.get('channel') != 'carriage' or sg.tag != 'travel' or not sg.extra.get('hurried'): continue
        tid = sg.extra.get('travel'); a, b = by.get(tid, (sg.t0, sg.t1)); by[tid] = (min(a, sg.t0), max(b, sg.t1))
    out = []
    for a, b in sorted(by.values()):
        dx = abs(float(st.x(b)-st.x(a)))
        out.append((a, b, dx, max(math.sqrt(A345*dx/(3*G)), V345*dx/(E*FPS)), b-a))
    return tuple(out)

def _frame_mask(N, intervals=(), points=()):
    """Frames k (the interval (t_{k-1}, t_k]) touched by any point or open interval."""
    m = np.zeros(N, bool)
    for t in points:
        k = int(math.ceil(t*FPS-1e-9))
        for kk in (k-1, k, k+1):
            if 0 < kk < N and (kk-1)/FPS < t <= kk/FPS: m[kk] = True
    for a, b in intervals:
        lo = max(int(math.floor(a*FPS)), 1); hi = min(int(math.ceil(b*FPS))+1, N-1)
        for kk in range(lo, hi+1):
            if a < kk/FPS and b > (kk-1)/FPS: m[kk] = True
    return m

CONTACT_OFF = .05     # s: ruler 1's p95_off leaves out frames within this of a contact (DESIGN 7.8)
STRIKE_TAIL = .05     # s: a struck head's strike window runs [t_apex, t + this] (the lead's ruler-1 amendment)

def r1_strobe(S):
    out = []
    for aid in S.arms:
        kind = S.kind(aid); P = S.poses(aid, 'frames'); t = P['t']; N = len(t)
        B = bodies(S, aid, P); hur = hurried(S, aid)
        imp = _frame_mask(N, S.click_intervals(aid), [k.t for k in S.impulse_knots(aid)])
        hmask = _frame_mask(N, [(h[0], h[1]) for h in hur])
        allow = np.where(imp | hmask, 1.5, 1.0)[1:]
        for part in ('tool', 'wrist', 'elbow'):
            pt, body, r = B[part]
            d = np.diff(pt, axis=0); dist = _norm(d)
            dhat = d/np.maximum(dist, 1e-15)[:, None]
            E = .5*(extent(body[:-1], r, dhat)+extent(body[1:], r, dhat))
            rho = dist/E; active = dist > 1e-4
            p95 = float(np.percentile(rho[active], 95)) if active.any() else 0.0
            k = int(np.argmax(rho)); over = rho > allow
            plain = allow == 1.0
            v = dict(max=_r(rho[k], 3), t_max=_r(t[k+1], 3), max_cm=_r(dist.max()*100, 2),
                     max_off_allow=_r(rho[plain].max(), 3) if plain.any() else None,
                     frames_over=int(over.sum()), p95_active=_r(p95, 3), active=int(active.sum()))
            if part == 'tool': v.update(hurried=len(hur), allow_frames=int((allow > 1).sum()))
            p95_gate = p95
            if part == 'tool' and kind == 'mallet':
                # The lead's decision (f), amending the Acceptance cell for a struck
                # head's tool: the p95 is taken over active frames off the STRIKE
                # WINDOWS [t_apex_i, t_i + 50 ms] (their speed is rulers 7 and 8's:
                # v_in >= 2.5 m/s is 0.69 E a frame), off impulse frames and off
                # hurried travels; that p95 is gated (<= 0.5). The max rule above
                # still holds on every frame. p95_active as written, and DESIGN
                # 7.8's p95_noimpulse / p95_off, stay as info.
                exi = (imp | hmask)[1:]
                exc = _frame_mask(N, [(c.t-CONTACT_OFF, c.t_end+CONTACT_OFF) for c in S.contacts(aid)])[1:]
                stw = _frame_mask(N, [(r['t_apex'], r['c'].t+STRIKE_TAIL) for r in prep(S, aid)])[1:]
                for key, m in (('p95_noimpulse', active & ~exi), ('p95_off', active & ~exi & ~exc)):
                    v[key] = _r(np.percentile(rho[m], 95), 3) if m.any() else None
                v['active_off'] = int((active & ~exi & ~exc).sum())
                # ...and, while BRISK_UNTIL_M8 (the lead's explicit policy, built as 'hurried' is), off the
                # frames of each brisk travel: a contact travel at tempo whose 3-4-5 time at 3 g and 0.5 E_x a
                # frame exceeds its IOI, where the plan's travel together with the float cannot hold 0.5 E a
                # frame; the whole gap (t_end -> contact), head included, until M8's splay changes replace
                # these leaps ('1 brisk' holds their count). The max rule above still holds on every frame.
                brk = brisk(S, aid) if BRISK_UNTIL_M8 else ()
                bm = _frame_mask(N, [(b[0], b[1]) for b in brk])[1:]
                gm = active & ~exi & ~stw & ~bm
                if BRISK_UNTIL_M8: v.update(brisk=len(brk), brisk_frames=int((active & bm & ~exi & ~stw).sum()))
                # an empty gated set with motion on the arm measures nothing: n/a (a gate fails on it), never 0
                p95_gate = float(np.percentile(rho[gm], 95)) if gm.any() else (None if active.any() else 0.0)
                v.update(p95_gated=_r(p95_gate, 3) if p95_gate is not None else None, active_gated=int(gm.sum()),
                         strike_frames=int((active & stw).sum()),
                         gated_share=_r(gm.sum()/active.sum(), 3) if active.any() else None)
            out.append(Result(1, f'1 {part}', aid, v, False if over.any() else (None if p95_gate is None else bool(p95_gate <= .5)),
                              ('rho = |dp|/E(part, dp^); <= 1.0 (1.5 on impulse frames and hurried travels) on every frame; '
                               'p95_gated <= 0.5: active frames off the strike windows [t_apex, t + 50 ms], impulse frames, '
                               +('hurried travels and, until M8, brisk travels (contact travels at tempo whose 3-4-5 time at 3 g and '
                                 '0.5 E_x a frame exceeds the IOI: the plan\'s travel with the float cannot hold 0.5 E a frame there, '
                                 'so the whole gap, head included, leaves the gate; the lead\'s policy for a struck head)'
                                 if BRISK_UNTIL_M8 else 'and hurried travels (the lead\'s amendment for a struck head)')+'; info: p95_active as written, '
                               'p95_noimpulse leaves out impulse frames and hurried travels, p95_off also +-50 ms of each contact; '
                               'hurried travels are the declared ones' if part == 'tool' and kind == 'mallet' else
                               'rho = |dp|/E(part, dp^); <= 1.0 (1.5 on impulse frames and hurried travels), p95 active <= 0.5')
                              +('; E_x(head) %.3f m, hurried = 3-4-5 at 3 g and 1 E/frame over the contact-to-contact window' % head_extent_x(S, aid) if part == 'tool' and S.rig.stepped(aid) else '')))
        if kind == 'mallet' and BRISK_UNTIL_M8:
            # the brisk policy's ceiling: no more brisk travels than today's (they read the frozen score)
            brk = brisk(S, aid); today = TODAY_BRISK.get(S.asset, {}).get(aid, 0)
            out.append(Result(1, '1 brisk', aid, dict(count=len(brk), today=today, at=[_r(b[1], 3) for b in brk][:8],
                                                      dx_m=_r(max([b[2] for b in brk], default=0.0), 3),
                                                      t_min_over_ioi=_r(max([b[3]/b[4] for b in brk], default=0.0), 3)),
                              len(brk) <= today,
                              f'brisk travels (out of the tool\'s gated p95 until M8) <= today\'s {today}'))
        # links: R |dtheta| at the far end against max(link width, E_head along the swing)
        cfg = S.cfg(aid); tool_pt, tool_body, tool_r = B['tool']; lv = {}; worst = 0.0
        for name, a_, b_ in (('upper', 'root', 'elbow'), ('lower', 'elbow', 'wrist')):
            u = P[b_]-P[a_]; L = _norm(u); uh = u/L[:, None]
            dth = np.arccos(np.clip((uh[1:]*uh[:-1]).sum(1), -1, 1))
            arc = .5*(L[1:]+L[:-1])*dth
            sw = uh[1:]-uh[:-1]; sn = _norm(sw)
            sw = np.where(sn[:, None] > 1e-12, sw/np.maximum(sn, 1e-15)[:, None], np.array([0, 1.0, 0]))
            Eh = .5*(extent(tool_body[:-1], tool_r, sw)+extent(tool_body[1:], tool_r, sw))
            ratio = arc/np.maximum(LINK_W, Eh); k = int(np.argmax(ratio))
            lv[name] = dict(max_cm=_r(arc.max()*100, 2), max_deg=_r(np.degrees(dth.max()), 2), ratio=_r(ratio[k], 3),
                            t=_r(t[k+1], 3), frames_over=int((ratio > 1).sum()))
            worst = max(worst, float(ratio[k]))
        out.append(Result(1, '1 links', aid, lv, worst <= 1.0,
                          f'R|dtheta| at the link end <= max(link width {LINK_W:.3f} m, E_head along its swing)'))
        # rotation of parts under 0.25 m: the hinged head; rigid tools hold their angle
        if S.rig.hammer(aid):
            dh = np.degrees(np.abs(np.diff(P['head']))); k = int(np.argmax(dh))
            out.append(Result(1, '1 rotation', aid, dict(max_deg=_r(dh[k], 2), t=_r(t[k+1], 3), frames_over=int((dh > 20).sum())),
                              bool(dh.max() <= 20), f'hinged head (head_l {R.HAMMER["head_l"]} m) <= 20 deg a frame'))
        else:
            out.append(Result(1, '1 rotation', aid, dict(max_deg=0.0), True,
                              'no part under 0.25 m rotates: the parallelogram holds the tool upright'))
        if kind in ('pick', 'rake'):
            out.append(Result(1, '1 digits, palm' if kind == 'pick' else '1 digits', aid, {}, None,
                              'no digits or palm yet (harp hands M7, rake hand M9)'))
    return out

# ---- preparation and action (rulers 3, 4) --------------------------------------
FINE = 1e-5          # s: the step the phase edges are refined to
STILL_V = 1e-4       # m/s: a one-sided dh/dt at or below this at a breakpoint is a stop

def _signs(ts, h):
    slope = np.diff(h)/np.diff(ts)
    return np.where(slope > STILL, 1, np.where(slope < -STILL, -1, 0))

def _run_start(hf, a, b, sign, bp=(), n=64):
    """On [a, b], the start of the run of `sign` slopes (+1 rising, -1
    falling) that ends at b, to FINE: coarse-to-fine, n secants a level, the
    bracket narrowed to the two secants about the change; snapped onto a
    breakpoint within FINE of it (the laws switch there)."""
    while True:
        dense = b-a <= n*FINE
        ts = np.linspace(a, b, max(3, int(math.ceil((b-a)/FINE))+1) if dense else n+1)
        sg = _signs(ts, np.array([hf(t) for t in ts]))
        j = len(sg)-1
        while j >= 0 and sg[j] == sign: j -= 1
        if dense or j < 0 or j == len(sg)-1: t = float(ts[j+1]); break
        a, b = float(ts[j]), float(ts[j+2])
    if len(bp):
        k = np.searchsorted(bp, t)
        for kk in (k-1, k):
            if 0 <= kk < len(bp) and abs(bp[kk]-t) <= FINE+1e-12: return float(bp[kk])
    return t

@functools.lru_cache(maxsize=None)
def prep(S, aid):
    """Per contact, on h(t) = (p - c).n of the scored point: the action (the
    last falling stretch before t_i, from t_apex), the wind-up (the rising
    stretch ending at t_apex, from t_w) and the lead L = t_i - t_w. Found on
    the 1 ms + breakpoint grid, then each edge refined to FINE (10 us). A
    rise that comes to rest at a breakpoint (one-sided dh/dt <= STILL_V, e.g.
    a release's end flowing into the next move) ends there: dh/dt > 0 must
    hold throughout W.

    A declared apex hold (PLAYERS M1, DESIGN 7.1): when a run of declared
    head-channel 'hold' segments (extra['channel'] == 'head'; a mallet's
    park and cocked hold) ends at t_apex (+-APEX_HOLD_TOL), W is the rise
    BEFORE that run: it ends where the run starts (`t_hold`), and L and the
    depth dh are measured from the rise's start. Arms that declare no head
    channel (every arm but the mallet) never have such a run, so their rows
    are what they were. Rulers 3, 4, 5, 8, 9, 10 and 21 share these rows:
    t_apex, t_w (the wind-up's start), t_hold (the apex hold's start; =
    t_apex when there is none), hold = t_apex - t_hold.

    The call shape is stable: prep(S, aid) -> [dict(c, t_apex, t_w, W,
    T_down, L, h_apex, dh, t_hold, hold)], one per contact in order."""
    f = point_fn(S, aid); C = S.contacts(aid); out = []; bp = breakpoints(S, aid)
    holds = _apex_hold_runs(S, aid)
    for c in C:
        t_i = c.t
        t_lo = C[c.i-1].t_end if c.i > 0 else t_i-30.0
        ts = _grid(S, aid, t_lo, t_i)
        hf = lambda t, c=c: float((np.asarray(f(t))-c.point)@c.normal)
        h = np.array([hf(t) for t in ts]); sg = _signs(ts, h)
        j = len(sg)-1
        while j >= 0 and sg[j] == 0: j -= 1                 # a dwell on the contact
        while j >= 0 and sg[j] < 0: j -= 1                  # the action
        i_apex = j+1
        n = len(ts)-1
        t_apex = float(ts[i_apex])
        if i_apex < n:                                      # refine: the fall starts in (ts[i_apex-1], ts[i_apex+1])
            t_apex = _run_start(hf, float(ts[max(i_apex-1, 0)]), float(ts[i_apex+1]), -1, bp)
        # a declared apex hold: the wind-up is the rise that ends where it starts
        t_hold = t_apex; i_top = i_apex
        run = _hold_run_at(holds, t_apex)
        if run is not None:
            t_hold = max(run, float(ts[0]))
            i_top = int(np.searchsorted(ts, t_hold-MERGE))  # t_hold is a segment end, so on the grid
            j = i_top-1
            # a rise eases into the hold (a 3-4-5 has zero slope at its end), so
            # the last samples before t_hold can read still (|dh/dt| <= STILL:
            # 2.3 ms of a 2.76 s 0.25 m wind-up). Inside the declared moving
            # head segment that ends at t_hold they are that rise's own end,
            # not a rest beside the hold; nothing outside it is skipped.
            s0 = _rise_into(S, aid, run)
            k = j
            while s0 is not None and k >= 0 and sg[k] == 0 and ts[k] >= s0-1e-12: k -= 1
            if k >= 0 and sg[k] > 0: j = k
        stopped = False
        while j >= 0 and sg[j] > 0:                         # the wind-up
            if j+1 < i_top and _near(bp, ts[j+1], 1e-9) and (
                    deriv(hf, ts[j+1], -1, 1) <= STILL_V or deriv(hf, ts[j+1], +1, 1) <= STILL_V):
                stopped = True; break                       # it came to rest at that breakpoint
            j -= 1
        i_w = j+1
        t_top = t_apex if run is None else t_hold
        t_w = float(ts[i_w])
        if i_w >= i_top: t_w = t_top
        elif not stopped:                                   # refine: the rise starts in (ts[i_w-1], ts[i_w+1])
            t_w = min(_run_start(hf, float(ts[max(i_w-1, 0)]), float(ts[i_w+1]), +1, bp), t_top)
        h_apex = hf(t_apex)
        out.append(dict(c=c, t_apex=t_apex, t_w=t_w, W=t_top-t_w, T_down=t_i-t_apex, L=t_i-t_w,
                        h_apex=h_apex, dh=h_apex-hf(t_w), t_hold=t_hold, hold=t_apex-t_hold))
    return out

APEX_HOLD_TOL = 2e-3   # s: a declared head hold "ends at t_apex" within this (DESIGN 7.1)

@functools.lru_cache(maxsize=None)
def _apex_hold_runs(S, aid):
    """The arm's runs of contiguous declared head-channel 'hold' segments:
    ((run start, run end), ...) sorted by end. Empty for every arm whose
    declaration has no head channel (all but the mallet)."""
    segs = sorted((sg for sg in S.declared(aid).segments if sg.extra.get('channel') == 'head'), key=lambda sg: sg.t0)
    runs = []; cur = None
    for sg in segs:
        if sg.tag == 'hold' and sg.law == 'hold':
            if cur is not None and abs(sg.t0-cur[1]) <= 1e-9: cur[1] = sg.t1
            else:
                if cur is not None: runs.append(tuple(cur))
                cur = [sg.t0, sg.t1]
        elif cur is not None:
            runs.append(tuple(cur)); cur = None
    if cur is not None: runs.append(tuple(cur))
    return tuple(r for r in runs if math.isfinite(r[1]))

def _rise_into(S, aid, t_hold):
    """t0 of the declared moving head segment ending at t_hold, or None."""
    for sg in S.declared(aid).segments:
        if sg.extra.get('channel') == 'head' and sg.law != 'hold' and abs(sg.t1-t_hold) <= 1e-9: return sg.t0
    return None

def _hold_run_at(runs, t_apex):
    """The start of the declared head hold run ending at t_apex (+-APEX_HOLD_TOL), or None."""
    for a, b in runs:
        if abs(b-t_apex) <= APEX_HOLD_TOL+1e-12: return a
    return None

def handoffs(S):
    """(incoming aid, its contact index, outgoing aid, outgoing hit) for every
    change of holder inside one mallet mechanism at the mechanism's IOI <= 0.6 s."""
    by = {}
    for aid in S.arms_of('mallet'): by.setdefault(S.mech(aid), []).extend(S.contacts(aid))
    out = []
    for cs in by.values():
        cs = sorted(cs, key=lambda c: c.t)
        for a, b in zip(cs, cs[1:]):
            if a.aid != b.aid and b.t-a.t <= PHRASE_IOI+1e-9: out.append((b.aid, b.i, a.aid, a.t))
    return out

def r3_preparation(S):
    out = []
    for aid in S.arms:
        rows = prep(S, aid)
        if not rows:
            out.append(Result(3, '3 preparation', aid, dict(n=0), None, 'no contacts on this arm')); continue
        fails = dict(windup=0, depth=0, lead=0, lead415=0)
        for r in rows:
            c = r['c']
            if r['W'] < (6 if c.gap >= .5 else 4)*FRAME-1e-9: fails['windup'] += 1
            if r['dh'] < .25*r['h_apex']-1e-12: fails['depth'] += 1
            if r['L'] < min(.2, .9*c.ioi)-1e-9: fails['lead'] += 1
            if c.gap >= 1.0 and r['L'] < .415-1e-9: fails['lead415'] += 1
        L = np.array([r['L'] for r in rows]); W = np.array([r['W'] for r in rows])
        depth = np.array([r['dh']/r['h_apex'] if r['h_apex'] > 0 else 0.0 for r in rows])
        v = dict(n=len(rows), lead_lt100=int((L < .1).sum()), lead_lt200=int((L < .2).sum()),
                 lead_ms=_mm(L, 1e3, 1), windup_frames=_mm(W, FPS, 2), windup_depth=_mm(depth, 1, 3),
                 gap_ge1=int(sum(r['c'].gap >= 1.0 for r in rows)), fail=fails)
        held = [r['hold'] for r in rows if r['hold'] > 0]
        if held: v.update(apex_holds=len(held), hold_ms=_mm(held, 1e3, 1))
        out.append(Result(3, '3 preparation', aid, v, not any(fails.values()),
                          '|W| >= 4 frames (6 if gap >= 0.5 s); dh(W) >= 0.25 h(t_apex); L >= min(200 ms, 0.9 IOI); L >= 415 ms if gap >= 1 s'
                          +('; W skips a declared head hold ending at t_apex (+-2 ms): W is the rise before it, L and dh from its start' if held else '')
                          +('; plucks: t_i = t and c = the contact (no t_place yet)' if S.kind(aid) == 'pick' else '')))
    # hand-offs, on the incoming holder
    ho = {}
    for b_aid, b_i, a_aid, a_t in handoffs(S):
        r = prep(S, b_aid)[b_i]
        ho.setdefault(b_aid, []).append((r['c'].t, r['t_w']-a_t))
    for aid in S.arms_of('mallet'):
        if aid not in ho: continue
        early = np.array([e for _, e in ho[aid]]); bad = [round(t, 2) for t, e in ho[aid] if e > 1e-9]
        out.append(Result(3, '3 hand-off', aid,
                          dict(n=len(early), fail=len(bad), late_ms=_mm(early, 1e3, 1), at=bad[:8]), not bad,
                          'incoming wind-up starts at or before the outgoing hit (holder change at mechanism IOI <= 0.6 s); late_ms = t_w - outgoing hit'))
    return out

def r4_action(S):
    out = []
    for aid in S.arms:
        rows = prep(S, aid)
        if not rows:
            out.append(Result(4, '4 action', aid, dict(n=0), None, 'no contacts on this arm')); continue
        T = np.array([r['T_down'] for r in rows])
        if S.kind(aid) in STRUCK:
            short = [r for r in rows if r['c'].ioi <= .5]; long_ = [r for r in rows if r['c'].ioi > .5]
            bad_s = sum(not (.35-1e-9 <= r['T_down']/r['c'].ioi <= .45+1e-9) for r in short)
            bad_l = sum(not (.125-1e-9 <= r['T_down'] <= .25+1e-9) for r in long_)
            ratio = [r['T_down']/r['c'].ioi for r in short]
            v = dict(n=len(rows), T_down_frames=_mm(T, FPS, 2), ioi_le05=len(short), ratio=_mm(ratio, 1, 3),
                     fail_le05=bad_s, ioi_gt05=len(long_), fail_gt05=bad_l)
            out.append(Result(4, '4 action', aid, v, bad_s+bad_l == 0,
                              'T_down = t_i - t_apex: 0.35-0.45 IOI at IOI <= 0.5 s, 125-250 ms above'))
        else:
            bad = int((T < 2.5*FRAME-1e-9).sum())
            out.append(Result(4, '4 action', aid, dict(n=len(rows), approach_frames=_mm(T, FPS, 2), fail=bad), bad == 0,
                              'approach >= 2.5 frames; today t_i = t (no t_place)'+('; the sweep is held to the pluck rule' if S.kind(aid) == 'rake' else '')))
    return out

# ---- no rest in a phrase (ruler 5) ----------------------------------------------
def _covered(ta, tb, segs):
    """True when the declared segments `segs` cover [ta, tb] but for pieces of
    at most a frame: the slow stretch is the hold itself plus the hold's own
    ease in and out, never another rest beside it."""
    iv = sorted((max(sg.t0, ta), min(sg.t1, tb)) for sg in segs if sg.t1 > ta and sg.t0 < tb)
    if not iv: return False
    cur = ta
    for a, b in iv:
        if a-cur > FRAME+1e-9: return False
        cur = max(cur, b)
    return tb-cur <= FRAME+1e-9

def r5_rest(S):
    out = []
    for aid in S.arms:
        C = S.contacts(aid); f = point_fn(S, aid); rows = prep(S, aid)
        holds = [sg for sg in _finite_segments(S, aid) if sg.tag == 'hold']
        gaps = []
        for c in C[1:]:
            pend = S.kind(aid) == 'rake' and RAKE_PENDULUM[0]-.01 <= C[c.i-1].t and c.t <= RAKE_PENDULUM[1]+.01
            if c.ioi <= PHRASE_IOI+1e-9 or pend: gaps.append(c)
        n_bad = 0; n_int = 0; n_viol = 0; n_ex = 0; n_lenient = 0; worst = 0.0; at = []
        for c in gaps:
            t0 = C[c.i-1].t_end; t1 = c.t
            ts = np.linspace(t0, t1, max(int(round((t1-t0)/STEP)), 1)+1)   # ends exactly on the two contacts
            if len(ts) < 3: continue
            P = np.array([f(t) for t in ts]); dt = float(ts[1]-ts[0])
            V = np.diff(P, axis=0)/dt; sp = _norm(V); A = np.diff(V, axis=0)/dt
            vpk = float(sp.max())
            X = P-P.mean(0)
            ax = np.linalg.svd(X, full_matrices=False)[2][0] if vpk > 0 else np.array([1.0, 0, 0])
            slow = sp < .15*vpk if vpk > 0 else np.ones(len(sp), bool)
            t_apex = rows[c.i]['t_apex']; bad_gap = False
            k = 0
            while k < len(slow):
                if not slow[k]: k += 1; continue
                e = k
                while e < len(slow) and slow[e]: e += 1
                dur = float(ts[e]-ts[k])
                if dur > FRAME+1e-9:
                    n_int += 1
                    s = V[k:e]@ax; nz = s[np.abs(s) > 1e-9]
                    rev = nz.size > 1 and bool(np.any(np.sign(nz[1:]) != np.sign(nz[:-1])))
                    acc = _norm(A[max(k-1, 0):max(e-1, k)]) if e-1 > k-1 else np.array([0.0])
                    turn = rev and bool(acc.size and acc.min() >= .5*G)
                    if not turn:
                        ta, tb = float(ts[k]), float(ts[e])
                        gap_long = c.gap >= .8
                        apex_holds = [sg for sg in holds if abs(sg.t1-t_apex) <= 2e-3]
                        if gap_long and _covered(ta, tb, holds): n_lenient += 1
                        if gap_long and _covered(ta, tb, apex_holds): n_ex += 1
                        else:
                            n_viol += 1; bad_gap = True; worst = max(worst, dur)
                            if len(at) < 6: at.append(round(float(ta), 2))
                k = e
            n_bad += bad_gap
        v = dict(gaps=len(gaps), gaps_violating=n_bad, frac=_r(n_bad/len(gaps), 3) if gaps else None,
                 slow_intervals=n_int, violations=n_viol, exempt=n_ex, exempt_lenient=n_lenient,
                 longest_ms=_r(worst*1e3, 1), at=at)
        out.append(Result(5, '5 no rest', aid, v, n_viol == 0,
                          'gaps with IOI <= 0.6 s'+(' and the 45.71-67.14 s pendulum' if S.kind(aid) == 'rake' else '')
                          +': |v| < 0.15 v_peak for > 1 frame must reverse the principal axis with |a| >= 0.5 g throughout'
                          +('' if gaps else '; no such gap on this arm')))
    return out

# ---- smoothness (ruler 6) --------------------------------------------------------
def _q3(u):   # 3-4-5 third derivative
    return 60-360*u+360*u*u

def _jerk_bound(sm, f):
    """The law's closed-form max |jerk| over the segment (m/s^3), or None."""
    sg = sm['seg']; law = sg.law; T = sg.t1-sg.t0; p0, p1 = sm['p0'], sm['p1']; D = p1-p0
    if law in ('quintic', '3-4-5'): return 60*float(np.linalg.norm(D))/T**3
    if law == 'scurve':
        r = R.SCURVE_RAMP; return 6/(r*r*(1-r))*float(np.linalg.norm(D))/T**3
    if law == 'linear': return 0.0
    u = np.linspace(0, 1, 2001)
    if law == 'quintic+sine':
        L = (np.asarray(f(sg.t0+.5*T))-p0-D*.5)/.45
        J = np.outer(_q3(u), D)-np.outer(.45*np.pi**3*np.cos(np.pi*u), L)
        return float(_norm(J).max())/T**3
    if law == 'quintic+cocked':
        c = R.COCK; ua = R.COCK_AT; qa = R.quintic(ua)
        L = (np.asarray(f(sg.t0+ua*T))-p0-D*qa)/(qa+c); Q = D+L
        cj = np.where(u < ua, c*(-12.0)/ua**3, 0.0)
        J = np.outer(_q3(u), Q)+np.outer(cj, L)
        return float(_norm(J).max())/T**3
    return None

D2_COEF = (35+104+114+56+11)/12   # core.deriv's one-sided second-difference weights, summed

def _da_noise(f, t, vm, vp):
    """The rounding floor of |a+ - a-| from two one-sided 5-point stencils at
    h = core.H: each of the 5 evaluations is good to eps(|p| + |v||t|) (the
    position's own ulp plus the time's ulp carried at speed), so each side
    is good to D2_COEF eps(|p| + |v||t|)/h^2. Without it a linear sweep's
    knot at t ~ 50 s, 28 m/s reads |da| ~ 0.02 m/s^2 of pure rounding, while
    a_peak of two linear neighbours is 0. Plus the 1e-3 m/s^2 the row allows."""
    eps = np.finfo(float).eps; p = float(np.abs(np.asarray(f(t))).max())
    v = max(float(np.abs(vm).max()), float(np.abs(vp).max()))
    return 1e-3+2*D2_COEF*eps*(p+v*abs(t))/H**2

@functools.lru_cache(maxsize=None)
def ring_corners(S, aid):
    """The rendered rings' own velocity corners, which no knot declares: the
    zero crossings of today's |damped sine| bounces (Rig.recoil's 'bounce'
    on a stepped mallet, every 1/(2 f) after the hit until the gate closes at
    the next approach; Rig.head_angle's check on a hinged hammer, every
    1/(2 f) after `end` until t_free), and the recoil gate's ends (C1, probed
    for completeness). -> ((t, 'ring'|'gate'), ...)"""
    rig = S.rig; sch = rig.sched[aid]; out = []
    if rig.hammer(aid):
        f = R.HAMMER['check'][1]
        for s in sch:
            end, free = float(s['end']), float(s['t_free']); m = 1
            while end+m/(2*f) < free-1e-12: out.append((end+m/(2*f), 'ring')); m += 1
    elif rig.stepped(aid):
        f = R.RECOIL['bounce'][1]; tau0 = R.RECOIL['bounce'][2]
        # a declared mallet (PLAYERS M1) has no |sine| bounce (no 'recoil.bounce'
        # ring) and gates its x/z rings at the next stroke's t_apex
        native = S.stroke(aid) is not None
        bounce = any(r['name'] == 'recoil.bounce' for r in S.declared(aid).rings) if native else True
        for k, s in enumerate(sch):
            hit = float(s['hit'])
            gate_end = float(sch[k+1]['t_apex' if native else 'approach']) if k+1 < len(sch) else math.inf
            if k+1 < len(sch): out += [(gate_end-R.RECOIL_GATE, 'gate'), (gate_end, 'gate')]
            if not bounce: continue
            stop = min(gate_end, hit+40*tau0, S.total)          # e^-40: rung out
            m = 1
            while hit+m/(2*f) < stop-1e-12: out.append((hit+m/(2*f), 'ring')); m += 1
    return tuple(out)

def r6_smoothness(S):
    out = []
    for aid in S.arms:
        f = path_fn(S, aid); D = S.declared(aid); sm = seg_samples(S, aid)
        segs = _finite_segments(S, aid)
        apk = {id(x['seg']): (0.0 if x['hold'] else x['a_peak']) for x in sm}
        def a_peak_at(t):
            return max([apk.get(id(sg), 0.0) for sg in segs if sg.t0-1e-9 <= t <= sg.t1+1e-9] or [0.0])
        imp_t = _knot_times(S, aid, SEG.IMPULSES)
        dv_cache = {}
        def jump(t):
            if t not in dv_cache:
                vm, vp = deriv(f, t, -1, 1), deriv(f, t, +1, 1)
                dv_cache[t] = (vm, vp)
            return dv_cache[t]
        # 6a, one judgement per knot TIME: segments._today declares a smooth
        # knot at both a travel's end and the strike's start, which coincide
        # (and a click at a travel's go); an impulse anywhere at t makes t an impulse.
        at_t = {}
        for k in D.knots:
            if math.isfinite(k.t): at_t.setdefault(k.t, []).append(k)
        n_sm = 0; bad_v = 0; bad_a = 0; worst_v = 0.0; worst_a = 0.0; at = []; by_fail = {}
        imp_dv = {}; undeclared = 0; imp_bad = 0
        for t, ks in sorted(at_t.items()):
            vm, vp = jump(t); dv = float(np.linalg.norm(vp-vm))
            imp = [k for k in ks if k.kind in SEG.IMPULSES]
            if imp:
                k = imp[0]; imp_dv.setdefault(k.kind, []).append(dv)
                if k.dv is None: undeclared += 1
                elif np.linalg.norm(vp-vm-np.asarray(k.dv, float)) > 1e-3+1e-3*np.linalg.norm(k.dv): imp_bad += 1
                continue
            am, ap = deriv(f, t, -1, 2), deriv(f, t, +1, 2); da = float(np.linalg.norm(ap-am))
            lim = .05*a_peak_at(t)+_da_noise(f, t, vm, vp)
            n_sm += 1; bv = dv > 1e-3; ba = da > lim
            bv = bool(bv); ba = bool(ba); bad_v += int(bv); bad_a += int(ba); worst_v = max(worst_v, dv); worst_a = max(worst_a, da/lim)
            if bv or ba:
                kk = '+'.join(sorted({k.kind for k in ks})); by_fail[kk] = by_fail.get(kk, 0)+1
                if len(at) < 6: at.append(round(t, 3))
        out.append(Result(6, '6a smooth knots', aid,
                          dict(knots=n_sm, fail_dv=bad_v, fail_da=bad_a, fail_by_kind=by_fail, max_dv=_r(worst_v, 3), max_da_ratio=_r(worst_a, 2), at=at),
                          (bad_v+bad_a == 0) if n_sm else None,
                          '|dv| <= 1e-3 m/s and |da| <= 0.05 a_peak (larger adjoining segment) + the stencil\'s rounding floor, at smooth, click and place knots'))
        imp_v = {kind: _mm(x, 1, 3) for kind, x in imp_dv.items()}
        if not imp_dv:
            out.append(Result(6, '6a impulse knots', aid, dict(knots=0), True, 'no impulse knots'))
        elif undeclared:
            out.append(Result(6, '6a impulse knots', aid, dict(knots=sum(map(len, imp_dv.values())), undeclared=undeclared, dv=imp_v), None,
                              'the rig declares no dv at its impulse knots yet: measured |dv| reported'))
        else:
            out.append(Result(6, '6a impulse knots', aid, dict(knots=sum(map(len, imp_dv.values())), fail=imp_bad, dv=imp_v), imp_bad == 0,
                              'measured dv = declared dv within 1e-3 m/s + 0.1 %'))
        # 6b on the rendered contact point (what the film shows: rule 4 lets
        # velocity jump only at a declared impulse, and its "what goes" names
        # the |sine| bounce): every branch point of the path plus the rings'
        # own corners.
        fr = rendered_fn(S, aid)
        n6b = 0; by = {}; w6b = 0.0; at6b = []; off_knots = 0
        kind_at = {t: '+'.join(sorted({k.kind for k in ks})) for t, ks in at_t.items()}
        all_t = _knot_times(S, aid)
        probes = {float(t): kind_at.get(t, 'internal') for t in breakpoints(S, aid)}
        for t, what in ring_corners(S, aid):
            if 0 < t < S.total: probes.setdefault(float(t), what)
        for t, what in sorted(probes.items()):
            dv = float(np.linalg.norm(deriv(fr, t, +1, 1)-deriv(fr, t, -1, 1)))
            if dv <= .02: continue
            if not _near(all_t, t, 20e-6): off_knots += 1
            if not _near(imp_t, t, 20e-6):
                n6b += 1; by[what] = by.get(what, 0)+1; w6b = max(w6b, dv)
                if len(at6b) < 6: at6b.append(round(float(t), 3))
        old = sum(float(np.linalg.norm(jump(t)[1]-jump(t)[0])) > .1 for t in at_t)
        out.append(Result(6, '6b corners', aid, dict(count=n6b, by=by, max_dv=_r(w6b, 3), at=at6b, off_knots=off_knots, **{'at_knots_0.1': old}),
                          (n6b == 0) if probes else None, '|dv| > 0.02 m/s (one-sided 5-point, 10 us) more than 20 us from an impulse knot, on the rendered contact point, '
                          'at every branch point of the path and every ring corner (by: the knot kind there, internal = a law\'s own joint, ring = a |sine| zero); '
                          'off_knots: away from any declared knot (the row\'s literal wording); at_knots_0.1: path |dv| > 0.1 m/s at knot times (the scratch count)'))
        # 6c
        if S.stroke(aid) is not None:
            out.append(_r6c_channels(S, aid))
        else:
            out.append(_r6c(S, aid, sm, f))
        laws = sorted({sg.law for sg in segs})
        bad_laws = [l for l in laws if l not in ALLOWED_LAWS]
        out.append(Result(6, '6c laws', aid, dict(laws=laws, not_allowed=bad_laws), not bad_laws,
                          "allowed: 3-4-5, 4-5-6-7, cycloidal, modified sine/trapezoid, servo S-curve, quintic/septic Hermite, ballistic ('linear' = ballistic at a = 0)"))
    return out

def _r6c_channels(S, aid):
    """Ruler 6c on a mallet's declared channels (DESIGN 7.4): every segment,
    holds included, judged on its own channel's signal against its declared
    jerk (or the closed form): max |da| per 1 ms <= 1.1 J 1e-3 + 1e-3."""
    rows = {ch: dict(segments=0, fail=0, worst_ratio=0.0) for ch in SEG.CHANNELS}
    undeclared = {}; na = {}; src = {}; worst = (0.0, None, None, None); dvc = []; low = 0
    for x in chan_samples(S, aid):
        sg = x['seg']; ch = x['channel']; cf = _closed_jerk(S, aid, x); J, why = _declared_jerk(x, cf)
        if cf is not None and sg.extra.get('jerk') is not None and sg.law != 'hold':
            r_ = float(sg.extra['jerk'])/cf if cf > 0 else (1.0 if float(sg.extra['jerk']) == 0 else math.inf)
            dvc.append(r_); low += r_ < 1-1e-6
        if J is None:
            d = undeclared if why == 'undeclared' else na; d[sg.law] = d.get(sg.law, 0)+1; continue
        if not x['pair_ok'].any(): continue
        src[why] = src.get(why, 0)+1
        dd = _norm(np.diff(x['a'], axis=0)); da = dd[x['pair_ok']]
        ratio = float(da.max()/(1.1*J*STEP+1e-3))
        r = rows.setdefault(ch, dict(segments=0, fail=0, worst_ratio=0.0))
        r['segments'] += 1; r['fail'] += ratio > 1; r['worst_ratio'] = max(r['worst_ratio'], ratio)
        if ratio > worst[0]:
            worst = (ratio, sg.law, float(x['t'][int(np.argmax(np.where(x['pair_ok'], dd, 0)))]), f'{ch}:{sg.tag}')
    for r in rows.values(): r['worst_ratio'] = _r(r['worst_ratio'], 3)
    checked = sum(r['segments'] for r in rows.values()); fail = sum(r['fail'] for r in rows.values())
    v = dict(segments=checked, fail=fail, worst_ratio=_r(worst[0], 3), worst_law=worst[1], worst_t=_r(worst[2], 3),
             worst_seg=worst[3], na=na, undeclared=undeclared, bound=src, by_channel=rows,
             declared_over_closed=dict(min=_r(min(dvc), 6), max=_r(max(dvc), 6), n=len(dvc)) if dvc else None,
             declared_below_closed=low)
    passed = False if fail or undeclared or low else (None if na or not checked else True)
    return Result(6, '6c jerk', aid, v, passed,
                  'per channel (carriage: ring-free x + y_c/z_c blend; head: path - carriage), holds included: '
                  'max |da| per 1 ms <= 1.1 J 1e-3 + 1e-3, J = min(the segment\'s declared jerk, this ruler\'s closed form on '
                  'its law and declared boundary data: carriage 3-4-5 60|D|/T^3, a glide\'s hermite halves / ballistic cruise '
                  'peak |x\'\'\'| x |p1 - p0|/|x1 - x0|; head hermite / ballistic / 3-4-5 through the arc), hold 0; a declared jerk below its closed form fails; ballistic and quintic Hermite need a '
                  'declared jerk (undeclared = fail)')

def _r6c(S, aid, sm, f):
    """Ruler 6c on the path signal against today's laws' closed forms (every arm but a declared mallet)."""
    checked = 0; fail = 0; na = {}; worst = (0.0, None, None)
    for x in sm:
        if x['hold']: continue
        J = _jerk_bound(x, f); sg = x['seg']
        if J is None:
            na[sg.law] = na.get(sg.law, 0)+1; continue
        if not x['pair_ok'].any(): continue
        da = _norm(np.diff(x['a'], axis=0))[x['pair_ok']]
        lim = 1.1*J*STEP+1e-3; ratio = float(da.max()/lim)
        checked += 1; fail += ratio > 1
        if ratio > worst[0]: worst = (ratio, sg.law, float(x['t'][int(np.argmax(np.where(x['pair_ok'], _norm(np.diff(x['a'], axis=0)), 0)))]))
    v = dict(segments=checked, fail=fail, worst_ratio=_r(worst[0], 3), worst_law=worst[1], worst_t=_r(worst[2], 3), na=na)
    return Result(6, '6c jerk', aid, v, False if fail else (None if na or not checked else True),
                  'max |da| per 1 ms <= 1.1 C_j h/T^3 1e-3'+(f'; no closed-form jerk bound for {sorted(na)}' if na else ''))

# ---- gravity scale (ruler 9) -----------------------------------------------------
def r9_gravity(S):
    out = []
    for aid in S.arms:
        rows = [r for r in prep(S, aid) if r['T_down'] > 0]
        s = np.array([G*r['T_down']**2/(2*r['h_apex']) if r['h_apex'] > 0 else math.inf for r in rows])
        d = np.array([r['h_apex'] for r in rows]); T = np.array([r['T_down'] for r in rows])
        if S.kind(aid) not in STRUCK:
            # a pluck's approach and the rake's sweep run across gravity, not along it
            out.append(Result(9, '9 gravity scale', aid, dict(approaches=len(s), s=_mm(s, 1, 4)), INFO,
                              'info: s = g T^2 / 2d over apex -> contact; plucks and sweeps are not strokes gravity acts along'))
            continue
        if not rows:
            out.append(Result(9, '9 gravity scale', aid, dict(strokes=0), None, 'no strokes on this arm')); continue
        f = point_fn(S, aid); s_seg = []
        for sg in _finite_segments(S, aid):
            if sg.tag != 'stroke': continue
            dd = abs(float(f(sg.t1)[1]-f(sg.t0)[1])); TT = sg.t1-sg.t0
            if dd > 0: s_seg.append(G*TT*TT/(2*dd))
        bad = int((s < .25-1e-12).sum())
        out.append(Result(9, '9 gravity scale', aid,
                          dict(strokes=len(s), s=_mm(s, 1, 4), fail=bad, d_m=_mm(d, 1, 3), T_ms=_mm(T, 1e3, 1),
                               s_stroke_segment=_mm(s_seg, 1, 4)),
                          bad == 0, 's = g/a, a = 2d/T^2 over the downstroke: d = h(t_apex), T = T_down (ruler 3/4\'s apex -> contact); '
                                    's_stroke_segment (info) spans the whole declared stroke segment, wind-up included'))
    return out

# ---- joints ------------------------------------------------------------------------
def joint_series(root, elbow, wrist):
    u = elbow-root; f = wrist-elbow
    sh = np.unwrap(np.arctan2(u[:, 1], u[:, 2])); fa = np.unwrap(np.arctan2(f[:, 1], f[:, 2]))
    cosel = -(u*f).sum(1)/(_norm(u)*_norm(f))
    return dict(x=root[:, 0], shoulder=sh, forearm=fa, rel=fa-sh, elbow=np.arccos(np.clip(cosel, -1, 1)))

def ik(S, aid, tips):
    """Rig.pose's IK (root above the tip on the rail, no sag) for tool points
    `tips` (N,3) -> root, elbow, wrist, reachable."""
    cfg = S.cfg(aid); tips = np.asarray(tips, float)
    root = np.c_[tips[:, 0], np.full(len(tips), cfg['root_y']), np.full(len(tips), cfg['root_z'])]
    wrist = tips+R.Rig.wrist_offset(cfg)
    delta = wrist-root; dist = _norm(delta); l1 = float(cfg['l1']); l2 = float(cfg['l2'])
    reach = (abs(l1-l2) <= dist) & (dist <= l1+l2)
    d = np.clip(dist, abs(l1-l2)+1e-5, l1+l2-1e-5); dirn = delta/dist[:, None]
    along = (l1*l1-l2*l2+d*d)/(2*d)
    hint = R.Rig.bend_hint(cfg); bend = hint-dirn*(dirn@hint)[:, None]
    bn = _norm(bend); bend = np.where(bn[:, None] < np.sqrt(1e-5), np.array([0, 0, -1.0]), bend/np.maximum(bn, 1e-12)[:, None])
    elbow = root+dirn*along[:, None]+bend*np.sqrt(np.maximum(0, l1*l1-along*along))[:, None]
    return root, elbow, wrist, reach

# ---- proximal -> distal, weight (ruler 15) ----------------------------------------
@functools.lru_cache(maxsize=None)
def khz(S, aid):
    """The rendered contact point on the 1 kHz grid, (t, p, mask, moving):
    sampled where it can move (everywhere on a stepped arm, whose rings ring
    through its rests; inside moving segments +-3 ms on a servo arm);
    `moving` marks the declared non-hold segments +-3 ms on either kind."""
    n = int(math.floor(S.total*1000))+1; t = np.arange(n)/1000.0
    moving = np.zeros(n, bool)
    for sg in _finite_segments(S, aid):
        if sg.law == 'hold': continue
        lo = max(int(math.floor(sg.t0*1000))-3, 0); hi = min(int(math.ceil(sg.t1*1000))+3, n-1)
        if hi >= lo: moving[lo:hi+1] = True
    mask = np.ones(n, bool) if S.rig.stepped(aid) else moving
    f = rendered_fn(S, aid); p = np.zeros((n, 3))
    idx = np.nonzero(mask)[0]
    if idx.size: p[idx] = np.array([f(tt) for tt in t[idx]])
    return t, p, mask, moving

def r15_proximal(S):
    out = []
    for aid in S.arms:
        kind = S.kind(aid); rig = S.rig; C = S.contacts(aid); by_hit = {round(c.t, 9): c for c in C}
        fseg = _finite_segments(S, aid)
        sweep_at = {round(sg.t0, 9): sg for sg in fseg if sg.tag == 'sweep'}
        # a stroke runs into its contact and, for a strum, on through the sweep
        # (the sweep is the stroke across the strings, not a travel or shift)
        strokes = [(sg.t0, sweep_at[round(sg.t1, 9)].t1 if round(sg.t1, 9) in sweep_at else sg.t1, sg.t1)
                   for sg in fseg if sg.tag == 'stroke']
        lag_w = []; lag_a = []; bad_order = 0; n_order = 0; bad_share = 0; bad_car = 0; shares = []; peak = dict(sh=0.0, el=0.0, fa=0.0)
        for s0, s1, s_hit in strokes:
            ts = np.arange(s0+STEP/2, s1, STEP)
            if len(ts) < 5: continue
            Ps = [rig.pose(aid, tt) for tt in ts]
            root = np.array([p['root'] for p in Ps]); elbow = np.array([p['elbow'] for p in Ps]); wrist = np.array([p['wrist'] for p in Ps])
            q = joint_series(root, elbow, wrist)
            w = {j: np.gradient(q[j], STEP) for j in ('x', 'shoulder', 'rel', 'forearm')}
            al = {j: np.gradient(w[j], STEP) for j in ('x', 'shoulder', 'rel')}
            peak['sh'] = max(peak['sh'], float(np.abs(w['shoulder']).max())); peak['el'] = max(peak['el'], float(np.abs(w['rel']).max()))
            peak['fa'] = max(peak['fa'], float(np.abs(w['forearm']).max()))
            contrib = np.array([np.abs(w['x']).sum(), (np.abs(w['shoulder'])*_norm(wrist-root)).sum(),
                                (np.abs(w['rel'])*_norm(wrist-elbow)).sum()])*STEP
            tot = contrib.sum()
            if tot <= 0: continue
            sh = contrib/tot; shares.append(sh)
            if not (sh[0] <= sh[1]+1e-9 and sh[1] <= sh[2]+1e-9): bad_share += 1
            if sh[0] > .15+1e-9: bad_car += 1
            c = by_hit.get(round(s_hit, 9)); ioi = c.ioi if c else math.inf
            elig = [j for j, s in zip(('x', 'shoulder', 'rel'), sh) if s >= .10]
            if len(elig) < 2: continue
            n_order += 1; ok = True
            lag_ok = (lambda L: L >= FRAME-1e-9) if ioi >= .35 else (lambda L: L > 1e-9)
            for prox, dist in zip(elig, elig[1:]):
                lw = ts[np.argmax(np.abs(w[dist]))]-ts[np.argmax(np.abs(w[prox]))]
                la = ts[np.argmax(np.abs(al[dist]))]-ts[np.argmax(np.abs(al[prox]))]
                lag_w.append(lw); lag_a.append(la)
                if not (lag_ok(lw) and lag_ok(la)): ok = False
            bad_order += not ok
        sh_arr = np.array(shares) if shares else np.zeros((0, 3))
        Ph = S.poses(aid, 'hz'); qh = joint_series(Ph['root'], Ph['elbow'], Ph['wrist'])
        whole = {j: _r(np.degrees(np.abs(np.gradient(qh[j], Ph['t'])).max()), 0) if len(Ph['t']) > 2 else None
                 for j in ('shoulder', 'forearm')}
        out.append(Result(15, '15 order', aid,
                          dict(strokes=n_order, fail=bad_order, lag_omega_ms=_mm(lag_w, 1e3, 1), lag_alpha_ms=_mm(lag_a, 1e3, 1),
                               peak_dps=dict(shoulder=_r(np.degrees(peak['sh']), 0), elbow=_r(np.degrees(peak['el']), 0), forearm=_r(np.degrees(peak['fa']), 0)),
                               piece_120hz_dps=dict(upper_link=whole['shoulder'], forearm=whole['forearm'])),
                          (bad_order == 0) if n_order else (True if shares else None),
                          'joints with >= 10 % share of a stroke (into the contact, through the sweep for a strum): peak |omega| and |alpha| '
                          'proximal -> distal (distal strictly later, 1 ms samples), >= 1 frame apart at IOI >= 0.35 s; '
                          'peak_dps over strokes (elbow = interior-angle rate, forearm = its world angle); piece_120hz_dps: link angular speed over the piece at 120 Hz'
                          +('' if n_order else '; no stroke moves two joints with >= 10 %')))
        out.append(Result(15, '15 shares', aid,
                          dict(strokes=len(shares), carriage=_r(np.median(sh_arr[:, 0]), 3) if len(shares) else None,
                               shoulder=_r(np.median(sh_arr[:, 1]), 3) if len(shares) else None,
                               elbow=_r(np.median(sh_arr[:, 2]), 3) if len(shares) else None,
                               fail_distal=bad_share, fail_carriage=bad_car),
                          (bad_share+bad_car == 0) if shares else None,
                          'per stroke (into the contact, through the sweep for a strum) share |J_j dq_j|, medians shown: '
                          'non-decreasing carriage <= shoulder <= elbow; carriage <= 15 %'))
        # tip acceleration
        t, p, mask, moving = khz(S, aid)
        a = np.zeros(len(t)); ok = mask.copy(); ok[0] = ok[-1] = False; ok[1:-1] &= mask[:-2] & mask[2:]
        i = np.nonzero(ok)[0]; a[i] = _norm(p[i+1]-2*p[i]+p[i-1])/(STEP*STEP)
        excl = np.zeros(len(t), bool)
        for c in C:
            lo = max(int(math.floor((c.t-.01)*1000)), 0); hi = min(int(math.ceil((c.t_end+.01)*1000)), len(t)-1)
            excl[lo:hi+1] = True
        for c0, c1 in S.click_intervals(aid):
            lo = max(int(math.floor(c0*1000)), 0); hi = min(int(math.ceil(c1*1000)), len(t)-1)
            excl[lo:hi+1] = True
        sel = a[ok & ~excl]/G; mv = a[ok & ~excl & moving]/G
        p99 = float(np.percentile(mv, 99)) if mv.size else 0.0
        k = int(np.argmax(np.where(ok & ~excl, a, 0)))
        out.append(Result(15, '15 tip accel', aid, dict(p99_g=_r(p99, 1), max_g=_r(a[k]/G, 1), t_max=_r(t[k], 3),
                                                      ms_over_10g=int((sel > 10).sum())),
                          bool(sel.max() <= 10) if sel.size else None,
                          'rendered contact point, 1 kHz second differences, outside +-10 ms of contacts (to t_end) and click intervals; <= 10 g; '
                          'p99 over the declared moving segments, max over every sample'+(' (rings included, rests too)' if rig.stepped(aid) else '')))
        if not rig.stepped(aid):
            x = p[:, 0]; vx = np.zeros(len(t)); ax_ = np.zeros(len(t))
            vx[i] = (x[i+1]-x[i-1])/(2*STEP); ax_[i] = (x[i+1]-2*x[i]+x[i-1])/(STEP*STEP)
            kv = int(np.argmax(np.abs(vx))); ka = int(np.argmax(np.abs(ax_)))
            ko = int(np.argmax(np.where(excl, 0, np.abs(ax_))))
            within = bool(abs(vx[kv]) <= R.SERVO_V_MAX+1e-9 and abs(ax_[ka]) <= 3*G)
            out.append(Result(15, '15 carriage', aid, dict(v_max=_r(abs(vx[kv]), 3), t_v=_r(t[kv], 3), a_max_g=_r(abs(ax_[ka])/G, 1), t_a=_r(t[ka], 3),
                                                           a_max_off_contact_g=_r(abs(ax_[ko])/G, 1), within_rule=within),
                              INFO, f'servo carriage = root x = tip x (1 kHz); row 15 sets no carriage limit, the rules say <= SERVO_V_MAX '
                                    f'{R.SERVO_V_MAX} m/s and <= 3 g (within_rule); the off-contact max excludes the same windows as the tip'))
        # phases
        mv = [sg for sg in _finite_segments(S, aid) if sg.law != 'hold']
        short = [sg for sg in mv if sg.t1-sg.t0 < 2.5*FRAME-1e-9]; tags = {}
        for sg in short: tags[sg.tag] = tags.get(sg.tag, 0)+1
        out.append(Result(15, '15 phases', aid, dict(phases=len(mv), short=len(short), by_tag=tags,
                                                   min_frames=_r(min((sg.t1-sg.t0) for sg in mv)*FPS, 2) if mv else None),
                          (not short) if mv else None, 'declared segments other than holds >= 2.5 frames'))
        out.append(Result(15, '15 weight', aid, {}, None, 'no part masses declared (manifest masses arrive in M4)'))
        if kind == 'pick':
            out.append(Result(15, '15 digit closing', aid, {}, None, 'no digits yet (M7)'))
    return out

# ---- joint use and limits (ruler 16) -------------------------------------------------
def _span_points(S, aid):
    rig = S.rig; geo = S.layout['strings']; lift = rig.hover(aid); pts = []
    for sid in rig.acts[aid].get('reach', [rig.acts[aid]['home']]):
        s = geo[sid]; a = np.asarray(s['a'], float); b = np.asarray(s['b'], float)
        us = np.linspace(.2, .8, 13) if s['struck'] else np.linspace(.05, .95, 19)
        for u in us:
            p = a*(1-u)+b*u; pts.append(p); pts.append(p+lift)
    return np.array(pts)

@functools.lru_cache(maxsize=None)
def _joint_track(S, aid):
    P = S.poses(aid, 'hz'); t = P['t']
    extra = [S.rig.pose(aid, c.t) for c in S.contacts(aid)]
    tt = np.r_[t, [c.t for c in S.contacts(aid)]]
    root = np.vstack([P['root']]+[[e['root'] for e in extra]] if extra else [P['root']])
    elbow = np.vstack([P['elbow']]+[[e['elbow'] for e in extra]] if extra else [P['elbow']])
    wrist = np.vstack([P['wrist']]+[[e['wrist'] for e in extra]] if extra else [P['wrist']])
    o = np.argsort(tt, kind='mergesort')
    q = joint_series(root[o], elbow[o], wrist[o])
    return tt[o], dict(carriage=q['x'], shoulder=np.degrees(q['shoulder']), elbow=np.degrees(q['elbow']))

def _union_len(q, mask):
    """|U q| over the kept samples: q is continuous in time, so each run of
    consecutive kept samples sweeps [min, max] of its own; the runs'
    intervals are merged (a 'home' segment cut out can leave a hole)."""
    idx = np.nonzero(mask)[0]
    if idx.size == 0: return 0.0
    cuts = np.nonzero(np.diff(idx) > 1)[0]+1
    iv = sorted((float(q[r].min()), float(q[r].max())) for r in np.split(idx, cuts))
    tot = 0.0; lo, hi = iv[0]
    for a, b in iv[1:]:
        if a > hi: tot += hi-lo; lo, hi = a, b
        else: hi = max(hi, b)
    return tot+hi-lo

def r16_joints(S):
    out = []
    for aid in S.arms:
        C = S.contacts(aid)
        pts = _span_points(S, aid); root, elbow, wrist, reach = ik(S, aid, pts)
        cfg = S.cfg(aid)
        sound = reach & (np.abs(_norm(elbow-root)-float(cfg['l1'])) < 1e-3) & (np.abs(_norm(wrist-elbow)-float(cfg['l2'])) < 1e-3)
        if not sound.any():
            out.append(Result(16, '16 coverage', aid, dict(reachable=0), None, 'no reachable span point')); continue
        u = elbow[sound]-root[sound]; sh = np.arctan2(u[:, 1], u[:, 2])
        ref = math.atan2(np.sin(sh).mean(), np.cos(sh).mean()); sh = ref+np.angle(np.exp(1j*(sh-ref)))
        qs = joint_series(root[sound], elbow[sound], wrist[sound])
        span = dict(carriage=float(np.ptp(qs['x'])), shoulder=float(np.degrees(np.ptp(sh))),
                    elbow=float(np.degrees(np.ptp(qs['elbow']))))
        tt, Q = _joint_track(S, aid)
        home = [sg for sg in _finite_segments(S, aid) if sg.tag == 'home']
        keep = np.ones(len(tt), bool)
        for sg in home: keep &= ~((tt >= sg.t0) & (tt <= sg.t1))
        piece = {j: (_union_len(Q[j], keep)/span[j] if span[j] > 0 and keep.any() else None) for j in span}
        # phrases
        phr = []; cur = []
        for c in C:
            if cur and c.gap >= 1.5: phr.append(cur); cur = []
            cur.append(c)
        if cur: phr.append(cur)
        pc = {j: [] for j in span}
        for ph in phr:
            a = float(ph[0].sched['go']); b = float(ph[-1].sched['t_free'])
            m = keep & (tt >= a) & (tt <= b)
            for j in span: pc[j].append(_union_len(Q[j], m)/span[j] if m.any() and span[j] > 0 else 0.0)
        out.append(Result(16, '16 coverage piece', aid,
                          dict(span=dict(carriage_m=_r(span['carriage'], 3), shoulder_deg=_r(span['shoulder'], 1), elbow_deg=_r(span['elbow'], 1)),
                               cover={j: _r(v, 3) for j, v in piece.items()}, reachable=f'{int(reach.sum())}/{len(reach)}',
                               ik_degenerate=int((reach & ~sound).sum())),
                          all(v is not None and v >= .40-1e-9 for v in piece.values()) if C else None,
                          'C_j = |q_j used| / IK span (picks 0.05-0.95, bars 0.2-0.8, contact and hover) >= 40 % over the piece; '
                          'span points where Rig.pose\'s bend hint is parallel to root->wrist (the IK degenerates) are left out'))
        out.append(Result(16, '16 coverage phrase', aid,
                          dict(phrases=len(phr), **{j: dict(min=_r(min(v), 3), p50=_r(np.median(v), 3), ok=int(sum(x >= .25-1e-9 for x in v)))
                                                     for j, v in pc.items() if v}),
                          all(x >= .25-1e-9 for v in pc.values() for x in v) if phr else None,
                          '>= 25 % per phrase for carriage, shoulder and elbow (phrases split at gaps >= 1.5 s)'+('' if phr else '; no contacts, no phrase')))
        # untagged path, reversals
        sm = seg_samples(S, aid); f = path_fn(S, aid)
        untagged = sum(x['length'] for x in sm if not x['hold'] and x['seg'].tag not in SEG.TAGS)
        segs = sorted(S.declared(aid).segments, key=lambda sg: sg.t0); hole = 0.0; holes = 0
        cover_to = -math.inf
        for sg in segs:
            if sg.t0 > cover_to+1e-9:
                holes += 1
                ts = np.arange(max(cover_to, 0.0), min(sg.t0, S.total)+STEP/2, STEP)
                if len(ts) > 1:
                    pp = np.array([f(t) for t in ts]); hole += float(_norm(np.diff(pp, axis=0)).sum())
            cover_to = max(cover_to, sg.t1)
        if cover_to < S.total-1e-9: holes += 1
        by_tag = {}
        for x in sm:
            if not x['hold']: by_tag[x['seg'].tag] = by_tag.get(x['seg'].tag, 0.0)+x['length']
        out.append(Result(16, '16 untagged path', aid, dict(m=_r(untagged+hole, 4), uncovered_spans=holes,
                                                            tagged_m={k: _r(v, 2) for k, v in sorted(by_tag.items())}),
                          untagged+hole <= 1e-9 and holes == 0,
                          "path length in segments whose tag is outside segments.TAGS (the goal's closed vocabulary) or in time no segment covers"))
        nrev = 0; excess = 0; worst = 0
        for x in sm:
            if x['hold'] or not x['valid'].any(): continue
            sg = x['seg']; X = x['p']-x['p'].mean(0)
            if np.ptp(x['p'], axis=0).max() < 1e-9: continue
            ax = np.linalg.svd(X, full_matrices=False)[2][0]
            s = (x['v'][x['valid']]@ax); s = s[np.abs(s) > 1e-4]
            n = int(np.sum(np.sign(s[1:]) != np.sign(s[:-1]))) if s.size > 1 else 0
            own = _own_reversals(S, aid, x)
            nrev += n
            if own is not None and n > own: excess += 1; worst = max(worst, n-own)
        out.append(Result(16, '16 reversals', aid, dict(reversals=nrev, segments_over=excess, worst_excess=worst),
                          excess == 0, "velocity reversals along the segment's principal axis <= the law's own (3-4-5, S-curve, linear 0; quintic+sine, quintic+cocked 1; ratchet: its own clicks)"))
        out.append(Result(16, '16 limits', aid, {}, None, 'no joint limits declared (M4)'))
    return out

_OWN = {'quintic': 0, 'scurve': 0, 'linear': 0, 'quintic+sine': 1, 'quintic+cocked': 1}

def _own_reversals(S, aid, x):
    law = x['seg'].law
    if law in _OWN: return _OWN[law]
    if law != 'ratchet': return None
    sg = x['seg']
    s = next((s for s in S.rig.sched[aid] if s['moving'] and abs(float(s['go'])-sg.t0) < 1e-9), None)
    if s is None: return None
    T = float(s['approach']-s['go']); dx = float(s['first'][0]-s['rest'][0])
    n = R.clicks(dx, T); over = R.OVERSHOOT*min(1.0, R.PITCH*n/max(abs(dx), 1e-6))
    taus = x['t'][x['valid']]
    xp = np.array([R.ratchet((tt+HC-sg.t0)/T, n, T, over) for tt in taus]); xm = np.array([R.ratchet((tt-HC-sg.t0)/T, n, T, over) for tt in taus])
    v = (xp-xm)*dx; v = v[np.abs(v)*(1/(2*HC)) > 1e-4]
    return int(np.sum(np.sign(v[1:]) != np.sign(v[:-1]))) if v.size > 1 else 0

RULERS = {1: r1_strobe, 3: r3_preparation, 4: r4_action, 5: r5_rest, 6: r6_smoothness,
          9: r9_gravity, 15: r15_proximal, 16: r16_joints}

"""Ruler for the mallet's stroke as the Rig plays it (PLAYERS M1, "mallets
ride the bounce"; formlab/stroke.py driven by formlab/rig.py).

    python3 tools/test_stroke.py                       # both built assets
    python3 tools/test_stroke.py LAYOUT.json SCORE.json

formlab/stroke.py plans a mallet arm's path in closed form; the Rig turns it
into what renders and what the rulers read. This holds the Rig to it:

  - the joint-angle conventions the homing sweep turns (Rig: ik, joint_series,
    span_points, joint_spans) are ruler 16's exactly (tools/players/r_motion.py
    ik / joint_series / _span_points, r_machine._joint_spans);
  - the homing sweep: x home -> lo -> hi -> home tooth by tooth, then the elbow
    and the shoulder swept one at a time in joint space for the cfg AS IT IS
    (a changed cfg re-derives them), >= 0.9 of reach_x and >= 0.8 of each
    span, the tool <= 0.5 SERVO_V_MAX, landing on the home rest to 1e-9 m,
    at home unless home is near another mechanism's reach;
  - path_at is the stroke's ring-free path; the tip adds the recoil's x and z
    rings (no bounce, zero at each contact, gated by the next apex) and the
    detent ring; the root rides carriage_x (path x + detent, no recoil);
  - the bus, the clicks (one a tooth), the pawl ride and the schedule's new
    fields;
  - Rig.declared: the mallet's own contract (channels, tags, laws, extras,
    knots, rings, prep, native), and every other arm's unchanged reading;
  - every float that hands over to a driven rise ('wind-up', 'raise') is
    carried to its park (the next 'stroke''s apex, or the coda's last hold) without stopping more
    than LOW_REV below it; a float that comes to rest short of its park is
    one the planner tags 'catch' (ruler 8 judges the shape either way, A11);
  - the plan as asked: no ArmStroke.issues entry on any mallet arm (a
    downstroke, float or Dahl loop out of its bounds, a wind-up with no room,
    a freewheel under the hurried ceilings, a late go...). The stroke records
    an issue instead of hiding it; on the assets this runs on, none may stand.
"""
import json, math, sys
from pathlib import Path
import numpy as np
ROOT = Path(__file__).resolve().parents[1]
for p in (str(ROOT), str(ROOT/'tools')):
    if p not in sys.path: sys.path.insert(0, p)
from formlab import rig as R
from formlab import stroke as ST
from formlab import segments as SEG
from formlab.rig import Rig
from players import r_motion as RM
from players import r_machine as RMa

failures = []
def check(ok, msg):
    print(('  PASS ' if ok else '  FAIL ')+msg)
    if not ok: failures.append(msg)

class _S:
    """The slice of tools/players/core.Subject the ruler functions mirrored here read."""
    def __init__(self, rig, layout): self.rig = rig; self.layout = layout
    def cfg(self, aid): return self.layout['arms'][aid]

HEAD_TAGS = {'float', 'rebound', 'catch', 'wind-up', 'hold', 'stroke', 'raise', 'home'}
CAR_TAGS = {'travel', 'hold', 'home'}

def mirrors(rig, S, aid):
    """Rig's joint-angle definitions against ruler 16's, bit for bit."""
    cfg = S.cfg(aid)
    pts = rig.span_points(aid); ref = RM._span_points(S, aid)
    rng = np.random.default_rng(7)
    probe = np.r_[pts, pts+rng.normal(0, .15, pts.shape)]
    a = R.ik(cfg, probe); b = RM.ik(S, aid, probe)
    same_ik = all(np.array_equal(x, y) for x, y in zip(a, b))
    qa = R.joint_series(*a[:3]); qb = RM.joint_series(*b[:3])
    same_q = all(np.array_equal(qa[k], qb[k]) for k in qb)
    sp = rig.joint_spans(aid); sr = RMa._joint_spans(S, aid)
    check(np.array_equal(pts, ref) and same_ik and same_q and sp == sr,
          f'{aid}: span points, ik, joint_series and the IK spans are ruler 16\'s exactly '
          f'(shoulder {math.degrees(sp[0]):.2f} deg, elbow {math.degrees(sp[1]):.2f} deg)')

def homing(rig, S, aid):
    hj = rig._home_joints(aid); st = rig.stroke(aid); cfg = S.cfg(aid)
    homes = rig.homes(aid, rig.joint_site(aid))
    if not homes:
        check(hj is None, f'{aid}: no home cue, no homing sweep'); return
    h0, h1, lo, hi, legs = homes[0]
    # where: at home unless home is near another mechanism's reach
    xh = float(rig.contact(rig.acts[aid]['home'])[0])
    site = rig.joint_site(aid); xs = {round(float(st.x(g['t0'])), 9) for g in hj['legs']}
    check(len(xs) == 1 and abs(xs.pop()-(xh if site is None else site)) < 1e-9,
          f'{aid}: the joint sweeps happen at {"home" if site is None else f"x {site:.3f} (home is near another mechanism)"}')
    # the joints, as ruler 16 measures them off the posed arm, are the commanded angles
    ts = np.unique(np.r_[np.arange(hj['t0'], hj['t1'], .005), hj['t1']])
    P = rig.poses(aid, ts); q = R.joint_series(P['root'], P['elbow'], P['wrist'])
    f = hj['legs'][0]['frame']; err = 0.0; sag = float(np.abs(P['root'][:, 1]-cfg['root_y']).max())
    for k, t in enumerate(ts):
        g = rig._home_q(hj, t)
        jn, qq = (g[0]['joint'], g[1]) if g is not None else ('elbow', 0.0)
        want_e = f['e0']+qq if jn == 'elbow' else f['e0']
        want_s = f['sh0']+qq if jn == 'shoulder' else f['sh0']
        err = max(err, abs(q['elbow'][k]-want_e), abs(R._wrap(q['shoulder'][k]-want_s)))
    check(err < 1e-9 and sag < 1e-12, f'{aid}: the posed joints are the commanded joint sweep (worst {err:.1e} rad, rail sag {sag:.0e})')
    # coverage over the whole sweep window, on the ruler's measures
    tw = np.unique(np.r_[np.arange(h0, h1, 1/240), h1]); Pw = rig.poses(aid, tw); qw = R.joint_series(Pw['root'], Pw['elbow'], Pw['wrist'])
    sp = rig.joint_spans(aid); rlo, rhi = cfg['reach_x']
    cov = dict(x=float(np.ptp(Pw['root'][:, 0]))/(rhi-rlo), shoulder=float(np.ptp(qw['shoulder']))/sp[0], elbow=float(np.ptp(qw['elbow']))/sp[1])
    check(cov['x'] >= .9 and cov['shoulder'] >= .8-1e-9 and cov['elbow'] >= .8-1e-9,
          f'{aid}: the sweep covers ' + ', '.join(f'{k} {v:.3f}' for k, v in cov.items()) + ' (>= 0.9 reach_x, >= 0.8 span)')
    path = np.array([rig.path_at(aid, t) for t in tw]); v = np.linalg.norm(np.gradient(path, tw, axis=0), axis=1)
    check(v.max() <= .5*R.SERVO_V_MAX, f'{aid}: the tool moves <= 0.5 SERVO_V_MAX through the sweep (peak {v.max():.3f} m/s)')
    end = rig.path_at(aid, h1); rest = rig.contact(rig.acts[aid]['home'])+rig.hover(aid)
    land = max(float(np.linalg.norm(end-rest)), abs(rig.carriage_x(aid, h1)-rest[0]))
    check(land <= 1e-9, f'{aid}: the sweep lands on the home rest (contact + hover) to {land:.1e} m')
    # one channel at a time: x still through the joint legs, the head still through the x legs
    xj = np.array([rig.carriage_x(aid, t) for t in ts])
    xlegs = [g for g in legs if g[2] == 'x']
    hx = max((float(np.ptp([rig.path_at(aid, t)[1:] for t in np.linspace(a, b, 200)], axis=0).max()) for a, b, *_ in xlegs), default=0.0)
    check(float(np.ptp(xj)) == 0.0 and hx == 0.0, f'{aid}: the carriage is still through the joint legs and the head through the x legs')
    # a different cfg re-derives the joint sweep (the rail search mutates the cfg per candidate)
    was = dict(cfg); before = rig.path_at(aid, .5*(hj['t0']+hj['t1']))
    try:
        cfg['root_y'] = float(cfg['root_y'])+.05; cfg['l1'] = float(cfg['l1'])+.03
        hk = rig._home_joints(aid); Pk = rig.poses(aid, ts); qk = R.joint_series(Pk['root'], Pk['elbow'], Pk['wrist'])
        fk = hk['legs'][0]['frame']; errk = 0.0
        for k, t in enumerate(ts):
            g = rig._home_q(hk, t); jn, qq = (g[0]['joint'], g[1]) if g is not None else ('elbow', 0.0)
            errk = max(errk, abs(qk['elbow'][k]-(fk['e0']+(qq if jn == 'elbow' else 0.0))),
                       abs(R._wrap(qk['shoulder'][k]-(fk['sh0']+(qq if jn == 'shoulder' else 0.0)))))
        moved = float(np.linalg.norm(rig.path_at(aid, .5*(hj['t0']+hj['t1']))-before))
        check(hk is not hj and errk < 1e-9 and moved > 1e-4,
              f'{aid}: a changed cfg re-derives the sweep in joint space (worst {errk:.1e} rad; the mid-sweep tool moves {moved*1000:.1f} mm)')
    finally:
        cfg.clear(); cfg.update(was)
    check(np.array_equal(rig.path_at(aid, .5*(hj['t0']+hj['t1'])), before), f'{aid}: and restoring the cfg restores the sweep exactly')

def rings_and_path(rig, aid):
    st = rig.stroke(aid); hj = rig._home_joints(aid); sched = rig.schedule(aid)
    total = float(rig.score['total_s'])
    ts = np.r_[np.arange(-1, total+1, 1/240), [k.t for k in st.knots]]
    inj = np.zeros(len(ts), bool)
    if hj is not None: inj = (ts > hj['t0']) & (ts < hj['t1'])
    diff = max(float(np.abs(rig.path_at(aid, t)-st.p(t)).max()) for t in ts[~inj])
    check(diff == 0.0, f'{aid}: path_at is the stroke\'s ring-free path outside the homing joint legs ({len(ts)} samples)')
    hits = [float(s['hit']) for s in sched]
    tip = max(float(np.linalg.norm(rig.pose(aid, s['hit'])['tip']-s['first'])) for s in sched)
    rz = max(float(np.linalg.norm(rig.recoil(aid, t))) for t in hits)
    check(tip < 1e-12 and rz == 0.0, f'{aid}: the posed tip is on every contact ({tip:.1e} m) and the recoil exactly zero there')
    N = sorted(st.notes, key=lambda n: n.t)
    gated = max((float(np.linalg.norm(rig.recoil(aid, n1.t_apex))) for n1 in N[1:]), default=0.0)
    ys = max(abs(float(rig.recoil(aid, t)[1])) for t in ts[::7])
    live = min(max(float(np.linalg.norm(rig.recoil(aid, n.t+dt))) for dt in np.arange(.005, .04, .005)) for n in N)
    check(gated == 0.0 and ys == 0.0 and live > 1e-3,
          f'{aid}: the recoil rings x and z only (no bounce), live in a blow\'s wake (least {live*1000:.1f} mm), gated to 0 by the next apex')
    sub = ts[::5]; bad_root = bad_tip = 0.0
    for t in sub:
        p = rig.pose(aid, t); cx = rig.carriage_x(aid, t)
        bad_root = max(bad_root, abs(p['root'][0]-cx), abs(cx-(st.x(t)+st.detent(t))))
        bad_tip = max(bad_tip, abs(p['tip'][0]-(rig.path_at(aid, t)[0]+rig.recoil(aid, t)[0]+st.detent(t))))
    check(bad_root == 0.0 and bad_tip < 1e-15, f'{aid}: root.x = carriage_x = path x + detent; tip = path + recoil + detent')
    # the detent ring: 0.3-1.0 x OVERSHOOT x PITCH past each stepped landing, measured on carriage_x
    rr = []
    for tv in st.travels:
        if tv['regime'] not in ('step', 'home'): continue
        sg = 1 if tv['x1'] > tv['x0'] else -1; lands = [k.t for k in st.knots if k.kind == 'detent' and k.extra.get('travel') == tv['id']]
        xs = [tv['x0']+(tv['x1']-tv['x0'])*(k+1)/tv['teeth'] for k in range(tv['teeth'])]
        for tl, xl in zip(sorted(lands), xs):
            u = np.linspace(tl, tl+.06, 121); rr.append(max(sg*(rig.carriage_x(aid, x)-xl) for x in u)/(R.OVERSHOOT*R.PITCH))
    check(not rr or (.3 <= min(rr) and max(rr) <= 1.0),
          f'{aid}: every stepped landing overshoots its detent by 0.3-1.0 x OVERSHOOT x PITCH on carriage_x '
          f'({len(rr)} landings, {min(rr, default=0):.2f}..{max(rr, default=0):.2f})')
    pr = [rig.pawl_ride(aid, t) for t in hits]; prs = [rig.pawl_ride(aid, t) for t in sub]
    check(max(pr) == 0.0 and 0.0 <= min(prs) and max(prs) <= 1.0, f'{aid}: the pawl ride is in [0, 1] and 0 at every contact (peak {max(prs):.2f})')
    # the pawl rides on freewheels only: exactly 0 across every stepped and homing travel (it stops on every
    # detent, so the pawl drops each tooth), the smoothstep of the tooth rate across a freewheel, and a freewheel
    # whose peak rate is past the band's foot does ride somewhere
    lo, hi = ST.PAWL_RIDE_BAND; sm = lambda u: u*u*(3-2*u)
    step_peak = free_err = 0.0; never = []; nfree = nstep = 0
    for tv in st.travels:
        clicks = [c for c in tv['clicks'] if tv['t0'] < c < tv['t1']]
        u = np.r_[np.arange(tv['t0'], tv['t1'], 1/240)[1:], clicks]
        if not len(u): continue
        ride = np.array([rig.pawl_ride(aid, float(t)) for t in u])
        if tv['regime'] == 'freewheel':
            nfree += 1; rate = np.abs(st.x(u, 1))/R.PITCH
            free_err = max(free_err, float(np.abs(ride-sm(np.clip((rate-lo)/(hi-lo), 0.0, 1.0))).max()))
            if rate.max() > lo and ride.max() <= 0.0: never.append(round(tv['t0'], 3))
        else:
            nstep += 1; step_peak = max(step_peak, float(np.abs(ride).max()))
    check(step_peak == 0.0, f'{aid}: the pawl never rides on a stepped or homing travel ({nstep} travels, peak {step_peak:.3f})')
    check(free_err < 1e-12 and not never,
          f'{aid}: across a freewheel the ride is the smoothstep of |x\'|/PITCH over PAWL_RIDE_BAND ({nfree} travels, '
          f'worst {free_err:.1e}), and rides wherever the rate passes the band\'s foot (never riding: {never})')
    ck = rig.click_times(aid); teeth = sum(tv['teeth'] for tv in st.travels)
    lands = sorted(k.extra['t_end'] for k in st.knots if k.kind == 'click' and 't_end' in k.extra)
    stepped_at = all(any(abs(t-l) < 1e-12 for t, _ in ck) for l in lands)
    check(len(ck) == teeth and all(n == 1.0 for _, n in ck) and stepped_at,
          f'{aid}: one click a tooth, (t, 1.0) each ({len(ck)} for {teeth} teeth), a stepped tooth\'s at its landing')
    bl = rig.blows_by_arm[aid]
    ok = all(abs(b['energy']-float(s['event'].get('amp', 1.0))) == 0 and b['t'] == s['hit'] for b, s in zip(bl, sched))
    ok &= all(b['gate_end'] == (N[i+1].t_apex if i+1 < len(N) else np.inf) and b['v_in'] == N[i].v_in and b['e'] == N[i].e for i, b in enumerate(bl))
    check(ok and len(bl) == len(sched), f'{aid}: each blow carries the score amp as its energy, v_in and e, gated by the next apex')
    ok = all(s['go'] == s['tm'] and s['t_head_free'] == s['hit'] and s['t_apex'] < s['hit'] and 'arrive' in s for s in sched)
    check(ok, f'{aid}: the schedule keeps go == t_move and gains t_head_free (the contact), t_apex and arrive')

def contract(rig, aid):
    D = rig.declared(aid); st = rig.stroke(aid)
    check(D.native and D.prep is ST.prep and all(abs(D.prep(n.a_raw, n.ioi)-n.h) <= 1e-12 for n in st.notes),
          f'{aid}: declared natively, with stroke.prep the prep every note was planned to')
    ok = True; msg = []
    for ch in ('head', 'carriage'):
        cs = sorted([g for g in D.segments if g.extra.get('channel') == ch], key=lambda g: g.t0)
        cov = cs[0].t0 == -np.inf and cs[-1].t1 == np.inf and all(a.t1 == b.t0 and b.t1 > b.t0 for a, b in zip(cs, cs[1:]))
        ok &= cov; msg.append(f'{ch} {len(cs)}')
    ok &= all(g.extra.get('channel') in ('head', 'carriage') for g in D.segments)
    check(ok, f'{aid}: each channel covers (-inf, inf) with no hole and no overlap ({", ".join(msg)} segments)')
    tags = all(g.tag in SEG.TAGS and g.tag in (HEAD_TAGS if g.extra['channel'] == 'head' else CAR_TAGS) for g in D.segments)
    laws = {g.law for g in D.segments}
    check(tags and laws <= set(SEG.LAWS), f'{aid}: tags from segments.TAGS per channel; laws {sorted(laws)}')
    ex = True; why = []
    for g in D.segments:
        e = g.extra
        if g.law != 'hold' and math.isfinite(g.t1-g.t0):
            if not (isinstance(e.get('jerk'), float) and math.isfinite(e['jerk'])): ex = False; why.append(('jerk', g.tag, g.t0))
        if g.tag == 'stroke' and not (len(e.get('pin', [])) == 3 and e.get('axis') == [1.0, 0.0, 0.0]): ex = False; why.append(('pin', g.t0))
        if e['channel'] == 'carriage' and g.tag in ('travel', 'home') and g.law != 'hold' or (e['channel'] == 'carriage' and 'regime' in e):
            if not (e.get('regime') in SEG.REGIMES and isinstance(e.get('travel'), int) and isinstance(e.get('hurried'), bool)): ex = False; why.append(('regime', g.t0))
        if g.law == 'quintic hermite' and not all(k in e for k in ('p0', 'v0', 'a0', 'p1', 'v1', 'a1')): ex = False; why.append(('hermite', g.t0))
        if e['channel'] == 'head' and g.tag == 'home' and e.get('joint') not in ('elbow', 'shoulder'): ex = False; why.append(('joint', g.t0))
        if g.tag == 'hold' and e['channel'] == 'head' and e.get('hold') not in SEG.HOLD_KINDS: ex = False; why.append(('hold', g.t0))
    check(ex, f'{aid}: every segment carries its declared extras (jerk, pin/axis, regime/travel/hurried, p0..a1, joint, hold) {why[:3]}')
    # the homing joint legs' declared jerk bounds the posed tool's (finite differences of path_at)
    hj = rig._home_joints(aid); worst = 0.0
    for g in [g for g in D.segments if g.tag == 'home' and g.extra['channel'] == 'head']:
        h = 2e-3; tt = np.arange(g.t0+2*h, g.t1-2*h, (g.t1-g.t0)/200)
        P = lambda t: rig.path_at(aid, t)
        j = [np.linalg.norm((P(t+2*h)-2*P(t+h)+2*P(t-h)-P(t-2*h))/(2*h**3)) for t in tt]
        worst = max(worst, max(j)/g.extra['jerk'])
    check(hj is None or worst <= 1.01, f'{aid}: the homing joint legs\' declared jerk bounds the tool\'s (measured/declared {worst:.3f})')
    K = D.knots; kinds = {k.kind for k in K}
    dv = max((float(np.linalg.norm(k.dv-np.array([0.0, (1+k.extra['e'])*k.extra['v_in'], 0.0]))) for k in K if k.kind == 'contact'), default=0.0)
    ncont = sum(k.kind == 'contact' for k in K)
    clk = [k for k in K if k.kind == 'click']
    ck_ok = all({'k', 'n', 'regime', 'pawl', 'travel'} <= set(k.extra) and k.extra['pawl'] in ('drop', 'ride')
                and (('t_end' in k.extra) == (k.extra['regime'] in ('step', 'home'))) for k in clk)
    det = {round(k.t, 9) for k in K if k.kind == 'detent'}
    det_ok = det == {round(k.extra['t_end'], 9) for k in clk if 't_end' in k.extra} and all(np.array_equal(k.dv, np.zeros(3)) for k in K if k.kind == 'detent')
    check(kinds <= {'contact', 'click', 'detent', 'smooth'} and ncont == len(st.notes) and dv <= 1e-12 and ck_ok and det_ok,
          f'{aid}: knots: {ncont} contacts with dv = (0, (1+e) v_in, 0), {len(clk)} clicks (t_end only stepped/home), {len(det)} detents at the landings')
    imp = np.array(sorted(k.t for k in K if k.kind in SEG.IMPULSES)); sm = {round(k.t, 9) for k in K if k.kind == 'smooth'}
    joins = set()
    for ch in ('head', 'carriage'):
        cs = sorted([g for g in D.segments if g.extra['channel'] == ch], key=lambda g: g.t0); joins |= {g.t0 for g in cs[1:]}
    bare = [t for t in joins if round(t, 9) not in sm and not (imp.size and np.min(np.abs(imp-t)) <= 1e-9)]
    check(not bare, f'{aid}: every join of either channel is a declared knot ({len(joins)} joins)')
    names = sorted(r['name'] for r in D.rings)
    check(names == sorted(['recoil.x', 'recoil.z', 'stand_thump', 'rail_sag', 'mast_sway', 'detent'])
          and next(r for r in D.rings if r['name'] == 'detent')['channel'] == 'root.x',
          f'{aid}: rings {names} (no recoil.bounce)')

def handovers(rig, aid):
    st = rig.stroke(aid); heads = sorted(st.segments('head'), key=lambda g: g.t0); bad = []; n = 0
    for k, g in enumerate(heads[:-1]):
        if g.tag != 'float' or heads[k+1].tag not in ('wind-up', 'raise'): continue
        # the park the rise ends at: the next downstroke's start (its apex), or the coda's last hold
        park = next((q.t0 for q in heads[k+1:] if q.tag == 'stroke'), heads[-1].t0)
        if park is None or park-g.t1 < 2/240: continue
        n += 1; ts = np.arange(g.t1, park, 1/240); h = np.array([float(st.h(t)) for t in ts])
        still = (np.abs(np.gradient(h, ts)) < ST.STILL_V) & (h < float(st.h(park))-ST.LOW_REV)
        run = best = 0
        for x in still: run = run+1 if x else 0; best = max(best, run)
        if best/240 > 1/30: bad.append((round(g.t0, 3), heads[k+1].tag, round(best/240*1e3, 1)))
    check(not bad, f'{aid}: every float handed to a driven rise reaches its park without stopping short '
                   f'({n} handovers'+(f'; short: {bad[:4]}' if bad else '')+')')

def issues(rig, aid):
    """Every issue the stroke recorded on this arm fails (the planner keeps going and says so: a gate must see it)."""
    iss = rig.stroke(aid).issues
    check(not iss, f'{aid}: the stroke records no issues ({len(iss)}'+(': '+'; '.join(
        f"{i['what']} at {i['t']:.3f} s" for i in iss[:4])+(' ...' if len(iss) > 4 else '') if iss else '')+')')

def others(rig, aid):
    D = rig.declared(aid); T = SEG._today(rig, aid)
    same = (not D.native and D.segments == T.segments and len(D.knots) == len(T.knots)
            and all(a.t == b.t and a.kind == b.kind and a.extra == b.extra for a, b in zip(D.knots, T.knots)) and D.rings == T.rings)
    check(same and rig.stroke(aid) is None and rig.pawl_ride(aid, 1.0) == 0.0,
          f'{aid} ({rig.acts[aid]["kind"]}): declared is today\'s reading of its schedule, unchanged; no stroke')

def unplaced(score, layout, rig):
    """layout_search.plan_arms builds its Rig before the rail search has placed
    any root: a mallet's plan may not need a cfg, and once the search writes
    one the Rig poses exactly what a Rig built on the placed layout does."""
    import copy
    from formlab import layout_search as LS
    bare = copy.deepcopy(layout); mallets = [a for a in rig.plans if rig.plans[a] and rig.mallet(a)]
    for aid in mallets:
        for k in LS.CFG_KEYS: bare['arms'][aid].pop(k, None)     # what the rail search chooses
    try:
        r0 = Rig(score, bare); built = True
    except Exception as e:
        check(False, f'a Rig builds on a layout whose mallets have no cfg yet ({type(e).__name__}: {e})'); return
    same_plan = all([n.t_apex for n in r0.stroke(a).notes] == [n.t_apex for n in rig.stroke(a).notes]
                    and r0.click_times(a) == rig.click_times(a) for a in mallets)
    check(built and same_plan, f'a Rig builds on a layout whose mallets have no cfg yet, with the same plan ({len(mallets)} mallets)')
    for aid in mallets: r0.geometry['arms'][aid].update(copy.deepcopy(layout['arms'][aid]))
    worst = 0.0
    for aid in mallets:
        hj = rig._home_joints(aid); ts = np.r_[np.linspace(hj['t0'], hj['t1'], 41), np.linspace(-1, float(score['total_s']), 401)]
        for t in ts:
            a, b = r0.pose(aid, float(t)), rig.pose(aid, float(t))
            worst = max(worst, max(float(np.abs(a[k]-b[k]).max()) for k in ('root', 'elbow', 'wrist', 'tip')))
    check(worst < 1e-12, f'...and once the search writes the cfg it poses what a Rig on the placed layout does (worst {worst:.1e} m)')

def run(layout_path, score_path):
    print(f'== {layout_path.name} / {score_path.name}')
    layout = json.loads(layout_path.read_text()); score = json.loads(score_path.read_text())
    rig = Rig(score, layout); S = _S(rig, layout)
    check(rig.pushed == [], 'the rig pushes no start (one occupancy model)')
    for aid in rig.plans:
        if not rig.plans[aid]: continue
        if rig.mallet(aid):
            mirrors(rig, S, aid); homing(rig, S, aid); rings_and_path(rig, aid); contract(rig, aid); handovers(rig, aid); issues(rig, aid)
        else:
            others(rig, aid)
    unplaced(score, layout, rig)

if __name__ == '__main__':
    if len(sys.argv) > 2: pairs = [(Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve())]
    else: pairs = [(ROOT/'harness/assets/clockwork.json', ROOT/'render/chamber/score.json'),
                   (ROOT/'harness/assets/clockwork_expanded.json', ROOT/'render/clockwork/score.json')]
    for lp, sp in pairs: run(lp, sp)
    print('STROKE: '+('FAIL' if failures else 'PASS'))
    sys.exit(1 if failures else 0)

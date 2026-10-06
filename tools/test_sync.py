"""Ruler 22's sync on the servo arms and mallets against D8 (PLAYERS A25), and
ruler 1's links measure against its copy in the rail plan (A28).

    python3 tools/test_sync.py          # the built assets (core.ASSETS: harness/assets/clockwork*.json, render/*/score.json)

D8 (docs/motion-design.md; tools/players/r_machine._sync_targets_m) classes
every carriage travel [a, b] of a declaring arm by where it ends, the first
class that applies: a 'travel->hold' target (the head enters an arrival hold
from the go on: a poise, the cocked hold, and on a servo a hover or park it
enters at or after the go), judged on the carriage's arrival past that hold's
start (hold_skew <= SKEW_MAX) and the in-position window; a strike into the
first contact after the go, crossing none: ending at most SKEW_MAX after it
(a carriage landing later moved under the pluck or hit, late into its
strike), and on it (at most a frame before it) or in the head's run-up to it
(the head moving at b, not in a 'release', and running on to that contact
with no head hold and no 'release' starting between); else unjudged, which
FAILS the row. This holds:

  - the shipped classification, on both assets: no travel unjudged, every
    servo strike ending in its head's 'stroke' or 'wind-up', every mallet
    strike on its contact (counts printed);
  - the mutation grid, in memory on the chamber (the arm's Rig.stroke swapped
    for a re-timed copy of its own plan; nothing on disk changes), each case
    with its D8 class and the arm's 'sync' row: a target's row PASSES at
    |d| <= 2 ms and FAILS at every |d| > SKEW_MAX, a strike's PASSES (rulers
    19 and 11 judge it), an unjudged travel's FAILS:
      shift   harp_arm1's 2.55 mm y/z ride 31.9607-32.0357 onto the 32.0357
              hover, moved d ms (the same S-curve and duration). Early into
              the 31.79 pluck's release (-150, -80, -40): the head is on its
              way out of a contact, no run-up: unjudged. Within a frame of
              the hover (-30, -10, +5, +20) or late into it (+60): a target
              on the hover. Leaving after the hover began (+300, +450, +700):
              the head waits in the hover or runs up into the 32.96 poise,
              no run-up: unjudged. Moved onto the 31.79 pluck itself (-250):
              a strike into that contact, by D8's own rule (it is rulers 19
              and 11's to judge, not sync's), so the row is monotone in d
              only until the ride's end reaches another contact's strike;
      comp    the same ride, same go, ending 40 ms early (in the release):
              unjudged;
      late    a strike's travel, same go, landing d ms late. harp_arm0's
              25.05-25.6243 (the stroke's run-up to the 25.7143 pluck, a
              release after it): +93 lands 3 ms past the pluck, a strike;
              +95, +110, +200 land 5, 20, 110 ms past it, crossed: unjudged.
              harp_arm2's 13.6214-13.66 (the wind-up's run-up to the 13.75
              pluck, the next wind-up straight after it, no release): +95,
              +100, +135 land 5, 10, 45 ms past it, in that wind-up: unjudged.
              bars_arm0's 47.5-47.8571 (a mallet's, onto its 47.8571 hit, the
              float after it): +5, +20 land 5, 20 ms past it: unjudged;
      stretch the ride, same go, landing 100 and 450 ms late: a target on the
              hover the head entered after the go, hold_skew > SKEW_MAX
              (round 3's fix: the old rule left it unjudged, or past 450 ms a
              strike into the next wind-up);
      open    the ride moved -150 ms with harp_arm1's declared head re-read in
              memory so that no hold follows the 31.79 pluck's release before
              the 33.21 pluck (the 32.0357 hover and 32.9643 poise declared as
              moving): only the 'release at b' term makes it no run-up, so
              unjudged. And moved -300 ms (landing in the stroke 50 ms before
              the 31.79 pluck) with that pluck also not played, so its release
              starts at no contact: only the 'release starting in [b, c)' term
              makes it no run-up, so unjudged. On the motion as built every
              release starts at its contact and reaches a hold before the next
              (A25), so neither term decides a class there; these hold them.
    Each of these rulers fails here: one that takes a release, or a run-up
    interrupted by a hold, for a strike (the early, far-late, comp and open
    cases); one that takes a contact the travel crossed for a strike, or
    reads a strike's contact off b (the late cases on harp_arm2 and
    bars_arm0); one whose after-contact bound is wider than 4 ms (late +95 on
    harp_arm0) or narrower than 3 ms (+93); one that drops the servo's hover
    from the arrival holds (the +60 and stretched cases read unjudged, not
    late into the hover).

Ruler 1's '1 links' (tools/players/r_motion.r1_strobe) is the judge, so it
must not call the planner it judges; layout_search.plan_arms breaks a tie on
clearance.link_strobe, a copy of the same measure (A28). This holds the copy
to the ruler: clearance.MALLET_HEAD_R is r_motion.MALLET_R, the bar floor is
r_motion.LINK_W's expression, and link_strobe on the planner's own poses
(layout_search.evaluate_arm on the installed cfg, 30 Hz from -1 s) equals
max(upper, lower) of ruler 1's '1 links', unrounded, on the chamber's
installed rake, harp_arm1 and bars_arm0 rails and the expanded's blocks_arm0
(a hinged hammer, measured on its head: A28's other tie): every branch of
the measure, the tool capsule, the mallet's wound head and the hammer's head.
It checks that it would catch a drift: a perturbed MALLET_HEAD_R moves the
mallet's link_strobe off ruler 1's, and the hammer read on its tool capsule
moves blocks_arm0's.
"""
import copy, dataclasses, inspect, json, sys, time
from pathlib import Path
import numpy as np
ROOT = Path(__file__).resolve().parents[1]
for p in (str(ROOT), str(ROOT/'tools')):
    if p not in sys.path: sys.path.insert(0, p)
from formlab import servo as SV
from formlab import stroke as STK
from formlab import segments as SEG
from formlab import clearance as CL
from formlab import layout_search as LS
from formlab.rig import Rig
from players import core
from players import r_machine as MM
from players import r_motion as RM

SKEW_MAX = MM.SKEW_MAX       # 1/240 s: the sync budget, D8's 'late'
TOL_EQ = 1e-12               # the planner's strobe and ruler 1's: one measure, the same expressions in the same order
RIDE = ('harp_arm1', 32.0357)   # the y/z ride 31.9607-32.0357 (2.55 mm along y) onto the hover 32.0357-32.4743
LATE = ('harp_arm0', 25.6243)   # 25.05-25.6243, a strike in the stroke's run-up to the 25.7143 pluck (a release after it)
LATE2 = ('harp_arm2', 13.66)    # 13.6214-13.66, a strike in the wind-up's run-up to the 13.75 pluck (a wind-up after it)
HIT = ('bars_arm0', 47.8571)    # 47.5-47.8571, a mallet's travel onto its 47.8571 hit (a float after it)
OPEN = dict(moving=(32.0357, 32.9643))                       # harp_arm1's hover and poise between the 31.79 and 33.21 plucks, declared moving
OPEN_NC = dict(moving=(32.0357, 32.9643), drop=(31.7857,))   # ... and the 31.79 pluck not played
GRID = ([(RIDE, 'shift', d, c, None) for d, c in ((0, 'T'), (-2, 'T'), (2, 'T'), (-150, 'U'), (-80, 'U'), (-40, 'U'),
                                                   (-30, 'T'), (-10, 'T'), (5, 'T'), (20, 'T'), (60, 'T'),
                                                   (300, 'U'), (450, 'U'), (700, 'U'), (-250, 'S'))]
        + [(RIDE, 'comp', -40, 'U', None)]
        + [(LATE, 'late', d, c, None) for d, c in ((0, 'S'), (93, 'S'), (95, 'U'), (110, 'U'), (200, 'U'))]
        + [(LATE2, 'late', d, 'U', None) for d in (95, 100, 135)]
        + [(HIT, 'late', d, 'U', None) for d in (5, 20)]
        + [(RIDE, 'stretch', d, 'T', None) for d in (100, 450)]
        + [(RIDE, 'shift', -150, 'U', OPEN), (RIDE, 'shift', -300, 'U', OPEN_NC)])
ARRIVAL = {('shift', 60), ('stretch', 100), ('stretch', 450)}   # the hover taken only by the servo's arrival clause
MIRROR = {'chamber': ('rake_arm0', 'harp_arm1', 'bars_arm0'),   # the rake, a pick (the tool capsule), a mallet (its wound head)
          'expanded': ('blocks_arm0',)}                          # a hinged hammer (its head): A28's other tie

failures = []
def check(ok, msg):
    print(('  PASS ' if ok else '  FAIL ')+msg)
    if not ok: failures.append(msg)

def fresh_caches():
    for name in ('declared', 'poses'): getattr(core.Subject, name).cache_clear()

def play(S, aid, st):
    """S's rig plays `st` for arm aid (None: its own plan again); the Subject's stroke-dependent caches cleared."""
    S.rig.__dict__.pop('stroke', None)
    if st is not None:
        own = type(S.rig).stroke; rig = S.rig
        rig.stroke = lambda a: st if a == aid else own(rig, a)
    fresh_caches()

def relabel(S, aid, moving=(), drop=()):
    """S with arm aid's declared head and contacts re-read in memory (the motion stays the plan's; only what the
    classifier reads changes): each head hold starting at a time in `moving` declared as a moving 'wind-up' (the
    head runs on through it), each contact at a time in `drop` not played. relabel(S, aid) restores both."""
    for name in ('declared', 'contacts'): S.__dict__.pop(name, None)
    if not (moving or drop): return
    own_d, own_c = type(S).declared, type(S).contacts
    hit = lambda t, ts: any(abs(t-u) < 2e-4 for u in ts)
    def declared(a):
        d = own_d(S, a)
        if a != aid: return d
        segs = [SEG.Segment(g.t0, g.t1, 'quintic hermite', 'wind-up', g.event, {k: v for k, v in g.extra.items() if k != 'hold'})
                if g.extra.get('channel') == 'head' and g.law == 'hold' and hit(g.t0, moving) else g for g in d.segments]
        assert sum(g.extra.get('channel') == 'head' and g.law == 'hold' and hit(g.t0, moving) for g in d.segments) == len(moving)
        return dataclasses.replace(d, segments=segs)
    def contacts(a):
        cs = own_c(S, a)
        if a != aid: return cs
        assert sum(hit(c.t, drop) for c in cs) == len(drop)
        return tuple(c for c in cs if not hit(c.t, drop))
    S.declared, S.contacts = declared, contacts

def retimed(seg, t0=None, t1=None):
    """A constant carriage segment (a hold) with new ends."""
    for name in ('c', 'cy', 'cz'):
        c = getattr(seg, name, None)
        if c is not None and np.any(np.asarray(c, float)[1:] != 0): raise ValueError(f'{seg} is not constant')
    s = copy.copy(seg); s.extra = copy.deepcopy(seg.extra)
    if t0 is not None: s.t0 = t0
    if t1 is not None: s.t1 = t1
    return s

def reseg(s, a, b):
    """Carriage travel segment s on [a, b], the same path: a servo's S-curve rebuilt between the same ends, a
    mallet's polynomial (in local time from t0) moved and stretched (its coefficients scaled)."""
    if isinstance(s, SV.ScurveSeg): return SV.ScurveSeg(a, b, s.P0, s.P1, s.tag, s.event, copy.deepcopy(s.extra))
    n = copy.copy(s); n.extra = copy.deepcopy(s.extra); n.t0, n.t1 = a, b; k = (b-a)/(s.t1-s.t0)
    for name in ('c', 'cy', 'cz'):
        c = getattr(s, name, None)
        if c is not None: setattr(n, name, np.asarray(c, float)/k**np.arange(len(c)))
    return n

def rebuilt(base, car):
    """base's plan with carriage segments `car`."""
    if isinstance(base, STK.ArmStroke):
        st = copy.copy(base); st.carriage = STK.Channel('carriage', car)
        st.yc = STK.Channel('yc', car, 'cy'); st.zc = STK.Channel('zc', car, 'cz'); return st
    return type(base)(base.arm, base.n, list(base.head.segs), car, list(base.knots), base.notes, base.travels, base.issues)

def mutate(base, TB, kind, d):
    """base's plan with its carriage travel ending at TB re-timed: 'shift' moves it d s (the same path and
    duration), every other kind keeps its go and moves its end d s; the carriage holds on either side follow.
    -> (stroke, (a, b))"""
    car = list(base.carriage.segs)
    i = next(i for i, s in enumerate(car) if s.law != 'hold' and abs(s.t1-TB) < 2e-4); s = car[i]
    assert car[i-1].law == 'hold' and car[i+1].law == 'hold'
    a, b = (s.t0+d, s.t1+d) if kind == 'shift' else (s.t0, s.t1+d)
    assert car[i-1].t0 < a and b < car[i+1].t1, 'the holds either side are too short for this d'
    new = list(car); new[i] = reseg(s, a, b)
    if kind == 'shift': new[i-1] = retimed(car[i-1], t1=a)
    new[i+1] = retimed(car[i+1], t0=b)
    return rebuilt(base, new), (a, b)

def head_at(S, aid, t):
    return next((g for g in MM._decl_segments(S, aid, 'head') if g.t0 <= t+1e-9 < g.t1), None)

def shipped(S):
    """D8 on the motion as built: no travel unjudged; a servo strike ends in its run-up ('stroke' or 'wind-up'), a
    mallet's on its contact."""
    n = dict(targets=0, hold=0, servo=0, mallet=0); tags = {}; bad = []
    for aid in S.arms:
        if not (S.rig.sched.get(aid) and MM._native(S, aid)): continue
        tg, st_, uj = MM._sync_targets_m(S, aid); n['targets'] += len(tg); n['hold'] += sum(r[2] == 'travel->hold' for r in tg)
        bad += [f'{aid} {a:.4f}-{b:.4f} unjudged' for a, b in uj]
        ct = np.array(sorted(c.t for c in S.contacts(aid)))
        for a, b, *_ in st_:
            if MM._mallet(S, aid):
                n['mallet'] += 1; c = ct[np.argmin(np.abs(ct-b))]
                if not -1/MM.FPS-1e-9 <= b-c <= SKEW_MAX: bad.append(f'{aid} {a:.4f}-{b:.4f} ends {(b-c)*1e3:+.2f} ms off its contact')
            else:
                n['servo'] += 1; g = head_at(S, aid, b); tag = g.tag if g else None; tags[tag] = tags.get(tag, 0)+1
                if tag not in ('stroke', 'wind-up'): bad.append(f'{aid} {a:.4f}-{b:.4f} ends in {tag}')
    check(not bad and n['servo'], f'{S.asset}: D8 as built: {n["targets"]} targets ({n["hold"]} travel->hold, {n["targets"]-n["hold"]} home); {n["servo"]} servo strikes, '
          f'each ending in its run-up ({", ".join(f"{v} {k}" for k, v in sorted(tags.items()))}); {n["mallet"]} mallet strikes '
          f'on their contacts; 0 unjudged'+(f'; {"; ".join(bad[:6])}' if bad else ''))

def grid(S):
    """The mutation grid on the chamber (module docstring)."""
    aids = {case[0] for case, *_ in GRID}
    bases = {aid: S.rig.stroke(aid) for aid in aids}
    holds = {aid: [g for g in MM._decl_segments(S, aid, 'head') if g.tag == 'hold'] for aid in aids}
    cts = {aid: np.array(sorted(c.t for c in S.contacts(aid))) for aid in aids}
    for (aid, TB), kind, dms, want, spec in GRID:
        t = time.time(); d = dms/1e3
        st, (a, b) = mutate(bases[aid], TB, kind, d)
        play(S, aid, st if dms else None)
        try:
            relabel(S, aid, **(spec or {}))
            assert MM._native(S, aid)                           # ruler 22's sync is _sync_mallet's on this arm
            tg, st_, uj = MM._sync_targets_m(S, aid)
            T = [x for x in tg if abs(x[1]-b) < 1e-6]; St = [x for x in st_ if abs(x[1]-b) < 1e-6]; U = [x for x in uj if abs(x[1]-b) < 1e-6]
            cls = 'T' if T else 'S' if St else 'U' if U else '?'
            row = next(r for r in MM._sync_mallet(S, aid) if r.name == 'sync'); v = row.value
            g = head_at(S, aid, b)
        finally:
            relabel(S, aid)
        f = next((x for x in v.get('failing', []) if abs(x['t']-round(a, 3)) < 2e-3), None)
        why = []
        if cls != want: why.append(f'class {cls}, D8 wants {want}')
        if T:
            h = next(x for x in holds[aid] if abs(x.t0-T[0][4]) < 1e-12)
            if want == 'T' and not (h.extra.get('hold') == 'hover' and abs(h.t0-TB) < 2e-4):
                why.append(f'judged against the {h.extra.get("hold")} at {h.t0:.4f}, not the {TB} hover')
            if (kind, dms) in ARRIVAL and not (T[0][5] == 'arrival' and f and f.get('hold_skew_ms', 0) > SKEW_MAX*1e3):
                why.append(f'not read late into the hover (via {T[0][5]}, {f})')
        passes = abs(d) <= SKEW_MAX if want == 'T' else want == 'S'     # a strike is rulers 19 and 11's; unjudged FAILS
        if bool(row.passed) != passes: why.append(f'the row {"PASSES" if row.passed else "FAILS"}')
        hs = f' hold_skew {f["hold_skew_ms"]:.2f} ms' if f and 'hold_skew_ms' in f else ''
        sk = f' arrival skew {f["skew_ms"][1]:.2f} ms' if f else ''
        ct = cts[aid]; c = ct[np.searchsorted(ct, a+1e-9, side='right')]
        past = f', {(b-c)*1e3:+.2f} ms from the {c:.4f} contact' if kind == 'late' or want == 'S' else ''
        op = f' [head re-read: holds at {", ".join(map(str, spec["moving"]))} moving{"; contact " + ", ".join(map(str, spec["drop"])) + " not played" if spec.get("drop") else ""}]' if spec else ''
        check(not why, f'{aid} {kind} {dms:+d} ms{op} (lands {b:.4f}{past}, head in {g.tag if g else None}): class {cls}'
              f'{" on the hover" if T and not why else ""}{" (arrival)" if T and T[0][5] == "arrival" else ""}; sync '
              f'{"PASS" if row.passed else "FAIL"} {v.get("ok")}/{v.get("n")}{" unjudged "+str(v["unjudged"]["at"]) if v.get("unjudged") else ""}'
              f'{hs}{sk} ({"PASS" if passes else "FAIL"} wanted)'+(f'; {"; ".join(why)}' if why else '')+f' [{time.time()-t:.1f} s]')
    play(S, RIDE[0], None)

def strobe_mirror(S, aids):
    """Ruler 1's '1 links' against the rail plan's link_strobe on S's arms `aids` (module docstring)."""
    check(CL.MALLET_HEAD_R == RM.MALLET_R, f'clearance.MALLET_HEAD_R {CL.MALLET_HEAD_R} is r_motion.MALLET_R {RM.MALLET_R} '
          '(a mallet\'s wound head, the tool ruler 1 reads)')
    expr = "max(DEFAULT_SPEC['width'], DEFAULT_SPEC['depth'])"
    w = max(CL.DEFAULT_SPEC['width'], CL.DEFAULT_SPEC['depth'])
    check(RM.DEFAULT_SPEC is CL.DEFAULT_SPEC and RM.LINK_W == w and expr in inspect.getsource(CL.link_strobe)
          and f'LINK_W = {expr}' in inspect.getsource(RM),
          f'link_strobe\'s bar floor is r_motion.LINK_W\'s expression, {expr} = {w} m, on one DEFAULT_SPEC')
    layout, score = S.layout, S.score
    times = np.arange(-30, int(float(score['total_s'])*30)+1)/30; boxes = LS.scene_boxes(layout)
    rig = Rig(score, copy.deepcopy(layout)); arms, rr, spied = S.arms, RM._r, {}
    def spy(poses, caps, kind):
        spied.update(poses=poses, caps=caps, kind=kind); return CL.link_strobe(poses, caps, kind)
    try:
        RM._r = lambda x, nd=4: None if x is None else float(x)          # ruler 1's numbers unrounded
        for aid in aids:
            t = time.time(); kind = rig.acts[aid]['kind']; mid = layout['arms'][aid]['mid']
            pz = float(np.mean([s['a'][2] for s in layout['strings'].values() if s['mid'] == mid])) if kind != 'mallet' else None
            cfg = {k: layout['arms'][aid][k] for k in ('root_y', 'root_z', 'l1', 'l2', 'bend', 'wrist_offset')}
            LS.link_strobe = spy
            try: ev = LS.evaluate_arm(rig, aid, cfg, times, boxes=boxes, string_plane_z=pz)
            finally: LS.link_strobe = CL.link_strobe
            S.arms = {aid: arms[aid]}
            lk = next(r for r in RM.r1_strobe(S) if r.name == '1 links').value
            ruler = max(lk['upper']['ratio'], lk['lower']['ratio'])
            if ev is None: check(False, f'{S.asset} {aid}: evaluate_arm finds its installed rail infeasible'); continue
            check(abs(ev['strobe']-ruler) <= TOL_EQ and spied['kind'] == kind,
                  f'{S.asset} {aid} ({kind}) on its installed rail ({cfg["root_y"]:.2f}, {cfg["root_z"]:.2f}, l {cfg["l1"]:.2f}): '
                  f'the plan\'s link_strobe {ev["strobe"]!r} = ruler 1\'s \'1 links\' {ruler!r} (upper {lk["upper"]["ratio"]:.6f}, '
                  f'lower {lk["lower"]["ratio"]:.6f}; |diff| {abs(ev["strobe"]-ruler):.1e} <= {TOL_EQ:g}) [{time.time()-t:.1f} s]')
            if kind == 'mallet':
                was = CL.MALLET_HEAD_R
                try:
                    CL.MALLET_HEAD_R = was+.001; drift = CL.link_strobe(spied['poses'], spied['caps'], kind)
                finally:
                    CL.MALLET_HEAD_R = was
                check(abs(drift-ruler) > TOL_EQ and CL.link_strobe(spied['poses'], spied['caps'], kind) == ev['strobe'],
                      f'the mirror catches a drift: MALLET_HEAD_R {was} -> {was+.001:.3f} moves {aid}\'s link_strobe to {drift:.9f} '
                      f'(ruler 1 {ruler:.9f}; restored {ev["strobe"]:.9f})')
            if kind == 'hammer':
                drift = CL.link_strobe(spied['poses'], spied['caps'], 'pick')      # the head branch dropped: the tool capsule
                check('head' in spied['caps'] and abs(drift-ruler) > TOL_EQ,
                      f'the mirror catches a drift: {aid} read on its tool capsule, not its head (the hammer branch dropped), '
                      f'moves its link_strobe to {drift:.9f} (ruler 1 {ruler:.9f})')
    finally:
        RM._r = rr; S.arms = arms; LS.link_strobe = CL.link_strobe

if __name__ == '__main__':
    t0 = time.time()
    print('== chamber'); S = core.Subject('chamber'); shipped(S); grid(S); strobe_mirror(S, MIRROR['chamber'])
    print('== expanded'); S = core.Subject('expanded'); shipped(S); strobe_mirror(S, MIRROR['expanded'])
    print(f'SYNC: {"FAIL" if failures else "PASS"} ({time.time()-t0:.0f} s)')
    sys.exit(1 if failures else 0)

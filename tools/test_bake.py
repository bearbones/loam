"""Ruler for the motion bake (formlab/bake.py, `loam-motion/1`).

    python3 tools/test_bake.py                       # both built assets
    python3 tools/test_bake.py LAYOUT.json SCORE.json

The harness plays the performance back from the bake and owns no motion of its
own, so this is where "what Godot shows is what formlab.rig computed" is held:
  - the bake on disk is fresh: its fingerprints are the score's and the
    manifest's (a stale one fails with the command that remakes it);
  - every row is the rig's pose at that row's time, to float32;
  - every contact is a row, so the baked tip (a hinged hammer's felt face)
    lands on it exactly; no arm is ever unreachable;
  - between rows, linear interpolation stays within INTERP_M of the rig (the
    tool path, the links' pins) and within INTERP_RAD of the head's flip;
  - the assembly's shudders, the clicks and the pawl's one-tooth table are
    the rig's and formlab.pawl's;
  - a stepped arm's `.ride` channel is Rig.pawl_ride at the rows, in [0, 1] and
    0 at every contact (the hammer's all 0, no servo arm has one); the clicks'
    parallel click_pawl / click_step are a mallet stroke's click knots (the
    hammer's all drop and stepped); every blow is the rig's recoil bus (a
    mallet's with its stroke's v_in and e, gate_end the next stroke's apex);
    pawl.ride_angle is the table's least angle (the nose on a tip);
  - the harness's reader (harness/motion_bake.gd, via dev/dump_bake.gd) reads
    what formlab.bake.Bake reads, off the grid, and refuses a stale bake.
Godot parts are skipped when godot is not on the PATH.
"""
import json, shutil, subprocess, sys, tempfile
from pathlib import Path
import numpy as np
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT))
from formlab import bake as B
from formlab import pawl as W
from formlab import stroke as ST
from formlab.rig import Rig

INTERP_M = .005      # 5 mm: the worst an interpolated pin strays from the rig mid-slew
INTERP_RAD = .01
FLOAT32_M = 2e-6     # a stored position against the rig's float64 one

failures = []
def check(ok, msg):
    print(('  PASS ' if ok else '  FAIL ')+msg)
    if not ok: failures.append(msg)

def godot(score_path, asset):
    exe = shutil.which('godot')
    if exe is None: return None
    return subprocess.run([exe, '--headless', '--path', str(ROOT/'harness'), '-s', 'dev/dump_bake.gd', '--',
                           f'--score={score_path}', f'--asset={asset}'], capture_output=True, text=True, timeout=900).stdout

def parity(bake, score_path, asset):
    out = godot(score_path, asset)
    if out is None: print('  SKIP godot not on PATH: the harness reader unmeasured'); return
    pose = shud = pawl = ride = posed = lean = 0.0; n = ns = npw = nr = nl = 0; clicks = {}; marks = {}
    for line in out.splitlines():
        f = line.split()
        if not f: continue
        if f[0] == 'POSE':
            aid, t = f[1], float(f[2]); v = np.array(f[3:], float); n += 1
            row = bake.row(t)
            mine = np.concatenate([bake.get(f'{aid}.{k}', t, row) for k in ('root', 'elbow', 'wrist', 'tip')]
                                  + [bake.felt(aid, t), [bake.get(f'{aid}.head', t, row)]])
            pose = max(pose, float(np.abs(mine-v).max()))
        elif f[0] == 'SHUD':
            aid, t = f[1], float(f[2]); ns += 1; arm = bake.header['arms'][aid]
            stand = bake.get(f'{arm["mech"]}.stand', t) if f'{arm["mech"]}.stand' in bake.index else 0.0
            mine = np.array([stand, bake.get(f'{aid}.sag', t), bake.get(f'{aid}.sway', t)])
            shud = max(shud, float(np.abs(mine-np.array(f[3:], float)).max()))
        elif f[0] == 'RIDE':
            aid, t = f[1], float(f[2]); nr += 1; row = bake.row(t)
            ride = max(ride, abs(bake.ride(aid, t, row)-float(f[3])))
            posed = max(posed, abs(bake.pawl(aid, t)-float(f[4])))
        elif f[0] == 'PAWL':
            npw += 1; pawl = max(pawl, abs(bake.pawl_angle(float(f[1]))-float(f[2])))
        elif f[0] == 'PAWLR':
            nl += 1; lean = max(lean, abs(bake.pawl_angle(float(f[1]), float(f[2]))-float(f[3])))
        elif f[0] == 'CLICK':
            clicks.setdefault(f[1], []).append(float(f[2]))
            marks.setdefault(f[1], []).append((int(f[4]), int(f[5])) if len(f) >= 6 else None)
    check(n > 1000 and pose < 1e-6, f'the harness reads the poses the reference reader does: {n} off-grid samples, worst {pose:.1e}')
    check(ns > 1000 and shud < 1e-9, f'...and the shudders: {ns} samples, worst {shud:.1e}')
    check(npw > 1000 and pawl < 1e-6, f'...and the pawl table: {npw} rail positions, worst {pawl:.1e} rad')
    rides = [a for a in bake.header['arms'] if f'{a}.ride' in bake.index]
    check(nr > 1000*len(rides) and ride < 1e-6 and posed < 1e-6,
          f'...and the pawl\'s ride and its posed angle (MotionBake.ride / .pawl): {nr} samples over {len(rides)} arms, worst {ride:.1e} / {posed:.1e} rad')
    check(nl > 1000 and lean < 1e-6, f'...and the table leaned toward pawl.ride_angle by a ride: {nl} samples, worst {lean:.1e} rad')
    want = {aid: [c[0] for c in a['clicks']] for aid, a in bake.header['arms'].items() if a['clicks']}
    same = want.keys() == clicks.keys() and all(np.allclose(want[a], clicks[a], atol=1e-8) for a in want)
    check(same, f'...and the clicks: {sum(len(v) for v in clicks.values())} over {len(clicks)} arms')
    wm = {aid: [(c['pawl'], c['step']) for c in bake.clicks(aid)] for aid in want}
    check(wm.keys() == marks.keys() and all(wm[a] == marks[a] for a in wm),
          f'...and each click\'s pawl (ride / drop) and step (stepped / freewheel)')

def refuses_stale(score_path, asset):
    """A copy of the export whose score.json has changed by one byte: the
    harness must refuse the bake rather than play it."""
    if shutil.which('godot') is None: return
    json_path, bin_path = B.paths(score_path, asset)
    with tempfile.TemporaryDirectory() as d:
        d = Path(d)
        for p in Path(score_path).parent.iterdir():
            if p.is_dir(): (d/p.name).symlink_to(p)
            elif p.name != 'score.json': (d/p.name).symlink_to(p)
        (d/'score.json').write_text(Path(score_path).read_text()+'\n')
        out = godot(d/'score.json', asset)
    check('stale motion bake' in out and 'POSE' not in out, 'the harness refuses a bake made from another score')

def run(layout_path, score_path):
    asset = layout_path.stem
    print(f'== {asset} / {score_path}')
    json_path, _ = B.paths(score_path, asset)
    if not json_path.exists():
        check(False, f'no bake at {json_path}: run python3 tools/bake_motion.py --asset={asset}'); return
    bake = B.Bake(json_path); h = bake.header
    fresh = bake.fresh(score_path, layout_path)
    check(fresh, f'the bake is fresh (score and manifest fingerprints)' +
          ('' if fresh else f' — run python3 tools/bake_motion.py --asset={asset}'))
    if not fresh: return
    rig = Rig.load(score_path, layout_path)
    check(h['format'] == B.FORMAT and len(bake.times) == h['samples'] and np.all(np.diff(bake.times) > 0),
          f'{h["samples"]} rows x {h["width"]} channels, strictly increasing times from {h["t0"]:.2f} to {h["t1"]:.2f} s')
    # every row is the rig, to float32 (a sample of rows: the rig is slow)
    worst = 0.0
    for i in range(0, len(bake.times), 11):
        t = float(bake.times[i])
        for aid in rig.plans:
            p = rig.pose(aid, t)
            for k in ('root', 'elbow', 'wrist', 'tip'):
                worst = max(worst, float(np.abs(bake.frames[i, bake.index[f'{aid}.{k}']['offset']:][:3]-p[k]).max()))
    check(worst < FLOAT32_M, f'every row is the rig\'s pose at its time (worst {worst:.1e} m over {len(bake.times)//11} rows)')
    # contacts are rows, so they land exactly
    worst = 0.0; nc = 0
    for e in rig.score['events']:
        aid = e['actuator']
        for sid, t in zip(e['strings'], ST.motion_timing.string_times(e)):  # a roll's at its onsets
            nc += 1
            worst = max(worst, float(np.linalg.norm(bake.felt(aid, t)-rig.contact(sid, e.get('pick')))))
    check(worst < FLOAT32_M, f'every contact lands exactly: {nc} contacts, worst {worst:.1e} m')
    bad = {aid: a['unreachable'] for aid, a in h['arms'].items() if a['unreachable']}
    check(not bad, f'no arm is ever out of reach' + (f': {bad}' if bad else ''))
    # between rows
    ts = np.random.default_rng(7).uniform(bake.times[0], bake.times[-1], 2500)
    pin = head = shake = 0.0; where = ''
    for aid in rig.plans:
        lo, hi = rig.rail_span(aid); mech = rig.mech_of[aid]
        for t in ts:
            row = bake.row(t); p = rig.pose(aid, t)
            for k in ('root', 'elbow', 'wrist', 'tip'):
                e = float(np.linalg.norm(bake.get(f'{aid}.{k}', t, row)-p[k]))
                if e > pin: pin = e; where = f'{aid}.{k} at {t:.3f} s'
            pin = max(pin, float(np.linalg.norm(bake.felt(aid, t)-p['felt'])))
            head = max(head, abs(bake.get(f'{aid}.head', t, row)-p['head']))
            shake = max(shake, abs(bake.get(f'{aid}.sag', t, row)-rig.rail_sag(aid, t, (lo+hi)/2)),
                        abs(bake.get(f'{aid}.sway', t, row)-rig.mast_sway(aid, t)),
                        abs(bake.get(f'{mech}.stand', t, row)-rig.stand_thump(mech, t)))
    check(pin < INTERP_M, f'between rows every pin stays within {INTERP_M*1000:.0f} mm of the rig (worst {pin*1000:.2f} mm, {where})')
    check(head < INTERP_RAD, f'...and the hinged head within {INTERP_RAD} rad (worst {head:.4f})')
    check(shake < 2e-4, f'...and the assembly\'s shudders within 0.2 mm / mrad (worst {shake*1000:.3f})')
    same = all(np.allclose(np.array(h['arms'][aid]['clicks']).reshape(-1, 2), np.array(rig.click_times(aid)).reshape(-1, 2))
               for aid in rig.plans)
    check(same, f'the clicks are the rig\'s: {sum(len(a["clicks"]) for a in h["arms"].values())}')
    # a stepped arm's pawl ride: Rig.pawl_ride at the rows, in [0, 1], nothing at a contact
    ride_info = []
    for aid, arm in h['arms'].items():
        name = f'{aid}.ride'
        if not rig.stepped(aid):
            check(name not in bake.index, f'{aid}: a servo arm has no .ride channel'); continue
        if name not in bake.index:
            check(False, f'{aid}: a stepped arm without a .ride channel'); continue
        c = bake.index[name]['offset']; col = bake.frames[:, c].astype(float)
        idx = range(0, len(bake.times), 11)
        worst = max(abs(col[i]-rig.pawl_ride(aid, float(bake.times[i]))) for i in idx)
        at_hit = max([abs(bake.ride(aid, float(b['t']))) for b in arm['blows']], default=0.0)
        check(worst < 1e-6 and col.min() >= 0.0 and col.max() <= 1.0 and at_hit < 1e-9,
              f'{aid}: .ride is Rig.pawl_ride at the rows (worst {worst:.1e} over {len(idx)} rows), in [0, 1] '
              f'(max {col.max():.3f}), 0 at every contact (worst {at_hit:.1e})')
        if rig.hammer(aid): check(np.abs(col).max() == 0.0, f'{aid}: the hammer\'s pawl never rides')
        else:
            # rows sit where the tooth rate crosses each RIDE_ROWS fraction of the band, so between two rows the
            # rate stays in one cell [k/8, (k+1)/8] of it and the smoothstep ride in [s(k/8), s((k+1)/8)]: a straight
            # line between the rows strays from Rig.pawl_ride by at most that cell's width (judged per interval,
            # on every interval that touches a freewheel travel)
            st = rig.stroke(aid); rt = st.ride_times()
            gap = np.array([float(np.min(np.abs(bake.times-t))) for t in rt]) if len(rt) else np.zeros(0)
            check(not gap.size or gap.max() <= B.MERGE_S,
                  f'{aid}: a row at every RIDE_ROWS crossing of the tooth rate ({len(rt)}, worst {gap.max() if gap.size else 0:.1e} s)')
            lo, hi = ST.PAWL_RIDE_BAND; lv = np.asarray(ST.RIDE_ROWS, float); sm = lambda u: u*u*(3-2*u)
            mid = bake.times[:-1]+.5*np.diff(bake.times)
            fw = [(tv['t0'], tv['t1']) for tv in st.travels if tv['regime'] == 'freewheel']
            sel = np.flatnonzero(np.any([(bake.times[1:] > a) & (bake.times[:-1] < b) for a, b in fw], axis=0)) if fw else []
            if len(sel):
                lin = .5*(col[sel]+col[sel+1]); live = np.array([rig.pawl_ride(aid, float(mid[i])) for i in sel])
                u = np.clip((np.abs(st.x(mid[sel], 1))/ST._PITCH-lo)/(hi-lo), 0.0, 1.0)
                k = np.clip(np.searchsorted(lv, u, side='right')-1, 0, len(lv)-2)
                bound = sm(lv[k+1])-sm(lv[k])+2e-7          # + the float32 rounding of the two stored rows
                err = np.abs(lin-live); worst = int(np.argmax(err/bound))
                check(np.all(err <= bound), f'{aid}: between rows the linear ride stays within its RIDE_ROWS cell of '
                      f'Rig.pawl_ride ({len(sel)} freewheel intervals; worst {err.max():.4f}, at most {(err/bound).max():.2f} of its cell)')
                ride_info.append(f'{aid} {err.max():.3f}')
    # each click's pawl and step: a mallet's are its stroke's click knots, the hammer's all drop and stepped
    for aid, arm in h['arms'].items():
        cs, cp, cs_step = arm['clicks'], arm.get('click_pawl'), arm.get('click_step')
        if cp is None or cs_step is None or not (len(cs) == len(cp) == len(cs_step)):
            check(False, f'{aid}: click_pawl / click_step missing or not parallel to clicks'); continue
        st = rig.stroke(aid) if rig.mallet(aid) else None
        if st is not None:
            kn = sorted([k for k in st.knots if k.kind == 'click'], key=lambda k: float(k.extra.get('t_end', k.t)))
            lab = [int(k.extra['pawl'] == 'ride') for k in kn]; stp = [int('t_end' in k.extra) for k in kn]
            bad = sum(k.extra['pawl'] != ('drop' if 't_end' in k.extra or abs(float(st.x(k.t, 1)))/ST._PITCH < ST.PAWL_RIDE else 'ride')
                      for k in kn)
            check(lab == cp and stp == cs_step and bad == 0,
                  f'{aid}: click_pawl / click_step are the stroke\'s click knots ({len(cs)} clicks: {sum(cp)} ride, '
                  f'{len(cs)-sum(cs_step)} freewheel; {bad} pawl labels off |x\'|/PITCH vs PAWL_RIDE)')
        else:
            check(cp == [0]*len(cs) and cs_step == [1]*len(cs), f'{aid}: every {arm["kind"]} click drops and is stepped ({len(cs)})')
    # the blows are the rig's recoil bus; a mallet's carry its stroke's v_in and e, gated by the next apex
    for aid, arm in h['arms'].items():
        bus = rig.blows_by_arm.get(aid, [])
        ok = len(arm['blows']) == len(bus)
        for b, r in zip(arm['blows'], bus):
            ok &= b['t'] == r['t'] and b['x'] == r['x'] and b['energy'] == r['energy']
            ok &= (b['gate_end'] is None) if not np.isfinite(r['gate_end']) else b['gate_end'] == r['gate_end']
            ok &= all((k in b) == (k in r) and (k not in r or b[k] == r[k]) for k in ('v_in', 'e'))
        st = rig.stroke(aid) if rig.mallet(aid) else None
        if st is not None:
            N = sorted(st.notes, key=lambda n: n.t)
            ok &= len(N) == len(arm['blows']) and all(
                b['v_in'] == float(n.v_in) and b['e'] == float(n.e) and b['energy'] == float(n.amp)
                and (b['gate_end'] is None if i+1 == len(N) else b['gate_end'] == float(N[i+1].t_apex))
                for i, (b, n) in enumerate(zip(arm['blows'], N)))
        elif arm['blows']: ok &= not any('v_in' in b or 'e' in b for b in arm['blows'])
        if bus or arm['blows']:
            check(ok, f'{aid}: {len(arm["blows"])} blows are the rig\'s recoil bus'
                      + (' (v_in, e from the stroke; gate_end the next apex)' if st is not None else ''))
    xs = np.random.default_rng(3).uniform(-5, 5, 5000)
    tab = max(abs(bake.pawl_angle(x)-a) for x, a in zip(xs, W.angle(xs)))
    check(tab < 5e-4, f'the pawl\'s one-tooth table is formlab.pawl.angle (worst {tab:.1e} rad over 5000 rail positions)')
    least = float(W.angle(np.linspace(0, W.PITCH, 20001)).min()); ra = h['pawl'].get('ride_angle')
    check(ra is not None and ra == min(h['pawl']['table']) and abs(least-ra) < 2e-4,
          f'pawl.ride_angle is the table\'s least angle, the nose on a tip ({np.degrees(ra) if ra is not None else float("nan"):.3f} deg; formlab.pawl.angle\'s least {np.degrees(least):.3f})')
    check(h['constants'].get('PAWL_RIDE') == ST.PAWL_RIDE, f'constants.PAWL_RIDE is formlab.stroke\'s ({h["constants"].get("PAWL_RIDE")})')
    parity(bake, score_path, asset)
    if asset == 'clockwork': refuses_stale(score_path, asset)

if __name__ == '__main__':
    if len(sys.argv) == 3: pairs = [(Path(sys.argv[1]), Path(sys.argv[2]))]
    else:
        pairs = []
        for asset in ('clockwork', 'clockwork_expanded'):
            lp = ROOT/'harness'/'assets'/f'{asset}.json'
            pairs.append((lp, Path(json.loads(lp.read_text())['score'])))
    for lp, sp in pairs: run(lp, sp)
    print('BAKE: PASS' if not failures else f'BAKE: FAIL ({len(failures)})')
    sys.exit(1 if failures else 0)

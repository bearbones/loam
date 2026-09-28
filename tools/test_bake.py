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
    pose = shud = pawl = 0.0; n = ns = npw = 0; clicks = {}
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
        elif f[0] == 'PAWL':
            npw += 1; pawl = max(pawl, abs(bake.pawl_angle(float(f[1]))-float(f[2])))
        elif f[0] == 'CLICK':
            clicks.setdefault(f[1], []).append(float(f[2]))
    check(n > 1000 and pose < 1e-6, f'the harness reads the poses the reference reader does: {n} off-grid samples, worst {pose:.1e}')
    check(ns > 1000 and shud < 1e-9, f'...and the shudders: {ns} samples, worst {shud:.1e}')
    check(npw > 1000 and pawl < 1e-6, f'...and the pawl table: {npw} rail positions, worst {pawl:.1e} rad')
    want = {aid: [c[0] for c in a['clicks']] for aid, a in bake.header['arms'].items() if a['clicks']}
    same = want.keys() == clicks.keys() and all(np.allclose(want[a], clicks[a], atol=1e-8) for a in want)
    check(same, f'...and the clicks: {sum(len(v) for v in clicks.values())} over {len(clicks)} arms')

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
        for k, sid in enumerate(e['strings']):
            t = float(e['t'])+k*float(e.get('spread_s', 0)); nc += 1
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
    xs = np.random.default_rng(3).uniform(-5, 5, 5000)
    tab = max(abs(bake.pawl_angle(x)-a) for x, a in zip(xs, W.angle(xs)))
    check(tab < 5e-4, f'the pawl\'s one-tooth table is formlab.pawl.angle (worst {tab:.1e} rad over 5000 rail positions)')
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

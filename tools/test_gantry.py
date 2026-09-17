"""Ruler for the rail gantries and for arms against every rail.

    python3 tools/test_gantry.py                       # both built assets
    python3 tools/test_gantry.py LAYOUT.json SCORE.json

Re-derives each rail end's bracket from the manifest and the score's motion
(formlab.gantry.plan_gantries) and checks:
  - a carriage parked at the end of its rail clears the rail head (the pin
    heads are the widest thing on the carriage plane);
  - every arm's swept capsules (pinion included) clear every OTHER rail's
    bars and rack — the planner rule that makes this true lives in
    formlab.layout_search.evaluate_arm; each carriage clears its own rack,
    and its second-bar boss and web miss its own guide bars;
  - the placement the build recorded is the one the search finds now, with
    the promised margin against arms, bars, forms, furniture and other
    gantries; every mast stands on the stage or a furniture lid, under its
    head; the heads capture the bar ends; every piece is a closed mesh.
"""
import json, sys
from pathlib import Path
import numpy as np
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT))
from formlab import gantry as G
from formlab import clearance as C
from formlab.rig import Rig
from formlab.linkage import parallelogram_arm, check_pieces
from formlab.clearance import segment_distance

failures = []
def check(ok, msg):
    print(('  PASS ' if ok else '  FAIL ')+msg)
    if not ok: failures.append(msg)

def run(layout_path, score_path):
    print(f'== {layout_path.name} / {score_path.name}')
    layout = json.loads(layout_path.read_text()); score = json.loads(score_path.read_text())
    rig = Rig(score, layout); times = rig.sample_times()
    poses = {aid: rig.poses(aid, times) for aid in layout['arms']}
    caps = G._caps(layout, poses, 1)
    # 1. the carriage's widest part vs the head's inner face
    probe = parallelogram_arm(1.0, 1.0, [0, -.11, 0], [0, 0, -.11])
    x_ext = max(abs(np.concatenate([p.vertices for p in probe[part]['pieces']])[:, 0]).max()
                for part in ('carriage', 'shoulder', 'upper', 'upper2'))
    check(x_ext+G.MARGIN <= G.RAIL_OVER+G.HEAD_INSET,
          f'pin heads ({x_ext:.3f} m off the carriage plane) clear the rail head ({G.RAIL_OVER+G.HEAD_INSET:.3f} m past the window)')
    # 2. every arm vs every other rail's bars
    worst = (1e9, '')
    for aid, cfg in layout['arms'].items():
        for A, B, r in G.rail_bars(cfg):
            for other, arm in caps.items():
                if other == aid: continue
                for name, (P, Q, ra) in arm.items():
                    g = segment_distance(P, Q, A[None], B[None])-r-ra; k = int(np.argmin(g))
                    if g[k] < worst[0]: worst = (float(g[k]), f'{other} {name} vs rail {aid} at t={times[k]:.2f} s')
    check(worst[0] >= G.MARGIN, f'arms clear other rails\' bars by {worst[0]:.3f} m ({worst[1]})')
    # 2b. every arm (its pinion included) vs every other rail's rack; each
    #     carriage vs its own rack — only the pinion may touch the rack
    worst = (1e9, ''); own = (1e9, '')
    for aid, cfg in layout['arms'].items():
        (A, B, r), = G.rail_racks(cfg)
        for other, arm in caps.items():
            for name, (P, Q, ra) in arm.items():
                if other == aid and not name.startswith('carriage'): continue
                g = segment_distance(P, Q, A[None], B[None])-r-ra; k = int(np.argmin(g))
                if other == aid and g[k] < own[0]: own = (float(g[k]), f'{aid} {name} vs its rack at t={times[k]:.2f} s')
                if other != aid and g[k] < worst[0]: worst = (float(g[k]), f'{other} {name} vs rack {aid} at t={times[k]:.2f} s')
        boss = poses[aid]['root']+np.asarray(cfg['o1'])
        g = np.linalg.norm(boss-np.clip(boss, A, B), axis=1)-r-G.DEFAULT_SPEC['boss_r']
        if g.min() < own[0]: own = (float(g.min()), f'{aid} second-bar boss vs its rack')
        mount = cfg.get('pinion'); best, drive_gap = C.pinion_mount(poses[aid], cfg['o1'], cfg['o2'], cfg['layers'], C.DEFAULT_SPEC)
        check(mount in C.MOUNTS and layout['arms'][aid]['gantry']['rack']['mount'] == mount and drive_gap >= 0
              and C.pinion_mount(poses[aid], cfg['o1'], cfg['o2'], cfg['layers'], C.DEFAULT_SPEC, [mount])[1] >= min(drive_gap, G.MARGIN)-1e-9,
              f'{aid}: pinion mounted {mount} (drive {drive_gap*1000:.0f} mm from the links; best {best}), rack recorded with it')
        check(not any(C.offset_hits(cfg['o1'], c, rr) for c, rr in C.rail_keep_clear()),
              f'{aid}: the carriage\'s second-bar boss and web miss the guide bars (o1 {np.round(cfg["o1"], 3).tolist()})')
    check(worst[0] >= G.MARGIN, f'arms clear other rails\' racks by {worst[0]:.3f} m ({worst[1]})')
    check(own[0] >= G.MARGIN, f'carriages clear their own racks by {own[0]:.3f} m ({own[1]})')
    cfg0 = next(iter(layout['arms'].values())); R = G.rack_geometry(cfg0); P = C.PINION
    check(R['s_tip'] > P['r_hub'] and R['s_root'] > P['r_tip'] and R['pitch']-P['r_tip']*.22-2*G.RACK_GAP > .008
          and P['r_tip']+G.MARGIN <= G.RAIL_OVER+G.HEAD_INSET,
          f'rack teeth pitched to the pinion: pitch {R["pitch"]*1000:.1f} mm, clearances {G.RACK_GAP*1000:.0f} mm; the disc clears the heads')
    # 3. the recorded placement is what the search finds, with its margins
    recipe = json.loads((ROOT/'render/form-study/recipe.json').read_text())
    form_boxes = [(o['name'], (V.min(0), V.max(0))) for o in recipe['objects']
                  if not o.get('local') and not o['name'].endswith(('_gantry', '_railhead'))
                  for V in [np.concatenate([np.array(p['vertices']) for p in o['pieces']])]]
    plan = G.plan_gantries(layout, poses, form_boxes, verbose=lambda *a: None)
    for aid, g in plan.items():
        rec = layout['arms'][aid].get('gantry')
        check(rec is not None and all(abs(e['setback']-r['setback']) < 1e-9 and abs(e['outreach']-r['outreach']) < 1e-9
                                      for e, r in zip(g['ends'], rec['ends'])),
              f'{aid}: recorded brackets match the search '+', '.join(f'(out {e["outreach"]:.2f}, back {e["setback"]:.2f})' for e in g['ends']))
        check(g['margin'] >= G.MARGIN, f'{aid}: gantry margin {g["margin"]:.3f} m ({g["worst"]})')
        check_pieces(g['brass']); check_pieces(g['steel'])
        x0, x1 = layout['arms'][aid]['reach_x']; ry = layout['arms'][aid]['root_y']; rz = layout['arms'][aid]['root_z']
        for e in g['ends']:
            boxes = [b for _, b in form_boxes]
            on_stage = abs(e['foot_y']-G.STAGE['top']) < 1e-9
            on_lid = any(abs(e['foot_y']-hi[1]) < 1e-9 for lo, hi in G.scene_boxes(layout)[1:])
            check(on_stage or on_lid, f'{aid} {"low" if e["side"] < 0 else "high"} end: mast stands on the stage or a lid (foot y {e["foot_y"]:.3f})')
            check(e['height'] > .2 and e['x_col']*e['side'] >= (x1 if e['side'] > 0 else -x0)+G.RAIL_OVER+G.HEAD_INSET+.09,
                  f'{aid} {"low" if e["side"] < 0 else "high"} end: mast {e["height"]:.2f} m tall, outside the head\'s inner face')
        # heads capture the bar ends
        H = np.concatenate([p.vertices for p in g['brass']])
        for x_bar in (x0-.26, x1+.26):
            inside = H[(abs(H[:, 0]-x_bar) < .03)]
            check(len(inside) and inside[:, 1].min() < ry-.075-.024 and inside[:, 1].max() > ry+.075+.024
                  and inside[:, 2].min() < rz-.024 and inside[:, 2].max() > rz+.024,
                  f'{aid}: head captures the bar end at x={x_bar:.3f}')

if __name__ == '__main__':
    if len(sys.argv) > 2: pairs = [(Path(sys.argv[1]), Path(sys.argv[2]))]
    else: pairs = [(ROOT/'harness/assets/clockwork.json', ROOT/'render/chamber/score.json'),
                   (ROOT/'harness/assets/clockwork_expanded.json', ROOT/'render/clockwork/score.json')]
    for lp, sp in pairs: run(lp, sp)
    print('GANTRY: '+('FAIL' if failures else 'PASS'))
    sys.exit(1 if failures else 0)

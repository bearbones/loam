"""Clearance-driven rig placement: where each arm's rail goes and how long its
links are, decided by the score's motion rather than by hand.

Why: three pick arms on rails stacked 0.23 m apart, all reaching the same
string plane with hanging elbows, cross one another in the yz plane whenever
they play neighbouring strings — the hand-placed layout had two harp arms
interpenetrating (gaps of -27 mm and -55 mm over the piece). No single rule
fixes that; a small search over (rail height, rail depth, link length) per
arm, scored by the worst gap against everything else, does.

Greedy then coordinate descent; the objective is the WORST of
  self-clearance (parallel bars, crossheads, tool), string clearance, cabinet
  and stage clearance, elbow-behind-the-strings margin, and cross-arm gaps —
clipped at `enough` so that beyond a comfortable gap the tie-breaks decide:
shorter links first, then rails near the original height.
"""
import os, json
import numpy as np
try:
    from .rig import Rig
    from .clearance import (DEFAULT_SPEC, default_layers, arm_capsules, pairwise_clearance,
                            choose_offset, segment_distance, pinion_mount, pinion_centre, rack_direction, rail_keep_clear, PINION)
except ImportError:   # imported bare from Blender's Python (formlab/ on sys.path, no SciPy)
    from rig import Rig
    from clearance import (DEFAULT_SPEC, default_layers, arm_capsules, pairwise_clearance,
                           choose_offset, segment_distance, pinion_mount, pinion_centre, rack_direction, rail_keep_clear, PINION)

def box_gap(P, Q, r, lo, hi, samples=16):
    """Conservative gap between capsule PQ (radius r) and an axis-aligned box."""
    u = np.linspace(0, 1, samples)[None, :, None]
    pts = P[:, None, :]*(1-u)+Q[:, None, :]*u
    d = np.maximum(np.maximum(lo-pts, pts-hi), 0)
    return float(np.linalg.norm(d, axis=-1).min())-r

def scene_boxes(layout):
    """Static obstacles an arm may not enter, from the manifest's own notes."""
    boxes = [((-1e9, -1e9, -1e9), (1e9, 0.05, 1e9))]      # the stage top
    for lo, hi in layout.get('obstacles', []): boxes.append((tuple(lo), tuple(hi)))
    return [(np.array(lo, float), np.array(hi, float)) for lo, hi in boxes]

def candidates(mech, layout):
    """Rail (y, z) and link length options for one mechanism's arms."""
    strings = [s for s in layout['strings'].values() if s['mid'] == mech['id']]
    if mech['kind'] == 'struck':
        cy = float(layout['mechanisms'][mech['id']]['center'][1]); cz = float(np.mean([s['a'][2] for s in strings]))
        # .28 above the felt: a 12 cm head, a shank you can see, the socket collar, the boss
        ys = [cy+.9, cy+1.15, cy+1.4]; zs = [cz-.75, cz-1.0, cz-1.3]; bend = 'up'; wrist = [0, .28, 0]
    else:
        zs_plane = float(np.mean([s['a'][2] for s in strings]))
        ys = [.55, 2.75, 3.15, 3.6, 4.1]; zs = [zs_plane+d for d in (-.75, -1.05, -1.4, -1.8, -2.25)]
        bend = 'back'; wrist = [0, .20, -.10]   # room for plectrum, ferrule, swan neck, socket
    ls = [1.0, 1.15, 1.3, 1.45, 1.6]
    return [dict(root_y=y, root_z=z, l1=l, l2=l, bend=bend, wrist_offset=wrist) for y in ys for z in zs for l in ls]

def evaluate_arm(rig, aid, cfg, times, spec=DEFAULT_SPEC, layers=None, boxes=(), string_plane_z=None):
    """Feasibility + self score for one arm config. Returns dict or None."""
    layers = layers or default_layers(spec)
    old = dict(rig.geometry['arms'][aid]); rig.geometry['arms'][aid].update(cfg)
    try:
        poses = rig.poses(aid, times)
    finally:
        rig.geometry['arms'][aid] = old
    dist = np.linalg.norm(poses['wrist']-poses['root'], axis=1)
    l = float(cfg['l1'])+float(cfg['l2'])
    if dist.max() > l*.985 or dist.min() < .30: return None
    # the carriage's second-bar boss must miss the guide bars; the pinion sits
    # on whichever mount the links never swing through
    o1, sep1, _ = choose_offset(poses, 'upper', .11, keep_clear=rail_keep_clear()); o2, sep2, _ = choose_offset(poses, 'lower', .11)
    mount, _ = pinion_mount(poses, o1, o2, layers, spec)
    caps, adjacent = arm_capsules(poses, o1, o2, layers, spec, mount)
    gaps = pairwise_clearance(caps, adjacent); self_gap = min(v[0] for v in gaps.values())
    margins = dict(self=self_gap, pair=min(sep1, sep2)-spec['depth'])
    if string_plane_z is not None and cfg['bend'] == 'back':
        margins['behind'] = float(string_plane_z-(poses['elbow'][:, 2].max()+spec['depth']/2))
    for name in ('upper', 'upper2', 'lower', 'lower2'):
        P, Q, r = caps[name]
        margins['scene'] = min(margins.get('scene', 1e9), min(box_gap(P, Q, r, lo, hi) for lo, hi in boxes) if boxes else 1e9)
    strings = {sid: s for sid, s in rig.geometry['strings'].items() if s['mid'] == rig.geometry['arms'][aid]['mid']}
    sg = 1e9
    for s in strings.values():
        A = np.broadcast_to(np.asarray(s['a'], float), poses['root'].shape); B = np.broadcast_to(np.asarray(s['b'], float), poses['root'].shape)
        for name in ('upper', 'upper2', 'lower', 'lower2', 'wristhead_web', 'elbowhead_web1', 'elbowhead_web2', 'shank'):
            P, Q, r = caps[name]; sg = min(sg, float((segment_distance(P, Q, A, B)-r-.002).min()))
    margins['strings'] = sg
    # The rail itself — two guide bars and a head at each end (formlab.gantry) —
    # is an obstacle to the OTHER arms of the mechanism: cross_gap measures every
    # arm against its neighbours' rails, not only their links. (The first layout
    # had an upper link sweeping 52 mm through a neighbouring rail.)
    caps = dict(caps); T = len(poses['root']); x0, x1 = rig.geometry['arms'][aid]['reach_x']; ry = cfg['root_y']; rz = cfg['root_z']
    def fixed(a, b, r): return (np.broadcast_to(np.array(a, float), (T, 3)), np.broadcast_to(np.array(b, float), (T, 3)), r)
    for dy in (-.075, .075): caps[f'rail{dy:+.3f}'] = fixed([x0-.26, ry+dy, rz], [x1+.26, ry+dy, rz], .024)
    for dy in (-.07, .07):
        caps[f'head_lo{dy:+.2f}'] = fixed([x0-.36, ry+dy, rz], [x0-.16, ry+dy, rz], .07)
        caps[f'head_hi{dy:+.2f}'] = fixed([x1+.16, ry+dy, rz], [x1+.36, ry+dy, rz], .07)
    # and the rack the pinion rolls on, in the disc's plane off its mount (formlab.gantry.rack)
    rm = np.array([0., ry, rz])+pinion_centre(mount)+rack_direction(mount)*(PINION['r_hub']+PINION['r_tip']+.039)/2
    caps['rack'] = fixed([x0-.26, rm[1], rm[2]], [x1+.26, rm[1], rm[2]], .04)
    return dict(cfg=dict(cfg, o1=o1.tolist(), o2=o2.tolist(), pinion=mount), poses=poses, caps=caps, margins=margins, worst=min(margins.values()))

def cross_gap(ca, cb):
    """Worst gap between two arms' capsules, each arm's rail included as an
    obstacle to the other's links; rail-vs-rail is `rails_compatible`'s job."""
    best = 1e9
    for na, (P1, Q1, r1) in ca.items():
        for nb, (P2, Q2, r2) in cb.items():
            if _is_rail(na) and _is_rail(nb): continue
            best = min(best, float((segment_distance(P1, Q1, P2, Q2)-r1-r2).min()))
    return best

def _is_rail(name): return name.startswith(('rail', 'head_', 'rack'))

def rails_compatible(a, b):
    return abs(a['root_y']-b['root_y']) > .22 or abs(a['root_z']-b['root_z']) > .16

def _mech_key(score, layout, mech, hz, enough):
    """Everything the search for one mechanism depends on, hashed: its
    events (times, strings, picks), its string geometry, the obstacles,
    the sampling, the candidate grid and the space model (the source text of
    candidates, evaluate_arm and the whole clearance module)."""
    import hashlib, inspect, sys
    ev = [{k: e.get(k) for k in ('t', 't_move', 't_free', 'strings', 'pick', 'spread_s', 'actuator')}
          for e in score['events'] if e.get('mech') == mech['id']]
    strings = {k: v for k, v in layout['strings'].items() if v['mid'] == mech['id']}
    blob = json.dumps([mech, ev, strings, layout.get('obstacles', []), layout['mechanisms'][mech['id']],
                       {a: layout['arms'][a] for a in (x['id'] for x in mech['actuators'])},
                       score['total_s'], hz, enough, inspect.getsource(candidates), inspect.getsource(evaluate_arm),
                       inspect.getsource(sys.modules[arm_capsules.__module__]), DEFAULT_SPEC], sort_keys=True, default=str)
    return hashlib.sha1(blob.encode()).hexdigest()

def plan_arms(score, layout, hz=30, enough=.08, verbose=print, cache=None):
    """Choose (root_y, root_z, l1, l2, bend, wrist_offset, o1, o2) per arm.
    Mutates and returns layout['arms']; also records the achieved margins.
    `cache` is a JSON path: a mechanism whose inputs are unchanged reuses its
    stored result (the search is minutes per mechanism)."""
    import json as _json
    rig = Rig(score, layout)
    total = float(score['total_s']); times = np.arange(-hz, int(total*hz)+1)/hz
    boxes = scene_boxes(layout)
    store = {}
    if cache and os.path.exists(cache):
        try: store = _json.load(open(cache))
        except ValueError: store = {}
    for mech in score['instrument']['mechanisms']:
        aids = [a['id'] for a in mech['actuators']]
        key = _mech_key(score, layout, mech, hz, enough) if cache else None
        if key and key in store:
            for aid in aids:
                layout['arms'][aid].update(store[key][aid])
                if verbose: verbose(f"  RAIL {aid}: (cached) "+' '.join(f'{k2}={v}' for k2, v in store[key][aid].items() if k2 != 'margins'))
            continue
        strings = [s for s in layout['strings'].values() if s['mid'] == mech['id']]
        plane_z = float(np.mean([s['a'][2] for s in strings])) if mech['kind'] != 'struck' else None
        options = {aid: [] for aid in aids}
        for aid in aids:
            for cfg in candidates(mech, layout):
                ev = evaluate_arm(rig, aid, cfg, times, boxes=boxes, string_plane_z=plane_z)
                if ev is not None: options[aid].append(ev)
            if not options[aid]: raise ValueError(f'no feasible rail for {aid}')
        chosen = {}
        def objective(aid, ev):
            worst = ev['worst']
            for other, oev in chosen.items():
                if other == aid: continue
                if not rails_compatible(ev['cfg'], oev['cfg']): return (-1e9,)
                worst = min(worst, cross_gap(ev['caps'], oev['caps']))
            return (min(worst, enough), -ev['cfg']['l1'], -abs(ev['cfg']['root_y']-2.75), worst)
        for aid in aids:                      # greedy
            chosen[aid] = max(options[aid], key=lambda ev: objective(aid, ev))
        for _ in range(2):                    # coordinate descent
            for aid in aids:
                chosen[aid] = max(options[aid], key=lambda ev: objective(aid, ev))
        for k, aid in enumerate(aids):
            ev = chosen[aid]; cfg = ev['cfg']
            cross = {o: cross_gap(ev['caps'], chosen[o]['caps']) for o in aids if o != aid}
            layout['arms'][aid].update(cfg)
            layout['arms'][aid]['margins'] = dict({k2: round(v, 4) for k2, v in ev['margins'].items()}, cross={o: round(g, 4) for o, g in cross.items()})
            if verbose: verbose(f"  RAIL {aid}: y={cfg['root_y']:.2f} z={cfg['root_z']:.2f} l={cfg['l1']:.2f} bend={cfg['bend']} margins="+
                                ' '.join(f'{k2}={v:.3f}' for k2, v in ev['margins'].items())+' cross='+' '.join(f'{o}={g:.3f}' for o, g in cross.items()))
        if key:
            store[key] = {aid: dict(chosen[aid]['cfg'], margins=layout['arms'][aid]['margins']) for aid in aids}
            os.makedirs(os.path.dirname(cache) or '.', exist_ok=True)
            _json.dump(store, open(cache, 'w'), indent=1)
    return layout['arms']

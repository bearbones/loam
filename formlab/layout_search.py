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
    from .clearance import (DEFAULT_SPEC, default_layers, arm_capsules, pairwise_clearance, choose_offset, segment_distance,
                            pinion_mount, pinion_centre, rack_direction, rail_keep_clear, PINION, GANTRY, mast_columns, head_box, bracket_solids, foot_level)
except ImportError:   # imported bare from Blender's Python (formlab/ on sys.path, no SciPy)
    from rig import Rig
    from clearance import (DEFAULT_SPEC, default_layers, arm_capsules, pairwise_clearance, choose_offset, segment_distance,
                           pinion_mount, pinion_centre, rack_direction, rail_keep_clear, PINION, GANTRY, mast_columns, head_box, bracket_solids, foot_level)

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

CFG_KEYS = ('root_y', 'root_z', 'l1', 'l2', 'bend', 'wrist_offset', 'o1', 'o2', 'pinion')

def _bounds(stack):
    """Axis-aligned bounds of a capsule stack over every pose (lo, hi)."""
    r = stack['r'][:, None, None]
    return np.minimum((stack['A']-r).min((0, 1)), (stack['B']-r).min((0, 1))), np.maximum((stack['A']+r).max((0, 1)), (stack['B']+r).max((0, 1)))

def _bracket_bounds(ends):
    """Axis-aligned bounds of every bracket solid of both rail ends."""
    lo = np.full(3, 1e9); hi = np.full(3, -1e9)
    for end in ends:
        for br in end['brackets']:
            for kind, *geo in br['solids']:
                if kind == 'box': lo = np.minimum(lo, geo[0]); hi = np.maximum(hi, geo[1])
                else: lo = np.minimum(lo, np.minimum(geo[0], geo[1])-geo[2]); hi = np.maximum(hi, np.maximum(geo[0], geo[1])+geo[2])
    return lo, hi

def _box_apart(a, b):
    """Gap between two (lo, hi) boxes, 0 when they meet."""
    return float(np.linalg.norm(np.maximum(np.maximum(a[0]-b[1], b[0]-a[1]), 0)))

def evaluate_arm(rig, aid, cfg, times, spec=DEFAULT_SPEC, layers=None, boxes=(), string_plane_z=None, enough=.08, others=()):
    """Feasibility + self score for one arm config. Returns dict or None.
    `others`: evaluated arms of the mechanisms planned before this one, at the
    same sampling — this arm is measured against them as the gantry planner
    measures every arm of the rig against every other."""
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
    # The scene's promises (cabinet, bases, instrument frames) bind the carriage,
    # the pinion and the rail's own bars, heads and rack as much as the links:
    # the gantry planner refuses a rack inside a frame after the rails are fixed.
    if boxes:
        for name, (P, Q, r) in caps.items():
            if name in ('upper', 'upper2', 'lower', 'lower2'): continue
            rows = 1 if _is_rail(name) else len(P)
            margins['scene'] = min(margins['scene'], min(box_gap(P[:rows], Q[:rows], r, lo, hi) for lo, hi in boxes))
    # A mast must stand at each rail end (formlab.gantry.plan_end searches the
    # same brackets and measures the same solids): keep, per end, every bracket
    # the arm's own motion and the scene leave clear, so the objective can ask
    # whether the neighbours leave at least one of them. (The first search
    # chose a rail whose high end no bracket could serve: a neighbour's links
    # swept its head within 50 mm, and the build failed after the rails were
    # fixed. The heads are boxes here as they are there — a capsule model let
    # that rail through by the corner it does not have.)
    G = GANTRY; zs = float(np.mean([s['a'][2] for s in strings.values()])) if strings else rz-1
    behind = -1.0 if rz < zs else 1.0
    ends = []
    for side, x_end in ((-1, x0-G['rail_over']), (1, x1+G['rail_over'])):
        brackets = []
        for x_col, z_m, o, sb in mast_columns(x_end, side, rz, behind):
            foot, on = foot_level(x_col, z_m, boxes[1:])      # a mast may stand on a furniture box (planner: the same rule)
            brackets.append(dict(solids=bracket_solids(x_end, side, ry, rz, behind, o, sb, foot), on=on))
        ends.append(dict(head=head_box(x_end, side, ry, rz), brackets=brackets))
    shifts = pin_shifts(caps, layers['pin_x'])
    # stack: the whole arm, rail included, for the neighbours' brackets and heads;
    # its moving rows only (stack_view) for its own — the bracket carries the head
    stack = stack_caps(caps, shifts)
    caps = {n: (stack['A'][i], stack['B'][i], stack['r'][i]) for i, n in enumerate(stack['names'])}     # views into the stack: one copy per arm
    ev = dict(cfg=dict(cfg, o1=o1.tolist(), o2=o2.tolist(), pinion=mount), poses=poses, caps=caps, shifts=shifts, stack=stack,
              ends=ends, mast_memo={}, margins=margins, bounds=_bounds(stack), bracket_bounds=_bracket_bounds(ends))
    margins['mast'] = mast_margin(ev, [], boxes, enough)
    if others:
        # The arms of the mechanisms planned before this one: their links and
        # rail hardware against this arm's (heads included), this arm's masts
        # against their motion and theirs against this arm's — what the gantry
        # planner measures across the whole rig once the rails are fixed. (The
        # expanded harp's rack was refused for a bells arm's lower link at
        # -31 mm before the search knew of it.) An arm whose bounds stand
        # `enough` apart is not measured; the margin records that bound.
        g = 1e9
        for o in others:
            apart = _box_apart(ev['bounds'], o['bounds'])
            g = min(g, apart if apart >= enough else cross_gap(caps, o['caps'], stack, o['stack'], heads(ev), heads(o)))
            if _box_apart(ev['bracket_bounds'], o['bounds']) < enough: margins['mast'] = min(margins['mast'], mast_margin(ev, [o], boxes, enough))
            if _box_apart(o['bracket_bounds'], ev['bounds']) < enough: g = min(g, mast_margin(o, [ev], boxes, enough))
            if g < 0: break
        margins['others'] = g
    ev['worst'] = min(margins.values())
    return ev

def pin_shifts(caps, pin_x):
    """How far each moving capsule may be slid along X either way so that the
    arm as a whole reaches the pin tips' planes at ±pin_x from its carriage
    plane (the parts sit at fixed offsets from that plane; the pins are the
    widest thing on it). The gantry planner slides by the same rule
    (formlab.gantry._stacks), so both rulers see one arm width. Rail parts: (0,)."""
    root = caps['upper'][0][:, 0]; out = {}
    for name, (P, Q, r) in caps.items():
        if _is_rail(name): out[name] = (0.,); continue
        lo = float(np.mean(np.minimum(P[:, 0], Q[:, 0])-root)); hi = float(np.mean(np.maximum(P[:, 0], Q[:, 0])-root))
        out[name] = tuple(sorted({round(min(-pin_x-lo+r, 0.), 6), 0., round(max(pin_x-hi-r, 0.), 6)}))
    return out

def stack_caps(caps, shifts, step=1):
    """Every capsule of an arm as rows of one array so a solid can be
    measured against the whole arm in one vectorised pass: A, B (N, T, 3),
    r (N,), the pin-span slide range per row d_lo, d_hi (N,), `rows` — the
    (row, slide) pairs a capsule solid is measured at — the moving-part
    rows `mov`, and the arm's whole bounding box lo, hi (slides and radii
    included) for a quick far-away verdict. `step` takes every step-th
    pose; the arrays are views of the capsules' own, not copies."""
    names = list(caps)
    A = np.stack([np.asarray(caps[n][0])[::step] for n in names]); B = np.stack([np.asarray(caps[n][1])[::step] for n in names])
    r = np.array([caps[n][2] for n in names], float)
    d_lo = np.array([min(shifts.get(n, (0.,))) for n in names]); d_hi = np.array([max(shifts.get(n, (0.,))) for n in names])
    rows = [(i, dx) for i, n in enumerate(names) for dx in shifts.get(n, (0.,))]
    mov = np.array([not _is_rail(n) for n in names])
    row_lo = np.minimum(A.min(1), B.min(1))+d_lo[:, None]*[1, 0, 0]-r[:, None]     # each capsule's sweep box, slides and radius in
    row_hi = np.maximum(A.max(1), B.max(1))+d_hi[:, None]*[1, 0, 0]+r[:, None]
    return dict(A=A, B=B, r=r, d_lo=d_lo, d_hi=d_hi, rows=rows, mov=mov, shifts=shifts, row_lo=row_lo, row_hi=row_hi, names=names)

def stack_view(stack, mov=False, step=1):
    """A view of `stack` with every step-th pose, and only the moving rows
    when `mov`; nothing is copied."""
    if not mov and step == 1: return stack
    keep = np.flatnonzero(stack['mov']) if mov else np.arange(len(stack['r'])); new = {int(i): k for k, i in enumerate(keep)}
    rows = [(new[i], dx) for i, dx in stack['rows'] if i in new]
    return dict(stack, A=stack['A'][keep, ::step], B=stack['B'][keep, ::step], r=stack['r'][keep], d_lo=stack['d_lo'][keep], d_hi=stack['d_hi'][keep],
                rows=rows, row_lo=stack['row_lo'][keep], row_hi=stack['row_hi'][keep], names=[stack['names'][i] for i in keep])

def solids_gap(solids, stack, margin=GANTRY['margin'], samples=24, chunk=12, far_enough=.15, who=False):
    """Worst gap between fixed solids — ('box', lo, hi) or ('capsule', a, b,
    r) — and an arm (stack_caps) over all poses, each capsule slid across
    its pin span as the gantry planner does (a box widened by the span, a
    capsule tried at the span's ends and the middle), less the planner's
    margin so that 0 here is its pass. A part whose whole sweep box keeps
    `far_enough` from a solid is scored by that bound, not measured — most
    of an arm never comes near a bracket. `who`: return (gap, part name)."""
    best = (1e9, None); u = np.linspace(0, 1, samples)[None, None, :, None]
    for sol in solids:
        if sol[0] == 'box': slo, shi = sol[1], sol[2]
        else: slo, shi = np.minimum(sol[1], sol[2])-sol[3], np.maximum(sol[1], sol[2])+sol[3]
        row = np.linalg.norm(np.maximum(np.maximum(stack['row_lo']-shi, slo-stack['row_hi']), 0), axis=1)     # (N,) lower bounds on each part's gap
        near = np.flatnonzero(row < far_enough)
        if sol[0] == 'box':
            lo = sol[1]-stack['d_hi'][near, None]*[1, 0, 0]; hi = sol[2]-stack['d_lo'][near, None]*[1, 0, 0]     # (n, 3)
            for i in range(0, len(near), chunk):
                rows = near[i:i+chunk]; A = stack['A'][rows]; B = stack['B'][rows]
                pts = A[:, :, None, :]*(1-u)+B[:, :, None, :]*u                                       # (n, T, S, 3)
                d = np.maximum(np.maximum(lo[i:i+chunk, None, None, :]-pts, pts-hi[i:i+chunk, None, None, :]), 0)
                row[rows] = np.linalg.norm(d, axis=-1).min(axis=(1, 2))-stack['r'][rows]
        else:
            P, Q, r = sol[1:]; keep = set(near.tolist())
            for i, dx in stack['rows']:
                if i not in keep: continue
                d = segment_distance(P[None], Q[None], stack['A'][i]+[dx, 0, 0], stack['B'][i]+[dx, 0, 0])   # (T,)
                row[i] = min(row[i], float(d.min()-r-stack['r'][i]))
        k = int(np.argmin(row))
        if row[k] < best[0]: best = (float(row[k]), stack['names'][k])
    return (best[0]-margin, best[1]) if who else best[0]-margin

def mast_gaps(P, Q, r, caps, shifts=None):
    """Per column c (P[c] to Q[c], radius r): the worst gap against every
    capsule in `caps` over all poses, each capsule slid by its `shifts`
    along X (pin_shifts). Shape (C,)."""
    best = np.full(len(P), 1e9)
    for name, (A, B, ra) in caps.items():
        for dx in (shifts or {}).get(name, (0.,)):
            d = segment_distance(P[:, None, :], Q[:, None, :], A[None]+[dx, 0, 0], B[None]+[dx, 0, 0])     # (C, T)
            best = np.minimum(best, d.min(axis=1)-r-ra)
    return best

def column_gap(ev, k, c, oev, boxes):
    """Gap of ev's bracket c at rail end k — its mast column, beams and knee
    braces — against option oev's capsules (its own moving parts, plus the
    scene boxes, when oev is ev: the bracket carries the head and the rail
    that would otherwise touch it). Memoised on ev."""
    key = (k, c, id(oev))
    if key not in ev['mast_memo']:
        br = ev['ends'][k]['brackets'][c]; sol = br['solids']
        # every 4th pose first: that gap bounds the true one from above, so a
        # bracket it already rules out needs no fine pass (the planner's quick/full)
        g = solids_gap(sol, stack_view(oev['stack'], oev is ev, 4))
        if g >= 0: g = solids_gap(sol, stack_view(oev['stack'], oev is ev))
        if oev is ev:
            for lo, hi in boxes[1:]:      # boxes[0] is the stage the mast stands on; br['on'] the furniture it stands on instead
                if br['on'] is not None and lo is br['on'][0]: continue
                for kind, *geo in sol:
                    if kind == 'box': g = min(g, float(np.linalg.norm(np.maximum(np.maximum(lo-geo[1], geo[0]-hi), 0)))-GANTRY['margin'])
                    else: g = min(g, box_gap(geo[0][None], geo[1][None], geo[2], lo, hi, 48)-GANTRY['margin'])
        ev['mast_memo'][key] = g
    return ev['mast_memo'][key]

def mast_margin(ev, others, boxes, enough=1e9):
    """Worst over ev's two rail ends of the best bracket there, brackets
    tried cheapest first (the gantry planner's order), each judged by the
    arm's own motion and the scene and by every other option's capsules; a
    bracket `enough` clear ends the search for that end."""
    worst = 1e9
    for k, end in enumerate(ev['ends']):
        best = -1e9
        for c in range(len(end['brackets'])):
            g = column_gap(ev, k, c, ev, boxes)
            for oev in others:
                if g <= best: break
                g = min(g, column_gap(ev, k, c, oev, boxes))
            best = max(best, g)
            if best >= enough: break
        worst = min(worst, best)
    return worst

def cross_gap(ca, cb, sa=None, sb=None, ha=(), hb=()):
    """Worst gap between two arms' capsules, each arm's rail included as an
    obstacle to the other's links (the links slid across their pin span,
    `sa`/`sb` from stack_caps), and each arm's rail heads (`ha`/`hb`, boxes)
    against the other's links as the gantry planner measures them;
    rail-vs-rail is `rails_compatible`'s job."""
    best = 1e9; sa = sa or {}; sb = sb or {}
    if ha or hb:
        best = min(solids_gap([('box',)+h for h in ha], sb) if ha else 1e9, solids_gap([('box',)+h for h in hb], sa) if hb else 1e9)
    sha = sa.get('shifts', {}); shb = sb.get('shifts', {})
    for na, (P1, Q1, r1) in ca.items():
        for nb, (P2, Q2, r2) in cb.items():
            if _is_rail(na) and _is_rail(nb): continue
            for dx in (sha.get(na, (0.,)) if _is_rail(nb) else (0.,)):
                for dy in (shb.get(nb, (0.,)) if _is_rail(na) else (0.,)):
                    best = min(best, float((segment_distance(P1+[dx, 0, 0], Q1+[dx, 0, 0], P2+[dy, 0, 0], Q2+[dy, 0, 0])-r1-r2).min()))
    return best

def heads(ev): return [e['head'] for e in ev['ends']]

def _is_rail(name): return name.startswith(('rail', 'head_', 'rack'))

def rails_compatible(a, b):
    return abs(a['root_y']-b['root_y']) > .22 or abs(a['root_z']-b['root_z']) > .16

def verify_fine(rig, aids, chosen, times, boxes, plane_z, enough, placed=()):
    """The chosen rail set re-measured with the poses sampled four times as
    finely: per arm, the worst of its own margins (the arms of the mechanisms
    planned before, `placed` at the fine rate, included), its cross gaps
    (heads included) and every arm's bracket margins in which it takes part.
    Returns (fine margins per arm, the arms whose option to drop) — an arm
    whose own margins fail; of a failing pair, the one later in `aids` (the
    earlier has priority)."""
    t4 = np.linspace(times[0], times[-1], 4*(len(times)-1)+1)
    evs = {}
    for aid in aids:
        cfg = {k: v for k, v in chosen[aid]['cfg'].items() if k not in ('o1', 'o2', 'pinion')}
        evs[aid] = evaluate_arm(rig, aid, cfg, t4, boxes=boxes, string_plane_z=plane_z, enough=enough, others=placed)
    fine = {aid: (evs[aid]['worst'] if evs[aid] is not None else -1.) for aid in aids}; bad = set()
    for aid in aids:
        if evs[aid] is None or evs[aid]['worst'] < 0: bad.add(aid)
    for i, a in enumerate(aids):
        for b in aids[i+1:]:
            if evs[a] is None or evs[b] is None: continue
            g = cross_gap(evs[a]['caps'], evs[b]['caps'], evs[a]['stack'], evs[b]['stack'], heads(evs[a]), heads(evs[b]))
            fine[a] = min(fine[a], g); fine[b] = min(fine[b], g)
            if g < 0: bad.add(b)
    for aid in aids:
        if evs[aid] is None: continue
        others = [o for o in aids if o != aid and evs[o] is not None]
        g = mast_margin(evs[aid], [evs[o] for o in others], boxes, enough); fine[aid] = min(fine[aid], g)
        if g < 0 and aid not in bad:
            # blame the arm whose parts close the brackets: the later in
            # `aids` of the owner and each arm that alone blocks every
            # bracket (the owner's own motion and the scene are in its
            # `worst` above); if only the combination does, the latest of all
            culprits = [o for o in others if mast_margin(evs[aid], [evs[o]], boxes, enough) < 0]
            if culprits: bad.update(max([aid, o], key=aids.index) for o in culprits)
            else: bad.add(max([aid]+others, key=aids.index))
    return fine, bad

def _mech_key(score, layout, mech, hz, enough, placed=None):
    """Everything the search for one mechanism depends on, hashed: its
    events (times, strings, picks), its string geometry, the obstacles,
    the rails and links of the mechanisms planned before it (`placed`: arm
    id -> cfg), the sampling, the candidate grid and the space model (the
    source text of candidates, evaluate_arm and the whole clearance module)."""
    import hashlib, inspect, sys
    ev = [{k: e.get(k) for k in ('t', 't_move', 't_free', 'strings', 'pick', 'spread_s', 'actuator')}
          for e in score['events'] if e.get('mech') == mech['id']]
    strings = {k: v for k, v in layout['strings'].items() if v['mid'] == mech['id']}
    blob = json.dumps([mech, ev, strings, layout.get('obstacles', []), layout['mechanisms'][mech['id']],
                       {a: layout['arms'][a] for a in (x['id'] for x in mech['actuators'])}, placed or {},
                       score['total_s'], hz, enough, inspect.getsource(candidates), inspect.getsource(evaluate_arm),
                       inspect.getsource(plan_arms), inspect.getsource(verify_fine), inspect.getsource(mast_margin), inspect.getsource(column_gap),
                       inspect.getsource(mast_gaps), inspect.getsource(pin_shifts), inspect.getsource(stack_caps), inspect.getsource(stack_view), inspect.getsource(solids_gap), inspect.getsource(cross_gap),
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
    # The mechanisms are planned in score order, each against the arms of
    # those before it (links, rail hardware and masts, both sampling rates):
    # the gantry planner measures the whole rig, and a harp rack it refused
    # for a bells arm's link was the search's blind spot, not the planner's.
    placed = {}                                   # aid -> dict(coarse=ev at hz, fine=ev at 4 hz)
    t4 = np.linspace(times[0], times[-1], 4*(len(times)-1)+1)
    def place(aid, cfg, plane_z):
        cfg = {k: v for k, v in cfg.items() if k in CFG_KEYS and k not in ('o1', 'o2', 'pinion')}
        placed[aid] = dict(coarse=evaluate_arm(rig, aid, cfg, times, boxes=boxes, string_plane_z=plane_z, enough=enough),
                           fine=evaluate_arm(rig, aid, cfg, t4, boxes=boxes, string_plane_z=plane_z, enough=enough))
    for mech in score['instrument']['mechanisms']:
        aids = [a['id'] for a in mech['actuators']]
        strings = [s for s in layout['strings'].values() if s['mid'] == mech['id']]
        plane_z = float(np.mean([s['a'][2] for s in strings])) if mech['kind'] != 'struck' else None
        key = _mech_key(score, layout, mech, hz, enough, {a: {k: layout['arms'][a][k] for k in CFG_KEYS if k in layout['arms'][a]} for a in placed}) if cache else None
        if key and key in store:
            for aid in aids:
                layout['arms'][aid].update(store[key][aid])
                if verbose: verbose(f"  RAIL {aid}: (cached) "+' '.join(f'{k2}={v}' for k2, v in store[key][aid].items() if k2 != 'margins'))
                place(aid, store[key][aid], plane_z)
            continue
        coarse = [p['coarse'] for p in placed.values()]; fine_placed = [p['fine'] for p in placed.values()]
        options = {aid: [] for aid in aids}
        for aid in aids:
            for cfg in candidates(mech, layout):
                ev = evaluate_arm(rig, aid, cfg, times, boxes=boxes, string_plane_z=plane_z, enough=enough, others=coarse)
                if ev is not None: options[aid].append(ev)
            if not options[aid]: raise ValueError(f'no feasible rail for {aid}')
        chosen = {}; memo = {}
        def objective(aid, ev):
            worst = ev['worst']
            others = {o: oev for o, oev in chosen.items() if o != aid}
            for other, oev in others.items():
                if not rails_compatible(ev['cfg'], oev['cfg']): return (-1e9,)
                key = ('cross', id(ev), id(oev))
                if key not in memo: memo[key] = cross_gap(ev['caps'], oev['caps'], ev['stack'], oev['stack'], heads(ev), heads(oev))
                worst = min(worst, memo[key])
            # every arm's masts must still stand with this option in place
            if others:
                worst = min(worst, mast_margin(ev, list(others.values()), boxes, enough))
                for other, oev in others.items():
                    worst = min(worst, mast_margin(oev, [ev]+[x for o, x in others.items() if o != other], boxes, enough))
            return (min(worst, enough), -ev['cfg']['l1'], -abs(ev['cfg']['root_y']-2.75), worst)
        from itertools import permutations
        orders = list(permutations(aids)) if len(aids) <= 3 else [tuple(aids[k:]+aids[:k]) for k in range(len(aids))]
        def set_worst(): return min(objective(aid, chosen[aid])[3] for aid in aids)
        for attempt in range(6):
            # Greedy placement then coordinate descent, from every placement
            # order: a set can lock — each arm's alternatives judged by a third
            # arm's blocked masts, so only the tie-breakers speak and nothing
            # moves — and the order the arms are placed in decides whether it
            # does. Keep the order whose set stands clearest.
            best = None
            for order in orders:
                chosen.clear()
                for aid in order:                     # greedy
                    chosen[aid] = max(options[aid], key=lambda ev: objective(aid, ev))
                for _ in range(2):                    # coordinate descent
                    for aid in order:
                        chosen[aid] = max(options[aid], key=lambda ev: objective(aid, ev))
                w = set_worst()
                if best is None or w > best[0]: best = (w, dict(chosen))
                if w >= enough: break
            chosen.clear(); chosen.update(best[1])
            if verbose and best[0] < enough: verbose(f"  RAIL {mech['id']}: clearest set over {len(orders)} placement orders stands {best[0]:+.3f} m at {hz} Hz")
            # The search samples at hz; the gantry planner confirms at 4 hz and
            # a pick's fast stroke can close 50 mm between samples. Re-measure
            # the chosen set at its rate and, if it does not pass there, drop
            # the offending option(s) and search again.
            fine, bad = verify_fine(rig, aids, chosen, times, boxes, plane_z, enough, placed=fine_placed)
            for aid in aids: chosen[aid]['margins']['fine'] = fine[aid]
            if not bad: break
            if verbose: verbose(f"  RAIL {mech['id']}: at {4*hz} Hz "+' '.join(f"{aid}(y={chosen[aid]['cfg']['root_y']:.2f} z={chosen[aid]['cfg']['root_z']:.2f} l={chosen[aid]['cfg']['l1']:.2f})={fine[aid]:+.3f}" for aid in aids))
            for aid in bad:
                if verbose: verbose(f"  RAIL {aid}: y={chosen[aid]['cfg']['root_y']:.2f} z={chosen[aid]['cfg']['root_z']:.2f} l={chosen[aid]['cfg']['l1']:.2f} blamed at {4*hz} Hz; dropped")
                options[aid] = [ev for ev in options[aid] if ev is not chosen[aid]]
                if not options[aid]: raise ValueError(f'no feasible rail for {aid} at {4*hz} Hz')
        else:
            raise ValueError(f'no rail set for {mech["id"]} passes at {4*hz} Hz')
        for k, aid in enumerate(aids):
            ev = chosen[aid]; cfg = ev['cfg']
            cross = {o: cross_gap(ev['caps'], chosen[o]['caps'], ev['stack'], chosen[o]['stack'], heads(ev), heads(chosen[o])) for o in aids if o != aid}
            ev['margins']['mast'] = min(ev['margins']['mast'], mast_margin(ev, [chosen[o] for o in aids if o != aid], boxes, enough))
            layout['arms'][aid].update(cfg)
            layout['arms'][aid]['margins'] = dict({k2: round(v, 4) for k2, v in ev['margins'].items()}, cross={o: round(g, 4) for o, g in cross.items()})
            if verbose: verbose(f"  RAIL {aid}: y={cfg['root_y']:.2f} z={cfg['root_z']:.2f} l={cfg['l1']:.2f} bend={cfg['bend']} margins="+
                                ' '.join(f'{k2}={v:.3f}' for k2, v in ev['margins'].items())+' cross='+' '.join(f'{o}={g:.3f}' for o, g in cross.items()))
        if key:
            store[key] = {aid: dict(chosen[aid]['cfg'], margins=layout['arms'][aid]['margins']) for aid in aids}
            os.makedirs(os.path.dirname(cache) or '.', exist_ok=True)
            _json.dump(store, open(cache, 'w'), indent=1)
        for aid in aids: place(aid, chosen[aid]['cfg'], plane_z)
    return layout['arms']

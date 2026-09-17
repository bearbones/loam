"""Rail gantries: what actually holds an arm's guide bars up.

The first rails hung from bare posts — a brass rod per end, up to four metres
tall, with a disc for a foot, and the neighbouring rails simply ran through
them. A linear guide in the real world ends in a **rail head** that captures
both bars, bolted down onto a **mast**; a tall mast stands on a stepped
**plinth**, and if the head cannot sit directly over the mast (another rail
or an arm is in the way) it is carried on a **bracket** back to the mast with
a **knee brace** under it, the way a signal gantry or a wall-jib crane does.

Every dimension here comes from a rule, not from the eye:

- The mast is a tapered box column, deep along Z (the arm's swing direction —
  the load that racks it) and growing toward the base as a cantilever's
  bending moment does; the width across X stays constant because nothing
  loads it that way.
- The head's inner face sits 0.16 m beyond the arm's reach window: the
  shoulder pin's head reaches 0.119 m from the carriage plane
  (``linkage.knuckle_pin``), so a carriage parked at the end of its rail
  clears the head by 40 mm. (The old posts stood at 0.12 m with a 35 mm
  radius — the pin passed through them.)
- The setback of the mast behind its rail is *searched*, smallest first, and
  the first placement whose pieces clear every arm's swept capsules, every
  other rail's bars, the instrument forms, the furniture boxes and the
  gantries already placed is kept. A mast may stand on a furniture box (the
  cabinet lid) as readily as on the stage.

Numpy only: ``tools/build_forms.py`` runs this in plain Python, and the
ruler ``tools/test_gantry.py`` re-derives the placement from a manifest.
"""
import numpy as np
try:
    from .sweep import sweep, validate_mesh
    from .linkage import rounded_rect, revolve
    from .clearance import arm_capsules, default_layers, DEFAULT_SPEC, segment_distance, PINION, MOUNTS, pinion_centre, rack_direction
    from .layout_search import box_gap, scene_boxes
except ImportError:   # bare import (formlab/ on sys.path)
    from sweep import sweep, validate_mesh
    from linkage import rounded_rect, revolve
    from clearance import arm_capsules, default_layers, DEFAULT_SPEC, segment_distance, PINION, MOUNTS, pinion_centre, rack_direction
    from layout_search import box_gap, scene_boxes

RAIL_OVER = .12        # the bars run this far beyond the reach window (build_clockwork)
BAR_R = .024; BAR_DY = .075
HEAD_INSET = .04       # head's inner face beyond the bar end: 0.16 m past the window
HEAD_LEN = .20; HEAD_H = .14; HEAD_D = .07       # rail head: half-height, half-depth
MAST_W = .045          # half-width across X (constant)
MAST_D_TOP = .05       # half-depth along Z at the top
MAST_D_CAP = .11       # half-depth at the base, at most
MARGIN = .02           # every gantry piece keeps this much from everything else
PIN_X = .119           # an arm's pin heads reach this far from its capsule plane (linkage.knuckle_pin)
STAGE = dict(x=(-6.4, 6.4), z=(-4.6, 3.3), top=-.02)
SETBACKS = (0., .40, .55, .70, .85, 1.0, 1.2, 1.5)     # mast behind the rail (Z); negative = in front
OUTREACHES = (0., .35, .5, .7)                          # mast beyond the rail end (X)
# cheapest bracket first: straight down, then back, then out, then both; behind before in front
CANDIDATES = sorted(((o, sb) for o in OUTREACHES for sb in SETBACKS+tuple(-x for x in SETBACKS[1:])),
                    key=lambda c: (c[0]+abs(c[1]), c[1] < 0, c[0]))


def prism(a, b, w, d, corner=.25, count=None):
    """Straight rounded-rectangle prism from a to b. On a path along ±X the
    half-widths are (Y, Z); along ±Y they are (X, Z); along ±Z, (Y, X) — the
    sweep's transport frame. `w` and `d` may be arrays along the path."""
    a = np.asarray(a, float); b = np.asarray(b, float)
    n = count or max(3, int(np.linalg.norm(b-a)/.25)+2)
    u = np.linspace(0, 1, n)[:, None]
    return sweep(a+(b-a)*u, w, d, profile=rounded_rect(corner, 16))


def bolt_head(centre, axis=(0, 1, 0), r=.011, h=.016):
    """A hex-ish bolt head standing on a face, along `axis`."""
    pr = [(0, -.006), (r, -.006), (r, h*.7), (r*.6, h), (0, h)]
    return revolve(pr, axis, centre, 12)


def aabb(pieces):
    V = np.concatenate([p.vertices for p in pieces]); return V.min(0), V.max(0)


def solids(end):
    """Each piece as its own bounding box, except the diagonal knee brace,
    which is a capsule — the union box of a bracket, brace and mast would fill
    the corner an arm's elbow legitimately swings through."""
    out = []
    for p in end['brass']+end['steel']:
        if getattr(p, 'brace', False): out.append(('capsule', (p.path[0], p.path[-1], .017*1.5)))
        else: out.append(('box', (p.vertices.min(0), p.vertices.max(0))))
    return out


def rail_end(x_end, side, ry, rz, behind, setback, foot_y, outreach=0.):
    """Pieces for one end of a rail. side = -1 (low x) / +1 (high x); behind =
    ±1, the side away from the strings. Returns dict(brass=[...], steel=[...],
    mast_z, x_col)."""
    s = float(side); x_in = x_end+s*HEAD_INSET; x_col = x_in+s*(HEAD_LEN-.07+outreach)
    z_m = rz+behind*setback; x_head = x_in+s*HEAD_LEN
    brass = [prism((x_in+s*HEAD_LEN, ry, rz), (x_in, ry, rz), HEAD_H, HEAD_D, .3, 3)]
    steel = []
    top = ry+HEAD_H if (setback or outreach) else ry-HEAD_H
    H = top-(foot_y+.08)
    d_base = min(MAST_D_TOP+.025*H, MAST_D_CAP)
    n = max(3, int(H/.25)+2)
    steel.append(prism((x_col, foot_y+.06, z_m), (x_col, top, z_m), MAST_W,
                       np.linspace(d_base, MAST_D_TOP, n), .2, n))
    # stepped plinth, anchor bolts at its corners
    steel.append(prism((x_col, foot_y, z_m), (x_col, foot_y+.045, z_m), .17, d_base+.10, .15, 3))
    steel.append(prism((x_col, foot_y+.04, z_m), (x_col, foot_y+.085, z_m), .12, d_base+.05, .15, 3))
    for dx in (-.13, .13):
        for dz in (-(d_base+.06), d_base+.06):
            steel.append(bolt_head((x_col+dx, foot_y+.045, z_m+dz)))
    if setback or outreach:
        # An L-bracket: out along X first (clear of the neighbouring arm's
        # carriage, which sits at the same height), then along Z to the
        # mast; a knee brace under each leg longer than a head.
        knee = (x_col, ry, rz); dz = behind*np.sign(setback)
        if outreach:
            brass.append(prism((x_head-s*.06, ry, rz), knee, .08, .04, .3, 3))
            brace = prism((x_head-s*.08, ry-.10, rz), (x_col, ry-.10-min(outreach+.13, 1.0), rz), .017, .017, .3, 3)
            brace.brace = True; steel.append(brace)
        if setback:
            brass.append(prism((x_col, ry, rz-dz*.04 if outreach else rz+dz*(HEAD_D-.02)), (x_col, ry, z_m), .08, .04, .3, 3))
            brace = prism((x_col, ry-.10, rz+dz*.03), (x_col, ry-.10-min(abs(setback), 1.0), z_m), .017, .017, .3, 3)
            brace.brace = True; steel.append(brace)
        for dzb in (-.03, .03):
            steel.append(bolt_head((x_col, ry+HEAD_H, z_m+dzb)))
    else:
        for dx in (-.05, .05):
            for dz in (-.035, .035):
                steel.append(bolt_head((x_col+dx, ry+HEAD_H, rz+dz)))
    return dict(brass=brass, steel=steel, mast_z=z_m, x_col=x_col, foot_y=foot_y, height=H, setback=setback, outreach=outreach)


def foot_level(x, z, boxes):
    """Stage top, or the lid of a furniture box the mast footprint stands on."""
    y = STAGE['top']; on = None
    for lo, hi in boxes:
        if lo[0]+.22 <= x <= hi[0]-.22 and lo[2]+.22 <= z <= hi[2]-.22 and hi[1] < 1e8:
            if hi[1] > y: y, on = float(hi[1]), (lo, hi)
    return y, on


def behind_sign(cfg, strings):
    zs = np.mean([s['a'][2] for s in strings.values() if s['mid'] == cfg['mid']])
    return -1.0 if cfg['root_z'] < zs else 1.0


def rail_bars(cfg):
    """The two guide bars as capsules (P, Q, r), running into the heads."""
    x0, x1 = cfg['reach_x']; ry = cfg['root_y']; rz = cfg['root_z']
    xa = x0-RAIL_OVER-HEAD_INSET-.10; xb = x1+RAIL_OVER+HEAD_INSET+.10
    return [(np.array([xa, ry+dy, rz]), np.array([xb, ry+dy, rz]), BAR_R) for dy in (-BAR_DY, BAR_DY)]


RACK_GAP = .004        # tooth tip to hub, tooth root to the pinion's tips, tooth flank to tooth flank


def rack_geometry(cfg):
    """A rail's rack: a toothed strip the pinion rolls on, as long as the
    bars, in the disc's plane on the side rack_direction points — above a
    front/back disc, behind an up/down one. Radial distances from the axle:
    s_tip (tooth tips, just off the hub), s_root (tooth roots, just past the
    pinion's tips), s_top (the strip's back). Tooth k is centred at
    x = (k + 1/2) * pitch, so the pinion's tooth pointing at the rack when
    its carriage is at x = 0 rolls into the gaps (harness/performance.gd
    turns it by x / r_pitch)."""
    G = PINION; x0, x1 = cfg['reach_x']; mount = cfg.get('pinion', 'back')
    centre = np.array([0., cfg['root_y'], cfg['root_z']])+pinion_centre(mount)
    return dict(mount=mount, normal=MOUNTS[mount], centre=centre, u=rack_direction(mount), h=G['thickness']/2,
                x_a=x0-RAIL_OVER-.14, x_b=x1+RAIL_OVER+.14, s_tip=G['r_hub']+RACK_GAP,
                s_root=G['r_tip']+RACK_GAP+.001, s_top=G['r_tip']+RACK_GAP+.031, pitch=2*np.pi*G['r_pitch']/G['teeth'])


def _rack_stub_x(R): return (R['x_a']+.03, R['x_b']-.03)


def rack(cfg):
    """Rack pieces (brass): the strip, its teeth, and a stub from each rail
    head carrying it — off the head's face for a front/back disc, an L up
    (or down) from the head's top (bottom) and back for an up/down disc.
    Pitched to formlab.clearance.PINION."""
    R = rack_geometry(cfg); G = PINION; ny, nz = R['normal']; c = R['centre']; u = R['u']; h = R['h']
    s_mid = (R['s_root']+R['s_top'])/2; w_strip = (R['s_top']-R['s_root'])/2
    tooth_w = R['pitch']-G['r_tip']*.22-2*RACK_GAP        # the pinion's tooth is .22 r_tip wide
    radial = nz != 0                                       # radial axis is Y (front/back) or Z (up/down)
    a = c+u*s_mid; b = c+u*s_mid; a[0] = R['x_a']; b[0] = R['x_b']
    pieces = [prism(a, b, w_strip if radial else h, h if radial else w_strip, .3, 3)]
    k0 = int(np.ceil((R['x_a']+.02)/R['pitch']-.5)); k1 = int(np.floor((R['x_b']-.02)/R['pitch']-.5))
    for k in range(k0, k1+1):
        x = (k+.5)*R['pitch']; a = c+u*(R['s_root']+.006); b = c+u*R['s_tip']; a[0] = b[0] = x
        pieces.append(prism(a, b, tooth_w/2 if radial else h-.006, h-.006 if radial else tooth_w/2, .3, 3))
    ry = cfg['root_y']; rz = cfg['root_z']
    for x in _rack_stub_x(R):
        if radial:
            pieces.append(prism((x, ry+s_mid, rz+nz*.05), (x, ry+s_mid, c[2]), w_strip-.002, .03, .3, 3))
        else:
            y_arm = ny*(PINION['up']+.005)
            pieces.append(prism((x, ry+ny*(HEAD_H-.02), rz-.05), (x, ry+y_arm+ny*.015, rz-.05), .03, .02, .3, 3))
            pieces.append(prism((x, ry+y_arm, rz-.05), (x, ry+y_arm, c[2]-R['s_top']-.01), .015, .03, .3, 3))
    return pieces


def rack_boxes(cfg):
    """AABBs of a rail's rack (strip with teeth) and its stubs."""
    R = rack_geometry(cfg); ny, nz = R['normal']; c = R['centre']; h = R['h']; ry = cfg['root_y']; rz = cfg['root_z']
    lo = c+R['u']*R['s_tip']; hi = c+R['u']*R['s_top']; lo[0] = R['x_a']; hi[0] = R['x_b']
    n = np.array([0., ny, nz])*h; boxes = [('rack', (np.minimum(lo, hi)-abs(n), np.maximum(lo, hi)+abs(n)))]
    for i, x in enumerate(_rack_stub_x(R)):
        if nz:
            z_lo, z_hi = sorted((rz+nz*.05, c[2]))
            boxes.append((f'rack stub {i}', (np.array([x-.03, ry+R['s_root'], z_lo]), np.array([x+.03, ry+R['s_top'], z_hi]))))
        else:
            y_arm = ny*(PINION['up']+.005); y0, y1 = sorted((ry+ny*(HEAD_H-.02), ry+y_arm+ny*.015))
            boxes.append((f'rack stub {i} post', (np.array([x-.03, y0, rz-.07]), np.array([x+.03, y1, rz-.03]))))
            boxes.append((f'rack stub {i} arm', (np.array([x-.03, ry+y_arm-.015, c[2]-R['s_top']-.01]), np.array([x+.03, ry+y_arm+.015, rz-.03]))))
    return boxes


def rail_racks(cfg):
    """The rack as one capsule (P, Q, r) for the arm rulers."""
    R = rack_geometry(cfg); m = R['centre']+R['u']*(R['s_tip']+R['s_top'])/2
    P = m.copy(); Q = m.copy(); P[0] = R['x_a']; Q[0] = R['x_b']
    return [(P, Q, max((R['s_top']-R['s_tip'])/2, R['h']))]


def _pin_span(arm, P, Q, r):
    """How far a capsule may be slid along X either way so that the arm, as a
    whole, reaches the pin tips' planes at ±PIN_X from its carriage plane:
    the capsules sit at fixed offsets from that plane (the parallel bars a
    layer outboard) and the knuckle pins are the widest thing on it."""
    root = arm['upper'][0][:, 0]
    lo = float(np.mean(np.minimum(P[:, 0], Q[:, 0])-root)); hi = float(np.mean(np.maximum(P[:, 0], Q[:, 0])-root))
    return (min(-PIN_X-lo+r, 0.), max(PIN_X-hi-r, 0.))


def _gap_box(lo, hi, caps, bars, boxes, others, exempt):
    worst = (1e9, 'nothing')
    for aid, arm in caps.items():
        for name, (P, Q, r) in arm.items():
            d_lo, d_hi = _pin_span(arm, P, Q, r)
            g = box_gap(P, Q, r, lo-[d_hi, 0, 0], hi-[d_lo, 0, 0], 24)
            if g < worst[0]: worst = (g, f'arm {aid} {name}')
    for name, (P, Q, r) in bars:
        g = box_gap(P[None], Q[None], r, lo, hi, 48)
        if g < worst[0]: worst = (g, f'rail {name}')
    for name, (blo, bhi) in boxes:
        if any(blo is e[0] for e in exempt): continue
        d = np.maximum(np.maximum(blo-hi, lo-bhi), 0); g = float(np.linalg.norm(d))
        if g < worst[0]: worst = (g, f'box {name}')
    for name, (olo, ohi) in others:
        d = np.maximum(np.maximum(olo-hi, lo-ohi), 0); g = float(np.linalg.norm(d))
        if g < worst[0]: worst = (g, f'gantry {name}')
    return worst


def _gap_capsule(P, Q, r, caps, bars, boxes, others, exempt):
    worst = (1e9, 'nothing')
    for aid, arm in caps.items():
        for name, (A, B, ra) in arm.items():
            for dx in _pin_span(arm, A, B, ra)+(0.,):
                g = float(segment_distance(A+[dx, 0, 0], B+[dx, 0, 0], P[None], Q[None]).min())-r-ra
                if g < worst[0]: worst = (g, f'arm {aid} {name}')
    for name, (A, B, rb) in bars:
        g = float(segment_distance(A[None], B[None], P[None], Q[None]).min())-r-rb
        if g < worst[0]: worst = (g, f'rail {name}')
    for name, (blo, bhi) in list(boxes)+list(others):
        if any(blo is e[0] for e in exempt): continue
        g = box_gap(P[None], Q[None], r, blo, bhi, 48)
        if g < worst[0]: worst = (g, f'box {name}')
    return worst


def clearance(end, caps, bars, boxes, others, exempt=()):
    """Worst gap between the end's solids and everything else."""
    worst = (1e9, 'nothing')
    for kind, geo in solids(end):
        g = _gap_box(*geo, caps, bars, boxes, others, exempt) if kind == 'box' else _gap_capsule(*geo, caps, bars, boxes, others, exempt)
        if g[0] < worst[0]: worst = g
    return worst


def _caps(layout, poses, step=1):
    layers = default_layers(DEFAULT_SPEC); out = {}
    for aid, cfg in layout['arms'].items():
        p = {k: v[::step] for k, v in poses[aid].items()}
        out[aid] = arm_capsules(p, cfg['o1'], cfg['o2'], cfg.get('layers', layers), DEFAULT_SPEC, cfg.get('pinion', 'back'))[0]
    return out


def plan_end(aid, cfg, side, x_end, behind, quick, full, other_bars, boxes, placed, verbose=print):
    """Cheapest bracket (outreach along X, setback along Z) for one rail end
    whose solids clear everything; screened at 30 Hz, confirmed at 120 Hz."""
    ry = cfg['root_y']; rz = cfg['root_z']; tried = []
    for outreach, sb in CANDIDATES:
        x_col = x_end+side*(HEAD_INSET+HEAD_LEN-.07+outreach); z_m = rz+behind*sb
        if not (STAGE['x'][0] < x_col < STAGE['x'][1] and STAGE['z'][0] < z_m < STAGE['z'][1]):
            tried.append((outreach, sb, -1, 'off the stage')); continue
        foot, on = foot_level(x_col, z_m, [b for _, b in boxes])
        end = rail_end(x_end, side, ry, rz, behind, sb, foot, outreach); exempt = [on] if on else ()
        # not its own head (the bracket carries it) or its rack's stubs (they are built into the head); its rack strip counts
        others = [pl for pl in placed if pl[0] != f'{aid} head' and not pl[0].startswith(f'{aid} rack stub')]
        gap, what = clearance(end, quick, other_bars, boxes, others, exempt)
        if gap >= MARGIN: gap, what = clearance(end, full, other_bars, boxes, others, exempt)
        if gap >= MARGIN:
            end.update(gap=gap, worst=what, side=side, tried=tried); return end
        tried.append((outreach, sb, gap, what))
    for outreach, sb, gap, what in tried:
        verbose(f'  gantry {aid} {"low" if side < 0 else "high"} end: out {outreach:.2f} back {sb:.2f} blocked by {what} ({gap:+.3f} m)')
    raise ValueError(f'no gantry placement clears the scene for {aid} ({"low" if side < 0 else "high"} end)')


def plan_gantries(layout, poses, form_boxes=(), verbose=print):
    """Choose a bracket per rail END and build it. `poses`: aid -> poses dict
    over the sampled piece (formlab.rig.Rig.poses, 120 Hz). `form_boxes`:
    (name, (lo, hi)) of the instrument forms. Returns aid -> dict(ends,
    brass, steel, margin, worst, ...)."""
    quick = _caps(layout, poses, 4); full = _caps(layout, poses, 1)
    boxes = [(f'obstacle{i}', b) for i, b in enumerate(scene_boxes(layout)[1:])]+list(form_boxes)
    bars = [(aid, b) for aid, cfg in layout['arms'].items() for b in rail_bars(cfg)]
    out = {}
    # every head is fixed by its rail: reserve them all before any bracket is chosen
    placed = [(f'{aid} head', (np.array([xa, cfg['root_y']-HEAD_H, cfg['root_z']-HEAD_D]), np.array([xb, cfg['root_y']+HEAD_H, cfg['root_z']+HEAD_D])))
              for aid, cfg in layout['arms'].items()
              for xa, xb in ((cfg['reach_x'][0]-RAIL_OVER-HEAD_INSET-HEAD_LEN, cfg['reach_x'][0]-RAIL_OVER-HEAD_INSET),
                             (cfg['reach_x'][1]+RAIL_OVER+HEAD_INSET, cfg['reach_x'][1]+RAIL_OVER+HEAD_INSET+HEAD_LEN))]
    # so are the racks: fixed by their rails, so every bracket avoids them
    placed += [(f'{aid} {name}', geo) for aid, cfg in layout['arms'].items() for name, geo in rack_boxes(cfg)]
    for aid, cfg in layout['arms'].items():
        x0, x1 = cfg['reach_x']; behind = behind_sign(cfg, layout['strings'])
        other_bars = [b for b in bars if b[0] != aid]; ends = []
        # The rack has no placement to search; it must simply clear the OTHER
        # arms (the rail search keeps them off it), rails, forms and gantries.
        others = [pl for pl in placed if not pl[0].startswith(f'{aid} ')]
        rack_gap = min((_gap_box(*geo, {a: c for a, c in full.items() if a != aid}, other_bars, boxes, others, ())
                        for _, geo in rack_boxes(cfg)), key=lambda g: g[0])
        if rack_gap[0] < MARGIN:
            raise ValueError(f'rack of {aid} blocked by {rack_gap[1]} ({rack_gap[0]:+.3f} m)')
        for side, x_end in ((-1, x0-RAIL_OVER), (1, x1+RAIL_OVER)):
            end = plan_end(aid, cfg, side, x_end, behind, quick, full, other_bars, boxes, placed, verbose)
            placed += [(aid, geo) for kind, geo in solids(end) if kind == 'box']; ends.append(end)
        out[aid] = dict(behind=behind, brass=sum((e['brass'] for e in ends), rack(cfg)), steel=sum((e['steel'] for e in ends), []),
                        rack=dict(gap=rack_gap[0], worst=rack_gap[1], mount=cfg.get('pinion', 'back')),
                        margin=min([e['gap'] for e in ends]+[rack_gap[0]]), worst=min(ends, key=lambda e: e['gap'])['worst'],
                        ends=[dict(side=e['side'], outreach=e['outreach'], setback=e['setback'], mast_z=e['mast_z'],
                                   x_col=e['x_col'], foot_y=e['foot_y'], height=e['height'], gap=e['gap'], worst=e['worst'])
                              for e in ends])
        verbose('  gantry %s: %s; margin %.3f m (%s)' % (aid, ', '.join(
            f'{"low" if e["side"] < 0 else "high"} end out {e["outreach"]:.2f} back {e["setback"]:.2f} mast {e["height"]:.2f} m' for e in ends),
            out[aid]['margin'], out[aid]['worst']))
    return out

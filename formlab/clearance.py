"""Space accounting for articulated rigs: capsule-vs-capsule clearance over a
sampled motion, and the parallelogram offset chooser.

Every moving part is abstracted to capsules (segment + radius) in WORLD space
per pose. Bars are one capsule pin-to-pin; ears and bosses are short capsules
along the pin axis; strings are capsules too. The ruler reports the minimum
signed gap between every pair of parts that is not joined at a shared pin,
over every sampled pose — a cheap, conservative pre-flight before the exact
BVH check in tools/check_form_clearance.py.
"""
import numpy as np

# Section dimensions shared with formlab.linkage (kept here so the space
# rulers import without SciPy, e.g. inside Blender's Python).
DEFAULT_SPEC = dict(width=.034, depth=.062, ear_r=.055, pin_r=.018, ear_t=.028, head_t=.03, boss_r=.05, web=.05)
# The linear carriage (formlab.linkage.carriage_body): a split bushing riding
# each guide bar, a cheek plate on the -X side joining them (the +X side is
# taken by the second bar's boss), and the pinion's axle out of the carriage
# plane — or, for a pinion above or below the carriage, a bridge back from
# the bushing carrying a vertical axle clear of the bars (bridge_y is the
# block's extent along the mount direction, bridge_z how far back it
# reaches; the axle stands at axle_z). bar_dy / bar_r are the rail's
# (tools/build_clockwork.py).
CARRIAGE = dict(bar_dy=.075, bar_r=.024, bush_r=.045, bush_len=.16, cheek_x=-.062, cheek_t=.02,
                cheek_y=.12, cheek_z=.045, axle_r=.02, bridge_y=(.085, .125), bridge_z=-.13, bridge_x=.03, axle_z=-.10)
# The drive pinion (build_clockwork.gear) on its axle, and the rack it rolls
# on (formlab.gantry.rack). The disc sits on one of four MOUNTS off the
# carriage — in front, behind, above or below — whichever the arm's links
# never swing through (pinion_mount): `out` from the carriage plane for
# front/back (axle along Z, rack above the disc), `up` above the rail axis
# for up/down (vertical axle at CARRIAGE.axle_z, rack behind the disc).
PINION = dict(out=.195, up=.17, r_pitch=.12, teeth=16, thickness=.07, r_tip=.13, r_hub=.1014)
# mount -> disc-plane normal (y, z); preference order for ties
MOUNTS = dict(back=(0., -1.), up=(1., 0.), down=(-1., 0.), front=(0., 1.))

def pinion_centre(mount):
    """Disc centre relative to the carriage's shoulder pin."""
    ny, nz = MOUNTS[mount]
    if nz: return np.array([0., 0., nz*PINION['out']])
    return np.array([0., ny*PINION['up'], CARRIAGE['axle_z']])

def rack_direction(mount):
    """Unit vector in the disc's plane from its axle toward the rack: up for
    a front/back disc, back for an up/down one (nothing swings behind the
    rail above or below its bars)."""
    return np.array([0., 1., 0.]) if MOUNTS[mount][1] else np.array([0., 0., -1.])

def drive_capsules(root, mount):
    """The pinion (a stack of chords in its plane, shortened by their radius
    so the disc's rim is not overstated toward the rail heads), its axle
    and — for an up/down mount — the bridge the axle stands on. World
    capsules per pose, name -> (P, Q, r)."""
    C = CARRIAGE; G = PINION; X = np.array([1., 0, 0]); ny, nz = MOUNTS[mount]
    n = np.array([0., ny, nz]); centre = root+pinion_centre(mount); h = G['thickness']/2
    u = rack_direction(mount)          # in-plane axis the chords are stacked along
    caps = {}
    if nz:
        caps['carriage_axle'] = (root+n*.03, centre-n*h, C['axle_r'])
    else:
        b0, b1 = C['bridge_y']; by = np.array([0., ny*(b0+b1)/2, 0.])
        caps['carriage_bridge'] = (root+by, root+by+[0, 0, C['bridge_z']], (b1-b0)/2+.01)
        caps['carriage_axle'] = (root+[0, ny*b1-ny*.01, C['axle_z']], centre-n*h, C['axle_r'])
    for k, s in enumerate((-.11, -.07, 0., .07, .11)):
        half = max(np.sqrt(G['r_tip']**2-s*s)-h, .02)
        caps[f'pinion{k}'] = (centre-X*half+u*s, centre+X*half+u*s, h)
    return caps

MOUNT_COMFORT = .05    # a mount this clear of the links is taken in preference order

def pinion_mount(poses, o1, o2, layers, spec, mounts=None):
    """Which mount keeps the drive clear of the arm's own links over the
    motion. The minimum gap between the pinion, axle and bridge and the
    links, webs and bars is measured for each mount; the first in MOUNTS
    order (behind the rail — away from the strings — then above, below, in
    front) with MOUNT_COMFORT to spare is taken, else the clearest.
    Returns (mount, gap)."""
    best = None
    for m in (mounts or MOUNTS):
        caps, adjacent = arm_capsules(poses, o1, o2, layers, spec, m)
        drive = [k for k in caps if k.startswith('pinion') or k in ('carriage_axle', 'carriage_bridge')]
        gap = 1e9
        for a in drive:
            for b in ('upper', 'upper2', 'lower', 'lower2', 'carriage_web', 'elbowhead_web1', 'elbowhead_web2'):
                if frozenset((a, b)) in adjacent: continue
                P1, Q1, r1 = caps[a]; P2, Q2, r2 = caps[b]
                gap = min(gap, float((segment_distance(P1, Q1, P2, Q2)-r1-r2).min()))
        if gap >= MOUNT_COMFORT: return m, gap
        if best is None or gap > best[1]+1e-9: best = (m, gap)
    return best

def rail_keep_clear():
    """The two guide bars in the carriage's swing plane, for choose_offset."""
    return [((s*CARRIAGE['bar_dy'], 0.), CARRIAGE['bar_r']) for s in (-1, 1)]
def bezier(points, count=24):
    """Cubic (or quadratic) Bezier samples, (count, 3)."""
    P = np.asarray(points, float); u = np.linspace(0, 1, count)[:, None]
    if len(P) == 4:
        return (1-u)**3*P[0]+3*(1-u)**2*u*P[1]+3*(1-u)*u**2*P[2]+u**3*P[3]
    return (1-u)**2*P[0]+2*(1-u)*u*P[1]+u**2*P[2]

SOCKET_DEPTH = .075    # socket mouth this far below the boss centre (boss radius .05 + collar)

def tool_mount(wrist_offset, o2):
    """Where a tool hangs from its wrist crosshead, relative to the contact
    point: under the wrist pin's boss, entered from directly below. The
    second bar's boss never hangs lower — choose_offset keeps that offset
    pointing up or level, so the web and the lower bar's second pin stay
    out of the shank's way. o2 is accepted for the record and checked."""
    w = np.asarray(wrist_offset, float); o = np.asarray(o2, float)
    if o[1] < -1e-9: raise ValueError('second-bar offset must point up or level (choose_offset half_plane)')
    return w

def shank_path(start, mount, rise=.05, count=24):
    """Swan-neck centreline from `start` (top of the tool) to the socket mouth
    under `mount`: rises vertically, curves across, arrives vertically. A
    straight drop when the mount is directly above."""
    start = np.asarray(start, float); mount = np.asarray(mount, float)
    end = mount-[0, SOCKET_DEPTH, 0]
    rise = min(rise, max((end[1]-start[1])/2, .005))
    return bezier([start, start+[0, rise, 0], end-[0, rise, 0], end], count)

def default_layers(spec=DEFAULT_SPEC):
    gap = spec['head_t']+.006
    outer = gap/2+spec['ear_t']+.006+spec['width']/2
    return dict(outer=outer, gap=gap, span=2*outer+spec['width']*.8+.004)

def segment_distance(p1, q1, p2, q2):
    """Vectorised minimum distance between segments p1q1 and p2q2 (Ericson 5.1.9).
    All inputs broadcast to (..., 3)."""
    d1 = q1-p1; d2 = q2-p2; r = p1-p2
    a = np.einsum('...i,...i', d1, d1); e = np.einsum('...i,...i', d2, d2); f = np.einsum('...i,...i', d2, r)
    c = np.einsum('...i,...i', d1, r); b = np.einsum('...i,...i', d1, d2)
    denom = a*e-b*b
    s = np.where(denom > 1e-14, np.clip((b*f-c*e)/np.where(denom > 1e-14, denom, 1), 0, 1), 0.0)
    t = (b*s+f)/np.where(e > 1e-14, e, 1)
    s = np.where(t < 0, np.clip(-c/np.where(a > 1e-14, a, 1), 0, 1), s)
    s = np.where(t > 1, np.clip((b-c)/np.where(a > 1e-14, a, 1), 0, 1), s)
    t = np.clip(t, 0, 1)
    c1 = p1+d1*s[..., None]; c2 = p2+d2*t[..., None]
    return np.linalg.norm(c1-c2, axis=-1)

def link_basis(a, b, pin_axis=(1, 0, 0)):
    """Orthonormal (x, y, z) per pose: y along the link, x the pin axis
    projected perpendicular to y, z = x × y. Same rule as the Godot poser."""
    y = b-a; y = y/np.linalg.norm(y, axis=-1, keepdims=True)
    x = np.broadcast_to(np.asarray(pin_axis, float), y.shape)-y*np.einsum('...i,...i', y, np.broadcast_to(pin_axis, y.shape))[..., None]
    x = x/np.linalg.norm(x, axis=-1, keepdims=True)
    return x, y, np.cross(x, y)

def arm_capsules(poses, o1, o2, layers, spec, mount='back'):
    """World capsules per pose for a parallelogram arm. Returns dict name ->
    (P, Q, r) arrays of shape (T,3),(T,3),scalar, plus the adjacency set
    (pairs that legitimately touch at a shared pin). `mount`: the pinion's
    (MOUNTS; pinion_mount chooses it)."""
    root, elbow, wrist = poses['root'], poses['elbow'], poses['wrist']
    o1 = np.asarray(o1, float); o2 = np.asarray(o2, float); X = np.array([1., 0, 0])
    r_bar = max(spec['width'], spec['depth'])/2; r_bar2 = r_bar*.8; outer = layers['outer']
    # The tool: contact point up to the swan neck's apex, then the shank into
    # its socket under the crosshead's lower boss (formlab.linkage.tool_mount).
    tip = poses['tip']; socket = tool_mount(wrist[0]-tip[0], o2)
    neck = shank_path([0, .07, 0], socket, count=25)
    apex = tip+neck[12]; socket_end = tip+socket-[0, .03, 0]
    caps = {
        'upper':  (root, elbow, r_bar),
        'lower':  (elbow, wrist, r_bar),
        'upper2': (root+o1+X*outer, elbow+o1+X*outer, r_bar2),
        'lower2': (elbow+o2-X*outer, wrist+o2-X*outer, r_bar2),
        'elbowhead_web1': (elbow, elbow+o1, spec['web']/2),
        'elbowhead_web2': (elbow, elbow+o2, spec['web']/2),
        'wristhead_web': (wrist, wrist+o2, spec['web']/2),
        'carriage_web': (root, root+o1, spec['web']/2),
        'tool': (tip, apex, .03),
        'shank': (apex, socket_end, .02),
    }
    # The carriage on its guide: bushings along the bars, the cheek plate, the
    # pinion's axle (and bridge); the pinion itself as a stack of chords.
    C = CARRIAGE; bx = X*C['bush_len']/2
    for s, tag in ((-1, '-'), (1, '+')):
        c = root+[0, s*C['bar_dy'], 0]; caps['carriage_bush'+tag] = (c-bx, c+bx, C['bush_r'])
    cx = X*C['cheek_x']; cy = np.array([0., C['cheek_y'], 0])
    caps['carriage_cheek'] = (root+cx-cy, root+cx+cy, C['cheek_z'])
    caps.update(drive_capsules(root, mount))
    carriage = [k for k in caps if k.startswith('carriage_') and k != 'carriage_web']
    pinion = [f'pinion{k}' for k in range(5)]
    adjacent = {frozenset(p) for p in [
        # the carriage's parts meet the links at the shoulder pin; the pinion
        # touches only its axle — a link swinging into the disc is a real hit
        *[(a, b) for a in carriage for b in carriage+pinion+['carriage_web', 'upper', 'upper2'] if a != b],
        *[(a, b) for a in pinion for b in pinion if a != b],
        ('upper', 'lower'), ('upper', 'elbowhead_web1'), ('upper', 'elbowhead_web2'), ('upper', 'carriage_web'),
        ('lower', 'elbowhead_web1'), ('lower', 'elbowhead_web2'), ('lower', 'wristhead_web'), ('lower', 'shank'),
        ('upper2', 'elbowhead_web1'), ('upper2', 'carriage_web'), ('upper2', 'elbowhead_web2'),
        ('lower2', 'elbowhead_web2'), ('lower2', 'wristhead_web'), ('lower2', 'elbowhead_web1'), ('lower2', 'shank'),
        ('elbowhead_web1', 'elbowhead_web2'), ('wristhead_web', 'shank'), ('upper', 'wristhead_web'),
        ('upper2', 'upper'), ('lower2', 'lower'), ('tool', 'shank')]}
    return caps, adjacent

def pairwise_clearance(caps, adjacent=frozenset()):
    """Minimum gap (distance - radii) per non-adjacent pair, over all poses."""
    names = list(caps); out = {}
    for i, a in enumerate(names):
        for b in names[i+1:]:
            if frozenset((a, b)) in adjacent: continue
            P1, Q1, r1 = caps[a]; P2, Q2, r2 = caps[b]
            gap = segment_distance(P1, Q1, P2, Q2)-r1-r2
            k = int(np.argmin(gap)); out[(a, b)] = (float(gap[k]), k)
    return out

def bar_pair_separation(poses, o, which='upper'):
    """In-plane distance between a primary bar and its parallel partner:
    |o| sin(angle(o, link)). Zero means the pair has folded onto itself."""
    a, b = (poses['root'], poses['elbow']) if which == 'upper' else (poses['elbow'], poses['wrist'])
    d = b-a; d /= np.linalg.norm(d, axis=-1, keepdims=True)
    o = np.asarray(o, float)
    perp = o-d*(d@o)[:, None]
    return np.linalg.norm(perp, axis=-1)

def offset_hits(o, centre, r, spec=DEFAULT_SPEC, margin=.004):
    """Would a crosshead's boss at offset `o`, or its web from the pin to `o`,
    come within `margin` of a bar of radius r at `centre` = (y, z) in the
    swing plane? (The carriage's second-bar boss used to pass straight
    through the upper guide bar whenever the offset pointed up.)"""
    o = np.asarray(o, float); c = np.array([0., centre[0], centre[1]])
    if np.linalg.norm(o-c) < spec['boss_r']+r+margin: return True
    t = float(np.clip((c@o)/(o@o), 0, 1))
    return bool(np.linalg.norm(c-t*o) < spec['web']/2+r+margin)

def choose_offset(poses, which, magnitude, candidates=72, half_plane=True, keep_clear=()):
    """Pick the in-plane direction (yz) for the parallel bar's offset that
    maximises the worst-case bar separation over the motion. Returns
    (offset, worst_separation, all candidates). o and -o separate the bars
    identically, so `half_plane` keeps the offset pointing up or level: the
    second bar's pin then never hangs below the wrist, where the tool's
    shank needs its socket (tool_mount). `keep_clear`: [((y, z), r), ...]
    bars in the crosshead's plane its boss and web must not touch
    (rail_keep_clear for the carriage)."""
    best = None; table = []
    for k in range(candidates):
        ang = 2*np.pi*k/candidates
        o = np.array([0, magnitude*np.cos(ang), magnitude*np.sin(ang)])
        if half_plane and o[1] < -1e-12: continue
        if any(offset_hits(o, c, r) for c, r in keep_clear): continue
        worst = float(bar_pair_separation(poses, o, which).min())
        table.append((ang, worst))
        if best is None or worst > best[1]: best = (o, worst)
    return best[0], best[1], table

def report(rig, aid, o1, o2, layers, spec, strings=None, string_r=.002, poses=None, mount='back'):
    poses = rig.poses(aid) if poses is None else poses
    caps, adjacent = arm_capsules(poses, o1, o2, layers, spec, mount)
    gaps = pairwise_clearance(caps, adjacent)
    worst = min(gaps.items(), key=lambda kv: kv[1][0])
    result = dict(arm=aid, samples=len(poses['t']),
                  upper_pair_separation_m=float(bar_pair_separation(poses, o1, 'upper').min()),
                  lower_pair_separation_m=float(bar_pair_separation(poses, o2, 'lower').min()),
                  worst_pair=list(worst[0]), worst_gap_m=worst[1][0], worst_time_s=float(poses['t'][worst[1][1]]),
                  pairs={'/'.join(k): v[0] for k, v in gaps.items()}, caps=caps)
    if strings:
        # Every bar vs every string of the mechanism. The tool legitimately
        # touches the played string, so the wrist head and bars are judged
        # against ALL strings — a bar through the played string is still a
        # bar through a string.
        sg = []
        for sid, s in strings.items():
            A = np.broadcast_to(np.asarray(s['a'], float), poses['root'].shape); B = np.broadcast_to(np.asarray(s['b'], float), poses['root'].shape)
            for name in ('upper', 'upper2', 'lower', 'lower2', 'wristhead_web', 'elbowhead_web1', 'elbowhead_web2', 'shank'):
                P, Q, r = caps[name]
                g = segment_distance(P, Q, A, B)-r-string_r
                k = int(np.argmin(g)); sg.append((float(g[k]), sid, name, float(poses['t'][k])))
        sg.sort(); result['string_gap_m'] = sg[0][0]; result['string_worst'] = sg[0][1:]
    return result

def cross_arm_clearance(reports):
    """Minimum gap between parts of DIFFERENT arms (same time samples), for
    every pair of arms. Arms on one rail share x only when playing the same
    string, but neighbouring rails stack in z and their bars cross in plane."""
    out = {}
    names = list(reports)
    for i, a in enumerate(names):
        for b in names[i+1:]:
            ca = reports[a]['caps']; cb = reports[b]['caps']; best = (1e9, None, 0)
            for na, (P1, Q1, r1) in ca.items():
                for nb, (P2, Q2, r2) in cb.items():
                    g = segment_distance(P1, Q1, P2, Q2)-r1-r2
                    k = int(np.argmin(g))
                    if g[k] < best[0]: best = (float(g[k]), (na, nb), k)
            out[(a, b)] = best
    return out

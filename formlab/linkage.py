"""Articulated-joint and link recipes: knuckle pins, forks, eyes, flat bars,
crossheads and the double-parallelogram arm.

Everything is a closed formlab Mesh in the LINK FRAME: the link runs from
pin A at the origin along +Y to pin B at (0, L, 0); every pin axis is +X, so
the link swings in the YZ plane. Godot places a part by setting its node
basis (x = pin axis, y = link direction, z = x × y) — meshes are built at
true length and never scaled at runtime.

Real-world grammar, kept honest:
- A KNUCKLE JOINT is a fork (two ears) straddling an eye on one pin. The pin
  has a domed head on one side and a washer + nut on the other; both ears
  carry a bronze bushing flange. Three bodies may share one pin (a stack).
- A DOUBLE PARALLELOGRAM (drafting-lamp / Luxo arm) holds every crosshead
  at one fixed orientation: the second bar of each segment runs parallel to
  the first at a constant offset o, so the wrist stays upright without any
  extra actuator. The offset direction is a design choice; the pair collapses
  onto itself when the link runs parallel to o (see formlab.clearance).
- Bars are FLAT with rounded corners, deepest mid-span (a fish-belly), and
  widen into a yoke before the fork so the ears are not pasted on.
"""
import numpy as np
from .sweep import Mesh, sweep, validate_mesh
from .clearance import bezier, SOCKET_DEPTH, tool_mount, shank_path

X, Y, Z = np.eye(3)

def rounded_rect(corner=.35, n=20):
    """Unit rounded rectangle, star-shaped, CCW; corner = fillet fraction."""
    pts = []
    for cx, cy, a0 in ((1, 1, 0), (-1, 1, np.pi/2), (-1, -1, np.pi), (1, -1, 3*np.pi/2)):
        for a in np.linspace(a0, a0+np.pi/2, n//4+1)[:-1] if n >= 8 else [a0]:
            pts.append([cx*(1-corner)+corner*np.cos(a), cy*(1-corner)+corner*np.sin(a)])
    return np.array(pts)

def transform(mesh, R=np.eye(3), t=(0, 0, 0)):
    R = np.asarray(R, float); t = np.asarray(t, float)
    return Mesh(mesh.vertices@R.T+t, mesh.faces.copy(), mesh.uv.copy(), mesh.path@R.T+t,
                mesh.widths.copy(), mesh.depths.copy())

def revolve(profile, axis=X, centre=(0, 0, 0), sides=32):
    """Closed solid of revolution. profile: (r, s) pairs with r >= 0, first and
    last r == 0 (poles); s is the coordinate along the axis. Outward-wound."""
    pr = np.asarray(profile, float)
    if pr[0, 0] != 0 or pr[-1, 0] != 0 or (pr[1:-1, 0] <= 0).any():
        raise ValueError('revolve profile must start and end on the axis with positive radii between')
    axis = np.asarray(axis, float)/np.linalg.norm(axis)
    u = np.cross(axis, Z if abs(axis@Z) < .9 else X); u /= np.linalg.norm(u); v = np.cross(axis, u)
    angle = np.arange(sides)*2*np.pi/sides
    ring = np.cos(angle)[:, None]*u+np.sin(angle)[:, None]*v
    inner = pr[1:-1]
    vertices = [np.asarray(centre, float)+axis*pr[0, 1]]
    for r, s in inner: vertices.extend(np.asarray(centre, float)+axis*s+r*ring)
    vertices.append(np.asarray(centre, float)+axis*pr[-1, 1])
    vertices = np.array(vertices); faces = []
    last = 1+len(inner)*sides
    for k in range(sides): faces.append((0, 1+k, 1+(k+1) % sides))
    for j in range(len(inner)-1):
        for k in range(sides):
            a = 1+j*sides+k; b = 1+j*sides+(k+1) % sides
            faces.extend(((a, a+sides, b), (b, a+sides, b+sides)))
    base = 1+(len(inner)-1)*sides
    for k in range(sides): faces.append((last, base+(k+1) % sides, base+k))
    faces = np.asarray(faces, int)
    signed = np.einsum('ij,ij->i', vertices[faces[:, 0]], np.cross(vertices[faces[:, 1]], vertices[faces[:, 2]])).sum()
    if signed < 0: faces = faces[:, ::-1].copy()
    uv = np.zeros((len(vertices), 2))
    path = np.asarray(centre, float)+axis*np.linspace(pr[0, 1], pr[-1, 1], 3)[:, None]
    return Mesh(vertices, faces, uv, path, np.full(3, pr[:, 0].max()), np.full(3, pr[:, 0].max()))

def ring(centre, r_in, r_out, thickness, axis=X, sides=64, corner=.4):
    """A washer / eye / ear: rounded-rectangular section swept around a circle.
    Closed genus-one mesh — the hole is real, no boolean."""
    if not 0 < r_in < r_out: raise ValueError('ring radii')
    angle = np.linspace(0, 2*np.pi, sides, endpoint=False)
    mid = (r_in+r_out)/2
    path = np.c_[mid*np.cos(angle), mid*np.sin(angle), np.zeros(sides)]   # axis = Z here
    m = sweep(path, (r_out-r_in)/2, thickness/2, closed=True, profile=rounded_rect(corner, 16))
    axis = np.asarray(axis, float)/np.linalg.norm(axis)
    if abs(axis@Z) > .999999:
        R = np.eye(3) if axis@Z > 0 else np.diag([1., -1., -1.])
    else:
        u = np.cross(Z, axis); u /= np.linalg.norm(u); c = axis@Z; s = np.sqrt(1-c*c)
        K = np.array([[0, -u[2], u[1]], [u[2], 0, -u[0]], [-u[1], u[0], 0]])
        R = np.eye(3)+s*K+(1-c)*K@K
    return transform(m, R, centre)

def bar(length, width, depth, taper=.85, belly=.18, yoke=None, sides_profile=None, samples=None):
    """Straight flat bar along +Y. width = thickness across the pin axis (X),
    depth = in-plane (Z). belly deepens mid-span; taper scales the far end.
    yoke=(start_fraction, full_width) widens X into a fork yoke near pin B."""
    count = samples or max(24, int(length/.02))
    u = np.linspace(0, 1, count)
    path = np.c_[np.zeros(count), u*length, np.zeros(count)]
    scale = 1+(taper-1)*u
    d = depth/2*scale*(1+belly*np.sin(np.pi*u))
    w = np.full(count, width/2)*scale
    if yoke is not None:
        start, full = yoke
        blend = np.clip((u-start)/max(1-start, 1e-9), 0, 1); blend = blend*blend*(3-2*blend)
        w = w*(1-blend)+full/2*blend
    return sweep(path, w, d, profile=rounded_rect(.4, 24) if sides_profile is None else sides_profile)

def knuckle_pin(radius, span, head=None, axis=X, centre=(0, 0, 0)):
    """Steel pin along `axis` through a stack of total width `span` (centred),
    domed head on the -axis side, washer + hex-ish nut on the +axis side."""
    h = head or radius*1.9
    hr = radius*1.75
    pr = [(0, -span/2-h), (hr*.55, -span/2-h), (hr*.9, -span/2-h*.55), (hr, -span/2-h*.2), (hr, -span/2),
          (radius, -span/2), (radius, span/2), (hr*1.05, span/2), (hr*1.05, span/2+h*.18),
          (hr*.8, span/2+h*.18), (hr*.8, span/2+h*.85), (radius*.6, span/2+h), (0, span/2+h)]
    return revolve(pr, axis, centre, 24)

def stub_pin(centre, side, layers, spec):
    """A secondary bar's pin, cast with its crosshead: a shouldered stub from
    the crosshead's mid-plane out to the eye's layer (`side` = ±1 along X),
    the pin proper the eye turns on, and a nut past it (layers: outer, span
    from clearance.default_layers)."""
    c = np.asarray(centre, float); r = spec['pin_r']; hr = r*1.75; h = r*1.9
    xs = layers['outer']-spec['width']*.8/2-.002; xe = layers['span']/2
    pr = [(0, 0), (r*1.6, 0), (r*1.6, xs), (r, xs), (r, xe), (hr*1.05, xe), (hr*1.05, xe+h*.18),
          (hr*.8, xe+h*.18), (hr*.8, xe+h*.85), (r*.6, xe+h), (0, xe+h)]
    pts = [(rr, side*x) for rr, x in pr]
    return revolve(pts[::-1] if side < 0 else pts, X, c, 24)

def eye_end(centre, ear_r, pin_r, thickness, axis=X):
    """One ear: a ring with a bushing hole. Returns [ring]."""
    return [ring(centre, pin_r*1.15, ear_r, thickness, axis)]

def fork_end(centre, ear_r, pin_r, thickness, gap, axis=X):
    """Two ears straddling a `gap` (the body between them)."""
    a = np.asarray(axis, float); c = np.asarray(centre, float)
    off = (gap+thickness)/2
    return [ring(c-a*off, pin_r*1.15, ear_r, thickness, axis), ring(c+a*off, pin_r*1.15, ear_r, thickness, axis)]

def link(length, width=.034, depth=.062, ear_r=.055, pin_r=.018, ear_t=.028, fork_gap=None,
         fork_at='B', eye_at='A', layer=0.0, taper=.88, belly=.18):
    """A complete flat link: bar body, a fork at one pin and an eye at the other.
    `layer` shifts the whole link along the pin axis (stacking). Pin A at the
    origin, pin B at (0, length, 0). Returns dict(pieces, pins)."""
    gap = fork_gap if fork_gap is not None else width+.006
    pieces = []
    yoke_w = gap+2*ear_t
    # body stops short of each pin so ears carry the end: an eye end's body
    # runs into its ring; a fork end's stops at the ears' rim, so the
    # crosshead's boss (radius < ear_r) turns between the ears, not in the yoke.
    stop = dict(eye=ear_r*.55, fork=ear_r*.96, none=ear_r*.55)
    y0 = stop['fork' if fork_at == 'A' else 'eye' if eye_at == 'A' else 'none']
    y1 = length-stop['fork' if fork_at == 'B' else 'eye' if eye_at == 'B' else 'none']
    body = bar(y1-y0, width, depth, taper, belly, yoke=(.86, yoke_w) if fork_at == 'B' else None)
    if fork_at == 'A':
        body = bar(y1-y0, width, depth, 1/taper, belly, yoke=(.86, yoke_w))
        body = transform(body, np.diag([1., -1., 1.]), (0, y1, 0))   # mirror so the yoke is at A
    else:
        body = transform(body, np.eye(3), (0, y0, 0))
    pieces.append(body)
    ends = {'A': np.array([0., 0., 0.]), 'B': np.array([0., length, 0.])}
    for key, kind in ((fork_at, 'fork'), (eye_at, 'eye')):
        if key not in ends: continue
        c = ends[key]
        if kind == 'fork': pieces += fork_end(c, ear_r, pin_r, ear_t, gap)
        else: pieces += eye_end(c, ear_r*.92, pin_r, width)
    if layer:
        pieces = [transform(p, np.eye(3), (layer, 0, 0)) for p in pieces]
    return dict(pieces=pieces, pins={'A': ends['A']+[layer, 0, 0], 'B': ends['B']+[layer, 0, 0]},
                fork_gap=gap, ear_t=ear_t, ear_r=ear_r, pin_r=pin_r)

def crosshead(pins, thickness=.012, boss_r=.05, pin_r=.018, web=.05, axis=X, plate=.019, eye=(0,)):
    """The rigid body a parallelogram holds at fixed orientation: two plates
    (each `thickness`, inner faces at X = ±plate) with a boss at every pin
    and a web between neighbouring pins, tied by a solid spacer boss at
    every pin except those in `eye`, where a primary link's eye turns
    between the plates. pins: list of (x=0, y, z) in the crosshead frame."""
    P = np.asarray(pins, float); pieces = []
    for x in (-(plate+thickness/2), plate+thickness/2):
        for p in P: pieces.append(ring(p+[x, 0, 0], pin_r*1.15, boss_r, thickness, axis))
        for a, b in zip(P[:-1], P[1:]):
            d = b-a; L = np.linalg.norm(d)
            if L < 1e-9: continue
            # swept along +Y (profile width across X, the plate's thickness)
            # then turned in the swing plane: sweep() picks its profile
            # frame from the path direction, so a web run straight along Z
            # would come out 50 mm thick along the pin axis.
            count = max(8, int(L/.01))
            u = np.linspace(boss_r*.6*L/L, L-boss_r*.6, count)[:, None]
            path = np.c_[np.zeros(count), u, np.zeros(count)]
            web_mesh = sweep(path, thickness/2*.98, web/2, profile=rounded_rect(.3, 16))
            c, s = d[1]/L, d[2]/L
            pieces.append(transform(web_mesh, np.array([[1., 0, 0], [0, c, -s], [0, s, c]]), a+[x, 0, 0]))
    for i, p in enumerate(P):
        if i in eye: continue
        pieces.append(ring(p, pin_r*1.15, boss_r, 2*plate+.002, axis))
    return pieces

def socket(mount, r=.017, depth=SOCKET_DEPTH, buried=.04):
    """Tapped socket boss hanging under a crosshead boss (radius .05): a
    collar with a chamfered mouth, its tenon buried in the boss above."""
    m = np.asarray(mount, float)
    pr = [(0, -depth-.006), (r*.72, -depth-.006), (r, -depth+.002), (r, -depth+.018),
          (r*.82, -depth+.022), (r*.82, -buried), (0, -buried)]
    return revolve(pr, Y, m, 20)

def swan_shank(start, mount, r0=.010, r1=.012, rise=.05):
    """Round steel shank along shank_path, thickening toward the socket, plus
    the socket itself. Returns [shank, socket]."""
    path = shank_path(start, mount, rise)
    u = np.linspace(0, 1, len(path))
    return [sweep(path, r0+(r1-r0)*u, r0+(r1-r0)*u, sides=16), socket(mount)]

def pick_tool(mount, blade_w=.05, blade_h=.07, blade_t=.007, ferrule_w=.04):
    """Plectrum in a clamped ferrule on a swan-neck shank. Origin at the
    contact point (the plectrum's tip); `mount` is the crosshead boss the
    shank hangs from (tool_mount). Returns [blade, ferrule, screws...] first
    (the contact tool) then [shank, socket]; build_forms splits at index 1."""
    n = 16; u = np.linspace(0, 1, n)
    path = np.c_[np.zeros(n), u*blade_h, np.zeros(n)]
    # tear-drop plectrum: a point at the contact, full shoulders at 80 % height
    half_w = blade_w/2*(.10+.90*np.sin(np.pi/2*np.minimum(u/.8, 1)))*(1-.12*np.clip((u-.8)/.2, 0, 1)**2)
    half_t = blade_t/2*(.35+.65*u)
    # sweep: width lies across X (the pin axis, along the string row), depth
    # along Z (the pluck). The face meets the string; the edge does not.
    blade = sweep(path, half_w, half_t, profile=rounded_rect(.45, 16))
    # ferrule: a block across the plectrum's top, clamped by two set screws
    fy = blade_h*.86; fh = .011; ft = .009
    fpath = np.c_[np.linspace(-ferrule_w/2, ferrule_w/2, 8), np.full(8, fy), np.zeros(8)]
    ferrule = sweep(fpath, fh, ft, profile=rounded_rect(.35, 16))
    screws = []
    for sx in (-ferrule_w*.28, ferrule_w*.28):
        pr = [(0, ft-.001), (.0035, ft-.001), (.0035, ft+.004), (.0025, ft+.0055), (0, ft+.0055)]
        screws.append(revolve(pr, Z, (sx, fy, 0), 12))
    tool = [blade, ferrule]+screws
    return [tool]+[swan_shank((0, fy+fh, 0), mount)]

def mallet_tool(mount, head_r=.06):
    """Felt mallet head on a steel shank to its socket; origin at the head's
    lowest point. Returns [[head], [shank, socket]]. The shank starts inside
    the head, so the felt is threaded on rather than pasted to the rod."""
    pr = [(0, 0)]+[(head_r*np.sin(a), head_r*(1-np.cos(a))) for a in np.linspace(.15, np.pi-.15, 14)]+[(0, 2*head_r)]
    head = revolve(pr, Y, (0, 0, 0), 28)
    return [[head], swan_shank((0, head_r*1.4, 0), mount, .012, .013)]

def carriage_body(o1, spec, mount='back', head=None):
    """The carriage that rides the rail: the shoulder crosshead (pins 0 and
    o1; the upper link's eye turns between its plates at the shoulder), a
    split bushing around each guide bar, a cheek plate on the -X side
    tying the bushings together (the +X side carries the second bar's boss),
    and the pinion's axle: out of the carriage plane for a front/back mount,
    or standing on a bridge back from a bushing for a pinion above or below
    the carriage (formlab.clearance.CARRIAGE / PINION / MOUNTS). One
    casting; pieces overlap. `head`: crosshead() keywords (parallelogram_arm)."""
    from .clearance import CARRIAGE as C, PINION as G, MOUNTS, default_layers
    L = default_layers(spec)
    if head is None:
        head = dict(thickness=spec['head_t'], boss_r=spec['boss_r'], pin_r=spec['pin_r'], web=spec['web'], plate=L['plate'])
    pieces = crosshead([[0, 0, 0], o1], eye=(0,), **head)
    pieces.append(stub_pin(o1, +1, L, spec))
    for s in (-1, 1):
        pieces.append(ring((0, s*C['bar_dy'], 0), C['bar_r']+.002, C['bush_r'], C['bush_len'], X, 48, .3))
    u = np.linspace(0, 1, 3)[:, None]
    a = np.array([C['cheek_x'], -C['cheek_y'], 0.]); b = np.array([C['cheek_x'], C['cheek_y'], 0.])
    pieces.append(sweep(a+(b-a)*u, C['cheek_t']/2, C['cheek_z'], profile=rounded_rect(.35, 16)))
    ny, nz = MOUNTS[mount]; h = G['thickness']/2
    if nz:
        z0, z1 = sorted((.03*nz, (G['out']-h+.02)*nz))
        pieces.append(revolve([(0, z0), (C['axle_r'], z0), (C['axle_r'], z1), (0, z1)], Z, (0, 0, 0), 20))
    else:
        b0, b1 = C['bridge_y']; yc = ny*(b0+b1)/2
        a = np.array([0., yc, 0.]); b = np.array([0., yc, C['bridge_z']])
        pieces.append(sweep(a+(b-a)*u, (b1-b0)/2, C['bridge_x'], profile=rounded_rect(.3, 16)))
        y0, y1 = sorted((ny*(b1-.01), ny*(G['up']-h+.02)))
        pieces.append(revolve([(0, y0), (C['axle_r'], y0), (C['axle_r'], y1), (0, y1)], Y, (0, 0, C['axle_z']), 20))
    return pieces

def parallelogram_arm(l1, l2, o1, o2, spec=None, mount='back'):
    """Double-parallelogram arm parts in their own local frames.

    o1, o2: constant world offsets (in the swing plane, x = 0) of the second
    bar of the upper / lower segment; `mount`: where the pinion sits off the
    carriage (clearance.MOUNTS / pinion_mount). Returns dict name ->
    dict(pieces, pins) with these local frames:
      carriage   at the shoulder pin, fixed orientation (holds pins 0 and o1)
      upper      link frame from shoulder pin to elbow pin      (fork at B)
      upper2     link frame from shoulder+o1 to elbow+o1        (eye both ends)
      elbowhead  at the elbow pin, fixed orientation (pins 0, o1, o2)
      lower      link frame from elbow pin to wrist pin         (fork at B)
      lower2     link frame from elbow+o2 to wrist+o2           (eye both ends)
      wristhead  at the wrist pin, fixed orientation (pins 0, o2)
    Layers along the pin axis (clearance.default_layers): a primary link's eye
    at the centre, between the two plates of the crosshead at the pin it
    hangs from (the carriage at the shoulder, the elbowhead at the elbow);
    its fork at the other end straddles the next crosshead's plates;
    secondary bars ride outside the ears on the +x (upper) / -x (lower)
    faces, so upper and lower bars can cross in plane without touching.
    """
    from .clearance import DEFAULT_SPEC, default_layers
    s = dict(DEFAULT_SPEC)
    if spec: s.update(spec)
    L = default_layers(s); gap = L['gap']; outer = L['outer']; span = L['span']
    head = dict(thickness=s['head_t'], boss_r=s['boss_r'], pin_r=s['pin_r'], web=s['web'], plate=L['plate'])
    upper = link(l1, s['width'], s['depth'], s['ear_r'], s['pin_r'], s['ear_t'], gap, fork_at='B', eye_at='A')
    lower = link(l2, s['width'], s['depth'], s['ear_r'], s['pin_r'], s['ear_t'], gap, fork_at='B', eye_at='A')
    upper2 = link(l1, s['width']*.8, s['depth']*.8, s['ear_r']*.85, s['pin_r'], s['width']*.8, None,
                  fork_at='none', eye_at='A', layer=+outer, taper=1, belly=.1)
    upper2['pieces'] += eye_end(np.array([outer, l1, 0]), s['ear_r']*.78, s['pin_r'], s['width']*.8)
    lower2 = link(l2, s['width']*.8, s['depth']*.8, s['ear_r']*.85, s['pin_r'], s['width']*.8, None,
                  fork_at='none', eye_at='A', layer=-outer, taper=1, belly=.1)
    lower2['pieces'] += eye_end(np.array([-outer, l2, 0]), s['ear_r']*.78, s['pin_r'], s['width']*.8)
    o1 = np.asarray(o1, float); o2 = np.asarray(o2, float)
    # the lower link's eye turns between the elbowhead's plates at the elbow pin
    elbow = crosshead([[0, 0, 0], o1, o2] if np.linalg.norm(o1-o2) > 1e-6 else [[0, 0, 0], o1], eye=(0,), **head)
    # the secondary bars' eyes turn on stub pins cast with the crosshead
    elbow += [stub_pin(o1, +1, L, s), stub_pin(o2, -1, L, s)]
    # the lower link's fork straddles the wristhead: solid at both pins (the
    # tool's socket tenon is buried in the wrist boss)
    wrist = crosshead([[0, 0, 0], o2], eye=(), **head)
    wrist += [stub_pin(o2, -1, L, s)]
    carriage = carriage_body(o1, s, mount, head)
    pins = dict(shoulder=[knuckle_pin(s['pin_r'], L['pin_span'])], elbow=[knuckle_pin(s['pin_r'], L['pin_span'])],
                wrist=[knuckle_pin(s['pin_r'], L['pin_span'])])
    return dict(carriage=dict(pieces=carriage), upper=dict(pieces=upper['pieces']),
                upper2=dict(pieces=upper2['pieces']), elbowhead=dict(pieces=elbow),
                lower=dict(pieces=lower['pieces']), lower2=dict(pieces=lower2['pieces']),
                wristhead=dict(pieces=wrist), **{k: dict(pieces=v) for k, v in pins.items()},
                layers=L, spec=s)

def check_pieces(pieces):
    reports = [validate_mesh(m) for m in pieces]
    bad = [r for r in reports if not r['ok']]
    if bad: raise ValueError(bad)
    return reports

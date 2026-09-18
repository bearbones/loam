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
from .clearance import bezier, SOCKET_DEPTH, tool_mount, shank_path, HAMMER_FORM

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

def bolt_head(centre, axis=(0, 1, 0), r=.011, h=.016):
    """A hex-ish bolt head standing on a face, along `axis` (sunk 6 mm in)."""
    pr = [(0, -.006), (r, -.006), (r, h*.7), (r*.6, h), (0, h)]
    return revolve(pr, axis, centre, 12)

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

FASTENING = dict(washer=.15, nut=(.15, .70), chamfer=.88, cotter=.86, cotter_r=.14, cotter_head=.30)
def fastening(x0, x1, r, axis=X, centre=(0, 0, 0)):
    """What holds a pin on: past the last ear at `x0` along `axis`, a washer, a
    hexagonal nut chamfered top and bottom, and a split pin (cotter) through
    the pin's end between the nut and the tip at `x1` — the pin's own shaft
    runs on to `x1` under them. Nothing reaches past `x1` along the axis or
    past the washer's radius (1.75 r × 1.05) across it, so a pin's room
    (clearance.default_layers, gantry.PIN_X) is what it was with the old
    turned nut. `x1` may lie on either side of `x0` (a -X stub pin)."""
    F = FASTENING; axis = np.asarray(axis, float)/np.linalg.norm(axis); c = np.asarray(centre, float)
    h = x1-x0; hr = r*1.75; p = lambda f: x0+f*h
    washer = revolve([(0, p(0)), (hr*1.05, p(0)), (hr*1.05, p(F['washer'])), (0, p(F['washer']))], axis, c, 24)
    n0, n1 = F['nut']; rc = hr*.98; ch = (n1-n0)*.12
    nut = revolve([(0, p(n0)), (rc*F['chamfer'], p(n0)), (rc, p(n0+ch)), (rc, p(n1-ch)), (rc*F['chamfer'], p(n1)), (0, p(n1))], axis, c, 6)
    pv = np.cross(axis, Z)
    if np.linalg.norm(pv) < .1: pv = np.cross(axis, X)
    pv /= np.linalg.norm(pv); rc = r*F['cotter_r']; lc = hr*.98; hd = r*F['cotter_head']
    cotter = revolve([(0, -lc), (rc, -lc), (rc, lc-hd), (rc*1.9, lc-hd), (rc*1.9, lc), (0, lc)], pv, c+axis*p(F['cotter']), 10)
    return [washer, nut, cotter]

def knuckle_pin(radius, span, head=None, axis=X, centre=(0, 0, 0)):
    """Steel pin along `axis` through a stack of total width `span` (centred),
    domed head on the -axis side; on the +axis side the shaft runs on through
    its washer, hex nut and split pin (`fastening`). Returns [pin, washer, nut,
    cotter]; the pin alone spans head to tip."""
    h = head or radius*1.9
    hr = radius*1.75
    pr = [(0, -span/2-h), (hr*.55, -span/2-h), (hr*.9, -span/2-h*.55), (hr, -span/2-h*.2), (hr, -span/2),
          (radius, -span/2), (radius, span/2+h*.94), (radius*.75, span/2+h), (0, span/2+h)]
    return [revolve(pr, axis, centre, 24)]+fastening(span/2, span/2+h, radius, axis, centre)

def stub_pin(centre, side, layers, spec):
    """A secondary bar's pin, cast with its crosshead: a shouldered stub from
    the crosshead's mid-plane out to the eye's layer (`side` = ±1 along X),
    the pin proper the eye turns on, and its washer, hex nut and split pin
    past it (`fastening`; layers: outer, span from clearance.default_layers).
    Returns [pin, washer, nut, cotter]."""
    c = np.asarray(centre, float); r = spec['pin_r']; h = r*1.9
    xs = layers['outer']-spec['width']*.8/2-.002; xe = layers['span']/2
    pr = [(0, 0), (r*1.6, 0), (r*1.6, xs), (r, xs), (r, xe+h*.94), (r*.75, xe+h), (0, xe+h)]
    pts = [(rr, side*x) for rr, x in pr]
    return [revolve(pts[::-1] if side < 0 else pts, X, c, 24)]+fastening(side*xe, side*(xe+h), r, X, c)

def eye_end(centre, ear_r, pin_r, thickness, axis=X):
    """One ear: a ring with a bushing hole. Returns [ring]."""
    return [ring(centre, pin_r*1.15, ear_r, thickness, axis)]

def fork_end(centre, ear_r, pin_r, thickness, gap, axis=X):
    """Two ears straddling a `gap` (the body between them)."""
    a = np.asarray(axis, float); c = np.asarray(centre, float)
    off = (gap+thickness)/2
    return [ring(c-a*off, pin_r*1.15, ear_r, thickness, axis), ring(c+a*off, pin_r*1.15, ear_r, thickness, axis)]

CUP = dict(base_r=.010, base_h=.004, stem_r=.006, stem_h=.007, r=.010, h=.011, lid=.009, sides=20)
def oil_cup(centre, axis=Y):
    """A lubricator on a bearing: a collar on the rim, a short stem, the cup
    and its domed hinged lid, standing `axis`-wards from `centre` (the rim
    point it is screwed into). Every bearing on a machine of this kind has
    one; here they mark the fork ends, where a rod's oil hole goes."""
    c = CUP; y0 = c['base_h']; y1 = y0+c['stem_h']; y2 = y1+c['h']; top = y2+c['lid']
    pr = [(0, 0), (c['base_r'], 0), (c['base_r'], y0), (c['stem_r'], y0), (c['stem_r'], y1), (c['r'], y1),
          (c['r'], y2), (c['r']*1.05, y2), (c['r']*1.05, y2+.003), (c['r']*.7, top-.002), (0, top)]
    return revolve(pr, axis, centre, c['sides'])

def cup_height():
    c = CUP; return c['base_h']+c['stem_h']+c['h']+c['lid']

def link(length, width=.034, depth=.062, ear_r=.055, pin_r=.018, ear_t=.028, fork_gap=None,
         fork_at='B', eye_at='A', layer=0.0, taper=.88, belly=.18, lubricator=True):
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
    cup = None
    if lubricator and fork_at in ends:
        # the oil cup on the fork's +X ear rim, beyond the pin along the link's
        # line (a rod end's oil hole), in the ear's own layer along the pin
        c = ends[fork_at]; sign = 1. if fork_at == 'B' else -1.
        cup = dict(centre=(c+[(gap+ear_t)/2+layer, sign*ear_r, 0]).tolist(), axis=[0, sign, 0], r=CUP['r']*1.05, h=cup_height())
        pieces.append(oil_cup(np.array(cup['centre'])-[layer, 0, 0], Y*sign))
    if layer:
        pieces = [transform(p, np.eye(3), (layer, 0, 0)) for p in pieces]
    return dict(pieces=pieces, pins={'A': ends['A']+[layer, 0, 0], 'B': ends['B']+[layer, 0, 0]},
                fork_gap=gap, ear_t=ear_t, ear_r=ear_r, pin_r=pin_r, cup=cup)

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

# The clamping collar that holds a tool's shank in its socket. A collar is
# what actually reads as "the tool comes off": a knurled ring you grip and
# one hex-socket set screw pinching the shank. 1.6x the shank radius is the
# usual proportion for a steel clamp collar; 25 mm long is two screw
# diameters, enough metal for the thread. The knurl is 32 shallow ridges,
# modelled as a per-ring sweep profile rather than geometry cut into one.
COLLAR = dict(r_mul=1.6, length=.025, top=.047, ridges=32, ridge=.0006,
              screw_r=.0075, pad=.002, hex_r=.0035, hex_depth=.0028)

def collar(mount, shank_r, spec=COLLAR):
    """The clamp collar around a tool socket and its set screw, as
    [collar, screw]. `mount` is the crosshead boss the socket hangs from
    (clearance.tool_mount); the collar sits on the socket's barrel, below the
    tenon buried in the boss, so it never fouls the crosshead plates."""
    m = np.asarray(mount, float)
    cr = shank_r*spec['r_mul']
    y1 = -spec['top']; y0 = y1-spec['length']
    # A knurl is longitudinal ridges: modulate the swept ring's radius by
    # cos(N*angle). sweep() takes the profile in units of width/depth, so the
    # modulation is relative and the ridge depth stays the declared 0.6 mm.
    a = np.arange(spec['ridges']*6)*2*np.pi/(spec['ridges']*6)
    bump = 1+spec['ridge']/cr*np.cos(spec['ridges']*a)
    profile = np.c_[np.cos(a)*bump, np.sin(a)*bump]
    path = np.c_[np.zeros(5), np.linspace(y0, y1, 5), np.zeros(5)]+m
    ring_mesh = sweep(path, cr, cr, profile=profile)
    # A hex-socket set screw is headless: a short cylinder sitting all but
    # flush in the collar, its hex recess sunk into the exposed face. The
    # recess is part of the screw's own revolve profile (there are no
    # booleans here): the profile steps down into the socket and back to the
    # axis at the recess floor.
    sr = spec['screw_r']; face = cr+spec['pad']; floor = face-spec['hex_depth']
    pr = [(0, cr*.45), (sr, cr*.45), (sr, face), (spec['hex_r']*1.3, face),
          (spec['hex_r'], floor), (0, floor)]
    screw = revolve(pr, X, m+[0, (y0+y1)/2, 0], 12)
    return [ring_mesh, screw]

def socket(mount, r=.017, depth=SOCKET_DEPTH, buried=.04, shank_r=.012):
    """Tapped socket boss hanging under a crosshead boss (radius .05): a
    barrel with a chamfered mouth, its tenon buried in the boss above, plus
    the clamp collar and set screw that hold the shank in it. Returns
    [boss, collar, screw]."""
    m = np.asarray(mount, float)
    pr = [(0, -depth-.006), (r*.72, -depth-.006), (r, -depth+.002), (r, -depth+.018),
          (r*.82, -depth+.022), (r*.82, -buried), (0, -buried)]
    return [revolve(pr, Y, m, 20)]+collar(mount, shank_r)

def swan_shank(start, mount, r0=.010, r1=.012, rise=.05):
    """Round steel shank along shank_path, thickening toward the socket, plus
    the socket, its clamp collar and the set screw. Returns
    [shank, boss, collar, screw]."""
    path = shank_path(start, mount, rise)
    u = np.linspace(0, 1, len(path))
    return [sweep(path, r0+(r1-r0)*u, r0+(r1-r0)*u, sides=16)]+socket(mount, shank_r=r1)

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
        # The driver slot. Nothing here is a boolean, so the slot is a thin bar
        # standing 0.15 mm through the dome rather than a groove cut into it:
        # the two creases where it meets the crown are what read as the slot.
        slot = np.c_[np.linspace(-.0037, .0037, 5), np.full(5, fy), np.full(5, ft+.0045)]
        screws.append(sweep(slot+[sx, 0, 0], .0009, .0011, profile=rounded_rect(.3, 12)))
    # The ferrule's shim slot: a plectrum is squared up by driving a brass shim
    # in beside it, and the slot is the gap under this lip across the ferrule's
    # face. A raised lip, again, not a cut.
    shim = np.c_[np.linspace(-ferrule_w*.42, ferrule_w*.42, 5), np.full(5, fy-fh*.42), np.full(5, ft+.0008)]
    tool = [blade, ferrule]+screws+[sweep(shim, .0013, .0015, profile=rounded_rect(.35, 12))]
    return [tool]+[swan_shank((0, fy+fh, 0), mount)]

# A mallet is not a blob: it is a core with yarn wound over it, the spiral
# visible in raking light, tied off at the top. 2 mm yarn and 14 turns across
# the head is a real winding for a 120 mm head; the wrap centre-line runs
# 0.6 of a yarn radius inside the core's surface, so the yarn stands 0.8 mm
# proud and the core still owns the lowest point — the contact stays exactly
# at the origin. The wrap stops short of the bottom pole (WRAP['pole']) so no
# yarn ever dips below the contact.
WRAP = dict(r=.002, turns=14, pole=.35, per_turn=18, sides=8, knot_r=.006, knot_t=.0022)

def _wound_head(head_r, spec=WRAP):
    """The mallet's core, the yarn wound over it and the knot it ties off in,
    as [core, wrap, knot]. The core is a sphere of radius head_r seated on the
    origin (centre at (0, head_r, 0))."""
    pr = [(0, 0)]+[(head_r*np.sin(a), head_r*(1-np.cos(a))) for a in np.linspace(.15, np.pi-.15, 14)]+[(0, 2*head_r)]
    core = revolve(pr, Y, (0, 0, 0), 28)
    count = int(spec['turns']*spec['per_turn'])
    polar = np.linspace(spec['pole'], np.pi-spec['pole'], count)
    phi = np.linspace(0, 2*np.pi*spec['turns'], count)
    R = head_r-spec['r']*.6
    path = np.c_[R*np.sin(polar)*np.cos(phi), head_r-R*np.cos(polar), R*np.sin(polar)*np.sin(phi)]
    wrap = sweep(path, spec['r'], spec['r'], sides=spec['sides'])
    # The knot: a small torus lying on the core where the last turn is tied
    # off, in the plane tangent to the core there.
    end = path[-1]; n = (end-[0, head_r, 0]); n = n/np.linalg.norm(n)
    u = np.cross(n, Y); u = u/np.linalg.norm(u) if np.linalg.norm(u) > 1e-9 else X
    v = np.cross(n, u)
    ang = np.arange(28)*2*np.pi/28
    ring = end+np.outer(np.cos(ang), u*spec['knot_r'])+np.outer(np.sin(ang), v*spec['knot_r'])
    knot = sweep(ring, spec['knot_t'], spec['knot_t'], sides=10, closed=True)
    return [core, wrap, knot]

# A HINGED HAMMER (formlab.rig.HAMMER, docs/plans/hinged-hammer.md): the arm
# positions and dips a little; a head on a pin at the shank's end flips, strikes
# and is caught on the rebound by a felt-faced check, so the sharpest motion in
# the piece happens in 120 mm of hinged metal rather than in a metre of arm.
# Three parts, because one of them moves on its own: the FORK, pin, check and
# return spring ride the tool frame (origin at the contact point, as every tool
# does); the HEAD is its own local part whose origin is the hinge, so the poser
# turns it by the flip angle and nothing is ever scaled.
# The spec is in clearance (it is what the capsules are measured from).

def hammer_head(head_l, head_r, spec=HAMMER_FORM):
    """The moving head in its own frame: the hinge at the origin, the felt face
    at (0, -head_l, 0) and the tail up at +y, built at flip angle zero — the
    instant of the blow. Returns (pieces, materials)."""
    s = spec; core_top = -head_l+head_r*1.4
    # one tapered rod from the tail, through the eye boss, into the head
    rod = sweep(np.c_[np.zeros(9), np.linspace(s['tail'], core_top, 9), np.zeros(9)],
                np.linspace(s['rod_r']*.8, s['rod_r'], 9), np.linspace(s['rod_r']*.8, s['rod_r'], 9), sides=16)
    # the eye the hinge pin turns in, a bushed boss across the flange's gap
    # the eye butts the flange's bosses with a running fit, not into them
    hx = s['cheek_x']-s['cheek_t']-.006-.0005
    eye = ring((0, 0, 0), s['pin_r']*1.1, s['ear_r']*.65, 2*hx, X, 40)
    # the tail's end is a flat pad: what actually meets the check's felt
    button = revolve([(0, s['tail']-.004), (s['rod_r']*1.6, s['tail']-.004),
                      (s['rod_r']*1.6, s['tail']), (0, s['tail'])], Y, (0, 0, 0), 20)
    head = [transform(m, np.eye(3), (0, -head_l, 0)) for m in _wound_head(head_r)]
    return [rod, eye, button]+head, ['steel', 'bronze', 'steel', 'felt', 'felt', 'felt']

def hammer_tool(mount, rest_angle, sign, head_l=None, head_r=None, spec=HAMMER_FORM):
    """A hinged hammer: ([fixed, shank, head], fixed materials, head materials).
    `mount` is the crosshead boss (clearance.tool_mount); `rest_angle` and
    `sign` are where the head lies back (rig.rest_angle / rig.flip_sign), which
    is what places the check. The fixed part's origin is the contact point; the
    head's is the hinge.

    The flange STRADDLES the head: the head's rod and its tail sweep the whole
    plane of the arc (the tail 48 mm one way, the felt 120 mm the other), so
    there is nowhere in that plane for a bracket to stand. Two cheek plates
    outboard of the felt head's own radius carry the hinge on inward bosses, the
    pin runs right through them, and the swan neck rises off the bridge above —
    which is how a piano hammer flange is built, for the same reason."""
    # both imported here, not at module scope: formlab.gantry imports this
    # module, and formlab.rig is the motion mirror rather than a geometry module.
    from .rig import HAMMER
    from .gantry import prism
    s = spec
    head_l = HAMMER['head_l'] if head_l is None else head_l
    head_r = HAMMER['head_r'] if head_r is None else head_r
    hy = head_l; cx = s['cheek_x']; top = hy+s['post']
    fixed = []
    for side in (-1, 1):
        fixed.append(prism([side*cx, hy-s['ear_r']*1.1, 0], [side*cx, top, 0], s['cheek_t'], s['cheek_z'], .3, 6))
        # the bearing boss reaching in from the cheek to the head's eye
        bx = cx-s['cheek_t']-.006
        fixed.append(ring((side*(cx+bx)/2, hy, 0), s['pin_r']*1.1, s['boss_r'], cx-bx, X, 32))
    fixed.append(prism([-cx, top, 0], [cx, top, 0], s['cheek_z'], s['cheek_z'], .3, 6))
    # the pin runs right through both cheeks, its domed head and its nut proud
    fixed += knuckle_pin(s['pin_r'], 2*(cx+s['cheek_t']+.004), axis=X, centre=(0, hy, 0))
    # The check: a felt-faced stop out where the tail lies at rest. The head's
    # frame turns by -rest_angle*sign about +X (rig.head_offset is the same
    # rotation seen from the felt face), so its tail points here. HAMMER['cock']
    # is small because THIS is what the cock presses into: the tail sinks a
    # couple of millimetres into the felt before the head flies.
    phi = -rest_angle*sign; c, sn = np.cos(phi), np.sin(phi)
    tail_dir = np.array([0., c, sn]); seat = np.array([0., hy, 0.])+tail_dir*(s['tail']+s['felt']/2)
    # ...and it is a BAR between the cheeks, not a stalk down the middle: the
    # tail sweeps the whole plane of the arc, so anything standing in that plane
    # is in the way (a 0.4 mm miss, measured, before this was a bar).
    bar = seat+tail_dir*(s['check_r']+s['felt']/2)
    fixed.append(prism(bar-[cx, 0, 0], bar+[cx, 0, 0], s['check_r'], s['check_r'], .4, 5))
    fixed.append(revolve([(0, -s['felt']/2), (s['check_r']*1.4, -s['felt']/2), (s['check_r']*1.5, 0),
                          (s['check_r']*1.4, s['felt']/2), (0, s['felt']/2)], tail_dir, seat, 20))
    # the return spring: a torsion coil about the hinge pin OUTBOARD of a cheek,
    # where the head's own radius cannot sweep it, with a tail up the cheek
    x0 = cx+s['cheek_t']+.002
    n = int(s['turns']*24)+1; u = np.linspace(0, 1, n); ang = 2*np.pi*s['turns']*u
    fixed.append(sweep(np.c_[x0+s['coil_len']*u, hy+s['coil_r']*np.cos(ang), s['coil_r']*np.sin(ang)],
                       s['wire_r'], s['wire_r'], profile=rounded_rect(1, 12)))
    fixed.append(sweep([[x0, hy+s['coil_r'], 0], [x0*.98, hy+s['coil_r']*1.6, 0], [cx, top-.004, 0]],
                       s['wire_r'], s['wire_r'], profile=rounded_rect(1, 12)))
    mats = ['steel', 'bronze']*2+['steel']+['steel', 'brass', 'brass', 'steel']+['steel', 'felt', 'brass', 'brass']
    head, head_mats = hammer_head(head_l, head_r, s)
    return [fixed, swan_shank((0, top+s['cheek_z'], 0), mount, .010, .012), head], mats, head_mats

def mallet_tool(mount, head_r=.06):
    """Wound felt mallet head on a steel shank to its socket; origin at the
    head's lowest point. Returns [[core, wrap, knot], [shank, boss, collar,
    screw]]. The shank starts inside the head, so the felt is threaded on
    rather than pasted to the rod."""
    return [_wound_head(head_r), swan_shank((0, head_r*1.4, 0), mount, .012, .013)]

def bar_bush(centre, C):
    """A guide-bar bushing as a linear guide has it: the housing round the bar
    (bore 2 mm over it, C['bush_body_r']), a flanged bush standing proud of
    it at either end (C['bush_r'], C['flange_t']) and four bolts through each
    flange on C['bolt_circle'] — the rail heads' shaft supports (gantry.BUSH)
    again, on the carriage. Every piece stays inside the capsule
    clearance.arm_capsules reserves for the bushing (bush_len long, bush_r
    round, hemispherical ends): a bolt bolt_h tall at bolt_circle sits under
    the end's dome, so the clearance model is unchanged."""
    cx, cy, cz = (float(v) for v in centre); L = C['bush_len']; ft = C['flange_t']; bore = C['bar_r']+.002
    out = [ring((cx, cy, cz), bore, C['bush_body_r'], L-2*ft, X, 48, .3)]
    for s in (-1, 1):
        out.append(ring((cx+s*(L-ft)/2, cy, cz), bore, C['bush_r'], ft, X, 48, .3))
        for k in range(4):
            a = np.pi/4+k*np.pi/2
            out.append(bolt_head((cx+s*L/2, cy+C['bolt_circle']*np.cos(a), cz+C['bolt_circle']*np.sin(a)), axis=(s, 0, 0), r=C['bolt_r'], h=C['bolt_h']))
    return out

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
    pieces += stub_pin(o1, +1, L, spec)
    for s in (-1, 1):
        pieces += bar_bush((0, s*C['bar_dy'], 0), C)
    u = np.linspace(0, 1, 3)[:, None]
    a = np.array([C['cheek_x'], -C['cheek_y'], 0.]); b = np.array([C['cheek_x'], C['cheek_y'], 0.])
    pieces.append(sweep(a+(b-a)*u, C['cheek_t']/2, C['cheek_z'], profile=rounded_rect(.35, 16)))
    ny, nz = MOUNTS[mount]; h = G['thickness']/2
    # The axle runs on through the disc and the hub boss on its outer face
    # (build_clockwork.gear casts the boss with the disc) to the washer, hex
    # nut and split pin that retain the pinion — `fastening`, as on every
    # pin of the arm — over PINION['retain'] past the boss.
    tip = (G['out'] if nz else G['up'])+h+G['boss_h']; end = tip+G['retain']
    if nz:
        z0, z1 = sorted((.03*nz, end*nz))
        pieces.append(revolve([(0, z0), (C['axle_r'], z0), (C['axle_r'], z1), (0, z1)], Z, (0, 0, 0), 20))
        pieces += fastening(tip, end, C['axle_r'], (0, 0, nz), (0, 0, 0))
    else:
        b0, b1 = C['bridge_y']; yc = ny*(b0+b1)/2
        a = np.array([0., yc, 0.]); b = np.array([0., yc, C['bridge_z']])
        pieces.append(sweep(a+(b-a)*u, (b1-b0)/2, C['bridge_x'], profile=rounded_rect(.3, 16)))
        y0, y1 = sorted((ny*(b1-.01), ny*end))
        pieces.append(revolve([(0, y0), (C['axle_r'], y0), (C['axle_r'], y1), (0, y1)], Y, (0, 0, C['axle_z']), 20))
        pieces += fastening(tip, end, C['axle_r'], (0, ny, 0), (0, 0, C['axle_z']))
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
    # no cup on the lower link's fork: it works at the wrist, where a rake's
    # sweep would carry a cup beyond the pin to within millimetres of the strings
    lower = link(l2, s['width'], s['depth'], s['ear_r'], s['pin_r'], s['ear_t'], gap, fork_at='B', eye_at='A', lubricator=False)
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
    elbow += stub_pin(o1, +1, L, s)+stub_pin(o2, -1, L, s)
    # the lower link's fork straddles the wristhead: solid at both pins (the
    # tool's socket tenon is buried in the wrist boss)
    wrist = crosshead([[0, 0, 0], o2], eye=(), **head)
    wrist += stub_pin(o2, -1, L, s)
    carriage = carriage_body(o1, s, mount, head)
    pins = dict(shoulder=knuckle_pin(s['pin_r'], L['pin_span']), elbow=knuckle_pin(s['pin_r'], L['pin_span']),
                wrist=knuckle_pin(s['pin_r'], L['pin_span']))
    return dict(carriage=dict(pieces=carriage), upper=dict(pieces=upper['pieces'], cup=upper['cup']),
                upper2=dict(pieces=upper2['pieces']), elbowhead=dict(pieces=elbow),
                lower=dict(pieces=lower['pieces'], cup=lower['cup']), lower2=dict(pieces=lower2['pieces']),
                wristhead=dict(pieces=wrist), **{k: dict(pieces=v) for k, v in pins.items()},
                layers=L, spec=s)

def check_pieces(pieces):
    reports = [validate_mesh(m) for m in pieces]
    bad = [r for r in reports if not r['ok']]
    if bad: raise ValueError(bad)
    return reports

"""A sprung detent pawl on the mallet arms' pinions: the mechanism the ratchet
click (docs/motion-design.md) is read from.

The pinion (tools/build_clockwork.gear, formlab.clearance.PINION) is a brass
disc with sixteen box teeth; the rack meshes with it above (formlab.gantry.rack).
Under the disc a steel pawl rides the teeth: a lever pivoted on a pin at a
bracket cast onto the carriage's lower bushing, reaching under the disc to a
yoke whose two tongues carry a roller, held up against the teeth by a torsion
spring on the pivot pin. It is a roller detent (an index pawl), not a one-way
pawl — the carriage travels both ways — so the nose is symmetric. The roller
is wider than the gap between two tips' bevels, so it rides the tips and dips
between each pair (9.5 mm, on 50° ramps — the bevels' arcs), one dip a tooth:
a click a tooth, the motion's ratchet made visible. A ball small enough to
enter a gap would wedge against the box teeth's radial flanks (the wheel turns
both ways and the pawl moves only on its arc), so the roller stays outside. Everything is carriage-local (the carriage's frame is world-oriented,
origin at the shoulder pin); the pawl's own frame has its origin at the pivot.

`angle(x)` — the pawl's rest angle for a carriage at rail position x — is the
one piece of kinematics: the largest angle (nose toward the disc's centre) at
which the roller is still clear of the teeth, found by bisection on the
exact distance to the toothed disc (`tooth_distance`). ClockworkMotion.pawl_angle
mirrors it and tools/test_pawl.py holds the two together.

Only a front or back mount carries a pawl (every mallet arm's pinion is behind
its carriage); an up/down disc lies flat over the rail and has no free rim.
"""
import numpy as np
from .clearance import PINION, MOUNTS, CARRIAGE, pinion_centre
from .linkage import ring, revolve, knuckle_pin, rounded_rect, Y, Z
from .sweep import sweep
from .gantry import prism

# lever: pivot to the yoke along -X; drop: the roller's rest radius past the
# tips (its radius and 5 mm of lift); finger: the roller's axle stands this far
# above the lever; nose_r: the roller; width: the eye and lever across the pin;
# the rest is the roller's axle, the pin, its ear and the spring.
PAWL = dict(lever=.10, drop=.02, finger=.03, nose_r=.015, roller_len=.03, axle_r=.004, width=.03, pivot_r=.011, ear_t=.014,
            coil_r=.019, wire_r=.0025, coil_turns=4.5, coil_len=.026, post_r=.004)
# One box tooth of build_clockwork.gear(r=.13): box (r*.28 radial, r*.22 across,
# .07 thick) centred at .86 r, edges bevelled .008; tips at multiples of 2π/16
# from +x in the disc's home frame (dev/test_performance.gd pins the spin).
TOOTH = dict(centre=PINION['r_tip']*.86, half_r=PINION['r_tip']*.14, half_t=PINION['r_tip']*.11, bevel=.008)
TEETH = PINION['teeth']

def pivot(mount):
    """Pivot pin, carriage-local: `lever` along +X from under the disc's centre,
    the nose's rest radius plus the finger below it, in the disc's plane."""
    if not MOUNTS[mount][1]: raise ValueError('a pawl needs a front or back pinion (an up/down disc has no free rim)')
    return pinion_centre(mount)+np.array([PAWL['lever'], -(PINION['r_tip']+PAWL['drop']+PAWL['finger']), 0.])

def nose_rest():
    """The roller's centre in the pawl's frame (origin at the pivot), at angle 0."""
    return np.array([-PAWL['lever'], PAWL['finger'], 0.])

def nose_at(alpha):
    """The nose in the pawl's frame at angle `alpha` (positive: toward the
    disc's centre — the lever turns clockwise about +Z seen from +Z, which
    lifts its -X end). Vectorised over alpha; (..., 3)."""
    a = np.asarray(alpha, float); c = np.cos(a); s = np.sin(a); n = nose_rest()
    # Rot(-alpha): (x, y) -> (x cos + y sin, -x sin + y cos)
    return np.stack([n[0]*c+n[1]*s, -n[0]*s+n[1]*c, np.zeros_like(a)], axis=-1)

def tooth_distance(qx, qy, x):
    """Signed distance from a point (qx, qy) — in the disc's plane relative
    to its centre, carriage-local — to the toothed disc as it stands for a
    carriage at rail position x (spun x / r_pitch about +Z). The hub and the
    three nearest bevelled box teeth; vectorised."""
    qx = np.asarray(qx, float); qy = np.asarray(qy, float); x = np.asarray(x, float)
    th = x/PINION['r_pitch']; c = np.cos(th); s = np.sin(th)
    hx = qx*c+qy*s; hy = -qx*s+qy*c                      # the disc's home frame
    d = np.hypot(hx, hy)-PINION['r_hub']
    step = 2*np.pi/TEETH; i = np.round(np.arctan2(hy, hx)/step)
    T = TOOTH; hr = T['half_r']-T['bevel']; ht = T['half_t']-T['bevel']
    for k in (-1, 0, 1):
        phi = (i+k)*step; cp = np.cos(phi); sp = np.sin(phi)
        u = hx*cp+hy*sp-T['centre']; v = -hx*sp+hy*cp        # the tooth's frame
        ex = np.maximum(np.abs(u)-hr, 0); ey = np.maximum(np.abs(v)-ht, 0)
        d = np.minimum(d, np.hypot(ex, ey)-T['bevel'])
    return d

ANGLE_LO, ANGLE_HI, ANGLE_ITERS = -.15, .45, 48

def angle(x):
    """The pawl's angle for a carriage at rail position x: the largest angle
    at which the nose is clear of the teeth (the spring lifts it until it
    touches). Bisection; vectorised over x; mirrored by ClockworkMotion.pawl_angle."""
    x = np.asarray(x, float)
    P = np.array([PAWL['lever'], -(PINION['r_tip']+PAWL['drop']+PAWL['finger'])])   # the pivot from the disc's centre
    lo = np.full(x.shape, ANGLE_LO); hi = np.full(x.shape, ANGLE_HI)
    for _ in range(ANGLE_ITERS):
        mid = (lo+hi)/2; n = nose_at(mid)
        clear = tooth_distance(P[0]+n[..., 0], P[1]+n[..., 1], x) >= PAWL['nose_r']
        lo = np.where(clear, mid, lo); hi = np.where(clear, hi, mid)
    return lo

def nose_radius(x):
    """Distance from the disc's centre to the nose for a carriage at x."""
    P = np.array([PAWL['lever'], -(PINION['r_tip']+PAWL['drop']+PAWL['finger'])]); n = nose_at(angle(x))
    return np.hypot(P[0]+n[..., 0], P[1]+n[..., 1])

def _side(mount):
    """+1 when the carriage lies at +Z of the disc (a back mount), else -1:
    the pin's ear, the spring and the bracket stack toward the carriage."""
    return -MOUNTS[mount][1]

def lever_pieces(mount='back'):
    """The moving pawl in its own frame (origin at the pivot, world-oriented,
    angle 0): the eye on the pin, the lever, the yoke, its tongues, the
    roller on its axle, and the torsion spring around the pin with a tail bearing under the lever and
    a tail against the bracket's post. Returns (pieces, materials)."""
    P = PAWL; s = _side(mount); w = P['width']; L = P['lever']; F = P['finger']; R = P['nose_r']; hl = P['roller_len']/2
    eye = ring((0, 0, 0), P['pivot_r']+.0015, .026, w, Z, 48, .4)
    u = np.linspace(0, 1, 9)[:, None]; a = np.array([-.012, 0, 0]); b = np.array([-L+.012, 0, 0])
    lever = sweep(a+(b-a)*u, np.linspace(.013, .0115, 9), .011, profile=rounded_rect(.4, 16))
    # the lever's end widens into a yoke; two tongues rise from it to carry the
    # roller's axle, the roller between them
    yoke = prism([-L+.016, 0, 0], [-L-.010, 0, 0], .012, hl+.005, .3, 5)
    tongues = [prism([-L, -.004, s_*(hl+.0025)], [-L, F+.004, s_*(hl+.0025)], .010, .0025, .5, 5) for s_ in (-1, 1)]
    axle = revolve([(0, -hl-.008), (P['axle_r']*.7, -hl-.008), (P['axle_r'], -hl-.006), (P['axle_r'], hl+.006), (P['axle_r']*.7, hl+.008), (0, hl+.008)], Z, (-L, F, 0), 16)
    roller = revolve([(0, -hl), (R-.002, -hl), (R, -hl+.002), (R, hl-.002), (R-.002, hl), (0, hl)], Z, (-L, F, 0), 40)
    # the spring: coil_turns about the pin from the eye's face toward the ear,
    # starting at +X (its fixed tail) and ending at -X (its moving tail)
    z0 = s*(w/2+.002); z1 = z0+s*P['coil_len']; n = int(P['coil_turns']*24)+1
    t = np.linspace(0, 1, n); ang = 2*np.pi*P['coil_turns']*t
    coil = sweep(np.c_[P['coil_r']*np.cos(ang), P['coil_r']*np.sin(ang), z0+(z1-z0)*t], P['wire_r'], P['wire_r'], profile=rounded_rect(1, 12))
    fixed = sweep([[P['coil_r'], -.002, z0], [P['coil_r'], .014, z0], [P['coil_r'], .03, z0]], P['wire_r'], P['wire_r'], profile=rounded_rect(1, 12))
    under = -.012-P['wire_r']
    moving = sweep([[-P['coil_r']+.002, 0, z1], [-.045, -.009, (z1+0)/2], [-.052, under, 0]], P['wire_r'], P['wire_r'], profile=rounded_rect(1, 12))
    pieces = [eye, lever, yoke, *tongues, axle, roller, coil, fixed, moving]
    return pieces, ['steel']*7+['brass']*3

def post_centre(mount='back'):
    """The bracket's spring post, pawl-frame (x, y): the fixed tail bears on it."""
    return np.array([PAWL['coil_r']+PAWL['wire_r']+PAWL['post_r'], .028])

def ear_offset(mount='back'):
    """The ear's centre along Z from the pivot (toward the carriage)."""
    return _side(mount)*(PAWL['width']/2+.002+PAWL['coil_len']+.002+PAWL['ear_t']/2)

def bracket_pieces(mount='back'):
    """The fixed hardware, carriage-local, to be cast onto the carriage: the
    pin's ear, an arm from the ear to the carriage plane, a strut into the
    lower bushing's wall, the spring post, and the knuckle pin with its
    washer, nut and split pin (head on the carriage side)."""
    P = PAWL; s = _side(mount); C = CARRIAGE; pv = pivot(mount); ze = ear_offset(mount)
    ear = ring(pv+[0, 0, ze], P['pivot_r']+.0015, .028, P['ear_t'], Z, 48, .4)
    knee = pv+[0, 0, -pv[2]-s*.045]                       # on the carriage's plane side, .045 short of it
    arm = prism(pv+[0, 0, ze], knee, .012, .014, .3, 5)
    strut = prism(knee, [.075, -C['bar_dy']-.05, 0], .012, .012, .3, 5)
    px, py = post_centre(mount); z_post = sorted((pv[2]+ze, pv[2]+s*P['width']/2))
    post = revolve([(0, z_post[0]), (P['post_r'], z_post[0]), (P['post_r'], z_post[1]), (0, z_post[1])], Z, (pv[0]+px, pv[1]+py, 0), 16)
    span = abs(ze)+P['ear_t']/2+P['width']/2
    centre = pv+[0, 0, (ze+s*P['ear_t']/2-s*P['width']/2)/2]
    pin = knuckle_pin(P['pivot_r'], span, axis=(0, 0, -s), centre=centre)
    return [ear, arm, strut, post]+pin

def manifest(mount='back'):
    """What the model manifest records for an arm's pawl (performance.gd poses
    the part at root + pivot, turned by pawl_angle about Z)."""
    return dict(mount=mount, pivot=pivot(mount).round(6).tolist(), nose=nose_rest().round(6).tolist(),
                lever=PAWL['lever'], finger=PAWL['finger'], nose_r=PAWL['nose_r'], drop=PAWL['drop'])

def capsules(root, mount='back'):
    """World capsules per pose for the rulers, name -> (P, Q, r): the lever,
    yoke, tongues and roller (turned by angle(x)); the eye, spring, ear, pin, post, arm
    and strut. `root`: (T, 3) shoulder-pin positions."""
    root = np.asarray(root, float); P = PAWL; s = _side(mount); pv = pivot(mount); ze = ear_offset(mount)
    al = angle(root[:, 0]); c = np.cos(al)[:, None]; sn = np.sin(al)[:, None]
    def turn(p):                                          # pawl-frame point -> world, per pose
        p = np.asarray(p, float); q = np.stack([p[0]*c[:, 0]+p[1]*sn[:, 0], -p[0]*sn[:, 0]+p[1]*c[:, 0], np.full(len(al), p[2])], axis=-1)
        return root+pv+q
    L = P['lever']; F = P['finger']; hl = P['roller_len']/2; caps = {
        'pawl_lever': (turn([-.012, 0, 0]), turn([-L+.012, 0, 0]), .0135),
        'pawl_yoke': (turn([-L+.016, 0, 0]), turn([-L-.010, 0, 0]), hl+.005),
        # the tongues' plates lie inside the roller's silhouette where the teeth are; a
        # capsule along each one's centre line stands for it
        'pawl_tongue-': (turn([-L, -.004, -hl-.0025]), turn([-L, F+.004, -hl-.0025]), .003),
        'pawl_tongue+': (turn([-L, -.004, hl+.0025]), turn([-L, F+.004, hl+.0025]), .003),
        'pawl_roller': (turn([-L, F, -hl-.008]), turn([-L, F, hl+.008]), P['nose_r']),
        'pawl_eye': (root+pv+[0, 0, -P['width']/2], root+pv+[0, 0, P['width']/2], .026),
        'pawl_spring': (root+pv+[0, 0, s*(P['width']/2)], root+pv+[0, 0, s*(P['width']/2+.004+P['coil_len'])], P['coil_r']+P['wire_r']),
        'pawl_ear': (root+pv+[0, 0, ze-s*P['ear_t']/2], root+pv+[0, 0, ze+s*P['ear_t']/2], .028),
        'pawl_pin': (root+pv+[0, 0, -s*(P['width']/2+P['pivot_r']*1.9)], root+pv+[0, 0, ze+s*(P['ear_t']/2+P['pivot_r']*1.9)], P['pivot_r']*1.75*1.05),
        'pawl_arm': (root+pv+[0, 0, ze], root+pv+[0, 0, -pv[2]-s*.045], .0185),
        'pawl_strut': (root+pv+[0, 0, -pv[2]-s*.045], root+[.075, -CARRIAGE['bar_dy']-.05, 0], .017),
    }
    # the moving tail reaches under the lever from the coil
    caps['pawl_tail'] = (turn([-P['coil_r'], 0, s*(P['width']/2+.002+P['coil_len'])]), turn([-.052, -.0145, 0]), P['wire_r'])
    return caps

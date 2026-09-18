"""A sprung detent pawl on the mallet arms' pinions: the mechanism the ratchet
click (docs/motion-design.md) is read from.

The pinion (tools/build_clockwork.gear, formlab.clearance.PINION) is a brass
disc with sixteen involute teeth (formlab.gear); the rack meshes with it above
(formlab.gantry.rack). Under the disc a steel pawl rides the teeth: a lever
pivoted on a pin at a bracket cast onto the carriage's lower bushing, reaching
under the disc to a yoke whose two tongues carry a roller, held up against the
teeth by a torsion spring on the pivot pin. It is a roller detent (an index
pawl), not a one-way pawl — the carriage travels both ways — so the nose is
symmetric. The roller is wider than the gap between two tips' corners, so it
rides the tip lands and dips between each pair (14.6 mm, on the corners and
the top of the flanks), one dip a tooth: a click a tooth, the motion's ratchet
made visible. It must not sink below the tip circle: a roller whose centre is
inside it is met by the next tooth's corner *below* its own centre, and since
the pawl can only move on its arc the corner drives it deeper and wedges it
between the flanks (a 15 mm roller did, once the tip lands narrowed from the
old box teeth's 29 mm to the involute's 13 mm). The lever also leans down
toward its pivot (`PAWL['tilt']`): with the lever level, the roller's arc ran
17° off radial and an approaching corner lifted it on a near-flat wedge — a
snap of 1.7° per 0.1 mm of rail; leaning, the arc is radial where the roller
meets the corners and the lift is smooth. Everything is carriage-local (the
carriage's frame is world-oriented, origin at the shoulder pin); the pawl's
own frame has its origin at the pivot, and its angle is the whole turn of that
frame about +Z, lean included.

`angle(x)` — the pawl's rest angle for a carriage at rail position x — is the
one piece of kinematics: the largest angle (nose toward the disc's centre) at
which the roller is still clear of the teeth, found by bisection on the
exact distance to the toothed disc (`tooth_distance`). ClockworkMotion.pawl_angle
mirrors it and tools/test_pawl.py holds the two together.

The roller is its own part (`roller_pieces`, origin on its axle) so the rig can
turn it as it rolls on the tips (`ROLLER_SPIN` radians a metre of rail), and
each pinion is spun with a phase (`dip_offset`) chosen so the roller sits at
the bottom of a dip when the arm parks at its home.

Only a front or back mount carries a pawl (every mallet arm's pinion is behind
its carriage); an up/down disc lies flat over the rail and has no free rim.
"""
import numpy as np
from .clearance import PINION, MOUNTS, CARRIAGE, pinion_centre
from .gear import tooth_polygon, inset, convex_distance, BEVEL as TOOTH_BEVEL
from .linkage import ring, revolve, knuckle_pin, rounded_rect, Y, Z
from .sweep import sweep
from .gantry import prism

# lever: pivot to the yoke along -X in the pawl's frame; tilt: the frame's
# lean at rest, the lever running down toward its pivot; drop: the roller's
# rest radius past the tips (its radius and 5 mm of lift); finger: the roller's
# axle stands this far above the lever; nose_r: the roller; width: the eye and
# lever across the pin; the rest is the roller's axle, the pin, its ear and the spring.
PAWL = dict(lever=.10, tilt=-.25, drop=.023, finger=.03, nose_r=.018, roller_len=.03, axle_r=.004, width=.03, pivot_r=.011, ear_t=.014,
            coil_r=.019, wire_r=.0025, coil_turns=4.5, coil_len=.026, post_r=.004)
# One tooth of build_clockwork.gear (formlab.gear.tooth_polygon: involute, 20°,
# 4 mm corners), as the convex polygon inset by its bevel — the distance field
# adds the bevel back, so the corners are round. Tips at multiples of 2π/16
# from +x in the disc's home frame (dev/test_performance.gd pins the spin).
TOOTH = inset(tooth_polygon(), TOOTH_BEVEL)
TEETH = PINION['teeth']

def _pivot_from_centre():
    """The pivot in the disc's plane relative to its centre: wherever puts
    the nose, at the frame's rest lean, straight under the centre at its rest
    radius (r_tip + drop) — `nose_rest` turned by the lean, subtracted."""
    L = PAWL['lever']; F = PAWL['finger']; t = PAWL['tilt']
    return np.array([L*np.cos(t)-F*np.sin(t), -(PINION['r_tip']+PAWL['drop'])-L*np.sin(t)-F*np.cos(t)])

def pivot(mount):
    """Pivot pin, carriage-local: off to +X from under the disc's centre and
    below the nose's rest radius, in the disc's plane (`_pivot_from_centre`)."""
    if not MOUNTS[mount][1]: raise ValueError('a pawl needs a front or back pinion (an up/down disc has no free rim)')
    return pinion_centre(mount)+np.array([*_pivot_from_centre(), 0.])

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
    three nearest teeth, each the inset polygon TOOTH grown back by its bevel;
    vectorised."""
    qx = np.asarray(qx, float); qy = np.asarray(qy, float); x = np.asarray(x, float)
    th = x/PINION['r_pitch']; c = np.cos(th); s = np.sin(th)
    hx = qx*c+qy*s; hy = -qx*s+qy*c                      # the disc's home frame
    d = np.hypot(hx, hy)-PINION['r_hub']
    step = 2*np.pi/TEETH; i = np.round(np.arctan2(hy, hx)/step)
    for k in (-1, 0, 1):
        phi = (i+k)*step; cp = np.cos(phi); sp = np.sin(phi)
        u = hx*cp+hy*sp; v = -hx*sp+hy*cp                  # the tooth's frame: u radial, v tangential
        d = np.minimum(d, convex_distance(u, v, TOOTH)-TOOTH_BEVEL)
    return d

# the bisection's bracket, either side of the frame's rest lean
ANGLE_LO, ANGLE_HI, ANGLE_ITERS = -.15+PAWL['tilt'], .45+PAWL['tilt'], 48

def angle(x):
    """The pawl's angle for a carriage at rail position x: the largest angle
    at which the nose is clear of the teeth (the spring lifts it until it
    touches). Bisection; vectorised over x; mirrored by ClockworkMotion.pawl_angle."""
    x = np.asarray(x, float); P = _pivot_from_centre()
    lo = np.full(x.shape, ANGLE_LO); hi = np.full(x.shape, ANGLE_HI)
    for _ in range(ANGLE_ITERS):
        mid = (lo+hi)/2; n = nose_at(mid)
        clear = tooth_distance(P[0]+n[..., 0], P[1]+n[..., 1], x) >= PAWL['nose_r']
        lo = np.where(clear, mid, lo); hi = np.where(clear, hi, mid)
    return lo

def nose_radius(x):
    """Distance from the disc's centre to the nose for a carriage at x."""
    P = _pivot_from_centre(); n = nose_at(angle(x))
    return np.hypot(P[0]+n[..., 0], P[1]+n[..., 1])

PITCH = 2*np.pi*PINION['r_pitch']/TEETH
# The roller rolls on the tips: the disc's rim at the tips moves r_tip/r_pitch
# as fast as the carriage, and the roller — under the disc, turning the other
# way — turns that arc over its own radius. Radians of roller per metre of rail.
ROLLER_SPIN = -PINION['r_tip']/(PINION['r_pitch']*PAWL['nose_r'])

def dip_offset(x_home):
    """The rail offset, in (-PITCH/2, PITCH/2], that puts the roller at the
    bottom of a dip when the carriage stands at `x_home`: the pinion is spun
    by (x + offset) / r_pitch instead of x / r_pitch, so a stepped arm parks
    with its pawl seated at its home. The other rests fall where the score's
    contacts put them (docs/motion-design.md)."""
    xs = np.arange(0, PITCH, PITCH/720); k = int(np.argmin(nose_radius(xs)))
    return float((xs[k]-x_home+PITCH/2) % PITCH-PITCH/2)

def seating(x, phase=0.):
    """How far down its dip the roller sits for carriages at x: 0 at the bottom
    of a dip, 1 on a tip. Vectorised."""
    xs = np.arange(0, PITCH, PITCH/720); r = nose_radius(xs)
    return (nose_radius(np.asarray(x, float)+phase)-r.min())/(r.max()-r.min())

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
    yoke = prism([-L+.016, 0, 0], [-L-.010, 0, 0], .009, hl+.005, .3, 5)   # its top 3 mm under the roller
    tongues = [prism([-L, -.004, s_*(hl+.0025)], [-L, F+.004, s_*(hl+.0025)], .010, .0025, .5, 5) for s_ in (-1, 1)]
    axle = revolve([(0, -hl-.008), (P['axle_r']*.7, -hl-.008), (P['axle_r'], -hl-.006), (P['axle_r'], hl+.006), (P['axle_r']*.7, hl+.008), (0, hl+.008)], Z, (-L, F, 0), 16)
    # the spring: coil_turns about the pin from the eye's face toward the ear,
    # starting at +X (its fixed tail) and ending at -X (its moving tail)
    z0 = s*(w/2+.002); z1 = z0+s*P['coil_len']; n = int(P['coil_turns']*24)+1
    t = np.linspace(0, 1, n); ang = 2*np.pi*P['coil_turns']*t
    coil = sweep(np.c_[P['coil_r']*np.cos(ang), P['coil_r']*np.sin(ang), z0+(z1-z0)*t], P['wire_r'], P['wire_r'], profile=rounded_rect(1, 12))
    fixed = sweep([[P['coil_r'], -.002, z0], [P['coil_r'], .014, z0], [P['coil_r'], .03, z0]], P['wire_r'], P['wire_r'], profile=rounded_rect(1, 12))
    under = -.012-P['wire_r']
    moving = sweep([[-P['coil_r']+.002, 0, z1], [-.045, -.009, (z1+0)/2], [-.052, under, 0]], P['wire_r'], P['wire_r'], profile=rounded_rect(1, 12))
    pieces = [eye, lever, yoke, *tongues, axle, coil, fixed, moving]
    return pieces, ['steel']*6+['brass']*3

def roller_pieces(mount='back'):
    """The roller in its own frame (origin on its axle, at `nose_rest()` in
    the pawl's frame): a steel drum on the axle, with a brass grease plug
    let into each face off the axis — so it can be seen to turn. Returns
    (pieces, materials)."""
    P = PAWL; R = P['nose_r']; hl = P['roller_len']/2
    drum = revolve([(0, -hl), (R-.002, -hl), (R, -hl+.002), (R, hl-.002), (R-.002, hl), (0, hl)], Z, (0, 0, 0), 40)
    plugs = [revolve([(0, s_*(hl-.002)), (.003, s_*(hl-.002)), (.003, s_*(hl+.0008)), (0, s_*(hl+.0008))], Z, (0, R*.6, 0), 16) for s_ in (-1, 1)]
    return [drum, *plugs], ['steel', 'brass', 'brass']

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
    # the post stands where the spring's fixed tail lies with the pawl at its rest lean
    px, py = post_centre(mount); t = P['tilt']; px, py = px*np.cos(t)+py*np.sin(t), -px*np.sin(t)+py*np.cos(t)
    z_post = sorted((pv[2]+ze, pv[2]+s*P['width']/2))
    post = revolve([(0, z_post[0]), (P['post_r'], z_post[0]), (P['post_r'], z_post[1]), (0, z_post[1])], Z, (pv[0]+px, pv[1]+py, 0), 16)
    span = abs(ze)+P['ear_t']/2+P['width']/2
    centre = pv+[0, 0, (ze+s*P['ear_t']/2-s*P['width']/2)/2]
    pin = knuckle_pin(P['pivot_r'], span, axis=(0, 0, -s), centre=centre)
    return [ear, arm, strut, post]+pin

def manifest(mount='back', x_home=0.):
    """What the model manifest records for an arm's pawl: performance.gd poses
    the pawl at root + pivot, turned by pawl_angle(x + phase) about Z, the
    roller at the pawl's nose turned by ROLLER_SPIN·x, and spins the pinion
    by (x + phase) / r_pitch so the pawl rests in a dip at x_home."""
    return dict(mount=mount, pivot=pivot(mount).round(6).tolist(), nose=nose_rest().round(6).tolist(),
                lever=PAWL['lever'], finger=PAWL['finger'], nose_r=PAWL['nose_r'], drop=PAWL['drop'],
                phase=round(dip_offset(x_home), 6), home_x=round(float(x_home), 6), roller_spin=round(ROLLER_SPIN, 6))

def capsules(root, mount='back', phase=0.):
    """World capsules per pose for the rulers, name -> (P, Q, r): the lever,
    yoke, tongues and roller (turned by angle(x + phase)); the eye, spring, ear, pin, post, arm
    and strut. `root`: (T, 3) shoulder-pin positions."""
    root = np.asarray(root, float); P = PAWL; s = _side(mount); pv = pivot(mount); ze = ear_offset(mount)
    al = angle(root[:, 0]+phase); c = np.cos(al)[:, None]; sn = np.sin(al)[:, None]
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

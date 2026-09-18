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
DEFAULT_SPEC = dict(width=.034, depth=.062, ear_r=.055, pin_r=.018, ear_t=.022, head_t=.012, boss_r=.05, web=.05)

def default_layers(spec=DEFAULT_SPEC):
    """The knuckle stack along the pin axis, half-widths from the crosshead's
    mid-plane outward, every layer with its own room: a primary link's eye
    at the centre (`width` thick); the crosshead's two plates (`head_t`
    each) sandwiching it 2 mm clear, inner faces at ±plate; the primary
    link's fork ears (`ear_t`) straddling the plates 3 mm clear (fork gap);
    the secondary bar outboard of the ears 6 mm clear, centred at ±outer.
    The primary knuckle pin spans the ears 2 mm over (pin_span); a
    secondary bar's stub pin reaches 2 mm past its eye (span) and its nut
    to pin_x, the widest thing on the arm."""
    plate = spec['width']/2+.002
    plate_out = plate+spec['head_t']
    gap = 2*plate_out+.006
    ear_out = gap/2+spec['ear_t']
    outer = ear_out+.006+spec['width']*.8/2
    span = 2*outer+spec['width']*.8+.004
    return dict(plate=plate, plate_out=plate_out, gap=gap, ear_out=ear_out, pin_span=2*ear_out+.004,
                outer=outer, span=span, pin_x=span/2+spec['pin_r']*1.9)

# The linear carriage (formlab.linkage.carriage_body): a split bushing riding
# each guide bar, a cheek plate on the -X side joining them (the +X side is
# taken by the second bar's boss), and the pinion's axle out of the carriage
# plane — or, for a pinion above or below the carriage, a bridge back from
# the bushing carrying a vertical axle clear of the bars (bridge_y is the
# block's extent along the mount direction, bridge_z how far back it
# reaches; the axle stands at axle_z). bar_dy / bar_r are the rail's
# (tools/build_clockwork.py). The cheek stands 6 mm outside the crosshead's
# -X plate, inside the pin span. Each bushing is a housing (bush_body_r)
# with a flanged bush at either end (bush_r, flange_t) held by four bolts
# on bolt_circle — the rail heads' shaft supports (gantry.BUSH) again — and
# all of it lies inside the bush_len × bush_r capsule arm_capsules reserves,
# the bolts under its domed ends (linkage.bar_bush).
CARRIAGE = dict(bar_dy=.075, bar_r=.024, bush_r=.045, bush_len=.16, bush_body_r=.039, flange_t=.008,
                bolt_circle=.036, bolt_r=.0055, bolt_h=.012, cheek_t=.02,
                cheek_x=-(default_layers()['plate_out']+.006+.01),
                cheek_y=.12, cheek_z=.045, axle_r=.02, bridge_y=(.085, .125), bridge_z=-.13, bridge_x=.03, axle_z=-.10)
# The drive pinion (build_clockwork.gear) on its axle, and the rack it rolls
# on (formlab.gantry.rack). The disc sits on one of four MOUNTS off the
# carriage — in front, behind, above or below — whichever the arm's links
# never swing through (pinion_mount): `out` from the carriage plane for
# front/back (axle along Z, rack above the disc), `up` above the rail axis
# for up/down (vertical axle at CARRIAGE.axle_z, rack behind the disc).
# boss_r / boss_h: the hub boss proud of the disc's outer face (build_clockwork
# .gear, it turns with the disc); the axle runs on through it and is retained
# by a washer, hex nut and split pin over the next `retain` (linkage.fastening,
# cast with the carriage). drive_capsules reserves boss+fastening as one
# capsule, `pinion_boss`, so the planner charges the depth.
PINION = dict(out=.195, up=.17, r_pitch=.12, teeth=16, thickness=.07, r_tip=.13, r_hub=.1014, boss_r=.045, boss_h=.03, retain=.05)
# mount -> disc-plane normal (y, z); preference order for ties
MOUNTS = dict(back=(0., -1.), up=(1., 0.), down=(-1., 0.), front=(0., 1.))
# Two drives for two vocabularies (docs/motion-design.md, docs/plans/leadscrew-
# servo-drive.md): a stepped arm (mallet, hammer) keeps rack, pinion and pawl;
# a servo arm (pick, rake) rides a LEADSCREW — a threaded shaft the length of
# the rail on the rack's line (s_axis from the axle line along rack_direction,
# in the disc's plane), turning in bearings on the head stubs with a finned
# drive housing at the low end, and a bronze nut on the carriage bracketed to
# the boss where the pinion's axle stood. The nut takes the pinion's place in
# the arm's capsules (drive_capsules), the shaft the rack's (gantry.rail_racks).
SCREW = dict(s_axis=.135, shaft_r=.010, thread_r=.003, pitch=.008, turn_samples=10, thread_sides=16,
             nut_r=.035, nut_len=.09, arm_r=.02, flange=.045, flange_t=.008, bolt_circle=.032,
             bearing_r=.03, bearing_len=.04, housing_r=.028, housing_len=.07, fin_r=.034, fin_t=.004)

def drive_kind(cfg):
    """'rack' for a stepped arm (mallet, hammer), 'screw' for a servo arm."""
    return 'rack' if cfg.get('kind') in ('mallet', 'hammer') else 'screw'
# The rail gantry (formlab.gantry builds it; the rail search screens it):
# bars run rail_over past the reach window into a head (head_len long from
# head_inset past the bar end, half-height head_h, half-depth head_d) that
# a tapered mast carries from the stage — straight down, or on a bracket
# `outreach` beyond the rail end along X and `setback` behind it along Z
# (gantry_candidates, cheapest first). mast_r is the column the rail search
# reserves for it: between the mast's half-depth at the top and at the base.
GANTRY = dict(rail_over=.12, head_inset=.04, head_len=.20, head_h=.14, head_d=.07,
              mast_w=.045, mast_d_top=.05, mast_d_cap=.11, mast_r=.08, margin=.02,
              stage=dict(x=(-6.4, 6.4), z=(-4.6, 3.3), top=-.02),
              setbacks=(0., .40, .55, .70, .85, 1.0, 1.2, 1.5), outreaches=(0., .35, .5, .7))

def gantry_candidates():
    """(outreach, setback) brackets, cheapest first: straight down, then
    back, then out, then both; behind before in front (negative setback)."""
    G = GANTRY
    return sorted(((o, sb) for o in G['outreaches'] for sb in G['setbacks']+tuple(-x for x in G['setbacks'][1:])),
                  key=lambda c: (c[0]+abs(c[1]), c[1] < 0, c[0]))

def mast_columns(x_end, side, rz, behind=1):
    """Where a mast could stand for the rail end at x_end (side ±1 along X):
    (x_col, z_m, outreach, setback) per bracket candidate on the stage, in
    the gantry planner's order (formlab.gantry.plan_end uses the same rule)."""
    G = GANTRY; out = []
    for o, sb in gantry_candidates():
        x_col = x_end+side*(G['head_inset']+G['head_len']-.07+o); z_m = rz+behind*sb
        if G['stage']['x'][0] < x_col < G['stage']['x'][1] and G['stage']['z'][0] < z_m < G['stage']['z'][1]:
            out.append((x_col, z_m, o, sb))
    return out

def head_box(x_end, side, ry, rz):
    """The rail head's bounding box at one rail end (formlab.gantry.rail_end's
    brass prism): head_inset beyond the bar end, head_len long."""
    G = GANTRY; x_in = x_end+side*G['head_inset']; x_out = x_in+side*G['head_len']
    return (np.array([min(x_in, x_out), ry-G['head_h'], rz-G['head_d']]), np.array([max(x_in, x_out), ry+G['head_h'], rz+G['head_d']]))

def foot_level(x, z, boxes):
    """Stage top, or the lid of a furniture box the mast footprint stands on:
    (y, box or None). boxes: (lo, hi) pairs."""
    y = GANTRY['stage']['top']; on = None
    for lo, hi in boxes:
        if lo[0]+.22 <= x <= hi[0]-.22 and lo[2]+.22 <= z <= hi[2]-.22 and hi[1] < 1e8:
            if hi[1] > y: y, on = float(hi[1]), (lo, hi)
    return y, on

def bracket_solids(x_end, side, ry, rz, behind, outreach, setback, foot_y=None):
    """The solids formlab.gantry.rail_end builds for one bracket, as the
    planner measures them (its `solids`): ('box', lo, hi) for the mast
    column, the bracket beams and the plinth; ('capsule', a, b, r) for the
    knee braces. Numpy-only so the rail search (inside Blender) can screen
    a bracket before the rails are fixed; rail_end must stay in step."""
    G = GANTRY; s = float(side); foot_y = G['stage']['top'] if foot_y is None else foot_y
    x_in = x_end+s*G['head_inset']; x_head = x_in+s*G['head_len']; x_col = x_in+s*(G['head_len']-.07+outreach); z_m = rz+behind*setback
    top = ry+G['head_h'] if (setback or outreach) else ry-G['head_h']
    H = top-(foot_y+.08); d_base = min(G['mast_d_top']+.025*H, G['mast_d_cap'])
    def box(xa, xb, ya, yb, za, zb): return ('box', np.array([min(xa, xb), min(ya, yb), min(za, zb)]), np.array([max(xa, xb), max(ya, yb), max(za, zb)]))
    out = [box(x_col-G['mast_w'], x_col+G['mast_w'], foot_y+.06, top, z_m-d_base, z_m+d_base),
           box(x_col-.17, x_col+.17, foot_y, foot_y+.085, z_m-d_base-.10, z_m+d_base+.10)]
    if setback or outreach:
        dz = behind*np.sign(setback)
        if outreach:
            out.append(box(x_head-s*.06, x_col, ry-.08, ry+.08, rz-.04, rz+.04))
            out.append(('capsule', np.array([x_head-s*.08, ry-.10, rz]), np.array([x_col, ry-.10-min(outreach+.13, 1.0), rz]), .017*1.5))
        if setback:
            z_a = rz-dz*.04 if outreach else rz+dz*(G['head_d']-.02)
            out.append(box(x_col-.04, x_col+.04, ry-.08, ry+.08, z_a, z_m))
            out.append(('capsule', np.array([x_col, ry-.10, rz+dz*.03]), np.array([x_col, ry-.10-min(abs(setback), 1.0), z_m]), .017*1.5))
    return out

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

def drive_capsules(root, mount, drive='rack'):
    """The pinion (a stack of chords in its plane, shortened by their radius
    so the disc's rim is not overstated toward the rail heads), its axle
    and — for an up/down mount — the bridge the axle stands on. World
    capsules per pose, name -> (P, Q, r). `drive` 'screw': no disc — the
    axle boss stops at the disc plane and carries the nut's bracket arm out
    along rack_direction to the leadscrew's nut (SCREW)."""
    C = CARRIAGE; G = PINION; X = np.array([1., 0, 0]); ny, nz = MOUNTS[mount]
    n = np.array([0., ny, nz]); centre = root+pinion_centre(mount); h = G['thickness']/2
    u = rack_direction(mount)          # in-plane axis the chords are stacked along
    caps = {}
    if drive == 'screw': h = 0.       # the boss reaches the plane the nut's arm lies in
    if nz:
        caps['carriage_axle'] = (root+n*.03, centre-n*h, C['axle_r'])
    else:
        b0, b1 = C['bridge_y']; by = np.array([0., ny*(b0+b1)/2, 0.])
        caps['carriage_bridge'] = (root+by, root+by+[0, 0, C['bridge_z']], (b1-b0)/2+.01)
        caps['carriage_axle'] = (root+[0, ny*b1-ny*.01, C['axle_z']], centre-n*h, C['axle_r'])
    if drive == 'screw':
        S = SCREW; axis = centre+u*S['s_axis']; bx = X*S['nut_len']/2
        caps['nut_arm'] = (centre, axis, S['arm_r']+.005)      # the rounded-rect arm's corners reach arm_r·(1+.5·(√2−1))
        caps['nut'] = (axis-bx, axis+bx, S['nut_r'])
        fm = axis-u*(S['nut_r']*.8+S['flange_t']/2); fx = X*S['flange']     # the square flange and its bolt heads
        caps['nut_flange'] = (fm-fx, fm+fx, S['flange']+.002)
        return caps
    for k, s in enumerate((-.11, -.07, 0., .07, .11)):
        half = max(np.sqrt(G['r_tip']**2-s*s)-h, .02)
        caps[f'pinion{k}'] = (centre-X*half+u*s, centre+X*half+u*s, h)
    # the hub boss on the outer face and the axle's fastening beyond it
    caps['pinion_boss'] = (centre+n*h, centre+n*(h+G['boss_h']+G['retain']), G['boss_r'])
    return caps

MOUNT_COMFORT = .05    # a mount this clear of the links is taken in preference order

def pinion_mount(poses, o1, o2, layers, spec, mounts=None, drive='rack'):
    """Which mount keeps the drive clear of the arm's own links over the
    motion. The minimum gap between the pinion (or the leadscrew's nut and
    its arm), axle and bridge and the links, webs and bars is measured for
    each mount; the first in MOUNTS order (behind the rail — away from the
    strings — then above, below, in front) with MOUNT_COMFORT to spare is
    taken, else the clearest. Returns (mount, gap)."""
    best = None
    for m in (mounts or MOUNTS):
        caps, adjacent = arm_capsules(poses, o1, o2, layers, spec, m, drive)
        drive_parts = [k for k in caps if k.startswith(('pinion', 'nut')) or k in ('carriage_axle', 'carriage_bridge')]
        gap = 1e9
        for a in drive_parts:
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

# A hinged hammer's flange and head (linkage.hammer_tool builds it, arm_capsules
# below measures it). It lives here rather than in linkage because both of those
# need it and linkage already imports this module: the arrow only points one way.
HAMMER_FORM = dict(ear_r=.020, pin_r=.008, cheek_x=.050, cheek_t=.010, cheek_z=.012,
                   boss_r=.013, post=.050, tail=.030, rod_r=.0085,
                   check_r=.009, felt=.007, coil_r=.014, wire_r=.0017, turns=3.5, coil_len=.016)

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

def arm_capsules(poses, o1, o2, layers, spec, mount='back', drive='rack'):
    """World capsules per pose for a parallelogram arm. Returns dict name ->
    (P, Q, r) arrays of shape (T,3),(T,3),scalar, plus the adjacency set
    (pairs that legitimately touch at a shared pin). `mount`: the pinion's
    (MOUNTS; pinion_mount chooses it); `drive`: 'rack' (pinion) or 'screw'
    (the leadscrew's nut) — drive_kind."""
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
        # 25 mm, not the shank's own 13: the socket carries a clamp collar
        # (linkage.COLLAR, 1.6x the 13 mm shank = 20.8) and a set screw on a
        # 2 mm pad whose 12-gon corner reaches 24.0 mm off the axis. The
        # capsule contains the widest thing on the shank, not the average one.
        # (Radially. Axially this pair is only a two-segment schematic of the
        # swan neck and the shank stands 63 mm off the chord; see
        # tools/test_linkage_tools.py and docs/articulated-arms.md, "Tools".)
        'shank': (apex, socket_end, .025),
    }
    # A HINGED HAMMER (rig.HAMMER, linkage.hammer_tool) has two more things to
    # measure and one fewer: the head turns on its own pin, so it is its own
    # capsule from the hinge to the felt face and sweeps with the flip; and what
    # rides the tool frame is the FLANGE that carries the pin, not the air the
    # head swings in. The flange's radius is its half-width across the pin —
    # the cheeks have to stand outboard of the felt head's own radius, which is
    # why it is 60 mm and not 30.
    # `head` is the flip angle per sample and is all zeros for a rigid tool;
    # callers that build a poses dict by hand (the rulers) may omit it.
    if np.any(poses.get('head', 0.0)):
        # rig is a leaf (numpy only) so this cannot cycle; the fallback is for
        # Blender, which puts formlab/ on sys.path and imports the modules bare.
        try: from .rig import HAMMER
        except ImportError: from rig import HAMMER
        HF = HAMMER_FORM
        hinge = tip+[0, HAMMER['head_l'], 0]
        top = hinge+[0, HF['post']+HF['cheek_z'], 0]
        caps['tool'] = (hinge-[0, HF['ear_r']*1.1, 0], top, HF['cheek_x']+HF['cheek_t'])
        # ...and the shank starts its own radius ABOVE the flange's bridge, not
        # at the 70 mm a rigid tool's ferrule gives it. The neck's lower 25 mm
        # is inside the flange's 60 mm capsule already; starting the shank at
        # the bridge instead would put its 25 mm radius down among the pin and
        # the tail, and read as 13 mm of collision at every blow.
        caps['shank'] = (top+[0, .025, 0], socket_end, .025)
        # The head is THREE capsules, not one, because it is a 9 mm rod with a
        # 90 mm ball on one end and a tail on the other: one fat capsule from
        # the pin to the face claims the ball's radius all the way up the rod
        # and reads as 11 mm inside the shank it in fact passes cleanly between.
        L = HAMMER['head_l']; hr = HAMMER['head_r']; rr = HF['rod_r']
        dirs = (poses['felt']-hinge)/L
        ball = poses['felt']-dirs*hr
        caps['head'] = (ball, ball, hr*1.02)                      # the felt, wrap proud
        caps['head_rod'] = (hinge, ball-dirs*hr, rr*1.6)          # the moulding
        caps['head_tail'] = (hinge, hinge-dirs*HF['tail']*1.2, rr*1.7)
    # The carriage on its guide: bushings along the bars, the cheek plate, the
    # pinion's axle (and bridge); the pinion itself as a stack of chords.
    C = CARRIAGE; bx = X*C['bush_len']/2
    for s, tag in ((-1, '-'), (1, '+')):
        c = root+[0, s*C['bar_dy'], 0]; caps['carriage_bush'+tag] = (c-bx, c+bx, C['bush_r'])
    cx = X*C['cheek_x']; cy = np.array([0., C['cheek_y'], 0])
    caps['carriage_cheek'] = (root+cx-cy, root+cx+cy, C['cheek_z'])
    caps.update(drive_capsules(root, mount, drive))
    carriage = [k for k in caps if k.startswith('carriage_') and k != 'carriage_web']
    pinion = [k for k in caps if k.startswith(('pinion', 'nut'))]     # the disc and boss, or the leadscrew's nut and its arm
    adjacent = {frozenset(p) for p in [
        # the carriage's parts meet the links at the shoulder pin; the pinion
        # (disc and hub boss) touches only its axle and its fastening — a link
        # swinging into the disc is a real hit
        *[(a, b) for a in carriage for b in carriage+pinion+['carriage_web', 'upper', 'upper2'] if a != b],
        *[(a, b) for a in pinion for b in pinion if a != b],
        ('upper', 'lower'), ('upper', 'elbowhead_web1'), ('upper', 'elbowhead_web2'), ('upper', 'carriage_web'),
        ('lower', 'elbowhead_web1'), ('lower', 'elbowhead_web2'), ('lower', 'wristhead_web'), ('lower', 'shank'),
        ('upper2', 'elbowhead_web1'), ('upper2', 'carriage_web'), ('upper2', 'elbowhead_web2'),
        ('lower2', 'elbowhead_web2'), ('lower2', 'wristhead_web'), ('lower2', 'elbowhead_web1'), ('lower2', 'shank'),
        ('elbowhead_web1', 'elbowhead_web2'), ('wristhead_web', 'shank'), ('upper', 'wristhead_web'),
        ('upper2', 'upper'), ('lower2', 'lower'), ('tool', 'shank'),
        # a hinged head hangs on the flange's own pin, and its three capsules
        # are one rigid body about that pin
        *[(a, b) for a in ('head', 'head_rod', 'head_tail') for b in ('head', 'head_rod', 'head_tail', 'tool') if a != b]]}
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

def report(rig, aid, o1, o2, layers, spec, strings=None, string_r=.002, poses=None, mount='back', drive='rack'):
    poses = rig.poses(aid) if poses is None else poses
    caps, adjacent = arm_capsules(poses, o1, o2, layers, spec, mount, drive)
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

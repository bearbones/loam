"""The joints table of `loam-motion/2` (formlab/bake.py writes it into the bake
header; formlab.bake.Bake and harness/motion_bake.gd evaluate it). Every part
the harness moves is a BODY bound to a JOINT, and every joint is a row of one
kinematic tree:

    {"id": "<owner>/<name>", "owner", "name", "parent" (an earlier id | null),
     "type": revolute | prismatic | fixed, "axis" (in the parent frame),
     "origin" (in the parent frame; a root joint may use {"mean": [[x,y,z],..]}),
     "q_home", "value": {"src", "ops"} | null, "spin", "unit", "limits",
     "range", "driver", "pose": {"pin", "aim", "orient"} | null, "extra"}

The value of a joint is a source (a baked channel, a component of one, an
earlier joint, the time, a constant) put through a short list of ops (add,
mul, div, neg, wrap, pawl, table). The ops copy the harness's M2 expressions
operand for operand and in their order, so the generic evaluator reproduces
the hand-written poser bit for bit (harness/dev/test_pose_parity.gd holds it).

Two modes read one table (formlab/bake.py's docstring is the normative spec):
  - POSE mode renders: a joint with a `pose.pin` sits exactly on its baked
    channel, an `aim` frame points at a joint (MotionBake.link_basis), an
    `orient` copies a joint's world basis. This is today's poser, as data.
  - FK mode is the pure chain rule from the q values (the shoulder, elbow and
    a mallet's lean are their own columns, `<aid>.q.*`). The writer checks it
    reproduces every pin on every row (FK_TOL) before it writes a bake.

This module is numpy-only and Blender-safe. It is not a GEOMETRY_SOURCE: the
rows read the manifest and the rig, never the reverse.

Adding a joint (M4, M5, M7, M9): add its rows here (and a `<aid>.q.<name>`
column in formlab/bake.py only for an angle with a law of its own per row).
No harness code changes unless the row needs a new op, source kind, joint
type or body mode: then bump KINEMATICS['version'], implement it in both
readers and extend tools/test_bake.py's synthetic test (T10). test_bake holds
every row to the rig, so a new row also adds its structure to T4
(expected_rows; a new body's node name to the vocabulary), its law to T6 and
a new column to T2 (docs/clockwork-build.md, "Adding a joint").
"""
import math
import numpy as np
try:
    from . import rig as R
    from . import segments as SEG
    from .clearance import PINION, pinion_centre
except ImportError:
    import rig as R
    import segments as SEG
    from clearance import PINION, pinion_centre

# The vocabulary a reader of kinematics v1 knows. The lists are documentation
# for other readers: each reader checks every row against its own built-in
# vocabulary and refuses a version above its own.
KINEMATICS = dict(
    version=1,
    types=['revolute', 'prismatic', 'fixed'],
    sources=['channel', 'joint', 'time', 'const'],
    ops=['add', 'mul', 'div', 'neg', 'wrap', 'pawl', 'table'],
    symbols=['TAU', '-TAU', 'PI', '-PI', 'PI/2'],
    modes=['frame', 'rest', 'world', 'spin'],
    drivers=['rack', 'screw', 'ik', 'lean', 'parallelogram', 'gear', 'thread', 'pawl', 'roll', 'flip',
             'recoil', 'clock', 'belt', 'stand'])
SYMBOLS = {'TAU': 2*math.pi, '-TAU': -2*math.pi, 'PI': math.pi, '-PI': -math.pi, 'PI/2': math.pi/2}
# The flywheel turns once a bar of the score's tempo (performance.gd's M2
# flywheel_angle: -TAU*t*bpm/240, bpm 84 when the score has none).
BPM_DEFAULT = 84.0
FLYWHEEL_DIV = 240.0
# The laws the table turns the harness's parts by (tools/players/r_machine.py
# reads them here; tools/test_bake.py holds the rows' ops to them): the pinion
# rolls (x + phase)/r_pitch on its rack, the leadscrew turns -2 pi x/pitch, the
# pawl's roller spins roller_spin x, the flywheel -2 pi t bpm/240 and the belt
# pulley the flywheel's angle times the pulleys' radii.
HARNESS_LAWS = dict(pinion_r=PINION['r_pitch'], screw=True, roller=True, flywheel=(BPM_DEFAULT, FLYWHEEL_DIV), belt=True)
LEAN_MAX = 0.05      # rad: a mallet's links leave the plane through the rail by under 3.1 mrad today
FK_TOL = 1e-9        # m: the writer's FK self-check (pure double trig round trips, ~1e-15)
PREP_A = np.linspace(0.0, 1.0, 9)
PREP_IOI = np.geomspace(0.02, 8.0, 64)
CMP_EPSILON = 1e-5   # Godot's, for wrapf's is_equal_approx / is_zero_approx
AXIS_TOL = 1e-6      # |axis| - 1: both readers refuse a joint axis that is not a unit vector

X = [1.0, 0.0, 0.0]; Y = [0.0, 1.0, 0.0]; Z = [0.0, 0.0, 1.0]
AIM_REF = [1.0, 0.0, 0.0]          # Vector3.RIGHT: a link's pin axis
AIM_FALLBACK = [0.0, 0.0, -1.0]    # Vector3.FORWARD: link_basis's fallback

# ---------------------------------------------------------------------- rows
def _z(x):
    """A float, never -0.0 (the writer emits no signed zero)."""
    x = float(x)
    return 0.0 if x == 0.0 else x

def _vec(v): return [_z(x) for x in v]

def _row(owner, name, parent=None, type='fixed', axis=None, origin=None, value=None, spin=False,
         driver=None, pose=None, extra=None):
    return dict(id=f'{owner}/{name}', owner=owner, name=name, parent=parent, type=type,
                axis=None if axis is None else list(axis), origin=[0.0, 0.0, 0.0] if origin is None else origin,
                q_home=0.0, value=value, spin=bool(spin), unit={'revolute': 'rad', 'prismatic': 'm'}.get(type),
                limits=None, range=None, driver=driver, pose=pose, extra=extra or {})

def _value(src, *ops): return dict(src=src, ops=[list(op) for op in ops])

def _pose(pin=None, aim=None, orient=None):
    return dict(pin=pin, aim=None if aim is None else dict(joint=aim, ref=list(AIM_REF), fallback=list(AIM_FALLBACK)),
                orient=orient)

def _body(joint, node, mode, optional=False):
    return dict(joint=joint, node=node, mode=mode, optional=bool(optional), mass=None, com=None, inertia=None)

def arm_rows(rig, aid, hdr, channels=()):
    """One arm's joints and bodies (table order), from the manifest's arm
    (rig.geometry['arms'][aid]) and the bake's arm record `hdr` (stepped,
    flip_sign, head_l). `channels`: the bake's channel names (an arm's pawl
    rides its `.ride` channel when it has one)."""
    cfg = rig.geometry['arms'][aid]; J = []; B = []
    def j(name, **kw):
        J.append(_row(aid, name, **kw)); return J[-1]['id']
    def body(joint, part, mode, optional=False): B.append(_body(joint, part, mode, optional))
    rootx = dict(channel=f'{aid}.root', index=0); rooty = dict(channel=f'{aid}.root', index=1)
    l1 = float(cfg['l1']); l2 = float(cfg['l2']); ry = float(cfg['root_y']); rz = float(cfg['root_z'])
    drive = str(cfg.get('drive', 'rack'))
    # The carriage rides its rail at (x, root_y + the rail's sag at x, root_z)
    # (formlab.rig.Rig.pose): the sag is a slide in y under the slide in x.
    cy = j('carriage_y', type='prismatic', axis=Y, origin=_vec([0.0, ry, rz]), value=_value(rooty, ['add', _z(-ry)]),
           driver=dict(kind='recoil', of='rail_sag'))
    # Crossheads and pins keep a fixed orientation: that is what the
    # parallelograms guarantee (pose mode: the carriage's identity frame).
    car = j('carriage', parent=cy, type='prismatic', axis=X, value=_value(rootx), driver=dict(kind=drive),
            pose=_pose(pin=f'{aid}.root'))
    body(car, f'{aid}__carriage', 'rest'); body(car, f'{aid}__shoulder', 'rest')
    base = car
    if rig.stepped(aid):
        # a stepped arm's carriage stands at carriage_x, off the tip's x by its
        # detent ring: the links lean out of the rail's plane by psi (<= 3.1
        # mrad today). FK only: the pose keeps the carriage's frame.
        base = j('lean', parent=car, type='revolute', axis=Y, value=_value(dict(channel=f'{aid}.q.lean')),
                 driver=dict(kind='lean'), pose=_pose(orient=car))
    # The links: zero along the parent's +y, right-handed about +x. The
    # columns are ruler 16's joint_series (shoulder s, rel), so the tree's
    # angles are pi/2 - s and (pi/2 - s) - rel. Each link's frame is
    # MotionBake.link_basis: y along the link, x the pin axis, z = x × y;
    # meshes are built at true length in it (formlab.linkage), never scaled.
    sh = j('shoulder', parent=base, type='revolute', axis=X,
           value=_value(dict(channel=f'{aid}.q.shoulder'), ['neg'], ['add', 'PI/2']),
           driver=dict(kind='ik'), pose=_pose(aim=f'{aid}/elbowhead'), extra=dict(length=l1))
    body(sh, f'{aid}__upper', 'frame')
    o1 = _vec(cfg['o1']); o2 = _vec(cfg['o2'])
    shp = j('shoulder_pair', parent=base, type='revolute', axis=X, origin=o1, value=_value(dict(joint=sh)),
            driver=dict(kind='parallelogram', of=sh), pose=_pose(orient=sh),
            extra=dict(closes=dict(joint=f'{aid}/elbowhead', offset=list(o1), length=l1)))
    body(shp, f'{aid}__upper2', 'frame')
    eh = j('elbowhead', parent=sh, type='revolute', axis=X, origin=[0.0, _z(l1), 0.0], value=_value(dict(joint=sh), ['neg']),
           driver=dict(kind='parallelogram', of=shp), pose=_pose(pin=f'{aid}.elbow', orient=car))
    body(eh, f'{aid}__elbowhead', 'rest'); body(eh, f'{aid}__elbow', 'rest')
    el = j('elbow', parent=eh, type='revolute', axis=X,
           value=_value(dict(channel=f'{aid}.q.elbow'), ['neg'], ['add', dict(joint=sh)]),
           driver=dict(kind='ik'), pose=_pose(aim=f'{aid}/wristhead'), extra=dict(length=l2))
    body(el, f'{aid}__lower', 'frame')
    elp = j('elbow_pair', parent=eh, type='revolute', axis=X, origin=o2, value=_value(dict(joint=el)),
            driver=dict(kind='parallelogram', of=el), pose=_pose(orient=el),
            extra=dict(closes=dict(joint=f'{aid}/wristhead', offset=list(o2), length=l2)))
    body(elp, f'{aid}__lower2', 'frame')
    wh = j('wristhead', parent=el, type='revolute', axis=X, origin=[0.0, _z(l2), 0.0], value=_value(dict(joint=el), ['neg']),
           driver=dict(kind='parallelogram', of=elp), pose=_pose(pin=f'{aid}.wrist', orient=car))
    body(wh, f'{aid}__wristhead', 'rest'); body(wh, f'{aid}__wrist', 'rest')
    wo = R.Rig.wrist_offset(cfg)
    tool = j('tool', parent=wh, origin=_vec([-float(v) for v in wo]), pose=_pose(pin=f'{aid}.tip'))
    body(tool, f'{aid}__tool', 'rest'); body(tool, f'{aid}__shank', 'rest')
    if 'head' in cfg:
        # A hinged hammer's head turns on the flange's pin, head_l above the
        # tool frame's origin. The head's mesh is built at the blow (angle 0,
        # the felt face straight down), and the flip is one rotation about the
        # pin axis: -angle*sign, the same rotation formlab.rig.head_offset
        # applies to the felt face, which is why the blow lands exactly on the
        # scored point.
        hd = j('head', parent=tool, type='revolute', axis=X, origin=[0.0, _z(hdr['head_l']), 0.0],
               value=_value(dict(channel=f'{aid}.head'), ['neg'], ['mul', float(hdr['flip_sign'])]),
               driver=dict(kind='flip'))
        body(hd, f'{aid}__head', 'rest')
    if drive == 'rack':
        # The pinion rides its axle on the carriage and rolls on the rack
        # (formlab.clearance.PINION / MOUNTS, formlab.gantry.rack): in front of
        # or behind the carriage it is upright under a rack above it; above or
        # below the carriage it lies flat against a rack behind the rail.
        # Either way +x travel turns it by x / pitch radius about its axle. A
        # pinion with a pawl is spun with a phase (formlab.pawl.dip_offset)
        # that seats the roller in a dip when the arm parks at its home. The
        # spin composes on the imported basis (a rest body): setting one Euler
        # component of a basis that is a quarter turn about X hits gimbal lock.
        mount = str(cfg.get('pinion', 'back')); flat = mount in ('up', 'down')
        phase = float(cfg['pawl'].get('phase', 0.0)) if 'pawl' in cfg else 0.0
        r_pitch = float(HARNESS_LAWS['pinion_r'])
        pn = j('pinion', parent=car, type='revolute', axis=(Y if flat else Z), origin=_vec(pinion_centre(mount)),
               value=_value(rootx, ['add', _z(phase)], ['div', r_pitch]), spin=True,
               driver=dict(kind='gear', r_pitch=r_pitch, teeth=int(PINION['teeth'])))
        body(pn, f'{aid}__gear', 'rest')
        if 'pawl' in cfg:
            # The roller detent pawl (formlab.pawl) hangs on its pivot off the
            # carriage and turns about z so its roller rides the spun teeth:
            # lifted (positive angle) on a tip, dropped into the gap between.
            # Above PAWL_RIDE teeth a second it rides the tips: the `.ride`
            # channel leans the table's angle toward pawl.ride_angle
            # (formlab.bake.Bake.pawl). The roller sits on the pawl's axle and
            # rolls on the tips: roller_spin radians a metre of rail.
            pw = cfg['pawl']; ride = f'{aid}.ride' if f'{aid}.ride' in channels else None
            pa = j('pawl', parent=car, type='revolute', axis=Z, origin=_vec(pw['pivot']),
                   value=_value(rootx, ['add', _z(phase)], ['pawl', ride], ['neg']), driver=dict(kind='pawl'))
            body(pa, f'{aid}__pawl', 'rest')
            ro = j('roller', parent=pa, type='revolute', axis=Z, origin=_vec(pw['nose']),
                   value=_value(rootx, ['mul', float(pw.get('roller_spin', 0.0))]), spin=True, driver=dict(kind='roll'))
            body(ro, f'{aid}__roller', 'rest')
    else:
        # A servo arm's leadscrew turns instead: a right-hand thread, so +x
        # travel of the nut is a negative turn about +x, 2 pi per pitch
        # (formlab.gantry.screw_geometry). The shaft's mesh is in world space,
        # so the turn is taken about the axis line through (0, y, z) (a world
        # body). Wrapped in double first: a Basis takes a 32-bit angle, and a
        # screw 4 m down its rail has turned ~3000 rad.
        sc = cfg['screw']; pitch = float(sc.get('lead', sc['pitch']))
        s = j('screw', type='revolute', axis=X, origin=_vec([0.0, sc['y'], sc['z']]),
              value=_value(rootx, ['mul', '-TAU'], ['div', pitch], ['wrap', '-PI', 'PI']), spin=True,
              driver=dict(kind='thread', pitch=pitch))
        body(s, f'form_{aid}_screw', 'world')
    if hdr['stepped']:
        # The blow shakes the assembly, not only the arm: the rail sags under
        # the carriage and rings (the guide bars are rigid meshes, so they
        # carry the sag at mid-span; the carriage follows it at its own x),
        # and the gantry sways about the line through its plinth feet (a tilt
        # ACROSS the rail, about world x: the braces stiffen it along the rail).
        # The stand's thump, the sag and the sway all come off the recoil bus
        # the arm's own recoil does, and are exactly zero at the blow they
        # answer (formlab.rig.Rig._shudder, baked).
        r = j('rail', type='prismatic', axis=Y, value=_value(dict(channel=f'{aid}.sag')), driver=dict(kind='recoil'))
        body(r, f'{aid} rail*', 'world'); body(r, f'form_{aid}_rack', 'world', optional=True)
        ends = cfg.get('gantry', {}).get('ends', [])
        w = j('sway', type='revolute', axis=X,
              origin=dict(mean=[_vec([e['x_col'], e['foot_y'], e['mast_z']]) for e in ends]),
              value=_value(dict(channel=f'{aid}.sway')), driver=dict(kind='recoil'))
        body(w, f'form_{aid}_gantry', 'world', optional=True); body(w, f'form_{aid}_railhead', 'world', optional=True)
    return J, B

def mechanism_rows(mid, channels=()):
    """A mechanism's stand: it thumps vertically under its blows (the
    `<mid>.stand` channel; 0 when the bake has none)."""
    name = f'{mid}.stand'
    jt = _row(mid, 'stand', type='prismatic', axis=Y,
              value=_value(dict(channel=name) if name in channels else dict(const=0.0)), driver=dict(kind='stand'))
    return [jt], [_body(jt['id'], f'form_{mid}_stand', 'world', optional=True)]

def chamber_rows(geometry, bpm=BPM_DEFAULT):
    """The flywheel turns once a bar (the +x face turning down toward the
    house: a negative turn about z); the belt pulley turns with it, faster by
    the pulleys' radii, the same way round (an open belt). Their imported
    bases are the unspun home (spin bodies)."""
    fw = _row('chamber', 'flywheel', type='revolute', axis=Z,
              value=_value(dict(time=True), ['mul', '-TAU'], ['mul', float(bpm)], ['div', FLYWHEEL_DIV]), spin=True,
              driver=dict(kind='clock', per='bar'))
    ops = []
    if 'flywheel' in geometry:
        fw_g = geometry['flywheel']; cy = fw_g['cyls']
        ops = [['mul', [float(fw_g['wraps'][0][1]), float(fw_g['wraps'][1][1])]]] if 'wraps' in fw_g else [['mul', [float(cy['drive pulley'][2]), float(cy['belt pulley'][2])]]]
    bp = _row('chamber', 'belt_pulley', type='revolute', axis=Z, value=dict(src=dict(joint=fw['id']), ops=ops), spin=True,
              driver=dict(kind='belt', of=fw['id']))
    bodies = [_body(fw['id'], lab, 'spin', optional=True) for lab in ('Chamber flywheel', 'Chamber hub', 'Chamber drive pulley')]
    bodies.append(_body(bp['id'], 'Chamber belt pulley', 'spin', optional=True))
    return [fw, bp], bodies

def build(rig, arms_hdr, channels, bpm=BPM_DEFAULT):
    """dict(joints, bodies): every arm (in the header's order, rig.plans'),
    every manifest mechanism's stand, the chamber's wheels."""
    names = {c['name'] if isinstance(c, dict) else c for c in channels}
    J, B = [], []
    for aid in arms_hdr:
        j, b = arm_rows(rig, aid, arms_hdr[aid], names); J += j; B += b
    for mid in rig.geometry.get('mechanisms', {}):
        j, b = mechanism_rows(mid, names); J += j; B += b
    j, b = chamber_rows(rig.geometry, bpm); J += j; B += b
    return dict(joints=J, bodies=B)

# ------------------------------------------------------------------ q columns
def q_columns(rig, aid, values, times=None):
    """{'q.lean'?, 'q.shoulder', 'q.elbow'} float64 over the rows, from the
    arm's float64 poses (values: root, elbow, wrist (N,3)). Ruler 16's
    joint_series convention: shoulder = unwrap(atan2(u.y, u.z)) of the upper
    link u, elbow = rel (the forearm's minus the shoulder's). A mallet's links
    lie in the vertical plane through root and wrist, which leans psi =
    arctan(d.x/d.z) off the rail's (d = wrist - root): its angles are read in
    that plane (Ry(psi)^T u) and psi is its own column."""
    root = np.asarray(values['root'], float); elbow = np.asarray(values['elbow'], float); wrist = np.asarray(values['wrist'], float)
    if not rig.stepped(aid):
        js = R.joint_series(root, elbow, wrist)
        return {'q.shoulder': np.asarray(js['shoulder'], float), 'q.elbow': np.asarray(js['rel'], float)}
    d = wrist-root
    with np.errstate(divide='ignore', invalid='ignore'):
        psi = np.arctan(d[:, 0]/d[:, 2])
    bad = ~(np.abs(psi) <= LEAN_MAX)
    if bad.any():
        i = int(np.flatnonzero(bad)[0]); t = '' if times is None else f' at t={float(times[i]):.6f}'
        raise ValueError(f'formlab.bake: {aid} leans {float(psi[i]):.6g} rad out of its rail\'s plane{t} '
                         f'(LEAN_MAX {LEAN_MAX}): the joints table no longer describes the rig')
    c = np.cos(psi); s = np.sin(psi)
    def unlean(v): return np.c_[c*v[:, 0]-s*v[:, 2], v[:, 1], s*v[:, 0]+c*v[:, 2]]
    u = unlean(elbow-root); f = unlean(wrist-elbow)
    sh = np.unwrap(np.arctan2(u[:, 1], u[:, 2])); fa = np.unwrap(np.arctan2(f[:, 1], f[:, 2]))
    return {'q.lean': psi, 'q.shoulder': sh, 'q.elbow': fa-sh}

# ------------------------------------------------------------- the compiler
def _godot_fposmod(x, y):
    v = math.fmod(x, y)
    if (v < 0 and y > 0) or (v > 0 and y < 0): v += y
    return v+0.0

def _godot_wrapf(v, lo, hi):
    """Math::wrapf (double), with Godot's is_zero_approx / is_equal_approx."""
    rng = hi-lo
    if abs(rng) < CMP_EPSILON: return lo
    r = v-(rng*math.floor((v-lo)/rng))
    if r == hi: return lo
    tol = max(CMP_EPSILON*abs(r), CMP_EPSILON)
    return lo if abs(r-hi) < tol else r

def _vfposmod(x, y):
    v = np.fmod(x, y)
    v = np.where(((v < 0) & (y > 0)) | ((v > 0) & (y < 0)), v+y, v)
    return v+0.0

def _vwrapf(v, lo, hi):
    v, lo, hi = np.broadcast_arrays(np.asarray(v, float), np.asarray(lo, float), np.asarray(hi, float))
    rng = hi-lo
    with np.errstate(divide='ignore', invalid='ignore'):
        r = v-(rng*np.floor((v-lo)/rng))
    tol = np.maximum(CMP_EPSILON*np.abs(r), CMP_EPSILON)
    r = np.where((r == hi) | (np.abs(r-hi) < tol), lo, r)
    return np.where(np.abs(rng) < CMP_EPSILON, lo, r)

class Compiled:
    """A header's joints and bodies, validated (§2.9 of formlab/bake.py) and
    resolved into arrays in table order."""
    def __init__(self, header):
        kin = header.get('kinematics') or {}
        ver = kin.get('version', 1)
        if not isinstance(ver, (int, float)) or ver > KINEMATICS['version']:
            raise ValueError(f'formlab.kinematics: the bake\'s kinematics version {ver} is newer than this reader\'s '
                             f'(loam-motion/2 kinematics v{KINEMATICS["version"]}) — update formlab/kinematics.py')
        self.channels = {c['name']: (int(c['offset']), int(c['width'])) for c in header['channels']}
        pw = header['pawl']
        self.pawl_table = np.asarray(pw['table'], np.float32).astype(np.float64)   # a PackedFloat32Array in Godot
        self.pawl_table64 = np.asarray(pw['table'], np.float64)                  # the header's doubles (Bake.pawl_angle)
        self.pawl_pitch = float(pw['pitch'])
        ra = pw.get('ride_angle'); self.ride_angle = float('nan') if ra is None else float(ra)
        self.joints = list(header['joints']); self.ids = [jt['id'] for jt in self.joints]
        self.idx = {}
        n = len(self.joints)
        self.parent = [-1]*n; self.type = ['fixed']*n; self.axis = [None]*n; self.slot = [-1]*n
        self.origin64 = [None]*n; self.origin32 = [None]*n; self.ozero = [False]*n
        self.qhome = [0.0]*n; self.pin = [None]*n; self.pin_name = [None]*n
        self.aim = [None]*n; self.orient = [-1]*n; self.src = [None]*n; self.ops = [[] for _ in range(n)]
        for i, jt in enumerate(self.joints):
            jid = jt.get('id')
            if not isinstance(jid, str) or not jid: raise ValueError(f'formlab.kinematics: row {i} has no id')
            if jid in self.idx: raise ValueError(f'formlab.kinematics: joint {jid} is listed twice')
            self._compile(i, jt, jid)
            self.idx[jid] = i
        self.bodies = []
        for b in header.get('bodies', []):
            jid = b.get('joint')
            if jid not in self.idx: raise ValueError(f'formlab.kinematics: body {b.get("node")} is bound to joint {jid}, which the table lacks')
            mode = b.get('mode')
            if mode not in KINEMATICS['modes']:
                raise ValueError(self._unknown(jid, 'mode', mode))
            i = self.idx[jid]
            if mode == 'world' and self.parent[i] >= 0:
                raise ValueError(f'formlab.kinematics: joint {jid} has a world body ({b.get("node")}) but is not a root joint')
            self.bodies.append(dict(joint=i, node=str(b['node']), mode=mode, optional=bool(b.get('optional', False))))
        self.finish_aims()

    @staticmethod
    def _unknown(jid, what, name):
        return (f"formlab.kinematics: joint {jid} uses {what} '{name}' this reader does not know "
                f"(loam-motion/2 kinematics v{KINEMATICS['version']}) — update formlab/kinematics.py")

    def _earlier(self, jid, ref, role):
        if ref not in self.idx:
            raise ValueError(f'formlab.kinematics: joint {jid}\'s {role} {ref} is not an earlier joint of the table')
        return self.idx[ref]

    def _channel(self, jid, name, width, role):
        if name not in self.channels:
            raise ValueError(f'formlab.kinematics: joint {jid}\'s {role} reads channel {name}, which the bake lacks')
        off, w = self.channels[name]
        if (w < 1) if width == 'any' else (w != width):
            raise ValueError(f'formlab.kinematics: joint {jid}\'s {role} reads channel {name} of width {w}, not {width}')
        return off

    def _operand(self, jid, x):
        if isinstance(x, bool): raise ValueError(f'formlab.kinematics: joint {jid} has an operand {x!r} that is not a number')
        if isinstance(x, (int, float)): return ('num', float(x))
        if isinstance(x, str):
            if x not in SYMBOLS: raise ValueError(self._unknown(jid, 'symbol', x))
            return ('num', SYMBOLS[x])
        if isinstance(x, list) and len(x) == 2 and all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in x):
            return ('num', float(x[0])/float(x[1]))
        if isinstance(x, dict) and set(x) == {'joint'}: return ('joint', self._earlier(jid, x['joint'], 'operand'))
        if isinstance(x, dict) and set(x) == {'channel'}: return ('channel', self._channel(jid, x['channel'], 1, 'operand'))
        raise ValueError(f'formlab.kinematics: joint {jid} has an operand {x!r} this reader does not know '
                         f'(loam-motion/2 kinematics v{KINEMATICS["version"]}) — update formlab/kinematics.py')

    def _compile(self, i, jt, jid):
        typ = jt.get('type')
        if typ not in KINEMATICS['types']: raise ValueError(self._unknown(jid, 'type', typ))
        self.type[i] = typ
        par = jt.get('parent')
        self.parent[i] = -1 if par is None else self._earlier(jid, par, 'parent')
        ax = jt.get('axis')
        if typ != 'fixed':
            if not (isinstance(ax, list) and len(ax) == 3): raise ValueError(f'formlab.kinematics: joint {jid} ({typ}) has no axis')
            self.axis[i] = np.array([float(v) for v in ax])
            n = math.sqrt(sum(float(v)*float(v) for v in ax))
            if not abs(n-1.0) <= AXIS_TOL:      # Godot's Basis(axis, angle) takes a unit axis (another: an error and identity)
                raise ValueError(f'formlab.kinematics: joint {jid} has a non-unit axis {ax} (|axis| {n:.9g}): an axis is a '
                                 f'unit vector in the parent frame')
            nz = [k for k in range(3) if float(ax[k]) != 0.0]
            self.slot[i] = nz[0] if len(nz) == 1 and float(ax[nz[0]]) == 1.0 else -1
        o = jt.get('origin', [0.0, 0.0, 0.0])
        if isinstance(o, dict):
            if set(o) != {'mean'}: raise ValueError(f'formlab.kinematics: joint {jid} has an origin {sorted(o)} this reader does not know')
            if self.parent[i] >= 0: raise ValueError(f'formlab.kinematics: joint {jid} has a {{"mean"}} origin but is not a root joint')
            ends = [[float(v) for v in e] for e in o['mean']]
            # performance.gd's M2 pivot: accumulated in float32, divided in float32
            pv = np.zeros(3, np.float32)
            for e in ends: pv = (pv+np.asarray(e, np.float32)).astype(np.float32)
            if ends: pv = (pv/np.float32(len(ends))).astype(np.float32)
            self.origin32[i] = pv.astype(np.float64)
            self.origin64[i] = np.mean(np.asarray(ends, float), axis=0) if ends else np.zeros(3)
            self.ozero[i] = False
        else:
            self.origin64[i] = np.array([float(v) for v in o])
            self.origin32[i] = self.origin64[i].astype(np.float32).astype(np.float64)
            self.ozero[i] = all(float(v) == 0.0 for v in o)
        self.qhome[i] = float(jt.get('q_home', 0.0))
        pose = jt.get('pose') or {}
        if pose.get('pin'):
            self.pin[i] = self._channel(jid, pose['pin'], 3, 'pin'); self.pin_name[i] = pose['pin']
        if pose.get('orient'): self.orient[i] = self._earlier(jid, pose['orient'], 'orient')
        if pose.get('aim'):
            a = pose['aim']; tgt = a['joint']
            self.aim[i] = [tgt, np.array([float(v) for v in a.get('ref', AIM_REF)]),
                           np.array([float(v) for v in a.get('fallback', AIM_FALLBACK)])]
        val = jt.get('value')
        if val is None: return
        src = val.get('src') or {}
        if 'channel' in src and set(src) <= {'channel', 'index'}:
            if 'index' in src:
                k = int(src['index']); off = self._channel(jid, src['channel'], 'any', 'source')
                if k < 0 or k >= self.channels[src['channel']][1]:
                    raise ValueError(f'formlab.kinematics: joint {jid}\'s source reads component {k} of {src["channel"]}, '
                                     f'which has width {self.channels[src["channel"]][1]}')
                self.src[i] = ('index', off+k)
            else:
                self.src[i] = ('channel', self._channel(jid, src['channel'], 1, 'source'))
        elif set(src) == {'joint'}: self.src[i] = ('joint', self._earlier(jid, src['joint'], 'source'))
        elif set(src) == {'time'}: self.src[i] = ('time',)
        elif set(src) == {'const'}: self.src[i] = ('const', float(src['const']))
        else: raise ValueError(self._unknown(jid, 'source', '/'.join(sorted(src)) or 'none'))
        for op in val.get('ops', []):
            if not isinstance(op, list) or not op or op[0] not in KINEMATICS['ops']:
                raise ValueError(self._unknown(jid, 'op', op[0] if isinstance(op, list) and op else op))
            k = op[0]
            if k in ('add', 'mul', 'div'):
                if len(op) != 2: raise ValueError(f'formlab.kinematics: joint {jid}\'s op {op!r} takes one operand')
                self.ops[i].append((k, self._operand(jid, op[1])))
            elif k == 'neg': self.ops[i].append(('neg',))
            elif k == 'wrap':
                if len(op) != 3: raise ValueError(f'formlab.kinematics: joint {jid}\'s op {op!r} takes two operands')
                self.ops[i].append(('wrap', self._operand(jid, op[1]), self._operand(jid, op[2])))
            elif k == 'pawl':
                if len(op) != 2: raise ValueError(f'formlab.kinematics: joint {jid}\'s op {op!r} takes one channel or null')
                self.ops[i].append(('pawl', None if op[1] is None else self._channel(jid, op[1], 1, 'pawl ride')))
            elif k == 'table':
                tb = op[1] if len(op) == 2 and isinstance(op[1], dict) else {}
                x = np.array([float(v) for v in tb.get('x', [])]); y = np.array([float(v) for v in tb.get('y', [])])
                per = tb.get('period')
                if len(x) < 2 or len(x) != len(y) or np.any(np.diff(x) <= 0) or (per is not None and float(per) <= 0):
                    raise ValueError(f'formlab.kinematics: joint {jid}\'s table op needs increasing x and y of one length (>= 2) and a positive period or null')
                self.ops[i].append(('table', x, y, None if per is None else float(per)))

    def finish_aims(self):
        """Aim targets: pinned, or earlier in the table (checked once every id is known)."""
        for i, a in enumerate(self.aim):
            if a is None or isinstance(a[0], int): continue
            tgt = a[0]; jid = self.ids[i]
            if tgt not in self.idx: raise ValueError(f'formlab.kinematics: joint {jid} aims at {tgt}, which the table lacks')
            ti = self.idx[tgt]
            if ti >= i and self.pin[ti] is None:
                raise ValueError(f'formlab.kinematics: joint {jid} aims at {tgt}, which is neither pinned nor earlier in the table')
            a[0] = ti

def compile(header):
    """The header's table, validated: every message names the joint."""
    return Compiled(header)

# ------------------------------------------------------- vectorized (writer)
def _rows_operand(C, opd, Q, cols):
    k = opd[0]
    if k == 'num': return opd[1]
    if k == 'joint': return Q[opd[1]]
    return cols[:, opd[1]]

def value_rows(C, frames, times, godot=True):
    """{id: q (N,)} over the rows: `frames` (N, width) float64, the bake's
    columns (the stored float32 widened, or the writer's float64 values).
    godot: a component source is read as Godot's Vector3 holds it (float32)
    and a pawl op reads the float32 table; else both stay double."""
    frames = np.asarray(frames, np.float64); times = np.asarray(times, np.float64); N = len(times)
    Q = []
    for i in range(len(C.ids)):
        s = C.src[i]
        if s is None: q = np.zeros(N)
        elif s[0] == 'channel': q = frames[:, s[1]].copy()
        elif s[0] == 'index':
            q = frames[:, s[1]].copy()
            if godot: q = q.astype(np.float32).astype(np.float64)
        elif s[0] == 'joint': q = Q[s[1]].copy()
        elif s[0] == 'time': q = times.copy()
        else: q = np.full(N, s[1])
        for op in C.ops[i]:
            k = op[0]
            if k == 'add': q = q+_rows_operand(C, op[1], Q, frames)
            elif k == 'mul': q = q*_rows_operand(C, op[1], Q, frames)
            elif k == 'div': q = q/_rows_operand(C, op[1], Q, frames)
            elif k == 'neg': q = -q
            elif k == 'wrap':
                lo = _rows_operand(C, op[1], Q, frames); hi = _rows_operand(C, op[2], Q, frames)
                q = _vwrapf(q, lo, hi)
            elif k == 'pawl':
                ride = np.zeros(N) if op[1] is None else frames[:, op[1]]
                q = _vpawl(C, q, ride, godot)
            elif k == 'table': q = _vtable(op, q)
        Q.append(q)
    return {jid: Q[i] for i, jid in enumerate(C.ids)}

def _vpawl(C, x, ride, godot=True):
    """The pawl op over the rows: the one-tooth table looked up periodically
    (fposmod) and lerped, leaned toward ride_angle by `ride`. godot: the table
    as the harness holds it (float32); else the header's doubles."""
    tab = C.pawl_table if godot else C.pawl_table64; n = len(tab); p = C.pawl_pitch
    u = _vfposmod(x, p)/p*n; fl = np.floor(u); k = fl.astype(np.int64); w = u-fl
    a0 = tab[k % n]; a1 = tab[(k+1) % n]; a = a0+(a1-a0)*w
    ra = a if math.isnan(C.ride_angle) else C.ride_angle
    return np.where(ride == 0.0, a, a+(ra-a)*ride)

def _vtable(op, q):
    _, x, y, per = op
    q = np.asarray(q, float)
    q = x[0]+_vfposmod(q-x[0], per) if per is not None else np.clip(q, x[0], x[-1])
    k = np.clip(np.searchsorted(x, q, 'left'), 1, len(x)-1)
    w = (q-x[k-1])/(x[k]-x[k-1])
    return y[k-1]+(y[k]-y[k-1])*w

def _vrot(axis, ang):
    """(N,3,3) Basis::set_axis_angle rows, in double."""
    x, y, z = (float(v) for v in axis)
    c = np.cos(ang); s = np.sin(ang); t = 1.0-c
    N = len(ang); M = np.empty((N, 3, 3))
    M[:, 0, 0] = x*x+c*(1.0-x*x); M[:, 1, 1] = y*y+c*(1.0-y*y); M[:, 2, 2] = z*z+c*(1.0-z*z)
    a = x*y*t; b = z*s; M[:, 0, 1] = a-b; M[:, 1, 0] = a+b
    a = x*z*t; b = y*s; M[:, 0, 2] = a+b; M[:, 2, 0] = a-b
    a = y*z*t; b = x*s; M[:, 1, 2] = a-b; M[:, 2, 1] = a+b
    return M

def _slide(C, i, qq):
    S = np.zeros((len(qq), 3))
    if C.slot[i] >= 0: S[:, C.slot[i]] = qq
    else: S = qq[:, None]*C.axis[i][None, :]
    return S

def fk_rows(C, frames, times, ids=None, godot=False, chunk=4096):
    """FK mode (pose ignored: the chain rule from the q values) at the rows,
    in double: {id: (P (N,3), B (N,3,3))} for `ids` (default: the pinned joints)."""
    frames = np.asarray(frames, np.float64); times = np.asarray(times, np.float64); N = len(times)
    want = ([i for i in range(len(C.ids)) if C.pin[i] is not None
             and (C.type[i] != 'fixed' or not C.joints[i]['owner'].startswith(('bars_', 'bells_', 'blocks_', 'harp_')))]
            if ids is None else [C.idx[j] for j in ids])
    out = {C.ids[i]: (np.empty((N, 3)), np.empty((N, 3, 3))) for i in want}
    for lo in range(0, N, chunk):
        hi = min(N, lo+chunk); fr = frames[lo:hi]; n = hi-lo
        Q = value_rows(C, fr, times[lo:hi], godot=godot)
        P = [None]*len(C.ids); B = [None]*len(C.ids)
        eye = np.broadcast_to(np.eye(3), (n, 3, 3))
        for i, jid in enumerate(C.ids):
            par = C.parent[i]; typ = C.type[i]
            Pp, Bp = (np.zeros((n, 3)), eye) if par < 0 else (P[par], B[par])
            qq = Q[jid]-C.qhome[i]
            O = C.origin64[i][None, :]
            OS = O+_slide(C, i, qq) if typ == 'prismatic' else np.broadcast_to(O, (n, 3))
            P[i] = Pp+np.einsum('nij,nj->ni', Bp, OS)
            B[i] = np.einsum('nij,njk->nik', Bp, _vrot(C.axis[i], qq)) if typ == 'revolute' else Bp
        for i in want: out[C.ids[i]][0][lo:hi] = P[i]; out[C.ids[i]][1][lo:hi] = B[i]
    return out

def fk_check(C, frames, times, tol=FK_TOL, godot=False):
    """FK of the table reproduces every pinned joint's channel on every row
    within `tol`; raises ValueError naming the arm, the pin, the error, the
    time and the joint. Returns (worst error, joint id, t)."""
    fk = fk_rows(C, frames, times, godot=godot)
    frames = np.asarray(frames, np.float64)
    worst = (0.0, None, None)
    for jid, (P, _) in fk.items():
        i = C.idx[jid]; off = C.pin[i]
        err = np.linalg.norm(P-frames[:, off:off+3], axis=1); k = int(np.argmax(err)); e = float(err[k])
        if not e <= tol:
            raise ValueError(f'formlab.bake: {C.joints[i]["owner"]} FK misses {C.pin_name[i]} by {e:.3g} m at '
                             f't={float(times[k]):.6f} (joint {jid}): the joints table no longer describes the rig')
        if e >= worst[0]: worst = (e, jid, float(times[k]))
    return worst

# ---------------------------------------------- the mirror (T9, T10: one t)
def _f32(v): return np.asarray(v, np.float32).astype(np.float64)

def _rot(axis, ang):
    """Basis(axis, angle): the angle is a real_t (float32) in Godot."""
    a = float(np.float32(ang)); x, y, z = (float(v) for v in axis)
    c = math.cos(a); s = math.sin(a); t = 1.0-c
    M = np.empty((3, 3))
    M[0, 0] = x*x+c*(1.0-x*x); M[1, 1] = y*y+c*(1.0-y*y); M[2, 2] = z*z+c*(1.0-z*z)
    p = x*y*t; r = z*s; M[0, 1] = p-r; M[1, 0] = p+r
    p = x*z*t; r = y*s; M[0, 2] = p+r; M[2, 0] = p-r
    p = y*z*t; r = x*s; M[1, 2] = p-r; M[2, 1] = p+r
    return M

def _normalized(v):
    l2 = float(v@v)
    return np.zeros(3) if l2 == 0.0 else v/math.sqrt(l2)

def link_basis(a, b, axis=AIM_REF, fallback=AIM_FALLBACK):
    """MotionBake.link_basis: y along a->b, x the axis projected off y (the
    fallback when they are parallel), z = x × y. Columns x, y, z."""
    y = _normalized(np.asarray(b, float)-np.asarray(a, float)); axis = np.asarray(axis, float)
    x = axis-y*float(y@axis)
    if float(x@x) < .000001: x = np.asarray(fallback, float)
    x = _normalized(x)
    return np.column_stack([x, y, np.cross(x, y)])

def _pawl1(C, x, ride):
    tab = C.pawl_table; n = len(tab)
    u = _godot_fposmod(x, C.pawl_pitch)/C.pawl_pitch*n; k = int(math.floor(u)); w = u-math.floor(u)
    a0 = float(tab[k % n]); a = a0+(float(tab[(k+1) % n])-a0)*w
    if ride == 0.0: return a
    return a+((a if math.isnan(C.ride_angle) else C.ride_angle)-a)*ride

def _table1(op, q):
    _, x, y, per = op
    q = float(x[0]+_godot_fposmod(q-x[0], per)) if per is not None else min(max(q, float(x[0])), float(x[-1]))
    k = min(max(int(np.searchsorted(x, q, 'left')), 1), len(x)-1)
    w = (q-float(x[k-1]))/(float(x[k])-float(x[k-1]))
    return float(y[k-1])+(float(y[k])-float(y[k-1]))*w

def evaluate(C, row, t, fk=False):
    """§2.7's evaluator at one t, mirroring Godot's arithmetic where it moves
    a value past the parity tolerances (§7.3): `row` is the bake's row at t as
    Godot's _at reads it (Bake.row_godot); a component source and every pin is
    float32 (a Vector3); a pawl op reads the float32 table; wrap is Godot's
    wrapf; every Basis angle is truncated to float32; origins (and a {"mean"}
    pivot) are float32. Sums and products are double on those inputs.
    Returns {id: (P (3,), B (3,3) columns x y z, q, ident)}."""
    row = np.asarray(row, np.float64)
    n = len(C.ids); P = [None]*n; B = [None]*n; I = [True]*n; Q = [0.0]*n
    def opnd(o):
        if o[0] == 'num': return o[1]
        if o[0] == 'joint': return Q[o[1]]
        return float(row[o[1]])
    def pin_at(k): return _f32(row[C.pin[k]:C.pin[k]+3])
    for i in range(n):
        s = C.src[i]
        if s is None: q = 0.0
        elif s[0] == 'channel': q = float(row[s[1]])
        elif s[0] == 'index': q = float(np.float32(row[s[1]]))
        elif s[0] == 'joint': q = Q[s[1]]
        elif s[0] == 'time': q = float(t)
        else: q = s[1]
        for op in C.ops[i]:
            k = op[0]
            if k == 'add': q = q+opnd(op[1])
            elif k == 'mul': q = q*opnd(op[1])
            elif k == 'div': q = q/opnd(op[1])
            elif k == 'neg': q = -q
            elif k == 'wrap': q = _godot_wrapf(q, opnd(op[1]), opnd(op[2]))
            elif k == 'pawl': q = _pawl1(C, q, 0.0 if op[1] is None else float(row[op[1]]))
            elif k == 'table': q = _table1(op, q)
        Q[i] = q; qq = q-C.qhome[i]
        par = C.parent[i]; typ = C.type[i]
        Pp, Bp, Ip = (np.zeros(3), np.eye(3), True) if par < 0 else (P[par], B[par], I[par])
        O = C.origin32[i]
        if typ == 'prismatic':
            S = np.zeros(3)
            if C.slot[i] >= 0: S[C.slot[i]] = float(np.float32(qq))
            else: S = _f32(C.axis[i]*float(np.float32(qq)))
            OS = O+S
        else: OS = O
        if not fk and C.pin[i] is not None: Pos = pin_at(i)
        elif par < 0: Pos = OS.copy()
        elif typ != 'prismatic' and C.ozero[i]: Pos = Pp
        elif Ip: Pos = Pp+OS
        else: Pos = Pp+Bp@OS
        if not fk and C.orient[i] >= 0: Bs, Is = B[C.orient[i]], I[C.orient[i]]
        elif not fk and C.aim[i] is not None:
            ti, ref, fb = C.aim[i]
            tgt = pin_at(ti) if C.pin[ti] is not None else P[ti]
            Bs, Is = link_basis(Pos, tgt, ref if Ip else Bp@ref, fb), False
        elif typ == 'revolute':
            Rm = _rot(C.axis[i], qq); Bs, Is = (Rm if Ip else Bp@Rm), False
        else: Bs, Is = Bp, Ip
        P[i] = Pos; B[i] = Bs; I[i] = Is
    return {jid: (P[i], B[i], Q[i], I[i]) for i, jid in enumerate(C.ids)}

# ------------------------------------------------------- declared structure
def json_safe(o, path='$'):
    """JSON-safe: numpy -> python, tuples -> lists, sets -> sorted lists,
    +-inf -> None (a bound), NaN -> ValueError naming the key path."""
    if isinstance(o, dict): return {str(k): json_safe(v, f'{path}.{k}') for k, v in o.items()}
    if isinstance(o, np.ndarray): o = o.tolist()
    if isinstance(o, (set, frozenset)): o = sorted(o)
    if isinstance(o, (list, tuple)): return [json_safe(v, f'{path}[{i}]') for i, v in enumerate(o)]
    if isinstance(o, (bool, np.bool_)): return bool(o)
    if isinstance(o, (int, np.integer)): return int(o)
    if isinstance(o, (float, np.floating)):
        o = float(o)
        if math.isnan(o): raise ValueError(f'formlab.kinematics: NaN at {path}')
        return o if math.isfinite(o) else None
    if o is None or isinstance(o, str): return o
    raise TypeError(f'formlab.kinematics: {type(o).__name__} at {path} is not JSON')

def _fn_name(fn):
    name = f'{getattr(fn, "__module__", "") or ""}.{getattr(fn, "__qualname__", getattr(fn, "__name__", "prep"))}'
    if name.startswith('.'): name = name[1:]
    return name if name.startswith('formlab.') else 'formlab.'+name

def prep_table(fn):
    """The prep function sampled: h[i][j] = fn(a[i], ioi[j]) on PREP_A x
    PREP_IOI, h_first[i] = fn(a[i], None) (a first note). None for none."""
    if fn is None: return None
    return dict(fn=_fn_name(fn), a=[float(a) for a in PREP_A], ioi=[float(i) for i in PREP_IOI],
                h=[[float(fn(float(a), float(i))) for i in PREP_IOI] for a in PREP_A],
                h_first=[float(fn(float(a), None)) for a in PREP_A])

def declared_block(rig, aid):
    """rig.declared(aid) serialized (formlab.segments.Declared): segments,
    knots, rings, the prep table, native."""
    d = SEG.declared(rig, aid)
    return dict(native=bool(d.native),
                segments=[dict(t0=g.t0, t1=g.t1, law=g.law, tag=g.tag, event=g.event, extra=g.extra) for g in d.segments],
                knots=[dict(t=k.t, kind=k.kind, dv=k.dv, event=k.event, extra=k.extra) for k in d.knots],
                rings=list(d.rings), prep=prep_table(d.prep))

def declared_vocab():
    """formlab/segments.py's vocabularies, sorted."""
    return dict(tags=sorted(SEG.TAGS), knot_kinds=sorted(SEG.KNOT_KINDS), impulses=sorted(SEG.IMPULSES),
                laws=sorted(SEG.LAWS), channels=sorted(SEG.CHANNELS), hold_kinds=sorted(SEG.HOLD_KINDS),
                regimes=sorted(SEG.REGIMES))

def prep_interp(p):
    """A header prep table as a function h(a, ioi): bilinear in (a, log ioi),
    clamped to the grid; ioi None or inf reads h_first. a None counts as 1.0."""
    if p is None: return None
    A = np.asarray(p['a'], float); L = np.log(np.asarray(p['ioi'], float))
    H = np.asarray(p['h'], float); HF = np.asarray(p['h_first'], float)
    def h(a, ioi):
        a = min(max(1.0 if a is None else float(a), A[0]), A[-1])
        if ioi is None or not math.isfinite(float(ioi)): return float(np.interp(a, A, HF))
        li = min(max(math.log(max(float(ioi), 1e-300)), L[0]), L[-1])
        return float(np.interp(a, A, [np.interp(li, L, H[k]) for k in range(len(A))]))
    h.table = p
    return h

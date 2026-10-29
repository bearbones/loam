"""The performance baked: `loam-motion/2`, the rig's every moving value sampled
over the piece and the joints table that turns those values into the
machine's parts, so a game engine plays the machine back without owning its
motion vocabulary (docs/chamber-spec.md: "Godot becomes a pure playback
engine").

    python3 tools/bake_motion.py [--asset=clockwork] [--hz=240] [--score=PATH]

`formlab.rig.Rig` is the one implementation of the motion: the planner's
costs (loam/motion_timing.py), the two vocabularies, the recoil bus, the IK.
Its poses are sampled here and written next to the score as

    <asset>.motion.json   the header: format, fingerprints, channels, per-arm
                          records (clicks, blows, head_l, joints, declared
                          structure), per-mechanism records, the pawl's angle
                          over one tooth, and the joints and bodies tables
    <asset>.motion.bin    little-endian: N float64 times, then N rows of W
                          float32 channel values (row-major)

The time grid is uniform at `hz` plus every instant the path turns a corner
exactly on, so linear interpolation between rows lands every contact exactly
and never rounds off a boundary:
  - an arm with a stroke (a mallet, PLAYERS M1, formlab/stroke.py; a pick or
    the rake, M2, formlab/servo.py and formlab/rake.py): every knot and every
    segment boundary the arm declares (Rig.declared: each contact, a mallet's
    step start and its landing on the detent, the apex, the park, the cocked
    or poised hold, a rake's roll knots, each homing leg) and every hit;
  - every other arm (the hinged hammer, a pick's multi-string event): each
    contact, each move's start and landing, each release, and for the hammer
    rows packed through every ratchet click (a tooth in ~16 ms).
Rows closer than MERGE_S are one row: a hit's time wins, then a declared
knot's. Before the first row and after the last a reader holds the end row.

COLUMNS. Per arm (rig.plans order) root, elbow, wrist, tip (3 each), head,
sag, sway (+ ride on a stepped arm); then each mechanism's stand; then, new in
/2 and appended so every /1 column keeps its name, offset and float32 bits,
per arm in rig.plans order: `<aid>.q.lean` (a mallet only), `<aid>.q.shoulder`
and `<aid>.q.elbow`, each record carrying `"joint"`, the row that reads it.
The q columns are ruler 16's joint_series: shoulder = unwrap(atan2(u.y, u.z))
of the upper link u = elbow - root, elbow = the forearm's angle minus the
shoulder's. A mallet's carriage stands at carriage_x, off the tip's x, so its
links lie in the vertical plane through root and wrist, which leans psi =
arctan(d.x/d.z) (d = wrist - root, |psi| <= kinematics.LEAN_MAX) off the rail's:
its angles are read in that plane and psi is `q.lean`.

Each arm's record carries, besides what it is (kind, mech, stepped, hammer,
flip_sign, rail_span, pawl_phase, unreachable):
    clicks       [[t, teeth]] in time order, when the ratchet sounds. A mallet
                 clicks a tooth (teeth 1.0): a freewheel where x crosses
                 mid-tooth, a stepped or homing travel at each landing. The
                 hammer clicks a ratchet click (teeth = what it spanned).
    click_pawl   parallel to clicks: 0 the pawl drops into the tooth, 1 it
                 rides the tips (the tooth rate |x'|/PITCH is at least
                 constants.PAWL_RIDE there). The hammer's always drop.
    click_step   parallel to clicks: 1 a stepped (or homing) landing, 0 a
                 freewheel's crossing. The hammer's are all 1.
    blows        [{t, gate_end, x, energy}] a blow, gate_end the time the
                 arm's next stroke starts (a mallet's next apex; null for the
                 last). A mallet's also carry v_in (the downstroke's speed at
                 the contact, m/s) and e (the rebound's restitution).
    head_l       the hinged head's pin above the tool frame (rig.HAMMER
                 head_l; on every arm, so a camera has a number to aim at)
    joints       the arm's rows of the joints table, in table order
    declared     Rig.declared(aid) serialized: native, segments [{t0, t1,
                 law, tag, event, extra}] (t0/t1 null = -/+inf), knots [{t,
                 kind, dv, event, extra}], rings, and prep (the declared prep
                 function sampled: fn, a (9), ioi (64, geometric 0.02-8 s),
                 h[a][ioi], h_first[a] for a first note) or null.
Each mechanism's: blows (a count) and joints (its stand). `declared_vocab`
lists formlab/segments.py's vocabularies.

The pawl's angle as the carriage crosses a tooth is NOT a time channel. It is
a function of where the carriage is on the rack, periodic in the tooth pitch
(formlab.pawl.angle), and its lift over a tooth tip lasts a few milliseconds
of a hurried click — shorter than a sample. So the header carries one tooth of
it (`pawl.table`) and a reader looks it up at the baked carriage x plus the
arm's phase: exact at any frame rate. Whether the pawl drops into each gap or
rides the tips IS a time channel: a stepped arm's `<aid>.ride` in [0, 1] (a
mallet's formlab.stroke pawl_ride, a smoothstep of the tooth rate around
PAWL_RIDE; the hammer's is 0), and a reader leans the table's angle toward
`pawl.ride_angle` (the table's least angle: the nose landed on a tip) by it
(Bake.pawl_angle).

THE JOINTS TABLE (formlab/kinematics.py builds it). `joints` is a list in
evaluation order; each row holds every field, in this order:
    id "<owner>/<name>" (owner an aid, a mechanism id or "chamber"), owner,
    name, parent (an EARLIER id, or null: the world), type (revolute |
    prismatic | fixed), axis (unit, in the parent frame; null for fixed),
    origin (in the parent frame; a root joint may give {"mean": [[x,y,z],..]}:
    the pivot accumulated in float32 and divided by the count), q_home (the q
    the mesh was built at; 0.0 throughout M3), value ({"src", "ops"}, null
    for fixed: q = 0), spin (descriptive: an unbounded angle; no reader wraps
    implicitly), unit (rad | m | null), limits (null until M4), range (the
    observed [min, max] of q over the rows), driver (informational), pose
    ({"pin": a width-3 channel | null, "aim": {"joint", "ref", "fallback"} |
    null, "orient": an earlier id | null} | null), extra ({"length"} on an
    aimed link, {"closes": {"joint", "offset", "length"}} on a parallel bar).
  value: q = src, then each op in order, in double.
    src  {"channel": C} a width-1 channel (the reader's interpolated value);
         {"channel": C, "index": i} component i of a vector channel AS A
         Vector3 HOLDS IT (float32, widened); {"joint": id} an earlier joint's
         q; {"time": true} t; {"const": x} x.
    ops  ["add"|"mul"|"div", operand], ["neg"], ["wrap", lo, hi] (Godot's
         wrapf), ["pawl", "<aid>.ride" | null] (Bake.pawl_angle of q, ridden
         by the channel), ["table", {"x", "y", "period"|null}] (piecewise-
         linear in double; periodic, or clamped to [x0, xn]).
    operand  a number; "TAU", "-TAU", "PI", "-PI", "PI/2"; a ratio [num, den]
         (num/den in double, once at load); {"joint": id}; {"channel": C}.
  bodies: [{joint, node, mode, optional, mass, com, inertia}] (mass, com,
    inertia null until M4). node is a GLB node name, or a pattern with `*`
    (every match). optional: a missing node is skipped; a missing required
    node refuses to bind. Every node is bound at most once. With the joint's
    frame (P, B, ident) and `home` the node's imported transform:
      frame  node.transform = Transform3D(B, P)
      rest   node.position = P; then, unless ident, node.basis = B * home.basis
      spin   node.basis = B * home.basis
      world  (root joints only) revolute: Transform3D(B, P - B*P) * home;
             prismatic: Transform3D(home.basis, home.origin + S)
  THE EVALUATOR (both readers implement exactly this; S is q - q_home in the
  axis's slot, Vector3(q,0,0) / (0,q,0) / (0,0,q), or axis*q off-axis):
    for each joint in table order, with the parent's frame (P, B, ident), or
    (ZERO, IDENTITY, true) at the root:
      position: a pin (pose mode)        -> the pin channel's Vector3
                a root joint             -> origin (+ S if prismatic)
                a revolute or fixed joint with a zero origin -> the parent's P
                an identity parent       -> P + (origin + S)
                else                     -> P + B * (origin + S)
      basis:    an orient (pose mode)    -> that joint's (B, ident)
                an aim (pose mode)       -> (link_basis(P, the target's pin or
                                             P, ident ? ref : B*ref, fallback), false)
                revolute                 -> (ident ? R : B*R, false),
                                            R = Basis(axis, q - q_home)
                prismatic, fixed         -> the parent's (B, ident)
  POSE mode (pins, aims, orients) is what renders: it is the M2 harness's
  poser as data, bit for bit (harness/dev/test_pose_parity.gd). FK mode
  ignores `pose`: the chain rule from the q values. The writer checks FK
  reproduces every pin (the carriage's root, the elbow and wrist crossheads,
  the tool) on every row within kinematics.FK_TOL, or refuses to write.
  `kinematics` lists the v1 vocabulary (types, sources, ops, symbols, modes,
  drivers); a reader refuses a version above its own, any row that uses a
  type, source, op, symbol or mode it does not know, and a revolute or
  prismatic axis that is not a unit vector (within kinematics.AXIS_TOL),
  naming the joint.

Adding a joint: add its rows in formlab/kinematics.py (and a `<aid>.q.<name>`
column here only for an angle with a law of its own per row). A new joint, a
new channel, a new driver kind or a new metadata key is not a format change:
readers find channels by name and ignore unknown keys, and the harness binds
and poses a new body with no code change. A new op, source, type or mode
bumps kinematics.version and is implemented in both readers.
tools/test_bake.py holds the table to the rig row by row, so a new row adds
what it must be there: its structure to T4 (expected_rows, and a new node
name to the body vocabulary), its law to T6, a new column to T2
(docs/clockwork-build.md, "Adding a joint").

The header's fingerprints (sha256 of the score.json and the manifest bytes)
are what a reader checks before it trusts the bake: a rebuilt model or a
re-exported score makes it stale, and a stale bake is refused rather than
played. An older format (`loam-motion/1`) is refused with the command that
remakes it. Everything here is numpy-only so Blender can run it at the end of
tools/build_clockwork.py.
"""
import hashlib, json
from pathlib import Path
import numpy as np
from . import rig as R
from . import pawl as P
from . import kinematics as J
from . import segments as SEG

FORMAT = 'loam-motion/2'
# Each asset's score, relative to the tree's root (r_notes.EXPANDED_SCORE and
# ScoreDoc.default_path agree): a manifest's own "score" is the absolute path
# it was built from, which in a copied tree is another tree's.
DEFAULT_SCORES = {'clockwork': 'render/chamber/score.json', 'clockwork_expanded': 'render/clockwork/score.json'}
# A hinged hammer's felt face is not a channel: it is the tip plus the head's
# offset at the baked angle (formlab.rig.head_offset), so the head a player
# renders and the face it strikes with cannot drift apart between rows.
ARM_CHANNELS = [('root', 3), ('elbow', 3), ('wrist', 3), ('tip', 3), ('head', 1), ('sag', 1), ('sway', 1)]
# a stepped arm's pawl riding the rack (0 drops into every gap, 1 rides the tips)
STEPPED_CHANNELS = [('ride', 1)]
MECH_CHANNELS = [('stand', 1)]
PAWL_TABLE_N = 1024
CLICK_SAMPLES = 8
MERGE_S = 1e-7       # rows closer than this are one row
# which time a merged row keeps: a hit's, then a stroke's declared knot or
# boundary, then a strokeless arm's schedule corner, then the grid's
_GRID, _CORNER, _KNOT, _HIT = 0, 1, 2, 3

def sha256(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def default_score(asset, root):
    """The asset's score in the tree at `root` (DEFAULT_SCORES); KeyError for
    an asset without one."""
    return Path(root)/DEFAULT_SCORES[asset]

def paths(score_path, asset):
    d = Path(score_path).resolve().parent
    return d/f'{asset}.motion.json', d/f'{asset}.motion.bin'

def _merge(times, prio, tol=MERGE_S):
    """One row per run of times closer than `tol` to their neighbour, at the
    run's highest-priority time (the earliest of equals)."""
    ok = np.isfinite(times); times = times[ok]; prio = prio[ok]
    order = np.lexsort((-prio, times)); t = times[order]; p = prio[order]
    cut = np.flatnonzero(np.diff(t) >= tol)+1
    return np.array([t[i+int(np.argmax(p[i:j]))] for i, j in zip(np.r_[0, cut], np.r_[cut, len(t)])])

def sample_times(rig, hz):
    """The uniform grid from one second before the piece to its end, plus the
    corners of every arm's path (see the module docstring): every declared
    knot and segment boundary of an arm with a stroke, every other arm's
    schedule corners (and the hammer's rows through each ratchet click),
    every hit."""
    total = float(rig.score['total_s'])
    T = [np.arange(-hz, int(np.ceil(total*hz))+1)/hz]; Pr = [np.full(len(T[0]), _GRID)]
    def add(ts, prio):
        ts = np.asarray(ts, float).ravel(); T.append(ts); Pr.append(np.full(len(ts), prio))
    for aid in rig.plans:
        sched = rig.schedule(aid)
        # every string's contact (a rake roll's at its own onsets: motion_timing.string_times)
        add([t for s in sched for t in R.motion_timing.string_times(s['event'])], _HIT)
        if rig.stroke(aid) is not None:
            # the stroke is closed form between its declared knots and
            # boundaries (a contact reverses the head's velocity, a stepped
            # landing starts the detent ring, a servo's piece changes law),
            # smooth everywhere else. A servo's schedule corners (the
            # planner's approach / end windows) are not corners of its
            # stroke; its pieces' bounds are (the poise hold, the rake's roll
            # knots, run-up and follow-through pieces of a few ms)
            d = rig.declared(aid)
            add([k.t for k in d.knots], _KNOT)
            add([t for g in d.segments for t in (g.t0, g.t1)], _KNOT)
            # ...and where the pawl's ride (a smoothstep of the tooth rate) bends (a servo: none)
            add(rig.stroke(aid).ride_times(), _GRID)
            continue
        corners = []
        for s in sched:
            corners += [s[key] for key in ('go', 'approach', 'hit', 'end', 't_free', 'tm')]
            # A ratchet click moves a tooth in CLICK_MOVE of 40-90 ms: far too
            # sharp a curve for the grid, so each click's move and the start of
            # its ring get CLICK_SAMPLES rows of their own.
            if rig.stepped(aid) and s['moving']:
                Tc = s['approach']-s['go']; n = R.clicks(s['first'][0]-s['rest'][0], Tc)
                corners += [s['go']+(k+R.CLICK_MOVE*1.5*j/CLICK_SAMPLES)*Tc/n
                            for k in range(n) for j in range(CLICK_SAMPLES+1)]
        add(corners, _CORNER)
    return _merge(np.concatenate(T), np.concatenate(Pr))

def arm_clicks(rig, aid):
    """(clicks [[t, teeth]], click_pawl [0 drop | 1 ride], click_step [1 stepped
    or homing | 0 freewheel]) in time order: a stepped arm's a tooth from its
    stroke."""
    st = rig.stroke(aid) if rig.stepped(aid) else None
    if st is not None:
        cs = st.clicks()
        clicks = [[float(c['t']), 1.0] for c in cs]
        if [c[0] for c in clicks] != [float(t) for t, _ in rig.click_times(aid)]:
            raise AssertionError(f'{aid}: the stroke\'s clicks are not Rig.click_times')
        return clicks, [int(c['pawl'] == 'ride') for c in cs], [int(c['step']) for c in cs]
    ct = rig.click_times(aid)
    return [[float(t), float(n)] for t, n in ct], [0]*len(ct), [1]*len(ct)

def arm_blows(rig, aid):
    """[{t, gate_end, x, energy}] a blow (gate_end None for the last); a
    stepped arm's also carry its stroke's v_in and e."""
    out = []
    for b in rig.blows_by_arm.get(aid, []):
        d = dict(t=b['t'], gate_end=(b['gate_end'] if np.isfinite(b['gate_end']) else None), x=b['x'], energy=b['energy'])
        d.update({k: float(b[k]) for k in ('v_in', 'e') if k in b})
        out.append(d)
    return out

def bake(score_path, manifest_path, asset=None, hz=240, verbose=print):
    score_path = Path(score_path).resolve(); manifest_path = Path(manifest_path).resolve()
    asset = asset or manifest_path.stem
    rig = R.Rig.load(score_path, manifest_path)
    times = sample_times(rig, hz)
    channels = []; columns = []
    arms = {}; by_arm = {}
    head_l = float(R.HAMMER['head_l'])
    for aid in rig.plans:
        cfg = rig.geometry['arms'][aid]
        poses = [rig.pose(aid, t) for t in times]
        lo, hi = rig.rail_span(aid); mid = (lo+hi)/2
        values = dict(
            root=np.array([p['root'] for p in poses]), elbow=np.array([p['elbow'] for p in poses]),
            wrist=np.array([p['wrist'] for p in poses]), tip=np.array([p['tip'] for p in poses]),
            head=np.array([p['head'] for p in poses]),
            sag=np.array([rig.rail_sag(aid, t, mid) for t in times]),
            sway=np.array([rig.mast_sway(aid, t) for t in times]))
        own = list(ARM_CHANNELS)
        if rig.stepped(aid):
            st = rig.stroke(aid)
            values['ride'] = np.asarray(st.pawl_ride(times), float) if st is not None else np.zeros(len(times))
            own += STEPPED_CHANNELS
        by_arm[aid] = values
        unreachable = int(sum(not p['reachable'] for p in poses))
        for name, width in own:
            channels.append(dict(name=f'{aid}.{name}', offset=len(columns), width=width))
            v = values[name].reshape(len(times), width)
            columns.extend(v[:, i] for i in range(width))
        clicks, click_pawl, click_step = arm_clicks(rig, aid)
        sp_plan = rig.mallet_splay_plan(aid)
        arms[aid] = dict(
            kind=rig.acts[aid]['kind'], mech=rig.mech_of[aid], stepped=rig.stepped(aid), hammer=rig.hammer(aid),
            flip_sign=rig.flip_sign(aid), rail_span=[lo, hi], unreachable=unreachable,
            pawl_phase=float(cfg['pawl'].get('phase', 0.0)) if cfg.get('pawl') else None,
            clicks=clicks, click_pawl=click_pawl, click_step=click_step, blows=arm_blows(rig, aid),
            # the hinged head's pin above the tool frame: rig.HAMMER's (per arm from M5)
            head_l=head_l)
        if sp_plan is not None:
            arms[aid]['splay'] = dict(
                dx_base=float(sp_plan['dx_base']),
                dx_init=float(sp_plan['dx_init']),
                segs=[[float(v) for v in g] for g in sp_plan['segs']],
                notes=sp_plan['notes'],
            )
        if rig.hammer(aid) or 'head' in cfg:
            hd = cfg.get('head') or {}
            if hd.get('length') is None or float(hd['length']) != head_l or [float(v) for v in hd.get('hinge', [])] != [0.0, head_l, 0.0]:
                raise ValueError(f'formlab.bake: {aid}\'s head in {manifest_path.name} (length {hd.get("length")}, hinge '
                                 f'{hd.get("hinge")}) is not rig.HAMMER head_l {head_l}: rebuild the model (tools/build_clockwork.py)')
    mechs = {}
    for m in rig.score['instrument']['mechanisms']:
        mid = m['id']
        stand = np.array([rig.stand_thump(mid, t) for t in times])
        channels.append(dict(name=f'{mid}.stand', offset=len(columns), width=1)); columns.append(stand)
        mechs[mid] = dict(blows=len(rig.blows_by_mech.get(mid, [])))
    # the joints' own angles, appended after every /1 column (formlab/kinematics.py q_columns)
    for aid in rig.plans:
        qs = J.q_columns(rig, aid, by_arm[aid], times)
        for key in ('q.lean', 'q.shoulder', 'q.elbow'):
            if key not in qs: continue
            channels.append(dict(name=f'{aid}.{key}', offset=len(columns), width=1, joint=f'{aid}/{key[2:]}'))
            columns.append(qs[key])
    exact = np.stack(columns, axis=1)            # the writer's float64 values
    frames = exact.astype('<f4')
    xs = np.arange(PAWL_TABLE_N)*P.PITCH/PAWL_TABLE_N
    table = [float(a) for a in P.angle(xs)]
    json_path, bin_path = paths(score_path, asset)
    bpm = float(rig.score.get('bpm', J.BPM_DEFAULT))
    tab = J.build(rig, arms, channels, bpm)
    for aid in arms: arms[aid]['joints'] = [jt['id'] for jt in tab['joints'] if jt['owner'] == aid]
    for mid in mechs: mechs[mid]['joints'] = [jt['id'] for jt in tab['joints'] if jt['owner'] == mid]
    # declared after the columns are stacked: Rig.declared annotates the stroke (stroke.declare_jerk)
    for aid in arms: arms[aid]['declared'] = J.declared_block(rig, aid)
    header = dict(
        format=FORMAT, asset=asset, hz=hz, samples=len(times), width=frames.shape[1],
        t0=float(times[0]), t1=float(times[-1]),
        score=score_path.name, score_sha256=sha256(score_path),
        manifest=manifest_path.name, manifest_sha256=sha256(manifest_path),
        data=bin_path.name, times_bytes=8*len(times), frames_bytes=frames.nbytes,
        channels=channels, arms=arms, mechanisms=mechs,
        # the constants a player needs besides the channels: the click's ring
        # and the tooth rate above which a mallet's pawl rides the tips (the
        # hinged head's pin is per arm: arms[aid].head_l)
        constants=dict(RING_HZ=R.RING_HZ, RING_TAU=R.RING_TAU,
                       CLICK_MIN_S=R.CLICK_MIN_S, CLICK_MOVE=R.CLICK_MOVE, PAWL_RIDE=float(R.stroke.PAWL_RIDE)),
        # one tooth of the pawl's angle, and the angle it holds riding the tips
        # (the table's least: the nose landed on a tooth's tip)
        pawl=dict(pitch=P.PITCH, table=table, ride_angle=min(table)),
        kinematics=J.KINEMATICS, joints=tab['joints'], bodies=tab['bodies'], declared_vocab=J.declared_vocab())
    kin = J.compile(header)
    # FK in double from the writer's own values must land on every pin, every row
    worst = J.fk_check(kin, exact, times)
    # each joint's observed range, from the stored float32 rows (what a reader sees)
    q = J.value_rows(kin, frames.astype(np.float64), times)
    for jt in header['joints']: jt['range'] = [float(q[jt['id']].min()), float(q[jt['id']].max())]
    text = json.dumps(J.json_safe(header), allow_nan=False, separators=(',', ':'))
    with open(bin_path, 'wb') as f:
        f.write(times.astype('<f8').tobytes()); f.write(frames.tobytes())
    json_path.write_text(text)
    if verbose: verbose(f'MOTION BAKE: {len(times)} samples x {frames.shape[1]} channels '
                        f'({(header["times_bytes"]+frames.nbytes)/1e6:.1f} MB), {len(header["joints"])} joints, '
                        f'{len(header["bodies"])} bodies, header {len(text)/1e3:.0f} kB, FK worst {worst[0]:.2g} m '
                        f'({worst[1]}) -> {json_path}')
    return header

class Bake:
    """The reference reader: what a player does with the files, in numpy.
    tools/test_bake.py holds harness/motion_bake.gd to it."""
    def __init__(self, json_path):
        json_path = Path(json_path)
        self.header = json.loads(json_path.read_text())
        fmt = self.header.get('format') if isinstance(self.header, dict) else None
        if fmt != FORMAT:
            asset = (self.header.get('asset') if isinstance(self.header, dict) else None) or json_path.name.split('.')[0]
            raise ValueError(f"{json_path} is a {fmt or 'non-loam-motion'} bake; formlab.bake reads {FORMAT} (the joints "
                             f"table, per-arm head_l, declared segments) — run python3 tools/bake_motion.py --asset={asset}")
        raw = (json_path.parent/self.header['data']).read_bytes()
        n = self.header['samples']; w = self.header['width']
        self.times = np.frombuffer(raw[:8*n], '<f8')
        self.frames = np.frombuffer(raw[8*n:], '<f4').reshape(n, w)
        self.index = {c['name']: c for c in self.header['channels']}
        self.kin = J.compile(self.header)

    def fresh(self, score_path, manifest_path):
        return sha256(score_path) == self.header['score_sha256'] and sha256(manifest_path) == self.header['manifest_sha256']

    def row(self, t):
        """The interpolated row at t (float64; the stored values are float32)."""
        i = int(np.searchsorted(self.times, t, 'left'))
        if i <= 0: return self.frames[0].astype(float)
        if i >= len(self.times): return self.frames[-1].astype(float)
        t0, t1 = self.times[i-1], self.times[i]
        w = (t-t0)/(t1-t0)
        return self.frames[i-1].astype(float)*(1-w)+self.frames[i].astype(float)*w

    def row_godot(self, t):
        """The row at t as harness/motion_bake.gd's _at reads it: Godot's row
        (bsearch before equals; the end rows hold) and a+(b-a)*w in double
        from the float32 values."""
        i = int(np.searchsorted(self.times, t, 'left'))
        if i <= 0: return self.frames[0].astype(np.float64)
        if i >= len(self.times): return self.frames[-1].astype(np.float64)
        w = (t-self.times[i-1])/(self.times[i]-self.times[i-1])
        a = self.frames[i-1].astype(np.float64)
        return a+(self.frames[i].astype(np.float64)-a)*w

    def head_l(self, aid):
        """The arm's hinged head's pin above its tool frame (m)."""
        return float(self.header['arms'][aid]['head_l'])

    def joint_ids(self): return list(self.kin.ids)

    def joint_frames(self, t, fk=False):
        """{id: (P, B (columns x y z), q, ident)} at t: the joints table's
        evaluator (formlab.kinematics.evaluate, Godot's arithmetic mirrored);
        fk=True ignores the pose overrides (the chain rule from q)."""
        return J.evaluate(self.kin, self.row_godot(t), t, fk)

    def joint_value(self, jid, t): return self.joint_frames(t)[jid][2]

    def joint_origin(self, jid, t):
        """A joint's world position at t (pose mode): a pinned joint's is its
        channel read as a Vector3 (float32), with no tree walk."""
        i = self.kin.idx[jid]
        if self.kin.pin[i] is not None:
            o = self.kin.pin[i]; return self.row_godot(t)[o:o+3].astype(np.float32).astype(np.float64)
        return self.joint_frames(t)[jid][0]

    def declared(self, aid):
        """The arm's declared structure as formlab.segments.Declared (null
        bounds back to -/+inf, dv back to arrays; prep a bilinear interpolant
        of the header's table, formlab.kinematics.prep_interp)."""
        d = self.header['arms'][aid]['declared']
        segs = [SEG.Segment(-np.inf if g['t0'] is None else g['t0'], np.inf if g['t1'] is None else g['t1'],
                            g['law'], g['tag'], g['event'], g['extra']) for g in d['segments']]
        knots = [SEG.Knot(k['t'], k['kind'], None if k['dv'] is None else np.asarray(k['dv'], float), k['event'], k['extra'])
                 for k in d['knots']]
        return SEG.Declared(segs, knots, list(d['rings']), J.prep_interp(d['prep']), native=bool(d['native']))

    def get(self, name, t, row=None):
        c = self.index[name]; r = self.row(t) if row is None else row
        v = r[c['offset']:c['offset']+c['width']]
        return float(v[0]) if c['width'] == 1 else v

    def felt(self, aid, t):
        """A hinged hammer's felt face: the tip plus the head's offset at the
        interpolated angle; the tip itself for a rigid tool."""
        tip = self.get(f'{aid}.tip', t); arm = self.header['arms'][aid]
        if not arm['hammer']: return tip
        return tip+R.head_offset(self.get(f'{aid}.head', t), arm['flip_sign'], self.head_l(aid))

    def ride(self, aid, t, row=None):
        """How far the arm's pawl rides the rack at t, in [0, 1] (its `.ride`
        channel); 0 for an arm that has none (a servo arm, an older bake)."""
        name = f'{aid}.ride'
        return self.get(name, t, row) if name in self.index else 0.0

    def clicks(self, aid):
        """[dict(t, teeth, pawl, step)] the arm's clicks in time order: pawl 0
        drops into the tooth, 1 rides the tips; step 1 a stepped (or homing)
        landing, 0 a freewheel's crossing. An older bake's are all drop and step."""
        arm = self.header['arms'][aid]; cs = arm['clicks']
        pawl = arm.get('click_pawl', [0]*len(cs)); step = arm.get('click_step', [1]*len(cs))
        return [dict(t=float(c[0]), teeth=float(c[1]), pawl=int(pw), step=int(sp)) for c, pw, sp in zip(cs, pawl, step)]

    def pawl_angle(self, x, ride=0.0):
        """The pawl's angle at rail position x (the phase already added): the
        tooth table, looked up periodically and linearly interpolated, leaned
        toward `pawl.ride_angle` (the nose on a tooth's tip) by `ride` in [0, 1].
        Every angle between the two is clear of the teeth."""
        p = self.header['pawl']; tab = p['table']; n = len(tab)
        u = (x % p['pitch'])/p['pitch']*n; k = int(np.floor(u)) % n; w = u-np.floor(u)
        a = tab[k]*(1-w)+tab[(k+1) % n]*w
        return a if not ride else a+(p.get('ride_angle', a)-a)*ride

    def pawl(self, aid, t):
        """The arm's pawl angle at t as a player poses it: the table at the
        carriage's x (the baked root) plus the arm's phase, ridden by its
        `.ride` channel. None for an arm without a pawl."""
        arm = self.header['arms'][aid]
        if arm.get('pawl_phase') is None: return None
        row = self.row(t)
        return self.pawl_angle(float(self.get(f'{aid}.root', t, row)[0])+arm['pawl_phase'], self.ride(aid, t, row))

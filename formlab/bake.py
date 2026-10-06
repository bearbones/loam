"""The performance baked: `loam-motion/1`, the rig's every moving value sampled
over the piece, so a game engine plays the machine back without owning its
motion vocabulary (docs/chamber-spec.md: "Godot becomes a pure playback
engine").

    python3 tools/bake_motion.py [--asset=clockwork] [--hz=240]

`formlab.rig.Rig` is the one implementation of the motion: the planner's
costs (loam/motion_timing.py), the two vocabularies, the recoil bus, the IK.
Its poses are sampled here and written next to the score as

    <asset>.motion.json   the header: format, fingerprints, channels, per-arm
                          records (clicks, blows), per-mechanism records and
                          the pawl's angle over one tooth
    <asset>.motion.bin    little-endian: N float64 times, then N rows of C
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

The header's fingerprints (sha256 of the score.json and the manifest bytes)
are what a reader checks before it trusts the bake: a rebuilt model or a
re-exported score makes it stale, and a stale bake is refused rather than
played. Everything here is numpy-only so Blender can run it at the end of
tools/build_clockwork.py.
"""
import hashlib, json
from pathlib import Path
import numpy as np
from . import rig as R
from . import pawl as P

FORMAT = 'loam-motion/1'
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
    or homing | 0 freewheel]) in time order: a mallet's a tooth from its
    stroke, the hammer's a ratchet click (its pawl drops at every landing)."""
    st = rig.stroke(aid) if rig.mallet(aid) else None
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
    mallet's also carry its stroke's v_in and e."""
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
    arms = {}
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
            st = rig.stroke(aid) if rig.mallet(aid) else None
            values['ride'] = np.asarray(st.pawl_ride(times), float) if st is not None else np.zeros(len(times))
            own += STEPPED_CHANNELS
        unreachable = int(sum(not p['reachable'] for p in poses))
        for name, width in own:
            channels.append(dict(name=f'{aid}.{name}', offset=len(columns), width=width))
            v = values[name].reshape(len(times), width)
            columns.extend(v[:, i] for i in range(width))
        clicks, click_pawl, click_step = arm_clicks(rig, aid)
        arms[aid] = dict(
            kind=rig.acts[aid]['kind'], mech=rig.mech_of[aid], stepped=rig.stepped(aid), hammer=rig.hammer(aid),
            flip_sign=rig.flip_sign(aid), rail_span=[lo, hi], unreachable=unreachable,
            pawl_phase=float(cfg['pawl'].get('phase', 0.0)) if cfg.get('pawl') else None,
            clicks=clicks, click_pawl=click_pawl, click_step=click_step, blows=arm_blows(rig, aid))
    mechs = {}
    for m in rig.score['instrument']['mechanisms']:
        mid = m['id']
        stand = np.array([rig.stand_thump(mid, t) for t in times])
        channels.append(dict(name=f'{mid}.stand', offset=len(columns), width=1)); columns.append(stand)
        mechs[mid] = dict(blows=len(rig.blows_by_mech.get(mid, [])))
    frames = np.stack(columns, axis=1).astype('<f4')
    xs = np.arange(PAWL_TABLE_N)*P.PITCH/PAWL_TABLE_N
    table = [float(a) for a in P.angle(xs)]
    json_path, bin_path = paths(score_path, asset)
    header = dict(
        format=FORMAT, asset=asset, hz=hz, samples=len(times), width=frames.shape[1],
        t0=float(times[0]), t1=float(times[-1]),
        score=score_path.name, score_sha256=sha256(score_path),
        manifest=manifest_path.name, manifest_sha256=sha256(manifest_path),
        data=bin_path.name, times_bytes=8*len(times), frames_bytes=frames.nbytes,
        channels=channels, arms=arms, mechanisms=mechs,
        # the constants a player needs besides the channels: the hinged head's
        # pin (it is posed HEAD_L above the tool frame), the click's ring, and
        # the tooth rate above which a mallet's pawl rides the tips
        constants=dict(HEAD_L=R.HAMMER['head_l'], RING_HZ=R.RING_HZ, RING_TAU=R.RING_TAU,
                       CLICK_MIN_S=R.CLICK_MIN_S, CLICK_MOVE=R.CLICK_MOVE, PAWL_RIDE=float(R.stroke.PAWL_RIDE)),
        # one tooth of the pawl's angle, and the angle it holds riding the tips
        # (the table's least: the nose landed on a tooth's tip)
        pawl=dict(pitch=P.PITCH, table=table, ride_angle=min(table)))
    with open(bin_path, 'wb') as f:
        f.write(times.astype('<f8').tobytes()); f.write(frames.tobytes())
    json_path.write_text(json.dumps(header, indent=1))
    if verbose: verbose(f'MOTION BAKE: {len(times)} samples x {frames.shape[1]} channels '
                        f'({(header["times_bytes"]+frames.nbytes)/1e6:.1f} MB) -> {json_path}')
    return header

class Bake:
    """The reference reader: what a player does with the files, in numpy.
    tools/test_bake.py holds harness/motion_bake.gd to it."""
    def __init__(self, json_path):
        json_path = Path(json_path)
        self.header = json.loads(json_path.read_text())
        raw = (json_path.parent/self.header['data']).read_bytes()
        n = self.header['samples']; w = self.header['width']
        self.times = np.frombuffer(raw[:8*n], '<f8')
        self.frames = np.frombuffer(raw[8*n:], '<f4').reshape(n, w)
        self.index = {c['name']: c for c in self.header['channels']}

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

    def get(self, name, t, row=None):
        c = self.index[name]; r = self.row(t) if row is None else row
        v = r[c['offset']:c['offset']+c['width']]
        return float(v[0]) if c['width'] == 1 else v

    def felt(self, aid, t):
        """A hinged hammer's felt face: the tip plus the head's offset at the
        interpolated angle; the tip itself for a rigid tool."""
        tip = self.get(f'{aid}.tip', t); arm = self.header['arms'][aid]
        if not arm['hammer']: return tip
        return tip+R.head_offset(self.get(f'{aid}.head', t), arm['flip_sign'], self.header['constants']['HEAD_L'])

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

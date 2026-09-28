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
exactly on (each contact, each move's start and landing, each release) and
rows packed through every ratchet click (a tooth in ~16 ms), so
linear interpolation between rows lands every contact exactly and never
rounds off a boundary. Before the first row and after the last a reader
holds the end row.

The pawl is NOT a time channel. Its angle is a function of where the carriage
is on the rack, periodic in the tooth pitch (formlab.pawl.angle), and its
lift over a tooth tip lasts a few milliseconds of a hurried click — shorter
than a sample. So the header carries one tooth of it (`pawl.table`) and a
reader looks it up at the baked carriage x plus the arm's phase: exact at
any frame rate.

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
MECH_CHANNELS = [('stand', 1)]
PAWL_TABLE_N = 1024
CLICK_SAMPLES = 8

def sha256(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def paths(score_path, asset):
    d = Path(score_path).resolve().parent
    return d/f'{asset}.motion.json', d/f'{asset}.motion.bin'

def sample_times(rig, hz):
    """The uniform grid from one second before the piece to its end, plus the
    corners of every scheduled path (see the module docstring)."""
    total = float(rig.score['total_s'])
    times = set((np.arange(-hz, int(np.ceil(total*hz))+1)/hz).tolist())
    for aid in rig.plans:
        for s in rig.schedule(aid):
            ids = s['event']['strings']
            for k in range(len(ids)): times.add(float(s['hit']+k*s['spread']))
            for key in ('go', 'approach', 'hit', 'end', 't_free', 'tm'): times.add(float(s[key]))
            # A ratchet click moves a tooth in CLICK_MOVE of 40-90 ms: far too
            # sharp a curve for the grid, so each click's move and the start of
            # its ring get CLICK_SAMPLES rows of their own.
            if rig.stepped(aid) and s['moving']:
                T = s['approach']-s['go']; n = R.clicks(s['first'][0]-s['rest'][0], T)
                for k in range(n):
                    for j in range(CLICK_SAMPLES+1):
                        times.add(float(s['go']+(k+R.CLICK_MOVE*1.5*j/CLICK_SAMPLES)*T/n))
    return np.array(sorted(t for t in times if np.isfinite(t)))

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
        unreachable = int(sum(not p['reachable'] for p in poses))
        for name, width in ARM_CHANNELS:
            channels.append(dict(name=f'{aid}.{name}', offset=len(columns), width=width))
            v = values[name].reshape(len(times), width)
            columns.extend(v[:, i] for i in range(width))
        arms[aid] = dict(
            kind=rig.acts[aid]['kind'], mech=rig.mech_of[aid], stepped=rig.stepped(aid), hammer=rig.hammer(aid),
            flip_sign=rig.flip_sign(aid), rail_span=[lo, hi], unreachable=unreachable,
            pawl_phase=float(cfg['pawl'].get('phase', 0.0)) if cfg.get('pawl') else None,
            clicks=[[t, n] for t, n in rig.click_times(aid)],
            blows=[dict(t=b['t'], gate_end=(b['gate_end'] if np.isfinite(b['gate_end']) else None), x=b['x'], energy=b['energy'])
                   for b in rig.blows_by_arm.get(aid, [])])
    mechs = {}
    for m in rig.score['instrument']['mechanisms']:
        mid = m['id']
        stand = np.array([rig.stand_thump(mid, t) for t in times])
        channels.append(dict(name=f'{mid}.stand', offset=len(columns), width=1)); columns.append(stand)
        mechs[mid] = dict(blows=len(rig.blows_by_mech.get(mid, [])))
    frames = np.stack(columns, axis=1).astype('<f4')
    xs = np.arange(PAWL_TABLE_N)*P.PITCH/PAWL_TABLE_N
    json_path, bin_path = paths(score_path, asset)
    header = dict(
        format=FORMAT, asset=asset, hz=hz, samples=len(times), width=frames.shape[1],
        t0=float(times[0]), t1=float(times[-1]),
        score=score_path.name, score_sha256=sha256(score_path),
        manifest=manifest_path.name, manifest_sha256=sha256(manifest_path),
        data=bin_path.name, times_bytes=8*len(times), frames_bytes=frames.nbytes,
        channels=channels, arms=arms, mechanisms=mechs,
        # the constants a player needs besides the channels: the hinged head's
        # pin (it is posed HEAD_L above the tool frame) and the click's ring
        constants=dict(HEAD_L=R.HAMMER['head_l'], RING_HZ=R.RING_HZ, RING_TAU=R.RING_TAU,
                       CLICK_MIN_S=R.CLICK_MIN_S, CLICK_MOVE=R.CLICK_MOVE),
        pawl=dict(pitch=P.PITCH, table=[float(a) for a in P.angle(xs)]))
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

    def pawl_angle(self, x):
        """The pawl's angle at rail position x (the phase already added): the
        tooth table, looked up periodically and linearly interpolated."""
        p = self.header['pawl']; tab = p['table']; n = len(tab)
        u = (x % p['pitch'])/p['pitch']*n; k = int(np.floor(u)) % n; w = u-np.floor(u)
        return tab[k]*(1-w)+tab[(k+1) % n]*w

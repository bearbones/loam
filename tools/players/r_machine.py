"""Rulers 17 (drives), 18 (aliasing), 20 (rings) and 22 (precision) of
docs/goals/the-players.md ("Acceptance"; "Rules of the machine" 1, 3, 5, 7, 8).

They read the rig and the manifest, never the bake (a bake can be stale while
a milestone works). Where the HARNESS is what turns a part — the pinion, the
leadscrew, the pawl's roller, the flywheel and its belt pulley
(harness/performance.gd) — its law is parsed out of that source, so a change
there is seen here instead of being re-implemented and drifting.

17 drives. The moving DOFs per arm today: carriage x, shoulder and elbow (the
upper link's angle from +z and the forearm's relative to it, in the arm's yz
plane — Rig.pose keeps root.x = tip.x, so the links never leave it), and the
hinged hammer's head. The wrist pin is not a DOF: the double parallelogram
fixes the tool's orientation. A DOF is driven when a visible driver turns at
its mechanism's closed-form law from a source: today only a screw carriage
(the leadscrew). A rack carriage's pinion has no motor — the harness turns it
from the carriage's x — so, as the goal says, the pinion is driverless. Per type:
gear (the harness's angle against N·q + c, N = 1/r_pitch from the recipe and
c fixed by the mesh, not free: the built pinion has a tooth on +x and the rack
a gap at x ≡ 0 mod one pitch (formlab.gantry: tooth tips at (k+½)·p), so
c ≡ 0 mod one tooth and the harness's `phase` (the rack's offset along the
carriage, which formlab never puts into the rack's teeth) is a mesh error;
with no backlash declared, Godot's 32-bit Basis angle is the only error
allowed; the minimum tooth-polygon separation over one pitch (formlab.gear) is
reported beside it; the centre distance moves by the pinion's sag (the
carriage rides the sagging rail) against the rack's mesh point, which rides
the railhead and so tilts with the mast's sway about the plinth feet — the
harness moves neither the railhead with sag nor the pinion with sway — to
0.5 mm), cam (the pawl's roller against the pinion's teeth as the harness
draws it: the baked 1024-entry one-tooth table lerped, formlab.pawl as the
rule), tendon (the flywheel's flat belt: Σρθ on the belt's centreline, the
radius the manifest draws its wraps at; picks and the rake have no tendon:
n/a), the hammer's head cam (no cam lifts it yet: n/a until M5), crank (none
today), backlash (none declared), drive rpm, and mates (every toothed wheel
meshes: the flywheel's ring does not).

18 aliasing. Every periodic visible feature turned by a law: the pinion's 16
teeth and the pawl roller's grease plug (one a face, off-axis: period 360°,
turned by its spin AND the pawl's swing, both about z) on rack arms, the leadscrew's thread (one start: 360°) on screw arms, the
flywheel's 52 teeth and 6 spokes. Per frame Δθ_k against 0.5·P, and the
apparent direction (Δθ wrapped into (−P/2, P/2]). No blur sheath exists, so
every frame over 0.5·P fails.

20 rings. The declared ring terms (formlab.segments: Declared.rings) against
what renders: (match) the channel minus the ring-free scored path (Rig.path_at
with the ratchet's overshoot ring taken out) — the tool (recoil, and the
detent it rides in x), the carriage (its x, the rail's sag), the gantry's
sway, the hammer head's check bounce, the stand's thump — against Σ over the
declared knots (contacts; detents for the detent) of amp·e^(−τ/τd)·sin(2πfτ)
on each term's axis, per axis (the tool's x carries recoil.x and the
detent; recoil.bounce's amp is a fraction of the hover lift in the Rig, so
the non-native declaration is scaled by |lift| into metres); (one) one
(f, ζ) per part, f_seen = 2f for the rectified rings (|sin|: the bounce, the
check) and aliasing when f_seen > 15 Hz; (heavier) n/a until
masses exist; (legible) per excitation, sampled at 120 Hz and put through the
film camera (render/film/camera.json; without one, an estimate from the film's
nearest camera): f ≤ 6 Hz and visible ≥ 1.5/f s, or ζ ≥ 0.4, or < 0.5 px.
Harness-only rings (the struck bars' bounce in performance.gd) are measured
and fail the match: nothing declares or bakes them.

22 precision. sync (rule 7): repositions ending in a placing or hold, placing
groups and homing sweeps, from the declared segments — none today: every
travel runs straight into its strike, which rule 7 lets blend, so sync is n/a
and today's travels are reported as INFO, measured the same way. The window
runs to the end of the reposition plus up to 2 frames of the hold or placing
that follows (the overshoot and settle live there). Per channel
(carriage x, shoulder and elbow from IK, the hammer's hinge) start = first
|v| > 1 mm/s (0.01 rad/s), arrival = the last; skew across the moving
channels; overshoot = excursion beyond the window's end values (a joint's as
the arc at its link's end); settle = still − entering the 0.5 mm band about
the end for good. repeat: strokes with equal (strings, pick, a', IOI, next a',
next IOI) as time-normalised contact-point paths over [stroke start, release
end], max pairwise RMS. home: the first rest ≥ 2 s holds a `home` segment
that sweeps ≥ 0.9 of reach_x and ≥ 0.8 of the shoulder's and elbow's IK spans
(ruler 16's) with the scored path ≤ 0.5·SERVO_V_MAX, landing on the home rest
to 1e-9 m.
"""
import functools, math, re
from pathlib import Path
import numpy as np
from players.core import Result, INFO, FPS, HZ, ROOT, deriv, stat
from formlab import rig as RIG
from formlab import gear as GEAR
from formlab import pawl as PAWL
from formlab.clearance import PINION, SCREW, drive_kind, pinion_centre, rack_direction
from formlab.gantry import RACK_GAP
from formlab.layout import FLYWHEEL
try: from formlab.bake import PAWL_TABLE_N
except Exception: PAWL_TABLE_N = 1024

PERF = ROOT/'harness/performance.gd'
FILM_CAMERA = ROOT/'render/film/camera.json'
RPM_MAX = 3000.0
SCREW_STARTS = 1          # formlab.gantry.screw: one helix (formlab.linkage.helix), lead = pitch
F32 = 4*2.0**-23          # the gear law's allowance: Godot's Basis takes a 32-bit angle
CENTRE_TOL = 5e-4         # centre distance ± 0.5 mm
CAM_GAP_TOL = 1e-4        # cam follower gap ≤ 0.1 mm
TENDON_TOL = 1e-4         # Σrθ + free spans constant ± 0.1 mm
RING_TOL = 1e-4           # rendered − scored = Σ declared rings ± 0.1 mm
PX_MIN = 0.5              # a ring under half a pixel is invisible
SKEW_MAX = 1/240          # sync: all axes leave and arrive within one 240 Hz sample
OVERSHOOT_MAX = 5e-4      # 0.5 mm
REPEAT_MAX = 1e-3         # 1 mm RMS
V_THR = 1e-3              # 1 mm/s
W_THR = 1e-2              # 0.01 rad/s
SYNC_DT = 5e-4            # sync sampling step (s): well inside the 240 Hz skew budget
HOME_REST = 2.0

# ---- shared ---------------------------------------------------------------
@functools.lru_cache(maxsize=None)
def harness_laws():
    """The laws harness/performance.gd turns parts by, read from its source.
    None (or False) where the expected expression is not found: the ruler
    then fails loudly instead of measuring a law nobody renders."""
    src = PERF.read_text() if PERF.exists() else ''
    m = re.search(r'p\["gear"\]\.basis=Basis\(.*?,\(root\.x\+phase\)/(\d*\.\d+)\)', src)
    fw = re.search(r'return -TAU\*t\*float\(score\.doc\.get\("bpm",([\d.]+)\)\)/(\d+\.?\d*)', src)
    return dict(
        pinion_r=float(m.group(1)) if m else None,             # θ = (x + phase) / r
        screw=bool(re.search(r'wrapf\(-TAU\*root\.x/float\(sc\["pitch"\]\),-PI,PI\)', src)),   # θ = −2π x / pitch
        roller=bool(re.search(r'float\(cfg\["pawl"\]\.get\("roller_spin",0\.0\)\)\*root\.x', src)),  # θ = roller_spin · x
        flywheel=(float(fw.group(1)), float(fw.group(2))) if fw else None,   # θ = −2π t bpm / 240 (default bpm, 240)
        belt=bool(re.search(r'k=float\(f\["cyls"\]\["drive pulley"\]\[2\]\)/float\(f\["cyls"\]\["belt pulley"\]\[2\]\)', src)),
    )

def drive_of(S, aid):
    cfg = S.cfg(aid)
    return cfg.get('drive') or drive_kind(cfg)

def joint_angles(P):
    """(shoulder, elbow) over a pose dict: the upper link's angle from +z and
    the forearm's relative to it, both in the arm's yz plane, unwrapped."""
    up = P['elbow']-P['root']; lo = P['wrist']-P['elbow']
    a1 = np.unwrap(np.arctan2(up[..., 1], up[..., 2])); a2 = np.unwrap(np.arctan2(lo[..., 1], lo[..., 2]))
    return a1, a2-a1

def _flywheel_theta(S, t):
    laws = harness_laws()
    if not laws['flywheel']: return None
    bpm = float(S.score.get('bpm', laws['flywheel'][0]))
    return -2*np.pi*np.asarray(t, float)*bpm/laws['flywheel'][1]

def _merge(wins, lo, hi):
    out = []
    for a, b in sorted(wins):
        a = max(a, lo); b = min(b, hi)
        if b <= a: continue
        if out and a <= out[-1][1]: out[-1][1] = max(out[-1][1], b)
        else: out.append([a, b])
    return out

def _f(x): return None if x is None else float(x)

# ---- 17 drives ------------------------------------------------------------
def _x_windows(S, aid):
    """Where the carriage can move: each event's [go, t_free], and after a
    mallet's blow its recoil (x follows the tip: Rig.pose's root.x = tip.x)
    until the next strike begins."""
    rig = S.rig; sched = rig.sched[aid]; wins = []
    rings = rig.stepped(aid) and not rig.hammer(aid)
    for i, s in enumerate(sched):
        wins.append((float(s['go']), float(s['t_free'])))
        if rings:
            nxt = float(sched[i+1]['approach']) if i+1 < len(sched) else float(s['hit'])+RIG.SHUDDER_TAIL
            wins.append((float(s['hit']), nxt))
    return _merge(wins, 0.0, S.total)

def peak_xdot(S, aid, dt=5e-4):
    """Peak |dx/dt| of the carriage (the rendered root.x = tip_at x) and its
    time: dense samples over the moving windows, refined with the one-sided
    5-point stencils around the best sample."""
    fx = lambda u: S.rig.tip_at(aid, u)[0]
    best, tb = 0.0, None
    for a, b in _x_windows(S, aid):
        ts = np.arange(a, b+dt, dt)
        if len(ts) < 3: continue
        v = np.gradient(np.array([fx(u) for u in ts]), ts)
        k = int(np.argmax(np.abs(v)))
        if abs(v[k]) > best: best, tb = float(abs(v[k])), float(ts[k])
    if tb is None: return 0.0, None
    for u in np.linspace(tb-dt, tb+dt, 21):
        for side in (-1, 1): best = max(best, abs(float(deriv(fx, u, side))))
    return best, tb

def _dofs(S, aid):
    P = S.poses(aid, 'frames'); sh, el = joint_angles(P)
    d = {'carriage x': (P['root'][:, 0], 1e-4), 'shoulder': (sh, 1e-4), 'elbow': (el, 1e-4)}
    if S.rig.hammer(aid): d['hinge'] = (P['head'], 1e-4)
    return d

def driven_share(S, aid):
    """Moving DOFs against their drivers. The leadscrew is a driver (the goal
    names only the shoulder, the elbow and the pinion driverless); a rack
    carriage is not driven: its pinion has no motor (M4 adds one), the harness
    turns it from the carriage's x, the driven part leading its driver."""
    drv = drive_of(S, aid)
    drivers = {'carriage x': 'leadscrew' if drv == 'screw' else None, 'shoulder': None, 'elbow': None, 'hinge': None}
    rng = {}; moving = []
    for name, (q, eps) in _dofs(S, aid).items():
        r = float(np.ptp(q)); rng[name] = round(r if name == 'carriage x' else math.degrees(r), 4)
        if r > eps: moving.append(name)
    driven = [n for n in moving if drivers.get(n)]
    share = len(driven)/len(moving) if moving else 1.0
    v = dict(share=round(share, 4), moving=moving, driven=driven, range=rng, carriage_drive=drv)
    if drv == 'rack': v['pinion_motor'] = False
    note = 'ranges: carriage m, joints deg; no sector, crank or tendon drives a joint'
    if drv == 'rack': note += '; the pinion has no motor (the harness turns it from the carriage x), so the carriage is undriven'
    return Result(17, 'driven share', aid, v, share >= 1.0-1e-12, note)

def drive_rpm(S, aid):
    v_peak, t_peak = peak_xdot(S, aid); drv = drive_of(S, aid)
    if drv == 'screw':
        lead = float(S.cfg(aid).get('screw', {}).get('pitch', SCREW['pitch']))*SCREW_STARTS
        rpm = v_peak/lead*60.0
        v = dict(drive='leadscrew', lead_mm=lead*1e3, starts=SCREW_STARTS, xdot=v_peak, rpm=rpm, t=t_peak)
    else:
        r = PINION['r_pitch']; rpm = v_peak/(2*np.pi*r)*60.0
        v = dict(drive='pinion', r_mm=r*1e3, teeth=PINION['teeth'], xdot=v_peak, rpm=rpm, t=t_peak)
        spin = S.cfg(aid).get('pawl', {}).get('roller_spin')
        if spin is not None: v['roller_rpm'] = abs(float(spin))*v_peak/(2*np.pi)*60.0
    note = '|xdot| of the rendered carriage; ' + ('leadscrew rpm = |xdot|/lead*60' if drv == 'screw' else
                                                  'pinion rpm = |xdot|/r/2pi*60 (the pawl roller, a follower, reported, not judged)')
    return Result(17, 'rpm', aid, v, bool(rpm <= RPM_MAX), note)

def _centre_offsets(S, aid):
    """The pinion's centre-distance error on the 120 Hz grid, along the line
    of centres (clearance.rack_direction). The pinion rides the carriage, so
    it follows the rail's sag at its own x (Rig.pose). The rack is NOT on the
    guide bars: build_forms.py packs it into form_<aid>_railhead (there is no
    form_<aid>_rack node, so performance.gd's sag lookup finds nothing), and
    the railhead is in the gantry frame performance.gd tilts by the mast sway
    about world X through the plinths' mean foot. So the error is the
    pinion's sag minus the swayed rack's displacement at the mesh point."""
    rig = S.rig; cfg = S.cfg(aid)
    if aid not in rig.blows_by_arm: return np.zeros(1)
    mount = cfg.get('pinion', 'back'); u = rack_direction(mount); ts = S.t_hz
    piv, _ = _gantry_tops(cfg)
    x = np.array([rig.tip_at(aid, t)[0] for t in ts])
    sag = np.array([rig.rail_sag(aid, t, xx) for t, xx in zip(ts, x)])
    th = np.array([rig.mast_sway(aid, t) for t in ts])
    mesh = np.c_[x, np.full(len(ts), float(cfg['root_y'])), np.full(len(ts), float(cfg['root_z']))]+pinion_centre(mount)+u*PINION['r_pitch']
    if piv is None: d_rack = np.zeros_like(mesh)
    else:
        r = mesh-piv; c, s = np.cos(th), np.sin(th)
        d_rack = np.c_[0*th, r[:, 1]*(c-1)-r[:, 2]*s, r[:, 1]*s+r[:, 2]*(c-1)]
    d_pin = np.c_[0*sag, sag, 0*sag]
    return np.abs((d_pin-d_rack)@u)

def _mesh_separation(phase, n=25):
    """The least separation (m; negative = the teeth overlap) between the
    pinion's teeth and the rack's over one tooth pitch, on formlab.gear's
    polygons: the rack's tooth k centred at (k + ½)·pitch (formlab.gantry.
    rack_geometry, as built), the pinion spun as the harness spins it, by
    (x + phase)/r_pitch, with its tooth 0 along +x at home (build_clockwork.gear)."""
    best = np.inf; s_tip = PINION['r_hub']+RACK_GAP; s_root = PINION['r_tip']+RACK_GAP+.001
    for x in np.linspace(0.0, GEAR.PITCH, n, endpoint=False):
        racks = [GEAR.rack_tooth(k, x, s_tip, s_root) for k in range(-3, 4)]
        for i in range(GEAR.TEETH):
            P = GEAR.pinion_tooth(i, x+phase)
            if P[:, 1].max() < s_tip-.002: continue
            for Rt in racks: best = min(best, GEAR.separation(P, Rt))
    return float(best)

def gear_law(S, aid):
    """The carriage's gear law as the harness renders it, on every frame."""
    laws = harness_laws(); drv = drive_of(S, aid); cfg = S.cfg(aid)
    x = S.poses(aid, 'frames')['root'][:, 0]
    if drv == 'screw':
        pitch = float(cfg.get('screw', {}).get('pitch', SCREW['pitch'])); lead = SCREW['pitch']*SCREW_STARTS
        if not laws['screw']:
            return Result(17, 'gear', aid, dict(drive='leadscrew'), False, 'harness/performance.gd no longer turns the leadscrew by -TAU*root.x/pitch: update this ruler')
        wrap = lambda a: (a+np.pi) % (2*np.pi)-np.pi
        th_d = wrap(-2*np.pi*x/pitch).astype(np.float32).astype(float)      # wrapped in double, then a 32-bit Basis angle
        res = np.abs(wrap(th_d-(-2*np.pi*x/lead)))
        tol = F32*np.maximum(1.0, np.abs(th_d))
        off = 0.0      # the nut is coaxial with the screw: a servo rail carries no sag
        v = dict(drive='leadscrew', law='theta = -2pi x / lead', N=-2*np.pi/lead, residual_rad=float(res.max()),
                 within_f32=bool((res <= tol).all()), centre_off_mm=off, mate='nut', manifest_pitch_ok=bool(abs(pitch-lead) < 1e-12))
        ok = bool((res <= tol).all()) and abs(pitch-lead) < 1e-12
        return Result(17, 'gear', aid, v, ok, 'screw and nut: Godot angle against N*q; the nut rides coaxial (no sag on a servo rail)')
    r_h = laws['pinion_r']
    if r_h is None:
        return Result(17, 'gear', aid, dict(drive='pinion'), False, 'harness/performance.gd no longer turns the pinion by (root.x+phase)/r: update this ruler')
    phase = float(cfg.get('pawl', {}).get('phase', 0.0)); r = PINION['r_pitch']; Pt = 2*np.pi/PINION['teeth']
    th_d = ((x+phase)/r_h).astype(np.float32).astype(float)
    # The law: N = 1/r_pitch (z·m/2 = r_pitch) and c = 0 mod one tooth — the
    # constant the mate fixes: the rack's teeth stand at (k + ½)·pitch, so a
    # pinion tooth points into the gap above it at θ = x/r_pitch. No backlash
    # state is declared (b = 0), so a constant offset is a mesh error.
    res = np.abs((th_d-x/r+Pt/2) % Pt-Pt/2); tol = F32*np.maximum(1.0, np.abs(th_d))
    f32 = float(np.abs(th_d-(x+phase)/r_h).max())            # the rendering's own rounding, for reference
    static = abs(GEAR.MODULE*PINION['teeth']/2-r)            # the rack's pitch line lies at r_pitch (formlab.gear.rack_half)
    off = static+float(_centre_offsets(S, aid).max())
    sep = _mesh_separation(phase)
    v = dict(drive='pinion', law='theta = x / r_pitch (+ k*360/z)', harness='(x + phase) / r', N=1/r, phase_mm=phase*1e3,
             residual_deg=float(np.degrees(res.max())), f32_rad=f32, within_f32=bool((res <= tol).all()),
             mesh_min_sep_mm=round(sep*1e3, 3), centre_off_mm=round(off*1e3, 4), mate='rack', module_mm=GEAR.MODULE*1e3)
    ok = bool((res <= tol).all()) and abs(r_h-r) < 1e-12 and off <= CENTRE_TOL
    note = ('the harness spins the pinion by (x + phase)/r, the pawl\'s seating phase, but the rack\'s teeth are cut at (k + 1/2)*pitch '
            'with no phase: residual_deg is that offset (mod a tooth), mesh_min_sep_mm the tooth polygons\' separation over a pitch '
            '(negative: the teeth overlap). centre_off: the pinion\'s sag at its x against the rack on the swaying railhead (120 Hz)')
    return Result(17, 'gear', aid, v, ok, note)

@functools.lru_cache(maxsize=None)
def _pawl_table():
    xs = np.arange(PAWL_TABLE_N)*PAWL.PITCH/PAWL_TABLE_N
    return np.asarray(PAWL.angle(xs), float)

def pawl_angle_rendered(x):
    """The pawl's angle as harness/motion_bake.gd poses it: the bake's
    one-tooth table (formlab.bake, PAWL_TABLE_N rows of formlab.pawl.angle)
    interpolated linearly at x (the phase already added)."""
    tab = _pawl_table(); n = len(tab)
    u = np.mod(np.asarray(x, float), PAWL.PITCH)/PAWL.PITCH*n; k = np.floor(u).astype(int); w = u-k
    return tab[k % n]*(1-w)+tab[(k+1) % n]*w

def _pawl_gap(x):
    al = pawl_angle_rendered(x); n = PAWL.nose_at(al); C = PAWL._pivot_from_centre()
    return PAWL.tooth_distance(C[0]+n[..., 0], C[1]+n[..., 1], x)-PAWL.PAWL['nose_r']

def cam_pawl(S, aid):
    """The pawl's roller (the follower) against the pinion's teeth (the cam),
    as rendered: the harness's interpolated angle on every frame, and the
    worst over any carriage position (the gap is a function of x mod a tooth,
    so a dense sweep of one pitch bounds every baked row)."""
    cfg = S.cfg(aid)
    if 'pawl' not in cfg: return None
    x = S.poses(aid, 'frames')['root'][:, 0]+float(cfg['pawl'].get('phase', 0.0))
    gap = _pawl_gap(x); dense = _pawl_gap(np.linspace(0, PAWL.PITCH, 8192, endpoint=False))
    g = float(max(np.abs(gap).max(), np.abs(dense).max()))
    return Result(17, 'cam', aid, dict(follower='pawl roller', gap_frames_max_mm=float(np.abs(gap).max())*1e3,
                                       gap_any_x_mm=[float(dense.min())*1e3, float(dense.max())*1e3]), g <= CAM_GAP_TOL,
                  'the roller against the teeth with the angle the harness poses (the bake\'s one-tooth table, lerped); '
                  'negative = into the tooth; any_x: [min, max] over a dense sweep of one pitch')

def flywheel_mates(S):
    """Every toothed wheel meshes: the flywheel's 52-tooth ring against every
    other gear's axle over the piece (a mate stands at module·(z1+z2)/2 ± 0.5 mm,
    parallel and coplanar)."""
    fw = S.layout.get('flywheel')
    if not fw: return None
    prof = GEAR.profile(int(fw['teeth']), float(fw['r'])); c = np.asarray(fw['centre'], float)
    best = (np.inf, None)
    for aid in S.layout['arms']:                   # every pinion in the layout, idle arms too
        if aid not in S.rig.acts or drive_of(S, aid) != 'rack': continue
        mount = S.cfg(aid).get('pinion', 'back')
        if not np.isclose(abs(pinion_centre(mount)[2]), PINION['out']): continue      # an up/down disc's axle is vertical: never parallel
        pc = S.poses(aid, 'frames')['root']+pinion_centre(mount)
        need = prof['module']*(prof['teeth']+PINION['teeth'])/2
        d = np.abs(np.hypot(pc[:, 0]-c[0], pc[:, 1]-c[1])-need)+np.maximum(0, np.abs(pc[:, 2]-c[2])-FLYWHEEL['width'])
        k = int(np.argmin(d))
        if d[k] < best[0]: best = (float(d[k]), aid)
    meshed = best[0] <= CENTRE_TOL
    v = dict(teeth=int(fw['teeth']), module_mm=prof['module']*1e3, nearest=best[1], nearest_miss_m=_f(best[0]) if best[1] else None,
             manifest_gears=list(S.layout.get('gears', [])))
    return Result(17, 'mates', 'flywheel', v, bool(meshed),
                  'the flywheel ring meshes nothing (no gear at module*(z1+z2)/2 on a parallel, coplanar axle); the pinions mesh their racks')

def flywheel_belt(S):
    """The flywheel's flat belt (a tendon): Σρθ on the belt's centreline, the
    radius the manifest draws its wraps at (pulley r + belt t/2), against the
    harness's ratio k = r_drive / r_belt."""
    fw = S.layout.get('flywheel'); laws = harness_laws()
    if not fw or 'drive pulley' not in fw.get('cyls', {}): return None
    r1 = float(fw['cyls']['drive pulley'][2]); r2 = float(fw['cyls']['belt pulley'][2])
    rho1, rho2 = (float(w[1]) for w in fw['wraps']) if 'wraps' in fw else (r1+FLYWHEEL['belt_t']/2, r2+FLYWHEEL['belt_t']/2)
    if not laws['belt'] or laws['flywheel'] is None:
        return Result(17, 'tendon', 'flywheel', dict(belt='flat'), False, 'harness/performance.gd belt law not found: update this ruler')
    k = r1/r2; th1 = float(np.abs(_flywheel_theta(S, S.total)))
    slip = abs(rho1-rho2*k)*th1; bare = abs(r1-r2*k)*th1
    v = dict(k_harness=k, k_centreline=rho1/rho2, residual_mm=slip*1e3, residual_bare_radii_mm=bare*1e3, turns=th1/(2*np.pi))
    return Result(17, 'tendon', 'flywheel', v, slip <= TENDON_TOL,
                  'belt centreline radii (manifest wraps, r + t/2) give the residual at the piece\'s end; on the bare pulley radii the harness ratio is exact')

def flywheel_rpm(S):
    fw = S.layout.get('flywheel')
    if not fw or harness_laws()['flywheel'] is None: return None
    w = float(abs(_flywheel_theta(S, 1.0)))/(2*np.pi)*60
    v = dict(flywheel_rpm=w)
    if 'belt pulley' in fw.get('cyls', {}):
        v['belt_pulley_rpm'] = w*float(fw['cyls']['drive pulley'][2])/float(fw['cyls']['belt pulley'][2])
    return Result(17, 'rpm', 'flywheel', v, max(v.values()) <= RPM_MAX, 'one turn a bar; the belt pulley at the harness ratio')

def drives(S):
    out = []
    for aid, kind in S.arms.items():
        if not S.rig.sched.get(aid):
            out.extend(Result(17, m, aid, {}, None, NO_MOTION) for m in ('driven share', 'rpm', 'gear')); continue
        out.append(driven_share(S, aid))
        out.append(drive_rpm(S, aid))
        out.append(gear_law(S, aid))
        c = cam_pawl(S, aid)
        if c: out.append(c)
        out.append(Result(17, 'crank', aid, {}, None, 'no crank exists yet (the elbow crank arrives in M4)'))
        if kind in ('pick', 'rake'):
            out.append(Result(17, 'tendon', aid, {}, None, 'no tendon exists yet (the digits\' drums arrive in M7, the rake\'s hand in M9)'))
        if kind == 'hammer':
            out.append(Result(17, 'cam (hammer lift)', aid, {}, None, 'no cam or whippen lifts the head yet (M5): the hinge is undriven'))
        if drive_of(S, aid) == 'rack':
            beta = 2*GEAR.BACKLASH/PINION['r_pitch']
            out.append(Result(17, 'backlash', aid, dict(declared_deg=None, geometric_deg=math.degrees(beta)), None,
                              'no backlash state in the motion (b(t) = 0); the cut teeth leave 2*BACKLASH at the pitch line'))
        else:
            out.append(Result(17, 'backlash', aid, dict(declared_deg=None), None, 'no backlash declared on the leadscrew'))
    for r in (flywheel_rpm(S), flywheel_mates(S), flywheel_belt(S)):
        if r: out.append(r)
    return out

# ---- 18 aliasing ----------------------------------------------------------
def alias(dth_deg, P):
    """Per-frame rotation of a feature of period P (both in degrees): the
    largest step, the frames over 0.5·P and those whose apparent (wrapped)
    step runs the other way."""
    d = np.asarray(dth_deg, float); a = np.abs(d)
    app = (d+P/2) % P-P/2
    over = a > P/2*(1+1e-12)
    rev = over & (np.sign(app)*np.sign(d) < 0)
    k = int(np.argmax(a)) if a.size else 0
    return dict(P_deg=P, max_deg=float(a.max()) if a.size else 0.0, max_over_half_P=float(a.max()/(P/2)) if a.size else 0.0,
                frames_over=int(over.sum()), frames_reversed=int(rev.sum()), frames_moving=int((a > 1e-9).sum()),
                worst_t=round((k+1)/FPS, 4))

def aliasing(S):
    out = []; laws = harness_laws()
    note = 'no blur sheath exists: every frame over 0.5*P fails'
    for aid in S.arms:
        if not S.rig.sched.get(aid):
            out.append(Result(18, 'leadscrew thread' if drive_of(S, aid) == 'screw' else 'pinion teeth', aid, {}, None, NO_MOTION)); continue
        x = S.poses(aid, 'frames')['root'][:, 0]; dx = np.diff(x); cfg = S.cfg(aid)
        if drive_of(S, aid) == 'screw':
            pitch = float(cfg.get('screw', {}).get('pitch', SCREW['pitch']))
            v = alias(np.degrees(-2*np.pi*dx/pitch), 360.0/SCREW_STARTS)
            out.append(Result(18, 'leadscrew thread', aid, v, v['frames_over'] == 0, f'{SCREW_STARTS} start, period 360/starts; '+note))
        else:
            r = laws['pinion_r'] or PINION['r_pitch']
            v = alias(np.degrees(dx/r), 360.0/PINION['teeth'])
            out.append(Result(18, 'pinion teeth', aid, v, v['frames_over'] == 0, f'{PINION["teeth"]} teeth; '+note))
            spin = cfg.get('pawl', {}).get('roller_spin')
            if spin is not None:
                # the roller turns about z by roller_spin*x on the pawl, which itself swings by -pawl_angle (performance.gd)
                th = float(spin)*x-pawl_angle_rendered(x+float(cfg['pawl'].get('phase', 0.0)))
                v = alias(np.degrees(np.diff(th)), 360.0)
                out.append(Result(18, 'pawl roller', aid, v, v['frames_over'] == 0,
                                  'one off-axis grease plug a face (formlab.pawl.roller_pieces): period 360; spin*x on the pawl\'s swing; '+note))
    fw = S.layout.get('flywheel')
    if fw:
        th = _flywheel_theta(S, S.t_frames)
        if th is None:
            out.append(Result(18, 'flywheel teeth', 'flywheel', {}, False, 'harness flywheel law not found: update this ruler'))
        else:
            d = np.degrees(np.diff(th))
            v = alias(d, 360.0/int(fw['teeth']))
            app = (d[0]+v['P_deg']/2) % v['P_deg']-v['P_deg']/2
            v['step_deg'] = round(float(d[0]), 4); v['apparent_deg'] = round(float(app), 4)
            out.append(Result(18, 'flywheel teeth', 'flywheel', v, v['frames_over'] == 0,
                              f'one turn a bar (bpm {S.score.get("bpm")}): it turns {d[0]:+.2f} deg a frame and its teeth appear to step '
                              f'{app:+.2f}' + (' (backwards)' if app*d[0] < 0 else '') + '; '+note))
            nsp = int(fw.get('spokes', {}).get('count', FLYWHEEL['spokes']))
            v = alias(d, 360.0/nsp)
            out.append(Result(18, 'flywheel spokes', 'flywheel', v, v['frames_over'] == 0, f'{nsp} spokes'))
    return out

# ---- 20 rings -------------------------------------------------------------
class Cam:
    """World displacement -> pixels. With the asset's camera.json, per frame
    (the 120 Hz sample takes its nearest frame's camera); without, an
    estimate: |d| times the film's largest pixels-per-metre at a target (its
    nearest camera to its target), every sample on screen."""
    def __init__(self, S):
        doc = S.camera()
        self.exact = doc is not None
        if self.exact:
            F = doc['frames']; self.W, self.H = float(doc['width']), float(doc['height'])
            self.pos = np.array([f['position'] for f in F], float); self.B = np.array([f['basis'] for f in F], float)
            self.f = (self.H/2)/np.tan(np.radians([f['fov_deg'] for f in F])/2)
            self.desc = f'{Path(S.camera_path).name} per frame'
        else:
            self.k, self.desc = self.bound()

    @staticmethod
    @functools.lru_cache(maxsize=None)
    def bound():
        import json
        if FILM_CAMERA.exists():
            doc = json.loads(FILM_CAMERA.read_text()); F = doc['frames']
            d = np.array([np.linalg.norm(np.subtract(f['position'], f['target'])) for f in F]); k = int(np.argmin(d))
            fov = float(F[k]['fov_deg']); dist = float(d[k]); H = float(doc['height'])
        else:
            fov, dist, H = 43.0, 2.25, 1080.0
        ppm = (H/2)/math.tan(math.radians(fov)/2)/dist
        return ppm, f'no camera.json for this asset: estimated at {ppm:.0f} px/m (fov {fov:.0f} deg at {dist:.2f} m, the film\'s nearest camera to its target)'

    def px(self, t, p, d):
        """Pixel length of displacement d (N,3) at points p (N,3) at times t (N)."""
        t = np.asarray(t, float); p = np.broadcast_to(np.asarray(p, float), (len(t), 3)); d = np.asarray(d, float)
        if not self.exact: return np.linalg.norm(d, axis=1)*self.k
        k = np.clip(np.round(t*FPS).astype(int), 0, len(self.pos)-1)
        B = self.B[k]; f = self.f[k]; o = self.pos[k]
        def proj(q):
            c = np.einsum('nij,nj->ni', B, q-o)
            z = -c[:, 2]
            with np.errstate(divide='ignore', invalid='ignore'):
                u = self.W/2+f*c[:, 0]/z; v = self.H/2-f*c[:, 1]/z
            return u, v, z
        u0, v0, z0 = proj(p); u1, v1, _ = proj(p+d)
        on = (z0 > 0) & (u0 >= 0) & (u0 <= self.W) & (v0 >= 0) & (v0 <= self.H)
        return np.where(on, np.hypot(u1-u0, v1-v0), 0.0)

def _zeta(f, tau): return 1.0/(2*np.pi*f*tau)

def _legible(ts, px, exc, f, tau, tail):
    """Per excitation: peak px until the next excitation (or `tail`), and how
    long it stays ≥ 0.5 px. Returns (peak px, count, illegible count, min visible s)."""
    z = _zeta(f, tau); peak = 0.0; bad = 0; vis_min = None; exc = sorted(exc)
    for i, te in enumerate(exc):
        t1 = min(exc[i+1] if i+1 < len(exc) else np.inf, te+tail)
        m = (ts >= te) & (ts < t1)
        if not m.any(): continue
        w = px[m]; a = float(w.max()); peak = max(peak, a)
        if a < PX_MIN: continue
        tv = float(ts[m][np.nonzero(w >= PX_MIN)[0][-1]]-te)
        vis_min = tv if vis_min is None else min(vis_min, tv)
        if not (z >= 0.4 or (f <= 6.0 and tv >= 1.5/f)): bad += 1
    return peak, len(exc), bad, vis_min

NO_MOTION = 'no motion on this arm: nothing to measure'
RECTIFIED = ('recoil.bounce', 'check')   # rig.recoil's lift*|ring| and rig.head_angle's |damped sine|: seen at 2f

def _amp_m(rig, aid, dec, p):
    """A declared term's amplitude in its channel's units. Today's reading
    (formlab.segments._rings_today, not native) declares recoil.bounce with
    rig.RECOIL's 0.06, which Rig.recoil applies as a FRACTION of the hover
    lift (lift.y*|ring|): that is 0.06*0.22 = 13.2 mm, not 60 mm."""
    a = float(p['amp'])
    if p['name'] == 'recoil.bounce' and not dec.native: a *= abs(float(rig.hover(aid)[1]))
    return a

def _declared_sum(ts, knots, amp, f, tau):
    """Σ over the knots of amp·e^(−τ/τd)·sin(2πfτ), τ = t − t_k ≥ 0."""
    out = np.zeros(len(ts))
    for tk in knots:
        u = ts-tk; m = (u >= 0) & (u < 10*tau)
        out[m] += amp*np.exp(-u[m]/tau)*np.sin(2*np.pi*f*u[m])
    return out

def _gantry_tops(cfg):
    ends = cfg.get('gantry', {}).get('ends', [])
    if not ends: return None, []
    piv = np.mean([[e['x_col'], e['foot_y'], e['mast_z']] for e in ends], axis=0)
    return piv, [np.array([e['x_col'], e['foot_y']+e['height'], e['mast_z']]) for e in ends]

def _detent_ring(rig, aid, ts):
    """The ratchet's overshoot ring in the carriage's x (Rig.ratchet with and
    without its overshoot): it lives inside the scored travel path."""
    out = np.zeros(len(ts)); knots = []
    for s in rig.sched[aid]:
        if not s['moving']: continue
        go, ap = float(s['go']), float(s['approach']); T = ap-go; dx = float(s['first'][0]-s['rest'][0])
        n = RIG.clicks(dx, T); over = RIG.OVERSHOOT*min(1.0, RIG.PITCH*n/max(abs(dx), 1e-6))
        knots += [go+k*T/n for k in range(n)]
        m = np.nonzero((ts >= go) & (ts < ap))[0]
        for i in m:
            u = (ts[i]-go)/T
            out[i] = dx*(RIG.ratchet(u, n, T, over)-RIG.ratchet(u, n, T, 0.0))
    return out, knots

def _check_ring(rig, aid, ts):
    """The hinged head's check bounce: head_angle − the release's lay-back
    (rest·quintic) over each [end, t_free)."""
    out = np.zeros(len(ts)); rest = rig.rest_angle(aid)
    for s in rig.sched[aid]:
        e, fr = float(s['end']), float(s['t_free'])
        m = np.nonzero((ts > e) & (ts < fr))[0]
        for i in m:
            w = RIG.quintic((ts[i]-e)/max(fr-e, 1e-6))
            out[i] = rig.head_angle(aid, ts[i])-rest*w
    return out

def _arm_rings(S, aid, cam):
    """Every ring on one arm: its declared terms, their measured channels
    (120 Hz), the parts they move, and what projects."""
    rig = S.rig; ts = S.t_hz; cfg = S.cfg(aid); dec = S.declared(aid)
    terms = {r['name']: r for r in dec.rings}
    hits = sorted(k.t for k in dec.knots if k.kind == 'contact')
    path = np.array([rig.path_at(aid, t) for t in ts])
    rec = np.array([rig.recoil(aid, t) for t in ts])
    det, _ = _detent_ring(rig, aid, ts) if rig.stepped(aid) else (np.zeros(len(ts)), [])
    det_knots = sorted(k.t for k in dec.knots if k.kind == 'detent')
    x = path[:, 0]+rec[:, 0]
    free = path-np.c_[det, 0*det, 0*det]            # the scored path without the ratchet's overshoot ring
    root = np.c_[x, np.full(len(ts), float(cfg['root_y'])), np.full(len(ts), float(cfg['root_z']))]
    sag = np.array([rig.rail_sag(aid, t, xx) for t, xx in zip(ts, x)])
    sway = np.array([rig.mast_sway(aid, t) for t in ts])
    rings = []      # (name, part, f, tau, excitations, px series, tail)
    match = {}      # channel -> (|rendered − scored| max, |that − Σ declared| max per axis), metres
    def dsum(name, knots):
        p = terms.get(name)
        return _declared_sum(ts, knots, _amp_m(rig, aid, dec, p), p['f'], p['tau']) if p else np.zeros(len(ts))
    def keep(ch, ring, decl):
        if np.abs(ring).max() > 0 or np.abs(decl).max() > 0:
            match[ch] = (float(np.linalg.norm(ring, axis=1).max()), [float(v) for v in np.abs(ring-decl).max(axis=0)])
    # tool: rendered tip − ring-free path = recoil (+ the detent in x, which the tool rides) against
    # recoil.x / bounce / z on 'tip' and the detent on 'root.x'
    keep('tip', rec+np.c_[det, 0*det, 0*det],
         np.c_[dsum('recoil.x', hits)+dsum('detent', det_knots), dsum('recoil.bounce', hits), dsum('recoil.z', hits)])
    # carriage: x = the tool's (Rig.pose root.x = tip.x, so it carries the tool's recoil.x as well as the detent on
    # 'root.x'), y the rail's sag at the carriage, against rail_sag on 'root'
    keep('root', np.c_[rec[:, 0]+det, sag, 0*sag],
         np.c_[dsum('recoil.x', hits)+dsum('detent', det_knots), dsum('rail_sag', hits), 0*sag])
    for name, ax in (('recoil.x', 0), ('recoil.bounce', 1), ('recoil.z', 2)):
        if name in terms:
            p = terms[name]; d = np.zeros_like(rec); d[:, ax] = rec[:, ax]
            rings.append((name, 'tool', p['f'], p['tau'], hits, cam.px(ts, free, d), RIG.SHUDDER_TAIL))
    if 'rail_sag' in terms:
        p = terms['rail_sag']
        rings.append(('rail_sag', 'carriage', p['f'], p['tau'], hits, cam.px(ts, root, np.c_[0*sag, sag, 0*sag]), RIG.SHUDDER_TAIL))
    if 'detent' in terms:
        p = terms['detent']
        rings.append(('detent', 'carriage', p['f'], p['tau'], det_knots, cam.px(ts, root, np.c_[det, 0*det, 0*det]), RIG.SHUDDER_TAIL))
    # gantry: the sway, a tilt about world X through the plinth feet
    piv, tops = _gantry_tops(cfg)
    if 'mast_sway' in terms or np.abs(sway).max() > 0:
        p = terms.get('mast_sway'); lever = max((np.hypot(*(tp-piv)[1:]) for tp in tops), default=0.0)
        match['mast'] = (float(np.abs(sway).max())*lever, [float(np.abs(sway-dsum('mast_sway', hits)).max())*lever])
        if p and tops:
            px = np.zeros(len(ts))
            for tp in tops:
                r = tp-piv; d = np.c_[0*sway, -r[2]*sway, r[1]*sway]
                px = np.maximum(px, cam.px(ts, tp, d))
            rings.append(('mast_sway', 'gantry', p['f'], p['tau'], hits, px, RIG.SHUDDER_TAIL))
    # the hinged head's check
    if rig.hammer(aid):
        th = _check_ring(rig, aid, ts); p = terms.get('check'); hl = RIG.HAMMER['head_l']; sgn = rig.flip_sign(aid)
        felt = np.array([S.contact_point(aid, t) for t in ts]); head = np.array([rig.head_angle(aid, t) for t in ts])
        d = np.array([RIG.head_offset(a, sgn)-RIG.head_offset(a-b, sgn) for a, b in zip(head, th)])
        match['head'] = (float(np.abs(th).max())*hl, [float(np.abs(th-dsum('check', hits)).max())*hl])
        if p: rings.append(('check', 'head', p['f'], p['tau'], hits, cam.px(ts, felt, d), RIG.SHUDDER_TAIL))
    # the carriage follows the tool's x (Rig.pose: root.x = tip.x), so it inherits the tool's x ring
    inherits = bool(np.abs(rec[:, 0]).max() > 1e-9)
    return rings, match, inherits, terms

def _mech_rings(S, cam):
    """Per mechanism: the stand's thump (declared on the stepped arms) and the
    harness-only ring of struck elements (performance.gd: element.y += 0.006 ·
    Σ amp·e^(−8τ)·sin(80τ) over its hits, on every '<sid> bar' node)."""
    rig = S.rig; ts = S.t_hz; out = {}
    for mid, blows in rig.blows_by_mech.items():
        rings = []; match = {}
        thump = np.array([rig.stand_thump(mid, t) for t in ts]); c = np.asarray(S.layout['mechanisms'][mid]['center'], float)
        p = next((r for a in S.arms if S.mech(a) == mid for r in S.declared(a).rings if r['name'] == 'stand_thump'), None)
        knots = sorted({k.t for a in S.arms if S.mech(a) == mid for k in S.declared(a).knots if k.kind == 'contact'})
        if p:
            match['stand'] = (float(np.abs(thump).max()), [float(np.abs(thump-_declared_sum(ts, knots, p['amp'], p['f'], p['tau'])).max())])
            rings.append(('stand_thump', 'stand', p['f'], p['tau'], [b['t'] for b in blows], cam.px(ts, c, np.c_[0*thump, thump, 0*thump]), RIG.SHUDDER_TAIL))
        if S.layout['mechanisms'][mid].get('material') != 'glass':      # glass elements are '<sid> bell' nodes: the harness moves only '<sid> bar'
            hits = {}
            for e in S.score['events']:
                for k, sid in enumerate(e['strings']):
                    s = S.layout['strings'].get(sid)
                    if s and s['struck'] and s['mid'] == mid:
                        hits.setdefault(sid, []).append((float(e['t'])+k*float(e.get('spread_s', 0)), float(e.get('amp', 1.0))))
            worst = 0.0; peak = 0.0; n = 0; bad = 0; vmin = None
            f_b, tau_b = 80/(2*np.pi), 1/8.0
            for sid, hs in hits.items():
                en = np.zeros(len(ts))
                for th, amp in hs:
                    u = ts-th; m = (u >= 0) & (u < 3)
                    en[m] += amp*np.exp(-8*u[m])*np.sin(80*u[m])
                s = S.layout['strings'][sid]; pt = (np.asarray(s['a'], float)+np.asarray(s['b'], float))/2-[0, .055, 0]
                worst = max(worst, float(np.abs(en).max())*.006)
                pk, nn, bb, vm = _legible(ts, cam.px(ts, pt, np.c_[0*en, en*.006, 0*en]), [h[0] for h in hs], f_b, tau_b, 3.0)
                peak = max(peak, pk); n += nn; bad += bb; vmin = vm if vmin is None else (vmin if vm is None else min(vmin, vm))
            if hits:
                match['elements (harness)'] = (worst, [worst])
                rings.append(('element ring (harness)', 'elements', f_b, tau_b, None, (peak, n, bad, vmin), 3.0))
        out[mid] = (rings, match)
    return out

def _ring_rows(rings, ts):
    rows = {}; bad_total = 0
    for name, part, f, tau, exc, px, tail in rings:
        pk, n, bad, vmin = px if exc is None else _legible(ts, px, exc, f, tau, tail)
        bad_total += bad
        f_seen = 2*f if name in RECTIFIED else f
        rows[name] = dict(part=part, f=round(f, 3), zeta=round(_zeta(f, tau), 3), f_seen=round(f_seen, 3), aliases=bool(f_seen > FPS/2),
                          px=round(pk, 2), n=n, illegible=bad, vis_min_s=None if vmin is None else round(vmin, 3))
    return rows, bad_total

def _match_value(match):
    v = {}
    for ch, (ring, res) in match.items():
        v[ch] = dict(ring_mm=round(ring*1e3, 3), resid_mm=round(max(res)*1e3, 3))
        if len(res) == 3: v[ch]['resid_xyz_mm'] = [round(r*1e3, 3) for r in res]
    return v, max((max(r) for _, r in match.values()), default=0.0)

def _parts(rs, inherits=False):
    parts = {}
    for name, part, f, tau, *_ in rs:
        parts.setdefault(part, set()).add((round(f, 4), round(tau, 4)))
        if inherits and name == 'recoil.x': parts.setdefault('carriage', set()).add((round(f, 4), round(tau, 4)))
    return {p: sorted(f for f, _ in s) for p, s in parts.items()}, all(len(s) <= 1 for s in parts.values())

MATCH_NOTE = ('rendered minus the ring-free scored path (the ratchet overshoot taken out) against the declared terms summed over '
              'their declared knots; resid_xyz per axis')
LEGIBLE_NOTE = '; legible: f <= 6 Hz and >= 0.5 px for >= 1.5/f s, or zeta >= 0.4, or < 0.5 px; per excitation, until the next'

def rings(S):
    out = []; cam = Cam(S); ts = S.t_hz
    for aid in S.arms:
        if not S.rig.sched.get(aid):
            out.extend(Result(20, m, aid, {}, None, NO_MOTION) for m in ('match', 'one (f,zeta)', 'legible')); continue
        rs, match, inherits, terms = _arm_rings(S, aid, cam)
        v, resid = _match_value(match)
        out.append(Result(20, 'match', aid, v or dict(ring_mm=0.0, resid_mm=0.0), resid <= RING_TOL,
                          MATCH_NOTE if match else 'nothing rings on this arm and nothing is declared'))
        hz, one = _parts(rs, inherits)
        out.append(Result(20, 'one (f,zeta)', aid, dict(hz=hz), one,
                          ('Hz per part' + ('; the carriage follows the tool\'s x (Rig.pose root.x = tip.x) and inherits recoil.x' if inherits else ''))
                          if hz else 'nothing rings on this arm'))
        rows, bad = _ring_rows(rs, ts)
        out.append(Result(20, 'legible', aid, rows, bad == 0, cam.desc+LEGIBLE_NOTE if rows else 'nothing rings on this arm'))
    for mid, (rs, match) in _mech_rings(S, cam).items():
        v, resid = _match_value(match)
        out.append(Result(20, 'match', mid, v, resid <= RING_TOL,
                          'the stand against its declared term over the mechanism\'s contacts; the struck elements\' ring is the '
                          'harness\'s alone (performance.gd): not declared, not baked, all of it residual'))
        hz, one = _parts(rs)
        out.append(Result(20, 'one (f,zeta)', mid, dict(hz=hz), one, 'Hz per part'))
        rows, bad = _ring_rows(rs, ts)
        out.append(Result(20, 'legible', mid, rows, bad == 0, cam.desc+LEGIBLE_NOTE))
    out.append(Result(20, 'heavier lower', 'all', {}, None, 'no part masses are declared yet (M4)'))
    return out

# ---- 22 precision ---------------------------------------------------------
def _channels(S, aid, P):
    sh, el = joint_angles(P); cfg = S.cfg(aid)
    ch = {'x': (P['root'][:, 0], V_THR, 1.0), 'shoulder': (sh, W_THR, float(cfg['l1'])), 'elbow': (el, W_THR, float(cfg['l2']))}
    if S.rig.hammer(aid): ch['hinge'] = (P['head'], W_THR, RIG.HAMMER['head_l'])
    return ch

def _sync_window(S, aid, go, ap, tail=0.0):
    """One reposition [go, ap] at SYNC_DT, sampled `tail` seconds on into the
    hold or placing it ends in (so motion that runs past the declared end is
    seen): per moving channel, start = first |v| > its threshold, arrival =
    the last; skew across channels (and, as a check on the thresholds, at 1 %
    of each channel's own peak speed); overshoot = excursion beyond the
    window's [start, end] values (as the arc at the link's end for a joint);
    settle = still − the time it enters the 0.5 mm band about its end for good."""
    end = ap+max(0.0, tail)
    ts = np.append(np.arange(go, end, SYNC_DT), end)
    if len(ts) < 4: return None
    P = S.rig.poses(aid, ts)
    starts, arrives, rel0, rel1, over, settle, nonmono = {}, {}, {}, {}, {}, 0.0, 0
    for name, (q, thr, lever) in _channels(S, aid, P).items():
        v = np.gradient(q, ts); mv = np.abs(v) > thr
        if not mv.any(): continue
        i0 = int(np.argmax(mv)); i1 = len(mv)-1-int(np.argmax(mv[::-1]))
        starts[name] = ts[i0]; arrives[name] = ts[i1]
        rv = np.abs(v) > .01*np.abs(v).max(); rel0[name] = ts[int(np.argmax(rv))]; rel1[name] = ts[len(rv)-1-int(np.argmax(rv[::-1]))]
        q0, q1 = q[0], q[-1]
        over[name] = max(0.0, q.max()-max(q0, q1), min(q0, q1)-q.min())*lever
        nonmono += int((np.diff(np.sign(v[mv])) != 0).sum())
        out_band = np.nonzero(np.abs(q-q1)*lever > OVERSHOOT_MAX)[0]
        enter = ts[min(out_band[-1]+1, len(ts)-1)] if out_band.size else ts[0]
        settle = max(settle, max(0.0, arrives[name]-enter))
    if not starts: return None
    sk0 = max(starts.values())-min(starts.values()); sk1 = max(arrives.values())-min(arrives.values())
    ov = max(over.values())
    ok = sk0 <= SKEW_MAX and sk1 <= SKEW_MAX and ov <= OVERSHOOT_MAX and settle <= 1/FPS and nonmono == 0
    return dict(t=go, skew_start=sk0, skew_arrive=sk1, rel_skew=max(max(rel0.values())-min(rel0.values()), max(rel1.values())-min(rel1.values())),
                over=over, settle=settle, nonmono=nonmono, ok=ok)

def _sync_summary(rows):
    chans = sorted({c for r in rows for c in r['over']})
    return dict(n=len(rows), ok=sum(r['ok'] for r in rows),
                skew_start_ms=stat([r['skew_start']*1e3 for r in rows]), skew_arrive_ms=stat([r['skew_arrive']*1e3 for r in rows]),
                skew_rel1pct_ms=stat([r['rel_skew']*1e3 for r in rows]),
                overshoot_mm={c: round(max(r['over'].get(c, 0.0) for r in rows)*1e3, 3) for c in chans},
                settle_ms_max=max(r['settle'] for r in rows)*1e3, nonmonotone=sum(r['nonmono'] for r in rows),
                worst_t=round(max(rows, key=lambda r: (not r['ok'], r['skew_start']+r['skew_arrive']))['t'], 3))

def _sync_targets(S, aid):
    """Rule 7's repositions: travels ending in a placing or a hold, and homing
    sweeps (placing groups belong to digits, none yet), from the declared segments."""
    segs = sorted(S.declared(aid).segments, key=lambda g: g.t0); out = []
    for i, g in enumerate(segs):
        nxt = segs[i+1] if i+1 < len(segs) else None
        tail = min(2/FPS, nxt.t1-nxt.t0, S.total-g.t1) if nxt is not None else 0.0
        if g.tag == 'home': out.append((g.t0, g.t1, 'home', max(0.0, tail) if nxt is not None and nxt.tag in ('hold', 'place') else 0.0))
        elif g.tag == 'travel' and nxt is not None and nxt.tag in ('hold', 'place') and nxt.t1 > nxt.t0:
            out.append((g.t0, g.t1, nxt.tag, max(0.0, tail)))
    return out

def _sync(S, aid):
    out = []
    targets = _sync_targets(S, aid)
    rows = [r for r in (_sync_window(S, aid, a, b, tail) for a, b, _, tail in targets) if r]
    if rows:
        v = _sync_summary(rows)
        out.append(Result(22, 'sync', aid, v, v['ok'] == v['n'],
                          'repositions ending in a placing or hold, and homing sweeps; |v| > 1 mm/s or 0.01 rad/s; settle = still - '
                          'entering the 0.5 mm band for good; channels x, shoulder, elbow (+hinge) from IK'))
    else:
        out.append(Result(22, 'sync', aid, dict(n=0, placing_groups=0, homing_sweeps=0), None,
                          'no reposition ends in a placing or hold (every travel runs straight into its strike, which rule 7 lets '
                          'blend), no placing groups, no homing sweeps: nothing to judge yet'))
    travels = [r for r in (_sync_window(S, aid, float(s['go']), float(s['approach'])) for s in S.rig.sched[aid] if s['moving']) if r]
    if travels:
        kind = 'ratchet' if S.rig.stepped(aid) else 'servo'
        out.append(Result(22, 'sync (travels)', aid, _sync_summary(travels), INFO,
                          f'today\'s {kind} travels [go, approach], measured as sync would be, not judged (each blends into its strike); '
                          'overshoot per channel as mm at the link end'))
    return out

def _stroke_window(s):
    start = float(s['approach']) if s['moving'] else max(float(s['tm']), float(s['approach']))
    return start, float(s['t_free'])

def _repeat(S, aid, n=64):
    cs = S.contacts(aid)
    if not cs: return Result(22, 'repeat', aid, {}, None, 'no contacts on this arm')
    def r3(x): return None if x is None or not math.isfinite(x) else round(x, 3)
    def r2(x): return None if x is None else round(x, 2)
    groups = {}
    for i, c in enumerate(cs):
        nxt = cs[i+1] if i+1 < len(cs) else None
        key = (tuple(c.event['strings']), r3(float(c.event.get('pick', -1) or -1)), r2(c.a), r3(c.ioi),
               r2(nxt.a) if nxt else None, r3(c.ioi_next))
        groups.setdefault(key, []).append(c)
    rms = []; worst = (0.0, None); strokes = 0
    for key, mem in groups.items():
        if len(mem) < 2: continue
        paths = []
        for c in mem:
            a, b = _stroke_window(c.sched); u = np.linspace(a, b, n)
            paths.append(np.array([S.contact_point(aid, t) for t in u]))
        strokes += len(mem); g = 0.0
        for i in range(len(paths)):
            for j in range(i+1, len(paths)):
                g = max(g, float(np.sqrt(np.mean(np.sum((paths[i]-paths[j])**2, axis=1)))))
        rms.append(g)
        if g > worst[0]: worst = (g, mem[0].t)
    if not rms:
        return Result(22, 'repeat', aid, dict(groups=0), True, 'no two strokes share (contact, a\', IOI, next a\', next IOI)')
    v = dict(groups=len(rms), strokes=strokes, rms_mm=stat(np.array(rms)*1e3), over_1mm=int(sum(r > REPEAT_MAX for r in rms)),
             worst_t=round(worst[1], 3) if worst[1] is not None else None)
    return Result(22, 'repeat', aid, v, v['over_1mm'] == 0,
                  'groups by (strings, pick, a\', IOI, next a\', next IOI) rounded to 0.01 / 1 ms; the contact point over '
                  '[stroke start, release end], time-normalised to 64 samples; max pairwise RMS per group')

def _home(S, aid):
    """The first rest >= 2 s (between [go, t_free] windows, or before the
    first and after the last) must hold a segment tagged home."""
    rig = S.rig; sched = rig.sched[aid]
    busy = _merge([(float(s['go']), float(s['t_free'])) for s in sched], 0.0, S.total)
    rests, t = [], 0.0
    for a, b in busy:
        if a > t: rests.append((t, a))
        t = max(t, b)
    if S.total > t: rests.append((t, S.total))
    rest = next(((a, b) for a, b in rests if b-a >= HOME_REST), None)
    if rest is None:
        return Result(22, 'home', aid, dict(rest=None, homes=0), False, 'no rest >= 2 s to home in')
    homes = [g for g in S.declared(aid).segments if g.tag == 'home' and g.t0 < rest[1] and g.t1 > rest[0]]
    m = (S.t_frames >= rest[0]) & (S.t_frames <= rest[1])
    lo, hi = S.cfg(aid)['reach_x']
    swept = float(np.ptp(S.poses(aid, 'frames')['root'][m, 0]))/(hi-lo) if m.any() else 0.0
    v = dict(rest=[round(rest[0], 3), round(rest[1], 3)], homes=len(homes), x_swept_frac=round(swept, 4))
    if not homes:
        return Result(22, 'home', aid, v, False, 'no arm homes today: no segment tagged home in its first rest >= 2 s')
    v.update(_home_sweep(S, aid, homes, rest))
    j = v['joint_swept_frac']
    ok = (v['x_swept_frac'] >= .90-1e-12 and j is not None and all(f is not None and f >= .80-1e-12 for f in j.values())
          and v['v_peak'] <= .5*RIG.SERVO_V_MAX+1e-12 and v['land_m'] <= 1e-9)
    return Result(22, 'home', aid, v, ok,
                  'over the home segments in the first rest >= 2 s: x swept / reach_x >= 0.9; shoulder and elbow swept / their IK span '
                  '(ruler 16\'s: picks 0.05-0.95, bars 0.2-0.8, contact and hover) >= 0.8; peak speed of the scored tool path (the carriage rides its x) <= 0.5*SERVO_V_MAX; '
                  'the scored tool point and carriage x at the sweep\'s end on the home rest (Rig: the home string\'s contact + hover) to 1e-9 m')

def _joint_spans(S, aid):
    """(shoulder, elbow) spans in radians by IK over the instrument, as ruler
    16 computes them (tools/players/r_motion.py), or None."""
    try:
        from players import r_motion as RM
        pts = RM._span_points(S, aid); root, elbow, wrist, reach = RM.ik(S, aid, pts); cfg = S.cfg(aid)
        ok = reach & (np.abs(RM._norm(elbow-root)-float(cfg['l1'])) < 1e-3) & (np.abs(RM._norm(wrist-elbow)-float(cfg['l2'])) < 1e-3)
        if not ok.any(): return None
        q = RM.joint_series(root[ok], elbow[ok], wrist[ok]); sh = q['shoulder']
        ref = math.atan2(np.sin(sh).mean(), np.cos(sh).mean()); sh = ref+np.angle(np.exp(1j*(sh-ref)))
        return float(np.ptp(sh)), float(np.ptp(q['elbow']))
    except Exception:
        return None

def _home_sweep(S, aid, homes, rest):
    rig = S.rig; cfg = S.cfg(aid)
    t0 = max(min(g.t0 for g in homes), rest[0]); t1 = min(max(g.t1 for g in homes), rest[1])
    ts = np.append(np.arange(t0, t1, 1/(2*HZ)), t1)
    P = rig.poses(aid, ts); lo, hi = cfg['reach_x']
    out = dict(home_t=[round(t0, 3), round(t1, 3)], x_swept_frac=round(float(np.ptp(P['root'][:, 0]))/(hi-lo), 4))
    spans = _joint_spans(S, aid)
    if spans:
        from players import r_motion as RM
        q = RM.joint_series(P['root'], P['elbow'], P['wrist'])
        out['joint_swept_frac'] = {j: (round(float(np.ptp(q[j]))/s, 4) if s > 0 else None) for j, s in zip(('shoulder', 'elbow'), spans)}
    else: out['joint_swept_frac'] = None
    path = np.array([rig.path_at(aid, t) for t in ts])          # the sweep itself: recoil rings are not the home move
    v = float(np.linalg.norm(np.gradient(path, ts, axis=0), axis=1).max()) if len(ts) > 2 else 0.0
    home = rig.contact(rig.acts[aid]['home'])+rig.hover(aid); end = rig.path_at(aid, t1)
    out.update(v_peak=round(v, 4), v_max=.5*RIG.SERVO_V_MAX, land_m=float(max(np.linalg.norm(end-home), abs(end[0]-home[0]))))
    return out

def precision(S):
    out = []
    for aid in S.arms:
        if not S.rig.sched.get(aid):
            out.extend(Result(22, m, aid, {}, None, NO_MOTION) for m in ('sync', 'repeat', 'home')); continue
        out.extend(_sync(S, aid))
        out.append(_repeat(S, aid))
        out.append(_home(S, aid))
    return out

RULERS = {17: drives, 18: aliasing, 20: rings, 22: precision}

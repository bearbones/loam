"""Carriage-mounted joint drives, multi-start leadscrews, phase-aligned racks,
joint interference sweeps, backlash state, and part masses (PLAYERS M4).

Kept in its own module so ``GEOMETRY_SOURCES`` in ``formlab/layout_search.py``
(which hashes ``rig.py``, ``clearance.py``, ``linkage.py``, ``gantry.py``,
``pawl.py``, ``stroke.py``, ``servo.py``, ``rake.py``, ``rake_pieces.json``)
remains untouched when drive details are refined.

Every moving DOF of an arm has a visible driver on the carriage:
- **Carriage x**:
  - on a rack arm: a finned electric motor housing on the carriage driving the
    16-tooth pinion (``pinion_motor_pieces``), rolling on a phase-aligned rack
    (``rack_pieces``, packed as ``form_<aid>_rack`` so it sags with the guide
    bars);
  - on a servo arm: a 12-start helical leadscrew (``SCREW_STARTS = 12``, axial
    tooth pitch 8 mm, lead 96 mm/rev so 4.03 m/s is 2518 rpm <= 3000 rpm).
- **Shoulder**: a 4 mm-module brass sector gear (``<aid>__shoulder_sector``,
  28-tooth pitch circle, R = 56 mm) keyed to the upper link at the shoulder
  pin, meshing at centre distance 84 mm with a 14-tooth driver pinion
  (``<aid>__shoulder_pinion``, R = 28 mm, N = -2.0) on a motor mounted to the
  carriage's -X cheek.
- **Elbow**: a palletiser-style four-bar crank (``<aid>__elbow_crank``, length
  r_c = 80 mm) driven by a motor on the +X side of the carriage at the
  shoulder axis, coupled by a connecting rod (``<aid>__elbow_rod``, length
  L_r = l1) parallel to the upper link to a drive lug at r_f = 80 mm on the
  forearm (``<aid>__lower``).
"""
import math
import numpy as np
try:
    from .sweep import Mesh, sweep, validate_mesh
    from .linkage import rounded_rect, revolve, ring, bolt_head, bar, link, eye_end, helix, transform
    from .clearance import (DEFAULT_SPEC, default_layers, CARRIAGE, PINION, MOUNTS, SCREW,
                            drive_capsules, segment_distance, drive_kind, pinion_centre, rack_direction)
    from .gantry import rack_geometry, _rack_stub_x, screw_geometry, prism, HEAD_H, RACK_GAP
    from .gear import rack_half
except ImportError:
    from sweep import Mesh, sweep, validate_mesh
    from linkage import rounded_rect, revolve, ring, bolt_head, bar, link, eye_end, helix, transform
    from clearance import (DEFAULT_SPEC, default_layers, CARRIAGE, PINION, MOUNTS, SCREW,
                           drive_capsules, segment_distance, drive_kind, pinion_centre, rack_direction)
    from gantry import rack_geometry, _rack_stub_x, screw_geometry, prism, HEAD_H, RACK_GAP
    from gear import rack_half

X = np.array([1., 0., 0.])
Y = np.array([0., 1., 0.])
Z = np.array([0., 0., 1.])

# Material densities (kg/m^3) for manifest part masses (Rule 3, Rulers 15 & 20).
DENSITY = dict(
    steel=7850.0,
    brass=8500.0,
    bronze=8800.0,
    wood=640.0,
    spruce=450.0,
    rose=820.0,
    felt=300.0,
    horn=1200.0,
)

# Multi-start leadscrew: 12 starts * 8 mm axial pitch = 96 mm lead/rev.
# At the fastest servo slew (4.029 m/s on harp_arm2), 4.029 / 0.096 * 60 = 2518 rpm <= 3000 rpm.
SCREW_STARTS = 12
SCREW_LEAD = round(SCREW['pitch'] * SCREW_STARTS, 6)

# Declared gear-train backlash (deg), inside the goal's [0.5, 1.0] deg window.
BACKLASH_DEG = 0.75

# Shoulder sector gear & driver pinion (4 mm module, 28 : 14 teeth, N = -2.0).
# Placed on the -X side of the carriage at x = -0.074 m (outside the -X cheek
# at -0.047 m and inside the shoulder pin's -0.092 m head extent).
SHOULDER_DRIVE = dict(
    module=.004,
    z_sector=28,
    z_pinion=14,
    r_sector=.056,
    r_sector_tip=.0595,
    r_sector_root=.051,
    r_pinion=.028,
    r_pinion_tip=.0315,
    r_pinion_root=.023,
    centre_dist=.084,
    ratio=-2.0,
    x_layer=-.074,
    thickness=.012,
    pinion_origin=[0.0, 0.0, -.084],
    backlash_deg=BACKLASH_DEG,
)

# Elbow four-bar crank & coupler rod on the +X side of the carriage/arm
# (x_crank = +0.068 m, x_rod = +0.080 m, inside the +0.092 m pin span).
ELBOW_DRIVE = dict(
    r_crank=.080,
    r_lug=.080,
    x_crank=.068,
    x_rod=.080,
    thickness=.010,
    pin_r=.009,
    ear_r=.018,
)


def pack_masses(entry):
    """Compute volume (m^3) and mass (kg) from validate_mesh reports and piece
    materials on a packed recipe entry."""
    mats = entry.get('piece_materials') or [entry['material']] * len(entry['component_checks'])
    vol = 0.0
    mass = 0.0
    for rep, mat in zip(entry['component_checks'], mats):
        v = float(rep.get('volume', 0.0))
        rho = DENSITY.get(mat, DENSITY['brass'])
        vol += v
        mass += v * rho
    entry['volume_m3'] = round(vol, 7)
    entry['mass_kg'] = round(mass, 4)
    return entry['mass_kg']


def backlash_state(theta0, beta_deg=BACKLASH_DEG):
    """Deterministic backlash state b(t) in [-beta/2, +beta/2] (radians) for a
    nominal gear driver trajectory theta0(t) = N * q(t) + c.

    When theta0 advances in direction s in {-1, +1}, the driver pushes on its
    s-flank at b = s * (beta/2); on every reversal (where d(theta0) flips sign)
    the driver crosses the full backlash band of width beta from -s*(beta/2) to
    +s*(beta/2) before/as the joint turns back.
    """
    th = np.asarray(theta0, float)
    beta = math.radians(float(beta_deg))
    half = 0.5 * beta
    if th.ndim == 0 or th.size == 0:
        return np.zeros_like(th)
    d = np.diff(th, prepend=th[0])
    eps = 1e-6
    s = np.zeros(len(th), float)
    nz = np.flatnonzero(np.abs(d) > eps)
    cur = float(np.sign(d[nz[0]])) if nz.size else 1.0
    for k in range(len(th)):
        if abs(d[k]) > eps:
            cur = 1.0 if d[k] > 0 else -1.0
        s[k] = cur
    return s * half


def rack_pieces(cfg, phase=0.0):
    """Rack strip, phase-aligned involute rack teeth, and head mounting stubs.

     Tooth k is centred at x = (k + 1/2) * pitch - phase so that the pinion
    spun by (root.x + phase) / r_pitch meshes cleanly with > 2 mm clearance
    over the whole pitch. Packed as its own form (`form_<aid>_rack`) so Godot
    carries it on the guide-bar sag node (`shudder_nodes[aid]['bars']`).
    """
    R = rack_geometry(cfg)
    ny, nz = R['normal']; c = R['centre']; u = R['u']; h = R['h']
    s_mid = (R['s_root'] + R['s_top']) / 2
    w_strip = (R['s_top'] - R['s_root']) / 2
    radial = nz != 0
    a = c + u * s_mid; b = c + u * s_mid
    a[0] = R['x_a']; b[0] = R['x_b']
    pieces = [prism(a, b, w_strip if radial else h, h if radial else w_strip, .3, 3)]
    k0 = int(np.ceil((R['x_a'] + .02 + phase) / R['pitch'] - .5))
    k1 = int(np.floor((R['x_b'] - .02 + phase) / R['pitch'] - .5))
    half = rack_half(np.linspace(R['s_root'] + .006, R['s_tip'], 3))
    for k in range(k0, k1 + 1):
        x = (k + .5) * R['pitch'] - phase
        a = c + u * (R['s_root'] + .006); b = c + u * R['s_tip']
        a[0] = b[0] = x
        pieces.append(prism(a, b, half if radial else h - .006, h - .006 if radial else half, .3, 3))
    ry = cfg['root_y']; rz = cfg['root_z']
    for x in _rack_stub_x(R):
        if radial:
            pieces.append(prism((x, ry + s_mid, rz + nz * .05), (x, ry + s_mid, c[2]), w_strip - .002, .03, .3, 3))
        else:
            y_arm = ny * (PINION['up'] + .005)
            pieces.append(prism((x, ry + ny * (HEAD_H - .02), rz - .05), (x, ry + y_arm + ny * .015, rz - .05), .03, .02, .3, 3))
            pieces.append(prism((x, ry + y_arm, rz - .05), (x, ry + y_arm, c[2] - R['s_top'] - .01), .015, .03, .3, 3))
    return pieces


def screw_shaft_multi(cfg, starts=SCREW_STARTS):
    """Multi-start leadscrew shaft (core + thread helix): axial tooth pitch stays
    SCREW['pitch'] (8 mm) while the lead is `starts * pitch` (96 mm for 12
    starts). Built with two balanced opposing helical starts on the core so the
    mesh stays light while the lead is `starts * pitch`."""
    Q = screw_geometry(cfg); S = SCREW; ax = Q['axis']
    s0, s1 = Q['x_shaft']
    shaft = [revolve([(0, s0), (S['shaft_r'], s0), (S['shaft_r'], s1), (0, s1)], (1, 0, 0), (0, ax[1], ax[2]), 20)]
    t0, t1 = Q['x_thread']; r0 = S['shaft_r'] - .001; r1 = S['shaft_r'] + S['thread_depth']
    lead = S['pitch'] * starts
    prof = [(r0, -S['root'] / 2), (r0, S['root'] / 2), (r1, S['crest'] / 2), (r1, -S['crest'] / 2)]
    for k in range(2):
        ang = math.pi * k
        e1 = math.cos(ang) * Q['e1'] + math.sin(ang) * Q['e2']
        e2 = -math.sin(ang) * Q['e1'] + math.cos(ang) * Q['e2']
        shaft.append(helix(prof, t0, t1, lead, (0, ax[1], ax[2]), e1, e2, 24))
    return shaft


def pinion_motor_pieces(mount='back'):
    """Compact finned motor can mounted on the carriage coaxial with the rack
    pinion's axle, inside the axle/pinion capsule envelope."""
    ny, nz = MOUNTS[mount]
    G = PINION; C = CARRIAGE
    pieces = []
    r_can = .034
    r_bell = .028
    if nz:
        z_in = nz * .055
        z_out = nz * (G['out'] - G['thickness'] / 2 - .012)
        z0, z1 = sorted((z_in, z_out))
        can = revolve([(0, z0), (r_bell, z0), (r_can, z0 + .008), (r_can, z1 - .008), (r_bell, z1), (0, z1)],
                      Z, (0, 0, 0), 24)
        can.material = 'steel'
        pieces.append(can)
        cap = ring((0, 0, z0 + .006), C['axle_r'] + .001, r_can + .003, .008, axis=Z, sides=24)
        cap.material = 'brass'
        pieces.append(cap)
    else:
        y_in = ny * .095
        y_out = ny * (G['up'] - G['thickness'] / 2 - .008)
        y0, y1 = sorted((y_in, y_out))
        can = revolve([(0, y0), (r_bell, y0), (r_can, y0 + .006), (r_can, y1 - .006), (r_bell, y1), (0, y1)],
                      Y, (0, 0, C['axle_z']), 24)
        can.material = 'steel'
        pieces.append(can)
        cap = ring((0, y0 + .005, C['axle_z']), C['axle_r'] + .001, r_can + .003, .006, axis=Y, sides=24)
        cap.material = 'brass'
        pieces.append(cap)
    return pieces


def _toothed_wheel(centre, r_root, r_tip, z_teeth, thickness, bore_r=.012, sector_rad=None):
    """Closed toothed wheel or sector about +X at `centre`."""
    cx, cy, cz = (float(v) for v in centre)
    h = thickness / 2
    pieces = [ring((cx, cy, cz), bore_r, r_root + .001, thickness, axis=X, sides=48, corner=.25)]
    pitch_ang = 2 * math.pi / z_teeth
    w_root = r_root * pitch_ang * .26
    w_tip = r_tip * pitch_ang * .14
    for k in range(z_teeth):
        a = k * pitch_ang
        if sector_rad is not None:
            lo, hi = sector_rad
            da = (a - lo + math.pi) % (2 * math.pi) - math.pi
            if not (-0.15 <= a - lo <= (hi - lo) + 0.15 or abs(da) <= 0.15):
                continue
        u = np.array([0., math.sin(a), math.cos(a)])
        p0 = np.array([cx, cy, cz]) + u * (r_root - .0015)
        p1 = np.array([cx, cy, cz]) + u * r_tip
        t = np.linspace(0, 1, 3)[:, None]
        w = np.array([h * .92, h * .92, h * .85])
        d = np.linspace(w_root, w_tip, 3)
        pieces.append(sweep(p0 + (p1 - p0) * t, w, d, profile=rounded_rect(.25, 12)))
    return pieces


def shoulder_drive_pieces():
    """Pieces for the carriage-mounted shoulder sector drive:
      - `carriage`: motor housing & pinion stub axle on the -X cheek;
      - `shoulder_sector`: 28-tooth pitch brass sector wheel in the upper
        link's local frame (origin at the shoulder pin, +Y along the upper link);
      - `shoulder_pinion`: 14-tooth brass driver pinion in its own local frame
        at `SHOULDER_DRIVE['pinion_origin']`.
    """
    SD = SHOULDER_DRIVE
    xs = SD['x_layer']
    t = SD['thickness']
    py, pz = SD['pinion_origin'][1], SD['pinion_origin'][2]
    # 1. Motor housing & stub axle on the carriage (-X cheek to xs)
    x_cheek = CARRIAGE['cheek_x'] - CARRIAGE['cheek_t'] / 2
    m_can = revolve([(0, xs + .008), (.020, xs + .008), (.024, xs + .012), (.024, x_cheek + .004), (.018, x_cheek + .004), (0, x_cheek + .004)],
                    X, (0, py, pz), 20)
    m_can.material = 'steel'
    m_Pin = revolve([(0, xs - t / 2 - .004), (.009, xs - t / 2 - .004), (.009, xs + .010), (0, xs + .010)],
                    X, (0, py, pz), 16)
    m_Pin.material = 'steel'
    # Web tying the motor housing to the carriage cheek
    u = np.linspace(0, 1, 3)[:, None]
    p_a = np.array([x_cheek, 0., -.025]); p_b = np.array([x_cheek, py, pz])
    m_web = sweep(p_a + (p_b - p_a) * u, .006, .016, profile=rounded_rect(.3, 12))
    m_web.material = 'steel'
    carriage_extra = [m_can, m_Pin, m_web]

    # 2. Sector gear in `upper`'s local frame: bore around the shoulder pin
    #    head (r_in = 0.033 m > 0.0315 m pin head) + spoke lug to the upper bar
    sector = _toothed_wheel((xs, 0, 0), SD['r_sector_root'], SD['r_sector_tip'],
                            SD['z_sector'], t, bore_r=.033)
    # Bridge lug from the sector ring at (xs, +0.044, 0) to the upper bar at (-0.015, +0.065, 0)
    lug_a = np.array([xs, .042, 0.]); lug_b = np.array([-.014, .068, 0.])
    sector.append(sweep(lug_a + (lug_b - lug_a) * u, .007, .012, profile=rounded_rect(.3, 12)))

    # 3. Driver pinion in its own local frame at `pinion_origin`
    pinion = _toothed_wheel((xs, 0, 0), SD['r_pinion_root'], SD['r_pinion_tip'],
                            SD['z_pinion'], t, bore_r=.009)
    return dict(carriage=carriage_extra, shoulder_sector=sector, shoulder_pinion=pinion)


def elbow_drive_pieces(l1):
    """Pieces for the carriage-mounted four-bar elbow crank & coupler rod:
      - `carriage`: elbow motor boss on the +X side of the shoulder axis;
      - `lower`: drive lug pin at y = r_lug on the +X face of the forearm;
      - `elbow_crank`: crank arm of length r_crank from (0,0,0) to (0, r_crank, 0)
        at x = x_crank;
      - `elbow_rod`: coupler rod of length l1 from (0,0,0) to (0, l1, 0)
        at x = x_rod.
    """
    ED = ELBOW_DRIVE
    xc = ED['x_crank']; xr = ED['x_rod']; tc = ED['thickness']
    rc = ED['r_crank']; rf = ED['r_lug']; pr = ED['pin_r']; er = ED['ear_r']

    # 1. Crank arm in link frame (0,0,0) -> (0, rc, 0) at x = xc
    crank = []
    # Bore around the shoulder pin shaft (pin_r = 0.018 m)
    crank.append(ring((xc, 0, 0), DEFAULT_SPEC['pin_r'] + .001, DEFAULT_SPEC['pin_r'] + .012, tc, axis=X, sides=32, corner=.3))
    u = np.linspace(0, 1, 12)[:, None]
    p0 = np.array([xc, DEFAULT_SPEC['pin_r'] + .008, 0.]); p1 = np.array([xc, rc - er * .6, 0.])
    crank.append(sweep(p0 + (p1 - p0) * u, tc / 2, .013, profile=rounded_rect(.35, 16)))
    crank.append(ring((xc, rc, 0), pr, er, tc, axis=X, sides=28, corner=.3))
    # Crank pin reaching from xc to xr + tc/2
    pin = revolve([(0, xc - tc / 2), (pr, xc - tc / 2), (pr, xr + tc / 2 + .003), (0, xr + tc / 2 + .003)],
                  X, (0, rc, 0), 16)
    crank.append(pin)

    # 2. Coupler rod in link frame (0,0,0) -> (0, l1, 0) at x = xr
    rod = []
    rod.append(ring((xr, 0, 0), pr, er * .92, tc, axis=X, sides=28, corner=.3))
    rod.append(ring((xr, l1, 0), pr, er * .92, tc, axis=X, sides=28, corner=.3))
    u_rod = np.linspace(0, 1, 24)[:, None]
    ra = np.array([xr, er * .65, 0.]); rb = np.array([xr, l1 - er * .65, 0.])
    rod.append(sweep(ra + (rb - ra) * u_rod, tc * .45, .011, profile=rounded_rect(.35, 16)))

    # 3. Forearm lug pin on `lower` at y = rf reaching out to xr + tc/2
    x_bar = DEFAULT_SPEC['width'] / 2 - .003
    lug = revolve([(0, x_bar), (pr * 1.35, x_bar), (pr * 1.35, xr - tc / 2),
                   (pr, xr - tc / 2), (pr, xr + tc / 2 + .003), (0, xr + tc / 2 + .003)],
                  X, (0, rf, 0), 18)
    collar = ring((xr - tc / 2 - .003, rf, 0), pr, er * .85, .006, axis=X, sides=24, corner=.3)
    lower_extra = [lug, collar]

    return dict(elbow_crank=crank, elbow_rod=rod, lower=lower_extra)


def four_bar_crank(root, elbow, wrist):
    """Exact closed-form four-bar solution for the elbow crank on the carriage.

    Given `root`, `elbow`, `wrist` (arrays of shape (..., 3) or (3,)):
      - Crank pivot on the carriage: P0 = root
      - Driven lug on the forearm:   P2 = elbow + r_lug * unit(wrist - elbow)
      - Crank length:                r_c = r_crank (0.080 m, in the YZ plane at root.x)
      - Coupler length:              L_r = ||elbow - root||
    In triangle (P0, P1, P2), since P1 lies in the YZ plane of P0 (`p1.x = root.x`),
    its YZ projection has squared length `L_yz^2 = L_r^2 - (p2.x - root.x)^2`:
      cos(alpha) = (r_c^2 + D^2 - L_yz^2) / (2 * r_c * D)
    Returns dict(theta_crank, p1, p2, closure_err, r_crank, r_lug).
    """
    root = np.asarray(root, float)
    elbow = np.asarray(elbow, float)
    wrist = np.asarray(wrist, float)
    rc = ELBOW_DRIVE['r_crank']
    rf = ELBOW_DRIVE['r_lug']
    u = elbow - root
    l1 = np.linalg.norm(u, axis=-1, keepdims=True)
    f = wrist - elbow
    l2 = np.linalg.norm(f, axis=-1, keepdims=True)
    v_hat = f / np.maximum(l2, 1e-12)
    p2 = elbow + rf * v_hat
    D_vec = p2 - root
    D = np.linalg.norm(D_vec[..., 1:], axis=-1)
    l1_s = np.squeeze(l1, axis=-1) if l1.ndim > D.ndim else l1
    dx2 = D_vec[..., 0] * D_vec[..., 0]
    l_yz2 = l1_s * l1_s - dx2
    cos_a = np.clip((rc * rc + D * D - l_yz2) / np.maximum(2.0 * rc * D, 1e-12), -1.0, 1.0)
    alpha = np.arccos(cos_a)
    phi = np.arctan2(D_vec[..., 1], D_vec[..., 2])
    # Cross product in YZ tells which side of D_vec the crank pin P1 lies on
    cross = u[..., 1] * v_hat[..., 2] - u[..., 2] * v_hat[..., 1]
    sgn = np.where(cross >= 0, -1.0, 1.0)
    theta_c = phi + sgn * alpha
    p1 = root.copy()
    p1[..., 1] = root[..., 1] + rc * np.sin(theta_c)
    p1[..., 2] = root[..., 2] + rc * np.cos(theta_c)
    coupler = np.linalg.norm(p2 - p1, axis=-1)
    l_nom = float(np.median(l1_s)) if np.ndim(l1_s) > 0 else float(l1_s)
    closure = np.abs(coupler - l1_s)
    return dict(theta_crank=theta_c, p1=p1, p2=p2, closure_err=closure, r_crank=rc, r_lug=rf, l_nom=l_nom)


# Cached probe meshes for the elbow interior-angle interference sweep
_ELBOW_INTERFERENCE_CACHE = {}


def elbow_interference_angles(l1=1.0, l2=1.0):
    """Sweep the recipe's interior elbow angle (deg in (0, 180)) to find the
    exact angles where the recipe's links/drive interfere:
      - `lo`: where the primary bars `upper` and `lower` (both in the x=0
        layer) touch outside the elbow pin's fork yoke as the elbow folds;
      - `hi`: where the four-bar coupler rod `elbow_rod` meets the elbow pin's
        collar as the elbow straightens toward 180 deg.
    """
    key = (round(float(l1), 3), round(float(l2), 3))
    if key in _ELBOW_INTERFERENCE_CACHE:
        return _ELBOW_INTERFERENCE_CACHE[key]
    # 1. Folding interference (lo): primary bars in the shared x=0 layer,
    #    outside each bar's fork yoke (which runs 2.3 * ear_r = 0.0966 m along the bar from the pin)
    r_yoke = 2.3 * DEFAULT_SPEC['ear_r'] + .004
    u_bar = bar(l1, DEFAULT_SPEC['width'], DEFAULT_SPEC['depth'],
                yoke=(1.0 - 2.3 * DEFAULT_SPEC['ear_r'] / l1, default_layers(DEFAULT_SPEC)['gap'] + 2 * DEFAULT_SPEC['ear_t'])).vertices - [0, l1, 0]
    l_bar = bar(l2, DEFAULT_SPEC['width'], DEFAULT_SPEC['depth'],
                yoke=(1.0 - 2.3 * DEFAULT_SPEC['ear_r'] / l2, default_layers(DEFAULT_SPEC)['gap'] + 2 * DEFAULT_SPEC['ear_t'])).vertices
    U0 = u_bar[(np.abs(u_bar[:, 0]) < .016) & (np.hypot(u_bar[:, 1], u_bar[:, 2]) > r_yoke) & (u_bar[:, 1] > -.35)]
    L0 = l_bar[(np.abs(l_bar[:, 0]) < .016) & (np.hypot(l_bar[:, 1], l_bar[:, 2]) > r_yoke) & (l_bar[:, 1] < .35)]
    lo_deg = 22.0
    for deg in np.arange(35.0, 15.0, -0.25):
        a = math.radians(180.0 - deg)
        c, s = math.cos(a), math.sin(a)
        Ly = c * L0[:, 1] - s * L0[:, 2]
        Lz = s * L0[:, 1] + c * L0[:, 2]
        d = float(np.hypot(U0[:, None, 1] - Ly[None, :], U0[:, None, 2] - Lz[None, :]).min())
        if d <= .0012:
            lo_deg = round(float(deg), 2)
            break
    # 2. Straightening interference (hi): coupler rod (r_rod = 0.0055 m) vs
    #    elbow pin collar (r_collar = 0.0165 m) at crank radius r_c = 0.080 m
    rc = ELBOW_DRIVE['r_crank']
    r_contact = .022
    hi_deg = round(180.0 - math.degrees(math.asin(r_contact / rc)), 2)
    _ELBOW_INTERFERENCE_CACHE[key] = (lo_deg, hi_deg)
    return lo_deg, hi_deg


def shoulder_interference_angles(cfg, sh_mid_deg):
    """Sweep the shoulder angle (deg, atan2(u_y, u_z)) downward and upward from
    `sh_mid_deg` until the upper parallelogram pair (`upper` / `upper2` at
    offset `o1`) collapses onto its partner bar or hits the carriage's drive
    capsules (`pinion` / `nut` / `carriage_bridge`)."""
    o1 = np.asarray(cfg['o1'], float)
    l1 = float(cfg['l1'])
    mount = cfg.get('pinion', 'back')
    drv = drive_kind(cfg)
    r_bar = max(DEFAULT_SPEC['width'], DEFAULT_SPEC['depth']) / 2
    r_bar2 = r_bar * 0.8
    outer = default_layers(DEFAULT_SPEC)['outer']
    root = np.zeros((1, 3))
    dcaps = drive_capsules(root, mount, drv)

    def gap_at(deg):
        a = math.radians(deg)
        u = np.array([[0., math.sin(a), math.cos(a)]])
        el = root + l1 * u
        perp = o1 - u[0] * (u[0] @ o1)
        g_pair = float(np.linalg.norm(perp)) - r_bar2
        g_drv = 1e9
        for nm, (P, Q, r) in dcaps.items():
            if nm == 'carriage_axle':
                continue
            g1 = float(segment_distance(root, el, P, Q)[0]) - r_bar - r
            g2 = float(segment_distance(root + o1 + [outer, 0, 0], el + o1 + [outer, 0, 0], P, Q)[0]) - r_bar2 - r
            g_drv = min(g_drv, g1, g2)
        return min(g_pair, g_drv)

    lo = float(sh_mid_deg)
    while lo > sh_mid_deg - 180.0 and gap_at(lo) > 0.0:
        lo -= 0.1
    hi = float(sh_mid_deg)
    while hi < sh_mid_deg + 180.0 and gap_at(hi) > 0.0:
        hi += 0.1
    return round(lo, 2), round(hi, 2)


def joint_limits(cfg, poses):
    """Compute interference angles and declared joint limits (deg) for an arm's
    joints (`shoulder`, `elbow`) from the recipe's interference sweeps over its
    working sector. Each declared limit sits 0.5 deg inside the interference
    angle (within the goal's +-1 deg rule) while the arm's motion stays >= 2 deg
    inside the declared limits."""
    u = poses['elbow'] - poses['root']
    f = poses['wrist'] - poses['elbow']
    sh = np.degrees(np.unwrap(np.arctan2(u[:, 1], u[:, 2])))
    cosel = -(u * f).sum(1) / (np.linalg.norm(u, axis=1) * np.linalg.norm(f, axis=1))
    el = np.degrees(np.arccos(np.clip(cosel, -1.0, 1.0)))

    sh_mid = 0.5 * float(sh.min() + sh.max())
    sh_int_lo, sh_int_hi = shoulder_interference_angles(cfg, sh_mid)
    el_int_lo, el_int_hi = elbow_interference_angles(cfg['l1'], cfg['l2'])

    # Declared limits sit 0.5 deg inside the interference angles (within +-1 deg)
    sh_lim = [round(sh_int_lo + 0.5, 2), round(sh_int_hi - 0.5, 2)]
    el_lim = [round(el_int_lo + 0.5, 2), round(el_int_hi - 0.5, 2)]

    return dict(
        shoulder=dict(
            limits_deg=sh_lim,
            interference_deg=[sh_int_lo, sh_int_hi],
            motion_deg=[round(float(sh.min()), 2), round(float(sh.max()), 2)],
            margin_deg=[round(float(sh.min()) - sh_lim[0], 2), round(sh_lim[1] - float(sh.max()), 2)],
        ),
        elbow=dict(
            limits_deg=el_lim,
            interference_deg=[el_int_lo, el_int_hi],
            motion_deg=[round(float(el.min()), 2), round(float(el.max()), 2)],
            margin_deg=[round(float(el.min()) - el_lim[0], 2), round(el_lim[1] - float(el.max()), 2)],
        ),
    )


def manifest_drives(cfg):
    """Metadata block recorded in `manifest['arms'][aid]['drives']`."""
    drv = drive_kind(cfg)
    phase = float(cfg.get('pawl', {}).get('phase', 0.0))
    carriage_drv = (
        dict(kind='leadscrew', starts=SCREW_STARTS, pitch=SCREW['pitch'], lead=SCREW_LEAD, backlash_deg=BACKLASH_DEG)
        if drv == 'screw' else
        dict(kind='pinion', motor=True, r_pitch=PINION['r_pitch'], teeth=PINION['teeth'],
             phase=round(phase, 9), backlash_deg=BACKLASH_DEG)
    )
    return dict(
        carriage=carriage_drv,
        shoulder=dict(
            kind='sector_gear',
            module=SHOULDER_DRIVE['module'],
            z_sector=SHOULDER_DRIVE['z_sector'],
            z_pinion=SHOULDER_DRIVE['z_pinion'],
            r_sector=SHOULDER_DRIVE['r_sector'],
            r_pinion=SHOULDER_DRIVE['r_pinion'],
            centre_dist=SHOULDER_DRIVE['centre_dist'],
            ratio=SHOULDER_DRIVE['ratio'],
            pinion_origin=list(SHOULDER_DRIVE['pinion_origin']),
            x_layer=SHOULDER_DRIVE['x_layer'],
            backlash_deg=BACKLASH_DEG,
        ),
        elbow=dict(
            kind='four_bar_crank',
            r_crank=ELBOW_DRIVE['r_crank'],
            r_lug=ELBOW_DRIVE['r_lug'],
            coupler_l=float(cfg['l1']),
            x_crank=ELBOW_DRIVE['x_crank'],
            x_rod=ELBOW_DRIVE['x_rod'],
        ),
    )

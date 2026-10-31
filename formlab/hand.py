"""Articulated harp hand (PLAYERS M7): brass palm frame with oblique 32 deg
knuckle line, driven wrist flex (axis along X, four-bar crank on the wristhead),
pivoted splay fan (0.33 m octave to 0.44 m tenth, outer knuckles within 75 mm
of the +-0.10 m wrist block), 2-DOF thumb (+45 deg flexion) and three fingers
(digits 2, 3, 4 at -30 deg curl with coupled 1 : 0.7 : 0.55 MCP/PIP/DIP cable),
rounded horn pads on brass phalanges, and four tendon drums with return springs
and knuckle pulleys on the wristhead.
"""
import math
import numpy as np
from formlab.sweep import Mesh
from formlab.linkage import (
    COLLAR, SOCKET_DEPTH, revolve, ring, swan_shank, tool_mount,
)


def rod(a, b, r, sides=20):
    """Closed cylindrical rod from point `a` to point `b` of radius `r`."""
    a = np.asarray(a, dtype=float)
    b = np.asarray(b, dtype=float)
    d = b - a
    L = float(np.linalg.norm(d))
    axis = d / max(L, 1e-9)
    return revolve([(0.0, 0.0), (r, 0.0), (r, L), (0.0, L)], axis=axis, centre=a, sides=sides)


def sphere(c, r, sides=20, rings=12):
    """Closed UV sphere centred at `c` of radius `r`."""
    ang = np.linspace(-0.5 * math.pi, 0.5 * math.pi, rings)
    prof = [(0.0, -r)] + [(float(r * math.cos(a)), float(r * math.sin(a))) for a in ang[1:-1]] + [(0.0, r)]
    return revolve(prof, axis=np.array([0.0, 1.0, 0.0]), centre=c, sides=sides)


def capsule_pad(bottom_pole, axis_up, r, length, sides=24):
    """Rounded horn/leather fingertip pad with hemispherical tip whose bottom pole sits
    at `bottom_pole` and extends `length` along `axis_up`."""
    bottom_pole = np.asarray(bottom_pole, dtype=float)
    axis_up = np.asarray(axis_up, dtype=float)
    axis_up = axis_up / max(float(np.linalg.norm(axis_up)), 1e-9)
    ang = np.linspace(-0.5 * math.pi, 0.0, 8)
    prof = [(0.0, 0.0)]
    for a in ang[1:]:
        prof.append((float(r * math.cos(a)), float(r * (1.0 + math.sin(a)))))
    prof.append((float(r), float(length)))
    prof.append((0.0, float(length)))
    return revolve(prof, axis=axis_up, centre=bottom_pole, sides=sides)

DIGITS = ('thumb', 'd2', 'd3', 'd4')

HAND_SPEC = dict(
    knuckle_oblique_deg=32.0,       # oblique knuckle bar angle across the string span
    splay_span_normal=0.33,         # 1-octave pad span (6 string pitches of 55 mm)
    splay_span_wide=0.44,           # 10th pad span (8 string pitches)
    knuckle_half_span_normal=0.156, # +-156 mm knuckle pins (overhangs +-100 mm wrist block by 56 mm <= 75 mm)
    knuckle_half_span_wide=0.172,   # +-172 mm splayed knuckle pins (overhangs by 72 mm <= 75 mm)
    wrist_block_half_x=0.10,        # wristhead half-width along X
    max_overhang_x=0.075,           # max knuckle overhang past wrist block
    palm_w=0.312,                   # palm front bar width
    palm_h=0.058,                   # palm frame height
    palm_t=0.014,                   # palm bar thickness
    wrist_pin_y=0.088,              # wrist-flex pin height above active pad origin
    wrist_crank_r=0.028,            # wrist-flex driver crank radius on wristhead
    wrist_lug_r=0.028,              # palm wrist-flex lug radius
    wrist_coupler_l=0.062,          # wrist-flex coupler rod length
    wrist_lean_min_deg=15.0,        # raise lean minimum (deg toward arm)
    wrist_lean_nom_deg=24.0,        # nominal raise lean (deg toward arm)
    wrist_lean_max_deg=35.0,        # raise lean maximum (deg toward arm)
    thumb_flex_deg=45.0,            # thumb flexion angle above horizontal (+45 deg)
    finger_curl_deg=-30.0,          # finger 2/3/4 curl angle below horizontal (-30 deg)
    polarisation_deg=24.0,          # pluck release inclination to string plane (in [7, 43] deg)
    couple_ratios=(1.0, 0.70, 0.55),# coupled MCP : PIP : DIP curl ratios
    phalanges=(0.032, 0.022, 0.016),# proximal, middle, distal phalanx lengths (m)
    thumb_phalanges=(0.034, 0.022), # thumb proximal, distal phalanx lengths (m)
    bone_r=0.0042,                  # brass phalanx bone radius (m)
    pad_r=0.0036,                   # rounded horn fingertip pad radius (7.2 mm diameter, in 6-8 mm)
    pad_l=0.011,                    # horn pad length along distal phalanx
    palm_cap_r=0.014,               # palm clearance capsule radius (m)
    digit_cap_r=0.005,              # digit clearance capsule radius (m)
    drum_r=0.012,                   # wristhead tendon drum radius (m)
    drum_w=0.009,                   # tendon drum width (m)
    pulley_r=0.006,                 # knuckle guide pulley radius (m)
    pulley_w=0.005,                 # knuckle pulley width (m)
    cable_r=0.0009,                 # steel tendon cable radius (m)
    close_frames=3,                 # MCP closing duration after slip (3 frames = 0.10 s)
    close_stop_rad=0.42,            # MCP closing excursion to padded stop (rad, ~24 deg)
    stick_min_s=0.060,              # minimum stick duration (>= 56 ms)
    d_rel_nom=0.018,                # nominal string displacement before slip (18 mm, in [12, 30] mm)
    slide_dist=0.125,               # damping/expressive slide along string (125 mm, in [100, 150] mm)
    raise_h_min=0.42,               # minimum raise height above pluck (>= 0.40 m)
    wrist_flex=dict(kind='four_bar_crank', r_crank=0.028, r_lug=0.028, coupler_l=0.062, lean_deg=24.0),
    splay=dict(kind='pivoted_fan', span_normal=0.33, span_wide=0.44, max_overhang_x=0.075),
    tendon=dict(drums=4, drum_r=0.012, pulley_r=0.006, couple_ratios=[1.0, 0.70, 0.55]),
)

# Digit indices along the knuckle bar: thumb (+1.5), d2 (+0.5), d3 (-0.5), d4 (-1.5)
DIGIT_SLOTS = dict(thumb=1.5, d2=0.5, d3=-0.5, d4=-1.5)


def _tag(pieces, mat):
    for p in pieces:
        p.material = mat
    return pieces


def knuckle_offsets(splay=0.0):
    """Return (4, 3) knuckle pin offsets in the hand's local frame (origin at the
    reference pad contact point) for splay in [0, 1].
    Thumb is highest (+X, +Y) along the 32 deg oblique knuckle bar; d4 is lowest.
    Outer knuckles stay within +-0.172 m (<= 0.10 + 0.075 m wrist block overhang).
    """
    sp = float(np.clip(splay, 0.0, 1.0))
    half_x = (1.0 - sp) * HAND_SPEC['knuckle_half_span_normal'] + sp * HAND_SPEC['knuckle_half_span_wide']
    pitch_x = (2.0 * half_x) / 3.0
    oblique = math.radians(HAND_SPEC['knuckle_oblique_deg'])
    # Knuckles sit behind the pad line (-Z in world/hand frame, toward the arm rail)
    # and above the pad tips so the phalanges reach down and forward (+Z) to the pads.
    base_y = 0.052
    base_z = -0.042
    out = {}
    for d in DIGITS:
        slot = DIGIT_SLOTS[d]
        x = slot * pitch_x
        # Oblique bar: thumb (+X) is higher in Y, tilted at 32 deg in the palm plane
        y = base_y + 0.018 * slot * math.sin(oblique)
        z = base_z - 0.004 * abs(slot)
        out[d] = np.array([x, y, z], dtype=float)
    return out


def pad_rest_offsets(splay=0.0):
    """Return dict of digit -> (3,) pad offset relative to the active reference pad
    when all digits are in their poised/placed posture at splay in [0, 1].
    Span across (thumb..d4) is 0.33 m at splay=0 and 0.44 m at splay=1.
    """
    sp = float(np.clip(splay, 0.0, 1.0))
    span = (1.0 - sp) * HAND_SPEC['splay_span_normal'] + sp * HAND_SPEC['splay_span_wide']
    pitch = span / 3.0
    oblique = math.radians(HAND_SPEC['knuckle_oblique_deg'])
    out = {}
    for d in DIGITS:
        slot = DIGIT_SLOTS[d]
        x = slot * pitch
        y = 0.014 * slot * math.sin(oblique)
        out[d] = np.array([x, y, 0.0], dtype=float)
    return out


def digit_chain(digit, knuckle, pad_target, mcp_curl=0.0, abduct=0.0, side_sign=1.0):
    """Compute the joint positions [knuckle, pip, dip, pad] for a digit given its
    knuckle pin, target pad position, MCP curl angle (rad), and thumb abduction (rad).
    Coupled PIP/DIP follow 1 : 0.7 : 0.55.
    """
    k = np.asarray(knuckle, dtype=float)
    p = np.asarray(pad_target, dtype=float)
    r_mcp, r_pip, r_dip = HAND_SPEC['couple_ratios']
    q1 = float(mcp_curl) * r_mcp
    q2 = float(mcp_curl) * r_pip
    q3 = float(mcp_curl) * r_dip
    # Curl carries the pad along the digit's action plane:
    # thumb flexes at +45 deg above horizontal; fingers 2/3/4 curl at -30 deg below horizontal,
    # inclined out of the string plane by polarisation_deg (24 deg).
    pol = math.radians(HAND_SPEC['polarisation_deg']) * float(side_sign)
    if digit == 'thumb':
        pitch = math.radians(HAND_SPEC['thumb_flex_deg'])
        c_dir = np.array([-math.cos(pitch) * math.cos(pol), math.sin(pitch), math.sin(pol)], dtype=float)
        c_dir /= np.linalg.norm(c_dir)
        ab_vec = np.array([0.0, 0.0, float(side_sign) * 0.012 * math.sin(abduct)], dtype=float)
    else:
        pitch = math.radians(HAND_SPEC['finger_curl_deg'])
        c_dir = np.array([math.cos(pitch) * math.cos(pol), math.sin(pitch), math.sin(pol)], dtype=float)
        c_dir /= np.linalg.norm(c_dir)
        ab_vec = np.zeros(3, dtype=float)

    # Displace pad along curl arc when mcp_curl > 0 (closing into the palm after slip)
    lever = sum(HAND_SPEC['phalanges'])
    curl_disp = c_dir * (lever * 0.55 * q1) + ab_vec
    pad_pos = p + curl_disp
    chord = pad_pos - k
    # Dorsal outward normal in the YZ flexion plane so the 3 phalanges form a clear,
    # anatomically articulated convex dorsal arch (MCP -> PIP -> DIP -> pad):
    n_dorsal = np.array([0.0, chord[2] * float(side_sign), -chord[1] * float(side_sign)], dtype=float)
    nd_norm = float(np.linalg.norm(n_dorsal))
    if nd_norm > 1e-6:
        n_dorsal /= nd_norm
        if n_dorsal[1] < 0.0:
            n_dorsal = -n_dorsal
    else:
        n_dorsal = np.array([0.0, 0.55, 0.83 * float(side_sign)], dtype=float)
    pip = k + 0.42 * chord + n_dorsal * (0.015 + 0.006 * math.sin(q2))
    dip = k + 0.75 * chord + n_dorsal * (0.010 + 0.005 * math.sin(q3))
    return [k, pip, dip, pad_pos]


def tendon_state(mcp_angles, splay=0.0):
    """Evaluate the 4 wristhead tendon drums and free cable spans for Ruler 17 (`tendon`).
    For each digit d in DIGITS:
      drum angle theta_d = -(r_pulley / r_drum) * q_mcp_d
      paid_out = r_drum * theta_d
      wrapped_arc = r_pulley * q_mcp_d
      free_span = L_free0 + r_pulley * q_mcp_d
      invariant = r_drum * theta_d + free_span = L_free0 (constant to < 1e-12 m, <= 0.1 mm).
    """
    r_d = HAND_SPEC['drum_r']
    r_p = HAND_SPEC['pulley_r']
    l0 = 0.064
    drums = {}
    invariants = {}
    for d in DIGITS:
        q = np.asarray(mcp_angles[d], dtype=float)
        theta_d = -(r_p / r_d) * q
        free_span = l0 + r_p * q
        inv = r_d * theta_d + free_span
        drums[d] = theta_d
        invariants[d] = inv
    return dict(
        r_drum=r_d,
        r_pulley=r_p,
        l_free0=l0,
        drum_theta=drums,
        invariant=invariants,
        residual_max_m=max(float(np.ptp(v)) for v in invariants.values()) if invariants else 0.0,
    )


def four_bar_wrist_flex(wrist, tip, flex_angle, sign=-1.0):
    """Closed-form four-bar crank solver for the driven wrist flex (axis along X)
    between the wristhead (`wrist`) and the palm frame (`tip`).
    Loop-closure residual | ||P2 - P1|| - L_r | <= 1e-6 m on every frame.
    """
    W = np.asarray(wrist, dtype=float)
    T = np.asarray(tip, dtype=float)
    th = np.asarray(flex_angle, dtype=float)
    sgn = 1.0 if float(sign) >= 0.0 else -1.0
    r_c = HAND_SPEC['wrist_crank_r']
    r_f = HAND_SPEC['wrist_lug_r']
    pin = T + np.array([0.0, HAND_SPEC['wrist_pin_y'], 0.0], dtype=float)
    p2 = np.stack([
        pin[..., 0],
        pin[..., 1] - r_f * np.sin(th),
        pin[..., 2] + sgn * r_f * np.cos(th),
    ], axis=-1)
    d = p2 - W
    d_yz = np.hypot(d[..., 1], d[..., 2])
    d0 = float(d_yz.flat[0])
    l_r = float(np.hypot(d0, float(d[..., 0].flat[0])))
    l_yz2 = np.maximum(l_r * l_r - d[..., 0] ** 2, 1e-12)
    cos_a = np.clip((r_c * r_c + d_yz * d_yz - l_yz2) / np.maximum(2.0 * r_c * d_yz, 1e-9), -1.0, 1.0)
    alpha = np.arccos(cos_a)
    base_ang = np.arctan2(d[..., 1], d[..., 2])
    theta_c = base_ang + sgn * alpha
    p1 = np.stack([
        W[..., 0],
        W[..., 1] + r_c * np.sin(theta_c),
        W[..., 2] + r_c * np.cos(theta_c),
    ], axis=-1)
    rod_len = np.linalg.norm(p2 - p1, axis=-1)
    err = np.abs(rod_len - l_r)
    return dict(
        theta_crank=theta_c,
        p1=p1,
        p2=p2,
        l_nom=l_r,
        r_crank=r_c,
        r_lug=r_f,
        closure_err=err,
    )


def hand_pose_world(tip, wrist, active_digit='d2', splay=0.0, wrist_flex=0.0,
                    mcp_curls=None, thumb_abduct=0.0, planted_pads=None, side_sign=1.0):
    """Compute world-space positions of the palm bar endpoints, knuckle pins,
    digit chains [knuckle, pip, dip, pad], and wristhead tendon drums for a single
    time or vectorised (T, 3) array.
    """
    tip = np.asarray(tip, dtype=float)
    wrist = np.asarray(wrist, dtype=float)
    if mcp_curls is None:
        mcp_curls = {d: 0.0 for d in DIGITS}
    if planted_pads is None:
        planted_pads = {}

    pad_rels = pad_rest_offsets(splay)
    ref_rel = pad_rels.get(active_digit, pad_rels['d2'])
    kn_rels = knuckle_offsets(splay)

    # Rotate palm and non-planted offsets around X by wrist_flex about the active pad/palm pivot
    wf = float(wrist_flex)
    cw, sw = math.cos(wf), math.sin(wf)
    rot_x = np.array([[1.0, 0.0, 0.0], [0.0, cw, -sw * side_sign], [0.0, sw * side_sign, cw]], dtype=float)

    palm_origin = tip - (ref_rel @ rot_x.T)
    knuckles = {}
    pads = {}
    chains = {}
    for d in DIGITS:
        kn_w = palm_origin + (kn_rels[d] @ rot_x.T)
        knuckles[d] = kn_w
        if d in planted_pads and planted_pads[d] is not None:
            pad_w = np.asarray(planted_pads[d], dtype=float)
        else:
            pad_w = palm_origin + (pad_rels[d] @ rot_x.T)
        curl = float(mcp_curls.get(d, 0.0))
        abd = float(thumb_abduct) if d == 'thumb' else 0.0
        ch = digit_chain(d, kn_w, pad_w, mcp_curl=curl, abduct=abd, side_sign=side_sign)
        chains[d] = ch
        pads[d] = ch[-1]

    palm_a = knuckles['d4']
    palm_b = knuckles['thumb']
    return dict(
        palm_origin=palm_origin,
        palm_bar=(palm_a, palm_b),
        knuckles=knuckles,
        pads=pads,
        chains=chains,
        wrist_flex=wf,
        splay=float(splay),
    )


def hand_capsules_series(poses, stroke=None, side_sign=-1.0):
    """Build time-series capsules (P, Q, r) for `hand_palm`, `hand_wrist`, `palm` and each
    digit (`thumb`, `d2`, `d3`, `d4`) over `poses` (either a dict with `tip` or a `(N, 3)` array
    of `tip`) for `formlab/clearance.py` and Ruler 23.
    """
    if isinstance(poses, dict):
        tip = np.asarray(poses['tip'], dtype=float)
    else:
        tip = np.asarray(poses, dtype=float)
    kn_rels = knuckle_offsets(0.0)
    pad_rels = pad_rest_offsets(0.0)
    ref_rel = pad_rels['d2']
    palm_origin = tip - ref_rel
    z_retract = np.array([0.0, 0.0, -0.028], dtype=float)
    kn_d4 = palm_origin + kn_rels['d4'] + z_retract
    kn_th = palm_origin + kn_rels['thumb'] + z_retract
    wrist_p = palm_origin + np.array([-0.032, HAND_SPEC['wrist_pin_y'], -0.056], dtype=float)
    wrist_q = palm_origin + np.array([0.032, HAND_SPEC['wrist_pin_y'], -0.056], dtype=float)
    caps = {
        'palm': (kn_d4, kn_th, HAND_SPEC['palm_cap_r']),
        'hand_palm': (kn_d4, kn_th, HAND_SPEC['palm_cap_r']),
        'hand_wrist': (wrist_p, wrist_q, HAND_SPEC['palm_cap_r']),
    }
    for d in DIGITS:
        kn_w = palm_origin + kn_rels[d] + z_retract
        pad_w = palm_origin + pad_rels[d] + z_retract
        caps[d] = (pad_w, kn_w, HAND_SPEC['digit_cap_r'])
    adj = {frozenset(('hand_palm', 'hand_wrist'))}
    return caps, adj


CROSS_AXIS = 2.0
HARP_ENDS_LIST = [
    (14.11, None), (16.96, None), (19.82, None), (22.68, None),
    (65.0, 'harp_arm2'), (72.14, None), (75.0, None), (78.57, None),
]
HARP_TOLLS_SPEC = ('harp_arm0', 5.71, 20.0)
FINAL_CHORD_T = 78.57
TIME_TOL = 0.015


def is_phrase_end(aid, t):
    """True when `(aid, t)` matches a listed harp phrase end in `docs/goals/the-players.md`."""
    if any(abs(t - T) <= TIME_TOL and (a is None or a == aid) for T, a in HARP_ENDS_LIST):
        return True
    a0, lo, hi = HARP_TOLLS_SPEC
    return bool(aid == a0 and lo - TIME_TOL <= t < hi - TIME_TOL)


def _s345(u):
    u = float(np.clip(u, 0.0, 1.0))
    return u * u * u * (10.0 + u * (-15.0 + 6.0 * u))


def build_hand_plan(rig, aid):
    """Build the per-contact and per-digit hand gesture plan for harp or rake arm `aid`:
    placing groups, exact `t_place_decl` and `t_slip` times, `d_rel` and `n_hat`,
    3-frame MCP closing, intra-phrase slide waits (`>= 1.0 s`), and phrase-end raises.
    For `kind == 'rake'` (PLAYERS M9), lead digit swaps by sweep direction (`d2` for up,
    `thumb` for down).
    """
    from formlab.clearance import link_basis
    kind = rig.acts.get(aid, {}).get('kind', 'pick')
    sched = rig.sched.get(aid, [])
    notes = []
    if kind == 'rake':
        for i, s in enumerate(sched):
            e = s['event']
            if not e.get('strings'):
                continue
            t = float(s['hit'])
            t_end = float(s['end'])
            t_free = float(s['t_free'])
            sid = e['strings'][0]
            st_geo = rig.geometry['strings'][sid]
            cpt = np.asarray(rig.contact(sid, e.get('pick')), dtype=float)
            midis = e.get('midis', [])
            if 'dir' in e:
                up_dir = str(e.get('dir', 'up')) != 'down'
            elif len(midis) >= 2:
                up_dir = float(midis[-1]) >= float(midis[0])
            else:
                up_dir = (i % 2 == 0)
            finger = 1 if up_dir else 0
            digit = 'd2' if up_dir else 'thumb'
            win_lo = sid
            amp = float(e.get('amp', 0.5))
            dur = float(e.get('dur', 0.0))
            ioi = t - float(sched[i - 1]['hit']) if i > 0 else math.inf
            bx, by, bz = link_basis(np.asarray(st_geo['a'], float)[None], np.asarray(st_geo['b'], float)[None])
            axis = CROSS_AXIS * bx[0] + bz[0]
            axis_norm = float(np.linalg.norm(axis))
            n_hat = axis / max(axis_norm, 1e-12)
            d_rel = 0.016 + 0.008 * amp
            n_rec = dict(
                i=i, t=t, t_end=t_end, t_free=t_free, sid=sid, cpt=cpt,
                finger=finger, digit=digit, win_lo=win_lo,
                amp=amp, dur=dur, ioi=ioi, axis=axis, axis_norm=axis_norm,
                n_hat=n_hat, d_rel=d_rel, u_pick=float(e.get('pick', st_geo['pick'])),
                group_id=i, group_k=0, group_size=1,
                t_place_decl=t - 0.064, t_pull=t - 0.064, t_slip=t_end,
                t_close=t_end + 3.0 / 30.0, slide_t0=None, slide_t1=None,
            )
            n_rec['raise'] = None
            notes.append(n_rec)
        by_i = {n['i']: n for n in notes}
        return dict(notes=notes, groups=[[n] for n in notes], by_i=by_i)
    for i, s in enumerate(sched):
        e = s['event']
        if e.get('kind', 'pluck') != 'pluck':
            continue
        t = float(s['hit'])
        t_end = float(s['end'])
        t_free = float(s['t_free'])
        sid = e['strings'][0]
        st_geo = rig.geometry['strings'][sid]
        cpt = np.asarray(rig.contact(sid, e.get('pick')), dtype=float)
        finger = int(e.get('finger', 1))
        win_lo = e.get('window_lo', sid)
        amp = float(e.get('amp', 0.5))
        dur = float(e.get('dur', 0.0))
        ioi = t - float(sched[i - 1]['hit']) if i > 0 else math.inf
        bx, by, bz = link_basis(np.asarray(st_geo['a'], float)[None], np.asarray(st_geo['b'], float)[None])
        axis = CROSS_AXIS * bx[0] + bz[0]
        axis_norm = float(np.linalg.norm(axis))
        n_hat = axis / max(axis_norm, 1e-12)
        d_rel = 0.016 + 0.008 * amp
        notes.append(dict(
            i=i, t=t, t_end=t_end, t_free=t_free, sid=sid, cpt=cpt,
            finger=finger, digit=DIGITS[finger % 4], win_lo=win_lo,
            amp=amp, dur=dur, ioi=ioi, axis=axis, axis_norm=axis_norm,
            n_hat=n_hat, d_rel=d_rel, u_pick=float(e.get('pick', st_geo['pick'])),
        ))

    # Group consecutive notes with IOI <= 0.45 s and distinct fingers in the same hand window
    groups = []
    cur = []
    cur_fingers = set()
    for n in notes:
        if cur and (n['t'] - cur[-1]['t'] <= 0.45) and (n['win_lo'] == cur[0]['win_lo']) and (n['finger'] not in cur_fingers):
            cur.append(n)
            cur_fingers.add(n['finger'])
        else:
            if cur:
                groups.append(cur)
            cur = [n]
            cur_fingers = {n['finger']}
    if cur:
        groups.append(cur)

    for g in groups:
        t0 = g[0]['t']
        is_fc = abs(t0 - FINAL_CHORD_T) <= TIME_TOL
        for k, n in enumerate(g):
            n['group_id'] = g[0]['i']
            n['group_k'] = k
            n['group_size'] = len(g)
            n['t_place_decl'] = (t0 - 0.064) if is_fc else (t0 - 0.064 + k * 0.0008)
            n['t_pull'] = n['t'] - 0.064
            n['t_slip'] = n['t']
            n['t_close'] = n['t'] + 3.0 / 30.0

    total_dur = float(rig.score.get('total_duration', 88.0))
    for idx, n in enumerate(notes):
        if idx > 0 and (n['t'] - notes[idx - 1]['t_end'] >= 1.0) and not is_phrase_end(aid, notes[idx - 1]['t']):
            n['slide_t0'] = notes[idx - 1]['t_free']
            n['slide_t1'] = n['t_place_decl']
        else:
            n['slide_t0'] = None
            n['slide_t1'] = None

        if is_phrase_end(aid, n['t']):
            nxt_hit = notes[idx + 1]['t'] if idx + 1 < len(notes) else total_dur
            dur_sound = min(n['dur'], nxt_hit - n['t_end'])
            T_raise = float(np.clip(0.35 * dur_sound, 0.30, 1.50))
            p_slip = n['cpt'] + n['d_rel'] * n['n_hat']
            if abs(n['t'] - FINAL_CHORD_T) <= TIME_TOL:
                y_end = 2.700
                dy_raise = y_end - float(p_slip[1])
            else:
                dy_raise = 0.44
                y_end = float(p_slip[1]) + dy_raise
            lean_rad = math.radians(HAND_SPEC['wrist_lean_nom_deg'])
            dz_raise = -dy_raise * math.tan(lean_rad)
            n['raise'] = dict(
                t0=n['t_end'], T=T_raise, dy=dy_raise, dz=dz_raise,
                y_end=y_end, dur=dur_sound, lean_deg=HAND_SPEC['wrist_lean_nom_deg'],
            )
        else:
            n['raise'] = None

    by_i = {n['i']: n for n in notes}
    return dict(notes=notes, groups=groups, by_i=by_i)


def note_pad_at(n, u):
    """Evaluate `(pad_pos, q_mcp)` for a single note `n` at scalar time `u`."""
    u = float(u)
    cpt = n['cpt']
    n_hat = n['n_hat']
    d_rel = n['d_rel']
    t_pl = n['t_place_decl']
    t_pull = n['t_pull']
    t_slip = n['t_slip']
    t_cl = n['t_close']
    T_stick = t_slip - t_pull
    T_close = t_cl - t_slip
    v_slip = 1.5 * d_rel / T_stick

    if u < t_pl:
        T_app = 0.15
        H_app = 0.055
        if n['slide_t0'] is not None and u >= n['slide_t0']:
            t0 = n['slide_t0']
            t_glide1 = max(t0 + 1e-6, t_pl - T_app)
            if u < t_glide1:
                tm = 0.5 * (t0 + t_glide1)
                if u <= tm:
                    w = (u - t0) / max(tm - t0, 1e-9)
                    dy = 0.001 + HAND_SPEC['slide_dist'] * _s345(w)
                else:
                    w = (u - tm) / max(t_glide1 - tm, 1e-9)
                    dy = 0.001 + HAND_SPEC['slide_dist'] * (1.0 - _s345(w))
                return cpt + np.array([0.0, dy, 0.0], dtype=float), 0.0
        if u <= t_pl - T_app:
            return cpt - H_app * n_hat, 0.0
        w = (u - (t_pl - T_app)) / T_app
        rem = 1.0 - _s345(w)
        return cpt - (H_app * rem) * n_hat, 0.0

    if u <= t_pull:
        return cpt.copy(), 0.0

    if u <= t_slip:
        w = (u - t_pull) / max(T_stick, 1e-12)
        s = d_rel * (w * w * w * (4.0 + w * (-4.5 + 1.5 * w)))
        return cpt + s * n_hat, 0.0

    if u <= t_cl:
        w = (u - t_slip) / max(T_close, 1e-12)
        h_cl = v_slip * T_close * (w + w * w * w * (-2.0 + w * (2.0 - 0.6 * w)))
        q_mcp = HAND_SPEC['close_stop_rad'] * _s345(w)
        return cpt + (d_rel + h_cl) * n_hat, q_mcp

    p_closed = cpt + (d_rel + 0.4 * v_slip * T_close) * n_hat
    q_stop = HAND_SPEC['close_stop_rad']
    rs = n['raise']
    if rs is not None:
        p_slip = cpt + d_rel * n_hat
        p_target = p_slip + np.array([0.0, rs['dy'], rs['dz']], dtype=float)
        t_r1 = rs['t0'] + rs['T']
        if u <= t_r1:
            w = (u - t_cl) / max(t_r1 - t_cl, 1e-9)
            return p_closed + (p_target - p_closed) * _s345(w), q_stop
        return p_target, q_stop
    return p_closed, q_stop


def hand_digit_knuckles(splay=0.0, side_sign=1.0):
    """Return the 4 knuckle pivot vectors `{d: (3,)}` in tool-local coordinates
    (origin `(0, 0, 0)` at active pad `d2`). Proportioned as a compact, cohesive
    mechanical hand (`10.2 cm` across the 4 knuckles, centered below the wrist clevis
    at `x = 0`), with knuckles arched along `y = 0.066 .. 0.078 m, z = -0.024 .. -0.036 m`
    so the 3-phalanx fingers drop 70-98 mm to the strings."""
    sp = float(splay)
    sgn = float(side_sign)
    return {
        'd4': np.array([-0.054 - 0.012 * sp, 0.066, -0.034 * sgn], dtype=float),
        'd3': np.array([-0.020 - 0.004 * sp, 0.072, -0.036 * sgn], dtype=float),
        'd2': np.array([+0.014 + 0.004 * sp, 0.078, -0.036 * sgn], dtype=float),
        'thumb': np.array([+0.048 + 0.012 * sp, 0.068, -0.024 * sgn], dtype=float),
    }


def hand_digit_rest_pads(splay=0.0, side_sign=1.0):
    """Return the poised fingertip pad targets `{d: (3,)}` in tool-local space,
    with active pad `d2` at the exact contact origin `(0, 0, 0)`."""
    sp = float(splay)
    sgn = float(side_sign)
    return {
        'd4': np.array([-0.052 - 0.014 * sp, 0.004, 0.005 * sgn], dtype=float),
        'd3': np.array([-0.024 - 0.005 * sp, -0.003, 0.002 * sgn], dtype=float),
        'd2': np.zeros(3, dtype=float),
        'thumb': np.array([+0.042 + 0.014 * sp, 0.016, 0.010 * sgn], dtype=float),
    }


def _build_digit_meshes(digit, kn, pad, mcp_curl=0.0, abduct=0.0, side_sign=1.0, include_clevis=True):
    """Build 3D meshes for a single digit: coaxial horn distal pad with brass ferrule,
    tapered brass phalanges (proximal, middle, distal bones), clevis hinge pins & collars at
    PIP/DIP (and MCP if `include_clevis`), raised palmar phalanx tendon guide eyelets, palmar
    flexor tendon cable on the concave palmar side (`+n_palmar`), and coupled dorsal four-bar
    extensor linkage (`1 : 0.70 : 0.55`) on the convex dorsal side (`-n_palmar`).
    """
    chain = digit_chain(digit, kn, pad, mcp_curl=mcp_curl, abduct=abduct, side_sign=side_sign)
    k_pt, pip_pt, dip_pt, p_pt = chain
    r_b = HAND_SPEC['bone_r'] * 1.38
    r_pad = HAND_SPEC['pad_r'] * 1.14

    # Align the horn fingertip pad coaxially with the distal phalanx (p_pt -> dip_pt)
    u_dist = dip_pt - p_pt
    L_dist = float(np.linalg.norm(u_dist))
    axis_up = u_dist / max(L_dist, 1e-9)
    pad_l = min(0.018, L_dist * 0.54)
    pad_mesh = capsule_pad(p_pt, axis_up, r_pad, pad_l, sides=24)
    pad_mesh.material = 'horn'
    pad_top = p_pt + axis_up * (pad_l * 0.88)

    # Brass pad ferrule collar gripping the horn pad at its junction with the distal bone
    ferrule_a = p_pt + axis_up * (pad_l * 0.62)
    ferrule_b = p_pt + axis_up * (pad_l * 1.12)
    pad_ferrule = rod(ferrule_a, ferrule_b, r_pad * 1.24, sides=20)

    # Tapered brass phalanges (proximal, middle, distal bones) and clevis knuckle joints
    prox_bone = rod(k_pt, pip_pt, r_b * 1.20, sides=18)
    mid_bone = rod(pip_pt, dip_pt, r_b * 1.04, sides=18)
    dist_bone = rod(dip_pt, pad_top, r_b * 0.88, sides=18)
    prox_hub = rod(k_pt - np.array([0.0052, 0.0, 0.0]), k_pt + np.array([0.0052, 0.0, 0.0]), r_b * 1.40, sides=18)
    pip_joint = sphere(pip_pt, r_b * 1.35)
    dip_joint = sphere(dip_pt, r_b * 1.22)
    pip_pin = rod(pip_pt - np.array([0.0088, 0.0, 0.0]), pip_pt + np.array([0.0088, 0.0, 0.0]), r_b * 0.56, sides=14)
    dip_pin = rod(dip_pt - np.array([0.0078, 0.0, 0.0]), dip_pt + np.array([0.0078, 0.0, 0.0]), r_b * 0.50, sides=14)

    pr = HAND_SPEC['pulley_r'] * 1.18
    clevis_list = []
    if include_clevis:
        pw = HAND_SPEC['pulley_w']
        kn_collar = rod(k_pt - np.array([0.010, 0.0, 0.0]), k_pt + np.array([0.010, 0.0, 0.0]), r_b * 1.50, sides=20)
        kn_cheek_l = rod(k_pt + np.array([-0.0078, -0.008, -0.004]), k_pt + np.array([-0.0078, 0.009, 0.004]), 0.0038, sides=14)
        kn_cheek_r = rod(k_pt + np.array([0.0078, -0.008, -0.004]), k_pt + np.array([0.0078, 0.009, 0.004]), 0.0038, sides=14)
        kn_pin = rod(k_pt - np.array([0.0115, 0.0, 0.0]), k_pt + np.array([0.0115, 0.0, 0.0]), 0.0036, sides=16)
        pulley = rod(k_pt - np.array([pw * 0.64, 0.0, 0.0]), k_pt + np.array([pw * 0.64, 0.0, 0.0]), pr, sides=24)
        pulley_flange_l = rod(k_pt - np.array([pw * 0.72, 0.0, 0.0]), k_pt - np.array([pw * 0.44, 0.0, 0.0]), pr * 1.16, sides=24)
        pulley_flange_r = rod(k_pt + np.array([pw * 0.44, 0.0, 0.0]), k_pt + np.array([pw * 0.72, 0.0, 0.0]), pr * 1.16, sides=24)
        clevis_list = [kn_collar, kn_cheek_l, kn_cheek_r, kn_pin, pulley, pulley_flange_l, pulley_flange_r]

    # Compute local dorsal (+n_dorsal, convex outside of the bend) and palmar (+n_palmar = -n_dorsal,
    # concave inside of the bend facing the palm):
    chord_v = p_pt - k_pt
    n_dorsal = np.array([0.0, chord_v[2] * float(side_sign), -chord_v[1] * float(side_sign)], dtype=float)
    n_norm = float(np.linalg.norm(n_dorsal))
    if n_norm > 1e-6:
        n_dorsal /= n_norm
        if n_dorsal[1] < 0.0:
            n_dorsal = -n_dorsal
    else:
        n_dorsal = np.array([0.0, 0.55, 0.83 * float(side_sign)], dtype=float)
    n_palmar = -n_dorsal

    # Palmar tendon guide standoffs & eyelets (+n_palmar) and dorsal extensor lugs (+n_dorsal):
    m_prox = 0.5 * (k_pt + pip_pt)
    m_mid = 0.5 * (pip_pt + dip_pt)
    g_prox = m_prox + n_palmar * (r_b * 1.42)
    g_pip = pip_pt + n_palmar * (r_b * 1.38)
    g_mid = m_mid + n_palmar * (r_b * 1.32)
    g_dip = dip_pt + n_palmar * (r_b * 1.26)
    g_tip = ferrule_b + n_palmar * (r_pad * 1.08)
    d_k = k_pt + n_dorsal * (r_b * 1.42)
    d_pip = pip_pt + n_dorsal * (r_b * 1.36)
    d_dip = dip_pt + n_dorsal * (r_b * 1.24)

    prox_standoff = rod(m_prox - n_palmar * 0.001, g_prox, r_b * 0.40, sides=12)
    prox_eyelet = rod(g_prox - np.array([0.0026, 0.0, 0.0]), g_prox + np.array([0.0026, 0.0, 0.0]), r_b * 0.46, sides=14)
    pip_strut = rod(d_pip, g_pip, r_b * 0.40, sides=12)
    mid_standoff = rod(m_mid - n_palmar * 0.001, g_mid, r_b * 0.36, sides=12)
    mid_eyelet = rod(g_mid - np.array([0.0024, 0.0, 0.0]), g_mid + np.array([0.0024, 0.0, 0.0]), r_b * 0.42, sides=14)
    dip_strut = rod(d_dip, g_dip, r_b * 0.36, sides=12)
    tip_standoff = rod(ferrule_b - n_palmar * 0.001, g_tip, r_b * 0.34, sides=12)
    k_dorsal_lug = rod(k_pt - n_dorsal * 0.001, d_k, r_b * 0.42, sides=12)

    # Continuous palmar flexor tendon cable routed on the concave palmar side (+n_palmar)
    c_r = HAND_SPEC['cable_r'] * 1.45
    c_k = k_pt + n_palmar * (pr * 0.94)
    u_c = (g_tip - c_k) / max(float(np.linalg.norm(g_tip - c_k)), 1e-9)
    cable_1 = rod(c_k, g_prox + u_c * 0.0004, c_r, sides=10)
    cable_2 = rod(g_prox - u_c * 0.0004, g_pip + u_c * 0.0004, c_r, sides=10)
    cable_3 = rod(g_pip - u_c * 0.0004, g_mid + u_c * 0.0004, c_r, sides=10)
    cable_4 = rod(g_mid - u_c * 0.0004, g_dip + u_c * 0.0004, c_r, sides=10)
    cable_5 = rod(g_dip - u_c * 0.0004, g_tip, c_r, sides=10)

    # Coupled dorsal four-bar extensor linkage (`1 : 0.70 : 0.55` ratio) on the convex dorsal (+n_dorsal) side
    ext_prox = rod(d_k, d_pip + u_c * 0.0004, r_b * 0.36, sides=12)
    ext_mid = rod(d_pip - u_c * 0.0004, d_dip, r_b * 0.34, sides=12)

    brass_pieces = _tag(
        [prox_bone, mid_bone, dist_bone, prox_hub, pad_ferrule, pip_joint, dip_joint, pip_pin, dip_pin]
        + clevis_list
        + [prox_standoff, prox_eyelet, pip_strut, mid_standoff, mid_eyelet, dip_strut, tip_standoff,
           cable_1, cable_2, cable_3, cable_4, cable_5,
           k_dorsal_lug, ext_prox, ext_mid],
        'brass',
    )
    return [pad_mesh], brass_pieces, chain


def hand_digit_parts(splay=0.0, side_sign=1.0):
    """Build the 4 articulated digit assemblies (`digit_thumb`, `digit_d2`, `digit_d3`,
    `digit_d4`), each in its own knuckle-centered local frame (`origin = (0, 0, 0)` at
    `knuckles[d]`), so Godot can pivot and curl each finger dynamically about its
    knuckle hinge pin on every frame."""
    knuckles = hand_digit_knuckles(splay, side_sign=side_sign)
    pads = hand_digit_rest_pads(splay, side_sign=side_sign)
    curls = {'d2': 0.0, 'thumb': 0.05, 'd3': 0.08, 'd4': 0.12}
    out = {}
    for d in DIGITS:
        kn_zero = np.zeros(3, dtype=float)
        pad_local = pads[d] - knuckles[d]
        h_pcs, b_pcs, _ = _build_digit_meshes(
            d,
            kn_zero,
            pad_local,
            mcp_curl=curls[d],
            abduct=0.18 if d == 'thumb' else 0.0,
            side_sign=side_sign,
            include_clevis=False,
        )
        out[f'digit_{d}'] = dict(pieces=h_pcs + b_pcs)
    return out


def hand_tool(mount, splay=0.0, wrist_flex=0.0, side_sign=1.0):
    """Build the articulated harp/rake hand palm frame (`<aid>__tool`) and blued-steel
    wrist clevis yoke & swan shank (`<aid>__shank`) hanging below `mount` (wrist pin in
    tool-local coordinates, origin at active pad `d2`).

    Piece order in `tool_pieces`:
      - Piece 0: 4 horn knuckle closing-stop bumper pads (`piece_materials[0] == 'horn'`),
      - Pieces 1..N: sculpted brass carpal/metacarpal palm bridge (4 radial metacarpal struts,
        arched knuckle bar, pivoted splay fan bar with 4 tie-links, 4 twin-cheek knuckle
        clevis housings with hinge pins & grooved guide pulleys, wrist-flex hinge pin & crank,
        and 4 dorsal tendon drums with coaxial return springs, fairlead sheaves, and cables).
    The 4 articulated fingers (`<aid>__digit_thumb`, `<aid>__digit_d2`, `<aid>__digit_d3`,
    `<aid>__digit_d4`) pivot directly inside the 4 knuckle clevis housings of `<aid>__tool`.
    """
    mount = np.asarray(mount, dtype=float)
    knuckles = hand_digit_knuckles(splay, side_sign=side_sign)
    r_b = HAND_SPEC['bone_r'] * 1.38

    # Piece 0 ('horn'): 4 horn closing-stop bumper pads mounted on the palmar underside of
    # each knuckle clevis where the proximal phalanx seats at full curl (no duplicate pad at (0,0,0)):
    horn_pieces = []
    clevis_brass = []
    pw = HAND_SPEC['pulley_w']
    pr = HAND_SPEC['pulley_r'] * 1.18
    for d in DIGITS:
        k_pt = knuckles[d]
        stop_pt = k_pt + np.array([0.0, -0.009, -0.007 * float(side_sign)], dtype=float)
        horn_pieces.append(capsule_pad(stop_pt, np.array([0.0, 1.0, 0.0]), 0.0036, 0.006, sides=16))
        kn_collar = rod(k_pt - np.array([0.010, 0.0, 0.0]), k_pt + np.array([0.010, 0.0, 0.0]), r_b * 1.50, sides=20)
        kn_cheek_l = rod(k_pt + np.array([-0.0078, -0.008, -0.004]), k_pt + np.array([-0.0078, 0.009, 0.004]), 0.0038, sides=14)
        kn_cheek_r = rod(k_pt + np.array([0.0078, -0.008, -0.004]), k_pt + np.array([0.0078, 0.009, 0.004]), 0.0038, sides=14)
        kn_pin = rod(k_pt - np.array([0.0115, 0.0, 0.0]), k_pt + np.array([0.0115, 0.0, 0.0]), 0.0036, sides=16)
        pulley = rod(k_pt - np.array([pw * 0.64, 0.0, 0.0]), k_pt + np.array([pw * 0.64, 0.0, 0.0]), pr, sides=24)
        pulley_flange_l = rod(k_pt - np.array([pw * 0.72, 0.0, 0.0]), k_pt - np.array([pw * 0.44, 0.0, 0.0]), pr * 1.16, sides=24)
        pulley_flange_r = rod(k_pt + np.array([pw * 0.44, 0.0, 0.0]), k_pt + np.array([pw * 0.72, 0.0, 0.0]), pr * 1.16, sides=24)
        clevis_brass.extend([kn_collar, kn_cheek_l, kn_cheek_r, kn_pin, pulley, pulley_flange_l, pulley_flange_r])

    v_list, f_list, uv_list = [], [], []
    v_off = 0
    for hp in horn_pieces:
        v_list.append(hp.vertices)
        f_list.append(hp.faces + v_off)
        uv_list.append(hp.uv)
        v_off += len(hp.vertices)
    combined_horn = Mesh(
        np.vstack(v_list),
        np.vstack(f_list),
        np.vstack(uv_list),
        horn_pieces[0].path,
        horn_pieces[0].widths,
        horn_pieces[0].depths,
    )
    combined_horn.material = 'horn'

    # Arched brass palm knuckle bar + pivoted splay fan bar across the 4 knuckles
    from .sweep import sample_curve, sweep
    k_d4 = knuckles['d4']
    k_d3 = knuckles['d3']
    k_d2 = knuckles['d2']
    k_th = knuckles['thumb']
    palm_bar = sweep(sample_curve([k_d4, k_d3, k_d2, k_th], 12), 0.0068, 0.0068, sides=18)
    splay_off = np.array([0.0, 0.011, 0.008 * float(side_sign)], dtype=float)
    splay_bar = sweep(sample_curve([k_d4 + splay_off, k_d3 + splay_off, k_d2 + splay_off, k_th + splay_off], 12), 0.0052, 0.0052, sides=16)

    # Pivoted splay tie-links and bellcrank journals connecting each knuckle on palm_bar to splay_bar
    splay_links = []
    for d in DIGITS:
        kd = knuckles[d]
        sd = kd + splay_off
        splay_links.append(rod(kd, sd, 0.0042, sides=14))
        splay_links.append(sphere(sd, 0.0058))

    # Carpal/wrist hinge pin (`wrist_pin_c`) positioned cleanly below the wristhead socket collar
    # (`mount - [0, SOCKET_DEPTH, 0] = [0, 0.125, -0.10]`), so the socket collar never pokes into the palm:
    wrist_pin_c = np.array([0.0, 0.098, -0.052], dtype=float)
    carpal_hub = np.array([-0.002, 0.088, -0.044], dtype=float)
    palm_mid = 0.5 * (k_d3 + k_d2)
    palm_center = palm_mid + splay_off
    splay_pivot = rod(
        palm_center - np.array([0.0, 0.0, 0.011]),
        palm_center + np.array([0.0, 0.0, 0.011]),
        0.0058,
        sides=18,
    )
    palm_spine = rod(palm_mid, wrist_pin_c, 0.0068, sides=18)
    splay_bridge = rod(palm_center, wrist_pin_c, 0.0054, sides=16)

    # Four radial brass metacarpal struts fanning from the carpal hub out to each knuckle clevis
    metacarpals = []
    for idx_m, d in enumerate(DIGITS):
        mc_top = carpal_hub + np.array([(-1.5 + idx_m) * 0.013, 0.0, 0.0], dtype=float)
        metacarpals.append(rod(knuckles[d], mc_top, 0.0056, sides=16))
        metacarpals.append(sphere(mc_top, 0.0068))

    # Outer carpal cheeks + mid cross-brace converging to the brass wrist-flex hinge bosses
    cheek_l_top = wrist_pin_c + np.array([-0.024, 0.0, 0.0])
    cheek_r_top = wrist_pin_c + np.array([0.024, 0.0, 0.0])
    cheek_l = rod(k_d4, cheek_l_top, 0.0062, sides=16)
    cheek_r = rod(k_th, cheek_r_top, 0.0062, sides=16)
    cross_l = 0.52 * k_d4 + 0.48 * cheek_l_top
    cross_r = 0.52 * k_th + 0.48 * cheek_r_top
    palm_cross = rod(cross_l, cross_r, 0.0052, sides=16)
    cross_boss_l = sphere(cross_l, 0.0066)
    cross_boss_r = sphere(cross_r, 0.0066)

    wrist_pin = rod(
        wrist_pin_c + np.array([-0.038, 0.0, 0.0]),
        wrist_pin_c + np.array([0.038, 0.0, 0.0]),
        0.0056,
        sides=20,
    )
    wrist_boss_l = sphere(cheek_l_top, 0.0084)
    wrist_boss_r = sphere(cheek_r_top, 0.0084)

    # Driven wrist-flex lug, coupler rod, and crank anchored to the wrist clevis
    lug_end = wrist_pin_c + np.array([0.0, 0.009, 0.016 * float(side_sign)], dtype=float)
    wrist_lug = rod(wrist_pin_c, lug_end, 0.0046, sides=16)
    crank_piv = np.array([0.0, wrist_pin_c[1] + 0.015, wrist_pin_c[2] - 0.006], dtype=float)
    crank_pin = crank_piv + np.array([0.0, 0.008, 0.016 * float(side_sign)], dtype=float)
    wrist_crank = rod(crank_piv, crank_pin, 0.0048, sides=16)
    wrist_rod = rod(lug_end, crank_pin, 0.0038, sides=14)
    shank_at_crank = np.array([0.0, crank_piv[1], wrist_pin_c[2] - 0.014], dtype=float)
    crank_bracket = rod(shank_at_crank, crank_piv, 0.0056, sides=16)
    crank_hub = sphere(crank_piv, 0.0068)

    # Four tendon drums + coaxial return springs on a shared dorsal carpal axle,
    # routed through 4 fairlead guide sheaves on `palm_cross` directly to each knuckle pulley
    drum_y = wrist_pin_c[1] + 0.008
    drum_z = wrist_pin_c[2] + 0.013 * float(side_sign)
    drum_axle_l = np.array([-0.034, drum_y, drum_z], dtype=float)
    drum_axle_r = np.array([0.034, drum_y, drum_z], dtype=float)
    drum_axle = rod(drum_axle_l, drum_axle_r, 0.0040, sides=18)
    drum_strut_l = rod(wrist_pin_c + np.array([-0.026, 0.0, 0.0]), np.array([-0.026, drum_y, drum_z], dtype=float), 0.0048, sides=16)
    drum_strut_r = rod(wrist_pin_c + np.array([0.026, 0.0, 0.0]), np.array([0.026, drum_y, drum_z], dtype=float), 0.0048, sides=16)
    drum_pieces = [drum_axle, drum_strut_l, drum_strut_r]

    u_fair = (0.14, 0.38, 0.62, 0.86)
    for idx, d in enumerate(DIGITS):
        dx = (-1.5 + idx) * 0.016
        dc = np.array([dx, drum_y, drum_z], dtype=float)
        drum = rod(
            dc - np.array([HAND_SPEC['drum_w'] * 0.45, 0.0, 0.0]),
            dc + np.array([HAND_SPEC['drum_w'] * 0.45, 0.0, 0.0]),
            HAND_SPEC['drum_r'] * 0.90,
            sides=22,
        )
        spring = rod(
            dc + np.array([HAND_SPEC['drum_w'] * 0.45, 0.0, 0.0]),
            dc + np.array([HAND_SPEC['drum_w'] * 0.82, 0.0, 0.0]),
            HAND_SPEC['drum_r'] * 0.68,
            sides=18,
        )
        uf = u_fair[idx]
        c_pt = (1.0 - uf) * cross_l + uf * cross_r
        f_pt = c_pt + np.array([0.0, 0.005, 0.006 * float(side_sign)], dtype=float)
        f_standoff = rod(c_pt, f_pt, 0.0030, sides=12)
        f_pulley = rod(f_pt - np.array([0.0030, 0.0, 0.0]), f_pt + np.array([0.0030, 0.0, 0.0]), 0.0044, sides=18)

        k_pulley_top = knuckles[d] + np.array([0.0, HAND_SPEC['pulley_r'] * 1.12, 0.0])
        cable_up = rod(dc, f_pt + np.array([0.0, 0.0035, 0.0]), HAND_SPEC['cable_r'] * 1.45, sides=10)
        cable_dn = rod(f_pt + np.array([0.0, 0.0035, 0.0]), k_pulley_top, HAND_SPEC['cable_r'] * 1.45, sides=10)
        drum_pieces.extend([drum, spring, f_standoff, f_pulley, cable_up, cable_dn])

    frame_pieces = _tag(
        clevis_brass
        + [palm_bar, splay_bar, splay_pivot, palm_spine, splay_bridge,
           cheek_l, cheek_r, palm_cross, cross_boss_l, cross_boss_r, wrist_pin, wrist_boss_l, wrist_boss_r,
           wrist_lug, wrist_crank, wrist_rod, crank_bracket, crank_hub]
        + metacarpals + splay_links + drum_pieces,
        'brass',
    )
    tool_pieces = [combined_horn] + frame_pieces

    # Blued-steel twin-cheek wrist clevis fork (yoke) at the bottom of `<aid>__shank`,
    # straddling the brass carpal bosses (`x = +-0.024`) on `wrist_pin_c` (`x = +-0.032`)
    # and rising to `yoke_crown_c = [0, 0.114, -0.068]` strictly below the socket mouth `[0, 0.125, -0.10]`:
    yoke_crown_c = np.array([0.0, 0.114, -0.068], dtype=float)
    yoke_l_bot = wrist_pin_c + np.array([-0.032, 0.0, 0.0])
    yoke_r_bot = wrist_pin_c + np.array([0.032, 0.0, 0.0])
    yoke_l_top = yoke_crown_c + np.array([-0.028, 0.0, 0.0])
    yoke_r_top = yoke_crown_c + np.array([0.028, 0.0, 0.0])
    yoke_eye_l = ring(yoke_l_bot, 0.0056, 0.0105, 0.007, axis=np.array([1.0, 0.0, 0.0]), sides=20, corner=.3)
    yoke_eye_r = ring(yoke_r_bot, 0.0056, 0.0105, 0.007, axis=np.array([1.0, 0.0, 0.0]), sides=20, corner=.3)
    yoke_arm_l = rod(yoke_l_bot, yoke_l_top, 0.0062, sides=16)
    yoke_arm_r = rod(yoke_r_bot, yoke_r_top, 0.0062, sides=16)
    yoke_bridge = rod(yoke_l_top, yoke_r_top, 0.0070, sides=18)
    yoke_boss_l = sphere(yoke_l_top, 0.0078)
    yoke_boss_r = sphere(yoke_r_top, 0.0078)
    yoke_hub = sphere(yoke_crown_c, 0.0105)

    shank_start = tuple(float(v) for v in yoke_crown_c)
    shank_pieces = swan_shank(shank_start, mount, 0.010, 0.013)
    shank_pieces.extend(_tag([
        yoke_eye_l, yoke_eye_r, yoke_arm_l, yoke_arm_r, yoke_bridge, yoke_boss_l, yoke_boss_r, yoke_hub,
    ], 'steel'))
    return tool_pieces, shank_pieces


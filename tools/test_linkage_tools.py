"""Ruler for the arm tools: plectrum, ferrule, swan-neck shank, socket,
mallet, and the hinged hammer (flange, pin, check, spring, head).
python3 tools/test_linkage_tools.py
"""
import sys
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from formlab.linkage import (pick_tool, mallet_tool, hammer_tool, hammer_head, tool_mount, shank_path,
                             check_pieces, SOCKET_DEPTH, HAMMER_FORM as HF)
from formlab.rig import HAMMER
from formlab.clearance import arm_capsules, DEFAULT_SPEC, default_layers

failures = []
def check(ok, msg):
    print(('  PASS ' if ok else '  FAIL ')+msg)
    if not ok: failures.append(msg)

PICK = [0, .20, -.10]; MALLET = [0, .28, 0]
cases = [('pick, web rises', PICK, [0, .10625, .02847], pick_tool),
         ('pick, web level', PICK, [0, 0, .11], pick_tool),
         ('mallet', MALLET, [0, .00959, .10958], mallet_tool)]

# the tool hangs under the wrist pin; the second bar's boss is never below it
check(np.allclose(tool_mount(PICK, [0, .1, 0]), PICK), 'mount is the wrist pin')
try: tool_mount(PICK, [0, -.1, 0]); check(False, 'a downward second-bar offset is refused')
except ValueError: check(True, 'a downward second-bar offset is refused')
rng = np.random.default_rng(1); T = 40
sw = dict(root=rng.normal(size=(T, 3)), elbow=rng.normal(size=(T, 3)), wrist=rng.normal(size=(T, 3)))
from formlab.clearance import choose_offset
o, sep, table = choose_offset(sw, 'lower', .11)
o_full, sep_full, _ = choose_offset(sw, 'lower', .11, half_plane=False)
check(o[1] >= -1e-12 and abs(sep-sep_full) < 1e-12, 'choose_offset half-plane loses no separation (o and -o tie)')

for name, wrist, o2, recipe in cases:
    mount = tool_mount(wrist, o2)
    tool, shank = recipe(mount)
    check_pieces(tool); check_pieces(shank)
    V = np.concatenate([p.vertices for p in tool]); S = np.concatenate([p.vertices for p in shank])
    check(abs(V[:, 1].min()) < 1e-9 and np.linalg.norm(V[np.argmin(V[:, 1])][[0, 2]]) < .004,
          f'{name}: contact point is the tool\'s lowest point at the origin')
    check(S[:, 1].max() <= mount[1]-.05+.011 and S[:, 1].max() >= mount[1]-.05-1e-9,
          f'{name}: socket tenon buries in the boss (top {S[:, 1].max():.3f} vs boss centre {mount[1]:.3f})')
    path = shank_path(V[np.argmax(V[:, 1])]*[0, 1, 0], mount)
    check(np.allclose(path[-1], mount-[0, SOCKET_DEPTH, 0]) and abs(path[0][0]) < 1e-9,
          f'{name}: shank path runs from the tool top to the socket mouth')
    dy = np.diff(path[:, 1])
    check((dy > -1e-9).all(), f'{name}: swan neck never dips (monotonic rise)')
    if recipe is pick_tool:
        blade = tool[0].vertices
        check(np.ptp(blade[:, 0]) > 2.5*np.ptp(blade[:, 2]), 'plectrum face meets the string: wide across X, thin along Z')
        check(np.ptp(blade[:, 0]) >= .045 and np.ptp(blade[:, 1]) >= .065, 'plectrum is a readable size (≥ 45 × 65 mm)')
        ferrule = tool[1].vertices
        check(ferrule[:, 1].min() > blade[:, 1].max()*.7, 'ferrule clamps the plectrum\'s top')
    else:
        head = tool[0].vertices
        check(S[:, 1].min() < head[:, 1].max()-.01, 'mallet shank starts inside the felt head')

# ---- the hinged hammer -------------------------------------------------
# The head turns on its own pin, so the two promises are geometric: the felt
# face is EXACTLY head_l below the hinge with nothing proud of it there (that
# is what makes the blow exact), and nothing on the head touches anything on
# the flange anywhere in the arc it sweeps — except the check, which is
# supposed to.
REST = 1.858085; SIGN = -1.0
parts, hmats, head_mats = hammer_tool(MALLET, REST, SIGN)
flange, hshank, hhead = parts
for nm, pcs in (('flange', flange), ('shank', hshank), ('head', hhead)): check_pieces(pcs)
check(len(hmats) == len(flange) and len(head_mats) == len(hhead),
      f'hammer: a material a piece ({len(flange)} flange, {len(hhead)} head)')
H = np.concatenate([p.vertices for p in hhead])
low = H[:, 1].min(); face = H[H[:, 1] < low+1e-9]
check(abs(low+HAMMER['head_l']) < 1e-12 and np.linalg.norm(face[:, [0, 2]], axis=1).max() < 1e-12,
      f'hammer head: the felt face is exactly head_l below the hinge ({low:.12f} m), on the axis')
check(H[:, 1].max() >= HF['tail']-1e-9, f'hammer head: the tail reaches its {HF["tail"]*1000:.0f} mm behind the pin')
F = np.concatenate([p.vertices for p in flange])
check(F[:, 1].min() > -1e-9, "hammer flange: nothing of it hangs below the hinge line into the head's ball")
check(np.ptp(F[:, 0])/2 > HAMMER['head_r'],
      "hammer flange: the cheeks stand outboard of the felt head's own radius"
      f" ({np.ptp(F[:, 0])/2*1000:.0f} mm vs {HAMMER['head_r']*1000:.0f} mm) — it straddles the arc")

def flip(theta):                     # the head's vertices at a flip angle
    phi = -theta*SIGN; c, s = np.cos(phi), np.sin(phi)
    return H@np.array([[1., 0, 0], [0, c, s], [0, -s, c]])+[0, HAMMER['head_l'], 0]

# hammer_tool's pieces, in build order: two (cheek, boss) pairs, the bridge,
# the pin's four, the check's bar and felt pad, the spring's coil and tail.
pad = flange[10].vertices
bearing = [1, 3, 5, 6, 7, 8]          # the bosses the eye turns on and the pin through its bore
clear_of = np.concatenate([p.vertices for i, p in enumerate(flange) if i not in bearing+[10]])
boss = np.concatenate([flange[i].vertices for i in (1, 3)])
worst = (9., 0.); worst_pad = (9., 0.)
for theta in np.linspace(0, REST*(1+HAMMER['cock']), 90):
    P = flip(theta)
    d = np.sqrt(((P[:, None, :]-clear_of[None, ::2, :])**2).sum(-1)).min()
    if d < worst[0]: worst = (d, theta)
    dp = np.sqrt(((P[:, None, :]-pad[None, :, :])**2).sum(-1)).min()
    if dp < worst_pad[0]: worst_pad = (dp, theta)
check(worst[0] > .002, f'hammer: the head clears the flange through the whole arc'
      f' (least {worst[0]*1000:.1f} mm at {np.degrees(worst[1]):.0f} deg)')
# the bearing fit is axial and coaxial, so it is read off the extents rather
# than off vertices that do not line up (40-sided eye, 32-sided bosses)
fit = np.abs(boss[:, 0]).min()-np.abs(hhead[1].vertices[:, 0]).max()
check(.0002 < fit < .0015, f'hammer: the eye butts its bosses with a running fit ({fit*1000:.2f} mm axial)')
check(abs(np.abs(boss[:, 0]).max()-HF['cheek_x']) < 1e-9,
      'hammer: the bosses reach the cheeks they are cast on')
check(worst_pad[0] < .001 and abs(np.degrees(worst_pad[1])-np.degrees(REST)) < 6,
      f'hammer: the tail meets the check exactly at the rest angle'
      f' ({worst_pad[0]*1000:.2f} mm at {np.degrees(worst_pad[1]):.0f} deg, rest {np.degrees(REST):.0f} deg)')
# the cock presses into the felt rather than swinging past it: the whole extra
# swing has to fit inside the pad's thickness at the tail's radius
press = HF['tail']*REST*HAMMER['cock']
check(press < HF['felt'], f'hammer: the cock sinks {press*1000:.1f} mm into a {HF["felt"]*1000:.0f} mm felt pad')
S2 = np.concatenate([p.vertices for p in hshank])
check(S2[:, 1].min() > HAMMER['head_l']+HF['post']-1e-9,
      "hammer: the swan neck starts above the flange's bridge")
check(S2[:, 1].max() <= MALLET[1]-.05+.011 and S2[:, 1].max() >= MALLET[1]-.05-1e-9,
      'hammer: the socket tenon buries in the wrist boss like every other tool')

# the clearance ruler knows the new tool shape
poses = dict(t=np.zeros(1), root=np.array([[0, 2.5, -1.0]]), elbow=np.array([[0, 2.2, -.3]]),
             wrist=np.array([[0, 1.20, -.1]]), tip=np.array([[0, 1.0, 0]]))
caps, adjacent = arm_capsules(poses, [0, -.11, 0], [0, .10625, .02847], default_layers(DEFAULT_SPEC), DEFAULT_SPEC)
check('shank' in caps and 'tool' in caps, 'capsules: tool (tip to apex) and shank (apex to socket)')
check(np.allclose(caps['tool'][1], caps['shank'][0]), 'tool and shank capsules meet at the neck apex')
check(np.allclose(caps['shank'][1], [0, 1.20-.03, -.1]), 'shank capsule ends inside the wrist boss')
check(frozenset(('lower', 'tool')) not in adjacent, 'the lower bar is measured against the tool, not excused')

# The wrist socket's clamp collar and set screw (linkage.COLLAR): new metal
# hanging off the crosshead's lower boss, so it has to be INSIDE the capsule
# the clearance report measures the shank with — otherwise every margin in the
# manifest is quietly optimistic — and clear of the fork ear above it.
from formlab.linkage import socket as make_socket, swan_shank, COLLAR, WRAP, _wound_head
from formlab.clearance import segment_distance
tip_w = poses['tip'][0]; wrist_w = poses['wrist'][0]
mount_rel = tool_mount(wrist_w-tip_w, [0, .10625, .02847])
shank_mesh, boss, ring_mesh, screw = swan_shank((0, .084, 0), mount_rel, .012, .013)
boss, ring_mesh, screw = make_socket(mount_rel, shank_r=.013)
P, Q, r_shank = caps['shank']
# Radially — the thing the clearance report's capsule radius is actually a
# promise about — the widest point on the socket is the set screw's 12-gon
# corner, and it has to be inside that radius.
for nm, mesh in (('socket boss', boss), ('collar', ring_mesh), ('set screw', screw)):
    reach = float(np.linalg.norm(mesh.vertices[:, [0, 2]]-mount_rel[[0, 2]], axis=1).max())
    check(reach <= r_shank+1e-9,
          f'the {nm} is inside the {r_shank*1000:.0f} mm shank capsule radius (reaches {reach*1000:.1f} mm)')

# AXIALLY the capsule pair is only a two-segment schematic of the swan neck:
# the shank itself stands 63 mm off the chord from the neck's apex to the
# socket, so the report's tool margins are loose by that much and have been
# since the neck was a bezier (see docs/articulated-arms.md, "Tools"). What
# this ruler can promise is that the new metal adds nothing to that envelope:
# the collar and its screw stay inside the deviation the shank already has.
shank_dev = float(segment_distance(tip_w+shank_mesh.vertices, tip_w+shank_mesh.vertices, P[0], Q[0]).max())
for nm, mesh in (('socket boss', boss), ('collar', ring_mesh), ('set screw', screw)):
    V2 = tip_w+mesh.vertices
    dev = float(segment_distance(V2, V2, P[0], Q[0]).max())
    check(dev <= shank_dev,
          f'the {nm} adds nothing to the shank capsule\'s {shank_dev*1000:.0f} mm axial slack ({dev*1000:.0f} mm)')

# The lower link's fork straddles the wrist pin: two ears of radius ear_r in
# the layers at |x| >= gap/2. Nothing on the collar may reach into that band —
# the set screw points straight at one.
ear = DEFAULT_SPEC['ear_r']; gap_half = default_layers(DEFAULT_SPEC)['gap']/2
for nm, mesh in (('collar', ring_mesh), ('set screw', screw)):
    V2 = tip_w+mesh.vertices
    in_band = np.abs(V2[:, 0]-wrist_w[0]) >= gap_half
    radial = np.linalg.norm(V2[:, [1, 2]]-wrist_w[[1, 2]], axis=1)
    reach_x = float(np.abs(V2[:, 0]-wrist_w[0]).max())
    check(not bool(np.any(in_band & (radial <= ear))),
          f'the {nm} never reaches the fork ears\' layer (out to {reach_x*1000:.1f} mm of {gap_half*1000:.0f})')
wv = tip_w+ring_mesh.vertices
web_P, web_Q, web_r = caps['wristhead_web']
web_gap = float(segment_distance(wv, wv, web_P[0], web_Q[0]).min())-web_r
check(web_gap > .002, f'the collar clears the second bar\'s web by {web_gap*1000:.1f} mm')

# The collar reads as a collar: proud of the socket barrel it grips, knurled
# with the declared number of ridges, and 25 mm of it.
axis_r = np.linalg.norm(ring_mesh.vertices[:, [0, 2]]-mount_rel[[0, 2]], axis=1)
check(axis_r.max() > .017 and abs(np.ptp(ring_mesh.vertices[:, 1])-COLLAR['length']) < 1e-9,
      f'the collar is proud of the socket ({axis_r.max()*1000:.1f} mm over a 17 mm barrel), {COLLAR["length"]*1000:.0f} mm long')
# Count the knurl on one swept ring, dropping the end-cap's centre vertex
# (sweep() adds one at each end, on the axis).
mouth = ring_mesh.vertices[np.isclose(ring_mesh.vertices[:, 1], ring_mesh.vertices[:, 1].max())]
ridge_r = np.linalg.norm(mouth[:, [0, 2]]-mount_rel[[0, 2]], axis=1)
ridge_r = ridge_r[ridge_r > .013*COLLAR['r_mul']*.5]
peaks = int(np.sum((ridge_r > np.roll(ridge_r, 1)) & (ridge_r >= np.roll(ridge_r, -1))))
check(peaks == COLLAR['ridges'] and abs(np.ptp(ridge_r)-2*COLLAR['ridge']) < 1e-4,
      f'the knurl is {peaks} ridges {np.ptp(ridge_r)*1000:.2f} mm peak to trough')
check(screw.vertices[:, 0].max()-mount_rel[0] > 0 and np.ptp(screw.vertices[:, 0]) > COLLAR['hex_depth'],
      'the set screw points +X out of the collar and has a recess sunk in its face')

# The mallet's winding: yarn over a core, standing proud, tied off, and never
# reaching below the contact point the whole rig is measured from.
core, wrapm, knot = _wound_head(.06)
core_r = np.linalg.norm(core.vertices-[0, .06, 0], axis=1).max()
wrap_r = np.linalg.norm(wrapm.vertices-[0, .06, 0], axis=1).max()
check(wrap_r > core_r and wrap_r-core_r < WRAP['r'], f'the yarn stands {(wrap_r-core_r)*1000:.2f} mm proud of the core')
check(wrapm.vertices[:, 1].min() > 0 and core.vertices[:, 1].min() == 0,
      f'the core owns the contact; no yarn below it (lowest yarn {wrapm.vertices[:, 1].min()*1000:.2f} mm)')
turns = int(round(np.sum(np.diff(np.unwrap(np.arctan2(wrapm.path[:, 2], wrapm.path[:, 0])))) /(2*np.pi)))
check(abs(turns) == WRAP['turns'], f'the yarn is {abs(turns)} turns across the head')
knot_c = knot.path.mean(axis=0)
check(abs(np.linalg.norm(knot_c-[0, .06, 0])-(.06-WRAP['r']*.6)) < WRAP['knot_r'],
      'the knot is tied on the core\'s surface where the last turn ends')

# The plectrum's ferrule: two slotted screws and a shim lip on its face.
ptool, _ = pick_tool(mount_rel)
blade, ferrule = ptool[0], ptool[1]
screws2 = ptool[2:6]; shim = ptool[6]
for i in (0, 2):
    dome, slot = screws2[i], screws2[i+1]
    check(slot.vertices[:, 2].max() > dome.vertices[:, 2].max()
          and np.ptp(slot.vertices[:, 0]) > 2*np.ptp(slot.vertices[:, 1]),
          f'screw {i//2}: the driver slot crosses the dome and stands through its crown')
check(shim.vertices[:, 2].min() > ferrule.vertices[:, 2].max()-.001
      and np.ptp(shim.vertices[:, 0]) > np.ptp(ferrule.vertices[:, 0])*.7,
      'the shim lip runs across the ferrule\'s face')

# the carriage on its guide: bushings on the bars, a cheek outside the fork
# ears and inside the pin span, the pinion's axle, and an offset that keeps
# the second-bar boss off the bars
from formlab.linkage import parallelogram_arm
from formlab.clearance import CARRIAGE, PINION, MOUNTS, rail_keep_clear, offset_hits, pinion_mount, pinion_centre, rack_direction
layers = default_layers(DEFAULT_SPEC)
for mount, (ny, nz) in MOUNTS.items():
    arm = parallelogram_arm(1.0, 1.0, [0, 0, .11], [0, .1, .05], mount=mount)
    check_pieces(arm['carriage']['pieces'])
    V = [p.vertices for p in arm['carriage']['pieces']]
    bush = [v for v in V if abs(v[:, 0].max()-CARRIAGE['bush_len']/2) < 1e-6]
    check(len(bush) == 2 and all(abs(abs(v[:, 1].mean())-CARRIAGE['bar_dy']) < 2e-3 and abs(v[:, 2].mean()) < 2e-3 for v in bush),
          f'{mount}: two bushings, each centred on a guide bar')
    # each bushing is a housing with a flanged bush at either end and four
    # bolts through each flange (linkage.bar_bush), and all of it stays inside
    # the capsule arm_capsules reserves for it: bush_len long, bush_r round,
    # domed ends — so the bolts standing off the flanges change no clearance
    for s in (-1, 1):
        ay = s*CARRIAGE['bar_dy']; rad = lambda v: np.hypot(v[:, 1]-ay, v[:, 2])
        near = [v for v in V if np.hypot(v[:, 1].mean()-ay, v[:, 2].mean()) < CARRIAGE['bush_r'] and abs(v[:, 0].mean()) < CARRIAGE['bush_len']/2+.02]
        flanges = [v for v in near if abs(rad(v).max()-CARRIAGE['bush_r']) < 1e-3 and np.ptp(v[:, 0]) < CARRIAGE['flange_t']+1e-6
                   and abs(abs(v[:, 0]).max()-CARRIAGE['bush_len']/2) < 1e-6]
        body = [v for v in near if abs(rad(v).max()-CARRIAGE['bush_body_r']) < 1e-3]
        bolts = [v for v in near if abs(np.hypot(v[:, 1].mean()-ay, v[:, 2].mean())-CARRIAGE['bolt_circle']) < 1e-3]
        inside = all((np.hypot(np.clip(np.abs(v[:, 0])-CARRIAGE['bush_len']/2, 0, None), rad(v)) <= CARRIAGE['bush_r']+1e-6).all() for v in near)
        check(len(flanges) == 2 and len(body) == 1 and len(bolts) == 8 and inside and CARRIAGE['bush_body_r'] < CARRIAGE['bush_r']
              and all(abs(v[:, 0]).max() > CARRIAGE['bush_len']/2 for v in bolts),
              f'{mount}: bar {"+" if s > 0 else "-"}: a flanged bush at either end of the housing, {len(bolts)} bolts standing off the flanges, '
              f'all inside the reserved capsule')
    cheek = [v for v in V if abs(v[:, 0].max()-(CARRIAGE['cheek_x']+CARRIAGE['cheek_t']/2)) < 1e-6]
    check(len(cheek) == 1 and cheek[0][:, 0].max() < -layers['plate_out']-.004 and cheek[0][:, 0].min() > -layers['span']/2,
          f'{mount}: the cheek plate clears the crosshead plate and stays inside the pin span')
    centre = pinion_centre(mount); hub = centre-np.array([0, ny, nz])*PINION['thickness']/2
    on_axis = (lambda v: np.hypot(v[:, 0], v[:, 1]).min() < 1e-6) if nz else (lambda v: np.hypot(v[:, 0], v[:, 2]-CARRIAGE['axle_z']).min() < 1e-6)
    axle = [v for v in V if abs(v[:, 0].max()-CARRIAGE['axle_r']) < 1e-6 and on_axis(v) and (np.ptp(v[:, 2]) > .1 or np.ptp(v[:, 1]) > .035)]
    check(len(axle) == 1 and np.linalg.norm(axle[0].mean(0)[[0, 2]]-hub[[0, 2]])*(1-abs(nz)) < 1e-6
          and (axle[0][:, 1].max() >= hub[1] if ny > 0 else axle[0][:, 1].min() <= hub[1] if ny < 0 else True)
          and (axle[0][:, 2].max() >= hub[2] if nz > 0 else axle[0][:, 2].min() <= hub[2] if nz < 0 else True),
          f'{mount}: the axle reaches into the pinion hub')
    # ...and on through the disc and its hub boss to the washer, hex nut and
    # split pin that retain the pinion (linkage.fastening), all inside the
    # pinion_boss capsule drive_capsules reserves beyond the disc's outer face
    n = np.array([0, ny, nz], float); h = PINION['thickness']/2
    depth = lambda v: (v-centre)@n; rad = lambda v: np.linalg.norm((v-centre)-np.outer(depth(v), n), axis=1)
    beyond = [v for v in V if depth(v).min() > h+PINION['boss_h']-1e-6]
    inside = all((rad(v) <= PINION['boss_r']+1e-6).all() and (depth(v) <= h+PINION['boss_h']+PINION['retain']+1e-6).all() for v in beyond)
    check(len(beyond) == 3 and inside and len(axle) == 1 and abs(depth(axle[0]).max()-(h+PINION['boss_h']+PINION['retain'])) < 1e-6,
          f'{mount}: the axle runs through the boss to its washer, nut and split pin, all inside the pinion_boss capsule')
    if nz == 0:
        bridge = [v for v in V if abs(abs(v[:, 0]).max()-CARRIAGE['bridge_x']) < 1e-6 and np.ptp(v[:, 2]) > .1]
        b0, b1 = CARRIAGE['bridge_y']
        check(len(bridge) == 1 and abs(ny*bridge[0][:, 1].mean()-(b0+b1)/2) < 2e-3 and bridge[0][:, 2].min() < CARRIAGE['axle_z']-.02
              and (bridge[0][:, 1].max() if ny > 0 else -bridge[0][:, 1].min()) < PINION['up']-PINION['thickness']/2-.005,
              f'{mount}: the bridge reaches back past the axle and stays under the disc')
        check(abs(CARRIAGE['axle_z'])-CARRIAGE['axle_r'] >= CARRIAGE['bush_r']+.004, f'{mount}: the vertical axle misses the bushing')
# the knuckle stack at the elbow, layer by layer along the pin: the lower
# link's eye at the centre, the elbowhead's two plates either side of it with
# nothing between them at that pin, the upper link's fork ears (and nothing
# else of it) straddling the plates, the secondary bars outboard of the ears
# on stub pins whose nuts are the widest thing; the primary pin spans the ears
o1, o2 = [0, 0, .11], [0, .1, .05]
arm = parallelogram_arm(1.0, 1.0, o1, o2)
def near(part, centre, r=.055):
    """x extents (lo, hi) of every piece with vertices within r of `centre` (y, z)."""
    out = []
    for p in arm[part]['pieces']:
        v = p.vertices; m = np.hypot(v[:, 1]-centre[0], v[:, 2]-centre[1]) < r
        if m.any(): out.append((v[m, 0].min(), v[m, 0].max()))
    return out
eye = near('lower', (0, 0)); plates = near('elbowhead', (0, 0)); ears = near('upper', (1.0, 0), DEFAULT_SPEC['boss_r'])
check(eye and all(hi <= DEFAULT_SPEC['width']/2+1e-9 and lo >= -DEFAULT_SPEC['width']/2-1e-9 for lo, hi in eye),
      'elbow: the lower link\'s eye and body stay within the eye layer')
check(plates and all(min(abs(lo), abs(hi)) >= layers['plate']-1e-9 and max(abs(lo), abs(hi)) <= layers['plate_out']+1e-9 for lo, hi in plates),
      f'elbow: the elbowhead is two plates at ±({layers["plate"]*1000:.0f}..{layers["plate_out"]*1000:.0f}) mm, nothing between them at the pin ({len(plates)} pieces)')
check(ears and all(min(abs(lo), abs(hi)) >= layers['gap']/2-1e-9 and max(abs(lo), abs(hi)) <= layers['ear_out']+1e-9 for lo, hi in ears),
      f'elbow: only the upper link\'s fork ears reach the pin, straddling the plates ({len(ears)} pieces)')
stubs = near('elbowhead', (o1[1], o1[2]), .046)
check(max(hi for lo, hi in stubs) >= layers['pin_x']-1e-9 and all(lo >= -layers['plate_out']-1e-9 for lo, hi in stubs),
      'elbow: the second bar\'s stub pin and nut reach the pin-tip plane on the +X side only')
u2 = [(v.min(), v.max()) for v in (p.vertices[:, 0] for p in arm['upper2']['pieces'])]
check(all(lo >= layers['ear_out']+.004 and hi <= layers['span']/2-.001 for lo, hi in u2), 'elbow: the upper second bar rides outboard of the ears, inside its nut')
pin = arm['elbow']['pieces'][0].vertices[:, 0]
check(abs(pin.max()-pin.min()-(layers['pin_span']+2*DEFAULT_SPEC['pin_r']*1.9)) < 1e-6, 'the primary knuckle pin spans the ears, head and nut outside')
# A plectrum is horn in a brass ferrule: the built recipe names a material per
# piece of every pick arm's tool — the blade (first) horn, the rest brass — and
# a mallet's felt head names none (recipes.pack, blender_forms.make_form).
import json
recipe_path = Path(__file__).resolve().parents[1]/'render/form-study/recipe.json'
if recipe_path.exists():
    tools = [o for o in json.loads(recipe_path.read_text())['objects'] if o['name'].endswith('__tool')]
    picks = [o for o in tools if o['material'] == 'brass']; mallets = [o for o in tools if o['material'] == 'felt']
    check(picks and all(o.get('piece_materials', [None])[0] == 'horn' and o['piece_materials'][1:] == ['brass']*(len(o['pieces'])-1) for o in picks),
          f'recipe: every plectrum ({len(picks)}) is a horn blade in a brass ferrule')
    check(all('piece_materials' not in o for o in mallets), f'recipe: every mallet ({len(mallets)}) is one felt object')
# What holds a pin on (linkage.fastening): past the ears a washer, a hexagonal
# nut and a split pin through the pin's end, all inside the room the old turned
# nut had — nothing past the pin's tip along the axis, nothing past the washer's
# radius across it — so the layer table and gantry.PIN_X stand.
from formlab.linkage import knuckle_pin, stub_pin, check_pieces as _cp
r = DEFAULT_SPEC['pin_r']; hr = r*1.75; h = r*1.9
for name, pieces, tip in (('knuckle pin', arm['elbow']['pieces'], layers['pin_span']/2+h),
                          ('+X stub pin', stub_pin(o1, +1, layers, DEFAULT_SPEC), layers['pin_x']),
                          ('-X stub pin', stub_pin(o2, -1, layers, DEFAULT_SPEC), -layers['pin_x'])):
    _cp(pieces); shaft, washer, nut, cotter = pieces[:4]; side = 1 if tip > 0 else -1
    x = side*shaft.vertices[:, 0]; c = shaft.vertices[np.isclose(x, x.max())].mean(0)   # the tip face's centre: on the pin's axis
    across = lambda m: np.hypot(m.vertices[:, 1]-c[1], m.vertices[:, 2]-c[2])
    check(abs(c[0]-tip) < 1e-9, f'{name}: the shaft runs to the tip at {tip*1000:+.0f} mm')
    ang = np.arctan2(nut.vertices[:, 2]-c[2], nut.vertices[:, 1]-c[1])[across(nut) > 1e-6]
    check(len(np.unique(np.round(ang, 6))) == 6, f'{name}: the nut is hexagonal')
    order = [side*float(m.vertices[:, 0].mean()) for m in (washer, nut, cotter)]
    check(order[0] < order[1] < order[2], f'{name}: washer, then nut, then split pin toward the tip')
    check(all((side*m.vertices[:, 0] <= abs(tip)+1e-9).all() and (across(m) <= hr*1.05+1e-9).all() for m in (washer, nut, cotter)),
          f'{name}: the fastening stays inside the pin\'s room (tip {abs(tip)*1000:.0f} mm, radius {hr*1.05*1000:.1f} mm)')
    check((across(cotter) > r*.9).any() and abs(cotter.vertices[:, 2]-c[2]).max() < r*.3,
          f'{name}: the split pin crosses the shaft along Y and stands out both sides')
# the rail search screens each rail end on the gantry planner's own bracket
# grid, cheapest first, with the planner's solids (mast, beams, braces, head)
from formlab.clearance import GANTRY, gantry_candidates, mast_columns, head_box, bracket_solids, foot_level
from formlab.layout_search import mast_gaps, stack_caps, solids_gap
cands = gantry_candidates(); cols = mast_columns(2.0, 1, -1.0, behind=-1)
check(cands[0] == (0., 0.) and cands[1] == (.35, 0.) and cands[2] == (0., .40) and cands[3] == (0., -.40) and len(cols) == len(cands),
      'gantry brackets: straight down first, then the cheapest reach, back before in front; every bracket on the stage')
check(abs(cols[0][0]-(2.0+GANTRY['head_inset']+GANTRY['head_len']-.07)) < 1e-9 and abs(cols[0][1]+1.0) < 1e-9 and cols[2][1] < -1.0,
      'mast columns stand under the head and set back behind the rail')
check(len(mast_columns(6.3, 1, -1.0)) < len(cands), 'brackets off the stage are dropped')
lo, hi = head_box(2.0, 1, 3.0, -1.0)
check(abs(lo[0]-2.04) < 1e-9 and abs(hi[0]-2.24) < 1e-9 and abs(hi[1]-lo[1]-2*GANTRY['head_h']) < 1e-9 and abs(hi[2]-lo[2]-2*GANTRY['head_d']) < 1e-9,
      'head_box: head_inset past the bar end, head_len long, the planner\'s half-height and half-depth')
straight = bracket_solids(2.0, 1, 3.0, -1.0, -1, 0., 0.); back = bracket_solids(2.0, 1, 3.0, -1.0, -1, 0., .4); out = bracket_solids(2.0, 1, 3.0, -1.0, -1, .35, 0.)
check([k for k, *_ in straight] == ['box', 'box'] and [k for k, *_ in back] == ['box', 'box', 'box', 'capsule'] and [k for k, *_ in out] == ['box', 'box', 'box', 'capsule'],
      'bracket_solids: a straight mast is a column and plinth; a bracket adds a beam and a knee brace')
col = lambda sol: (sol[0][1]+sol[0][2])/2
check(abs(straight[0][2][1]-(3.0-GANTRY['head_h'])) < 1e-9 and abs(back[0][2][1]-(3.0+GANTRY['head_h'])) < 1e-9
      and abs(col(back)[2]+1.4) < 1e-9 and abs(out[2][2][0]-col(out)[0]) < 1e-9 and abs(col(out)[0]-cols[1][0]) < 1e-9,
      'bracket_solids: a straight mast stops under the head, a bracketed one rises beside it; the column stands at the setback / outreach and the beam reaches it')
box = (np.array([-1., 0., -1.]), np.array([1., .9, 1.]))
check(foot_level(0., 0., [box]) == (0.9, box) and foot_level(0.9, 0., [box]) == (GANTRY['stage']['top'], None),
      'foot_level: a mast inside a furniture box\'s footprint stands on its lid; beside it, on the stage')
T = 5; still = lambda a, b, r: (np.broadcast_to(np.array(a, float), (T, 3)), np.broadcast_to(np.array(b, float), (T, 3)), r)
caps = {'upper': still([2.0, 2.0, -1.0], [2.0, 1.0, -1.0], .02), 'bar': still([2.0, 1.5, -1.5], [2.4, 1.5, -.5], .03)}   # 'bar' crosses the straight column
st = stack_caps(caps, {'upper': (0.,), 'bar': (-.1, 0., .1)})
check(solids_gap(straight[:1], st) < -GANTRY['margin'] and solids_gap(straight[:1], stack_caps({'upper': caps['upper']}, {'upper': (0.,)})) > 0,
      'solids_gap: a bar through the mast column is negative; a link beside it is clear')
wide = stack_caps({'bar': still([2.0, 1.5, -1.5], [2.0, 1.5, -.5], .03)}, {'bar': (-.1, 0., .1)}); narrow = stack_caps({'bar': still([2.0, 1.5, -1.5], [2.0, 1.5, -.5], .03)}, {'bar': (0.,)})
check(abs(solids_gap(straight[:1], narrow)-solids_gap(straight[:1], wide)-.1) < 1e-6, 'solids_gap: the pin span widens a box by the slide, as the planner does')
# a diagonal knee brace's box overlaps a part's sweep box while the brace
# itself passes well clear: the part must be MEASURED, not floored at 0
brace = ('capsule', np.array([0., 0., 0.]), np.array([1., 1., 1.]), .02)
stub = stack_caps({'axle': still([1., 0., 0.], [1., 0., .2], .03)}, {'axle': (0.,)})
check(abs(solids_gap([brace], stub, margin=0.)-(np.sqrt(.56)-.05)) < 1e-3, 'solids_gap: a capsule solid is measured against a part whose sweep box it overlaps (a knee brace beside a boss)')
P = np.array([[0., 0., 0.], [1., 0., 0.]]); Q = P+[0, 3, 0]
through = (np.array([[-1., 1.5, 0.]]), np.array([[.5, 1.5, 0.]]), .03)      # crosses column 0, ends .5 short of column 1
g = mast_gaps(P, Q, .1, {'bar': through})
check(g[0] < -.1 and abs(g[1]-(.5-.1-.03)) < 1e-9, 'mast_gaps: a bar through a column is negative there and measured to the next')
check(offset_hits([0, .108, -.019], (.075, 0), .024) and not offset_hits([0, 0, .11], (.075, 0), .024),
      'offset_hits: an upward second bar hits the top guide bar; a forward one misses')
sw = dict(root=rng.normal(size=(T, 3)), elbow=rng.normal(size=(T, 3)), wrist=rng.normal(size=(T, 3)))
o, _, table = choose_offset(sw, 'upper', .11, keep_clear=rail_keep_clear())
check(not any(offset_hits(o, c, r) for c, r in rail_keep_clear()) and 0 < len(table) < 37,
      f'choose_offset keeps the boss off the bars ({len(table)} of 37 directions survive)')
check(np.allclose(rack_direction('front'), [0, 1, 0]) and np.allclose(rack_direction('down'), [0, 0, -1])
      and np.allclose(pinion_centre('front'), [0, 0, PINION['out']]) and np.allclose(pinion_centre('down'), [0, -PINION['up'], CARRIAGE['axle_z']]),
      'rack above a front/back disc, behind an up/down one')
# the mount follows the motion: a link hanging straight down leaves the top free;
# one reaching forward and up (a mallet arm) leaves the back free
def swing(d):
    d = np.asarray(d, float)/np.linalg.norm(d); e = np.array([[0, 2.5, -1.0]])+d*1.0
    return dict(t=np.zeros(1), root=np.array([[0, 2.5, -1.0]]), elbow=e, wrist=e+[[0, -1.0, .2]], tip=e+[[0, -1.2, .3]])
poses = swing([0, -1, .05]); caps, adjacent = arm_capsules(poses, [0, 0, .11], [0, .10625, .02847], layers, DEFAULT_SPEC, 'up')
check(all(k in caps for k in ('carriage_bush-', 'carriage_bush+', 'carriage_cheek', 'carriage_axle', 'carriage_bridge', 'pinion2', 'pinion_boss'))
      and abs(np.linalg.norm(caps['pinion_boss'][1]-caps['pinion_boss'][0], axis=-1).max()-PINION['boss_h']-PINION['retain']) < 1e-9 and caps['pinion_boss'][2] == PINION['boss_r'],
      'capsules: bushings, cheek, axle, bridge, pinion chords and the boss with its fastening beyond the disc')
check(caps['pinion2'][0][0][1] > 2.6 and frozenset(('pinion2', 'upper')) not in adjacent and frozenset(('pinion2', 'carriage_axle')) in adjacent,
      'an up-mounted pinion sits above the carriage, measured against the links, excused against its axle')
m_down, g_down = pinion_mount(poses, [0, 0, .11], [0, .10625, .02847], layers, DEFAULT_SPEC)
m_mallet, g_mallet = pinion_mount(swing([0, .8, 1.0]), [0, 0, .11], [0, .10625, .02847], layers, DEFAULT_SPEC)
m_upward, g_upward = pinion_mount(swing([0, 1.0, .3]), [0, 0, .11], [0, .10625, .02847], layers, DEFAULT_SPEC)
check(m_down != 'down' and m_mallet not in ('front', 'up') and m_upward != 'up' and min(g_down, g_mallet, g_upward) > .05,
      f'pinion_mount: hanging link -> {m_down} ({g_down*1000:.0f} mm), mallet link -> {m_mallet} ({g_mallet*1000:.0f} mm), upward link -> {m_upward} ({g_upward*1000:.0f} mm)')
m_front, g_front = pinion_mount(swing([0, -.3, -1.0]), [0, 0, .11], [0, .10625, .02847], layers, DEFAULT_SPEC)
check(m_front != 'back' and g_front > .05, f'pinion_mount: a link swinging back -> {m_front} ({g_front*1000:.0f} mm)')
check(pinion_mount(swing([0, -.3, -1.0]), [0, 0, .11], [0, .10625, .02847], layers, DEFAULT_SPEC, ['back'])[1] < 0,
      'pinion_mount: forcing the mount the link swings through reports the hit')

# A servo arm's carriage (drive='screw', docs/plans/leadscrew-servo-drive.md)
# carries no pinion: the axle boss stops at the disc plane and a bracket arm
# runs out along rack_direction to a flanged, bolted BRONZE nut on the
# leadscrew's axis — all inside the nut / nut_arm capsules drive_capsules
# reserves, with no pinion capsule and nothing beyond the plane.
from formlab.clearance import SCREW, drive_capsules, drive_kind
check(drive_kind(dict(kind='mallet')) == 'rack' and drive_kind(dict(kind='hammer')) == 'rack' and drive_kind(dict(kind='pick')) == 'screw' and drive_kind(dict(kind='rake')) == 'screw',
      'drive_kind: mallet and hammer arms keep the rack, pick and rake arms ride a leadscrew')
for mount in MOUNTS:
    ny, nz = MOUNTS[mount]; n = np.array([0, ny, nz], float); u = rack_direction(mount)
    arm = parallelogram_arm(1.0, 1.0, [0, 0, .11], [0, .10625, .02847], mount=mount, drive='screw'); V = [p.vertices for p in arm['carriage']['pieces']]
    check_pieces(arm['carriage']['pieces'])
    centre = pinion_centre(mount); axis = centre+u*SCREW['s_axis']; depth = lambda v: (v-centre)@n
    nut = [p for p in arm['carriage']['pieces'] if getattr(p, 'material', None) == 'bronze']
    rad = lambda v: np.linalg.norm((v-axis)-np.outer((v-axis)@[1, 0, 0], [1, 0, 0]), axis=1)
    caps = drive_capsules(np.zeros(3), mount, 'screw')
    def housed(v):                    # every vertex inside one of the nut capsules
        ok = np.zeros(len(v), bool)
        for k in ('nut', 'nut_arm', 'nut_flange'):
            a, b, r = caps[k]; d = b-a; t = np.clip((v-a)@d/(d@d), 0, 1); ok |= np.linalg.norm(v-a-np.outer(t, d), axis=1) <= r+1e-6
        return ok.all()
    # the nut's axis lies in the disc plane, so the nut, flange and bolts straddle it by no more than the flange's half-width
    beyond = max(depth(v).max() for v in V)
    drive_pieces = [v for v in V if abs(depth(v)).max() < .06 and (v@u).max() > centre@u+.03]   # the arm, flange, bolts and nut: about the plane and out along u (not the axle's stub)
    check(len(nut) == 1 and abs(nut[0].vertices.mean(0)-axis).max() < 1e-6 and abs(rad(nut[0].vertices).max()-SCREW['nut_r']) < 1e-6
          and abs(np.ptp(nut[0].vertices[:, 0])-SCREW['nut_len']) < 1e-6 and beyond <= SCREW['flange']+1e-6 and len(drive_pieces) == 7 and all(housed(v) for v in drive_pieces)
          and not any(k.startswith('pinion') for k in caps) and {'nut', 'nut_arm', 'nut_flange', 'carriage_axle'} <= set(caps),
          f'{mount}: a screw carriage — one bronze nut on the screw axis {SCREW["s_axis"]*1000:.0f} mm out, its arm, flange and bolts inside the nut capsules, nothing past the plane but them, no pinion')

# the built pinions carry the boss on their outer face (build_clockwork.gear,
# cast with the disc so it turns): the gear mesh reaches boss_h past the disc
# on the mount's side — the side away from the carriage — and no further
# than the disc on the other, for the tilted (front/back) and flat (up/down)
# builds alike
import json
sys.path.insert(0, str(Path(__file__).resolve().parent)); from test_flywheel import glb_vertices
assets = Path(__file__).resolve().parents[1]/'harness/assets'
for asset in ('clockwork', 'clockwork_expanded'):
    if not (assets/f'{asset}.glb').exists(): continue
    layout = json.loads((assets/f'{asset}.json').read_text())
    for aid, cfg in layout['arms'].items():
        # a servo arm is built without a pinion; its leadscrew shaft is its own form
        if drive_kind(cfg) == 'screw':
            try: V = glb_vertices(assets/f'{asset}.glb', f'form_{aid}_screw')
            except Exception: V = None
            try: gear = glb_vertices(assets/f'{asset}.glb', aid+'__gear')
            except Exception: gear = None
            sc = cfg.get('screw', {})
            check(V is not None and gear is None and cfg.get('drive') == 'screw' and sc and abs(V[:, 1].mean()-sc['y']) < .002 and abs(V[:, 2].mean()-sc['z']) < .002
                  and V[:, 0].min() < sc['x_thread'][0] and V[:, 0].max() > sc['x_thread'][1] and np.ptp(V[:, 1]) < 2*(SCREW['shaft_r']+2*SCREW['thread_r'])+.001,
                  f'{asset} {aid}: built with a leadscrew (form_{aid}_screw on its recorded axis, threaded over {sc.get("x_thread")}) and no pinion')
            continue
        # the exported node carries its home pose, so measure the mesh about
        # itself: its extent along n is disc + boss; the slab at the +n end is
        # boss-sized (a boss on the wrong side would put the disc's rim there)
        # and the slab at the -n end is the full disc
        ny, nz = MOUNTS[cfg.get('pinion', 'back')]; n = np.array([0, ny, nz], float)
        V = glb_vertices(assets/f'{asset}.glb', aid+'__gear'); d = V@n
        top = V[d > d.max()-PINION['boss_h']+.002]; ctr = top.mean(0)
        rad = lambda W: np.linalg.norm((W-ctr)-np.outer((W-ctr)@n, n), axis=1)
        check(abs(d.max()-d.min()-PINION['thickness']-PINION['boss_h']) < .003 and rad(top).max() < PINION['boss_r']+.003
              and rad(V[d < d.min()+.005]).max() > PINION['r_tip']-.01,
              f'{asset} {aid}: the built pinion carries its hub boss {PINION["boss_h"]*1000:.0f} mm proud of its outer ({cfg.get("pinion", "back")}) face')

if failures: raise SystemExit('LINKAGE TOOLS FAIL: '+'; '.join(failures))
print('LINKAGE TOOLS: PASS')

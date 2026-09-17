"""Ruler for the arm tools: plectrum, ferrule, swan-neck shank, socket, mallet.
python3 tools/test_linkage_tools.py
"""
import sys
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from formlab.linkage import pick_tool, mallet_tool, tool_mount, shank_path, check_pieces, SOCKET_DEPTH
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

# the clearance ruler knows the new tool shape
poses = dict(t=np.zeros(1), root=np.array([[0, 2.5, -1.0]]), elbow=np.array([[0, 2.2, -.3]]),
             wrist=np.array([[0, 1.20, -.1]]), tip=np.array([[0, 1.0, 0]]))
caps, adjacent = arm_capsules(poses, [0, -.11, 0], [0, .10625, .02847], default_layers(DEFAULT_SPEC), DEFAULT_SPEC)
check('shank' in caps and 'tool' in caps, 'capsules: tool (tip to apex) and shank (apex to socket)')
check(np.allclose(caps['tool'][1], caps['shank'][0]), 'tool and shank capsules meet at the neck apex')
check(np.allclose(caps['shank'][1], [0, 1.20-.03, -.1]), 'shank capsule ends inside the wrist boss')
check(frozenset(('lower', 'tool')) not in adjacent, 'the lower bar is measured against the tool, not excused')

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
    cheek = [v for v in V if abs(v[:, 0].max()-(CARRIAGE['cheek_x']+CARRIAGE['cheek_t']/2)) < 1e-6]
    check(len(cheek) == 1 and cheek[0][:, 0].max() < -(layers['gap']/2+DEFAULT_SPEC['ear_t']) and cheek[0][:, 0].min() > -layers['span']/2,
          f'{mount}: the cheek plate clears the fork ears and stays inside the pin span')
    centre = pinion_centre(mount); hub = centre-np.array([0, ny, nz])*PINION['thickness']/2
    axle = [v for v in V if abs(v[:, 0].max()-CARRIAGE['axle_r']) < 1e-6 and (np.ptp(v[:, 2]) > .1 or np.ptp(v[:, 1]) > .035)]
    check(len(axle) == 1 and np.linalg.norm(axle[0].mean(0)[[0, 2]]-hub[[0, 2]])*(1-abs(nz)) < 1e-6
          and (axle[0][:, 1].max() >= hub[1] if ny > 0 else axle[0][:, 1].min() <= hub[1] if ny < 0 else True)
          and (axle[0][:, 2].max() >= hub[2] if nz > 0 else axle[0][:, 2].min() <= hub[2] if nz < 0 else True),
          f'{mount}: the axle reaches into the pinion hub')
    if nz == 0:
        bridge = [v for v in V if abs(abs(v[:, 0]).max()-CARRIAGE['bridge_x']) < 1e-6 and np.ptp(v[:, 2]) > .1]
        b0, b1 = CARRIAGE['bridge_y']
        check(len(bridge) == 1 and abs(ny*bridge[0][:, 1].mean()-(b0+b1)/2) < 2e-3 and bridge[0][:, 2].min() < CARRIAGE['axle_z']-.02
              and (bridge[0][:, 1].max() if ny > 0 else -bridge[0][:, 1].min()) < PINION['up']-PINION['thickness']/2-.005,
              f'{mount}: the bridge reaches back past the axle and stays under the disc')
        check(abs(CARRIAGE['axle_z'])-CARRIAGE['axle_r'] >= CARRIAGE['bush_r']+.004, f'{mount}: the vertical axle misses the bushing')
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
check(all(k in caps for k in ('carriage_bush-', 'carriage_bush+', 'carriage_cheek', 'carriage_axle', 'carriage_bridge', 'pinion2')),
      'capsules: bushings, cheek, axle, bridge and pinion chords')
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

if failures: raise SystemExit('LINKAGE TOOLS FAIL: '+'; '.join(failures))
print('LINKAGE TOOLS: PASS')

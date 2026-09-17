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

if failures: raise SystemExit('LINKAGE TOOLS FAIL: '+'; '.join(failures))
print('LINKAGE TOOLS: PASS')

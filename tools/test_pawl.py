"""Ruler for the roller detent pawl on the mallet arms' pinions (formlab.pawl).

    python3 tools/test_pawl.py                       # both built assets
    python3 tools/test_pawl.py LAYOUT.json SCORE.json

Checks, per built asset:
  - every stepped arm with a front/back pinion records a pawl, placed where
    formlab.pawl puts it; no other arm does;
  - the kinematics: the roller touches the teeth at every rail position
    (never clips them), dips once a tooth by a visible amount, and moves
    without a jump; the rendered rig's angle (harness/dev/dump_motion.gd,
    ClockworkMotion.pawl_angle) matches the numpy one;
  - the pawl's body — lever, yoke, tongues — keeps clear of the teeth at every
    rail position, and its pieces and the bracket's are closed meshes;
  - space: over the score's motion the pawl and its bracket clear the arm's
    own links and tool, every sibling arm, every other rail's bars and rack,
    its own rack, its own guide bars, and the forms and furniture.
"""
import json, shutil, subprocess, sys
from pathlib import Path
import numpy as np
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT))
from formlab import pawl as W
from formlab import gantry as G
from formlab import clearance as C
from formlab.rig import Rig
from formlab.linkage import check_pieces
from formlab.layout_search import scene_boxes

failures = []
def check(ok, msg):
    print(('  PASS ' if ok else '  FAIL ')+msg)
    if not ok: failures.append(msg)

def parity(layout_path, score_path):
    godot = shutil.which('godot')
    if godot is None: print('  SKIP godot not on PATH: rendered pawl angle unmeasured'); return
    out = subprocess.run([godot, '--headless', '--path', str(ROOT/'harness'), '-s', 'dev/dump_motion.gd', '--',
                          f'--score={score_path}', f'--asset={layout_path.stem}'], capture_output=True, text=True, timeout=600).stdout
    rows = np.array([[float(a), float(b)] for line in out.splitlines() if line.startswith('PAWL ') for _, a, b in [line.split()]])
    worst = abs(W.angle(rows[:, 0])-rows[:, 1]).max() if len(rows) else np.inf
    check(len(rows) > 1000 and worst < 1e-9, f'rendered pawl angle and numpy mirror agree: {len(rows)} samples, worst {worst:.1e} rad')

def box_gap(P, Q, r, lo, hi, samples=33):
    """Least distance from capsule PQ (per pose) to an axis-aligned box, sampled along the axis."""
    best = np.full(len(P), np.inf)
    for t in np.linspace(0, 1, samples):
        p = P+(Q-P)*t; best = np.minimum(best, np.linalg.norm(p-np.clip(p, lo, hi), axis=1))
    return best-r

def kinematics():
    pitch = 2*np.pi*C.PINION['r_pitch']/C.PINION['teeth']
    xs = np.arange(-3*pitch, 3*pitch, .0001); al = W.angle(xs); r = W.nose_radius(xs)
    P = np.array([W.PAWL['lever'], -(C.PINION['r_tip']+W.PAWL['drop']+W.PAWL['finger'])]); n = W.nose_at(al)
    touch = W.tooth_distance(P[0]+n[:, 0], P[1]+n[:, 1], xs)-W.PAWL['nose_r']
    check(abs(touch).max() < 1e-9, f'the roller touches the teeth at every rail position (worst {abs(touch).max():.1e} m)')
    # a local minimum below the half-way radius (riding a tip's flat has its own shallow one)
    dips = int(np.sum((r[1:-1] < r[:-2]) & (r[1:-1] <= r[2:]) & (r[1:-1] < (r.max()+r.min())/2)))
    check(dips == 6 and r.max()-r.min() > .008, f'one dip a tooth ({dips} over 6 teeth), {1000*(r.max()-r.min()):.1f} mm deep')
    check(np.degrees(np.abs(np.diff(al)).max()) < .5, f'the pawl moves without a jump (worst {np.degrees(np.abs(np.diff(al)).max()):.2f} deg per 0.1 mm)')
    # the body vs the teeth, at every rail position: lever, yoke, tongues
    caps = W.capsules(np.c_[xs, np.zeros_like(xs), np.zeros_like(xs)], 'back'); worst = (1e9, '')
    centre = C.pinion_centre('back')
    for name in ('pawl_lever', 'pawl_yoke', 'pawl_tongue-', 'pawl_tongue+'):
        A, B, rr = caps[name]
        for t in np.linspace(0, 1, 41):
            q = A+(B-A)*t-centre-np.c_[xs, np.zeros_like(xs), np.zeros_like(xs)]; g = W.tooth_distance(q[:, 0], q[:, 1], xs)-rr; k = int(np.argmin(g))
            if g[k] < worst[0]: worst = (float(g[k]), f'{name} at x={xs[k]:.4f}')
    check(worst[0] > .003, f'the pawl\'s body keeps off the teeth ({worst[0]*1000:.1f} mm, {worst[1]})')
    lever, mats = W.lever_pieces('back'); check_pieces(lever); check_pieces(W.bracket_pieces('back'))
    check(len(mats) == len(lever), f'{len(lever)} pawl pieces and {len(W.bracket_pieces("back"))} bracket pieces are closed meshes')
    for mount in ('up', 'down'):
        try: W.pivot(mount); check(False, f'a {mount} mount refused a pawl')
        except ValueError: pass

def run(layout_path, score_path):
    print(f'== {layout_path.name} / {score_path.name}')
    layout = json.loads(layout_path.read_text()); score = json.loads(score_path.read_text())
    rig = Rig(score, layout); times = rig.sample_times()
    poses = {aid: rig.poses(aid, times) for aid in layout['arms']}
    arm_caps = G._caps(layout, poses, 1)
    with_pawl = [aid for aid, cfg in layout['arms'].items() if cfg.get('pawl')]
    want = [aid for aid, cfg in layout['arms'].items() if rig.stepped(aid) and C.MOUNTS[cfg['pinion']][1]]
    check(sorted(with_pawl) == sorted(want) and with_pawl, f'pawls on the stepped arms with a free rim: {", ".join(with_pawl)}')
    boxes = scene_boxes(layout)
    for aid in with_pawl:
        cfg = layout['arms'][aid]; mount = cfg['pinion']; rec = cfg['pawl']
        check(np.allclose(rec['pivot'], W.pivot(mount), atol=1e-6) and np.allclose(rec['nose'], W.nose_rest(), atol=1e-6)
              and rec['nose_r'] == W.PAWL['nose_r'] and rec['mount'] == mount, f'{aid}: the manifest records the pawl where formlab.pawl puts it')
        caps = W.capsules(poses[aid]['root'], mount)
        # its own links and tool (the carriage and pinion are what it is mounted to)
        own = (1e9, '')
        for pname, (P, Q, r) in caps.items():
            for lname, (A, B, ra) in arm_caps[aid].items():
                if lname.startswith(('carriage', 'pinion')): continue
                g = C.segment_distance(P, Q, A, B)-r-ra; k = int(np.argmin(g))
                if g[k] < own[0]: own = (float(g[k]), f'{pname} vs {lname} at t={times[k]:.2f} s')
        check(own[0] >= G.MARGIN, f'{aid}: pawl clears the arm\'s own links and tool by {own[0]*1000:.0f} mm ({own[1]})')
        # sibling arms and every other rail
        sib = (1e9, ''); rails = (1e9, '')
        for other, cfg2 in layout['arms'].items():
            if other == aid: continue
            for pname, (P, Q, r) in caps.items():
                for lname, (A, B, ra) in arm_caps[other].items():
                    g = C.segment_distance(P, Q, A, B)-r-ra; k = int(np.argmin(g))
                    if g[k] < sib[0]: sib = (float(g[k]), f'{pname} vs {other} {lname} at t={times[k]:.2f} s')
                for A, B, ra in G.rail_bars(cfg2)+G.rail_racks(cfg2):
                    g = C.segment_distance(P, Q, A[None], B[None])-r-ra; k = int(np.argmin(g))
                    if g[k] < rails[0]: rails = (float(g[k]), f'{pname} vs rail {other} at t={times[k]:.2f} s')
        check(sib[0] >= G.MARGIN, f'{aid}: pawl clears every other arm by {sib[0]*1000:.0f} mm ({sib[1]})')
        check(rails[0] >= G.MARGIN, f'{aid}: pawl clears every other rail\'s bars and rack by {rails[0]*1000:.0f} mm ({rails[1]})')
        # its own rack (above the disc) and its own guide bars (the bracket rides beside them)
        (A, B, ra), = G.rail_racks(cfg); rack = min(float((C.segment_distance(P, Q, A[None], B[None])-r-ra).min()) for P, Q, r in caps.values())
        bars = 1e9
        for A, B, ra in G.rail_bars(cfg):
            for pname, (P, Q, r) in caps.items():
                bars = min(bars, float((C.segment_distance(P, Q, A[None], B[None])-r-ra).min()))
        check(rack >= G.MARGIN and bars >= .004, f'{aid}: pawl clears its own rack by {rack*1000:.0f} mm and its guide bars by {bars*1000:.0f} mm')
        # forms, furniture and the stage
        form = (1e9, '')
        for pname, (P, Q, r) in caps.items():
            for lo, hi in boxes:
                g = box_gap(P, Q, r, lo, hi); k = int(np.argmin(g))
                if g[k] < form[0]: form = (float(g[k]), f'{pname} at t={times[k]:.2f} s')
        check(form[0] >= G.MARGIN, f'{aid}: pawl clears the forms, furniture and stage by {form[0]*1000:.0f} mm ({form[1]})')
    parity(layout_path, score_path)

if __name__ == '__main__':
    kinematics()
    if len(sys.argv) > 2: pairs = [(Path(sys.argv[1]), Path(sys.argv[2]))]
    else: pairs = [(ROOT/'harness/assets/clockwork.json', ROOT/'render/chamber/score.json'),
                   (ROOT/'harness/assets/clockwork_expanded.json', ROOT/'render/clockwork/score.json')]
    for lp, sp in pairs: run(lp, sp)
    print('PAWL: '+('FAIL' if failures else 'PASS'))
    sys.exit(1 if failures else 0)

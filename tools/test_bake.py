"""Ruler for the motion bake (formlab/bake.py, `loam-motion/2`).

    python3 tools/test_bake.py                       # both built assets
    python3 tools/test_bake.py LAYOUT.json SCORE.json

The harness plays the performance back from the bake and owns no motion of its
own, so this is where "what Godot shows is what formlab.rig computed" is held:
  - the bake on disk is fresh: its fingerprints are the score's and the
    manifest's (a stale one fails with the command that remakes it);
  - every row is the rig's pose at that row's time, to float32;
  - every contact is a row, so the baked tip (a hinged hammer's felt face)
    lands on it exactly; no arm is ever unreachable;
  - between rows, linear interpolation stays within INTERP_M of the rig (the
    tool path, the links' pins) and within INTERP_RAD of the head's flip;
  - the assembly's shudders, the clicks and the pawl's one-tooth table are
    the rig's and formlab.pawl's;
  - a stepped arm's `.ride` channel is Rig.pawl_ride at the rows, in [0, 1] and
    0 at every contact (the hammer's all 0, no servo arm has one); the clicks'
    parallel click_pawl / click_step are a mallet stroke's click knots (the
    hammer's all drop and stepped); every blow is the rig's recoil bus (a
    mallet's with its stroke's v_in and e, gate_end the next stroke's apex);
    pawl.ride_angle is the table's least angle (the nose on a tip);
  - the /2 format (T1-T13 of docs/goals/the-players.md M3): a /1 bake is
    refused by both readers; /1's columns are a byte-identical prefix and the
    q columns follow, equal to the rig's joint angles; the joints table
    compiles, has every arm kind's rows and binds only known nodes, with the
    harness's laws (formlab.kinematics.HARNESS_LAWS); FK of the table lands on
    the pins, the aimed links keep their lengths and the parallelogram pairs
    close; every value is its law on the rows; the declared structure round
    trips; the header is strict JSON; future joints (a thumb, a finger, a
    pendulum: unpinned rows with no bodies) evaluate in both readers with no
    reader change, and an unknown op and a non-unit axis are refused by name;
    each joint's range is its values' and its spin flag the wheels';
  - the harness's reader (harness/motion_bake.gd, via dev/dump_bake.gd) reads
    what formlab.bake.Bake reads, off the grid (the poses, the shudders, the
    pawl, the clicks, and every joint's frame, pose mode and FK, against
    formlab.kinematics.evaluate, Godot's arithmetic mirrored), and refuses a stale
    bake and a /1 one.
Godot parts are skipped when godot is not on the PATH.
"""
import json, math, re, shutil, subprocess, sys, tempfile, time
from contextlib import contextmanager
from pathlib import Path
import numpy as np
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT))
from formlab import bake as B
from formlab import pawl as W
from formlab import stroke as ST
from formlab import kinematics as J
from formlab import segments as SEG
from formlab import rig as RIG
from formlab.clearance import PINION
from formlab.rig import Rig

INTERP_M = .005      # 5 mm: the worst an interpolated pin strays from the rig mid-slew
INTERP_RAD = .01
FLOAT32_M = 2e-6     # a stored position against the rig's float64 one
# the joints table (loam-motion/2): the harness's frames against formlab.kinematics.evaluate (Godot's arithmetic
# mirrored where it moves a value: float32 pins, component sources, origins and Basis angles); Godot's own
# per-op float32 rounding is a few x 2.4e-7 at 4 m, more down an FK chain
Q_RAD = 1e-9         # a joint's value (a double in both readers)
POSE_M = 2e-6        # a pose-mode frame: P (m) and B
FK_M = 5e-6          # an FK-mode frame: P (m) and B
Q_COL_RAD = 1e-6     # a stored q column against the rig's float64 angle (float32: the ulp at 2 pi is 4.8e-7)
LAW = 1e-12          # a value against its law, on the same float32 inputs
LOADMS_WARN = 250.0  # the harness's load time: reported, warned above this, not gated
SPIN = ('pinion', 'roller', 'screw', 'flywheel', 'belt_pulley')
CHAMBER_LABELS = ('Chamber flywheel', 'Chamber hub', 'Chamber drive pulley', 'Chamber belt pulley')

failures = []
def check(ok, msg):
    print(('  PASS ' if ok else '  FAIL ')+msg)
    if not ok: failures.append(msg)

def godot(score_path, asset, extra=[]):
    exe = shutil.which('godot')
    if exe is None: return None
    return subprocess.run([exe, '--headless', '--path', str(ROOT/'harness'), '-s', 'dev/dump_bake.gd', '--',
                           f'--score={score_path}', f'--asset={asset}', *extra], capture_output=True, text=True,
                          timeout=900).stdout

def parity(bake, score_path, asset):
    out = godot(score_path, asset)
    if out is None: print('  SKIP godot not on PATH: the harness reader unmeasured'); return
    pose = shud = pawl = ride = posed = lean = 0.0; n = ns = npw = nr = nl = 0; clicks = {}; marks = {}
    for line in out.splitlines():
        f = line.split()
        if not f: continue
        if f[0] == 'POSE':
            aid, t = f[1], float(f[2]); v = np.array(f[3:], float); n += 1
            row = bake.row(t)
            mine = np.concatenate([bake.get(f'{aid}.{k}', t, row) for k in ('root', 'elbow', 'wrist', 'tip')]
                                  + [bake.felt(aid, t), [bake.get(f'{aid}.head', t, row)]])
            pose = max(pose, float(np.abs(mine-v).max()))
        elif f[0] == 'SHUD':
            aid, t = f[1], float(f[2]); ns += 1; arm = bake.header['arms'][aid]
            stand = bake.get(f'{arm["mech"]}.stand', t) if f'{arm["mech"]}.stand' in bake.index else 0.0
            mine = np.array([stand, bake.get(f'{aid}.sag', t), bake.get(f'{aid}.sway', t)])
            shud = max(shud, float(np.abs(mine-np.array(f[3:], float)).max()))
        elif f[0] == 'RIDE':
            aid, t = f[1], float(f[2]); nr += 1; row = bake.row(t)
            ride = max(ride, abs(bake.ride(aid, t, row)-float(f[3])))
            posed = max(posed, abs(bake.pawl(aid, t)-float(f[4])))
        elif f[0] == 'PAWL':
            npw += 1; pawl = max(pawl, abs(bake.pawl_angle(float(f[1]))-float(f[2])))
        elif f[0] == 'PAWLR':
            nl += 1; lean = max(lean, abs(bake.pawl_angle(float(f[1]), float(f[2]))-float(f[3])))
        elif f[0] == 'CLICK':
            clicks.setdefault(f[1], []).append(float(f[2]))
            marks.setdefault(f[1], []).append((int(f[4]), int(f[5])) if len(f) >= 6 else None)
    check(n > 1000 and pose < 1e-6, f'the harness reads the poses the reference reader does: {n} off-grid samples, worst {pose:.1e}')
    check(ns > 1000 and shud < 1e-9, f'...and the shudders: {ns} samples, worst {shud:.1e}')
    check(npw > 1000 and pawl < 1e-6, f'...and the pawl table: {npw} rail positions, worst {pawl:.1e} rad')
    rides = [a for a in bake.header['arms'] if f'{a}.ride' in bake.index]
    check(nr > 1000*len(rides) and ride < 1e-6 and posed < 1e-6,
          f'...and the pawl\'s ride and its posed angle (MotionBake.ride / .pawl): {nr} samples over {len(rides)} arms, worst {ride:.1e} / {posed:.1e} rad')
    check(nl > 1000 and lean < 1e-6, f'...and the table leaned toward pawl.ride_angle by a ride: {nl} samples, worst {lean:.1e} rad')
    want = {aid: [c[0] for c in a['clicks']] for aid, a in bake.header['arms'].items() if a['clicks']}
    same = want.keys() == clicks.keys() and all(np.allclose(want[a], clicks[a], atol=1e-8) for a in want)
    check(same, f'...and the clicks: {sum(len(v) for v in clicks.values())} over {len(clicks)} arms')
    wm = {aid: [(c['pawl'], c['step']) for c in bake.clicks(aid)] for aid in want}
    check(wm.keys() == marks.keys() and all(wm[a] == marks[a] for a in wm),
          f'...and each click\'s pawl (ride / drop) and step (stepped / freewheel)')
    v2_parity(bake, out)

def refuses_stale(score_path, asset):
    """A copy of the export whose score.json has changed by one byte: the
    harness must refuse the bake rather than play it."""
    if shutil.which('godot') is None: return
    json_path, bin_path = B.paths(score_path, asset)
    with tempfile.TemporaryDirectory() as d:
        d = Path(d)
        for p in Path(score_path).parent.iterdir():
            if p.is_dir(): (d/p.name).symlink_to(p)
            elif p.name != 'score.json': (d/p.name).symlink_to(p)
        (d/'score.json').write_text(Path(score_path).read_text()+'\n')
        out = godot(d/'score.json', asset)
    check('stale motion bake' in out and 'POSE' not in out, 'the harness refuses a bake made from another score')

# ------------------------------------------------------------- loam-motion/2
@contextmanager
def temp_bake(score_path, asset, edit):
    """The export's directory as symlinks (the refuses_stale pattern), with a
    real copy of the score (so a resolved path stays here) and the bake's
    header replaced by edit(header). Yields (score, header) paths."""
    json_path, _ = B.paths(score_path, asset)
    with tempfile.TemporaryDirectory() as d:
        d = Path(d); sp = Path(score_path)
        for p in sp.parent.iterdir():
            if p.name in (json_path.name, sp.name): continue
            (d/p.name).symlink_to(p)
        (d/sp.name).write_bytes(sp.read_bytes())
        h = json.loads(json_path.read_text()); h = edit(h) or h
        (d/json_path.name).write_text(json.dumps(h, separators=(',', ':')))
        yield d/sp.name, d/json_path.name

def frame_vec(fr):
    """A joint's frame as the dump prints it: q, P, then B's columns x, y, z."""
    P, Bm, q, _ = fr
    return np.concatenate([[q], P, Bm[:, 0], Bm[:, 1], Bm[:, 2]])

def joint_lines(out, kind):
    rows = []
    for line in out.splitlines():
        f = line.split()
        if f and f[0] == kind: rows.append((f[1], float(f[2]), np.array(f[3:], float)))
    return rows

def compare_joints(bake, rows, fk, snap, ids=None):
    """(n, worst q, worst P, worst B, where) of the dump's JOINT / JOINTFK
    lines against Bake.joint_frames at the same t (`snap` recovers the exact
    double the harness evaluated from its printed %.9f)."""
    cache = {}; n = 0; wq = wp = wb = 0.0; where = ''
    for jid, tp, v in rows:
        if ids is not None and jid not in ids: continue
        t = snap(tp)
        if t not in cache: cache[t] = bake.joint_frames(t, fk)
        m = frame_vec(cache[t][jid]); n += 1
        eq, ep, eb = abs(m[0]-v[0]), float(np.abs(m[1:4]-v[1:4]).max()), float(np.abs(m[4:]-v[4:]).max())
        if ep > wp or eb > wb or eq > wq: where = f'{jid} at {t:.4f} s'
        wq, wp, wb = max(wq, eq), max(wp, ep), max(wb, eb)
    return n, wq, wp, wb, where

def part_names():
    """performance.gd's PART_NAMES: every moving part of one arm, as named in the GLB."""
    m = re.search(r'const PART_NAMES := \[([^\]]*)\]', (ROOT/'harness'/'performance.gd').read_text())
    return [x.strip().strip('"') for x in m.group(1).split(',')] if m else []

def t1_refuses_v1(score_path, asset):
    """T1: a header saying loam-motion/1 is refused by both readers, with the
    command that remakes it."""
    def v1(h): h['format'] = 'loam-motion/1'
    with temp_bake(score_path, asset, v1) as (sp, jp):
        try: B.Bake(jp); msg = ''
        except ValueError as e: msg = str(e)
        check('is a loam-motion/1 bake; formlab.bake reads loam-motion/2' in msg and f'tools/bake_motion.py --asset={asset}' in msg,
              f'T1 formlab.bake refuses a loam-motion/1 bake by name, with the command that remakes it'
              + ('' if msg else ' (it read it)'))
        out = godot(sp, asset)
        if out is None: print('  SKIP godot not on PATH: the harness\'s /1 refusal unmeasured'); return
        check('ERROR' in out and 'loam-motion/1 bake; this harness reads loam-motion/2' in out and 'POSE' not in out,
              'T1 ...and so does the harness (dump_bake prints the refusal and no pose)')

def t2_prefix(bake, rig):
    """T2: /1's columns, then the q columns."""
    h = bake.header; ch = h['channels']; want = []; off = 0
    for aid in rig.plans:
        for name, w in B.ARM_CHANNELS+(B.STEPPED_CHANNELS if rig.stepped(aid) else []):
            want.append((f'{aid}.{name}', off, w)); off += w
    for m in rig.score['instrument']['mechanisms']:
        want.append((f'{m["id"]}.stand', off, 1)); off += 1
    w1 = off; n1 = len(want)
    check([(c['name'], c['offset'], c['width']) for c in ch[:n1]] == want and all('joint' not in c for c in ch[:n1]),
          f'T2 /1\'s {n1} channels are the prefix: columns [0, {w1}) by name, offset and width, in /1\'s order')
    q = []
    for aid in rig.plans:
        for key in (['lean'] if rig.mallet(aid) else [])+['shoulder', 'elbow']:
            q.append(dict(name=f'{aid}.q.{key}', offset=off, width=1, joint=f'{aid}/{key}')); off += 1
    nm = sum(bool(rig.mallet(a)) for a in rig.plans)
    check(ch[n1:] == q and h['width'] == w1+2*len(rig.plans)+nm == off == bake.frames.shape[1],
          f'T2 ...then the q columns, contiguous from {w1}, per arm in rig.plans order, each naming its joint, q.lean on '
          f'the {nm} mallets only: width {h["width"]} = {w1} + 2 x {len(rig.plans)} + {nm}')

def t3_q(bake, rig, poses):
    """T3: the q columns are the rig's joint angles (float64) at the sampled
    rows: ruler 16's joint_series, a mallet's read in its leaned plane."""
    worst = 0.0; where = ''
    for aid in rig.plans:
        idx, root, elbow, wrist = poses[aid]
        if rig.mallet(aid):
            d = wrist-root; psi = np.arctan(d[:, 0]/d[:, 2]); c, s = np.cos(psi), np.sin(psi)
            Ry = np.zeros((len(psi), 3, 3)); Ry[:, 0, 0] = c; Ry[:, 0, 2] = s; Ry[:, 1, 1] = 1.0; Ry[:, 2, 0] = -s; Ry[:, 2, 2] = c
            u = np.einsum('nji,nj->ni', Ry, elbow-root); f = np.einsum('nji,nj->ni', Ry, wrist-elbow)   # Ry(psi)^T v
            sh = np.unwrap(np.arctan2(u[:, 1], u[:, 2]))
            want = {'q.lean': psi, 'q.shoulder': sh, 'q.elbow': np.unwrap(np.arctan2(f[:, 1], f[:, 2]))-sh}
        else:
            js = RIG.joint_series(root, elbow, wrist); want = {'q.shoulder': js['shoulder'], 'q.elbow': js['rel']}
        for k, v in want.items():
            e = float(np.abs(bake.frames[idx, bake.index[f'{aid}.{k}']['offset']].astype(float)-v).max())
            if e > worst: worst = e; where = f'{aid}.{k}'
    check(worst <= Q_COL_RAD, f'T3 the q columns are the rig\'s joint angles at every 11th row (worst {worst:.1e} rad, {where})')

def expected_rows(rig, aid, hdr):
    """§3's rows for one arm: name -> (parent name, type, axis, pin)."""
    cfg = rig.geometry['arms'][aid]; X, Y, Z = [1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]
    base = 'lean' if rig.mallet(aid) else 'carriage'
    rows = dict(carriage_y=(None, 'prismatic', Y, None), carriage=('carriage_y', 'prismatic', X, '.root'))
    if rig.mallet(aid): rows['lean'] = ('carriage', 'revolute', Y, None)
    rows.update(shoulder=(base, 'revolute', X, None), shoulder_pair=(base, 'revolute', X, None),
                elbowhead=('shoulder', 'revolute', X, '.elbow'), elbow=('elbowhead', 'revolute', X, None),
                elbow_pair=('elbowhead', 'revolute', X, None), wristhead=('elbow', 'revolute', X, '.wrist'),
                tool=('wristhead', 'fixed', None, '.tip'))
    if 'head' in cfg: rows['head'] = ('tool', 'revolute', X, None)
    if cfg.get('drive', 'rack') == 'rack':
        rows['pinion'] = ('carriage', 'revolute', Y if cfg.get('pinion', 'back') in ('up', 'down') else Z, None)
        if 'pawl' in cfg: rows.update(pawl=('carriage', 'revolute', Z, None), roller=('pawl', 'revolute', Z, None))
    else: rows['screw'] = (None, 'revolute', X, None)
    if hdr['stepped']: rows.update(rail=(None, 'prismatic', Y, None), sway=(None, 'revolute', X, None))
    return rows

def t4_table(bake, rig):
    """T4: the table compiles; every arm has its kind's rows; the bodies bind
    known node names; one stand a mechanism; the harness's laws."""
    h = bake.header; C = bake.kin; JT = {jt['id']: jt for jt in h['joints']}
    try: J.compile(h); err = ''
    except ValueError as e: err = str(e)
    check(not err and len(C.ids) == len(h['joints']) and len(C.bodies) == len(h['bodies']),
          f'T4 the joints table compiles: {len(h["joints"])} joints, {len(h["bodies"])} body rows' + (f' ({err})' if err else ''))
    bad = []
    for aid, hdr in h['arms'].items():
        rows = expected_rows(rig, aid, hdr)
        if hdr['joints'] != [f'{aid}/{n}' for n in rows]: bad.append(f'{aid} rows {hdr["joints"]}'); continue
        for n, (par, typ, ax, pin) in rows.items():
            jt = JT[f'{aid}/{n}']; pose = jt['pose'] or {}
            if (jt['parent'] != (None if par is None else f'{aid}/{par}') or jt['type'] != typ or jt['axis'] != ax
                    or pose.get('pin') != (None if pin is None else aid+pin)):
                bad.append(f'{aid}/{n}')
    check(not bad, f'T4 every arm has its kind\'s rows (§3: parent, type, axis, pin): {sum(len(a["joints"]) for a in h["arms"].values())} arm joints'
          + (f'; off: {bad[:6]}' if bad else ''))
    parts = set(part_names()) | {'gear', 'head', 'pawl', 'roller'}
    def known(node, owner):
        if node.startswith(f'{owner}__'): return node[len(owner)+2:] in parts
        return node.startswith('form_') or node in CHAMBER_LABELS or node == f'{owner} rail*'
    unknown = [b['node'] for b in h['bodies'] if not known(b['node'], JT[b['joint']]['owner'])]
    nodes = [b['node'] for b in h['bodies']]
    check(len(parts) > 4 and not unknown and len(set(nodes)) == len(nodes),
          f'T4 every body binds a known node name (PART_NAMES + gear/head/pawl/roller, form_*, the chamber\'s, "<aid> rail*"), '
          f'each once: {len(nodes)}' + (f'; unknown {unknown[:6]}' if unknown else ''))
    mids = [m for m in rig.geometry.get('mechanisms', {})]
    stands = [jt['owner'] for jt in h['joints'] if jt['name'] == 'stand']
    check(sorted(stands) == sorted(mids) and all(h['mechanisms'].get(m, {}).get('joints') == [f'{m}/stand'] for m in h['mechanisms']),
          f'T4 exactly one stand a manifest mechanism ({len(mids)})')
    L = J.HARNESS_LAWS; ok = L['pinion_r'] == PINION['r_pitch'] == .12
    for aid in h['arms']:
        if f'{aid}/pinion' in JT: ok &= JT[f'{aid}/pinion']['value']['ops'][-1] == ['div', L['pinion_r']]
    bpm = float(rig.score.get('bpm', L['flywheel'][0]))
    ok &= JT['chamber/flywheel']['value'] == dict(src=dict(time=True), ops=[['mul', '-TAU'], ['mul', bpm], ['div', L['flywheel'][1]]])
    fw = rig.geometry.get('flywheel')
    ratio = [] if fw is None else ([['mul', [float(fw['wraps'][0][1]), float(fw['wraps'][1][1])]]] if 'wraps' in fw else [['mul', [float(fw['cyls']['drive pulley'][2]), float(fw['cyls']['belt pulley'][2])]]])
    ok &= JT['chamber/belt_pulley']['value'] == dict(src=dict(joint='chamber/flywheel'), ops=ratio)
    check(ok, f'T4 the ops are the harness\'s laws (formlab.kinematics.HARNESS_LAWS): the pinion over r_pitch {L["pinion_r"]}, '
              f'the flywheel -TAU t bpm/{L["flywheel"][1]:g} at {bpm:g} bpm, the belt at the manifest\'s pulley ratio {ratio[0][1] if ratio else None}')

def t5_tree(bake, rig, F, T):
    """T5: FK of the table on the stored rows lands on the pins; the aimed
    links keep their lengths and the parallelogram pairs close (pose mode);
    the head's pin is the manifest's hinge; head_l is rig.HAMMER's."""
    C = bake.kin; fk = J.fk_rows(C, F, T); worst = 0.0; where = ''
    for jid, (P, _) in fk.items():
        o = C.pin[C.idx[jid]]; e = np.linalg.norm(P-F[:, o:o+3], axis=1); k = int(np.argmax(e))
        if e[k] > worst: worst = float(e[k]); where = f'{jid} at {T[k]:.3f} s'
    check(worst <= FLOAT32_M, f'T5 FK of the table from the stored q lands on every pin, every row: {len(fk)} pinned joints x '
                              f'{len(T)} rows, worst {worst:.2e} m ({where})')
    aims = [i for i, a in enumerate(C.aim) if a is not None]; pairs = [jt for jt in C.joints if 'closes' in (jt['extra'] or {})]
    ln = cl = 0.0; n = 0
    for k in range(0, len(T), 11):
        fr = bake.joint_frames(float(T[k])); n += 1
        for i in aims:
            ti = C.aim[i][0]; tgt = fr[C.ids[ti]][0]
            ln = max(ln, abs(float(np.linalg.norm(tgt-fr[C.ids[i]][0]))-float(C.joints[i]['extra']['length'])))
        for jt in pairs:
            c = jt['extra']['closes']; P, Bm, _, _ = fr[jt['id']]
            cl = max(cl, float(np.linalg.norm(P+Bm@np.array([0.0, c['length'], 0.0])-(fr[c['joint']][0]+np.asarray(c['offset'])))))
    check(ln <= FLOAT32_M and cl <= FLOAT32_M,
          f'T5 the aimed links keep their lengths ({len(aims)} links, worst {ln:.1e} m) and the pairs close ({len(pairs)}, worst '
          f'{cl:.1e} m) over {n} rows')
    hl = float(RIG.HAMMER['head_l']); ok = all(bake.head_l(a) == hl for a in bake.header['arms']); nh = 0
    for aid in bake.header['arms']:
        cfg = rig.geometry['arms'][aid]
        if 'head' not in cfg: continue
        nh += 1; jt = C.joints[C.idx[f'{aid}/head']]
        ok &= jt['origin'] == [float(v) for v in cfg['head']['hinge']] and float(cfg['head']['length']) == hl
    check(ok, f'T5 every arm\'s head_l is rig.HAMMER\'s {hl}; the {nh} hinged heads\' pins are the manifest\'s hinge and length')

def t6_laws(bake, rig, F, T):
    """T6: every joint's value is its law on the rows (the same float32
    inputs, double ops), and the harness's pawl reads the float32 table."""
    h = bake.header; C = bake.kin; Q = J.value_rows(C, F, T); Q64 = J.value_rows(C, F, T, godot=False)
    def col(name, k=0): return F[:, bake.index[name]['offset']+k]
    law = {}; wrapped = set(); pawls = []
    for aid, hdr in h['arms'].items():
        cfg = rig.geometry['arms'][aid]; x = col(f'{aid}.root')
        law[f'{aid}/carriage_y'] = col(f'{aid}.root', 1)-float(cfg['root_y']); law[f'{aid}/carriage'] = x
        if rig.mallet(aid): law[f'{aid}/lean'] = col(f'{aid}.q.lean')
        th = math.pi/2-col(f'{aid}.q.shoulder'); el = th-col(f'{aid}.q.elbow')
        law.update({f'{aid}/shoulder': th, f'{aid}/shoulder_pair': th, f'{aid}/elbowhead': -th,
                    f'{aid}/elbow': el, f'{aid}/elbow_pair': el, f'{aid}/wristhead': -el, f'{aid}/tool': np.zeros(len(T))})
        if 'head' in cfg: law[f'{aid}/head'] = -col(f'{aid}.head')*float(hdr['flip_sign'])
        if cfg.get('drive', 'rack') == 'rack':
            phase = hdr['pawl_phase'] if hdr['pawl_phase'] is not None else 0.0
            law[f'{aid}/pinion'] = (x+phase)/PINION['r_pitch']
            if 'pawl' in cfg:
                law[f'{aid}/pawl'] = -np.array([bake.pawl(aid, float(t)) for t in T]); pawls.append(f'{aid}/pawl')
                law[f'{aid}/roller'] = x*float(cfg['pawl'].get('roller_spin', 0.0))
        else:
            law[f'{aid}/screw'] = -2*math.pi*x/float(cfg['screw']['pitch']); wrapped.add(f'{aid}/screw')
        if hdr['stepped']: law[f'{aid}/rail'] = col(f'{aid}.sag'); law[f'{aid}/sway'] = col(f'{aid}.sway')
    for mid in h['mechanisms']:
        law[f'{mid}/stand'] = col(f'{mid}.stand') if f'{mid}.stand' in bake.index else np.zeros(len(T))
    bpm = float(rig.score.get('bpm', 84.0)); fw = -2*math.pi*T*bpm/240.0; law['chamber/flywheel'] = fw
    g = rig.geometry.get('flywheel')
    law['chamber/belt_pulley'] = fw*((float(g['wraps'][0][1])/float(g['wraps'][1][1])) if 'wraps' in g else (float(g['cyls']['drive pulley'][2])/float(g['cyls']['belt pulley'][2]))) if g else fw
    missing = sorted(set(C.ids)-set(law)); worst = 0.0; where = ''; inband = True
    for jid, v in law.items():
        q = (Q64 if jid in pawls else Q)[jid]
        if jid in wrapped:
            w = np.mod(v+math.pi, 2*math.pi)-math.pi; e = np.abs(np.remainder(q-w+math.pi, 2*math.pi)-math.pi)
            inband &= bool(np.all((q >= -math.pi) & (q <= math.pi)))
        else: e = np.abs(q-v)
        k = int(np.argmax(e))
        if e[k] > worst: worst = float(e[k]); where = f'{jid} at {T[k]:.3f} s'
    check(not missing and worst <= LAW and inband,
          f'T6 every joint\'s value is its law on the rows: {len(law)} joints x {len(T)} rows, worst {worst:.1e} ({where})'
          + (f'; no law for {missing}' if missing else '') + ('' if inband else '; a screw outside [-pi, pi]'))
    tab = max([float(np.abs(Q[j]-Q64[j]).max()) for j in pawls], default=0.0)
    check(tab < 1e-6, f'T6 ...and the harness\'s pawl, on the float32 table, within {tab:.1e} rad of it ({len(pawls)} pawls)')

def t7_declared(bake, rig):
    """T7: the declared structure round trips: the header's is rig.declared's
    serialized, Bake.declared gives it back (bounds to +-inf), and the prep
    table is the prep function sampled."""
    h = bake.header; hdr_ok = back_ok = prep_ok = True; n_s = n_k = n_p = 0; interp = 0.0
    def fin(x): return None if not math.isfinite(x) else float(x)
    for aid in rig.plans:
        d = SEG.declared(rig, aid); got = h['arms'][aid]['declared']
        want = dict(native=bool(d.native),
                    segments=[dict(t0=fin(g.t0), t1=fin(g.t1), law=g.law, tag=g.tag, event=g.event, extra=J.json_safe(g.extra))
                              for g in d.segments],
                    knots=[dict(t=float(k.t), kind=k.kind, dv=None if k.dv is None else [float(v) for v in k.dv],
                                event=k.event, extra=J.json_safe(k.extra)) for k in d.knots],
                    rings=J.json_safe(list(d.rings)))
        hdr_ok &= all(got[k] == want[k] for k in want)
        n_s += len(d.segments); n_k += len(d.knots)
        b = bake.declared(aid)
        back_ok &= b.native == d.native and len(b.segments) == len(d.segments) and len(b.knots) == len(d.knots)
        back_ok &= all((x.t0, x.t1, x.law, x.tag, x.event) == (y.t0, y.t1, y.law, y.tag, y.event)
                       and J.json_safe(x.extra) == J.json_safe(y.extra) for x, y in zip(b.segments, d.segments))
        back_ok &= all(x.t == y.t and x.kind == y.kind and x.event == y.event
                       and ((x.dv is None and y.dv is None) or (x.dv is not None and y.dv is not None and np.array_equal(x.dv, y.dv)))
                       and J.json_safe(x.extra) == J.json_safe(y.extra) for x, y in zip(b.knots, d.knots))
        back_ok &= J.json_safe(list(b.rings)) == J.json_safe(list(d.rings))
        p = got['prep']
        if d.prep is None: prep_ok &= p is None and b.prep is None; continue
        n_p += 1; fn = d.prep
        name = f'{fn.__module__}.{fn.__qualname__}'; name = name if name.startswith('formlab.') else 'formlab.'+name
        prep_ok &= (p['fn'] == name and p['a'] == [float(a) for a in np.linspace(0, 1, 9)]
                    and p['ioi'] == [float(i) for i in np.geomspace(0.02, 8.0, 64)]
                    and all(p['h'][i][j] == float(fn(a, ioi)) for i, a in enumerate(p['a']) for j, ioi in enumerate(p['ioi']))
                    and all(p['h_first'][i] == float(fn(a, None)) for i, a in enumerate(p['a'])))
        interp = max([interp]+[abs(b.prep(a, ioi)-p['h'][i][j]) for i, a in enumerate(p['a']) for j, ioi in enumerate(p['ioi'])]
                     + [abs(b.prep(a, None)-p['h_first'][i]) for i, a in enumerate(p['a'])])
    check(hdr_ok, f'T7 the header\'s declared structure is rig.declared\'s, field for field ({n_s} segments, {n_k} knots, the rings)')
    check(back_ok, 'T7 ...and Bake.declared gives it back (null bounds to -/+inf, dv to arrays)')
    check(prep_ok and interp <= 1e-12,
          f'T7 ...and the {n_p} prep tables are the prep functions sampled on 9 a x 64 ioi, h_first a first note; '
          f'Bake.declared\'s prep reads them back at the nodes (worst {interp:.1e})')
    vocab = dict(tags=sorted(SEG.TAGS), knot_kinds=sorted(SEG.KNOT_KINDS), impulses=sorted(SEG.IMPULSES), laws=sorted(SEG.LAWS),
                 channels=sorted(SEG.CHANNELS), hold_kinds=sorted(SEG.HOLD_KINDS), regimes=sorted(SEG.REGIMES))
    check(h['declared_vocab'] == vocab, 'T7 declared_vocab is formlab/segments.py\'s vocabularies, sorted')

def t8_strict(json_path):
    """T8: the header is strict JSON (no NaN, no Infinity)."""
    def no(c): raise ValueError(c)
    try: json.loads(Path(json_path).read_text(), parse_constant=no); err = ''
    except ValueError as e: err = str(e)
    check(not err, f'T8 the header is strict JSON ({Path(json_path).stat().st_size/1e3:.0f} kB)' + (f': {err}' if err else ''))

def synth_row(owner, name, parent, typ, axis, origin, value):
    return dict(id=f'{owner}/{name}', owner=owner, name=name, parent=parent, type=typ, axis=axis, origin=origin,
                q_home=0.0, value=value, spin=False, unit={'revolute': 'rad', 'prismatic': 'm'}.get(typ), limits=None,
                range=None, driver=dict(kind='synthetic'), pose=None, extra={})

SYNTH = 't10_'   # the synthetic rows' name prefix: never a real joint's (M7's palm, M9's pendulum are)

def synth_joints(h):
    """Future joints as rows (§4): a palm on a pick's tool with a 2-DOF thumb,
    a finger (MCP about the palm's y, PIP coupled to it, DIP through a table),
    a tendon drum on a periodic table, a slide off a principal axis, a fixed
    splay and a pendulum on the rake's carriage reading a channel operand.
    Unpinned, no bodies: the evaluator's general path. Named `t10_*`, so a
    real joint added later (a palm, a pendulum) never collides with them."""
    a = 'harp_arm0'; rk = 'rake_arm0'; p = SYNTH
    def v(src, *ops): return dict(src=src, ops=[list(o) for o in ops])
    T = dict(time=True)
    return [
        synth_row(a, p+'palm', f'{a}/tool', 'fixed', None, [0.0, -0.03, 0.01], None),
        synth_row(a, p+'thumb_a', f'{a}/{p}palm', 'revolute', [1.0, 0.0, 0.0], [0.02, 0.0, 0.0], v(T, ['mul', 1.7], ['wrap', '-PI', 'PI'])),
        synth_row(a, p+'thumb_b', f'{a}/{p}thumb_a', 'revolute', [0.0, 0.0, 1.0], [0.0, -0.02, 0.0], v(T, ['mul', -2.3], ['add', 0.4], ['wrap', -1.0, 1.0])),
        synth_row(a, p+'mcp', f'{a}/{p}palm', 'revolute', [0.0, 1.0, 0.0], [0.0, -0.04, 0.0], v(T, ['mul', 0.9], ['wrap', '-PI', 'PI'])),
        synth_row(a, p+'pip', f'{a}/{p}mcp', 'revolute', [1.0, 0.0, 0.0], [0.0, -0.03, 0.0], v(dict(joint=f'{a}/{p}mcp'), ['mul', 0.7])),
        synth_row(a, p+'dip', f'{a}/{p}pip', 'revolute', [1.0, 0.0, 0.0], [0.0, -0.02, 0.0],
                  v(dict(joint=f'{a}/{p}pip'), ['table', dict(x=[-3.0, -1.0, 0.0, 3.0], y=[-1.0, -0.4, 0.2, 1.5], period=None)])),
        synth_row(a, p+'drum', f'{a}/{p}mcp', 'revolute', [0.0, 0.0, 1.0], [0.0, 0.0, 0.0],
                  v(dict(joint=f'{a}/{p}mcp'), ['mul', [3, 2]], ['table', dict(x=[0.0, 1.0, 2.0], y=[0.0, 0.5, 0.25], period=2.0)])),
        synth_row(a, p+'slide', f'{a}/{p}palm', 'prismatic', [0.6, 0.8, 0.0], [0.01, 0.0, 0.0], v(T, ['mul', 0.01], ['wrap', -0.5, 0.5])),
        synth_row(a, p+'splay', f'{a}/{p}thumb_b', 'revolute', [0.0, 1.0, 0.0], [0.0, -0.01, 0.0], v(dict(const=0.25))),
        synth_row(rk, p+'pendulum', f'{rk}/carriage', 'revolute', [0.0, 0.0, 1.0], [0.0, -0.1, 0.05],
                  v(T, ['mul', 3.0], ['add', {'channel': f'{rk}.sway'}], ['wrap', 'PI/2', 'TAU'])),
    ]

def synth_header(h):
    h['joints'] += synth_joints(h)
    return h

def _axis_rot(axis, a):
    k = np.asarray(axis, float); k = k/np.linalg.norm(k); K = np.array([[0, -k[2], k[1]], [k[2], 0, -k[0]], [-k[1], k[0], 0]])
    return np.eye(3)+math.sin(a)*K+(1-math.cos(a))*K@K

def t10_synthetic(score_path, asset, out_fn=None):
    """T10: future joints evaluate with no reader change (both readers), and
    an op the readers do not know and an axis that is not a unit vector are
    refused by name. A reader that raises fails T10; the checks after it run."""
    try: _t10_synthetic(score_path, asset, out_fn)
    except Exception as e:
        check(False, f'T10 the synthetic joints: {type(e).__name__}: {e}')

def _t10_synthetic(score_path, asset, out_fn=None):
    def wrap(q, lo, hi): return lo+np.mod(q-lo, hi-lo)
    with temp_bake(score_path, asset, synth_header) as (sp, jp):
        bake = B.Bake(jp); C = bake.kin; S = synth_joints({})
        ids = [r['id'] for r in S]; sway = bake.index['rake_arm0.sway']['offset']
        ts = list(np.linspace(bake.times[0]-1, bake.times[-1]+1, 301))+[float(bake.times[k]) for k in (0, 7, 1000, len(bake.times)-1)]
        wq = wp = wb = 0.0
        for t in ts:
            fr = bake.joint_frames(t); row = bake.row_godot(t)
            q = {'palm': 0.0, 'thumb_a': wrap(t*1.7, -math.pi, math.pi), 'thumb_b': wrap(t*-2.3+0.4, -1.0, 1.0),
                 'mcp': wrap(t*0.9, -math.pi, math.pi), 'splay': 0.25,
                 'slide': wrap(t*0.01, -0.5, 0.5)}
            q['pip'] = q['mcp']*0.7
            q['dip'] = float(np.interp(min(max(q['pip'], -3.0), 3.0), [-3.0, -1.0, 0.0, 3.0], [-1.0, -0.4, 0.2, 1.5]))
            q['drum'] = float(np.interp(np.mod(q['mcp']*1.5, 2.0), [0.0, 1.0, 2.0], [0.0, 0.5, 0.25]))
            q['pendulum'] = wrap(t*3.0+float(row[sway]), math.pi/2, 2*math.pi)
            mine = {}   # the independent chain: a parent's frame is this loop's own once it is a synthetic joint
            for r in S:
                pid = r['parent']; n = r['name'][len(SYNTH):]
                Pp, Bp = mine[pid] if pid in mine else (fr[pid][0], np.eye(3) if fr[pid][3] else fr[pid][1])
                O = np.asarray(r['origin'], float)
                if r['type'] == 'prismatic': O = O+np.asarray(r['axis'], float)*q[n]
                P = Pp+Bp@O; Bm = Bp@_axis_rot(r['axis'], q[n]) if r['type'] == 'revolute' else Bp
                mine[r['id']] = (P, Bm); got = fr[r['id']]
                wq = max(wq, abs(got[2]-q[n])); wp = max(wp, float(np.abs(got[0]-P).max())); wb = max(wb, float(np.abs(got[1]-Bm).max()))
        check(wq <= Q_RAD and wp <= POSE_M and wb <= POSE_M,
              f'T10 future joints as rows ({len(ids)}: a thumb, a finger, a drum, a slide, a pendulum) evaluate in formlab.bake.Bake '
              f'as an independent FK computes them: {len(ts)} times, worst q {wq:.1e}, P {wp:.1e} m, B {wb:.1e}')
        if out_fn is not None: out_fn(bake, sp, ids)
    def spline(h):
        h = synth_header(h); h['joints'][-2]['value']['ops'].append(['spline', 1.0]); return h
    with temp_bake(score_path, asset, spline) as (sp, jp):
        try: B.Bake(jp); msg = ''
        except ValueError as e: msg = str(e)
        jid = f'harp_arm0/{SYNTH}splay'
        check(f"joint {jid} uses op 'spline' this reader does not know" in msg,
              f'T10 formlab.bake refuses an op it does not know, naming the joint and the op' + ('' if msg else ' (it read it)'))
        out = godot(sp, asset, ['--joints_only'])
        if out is None: print('  SKIP godot not on PATH: the harness\'s unknown-op refusal unmeasured'); return
        out = out.replace("\\'", "'")      # dump_bake prints MotionBake.errors, a PackedStringArray: quotes come escaped
        check('ERROR' in out and f"joint {jid} uses op 'spline' this reader does not know" in out and 'JOINT' not in out,
              'T10 ...and so does the harness')
    def tilted(h):
        h = synth_header(h); h['joints'][-1]['axis'] = [0.0, 1.0, 1.0]; return h
    with temp_bake(score_path, asset, tilted) as (sp, jp):
        try: B.Bake(jp); msg = ''
        except ValueError as e: msg = str(e)
        jid = f'rake_arm0/{SYNTH}pendulum'
        check(f'joint {jid} has a non-unit axis' in msg,
              f'T10 formlab.bake refuses a joint axis that is not a unit vector, naming the joint' + ('' if msg else ' (it read it)'))
        out = godot(sp, asset, ['--joints_only'])
        if out is None: print('  SKIP godot not on PATH: the harness\'s axis refusal unmeasured'); return
        check('ERROR' in out and f'joint {jid} has a non-unit axis' in out and 'JOINT' not in out,
              'T10 ...and so does the harness (it would pose an identity basis, with an engine error a frame)')

def t12_ranges(bake, F, T):
    """T12: each joint's range is its values' on the rows; no limits in M3;
    spin marks the wheels."""
    h = bake.header; Q = J.value_rows(bake.kin, F, T)
    rng = all(jt['range'] == [float(Q[jt['id']].min()), float(Q[jt['id']].max())] for jt in h['joints'])
    lim = all(jt['limits'] is None for jt in h['joints'])
    spin = all(jt['spin'] == (jt['name'] in SPIN) for jt in h['joints'])
    check(rng and lim and spin, f'T12 every joint\'s range is [min, max] of its values on the rows, its limits null, and spin '
                                f'set exactly on {", ".join(SPIN)} ({sum(jt["spin"] for jt in h["joints"])} joints)')

def v2_checks(bake, rig, score_path, json_path, asset, poses, load_ms):
    F = bake.frames.astype(np.float64); T = np.asarray(bake.times, np.float64)
    t1_refuses_v1(score_path, asset)
    t2_prefix(bake, rig)
    t3_q(bake, rig, poses)
    t4_table(bake, rig)
    t5_tree(bake, rig, F, T)
    t6_laws(bake, rig, F, T)
    t7_declared(bake, rig)
    t8_strict(json_path)
    t10_synthetic(score_path, asset, out_fn=lambda b, sp, ids: synthetic_parity(b, sp, asset, ids))
    t12_ranges(bake, F, T)
    print(f'  INFO T13 formlab.bake.Bake loads the bake in {load_ms:.0f} ms')

def synthetic_parity(bake, score_path, asset, ids):
    """T10 in the harness: dump_bake --joints_only on the synthetic header."""
    out = godot(score_path, asset, ['--joints_only'])
    if out is None: print('  SKIP godot not on PATH: the harness\'s future joints unmeasured'); return
    rows = joint_lines(out, 'JOINT')
    n, wq, wp, wb, where = compare_joints(bake, rows, False, lambda tp: round(tp*13)/13.0, set(ids))
    check(n > 1000 and wq <= Q_RAD and wp <= POSE_M and wb <= POSE_M,
          f'T10 ...and in the harness (MotionBake.frames_at, no reader change): {n} JOINT lines of the synthetic joints, worst q '
          f'{wq:.1e}, P {wp:.1e} m, B {wb:.1e} ({where})')

def snap_row(bake):
    """The bake row time nearest a printed %.9f t (rows are >= MERGE_S apart)."""
    T = bake.times
    def f(tp):
        i = int(np.clip(np.searchsorted(T, tp), 1, len(T)-1))
        return float(T[i] if abs(T[i]-tp) < abs(T[i-1]-tp) else T[i-1])
    return f

def v2_parity(bake, out):
    """T9 and T13: the harness's joints table (dump_bake's JOINT / JOINTFK /
    HEADL / SEG / KNOT / RING / LOADMS lines) against formlab.bake.Bake."""
    h = bake.header
    rows = joint_lines(out, 'JOINT')
    n, wq, wp, wb, where = compare_joints(bake, rows, False, lambda tp: round(tp*13)/13.0)
    check(n > 1000 and wq <= Q_RAD and wp <= POSE_M and wb <= POSE_M,
          f'T9 the harness\'s joint frames are formlab.kinematics.evaluate\'s (pose mode): {n} JOINT lines over {len(set(r[1] for r in rows))} '
          f'times, worst q {wq:.1e} rad, P {wp:.1e} m, B {wb:.1e} ({where})')
    rows = joint_lines(out, 'JOINTFK')
    n, wq, wp, wb, where = compare_joints(bake, rows, True, snap_row(bake))
    check(n > 200 and wq <= Q_RAD and wp <= FK_M and wb <= FK_M,
          f'T9 ...and in FK mode (the chain rule from q, at every 50th row): {n} JOINTFK lines, worst q {wq:.1e} rad, P {wp:.1e} m, '
          f'B {wb:.1e} ({where})')
    hl = {}; segs = {}; knots = {}; rings = {}; ms = None
    for line in out.splitlines():
        f = line.split()
        if not f: continue
        if f[0] == 'HEADL': hl[f[1]] = float(f[2])
        elif f[0] == 'SEG': segs.setdefault(f[1], []).append((None if f[2] == 'null' else float(f[2]), None if f[3] == 'null' else float(f[3]),
                                                             int(f[4]), f[5], ' '.join(f[6:])))
        elif f[0] == 'KNOT': knots.setdefault(f[1], []).append((float(f[2]), f[3], int(f[4])))
        elif f[0] == 'RING': rings.setdefault(f[1], []).append((f[2], f[3], float(f[4]), float(f[5]), float(f[6])))
        elif f[0] == 'LOADMS': ms = float(f[1])
    check(hl.keys() == h['arms'].keys() and all(abs(hl[a]-bake.head_l(a)) <= 1e-12 for a in hl),
          f'T9 the harness\'s head_length is the header\'s head_l on every arm ({len(hl)})')
    def near(a, b): return (a is None and b is None) or (a is not None and b is not None and abs(a-b) <= 1e-9)
    ok = True; ns = nk = nr = 0
    for aid, arm in h['arms'].items():
        d = arm['declared']; S = segs.get(aid, []); K = knots.get(aid, []); Rg = rings.get(aid, [])
        ok &= len(S) == len(d['segments']) and len(K) == len(d['knots']) and len(Rg) == len(d['rings'])
        ok &= all(near(s[0], g['t0']) and near(s[1], g['t1']) and s[2] == g['event'] and s[3] == g['tag'] and s[4] == g['law']
                  for s, g in zip(S, d['segments']))
        ok &= all(near(k[0], g['t']) and k[1] == g['kind'] and k[2] == g['event'] for k, g in zip(K, d['knots']))
        ok &= all(r[0] == g['name'] and r[1] == g['channel'] and abs(r[2]-g['amp']) <= 1e-9 and abs(r[3]-g['f']) <= 1e-9
                  and abs(r[4]-g['tau']) <= 1e-9 for r, g in zip(Rg, d['rings']))
        ns += len(S); nk += len(K); nr += len(Rg)
    check(ok and ns > 0, f'T9 ...and MotionBake.declared reads the declared structure: {ns} segments, {nk} knots, {nr} rings (t within 1e-9 s)')
    if ms is None: check(False, 'T13 dump_bake reports LOADMS')
    else: print(f'  {"WARN" if ms > LOADMS_WARN else "INFO"} T13 the harness loads the bake (MotionBake.load, the joints table compiled) in {ms:.0f} ms'
                + (f' (above {LOADMS_WARN:.0f} ms)' if ms > LOADMS_WARN else ''))

def run(layout_path, score_path):
    asset = layout_path.stem
    print(f'== {asset} / {score_path}')
    json_path, _ = B.paths(score_path, asset)
    if not json_path.exists():
        check(False, f'no bake at {json_path}: run python3 tools/bake_motion.py --asset={asset}'); return
    t_load = time.perf_counter(); bake = B.Bake(json_path); load_ms = (time.perf_counter()-t_load)*1e3; h = bake.header
    fresh = bake.fresh(score_path, layout_path)
    check(fresh, f'the bake is fresh (score and manifest fingerprints)' +
          ('' if fresh else f' — run python3 tools/bake_motion.py --asset={asset}'))
    if not fresh: return
    rig = Rig.load(score_path, layout_path)
    check(h['format'] == B.FORMAT and len(bake.times) == h['samples'] and np.all(np.diff(bake.times) > 0),
          f'{h["samples"]} rows x {h["width"]} channels, strictly increasing times from {h["t0"]:.2f} to {h["t1"]:.2f} s')
    # every row is the rig, to float32 (a sample of rows: the rig is slow)
    worst = 0.0; samp = {aid: [] for aid in rig.plans}
    for i in range(0, len(bake.times), 11):
        t = float(bake.times[i])
        for aid in rig.plans:
            p = rig.pose(aid, t); samp[aid].append(p)
            for k in ('root', 'elbow', 'wrist', 'tip'):
                worst = max(worst, float(np.abs(bake.frames[i, bake.index[f'{aid}.{k}']['offset']:][:3]-p[k]).max()))
    check(worst < FLOAT32_M, f'every row is the rig\'s pose at its time (worst {worst:.1e} m over {len(bake.times)//11} rows)')
    idx = np.arange(0, len(bake.times), 11)
    poses = {aid: (idx,)+tuple(np.array([p[k] for p in samp[aid]], float) for k in ('root', 'elbow', 'wrist')) for aid in rig.plans}
    # contacts are rows, so they land exactly
    worst = 0.0; nc = 0
    for e in rig.score['events']:
        aid = e['actuator']
        for sid, t in zip(e['strings'], ST.motion_timing.string_times(e)):  # a roll's at its onsets
            nc += 1
            worst = max(worst, float(np.linalg.norm(bake.felt(aid, t)-rig.contact(sid, e.get('pick')))))
    check(worst < FLOAT32_M, f'every contact lands exactly: {nc} contacts, worst {worst:.1e} m')
    bad = {aid: a['unreachable'] for aid, a in h['arms'].items() if a['unreachable']}
    check(not bad, f'no arm is ever out of reach' + (f': {bad}' if bad else ''))
    # between rows
    ts = np.random.default_rng(7).uniform(bake.times[0], bake.times[-1], 2500)
    pin = head = shake = 0.0; where = ''
    for aid in rig.plans:
        lo, hi = rig.rail_span(aid); mech = rig.mech_of[aid]
        for t in ts:
            row = bake.row(t); p = rig.pose(aid, t)
            for k in ('root', 'elbow', 'wrist', 'tip'):
                e = float(np.linalg.norm(bake.get(f'{aid}.{k}', t, row)-p[k]))
                if e > pin: pin = e; where = f'{aid}.{k} at {t:.3f} s'
            pin = max(pin, float(np.linalg.norm(bake.felt(aid, t)-p['felt'])))
            head = max(head, abs(bake.get(f'{aid}.head', t, row)-p['head']))
            shake = max(shake, abs(bake.get(f'{aid}.sag', t, row)-rig.rail_sag(aid, t, (lo+hi)/2)),
                        abs(bake.get(f'{aid}.sway', t, row)-rig.mast_sway(aid, t)),
                        abs(bake.get(f'{mech}.stand', t, row)-rig.stand_thump(mech, t)))
    check(pin < INTERP_M, f'between rows every pin stays within {INTERP_M*1000:.0f} mm of the rig (worst {pin*1000:.2f} mm, {where})')
    check(head < INTERP_RAD, f'...and the hinged head within {INTERP_RAD} rad (worst {head:.4f})')
    check(shake < 2e-4, f'...and the assembly\'s shudders within 0.2 mm / mrad (worst {shake*1000:.3f})')
    same = all(np.allclose(np.array(h['arms'][aid]['clicks']).reshape(-1, 2), np.array(rig.click_times(aid)).reshape(-1, 2))
               for aid in rig.plans)
    check(same, f'the clicks are the rig\'s: {sum(len(a["clicks"]) for a in h["arms"].values())}')
    # a stepped arm's pawl ride: Rig.pawl_ride at the rows, in [0, 1], nothing at a contact
    ride_info = []
    for aid, arm in h['arms'].items():
        name = f'{aid}.ride'
        if not rig.stepped(aid):
            check(name not in bake.index, f'{aid}: a servo arm has no .ride channel'); continue
        if name not in bake.index:
            check(False, f'{aid}: a stepped arm without a .ride channel'); continue
        c = bake.index[name]['offset']; col = bake.frames[:, c].astype(float)
        idx = range(0, len(bake.times), 11)
        worst = max(abs(col[i]-rig.pawl_ride(aid, float(bake.times[i]))) for i in idx)
        at_hit = max([abs(bake.ride(aid, float(b['t']))) for b in arm['blows']], default=0.0)
        check(worst < 1e-6 and col.min() >= 0.0 and col.max() <= 1.0 and at_hit < 1e-9,
              f'{aid}: .ride is Rig.pawl_ride at the rows (worst {worst:.1e} over {len(idx)} rows), in [0, 1] '
              f'(max {col.max():.3f}), 0 at every contact (worst {at_hit:.1e})')
        if rig.hammer(aid): check(np.abs(col).max() == 0.0, f'{aid}: the hammer\'s pawl never rides')
        else:
            # rows sit where the tooth rate crosses each RIDE_ROWS fraction of the band, so between two rows the
            # rate stays in one cell [k/8, (k+1)/8] of it and the smoothstep ride in [s(k/8), s((k+1)/8)]: a straight
            # line between the rows strays from Rig.pawl_ride by at most that cell's width (judged per interval,
            # on every interval that touches a freewheel travel)
            st = rig.stroke(aid); rt = st.ride_times()
            gap = np.array([float(np.min(np.abs(bake.times-t))) for t in rt]) if len(rt) else np.zeros(0)
            check(not gap.size or gap.max() <= B.MERGE_S,
                  f'{aid}: a row at every RIDE_ROWS crossing of the tooth rate ({len(rt)}, worst {gap.max() if gap.size else 0:.1e} s)')
            lo, hi = ST.PAWL_RIDE_BAND; lv = np.asarray(ST.RIDE_ROWS, float); sm = lambda u: u*u*(3-2*u)
            mid = bake.times[:-1]+.5*np.diff(bake.times)
            fw = [(tv['t0'], tv['t1']) for tv in st.travels if tv['regime'] == 'freewheel']
            sel = np.flatnonzero(np.any([(bake.times[1:] > a) & (bake.times[:-1] < b) for a, b in fw], axis=0)) if fw else []
            if len(sel):
                lin = .5*(col[sel]+col[sel+1]); live = np.array([rig.pawl_ride(aid, float(mid[i])) for i in sel])
                u = np.clip((np.abs(st.x(mid[sel], 1))/ST._PITCH-lo)/(hi-lo), 0.0, 1.0)
                k = np.clip(np.searchsorted(lv, u, side='right')-1, 0, len(lv)-2)
                bound = sm(lv[k+1])-sm(lv[k])+2e-7          # + the float32 rounding of the two stored rows
                err = np.abs(lin-live); worst = int(np.argmax(err/bound))
                check(np.all(err <= bound), f'{aid}: between rows the linear ride stays within its RIDE_ROWS cell of '
                      f'Rig.pawl_ride ({len(sel)} freewheel intervals; worst {err.max():.4f}, at most {(err/bound).max():.2f} of its cell)')
                ride_info.append(f'{aid} {err.max():.3f}')
    # each click's pawl and step: a mallet's are its stroke's click knots, the hammer's all drop and stepped
    for aid, arm in h['arms'].items():
        cs, cp, cs_step = arm['clicks'], arm.get('click_pawl'), arm.get('click_step')
        if cp is None or cs_step is None or not (len(cs) == len(cp) == len(cs_step)):
            check(False, f'{aid}: click_pawl / click_step missing or not parallel to clicks'); continue
        st = rig.stroke(aid) if rig.mallet(aid) else None
        if st is not None:
            kn = sorted([k for k in st.knots if k.kind == 'click'], key=lambda k: float(k.extra.get('t_end', k.t)))
            lab = [int(k.extra['pawl'] == 'ride') for k in kn]; stp = [int('t_end' in k.extra) for k in kn]
            bad = sum(k.extra['pawl'] != ('drop' if 't_end' in k.extra or abs(float(st.x(k.t, 1)))/ST._PITCH < ST.PAWL_RIDE else 'ride')
                      for k in kn)
            check(lab == cp and stp == cs_step and bad == 0,
                  f'{aid}: click_pawl / click_step are the stroke\'s click knots ({len(cs)} clicks: {sum(cp)} ride, '
                  f'{len(cs)-sum(cs_step)} freewheel; {bad} pawl labels off |x\'|/PITCH vs PAWL_RIDE)')
        else:
            check(cp == [0]*len(cs) and cs_step == [1]*len(cs), f'{aid}: every {arm["kind"]} click drops and is stepped ({len(cs)})')
    # the blows are the rig's recoil bus; a mallet's carry its stroke's v_in and e, gated by the next apex
    for aid, arm in h['arms'].items():
        bus = rig.blows_by_arm.get(aid, [])
        ok = len(arm['blows']) == len(bus)
        for b, r in zip(arm['blows'], bus):
            ok &= b['t'] == r['t'] and b['x'] == r['x'] and b['energy'] == r['energy']
            ok &= (b['gate_end'] is None) if not np.isfinite(r['gate_end']) else b['gate_end'] == r['gate_end']
            ok &= all((k in b) == (k in r) and (k not in r or b[k] == r[k]) for k in ('v_in', 'e'))
        st = rig.stroke(aid) if rig.mallet(aid) else None
        if st is not None:
            N = sorted(st.notes, key=lambda n: n.t)
            ok &= len(N) == len(arm['blows']) and all(
                b['v_in'] == float(n.v_in) and b['e'] == float(n.e) and b['energy'] == float(n.amp)
                and (b['gate_end'] is None if i+1 == len(N) else b['gate_end'] == float(N[i+1].t_apex))
                for i, (b, n) in enumerate(zip(arm['blows'], N)))
        elif arm['blows']: ok &= not any('v_in' in b or 'e' in b for b in arm['blows'])
        if bus or arm['blows']:
            check(ok, f'{aid}: {len(arm["blows"])} blows are the rig\'s recoil bus'
                      + (' (v_in, e from the stroke; gate_end the next apex)' if st is not None else ''))
    xs = np.random.default_rng(3).uniform(-5, 5, 5000)
    tab = max(abs(bake.pawl_angle(x)-a) for x, a in zip(xs, W.angle(xs)))
    check(tab < 5e-4, f'the pawl\'s one-tooth table is formlab.pawl.angle (worst {tab:.1e} rad over 5000 rail positions)')
    least = float(W.angle(np.linspace(0, W.PITCH, 20001)).min()); ra = h['pawl'].get('ride_angle')
    check(ra is not None and ra == min(h['pawl']['table']) and abs(least-ra) < 2e-4,
          f'pawl.ride_angle is the table\'s least angle, the nose on a tip ({np.degrees(ra) if ra is not None else float("nan"):.3f} deg; formlab.pawl.angle\'s least {np.degrees(least):.3f})')
    check(h['constants'].get('PAWL_RIDE') == ST.PAWL_RIDE, f'constants.PAWL_RIDE is formlab.stroke\'s ({h["constants"].get("PAWL_RIDE")})')
    v2_checks(bake, rig, score_path, json_path, asset, poses, load_ms)
    parity(bake, score_path, asset)
    if asset == 'clockwork': refuses_stale(score_path, asset)

if __name__ == '__main__':
    if len(sys.argv) == 3: pairs = [(Path(sys.argv[1]), Path(sys.argv[2]))]
    else:
        pairs = []
        for asset in ('clockwork', 'clockwork_expanded'):   # this tree's scores (a manifest's "score" is where it was built)
            pairs.append((ROOT/'harness'/'assets'/f'{asset}.json', B.default_score(asset, ROOT)))
    for lp, sp in pairs: run(lp, sp)
    print('BAKE: PASS' if not failures else f'BAKE: FAIL ({len(failures)})')
    sys.exit(1 if failures else 0)

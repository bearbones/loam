"""Ruler 2 (screen) of docs/goals/the-players.md: how far each part jumps on
the film's frame, against its own size there.

For every film frame k (t_k = k/30) and every arm, three parts are put on the
1920x1080 frame through render/film/camera.json (exported from
harness/film_director.gd by harness/dev/export_camera.gd — never
re-implemented here; the projection is the one the file states, checked
against Godot's own unproject_position on the file's probes):

    tool   the point that touches the instrument (Rig.pose 'felt': the tip, or
           a hinged hammer's felt face), carrying the tool's body
    wrist  the wrist pin, carrying the wristhead's boss
    elbow  the elbow pin, carrying the elbowhead's boss

    rho_px = |dq_k| / X_k,   dq_k = q(t_k) - q(t_{k-1})   (each through its own frame's camera)

X_k is the part's projected extent along dq: the spread of its body points
along the screen direction of dq plus twice its radius in pixels at its depth
— the screen form of the goal's E(part, d) = 2r + |seg.d| — the mean of the
two frames'. The bodies are formlab.clearance.arm_capsules' where it has one
(called as formlab.gantry does), documented extents where it has none:

    pick, rake  arm_capsules 'tool': the plectrum and swan neck, contact to the
             neck's apex, r 0.03 (so 0.06 m along the pluck, not the blade's 7 mm)
    hammer   arm_capsules 'head': the felt ball
    mallet   the wound head, a sphere r 0.06 seated on the contact, 0.12 m across
             (linkage.mallet_tool; arm_capsules' generic r 0.03 'tool' does not hold it)
    wrist    the wristhead's bosses (r DEFAULT_SPEC boss_r = 0.05) at the wrist
             pin and the second bar's pin (wrist + o2)
    elbow    the elbowhead's bosses at the elbow pin, elbow + o1 and elbow + o2

Only frame pairs inside one shot (a cut is not motion) with the point in front
of the camera and inside the frame in both frames are measured — the
conditions of the scratch baseline that gave the goal its provisional cells.

Target: rho_px <= 1.0 on every frame that is not an impulse frame of its arm
(Subject.impulse_frame). Report only: per-frame jumps of the tool over 30 px
and the largest, over the piece and in 44-68 s, under the current camera and,
when render/players/before/camera.json exists (the camera frozen at M0 with
the before reel: tools/players_reel.sh before), under that one too.

The expanded asset has no film, so no camera: n/a.
"""
import hashlib, json, sys
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from players.core import FPS, INFO, ROOT, Result
from formlab.clearance import DEFAULT_SPEC, arm_capsules, default_layers, drive_kind

JUMP_PX = 30.0
WINDOW = (44.0, 68.0)            # the busiest stretch of the film: the tune and its runs
TARGET = 1.0
BOSS_R = DEFAULT_SPEC['boss_r']
MALLET_R = .06
FROZEN = ROOT/'render/players/before/camera.json'
PARTS = ('tool', 'wrist', 'elbow')

# ---- the camera ----------------------------------------------------------
class Camera:
    """camera.json as arrays: per frame the camera's world axes (rows), its
    position, its focal length in pixels and its shot."""
    def __init__(self, doc):
        self.doc = doc
        self.W = float(doc['width']); self.H = float(doc['height'])
        if doc.get('keep_aspect', 'KEEP_HEIGHT') != 'KEEP_HEIGHT':
            raise ValueError(f"camera.json keep_aspect {doc.get('keep_aspect')}: this reader knows KEEP_HEIGHT (vertical fov) only")
        fr = doc['frames']
        self.k = np.array([f['k'] for f in fr]); self.t = np.array([f['t'] for f in fr], float)
        self.A = np.array([f['basis'] for f in fr], float)          # (N, 3 axes, 3)
        self.pos = np.array([f['position'] for f in fr], float)
        self.f = (self.H/2)/np.tan(np.radians(np.array([f['fov_deg'] for f in fr], float))/2)
        self.shot = np.array([f['shot'] for f in fr])
        self.near = float(doc.get('near', .05))

    def project(self, p, idx=None):
        """World points p (N, ..., 3) on frames idx (N,) -> (uv (N, ..., 2), depth (N, ...)),
        depth = distance in front of the lens (> 0 in front)."""
        idx = np.arange(len(p)) if idx is None else idx
        A = self.A[idx]; pos = self.pos[idx]; f = self.f[idx]
        extra = p.ndim-2
        shape = (len(idx),)+(1,)*extra
        d = p-pos.reshape(shape+(3,))
        q = np.einsum('n...j,nij->n...i', d, A)                    # camera-space coordinates
        z = -q[..., 2]
        with np.errstate(divide='ignore', invalid='ignore'):
            u = self.W/2+f.reshape(shape)*q[..., 0]/z
            v = self.H/2-f.reshape(shape)*q[..., 1]/z
        return np.stack([u, v], -1), z

    def check_probes(self):
        """Largest disagreement (px) between this projection and Godot's own
        unproject_position on the file's probe points."""
        pr = self.doc.get('probes', [])
        if not pr: return None
        idx = np.array([p['k'] for p in pr]); P = np.array([p['p'] for p in pr], float)
        uv, _ = self.project(P, idx)
        return float(np.abs(uv-np.array([p['px'] for p in pr], float)).max())

def _sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest() if Path(path).exists() else None

def stale(S, doc):
    """Why camera.json no longer matches what it was exported from, or ''."""
    why = []
    if doc.get('score_sha256') and doc['score_sha256'] != _sha(S.score_path): why.append('score')
    bin_path = Path(S.score_path).parent/'clockwork.motion.bin'
    if doc.get('bake_sha256') and bin_path.exists() and doc['bake_sha256'] != _sha(bin_path): why.append('bake')
    if doc.get('director_sha256') and doc['director_sha256'] != _sha(ROOT/'harness/film_director.gd'): why.append('film_director.gd')
    return ', '.join(why)

# ---- the parts -----------------------------------------------------------
def bodies(S, aid, P):
    """part -> (tracked point (N, 3), body points (N, m, 3), radius m) over the poses P."""
    kind = S.kind(aid); cfg = S.cfg(aid); felt = P['felt']
    o1 = np.asarray(cfg['o1'], float); o2 = np.asarray(cfg['o2'], float)
    if kind == 'mallet':
        tool = ((felt+[0, MALLET_R, 0])[:, None, :], MALLET_R)
    else:
        caps = arm_capsules(P, o1, o2, cfg.get('layers', default_layers(DEFAULT_SPEC)), DEFAULT_SPEC,
                            cfg.get('pinion', 'back'), drive_kind(cfg))[0]
        a, b, r = caps.get('head', caps['tool']) if kind == 'hammer' else caps['tool']
        tool = (np.stack([a, b], 1), float(r))
    wrist, elbow = P['wrist'], P['elbow']
    return dict(tool=(felt,)+tool,
                wrist=(wrist, np.stack([wrist, wrist+o2], 1), BOSS_R),
                elbow=(elbow, np.stack([elbow, elbow+o1, elbow+o2], 1), BOSS_R))

def extent(cam, body, r, idx, dhat):
    """Projected extent (px) of a body on frames idx along screen directions dhat (N, 2)."""
    uv, z = cam.project(body, idx)                       # (N, m, 2), (N, m)
    s = np.einsum('nmi,ni->nm', uv, dhat)
    zc = z.mean(axis=1)
    with np.errstate(divide='ignore', invalid='ignore'):
        return s.max(1)-s.min(1)+2*r*cam.f[idx]/zc

def measure(S, cam):
    """Per arm and part, over frame pairs (k-1, k) inside one shot with the point
    on the frame both times: k, |dq| px, rho_px."""
    n = min(len(S.t_frames), len(cam.t))
    if np.abs(cam.t[:n]-S.t_frames[:n]).max() > 1e-6: raise ValueError('camera.json frames are not t = k/30')
    out = {}
    k1 = np.arange(1, n); k0 = k1-1
    same = cam.shot[k1] == cam.shot[k0]
    for aid in S.arms:
        P = S.poses(aid, 'frames')
        for part, (pt, body, r) in bodies(S, aid, P).items():
            pt = pt[:n]; body = body[:n]
            uv, z = cam.project(pt)
            on = (z > cam.near) & (uv[:, 0] >= 0) & (uv[:, 0] <= cam.W) & (uv[:, 1] >= 0) & (uv[:, 1] <= cam.H)
            ok = same & on[k1] & on[k0]
            dq = uv[k1]-uv[k0]; px = np.linalg.norm(dq, axis=1)
            dhat = np.divide(dq, px[:, None], out=np.zeros_like(dq), where=px[:, None] > 0)
            X = .5*(extent(cam, body[k0], r, k0, dhat)+extent(cam, body[k1], r, k1, dhat))
            rho = np.divide(px, X, out=np.zeros_like(px), where=X > 0)
            out[(aid, part)] = dict(k=k1[ok], px=px[ok], rho=rho[ok])
    return out

def jumps(S, m, part='tool'):
    """The report-only numbers: jumps over JUMP_PX and the largest, overall and in WINDOW."""
    rows = [(float(px), int(k), aid) for (aid, p), d in m.items() if p == part for px, k in zip(d['px'], d['k'])]
    def summary(sel):
        big = [r for r in sel if r[0] > JUMP_PX]
        top = max(sel, default=(0.0, 0, ''))
        return dict(jumps30=len(big), px_max=round(top[0], 1), t=round(top[1]/FPS, 3), aid=top[2])
    win = [r for r in rows if WINDOW[0] <= r[1]/FPS <= WINDOW[1]]
    a = summary(rows); w = summary(win)
    return dict(jumps30=a['jumps30'], px_max=a['px_max'], t=a['t'], aid=a['aid'],
                jumps30_44_68=w['jumps30'], px_max_44_68=w['px_max'], t_44_68=w['t'], aid_44_68=w['aid'])

def screen(S):
    doc = S.camera()
    if doc is None:
        why = 'the expanded asset has no film, so no film camera' if S.camera_path is None else \
              f'no {Path(S.camera_path).relative_to(ROOT)}: run godot --headless --path harness -s dev/export_camera.gd'
        return [Result(2, 'screen', 'all', {}, None, why)]
    cam = Camera(doc)
    probe = cam.check_probes()
    if probe is not None and probe > .5:
        return [Result(2, 'screen', 'all', dict(probe_px=probe), False,
                       'this projection disagrees with Godot unproject_position on the camera.json probes')]
    old = stale(S, doc)
    m = measure(S, cam)
    out = []
    for aid in S.arms:
        best = None; over = 0; pairs = 0; worst_px = (0.0, 0, '')
        imp = {}
        for part in PARTS:
            d = m[(aid, part)]; pairs += len(d['k'])
            if len(d['px']):
                i = int(np.argmax(d['px']))
                if d['px'][i] > worst_px[0]: worst_px = (float(d['px'][i]), int(d['k'][i]), part)
            # the worst off-impulse frame: walk down from the largest rho until
            # a frame that is not an impulse frame of this arm
            for i in np.argsort(-d['rho']):
                k = int(d['k'][i]); rho = float(d['rho'][i])
                if k not in imp: imp[k] = S.impulse_frame(aid, k)
                if imp[k]:
                    continue
                if rho > TARGET: over += 1
                if best is None or rho > best[0]: best = (rho, k, part)
                if rho <= TARGET: break
        jt = int(np.sum(m[(aid, 'tool')]['px'] > JUMP_PX))
        if best is None:
            out.append(Result(2, 'screen', aid, dict(pairs=pairs), None,
                              'never on screen in the film' if not pairs else 'on screen only on its impulse frames'))
            continue
        v = dict(rho_max=round(best[0], 3), t=round(best[1]/FPS, 3), part=best[2], over=over, pairs=pairs,
                 px_max=round(worst_px[0], 1), px_t=round(worst_px[1]/FPS, 3), px_part=worst_px[2], jumps30=jt)
        note = 'target rho_px <= 1.0 off impulse frames; over = part-frames above it'+(f'; camera.json STALE ({old}): re-export' if old else '')
        out.append(Result(2, 'screen', aid, v, (best[0] <= TARGET) and not old, note))
    v = jumps(S, m)
    v['pins_jumps30'] = int(sum(np.sum(d['px'] > JUMP_PX) for (a, p), d in m.items() if p != 'tool'))
    out.append(Result(2, 'screen jumps', 'all', v, INFO,
                      f'tool point, px a frame on the 1920x1080 film, same shot, on screen; window {WINDOW[0]:g}-{WINDOW[1]:g} s; current camera'
                      +(f' (STALE: {old})' if old else '')))
    if FROZEN.exists() and FROZEN.resolve() != Path(S.camera_path).resolve():
        frozen = json.loads(FROZEN.read_text())
        if frozen.get('frames') != doc.get('frames'):
            out.append(Result(2, 'screen jumps M0 camera', 'all', jumps(S, measure(S, Camera(frozen))), INFO,
                              f'as above, under the camera frozen at M0 ({FROZEN.relative_to(ROOT)})'))
    return out

RULERS = {2: screen}

if __name__ == '__main__':
    from players.core import Subject
    for asset in sys.argv[1:] or ['chamber', 'expanded']:
        for r in screen(Subject(asset)): print(asset, r)

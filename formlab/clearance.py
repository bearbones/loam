"""Space accounting for articulated rigs: capsule-vs-capsule clearance over a
sampled motion, and the parallelogram offset chooser.

Every moving part is abstracted to capsules (segment + radius) in WORLD space
per pose. Bars are one capsule pin-to-pin; ears and bosses are short capsules
along the pin axis; strings are capsules too. The ruler reports the minimum
signed gap between every pair of parts that is not joined at a shared pin,
over every sampled pose — a cheap, conservative pre-flight before the exact
BVH check in tools/check_form_clearance.py.
"""
import numpy as np

# Section dimensions shared with formlab.linkage (kept here so the space
# rulers import without SciPy, e.g. inside Blender's Python).
DEFAULT_SPEC = dict(width=.034, depth=.062, ear_r=.055, pin_r=.018, ear_t=.028, head_t=.03, boss_r=.05, web=.05)
def default_layers(spec=DEFAULT_SPEC):
    gap = spec['head_t']+.006
    outer = gap/2+spec['ear_t']+.006+spec['width']/2
    return dict(outer=outer, gap=gap, span=2*outer+spec['width']*.8+.004)

def segment_distance(p1, q1, p2, q2):
    """Vectorised minimum distance between segments p1q1 and p2q2 (Ericson 5.1.9).
    All inputs broadcast to (..., 3)."""
    d1 = q1-p1; d2 = q2-p2; r = p1-p2
    a = np.einsum('...i,...i', d1, d1); e = np.einsum('...i,...i', d2, d2); f = np.einsum('...i,...i', d2, r)
    c = np.einsum('...i,...i', d1, r); b = np.einsum('...i,...i', d1, d2)
    denom = a*e-b*b
    s = np.where(denom > 1e-14, np.clip((b*f-c*e)/np.where(denom > 1e-14, denom, 1), 0, 1), 0.0)
    t = (b*s+f)/np.where(e > 1e-14, e, 1)
    s = np.where(t < 0, np.clip(-c/np.where(a > 1e-14, a, 1), 0, 1), s)
    s = np.where(t > 1, np.clip((b-c)/np.where(a > 1e-14, a, 1), 0, 1), s)
    t = np.clip(t, 0, 1)
    c1 = p1+d1*s[..., None]; c2 = p2+d2*t[..., None]
    return np.linalg.norm(c1-c2, axis=-1)

def link_basis(a, b, pin_axis=(1, 0, 0)):
    """Orthonormal (x, y, z) per pose: y along the link, x the pin axis
    projected perpendicular to y, z = x × y. Same rule as the Godot poser."""
    y = b-a; y = y/np.linalg.norm(y, axis=-1, keepdims=True)
    x = np.broadcast_to(np.asarray(pin_axis, float), y.shape)-y*np.einsum('...i,...i', y, np.broadcast_to(pin_axis, y.shape))[..., None]
    x = x/np.linalg.norm(x, axis=-1, keepdims=True)
    return x, y, np.cross(x, y)

def arm_capsules(poses, o1, o2, layers, spec):
    """World capsules per pose for a parallelogram arm. Returns dict name ->
    (P, Q, r) arrays of shape (T,3),(T,3),scalar, plus the adjacency set
    (pairs that legitimately touch at a shared pin)."""
    root, elbow, wrist = poses['root'], poses['elbow'], poses['wrist']
    o1 = np.asarray(o1, float); o2 = np.asarray(o2, float); X = np.array([1., 0, 0])
    r_bar = max(spec['width'], spec['depth'])/2; r_bar2 = r_bar*.8; outer = layers['outer']
    caps = {
        'upper':  (root, elbow, r_bar),
        'lower':  (elbow, wrist, r_bar),
        'upper2': (root+o1+X*outer, elbow+o1+X*outer, r_bar2),
        'lower2': (elbow+o2-X*outer, wrist+o2-X*outer, r_bar2),
        'elbowhead_web1': (elbow, elbow+o1, spec['web']/2),
        'elbowhead_web2': (elbow, elbow+o2, spec['web']/2),
        'wristhead_web': (wrist, wrist+o2, spec['web']/2),
        'carriage_web': (root, root+o1, spec['web']/2),
        'tool': (poses['tip'], wrist, .03),
    }
    adjacent = {frozenset(p) for p in [
        ('upper', 'lower'), ('upper', 'elbowhead_web1'), ('upper', 'elbowhead_web2'), ('upper', 'carriage_web'),
        ('lower', 'elbowhead_web1'), ('lower', 'elbowhead_web2'), ('lower', 'wristhead_web'), ('lower', 'tool'),
        ('upper2', 'elbowhead_web1'), ('upper2', 'carriage_web'), ('upper2', 'elbowhead_web2'),
        ('lower2', 'elbowhead_web2'), ('lower2', 'wristhead_web'), ('lower2', 'elbowhead_web1'),
        ('elbowhead_web1', 'elbowhead_web2'), ('wristhead_web', 'tool'), ('upper', 'wristhead_web'),
        ('upper2', 'upper'), ('lower2', 'lower')]}
    return caps, adjacent

def pairwise_clearance(caps, adjacent=frozenset()):
    """Minimum gap (distance - radii) per non-adjacent pair, over all poses."""
    names = list(caps); out = {}
    for i, a in enumerate(names):
        for b in names[i+1:]:
            if frozenset((a, b)) in adjacent: continue
            P1, Q1, r1 = caps[a]; P2, Q2, r2 = caps[b]
            gap = segment_distance(P1, Q1, P2, Q2)-r1-r2
            k = int(np.argmin(gap)); out[(a, b)] = (float(gap[k]), k)
    return out

def bar_pair_separation(poses, o, which='upper'):
    """In-plane distance between a primary bar and its parallel partner:
    |o| sin(angle(o, link)). Zero means the pair has folded onto itself."""
    a, b = (poses['root'], poses['elbow']) if which == 'upper' else (poses['elbow'], poses['wrist'])
    d = b-a; d /= np.linalg.norm(d, axis=-1, keepdims=True)
    o = np.asarray(o, float)
    perp = o-d*(d@o)[:, None]
    return np.linalg.norm(perp, axis=-1)

def choose_offset(poses, which, magnitude, candidates=72):
    """Pick the in-plane direction (yz) for the parallel bar's offset that
    maximises the worst-case bar separation over the motion. Returns
    (offset, worst_separation, all candidates)."""
    best = None; table = []
    for k in range(candidates):
        ang = 2*np.pi*k/candidates
        o = np.array([0, magnitude*np.cos(ang), magnitude*np.sin(ang)])
        worst = float(bar_pair_separation(poses, o, which).min())
        table.append((ang, worst))
        if best is None or worst > best[1]: best = (o, worst)
    return best[0], best[1], table

def report(rig, aid, o1, o2, layers, spec, strings=None, string_r=.002, poses=None):
    poses = rig.poses(aid) if poses is None else poses
    caps, adjacent = arm_capsules(poses, o1, o2, layers, spec)
    gaps = pairwise_clearance(caps, adjacent)
    worst = min(gaps.items(), key=lambda kv: kv[1][0])
    result = dict(arm=aid, samples=len(poses['t']),
                  upper_pair_separation_m=float(bar_pair_separation(poses, o1, 'upper').min()),
                  lower_pair_separation_m=float(bar_pair_separation(poses, o2, 'lower').min()),
                  worst_pair=list(worst[0]), worst_gap_m=worst[1][0], worst_time_s=float(poses['t'][worst[1][1]]),
                  pairs={'/'.join(k): v[0] for k, v in gaps.items()}, caps=caps)
    if strings:
        # Every bar vs every string of the mechanism. The tool legitimately
        # touches the played string, so the wrist head and bars are judged
        # against ALL strings — a bar through the played string is still a
        # bar through a string.
        sg = []
        for sid, s in strings.items():
            A = np.broadcast_to(np.asarray(s['a'], float), poses['root'].shape); B = np.broadcast_to(np.asarray(s['b'], float), poses['root'].shape)
            for name in ('upper', 'upper2', 'lower', 'lower2', 'wristhead_web', 'elbowhead_web1', 'elbowhead_web2'):
                P, Q, r = caps[name]
                g = segment_distance(P, Q, A, B)-r-string_r
                k = int(np.argmin(g)); sg.append((float(g[k]), sid, name, float(poses['t'][k])))
        sg.sort(); result['string_gap_m'] = sg[0][0]; result['string_worst'] = sg[0][1:]
    return result

def cross_arm_clearance(reports):
    """Minimum gap between parts of DIFFERENT arms (same time samples), for
    every pair of arms. Arms on one rail share x only when playing the same
    string, but neighbouring rails stack in z and their bars cross in plane."""
    out = {}
    names = list(reports)
    for i, a in enumerate(names):
        for b in names[i+1:]:
            ca = reports[a]['caps']; cb = reports[b]['caps']; best = (1e9, None, 0)
            for na, (P1, Q1, r1) in ca.items():
                for nb, (P2, Q2, r2) in cb.items():
                    g = segment_distance(P1, Q1, P2, Q2)-r1-r2
                    k = int(np.argmin(g))
                    if g[k] < best[0]: best = (float(g[k]), (na, nb), k)
            out[(a, b)] = best
    return out

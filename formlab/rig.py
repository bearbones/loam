"""Python mirror of harness/clockwork_motion.gd: the two-link planar IK and the
score-driven tool path, so offline geometry rulers (clearance, offset choice)
sample exactly the poses Godot will render. Kept numerically identical to the
GDScript: same clamps, same bend rule, same smoothstep."""
import json
import numpy as np

def _v(a): return np.asarray(a, float)

def smooth(u):
    u = min(max(u, 0.0), 1.0)
    return u*u*(3-2*u)

class Rig:
    def __init__(self, score, layout):
        self.score = score; self.geometry = layout
        self.acts = {}; self.plans = {}
        for m in score['instrument']['mechanisms']:
            for a in m['actuators']:
                self.acts[a['id']] = a; self.plans[a['id']] = []
        for e in score['events']:
            if e.get('actuator') in self.plans: self.plans[e['actuator']].append(e)
        for aid in self.plans: self.plans[aid].sort(key=lambda e: float(e['t_move']))

    @classmethod
    def load(cls, score_path, layout_path):
        return cls(json.loads(open(score_path).read()), json.loads(open(layout_path).read()))

    def contact(self, sid, pick=None):
        s = self.geometry['strings'][sid]
        u = .5 if s['struck'] else float(s['pick'] if pick is None else pick)
        return _v(s['a'])*(1-u)+_v(s['b'])*u

    def clearance(self, aid):
        return _v([0, .22, 0]) if self.geometry['strings'][self.acts[aid]['home']]['struck'] else _v([0, 0, -.22])

    def tip_at(self, aid, t):
        lift = self.clearance(aid); act = self.acts[aid]
        rest = self.contact(act['home'])+lift
        for e in self.plans[aid]:
            tm = float(e['t_move'])
            if t < tm: return rest
            hit = float(e['t']); ids = e['strings']
            first = self.contact(ids[0], e.get('pick')); last = self.contact(ids[-1], e.get('pick'))
            spread = float(e.get('spread_s', 0)); end = hit+spread*(len(ids)-1)
            if t < hit:
                approach = hit-float(act['approach_s'])
                if approach > tm+1e-6 and t < approach:
                    return rest+(first+lift-rest)*smooth((t-tm)/(approach-tm))
                start = max(tm, approach)
                origin = first+lift if approach > tm+1e-6 else rest
                u = min(max((t-start)/max(hit-start, 1e-6), 0), 1)
                return origin+(first-origin)*smooth(u)+lift*.45*np.sin(np.pi*u)
            if t <= end:
                if len(ids) == 1 or spread <= 0: return first
                index = min((t-hit)/spread, len(ids)-1); k = min(int(index), len(ids)-2)
                a = self.contact(ids[k], e.get('pick')); b = self.contact(ids[k+1], e.get('pick'))
                return a+(b-a)*(index-k)
            if t < float(e['t_free']):
                return last+lift*smooth((t-end)/max(float(e['t_free'])-end, 1e-6))
            rest = last+lift
        return rest

    @staticmethod
    def wrist_offset(cfg):
        """Where the wrist pin sits relative to the tool's contact point. Older
        manifests (no field) keep the original 0.15 m straight above."""
        return _v(cfg.get('wrist_offset', [0, .15, 0]))

    @staticmethod
    def bend_hint(cfg):
        """Elbow side. 'up' (original) bulges the elbow up/forward — fine for a
        mallet over a horizontal bar, but a pick arm reaching forward from a
        rail behind the strings would push its elbow THROUGH the string plane.
        'back' always puts the elbow on the far side from the strings: hanging
        down-back like a seated harpist's when reaching below the shoulder,
        rising up-back when reaching above it."""
        return _v([0, 0, -1]) if cfg.get('bend', 'up') == 'back' else _v([0, 1, 0])

    def pose(self, aid, t):
        cfg = self.geometry['arms'][aid]; tip = self.tip_at(aid, t)
        root = _v([tip[0], cfg['root_y'], cfg['root_z']])
        wrist = tip+self.wrist_offset(cfg)
        delta = wrist-root; distance = np.linalg.norm(delta)
        l1 = float(cfg['l1']); l2 = float(cfg['l2'])
        d = min(max(distance, abs(l1-l2)+1e-5), l1+l2-1e-5)
        direction = delta/distance
        along = (l1*l1-l2*l2+d*d)/(2*d)
        hint = self.bend_hint(cfg); bend = hint-direction*(direction@hint)
        if bend@bend < 1e-5: bend = _v([0, 0, -1])
        bend /= np.linalg.norm(bend)
        elbow = root+direction*along+bend*np.sqrt(max(0, l1*l1-along*along))
        return dict(root=root, elbow=elbow, wrist=wrist, tip=tip,
                    reachable=abs(l1-l2) <= distance <= l1+l2)

    def sample_times(self, hz=120):
        total = float(self.score['total_s'])
        times = set(np.arange(-hz, int(total*hz)+1)/hz)
        for e in self.score['events']:
            for k in range(len(e['strings'])): times.add(float(e['t'])+k*float(e.get('spread_s', 0)))
        return np.array(sorted(times))

    def poses(self, aid, times=None):
        """Arrays root/elbow/wrist/tip of shape (T, 3) over the sampled times."""
        times = self.sample_times() if times is None else times
        P = [self.pose(aid, t) for t in times]
        return dict(t=times, **{k: np.array([p[k] for p in P]) for k in ('root', 'elbow', 'wrist', 'tip')})

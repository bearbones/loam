"""Python mirror of harness/clockwork_motion.gd: the two-link planar IK and the
score-driven tool path, so offline geometry rulers (clearance, offset choice)
sample exactly the poses Godot will render. Kept numerically identical to the
GDScript: same clamps, same bend rule, same profiles and schedules."""
import json
import numpy as np

def _v(a): return np.asarray(a, float)

def smooth(u):
    u = min(max(u, 0.0), 1.0)
    return u*u*(3-2*u)

# Two motion vocabularies (docs/motion-design.md); the constants and every
# profile mirror ClockworkMotion. A mallet arm is a stepped machine (ratchet
# clicks along the rack, a cocked drop, the assembly shuddering after the blow);
# a pick or rake arm is a servo (S-curve slews, no overshoot, nothing rings).
PITCH = 2*np.pi*.12/16
CLICK_S = .09; CLICK_MIN_S = .04; CLICK_MOVE = .4; OVERSHOOT = .10; RING_HZ = 14.0; RING_TAU = .09
SLEW_S = .4; SCURVE_RAMP = .3
COCK = .5; COCK_AT = .4
RECOIL = dict(x=[.004, 11.0, .14], z=[.0025, 17.0, .10], bounce=[.06, 8.0, .16]); RECOIL_GATE = .08
PAD = .01
# The blow shakes the ASSEMBLY, not only the arm: [amplitude, Hz, decay s] each,
# driven from the recoil bus (Rig._bus). The stand and the gantry are fixed
# forms as far as the rulers are concerned; the RAIL sag moves the carriage and
# so every capsule of the arm, which is why it is mirrored here.
STAND_THUMP = [.0015, 9.0, .12]   # the instrument's stand, vertically (m)
RAIL_SAG = [.001, 12.0, .15]      # the rail's first bending mode, at mid-span (m)
MAST_SWAY = [.0003, 6.0, .30]     # the gantry swaying about its plinths (rad)
BLOW_DROP_REF = .33               # a full blow: 0.22 m of lift risen COCK again
SHUDDER_GAIN = 1.0                # ...all three together: the one dial to tune by eye
SHUDDER_TAIL = 1.0                # a ring is spent this long after its blow
RAIL_OVER = .26                   # the guide bars run this far past the reach window (formlab.gantry)

def quintic(u):
    u = min(max(u, 0.0), 1.0)
    return u*u*u*(10-15*u+6*u*u)

def _ramp(w): return w*w*w-w*w*w*w*.5

def scurve(u):
    u = min(max(u, 0.0), 1.0); r = SCURVE_RAMP
    if u < r: s = r*_ramp(u/r)
    elif u <= 1-r: s = r*.5+(u-r)
    else: s = (1-r)-r*_ramp((1-u)/r)
    return s/(1-r)

def teeth(dx): return max(1, int(np.floor(abs(dx)/PITCH+.5)))

def clicks(dx, T): return min(teeth(dx), max(1, int(np.floor(T/CLICK_MIN_S))))

def ratchet(u, n, T, over):
    u = min(max(u, 0.0), 1.0)
    k = min(int(np.floor(u*n)), n-1); w = u*n-k
    if w < CLICK_MOVE: p = quintic(w/CLICK_MOVE)*(1+over)
    else:
        tr = (w-CLICK_MOVE)*T/n; fade = 1.0-smooth((w-.7)/.3)
        p = 1+over*np.exp(-tr/RING_TAU)*np.cos(2*np.pi*RING_HZ*tr)*fade
    return (k+p)/n

def travel(a, b, u, T, clicky):
    if not clicky: return a+(b-a)*scurve(u)
    p = a+(b-a)*quintic(u); n = clicks(b[0]-a[0], T)
    over = OVERSHOOT*min(1.0, PITCH*n/max(abs(b[0]-a[0]), 1e-6))
    p[0] = a[0]+(b[0]-a[0])*ratchet(u, n, T, over)
    return p

def strike(origin, first, lift, u, hammer):
    if not hammer: return origin+(first-origin)*quintic(u)+lift*.45*np.sin(np.pi*u)
    if u < COCK_AT: h = 1+COCK*smooth(u/COCK_AT)
    else:
        v = (u-COCK_AT)/(1-COCK_AT); h = (1+COCK)*(1-v*v)
    return origin+(first+lift-origin)*quintic(u)+lift*(h-1)

def _ring(p, tau): return p[0]*np.exp(-tau/p[2])*np.sin(2*np.pi*p[1]*tau)

class Rig:
    def __init__(self, score, layout):
        self.score = score; self.geometry = layout
        self.acts = {}; self.plans = {}; self.mech_of = {}
        for m in score['instrument']['mechanisms']:
            for a in m['actuators']:
                self.acts[a['id']] = a; self.plans[a['id']] = []; self.mech_of[a['id']] = m['id']
        for e in score['events']:
            if e.get('actuator') in self.plans: self.plans[e['actuator']].append(e)
        for aid in self.plans: self.plans[aid].sort(key=lambda e: float(e['t_move']))
        self._schedules()

    @classmethod
    def load(cls, score_path, layout_path):
        return cls(json.loads(open(score_path).read()), json.loads(open(layout_path).read()))

    def contact(self, sid, pick=None):
        s = self.geometry['strings'][sid]
        u = .5 if s['struck'] else float(s['pick'] if pick is None else pick)
        return _v(s['a'])*(1-u)+_v(s['b'])*u

    def clearance(self, aid):
        return _v([0, .22, 0]) if self.geometry['strings'][self.acts[aid]['home']]['struck'] else _v([0, 0, -.22])

    def stepped(self, aid): return self.acts[aid]['kind'] in ('mallet', 'hammer')

    def _windows(self, aid):
        lift = self.clearance(aid); act = self.acts[aid]; clicky = self.stepped(aid)
        rest = self.contact(act['home'])+lift; free_prev = -np.inf; out = []
        for e in self.plans[aid]:
            tm = float(e['t_move']); hit = float(e['t']); ids = e['strings']
            first = self.contact(ids[0], e.get('pick')); last = self.contact(ids[-1], e.get('pick'))
            spread = float(e.get('spread_s', 0)); approach = hit-float(act['approach_s'])
            want = teeth(first[0]-rest[0])*CLICK_S if clicky else SLEW_S
            g0 = max(free_prev, min(tm, approach-want))
            xs = [rest[0]]+[self.contact(sid, e.get('pick'))[0] for sid in ids]
            out.append(dict(event=e, rest=rest, first=first, last=last, spread=spread, tm=tm, g0=g0, go=g0, approach=approach,
                            hit=hit, end=hit+spread*(len(ids)-1), t_free=float(e['t_free']), lo=min(xs), hi=max(xs), moving=False))
            rest = last+lift; free_prev = float(e['t_free'])
        return out

    def _schedules(self):
        """Each event's timing as the path uses it. Repositioning starts as
        soon as the arm is free and the move wants (`g0`), never later than the
        score's t_move: a machine moves, then waits. The score planner only
        promised the mechanism's arm clearance from t_move on, so an earlier
        start is checked here against the siblings under the planner's own
        occupancy model — an arm owns the whole x interval it crosses while it
        may be moving (from its own g0, since it may start early too) and
        hovers over its last contact after — and pushed later until the
        interval it wants is clear."""
        win = {aid: self._windows(aid) for aid in self.plans}
        mechs = self.geometry.get('mechanisms', {})
        for aid in self.plans:
            need = float(mechs.get(self.mech_of[aid], {}).get('arm_clearance_m', 0.0))
            for s in win[aid]:
                go = s['g0']
                if need > 0.0:
                    for other in self.plans:
                        if other == aid or self.mech_of[other] != self.mech_of[aid]: continue
                        home = self.contact(self.acts[other]['home'])[0]
                        segments = [(-np.inf, win[other][0]['g0'] if win[other] else np.inf, home, home)]
                        for i, o in enumerate(win[other]):
                            until = win[other][i+1]['g0'] if i+1 < len(win[other]) else np.inf
                            segments.append((o['g0'], o['end'], o['lo'], o['hi']))
                            segments.append((o['end'], until, o['last'][0], o['last'][0]))
                        for t0, t1, lo, hi in segments:
                            if t0 >= s['tm'] or t1 <= go: continue
                            if max(s['lo']-hi, lo-s['hi'])-PAD < need: go = max(go, min(t1, s['tm']))
                s['go'] = go; s['moving'] = s['approach'] > go+1e-6
        self.sched = win
        self._bus()

    def _bus(self):
        """The recoil bus: one entry a blow, shared by every rigid-body shudder
        so the stand, the rail and the gantry answer the same hits the arm's own
        recoil does. A blow records where it landed along the rail and how hard
        (the score's amplitude times the cocked drop's height, 1.0 for a
        full-amplitude mallet) and the time its arm's NEXT strike begins, which
        gates its ring to nothing. Mirrors ClockworkMotion._bus."""
        self.blows_by_arm = {}; self.blows_by_mech = {}
        for aid in self.plans:
            if not self.stepped(aid): continue
            scale = self.clearance(aid)[1]*(1+COCK)/BLOW_DROP_REF; mid = self.mech_of[aid]
            sched = self.sched[aid]
            self.blows_by_arm[aid] = [dict(t=float(s['hit']), aid=aid, mid=mid, x=float(s['first'][0]),
                                           energy=float(s['event'].get('amp', 1.0))*scale,
                                           gate_end=float(sched[i+1]['approach']) if i+1 < len(sched) else np.inf)
                                      for i, s in enumerate(sched)]
            self.blows_by_mech.setdefault(mid, []).extend(self.blows_by_arm[aid])
        for mid in self.blows_by_mech: self.blows_by_mech[mid].sort(key=lambda b: b['t'])

    @staticmethod
    def _blow_gate(b, t):
        """A blow's ring is gated exactly as `recoil` is: full until RECOIL_GATE
        before its arm's next strike begins, nothing after."""
        return 1.0-smooth((t-(b['gate_end']-RECOIL_GATE))/RECOIL_GATE)

    def _shudder(self, blows, t, p, shape):
        """One bus's rings summed at t: a damped sinusoid a blow, weighted by the
        blow's energy and by `shape` (a mode shape; 1.0 for a rigid body) and
        negative-going first, because a blow pushes down."""
        total = 0.0
        for b in reversed(blows):
            tau = t-b['t']
            if tau < 0.0: continue
            if tau > SHUDDER_TAIL: break
            total += -_ring(p, tau)*b['energy']*shape(b)*self._blow_gate(b, t)
        return total*SHUDDER_GAIN

    def rail_span(self, aid):
        """The rail's guide bars run RAIL_OVER past the reach window into their heads."""
        lo, hi = self.geometry['arms'][aid]['reach_x']
        return float(lo)-RAIL_OVER, float(hi)+RAIL_OVER

    def stand_thump(self, mid, t):
        """The instrument's stand answers every blow on it with a short vertical thump."""
        if mid not in self.blows_by_mech: return 0.0
        return self._shudder(self.blows_by_mech[mid], t, STAND_THUMP, lambda b: 1.0)

    def rail_sag(self, aid, t, x):
        """The rail's vertical deflection at rail position x: a steel bar pinned
        in its two heads, rung in its first bending mode (a half sine over the
        span) by a blow whose own position sets how much of that mode it excites."""
        if aid not in self.blows_by_arm: return 0.0
        lo, hi = self.rail_span(aid); L = max(hi-lo, .001)
        here = np.sin(np.pi*min(max((x-lo)/L, 0.0), 1.0))
        return self._shudder(self.blows_by_arm[aid], t, RAIL_SAG,
                             lambda b: here*np.sin(np.pi*min(max((b['x']-lo)/L, 0.0), 1.0)))

    def mast_sway(self, aid, t):
        """The gantry sways about its plinths after a blow: a tilt across the rail."""
        if aid not in self.blows_by_arm: return 0.0
        return self._shudder(self.blows_by_arm[aid], t, MAST_SWAY, lambda b: 1.0)

    def schedule(self, aid): return self.sched[aid]

    def recoil(self, aid, t):
        """The assembly's shudder after a mallet blow: zero at the blow, rung
        out and gated to nothing by the time the next strike begins."""
        if not self.stepped(aid): return np.zeros(3)
        hit = -np.inf; gate_end = np.inf
        for s in self.sched[aid]:
            if s['hit'] <= t: hit = s['hit']
            else:
                gate_end = s['approach']; break
        if hit == -np.inf: return np.zeros(3)
        tau = t-hit; gate = 1.0-smooth((t-(gate_end-RECOIL_GATE))/RECOIL_GATE)
        lift = self.clearance(aid)
        return _v([_ring(RECOIL['x'], tau), lift[1]*abs(_ring(RECOIL['bounce'], tau)), _ring(RECOIL['z'], tau)])*gate

    def tip_at(self, aid, t): return self.path_at(aid, t)+self.recoil(aid, t)

    def path_at(self, aid, t):
        """The scored path alone: rest, travel, strike, sweep, release, rest."""
        lift = self.clearance(aid); clicky = self.stepped(aid)
        rest = self.contact(self.acts[aid]['home'])+lift
        for s in self.sched[aid]:
            if t < s['go']: return rest
            first = s['first']; hit = s['hit']; approach = s['approach']; e = s['event']; ids = e['strings']
            if t < hit:
                if s['moving'] and t < approach:
                    return travel(rest, first+lift, (t-s['go'])/(approach-s['go']), approach-s['go'], clicky)
                start = approach if s['moving'] else max(s['tm'], approach)
                origin = first+lift if s['moving'] else rest
                u = min(max((t-start)/max(hit-start, 1e-6), 0), 1)
                return strike(origin, first, lift, u, clicky)
            if t <= s['end']:
                if len(ids) == 1 or s['spread'] <= 0: return first
                index = min((t-hit)/s['spread'], len(ids)-1); k = min(int(index), len(ids)-2)
                a = self.contact(ids[k], e.get('pick')); b = self.contact(ids[k+1], e.get('pick'))
                return a+(b-a)*(index-k)
            if t < s['t_free']:
                return s['last']+lift*quintic((t-s['end'])/max(s['t_free']-s['end'], 1e-6))
            rest = s['last']+lift
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
        # The carriage rides the rail, so it follows the rail's sag at its own x:
        # the links and the pawl move with the bar. The tip is the scored path
        # and its own recoil, untouched — every contact stays exact.
        root = _v([tip[0], cfg['root_y']+self.rail_sag(aid, t, tip[0]), cfg['root_z']])
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

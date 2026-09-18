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
#
# What a travel COSTS lives in loam/motion_timing.py, because the score planner
# decides its schedule from the same numbers (docs/plans/planner-uses-the-motion).
# It is loaded by PATH rather than imported: `import loam` would pull the synth
# package in, and this module must stay numpy-only so Blender can run it.
import importlib.util as _ilu
_mt_spec = _ilu.spec_from_file_location(
    'loam_motion_timing',
    __import__('pathlib').Path(__file__).resolve().parents[1]/'loam'/'motion_timing.py')
motion_timing = _ilu.module_from_spec(_mt_spec); _mt_spec.loader.exec_module(motion_timing)
PITCH = motion_timing.PITCH
CLICK_S = motion_timing.CLICK_S; CLICK_MIN_S = motion_timing.CLICK_MIN_S
SLEW_S = motion_timing.SLEW_S
CLICK_TEETH_MAX = motion_timing.CLICK_TEETH_MAX; SERVO_V_MAX = motion_timing.SERVO_V_MAX
WORLD_SCALE = motion_timing.WORLD_SCALE
CLICK_MOVE = .4; OVERSHOOT = .10; RING_HZ = 14.0; RING_TAU = .09
SCURVE_RAMP = .3
COCK = .5; COCK_AT = .4
RECOIL = dict(x=[.004, 11.0, .14], z=[.0025, 17.0, .10], bounce=[.06, 8.0, .16]); RECOIL_GATE = .08
PAD = .01
# A HINGED HAMMER (`kind == 'hammer'`, the expanded asset's block arm): the arm
# positions and dips a little, and a head hinged on a pin at the shank's end
# does the rest of the blow. The head lies back on a felt-faced check at rest,
# swings a touch further, falls through its arc, strikes, and the check catches
# the rebound. `arm_share` of the contact's clearance is the arm's dip; the flip
# supplies the remainder, and THAT is what sets the rest angle — the head can
# raise its felt face by head_l*(1 - cos(theta)), so the rise it must cover can
# never exceed 2*head_l. The angle runs 0 at the blow (felt on the bar) and
# positive lying back.
HAMMER = dict(head_l=.12, head_r=.045, arm_share=.30, cock=.02, check=[.10, 12.5, .045])
# `cock` is small because the check is what it presses into: at rest the
# head's tail lies on a felt-faced stop, and the cock sinks it a couple of
# millimetres further in before the head flies. The ARM still cocks its own
# COCK (a stepped arm's vocabulary); the head's back-swing is the felt's.
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

def cocked(u, c):
    """The cocked drop's height profile: 1 at the start, lifted to 1+c at
    COCK_AT, then falling as 1-v^2 to exactly 0 at the blow. Used for the lift
    of a stepped arm's tip and, scaled by its rest angle, for a hinged
    hammer's flip — one profile, so the two stay in phase."""
    u = min(max(u, 0.0), 1.0)
    if u < COCK_AT: return 1+c*smooth(u/COCK_AT)
    v = (u-COCK_AT)/(1-COCK_AT)
    return (1+c)*(1-v*v)

def strike(origin, first, lift, u, hammer):
    if not hammer: return origin+(first-origin)*quintic(u)+lift*.45*np.sin(np.pi*u)
    return origin+(first+lift-origin)*quintic(u)+lift*(cocked(u, COCK)-1)

def head_offset(theta, sign, head_l=HAMMER['head_l']):
    """Where a hinged head's felt face sits relative to the tool frame's
    origin, given the flip angle. The hinge is head_l above the origin and the
    face swings on it, so the face rises head_l*(1-cos) and moves head_l*sin
    toward the arm's own rail (`sign`). Zero at theta = 0: the blow is exact."""
    return _v([0.0, head_l*(1-np.cos(theta)), head_l*np.sin(theta)*sign])

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

    def hammer(self, aid): return self.acts[aid]['kind'] == 'hammer'

    def hover(self, aid):
        """What the TOOL FRAME's origin clears the contact by. For a rigid tool
        that is the contact's own clearance; a hinged hammer's arm hovers only
        `arm_share` of it, because the head lying back on its check holds the
        felt face the rest of the way up."""
        lift = self.clearance(aid)
        return lift*HAMMER['arm_share'] if self.hammer(aid) else lift

    def rest_angle(self, aid):
        """The flip angle at which the head's felt face clears by the whole
        lift while the arm hovers at `hover`: head_l*(1-cos) = the remainder."""
        if not self.hammer(aid): return 0.0
        rise = float(np.linalg.norm(self.clearance(aid)-self.hover(aid)))
        return float(np.arccos(np.clip(1.0-rise/HAMMER['head_l'], -1.0, 1.0)))

    def flip_sign(self, aid):
        """Which way the head swings back: toward its own rail, never across
        the instrument. Derived from the geometry, so both implementations
        agree without carrying it in the manifest."""
        cfg = self.geometry['arms'][aid]
        return 1.0 if float(cfg['root_z']) >= self.contact(self.acts[aid]['home'])[2] else -1.0

    def head_angle(self, aid, t):
        """The hinged head's flip angle at t: `rest_angle` lying back on its
        check, cocked a touch further over the strike, exactly 0 at the blow,
        then the rebound the check catches, and back to rest. Mirrors
        ClockworkMotion.head_angle."""
        if not self.hammer(aid): return 0.0
        rest = self.rest_angle(aid); c = HAMMER['cock']; chk = HAMMER['check']
        for s in self.sched[aid]:
            if t < s['go']: return rest
            if t < s['hit']:
                # travelling with the head laid back; the flip is the strike itself
                if s['moving'] and t < s['approach']: return rest
                start = s['approach'] if s['moving'] else max(s['tm'], s['approach'])
                u = min(max((t-start)/max(s['hit']-start, 1e-6), 0.0), 1.0)
                return rest*cocked(u, c)
            if t <= s['end']: return 0.0
            if t < s['t_free']:
                # the head bounces off the bar and the check takes it: |damped
                # sine| so the felt never passes through the string it just hit,
                # fading into the lay-back as the arm releases.
                tau = t-s['end']; w = quintic((t-s['end'])/max(s['t_free']-s['end'], 1e-6))
                bounce = chk[0]*abs(np.exp(-tau/chk[2])*np.sin(2*np.pi*chk[1]*tau))
                return rest*w+bounce*(1-w)
        return rest

    def head_pose(self, aid, t):
        """(angle, felt-face offset from the tool frame's origin) at t."""
        theta = self.head_angle(aid, t)
        return theta, head_offset(theta, self.flip_sign(aid)) if self.hammer(aid) else np.zeros(3)

    def _segments(self, aid, win):
        """One arm's whole occupancy of the rail as (t0, t1, lo, hi) spans.
        Three phases a contact, because the interval an arm CROSSED is not
        where it stands: it owns everything between where it left and where
        it lands until it arrives, then only the strings it is playing, then
        the one it hovers over. Mirrors loam.score._Solver's model exactly —
        that is the point of the plan it is checking."""
        home = self.contact(self.acts[aid]['home'])[0]
        segs = [(-np.inf, win[0]['go'] if win else np.inf, home, home)]
        for i, o in enumerate(win):
            until = win[i+1]['go'] if i+1 < len(win) else np.inf
            segs.append((o['go'], o['approach'], o['mlo'], o['mhi']))
            segs.append((o['approach'], o['end'], o['plo'], o['phi']))
            segs.append((o['end'], until, o['last'][0], o['last'][0]))
        return segs

    def _windows(self, aid):
        lift = self.hover(aid); act = self.acts[aid]
        rest = self.contact(act['home'])+lift; free_prev = -np.inf; out = []
        for e in self.plans[aid]:
            tm = float(e['t_move']); hit = float(e['t']); ids = e['strings']
            first = self.contact(ids[0], e.get('pick')); last = self.contact(ids[-1], e.get('pick'))
            spread = float(e.get('spread_s', 0)); approach = hit-float(act['approach_s'])
            # `want` is what this move would take unhurried, by the same
            # function the planner charged it with (loam.motion_timing) but
            # over the distance the rendered arm really crosses. The planner
            # already gave it everything it could, so the start is the
            # score's; `want` is kept for the rulers to compare against.
            want = motion_timing.travel_s(act['kind'], first[0]-rest[0])
            g0 = max(free_prev, tm)
            xs = [rest[0]]+[self.contact(sid, e.get('pick'))[0] for sid in ids]
            ps = [self.contact(sid, e.get('pick'))[0] for sid in ids]
            out.append(dict(event=e, rest=rest, first=first, last=last, spread=spread, tm=tm, g0=g0, go=g0, approach=approach,
                            hit=hit, end=hit+spread*(len(ids)-1), t_free=float(e['t_free']), lo=min(xs), hi=max(xs), want=want,
                            mlo=min(rest[0], first[0]), mhi=max(rest[0], first[0]), plo=min(ps), phi=max(ps), moving=False))
            rest = last+lift; free_prev = float(e['t_free'])
        return out

    def _schedules(self):
        """Each event's timing as the path uses it. Repositioning starts as
        soon as the arm is free and the move wants: a machine moves, then
        waits. That instant is the score's own `t_move` now — the planner
        charges each reposition what the vocabulary costs (loam.motion_timing)
        and hands over the start it checked, so there is nothing left here to
        second-guess. The sweep below is the assertion that it is so: the same
        three-phase occupancy loam.score._Solver planned under, and every start
        it has to push counts in `self.pushed` for tools/test_motion.py to
        insist on none."""
        win = {aid: self._windows(aid) for aid in self.plans}
        mechs = self.geometry.get('mechanisms', {})
        self.pushed = []
        for aid in self.plans:
            need = float(mechs.get(self.mech_of[aid], {}).get('arm_clearance_m', 0.0))
            for s in win[aid]:
                go = s['g0']
                if need > 0.0:
                    for other in self.plans:
                        if other == aid or self.mech_of[other] != self.mech_of[aid]: continue
                        for t0, t1, lo, hi in self._segments(other, win[other]):
                            if t0 >= s['approach'] or t1 <= go: continue
                            if max(s['mlo']-hi, lo-s['mhi'])-PAD < need: go = max(go, min(t1, s['approach']))
                if go > s['g0']+1e-9: self.pushed.append((aid, s['g0'], go))
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
        # A hinged hammer recoils in its HEAD and its check, not in the whole
        # arm (Rig.head_angle): the arm holds the contact while the head bounces.
        if self.hammer(aid): return np.zeros(3)
        hit = -np.inf; gate_end = np.inf
        for s in self.sched[aid]:
            if s['hit'] <= t: hit = s['hit']
            else:
                gate_end = s['approach']; break
        if hit == -np.inf: return np.zeros(3)
        tau = t-hit; gate = 1.0-smooth((t-(gate_end-RECOIL_GATE))/RECOIL_GATE)
        lift = self.hover(aid)
        return _v([_ring(RECOIL['x'], tau), lift[1]*abs(_ring(RECOIL['bounce'], tau)), _ring(RECOIL['z'], tau)])*gate

    def tip_at(self, aid, t): return self.path_at(aid, t)+self.recoil(aid, t)

    def path_at(self, aid, t):
        """The scored path alone: rest, travel, strike, sweep, release, rest."""
        lift = self.hover(aid); clicky = self.stepped(aid)
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
        # A hinged hammer's felt face is not the tool frame's origin: it hangs
        # on the hinge head_l above it and swings. `tip` stays the tool frame
        # (the shank, the fork and the check ride it); `felt` is the contact.
        theta, off = self.head_pose(aid, t)
        return dict(root=root, elbow=elbow, wrist=wrist, tip=tip, head=theta, felt=tip+off,
                    reachable=abs(l1-l2) <= distance <= l1+l2)

    def sample_times(self, hz=120):
        total = float(self.score['total_s'])
        times = set(np.arange(-hz, int(total*hz)+1)/hz)
        for e in self.score['events']:
            for k in range(len(e['strings'])): times.add(float(e['t'])+k*float(e.get('spread_s', 0)))
        return np.array(sorted(times))

    def poses(self, aid, times=None):
        """Arrays root/elbow/wrist/tip/felt of shape (T, 3) over the sampled
        times, plus `head`, the hinged head's flip angle (zero for rigid tools).

        Every value is an array over `times` and nothing else: gantry._caps
        subsamples this dict wholesale with `v[::step]`, so a scalar flag in
        here ("is this a hammer?") is a crash. Ask `hammer(aid)` for that, or
        read it off the angles — a rigid tool's `head` is all zeros."""
        times = self.sample_times() if times is None else times
        P = [self.pose(aid, t) for t in times]
        return dict(t=times, head=np.array([p['head'] for p in P]),
                    **{k: np.array([p[k] for p in P]) for k in ('root', 'elbow', 'wrist', 'tip', 'felt')})

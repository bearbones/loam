"""The rig's motion — the one implementation: the two-link planar IK, the
score-driven tool path in its two vocabularies, the recoil bus. Offline
geometry rulers (clearance, offset choice) sample it directly, and the harness
plays a bake of it (formlab/bake.py, `loam-motion/1`), so what they check is
what Godot renders; tools/test_bake.py holds the bake to this."""
import json
import numpy as np

def _v(a): return np.asarray(a, float)

def smooth(u):
    u = min(max(u, 0.0), 1.0)
    return u*u*(3-2*u)

# Two motion vocabularies (docs/motion-design.md); the constants and every
# profile are here, except a mallet's stroke, which is formlab/stroke.py's.
# A stepped arm moves tooth by tooth along a rack and shudders after the blow:
# a mallet steps or freewheels contact to contact under a head riding its
# rebound (PLAYERS M1), the hinged hammer clicks a ratchet and cocks its drop;
# a pick or rake arm is a servo (S-curve slews, no overshoot, nothing rings).
#
# What a travel COSTS lives in loam/motion_timing.py, because the score planner
# decides its schedule from the same numbers (docs/plans/planner-uses-the-motion).
# It is loaded by PATH rather than imported: `import loam` would pull the synth
# package in, and this module must stay numpy-only so Blender can run it.
# formlab/stroke.py (the mallet's stroke, PLAYERS M1) loads it and shares the
# one instance through sys.modules, so tuning `rig.motion_timing.X` reaches the
# stroke's planning too. Imported both ways: as formlab.rig, and bare (Blender
# puts formlab/ on sys.path).
try:
    from . import stroke
except ImportError:
    import stroke
motion_timing = stroke.motion_timing
PITCH = motion_timing.PITCH
CLICK_S = motion_timing.CLICK_S; CLICK_MIN_S = motion_timing.CLICK_MIN_S
SLEW_S = motion_timing.SLEW_S
CLICK_TEETH_MAX = motion_timing.CLICK_TEETH_MAX; SERVO_V_MAX = motion_timing.SERVO_V_MAX
WORLD_SCALE = motion_timing.WORLD_SCALE
CLICK_MOVE = .4
# The detent ring's constants live in formlab/stroke.py (the mallet's stroke
# vocabulary, PLAYERS M1); re-exported here for the harness mirror and the cache.
OVERSHOOT = stroke.OVERSHOOT; RING_HZ = stroke.RING_HZ; RING_TAU = stroke.RING_TAU
SCURVE_RAMP = .3
COCK = .5; COCK_AT = .4
RECOIL = dict(x=[.004, 11.0, .14], z=[.0025, 17.0, .10], bounce=[.06, 8.0, .16]); RECOIL_GATE = .08
# (a mallet keeps the x and z rings; its |sine| 'bounce' is retired, PLAYERS M1:
# the head's rebound is the scored float now. 'bounce' stays importable.)
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

# ---- joint angles: ruler 16's conventions, mirrored exactly ------------------------
# tools/players/r_motion.py `ik` / `joint_series` / `_span_points` and
# r_machine._joint_spans define what a joint angle and a joint's span ARE for
# the rulers; the homing sweep (Rig.path_at) moves those angles, so it uses the
# same definitions (tools/test_stroke.py holds the two copies equal).
def ik(cfg, tips):
    """Rig.pose's IK (root above the tip on the rail, no sag) for tool points
    `tips` (N,3) -> root, elbow, wrist, reachable. Mirrors r_motion.ik."""
    tips = np.asarray(tips, float)
    root = np.c_[tips[:, 0], np.full(len(tips), cfg['root_y']), np.full(len(tips), cfg['root_z'])]
    wrist = tips+Rig.wrist_offset(cfg)
    delta = wrist-root; dist = np.linalg.norm(delta, axis=-1); l1 = float(cfg['l1']); l2 = float(cfg['l2'])
    reach = (abs(l1-l2) <= dist) & (dist <= l1+l2)
    d = np.clip(dist, abs(l1-l2)+1e-5, l1+l2-1e-5); dirn = delta/dist[:, None]
    along = (l1*l1-l2*l2+d*d)/(2*d)
    hint = Rig.bend_hint(cfg); bend = hint-dirn*(dirn@hint)[:, None]
    bn = np.linalg.norm(bend, axis=-1)
    bend = np.where(bn[:, None] < np.sqrt(1e-5), np.array([0, 0, -1.0]), bend/np.maximum(bn, 1e-12)[:, None])
    elbow = root+dirn*along[:, None]+bend*np.sqrt(np.maximum(0, l1*l1-along*along))[:, None]
    return root, elbow, wrist, reach

def joint_series(root, elbow, wrist):
    """Joint angles along a pose series (rad): shoulder = the upper link's
    angle atan2(y, z), forearm likewise, rel = forearm - shoulder, elbow = the
    interior angle (pi straight). Mirrors r_motion.joint_series."""
    u = elbow-root; f = wrist-elbow
    sh = np.unwrap(np.arctan2(u[:, 1], u[:, 2])); fa = np.unwrap(np.arctan2(f[:, 1], f[:, 2]))
    cosel = -(u*f).sum(1)/(np.linalg.norm(u, axis=-1)*np.linalg.norm(f, axis=-1))
    return dict(x=root[:, 0], shoulder=sh, forearm=fa, rel=fa-sh, elbow=np.arccos(np.clip(cosel, -1, 1)))

def _wrap(a): return float(np.angle(np.exp(1j*a)))


_cfg_cache_n = 64     # per-cfg caches keep this many cfgs (the rail search tries thousands)


def _bounded(cache):
    """The cache with room for one more entry: the oldest cfg is dropped once
    it holds _cfg_cache_n (dicts keep insertion order)."""
    while len(cache) >= _cfg_cache_n: cache.pop(next(iter(cache)))
    return cache

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

    def mallet(self, aid):
        """A rigid mallet: its stroke is formlab/stroke.py's (PLAYERS M1). Every
        M1 branch keys on this, never on stepped(): the hinged hammer keeps the
        older vocabulary until M5."""
        return self.acts[aid]['kind'] == 'mallet'

    def hover(self, aid):
        """What the TOOL FRAME's origin clears the contact by. For a rigid tool
        that is the contact's own clearance; a hinged hammer's arm hovers only
        `arm_share` of it, because the head lying back on its check holds the
        felt face the rest of the way up. A mallet rests on its stroke's arc
        (formlab.stroke: the head at height h sits sigma*Z(h) toward its own
        root side), so its hover leans by Z(clearance)."""
        lift = self.clearance(aid)
        if self.hammer(aid): return lift*HAMMER['arm_share']
        if self.mallet(aid):
            rho, k = stroke.arc(self.acts[aid]['kind'])
            return _v([lift[0], lift[1], lift[2]+self._sigma(aid)*float(stroke.arc_Z(lift[1], rho, k))])
        return lift

    def _sigma(self, aid):
        """A mallet's root side (flip_sign) for its stroke. The Rig is built
        before the rail search has placed any root (layout_search.plan_arms),
        so until the cfg names a root_z this is the side every struck rail
        candidate lies on (layout_search.candidates: root_z below the strings'
        z, so -1). Only the stroke's z map depends on it (the timing, the
        carriage, the knots and the clicks do not), and stroke() re-plans
        when the cfg's side differs from the plan's."""
        if 'root_z' not in self.geometry['arms'].get(aid, {}): return -1.0
        return self.flip_sign(aid)

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
        then the rebound the check catches, and back to rest."""
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

    def homes(self, aid, x_joint=None):
        """The arm's homing sweeps, as the score's `home` cues name them
        (loam.score._Solver.home): (t0, t1, lo, hi, legs), the legs
        (t0, t1, what, a, b) from motion_timing.home_legs over the contacts'
        world x, so they take the times the planner charged ('x' legs tooth by
        tooth at step_period, then the 'elbow' and 'shoulder' sweeps at a still
        x: `x_joint`, or home when None)."""
        out = []
        for c in self.score.get('cues', []):
            if c.get('kind') != 'home' or c.get('actuator') != aid: continue
            xh, xlo, xhi = (float(self.contact(sid)[0]) for sid in c['path'][:3])
            t0 = float(c['t'])
            legs = [(t0+a, t0+b, what, xa, xb) for a, b, what, xa, xb in motion_timing.home_legs(xh, xlo, xhi, x_joint)]
            # the planner charged the sweep over axis x WORLD_SCALE, the rig draws it over the contacts'
            # world x: the drawn sweep must end where the occupancy the planner cleared ends
            if 't_end' in c and abs(legs[-1][1]-float(c['t_end'])) > 1e-9:
                raise ValueError(f'{aid}: the homing sweep drawn over world x ends at {legs[-1][1]:.9f} s, '
                                 f'the planner cleared it to {float(c["t_end"]):.9f} s')
            out.append((legs[0][0], legs[-1][1], min(xlo, xhi), max(xlo, xhi), legs))
        return out

    def _segments(self, aid, win):
        """One arm's whole occupancy of the rail as (t0, t1, lo, hi) spans.
        Three phases a contact, because the interval an arm CROSSED is not
        where it stands: it owns everything between where it left and where
        it lands until it ARRIVES (`arrive`: the wind-up before the contact,
        or the contact itself for a carriage that travels contact to
        contact), then only the strings it is playing, then the one it hovers
        over; a homing sweep owns the whole reach it sweeps. Mirrors
        loam.score._Solver's model exactly — that is the point of the plan it
        is checking."""
        home = self.contact(self.acts[aid]['home'])[0]
        segs = []; t = -np.inf
        for h0, h1, lo, hi, _ in self.homes(aid):
            segs += [(t, h0, home, home), (h0, h1, lo, hi)]; t = h1
        segs.append((t, win[0]['go'] if win else np.inf, home, home))
        for i, o in enumerate(win):
            until = win[i+1]['go'] if i+1 < len(win) else np.inf
            segs.append((o['go'], o['arrive'], o['mlo'], o['mhi']))
            segs.append((o['arrive'], o['end'], o['plo'], o['phi']))
            segs.append((o['end'], until, o['last'][0], o['last'][0]))
        return segs

    def _windows(self, aid):
        lift = self.hover(aid); act = self.acts[aid]
        rest = self.contact(act['home'])+lift; free_prev = -np.inf; out = []
        lead = motion_timing.arrive_lead(act['kind'], float(act['approach_s']))
        for e in self.plans[aid]:
            tm = float(e['t_move']); hit = float(e['t']); ids = e['strings']
            first = self.contact(ids[0], e.get('pick')); last = self.contact(ids[-1], e.get('pick'))
            spread = float(e.get('spread_s', 0)); approach = hit-float(act['approach_s'])
            # where the carriage stands on the contact's x: the planner's
            # t_arrive (motion_timing.arrive_lead), which the occupancy uses
            arrive = hit-lead
            head_free = float(e.get('t_head_free', e['t_free']))
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
                            arrive=arrive, head_free=head_free, hit=hit, end=hit+spread*(len(ids)-1), t_free=float(e['t_free']), lo=min(xs), hi=max(xs), want=want,
                            mlo=min(rest[0], first[0]), mhi=max(rest[0], first[0]), plo=min(ps), phi=max(ps), moving=False))
            # the carriage is free at t_head_free: t_free, or the contact
            # itself for a head that rides its rebound into the next travel
            rest = last+lift; free_prev = head_free
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
                            if t0 >= s['arrive'] or t1 <= go: continue
                            if max(s['mlo']-hi, lo-s['mhi'])-PAD < need: go = max(go, min(t1, s['arrive']))
                if go > s['g0']+1e-9: self.pushed.append((aid, s['g0'], go))
                s['go'] = go; s['moving'] = s['arrive'] > go+1e-6
        self.sched = win
        # the mallets' strokes (formlab/stroke.py), planned once from the
        # schedule: each entry gains its head's free instant and its stroke's apex
        self._strokes = {}; self._hj = {}; self._spans = {}; self._recoil_at = {}
        for aid in self.plans:
            st = self.stroke(aid)
            if st is None: continue
            notes = {n.event: n for n in st.notes}
            for i, s in enumerate(self.sched[aid]):
                n = notes[int(s['event'].get('i', i))]
                s['t_head_free'] = s['head_free']; s['t_apex'] = float(n.t_apex)
        self._bus()

    # ---- the mallet's stroke (PLAYERS M1; formlab/stroke.py) ----------------------
    def _a_norm(self, e):
        """a' exactly as tools/players/core.Subject.a_norm: the amp normalised
        over every score event of its voice; None when the voice has one amp."""
        rng = getattr(self, '_amp_range', None)
        if rng is None:
            rng = self._amp_range = stroke.amp_ranges(self.score['events'])
        return stroke.a_prime(e, rng)

    def joint_site(self, aid):
        """Where the arm's homing joint sweeps happen (the M1 build spec, 4):
        at home (None) unless home is within stroke.HOME_NEAR in x of another
        mechanism's reach window, then whichever end of its own x path is
        farther from it."""
        cues = [c for c in self.score.get('cues', []) if c.get('kind') == 'home' and c.get('actuator') == aid]
        if not cues: return None
        xh, xlo, xhi = (float(self.contact(sid)[0]) for sid in cues[0]['path'][:3])
        arms = self.geometry['arms']; mine = self.mech_of[aid]
        others = [tuple(float(v) for v in c['reach_x']) for a, c in arms.items()
                  if 'reach_x' in c and self.mech_of.get(a, c.get('mid')) != mine]
        return stroke.joint_site(xh, xlo, xhi, others)

    def _cfg_key(self, aid):
        cfg = self.geometry['arms'][aid]
        return (float(cfg['root_y']), float(cfg['root_z']), float(cfg['l1']), float(cfg['l2']),
                tuple(float(v) for v in self.wrist_offset(cfg)), cfg.get('bend', 'up'), self.flip_sign(aid))

    def span_points(self, aid):
        """Ruler 16's span points: each reach element at 0.2-0.8 (struck) or
        0.05-0.95 (plucked) of its length, at the contact and at the hover.
        Mirrors r_motion._span_points."""
        geo = self.geometry['strings']; lift = self.hover(aid); pts = []
        for sid in self.acts[aid].get('reach', [self.acts[aid]['home']]):
            g = geo[sid]; a = _v(g['a']); b = _v(g['b'])
            us = np.linspace(.2, .8, 13) if g['struck'] else np.linspace(.05, .95, 19)
            for u in us:
                q = a*(1-u)+b*u; pts.append(q); pts.append(q+lift)
        return np.array(pts)

    def joint_spans(self, aid):
        """(shoulder, elbow) spans in radians by IK over the span points, for
        the arm's cfg as it is now (r_machine._joint_spans' rule), or None."""
        key = (aid,)+self._cfg_key(aid)
        if key not in self._spans:
            cfg = self.geometry['arms'][aid]
            root, elbow, wrist, reach = ik(cfg, self.span_points(aid))
            ok = reach & (np.abs(np.linalg.norm(elbow-root, axis=-1)-float(cfg['l1'])) < 1e-3) \
                       & (np.abs(np.linalg.norm(wrist-elbow, axis=-1)-float(cfg['l2'])) < 1e-3)
            out = None
            if ok.any():
                q = joint_series(root[ok], elbow[ok], wrist[ok]); sh = q['shoulder']
                ref = np.arctan2(np.sin(sh).mean(), np.cos(sh).mean()); sh = ref+np.angle(np.exp(1j*(sh-ref)))
                out = (float(np.ptp(sh)), float(np.ptp(q['elbow'])))
            _bounded(self._spans)[key] = out
        return self._spans[key]

    def _arm_input(self, aid):
        home = self.contact(self.acts[aid]['home'])
        hits = [stroke.HitIn(t=float(s['hit']), point=tuple(float(v) for v in s['first']), a=self._a_norm(s['event']),
                             go=float(s['go']), event=int(s['event'].get('i', i)), amp=float(s['event'].get('amp', 1.0)))
                for i, s in enumerate(self.sched[aid])]
        hm = self.homes(aid, self.joint_site(aid))
        # joint_spans=None: the plan holds the head at the hover through each
        # joint window and only sketches the legs (st.joints, HOME_SPAN_GUESS);
        # the Rig turns the real ones from the cfg at pose time (_home_joints),
        # so the plan never depends on a cfg (the Rig exists before the rail
        # search has placed any root).
        return stroke.ArmIn(hits=hits, home=tuple(float(v) for v in home), hover=float(self.clearance(aid)[1]),
                            sigma=self._sigma(aid), homing=hm[0][4] if hm else [], joint_spans=None,
                            kind=self.acts[aid]['kind'], name=aid)

    def stroke(self, aid):
        """A mallet arm's planned stroke (formlab.stroke.ArmStroke: the two
        channels, knots, per-note records with t_apex, T_down, v_in, e, a_f, h,
        regime and travel windows, the travels), or None for any other arm. The
        plan reads only the score and the contacts (and which side the root is
        on), so it is made once; what depends on the arm's cfg (the homing
        joint sweeps) is computed from the cfg at pose time."""
        if not self.mallet(aid) or not self.sched.get(aid): return None
        sig = self._sigma(aid); c = self._strokes.get(aid)
        if c is None or c[0] != sig:
            c = (sig, stroke.plan(self._arm_input(aid), jerk=False)); self._strokes[aid] = c
        return c[1]

    def _home_joints(self, aid):
        """The homing joint sweeps for the arm's cfg AS IT IS NOW (the rail
        search mutates geometry['arms'][aid] per candidate): the legs
        (stroke.joint_legs over the cue's windows, amplitudes from this cfg's
        spans) and, per window, the home pose's joint angles in ruler 16's
        conventions. Cached per cfg tuple."""
        st = self.stroke(aid)
        if st is None: return None
        key = (aid,)+self._cfg_key(aid)
        if key in self._hj: return self._hj[key]
        wins = [(float(a), float(b), what) for a, b, what, _, _ in st.arm.homing if what != 'x']
        out = None
        if wins:
            cfg = self.geometry['arms'][aid]; l1 = float(cfg['l1']); l2 = float(cfg['l2'])
            sp = self.joint_spans(aid)
            spans = dict(shoulder=sp[0], elbow=sp[1]) if sp else dict(stroke.HOME_SPAN_GUESS)
            frames = {}
            for t0, t1, what in sorted(wins):
                base = _v(st.p(t0)); root, elbow, wrist, _ = ik(cfg, base[None])
                u = (elbow-root)[0]; f = (wrist-elbow)[0]
                sh0 = float(np.arctan2(u[1], u[2])); fa0 = float(np.arctan2(f[1], f[2]))
                e0 = float(joint_series(root, elbow, wrist)['elbow'][0])
                frames[(t0, t1, what)] = dict(base=base, root=root[0], sh0=sh0, fa0=fa0, e0=e0, sgn=1.0 if _wrap(fa0-sh0) >= 0 else -1.0,
                                              l1=l1, l2=l2, wo=self.wrist_offset(cfg), r_sh=float(np.linalg.norm(wrist[0]-root[0])))
            # The planner charges each joint a fixed share of the sweep (it has
            # no arm geometry: motion_timing.HOME_JOINT_S); here, where the cfg
            # is known, back-to-back joint windows at one x share their time in
            # proportion to each joint's TOOL path (radius x total angle: the
            # forearm l2 about the elbow pin, |wrist - root| about the root), so
            # every leg of the sweep peaks at the same tool speed. The window's
            # ends, and so what the planner charged, are unchanged.
            def tool_len(key):
                fr = frames[key]; q = stroke.joint_points(key[2], spans[key[2]])
                return (fr['l2'] if key[2] == 'elbow' else fr['r_sh'])*sum(abs(b-a) for a, b in zip(q, q[1:]))
            runs = []
            for key in sorted(frames):
                if runs and abs(runs[-1][-1][1]-key[0]) < 1e-12 and abs(frames[runs[-1][-1]]['base'][0]-frames[key]['base'][0]) < 1e-12:
                    runs[-1].append(key)
                else: runs.append([key])
            legs = []
            for run in runs:
                T0, T1 = run[0][0], run[-1][1]; L = [tool_len(k) for k in run]; tot = sum(L) or 1.0; t = T0
                for k, (key, l) in enumerate(zip(run, L)):
                    tb = T1 if k == len(run)-1 else t+(T1-T0)*l/tot
                    for g in stroke.joint_legs(key[2], t, tb, spans[key[2]]):
                        legs.append(dict(g, joint=key[2], frame=frames[key], span=spans[key[2]], span_assumed=sp is None))
                    t = tb
            out = dict(t0=legs[0]['t0'], t1=legs[-1]['t1'], legs=legs, starts=np.array([g['t0'] for g in legs]))
        _bounded(self._hj)[key] = out
        return out

    @staticmethod
    def _fk(frame, joint, q):
        """The tool point with one joint turned q rad from the home pose: the
        elbow's interior angle (the forearm turns about the elbow pin), or the
        shoulder (the whole arm turns rigidly about the root pin)."""
        sh = frame['sh0']; fa = frame['fa0']
        if joint == 'elbow': fa = sh+frame['sgn']*(np.pi-(frame['e0']+q))
        else: sh = sh+q; fa = fa+q
        elbow = frame['root']+frame['l1']*_v([0.0, np.sin(sh), np.cos(sh)])
        return elbow+frame['l2']*_v([0.0, np.sin(fa), np.cos(fa)])-frame['wo']

    def _home_q(self, hj, t):
        """(leg, q) of the homing joint sweep at t, or None outside it."""
        if not hj['t0'] < t < hj['t1']: return None
        g = hj['legs'][int(np.searchsorted(hj['starts'], t, 'right'))-1]
        u = (t-g['t0'])/(g['t1']-g['t0'])
        return g, g['q0']+(g['q1']-g['q0'])*float(stroke.s345(u))

    def carriage_x(self, aid, t):
        """Where the carriage stands on the rail: a mallet's scored x plus the
        detent ring of its stepped landings (no recoil ring); for every other
        arm, the tip's x as the IK puts the root there."""
        st = self.stroke(aid)
        if st is not None: return float(st.carriage_x(t))
        return float(self.tip_at(aid, t)[0])

    def pawl_ride(self, aid, t):
        """In [0, 1]: a mallet pawl riding the rack (a smoothstep of the tooth
        rate |x'|/PITCH over stroke.PAWL_RIDE_BAND); 0 at rest, at contacts and
        for every other arm."""
        st = self.stroke(aid)
        return float(st.pawl_ride(t)) if st is not None else 0.0

    def _bus(self):
        """The recoil bus: one entry a blow, shared by every rigid-body shudder
        so the stand, the rail and the gantry answer the same hits the arm's own
        recoil does. A blow records where it landed along the rail and how hard
        (a mallet's: the score's amplitude, with the stroke's v_in and e; the
        hinged hammer's: the amplitude times its cocked drop's height, 1.0 for
        a full blow) and the time its arm's NEXT strike begins (a mallet's next
        t_apex, the hammer's next approach), which gates its ring to nothing."""
        self.blows_by_arm = {}; self.blows_by_mech = {}
        for aid in self.plans:
            if not self.stepped(aid): continue
            st = self.stroke(aid)
            if st is not None:
                # a mallet: the energy is the score's amplitude (the cocked drop
                # is retired), each blow carries the stroke's v_in and e, and its
                # ring is gated by the NEXT stroke's start, its apex
                mid = self.mech_of[aid]; N = sorted(st.notes, key=lambda n: n.t)
                self.blows_by_arm[aid] = [dict(t=float(n.t), aid=aid, mid=mid, x=float(n.x), energy=float(n.amp),
                                               gate_end=float(N[i+1].t_apex) if i+1 < len(N) else np.inf,
                                               v_in=float(n.v_in), e=float(n.e))
                                          for i, n in enumerate(N)]
                self._recoil_at[aid] = (np.array([b['t'] for b in self.blows_by_arm[aid]]),
                                        [b['gate_end'] for b in self.blows_by_arm[aid]])
                self.blows_by_mech.setdefault(mid, []).extend(self.blows_by_arm[aid])
                continue
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

    def click_times(self, aid):
        """When a stepped arm clicks. A mallet: (t, 1.0) a tooth (formlab.stroke
        ArmStroke.click_times) — a freewheel's where x crosses mid-tooth, a stepped
        or homing travel's at each landing. The hinged hammer: one (t, teeth) a
        ratchet click, at the moment the click's move lands on its detent and the
        pawl drops (go + (k+CLICK_MOVE)*T/n for the k-th of n clicks in a travel of
        T seconds — the same division `ratchet` makes), with the teeth that click
        spanned. A servo arm never clicks."""
        if not self.stepped(aid): return []
        if self.mallet(aid):
            # a mallet clicks a tooth, (t, 1.0) each: a freewheel's where x
            # crosses mid-tooth, a stepped (or homing) travel's at each landing
            st = self.stroke(aid)
            return st.click_times() if st is not None else []
        out = []
        for s in self.sched[aid]:
            if not s['moving']: continue
            T = s['approach']-s['go']; dx = s['first'][0]-s['rest'][0]
            n = clicks(dx, T); spanned = teeth(dx)
            out.extend((float(s['go']+(k+CLICK_MOVE)*T/n), spanned/n) for k in range(n))
        return out

    def recoil(self, aid, t):
        """The assembly's shudder after a mallet blow: zero at the blow, rung
        out and gated to nothing by the time the next strike begins."""
        if not self.stepped(aid): return np.zeros(3)
        # A hinged hammer recoils in its HEAD and its check, not in the whole
        # arm (Rig.head_angle): the arm holds the contact while the head bounces.
        if self.hammer(aid): return np.zeros(3)
        if self.mallet(aid):
            # the x and z rings only (the head's rebound is the scored float
            # now), gated by the next stroke's apex; exactly zero at each contact
            ts, gates = self._recoil_at.get(aid, (np.zeros(0), []))
            i = int(np.searchsorted(ts, t, 'right'))-1
            if i < 0: return np.zeros(3)
            tau = t-ts[i]; gate = 1.0-smooth((t-(gates[i]-RECOIL_GATE))/RECOIL_GATE)
            return _v([_ring(RECOIL['x'], tau), 0.0, _ring(RECOIL['z'], tau)])*gate
        hit = -np.inf; gate_end = np.inf
        for s in self.sched[aid]:
            if s['hit'] <= t: hit = s['hit']
            else:
                gate_end = s['approach']; break
        if hit == -np.inf: return np.zeros(3)
        tau = t-hit; gate = 1.0-smooth((t-(gate_end-RECOIL_GATE))/RECOIL_GATE)
        lift = self.hover(aid)
        return _v([_ring(RECOIL['x'], tau), lift[1]*abs(_ring(RECOIL['bounce'], tau)), _ring(RECOIL['z'], tau)])*gate

    def tip_at(self, aid, t):
        """What renders: the scored path plus its rings (a mallet's carriage
        also carries its detent ring along x)."""
        p = self.path_at(aid, t)+self.recoil(aid, t)
        st = self.stroke(aid) if self.mallet(aid) else None
        if st is not None: p[0] += st.detent(t)
        return p

    def path_at(self, aid, t):
        """The scored path alone: rest, travel, strike, sweep, release, rest.
        A mallet's is its stroke's ring-free closed form (formlab/stroke.py),
        with the homing joint sweeps turned in joint space for the cfg as it is."""
        st = self.stroke(aid) if self.mallet(aid) else None
        if st is not None:
            hj = self._home_joints(aid)
            if hj is not None:
                gq = self._home_q(hj, t)
                if gq is not None and gq[1] != 0.0: return self._fk(gq[0]['frame'], gq[0]['joint'], gq[1])
            return _v(st.p(t))
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
        # and its own recoil, untouched — every contact stays exact. A mallet's
        # carriage stands at carriage_x: its scored x and detent ring, without
        # the tip's recoil ring.
        rx = self.carriage_x(aid, t) if self.mallet(aid) else tip[0]
        root = _v([rx, cfg['root_y']+self.rail_sag(aid, t, rx), cfg['root_z']])
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

    @staticmethod
    def _leg_jerk(g, radius, n=1025):
        """Peak |p'''| of a homing joint leg's tool point: a 3-4-5 in the joint
        angle phi, the point on a circle of `radius` about the turning pin, so
        |p'''| = radius*sqrt(9 phi'^2 phi''^2 + (phi''' - phi'^3)^2)."""
        T = g['t1']-g['t0']; D = g['q1']-g['q0']; u = np.linspace(0.0, 1.0, n)
        p1 = D*(30*u**2-60*u**3+30*u**4)/T; p2 = D*(60*u-180*u**2+120*u**3)/T**2; p3 = D*(60-360*u+360*u**2)/T**3
        return float(radius*np.sqrt(9*p1*p1*p2*p2+(p3-p1**3)**2).max())

    def declared(self, aid):
        """The arm's declared structure (formlab.segments.Declared). A mallet
        declares its own (PLAYERS M1): its stroke's segments on the 'head' and
        'carriage' channels with their extras, the knots ('contact' with the
        declared impulse, 'click' a tooth, 'detent' at each stepped landing,
        'smooth' at every other join), its rings, and the prep function. Every
        other arm keeps today's reading of its schedule (segments._today)."""
        try:
            from . import segments as SEG
        except ImportError:
            import segments as SEG
        st = self.stroke(aid)
        if st is None: return SEG._today(self, aid)
        stroke.declare_jerk(st)
        def ext(d): return {k: (list(v) if isinstance(v, (list, tuple, np.ndarray)) else v) for k, v in d.items()}
        segs = [SEG.Segment(g.t0, g.t1, g.law, g.tag, g.event, ext(g.extra))
                for g in st.head.segs+st.carriage.segs if not (g.channel == 'head' and g.tag == 'home')]
        hj = self._home_joints(aid)
        if hj is not None:
            # the homing joint legs for this cfg: the head holds the hover while
            # one joint turns (stroke.joint_legs), each leg a 3-4-5 in the angle
            for g in hj['legs']:
                f = g['frame']; r = f['l2'] if g['joint'] == 'elbow' else f['r_sh']
                segs.append(SEG.Segment(g['t0'], g['t1'], '3-4-5', 'home', -1, dict(
                    channel='head', joint=g['joint'], leg=g['leg'], q0=g['q0'], q1=g['q1'], span=g['span'],
                    span_assumed=g['span_assumed'], jerk=self._leg_jerk(g, r),
                    jerk_rad=60*abs(g['q1']-g['q0'])/(g['t1']-g['t0'])**3)))
        segs.sort(key=lambda g: (g.t0, g.extra['channel']))
        knots = [SEG.Knot(k.t, k.kind, None if k.dv is None else np.asarray(k.dv, float).copy(), k.event, ext(k.extra))
                 for k in st.knots if k.kind != 'smooth']
        imp = np.array(sorted(k.t for k in knots if k.kind in SEG.IMPULSES))
        joins = set()
        for ch in ('head', 'carriage'):
            cs = [g for g in segs if g.extra['channel'] == ch]
            joins.update(g.t0 for g in cs[1:])
        for t in sorted(joins):
            if imp.size and np.min(np.abs(imp-t)) <= 1e-9: continue
            knots.append(SEG.Knot(t, 'smooth'))
        knots.sort(key=lambda k: (k.t, k.kind))
        rings = [dict(name=f'recoil.{a}', channel='tip', amp=RECOIL[a][0], f=RECOIL[a][1], tau=RECOIL[a][2]) for a in ('x', 'z')]
        rings += [dict(name='stand_thump', channel='stand', amp=STAND_THUMP[0], f=STAND_THUMP[1], tau=STAND_THUMP[2]),
                  dict(name='rail_sag', channel='root', amp=RAIL_SAG[0], f=RAIL_SAG[1], tau=RAIL_SAG[2]),
                  dict(name='mast_sway', channel='mast', amp=MAST_SWAY[0], f=MAST_SWAY[1], tau=MAST_SWAY[2]),
                  dict(name='detent', channel='root.x', amp=OVERSHOOT*PITCH, f=RING_HZ, tau=RING_TAU, fade='3-4-5')]
        return SEG.Declared(segs, knots, rings, stroke.prep, native=True)

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

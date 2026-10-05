"""The rig's declared structure: what each arm's motion SAYS it is made of.

docs/goals/the-players.md ("Acceptance", "What the rig declares") measures
every gesture against structure the rig declares, never against shapes guessed
from samples:

    segments(rig, aid) -> [Segment(t0, t1, law, tag)]   the planned pieces
    knots(rig, aid)    -> [Knot(t, kind, dv)]           where pieces meet

A knot's `kind` is one of KNOT_KINDS: 'smooth' (the pieces must join in
position, velocity and acceleration), or a declared impulse — 'contact' (a
rebound, with its velocity change `dv` when the rig declares one; a mallet's
is (0, (1 + e) v_in, 0)), 'slip' (a string let go), 'detent' (a stepped
landing on the rack; dv 0 on a mallet's ring-free path, whose detent knot
carries its ring's `sign` and `fade` = (t_fade0, t_fade1) in `extra`) — or
'click' (the pawl passing a tooth) or 'place' (a digit set on its string). A
click that carries `extra['t_end']` is a path interval [t, t_end]: a mallet's
stepped or homing step from its start to its landing, and the hinged hammer's
ratchet click, whose interval today is [t, t + CLICK_MOVE*T/n]. A mallet's
freewheel click has no `t_end`: it is sound (`extra` k, n, regime, pawl
'drop'|'ride', travel), not a path impulse. A segment's `tag` is one of TAGS.

The rig of 6c326b5 (`loam-motion/1`) declared nothing, so `declared()` reads
an arm's vocabulary off the rig's own schedule (Rig.sched) — the boundaries
its path_at switches on, which is the rig's own account of its pieces
(`_today`). From PLAYERS M1 a mallet declares itself (`Rig.declared`, from
formlab/stroke.py: native=True, every segment's `extra`, the click and detent
knots, prep); every other arm is still read by `_today`. This module is NOT one of layout_search.GEOMETRY_SOURCES:
it moves nothing, so editing it must not replan the rails.
"""
from dataclasses import dataclass, field
import numpy as np
from formlab import rig as R

TAGS = ('travel', 'wind-up', 'stroke', 'rebound', 'float', 'release', 'place', 'stick', 'close',
        'raise', 'fall', 'slide', 'sweep', 'follow-through', 'ghost', 'home', 'hold', 'catch')
KNOT_KINDS = ('smooth', 'contact', 'slip', 'detent', 'click', 'place')
IMPULSES = ('contact', 'slip', 'detent')

@dataclass
class Segment:
    t0: float
    t1: float
    law: str          # timing law along the segment's path (LAWS when declared; today's names below)
    tag: str          # one of TAGS
    event: int = -1   # index of the score event it serves (-1: none)
    extra: dict = field(default_factory=dict)   # declared fields (a mallet's: channel, jerk, pin/axis, regime/travel/hurried, joint, hold, p0..a1)

@dataclass
class Knot:
    t: float
    kind: str                 # one of KNOT_KINDS
    dv: object = None         # declared velocity change (3-vector) at an impulse, or None if undeclared
    event: int = -1
    extra: dict = field(default_factory=dict)

@dataclass
class Declared:
    segments: list
    knots: list
    rings: list               # [dict(name, channel, amp, f, tau)] the declared ring terms
    prep: object = None       # callable h(a', ioi) -> prep height, or None (undeclared)
    native: bool = False      # True when the rig declared this itself

# The laws a rig that declares itself names (formlab/stroke.py LAWS, PLAYERS M1:
# the mallet), and the channels its segments ride: each channel covers
# (-inf, +inf) with no hole and no overlap.
LAWS = ('3-4-5', 'quintic hermite', 'ballistic', 'hold')
CHANNELS = ('head', 'carriage')
HOLD_KINDS = ('park', 'cocked')           # a mallet head 'hold' segment's extra['hold']
REGIMES = ('step', 'freewheel', 'home')   # a carriage travel's extra['regime'] (and a click's)

# Today's laws, named after the rig functions that implement them.
LAW_TODAY = dict(servo_travel='scurve', stepped_travel='ratchet', servo_strike='quintic+sine',
                 stepped_strike='quintic+cocked', sweep='linear', release='quintic', hold='hold')

def _rings_today(rig, aid):
    """The ring terms the rig of 6c326b5 applies, by name (rig.RECOIL, the
    shudder buses, the ratchet's detent ring, the hammer's check)."""
    out = []
    if rig.stepped(aid) and not rig.hammer(aid):
        for axis, p in R.RECOIL.items():
            out.append(dict(name=f'recoil.{axis}', channel='tip', amp=p[0], f=p[1], tau=p[2]))
    if rig.stepped(aid):
        out.append(dict(name='stand_thump', channel='stand', amp=R.STAND_THUMP[0], f=R.STAND_THUMP[1], tau=R.STAND_THUMP[2]))
        out.append(dict(name='rail_sag', channel='root', amp=R.RAIL_SAG[0], f=R.RAIL_SAG[1], tau=R.RAIL_SAG[2]))
        out.append(dict(name='mast_sway', channel='mast', amp=R.MAST_SWAY[0], f=R.MAST_SWAY[1], tau=R.MAST_SWAY[2]))
        out.append(dict(name='detent', channel='root.x', amp=R.OVERSHOOT*R.PITCH, f=R.RING_HZ, tau=R.RING_TAU))
    if rig.hammer(aid):
        chk = R.HAMMER['check']
        out.append(dict(name='check', channel='head', amp=chk[0], f=chk[1], tau=chk[2]))
    return out

def _today(rig, aid):
    """Read the 6c326b5 vocabulary's pieces off Rig.sched, boundary for
    boundary as Rig.path_at switches between them."""
    segs, knots = [], []
    stepped = rig.stepped(aid)
    struck = rig.geometry['strings'][rig.acts[aid]['home']]['struck']
    rest_from = -np.inf
    for i, s in enumerate(rig.sched[aid]):
        e = s['event']; ev = int(e.get('i', i)); ids = e['strings']
        go, approach, hit, end, free = float(s['go']), float(s['approach']), float(s['hit']), float(s['end']), float(s['t_free'])
        start = approach if s['moving'] else max(float(s['tm']), approach)
        if go > rest_from: segs.append(Segment(rest_from, go, 'hold', 'hold', ev))
        if s['moving']:
            segs.append(Segment(go, approach, LAW_TODAY['stepped_travel' if stepped else 'servo_travel'], 'travel', ev))
            knots.append(Knot(go, 'smooth', event=ev))
            if stepped:
                T = approach-go; n = R.clicks(s['first'][0]-s['rest'][0], T)
                for k in range(n):
                    t0 = go+k*T/n
                    knots.append(Knot(t0, 'click', event=ev, extra=dict(t_end=t0+R.CLICK_MOVE*T/n, k=k, n=n)))
                    knots.append(Knot(t0+R.CLICK_MOVE*T/n, 'detent', event=ev))
            knots.append(Knot(approach, 'smooth', event=ev))
            if start > approach: segs.append(Segment(approach, start, 'hold', 'hold', ev))
        elif start > go:
            segs.append(Segment(go, start, 'hold', 'hold', ev))
        segs.append(Segment(start, hit, LAW_TODAY['stepped_strike' if stepped else 'servo_strike'], 'stroke', ev))
        knots.append(Knot(start, 'smooth', event=ev))
        # A blow or a pluck meets its surface at `hit`: declared a contact, but
        # the 6c326b5 rig declares no velocity change for it (dv None). A sweep
        # does not collide with anything as it enters: that is a smooth knot.
        sweep = len(ids) > 1 and s['spread'] > 0
        knots.append(Knot(hit, 'smooth' if sweep and not struck else 'contact', event=ev))
        if end > hit:
            segs.append(Segment(hit, end, LAW_TODAY['sweep'], 'sweep', ev))
            for k in range(1, len(ids)-1): knots.append(Knot(hit+k*s['spread'], 'smooth', event=ev))
            knots.append(Knot(end, 'smooth', event=ev))
        if free > end:
            segs.append(Segment(end, free, LAW_TODAY['release'], 'release', ev))
            knots.append(Knot(free, 'smooth', event=ev))
        rest_from = free
    segs.append(Segment(rest_from, np.inf, 'hold', 'hold'))
    knots.sort(key=lambda k: k.t)
    return Declared(segs, knots, _rings_today(rig, aid), None, native=False)

def declared(rig, aid):
    """The arm's declared structure: Rig.declared (the mallet's own from M1;
    `_today` for every other arm), or today's vocabulary read off the schedule
    for a rig without one."""
    if hasattr(rig, 'declared'): return rig.declared(aid)
    return _today(rig, aid)

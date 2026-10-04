"""The score — loam remembers what it plays.

Until now a song computed an event time inline, mixed the chunk, and
forgot: `add_wrapped(buf, beat_t(bar, 2.5), stereo(v, pan))`. The
time, pitch and voice were consumed into the buffer. That was fine
for a loop that only had to SOUND right; a machine that has to be
SEEN playing the music needs the decisions, not just their sum.

Score sits between the composer and the canvas. `play` mixes exactly
as `canvas.add` would (byte-identical — e97's claim), also into a
per-mechanism stem, and records an event. `cue` records without
mixing. `export` writes score.json + stems (+ shapes, see fdstring)
— everything an engine needs to move the machine, from the thing
that decided every note.

The instrument model (Stage 2) is authored here in Python and
embedded in the export as the single source of truth for both
worlds: loam reads a mechanism's MATERIAL for timbre, the engine
reads its GEOMETRY for the machine. `pick` — where along the string
the arm lands, 0..0.5 — is the same number in both.

The playability solver: Animusic edited MIDI until their machine
could play it. Here the machine is a constraint the composer ASKS
before writing a note (`can_play`). Per actuator: busy until
`t0 + recover_s` after a contact, then travel the world distance to
the next string and wind up for `approach_s`:

    feasible  iff  travel available >= what the vocabulary needs

What a travel COSTS is not the planner's invention any more. It comes
from `loam.motion_timing`, the same module `formlab/rig.py` moves by
(and the harness plays back, baked): a stepped arm clicks along a
rack tooth by tooth, a servo slews. An arm that has the room takes the
unhurried time; one that does not is charged everything the score left
it and refused outright below `motion_timing.floor_s` — the plan and
the motion are now one model rather than two that disagreed by a
factor of twenty. `Actuator.travel_s` survives as a per-index floor
for a mechanism whose strings carry no usable geometry.

Least travel wins, ties to the earliest free. A string refuses a
re-strike inside `restrike_s` (the pick must clear it). Every event
exports its plan — actuator, t_move, t, t_free, from — which IS the
keyframe plan the engine interpolates. Note that "string" here is
the struck element of any mechanism: a marimba bar is a string with
kind="struck"; the solver does not care what rings.
"""

import json
import os
from dataclasses import dataclass, field, asdict

import numpy as np

from . import SR, hz, stereo, write_wav
from . import strings as _strings
from . import modal as _modal
from . import motion_timing as _mt

FORMAT = "loam-score/1"

# Synthesis hangs off the material so the timbre follows the machine.
# pluck: strings.pluck kwargs; strike: modal.strike table + t60.
MATERIALS = {
    "steel":    dict(synth="pluck", damp=0.18, t60=3.2, soft=0),
    "bronze":   dict(synth="pluck", damp=0.30, t60=4.0, soft=0),
    "nylon":    dict(synth="pluck", damp=0.50, t60=2.0, soft=1),
    "gut":      dict(synth="pluck", damp=0.60, t60=1.6, soft=2),
    "rosewood": dict(synth="strike", table="MARIMBA", t60=1.4,
                     bright=1.0),
    "padauk":   dict(synth="strike", table="XYLOPHONE", t60=0.9,
                     bright=1.3),
    "glass":    dict(synth="strike", table="GLASS", t60=3.0,
                     bright=0.8),
    "wood":     dict(synth="strike", table="WOOD", t60=0.25,
                     bright=1.0),
}


@dataclass
class StringDef:
    """One struck element. pos is mechanism-local [x, y, z]; length
    along the mechanism's axis is in the same units as span."""
    id: str
    midi: float
    pos: list = field(default_factory=lambda: [0.0, 0.0, 0.0])
    length: float = 1.0
    pick_default: float = 0.2


@dataclass
class Actuator:
    """An arm. reach = ids it can strike; home = id it rests over.
    Times in seconds: approach (wind-up before contact), recover (dead
    time after). `travel_s` is a per-string-index FLOOR, not the travel
    itself: what a reposition costs comes from the arm's motion
    vocabulary and the distance it has to cross (`loam.motion_timing`,
    via `_Solver.travel`). It is what a mechanism laid out with no
    usable spacing still charges."""
    id: str
    kind: str = "pick"          # pick | hammer | mallet | rake
    reach: list = field(default_factory=list)
    approach_s: float = 0.12
    recover_s: float = 0.06
    travel_s: float = 0.03
    home: str = ""


@dataclass
class Mechanism:
    id: str
    kind: str                   # plucked | struck | raked
    material: str
    strings: list = field(default_factory=list)
    actuators: list = field(default_factory=list)
    pos: list = field(default_factory=lambda: [0.0, 0.0, 0.0])
    axis: list = field(default_factory=lambda: [1.0, 0.0, 0.0])
    span: float = 1.0           # world extent along axis
    restrike_s: float = 0.05
    # Minimum distance along the axis between any two of this mechanism's
    # arms, at every moment (hovering, travelling, playing). An arm is a
    # real object with width across its pin axis; 0 keeps the historical
    # point-arm planning. Same units as pos/span.
    arm_clearance: float = 0.0
    fanned: bool = False        # pos already carries the neck fan (see fan())

    def axis_pos(self, sid: str) -> float:
        """A string's coordinate along the mechanism axis (pos units)."""
        ax = np.asarray(self.axis, float)
        return float(np.dot(self.string(sid).pos, ax) / max(np.linalg.norm(ax), 1e-12))

    def fan(self, width: float = 1.0, power: float = 1.0,
            rise=(0.0, 0.0), by: str = "length", smooth: int = 0) -> "Mechanism":
        """Re-space the strings along the axis the way a harp neck does.
        by="index": one scale degree per equal step, as real harps are
        strung (the neck's curve then comes from the lengths alone);
        by="length": log-spaced by string length (equal pitch ratios,
        equal steps). `power` < 1 compresses the treble end; the whole
        fan is `width` times the built span. `rise` = (foot at the bass
        end, foot at the treble end) lifts each string's origin across
        the fan — the diagonal soundboard of a triangular frame.
        `smooth` > 0 refits log(length) with a polynomial of that degree
        across the fan: a scale's uneven steps would otherwise put a
        kink at every string top, and a real neck is one fair curve the
        strings are cut to (a few percent of length; pitch is untouched).
        Everything downstream (planner clearance, layout, contacts)
        reads the result from pos, so the score stays the single truth."""
        n = len(self.strings)
        if smooth > 0 and n > smooth + 1:
            uu = np.linspace(0.0, 1.0, n)
            coef = np.polyfit(uu, np.log([s.length for s in self.strings]), smooth)
            for s, v in zip(self.strings, np.exp(np.polyval(coef, uu))):
                s.length = float(v)
        lengths = [s.length for s in self.strings]
        hi, lo = max(lengths), min(lengths)
        ax = np.asarray(self.axis, float)
        ax = ax / max(np.linalg.norm(ax), 1e-12)
        ext = max(float(np.dot(s.pos, ax)) for s in self.strings) \
            - min(float(np.dot(s.pos, ax)) for s in self.strings)
        for i, s in enumerate(self.strings):
            if by == "index":
                u = i / max(n - 1, 1)
            else:
                u = np.log(hi / s.length) / np.log(hi / lo) if hi > lo else 0.0
            u = float(u) ** power
            off = np.asarray(s.pos, float) - ax * float(np.dot(s.pos, ax))
            p = off + ax * ((u - 0.5) * ext * width)
            p[1] += rise[0] + (rise[1] - rise[0]) * u
            s.pos = [float(v) for v in p]
        self.fanned = True
        return self

    def index(self, sid: str) -> int:
        for i, s in enumerate(self.strings):
            if s.id == sid:
                return i
        raise KeyError(f"{self.id}: no string {sid}")

    def string(self, sid: str) -> StringDef:
        return self.strings[self.index(sid)]

    def actuator(self, aid: str) -> Actuator:
        for a in self.actuators:
            if a.id == aid:
                return a
        raise KeyError(f"{self.id}: no actuator {aid}")

    def pan_of(self, sid: str, width: float = 0.8) -> float:
        """Stereo position from geometry: the string's place along
        the axis, so the engine's left is the mix's left."""
        n = len(self.strings)
        if n < 2:
            return 0.0
        return width * (2.0 * self.index(sid) / (n - 1) - 1.0)

    @classmethod
    def build(cls, id: str, kind: str, material: str, midis,
            arms: int = 1, overlap: int = 0, span: float = 1.0,
            pos=None, axis=None, restrike_s: float = 0.05,
            arm_kind: str = "pick", approach_s: float = None,
            recover_s: float = 0.06, travel_s: float = 0.03,
            pick_default: float = 0.2, length_max: float = 0.6):
        """Lay out strings evenly along the axis, lengths ∝ 1/f
        (longest = length_max, the lowest string), and `arms`
        actuators with reach windows that overlap by `overlap`
        strings. Redundant arms are the scheduling slack: a dense
        passage needs a second arm to be free."""
        midis = list(midis)
        n = len(midis)
        # The wind-up is a property of the arm kind unless a score names
        # its own (they all do today); motion_timing holds the defaults
        # so the rig and the planner cannot drift apart on them.
        if approach_s is None:
            approach_s = _mt.approach_s(arm_kind)
        axis = list(axis or [1.0, 0.0, 0.0])
        f_lo = min(hz(m) for m in midis)
        strs = []
        for i, m in enumerate(midis):
            u = i / max(n - 1, 1)
            p = [(u - 0.5) * span * a for a in axis]
            strs.append(StringDef(id=f"{id}{i:02d}", midi=float(m),
                    pos=p, length=length_max * f_lo / hz(m),
                    pick_default=pick_default))
        acts = []
        if arms > 0:
            win = int(np.ceil((n + overlap * (arms - 1)) / arms))
            for k in range(arms):
                lo = max(0, k * (win - overlap))
                hi = min(n, lo + win)
                if k == arms - 1:
                    hi = n
                ids = [s.id for s in strs[lo:hi]]
                acts.append(Actuator(id=f"{id}_arm{k}", kind=arm_kind,
                        reach=ids, approach_s=approach_s,
                        recover_s=recover_s, travel_s=travel_s,
                        home=ids[len(ids) // 2]))
        return cls(id=id, kind=kind, material=material, strings=strs,
                actuators=acts, pos=list(pos or [0.0, 0.0, 0.0]),
                axis=axis, span=span, restrike_s=restrike_s)


@dataclass
class Instrument:
    name: str
    mechanisms: list = field(default_factory=list)

    def mech(self, mid: str) -> Mechanism:
        for m in self.mechanisms:
            if m.id == mid:
                return m
        raise KeyError(f"no mechanism {mid}")

    def to_dict(self) -> dict:
        return asdict(self)


class _Solver:
    """Per-mechanism actuator state for the playability rule."""

    def __init__(self, mech: Mechanism):
        self.mech = mech
        self.free_at = {a.id: -np.inf for a in mech.actuators}
        self.at = {a.id: a.home for a in mech.actuators}
        self.last_hit = {}
        self.last_t = -np.inf
        # Occupancy timeline per arm, one entry a contact:
        # (t_move, t_arrive, t_last, travel interval, contact interval,
        # where it comes to rest). An arm crossing the rail is charged
        # the whole interval between where it left and where it lands,
        # because the plan does not model the profile in between; once
        # it has ARRIVED it is charged only the strings it is playing,
        # and afterwards the one it hovers over. Three phases, not two:
        # the interval it crossed is not where it stands.
        self.moves = {a.id: [] for a in mech.actuators}

    def span_m(self, s_from: str, s_to: str) -> float:
        """World metres along the rail between two strings' contacts.
        The mechanism's axis coordinate is in score units and the build
        places the instrument at `motion_timing.WORLD_SCALE` times
        those, which is the scale the arm actually has to move at."""
        m = self.mech
        return abs(m.axis_pos(s_from) - m.axis_pos(s_to)) * _mt.WORLD_SCALE

    def travel(self, act: Actuator, s_from: str, s_to: str) -> float:
        """What an unhurried reposition costs this arm: its vocabulary's
        time over the world distance (clicks for a stepped arm, a slew
        for a servo), never below the per-index floor `act.travel_s`
        keeps for a mechanism whose strings share a coordinate."""
        if not s_from:
            return 0.0
        floor = abs(self.mech.index(s_from) - self.mech.index(s_to)) \
            * act.travel_s
        return max(_mt.travel_s(act.kind, self.span_m(s_from, s_to)), floor)

    def _range_at(self, aid: str, t: float):
        """Axis interval arm `aid` occupies at time t under the plan
        committed so far: the crossed interval while moving, else a
        point over the destination of its latest finished move (its
        home before any)."""
        hover = self.mech.axis_pos(self.mech.actuator(aid).home)
        latest = -np.inf
        for t0, t_arr, t1, mv, pl, dest in self.moves[aid]:
            if t0 <= t < t_arr:
                return mv
            if t_arr <= t <= t1:
                return pl
            if t1 < t and t1 > latest:
                latest, hover = t1, dest
        return hover, hover

    def _spans(self, act: Actuator, sids):
        """((lo, hi) crossed on the way, (lo, hi) played on arrival)."""
        m = self.mech
        xs = [m.axis_pos(s) for s in sids]
        played = (min(xs), max(xs))
        s_from = self.at[act.id]
        if not s_from:
            return played, played
        x0 = m.axis_pos(s_from)
        return (min(x0, xs[0]), max(x0, xs[0])), played

    def _separated(self, act: Actuator, t_move: float, t_arrive: float,
            t_last: float, sids) -> bool:
        """The candidate move keeps `arm_clearance` from every other arm
        of the mechanism for all time from t_move on, in the three
        phases `self.moves` records: the interval it crosses until it
        arrives, the strings it plays until t_last, then a point over
        sids[-1]. Ranges are piecewise constant in time, so testing
        every breakpoint plus the midpoints between them is exact.

        There is only the one model. `_feasible` charges a hurried arm
        from the moment it comes free, so t_move is the instant the
        carriage really starts and the rig has no earlier start to
        reconcile (`formlab.rig._schedules`, which now only logs if it
        ever has to push one later)."""
        w = float(self.mech.arm_clearance)
        if w <= 0.0:
            return True
        m = self.mech
        moving, played = self._spans(act, sids)
        rest = m.axis_pos(sids[-1])

        def mine(t):
            if t < t_arrive:
                return moving
            return played if t <= t_last else (rest, rest)
        for other in m.actuators:
            if other.id == act.id:
                continue
            times = {t_move, t_arrive, t_last, t_last + 1e-6}
            for t0, t_arr, t1, _, _, _ in self.moves[other.id]:
                for tb in (t0, t_arr, t1):
                    if tb >= t_move:
                        times.add(tb)
                    times.add(max(t_move, tb))
            ts = sorted(times)
            probes = list(ts) + [0.5 * (u + v) for u, v in zip(ts, ts[1:])] \
                + [ts[-1] + 1.0]
            for tp in probes:
                a_lo, a_hi = mine(tp)
                b_lo, b_hi = self._range_at(other.id, tp)
                if max(a_lo - b_hi, b_lo - a_hi) < w:
                    return False
        return True

    def _push(self, act: Actuator, t0: float, t_hi: float,
            t_arrive: float, t_last: float, sids) -> float:
        """The earliest start in [t0, t_hi] whose whole occupancy is clear
        of the siblings, or None if the arm cannot get across at all.

        A blocked arm waits and then moves in what is left rather than
        losing the note: that is what `formlab.rig._schedules` used to do
        after the fact, on a schedule the planner had not checked. It is
        done here now, where the plan is made, and the rig inherits the
        answer. Sibling ranges are piecewise constant in time, so a start
        that clears at all clears at t0 or at the instant one of them next
        changes."""
        # t_hi is always worth trying: leaving at the last possible moment
        # is the shortest crossing there is, so it is the start least
        # likely to sit in anyone's way.
        cands = {t0, t_hi}
        for other in self.mech.actuators:
            if other.id == act.id:
                continue
            for seg in self.moves[other.id]:
                for tb in (seg[0] + 1e-9, seg[1] + 1e-9):
                    if t0 < tb <= t_hi:
                        cands.add(tb)
        for start in sorted(cands):
            if self._separated(act, start, t_arrive, t_last, sids):
                return start
        return None

    def _feasible(self, a: Actuator, t: float, sids, spread_s: float):
        """(t_move, travel, t_last, dx) if arm `a` can take the contact
        under the busy rule and the clearance rule, else None.

        `dx` is the world distance the arm has to cross (what "least
        travel wins" is decided on) and `travel` what the score actually
        leaves for the crossing. An arm with room takes the whole
        unhurried want; one without is charged everything between the
        moment it comes free and the wind-up, and leaves at that moment.
        `t_move` is therefore the instant the carriage really starts, and
        `formlab.rig._windows` takes it as given rather than deriving a
        second, earlier one of its own.

        Below `motion_timing.floor_s` there is no plan at all: the
        carriage would have to cross the distance faster than the
        ratchet can click or the servo can run, so the contact is
        refused and the composer hears about it. Between the two, a
        sibling in the way costs time rather than the note — `_push`
        waits and crosses in what is left."""
        if any(s not in a.reach for s in sids):
            return None
        s_from = self.at[a.id]
        dx = self.span_m(s_from, sids[0]) if s_from else 0.0
        want = self.travel(a, s_from, sids[0])
        room = t - a.approach_s - self.free_at[a.id]
        if room < 0.0:
            return None
        tr = want if room >= want else room
        flr = _mt.floor_s(a.kind, dx) if s_from else 0.0
        if tr < flr - 1e-9:
            return None
        t_last = t + spread_s * (len(sids) - 1)
        t_move = self._push(a, t - a.approach_s - tr,
                t - a.approach_s - flr, t - a.approach_s, t_last, sids)
        if t_move is None:
            return None
        return t_move, t - a.approach_s - t_move, t_last, dx

    def plan(self, t: float, sids, spread_s: float = 0.0):
        """Best feasible actuator for a contact at t on sids (a run
        of strings for a rake). Returns (act, plan dict) or None.
        Does not commit."""
        m = self.mech
        for s in sids:
            lh = self.last_hit.get(s)
            if lh is not None and abs(t - lh) < m.restrike_s:
                return None
        best = None
        for a in m.actuators:
            f = self._feasible(a, t, sids, spread_s)
            if f is None:
                continue
            t_move, tr, t_last, dx = f
            # Least travel wins on the DISTANCE, not on the time: a
            # servo's time is SLEW_S for nearly every move on a
            # mechanism this size, so timing it ties every arm and
            # hands the note to whichever is idle. Distance still
            # separates them, and a hurried arm charged less than it
            # wanted does not masquerade as the nearer one.
            key = (dx, self.free_at[a.id])
            if best is None or key < best[0]:
                best = (key, a, t_move, tr, t_last)
        if best is None:
            return None
        _, a, t_move, tr, t_last = best
        return a, dict(actuator=a.id, t_move=float(t_move),
                t_free=float(t_last + a.recover_s),
                travel_s=float(tr), from_string=self.at[a.id])

    def options(self, t: float, sids, spread_s: float = 0.0) -> int:
        """How many actuators could take this contact now — the
        constraint count for tie-breaking."""
        return sum(1 for a in self.mech.actuators
                   if self._feasible(a, t, sids, spread_s) is not None)

    def commit(self, t: float, sids, act: Actuator, p: dict) -> None:
        m = self.mech
        moving, played = self._spans(act, sids)
        t_last = p["t_free"] - act.recover_s
        self.moves[act.id].append((p["t_move"], t - act.approach_s, t_last,
                moving, played, m.axis_pos(sids[-1])))
        self.free_at[act.id] = p["t_free"]
        self.at[act.id] = sids[-1]
        for s in sids:
            self.last_hit[s] = t
        self.last_t = max(self.last_t, t)


class Score:
    """The recorder. canvas: a Loop or a Take."""

    def __init__(self, canvas, name: str, bpm: float = 120.0,
            seed: int = 0, instrument: Instrument = None):
        self.canvas = canvas
        self.name = name
        self.bpm = bpm
        self.seed = seed
        self.instrument = instrument or Instrument(name)
        self.events = []
        self.cues = []
        self.conflicts = []
        self.stems = {}
        self.solvers = {}
        self.shapes = None
        self.refused = 0
        self.asked = 0
        self._ooo = False        # events arrived out of time order
        for m in self.instrument.mechanisms:
            self._ensure(m.id)

    # -- canvases and stems ------------------------------------------

    def _ensure(self, mech: str) -> None:
        if mech not in self.stems:
            self.stems[mech] = np.zeros_like(self.canvas.buf)
        if mech not in self.solvers:
            try:
                self.solvers[mech] = _Solver(self.instrument.mech(mech))
            except KeyError:
                pass

    def bus(self, mech: str) -> np.ndarray:
        """The mechanism's dry stem. Process it in place (e.g. print
        sympathetic() onto it): mixdown() re-sums stems, so
        stem-level work is heard."""
        self._ensure(mech)
        return self.stems[mech]

    def mixdown(self) -> np.ndarray:
        """Sum of stems — equals the canvas buffer unless a stem was
        processed in place, in which case this is the truth."""
        out = np.zeros_like(self.canvas.buf)
        for s in self.stems.values():
            out += s
        return out

    def _mix(self, mech: str, t: float, chunk: np.ndarray) -> None:
        self._ensure(mech)
        self.canvas.add(t, chunk)
        idx = self.canvas.place(t, len(chunk))
        if len(idx) == 0:
            return
        # a Loop's indices wrap (lead 0); a Take's are clipped and may
        # start inside the chunk when t < 0
        lead = 0 if hasattr(self.canvas, "loop_s") \
            else idx[0] - int(t * SR)
        np.add.at(self.stems[mech], idx, chunk[lead:lead + len(idx)])

    # -- recording -----------------------------------------------------

    def play(self, mech: str, t: float, chunk: np.ndarray,
            midi=None, string=None, strings=None, midis=None,
            amp: float = 1.0, pan: float = 0.0, pick=None,
            dur=None, voice: str = "", spread_s: float = 0.0,
            assign: bool = True, **extra) -> dict:
        """Mix a MONO chunk (panned, scaled) and record the event.
        Pass string/strings for the solver to plan an actuator."""
        sids = list(strings) if strings is not None else \
            ([string] if string is not None else [])
        ms = list(midis) if midis is not None else \
            ([float(midi)] if midi is not None else [])
        ev = dict(i=len(self.events), t=float(t), mech=mech,
                voice=voice, strings=sids, midis=ms, amp=float(amp),
                pan=float(pan), pick=pick,
                dur=float(dur if dur is not None else len(chunk) / SR),
                spread_s=float(spread_s))
        ev.update(extra)
        if assign and sids and mech in self.solvers:
            sv = self.solvers[mech]
            if t < sv.last_t:
                self._ooo = True
            p = sv.plan(t, sids, spread_s)
            if p is None:
                ev["actuator"] = None
                self.conflicts.append(ev["i"])
            else:
                a, plan = p
                ev.update(plan)
                sv.commit(t, sids, a, plan)
        self.events.append(ev)
        self._mix(mech, t, stereo(chunk * amp, pan))
        return ev

    def cue(self, t: float, kind: str, **data) -> dict:
        """Record without mixing: sections, camera cuts, anything the
        engine should know that makes no sound."""
        c = dict(t=float(t), kind=kind)
        c.update(data)
        self.cues.append(c)
        return c

    def can_play(self, mech: str, t: float, string=None, strings=None,
            spread_s: float = 0.0):
        """Ask before writing. Returns the Actuator that would take
        the note, or None. Counted: stats.asked / stats.refused."""
        sids = list(strings) if strings is not None else [string]
        self.asked += 1
        p = self.solvers[mech].plan(t, sids, spread_s)
        if p is None:
            self.refused += 1
            return None
        return p[0]

    # -- instrument-aware voices -------------------------------------

    def _synth(self, mech: Mechanism, sid: str, amp: float, pick,
            dur, seed: int) -> tuple:
        s = mech.string(sid)
        mat = MATERIALS[mech.material]
        f = hz(s.midi)
        if mat["synth"] == "pluck":
            pk = s.pick_default if pick is None else pick
            d = dur if dur is not None else mat["t60"] * 1.1
            v = _strings.pluck(f, d, amp=1.0, t60=mat["t60"],
                    damp=mat["damp"], pick=pk, soft=mat["soft"],
                    seed=seed)
            return v, pk, d
        table = getattr(_modal, mat["table"])
        v = _modal.strike(f, mat["t60"], table, amp=1.0,
                bright=mat["bright"])
        return v, None, len(v) / SR

    def pluck(self, mech: str, t: float, string: str, amp: float = 1.0,
            pick=None, dur=None, pan=None, voice: str = "",
            seed=None, **extra) -> dict:
        """Play one string of a mechanism with the material's synth.
        pick is where the arm lands (0..0.5); pan defaults to the
        string's geometric position."""
        m = self.instrument.mech(mech)
        seed = len(self.events) if seed is None else seed
        v, pk, d = self._synth(m, string, amp, pick, dur, seed)
        pn = m.pan_of(string) if pan is None else pan
        return self.play(mech, t, v, midi=m.string(string).midi,
                string=string, amp=amp, pan=pn, pick=pk, dur=d,
                voice=voice, **extra)

    def rake(self, mech: str, t: float, strings, amp: float = 1.0,
            spread_s: float = 0.018, pick=None, dur=None, pan=None,
            voice: str = "", seed=None, **extra) -> dict:
        """One sweep across several strings: ONE event, one
        actuator, onsets spread_s apart in order given."""
        m = self.instrument.mech(mech)
        seed = len(self.events) if seed is None else seed
        sids = list(strings)
        parts = []
        for k, sid in enumerate(sids):
            v, pk, d = self._synth(m, sid, amp, pick, dur, seed + k)
            parts.append((int(k * spread_s * SR), v))
        n = max(o + len(v) for o, v in parts)
        mono = np.zeros(n)
        for o, v in parts:
            mono[o:o + len(v)] += v / np.sqrt(len(sids))
        pn = m.pan_of(sids[len(sids) // 2]) if pan is None else pan
        return self.play(mech, t, mono, strings=sids,
                midis=[m.string(s).midi for s in sids], amp=amp,
                pan=pn, pick=pk, dur=n / SR, voice=voice,
                spread_s=spread_s, **extra)

    # -- solving and export --------------------------------------------

    def finalize(self) -> dict:
        """Global re-solve, time-sorted, from fresh solvers. If events
        came in time order this reproduces the incremental plan; if
        not, this is authoritative and `reassigned` counts the
        difference. Returns stats."""
        reassigned = 0
        self.conflicts = []
        fresh = {mid: _Solver(self.instrument.mech(mid))
                 for mid in self.solvers}
        # ties (simultaneous notes on one mechanism) resolve MOST
        # CONSTRAINED FIRST — the event with the fewest arms able to
        # take it — then by string index, low first. Content-only:
        # the plan never depends on the order a composer wrote in
        # (e99 claim 3). Least-travel alone is myopic: The Chamber's
        # arm2, resting one string from an answer note arm1 could
        # also play, took it and blocked the run only arm2 reaches.
        def key(i):
            ev = self.events[i]
            si = self.instrument.mech(ev["mech"]).index(ev["strings"][0]) \
                if ev["strings"] and ev["mech"] in fresh else -1
            return (ev["t"], ev["mech"], si, i)
        order = sorted(range(len(self.events)), key=key)
        k = 0
        while k < len(order):
            ev0 = self.events[order[k]]
            grp = [order[k]]
            while (k + len(grp) < len(order)
                   and self.events[order[k + len(grp)]]["t"] == ev0["t"]
                   and self.events[order[k + len(grp)]]["mech"]
                   == ev0["mech"]):
                grp.append(order[k + len(grp)])
            if len(grp) > 1 and ev0["mech"] in fresh:
                sv = fresh[ev0["mech"]]
                grp.sort(key=lambda i: (sv.options(self.events[i]["t"],
                        self.events[i]["strings"]), key(i)))
                order[k:k + len(grp)] = grp
            k += len(grp)
        for i in order:
            ev = self.events[i]
            if not ev["strings"] or ev["mech"] not in fresh:
                continue
            was = ev.get("actuator")
            p = fresh[ev["mech"]].plan(ev["t"], ev["strings"],
                    ev.get("spread_s", 0.0))
            if p is None:
                ev["actuator"] = None
                for k in ("t_move", "t_free", "travel_s", "from_string"):
                    ev.pop(k, None)
                self.conflicts.append(i)
            else:
                a, plan = p
                ev.update(plan)
                fresh[ev["mech"]].commit(ev["t"], ev["strings"], a, plan)
            if ev.get("actuator") != was:
                reassigned += 1
        if self.shapes is not None:
            self._name_shapes()
        return self.stats(reassigned)

    def stats(self, reassigned: int = 0) -> dict:
        return dict(events=len(self.events), cues=len(self.cues),
                asked=self.asked, refused=self.refused,
                conflicts=len(self.conflicts), reassigned=reassigned,
                out_of_order=self._ooo)

    def attach_shapes(self, clips) -> None:
        """Stage 3: a shape library (fdstring.shape_library). Each
        plucked event names the clip nearest its pick."""
        self.shapes = list(clips)
        self._name_shapes()

    def _name_shapes(self) -> None:
        picks = np.array([c["pick"] for c in self.shapes])
        for ev in self.events:
            if ev.get("pick") is None:
                ev["shape"] = None
                continue
            ev["shape"] = self.shapes[int(np.argmin(
                    np.abs(picks - ev["pick"])))]["id"]

    def duration_s(self) -> float:
        return getattr(self.canvas, "dur_s",
                getattr(self.canvas, "loop_s", self.canvas.n / SR))

    def export(self, outdir: str, stem_gain=None,
            env_hz: int = 50) -> dict:
        """score.json + stems/<mech>.wav (+ shapes.f32). Stems share
        ONE gain (recorded) so their sum is still the mix. Per-stem
        peak envelopes at env_hz ride along for the engine."""
        os.makedirs(os.path.join(outdir, "stems"), exist_ok=True)
        stats = self.finalize()
        # A composer's ledger (songs/chamber.py: intended, as written,
        # substituted, dropped) rides in the stats when the song kept one.
        stats.update(getattr(self, "ledger", None) or {})
        mix = self.mixdown()
        if stem_gain is None:
            stem_gain = 0.9 / (np.max(np.abs(mix)) + 1e-12)
        stems = {}
        for mid, buf in self.stems.items():
            rel = os.path.join("stems", f"{mid}.wav")
            write_wav(os.path.join(outdir, rel), buf * stem_gain)
            stems[mid] = rel
        # coarse |x| envelopes per stem, for the engine to breathe by
        hop = SR // env_hz
        envs = {}
        for mid, buf in self.stems.items():
            e = np.abs(buf * stem_gain).max(axis=1)
            e = e[:len(e) // hop * hop].reshape(-1, hop).max(axis=1)
            envs[mid] = [round(float(v), 4) for v in e]
        doc = dict(format=FORMAT, name=self.name, bpm=self.bpm,
                seed=self.seed, sr=SR, duration_s=self.duration_s(),
                total_s=self.canvas.n / SR,
                loop=hasattr(self.canvas, "loop_s"),
                instrument=self.instrument.to_dict(),
                events=self.events, cues=self.cues, stems=stems,
                stems_gain=float(stem_gain), stats=stats,
                conflicts=self.conflicts,
                envelopes=dict(rate_hz=env_hz, stems=envs))
        if self.shapes is not None:
            doc["shapes"] = self._write_shapes(outdir)
        with open(os.path.join(outdir, "score.json"), "w") as f:
            json.dump(doc, f, indent=1)
        print(f"score {self.name}: {stats['events']} events, "
              f"{stats['cues']} cues, {stats['conflicts']} conflicts, "
              f"{stats['refused']}/{stats['asked']} refused"
              + (f", {len(self.shapes)} shape clips"
                 if self.shapes else ""))
        return doc

    def _write_shapes(self, outdir: str) -> dict:
        clips, off = [], 0
        blobs = []
        for c in self.shapes:
            fr = np.asarray(c["frames"], dtype="<f4")
            F, N = fr.shape
            clips.append(dict(id=c["id"], pick=c["pick"], nodes=N,
                    rate_hz=c["rate_hz"], frames=F, offset=off,
                    scale_m=c["scale_m"], t60_s=c.get("t60_s")))
            blobs.append(fr.tobytes())
            off += F * N
        with open(os.path.join(outdir, "shapes.f32"), "wb") as f:
            for b in blobs:
                f.write(b)
        return dict(file="shapes.f32", dtype="float32le",
                total_floats=off, clips=clips)

    # -- the reference picture ---------------------------------------

    def plot(self, path: str, title=None) -> None:
        """The annotated track — lanes per mechanism, events as
        ticks (pitch up, amp = height, color = actuator), motion and
        recover spans as bars, cues as lines. The image the engine
        harness must match."""
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        mechs = [m.id for m in self.instrument.mechanisms] + \
            [k for k in self.stems if k not in
             [m.id for m in self.instrument.mechanisms]]
        fig, axes = plt.subplots(len(mechs), 1, sharex=True,
                figsize=(16, 2.2 * len(mechs) + 1), squeeze=False)
        total = self.canvas.n / SR
        palette = plt.rcParams["axes.prop_cycle"].by_key()["color"]
        for ax, mid in zip(axes[:, 0], mechs):
            evs = [e for e in self.events if e["mech"] == mid]
            acts = sorted({e.get("actuator") for e in evs
                           if e.get("actuator")})
            col = {a: palette[k % len(palette)]
                   for k, a in enumerate(acts)}
            ms = [m for e in evs for m in e["midis"]] or [60]
            lo, hi = min(ms) - 1, max(ms) + 1
            stem = self.stems.get(mid)
            if stem is not None:
                env = np.abs(stem).max(axis=1)
                hop = SR // 50
                env = env[:len(env) // hop * hop].reshape(-1, hop).max(1)
                tt = np.arange(len(env)) * hop / SR
                ax.fill_between(tt, lo, lo + (hi - lo) * env
                        / (env.max() + 1e-12), color="0.85", lw=0)
            for e in evs:
                c = col.get(e.get("actuator"), "0.3")
                y = e["midis"][0] if e["midis"] else (lo + hi) / 2
                if e.get("t_move") is not None:
                    ax.plot([e["t_move"], e["t"]], [y, y], color=c,
                            lw=3, alpha=0.35, solid_capstyle="butt")
                    ax.plot([e["t"], e["t_free"]], [y, y], color=c,
                            lw=3, alpha=0.15, solid_capstyle="butt")
                if e.get("actuator") is None and e["strings"]:
                    ax.plot(e["t"], y, "x", color="red", ms=8)
                for m in e["midis"]:
                    ax.plot([e["t"], e["t"]],
                            [m - 0.4 * e["amp"], m + 0.4 * e["amp"]],
                            color=c, lw=2)
            for a in acts:
                ax.plot([], [], color=col[a], lw=3, label=a)
            ax.set_ylim(lo, hi)
            ax.set_ylabel(mid)
            if acts:
                ax.legend(loc="upper right", fontsize=7, ncol=len(acts))
            for c in self.cues:
                ax.axvline(c["t"], color="k", lw=0.6, alpha=0.5, ls="--")
        for c in self.cues:
            axes[0, 0].text(c["t"], axes[0, 0].get_ylim()[1],
                    f" {c['kind']}:{c.get('name', '')}", fontsize=7,
                    va="top", rotation=90)
        axes[-1, 0].set_xlim(0, total)
        axes[-1, 0].set_xlabel("seconds")
        fig.suptitle(title or self.name)
        fig.tight_layout()
        fig.savefig(path, dpi=110)
        plt.close(fig)
        print(f"wrote {path}")

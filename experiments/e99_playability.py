#!/usr/bin/env python3
"""e99 — playability: the machine as a constraint in the composer.

Stage 2's solver, claimed (docs/chamber-spec.md). Animusic edited
MIDI until the machine could play it; here the composer ASKS
(`can_play`) before writing, and every event exports its plan —
actuator, t_move, t, t_free — which is what the engine interpolates.

  1. DENSE PASSAGE PLAYS: 16 strings, 3 arms overlapping by 4, a
     140 BPM line of 8ths with 16th-note runs, written by asking
     first. Zero conflicts, plan consistent (no actuator overlaps
     its own busy spans), and the incremental plan equals the global
     re-solve (reassigned = 0) because events came in time order.
  2. CAPACITY, PREDICTED: one arm, 16ths (107 ms). (a) Alternating
     strings 0 and 15: crossing needs approach + 15 * travel +
     recover = 630 ms, but the NEXT string-0 note needs only 180 ms
     — greedy takes it and never crosses: exactly n/2 conflicts, every
     played note on string 0. (First draft predicted every-6th-note
     and was wrong; the solver was right — a lesson about writing
     the arithmetic for the rule, not for the intent.) (b) String 0
     once, then string 15 forever: forced to cross once (k = 6), then
     every 2nd: played = 1 + |{even k >= 6}|. The number, not "some".
  3. ORDER-INDEPENDENCE: the passage of (1) written with its voices
     in REVERSE insertion order (melody first, then the earlier
     bass) sets the out-of-order flag, finalize() re-solves, and the
     authoritative plan matches (1)'s event for event, with (1)'s
     refusals now appearing as exactly that many conflicts. (First
     run: 9 mismatches, all SIMULTANEOUS notes — the tie-break was
     insertion order. Now ties resolve by string index, low first:
     the plan depends on the score's content, never on the order a
     composer wrote it in.)
  4. A RAKE HOLDS ITS ARM: a 5-string sweep is one event on one
     actuator; the next note on that arm waits past t + 4*spread +
     recover (t_free says so), and a second arm takes a note asked
     for inside that span.
  5. RESTRIKE: two hits on one string 30 ms apart — the second is
     refused (the pick must clear the string), any arm.

    python3 experiments/e99_playability.py [outdir]
"""

import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))))
from loam import SR, Take
from loam import ruler
from loam.score import Score, Instrument, Mechanism
from loam.rhythm import scale_notes

outdir = sys.argv[1] if len(sys.argv) > 1 else "render"
ex = os.path.join(outdir, "e99")
os.makedirs(ex, exist_ok=True)
fails = []


def check(name, cond, detail):
    print(f"  {'PASS' if cond else 'FAIL'} {name}: {detail}")
    if not cond:
        fails.append(name)


BPM = 140.0
SPB = 60.0 / BPM
MIDIS = scale_notes(50, "dorian", 3)[:16]          # D3 dorian, 16 strings
HARP = dict(id="harp", kind="plucked", material="steel", midis=MIDIS,
        arms=3, overlap=4, approach_s=0.12, recover_s=0.06,
        travel_s=0.03)


def passage():
    """(t, string index, amp, voice) — 8 bars: a bass on beats, a
    melody in 8ths with 16th runs on bar ends."""
    rng = np.random.default_rng(99)
    ev = []
    for bar in range(8):
        for b in range(4):
            ev.append(((bar * 4 + b) * SPB, [0, 2, 4, 2][b] + (bar % 2) * 3,
                       0.9, "bass"))
        for e8 in range(8):
            t = (bar * 4 + e8 * 0.5) * SPB
            si = 8 + int((e8 * 3 + bar) % 8)
            ev.append((t, si, 0.7, "melody"))
        if bar % 2 == 1:
            for s16 in range(4):
                t = (bar * 4 + 3 + 0.25 * s16) * SPB
                ev.append((t + 0.125 * SPB, 6 + s16 * 2, 0.5, "run"))
    return ev


def write(sc, evs, ask=True):
    """Compose by asking. Returns (written, refused)."""
    w = r = 0
    for t, si, a, voice in evs:
        sid = f"harp{si:02d}"
        if ask and sc.can_play("harp", t, sid) is None:
            r += 1
            continue
        sc.pluck("harp", t, sid, amp=a, voice=voice, dur=0.6)
        w += 1
    return w, r


# ---- 1. dense passage, in time order -------------------------------------------
evs = sorted(passage(), key=lambda e: e[0])
inst = Instrument("e99", [Mechanism.build(**HARP)])
tk = Take(8 * 4 * SPB, 99, tail_s=1.0)
sc = Score(tk, "e99-dense", bpm=BPM, seed=99, instrument=inst)
w, r = write(sc, evs)
stats = sc.finalize()
pc = ruler.plan_consistent(sc.events)
check("dense passage plays: 0 conflicts, consistent, in-order == global",
        stats["conflicts"] == 0 and pc["ok"] and stats["reassigned"] == 0
        and not stats["out_of_order"],
        f"{w} written, {r} refused of {len(evs)}; plan ok={pc['ok']} "
        f"overlaps={len(pc['overlaps'])}; reassigned {stats['reassigned']}")
arms = {}
for e in sc.events:
    arms[e["actuator"]] = arms.get(e["actuator"], 0) + 1
check("all three arms work", len(arms) == 3 and min(arms.values()) > 10,
        ", ".join(f"{k}:{v}" for k, v in sorted(arms.items())))

# ---- 2. capacity, predicted --------------------------------------------------------
one = Instrument("e99", [Mechanism.build(**{**HARP, "arms": 1})])
n = 40
tk2 = Take(n * SPB / 4 + 1, 1, tail_s=1.0)
sc2 = Score(tk2, "e99-capacity", bpm=BPM, seed=1, instrument=one)
for k in range(n):
    sc2.pluck("harp", k * SPB / 4, f"harp{0 if k % 2 == 0 else 15:02d}",
            dur=0.3)
st2 = sc2.finalize()
on0 = all(e["strings"][0] == "harp00" for e in sc2.events
          if e["actuator"] is not None)
check("capacity (a): alternating — greedy stays home, n/2 conflicts",
        st2["conflicts"] == n // 2 and on0,
        f"predicted {n // 2} conflicts, solver {st2['conflicts']}; "
        f"all played on string 0: {on0}")
tk2b = Take(n * SPB / 4 + 1, 1, tail_s=1.0)
sc2b = Score(tk2b, "e99-capacity-b", bpm=BPM, seed=1, instrument=one)
for k in range(n):
    sc2b.pluck("harp", k * SPB / 4, f"harp{0 if k == 0 else 15:02d}",
            dur=0.3)
st2b = sc2b.finalize()
need = 0.12 + 15 * 0.03 + 0.06                  # the one crossing
k_first = int(np.ceil(need / (SPB / 4)))        # -> 6
hop = int(np.ceil((0.12 + 0.06) / (SPB / 4)))   # same-string -> 2
predicted = n - (1 + len(range(k_first, n, hop)))
check("capacity (b): forced crossing, then every 2nd — the arithmetic",
        st2b["conflicts"] == predicted,
        f"cross at k={k_first}, then every {hop}: predicted {predicted} "
        f"conflicts, solver {st2b['conflicts']}")

# ---- 3. order-independence ---------------------------------------------------------
tk3 = Take(8 * 4 * SPB, 99, tail_s=1.0)
sc3 = Score(tk3, "e99-reversed", bpm=BPM, seed=99, instrument=inst)
by_voice = {}
for e in evs:
    by_voice.setdefault(e[3], []).append(e)
rev = by_voice["run"] + by_voice["melody"] + by_voice["bass"]   # layered
# NOTE: write without asking — a layered composer can't ask
# incrementally in time order; the global re-solve is the truth
w3, _ = write(sc3, rev, ask=False)
st3 = sc3.finalize()
plan1 = {(e["t"], e["strings"][0]): e["actuator"] for e in sc.events}
plan3 = {(e["t"], e["strings"][0]): e["actuator"] for e in sc3.events}
same = sum(plan1.get(k) == v for k, v in plan3.items())
check("order-independence: reversed insertion, same authoritative plan",
        st3["out_of_order"] and st3["reassigned"] > 0
        and same == len(plan3) and st3["conflicts"] == r,
        f"out_of_order={st3['out_of_order']}, {st3['reassigned']} reassigned "
        f"by the re-solve; {same}/{len(plan3)} events match passage (1)")

# ---- 4. a rake holds its arm --------------------------------------------------
inst4 = Instrument("e99", [Mechanism.build(**{**HARP, "arms": 2,
        "overlap": 8})])
tk4 = Take(3.0, 4, tail_s=1.0)
sc4 = Score(tk4, "e99-rake", bpm=BPM, seed=4, instrument=inst4)
rk = sc4.rake("harp", 1.0, [f"harp{i:02d}" for i in range(6, 11)],
        spread_s=0.02, dur=0.5)
t_after = rk["t_free"]
a_rake = rk["actuator"]
# a note inside the rake's span, reachable by both arms
inside = sc4.pluck("harp", 1.10, "harp08", dur=0.3)
check("rake holds its arm; the other arm takes the note inside",
        abs(t_after - (1.0 + 4 * 0.02 + 0.06)) < 1e-9
        and inside["actuator"] is not None and inside["actuator"] != a_rake,
        f"rake on {a_rake} free at {t_after:.3f}s; note at 1.10 on "
        f"{inside['actuator']}")

# ---- 5. restrike ---------------------------------------------------------------------
tk5 = Take(2.0, 5, tail_s=1.0)
sc5 = Score(tk5, "e99-restrike", bpm=BPM, seed=5, instrument=inst)
a = sc5.can_play("harp", 1.0, "harp05")
sc5.pluck("harp", 1.0, "harp05", dur=0.3)
b = sc5.can_play("harp", 1.03, "harp05")
c = sc5.can_play("harp", 1.03, "harp06")
check("restrike inside 50 ms refused; the neighbour string is fine",
        a is not None and b is None and c is not None,
        f"harp05 @1.00 -> {a.id}; harp05 @1.03 -> {b}; harp06 @1.03 -> {c.id}")

doc = sc.export(ex)
sc.plot(os.path.join(ex, "track.png"),
        "e99 — dense passage, three arms, written by asking")

if fails:
    print("FAILED RULERS:", fails)
    sys.exit(1)
print("ALL RULERS PASS")

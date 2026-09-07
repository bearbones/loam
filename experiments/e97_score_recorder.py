#!/usr/bin/env python3
"""e97 — the Score recorder: loam remembers what it plays.

Stage 1 of the chamber (docs/chamber-spec.md). Before this, a song
computed an event time inline, mixed, and forgot. Score sits between
composer and canvas and records; the claim is that it changes
NOTHING about the sound:

  1. LOOP identity — a passage mixed by the ORIGINAL Loop.add formula
     (inlined here: modulo indices + np.add.at, so the place()
     refactor cannot hide a change) equals the same passage through
     Score.play over a fresh Loop, np.array_equal — bit for bit.
  2. TAKE identity — same claim over the one-shot canvas, including
     a note whose tail runs past the take (clipped, not wrapped) and
     one starting before 0.
  3. STEMS sum to the canvas (two mechanisms, interleaved).
  4. JSON round-trip: every event's t is sample-exact after the trip
     (json.dump uses repr; repr round-trips a double), and the plan
     fields survive.
  5. A processed stem is heard: print sympathetic() onto one stem,
     mixdown() differs from the canvas by exactly that stem's change.

    python3 experiments/e97_score_recorder.py [outdir]
"""

import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))))
from loam import SR, hz, Loop, Take, stereo
from loam.score import Score, Instrument, Mechanism
from loam.strings import pluck, sympathetic

outdir = sys.argv[1] if len(sys.argv) > 1 else "render"
os.makedirs(outdir, exist_ok=True)
fails = []


def check(name, cond, detail):
    print(f"  {'PASS' if cond else 'FAIL'} {name}: {detail}")
    if not cond:
        fails.append(name)


# a passage: 24 plucks over 4 s, D dorian, the last ones wrap/run over
MIDIS = [62, 64, 65, 67, 69, 71, 72, 74]
PASSAGE = [(k * 0.17 + 0.05, MIDIS[(k * 3) % 8], 0.6 + 0.4 * ((k * 5) % 3) / 2,
            -0.6 + 1.2 * (k % 4) / 3) for k in range(24)]
NOTES = {m: pluck(hz(m), 1.4, t60=2.0, damp=0.2, pick=0.2, seed=m)
         for m in MIDIS}

# ---- 1. loop identity, against the original formula ------------------
ref = Loop(4.0, 7)
for t, m, a, p in PASSAGE:
    ch = stereo(NOTES[m] * a, p)
    idx = (int(t * SR) + np.arange(len(ch))) % ref.n      # the old add
    np.add.at(ref.buf, idx, ch)

inst = Instrument("e97", [Mechanism.build("harp", "plucked", "steel",
        MIDIS, arms=2, overlap=2)])
lp = Loop(4.0, 7)
sc = Score(lp, "e97-loop", bpm=120, seed=7, instrument=inst)
for t, m, a, p in PASSAGE:
    sc.play("harp", t, NOTES[m], midi=m, string=f"harp{MIDIS.index(m):02d}",
            amp=a, pan=p)
check("loop identity (bit-exact vs original add)",
        np.array_equal(ref.buf, lp.buf),
        f"max |diff| = {np.max(np.abs(ref.buf - lp.buf)):.3e}")
check("loop stem is the canvas",
        np.array_equal(sc.bus("harp"), lp.buf), "single stem == buffer")

# ---- 2. take identity ----------------------------------------------------
tref = Take(4.0, 7, tail_s=0.5)
tk = Take(4.0, 7, tail_s=0.5)
sc2 = Score(tk, "e97-take", bpm=120, seed=7, instrument=inst)
extra = PASSAGE + [(4.3, 62, 0.8, 0.0), (-0.3, 74, 0.5, 0.2)]
for t, m, a, p in extra:
    tref.add(t, stereo(NOTES[m] * a, p))
    sc2.play("harp", t, NOTES[m], midi=m,
            string=f"harp{MIDIS.index(m):02d}", amp=a, pan=p)
check("take identity (clipped tail, negative start)",
        np.array_equal(tref.buf, tk.buf),
        f"max |diff| = {np.max(np.abs(tref.buf - tk.buf)):.3e}; "
        f"last sample {tk.buf[-1, 0]:+.4f} (tail clipped, nonzero)")

# ---- 3. stems sum to the canvas ------------------------------------------
inst3 = Instrument("e97", [
    Mechanism.build("harp", "plucked", "steel", MIDIS, arms=2, overlap=2),
    Mechanism.build("bars", "struck", "rosewood", MIDIS[:4], arms=1)])
tk3 = Take(4.0, 7, tail_s=0.5)
sc3 = Score(tk3, "e97-stems", bpm=120, seed=7, instrument=inst3)
for k, (t, m, a, p) in enumerate(PASSAGE):
    mech = "bars" if k % 3 == 0 else "harp"
    sid = f"{mech}{(MIDIS.index(m) % (4 if mech == 'bars' else 8)):02d}"
    sc3.play(mech, t, NOTES[m], midi=m, string=sid, amp=a, pan=p)
mix = sc3.mixdown()
check("stems sum to canvas",
        np.max(np.abs(mix - tk3.buf)) < 1e-12,
        f"max |sum(stems) - canvas| = {np.max(np.abs(mix - tk3.buf)):.2e} "
        f"over {len(sc3.stems)} stems")

# ---- 4. json round trip ----------------------------------------------------
sc3.cue(0.0, "section", name="A")
sc3.cue(2.04, "camera", name="cut-wide")
ex = os.path.join(outdir, "e97")
doc = sc3.export(ex)
back = json.load(open(os.path.join(ex, "score.json")))
same_t = all(int(a["t"] * SR) == int(b["t"] * SR) and a["t"] == b["t"]
             for a, b in zip(sc3.events, back["events"]))
have_plan = all(("t_move" in e and "t_free" in e and e["actuator"])
                for e in back["events"])
check("json round-trip: t sample-exact, plans present",
        same_t and have_plan and len(back["events"]) == len(PASSAGE)
        and len(back["cues"]) == 2 and back["format"] == "loam-score/1",
        f"{len(back['events'])} events, {len(back['cues'])} cues, "
        f"conflicts {back['stats']['conflicts']}")
stem_wavs = all(os.path.exists(os.path.join(ex, p))
                for p in back["stems"].values())
check("stems written", stem_wavs, ", ".join(back["stems"].values()))

# ---- 5. a processed stem is heard ------------------------------------------
before = sc3.mixdown()
harp = sc3.bus("harp")
wet = sympathetic(harp, [62, 69, 74], t60=2.0, coupling=0.2, mix=0.5,
        loop=False)
harp[:] = wet
after = sc3.mixdown()
delta_mix = after - before
delta_stem = wet - (before - sc3.bus("bars"))
check("stem processing reaches the mixdown",
        np.max(np.abs(delta_mix - delta_stem)) < 1e-9
        and np.max(np.abs(delta_mix)) > 1e-3,
        f"mixdown moved by exactly the stem's change "
        f"(max {np.max(np.abs(delta_mix)):.3f})")

sc3.plot(os.path.join(ex, "track.png"), "e97 — the recorder's view")

if fails:
    print("FAILED RULERS:", fails)
    sys.exit(1)
print("ALL RULERS PASS")

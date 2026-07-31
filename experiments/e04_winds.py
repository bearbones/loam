#!/usr/bin/env python3
"""e04 — the waveguide flute speaks. A ney phrase in D over a
bowed-glass drone, sentence grammar (statement, rest, answer),
one overblown note as the peak.

    python3 experiments/e04_winds.py [outdir]
"""

import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))))
from loam import SR, hz, Loop, stereo, write_wav, seam_report
from loam.winds import flute, ney, _fpeak
from loam.modal import bow, GLASS
from loam.space import reverb_loop

outdir = sys.argv[1] if len(sys.argv) > 1 else "render"
os.makedirs(outdir, exist_ok=True)

L = Loop(32.0, 0xF1E)

# drone: bowed glass D3 + A3, re-bowed to cover the loop
for at, midi, dur, amp in [(0, 50, 9.0, 0.16), (8, 57, 9.0, 0.10),
        (16, 50, 9.0, 0.16), (24, 57, 9.5, 0.10)]:
    g = bow(hz(midi), dur, GLASS, amp=amp, vib_hz=0.0, rng=L.rng)
    L.add(at, stereo(g, -0.2 if midi == 50 else 0.25))

# the sentence: D dorian-ish ney, statement 2-10s, rest, answer 14-24
PHRASE = [
    (2.0, 62, 1.6, 0.30), (3.8, 65, 1.2, 0.28), (5.2, 67, 1.8, 0.32),
    (7.2, 65, 1.0, 0.26), (8.4, 62, 2.2, 0.30),          # cadence
]
ANSWER = [
    (14.0, 69, 1.6, 0.30), (15.8, 70, 1.2, 0.28),
    (17.2, 74, 2.4, 0.34, 1.0),                          # overblown peak
    (20.0, 70, 1.0, 0.26), (21.2, 67, 1.1, 0.26),
    (22.5, 62, 2.6, 0.30),                               # home
]
checks = []
for note in PHRASE:
    at, midi, dur, amp = note
    m = ney(hz(midi), dur, amp=amp, seed=midi * 3)
    checks.append((midi, m))
    L.add(at, stereo(m, 0.1))
for note in ANSWER:
    at, midi, dur, amp = note[:4]
    ob = note[4] if len(note) > 4 else 0.0
    if ob > 0:
        m = flute(hz(midi - 12), dur, amp=amp, breath=0.12,
                overblow=ob, vib_amt=0.05, seed=midi * 3)
    else:
        m = ney(hz(midi), dur, amp=amp, seed=midi * 3)
    L.add(at, stereo(m, 0.15))

L.buf = reverb_loop(L.buf, t60=2.8, size=1.1, damp_hz=3600.0, mix=0.35)
out = L.master(6500.0, drive=1.3)
write_wav(os.path.join(outdir, "e04_ney.wav"), out)
print(" ", seam_report(out))
# pitch is verified on the SOLO stems — measuring one pitch inside
# the mixed loop finds the drone, not the ney (learned the hard way)
for midi, m in checks:
    c = 1200 * np.log2(_fpeak(m) / hz(midi))
    print(f"  stem note {midi}: {c:+.0f} cents")

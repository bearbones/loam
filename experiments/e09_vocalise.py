#!/usr/bin/env python3
"""e09 — the hermit hums. Solo voice (source-filter vocalise) over
a low pad, feeding a D-minor taraf so the room hums back; FDN
reverb. Sentence grammar: statement, rest, answer, rest.

    python3 experiments/e09_vocalise.py [outdir]
"""

import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))))
from loam import SR, hz, Loop, stereo, write_wav, seam_report
from loam.voice import sing
from loam.pads import padsynth_stereo, formant_amps, VOWELS
from loam.strings import sympathetic
from loam.space import reverb_loop

outdir = sys.argv[1] if len(sys.argv) > 1 else "render"
os.makedirs(outdir, exist_ok=True)
L = Loop(28.0, 0xE09)

# low bed: 'oo' choir D2+A2, quiet
for i, (midi, g) in enumerate([(38, 1.0), (45, 0.6)]):
    f0 = hz(midi)
    L.buf += padsynth_stereo(28.0, f0,
            formant_amps(f0, 40, VOWELS["oo"]),
            bw_cents=40.0, seed=900 + i) * 0.05 * g

# the sentence (D minor, signature falling 4th A->E at the cadence)
S = [(69, 1.5, "ah"), (67, 0.5, "ah"), (65, 1.0, ("ah", "oh")),
     (62, 1.0, "oh"), (64, 1.5, "oh"), (64, 0.5, ("oh", "ah")),
     (65, 1.0, "ah"), (62, 2.0, ("ah", "oo"))]
A = [(70, 1.5, "ah"), (69, 0.5, "ah"), (67, 1.0, ("ah", "eh")),
     (69, 1.0, "eh"), (65, 1.5, ("eh", "oh")), (64, 0.5, "oh"),
     (62, 3.0, ("oh", "oo"))]
v1 = sing(S, bpm=84, seed=11)
v2 = sing(A, bpm=84, seed=12, amp=0.9)
vbus = np.zeros((L.n, 2))


def addw(buf, at_s, chunk):
    idx = (int(at_s * SR) + np.arange(len(chunk))) % len(buf)
    np.add.at(buf, idx, chunk)


addw(vbus, 2.0, stereo(v1 * 0.5, 0.06))
addw(vbus, 15.0, stereo(v2 * 0.5, -0.06))

# the room hums back: voice drives the taraf
taraf = sympathetic(vbus, [50, 53, 57, 62, 65, 69], t60=3.5,
        coupling=0.2, mix=1.0) * 0.35
L.buf += vbus + taraf
L.buf = reverb_loop(L.buf, t60=3.0, size=1.2, damp_hz=3800.0, mix=0.32)
out = L.master(6800.0, drive=1.35)
write_wav(os.path.join(outdir, "e09_vocalise.wav"), out)
print(" ", seam_report(out))
for a, b, tag in [(2, 10, "statement"), (10.5, 14.5, "rest"),
        (15, 23, "answer"), (24, 28, "wrap rest")]:
    r = np.sqrt((out[int(a * SR): int(b * SR)] ** 2).mean())
    print(f"  {tag:10s} rms {r:.3f}")

#!/usr/bin/env python3
"""e10 — same phrase, three invented rooms: a dark cathedral, a
metal tank, the inside of a bone. 8s each, back to back.

    python3 experiments/e10_threerooms.py [outdir]
"""

import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))))
from loam import SR, hz, stereo, write_wav
from loam.modal import strike, CHURCH_BELL
from loam.strings import pluck
from loam.space import ir_room, ir_tank, ir_bone, convolve_loop

outdir = sys.argv[1] if len(sys.argv) > 1 else "render"
os.makedirs(outdir, exist_ok=True)
SEG = 8.0
n = int(SEG * SR)

dry = np.zeros((n, 2))
rng = np.random.default_rng(4)
b = strike(hz(50), 4.0, CHURCH_BELL, amp=0.5, rng=rng, knock=0.1)
dry[: len(b)] += stereo(b, 0.0)
for at, midi in [(1.2, 62), (1.9, 65), (2.6, 69), (3.3, 74),
        (4.4, 70), (5.2, 65), (6.0, 62)]:
    p = pluck(hz(midi), 1.6, amp=0.3, seed=midi)
    i0 = int(at * SR)
    end = min(i0 + len(p), n)
    dry[i0:end] += stereo(p, 0.2 if midi % 2 else -0.2)[: end - i0]

ROOMS = [("cathedral", ir_room(3.4, size=1.6, bright=0.35, seed=11)),
         ("tank", ir_tank(1.8, seed=12)),
         ("bone", ir_bone(1.2, seed=13))]
out = np.zeros((3 * n, 2))
print("section character (wet tail 6.5-8s of each):")
for k, (name, ir) in enumerate(ROOMS):
    w = convolve_loop(dry, ir, mix=0.5)
    out[k * n: (k + 1) * n] = w
    tail = w[int(6.5 * SR): n, 0]
    sp = np.abs(np.fft.rfft(tail))
    fr = np.fft.rfftfreq(len(tail), 1 / SR)
    cen = float((sp * fr).sum() / (sp.sum() + 1e-12))
    r = float(np.sqrt((tail ** 2).mean()))
    print(f"  {name:10s} tail rms {r:.4f}  centroid {cen:6.0f} Hz")
out *= 0.88 / np.max(np.abs(out))
write_wav(os.path.join(outdir, "e10_threerooms.wav"), out)

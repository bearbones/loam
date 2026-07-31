#!/usr/bin/env python3
"""e13 — Euclidean clockwork. Every voice its own euclid(k,n):
kick 5/16, clap 3/8, hats 7/16 (swung), shaker 11/16, cowbell
2/5 across the bar; psaltery walks Hijaz Kar on euclid(5,12).

    python3 experiments/e13_clockwork.py [outdir]
"""

import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))))
from loam import SR, hz, Loop, stereo, write_wav, seam_report
from loam.rhythm import euclid, rotate, onsets, swing, scale_notes
from loam.strings import pluck
from loam.dyn import duck, limiter
from loam import drums as dr

outdir = sys.argv[1] if len(sys.argv) > 1 else "render"
os.makedirs(outdir, exist_ok=True)
BPM = 108.0
spb = 60.0 / BPM
BARS = 8
L = Loop(BARS * 4 * spb, 0xE13)
e16 = spb / 4

VOICES = [
    ("kick", euclid(5, 16), 0, lambda s: dr.kick(f1=45.0), 0.9, 0.0),
    ("clap", rotate(euclid(3, 8), 1), 1, lambda s: dr.clap(seed=s) * 0.6,
        0.8, 0.1),
    ("hat", euclid(7, 16), 0, lambda s: dr.hat(seed=s) * 0.5, 0.6, None),
    ("shaker", euclid(11, 16), 0, lambda s: dr.shaker(seed=s) * 0.35,
        0.5, None),
    ("cowbell", euclid(2, 5), 2, lambda s: dr.cowbell() * 0.16, 0.5, -0.3),
]
kick_tr = np.zeros(L.n)
drums = np.zeros((L.n, 2))
counts = {}
for name, pat, half_shift, mk, gain, pan in VOICES:
    step = e16 if len(pat) in (16,) else (spb / 2 if len(pat) == 8
            else 4 * spb / len(pat))
    times = onsets(pat, step / spb)
    if name == "hat":
        times = swing(times, 0.14, 0.25)
    counts[name] = len(times)
    for bar in range(BARS):
        for k, tb in enumerate(times):
            v = mk(bar * 16 + k)
            at_s = (bar * 4 + tb) * spb
            p = pan if pan is not None else (0.75 if k % 2 else -0.75)
            c = stereo(v, p) * gain
            idx = (int(at_s * SR) + np.arange(len(c))) % L.n
            np.add.at(drums, idx, c)
            if name == "kick":
                np.add.at(kick_tr, idx[: len(v)], v * gain)

NOTES = scale_notes(62, "hijaz_kar", 1)          # D4 hijaz kar
mel_pat = euclid(5, 12)
mel = np.zeros((L.n, 2))
walk = [0, 2, 4, 3, 5, 6, 4, 7, 5, 3, 2, 1]
wi = 0
for bar in range(BARS):
    if bar in (0, 7):
        continue
    for k, tb in enumerate(onsets(mel_pat, (4.0 / 12))):
        midi = NOTES[walk[wi % len(walk)] % len(NOTES)]
        wi += 1
        p = pluck(hz(midi), 1.4, amp=0.24, t60=1.8, seed=midi + bar)
        at_s = (bar * 4 + tb) * spb
        c = stereo(p, 0.3 if k % 2 else -0.2)
        idx = (int(at_s * SR) + np.arange(len(c))) % L.n
        np.add.at(mel, idx, c)

L.buf += duck(mel, kick_tr, amount_db=5.0, release_ms=120.0)
L.buf += drums
out = limiter(L.master(10500.0, drive=1.4), ceiling=0.92)
write_wav(os.path.join(outdir, "e13_clockwork.wav"), out)
print(" ", seam_report(out))
print("  onsets/bar:", counts, "(design k of each euclid)")

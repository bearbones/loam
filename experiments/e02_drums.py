#!/usr/bin/env python3
"""e02 — the drum kit. Every voice fired once for inspection, then
an 8-bar groove loop @ 102 BPM using the whole kit.

    python3 experiments/e02_drums.py [outdir]
"""

import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))))
from loam import SR, Loop, stereo, write_wav, seam_report
from loam import drums as dr

outdir = sys.argv[1] if len(sys.argv) > 1 else "render"
os.makedirs(outdir, exist_ok=True)

# --- inspection: one of each, spectral centroid + length ------------
def centroid(x):
    sp = np.abs(np.fft.rfft(x))
    f = np.fft.rfftfreq(len(x), 1 / SR)
    return float((sp * f).sum() / (sp.sum() + 1e-12))

VOICES = [("kick", dr.kick()), ("snare", dr.snare()),
        ("hat", dr.hat()), ("openhat", dr.hat(open_=True)),
        ("clap", dr.clap()), ("tom", dr.tom()),
        ("conga", dr.conga()), ("cowbell", dr.cowbell()),
        ("rim", dr.rim()), ("shaker", dr.shaker())]
for name, v in VOICES:
    print(f"  {name:8s} len={len(v)/SR:.3f}s peak={np.abs(v).max():.2f} "
          f"centroid={centroid(v):6.0f} Hz")

# --- the groove -----------------------------------------------------
BPM, BARS = 102.0, 8
spb = 60.0 / BPM
L = Loop(BARS * 4 * spb, 0xD2)
e8 = spb / 2

for bar in range(BARS):
    b0 = bar * 4 * spb
    L.add(b0, stereo(dr.kick(), 0.0))
    L.add(b0 + 2 * spb, stereo(dr.kick(amp=0.8), 0.0))
    if bar % 4 == 3:
        L.add(b0 + 3.5 * spb, stereo(dr.kick(amp=0.55), 0.0))
    L.add(b0 + 1 * spb, stereo(dr.snare(seed=10 + bar), 0.08))
    L.add(b0 + 3 * spb, stereo(dr.clap(seed=20 + bar) * 0.8, -0.08))
    for e in range(8):
        hp = 0.85 if e % 2 else -0.85        # alternate hard L/R
        if e == 6 and bar % 2 == 1:
            L.add(b0 + e * e8, stereo(dr.hat(open_=True,
                    seed=30 + e + 8 * bar) * 0.5, hp))
        else:
            g = 0.5 if e % 2 else 0.72
            L.add(b0 + e * e8, stereo(dr.hat(
                    seed=30 + e + 8 * bar) * g, hp))
        L.add(b0 + e * e8 + e8 / 2, stereo(dr.shaker(
                seed=40 + e + 8 * bar) * 0.30, -hp))
    if bar % 4 == 2:
        L.add(b0 + 1.5 * spb, stereo(dr.rim() * 0.5, -0.2))
        L.add(b0 + 2.75 * spb, stereo(dr.conga(seed=50 + bar) * 0.5,
                0.45))
        L.add(b0 + 3.25 * spb, stereo(dr.conga(160.0,
                seed=60 + bar) * 0.45, -0.45))
    if bar == 7:
        L.add(b0 + 3.0 * spb, stereo(dr.tom(150) * 0.6, 0.3))
        L.add(b0 + 3.5 * spb, stereo(dr.tom(95) * 0.65, -0.3))
        L.add(b0 + 2.5 * spb, stereo(dr.cowbell() * 0.35, 0.1))

out = L.master(11000.0, drive=1.5)
write_wav(os.path.join(outdir, "e02_groove.wav"), out)
print(" ", seam_report(out))
hi = np.fft.rfft(out, axis=0)
f = np.fft.rfftfreq(len(out), 1 / SR)
hi[f < 250] = 0.0
w = np.fft.irfft(hi, len(out), axis=0)
print(f"  stereo corr >250Hz: "
      f"{float(np.corrcoef(w[:, 0], w[:, 1])[0, 1]):+.3f}")

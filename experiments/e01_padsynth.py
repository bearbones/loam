#!/usr/bin/env python3
"""e01 — PADsynth proof. A D minor pad and an 'ah' choir on the same
loop length; verify: seam is exactly zero, L/R decorrelated, energy
sits where the harmonics were painted.

    python3 experiments/e01_padsynth.py [outdir]
"""

import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))))
from loam import SR, hz, write_wav, seam_report
from loam.pads import padsynth_stereo, saw_amps, formant_amps, VOWELS

outdir = sys.argv[1] if len(sys.argv) > 1 else "render"
os.makedirs(outdir, exist_ok=True)
LOOP_S = 12.0

# --- 1. Dm chord pad: three padsynth notes summed -------------------
pad = np.zeros((int(LOOP_S * SR), 2))
for i, (midi, g) in enumerate([(50, 1.0), (53, 0.8), (57, 0.8),
        (62, 0.5)]):
    pad += padsynth_stereo(LOOP_S, hz(midi), saw_amps(24, 1.4),
            bw_cents=35.0, bwscale=1.0, seed=100 + 7 * i) * g
pad *= 0.55 / np.max(np.abs(pad))
write_wav(os.path.join(outdir, "e01_pad.wav"), pad)
print(" ", seam_report(pad))

# --- 2. 'ah' choir on D3+D4: formant-shaped harmonics ---------------
choir = np.zeros((int(LOOP_S * SR), 2))
for i, (midi, g) in enumerate([(50, 1.0), (57, 0.55), (62, 0.6)]):
    f0 = hz(midi)
    choir += padsynth_stereo(LOOP_S, f0,
            formant_amps(f0, 60, VOWELS["ah"]),
            bw_cents=55.0, bwscale=1.0, seed=200 + 11 * i) * g
choir *= 0.55 / np.max(np.abs(choir))
write_wav(os.path.join(outdir, "e01_choir_ah.wav"), choir)
print(" ", seam_report(choir))

# --- numbers --------------------------------------------------------
for name, sig in [("pad", pad), ("choir", choir)]:
    corr = float(np.corrcoef(sig[:, 0], sig[:, 1])[0, 1])
    spec = np.abs(np.fft.rfft(sig[:, 0]))
    peak_bin = int(np.argmax(spec))
    print(f"  {name}: L/R corr={corr:+.3f}  "
          f"spectral peak at {peak_bin / LOOP_S:.1f} Hz")

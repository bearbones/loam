#!/usr/bin/env python3
"""e05 — modulation effects proof.

    python3 experiments/e05_mod.py [outdir]
"""

import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))))
from loam import SR, hz, write_wav, seam_report
from loam.pads import padsynth_table, saw_amps
from loam.mod import chorus, flanger, phaser

outdir = sys.argv[1] if len(sys.argv) > 1 else "render"
os.makedirs(outdir, exist_ok=True)
LOOP_S = 10.0
rng = np.random.default_rng(5)


def corr(s):
    return float(np.corrcoef(s[:, 0], s[:, 1])[0, 1])


def contrast(s, lo=300, hi=3000):
    """max/min dB spread of the band in a 50ms window."""
    seg = s[SR: SR + int(0.05 * SR), 0]
    sp = np.abs(np.fft.rfft(seg * np.hanning(len(seg))))
    f = np.fft.rfftfreq(len(seg), 1 / SR)
    band = sp[(f > lo) & (f < hi)]
    return 20 * np.log10(band.max() / (band.min() + 1e-12))


# 1. chorus: mono pad -> ensemble
pad = padsynth_table(LOOP_S, hz(50), saw_amps(20, 1.3), seed=42)
mono2 = np.stack([pad, pad], axis=1) * 0.5
ch = chorus(mono2, LOOP_S, mix=0.6)
print(f"chorus: corr {corr(mono2):+.3f} -> {corr(ch):+.3f}; "
      + seam_report(ch))
write_wav(os.path.join(outdir, "e05_chorus.wav"),
        ch * 0.8 / np.max(np.abs(ch)))

# 2. flanger on noise: a comb MUST leave an autocorrelation peak
# at its delay lag (spectral contrast on 50ms of noise is ~30 dB
# of intrinsic variance — useless metric, measured and discarded)
nz = rng.standard_normal((int(LOOP_S * SR), 2)) * 0.2
fl = flanger(nz, LOOP_S)


def ac_peak(s, lo_ms=0.4, hi_ms=3.0):
    seg = s[SR: 3 * SR, 0]
    ac = np.correlate(seg, seg, "same")[len(seg) // 2:]
    ac /= ac[0]
    lo, hi = int(lo_ms * 1e-3 * SR), int(hi_ms * 1e-3 * SR)
    return float(np.max(np.abs(ac[lo:hi])))


print(f"flanger: autocorr peak in 0.4-3ms dry {ac_peak(nz):.3f} "
      f"-> wet {ac_peak(fl):.3f} (comb signature)")

# 3. phaser: notches + allpass energy conservation
phn = phaser(nz, LOOP_S, mix=0.5)
pure = phaser(nz, LOOP_S, mix=1.0, feedback=0.0)
print(f"phaser: contrast dry {contrast(nz):.1f} dB -> wet "
      f"{contrast(phn):.1f} dB; allpass rms ratio "
      f"{np.sqrt((pure**2).mean())/np.sqrt((nz**2).mean()):.3f} "
      f"(want ~1)")

# 4. audible demo: pad dry->chorus->phaser, drums->flanger
from loam import Loop, stereo
from loam import drums as dr
L = Loop(16.0, 0xE05)
seg = np.stack([pad, pad], axis=1) * 0.4
L.buf[: L.n // 2] += chorus(seg, LOOP_S, mix=0.65)[: L.n // 2]
L.buf[L.n // 2:] += phaser(chorus(seg, LOOP_S, mix=0.65), LOOP_S,
        mix=0.6)[: L.n - L.n // 2]
spb = 60.0 / 100.0
groove = np.zeros((L.n, 2))
for bar in range(int(16.0 / (4 * spb))):
    b0 = bar * 4 * spb
    for beat, v, p in [(0.0, dr.kick(), 0), (1.0, dr.snare(seed=bar), 0.1),
            (2.0, dr.kick(amp=0.8), 0), (3.0, dr.clap(seed=bar) * 0.7, -0.1),
            (0.5, dr.hat(seed=bar) * 0.5, 0.6), (1.5, dr.hat(seed=bar + 1) * 0.5, -0.6),
            (2.5, dr.hat(seed=bar + 2) * 0.5, 0.6), (3.5, dr.hat(seed=bar + 3) * 0.5, -0.6)]:
        at = int((b0 + beat * spb) * SR)
        c = stereo(v, p)
        end = min(at + len(c), L.n)
        groove[at:end] += c[: end - at]
L.buf += flanger(groove, 16.0, feedback=0.62, mix=0.45) * 0.9
out = L.master(9500.0, drive=1.4)
write_wav(os.path.join(outdir, "e05_swim.wav"), out)
print(" ", seam_report(out))

#!/usr/bin/env python3
"""e08 — virtual analog demo: acid bassline (pulse -> swept ladder,
self-oscillation squeal on the peak), supersaw pad, drums.

    python3 experiments/e08_acid.py [outdir]
"""

import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))))
from loam import SR, hz, Loop, stereo, write_wav, seam_report
from loam.analog import pulse, supersaw, ladder
from loam.dyn import duck, limiter
from loam import drums as dr

outdir = sys.argv[1] if len(sys.argv) > 1 else "render"
os.makedirs(outdir, exist_ok=True)
BPM = 128.0
spb = 60.0 / BPM
BARS = 8
LOOP_S = BARS * 4 * spb
L = Loop(LOOP_S, 0xAC1D)

# acid line: 16th pattern in D minor, accent = cutoff + res kick
PAT = [(50, 1), (50, 0), (62, 1), (50, 0), (53, 1), (50, 0), (57, 1),
       (55, 0), (50, 1), (50, 0), (61, 1), (62, 0), (50, 1), (65, 1),
       (57, 0), (48, 1)]
bass = np.zeros(L.n)
e16 = spb / 4
for bar in range(BARS):
    openness = bar / (BARS - 1)          # filter opens over the loop
    for s, (midi, acc) in enumerate(PAT):
        at = bar * 4 * spb + s * e16
        ndur = e16 * (1.6 if acc else 0.9)
        n = int(ndur * SR)
        v = pulse(hz(midi - 12), ndur, width=0.62)
        tt = np.arange(n) / SR
        fc = (300 + 2600 * openness * (1.0 if acc else 0.45)) \
            * np.exp(-tt * 9.0) + 120
        w = ladder(v, fc, res=0.88 + 0.1 * openness, drive=1.6)
        env = np.ones(n)
        r = max(int(0.012 * SR), 1)
        env[-r:] = np.linspace(1, 0, r)
        idx = (int(at * SR) + np.arange(n)) % L.n
        np.add.at(bass, idx, w * env * (0.5 if acc else 0.34))
bass_st = np.stack([bass, bass], axis=1)

# supersaw pad: Dm -> Bb, half-loop each, seam-safe quantized
pad = np.zeros((L.n, 2))
for midi, g in [(50, 0.5), (53, 0.45), (57, 0.4), (62, 0.3)]:
    pad += supersaw(hz(midi), LOOP_S, loop_s=LOOP_S,
            seed=midi) * g * 0.16
w_b = 0.5 - 0.5 * np.cos(2 * np.pi * np.arange(L.n) / L.n)
pad2 = np.zeros((L.n, 2))
for midi, g in [(46, 0.5), (53, 0.45), (58, 0.4), (65, 0.25)]:
    pad2 += supersaw(hz(midi), LOOP_S, loop_s=LOOP_S,
            seed=midi + 50) * g * 0.16
pad = pad * (1 - w_b)[:, None] + pad2 * w_b[:, None]

# drums
kick_tr = np.zeros(L.n)
drums = np.zeros((L.n, 2))
for bar in range(BARS):
    b0 = bar * 4 * spb
    for beat in range(4):
        v = dr.kick(f1=46.0)
        at = int((b0 + beat * spb) * SR)
        end = min(at + len(v), L.n)
        kick_tr[at:end] += v[: end - at]
    for e in range(8):
        h = dr.hat(seed=e + 8 * bar, open_=(e == 7 and bar % 2 == 1))
        at = int((b0 + e * spb / 2) * SR)
        c = stereo(h * (0.42 if e % 2 else 0.3), 0.75 if e % 2 else -0.75)
        end = min(at + len(c), L.n)
        drums[at:end] += c[: end - at]
    if bar % 2 == 1:
        at = int((b0 + 3 * spb) * SR)
        c = stereo(dr.clap(seed=bar) * 0.6, 0.1)
        drums[at: min(at + len(c), L.n)] += c[: L.n - at][: len(c)]
drums[:, 0] += kick_tr
drums[:, 1] += kick_tr

L.buf += duck(pad, kick_tr, amount_db=7.0, release_ms=150.0)
L.buf += duck(bass_st, kick_tr, amount_db=5.0, release_ms=90.0)
L.buf += drums * 0.85
out = limiter(L.master(11000.0, drive=1.35), ceiling=0.93)
write_wav(os.path.join(outdir, "e08_acid.wav"), out)
print(" ", seam_report(out))
hi = np.fft.rfft(out, axis=0)
fr = np.fft.rfftfreq(len(out), 1 / SR)
hi[fr < 250] = 0
w = np.fft.irfft(hi, len(out), axis=0)
print(f"  stereo corr >250Hz: {float(np.corrcoef(w[:,0], w[:,1])[0,1]):+.3f}"
      f"; peak {np.abs(out).max():.3f}")

#!/usr/bin/env python3
"""e06 — sympathetic string bank proof.

1. One click in -> peaks at exactly the tuned frequencies.
2. Selectivity: a D pluck wakes the D string ~more than the Eb
   string one semitone away.
3. Demo: drum groove + psaltery through a D-minor taraf; seam.

    python3 experiments/e06_sympathetic.py [outdir]
"""

import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))))
from loam import SR, hz, Loop, stereo, write_wav, seam_report
from loam.strings import pluck, sympathetic
from loam import drums as dr

outdir = sys.argv[1] if len(sys.argv) > 1 else "render"
os.makedirs(outdir, exist_ok=True)
TARAF = [50, 53, 57, 62, 65, 69, 74]      # D minor spread

# 1. click -> tuned peaks
click = np.zeros((4 * SR, 2))
click[100] = 1.0
ring = sympathetic(click, TARAF, mix=1.0, loop=False)
sp = np.abs(np.fft.rfft(ring[SR // 2:, 0]))
f = np.fft.rfftfreq(len(ring) - SR // 2, 1 / SR)
print("click response peaks at tuned strings:")
floor = np.median(sp)
for midi in TARAF:
    k = np.argmin(np.abs(f - hz(midi)))
    win = sp[max(k - 3, 0): k + 4].max()
    print(f"  midi {midi} ({hz(midi):6.1f} Hz): {20*np.log10(win/floor):5.1f} dB above floor")

# 2. selectivity
d_note = pluck(hz(62), 1.5, seed=1)
eb_note = pluck(hz(63), 1.5, seed=1)


def band_energy(sig, f0, halftones=0.4):
    s = np.abs(np.fft.rfft(sig[:, 0]))
    fr = np.fft.rfftfreq(len(sig), 1 / SR)
    m = (fr > f0 * 2 ** (-halftones / 12)) & (fr < f0 * 2 ** (halftones / 12))
    return float((s[m] ** 2).sum())


pad_z = np.zeros(2 * SR)
d_in = np.concatenate([d_note, pad_z])
e_in = np.concatenate([eb_note, pad_z])
rd = sympathetic(np.stack([d_in, d_in], 1), [62], mix=1.0, loop=False,
        norm=False)
re = sympathetic(np.stack([e_in, e_in], 1), [62], mix=1.0, loop=False,
        norm=False)
tail_d = rd[int(1.6 * SR):]
tail_e = re[int(1.6 * SR):]
ed, ee = (tail_d ** 2).sum(), (tail_e ** 2).sum()
print(f"D-string ring tail: D pluck {ed:.2e} vs Eb pluck {ee:.2e} "
      f"(ratio {ed/max(ee,1e-12):.1f}x — resonance selectivity)")

# 3. demo loop
L = Loop(16.0, 0xE06)
spb = 60.0 / 96.0
groove = np.zeros((L.n, 2))
for bar in range(int(16.0 / (4 * spb))):
    b0 = bar * 4 * spb
    for beat, v, p in [(0.0, dr.kick(), 0), (2.0, dr.kick(amp=0.75), 0),
            (1.0, dr.snare(seed=bar), 0.08), (3.0, dr.rim() * 0.6, -0.2),
            (0.5, dr.hat(seed=bar) * 0.4, 0.7), (1.5, dr.hat(seed=bar + 4) * 0.4, -0.7),
            (2.5, dr.hat(seed=bar + 8) * 0.4, 0.7), (3.5, dr.hat(seed=bar + 12) * 0.4, -0.7)]:
        at = int((b0 + beat * spb) * SR)
        c = stereo(v, p)
        end = min(at + len(c), L.n)
        groove[at:end] += c[: end - at] * 0.8
pl = np.zeros((L.n, 2))
for bar, beat, midi in [(0, 0, 62), (1, 2, 65), (2, 0, 69), (3, 2, 74),
        (4, 0, 70), (5, 2, 67), (6, 0, 65), (7, 0, 62)]:
    v = pluck(hz(midi), 2.2, amp=0.5, seed=midi)
    at = int((bar * 4 + beat) * spb * SR) % L.n
    c = stereo(v, 0.2 if bar % 2 else -0.2)
    idx = (at + np.arange(len(c))) % L.n
    np.add.at(pl, idx, c)
L.buf += sympathetic(groove + pl, TARAF, t60=2.6, coupling=0.15,
        mix=0.45)
out = L.master(9000.0, drive=1.4)
write_wav(os.path.join(outdir, "e06_taraf.wav"), out)
print(" ", seam_report(out))
hi = np.fft.rfft(out, axis=0)
fr = np.fft.rfftfreq(len(out), 1 / SR)
hi[fr < 250] = 0
w = np.fft.irfft(hi, len(out), axis=0)
print(f"  stereo corr >250Hz: {float(np.corrcoef(w[:,0], w[:,1])[0,1]):+.3f}")

#!/usr/bin/env python3
"""e11 — sidebands. A psaltery phrase plays dry (bars 1-2), then
frequency-shifted +44 Hz into bell-ghosts (bars 3-4), over a
barberpole wash that rises forever underneath.

    python3 experiments/e11_barber.py [outdir]
"""

import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))))
from loam import SR, hz, Loop, stereo, write_wav, seam_report
from loam.pads import padsynth_stereo, saw_amps
from loam.strings import pluck
from loam.shift import freq_shift, barber
from loam.dyn import limiter

outdir = sys.argv[1] if len(sys.argv) > 1 else "render"
os.makedirs(outdir, exist_ok=True)
LOOP_S = 20.0
L = Loop(LOOP_S, 0xE11)

# the rising floor: dark pad through the barberpole
pad = np.zeros((L.n, 2))
for i, (midi, g) in enumerate([(38, 1.0), (50, 0.8), (57, 0.6)]):
    pad += padsynth_stereo(LOOP_S, hz(midi), saw_amps(16, 1.7),
            bw_cents=30.0, seed=700 + i) * g * 0.12
L.buf += barber(pad, LOOP_S, shift_hz=4.0, delay_s=0.31,
        feedback=0.8, mix=0.55)

# the phrase: twice — dry, then shifted into inharmonic ghosts
PHRASE = [(0.0, 62), (0.9, 65), (1.8, 69), (2.7, 74), (3.8, 70),
          (4.7, 65), (5.6, 62)]
stem = np.zeros((int(9.0 * SR), 2))
for at, midi in PHRASE:
    p = pluck(hz(midi), 2.2, amp=0.42, seed=midi)
    i0 = int(at * SR)
    end = min(i0 + len(p), len(stem))
    stem[i0:end] += stereo(p, 0.18 if midi % 2 else -0.18)[: end - i0]


def addw(buf, at_s, chunk):
    idx = (int(at_s * SR) + np.arange(len(chunk))) % len(buf)
    np.add.at(buf, idx, chunk)


addw(L.buf, 0.5, stem)
addw(L.buf, 10.5, freq_shift(stem, 44.0) * 0.9)

out = limiter(L.master(7800.0, drive=1.35), ceiling=0.92)
write_wav(os.path.join(outdir, "e11_barber.wav"), out)
print(" ", seam_report(out))
# ghost check: shifted phrase partials sit off the harmonic grid
seg = out[int(11.0 * SR): int(13.0 * SR), 0]
sp = np.abs(np.fft.rfft(seg * np.hanning(len(seg))))
fr = np.fft.rfftfreq(len(seg), 1 / SR)
top = fr[np.argsort(sp)[-6:]]
print("  loudest partials 11-13s:",
      sorted(round(float(v), 1) for v in top))

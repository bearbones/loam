#!/usr/bin/env python3
"""e12 — the hermit's record. Tonight's vocalise (e09) plays dry;
at 9s the needle drops and the rest arrives through a gramophone.

    python3 experiments/e12_record.py [outdir]
"""

import os
import sys
import wave

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))))
from loam import SR, write_wav
from loam.lofi import gramophone

outdir = sys.argv[1] if len(sys.argv) > 1 else "render"
src_path = os.path.join(outdir, "e09_vocalise.wav")
with wave.open(src_path) as w:
    x = np.frombuffer(w.readframes(w.getnframes()),
            np.int16).reshape(-1, 2) / 32767.0

loop_s = len(x) / SR
g = gramophone(x, loop_s=loop_s, seed=9)
xf_at, xf_len = int(9.0 * SR), int(0.4 * SR)
xf = np.zeros(len(x))
xf[xf_at: xf_at + xf_len] = np.linspace(0, 1, xf_len)
xf[xf_at + xf_len:] = 1.0
out = x * (1 - xf)[:, None] + g * xf[:, None]
out *= 0.9 / np.max(np.abs(out))
write_wav(os.path.join(outdir, "e12_record.wav"), out)
d_rms = float(np.sqrt((out[int(3*SR):int(8*SR)] ** 2).mean()))
g_rms = float(np.sqrt((out[int(12*SR):int(20*SR)] ** 2).mean()))
hi = np.abs(np.fft.rfft(out[int(12*SR):int(20*SR), 0]))
fr = np.fft.rfftfreq(8 * SR, 1 / SR)
funnel = 10 * np.log10((hi[(fr>1000)&(fr<3000)]**2).mean()
        / (hi[(fr>7000)&(fr<11000)]**2).mean())
print(f"  dry rms {d_rms:.3f} vs record rms {g_rms:.3f}; "
      f"record band funnel {funnel:.0f} dB (1-3k over 7-11k)")

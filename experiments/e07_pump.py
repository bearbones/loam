#!/usr/bin/env python3
"""e07 — dynamics demo: the sidechain pump. Four-on-the-floor kick
ducks a padsynth chord + sub bass; transient-shaped hats; limiter
on the bus. First half NO duck, second half ducked — A/B in one
loop.

    python3 experiments/e07_pump.py [outdir]
"""

import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))))
from loam import SR, hz, Loop, stereo, write_wav, seam_report
from loam.pads import padsynth_stereo, saw_amps
from loam.dyn import duck, transient, limiter
from loam import drums as dr

outdir = sys.argv[1] if len(sys.argv) > 1 else "render"
os.makedirs(outdir, exist_ok=True)
BPM = 122.0
spb = 60.0 / BPM
BARS = 8
LOOP_S = BARS * 4 * spb
L = Loop(LOOP_S, 0xE07)

pad = np.zeros((L.n, 2))
for i, (midi, g) in enumerate([(38, 0.9), (50, 1.0), (53, 0.8),
        (57, 0.75), (60, 0.5)]):
    pad += padsynth_stereo(LOOP_S, hz(midi), saw_amps(18, 1.5),
            bw_cents=30.0, seed=500 + 3 * i) * g * 0.11

kick_track = np.zeros(L.n)
drums = np.zeros((L.n, 2))
for bar in range(BARS):
    b0 = bar * 4 * spb
    for beat in range(4):
        v = dr.kick(f1=48.0)
        at = int((b0 + beat * spb) * SR)
        end = min(at + len(v), L.n)
        kick_track[at:end] += v[: end - at]
        if beat in (1, 3):
            c = stereo(dr.clap(seed=bar * 4 + beat) * 0.55, 0.1)
            drums[at: min(at + len(c), L.n)] += c[: L.n - at][: len(c)]
    for e in range(8):
        h = transient(dr.hat(seed=e + 8 * bar), attack_db=5.0) * 0.4
        at = int((b0 + e * spb / 2) * SR)
        c = stereo(h, 0.7 if e % 2 else -0.7)
        end = min(at + len(c), L.n)
        drums[at:end] += c[: end - at]
drums[:, 0] += kick_track
drums[:, 1] += kick_track

# duck ONLY the second half — audible A/B across one loop
half = L.n // 2
ducked = duck(pad, kick_track, amount_db=10.0, release_ms=180.0)
xf = np.clip((np.arange(L.n) - half) / (0.05 * SR), 0, 1)[:, None]
L.buf += pad * (1 - xf) + ducked * xf
L.buf += drums * 0.8
out = limiter(L.master(10000.0, drive=1.3), ceiling=0.92)
write_wav(os.path.join(outdir, "e07_pump.wav"), out)
print(" ", seam_report(out))
# measure the PAD BUS, not the mix — in the mix the kick owns the
# very windows where the duck acts and buries the comparison
kw = int(0.12 * SR)
kts = [int((bar * 4 + beat) * spb * SR) + 800
        for bar in range(BARS) for beat in range(4)]
rp = np.sqrt(np.mean([float((pad[k: k + kw] ** 2).mean())
        for k in kts]))
rd = np.sqrt(np.mean([float((ducked[k: k + kw] ** 2).mean())
        for k in kts]))
print(f"  pad bus at kick windows: dry {rp:.4f} vs ducked {rd:.4f} "
      f"({20*np.log10(rd/rp):.1f} dB); peak {np.abs(out).max():.3f}")

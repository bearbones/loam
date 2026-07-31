#!/usr/bin/env python3
"""e03 — spectral surgery proof.

1. FREEZE a church bell 0.4s into its ring -> 12s drone loop.
   Verify: windowed RMS stays flat, seam clean.
2. STRETCH a pluck 6x. Verify: duration ratio, pitch unchanged.
3. CROSS-SYNTH: choir magnitudes on drum-groove phases.
   Verify: output envelope tracks the drums, spectrum tracks choir.

    python3 experiments/e03_spectral.py [outdir]
"""

import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))))
from loam import SR, hz, stereo, write_wav, seam_report
from loam.modal import strike, CHURCH_BELL
from loam.strings import pluck
from loam.pads import padsynth_stereo, formant_amps, VOWELS
from loam.spectral import freeze, stretch, cross_synth
from loam import drums as dr

outdir = sys.argv[1] if len(sys.argv) > 1 else "render"
os.makedirs(outdir, exist_ok=True)


def f_peak(x, lo=40):
    sp = np.abs(np.fft.rfft(x))
    f = np.fft.rfftfreq(len(x), 1 / SR)
    sp[f < lo] = 0
    return float(f[np.argmax(sp)])


# --- 1. bell freeze -------------------------------------------------
bell = strike(hz(50), 5.0, CHURCH_BELL,
        rng=np.random.default_rng(3), knock=0.1)
fro = freeze(bell, 0.4, 12.0, jitter=0.3, seed=9)
frz = np.stack([freeze(bell, 0.4, 12.0, jitter=0.3, seed=9),
        freeze(bell, 0.4, 12.0, jitter=0.3, seed=10)], axis=1) * 0.6
write_wav(os.path.join(outdir, "e03_freeze.wav"), frz)
w = SR // 2
rms = [float(np.sqrt((frz[i:i + w] ** 2).mean()))
        for i in range(0, len(frz) - w, w)]
print(f"  freeze RMS flatness: mean={np.mean(rms):.3f} "
      f"std={np.std(rms):.4f}  ", seam_report(frz))

# --- 2. pluck stretch ----------------------------------------------
p = pluck(hz(62), 1.2, t60=1.0, seed=4)
st = stretch(p, 6.0)
print(f"  stretch: in {len(p)/SR:.2f}s -> out {len(st)/SR:.2f}s "
      f"(x{len(st)/len(p):.2f}, want ~6); pitch {f_peak(p):.1f} -> "
      f"{f_peak(st):.1f} Hz")
write_wav(os.path.join(outdir, "e03_stretch.wav"),
        np.stack([st, st], axis=1) * 0.7)

# --- 3. choir x drums ----------------------------------------------
LOOP_S = 4 * 60.0 / 102.0 * 4
f0 = hz(50)
choir = padsynth_stereo(LOOP_S, f0, formant_amps(f0, 48, VOWELS["ah"]),
        bw_cents=50.0, seed=77).mean(axis=1)
groove = np.zeros(int(LOOP_S * SR))
spb = 60.0 / 102.0
for bar in range(4):
    b0 = bar * 4 * spb
    for beat, v in [(0.0, dr.kick()), (1.0, dr.snare(seed=bar)),
            (2.0, dr.kick(amp=0.8)), (3.0, dr.clap(seed=bar)),
            (1.5, dr.hat(seed=bar) * 0.7), (2.5, dr.hat(seed=bar + 9) * 0.7),
            (3.5, dr.hat(open_=True, seed=bar) * 0.5)]:
        at = int((b0 + beat * spb) * SR)
        groove[at:at + len(v)] += v[: max(0, len(groove) - at)]
talk = cross_synth(choir, groove, whiten=0.7, punch=1.2)
write_wav(os.path.join(outdir, "e03_talkroom.wav"),
        np.stack([talk, talk], axis=1) * 0.8)


def env_of(x, w=2048):
    k = len(x) // w
    return np.array([(x[i * w:(i + 1) * w] ** 2).mean()
            for i in range(k)])


ea, eb = env_of(talk), env_of(groove[: len(talk)])
k = min(len(ea), len(eb))
print(f"  cross-synth envelope corr vs drums: "
      f"{float(np.corrcoef(ea[:k], eb[:k])[0, 1]):+.3f} "
      f"(want high); spectral peak {f_peak(talk):.0f} Hz "
      f"(choir formant zone, want ~600-800)")

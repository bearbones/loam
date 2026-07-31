#!/usr/bin/env python3
"""loam — "Reliquary" (spin-off day). Where the grafts sleep.

72s seamless loop, D aeolian, 60 BPM. A showcase for the new kit:

- PADsynth choir bed (formant 'oh' <-> 'ah', circular crossfade —
  the room slowly opens its mouth), decorrelated stereo by phase.
- Church bells (modal; the 1.2-ratio tierce supplies the minor
  third all by itself) into the FDN reverb.
- Psaltery (Karplus-Strong) speaking ONE sentence mid-loop, per
  the standing grammar: cadence = full stop, rest, then the low
  answer in its own bars. Dotted-eighth circular tape echo.
- Bowed glass swells on the color tones.
- Wavefolded D2 drone breathing on a cycle-quantized LFO.
- Grain shimmer (+12/+19) of the bell bus, faint, in the reverb.

    python3 songs/reliquary.py [outdir]
"""

import os
import sys

import numpy as np
from scipy.signal import butter

sys.path.insert(0, os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))))
from loam import SR, hz, Loop, stereo, write_wav, seam_report
from loam.pads import padsynth_stereo, formant_amps, VOWELS
from loam.modal import strike, bow, CHURCH_BELL, GLASS
from loam.strings import pluck
from loam.space import reverb_loop, tape_echo_loop
from loam.shape import wavefold
from loam.grain import cloud

BPM, BARS = 60.0, 18
spb = 60.0 / BPM
LOOP_S = BARS * 4 * spb          # 72.0
L = Loop(LOOP_S, 0x2E11C)


def bt(bar: float, beat: float = 0.0) -> float:
    return (bar * 4 + beat) * spb


def addw(buf: np.ndarray, at_s: float, chunk: np.ndarray) -> None:
    idx = (int(at_s * SR) + np.arange(len(chunk))) % len(buf)
    np.add.at(buf, idx, chunk)


# ---- 1. Choir bed: 'oh' at the seam, 'ah' mid-loop -----------------
NOTES = [(38, 0.9), (50, 1.0), (57, 0.7), (62, 0.55)]   # D1 D3 A3 D4
w_ah = 0.5 - 0.5 * np.cos(2 * np.pi * L.t / LOOP_S)      # 0 at seam
for i, (midi, g) in enumerate(NOTES):
    f0 = hz(midi)
    oh = padsynth_stereo(LOOP_S, f0, formant_amps(f0, 48, VOWELS["oh"]),
            bw_cents=45.0, seed=300 + 13 * i)
    ah = padsynth_stereo(LOOP_S, f0, formant_amps(f0, 48, VOWELS["ah"]),
            bw_cents=45.0, seed=400 + 13 * i)
    L.buf += (oh * (1 - w_ah)[:, None] + ah * w_ah[:, None]) * 0.075 * g

# ---- 2. Folded drone: D2, drive breathing over 24s -----------------
drone_src = np.sin(2 * np.pi * L.q(hz(38)) * L.t)
drive = 1.15 + 0.75 * np.sin(2 * np.pi * L.t / (LOOP_S / 3.0))
folded = wavefold(drone_src, drive)
sos_dr = butter(2, 700, btype="low", fs=SR, output="sos")
folded = L.filt_circular(sos_dr, np.stack([folded, folded], axis=1))
L.buf += folded * 0.045

# ---- 3. Bells into their own bus -----------------------------------
bus = np.zeros((L.n, 2))
BELLS = [(0, 50, 0.55, 0.0), (4, 45, 0.40, -0.3), (8, 53, 0.34, 0.3),
         (12, 45, 0.38, -0.2), (16, 38, 0.50, 0.0)]
for bar, midi, amp, pan in BELLS:
    b = strike(hz(midi), 6.5, CHURCH_BELL, amp=amp, bright=0.92,
            detune=3.0, rng=L.rng, knock=0.10)
    addw(bus, bt(bar), stereo(b, pan))

# ---- 4. Psaltery sentence (the one voice that speaks) --------------
# S1 bars 8-10, cadence held, bar 11 RESTS. Low answer bars 13-15,
# bar 16-17 rest into the wrap. Signature: the drop G->D (a 4th).
S1 = [
    (8, 0.0, 69, 0.24), (8, 0.5, 67, 0.18), (8, 1.0, 65, 0.20),
    (8, 2.0, 62, 0.20), (8, 3.0, 65, 0.18),
    (9, 0.0, 67, 0.22), (9, 1.5, 69, 0.18), (9, 2.0, 70, 0.24),
    (9, 3.0, 67, 0.18),
    (10, 0.0, 67, 0.20), (10, 1.0, 62, 0.26),        # G -> D: the sign
    (10, 2.0, 62, 0.0),                              # let it ring
]
pl_bus = np.zeros((L.n, 2))
for bar, beat, midi, amp in S1:
    if amp <= 0.0:
        continue
    p = pluck(hz(midi), 2.8, amp=amp, t60=2.6, damp=0.30, pick=0.18,
            soft=1, seed=midi * 7 + bar)
    addw(pl_bus, bt(bar, beat), stereo(p, 0.15))
for bar, beat, midi, amp in S1:                       # the low answer
    if amp <= 0.0:
        continue
    p = pluck(hz(midi - 12), 2.8, amp=amp * 0.55, t60=2.6, damp=0.45,
            pick=0.22, soft=2, seed=midi * 11 + bar)
    addw(pl_bus, bt(bar + 5, beat), stereo(p, -0.35))
pl_bus = tape_echo_loop(pl_bus, LOOP_S, spb * 0.75, feedback=0.42,
        damp_hz=2600.0, wow_hz=3.0 / LOOP_S * 3, mix=0.30)
bus += pl_bus

# ---- 5. Bowed glass: color swells in the rests ---------------------
for bar, midi, amp, pan in [(5.0, 69, 0.10, 0.4), (11.0, 74, 0.085, -0.4),
        (15.5, 70, 0.09, 0.35)]:
    g = bow(hz(midi), 3.6, GLASS, amp=amp, vib_hz=4.2, rng=L.rng)
    addw(bus, bt(bar), stereo(g, pan))

# ---- 6. Shimmer: grains of the bus, up an octave+, faint -----------
shimmer = cloud(bus.mean(axis=1), LOOP_S, density=9.0, grain_s=0.22,
        pitches=(12.0, 19.0), pan_spread=0.8, gain=0.05, seed=0x51)
bus += shimmer

# ---- 7. The room ---------------------------------------------------
bus = reverb_loop(bus, t60=3.4, size=1.25, damp_hz=3400.0, mix=0.42)
L.buf += bus

out = L.master(6800.0, drive=1.4)

outdir = sys.argv[1] if len(sys.argv) > 1 else "render"
os.makedirs(outdir, exist_ok=True)
write_wav(os.path.join(outdir, "reliquary.wav"), out)
print(" ", seam_report(out))
hi = np.fft.rfft(out, axis=0)
f = np.fft.rfftfreq(len(out), 1 / SR)
hi[f < 250] = 0.0
w = np.fft.irfft(hi, len(out), axis=0)
print(f"  stereo corr >250Hz: "
      f"{float(np.corrcoef(w[:, 0], w[:, 1])[0, 1]):+.3f}")

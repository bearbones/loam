#!/usr/bin/env python3
"""e36 — the treadmill: a Risset rhythm. barber() is the endless
pitch staircase; this is its rhythmic sibling — an accelerando
that gains one tempo-octave per loop and never arrives. Tempo
layers at octave spacing (rate R0*2^(k + t/T)) hand off under a
Gaussian loudness window in log-rate space; every per-hit property
(pitch, pan, duration, gain) is a pure function of the octave
position o = k + t/T, so layer k at the seam IS layer k+1 at bar
one. The layers are phase-locked by construction (layer k's hit n
coincides with layer k+1's hit 2n): one metric tree, forever
climbing. Underneath, a barber'd choir pad rises with it.

First customer of loam.ruler — the consolidated measurement kit.

    python3 experiments/e36_treadmill.py [outdir]
"""

import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))))
from loam import SR, hz, Loop, stereo, write_wav, seam_report
from loam import ruler
from loam.drums import tom
from loam.pads import padsynth_stereo, formant_amps, VOWELS
from loam.shift import barber
from loam.space import reverb_loop

outdir = sys.argv[1] if len(sys.argv) > 1 else "render"
os.makedirs(outdir, exist_ok=True)

R0 = 2.0                     # rate (Hz) at the loudness-window center
N = 72                       # window-center beats per loop (div. by 8)
T = N * np.log(2.0) / R0     # loop length: exactly one tempo octave
SIG = 1.1                    # loudness window width, octaves
KMIN, KMAX = -3, 2
L = Loop(T, 0xE36)


def gain_of(o):
    """Gaussian window in log-rate, times 2^(-o/2) so each stream's
    ENERGY density (rate * amp^2) is window-shaped, not rate-tilted."""
    return np.exp(-0.5 * (o / SIG) ** 2) * 2.0 ** (-o / 2.0)


def midi_of(o):
    return 45.0 + 12.0 * o   # pitch rides the rate: 110 Hz tom at center


def pan_of(o):
    return 0.65 * np.sin(2 * np.pi * o / 2.5)


layer_bus = {}
for k in range(KMIN, KMAX + 1):
    bus = np.zeros((L.n, 2))
    beats = int(round(N * 2.0 ** k))
    for n in range(beats):
        t = T * np.log2(1.0 + n / beats)
        o = k + t / T
        r = R0 * 2.0 ** o
        d = float(np.clip(0.9 / r, 0.12, 0.45))
        a = gain_of(o) * (1.3 if n % 4 == 0 else 1.0)
        m = tom(f0=hz(midi_of(o)), dur=d, seed=1000 * (k + 4) + n) * a
        ch = stereo(m, pan_of(o))
        idx = (int(t * SR) + np.arange(len(ch))) % L.n
        np.add.at(bus, idx, ch)
    layer_bus[k] = bus
    L.buf += bus * 0.55

pad = padsynth_stereo(T, hz(38.0), formant_amps(hz(38.0), 24,
        VOWELS["oh"]), seed=7)
pad /= np.max(np.abs(pad))
pad = barber(pad, T, shift_hz=2.2, mix=0.5)
L.buf += pad * 0.16

L.buf = reverb_loop(L.buf, t60=1.9, damp_hz=3800.0, mix=0.16)
mix = L.master(lp_hz=8000.0, drive=1.2)
write_wav(os.path.join(outdir, "e36_treadmill.wav"), mix)
print(seam_report(mix))
ruler.report(mix, "mix")

# ---- rulers -----------------------------------------------------
W = 6.0
nw = int(W * SR)
fails = []


def check(name, cond, detail):
    print(f"  {'PASS' if cond else 'FAIL'} {name}: {detail}")
    if not cond:
        fails.append(name)


def r_design(k, t):
    return R0 * 2.0 ** (k + t / T)


# 1. the loop seam is clickless
check("seam", ruler.seam_rank(mix) <= 0.999,
        f"rank=p{100 * ruler.seam_rank(mix):.1f}")

# 2. each audible layer accelerates to design, on its OWN bus
meas = {}
for k in (-1, 0, 1):
    for tag, seg, tc in (("early", layer_bus[k][:nw], W / 2),
                         ("late", layer_bus[k][-nw:], T - W / 2)):
        rd = r_design(k, tc)
        rm = ruler.pulse_rate(seg, 0.6 * rd, 1.6 * rd)
        meas[(k, tag)] = rm
        check(f"rate k={k} {tag}", 0.88 <= rm / rd <= 1.14,
                f"measured {rm:.2f}/s vs design {rd:.2f}/s")

# 3. the handoff: layer k ends where layer k+1 begins. The windows
#    straddle o = k+1 (late center sits BELOW it, early center
#    ABOVE), so the design ratio is 2^(-W/T) — first cut had it
#    inverted and blamed the sound for the ruler's sign error.
for k in (-1, 0):
    gap = meas[(k, "late")] / meas[(k + 1, "early")]
    rd = 2.0 ** (-W / T)
    check(f"handoff {k}->{k + 1}", 0.88 * rd <= gap <= 1.14 * rd,
            f"late/early = {gap:.3f} (design {rd:.3f})")

# 4. the mix is stationary — perpetual acceleration, flat loudness
contour = ruler.rms_contour(mix, 8)
spread = max(contour) - min(contour)
check("stationary", spread <= 3.0, f"RMS spread {spread:.2f} dB over 8 win")

# 5. aggregate percussive density holds (scale invariance): the
#    onset-band envelope carries equal energy in each half
e1 = float(np.sqrt(np.mean(ruler.onset_env(mix[:L.n // 2]) ** 2)))
e2 = float(np.sqrt(np.mean(ruler.onset_env(mix[L.n // 2:]) ** 2)))
check("density", 0.7 <= e1 / e2 <= 1.4, f"half ratio {e1 / e2:.3f}")

print("ALL RULERS PASS" if not fails else f"FAILED: {fails}")
sys.exit(1 if fails else 0)

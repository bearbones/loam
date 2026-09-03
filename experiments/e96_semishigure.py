#!/usr/bin/env python3
"""loam e96 — semishigure: cicada rain.

The last voice the niwa garden was waiting for. New in
texture.py: cicada() — the tymbal as a jittered click train
through the abdominal resonator (bandpass at f_c, width
f_c/q). The click RATE is the buzz; the resonator is the
species' formant; syllables are sung windows with sin^2
edges.

Two species, both written tables:

  - the ABURAZEMI bed: five continuous sizzlers (formants
    5250-5850 Hz, rates 80-93 Hz), each swelling on the ONE
    written chorus wave (4 cycles in the 30 s loop, phases
    staggered but coherent) — semishigure surges together;
  - a MINMIN-ZEMI soloist (formant 4300 Hz, rate 118 Hz)
    singing two phrases of written syllables:
    miiin, min min min min, miiiin.

Rate is measured with ruler.rate_contour on a FAST flux clock
(frame=256, hop=32): the default hop's 5.8 ms puts the flux
series' Nyquist at 86 Hz — under the click rate it would be
measuring. The ruler's sample rate is part of the claim
(e94's bandwidth lesson, rhythm edition).

    python3 experiments/e96_semishigure.py [outdir]
"""

import os
import sys

import numpy as np
from scipy.signal import butter, sosfilt

sys.path.insert(0, os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))))
from loam import SR, stereo, write_wav
from loam import ruler
from loam.texture import cicada, wind
from loam.space import reverb_loop

outdir = sys.argv[1] if len(sys.argv) > 1 else "render"
os.makedirs(outdir, exist_ok=True)
fails = []


def check(name, cond, detail):
    print(f"  {'PASS' if cond else 'FAIL'} {name}: {detail}")
    if not cond:
        fails.append(name)


LOOP_S = 30.0
N = int(LOOP_S * SR)
WAVE_HZ = 4.0 / LOOP_S            # integer cycles: the loop closes

# (f_c, rate, seed, pan, wave phase) — the written bed
ABURA = [(5400.0, 84.0, 1, -0.50, 0.00),
         (5650.0, 89.0, 2, -0.20, 0.06),
         (5850.0, 93.0, 3, 0.10, 0.12),
         (5250.0, 80.0, 4, 0.35, 0.18),
         (5550.0, 86.0, 5, 0.55, 0.09)]

MM_FC, MM_RATE = 4300.0, 118.0
SYL = [(0.00, 0.62), (0.75, 0.30), (1.14, 0.30),
       (1.53, 0.30), (1.92, 0.30), (2.31, 0.85)]
PHRASES = [(6.0, 11, 0.25), (19.5, 12, -0.15)]   # (t0, seed, pan)

t = np.arange(N) / SR
bed_bus = np.zeros((N, 2))
bed_renders = []
gains = []
for f_c, rate, sd, pan, ph in ABURA:
    v = cicada(LOOP_S, f_c=f_c, rate=rate, seed=sd)
    s = 0.5 + 0.5 * np.sin(2.0 * np.pi * (WAVE_HZ * t - ph))
    g = 0.35 + 0.65 * s ** 1.6
    bed_renders.append(v)
    gains.append(g)
    bed_bus += stereo(v * g, pan) * 0.050

mm_bus = np.zeros((N, 2))
mm_renders = []
for t0, sd, pan in PHRASES:
    dur = SYL[-1][0] + SYL[-1][1] + 0.05
    v = cicada(dur, f_c=MM_FC, rate=MM_RATE, q=10.0,
            jitter=0.05, syllables=SYL, seed=sd)
    mm_renders.append(v)
    i0 = int(t0 * SR)
    mm_bus[i0:i0 + len(v)] += stereo(v, pan)[:N - i0] * 0.16

air = 0.022 * wind(LOOP_S, base_hz=250.0, howl=0.20, gust=0.30,
        seed=0x51)

dry = bed_bus + mm_bus + air
mix = 0.90 * dry + 0.10 * reverb_loop(dry, t60=0.9, size=1.4)
mix *= 0.92 / (np.abs(mix).max() + 1e-12)
write_wav(os.path.join(outdir, "e96_semishigure.wav"), mix)

# ---- rulers ------------------------------------------------------
print("e96 rulers:")

# 1. every tymbal runs at its written rate (own renders; the
# minmin pooled over BOTH long syllables of both phrases — a
# single 0.5 s window holds ~59 jittered clicks and its sample
# mean wanders 4%; the claim needs integration time)
worst_r = 0.0
for (f_c, rate, sd, pan, ph), v in zip(ABURA, bed_renders):
    _, rs = ruler.rate_contour(v, rmin=rate * 0.6,
            rmax=rate * 1.5, win_s=0.5, hop_s=0.25,
            frame=256, hop=32)
    worst_r = max(worst_r,
            abs(float(np.median(rs)) / rate - 1.0))
mm_rs = []
for v in mm_renders:
    for s_on, s_dur in (SYL[0], SYL[-1]):
        a, b = s_on + 0.05, s_on + s_dur - 0.05
        _, rs = ruler.rate_contour(v[int(a * SR):int(b * SR)],
                rmin=MM_RATE * 0.6, rmax=MM_RATE * 1.5,
                win_s=0.5, hop_s=0.25, frame=256, hop=32)
        mm_rs.extend(rs)
worst_r = max(worst_r,
        abs(float(np.median(mm_rs)) / MM_RATE - 1.0))
check("rates", worst_r <= 0.04,
        f"5 bed calls + the pooled minmin, worst rate error "
        f"{100 * worst_r:.1f}%")

# 2. every resonator peaks at its written formant, and the two
# species stand apart
def peak_hz(v):
    p = np.abs(np.fft.rfft(v * np.hanning(len(v)))) ** 2
    f = np.fft.rfftfreq(len(v), 1.0 / SR)
    sel = (f > 2000.0) & (f < 8000.0)
    return float(f[sel][np.argmax(p[sel])])


worst_f = 0.0
ab_pk = []
for (f_c, rate, sd, pan, ph), v in zip(ABURA, bed_renders):
    pk = peak_hz(v)
    ab_pk.append(pk)
    worst_f = max(worst_f, abs(pk / f_c - 1.0))
mm_pk = [peak_hz(v) for v in mm_renders]
worst_f = max(worst_f, max(abs(pk / MM_FC - 1.0)
        for pk in mm_pk))
gap = min(ab_pk) - max(mm_pk)
check("formants", worst_f <= 0.05 and gap >= 700.0,
        f"worst formant error {100 * worst_f:.1f}%, species "
        f"gap {gap:.0f} Hz")

# 3. every written syllable marks (bloom rule: first crossing
# of -12 dB re the syllable's own peak, minmin bus)
sos_mm = butter(4, [3800.0, 4800.0], btype="bandpass", fs=SR,
        output="sos")
env = np.abs(sosfilt(sos_mm, mm_bus.mean(axis=1)))
ke = int(0.006 * SR)
env = np.convolve(env, np.ones(ke) / ke, mode="same")
# window starts INSIDE the 90 ms inter-syllable gap: a -0.10 s
# pre-roll reached into the previous syllable's plateau and the
# "first crossing" was the window's own first sample
worst_s = 0.0
for t0, sd, pan in PHRASES:
    for s_on, s_dur in SYL:
        tw = t0 + s_on
        i0, i1 = int((tw - 0.04) * SR), int((tw + 0.20) * SR)
        w = env[i0:i1]
        tm = (i0 + int(np.argmax(w >= 0.25 * w.max()))) / SR
        worst_s = max(worst_s, abs(tm - tw) * 1000.0)
check("syllables", worst_s <= 30.0,
        f"{2 * len(SYL)} syllables, worst |mark - written| "
        f"{worst_s:.1f} ms")

# 4. the chorus breathes at the written wave, by the written
# amount: bed envelope spectrum peaks at WAVE_HZ, and the
# measured swell contrast matches the design column (written
# gains x each render's own mean level)
bm = np.abs(bed_bus.mean(axis=1))
kb = int(0.08 * SR)
bm = np.convolve(bm, np.ones(kb) / kb, mode="same")
dec = bm[::441]
sp = np.abs(np.fft.rfft((dec - dec.mean())
        * np.hanning(len(dec))))
fq = np.fft.rfftfreq(len(dec), 441.0 / SR)
sel = (fq >= 0.06) & (fq <= 0.35)
w_me = float(fq[sel][np.argmax(sp[sel])])
design = np.zeros(N)
for v, g in zip(bed_renders, gains):
    design += float(np.mean(np.abs(v))) * g
c_de = 20.0 * np.log10(design.max() / design.min())
c_me = 20.0 * np.log10(np.percentile(bm, 98.0)
        / np.percentile(bm, 2.0))
check("chorus_wave",
        abs(w_me - WAVE_HZ) <= 0.012
        and abs(c_me - c_de) <= 2.0,
        f"wave {w_me:.3f} Hz (written {WAVE_HZ:.3f}), swell "
        f"{c_me:.1f} dB vs designed {c_de:.1f}")

# 5. the loop closes (integer wave cycles by construction)
check("seam", ruler.seam_rank(mix) <= 0.999,
        f"p{100 * ruler.seam_rank(mix):.2f}")

ruler.report(mix, "e96_semishigure")
print(f"\n{'ALL PASS' if not fails else 'FAILS: ' + str(fails)}")
sys.exit(1 if fails else 0)

#!/usr/bin/env python3
"""loam e89 — komibuki: the pulsed breath (two cranes).

nihon.shakuhachi() learns KOMIBUKI — the rhythmic diaphragm
pushes on a held tone that voice the cranes of Tsuru no
Sugomori. Three coupled layers per push, all gated in after
the attack: an amplitude pulse (tone dips to 1-komibuki
between pushes), a burst of direct-radiation turbulence riding
each push, and a small mean-removed pitch flutter written into
the warp (jet pressure provably cannot bend this bore).

What is claimable and what is not, learned the hard way:

  - the AMPLITUDE layers are strongly measurable: envelope-
    spectrum line at the written rate (+30 dB over a
    komibuki=0 twin), regression depth within a dB of design,
    high-band hiss envelope r=0.97 against the design pulse;
  - the PITCH flutter is NOT claimable. Blind FFT of the IF
    track: the breathy bore's IF noise floor is ~11.5 cents
    per bin — the written 3-cent line drowns (e86's BT wall,
    periodic edition). Twin-delta (e82): FAILS here, and the
    residual names why — a warp delta is a CLOCK delta. The
    twins' sample clocks oscillate ~12 samples apart, so the
    waveform difference is noise-slew x clock-offset, 14 c rms
    of fresh in-band noise. e82 differenced MEASUREMENTS
    (peak positions); differencing WAVEFORMS of time-warped
    twins floods the delta. The flutter stays in the sound as
    physical micro-motion and earns no ruler.

The piece: a 33.6 s loop in D minyo over low wind. Two cranes
answer at DIFFERENT written pulse rates (5.2 Hz and 6.5 Hz),
and a final settling note pulses slow (4.5 Hz) — so the rate
ruler proves per-note control, and a selectivity ruler proves
the rates do not blur into each other.

    python3 experiments/e89_tsuru_komibuki.py [outdir]
"""

import os
import sys

import numpy as np
from scipy.signal import butter, sosfilt

sys.path.insert(0, os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))))
from loam import SR, hz, stereo, write_wav
from loam import ruler
from loam.nihon import shakuhachi
from loam.texture import wind
from loam.space import reverb_loop

outdir = sys.argv[1] if len(sys.argv) > 1 else "render"
os.makedirs(outdir, exist_ok=True)
fails = []


def check(name, cond, detail):
    print(f"  {'PASS' if cond else 'FAIL'} {name}: {detail}")
    if not cond:
        fails.append(name)


def rms(x):
    return float(np.sqrt(np.mean(np.asarray(x, float) ** 2) + 1e-30))


LOOP_S = 33.6
N = int(LOOP_S * SR)

# (start, midi, dur, muraiki, scoop, yuri_c, komibuki, komi_hz,
#  amp, pan)
PHRASES = [
    (0.8, 67, 5.6, 0.45, 35.0, 0.0, 0.50, 5.2, 0.95, 0.12),
    (7.6, 69, 1.8, 0.25, 25.0, 0.0, 0.0, 5.5, 0.80, 0.0),
    (9.6, 72, 1.5, 0.30, 30.0, 0.0, 0.0, 5.5, 0.85, 0.0),
    (11.3, 69, 3.2, 0.20, 20.0, 24.0, 0.0, 5.5, 0.85, 0.0),
    (15.6, 74, 2.6, 0.85, 45.0, 0.0, 0.0, 5.5, 1.00, 0.0),
    (18.4, 72, 1.6, 0.20, 25.0, 0.0, 0.0, 5.5, 0.80, 0.0),
    (20.2, 69, 4.8, 0.35, 30.0, 0.0, 0.60, 6.5, 0.95, -0.12),
    (26.2, 65, 1.6, 0.30, 30.0, 0.0, 0.0, 5.5, 0.75, 0.0),
    (28.0, 62, 5.0, 0.90, 60.0, 0.0, 0.35, 4.5, 1.00, 0.0),
]
KOMI = [i for i, p in enumerate(PHRASES) if p[6] > 0.0]


def add_wrap(bus, t, ss):
    i0 = int(round(t * SR)) % N
    n = len(ss)
    if i0 + n <= N:
        bus[i0:i0 + n] += ss
    else:
        k = N - i0
        bus[i0:] += ss[:k]
        bus[:n - k] += ss[k:]


NOTES = []
flt = np.zeros((N, 2))
for i, (t, m, dur, mur, sc, yc, ko, khz, a, pn) in \
        enumerate(PHRASES):
    v = shakuhachi(hz(m), dur, muraiki=mur, scoop=sc, yuri_c=yc,
            komibuki=ko, komi_hz=khz, seed=23 + 9 * i)
    NOTES.append(v)
    add_wrap(flt, t, stereo(v * a, pn))

air = 0.05 * wind(LOOP_S, base_hz=280.0, howl=0.35, gust=0.4,
        seed=0x77)

dry = 0.88 * flt + air
wet = reverb_loop(dry, t60=2.4, size=1.25)
mix = 0.82 * dry + 0.30 * wet
mix *= 0.92 / (np.abs(mix).max() + 1e-12)
write_wav(os.path.join(outdir, "e89_tsuru_komibuki.wav"), mix)

# ---- rulers ------------------------------------------------------
print("e89 rulers (komibuki claims on each note's own buffer):")


def env_of(v, s0, s1):
    e = np.abs(v)
    k = int(0.02 * SR)
    e = np.convolve(e, np.ones(k) / k, mode="same")
    return e[int(s0 * SR):int(s1 * SR)]


def env_spec(v, s0, s1):
    e = env_of(v, s0, s1)
    e = e / e.mean() - 1.0
    S = np.abs(np.fft.rfft(e * np.hanning(len(e))))
    fr = np.fft.rfftfreq(len(e), 1.0 / SR)
    return fr, S


# 1. each pulsing note flickers at ITS OWN written rate
worst_df = 0.0
det = []
for i in KOMI:
    t, m, dur, mur, sc, yc, ko, khz, a, pn = PHRASES[i]
    fr, S = env_spec(NOTES[i], 0.9, dur - 0.35)
    sel = (fr >= 3.0) & (fr <= 8.5)
    fpk = float(fr[sel][np.argmax(S[sel])])
    worst_df = max(worst_df, abs(fpk - khz))
    det.append(f"{khz:.1f}->{fpk:.2f}")
check("komi_rates", worst_df <= 0.25,
        f"written->measured Hz: {', '.join(det)} "
        f"(worst |df| {worst_df:.2f})")

# 2. the rates do not blur: each note's own-rate bin stands
# >= 10 dB over the OTHER cranes' rate bins in its spectrum
worst_sel = 99.0
for i in KOMI:
    t, m, dur, mur, sc, yc, ko, khz, a, pn = PHRASES[i]
    fr, S = env_spec(NOTES[i], 0.9, dur - 0.35)
    own = S[np.argmin(np.abs(fr - khz))]
    for j in KOMI:
        if j == i:
            continue
        okhz = PHRASES[j][7]
        other = S[np.argmin(np.abs(fr - okhz))]
        worst_sel = min(worst_sel,
                20.0 * np.log10(own / (other + 1e-12)))
check("komi_selectivity", worst_sel >= 10.0,
        f"own-rate line over other cranes' bins: worst "
        f"{worst_sel:+.1f} dB")

# 3. pulse depth, design vs measured: regress the envelope on
# the design pulse over the sustain; depth = (a+b)/a in dB
# against -20 log10(1-komibuki)
worst_dd = 0.0
det = []
for i in KOMI:
    t, m, dur, mur, sc, yc, ko, khz, a, pn = PHRASES[i]
    s0, s1 = 0.9, dur - 0.35
    e = env_of(NOTES[i], s0, s1)
    tt = np.arange(int(s0 * SR), int(s0 * SR) + len(e)) / SR
    pul = (0.5 - 0.5 * np.cos(2.0 * np.pi * khz * tt)) ** 2
    A = np.vstack([np.ones_like(pul), pul]).T
    co, *_ = np.linalg.lstsq(A, e, rcond=None)
    md = 20.0 * np.log10((co[0] + co[1]) / co[0])
    dd = -20.0 * np.log10(1.0 - ko)
    worst_dd = max(worst_dd, abs(md - dd))
    det.append(f"{dd:.1f}->{md:.1f}")
check("komi_depth", worst_dd <= 2.5,
        f"design->measured dB: {', '.join(det)} "
        f"(worst |dd| {worst_dd:.2f})")

# 4. twin contrast, MEASUREMENT-differenced (never waveform-
# differenced, see header): own-rate envelope bin vs the same
# bin of a komibuki=0 twin, same seed and window
worst_tw = 99.0
for i in KOMI:
    t, m, dur, mur, sc, yc, ko, khz, a, pn = PHRASES[i]
    tw = shakuhachi(hz(m), dur, muraiki=mur, scoop=sc,
            yuri_c=yc, komibuki=0.0, seed=23 + 9 * i)
    fr, S = env_spec(NOTES[i], 0.9, dur - 0.35)
    _, St = env_spec(tw, 0.9, dur - 0.35)
    bi = np.argmin(np.abs(fr - khz))
    worst_tw = min(worst_tw,
            20.0 * np.log10(S[bi] / (St[bi] + 1e-12)))
check("komi_twin", worst_tw >= 15.0,
        f"own-rate line vs still-breath twin: worst "
        f"{worst_tw:+.1f} dB")

# 5. each push carries breath: 3-9 kHz envelope tracks the
# design pulse across the sustain
sos_h = butter(3, [3000.0, 9000.0], btype="bandpass", fs=SR,
        output="sos")
worst_r = 1.0
for i in KOMI:
    t, m, dur, mur, sc, yc, ko, khz, a, pn = PHRASES[i]
    s0, s1 = 0.9, dur - 0.35
    he = np.abs(sosfilt(sos_h, NOTES[i]))
    k = int(0.02 * SR)
    he = np.convolve(he, np.ones(k) / k, mode="same")
    he = he[int(s0 * SR):int(s1 * SR)]
    tt = np.arange(int(s0 * SR), int(s0 * SR) + len(he)) / SR
    pul = (0.5 - 0.5 * np.cos(2.0 * np.pi * khz * tt)) ** 2
    worst_r = min(worst_r, float(np.corrcoef(he, pul)[0, 1]))
check("komi_hiss", worst_r >= 0.6,
        f"high-band env vs design pulse: worst r={worst_r:.3f}")

# 6. pulsing must not bend the center: every note still sits
# on its written pitch (e82's gate, now under modulation)
worst_c = 0.0
for v, (t, m, dur, mur, sc, yc, ko, khz, a, pn) in \
        zip(NOTES, PHRASES):
    inst = ruler.if_pitch(v, hz(m))
    s0, s1 = max(0.5, 0.3 * dur), dur - 0.3
    c = 1200.0 * np.log2(np.median(
            inst[int(s0 * SR):int(s1 * SR)]) / hz(m))
    worst_c = max(worst_c, abs(c))
check("centers", worst_c <= 20.0,
        f"9 notes, worst sustain center {worst_c:.1f} cents")

# 7. the loop closes
check("seam", ruler.seam_rank(mix) <= 0.999,
        f"p{100 * ruler.seam_rank(mix):.2f}")

ruler.report(mix, "e89_tsuru_komibuki")
print(f"\n{'ALL PASS' if not fails else 'FAILS: ' + str(fails)}")
sys.exit(1 if fails else 0)

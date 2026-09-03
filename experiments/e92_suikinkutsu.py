#!/usr/bin/env python3
"""loam e92 — suikinkutsu: the water-echo pot.

A buried ceramic pot, half-filled; drops fall through the hole
and each drop's bubble rings the cavity into a faint hollow
chime. New in nihon.py:

  - suikinkutsu_ir(): the pot as a stereo modal IR — one
    hollow ~360 Hz body mode plus three ceramic rings (1150 /
    1720 / 2310 Hz), channels detuned +-0.2% (two listening
    points on one pot);
  - waterdrop(): Minnaert bubble (rising chirp) + a 2 ms
    impact tick. The tick is load-bearing: a 900-2400 Hz
    bubble has no energy at 360 Hz, so without the impact the
    pot's hollow would stay silent (e84's register rule —
    excitation must reach the resonance you claim).

The experiment owns the WRITTEN arrival times (seeded draw,
min gap 0.30 s), so timing, chirp, chamber modes and the pot's
transfer gain are all design-vs-measured.

    python3 experiments/e92_suikinkutsu.py [outdir]
"""

import os
import sys

import numpy as np
from scipy.signal import butter, sosfilt, fftconvolve, hilbert

sys.path.insert(0, os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))))
from loam import SR, hz, stereo, write_wav
from loam import ruler
from loam.nihon import suikinkutsu_ir, waterdrop, SUIKIN_MODES
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


LOOP_S = 34.0
N = int(LOOP_S * SR)
CHIRP, DAMP = 1.7, 0.75

# written arrivals: seeded draw, min gap 0.30 s — the list IS
# the design
rng = np.random.default_rng(0x5D0)
ARR, F0S, AMPS = [], [], []
t = 0.4
while t < LOOP_S - 0.35:
    ARR.append(round(t, 4))
    F0S.append(float(rng.uniform(900.0, 2400.0)))
    AMPS.append(float(rng.uniform(0.45, 1.0)))
    t += max(0.30, float(rng.exponential(1.9)))

DROPS = [waterdrop(f, chirp=CHIRP, damp=DAMP) for f in F0S]

dry = np.zeros(N)
for tt, d, a in zip(ARR, DROPS, AMPS):
    i0 = int(round(tt * SR)) % N
    n = len(d)
    if i0 + n <= N:
        dry[i0:i0 + n] += a * d
    else:
        k = N - i0
        dry[i0:] += a * d[:k]
        dry[:n - k] += a * d[k:]

IR = suikinkutsu_ir()
wet = np.zeros((N, 2))
for ch in range(2):
    c = fftconvolve(dry, IR[:, ch])
    wet[:, ch] = c[:N]
    tail = c[N:]
    wet[:len(tail), ch] += tail          # the pot rings across
                                         # the seam

air = 0.045 * wind(LOOP_S, base_hz=220.0, howl=0.30, gust=0.35,
        seed=0x3A)

mixdry = 0.16 * stereo(dry, 0.0) + 0.95 * wet + air
room = reverb_loop(mixdry, t60=1.3, size=0.9)
mix = 0.88 * mixdry + 0.18 * room
mix *= 0.92 / (np.abs(mix).max() + 1e-12)
write_wav(os.path.join(outdir, "e92_suikinkutsu.wav"), mix)

# ---- rulers ------------------------------------------------------
print(f"e92 rulers ({len(ARR)} written drops):")

wm = wet.mean(axis=1)

# 1. the pot's modes stand in the rendered loop where they were
# written (whole-signal FFT peaks, ruler.mode_freqs). merge:
# each mode is a CLUSTER (two detuned channel lines + arrival-
# pattern sidebands) — unmerged, all eight peak slots go to the
# strongest cluster and the other modes never make the list
mf = ruler.mode_freqs(wm, k=8, fmin=280.0, fmax=2600.0,
        merge=0.02)
worst_m = 0.0
det = []
for f, a, t60 in SUIKIN_MODES:
    near = mf[np.argmin(np.abs(np.log(mf / f)))]
    c = abs(1200.0 * np.log2(near / f))
    worst_m = max(worst_m, c)
    det.append(f"{f:.0f}->{near:.0f}")
check("pot_modes", worst_m <= 25.0,
        f"{', '.join(det)} Hz (worst {worst_m:.1f} c)")

# 2. every written drop marks on time
sos_hp = butter(4, 700.0, btype="highpass", fs=SR, output="sos")
h = np.abs(sosfilt(sos_hp, wm))
ker = int(0.003 * SR)
h = np.convolve(h, np.ones(ker) / ker, mode="same")
fx = np.maximum(np.diff(h, prepend=h[:1]), 0.0)
worst_mk = 0.0
for tt in ARR:
    i0, i1 = int((tt - 0.10) * SR), int((tt + 0.10) * SR)
    tmk = (i0 + int(np.argmax(fx[i0:i1]))) / SR
    worst_mk = max(worst_mk, abs(tmk - tt) * 1000.0)
check("drops_mark", worst_mk <= 12.0,
        f"worst |mark - written| {worst_mk:.1f} ms")

# 3. every drop RISES as written (van den Doel chirp,
# design-vs-measured on the drop's own render)
worst_ch = 0.0
for f0, d in zip(F0S, DROPS):
    dd = (0.13 * f0 + 0.0072 * f0 ** 1.5) * DAMP
    ring = 6.91 / dd
    t1, t2 = 0.15 * ring, 0.55 * ring
    ph = np.unwrap(np.angle(hilbert(d[:int(0.9 * ring * SR)])))
    inst = np.diff(ph) * SR / (2 * np.pi)
    k = max(int(0.0004 * SR), 1)
    inst = np.convolve(inst, np.ones(k) / k, mode="same")
    r_me = inst[int(t2 * SR)] / inst[int(t1 * SR)]
    r_de = (1.0 + 0.1 * CHIRP * dd * t2) \
        / (1.0 + 0.1 * CHIRP * dd * t1)
    worst_ch = max(worst_ch, abs(r_me / r_de - 1.0))
check("chirps_rise", worst_ch <= 0.05,
        f"{len(F0S)} drops, worst chirp-ratio error "
        f"{100 * worst_ch:.1f}%")

# 4. the pot amplifies its modes: wet/dry transfer at the
# written modes vs between them
W = np.abs(np.fft.rfft(wm))
D = np.abs(np.fft.rfft(dry))
fr = np.fft.rfftfreq(N, 1.0 / SR)


def xfer(f):
    sel = (fr >= f * 2 ** (-40 / 1200)) \
        & (fr <= f * 2 ** (40 / 1200))
    return 20.0 * np.log10(
            np.sqrt(np.mean(W[sel] ** 2))
            / (np.sqrt(np.mean(D[sel] ** 2)) + 1e-12))


g_mode = np.median([xfer(f) for f, a, t in SUIKIN_MODES])
g_ref = np.median([xfer(f) for f in (500.0, 700.0, 1420.0,
        2000.0)])
check("pot_gain", g_mode - g_ref >= 8.0,
        f"transfer at modes {g_mode:+.1f} dB vs between "
        f"{g_ref:+.1f} dB (contrast {g_mode - g_ref:.1f})")

# 5. the garden is quiet between drops
e = np.abs(mix.mean(axis=1))
ke = int(0.02 * SR)
e = np.convolve(e, np.ones(ke) / ke, mode="same")
dyn = 20.0 * np.log10(np.percentile(e, 99.5)
        / (np.percentile(e, 15.0) + 1e-12))
check("sparse", dyn >= 30.0,
        f"p99.5 sits {dyn:.1f} dB over p15 of the envelope")

# 6. the loop closes (the pot rings across the seam by
# construction — the convolution tail wraps)
check("seam", ruler.seam_rank(mix) <= 0.999,
        f"p{100 * ruler.seam_rank(mix):.2f}")

ruler.report(mix, "e92_suikinkutsu")
print(f"\n{'ALL PASS' if not fails else 'FAILS: ' + str(fails)}")
sys.exit(1 if fails else 0)

#!/usr/bin/env python3
"""loam e94 — shishi-odoshi: the bamboo deer-scarer.

A pivoted bamboo arm under a thin water feed: it fills, tips,
dumps its water (the POUR), swings back and strikes its stone
(the TOK), and starts filling again. A mechanical water clock —
which makes it a ruler's dream, because the mechanism IS the
design column:

  - the period is written (9 s, three cycles in a 27 s loop);
  - each tok must FOLLOW its pour by the written arm-return
    time (0.55 s) — order and gap are both claims;
  - the strike's modes and decay are a written table
    (nihon.BAMBOO_MODES), measured on the tok's own render;
  - the tok decay is measured with ruler.line_env at
    width_c=150 — NOT the default 25: at 820 Hz the default's
    12 Hz lowpass has a ~30 ms step response, the same order as
    the 47 ms/20 dB decay it would be measuring. The ruler's
    bandwidth is part of the claim (e92's threshold lesson,
    time-domain edition).

New in nihon.py: bamboo_tok() (modal strike + 3 ms contact
burst) and pour() (gurgle-wobbled splash). Both deterministic.

    python3 experiments/e94_shishi_odoshi.py [outdir]
"""

import os
import sys

import numpy as np
from scipy.signal import butter, sosfilt

sys.path.insert(0, os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))))
from loam import SR, stereo, write_wav
from loam import ruler
from loam.nihon import bamboo_tok, pour, BAMBOO_MODES
from loam.texture import wind
from loam.space import reverb_loop

outdir = sys.argv[1] if len(sys.argv) > 1 else "render"
os.makedirs(outdir, exist_ok=True)
fails = []


def check(name, cond, detail):
    print(f"  {'PASS' if cond else 'FAIL'} {name}: {detail}")
    if not cond:
        fails.append(name)


LOOP_S = 27.0
N = int(LOOP_S * SR)
PERIOD = 9.0
TIPS = [1.8, 10.8, 19.8]         # written tip times (the clock)
RETURN_S = 0.55                  # arm swing-back: pour -> tok
BOUNCE_S = 0.13                  # soft secondary contact
POUR_DUR = 1.1

bus = np.zeros((N, 2))
for k, tip in enumerate(TIPS):
    p = pour(POUR_DUR, seed=0x9042 + k)      # new water each tip
    i0 = int(tip * SR)
    bus[i0:i0 + len(p)] += 0.24 * stereo(p, -0.06)[:N - i0]
    tk = bamboo_tok()
    j0 = int((tip + RETURN_S) * SR)
    bus[j0:j0 + len(tk)] += 0.85 * stereo(tk, 0.10)[:N - j0]
    j1 = int((tip + RETURN_S + BOUNCE_S) * SR)
    bus[j1:j1 + len(tk)] += 0.30 * stereo(tk, 0.10)[:N - j1]

# the feed itself: a thin constant trickle, barely there
rng = np.random.default_rng(0x7211)
tr = sosfilt(butter(2, [2800.0, 7800.0], btype="bandpass",
        fs=SR, output="sos"), rng.standard_normal(N))
tr /= np.abs(tr).max() + 1e-12
bus += 0.010 * stereo(tr, -0.02)

air = 0.030 * wind(LOOP_S, base_hz=200.0, howl=0.25, gust=0.30,
        seed=0x44)

dry = bus + air
mix = 0.88 * dry + 0.22 * reverb_loop(dry, t60=1.6, size=1.0)
mix *= 0.92 / (np.abs(mix).max() + 1e-12)
write_wav(os.path.join(outdir, "e94_shishi_odoshi.wav"), mix)

# ---- rulers ------------------------------------------------------
print("e94 rulers (the mechanism is the design column):")

dm = dry.mean(axis=1)


def flux_of(x, f0, f1):
    sos = butter(4, [f0, f1], btype="bandpass", fs=SR,
            output="sos")
    h = np.abs(sosfilt(sos, x))
    ker = int(0.003 * SR)
    h = np.convolve(h, np.ones(ker) / ker, mode="same")
    return np.maximum(np.diff(h, prepend=h[:1]), 0.0)


# 1. every tok marks at its written time (tip + return)
fx_tok = flux_of(dm, 500.0, 4500.0)
tok_marks = []
worst_t = 0.0
for tip in TIPS:
    tw = tip + RETURN_S
    i0, i1 = int((tw - 0.15) * SR), int((tw + 0.15) * SR)
    tm = (i0 + int(np.argmax(fx_tok[i0:i1]))) / SR
    tok_marks.append(tm)
    worst_t = max(worst_t, abs(tm - tw) * 1000.0)
check("toks_mark", worst_t <= 10.0,
        f"3 strikes, worst |mark - written| {worst_t:.1f} ms")

# 2. every pour marks at its written tip. A pour is a BLOOM,
# not a strike (e91's lesson): flux argmax lands on whichever
# gurgle swell rises fastest, tens of ms into the water. Mark
# where the band envelope FIRST crosses -12 dB re its window
# peak instead.
sos_po = butter(4, [1500.0, 5200.0], btype="bandpass", fs=SR,
        output="sos")
env_po = np.abs(sosfilt(sos_po, dm))
kp = int(0.005 * SR)
env_po = np.convolve(env_po, np.ones(kp) / kp, mode="same")
po_marks = []
worst_p = 0.0
for tip in TIPS:
    i0, i1 = int((tip - 0.15) * SR), int((tip + 0.35) * SR)
    w = env_po[i0:i1]
    tm = (i0 + int(np.argmax(w >= 0.25 * w.max()))) / SR
    po_marks.append(tm)
    worst_p = max(worst_p, abs(tm - tip) * 1000.0)
check("pours_mark", worst_p <= 30.0,
        f"3 pours, worst |mark - written| {worst_p:.1f} ms")

# 3. the mechanism's order: each tok follows ITS pour by the
# written arm-return time (measured marks, not written times)
worst_g = max(abs((tm - pm) - RETURN_S) * 1000.0
        for tm, pm in zip(tok_marks, po_marks))
check("arm_return", worst_g <= 30.0,
        f"measured tok-pour gaps within {worst_g:.1f} ms of "
        f"written {RETURN_S * 1000:.0f} ms")

# 4. the strike's modes stand where written (own render)
tk = bamboo_tok()
# rel=1e-4: the 3060 Hz mode's fast decay (t60 45 ms) leaves it
# -36 dB in the whole-file FFT — a -30 dB bar silently drops a
# written mode (e92: the threshold is part of the claim)
mf = ruler.mode_freqs(tk, k=12, fmin=140.0, fmax=3400.0,
        rel=1e-4, merge=0.02)
worst_m = 0.0
det = []
for f, a, t60 in BAMBOO_MODES:
    near = mf[np.argmin(np.abs(np.log(mf / f)))]
    c = abs(1200.0 * np.log2(near / f))
    worst_m = max(worst_m, c)
    det.append(f"{f:.0f}->{near:.0f}")
check("bamboo_modes", worst_m <= 25.0,
        f"{', '.join(det)} Hz (worst {worst_m:.1f} c)")

# 5. the main mode decays at its written rate: log-slope of the
# 820 Hz line env between -8 and -28 dB re peak -> t60.
# width_c=150 on purpose — see the docstring.
e = ruler.line_env(tk, 820.0, width_c=150.0)
pk = float(e.max())
ipk = int(np.argmax(e))
db = 20.0 * np.log10(e[ipk:] / pk + 1e-30)
sel = np.where((db <= -8.0) & (db >= -28.0))[0]
tt = sel / SR
slope = np.polyfit(tt, db[sel], 1)[0]          # dB per second
t60_me = -60.0 / slope
t60_de = dict((f, t) for f, a, t in BAMBOO_MODES)[820.0]
check("tok_decay", abs(t60_me / t60_de - 1.0) <= 0.25,
        f"820 Hz line t60 {t60_me * 1000:.0f} ms vs written "
        f"{t60_de * 1000:.0f} ms "
        f"({100 * (t60_me / t60_de - 1.0):+.1f}%)")

# 6. the garden is quiet between events
env = np.abs(mix.mean(axis=1))
ke = int(0.02 * SR)
env = np.convolve(env, np.ones(ke) / ke, mode="same")
dyn = 20.0 * np.log10(np.percentile(env, 99.5)
        / (np.percentile(env, 20.0) + 1e-12))
check("sparse", dyn >= 25.0,
        f"p99.5 sits {dyn:.1f} dB over p20 of the envelope")

# 7. the loop closes
check("seam", ruler.seam_rank(mix) <= 0.999,
        f"p{100 * ruler.seam_rank(mix):.2f}")

ruler.report(mix, "e94_shishi_odoshi")
print(f"\n{'ALL PASS' if not fails else 'FAILS: ' + str(fails)}")
sys.exit(1 if fails else 0)

#!/usr/bin/env python3
"""loam e88 — Surfacing. The turtle rises, breaks the water,
and breathes.

loam's first ARC piece: no loop, no seam — a shape in time.
The seam ruler retires for one cycle and arc-shaped claims
take its place: silence at both ends, monotonic brightening
through the ascent, an accelerating exhale, a single loudest
moment at the break, and the major third arriving with the
sun (the deep is bare E-B; G# exists only above the water).

Timeline (72 s):
    0-20    THE DEEP    e83's world: dark surge, body drone,
                        caustics dim and far above
    20-52   ASCENT      brightness, light and bubbles all
                        rise with u(t) = smoothstep
    52.0    THE BREAK   splash — loudest instant of the piece
    52.6    FIRST BREATH the hiss-band climax
    52-72   AIR         major-third pad, surface sparkle,
                        wind, fade to silence

texture.caustics() is promoted this cycle (born e83, second
customer here — arcs need intensity as a CURVE, so it takes
scalar or array).

    python3 experiments/e88_surfacing.py [outdir]
"""

import os
import sys

import numpy as np
from scipy.signal import butter, sosfilt

sys.path.insert(0, os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))))
from loam import SR, hz, stereo, write_wav
from loam import ruler
from loam.pads import padsynth_table, padsynth_stereo
from loam.texture import caustics, bubble
from loam.space import reverb_tail

outdir = sys.argv[1] if len(sys.argv) > 1 else "render"
os.makedirs(outdir, exist_ok=True)
fails = []


def check(name, cond, detail):
    print(f"  {'PASS' if cond else 'FAIL'} {name}: {detail}")
    if not cond:
        fails.append(name)


def rms(x):
    return float(np.sqrt(np.mean(np.asarray(x, float) ** 2) + 1e-30))


DUR = 72.0
N = int(DUR * SR)
T = np.arange(N) / SR
BREAK = 52.0
BREATH = 52.6


def smoothstep(x):
    x = np.clip(x, 0.0, 1.0)
    return x * x * (3.0 - 2.0 * x)


u = smoothstep((T - 20.0) / 32.0)         # the ascent 20 -> 52
surge = np.sin(2 * np.pi * 0.07 * T - 1.2)
under = np.clip((BREAK - T) / 1.2, 0.0, 1.0)   # water's weight
over = np.clip((T - BREAK) / 1.2, 0.0, 1.0)


def add_at(bus, t, ss):
    i0 = int(t * SR)
    k = min(len(ss), N - i0)
    if ss.ndim == 1:
        bus[i0:i0 + k] += np.stack([ss[:k], ss[:k]], axis=1)
    else:
        bus[i0:i0 + k] += ss[:k]


# ---- the water (dies at the break) ------------------------------
dark = padsynth_stereo(DUR, hz(40),
        [h ** -2.6 for h in range(1, 11)], bw_cents=45.0, seed=21)
# bright water stops at h16: h20 of E2 is 1648 Hz = G#6 exactly,
# and the sunrise ruler claims that line exists only above water
brgt = padsynth_stereo(DUR, hz(40),
        [h ** -1.4 for h in range(1, 17)], bw_cents=45.0, seed=23)
dark /= rms(dark)
brgt /= rms(brgt)
gd, gb = (1.0 - 0.8 * u), 0.9 * (0.25 + 0.75 * u)
nrm = np.sqrt(gd ** 2 + gb ** 2)
level = (0.75 + 0.25 * surge) * under
water = ((gd / nrm)[:, None] * dark + (gb / nrm)[:, None] * brgt) \
    * (level * np.clip(T / 6.0, 0.0, 1.0))[:, None]

# ---- the body (fades in the last fathom) ------------------------
# body skips h10: E3 x 10 = 1648 Hz = G#6, the sunrise line
btab = padsynth_table(DUR, hz(52),
        [h ** -2.0 if h != 10 else 0.0 for h in range(1, 13)],
        bw_cents=15.0, seed=27)
ratio = 2.0 ** (10.0 * surge / 1200.0)
idx = np.cumsum(ratio)
idx -= idx[0]
idx = np.clip(idx, 0.0, len(btab) - 1.0)
body_m = np.interp(idx, np.arange(len(btab), dtype=float), btab)
body = stereo(body_m, 0.0) * (under * np.clip(T / 6.0, 0, 1)
        * (1.0 - 0.55 * u))[:, None]

# ---- the light (approaches, then becomes surface sparkle) -------
inten_deep = (0.18 + 0.82 * u ** 1.5) * under
# deep glints avoid midi 92 (G#6): the third belongs to the sun
light = 0.9 * caustics(DUR, ripple_hz=1.4, intensity=inten_deep,
        midis=(88, 90, 95, 97, 100),
        weights=(0.32, 0.14, 0.30, 0.14, 0.10),
        wrap=False, seed=0xC4E)
sparkle = 0.7 * caustics(DUR, ripple_hz=2.2,
        intensity=over * np.clip((70.0 - T) / 6.0, 0.0, 1.0),
        midis=(93, 95, 97, 100, 102), lam_max=16.0,
        weights=(0.24, 0.26, 0.20, 0.18, 0.12), wrap=False,
        seed=0xA1)

# ---- the exhale stream (accelerates toward the surface) ---------
bub = np.zeros((N, 2))
BUB_T = []
rng = np.random.default_rng(0xB0B)
tt = 21.0
while tt < BREAK - 0.6:
    uu = float(np.interp(tt, T, u))
    BUB_T.append(tt)
    b = bubble(rng.uniform(380.0, 850.0) * (1.0 - 0.25 * uu),
            chirp=1.3, amp=0.5 + 0.5 * uu)
    add_at(bub, tt, stereo(b, float(rng.uniform(-0.3, 0.3))))
    tt += 1.9 - 1.55 * uu + rng.uniform(-0.05, 0.05)

# ---- the break: splash + droplets -------------------------------
spl = np.zeros((N, 2))
ns = int(0.9 * SR)
tsp = np.arange(ns) / SR
nz = rng.standard_normal(ns)
nz = sosfilt(butter(2, [600.0, 3800.0], btype="bandpass", fs=SR,
        output="sos"), nz)          # splash stays below the hiss
                                    # band: the BREATH owns 4k+
nz *= np.exp(-tsp / 0.16) * (1.0 - np.exp(-tsp / 0.004))
add_at(spl, BREAK, stereo(nz / (np.abs(nz).max() + 1e-12), 0.0))
low = rng.standard_normal(ns)
low = sosfilt(butter(2, 160.0, btype="lowpass", fs=SR,
        output="sos"), low) * np.exp(-tsp / 0.10)
add_at(spl, BREAK, stereo(0.8 * low / (np.abs(low).max() + 1e-12),
        0.0))
for k in range(7):                       # droplets falling back
    td = BREAK + 0.25 + 0.18 * k + rng.uniform(0, 0.08)
    b = bubble(rng.uniform(900.0, 2200.0), chirp=1.6,
            amp=0.5 * 0.85 ** k)
    add_at(spl, td, stereo(b, float(rng.uniform(-0.6, 0.6))))

# ---- the first breath (hiss-band climax) ------------------------
brt = np.zeros((N, 2))
nb = int(1.6 * SR)
tb = np.arange(nb) / SR
h = rng.standard_normal(nb)
h = sosfilt(butter(3, [2500.0, 8000.0], btype="bandpass", fs=SR,
        output="sos"), h)
h *= (1.0 - np.exp(-tb / 0.03)) * np.exp(-tb / 0.45)
add_at(brt, BREATH, stereo(1.0 * h / (np.abs(h).max() + 1e-12),
        0.0))

# ---- the air: the major third arrives ---------------------------
air = padsynth_stereo(DUR, hz(64),
        [1.0, 0.0, 0.55, 0.0, 0.40],
        bw_cents=25.0, seed=41)          # E4 + B5(h3) + G#6(h5)
airenv = over * np.clip((70.0 - T) / 8.0, 0.0, 1.0)
air = air * (0.9 * airenv)[:, None]

# ---- mix ---------------------------------------------------------
dry = (0.60 * water + 0.30 * body + 0.85 * light + 0.9 * sparkle
       + 0.30 * bub + 0.9 * spl + 0.75 * brt + 0.32 * air)
wet = reverb_tail(dry, t60=2.6, size=1.3)
wet = wet[:N]
mix = 0.82 * dry + 0.30 * wet
mix *= 0.92 / (np.abs(mix).max() + 1e-12)
write_wav(os.path.join(outdir, "e88_surfacing.wav"), mix)

# ---- rulers (arc claims — the seam retires this cycle) ----------
print("e88 rulers:")
mm = mix.mean(axis=1)
pk_db = 20.0 * np.log10(np.abs(mm).max() + 1e-30)

# 1. an arc starts and ends in silence
e0 = 20.0 * np.log10(rms(mm[:int(0.4 * SR)]) + 1e-30) - pk_db
e1 = 20.0 * np.log10(rms(mm[-int(0.4 * SR):]) + 1e-30) - pk_db
check("arc_silence", e0 <= -38.0 and e1 <= -38.0,
        f"first 0.4 s {e0:.0f} dB, last 0.4 s {e1:.0f} dB re peak")

# 2. the ascent brightens WITH THE WRITTEN ASCENT — own bus
# (mix windows breathe with surge/bubbles), design-vs-measured
# (rank-vs-index demands monotonicity even where smoothstep u
# is written flat, so early ranks were noise-decided; correlate
# against u itself and the flat start stops voting)
# 6 s windows, not 2: each pad harmonic is a ~2 Hz-wide noise
# (0.5 s coherence), and the whole written swing is one octave
# (94 -> 198 Hz design centroid) — short windows have estimator
# noise rivaling the signal (BT budget, cf. e86)
cen, uu_ = [], []
wm2 = water.mean(axis=1)
for w0 in np.arange(20.0, 44.0 + 0.1, 2.0):
    cen.append(ruler.centroid_hz(wm2[int(w0 * SR):
            int((w0 + 6.0) * SR)]))
    uu_.append(float(np.interp(w0 + 3.0, T, u)))
r_asc = float(np.corrcoef(cen, uu_)[0, 1])
check("ascent_brightens", r_asc >= 0.9,
        f"water centroid vs written u: r={r_asc:.3f} over "
        f"{len(cen)} 6 s windows ({cen[0]:.0f} -> {cen[-1]:.0f} Hz)")

# 3. the light approaches: caustic level tracks the written curve
lv, ds = [], []
lm = light.mean(axis=1)
for w0 in np.arange(20.0, 50.0, 2.0):
    a, b = int(w0 * SR), int((w0 + 2.0) * SR)
    lv.append(rms(lm[a:b]))
    ds.append(float(np.mean(inten_deep[a:b])))
r_l = float(np.corrcoef(lv, ds)[0, 1])
check("light_approaches", r_l >= 0.85,
        f"caustic level vs written intensity r={r_l:.3f}")

# 4. the exhale accelerates: bubble marks' IOIs shrink
sos_bb = butter(4, [250.0, 1500.0], btype="bandpass", fs=SR,
        output="sos")
bm = sosfilt(sos_bb, bub.mean(axis=1))
fx, dt = ruler.flux_series(bm, frame=512, hop=128)
tf = np.arange(len(fx)) * dt
tm = []
for t0 in BUB_T:
    sel = (tf >= t0 - 0.1) & (tf <= t0 + 0.1)
    tm.append(tf[sel][np.argmax(fx[sel])])
ioi = np.diff(tm)
rk2 = np.argsort(np.argsort(ioi))
rho2 = float(np.corrcoef(rk2, np.arange(len(ioi)))[0, 1])
check("exhale_accelerates",
        rho2 <= -0.85 and ioi[-1] / ioi[0] <= 0.4,
        f"{len(BUB_T)} bubbles, IOI Spearman {rho2:.2f}, "
        f"last/first {ioi[-1] / ioi[0]:.2f}")

# 5. the break: marked, loudest, and the water's weight vanishes
sos_hp = butter(4, 1000.0, btype="highpass", fs=SR, output="sos")
fx2, dt2 = ruler.flux_series(sosfilt(sos_hp, mm), frame=512,
        hop=128)
tf2 = np.arange(len(fx2)) * dt2
sel = (tf2 >= BREAK - 0.3) & (tf2 <= BREAK + 0.3)
off = tf2[sel][np.argmax(fx2[sel])] - BREAK
t_pk = np.argmax(np.abs(mm)) / SR
sos_sub = butter(4, 250.0, btype="lowpass", fs=SR, output="sos")
sub = sosfilt(sos_sub, mm)
drop = 20.0 * np.log10(
        rms(sub[int(49.0 * SR):int(51.5 * SR)])
        / rms(sub[int(53.0 * SR):int(55.5 * SR)]))
check("the_break", abs(off) <= 0.03
        and BREAK - 1.5 <= t_pk <= BREAK + 1.5
        and drop >= 10.0,
        f"splash marks {1000 * off:+.1f} ms, piece peak at "
        f"{t_pk:.2f} s, sub-250 Hz falls {drop:.1f} dB")

# 6. the first breath is the hiss climax of the whole piece.
# Measure 4000-9000: the splash is written below 3800, so this
# band belongs to the breath alone (band ownership, cf. e87
# percussion registers)
sos_h2 = butter(4, [4000.0, 9000.0], btype="bandpass", fs=SR,
        output="sos")
he = np.abs(sosfilt(sos_h2, mm))
ker = int(0.08 * SR)
he = np.convolve(he, np.ones(ker) / ker, mode="same")
t_h = np.argmax(he) / SR
check("first_breath", abs(t_h - BREATH) <= 0.4,
        f"hiss-band argmax at {t_h:.2f} s (breath written "
        f"{BREATH:.1f} s)")

# 7. the sun's major third exists only above the water.
# Chroma can't say this: E's own harmonic series contains G#
# (h5, h10, ...), so the class is never empty underwater. The
# honest claim is about a WRITTEN line: the air pad's G#6
# fundamental at hz(92) = 1648 Hz. Line prominence = FFT peak
# in 1648 Hz +/- 25 c vs the median floor 1400-1900 Hz
# (excluding +/- 50 c around the line), post vs pre.
def _gs_prom(seg):
    v = seg.mean(axis=1) * np.hanning(len(seg))
    S = np.abs(np.fft.rfft(v))
    fr = np.fft.rfftfreq(len(v), 1.0 / SR)
    f_gs = hz(92)
    line = S[(fr >= f_gs * 2 ** (-25 / 1200))
             & (fr <= f_gs * 2 ** (25 / 1200))].max()
    fl_m = ((fr >= 1400.0) & (fr <= 1900.0)
            & ((fr < f_gs * 2 ** (-50 / 1200))
               | (fr > f_gs * 2 ** (50 / 1200))))
    floor = np.median(S[fl_m])
    return 20.0 * np.log10(line / floor)

p_pre = _gs_prom(mix[int(30 * SR):int(50 * SR)])
p_post = _gs_prom(mix[int(54 * SR):int(70 * SR)])
check("sunrise_third", p_post >= 12.0 and p_pre <= 4.0,
        f"G#6 line prominence {p_pre:+.1f} dB under -> "
        f"{p_post:+.1f} dB above (gates <=+4 / >=+12)")

ruler.report(mix, "e88_surfacing")
print(f"\n{'ALL PASS' if not fails else 'FAILS: ' + str(fails)}")
sys.exit(1 if fails else 0)

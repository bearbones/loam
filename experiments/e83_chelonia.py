#!/usr/bin/env python3
"""loam e83 — Chelonia: the turtle in the light.

Operator commission: a green sea turtle feeling the current,
enjoying the sunlight catching through the water's ripple
crests. Chelonia mydas IS the green sea turtle.

Four layers, each with a written physics and its own ruler:

  - THE WATER: two padsynth pads (dark and bright draws of E2)
    crossfaded by the SURGE — 4 slow swells per loop (19.2 s
    period), so the medium both breathes in level and brightens
    as it pushes. The current is the piece's clock.
  - THE BODY: a mono E3 pad drone that pitch-LEANS +-10 cents
    with the surge (e82's warp resample, now an expressive
    gesture instead of a correction). The turtle is silent; the
    body is felt as a lean, dead-center in the image.
  - THE LIGHT: glass glints (modal GLASS, high E pentatonic)
    whose density is gated by crest(t)^3 at the RIPPLE RATE —
    1.25 Hz, exactly 96 cycles per loop — under a slower 2-cycle
    sun curve. Caustics are a point process in time: bright
    lines sweep past at the ripple rate, and clouds pass.
  - THE EXHALE: a short run of rising-chirp bubbles at each
    surge crest — the breath rides the measured swell, not the
    written one (the ruler ties the two buses together).

    python3 experiments/e83_chelonia.py [outdir]
"""

import os
import sys

import numpy as np
from scipy.signal import butter, sosfilt, sosfiltfilt

sys.path.insert(0, os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))))
from loam import SR, hz, stereo, write_wav
from loam import ruler
from loam.pads import padsynth_table, padsynth_stereo
from loam.modal import strike, GLASS
from loam.texture import bubble
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


LOOP_S = 76.8
N = int(LOOP_S * SR)
T = np.arange(N) / SR

# ---- the written physics ----------------------------------------
SURGE_K = 4                       # swells per loop (19.2 s period)
RIPPLE_HZ = 96 / LOOP_S           # 1.25 Hz, integer cycles: seam-safe
SUN_K = 2                         # cloud passes per loop
LEAN_C = 10.0                     # body lean depth, cents

surge = np.sin(2 * np.pi * SURGE_K * T / LOOP_S)      # -1..1
sun = 0.35 + 0.65 * (0.5 + 0.5 * np.cos(
        2 * np.pi * SUN_K * T / LOOP_S + 0.9)) ** 1.2
crest = (0.5 + 0.5 * np.cos(2 * np.pi * RIPPLE_HZ * T)) ** 3
CREST_TIMES = [LOOP_S / (4 * SURGE_K) + k * LOOP_S / SURGE_K
               for k in range(SURGE_K)]               # surge maxima


def add_wrap(bus, t, ss):
    i0 = int(round(t * SR)) % N
    n = len(ss)
    if i0 + n <= N:
        bus[i0:i0 + n] += ss
    else:
        k = N - i0
        bus[i0:] += ss[:k]
        bus[:n - k] += ss[k:]


# ---- the water ---------------------------------------------------
F_WATER = hz(40)                                      # E2
dark = padsynth_stereo(LOOP_S, F_WATER,
        [h ** -2.6 for h in range(1, 11)], bw_cents=45.0, seed=21)
brgt = padsynth_stereo(LOOP_S, F_WATER,
        [h ** -1.4 for h in range(1, 25)], bw_cents=45.0, seed=23)
w = 0.5 + 0.5 * surge                                 # 0..1
level = (1.0 + 0.35 * surge)[:, None]
# energy-preserving crossfade: a plain linear fade of two
# decorrelated pads dips ~6 dB mid-fade, which stamped a
# double-humped (2x surge rate) envelope on a 4-cycle design —
# normalize the fade gains so the level curve IS the envelope
dark /= rms(dark)
brgt /= rms(brgt)
gd, gb = (1.0 - w), 0.9 * w
nrm = np.sqrt(gd ** 2 + gb ** 2)
water = ((gd / nrm)[:, None] * dark + (gb / nrm)[:, None] * brgt) \
        * level
water *= 0.9 / (np.abs(water).max() + 1e-12)

# ---- the body ----------------------------------------------------
F_BODY = hz(52)                                       # E3
btab = padsynth_table(LOOP_S, F_BODY,
        [h ** -2.0 for h in range(1, 13)], bw_cents=15.0, seed=27)
ratio = 2.0 ** (LEAN_C * surge / 1200.0)
idx = np.cumsum(ratio)
idx -= idx[0]
# close the loop exactly: scale total advance to one full table
# (the rescale is a ~1e-5 detune — the seam is worth 0.02 cents)
idx *= N / (idx[-1] + ratio[-1])
body_m = np.interp(idx % N, np.arange(N + 1, dtype=float),
        np.append(btab, btab[0]))
body = stereo(body_m, 0.0)

# ---- the light ---------------------------------------------------
GLINT_MIDI = [88, 90, 92, 95, 97, 100]                # E pentatonic
GLINT_W = [0.30, 0.12, 0.16, 0.26, 0.10, 0.06]
rng = np.random.default_rng(0xC4E)
step = 0.005
tg = np.arange(0.0, LOOP_S, step)
lam = 12.0 * np.interp(tg, T, sun) * np.interp(tg, T, crest)
hits = tg[rng.random(len(tg)) < lam * step]
caust = np.zeros((N, 2))
for t0 in hits:
    m = rng.choice(GLINT_MIDI, p=GLINT_W)
    t60 = 0.25 + 0.6 * rng.random()
    g = strike(hz(m), t60, GLASS, amp=1.0, detune=1.5,
            rng=np.random.default_rng(int(rng.integers(1 << 31))),
            knock=0.02)
    g = g / (np.abs(g).max() + 1e-12)
    s_here = float(np.interp(t0, T, sun))
    c_here = float(np.interp(t0, T, crest))
    a = (0.35 + 0.65 * rng.random()) * s_here * (0.5 + 0.5 * c_here)
    add_wrap(caust, t0 + rng.uniform(0, step),
            stereo(g * a, float(rng.uniform(-0.95, 0.95))))
print(f"placed {len(hits)} glints")

# ---- the exhale --------------------------------------------------
bub = np.zeros((N, 2))
for tc in CREST_TIMES:
    t0 = tc
    f0 = rng.uniform(600.0, 800.0)
    for k in range(int(rng.integers(3, 6))):
        b = bubble(f0 * 0.88 ** k, chirp=1.3, amp=0.9 * 0.8 ** k)
        add_wrap(bub, t0, stereo(b, float(rng.uniform(-0.25, 0.25))))
        t0 += rng.uniform(0.15, 0.32)

# ---- mix ---------------------------------------------------------
dry = 0.55 * water + 0.30 * body + 0.90 * caust + 0.28 * bub
wet = reverb_loop(dry, t60=3.2, size=1.35)
sos_lp = butter(2, 2600.0, btype="lowpass", fs=SR, output="sos")
wet = np.stack([sosfilt(sos_lp, np.concatenate(
        [wet[:, c], wet[:, c]]))[N:] for c in range(2)], axis=1)
mix = 0.80 * dry + 0.38 * wet
mix *= 0.92 / (np.abs(mix).max() + 1e-12)
write_wav(os.path.join(outdir, "e83_chelonia.wav"), mix)

# ---- rulers ------------------------------------------------------
print("e83 rulers (own-bus claims, design vs measured):")

# 1. seam
check("seam", ruler.seam_rank(mix) <= 0.999,
        f"p{100 * ruler.seam_rank(mix):.2f}")

# 2. the surge is the clock: water RMS envelope has its dominant
# LF line at exactly SURGE_K cycles per loop
fr = int(0.2 * SR)
wm = water.mean(axis=1)
env = np.sqrt(np.mean(wm[:len(wm) // fr * fr].reshape(-1, fr) ** 2,
        axis=1))
sp = np.abs(np.fft.rfft(env - env.mean()))
kk = int(np.argmax(sp[1:20])) + 1
prom = sp[kk] / (np.median(sp[1:20]) + 1e-30)
check("surge_line", kk == SURGE_K and prom >= 4.0,
        f"water envelope line at {kk} cyc/loop (want {SURGE_K}), "
        f"{prom:.1f}x median")

# 3. the water brightens as it pushes: per-window centroid tracks
# the written crossfade
WIN = 1.2
nw = int(LOOP_S / WIN)
cen, des = [], []
for i in range(nw):
    a, b = int(i * WIN * SR), int((i + 1) * WIN * SR)
    cen.append(ruler.centroid_hz(wm[a:b]))
    des.append(float(np.mean(w[a:b])))
r_br = float(np.corrcoef(cen, des)[0, 1])
check("brightness_breath", r_br >= 0.7,
        f"centroid-vs-crossfade r={r_br:.3f} over {nw} windows "
        f"(centroid {min(cen):.0f}-{max(cen):.0f} Hz)")

# 4. the body leans with the current: IF contour at the surge
# rate, at the written depth (circular: measure the doubled bus)
inst = ruler.if_pitch(np.concatenate([body_m, body_m]),
        F_BODY)[N:2 * N]
cents = 1200.0 * np.log2(np.maximum(inst, 1.0) / F_BODY)
hopn = int(0.3 * SR)
cm = np.array([np.median(cents[i:i + hopn])
               for i in range(0, N - hopn, hopn)])
dm = np.array([np.median(surge[i:i + hopn]) * LEAN_C
               for i in range(0, N - hopn, hopn)])
r_lean = float(np.corrcoef(cm, dm)[0, 1])
depth = float(np.sqrt(2.0) * np.std(cm))
check("lean", r_lean >= 0.75 and 5.0 <= depth <= 16.0,
        f"IF-vs-written r={r_lean:.3f}, depth {depth:.1f}c "
        f"(want {LEAN_C:.0f}c)")

# 5. the light flickers at the ripple rate: envelope spectrum of
# the caustic bus has a line at 1.25 Hz
cm2 = caust.mean(axis=1)
sos_hp = butter(4, 1000.0, btype="highpass", fs=SR, output="sos")
he = np.abs(sosfilt(sos_hp, np.concatenate([cm2, cm2]))[N:])
fr2 = int(0.02 * SR)
he = np.sqrt(np.mean(he[:len(he) // fr2 * fr2].reshape(-1, fr2)
        ** 2, axis=1))
spe = np.abs(np.fft.rfft(he - he.mean()))
fre = np.fft.rfftfreq(len(he), fr2 / SR)
sel = (fre > 0.5) & (fre < 4.0)
pk = float(fre[sel][np.argmax(spe[sel])])
prom2 = float(spe[sel].max() / np.median(spe[sel]))
check("ripple_line", abs(pk - RIPPLE_HZ) <= 0.05 and prom2 >= 3.0,
        f"caustic flicker line {pk:.3f} Hz "
        f"(want {RIPPLE_HZ:.3f}), {prom2:.1f}x median")

# 6. clouds pass: caustic level tracks the written sun curve
# (1.6 s windows = exactly 2 ripple periods, so the flicker
# integrates out of the level measurement)
WIN2 = 1.6
nw2 = int(LOOP_S / WIN2)
lv, ds = [], []
for i in range(nw2):
    a, b = int(i * WIN2 * SR), int((i + 1) * WIN2 * SR)
    lv.append(rms(cm2[a:b]))
    ds.append(float(np.mean(sun[a:b])))
r_sun = float(np.corrcoef(lv, ds)[0, 1])
check("sun_arc", r_sun >= 0.8,
        f"caustic level vs sun curve r={r_sun:.3f} "
        f"over {nw2} windows")

# 7. the image: light scattered wide, body dead center, medium
# decorrelated
def _sidemid(x):
    s = rms((x[:, 0] - x[:, 1]) * 0.5)
    m = rms((x[:, 0] + x[:, 1]) * 0.5)
    return 20.0 * np.log10(s / m + 1e-30)


sm_c, sm_b = _sidemid(caust), _sidemid(body)
wc_w = ruler.width_corr(water)
check("image", sm_c >= -9.0 and sm_b <= -30.0 and wc_w <= 0.3,
        f"caustic side/mid {sm_c:.1f} dB, body {sm_b:.1f} dB, "
        f"water corr {wc_w:.2f}")

# 8. the light is ABOVE: register split between glints and medium
c_hi = ruler.centroid_hz(cm2)
c_lo = ruler.centroid_hz((0.55 * water + 0.30 * body).mean(axis=1))
check("register_split", c_hi / c_lo >= 5.0,
        f"caustics {c_hi:.0f} Hz vs medium {c_lo:.0f} Hz "
        f"({c_hi / c_lo:.1f}x)")

# 9. the exhale rides the MEASURED swell: for each written crest,
# the water envelope peaks nearby and the bubble run peaks within
# 0.8 s of that measured crest
te = np.arange(len(env)) * fr / SR
sos_bb = butter(4, [250.0, 1500.0], btype="bandpass", fs=SR,
        output="sos")
be = np.abs(sosfilt(sos_bb, np.concatenate(
        [bub.mean(axis=1), bub.mean(axis=1)]))[N:])
ker = int(0.05 * SR)
be = np.convolve(be, np.ones(ker) / ker, mode="same")
# crest times come from a GLOBAL phase fit of the envelope at the
# surge rate (the pad's own narrowband beating wobbles 0.2 s RMS
# frames by a couple dB, and near a crest the written sine is flat
# enough that a local argmax wanders +-1 s for free — project the
# whole loop onto the quadrature pair instead)
th = 2 * np.pi * SURGE_K * te / LOOP_S
yd = env - env.mean()
phi = float(np.arctan2(np.sum(yd * np.cos(th)),
        np.sum(yd * np.sin(th))))
t_meas0 = (np.pi / 2 - phi) / (2 * np.pi * SURGE_K / LOOP_S)
ex_ok, ex_off = True, 0.0
for k in range(SURGE_K):
    t_meas = (t_meas0 + k * LOOP_S / SURGE_K) % LOOP_S
    a, b = int((t_meas - 1.5) * SR), int((t_meas + 1.5) * SR)
    t_bub = (a + int(np.argmax(be[a:b]))) / SR
    ex_off = max(ex_off, abs(t_bub - t_meas))
    ex_ok = ex_ok and abs(t_bub - t_meas) <= 0.8
check("exhale_on_crest", ex_ok,
        f"{SURGE_K} exhales, measured crest phase offset "
        f"{t_meas0 - CREST_TIMES[0]:+.2f} s, worst bubble-to-crest "
        f"offset {ex_off:.2f} s")

# 10. the key is E, the fifth beneath it (relative claim, e35)
ch = ruler.chroma(mix)
top2 = set(np.argsort(ch)[-2:].tolist())
check("chroma_poles", top2 == {4, 11},
        f"top-2 classes {sorted(top2)} (want E=4, B=11); "
        f"E {ch[4]:.2f} B {ch[11]:.2f}")

ruler.report(mix, "e83_chelonia")
print(f"\n{'ALL PASS' if not fails else 'FAILS: ' + str(fails)}")
sys.exit(1 if fails else 0)

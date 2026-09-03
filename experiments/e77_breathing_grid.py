#!/usr/bin/env python3
"""e77 — the breathing grid: an accelerando that closes the loop.

Brand-new rhythm: e75's jhala engine with the GRID itself
breathing. Stroke rate is a smooth periodic contour,
rate(t) = 8.333 - 2.5 cos(2 pi t / 9.6) strokes/s — the strum
eases from 5.8/s at the sam to 10.8/s mid-loop and back.
Stroke times come from inverting the phase integral
phi(t) = int rate dt; the mean rate is chosen so
phi(9.6) = 80.000 exactly: eighty strokes per loop by
arithmetic, so the seam-lock survives a tempo that never
stops changing. The gat line rides every 4th stroke, chikari
da/ra fill the rest — the whole texture accelerates and
relaxes as one breath (e73/e74's breath lineage married to
the e75/e76 strum lineage).

Rulers earned:
  - ruler.rate_contour — pitch_contour's rhythmic twin.
    flux_spectrum is a claim of STATIONARITY: this grid's
    flux spectrum piles energy at the TURNING rate (10.66 Hz
    measured, where the cosine lingers) and shows no line at
    its 8.33 mean. The contour is the honest ruler for
    chirped rhythm: 0.7% median tracking, integral 80.3
    strokes vs 80 written.
  - Window width is a claim: below ~7 periods of the slowest
    rate the strongest line is often the octave (100% errors
    at 0.6-1.0 s windows; 1.2 s tracks clean).
  - Paired control: the SAME strokes on a uniform 0.12 s
    grid — flat contour, stroke line back at its mean (and at
    0.62x crown, e75's exact number: determinism as a free
    regression test).
  - In the MASTERED mix every contour outlier has a written
    mechanism: windows holding a drone strike (excluded by
    design), the da/ra alternation's own rate/2 sub-line and
    the octave (folded by design — a 2-stroke-period hand
    pattern OWNS its subharmonic). The ruler listens above
    400 Hz there: the master's lowpass tilts the balance
    toward sung fundamentals, and the strum's clock lives in
    the stroke transients.

    python3 experiments/e77_breathing_grid.py [outdir]
"""

import os
import sys

import numpy as np
from scipy.signal import butter, sosfilt

sys.path.insert(0, os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))))
from loam import SR, hz, Loop, stereo, write_wav
from loam import ruler
from loam.fdstring import fdpluck2, fdsym

outdir = sys.argv[1] if len(sys.argv) > 1 else "render"
os.makedirs(outdir, exist_ok=True)
fails = []


def check(name, cond, detail):
    print(f"  {'PASS' if cond else 'FAIL'} {name}: {detail}")
    if not cond:
        fails.append(name)


def rms(x):
    return float(np.sqrt(np.mean(np.asarray(x) ** 2)))


LOOP_S = 9.6
L = int(LOOP_S * SR)
NST = 80
RMEAN = NST / LOOP_S            # 8.333 strokes/s mean
RDEP = 2.5                      # breath depth: 5.83..10.83
RLO, RHI = RMEAN - RDEP, RMEAN + RDEP

print("== the breathing grid ==")

tg = np.linspace(0.0, LOOP_S, 200001)
phase = RMEAN * tg - RDEP * (LOOP_S / (2 * np.pi)) \
    * np.sin(2 * np.pi * tg / LOOP_S)
check("eighty strokes by arithmetic",
        abs(phase[-1] - NST) <= 1e-9,
        f"phase integral over one loop = {phase[-1]:.9f} "
        f"strokes — the mean rate {RMEAN:.3f} makes the "
        f"breathing pattern loop-periodic exactly")
tk = np.interp(np.arange(NST), phase, tg)

LINE = [50, 52, 53, 55, 53, 52, 50, 48, 47, 48, 50, 52,
        53, 52, 50, 48, 50, 52, 50, 50]
CH_DA = (hz(62) * 2 ** (0.8 / 1200), 0.9, 0.38, 0.24)
CH_RA = (hz(62) * 2 ** (-3.2 / 1200), 0.9, 0.33, 0.33)


def add_wrap(buf, at, v):
    idx = (int(at * SR) + np.arange(len(v))) % len(buf)
    np.add.at(buf, idx, v)


def build(times):
    cache = {}
    mel = np.zeros(L)
    chik = np.zeros(L)
    for k in range(NST):
        if k % 4 == 0:
            m = LINE[k // 4]
            if ("m", m) not in cache:
                cache[("m", m)] = fdpluck2(hz(m), 1.2,
                        amp=1.0, pick=0.28)
            add_wrap(mel, times[k], cache[("m", m)])
        else:
            f0, dur, amp, pick = CH_DA if k % 2 else CH_RA
            key = ("c", k % 2)
            if key not in cache:
                cache[key] = fdpluck2(f0, dur, amp=amp,
                        pick=pick)
            add_wrap(chik, times[k], cache[key])
    return mel, chik


mel, chik = build(tk)
melu, chiku = build(np.arange(NST) * 0.12)   # uniform control
meln = mel / np.abs(mel).max()
chikn = chik / np.abs(chik).max()
sar = 0.55 * meln + 0.35 * chikn
saru = 0.55 * melu / np.abs(melu).max() \
    + 0.35 * chiku / np.abs(chiku).max()

errs = []
for i in range(20):
    t = tk[4 * i]
    m = LINE[i]
    idx = np.arange(int((t + 0.02) * SR),
            int((t + 0.42) * SR)) % L
    f = ruler.partial_freq(meln[idx], hz(m) * 0.96,
            hz(m) * 1.04)
    errs.append(abs(1200 * np.log2(f / hz(m))))
check("the gat rides the breath",
        float(np.median(errs)) <= 5.0 and max(errs) <= 8.0,
        f"20 melody fundamentals at their breathing times read "
        f"back at median {np.median(errs):.1f}c, worst "
        f"{max(errs):.1f}c")

print("== the old ruler's boundary ==")

fr, fsp = ruler.flux_spectrum(sar)
msel = (fr > 1.2) & (fr < 20.0)
cv = fsp[msel].max()
b = (fr >= 5.0) & (fr <= 11.5)
i = int(np.argmax(fsp[b]))
fline, fmag = float(fr[b][i]), float(fsp[b][i] / cv)
fru, fspu = ruler.flux_spectrum(saru)
cvu = fspu[(fru > 1.2) & (fru < 20.0)].max()
bu = (fru >= 7.5) & (fru <= 9.2)
iu = int(np.argmax(fspu[bu]))
check("a breathing grid has no line at its mean",
        abs(fline - RMEAN) >= 1.0
        and (abs(fline - RHI) <= 0.35
            or abs(fline - RLO) <= 0.35)
        and fmag <= 0.80
        and fspu[bu][iu] / cvu >= 0.55
        and abs(fru[bu][iu] / RMEAN - 1) <= 0.01,
        f"strongest stroke-band line sits at {fline:.2f} Hz "
        f"({fmag:.2f}x crown) — at the TURNING rate where the "
        f"cosine lingers, {abs(fline - RMEAN):.1f} Hz away "
        f"from the 8.33 mean; the uniform control reads "
        f"{fru[bu][iu]:.2f} Hz at {fspu[bu][iu] / cvu:.2f}x "
        f"crown. flux_spectrum is a claim of stationarity")

print("== the new ruler ==")


def written_rate(t):
    return RMEAN - RDEP * np.cos(2 * np.pi * t / LOOP_S)


def contour(x):
    xx = np.concatenate([x, x[:int(2.5 * SR)]])
    t_, r_ = ruler.rate_contour(xx, 4.0, 14.0)
    keep = (t_ >= t_[0]) & (t_ < t_[0] + LOOP_S)
    return t_[keep], r_[keep]


ct, cr = contour(sar)
dev = np.abs(cr / written_rate(ct % LOOP_S) - 1)
integral = float(np.mean(cr) * LOOP_S)
check("the contour tracks the written breath",
        float(np.median(dev)) <= 0.02 and dev.max() <= 0.06,
        f"rate_contour follows rate(t) at median "
        f"{100 * np.median(dev):.1f}%, worst "
        f"{100 * dev.max():.1f}% across the loop")
check("the contour counts the strokes",
        abs(integral - NST) <= 1.5,
        f"integral of the measured contour = {integral:.1f} "
        f"strokes per loop vs 80 written — the census that "
        f"counting could not take, taken by integration")
i48 = int(np.argmin(np.abs(ct - 4.8)))
i06 = int(np.argmin(np.abs(ct - 0.9)))
check("the breath has the written shape",
        abs(cr.max() / RHI - 1) <= 0.06
        and abs(cr.min() / RLO - 1) <= 0.06
        and cr[i48] / cr[i06] >= 1.4,
        f"measured extremes {cr.min():.2f}/{cr.max():.2f} Hz "
        f"vs written {RLO:.2f}/{RHI:.2f}; mid-loop over "
        f"early-loop rate x{cr[i48] / cr[i06]:.2f}")
ctu, cru = contour(saru)
check("the uniform control does not breathe",
        cru.max() / cru.min() <= 1.05
        and abs(np.median(cru) / RMEAN - 1) <= 0.01,
        f"control contour {cru.min():.2f}..{cru.max():.2f} Hz "
        f"(x{cru.max() / cru.min():.3f}) around "
        f"{np.median(cru):.2f} — flat, at the written 8.333; "
        f"one variable changed: the stroke times")

print("== the texture ==")

menv = ruler.band_env(sar, 100.0, 210.0, 0.01)
acc_m = [menv[int((tk[k] + 0.03) / 0.01)]
        for k in range(0, NST, 4)]
acc_c = [menv[int((tk[k] + 0.03) / 0.01)]
        for k in range(NST) if k % 4]
acc = float(np.median(acc_m) / np.median(acc_c))
check("the melody carries the accent",
        acc >= 1.3,
        f"melody-band accent ratio {acc:.2f} at melody strokes "
        f"vs chikari strokes")

cuc = ruler.chroma_uniform(chik)
runner = max(v for i, v in enumerate(cuc) if i != 2)
check("the chikari is one pitch",
        cuc[2] >= 2.5 * runner,
        f"chikari bus chroma class 2 at {cuc[2]:.2f} vs "
        f"runner-up {runner:.2f}")

# ---- the mix ---------------------------------------------------
_, tb = fdsym([hz(n) for n in [50, 52, 53, 55, 57, 59, 60, 62]],
        sar / np.abs(sar).max(), buses=True, jawari=True,
        gain=5000.0)
pans = np.linspace(-0.55, 0.55, 8)
tnorm = np.abs(tb).max() + 1e-12
taraf_st = np.zeros((L, 2))
for b_, p in zip(tb, pans):
    gg = (b_[:L] / tnorm) * 0.05
    taraf_st[:, 0] += gg * np.cos((p + 1) * np.pi / 4)
    taraf_st[:, 1] += gg * np.sin((p + 1) * np.pi / 4)
norm = np.abs(sar).max() + 1e-12
halo_db = 20 * np.log10(rms(taraf_st.sum(axis=1))
        / rms(sar * 0.85 / norm * 0.9))
check("the halo sits under the strum",
        -32.0 <= halo_db <= -8.0,
        f"taraf/strum {halo_db:.1f} dB")

DRONE = [("sa+", hz(50.015), 112, 0.96, 0.15, 0.50),
        ("sa-", hz(49.985), 112, 2.16, -0.15, 0.50),
        ("SA", hz(38), 138, 3.36, 0.35, 0.75)]
loop = Loop(LOOP_S, seed=77)
for name, f0d, n, at, pan, ampd in DRONE:
    loop.add(at, stereo(fdpluck2(f0d, 12.0, amp=ampd, N=n),
            pan))
loop.add(0.0, stereo(meln * 0.55 * 0.85 / norm * 0.9, 0.15))
loop.add(0.0, stereo(chikn * 0.35 * 0.85 / norm * 0.9, -0.35))
loop.add(0.0, taraf_st)
mix = loop.master(lp_hz=6500.0, drive=1.2)
mono = mix.mean(axis=1)

# the strum's clock lives in the stroke transients — listen
# above the sung fundamentals (the master's lowpass tilted
# the balance); exclude windows holding a written drone
# strike; fold the alternation's own rate/2 sub-line and the
# octave, both written features of a 2-stroke-period pattern
sos_hp = butter(4, 400.0, btype="high", fs=SR, output="sos")
xf = sosfilt(sos_hp, np.concatenate([mono,
        mono[:int(2.5 * SR)]]))
mt, mr = ruler.rate_contour(xf, 4.5, 11.5)
keep = (mt >= mt[0]) & (mt < mt[0] + LOOP_S)
mt, mr = mt[keep], mr[keep]
clear = np.array([all(min(abs(c - dat), LOOP_S - abs(c - dat))
        > 0.6 for _, _, _, dat, _, _ in DRONE)
        for c in (mt % LOOP_S)])
wrm = written_rate(mt % LOOP_S)
folded = np.min(np.abs(mr[:, None] * np.array([1.0, 2.0, 0.5])
        / wrm[:, None] - 1), axis=1)
raw_ok = np.abs(mr / wrm - 1) <= 0.06
check("the listener's contour still breathes",
        folded[clear].max() <= 0.06
        and float(np.mean(raw_ok[clear])) >= 0.6,
        f"mastered mix (heard above 400 Hz): of "
        f"{int(clear.sum())} windows clear of drone strikes, "
        f"{int(raw_ok[clear].sum())} read the stroke rate "
        f"directly and every one lands within "
        f"{100 * folded[clear].max():.1f}% after folding the "
        f"hand-pattern's own rate/2 sub-line and the octave — "
        f"each deviation has a written mechanism")
check("seam", ruler.seam_rank(mix) <= 0.999,
        f"p{100 * ruler.seam_rank(mix):.2f}")

cu = ruler.chroma_uniform(mono)
check("Sa crowns the mix",
        int(np.argmax(cu)) == 2,
        f"chroma crowns class 2 at {max(cu):.2f}")

out = np.concatenate([mix, mix])
wav = os.path.join(outdir, "e77_breathing_grid.wav")
write_wav(wav, out)
ruler.report(out, "breathing_grid")

if fails:
    print("FAILED RULERS:", fails)
    sys.exit(1)
print("ALL RULERS PASS")

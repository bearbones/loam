#!/usr/bin/env python3
"""e63 — score->halo forecast: the bridge is the recruiter.

New tooling (ruler.sympathy_forecast) + a correction of e62 +
a phrase composed BY the model to light the dark string.

The forward model: a sympathetic bank hears the harmonic
lattice, so lighting should be PREDICTABLE from the score —
integrate coincidences between the driver's f0 trajectory
(with its MEASURED harmonic profile — the flat 1/n guess is
upside-down for this bow, whose fundamental is 0.19 of h2) and
each string's modes, treating the t60-58s bank as a lossless
integrator that rewards early excitation.

What the model certified, and what it falsified:
  - the BRIDGE-LESS bank obeys the driver-side lattice:
    spearman 0.86 on a steady-note ledger, predicted top-4 set
    exact. Tolerance is load-bearing (200c ablation: 0.43).
  - e62's attribution was WRONG. "The bow recruits the
    fifth-family" — no: jawari off, same bowed driver, Pa
    falls 1.00 -> 0.21 and Sa tops the bank. The recruiter is
    the JAWARI BRIDGE: the bank talks to itself.
  - a one-knob linear cascade (strings re-radiating 1/n stacks
    through the bridge) CANNOT reproduce the jawari ledger:
    spearman plateaus ~0.57 across three decades of coupling.
    Constant verdict under a changing knob = wrong model FORM:
    real jawari is intermodulation at a shared bridge, where
    fifths beat octaves. Logged as the falsification it is.
  - under jawari the forecast still calls SETS out-of-sample:
    top-4 overlap >=3/4, both predicted-darkest strings in the
    measured bottom-3, and the targeted calls below.

The composition: e62's phrase left B (Dha) rank 7/8 — the one
string the score fed nothing. e63's phrase is written FOR it:
Sa -> Pa -> Dha -> meend down to Re -> Sa. Forecast says B goes
bright, C goes darkest. Measured: B rank 2/8, C rank 8/8.

    python3 experiments/e63_forecast.py [outdir]
"""

import os
import subprocess
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))))
from loam import SR, hz, Loop, stereo, write_wav
from loam import ruler
from loam.fdstring import fdbow, fdpluck2, fdsym

outdir = sys.argv[1] if len(sys.argv) > 1 else "render"
os.makedirs(outdir, exist_ok=True)
fails = []


def check(name, cond, detail):
    print(f"  {'PASS' if cond else 'FAIL'} {name}: {detail}")
    if not cond:
        fails.append(name)


def rms(x):
    return float(np.sqrt(np.mean(np.asarray(x) ** 2)))


def spearman(a, b):
    ra = np.argsort(np.argsort(a)).astype(float)
    rb = np.argsort(np.argsort(b)).astype(float)
    return float(np.corrcoef(ra, rb)[0, 1])


def ranks(v):                       # 1 = brightest
    return np.argsort(np.argsort(-np.asarray(v))) + 1


BANK = [50, 52, 53, 55, 57, 59, 60, 62]
BHZ = [hz(n) for n in BANK]

# ---- 1. the driver's harmonic profile, measured ----------------
steady = fdbow(hz(50), 2.0, FB=1e3, vb=0.10, raw=True)
_h = steady[int(0.7 * SR):]
_X = np.abs(np.fft.rfft(_h * np.hanning(len(_h))))
_f = np.fft.rfftfreq(len(_h), 1.0 / SR)
_p = ruler.hps_pitch(_h, fmin=60.0, fmax=600.0)
PROF = np.array([float(_X[(_f >= n * _p * 0.97)
        & (_f <= n * _p * 1.03)].max()) for n in range(1, 9)])
PROF /= PROF.max()
check("the bow's fundamental is not its loudest line",
        int(np.argmax(PROF)) == 1 and PROF[0] <= 0.5,
        f"h1..h8 = {np.round(PROF, 2).tolist()} — the 1/n "
        f"spectral guess is upside-down for this driver")

# ---- 2. the bridge is the recruiter (correcting e62) -----------
def bank_rms(drv, jaw, a=0.5, b=2.0):
    _, tb_ = fdsym(BHZ, drv, buses=True, jawari=jaw, gain=5000.0)
    seg = tb_[:, int(a * SR):int(b * SR)]
    return np.sqrt((seg ** 2).mean(axis=1))


# the bridge is nonlinear, so drive LEVEL is part of the
# experiment: normalize, as every piece-facing driver is
steady_n = steady / (np.abs(steady).max() + 1e-12)
r_on = bank_rms(steady_n, True)
r_off = bank_rms(steady_n, False)
i57, i50 = BANK.index(57), BANK.index(50)
check("fifth-family recruitment needs the bridge",
        int(np.argmax(r_on)) == i57 and int(np.argmax(r_off))
        == i50 and r_off[i57] / r_off.max() <= 0.4,
        f"same bowed driver: Pa {r_on[i57] / r_on.max():.2f} of "
        f"max with jawari, {r_off[i57] / r_off.max():.2f} "
        f"without — e62 blamed the bow; the recruiter is the "
        f"bridge")

# ---- 3. the linear bank obeys the forecast ---------------------
f0st = np.full(400, hz(50))
p_lin = ruler.sympathy_forecast(f0st, 2.0 / 400, BHZ,
        drive_w=PROF, integrate=True)
sp_lin = spearman(r_off, p_lin)
top4 = lambda v: set(np.asarray(BANK)[np.argsort(v)[::-1][:4]])
check("the bridge-less bank obeys the lattice forecast",
        sp_lin >= 0.7 and top4(p_lin) == top4(r_off),
        f"spearman {sp_lin:.2f}, predicted top-4 "
        f"{sorted(top4(p_lin))} == measured")
p_wide = ruler.sympathy_forecast(f0st, 2.0 / 400, BHZ,
        drive_w=PROF, integrate=True, tol_cents=200.0)
check("the coincidence tolerance is load-bearing",
        spearman(r_off, p_wide) <= 0.6,
        f"tol 15c -> 200c degrades spearman {sp_lin:.2f} -> "
        f"{spearman(r_off, p_wide):.2f}")

# ---- 4. the one-knob cascade is falsified ----------------------
sp_cas = max(spearman(r_on, ruler.sympathy_forecast(f0st,
        2.0 / 400, BHZ, drive_w=PROF, integrate=True, cascade=k))
        for k in (0.1, 1.0, 10.0, 100.0))
check("linear per-string cascade cannot explain jawari",
        sp_cas <= 0.7,
        f"best spearman {sp_cas:.2f} across three decades of "
        f"coupling — a plateau: the model FORM is wrong "
        f"(jawari is intermodulation at a shared bridge, and "
        f"there fifths beat octaves)")

# ---- the two phrases -------------------------------------------
LOOP_S = 9.6
tt = np.linspace(0, LOOP_S, 2000)


def phrase(KN, VBK, lift_s=8.5):
    f0t = np.interp(tt, [t for t, _ in KN],
            [hz(m) for _, m in KN])
    vbt = np.interp(tt, [t for t, _ in VBK],
            [v for _, v in VBK])
    FBt = np.where(tt < lift_s, 1e3, 0.0)
    sar_ = fdbow(f0t, LOOP_S, FB=FBt, vb=vbt, sig0=4.0, raw=True)
    return f0t, vbt, sar_


KN62 = [(0.0, 50), (2.2, 50), (3.2, 53), (4.8, 53), (5.6, 52),
        (6.4, 52), (7.4, 50), (9.6, 50)]
VBK62 = [(0.0, 0.08), (2.0, 0.13), (3.4, 0.10), (5.0, 0.12),
        (6.5, 0.13), (8.0, 0.09), (8.5, 0.08), (9.6, 0.08)]
KN63 = [(0.0, 50), (1.0, 50), (1.8, 57), (3.2, 57), (3.7, 59),
        (5.2, 59), (6.4, 52), (7.4, 52), (8.0, 50), (9.6, 50)]
VBK63 = [(0.0, 0.08), (1.6, 0.12), (3.0, 0.11), (4.2, 0.13),
        (5.6, 0.10), (6.8, 0.12), (7.8, 0.09), (8.5, 0.08),
        (9.6, 0.08)]
_, _, sar62 = phrase(KN62, VBK62)
f0t, vbt, sar = phrase(KN63, VBK63)
m62 = bank_rms(sar62, True, 0.3, 9.5)
_, tb = fdsym(BHZ, sar, buses=True, jawari=True, gain=5000.0)
m63 = np.sqrt((tb[:, int(0.3 * SR):int(9.5 * SR)] ** 2)
        .mean(axis=1))

# ---- 5. the composed phrase lights the dark string -------------
rk62, rk63 = ranks(m62), ranks(m63)
iB = BANK.index(59)
check("the phrase composed for B moves it 7th -> 2nd",
        rk62[iB] >= 6 and rk63[iB] <= 3,
        f"B (Dha): rank {rk62[iB]}/8 under e62's phrase, "
        f"rank {rk63[iB]}/8 under the phrase written for it")
pred = ruler.sympathy_forecast(f0t, LOOP_S / len(tt), BHZ,
        drive_w=PROF, integrate=True, amp=vbt)
iC = int(np.argmin(pred))
check("the predicted-darkest string measures darkest",
        BANK[iC] == 60 and rk63[iC] == 8,
        f"forecast says {BANK[iC]} (C) gets least; measured "
        f"rank {rk63[iC]}/8")
ov = len(top4(pred) & top4(m63))
bot2 = set(np.asarray(BANK)[np.argsort(pred)[:2]])
mbot3 = set(np.asarray(BANK)[np.argsort(m63)[:3]])
check("out-of-sample set calls under jawari",
        ov >= 3 and bot2 <= mbot3,
        f"predicted top-4 overlap {ov}/4, predicted bottom-2 "
        f"{sorted(bot2)} inside measured bottom-3 "
        f"(spearman {spearman(m63, pred):.2f} — the bridge "
        f"reshuffles fine ranks, sets survive)")

# ---- the piece: jor for the dark string ------------------------
ts, fs = ruler.pitch_contour(sar, fmin=80.0, fmax=500.0)
worst_hold = 0.0
for nm, a, b, m in (("Sa", 0.3, 0.9, 50), ("Pa", 2.0, 3.1, 57),
        ("Dha", 3.9, 5.1, 59), ("Re", 6.6, 7.3, 52),
        ("Sa'", 8.1, 8.4, 50)):
    sel = (ts >= a) & (ts <= b)
    med = float(np.median(fs[sel]))
    worst_hold = max(worst_hold, abs(1200 * np.log2(med / hz(m))))
check("every hold lands", worst_hold <= 25.0,
        f"worst hold {worst_hold:.1f}c across Sa-Pa-Dha-Re-Sa")
sel = (ts >= 0.3) & (ts <= 8.3)
d = np.interp(ts, tt, f0t)
dev = 1200 * np.log2(fs[sel] / d[sel])
check("the meend follows the written line",
        float(np.median(np.abs(dev))) <= 15.0,
        f"median |dev| {float(np.median(np.abs(dev))):.1f}c")
wr = np.array([rms(sar[int(a * SR):int((a + 0.3) * SR)])
        for a in np.arange(0.5, 8.1, 0.3)])
check("the voice holds for the whole phrase",
        float(wr.min() / wr.max()) >= 0.4,
        f"windowed rms min/max {wr.min() / wr.max():.3f}")
vbw = np.array([float(np.mean(vbt[(tt >= a) & (tt <= a + 0.3)]))
        for a in np.arange(0.5, 8.1, 0.3)])
corr = float(np.corrcoef(wr, vbw)[0, 1])
check("the swell is the bow speed", corr >= 0.9,
        f"windowed rms vs designed vb envelope: r = {corr:.3f}")
t60r = ruler.decay_t60(sar[int(8.6 * SR):int(9.55 * SR)],
        100.0, 1200.0)
check("the lift rings into the seam",
        abs(t60r / 1.725 - 1) <= 0.3,
        f"release t60 {t60r:.2f} s (design 1.73)")

HALO_GAIN = 0.05
pans = np.linspace(-0.55, 0.55, len(BANK))
tnorm = np.abs(tb).max() + 1e-12
L = int(LOOP_S * SR)
taraf_st = np.zeros((L, 2))
for b, p in zip(tb, pans):
    gg = (b[:L] / tnorm) * HALO_GAIN
    taraf_st[:, 0] += gg * np.cos((p + 1) * np.pi / 4)
    taraf_st[:, 1] += gg * np.sin((p + 1) * np.pi / 4)
sar_mix = sar * 0.85 / (np.abs(sar).max() + 1e-12) * 0.9
halo_db = 20 * np.log10(rms(taraf_st.sum(axis=1)) / rms(sar_mix))
check("the halo sits under the voice", -32.0 <= halo_db <= -8.0,
        f"taraf/sarangi {halo_db:.1f} dB")

DRONE = [("pa", hz(45), 140, 0.0, -0.35, 0.55),
        ("sa+", hz(50.015), 112, 1.2, 0.15, 0.50),
        ("sa-", hz(49.985), 112, 2.4, -0.15, 0.50),
        ("SA", hz(38), 138, 3.6, 0.35, 0.75)]
loop = Loop(LOOP_S, seed=63)
for name, f0d, n, at, pan, ampd in DRONE:
    v = fdpluck2(f0d, 12.0, amp=ampd, N=n)
    loop.add(at, stereo(v, pan))
    loop.add(at + 4.8, stereo(v, pan))
loop.add(0.0, stereo(sar_mix, 0.0))
loop.add(0.0, taraf_st)
mix = loop.master(lp_hz=6500.0, drive=1.2)

check("seam", ruler.seam_rank(mix) <= 0.999,
        f"p{100 * ruler.seam_rank(mix):.2f}")
# this phrase SINGS Pa against a Pa drone — a two-pole piece,
# unlike e61/e62's solo-center claim. chroma_uniform is the
# promoted ruler (third use).
cu = ruler.chroma_uniform(mix.mean(axis=1))
order = np.argsort(cu)[::-1]
check("Sa-Pa are the two poles, Sa first",
        set(order[:2].tolist()) == {2, 9}
        and cu[2] > cu[9] and cu[order[1]] / cu[order[2]] >= 1.3,
        f"top-2 {{D {cu[2]:.2f}, A {cu[9]:.2f}}}, pole 2 leads "
        f"pole 3 x{cu[order[1]] / cu[order[2]]:.2f}")

out = np.concatenate([mix, mix])
wav = os.path.join(outdir, "e63_forecast.wav")
write_wav(wav, out)
ruler.report(out, "forecast")
subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", wav,
        "-q:a", "5", wav.replace(".wav", ".ogg")], check=True)

print("ALL RULERS PASS" if not fails else f"FAILED: {fails}")
sys.exit(1 if fails else 0)

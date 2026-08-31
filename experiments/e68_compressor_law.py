#!/usr/bin/env python3
"""e68 — the compressor law becomes the forecast (v3).

The thread carried since e64 ("fold the compressor into
sympathy_forecast"), closed. Refinement cycle: no new sound —
the forward model finally learns what the bridge does.

The measurement that cracked it: e64's flat-fed phrase driven
into the bank at FOUR levels (x0.05 .. x1.0), jawari off and
on. Per string the contact is a saturator — identity below a
knee, gain <= 0.21 on the overfed sung strings above it. But
across strings at EQUAL feed the outputs differ 2.3x, so
velocity-rms is the wrong variable: the barrier engages on
DISPLACEMENT, and a lower string swings further per unit
velocity (u ~ v/omega). Scaling the knee by omega collapses
the family (log-residual 0.26 vs 0.33 frequency-blind).

Two structural lessons ride in the law's form:
  - a frequency-blind compressor CANNOT move a rank: any
    shared monotone map preserves feed order. Demonstrated as
    an in-script control (the a=0 law reproduces v2's spearman
    to the last digit). The entire rank repair lives in the
    omega term.
  - the law is a floor, not a crown: v3 rescues the ledgers v2
    inverts (flat -0.07 -> 0.76, ph62 -0.07 -> 0.81 — the
    F<->C anomaly, resolved at last) at the cost of the one v2
    nailed (ph63 0.98 -> 0.52). Worst case rises from -0.07 to
    0.52, and a 16x band of calibration error does not break
    the floor.

The piece: "the climb" — jor ascending the Kafi lower
tetrachord, Sa-Re-ga-ma, every note a bank string, sung long
and hard. v3's out-of-sample call on its own halo: the sung
strings SINK (mean rank 6.5/8) and the halo answers from the
unsung upper lattice — sing hardest, glow least. Spearman
0.93, v2 reads the same ledger upside-down (-0.36).

    python3 experiments/e68_compressor_law.py [outdir]
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


def fund_presence(x, f0):
    X = np.abs(np.fft.rfft(x * np.hanning(len(x))))
    f = np.fft.rfftfreq(len(x), 1.0 / SR)
    s = (f >= f0 * 0.95) & (f <= f0 * 1.05)
    return float(X[s].max() / (X[f < 2000.0].max() + 1e-12))


BANK = [50, 52, 53, 55, 57, 59, 60, 62]
BHZ = [hz(n) for n in BANK]
BHZa = np.array(BHZ)
LOOP_S = 9.6
L = int(LOOP_S * SR)
tt = np.arange(L) / SR
tf = np.linspace(0, LOOP_S, 2000)


def played_prof(sar, f0t):
    """driver harmonic profile measured from the take (e64)."""
    prof = np.zeros(8)
    for a in np.arange(0.3, 8.2, 0.3):
        seg = sar[int(a * SR):int((a + 0.3) * SR)]
        f0 = float(np.interp(a + 0.15, tt, f0t))
        X = np.abs(np.fft.rfft(seg * np.hanning(len(seg))))
        fr = np.fft.rfftfreq(len(seg), 1.0 / SR)
        for n in range(1, 9):
            s = (fr >= n * f0 * 0.95) & (fr <= n * f0 * 1.05)
            if s.any():
                prof[n - 1] += float(X[s].max())
    return prof / prof.max()


def bank_rms(drv, jaw):
    _, tb_ = fdsym(BHZ, drv, buses=True, jawari=jaw, gain=5000.0)
    seg = tb_[:, int(0.3 * SR):int(9.5 * SR)]
    return np.sqrt((seg ** 2).mean(axis=1))


# ---- the probe driver: e64's flat-fed phrase -------------------
SEQ = [50, 53, 52, 55, 52, 50]
KNf = []
t = 0.0
for m in SEQ:
    KNf.append((t, m))
    KNf.append((min(t + 0.8, LOOP_S), m))
    t += 1.6
KNf.append((LOOP_S, SEQ[-1]))
f0f = np.interp(tt, [t for t, _ in KNf], [hz(m) for _, m in KNf])
VBKf = [(0.0, 0.085), (0.8, 0.10), (2.4, 0.11), (4.0, 0.115),
        (5.6, 0.105), (7.2, 0.11), (8.5, 0.085), (9.6, 0.085)]
vbf = np.interp(tt, [t for t, _ in VBKf], [v for _, v in VBKf])
sarf = fdbow(f0f, LOOP_S, FB=np.where(tt < 8.5, 1e4 * vbf, 0.0),
        vb=vbf, sig0=4.0, raw=True)
sarf /= np.abs(sarf).max()

# ---- 1. the transfer curve: four levels, off and on ------------
SCALES = [0.05, 0.15, 0.4, 1.0]
mLs, mJs = {}, {}
for c in SCALES:
    mLs[c] = bank_rms(sarf * c, False)
    mJs[c] = bank_rms(sarf * c, True)
check("the linear bank is linear",
        float(np.abs(mLs[0.05] * 20.0 / mLs[1.0] - 1.0).max())
        <= 0.02,
        f"x20 drive -> x{float((mLs[1.0] / mLs[0.05]).mean()):.1f}"
        f" output, worst rel err "
        f"{float(np.abs(mLs[0.05] * 20 / mLs[1.0] - 1).max()):.3f}"
        f" (the off-bridge bank is superposition)")
g_lo = mJs[0.05] / mLs[0.05]
n_id = int(np.sum(np.abs(g_lo - 1.0) <= 0.05))
check("below the knee the barrier is a bystander",
        n_id >= 6,
        f"x0.05 drive: {n_id}/8 strings within 5% of identity "
        f"(the outlier is Re at gain {float(g_lo[1]):.2f} — a "
        f"soft contact can also ADD sizzle)")
SUNG = {50, 52, 53, 55}
g_hi = mJs[1.0] / mLs[1.0]
gs = [float(g_hi[i]) for i, n in enumerate(BANK) if n in SUNG]
gu = [float(g_hi[i]) for i, n in enumerate(BANK)
        if n not in SUNG]
check("above it the fed are taxed, the light are spared",
        max(gs) <= 0.3 and min(gu) >= 0.55,
        f"x1.0 drive: sung-string gains <= {max(gs):.2f}, "
        f"unsung >= {min(gu):.2f} — a per-string limiter")

# ---- 2. the knee is displacement, not speed --------------------
mL = np.concatenate([mLs[c] for c in SCALES])
mJ = np.concatenate([mJs[c] for c in SCALES])
ii = np.tile(np.arange(8), len(SCALES))


def fit_law(a):
    x0 = mL * (200.0 / BHZa[ii]) ** a
    best = None
    for K in np.geomspace(x0.min() / 3, x0.max() * 3, 60):
        for q in np.linspace(0.5, 8.0, 31):
            for p in np.linspace(0.05, 1.5, 30):
                pred = mL * (1.0 + (x0 / K) ** q) ** (-p)
                r = np.log(mJ) - np.log(pred)
                s = float(np.sqrt((r ** 2).mean()))
                if best is None or s < best[0]:
                    best = (s, K, q, p)
    return best


res0, K0, q0, p0 = fit_law(0.0)
res1, K1, q1, p1 = fit_law(1.0)
check("the knee is displacement, not speed",
        res1 <= 0.30 and res1 <= 0.85 * res0,
        f"omega-scaled knee: log-residual {res1:.2f} vs "
        f"{res0:.2f} frequency-blind (K={K1:.2f}, high-end "
        f"slope {1 - q1 * p1:.2f}) — u ~ v/omega, the low "
        f"strings swing further and saturate first")

# ---- 3. the four-ledger test: v2 vs v3 -------------------------
proff = played_prof(sarf, f0f)
f0ff = np.interp(tf, [t for t, _ in KNf],
        [hz(m) for _, m in KNf])
vbff = np.interp(tf, [t for t, _ in VBKf],
        [v for _, v in VBKf])
V2 = dict(drive_w=None, integrate=True, node=0.93, tap=0.12,
        vel=True)
predf = ruler.sympathy_forecast(f0ff, LOOP_S / 2000, BHZ,
        **{**V2, "drive_w": proff}, amp=vbff)
s_cal = float(np.median(mLs[1.0] / predf))
COMP = (s_cal, K1, q1, p1)


def law_a0(feed):
    return feed * (1.0 + (feed / K0) ** q0) ** (-p0)


def phrase63(KN, VBK):
    f0t = np.interp(tt, [t for t, _ in KN],
            [hz(m) for _, m in KN])
    vbt = np.interp(tt, [t for t, _ in VBK],
            [v for _, v in VBK])
    # e62/e63's phrases as shipped: flat FB=1e3, pre-ratio-rule
    sar = fdbow(f0t, LOOP_S, FB=np.where(tt < 8.5, 1e3, 0.0),
            vb=vbt, sig0=4.0, raw=True)
    return f0t, vbt, sar / np.abs(sar).max()


KN62 = [(0.0, 50), (2.2, 50), (3.2, 53), (4.8, 53), (5.6, 52),
        (6.4, 52), (7.4, 50), (9.6, 50)]
VBK62 = [(0.0, 0.08), (2.0, 0.13), (3.4, 0.10), (5.0, 0.12),
        (6.5, 0.13), (8.0, 0.09), (8.5, 0.08), (9.6, 0.08)]
KN63 = [(0.0, 50), (1.0, 50), (1.8, 57), (3.2, 57), (3.7, 59),
        (5.2, 59), (6.4, 52), (7.4, 52), (8.0, 50), (9.6, 50)]
VBK63 = [(0.0, 0.08), (1.6, 0.12), (3.0, 0.11), (4.2, 0.13),
        (5.6, 0.10), (6.8, 0.12), (7.8, 0.09), (8.5, 0.08),
        (9.6, 0.08)]
ledgers = {}
for nm, KN, VBK in (("ph62", KN62, VBK62), ("ph63", KN63, VBK63)):
    f0t, vbt, sar = phrase63(KN, VBK)
    m = bank_rms(sar, True)
    f0tf_ = np.interp(tf, [t for t, _ in KN],
            [hz(m_) for _, m_ in KN])
    vbtf_ = np.interp(tf, [t for t, _ in VBK],
            [v for _, v in VBK])
    pred = ruler.sympathy_forecast(f0tf_, LOOP_S / 2000, BHZ,
            **{**V2, "drive_w": played_prof(sar, f0t)}, amp=vbtf_)
    ledgers[nm] = (pred, m)
steady = fdbow(hz(50), 2.0, FB=1e3, vb=0.10, raw=True)
stn = steady / np.abs(steady).max()
_, tbs = fdsym(BHZ, stn, buses=True, jawari=True, gain=5000.0)
ms = np.sqrt((tbs[:, int(0.5 * SR):int(2.0 * SR)] ** 2)
        .mean(axis=1))
h = stn[int(0.7 * SR):]
X = np.abs(np.fft.rfft(h * np.hanning(len(h))))
fr = np.fft.rfftfreq(len(h), 1.0 / SR)
p_ = ruler.hps_pitch(h, fmin=60.0, fmax=600.0)
PROFs = np.array([float(X[(fr >= n * p_ * 0.97)
        & (fr <= n * p_ * 1.03)].max()) for n in range(1, 9)])
PROFs /= PROFs.max()
preds = ruler.sympathy_forecast(np.full(400, hz(50)), 2.0 / 400,
        BHZ, **{**V2, "drive_w": PROFs})
ledgers["flat"] = (predf, mJs[1.0])
ledgers["steady"] = (preds, ms)


def v3(pred, sc=s_cal):
    x = sc * pred * (200.0 / BHZa)
    return sc * pred * (1.0 + (x / K1) ** q1) ** (-p1)


sp2 = {nm: spearman(pred, m) for nm, (pred, m) in ledgers.items()}
sp3 = {nm: spearman(v3(pred), m)
        for nm, (pred, m) in ledgers.items()}
p62, m62 = ledgers["ph62"]
check("a frequency-blind compressor cannot move a rank",
        abs(spearman(law_a0(s_cal * p62), m62) - sp2["ph62"])
        <= 1e-9,
        f"the a=0 law reproduces v2's ph62 spearman "
        f"{sp2['ph62']:.2f} to the last digit — a shared "
        f"monotone map preserves feed order; ALL of v3's rank "
        f"repair lives in the omega term")
check("v3 rescues what v2 inverts",
        sp2["flat"] <= 0.2 and sp2["ph62"] <= 0.2
        and sp3["flat"] >= 0.6 and sp3["ph62"] >= 0.7,
        f"flat {sp2['flat']:.2f} -> {sp3['flat']:.2f}, ph62 "
        f"{sp2['ph62']:.2f} -> {sp3['ph62']:.2f} — e63's F<->C "
        f"anomaly was the compressor all along")
worst2 = min(sp2.values())
worst3 = min(sp3.values())
check("the law is a floor, not a crown",
        worst3 >= 0.45 and worst2 <= 0.1,
        f"worst ledger {worst2:.2f} v2 -> {worst3:.2f} v3 "
        f"(the cost is honest: ph63 {sp2['ph63']:.2f} -> "
        f"{sp3['ph63']:.2f} — saturation flattens the fine "
        f"ranks v2 nailed; steady {sp2['steady']:.2f} -> "
        f"{sp3['steady']:.2f})")
floor = min(min(spearman(v3(pred, s_cal * f), m)
        for nm, (pred, m) in ledgers.items())
        for f in (0.25, 1.0, 4.0))
check("the floor survives a sloppy calibration",
        floor >= 0.45,
        f"scale swept x0.25..x4 (a 16x band): worst ledger "
        f"still {floor:.2f} — the verdict is not riding on "
        f"one fitted number")

# ---- the piece: the climb --------------------------------------
KN = [(0.0, 50), (1.2, 50), (1.6, 52), (2.8, 52), (3.2, 53),
        (4.4, 53), (4.8, 55), (6.4, 55), (6.8, 53), (7.4, 53),
        (7.8, 50), (9.6, 50)]
VBK = [(0.0, 0.085), (0.7, 0.105), (2.0, 0.11), (3.6, 0.115),
        (5.0, 0.12), (6.6, 0.11), (7.6, 0.10), (8.5, 0.085),
        (9.6, 0.085)]
f0t = np.interp(tt, [t for t, _ in KN], [hz(m) for _, m in KN])
vbt = np.interp(tt, [t for t, _ in VBK], [v for _, v in VBK])
sar = fdbow(f0t, LOOP_S, FB=np.where(tt < 8.5, 1e4 * vbt, 0.0),
        vb=vbt, sig0=4.0, raw=True)
sarn = sar / np.abs(sar).max()

HOLDS = (("Sa", 0.3, 1.1, 50), ("Re", 1.9, 2.7, 52),
        ("ga", 3.5, 4.3, 53), ("ma", 5.1, 6.3, 55),
        ("ga'", 7.0, 7.3, 53), ("Sa'", 8.0, 8.4, 50))
locks = [ruler.lock_ratio(sar[int(a * SR):int(b * SR)], hz(m))
        for _, a, b, m in HOLDS]
fps = [fund_presence(sar[int(a * SR):int(b * SR)], hz(m))
        for _, a, b, m in HOLDS]
ts, fsc = ruler.pitch_contour(sar, fmin=80.0, fmax=500.0)
worst_hold = 0.0
for nm, a, b, m in HOLDS:
    sel = (ts >= a) & (ts <= b)
    med = float(np.median(fsc[sel]))
    worst_hold = max(worst_hold,
            abs(1200 * np.log2(med / hz(m))))
check("the climb sings every step",
        min(locks) >= 0.2 and min(fps) >= 0.05
        and worst_hold <= 25.0,
        f"lock >= {min(locks):.2f}, presence >= {min(fps):.2f}, "
        f"worst hold {worst_hold:.1f}c across Sa-Re-ga-ma-ga-Sa")
sel = (ts >= 0.3) & (ts <= 8.3)
dline = np.interp(ts, tt, f0t)
dev = 1200 * np.log2(fsc[sel] / dline[sel])
check("the line follows the written climb",
        float(np.median(np.abs(dev))) <= 15.0,
        f"median |dev| {float(np.median(np.abs(dev))):.1f}c")
wr = np.array([rms(sar[int(a * SR):int((a + 0.3) * SR)])
        for a in np.arange(0.5, 8.1, 0.3)])
vbw = np.array([float(np.mean(vbt[(tt >= a) & (tt <= a + 0.3)]))
        for a in np.arange(0.5, 8.1, 0.3)])
check("the voice holds and swells on bow speed",
        float(wr.min() / wr.max()) >= 0.4
        and float(np.corrcoef(wr, vbw)[0, 1]) >= 0.9,
        f"rms min/max {wr.min() / wr.max():.3f}, swell corr "
        f"{float(np.corrcoef(wr, vbw)[0, 1]):.3f}")
t60r = ruler.decay_t60(sar[int(8.6 * SR):int(9.55 * SR)],
        100.0, 1200.0)
check("the lift rings into the seam",
        abs(t60r / 1.725 - 1) <= 0.3,
        f"release t60 {t60r:.2f} s (design 1.73)")

# the halo, and v3's out-of-sample call on it (via the ruler
# API this time — the law lives in the library now)
_, tb = fdsym(BHZ, sarn, buses=True, jawari=True, gain=5000.0)
m68 = np.sqrt((tb[:, int(0.3 * SR):int(9.5 * SR)] ** 2)
        .mean(axis=1))
f0tf = np.interp(tf, [t for t, _ in KN], [hz(m) for _, m in KN])
vbtf = np.interp(tf, [t for t, _ in VBK], [v for _, v in VBK])
prof68 = played_prof(sarn, f0t)
pred2 = ruler.sympathy_forecast(f0tf, LOOP_S / 2000, BHZ,
        **{**V2, "drive_w": prof68}, amp=vbtf)
pred3 = ruler.sympathy_forecast(f0tf, LOOP_S / 2000, BHZ,
        **{**V2, "drive_w": prof68}, amp=vbtf, comp=COMP)
sp68_2, sp68_3 = spearman(pred2, m68), spearman(pred3, m68)
top = lambda v, k: set(np.asarray(BANK)[np.argsort(v)[::-1][:k]])
bot = lambda v, k: set(np.asarray(BANK)[np.argsort(v)[:k]])
check("v3 calls the climb's halo out-of-sample",
        sp68_3 >= 0.8 and top(pred3, 2) <= top(m68, 3)
        and bot(pred3, 2) <= bot(m68, 3),
        f"spearman {sp68_3:.2f}; predicted top-2 "
        f"{sorted(top(pred3, 2))} in measured top-3, predicted "
        f"bottom-2 {sorted(bot(pred3, 2))} in measured bottom-3")
check("v2 alone reads the climb upside-down",
        sp68_2 <= 0.0,
        f"spearman {sp68_2:.2f} — the linear model promotes "
        f"exactly the strings the barrier will tax")
rk68 = ranks(m68)
mr_sung = float(np.mean([rk68[BANK.index(n)] for n in SUNG]))
check("sing hardest, glow least",
        mr_sung >= 5.5 and BANK[int(np.argmax(m68))] not in SUNG,
        f"sung tetrachord mean measured rank {mr_sung:.1f}/8; "
        f"the halo's crown is {BANK[int(np.argmax(m68))]} "
        f"(c'), a string the phrase never touches")

# ---- the mix ---------------------------------------------------
HALO_GAIN = 0.05
pans = np.linspace(-0.55, 0.55, len(BANK))
tnorm = np.abs(tb).max() + 1e-12
taraf_st = np.zeros((L, 2))
for b, p in zip(tb, pans):
    gg = (b[:L] / tnorm) * HALO_GAIN
    taraf_st[:, 0] += gg * np.cos((p + 1) * np.pi / 4)
    taraf_st[:, 1] += gg * np.sin((p + 1) * np.pi / 4)
sar_mix = sar * 0.85 / (np.abs(sar).max() + 1e-12) * 0.9
halo_db = 20 * np.log10(rms(taraf_st.sum(axis=1))
        / rms(sar_mix))
check("the halo sits under the voice",
        -32.0 <= halo_db <= -8.0,
        f"taraf/sarangi {halo_db:.1f} dB")

DRONE = [("pa", hz(45), 140, 0.0, -0.35, 0.55),
        ("sa+", hz(50.015), 112, 1.2, 0.15, 0.50),
        ("sa-", hz(49.985), 112, 2.4, -0.15, 0.50),
        ("SA", hz(38), 138, 3.6, 0.35, 0.75)]
loop = Loop(LOOP_S, seed=68)
for name, f0d, n, at, pan, ampd in DRONE:
    v = fdpluck2(f0d, 12.0, amp=ampd, N=n)
    loop.add(at, stereo(v, pan))
    loop.add(at + 4.8, stereo(v, pan))
loop.add(0.0, stereo(sar_mix, 0.0))
loop.add(0.0, taraf_st)
mix = loop.master(lp_hz=6500.0, drive=1.2)

check("seam", ruler.seam_rank(mix) <= 0.999,
        f"p{100 * ruler.seam_rank(mix):.2f}")
# claim shape follows the phrase: the climb sings the whole
# lower tetrachord long and equal-ish — Sa leads (drone +
# returns), and the top-4 chroma IS the sung set
cu = ruler.chroma_uniform(mix.mean(axis=1))
order = np.argsort(cu)[::-1]
m01 = cu[order[0]] / cu[order[1]]
m45 = cu[order[3]] / cu[order[4]]
check("Sa leads and the tetrachord owns the top-4",
        order[0] == 2 and set(order[:4].tolist()) == {2, 4, 5, 7}
        and m01 >= 1.3 and m45 >= 1.4,
        f"D {cu[2]:.2f} leads x{m01:.2f}; top-4 "
        f"{sorted(order[:4].tolist())} == sung {{D,E,F,G}}, "
        f"x{m45:.2f} over the rest")

out = np.concatenate([mix, mix])
wav = os.path.join(outdir, "e68_compressor_law.wav")
write_wav(wav, out)
ruler.report(out, "compressor_law")
subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", wav,
        "-q:a", "5", wav.replace(".wav", ".ogg")], check=True)

print("ALL RULERS PASS" if not fails else f"FAILED: {fails}")
sys.exit(1 if fails else 0)

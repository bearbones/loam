#!/usr/bin/env python3
"""e64 — the flat halo: composing evenness, finding the compressor.

Refinement cycle on e63's forecast, planned as "use v2 receiver
physics to compose the flattest ledger." The bank and the bow
both had corrections waiting:

RECEIVER PHYSICS (v2, zero fitted knobs): fdsym injects force
at x=0.93 and reads velocity at x=0.12, so mode m couples as
|sin(.93 m pi)| * |sin(.12 m pi)| and speaks with a velocity
factor m*fs. The fundamental couples at 0.22, m=4 at 0.78 —
the bank is BUILT for its upper modes. On e63's session
ledgers this lifted jawari-steady 0.76->0.88 and the e63
phrase 0.52->0.81 spearman.

THE BOW'S CLIFF (correcting e61): the certified operating
point FB=1e3, vb=0.10 sits on a chaotic multistability edge —
one phrase's vb ramp survives it, another falls onto the
even-harmonics-only double-slip branch at 0.6 s and HYSTERESIS
keeps it there (e61-63 survived on initial conditions). The
honest regime detector is ruler.lock_ratio (odd/even), born
from a broken classifier: "tallest line = 2 f0" misreads a
bright locked tone as octave. Certified recipe: FB = 1e4 * vb
(Schelleng's wedge scales with speed: flat FB=1e3 at vb=0.065
CHOKES — force above the speed-scaled maximum), vb in
[0.08, 0.14], stepwise notes, slow glides.

THE COMPRESSOR (explaining e63's anomaly): drive the same
flat-fed phrase into the bank with jawari off and on. Linear:
the sung four strings rank exactly 1-4. Jawari: they sink to
mean rank 6.5 and the ledger CV halves. The jawari contact is
a per-string LIMITER — overfed strings work the barrier
hardest and pay the contact tax. This is e63's F<->C anomaly
(sung F darkest, lattice C 2nd) as a law, not a glitch: the
jawari bank flattens its own halo.

The piece: "sarva" — Sa ga Re ma Re Sa, the phrase v2 chose to
feed all eight strings, bowed on the certified ratio recipe.
Its measured ledger CV 0.24 is the flattest of the series
(e62 0.28, e63 0.35): every string lit, none shouting.

    python3 experiments/e64_flat_halo.py [outdir]
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


def ranks(v):
    return np.argsort(np.argsort(-np.asarray(v))) + 1


BANK = [50, 52, 53, 55, 57, 59, 60, 62]
BHZ = [hz(n) for n in BANK]
LOOP_S = 9.6
tt = np.linspace(0, LOOP_S, 2000)

# ---- 1. the lock shelf: FB = 1e4 * vb --------------------------
worst_oe = np.inf
for m in (50, 53, 60):
    for vb in (0.08, 0.12):
        x = fdbow(hz(m), 2.0, FB=1e4 * vb, vb=vb, raw=True)[SR:]
        worst_oe = min(worst_oe, ruler.lock_ratio(x, hz(m)))
check("constant-ratio bowing locks across the swell band",
        worst_oe >= 0.3,
        f"odd/even >= {worst_oe:.2f} over notes x vb in "
        f"[0.08, 0.12] at FB = 1e4*vb")
chk = fdbow(hz(50), 2.0, FB=1e3, vb=0.065, raw=True)[SR:]
check("flat force below the speed-scaled maximum chokes",
        rms(chk) <= 0.01,
        f"FB=1e3 at vb=0.065: rms {rms(chk):.4f} — Schelleng's "
        f"ceiling scales with bow speed; force must follow")

# ---- 2. the cliff exhibit (correcting e61's operating point) ---
KN_X = [(0.0, 50), (1.1, 50), (1.6, 52), (2.7, 52), (3.2, 53),
        (4.3, 53), (4.8, 55), (5.9, 55), (6.4, 60), (7.5, 60),
        (8.0, 50), (9.6, 50)]
f0x = np.interp(tt, [t for t, _ in KN_X], [hz(m) for _, m in KN_X])
VBX = [(0.0, 0.08), (1.3, 0.12), (2.9, 0.10), (4.5, 0.13),
        (6.1, 0.11), (7.7, 0.12), (8.5, 0.08), (9.6, 0.08)]
vbx = np.interp(tt, [t for t, _ in VBX], [v for _, v in VBX])
sx = fdbow(f0x, LOOP_S, FB=np.where(tt < 8.5, 1e3, 0.0), vb=vbx,
        raw=True)
oe0 = ruler.lock_ratio(sx[int(0.25 * SR):int(1.0 * SR)], hz(50))
oe_ga = ruler.lock_ratio(sx[int(3.45 * SR):int(4.2 * SR)], hz(53))
check("the e61 operating point is a cliff edge",
        oe0 >= 0.3 and oe_ga <= 0.05,
        f"same flat FB=1e3 that e61-63 shipped: first Sa hold "
        f"locked ({oe0:.2f}), ga hold on the even-only octave "
        f"branch ({oe_ga:.3f}) — hysteresis keeps a fallen "
        f"phrase fallen")

# ---- the piece phrase: sarva (chosen by v2 for flatness) -------
# provenance: exhaustive search over stepwise Sa-X-Y-Z-W-Sa Kafi
# phrases, minimizing predicted-feed CV under the v2 model
SEQ = [50, 53, 52, 55, 52, 50]
KN = []
t = 0.0
for i, m in enumerate(SEQ):
    KN.append((t, m))
    KN.append((min(t + 0.8, LOOP_S), m))
    t += 1.6
KN.append((LOOP_S, SEQ[-1]))
f0t = np.interp(tt, [t for t, _ in KN], [hz(m) for _, m in KN])
VBK = [(0.0, 0.085), (0.8, 0.10), (2.4, 0.11), (4.0, 0.115),
        (5.6, 0.105), (7.2, 0.11), (8.5, 0.085), (9.6, 0.085)]
vbt = np.interp(tt, [t for t, _ in VBK], [v for _, v in VBK])
FBt = np.where(tt < 8.5, 1e4 * vbt, 0.0)
sar = fdbow(f0t, LOOP_S, FB=FBt, vb=vbt, sig0=4.0, raw=True)

oes = [ruler.lock_ratio(
        sar[int((i * 1.6 + 0.2) * SR):
            int(min(i * 1.6 + 0.75, 9.4) * SR)], hz(m))
        for i, m in enumerate(SEQ)]
check("every hold stays on the fundamental branch",
        min(oes) >= 0.2,
        f"odd/even {[round(v, 2) for v in oes]} across "
        f"Sa-ga-Re-ma-Re-Sa (the recipe holds in a phrase)")

ts, fsc = ruler.pitch_contour(sar, fmin=80.0, fmax=500.0)
worst_hold = 0.0
for i, m in enumerate(SEQ):
    sel = (ts >= i * 1.6 + 0.2) & (ts <= min(i * 1.6 + 0.75, 9.4))
    med = float(np.median(fsc[sel]))
    worst_hold = max(worst_hold, abs(1200 * np.log2(med / hz(m))))
check("every hold lands", worst_hold <= 25.0,
        f"worst hold {worst_hold:.1f}c")
sel = (ts >= 0.3) & (ts <= 8.3)
d = np.interp(ts, tt, f0t)
dev = 1200 * np.log2(fsc[sel] / d[sel])
check("the meend follows the written line",
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
        f"{float(np.corrcoef(wr, vbw)[0, 1]):.3f} (with FB "
        f"riding vb, the swell survives the ratio rule)")
t60r = ruler.decay_t60(sar[int(8.6 * SR):int(9.55 * SR)],
        100.0, 1200.0)
check("the lift rings into the seam",
        abs(t60r / 1.725 - 1) <= 0.3,
        f"release t60 {t60r:.2f} s (design 1.73)")

# ---- 3. flat feed by design (v2 forecast, played profile) ------
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
prof /= prof.max()
pred = ruler.sympathy_forecast(f0t, LOOP_S / len(tt), BHZ,
        drive_w=prof, integrate=True, node=0.93, tap=0.12,
        vel=True)
pcv = float(np.std(pred) / np.mean(pred))
check("the phrase feeds the bank evenly by design",
        pcv <= 0.15,
        f"v2 predicted-feed CV {pcv:.3f} (e62's phrase 0.33, "
        f"e63's 0.45 under the same model)")

# ---- 4. the compressor: jawari on/off A/B ----------------------
_, tbL = fdsym(BHZ, sar, buses=True, jawari=False, gain=5000.0)
_, tbJ = fdsym(BHZ, sar, buses=True, jawari=True, gain=5000.0)
mL = np.sqrt((tbL[:, int(0.3 * SR):int(9.5 * SR)] ** 2)
        .mean(axis=1))
mJ = np.sqrt((tbJ[:, int(0.3 * SR):int(9.5 * SR)] ** 2)
        .mean(axis=1))
SUNG = {50, 52, 53, 55}
top4L = set(np.asarray(BANK)[np.argsort(mL)[::-1][:4]])
check("the linear bank returns what the phrase sings",
        top4L == SUNG,
        f"jawari off: top-4 {sorted(top4L)} == the sung notes "
        f"(v2's feed account, confirmed on its home ground)")
rkL, rkJ = ranks(mL), ranks(mJ)
mrL = float(np.mean([rkL[BANK.index(n)] for n in SUNG]))
mrJ = float(np.mean([rkJ[BANK.index(n)] for n in SUNG]))
check("the jawari contact taxes the overfed",
        mrL <= 3.5 and mrJ >= 5.5,
        f"sung-set mean rank {mrL:.1f} linear -> {mrJ:.1f} "
        f"jawari — the fed sink, the lattice-lit rise "
        f"(e63's F<->C anomaly, now a law)")
cvL = float(np.std(mL) / np.mean(mL))
cvJ = float(np.std(mJ) / np.mean(mJ))
check("the jawari bank flattens its own halo",
        cvJ <= 0.7 * cvL,
        f"ledger CV {cvL:.3f} linear -> {cvJ:.3f} jawari — "
        f"the bridge is a per-string compressor")

# ---- 5. flattest halo of the series ----------------------------
def phrase_ledger(KNp, VBKp):
    f0p = np.interp(tt, [t for t, _ in KNp],
            [hz(m) for _, m in KNp])
    vbp = np.interp(tt, [t for t, _ in VBKp],
            [v for _, v in VBKp])
    sp = fdbow(f0p, LOOP_S, FB=np.where(tt < 8.5, 1e3, 0.0),
            vb=vbp, sig0=4.0, raw=True)
    _, tbp = fdsym(BHZ, sp, buses=True, jawari=True, gain=5000.0)
    mm = np.sqrt((tbp[:, int(0.3 * SR):int(9.5 * SR)] ** 2)
            .mean(axis=1))
    return float(np.std(mm) / np.mean(mm))


cv62 = phrase_ledger(
    [(0.0, 50), (2.2, 50), (3.2, 53), (4.8, 53), (5.6, 52),
     (6.4, 52), (7.4, 50), (9.6, 50)],
    [(0.0, 0.08), (2.0, 0.13), (3.4, 0.10), (5.0, 0.12),
     (6.5, 0.13), (8.0, 0.09), (8.5, 0.08), (9.6, 0.08)])
cv63 = phrase_ledger(
    [(0.0, 50), (1.0, 50), (1.8, 57), (3.2, 57), (3.7, 59),
     (5.2, 59), (6.4, 52), (7.4, 52), (8.0, 50), (9.6, 50)],
    [(0.0, 0.08), (1.6, 0.12), (3.0, 0.11), (4.2, 0.13),
     (5.6, 0.10), (6.8, 0.12), (7.8, 0.09), (8.5, 0.08),
     (9.6, 0.08)])
check("the composed halo is the flattest of the series",
        cvJ < cv62 and cvJ < cv63,
        f"measured ledger CV: e62 {cv62:.3f}, e63 {cv63:.3f}, "
        f"e64 {cvJ:.3f} — every string lit, none shouting")

# ---- the mix ---------------------------------------------------
HALO_GAIN = 0.05
pans = np.linspace(-0.55, 0.55, len(BANK))
tnorm = np.abs(tbJ).max() + 1e-12
L = int(LOOP_S * SR)
taraf_st = np.zeros((L, 2))
for b, p in zip(tbJ, pans):
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
loop = Loop(LOOP_S, seed=64)
for name, f0d, n, at, pan, ampd in DRONE:
    v = fdpluck2(f0d, 12.0, amp=ampd, N=n)
    loop.add(at, stereo(v, pan))
    loop.add(at + 4.8, stereo(v, pan))
loop.add(0.0, stereo(sar_mix, 0.0))
loop.add(0.0, taraf_st)
mix = loop.master(lp_hz=6500.0, drive=1.2)

check("seam", ruler.seam_rank(mix) <= 0.999,
        f"p{100 * ruler.seam_rank(mix):.2f}")
# claim shape follows the phrase (e63's lesson): a phrase
# composed for EVENNESS has no single pole — its chroma is the
# sung set, evenly held. e61's "Sa is the center" gate belongs
# to phrases with a home dwell.
cu = ruler.chroma_uniform(mix.mean(axis=1))
order = np.argsort(cu)[::-1]
margin = cu[order[0]] / cu[order[1]]
sung_mass = float(cu[[2, 4, 5, 7]].sum())
check("the chroma is the phrase's own evenness",
        set(order[:4].tolist()) == {2, 4, 5, 7}
        and sung_mass >= 0.55 and margin <= 1.4,
        f"top-4 == the sung classes {{D,E,F,G}} at "
        f"{sung_mass:.2f} of the mass, no pole above "
        f"x{margin:.2f} — flat bank, flat chroma")

out = np.concatenate([mix, mix])
wav = os.path.join(outdir, "e64_flat_halo.wav")
write_wav(wav, out)
ruler.report(out, "flat_halo")
subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", wav,
        "-q:a", "5", wav.replace(".wav", ".ogg")], check=True)

print("ALL RULERS PASS" if not fails else f"FAILED: {fails}")
sys.exit(1 if fails else 0)

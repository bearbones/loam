#!/usr/bin/env python3
"""e66 — the gat: sarangi meets the theka.

Refinement joining the bowed voice (e61-65) to the tabla
vocabulary (e59-60): a vilambit gat in tintal — two avartans,
the theka underneath, the sarangi singing a stepwise Kafi line
composed ON the slot grid, sam arrivals shared.

The physics gate for playing in laya: gat motion means 0.3 s
glides, far quicker than e64's certified 0.8 s. Measured: the
bow takes them ALL in lock — provided the take ENTERS through
the vb=0.085 shelf. The ATTACK is the recipe:
  - slammed flat at vb=0.105 from t=0, the string never finds
    Helmholtz — it plays a fundamental-less multiphonic
    (lines at {2,5,7}*f0) at healthy rms for the WHOLE take,
    and even lock_ratio is fooled by the strong 5f0 (the
    honest slam detector is fundamental PRESENCE).
  - ramped in from the shelf over 0.6 s, every downstream
    hold locks (odd/even 0.40-1.11) and lands within 3c,
    0.3 s glides included.

The piece: theka dha dhin dhin dha / dha dhin dhin dha / dha
tin tin ta / ta dhin dhin dha (khali bass-hole measured in
both avartans), sarangi Sa-Re-ga-Re-Sa twice — arriving home
a breath BEFORE each sam and holding through it, mukhda
fashion; the lift at 8.5 s rings the wrap. Taraf halo and
tanpura as established.

    python3 experiments/e66_gat_sarangi.py [outdir]
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
from loam.membrane import fddrum

outdir = sys.argv[1] if len(sys.argv) > 1 else "render"
os.makedirs(outdir, exist_ok=True)
fails = []


def check(name, cond, detail):
    print(f"  {'PASS' if cond else 'FAIL'} {name}: {detail}")
    if not cond:
        fails.append(name)


def rms(x):
    return float(np.sqrt(np.mean(np.asarray(x) ** 2)))


def fund_presence(x, f0):
    X = np.abs(np.fft.rfft(x * np.hanning(len(x))))
    f = np.fft.rfftfreq(len(x), 1.0 / SR)
    s = (f >= f0 * 0.95) & (f <= f0 * 1.05)
    return float(X[s].max() / (X[f < 2000.0].max() + 1e-12))


# ---- 1. the attack is the recipe -------------------------------
KNr = [(0.0, 50), (0.9, 50), (1.2, 52), (1.8, 52), (2.1, 53),
        (3.0, 53), (3.3, 52), (3.9, 52), (4.2, 50), (5.4, 50)]
ttr = np.arange(int(5.4 * SR)) / SR
f0r = np.interp(ttr, [t for t, _ in KNr], [hz(m) for _, m in KNr])
vb_slam = np.full_like(ttr, 0.105)
slam = fdbow(f0r, 5.4, FB=1e4 * vb_slam, vb=vb_slam, sig0=4.0,
        raw=True)
vb_ramp = np.interp(ttr, [0.0, 0.6, 4.6, 5.4],
        [0.085, 0.105, 0.11, 0.10])
ramp = fdbow(f0r, 5.4, FB=1e4 * vb_ramp, vb=vb_ramp, sig0=4.0,
        raw=True)
RH = ((1.35, 1.75, 52), (2.25, 2.95, 53), (3.45, 3.85, 52),
        (4.35, 5.2, 50))
fp_slam = min(fund_presence(slam[int(a * SR):int(b * SR)], hz(m))
        for a, b, m in RH)
fp_ramp = min(fund_presence(ramp[int(a * SR):int(b * SR)], hz(m))
        for a, b, m in RH)
r_slam = rms(slam[SR:])
check("a slammed attack poisons the whole take",
        fp_slam <= 0.05 and r_slam >= 0.05,
        f"flat vb=0.105 from t=0: fundamental {fp_slam:.3f} of "
        f"the strongest line on EVERY later hold, at healthy rms "
        f"{r_slam:.2f} — a multiphonic the level rulers never "
        f"see (and lock_ratio is fooled by its strong 5f0: "
        f"presence, not parity, catches it)")
lk_ramp = min(ruler.lock_ratio(ramp[int(a * SR):int(b * SR)],
        hz(m)) for a, b, m in RH)
check("entered through the shelf, the bow plays in laya",
        fp_ramp >= 0.1 and lk_ramp >= 0.2,
        f"0.6 s ramp from vb=0.085: fundamental >= "
        f"{fp_ramp:.2f}, lock >= {lk_ramp:.2f} across the same "
        f"holds — 0.3 s glides, all taken in stride")

# ---- the theka (e59 vocabulary, certified there) ---------------
LOAD, RS = 40.0, 0.45
F1, F1A, F1D = 283.8, 105.6, 141.2
na = fddrum(F1, 1.5, strike=(0.55, 0.0), load=LOAD, rs=RS,
        sig_s=60.0)
tun = fddrum(F1, 1.5, strike=(0.0, 0.0), load=LOAD, rs=RS,
        sig_s=60.0)
ge = fddrum(F1A, 1.0, strike=(0.30, 0.0), load=LOAD, rs=RS,
        sig0=9.0, sig_s=20.0)
ge_sam = fddrum(F1D, 1.0, strike=(0.30, 0.0), load=LOAD, rs=RS,
        sig0=9.0, sig_s=20.0)
TRE = {"dha": (na, 1.0), "dhin": (tun, 0.95), "tin": (tun, 0.95),
        "ta": (na, 0.9)}
BAS = {"dha": (ge, 0.9), "dhin": (ge, 0.9)}

SUB = 0.3
LOOP_S = 9.6
L = int(LOOP_S * SR)
THEKA = ["dha", "dhin", "dhin", "dha", "dha", "dhin", "dhin",
        "dha", "dha", "tin", "tin", "ta", "ta", "dhin", "dhin",
        "dha"]
EVENTS = [(i + 16 * av, b) for av in (0, 1)
        for i, b in enumerate(THEKA)]
KHALI_SLOTS = {9, 10, 11, 12, 25, 26, 27, 28}

tre = np.zeros(L + 2 * SR)
bas = np.zeros(L + 2 * SR)
for t_slot, b in EVENTS:
    a = int(t_slot * SUB * SR)
    v, g = TRE[b]
    tre[a:a + len(v)] += v * g
    if b in BAS:
        v, g = BAS[b]
        if b == "dha" and t_slot in (0, 16):
            v = ge_sam
        bas[a:a + len(v)] += v * g
tre, bas = tre[:L], bas[:L]
drums = stereo(tre, 0.25) + stereo(bas, -0.25)

design = sorted(t * SUB for t, _ in EVENTS) + [LOOP_S]
dbl = np.concatenate([drums, drums]).mean(axis=1)
onsets = np.array([t for t in ruler.onset_times(dbl,
        min_sep=0.12) if t <= LOOP_S + 0.06])
d = np.asarray(design)
miss = [dt for dt in d if not (np.abs(onsets - dt) <= 0.05).any()]
extra = [t for t in onsets
        if not (np.abs(d - t) <= 0.06).any()]
check("every theka stroke sounds, and nothing else",
        len(miss) == 0 and len(extra) == 0,
        f"{len(d) - len(miss)}/{len(d)} matched, {len(extra)} "
        f"extras across two avartans")

w0, w1 = int(0.08 * SR), int(0.28 * SR)
mono_d = drums.mean(axis=1)
hann = np.hanning(w1 - w0)


def band_rms(seg):
    p = np.abs(np.fft.rfft(seg * hann)) ** 2
    f = np.fft.rfftfreq(len(seg), 1.0 / SR)
    return float(np.sqrt(p[(f >= 30.0) & (f <= 100.0)].sum()))


be = np.array([band_rms(mono_d[int(k * SUB * SR) + w0:
        int(k * SUB * SR) + w1]) for k in range(32)])
kh = np.array([k in KHALI_SLOTS for k in range(32)])
hole = float(np.median(be[kh]) / np.median(be[~kh]))
check("the khali is a bass hole in both avartans", hole <= 0.35,
        f"khali/bhari bass-band energy {hole:.3f}")
pr = ruler.pulse_rate(mono_d, 2.0, 5.0, lo=300.0, hi=2500.0)
check("the theka keeps the pulse", abs(pr - 1.0 / SUB) <= 0.2,
        f"designed {1.0 / SUB:.2f} Hz, measured {pr:.2f} Hz")

# ---- the gat line ----------------------------------------------
tt = np.arange(L) / SR
KN = [(0.0, 50), (0.9, 50), (1.2, 52), (1.8, 52), (2.1, 53),
        (3.0, 53), (3.3, 52), (3.9, 52), (4.2, 50), (5.1, 50),
        (5.4, 52), (6.0, 52), (6.3, 53), (7.2, 53), (7.5, 52),
        (8.1, 52), (8.4, 50), (9.6, 50)]
f0t = np.interp(tt, [t for t, _ in KN], [hz(m) for _, m in KN])
VBK = [(0.0, 0.085), (0.6, 0.105), (2.5, 0.115), (4.6, 0.10),
        (6.6, 0.115), (8.0, 0.095), (8.5, 0.085), (9.6, 0.085)]
vbt = np.interp(tt, [t for t, _ in VBK], [v for _, v in VBK])
FBt = np.where(tt < 8.5, 1e4 * vbt, 0.0)
sar = fdbow(f0t, LOOP_S, FB=FBt, vb=vbt, sig0=4.0, raw=True)

HOLDS = (("Sa", 0.15, 0.85, 50), ("Re", 1.35, 1.75, 52),
        ("ga", 2.25, 2.95, 53), ("Re'", 3.45, 3.85, 52),
        ("Sa|sam", 4.35, 5.05, 50), ("Re2", 5.55, 5.95, 52),
        ("ga2", 6.45, 7.15, 53), ("Re3", 7.65, 8.05, 52),
        ("Sa'", 8.42, 8.48, 50))
locks = [ruler.lock_ratio(sar[int(a * SR):int(b * SR)], hz(m))
        for _, a, b, m in HOLDS[:-1]]
fps = [fund_presence(sar[int(a * SR):int(b * SR)], hz(m))
        for _, a, b, m in HOLDS[:-1]]
check("every gat hold is locked and voiced",
        min(locks) >= 0.2 and min(fps) >= 0.1,
        f"lock >= {min(locks):.2f}, fundamental presence >= "
        f"{min(fps):.2f} across 8 holds at gat speed")
ts, fsc = ruler.pitch_contour(sar, fmin=80.0, fmax=500.0)
worst_hold = 0.0
for nm, a, b, m in HOLDS:
    sel = (ts >= a) & (ts <= b)
    med = float(np.median(fsc[sel]))
    worst_hold = max(worst_hold, abs(1200 * np.log2(med / hz(m))))
check("every hold lands, sam arrivals included",
        worst_hold <= 25.0,
        f"worst hold {worst_hold:.1f}c — the voice is home "
        f"BEFORE each sam and holds through it")
sel = (ts >= 0.3) & (ts <= 8.3)
dline = np.interp(ts, tt, f0t)
dev = 1200 * np.log2(fsc[sel] / dline[sel])
check("the line follows the written gat",
        float(np.median(np.abs(dev))) <= 15.0,
        f"median |dev| {float(np.median(np.abs(dev))):.1f}c")
t60r = ruler.decay_t60(sar[int(8.6 * SR):int(9.55 * SR)],
        100.0, 1200.0)
check("the lift rings the wrap into sam",
        abs(t60r / 1.725 - 1) <= 0.3,
        f"release t60 {t60r:.2f} s (design 1.73)")

# ---- the mix ---------------------------------------------------
BANK = [50, 52, 53, 55, 57, 59, 60, 62]
_, tb = fdsym([hz(n) for n in BANK], sar, buses=True,
        jawari=True, gain=5000.0)
HALO_GAIN = 0.05
pans = np.linspace(-0.55, 0.55, len(BANK))
tnorm = np.abs(tb).max() + 1e-12
taraf_st = np.zeros((L, 2))
for b, p in zip(tb, pans):
    gg = (b[:L] / tnorm) * HALO_GAIN
    taraf_st[:, 0] += gg * np.cos((p + 1) * np.pi / 4)
    taraf_st[:, 1] += gg * np.sin((p + 1) * np.pi / 4)
sar_mix = sar * 0.85 / (np.abs(sar).max() + 1e-12) * 0.9
halo_db = 20 * np.log10(rms(taraf_st.sum(axis=1)) / rms(sar_mix))
check("the halo sits under the voice", -32.0 <= halo_db <= -8.0,
        f"taraf/sarangi {halo_db:.1f} dB")
drums_g = drums * 0.8
bal_db = 20 * np.log10(rms(drums_g.mean(axis=1))
        / rms(sar_mix))
check("the theka sits beside the voice, not over it",
        -14.0 <= bal_db <= 0.0,
        f"drums/sarangi {bal_db:.1f} dB")

DRONE = [("pa", hz(45), 140, 0.0, -0.35, 0.55),
        ("sa+", hz(50.015), 112, 1.2, 0.15, 0.50),
        ("sa-", hz(49.985), 112, 2.4, -0.15, 0.50),
        ("SA", hz(38), 138, 3.6, 0.35, 0.75)]
loop = Loop(LOOP_S, seed=66)
for name, f0d, n, at, pan, ampd in DRONE:
    v = fdpluck2(f0d, 12.0, amp=ampd, N=n)
    loop.add(at, stereo(v, pan))
    loop.add(at + 4.8, stereo(v, pan))
loop.add(0.0, drums_g)
loop.add(0.0, stereo(sar_mix, 0.0))
loop.add(0.0, taraf_st)
mix = loop.master(lp_hz=6500.0, drive=1.2)

check("seam", ruler.seam_rank(mix) <= 0.999,
        f"p{100 * ruler.seam_rank(mix):.2f}")
# claim shape follows the phrase: the gat line approaches Re
# four times and dwells there — the bowed voice, not the
# theka, owns the mix's chroma. Its three-note compass is the
# top of the table, the orbited Re first.
cu = ruler.chroma_uniform(mix.mean(axis=1))
order = np.argsort(cu)[::-1]
m34 = cu[order[2]] / cu[order[3]]
check("the gat's compass owns the chroma, Re the pivot",
        set(order[:3].tolist()) == {2, 4, 5}
        and order[0] == 4 and m34 >= 1.8,
        f"E {cu[4]:.2f} > D {cu[2]:.2f} > F {cu[5]:.2f}, then "
        f"x{m34:.1f} down to the drone's A — Sa-Re-ga is the "
        f"whole story and Re is where the line lives")

out = np.concatenate([mix, mix])
wav = os.path.join(outdir, "e66_gat_sarangi.wav")
write_wav(wav, out)
ruler.report(out, "gat_sarangi")
subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", wav,
        "-q:a", "5", wav.replace(".wav", ".ogg")], check=True)

print("ALL RULERS PASS" if not fails else f"FAILED: {fails}")
sys.exit(1 if fails else 0)

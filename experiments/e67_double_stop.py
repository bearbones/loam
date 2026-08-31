#!/usr/bin/env python3
"""e67 — double stops: the tempered fifth beats.

New texture: two strings under one bow. And with it, the
physics of temperament made audible and measured:

  - an equal-tempered fifth is 2 cents narrow of pure, so a
    bowed Sa+Pa dyad BEATS where Sa's h3 meets Pa's h2. The
    full measurement chain: each string's SOUNDING pitch
    (own-bus, friction-flattened -2.7c/-3.2c), predicted beat
    |3*fSa - 2*fPa| = 0.60 Hz, measured in the mix's 440 Hz
    band envelope: 0.61 Hz at 2.4 dB depth.
  - the just-intonation control (Pa = 1.5*Sa exactly) goes
    STILL: depth collapses 2.4 -> 0.3 dB. Its rate reading is
    meaningless at that depth — you cannot read the rate of a
    beat that isn't there — so the JI claim is DEPTH, not
    rate (beat_profile's own detrending lesson, extended).

The piece: jor in double stops — the melody line (Sa - ga -
Re - Sa, certified recipe: shelf attack, ratio rule, stepwise)
over a bowed Sa pedal on the second string, both lifting at
8.5 s. The dyad readback is e58's polyphonic practice: both
notes found in every two-note hold, with the -50c shifted
design refused.

    python3 experiments/e67_double_stop.py [outdir]
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


def fund_presence(x, f0):
    X = np.abs(np.fft.rfft(x * np.hanning(len(x))))
    f = np.fft.rfftfreq(len(x), 1.0 / SR)
    s = (f >= f0 * 0.95) & (f <= f0 * 1.05)
    return float(X[s].max() / (X[f < 2000.0].max() + 1e-12))


# ---- 1. the tempered fifth beats, the just fifth is still ------
DUR = 6.0
ttp = np.arange(int(DUR * SR)) / SR
vbp = np.interp(ttp, [0.0, 0.6, DUR], [0.085, 0.105, 0.105])
fSa = hz(50)


def bow_steady(f0):
    return fdbow(f0, DUR, FB=1e4 * vbp, vb=vbp, sig0=4.0,
            raw=True)


res = {}
for nm, fPa in (("ET", hz(57)), ("JI", 1.5 * fSa)):
    A = bow_steady(fSa)[SR:]
    B = bow_steady(fPa)[SR:]
    pA = ruler.hps_pitch(A, fmin=100.0, fmax=200.0)
    pB = ruler.hps_pitch(B, fmin=180.0, fmax=280.0)
    mixd = A / np.abs(A).max() + B / np.abs(B).max()
    br, bd = ruler.beat_profile(mixd, 400.0, 480.0)
    res[nm] = (abs(3 * pA - 2 * pB), br, bd, pA, pB)
pred, br, bd, pA, pB = res["ET"]
check("the tempered fifth beats at the predicted rate",
        abs(br / pred - 1.0) <= 0.2 and bd >= 1.5,
        f"sounding {pA:.2f}/{pB:.2f} Hz (friction-flattened "
        f"{1200 * np.log2(pA / fSa):+.1f}c/"
        f"{1200 * np.log2(pB / hz(57)):+.1f}c) -> predicted "
        f"|3fSa-2fPa| = {pred:.2f} Hz, measured {br:.2f} Hz "
        f"at {bd:.1f} dB depth")
_, _, bd_ji, _, _ = res["JI"]
check("the just fifth is still",
        bd_ji <= 0.4 * bd,
        f"beat depth {bd:.1f} dB tempered -> {bd_ji:.1f} dB "
        f"just (rate unreadable at that depth, and honestly "
        f"so: the claim is DEPTH)")

# ---- the piece: jor in double stops ----------------------------
LOOP_S = 9.6
L = int(LOOP_S * SR)
tt = np.arange(L) / SR
KN = [(0.0, 50), (1.4, 50), (2.2, 53), (4.6, 53), (5.2, 52),
        (6.4, 52), (7.2, 50), (9.6, 50)]
f0m = np.interp(tt, [t for t, _ in KN], [hz(m) for _, m in KN])
VBM = [(0.0, 0.085), (0.7, 0.105), (2.3, 0.12), (4.4, 0.105),
        (5.8, 0.115), (7.0, 0.10), (8.5, 0.085), (9.6, 0.085)]
vbm = np.interp(tt, [t for t, _ in VBM], [v for _, v in VBM])
mel = fdbow(f0m, LOOP_S, FB=np.where(tt < 8.5, 1e4 * vbm, 0.0),
        vb=vbm, sig0=4.0, raw=True)
vbd = np.interp(tt, [0.0, 0.7, 8.5, 9.6],
        [0.085, 0.095, 0.085, 0.085])
ped = fdbow(np.full(L, fSa), LOOP_S,
        FB=np.where(tt < 8.5, 1e4 * vbd, 0.0), vb=vbd,
        sig0=4.0, raw=True)

# own-bus: the melody string
HOLDS = (("Sa", 0.3, 1.3, 50), ("ga", 2.5, 4.4, 53),
        ("Re", 5.5, 6.2, 52), ("Sa'", 7.5, 8.4, 50))
locks = [ruler.lock_ratio(mel[int(a * SR):int(b * SR)], hz(m))
        for _, a, b, m in HOLDS]
fps = [fund_presence(mel[int(a * SR):int(b * SR)], hz(m))
        for _, a, b, m in HOLDS]
ts, fsc = ruler.pitch_contour(mel, fmin=80.0, fmax=500.0)
worst_hold = 0.0
for nm, a, b, m in HOLDS:
    sel = (ts >= a) & (ts <= b)
    med = float(np.median(fsc[sel]))
    worst_hold = max(worst_hold, abs(1200 * np.log2(med / hz(m))))
# presence gate 0.05: the slam failure it guards against reads
# 0.000-0.005 (e66); true locked tones read 0.09-0.19 across
# e66/e67 — 0.05 sits at the calibrated midpoint, and a bright
# high-vb hold (ga at vb 0.12) honestly dips to 0.09
check("the melody string sings its line",
        min(locks) >= 0.2 and min(fps) >= 0.05
        and worst_hold <= 25.0,
        f"lock >= {min(locks):.2f}, presence >= {min(fps):.2f}, "
        f"worst hold {worst_hold:.1f}c")
sel = (ts >= 0.3) & (ts <= 8.3)
dline = np.interp(ts, tt, f0m)
dev = 1200 * np.log2(fsc[sel] / dline[sel])
check("the line follows the written jor",
        float(np.median(np.abs(dev))) <= 15.0,
        f"median |dev| {float(np.median(np.abs(dev))):.1f}c")

# own-bus: the pedal string
tsp, fsp = ruler.pitch_contour(ped, fmin=80.0, fmax=500.0)
selp = (tsp >= 0.5) & (tsp <= 8.3)
pdev = np.abs(1200 * np.log2(fsp[selp] / fSa))
check("the pedal string holds Sa for the whole phrase",
        float(np.max(pdev)) <= 12.0
        and ruler.lock_ratio(ped[SR:int(8.3 * SR)], fSa) >= 0.2
        and fund_presence(ped[SR:int(8.3 * SR)], fSa) >= 0.1,
        f"worst pedal deviation {float(np.max(pdev)):.1f}c "
        f"over 7.8 s, locked and voiced")

# the dyad readback (e58 practice, both notes + refused control)
duet = mel / np.abs(mel).max() + ped / np.abs(ped).max() * 0.6
worst_dy, worst_ctl = 0.0, np.inf
for nm, a, b, m in (("ga+Sa", 2.5, 4.4, 53),
        ("Re+Sa", 5.5, 6.2, 52)):
    dp = ruler.dyad_pitches(duet[int(a * SR):int(b * SR)],
            fmin=130.0, fmax=360.0)
    for target in (hz(m), fSa):
        dv = min(abs(1200 * np.log2(f / target)) for f in dp)
        ct = min(abs(1200 * np.log2(f / target) + 50.0)
                for f in dp)
        worst_dy = max(worst_dy, dv)
        worst_ctl = min(worst_ctl, ct)
check("every two-note hold reads as its dyad",
        worst_dy <= 25.0 and worst_ctl >= 35.0,
        f"both notes found in ga+Sa and Re+Sa (worst "
        f"{worst_dy:.1f}c); the -50c shifted design refuses "
        f"at {worst_ctl:.1f}c")

bal_db = 20 * np.log10(rms(ped) * 0.6 / (rms(mel) + 1e-12))
check("the pedal sits under the line", -12.0 <= bal_db <= -2.0,
        f"pedal/melody {bal_db:.1f} dB")
t60r = ruler.decay_t60(duet[int(8.6 * SR):int(9.55 * SR)],
        100.0, 1200.0)
check("both strings lift into the seam",
        abs(t60r / 1.725 - 1) <= 0.35,
        f"release t60 {t60r:.2f} s (design 1.73)")

# ---- the mix ---------------------------------------------------
BANK = [50, 52, 53, 55, 57, 59, 60, 62]
_, tb = fdsym([hz(n) for n in BANK], duet, buses=True,
        jawari=True, gain=5000.0)
HALO_GAIN = 0.05
pans = np.linspace(-0.55, 0.55, len(BANK))
tnorm = np.abs(tb).max() + 1e-12
taraf_st = np.zeros((L, 2))
for b, p in zip(tb, pans):
    gg = (b[:L] / tnorm) * HALO_GAIN
    taraf_st[:, 0] += gg * np.cos((p + 1) * np.pi / 4)
    taraf_st[:, 1] += gg * np.sin((p + 1) * np.pi / 4)
duet_mix = duet * 0.85 / (np.abs(duet).max() + 1e-12) * 0.9
halo_db = 20 * np.log10(rms(taraf_st.sum(axis=1))
        / rms(duet_mix))
check("the halo sits under the duet", -32.0 <= halo_db <= -8.0,
        f"taraf/duet {halo_db:.1f} dB")

DRONE = [("pa", hz(45), 140, 0.0, -0.35, 0.55),
        ("sa+", hz(50.015), 112, 1.2, 0.15, 0.50),
        ("sa-", hz(49.985), 112, 2.4, -0.15, 0.50),
        ("SA", hz(38), 138, 3.6, 0.35, 0.75)]
loop = Loop(LOOP_S, seed=67)
for name, f0d, n, at, pan, ampd in DRONE:
    v = fdpluck2(f0d, 12.0, amp=ampd, N=n)
    loop.add(at, stereo(v, pan))
    loop.add(at + 4.8, stereo(v, pan))
loop.add(0.0, stereo(duet_mix, 0.0))
loop.add(0.0, taraf_st)
mix = loop.master(lp_hz=6500.0, drive=1.2)

check("seam", ruler.seam_rank(mix) <= 0.999,
        f"p{100 * ruler.seam_rank(mix):.2f}")
cu = ruler.chroma_uniform(mix.mean(axis=1))
order = np.argsort(cu)[::-1]
margin = cu[order[0]] / cu[order[1]]
check("Sa is the tonal center (pedal-anchored)",
        order[0] == 2 and margin >= 1.5,
        f"top class {order[0]} at {cu[order[0]]:.2f}, "
        f"x{margin:.2f} over runner-up — the pedal string "
        f"does what a pedal does")

out = np.concatenate([mix, mix])
wav = os.path.join(outdir, "e67_double_stop.wav")
write_wav(wav, out)
ruler.report(out, "double_stop")
subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", wav,
        "-q:a", "5", wav.replace(".wav", ".ogg")], check=True)

print("ALL RULERS PASS" if not fails else f"FAILED: {fails}")
sys.exit(1 if fails else 0)

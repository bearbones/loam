#!/usr/bin/env python3
"""e72 — written shimmer: composing the beat rate.

Refinement of e71: last session CLOSED the beat chain
(own-bus sounded lines predict the mix's beat to 0.03 Hz);
this session runs it BACKWARDS — the beat rate becomes
written musical material. Given the melody's measured h3 line
and the bass bow's measured flattening ratio rho (sounded
h4 / 4*command, flat to 0.36c across +-10c of command), the
bass command for any target rate r is one division:

    command = (f3_measured - r) / (4 * rho)

One-shot writing carries an ABSOLUTE error (the rho wobble,
0.03-0.16 Hz measured, pinned as a gate) — fine at 4 Hz,
up to 30% of a 0.5 Hz target. The piece
does better: fdbow is deterministic, so the score LISTENS
TWICE — render the bass, measure each segment's achieved
separation, correct the commands (+0.2c), render final.
Two-shot lands within 0.05 Hz of every written rate.

And the score listens to THE TAKE, not a reference: the
in-piece melody sounds ~0.2 Hz flatter at h3 than the same
recipe's standalone take (context: trajectory history moves
the line). A bass tuned to the reference would miss s1's
written 0.8 Hz by 25%. Tune to what THIS take sings.

The piece: "written shimmer" — the melody is ONE note. Sa,
held; the bass holds the fourth below and all the motion is
the beat rate, written to double twice: 0.8 -> 1.6 -> 3.2 Hz.
Then the melody steps away to ga (no line pair in the band —
the shimmer stops) and WHILE IT IS AWAY the bass silently
retunes to the melody's own sounded line; the melody returns
home to written stillness (separation 0.04 Hz, ripple 0.4 dB
where the beating segment reads 5.7). The drone's pa pluck is
REMOVED by design: its h4 = 440.0 Hz exactly, a third line in
the written band. Library: beat_profile short-window detrend
clamp (a trend_s longer than the window crashed the slice).

    python3 experiments/e72_written_shimmer.py [outdir]
"""

import os
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


def w(x, a, b):
    return x[int(a * SR):int(b * SR)]


def steady_f(f0, k, dur, vtop):
    tp = np.arange(int(dur * SR)) / SR
    vbp = np.interp(tp, [0.0, 0.6, dur], [0.085, vtop, vtop])
    return fdbow(f0, dur, FB=k * vbp, vb=vbp, sig0=4.0,
            raw=True)[SR:]


print("== part A: the writing tool ==")

rhos = []
for x in (-10, -5, 0, 5, 10):
    c = hz(45) * 2 ** (x / 1200)
    B = steady_f(c, 4e4, 5.0, 0.10)
    f4 = ruler.partial_freq(B, 4 * c * 0.99, 4 * c * 1.01)
    rhos.append(f4 / (4 * c))
spread = 1200 * np.log2(max(rhos) / min(rhos))
RHO = rhos[2]
check("the flattening ratio is flat",
        spread <= 0.6,
        f"rho = sounded h4 / 4*command across +-10c: "
        f"{1200 * np.log2(RHO):+.2f}c at center, spread "
        f"{spread:.2f}c — one number licenses one-shot "
        f"writing")

Aref = steady_f(hz(50), 1e4, 8.0, 0.105)
f3ref = ruler.partial_freq(Aref, 3 * hz(50) * 0.985,
        3 * hz(50) * 1.015)
An = Aref / np.abs(Aref).max()
ladder = {}
for r in (1.0, 2.0, 4.0, 0.5, 0.0):
    c = (f3ref - r) / (4 * RHO)
    B = steady_f(c, 4e4, 8.0, 0.10)
    mixd = An + B / np.abs(B).max()
    if r > 0:
        mr = max(0.1, r / 2)
        tr = max(1.5, 2.5 / max(r, 0.4))
        ladder[r] = ruler.beat_profile(mixd, 400.0, 480.0,
                trend_s=tr, min_rate=mr)
    else:
        f4 = ruler.partial_freq(B, 4 * c * 0.99, 4 * c * 1.01)
        still_sep = abs(f3ref - f4)
        still_depth = ruler.beat_profile(mixd, 400.0,
                480.0)[1]
check("one-shot writing works from 1 Hz up",
        all(abs(ladder[r][0] / r - 1) <= 0.25
            and ladder[r][1] >= 4.0 for r in (1.0, 2.0, 4.0)),
        f"write 1/2/4 Hz, read {ladder[1.0][0]:.2f}/"
        f"{ladder[2.0][0]:.2f}/{ladder[4.0][0]:.2f} Hz at "
        f"{ladder[1.0][1]:.1f}/{ladder[2.0][1]:.1f}/"
        f"{ladder[4.0][1]:.1f} dB — command is one division")
errs = {r: abs(ladder[r][0] - r) for r in ladder}
check("one-shot error is absolute, not relative",
        max(errs.values()) <= 0.25
        and max(errs.values()) >= 0.05,
        f"|read - written| = "
        f"{errs[0.5]:.2f}/{errs[1.0]:.2f}/{errs[2.0]:.2f}/"
        f"{errs[4.0]:.2f} Hz across the 0.5-4 Hz ladder — the "
        f"rho wobble sets a fixed ~0.1 Hz band, so a 4 Hz "
        f"write lands at 1-4% and a 0.5 Hz write can miss by "
        f"30%. Slow shimmer needs the two-shot score")
check("written stillness, one shot",
        still_sep <= 0.15 and still_depth <= 1.5,
        f"write 0 Hz: lines land {still_sep:.2f} Hz apart, "
        f"default-window depth {still_depth:.1f} dB (the "
        f"default window is properly blind below 0.25 Hz — "
        f"its blindness is the right ruler for 'no audible "
        f"beat')")

print("== part B: the piece ==")

LOOP_S = 9.6
L = int(LOOP_S * SR)
tt = np.arange(L) / SR
KN_M = [(0.0, 50), (6.7, 50), (6.9, 52), (6.95, 53),
        (7.45, 53), (7.5, 52), (7.7, 50), (9.6, 50)]
f0m = np.interp(tt, [t for t, _ in KN_M],
        [hz(m) for _, m in KN_M])
vbm = np.interp(tt, [0.0, 0.6, 8.5, 9.6],
        [0.085, 0.105, 0.105, 0.085])
mel = fdbow(f0m, LOOP_S, FB=np.where(tt >= 8.5, 0.0,
        1e4 * vbm), vb=vbm, sig0=4.0, raw=True)

SEGS = [("s1", 0.7, 3.3, 0.8), ("s2", 3.5, 5.4, 1.6),
        ("s3", 5.6, 6.6, 3.2), ("s4", 7.7, 8.45, 0.0)]
f3 = {nm: ruler.partial_freq(w(mel, a, b),
        3 * hz(50) * 0.985, 3 * hz(50) * 1.015)
        for nm, a, b, r in SEGS}
ctx = f3ref - np.array(list(f3.values()))
check("the score listens to the take, not the reference",
        float(ctx.min()) >= 0.12
        and float(max(f3.values()) - min(f3.values())) <= 0.1,
        f"in-piece h3 sits {ctx.min():.2f}-{ctx.max():.2f} Hz "
        f"below the standalone reference (segments agree "
        f"within {max(f3.values()) - min(f3.values()):.2f} Hz)"
        f" — a bass tuned to the reference would miss s1's "
        f"written 0.8 Hz by ~25%. Context moves the line; "
        f"tune to what THIS take sings")


def bass_take(cs):
    KT = [(0.0, cs["s1"]), (3.35, cs["s1"]), (3.45, cs["s2"]),
            (5.45, cs["s2"]), (5.55, cs["s3"]),
            (6.8, cs["s3"]), (7.0, cs["s4"]), (9.6, cs["s4"])]
    f0b = np.interp(tt, [t for t, _ in KT],
            [c for _, c in KT])
    vbb = np.interp(tt, [0.0, 0.6, 8.5, 9.6],
            [0.085, 0.10, 0.10, 0.085])
    return fdbow(f0b, LOOP_S, FB=np.where(tt >= 8.5, 0.0,
            4e4 * vbb), vb=vbb, sig0=4.0, raw=True)


cs = {nm: (f3[nm] - r) / (4 * RHO) for nm, a, b, r in SEGS}
b1 = bass_take(cs)
for nm, a, b, r in SEGS:
    f4 = ruler.partial_freq(w(b1, a, b), 4 * cs[nm] * 0.99,
            4 * cs[nm] * 1.01)
    cs[nm] += ((f3[nm] - f4) - r) / (4 * RHO)
bas = bass_take(cs)

seps = {}
for nm, a, b, r in SEGS:
    f4 = ruler.partial_freq(w(bas, a, b), 4 * cs[nm] * 0.99,
            4 * cs[nm] * 1.01)
    seps[nm] = f3[nm] - f4
check("the two-shot score lands every rate",
        all(abs(seps[nm] - r) <= 0.08 for nm, a, b, r in SEGS),
        f"written 0.8/1.6/3.2/0, lines land at "
        f"{seps['s1']:.2f}/{seps['s2']:.2f}/{seps['s3']:.2f}/"
        f"{seps['s4']:.2f} Hz — measure, correct ~0.2c, "
        f"render: within 0.05 Hz of the score")

meln = mel / np.abs(mel).max()
basn = bas / np.abs(bas).max()
sub = meln + basn
rates = {}
for nm, a, b, r in SEGS[:3]:
    per = 1.0 / r
    trm = min(0.8 * (b - a), 2.5 * per)
    rates[nm] = ruler.beat_profile(w(sub, a, b), 400.0, 480.0,
            trend_s=trm, min_rate=0.6 * r)
check("the shimmer reads as written",
        all(abs(rates[nm][0] / r - 1) <= 0.25
            and rates[nm][1] >= 4.0 for nm, a, b, r in SEGS[:3]),
        f"segments read {rates['s1'][0]:.2f}/"
        f"{rates['s2'][0]:.2f}/{rates['s3'][0]:.2f} Hz at "
        f"{rates['s1'][1]:.1f}/{rates['s2'][1]:.1f}/"
        f"{rates['s3'][1]:.1f} dB against written 0.8/1.6/3.2")
check("the shimmer doubles twice",
        1.7 <= rates["s2"][0] / rates["s1"][0] <= 2.3
        and 1.7 <= rates["s3"][0] / rates["s2"][0] <= 2.3,
        f"ratios {rates['s2'][0] / rates['s1'][0]:.2f} and "
        f"{rates['s3'][0] / rates['s2'][0]:.2f} — a written "
        f"accelerando of pure beat")

rip = {}
for nm, a, b in (("s3", 5.6, 6.6), ("away", 6.95, 7.45),
        ("s4", 7.7, 8.45)):
    rip[nm] = ruler.beat_profile(w(sub, a, b), 400.0, 480.0,
            trend_s=0.5, min_rate=0.5)[1]
check("away kills it, home is retuned still",
        rip["s3"] >= 4.0 and rip["away"] <= 1.0
        and rip["s4"] <= 1.0,
        f"band ripple (same short-trend ruler): beating s3 "
        f"{rip['s3']:.1f} dB, melody-away {rip['away']:.1f}, "
        f"returned-home {rip['s4']:.1f} — the bass retuned "
        f"WHILE no partner sounded, and home came back still")

fps = [ruler.fund_presence(w(basn, a, b), cs[nm])
        for nm, a, b, r in SEGS]
check("the bass stays dark",
        min(fps) >= 0.6,
        f"fund_presence {min(fps):.2f}-{max(fps):.2f} across "
        f"all segments")
t60m = ruler.decay_t60(meln[int(8.6 * SR):int(9.55 * SR)],
        100.0, 1200.0)
t60b = ruler.decay_t60(basn[int(8.6 * SR):int(9.55 * SR)],
        100.0, 1200.0)
check("both voices obey the release law",
        abs(t60m / 1.725 - 1) <= 0.3
        and abs(t60b / 1.725 - 1) <= 0.3,
        f"release t60 mel {t60m:.2f} / bass {t60b:.2f} s "
        f"(design 1.73)")

# ---- the mix ---------------------------------------------------
BANK = [50, 52, 53, 55, 57, 59, 60, 62]
sar = meln * 0.55 + basn * 0.50
_, tb = fdsym([hz(n) for n in BANK],
        sar / np.abs(sar).max(), buses=True, jawari=True,
        gain=5000.0)
HALO_GAIN = 0.05
pans = np.linspace(-0.55, 0.55, len(BANK))
tnorm = np.abs(tb).max() + 1e-12
taraf_st = np.zeros((L, 2))
for b_, p in zip(tb, pans):
    gg = (b_[:L] / tnorm) * HALO_GAIN
    taraf_st[:, 0] += gg * np.cos((p + 1) * np.pi / 4)
    taraf_st[:, 1] += gg * np.sin((p + 1) * np.pi / 4)
norm = np.abs(sar).max() + 1e-12
sar_mix = sar * 0.85 / norm * 0.9
halo_db = 20 * np.log10(rms(taraf_st.sum(axis=1))
        / rms(sar_mix))
check("the halo sits under the voices",
        -32.0 <= halo_db <= -8.0,
        f"taraf/voices {halo_db:.1f} dB")

# drone WITHOUT the pa pluck: its h4 = 440.0 Hz exactly — a
# third line inside the written band. The bass voice IS the
# piece's pa.
DRONE = [("sa+", hz(50.015), 112, 1.2, 0.15, 0.50),
        ("sa-", hz(49.985), 112, 2.4, -0.15, 0.50),
        ("SA", hz(38), 138, 3.6, 0.35, 0.75)]
loop = Loop(LOOP_S, seed=72)
for name, f0d, n, at, pan, ampd in DRONE:
    v = fdpluck2(f0d, 12.0, amp=ampd, N=n)
    loop.add(at, stereo(v, pan))
    loop.add(at + 4.8, stereo(v, pan))
loop.add(0.0, stereo(meln * 0.55 * 0.85 / norm * 0.9, 0.2))
loop.add(0.0, stereo(basn * 0.50 * 0.85 / norm * 0.9, -0.2))
loop.add(0.0, taraf_st)
mix = loop.master(lp_hz=6500.0, drive=1.2)
mono = mix.mean(axis=1)

mrates = {}
for nm, a, b, r in SEGS[:3]:
    per = 1.0 / r
    trm = min(0.8 * (b - a), 2.5 * per)
    mrates[nm] = ruler.beat_profile(w(mono, a, b), 400.0,
            480.0, trend_s=trm, min_rate=0.6 * r)
mstill = {nm: ruler.beat_profile(w(mono, a, b), 400.0, 480.0,
        trend_s=0.5, min_rate=0.5)[1]
        for nm, a, b in (("away", 6.95, 7.45),
            ("s4", 7.7, 8.45))}
check("the listener hears the written shimmer",
        all(abs(mrates[nm][0] / r - 1) <= 0.25
            for nm, a, b, r in SEGS[:3])
        and mstill["away"] <= 1.5 and mstill["s4"] <= 1.5,
        f"mastered mix reads {mrates['s1'][0]:.2f}/"
        f"{mrates['s2'][0]:.2f}/{mrates['s3'][0]:.2f} Hz, "
        f"away/home ripple {mstill['away']:.1f}/"
        f"{mstill['s4']:.1f} dB — the accelerando survives "
        f"the drone, halo, and master chain")

check("seam", ruler.seam_rank(mix) <= 0.999,
        f"p{100 * ruler.seam_rank(mix):.2f}")

cu = ruler.chroma_uniform(mono)
order = np.argsort(cu)[::-1].tolist()
check("one note and its fourth",
        order[:2] == [2, 9] and cu[2] >= 1.8 * cu[9]
        and cu[9] >= 2.5 * cu[order[2]],
        f"Sa {cu[2]:.2f}, Pa- {cu[9]:.2f}, everything else "
        f"<= {cu[order[2]]:.2f} — the piece's whole pitch "
        f"story is two classes; the music was the beat rate")

out = np.concatenate([mix, mix])
wav = os.path.join(outdir, "e72_written_shimmer.wav")
write_wav(wav, out)
ruler.report(out, "written_shimmer")

if fails:
    print("FAILED RULERS:", fails)
    sys.exit(1)
print("ALL RULERS PASS")

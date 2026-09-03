#!/usr/bin/env python3
"""e78 — the prominence floor: at what depth does a clock die?

Refinement cycle. The Avartan showcase forced a ruler change:
crown ratios (line over window max) fail wherever a carpet
voice owns the flux spectrum — the tanpura's strike comb
crowned every quiet section, while a real 2.08 Hz jor tick sat
6x above the spectrum MEDIAN. That measure — prominence — is
now loam.ruler.flux_line. This experiment calibrates it: ONE
variable, the written depth of a 3.333 Hz tabla tick that
sinks into a constant tanpura carpet and returns,

    level(t) = -18 + 12 cos(2 pi t / 19.2)  dB re the loudest

(-6 dB at the seam, -30 dB mid-loop). Windowed flux_line then
maps measured prominence against written depth: where the map
is monotone the ruler is honest; where prominence flattens
into the carpet's floor is the depth below which NO flux ruler
can testify — the number Avartan's jor (6x) and jhala (5x)
gates now stand on.

    python3 experiments/e78_prominence_floor.py [outdir]
"""

import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))))
from loam import SR, hz, Loop, stereo, write_wav
from loam import ruler
from loam.fdstring import fdpluck2
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


LOOP_S = 19.2
L = int(LOOP_S * SR)
RATE = 1 / 0.3                    # 3.333 ticks/s
NTICK = 64


def add_wrap(buf, at, v):
    idx = (int(at * SR) + np.arange(len(v))) % len(buf)
    np.add.at(buf, idx, v)


def level_db(t):
    return -18.0 + 12.0 * np.cos(2 * np.pi * t / LOOP_S)


# ---- the tick that sinks ---------------------------------------
print("== voices ==")
na = fddrum(283.8, 1.5, strike=(0.55, 0.0), load=40.0, rs=0.45,
        sig_s=60.0)
tick = np.zeros(L)
for k in range(NTICK):
    t = k * 0.3
    add_wrap(tick, t, na * 10 ** (level_db(t) / 20.0))

# the carpet must be FLUX-STATIONARY: the first cut used
# avartan's 4-strikes-then-6s-silence cycle, and windows with
# no strike had collapsed medians — the same written tick depth
# read 2.4x in a strike-rich window and 31x in a strike-free
# one. A real tanpura cycles endlessly: 16 strikes, one every
# 1.2 s, same floor in every window. Its strike comb's 4th
# harmonic (4 x 0.833 = 3.333 Hz) then sits EXACTLY on the tick
# rate — so the carpet's own line is measured as a per-window
# control bus, not assumed away.
DRONE = [("pa", hz(45), 140, -0.35, 0.55),
        ("sa+", hz(50.015), 112, 0.15, 0.50),
        ("sa-", hz(49.985), 112, -0.15, 0.50),
        ("SA", hz(38), 138, 0.35, 0.75)]
carpet = np.zeros((L, 2))
for k in range(16):
    name, f0d, n, pan, ampd = DRONE[k % 4]
    v = fdpluck2(f0d, 12.0, amp=ampd, N=n)
    add_wrap(carpet, k * 1.2, stereo(v, pan))

loop = Loop(LOOP_S, seed=0x78)
loop.add(0.0, carpet * 0.85)
loop.add(0.0, stereo(tick / (np.abs(na).max() + 1e-12) * 0.55,
        0.2))
mix = loop.master(6500.0, drive=1.2)
mono = mix.mean(axis=1)

# ---- windowed prominence vs written depth ----------------------
print("== the map ==")
dbl = np.concatenate([mono, mono])
HALF = 2.4
centers = np.arange(0.0, LOOP_S, 0.8)
lv, pr, fq = [], [], []
for c in centers:
    a = int((c - HALF + LOOP_S) * SR)
    seg = dbl[a:a + int(2 * HALF * SR)]
    f, p = ruler.flux_line(seg, 3.0, 3.7)
    tt = np.linspace(c - HALF, c + HALF, 97)
    lw = float(10 * np.log10(np.mean(10 ** (level_db(tt)
            / 10.0))))
    lv.append(lw)
    pr.append(p)
    fq.append(f)
lv, pr, fq = np.array(lv), np.array(pr), np.array(fq)
for c, l_, p, f in zip(centers, lv, pr, fq):
    print(f"    t={c:5.1f}  written {l_:6.1f} dB  "
          f"prom {p:5.1f}  line {f:.2f} Hz")

# ================= the rulers ===================================
print("== rulers ==")
check("seam", ruler.seam_rank(mix) <= 0.999,
        f"p{100 * ruler.seam_rank(mix):.2f}")

r = float(np.corrcoef(lv, np.log(pr))[0, 1])
check("prominence is monotone in depth", r >= 0.85,
        f"corr(written dB, log prominence) = {r:.3f} across "
        f"{len(centers)} windows — the ruler moves with the "
        f"one variable (ramp-holding windows depress it; see "
        f"the shoulder report below)")

loud = lv >= -11.0
quiet = lv <= -26.0
check("a loud clock stands", float(pr[loud].min()) >= 4.0,
        f"windows written >= -11 dB read prominence "
        f"{pr[loud].min():.1f}..{pr[loud].max():.1f}")
check("a sunken clock is gone", float(pr[quiet].max()) <= 3.0,
        f"windows written <= -26 dB read prominence "
        f"{pr[quiet].min():.1f}..{pr[quiet].max():.1f} — "
        f"indistinguishable from the carpet")
check("loud and sunken do not overlap",
        float(pr[loud].min()) >= 1.5 * float(pr[quiet].max()),
        f"weakest loud window ({pr[loud].min():.1f}) stands "
        f"x{pr[loud].min() / pr[quiet].max():.2f} over the "
        f"strongest sunken one ({pr[quiet].max():.1f})")
meas = pr >= 6.0
check("where it stands, it tells the truth",
        bool(np.all(np.abs(fq[meas] / RATE - 1) <= 0.02)),
        f"all {int(meas.sum())} windows with prominence >= 6 "
        f"read the line within 2% of the written 3.333 Hz")

# reported, not gated: a window holding a steep level ramp
# smears the line (e77's stationarity lesson, in AMPLITUDE) —
# and asymmetrically: the two shoulder windows straddling the
# seam-side crest read 5.9/4.6 (one drifting a bin low) while
# their mirror images read 7.7/8.4. Mechanism not yet earned:
# open thread.
slope = level_db((centers + HALF) % LOOP_S) \
    - level_db((centers - HALF) % LOOP_S)
for c, l_, s_, p in zip(centers, lv, slope, pr):
    if l_ >= -11.0:
        print(f"    shoulder report: t={c:5.1f} written "
              f"{l_:5.1f} dB slope {s_:+5.1f} dB/win "
              f"prom {p:5.1f}")

# the floor itself: reported, not gated — interpolate the depth
# where prominence crosses 2x (the carpet's own median scatter)
order = np.argsort(lv)
floor_db = float(np.interp(np.log(2.0), np.log(pr[order]),
        lv[order]))
print(f"  the floor: prominence crosses 2.0x at "
      f"{floor_db:.1f} dB written depth — below this, in this "
      f"carpet, no flux ruler can testify")

wav = os.path.join(outdir, "e78_prominence_floor.wav")
write_wav(wav, mix)
ruler.report(mix, "e78")

if fails:
    print("FAILED RULERS:", fails)
    sys.exit(1)
print("ALL RULERS PASS")

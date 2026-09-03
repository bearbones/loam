#!/usr/bin/env python3
"""loam — "Nine Landings". Equal in phase, unequal on the clock.

A chakradar — the tihai of tihais — over a breathing grid.
The mukhda (ma-ga-Sa, landing on Sa) is stated nine times:
three statements make a tihai, three tihais make the
chakradar, and the ninth landing IS the sam. The statements
are laid out in STROKES — phase-equal lags of 7 slots inside
each tihai, 24 between tihais, the arithmetic closing at slot
320 = 0 exactly — but the grid underneath breathes (e77):

    rate(t) = 8.333 - 2.2 cos(2 pi 2t / 38.4)  strokes/s

two breath cycles per loop, so the chakradar enters near 10
strokes/s and DECELERATES into the sam at 6.1. Nine landings
equally spaced in phase, visibly stretching on the clock as
the arrival nears — a countdown that slows down and still
lands, by arithmetic, on zero. Tabla marks each landing (dha)
and takes the sam with the pressed bayan; tanpura breathes
underneath; the jhala strum never stops.

38.4 s seamless loop. Lands the chakradar open thread (e76).

    python3 songs/landings.py [outdir]
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


LOOP_S = 38.4
L = int(LOOP_S * SR)
NST = 320
NB = 2                            # breath cycles per loop
RMEAN = NST / LOOP_S              # 8.333 strokes/s
RDEP = 2.2                        # 6.13 .. 10.53 strokes/s
RLO, RHI = RMEAN - RDEP, RMEAN + RDEP


def add_wrap(buf, at, v):
    idx = (int(at * SR) + np.arange(len(v))) % len(buf)
    np.add.at(buf, idx, v)


# ---- the breathing grid ----------------------------------------
print("== the grid ==")
tg = np.linspace(0.0, LOOP_S, 400001)
phase = RMEAN * tg - RDEP * (LOOP_S / (2 * np.pi * NB)) \
    * np.sin(2 * np.pi * NB * tg / LOOP_S)
check("320 strokes by arithmetic",
        abs(phase[-1] - NST) <= 1e-9,
        f"phase integral over one loop = {phase[-1]:.9f} — the "
        f"mean rate closes the breathing grid exactly")
tk = np.interp(np.arange(NST), phase, tg)


def written_rate(t):
    return RMEAN - RDEP * np.cos(2 * np.pi * NB * t / LOOP_S)


# ---- the chakradar arithmetic ----------------------------------
# statement: ma ga Sa at slot offsets 0 2 4, landing on the Sa.
# intra-tihai lag 7 slots, inter-tihai lag 24; ninth landing at
# slot 320 = 0 = sam:  254 + 2*24 + 2*7 + 4 = 320.
A_LAG, B_LAG, LANDOFF = 7, 24, 4
S0 = NST - LANDOFF - 2 * A_LAG - 2 * B_LAG
STARTS = [S0 + i * B_LAG + j * A_LAG
        for i in range(3) for j in range(3)]
LANDINGS = [s + LANDOFF for s in STARTS]
assert STARTS[0] == 254 and LANDINGS[-1] == NST
MUKHDA = [(0, 55), (2, 53), (4, 50)]

# ---- jhala + line + mukhda -------------------------------------
print("== strings ==")
LINE = [50, 52, 53, 55, 53, 52, 50, 48, 47, 48, 50, 52,
        53, 52, 50, 48, 50, 52, 50, 50]
cache = {}


def mpluck(m):
    if m not in cache:
        cache[m] = fdpluck2(hz(m), 1.2, amp=1.0, pick=0.28)
    return cache[m]


CH_DA = fdpluck2(hz(62) * 2 ** (0.8 / 1200), 0.9, amp=0.38,
        pick=0.24)
CH_RA = fdpluck2(hz(62) * 2 ** (-3.2 / 1200), 0.9, amp=0.33,
        pick=0.33)

mel = np.zeros(L)
chik = np.zeros(L)
for j in range(NST):
    if j % 4 == 0 and j < S0:
        add_wrap(mel, tk[j], mpluck(LINE[(j // 4) % 20]))
    else:
        add_wrap(chik, tk[j], CH_DA if j % 2 else CH_RA)
for i, s in enumerate(STARTS):
    amp = (1.0, 1.1, 1.2)[i // 3]
    for off, m in MUKHDA:
        sl = s + off
        at = 0.0 if sl >= NST else tk[sl]
        add_wrap(mel, at, mpluck(m) * amp)
add_wrap(mel, 0.0, mpluck(50) * 0.6)      # the ninth Sa, pressed

meln = mel / np.abs(mel).max()
chikn = chik / np.abs(chik).max()
sar = 0.55 * meln + 0.35 * chikn          # design bus (e77)

# ---- tabla: a dha for each landing, the bayan for the sam ------
print("== drums ==")
LOAD, RS = 40.0, 0.45
na = fddrum(283.8, 1.5, strike=(0.55, 0.0), load=LOAD, rs=RS,
        sig_s=60.0)
ge = fddrum(105.6, 1.0, strike=(0.30, 0.0), load=LOAD, rs=RS,
        sig0=9.0, sig_s=20.0)
ge_sam = fddrum(141.2, 1.0, strike=(0.30, 0.0), load=LOAD,
        rs=RS, sig0=9.0, sig_s=20.0)
def dha(treb, tg_, bass, bg):
    v = treb * tg_
    v[:len(bass)] += bass * bg
    return v


drum = np.zeros(L)
for i, sl in enumerate(LANDINGS[:-1]):
    add_wrap(drum, tk[sl], dha(na, 0.9, ge, 0.85))
add_wrap(drum, 0.0, dha(na, 1.15, ge_sam, 1.0))

# ---- tanpura ---------------------------------------------------
print("== tanpura ==")
DRONE = [("pa", hz(45), 140, 0.0, -0.35, 0.55),
        ("sa+", hz(50.015), 112, 1.2, 0.15, 0.50),
        ("sa-", hz(49.985), 112, 2.4, -0.15, 0.50),
        ("SA", hz(38), 138, 3.6, 0.35, 0.75)]
drone_st = np.zeros((L, 2))
for name, f0d, n, at, pan, ampd in DRONE:
    v = fdpluck2(f0d, 12.0, amp=ampd, N=n)
    sv = stereo(v, pan)
    for cyc in range(4):
        idx = (int((at + 9.6 * cyc) * SR)
                + np.arange(len(sv))) % L
        np.add.at(drone_st, idx, sv)

# ---- mix -------------------------------------------------------
print("== mix ==")
loop = Loop(LOOP_S, seed=0x91A)
loop.add(0.0, drone_st * 0.85)
loop.add(0.0, stereo(meln * 0.60, 0.1))
loop.add(0.0, stereo(chikn * 0.30, -0.45))
loop.add(0.0, stereo(drum / (np.abs(drum).max() + 1e-12)
        * 0.55, 0.35))
mix = loop.master(6500.0, drive=1.2)
mono = mix.mean(axis=1)

# ================= the rulers ===================================
print("== rulers ==")
check("seam", ruler.seam_rank(mix) <= 0.999,
        f"p{100 * ruler.seam_rank(mix):.2f}")


def contour(x):
    xx = np.concatenate([x, x[:int(2.5 * SR)]])
    t_, r_ = ruler.rate_contour(xx, 4.5, 12.5)
    keep = (t_ >= t_[0]) & (t_ < t_[0] + LOOP_S)
    return t_[keep], r_[keep]


ct, cr = contour(sar)
wr = written_rate(ct % LOOP_S)
dev = np.abs(cr / wr - 1)
# e77: a 2-stroke da/ra hand pattern OWNS its subharmonic and
# octave — fold {1, 2, 1/2} before judging the worst window
folds = np.stack([np.abs(cr * m / wr - 1)
        for m in (1.0, 2.0, 0.5)])
mbest = np.array((1.0, 2.0, 0.5))[np.argmin(folds, axis=0)]
fdev = folds.min(axis=0)
# a window holding a mukhda statement does not read the grid:
# the statement's 2-slot melody spacing owns rate/2, BELOW the
# band, and the estimator pins at the band edge (measured: one
# window at 4.50 = the floor, 0.2 slots from a landing). Those
# windows' content is claimed by the phase-lag ruler instead.
land_t = np.array([tk[sl] for sl in LANDINGS[:-1]] + [0.0])
dist = np.min(np.abs(((ct % LOOP_S)[:, None] - land_t
        + LOOP_S / 2) % LOOP_S - LOOP_S / 2), axis=1)
clear = dist > 0.55
check("the strum tracks the written breath",
        float(np.median(dev)) <= 0.03
        and fdev[clear].max() <= 0.08
        and float(np.mean(dev <= 0.08)) >= 0.9,
        f"rate_contour follows rate(t) at median "
        f"{100 * np.median(dev):.1f}%, worst "
        f"{100 * fdev[clear].max():.1f}% in the "
        f"{int(clear.sum())} statement-clear windows "
        f"({100 * np.mean(dev <= 0.08):.0f}% of all {len(ct)} "
        f"read the rate raw) — two breath cycles")
integral = float(np.mean(cr * mbest) * LOOP_S)
check("the contour counts 320", abs(integral - NST) <= 5.0,
        f"integral of the folded contour = {integral:.1f} "
        f"strokes vs 320 written")

# the nine landings, read from the tabla bus
dbl = np.concatenate([drum, drum[:4 * SR]])
# the sam strike is read at t=0.01; its copy at the doubled-
# signal boundary shows one detector hop EARLY (38.39), so the
# last 50 ms — where nothing is written — is the wrap image
ons = np.array([t for t in ruler.onset_times(dbl, min_sep=0.3)
        if t < LOOP_S - 0.05])
lt_written = [tk[sl] for sl in LANDINGS[:-1]] + [LOOP_S]
# measured onsets: sam lives at t=0; shift it to the loop end
ons_s = np.sort(np.where(ons < 1.0, ons + LOOP_S, ons))
check("nine landings", len(ons) == 9,
        f"{len(ons)} tabla strikes per loop")
ph_meas = np.interp(ons_s % LOOP_S, tg, phase) \
    + np.where(ons_s >= LOOP_S, NST, 0)
ph_err = np.abs(ph_meas - np.array(LANDINGS))
check("equal in phase",
        len(ons) == 9 and float(ph_err.max()) <= 0.3,
        f"measured landing phases sit at written slots "
        f"254+{{4,11,18,28,35,42,52,59,66}} within "
        f"{ph_err.max():.2f} slots — lags 7/7/24 exactly, in "
        f"strokes")
gaps = np.diff(ons_s)
g_first, g_last = float(gaps[0]), float(gaps[-1])
check("unequal on the clock",
        len(gaps) == 8 and g_last / g_first >= 1.25,
        f"first intra-tihai gap {g_first:.2f} s, last "
        f"{g_last:.2f} s — x{g_last / g_first:.2f} stretch: the "
        f"grid decelerates into the sam")
check("the ninth landing is the sam",
        len(ons) >= 1 and float(min(ons)) <= 0.04,
        f"pressed-bayan dha at t={min(ons) * 1000:.0f} ms — "
        f"254 + 2x24 + 2x7 + 4 = 320 = 0, by arithmetic")

errs = []
for i in range(0, 60, 5):
    t = tk[4 * i]
    m = LINE[i % 20]
    idx = np.arange(int((t + 0.02) * SR),
            int((t + 0.42) * SR)) % L
    f = ruler.partial_freq(meln[idx], hz(m) * 0.96,
            hz(m) * 1.04)
    errs.append(abs(1200 * np.log2(f / hz(m))))
check("the line rides the breath",
        float(np.median(errs)) <= 5.0 and max(errs) <= 10.0,
        f"12 melody fundamentals at their breathing times: "
        f"median {np.median(errs):.1f}c, worst {max(errs):.1f}c")

dr_db = 20 * np.log10(rms(drum / np.abs(drum).max() * 0.55)
        / rms(mono) + 1e-12)
check("the tabla marks, it does not rule",
        -26.0 <= dr_db <= -6.0,
        f"landing strikes sit {dr_db:.1f} dB under the mix")

cu = ruler.chroma_uniform(mono)
check("Sa crowns the cycle", int(np.argmax(cu)) == 2,
        f"chroma crowns class 2 at {cu[2]:.2f}")

wav = os.path.join(outdir, "landings.wav")
write_wav(wav, mix)
ruler.report(mix, "landings")

if fails:
    print("FAILED RULERS:", fails)
    sys.exit(1)
print("ALL RULERS PASS")

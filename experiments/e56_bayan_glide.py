#!/usr/bin/env python3
"""e56 — bayan glide: meend comes to the drum.

Refinement cycle on e55's membrane: the bayan's signature
gesture, palm pressure bending the pitch mid-ring. In the
lattice this is fdpluck's meend trick transplanted — pitch
lives in one coefficient (lam2 per step), so time-varying
tension is one multiply, and because every mode frequency
scales with f1 on a fixed grid, THE WHOLE STACK BENDS AS ONE
VOICE (measured: fund/f1 ratio identical at two static
tunings).

New ruler: partial_track — one spectral peak followed through
time. pitch_contour's HPS is the wrong tool for a drum (sparse
stack, low fundamental); the gliding mode itself is loud and
alone in its band, so track THAT.

Checks: (1) scaling law — static fund/f1 ratio invariant
across tunings; (2) design-vs-measured glide — the tracked
fundamental follows the designed trajectory within tolerance
through the ramp; (3) the glide lands on Sa (D2) within 25
cents; (4) static control — an unbent drum tracks flat while
the glide spans a fourth (~500 cents); (5) the piece: teental,
straight first avartan, and in the second the bayan drops out
after khali for ONE long stroke that glides A1 -> D2 into sam
(the wrap point) — glide read back on the piece's own ge bus,
across the loop seam; slots, pulse, khali hole, seam, poles.

    python3 experiments/e56_bayan_glide.py [outdir]
"""

import os
import subprocess
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


LOAD, RS = 40.0, 0.45
F1A = 105.6                    # rest tuning: fundamental ~ A1
F1D = 141.2                    # pressed tuning: fundamental ~ D2


def bayan(f1, dur, amp=1.0):
    return fddrum(f1, dur, amp=amp, strike=(0.30, 0.0),
            load=LOAD, rs=RS, sig0=9.0, sig_s=20.0)


# ---- 1. the whole stack bends as one (scaling law) -------------
ra = {}
for f1 in (F1A, F1D):
    d = bayan(f1, 0.8)
    mf = ruler.mode_freqs(d, k=6, fmin=0.35 * f1, fmax=250.0,
            rel=1e-3, merge=0.06)
    ra[f1] = mf[0] / f1
check("the whole stack bends as one",
        abs(ra[F1D] / ra[F1A] - 1.0) <= 0.005,
        f"fund/f1 = {ra[F1A]:.4f} at rest, {ra[F1D]:.4f} "
        f"pressed — one scaling law, {abs(ra[F1D] / ra[F1A] - 1)
        * 100:.2f}% apart")

# ---- 2/3. the glide follows design and lands on Sa -------------
tt = np.linspace(0, 1, 200)
T0, T1 = 0.14, 0.64            # hold, ramp, hold (of dur 0.7)
f1t = np.where(tt < T0, F1A, np.where(tt > T1, F1D,
        F1A + (F1D - F1A) * (tt - T0) / (T1 - T0)))
g = bayan(f1t, 0.7)
ts, fs = ruler.partial_track(g, 45.0, 80.0)
design = np.interp(ts / 0.7, tt, f1t) * ra[F1A]
sel = (ts >= 0.12) & (ts <= 0.60)
dev = 1200 * np.log2(fs[sel] / design[sel])
check("the glide follows the designed trajectory",
        float(np.median(np.abs(dev))) <= 20.0,
        f"median |dev| {float(np.median(np.abs(dev))):.1f} "
        f"cents across the ramp (worst "
        f"{float(np.max(np.abs(dev))):.1f})")
land = float(np.median(fs[ts >= 0.62]))
cents = 1200 * np.log2(land / hz(38))
check("the glide lands on Sa", abs(cents) <= 25.0,
        f"final fundamental {land:.1f} Hz = {cents:+.0f} cents "
        f"from D2 — a perfect fourth up from A1, "
        f"{1200 * np.log2(land / (F1A * ra[F1A])):.0f} cents "
        f"traveled")

# ---- 4. the control does not move ------------------------------
# median, the same statistic as check 2: the staircase-split
# degenerate pair (~0.5 Hz apart) BEATS early in the ring and
# the apparent peak wobbles +/-30 cents at beat rate — real
# interference, not tracker noise; the median rides through it
s = bayan(F1A, 0.7)
_, fs0 = ruler.partial_track(s, 45.0, 80.0)
flat = 1200 * np.abs(np.log2(fs0 / np.nanmedian(fs0)))
check("an unbent drum tracks flat",
        float(np.nanmedian(flat)) <= 20.0,
        f"static drum median dev {float(np.nanmedian(flat)):.1f} "
        f"cents (max {float(np.nanmax(flat)):.1f} at the split-"
        f"pair beat) vs the glide's 503 — the tracker says no")

# ---- 5. the piece: the bayan bends into sam --------------------
SUB = 0.3
NB = 16
LOOP_S = 2 * NB * SUB
na = fddrum(283.8, 1.5, strike=(0.55, 0.0), load=LOAD, rs=RS,
        sig_s=60.0)
ge = bayan(F1A, 1.0)
ge_sam = bayan(F1D, 1.0)       # sam arrives PRESSED: Sa itself
tt2 = np.linspace(0, 1, 200)
G_DUR = 0.9                    # one long stroke spanning 3 slots
f1g = np.where(tt2 < 0.10, F1A, np.where(tt2 > 0.85, F1D,
        F1A + (F1D - F1A) * (tt2 - 0.10) / 0.75))
ge_glide = bayan(f1g, G_DUR)

THEKA = [(1.0, 0.9), (1.0, 0.55), (1.0, 0.55), (1.0, 0.9),
        (1.0, 0.9), (1.0, 0.55), (1.0, 0.55), (1.0, 0.9),
        (1.0, 0.9), (0.85, 0.0), (0.85, 0.0), (1.0, 0.0),
        (1.0, 0.0), (1.0, 0.55), (1.0, 0.55), (1.0, 0.9)]
KHALI = {9, 10, 11, 12}
GLIDE_SLOT = 29                # second avartan: 13th matra

ge_damp = ge.copy()
cut = int(SUB * SR)
fdn = int(0.06 * SR)
ge_damp[cut - fdn:cut] *= np.linspace(1, 0, fdn)
ge_damp[cut:] = 0.0

nslots = 2 * NB
drums = np.zeros((int(LOOP_S * SR) + 2 * SR, 2))
gebus = np.zeros(int(LOOP_S * SR) + 2 * SR)
for k in range(nslots):
    na_a, ge_a = THEKA[k % NB]
    a = int(k * SUB * SR)
    v = stereo(na * na_a, 0.25)
    drums[a:a + len(v)] += v
    if k == GLIDE_SLOT:
        v = stereo(ge_glide * 0.95, -0.25)
        drums[a:a + len(v)] += v
        gebus[a:a + len(ge_glide)] += ge_glide * 0.95
    elif k in (GLIDE_SLOT + 1, GLIDE_SLOT + 2):
        continue               # the glide owns these slots
    elif ge_a > 0:
        gk = ge_sam if k % NB == 0 else \
            (ge_damp if (k + 1) % NB in KHALI else ge)
        v = stereo(gk * ge_a, -0.25)
        drums[a:a + len(v)] += v
        gebus[a:a + len(gk)] += gk * ge_a
L = int(LOOP_S * SR)
drums = drums[:L]
gebus = gebus[:L]

# own-bus: the glide reads back ACROSS THE SEAM (doubled bus)
ge2 = np.concatenate([gebus, gebus])
t0g = GLIDE_SLOT * SUB
tsg, fsg = ruler.partial_track(
        ge2[int(t0g * SR):int((t0g + G_DUR + 0.35) * SR)],
        45.0, 80.0)
landp = float(np.nanmedian(fsg[tsg >= G_DUR - 0.05]))
risep = 1200 * np.log2(landp / float(np.nanmedian(
        fsg[tsg <= 0.10])))
centp = 1200 * np.log2(landp / hz(38))
check("the bayan bends into sam", risep >= 450.0
        and abs(centp) <= 25.0,
        f"{risep:.0f} cents risen across slots 13-15, arriving "
        f"{centp:+.0f} cents from Sa as the loop wraps")

# own-bus: slots strike (glide slots 30/31 are OWNED, not empty)
dbl = np.concatenate([drums, drums]).mean(axis=1)
onsets = ruler.onset_times(dbl, min_sep=0.12)
slots = {}
for t in onsets:
    k = int(round(t / SUB))
    if abs(t - k * SUB) <= 0.06:
        slots.setdefault(k % nslots, t)
check("every slot strikes", len(slots) == nslots,
        f"{len(slots)}/{nslots} onsets within 60 ms of grid "
        f"(the na keeps time through the glide)")
pr = ruler.pulse_rate(drums.mean(axis=1), 2.0, 5.0,
        lo=300.0, hi=2500.0)
check("the theka pulse reads back", abs(pr - 1.0 / SUB) <= 0.2,
        f"designed {1.0 / SUB:.2f} Hz, measured {pr:.2f} Hz")

# own-bus: khali still a hole (FFT band power, e55 ruler)
w0, w1 = int(0.08 * SR), int(0.28 * SR)
mono = drums.mean(axis=1)
hann = np.hanning(w1 - w0)


def band_rms(seg):
    p = np.abs(np.fft.rfft(seg * hann)) ** 2
    f = np.fft.rfftfreq(len(seg), 1.0 / SR)
    return float(np.sqrt(p[(f >= 30.0) & (f <= 100.0)].sum()))


be = np.array([band_rms(mono[int(k * SUB * SR) + w0:
        int(k * SUB * SR) + w1]) for k in range(nslots)])
kh = np.array([k % NB in KHALI for k in range(nslots)])
hole = float(np.median(be[kh]) / np.median(be[~kh]))
check("the khali quarter is a bass hole", hole <= 0.35,
        f"khali/bhari sustained bass-band slot energy {hole:.3f}")

DRONE = [("pa", hz(45), 140, 0.0, -0.35, 0.55),
        ("sa+", hz(50.015), 112, 1.2, 0.15, 0.50),
        ("sa-", hz(49.985), 112, 2.4, -0.15, 0.50),
        ("SA", hz(38), 138, 3.6, 0.35, 0.75)]
loop = Loop(LOOP_S, seed=56)
for name, f0d, n, at, pan, ampd in DRONE:
    v = fdpluck2(f0d, 12.0, amp=ampd, N=n)
    loop.add(at, stereo(v, pan))
    loop.add(at + 4.8, stereo(v, pan))
loop.add(0.0, drums * 0.8)
mix = loop.master(lp_hz=6500.0, drive=1.2)

check("seam", ruler.seam_rank(mix) <= 0.999,
        f"p{100 * ruler.seam_rank(mix):.2f}")
ch = ruler.chroma(mix.mean(axis=1))
top2 = set(np.argsort(ch)[-2:].tolist())
check("D and A are the two poles", top2 == {2, 9},
        f"top-2 classes {sorted(top2)} — the bayan lives on A "
        f"and arrives on D")

out = np.concatenate([mix, mix])
wav = os.path.join(outdir, "e56_bayan_glide.wav")
write_wav(wav, out)
ruler.report(out, "bayan_glide")
subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", wav,
        "-q:a", "5", wav.replace(".wav", ".ogg")], check=True)

print("ALL RULERS PASS" if not fails else f"FAILED: {fails}")
sys.exit(1 if fails else 0)

#!/usr/bin/env python3
"""e47 — gamak and andolan: the ornament earns its ruler.

Session 46's lead thread. The meend machinery does oscillating
ornaments for free — andolan (slow sway inside a note, +/-30
cents at 3 Hz, residence that breathes) and gamak (a full
ga<->ma shake, 200 cents peak-to-peak at 6 Hz, motion worn as
ornament). What it needed was an honest ruler: ornament_profile
reads (rate, depth) off a pitch contour.

The measurement lessons are the heart of the cycle. First, the
transfer is milder than theory predicted: a contour is NOT a
plain moving average under FM — each partial's refined peak
sits where the oscillation DWELLS (its extremes), so a 0.08 s
window keeps 0.88 of a 6 Hz depth where naive averaging says
0.66. Empiricism beats the sinc story; depth is verified through
a TRANSFER CALIBRATION (design x the control's measured ratio,
+/-20%). Second — the failure that taught it — the control must
model the INSTRUMENT CLASS: a bare FM sine (single partial) at
0.08 s windows glitches the contour into rate-multiplied junk
(24 Hz for a 6 Hz ornament), while a harmonic-rich control reads
true. Rate itself passes through untouched and is asserted
absolutely.

The piece: two drone cycles under one sung line — Sa, rise to
ga, andolan on ga, then the gamak shake up to ma, settle, and
the long way home to Sa (two plucks, the re-articulation landing
where a singer would take breath).

    python3 experiments/e47_gamak.py [outdir]
"""

import os
import subprocess
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))))
from loam import SR, hz, Loop, stereo, write_wav
from loam import ruler
from loam.fdstring import fdpluck

outdir = sys.argv[1] if len(sys.argv) > 1 else "render"
os.makedirs(outdir, exist_ok=True)
fails = []
WIN, HOP = 0.08, 0.02                 # ornament-grade contour


def check(name, cond, detail):
    print(f"  {'PASS' if cond else 'FAIL'} {name}: {detail}")
    if not cond:
        fails.append(name)


def contour(x):
    return ruler.pitch_contour(x, win_s=WIN, hop_s=HOP,
            fmin=80.0, fmax=800.0)


def seg(ts, fs, a, b):
    m = (ts >= a) & (ts <= b)
    return ts[m], fs[m]


def seg_err(ts, fs, tt, traj, a, b):
    m = (ts >= a) & (ts <= b)
    des = np.interp(ts[m], tt, traj)
    return float(np.abs(1200 * np.log2(fs[m] / des)).max())


SA, RE, GA, MA = hz(50), hz(52), hz(53), hz(55)

# ---- 1. transfer calibration: FM controls at each design rate --
# the control IS the transfer function: same rate, same window,
# known depth — and it must model the INSTRUMENT CLASS being
# measured. A plucked string is harmonic-rich, so the control is
# too (fundamental + 0.4 h2 + 0.2 h3); a bare FM sine is a
# single-partial adversarial signal, not a calibration (asserted
# below).
kk = {}
tt = np.arange(int(2.5 * SR)) / SR


def fm(r, d, rich):
    ph = 2 * np.pi * np.cumsum(
            200.0 * 2 ** (d * np.sin(2 * np.pi * r * tt) / 1200)) \
        / SR
    x = np.sin(ph)
    if rich:
        x = x + 0.4 * np.sin(2 * ph) + 0.2 * np.sin(3 * ph)
    return x


for r, d in ((3.0, 30.0), (6.0, 100.0)):
    ts, fs = contour(fm(r, d, True))
    mr, md = ruler.ornament_profile(*seg(ts, fs, 0.2, 2.3))
    kk[r] = md / d
    check(f"control rate reads true ({r:.0f} Hz)",
            abs(mr - r) <= 0.4, f"measured {mr:.2f} Hz, "
            f"transfer {kk[r]:.2f} of designed depth")
# the lesson, asserted: strip the control to a single partial and
# the same measurement collapses into rate-multiplied junk — the
# contour needs partials to refine against, so a control that
# fails to model the instrument class calibrates nothing
rp, _ = ruler.ornament_profile(
        *seg(*contour(fm(6.0, 100.0, False)), 0.2, 2.3))
check("a single-partial control is no control",
        abs(rp - 6.0) > 2.0,
        f"bare FM sine reads {rp:.1f} Hz for a 6 Hz ornament "
        f"(rich control: within 0.4)")

# ---- 2. the sung line, two plucks ------------------------------
# phrase A: Sa, rise, andolan on ga (3 Hz, +/-30 cents)
tA = np.arange(int(3.2 * SR)) / SR
trajA = np.where(tA < 0.8, SA,
        np.where(tA < 1.4, SA * (GA / SA) ** ((tA - 0.8) / 0.6),
        GA * 2 ** (30.0 * np.sin(2 * np.pi * 3.0 * (tA - 1.4))
                / 1200)))
# phrase B: gamak ga<->ma (6 Hz, 11.5 cycles so it LANDS on ma),
# settle, descend Re, home to Sa
GDUR = 11.5 / 6.0
segsB = [(0.7, MA, MA), (0.6, MA, RE), (0.5, RE, RE),
        (0.5, RE, SA), (1.7, SA, SA)]
tB_g = np.arange(int(GDUR * SR)) / SR
oscB = GA * (MA / GA) ** ((1 - np.cos(2 * np.pi * 6.0 * tB_g)) / 2)
tailB = [f_a * (f_b / f_a) ** np.linspace(0, 1, int(du * SR))
        for du, f_a, f_b in segsB]
trajB = np.concatenate([oscB] + tailB)
tBt = np.arange(len(trajB)) / SR

soloA = fdpluck(trajA, len(trajA) / SR, amp=1.0)
soloB = fdpluck(trajB, len(trajB) / SR, amp=1.0)

# ---- 3. own-bus rulers: design vs measured ---------------------
tsA, fsA = contour(soloA)
check("A: Sa dwell", seg_err(tsA, fsA, tA, trajA, 0.15, 0.65)
        <= 15.0,
        f"{seg_err(tsA, fsA, tA, trajA, 0.15, 0.65):.1f} cents")
rA, dA = ruler.ornament_profile(*seg(tsA, fsA, 1.55, 3.05))
check("A: andolan rate", abs(rA - 3.0) <= 0.4,
        f"designed 3.0 Hz, measured {rA:.2f} Hz")
check("A: andolan depth through transfer",
        0.8 * kk[3.0] <= dA / 30.0 <= 1.2 * kk[3.0],
        f"measured {dA:.0f} c / designed 30 c = {dA / 30.0:.2f} "
        f"(transfer {kk[3.0]:.2f})")

tsB, fsB = contour(soloB)
rB, dB = ruler.ornament_profile(*seg(tsB, fsB, 0.25, 1.85))
check("B: gamak rate", abs(rB - 6.0) <= 0.4,
        f"designed 6.0 Hz, measured {rB:.2f} Hz")
check("B: gamak depth through transfer",
        0.8 * kk[6.0] <= dB / 100.0 <= 1.2 * kk[6.0],
        f"measured {dB:.0f} c / designed 100 c = {dB / 100.0:.2f}"
        f" (transfer {kk[6.0]:.2f})")
for nm, a, b in (("ma settle", 2.05, 2.5), ("Sa home", 4.1, 5.2)):
    e = seg_err(tsB, fsB, tBt, trajB, a, b)
    check(f"B: {nm}", e <= 15.0, f"{e:.1f} cents")

# ---- 4. the piece ----------------------------------------------
DRONE = [("pa", hz(45), 140, 0.0, -0.35, 0.60),
        ("sa+", hz(50.015), 112, 1.2, 0.15, 0.55),
        ("sa-", hz(49.985), 112, 2.4, -0.15, 0.55),
        ("SA", hz(38), 138, 3.6, 0.35, 0.80)]
loop = Loop(9.6, seed=47)
for name, f0, n, at, pan, amp in DRONE:
    v = fdpluck(f0, 12.0, amp=amp, N=n)
    loop.add(at, stereo(v, pan))
    loop.add(at + 4.8, stereo(v, pan))
loop.add(0.3, stereo(soloA, 0.0))
loop.add(3.5, stereo(soloB, 0.0))

mix = loop.master(lp_hz=6500.0, drive=1.2)
check("seam", ruler.seam_rank(mix) <= 0.999,
        f"p{100 * ruler.seam_rank(mix):.2f}")
ch = ruler.chroma(mix.mean(axis=1))
top2 = set(np.argsort(ch)[-2:].tolist())
check("D and A are the two poles", top2 == {2, 9},
        f"top-2 classes {sorted(top2)}")

out = np.concatenate([mix, mix])
wav = os.path.join(outdir, "e47_gamak.wav")
write_wav(wav, out)
ruler.report(out, "gamak")
subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", wav,
        "-q:a", "5", wav.replace(".wav", ".ogg")], check=True)

print("ALL RULERS PASS" if not fails else f"FAILED: {fails}")
sys.exit(1 if fails else 0)

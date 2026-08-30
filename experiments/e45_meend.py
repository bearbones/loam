#!/usr/bin/env python3
"""e45 — meend: the FD string learns to bend.

Session 43's open thread. Pitch lives in one coefficient of the
scheme (lambda^2 = (c dt/dx)^2), so time-varying tension is one
multiply per step: fdpluck now takes an ARRAY of per-sample Hz
and the grid is sized for the trajectory's highest note. The new
ruler is pitch_contour (windowed HPS + sub-bin partial
refinement) — it turns "it bends" into cents, and earning it
cost two honest lessons recorded in ruler.py: chirped partials
smear in proportion to harmonic number, and a numerically CLEAN
spectrum lets log(junk) decide contests (fixed by clamping the
spectrum at -120 dB of peak — silence must be uniformly silent
evidence).

Rulers: the designed glide (hold - bend up 2 semitones - hold)
is measured back within tolerance on every segment, monotone
through the bend; the jawari still blooms on a BENT string
(sustain enrichment vs the same trajectory unbridged); and the
render loop — the e42 tanpura drone under a solo voice singing
two meend gestures (D-F-E, then E-D home to sa) — keeps its
seam and its D+A chroma.

    python3 experiments/e45_meend.py [outdir]
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


def check(name, cond, detail):
    print(f"  {'PASS' if cond else 'FAIL'} {name}: {detail}")
    if not cond:
        fails.append(name)


def seg_err(ts, fs, tt, traj, a, b):
    m = (ts >= a) & (ts <= b)
    des = np.interp(ts[m], tt, traj)
    return float(np.abs(1200 * np.log2(fs[m] / des)).max())


# ---- 1. the contour ruler can read a glide it did not render ---
t = np.arange(int(2.5 * SR)) / SR
fdes = 200.0 + 100.0 * np.clip(t - 0.5, 0, 1.5) / 1.5
ph = 2 * np.pi * np.cumsum(fdes) / SR
synth = np.sin(ph) + 0.4 * np.sin(2 * ph) + 0.2 * np.sin(3 * ph)
ts, fs = ruler.pitch_contour(synth, fmin=100.0, fmax=800.0)
err = float(np.abs(1200 * np.log2(
        fs / np.interp(ts, t, fdes))).max())
check("contour ruler reads a synthetic glide", err <= 25.0,
        f"max |err| {err:.1f} cents across hold+glide")

# ---- 2. the meend, designed vs measured ------------------------
DUR = 4.0
tt = np.arange(int(DUR * SR)) / SR
traj = np.where(tt < 1.0, 110.0,
        np.where(tt < 2.0, 110.0 * 2 ** ((tt - 1.0) * 2 / 12),
        123.47))
bent = fdpluck(traj, DUR)
check("bent string rings", bool(np.all(np.isfinite(bent))),
        f"peak {np.abs(bent).max():.2f}")
ts, fs = ruler.pitch_contour(bent, fmin=60.0, fmax=600.0)
for name, a, b, tol in (("hold A2", 0.2, 0.8, 12.0),
        ("the bend itself", 1.2, 1.8, 25.0),
        ("hold B2", 2.3, 3.7, 12.0)):
    e = seg_err(ts, fs, tt, traj, a, b)
    check(f"meend tracks design ({name})", e <= tol,
            f"max |err| {e:.1f} cents (tol {tol:.0f})")
m = (ts >= 1.1) & (ts <= 1.9)
check("bend is monotone", bool(np.all(np.diff(fs[m]) > -1.0)),
        f"{m.sum()} contour points rise through the glide")

# ---- 3. the jawari survives the bend ---------------------------
open_ = fdpluck(traj, DUR, bridge=False)
sus = slice(int(2.3 * SR), int(3.7 * SR))
enr = ruler.band_density(bent[sus], 1500, 6000) \
    / (ruler.band_density(open_[sus], 1500, 6000) + 1e-30)
check("bridge blooms on a bent string", enr >= 3.0,
        f"sustain 1.5-6 kHz x{enr:.1f} vs unbridged, same bend")

# ---- 4. the piece: drone + two meend gestures ------------------
DRONE = [("pa", hz(45), 140, 0.0, -0.35, 0.60),
        ("sa+", hz(50.015), 112, 1.2, 0.15, 0.55),
        ("sa-", hz(49.985), 112, 2.4, -0.15, 0.55),
        ("SA", hz(38), 138, 3.6, 0.35, 0.80)]
loop = Loop(9.6, seed=7)                 # two drone cycles
for name, f0, n, at, pan, amp in DRONE:
    v = fdpluck(f0, 12.0, amp=amp, N=n)
    loop.add(at, stereo(v, pan))
    loop.add(at + 4.8, stereo(v, pan))

D3, E3, F3 = hz(50), hz(52), hz(53)
p1t = np.arange(int(4.5 * SR)) / SR
phrase1 = np.where(p1t < 1.0, D3,
        np.where(p1t < 1.7, D3 * (F3 / D3) ** ((p1t - 1.0) / 0.7),
        np.where(p1t < 2.5, F3,
        np.where(p1t < 3.0, F3 * (E3 / F3) ** ((p1t - 2.5) / 0.5),
        E3))))
p2t = np.arange(int(4.2 * SR)) / SR
phrase2 = np.where(p2t < 0.8, E3,
        np.where(p2t < 1.5, E3 * (D3 / E3) ** ((p2t - 0.8) / 0.7),
        D3))
solo1 = fdpluck(phrase1, 4.5, amp=1.0)
solo2 = fdpluck(phrase2, 4.2, amp=1.0)
loop.add(0.3, stereo(solo1, 0.0))
loop.add(5.0, stereo(solo2, 0.0))

# solo rulers on the solo's OWN BUS (house rule)
for tag, solo, pt, ph_, dwells in (
        ("phrase1", solo1, p1t, phrase1,
            ((0.3, 0.9), (1.9, 2.4), (3.2, 4.3))),
        ("phrase2", solo2, p2t, phrase2,
            ((0.2, 0.7), (1.7, 4.0)))):
    ts, fs = ruler.pitch_contour(solo, fmin=80.0, fmax=800.0)
    worst = max(seg_err(ts, fs, pt, ph_, a, b) for a, b in dwells)
    check(f"solo {tag} dwells on pitch", worst <= 15.0,
            f"worst dwell max |err| {worst:.1f} cents")

mix = loop.master(lp_hz=6500.0, drive=1.2)
check("seam", ruler.seam_rank(mix) <= 0.999,
        f"p{100 * ruler.seam_rank(mix):.2f}")
# with a melody dwelling on E, e42's drone-only expectation
# (top-2 == {D, A}) is wrong BY DESIGN — the honest claim now:
# the tonic is supreme, and the drone's fifth still outweighs
# everything but the tonic and the melody's own dwell notes
ch = ruler.chroma(mix.mean(axis=1))
top4 = set(np.argsort(ch)[-4:].tolist())
check("D is the tonal center", int(np.argmax(ch)) == 2,
        f"argmax class {int(np.argmax(ch))}")
check("the drone's fifth holds top-4", 9 in top4,
        f"top-4 classes {sorted(top4)}")

out = np.concatenate([mix, mix])
wav = os.path.join(outdir, "e45_meend.wav")
write_wav(wav, out)
ruler.report(out, "meend")
subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", wav,
        "-q:a", "5", wav.replace(".wav", ".ogg")], check=True)

print("ALL RULERS PASS" if not fails else f"FAILED: {fails}")
sys.exit(1 if fails else 0)

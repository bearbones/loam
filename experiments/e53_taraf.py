#!/usr/bin/env python3
"""e53 — taraf: strings nobody plucks.

The oldest carried thread (banked in the tanpura sessions):
SYMPATHETIC strings. fdstring.fdsym runs a bank of undisturbed
FD lattices forced at a shared bridge node by an external
signal — no pluck, no initial condition, long ring (sig0=0.12,
t60 ~ 58 s). Everything a taraf bank claims is measured on its
raw per-string buses:

  - RESONANCE SELECTIVITY: driven by a sustained note at its own
    pitch, a taraf outsings its semitone-off neighbour by an
    order of magnitude; retune the DRIVE a semitone and the
    ratio inverts (the same measurement can say no).
  - CROSS-TUNING SYMPATHY: the taraf a fifth BELOW the drive
    sings on the shared partial (its h3 == the drive's h2) —
    and with a jawari-bright driver it sings LOUDER than the
    unison string. Sympathy follows the exciter's spectrum, not
    the score.
  - MEMORY: kicked by a short pluck that dies in ~1 s, the bank
    still holds its ring seconds later (late/early RMS ratio).
  - SILENCE: zero drive in, exactly zero out.

The piece: a slow Kafi phrase (fdpluck) whose own bus drives an
8-string Kafi-tuned taraf bank, the halo panned across the
field, over the two-pol drone. The halo's chroma must stay
inside Kafi — taraf can only say their own names.

    python3 experiments/e53_taraf.py [outdir]
"""

import os
import subprocess
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))))
from loam import SR, hz, Loop, stereo, write_wav
from loam import ruler
from loam.fdstring import fdpluck, fdpluck2, fdsym
from loam.strings import pluck

outdir = sys.argv[1] if len(sys.argv) > 1 else "render"
os.makedirs(outdir, exist_ok=True)
fails = []


def check(name, cond, detail):
    print(f"  {'PASS' if cond else 'FAIL'} {name}: {detail}")
    if not cond:
        fails.append(name)


def rms(x):
    return float(np.sqrt(np.mean(np.asarray(x) ** 2)))


# ---- 1. selectivity, and its inversion -------------------------
PROBE = [50, 53, 55, 57, 58, 60]
r_by_drive = {}
for dm in (57, 58):
    _, buses = fdsym([hz(n) for n in PROBE],
            fdpluck(hz(dm), 3.0), buses=True)
    r_by_drive[dm] = {n: rms(b) for n, b in zip(PROBE, buses)}
r57 = r_by_drive[57]
sel = r57[57] / r57[58]
r58d = r_by_drive[58]
inv = r58d[58] / r58d[57]
# thresholds calibrated: measured true ratios 12-14, and the
# broadband-attack failure mode (a KS pluck drive) measured 2.9
check("a taraf knows its own pitch", sel >= 6.0,
        f"unison/semitone RMS x{sel:.1f} under a driven 57")
check("retune the drive and the verdict flips", inv >= 6.0,
        f"semitone pair inverts to x{inv:.1f} under a driven 58")

# ---- 2. cross-tuning sympathy ----------------------------------
fifth = r57[50] / r57[58]
check("the fifth below sings on the shared partial",
        fifth >= 6.0, f"taraf 50 (h3 == drive h2) x{fifth:.1f} "
        f"over the semitone string — x{r57[50] / r57[57]:.2f} "
        f"vs unison: sympathy follows the exciter's spectrum")

# ---- 3. memory: the ring outlives the exciter ------------------
kick = pluck(hz(57), 3.0, t60=0.35, damp=0.3, seed=1)
_, kb = fdsym([hz(57)], kick, buses=True)
early = rms(kb[0][:int(1.0 * SR)])
late = rms(kb[0][int(1.5 * SR):int(2.8 * SR)])
klate = rms(kick[int(1.5 * SR):int(2.8 * SR)])
check("the bank remembers", late >= 0.5 * early
        and late > 1e6 * klate,
        f"taraf late/early RMS {late / early:.2f} while the "
        f"exciter decayed to {klate:.1e}")

# ---- 4. silence in, silence out --------------------------------
_, zb = fdsym([hz(57)], np.zeros(SR), buses=True)
check("no drive, no sound", float(np.abs(zb).max()) <= 1e-12,
        f"zero-drive bank peak {float(np.abs(zb).max()):.1e}")

# ---- 5. the piece ----------------------------------------------
LOOP_S = 9.6
KAFI = {2, 4, 5, 7, 9, 11, 0}
PHRASE = [(0.0, 1.8, 50), (1.8, 1.2, 53), (3.0, 1.2, 52),
        (4.2, 1.2, 50), (5.4, 1.2, 55), (6.6, 1.8, 57),
        (8.4, 1.2, 53)]
assert all(m % 12 in KAFI for _, _, m in PHRASE)

solo = np.zeros(int(LOOP_S * SR) + SR)
for at, dur, m in PHRASE:
    v = fdpluck(hz(m), dur + 0.25, amp=0.85)
    a = int(at * SR)
    solo[a:a + len(v)] += v
solo = solo[:int(LOOP_S * SR)]

BANK = [50, 52, 53, 55, 57, 59, 60, 62]
assert all(m % 12 in KAFI for m in BANK)
_, tb = fdsym([hz(n) for n in BANK], solo, buses=True)

# stereo halo: strings fan across the field; one shared norm so
# the buses keep their measured ratios. HALO_GAIN calibrated:
# 0.55 measured +8.5 dB over the melody (a halo louder than the
# hand), 0.041 sits it ~-14 dB under
HALO_GAIN = 0.041
pans = np.linspace(-0.55, 0.55, len(BANK))
tnorm = np.abs(tb).max() + 1e-12
taraf_st = np.zeros((len(solo), 2))
for b, p in zip(tb, pans):
    g = (b / tnorm) * HALO_GAIN
    taraf_st[:, 0] += g * np.cos((p + 1) * np.pi / 4)
    taraf_st[:, 1] += g * np.sin((p + 1) * np.pi / 4)

# own-bus: the halo speaks only Kafi
tch = ruler.chroma(tb.sum(axis=0))
top3 = set(np.argsort(tch)[-3:].tolist())
check("the halo speaks only Kafi", top3 <= KAFI,
        f"taraf-bus top-3 chroma classes {sorted(top3)}")
halo_db = 20 * np.log10(rms(taraf_st.sum(axis=1)) / rms(solo))
check("the halo sits under the melody", -32.0 <= halo_db <= -8.0,
        f"taraf/melody {halo_db:.1f} dB")

# own-bus: every melody note reads back
ts, fs = ruler.pitch_contour(solo, fmin=80.0, fmax=500.0)
worst = 0.0
for at, dur, m in PHRASE:
    sel_w = (ts >= at + 0.15) & (ts <= at + dur - 0.1)
    if sel_w.sum():
        med = float(np.median(fs[sel_w]))
        worst = max(worst, abs(1200 * np.log2(med / hz(m))))
check("every melody note reads back", worst <= 25.0,
        f"worst {worst:.1f} cents across {len(PHRASE)} notes")
dw = ruler.dwell_seconds(ts, fs, hz(50))
check("the line lives on Sa", int(np.argmax(dw)) == 0,
        f"dwell argmax class {int(np.argmax(dw))} "
        f"({dw[0]:.1f}s on Sa)")

DRONE = [("pa", hz(45), 140, 0.0, -0.35, 0.55),
        ("sa+", hz(50.015), 112, 1.2, 0.15, 0.50),
        ("sa-", hz(49.985), 112, 2.4, -0.15, 0.50),
        ("SA", hz(38), 138, 3.6, 0.35, 0.75)]
loop = Loop(LOOP_S, seed=53)
for name, f0, n, at, pan, ampd in DRONE:
    v = fdpluck2(f0, 12.0, amp=ampd, N=n)
    loop.add(at, stereo(v, pan))
    loop.add(at + 4.8, stereo(v, pan))
loop.add(0.0, stereo(solo, 0.0))
loop.add(0.0, taraf_st)
mix = loop.master(lp_hz=6500.0, drive=1.2)

check("seam", ruler.seam_rank(mix) <= 0.999,
        f"p{100 * ruler.seam_rank(mix):.2f}")
ch = ruler.chroma(mix.mean(axis=1))
top2 = set(np.argsort(ch)[-2:].tolist())
check("D and A are the two poles", top2 == {2, 9},
        f"top-2 classes {sorted(top2)}")

out = np.concatenate([mix, mix])
wav = os.path.join(outdir, "e53_taraf.wav")
write_wav(wav, out)
ruler.report(out, "taraf")
subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", wav,
        "-q:a", "5", wav.replace(".wav", ".ogg")], check=True)

print("ALL RULERS PASS" if not fails else f"FAILED: {fails}")
sys.exit(1 if fails else 0)

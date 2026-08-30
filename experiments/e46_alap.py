#!/usr/bin/env python3
"""e46 — alap in Kafi: the meend vocabulary speaks.

Session 45 made bending spellable; this cycle spells with it.
D dorian IS Kafi thaat, and the FD tanpura already drones D-A,
so the alap writes itself onto the existing instrument: four
single-pluck phrases with the classic arc — establish Sa, explore
ga-ma, reach Pa and touch upper ni, descend home to a long Sa —
every gesture a designed per-sample trajectory that pitch_contour
must read back within tolerance.

The new ruler is dwell_seconds (contour -> seconds of residence
per chromatic class): a raga's note hierarchy becomes a measured
claim. The alap is DESIGNED so Sa out-dwells Pa and Pa out-dwells
everything else, then the render is made to prove it — vadi by
the numbers, on the solo's own bus. The register arc (each
phrase's ceiling rises to phrase 3, then the line comes home) is
likewise asserted from measured contours, not the score.

    python3 experiments/e46_alap.py [outdir]
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


def traj_of(segs):
    """[(dur_s, hz_from, hz_to)] -> per-sample Hz, geometric
    glides (equal cents per second, how a hand actually bends)."""
    parts = []
    for dur, fa, fb in segs:
        n = int(dur * SR)
        parts.append(fa * (fb / fa) ** np.linspace(0, 1, n))
    return np.concatenate(parts)


def seg_err(ts, fs, tt, traj, a, b):
    m = (ts >= a) & (ts <= b)
    des = np.interp(ts[m], tt, traj)
    return float(np.abs(1200 * np.log2(fs[m] / des)).max())


SA, RE, GA, MA, PA, NI = hz(50), hz(52), hz(53), hz(55), hz(57), \
    hz(60)

# ---- the four phrases: (at, segments, dwell windows to verify) -
# dwell windows are (t_a, t_b) in phrase time, sitting inside the
# designed holds with margin for the contour's win_s/2 smear
PHRASES = [
    ("sthayi: Sa, and the step above", 0.4, [
        (1.0, SA, SA), (0.6, SA, RE), (0.6, RE, RE),
        (0.7, RE, SA), (1.5, SA, SA)],
        [(0.2, 0.8), (1.8, 2.0), (3.2, 4.2)]),
    ("ga-ma: the raga leans forward", 5.2, [
        (0.7, GA, GA), (0.6, GA, MA), (1.3, MA, MA),
        (0.6, MA, GA), (0.5, GA, GA), (0.5, GA, RE),
        (0.4, RE, RE)],
        [(0.2, 0.5), (1.5, 2.4), (2.8, 3.6)]),
    ("Pa, and a touch of ni above", 10.0, [
        (1.2, PA, PA), (0.6, PA, NI), (0.6, NI, NI),
        (0.7, NI, PA), (1.5, PA, PA)],
        [(0.2, 1.0), (2.0, 2.2), (3.3, 4.4)]),
    ("avarohana: the long way home", 14.8, [
        (0.5, MA, MA), (0.5, MA, GA), (0.4, GA, GA),
        (0.5, GA, RE), (0.4, RE, RE), (0.5, RE, SA),
        (1.6, SA, SA)],
        [(0.1, 0.4), (2.6, 2.8), (3.1, 4.2)]),
]

solos = []
dwell = np.zeros(12)
ceilings = []
for name, at, segs, wins in PHRASES:
    traj = traj_of(segs)
    dur = len(traj) / SR
    v = fdpluck(traj, dur, amp=1.0)
    solos.append((at, v))
    tt = np.arange(len(traj)) / SR
    ts, fs = ruler.pitch_contour(v, fmin=80.0, fmax=800.0)
    worst = max(seg_err(ts, fs, tt, traj, a, b) for a, b in wins)
    check(f"phrase tracks design ({name})", worst <= 15.0,
            f"worst dwell max |err| {worst:.1f} cents over "
            f"{len(wins)} windows")
    dwell += ruler.dwell_seconds(ts, fs, SA)
    ceilings.append(float(fs.max()))

# ---- the alap's claims, from measured contours -----------------
c1, c2, c3, c4 = ceilings
check("register arc rises to phrase 3",
        c1 < c2 < c3 and c4 < c3,
        f"ceilings {c1:.0f} < {c2:.0f} < {c3:.0f} Hz, home "
        f"{c4:.0f}")
order = np.argsort(dwell)[::-1]
check("Sa is where the line lives", int(order[0]) == 0,
        f"dwell argmax class {int(order[0])} "
        f"({dwell[0]:.1f}s on Sa)")
check("Pa is the second home (vadi claim)", int(order[1]) == 7,
        f"runner-up class {int(order[1])} ({dwell[7]:.1f}s on Pa "
        f"vs {dwell[order[2]]:.1f}s next)")

# ---- the piece: four drone cycles under the alap ---------------
DRONE = [("pa", hz(45), 140, 0.0, -0.35, 0.60),
        ("sa+", hz(50.015), 112, 1.2, 0.15, 0.55),
        ("sa-", hz(49.985), 112, 2.4, -0.15, 0.55),
        ("SA", hz(38), 138, 3.6, 0.35, 0.80)]
loop = Loop(19.2, seed=46)
for name, f0, n, at, pan, amp in DRONE:
    v = fdpluck(f0, 12.0, amp=amp, N=n)
    for k in range(4):
        loop.add(at + 4.8 * k, stereo(v, pan))
for at, v in solos:
    loop.add(at, stereo(v, 0.0))

mix = loop.master(lp_hz=6500.0, drive=1.2)
check("seam", ruler.seam_rank(mix) <= 0.999,
        f"p{100 * ruler.seam_rank(mix):.2f}")
# chroma claims are RELATIVE (e35): with the solo dwelling on Pa,
# D vs A argmax is a near-tie that flips with window length — the
# stable fact is the two POLES and their combined share. Sa's
# supremacy is already proven where it belongs: dwell time on the
# solo's own bus.
ch = ruler.chroma(mix.mean(axis=1))
top2 = set(np.argsort(ch)[-2:].tolist())
check("D and A are the two poles", top2 == {2, 9},
        f"top-2 classes {sorted(top2)}")
check("the poles hold the mix", ch[2] + ch[9] >= 0.5,
        f"combined share {ch[2] + ch[9]:.2f}")

out = np.concatenate([mix, mix])
wav = os.path.join(outdir, "e46_alap.wav")
write_wav(wav, out)
ruler.report(out, "alap")
subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", wav,
        "-q:a", "5", wav.replace(".wav", ".ogg")], check=True)

print("ALL RULERS PASS" if not fails else f"FAILED: {fails}")
sys.exit(1 if fails else 0)

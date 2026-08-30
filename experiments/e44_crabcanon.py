#!/usr/bin/env python3
"""e44 — crab canon, heard blind: ruler.dyad_pitches earns its keep.

The tooling half: blind two-voice pitch recovery (HPS finds the
stronger voice, its refined comb is nulled, HPS reads the
survivor — ruler.dyad_pitches). Its honest contract, measured on
126 + 87 random pluck dyads (100% inside it): both voices above
~midi 43, and NO SHADOW INTERVALS — an octave (2:1), a twelfth
(19, 2.997:1) or its penumbra (20, thirty cents off harmonic 3)
hide voice 2's spectrum inside voice 1's. The chase also fixed
two real hps_pitch octave bugs (winner can be harmonic 6 or 8;
a true fundamental can be <1% of winner yet 1000x the floor).

The musical half: a crab canon — voice 2 is voice 1 played
BACKWARDS, an octave down, both looping. Every beat's vertical
interval is drawn from the verified consonant palette
{3,4,7,8,9,15,16,21}, so the canon is composed to be provable by
its own measuring stick. The rulers then recover the score from
the MIXED render alone: 28/28 dyads named blind, and the crab
property (low voice reversed + 12 == high voice) asserted on
recovered data, not on the score.

    python3 experiments/e44_crabcanon.py [outdir]
"""

import os
import subprocess
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))))
from loam import SR, hz, Loop, stereo, write_wav
from loam import ruler
from loam.strings import pluck

outdir = sys.argv[1] if len(sys.argv) > 1 else "render"
os.makedirs(outdir, exist_ok=True)
fails = []


def check(name, cond, detail):
    print(f"  {'PASS' if cond else 'FAIL'} {name}: {detail}")
    if not cond:
        fails.append(name)


# ---- compose: backtracking crab in D dorian --------------------
L = 28
IV = {3, 4, 7, 8, 9, 15, 16, 21}     # verified palette, signed:
                                      # v1 stays above v2, no cross
DORIAN = {2, 4, 5, 7, 9, 11, 0}       # D dorian pitch classes
LO, HI = 57, 76
# placement order pairs t with L-1-t early, so vertical
# constraints bind as soon as possible
ORDER = []
for k in range(L // 2):
    ORDER += [k, L - 1 - k]


def ok_at(n, t):
    v = n[t]
    if v % 12 not in DORIAN:
        return False
    for nb in (t - 1, t + 1):
        if 0 <= nb < L and n[nb] is not None:
            if not (1 <= abs(v - n[nb]) <= 5):
                return False
    mate = L - 1 - t
    if n[mate] is not None:
        # the crab algebra: pair (a, b) sounds TWICE — beat t
        # plays (a, b-12), beat L-1-t plays (b, a-12). Both
        # vertical intervals must sit in the palette (e40's
        # inversion-closure lesson, wearing its retrograde
        # costume — first caught by the dyad ruler reading an
        # unverified 17 out of a "finished" canon).
        if (n[t] - (n[mate] - 12)) not in IV:
            return False
        if (n[mate] - (n[t] - 12)) not in IV:
            return False
    return True


def solve(idx, n, rng):
    if idx == len(ORDER):
        return len(set(n)) >= 12
    t = ORDER[idx]
    for v in rng.permutation(np.arange(LO, HI + 1)):
        n[t] = int(v)
        if ok_at(n, t) and solve(idx + 1, n, rng):
            return True
    n[t] = None
    return False


melody = [None] * L
assert solve(0, melody, np.random.default_rng(4)), "no crab found"
v2 = [melody[(L - 1 - t) % L] - 12 for t in range(L)]
print(f"  crab: v1 {melody}")

# ---- render the loop -------------------------------------------
# dur barely past BEAT: only the fade-to-zero tail wraps the seam.
# A longer ring would plant a structural octave shadow — the crab
# guarantees v2[L-1] == melody[0]-12, so beat L-1's low tail rings
# the exact sub-octave UNDER beat 0's high voice.
BEAT = 0.5
loop = Loop(L * BEAT, seed=3)
for t in range(L):
    hiv = pluck(hz(melody[t]), 0.55, t60=0.5, damp=0.3, seed=t)
    lov = pluck(hz(v2[t]), 0.55, t60=0.5, damp=0.3, seed=100 + t)
    loop.add(t * BEAT, stereo(hiv * 0.55, 0.4))
    loop.add(t * BEAT, stereo(lov * 0.55, -0.4))
mix = loop.master(lp_hz=7000.0, drive=1.15)
check("seam", ruler.seam_rank(mix) <= 0.999,
        f"p{100 * ruler.seam_rank(mix):.2f}")

# ---- hear it back, blind ---------------------------------------
mono = np.concatenate([mix, mix]).mean(axis=1)   # windows wrap
# pace prior (e39): onsets snap to the declared beat grid; a
# flux spike that lands nowhere near a beat is not a note
beats = {}
for t in ruler.onset_times(mono, min_sep=0.35):
    k = int(round(t / BEAT))
    if k < L and abs(t - k * BEAT) <= 0.08:
        beats.setdefault(k, t)
check("beat grid recovered", len(beats) == L,
        f"{len(beats)}/{L} beats claimed by onsets")

got = []
for k in sorted(beats):
    a = int((beats[k] + 0.02) * SR)
    seg = mono[a:a + int(0.45 * SR)].copy()
    fd = int(0.04 * SR)
    seg[-fd:] *= np.linspace(1, 0, fd)
    lo, hi = ruler.dyad_pitches(seg, 60.0, 2000.0)
    got.append((int(round(69 + 12 * np.log2(lo / 440.0))),
            int(round(69 + 12 * np.log2(hi / 440.0)))))

hits = sum(g == (v2[k], melody[k])
        for g, k in zip(got, sorted(beats)))
check("dyads named blind", hits == L, f"{hits}/{L} exact")

rec_hi = [g[1] for g in got]
rec_lo = [g[0] for g in got]
check("crab property, from recovered data alone",
        [m + 12 for m in rec_lo[::-1]] == rec_hi,
        "low voice reversed + octave == high voice")
pcs = {m % 12 for g in got for m in g}
check("recovered notes stay in D dorian", pcs <= DORIAN,
        f"classes {sorted(pcs)}")

# ---- ship ------------------------------------------------------
out = np.concatenate([mix, mix])
wav = os.path.join(outdir, "e44_crabcanon.wav")
write_wav(wav, out)
ruler.report(out, "crab")
subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", wav,
        "-q:a", "5", wav.replace(".wav", ".ogg")], check=True)

print("ALL RULERS PASS" if not fails else f"FAILED: {fails}")
sys.exit(1 if fails else 0)

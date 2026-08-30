#!/usr/bin/env python3
"""e40 — ouroboros: a circular canon. One 32-beat melody in D
dorian, composed (by seeded backtracking search) to harmonize
with ITSELF rotated half the loop: voice two is the same line 16
beats behind, an octave down, forever — the loop makes the round
endless, the search makes it counterpoint. Constraints: stepwise
motion (1-5 semitones, no immediate repeats), every rotation
interval consonant (unison/3rds/5th/6ths), no parallel perfects,
range >= an octave, and the wrap obeys the same laws — bar one is
the counterpoint of bar seventeen in both directions.

The cycle's ruler: loam.ruler.transcribe (onset_times + HPS per
inter-onset window, new this cycle) must hand the tune back from
voice one's own bus, note for note.

    python3 experiments/e40_ouroboros.py [outdir]
"""

import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))))
from loam import SR, hz, Loop, stereo, write_wav, seam_report
from loam import ruler
from loam.strings import pluck
from loam.pads import padsynth_stereo, formant_amps, VOWELS
from loam.space import reverb_loop
from loam.rhythm import scale_notes

outdir = sys.argv[1] if len(sys.argv) > 1 else "render"
os.makedirs(outdir, exist_ok=True)
fails = []


def check(name, cond, detail):
    print(f"  {'PASS' if cond else 'FAIL'} {name}: {detail}")
    if not cond:
        fails.append(name)


# ---- compose: the self-accompanying line -----------------------
NB = 32
HALF = NB // 2
SCALE = [m for m in scale_notes(50, "dorian", 2) if 55 <= m <= 79]
# inversion-closed consonances ONLY (unison, 3rds, 6ths): each
# rotation pair sounds in BOTH directions half a loop apart, so a
# P5 one way is a P4 the other — this canon must be invertible
# counterpoint at the octave, and the fifth goes home
CONS = {0, 3, 4, 8, 9}
rng = np.random.default_rng(0xE40)


def solve():
    n = [None] * NB
    n[0] = 62

    def ok(b, v):
        prev = n[b - 1]
        if not (1 <= abs(v - prev) <= 5):
            return False
        p = (b + HALF) % NB
        if n[p] is not None:
            if (v - n[p]) % 12 not in CONS:
                return False
            q = (b - 1 + HALF) % NB
            if n[b - 1] is not None and n[q] is not None:
                i1 = (n[b - 1] - n[q]) % 12
                if (v - n[p]) % 12 == i1 and i1 == 0:
                    return False
        return True

    def rec(b):
        if b == NB:
            if not (1 <= abs(n[0] - n[-1]) <= 5):
                return False
            if len(set(n)) < 10 or max(n) - min(n) < 12:
                return False
            i_last = (n[-1] - n[HALF - 1]) % 12
            i_first = (n[0] - n[HALF]) % 12
            return not (i_first == i_last and i_first == 0)
        cands = list(SCALE)
        rng.shuffle(cands)
        for v in cands:
            if ok(b, v):
                n[b] = v
                if rec(b + 1):
                    return True
                n[b] = None
        return False

    return n if rec(1) else None


mel = solve()
check("a line exists", mel is not None, f"melody: {mel}")
ivs = [(mel[b] - mel[(b + HALF) % NB]) % 12 for b in range(NB)]
par = sum(1 for b in range(NB)
        if ivs[b] == ivs[b - 1] and ivs[b] == 0)
check("counterpoint holds", all(i in CONS for i in ivs) and par == 0
        and max(mel) - min(mel) >= 12,
        f"all {NB} rotation intervals consonant, 0 parallel perfects, "
        f"range {max(mel) - min(mel)} semitones")

# ---- ring it ---------------------------------------------------
BPM = 84.0
spb = 60.0 / BPM
T = NB * spb
L = Loop(T, 0xE40)
v1 = np.zeros((L.n, 2))
v2 = np.zeros((L.n, 2))
for b in range(NB):
    at = b * spb
    a = 0.9 if b % 4 == 0 else 0.62
    m1 = pluck(hz(mel[b]), 1.6, amp=a * 0.8, damp=0.25, seed=b)
    m2 = pluck(hz(mel[(b - HALF) % NB] - 12), 1.8, amp=a * 0.7,
            damp=0.45, soft=1, seed=100 + b)
    for bus, ch in ((v1, stereo(m1, -0.45)), (v2, stereo(m2, 0.45))):
        idx = (int(at * SR) + np.arange(len(ch))) % L.n
        np.add.at(bus, idx, ch)

drone = padsynth_stereo(T, hz(38.0), formant_amps(hz(38.0), 18,
        VOWELS["oh"]), seed=3)
drone *= 0.1 / (np.max(np.abs(drone)) + 1e-12)

L.buf = v1 + v2 + drone
L.buf = reverb_loop(L.buf, t60=1.6, damp_hz=4400.0, mix=0.14)
mix = L.master(lp_hz=8000.0, drive=1.2)
write_wav(os.path.join(outdir, "e40_ouroboros.wav"), mix)
print(seam_report(mix))
ruler.report(mix, "canon")

# ---- audio rulers ----------------------------------------------
notes = ruler.transcribe(v1, min_sep=0.3, fmin=100.0, fmax=1200.0)
got = [int(round(md)) for _, md in notes]
hits = sum(1 for a, b in zip(got, mel) if a == b) if len(got) == NB else 0
check("the tune comes back", len(got) == NB and hits >= NB - 1,
        f"{len(got)} notes transcribed, {hits}/{NB} exact "
        f"(voice-1 bus)")

duet = v1 + v2
tuned, probe = 0.0, 0.0
for b in range(NB):
    seg = duet[int(b * spb * SR):int((b + 0.6) * spb * SR)]
    # Hann-taper: a loud fundamental's rectangular-window sidelobes
    # flood a narrow probe band; and probes sit at 3/4-semitone with
    # +/-2% width — a quarter-tone probe at +/-3% CONTAINS the very
    # peak it probes against (band [0.998f, 1.060f])
    segw = seg.mean(axis=1) * np.hanning(len(seg))
    for f in (hz(mel[b]), hz(mel[(b - HALF) % NB] - 12)):
        tuned += ruler.band_density(segw, f * 0.98, f * 1.02)
        probe += 0.5 * sum(ruler.band_density(segw,
                f * 2.0 ** (s / 12.0) * 0.98,
                f * 2.0 ** (s / 12.0) * 1.02) for s in (-1.5, 1.5))
check("both voices sound the design", tuned > 5.0 * probe,
        f"designed-dyad density {tuned / (probe + 1e-30):.1f}x "
        f"quarter-tone probes across all {NB} beats")

check("canon seam", ruler.seam_rank(mix) <= 0.999,
        f"rank=p{100 * ruler.seam_rank(mix):.1f}")

print("ALL RULERS PASS" if not fails else f"FAILED: {fails}")
sys.exit(1 if fails else 0)

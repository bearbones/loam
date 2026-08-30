#!/usr/bin/env python3
"""e39 — Plain Bob Minor: change ringing on the modal church
bells. Permutation music — six bells ring every row; the rows
walk a path through the symmetric group by place notation
(x.16 alternating, 12 at each lead end), and a plain course of
five leads returns to rounds after 60 rows: the loop IS the
group-theoretic closure. Handstroke gap observed (one bell-space
of silence before every handstroke row, the breath English
ringing takes).

The audio ruler this cycle was built for: ruler.onset_times
(spectral flux, promised in e36) must count all 360 strikes on
the dry bus, and a per-bell narrowband energy-RISE classifier
(rise, not level — ringing tails don't rise) must recover the
entire played permutation sequence from sound alone, matched
against the design.

    python3 experiments/e39_plainbob.py [outdir]
"""

import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))))
from loam import SR, hz, Loop, stereo, write_wav, seam_report
from loam import ruler
from loam.modal import strike, CHURCH_BELL
from loam.space import reverb_loop

outdir = sys.argv[1] if len(sys.argv) > 1 else "render"
os.makedirs(outdir, exist_ok=True)
fails = []


def check(name, cond, detail):
    print(f"  {'PASS' if cond else 'FAIL'} {name}: {detail}")
    if not cond:
        fails.append(name)


# ---- the method (design side) ----------------------------------
def change(row, notation):
    r = list(row)
    if notation == "x":
        pairs = [(0, 1), (2, 3), (4, 5)]
    elif notation == "16":
        pairs = [(1, 2), (3, 4)]
    elif notation == "12":
        pairs = [(2, 3), (4, 5)]
    for a, b in pairs:
        r[a], r[b] = r[b], r[a]
    return tuple(r)


LEAD = ["x", "16", "x", "16", "x", "16", "x", "16", "x", "16", "x", "12"]
ROUNDS = (1, 2, 3, 4, 5, 6)
rows = [ROUNDS]
for i in range(60):
    rows.append(change(rows[-1], LEAD[i % 12]))
check("course closes", rows[60] == ROUNDS and len(set(rows[:60])) == 60,
        f"60 distinct rows, row 60 = rounds: {rows[60] == ROUNDS}")
rows = rows[:60]

# ---- the ringing ------------------------------------------------
BELLS = [76, 74, 72, 71, 69, 67]        # G-major hexachord, rounds descend
SPACE = 0.24
T = 390 * SPACE                          # 360 bells + 30 handstroke gaps
L = Loop(T, 0xE39)
rng = np.random.default_rng(0xE39)
pans = np.linspace(-0.7, 0.7, 6)         # the rope circle
t60s = np.linspace(2.2, 3.2, 6)          # tenor rings longest
amps = np.linspace(0.55, 0.8, 6)

dry = np.zeros((L.n, 2))
design = []                              # (time, bell) ground truth
for r, row in enumerate(rows):
    t_row = SPACE * (6 * r + r // 2)     # r//2 gaps have passed
    for pos, bell in enumerate(row):
        at = t_row + pos * SPACE
        b = bell - 1
        m = strike(hz(BELLS[b]), float(t60s[b]), CHURCH_BELL,
                amp=float(amps[b]), rng=rng, knock=0.06)
        ch = stereo(m, float(pans[b]))
        idx = (int(at * SR) + np.arange(len(ch))) % L.n
        np.add.at(dry, idx, ch)
        design.append((at, b))

L.buf = reverb_loop(dry, t60=2.8, size=1.3, damp_hz=3600.0, mix=0.22)
mix = L.master(lp_hz=8500.0, drive=1.1)
write_wav(os.path.join(outdir, "e39_plainbob.wav"), mix)
print(seam_report(mix))
ruler.report(mix, "tower")

# ---- audio rulers (dry bus, house rule) ------------------------
# min_sep just under the bell spacing: a ghost 130-210 ms after a
# strike (tail flutter in the gap) then loses the local-max contest
# to its parent peak — the ringing pace is the caller's prior
onsets = ruler.onset_times(dry, min_sep=0.2)
check("all strikes counted", len(onsets) == 360,
        f"{len(onsets)} onsets detected of 360 struck")

primes = [hz(m) for m in BELLS]
wpre, wpost = int(0.11 * SR), int(0.11 * SR)


def band_e(seg, f):
    return ruler.band_density(seg, f * 0.97, f * 1.03)


recovered = []
mono = dry.mean(axis=1)
for t in onsets:
    i = int(t * SR)
    pre = mono[max(0, i - wpre):max(1, i)]
    post = mono[i:i + wpost]
    rises = [band_e(post, f) - band_e(pre, f) for f in primes]
    recovered.append(int(np.argmax(rises)))

n_cmp = min(len(recovered), 360)
truth = [b for _, b in sorted(design)][:n_cmp]
match = sum(1 for a, b in zip(recovered[:n_cmp], truth) if a == b)
check("order recovered", len(onsets) == 360 and match / 360 >= 0.97,
        f"{match}/{n_cmp} strikes classified to the designed bell "
        f"({match / max(n_cmp, 1) * 100:.1f}%)")

gaps = np.diff(onsets)
row_end = gaps[5::6]                     # every 6th interval spans rows
within = np.concatenate([gaps[i::6] for i in range(5)])
big = row_end[1::2]                      # after backstroke: the breath
small = row_end[0::2]
check("handstroke gap", 1.8 <= np.median(big) / np.median(within) <= 2.2
        and 0.9 <= np.median(small) / np.median(within) <= 1.1,
        f"gap {np.median(big) / np.median(within):.2f}x a bell-space "
        f"(design 2.0), plain row joins {np.median(small)
        / np.median(within):.2f}x (design 1.0)")

check("tower seam", ruler.seam_rank(mix) <= 0.999,
        f"rank=p{100 * ruler.seam_rank(mix):.1f}")

print("ALL RULERS PASS" if not fails else f"FAILED: {fails}")
sys.exit(1 if fails else 0)

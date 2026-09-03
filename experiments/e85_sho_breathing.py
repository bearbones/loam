#!/usr/bin/env python3
"""loam e85 — the sho breathes through Etenraku's harmony.

nihon.sho() + nihon.AITAKE are new: the mouth organ's cluster
chords. The documented practice is that the sho sounds the
aitake whose FUNDAMENTAL is the current melody note — so this
piece is e84's Etenraku phrase A with the melody removed and
only its harmonic halo left breathing:

    bo | otsu ... ichi ... kotsu ichi otsu ... bo otsu

Each chord is one breath: an arch swell that never reaches
zero (the sho player inhales AND exhales through the reeds —
the sound turns, it does not stop), and the reed BRIGHTENS as
pressure rises, so the swell opens the spectrum. Chord changes
sit in the breath troughs.

Voicing stance (see nihon.AITAKE): fundamentals and the
Category-1 collection are verified against the literature;
gyo and sojo-ju are published exactly; the Category-1 chords
are collection-constrained realizations because every source
keeps its full chart inside an image.

    python3 experiments/e85_sho_breathing.py [outdir]
"""

import os
import sys

import numpy as np
from scipy.signal import butter, sosfilt

sys.path.insert(0, os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))))
from loam import SR, hz, write_wav
from loam import ruler
from loam.nihon import sho, AITAKE
from loam.space import reverb_loop

outdir = sys.argv[1] if len(sys.argv) > 1 else "render"
os.makedirs(outdir, exist_ok=True)
fails = []


def check(name, cond, detail):
    print(f"  {'PASS' if cond else 'FAIL'} {name}: {detail}")
    if not cond:
        fails.append(name)


def rms(x):
    return float(np.sqrt(np.mean(np.asarray(x, float) ** 2) + 1e-30))


LOOP_S = 38.4
N = int(LOOP_S * SR)
BEAT = 1.6

# Etenraku phrase A as its aitake halo (chord = melody note's
# fundamental; consecutive repeats merge into one long breath)
PROG = [
    ("bo", 1), ("otsu", 4), ("ichi", 4), ("kotsu", 2),
    ("ichi", 2), ("otsu", 4), ("bo", 2), ("otsu", 5),
]
OVER = 0.35                       # breath overlap at the change


def add_wrap(bus, t, ss):
    i0 = int(round(t * SR)) % N
    n = len(ss)
    if i0 + n <= N:
        bus[i0:i0 + n] += ss
    else:
        k = N - i0
        bus[i0:] += ss[:k]
        bus[:n - k] += ss[k:]


bus = np.zeros((N, 2))
t = 0.2
BOUNDS, SEGS = [], []
for i, (name, beats) in enumerate(PROG):
    dur = beats * BEAT + OVER
    v = sho(AITAKE[name], dur, edge_s=OVER, seed=17 + 5 * i)
    add_wrap(bus, t - OVER / 2, v)
    SEGS.append((name, t, beats * BEAT))
    t += beats * BEAT
    BOUNDS.append(t % LOOP_S)

wet = reverb_loop(bus, t60=2.6, size=1.25)
mix = 0.80 * bus + 0.30 * wet
mix *= 0.92 / (np.abs(mix).max() + 1e-12)
write_wav(os.path.join(outdir, "e85_sho_breathing.wav"), mix)

# ---- rulers ------------------------------------------------------
print("e85 rulers:")

# 1. seam
check("seam", ruler.seam_rank(mix) <= 0.999,
        f"p{100 * ruler.seam_rank(mix):.2f}")

# 2 + 3. membership, both directions, once per distinct aitake at
# the mid of its longest breath: every written pipe's fundamental
# is a line within 25 cents, and probe pitches OUTSIDE the
# collection (C5 F5 G5 G#5 — none is a low harmonic of a written
# pipe) stay at least 12 dB below the weakest written line. The
# lowest prominent line is the chord's FUNDAMENTAL (the naming
# rule the aitake system runs on).
best = {}
for name, t0, dur in SEGS:
    if name not in best or dur > best[name][1]:
        best[name] = (t0, dur)
mem_ok, fund_ok = True, True
worst_gap, worst_cents = 1e9, 0.0
for name, (t0, dur) in best.items():
    mid = t0 + dur / 2
    seg = mix[int((mid - 0.75) * SR):int((mid + 0.75) * SR), :]
    seg = seg.mean(axis=1)
    n4 = 4 * len(seg)
    sp = np.abs(np.fft.rfft(seg * np.hanning(len(seg)), n4))
    fq = np.fft.rfftfreq(n4, 1.0 / SR)

    def line_db(f0):
        sel = (fq > f0 * 0.985) & (fq < f0 * 1.015)
        return 20.0 * np.log10(sp[sel].max() + 1e-30), \
            1200.0 * np.log2(fq[sel][np.argmax(sp[sel])] / f0)

    written = [line_db(hz(m)) for m in AITAKE[name]]
    worst_cents = max(worst_cents,
            max(abs(c) for _, c in written))
    probes = [line_db(hz(m))[0] for m in (72, 77, 79, 80)]
    gap = min(d for d, _ in written) - max(probes)
    worst_gap = min(worst_gap, gap)
    mem_ok = mem_ok and gap >= 12.0 \
        and max(abs(c) for _, c in written) <= 25.0
    # lowest prominent line == fundamental: strongest line below
    # the second-written pipe must sit on pipe one
    f_fund = hz(AITAKE[name][0])
    f_next = hz(AITAKE[name][1])
    sel = (fq > 300.0) & (fq < f_next * 0.97)
    f_low = fq[sel][np.argmax(sp[sel])]
    fund_ok = fund_ok and abs(1200.0 * np.log2(
            f_low / f_fund)) <= 30.0
check("membership", mem_ok,
        f"4 aitake: written lines within {worst_cents:.1f} c, "
        f"weakest written vs loudest probe {worst_gap:+.1f} dB")
check("fundamental_lowest", fund_ok,
        "lowest prominent line is the naming pipe in all 4 aitake")

# 4. the breath turns at the change: envelope trough within
# 0.35 s of each written boundary. OWN BUS: these are claims
# about the sho's breath, and 2.6 s of room fills the troughs
# and smears level-vs-brightness (measured through the mix,
# the trough drifted +0.40 s and the coupling read r=-0.09)
fr = int(0.05 * SR)
mm = bus.mean(axis=1)
env = np.sqrt(np.mean(mm[:len(mm) // fr * fr].reshape(-1, fr) ** 2,
        axis=1))
env = np.convolve(env, np.ones(9) / 9, mode="same")
te = np.arange(len(env)) * fr / SR
worst_off = 0.0
for tb in BOUNDS:
    sel = (te >= tb - 0.9) & (te <= tb + 0.9)
    off = te[sel][np.argmin(env[sel])] - tb
    worst_off = max(worst_off, abs(off))
check("breath_turns", worst_off <= 0.35,
        f"{len(BOUNDS)} changes, worst trough offset "
        f"{worst_off:.2f} s")

# 5. the swell opens the spectrum — WITHIN each long breath
# (across chords the claim is unmeasurable: chord identity moves
# the centroid ~150 Hz on its own, uncorrelated with level, and
# the first cut of this ruler read r=-0.08 pooling all windows)
WIN = 0.4
r_min, r_all = 1.0, []
for name, t0, dur in SEGS:
    if dur < 3.0:
        continue
    cen, lvl = [], []
    i = t0 + 0.3
    while i + WIN <= t0 + dur - 0.3:
        a, b = int(i * SR), int((i + WIN) * SR)
        cen.append(ruler.centroid_hz(mm[a:b]))
        lvl.append(rms(mm[a:b]))
        i += WIN
    r_c = float(np.corrcoef(cen, lvl)[0, 1])
    r_all.append(r_c)
    r_min = min(r_min, r_c)
check("swell_brightens", r_min >= 0.7,
        f"{len(r_all)} long breaths, centroid-vs-level r "
        f"{min(r_all):.3f}..{max(r_all):.3f}")

# 6. hyojo poles: the halo rests on E and B (otsu holds 13 of 24
# beats and every chord carries B5)
ch = ruler.chroma(mix, lo=200.0, hi=2500.0)
top2 = set(np.argsort(ch)[-2:].tolist())
check("chroma_poles", top2 == {4, 11},
        f"top-2 classes {sorted(top2)} (want E=4, B=11); "
        f"E {ch[4]:.2f} B {ch[11]:.2f}")

ruler.report(mix, "e85_sho_breathing")
print(f"\n{'ALL PASS' if not fails else 'FAILS: ' + str(fails)}")
sys.exit(1 if fails else 0)

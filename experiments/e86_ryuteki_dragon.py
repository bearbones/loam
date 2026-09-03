#!/usr/bin/env python3
"""loam e86 — ryuteki: the dragon flute completes the trio.

nihon.ryuteki(): the waveguide flute voiced breathy, plus the
gestures that make the gagaku flute:

  - REGISTER FLIP: fukura -> seme, the mid-breath jump to the
    overblown octave on the same fingering. Two renders of the
    same bore (flute()'s `overblow` IS the jet-speed jump),
    crossfaded in ~80 ms.
  - FINGER FLICKS: ~90 c warp pits + ~6 dB amplitude notches,
    because the striking finger briefly kills the resonance.
    The notch is the measurable mark; the pitch pit is design-
    stated color (at this breathiness a bare 50 ms pitch dip
    sits below honest measurability — the cycle's ruler story).

The piece: Etenraku phrase A a third time — e84 played the
melody (hichiriki), e85 the harmony (sho aitake), e86 plays it
the ryuteki way: an octave up, the long E's starting fukura
and flipping to seme mid-breath. Next: all three at once.

    python3 experiments/e86_ryuteki_dragon.py [outdir]
"""

import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))))
from loam import SR, hz, stereo, write_wav
from loam import ruler
from loam.nihon import ryuteki
from loam.space import reverb_loop

outdir = sys.argv[1] if len(sys.argv) > 1 else "render"
os.makedirs(outdir, exist_ok=True)
fails = []


def check(name, cond, detail):
    print(f"  {'PASS' if cond else 'FAIL'} {name}: {detail}")
    if not cond:
        fails.append(name)


LOOP_S = 38.4
N = int(LOOP_S * SR)
BEAT = 1.6

# (midi, beats, flip_at, graces) — flip notes are written at the
# FUKURA pitch and sound the octave after the flip
MELODY = [
    (86, 1, -1.0, ()),                    # D6 pickup
    (76, 2, 0.9, ()),                     # E5 -> E6, the first cry
    (88, 2, -1.0, ()),                    # stays seme
    (83, 2, -1.0, (0.25,)),               # B5, struck
    (83, 2, -1.0, ()),
    (81, 2, -1.0, (0.30,)),               # A5, the low turn
    (83, 2, -1.0, ()),
    (76, 2, 0.8, ()),                     # E5 -> E6 again
    (88, 1, -1.0, ()),
    (88, 1, -1.0, (0.45,)),
    (86, 2, -1.0, (0.35,)),               # D6, struck
    (76, 3, 1.1, ()),                     # the long last flip
]


def add_wrap(bus, t, ss):
    i0 = int(round(t * SR)) % N
    n = len(ss)
    if i0 + n <= N:
        bus[i0:i0 + n] += ss
    else:
        k = N - i0
        bus[i0:] += ss[:k]
        bus[:n - k] += ss[k:]


NOTES, DURS = [], []
mel = np.zeros((N, 2))
t = 0.2
for i, (m, beats, fl, gr) in enumerate(MELODY):
    dur = beats * BEAT - 0.15
    v = ryuteki(hz(m), dur, flip_at=fl, graces=gr, seed=41 + 7 * i)
    NOTES.append(v)
    DURS.append(dur)
    add_wrap(mel, t, stereo(v * 0.9, -0.06))
    t += beats * BEAT

wet = reverb_loop(mel, t60=2.0, size=1.15)
mix = 0.85 * mel + 0.26 * wet
mix *= 0.92 / (np.abs(mix).max() + 1e-12)
write_wav(os.path.join(outdir, "e86_ryuteki_dragon.wav"), mix)

# ---- rulers ------------------------------------------------------
print("e86 rulers:")

# 1. seam
check("seam", ruler.seam_rank(mix) <= 0.999,
        f"p{100 * ruler.seam_rank(mix):.2f}")

# 2. the flip is two honest registers: fukura centers on f0,
# seme centers on the octave, each in its own IF band
worst_lo, worst_hi = 0.0, 0.0
for v, (m, beats, fl, gr), dur in zip(NOTES, MELODY, DURS):
    if fl <= 0.0:
        continue
    f0 = hz(m)
    lo = ruler.if_pitch(v, f0)
    hi = ruler.if_pitch(v, 2 * f0)
    c_lo = 1200.0 * np.log2(np.median(
            lo[int(0.25 * SR):int((fl - 0.15) * SR)]) / f0)
    c_hi = 1200.0 * np.log2(np.median(
            hi[int((fl + 0.15) * SR):int((dur - 0.2) * SR)])
            / (2 * f0))
    worst_lo = max(worst_lo, abs(c_lo))
    worst_hi = max(worst_hi, abs(c_hi))
check("flip_registers", worst_lo <= 30.0 and worst_hi <= 30.0,
        f"4 flips: fukura within {worst_lo:.1f} c, "
        f"seme within {worst_hi:.1f} c of the octave")

# 3. non-flip notes center on their written pitch
worst = 0.0
for v, (m, beats, fl, gr), dur in zip(NOTES, MELODY, DURS):
    if fl > 0.0:
        continue
    inst = ruler.if_pitch(v, hz(m))
    s0, s1 = max(0.45, 0.3 * dur), dur - 0.2
    c = 1200.0 * np.log2(np.median(
            inst[int(s0 * SR):int(s1 * SR)]) / hz(m))
    worst = max(worst, abs(c))
check("centers", worst <= 20.0,
        f"8 held notes, worst center {worst:.1f} c")

# 4. finger strikes mark where written and nowhere else:
# broadband envelope notch >= 5 dB at each written grace, and no
# false notch beyond 4 dB elsewhere in any graced note
k = int(0.010 * SR)
worst_notch, worst_false = 1e9, 0.0
for v, (m, beats, fl, gr), dur in zip(NOTES, MELODY, DURS):
    if not gr:
        continue
    e = np.convolve(np.abs(v), np.ones(k) / k, mode="same")
    edb = 20.0 * np.log10(e + 1e-12)
    away = np.zeros(len(edb), bool)
    away[int(0.3 * SR):int((dur - 0.2) * SR)] = True
    base_all = np.median(edb[int(0.3 * SR):int((dur - 0.2) * SR)])
    for tg in gr:
        a, b = int((tg - 0.04) * SR), int((tg + 0.04) * SR)
        base = np.median(edb[max(0, int((tg - 0.25) * SR)):
                             int((tg + 0.25) * SR)])
        worst_notch = min(worst_notch, base - edb[a:b].min())
        away[int((tg - 0.12) * SR):int((tg + 0.12) * SR)] = False
    worst_false = max(worst_false, base_all - edb[away].min())
check("grace_marks", worst_notch >= 5.0 and worst_false <= 4.0,
        f"4 strikes: weakest notch {worst_notch:.1f} dB, deepest "
        f"false notch {worst_false:.1f} dB")

# 5. the breath is loud and front-loaded: hiss-band gust in the
# attack over the same note's sustain
from scipy.signal import butter, sosfilt
sos_h = butter(4, [2500.0, 7000.0], btype="bandpass", fs=SR,
        output="sos")


def rmsv(x):
    return float(np.sqrt(np.mean(x ** 2) + 1e-30))


gusts = []
for v, (m, beats, fl, gr), dur in zip(NOTES, MELODY, DURS):
    h = sosfilt(sos_h, v)
    gusts.append(20.0 * np.log10(
            rmsv(h[:int(0.22 * SR)])
            / rmsv(h[int(0.5 * dur * SR):int((dur - 0.2) * SR)])))
check("breath_gust", min(gusts) >= 2.0,
        f"12 notes, gust {min(gusts):.1f}-{max(gusts):.1f} dB "
        f"over sustain")

# 6. the phrase rests on E. A solo BREATHY instrument votes its
# hiss into every chroma class (full-band top-2 came out a coin
# flip between near-equal 0.1s) — restrict the claim to the band
# the fundamentals actually live in, and claim only the crown
ch = ruler.chroma(mix, lo=600.0, hi=1400.0)
check("chroma_crown", int(np.argmax(ch)) == 4,
        f"argmax class {int(np.argmax(ch))} (want E=4); "
        f"E {ch[4]:.2f} B {ch[11]:.2f} D {ch[2]:.2f}")

ruler.report(mix, "e86_ryuteki_dragon")
print(f"\n{'ALL PASS' if not fails else 'FAILS: ' + str(fails)}")
sys.exit(1 if fails else 0)

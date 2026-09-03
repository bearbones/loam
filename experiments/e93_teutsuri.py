#!/usr/bin/env python3
"""loam e93 — te-utsuri: the sho changes chords one pipe at a time.

In gagaku practice the sho does not switch aitake as a block:
common tones HOLD, departing pipes fade with the breath, and
the new pipes roll in one by one, lowest first. So the unit of
this piece is the PIPE, not the chord — the progression
(kotsu -> bo -> otsu -> ju_so, 6 s each, 24 s loop) compiles
into pipe segments:

  - {A5 B5 D6 E6} are common to ALL four aitake: they become
    continuous drones, each built as a lapped equal-power pair
    (two renders, 1 s sin/cos gain laps placed mid-chord) so
    the loop closes without a seam dip;
  - F#6 holds across one interior boundary (bo -> otsu);
  - six entrance events roll at written times (chord start +
    0.10 + 0.15 per rank, lowest first).

Measurement gifts, verified against the harmonic table before
writing a single ruler: the drones are the HIGH common tones
and every entrant sits below or between them, so NO sounding
pipe has a harmonic at any entrant's fundamental — every
entrance and departure line is unpolluted (e88/e90's pollution
rule, passed for once by design). And the written sin^2 edge
predicts its own -20 dB crossing analytically, so entrances
are design-vs-measured to the millisecond, not to a vibe.

    python3 experiments/e93_teutsuri.py [outdir]
"""

import os
import sys

import numpy as np
from scipy.signal import butter, sosfiltfilt

sys.path.insert(0, os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))))
from loam import SR, hz, write_wav
from loam import ruler
from loam.nihon import sho
from loam.space import reverb_loop

outdir = sys.argv[1] if len(sys.argv) > 1 else "render"
os.makedirs(outdir, exist_ok=True)
fails = []


def check(name, cond, detail):
    print(f"  {'PASS' if cond else 'FAIL'} {name}: {detail}")
    if not cond:
        fails.append(name)


LOOP_S = 24.0
N = int(LOOP_S * SR)
CHORD_S = 6.0
EDGE = 0.30
STAG = 0.15

PROG = [("kotsu", [69, 76, 81, 83, 86, 88]),
        ("bo", [74, 81, 83, 86, 88, 90]),
        ("otsu", [76, 81, 83, 86, 88, 90]),
        ("ju_so", [79, 81, 83, 86, 88])]
DRONES = [81, 83, 86, 88]

# pipe segments for the changing voices: (midi, start_chord,
# end_chord) in chord indices, end exclusive
SEGS = [(69, 0, 1), (76, 0, 1), (74, 1, 2), (90, 1, 3),
        (76, 2, 3), (79, 3, 4)]
# entrance roll: rank among that chord's NEW pipes, low first
ENTR = {}
for ci, (nm, ch) in enumerate(PROG):
    prev = PROG[(ci - 1) % 4][1]
    new = sorted(m for m in ch if m not in prev)
    for r, m in enumerate(new):
        ENTR[(m, ci)] = ci * CHORD_S + 0.10 + r * STAG


def add_wrap(bus, t, ss):
    i0 = int(round(t * SR)) % N
    n = len(ss)
    if i0 + n <= N:
        bus[i0:i0 + n] += ss
    else:
        k = N - i0
        bus[i0:] += ss[:k]
        bus[:n - k] += ss[k:]


def rms(x):
    return float(np.sqrt(np.mean(np.asarray(x, float) ** 2) + 1e-30))


bus = np.zeros((N, 2))

# drones: lapped equal-power pairs — A spans [3,16], B spans
# [15,28]->[15,24]+[0,4], sin/cos amplitude laps over 1 s
# (equal POWER: gains sin/cos, not sin^2/cos^2 — e83)
DR_DUR = 13.0
for m in DRONES:
    for t0, sd in ((3.0, 100 + m), (15.0, 200 + m)):
        v = sho([m], DR_DUR, floor=1.0, edge_s=0.01, seed=sd)
        v = v / rms(v)
        tl = np.arange(len(v)) / SR
        g = np.ones(len(v))
        g[tl < 1.0] = np.sin(0.5 * np.pi * tl[tl < 1.0])
        gd = tl > DR_DUR - 1.0
        g[gd] = np.cos(0.5 * np.pi * (tl[gd] - (DR_DUR - 1.0)))
        add_wrap(bus, t0, v * (0.055 * g)[:, None])

# changing pipes: one render per segment, sho's own fixed-time
# edges as the entrance/release
SEG_R = []
for m, c0, c1 in SEGS:
    t_on = ENTR[(m, c0)]
    dur = c1 * CHORD_S + 0.30 - t_on
    v = sho([m], dur, floor=1.0, edge_s=EDGE,
            seed=300 + m + 17 * c0)
    v = v / rms(v)
    SEG_R.append((t_on, dur, v))
    add_wrap(bus, t_on, v * 0.075)

dry = bus
wet = reverb_loop(dry, t60=2.3, size=1.3)
mix = 0.80 * dry + 0.30 * wet
mix *= 0.92 / (np.abs(mix).max() + 1e-12)
write_wav(os.path.join(outdir, "e93_teutsuri.wav"), mix)

# ---- rulers ------------------------------------------------------
print("e93 rulers (per-pipe line claims on the dry sho bus):")

dm = dry.mean(axis=1)


def line_env(m):
    # ruler.line_env, born this cycle: the old bandpass-and-
    # rectify version leaked 100 c neighbors through its skirts
    # (a 4th-order +-25 c bandpass rejects them by only ~3 dB)
    # and notched at the bare array's ends. Heterodyne + wrap
    # fixes both; see the ruler's docstring. What it CANNOT fix
    # is an exact 0 c coincidence — that is the scoping job of
    # the harmonic-table audit below.
    return ruler.line_env(dm, hz(m), width_c=25.0, wrap=True)


def seg_med(e, a, b):
    return float(np.median(e[int(a * SR):int(b * SR)]))


# 1. entrances: the written sin^2 edge crosses -20 dB (re its
# own steady level) at an ANALYTIC time — measure that crossing
t_cross_off = EDGE * (2.0 / np.pi) * np.arcsin(np.sqrt(0.1))
worst_e = 0.0
order_ok = True
det = []
for ci, (nm, ch) in enumerate(PROG):
    prev = PROG[(ci - 1) % 4][1]
    new = sorted(m for m in ch if m not in prev)
    marks = []
    for m in new:
        t_on = ENTR[(m, ci)]
        e = line_env(m)
        ref = seg_med(e, t_on + 0.8,
                min(t_on + 3.0, (ci + 1) * CHORD_S - 0.5))
        i0 = max(0, int((t_on - 0.30) * SR))
        i1 = int((t_on + 0.60) * SR)
        idx = np.argmax(e[i0:i1] >= 0.1 * ref)
        t_me = (i0 + idx) / SR
        t_de = t_on + t_cross_off
        worst_e = max(worst_e, abs(t_me - t_de) * 1000.0)
        marks.append(t_me)
        det.append(f"{m}@{t_de:.2f}->{t_me:.2f}")
    order_ok = order_ok and all(
            marks[i] < marks[i + 1] for i in range(len(marks) - 1))
check("entrances", worst_e <= 35.0 and order_ok,
        f"6 pipes, worst |measured-design| {worst_e:.1f} ms, "
        f"order kept: {order_ok}")

# 2. held pipes do not dip at chord changes — SCOPED to
# line/boundary pairs with no EXACT harmonic coincidence: the
# pollution audit must cover every CLAIMED line, not just the
# entrants'. Three exact octaves hide in the progression:
# A4 h2 IS the A5 drone (880.0 Hz), E5 h2 IS the E6 drone
# (1318.5 Hz), and D5 h2 IS the D6 drone (1174.66 Hz) — 0 c
# offsets no filter can reject. So A5 is claimed only where A4
# is not sounding, D6 only where D5 is not (bo = [6,12) is out:
# its h2 beats the D6 drones at the +-2 c pipe detunes, ~0.8 s
# period, faking a -5 dB "dip" at the departure boundary), and
# E6 never. B5 and F#6 have no octave-mate anywhere: claimed
# at every boundary they hold across.
worst_h = 99.0
for m, bounds in [(83, (0.0, 6.0, 12.0, 18.0)),
                  (86, (0.0, 18.0)),
                  (81, (12.0, 18.0)),
                  (90, (12.0,))]:
    e = line_env(m)
    for b in bounds:
        w0, w1 = (b - 0.4) % LOOP_S, b + 0.4
        seg = np.concatenate([e[int(w0 * SR):]
                if w0 > w1 else np.array([]),
                e[0 if w0 > w1 else int(w0 * SR):
                  int(w1 * SR)]])
        ref = seg_med(e, (b + 1.0) % LOOP_S,
                (b + 2.2) % LOOP_S) \
            if (b + 2.2) <= LOOP_S else seg_med(e, 1.0, 2.2)
        dip = 20.0 * np.log10(seg.min() / (ref + 1e-30))
        worst_h = min(worst_h, dip)
check("holds", worst_h >= -3.0,
        f"9 clean boundary crossings, worst dip "
        f"{worst_h:+.1f} dB")

# 3. departing pipes actually leave: line level 0.9 s after the
# boundary sits >= 18 dB under the held level
worst_d = 99.0
for m, c0, c1 in SEGS:
    e = line_env(m)
    b = (c1 * CHORD_S) % LOOP_S
    held = seg_med(e, ENTR[(m, c0)] + 0.8,
            ENTR[(m, c0)] + 2.5)
    after = seg_med(e, (b + 0.9) % LOOP_S, (b + 1.6) % LOOP_S) \
        if (b + 1.6) <= LOOP_S else seg_med(e, 0.9, 1.6)
    fall = 20.0 * np.log10(held / (after + 1e-30))
    worst_d = min(worst_d, fall)
check("departures", worst_d >= 18.0,
        f"6 departures, worst fall {worst_d:.1f} dB")

# 4. membership (e85's ruler): mid-chord, every member's line
# stands and the probe classes (C5, Eb5) sit >= 12 dB under the
# weakest member
worst_gap = 99.0
for ci, (nm, ch) in enumerate(PROG):
    a = ci * CHORD_S + 1.5
    seg = dm[int(a * SR):int((a + 4.0) * SR)]
    S = np.abs(np.fft.rfft(seg * np.hanning(len(seg))))
    fq = np.fft.rfftfreq(len(seg), 1.0 / SR)

    def line_db(m):
        f = hz(m)
        sel = (fq > f * 2 ** (-25 / 1200)) \
            & (fq < f * 2 ** (25 / 1200))
        return 20.0 * np.log10(S[sel].max() + 1e-30)

    weakest = min(line_db(m) for m in ch)
    probes = max(line_db(m) for m in (72, 75))
    worst_gap = min(worst_gap, weakest - probes)
check("membership", worst_gap >= 12.0,
        f"4 chords, weakest member sits {worst_gap:.1f} dB "
        f"over the loudest probe")

# 5. the loop closes (ju_so -> kotsu rolls across the seam)
check("seam", ruler.seam_rank(mix) <= 0.999,
        f"p{100 * ruler.seam_rank(mix):.2f}")

ruler.report(mix, "e93_teutsuri")
print(f"\n{'ALL PASS' if not fails else 'FAILS: ' + str(fails)}")
sys.exit(1 if fails else 0)

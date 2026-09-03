#!/usr/bin/env python3
"""loam e95 — gagaku: the dragon flute over the moving sho.

The capstone assembly the way e91 was for sankyoku: three
families loam already owns, played together as a court
ensemble and each measured ON ITS OWN BUS (the practice since
e91 — cross-family pollution never gets a vote):

  - the SHO plays e93's te-utsuri (kotsu -> bo -> otsu ->
    ju_so, common tones droning, entrances rolling lowest-
    first at written times — the analytic sin^2 crossing);
  - the RYUTEKI (e86) carries a written eight-breath melody
    above it, with the flute's own gestures as claims: every
    center inside e82's 20 c wind gate, one written REGISTER
    FLIP (D5 -> D6 mid-breath, an octave the ruler reads as
    1200 c), and grace flicks that notch the envelope;
  - the GAGAKU PERCUSSION (e87) keeps the cycle: shoko at
    chord starts, kakko taps accelerating into the seam,
    one taiko DOU at the loop's center.

    python3 experiments/e95_gagaku.py [outdir]
"""

import os
import sys

import numpy as np
from scipy.signal import butter, sosfilt

sys.path.insert(0, os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))))
from loam import SR, hz, stereo, write_wav
from loam import ruler
from loam.nihon import sho, ryuteki, shoko, kakko, taiko
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


LOOP_S = 24.0
N = int(LOOP_S * SR)
CHORD_S = 6.0
EDGE = 0.30
STAG = 0.15

# ---- sho: e93's te-utsuri, verbatim ------------------------------
PROG = [("kotsu", [69, 76, 81, 83, 86, 88]),
        ("bo", [74, 81, 83, 86, 88, 90]),
        ("otsu", [76, 81, 83, 86, 88, 90]),
        ("ju_so", [79, 81, 83, 86, 88])]
DRONES = [81, 83, 86, 88]
SEGS = [(69, 0, 1), (76, 0, 1), (74, 1, 2), (90, 1, 3),
        (76, 2, 3), (79, 3, 4)]
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


sho_bus = np.zeros((N, 2))
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
        add_wrap(sho_bus, t0, v * (0.055 * g)[:, None])
for m, c0, c1 in SEGS:
    t_on = ENTR[(m, c0)]
    v = sho([m], c1 * CHORD_S + 0.30 - t_on, floor=1.0,
            edge_s=EDGE, seed=300 + m + 17 * c0)
    add_wrap(sho_bus, t_on, (v / rms(v)) * 0.075)

# ---- ryuteki: eight written breaths ------------------------------
# (midi, t_on, dur, flip_at rel, graces rel) — one chord tone or
# neighbor per breath, hyojo color, ma between breaths
FUE = [(76, 0.30, 2.85, -1.0, ()),
       (81, 3.35, 2.75, -1.0, (1.40,)),
       (78, 6.30, 2.85, -1.0, ()),
       (74, 9.30, 2.85, 1.50, ()),
       (76, 12.30, 2.85, -1.0, (0.90, 1.70)),
       (83, 15.35, 2.75, -1.0, ()),
       (79, 18.30, 2.85, -1.0, ()),
       (81, 21.30, 2.55, -1.0, (1.20,))]

fue_bus = np.zeros((N, 2))
for i, (m, t_on, dur, flip, gr) in enumerate(FUE):
    v = ryuteki(hz(m), dur, flip_at=flip, graces=gr,
            seed=500 + i)
    add_wrap(fue_bus, t_on, stereo(v, 0.15) * 0.16)

# ---- percussion: the written cycle -------------------------------
SHOKO_T = [0.0, 6.0, 12.0, 18.0]
KAKKO_T = [3.0, 4.5, 9.0, 10.5, 15.0, 16.5,
           21.0, 21.9, 22.65, 23.25]        # roll into the seam
TAIKO_T = [12.0]

gbus = np.zeros((N, 2))
kbus = np.zeros((N, 2))
dbus = np.zeros((N, 2))
for t in SHOKO_T:
    add_wrap(gbus, t, stereo(shoko(), -0.20) * 0.30)
for t in KAKKO_T:
    add_wrap(kbus, t, stereo(kakko(), -0.35) * 0.22)
for t in TAIKO_T:
    add_wrap(dbus, t, stereo(taiko(), 0.0) * 0.60)
perc_bus = gbus + kbus + dbus

dry = sho_bus + fue_bus + perc_bus
mix = 0.82 * dry + 0.26 * reverb_loop(dry, t60=2.0, size=1.2)
mix *= 0.92 / (np.abs(mix).max() + 1e-12)
write_wav(os.path.join(outdir, "e95_gagaku.wav"), mix)

# ---- rulers (each family on its own bus) -------------------------
print("e95 rulers:")

sm = sho_bus.mean(axis=1)
fm = fue_bus.mean(axis=1)
pm = perc_bus.mean(axis=1)

# 1. sho entrances: e93's analytic sin^2 crossing, own bus
t_cross_off = EDGE * (2.0 / np.pi) * np.arcsin(np.sqrt(0.1))
worst_e = 0.0
order_ok = True
for ci, (nm, ch) in enumerate(PROG):
    prev = PROG[(ci - 1) % 4][1]
    new = sorted(m for m in ch if m not in prev)
    marks = []
    for m in new:
        t_on = ENTR[(m, ci)]
        e = ruler.line_env(sm, hz(m), width_c=25.0, wrap=True)
        ref = float(np.median(e[int((t_on + 0.8) * SR):
                int(min(t_on + 3.0,
                        (ci + 1) * CHORD_S - 0.5) * SR)]))
        i0 = max(0, int((t_on - 0.30) * SR))
        idx = np.argmax(e[i0:int((t_on + 0.60) * SR)]
                >= 0.1 * ref)
        t_me = (i0 + idx) / SR
        worst_e = max(worst_e, abs(t_me - (t_on + t_cross_off))
                * 1000.0)
        marks.append(t_me)
    order_ok = order_ok and all(
            marks[i] < marks[i + 1] for i in range(len(marks) - 1))
check("sho_entrances", worst_e <= 35.0 and order_ok,
        f"6 pipes, worst |measured-design| {worst_e:.1f} ms, "
        f"order kept: {order_ok}")

# 2. ryuteki centers: every held span inside e82's 20 c wind
# gate (flipped breath measured per register)
worst_c = 0.0
spans = []
for m, t_on, dur, flip, gr in FUE:
    if flip > 0.0:
        spans.append((hz(m), t_on + 0.40, t_on + flip - 0.25))
        spans.append((2.0 * hz(m), t_on + flip + 0.35,
                t_on + dur - 0.35))
    else:
        spans.append((hz(m), t_on + 0.50, t_on + dur - 0.40))
cents = []
for f0, a, b in spans:
    tr = ruler.if_pitch(fm[int(a * SR):int(b * SR)], f0)
    c = 1200.0 * np.log2(float(np.median(tr)) / f0)
    cents.append(c)
    worst_c = max(worst_c, abs(c))
check("fue_centers", worst_c <= 20.0,
        f"{len(spans)} held spans, worst center "
        f"{worst_c:.1f} c (gate 20, e82's wind gate)")

# 3. the register flip is an octave: post - pre center = 1200 c
flip_i = [i for i, (m, t, d, fl, g) in enumerate(FUE)
        if fl > 0.0][0]
m, t_on, dur, flip, gr = FUE[flip_i]
pre = cents[[j for j, (f0, a, b) in enumerate(spans)
        if abs(f0 - hz(m)) < 1e-6][0]]
post = cents[[j for j, (f0, a, b) in enumerate(spans)
        if abs(f0 - 2.0 * hz(m)) < 1e-6][0]]
d_oct = 1200.0 + post - pre
check("fue_flip", abs(d_oct - 1200.0) <= 25.0,
        f"D5 -> D6 measures {d_oct:.1f} c (written 1200)")

# 4. grace flicks notch the envelope at their written times
env = np.abs(fm)
kg = int(0.008 * SR)
env = np.convolve(env, np.ones(kg) / kg, mode="same")
worst_g = 99.0
n_gr = 0
for m, t_on, dur, flip, gr in FUE:
    for g in gr:
        tg = t_on + g
        i0, i1 = int((tg - 0.06) * SR), int((tg + 0.06) * SR)
        j0, j1 = int((tg - 0.30) * SR), int((tg + 0.30) * SR)
        around = np.concatenate([env[j0:i0], env[i1:j1]])
        notch = 20.0 * np.log10(env[i0:i1].min()
                / (np.median(around) + 1e-30))
        worst_g = min(worst_g, -notch)
        n_gr += 1
check("fue_graces", worst_g >= 3.0,
        f"{n_gr} flicks, weakest notch {worst_g:.1f} dB")

# 5. percussion marks: e87's ruler verbatim — spectral flux on
# the doubled OWN bus per voice, per-voice gates (the taiko's
# membrane blooms ~35 ms by physics, so the big drum keeps
# e87's 30 ms gate; amplitude-diff flux read that bloom as a
# 38.6 ms miss before this switch)
def marks(bus, times, sos, win=0.2):
    m = sosfilt(sos, np.concatenate([bus.mean(axis=1),
            bus.mean(axis=1)]))
    fx, dt = ruler.flux_series(m, frame=512, hop=128)
    tf = np.arange(len(fx)) * dt
    offs = []
    for t in times:
        c = (t % LOOP_S) + LOOP_S
        sel = (tf >= c - win) & (tf <= c + win)
        offs.append(tf[sel][np.argmax(fx[sel])] - c)
    return offs


sos_hi = butter(4, 2500.0, btype="highpass", fs=SR, output="sos")
sos_lo = butter(4, 200.0, btype="lowpass", fs=SR, output="sos")
sos_md = butter(4, [350.0, 1500.0], btype="bandpass", fs=SR,
        output="sos")
o_g = marks(gbus, SHOKO_T, sos_hi, 0.025)
o_d = marks(dbus, TAIKO_T, sos_lo, 0.030)
o_k = marks(kbus, KAKKO_T, sos_md, 0.025)
worst_p = 1000.0 * max(max(np.abs(o_g)), max(np.abs(o_d)),
        max(np.abs(o_k)))
check("perc_marks", max(np.abs(o_g)) <= 0.025
        and max(np.abs(o_d)) <= 0.030
        and max(np.abs(o_k)) <= 0.025,
        f"{len(SHOKO_T) + len(KAKKO_T) + len(TAIKO_T)} strokes "
        f"in 3 voices, worst |mark - written| {worst_p:.1f} ms")

# 6. the loop closes (the kakko roll lands across the seam)
check("seam", ruler.seam_rank(mix) <= 0.999,
        f"p{100 * ruler.seam_rank(mix):.2f}")

ruler.report(mix, "e95_gagaku")
print(f"\n{'ALL PASS' if not fails else 'FAILS: ' + str(fails)}")
sys.exit(1 if fails else 0)

#!/usr/bin/env python3
"""loam e87 — ETENRAKU: the full ensemble. The capstone.

Three cycles built three views of the same phrase; this one
plays them together, the gagaku way:

  - hichiriki (e84): the melody, embai glides and all;
  - sho (e85): the aitake halo, one breath per chord, the
    aitake being the melody note's own chord;
  - ryuteki (e86): the same phrase an octave up, the long E's
    flipping fukura -> seme mid-breath;
  - NEW — the time-keepers: kakko (tight 'ka', katarai taps
    and the mororai accelerating roll into each big beat),
    shoko (bronze 'chin' every other beat), taiko (the soft
    zun / big DOU at the head of each 8-beat cycle).

Haya yo-hyoshi at 1.6 s/beat, 24 beats, 38.4 s loop. The
percussion pattern is gagaku-style simplified (the exact
Etenraku drum score is figure-locked, like the aitake charts).

    python3 experiments/e87_etenraku.py [outdir]
"""

import os
import sys

import numpy as np
from scipy.signal import butter, sosfilt

sys.path.insert(0, os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))))
from loam import SR, hz, stereo, write_wav
from loam import ruler
from loam.nihon import (hichiriki, sho, ryuteki, AITAKE,
        shoko, kakko, taiko)
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
T0 = 0.2


def bt(b):
    return T0 + b * BEAT


def add_wrap(bus, t, ss):
    i0 = int(round(t * SR)) % N
    n = len(ss)
    if ss.ndim == 1:
        ss = ss[:, None] * np.ones((1, bus.shape[1]))
    if i0 + n <= N:
        bus[i0:i0 + n] += ss
    else:
        k = N - i0
        bus[i0:] += ss[:k]
        bus[:n - k] += ss[k:]


# ---- hichiriki: e84's melody ------------------------------------
H_MELODY = [
    (74, 1, 140.0, 0.0), (76, 2, 30.0, 0.0), (76, 2, 25.0, 0.0),
    (71, 2, 120.0, 0.0), (71, 2, 25.0, 0.0), (69, 2, 100.0, 0.0),
    (71, 2, 30.0, 0.0), (76, 2, 120.0, 0.0), (76, 1, 25.0, 0.0),
    (76, 1, 25.0, 0.0), (74, 2, 40.0, 0.0), (76, 3, 30.0, 18.0),
]
hbus = np.zeros((N, 2))
H_NOTES, H_DURS = [], []
b = 0
for i, (m, beats, em, yc) in enumerate(H_MELODY):
    dur = beats * BEAT - 0.12
    v = hichiriki(hz(m), dur, embai=em, yuri_c=yc, seed=m + 3 * i)
    H_NOTES.append(v)
    H_DURS.append(dur)
    add_wrap(hbus, bt(b), stereo(v, -0.08))
    b += beats

# ---- sho: e85's halo --------------------------------------------
PROG = [
    ("bo", 1), ("otsu", 4), ("ichi", 4), ("kotsu", 2),
    ("ichi", 2), ("otsu", 4), ("bo", 2), ("otsu", 5),
]
OVER = 0.35
sbus = np.zeros((N, 2))
b = 0
S_BOUNDS = []
for i, (name, beats) in enumerate(PROG):
    v = sho(AITAKE[name], beats * BEAT + OVER, edge_s=OVER,
            seed=17 + 5 * i)
    add_wrap(sbus, bt(b) - OVER / 2, v)
    b += beats
    S_BOUNDS.append(bt(b) % LOOP_S)

# ---- ryuteki: e86's dragon line ---------------------------------
R_MELODY = [
    (86, 1, -1.0, ()), (76, 2, 0.9, ()), (88, 2, -1.0, ()),
    (83, 2, -1.0, (0.25,)), (83, 2, -1.0, ()),
    (81, 2, -1.0, (0.30,)), (83, 2, -1.0, ()),
    (76, 2, 0.8, ()), (88, 1, -1.0, ()), (88, 1, -1.0, (0.45,)),
    (86, 2, -1.0, (0.35,)), (76, 3, 1.1, ()),
]
rbus = np.zeros((N, 2))
R_NOTES, R_DURS = [], []
b = 0
for i, (m, beats, fl, gr) in enumerate(R_MELODY):
    dur = beats * BEAT - 0.15
    v = ryuteki(hz(m), dur, flip_at=fl, graces=gr, seed=41 + 7 * i)
    R_NOTES.append(v)
    R_DURS.append(dur)
    add_wrap(rbus, bt(b), stereo(v, 0.18))
    b += beats

# ---- the time-keepers -------------------------------------------
kbus = np.zeros((N, 2))
gbus = np.zeros((N, 2))          # shoko (gong)
dbus = np.zeros((N, 2))          # taiko
SHOKO_T, TAIKO_T = [], []
for b in range(0, 24, 2):
    t = bt(b) % LOOP_S
    add_wrap(gbus, t, stereo(shoko(0.9), 0.30))
    SHOKO_T.append(t)
for b in (0, 8, 16):
    t = bt(b) % LOOP_S
    add_wrap(dbus, t - 0.45, stereo(taiko(1.0, small=True), 0.0))
    add_wrap(dbus, t, stereo(taiko(1.0), 0.0))
    TAIKO_T.append(t)
# katarai: single taps answering the shoko
KAKKO_TAPS = [bt(b) % LOOP_S for b in (3, 5, 11, 13, 19, 21)]
for t in KAKKO_TAPS:
    add_wrap(kbus, t, stereo(kakko(0.8), -0.30))
# mororai: the accelerating roll into each cycle head
ROLLS = []
for target_b in (8, 16, 24):
    target = bt(target_b)
    taps, g, tt = [], 0.075, target
    while g <= 0.30:
        tt -= g
        taps.append(tt)
        g /= 0.82
    taps = taps[::-1]
    for j, t in enumerate(taps):
        a = 0.35 + 0.55 * j / (len(taps) - 1)
        add_wrap(kbus, t % LOOP_S, stereo(kakko(a), -0.30))
    # keep UNWRAPPED times: IOI math needs monotonic time (the
    # third roll crosses the seam, and a %-wrapped list read one
    # interval as -38.3 s); marks() wraps for the lookup itself
    ROLLS.append(list(taps))

# ---- mix ---------------------------------------------------------
dry = (0.80 * hbus + 0.26 * sbus + 0.40 * rbus
       + 0.38 * gbus + 0.50 * kbus + 0.85 * dbus)
wet = reverb_loop(dry, t60=2.2, size=1.3)
mix = 0.82 * dry + 0.30 * wet
mix *= 0.92 / (np.abs(mix).max() + 1e-12)
write_wav(os.path.join(outdir, "e87_etenraku.wav"), mix)

# ---- rulers ------------------------------------------------------
print("e87 rulers:")

# 1. seam
check("seam", ruler.seam_rank(mix) <= 0.999,
        f"p{100 * ruler.seam_rank(mix):.2f}")


def marks(bus, times, sos, win=0.2):
    """Per-written-time flux argmax on the doubled own bus. `win`
    must stay under half the smallest written gap — a wide window
    lets neighboring marks lock onto one loud event (the mororai
    read zero IOIs through a +-0.2 s window before this was a
    parameter)."""
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

# 2. the time-keepers keep time
o_g = marks(gbus, SHOKO_T, sos_hi, 0.025)
o_d = marks(dbus, TAIKO_T, sos_lo, 0.030)
o_k = marks(kbus, KAKKO_TAPS, sos_md, 0.025)
worst = max(max(np.abs(o_g)), max(np.abs(o_d)), max(np.abs(o_k)))
check("perc_marks", max(np.abs(o_g)) <= 0.025
        and max(np.abs(o_d)) <= 0.030
        and max(np.abs(o_k)) <= 0.025,
        f"12 shoko + 3 DOU + 6 katarai, worst "
        f"{1000 * worst:.1f} ms")

# 3. the mororai accelerates: every tap marks, and the MEASURED
# intervals shrink monotonically into the beat
roll_ok, ratios = True, []
for taps in ROLLS:
    offs = marks(kbus, taps, sos_md, win=0.035)
    tm = np.array(taps) + np.array(offs)
    ioi = np.diff(tm)
    roll_ok = roll_ok and max(np.abs(offs)) <= 0.020 \
        and bool(np.all(np.diff(ioi) < 0.015)) \
        and ioi[-1] / ioi[0] <= 0.45
    ratios.append(ioi[-1] / ioi[0])
check("mororai", roll_ok,
        f"3 rolls x {len(ROLLS[0])} taps, final/first IOI "
        f"{min(ratios):.2f}-{max(ratios):.2f} (accelerando)")

# 4. hichiriki holds the melody (e84's gate, re-measured here)
worst = 0.0
for v, (m, beats, em, yc), dur in zip(H_NOTES, H_MELODY, H_DURS):
    inst = ruler.if_pitch(v, hz(m))
    s0 = max(0.5, dur - 0.6)
    c = 1200.0 * np.log2(np.median(
            inst[int(s0 * SR):int((dur - 0.15) * SR)]) / hz(m))
    worst = max(worst, abs(c))
check("melody", worst <= 20.0,
        f"12 hichiriki notes, worst late center {worst:.1f} c")

# 5. ryuteki flips hold both registers (e86's gate)
w_lo, w_hi = 0.0, 0.0
for v, (m, beats, fl, gr), dur in zip(R_NOTES, R_MELODY, R_DURS):
    if fl <= 0.0:
        continue
    f0 = hz(m)
    c_lo = 1200.0 * np.log2(np.median(ruler.if_pitch(v, f0)[
            int(0.25 * SR):int((fl - 0.15) * SR)]) / f0)
    c_hi = 1200.0 * np.log2(np.median(ruler.if_pitch(v, 2 * f0)[
            int((fl + 0.15) * SR):int((dur - 0.2) * SR)])
            / (2 * f0))
    w_lo = max(w_lo, abs(c_lo))
    w_hi = max(w_hi, abs(c_hi))
check("dragon_flips", w_lo <= 30.0 and w_hi <= 30.0,
        f"4 flips: fukura {w_lo:.1f} c, seme {w_hi:.1f} c")

# 6. the sho's breath turns at every chord change (e85's gate)
fr = int(0.05 * SR)
sm = sbus.mean(axis=1)
env = np.sqrt(np.mean(sm[:len(sm) // fr * fr].reshape(-1, fr) ** 2,
        axis=1))
env = np.convolve(env, np.ones(9) / 9, mode="same")
te = np.arange(len(env)) * fr / SR
w_off = 0.0
for tb in S_BOUNDS:
    sel = (te >= tb - 0.9) & (te <= tb + 0.9)
    if not sel.any():
        continue
    w_off = max(w_off, abs(te[sel][np.argmin(env[sel])] - tb))
check("halo_breathes", w_off <= 0.35,
        f"8 changes, worst trough offset {w_off:.2f} s")

# 7. everyone in their register: the ensemble layers
c_d = ruler.centroid_hz(dbus.mean(axis=1))
c_k = ruler.centroid_hz(kbus.mean(axis=1))
c_g = ruler.centroid_hz(gbus.mean(axis=1))
check("layers", c_d < 300.0 and 300.0 < c_k < 1500.0
        and c_g > 1400.0,
        f"taiko {c_d:.0f} / kakko {c_k:.0f} / shoko {c_g:.0f} Hz")

# 8. hyojo rests on E, B beneath
ch = ruler.chroma(mix)
top2 = set(np.argsort(ch)[-2:].tolist())
check("chroma_poles", top2 == {4, 11},
        f"top-2 classes {sorted(top2)} (want E=4, B=11); "
        f"E {ch[4]:.2f} B {ch[11]:.2f}")

ruler.report(mix, "e87_etenraku")
print(f"\n{'ALL PASS' if not fails else 'FAILS: ' + str(fails)}")
sys.exit(1 if fails else 0)

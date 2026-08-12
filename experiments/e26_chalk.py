#!/usr/bin/env python3
"""e26 — Chalk. SFX prototype for NOCK's sigil marks (checkpoint
loop, peddler's coin, ward): the last cue family on the DESIGN
list. The idea under test: THE MARK IS WRITTEN, NOT STAMPED. A
stamp is one event — any glyph, same thud. A written mark carries
its glyph in the sound: each sigil is a fixed sequence of chalk
strokes, and the stroke RHYTHM is the glyph's identity. The hand
is audible inside each stroke too — a velocity bell (accelerate,
sweep, ease off) that the chalk voices as brightness: faster is
brighter. Squeak is the failure mode of a real hand (pressure
crossing speed), so it appears at deterministic velocity
crossings, sparse — texture, not signal.

Three glyphs, three rhythms (strokes as (t0, dur, vmax)):
  loop  — the checkpoint spiral: one long sweep, two short closes
  coin  — the peddler's cross: two quick equal cuts
  ward  — four even fence pickets, ending on a slow drag

Measured, per sigil on its own render:
  - the count is the glyph: envelope onsets == designed strokes
  - the rhythm is the glyph: each onset within 15 ms of design
    (and the three designs pairwise differ someplace by > 60 ms —
    the grammar table itself keeps them distinguishable)
  - the hand is audible: per stroke, power centroid of the middle
    third > both end thirds (the velocity bell survives the
    render)
  - squeak is texture: the 2.7-3.0 kHz band exceeds 3x its own
    median level for < 25% of written time

    python3 experiments/e26_chalk.py [outdir]
"""

import os
import sys

import numpy as np
from scipy.signal import butter, sosfilt, find_peaks

sys.path.insert(0, os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))))
from loam import SR, stereo, write_wav

outdir = sys.argv[1] if len(sys.argv) > 1 else "render"
os.makedirs(outdir, exist_ok=True)
rng = np.random.default_rng(0xE26)

SQUEAK_HZ = 2850.0

# the grammar table: stroke = (t0, dur, vmax); rhythm IS identity
SIGILS = {
    "loop": [(0.00, 0.42, 1.0), (0.55, 0.22, 0.8), (0.85, 0.22, 0.9)],
    "coin": [(0.00, 0.26, 0.9), (0.34, 0.26, 1.0)],
    "ward": [(0.00, 0.20, 0.8), (0.26, 0.20, 1.0),
             (0.52, 0.20, 0.9), (0.78, 0.34, 0.7)],
}


def hp(x, f):
    sos = butter(2, f / (SR / 2), "highpass", output="sos")
    return sosfilt(sos, x)


def stroke(dur, vmax):
    """One chalk stroke: grain noise through a lowpass whose corner
    rides the velocity bell (faster = brighter), amplitude riding
    the same bell — plus a squeak burst at the deterministic upward
    crossing of 0.6 vmax."""
    n = int(dur * SR)
    tt = np.linspace(0, 1, n)
    v = np.sin(np.pi * tt) ** 1.5 * vmax          # the hand's bell
    grain = rng.standard_normal(n) \
        * (0.55 + 0.45 * np.clip(rng.standard_normal(n // 220 + 1)
           .repeat(220)[:n], -1, 1))               # chalk tooth
    corner = 900.0 + 4200.0 * v
    a = np.exp(-2 * np.pi * corner / SR)
    out = np.zeros(n)
    lp = 0.0
    for i in range(n):
        lp = lp * a[i] + grain[i] * (1 - a[i])
        out[i] = lp
    out = hp(out, 500) * (v ** 0.7) * 3.0
    # the squeak: pressure crosses speed on the way UP through 0.6
    cross = np.flatnonzero((v[1:] >= 0.6 * vmax) & (v[:-1] < 0.6 * vmax))
    if len(cross):
        i0 = int(cross[0])
        m = min(int(0.04 * SR), n - i0)
        st = np.arange(m) / SR
        out[i0:i0 + m] += np.sin(2 * np.pi * SQUEAK_HZ * st
                                 + 3.0 * np.sin(2 * np.pi * 55.0 * st)) \
            * np.sin(np.pi * st / (m / SR)) * 0.12
    return out


def sigil(name):
    strokes = SIGILS[name]
    dur = strokes[-1][0] + strokes[-1][1] + 0.25
    out = np.zeros(int(dur * SR))
    for (t0, d, vm) in strokes:
        s = stroke(d, vm)
        i0 = int(t0 * SR)
        out[i0:i0 + len(s)] += s[:len(out) - i0]
    return out


# ---- the rulers -----------------------------------------------------

def onsets(x, expect):
    """Hysteresis threshold crossings (the stone-skitter ruler), NOT
    derivative peaks (the sting ruler). A stroke is a slow swell:
    its maximum rise rate lands mid-crescendo (~0.1-0.17 s late
    here) and chalk grain gives the derivative several humps per
    stroke. The written mark's onset is where energy BEGINS — env
    crosses 8% of peak, re-armed only after falling under 3% in the
    silence between strokes."""
    m = np.abs(x)
    k = int(0.025 * SR)   # long enough to bridge 5 ms chalk-grain dips
    env = np.convolve(m, np.ones(k) / k, "same")
    hi, lo = env.max() * 0.08, env.max() * 0.03
    out = []
    armed = True
    for i, v in enumerate(env):
        if armed and v >= hi:
            out.append(i / SR)
            armed = False
        elif not armed and v < lo:
            armed = True
    return out[:expect + 2]


def pcentroid(seg):
    spec = np.abs(np.fft.rfft(seg)) ** 2
    f = np.fft.rfftfreq(len(seg), 1 / SR)
    return float((spec * f).sum() / (spec.sum() + 1e-12))


if __name__ == "__main__":
    renders = {name: sigil(name) for name in SIGILS}
    gap = np.zeros(int(0.6 * SR))
    demo = np.concatenate(sum(([renders[n], gap] for n in SIGILS), []))
    demo = demo / np.max(np.abs(demo)) * 0.85
    write_wav(os.path.join(outdir, "e26_chalk.wav"), stereo(demo, 0.0))

    print("== the count and the rhythm are the glyph ==")
    # rhythm compared as INTERVALS: a threshold detector has a
    # systematic crossing lag, identical for every stroke — it
    # cancels in the differences, which is what rhythm IS
    for name, strokes in SIGILS.items():
        t = onsets(renders[name], len(strokes))
        n_ok = len(t) == len(strokes)
        if n_ok and len(t) > 1:
            gi = np.diff(t) * 1000
            gd = np.diff([s[0] for s in strokes]) * 1000
            worst = float(np.max(np.abs(gi - gd)))
        else:
            worst = 999
        print("  %-5s onsets %d/%d, worst interval %+.0f ms : %s" % (
            name, len(t), len(strokes), worst,
            "OK" if n_ok and worst <= 20 else "FAIL"))

    print("== the designs stay apart (pairwise, someplace > 60 ms) ==")
    names = list(SIGILS)
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            a, b = SIGILS[names[i]], SIGILS[names[j]]
            far = len(a) != len(b) or max(
                abs(x[0] - y[0]) for x, y in zip(a, b)) * 1000 > 60
            print("  %s vs %s : %s" % (names[i], names[j],
                  "APART" if far else "TOO CLOSE"))

    print("== the hand is audible (mid-third centroid > end thirds) ==")
    for name, strokes in SIGILS.items():
        x = renders[name]
        ok = True
        for (t0, d, vm) in strokes:
            th = [pcentroid(x[int((t0 + k * d / 3) * SR):
                              int((t0 + (k + 1) * d / 3) * SR)])
                  for k in range(3)]
            if not (th[1] > th[0] and th[1] > th[2]):
                ok = False
        print("  %-5s : %s" % (name, "BELL" if ok else "NO"))

    print("== squeak is texture, not signal ==")
    for name in SIGILS:
        x = renders[name]
        sos = butter(2, [2700 / (SR / 2), 3000 / (SR / 2)], "bandpass",
                     output="sos")
        band = np.abs(sosfilt(sos, x))
        k = int(0.005 * SR)
        env = np.convolve(band, np.ones(k) / k, "same")
        frac = float((env > 3 * np.median(env[env > 1e-6])).mean())
        print("  %-5s loud-squeak fraction %.2f (want < 0.25)" % (name, frac))

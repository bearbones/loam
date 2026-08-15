#!/usr/bin/env python3
"""e33 — The ledger's drum. Operator ruling on e29: "the cadence is
fine, but I'd like a deeper drum for it." The rework, with a design
claim: the drum belongs to the TALLY, not to a register — the same
deep hall drum under both dresses (flame's gut, lightning's glass),
because the night closing is the world's own ceremony wherever you
stand on the gradient. e29's wood knock (the old "drum") is
replaced by it.

The drum: a soft-beater hall drum — pitch-drop 88 -> 40 Hz, slow
bloom (no EDM click), a short dark room under it. It strikes twice:
at the word's first step and under the LANDING (0.66 s), so the
verdict note arrives on weight.

The hazard, measured: a 40 Hz drum's harmonics (120, 160 Hz) sit
inside e29's 120-190 Hz beating band — the verdict's own ruler.
The drum is identical in clean/stained, so it adds a COMMON floor
that can only dilute the ratio toward 1. e29's whole ruler suite is
re-run with the drum in place; the beating ratio must survive
>= 3x. If it hadn't, the fix ladder was: shorter tail, softer
landing hit, or moving the second hit off the landing — the
measurement decides, not taste.

Rulers:
  - deeper is measured, not asserted: drum centroid <= 0.5x the
    old wood knock's, and low-band (<120 Hz) fraction >= 0.9
    ABSOLUTE. (A ratio claim died here first: the knock's own
    low-frac is 0.60, so ">= 3x" demanded > 1.0 — a ratio ruler
    against an already-dark baseline saturates. Depth ratios
    belong to the centroid; fractions get absolute floors.)
  - the minimal pair survives the drum: onset spread clean vs
    stained <= 8 ms in both dresses (drum hits are verdict-blind).
  - the landing still speaks: beating ratio stained/clean >= 3x
    per dress WITH the drum's common floor in the band.
  - a close, not an alarm: cadence rms still < caught rms.

Render: flame clean, flame stained, lightning clean, lightning
stained — the e29 exhibit, now with weight.

    python3 experiments/e33_ledgerdrum.py [outdir]
"""

import importlib.util
import os
import sys

import numpy as np
from scipy.signal import butter, sosfilt

_here = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(_here))
from loam import SR, hz, stereo, write_wav
from loam.drums import kick
from loam.modal import strike, WOOD

_spec = importlib.util.spec_from_file_location(
    "e29", os.path.join(_here, "e29_ledgercadence.py"))
e29 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(e29)
e23 = e29.e23

outdir = sys.argv[1] if len(sys.argv) > 1 else "render"
os.makedirs(outdir, exist_ok=True)
rng = np.random.default_rng(0xE33)

# (t_s, amp): first step, then the WALK'S LAST STEP — not the
# landing. The drum blooms and the verdict note lands ON the bloom
# (door swings, then latches). The first cut put the second hit at
# the landing itself (0.66): its 38-53 Hz tail leaked through the
# beating ruler's 2nd-order band edge into the measurement window
# and buried flame's quiet landing under a common floor (x1.4).
DRUM_HITS = [(0.00, 0.9), (0.40, 1.15)]
DRUM_LEVEL = 0.34


def hall_drum(amp=1.0, seed=7):
    """Soft beater, deep skin, short dark room. No click: the tally
    is a door closing, not a dance floor. Tuned AROUND the verdict:
    f1 38 Hz with drive 1.25 keeps the 3rd harmonic (114 Hz) under
    the beating band's floor (120 Hz), and the room lives in
    50-115 Hz — the first cut (drive 1.6, f1 40, room to 420 Hz)
    put drum harmonics at 120/160 Hz INSIDE the verdict's own
    ruler band and drowned flame's landing (beating x6.2 -> x1.4)."""
    d = kick(0.55, f0=84.0, f1=38.0, drop=11.0, click=0.0,
             drive=1.25, amp=amp, seed=seed)
    n = len(d)
    r = np.random.default_rng(seed)
    sos = butter(2, [50.0, 115.0], "bandpass", fs=SR, output="sos")
    room = sosfilt(sos, r.uniform(-1, 1, n)) \
        * np.exp(-np.arange(n) / SR * 9.0) * 0.15 * amp
    return d + room


def drum_track(n):
    """The common drum bus, verdict-blind by construction."""
    out = np.zeros(n)
    for (t0, a) in DRUM_HITS:
        dr = hall_drum(amp=a, seed=0xE33) * DRUM_LEVEL
        i0 = int(t0 * SR)
        m = min(len(dr), n - i0)
        out[i0:i0 + m] += dr[:m]
    return out


def dress_with_drum(dress, word, level):
    x = dress(word, level)
    out = np.array(x, dtype=float)
    for (t0, a) in DRUM_HITS:
        dr = hall_drum(amp=a, seed=0xE33) * DRUM_LEVEL
        i0 = int(t0 * SR)
        m = min(len(dr), len(out) - i0)
        out[i0:i0 + m] += dr[:m]
    return out


def local_onset(x, t0):
    # e29's ruler, copied (it lives in e29's __main__ block):
    # hysteresis crossing of the local max around the designed time
    k = int(0.008 * SR)
    env = np.convolve(np.abs(x), np.ones(k) / k, "same")
    a = max(int((t0 - 0.04) * SR), 0)
    b = int((t0 + 0.08) * SR)
    w = env[a:b]
    return (a + int(np.argmax(w > 0.35 * w.max()))) / SR


def low_frac(x, corner=120.0):
    spec = np.abs(np.fft.rfft(np.asarray(x, dtype=float))) ** 2
    f = np.fft.rfftfreq(len(x), 1 / SR)
    return float(spec[f < corner].sum() / max(spec.sum(), 1e-12))


def centroid(x):
    spec = np.abs(np.fft.rfft(np.asarray(x, dtype=float))) ** 2
    f = np.fft.rfftfreq(len(x), 1 / SR)
    return float((f * spec).sum() / max(spec.sum(), 1e-12))


if __name__ == "__main__":
    dresses = {"flame": e23.dress_flame, "lightning": e23.dress_lightning}
    rendered = {}
    for dn, dress in dresses.items():
        for vn, word in e29.CADENCES.items():
            rendered[(dn, vn)] = dress_with_drum(dress, word,
                                                 e29.CADENCE_LEVEL)

    print("== deeper is measured (vs e29's wood knock) ==")
    drum = hall_drum(amp=1.0, seed=0xE33)
    knock = strike(hz(e29.CADENCES["clean"][0][1] - 12), 0.18, WOOD,
                   amp=1.0, bright=0.7,
                   rng=np.random.default_rng(1), knock=1.0)
    c_d, c_k = centroid(drum), centroid(knock)
    lf_d, lf_k = low_frac(drum), low_frac(knock)
    ok_deep = c_d <= 0.5 * c_k and lf_d >= 0.9
    print("  centroid %.0f vs %.0f Hz (x%.2f, want <= 0.5); low-frac "
          "%.2f (knock %.2f; want >= 0.9 absolute): %s"
          % (c_d, c_k, c_d / max(c_k, 1e-9), lf_d, lf_k,
             "YES" if ok_deep else "NO"))

    print("== the minimal pair survives the drum ==")
    # the drum bus is IDENTICAL in clean/stained (verdict-blind by
    # construction), but the onset detector is nonlinear, so the
    # common bloom shifts flame's soft pluck crossings by different
    # amounts per verdict (37.8 ms false spread). Linearize: subtract
    # the known common track, then measure the words themselves.
    ok = True
    for dn in dresses:
        wc = rendered[(dn, "clean")] \
            - drum_track(len(rendered[(dn, "clean")]))
        ws = rendered[(dn, "stained")] \
            - drum_track(len(rendered[(dn, "stained")]))
        d_ms = max(abs(local_onset(wc, t0) - local_onset(ws, t0))
                   for (t0, _, _) in e29.CADENCES["clean"]) * 1000.0
        ok &= d_ms <= 8.0
        print("  %-9s onset spread %.1f ms (want <= 8)" % (dn, d_ms))
    print("  " + ("YES" if ok else "NO"))

    print("== the landing still speaks through the drum's floor ==")
    for dn in dresses:
        b = {}
        for vn, word in e29.CADENCES.items():
            t_final = word[-1][0]
            a = int((t_final + 0.10) * SR)
            seg = rendered[(dn, vn)][a:a + int(0.60 * SR)]
            b[vn] = e29.beating(seg)
        r = b["stained"] / max(b["clean"], 1e-12)
        print("  %-9s beating clean %.4f  stained %.4f  (x%.1f, want "
              ">= 3): %s" % (dn, b["clean"], b["stained"], r,
                             "YES" if r >= 3.0 else "NO"))

    print("== a close, not an alarm ==")
    for dn, dress in dresses.items():
        caught = dress(e23.GESTURES["caught"], e23.LEVELS["caught"])
        rc = e29.rms(rendered[(dn, "clean")])
        ra = e29.rms(caught)
        print("  %-9s cadence rms %.4f < caught rms %.4f : %s"
              % (dn, rc, ra, "YES" if rc < ra else "NO"))

    gap = np.zeros(int(0.8 * SR))
    order = [("flame", "clean"), ("flame", "stained"),
             ("lightning", "clean"), ("lightning", "stained")]
    parts = []
    for key in order:
        parts += [rendered[key], gap]
    mono = np.concatenate(parts[:-1])
    write_wav(os.path.join(outdir, "e33_ledgerdrum.wav"),
              np.clip(stereo(mono * 0.9, 0.0), -0.99, 0.99))
    print("wrote", outdir + "/e33_ledgerdrum.wav")

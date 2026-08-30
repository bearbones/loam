#!/usr/bin/env python3
"""e41 — the bridge that wouldn't buzz: a NEGATIVE RESULT, kept.

Goal was the tanpura's jawari in strings.pluck: one-sided bridge
contact whose signature is the BLOOM — high partials swelling
AFTER the attack. Four bridge models went into the KS loop; the
rulers below assert what each was MEASURED to do, so the negative
result is reproducible, not an anecdote:

- saturator (one-sided rational compression): a damper. Anything
  riding the fundamental's positive half-cycle sees the transfer
  curve's derivative gain < 1 — modulation loss beats harmonic
  generation.
- saturator + per-block RMS restitution: restores ENERGY (which
  the fundamental owns), not the high partials. Still a damper.
- moving contact (displacement-dependent delay, the honest
  physics): lossless in intent, but the swept fractional-delay
  interpolation smears highs — a subtler damper.
- hard obstacle (fixed clip height): barely engages — measures as
  uniform gain, not spectral change.

A synthetic bloom signal proves the bloom ruler ISN'T blind.
Conclusion for the log: delayed-HF-max bloom needs distributed
contact + string dispersion (van Walstijn's tanpura sims), not a
point nonlinearity in a KS loop. The library keeps its shipped
pluck; this file keeps the evidence. Render: the same A2 pluck
through all five bridges, in sequence (not a loop; no seam claim).

    python3 experiments/e41_bridgetrials.py [outdir]
"""

import os
import sys

import numpy as np
from scipy.signal import butter, sosfilt

sys.path.insert(0, os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))))
from loam import SR, hz, stereo, write_wav
from loam import ruler

outdir = sys.argv[1] if len(sys.argv) > 1 else "render"
os.makedirs(outdir, exist_ok=True)
fails = []


def check(name, cond, detail):
    print(f"  {'PASS' if cond else 'FAIL'} {name}: {detail}")
    if not cond:
        fails.append(name)


def ks(f0, dur, mode="dry", t60=12.0, damp=0.22, seed=5):
    """The pluck core with a pluggable bridge."""
    n = int(dur * SR)
    pf = SR / f0
    pi_ = int(pf)
    frac = pf - pi_
    rho = 10.0 ** (-3.0 * (pf / SR) / t60)
    rng = np.random.default_rng(seed)
    ex = rng.standard_normal(pi_ + 2)
    d = max(int(round(0.2 * pi_)), 1)
    ex = ex - np.concatenate([np.zeros(d), ex[:-d]])
    ex /= np.max(np.abs(ex)) + 1e-12
    y = np.zeros(n + pi_ + 2)
    y[: pi_ + 2] = ex
    blk = max(pi_ - 2, 8)
    i = pi_ + 2
    while i < len(y):
        j = min(i + blk, len(y))
        idx = np.arange(i, j)
        if mode == "contact":
            shift = frac + 0.6 * np.maximum(y[idx - pi_], 0.0)
            base = np.minimum(np.floor(shift), 2.0).astype(int)
            fr = np.clip(shift - base, 0.0, 1.0)
            t0, t1, t2 = (y[idx - pi_ - base], y[idx - pi_ - base - 1],
                    y[idx - pi_ - base - 2])
            s0 = (1 - fr) * t0 + fr * t1
            s1 = (1 - fr) * t1 + fr * t2
        else:
            s0 = (1 - frac) * y[idx - pi_] + frac * y[idx - pi_ - 1]
            s1 = (1 - frac) * y[idx - pi_ - 1] + frac * y[idx - pi_ - 2]
        v = rho * ((1 - 0.5 * damp) * s0 + 0.5 * damp * s1)
        if mode in ("saturator", "restored"):
            p = np.maximum(v, 0.0)
            shaped = v - p + p / (1.0 + 1.8 * p)
            if mode == "restored":
                e0 = np.sqrt(np.mean(v * v)) + 1e-12
                e1 = np.sqrt(np.mean(shaped * shaped)) + 1e-12
                shaped *= e0 / e1
            v = shaped
        elif mode == "obstacle":
            v = np.where(v > 0.35, 0.35 + (v - 0.35) * 0.12, v)
        y[i:j] = v
        i = j
    out = y[pi_ + 2:]
    return out / (np.max(np.abs(out)) + 1e-12) * 0.9


def hf_peak_s(x):
    sos = butter(2, [1500, 6000], btype="band", fs=SR, output="sos")
    e = np.abs(sosfilt(sos, x))
    win = int(0.1 * SR)
    env = [e[k:k + win].mean() for k in range(0, len(e) - win, win)]
    return float(np.argmax(env)) * 0.1


def late_centroid(x):
    return ruler.centroid_hz(x[int(3.5 * SR):int(4.0 * SR)])


MODES = ["dry", "saturator", "restored", "contact", "obstacle"]
p = {m: ks(hz(45), 8.0, m) for m in MODES}

# control 1: every bridge leaves the pitch alone
for m in MODES:
    f = ruler.hps_pitch(p[m][int(1.0 * SR):int(3.0 * SR)], 60.0, 500.0)
    check(f"pitch holds ({m})", abs(f - hz(45)) < 1.0, f"{f:.1f} Hz")

# control 2: the nonlinear bridges actually do something
for m in MODES[1:]:
    dmax = float(np.abs(p[m][:int(4 * SR)] - p["dry"][:int(4 * SR)]).max())
    check(f"bridge engages ({m})", dmax > 0.05, f"maxdiff {dmax:.3f}")

# the findings, asserted
sus = slice(int(1.5 * SR), int(4.0 * SR))
r_sat = ruler.band_density(p["saturator"][sus], 2500, 6000) / \
    (ruler.band_density(p["dry"][sus], 2500, 6000) + 1e-30)
check("saturator is a damper", r_sat < 0.75,
        f"sustain 2.5-6 kHz x{r_sat:.2f} vs dry")

for m in ("restored", "contact"):
    rc = late_centroid(p[m]) / (late_centroid(p["dry"]) + 1e-30)
    check(f"{m} still darkens", rc < 0.75,
            f"late centroid {rc:.2f}x dry's")

ring = slice(int(0.3 * SR), int(1.5 * SR))
bands = [(40, 300), (300, 800), (800, 1500), (1500, 3000), (3000, 6000)]
rr = [ruler.band_density(p["obstacle"][ring], lo, hi)
        / (ruler.band_density(p["dry"][ring], lo, hi) + 1e-30)
        for lo, hi in bands]
check("obstacle barely engages", max(rr) / min(rr) < 1.6,
        f"per-band ratios {min(rr):.2f}..{max(rr):.2f} — gain, not shape")

for m in MODES:
    check(f"no bloom ({m})", hf_peak_s(p[m][:int(4 * SR)]) < 0.15,
            f"HF envelope peaks at {hf_peak_s(p[m][:int(4 * SR)]):.1f}s")

# control 3: the bloom ruler can SEE a bloom (synthetic positive)
tt = np.arange(int(4 * SR)) / SR
synth = np.sin(2 * np.pi * 110 * tt) * np.exp(-tt * 0.5) \
    + np.sin(2 * np.pi * 2500 * tt) * np.exp(-((tt - 0.8) / 0.35) ** 2)
tp = hf_peak_s(synth)
check("bloom ruler not blind", 0.6 <= tp <= 1.0,
        f"synthetic bloom read at {tp:.1f}s (designed 0.8)")

# ---- the exhibit render ----------------------------------------
gap = np.zeros(int(0.6 * SR))
seq = []
for m in MODES:
    seq += [p[m][:int(4 * SR)] * np.concatenate([
        np.ones(int(3.8 * SR)), np.linspace(1, 0, int(0.2 * SR))]), gap]
mono = np.concatenate(seq)
out = stereo(mono * 0.9 / (np.max(np.abs(mono)) + 1e-12), 0.0)
write_wav(os.path.join(outdir, "e41_bridgetrials.wav"), out)
ruler.report(out, "trials")

print("ALL RULERS PASS" if not fails else f"FAILED: {fails}")
sys.exit(1 if fails else 0)

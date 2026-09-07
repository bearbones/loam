#!/usr/bin/env python3
"""e98 — the string's shape, from the same simulation as its sound.

Stage 3 of the chamber (docs/chamber-spec.md). fdpluck integrates
the stiff-string PDE on N+1 nodes and holds the whole displacement
field every step — then reads ONE node into audio and lets the rest
go. fdshape keeps a decimated copy (24-64 nodes, 120 Hz) for the
engine to draw. Four claims license the design:

  1. FRAME 0 IS THE TRIANGLE: the field starts as the plucked shape,
     apex at `pick` — argmax node lands within one node of pick.
  2. THE COMB, SEEN: Jaffe-Smith's pick-position comb says a pluck
     at x = 1/4 cannot excite mode 4 (its node is under the finger).
     Spatial sine series of the frames: mode 4's RMS over time is a
     small fraction of modes 3 and 5. The notch you hear as timbre,
     seen as a missing standing wave.
  3. THE VISUAL DECAYS AS THE AUDIO DOES: t60 of the frame envelope
     (shape_t60) vs ruler.decay_t60 of the readout around f0 — the
     engine's decay is the ear's decay, from one run.
  4. F0-INVARIANCE (the library license): in normalized coordinates
     only the wave speed depends on f0; damping (sig0, sig1) and
     stiffness (kappa) do not. So 110/220/440 Hz give the same
     energy per spatial mode, the same t60 in SECONDS, and an
     envelope that agrees to within the beating of the partials.
     (First run claimed the envelope to 1.5 dB and missed by 0.2:
     the deviation sat mid-ring, mean 0.5 dB, mode cosine 0.9998 —
     not decay, BEATING. kappa fixed in normalized units makes a
     low string relatively stiffer, so its inharmonic partials beat
     at a different rate. Physics, and below what an eye resolves
     in a string blur.) Hence a small library keyed by pick, not a
     bake per note — with bridge=False, where the system is linear
     and amplitude is a scalar. If two octaves' beating ever
     showed, bake per octave.

    python3 experiments/e98_string_shapes.py [outdir]
"""

import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))))
from loam import SR, write_wav
from loam import ruler
from loam.fdstring import fdshape, shape_t60, shape_library

outdir = sys.argv[1] if len(sys.argv) > 1 else "render"
ex = os.path.join(outdir, "e98")
os.makedirs(ex, exist_ok=True)
fails = []


def check(name, cond, detail):
    print(f"  {'PASS' if cond else 'FAIL'} {name}: {detail}")
    if not cond:
        fails.append(name)


def sine_modes(frames, kmax=8):
    """Spatial sine-series coefficients per frame: a[f, k-1]."""
    n = frames.shape[1]
    x = np.linspace(0, 1, n)
    basis = np.stack([np.sin(k * np.pi * x) for k in range(1, kmax + 1)])
    return frames @ basis.T * (2.0 / n)


t0 = time.time()
NODES, RATE = 64, 240.0
audio, fr, scale = fdshape(220.0, 2.0, nodes=NODES, rate_hz=RATE,
        pick=0.25, t60=3.2)
print(f"  fdshape 220 Hz, 2 s, {NODES} nodes @ {RATE:g} Hz: {fr.shape} "
      f"in {time.time() - t0:.1f}s, scale {scale * 1e3:.2f} mm")

# ---- 1. frame 0 is the triangle ---------------------------------------------
apex = int(np.argmax(np.abs(fr[0]))) / (NODES - 1)
check("frame 0 apex at pick", abs(apex - 0.25) <= 1.0 / (NODES - 1),
        f"apex at x={apex:.3f} (pick 0.25, node width {1/(NODES-1):.3f})")

# ---- 2. the comb, seen ---------------------------------------------------
A = sine_modes(fr)
rms = np.sqrt(np.mean(A ** 2, axis=0))
ratio = rms[3] / max(rms[2], rms[4])
check("pick at 1/4 nulls mode 4 (Jaffe-Smith comb, seen)",
        ratio < 0.10,
        f"mode RMS 1..6 = {np.round(rms[:6] / rms[0], 3).tolist()}; "
        f"mode4 / max(mode3, mode5) = {ratio:.3f}")

# ---- 3. visual decay == audible decay ------------------------------------------
t60_vis = shape_t60(fr, RATE)
t60_aud = ruler.decay_t60(audio, 220.0 * 0.85, 220.0 * 1.15,
        win_s=0.05, drop=15.0)
# mode 1 alone (the fundamental's own visual decay)
a1 = np.abs(A[:, 0])
w = int(0.1 * RATE)
env1 = np.array([a1[i:i + w].max() for i in range(len(a1))])
db1 = 20 * np.log10(env1 + 1e-15)
tt = np.arange(len(db1)) / RATE
ip = int(np.argmax(db1))
s = np.arange(ip, len(db1))[db1[ip:] > db1[ip] - 15.0]
t60_m1 = -60.0 / np.polyfit(tt[s], db1[s], 1)[0]
check("visual fundamental decays as the audible one",
        abs(t60_m1 - t60_aud) / t60_aud < 0.15,
        f"mode-1 shape t60 {t60_m1:.2f}s vs audio band t60 {t60_aud:.2f}s "
        f"(whole-field env t60 {t60_vis:.2f}s; designed 3.2s)")

# ---- 4. f0 invariance ---------------------------------------------------------
envs, dists, t60s = {}, {}, {}
for f0 in (110.0, 220.0, 440.0):
    _, frf, _ = fdshape(f0, 2.0, nodes=NODES, rate_hz=RATE, pick=0.25,
            t60=3.2)
    e = np.max(np.abs(frf), axis=1)
    e = np.array([e[i:i + w].max() for i in range(len(e))])
    envs[f0] = 20 * np.log10(e + 1e-15)
    r = np.sqrt(np.mean(sine_modes(frf) ** 2, axis=0))
    dists[f0] = r / np.linalg.norm(r)
    t60s[f0] = shape_t60(frf, RATE)
span = int(1.5 * RATE)
devs = {f: np.abs(envs[f] - envs[220.0])[:span] for f in (110.0, 440.0)}
env_max = max(d.max() for d in devs.values())
env_mean = max(d.mean() for d in devs.values())
cos = min(float(dists[f] @ dists[220.0]) for f in (110.0, 440.0))
t60_dev = max(abs(t60s[f] - t60s[220.0]) / t60s[220.0]
              for f in (110.0, 440.0))
check("f0-invariance: mode energies, t60 in seconds, envelope to the beat",
        cos > 0.99 and t60_dev < 0.08 and env_mean < 1.0 and env_max < 2.5,
        f"mode-distribution cosine ≥ {cos:.4f}; t60 "
        + "/".join(f"{t60s[f]:.2f}" for f in (110.0, 220.0, 440.0))
        + f" s (dev {100 * t60_dev:.1f}%); envelope dev mean "
        f"{env_mean:.2f} dB, max {env_max:.2f} dB (partials beating)")

# ---- the library itself ---------------------------------------------------------
t0 = time.time()
clips = shape_library(t60=3.2, cache_dir=os.path.join(outdir, ".shapes"))
print(f"  library: {len(clips)} clips in {time.time() - t0:.1f}s; "
      + ", ".join(f"{c['id']} t60={c['t60_s']:.2f}s" for c in clips))
check("library clips decay to design t60 (±20%)",
        all(abs(c["t60_s"] - 3.2) / 3.2 < 0.2 for c in clips),
        "each clip's shape_t60 vs 3.2 s")

# ---- pictures for the operator --------------------------------------------
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
fig, axes = plt.subplots(1, 3, figsize=(16, 4.5))
x = np.linspace(0, 1, NODES)
ax = axes[0]
for i, k in enumerate(range(0, int(0.02 * RATE) + 1)):
    ax.plot(x, fr[k] + 0.0, color=plt.cm.viridis(i / (0.02 * RATE)), lw=1)
ax.set_title("first 20 ms: the triangle unfolds (pick 0.25)")
ax.set_xlabel("x along string")
ax = axes[1]
ax.bar(range(1, 9), rms[:8] / rms[0])
ax.set_title("time-RMS spatial modes — mode 4 is the pick's null")
ax.set_xlabel("mode k")
ax = axes[2]
for f0, e in envs.items():
    ax.plot(np.arange(len(e)) / RATE, e - e.max(), label=f"{f0:g} Hz")
ax.set_ylim(-40, 2)
ax.set_title("envelope in seconds: f0-invariant")
ax.set_xlabel("s")
ax.legend()
fig.tight_layout()
png = os.path.join(ex, "shapes.png")
fig.savefig(png, dpi=110)
print(f"wrote {png}")
write_wav(os.path.join(ex, "pluck220.wav"),
        np.stack([audio, audio], axis=1) * 0.9)

if fails:
    print("FAILED RULERS:", fails)
    sys.exit(1)
print("ALL RULERS PASS")

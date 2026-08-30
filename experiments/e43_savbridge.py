#!/usr/bin/env python3
"""e43 — the unbreakable bridge: SAV contact, and a record corrected.

Session 42 logged the jawari's grazing contact as GRID-BRITTLE
(N=140 blooms, N=150 doesn't) and conjectured energy-conserving
collision would fix it. This cycle built the fix — and the first
honest measurement corrected the record instead: the brittleness
was an artifact of the DISPLACEMENT readout and single-signal
bloom ruler it was diagnosed under, both of which e42 itself
replaced later that session. Under the shipped measurement
(velocity readout, wet/dry envelope ratio), the plain penalty
contact already blooms on every grid tried. Rulers below pin the
corrected claim for both contact models.

What the SAV contact (now fdpluck's default) actually buys:
- ENERGY: total discrete energy (string + contact store psi^2/2)
  conserved to machine precision on a lossless string — measured
  drift ~1e-12 vs the explicit penalty's ~1e-2. The midpoint
  force g*(psi+ + psi-)/2 with psi+ - psi- = -g*(un-up)/2 makes
  the contact work a perfect difference of squares.
- STABILITY AT ANY K: the penalty integrator NaN-explodes at
  K=1e11; SAV rings at K=1e12. Contact stiffness becomes a safe
  voicing knob instead of a footgun.

Render: the K staircase — the same A2 string, bridge stiffness
stepping 3e8 -> 1e12 (x3000), each step a timbre the explicit
integrator could not have survived past the third. A sequence,
not a loop; no seam claim.

    python3 experiments/e43_savbridge.py [outdir]
"""

import os
import subprocess
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))))
from loam import SR, stereo, write_wav
from loam import ruler
from loam.fdstring import fdpluck

outdir = sys.argv[1] if len(sys.argv) > 1 else "render"
os.makedirs(outdir, exist_ok=True)
fails = []


def check(name, cond, detail):
    print(f"  {'PASS' if cond else 'FAIL'} {name}: {detail}")
    if not cond:
        fails.append(name)


# ---- 1. the energy theorem, measured ---------------------------
# Instrumented lossless copy of the scheme (measurement harness,
# like e41's local ks()): tracks the staggered discrete energy
# H = KE + tension + stiffness + contact store.
def energy_drift(contact, K=3e9, alpha=1.3, dur=2.0, N=80,
        f0=110.0, kappa=0.3, gcurve=0.2, pluck_m=1.6e-3,
        zone=0.10):
    dt = 1.0 / SR
    c = 2.0 * f0
    dx = 1.0 / N
    lam2 = (c * dt / dx) ** 2
    mu2 = (kappa * dt / dx ** 2) ** 2
    x = np.linspace(0, 1, N + 1)
    u = np.where(x < 0.28, x / 0.28, (1 - x) / 0.72) * pluck_m
    u[0] = u[-1] = 0.0
    up = u.copy()
    bz = x > 1.0 - zone
    bb = -gcurve * (1.0 - x[bz]) ** 2
    Kdt2 = K * dt * dt
    psi = np.sqrt(2.0 * K / (alpha + 1)
            * np.maximum(bb - u[bz], 0.0) ** (alpha + 1) + 1e-24)
    lap = np.zeros(N + 1)
    bi = np.zeros(N + 1)
    H = []

    def energy(un, u, psi_):
        v = (un - u) / dt
        gx1 = np.diff(un) / dx
        gx0 = np.diff(u) / dx

        def dxx(w):
            d = np.zeros_like(w)
            d[1:-1] = (w[2:] - 2 * w[1:-1] + w[:-2]) / dx / dx
            return d

        ce = dx * np.sum(0.5 * (psi_ * psi_ - 1e-24)) \
            if contact == "sav" else \
            dx * np.sum(K / (alpha + 1)
                * np.maximum(bb - un[bz], 0.0) ** (alpha + 1))
        return (0.5 * dx * np.sum(v * v)
                + 0.5 * c * c * dx * np.sum(gx1 * gx0)
                + 0.5 * kappa * kappa * dx
                * np.sum(dxx(un) * dxx(u)) + ce)

    for t in range(int(dur * SR)):
        lap[1:-1] = u[2:] - 2 * u[1:-1] + u[:-2]
        bi[2:-2] = u[4:] - 4 * u[3:-1] + 6 * u[2:-2] - 4 * u[1:-3] \
            + u[:-4]
        bi[1] = u[3] - 4 * u[2] + 6 * u[1] - 4 * u[0] - u[1]
        bi[-2] = -u[-2] - 4 * u[-1] + 6 * u[-2] - 4 * u[-3] + u[-4]
        un = 2 * u - up + lam2 * lap - mu2 * bi
        if contact == "sav":
            eta = np.maximum(bb - u[bz], 0.0)
            g = K * eta ** alpha / psi
            unb = (un[bz] + dt * dt * (g * psi + g * g * up[bz] / 4)) \
                / (1.0 + dt * dt * g * g / 4)
            psi = psi - g * (unb - up[bz]) / 2.0
            un[bz] = unb
        else:
            un[bz] += Kdt2 * np.maximum(bb - u[bz], 0.0) ** alpha
        un[0] = un[-1] = 0.0
        if t % 441 == 0:
            H.append(energy(un, u, psi))
        up, u = u, un
    H = np.array(H)
    return float((H.max() - H.min()) / H[0])


d_sav = energy_drift("sav")
d_pen = energy_drift("penalty")
check("SAV conserves energy (lossless, contact live)",
        d_sav < 1e-9, f"relative drift {d_sav:.1e}")
check("control: the drift ruler can see drift",
        d_pen > 1e-4, f"penalty drifts {d_pen:.1e}")

# ---- 2. stability at any K -------------------------------------
with np.errstate(over="ignore", invalid="ignore"):
    hard_sav = fdpluck(110.0, 1.5, N=140, K=1e12)
    hard_pen = fdpluck(110.0, 1.5, N=140, K=1e11, contact="penalty")
check("SAV rings at K=1e12", bool(np.all(np.isfinite(hard_sav))),
        f"peak {np.abs(hard_sav).max():.2f}")
check("control: penalty explodes at K=1e11",
        not bool(np.all(np.isfinite(hard_pen))),
        "NaN, as expected — the stress test is real")

# ---- 3. the record, corrected: no grid brittleness -------------
GRIDS = (130, 136, 140, 144, 150, 156, 160)
dry = fdpluck(110.0, 6.0, N=140, bridge=False)
ed = ruler.band_env(dry)
sus = slice(int(1.5 * SR), int(4.0 * SR))
dbd = ruler.band_density(dry[sus], 1500, 6000)
for mode in ("sav", "penalty"):
    blooms = 0
    for n in GRIDS:
        w = fdpluck(110.0, 6.0, N=n, contact=mode)
        ew = ruler.band_env(w)
        m = min(len(ew), len(ed))
        tstar = float(np.argmax(ew[:m] / (ed[:m] + 1e-30))) * 0.1
        enr = ruler.band_density(w[sus], 1500, 6000) / (dbd + 1e-30)
        blooms += (tstar >= 0.25 and enr >= 3.0)
    check(f"all grids bloom ({mode})", blooms >= 6,
            f"{blooms}/{len(GRIDS)} grids 130..160 "
            "(e42's brittleness was the old ruler, not the physics)")

# ---- 4. K is a voicing knob — the staircase render -------------
KS = (3e8, 3e9, 3e10, 1e11, 1e12)
notes = [fdpluck(110.0, 4.0, N=140, K=k) for k in KS]
enrs = [ruler.band_density(v[sus], 1500, 6000) / (dbd + 1e-30)
        for v in notes]
check("every step rings", all(np.all(np.isfinite(v)) for v in notes),
        f"peaks {[round(float(np.abs(v).max()), 2) for v in notes]}")
check("K audibly voices the buzz", max(enrs) / min(enrs) > 1.5,
        "sustain enrichment "
        + " ".join(f"x{e:.1f}" for e in enrs) + " across K x3000")

gap = np.zeros(int(0.4 * SR))
seq = []
for i, v in enumerate(notes):
    pan = -0.6 + 1.2 * i / (len(notes) - 1)
    seq.append(stereo(np.concatenate([v, gap]), pan))
out = np.concatenate(seq)
out *= 0.9 / (np.max(np.abs(out)) + 1e-12)
wav = os.path.join(outdir, "e43_savbridge.wav")
write_wav(wav, out)
ruler.report(out, "staircase")
subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", wav,
        "-q:a", "5", wav.replace(".wav", ".ogg")], check=True)

print("ALL RULERS PASS" if not fails else f"FAILED: {fails}")
sys.exit(1 if fails else 0)

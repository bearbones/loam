#!/usr/bin/env python3
"""e48 — the two-polarization string: shimmer by physics.

A real string vibrates in two transverse planes at once, split a
few cents by bridge anisotropy, exchanging energy through the
bridge, and only ONE plane meets the jawari. fdpluck2 simulates
both lattices: vertical u (plucked, bridged), horizontal v
(silent at t=0, detuned by `split`, fed only through a spring
across the bridge zone). Everything the design promises is
measured, on the buses it happens on:

  - delayed transfer: v blooms ~0.4 s after a pluck it never
    received, ringing ~24 dB under u; with the coupling removed
    it stays at numerical silence (-600 dB).
  - the jawari touches only u: the vertical's sustain holds
    thousands of times the horizontal's high-band density.
  - polarization beating: the detuned mode pair makes the v-bus
    envelope breathe at f0*split — read by the new
    ruler.beat_profile (log-domain DETRENDED envelope spectrum;
    an un-detrended decay ramp votes ~0.3 Hz for any signal,
    beating or not). Beat tracks design across two split values
    and collapses to the junk floor at split=0.
  - and the beats SURVIVE THE MIX: in the full four-string
    drone each string's fundamental band carries its own beat
    (rate proportional to its f0 — a chord of shimmer rates),
    verified per band in the render itself.

    python3 experiments/e48_twopol.py [outdir]
"""

import os
import subprocess
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))))
from loam import SR, hz, Loop, stereo, write_wav
from loam import ruler
from loam.fdstring import fdpluck2

outdir = sys.argv[1] if len(sys.argv) > 1 else "render"
os.makedirs(outdir, exist_ok=True)
fails = []


def check(name, cond, detail):
    print(f"  {'PASS' if cond else 'FAIL'} {name}: {detail}")
    if not cond:
        fails.append(name)


F0 = hz(50)

# ---- 1. energy transfer to the plane nobody plucked ------------
out, ou, ov = fdpluck2(F0, 6.0, buses=True)
vpk_t = float(np.argmax(np.abs(ov))) / SR
vpk_db = 20 * np.log10(np.abs(ov).max() / np.abs(ou).max())
check("horizontal blooms late", vpk_t >= 0.2,
        f"v peaks {vpk_t:.2f}s after a pluck it never received")
check("horizontal rings in earshot", -30.0 <= vpk_db <= -10.0,
        f"v/u peak {vpk_db:.1f} dB")
_, ou0, ov0 = fdpluck2(F0, 3.0, kc=0.0, buses=True)
z_db = 20 * np.log10((np.abs(ov0).max() + 1e-30)
        / np.abs(ou0).max())
check("no coupling, no transfer", z_db <= -80.0,
        f"kc=0 control: v/u {z_db:.0f} dB")

# ---- 2. the jawari touches only the vertical -------------------
sus = slice(int(1.5 * SR), int(5.5 * SR))
asym = ruler.band_density(ou[sus], 1500, 6000) \
    / (ruler.band_density(ov[sus], 1500, 6000) + 1e-30)
check("bloom stays on the bridged plane", asym >= 100.0,
        f"u/v sustain hi-band density x{asym:.0f}")

# ---- 3. beating tracks the designed detune ---------------------
# one envelope-FFT bin over a 6 s note is ~0.17 Hz; the junk/true
# calibration is measured: detuned depths 6-9 dB, zero-split
# floor under 4 (the decay ramp's leftovers)
for split in (0.006, 0.003):
    _, _, ovs = fdpluck2(F0, 6.0, split=split, buses=True)
    r, d = ruler.beat_profile(ovs, F0 * 0.85, F0 * 1.15)
    check(f"beat tracks detune (split={split})",
            abs(r - F0 * split) <= 0.17 and d >= 5.0,
            f"designed {F0 * split:.2f} Hz, measured {r:.2f} Hz "
            f"at {d:.1f} dB depth")
_, _, ov_z = fdpluck2(F0, 6.0, split=0.0, buses=True)
rz, dz = ruler.beat_profile(ov_z, F0 * 0.85, F0 * 1.15)
check("no detune, no beat", dz <= 4.0,
        f"split=0 depth {dz:.1f} dB (true beats read 6-9)")

# ---- 4. the piece: a drone that breathes -----------------------
DRONE = [("pa", hz(45), 140, 0.0, -0.35, 0.60),
        ("sa+", hz(50.015), 112, 1.2, 0.15, 0.55),
        ("sa-", hz(49.985), 112, 2.4, -0.15, 0.55),
        ("SA", hz(38), 138, 3.6, 0.35, 0.80)]
loop = Loop(9.6, seed=48)
for name, f0, n, at, pan, amp in DRONE:
    v = fdpluck2(f0, 12.0, amp=amp, N=n)
    loop.add(at, stereo(v, pan))
    loop.add(at + 4.8, stereo(v, pan))
mix = loop.master(lp_hz=6500.0, drive=1.2)
check("seam", ruler.seam_rank(mix) <= 0.999,
        f"p{100 * ruler.seam_rank(mix):.2f}")
early = float(np.sqrt(np.mean(mix[:SR] ** 2)))
late = float(np.sqrt(np.mean(mix[-SR:] ** 2)))
check("the coupled pair still decays", np.all(np.isfinite(mix))
        and late < 4.0 * early,
        f"loop RMS first/last second {early:.3f}/{late:.3f}")

# each string's fundamental band carries its OWN beat rate in the
# full render — a chord of shimmer, verified per band (two loop
# passes so the envelope FFT gets 19.2 s of resolution). Band
# isolation lesson: band_env's 2nd-order edges are shallow, and a
# LOUDER, DEEPER neighbor's beat colonizes a wide band (pa at
# +/-10% read the sa pair's 0.84 where its own rate is 0.66 —
# ring-over enfranchisement's cousin, in the envelope domain).
# Bands are as narrow as each string's neighborhood demands.
big = np.concatenate([mix, mix]).mean(axis=1)
for name, f0, w in (("pa", hz(45), 0.05), ("sa", hz(50), 0.07),
        ("SA", hz(38), 0.10)):
    r, d = ruler.beat_profile(big, f0 * (1 - w), f0 * (1 + w))
    check(f"the mix breathes at {name}'s own rate",
            abs(r - f0 * 0.006) <= 0.11 and d >= 6.0,
            f"designed {f0 * 0.006:.2f} Hz, measured {r:.2f} Hz "
            f"at {d:.1f} dB")
ch = ruler.chroma(big)
top2 = set(np.argsort(ch)[-2:].tolist())
check("D and A are the two poles", top2 == {2, 9},
        f"top-2 classes {sorted(top2)}")

out = np.concatenate([mix, mix])
wav = os.path.join(outdir, "e48_twopol.wav")
write_wav(wav, out)
ruler.report(out, "twopol")
subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", wav,
        "-q:a", "5", wav.replace(".wav", ".ogg")], check=True)

print("ALL RULERS PASS" if not fails else f"FAILED: {fails}")
sys.exit(1 if fails else 0)

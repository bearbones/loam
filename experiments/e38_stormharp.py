#!/usr/bin/env python3
"""e38 — the storm harp: e37's open thread, thunder as a chord
source. Four lightning strikes drive sympathetic() — the taraf
bank that hums along with anything — tuned to a nine-string D
minor bank (pitch classes D/F/A/C only; no E, so foreign notes
are falsifiable). Broadband rumble in, chord out: the sky plays
the harp. Rain and low wind underneath; every string tail and
thunder tail wraps per seam-craft rule 3.

Rulers (own buses, norm=False where energy is compared):
tonalization (ruler.flatness, new this cycle), comb selectivity
(tuned vs quarter-tone probes), the strings ANSWER the sky
(envelope cross-correlation, lag >= 0), no foreign notes (top-4
chroma inside the tuned classes), scene seam.

    python3 experiments/e38_stormharp.py [outdir]
"""

import os
import sys

import numpy as np
from scipy.signal import butter, sosfiltfilt

sys.path.insert(0, os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))))
from loam import SR, hz, Loop, write_wav, seam_report
from loam import ruler
from loam.texture import rain, wind, thunder
from loam.strings import sympathetic

outdir = sys.argv[1] if len(sys.argv) > 1 else "render"
os.makedirs(outdir, exist_ok=True)
fails = []


def check(name, cond, detail):
    print(f"  {'PASS' if cond else 'FAIL'} {name}: {detail}")
    if not cond:
        fails.append(name)


T = 40.0
n = int(T * SR)
BANK = [38, 45, 50, 53, 57, 60, 62, 65, 69]   # D A D F A C D F A
TUNED_CLASSES = {0, 2, 5, 9}                  # C D F A

# ---- the sky ---------------------------------------------------
sky = np.zeros((n, 2))
for at, dist, amp, sd in ((3.0, 1.2, 0.9, 21), (14.0, 4.5, 0.55, 22),
                          (24.0, 2.2, 0.75, 23), (33.0, 6.5, 0.5, 24)):
    ev = thunder(dist, seed=sd) * amp
    idx = (int(at * SR) + np.arange(len(ev))) % n
    np.add.at(sky, idx, ev)

# ---- the harp (wet only, unnormalized: the physical response) --
harp = sympathetic(sky, BANK, t60=10.0, damp=0.3, coupling=0.5,
        mix=1.0, loop=True, norm=False)
harp_raw = harp.copy()
harp = harp * (0.6 / (np.max(np.abs(harp)) + 1e-12))

# ---- rulers ----------------------------------------------------
fl_sky = ruler.flatness(sky)
fl_harp = ruler.flatness(harp_raw)
check("tonalization", fl_harp < fl_sky / 10.0,
        f"flatness sky {fl_sky:.4f} -> harp {fl_harp:.5f} "
        f"({fl_sky / (fl_harp + 1e-30):.0f}x more tonal)")

tuned = sum(ruler.band_density(harp_raw, hz(m) * 0.985, hz(m) * 1.015)
        for m in BANK)
probe = sum(ruler.band_density(harp_raw, hz(m + 0.5) * 0.985,
        hz(m + 0.5) * 1.015) for m in BANK)
check("comb selectivity", tuned > 3.0 * probe,
        f"tuned-band density {tuned / (probe + 1e-30):.1f}x "
        f"the quarter-tone probes")

sos_e = butter(2, 2.0, btype="low", fs=SR, output="sos")
env_s = sosfiltfilt(sos_e, np.abs(sky.mean(axis=1)))
env_h = sosfiltfilt(sos_e, np.abs(harp_raw.mean(axis=1)))
env_s -= env_s.mean()
env_h -= env_h.mean()
cc = np.correlate(env_h, env_s, mode="full")
lag = int(np.argmax(cc)) - (len(env_s) - 1)
r = float(cc.max() / (np.sqrt((env_s ** 2).sum() * (env_h ** 2).sum())
        + 1e-30))
check("strings answer the sky", r > 0.6 and 0 <= lag <= int(2.0 * SR),
        f"envelope corr {r:.2f} at lag {lag / SR * 1000:.0f} ms")

ch = ruler.chroma(harp_raw)
top4 = set(np.argsort(ch)[-4:].tolist())
names = "C C# D D# E F F# G G# A A# B".split()
check("no foreign notes", top4 <= TUNED_CLASSES,
        f"top-4 chroma {{{', '.join(names[i] for i in sorted(top4))}}} "
        f"vs tuned {{C, D, F, A}}")

# ---- the scene -------------------------------------------------
L = Loop(T, 0xE38)
L.buf += rain(T, density=8.0, near=0.35, bright=0.25, seed=1) * 0.55
L.buf += wind(T, base_hz=240.0, howl=0.35, gust=0.5, seed=2) * 0.3
L.buf += sky * 0.85
L.buf += harp
mix = L.master(lp_hz=9000.0, drive=1.15)
write_wav(os.path.join(outdir, "e38_stormharp.wav"), mix)
print(seam_report(mix))
ruler.report(mix, "scene")
check("scene seam", ruler.seam_rank(mix) <= 0.999,
        f"rank=p{100 * ruler.seam_rank(mix):.1f}")

print("ALL RULERS PASS" if not fails else f"FAILED: {fails}")
sys.exit(1 if fails else 0)

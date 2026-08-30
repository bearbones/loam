#!/usr/bin/env python3
"""e37 — stormfront: texture.thunder() (the open thread from e36)
and the storm it completes. Thunder as geometry: channel-segment
arrival times smear a close strike over seconds; per-arrival air
absorption darkens the tail causally. Rulers check the PHYSICS on
bare buses (norm=False, house rule): distance darkens, distance
softens, the crack is a crest, the tail out-rumbles its own highs,
and unnormalized loudness falls with distance. Then the scene: a
36 s loop of rain + wind + three strikes at three distances, tails
wrapping per seam-craft rule 3.

    python3 experiments/e37_stormfront.py [outdir]
"""

import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))))
from loam import SR, Loop, write_wav, seam_report
from loam import ruler
from loam.texture import rain, wind, thunder

outdir = sys.argv[1] if len(sys.argv) > 1 else "render"
os.makedirs(outdir, exist_ok=True)
fails = []


def check(name, cond, detail):
    print(f"  {'PASS' if cond else 'FAIL'} {name}: {detail}")
    if not cond:
        fails.append(name)


# ---- physics rulers, bare buses, norm OFF ----------------------
near = thunder(0.8, seed=11, norm=False)
far = thunder(5.5, seed=12, norm=False)
print(f"near: {len(near) / SR:.1f}s   far: {len(far) / SR:.1f}s")

c_near, c_far = ruler.centroid_hz(near), ruler.centroid_hz(far)
check("distance darkens", c_near > 2.0 * c_far,
        f"centroid near {c_near:.0f} Hz vs far {c_far:.0f} Hz")

cr_n, cr_f = ruler.crest_db(near), ruler.crest_db(far)
check("crack is a crest", cr_n > cr_f + 5.0,
        f"crest near {cr_n:.1f} dB vs far {cr_f:.1f} dB")

head = near[:int(0.5 * SR)]
tail = near[int(2.5 * SR):int(5.0 * SR)]
check("tail walked farther", ruler.centroid_hz(head)
        > 2.0 * ruler.centroid_hz(tail),
        f"centroid head {ruler.centroid_hz(head):.0f} Hz "
        f"vs tail {ruler.centroid_hz(tail):.0f} Hz")

lo_d = ruler.band_density(tail, 25, 120)
hi_d = ruler.band_density(tail, 500, 2500)
check("tail rumbles", lo_d > 4.0 * hi_d,
        f"25-120 Hz density {lo_d / hi_d:.1f}x the 500-2500 band")

contour = ruler.rms_contour(near, 8)
check("strike decays", int(np.argmax(contour)) == 0
        and contour[0] - contour[-1] >= 10.0,
        f"peak window {int(np.argmax(contour))}, "
        f"fall {contour[0] - contour[-1]:.1f} dB")

check("distance softens", ruler.rms_db(near) > ruler.rms_db(far) + 6.0,
        f"rms near {ruler.rms_db(near):.1f} dB vs far "
        f"{ruler.rms_db(far):.1f} dB (unnormalized)")

# ---- the scene -------------------------------------------------
T = 36.0
L = Loop(T, 0xE37)
L.buf += rain(T, density=10.0, near=0.4, bright=0.3, seed=1) * 0.8
L.buf += wind(T, base_hz=300.0, howl=0.4, gust=0.6, seed=2) * 0.45

for at, dist, amp, sd in ((5.0, 0.8, 0.95, 11), (20.0, 5.5, 0.5, 12),
                          (29.0, 2.5, 0.7, 13)):
    ev = thunder(dist, seed=sd) * amp
    L.add(at, ev)

mix = L.master(lp_hz=9000.0, drive=1.15)
write_wav(os.path.join(outdir, "e37_stormfront.wav"), mix)
print(seam_report(mix))
ruler.report(mix, "scene")
check("scene seam", ruler.seam_rank(mix) <= 0.999,
        f"rank=p{100 * ruler.seam_rank(mix):.1f}")

print("ALL RULERS PASS" if not fails else f"FAILED: {fails}")
sys.exit(1 if fails else 0)

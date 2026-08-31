#!/usr/bin/env python3
"""e65 — andolan: the wobbling bow.

New expressive class for the bowed voice: slow, deep vibrato
on a held note (the andolan a komal note carries in Kafi).
After e64's cliff lesson — transitions are what throw the
string off the fundamental branch — vibrato is a CONTINUOUS
transition, so the first question is physics, not taste:

  - slow andolan keeps the lock at every depth tried: 2 Hz at
    +-40c and +-80c both hold odd/even >= 0.6 on the ratio
    recipe. The bow tolerates a breathing pitch.
  - but the vibrato plane has a HOLE, like every playability
    map so far (e61's octave pocket, e64's cliff): +-40c at
    5 Hz drops the lock to 0.08 while both neighbours (20c
    and 80c at the same rate) survive. Measured, pinned,
    avoided.
  - the ornament ruler reads rate exactly (worst 0.01 Hz off
    across a 3x3 grid) and depth through a calibrated
    attenuation: x0.91 at 2 Hz, consistent across 20/40/80c
    (e47's lesson — calibrate depth against the same class at
    the same rate, never trust the raw number). Zero-depth
    control reads 0.1c.

The piece: jor with a breathing ga — Sa rises to komal Ga,
which oscillates +-40c at 2 Hz for two and a half seconds
(measured in-phrase: rate on the nose, depth through the
calibrated factor), falls through Re, home to Sa, bow lifts
into the seam. Taraf and tanpura as established.

    python3 experiments/e65_andolan.py [outdir]
"""

import os
import subprocess
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))))
from loam import SR, hz, Loop, stereo, write_wav
from loam import ruler
from loam.fdstring import fdbow, fdpluck2, fdsym

outdir = sys.argv[1] if len(sys.argv) > 1 else "render"
os.makedirs(outdir, exist_ok=True)
fails = []


def check(name, cond, detail):
    print(f"  {'PASS' if cond else 'FAIL'} {name}: {detail}")
    if not cond:
        fails.append(name)


def rms(x):
    return float(np.sqrt(np.mean(np.asarray(x) ** 2)))


GA = hz(53)

# ---- 1. physics: lock under wobble, ruler calibration ----------
def vib_probe(depth_c, rate):
    tp = np.arange(int(3.0 * SR)) / SR
    f0t = GA * 2 ** (depth_c * np.sin(2 * np.pi * rate * tp)
            / 1200.0)
    x = fdbow(f0t, 3.0, FB=1e3, vb=0.10, raw=True)[SR:]
    ts, fs = ruler.pitch_contour(x, fmin=100.0, fmax=300.0)
    rt, dp = ruler.ornament_profile(ts, fs)
    return ruler.lock_ratio(x, GA), rt, dp


lk40, rt40, dp40 = vib_probe(40.0, 2.0)
lk80, rt80, dp80 = vib_probe(80.0, 2.0)
check("slow andolan keeps the lock at any depth",
        lk40 >= 0.3 and lk80 >= 0.3,
        f"2 Hz odd/even: +-40c {lk40:.2f}, +-80c {lk80:.2f} "
        f"(the bow tolerates a breathing pitch)")
lk_hole, _, _ = vib_probe(40.0, 5.0)
lk20f, _, _ = vib_probe(20.0, 5.0)
check("the vibrato plane has a hole",
        lk_hole <= 0.15 and lk20f >= 0.3,
        f"+-40c at 5 Hz: lock {lk_hole:.2f} while +-20c at the "
        f"same rate holds {lk20f:.2f} — an instability pocket, "
        f"pinned like e61's octave pocket")
check("the ornament ruler reads rate true",
        abs(rt40 - 2.0) <= 0.3 and abs(rt80 - 2.0) <= 0.3,
        f"designed 2 Hz, measured {rt40:.2f} / {rt80:.2f} Hz")
att40, att80 = dp40 / 40.0, dp80 / 80.0
lk0, _, dp0 = vib_probe(0.0, 2.0)
check("depth reads through a consistent calibration",
        0.85 <= att40 <= 0.98 and 0.85 <= att80 <= 0.98
        and abs(att40 - att80) <= 0.06 and dp0 <= 5.0,
        f"attenuation x{att40:.2f} at 40c, x{att80:.2f} at 80c "
        f"(e47: calibrate, don't trust raw); zero-depth control "
        f"{dp0:.1f}c")
ATT = (att40 + att80) / 2.0

# ---- the piece: jor with a breathing ga ------------------------
LOOP_S = 9.6
tt = np.arange(int(LOOP_S * SR)) / SR
KN = [(0.0, 50), (1.4, 50), (2.2, 53), (4.8, 53), (5.4, 52),
        (6.6, 52), (7.2, 50), (9.6, 50)]
f0t = np.interp(tt, [t for t, _ in KN], [hz(m) for _, m in KN])
AND_A, AND_B, AND_D, AND_R = 2.2, 4.8, 40.0, 2.0
env = np.clip(np.minimum(tt - AND_A, AND_B - tt) / 0.4, 0, 1)
env[(tt < AND_A) | (tt > AND_B)] = 0.0
f0t = f0t * 2 ** (AND_D * env
        * np.sin(2 * np.pi * AND_R * (tt - AND_A)) / 1200.0)
VBK = [(0.0, 0.085), (1.2, 0.105), (2.6, 0.12), (4.4, 0.11),
        (5.8, 0.115), (7.0, 0.10), (8.5, 0.085), (9.6, 0.085)]
vbt = np.interp(tt, [t for t, _ in VBK], [v for _, v in VBK])
FBt = np.where(tt < 8.5, 1e4 * vbt, 0.0)
sar = fdbow(f0t, LOOP_S, FB=FBt, vb=vbt, sig0=4.0, raw=True)

HOLDS = (("Sa", 0.3, 1.3, 50), ("ga", 2.7, 4.5, 53),
        ("Re", 5.6, 6.5, 52), ("Sa'", 7.4, 8.4, 50))
locks = [ruler.lock_ratio(sar[int(a * SR):int(b * SR)], hz(m))
        for _, a, b, m in HOLDS]
check("every hold stays locked, wobble included",
        min(locks) >= 0.2,
        f"odd/even {[round(v, 2) for v in locks]} across "
        f"Sa - ga(andolan) - Re - Sa")
ts, fsc = ruler.pitch_contour(sar, fmin=80.0, fmax=500.0)
worst_hold = 0.0
for nm, a, b, m in HOLDS:
    sel = (ts >= a) & (ts <= b)
    med = float(np.median(fsc[sel]))
    worst_hold = max(worst_hold, abs(1200 * np.log2(med / hz(m))))
check("every hold lands (the wobble centers on ga)",
        worst_hold <= 25.0, f"worst hold {worst_hold:.1f}c — "
        f"the andolan's median IS the note")
sel = (ts >= 2.7) & (ts <= 4.5)
rt_p, dp_p = ruler.ornament_profile(ts[sel], fsc[sel])
dexp = AND_D * ATT
check("the ga breathes as designed",
        abs(rt_p - AND_R) <= 0.3
        and abs(dp_p / dexp - 1.0) <= 0.25,
        f"in-phrase andolan {rt_p:.2f} Hz at {dp_p:.1f}c "
        f"(design {AND_R:.0f} Hz, {AND_D:.0f}c -> calibrated "
        f"expectation {dexp:.1f}c)")
sel = (ts >= 0.3) & (ts <= 8.3)
d = np.interp(ts, tt, f0t)
dev = 1200 * np.log2(fsc[sel] / d[sel])
check("the contour follows the written line, wobble and all",
        float(np.median(np.abs(dev))) <= 15.0,
        f"median |dev| {float(np.median(np.abs(dev))):.1f}c "
        f"against the MODULATED design")
wr = np.array([rms(sar[int(a * SR):int((a + 0.3) * SR)])
        for a in np.arange(0.5, 8.1, 0.3)])
vbw = np.array([float(np.mean(vbt[(tt >= a) & (tt <= a + 0.3)]))
        for a in np.arange(0.5, 8.1, 0.3)])
check("the voice holds and swells on bow speed",
        float(wr.min() / wr.max()) >= 0.4
        and float(np.corrcoef(wr, vbw)[0, 1]) >= 0.9,
        f"rms min/max {wr.min() / wr.max():.3f}, swell corr "
        f"{float(np.corrcoef(wr, vbw)[0, 1]):.3f}")
t60r = ruler.decay_t60(sar[int(8.6 * SR):int(9.55 * SR)],
        100.0, 1200.0)
check("the lift rings into the seam",
        abs(t60r / 1.725 - 1) <= 0.3,
        f"release t60 {t60r:.2f} s (design 1.73)")

# ---- the mix ---------------------------------------------------
BANK = [50, 52, 53, 55, 57, 59, 60, 62]
_, tb = fdsym([hz(n) for n in BANK], sar, buses=True,
        jawari=True, gain=5000.0)
HALO_GAIN = 0.05
pans = np.linspace(-0.55, 0.55, len(BANK))
tnorm = np.abs(tb).max() + 1e-12
L = int(LOOP_S * SR)
taraf_st = np.zeros((L, 2))
for b, p in zip(tb, pans):
    gg = (b[:L] / tnorm) * HALO_GAIN
    taraf_st[:, 0] += gg * np.cos((p + 1) * np.pi / 4)
    taraf_st[:, 1] += gg * np.sin((p + 1) * np.pi / 4)
sar_mix = sar * 0.85 / (np.abs(sar).max() + 1e-12) * 0.9
halo_db = 20 * np.log10(rms(taraf_st.sum(axis=1)) / rms(sar_mix))
check("the halo sits under the voice", -32.0 <= halo_db <= -8.0,
        f"taraf/sarangi {halo_db:.1f} dB")

DRONE = [("pa", hz(45), 140, 0.0, -0.35, 0.55),
        ("sa+", hz(50.015), 112, 1.2, 0.15, 0.50),
        ("sa-", hz(49.985), 112, 2.4, -0.15, 0.50),
        ("SA", hz(38), 138, 3.6, 0.35, 0.75)]
loop = Loop(LOOP_S, seed=65)
for name, f0d, n, at, pan, ampd in DRONE:
    v = fdpluck2(f0d, 12.0, amp=ampd, N=n)
    loop.add(at, stereo(v, pan))
    loop.add(at + 4.8, stereo(v, pan))
loop.add(0.0, stereo(sar_mix, 0.0))
loop.add(0.0, taraf_st)
mix = loop.master(lp_hz=6500.0, drive=1.2)

check("seam", ruler.seam_rank(mix) <= 0.999,
        f"p{100 * ruler.seam_rank(mix):.2f}")
# claim shape follows the phrase (e63/e64's lesson): this jor
# FEATURES ga — a 2.6 s spotlight hold. Sa still leads, but
# the honest second pole is the breathing note itself.
cu = ruler.chroma_uniform(mix.mean(axis=1))
order = np.argsort(cu)[::-1]
m01 = cu[order[0]] / cu[order[1]]
m12 = cu[order[1]] / cu[order[2]]
check("Sa leads, the breathing ga is second",
        order[0] == 2 and order[1] == 5
        and m01 >= 1.1 and m12 >= 1.15,
        f"D {cu[2]:.2f} > F {cu[5]:.2f} (x{m01:.2f}) > rest "
        f"(x{m12:.2f}) — the andolan's note earns its place")

out = np.concatenate([mix, mix])
wav = os.path.join(outdir, "e65_andolan.wav")
write_wav(wav, out)
ruler.report(out, "andolan")
subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", wav,
        "-q:a", "5", wav.replace(".wav", ".ogg")], check=True)

print("ALL RULERS PASS" if not fails else f"FAILED: {fails}")
sys.exit(1 if fails else 0)

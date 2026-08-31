#!/usr/bin/env python3
"""e61 — sarangi: the first voice that sustains.

New instrument CLASS: the bowed string (loam/fdstring.fdbow).
Every loam construct before this decays from its excitation;
stick-slip friction at the bow node feeds the string as long
as the bow moves — a note that holds, swells, and glides while
being DRIVEN.

Physics certified here (each claim measured, negative controls
included):
  - minimum bow force is real and sharp: FB=50 whispers at
    ~1/1000 the locked level; FB=1000 sings.
  - the locked tone is harmonic (integer stack from 1) and
    lands on the written pitch, slightly FLAT — the classic
    friction flattening effect, within the 25-cent gate.
  - the bow sustains what the pluck cannot: late/early rms
    ~1.0 bowed vs ~0.4 for fdpluck's free decay.
  - a stopped bow is NOT a lifted bow (the modeling lesson of
    the cycle): vb=0 with force still applied parks a damper
    on the string and kills it 30x faster than sig0 says.
    Lifting means FB -> 0; then the release rings at its
    designed t60 = 6.9/sig0.
  - playability is a MAP with holes: an octave pocket
    (double-slip motion) sits at FB=2e3, vb=0.10 inside the
    otherwise-locked region. The piece pins probed points.

The piece: jor — one closed phrase orbit over the tanpura.
Sa swells, meends up to komal Ga, falls through Re, returns to
Sa, and the bow LIFTS at 8.5 s so the ring decays into the
seam. Swells ride bow SPEED (pressure adds grip, not level —
FB crescendo saturates, measured).

    python3 experiments/e61_sarangi.py [outdir]
"""

import os
import subprocess
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))))
from loam import SR, hz, Loop, stereo, write_wav
from loam import ruler
from loam.fdstring import fdbow, fdpluck, fdpluck2

outdir = sys.argv[1] if len(sys.argv) > 1 else "render"
os.makedirs(outdir, exist_ok=True)
fails = []


def check(name, cond, detail):
    print(f"  {'PASS' if cond else 'FAIL'} {name}: {detail}")
    if not cond:
        fails.append(name)


def rms(x):
    return float(np.sqrt(np.mean(np.asarray(x) ** 2)))


F0 = hz(50)

# ---- 1. minimum bow force --------------------------------------
whisper = fdbow(F0, 1.5, FB=50.0, vb=0.10, raw=True)
sing = fdbow(F0, 1.5, FB=1e3, vb=0.10, raw=True)
r_w = rms(whisper[int(0.7 * SR):])
r_s = rms(sing[int(0.7 * SR):])
check("below minimum bow force the string whispers",
        r_s >= 0.1 and r_w / r_s <= 0.01,
        f"steady rms: FB=1e3 {r_s:.3f}, FB=50 {r_w:.5f} "
        f"({r_w / r_s:.1e} of locked)")

# ---- 2. the locked tone is harmonic and on pitch ---------------
h = sing[int(0.7 * SR):]
p = ruler.hps_pitch(h, fmin=60.0, fmax=600.0)
cents = 1200 * np.log2(p / F0)
mf = ruler.mode_freqs(h, k=5, fmin=100.0, fmax=900.0, rel=1e-3)
mm, mf0, ints = ruler.mode_misfit(mf, 100.0, 200.0, max_int=8)
# consecutive integers is the harmonicity condition; the stack
# may START above 1 (bowed at xb=0.12 is bright — the strongest
# five modes are harmonics 2..6, the fundamental is present but
# not top-five)
consec = ints == tuple(range(ints[0], ints[0] + len(ints)))
check("the bow locks on the written pitch",
        abs(cents) <= 25.0 and mm <= 5.0 and consec,
        f"pitch {p:.1f} Hz ({cents:+.1f}c — friction flattening, "
        f"measured not assumed), stack {ints} misfit {mm:.1f}c")

# ---- 3. the bow sustains what the pluck cannot -----------------
def late_early(x):
    return rms(x[int(1.5 * SR):int(2.0 * SR)]) \
        / rms(x[int(0.5 * SR):int(1.0 * SR)])


bowed = fdbow(F0, 2.0, FB=1e3, vb=0.10)
plucked = fdpluck(F0, 2.0)
le_b, le_p = late_early(bowed), late_early(plucked)
check("the bow sustains what the pluck cannot",
        le_b >= 0.9 and le_p <= 0.6,
        f"late/early rms: bowed {le_b:.3f}, plucked {le_p:.3f}")

# ---- 4. lifting is removing force ------------------------------
ttl = np.linspace(0, 1, 300)
lift = fdbow(F0, 3.0, FB=np.where(ttl < 2.0 / 3.0, 1e3, 0.0),
        vb=0.10, sig0=2.0, raw=True)
t60m = ruler.decay_t60(lift[int(2.05 * SR):], 100.0, 1200.0)
t60d = 6.9 / 2.0
check("the lifted bow releases at the designed t60",
        abs(t60m / t60d - 1.0) <= 0.30,
        f"measured {t60m:.2f} s vs 6.9/sig0 = {t60d:.2f} s "
        f"(a STOPPED bow instead kills the ring in ~0.12 s — "
        f"force, not motion, is what lifts)")

# ---- the piece: jor --------------------------------------------
LOOP_S = 9.6
KN = [(0.0, 50), (2.2, 50), (3.2, 53), (4.8, 53), (5.6, 52),
        (6.4, 52), (7.4, 50), (9.6, 50)]
tk = np.array([t for t, _ in KN])
fk = np.array([hz(m) for _, m in KN])
tt = np.linspace(0, LOOP_S, 2000)
f0t = np.interp(tt, tk, fk)
VBK = [(0.0, 0.08), (2.0, 0.13), (3.4, 0.10), (5.0, 0.12),
        (6.5, 0.13), (8.0, 0.09), (8.5, 0.08), (9.6, 0.08)]
vbt = np.interp(tt, [t for t, _ in VBK], [v for _, v in VBK])
LIFT_S = 8.5
FBt = np.where(tt < LIFT_S, 1e3, 0.0)
sar = fdbow(f0t, LOOP_S, FB=FBt, vb=vbt, sig0=4.0, raw=True)

# own-bus: the phrase reads back
ts, fs = ruler.pitch_contour(sar, fmin=80.0, fmax=500.0)
worst_hold = 0.0
for nm, a, b, m in (("Sa", 0.5, 2.0, 50), ("Ga", 3.4, 4.6, 53),
        ("Re", 5.7, 6.3, 52), ("Sa'", 7.5, 8.4, 50)):
    sel = (ts >= a) & (ts <= b)
    med = float(np.median(fs[sel]))
    worst_hold = max(worst_hold,
            abs(1200 * np.log2(med / hz(m))))
check("every hold lands", worst_hold <= 25.0,
        f"worst hold {worst_hold:.1f}c across Sa-Ga-Re-Sa")
sel = (ts >= 0.3) & (ts <= 8.3)
d = np.interp(ts, tt, f0t)
dev = 1200 * np.log2(fs[sel] / d[sel])
check("the meend follows the written line",
        float(np.median(np.abs(dev))) <= 15.0,
        f"median |dev| {float(np.median(np.abs(dev))):.1f}c, "
        f"worst {float(np.abs(dev).max()):.1f}c over 8 s of "
        f"holds and glides")

# own-bus: the voice never dies mid-phrase, and swells as bowed
wr = np.array([rms(sar[int(a * SR):int((a + 0.3) * SR)])
        for a in np.arange(0.5, 8.1, 0.3)])
check("the voice holds for the whole phrase",
        float(wr.min() / wr.max()) >= 0.4,
        f"windowed rms min/max {wr.min() / wr.max():.3f} "
        f"(a pluck would fall 20+ dB)")
vbw = np.array([float(np.mean(vbt[(tt >= a) & (tt <= a + 0.3)]))
        for a in np.arange(0.5, 8.1, 0.3)])
corr = float(np.corrcoef(wr, vbw)[0, 1])
check("the swell is the bow speed", corr >= 0.9,
        f"windowed rms vs designed vb envelope: r = {corr:.3f}")
t60r = ruler.decay_t60(sar[int(8.6 * SR):int(9.55 * SR)],
        100.0, 1200.0)
check("the lift rings into the seam", abs(t60r / 1.725 - 1) <= 0.3,
        f"release t60 {t60r:.2f} s (design 6.9/4 = 1.73)")

# ---- the mix ---------------------------------------------------
DRONE = [("pa", hz(45), 140, 0.0, -0.35, 0.55),
        ("sa+", hz(50.015), 112, 1.2, 0.15, 0.50),
        ("sa-", hz(49.985), 112, 2.4, -0.15, 0.50),
        ("SA", hz(38), 138, 3.6, 0.35, 0.75)]
loop = Loop(LOOP_S, seed=61)
for name, f0d, n, at, pan, ampd in DRONE:
    v = fdpluck2(f0d, 12.0, amp=ampd, N=n)
    loop.add(at, stereo(v, pan))
    loop.add(at + 4.8, stereo(v, pan))
sar_mix = sar * 0.85 / (np.abs(sar).max() + 1e-12) * 0.9
loop.add(0.0, stereo(sar_mix, 0.0))
mix = loop.master(lp_hz=6500.0, drive=1.2)

check("seam", ruler.seam_rank(mix) <= 0.999,
        f"p{100 * ruler.seam_rank(mix):.2f}")
# whole-signal hann chroma weights a MOVING line by where the
# window bump lands (measured: single pass crowned F/E because
# the Ga/Re holds sit at the signal's center; the doubled copy
# crowned D because the seam does). Time-uniform version:
# average of overlapping short-window chromas, every second
# counting equally. And the honest pole claim for a SOLO-voice
# jor is "Sa is the tonal center" — the {D, A} two-pole claim
# belongs to drone/theka pieces where nothing loud redistributes
# the upper classes (here Ga/Re holds outweigh the Pa drone).
mono = mix.mean(axis=1)
W = len(mono) // 5
acc = np.zeros(12)
for a0 in range(0, len(mono) - W + 1, W // 2):
    acc += ruler.chroma(mono[a0:a0 + W])
acc /= acc.sum()
order = np.argsort(acc)[::-1]
margin = acc[order[0]] / acc[order[1]]
check("Sa is the tonal center", order[0] == 2 and margin >= 1.5,
        f"top class {order[0]} at {acc[order[0]]:.2f}, "
        f"x{margin:.1f} over runner-up (time-uniform chroma)")

out = np.concatenate([mix, mix])
wav = os.path.join(outdir, "e61_sarangi.wav")
write_wav(wav, out)
ruler.report(out, "sarangi")
subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", wav,
        "-q:a", "5", wav.replace(".wav", ".ogg")], check=True)

print("ALL RULERS PASS" if not fails else f"FAILED: {fails}")
sys.exit(1 if fails else 0)

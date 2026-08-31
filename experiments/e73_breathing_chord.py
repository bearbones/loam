#!/usr/bin/env python3
"""e73 — the breathing chord: polyrhythm with no onsets.

Brand-new territory: RHYTHM MADE ONLY OF INTERFERENCE. Four
held voices — Sa and ga on the treble bow, Pa- and ni- on the
heavy bow (e71's two windows) — form a tetrad that never
articulates a single attack after its entries. All the motion
is written beat: two coincidence bands (Sa h3 / Pa- h4 near
440 Hz; ga h3 / ni- h4 near 523 Hz) carry two written rates
in exact 2:3 — and both rates are chosen as INTEGER CYCLES
PER LOOP (18 and 27 in 9.6 s), so the interference pattern
itself closes at the seam. A chord that breathes in
polyrhythm; the breathing is seam-locked by construction.

What the cycle taught (each pinned as a gate):
  - THE BOW CANNOT CREEP FROM ZERO: an entry that ramps vb
    0 -> 0.085 crosses the bow's dead zone and the string
    never locks (fund 0.000 on BOTH grids) — the certified
    attack must STEP to 0.085 at entry. Found as a confound:
    the first probe changed attack and grid in one edit and
    blamed the grid; the script's own paired control unmasked
    it (native-grid solo Sa with a step attack is fine —
    fund 0.52). One variable per probe, or the control
    catches you.
  - THE TUNING KNOB IS NOTE-DEPENDENT: ni-'s line converges
    to 0.003 Hz in four iterations; Pa-'s line jitters in a
    ~0.05 Hz band under sub-cent command steps and bottoms
    out ~8x coarser. Iterate with a best-pick, not a formula.
  - THE ONSET RULER CANNOT HEAR THIS RHYTHM: beating and
    still chords read the SAME onset count (the detector
    fires on bow jitter, not interference). The env-spectrum
    integer bin is the honest ruler for onset-free rhythm.

The still control: same four voices, same envelopes, basses
retuned ONTO the melody lines — every rhythm claim is paired
against a chord that differs only in the written separations.

    python3 experiments/e73_breathing_chord.py [outdir]
"""

import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))))
from loam import SR, hz, Loop, stereo, write_wav
from loam import ruler
from loam.fdstring import fdbow, fdsym

outdir = sys.argv[1] if len(sys.argv) > 1 else "render"
os.makedirs(outdir, exist_ok=True)
fails = []


def check(name, cond, detail):
    print(f"  {'PASS' if cond else 'FAIL'} {name}: {detail}")
    if not cond:
        fails.append(name)


def rms(x):
    return float(np.sqrt(np.mean(np.asarray(x) ** 2)))


def w(x, a, b):
    return x[int(a * SR):int(b * SR)]


LOOP_S = 9.6
L = int(LOOP_S * SR)
tt = np.arange(L) / SR
RA, RB = 18 / LOOP_S, 27 / LOOP_S       # integer cycles/loop


def voice(f0, k, vtop, te, N=0):
    """Certified attack from entry te: STEP to vb=0.085 (a slow
    creep from zero crosses the bow's dead zone and never
    locks), shelf to vtop, lift FB at 8.5."""
    if te <= 0:
        vb = np.interp(tt, [0.0, 0.6, 8.5, 9.6],
                [0.085, vtop, vtop, 0.085])
    else:
        vb = np.interp(tt, [0.0, te - 1e-3, te, te + 0.6,
                8.5, 9.6], [0.0, 0.0, 0.085, vtop, vtop, 0.085])
    FB = np.where(tt >= 8.5, 0.0, k * vb)
    return fdbow(f0, LOOP_S, FB=FB, vb=vb, sig0=4.0, raw=True,
            N=N)


def line_spread(x, lo, hi):
    thirds = [(1.5, 3.8), (3.8, 6.1), (6.1, 8.4)]
    fs = [ruler.partial_freq(w(x, a, b), lo, hi)
            for a, b in thirds]
    return max(fs) - min(fs)


print("== the voices ==")

# negative control: same note, same grid, attack CREEPS from
# zero instead of stepping to 0.085
vb_creep = np.interp(tt, [0.0, 0.4, 1.0, 8.5, 9.6],
        [0.0, 0.085, 0.105, 0.105, 0.085])
sa_creep = fdbow(hz(50), LOOP_S, FB=np.where(tt >= 8.5, 0.0,
        1e4 * vb_creep), vb=vb_creep, sig0=4.0, raw=True, N=96)
sa = voice(hz(50), 1e4, 0.105, 0.4, N=96)
spread_p = line_spread(sa, 434.0, 447.0)
check("the bow cannot creep from zero",
        ruler.fund_presence(w(sa_creep, 2.0, 8.4), hz(50))
            <= 0.02
        and ruler.fund_presence(w(sa, 2.0, 8.4), hz(50)) >= 0.08
        and spread_p <= 0.2,
        f"vb ramped 0 -> 0.085 over the entry: fund "
        f"{ruler.fund_presence(w(sa_creep, 2.0, 8.4), hz(50)):.3f}"
        f" — the string never speaks. Same note, same grid, "
        f"STEP to 0.085: fund "
        f"{ruler.fund_presence(w(sa, 2.0, 8.4), hz(50)):.2f}, "
        f"h3 steady to {spread_p:.2f} Hz. The dead zone under "
        f"the certified attack is real, and entries must jump "
        f"over it")

ga = voice(hz(53), 1e4, 0.105, 1.2)
f3sa = ruler.partial_freq(w(sa, 1.5, 8.4), 434.0, 447.0)
f3ga = ruler.partial_freq(w(ga, 2.0, 8.4), 516.0, 531.0)


def tune(f3, R, wlo, te, c0, label):
    c, c_prev, s_prev = c0, None, None
    best = (9.0, None, None, None)
    for it in range(5):
        b = voice(c, 4e4, 0.10, te)
        f4 = ruler.partial_freq(w(b, wlo, 8.4), 4 * c * 0.99,
                4 * c * 1.01)
        sep = f3 - f4
        err = sep - R
        if abs(err) < best[0]:
            best = (abs(err), b, c, sep)
        if abs(err) <= 0.008:
            break
        if c_prev is None:
            dc = err / 4
        else:
            sl = (sep - s_prev) / (c - c_prev)
            dc = -err / sl if abs(sl) > 1e-6 else err / 4
        c_prev, s_prev = c, sep
        c += dc
    return best


bestA = tune(f3sa, RA, 1.5, 0.0, (f3sa - RA) / 4 / 0.9996, "A")
bestB = tune(f3ga, RB, 2.0, 0.8, (f3ga - RB) / 4 / 0.996, "B")
pa, cA, sepA = bestA[1], bestA[2], bestA[3]
ni, cB, sepB = bestB[1], bestB[2], bestB[3]
check("the tuning knob is note-dependent",
        bestB[0] <= 0.01 and 0.01 <= bestA[0] <= 0.035
        and bestA[0] >= 3 * bestB[0],
        f"ni- converges to {bestB[0] * 1000:.0f} mHz; Pa- "
        f"bottoms out at {bestA[0] * 1000:.0f} mHz over the "
        f"same iterations — Pa-'s line jitters under sub-cent "
        f"command steps where ni-'s follows smoothly. "
        f"Iterate with a best-pick, not a formula")
check("the two-shot score generalizes",
        abs((sepA - RA) * LOOP_S) <= 0.35
        and abs((sepB - RB) * LOOP_S) <= 0.10,
        f"written 18 and 27 cycles/loop; lines land "
        f"{(sepA - RA) * LOOP_S:+.2f} and "
        f"{(sepB - RB) * LOOP_S:+.2f} cycles of drift at the "
        f"seam")

print("== the rhythm ==")

sub = sum(v / np.abs(v).max() for v in (sa, ga, pa, ni))
brA = ruler.beat_profile(w(sub, 1.5, 8.4), 400.0, 480.0,
        trend_s=2.0, min_rate=1.0)
brB = ruler.beat_profile(w(sub, 2.0, 8.4), 480.0, 570.0,
        trend_s=1.5, min_rate=1.5)
check("two written rates, one chord",
        abs(brA[0] / RA - 1) <= 0.05 and brA[1] >= 2.5
        and abs(brB[0] / RB - 1) <= 0.05 and brB[1] >= 2.5,
        f"band A breathes at {brA[0]:.2f} Hz ({brA[1]:.1f} dB) "
        f"against written 1.875; band B at {brB[0]:.2f} Hz "
        f"({brB[1]:.1f} dB) against 2.8125")
check("the breathing is two against three",
        1.45 <= brB[0] / brA[0] <= 1.55,
        f"measured ratio {brB[0] / brA[0]:.3f} — a 2:3 "
        f"polyrhythm carried entirely by interference")


def env_crown(x, lo, hi):
    env = ruler.band_env(x, lo, hi, 0.05)[:192]
    le = np.log(env + 1e-12)
    k = 41
    pad = np.concatenate([le[:k][::-1], le, le[-k:][::-1]])
    tr = np.convolve(pad, np.ones(k) / k, "same")[k:-k]
    sp = np.abs(np.fft.rfft((le - tr) * np.hanning(len(le))))
    return int(np.argmax(sp[8:70])) + 8


check("the breathing closes at the seam",
        env_crown(sub, 400.0, 480.0) == 18
        and env_crown(sub, 480.0, 570.0) == 27,
        f"one-loop envelope spectra crown at bins "
        f"{env_crown(sub, 400.0, 480.0)} and "
        f"{env_crown(sub, 480.0, 570.0)} — exactly the written "
        f"integer cycles: the interference pattern is itself "
        f"seamless")

best0A = tune(f3sa, 0.0, 1.5, 0.0, cA + sepA / 4, "A0")
best0B = tune(f3ga, 0.0, 2.0, 0.8, cB + sepB / 4, "B0")
sub0 = sum(v / np.abs(v).max()
        for v in (sa, ga, best0A[1], best0B[1]))
d0A = ruler.beat_profile(w(sub0, 1.5, 8.4), 400.0, 480.0,
        trend_s=2.0, min_rate=1.0)[1]
d0B = ruler.beat_profile(w(sub0, 2.0, 8.4), 480.0, 570.0,
        trend_s=1.5, min_rate=1.5)[1]
check("the still control does not breathe",
        d0A <= 1.2 and d0B <= 1.2,
        f"basses retuned onto the melody lines: band depths "
        f"{d0A:.1f}/{d0B:.1f} dB vs {brA[1]:.1f}/{brB[1]:.1f} "
        f"beating — same voices, same envelopes, no rhythm")

n_beat = len(ruler.onset_times(w(sub, 1.5, 8.4)))
n_still = len(ruler.onset_times(w(sub0, 1.5, 8.4)))
check("the onset ruler cannot hear this rhythm",
        abs(n_beat - n_still) <= 0.2 * max(n_beat, n_still),
        f"onset counts: beating {n_beat}, still {n_still} — "
        f"the detector fires on bow jitter either way and the "
        f"interference is invisible to it. Onset-free rhythm "
        f"lives in the envelope spectrum, not the onset list")

print("== the chord ==")

fp = {nm: ruler.fund_presence(w(v, 2.0, 8.4), f)
        for nm, v, f in (("sa", sa, hz(50)), ("ga", ga, hz(53)),
            ("pa", pa, cA), ("ni", ni, cB))}
check("two windows, two voices",
        min(fp["pa"], fp["ni"]) >= 0.6
        and max(fp["sa"], fp["ga"]) <= 0.3
        and min(fp["pa"], fp["ni"])
            >= 5 * max(fp["sa"], fp["ga"]),
        f"bass fund {fp['pa']:.2f}/{fp['ni']:.2f} vs treble "
        f"{fp['sa']:.2f}/{fp['ga']:.2f} — the dark voices crown "
        f"their fundamentals 5x over the h2-crowned trebles")
t60s = [ruler.decay_t60((v / np.abs(v).max())
        [int(8.6 * SR):int(9.55 * SR)], 100.0, 1200.0)
        for v in (sa, ga, pa, ni)]
check("four voices obey the release law",
        all(abs(t / 1.725 - 1) <= 0.3 for t in t60s),
        f"release t60 {'/'.join(f'{t:.2f}' for t in t60s)} s "
        f"(design 1.73)")

# ---- the mix: no tanpura — the tetrad IS the drone ------------
V = [(sa, 0.30, 0.25), (ga, 0.26, 0.45), (pa, 0.30, -0.25),
        (ni, 0.26, -0.45)]
sar = sum(v / np.abs(v).max() * g for v, g, _ in V)
BANK = [50, 52, 53, 55, 57, 59, 60, 62]
_, tb = fdsym([hz(n) for n in BANK], sar / np.abs(sar).max(),
        buses=True, jawari=True, gain=5000.0)
pans = np.linspace(-0.55, 0.55, len(BANK))
tnorm = np.abs(tb).max() + 1e-12
taraf_st = np.zeros((L, 2))
for b_, p in zip(tb, pans):
    gg = (b_[:L] / tnorm) * 0.05
    taraf_st[:, 0] += gg * np.cos((p + 1) * np.pi / 4)
    taraf_st[:, 1] += gg * np.sin((p + 1) * np.pi / 4)
norm = np.abs(sar).max() + 1e-12
halo_db = 20 * np.log10(rms(taraf_st.sum(axis=1))
        / rms(sar * 0.85 / norm * 0.9))
check("the halo sits under the chord",
        -32.0 <= halo_db <= -8.0,
        f"taraf/tetrad {halo_db:.1f} dB")

loop = Loop(LOOP_S, seed=73)
for v, g, pan in V:
    loop.add(0.0, stereo(v / np.abs(v).max() * g * 0.85
            / norm * 0.9, pan))
loop.add(0.0, taraf_st)
mix = loop.master(lp_hz=6500.0, drive=1.2)
mono = mix.mean(axis=1)

mA = ruler.beat_profile(w(mono, 1.5, 8.4), 400.0, 480.0,
        trend_s=2.0, min_rate=1.0)
mB = ruler.beat_profile(w(mono, 2.0, 8.4), 480.0, 570.0,
        trend_s=1.5, min_rate=1.5)
check("the listener hears both breaths",
        abs(mA[0] / RA - 1) <= 0.05 and mA[1] >= 2.5
        and abs(mB[0] / RB - 1) <= 0.05 and mB[1] >= 2.0
        and env_crown(mono, 400.0, 480.0) == 18
        and env_crown(mono, 480.0, 570.0) == 27,
        f"mastered mix: {mA[0]:.2f} Hz {mA[1]:.1f} dB and "
        f"{mB[0]:.2f} Hz {mB[1]:.1f} dB, envelope crowns still "
        f"at bins 18/27 — the polyrhythm survives halo and "
        f"master")
check("seam", ruler.seam_rank(mix) <= 0.999,
        f"p{100 * ruler.seam_rank(mix):.2f}")
cu = ruler.chroma_uniform(mono)
order = np.argsort(cu)[::-1].tolist()
check("the tetrad owns the chroma",
        set(order[:3]) == {9, 2, 0} and 5 in order[:5],
        f"Pa {cu[9]:.2f}, Sa {cu[2]:.2f}, ni {cu[0]:.2f} lead "
        f"with ga at {cu[5]:.2f} in the top five — all four "
        f"chord classes above every unsung one but Re's taraf "
        f"({cu[4]:.2f})")

out = np.concatenate([mix, mix])
wav = os.path.join(outdir, "e73_breathing_chord.wav")
write_wav(wav, out)
ruler.report(out, "breathing_chord")

if fails:
    print("FAILED RULERS:", fails)
    sys.exit(1)
print("ALL RULERS PASS")

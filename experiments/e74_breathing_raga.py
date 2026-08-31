#!/usr/bin/env python3
"""e74 — the breathing raga: 2:3:4, the breath grows harmonics.

Refinement of e73: the breathing chord, completed to the full
Kafi hexad. Six held voices — Sa, Re, ga on the treble bow;
Pa-, Dha-, ni- on the heavy bow — and THREE coincidence bands
(Sa h3/Pa- h4 near 440; Re h3/Dha- h4 near 494; ga h3/ni- h4
near 523), each carrying a written beat rate in the harmonic
proportion 2:3:4 — 18, 27 and 36 integer cycles per loop.
The rhythm ratios mirror the pitch ratios of the raga's own
intervals: the chord breathes a chord, and every breath
closes at the seam by construction.

Measured: envelope spectra crown at EXACTLY bins 18/27/36 in
the six-voice sub-mix and again in the mastered mix; achieved
line separations hold the harmonic proportion to 0.5%
(1.507 : 1.332 : 2.007 against 3/2, 4/3, 2). The still
control (all three basses retuned onto their melody lines)
breathes at 1.6/0.2/1.1 dB against 7.1/5.6/4.8.

Boundaries pinned:
  - THE JITTER IS PA-SPECIFIC: Dha- and ni- converge to
    2 mHz in 3-4 iterations; Pa-'s line sign-flips around its
    target and bottoms out ~3x coarser. One bass note of
    three wanders — a fine-structure map of the heavy bow is
    an open thread with a face now.
  - CHROMA COUNTS PARTIALS, NOT NOTES: the dark basses crown
    h1 but sing a strong h3 that octave-folds a FIFTH UP —
    Dha-'s h3 (370 Hz) lands on class 6 above the sung ga's
    class 5, and Pa-'s h3 (330 Hz) inflates Re's class. The
    hexad's five other classes lead the chroma, but ga trails
    a class nobody sang. chroma_uniform is register-blind by
    design; read it with the lattice in hand.

    python3 experiments/e74_breathing_raga.py [outdir]
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
RA, RC, RB = 18 / LOOP_S, 27 / LOOP_S, 36 / LOOP_S
BANDS = {"A": (425.0, 458.0), "C": (478.0, 508.0),
        "B": (510.0, 542.0)}


def voice(f0, k, vtop, te, N=0):
    if te <= 0:
        vb = np.interp(tt, [0.0, 0.6, 8.5, 9.6],
                [0.085, vtop, vtop, 0.085])
    else:
        vb = np.interp(tt, [0.0, te - 1e-3, te, te + 0.6,
                8.5, 9.6], [0.0, 0.0, 0.085, vtop, vtop, 0.085])
    FB = np.where(tt >= 8.5, 0.0, k * vb)
    return fdbow(f0, LOOP_S, FB=FB, vb=vb, sig0=4.0, raw=True,
            N=N)


def tune(f3v, R, te, c0, maxit=5):
    """Best-pick iteration onto a target separation (e73)."""
    c, c_prev, s_prev = c0, None, None
    best = (9.0, None, None, None)
    for it in range(maxit):
        b = voice(c, 4e4, 0.10, te)
        f4 = ruler.partial_freq(w(b, 2.2, 8.4), 4 * c * 0.99,
                4 * c * 1.01)
        sep = f3v - f4
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


def env_crown(x, lo, hi):
    env = ruler.band_env(x, lo, hi, 0.05)[:192]
    le = np.log(env + 1e-12)
    k = 41
    pad = np.concatenate([le[:k][::-1], le, le[-k:][::-1]])
    tr = np.convolve(pad, np.ones(k) / k, "same")[k:-k]
    sp = np.abs(np.fft.rfft((le - tr) * np.hanning(len(le))))
    return int(np.argmax(sp[8:80])) + 8


print("== the six voices ==")

sa = voice(hz(50), 1e4, 0.105, 1.0, N=96)
re = voice(hz(52), 1e4, 0.105, 1.4, N=96)
ga = voice(hz(53), 1e4, 0.105, 1.8)
f3 = {"sa": ruler.partial_freq(w(sa, 2.2, 8.4), 434.0, 447.0),
      "re": ruler.partial_freq(w(re, 2.2, 8.4), 487.0, 500.0),
      "ga": ruler.partial_freq(w(ga, 2.2, 8.4), 516.0, 531.0)}

bA = tune(f3["sa"], RA, 0.0, (f3["sa"] - RA) / 4 / 0.9996)
bC = tune(f3["re"], RC, 0.3, (f3["re"] - RC) / 4 / 0.998)
bB = tune(f3["ga"], RB, 0.6, (f3["ga"] - RB) / 4 / 0.996)
pa, dha, ni = bA[1], bC[1], bB[1]
check("the jitter is Pa-specific",
        bC[0] <= 0.004 and bB[0] <= 0.004
        and 0.004 <= bA[0] <= 0.035
        and bA[0] >= 2 * max(bC[0], bB[0]),
        f"tuning floors: Pa- {bA[0] * 1000:.0f} mHz, Dha- "
        f"{bC[0] * 1000:.0f} mHz, ni- {bB[0] * 1000:.0f} mHz — "
        f"two of three bass lines follow the command smoothly; "
        f"Pa-'s wanders. The heavy bow has fine structure, and "
        f"it is per-note")

VOICES = {"sa": sa, "re": re, "ga": ga, "pa": pa, "dha": dha,
        "ni": ni}
OWNERS = {"A": {"sa", "pa"}, "C": {"re", "dha"},
        "B": {"ga", "ni"}}


def lines_in(x, lo, hi):
    seg = w(x, 2.2, 8.4)
    X = np.abs(np.fft.rfft(seg * np.hanning(len(seg))))
    f = np.fft.rfftfreq(len(seg), 1.0 / SR)
    top = X.max()
    s = (f >= lo) & (f <= hi)
    Xs = X[s]
    n = 0
    for i in range(1, len(Xs) - 1):
        if Xs[i] > Xs[i - 1] and Xs[i] > Xs[i + 1] \
                and 20 * np.log10(Xs[i] / top) > -35.0:
            n += 1
    return n


own_ok = all(
        (lines_in(v, *BANDS[bn]) >= 1) == (nm in OWNERS[bn])
        for bn in BANDS for nm, v in VOICES.items())
check("each band holds exactly its two lines",
        own_ok,
        f"6 voices x 3 bands: every claim band contains lines "
        f"from its two design owners and from nobody else "
        f"(-35 dB floor) — no parasitic coincidences in the "
        f"hexad")

print("== the breath ==")

sub = sum(v / np.abs(v).max() for v in VOICES.values())
rates = {}
for bn, R, tr in (("A", RA, 2.0), ("C", RC, 0.9),
        ("B", RB, 0.7)):
    rates[bn] = ruler.beat_profile(w(sub, 2.2, 8.4),
            *BANDS[bn], trend_s=tr, min_rate=0.6 * R)
check("three written rates, one chord",
        all(abs(rates[bn][0] / R - 1) <= 0.06
            and rates[bn][1] >= 4.0
            for bn, R in (("A", RA), ("C", RC), ("B", RB))),
        f"bands breathe at {rates['A'][0]:.2f}/"
        f"{rates['C'][0]:.2f}/{rates['B'][0]:.2f} Hz "
        f"({rates['A'][1]:.1f}/{rates['C'][1]:.1f}/"
        f"{rates['B'][1]:.1f} dB) against written "
        f"1.875/2.8125/3.75")
sA, sC, sB = bA[3], bC[3], bB[3]
check("the breath is a harmonic series",
        abs(sC / sA / 1.5 - 1) <= 0.015
        and abs(sB / sC / (4 / 3) - 1) <= 0.015
        and abs(sB / sA / 2 - 1) <= 0.015,
        f"achieved separations {sA:.3f}/{sC:.3f}/{sB:.3f} Hz "
        f"in proportion {sC / sA:.3f} : {sB / sC:.3f} : "
        f"{sB / sA:.3f} against 3/2, 4/3, 2 — the rhythm "
        f"ratios mirror the raga's pitch ratios")
crowns = [env_crown(sub, *BANDS[bn]) for bn in "ACB"]
check("every breath closes at the seam",
        crowns == [18, 27, 36],
        f"one-loop envelope spectra crown at bins "
        f"{crowns[0]}/{crowns[1]}/{crowns[2]} — exactly the "
        f"written integer cycles, three bands at once")

pa0 = tune(f3["sa"], 0.0, 0.0, bA[2] + RA / 4, maxit=6)
dha0 = tune(f3["re"], 0.0, 0.3, bC[2] + RC / 4, maxit=3)
ni0 = tune(f3["ga"], 0.0, 0.6, bB[2] + RB / 4, maxit=3)
sub0 = sum(v / np.abs(v).max() for v in (sa, re, ga,
        pa0[1], dha0[1], ni0[1]))
stills = {}
for bn, R, tr in (("A", RA, 2.0), ("C", RC, 0.9),
        ("B", RB, 0.7)):
    stills[bn] = ruler.beat_profile(w(sub0, 2.2, 8.4),
            *BANDS[bn], trend_s=tr, min_rate=0.6 * R)[1]
check("the still control does not breathe",
        stills["A"] <= 2.0 and stills["C"] <= 1.0
        and stills["B"] <= 1.5
        and all(rates[bn][1] >= 2.5 * stills[bn]
            for bn in "ACB"),
        f"basses retuned onto the lines (residuals "
        f"{pa0[0] * 1000:.0f}/{dha0[0] * 1000:.0f}/"
        f"{ni0[0] * 1000:.0f} mHz): depths "
        f"{stills['A']:.1f}/{stills['C']:.1f}/"
        f"{stills['B']:.1f} dB vs {rates['A'][1]:.1f}/"
        f"{rates['C'][1]:.1f}/{rates['B'][1]:.1f} beating — "
        f"still-A is bounded by Pa-'s own jitter floor")

print("== the chord ==")

fp = {nm: ruler.fund_presence(w(v, 2.2, 8.4),
        {"sa": hz(50), "re": hz(52), "ga": hz(53),
         "pa": bA[2], "dha": bC[2], "ni": bB[2]}[nm])
        for nm, v in VOICES.items()}
check("three dark voices, three bright",
        min(fp["pa"], fp["dha"], fp["ni"]) >= 0.6
        and max(fp["sa"], fp["re"], fp["ga"]) <= 0.3,
        f"bass fund {fp['pa']:.2f}/{fp['dha']:.2f}/"
        f"{fp['ni']:.2f} vs treble {fp['sa']:.2f}/"
        f"{fp['re']:.2f}/{fp['ga']:.2f}")
t60s = [ruler.decay_t60((v / np.abs(v).max())
        [int(8.6 * SR):int(9.55 * SR)], 100.0, 1200.0)
        for v in VOICES.values()]
check("six voices obey the release law",
        all(abs(t / 1.725 - 1) <= 0.3 for t in t60s),
        f"release t60 {'/'.join(f'{t:.2f}' for t in t60s)} s")

# ---- the mix ---------------------------------------------------
PLACE = [("pa", 0.24, -0.45), ("dha", 0.24, -0.25),
        ("ni", 0.24, -0.08), ("sa", 0.20, 0.08),
        ("re", 0.20, 0.28), ("ga", 0.20, 0.48)]
sar = sum(VOICES[n] / np.abs(VOICES[n]).max() * g
        for n, g, _ in PLACE)
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
check("the halo sits under the hexad",
        -32.0 <= halo_db <= -8.0,
        f"taraf/voices {halo_db:.1f} dB")

loop = Loop(LOOP_S, seed=74)
for n, g, pan in PLACE:
    loop.add(0.0, stereo(VOICES[n] / np.abs(VOICES[n]).max()
            * g * 0.85 / norm * 0.9, pan))
loop.add(0.0, taraf_st)
mix = loop.master(lp_hz=6500.0, drive=1.2)
mono = mix.mean(axis=1)

mrates = {}
for bn, R, tr in (("A", RA, 2.0), ("C", RC, 0.9),
        ("B", RB, 0.7)):
    mrates[bn] = ruler.beat_profile(w(mono, 2.2, 8.4),
            *BANDS[bn], trend_s=tr, min_rate=0.6 * R)
mcrowns = [env_crown(mono, *BANDS[bn]) for bn in "ACB"]
check("the listener hears all three breaths",
        all(abs(mrates[bn][0] / R - 1) <= 0.06
            and mrates[bn][1] >= 4.0
            for bn, R in (("A", RA), ("C", RC), ("B", RB)))
        and mcrowns == [18, 27, 36],
        f"mastered mix: {mrates['A'][0]:.2f}/"
        f"{mrates['C'][0]:.2f}/{mrates['B'][0]:.2f} Hz at "
        f"{mrates['A'][1]:.1f}/{mrates['C'][1]:.1f}/"
        f"{mrates['B'][1]:.1f} dB, crowns {mcrowns} — the "
        f"2:3:4 survives halo and master")
check("seam", ruler.seam_rank(mix) <= 0.999,
        f"p{100 * ruler.seam_rank(mix):.2f}")

cu = ruler.chroma_uniform(mono)
order = np.argsort(cu)[::-1].tolist()
check("chroma counts partials, not notes",
        set(order[:5]) == {0, 2, 4, 9, 11}
        and cu[6] >= cu[5],
        f"five hexad classes lead (Pa {cu[9]:.2f}, Re "
        f"{cu[4]:.2f}, Dha {cu[11]:.2f}, ni {cu[0]:.2f}, Sa "
        f"{cu[2]:.2f}) but ga ({cu[5]:.2f}) trails class 6 "
        f"({cu[6]:.2f}) — WHICH NOBODY SANG: it is Dha-'s h3 "
        f"(370 Hz) octave-folded a fifth up, as Pa-'s h3 "
        f"inflates Re. The dark voices' twelfths are chroma "
        f"ghosts; read chroma with the lattice in hand")

out = np.concatenate([mix, mix])
wav = os.path.join(outdir, "e74_breathing_raga.wav")
write_wav(wav, out)
ruler.report(out, "breathing_raga")

if fails:
    print("FAILED RULERS:", fails)
    sys.exit(1)
print("ALL RULERS PASS")

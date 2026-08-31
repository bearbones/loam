#!/usr/bin/env python3
"""e75 — jhala: the strum that cannot be counted hums its rate.

Brand-new texture: the fast strummed climax of a sitar raga.
An 0.12 s grid, 80 slots to the 9.6 s loop — a melody pluck
every 4th slot (20-note gat line over Sa=D) and chikari
strokes on hz(62) filling the other three (da-da-ra hand
alternation: two "strings" a few cents apart, different pick
points). 8.33 strokes per second, wall to wall.

At this density the onset ruler FAILS FROM BOTH SIDES — the
boundary e73 found from below (bow jitter firing a counter)
completes from above, and it is a THRESHOLD dilemma: at
defaults the solo buses count almost true (chikari exactly
60/60) but the mix recalls only ~42% (masking merges repeated
strokes); sensitize the detector until the mix recovers
(k=0.7 finds 60/80) and that same setting makes the buses
hallucinate — jawari buzz reads as re-attacks (41/20, 71/60).
No single threshold serves both sides. And the amplitude
envelope barely ripples at the stroke rate (grid-phase ratio
~1.1) — ringing tails fill the 120 ms gaps, so beat_profile
is blind here as well. In the mastered mix even the
melody-band envelope defects: the drone's sustained 147 Hz
floods the band and its own seam-locked attack lattice
(plucks every 1.2 s = 8 cycles/loop) crowns the envelope
spectrum — energy-rhythm and attack-rhythm are different
quantities, and only the flux still points at the strum.

The honest ruler is new: ruler.flux_spectrum, the FFT of the
spectral-flux series. Counting events fails, but the
PERIODICITY of the flux survives masking and buzz alike — the
stroke rate stands as a clear line (measured 8.36 Hz against
the written 8.333, with its octave beside it) under a crown at
the 4-slot group cycle (2.08 Hz). Rhythm read as a spectrum,
not a census.

    python3 experiments/e75_jhala.py [outdir]
"""

import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))))
from loam import SR, hz, Loop, stereo, write_wav
from loam import ruler
from loam.fdstring import fdpluck2, fdsym

outdir = sys.argv[1] if len(sys.argv) > 1 else "render"
os.makedirs(outdir, exist_ok=True)
fails = []


def check(name, cond, detail):
    print(f"  {'PASS' if cond else 'FAIL'} {name}: {detail}")
    if not cond:
        fails.append(name)


def rms(x):
    return float(np.sqrt(np.mean(np.asarray(x) ** 2)))


LOOP_S = 9.6
L = int(LOOP_S * SR)
DT = 0.12                       # the strum grid
NSLOT = 80                      # 80 slots = 9.6 s exactly
R_STROKE = 1.0 / DT             # 8.333 Hz written stroke rate
R_GROUP = 1.0 / (4 * DT)        # 2.083 Hz melody-group cycle

# 20-note gat line over Sa = D (midi 50), Kafi colors
LINE = [50, 52, 53, 55, 53, 52, 50, 48, 47, 48, 50, 52,
        53, 52, 50, 48, 50, 52, 50, 50]
# chikari: one string, two hand strokes — da (down) and ra
# (up) differ in pick point, level and a few cents of detune,
# which is what lets ANY of them be found at all
CH_DA = (hz(62) * 2 ** (0.8 / 1200), 0.9, 0.38, 0.24)
CH_RA = (hz(62) * 2 ** (-3.2 / 1200), 0.9, 0.33, 0.33)


def add_wrap(buf, at, v):
    idx = (int(at * SR) + np.arange(len(v))) % len(buf)
    np.add.at(buf, idx, v)


print("== the strum ==")

cache = {}
mel = np.zeros(L)
chik = np.zeros(L)
for s in range(NSLOT):
    t = s * DT
    if s % 4 == 0:
        m = LINE[s // 4]
        if ("m", m) not in cache:
            cache[("m", m)] = fdpluck2(hz(m), 1.2, amp=1.0,
                    pick=0.28)
        add_wrap(mel, t, cache[("m", m)])
    else:
        f0, dur, amp, pick = CH_DA if s % 4 in (1, 3) else CH_RA
        key = ("c", s % 4 in (1, 3))
        if key not in cache:
            cache[key] = fdpluck2(f0, dur, amp=amp, pick=pick)
        add_wrap(chik, t, cache[key])
meln = mel / np.abs(mel).max()
chikn = chik / np.abs(chik).max()

# the gat line, read back off the melody bus itself
errs = []
for i, m in enumerate(LINE):
    t = 4 * i * DT
    seg = meln[int((t + 0.02) * SR):int((t + 0.45) * SR)]
    f = ruler.partial_freq(seg, hz(m) * 0.96, hz(m) * 1.04)
    errs.append(abs(1200 * np.log2(f / hz(m))))
check("the gat line is played",
        float(np.median(errs)) <= 5.0 and max(errs) <= 10.0,
        f"20 melody fundamentals read back at median "
        f"{np.median(errs):.1f}c, worst {max(errs):.1f}c from "
        f"the written line")

cuc = ruler.chroma_uniform(chik)
runner = max(v for i, v in enumerate(cuc) if i != 2)
check("the chikari is one pitch, twice struck",
        cuc[2] >= 2.5 * runner,
        f"chikari bus chroma crowns class 2 at {cuc[2]:.2f}, "
        f"runner-up {runner:.2f} — da and ra are hand strokes, "
        f"not notes")

print("== the boundary, completed from both sides ==")

n_mel = len(ruler.onset_times(meln))
n_chik = len(ruler.onset_times(chikn))
n_mel7 = len(ruler.onset_times(meln, k=0.7))
n_chik7 = len(ruler.onset_times(chikn, k=0.7))
check("no one setting counts the buses AND the mix",
        n_chik == 60 and 20 <= n_mel <= 30
        and n_mel7 >= 30 and n_chik7 >= 65,
        f"at defaults the SOLO buses count almost true "
        f"(chikari {n_chik}/60 exact, melody {n_mel}/20 with a "
        f"few buzz ghosts) — but the mix will under-count "
        f"(masking), and sensitizing the detector to recover "
        f"the mix (k=0.7) makes the buses over-count "
        f"({n_mel7}/20, {n_chik7}/60): jawari buzz reads as "
        f"re-attacks. No single threshold serves both sides")

sar = 0.55 * meln + 0.35 * chikn
env = ruler.band_env(sar, 30.0, 8000.0, 0.01)
on = [env[int((s * DT + 0.025) / 0.01)] for s in range(NSLOT)]
off = [env[int((s * DT + 0.085) / 0.01)] for s in range(NSLOT)]
gph = float(np.median(on) / np.median(off))
check("the envelope cannot see the strum",
        gph <= 1.15,
        f"grid-phase envelope ratio {gph:.2f} (stroke moment "
        f"vs mid-gap) — ringing tails fill the 120 ms gaps, so "
        f"amplitude rulers are blind at this density")


def flux_lines(x):
    fr, sp = ruler.flux_spectrum(x)
    m = (fr > 1.2) & (fr < 20.0)
    crown_f = fr[m][int(np.argmax(sp[m]))]
    crown_v = sp[m].max()
    out = {}
    for nm, lo, hi in (("group", 1.7, 2.5), ("stroke", 7.5, 9.2),
            ("oct", 15.5, 18.0)):
        b = (fr >= lo) & (fr <= hi)
        i = int(np.argmax(sp[b]))
        out[nm] = (float(fr[b][i]), float(sp[b][i] / crown_v))
    return crown_f, out

crown_f, fx = flux_lines(sar)
check("the flux hums the written rates",
        abs(crown_f / R_GROUP - 1) <= 0.015
        and abs(fx["stroke"][0] / R_STROKE - 1) <= 0.01
        and fx["stroke"][1] >= 0.35,
        f"flux spectrum crowns at {crown_f:.2f} Hz (written "
        f"group cycle {R_GROUP:.3f}) with the stroke line at "
        f"{fx['stroke'][0]:.2f} Hz (written {R_STROKE:.3f}) at "
        f"{fx['stroke'][1]:.2f}x crown and its octave at "
        f"{fx['oct'][0]:.1f} — the rate the census cannot count")

print("== the accent cycle ==")

# melody fundamentals live in 100-210 Hz; chikari (293.7) does
# not — the band isolates the gat's pulse inside the strum
menv = ruler.band_env(sar, 100.0, 210.0, 0.01)
acc_m = [menv[int((4 * i * DT + 0.03) / 0.01)]
        for i in range(len(LINE))]
acc_c = [menv[int((s * DT + 0.03) / 0.01)]
        for s in range(NSLOT) if s % 4]
acc = float(np.median(acc_m) / np.median(acc_c))
check("every fourth stroke carries the gat",
        acc >= 1.4,
        f"melody-band accent ratio {acc:.2f} at melody slots "
        f"vs chikari slots")


def env_crown(x, lo, hi):
    ev = ruler.band_env(x, lo, hi, 0.05)[:192]
    le = np.log(ev + 1e-12)
    k = 41
    pad = np.concatenate([le[:k][::-1], le, le[-k:][::-1]])
    tr = np.convolve(pad, np.ones(k) / k, "same")[k:-k]
    sp = np.abs(np.fft.rfft((le - tr) * np.hanning(len(le))))
    return int(np.argmax(sp[8:80])) + 8

cr = env_crown(sar, 100.0, 210.0)
check("the gat cycle closes at the seam",
        cr == 20,
        f"melody-band envelope spectrum crowns at bin {cr} — "
        f"exactly the 20 written melody strokes per loop")

# ---- the mix ---------------------------------------------------
_, tb = fdsym([hz(n) for n in [50, 52, 53, 55, 57, 59, 60, 62]],
        sar / np.abs(sar).max(), buses=True, jawari=True,
        gain=5000.0)
pans = np.linspace(-0.55, 0.55, 8)
tnorm = np.abs(tb).max() + 1e-12
taraf_st = np.zeros((L, 2))
for b_, p in zip(tb, pans):
    gg = (b_[:L] / tnorm) * 0.05
    taraf_st[:, 0] += gg * np.cos((p + 1) * np.pi / 4)
    taraf_st[:, 1] += gg * np.sin((p + 1) * np.pi / 4)
norm = np.abs(sar).max() + 1e-12
halo_db = 20 * np.log10(rms(taraf_st.sum(axis=1))
        / rms(sar * 0.85 / norm * 0.9))
check("the halo sits under the strum",
        -32.0 <= halo_db <= -8.0,
        f"taraf/strum {halo_db:.1f} dB")

# drone attacks land ON the grid (multiples of 0.12) so they
# join the strum instead of fighting it; no pa pluck (e72: its
# h4 = 440.0 exactly)
DRONE = [("sa+", hz(50.015), 112, 1.2, 0.15, 0.50),
        ("sa-", hz(49.985), 112, 2.4, -0.15, 0.50),
        ("SA", hz(38), 138, 3.6, 0.35, 0.75)]
loop = Loop(LOOP_S, seed=75)
for name, f0d, n, at, pan, ampd in DRONE:
    v = fdpluck2(f0d, 12.0, amp=ampd, N=n)
    loop.add(at, stereo(v, pan))
    loop.add(at + 4.8, stereo(v, pan))
loop.add(0.0, stereo(meln * 0.55 * 0.85 / norm * 0.9, 0.15))
loop.add(0.0, stereo(chikn * 0.35 * 0.85 / norm * 0.9, -0.35))
loop.add(0.0, taraf_st)
mix = loop.master(lp_hz=6500.0, drive=1.2)
mono = mix.mean(axis=1)

n_mix = len(ruler.onset_times(mono))
n_mix7 = len(ruler.onset_times(mono, k=0.7))
check("the mix under-counts (masking)",
        20 <= n_mix <= 0.6 * NSLOT
        and 50 <= n_mix7 <= 0.9 * NSLOT,
        f"mastered mix yields {n_mix} onsets against 80 struck "
        f"at defaults; sensitized (k=0.7) it climbs to "
        f"{n_mix7} — the setting that recovers the mix is the "
        f"one that hallucinates on the buses. The boundary is "
        f"pinned from both sides")

mcrown_f, mfx = flux_lines(mono)
mcr = env_crown(mono, 100.0, 210.0)
check("energy-rhythm vs attack-rhythm",
        mcr == 8
        and abs(mcrown_f / R_GROUP - 1) <= 0.015
        and abs(mfx["stroke"][0] / R_STROKE - 1) <= 0.01
        and mfx["stroke"][1] >= 0.25,
        f"in the mastered mix the melody-band ENVELOPE crowns "
        f"at bin {mcr} — the drone's own seam-locked attack "
        f"lattice (plucks every 1.2 s = 8 cycles), whose "
        f"sustained 147 Hz floods the band. But the FLUX still "
        f"crowns at {mcrown_f:.2f} Hz (the written gat cycle "
        f"{R_GROUP:.3f}) with the stroke line at "
        f"{mfx['stroke'][0]:.2f} Hz at {mfx['stroke'][1]:.2f}x "
        f"crown — envelope follows energy, flux follows "
        f"attacks; six loud drone events cannot outvote eighty "
        f"strums in the flux")
check("seam", ruler.seam_rank(mix) <= 0.999,
        f"p{100 * ruler.seam_rank(mix):.2f}")

cu = ruler.chroma_uniform(mono)
check("Sa crowns the mix",
        int(np.argmax(cu)) == 2,
        f"chroma crowns class 2 at {max(cu):.2f} — gat line, "
        f"chikari and drone all agree on D")

out = np.concatenate([mix, mix])
wav = os.path.join(outdir, "e75_jhala.wav")
write_wav(wav, out)
ruler.report(out, "jhala")

if fails:
    print("FAILED RULERS:", fails)
    sys.exit(1)
print("ALL RULERS PASS")

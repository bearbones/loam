#!/usr/bin/env python3
"""loam e91 — SANKYOKU: koto, shamisen, shakuhachi (capstone).

The trio exists as of e90: koto (e90), shamisen (e81),
shakuhachi (e82, komibuki e89). This piece assembles them the
way sankyoku actually works — HETEROPHONY: all three voices
carry the SAME melody, individually ornamented, with small
written time offsets. The strings sit nearly together (the
shamisen trails the koto by a written 40 ms), the wind floats
behind (a written 120 ms), and everyone agrees at the cadence.

Because the texture is written as numbers, it is claimable as
numbers:

  - LAG: per matched note, measured onset difference between
    buses vs the written offset (koto/shamisen marked by pick
    flux; the shakuhachi's onset is a BLOOM, marked where its
    own envelope first crosses -12 dB re the note's peak);
  - CADENCE: all three land on written D's (per-voice IF
    center within 15 c of its own octave's D);
  - MA: the shared breath before the cadence is actually
    silent on the summed dry buses;
  - SIGNATURES: each instrument re-passes its own voice test
    inside the capstone (sawari buzz vs barrier-out twin,
    tsume click, muraiki gust vs still twin) — e87's rule that
    verified components must stay verified when composed.

32 s loop, D hirajoshi / honchoshi on D.

    python3 experiments/e91_sankyoku.py [outdir]
"""

import os
import sys

import numpy as np
from scipy.signal import butter, sosfilt

sys.path.insert(0, os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))))
from loam import SR, hz, stereo, write_wav
from loam import ruler
from loam.nihon import koto, shamisen, shakuhachi
from loam.space import reverb_loop

outdir = sys.argv[1] if len(sys.argv) > 1 else "render"
os.makedirs(outdir, exist_ok=True)
fails = []


def check(name, cond, detail):
    print(f"  {'PASS' if cond else 'FAIL'} {name}: {detail}")
    if not cond:
        fails.append(name)


def rms(x):
    return float(np.sqrt(np.mean(np.asarray(x, float) ** 2) + 1e-30))


LOOP_S = 32.0
N = int(LOOP_S * SR)
LAG_SH = 0.04     # shamisen trails the koto (written)
LAG_FL = 0.12     # shakuhachi trails the koto (written)

# koto line: (onset, midi, dur, bend_c, bend_at, vib_c, amp)
KOTO = [
    # phrase 1 — koto alone states the kernel
    (0.9, 62, 1.1, 0.0, 0.0, 0.0, 0.85),
    (2.1, 57, 0.9, 0.0, 0.0, 0.0, 0.80),
    (3.0, 58, 0.9, 100.0, 0.30, 0.0, 0.85),
    (3.9, 57, 1.1, 0.0, 0.0, 0.0, 0.80),
    (5.1, 55, 2.2, 0.0, 0.0, 10.0, 0.90),
    # phrase 2 — the trio
    (8.1, 62, 0.9, 0.0, 0.0, 0.0, 0.85),
    (9.0, 63, 0.9, 0.0, 0.0, 0.0, 0.80),
    (9.9, 62, 0.9, 0.0, 0.0, 0.0, 0.85),
    (10.8, 58, 1.1, 180.0, 0.35, 0.0, 0.90),
    (12.0, 57, 1.8, 0.0, 0.0, 10.0, 0.85),
    # phrase 3
    (16.5, 55, 0.9, 0.0, 0.0, 0.0, 0.80),
    (17.4, 57, 0.9, 0.0, 0.0, 0.0, 0.80),
    (18.3, 58, 0.9, 0.0, 0.0, 0.0, 0.85),
    (19.2, 57, 1.1, 0.0, 0.0, 0.0, 0.80),
    (20.4, 62, 1.7, 0.0, 0.0, 0.0, 0.90),
    # cadence (after the shared breath)
    (23.4, 62, 4.5, 0.0, 0.0, 10.0, 1.00),
]
# shamisen doubles phrases 2+3 and the cadence, LAG_SH behind;
# sawari wakes only on the low D (the lowest string, as built)
SHAM = [(KOTO[i][0] + LAG_SH, KOTO[i][1], 0.85, 0.0, 0.50)
        for i in range(5, 15)]
SHAM.append((23.4 + LAG_SH, 50, 2.6, 0.85, 0.62))
# shakuhachi floats a simplified line an octave up, LAG_FL
# behind: (onset, midi, dur, muraiki, yuri_c, amp, koto_idx)
FLUTE = [
    (KOTO[5][0] + LAG_FL, 74, 1.6, 0.20, 0.0, 0.72, 5),
    (KOTO[7][0] + LAG_FL, 74, 1.7, 0.20, 0.0, 0.70, 7),
    (KOTO[9][0] + LAG_FL, 69, 2.6, 0.25, 14.0, 0.75, 9),
    (KOTO[10][0] + LAG_FL, 67, 1.6, 0.20, 0.0, 0.70, 10),
    (KOTO[12][0] + LAG_FL, 70, 1.7, 0.20, 0.0, 0.72, 12),
    (KOTO[14][0] + LAG_FL, 74, 2.2, 0.25, 0.0, 0.75, 14),
    (23.4 + LAG_FL, 74, 4.8, 0.85, 16.0, 0.85, 15),
]


def add_wrap(bus, t, ss):
    i0 = int(round(t * SR)) % N
    n = len(ss)
    if i0 + n <= N:
        bus[i0:i0 + n] += ss
    else:
        k = N - i0
        bus[i0:] += ss[:k]
        bus[:n - k] += ss[k:]


NK, NS, NF = [], [], []
kt = np.zeros((N, 2))
for t, m, dur, bc, ba, vc, a in KOTO:
    v = koto(hz(m), dur, bend_c=bc, bend_at=ba, vib_c=vc,
            body=0.55, tsume=0.85)
    NK.append(v)
    add_wrap(kt, t, stereo(v * a, 0.18))

sb = np.zeros((N, 2))
for t, m, dur, sw, a in SHAM:
    v = shamisen(hz(m), dur, sawari=sw, snap=0.5, thump=0.40)
    NS.append(v)
    add_wrap(sb, t, stereo(v * a, -0.20))

fl = np.zeros((N, 2))
for i, (t, m, dur, mur, yc, a, ki) in enumerate(FLUTE):
    v = shakuhachi(hz(m), dur, muraiki=mur, scoop=30.0,
            yuri_c=yc, seed=31 + 5 * i)
    NF.append(v)
    add_wrap(fl, t, stereo(v * a, 0.02))

dry = 0.92 * kt + 0.60 * sb + 0.85 * fl
wet = reverb_loop(dry, t60=2.1, size=1.15)
mix = 0.82 * dry + 0.28 * wet
mix *= 0.92 / (np.abs(mix).max() + 1e-12)
write_wav(os.path.join(outdir, "e91_sankyoku.wav"), mix)

# ---- rulers ------------------------------------------------------
print("e91 rulers (heterophony as numbers; own-bus marks):")

# onset marks: pick flux for the strings, envelope bloom for
# the wind (its attack IS a breath, there is no click to find)
sos_hi = butter(4, [2500.0, 11000.0], btype="bandpass", fs=SR,
        output="sos")


def flux_marks(bus, times, win=0.15):
    h = np.abs(sosfilt(sos_hi, bus.mean(axis=1)))
    ker = int(0.004 * SR)
    h = np.convolve(h, np.ones(ker) / ker, mode="same")
    fx = np.maximum(np.diff(h, prepend=h[:1]), 0.0)
    out = []
    for t in times:
        i0, i1 = int((t - win) * SR), int((t + win) * SR)
        out.append((i0 + int(np.argmax(fx[i0:i1]))) / SR)
    return out


def bloom_marks(bus, times, durs, win=0.20):
    e = np.abs(bus.mean(axis=1))
    ker = int(0.02 * SR)
    e = np.convolve(e, np.ones(ker) / ker, mode="same")
    out = []
    for t, d in zip(times, durs):
        i0 = int((t - win) * SR)
        i1 = int((t + min(d, 0.8)) * SR)
        seg = e[i0:i1]
        thr = seg.max() * 10.0 ** (-12.0 / 20.0)
        out.append((i0 + int(np.argmax(seg >= thr))) / SR)
    return out


mk_k = flux_marks(kt, [p[0] for p in KOTO])
mk_s = flux_marks(sb, [p[0] for p in SHAM])
mk_f = bloom_marks(fl, [p[0] for p in FLUTE],
        [p[2] for p in FLUTE])

# 1. the strings sit a written 40 ms apart
lags = [mk_s[j] - mk_k[5 + j] for j in range(10)]
med_s = float(np.median(lags)) * 1000.0
worst_s = max(abs(l - LAG_SH) for l in lags) * 1000.0
check("lag_strings", abs(med_s - 40.0) <= 20.0
        and worst_s <= 40.0,
        f"median {med_s:.0f} ms (written 40), worst pair "
        f"off by {worst_s:.0f} ms")

# 2. the wind floats a written 120 ms behind
lagf = [mk_f[j] - mk_k[FLUTE[j][6]] for j in range(len(FLUTE))]
med_f = float(np.median(lagf)) * 1000.0
worst_f = max(abs(l - LAG_FL) for l in lagf) * 1000.0
check("lag_wind", abs(med_f - 120.0) <= 40.0
        and worst_f <= 100.0,
        f"median {med_f:.0f} ms (written 120), worst pair "
        f"off by {worst_f:.0f} ms")

# 3. every voice centers on its written pitch — PER-VOICE
# gates: the strings hold sub-cent (FD strings, gate 5 c), the
# wind keeps e82's own 20 c gate (wander kept, the gate is the
# center — a 1.6 s note averages less wander than e82's 5 s)
worst_st = 0.0
for v, (t, m, dur, bc, ba, vc, a) in zip(NK, KOTO):
    if bc > 0.0:
        continue
    inst = ruler.if_pitch(v, hz(m))
    s1 = min(1.2, dur - 0.25)
    worst_st = max(worst_st, abs(1200.0 * np.log2(np.median(
            inst[int(0.2 * SR):int(s1 * SR)]) / hz(m))))
for v, (t, m, dur, sw, a) in zip(NS, SHAM):
    inst = ruler.if_pitch(v, hz(m))
    s1 = min(0.8, dur - 0.2)
    worst_st = max(worst_st, abs(1200.0 * np.log2(np.median(
            inst[int(0.15 * SR):int(s1 * SR)]) / hz(m))))
worst_w = 0.0
for v, (t, m, dur, mur, yc, a, ki) in zip(NF, FLUTE):
    inst = ruler.if_pitch(v, hz(m))
    s0, s1 = max(0.45, 0.3 * dur), dur - 0.3
    worst_w = max(worst_w, abs(1200.0 * np.log2(np.median(
            inst[int(s0 * SR):int(s1 * SR)]) / hz(m))))
check("centers", worst_st <= 5.0 and worst_w <= 20.0,
        f"strings worst {worst_st:.1f} c (gate 5), wind worst "
        f"{worst_w:.1f} c (gate 20, e82's)")

# 4. the cadence agrees: three D's, one per octave
errs = []
for v, m in ((NK[15], 62), (NS[10], 50), (NF[6], 74)):
    inst = ruler.if_pitch(v, hz(m))
    errs.append(1200.0 * np.log2(np.median(
            inst[int(0.5 * SR):int(1.8 * SR)]) / hz(m)))
worst_cad = max(abs(e) for e in errs)
check("cadence", worst_cad <= 15.0,
        f"koto {errs[0]:+.1f} c, shamisen {errs[1]:+.1f} c, "
        f"shakuhachi {errs[2]:+.1f} c on written D")

# 5. ma: the shared breath before the cadence is real silence
# on the summed dry buses
dm = dry.mean(axis=1)
r_rest = rms(dm[int(22.6 * SR):int(23.25 * SR)])
r_act = rms(dm[int(8.1 * SR):int(14.0 * SR)])
drop = 20.0 * np.log10(r_act / r_rest)
check("ma", drop >= 20.0,
        f"rest sits {drop:.1f} dB under the trio passage")

# 6. signatures survive the ensemble (e87's rule): each voice
# re-passes its own test inside the capstone
tw_sw = shamisen(hz(50), 2.6, sawari=0.0, snap=0.5, thump=0.40)
sos2k = butter(4, 2000.0, btype="highpass", fs=SR, output="sos")
buzz = 20.0 * np.log10(rms(sosfilt(sos2k, NS[10]))
        / rms(sosfilt(sos2k, tw_sw)))
# tsume measured on the A3 note (NK[9]) — the click band is
# register-limited at D4 and above (e90's scoping)
atk = 20.0 * np.log10(
        rms(sosfilt(sos_hi, NK[9])[:int(0.012 * SR)])
        / rms(sosfilt(sos_hi, NK[9])[int(0.5 * SR):
                int(0.9 * SR)]))
tw_mu = shakuhachi(hz(74), 4.8, muraiki=0.0, scoop=30.0,
        yuri_c=16.0, seed=31 + 5 * 6)
sos_g = butter(4, [1500.0, 6500.0], btype="bandpass", fs=SR,
        output="sos")


def gust(v):
    h = sosfilt(sos_g, v)
    return 20.0 * np.log10(rms(h[:int(0.25 * SR)])
            / rms(h[int(0.6 * SR):int(0.9 * SR)]))


dg = gust(NF[6]) - gust(tw_mu)
check("signatures", buzz >= 5.0 and atk >= 12.0 and dg >= 6.0,
        f"sawari +{buzz:.1f} dB, tsume +{atk:.1f} dB, "
        f"muraiki +{dg:.1f} dB (each vs its own floor)")

# 7. the loop closes
check("seam", ruler.seam_rank(mix) <= 0.999,
        f"p{100 * ruler.seam_rank(mix):.2f}")

ruler.report(mix, "e91_sankyoku")
print(f"\n{'ALL PASS' if not fails else 'FAILS: ' + str(fails)}")
sys.exit(1 if fails else 0)

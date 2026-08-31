#!/usr/bin/env python3
"""e62 — sarangi + taraf: the halo hears the lattice.

Refinement joining e61's bowed voice to e53/e54's sympathetic
bank — the full sarangi, whose signature IS its taraf. Two
predictions tested, one dead, one transformed:

  - DEAD: "a sustained driver out-selects a plucked one".
    Measured x18.9 bowed vs x18.7 plucked — parity. e53's
    coherence lesson was really line-spectrum vs broadband;
    fdpluck (t60 7.7 s) is already maximally coherent, and
    selectivity saturates there. What the bow DOES change:
    its brighter sawtooth recruits the FIFTH-FAMILY — the Pa
    string tops the whole bank under bowed drive (1.00 vs
    0.25 plucked).

  - TRANSFORMED: "the halo hands off as the meend moves"
    became a four-way taxonomy of how a string can light,
    measured across the Sa-hold -> Ga-hold windows:
      sung     (F string, the note itself)        x17
      crossed  (E string, brushed by the glide)   x23
      lattice  (C string — NEVER sung, never
                crossed: Ga's h3 sits on its h2,
                the fifth-above recruitment)      x45
      remembered (Sa and high-Sa strings hold
                within 2% through the Ga hold —
                t60 58 s designs a -0.3 dB fall)  x1.0
    The relatively dark control (B) moves only x4.6.

The piece: e61's jor with its halo — the bowed phrase drives
the bank, the taraf shimmers under the voice at -14 dB, and
every e61 piece claim is re-verified in the new mix.

    python3 experiments/e62_sarangi_taraf.py [outdir]
"""

import os
import subprocess
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))))
from loam import SR, hz, Loop, stereo, write_wav
from loam import ruler
from loam.fdstring import fdbow, fdpluck, fdpluck2, fdsym

outdir = sys.argv[1] if len(sys.argv) > 1 else "render"
os.makedirs(outdir, exist_ok=True)
fails = []


def check(name, cond, detail):
    print(f"  {'PASS' if cond else 'FAIL'} {name}: {detail}")
    if not cond:
        fails.append(name)


def rms(x):
    return float(np.sqrt(np.mean(np.asarray(x) ** 2)))


BANK = [50, 52, 53, 55, 57, 59, 60, 62]
DET = [i for i, n in enumerate(BANK) if n in (52, 53, 59, 60)]

# ---- 1/2. driver A/B: parity of selectivity, recruitment -------
bow2 = fdbow(hz(50), 2.0, FB=1e3, vb=0.10)
plk2 = fdpluck(hz(50), 2.0)


def bank_rms(drive):
    _, tb = fdsym([hz(n) for n in BANK], drive, buses=True,
            jawari=True, gain=5000.0)
    seg = tb[:, int(0.5 * SR):int(2.0 * SR)]
    return np.sqrt((seg ** 2).mean(axis=1))


rb = bank_rms(bow2)
rp = bank_rms(plk2)
sb = rb[BANK.index(50)] / np.mean(rb[DET])
sp = rp[BANK.index(50)] / np.mean(rp[DET])
check("line-spectrum drivers saturate selectivity",
        sb >= 10.0 and sp >= 10.0 and 0.7 <= sb / sp <= 1.4,
        f"bowed x{sb:.1f} vs plucked x{sp:.1f} — parity "
        f"(e53's coherence lesson was line-vs-broadband, and "
        f"the pluck is already a line spectrum)")
i57 = BANK.index(57)
check("the bow recruits the fifth-family",
        int(np.argmax(rb)) == i57 and rp[i57] / rp.max() <= 0.4,
        f"Pa string under bowed drive: TOP of the bank "
        f"({rb[i57] / rb.max():.2f}); plucked: "
        f"{rp[i57] / rp.max():.2f} of max")

# ---- the phrase and its halo -----------------------------------
LOOP_S = 9.6
KN = [(0.0, 50), (2.2, 50), (3.2, 53), (4.8, 53), (5.6, 52),
        (6.4, 52), (7.4, 50), (9.6, 50)]
tt = np.linspace(0, LOOP_S, 2000)
f0t = np.interp(tt, [t for t, _ in KN], [hz(m) for _, m in KN])
VBK = [(0.0, 0.08), (2.0, 0.13), (3.4, 0.10), (5.0, 0.12),
        (6.5, 0.13), (8.0, 0.09), (8.5, 0.08), (9.6, 0.08)]
vbt = np.interp(tt, [t for t, _ in VBK], [v for _, v in VBK])
LIFT_S = 8.5
FBt = np.where(tt < LIFT_S, 1e3, 0.0)
sar = fdbow(f0t, LOOP_S, FB=FBt, vb=vbt, sig0=4.0, raw=True)
_, tb = fdsym([hz(n) for n in BANK], sar, buses=True,
        jawari=True, gain=5000.0)


def wrms(i, a, b):
    return float(np.sqrt((tb[i, int(a * SR):int(b * SR)] ** 2)
            .mean()))


# ---- 3. four ways a string lights (Sa-hold vs Ga-hold) ---------
rat = {n: wrms(BANK.index(n), 3.4, 4.6)
        / max(wrms(BANK.index(n), 0.5, 2.0), 1e-9) for n in BANK}
check("the sung string lights", rat[53] >= 8.0,
        f"F (Ga itself) x{rat[53]:.1f}")
check("the crossed string lights", rat[52] >= 8.0,
        f"E (brushed by the Sa->Ga glide) x{rat[52]:.1f}")
check("the lattice lights the unsung fifth", rat[60] >= 15.0,
        f"C (never sung, never crossed — Ga's h3 on its h2) "
        f"x{rat[60]:.1f}")
check("the dark string stays relatively dark", rat[59] <= 8.0,
        f"B x{rat[59]:.1f} — the only string the phrase gives "
        f"nothing to")
check("the halo remembers",
        0.85 <= rat[50] <= 1.15 and 0.85 <= rat[62] <= 1.15,
        f"Sa x{rat[50]:.2f}, high Sa x{rat[62]:.2f} through the "
        f"Ga hold (t60 58 s designs -0.3 dB)")

# ---- the piece: jor with halo ----------------------------------
HALO_GAIN = 0.05               # first run: 0.012 -> -32.2 dB,
                               # peak-norm not rms-norm; x4 -> -20
pans = np.linspace(-0.55, 0.55, len(BANK))
tnorm = np.abs(tb).max() + 1e-12
L = int(LOOP_S * SR)
taraf_st = np.zeros((L, 2))
for b, p in zip(tb, pans):
    gg = (b[:L] / tnorm) * HALO_GAIN
    taraf_st[:, 0] += gg * np.cos((p + 1) * np.pi / 4)
    taraf_st[:, 1] += gg * np.sin((p + 1) * np.pi / 4)
halo_db = 20 * np.log10(rms(taraf_st.sum(axis=1))
        / rms(sar * 0.85 / np.abs(sar).max() * 0.9))
# note: level vs the MIX-scaled sarangi, same as it will sound

ts, fs = ruler.pitch_contour(sar, fmin=80.0, fmax=500.0)
worst_hold = 0.0
for nm, a, b, m in (("Sa", 0.5, 2.0, 50), ("Ga", 3.4, 4.6, 53),
        ("Re", 5.7, 6.3, 52), ("Sa'", 7.5, 8.4, 50)):
    sel = (ts >= a) & (ts <= b)
    med = float(np.median(fs[sel]))
    worst_hold = max(worst_hold, abs(1200 * np.log2(med / hz(m))))
check("every hold lands", worst_hold <= 25.0,
        f"worst hold {worst_hold:.1f}c across Sa-Ga-Re-Sa")
sel = (ts >= 0.3) & (ts <= 8.3)
d = np.interp(ts, tt, f0t)
dev = 1200 * np.log2(fs[sel] / d[sel])
check("the meend follows the written line",
        float(np.median(np.abs(dev))) <= 15.0,
        f"median |dev| {float(np.median(np.abs(dev))):.1f}c")
wr = np.array([rms(sar[int(a * SR):int((a + 0.3) * SR)])
        for a in np.arange(0.5, 8.1, 0.3)])
check("the voice holds for the whole phrase",
        float(wr.min() / wr.max()) >= 0.4,
        f"windowed rms min/max {wr.min() / wr.max():.3f}")
t60r = ruler.decay_t60(sar[int(8.6 * SR):int(9.55 * SR)],
        100.0, 1200.0)
check("the lift rings into the seam",
        abs(t60r / 1.725 - 1) <= 0.3,
        f"release t60 {t60r:.2f} s (design 1.73)")
check("the halo sits under the voice", -32.0 <= halo_db <= -8.0,
        f"taraf/sarangi {halo_db:.1f} dB")

# ---- the mix ---------------------------------------------------
DRONE = [("pa", hz(45), 140, 0.0, -0.35, 0.55),
        ("sa+", hz(50.015), 112, 1.2, 0.15, 0.50),
        ("sa-", hz(49.985), 112, 2.4, -0.15, 0.50),
        ("SA", hz(38), 138, 3.6, 0.35, 0.75)]
loop = Loop(LOOP_S, seed=62)
for name, f0d, n, at, pan, ampd in DRONE:
    v = fdpluck2(f0d, 12.0, amp=ampd, N=n)
    loop.add(at, stereo(v, pan))
    loop.add(at + 4.8, stereo(v, pan))
sar_mix = sar * 0.85 / (np.abs(sar).max() + 1e-12) * 0.9
loop.add(0.0, stereo(sar_mix, 0.0))
loop.add(0.0, taraf_st)
mix = loop.master(lp_hz=6500.0, drive=1.2)

check("seam", ruler.seam_rank(mix) <= 0.999,
        f"p{100 * ruler.seam_rank(mix):.2f}")
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
wav = os.path.join(outdir, "e62_sarangi_taraf.wav")
write_wav(wav, out)
ruler.report(out, "sarangi_taraf")
subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", wav,
        "-q:a", "5", wav.replace(".wav", ".ogg")], check=True)

print("ALL RULERS PASS" if not fails else f"FAILED: {fails}")
sys.exit(1 if fails else 0)

#!/usr/bin/env python3
"""e57 — gat: the arc arrives.

The raga arc's destination, banked since the alap (e46) and
unblocked by five sessions of instrument-building: melody,
theka, and halo TOGETHER. Every voice is a certified construct
playing inside its measured contract:

  - fdpluck gat melody (Kafi, D dorian) on the matra grid
  - fdpluck2 two-polarization tanpura drone (D-A poles)
  - fdsym + jawari taraf halo, driven by the MELODY bus only
    (e53: driver coherence determines selectivity — the drums
    would kick every string alike)
  - e55's tuned na (D3, overtones D-A-D-F#) and bayan on A1,
    teental with the khali bass hole and palm-damp gesture
  - e56's glide: avartan 2's answer — the melody rests after
    khali and the bayan bends a perfect fourth into sam

Call and answer: the hand states the sthayi, the drum replies
by ARRIVING ON SA. Every claim is measured per-bus in situ —
assembly is not exemption.

    python3 experiments/e57_gat.py [outdir]
"""

import os
import subprocess
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))))
from loam import SR, hz, Loop, stereo, write_wav
from loam import ruler
from loam.fdstring import fdpluck, fdpluck2, fdsym
from loam.membrane import fddrum

outdir = sys.argv[1] if len(sys.argv) > 1 else "render"
os.makedirs(outdir, exist_ok=True)
fails = []


def check(name, cond, detail):
    print(f"  {'PASS' if cond else 'FAIL'} {name}: {detail}")
    if not cond:
        fails.append(name)


def rms(x):
    return float(np.sqrt(np.mean(np.asarray(x) ** 2)))


SUB = 0.3
NB = 16
LOOP_S = 2 * NB * SUB
KAFI = {2, 4, 5, 7, 9, 11, 0}
L = int(LOOP_S * SR)

# ---- the sthayi: two avartans, rest for the drum's answer ------
MEL = [(0, 3, 50), (3, 1, 53), (4, 2, 52), (6, 1, 55),
        (7, 1, 57), (8, 1, 57), (9, 1, 55), (10, 1, 59),
        (11, 1, 57), (12, 2, 50), (14, 1, 53), (15, 1, 55),
        (16, 2, 57), (18, 1, 60), (19, 1, 59), (20, 1, 57),
        (21, 1, 55), (22, 1, 53), (23, 1, 52), (24, 3, 50),
        (27, 1, 52)]           # slots 28-31: the bayan answers
assert all(m % 12 in KAFI for _, _, m in MEL)

mel = np.zeros(L + SR)
for at, durs, m in MEL:
    v = fdpluck(hz(m), durs * SUB + 0.25, amp=0.85)
    a = int(at * SUB * SR)
    mel[a:a + len(v)] += v
mel = mel[:L]

# ---- the drums (e55/e56 contracts) -----------------------------
LOAD, RS = 40.0, 0.45
F1A, F1D = 105.6, 141.2
na = fddrum(283.8, 1.5, strike=(0.55, 0.0), load=LOAD, rs=RS,
        sig_s=60.0)
ge = fddrum(F1A, 1.0, strike=(0.30, 0.0), load=LOAD, rs=RS,
        sig0=9.0, sig_s=20.0)
ge_sam = fddrum(F1D, 1.0, strike=(0.30, 0.0), load=LOAD, rs=RS,
        sig0=9.0, sig_s=20.0)
tt2 = np.linspace(0, 1, 200)
G_DUR = 0.9
f1g = np.where(tt2 < 0.10, F1A, np.where(tt2 > 0.85, F1D,
        F1A + (F1D - F1A) * (tt2 - 0.10) / 0.75))
ge_glide = fddrum(f1g, G_DUR, strike=(0.30, 0.0), load=LOAD,
        rs=RS, sig0=9.0, sig_s=20.0)

THEKA = [(1.0, 0.9), (1.0, 0.55), (1.0, 0.55), (1.0, 0.9),
        (1.0, 0.9), (1.0, 0.55), (1.0, 0.55), (1.0, 0.9),
        (1.0, 0.9), (0.85, 0.0), (0.85, 0.0), (1.0, 0.0),
        (1.0, 0.0), (1.0, 0.55), (1.0, 0.55), (1.0, 0.9)]
KHALI = {9, 10, 11, 12}
GLIDE_SLOT = 29

ge_damp = ge.copy()
cut = int(SUB * SR)
fdn = int(0.06 * SR)
ge_damp[cut - fdn:cut] *= np.linspace(1, 0, fdn)
ge_damp[cut:] = 0.0

nslots = 2 * NB
drums = np.zeros((L + 2 * SR, 2))
gebus = np.zeros(L + 2 * SR)
for k in range(nslots):
    na_a, ge_a = THEKA[k % NB]
    a = int(k * SUB * SR)
    v = stereo(na * na_a, 0.25)
    drums[a:a + len(v)] += v
    if k == GLIDE_SLOT:
        v = stereo(ge_glide * 0.95, -0.25)
        drums[a:a + len(v)] += v
        gebus[a:a + len(ge_glide)] += ge_glide * 0.95
    elif k in (GLIDE_SLOT + 1, GLIDE_SLOT + 2):
        continue
    elif ge_a > 0:
        gk = ge_sam if k % NB == 0 else \
            (ge_damp if (k + 1) % NB in KHALI else ge)
        v = stereo(gk * ge_a, -0.25)
        drums[a:a + len(v)] += v
        gebus[a:a + len(gk)] += gk * ge_a
drums = drums[:L]
gebus = gebus[:L]

# ---- the halo: melody-driven jawari taraf (e54 contract) -------
BANK = [50, 52, 53, 55, 57, 59, 60, 62]
_, tb = fdsym([hz(n) for n in BANK], mel, buses=True,
        jawari=True, gain=5000.0)
HALO_GAIN = 0.041
pans = np.linspace(-0.55, 0.55, len(BANK))
tnorm = np.abs(tb).max() + 1e-12
taraf_st = np.zeros((L, 2))
for b, p in zip(tb, pans):
    gg = (b / tnorm) * HALO_GAIN
    taraf_st[:, 0] += gg * np.cos((p + 1) * np.pi / 4)
    taraf_st[:, 1] += gg * np.sin((p + 1) * np.pi / 4)

# ---- own-bus: the melody -----------------------------------------
ts, fs = ruler.pitch_contour(mel, fmin=80.0, fmax=700.0)
worst = 0.0
for at, durs, m in MEL:
    # measure each note at its HEAD: a 1-slot note's strict
    # interior holds only 2 windows and a 2-sample median is a
    # mean — the previous pluck's 0.25 s ring-over pulled the
    # A-after-B notes to +103 cents (probe ledger); the first
    # 0.26 s gives >=3 windows and a real median
    t0n = at * SUB + 0.10
    selw = (ts >= t0n) & (ts <= t0n + 0.16)
    if selw.sum():
        med = float(np.median(fs[selw]))
        worst = max(worst, abs(1200 * np.log2(med / hz(m))))
check("every gat note reads back", worst <= 25.0,
        f"worst {worst:.1f} cents across {len(MEL)} notes")
dw = ruler.dwell_seconds(ts, fs, hz(50))
check("the line lives on Sa", int(np.argmax(dw)) == 0,
        f"dwell argmax class {int(np.argmax(dw))} "
        f"({dw[0]:.1f}s on Sa)")

# ---- own-bus: the halo -----------------------------------------
# chroma was the wrong ruler here: the jawari's job is to pour
# energy up the harmonic ladder, and Sa's 5th harmonic lands on
# F# (734 Hz) — harmonic COLOR, not scale membership — while any
# band narrow enough to exclude h5 makes "halo is Kafi" true by
# construction (the bank IS Kafi). Measure SELECTIVITY instead:
# which strings ring. Whole-piece ranking is honestly flat
# (a gat visits every class and t60~58s never forgets), so the
# claims are (a) the piece's front door, before the memory
# fills, and (b) which strings win the long integration.
rbus = np.sqrt((tb ** 2).mean(axis=1))
seg = tb[:, int(0.30 * SR):int(0.90 * SR)]
ropen = np.sqrt((seg ** 2).mean(axis=1))
oo = np.argsort(ropen)[::-1]
want = {BANK.index(50), BANK.index(55), BANK.index(62)}
gap = ropen[oo[2]] / ropen[oo[3]]
check("the opening halo is Sa's family",
        set(oo[:3].tolist()) == want and gap >= 2.0,
        f"during the sam hold the top-3 strings are "
        f"{sorted(BANK[i] for i in oo[:3])} — Sa, high Sa (never "
        f"played, octave sympathy), and G (h3 on Sa's h4), "
        f"3rd/4th gap x{gap:.1f} (bar 2.0, probe x3.9)")
op = np.argsort(rbus)[::-1]
top2c = {BANK[i] % 12 for i in op[:2]}
check("the halo's poles are Sa and Pa", top2c == {2, 9},
        f"whole-piece loudest strings midi "
        f"{sorted(BANK[i] for i in op[:2])}, 2nd/3rd gap "
        f"x{rbus[op[1]] / rbus[op[2]]:.2f}")
halo_db = 20 * np.log10(rms(taraf_st.sum(axis=1)) / rms(mel))
check("the halo sits under the melody", -32.0 <= halo_db <= -8.0,
        f"taraf/melody {halo_db:.1f} dB")

# ---- own-bus: the theka ----------------------------------------
dbl = np.concatenate([drums, drums]).mean(axis=1)
onsets = ruler.onset_times(dbl, min_sep=0.12)
slots = {}
for t in onsets:
    k = int(round(t / SUB))
    if abs(t - k * SUB) <= 0.06:
        slots.setdefault(k % nslots, t)
check("every slot strikes", len(slots) == nslots,
        f"{len(slots)}/{nslots} onsets within 60 ms of grid")
pr = ruler.pulse_rate(drums.mean(axis=1), 2.0, 5.0,
        lo=300.0, hi=2500.0)
check("the theka pulse reads back", abs(pr - 1.0 / SUB) <= 0.2,
        f"designed {1.0 / SUB:.2f} Hz, measured {pr:.2f} Hz")

w0, w1 = int(0.08 * SR), int(0.28 * SR)
mono_d = drums.mean(axis=1)
hann = np.hanning(w1 - w0)


def band_rms(seg):
    p = np.abs(np.fft.rfft(seg * hann)) ** 2
    f = np.fft.rfftfreq(len(seg), 1.0 / SR)
    return float(np.sqrt(p[(f >= 30.0) & (f <= 100.0)].sum()))


be = np.array([band_rms(mono_d[int(k * SUB * SR) + w0:
        int(k * SUB * SR) + w1]) for k in range(nslots)])
kh = np.array([k % NB in KHALI for k in range(nslots)])
hole = float(np.median(be[kh]) / np.median(be[~kh]))
check("the khali quarter is a bass hole", hole <= 0.35,
        f"khali/bhari sustained bass-band slot energy {hole:.3f}")

# ---- own-bus: the drum's answer arrives on Sa ------------------
ge2 = np.concatenate([gebus, gebus])
t0g = GLIDE_SLOT * SUB
tsg, fsg = ruler.partial_track(
        ge2[int(t0g * SR):int((t0g + G_DUR + 0.35) * SR)],
        45.0, 80.0)
landp = float(np.nanmedian(fsg[tsg >= G_DUR - 0.05]))
risep = 1200 * np.log2(landp / float(np.nanmedian(
        fsg[tsg <= 0.10])))
centp = 1200 * np.log2(landp / hz(38))
check("the drum answers by arriving on Sa", risep >= 450.0
        and abs(centp) <= 25.0,
        f"{risep:.0f} cents risen while the melody rests, "
        f"{centp:+.0f} cents from Sa at sam")

# ---- the mix ---------------------------------------------------
DRONE = [("pa", hz(45), 140, 0.0, -0.35, 0.55),
        ("sa+", hz(50.015), 112, 1.2, 0.15, 0.50),
        ("sa-", hz(49.985), 112, 2.4, -0.15, 0.50),
        ("SA", hz(38), 138, 3.6, 0.35, 0.75)]
loop = Loop(LOOP_S, seed=57)
for name, f0d, n, at, pan, ampd in DRONE:
    v = fdpluck2(f0d, 12.0, amp=ampd, N=n)
    loop.add(at, stereo(v, pan))
    loop.add(at + 4.8, stereo(v, pan))
loop.add(0.0, stereo(mel, 0.0))
loop.add(0.0, taraf_st)
loop.add(0.0, drums * 0.7)
mix = loop.master(lp_hz=6500.0, drive=1.2)

check("seam", ruler.seam_rank(mix) <= 0.999,
        f"p{100 * ruler.seam_rank(mix):.2f}")
prm = ruler.pulse_rate(mix.mean(axis=1), 2.0, 5.0,
        lo=300.0, hi=2500.0)
check("the pulse survives the mix", abs(prm - 1.0 / SUB) <= 0.2,
        f"measured {prm:.2f} Hz in the full render")
ch = ruler.chroma(mix.mean(axis=1))
top2 = set(np.argsort(ch)[-2:].tolist())
check("D and A are the two poles", top2 == {2, 9},
        f"top-2 classes {sorted(top2)}")

out = np.concatenate([mix, mix])
wav = os.path.join(outdir, "e57_gat.wav")
write_wav(wav, out)
ruler.report(out, "gat")
subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", wav,
        "-q:a", "5", wav.replace(".wav", ".ogg")], check=True)

print("ALL RULERS PASS" if not fails else f"FAILED: {fails}")
sys.exit(1 if fails else 0)

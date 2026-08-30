#!/usr/bin/env python3
"""e58 — antara: the gat learns its second half.

Refinement of e57's gat: classic development. The piece grows
to FOUR avartans — the sthayi states home twice, then the
antara climbs through a mukhda (G-A-B-C across the old rest
bar) into the upper tetrachord, dwells on taar Sa, touches Ga'
above it, and descends the whole ladder home. The bayan's
glide answer moves to the final bar, so the entire 19.2 s form
funnels into one sam.

Measured negative result (probe, kept honest by logging): the
planned claim "the antara STRIKES the string the sthayi only
whispered to" dies on good physics — an octave-below drive
contains every harmonic of the upper string, so octave
sympathy is nearly lossless (struck/whispered x1.31 vs
unplayed controls x1.06-1.36; no honest bar fits). Register
lives on the MELODY bus instead, where the contrast is x3.6.

    python3 experiments/e58_antara.py [outdir]
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
NAV = 4                        # four avartans now
LOOP_S = NAV * NB * SUB        # 19.2 s
KAFI = {2, 4, 5, 7, 9, 11, 0}
L = int(LOOP_S * SR)

# ---- sthayi + antara -------------------------------------------
# slots 28-31: the mukhda — the old rest bar becomes the climb
# into the antara. Ga' (64) holds TWO slots: a 1-slot note
# sandwiched between two taar-Sa notes reads as its neighbours
# (both contaminants AGREE and outvote the head window — the
# e57 2-sample-median lesson, sharpened).
MEL = [
    (0, 3, 50), (3, 1, 53), (4, 2, 52), (6, 1, 55),
    (7, 1, 57), (8, 1, 57), (9, 1, 55), (10, 1, 59),
    (11, 1, 57), (12, 2, 50), (14, 1, 53), (15, 1, 55),
    (16, 2, 57), (18, 1, 60), (19, 1, 59), (20, 1, 57),
    (21, 1, 55), (22, 1, 53), (23, 1, 52), (24, 3, 50),
    (27, 1, 52), (28, 1, 55), (29, 1, 57), (30, 1, 59),
    (31, 1, 60),
    (32, 2, 57), (34, 1, 59), (35, 1, 60), (36, 3, 62),
    (39, 1, 60), (40, 1, 62), (41, 2, 64), (43, 1, 62),
    (44, 1, 60), (45, 1, 59), (46, 2, 60), (48, 2, 62),
    (50, 1, 60), (51, 1, 59), (52, 1, 57), (53, 1, 55),
    (54, 2, 57), (56, 1, 55), (57, 1, 53), (58, 1, 52),
    (59, 2, 50)]               # 61-63: the bayan answers
assert all(m % 12 in KAFI for _, _, m in MEL)

mel = np.zeros(L + SR)
for at, durs, m in MEL:
    v = fdpluck(hz(m), durs * SUB + 0.25, amp=0.85)
    a = int(at * SUB * SR)
    mel[a:a + len(v)] += v
mel = mel[:L]

# ---- the drums (e55/e56 contracts, four avartans) --------------
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
GLIDE_SLOT = 61                # final bar: everything funnels in

ge_damp = ge.copy()
cut = int(SUB * SR)
fdn = int(0.06 * SR)
ge_damp[cut - fdn:cut] *= np.linspace(1, 0, fdn)
ge_damp[cut:] = 0.0

nslots = NAV * NB
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

# ---- the halo (e54/e57 contract) -------------------------------
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

# ---- own-bus: the melody ---------------------------------------
# fdpluck's played-string t60 ~ 7.7 s, so the 0.25 s ring-over
# is a SECOND NOTE at full amplitude, not a decaying ghost:
# during every note's head the bus honestly holds two pitches,
# and single-pitch HPS per window is a register-weighted coin
# flip (e57's low octave always won; the antara's C/B/D/E
# cluster flips, ledger showed windows reading the neighbour).
# Ask the polyphonic question: is the DESIGNED pitch one of the
# two sounding? dyad_pitches per note head, with a -50 cent
# shifted-design negative control (maximally far from the
# chromatic grid — an offset like -86c would falsely match the
# previous note wherever the line steps a semitone).
worst, worst_ctl = 0.0, 999.0
for at, durs, m in MEL:
    a0 = int((at * SUB + 0.02) * SR)
    a1 = int((at * SUB + 0.28) * SR)
    d = ruler.dyad_pitches(mel[a0:a1], fmin=130.0, fmax=360.0)
    dev = min(abs(1200 * np.log2(f / hz(m))) for f in d)
    ctl = min(abs(1200 * np.log2(f / hz(m)) + 50.0) for f in d)
    worst = max(worst, dev)
    worst_ctl = min(worst_ctl, ctl)
check("every note sounds as designed", worst <= 25.0,
        f"worst {worst:.1f} cents across {len(MEL)} note heads "
        f"(dyad ruler: designed pitch among the two sounding)")
check("a -50c design would not", worst_ctl > 25.0,
        f"shifted design's best match {worst_ctl:.1f} cents — "
        f"the ruler can say no")
# contour still the right ruler for LONG-SPAN statistics (dwell,
# register): per-frame flips average out over hundreds of frames
ts, fs = ruler.pitch_contour(mel, fmin=80.0, fmax=700.0)
dw = ruler.dwell_seconds(ts, fs, hz(50))
check("the line lives on Sa in both octaves",
        int(np.argmax(dw)) == 0,
        f"dwell argmax class {int(np.argmax(dw))} "
        f"({dw[0]:.1f}s on Sa/taar Sa vs {dw[9]:.1f}s on Pa)")

# register: the antara lives upstairs, the sthayi does not —
# fraction of contour frames above 240 Hz (between Pa and B),
# probe 0.174 / 0.626, bars at 0.30 / 0.45
sth = (ts >= 0.0) & (ts <= 2 * NB * SUB)
ant = (ts >= 2 * NB * SUB) & (ts <= GLIDE_SLOT * SUB)
fr_s = float((fs[sth] >= 240.0).mean())
fr_a = float((fs[ant] >= 240.0).mean())
check("the antara lives upstairs", fr_a >= 0.45 and fr_s <= 0.30,
        f"frames above 240 Hz: sthayi {fr_s:.2f} (bar <=0.30), "
        f"antara {fr_a:.2f} (bar >=0.45)")

# ---- own-bus: the halo (claims that kept their margins) --------
seg = tb[:, int(0.30 * SR):int(0.90 * SR)]
ropen = np.sqrt((seg ** 2).mean(axis=1))
oo = np.argsort(ropen)[::-1]
want = {BANK.index(50), BANK.index(55), BANK.index(62)}
gap = ropen[oo[2]] / ropen[oo[3]]
check("the opening halo is Sa's family",
        set(oo[:3].tolist()) == want and gap >= 2.0,
        f"sam-hold top-3 strings "
        f"{sorted(BANK[i] for i in oo[:3])}, 3rd/4th gap "
        f"x{gap:.1f} (bar 2.0)")
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
check("all four khali quarters are bass holes", hole <= 0.35,
        f"khali/bhari sustained bass-band slot energy {hole:.3f}")

# ---- own-bus: the answer at the single sam ---------------------
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
        f"{risep:.0f} cents risen in the final bar, "
        f"{centp:+.0f} cents from Sa at the one sam")

# ---- the mix ---------------------------------------------------
DRONE = [("pa", hz(45), 140, 0.0, -0.35, 0.55),
        ("sa+", hz(50.015), 112, 1.2, 0.15, 0.50),
        ("sa-", hz(49.985), 112, 2.4, -0.15, 0.50),
        ("SA", hz(38), 138, 3.6, 0.35, 0.75)]
loop = Loop(LOOP_S, seed=58)
for name, f0d, n, at, pan, ampd in DRONE:
    v = fdpluck2(f0d, 12.0, amp=ampd, N=n)
    for off in (0.0, 4.8, 9.6, 14.4):
        loop.add(at + off, stereo(v, pan))
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
wav = os.path.join(outdir, "e58_antara.wav")
write_wav(wav, out)
ruler.report(out, "antara")
subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", wav,
        "-q:a", "5", wav.replace(".wav", ".ogg")], check=True)

print("ALL RULERS PASS" if not fails else f"FAILED: {fails}")
sys.exit(1 if fails else 0)

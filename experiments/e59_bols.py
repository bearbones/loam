#!/usr/bin/env python3
"""e59 — bols: the drum learns its consonants.

New idea: strike FAMILIES on the e55 membrane — the tabla's
vocabulary as physics, not samples. Same drum, different
touch:

  na  — rim strike (0.55), the full commensurate stack, sings
  tun — CENTER strike (0.0): the {2,4,6}f0 family collapses by
        ~5 orders and the {3,5}f0 family remains. Strike-
        position symmetry says r=0 can only drive modes with
        angular symmetry; the uniform-drum control confirms the
        mechanism (center keeps its fund, kills (1,1)), and the
        LOADED fund dying at center shows the syahi has pushed
        the fundamental out into the annulus.
        Musical consequence: tun's strongest mode is 3f0 =
        221.7 Hz ~ A3 — THE DRUM TRANSPOSES UP A FIFTH AT ITS
        CENTER. One drum, Sa at the rim, Pa at the middle.
  te  — closed stroke: sig0=200 beats the syahi damping and the
        tone dies in ~31 ms (na: 158) — a consonant, not a vowel.
  ke  — muted bayan (sig0=45): 1% of ge's sustained bass, the
        khali stroke.

Composition: a kaida on the new vocabulary —
  dha dha te te | dha dha tun na   (x2, bhari)
  ta  ta  te te | ta  ta  tun na   (khali: ke under the ta)
  ta  ta  te te | dha dha dhin na  (bass returns into sam)

New ruler this cycle: ruler.decay_t60 (memoryless FFT-envelope
band decay — a narrowband filtfilt rings ~1/bandwidth and
floors every t60 near its own, e55's khali lesson re-earned on
a new claim).

    python3 experiments/e59_bols.py [outdir]
"""

import os
import subprocess
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))))
from loam import SR, hz, Loop, stereo, write_wav
from loam import ruler
from loam.fdstring import fdpluck2
from loam.membrane import fddrum

outdir = sys.argv[1] if len(sys.argv) > 1 else "render"
os.makedirs(outdir, exist_ok=True)
fails = []


def check(name, cond, detail):
    print(f"  {'PASS' if cond else 'FAIL'} {name}: {detail}")
    if not cond:
        fails.append(name)


LOAD, RS = 40.0, 0.45
F1, F1A, F1D = 283.8, 105.6, 141.2
F0 = 73.9                      # GCD base: na stack = (2,3,4,5) x F0

na = fddrum(F1, 1.5, strike=(0.55, 0.0), load=LOAD, rs=RS,
        sig_s=60.0)
tun = fddrum(F1, 1.5, strike=(0.0, 0.0), load=LOAD, rs=RS,
        sig_s=60.0)
te = fddrum(F1, 0.5, strike=(0.55, 0.0), load=LOAD, rs=RS,
        sig0=200.0, sig_s=60.0)
ge = fddrum(F1A, 1.0, strike=(0.30, 0.0), load=LOAD, rs=RS,
        sig0=9.0, sig_s=20.0)
ke = fddrum(F1A, 0.5, strike=(0.30, 0.0), load=LOAD, rs=RS,
        sig0=45.0, sig_s=20.0)
ge_sam = fddrum(F1D, 1.0, strike=(0.30, 0.0), load=LOAD, rs=RS,
        sig0=9.0, sig_s=20.0)


# ---- 1. center strike selects a mode family --------------------
def fam_frac(x, ks, tlo=100.0, thi=600.0):
    p = np.abs(np.fft.rfft(x * np.hanning(len(x)))) ** 2
    f = np.fft.rfftfreq(len(x), 1.0 / SR)
    tot = p[(f >= tlo) & (f <= thi)].sum()
    got = sum(p[(f >= k * F0 * 0.94) & (f <= k * F0 * 1.06)].sum()
            for k in ks)
    return float(got / tot)


ev_na = fam_frac(na, (2, 4, 6))
ev_tun = fam_frac(tun, (2, 4, 6))
check("the center strike collapses the even family",
        ev_na >= 0.5 and ev_tun <= 0.01,
        f"{{2,4,6}}f0 fraction: na {ev_na:.3f}, tun {ev_tun:.6f} "
        f"— {ev_na / max(ev_tun, 1e-12):.0f}x apart")

# ---- 2. mechanism controls (uniform drum) ----------------------
u_edge = fddrum(180.0, 1.2, strike=(0.55, 0.0), N=35)
u_cent = fddrum(180.0, 1.2, strike=(0.0, 0.0), N=35)


def ufrac(x, lo, hi):
    p = np.abs(np.fft.rfft(x * np.hanning(len(x)))) ** 2
    f = np.fft.rfftfreq(len(x), 1.0 / SR)
    return float(p[(f >= lo) & (f <= hi)].sum()
            / p[(f >= 100.0) & (f <= 800.0)].sum())


uf_c, uf_e = ufrac(u_cent, 170, 190), ufrac(u_edge, 170, 190)
u11_c, u11_e = ufrac(u_cent, 272, 302), ufrac(u_edge, 272, 302)
check("uniform control: symmetry does the selecting",
        uf_c >= 0.6 and u11_c <= 0.01 and u11_e >= 0.2,
        f"center keeps fund ({uf_c:.2f}) and kills (1,1) "
        f"({u11_c:.4f} vs edge {u11_e:.2f})")
lf_tun = fam_frac(tun, (2,))
check("the syahi pushed the fund into the annulus",
        lf_tun <= 0.01,
        f"loaded fund at center strike: {lf_tun:.6f} of power "
        f"(uniform center keeps {uf_c:.2f} — localization, "
        f"not symmetry, silences it)")

# ---- 3. one drum, two poles ------------------------------------
m_na = ruler.mode_freqs(na, k=1, fmin=100.0, fmax=600.0)[0]
m_tun = ruler.mode_freqs(tun, k=1, fmin=100.0, fmax=600.0)[0]
c_na = 1200 * np.log2(m_na / hz(50))
c_tun = 1200 * np.log2(m_tun / hz(57))
check("the rim sings Sa, the center sings Pa",
        abs(c_na) <= 25.0 and abs(c_tun) <= 25.0,
        f"na {m_na:.1f} Hz = D3{c_na:+.0f}c, tun {m_tun:.1f} Hz "
        f"= A3{c_tun:+.0f}c — a fifth apart on one drum")

# ---- 4. vowel and consonant (decay_t60) ------------------------
kw = dict(win_s=0.02, hop_s=0.003)
t_na = ruler.decay_t60(na, 135.0, 165.0, **kw)
t_tun = ruler.decay_t60(tun, 205.0, 240.0, **kw)
t_te = ruler.decay_t60(te, 100.0, 600.0, **kw)
check("te is a consonant", t_te <= 0.06
        and t_na >= 0.12 and t_tun >= 0.12,
        f"t60: na {t_na * 1000:.0f} ms, tun {t_tun * 1000:.0f} ms, "
        f"te {t_te * 1000:.0f} ms")

# ---- 5. ke is the khali stroke ---------------------------------
w0, w1 = int(0.08 * SR), int(0.28 * SR)


def bass_sus(x):
    seg = x[w0:w1] * np.hanning(w1 - w0)
    p = np.abs(np.fft.rfft(seg)) ** 2
    f = np.fft.rfftfreq(w1 - w0, 1.0 / SR)
    return float(np.sqrt(p[(f >= 30.0) & (f <= 100.0)].sum()))


kr = bass_sus(ke) / bass_sus(ge)
check("ke is muted", kr <= 0.1,
        f"sustained bass ke/ge {kr:.4f}")

# ---- the kaida -------------------------------------------------
SUB = 0.3
BOLS = (["dha", "dha", "te", "te", "dha", "dha", "tun", "na"] * 2
        + ["ta", "ta", "te", "te", "ta", "ta", "tun", "na",
           "ta", "ta", "te", "te", "dha", "dha", "dhin", "na"])
TRE = {"dha": (na, 1.0), "ta": (na, 1.0), "na": (na, 0.9),
        "tun": (tun, 0.95), "dhin": (tun, 0.95), "te": (te, 0.8)}
BAS = {"dha": (ge, 0.9), "dhin": (ge, 0.9), "ta": (ke, 0.8)}
KHALI_SLOTS = set(range(16, 28))
nslots = len(BOLS)
LOOP_S = nslots * SUB
L = int(LOOP_S * SR)

tre = np.zeros(L + 2 * SR)
bas = np.zeros(L + 2 * SR)
for k, b in enumerate(BOLS):
    a = int(k * SUB * SR)
    v, g = TRE[b]
    tre[a:a + len(v)] += v * g
    if b in BAS:
        v, g = BAS[b]
        if b == "dha" and k == 0:
            v = ge_sam           # sam arrives pressed (e56)
        bas[a:a + len(v)] += v * g
tre, bas = tre[:L], bas[:L]
drums = stereo(tre, 0.25) + stereo(bas, -0.25)

# ---- own-bus: the open/closed pattern reads back ---------------
# on the TREBLE bus (the bass rings under dha and would fill the
# late window, probe ledger); windows inside the first 120 ms
# because the whole voiced-na vocabulary lives there


def bpow(seg):
    p = np.abs(np.fft.rfft(seg * np.hanning(len(seg)))) ** 2
    f = np.fft.rfftfreq(len(seg), 1.0 / SR)
    return float(p[(f >= 130.0) & (f <= 600.0)].sum())


sus = []
for k in range(nslots):
    a = int(k * SUB * SR)
    e = bpow(tre[a:a + int(0.03 * SR)])
    late = bpow(tre[a + int(0.06 * SR):a + int(0.12 * SR)])
    sus.append(late / e)
sus = np.array(sus)
tes = np.array([b == "te" for b in BOLS])
m_te = float(np.median(sus[tes]))
m_open = float(np.median(sus[~tes]))
check("consonants and vowels read back in the kaida",
        m_te <= 1e-7 and m_open >= 1e-4,
        f"sustain median: te {m_te:.1e}, open {m_open:.1e} "
        f"(probe split 5e-12 vs 4e-3)")

# ---- own-bus: theka mechanics ----------------------------------
dbl = np.concatenate([drums, drums]).mean(axis=1)
onsets = ruler.onset_times(dbl, min_sep=0.12)
slots = {}
for t in onsets:
    k = int(round(t / SUB))
    if abs(t - k * SUB) <= 0.06:
        slots.setdefault(k % nslots, t)
check("every bol strikes", len(slots) == nslots,
        f"{len(slots)}/{nslots} onsets within 60 ms of grid")
pr = ruler.pulse_rate(drums.mean(axis=1), 2.0, 5.0,
        lo=300.0, hi=2500.0)
check("the kaida pulse reads back", abs(pr - 1.0 / SUB) <= 0.2,
        f"designed {1.0 / SUB:.2f} Hz, measured {pr:.2f} Hz")

mono_d = drums.mean(axis=1)
hann = np.hanning(w1 - w0)


def band_rms(seg):
    p = np.abs(np.fft.rfft(seg * hann)) ** 2
    f = np.fft.rfftfreq(len(seg), 1.0 / SR)
    return float(np.sqrt(p[(f >= 30.0) & (f <= 100.0)].sum()))


be = np.array([band_rms(mono_d[int(k * SUB * SR) + w0:
        int(k * SUB * SR) + w1]) for k in range(nslots)])
kh = np.array([k in KHALI_SLOTS for k in range(nslots)])
hole = float(np.median(be[kh]) / np.median(be[~kh]))
check("the khali quarter is a bass hole", hole <= 0.35,
        f"khali/bhari sustained bass-band slot energy {hole:.3f}")

# ---- the mix ---------------------------------------------------
DRONE = [("pa", hz(45), 140, 0.0, -0.35, 0.55),
        ("sa+", hz(50.015), 112, 1.2, 0.15, 0.50),
        ("sa-", hz(49.985), 112, 2.4, -0.15, 0.50),
        ("SA", hz(38), 138, 3.6, 0.35, 0.75)]
loop = Loop(LOOP_S, seed=59)
for name, f0d, n, at, pan, ampd in DRONE:
    v = fdpluck2(f0d, 12.0, amp=ampd, N=n)
    loop.add(at, stereo(v, pan))
    loop.add(at + 4.8, stereo(v, pan))
loop.add(0.0, drums * 0.8)
mix = loop.master(lp_hz=6500.0, drive=1.2)

check("seam", ruler.seam_rank(mix) <= 0.999,
        f"p{100 * ruler.seam_rank(mix):.2f}")
ch = ruler.chroma(mix.mean(axis=1))
top2 = set(np.argsort(ch)[-2:].tolist())
check("D and A are the two poles", top2 == {2, 9},
        f"top-2 classes {sorted(top2)} — and now the treble drum "
        f"itself plays both")

out = np.concatenate([mix, mix])
wav = os.path.join(outdir, "e59_bols.wav")
write_wav(wav, out)
ruler.report(out, "bols")
subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", wav,
        "-q:a", "5", wav.replace(".wav", ".ogg")], check=True)

print("ALL RULERS PASS" if not fails else f"FAILED: {fails}")
sys.exit(1 if fails else 0)

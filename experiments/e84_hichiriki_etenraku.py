#!/usr/bin/env python3
"""loam e84 — hichiriki: Etenraku, phrase A.

The winds continue ("and so forth"). Two things are new:

  - winds.reedpipe(): the OTHER wind circuit. The flute is a
    jet adding energy at a labium; this is a pressure-driven
    REED VALVE on a cylindrical quarter-wave bore (clarinet
    family, after Cook/Smith). The open end inverts the
    reflection, so odd harmonics dominate — measured +44 to
    +59 dB odd/even on the raw model, the signature the ruler
    holds. Same block-vectorized loop and self-tuning-by-
    listening practice as flute().
  - nihon.hichiriki(): the gesture layer — EMBAI, the famous
    wide approach glide (~120 cents, twice the shakuhachi's
    meri: the big soft reed bends further than any embouchure),
    the nasal 0.9-1.9 kHz formant, and reed warmth (the raw
    valve is square-pure; asymmetric waveshaping puts the even
    partials back, because a real reed never closes with
    perfect symmetry).

The demo is the opening phrase of Etenraku (hyojo mode on E,
melodic contour D-EEBBABEEEDE per the standard transcription),
the most famous melody in gagaku, over a soft sho-like drone.
Haya yo-hyoshi: 4 slow beats to the bar, 38.4 s loop.

    python3 experiments/e84_hichiriki_etenraku.py [outdir]
"""

import os
import sys

import numpy as np
from scipy.signal import butter, sosfilt

sys.path.insert(0, os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))))
from loam import SR, hz, stereo, write_wav
from loam import ruler
from loam.nihon import hichiriki
from loam.winds import reedpipe
from loam.pads import padsynth_stereo
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


LOOP_S = 38.4
N = int(LOOP_S * SR)
BEAT = 1.6

# (midi, beats, embai_cents, yuri_c) — Etenraku phrase A, hyojo:
# pickup D5 then E E B B A B E E E D E. Subphrase heads take the
# deep embai; the long final E carries yuri.
MELODY = [
    (74, 1, 140.0, 0.0),          # D5 pickup — the deep pour
    (76, 2, 30.0, 0.0),
    (76, 2, 25.0, 0.0),
    (71, 2, 120.0, 0.0),          # B4 — new subphrase
    (71, 2, 25.0, 0.0),
    (69, 2, 100.0, 0.0),          # A4 — the low turn
    (71, 2, 30.0, 0.0),
    (76, 2, 120.0, 0.0),          # E5 — the return
    (76, 1, 25.0, 0.0),
    (76, 1, 25.0, 0.0),
    (74, 2, 40.0, 0.0),
    (76, 3, 30.0, 18.0),          # the long E, yuri blooming
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


NOTES, STARTS, DURS = [], [], []
mel = np.zeros((N, 2))
t = 0.2
for i, (m, beats, em, yc) in enumerate(MELODY):
    dur = beats * BEAT - 0.12                 # the re-breath gap
    v = hichiriki(hz(m), dur, embai=em, yuri_c=yc, seed=m + 3 * i)
    NOTES.append(v)
    STARTS.append(t)
    DURS.append(dur)
    add_wrap(mel, t, stereo(v * 0.9, 0.04))
    t += beats * BEAT

drone = 0.5 * padsynth_stereo(LOOP_S, hz(52),
        [h ** -1.7 for h in range(1, 9)], bw_cents=30.0, seed=31) \
    + 0.30 * padsynth_stereo(LOOP_S, hz(59),
        [h ** -2.0 for h in range(1, 7)], bw_cents=30.0, seed=33)
drone *= 0.9 / (np.abs(drone).max() + 1e-12)

dry = 0.95 * mel + 0.30 * drone
wet = reverb_loop(dry, t60=1.8, size=1.1)
mix = 0.85 * dry + 0.22 * wet
mix *= 0.92 / (np.abs(mix).max() + 1e-12)
write_wav(os.path.join(outdir, "e84_hichiriki_etenraku.wav"), mix)

# ---- rulers ------------------------------------------------------
print("e84 rulers:")

# 1. seam
check("seam", ruler.seam_rank(mix) <= 0.999,
        f"p{100 * ruler.seam_rank(mix):.2f}")


def _oe_db(v, f0):
    """Odd/even partial energy on the sustain."""
    seg = v[int(0.4 * SR):int(1.0 * SR)]
    n4 = 4 * len(seg)
    sp = np.abs(np.fft.rfft(seg * np.hanning(len(seg)), n4)) ** 2
    fq = np.fft.rfftfreq(n4, 1.0 / SR)

    def he(h):
        sel = (fq > f0 * h * 0.94) & (fq < f0 * h * 1.06)
        return sp[sel].max() if sel.any() else 1e-30
    return 10.0 * np.log10((he(1) + he(3) + he(5))
                           / (he(2) + he(4) + he(6)))


# 2. the bore is cylindrical: raw reedpipe is odd-dominant
raw = reedpipe(hz(69), 1.2, seed=69)
oe_raw = _oe_db(raw, hz(69))
check("odd_bore", oe_raw >= 15.0,
        f"raw reedpipe odd/even {oe_raw:+.1f} dB (want >= 15)")

# 3. the reed is asymmetric: hichiriki restores the evens
hv = hichiriki(hz(69), 1.2, embai=0.0, seed=69)
oe_h = _oe_db(hv, hz(69))
check("reed_warmth", oe_h <= oe_raw - 15.0,
        f"hichiriki odd/even {oe_h:+.1f} dB, "
        f"{oe_raw - oe_h:.1f} dB of evens restored")

# 4. every note settles on its written pitch AND IS its written
# pitch (the contour claim and the tuning claim are one ruler):
# measure late in the note, past the embai tail
worst, ident = 0.0, True
for v, (m, beats, em, yc), dur in zip(NOTES, MELODY, DURS):
    inst = ruler.if_pitch(v, hz(m))
    s0 = max(0.5, dur - 0.6)
    c = 1200.0 * np.log2(np.median(
            inst[int(s0 * SR):int((dur - 0.15) * SR)]) / hz(m))
    worst = max(worst, abs(c))
    ident = ident and abs(c) <= 50.0
check("contour", ident and worst <= 20.0,
        f"12 notes all land their written midi, worst late-sustain "
        f"center {worst:.1f} c")


def _early_peak(v, f0):
    seg = v[int(0.05 * SR):int(0.30 * SR)]
    n4 = 8 * len(seg)
    sp = np.abs(np.fft.rfft(seg * np.hanning(len(seg)), n4))
    fq = np.fft.rfftfreq(n4, 1.0 / SR)
    sel = np.where((fq > f0 * 0.70) & (fq < f0 * 1.15))[0]
    return 1200.0 * np.log2(fq[sel[int(np.argmax(sp[sel]))]] / f0)


# 5. embai, by e82's twin-delta ruler: deep glides carry at least
# half their written slide vs same-seed glideless twins
fr_l = []
for i, (v, (m, beats, em, yc)) in enumerate(zip(NOTES, MELODY)):
    if em < 100.0:
        continue
    tw = hichiriki(hz(m), DURS[i], embai=0.0, yuri_c=yc,
            seed=m + 3 * i)
    delta = _early_peak(v, hz(m)) - _early_peak(tw, hz(m))
    fr_l.append(delta / (-0.63 * em))
check("embai", min(fr_l) >= 0.5,
        f"{len(fr_l)} deep glides carry "
        f"{[f'{100 * x:.0f}%' for x in fr_l]} of design")

# 6. the nasal formant, in the register where the claim is
# physical (at E5 the odd-harmonic comb skips the band entirely)
sos_f = butter(2, [900.0, 1900.0], btype="bandpass", fs=SR,
        output="sos")
sos_l = butter(2, [250.0, 700.0], btype="bandpass", fs=SR,
        output="sos")


def _bandgain(v):
    return 20.0 * np.log10(rms(sosfilt(sos_f, v))
                           / rms(sosfilt(sos_l, v)))


gains = []
for v, (m, beats, em, yc) in zip(NOTES, MELODY):
    if m not in (69, 71):
        continue
    gains.append(_bandgain(v) - _bandgain(reedpipe(hz(m), 1.2,
            seed=m)))
check("formant", min(gains) >= 5.0,
        f"{len(gains)} low-register notes carry the presence band "
        f"at {min(gains):+.1f} to {max(gains):+.1f} dB over raw")

# 7. hyojo rests on E, B beneath (relative claim, e35)
ch = ruler.chroma(mix)
top2 = set(np.argsort(ch)[-2:].tolist())
check("chroma_poles", top2 == {4, 11},
        f"top-2 classes {sorted(top2)} (want E=4, B=11); "
        f"E {ch[4]:.2f} B {ch[11]:.2f}")

ruler.report(mix, "e84_hichiriki_etenraku")
print(f"\n{'ALL PASS' if not fails else 'FAILS: ' + str(fails)}")
sys.exit(1 if fails else 0)

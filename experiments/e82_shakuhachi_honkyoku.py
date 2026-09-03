#!/usr/bin/env python3
"""loam e82 — shakuhachi: a honkyoku for the temple bell.

The winds, on operator direction. loam.nihon.shakuhachi():
the self-tuning waveguide flute plus a gesture layer —

  - muraiki: turbulent breath burst decaying into tone (an
    in-bore breath envelope AND a direct-radiation hiss,
    because the jet nonlinearity saturates: pushing breath
    through the bore gained 1.9 dB where the ear wants a gust);
  - meri approach (scoop): the note slides up into pitch over
    ~0.45 s via a time-warp of the tuned note (measured: the
    waveguide's own tone doesn't speak until ~0.25 s, so a
    faster scoop dies inside the attack fog — and jet pressure
    cannot bend pitch at all, so the warp is the only honest
    scoop);
  - yuri: slow deep pitch vibrato entering after ~0.9 s;
  - center correction, wander kept: the tone wanders +-25
    cents (the bamboo's life); only the median IF error is
    folded back, so the written note is the note's center.

New ruler earned: ruler.if_pitch — spectral-peak detectors
scatter +-100 cents on breathy tones; the analytic phase of
the zero-phase narrowband-filtered signal does not care.

The piece: four breath-paced phrases in D minyo over the e79
temple bell (D2 at the seam, D3 at the half). 38.4 s loop.

    python3 experiments/e82_shakuhachi_honkyoku.py [outdir]
"""

import os
import sys

import numpy as np
from scipy.signal import butter, sosfilt

sys.path.insert(0, os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))))
from loam import SR, hz, stereo, write_wav
from loam import ruler
from loam.nihon import shakuhachi
from loam.modal import strike, CHURCH_BELL
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


def db(r):
    return 20.0 * np.log10(r + 1e-30)


LOOP_S = 38.4
N = int(LOOP_S * SR)

# (start, midi, dur, muraiki, scoop_c, yuri_c, amp) — D minyo
PHRASES = [
    (1.1, 62, 3.4, 0.90, 55.0, 0.0, 0.90),
    (5.4, 65, 1.7, 0.25, 30.0, 0.0, 0.80),
    (7.2, 67, 4.4, 0.35, 25.0, 26.0, 0.95),      # the yuri note
    (13.4, 69, 1.5, 0.20, 20.0, 0.0, 0.80),
    (15.0, 72, 2.8, 0.85, 40.0, 0.0, 1.00),
    (17.9, 69, 1.4, 0.15, 18.0, 0.0, 0.75),
    (19.4, 67, 3.4, 0.30, 22.0, 22.0, 0.90),
    (24.6, 65, 2.0, 0.30, 30.0, 0.0, 0.80),
    (26.8, 62, 5.2, 0.95, 65.0, 20.0, 1.00),     # the last breath
]
BELLS = [(0.0, 38, 9.0, 1.0), (19.2, 50, 7.0, 0.45)]


def add_wrap(bus, t, ss):
    i0 = int(round(t * SR)) % N
    n = len(ss)
    if i0 + n <= N:
        bus[i0:i0 + n] += ss
    else:
        k = N - i0
        bus[i0:] += ss[:k]
        bus[:n - k] += ss[k:]


NOTES = []
flt = np.zeros((N, 2))
for i, (t, m, dur, mur, sc, yc, a) in enumerate(PHRASES):
    v = shakuhachi(hz(m), dur, muraiki=mur, scoop=sc,
            yuri_c=yc, seed=11 + 7 * i)
    NOTES.append(v)
    add_wrap(flt, t, stereo(v * a, 0.05))

bell = np.zeros((N, 2))
for t, m, t60, a in BELLS:
    b = strike(hz(m), t60, CHURCH_BELL, amp=1.0, detune=3.0,
            rng=np.random.default_rng(m), knock=0.03)
    b = b / (np.abs(b).max() + 1e-12)
    add_wrap(bell, t, stereo(b * a, 0.0))

dry = 0.85 * flt + 0.55 * bell
wet = reverb_loop(dry, t60=2.2, size=1.2)
mix = 0.82 * dry + 0.30 * wet
mix *= 0.92 / (np.abs(mix).max() + 1e-12)
write_wav(os.path.join(outdir, "e82_shakuhachi_honkyoku.wav"),
        mix)

# ---- rulers ------------------------------------------------------
print("e82 rulers (per-note claims on the note's own buffer):")

# 1. seam
check("seam", ruler.seam_rank(mix) <= 0.999,
        f"p{100 * ruler.seam_rank(mix):.2f}")

# 2. every note centers on its written pitch (wander kept, so
# the gate is the center, not the instant)
worst = 0.0
for v, (t, m, dur, mur, sc, yc, a) in zip(NOTES, PHRASES):
    inst = ruler.if_pitch(v, hz(m))
    s0, s1 = max(0.5, 0.3 * dur), dur - 0.3
    c = 1200.0 * np.log2(np.median(
            inst[int(s0 * SR):int(s1 * SR)]) / hz(m))
    worst = max(worst, abs(c))
check("centers", worst <= 20.0,
        f"9 notes, worst sustain center {worst:.1f} cents")

# 3. the meri approach, as a TWIN DELTA on the strongest early
# line. A breathy attack is not one clean chirp: this piece's
# C5 opens on TWO tonal lines ~90c apart at comparable power
# (plus transients), so no median — IF or otherwise — reliably
# names "the" pitch there, and single-note early reads
# scattered from +14c to 246% of design across attempts. The
# same-seed scoopless twin shares the exact line cluster; the
# FFT-peak delta between note and twin cancels the cluster and
# isolates the written slide (C5 verified: -26.3c measured on
# a -26c design). Gate: at least half the written slide,
# every deep note.
def _early_peak(v, f0):
    seg = v[int(0.05 * SR):int(0.30 * SR)]
    n4 = 8 * len(seg)
    sp = np.abs(np.fft.rfft(seg * np.hanning(len(seg)), n4))
    fq = np.fft.rfftfreq(n4, 1.0 / SR)
    sel = np.where((fq > f0 * 0.80) & (fq < f0 * 1.15))[0]
    k = sel[int(np.argmax(sp[sel]))]
    a2, b2, c2 = sp[k - 1], sp[k], sp[k + 1]
    den = a2 - 2 * b2 + c2
    k = k + (0.5 * (a2 - c2) / den if abs(den) > 1e-12 else 0.0)
    return 1200.0 * np.log2(k * SR / n4 / f0)


sc_frac = []
for i, (v, (t, m, dur, mur, sc, yc, a)) in enumerate(
        zip(NOTES, PHRASES)):
    if sc < 40.0:
        continue
    tw = shakuhachi(hz(m), dur, muraiki=mur, scoop=0.0,
            yuri_c=yc, seed=11 + 7 * i)
    delta = _early_peak(v, hz(m)) - _early_peak(tw, hz(m))
    sc_frac.append(delta / (-0.70 * sc))
check("meri_scoop", min(sc_frac) >= 0.5,
        f"deep notes carry {[f'{100 * x:.0f}%' for x in sc_frac]}"
        f" of the written slide vs scoopless twins")

# 4. muraiki: the gust is in the hiss band at the attack
sos_h = butter(4, [1500.0, 6500.0], btype="bandpass", fs=SR,
        output="sos")
mur_x, soft_x = [], []
for v, (t, m, dur, mur, sc, yc, a) in zip(NOTES, PHRASES):
    h = sosfilt(sos_h, v)
    x = db(rms(h[:int(0.25 * SR)])
           / rms(h[int(0.5 * dur * SR):int((dur - 0.3) * SR)]))
    (mur_x if mur >= 0.8 else soft_x).append(x)
# separation gate, not absolutes: a muraiki-0.3 note still has
# a small written gust — the claim is that deep and shallow
# breath SEPARATE in the measurement
check("muraiki", min(mur_x) >= 6.0
        and min(mur_x) - max(soft_x) >= 4.0,
        f"gust notes {[f'{x:.1f}' for x in mur_x]} dB, "
        f"soft max {max(soft_x):.1f}, "
        f"separation {min(mur_x) - max(soft_x):.1f} dB")

# 5. yuri on the featured note: a line at the written rate
v = NOTES[2]
inst = ruler.if_pitch(v, hz(67))
seg = inst[int(1.5 * SR):int(4.1 * SR)]
hopn = 441
d = np.array([np.median(seg[i:i + hopn])
              for i in range(0, len(seg) - hopn, hopn)])
d = 1200.0 * np.log2(d / hz(67))
d = d - d.mean()
sp = np.abs(np.fft.rfft(d * np.hanning(len(d))))
fr = np.fft.rfftfreq(len(d), hopn / SR)
sel = (fr > 0.8) & (fr < 15.0)
pk = float(fr[sel][np.argmax(sp[sel])])
prom = float(sp[sel].max() / np.median(sp[sel]))
check("yuri", abs(pk - 2.8) <= 0.6 and prom >= 2.2
        and float(np.std(d)) >= 10.0,
        f"line {pk:.2f} Hz (want 2.8) prom {prom:.1f}x "
        f"depth-std {np.std(d):.1f}c")

# 6. the bell is a bell, and it tolls where written
b38 = strike(hz(38), 9.0, CHURCH_BELL, amp=1.0, detune=3.0,
        rng=np.random.default_rng(38), knock=0.03)
mf = ruler.mode_freqs(b38, k=6, fmin=30.0, fmax=500.0)
hum_ok = bool(np.any(np.abs(mf / (0.5 * hz(38)) - 1.0) < 0.015))
pri_ok = bool(np.any(np.abs(mf / hz(38) - 1.0) < 0.015))
# mark on the knock's band (e79: a bell's low modes bloom over
# tens of ms; the contact knock above the ring marks the time)
sos_k = butter(4, 2500.0, btype="highpass", fs=SR, output="sos")
fx, dt = ruler.flux_series(sosfilt(sos_k, np.concatenate(
        [bell.mean(axis=1), bell.mean(axis=1)])), frame=512,
        hop=128)
tf = np.arange(len(fx)) * dt
toll_ok = True
for t, m, t60, a in BELLS:
    c = t + LOOP_S
    sel2 = (tf >= c - 0.2) & (tf <= c + 0.2)
    off = tf[sel2][np.argmax(fx[sel2])] - c
    toll_ok = toll_ok and abs(off) <= 0.030
check("bell", hum_ok and pri_ok and toll_ok,
        f"hum {hum_ok} prime {pri_ok} tolls-on-time {toll_ok}")

# 7. the two poles: this honkyoku rests on D and dwells on G
# (the long yuri note is the piece's peak — the fourth carries
# the weight, as minyo phrases do). e35's lesson stands:
# honest chroma claims are relative — the claim is top-2
# membership, D and G and nothing else.
ch = ruler.chroma(mix)
top2 = set(np.argsort(ch)[-2:].tolist())
check("chroma_poles", top2 == {2, 7},
        f"top-2 classes {sorted(top2)} (want D=2, G=7); "
        f"D {ch[2]:.2f} G {ch[7]:.2f}")

ruler.report(mix, "e82_shakuhachi_honkyoku")
print(f"\n{'ALL PASS' if not fails else 'FAILS: ' + str(fails)}")
sys.exit(1 if fails else 0)

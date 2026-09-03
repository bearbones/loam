#!/usr/bin/env python3
"""loam — "Avartan". One full cycle, returning to sam.

The showcase of the raga arc (sessions 37-77): a complete
miniature performance in Kafi over D, 96 seconds, seamless.
The form IS the loop: a tihai countdown lands its final Sa on
the loop's own first instant, so the climax resolves forever
into the stillness it grew from. An avartan — the cycle that
returns.

  0.0- 24.0  ALAP    tanpura alone, then the sarangi: three
                     unmetered phrases — a rise to ga held
                     with andolan, a reach through ma, a
                     settling through komal ni. No pulse.
  24.0- 38.4  JOR    pulse arrives without drums: jawari
                     plucks tick at 2.08 Hz; the bow moves in
                     laya.
  38.4- 67.2  GAT    the theka enters (tintal, khali hole and
                     all); the sarangi sings the gat, home a
                     breath before every sam.
  67.2- 86.4  JHALA  the strum: melody every 4th stroke,
                     chikari filling, 8.33 strokes/s. The bow
                     rests; the theka keeps time.
  86.4- 96.0  TIHAI  ga-Re-Sa three times at a 0.84 s lag,
                     arithmetic landing the last Sa at
                     96.0 == 0.0: the sam, the pressed drum,
                     one bright pluck ringing into the drone.

Verified: seam, section pulse signatures (alap has no line;
jor ticks; jhala hums 8.33), sarangi holds by pitch contour,
the andolan by rate and depth, theka khali hole, tihai
self-similarity at its lag, sam arithmetic, halo and balance
gates, Sa crowning the chroma.

    python3 songs/avartan.py [outdir]
"""

import os
import sys

import numpy as np
from scipy.signal import butter, sosfilt

sys.path.insert(0, os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))))
from loam import SR, hz, Loop, stereo, write_wav
from loam import ruler
from loam.fdstring import fdbow, fdpluck2, fdsym
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


LOOP_S = 96.0
L = int(LOOP_S * SR)


def add_wrap(buf, at, v):
    idx = (int(at * SR) + np.arange(len(v))) % len(buf)
    if buf.ndim == 2 and v.ndim == 2:
        np.add.at(buf, idx, v)
    else:
        np.add.at(buf, idx, v)


# ---- tanpura: pa sa sa SA, cycling all 96 s --------------------
print("== tanpura ==")
DRONE = [("pa", hz(45), 140, 0.0, -0.35, 0.55),
        ("sa+", hz(50.015), 112, 1.2, 0.15, 0.50),
        ("sa-", hz(49.985), 112, 2.4, -0.15, 0.50),
        ("SA", hz(38), 138, 3.6, 0.35, 0.75)]
drone_st = np.zeros((L, 2))
for name, f0d, n, at, pan, ampd in DRONE:
    v = fdpluck2(f0d, 12.0, amp=ampd, N=n)
    sv = stereo(v, pan)
    for cyc in range(10):
        add_wrap(drone_st, at + 9.6 * cyc, sv)

# ---- sarangi: five takes, each entered through the shelf -------
print("== sarangi ==")


def bow_take(knots, vtop, dur, andol=None):
    """One phrase: f0 from knots [(t, midi)...], entry step to
    the 0.085 shelf, 0.6 s ramp to vtop, lift 1.1 s before the
    end (FB -> 0, the certified ring release). andol = (t0, t1,
    rate_hz, depth_c) modulates the hold."""
    tt = np.arange(int(dur * SR)) / SR
    f0 = np.interp(tt, [t for t, _ in knots],
            [hz(m) for _, m in knots])
    if andol is not None:
        a0, a1, arate, adep = andol
        w = ((tt >= a0) & (tt <= a1)).astype(float)
        # soft edges so the wobble fades in and out
        w = np.convolve(w, np.hanning(int(0.3 * SR))
                / np.hanning(int(0.3 * SR)).sum(), "same")
        c = adep * np.sin(2 * np.pi * arate * (tt - a0)) * w
        f0 = f0 * 2.0 ** (c / 1200.0)
    vb = np.interp(tt, [0.0, 0.6, max(dur - 1.4, 0.7),
            dur - 1.1, dur],
            [0.085, vtop, vtop, 0.085, 0.085])
    FB = np.where(tt < dur - 1.1, 1e4 * vb, 0.0)
    return fdbow(f0, dur, FB=FB, vb=vb, sig0=4.0, raw=True)


sar = np.zeros(L)

# alap phrase 1 (2.4-9.6): Sa -> Re -> ga, andolan on ga, back
P1 = [(0.0, 50), (1.2, 50), (1.6, 52), (2.4, 52), (2.9, 53),
      (5.3, 53), (5.9, 52), (6.3, 50), (7.2, 50)]
p1 = bow_take(P1, 0.105, 7.2, andol=(3.0, 5.2, 1.25, 35.0))
add_wrap(sar, 2.4, p1)

# alap phrase 2 (11.4-18.6): ga -> ma -> ga -> Re, the reach
P2 = [(0.0, 53), (1.0, 53), (1.5, 55), (3.1, 55), (3.7, 53),
      (4.9, 53), (5.5, 52), (7.2, 52)]
p2 = bow_take(P2, 0.105, 7.2)
add_wrap(sar, 11.4, p2)

# alap phrase 3 (19.8-24.6): Sa -> ni- touch -> Sa, settling
P3 = [(0.0, 50), (1.6, 50), (1.9, 48), (2.2, 48), (2.5, 50),
      (4.8, 50)]
p3 = bow_take(P3, 0.100, 4.8)
add_wrap(sar, 19.8, p3)

# jor (25.2-38.4): the line moves in laya, 0.3 s glides
PJ = [(0.0, 50), (0.9, 50), (1.2, 52), (1.8, 52), (2.1, 53),
      (3.0, 53), (3.3, 55), (3.9, 55), (4.2, 53), (5.1, 53),
      (5.4, 52), (6.0, 52), (6.3, 53), (7.2, 53), (7.5, 52),
      (8.1, 52), (8.4, 50), (9.9, 50), (10.2, 52), (10.8, 52),
      (11.1, 50), (13.2, 50)]
pj = bow_take(PJ, 0.11, 13.2)
add_wrap(sar, 25.2, pj)

# gat (38.4-67.2): e66's certified sentence three times; the
# third reaches ma before coming home. Home 0.3 s before every
# 9.6 s boundary, held through it — mukhda fashion.
S = [(0.0, 50), (0.9, 50), (1.2, 52), (1.8, 52), (2.1, 53),
     (3.0, 53), (3.3, 52), (3.9, 52), (4.2, 50), (5.1, 50),
     (5.4, 52), (6.0, 52), (6.3, 53), (7.2, 53), (7.5, 52),
     (8.1, 52), (8.4, 50), (9.6, 50)]
S3 = [(t, (55 if (m == 53 and 6.0 < t < 7.5) else m))
      for t, m in S]
KG = ([(t, m) for t, m in S]
      + [(t + 9.6, m) for t, m in S[1:]]
      + [(t + 19.2, m) for t, m in S3[1:]])
pg = bow_take(KG, 0.11, 28.8)
add_wrap(sar, 38.4, pg)

sarn = sar / (np.abs(sar).max() + 1e-12)

# ---- theka: tintal, 12 avartans, sam at the loop point ---------
print("== theka ==")
LOAD, RS = 40.0, 0.45
F1, F1A, F1D = 283.8, 105.6, 141.2
na = fddrum(F1, 1.5, strike=(0.55, 0.0), load=LOAD, rs=RS,
        sig_s=60.0)
tun = fddrum(F1, 1.5, strike=(0.0, 0.0), load=LOAD, rs=RS,
        sig_s=60.0)
ge = fddrum(F1A, 1.0, strike=(0.30, 0.0), load=LOAD, rs=RS,
        sig0=9.0, sig_s=20.0)
ge_sam = fddrum(F1D, 1.0, strike=(0.30, 0.0), load=LOAD, rs=RS,
        sig0=9.0, sig_s=20.0)
TREB = {"dha": (na, 1.0), "dhin": (tun, 0.95),
        "tin": (tun, 0.95), "ta": (na, 0.9)}
BASS = {"dha": (ge, 0.9), "dhin": (ge, 0.9)}
SUB = 0.3
THEKA = ["dha", "dhin", "dhin", "dha", "dha", "dhin", "dhin",
        "dha", "dha", "tin", "tin", "ta", "ta", "dhin", "dhin",
        "dha"]
KHALI = {9, 10, 11, 12}
tre = np.zeros(L)
bas = np.zeros(L)
for av in range(12):
    for i, b in enumerate(THEKA):
        t = 38.4 + av * 4.8 + i * SUB
        if t >= 93.8:            # the tabla rests for the tihai
            continue
        v, g = TREB[b]
        add_wrap(tre, t, v * g)
        if b in BASS:
            v, g = BASS[b]
            add_wrap(bas, t, v * g)
# the arrival: sam of the whole cycle at t = 0, pressed bayan
add_wrap(tre, 0.0, na * 1.1)
add_wrap(bas, 0.0, ge_sam * 1.0)
drums = stereo(tre, 0.4) + stereo(bas, -0.35)

# ---- plucked voices: jor ticks, jhala, tihai -------------------
print("== plucks ==")
cache = {}


def mpluck(m):
    if m not in cache:
        cache[m] = fdpluck2(hz(m), 1.2, amp=1.0, pick=0.28)
    return cache[m]


mel = np.zeros(L)
chik = np.zeros(L)

# jor ticks: Sa-Sa-ga-Sa on the 0.48 s grid, sparse then full
# the luthier's toolkit from Nine Landings (operator: "notes on
# top are missing the time mark"): write each voice speak_time
# early so perceived attacks sit on the grid, and stamp every
# melody-family stroke with a mizrab click — a low string BLOOMS
# over tens of ms and cannot mark time by itself.
GUARD = 0.004
_stc = {}


def spk(key, v):
    if key not in _stc:
        _stc[key] = ruler.speak_time(v) - GUARD
    return _stc[key]


_rngc = np.random.default_rng(0x5EED)
click = _rngc.standard_normal(int(0.008 * SR)) \
    * np.hanning(int(0.008 * SR))
click = sosfilt(butter(3, [3500.0, 9000.0], btype="bandpass",
        fs=SR, output="sos"), click)
click = click / np.abs(click).max()


def mstroke(bus, at, m, g=1.0):
    add_wrap(bus, at - spk(("m", m), mpluck(m)), mpluck(m) * g)
    add_wrap(bus, at, click * 0.16 * g)


JORP = [50, None, 53, 50] * 8
for k, m in enumerate(JORP):
    if m is None or (k < 8 and k % 2):
        continue
    mstroke(mel, 24.0 + 0.48 * k, m, 1.4)

# jhala + tihai: 240 slots of 0.12 s from 67.2 to 96.0
DT = 0.12
LINE = [50, 52, 53, 55, 53, 52, 50, 48, 47, 48, 50, 52,
        53, 52, 50, 48, 50, 52, 50, 50]
TIHAI = {222: (53, 1.0), 224: (52, 1.0), 226: (50, 1.0),
         229: (53, 1.1), 231: (52, 1.1), 233: (50, 1.1),
         236: (53, 1.2), 238: (52, 1.2)}
CH_DA = fdpluck2(hz(62) * 2 ** (0.8 / 1200), 0.9, amp=0.38,
        pick=0.24)
CH_RA = fdpluck2(hz(62) * 2 ** (-3.2 / 1200), 0.9, amp=0.33,
        pick=0.33)
# the timekeeper never lapses (Nine Landings): chikari on EVERY
# slot; melody and tihai ride on top of the tick, not instead
for j in range(240):
    t = 67.2 + DT * j
    v = CH_DA if j % 2 else CH_RA
    add_wrap(chik, t - spk(("c", j % 2), v), v)
    if j in TIHAI:
        m, g = TIHAI[j]
        mstroke(mel, t, m, g)
    elif j % 4 == 0 and j < 222:
        mstroke(mel, t, LINE[(j // 4) % 20])
# the tihai's last Sa IS the sam: one bright pluck at zero
mstroke(mel, 0.0, 50, 1.3)

meln = mel / (np.abs(mel).max() + 1e-12)
chikn = chik / (np.abs(chik).max() + 1e-12)

# ---- taraf: the halo hears everything --------------------------
print("== taraf ==")
drive = sarn * 0.6 + meln * 0.3 + chikn * 0.15
BANK = [50, 52, 53, 55, 57, 59, 60, 62]
_, tb = fdsym([hz(n) for n in BANK], drive, buses=True,
        jawari=True, gain=5000.0)
pans = np.linspace(-0.55, 0.55, len(BANK))
tnorm = np.abs(tb).max() + 1e-12
taraf_st = np.zeros((L, 2))
for b_, p in zip(tb, pans):
    gg = (b_[:L] / tnorm) * 0.05
    taraf_st[:, 0] += gg * np.cos((p + 1) * np.pi / 4)
    taraf_st[:, 1] += gg * np.sin((p + 1) * np.pi / 4)

# ---- the mix ---------------------------------------------------
print("== mix ==")
G_SAR, G_MEL, G_CHIK, G_DRUM = 0.72, 0.42, 0.26, 0.68
loop = Loop(LOOP_S, seed=96)
loop.add(0.0, drone_st * 0.9)
loop.add(0.0, stereo(sarn * G_SAR, 0.12))
loop.add(0.0, stereo(meln * G_MEL, 0.10))
loop.add(0.0, stereo(chikn * G_CHIK, -0.5))
loop.add(0.0, drums * G_DRUM)
loop.add(0.0, taraf_st)
mix = loop.master(lp_hz=6500.0, drive=1.2)
mono = mix.mean(axis=1)

# ================= the rulers ===================================
print("== rulers ==")
check("seam", ruler.seam_rank(mix) <= 0.999,
        f"p{100 * ruler.seam_rank(mix):.2f}")


# prominence = line power over the spectrum's own median: an
# absolute ruler. Crown ratios fail here because the tanpura's
# strike comb (4 plucks / 9.6 s cycle, lines near 0.83n Hz)
# carpets EVERY window and crowns the quiet ones.
def flux_line(a, b, lo, hi):
    fr, sp = ruler.flux_spectrum(mono[int(a * SR):int(b * SR)])
    m = (fr > 1.2) & (fr < 20.0)
    med = float(np.median(sp[m]))
    bsel = (fr >= lo) & (fr <= hi)
    i = int(np.argmax(sp[bsel]))
    return float(fr[bsel][i]), float(sp[bsel][i] / med)


f_alap = flux_line(4.0, 22.0, 1.8, 12.0)
f_jor = flux_line(24.4, 38.0, 1.9, 2.3)
f_jhala = flux_line(68.0, 86.0, 7.8, 8.9)
f_gat = flux_line(39.0, 67.0, 3.0, 3.7)
check("the sections keep their clocks",
        abs(f_jor[0] / (1 / 0.48) - 1) <= 0.02 and f_jor[1] >= 4.5
        and abs(f_jhala[0] / (1 / 0.12) - 1) <= 0.01
        and f_jhala[1] >= 3.5
        and abs(f_gat[0] / (1 / 0.3) - 1) <= 0.02
        and f_gat[1] >= 20.0,
        f"jor ticks at {f_jor[0]:.2f} Hz ({f_jor[1]:.0f}x "
        f"median), gat theka at {f_gat[0]:.2f} ({f_gat[1]:.0f}x), "
        f"jhala strums at {f_jhala[0]:.2f} ({f_jhala[1]:.0f}x) — "
        f"written 2.083 / 3.333 / 8.333")
check("the alap does not tick",
        f_alap[1] <= 8.0,
        f"alap's strongest rhythm line is {f_alap[1]:.1f}x its "
        f"spectrum median (the tanpura comb) vs the sections' "
        f"{f_jor[1]:.0f}/{f_gat[1]:.0f}/{f_jhala[1]:.0f}x — "
        f"stillness, then pulse")

ts, fsc = ruler.pitch_contour(sar, fmin=80.0, fmax=500.0)
HOLDS = [("alap ga", 5.6, 7.4, 53), ("alap ma", 12.6, 14.3, 55),
        ("alap Sa", 22.5, 24.0, 50), ("jor Sa end", 36.6, 37.8, 50),
        ("gat Sa|sam1", 42.8, 43.4, 50),
        ("gat ga", 40.7, 41.3, 53),
        ("gat Sa|sam2", 52.4, 53.0, 50),
        ("gat ma", 63.8, 64.4, 55),
        ("gat Sa home", 62.0, 62.6, 50)]
worst = 0.0
for nm, a, b, m in HOLDS:
    sel = (ts >= a) & (ts <= b)
    med = float(np.median(fsc[sel]))
    worst = max(worst, abs(1200 * np.log2(med / hz(m))))
check("the bow lands its holds", worst <= 25.0,
        f"worst of {len(HOLDS)} holds across alap/jor/gat: "
        f"{worst:.1f}c")

sel = (ts >= 5.6) & (ts <= 7.4)
arate, adep = ruler.ornament_profile(ts[sel], fsc[sel])
check("the andolan swings as written",
        abs(arate - 1.25) <= 0.3 and 20.0 <= adep <= 70.0,
        f"ga hold wobbles at {arate:.2f} Hz, depth {adep:.0f}c "
        f"(written 1.25 Hz, 35c)")

w0, w1 = int(0.08 * SR), int(0.28 * SR)
hann = np.hanning(w1 - w0)
mono_d = drums.mean(axis=1)


def bassband(seg):
    p = np.abs(np.fft.rfft(seg * hann)) ** 2
    f = np.fft.rfftfreq(len(seg), 1.0 / SR)
    return float(np.sqrt(p[(f >= 30.0) & (f <= 100.0)].sum()))


be, kh = [], []
for av in range(12):
    for i in range(16):
        a = int((38.4 + av * 4.8 + i * SUB) * SR)
        be.append(bassband(mono_d[a + w0:a + w1]))
        kh.append(i in KHALI)
be, kh = np.array(be), np.array(kh)
hole = float(np.median(be[kh]) / np.median(be[~kh]))
check("the khali is a bass hole, twelve avartans deep",
        hole <= 0.35, f"khali/bhari bass energy {hole:.3f}")

# tihai: self-similarity at the 0.84 s lag, banded to the
# tihai's own notes (146.8/164.8/174.6 Hz) — the wider 100-210
# band belongs to the bayan (105.6) and reads the theka instead
menv = ruler.band_env(np.concatenate([mono, mono[:5 * SR]]),
        135.0, 190.0, 0.01)


def ecorr(t0):
    a = int(round(t0 / 0.01))
    lg, wn = 84, 78
    u = menv[a:a + wn] - menv[a:a + wn].mean()
    v = menv[a + lg:a + lg + wn] \
        - menv[a + lg:a + lg + wn].mean()
    return float(np.dot(u, v) / (np.linalg.norm(u)
            * np.linalg.norm(v) + 1e-12))


r12 = ecorr(86.4 + 7.44 - 0.03)
r23 = ecorr(86.4 + 8.28 - 0.03)
ctrl = max(ecorr(t0) for t0 in np.arange(68.0, 84.0, 0.8))
check("the tihai echoes at its lag",
        # r23 tops near 0.84: the sam's pressed bayan (141.2 Hz,
        # in-band) lands inside the third window only — the
        # arrival outweighs the echo, by design
        r23 >= 0.80 and r12 >= 0.4 and ctrl <= 0.5,
        f"melody-band self-correlation at 0.84 s: r12 "
        f"{r12:.2f}, r23 {r23:.2f}; jhala control max "
        f"{ctrl:.2f}")

# the time marks (Nine Landings rulers): the tick holds every
# jhala slot, and the notes on top stamp theirs with the click
def mark_offsets(bus, times):
    dblb = np.concatenate([bus, bus])
    fl, dtf = ruler.flux_series(dblb, frame=512, hop=128)
    offs = []
    for t0 in times:
        tt = t0 % LOOP_S + LOOP_S
        a, b = int((tt - 0.05) / dtf), int((tt + 0.07) / dtf)
        i = int(np.argmax(fl[a:b]))
        offs.append((a + i) * dtf - tt)
    return np.array(offs)


off_c = mark_offsets(chikn, [67.2 + DT * j for j in range(240)])
med_c = float(np.median(off_c))
check("the timekeeper never lapses",
        float(np.max(np.abs(off_c - med_c))) <= 0.010,
        f"chikari attack on all 240 jhala slots, every one "
        f"within {1000 * np.max(np.abs(off_c - med_c)):.1f} ms "
        f"of its median tick")
tmarks = ([24.0 + 0.48 * k for k, m in enumerate(JORP)
        if not (m is None or (k < 8 and k % 2))]
        + [67.2 + DT * j for j in range(240)
            if j in TIHAI or (j % 4 == 0 and j < 222)]
        + [0.0])
mel_hp = sosfilt(butter(4, 3200.0, btype="high", fs=SR,
        output="sos"), meln)
off_m = mark_offsets(mel_hp, tmarks)
med_m = float(np.median(off_m))
check("the notes on top speak with the tick",
        abs(med_m - med_c) <= 0.008
        and float(np.max(np.abs(off_m - med_c))) <= 0.015,
        f"all {len(tmarks)} jor/jhala/tihai time marks land "
        f"{1000 * med_m:+.1f} ms vs the tick's "
        f"{1000 * med_c:+.1f} ms (worst "
        f"{1000 * np.max(np.abs(off_m - med_c)):.1f} ms out) — "
        f"mizrab clicks stamp the mark, blooms read as legato")

ons = ruler.onset_times(mono_d[:int(1.0 * SR)])
check("the countdown lands on sam",
        len(ons) >= 1 and abs(ons[0]) <= 0.04,
        f"pressed-bayan sam stroke at t={ons[0] * 1000:.0f} ms "
        f"— 86.4 + 62x0.12 + 2x(7x0.12) + 4x0.12 = 96.0 = 0, "
        f"by arithmetic")

sar_mix = sarn * G_SAR
halo_db = 20 * np.log10(rms(taraf_st.sum(axis=1))
        / rms(sar_mix[int(38.4 * SR):int(67.2 * SR)]))
check("the halo sits under the voice",
        -32.0 <= halo_db <= -8.0, f"taraf/sarangi {halo_db:.1f} dB")
bal = 20 * np.log10(rms(drums.mean(axis=1)[int(38.4 * SR):
        int(67.2 * SR)] * G_DRUM)
        / rms(sar_mix[int(38.4 * SR):int(67.2 * SR)]))
check("the theka sits beside the voice",
        -14.0 <= bal <= 0.0, f"drums/sarangi {bal:.1f} dB in the gat")

cu = ruler.chroma_uniform(mono)
check("Sa crowns the cycle", int(np.argmax(cu)) == 2,
        f"chroma crowns class 2 at {max(cu):.2f}")

out = mix
wav = os.path.join(outdir, "avartan.wav")
write_wav(wav, out)
ruler.report(out, "avartan")

if fails:
    print("FAILED RULERS:", fails)
    sys.exit(1)
print("ALL RULERS PASS")

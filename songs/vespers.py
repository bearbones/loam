#!/usr/bin/env python3
"""loam — "Vespers for the Workshop". The first machines learn
to breathe.

An evening service for era I: the PADsynth choir, the church
bells, the FDN room and the grain shimmer of the very first
sessions — revisited with what the raga arc learned about
written interference (e73-e74). Inside the choir hangs a
quiet organ of paired lines, each pair split by an EXACT
integer number of cycles per loop, so the chord breathes on
a harmonic series of breath:

    drone D2   12 cycles/loop   0.156 Hz   (the grand breath)
    D3 pair    24 cycles/loop   0.3125 Hz
    A3 pair    36 cycles/loop   0.469 Hz
    D4 pair    48 cycles/loop   0.625 Hz     -> 1 : 2 : 3 : 4

Every breath closes at the seam by construction, and all four
rates agree every 6.4 seconds — where, and only where, a bell
tolls: twelve tolls a loop, rung when the breaths align. The
choir slowly opens its mouth (oh to ah, one cycle — the
breath's own fundamental), the workshop's folded drone sighs
underneath, and the bell bus shimmers an octave up through
the grain cloud, all in the same FDN room Reliquary hung in
on day one.

76.8 s seamless loop, D aeolian — the workshop's home key,
which Kafi shares.

    python3 songs/vespers.py [outdir]
"""

import os
import sys

import numpy as np
from scipy.signal import butter

sys.path.insert(0, os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))))
from loam import SR, hz, Loop, stereo, write_wav
from loam import ruler
from loam.pads import padsynth_stereo, formant_amps, VOWELS
from loam.modal import strike, CHURCH_BELL
from loam.space import reverb_loop
from loam.shape import wavefold
from loam.grain import cloud

outdir = sys.argv[1] if len(sys.argv) > 1 else "render"
os.makedirs(outdir, exist_ok=True)
fails = []


def check(name, cond, detail):
    print(f"  {'PASS' if cond else 'FAIL'} {name}: {detail}")
    if not cond:
        fails.append(name)


def rms(x):
    return float(np.sqrt(np.mean(np.asarray(x) ** 2)))


LOOP_S = 76.8
L = Loop(LOOP_S, 0xE55E)
DF = 1.0 / LOOP_S                 # the loop's own frequency grid


def addw(buf, at_s, chunk):
    idx = (int(at_s * SR) + np.arange(len(chunk))) % len(buf)
    np.add.at(buf, idx, chunk)


# ---- 1. choir: oh at the seam, ah mid-loop (bin-1 breath) ------
NOTES = [(38, 0.9), (50, 1.0), (57, 0.7), (62, 0.55), (65, 0.4)]
w_ah = 0.5 - 0.5 * np.cos(2 * np.pi * L.t / LOOP_S)
for i, (midi, g) in enumerate(NOTES):
    f0 = hz(midi)
    oh = padsynth_stereo(LOOP_S, f0,
            formant_amps(f0, 48, VOWELS["oh"]),
            bw_cents=45.0, seed=500 + 13 * i)
    ah = padsynth_stereo(LOOP_S, f0,
            formant_amps(f0, 48, VOWELS["ah"]),
            bw_cents=45.0, seed=600 + 13 * i)
    L.buf += (oh * (1 - w_ah)[:, None]
            + ah * w_ah[:, None]) * 0.065 * g

# ---- 2. the breath organ: exact-bin pairs, 2:3:4 ---------------
BREATH = [("D3", hz(50), 24, 0.0100, 0.25),
          ("A3", hz(57), 36, 0.0080, -0.25),
          ("D4", hz(62), 48, 0.0064, 0.45)]
organ = np.zeros((L.n, 2))
for name, fc, nbin, amp, pan in BREATH:
    f_lo = L.q(fc) - 0.5 * nbin * DF
    f_hi = L.q(fc) + 0.5 * nbin * DF
    v = amp * (np.sin(2 * np.pi * f_lo * L.t)
            + np.sin(2 * np.pi * f_hi * L.t))
    organ += stereo(v, pan)
L.buf += organ

# ---- 3. folded drone D2, drive breathing at bin 12 -------------
drone_src = np.sin(2 * np.pi * L.q(hz(38)) * L.t)
# the folder's fundamental is non-monotonic in drive, so drive
# alone breathes at 2x the written rate; the level carries the
# bin-12 breath, the drive only colors it
breath12 = np.sin(2 * np.pi * 12.0 * L.t / LOOP_S)
drive = 1.15 + 0.35 * breath12
folded = wavefold(drone_src, drive) * (1.0 + 0.55 * breath12)
sos_dr = butter(2, 700, btype="low", fs=SR, output="sos")
folded = L.filt_circular(sos_dr,
        np.stack([folded, folded], axis=1))
L.buf += folded * 0.050

# ---- 4. bells: rung where the breaths agree --------------------
# all four rates share the period 76.8/12 = 6.4 s
bellbus = np.zeros((L.n, 2))
TOLLS = [50, 45, 53, 38, 50, 45, 53, 45, 50, 53, 45, 38]
bell_bare = np.zeros(L.n)
for k, midi in enumerate(TOLLS):
    b = strike(hz(midi), 6.5, CHURCH_BELL,
            amp=0.40 if midi != 38 else 0.5, bright=0.92,
            detune=3.0, rng=L.rng, knock=0.10)
    addw(bellbus, 6.4 * k, stereo(b, [0.0, -0.3, 0.3, 0.0][k % 4]))
    addw(bell_bare, 6.4 * k, b)

# ---- 5. shimmer of the bells, an octave up, faint --------------
shimmer = cloud(bellbus.mean(axis=1), LOOP_S, density=9.0,
        grain_s=0.22, pitches=(12.0, 19.0), pan_spread=0.8,
        gain=0.045, seed=0x77)
bellbus += shimmer

# ---- 6. the room -----------------------------------------------
bellbus = reverb_loop(bellbus, t60=4.0, size=1.25,
        damp_hz=3200.0, mix=0.45)
L.buf += bellbus

out = L.master(6800.0, drive=1.35)
mono = out.mean(axis=1)

# ================= the rulers ===================================
print("== rulers ==")
check("seam", ruler.seam_rank(out) <= 0.999,
        f"p{100 * ruler.seam_rank(out):.2f}")


def env_crown(x, lo, hi, bmax=70):
    ev = ruler.band_env(x, lo, hi, 0.05)[:int(LOOP_S / 0.05)]
    le = np.log(ev + 1e-12)
    k = 81
    pad = np.concatenate([le[:k][::-1], le, le[-k:][::-1]])
    tr = np.convolve(pad, np.ones(k) / k, "same")[k:-k]
    sp = np.abs(np.fft.rfft((le - tr) * np.hanning(len(le))))
    return int(np.argmax(sp[6:bmax])) + 6


BANDS = {"D3": (139.0, 155.0), "A3": (210.0, 230.0),
        "D4": (285.0, 302.0)}
crowns = {nm: env_crown(mono, *BANDS[nm]) for nm in BANDS}
check("the chord breathes 2:3:4, on the grid",
        crowns == {"D3": 24, "A3": 36, "D4": 48},
        f"envelope spectra crown at bins {crowns['D3']}/"
        f"{crowns['A3']}/{crowns['D4']} cycles per loop — the "
        f"written 24/36/48, exact, through choir, room and "
        f"master")
dcrown = env_crown(mono, 62.0, 84.0, bmax=40)
check("the grand breath underneath", dcrown == 12,
        f"folded-drone band crowns at bin {dcrown} — the "
        f"series is 12:24:36:48 = 1:2:3:4")

dbl = np.concatenate([bell_bare, bell_bare[:8 * SR]])
tolls = [t for t in ruler.onset_times(dbl, min_sep=3.0)
        if t < LOOP_S + 3.0]
gaps = np.diff(tolls)
check("twelve bells, where the breaths agree",
        len(tolls) == 13 and np.all(np.abs(gaps - 6.4) <= 0.08),
        f"{len(tolls) - 1} tolls per loop at spacing "
        f"{gaps.min():.2f}..{gaps.max():.2f} s — the common "
        f"period of all four breaths (76.8/12 = 6.4)")

organ_db = 20 * np.log10(rms(organ.sum(axis=1))
        / rms(L.buf.sum(axis=1) - organ.sum(axis=1) + 1e-12))
check("the organ hides inside the choir",
        -26.0 <= organ_db <= -6.0,
        f"breath organ sits {organ_db:.1f} dB under the rest")

cu = ruler.chroma_uniform(mono)
order = np.argsort(cu)[::-1][:3].tolist()
check("D crowns the vespers", order[0] == 2,
        f"chroma crowns class 2 at {cu[2]:.2f} "
        f"(then {order[1]}, {order[2]})")

hi = np.fft.rfft(out, axis=0)
f = np.fft.rfftfreq(len(out), 1 / SR)
hi[f < 250] = 0.0
w = np.fft.irfft(hi, len(out), axis=0)
wc = float(np.corrcoef(w[:, 0], w[:, 1])[0, 1])
check("the room is wide but mono-safe",
        -0.25 <= wc <= 0.6, f"stereo corr >250 Hz {wc:+.3f}")

wav = os.path.join(outdir, "vespers.wav")
write_wav(wav, out)
ruler.report(out, "vespers")

if fails:
    print("FAILED RULERS:", fails)
    sys.exit(1)
print("ALL RULERS PASS")

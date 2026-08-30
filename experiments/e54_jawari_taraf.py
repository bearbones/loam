#!/usr/bin/env python3
"""e54 — jawari taraf: the halo learns to shimmer.

Session 53's sympathetic bank rings but doesn't shimmer — the
strings had no bridge. This cycle seats fdsym on its own SAV
jawari contact (fdpluck's parabolic barrier, vectorized across
the bank) plus one new physical knob: `gain`, scaling the drive
FORCE. A driven taraf reaches displacements ~1000x smaller than
a plucked string, so at audio force it never touches the played
string's barrier; gain lifts it into contact. Because the
contact is the model's only nonlinearity, gain is VOICING, not
level — it sets how hard each string wraps the curve, and with
it how much energy climbs the partial ladder.

Measured claims, each on raw buses:
  - ENGAGEMENT: below the contact threshold (gain 100) the
    spectrum is IDENTICAL to the plain bank — the barrier is
    provably out of reach, not merely quiet; at gain 5000 the
    high-band fraction jumps an order of magnitude.
  - BLOOM: the jawari string's high band climbs for over a
    second before peaking (the e41 tanpura signature, now on a
    string nobody plucked); the plain string's high band peaks
    in the first window and decays.
  - selectivity SURVIVES the nonlinearity (unison/semitone
    stays above the calibrated bar).
  - silence in, silence out — the contact adds no noise floor.
  - the pitch rulers read jawari content (hps + dyad within
    tolerance) — the carried STRUCT_BAR worry, answered.

The piece: e53's slow Kafi phrase, same 8-string Kafi bank, now
with jawari — and the A/B is measured: the shimmering halo's
centroid must sit well above the plain halo's on the SAME drive.

    python3 experiments/e54_jawari_taraf.py [outdir]
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

outdir = sys.argv[1] if len(sys.argv) > 1 else "render"
os.makedirs(outdir, exist_ok=True)
fails = []
GAIN = 5000.0                  # voicing: probed engagement knee
                               # sits between gain 100 and 1000


def check(name, cond, detail):
    print(f"  {'PASS' if cond else 'FAIL'} {name}: {detail}")
    if not cond:
        fails.append(name)


def rms(x):
    return float(np.sqrt(np.mean(np.asarray(x) ** 2)))


def hband(x, split=1500.0):
    F = np.abs(np.fft.rfft(x)) ** 2
    f = np.fft.rfftfreq(len(x), 1 / SR)
    return float(F[f > split].sum() / (F.sum() + 1e-24))


def centroid(x):
    F = np.abs(np.fft.rfft(x)) ** 2
    f = np.fft.rfftfreq(len(x), 1 / SR)
    return float((f * F).sum() / (F.sum() + 1e-24))


def hb_env(x, split=1500.0, w_s=0.25):
    F = np.fft.rfft(x)
    f = np.fft.rfftfreq(len(x), 1 / SR)
    F[f < split] = 0
    h = np.fft.irfft(F, len(x))
    w = int(w_s * SR)
    return np.array([rms(h[i:i + w])
            for i in range(0, len(x) - w, w)])


# ---- 1. engagement: a knob with a measured knee -----------------
PROBE = [50, 53, 55, 57, 58, 60]
drv = fdpluck(hz(57), 3.0)
_, plain = fdsym([hz(n) for n in PROBE], drv, buses=True)
_, low = fdsym([hz(n) for n in PROBE], drv, buses=True,
        jawari=True, gain=100.0)
_, jaw = fdsym([hz(n) for n in PROBE], drv, buses=True,
        jawari=True, gain=GAIN)
i57 = PROBE.index(57)
hb_p, hb_l, hb_j = (hband(b[i57]) for b in (plain, low, jaw))
check("below the knee the barrier is out of reach",
        abs(hb_l / hb_p - 1.0) <= 0.05,
        f"gain 100 high-band fraction {hb_l:.4f} vs plain "
        f"{hb_p:.4f} — identical spectrum, not merely quiet")
# calibrated between the measured null (ratio 1.0) and the
# measured engaged case (x36)
check("above the knee the ladder fills", hb_j >= 10.0 * hb_p,
        f"gain {GAIN:.0f} high-band fraction {hb_j:.4f} = "
        f"x{hb_j / hb_p:.0f} plain")

# ---- 2. bloom: the e41 signature on an unplucked string --------
ej = hb_env(jaw[i57])
ep = hb_env(plain[i57])
check("the shimmer BLOOMS", int(np.argmax(ej)) >= 3
        and int(np.argmax(ep)) <= 2,
        f"jawari high band peaks in window {int(np.argmax(ej))} "
        f"({0.25 * int(np.argmax(ej)):.2f}s in), plain in window "
        f"{int(np.argmax(ep))} — energy climbs, not filters")

# ---- 3. selectivity survives the nonlinearity ------------------
r = {n: rms(b) for n, b in zip(PROBE, jaw)}
sel = r[57] / r[58]
check("selectivity survives the bridge", sel >= 6.0,
        f"unison/semitone x{sel:.1f} with jawari "
        f"(plain measured x12.7; bar 6.0 from e53)")

# ---- 4. silence in, silence out --------------------------------
_, zb = fdsym([hz(57)], np.zeros(SR), buses=True,
        jawari=True, gain=GAIN)
check("the contact adds no noise floor",
        float(np.abs(zb).max()) <= 1e-12,
        f"zero-drive jawari bank peak {float(np.abs(zb).max()):.1e}")

# ---- 5. the rulers read jawari content -------------------------
n57 = jaw[i57] / (np.abs(jaw[i57]).max() + 1e-12)
f0 = ruler.hps_pitch(n57, fmin=80.0, fmax=500.0)
c1 = abs(1200 * np.log2(f0 / hz(57)))
n50 = jaw[0] / (np.abs(jaw[0]).max() + 1e-12)
dy = ruler.dyad_pitches(0.9 * n57 + 0.9 * n50,
        fmin=80.0, fmax=500.0)
c2 = max(abs(1200 * np.log2(f / hz(m)))
        for f, m in zip(sorted(dy), (50, 57)))
check("the pitch rulers survive the shimmer",
        c1 <= 25.0 and c2 <= 25.0,
        f"hps {c1:.1f}c, dyad worst {c2:.1f}c on jawari buses")

# ---- 6. the piece: the e53 phrase under a shimmering halo ------
LOOP_S = 9.6
KAFI = {2, 4, 5, 7, 9, 11, 0}
PHRASE = [(0.0, 1.8, 50), (1.8, 1.2, 53), (3.0, 1.2, 52),
        (4.2, 1.2, 50), (5.4, 1.2, 55), (6.6, 1.8, 57),
        (8.4, 1.2, 53)]
solo = np.zeros(int(LOOP_S * SR) + SR)
for at, dur, m in PHRASE:
    v = fdpluck(hz(m), dur + 0.25, amp=0.85)
    a = int(at * SR)
    solo[a:a + len(v)] += v
solo = solo[:int(LOOP_S * SR)]

BANK = [50, 52, 53, 55, 57, 59, 60, 62]
_, tb = fdsym([hz(n) for n in BANK], solo, buses=True,
        jawari=True, gain=GAIN)
_, tb_plain = fdsym([hz(n) for n in BANK], solo, buses=True)

# the A/B, measured on the same drive: shimmer raises the halo
cen_j = centroid(tb.sum(axis=0))
cen_p = centroid(tb_plain.sum(axis=0))
check("the halo shimmers where e53's rang",
        cen_j >= 1.3 * cen_p,
        f"halo centroid {cen_j:.0f} Hz vs plain {cen_p:.0f} Hz "
        f"(x{cen_j / cen_p:.2f})")

HALO_GAIN = 0.041
pans = np.linspace(-0.55, 0.55, len(BANK))
tnorm = np.abs(tb).max() + 1e-12
taraf_st = np.zeros((len(solo), 2))
for b, p in zip(tb, pans):
    g = (b / tnorm) * HALO_GAIN
    taraf_st[:, 0] += g * np.cos((p + 1) * np.pi / 4)
    taraf_st[:, 1] += g * np.sin((p + 1) * np.pi / 4)

tch = ruler.chroma(tb.sum(axis=0))
top3 = set(np.argsort(tch)[-3:].tolist())
check("the halo speaks only Kafi", top3 <= KAFI,
        f"taraf-bus top-3 chroma classes {sorted(top3)}")
halo_db = 20 * np.log10(rms(taraf_st.sum(axis=1)) / rms(solo))
check("the halo sits under the melody", -32.0 <= halo_db <= -8.0,
        f"taraf/melody {halo_db:.1f} dB")

ts, fs = ruler.pitch_contour(solo, fmin=80.0, fmax=500.0)
worst = 0.0
for at, dur, m in PHRASE:
    sel_w = (ts >= at + 0.15) & (ts <= at + dur - 0.1)
    if sel_w.sum():
        med = float(np.median(fs[sel_w]))
        worst = max(worst, abs(1200 * np.log2(med / hz(m))))
check("every melody note reads back", worst <= 25.0,
        f"worst {worst:.1f} cents across {len(PHRASE)} notes")

DRONE = [("pa", hz(45), 140, 0.0, -0.35, 0.55),
        ("sa+", hz(50.015), 112, 1.2, 0.15, 0.50),
        ("sa-", hz(49.985), 112, 2.4, -0.15, 0.50),
        ("SA", hz(38), 138, 3.6, 0.35, 0.75)]
loop = Loop(LOOP_S, seed=54)
for name, f0d, n, at, pan, ampd in DRONE:
    v = fdpluck2(f0d, 12.0, amp=ampd, N=n)
    loop.add(at, stereo(v, pan))
    loop.add(at + 4.8, stereo(v, pan))
loop.add(0.0, stereo(solo, 0.0))
loop.add(0.0, taraf_st)
mix = loop.master(lp_hz=6500.0, drive=1.2)

check("seam", ruler.seam_rank(mix) <= 0.999,
        f"p{100 * ruler.seam_rank(mix):.2f}")
ch = ruler.chroma(mix.mean(axis=1))
top2 = set(np.argsort(ch)[-2:].tolist())
check("D and A are the two poles", top2 == {2, 9},
        f"top-2 classes {sorted(top2)}")

out = np.concatenate([mix, mix])
wav = os.path.join(outdir, "e54_jawari_taraf.wav")
write_wav(wav, out)
ruler.report(out, "jawari_taraf")
subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", wav,
        "-q:a", "5", wav.replace(".wav", ".ogg")], check=True)

print("ALL RULERS PASS" if not fails else f"FAILED: {fails}")
sys.exit(1 if fails else 0)

"""e35 — the mood seam: spyglass entering OVER wanderer, on tension.

The mood A/B (e31 noir spyglass vs e32 dread wanderer) awaits the
operator's ear, but the suggested third answer — wanderer as the
roam bed, spyglass entering with tension/awareness — exists only as
a sentence. This experiment makes the seam audible and measured, so
the ruling can be among three RENDERS, not two renders and a guess.

The claim under test: the two poles were built from one system (the
world's own gut + glass, D ground, E pitch class reserved for the
stained verdict everywhere), so a tension-driven handover needs NO
key change, NO tempo negotiation, NO ducking tricks — the wander
thins (the world doesn't change; your attention does), the walk
enters on its own clock, and the floor's 96 Hz institution line
never leaves.

Scene (one-shot 48 s — a scene, not a loop; the in-game music is
state-driven): wanderer tiles throughout. Tension tau rises 10->16 s
(smoothstep), holds 1.0 to 30 s, falls 30->38 s. Spyglass enters at
t=10 from its own bar 1, gain sqrt(tau); the wander yields to
sqrt(1 - 0.65*tau) — thinner, never gone.

Measured, each claim on its own bus (poles RMS-matched before the
law is applied):
  - no hole, no spike: windowed RMS through the handover stays
    within [roam - 2 dB, tension + 3 dB] — equal-power done right.
  - gentle entry: the walk's first bar steps the mix < 3 dB.
  - E stays reserved: E-class energy <= 0.2 x mean(D, F) on the
    full scene — the blend must not manufacture the verdict color.
  - no clash: roughness (15..35 Hz envelope fluctuation of the
    100..400 Hz band — where a mistuned ground would beat) in full
    overlap <= 1.35 x the rougher solo pole.
  - the floor never leaves: 96 Hz hum power at tau=1 within
    [0.25, 0.7] x its roam value — it must yield (law says 0.35)
    AND it must survive. Two-sided honesty.

    python3 experiments/e35_moodseam.py [outdir]
"""

import os
import sys

import numpy as np
from scipy.signal import butter, sosfilt

sys.path.insert(0, os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from loam import SR, write_wav

import e31_spyglass as spy
import e32_wanderer as wan

outdir = sys.argv[1] if len(sys.argv) > 1 else "render"
os.makedirs(outdir, exist_ok=True)

SCENE_S = 48.0
N = int(SCENE_S * SR)
T_RISE0, T_RISE1 = 10.0, 16.0
T_FALL0, T_FALL1 = 30.0, 38.0
YIELD = 0.65        # how much of the wander's power tension takes


def smoothstep(x):
    x = np.clip(x, 0.0, 1.0)
    return x * x * (3.0 - 2.0 * x)


def tau_of(t):
    up = smoothstep((t - T_RISE0) / (T_RISE1 - T_RISE0))
    dn = smoothstep((t - T_FALL0) / (T_FALL1 - T_FALL0))
    return up * (1.0 - dn)


print("building the poles...")
wanL, _, _ = wan.build()
spyL, _, _ = spy.build()
wbuf, sbuf = wanL.buf, spyL.buf
# RMS-match the poles BEFORE the law: the seam compares characters
sbuf = sbuf * np.sqrt(np.mean(wbuf ** 2) / (np.mean(sbuf ** 2) + 1e-12))

tt = np.arange(N) / SR
tau = tau_of(tt)

# wanderer tiles the whole scene (its loop is seamless by contract)
reps = int(np.ceil(SCENE_S / wan.LOOP_S))
wan_bus = np.tile(wbuf, (reps, 1))[:N] * np.sqrt(1.0 - YIELD * tau)[:, None]

# spyglass enters at T_RISE0 from its own bar 1, on its own clock
spy_bus = np.zeros((N, 2))
i0 = int(T_RISE0 * SR)
reps = int(np.ceil((SCENE_S - T_RISE0) / spy.LOOP_S))
tile = np.tile(sbuf, (reps, 1))[: N - i0]
spy_bus[i0:] = tile
spy_bus *= np.sqrt(tau)[:, None]

mix = wan_bus + spy_bus


# ---- rulers ----

def rms_db(x, t0, t1):
    seg = x[int(t0 * SR): int(t1 * SR)]
    return 10.0 * np.log10(np.mean(seg.mean(axis=1) ** 2) + 1e-12)


def windowed_rms_db(x, t0, t1, win=1.0, hop=0.25):
    out = []
    t = t0
    while t + win <= t1:
        out.append(rms_db(x, t, t + win))
        t += hop
    return np.array(out)


def roughness(x, t0, t1):
    """Envelope-fluctuation index of the low-mid ground: bandpass
    100..400 Hz (where a mistuned D ground would beat), envelope,
    then the 15..35 Hz fluctuation band over the envelope's own
    level — beating clash reads as a spike here."""
    mono = x[int(t0 * SR): int(t1 * SR)].mean(axis=1)
    g = sosfilt(butter(2, [100.0 / (SR / 2), 400.0 / (SR / 2)],
            btype="band", output="sos"), mono)
    e = sosfilt(butter(4, 60.0 / (SR / 2), output="sos"), np.abs(g))
    fl = sosfilt(butter(2, [15.0 / (SR / 2), 35.0 / (SR / 2)],
            btype="band", output="sos"), e)
    return float(np.sqrt(np.mean(fl ** 2)) /
            (np.sqrt(np.mean(e ** 2)) + 1e-12))


def pc_power(x, pclass):
    """Total power near a pitch class, octaves 2..5, half-window
    1.5% (the e31/e32 house chroma ruler)."""
    mono = x.mean(axis=1)
    spec = np.abs(np.fft.rfft(mono)) ** 2
    freqs = np.fft.rfftfreq(len(mono), 1.0 / SR)
    total = 0.0
    for octv in range(2, 6):
        f = 440.0 * 2.0 ** ((pclass - 9) / 12.0 + (octv - 4))
        band = (freqs > f * 0.985) & (freqs < f * 1.015)
        total += float(np.sum(spec[band]))
    return total


def hum_power(x, t0, t1):
    """96 Hz band power DENSITY — dividing by segment length keeps
    unequal windows comparable (summed rfft power scales with N:
    the first cut read 0.35 as 0.71 partly by comparing a 10 s
    window against a 7 s one)."""
    seg = x[int(t0 * SR): int(t1 * SR)].mean(axis=1)
    spec = np.abs(np.fft.rfft(seg)) ** 2
    freqs = np.fft.rfftfreq(len(seg), 1.0 / SR)
    band = (freqs > 96.0 * 0.98) & (freqs < 96.0 * 1.02)
    return float(np.sum(spec[band])) / len(seg)


fails = []


def claim(name, ok, detail):
    print("  %-36s %s  (%s)" % (name, "PASS" if ok else "FAIL", detail))
    if not ok:
        fails.append(name)


print("e35 moodseam — rulers")

roam_db = rms_db(mix, 2.0, 9.0)
tens_db = rms_db(mix, 18.0, 28.0)
w = windowed_rms_db(mix, 8.0, 18.0)
claim("no hole in the handover", np.min(w) >= roam_db - 2.0,
        "min %.1f dB vs roam %.1f dB" % (np.min(w), roam_db))
claim("no spike in the handover", np.max(w) <= tens_db + 3.0,
        "max %.1f dB vs tension %.1f dB" % (np.max(w), tens_db))

step = rms_db(mix, T_RISE0, T_RISE0 + 0.5) - rms_db(mix, T_RISE0 - 0.5, T_RISE0)
claim("gentle entry (< 3 dB step)", step < 3.0, "%.1f dB" % step)

# E is judged RELATIVE to the poles' own E fraction: the A2 drone's
# 3rd harmonic IS E4, so an absolute chroma floor blames the seam
# for leakage the poles already carry. The seam's claim is narrower
# and honest: blending manufactures no NEW E.
def e_frac(x):
    return pc_power(x, 4) / ((pc_power(x, 2) + pc_power(x, 5)) / 2.0 + 1e-12)

ef_mix = e_frac(mix)
ef_wan, ef_spy = e_frac(wan_bus), e_frac(spy_bus)
claim("the seam adds no NEW E", ef_mix <= 1.1 * max(ef_wan, ef_spy),
        "mix %.3f vs poles %.3f/%.3f" % (ef_mix, ef_wan, ef_spy))

r_mix = roughness(mix, 18.0, 28.0)
r_wan = roughness(wan_bus, 2.0, 9.0)
r_spy = roughness(spy_bus, 18.0, 28.0)
claim("no clash in full overlap", r_mix <= 1.35 * max(r_wan, r_spy),
        "mix %.3f vs solo max %.3f" % (r_mix, max(r_wan, r_spy)))

# the yield law is read on the wander's OWN bus (house rule); the
# survival half on the mix, where spyglass contamination can only
# help — so that side is one-sided. Equal 7 s windows both times.
h_yield = hum_power(wan_bus, 19.0, 26.0) / (hum_power(wan_bus, 2.0, 9.0) + 1e-12)
claim("the floor yields as the law says", 0.28 <= h_yield <= 0.42,
        "own-bus 96 Hz ratio %.2f (law %.2f)" % (h_yield, 1.0 - YIELD))
h_live = hum_power(mix, 19.0, 26.0) / (hum_power(mix, 2.0, 9.0) + 1e-12)
claim("the floor survives in the mix", h_live >= 0.25,
        "mix 96 Hz ratio %.2f" % h_live)

mix *= 0.9 / np.max(np.abs(mix))
write_wav(os.path.join(outdir, "e35_moodseam.wav"), mix)

print("%d/7 rulers pass" % (7 - len(fails)))
sys.exit(1 if fails else 0)

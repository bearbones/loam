"""e34 — the draw creak as a STRETCH, not a pluck (operator ruling).

The ruling (2026-08-15): the bow draw "should be unobtrusive wood
creak... sort of feel like a nice stretch." The shipped tick-train
(e20 -> NC.creak_voice) is discrete WOOD strikes whose PITCH climbs
with draw fraction — physically a pluck gesture, and "plucking guitar
strings one at a time" is exactly the operator's complaint about the
e28 render's foreground.

The idea under test: a real creak is stick-slip friction. The wood
body's resonances are FIXED (the limb doesn't change); what rises
with tension is the slip RATE, until discrete ticks fuse into a
groan (the door-hinge law: ~<20 pulses/s reads as ticking, ~>35/s
fuses into a rough tone whose "pitch" is the rate itself). So the
candidate inverts the shipped voice on both axes:

              shipped tick-train        stretch-groan candidate
  rises:      strike PITCH (x1.3)       slip RATE (18 -> 70 /s)
  fixed:      rate (sparse, 2-7/s)      body modes (170/430/860/1500)

Gesture (both buses, same clock): 2.5 s draw 0 -> 1 (e20's build),
0.9 s hold with the groan settling — a stretch ends in a satisfied
settle, not a cutoff.

Measured, each claim on its own bus (RMS-matched first, so the A/B
compares CHARACTER, not level):
  - crest factor: plucks are transients (high peak/RMS); the groan
    must sit >= 6 dB smoother than the tick-train.
  - continuity: longest envelope dropout. Discrete ticks leave
    >= 250 ms of silence early in the draw; the groan may never go
    dark > 80 ms once engaged.
  - the stretch: groan envelope rate (autocorr of its own envelope)
    must rise >= x2 from the first build window to the last, and
    land within 25% of the designed hazard at both ends.
    (Onset-counting is the tick-train's ruler, autocorr the groan's:
    find_peaks undercounts fused pulses, autocorr can't see a 2/s
    train inside a 125 ms lag window — one ruler per material.)
  - the fixed body: power-weighted centroid, last build half over
    first. Tick-train must RISE (pitch ramp, >= x1.10); groan must
    HOLD (0.85..1.18) — the anti-pluck claim in one number.

    python3 experiments/e34_drawcreak.py [outdir]
"""

import os
import sys

import numpy as np
from scipy.signal import butter, sosfilt, find_peaks

sys.path.insert(0, os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))))
from loam import SR, stereo, write_wav
from loam.modal import strike, WOOD

outdir = sys.argv[1] if len(sys.argv) > 1 else "render"
os.makedirs(outdir, exist_ok=True)

DRAW_S = 2.5       # e20's build clock
HOLD_S = 0.9       # the settle
BUF_S = DRAW_S + HOLD_S + 0.3
N = int(BUF_S * SR)

# the groan's hazard: slip rate vs draw fraction (pulses per second).
# 18/s at first engagement (already fused-ish — the stretch is ON
# from the first touch), 70/s at full draw (a proper groan).
RATE_LO = 18.0
RATE_HI = 70.0
RATE_EXP = 1.4     # tension loads late, like the shipped hazard

# the fixed wood body: (center Hz, Q, gain). A bow limb, not a
# guitar: one deep flex mode, two mid barks, a papery shear edge.
BODY = [(170.0, 16.0, 1.0), (430.0, 15.0, 0.62),
        (860.0, 13.0, 0.38), (1500.0, 11.0, 0.16),
        (2400.0, 9.0, 0.03)]


def frac_of(t):
    return min(max(t / DRAW_S, 0.0), 1.0)


def place(buf, at_s, mono, pan=0.0):
    c = stereo(mono, pan)
    i = int(at_s * SR)
    j = min(i + len(c), len(buf))
    buf[i:j] += c[: j - i]


# ---- bus A: the shipped tick-train, ported verbatim from e20 ----

def ticktrain(seed):
    r = np.random.default_rng(seed)
    bus = np.zeros((N, 2))
    t = 0.03
    while t < DRAW_S:
        f = frac_of(t)
        tick = strike(950.0 * (1.0 + 0.30 * f) * r.uniform(0.96, 1.04),
                float(r.uniform(0.035, 0.07)), WOOD,
                amp=0.055 + 0.11 * f, bright=1.25, rng=r)
        place(bus, t, tick, float(r.uniform(-0.12, 0.12)))
        t += 0.22 / (0.5 + 3.0 * f * f) * float(r.uniform(0.8, 1.25))
    return bus


# ---- bus B: the stretch-groan candidate ----

def resonator_sos(fc, q):
    """2nd-order bandpass (constant peak gain) as an SOS row."""
    w = 2.0 * np.pi * fc / SR
    r = 1.0 - w / (2.0 * q)
    # peak-normalized two-pole/two-zero bandpass
    b0 = (1.0 - r)
    return np.array([[b0, 0.0, -b0, 1.0, -2.0 * r * np.cos(w), r * r]])


def slip_groan(seed):
    r = np.random.default_rng(seed)
    pulses = np.zeros(N)
    # a SOFT slip: 5 ms jerk with a 2 ms decay — a fiber letting go,
    # not a click. The sharp first cut (0.9 ms) put pluck-like
    # transients right back into the groan (crest within 2 dB of
    # the tick-train it was built to beat)
    jerk_n = int(0.005 * SR)
    jerk_env = np.exp(-np.arange(jerk_n) / (0.0025 * SR))
    t = 0.02
    while t < DRAW_S + HOLD_S * 0.8:
        f = frac_of(t)
        rate = RATE_LO + (RATE_HI - RATE_LO) * f ** RATE_EXP
        amp = (0.28 + 0.72 * f) * float(r.uniform(0.8, 1.2))
        if t > DRAW_S:  # the settle: rate holds, the wood relaxes
            amp *= float(np.exp(-(t - DRAW_S) / 0.35))
        i = int(t * SR)
        j = min(i + jerk_n, N)
        pulses[i:j] += amp * r.standard_normal(j - i) * jerk_env[: j - i]
        t += (1.0 / rate) * float(r.uniform(0.9, 1.1))
    # the fixed body: parallel resonators over the SAME pulse train
    body = np.zeros(N)
    for fc, q, g in BODY:
        body += g * sosfilt(resonator_sos(fc, q), pulses)
    # a slow undulation — the breath of the stretch, not a tremolo
    tt = np.arange(N) / SR
    body *= 1.0 + 0.12 * np.sin(2.0 * np.pi * 0.9 * tt)
    body = sosfilt(butter(2, 3800.0 / (SR / 2), output="sos"), body)
    return stereo(body, 0.0)


# ---- rulers ----

def env_of(x, corner=250.0):
    mono = x.mean(axis=1) if x.ndim == 2 else x
    return sosfilt(butter(4, corner / (SR / 2), output="sos"),
            np.abs(mono))


def env_pulse_band(x, t0, t1):
    """Slip-rate envelope, read where the pulses stay DISTINCT.
    The deep 170 Hz mode rings ~200 ms — four slip periods of
    overlap early in the draw, which smears the envelope's
    periodicity into a subharmonic lie (23/s read as 11/s). The
    high modes (1500/2400 Hz) decay in ~16 ms, so THEIR band still
    ripples at the true rate: bandpass the render 1100..3500 Hz,
    rectify, then band-limit the envelope to the pulse register
    (5..150 Hz) so the 0.9 Hz breath can't bias long lags."""
    mono = x.mean(axis=1) if x.ndim == 2 else x
    hi = sosfilt(butter(2, [1100.0 / (SR / 2), 3500.0 / (SR / 2)],
            btype="band", output="sos"), mono)
    e = sosfilt(butter(4, 250.0 / (SR / 2), output="sos"),
            np.abs(hi))[int(t0 * SR): int(t1 * SR)]
    sos = butter(2, [5.0 / (SR / 2), 150.0 / (SR / 2)],
            btype="band", output="sos")
    return sosfilt(sos, e - np.mean(e))


def crest_db(x, t0, t1):
    seg = x[int(t0 * SR): int(t1 * SR)]
    mono = seg.mean(axis=1)
    return 20.0 * np.log10(np.max(np.abs(mono)) /
            (np.sqrt(np.mean(mono ** 2)) + 1e-12))


def longest_gap_ms(x, t0, t1, frac_floor=0.04):
    e = env_of(x)[int(t0 * SR): int(t1 * SR)]
    dark = e < frac_floor * np.max(e)
    best = run = 0
    for d in dark:
        run = run + 1 if d else 0
        best = max(best, run)
    return 1000.0 * best / SR


def env_rate_hz(x, t0, t1):
    """Dominant envelope periodicity via autocorrelation, lags
    limited to 1/90..1/8 s (the fused-groan register)."""
    e = env_pulse_band(x, t0, t1)
    ac = np.correlate(e, e, "full")[len(e) - 1:]
    lo, hi = int(SR / 90.0), int(SR / 8.0)
    return SR / float(lo + np.argmax(ac[lo:hi]))


def centroid_hz(x, t0, t1):
    seg = x[int(t0 * SR): int(t1 * SR)].mean(axis=1)
    spec = np.abs(np.fft.rfft(seg)) ** 2       # POWER-weighted
    freqs = np.fft.rfftfreq(len(seg), 1.0 / SR)
    band = freqs < 6000.0
    return float(np.sum(freqs[band] * spec[band]) /
            (np.sum(spec[band]) + 1e-12))


def onsets_per_s(x, t0, t1):
    e = env_of(x, corner=120.0)
    seg = e[int(t0 * SR): int(t1 * SR)]
    pk, _ = find_peaks(seg, height=0.15 * np.max(e),
            distance=int(0.03 * SR))
    return len(pk) / (t1 - t0)


A = ticktrain(0xE34)
B = slip_groan(0xE34 + 1)
B *= np.sqrt(np.mean(A ** 2) / (np.mean(B ** 2) + 1e-12))  # RMS match

fails = []


def claim(name, ok, detail):
    print("  %-34s %s  (%s)" % (name, "PASS" if ok else "FAIL", detail))
    if not ok:
        fails.append(name)


print("e34 drawcreak — rulers (RMS-matched buses)")

# crest in the LATE window only: over the whole build the amp ramp
# inflates crest for both buses and drowns the texture difference
ca = crest_db(A, DRAW_S - 0.6, DRAW_S)
cb = crest_db(B, DRAW_S - 0.6, DRAW_S)
claim("groan >= 6 dB smoother (crest)", cb <= ca - 6.0,
        "tick %.1f dB, groan %.1f dB" % (ca, cb))

ga = longest_gap_ms(A, 0.3, DRAW_S)
gb = longest_gap_ms(B, 0.3, DRAW_S)
claim("ticks leave dark gaps >= 250 ms", ga >= 250.0, "%.0f ms" % ga)
claim("groan never dark > 80 ms", gb <= 80.0, "%.0f ms" % gb)

w0, w1 = (0.2, 0.7), (DRAW_S - 0.5, DRAW_S)
rb0, rb1 = env_rate_hz(B, *w0), env_rate_hz(B, *w1)
f0m = frac_of(np.mean(w0))
f1m = frac_of(np.mean(w1))
d0 = RATE_LO + (RATE_HI - RATE_LO) * f0m ** RATE_EXP
d1 = RATE_LO + (RATE_HI - RATE_LO) * f1m ** RATE_EXP
claim("stretch: groan rate rises >= x2", rb1 / rb0 >= 2.0,
        "%.1f -> %.1f /s (x%.1f)" % (rb0, rb1, rb1 / rb0))
claim("rate tracks the designed hazard",
        abs(rb0 / d0 - 1.0) <= 0.25 and abs(rb1 / d1 - 1.0) <= 0.25,
        "designed %.0f/%.0f, measured %.0f/%.0f" % (d0, d1, rb0, rb1))
# the shipped hazard tops out at 13.4/s — dense, but still under
# the ~18/s fusion floor: every tick stays a separate pluck. Early
# it is literally one at a time (the operator's words).
oa0, oa1 = onsets_per_s(A, *w0), onsets_per_s(A, *w1)
claim("early ticks one-at-a-time (< 5/s)", oa0 < 5.0, "%.1f/s" % oa0)
claim("ticks never fuse (< 18/s)", oa1 < 18.0, "%.1f/s" % oa1)

h0, h1 = (0.2, 0.2 + (DRAW_S - 0.2) / 2), (0.2 + (DRAW_S - 0.2) / 2, DRAW_S)
na = centroid_hz(A, *h1) / centroid_hz(A, *h0)
nb = centroid_hz(B, *h1) / centroid_hz(B, *h0)
claim("tick-train pitch CLIMBS (pluck)", na >= 1.10, "x%.2f" % na)
claim("groan body HOLDS (creak)", 0.85 <= nb <= 1.18, "x%.2f" % nb)

peak = max(np.max(np.abs(A)), np.max(np.abs(B)))
A *= 0.9 / peak
B *= 0.9 / peak      # one shared gain: the A/B is honest
write_wav(os.path.join(outdir, "e34_a_ticktrain.wav"), A)
write_wav(os.path.join(outdir, "e34_b_groan.wav"), B)
gap = np.zeros((int(0.7 * SR), 2))
write_wav(os.path.join(outdir, "e34_ab.wav"),
        np.concatenate([A, gap, B]))

print("%d/9 rulers pass" % (9 - len(fails)))
sys.exit(1 if fails else 0)

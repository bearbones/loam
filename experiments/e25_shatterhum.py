#!/usr/bin/env python3
"""e25 — The death of a hum. SFX prototype for NOCK's lightning-
fixture shatter: what connects the living 96 Hz hum to the silence
after the crash. The idea under test: THE INSTITUTION'S TONE ONLY
GOES FLAT WHEN YOU BREAK IT. All of lightning's language is precise
— grid-locked, cycle-quantized, dead in tune (e22/e23). A thrown
switch should therefore end the hum CLEANLY (one cycle, gone: a
precise thing ends precisely). But a SMASHED tube loses its mains
lock and dies badly: the hum survives the crash for a moment and
glides flat — phase-continuous, pitch falling like a generator
spinning down — under a decaying rain of glass. The glide is the
one detuned thing lightning ever says, and it only says it when
the player has done something loud and permanent.

One ~4 s take: 1.5 s of locked hum -> crash -> glass rain + the
dying glide -> room. (The clean switch-off is rendered as a 1 s
coda after a beat of silence, for the A/B the thesis needs.)

Measured, each claim on its own bus:
  - the lock: every 0.25 s window of pre-crash hum sits within
    5 cents of 96.0 Hz (parabolic-interpolated spectral peak)
  - the death: post-crash hum pitch falls MONOTONICALLY through
    every voiced window and travels > 12 semitones before the
    envelope gate silences it (tau 0.18 s)
  - the crash is glass: crash-bus power centroid > 3 kHz
  - the rain thins: tick count per 0.3 s window strictly falls
    across three windows (one detection pass, one threshold,
    binned after — e24's rule)
  - two deaths, one ruler: hum holds > 0.2 s of energy after the
    smash but < 30 ms after the switch cut (the contrast IS the
    claim — precision ends precisely, breakage rings)

    python3 experiments/e25_shatterhum.py [outdir]
"""

import os
import sys

import numpy as np
from scipy.signal import butter, sosfilt, find_peaks

sys.path.insert(0, os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))))
from loam import SR, stereo, write_wav, ad_env
from loam.modal import strike, GLASS

outdir = sys.argv[1] if len(sys.argv) > 1 else "render"
os.makedirs(outdir, exist_ok=True)
rng = np.random.default_rng(0xE25)

HUM_HZ = 96.0
CRASH_T = 1.5        # the smash lands here
GLIDE_TAU = 0.18     # s: pitch fall constant (generator spin-down)
GLIDE_AMP_K = 6.0    # /s: the dying hum's envelope decay
RAIN_S = 1.2         # glass keeps landing this long
DUR = 4.0


def bp(x, lo, hi):
    sos = butter(2, [lo / (SR / 2), hi / (SR / 2)], "bandpass",
                 output="sos")
    return sosfilt(sos, x)


def hum_locked(dur):
    """The living fixture: 96 Hz + its octave, dead steady."""
    tt = np.arange(int(dur * SR)) / SR
    return (np.sin(2 * np.pi * HUM_HZ * tt) * 0.20
            + np.sin(2 * np.pi * 2 * HUM_HZ * tt) * 0.07)


def hum_dying(dur):
    """The glide: phase-continuous chirp from 96 Hz falling with
    tau, envelope dying with GLIDE_AMP_K. Phase integrates f(t) so
    there is no seam at the crash — the same hum, losing its grip."""
    n = int(dur * SR)
    tt = np.arange(n) / SR
    f = HUM_HZ * np.exp(-tt / GLIDE_TAU)
    phase = 2 * np.pi * np.cumsum(f) / SR
    env = np.exp(-tt * GLIDE_AMP_K)
    return (np.sin(phase) * 0.20 + np.sin(2 * phase) * 0.07) * env


def crash():
    """The smash: bright broadband + a cluster of big glass."""
    n = int(0.5 * SR)
    burst = bp(rng.standard_normal(n), 1800, 9000) \
        * ad_env(n, 0.001, 26.0) * 0.9
    out = np.zeros(n)
    for f0 in (1170.0, 1560.0, 2140.0):
        s = strike(f0, 0.45, GLASS, amp=0.5, bright=1.2, rng=rng,
                   knock=0.4)
        out[:min(len(s), n)] += s[:n]
    return out * 0.6 + burst


def glass_rain(dur):
    """Falling shards: tiny glass strikes whose RATE decays — the
    event-rate instrument again (e24). Seeded exponential gaps
    against a falling rate."""
    n = int(dur * SR)
    out = np.zeros(n)
    t = 0.0
    while t < dur:
        rate = 24.0 * np.exp(-t / 0.45) + 1.0
        t += rng.exponential(1.0 / rate)
        if t >= dur:
            break
        f0 = rng.uniform(1900.0, 3800.0)
        s = strike(f0, rng.uniform(0.06, 0.16), GLASS,
                   amp=rng.uniform(0.05, 0.16), bright=1.0,
                   rng=rng, knock=0.2)
        i0 = int(t * SR)
        m = min(len(s), n - i0)
        out[i0:i0 + m] += s[:m]
    return out


def scene():
    n = int(DUR * SR)
    buses = {"hum": np.zeros(n), "crash": np.zeros(n),
             "rain": np.zeros(n)}

    def put(bus, at, x):
        i0 = int(at * SR)
        m = min(len(x), n - i0)
        buses[bus][i0:i0 + m] += x[:m]

    put("hum", 0.0, hum_locked(CRASH_T))
    put("hum", CRASH_T, hum_dying(DUR - CRASH_T))
    put("crash", CRASH_T, crash())
    put("rain", CRASH_T + 0.04, glass_rain(RAIN_S))
    mix = sum(buses.values())
    return mix / np.max(np.abs(mix)) * 0.85, buses


def clean_off(dur=1.0, cut=0.5):
    """The switch coda: locked hum, then gone inside a cycle —
    a 4 ms cosine ramp ending on the cut. Precision ends precisely."""
    x = hum_locked(dur)
    k = int(0.004 * SR)
    i0 = int(cut * SR)
    x[i0 - k:i0] *= 0.5 * (1 + np.cos(np.linspace(0, np.pi, k)))
    x[i0:] = 0.0
    return x


# ---- the rulers -----------------------------------------------------

def peak_hz(seg, lo, hi):
    """Parabolic-interpolated spectral peak inside [lo, hi] Hz."""
    spec = np.abs(np.fft.rfft(seg * np.hanning(len(seg)), n=1 << 17))
    f = np.fft.rfftfreq(1 << 17, 1 / SR)
    band = (f >= lo) & (f <= hi)
    i = np.argmax(spec[band]) + np.flatnonzero(band)[0]
    a, b, c = spec[i - 1], spec[i], spec[i + 1]
    d = 0.5 * (a - c) / (a - 2 * b + c + 1e-12)
    return float(f[i] + d * (f[1] - f[0]))


def cents(a, b):
    return 1200.0 * np.log2(a / b)


if __name__ == "__main__":
    mix, buses = scene()
    coda = clean_off()
    full = np.concatenate([mix, np.zeros(int(0.5 * SR)),
                           coda / np.max(np.abs(coda)) * 0.28])
    write_wav(os.path.join(outdir, "e25_shatterhum.wav"),
              stereo(full, 0.0))

    print("== the lock (pre-crash windows vs 96.0) ==")
    worst = 0.0
    for k in range(5):
        seg = buses["hum"][int(k * 0.25 * SR):int((k + 1) * 0.25 * SR)]
        worst = max(worst, abs(cents(peak_hz(seg, 40, 200), HUM_HZ)))
    print("  worst %+.1f cents (want within 5)" % worst)

    print("== the death (post-crash pitch track) ==")
    track = []
    for k in range(8):
        a = CRASH_T + k * 0.06
        seg = buses["hum"][int(a * SR):int((a + 0.06) * SR)]
        if np.sqrt((seg ** 2).mean()) < 0.005:
            break  # the envelope gate: unvoiced windows don't vote
        p = peak_hz(seg, 20, 200)
        if p < 25.0:
            break  # the ruler's own floor: parabolic interpolation
            # at the band edge invents pitches (negative Hz) once
            # the glide falls below what the band can hold
        track.append(p)
    falls = all(a > b for a, b in zip(track, track[1:]))
    span = cents(track[0], track[-1]) / 100.0 if len(track) > 1 else 0
    print("  %s Hz" % ["%.1f" % p for p in track])
    print("  monotone fall: %s, span %.1f semitones (want > 12)"
          % ("YES" if falls else "NO", span))

    spec = np.abs(np.fft.rfft(buses["crash"])) ** 2
    fr = np.fft.rfftfreq(len(buses["crash"]), 1 / SR)
    cen = (spec * fr).sum() / spec.sum()
    print("== the crash is glass: centroid %.0f Hz (want > 3000) ==" % cen)

    print("== the rain thins (ticks per 0.3 s window) ==")
    seg = np.abs(buses["rain"][int((CRASH_T + 0.04) * SR):
                               int((CRASH_T + 0.04 + 0.9) * SR)])
    k = int(0.003 * SR)
    env = np.convolve(seg, np.ones(k) / k, "same")
    pk, _ = find_peaks(env, height=env.max() * 0.06,
                       distance=int(0.02 * SR))
    tks = pk / SR
    counts = [int(((tks >= w * 0.3) & (tks < (w + 1) * 0.3)).sum())
              for w in range(3)]
    print("  %s : %s" % (counts,
          "THINS" if counts[0] > counts[1] > counts[2] else "NO"))

    print("== two deaths, one ruler: hum hold after the event ==")
    # duration the hum stays above 1% of its post-event peak. The
    # first draft asserted the coda's tail was zero — a tautology
    # (it measured zeros written by construction; e24's lesson). The
    # honest claim is the CONTRAST, same ruler both sides: a smashed
    # hum holds for a fifth of a second or more, a switched hum is
    # gone within a cycle or three.
    def hold_s(x):
        k = int(0.004 * SR)
        env = np.convolve(np.abs(x), np.ones(k) / k, "same")
        above = np.flatnonzero(env > env.max() * 0.01)
        return float(above[-1]) / SR if len(above) else 0.0

    smashed = hold_s(buses["hum"][int(CRASH_T * SR):])
    cut = 0.5
    # straddle the ramp: a window starting AT the cut sees only the
    # zeros again — the ruler must watch the hum actually leave
    clean = hold_s(coda[int((cut - 0.02) * SR):])
    print("  smashed %.3f s (want > 0.2)  vs  switched %.3f s "
          "(want < 0.03)" % (smashed, clean))

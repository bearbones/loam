#!/usr/bin/env python3
"""e24 — The water cycle. SFX prototype for NOCK's douse / relight
pair: the flame is a character, and the water arrow kills it only
for a while. The douse (splash -> steam bloom -> crackle dies) OPENS
a stealth window; the relight (flint scrapes -> catch whump ->
crackle reborn) CLOSES it. The idea under test: the pair must
MEASURE the window for the ear —
  - the douse ends in genuine silence (the prize is audible as
    absence),
  - the relight TELEGRAPHS: the flint scrapes are a fixed-length
    countdown before the whump brings the light back. A player who
    hears tick one knows exactly how long their darkness has left.
    The telegraph is grammar: its length never varies.

Scene render (~10s, one continuous take over a faint night bed):
steady crackle -> splash + steam bloom (crackle dies mid-hiss) ->
the dark window (bed only) -> three flint scrapes -> catch whump ->
crackle ramps back to steady.

Measured, each claim on its own bus:
  - steam cooling: POWER centroid of the hiss, first 0.3s vs last
    0.3s — must fall by > 2x (steam starts as a shriek, ends as a
    sigh)
  - the window is real: rms of the dark gap < 1/8 of the lit
    steady-state rms — measured against the night bed, because a
    gap of digital zero makes the ratio a lie
  - the telegraph: first-scrape -> whump interval == design
    (0.90s) within 30 ms, and exactly 3 scrape ticks
  - rebirth ramps: crackle ticks per 1.4s window strictly rise
    across the three windows after the whump (one detection pass,
    one threshold, binned after — never thresholded per window)

    python3 experiments/e24_watercycle.py [outdir]
"""

import os
import sys

import numpy as np
from scipy.signal import butter, sosfilt, find_peaks

sys.path.insert(0, os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))))
from loam import SR, stereo, write_wav, ad_env

outdir = sys.argv[1] if len(sys.argv) > 1 else "render"
os.makedirs(outdir, exist_ok=True)
rng = np.random.default_rng(0xE24)

TELEGRAPH_S = 0.90       # first scrape -> whump: the grammar length
SCRAPE_N = 3
SCENE = {                # the take's clock
    "douse": 2.0,        # splash lands here; crackle dies at +0.35
    "scrape0": 4.6,      # the countdown begins
    "steady2": 6.2,      # crackle back at full (whump at 5.5)
}
DUR = 10.0


def bp(x, lo, hi):
    sos = butter(2, [lo / (SR / 2), hi / (SR / 2)], "bandpass",
                 output="sos")
    return sosfilt(sos, x)


def splash():
    n = int(0.30 * SR)
    w = rng.standard_normal(n) * ad_env(n, 0.002, 22.0)
    body = bp(w, 400, 2400) * 0.8
    tt = np.arange(n) / SR
    plop = np.sin(2 * np.pi * (300 - 400 * tt) * tt) \
        * np.exp(-tt * 30.0) * 0.5
    return body + plop


def steam(dur=1.6):
    """The bloom: broadband shriek cooling to a sigh — a lowpass
    whose corner glides down, plus sparse droplet ticks."""
    n = int(dur * SR)
    w = rng.standard_normal(n)
    out = np.zeros(n)
    # time-varying one-pole: corner 5k -> 500 exponential
    a_hi = np.exp(-2 * np.pi * 5000.0 / SR)
    a_lo = np.exp(-2 * np.pi * 500.0 / SR)
    tt = np.linspace(0, 1, n)
    a = a_hi + (a_lo - a_hi) * (tt ** 0.6)
    lp = 0.0
    for i in range(n):
        lp = lp * a[i] + w[i] * (1 - a[i])
        out[i] = lp
    # fixed highpass to lift rumble; the GLIDE carries the cooling.
    # (a differencing hp here was a +6dB/oct shelf that erased the
    # glide — centroid pinned at 13k regardless of the corner)
    sos = butter(2, 300 / (SR / 2), "highpass", output="sos")
    out = sosfilt(sos, out)
    env = np.exp(-tt * 2.2) * (1 - np.exp(-tt * 40))
    out = out * env * 4.0
    for _ in range(6):    # droplets: the puddle answering
        t0 = rng.uniform(0.3, dur - 0.1)
        m = int(0.03 * SR)
        i0 = int(t0 * SR)
        d = np.sin(2 * np.pi * rng.uniform(900, 1800)
                   * np.arange(m) / SR) * ad_env(m, 0.001, 90.0) * 0.12
        out[i0:i0 + m] += d
    return out


def scrape():
    """One flint tick: a short grainy bright scratch."""
    n = int(0.07 * SR)
    w = rng.standard_normal(n)
    grain = np.sign(np.sin(2 * np.pi * 38.0 * np.arange(n) / SR))
    return bp(w * (0.6 + 0.4 * grain), 2200, 6800) \
        * ad_env(n, 0.004, 40.0) * 0.8


def whump():
    """The catch: air igniting — a soft low bloom, no click."""
    n = int(0.5 * SR)
    tt = np.arange(n) / SR
    tone = np.sin(2 * np.pi * (85.0 - 30.0 * tt) * tt) \
        * np.exp(-tt * 7.0)
    breath = bp(rng.standard_normal(n), 150, 700) * np.exp(-tt * 9.0)
    out = (tone * 0.8 + breath * 0.35)
    a = int(0.025 * SR)
    out[:a] *= np.linspace(0, 1, a)
    return out


def crackle_ramp(dur, r0, r1, seed):
    """Fire crackle with event rate ramping r0 -> r1 (the rebirth).
    Hand-rolled so the RATE is the instrument: seeded exponential
    gaps against a linearly interpolated rate. Returns (ticks,
    rumble) SEPARATELY — the tick-count ruler must never share a bus
    with the rumble (early quiet windows let rumble wobble over a
    local threshold and count as ticks)."""
    r = np.random.default_rng(seed)
    n = int(dur * SR)
    out = np.zeros(n)
    t = 0.0
    while t < dur:
        rate = r0 + (r1 - r0) * (t / dur)
        t += r.exponential(1.0 / max(rate, 0.3))
        if t >= dur:
            break
        m = int(0.02 * SR)
        i0 = int(t * SR)
        if i0 + m > n:
            break
        out[i0:i0 + m] += bp(r.standard_normal(m), 1200, 5200) \
            * ad_env(m, 0.001, 140.0) * r.uniform(0.2, 0.55)
    rumble = bp(r.standard_normal(n), 40, 200) * 0.12
    return out, rumble


def night_bed(dur):
    """A faint room tone under the whole take (e20's world: 96 Hz +
    soft air). Without it the dark window is DIGITAL ZERO and the
    silence ruler divides by nothing — silence must be measured
    against a floor that exists."""
    n = int(dur * SR)
    tt = np.arange(n) / SR
    hum = np.sin(2 * np.pi * 96.0 * tt) * 0.0035
    sos = butter(2, 900 / (SR / 2), "lowpass", output="sos")
    air = sosfilt(sos, rng.standard_normal(n)) * 0.0025
    return hum + air


def scene():
    n = int(DUR * SR)
    buses = {"fire": np.zeros(n), "rumble": np.zeros(n),
             "steam": np.zeros(n), "scrape": np.zeros(n),
             "whump": np.zeros(n), "bed": np.zeros(n)}

    def put(bus, at, x):
        i0 = int(at * SR)
        m = min(len(x), n - i0)
        buses[bus][i0:i0 + m] += x[:m]

    put("bed", 0.0, night_bed(DUR))
    # act one: the lit world (steady crackle, dies at douse+0.35)
    lit, lit_rum = crackle_ramp(SCENE["douse"] + 0.35, 6.0, 6.0, 1)
    fade = np.linspace(1, 0, int(0.2 * SR))
    lit[-len(fade):] *= fade
    lit_rum[-len(fade):] *= fade
    put("fire", 0.0, lit)
    put("rumble", 0.0, lit_rum)
    # act two: the douse
    put("steam", SCENE["douse"], splash())
    put("steam", SCENE["douse"] + 0.12, steam())
    # act three: the countdown and the catch
    whump_t = SCENE["scrape0"] + TELEGRAPH_S
    for k in range(SCRAPE_N):
        put("scrape", SCENE["scrape0"] + k * 0.32, scrape())
    put("whump", whump_t, whump())
    # act four: rebirth — rate climbs back to steady
    reborn, reborn_rum = crackle_ramp(DUR - whump_t - 0.1, 0.8, 6.0, 2)
    put("fire", whump_t + 0.1, reborn)
    put("rumble", whump_t + 0.1, reborn_rum)
    mix = sum(buses.values())
    return mix / np.max(np.abs(mix)) * 0.85, buses, whump_t


# ---- the rulers -----------------------------------------------------

def pcentroid(x):
    spec = np.abs(np.fft.rfft(x)) ** 2
    f = np.fft.rfftfreq(len(x), 1 / SR)
    return float((spec * f).sum() / (spec.sum() + 1e-12))


def tick_times(bus, a_s, b_s, thresh=0.25):
    """Onset times in [a_s, b_s). Threshold is a fraction of THIS
    segment's peak — so a caller comparing counts across windows
    must pass one segment and bin afterward, never call per-window
    (per-window normalization is the loam standing sin)."""
    seg = np.abs(bus[int(a_s * SR):int(b_s * SR)])
    k = int(0.004 * SR)
    env = np.convolve(seg, np.ones(k) / k, "same")
    pk, _ = find_peaks(env, height=env.max() * thresh,
                       distance=int(0.1 * SR))
    return pk / SR + a_s


if __name__ == "__main__":
    mix, buses, whump_t = scene()
    write_wav(os.path.join(outdir, "e24_watercycle.wav"),
              stereo(mix, 0.0))

    st = buses["steam"][int((SCENE["douse"] + 0.12) * SR):
                        int((SCENE["douse"] + 0.12 + 1.6) * SR)]
    c0 = pcentroid(st[:int(0.3 * SR)])
    c1 = pcentroid(st[-int(0.3 * SR):])
    print("== steam cooling: %.0f -> %.0f Hz (x%.1f, want > 2) =="
          % (c0, c1, c0 / max(c1, 1)))

    lit_rms = float(np.sqrt((mix[int(0.5 * SR):int(1.8 * SR)] ** 2).mean()))
    gap_rms = float(np.sqrt((mix[int(4.0 * SR):int(4.5 * SR)] ** 2).mean()))
    print("== the window: lit rms %.4f vs dark %.4f (1/%.0f, want > 8) =="
          % (lit_rms, gap_rms, lit_rms / max(gap_rms, 1e-9)))

    scr = tick_times(buses["scrape"], SCENE["scrape0"] - 0.2,
                     whump_t + 0.1)
    wh = tick_times(buses["whump"], whump_t - 0.2, whump_t + 0.5,
                    thresh=0.5)
    tele = (wh[0] - scr[0]) * 1000 if len(scr) and len(wh) else -1
    print("== telegraph: %d scrapes, first->whump %.0f ms (design %.0f) =="
          % (len(scr), tele, TELEGRAPH_S * 1000))

    print("== rebirth ramp (crackle ticks per 1.4s window) ==")
    ticks = tick_times(buses["fire"], whump_t + 0.1, DUR, thresh=0.12)
    counts = [int(((ticks >= whump_t + 0.1 + k * 1.4)
                   & (ticks < whump_t + 0.1 + (k + 1) * 1.4)).sum())
              for k in range(3)]
    print("  %s : %s" % (counts,
          "RISES" if counts[0] < counts[1] < counts[2] else "NO"))

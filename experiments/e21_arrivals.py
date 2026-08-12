#!/usr/bin/env python3
"""e21 — Arrival by material. SFX prototype for NOCK's arrow-arrival
family: the same arrow, four grounds. STONE clatters (no bite — the
shaft skitters), WOOD thunks and HOLDS (the stuck shaft quivers),
METAL rings (long, beating — the fixture remembers), BODY swallows
(the kill word is the family's whisper).

The idea under test: material arrivals read as ONE event vocabulary
when they share a single excitation — a 3 ms broadhead contact snap —
and differ only in the body it drives. That is NOCK's uniform-grammar
law done in audio: same word, material timbre. Physics agrees
(impact sound = excitation x resonator), so legibility and
simulation shake hands for once.

Each material carries one measurable signature:
  STONE  bounce train — impact + 3 rebounds, countable envelope peaks
  WOOD   stuck-shaft quiver — a ~64 Hz cantilever ring under the
         thunk; the family's lowest centroid
  METAL  detuned mode pairs — an envelope-visible beat in the ring
         tail; the family's longest decay and highest centroid
  BODY   no modes to speak of — lowest crest AND lowest level (its
         in-game noise radius is the smallest; the sound says so)

Impact speed scales the family the way NOCK's loose_voice scales the
launch: velocity drives level AND mallet hardness (bright), so a
soft lob arrives darker, not just quieter.

Render: e21_arrivals.wav — full-power row (stone, wood, metal,
body), then the soft-lob row, 1.4s spacing, light exterior tail.

Measured, each claim on its OWN bus (strike() peak-normalizes per
call, so every cross-material relation below is set by explicit
gains and measured after them):
  - POWER-weighted centroid: bright pair {stone, metal} strictly
    above dark pair {wood, body}. NOT a full ordering — the first
    draft claimed metal > stone and the ruler refused: broadband
    contact noise out-brightens any ring. Brightness separates the
    pairs; RING TIME separates stone from metal.
  - T30 ring time (measured 40 ms past the contact peak): metal
    at least 1.7x the runner-up
  - crest factor: stone highest (skitter spikes), body lowest
  - metal beat rate from the fundamental-pair envelope, decay-ramp
    detrended (~design delta-f)
  - stone bounce count: 4 envelope peaks (impact + 3 rebounds)
  - full vs soft: every material drops in rms AND none brightens;
    stone/wood/metal darken (velocity buys knock + mallet
    hardness), body stays tint-flat — flesh has no hardness range

    python3 experiments/e21_arrivals.py [outdir]
"""

import os
import sys

import numpy as np
from scipy.signal import butter, sosfilt, find_peaks

sys.path.insert(0, os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))))
from loam import SR, stereo, write_wav, ad_env
from loam.modal import strike, WOOD
from loam.space import reverb_tail
from loam.dyn import limiter

outdir = sys.argv[1] if len(sys.argv) > 1 else "render"
os.makedirs(outdir, exist_ok=True)
rng = np.random.default_rng(0xE21)

# the resonators the arrow finds
STONE_T = [(1.0, 1.0, 1.0), (2.76, 0.80, 0.75), (5.40, 0.55, 0.55),
           (8.93, 0.35, 0.40), (13.3, 0.20, 0.30)]   # plate-inharmonic
STONE_F0 = 420.0
WOOD_F0 = 168.0
# the lamp tube: anvil-family inharmonic ratios but LONG rings — thin
# steel remembers (ANVIL's own ring multipliers are smithy-short)
LAMP_T = [(1.0, 1.0, 1.0), (1.51, 0.50, 0.85), (2.39, 0.34, 0.70),
          (3.66, 0.26, 0.55), (5.43, 0.15, 0.42)]
METAL_F0 = 900.0
METAL_DETUNE = 10.0      # cents -> ~5.2 Hz beat at the fundamental
SHAFT_F0 = 64.0          # the stuck arrow's cantilever mode


def snap(v, seed):
    """The broadhead contact — the shared word. 3 ms bandpassed
    tick; velocity buys brightness (band center) and level."""
    r = np.random.default_rng(seed)
    n = int(0.003 * SR)
    w = r.standard_normal(n) * ad_env(n, 0.0003, 900.0)
    lo, hi = 1400.0 + 1400.0 * v, 3200.0 + 2600.0 * v
    sos = butter(2, [lo / (SR / 2), hi / (SR / 2)], "bandpass",
                 output="sos")
    return sosfilt(sos, w) * (0.15 + 0.85 * v)


def arrive_stone(v, seed):
    """Clatter: the arrow does not bite stone — it hits and
    skitters. Impact + 3 rebounds, each shorter, darker, softer."""
    r = np.random.default_rng(seed)
    dur = 0.9
    out = np.zeros(int(dur * SR))
    t_at = 0.0
    gain = 1.0
    for b in range(4):                       # impact + 3 rebounds
        s = strike(STONE_F0 * (1.0 + 0.06 * b), 0.10 - 0.012 * b,
                   STONE_T, bright=(0.40 + 0.45 * v) * 0.82 ** b,
                   rng=r, knock=(0.3 + 1.1 * v) * 0.82 ** b)
        i0 = int(t_at * SR)
        n = min(len(s), len(out) - i0)
        out[i0:i0 + n] += s[:n] * gain
        t_at += 0.17 - 0.035 * b             # rebounds tighten
        gain *= 0.45
    out[:len(snap(v, seed))] += snap(v, seed) * 1.2
    return out * (0.25 + 0.75 * v)


def arrive_wood(v, seed):
    """Thunk + bite: the arrow sticks. A deep short knock, then the
    shaft's own cantilever quiver rings under it."""
    r = np.random.default_rng(seed)
    body = strike(WOOD_F0, 0.22, WOOD, bright=0.35 + 0.45 * v,
                  rng=r, knock=0.5 + 1.3 * v)
    dur = max(0.6, len(body) / SR)
    out = np.zeros(int(dur * SR))
    out[:len(body)] += body
    tt = np.arange(len(out)) / SR
    # the quiver does NOT scale with speed: sticking is sticking,
    # and the cantilever rings at its own amplitude once bitten
    quiver = (np.sin(2 * np.pi * SHAFT_F0 * tt)
              + 0.35 * np.sin(2 * np.pi * SHAFT_F0 * 2.7 * tt)) \
        * np.exp(-tt * 9.0) * 0.28
    a_n = int(0.004 * SR)
    quiver[:a_n] *= np.linspace(0, 1, a_n)
    out += quiver
    out[:len(snap(v, seed))] += snap(v, seed) * 0.8
    return out * (0.25 + 0.75 * v)


def arrive_metal(v, seed):
    """Ring: the fixture remembers the hit. Detuned mode pairs beat
    in the tail; the shaft drops off and ticks once on the ground."""
    r = np.random.default_rng(seed)
    ring = strike(METAL_F0, 1.3, LAMP_T, bright=0.55 + 0.45 * v,
                  detune=METAL_DETUNE, rng=r, knock=0.2 + 0.5 * v)
    dur = max(1.6, len(ring) / SR)
    out = np.zeros(int(dur * SR))
    out[:len(ring)] += ring
    drop = strike(340.0, 0.06, WOOD, bright=0.5, rng=r,
                  knock=0.9 * v)
    i0 = int(0.30 * SR)
    out[i0:i0 + len(drop)] += drop * 0.35 * v
    out[:len(snap(v, seed))] += snap(v, seed) * 1.0
    return out * (0.22 + 0.78 * v)


def arrive_body(v, seed):
    """The kill word: soft tissue has no modes worth the name. A
    dark thump and a breath of cloth — the family's whisper."""
    r = np.random.default_rng(seed)
    dur = 0.35
    n = int(dur * SR)
    tt = np.arange(n) / SR
    thump = np.sin(2 * np.pi * (110.0 - 30.0 * tt / dur) * tt) \
        * np.exp(-tt * 26.0)
    cloth = r.standard_normal(n) * np.exp(-tt * 20.0)
    sos = butter(2, 900.0 / (SR / 2), "lowpass", output="sos")
    cloth = sosfilt(sos, cloth)
    out = thump * 0.9 + cloth * 0.22
    out[:len(snap(v, seed))] += snap(v, seed) * 0.35   # muffled word
    return out * (0.20 + 0.55 * v)


MATERIALS = [("stone", arrive_stone, 0.80),
             ("wood", arrive_wood, 0.85),
             ("metal", arrive_metal, 0.75),
             ("body", arrive_body, 0.55)]
SPACING = 1.4
ROW_GAP = 0.8


def render():
    total = 2 * (SPACING * len(MATERIALS)) + ROW_GAP + 1.2
    n = int(total * SR)
    mix = np.zeros((n, 2))
    buses = {}
    for row, v in enumerate([1.0, 0.35]):
        for k, (name, fn, gain) in enumerate(MATERIALS):
            at = row * (SPACING * len(MATERIALS) + ROW_GAP) \
                + k * SPACING
            mono = fn(v, 0xE21 + 16 * row + k) * gain
            key = (name, "full" if v == 1.0 else "soft")
            buses[key] = (at, mono)
            c = stereo(mono, (k - 1.5) * 0.25)
            i0 = int(at * SR)
            m = min(len(c), n - i0)
            mix[i0:i0 + m] += c[:m]
    wet = reverb_tail(mix, t60=0.9, mix=0.10)
    return limiter(wet, ceiling=0.9), buses


# ---- the rulers -----------------------------------------------------

def centroid(mono):
    """POWER-weighted spectral centroid of a whole bus."""
    spec = np.abs(np.fft.rfft(mono)) ** 2
    f = np.fft.rfftfreq(len(mono), 1 / SR)
    return float((spec * f).sum() / (spec.sum() + 1e-12))


def t30(mono):
    """Ring time: seconds from 40 ms past the envelope peak down to
    -30 dB below THAT point. Measured past the contact on purpose —
    a knock's crest would otherwise hand every material the same
    verdict (the tail is already 'quiet' next to the spike)."""
    k = int(0.005 * SR)
    env = np.convolve(np.abs(mono), np.ones(k) / k, "same")
    p = int(np.argmax(env)) + int(0.040 * SR)
    if p >= len(env):
        return 0.0
    th = env[p] * 10 ** (-30 / 20)
    below = np.where(env[p:] < th)[0]
    return float(below[0] / SR) if len(below) else len(env[p:]) / SR


def crest(mono):
    rms = np.sqrt(np.mean(mono ** 2) + 1e-18)
    return float(np.max(np.abs(mono)) / rms)


def beat_rate(mono, a_s, b_s, f0):
    """Envelope-spectrum peak of the ring tail, 1..12 Hz — measured
    on the FUNDAMENTAL PAIR alone (bandpass f0 +/- 8%). Every
    detuned mode beats at its own delta-f; the mixed-bus envelope
    is a committee, and the shaft-drop tick votes too."""
    sos = butter(2, [f0 * 0.92 / (SR / 2), f0 * 1.08 / (SR / 2)],
                 "bandpass", output="sos")
    seg = np.abs(sosfilt(sos, mono)[int(a_s * SR):int(b_s * SR)])
    k = int(0.01 * SR)
    env = np.convolve(seg, np.ones(k) / k, "same")
    # detrend against the decay ramp, not the mean — the ring's
    # exponential slope is the loudest 'low frequency' in the
    # envelope and buries the beat under mere mean-subtraction
    kb = int(0.35 * SR)
    base = np.convolve(env, np.ones(kb) / kb, "same")
    env = env - base
    spec = np.abs(np.fft.rfft(env * np.hanning(len(env))))
    f = np.fft.rfftfreq(len(env), 1 / SR)
    band = (f >= 1.0) & (f <= 12.0)
    return float(f[band][np.argmax(spec[band])])


def bounce_count(mono):
    k = int(0.004 * SR)
    env = np.convolve(np.abs(mono), np.ones(k) / k, "same")
    pk, _ = find_peaks(env, height=env.max() * 0.05,
                       distance=int(0.05 * SR))
    return len(pk)


if __name__ == "__main__":
    out, buses = render()
    write_wav(os.path.join(outdir, "e21_arrivals.wav"), out)

    full = {m: buses[(m, "full")][1] for m, _, _ in MATERIALS}
    soft = {m: buses[(m, "soft")][1] for m, _, _ in MATERIALS}

    print("== centroids (POWER-weighted, full row) ==")
    cents = {m: centroid(b) for m, b in full.items()}
    for m, c in cents.items():
        print("  %-6s %7.1f Hz" % (m, c))
    bright_pair = min(cents["stone"], cents["metal"]) \
        > max(cents["wood"], cents["body"])
    print("  bright pair {stone, metal} > dark pair {wood, body}:",
          "YES" if bright_pair else "NO")

    print("== T30 ring time (full row) ==")
    decs = {m: t30(b) for m, b in full.items()}
    for m, d in decs.items():
        print("  %-6s %6.3f s" % (m, d))
    others = [d for m, d in decs.items() if m != "metal"]
    print("  metal rings %.1fx the runner-up (want >= 1.7)"
          % (decs["metal"] / max(others)))

    print("== crest factor (full row) ==")
    crs = {m: crest(b) for m, b in full.items()}
    for m, c in crs.items():
        print("  %-6s %6.1f" % (m, c))

    beat = beat_rate(full["metal"], 0.45, 1.3, METAL_F0)
    want = METAL_F0 * (2 ** (METAL_DETUNE / 1200.0) - 1)
    print("== metal beat: %.1f Hz (design ~%.1f) ==" % (beat, want))
    print("== stone bounces: %d envelope peaks (design 4) =="
          % bounce_count(full["stone"]))

    print("== soft lob vs full (rms dB drop / centroid ratio) ==")
    for m, _, _ in MATERIALS:
        rf = np.sqrt(np.mean(full[m] ** 2))
        rs = np.sqrt(np.mean(soft[m] ** 2))
        print("  %-6s %+5.1f dB, centroid x%.2f" % (
            m, 20 * np.log10(rs / (rf + 1e-12)),
            centroid(soft[m]) / (cents[m] + 1e-12)))

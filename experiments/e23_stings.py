#!/usr/bin/env python3
"""e23 — Detection stings per awareness state, in two accents. The
NOCK cue list wants a sting per awareness rung; the e22 registers
want alarm language that matches the ground it stands on. The
law-2 tension (stings are GRAMMAR — contract words, identical
everywhere) resolves as: THE GESTURE IS THE WORD, THE REGISTER IS
THE ACCENT. Pitch contour, rhythm, and envelope arc are identical
in both dresses; only the instrument changes. And unlike the e22
melody, stings take NO cents drift and NO swing even in flame
dress — the alarm is the one thing the margins say precisely.

Three rungs, escalating (D minor pentatonic, e22's world):
  NOTICE (suspicious): two notes, a rising question.     ~0.5s
  HUNT   (searching):  three notes circling downward-up. ~0.7s
  CAUGHT (spotted):    four notes falling to a low slam. ~1.0s

Two dresses per rung:
  FLAME:     gut pluck + a wood knock on the first onset
  LIGHTNING: struck glass + a low hum swell underneath (192 Hz,
             the institution's octave line, rising through the word)

Measured, per rung and dress:
  - gesture identity: onset times within 8 ms of the DESIGN in
    both dresses (grammar rhythm is grid-precise); note pitches
    within 15 cents of design by harmonic product spectrum
  - escalation: rms and duration strictly rise notice < hunt <
    caught within each dress
  - the accent is real: lightning's tail (last 0.2s vs peak)
    carries far more than flame's — glass + hum sustain, gut dies

    python3 experiments/e23_stings.py [outdir]
"""

import os
import sys

import numpy as np
from scipy.signal import find_peaks

sys.path.insert(0, os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))))
from loam import SR, hz, stereo, write_wav
from loam.modal import strike, GLASS, WOOD
from loam.strings import pluck

outdir = sys.argv[1] if len(sys.argv) > 1 else "render"
os.makedirs(outdir, exist_ok=True)
rng = np.random.default_rng(0xE23)

HUM_HZ = 192.0     # the institution's octave line (2 x 96)

# the words: (t_s, midi, dur_s) — grammar, shared verbatim by both
# dresses, forever
GESTURES = {
    "notice": [(0.00, 57, 0.20), (0.16, 60, 0.34)],
    "hunt":   [(0.00, 55, 0.16), (0.14, 53, 0.16), (0.28, 57, 0.42)],
    "caught": [(0.00, 62, 0.12), (0.11, 60, 0.12), (0.22, 57, 0.14),
               (0.36, 50, 0.64)],
}
LEVELS = {"notice": 0.45, "hunt": 0.62, "caught": 0.92}


def dress_flame(word, level):
    dur = word[-1][0] + word[-1][2] + 0.5
    out = np.zeros(int(dur * SR))
    for k, (t0, midi, d) in enumerate(word):
        p = pluck(hz(midi), d + 0.4, amp=level * (1.3 if k == len(word) - 1
                  else 1.0), t60=0.9, damp=0.5, soft=1,
                  seed=int(rng.integers(1 << 30)))
        i0 = int(t0 * SR)
        n = min(len(p), len(out) - i0)
        out[i0:i0 + n] += p[:n]
    kn = strike(hz(word[0][1] - 12), 0.18, WOOD, amp=level * 0.5,
                bright=0.7, rng=rng, knock=1.0)
    out[:len(kn)] += kn[:len(out)]
    return out


def dress_lightning(word, level):
    dur = word[-1][0] + word[-1][2] + 0.5
    n = int(dur * SR)
    out = np.zeros(n)
    for k, (t0, midi, d) in enumerate(word):
        s = strike(hz(midi), max(d + 0.3, 0.5), GLASS,
                   amp=level * (1.3 if k == len(word) - 1 else 1.0) * 0.8,
                   bright=1.1, rng=rng, knock=0.15)
        i0 = int(t0 * SR)
        m = min(len(s), n - i0)
        out[i0:i0 + m] += s[:m]
    # the hum swell: the institution leans in as the word lands
    tt = np.arange(n) / SR
    swell = np.minimum(tt / (word[-1][0] + 0.1), 1.0) ** 2 \
        * np.exp(-np.maximum(tt - (word[-1][0] + word[-1][2]), 0) * 6.0)
    out += np.sin(2 * np.pi * HUM_HZ * tt) * swell * level * 0.10
    return out


# ---- the rulers -----------------------------------------------------

def onset_times(x, n_expect):
    m = np.abs(x)
    k = int(0.008 * SR)
    env = np.convolve(m, np.ones(k) / k, "same")
    d = np.diff(env)
    d[d < 0] = 0
    pk, _ = find_peaks(d, height=d.max() * 0.18,
                       distance=int(0.09 * SR))
    return pk[:n_expect] / SR


def note_pitch(seg, f_design):
    """Plain spectral peak within +/-15% of the designed
    fundamental. Two rulers died here in sequence: open-band HPS
    octave-erred (+1196/+2398 — a bright string's even harmonics
    outvote the fundamental through the product), and band-limited
    HPS then lied about GLASS by +237 cents — HPS assumes HARMONIC
    spectra, and glass's inharmonic 2.32x mode masquerades as the
    2nd harmonic of a false fundamental at 1.16x. Match-to-design
    in a narrow band needs no harmonic model at all: the
    fundamental mode is the loudest thing in its own neighborhood,
    for string and bell alike."""
    spec = np.abs(np.fft.rfft(seg * np.hanning(len(seg)), n=1 << 16))
    f = np.fft.rfftfreq(1 << 16, 1 / SR)
    band = (f >= f_design * 0.85) & (f <= f_design * 1.15)
    return float(f[band][np.argmax(spec[band])])


def cents(a, b):
    return 1200.0 * np.log2(a / b)


def tail_ratio(x):
    env = np.abs(x)
    return float(env[-int(0.25 * SR):].mean() / (env.max() + 1e-12))


if __name__ == "__main__":
    renders = {}
    for name, word in GESTURES.items():
        renders[(name, "flame")] = dress_flame(word, LEVELS[name])
        renders[(name, "lightning")] = dress_lightning(word, LEVELS[name])

    gap = int(0.7 * SR)
    seq = []
    for dress in ("flame", "lightning"):
        for name in GESTURES:
            seq.append(renders[(name, dress)])
            seq.append(np.zeros(gap))
    demo = np.concatenate(seq)
    demo = demo / np.max(np.abs(demo)) * 0.85
    write_wav(os.path.join(outdir, "e23_stings.wav"), stereo(demo, 0.0))

    print("== gesture identity (grammar) ==")
    ok = True
    for name, word in GESTURES.items():
        for dress in ("flame", "lightning"):
            x = renders[(name, dress)]
            t = onset_times(x, len(word))
            dev = [abs(a - b[0]) * 1000 for a, b in zip(t, word)]
            worst = max(dev) if len(dev) == len(word) else 999
            line = "  %-6s %-9s onsets %d/%d, worst %+.0f ms" % (
                name, dress, len(t), len(word), worst)
            pitches = []
            for (t0, midi, d) in word:
                seg = x[int((t0 + 0.02) * SR):int((t0 + min(d, 0.12) + 0.02) * SR)]
                pitches.append(cents(note_pitch(seg, hz(midi)), hz(midi)))
            worst_c = max(abs(c) for c in pitches)
            line += ", worst pitch %+.0f cents" % worst_c
            if worst > 8 or worst_c > 15:
                ok = False
                line += "  <-- FAIL"
            print(line)
    print("  grammar: %s" % ("HOLDS" if ok else "BROKEN"))

    print("== escalation (rms, duration) ==")
    for dress in ("flame", "lightning"):
        rmss = [float(np.sqrt((renders[(n, dress)] ** 2).mean()))
                for n in GESTURES]
        durs = [len(renders[(n, dress)]) / SR for n in GESTURES]
        mono = all(a < b for a, b in zip(rmss, rmss[1:])) \
            and all(a < b for a, b in zip(durs, durs[1:]))
        print("  %-9s rms %s dur %s : %s" % (
            dress, ["%.3f" % r for r in rmss],
            ["%.2f" % d for d in durs], "RISES" if mono else "NO"))

    print("== the accent is real (tail/peak, last 0.25s) ==")
    for name in GESTURES:
        tf = tail_ratio(renders[(name, "flame")])
        tl = tail_ratio(renders[(name, "lightning")])
        print("  %-6s flame %.3f  <<  lightning %.3f : %s"
              % (name, tf, tl, "YES" if tl > 2.0 * tf else "NO"))

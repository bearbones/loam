"""Prototype C2: a tone as the latent primitive, with an additive decoder.

    python3 -m soundgarden.tone --build --train --walk 8     # corpus, fit, traversal WAVs
    python3 -m soundgarden.tone analyze note.wav --out resynth.wav

The struck-sound latent (latent.py) failed at its decoder: a mel grid with a
time axis cannot be inverted without smearing attacks. A stationary tone has
no time axis. Its descriptor is one spectrum, split the way additive synthesis
wants it: 64 harmonic amplitudes at k·f0·sqrt(1 + B·k²) (B = inharmonicity, a
piano-style stretch), plus 24 noise band levels for what sits between the
harmonics. Decoding is an oscillator bank plus shaped noise, exact for
stationary sounds, no phase recovery. Time is a separate, optional factor:
per-harmonic and per-band decay rates multiply the tone afterwards.

The corpus comes from Loam's own tone makers (PADsynth saws and vowels, analog
waveforms, bowed modal tables, flute/ney/reed, plucked strings) plus
Soundgarden renders, all analyzed by the same function, so the
latent is a timbre space rather than a recipe space. Sounds that do not sit on
a stretched harmonic grid (bells) are the honest limit: their partials land
between harmonics and are absorbed by the noise bands.
"""
import argparse
import json
from pathlib import Path
import time

import numpy as np

from loam import SR, hz
from .describe import BANDS, FLOOR_DB, _BANK
from .stft import HOP, NFFT, istft, stft
from .synth import wav_bytes

VERSION = "soundgarden-tone/0"
HARMONICS = 64
STRETCHES = np.concatenate([[0.0], np.logspace(-5, -1.5, 71)])  # inharmonicity B candidates
SEARCH = .03   # ±fraction of the predicted partial frequency to look for its peak
MASK_BINS = 3
ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DIR = ROOT / "render/soundgarden-tone"
FREQS = np.fft.rfftfreq(NFFT, 1 / SR)
STRETCH_CODE = lambda b: float(np.clip((np.log10(max(b, 1e-6)) + 6) / 6, 0, 1))
STRETCH_FROM_CODE = lambda c: 0.0 if c <= 1e-3 else float(10 ** (6 * c - 6))


def partial_frequencies(f0, stretch, count=HARMONICS):
    k = np.arange(1, count + 1)
    return f0 * k * np.sqrt(1 + stretch * k * k)


def steady_spectrum(signal, skip=(.15, .15)):
    """Mean STFT power over the middle of a sound, so vibrato and noise average out."""
    x = np.asarray(signal, dtype=float)
    if x.ndim == 2:
        x = x.mean(axis=1)
    spec = np.abs(stft(x)) ** 2
    a, b = int(len(spec) * skip[0]), int(len(spec) * (1 - skip[1]))
    if b - a < 2:
        a, b = 0, len(spec)
    return spec[a:b].mean(axis=0)


def estimate_f0(power, lo_hz=40.0, hi_hz=2000.0):
    """Lowest peak within 20 dB of the strongest, refined by parabolic interpolation."""
    p = np.where((FREQS >= lo_hz) & (FREQS <= hi_hz), power, 0)
    peaks = np.flatnonzero((p[1:-1] > p[:-2]) & (p[1:-1] >= p[2:]) & (p[1:-1] > p.max() * .01)) + 1
    if not len(peaks):
        return 261.63
    k = int(peaks[0])
    a, b, c = np.log(power[k - 1:k + 2] + 1e-30)
    shift = .5 * (a - c) / (a - 2 * b + c) if (a - 2 * b + c) != 0 else 0
    return float((k + np.clip(shift, -.5, .5)) * SR / NFFT)


def _peak_near(power, frequency):
    lo = int(np.floor(frequency * (1 - SEARCH) * NFFT / SR))
    hi = int(np.ceil(frequency * (1 + SEARCH) * NFFT / SR))
    lo, hi = max(lo, 1), min(hi, len(power) - 1)
    if hi < lo:
        return 0.0, lo
    k = lo + int(np.argmax(power[lo:hi + 1]))
    if 1 <= k < len(power) - 1:  # parabolic peak height in log power removes the scalloping loss
        a, b, c = np.log(power[k - 1:k + 2] + 1e-30)
        curve = a - 2 * b + c
        if curve < 0 and abs(.5 * (a - c) / curve) <= .5:  # a real interior peak; the loss is at most 1.4 dB
            return float(np.exp(min(b - (a - c) ** 2 / (8 * curve), b + .4))), k
    return float(power[k]), k


def estimate_stretch(power, f0, count=24, tolerance=.01):
    """Grid search the stretch whose predicted partials land closest to strong peaks.

    Each partial scores its dB above a −60 dB floor, discounted by a Gaussian in
    the fractional distance between the predicted and found frequency, so empty
    windows score nothing and a partial caught off-center counts little."""
    best, best_score = 0.0, -1.0
    top = max(power.max(), 1e-20)
    for stretch in STRETCHES:
        score = 0.0
        for f in partial_frequencies(f0, stretch, count):
            if f >= SR * .45:
                break
            p, k = _peak_near(power, f)
            offset = (k * SR / NFFT - f) / f
            score += max(10 * np.log10(p / top + 1e-20) + 60, 0) * np.exp(-.5 * (offset / tolerance) ** 2)
        if score > best_score + 1e-9:
            best, best_score = float(stretch), score
    return best


def profile(signal, f0=None, skip=(.15, .15)):
    """Tone descriptor: f0, stretch, harmonic dB (≤ 0), noise band dB, same reference."""
    power = steady_spectrum(signal, skip)
    f0 = estimate_f0(power) if f0 is None else float(f0)
    stretch = estimate_stretch(power, f0)
    freqs = partial_frequencies(f0, stretch)
    mask = np.ones(len(power), dtype=bool)
    harmonic_power = np.zeros(HARMONICS)
    for i, f in enumerate(freqs):
        if f >= SR * .45:
            break
        harmonic_power[i], k = _peak_near(power, f)
        mask[max(k - MASK_BINS, 0):k + MASK_BINS + 1] = False
    reference = max(harmonic_power.max(), 1e-20)
    band_power = (power * mask) @ _BANK.T
    return {"version": VERSION, "f0": f0, "stretch": stretch,
            "harmonics": np.clip(10 * np.log10(harmonic_power / reference + 1e-20), FLOOR_DB, 0).tolist(),
            "noise": np.clip(10 * np.log10(band_power / reference + 1e-20), FLOOR_DB, 0).tolist()}


def vector(tone):
    """89 numbers in [-1, 1]: harmonics, noise bands, stretch code."""
    return np.concatenate([np.asarray(tone["harmonics"]) / -FLOOR_DB, np.asarray(tone["noise"]) / -FLOOR_DB,
                           [STRETCH_CODE(tone["stretch"])]])


def from_vector(v, f0=261.63):
    v = np.asarray(v, dtype=float)
    if v.shape != (HARMONICS + BANDS + 1,):
        raise ValueError("A tone vector has 89 numbers.")
    return {"version": VERSION, "f0": float(f0), "stretch": STRETCH_FROM_CODE(float(v[-1])),
            "harmonics": (np.clip(v[:HARMONICS], -1, 0) * -FLOOR_DB).tolist(),
            "noise": (np.clip(v[HARMONICS:-1], -1, 0) * -FLOOR_DB).tolist()}


def synthesize(tone, seconds=1.5, midi=None, decays=None, noise_decay=None, attack=.01, release=.05, seed=0):
    """Additive oscillator bank plus shaped noise. decays: per-harmonic 1/s (the time factor)."""
    f0 = tone["f0"] if midi is None else hz(midi)
    n = max(int(seconds * SR), NFFT)
    t = np.arange(n) / SR
    rng = np.random.default_rng(seed)
    out = np.zeros(n)
    amps = 10 ** (np.asarray(tone["harmonics"]) / 20)
    freqs = partial_frequencies(f0, tone["stretch"])
    for i, (f, a) in enumerate(zip(freqs, amps)):
        if f >= SR * .45 or a <= 10 ** (FLOOR_DB / 20) * 1.01:
            continue
        envelope = np.exp(-decays[i] * t) if decays is not None else 1.0
        out += a * envelope * np.sin(2 * np.pi * f * t + rng.uniform(0, 2 * np.pi))
    # Harmonic amplitudes are STFT peak powers relative to the strongest harmonic; a sine of
    # amplitude a peaks at (a·NFFT/4)² in this STFT, so noise targets are scaled the same way.
    noise = rng.standard_normal(n)
    spec = stft(noise)
    have = (np.abs(spec) ** 2) @ _BANK.T
    want = 10 ** (np.asarray(tone["noise"]) / 10) * (NFFT / 4) ** 2
    if noise_decay is not None:
        frames_t = np.arange(len(spec)) * HOP / SR
        want = want[None, :] * np.exp(-np.asarray(noise_decay)[None, :] * frames_t[:, None])
    else:
        want = np.broadcast_to(want, have.shape)
    band_gain = np.sqrt(want / np.maximum(have, 1e-20))
    bin_weights = _BANK.T / np.maximum(_BANK.sum(axis=0)[:, None], 1e-12)
    out += istft(spec * (band_gain @ bin_weights.T), n)
    ramp_in, ramp_out = min(int(attack * SR), n // 2), min(int(release * SR), n // 2)
    out[:ramp_in] *= np.linspace(0, 1, ramp_in)
    out[-ramp_out:] *= np.linspace(1, 0, ramp_out)
    return (out / (np.max(np.abs(out)) + 1e-12) * .5).astype(np.float32)


def corpus_sources(pitches=(48, 55, 60, 67, 72), soundgarden=400, seed=11):
    """(name, audio, f0) from Loam's tone makers plus Soundgarden renders."""
    from loam.analog import pulse, saw, supersaw
    from loam.modal import ANVIL, BELL, CHURCH_BELL, GLASS, MARIMBA, WOOD, bow
    from loam.pads import VOWELS, formant_amps, padsynth_stereo, saw_amps
    from loam.strings import pluck
    from loam.winds import flute, ney, reedpipe  # loam.voice.sing is left out: its formant bank runs per sample, minutes per note
    from .synth import render
    rng = np.random.default_rng(seed)
    for midi in pitches:
        f = hz(midi)
        for tilt in (.6, 1.0, 1.5, 2.2, 3.0):
            yield f"pad saw tilt {tilt} @{midi}", padsynth_stereo(1.0, f, saw_amps(48, tilt)).mean(axis=1), f
        for name, formants in VOWELS.items():
            yield f"pad {name} @{midi}", padsynth_stereo(1.0, f, formant_amps(f, 48, formants)).mean(axis=1), f
        yield f"saw @{midi}", saw(f, 1.0), f
        for width in (.1, .25, .5):
            yield f"pulse {width} @{midi}", pulse(f, 1.0, width), f
        yield f"supersaw @{midi}", supersaw(f, 1.0).mean(axis=1), f
        for name, table in [("glass", GLASS), ("bell", BELL), ("wood", WOOD), ("marimba", MARIMBA), ("church", CHURCH_BELL), ("anvil", ANVIL)]:
            yield f"bowed {name} @{midi}", bow(f, 1.5, table, rng=np.random.default_rng(midi)), f
        yield f"flute @{midi}", flute(f, 1.2), f
        yield f"flute overblown @{midi}", flute(f, 1.2, overblow=.8), None
        yield f"ney @{midi}", ney(f, 1.2), f
        yield f"reedpipe @{midi}", reedpipe(f, 1.2), f
        for damp in (.2, .5):
            yield f"pluck damp {damp} @{midi}", pluck(f, 1.5, damp=damp), f
    for i in range(soundgarden):
        v = rng.uniform(.025, .975, 10).tolist()
        yield f"soundgarden {i}", render(v, int(rng.choice(pitches))), None


def build_corpus(count_soundgarden=400, seed=11, log=None):
    names, vectors, f0s = [], [], []
    for name, audio, f0 in corpus_sources(soundgarden=count_soundgarden, seed=seed):
        tone = profile(audio, f0, skip=(.05, .3) if name.startswith("soundgarden") or "pluck" in name else (.15, .15))
        names.append(name); vectors.append(vector(tone)); f0s.append(tone["f0"])
        if log and len(names) % 100 == 0:
            log(f"{len(names)} tones analyzed")
    return np.array(names), np.array(vectors), np.array(f0s)


def __getattr__(name):  # the autoencoder lives in latent.py; re-export it lazily so tests and callers find it here
    if name == "Autoencoder":
        from .latent import Autoencoder
        return Autoencoder
    raise AttributeError(name)


def mixup(vectors, count, seed=0):
    """Convex combinations of tones are tones; grow the corpus for the autoencoder."""
    rng = np.random.default_rng(seed)
    i, j = rng.integers(len(vectors), size=(2, count))
    w = rng.uniform(.2, .8, (count, 1))
    return vectors[i] * w + vectors[j] * (1 - w)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("command", nargs="?", choices=["analyze"])
    parser.add_argument("input", nargs="?", type=Path)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--midi", type=int)
    parser.add_argument("--build", action="store_true")
    parser.add_argument("--train", action="store_true")
    parser.add_argument("--epochs", type=int, default=400)
    parser.add_argument("--walk", type=int)
    parser.add_argument("--dir", type=Path, default=DEFAULT_DIR)
    parser.add_argument("--seed", type=int, default=11)
    args = parser.parse_args()
    args.dir.mkdir(parents=True, exist_ok=True)
    if args.command == "analyze":
        from .match import load_wav
        tone = profile(load_wav(args.input.read_bytes()))
        print(json.dumps({k: (round(v, 2) if isinstance(v, float) else v) for k, v in tone.items() if k != "harmonics"}, indent=1))
        print("harmonics dB:", np.round(tone["harmonics"][:16], 1).tolist())
        out = args.out or args.input.with_name(args.input.stem + "-tone.wav")
        out.write_bytes(wav_bytes(synthesize(tone, midi=args.midi)))
        print(f"Wrote {out}")
        return
    from .latent import Autoencoder, pca_baseline
    if args.build:
        t0 = time.time()
        names, vectors, f0s = build_corpus(seed=args.seed, log=print)
        np.savez(args.dir / "corpus.npz", names=names, vectors=vectors, f0s=f0s)
        print(f"Built {len(names)} tones in {time.time() - t0:.0f} s → {args.dir / 'corpus.npz'}")
    if args.train:
        data = np.load(args.dir / "corpus.npz")
        rng = np.random.default_rng(args.seed)
        order = rng.permutation(len(data["vectors"]))
        split = int(len(order) * .85)
        train, test = data["vectors"][order[:split]], data["vectors"][order[split:]]
        train = np.vstack([train, mixup(train, len(train), args.seed)])
        model = Autoencoder(sizes=(HARMONICS + BANDS + 1, 48, 6), seed=args.seed).fit(train, args.epochs, log=print)
        mse = lambda a, b: float(((a - b) ** 2).mean())
        print(f"held-out mse: autoencoder {mse(model.reconstruct(test), test):.5f} | pca-6 {mse(pca_baseline(train)(test), test):.5f} | mean {mse(train.mean(axis=0), test):.5f}")
        model.save(args.dir / "model.npz")
        print(f"Saved {args.dir / 'model.npz'}")
    if args.walk:
        model = Autoencoder.load(args.dir / "model.npz")
        data = np.load(args.dir / "corpus.npz")
        rng = np.random.default_rng(args.seed + 1)
        picks = rng.choice(len(data["vectors"]), 2, replace=False)
        z = model.encode(data["vectors"][picks])
        gap = np.zeros(int(.12 * SR), dtype=np.float32)
        pieces = []
        for i in range(args.walk):
            tone = from_vector(model.decode(z[0] + (z[1] - z[0]) * i / max(args.walk - 1, 1))[0])
            pieces += [synthesize(tone, seconds=.9, seed=i), gap]
        (args.dir / "walk-additive.wav").write_bytes(wav_bytes(np.concatenate(pieces)))
        print(f"Walk from '{data['names'][picks[0]]}' to '{data['names'][picks[1]]}' → {args.dir / 'walk-additive.wav'}")


if __name__ == "__main__":
    main()

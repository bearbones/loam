"""Prototype B: a sinusoidal-plus-residual model of a one-shot sound.

    python3 -m soundgarden.sms input.wav --out resynth.wav
    python3 -m soundgarden.sms a.wav --morph b.wav --steps 5 --out morph.wav
    python3 -m soundgarden.sms --demo                      # Porcelain → Small alloy

Unlike an MFCC sequence, this representation reconstructs audio: each partial
is (frequency ratio, amplitude, decay rate, attack), and everything the partials
miss becomes a 24-band × 8-anchor noise envelope on the same log-time grid the
descriptor uses. The model is a few hundred numbers, any recording can become
one, and interpolating two models is a real morph. Phase is discarded, so a
resynthesis is "the same partials and the same noise", not the same waveform.
This is Serra's SMS idea reduced to exponentially decaying partials, which is
what struck resonators are.
"""
import argparse
import json
from pathlib import Path

import numpy as np

from loam import SR, hz
from .describe import ANCHORS_S, BANDS, TIMES, _BANK, _RATIO, f0_midi
from .stft import HOP, NFFT, frame_times, istft, stft
from .synth import ANCHORS, render, wav_bytes

VERSION = "soundgarden-sms/0"
MAX_PARTIALS = 40
PEAK_FLOOR_DB = -60.0
TRACK_FLOOR_DB = -45.0
MASK_BINS = 4


def _peaks(x, count):
    """Partial frequencies from a zero-padded whole-signal spectrum."""
    n = len(x)
    m = 1 << int(np.ceil(np.log2(max(n * 4, 4096))))
    spec = np.abs(np.fft.rfft(x * np.hanning(n), m))
    freqs = np.fft.rfftfreq(m, 1 / SR)
    floor = spec.max() * 10 ** (PEAK_FLOOR_DB / 20)
    guard = max(int(4 * m / n), 2)  # a Hann main lobe in padded bins
    found = []
    candidates = np.flatnonzero((spec[1:-1] > spec[:-2]) & (spec[1:-1] >= spec[2:]) & (spec[1:-1] > floor)) + 1
    for k in candidates[np.argsort(spec[candidates])[::-1]]:
        if not 30 <= freqs[k] <= SR * .45:
            continue
        if any(abs(k - other) < guard for other, _ in found):
            continue
        a, b, c = np.log(spec[k - 1:k + 2] + 1e-20)
        shift = .5 * (a - c) / (a - 2 * b + c) if (a - 2 * b + c) != 0 else 0
        found.append((k, freqs[k] + shift * SR / m))
        if len(found) >= count:
            break
    return sorted(f for _, f in found)


def _track(spec, frequency):
    """Sine amplitude per frame at a frequency, interpolating neighboring bins."""
    position = frequency * NFFT / SR
    k = int(np.floor(position))
    frac = position - k
    magnitude = np.abs(spec[:, k]) * (1 - frac) + np.abs(spec[:, min(k + 1, spec.shape[1] - 1)]) * frac
    return 4 * magnitude / NFFT


def _fit(envelope, times):
    """Exponential fit: amplitude, decay per second, attack seconds."""
    peak = envelope.max()
    if peak <= 0:
        return 0.0, 10.0, .001
    usable = envelope > peak * 10 ** (TRACK_FLOOR_DB / 20)
    start = int(np.argmax(envelope >= .9 * peak))
    t, y, w = times[usable], np.log(envelope[usable]), envelope[usable]
    if len(t) < 3 or np.ptp(t) <= 0:
        return float(peak), 10.0, float(times[start])
    slope, intercept = np.polyfit(t, y, 1, w=np.sqrt(w))
    decay = float(np.clip(-slope, .05, 400))
    amplitude = float(min(np.exp(intercept), peak * 1.5))
    return amplitude, decay, float(max(times[start], .0005))


def _residual_grid(power):
    """Band power averaged inside each log-time anchor window (linear units)."""
    times = frame_times(len(power))
    out = np.zeros((BANDS, TIMES))
    for j, anchor in enumerate(ANCHORS_S):
        inside = (times >= anchor / _RATIO) & (times < anchor * _RATIO)
        if inside.any():
            out[:, j] = power[inside].mean(axis=0)
    return out


def analyze(signal, partials=24):
    x = np.asarray(signal, dtype=float)
    partials = int(np.clip(partials, 1, MAX_PARTIALS))
    frequencies = _peaks(x, partials)
    spec = stft(x)
    times = frame_times(len(spec))
    f0 = hz(f0_midi(x))
    if frequencies:
        f0 = min(frequencies, key=lambda f: abs(np.log(f / f0)))
    model_partials = []
    mask = np.ones(spec.shape[1], dtype=bool)
    for f in frequencies:
        amplitude, decay, attack = _fit(_track(spec, f), times)
        model_partials.append({"ratio": f / f0, "amp": amplitude, "decay": decay, "attack": attack})
        k = int(round(f * NFFT / SR))
        mask[max(k - MASK_BINS, 0):k + MASK_BINS + 1] = False
    power = (np.abs(spec) ** 2 * mask[None, :]) @ _BANK.T
    return {"version": VERSION, "f0": float(f0), "seconds": len(x) / SR,
            "partials": model_partials, "residual": _residual_grid(power).tolist()}


def _residual_envelope(grid, times):
    """Interpolate the anchor grid in log time; beyond the last anchor keep decaying."""
    log_anchor = np.log(ANCHORS_S)
    db = 10 * np.log10(np.maximum(np.asarray(grid, dtype=float), 1e-20))
    slope = (db[:, -1] - db[:, -2]) / (log_anchor[-1] - log_anchor[-2])
    lt = np.log(np.maximum(times, ANCHORS_S[0] * .5))
    out = np.empty((len(times), BANDS))
    for b in range(BANDS):
        out[:, b] = np.interp(lt, log_anchor, db[b])
        beyond = lt > log_anchor[-1]
        out[beyond, b] = db[b, -1] + np.minimum(slope[b], 0) * (lt[beyond] - log_anchor[-1])
    return 10 ** (out / 10)


def synthesize(model, midi=None, seconds=None, seed=1729):
    f0 = model["f0"] if midi is None else hz(midi)
    seconds = model["seconds"] if seconds is None else seconds
    n = max(int(seconds * SR), NFFT)
    t = np.arange(n) / SR
    out = np.zeros(n)
    for p in model["partials"]:
        f = f0 * p["ratio"]
        if f * 1.02 >= SR * .45 or p["amp"] <= 0:
            continue
        out += p["amp"] * np.exp(-p["decay"] * t) * np.minimum(t / max(p["attack"], 1e-4), 1) * np.sin(2 * np.pi * f * t)
    noise = np.random.default_rng(seed).standard_normal(n)
    spec = stft(noise)
    have = (np.abs(spec) ** 2) @ _BANK.T
    want = _residual_envelope(model["residual"], frame_times(len(spec)))
    band_gain = np.sqrt(want / np.maximum(have, 1e-20))
    bin_weights = _BANK.T / np.maximum(_BANK.sum(axis=0)[:, None], 1e-12)  # bins → bands, rows sum to 1
    gain = band_gain @ bin_weights.T
    out += istft(spec * gain, n)
    fade = min(int(.02 * SR), n)
    out[-fade:] *= np.linspace(1, 0, fade)
    return np.clip(out, -1, 1).astype(np.float32)


def morph(a, b, t):
    """Interpolate two models: log frequency, log amplitude, log decay, dB residual."""
    t = float(np.clip(t, 0, 1))
    pa = sorted(a["partials"], key=lambda p: p["ratio"])
    pb = sorted(b["partials"], key=lambda p: p["ratio"])
    silent = lambda p: {"ratio": p["ratio"], "amp": 1e-5, "decay": p["decay"], "attack": p["attack"]}
    while len(pa) < len(pb):
        pa.append(silent(pb[len(pa)]))
    while len(pb) < len(pa):
        pb.append(silent(pa[len(pb)]))
    mix = lambda x, y: (1 - t) * x + t * y
    lmix = lambda x, y: float(np.exp(mix(np.log(max(x, 1e-9)), np.log(max(y, 1e-9)))))
    partials = [{"ratio": lmix(p["ratio"], q["ratio"]), "amp": lmix(p["amp"], q["amp"]),
                 "decay": lmix(p["decay"], q["decay"]), "attack": mix(p["attack"], q["attack"])} for p, q in zip(pa, pb)]
    ra, rb = [10 * np.log10(np.maximum(np.asarray(m["residual"], dtype=float), 1e-20)) for m in (a, b)]
    return {"version": VERSION, "f0": lmix(a["f0"], b["f0"]), "seconds": mix(a["seconds"], b["seconds"]),
            "partials": partials, "residual": (10 ** (mix(ra, rb) / 10)).tolist()}


def load(path):
    from .match import load_wav
    return load_wav(Path(path).read_bytes())


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("input", nargs="?", type=Path)
    parser.add_argument("--morph", type=Path, help="Second sound; output walks from input to it")
    parser.add_argument("--steps", type=int, default=5)
    parser.add_argument("--partials", type=int, default=24)
    parser.add_argument("--midi", type=int, help="Resynthesize at this pitch")
    parser.add_argument("--out", type=Path)
    parser.add_argument("--json", type=Path, help="Write the model as JSON")
    parser.add_argument("--demo", action="store_true", help="Morph the Porcelain and Small alloy starters")
    args = parser.parse_args()
    if args.demo:
        a, b = (analyze(render(v)) for v in (ANCHORS[0][1], ANCHORS[3][1]))
    elif args.input:
        a = analyze(load(args.input), args.partials)
        b = analyze(load(args.morph), args.partials) if args.morph else None
    else:
        parser.error("Give an input WAV or --demo.")
    if args.json:
        args.json.write_text(json.dumps(a, indent=1))
    if b is None:
        audio = synthesize(a, args.midi)
        print(f"{len(a['partials'])} partials, f0 {a['f0']:.1f} Hz, {a['seconds']:.2f} s")
    else:
        pieces = [synthesize(morph(a, b, i / max(args.steps - 1, 1)), args.midi) for i in range(args.steps)]
        gap = np.zeros(int(.15 * SR), dtype=np.float32)
        audio = np.concatenate([piece_or_gap for piece in pieces for piece_or_gap in (piece, gap)])
        print(f"{args.steps} morph steps, {len(audio) / SR:.2f} s")
    out = args.out or Path("render/soundgarden-sms.wav")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(wav_bytes(audio))
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()

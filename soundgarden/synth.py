"""A continuous, deterministic struck-resonator space built from Loam mode tables.

No per-sample peak normalization: measurements retain energy differences.
The bounded output stage is shared by the audition server and offline explorer.
"""
import base64
import io
import wave

import numpy as np
import scipy.fft

from loam import SR, hz
from loam.modal import GLASS, WOOD

VERSION = "soundgarden-resonator/1"
DIMENSIONS = ["Material", "Ring", "Brightness", "Damping", "Beating",
              "Mallet", "Softness", "Hollow", "Bloom", "Drive"]
DEFAULT = [0.64, 0.52, 0.51, 0.4, 0.15, 0.2, 0.12, 0.2, 0.18, 0.2]
ANCHORS = [
    ("Porcelain", DEFAULT),
    ("Hollow timber", [0.08, .2, .4, .8, .02, .6, .08, .65, .02, .1]),
    ("Slow glass", [.7, .9, .45, .25, .4, .05, .7, .2, .7, .1]),
    ("Small alloy", [.95, .5, .85, .4, .6, .3, .04, .4, .15, .5]),
]


def validate_vector(value):
    if not isinstance(value, list) or len(value) != len(DIMENSIONS):
        raise ValueError("A recipe needs exactly 10 parameters.")
    if any(isinstance(x, bool) or not isinstance(x, (int, float)) for x in value):
        raise ValueError("Recipe parameters must be numbers.")
    a = np.asarray(value, dtype=float)
    if not np.all(np.isfinite(a)) or np.any(a < 0) or np.any(a > 1):
        raise ValueError("Recipe parameters must be finite numbers between 0 and 1.")
    return a


def render(vector, midi=60):
    p = validate_vector(list(vector))
    if isinstance(midi, bool) or not isinstance(midi, int) or not 48 <= midi <= 84:
        raise ValueError("Choose a whole MIDI note between 48 and 84.")
    material, ring, bright, damp, beating, mallet, soft, hollow, bloom, drive = p
    t60 = .18 * (16 ** ring)
    n = int((t60 * 1.12 + .05) * SR)
    t = np.arange(n) / SR
    # Fixed mode count and smoothly interpolated ratios avoid topology jumps.
    wood = np.array([r for r, _, _ in WOOD[:5]])
    glass = np.array([r for r, _, _ in GLASS])
    metal = np.array([1, 2.0, 2.803, 3.871, 5.074])
    if material < .65:
        ratios = wood + (glass - wood) * material / .65
    else:
        ratios = glass + (metal - glass) * (material - .65) / .35
    signal = np.zeros(n)
    for i, ratio in enumerate(ratios):
        frequency = hz(midi) * ratio
        if frequency * 1.02 >= SR * .45:
            continue
        amplitude = np.exp(-i * (1.75 - 1.45 * bright))
        if i == 0:
            amplitude *= 1 - .8 * hollow
        decay = 6.9078 / (t60 / (1 + i * damp * .8))
        envelope = np.exp(-t * decay)
        if i > 0:
            envelope *= 1 - bloom * .85 * np.exp(-t / (.015 + t60 * .1))
        phase = 2 * np.pi * frequency * t
        pair = 2 ** ((beating ** 2 * 24) / 1200)
        signal += amplitude * envelope * (np.sin(phase) + np.sin(phase * pair)) * .5
    rng = np.random.default_rng(1729)  # same excitation at every position and note
    signal += rng.standard_normal(n) * np.exp(-t / (.002 + .016 * mallet)) * mallet * .4
    attack = .0008 + soft ** 2 * .09
    signal *= np.minimum(t / attack, 1)
    signal = .62 * np.tanh(signal * (.65 + drive * 1.5))
    fade = min(int(.025 * SR), n)
    signal[-fade:] *= np.linspace(1, 0, fade)
    return signal.astype(np.float32)


def measure(signal):
    x = np.asarray(signal, dtype=float)
    # These one-shots already start/end at zero. A full-length Hann would erase
    # their attack and make short woody transients look falsely dark.
    # scipy.fft handles awkward lengths (a 2.5 s ring is ~110k samples) in a
    # few ms where numpy's takes ~16; results agree to ~1e-7 relative.
    power = np.abs(scipy.fft.rfft(x)) ** 2
    frequencies = scipy.fft.rfftfreq(len(x), 1 / SR)
    total = float(power.sum()) + 1e-20
    energy = x * x
    cumulative = np.cumsum(energy)
    end = int(np.searchsorted(cumulative, cumulative[-1] * .95)) / SR
    return {"peak": float(np.max(np.abs(x))),
            "rms": float(np.sqrt(energy.mean())),
            "centroid_hz": float(np.sum(frequencies * power) / total),
            "high_fraction": float(power[frequencies > 2000].sum() / total),
            "energy95_s": end,
            "crest": float(np.max(np.abs(x)) / (np.sqrt(energy.mean()) + 1e-12))}


def features(metrics):
    """Fixed feature scales, so adding a candidate doesn't change old distances."""
    return np.array([np.log2(max(metrics["centroid_hz"], 1) / 261.63) / 3,
                     metrics["high_fraction"] * 2,
                     np.log2(max(metrics["energy95_s"], .01) / .1) / 5,
                     np.log2(max(metrics["crest"], 1)) / 4])


def wav_bytes(signal):
    stream = io.BytesIO()
    with wave.open(stream, "wb") as output:
        output.setnchannels(1)
        output.setsampwidth(2)
        output.setframerate(SR)
        output.writeframes((np.clip(signal, -1, 1) * 32767).astype("<i2").tobytes())
    return stream.getvalue()


def encoded_sample(vector, midi):
    return base64.b64encode(wav_bytes(render(vector, midi))).decode("ascii")

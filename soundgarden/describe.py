"""A perceptual-ish descriptor for one-shot sounds: log-mel bands on a log-time grid.

The four scalar features in synth.features stay for compatibility; this module
adds a 24-band × 8-anchor grid of relative band levels. Time anchors are spaced
logarithmically from 5 ms to 1.5 s because struck sounds decay exponentially:
the interesting differences live in the first 50 ms and the last second alike.

The grid is level-invariant (dB relative to the loudest band-frame). Level and
transient sharpness travel in the scalar features. Euclidean distance on the
grid equals Euclidean distance on a full-length MFCC vector per anchor, since
the DCT is orthogonal; truncating to 13 coefficients would only smooth it.
"""
import numpy as np

from loam import SR
from .synth import features, measure, render, validate_vector

VERSION = "mel24x8/1"
NFFT, HOP = 2048, 256
BANDS, TIMES = 24, 8
LO_HZ, HI_HZ = 60.0, 12000.0
FLOOR_DB = -80.0
ANCHORS_S = 0.005 * 300.0 ** (np.arange(TIMES) / (TIMES - 1))
_RATIO = np.sqrt(300.0 ** (1 / (TIMES - 1)))
# Weight of the grid relative to the four scalar features inside embed(). Chosen
# so that a typical random plane endpoint moves both parts by similar amounts.
GRID_WEIGHT = 0.16
SENSITIVITY_STEP = 0.5  # logit units for the finite-difference Jacobian


def _mel(hz):
    return 2595.0 * np.log10(1.0 + np.asarray(hz, dtype=float) / 700.0)


def _hz(mel):
    return 700.0 * (10.0 ** (np.asarray(mel, dtype=float) / 2595.0) - 1.0)


def melbank(nfft=NFFT, bands=BANDS):
    """Triangular filters, unit area each, over the rfft grid."""
    edges = _hz(np.linspace(_mel(LO_HZ), _mel(HI_HZ), bands + 2))
    freqs = np.fft.rfftfreq(nfft, 1 / SR)
    bank = np.zeros((bands, len(freqs)))
    for b in range(bands):
        lo, mid, hi = edges[b:b + 3]
        bank[b] = np.clip(np.minimum((freqs - lo) / (mid - lo), (hi - freqs) / (hi - mid)), 0, None)
    return bank / np.maximum(bank.sum(axis=1, keepdims=True), 1e-12)


_BANK = melbank()


def frame_times(count, hop=HOP):
    return np.arange(count) * hop / SR


def mel_frames(signal, nfft=NFFT, hop=HOP):
    """Log-mel power per frame in dB, frames centered so frame 0 sits at t=0."""
    x = np.asarray(signal, dtype=float)
    pad = nfft // 2
    x = np.concatenate([np.zeros(pad), x, np.zeros(pad)])
    count = 1 + max(0, len(x) - nfft) // hop
    idx = np.arange(nfft)[None, :] + hop * np.arange(count)[:, None]
    frames = x[idx] * np.hanning(nfft)[None, :]
    power = np.abs(np.fft.rfft(frames, axis=1)) ** 2
    bands = power @ _BANK.T
    return 10 * np.log10(np.maximum(bands, 1e-20))


def grid_from_frames(db, hop=HOP):
    """Average dB frames inside each log-time anchor window, relative to the peak."""
    db = db - db.max()
    times = frame_times(len(db), hop)
    out = np.full((BANDS, TIMES), FLOOR_DB)
    for j, anchor in enumerate(ANCHORS_S):
        inside = (times >= anchor / _RATIO) & (times < anchor * _RATIO)
        if not inside.any():
            nearest = int(np.argmin(np.abs(times - anchor)))
            inside = np.zeros(len(times), dtype=bool)
            if times[nearest] < anchor * _RATIO:
                inside[nearest] = True
        if inside.any():
            out[:, j] = db[inside].mean(axis=0)
    return np.clip(out, FLOOR_DB, 0) / -FLOOR_DB  # in [-1, 0]


def describe(signal):
    """Descriptor dict: 192 relative levels in [-1, 0], row-major band × anchor."""
    return {"version": VERSION, "grid": grid_from_frames(mel_frames(signal)).ravel().tolist()}


def embed(metrics, grid):
    """Fixed-scale vector for distances; adding a candidate never changes old distances."""
    g = np.asarray(grid, dtype=float)
    if g.shape != (BANDS * TIMES,):
        raise ValueError("Descriptor grid has the wrong shape.")
    return np.concatenate([features(metrics), g * GRID_WEIGHT])


def analyze(vector, midi=60):
    """Render and measure at once: (audio, metrics, descriptor, embedding)."""
    audio = render(vector, midi)
    metrics = measure(audio)
    descriptor = describe(audio)
    return audio, metrics, descriptor, embed(metrics, descriptor["grid"])


def logits(vector):
    center = np.clip(np.asarray(vector, dtype=float), .001, .999)
    return np.log(center / (1 - center))


def from_logits(z):
    return 1 / (1 + np.exp(-np.asarray(z, dtype=float)))


def sensitivity(vector, midi=60, step=SENSITIVITY_STEP):
    """How far the embedding moves per logit unit along each recipe dimension.

    Forward differences: eleven renders. A heuristic Jacobian norm per column,
    not a perceptual model. Zero means the dimension is currently inaudible.
    """
    p = validate_vector(list(vector))
    base = analyze(p, midi)[3]
    z = logits(p)
    out = []
    for i in range(len(p)):
        moved = z.copy()
        moved[i] += step
        out.append(float(np.linalg.norm(analyze(from_logits(moved), midi)[3] - base) / step))
    return np.array(out)


def f0_midi(signal, lo_hz=55.0, hi_hz=1500.0):
    """Lowest strong spectral peak, as a MIDI note clamped to the render range."""
    x = np.asarray(signal, dtype=float)[:SR]
    if len(x) < 64 or not np.any(x):
        return 60
    n = 1 << int(np.ceil(np.log2(len(x) * 4)))
    power = np.abs(np.fft.rfft(x * np.hanning(len(x)), n)) ** 2
    freqs = np.fft.rfftfreq(n, 1 / SR)
    band = (freqs >= lo_hz) & (freqs <= hi_hz)
    p = np.where(band, power, 0)
    peaks = np.flatnonzero((p[1:-1] > p[:-2]) & (p[1:-1] >= p[2:]) & (p[1:-1] > p.max() * .1)) + 1
    if not len(peaks):
        return 60
    f = float(freqs[peaks[0]])
    return int(np.clip(round(69 + 12 * np.log2(f / 440)), 48, 84))

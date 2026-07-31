"""Granular clouds — a source becomes weather.

Chop any signal into short Hann-windowed grains, scatter them in
time (wrapped — clouds are loop-safe by construction), transpose
each by resampling, spray across the stereo field. High density +
long grains = time-smeared freeze; short grains + wide pitch set =
glitter. Feed a +12 cloud into reverb_loop and you have shimmer
reverb (the Eno/Lanois trick).
"""

import numpy as np

from . import SR, stereo


def cloud(src: np.ndarray, out_s: float, density: float = 25.0,
        grain_s: float = 0.09, pitches=(0.0,), pan_spread: float = 0.7,
        jitter: float = 1.0, gain: float = 1.0,
        seed: int = 0) -> np.ndarray:
    """Scatter grains of mono `src` over an out_s-long stereo loop.
    density = grains/sec; pitches = semitone choices per grain."""
    if src.ndim == 2:
        src = src.mean(axis=1)
    n_out = int(out_s * SR)
    out = np.zeros((n_out, 2))
    rng = np.random.default_rng(seed)
    count = int(density * out_s)
    gn = int(grain_s * SR)
    win = np.hanning(gn)
    for _ in range(count):
        at = rng.uniform(0, out_s) if jitter >= 1.0 else None
        if at is None:
            at = (rng.integers(0, max(int(out_s / grain_s), 1))
                    * grain_s + rng.uniform(0, grain_s * jitter))
        st = rng.integers(0, max(len(src) - 2, 1))
        rate = 2.0 ** (float(rng.choice(pitches)) / 12.0)
        pos = (st + np.arange(gn) * rate) % (len(src) - 1)
        g = np.interp(pos, np.arange(len(src)), src) * win
        ch = stereo(g, float(rng.uniform(-pan_spread, pan_spread)))
        idx = (int(at * SR) + np.arange(gn)) % n_out
        np.add.at(out, idx, ch)
    peak = np.max(np.abs(out)) + 1e-12
    return out * (gain / peak) * min(peak, 1.0)

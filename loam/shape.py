"""Nonlinear color — waveshapers and degraders.

- wavefold: the West-Coast move. Instead of clipping peaks off,
  REFLECT them back into range (triangle fold). A sine pushed into
  a folder blooms odd+even harmonics that sweep as the drive
  moves — animate `drive` for the classic Buchla bloom.
- chebyshev: Chebyshev polynomials T_k turn a unit sine into its
  k-th harmonic EXACTLY, so a weight list is literally an additive
  recipe applied by distortion. On complex signals it's a related
  but wilder animal (intermodulation).
- bitcrush / downsample: quantization grit and aliasing sheen.
- tape_sat: tanh with pre-emphasis — highs saturate first, like
  ferric oxide does.

All are memoryless (or FIR-warmed) — loop-safe as long as the
input is a loop.
"""

import numpy as np
from scipy.signal import lfilter

from . import SR


def wavefold(x: np.ndarray, drive=2.5, sym: float = 0.0) -> np.ndarray:
    """Triangle-reflect fold. `drive` may be a scalar or an array
    (per-sample — animate it). `sym` biases the fold asymmetric
    (even harmonics)."""
    y = (x * drive + sym + 1.0) * 0.25
    y = 4.0 * np.abs(y - np.floor(y + 0.5)) - 1.0
    return y


def chebyshev(x: np.ndarray, weights) -> np.ndarray:
    """Harmonic recipe by distortion: weights[k] drives harmonic
    k+1 (weights[0] = fundamental T1, weights[1] = T2, ...). On a
    unit sine the result is EXACTLY that additive mix; on complex
    signals, intermodulation. x must live in [-1, 1]."""
    x = np.clip(x, -1.0, 1.0)
    tk_prev = np.ones_like(x)
    tk = x
    out = weights[0] * tk if len(weights) > 0 else np.zeros_like(x)
    for w in weights[1:]:
        tk_prev, tk = tk, 2.0 * x * tk - tk_prev
        if w != 0.0:
            out += w * tk
    return out


def bitcrush(x: np.ndarray, bits: float = 8.0,
        down: int = 1) -> np.ndarray:
    """Quantize to `bits`; hold every `down`-th sample (aliasing)."""
    q = 2.0 ** (bits - 1)
    y = np.round(x * q) / q
    if down > 1:
        idx = (np.arange(len(y)) // down) * down
        y = y[idx]
    return y


def tape_sat(x: np.ndarray, drive: float = 2.0,
        emph_hz: float = 1800.0) -> np.ndarray:
    """Pre-emphasized tanh: boost highs, saturate, cut them back.
    Highs distort first; lows stay round."""
    c = np.exp(-2.0 * np.pi * emph_hz / SR)
    lo = lfilter([1 - c], [1, -c], x, axis=0)
    hi = x - lo
    y = np.tanh((lo + hi * 2.5) * drive) / np.tanh(drive)
    lo2 = lfilter([1 - c], [1, -c], y, axis=0)
    return lo2 + (y - lo2) * 0.4

"""Sidebands — ring modulation and the Bode frequency shifter.

Frequency shifting is NOT pitch shifting: every partial moves by
the same NUMBER OF HZ, not the same ratio. A harmonic sound
(f, 2f, 3f...) becomes inharmonic (f+s, 2f+s, 3f+s...) — harps
turn to bells, voices to ghosts. Ring modulation is its two-sided
cousin: multiply by a sine and every partial splits into +-f
sidebands.

Implementation is seam-craft-native: the analytic signal comes
from an FFT Hilbert transform, which is CIRCULAR by definition,
and the shift frequency is quantized to whole cycles per loop —
so a shifted loop is still a perfect loop.

barber() is the classic abuse: a feedback delay whose loop
contains a small frequency shift — every echo arrives a few Hz
higher (or lower) than the last, an endless staircase. Shepard's
barberpole, from three lines of DSP.
"""

import numpy as np
from scipy.signal import butter, sosfilt

from . import SR


def _analytic(x: np.ndarray) -> np.ndarray:
    """Circular Hilbert: zero the negative frequencies."""
    n = len(x)
    X = np.fft.fft(x)
    h = np.zeros(n)
    h[0] = 1.0
    if n % 2 == 0:
        h[n // 2] = 1.0
        h[1: n // 2] = 2.0
    else:
        h[1: (n + 1) // 2] = 2.0
    return np.fft.ifft(X * h)


def freq_shift(x: np.ndarray, shift_hz: float,
        loop_s=None) -> np.ndarray:
    """Shift every partial by shift_hz (negative shifts down).
    Mono or stereo; loop_s quantizes the shift for seamlessness."""
    if loop_s is not None:
        shift_hz = round(shift_hz * loop_s) / loop_s
    if x.ndim == 2:
        return np.stack([freq_shift(x[:, 0], shift_hz, None),
                freq_shift(x[:, 1], shift_hz, None)], axis=1)
    n = len(x)
    t = np.arange(n) / SR
    a = _analytic(x)
    return np.real(a * np.exp(2j * np.pi * shift_hz * t))


def ring_mod(x: np.ndarray, f_hz: float, loop_s=None,
        mix: float = 1.0) -> np.ndarray:
    """Multiply by a sine: partials split into +-f_hz sidebands."""
    if loop_s is not None:
        f_hz = round(f_hz * loop_s) / loop_s
    n = len(x)
    car = np.sin(2 * np.pi * f_hz * np.arange(n) / SR)
    wet = x * (car[:, None] if x.ndim == 2 else car)
    return x * (1.0 - mix) + wet * mix


def barber(x: np.ndarray, loop_s: float, shift_hz: float = 5.0,
        delay_s: float = 0.24, feedback: float = 0.78,
        damp_hz: float = 5200.0, mix: float = 0.5) -> np.ndarray:
    """The endless staircase: each echo returns shift_hz higher
    (negative = an endless descent). Circular in time AND spectrum."""
    if x.ndim == 1:
        x = np.stack([x, x], axis=1)
    n = len(x)
    pos = (np.arange(n) - delay_s * SR) % n
    c = np.exp(-2.0 * np.pi * damp_hz / SR)
    from scipy.signal import lfilter
    e = x.mean(axis=1)
    wet = np.zeros((n, 2))
    g = 1.0
    for k in range(24):
        e = np.interp(pos, np.arange(n), e, period=n)
        e = freq_shift(e, shift_hz, loop_s)
        warm = e[-SR:]
        e = lfilter([1 - c], [1, -c], np.concatenate([warm, e]))[SR:]
        g *= feedback
        side = k % 2
        wet[:, side] += e * g * 0.85
        wet[:, 1 - side] += e * g * 0.45
        if g < 2e-3:
            break
    wet *= np.max(np.abs(x)) / (np.max(np.abs(wet)) + 1e-12)
    return x * (1.0 - mix) + wet * mix

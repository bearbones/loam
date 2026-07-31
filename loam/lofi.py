"""The lo-fi channel — age as an effect.

gramophone() and worn_tape() push a signal through the physics of
a degraded medium:

- wow & flutter: slow (~0.8 Hz) and fast (~7 Hz) pitch wobble,
  applied by resampling along a warped time map (cycle-quantized,
  so loops survive).
- crackle: Poisson-timed impulses, each a tiny filtered snap with
  its own brightness — the big rare pops ride over a fine dust.
- hiss: shaped surface noise.
- dropouts: brief gain dips with soft edges (oxide shed).
- hum: 60 Hz + harmonics, faint.
- bandwidth: the funnel — steep band edges (78s live ~200-4500 Hz),
  plus a resonant bump near the horn's throat for the gramophone.

All parameters are exposed; the presets are opinions.
"""

import numpy as np
from scipy.signal import butter, sosfilt

from . import SR


def _warp(x: np.ndarray, loop_s, wow_hz: float, wow_depth: float,
        flut_hz: float, flut_depth: float, seed: int) -> np.ndarray:
    """Depths are PITCH fractions (0.003 = 0.3% = ~5 cents peak).
    Position amplitude = depth/(2*pi*rate), so a fast flutter does
    NOT swing harder than a slow wow (first draft specified
    position directly and the flutter dominated 3:1)."""
    n = len(x)
    t = np.arange(n) / SR

    def q(f):
        return f if loop_s is None else max(round(f * loop_s), 1) / loop_s

    wq, fq = q(wow_hz), q(flut_hz)
    dev = wow_depth / (2 * np.pi * wq) * np.sin(2 * np.pi * wq * t) \
        + flut_depth / (2 * np.pi * fq) \
        * np.sin(2 * np.pi * fq * t + 1.3)
    pos = (np.arange(n) + dev * SR) % n
    if x.ndim == 2:
        return np.stack([np.interp(pos, np.arange(n), x[:, 0], period=n),
                np.interp(pos, np.arange(n), x[:, 1], period=n)], axis=1)
    return np.interp(pos, np.arange(n), x, period=n)


def _crackle(n: int, rate_hz: float, big_rate_hz: float,
        seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    out = np.zeros(n)
    for rate, amp_lo, amp_hi, dur_s in [
            (rate_hz, 0.004, 0.02, 0.0012),
            (big_rate_hz, 0.05, 0.22, 0.004)]:
        count = int(rate * n / SR)
        for _ in range(count):
            at = rng.integers(0, n)
            ln = max(int(dur_s * SR * rng.uniform(0.5, 1.5)), 4)
            snap = rng.standard_normal(ln) \
                * np.exp(-np.arange(ln) / (ln * 0.25))
            amp = rng.uniform(amp_lo, amp_hi)
            end = min(at + ln, n)
            out[at:end] += snap[: end - at] * amp
    sos = butter(1, 900, btype="high", fs=SR, output="sos")
    return sosfilt(sos, out)


def gramophone(x: np.ndarray, loop_s=None, wow_depth: float = 0.006,
        crackle_rate: float = 60.0, pop_rate: float = 1.2,
        hiss: float = 0.006, hum: float = 0.0022,
        dropout_rate: float = 0.10, band=(240.0, 4200.0),
        horn_hz: float = 900.0, drive: float = 1.5,
        seed: int = 0) -> np.ndarray:
    """The full 78: mono-ized, horn-resonant, crackling."""
    rng = np.random.default_rng(seed + 1)
    if x.ndim == 2:
        x = x.mean(axis=1)
    n = len(x)
    y = _warp(x, loop_s, 0.8, wow_depth, 6.8, wow_depth * 0.3, seed)
    sos_b = butter(3, band, btype="band", fs=SR, output="sos")
    y = sosfilt(sos_b, y)
    sos_h = butter(2, [horn_hz * 0.7, horn_hz * 1.4], btype="band",
            fs=SR, output="sos")
    y = y + sosfilt(sos_h, y) * 0.6            # the horn's throat
    y = np.tanh(y * drive) / np.tanh(drive)
    # dropouts
    n_drop = int(dropout_rate * n / SR) + 1
    env = np.ones(n)
    for _ in range(n_drop):
        at = rng.integers(0, n)
        ln = int(rng.uniform(0.02, 0.12) * SR)
        end = min(at + ln, n)
        dip = 1.0 - rng.uniform(0.4, 0.85) \
            * np.sin(np.pi * np.arange(end - at) / max(end - at, 1))
        env[at:end] *= dip
    y *= env
    y = y + _crackle(n, crackle_rate, pop_rate, seed + 2)
    sos_n = butter(2, [800, 6000], btype="band", fs=SR, output="sos")
    y = y + sosfilt(sos_n, rng.standard_normal(n)) * hiss
    t = np.arange(n) / SR
    y = y + hum * (np.sin(2 * np.pi * 60 * t)
            + 0.5 * np.sin(2 * np.pi * 180 * t))
    return np.stack([y, y], axis=1)


def worn_tape(x: np.ndarray, loop_s=None, wow_depth: float = 0.0035,
        hiss: float = 0.004, drive: float = 1.8,
        seed: int = 0) -> np.ndarray:
    """Gentler: stereo survives, wider band, tape squash, no pops."""
    if x.ndim == 1:
        x = np.stack([x, x], axis=1)
    n = len(x)
    y = _warp(x, loop_s, 0.5, wow_depth, 8.5, wow_depth * 0.4, seed)
    sos_b = butter(2, [45.0, 11000.0], btype="band", fs=SR, output="sos")
    y = sosfilt(sos_b, y, axis=0)
    y = np.tanh(y * drive) / np.tanh(drive)
    rng = np.random.default_rng(seed + 3)
    sos_n = butter(2, [1200, 9000], btype="band", fs=SR, output="sos")
    y += sosfilt(sos_n, rng.standard_normal((n, 2)), axis=0) * hiss
    return y

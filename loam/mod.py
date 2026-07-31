"""Modulation — the effects that swim.

- chorus: N voices reading a circular delay at slowly-wobbling
  offsets, each voice its own LFO phase per channel. Turns a mono
  source into an ensemble; the cheapest honest stereo there is.
- flanger: one very short wobbling delay (0.5..5 ms) mixed back
  with feedback — a comb whose teeth sweep. Feedback is unrolled
  circular passes (like the tape echo).
- phaser: cascaded first-order allpasses whose coefficient rides
  the LFO; notches where the phase wraps. Time-varying recursion
  is processed in 128-sample blocks with piecewise-constant
  coefficients (the LFO moves ~0.001/block at 0.5 Hz — inaudible
  staircase, vectorizable).

Loop-safety: every LFO is quantized to whole cycles per loop
(pass loop_s); delay reads are modulo the buffer.
"""

import numpy as np
from scipy.signal import lfilter

from . import SR


def _lfo(n: int, loop_s: float, rate_hz: float,
        phase: float) -> np.ndarray:
    t = np.arange(n) / SR
    rq = max(round(rate_hz * loop_s), 1) / loop_s
    return np.sin(2 * np.pi * rq * t + phase)


def _read(x: np.ndarray, delay_smp: np.ndarray) -> np.ndarray:
    n = len(x)
    pos = (np.arange(n) - delay_smp) % n
    return np.interp(pos, np.arange(n), x, period=n)


def chorus(x: np.ndarray, loop_s: float, voices: int = 3,
        base_ms: float = 18.0, depth_ms: float = 5.0,
        rate_hz: float = 0.55, mix: float = 0.5) -> np.ndarray:
    """Mono/stereo in -> ensemble stereo out."""
    mono = x.mean(axis=1) if x.ndim == 2 else x
    n = len(mono)
    wet = np.zeros((n, 2))
    for v in range(voices):
        for ch in range(2):
            ph = 2 * np.pi * (v / voices + 0.31 * ch + 0.13 * v)
            d = (base_ms + depth_ms * _lfo(n, loop_s,
                    rate_hz * (1.0 + 0.17 * v), ph)) * 1e-3 * SR
            wet[:, ch] += _read(mono, d)
    wet /= voices
    dry = x if x.ndim == 2 else np.stack([mono, mono], axis=1)
    return dry * (1.0 - mix) + wet * mix


def flanger(x: np.ndarray, loop_s: float, base_ms: float = 1.6,
        depth_ms: float = 1.2, rate_hz: float = 0.22,
        feedback: float = 0.55, mix: float = 0.5) -> np.ndarray:
    """The jet plane. Stereo-preserving; channels get opposite
    LFO phase."""
    if x.ndim == 1:
        x = np.stack([x, x], axis=1)
    n = len(x)
    out = np.zeros_like(x)
    for ch in range(2):
        d = (base_ms + depth_ms * _lfo(n, loop_s, rate_hz,
                np.pi * ch)) * 1e-3 * SR
        e = x[:, ch].copy()
        wet = np.zeros(n)
        g = 1.0
        for _ in range(10):
            e = _read(e, d)
            wet += e * g
            g *= feedback
            if g < 1e-3:
                break
        out[:, ch] = x[:, ch] * (1.0 - mix) + wet * mix \
            / (1.0 / (1.0 - feedback))
    return out


def phaser(x: np.ndarray, loop_s: float, stages: int = 6,
        rate_hz: float = 0.35, f_lo: float = 350.0,
        f_hi: float = 2800.0, feedback: float = 0.3,
        mix: float = 0.5) -> np.ndarray:
    """Cascaded time-varying allpasses; notch count = stages/2."""
    if x.ndim == 1:
        x = np.stack([x, x], axis=1)
    n = len(x)
    out = np.zeros_like(x)
    blk = 128
    for ch in range(2):
        lfo = 0.5 + 0.5 * _lfo(n, loop_s, rate_hz, np.pi * ch)
        fc = f_lo * (f_hi / f_lo) ** lfo          # exp sweep
        coef = (1.0 - np.tan(np.pi * fc / SR)) \
            / (1.0 + np.tan(np.pi * fc / SR))
        sig = x[:, ch]
        wet = np.zeros(n)
        zi = np.zeros(stages)
        fb = np.zeros(blk)
        i = 0
        while i < n:
            j = min(i + blk, n)
            a = float(coef[(i + j) // 2])
            seg = sig[i:j] + feedback * fb[: j - i]
            for s in range(stages):
                seg, z = lfilter([a, -1.0], [1.0, -a], seg,
                        zi=np.array([zi[s]]))
                zi[s] = z[0]
            wet[i:j] = seg
            fb = seg
            i = j
        out[:, ch] = x[:, ch] * (1.0 - mix) + wet * mix
    return out

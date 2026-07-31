"""Virtual analog — oscillators with edges, and the ladder.

- polyBLEP saw/pulse (Valimaki): a naive digital saw aliases —
  its discontinuity contains energy above Nyquist that folds back
  as non-harmonic garbage. polyBLEP subtracts a 2-sample
  polynomial correction at each discontinuity: the edge stays
  crisp, the folding drops ~30 dB.
- supersaw: 7 detuned polyBLEP saws, center + 3 pairs (the
  JP-8000 recipe), phase-scattered so the ensemble doesn't comb.
- ladder: Huovilainen-style Moog ladder — four cascaded tanh
  one-poles, feedback k*resonance from the last stage. Nonlinear
  and recursive per sample (scalar loop, ~0.5s per rendered
  second — budget accordingly). Self-oscillates above res ~1.0
  like the hardware.

Loop-safety: oscillators take loop_s and quantize their frequency
to whole cycles per loop; phase accumulates mod 1.
"""

import numpy as np

from . import SR


def _q(f: float, loop_s) -> float:
    if loop_s is None:
        return f
    return max(round(f * loop_s), 1) / loop_s


def _polyblep(ph: np.ndarray, dt: float) -> np.ndarray:
    """Band-limiting correction at phase wrap points."""
    c = np.zeros_like(ph)
    m = ph < dt
    t = ph[m] / dt
    c[m] = t + t - t * t - 1.0
    m2 = ph > 1.0 - dt
    t2 = (ph[m2] - 1.0) / dt
    c[m2] = t2 * t2 + t2 + t2 + 1.0
    return c


def saw(f: float, dur: float, loop_s=None, phase: float = 0.0) -> np.ndarray:
    fq = _q(f, loop_s)
    n = int(dur * SR)
    dt = fq / SR
    ph = (phase + dt * np.arange(n)) % 1.0
    return 2.0 * ph - 1.0 - _polyblep(ph, dt)


def pulse(f: float, dur: float, width: float = 0.5, loop_s=None,
        phase: float = 0.0) -> np.ndarray:
    fq = _q(f, loop_s)
    n = int(dur * SR)
    dt = fq / SR
    ph = (phase + dt * np.arange(n)) % 1.0
    ph2 = (ph + (1.0 - width)) % 1.0
    y = np.where(ph < width, 1.0, -1.0).astype(float)
    return y + _polyblep(ph, dt) - _polyblep(ph2, dt)


def supersaw(f: float, dur: float, detune_cents: float = 12.0,
        loop_s=None, seed: int = 0) -> np.ndarray:
    """7 detuned saws, stereo. Center dry, pairs panned out."""
    rng = np.random.default_rng(seed)
    n = int(dur * SR)
    out = np.zeros((n, 2))
    offs = [0.0, -1.0, 1.0, -0.55, 0.55, -0.24, 0.24]
    for k, o in enumerate(offs):
        fk = f * 2.0 ** (o * detune_cents / 1200.0)
        v = saw(fk, dur, loop_s, phase=float(rng.uniform(0, 1)))
        if k == 0:
            # center voice quiet: at equal gain it correlates the
            # channels back up (measured 0.81 -> 0.55 by muting it)
            out[:, 0] += v * 0.28
            out[:, 1] += v * 0.28
        else:
            side = k % 2
            out[:, side] += v * 0.46
            out[:, 1 - side] += v * 0.07
    return out / 2.0


def ladder(x: np.ndarray, cutoff_hz, res: float = 0.5,
        drive: float = 1.0) -> np.ndarray:
    """Moog ladder, Huovilainen-style. cutoff_hz: scalar or
    per-sample array (sweep it). res 0..~1.0; >1 self-oscillates.
    Mono in, mono out."""
    n = len(x)
    fc = np.broadcast_to(np.asarray(cutoff_hz, dtype=float), (n,))
    g = 1.0 - np.exp(-2.0 * np.pi * np.clip(fc, 10.0, SR * 0.45) / SR)
    k = 4.0 * res
    s1 = s2 = s3 = s4 = 0.0
    out = np.empty(n)
    for i in range(n):
        gi = g[i]
        u = np.tanh(x[i] * drive - k * s4)
        s1 += gi * (u - s1)
        s2 += gi * (np.tanh(s1) - s2)
        s3 += gi * (np.tanh(s2) - s3)
        s4 += gi * (np.tanh(s3) - s4)
        out[i] = s4
    return out

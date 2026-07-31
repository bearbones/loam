"""Karplus-Strong plucked strings, with the Jaffe-Smith refinements.

The original trick (Karplus & Strong 1983): fill a delay line with
noise, then replay it forever through a gentle lowpass — the noise
converges to the delay line's resonance and rings like a string.
Jaffe & Smith (1983) turned the toy into an instrument:

- pick-position comb: subtract a delayed copy of the excitation
  (delay = pick * period) — plucking near the bridge notches the
  spectrum exactly like a real pluck does.
- damping blend: how much of the two-point average is applied per
  trip controls how fast brightness dies relative to energy.
- fractional delay: interpolated reads tune between integer sample
  periods (a 100-vs-100.2-sample period is 4 cents — chords beat
  without this).

Implementation note: y[n] references nothing newer than n - P, so
the recursion runs in period-sized numpy blocks — fast enough to
strum with.
"""

import numpy as np

from . import SR


def pluck(f0: float, dur: float, amp: float = 1.0, t60: float = 2.5,
        damp: float = 0.35, pick: float = 0.2, soft: int = 0,
        seed: int = 0) -> np.ndarray:
    """One plucked note. damp 0..1 = HF loss per trip (nylon ~0.5,
    steel ~0.2); pick = pluck point 0..0.5 of the string; soft =
    extra moving-average passes on the excitation (fingertip vs
    plectrum)."""
    n = int(dur * SR)
    pf = SR / f0
    pi_ = int(pf)
    frac = pf - pi_
    rho = 10.0 ** (-3.0 * (pf / SR) / t60)   # loop gain for this t60

    rng = np.random.default_rng(seed)
    ex = rng.standard_normal(pi_ + 2)
    if pick > 0.0:
        d = max(int(round(pick * pi_)), 1)
        ex = ex - np.concatenate([np.zeros(d), ex[:-d]])
    for _ in range(soft):
        ex = np.convolve(ex, [0.5, 0.5], mode="same")
    ex /= np.max(np.abs(ex)) + 1e-12

    y = np.zeros(n + pi_ + 2)
    y[: pi_ + 2] = ex
    blk = max(pi_ - 2, 8)
    i = pi_ + 2
    while i < len(y):
        j = min(i + blk, len(y))
        idx = np.arange(i, j)
        s0 = (1 - frac) * y[idx - pi_] + frac * y[idx - pi_ - 1]
        s1 = (1 - frac) * y[idx - pi_ - 1] + frac * y[idx - pi_ - 2]
        y[i:j] = rho * ((1 - 0.5 * damp) * s0 + 0.5 * damp * s1)
        i = j
    out = y[pi_ + 2:]
    r = int(min(0.05, dur * 0.1) * SR)
    if r > 0:
        out[-r:] *= np.linspace(1, 0, r)
    return out * amp / (np.max(np.abs(out)) + 1e-12) * 0.9


def strum(notes, dur: float, amp: float = 1.0, spread_s: float = 0.018,
        seed: int = 0, **kw) -> np.ndarray:
    """Chord with per-string onset spread. Returns mono of length
    dur + spread."""
    rng = np.random.default_rng(seed)
    n = int((dur + spread_s * len(notes)) * SR)
    out = np.zeros(n)
    for k, midi in enumerate(notes):
        f = 440.0 * 2.0 ** ((midi - 69) / 12.0)
        v = pluck(f, dur, amp / max(len(notes) ** 0.5, 1), seed=seed + k,
                **kw)
        at = int(k * spread_s * SR + rng.uniform(0, 0.004) * SR)
        out[at:at + len(v)] += v[: max(0, n - at)]
    return out

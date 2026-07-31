"""Dynamics — the invisible hand on the fader.

- env_follow: rectify -> one-pole attack/release. The primitive
  everything else here is built from. Circular-warm option so
  loops don't pump at the seam.
- compress: feed-forward log-domain compressor. Slope above
  threshold = 1/ratio, by construction — and by measurement.
- duck: sidechain — a key signal pushes the payload down. The
  kick-duck loam songs kept hand-rolling, now with proper
  attack/release instead of a stamped exponential.
- transient: fast-envelope minus slow-envelope shaper; positive
  difference IS the attack, so gain it up or down independently
  of sustain.
- limiter: lookahead brickwall — running max over the lookahead
  window, smoothed, never exceeded.
"""

import numpy as np
from scipy.signal import lfilter

from . import SR


def env_follow(x: np.ndarray, attack_ms: float = 5.0,
        release_ms: float = 80.0, circular: bool = False) -> np.ndarray:
    """Envelope of |mono|; separate attack/release poles."""
    if x.ndim == 2:
        x = np.max(np.abs(x), axis=1)
    else:
        x = np.abs(x)
    ca = np.exp(-1.0 / (attack_ms * 1e-3 * SR))
    cr = np.exp(-1.0 / (release_ms * 1e-3 * SR))
    n = len(x)
    src = np.concatenate([x[-SR:], x]) if circular else x
    env = np.empty(len(src))
    e = 0.0
    for i in range(len(src)):        # scalar, but simple + correct;
        v = src[i]                   # ~0.2s/loop-second, acceptable
        c = ca if v > e else cr
        e = c * e + (1.0 - c) * v
        env[i] = e
    return env[-n:]


def _db(v):
    return 20.0 * np.log10(np.maximum(v, 1e-9))


def compress(x: np.ndarray, thresh_db: float = -18.0,
        ratio: float = 4.0, attack_ms: float = 8.0,
        release_ms: float = 120.0, makeup_db: float = 0.0,
        knee_db: float = 4.0, circular: bool = False) -> np.ndarray:
    """Feed-forward compressor; soft knee; gain computed in dB."""
    env = env_follow(x, attack_ms, release_ms, circular)
    lev = _db(env)
    over = lev - thresh_db
    if knee_db > 0.0:
        soft = np.clip((over + knee_db / 2) / knee_db, 0.0, 1.0)
        over_eff = over * soft * soft * (3 - 2 * soft) \
            * (over > -knee_db / 2)
    else:
        over_eff = np.maximum(over, 0.0)
    gr_db = -over_eff * (1.0 - 1.0 / ratio)
    g = 10.0 ** ((gr_db + makeup_db) / 20.0)
    return x * (g[:, None] if x.ndim == 2 else g)


def duck(x: np.ndarray, key: np.ndarray, amount_db: float = 9.0,
        attack_ms: float = 4.0, release_ms: float = 140.0,
        thresh_db: float = -30.0,
        circular: bool = True) -> np.ndarray:
    """Sidechain: push x down by up to amount_db while key is hot."""
    env = env_follow(key, attack_ms, release_ms, circular)
    lev = _db(env)
    depth = np.clip((lev - thresh_db) / 18.0, 0.0, 1.0)
    g = 10.0 ** (-amount_db * depth / 20.0)
    return x * (g[:, None] if x.ndim == 2 else g)


def transient(x: np.ndarray, attack_db: float = 6.0,
        sustain_db: float = 0.0) -> np.ndarray:
    """Shape attacks apart from sustains (SPL-style differential
    envelope)."""
    fast = env_follow(x, 0.6, 40.0)
    slow = env_follow(x, 18.0, 40.0)
    att = np.clip((fast - slow) / (np.maximum(slow, 1e-6)), 0.0, 3.0) / 3.0
    g_db = attack_db * att + sustain_db * (1.0 - att)
    g = 10.0 ** (g_db / 20.0)
    return x * (g[:, None] if x.ndim == 2 else g)


def limiter(x: np.ndarray, ceiling: float = 0.95,
        lookahead_ms: float = 3.0,
        release_ms: float = 60.0) -> np.ndarray:
    """Brickwall: gain from smoothed running max over lookahead."""
    from scipy.ndimage import maximum_filter1d
    la = max(int(lookahead_ms * 1e-3 * SR), 1)
    mono = np.max(np.abs(x), axis=1) if x.ndim == 2 else np.abs(x)
    n = len(mono)
    # sliding max over [i, i+la) — origin shifts the window forward
    peak = maximum_filter1d(mono, la, mode="constant",
            origin=-(la // 2))
    need = np.minimum(ceiling / np.maximum(peak, 1e-9), 1.0)
    cr = np.exp(-1.0 / (release_ms * 1e-3 * SR))
    g = np.empty(n)
    e = 1.0
    for i in range(n):
        v = need[i]
        e = v if v < e else cr * e + (1.0 - cr) * v
        g[i] = e
    out = x * (g[:, None] if x.ndim == 2 else g)
    return np.clip(out, -ceiling, ceiling)
"""Simulated drum samples — the classic analog recipes.

These are the documented circuits, not recordings: the TR-808 hat
is six square oscillators (a deliberately inharmonic cluster)
through a high bandpass; the cowbell is two squares at ~540+800 Hz;
the clap is three fast noise bursts riding a fourth with a longer
tail; the kick is a self-FM'd sine with a pitch drop; the snare is
two detuned tones (~180/330 Hz) plus a snappy noise band. Congas
and toms are pitch-dropping sines with softer skins.

Every function returns mono; pan with loam.stereo. Deterministic
where noise is involved (seed arg).
"""

import numpy as np
from scipy.signal import butter, sosfilt

from . import SR, ad_env


def _noise(n: int, seed: int) -> np.ndarray:
    return np.random.default_rng(seed).standard_normal(n)


def _sq(f: float, tt: np.ndarray) -> np.ndarray:
    return np.sign(np.sin(2 * np.pi * f * tt))


def kick(dur: float = 0.42, f0: float = 160.0, f1: float = 44.0,
        drop: float = 14.0, click: float = 0.4, drive: float = 2.2,
        amp: float = 1.0, seed: int = 0) -> np.ndarray:
    """Pitch-drop sine kick. drop = decay rate of the sweep;
    click = beater transient level."""
    n = int(dur * SR)
    tt = np.arange(n) / SR
    freq = f1 + (f0 - f1) * np.exp(-tt * drop)
    ph = 2 * np.pi * np.cumsum(freq) / SR
    m = np.tanh(np.sin(ph) * drive) * np.exp(-tt * (3.2 / dur))
    if click > 0:
        cn = int(0.004 * SR)
        sos = butter(2, [700, 3800], btype="band", fs=SR, output="sos")
        ck = sosfilt(sos, _noise(cn * 4, seed))[:cn]
        m[:cn] += ck / (np.max(np.abs(ck)) + 1e-12) \
            * np.linspace(1, 0, cn) * click
    return m * amp / (np.max(np.abs(m)) + 1e-12) * 0.95


def snare(dur: float = 0.24, tone_hz: float = 185.0, snap: float = 1.0,
        amp: float = 1.0, seed: int = 1) -> np.ndarray:
    """Two drum-head tones + the snare-wire noise band."""
    n = int(dur * SR)
    tt = np.arange(n) / SR
    m = 0.5 * np.sin(2 * np.pi * tone_hz * tt) \
        + 0.35 * np.sin(2 * np.pi * tone_hz * 1.78 * tt)
    m *= np.exp(-tt * 24.0)
    sos = butter(2, [1400, 8200], btype="band", fs=SR, output="sos")
    wires = sosfilt(sos, _noise(n, seed)) * np.exp(-tt * 17.0) * snap
    m = m + wires * 0.9
    return m * amp / (np.max(np.abs(m)) + 1e-12) * 0.9


def hat(dur: float = 0.08, open_: bool = False, amp: float = 1.0,
        seed: int = 2) -> np.ndarray:
    """808-style: six squares, inharmonic cluster, high bandpass."""
    n = int((0.45 if open_ else dur) * SR)
    tt = np.arange(n) / SR
    m = np.zeros(n)
    for f in (263.7, 400.0, 421.0, 474.0, 587.0, 845.0):
        m += _sq(f * 8.02, tt)          # cluster up in the 2-7k zone
    sos = butter(2, [5200, 14000], btype="band", fs=SR, output="sos")
    m = sosfilt(sos, m + _noise(n, seed) * 0.6)
    rate = 9.0 if open_ else 55.0
    return m * np.exp(-tt * rate) * amp \
        / (np.max(np.abs(m)) + 1e-12) * 0.8


def clap(amp: float = 1.0, seed: int = 3) -> np.ndarray:
    """Three fast bursts then the room burst — the 808 spec."""
    n = int(0.30 * SR)
    tt = np.arange(n) / SR
    sos = butter(2, [900, 5800], btype="band", fs=SR, output="sos")
    nz = sosfilt(sos, _noise(n, seed))
    env = np.zeros(n)
    for k, (at, g, rate) in enumerate([(0.0, 1.0, 120.0),
            (0.011, 0.85, 120.0), (0.022, 0.7, 120.0),
            (0.033, 0.9, 14.0)]):
        i0 = int(at * SR)
        seg = np.exp(-(tt[: n - i0]) * rate) * g
        env[i0:] = np.maximum(env[i0:], seg)
    m = nz * env
    return m * amp / (np.max(np.abs(m)) + 1e-12) * 0.85


def tom(f0: float = 110.0, dur: float = 0.5, amp: float = 1.0,
        seed: int = 4) -> np.ndarray:
    n = int(dur * SR)
    tt = np.arange(n) / SR
    freq = f0 * (1.0 + 0.5 * np.exp(-tt * 18.0))
    ph = 2 * np.pi * np.cumsum(freq) / SR
    m = np.sin(ph) * np.exp(-tt * (4.5 / dur))
    sos = butter(2, [500, 3200], btype="band", fs=SR, output="sos")
    skin = sosfilt(sos, _noise(n, seed)) * np.exp(-tt * 90.0) * 0.35
    m = np.tanh((m + skin) * 1.25)
    return m * amp / (np.max(np.abs(m)) + 1e-12) * 0.9


def conga(f0: float = 210.0, slap: float = 0.25, amp: float = 1.0,
        seed: int = 5) -> np.ndarray:
    n = int(0.22 * SR)
    tt = np.arange(n) / SR
    freq = f0 * (1.0 + 0.25 * np.exp(-tt * 60.0))
    ph = 2 * np.pi * np.cumsum(freq) / SR
    m = np.sin(ph) * np.exp(-tt * 26.0)
    if slap > 0:
        sn = int(0.006 * SR)
        sos = butter(2, [1200, 5200], btype="band", fs=SR, output="sos")
        sl = sosfilt(sos, _noise(sn * 4, seed))[:sn]
        m[:sn] += sl / (np.max(np.abs(sl)) + 1e-12) \
            * np.linspace(1, 0, sn) * slap
    return m * amp / (np.max(np.abs(m)) + 1e-12) * 0.9


def cowbell(amp: float = 1.0) -> np.ndarray:
    """540 + 800 Hz squares, bandpassed, fast clang."""
    n = int(0.30 * SR)
    tt = np.arange(n) / SR
    m = _sq(540.0, tt) + 0.9 * _sq(800.0, tt)
    sos = butter(2, [450, 2600], btype="band", fs=SR, output="sos")
    m = sosfilt(sos, m)
    env = np.exp(-tt * 13.0)
    env[: int(0.01 * SR)] *= 2.2          # the attack spike
    m = np.tanh(m * env * 2.0)
    return m * amp / (np.max(np.abs(m)) + 1e-12) * 0.85


def rim(amp: float = 1.0, seed: int = 6) -> np.ndarray:
    n = int(0.06 * SR)
    tt = np.arange(n) / SR
    m = np.sin(2 * np.pi * 1720.0 * tt) * 0.6 \
        + np.sin(2 * np.pi * 480.0 * tt)
    m = np.tanh(m * 3.0) * ad_env(n, 0.0004, 90.0)
    return m * amp / (np.max(np.abs(m)) + 1e-12) * 0.8


def shaker(dur: float = 0.09, amp: float = 1.0,
        seed: int = 7) -> np.ndarray:
    n = int(dur * SR)
    tt = np.arange(n) / SR
    sos = butter(2, [6000, 13500], btype="band", fs=SR, output="sos")
    m = sosfilt(sos, _noise(n, seed))
    env = np.sin(np.pi * np.clip(tt / dur, 0, 1)) ** 1.5
    return m * env * amp / (np.max(np.abs(m)) + 1e-12) * 0.7

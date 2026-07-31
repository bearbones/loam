"""Rooms and tape — the first real EFFECTS in loam.

FDN reverb (after Jot; see also Smith's Physical Audio Signal
Processing): N=8 delay lines with mutually-prime lengths (no shared
resonances), fed back through a Householder matrix I - 2/N·J (every
line scatters into every other — echo density builds fast), each
line with a one-pole damping lowpass and a gain set from the target
t60. Runs block-vectorized: within a block shorter than the
shortest delay, line outputs don't depend on line inputs, so each
block is pure numpy.

Loop-safety: `reverb_loop` processes the loop TWICE and keeps the
second pass — by then the network state is exactly what the end of
the loop leaves behind, so the wrap is continuous (valid when t60 <
loop length).

Tape echo: delay reads at fractional positions on a CIRCULAR tape
(modulo the loop, np.interp period=), with wow (slow pitch drift)
quantized to whole cycles per loop. Feedback is unrolled — each
round trip gets its own damping pass, so repeats darken the way
tape darkens.
"""

import numpy as np
from scipy.signal import lfilter

from . import SR

# Mutually prime delay lengths (samples at 44.1k): 32..66 ms.
_PRIMES = np.array([1433, 1601, 1867, 2053, 2251, 2399, 2689, 2903])


def _fdn_stereo(mono: np.ndarray, t60: float, size: float,
        damp_hz: float) -> np.ndarray:
    """The raw network: mono in, decorrelated stereo wet out."""
    n = len(mono)
    delays = np.maximum((_PRIMES * size).astype(int), 64)
    nl = len(delays)
    a = np.eye(nl) - 2.0 / nl                       # Householder
    gains = 10.0 ** (-3.0 * delays / (SR * t60))
    c = np.exp(-2.0 * np.pi * damp_hz / SR)         # one-pole damp
    in_g = np.array([1, -1, 1, -1, 1, -1, 1, -1], dtype=float)
    out_l = np.array([1, 0, -1, 0, 1, 0, -1, 0], dtype=float)
    out_r = np.array([0, 1, 0, -1, 0, 1, 0, 1], dtype=float)

    bufs = [np.zeros(d) for d in delays]
    ptrs = [0] * nl
    zi = np.zeros(nl)
    wet = np.zeros((n, 2))
    blk = int(np.min(delays))
    i = 0
    while i < n:
        b = min(blk, n - i)
        outs = np.empty((nl, b))
        for k in range(nl):
            d, p = delays[k], ptrs[k]
            if p + b <= d:
                outs[k] = bufs[k][p:p + b]
            else:
                outs[k] = np.concatenate([bufs[k][p:],
                        bufs[k][: p + b - d]])
        wet[i:i + b, 0] = out_l @ outs
        wet[i:i + b, 1] = out_r @ outs
        fb = (a @ outs) * gains[:, None]
        fb += in_g[:, None] * mono[i:i + b][None, :] * 0.25
        for k in range(nl):
            y, zk = lfilter([1 - c], [1, -c], fb[k],
                    zi=np.array([zi[k]]))
            zi[k] = zk[0]
            d, p = delays[k], ptrs[k]
            if p + b <= d:
                bufs[k][p:p + b] = y
            else:
                bufs[k][p:] = y[: d - p]
                bufs[k][: p + b - d] = y[d - p:]
            ptrs[k] = (p + b) % d
        i += b
    return wet


def reverb_loop(x: np.ndarray, t60: float = 2.4, size: float = 1.0,
        damp_hz: float = 4200.0, mix: float = 0.25,
        pre_ms: float = 12.0) -> np.ndarray:
    """Circular reverb for a LOOP (n,2). Processes twice, keeps the
    warm pass."""
    n = len(x)
    mono = x.mean(axis=1)
    pre = int(pre_ms * 1e-3 * SR)
    mono = np.roll(mono, pre)
    wet2 = _fdn_stereo(np.tile(mono, 2), t60, size, damp_hz)[n:]
    wet2 *= 1.0 / (np.max(np.abs(wet2)) + 1e-12) \
        * np.max(np.abs(x))
    return x * (1.0 - mix) + wet2 * mix


def reverb_tail(x: np.ndarray, t60: float = 2.4, size: float = 1.0,
        damp_hz: float = 4200.0, mix: float = 0.25,
        pre_ms: float = 12.0) -> np.ndarray:
    """One-shot reverb: returns x extended by the full tail."""
    n_tail = int(t60 * SR)
    if x.ndim == 1:
        x = np.stack([x, x], axis=1)
    xp = np.vstack([x, np.zeros((n_tail, 2))])
    mono = np.roll(xp.mean(axis=1), int(pre_ms * 1e-3 * SR))
    wet = _fdn_stereo(mono, t60, size, damp_hz)
    wet *= 1.0 / (np.max(np.abs(wet)) + 1e-12) * np.max(np.abs(x))
    return xp * (1.0 - mix) + wet * mix


def tape_echo_loop(x: np.ndarray, loop_s: float, delay_s: float,
        feedback: float = 0.5, damp_hz: float = 3200.0,
        wow_hz: float = 0.4, wow_ms: float = 3.0,
        pingpong: bool = True, mix: float = 0.35) -> np.ndarray:
    """Dub delay on circular tape. Echo k reads echo k-1 at
    t - delay(t) (mod loop), darkened each pass. wow_hz is
    quantized to whole cycles per loop."""
    n = len(x)
    t = np.arange(n) / SR
    wq = round(wow_hz * loop_s) / loop_s
    sway = np.sin(2 * np.pi * wq * t) * wow_ms * 1e-3
    pos = (np.arange(n) - (delay_s + sway) * SR) % n
    c = np.exp(-2.0 * np.pi * damp_hz / SR)
    xp_idx = np.arange(n)

    wet = np.zeros((n, 2))
    e = x.mean(axis=1)
    g = 1.0
    for k in range(12):
        e = np.interp(pos, xp_idx, e, period=n)
        # circular one-pole: warm on the tail
        warm = e[-SR:]
        y = lfilter([1 - c], [1, -c], np.concatenate([warm, e]))[SR:]
        e = y
        g *= feedback
        if pingpong:
            side = k % 2
            wet[:, side] += e * g * 0.9
            wet[:, 1 - side] += e * g * 0.35
        else:
            wet += e[:, None] * g
        if g < 1e-3:
            break
    return x + wet * mix


# ---------------------------------------------------------------
# Convolution spaces: synthesized impulse responses + circular
# convolution. A loop convolved CIRCULARLY with an IR is seamless
# by mathematical construction — the tail wraps into bar 1 because
# that is literally what circular convolution means. The IRs are
# designed, not sampled: rooms that don't exist.

def ir_room(t60: float = 2.0, size: float = 1.0,
        bright: float = 0.5, er_count: int = 8,
        seed: int = 0) -> np.ndarray:
    """Generic room: 4-band noise with per-band decay (highs die
    faster as `bright` falls) + sparse early reflections."""
    from scipy.signal import butter as _butter, sosfilt as _sosfilt
    rng = np.random.default_rng(seed)
    n = int(t60 * 1.15 * SR)
    tt = np.arange(n) / SR
    ir = np.zeros((n, 2))
    bands = [(20, 250, 1.25), (250, 1000, 1.0),
             (1000, 4000, 0.45 + 0.55 * bright),
             (4000, 14000, 0.2 + 0.5 * bright)]
    for lo, hi, tmul in bands:
        sos = _butter(2, [lo, hi], btype="band", fs=SR, output="sos")
        for ch in range(2):
            nz = _sosfilt(sos, rng.standard_normal(n))
            ir[:, ch] += nz * np.exp(-6.91 * tt / (t60 * tmul))
    ir[: int(0.003 * SR)] *= np.linspace(0, 1, int(0.003 * SR))[:, None]
    for _ in range(er_count):
        at = int(rng.uniform(0.004, 0.05) * size * SR)
        g = rng.uniform(0.2, 0.7)
        ch = rng.integers(0, 2)
        if at < n:
            ir[at, ch] += g
    ir[0, 0] += 1.0
    ir[0, 1] += 1.0
    return ir / np.max(np.abs(ir))


def ir_tank(t60: float = 1.6, modes: int = 9,
        seed: int = 0) -> np.ndarray:
    """Metal tank: the decay RINGS — inharmonic decaying sines on
    top of a short dark wash."""
    rng = np.random.default_rng(seed)
    n = int(t60 * 1.15 * SR)
    tt = np.arange(n) / SR
    ir = ir_room(t60 * 0.4, 0.7, 0.3, 5, seed) * 0.5
    ir = np.vstack([ir, np.zeros((n - len(ir), 2))])
    for _ in range(modes):
        f = rng.uniform(300, 4200)
        ring = np.sin(2 * np.pi * f * tt + rng.uniform(0, 6.28)) \
            * np.exp(-6.91 * tt / (t60 * rng.uniform(0.5, 1.0)))
        pan = rng.uniform(0.2, 0.8)
        ir[:, 0] += ring * 0.10 * pan
        ir[:, 1] += ring * 0.10 * (1 - pan)
    return ir / np.max(np.abs(ir))


def ir_bone(t60: float = 1.1, seed: int = 0) -> np.ndarray:
    """MARROW's own: a resonant cavity in old bone — bandpassed
    900-3200 Hz chitter, fast dense early cluster, dry low end."""
    from scipy.signal import butter as _butter, sosfilt as _sosfilt
    rng = np.random.default_rng(seed)
    n = int(t60 * 1.15 * SR)
    tt = np.arange(n) / SR
    ir = np.zeros((n, 2))
    sos = _butter(2, [900, 3200], btype="band", fs=SR, output="sos")
    for ch in range(2):
        nz = _sosfilt(sos, rng.standard_normal(n))
        ir[:, ch] = nz * np.exp(-6.91 * tt / t60)
    for _ in range(24):                      # the chitter cluster
        at = int(rng.uniform(0.001, 0.02) * SR)
        ir[at, rng.integers(0, 2)] += rng.uniform(0.3, 0.9)
    ir[0] += 0.8
    return ir / np.max(np.abs(ir))


def convolve_loop(x: np.ndarray, ir: np.ndarray,
        mix: float = 0.35) -> np.ndarray:
    """CIRCULAR convolution of a stereo loop with a stereo IR —
    seamless by construction (requires len(ir) <= len(x))."""
    n = len(x)
    wet = np.zeros_like(x)
    for ch in range(2):
        irp = np.zeros(n)
        irp[: min(len(ir), n)] = ir[: min(len(ir), n), ch]
        wet[:, ch] = np.fft.irfft(np.fft.rfft(x[:, ch])
                * np.fft.rfft(irp), n)
    wet *= np.max(np.abs(x)) / (np.max(np.abs(wet)) + 1e-12)
    return x * (1.0 - mix) + wet * mix


def convolve_tail(x: np.ndarray, ir: np.ndarray,
        mix: float = 0.35) -> np.ndarray:
    """Linear convolution — returns x extended by the IR tail."""
    from scipy.signal import fftconvolve
    if x.ndim == 1:
        x = np.stack([x, x], axis=1)
    n_out = len(x) + len(ir) - 1
    wet = np.zeros((n_out, 2))
    for ch in range(2):
        wet[:, ch] = fftconvolve(x[:, ch], ir[:, ch])
    wet *= np.max(np.abs(x)) / (np.max(np.abs(wet)) + 1e-12)
    dry = np.vstack([x, np.zeros((len(ir) - 1, 2))])
    return dry * (1.0 - mix) + wet * mix

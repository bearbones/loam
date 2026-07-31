"""loam — a headless music composition library.

Grown in the MARROW project (a Godot game whose every sound is
synthesized in code); spun off 2026-07-30 at the director's word.
Everything renders offline from numpy — no DAW, no samples, no
audio server. Compositions are Python scripts; the output is a
seamless loop unless you ask otherwise.

Seam-craft (the founding rules, learned the hard way):
- Continuous oscillators are quantized to a whole number of cycles
  per loop (`Loop.q`) so the seam is phase-exact.
- IIR filters are warmed with the signal's own tail
  (`Loop.filt_circular`) so sample 0 exits an already-settled filter.
- Event tails wrap past the loop end (`Loop.add` uses modulo
  indexing) — bar 1 already contains the reverb of the final bar.
- Deterministic: seeded RNG per piece, no wall clock.

Verify renders numerically, not by vibes: seam step vs typical
adjacent-sample delta, RMS contour, peak, and stereo width measured
ABOVE ~250 Hz (full-band L/R correlation is bass-dominated).
"""

import numpy as np
from scipy.signal import butter, sosfilt

SR = 44100


def hz(midi: float) -> float:
    """MIDI note number -> frequency (equal temperament, A440)."""
    return 440.0 * 2.0 ** ((midi - 69) / 12.0)


class Loop:
    """A seamless stereo loop canvas with the seam-craft built in."""

    def __init__(self, loop_s: float, seed: int):
        self.loop_s = loop_s
        self.n = int(round(SR * loop_s))
        self.buf = np.zeros((self.n, 2))
        self.t = np.arange(self.n) / SR
        self.rng = np.random.default_rng(seed)

    def q(self, f: float) -> float:
        """Quantize to a whole number of cycles per loop: continuous
        oscillators must land at the seam phase-exact."""
        return round(f * self.loop_s) / self.loop_s

    def add(self, start_s: float, chunk: np.ndarray) -> None:
        """Mix a stereo chunk in at start_s, wrapping past the end."""
        idx = (int(start_s * SR) + np.arange(len(chunk))) % self.n
        np.add.at(self.buf, idx, chunk)

    def filt_circular(self, sos, x: np.ndarray) -> np.ndarray:
        """IIR-filter a LOOP: warm the filter with the signal's own
        tail so sample 0 exits an already-settled filter."""
        warm = SR
        y = sosfilt(sos, np.vstack([x[-warm:], x]), axis=0)
        return y[warm:]

    def master(self, lp_hz: float = 7500.0, drive: float = 1.35,
            ceil: float = 0.90) -> np.ndarray:
        sos = butter(2, lp_hz, btype="low", fs=SR, output="sos")
        y = self.filt_circular(sos, self.buf)
        y = np.tanh(y * drive) / np.tanh(drive)
        return y * (ceil / np.max(np.abs(y)))


def stereo(mono: np.ndarray, pan: float) -> np.ndarray:
    """Equal-power pan a mono signal into a stereo chunk. -1..1."""
    a = (pan + 1.0) * np.pi / 4.0
    return np.stack([mono * np.cos(a), mono * np.sin(a)], axis=1)


def ad_env(n: int, a_s: float, decay: float) -> np.ndarray:
    """Linear attack (a_s seconds) into exponential decay (rate/s)."""
    tt = np.arange(n) / SR
    e = np.exp(-tt * decay)
    a = max(int(a_s * SR), 1)
    e[:a] *= np.linspace(0, 1, a)
    return e


def write_wav(path: str, data: np.ndarray) -> None:
    import wave
    pcm = (data * 32767).astype(np.int16)
    with wave.open(path, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())
    rms = float(np.sqrt(np.mean(data ** 2)))
    print(f"wrote {path}  {len(data)/SR:.1f}s  "
          f"peak={np.max(np.abs(data)):.3f} rms={rms:.3f}")


def seam_report(data: np.ndarray) -> str:
    """The loop-seam check. The wrap step |x[0] - x[-1]| is CLICKLESS
    when it is an unremarkable member of the adjacent-sample-delta
    distribution — report its percentile rank (<= ~0.999 passes; a
    genuine click sits far beyond the distribution max)."""
    step = float(np.max(np.abs(data[0] - data[-1])))
    dd = np.abs(np.diff(data, axis=0))
    rank = float((dd < step).mean())
    return (f"seam step={step:.4f} rank=p{100 * rank:.1f} "
            f"(dist p50={np.percentile(dd, 50):.4f} "
            f"max={dd.max():.4f})")

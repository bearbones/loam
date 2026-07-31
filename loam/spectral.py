"""Spectral surgery — the phase-vocoder family.

STFT the sound, operate on magnitudes and phases separately,
overlap-add back. Three classics, loam-shaped:

- freeze: grab ONE analysis frame's magnitude spectrum and
  resynthesize it forever. Each synthesis frame gets the bin's
  natural phase advance plus a little jitter — the sound holds
  still but stays alive (pure phase advance alone is a buzzy
  organ; pure random phase is noise; the blend is the trick).
  Output loops seamlessly: frames are overlap-added with wrap.
- stretch: the standard phase vocoder (Flanagan/Dolson). Phase
  differences between input frames are unwrapped to true bin
  frequencies, then re-accumulated at the output hop — time moves
  slower, pitch stays put.
- cross_synth: A's magnitudes on B's phases per frame. Give a
  choir the phases of a drum loop and the room learns to talk.

Frames: 4096/1024 hann (loam is not real-time; bigger frames,
better bass).
"""

import numpy as np

from . import SR

_NFFT = 4096
_HOP = 1024


def _frames(x: np.ndarray, nfft: int, hop: int) -> np.ndarray:
    n = 1 + max(0, (len(x) - nfft)) // hop
    idx = np.arange(nfft)[None, :] + hop * np.arange(n)[:, None]
    return x[idx] * np.hanning(nfft)[None, :]


def freeze(x: np.ndarray, at_s: float, out_s: float,
        jitter: float = 0.35, nfft: int = _NFFT, hop: int = _HOP,
        seed: int = 0) -> np.ndarray:
    """Hold the spectrum at at_s for out_s seconds, as a seamless
    loop. jitter 0..1 blends organ-steady (0) to airy (1)."""
    if x.ndim == 2:
        x = x.mean(axis=1)
    i0 = min(int(at_s * SR), max(len(x) - nfft, 0))
    mag = np.abs(np.fft.rfft(x[i0:i0 + nfft] * np.hanning(nfft)))
    n_out = int(out_s * SR)
    out = np.zeros(n_out)
    rng = np.random.default_rng(seed)
    omega = 2.0 * np.pi * np.arange(len(mag)) * hop / nfft
    phase = rng.uniform(0, 2 * np.pi, len(mag))
    win = np.hanning(nfft)
    for k in range(int(np.ceil(n_out / hop))):
        phase = phase + omega \
            + rng.uniform(-np.pi, np.pi, len(mag)) * jitter
        frame = np.fft.irfft(mag * np.exp(1j * phase), nfft) * win
        idx = (k * hop + np.arange(nfft)) % n_out
        np.add.at(out, idx, frame)
    return out / (np.max(np.abs(out)) + 1e-12) * 0.9


def stretch(x: np.ndarray, factor: float, nfft: int = _NFFT,
        hop: int = _HOP) -> np.ndarray:
    """Phase-vocoder time stretch (factor 2 = twice as long)."""
    if x.ndim == 2:
        x = x.mean(axis=1)
    fr = _frames(x, nfft, hop)
    spec = np.fft.rfft(fr, axis=1)
    mag, ph = np.abs(spec), np.angle(spec)
    omega = 2.0 * np.pi * np.arange(spec.shape[1]) * hop / nfft
    dph = ph[1:] - ph[:-1] - omega[None, :]
    dph = dph - 2.0 * np.pi * np.round(dph / (2.0 * np.pi))
    true_w = omega[None, :] + dph                    # rad per hop
    n_in = len(fr)
    n_syn = max(int(round((n_in - 1) * factor)), 1)
    out = np.zeros(n_syn * hop + nfft)
    phase = ph[0].copy()
    win = np.hanning(nfft)
    for k in range(n_syn):
        pos = k / factor
        i = min(int(pos), n_in - 2)
        frac = pos - i
        m = mag[i] * (1 - frac) + mag[i + 1] * frac
        phase = phase + true_w[min(i, len(true_w) - 1)]
        out[k * hop: k * hop + nfft] += np.fft.irfft(
                m * np.exp(1j * phase), nfft) * win
    return out / (np.max(np.abs(out)) + 1e-12) * 0.9


def cross_synth(mag_src: np.ndarray, ph_src: np.ndarray,
        nfft: int = _NFFT, hop: int = _HOP,
        whiten: float = 0.5, punch: float = 0.0) -> np.ndarray:
    """A's magnitudes, B's phases (and B's transient grid). whiten
    blends in B's per-band envelope; punch (0..~2) additionally
    gates each frame by B's broadband energy — the vocoder's
    envelope follower, needed because ~90ms analysis windows smear
    transients that phases alone can't restore."""
    if mag_src.ndim == 2:
        mag_src = mag_src.mean(axis=1)
    if ph_src.ndim == 2:
        ph_src = ph_src.mean(axis=1)
    n = min(len(mag_src), len(ph_src))
    fa = np.fft.rfft(_frames(mag_src[:n], nfft, hop), axis=1)
    fb = np.fft.rfft(_frames(ph_src[:n], nfft, hop), axis=1)
    k = min(len(fa), len(fb))
    mag = np.abs(fa[:k])
    if whiten > 0.0:
        env = np.maximum(np.abs(fb[:k]), 1e-9)
        mag = mag * env ** whiten
    spec = mag * np.exp(1j * np.angle(fb[:k]))
    frames = np.fft.irfft(spec, nfft, axis=1) * np.hanning(nfft)[None, :]
    if punch > 0.0:
        eng = np.sqrt((np.abs(fb[:k]) ** 2).sum(axis=1))
        eng = (eng / (eng.max() + 1e-12)) ** punch
        frames *= eng[:, None]
    out = np.zeros(k * hop + nfft)
    for i in range(k):
        out[i * hop: i * hop + nfft] += frames[i]
    return out / (np.max(np.abs(out)) + 1e-12) * 0.9

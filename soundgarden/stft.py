"""Small STFT toolkit shared by the sinusoidal (sms) and latent prototypes.

Frames are centered (nfft/2 zero padding), Hann windowed, and the inverse
divides by the summed squared window so analysis→synthesis is an identity.
Griffin-Lim recovers a waveform from magnitudes only; it is the honest
baseline decoder and the reason mel-only latents smear transients.
"""
import numpy as np

from loam import SR

NFFT, HOP = 2048, 256


def stft(x, nfft=NFFT, hop=HOP):
    x = np.asarray(x, dtype=float)
    pad = nfft // 2
    x = np.concatenate([np.zeros(pad), x, np.zeros(pad)])
    count = 1 + max(0, len(x) - nfft) // hop
    idx = np.arange(nfft)[None, :] + hop * np.arange(count)[:, None]
    return np.fft.rfft(x[idx] * np.hanning(nfft)[None, :], axis=1)


def istft(spec, length, nfft=NFFT, hop=HOP):
    window = np.hanning(nfft)
    frames = np.fft.irfft(spec, nfft, axis=1) * window[None, :]
    total = (len(spec) - 1) * hop + nfft
    out = np.zeros(total)
    norm = np.zeros(total)
    for i, frame in enumerate(frames):
        out[i * hop:i * hop + nfft] += frame
        norm[i * hop:i * hop + nfft] += window ** 2
    out = out / np.maximum(norm, 1e-8)
    pad = nfft // 2
    return out[pad:pad + length]


def griffin_lim(magnitude, length, iterations=40, seed=0, nfft=NFFT, hop=HOP):
    """Phase recovery from a magnitude spectrogram (frames × bins)."""
    rng = np.random.default_rng(seed)
    phase = np.exp(2j * np.pi * rng.uniform(size=magnitude.shape))
    for _ in range(iterations):
        x = istft(magnitude * phase, length, nfft, hop)
        spec = stft(x, nfft, hop)[:len(magnitude)]
        if len(spec) < len(magnitude):
            spec = np.vstack([spec, np.zeros((len(magnitude) - len(spec), spec.shape[1]), dtype=complex)])
        phase = np.exp(1j * np.angle(spec))
    return istft(magnitude * phase, length, nfft, hop)


def frame_times(count, hop=HOP):
    return np.arange(count) * hop / SR

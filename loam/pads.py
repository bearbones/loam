"""PADsynth — Paul Nasca's pad algorithm, loam-shaped.

Build an amplitude spectrum where each harmonic is a Gaussian BAND
(not a line), give every bin a random phase, and take one big IFFT.
The width is heard as ensemble/chorus richness; the random phases
make it breathe. Because the spectrum lives on the DFT grid of the
table itself, the render is EXACTLY periodic — the seam does not
exist. This is seam-craft's favorite instrument.

Stereo comes free: draw phases twice with different seeds and the
two channels are fully decorrelated versions of the same timbre.

Bandwidth formula (after the ZynAddSubFX reference): a harmonic at
frequency f_h with bandwidth `bw` cents spans
    bw_hz = (2**(bw/1200) - 1) * f_h * relbw(h)
where relbw(h) = h**bwscale lets upper harmonics spread wider
(bwscale=1 mimics natural ensembles, where detune in Hz scales
with frequency).
"""

import numpy as np

from . import SR


def padsynth_table(loop_s: float, f0: float, amps, bw_cents: float = 40.0,
        bwscale: float = 1.0, seed: int = 0) -> np.ndarray:
    """Render one mono loop-length table. `amps` is the per-harmonic
    amplitude list (index 0 = fundamental)."""
    n = int(round(loop_s * SR))
    half = n // 2 + 1
    spec_amp = np.zeros(half)
    bin_hz = 1.0 / loop_s
    for h, a in enumerate(amps, start=1):
        if a <= 0.0:
            continue
        fh = f0 * h
        if fh >= SR * 0.5:
            break
        bw_hz = (2.0 ** (bw_cents / 1200.0) - 1.0) * fh \
            * (h ** (bwscale - 1.0))
        sigma = max(bw_hz / 2.355, bin_hz * 0.5)   # FWHM -> sigma
        lo = max(int((fh - 5 * sigma) / bin_hz), 1)
        hi = min(int((fh + 5 * sigma) / bin_hz) + 2, half)
        f_bins = np.arange(lo, hi) * bin_hz
        spec_amp[lo:hi] += a * np.exp(-((f_bins - fh) ** 2)
                / (2.0 * sigma * sigma))
    rng = np.random.default_rng(seed)
    phases = rng.uniform(0, 2 * np.pi, half)
    spec = spec_amp * np.exp(1j * phases)
    spec[0] = 0.0
    table = np.fft.irfft(spec, n)
    return table / (np.max(np.abs(table)) + 1e-12)


def padsynth_stereo(loop_s: float, f0: float, amps, bw_cents: float = 40.0,
        bwscale: float = 1.0, seed: int = 0) -> np.ndarray:
    """Two independent phase draws of the same spectrum: a stereo
    pad with zero inter-channel correlation and identical color."""
    l = padsynth_table(loop_s, f0, amps, bw_cents, bwscale, seed)
    r = padsynth_table(loop_s, f0, amps, bw_cents, bwscale, seed + 1)
    return np.stack([l, r], axis=1)


def saw_amps(k: int, tilt: float = 1.0):
    """1/h**tilt harmonic rolloff — tilt 1 = saw, 2 = square-ish."""
    return [1.0 / (h ** tilt) for h in range(1, k + 1)]


def formant_amps(f0: float, k: int, formants, tilt: float = 0.8):
    """Shape a harmonic stack through vowel formant resonances:
    `formants` is [(center_hz, bandwidth_hz, gain), ...]. Feeding
    this to padsynth gives a seamless CHOIR — the ensemble width of
    PADsynth plus the vowel of a voice."""
    amps = []
    for h in range(1, k + 1):
        fh = f0 * h
        g = 0.06 / (h ** tilt)          # residual glottal rolloff
        for fc, bw, fg in formants:
            g += fg * np.exp(-((fh - fc) ** 2) / (2.0 * (bw / 2.355) ** 2)) \
                / (h ** 0.3)
        amps.append(g)
    return amps


# Vowel formant tables (F1, F2, F3 — classic average adult values).
VOWELS = {
    "ah": [(730, 90, 1.0), (1090, 110, 0.5), (2440, 170, 0.20)],
    "oh": [(570, 80, 1.0), (840, 100, 0.45), (2410, 170, 0.12)],
    "oo": [(300, 70, 1.0), (870, 100, 0.30), (2240, 170, 0.08)],
    "eh": [(530, 80, 1.0), (1840, 120, 0.45), (2480, 170, 0.20)],
    "ee": [(270, 70, 1.0), (2290, 140, 0.35), (3010, 180, 0.20)],
}

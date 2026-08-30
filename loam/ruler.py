"""The consolidated rulers — every measurement this library has had
to learn the hard way, in one module, with the hard-way version as
the default.

The log's recurring lesson: the instrument is easy, the ruler is
hard. Until now every experiment hand-rolled its measurements and
paid the tuition again. Each function below encodes a specific
earned rule (cited from LOG.md); experiments should reach here
first and hand-roll only what is genuinely new.

House rules these tools assume but cannot enforce:
- Measure a processor on its OWN BUS, never in the mix.
- Per-call peak normalization inverts cross-call energy
  comparisons — render comparison material with norm off.
- Judge stereo width PER MATERIAL (a centered drum backbone is
  correct, not a failure).
"""

import numpy as np
from scipy.signal import butter, sosfilt, sosfiltfilt

from . import SR


def _mono(x: np.ndarray) -> np.ndarray:
    return x.mean(axis=1) if x.ndim == 2 else x


def hps_pitch(x: np.ndarray, fmin: float = 40.0, fmax: float = 2500.0,
        nharm: int = 5) -> float:
    """Fundamental via harmonic product spectrum. Earned rule:
    plain argmax lies when a harmonic edges the fundamental (e04);
    multiplying downsampled spectra makes only the true f0's comb
    line up."""
    m = _mono(x)
    w = m * np.hanning(len(m))
    mag = np.abs(np.fft.rfft(w))
    f = np.fft.rfftfreq(len(m), 1.0 / SR)
    acc = np.log(mag + 1e-12).copy()
    for h in range(2, nharm + 1):
        dec = np.log(mag[::h] + 1e-12)
        acc[:len(dec)] += dec
    band = (f >= fmin) & (f <= fmax)
    acc[~band] = -np.inf
    return float(f[int(np.argmax(acc))])


def centroid_hz(x: np.ndarray) -> float:
    """Spectral centroid, POWER-weighted. Earned rule: magnitude
    weighting lets thousands of tiny high bins outvote three loud
    low ones (session 33: drum centroid 62 vs 1224 Hz was the
    honest depth claim)."""
    m = _mono(x)
    p = np.abs(np.fft.rfft(m * np.hanning(len(m)))) ** 2
    f = np.fft.rfftfreq(len(m), 1.0 / SR)
    return float((f * p).sum() / (p.sum() + 1e-12))


def crest_db(x: np.ndarray) -> float:
    """Crest factor (peak over RMS) in dB — transients are PEAKS,
    not energy sums (e19). Over a ramping gesture, window the
    steady region first or you measure the ramp (e34)."""
    m = _mono(x)
    rms = float(np.sqrt(np.mean(m ** 2)) + 1e-12)
    return 20.0 * np.log10(float(np.max(np.abs(m))) / rms + 1e-12)


def band_density(x: np.ndarray, lo: float, hi: float) -> float:
    """Mean power per sample within [lo, hi] Hz. Earned rule
    (session 35): summed rfft power scales with segment LENGTH —
    a 10 s window against a 7 s one inflated a ratio 0.35 -> 0.71.
    Density (divide by N) compares unequal windows honestly."""
    m = _mono(x)
    p = np.abs(np.fft.rfft(m)) ** 2
    f = np.fft.rfftfreq(len(m), 1.0 / SR)
    sel = (f >= lo) & (f < hi)
    return float(p[sel].sum() / len(m))


def width_corr(x: np.ndarray, above_hz: float = 250.0) -> float:
    """L/R correlation ABOVE ~250 Hz (full-band correlation is
    bass-dominated). +1 mono, 0 decorrelated. Judge the target per
    material."""
    sos = butter(4, above_hz, btype="high", fs=SR, output="sos")
    y = sosfilt(sos, x, axis=0)
    c = np.corrcoef(y[:, 0], y[:, 1])[0, 1]
    return float(c)


def rms_db(x: np.ndarray) -> float:
    return 20.0 * np.log10(float(np.sqrt(np.mean(_mono(x) ** 2))) + 1e-12)


def rms_contour(x: np.ndarray, nwin: int = 8) -> list:
    """Windowed RMS in dB — the stationarity / hole-and-spike
    ruler (session 35's handover check)."""
    m = _mono(x)
    edges = np.linspace(0, len(m), nwin + 1).astype(int)
    return [20.0 * np.log10(float(np.sqrt(np.mean(
            m[a:b] ** 2))) + 1e-12) for a, b in zip(edges, edges[1:])]


def onset_env(x: np.ndarray, lo: float = 1100.0, hi: float = 3500.0,
        smooth_hz: float = 40.0) -> np.ndarray:
    """Rectified band-limited envelope for pulse-rate reading.
    Earned rules (e34): read rate where pulses stay DISTINCT — the
    high band, whose modes decay fast — and smooth only enough to
    merge waveform cycles, not adjacent pulses."""
    band = butter(2, [lo, hi], btype="band", fs=SR, output="sos")
    e = np.abs(sosfilt(band, _mono(x)))
    lp = butter(2, smooth_hz, btype="low", fs=SR, output="sos")
    return sosfiltfilt(lp, e)


def pulse_rate(x: np.ndarray, rate_lo: float, rate_hi: float,
        lo: float = 1100.0, hi: float = 3500.0) -> float:
    """Dominant pulse rate (Hz) via envelope autocorrelation,
    searched only within [rate_lo, rate_hi]. Earned rules (e34):
    a long-ringing low mode makes autocorr read subharmonics
    (23/s -> 11/s), so the envelope comes from the fast-decaying
    band; and the envelope is high-passed at rate_lo/2 so slow
    undulation cannot bias long lags."""
    env = onset_env(x, lo, hi)
    hp = butter(2, max(rate_lo / 2.0, 0.5), btype="high", fs=SR,
            output="sos")
    env = sosfiltfilt(hp, env)
    env = env - env.mean()
    ac = np.correlate(env, env, mode="full")[len(env) - 1:]
    lag_lo = int(SR / rate_hi)
    lag_hi = min(int(SR / rate_lo), len(ac) - 1)
    if lag_hi <= lag_lo:
        return float("nan")
    k = lag_lo + int(np.argmax(ac[lag_lo:lag_hi]))
    return SR / float(k)


def flatness(x: np.ndarray, lo: float = 60.0, hi: float = 2000.0) -> float:
    """Spectral flatness (Wiener entropy: geometric over arithmetic
    mean of power), computed PER OCTAVE BAND over [lo, hi] and
    averaged. ~1 = noise, orders of magnitude lower = tonal comb.
    Born in e38 to measure TONALIZATION (noise in, chord out)
    without smuggling in which pitches — that is a separate
    (chroma) claim. Earned rule, same cycle: a single wide-band
    flatness confounds TILT with tonality — steeply low-tilted
    noise (thunder) measured 'tonal' because most of the window's
    bins were merely empty. Per-octave, tilted noise is still
    locally flat; only a comb is spiky inside its own octave.
    And the octave average is POWER-weighted (the centroid lesson
    again): unweighted, the quiet noise-floor octaves above the
    music outvote the loud combed ones."""
    m = _mono(x)
    p = np.abs(np.fft.rfft(m * np.hanning(len(m)))) ** 2
    f = np.fft.rfftfreq(len(m), 1.0 / SR)
    vals, wts = [], []
    edge = lo
    while edge < hi:
        sel = (f >= edge) & (f < min(edge * 2.0, hi))
        if sel.sum() >= 32:
            pb = p[sel]
            gm = np.exp(np.mean(np.log(pb + 1e-30)))
            vals.append(gm / (np.mean(pb) + 1e-30))
            wts.append(float(pb.sum()))
        edge *= 2.0
    if not vals:
        return 1.0
    return float(np.average(vals, weights=wts))


def chroma(x: np.ndarray, lo: float = 60.0, hi: float = 2000.0) -> np.ndarray:
    """Fold spectral POWER into 12 pitch classes (C=0..B=11) over
    [lo, hi], normalized to sum 1. Remember e35: harmonic leakage
    means honest chroma claims are RELATIVE (top-k membership,
    pole comparisons), never absolute floors."""
    m = _mono(x)
    p = np.abs(np.fft.rfft(m * np.hanning(len(m)))) ** 2
    f = np.fft.rfftfreq(len(m), 1.0 / SR)
    sel = (f >= lo) & (f <= hi)
    cls = np.mod(np.round(69.0 + 12.0 * np.log2(
            np.maximum(f[sel], 1e-6) / 440.0)), 12).astype(int)
    out = np.zeros(12)
    np.add.at(out, cls, p[sel])
    return out / (out.sum() + 1e-30)


def seam_rank(x: np.ndarray) -> float:
    """Numeric twin of loam.seam_report: percentile rank of the
    wrap step in the adjacent-delta distribution. <= ~0.999 is
    clickless; a genuine click sits beyond the distribution max."""
    step = float(np.max(np.abs(x[0] - x[-1])))
    dd = np.abs(np.diff(x, axis=0))
    return float((dd < step).mean())


def report(x: np.ndarray, name: str = "bus") -> dict:
    """The standard card: the numbers every render should face."""
    d = {
        "name": name,
        "peak": float(np.max(np.abs(x))),
        "rms_db": rms_db(x),
        "crest_db": crest_db(x),
        "centroid_hz": centroid_hz(x),
        "seam_rank": seam_rank(x),
    }
    if x.ndim == 2:
        d["width_corr"] = width_corr(x)
    print(f"[{name}] peak={d['peak']:.3f} rms={d['rms_db']:.1f}dB "
          f"crest={d['crest_db']:.1f}dB centroid={d['centroid_hz']:.0f}Hz "
          f"seam=p{100 * d['seam_rank']:.1f}"
          + (f" width={d['width_corr']:+.3f}" if x.ndim == 2 else ""))
    return d

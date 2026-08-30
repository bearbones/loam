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
        nharm: int = 5, tol_bins: int = 3) -> float:
    """Fundamental via harmonic product spectrum. Earned rules:
    plain argmax lies when a harmonic edges the fundamental (e04);
    multiplying downsampled spectra makes only the true f0's comb
    line up. And (e40) PARTIALS ARE NOT BINS: exact-bin
    downsampling demands partial h sit exactly at bin h*i, but
    real partials drift a bin or three (inharmonicity, window
    edges) — one missed high partial lands on log(~0) and the
    true candidate loses to its own 3rd harmonic. Dilating the
    magnitudes (local max over +/-tol_bins) before the harmonic
    sum forgives the drift. Then the octave rescue (same cycle):
    an instrument can NOTCH a low harmonic (a pluck picked at 0.2
    of the string zeroes partial 5), sabotaging the true
    candidate's product while 2*f0's harmonic set dodges the
    notch — so if genuine energy sits AT a subharmonic of the
    winner, the subharmonic is the fundamental. "Genuine" is
    two-sided: a modest fraction of the winner (>= 6%) AND far
    above the spectral floor (>= 8x the dilated median) — a KS
    fundamental can be 12x weaker than its own 2nd partial and
    still be unmistakably a partial, not noise."""
    from scipy.ndimage import maximum_filter1d
    m = _mono(x)
    w = m * np.hanning(len(m))
    mag = maximum_filter1d(np.abs(np.fft.rfft(w)), 2 * tol_bins + 1)
    f = np.fft.rfftfreq(len(m), 1.0 / SR)
    acc = np.log(mag + 1e-12).copy()
    for h in range(2, nharm + 1):
        dec = np.log(mag[::h] + 1e-12)
        acc[:len(dec)] += dec
    band = (f >= fmin) & (f <= fmax)
    acc[~band] = -np.inf
    i0 = int(np.argmax(acc))
    floor = np.median(mag) + 1e-12
    subs = [j for j in (int(round(i0 / d)) for d in (2, 3, 4))
            if f[j] >= fmin and mag[j] >= 0.06 * mag[i0]
            and mag[j] >= 8.0 * floor]
    if subs:
        i0 = min(subs)
    return float(f[i0])


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


def onset_times(x: np.ndarray, frame: int = 1024, hop: int = 256,
        k: float = 3.0, min_sep: float = 0.08,
        floor_frac: float = 0.15) -> np.ndarray:
    """Onset times (s) via spectral flux — the half-wave-rectified
    frame-to-frame magnitude increase, peak-picked above a LOCAL
    adaptive threshold (median + k*MAD over a sliding ~1 s
    neighborhood; a global threshold misses soft strikes under
    loud ones). Promised in e36, born in e39, where change
    ringing needed its 360 strikes counted and ordered.
    Earned rule, same cycle: in a rest the local median AND MAD
    collapse together and the threshold chases noise — every ghost
    fired inside the handstroke gaps. The floor (floor_frac of the
    flux's own 90th percentile) keeps silence from becoming
    hypersensitive. Absolute times carry a ~frame/2 latency —
    compare onsets to onsets, or allow that offset when matching
    design times."""
    m = _mono(x)
    n_fr = 1 + (len(m) - frame) // hop
    idx = np.arange(frame)[None, :] + hop * np.arange(n_fr)[:, None]
    w = np.hanning(frame)
    mags = np.abs(np.fft.rfft(m[idx] * w, axis=1))
    flux = np.sum(np.maximum(mags[1:] - mags[:-1], 0.0), axis=1)
    flux = np.concatenate([[0.0], flux])
    half = max(int(0.5 * SR / hop), 8)
    floor = floor_frac * np.percentile(flux, 90)
    thr = np.empty_like(flux)
    for i in range(len(flux)):
        seg = flux[max(0, i - half):i + half]
        med = np.median(seg)
        mad = np.median(np.abs(seg - med)) + 1e-12
        thr[i] = max(med + k * mad, floor)
    sep = max(int(min_sep * SR / hop), 1)
    hits = []
    for i in range(1, len(flux) - 1):
        if flux[i] > thr[i] and flux[i] == flux[
                max(0, i - sep):i + sep + 1].max():
            if not hits or i - hits[-1] >= sep:
                hits.append(i)
    return np.array(hits) * hop / SR


def transcribe(x: np.ndarray, min_sep: float = 0.08,
        fmin: float = 80.0, fmax: float = 1500.0,
        max_win: float = 0.5) -> list:
    """MONOPHONIC transcription: onset_times for the whens,
    hps_pitch over each inter-onset window for the whats. Returns
    [(onset_s, midi_float)] — round midi yourself, and remember
    onset latency (see onset_times). Born in e40, where the
    ouroboros canon had to give its tune back from the render.
    Polyphony is a different animal — do not point this at it."""
    m = _mono(x)
    ts = onset_times(x, min_sep=min_sep)
    out = []
    for i, t in enumerate(ts):
        a = int((t + 0.015) * SR)
        end = ts[i + 1] - 0.01 if i + 1 < len(ts) else t + max_win
        b = int(min(end, t + max_win) * SR)
        b = max(b, a + int(0.05 * SR))
        f = hps_pitch(m[a:min(b, len(m))], fmin, fmax)
        out.append((float(t), 69.0 + 12.0 * np.log2(f / 440.0)))
    return out


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

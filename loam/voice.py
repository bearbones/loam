"""The singing voice — source-filter, Klatt-style.

Source: Rosenberg glottal pulse — a smooth rise while the glottis
opens, a sharper cosine fall as it snaps shut; the snap is where
the harmonics come from. Phase is ACCUMULATED, so pitch glides
(portamento) never click. Naturalness is jitter (slow random f0
wander, ~0.3%), shimmer (amplitude wander), delayed vibrato, and
breath (formant-filtered aspiration).

Filter: parallel bank of second-order resonators at the formant
frequencies (loam.pads.VOWELS tables), coefficients recomputed
every 128 samples so vowels can MORPH mid-note (diphthongs, or
just the lazy drift real mouths do).

sing() takes a phrase [(midi, beats, vowel), ...] and renders a
legato vocalise line — one breath, portamento between notes.
"""

import numpy as np
from scipy.signal import lfilter, butter, sosfilt

from . import SR
from .pads import VOWELS


def _rosenberg(ph: np.ndarray, open_q: float = 0.6) -> np.ndarray:
    """Glottal flow pulse from phase in [0,1)."""
    g = np.zeros_like(ph)
    rise = ph < open_q * 0.67
    t = ph[rise] / (open_q * 0.67)
    g[rise] = 0.5 * (1.0 - np.cos(np.pi * t))
    fall = (~rise) & (ph < open_q)
    t2 = (ph[fall] - open_q * 0.67) / (open_q * 0.33)
    g[fall] = np.cos(0.5 * np.pi * t2)
    return g


def _formant_bank(src: np.ndarray, tracks, blk: int = 128) -> np.ndarray:
    """Parallel resonators; tracks = list of (fc[n], bw, gain)."""
    n = len(src)
    out = np.zeros(n)
    for fc_arr, bw, gain in tracks:
        zi = np.zeros(2)
        i = 0
        y = np.empty(n)
        while i < n:
            j = min(i + blk, n)
            fc = float(fc_arr[(i + j) // 2]) if hasattr(fc_arr, "__len__") \
                else float(fc_arr)
            r = np.exp(-np.pi * bw / SR)
            th = 2.0 * np.pi * np.clip(fc, 60.0, SR * 0.45) / SR
            a1, a2 = -2.0 * r * np.cos(th), r * r
            b0 = (1.0 - r) * np.sqrt(1.0 + r * r - 2.0 * r * np.cos(2 * th))
            seg, zi = lfilter([b0], [1.0, a1, a2], src[i:j], zi=zi)
            y[i:j] = seg
            i = j
        out += y * gain
    return out


def sing(phrase, bpm: float = 72.0, base_vib_hz: float = 5.2,
        vib_cents: float = 35.0, porta_s: float = 0.09,
        breath: float = 0.045, jitter: float = 0.003,
        amp: float = 1.0, seed: int = 0) -> np.ndarray:
    """phrase: [(midi, beats, vowel), ...]; vowel from VOWELS or a
    (v1, v2) pair to morph across the note. Returns mono."""
    spb = 60.0 / bpm
    rng = np.random.default_rng(seed)
    durs = [b * spb for (_, b, _) in phrase]
    n = int(sum(durs) * SR) + int(0.25 * SR)
    t = np.arange(n) / SR

    # --- f0 track: steps -> exponential portamento -> vib/jitter ---
    f0 = np.zeros(n)
    at = 0
    for (midi, b, _), d in zip(phrase, durs):
        seg = int(d * SR)
        f0[at: at + seg] = 440.0 * 2.0 ** ((midi - 69) / 12.0)
        at += seg
    f0[at:] = f0[at - 1]
    tau = int(porta_s * SR)
    ker_t = np.arange(4 * tau)
    ker = np.exp(-ker_t / tau)
    ker /= ker.sum()
    f0 = np.convolve(np.concatenate([np.full(4 * tau, f0[0]), f0]),
            ker, mode="same")[4 * tau:]
    wander = np.cumsum(rng.standard_normal(n)) / SR
    wander -= np.linspace(0, wander[-1], n)
    f0 *= 1.0 + jitter * wander / max(np.abs(wander).max(), 1e-9)
    vib_on = np.clip((t - 0.35) / 0.5, 0, 1)
    f0 *= 2.0 ** (vib_cents * vib_on
            * np.sin(2 * np.pi * base_vib_hz * t) / 1200.0)

    # --- glottal source with accumulated phase --------------------
    ph = np.cumsum(f0) / SR % 1.0
    src = _rosenberg(ph)
    src = np.diff(src, prepend=src[0])       # flow derivative: brighter
    shimmer = 1.0 + 0.06 * sosfilt(butter(2, 6.0, fs=SR, output="sos"),
            rng.standard_normal(n))
    src *= shimmer

    # --- formant tracks: per-note vowels, morph across note -------
    def vw(name):
        return VOWELS[name]

    n_form = 3
    tracks = []
    for fi in range(n_form):
        fc = np.zeros(n)
        at = 0
        for (midi, b, vowel), d in zip(phrase, durs):
            seg = int(d * SR)
            if isinstance(vowel, tuple):
                a_f = vw(vowel[0])[fi][0]
                b_f = vw(vowel[1])[fi][0]
                x = np.linspace(0, 1, seg)
                fc[at: at + seg] = a_f + (b_f - a_f) * x * x * (3 - 2 * x)
            else:
                fc[at: at + seg] = vw(vowel)[fi][0]
            at += seg
        fc[at:] = fc[at - 1]
        fc = np.convolve(fc, ker, mode="same")
        bw = [90.0, 110.0, 170.0][fi]
        gain = [1.0, 0.55, 0.22][fi]
        tracks.append((fc, bw, gain))
    voiced = _formant_bank(src, tracks)

    # --- aspiration through the same mouth ------------------------
    asp = _formant_bank(rng.standard_normal(n) * breath, tracks)
    envs = np.ones(n)
    a_n = int(0.10 * SR)
    envs[:a_n] = np.linspace(0, 1, a_n) ** 1.5
    r_n = int(0.22 * SR)
    envs[-r_n:] *= np.linspace(1, 0, r_n) ** 1.2
    out = (voiced + asp) * envs
    return out * amp / (np.max(np.abs(out)) + 1e-12) * 0.9

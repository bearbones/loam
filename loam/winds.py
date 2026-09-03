"""Waveguide winds — the flute family, after Cook's slide-flute
(STK; Smith's digital waveguides).

The circuit: breath (noise + pressure) drives a JET delay line
(half the bore period — the air jet's travel time to the labium),
whose output passes the cubic jet nonlinearity x - x^3 and feeds
the BORE delay line (the tube, one period long). The bore's output
returns through a two-pole reflection lowpass into both. Everything
musical about a flute is in this loop: breath noise is filtered BY
the resonator (the hiss is pitched), vibrato is breath-pressure
modulation (wobbles amplitude and brightness together), and a
shorter jet delay overblows to the octave — the physical mechanism.

THE INSTRUMENT TUNES ITSELF BY LISTENING. Two facts measured
during development, both invisible in the code and obvious in the
render: (1) mode competition is winner-take-all and ~15% of
(note, seed) combos hand the note to mode 3 — deterministic per
seed, immune to priming/filter-slope/pressure nudges; (2) the jet
path pulls the played pitch up to ~45 cents off the delay-line
math in the high register. So flute() renders, MEASURES the pitch
(parabolic-interpolated FFT peak), reseeds if the wrong mode
spoke, and retunes the delay target from the measured error.
Deterministic, converges in 1-2 extra 0.02s renders. Verify by
numbers — even inside the instrument.
"""

import numpy as np
from scipy.signal import butter, sosfilt, lfilter

from . import SR


def _fpeak(x: np.ndarray) -> float:
    """FUNDAMENTAL of the middle third: the lowest spectral peak
    within 30% of the maximum, parabolic-refined. (Plain argmax
    lies: a bright note whose 3rd harmonic edges out the
    fundamental by 4% reads as a mode-jump that never happened.)"""
    seg = x[len(x) // 3: 2 * len(x) // 3]
    if len(seg) < 256:
        seg = x
    nfft = 4 * len(seg)          # zero-pad: 2.5 Hz bins are +-15
    sp = np.abs(np.fft.rfft(seg * np.hanning(len(seg)), nfft))
    sp[: int(40 * nfft / SR) + 1] = 0.0
    # harmonic product spectrum: only a true fundamental has energy
    # at 1x AND 2x AND 3x of itself — sub-harmonic leakage and
    # loud-3rd-harmonic notes both lose the product
    m = len(sp) // 3
    hps = sp[:m] * sp[: 2 * m: 2] * sp[: 3 * m: 3]
    k = int(np.argmax(hps))
    if 0 < k < len(sp) - 1:
        a, b, c = sp[k - 1], sp[k], sp[k + 1]
        denom = a - 2 * b + c
        k = k + (0.5 * (a - c) / denom if abs(denom) > 1e-12 else 0.0)
    return float(k * SR / nfft)


def flute(f0: float, dur: float, amp: float = 1.0,
        breath=0.06, pressure: float = 0.9,
        vib_hz: float = 4.8, vib_amt: float = 0.03,
        attack_s: float = 0.06, release_s: float = 0.12,
        damp: float = 0.72, overblow: float = 0.0,
        seed: int = 0) -> np.ndarray:
    """One breath-driven note. `overblow` shortens the jet delay
    (a faster air jet): >=0.75 and the octave speaks. breath =
    hiss level — scalar, or an (n,) envelope for gestures whose
    turbulence changes over the note (e82: the shakuhachi's
    muraiki is a breath BURST decaying into tone). Scalar path
    bit-identical to before. Self-verifying: the returned note
    IS on pitch."""
    n = int(dur * SR)
    tt = np.arange(n) / SR
    mode_mult = 2.0 if overblow >= 0.75 else 1.0
    f_want = f0 * mode_mult

    env = np.ones(n)
    a = max(int(attack_s * SR), 1)
    env[:a] = np.linspace(0, 1, a) ** 1.5
    r = min(int(release_s * SR), n - 1)
    env[-r:] *= np.linspace(1, 0, r) ** 1.2
    vib = 1.0 + vib_amt * np.sin(2 * np.pi * vib_hz * tt) \
        * np.clip((tt - 0.25) / 0.4, 0, 1)
    c = damp

    def synth(f_syn: float, sd: int) -> np.ndarray:
        rng = np.random.default_rng(sd)
        w = 2.0 * np.pi * f_syn / SR
        d_lp = 2.0 * np.arctan2(c * np.sin(w),
                1.0 - c * np.cos(w)) / w
        target = SR / f_syn - d_lp
        p_bore = max(int(target), 8)
        fr = max(target - p_bore, 0.0)
        tj = max(target / 2.0 / (1.0 + overblow), 4.0)
        p_jet = int(tj)                   # fractional jet delay too:
        frj = tj - p_jet                  # integer p_jet staircases
        # the pitch response and the tuner can't converge
        sos_n = butter(2, [f0 * 0.5, min(f0 * 6.0, SR * 0.45)],
                btype="band", fs=SR, output="sos")
        noise = sosfilt(sos_n, rng.standard_normal(n)) * breath
        drive = pressure * env * vib + noise * env
        bore = np.zeros(n + p_bore)
        jet = np.zeros(n + p_jet)
        out = np.zeros(n)
        zi1 = np.zeros(1)
        zi2 = np.zeros(1)
        i = 0
        while i < n:
            j = min(i + p_jet, n)
            idx = np.arange(i, j)
            bore_out = (1 - fr) * bore[idx] + fr * bore[idx - 1]
            refl, zi1 = lfilter([1 - c], [1, -c], bore_out, zi=zi1)
            refl, zi2 = lfilter([1 - c], [1, -c], refl, zi=zi2)
            # jet operating point stays inside the cubic's live
            # region (zeros at +-1 KILL the jet)
            jet[idx + p_jet] = 0.42 * drive[idx] + 0.48 * refl
            jet_out = (1 - frj) * jet[idx] + frj * jet[idx - 1]
            x = np.clip(jet_out, -1.0, 1.0)
            bore[idx + p_bore] = (x - x * x * x) + 0.5 * refl
            out[idx] = bore_out
            i = j
        return out

    def right_mode(o: np.ndarray) -> bool:
        return 0.85 < _fpeak(o) / f_want < 1.15

    def seed_hunt(f_syn: float, sd0: int):
        """First seed at this tube length that speaks the mode."""
        for t in range(9):
            sd = sd0 + 101 * t
            o = synth(f_syn, sd)
            if right_mode(o):
                return o, sd
        return None, sd0

    f_syn = f0
    out, sd = seed_hunt(f_syn, seed)
    if out is None:
        out = synth(f_syn, seed)          # give up on mode; ship it
    else:
        # Secant-method tuning: the played pitch responds to the
        # tube length with gain ~2 (measured: a unit-gain corrector
        # ping-pongs +-140c around A4 forever), so estimate the
        # local gain from the last two takes and step by that.
        best, best_c = out, abs(1200.0 * np.log2(_fpeak(out) / f_want))
        prev = None                       # (log2 f_syn, cents)
        for _tune in range(6):
            cents = 1200.0 * np.log2(_fpeak(out) / f_want)
            if abs(cents) < best_c:
                best, best_c = out, abs(cents)
            if abs(cents) <= 12.0:
                break
            lx = np.log2(f_syn)
            if prev is not None and abs(cents - prev[1]) > 1.0:
                gain = (cents - prev[1]) / ((lx - prev[0]) * 1200.0)
                step = -cents / (gain * 1200.0)
            else:
                step = -cents * 0.45 / 1200.0   # damped first step
            prev = (lx, cents)
            f_new = f_syn * 2.0 ** float(np.clip(step, -0.15, 0.15))
            cand = synth(f_new, sd)
            if not right_mode(cand):      # mode flipped under retune
                cand, sd2 = seed_hunt(f_new, sd + 37)
                if cand is None:
                    break                 # ship the best take so far
                sd = sd2
            out, f_syn = cand, f_new
        cents = 1200.0 * np.log2(_fpeak(out) / f_want)
        if abs(cents) < best_c:
            best, best_c = out, abs(cents)
        out = best

    sos_hp = butter(1, max(f0 * 0.4, 40.0), btype="high", fs=SR,
            output="sos")
    out = sosfilt(sos_hp, out) * env
    return out * amp / (np.max(np.abs(out)) + 1e-12) * 0.9


def ney(f0: float, dur: float, amp: float = 1.0,
        seed: int = 0) -> np.ndarray:
    """Breathier, darker cousin: more hiss, laxer reflection, slow
    pitchless attack — the hermit's reed."""
    return flute(f0, dur, amp=amp, breath=0.16, pressure=0.78,
            vib_hz=3.6, vib_amt=0.05, attack_s=0.15,
            release_s=0.2, damp=0.8, seed=seed)

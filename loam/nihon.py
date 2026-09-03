"""loam.nihon — Japan. Voices of the sankyoku and beyond.

Born session 81, on operator direction: "take it over to Japan."
The shamisen turned out to be waiting inside instruments loam
already owned:

  - SAWARI is jawari physics. The buzzing ridge under the
    shamisen's lowest string is the same one-sided barrier as
    the sitar bridge fdpluck2 has carried since e48 — Japan and
    India discovered the same trick: give the string something
    to slap, and it sings brighter than it was plucked.
  - The BACHI SNAP is e80's `click` writ large. The weighted
    plectrum's contact transient, wider-band and harder than a
    wire mizrab.
  - The DON is new here: the bachi strikes the skin head and
    the string in one gesture, so every stroke carries a short
    membrane thump under the note — placed, like the click, at
    the string's own speak time.

shakuhachi and friends will join this module as the winds are
developed.
"""

import numpy as np
from scipy.signal import butter, sosfilt

from . import SR
from .fdstring import fdpluck2, _speak
from .winds import flute, reedpipe, _fpeak
from .membrane import fddrum
from .modal import strike as _mstrike

_thump_cache = {}


def _don(dur_s=0.14, f1=175.0, f2=282.0):
    """The bachi hitting the hide: two fast-decaying head modes
    plus a breath of bandpassed noise. Deterministic."""
    key = (dur_s, f1, f2)
    if key not in _thump_cache:
        n = int(dur_s * SR)
        t = np.arange(n) / SR
        env = np.exp(-t / 0.030)
        d = (np.sin(2 * np.pi * f1 * t) * 1.0
             + np.sin(2 * np.pi * f2 * t) * 0.45) * env
        rng = np.random.default_rng(0xD0)
        nz = rng.standard_normal(n) * np.exp(-t / 0.012)
        nz = sosfilt(butter(2, [120.0, 900.0], btype="bandpass",
                fs=SR, output="sos"), nz)
        d = d + 0.8 * nz
        _thump_cache[key] = d / (np.abs(d).max() + 1e-12)
    return _thump_cache[key]


def shamisen(f0: float, dur: float = 1.6, amp: float = 1.0,
        sawari: float = 0.0, snap: float = 0.5,
        thump: float = 0.45, pick: float = 0.76,
        N: int = 0) -> np.ndarray:
    """One bachi stroke. `sawari` 0..1 brings the barrier ridge
    up under the string (0 = clean string, barrier out of reach;
    1 = full buzz — use on the lowest string, as built). `snap`
    is the bachi contact click (fdpluck2's click, wider band),
    `thump` the skin don; both land at the string's speak time,
    because the bachi hits everything in one gesture. Silk/nylon
    string: low stiffness, faster damping than the sitar."""
    # sawari->barrier depth is exponential: the buzz only wakes
    # below gcurve ~0.06 (measured: gc 0.03 lifts 2 kHz+ energy
    # +7 dB and moves the centroid 600 -> 1957 Hz; gc 0.2, the
    # sitar's own setting, is barely audible on this softer
    # string). 0.9 parks the ridge out of reach.
    s = min(max(sawari, 0.0), 1.0)
    gc = 0.9 * (0.03 / 0.9) ** s
    v = fdpluck2(f0, dur, amp=1.0, kappa=0.12, sig0=1.1,
            sig1=1e-4, pick=pick, zone=0.12, gcurve=gc,
            K=2.5e9, alpha=1.3, split=0.004, kc=6e4,
            angle=0.6, click=snap * 0.55,
            click_band=(2500.0, 11000.0), click_s=0.006, N=N)
    if thump > 0.0:
        d = _don() * (thump * 0.9)
        i0 = int(_speak(v) * SR)
        n = min(len(d), len(v) - i0)
        v[i0:i0 + n] += d[:n]
    return v / (np.abs(v).max() + 1e-12) * (0.9 * amp)


# honchoshi: root, fourth, octave — the shamisen's home tuning
def honchoshi(root_hz: float):
    return (root_hz, root_hz * 4.0 / 3.0, root_hz * 2.0)


# hirajoshi: the koto's home tuning as semitone offsets from the
# root (D: D Eb G A Bb)
HIRAJOSHI = (0, 1, 5, 7, 8)


# suikinkutsu pot modes: (freq_hz, amp, t60_s) — one hollow
# Helmholtz-ish body mode plus three ceramic cavity rings
SUIKIN_MODES = ((360.0, 0.9, 0.50), (1150.0, 1.0, 0.35),
        (1720.0, 0.8, 0.28), (2310.0, 0.55, 0.20))


def suikinkutsu_ir(modes=SUIKIN_MODES, dur: float = 1.4,
        detune: float = 0.004) -> np.ndarray:
    """The buried pot as a stereo impulse response: a sum of
    decaying sinusoids at the cavity modes, each channel's
    modes detuned +-detune/2 (two listening points on one pot —
    decorrelation without a second pot). Deterministic."""
    n = int(dur * SR)
    t = np.arange(n) / SR
    ir = np.zeros((n, 2))
    for ch, dt in ((0, -0.5 * detune), (1, 0.5 * detune)):
        for f, a, t60 in modes:
            fc = f * (1.0 + dt)
            ir[:, ch] += a * np.sin(2 * np.pi * fc * t) \
                * np.exp(-6.91 * t / t60)
    a_n = max(int(0.001 * SR), 1)
    ir[:a_n] *= np.linspace(0.0, 1.0, a_n)[:, None]
    return ir / (np.abs(ir).max() + 1e-12)


def waterdrop(f0: float, chirp: float = 1.7, damp: float = 0.75,
        tick: float = 0.25) -> np.ndarray:
    """One drop striking the pool: the Minnaert bubble (the
    pitched, RISING blip) plus a 2 ms broadband tick — the
    impact itself. The tick matters for the pot: a 900-2400 Hz
    bubble carries no energy at a ~360 Hz body mode, so without
    the impact the hollow of the chamber stays silent (e84's
    register rule: excitation must reach the resonance you
    claim). Deterministic per f0."""
    from .texture import bubble
    b = bubble(f0, chirp=chirp, damp=damp)
    n = max(len(b), int(0.012 * SR))
    v = np.zeros(n)
    v[:len(b)] += b
    rng = np.random.default_rng(int(f0 * 1000.0) & 0x7FFFFFFF)
    tk = rng.standard_normal(int(0.002 * SR))
    tk = sosfilt(butter(2, [200.0, 4500.0], btype="bandpass",
            fs=SR, output="sos"), tk)
    tk *= np.linspace(1.0, 0.0, len(tk)) ** 2
    v[:len(tk)] += tick * tk / (np.abs(tk).max() + 1e-12)
    return v


def koto(f0: float, dur: float = 2.8, amp: float = 1.0,
        tsume: float = 0.6, bend_c: float = 0.0,
        bend_at: float = 0.30, bend_rise: float = 0.22,
        vib_c: float = 0.0, vib_hz: float = 4.2,
        body: float = 0.5, N: int = 0) -> np.ndarray:
    """One tsume pluck on the paulownia zither — the shamisen's
    clean-string cousin (barrier parked out of reach, no buzz),
    longer ring, hard pick close to the bridge:

      - `tsume`: the ivory pick's contact click, harder and
        higher than the bachi snap;
      - OSHIDE (`bend_c` cents, `bend_at`, `bend_rise`): the
        left hand presses the string behind the bridge AFTER
        the pluck and the sounding pitch rises — written as a
        smoothstep warp of the decaying note, because that is
        the honest bend (same stance as the shakuhachi scoop);
      - `vib_c`/`vib_hz`: left-hand vibrato entering ~0.5 s;
      - `body` 0..1: the hollow paulownia box — two parallel
        resonant bands (~230 and ~560 Hz) added to the direct
        string.

    Deterministic (no seed: the FD string and the click are)."""
    pad = 1.0 + max(bend_c, 0.0) / 1200.0 * 0.8 + 0.06
    v = fdpluck2(f0, dur * pad, amp=1.0, kappa=0.18, sig0=0.55,
            sig1=8e-5, pick=0.86, zone=0.10, gcurve=0.9,
            K=2.5e9, alpha=1.3, split=0.005, kc=8e4, angle=0.55,
            click=tsume * 1.2, click_band=(3500.0, 10500.0),
            click_s=0.005, N=N)
    n = int(dur * SR)
    t = np.arange(n) / SR
    if bend_c != 0.0 or vib_c > 0.0:
        x = np.clip((t - bend_at) / bend_rise, 0.0, 1.0)
        cents = (bend_c * x * x * (3.0 - 2.0 * x)
                 + vib_c * np.sin(2.0 * np.pi * vib_hz * t)
                 * np.clip((t - 0.5) / 0.4, 0.0, 1.0))
        ratio = 2.0 ** (cents / 1200.0)
        idx = np.cumsum(ratio)
        idx -= idx[0]
        idx = np.clip(idx, 0.0, len(v) - 1.0)
        v = np.interp(idx, np.arange(len(v), dtype=float), v)
    else:
        v = v[:n]
    if body > 0.0:
        # zero-phase bands: a causal bandpass adds ~90 deg out
        # of phase and CANCELS instead of boosting (measured
        # -1.3 dB where the design said +5)
        from scipy.signal import sosfiltfilt
        b1 = sosfiltfilt(butter(2, [190.0, 270.0],
                btype="bandpass", fs=SR, output="sos"), v)
        b2 = sosfiltfilt(butter(2, [480.0, 640.0],
                btype="bandpass", fs=SR, output="sos"), v)
        v = v + body * (1.4 * b1 + 0.9 * b2)
    r = int(0.02 * SR)
    v[-r:] *= np.linspace(1.0, 0.0, r)
    return v / (np.abs(v).max() + 1e-12) * (0.9 * amp)


def _if_track(x: np.ndarray, f0: float) -> np.ndarray:
    """Instantaneous-frequency track near a KNOWN f0 (inline
    twin of ruler.if_pitch, same stance as _speak: the
    instrument listens to itself without the ruler kit).
    Spectral-peak detectors scatter +-100 cents on breathy
    signals — the noise in any honest search band out-competes
    the tone in short windows. The analytic phase of the
    zero-phase-narrowband-filtered signal does not care."""
    from scipy.signal import sosfiltfilt, hilbert
    sos = butter(4, [f0 * 0.93, f0 * 1.075], btype="bandpass",
            fs=SR, output="sos")
    nbf = sosfiltfilt(sos, x)
    ph = np.unwrap(np.angle(hilbert(nbf)))
    return np.diff(ph) * SR / (2.0 * np.pi)


def shakuhachi(f0: float, dur: float, amp: float = 1.0,
        muraiki: float = 0.5, scoop: float = 40.0,
        yuri_hz: float = 2.8, yuri_c: float = 18.0,
        breathiness: float = 0.10, komibuki: float = 0.0,
        komi_hz: float = 5.5, komi_c: float = 5.0,
        seed: int = 0) -> np.ndarray:
    """One breath on the bamboo. Built on the self-tuning
    waveguide flute plus a GESTURE LAYER, because the gestures
    that make a shakuhachi a shakuhachi are pitch motions the
    stationary bore cannot make (measured: jet pressure does
    not bend the sustained pitch at all — the scoop cannot come
    from blowing harder):

      - muraiki: a burst of turbulent breath decaying into tone
        (flute's breath input as an envelope, ~300 ms fall);
      - meri approach (`scoop`, cents): the note starts flat
        and slides up into pitch over ~280 ms, via a time-warp
        resample of the tuned note;
      - yuri (`yuri_hz`, `yuri_c`): slow deep pitch vibrato,
        entering after ~0.9 s, same warp; a small in-loop
        pressure vibrato keeps amplitude and brightness
        breathing with it;
      - KOMIBUKI (`komibuki` 0..1 depth, `komi_hz`, `komi_c`):
        pulsed breath — rhythmic diaphragm pushes on the held
        tone (Tsuru no Sugomori's crane voice). Three coupled
        layers per push, entering after ~0.35 s: an amplitude
        pulse (floor 1-komibuki between pushes), a burst of
        direct-radiation hiss riding each push, and a small
        written pitch flutter (`komi_c` cents, mean-removed so
        the sustain center holds) — written into the warp, not
        blown, because jet pressure provably cannot bend this
        bore's pitch.

    The warp also folds in the note's measured residual tuning
    error (the waveguide tuner promises ~12 cents; here the
    sustain is re-measured and corrected, so the shipped
    sustain sits within a few cents). Deterministic per seed."""
    # PRE-ROLL THE BORE: the waveguide spends its first ~0.25 s
    # (seed-dependent, sometimes 0.5 s) in mode-settling fog —
    # no stable tone, so no gesture written there is heard or
    # measurable. Render 0.5 s extra, discard it: the shipped
    # note has tone from sample zero, and the attack becomes
    # the gesture layer's fade plus the muraiki hiss — a breath
    # blooming into tone, which is what a shakuhachi attack IS.
    PRE = 0.5
    padf = 1.06
    nb = int((dur * padf + PRE) * SR)
    tb = np.arange(nb) / SR
    breath = breathiness + 0.5 * muraiki * np.exp(
            -np.maximum(tb - PRE, 0.0) / 0.30)
    base = flute(f0, dur * padf + PRE, amp=1.0, breath=breath,
            pressure=0.86, vib_hz=yuri_hz, vib_amt=0.012,
            attack_s=0.08, release_s=0.22, damp=0.80, seed=seed)
    base = base[int(PRE * SR):]
    nb = len(base)
    # Contour correction, wander kept. The bore drifts on two
    # timescales: a seed-dependent early sharpness that outlasts
    # even the pre-roll (measured +21c at 0.05-0.35 s on one C5
    # seed — enough to eat a written -40c scoop exactly), and a
    # slow +-25c wander. The instrument measures its own IF
    # drift at 0.25 s knots and writes the INVERSE into the
    # warp: slower-than-~0.3s drift is corrected (so the written
    # contour is the played contour), faster wander is below the
    # knot rate and survives — the bamboo's life.
    inst_b = _if_track(base, f0)
    kc, kv = [], []
    c = 0.15
    while c < dur * padf - 0.12:
        seg = inst_b[int((c - 0.15) * SR):int((c + 0.15) * SR)]
        kv.append(float(np.clip(1200.0 * np.log2(
                np.median(seg) / f0), -80.0, 80.0)))
        kc.append(c)
        c += 0.25
    n = int(dur * SR)
    t = np.arange(n) / SR
    drift = np.interp(t, kc, kv)
    # komibuki pulse train: (0.5-0.5cos)^2 peaks once per period
    # (mean 3/8), gated in after the attack settles
    kg = np.clip((t - 0.35) / 0.30, 0.0, 1.0) * (komibuki > 0.0)
    pul = (0.5 - 0.5 * np.cos(2.0 * np.pi * komi_hz * t)) ** 2
    cents = (-scoop * np.exp(-t / 0.45)
             + yuri_c * np.sin(2.0 * np.pi * yuri_hz * t)
             * np.clip((t - 0.9) / 0.7, 0.0, 1.0)
             + komi_c * (pul - 0.375) * kg
             - drift)
    ratio = 2.0 ** (cents / 1200.0)
    idx = np.cumsum(ratio)
    idx -= idx[0]
    out = np.interp(idx, np.arange(nb, dtype=float), base)
    if muraiki > 0.0:
        # direct-radiation hiss: the mouth noise that never
        # enters the bore (the jet saturates — pushing breath
        # through the nonlinearity gained 1.9 dB where the ear
        # wants a gust). Same stance as the click and the don.
        rngm = np.random.default_rng(seed * 77 + 5)
        hiss = rngm.standard_normal(n)
        # band floor at 2 kHz with steep skirts: the gust must
        # stay out of the melody register (a hiss floor inside
        # the tone's band pulls any IF median toward the band
        # center — it cost a written -26c slide its measurement
        # before it cost anything musical)
        hiss = sosfilt(butter(3, [2000.0, 8000.0],
                btype="bandpass", fs=SR, output="sos"), hiss)
        hiss = hiss / (np.abs(hiss).max() + 1e-12)
        out = out + hiss * np.exp(-t / 0.30) * (0.30 * muraiki
                * np.abs(out).max())
    if komibuki > 0.0:
        ref = np.abs(out).max()
        # the diaphragm push: tone dips to (1-komibuki) between
        # pushes, and each push carries its own turbulence
        # (direct radiation, same stance as the muraiki gust)
        out = out * (1.0 - komibuki * kg * (1.0 - pul))
        rngk = np.random.default_rng(seed * 91 + 7)
        kh = sosfilt(butter(3, [2500.0, 9000.0], btype="bandpass",
                fs=SR, output="sos"), rngk.standard_normal(n))
        kh = kh / (np.abs(kh).max() + 1e-12)
        out = out + kh * (0.10 * komibuki * ref) * kg * pul ** 2
    na = int(0.06 * SR)
    out[:na] *= np.linspace(0.0, 1.0, na) ** 1.5
    r = int(0.03 * SR)
    out[-r:] *= np.linspace(1.0, 0.0, r)
    return out / (np.abs(out).max() + 1e-12) * (0.9 * amp)


def hichiriki(f0: float, dur: float, amp: float = 1.0,
        embai: float = 120.0, yuri_hz: float = 3.2,
        yuri_c: float = 0.0, seed: int = 0) -> np.ndarray:
    """One cry of the flattened cypress reed. reedpipe() (e84's
    valve-on-a-quarter-wave-bore) plus the hichiriki's three
    signatures:

      - EMBAI (`embai`, cents): the famous wide approach glide —
        the note starts far flat and pours up into pitch over
        ~0.35 s. Same warp-resample stance as the shakuhachi's
        meri scoop, but twice the depth: the hichiriki's large
        soft reed lets the player bend further than any flute
        embouchure.
      - The NASAL FORMANT: the short cylindrical bore radiates a
        strong presence band around 0.9-1.9 kHz; a bandpass
        emphasis is added to the direct sound.
      - REED WARMTH: the raw valve model is nearly square-wave
        odd-pure (+50 dB); a touch of asymmetric waveshaping puts
        the even partials back (a real reed never closes with
        perfect symmetry).

    yuri enters after ~0.8 s. Deterministic per seed."""
    PRE = 0.2                     # the reed speaks fast; a short
    padf = 1.05                   # pre-roll clears the lock-in
    base = reedpipe(f0, dur * padf + PRE, amp=1.0, breath=0.02,
            pressure=0.92, vib_hz=yuri_hz, vib_amt=0.010,
            attack_s=0.05, release_s=0.15, seed=seed)
    base = base[int(PRE * SR):]
    nb = len(base)
    n = int(dur * SR)
    t = np.arange(n) / SR
    cents = (-embai * np.exp(-t / 0.35)
             + yuri_c * np.sin(2.0 * np.pi * yuri_hz * t)
             * np.clip((t - 0.8) / 0.6, 0.0, 1.0))
    idx = np.cumsum(2.0 ** (cents / 1200.0))
    idx -= idx[0]
    out = np.interp(idx, np.arange(nb, dtype=float), base)
    out = out + 0.12 * out * out          # reed asymmetry: evens
    sos_dc = butter(1, max(f0 * 0.4, 40.0), btype="highpass",
            fs=SR, output="sos")
    out = sosfilt(sos_dc, out)
    sos_fm = butter(2, [900.0, 1900.0], btype="bandpass", fs=SR,
            output="sos")
    out = out + 1.6 * sosfilt(sos_fm, out)
    na = int(0.04 * SR)
    out[:na] *= np.linspace(0.0, 1.0, na) ** 1.5
    r = int(0.05 * SR)
    out[-r:] *= np.linspace(1.0, 0.0, r)
    return out / (np.abs(out).max() + 1e-12) * (0.9 * amp)


# The sho's aitake cluster chords (e85). Verified against the
# literature: the four Category-1 fundamentals (kotsu A4, ichi B4,
# bo D5, otsu E5) and their shared two-octave collection
# A4-B4-D5-E5-A5-B5-D6-E6-F#6, plus gyo and the sojo variant of ju
# exactly as published (Momii, MTO 26.4). The Category-1 voicings
# below are COLLECTION-CONSTRAINED REALIZATIONS — fundamental at
# the bottom, the gyo-like cluster above — because every source
# keeps its full chord chart inside an image. Named, not guessed:
# see LOG e85.
AITAKE = {
    "kotsu": [69, 76, 81, 83, 86, 88],
    "ichi":  [71, 76, 81, 83, 86, 90],
    "bo":    [74, 81, 83, 86, 88, 90],
    "otsu":  [76, 81, 83, 86, 88, 90],
    "gyo":   [81, 83, 86, 88, 90],
    "ju_so": [79, 81, 83, 86, 88],
}


def sho(midis, dur: float, amp: float = 1.0, floor: float = 0.25,
        bright: float = 0.45, nharm: int = 9, edge_s: float = 0.35,
        seed: int = 0) -> np.ndarray:
    """One breath of the mouth organ: an aitake cluster swelling
    through an arch and subsiding. Free-reed-with-resonator tone
    by additive recipe (a per-sample reed ODE at 15 pipes is not a
    price this library pays for a steady tone): harmonics fall
    h^-2.2, and each harmonic rides env^(1 + bright*(h-1)) — the
    reed BRIGHTENS as pressure rises, so the swell opens the
    spectrum, not just the level. The arch never reaches zero
    (`floor`): the sho breathes in and out without stopping. The
    first and last `edge_s` are a FIXED-TIME equal-power turn
    (sin^2/cos^2 from silence), whatever the breath's length —
    turning the breath takes the same moment on a short chord as
    a long one, and two overlapped breaths sum to a level floor
    with the trough centered on the change. Reeds hold within
    +-2 cents; pipes sit slightly apart in the image. Stereo.
    Deterministic per seed."""
    n = int(dur * SR)
    t = np.arange(n) / SR
    arch = floor + (1.0 - floor) * np.sin(
            np.pi * np.clip(t / dur, 0.0, 1.0)) ** 0.7
    e_in = np.sin(0.5 * np.pi * np.clip(t / edge_s, 0.0, 1.0)) ** 2
    e_out = np.sin(0.5 * np.pi * np.clip((dur - t) / edge_s,
            0.0, 1.0)) ** 2
    env = arch * e_in * e_out
    rng = np.random.default_rng(seed)
    out = np.zeros((n, 2))
    for m in midis:
        f = 440.0 * 2.0 ** ((m - 69) / 12.0)
        f *= 2.0 ** (rng.uniform(-2.0, 2.0) / 1200.0)
        pan = float(np.clip((m - 80) * 0.03, -0.22, 0.22)
                    + rng.uniform(-0.05, 0.05))
        v = np.zeros(n)
        for h in range(1, nharm + 1):
            if f * h >= SR * 0.45:
                break
            v += (h ** -1.7) * np.sin(
                    2.0 * np.pi * f * h * t
                    + rng.uniform(0, 2 * np.pi)) \
                * env ** (1.0 + bright * (h - 1))
        out += np.stack([v * (0.5 - 0.5 * pan),
                         v * (0.5 + 0.5 * pan)], axis=1)
    hiss = np.stack([rng.standard_normal(n),
                     rng.standard_normal(n)], axis=1)
    sos_h = butter(2, [2000.0, 6000.0], btype="bandpass", fs=SR,
            output="sos")
    hiss = sosfilt(sos_h, hiss, axis=0)
    out += hiss * (0.006 * env[:, None])
    return out / (np.abs(out).max() + 1e-12) * (0.9 * amp)


def ryuteki(f0: float, dur: float, amp: float = 1.0,
        flip_at: float = -1.0, graces=(),
        breath: float = 0.13, seed: int = 0) -> np.ndarray:
    """One breath of the dragon flute (e86). The waveguide flute
    voiced breathy, plus the ryuteki's gestures:

      - REGISTER FLIP (`flip_at`, seconds): the signature move —
        the note starts fukura (the fundamental) and flips to
        seme (the overblown OCTAVE, same fingering) mid-breath.
        Two full renders of the same bore, low mode and
        overblown, crossfaded in ~80 ms: the physical gesture is
        a jet-speed jump, and flute()'s `overblow` IS that jet.
        Negative = no flip.
      - FINGER FLICKS (`graces`, seconds): the finger re-strikes
        a hole in ~50 ms — a ~90-cent gaussian pit in the warp
        AND a ~6 dB amplitude notch, because the strike briefly
        kills the resonance. The finger is part of the model
        (e81's hand lesson, wind edition) — and the notch is
        what a ruler can hold: at this voice's breathiness a
        bare 50 ms pitch dip is below honest measurability
        (narrowband noise fluctuates on exactly that timescale).
      - The breath is high and stays audible: the in-bore noise
        is pitched by the resonator (the ryuteki's hiss sings
        the note), and the attack carries a mild gust.

    Deterministic per seed. Mono."""
    n = int(dur * SR)
    t = np.arange(n) / SR
    tb = np.arange(int(dur * SR)) / SR
    gust = breath + 0.30 * np.exp(-tb / 0.18)

    def _center(v, f_want):
        # constant self-correction, e82's stance without the
        # knots: the bore is stable, only the residual offset
        # needs folding back
        c = float(np.clip(1200.0 * np.log2(np.median(
                _if_track(v, f_want)[int(0.4 * SR):
                                     int((dur - 0.25) * SR)])
                / f_want), -45.0, 45.0))
        ii = np.arange(n) * 2.0 ** (-c / 1200.0)
        return np.interp(ii, np.arange(len(v), dtype=float), v)

    lo = _center(flute(f0, dur, amp=1.0, breath=gust,
            pressure=0.88, vib_hz=4.0, vib_amt=0.010,
            attack_s=0.10, release_s=0.18, damp=0.78,
            seed=seed), f0)
    if flip_at > 0.0:
        hi = _center(flute(f0, dur, amp=1.0, breath=gust,
                pressure=0.90, vib_hz=4.0, vib_amt=0.010,
                attack_s=0.06, release_s=0.18, damp=0.78,
                overblow=0.9, seed=seed + 1), 2.0 * f0)
        xf = 1.0 / (1.0 + np.exp(-(t - flip_at) / 0.020))
        out = lo * (1.0 - xf) + hi * xf
    else:
        out = lo
    cents = np.zeros(n)
    for tg in graces:
        cents -= 90.0 * np.exp(-((t - tg) / 0.025) ** 2)
    if graces:
        idx = np.cumsum(2.0 ** (cents / 1200.0))
        idx -= idx[0]
        out = np.interp(idx, np.arange(n, dtype=float), out)
        for tg in graces:
            out *= 1.0 - 0.6 * np.exp(-((t - tg) / 0.020) ** 2)
    r = int(0.03 * SR)
    out[-r:] *= np.linspace(1.0, 0.0, r)
    return out / (np.abs(out).max() + 1e-12) * (0.9 * amp)


# ---- the gagaku percussion (e87) ---------------------------------
# Three time-keepers, deterministic and cached: the pattern is the
# music, so the voices are single renders reused.
SHOKO = [(1.0, 1.0, 1.0), (1.83, 0.60, 0.75), (2.66, 0.75, 0.60),
         (3.56, 0.50, 0.50), (4.51, 0.35, 0.40),
         (5.42, 0.25, 0.32)]                    # flat bronze plate

_gk_cache = {}


def shoko(amp: float = 1.0) -> np.ndarray:
    """The small bronze gong: 'chin'. Flat-plate mode ratios,
    struck hard, ~1.3 s ring."""
    if "shoko" not in _gk_cache:
        v = _mstrike(1150.0, 1.3, SHOKO, amp=1.0, detune=2.0,
                rng=np.random.default_rng(0x5C), knock=0.04)
        _gk_cache["shoko"] = v / (np.abs(v).max() + 1e-12)
    return _gk_cache["shoko"] * amp


def kakko(amp: float = 1.0) -> np.ndarray:
    """The small tight drum: 'ka'. High-tension membrane, fast
    decay, struck off-center."""
    if "kakko" not in _gk_cache:
        v = fddrum(295.0, 0.30, amp=1.0, strike=(0.62, 0.0),
                width=0.12, sig0=24.0, sig1=3e-4, N=41)
        _gk_cache["kakko"] = v / (np.abs(v).max() + 1e-12)
    return _gk_cache["kakko"] * amp


def taiko(amp: float = 1.0, small: bool = False) -> np.ndarray:
    """The big hanging drum: 'DOU' (or the soft 'zun' pickup with
    small=True — same skin, lighter arm)."""
    key = "taiko_s" if small else "taiko"
    if key not in _gk_cache:
        v = fddrum(60.0, 1.5, amp=1.0,
                strike=(0.30 if small else 0.42, 0.0),
                width=0.30 if small else 0.22,
                sig0=4.5, sig1=1.5e-4, N=45)
        _gk_cache[key] = v / (np.abs(v).max() + 1e-12)
    return _gk_cache[key] * (amp * (0.45 if small else 1.0))

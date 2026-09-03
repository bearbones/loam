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
from .winds import flute, _fpeak

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
        breathiness: float = 0.10, seed: int = 0) -> np.ndarray:
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
        breathing with it.

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
    cents = (-scoop * np.exp(-t / 0.45)
             + yuri_c * np.sin(2.0 * np.pi * yuri_hz * t)
             * np.clip((t - 0.9) / 0.7, 0.0, 1.0)
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
    na = int(0.06 * SR)
    out[:na] *= np.linspace(0.0, 1.0, na) ** 1.5
    r = int(0.03 * SR)
    out[-r:] *= np.linspace(1.0, 0.0, r)
    return out / (np.abs(out).max() + 1e-12) * (0.9 * amp)

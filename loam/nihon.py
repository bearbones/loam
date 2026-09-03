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

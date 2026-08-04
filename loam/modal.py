"""Modal synthesis — struck and bowed resonators.

A struck object IS its mode table: each mode an exponentially
decaying sine at (ratio * f0), with its own amplitude and ring
time. Tables below come from the literature / measured analyses:

- BELL: measured modal analysis of a real bell (Risset-style table
  via the SuperCollider modal-synthesis study): inharmonic upper
  partials, hum below the strike tone.
- CHURCH_BELL: the classic western minor-third bell recipe —
  hum 0.5, prime 1, tierce 1.2, quint 1.5, nominal 2, plus rim
  partials. The tierce is why big bells sound sad.
- MARIMBA: bars are TUNED so the first three bending modes land at
  1:4:10 (xylophone: 1:3:6 — that 3rd partial is why xylophone
  sounds hollow/quinty and marimba sounds round).
- GLASS: wine-glass shell modes, near 1 : 2.32 : 4.25 : 6.63.
- WOOD: a few dense fast-dying modes — knock, not tone.
- ANVIL: designed, not measured (documented honestly): the clank
  is the fundamental body mode dying fast; the RING that carries
  across the smithy is a tight inharmonic pair of face modes
  (2.72 : 2.736 — beat rate 0.016*f0, ~3 Hz on a 200 Hz strike)
  with the longest ring in the table, plus sparse inharmonic
  uppers. Strike with bright>1 and knock for hammer contact.

Mode table format: (ratio, amp, ring) where ring scales t60.
"""

import numpy as np

from . import SR, ad_env

BELL = [(1.0, 1.0, 1.0), (2.0, 0.044, 0.205), (2.803, 0.891, 1.0),
        (3.871, 0.089, 0.196), (5.074, 0.794, 0.339),
        (7.81, 0.1, 0.047), (10.948, 0.281, 0.058),
        (14.421, 0.079, 0.047)]
CHURCH_BELL = [(0.5, 0.55, 1.0), (1.0, 1.0, 0.80), (1.2, 0.85, 0.72),
        (1.5, 0.32, 0.55), (2.0, 0.75, 0.40), (2.5, 0.18, 0.24),
        (2.67, 0.14, 0.20), (3.0, 0.22, 0.16), (4.0, 0.10, 0.10)]
MARIMBA = [(1.0, 1.0, 1.0), (4.0, 0.45, 0.35), (10.0, 0.18, 0.12),
        (17.3, 0.05, 0.06)]
XYLOPHONE = [(1.0, 1.0, 1.0), (3.0, 0.55, 0.30), (6.0, 0.22, 0.10),
        (10.5, 0.06, 0.05)]
GLASS = [(1.0, 1.0, 1.0), (2.32, 0.45, 0.75), (4.25, 0.18, 0.5),
        (6.63, 0.08, 0.3), (9.38, 0.03, 0.2)]
WOOD = [(1.0, 1.0, 1.0), (1.47, 0.7, 0.8), (2.09, 0.55, 0.6),
        (2.56, 0.4, 0.5), (3.35, 0.3, 0.4), (4.83, 0.2, 0.3)]
ANVIL = [(1.0, 0.65, 0.30), (1.51, 0.25, 0.22),
        (2.72, 1.0, 1.0), (2.736, 0.92, 1.0),
        (3.97, 0.35, 0.45), (5.42, 0.30, 0.38),
        (6.79, 0.18, 0.22), (8.21, 0.12, 0.14), (9.73, 0.07, 0.09)]


def strike(f0: float, t60: float, table, amp: float = 1.0,
        bright: float = 1.0, detune: float = 0.0,
        rng=None, knock: float = 0.0) -> np.ndarray:
    """Hit the object. `bright` tilts upper-mode energy (mallet
    hardness), `detune` (cents) doubles every mode into a slow-
    beating pair (cracked / ancient), `knock` adds the contact
    transient (filtered noise thump)."""
    dur = t60 * 1.1
    n = int(dur * SR)
    tt = np.arange(n) / SR
    m = np.zeros(n)
    for i, (ratio, a, ring) in enumerate(table):
        f = f0 * ratio
        if f >= SR * 0.45:
            break
        g = a * (bright ** i)
        decay = 6.91 / max(t60 * ring, 1e-3)      # ln(1000)
        ph = 0.0 if rng is None else rng.uniform(0, 2 * np.pi)
        mode = np.sin(2 * np.pi * f * tt + ph)
        if detune > 0.0:
            f2 = f * 2.0 ** (detune / 1200.0)
            mode = 0.5 * (mode + np.sin(2 * np.pi * f2 * tt + ph))
        m += g * mode * np.exp(-tt * decay)
    if knock > 0.0 and rng is not None:
        kn = int(0.012 * SR)
        m[:kn] += rng.standard_normal(kn) * ad_env(kn, 0.0005, 300.0) \
            * knock
    a_n = max(int(0.0015 * SR), 1)
    m[:a_n] *= np.linspace(0, 1, a_n)
    return m * amp / (np.max(np.abs(m)) + 1e-12) * 0.9


def bow(f0: float, dur: float, table, amp: float = 1.0,
        bright: float = 0.9, vib_hz: float = 0.0,
        rng=None) -> np.ndarray:
    """Rub it instead: same modes, slow swell in, held, released.
    Glass armonica when used on GLASS."""
    n = int(dur * SR)
    tt = np.arange(n) / SR
    m = np.zeros(n)
    vib = np.ones(n)
    if vib_hz > 0.0:
        vib += 0.004 * np.sin(2 * np.pi * vib_hz * tt) \
            * np.clip((tt - 0.4) / 0.6, 0, 1)
    for i, (ratio, a, ring) in enumerate(table):
        f = f0 * ratio
        if f >= SR * 0.45:
            break
        ph = 0.0 if rng is None else rng.uniform(0, 2 * np.pi)
        m += a * (bright ** i) * (0.5 + 0.5 * ring) \
            * np.sin(2 * np.pi * f * np.cumsum(vib) / SR + ph)
    swell = np.clip(tt / (dur * 0.35), 0, 1) ** 2
    rel = int(min(0.3 * dur, 0.8) * SR)
    env = swell.copy()
    env[-rel:] *= np.linspace(1, 0, rel) ** 1.3
    if rng is not None:
        breath = rng.standard_normal(n) * 0.006
        m += breath
    return m * env * amp / (np.max(np.abs(m * env)) + 1e-12) * 0.9


def gong(f0: float = 62.0, t60: float = 8.0, amp: float = 1.0,
        bloom_s: float = 1.1, bloom_amt: float = 0.8,
        seed: int = 0) -> np.ndarray:
    """Tam-tam. Real gongs BLOOM: nonlinear mode coupling cascades
    strike energy upward, so the shimmer arrives AFTER the thud
    (Chaigne/Touze nonlinear plates). Simulated three ways at once:
    a dense inharmonic low mode bed that speaks immediately; a high
    shimmer bed whose envelope RISES over bloom_s before decaying;
    and strike-dependent pitch flattening (big plates go momentarily
    sharp then settle). Verification: spectral centroid must RISE
    from strike into the bloom."""
    rng = np.random.default_rng(seed)
    dur = t60 * 1.05
    n = int(dur * SR)
    tt = np.arange(n) / SR
    # the cascade envelope: energy leaves the low modes and arrives
    # in the shimmer (real coupling conserves it; we fake the
    # transfer explicitly — without the low-bed dip the thud owns
    # the power spectrum and no bloom ever registers)
    rise = (tt / bloom_s) ** 2 * np.exp(1.0 - tt / bloom_s)
    rise = np.clip(rise, 0.0, 1.0)
    low = np.zeros(n)
    for _ in range(14):
        r = float(rng.uniform(1.0, 6.0)) ** 1.3
        f = f0 * r
        dec = 6.91 / (t60 * float(rng.uniform(0.5, 1.0)) / r ** 0.4)
        bend = 1.0 + 0.012 * np.exp(-tt * 6.0)     # settles flat
        g = float(rng.uniform(0.4, 1.0)) / r ** 0.5
        low += g * np.sin(2 * np.pi * f * bend * tt
                + float(rng.uniform(0, 6.28))) * np.exp(-tt * dec)
    m = low * (1.0 - 0.55 * bloom_amt * rise)
    for _ in range(24):
        r = float(rng.uniform(8.0, 40.0))
        f = f0 * r
        if f > SR * 0.42:
            continue
        dec = 6.91 / (t60 * float(rng.uniform(0.15, 0.45)))
        g = float(rng.uniform(0.3, 1.1)) / r ** 0.25
        m += bloom_amt * g * np.sin(2 * np.pi * f * tt
                + float(rng.uniform(0, 6.28))) \
            * rise * np.exp(-tt * dec)
    # the strike itself: brief dark thump
    kn = int(0.03 * SR)
    thump = rng.standard_normal(kn) * np.exp(-np.arange(kn) / (kn * 0.2))
    from scipy.signal import butter as _b, sosfilt as _s
    m[:kn] += _s(_b(2, 500, btype="low", fs=SR, output="sos"),
            thump) * 1.2
    a_n = max(int(0.002 * SR), 1)
    m[:a_n] *= np.linspace(0, 1, a_n)
    return m * amp / (np.max(np.abs(m)) + 1e-12) * 0.9

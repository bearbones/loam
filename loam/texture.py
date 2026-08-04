"""Procedural nature — rain, wind, fire, water (after Farnell's
"Designing Sound": the world's ambiences are statistics, not
recordings).

- rain: two Poisson populations — near droplets (downward chirped
  blips, individually audible) over a dense far wash (the hiss a
  million distant drops average into).
- wind: noise through slowly WANDERING resonances (random-walk
  center frequencies, cycle-safe) — the howl is the resonance,
  the gust is the level's low-frequency walk.
- fire: three populations again — crackle snaps (Poisson), low
  rumble (filtered noise, slow swell), and hiss flares (bursts
  with fast attack / slow release).
- bubble/bubbles: van den Doel's physically-based liquid sound.
  A bubble rings at its Minnaert resonance (f0 ~ 3/radius_m) as a
  damped sine whose frequency RISES as it decays — that upward
  chirp is the entire difference between "sine blip" and "water".
  bubbles() draws a population over a size distribution: fizz,
  glugs, and a rolling simmer bed.

All loop-safe: Poisson events wrap via modulo add, walks are
drift-corrected to close their loops.
"""

import numpy as np
from scipy.signal import butter, sosfilt

from . import SR, stereo


def _closed_walk(n: int, rng, smooth_hz: float = 0.5) -> np.ndarray:
    """Random walk that ends where it started (loop-safe), roughly
    band-limited to smooth_hz."""
    w = np.cumsum(rng.standard_normal(n))
    w -= np.linspace(w[0], w[-1], n)          # close the loop
    sos = butter(2, max(smooth_hz, 0.05), btype="low", fs=SR,
            output="sos")
    warm = n // 4
    w = sosfilt(sos, np.concatenate([w[-warm:], w]))[warm:]
    m = np.max(np.abs(w)) + 1e-12
    return w / m


def rain(loop_s: float, density: float = 14.0, near: float = 0.5,
        bright: float = 0.5, seed: int = 0) -> np.ndarray:
    """density = near-droplets/sec; near = their level over the
    far wash; bright tilts the wash (tin roof vs soil)."""
    rng = np.random.default_rng(seed)
    n = int(loop_s * SR)
    out = np.zeros((n, 2))
    lo, hi = 1200 + 2500 * bright, 6500 + 5500 * bright
    sos_w = butter(2, [lo, hi], btype="band", fs=SR, output="sos")
    wash = np.stack([sosfilt(sos_w, rng.standard_normal(n)),
            sosfilt(sos_w, rng.standard_normal(n))], axis=1)
    swell = 1.0 + 0.25 * _closed_walk(n, rng, 0.3)
    out += wash * 0.035 * swell[:, None]
    for _ in range(int(density * loop_s)):
        at = rng.uniform(0, loop_s)
        f0 = rng.uniform(1800, 5200)
        ln = int(rng.uniform(0.004, 0.014) * SR)
        tt = np.arange(ln) / SR
        fr = f0 * (1.0 + 0.8 * np.exp(-tt * 900.0))
        ph = 2 * np.pi * np.cumsum(fr) / SR
        blip = np.sin(ph) * np.exp(-tt * rng.uniform(300, 900)) \
            * rng.uniform(0.2, 1.0) * 0.16 * near
        ch = stereo(blip, float(rng.uniform(-0.8, 0.8)))
        idx = (int(at * SR) + np.arange(ln)) % n
        np.add.at(out, idx, ch)
    return out


def wind(loop_s: float, base_hz: float = 400.0, howl: float = 0.5,
        gust: float = 0.5, seed: int = 0) -> np.ndarray:
    """Wandering-resonance noise. howl = resonance sharpness;
    gust = level walk depth."""
    rng = np.random.default_rng(seed)
    n = int(loop_s * SR)
    out = np.zeros((n, 2))
    from scipy.signal import lfilter
    for ch, po in [(0, 0.0), (1, 0.5)]:
        nz = rng.standard_normal(n)
        wander = _closed_walk(n, rng, 0.4)
        fc = base_hz * 2.0 ** (wander * 1.2 + po * 0.2)
        # warm the resonator on the loop's own tail — the walks
        # close their loops but a cold filter state still seams
        warm = SR // 2
        nzw = np.concatenate([nz[-warm:], nz])
        fcw = np.concatenate([fc[-warm:], fc])
        y = np.zeros(n + warm)
        blk = 512
        zi = np.zeros(2)
        i = 0
        while i < len(y):
            j = min(i + blk, len(y))
            f = float(np.clip(fcw[(i + j) // 2], 60, 6000))
            r = 0.985 + 0.012 * howl
            th = 2 * np.pi * f / SR
            b0 = (1 - r) * np.sqrt(1 + r * r - 2 * r * np.cos(2 * th))
            seg, zi = lfilter([b0], [1, -2 * r * np.cos(th), r * r],
                    nzw[i:j], zi=zi)
            y[i:j] = seg
            i = j
        out[:, ch] = y[warm:]
    lvl = 1.0 + gust * 0.8 * _closed_walk(n, rng, 0.25)
    sos_b = butter(1, 80, btype="high", fs=SR, output="sos")
    out = sosfilt(sos_b, out, axis=0) * lvl[:, None]
    return out * 0.4 / (np.max(np.abs(out)) + 1e-12)


def fire(loop_s: float, crackle_rate: float = 9.0,
        rumble: float = 0.6, seed: int = 0) -> np.ndarray:
    rng = np.random.default_rng(seed)
    n = int(loop_s * SR)
    out = np.zeros((n, 2))
    sos_r = butter(2, [40, 220], btype="band", fs=SR, output="sos")
    low = np.stack([sosfilt(sos_r, rng.standard_normal(n)),
            sosfilt(sos_r, rng.standard_normal(n))], axis=1)
    surge = 1.0 + 0.4 * _closed_walk(n, rng, 0.35)
    out += low * 0.14 * rumble * surge[:, None]
    for _ in range(int(crackle_rate * loop_s)):
        at = rng.uniform(0, loop_s)
        ln = max(int(rng.uniform(0.002, 0.010) * SR), 8)
        snap = rng.standard_normal(ln) \
            * np.exp(-np.arange(ln) / (ln * 0.2)) \
            * rng.uniform(0.15, 0.8)
        sos_c = butter(1, rng.uniform(1500, 4000), btype="high",
                fs=SR, output="sos")
        snap = sosfilt(sos_c, snap)
        ch = stereo(snap, float(rng.uniform(-0.6, 0.6)))
        idx = (int(at * SR) + np.arange(ln)) % n
        np.add.at(out, idx, ch)
    for _ in range(int(0.8 * loop_s)):
        at = rng.uniform(0, loop_s)
        ln = int(rng.uniform(0.3, 1.1) * SR)
        tt = np.arange(ln) / SR
        env = (tt / 0.06) * np.exp(1 - tt / 0.06)
        env = np.clip(env, 0, 1) * np.exp(-tt * 3.0)
        sos_h = butter(2, [2500, 9000], btype="band", fs=SR,
                output="sos")
        fl = sosfilt(sos_h, rng.standard_normal(ln)) * env \
            * rng.uniform(0.05, 0.14)
        ch = stereo(fl, float(rng.uniform(-0.4, 0.4)))
        idx = (int(at * SR) + np.arange(ln)) % n
        np.add.at(out, idx, ch)
    return out


def bubble(f0: float, chirp: float = 1.0, amp: float = 1.0,
        damp: float = 1.0) -> np.ndarray:
    """One bubble (van den Doel): damped sine at the Minnaert
    frequency f0, decay rate d = 0.13*f0 + 0.0072*f0^1.5, and the
    signature RISING chirp f(t) = f0 * (1 + xi*d*t), xi ~ 0.1.
    `chirp` scales xi (0 = dead sine blip, 2 = cartoon plook);
    `damp` scales d (< 1 rings longer than physics — a musical
    lie the potion pieces lean on). Usable as a pitched plink
    voice, not just texture: f0 IS the perceived pitch."""
    d = (0.13 * f0 + 0.0072 * f0 ** 1.5) * damp
    n = max(int(6.91 / d * SR), 32)               # ring to -60 dB
    tt = np.arange(n) / SR
    f_inst = f0 * (1.0 + 0.1 * chirp * d * tt)
    ph = 2 * np.pi * np.cumsum(f_inst) / SR
    y = np.sin(ph) * np.exp(-d * tt)
    a_n = max(int(0.0008 * SR), 1)                # soft onset:
    y[:a_n] *= np.linspace(0, 1, a_n)             # no click, all chirp
    return y * amp


def bubbles(loop_s: float, rate: float = 16.0, size: float = 0.5,
        chirp: float = 1.0, glug_rate: float = 0.8,
        simmer: float = 0.4, seed: int = 0) -> np.ndarray:
    """A liquid at work. Three populations:
    - fizz: Poisson bubbles, radii log-uniform (size 0 = soda
      fizz ~700-4000 Hz, size 1 = thick brew ~350-2000 Hz),
      amplitude ~ radius (big bubbles are loud bubbles);
    - glugs: rare LARGE bubbles (70-220 Hz) with deeper chirp —
      the pot's swallow;
    - simmer: rolling band-limited rumble whose level wobbles on
      a fast closed walk (the boil, not the bubbles)."""
    rng = np.random.default_rng(seed)
    n = int(loop_s * SR)
    out = np.zeros((n, 2))
    sos_s = butter(2, [70, 320], btype="band", fs=SR, output="sos")
    bed = np.stack([sosfilt(sos_s, rng.standard_normal(n)),
            sosfilt(sos_s, rng.standard_normal(n))], axis=1)
    wob = 1.0 + 0.45 * _closed_walk(n, rng, 1.5)
    out += bed * 0.11 * simmer * wob[:, None]
    f_lo, f_hi = 700.0 * 2.0 ** (-size), 4000.0 * 2.0 ** (-size)
    for _ in range(int(rate * loop_s)):
        at = rng.uniform(0, loop_s)
        f0 = float(np.exp(rng.uniform(np.log(f_lo), np.log(f_hi))))
        b = bubble(f0, chirp=chirp * rng.uniform(0.7, 1.4),
                amp=(f_lo / f0) ** 0.8 * rng.uniform(0.3, 1.0) * 0.22)
        ch = stereo(b, float(rng.uniform(-0.85, 0.85)))
        idx = (int(at * SR) + np.arange(len(ch))) % n
        np.add.at(out, idx, ch)
    for _ in range(max(int(glug_rate * loop_s), 0)):
        at = rng.uniform(0, loop_s)
        f0 = rng.uniform(70.0, 220.0)
        b = bubble(f0, chirp=chirp * rng.uniform(1.2, 2.0),
                amp=rng.uniform(0.35, 0.7))
        ch = stereo(b, float(rng.uniform(-0.5, 0.5)))
        idx = (int(at * SR) + np.arange(len(ch))) % n
        np.add.at(out, idx, ch)
    return out

#!/usr/bin/env python3
"""e28 — The held breath. What should NOCK's music do at full draw?

The shipped law (music.gd, cycle 46): music is WORLD, so it rides
NC.world_pitch — pitch_scale follows Engine.time_scale down to 0.2x
at full draw. Tape law, elegant on paper. But NOCK is MOBILE-FIRST,
and a phone's driver reproduces almost nothing below ~300 Hz: at
0.2x the gut motif's 110 Hz fundamental lands at 22 Hz, and the
question under measurement is whether the tune AS SHIPPED simply
leaves the target hardware's band at the exact moment the game is
at its most dramatic (full draw, the aim, the held breath).

The candidate: THE HELD BREATH. As the draw deepens the world's
music recedes (a dB-linear duck to a floor, not to zero — the world
recedes, it does not vanish), and the archer's own body takes over
ON ARCHER TIME (never dilated — the creak precedent): a heartbeat
whose RATE rides the draw fraction (rest -> strain), each thump a
low body + a tiny mitral CLICK band-placed so the phone keeps it
when it drops the body. Release snaps the world back over a short
gain ramp — click-free by contrast ruler.

Measured:
  - THE DEFECT IS REGISTER, NOT SILENCE. The first ruler (melody
    phone survival, fraction of RMS through a 4th-order 300 Hz
    highpass) DIED honestly: it descends monotonically but only to
    0.73 — a Karplus pluck is mostly harmonics and the phone keeps
    them; what leaves the band is the FUNDAMENTAL (110 -> 22 Hz,
    fundamental-band phone survival ~0 at full draw) and the
    BRIGHTNESS (power-weighted centroid of the phone-heard melody
    at full draw <= 0.4x undrawn). The feared total mush was
    overstated; the real loss is the tune's register and light.
  - THE THESIS: at full draw, what the phone FOREGROUNDS is the
    body — heartbeats are transients, so the ruler is peaks, not
    sums (the house crest rule): p99.9 |phone(heart * fade)| >=
    3x p99.9 |phone(ducked slowed melody)|.
  - the heartbeat is honest: measured rate (hysteresis onsets on
    its own envelope, e26's ruler) within 3% of design at frac
    0.5 and 1.0, and intervals alternate lub-dub short/long.
  - the release is a seam: max |sample delta| in the snap window
    with the 40 ms ramp <= half the hard-cut control's.

Renders: an A/B exhibit (8 s shipped full-draw tape mush, a beat
of silence, 8 s held breath at the same draw), then an 18 s draw
arc: rest -> full draw -> release -> the world back.

    python3 experiments/e28_heldbreath.py [outdir]
"""

import importlib.util
import os
import sys

import numpy as np
from scipy.signal import butter, sosfilt

_here = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(_here))
from loam import SR, stereo, write_wav

_spec = importlib.util.spec_from_file_location(
    "e22", os.path.join(_here, "e22_registers.py"))
e22 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(e22)

outdir = sys.argv[1] if len(sys.argv) > 1 else "render"
os.makedirs(outdir, exist_ok=True)

# NC-ready candidates (names for src/nc.gd if promoted)
HELD_DUCK_DB = -24.0   # music floor at full draw: recede, don't vanish
                       # (-18 measured x1.8 on the thesis ruler — the
                       # stage wasn't cleared; -24 clears it and the
                       # tune is still plainly there on release)
HEART_BPM_REST = 55.0
HEART_BPM_FULL = 108.0
HEART_DUB_FRAC = 0.32  # dub lands this fraction of a period after lub
SNAP_S = 0.04          # release gain ramp (the world snaps back)

PHONE_HZ = 300.0       # small-driver stand-in: 4th-order HP corner


def ts_of(frac):
    """NC.dilation verbatim: lerp(1.0, 0.2, frac^1.6)."""
    return 1.0 - 0.8 * np.clip(frac, 0.0, 1.0) ** 1.6


def tape(x, ts):
    """Constant-rate tape playback at speed ts (pitch AND time,
    exactly what pitch_scale does). Wrapped read: the source is a
    seamless loop, so slowing it stays seamless."""
    n_out = int(round(len(x) / ts))
    pos = (np.arange(n_out) * ts) % len(x)
    i0 = pos.astype(int)
    i1 = (i0 + 1) % len(x)
    w = (pos - i0)[:, None]
    return x[i0] * (1.0 - w) + x[i1] * w


_PHONE_SOS = butter(4, PHONE_HZ, "high", fs=SR, output="sos")


def phone(x):
    """The phone ruler: what survives a small driver's rolloff.
    Causal (a speaker is), applied per channel."""
    return sosfilt(_PHONE_SOS, x, axis=0)


def rms(x):
    return float(np.sqrt(np.mean(np.asarray(x, dtype=float) ** 2)))


def survival(x):
    """Fraction of a bus's RMS the phone keeps. Own-bus rule: fed
    the melody alone — the broadband stove would launder it."""
    return rms(phone(x)) / max(rms(x), 1e-12)


def centroid(x):
    """Power-weighted spectral centroid (the house ruler — magnitude
    weighting lets a thousand tiny high bins outvote the tune)."""
    m = np.asarray(x, dtype=float)
    if m.ndim == 2:
        m = m.sum(axis=1)
    spec = np.abs(np.fft.rfft(m)) ** 2
    f = np.fft.rfftfreq(len(m), 1 / SR)
    return float((f * spec).sum() / max(spec.sum(), 1e-12))


def fund_survival(x, f0):
    """The register ruler: how much of the fundamental's own band
    [0.7 f0, 1.4 f0] the phone keeps."""
    m = np.asarray(x, dtype=float).sum(axis=1)
    spec_r = np.abs(np.fft.rfft(m)) ** 2
    spec_p = np.abs(np.fft.rfft(phone(m))) ** 2
    f = np.fft.rfftfreq(len(m), 1 / SR)
    band = (f >= 0.7 * f0) & (f <= 1.4 * f0)
    return float(np.sqrt(spec_p[band].sum() /
                         max(spec_r[band].sum(), 1e-12)))


def p999(x):
    """Peak ruler for transients: 99.9th percentile of |x|."""
    return float(np.percentile(np.abs(x), 99.9))


def duck_gain(frac):
    """dB-linear duck: 0 dB undrawn -> HELD_DUCK_DB at full draw."""
    return 10.0 ** (np.clip(frac, 0.0, 1.0) * HELD_DUCK_DB / 20.0)


def heart_gain(frac):
    """The body fades in as the world recedes (equal-power arm)."""
    return np.sin(np.clip(frac, 0.0, 1.0) * np.pi / 2.0)


def _thump(f0, amp, click_amp, rng):
    """One heart sound: a damped low body + a short band-placed
    click (the valve). The click is the phone's share — the body
    is below the driver, the click is not."""
    n = int(0.20 * SR)
    t = np.arange(n) / SR
    body = np.sin(2 * np.pi * f0 * t) * np.exp(-t * 28.0)
    nc = int(0.010 * SR)
    sos = butter(2, [900.0, 1800.0], "bandpass", fs=SR, output="sos")
    click = np.zeros(n)
    click[:nc] = sosfilt(sos, rng.uniform(-1, 1, nc)) \
        * np.exp(-np.arange(nc) / SR * 400.0)
    return amp * (body + click_amp * click)


def heartbeat(dur_s, bpm, seed=0xE28):
    """A lub-dub train at fixed rate, ON ARCHER TIME (the render is
    never taped). Event train, not a loop — in game this is an sfx
    tick clock like the creak, not a music player."""
    rng = np.random.default_rng(seed)
    n = int(dur_s * SR)
    out = np.zeros(n)
    period = 60.0 / bpm
    t = 0.0
    while t < dur_s:
        for (dt, f0, a) in [(0.0, 62.0, 0.50),
                            (HEART_DUB_FRAC * period, 52.0, 0.33)]:
            th = _thump(f0, a, 1.1, rng)
            i0 = int((t + dt) * SR)
            i1 = min(i0 + len(th), n)
            if i0 < n:
                out[i0:i1] += th[:i1 - i0]
        t += period
    return out


def onsets(x, arm=0.35, disarm=0.15):
    """e26's onset ruler: envelope hysteresis crossings, never
    derivative peaks. Returns onset times in seconds."""
    env = np.abs(x)
    sos = butter(2, 40.0, "low", fs=SR, output="sos")
    env = sosfilt(sos, env)
    hi, lo = arm * env.max(), disarm * env.max()
    times, armed = [], True
    for i in range(len(env)):
        if armed and env[i] > hi:
            times.append(i / SR)
            armed = False
        elif not armed and env[i] < lo:
            armed = True
    return np.array(times)


def draw_arc(master, dur_s=18.0, t_full=7.0, t_release=11.0,
             ramp_s=SNAP_S):
    """The narrative render: frac ramps 0->1 over t_full, holds,
    releases at t_release (ts and gains snap back over ramp_s).
    Music: variable-rate wrapped tape read + per-sample duck.
    Heart: integrated phase — rate rides frac, time never dilates."""
    n = int(dur_s * SR)
    tt = np.arange(n) / SR
    frac = np.clip(tt / t_full, 0.0, 1.0)
    rel = tt >= t_release
    # the snap: frac collapses to 0 across ramp_s after release
    snap = np.clip((tt - t_release) / ramp_s, 0.0, 1.0)
    frac = np.where(rel, frac[int(t_release * SR) - 1] * (1 - snap),
                    frac)
    ts = ts_of(frac)
    pos = np.cumsum(ts) % len(master)
    i0 = pos.astype(int)
    i1 = (i0 + 1) % len(master)
    w = (pos - i0)[:, None]
    music = (master[i0] * (1 - w) + master[i1] * w) \
        * duck_gain(frac)[:, None]
    # heartbeat: phase integrates the frac-ridden rate; a lub fires
    # on each integer crossing, its dub HEART_DUB_FRAC later
    bpm = HEART_BPM_REST + (HEART_BPM_FULL - HEART_BPM_REST) * frac
    phase = np.cumsum(bpm / 60.0 / SR)
    heart = np.zeros(n)
    rng = np.random.default_rng(0xE28)
    beats = np.flatnonzero(np.diff(np.floor(phase)) > 0)
    for i in beats:
        p = 60.0 / bpm[i]
        for (dt, f0, a) in [(0.0, 62.0, 0.50),
                            (HEART_DUB_FRAC * p, 52.0, 0.33)]:
            th = _thump(f0, a, 1.1, rng)
            j0 = i + int(dt * SR)
            j1 = min(j0 + len(th), n)
            if j0 < n:
                heart[j0:j1] += th[:j1 - j0]
    hg = heart_gain(frac)
    # the body is gone once the string is loosed
    hg = np.where(rel, hg[int(t_release * SR) - 1] * (1 - snap), hg)
    return music + stereo(heart, 0.0) * hg[:, None], frac


if __name__ == "__main__":
    Lf, mel_f, bed_f = e22.flame()
    master = Lf.master(lp_hz=4800.0, drive=1.3)

    print("== the defect is REGISTER, not silence ==")
    fracs = [0.0, 0.25, 0.5, 0.75, 1.0]
    rows = []
    for fr in fracs:
        slowed = tape(mel_f, ts_of(fr))
        rows.append((survival(slowed),
                     fund_survival(slowed, 110.0 * ts_of(fr)),
                     centroid(phone(slowed))))
        print("  frac %.2f  ts %.3f  f0 %5.1f Hz  rms-surv %.3f  "
              "fund-surv %.4f  phone-centroid %5.0f Hz"
              % (fr, ts_of(fr), 110.0 * ts_of(fr), *rows[-1]))
    mono = all(rows[i][0] > rows[i + 1][0] for i in range(len(rows) - 1))
    print("  rms ruler: monotone %s but ends %.2f — the harmonics"
          " carry; NOT a silence defect (ruler death, kept as"
          " exhibit)" % ("YES" if mono else "NO", rows[-1][0]))
    print("  register: fund-surv %.4f -> %.4f (want full-draw"
          " <= 0.1)  centroid %5.0f -> %5.0f Hz (want <= 0.4x): %s"
          % (rows[0][1], rows[-1][1], rows[0][2], rows[-1][2],
             "YES" if rows[-1][1] <= 0.1
             and rows[-1][2] <= 0.4 * rows[0][2] else "NO"))

    print("== the thesis: at full draw the phone foregrounds the BODY ==")
    slow_mel = tape(mel_f, ts_of(1.0))[:int(8.0 * SR)]
    hb = heartbeat(8.0, HEART_BPM_FULL)
    pm = p999(phone(slow_mel * duck_gain(1.0)))
    ph = p999(phone(hb * heart_gain(1.0)))
    print("  phone-p99.9 heart %.4f vs ducked slow melody %.4f "
          "(x%.1f, want >= 3)" % (ph, pm, ph / max(pm, 1e-12)))

    print("== the heartbeat is honest ==")
    for fr in [0.5, 1.0]:
        want = HEART_BPM_REST + (HEART_BPM_FULL - HEART_BPM_REST) * fr
        ons = onsets(heartbeat(10.0, want))
        # lub->lub spans (skip the dub between): every other onset
        lubs = ons[::2]
        got = 60.0 / np.mean(np.diff(lubs))
        iv = np.diff(ons)
        short = np.mean(iv[::2])   # lub -> dub
        lng = np.mean(iv[1::2])    # dub -> next lub
        print("  frac %.1f: rate %.1f bpm (want %.1f, err %.1f%%), "
              "lub-dub frac %.2f (want %.2f)"
              % (fr, got, want, 100 * abs(got - want) / want,
                 short / (short + lng), HEART_DUB_FRAC))

    print("== the release is a seam (contrast: hard cut control) ==")
    arc, frac_tv = draw_arc(master)
    arc0, _ = draw_arc(master, ramp_s=1e-9)
    a = int((11.0 - 0.005) * SR)
    b = int((11.0 + SNAP_S + 0.005) * SR)
    d_ramp = float(np.max(np.abs(np.diff(arc[a:b], axis=0))))
    d_cut = float(np.max(np.abs(np.diff(arc0[a:b], axis=0))))
    print("  snap-window max |delta|: ramped %.4f vs cut %.4f "
          "(want <= 0.5x)" % (d_ramp, d_cut))

    # exhibits (norm=False: the A/B compares LEVELS — one scale)
    n8 = int(8.0 * SR)
    gap = np.zeros((int(0.7 * SR), 2))
    shipped = tape(master, ts_of(1.0))[:n8]
    held = tape(master, ts_of(1.0))[:n8] * duck_gain(1.0) \
        + stereo(heartbeat(8.0, HEART_BPM_FULL), 0.0)
    # one shared scale, no per-file normalize: the A/B compares
    # LEVELS (write_wav wraps past +/-1, so clip explicitly)
    ab = np.clip(np.concatenate([shipped, gap, held]) * 0.85,
                 -0.99, 0.99)
    write_wav(os.path.join(outdir, "e28_ab_fulldraw.wav"), ab)
    write_wav(os.path.join(outdir, "e28_drawarc.wav"),
              np.clip(arc * 0.85, -0.99, 0.99))
    print("wrote", outdir + "/e28_ab_fulldraw.wav",
          outdir + "/e28_drawarc.wav")

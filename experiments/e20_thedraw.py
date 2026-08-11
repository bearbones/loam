#!/usr/bin/env python3
"""e20 — The Draw. SFX prototype for NOCK's signature verb: tap-hold
draw builds ~2.5s, TIME DILATION scales with draw fraction (full draw
slows the world to 0.2x), overheld draw strains (wobble grows), and
draw power trades: full = flat, lethal, loud; soft = lobbed, quiet.

The idea under test: the draw cue is not just a creak — it is the
WORLD dilating audibly. The archer's own sounds (wood creak, fiber
ticks, hemp tension) stay in "archer time" while the night bed (fire
rumble + wind + a 96 Hz night tone) tape-slows underneath, pitch
falling with rate, and whip-snaps back at release. Slow-motion fire
is the flame-lit-margins register doing the dilation's work for it.

FULL (one-shot ~10.5s): bed alone -> 2.5s build (tick density and
pitch rise with frac, hemp tone glisses up as tension climbs, bed
eases 1.0 -> 0.2x on the eased dilation curve) -> 2.3s overheld hold
(tremor accelerates 4 -> 9 Hz, high whine grows) -> release: string
twang + limb thunk + bright whoosh (3k -> 350 Hz sweep), bed snaps
back in 0.35s -> afterglow.

SOFT (one-shot ~6s): the lure lob. 0.5s draw to frac 0.2: a handful
of ticks, barely-dipped bed, small twang, low quiet whoosh.

Measured from the renders, each claim on its own bus:
  - bed honesty: the 96 Hz night tone must sit at ~19.2 Hz mid-hold
  - tick density ratio last/first build half-second (~hazard design)
  - whoosh POWER-weighted centroid, full vs soft
  - strain tremor rate from the creak bus envelope, late hold

    python3 experiments/e20_thedraw.py [outdir]
"""

import os
import sys

import numpy as np
from scipy.signal import butter, sosfilt, lfilter, find_peaks

sys.path.insert(0, os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))))
from loam import SR, hz, stereo, write_wav
from loam.modal import strike, bow, WOOD
from loam.strings import pluck
from loam.texture import fire, wind
from loam.space import reverb_tail
from loam.dyn import limiter

outdir = sys.argv[1] if len(sys.argv) > 1 else "render"
os.makedirs(outdir, exist_ok=True)
rng = np.random.default_rng(0xE20)

DIL_EXP = 1.6      # eased dilation: d = 1 - 0.8 * frac**DIL_EXP
DIL_FLOOR = 0.2    # full draw slows the world to 0.2x (NOCK ruling)
NIGHT_TONE = 96.0  # the bed's measurable partial (mains-adjacent)


def place(buf, at_s, mono, pan=0.0):
    c = stereo(mono, pan)
    i0 = int(at_s * SR)
    n = min(len(c), len(buf) - i0)
    buf[i0:i0 + n] += c[:n]


def night_bed(dur_s, seed):
    """Flame-lit margin: fire + low wind + the night tone drone."""
    b = fire(dur_s, crackle_rate=5.0, rumble=0.7, seed=seed) * 0.42
    b += wind(dur_s, base_hz=240.0, howl=0.35, gust=0.4,
            seed=seed + 1) * 0.35
    tt = np.arange(int(dur_s * SR)) / SR
    tone = (np.sin(2 * np.pi * NIGHT_TONE * tt) * 0.030
            + np.sin(2 * np.pi * 2.011 * NIGHT_TONE * tt) * 0.012)
    return b + stereo(tone, 0.0)


def varispeed(src, rate):
    """Tape-read src (stereo) at per-sample rate; pitch follows."""
    pos = np.cumsum(rate)
    pos = np.clip(pos, 0, len(src) - 1)
    idx = np.arange(len(src))
    return np.stack([np.interp(pos, idx, src[:, 0]),
            np.interp(pos, idx, src[:, 1])], axis=1)


def dilation(frac):
    return 1.0 - (1.0 - DIL_FLOOR) * frac ** DIL_EXP


def creak_ticks(t0, t1, frac_of, buf_len_s, seed):
    """Stick-slip fiber ticks: density AND pitch rise with frac.
    Interval hazard 0.22 / (0.5 + 3 frac^2)."""
    r = np.random.default_rng(seed)
    bus = np.zeros((int(buf_len_s * SR), 2))
    t = t0 + 0.03
    while t < t1:
        f = frac_of(t)
        tick = strike(950.0 * (1.0 + 0.30 * f) * r.uniform(0.96, 1.04),
                float(r.uniform(0.035, 0.07)), WOOD,
                amp=0.055 + 0.11 * f, bright=1.25, rng=r)
        place(bus, t, tick, float(r.uniform(-0.12, 0.12)))
        t += 0.22 / (0.5 + 3.0 * f * f) * float(r.uniform(0.8, 1.25))
    return bus


def whoosh(dur_s, c_hi, c_lo, amp, decay):
    """Bandpassed noise, resonator center sweeping c_hi -> c_lo
    exponentially (the arrow taking the air with it)."""
    n = int(dur_s * SR)
    tt = np.arange(n) / SR
    c = c_hi * (c_lo / c_hi) ** (tt / dur_s)
    nz = rng.standard_normal(n)
    y = np.zeros(n)
    blk = 256
    zi = np.zeros(2)
    i = 0
    while i < n:
        j = min(i + blk, n)
        f = float(np.clip(c[(i + j) // 2], 50, 8000))
        rr = 0.972
        th = 2 * np.pi * f / SR
        b0 = (1 - rr) * np.sqrt(1 + rr * rr - 2 * rr * np.cos(2 * th))
        seg, zi = lfilter([b0], [1, -2 * rr * np.cos(th), rr * rr],
                nz[i:j], zi=zi)
        y[i:j] = seg
        i = j
    env = np.exp(-tt * decay)
    a = int(0.008 * SR)
    env[:a] *= np.linspace(0, 1, a)
    return y * env * amp


def render_draw(name, dur_s, bed_seed, t_draw, build_s, hold_s,
        frac_max, wh):
    """One night, one draw, one release. Returns the buses for the
    metrology so every claim is measured on its own bus."""
    n = int(dur_s * SR)
    t_full = t_draw + build_s          # frac_max reached
    t_rel = t_full + hold_s            # release

    def frac_of(t):
        return frac_max * min(max((t - t_draw) / build_s, 0.0), 1.0)

    # -- the world's bus: bed through the dilation tape-read --
    tt = np.arange(n) / SR
    fr = np.array([frac_of(t) for t in tt])
    rate = dilation(fr)
    snap = 0.35
    post = tt >= t_rel
    ease = np.clip((tt[post] - t_rel) / snap, 0, 1)
    r_rel = rate[np.searchsorted(tt, t_rel) - 1]
    rate[post] = r_rel + (1.0 - r_rel) * (0.5 - 0.5 * np.cos(
            np.pi * ease))
    src = night_bed(dur_s + 2.0, bed_seed)   # tape to read from
    bed = varispeed(src, rate)

    # -- the archer's bus: creak family, strain tremor. The ticks
    # keep their OWN bus for the metrology (the groan and hemp
    # would outvote the counter on the mixed bus) --
    ticks = creak_ticks(t_draw, t_rel, frac_of, dur_s, bed_seed + 7)
    creak = ticks.copy()
    place(creak, t_draw + 0.05, bow(hz(36), build_s + hold_s + 0.3,
            WOOD, amp=0.16, rng=rng), 0.0)         # the limb groans
    hemp_f = 105.0 * (1.0 + 0.5 * fr)              # tension gliss
    hemp = np.sin(2 * np.pi * np.cumsum(hemp_f) / SR) * 0.058 * fr
    creak += stereo(hemp, 0.0)
    if hold_s > 0.6:                               # overheld: strain
        hw = (tt >= t_full) & (tt < t_rel)
        ht = tt[hw] - t_full
        trem_f = 4.0 + 5.0 * ht / hold_s           # 4 -> 9 Hz
        trem = 1.0 + 0.38 * (ht / hold_s) * np.sin(
                2 * np.pi * np.cumsum(trem_f) / SR)
        creak[hw] *= trem[:, None]
        whine = np.zeros(n)
        whine[hw] = np.sin(2 * np.pi * 2210.0 * ht) \
            * 0.028 * (ht / hold_s) * trem
        creak += stereo(whine, 0.0)

    # -- the release bus: twang + limb thunk + the air --
    rel = np.zeros((n, 2))
    place(rel, t_rel, pluck(147.0, 0.6, amp=wh["twang"], t60=0.4,
            damp=0.2, pick=0.12, seed=3), 0.05)
    place(rel, t_rel + 0.008, strike(hz(41), 0.30, WOOD,
            amp=wh["thunk"], bright=0.5, knock=0.6, rng=rng), -0.05)
    wbus = np.zeros((n, 2))
    place(wbus, t_rel + 0.004, whoosh(wh["dur"], wh["hi"], wh["lo"],
            wh["amp"], wh["decay"]), 0.1)

    mix = bed + creak + rel + wbus
    out = limiter(reverb_tail(mix, t60=1.6, size=0.8,
            damp_hz=3800.0, mix=0.14), ceiling=0.90)
    write_wav(os.path.join(outdir, name), out)
    return bed, ticks, creak, wbus, t_draw, t_full, t_rel


# ===============================================================
# FULL: build 2.5s to frac 1.0, overheld 2.3s, loud flat release
# ===============================================================
bedF, ticksF, creakF, whF, tdF, tfF, trF = render_draw(
        "e20_draw_full.wav", 10.5, 11, 2.0, 2.5, 2.3, 1.0,
        {"twang": 0.50, "thunk": 0.42, "dur": 0.30,
         "hi": 3000.0, "lo": 350.0, "amp": 0.78, "decay": 12.0})

# ===============================================================
# SOFT: the lure lob — 0.5s draw to frac 0.2, quiet low release
# ===============================================================
bedS, ticksS, creakS, whS, tdS, tfS, trS = render_draw(
        "e20_draw_soft.wav", 6.0, 23, 1.5, 0.5, 0.0, 0.2,
        {"twang": 0.14, "thunk": 0.11, "dur": 0.22,
         "hi": 1200.0, "lo": 260.0, "amp": 0.17, "decay": 16.0})

# --- metrology -------------------------------------------------
def tone_peak(bus, a_s, b_s, f_lo, f_hi):
    seg = bus[int(a_s * SR):int(b_s * SR)].mean(axis=1)
    seg = seg - seg.mean()
    sp = np.abs(np.fft.rfft(seg * np.hanning(len(seg))))
    fax = np.fft.rfftfreq(len(seg), 1.0 / SR)
    w = (fax >= f_lo) & (fax <= f_hi)
    return fax[w][np.argmax(sp[w])]


pre = tone_peak(bedF, 0.4, 1.9, 60, 130)
mid = tone_peak(bedF, 4.9, 6.6, 10, 40)
print(f"  bed night tone: {pre:.1f} Hz before the draw, "
      f"{mid:.1f} Hz mid-hold (designed {NIGHT_TONE:.0f} -> "
      f"{NIGHT_TONE * DIL_FLOOR:.1f})")


def tick_count(bus, a_s, b_s):
    seg = np.abs(bus[int(a_s * SR):int(b_s * SR)]).mean(axis=1)
    env = np.convolve(seg, np.ones(96) / 96, mode="same")
    pk, _ = find_peaks(env, height=0.18 * env.max(),
            distance=int(0.018 * SR))
    return len(pk)


early = tick_count(ticksF, tdF, tdF + 0.5)
late = tick_count(ticksF, tfF - 0.5, tfF)
haz = (0.5 + 3.0 * 0.9 ** 2) / (0.5 + 3.0 * 0.1 ** 2)
print(f"  creak ticks/0.5s: {early} early -> {late} late build "
      f"(hazard design ratio ~{haz:.1f}x)")


def centroid(bus, a_s, b_s):
    seg = bus[int(a_s * SR):int(b_s * SR)].mean(axis=1)
    p = np.abs(np.fft.rfft(seg)) ** 2          # POWER-weighted
    fax = np.fft.rfftfreq(len(seg), 1.0 / SR)
    return float((fax * p).sum() / (p.sum() + 1e-12))


cF = centroid(whF, trF, trF + 0.32)
cS = centroid(whS, trS, trS + 0.26)
print(f"  whoosh centroid: full {cF:.0f} Hz vs soft {cS:.0f} Hz "
      f"({cF / cS:.2f}x — power reads as air speed)")

seg = np.abs(creakF[int((trF - 1.0) * SR):int(trF * SR)]).mean(axis=1)
env = np.convolve(seg, np.ones(1024) / 1024, mode="same")
sp = np.abs(np.fft.rfft(env - env.mean()))
fax = np.fft.rfftfreq(len(env), 1.0 / SR)
w = (fax >= 2.0) & (fax <= 15.0)
print(f"  strain tremor, late hold: {fax[w][np.argmax(sp[w])]:.1f} Hz "
      f"(designed ramp 4 -> 9)")

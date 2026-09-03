#!/usr/bin/env python3
"""loam e80 — "The Mizrab Leans In". The click becomes a
written parameter of the string.

The luthier's repair of Nine Landings stamped an 8 ms contact
click OVER every melody stroke so a low string could mark
time under nine ringing tails. This cycle promotes the hack:
fdpluck2 now takes `click` — the mizrab's body-radiated
contact transient, fused into the buffer at the string's own
speak time (dev_smoke holds the subtraction contract: clicked
minus bare IS the click, exact peak, exact place, low band
untouched).

Here the parameter plays MUSIC: a 20-note jhala line strokes
every 0.3 s under a chikari carpet, and the click depth rides
one seamless cosine — bare at the seam, leaning in to 0.35
mid-loop, easing out again. The claims:

  - on the string's own bus, attack-window HF excess tracks
    the written lean (design-vs-measured correlation);
  - the string's tone does not follow the lean (low band
    uncorrelated — the click adds mark, not loudness);
  - and the point of the whole repair, now shown as an arc:
    in the MIX, clicked strokes mark time tightly where
    bare strokes' marks scatter. Time legibility is now a
    parameter you write, per stroke.

38.4 s seamless loop, D (Sa = D3), no drone — just the two
hands of one player.

    python3 experiments/e80_mizrab_leans_in.py [outdir]
"""

import os
import sys

import numpy as np
from scipy.signal import butter, sosfilt

sys.path.insert(0, os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))))
from loam import SR, hz, stereo, write_wav
from loam import ruler
from loam.fdstring import fdpluck2, _speak

outdir = sys.argv[1] if len(sys.argv) > 1 else "render"
os.makedirs(outdir, exist_ok=True)
fails = []


def check(name, cond, detail):
    print(f"  {'PASS' if cond else 'FAIL'} {name}: {detail}")
    if not cond:
        fails.append(name)


def rms(x):
    return float(np.sqrt(np.mean(np.asarray(x, float) ** 2) + 1e-30))


def db(r):
    return 20.0 * np.log10(r + 1e-30)


LOOP_S = 38.4
STROKE = 0.3
NST = 128
CMAX = 0.35
NLVL = 12                       # click depth quantization (cache)
GUARD = 0.004
N = int(LOOP_S * SR)

LINE = [50, 52, 53, 55, 53, 52, 50, 48, 47, 48,
        50, 52, 53, 52, 50, 48, 50, 52, 50, 50]
CH_DA = hz(62) * 2.0 ** (0.8 / 1200.0)
CH_RA = hz(62) * 2.0 ** (-3.2 / 1200.0)

_cache = {}


def mpluck(m, lvl):
    key = (m, lvl)
    if key not in _cache:
        _cache[key] = fdpluck2(hz(m), 1.2, amp=1.0, pick=0.28,
                click=lvl * CMAX / NLVL)
    return _cache[key]


def chik(which):
    key = ("c", which)
    if key not in _cache:
        f = CH_DA if which == 0 else CH_RA
        _cache[key] = fdpluck2(f, 0.9, amp=0.36 if which == 0
                else 0.32, pick=0.24 if which == 0 else 0.33)
    return _cache[key]


_spkc = {}


def spk(v, key):
    if key not in _spkc:
        _spkc[key] = _speak(v)
    return _spkc[key]


def add_wrap(bus, t, ss):
    i0 = int(round(t * SR)) % N
    n = len(ss)
    if i0 + n <= N:
        bus[i0:i0 + n] += ss
    else:
        k = N - i0
        bus[i0:] += ss[:k]
        bus[:n - k] += ss[k:]


# ---- the two hands ----------------------------------------------
mel = np.zeros((N, 2))
chikb = np.zeros((N, 2))
STK = []                        # (t, midi, lvl)
for k in range(NST):
    t = k * STROKE
    lean = 0.5 - 0.5 * np.cos(2.0 * np.pi * t / LOOP_S)
    lvl = int(round(lean * NLVL))
    m = LINE[k % len(LINE)]
    v = mpluck(m, lvl)
    add_wrap(mel, t - spk(mpluck(m, 0), ("m", m)) + GUARD,
            stereo(v, 0.0))
    STK.append((t, m, lvl))
    # the curtain: chikari every 0.15 s — landings density, the
    # texture whose stacked tails made bare blooms illegible
    for j in range(2):
        cj = chik((2 * k + j) % 2)
        add_wrap(chikb, t + (j + 0.5) * STROKE / 2.0
                - spk(cj, ("c", (2 * k + j) % 2)) + GUARD,
                stereo(cj, 0.40 if (2 * k + j) % 2 == 0 else -0.40))

mix = 0.50 * mel + 0.68 * chikb
mix *= 0.92 / (np.abs(mix).max() + 1e-12)
write_wav(os.path.join(outdir, "e80_mizrab_leans_in.wav"), mix)

# ---- rulers ------------------------------------------------------
print("e80 rulers:")

# 1. seam
check("seam", ruler.seam_rank(mix) <= 0.999,
        f"p{100 * ruler.seam_rank(mix):.2f}")

# 2. own-bus arc: attack-window HF excess tracks the written lean
mmono = mel.mean(axis=1)
sos_hp = butter(4, 3200.0, btype="highpass", fs=SR, output="sos")
hp_own = sosfilt(sos_hp, np.concatenate([mmono, mmono]))[N:]
ex, lo_e, cw, lvls = [], [], [], []
sos_lo = butter(4, 2000.0, btype="lowpass", fs=SR, output="sos")
lo_own = sosfilt(sos_lo, np.concatenate([mmono, mmono]))[N:]
for t, m, lvl in STK:
    a = rms(hp_own[int((t + GUARD) * SR):
                   int((t + GUARD + 0.012) * SR)])
    f = rms(hp_own[int((t - 0.030) * SR):int((t - 0.018) * SR)])
    ex.append(max(a * a - f * f, 0.0))
    lo_e.append(rms(lo_own[int(t * SR):int((t + 0.25) * SR)]))
    cw.append(lvl * CMAX / NLVL)
    lvls.append(lvl)
ex, lvls = np.array(ex), np.array(lvls)
# per-stroke correlation is diluted by per-note bloom variance
# (six different strings, six different bare HF attacks) — the
# e78 move applies: aggregate to the written variable's levels
# and correlate the medians. Per-stroke r reported as info.
lm = [float(np.median(np.sqrt(ex[lvls == l])))
      for l in range(NLVL + 1)]
r_arc = float(np.corrcoef(lm, np.arange(NLVL + 1))[0, 1])
r_stk = float(np.corrcoef(np.sqrt(ex), cw)[0, 1])
check("lean_arc", r_arc >= 0.90,
        f"level-median HF excess vs lean r={r_arc:.3f} "
        f"(per-stroke r={r_stk:.3f} info)")

# 3. tone invariance: the click adds mark, not loudness
r_tone = float(np.corrcoef(lo_e, cw)[0, 1])
check("tone_inv", abs(r_tone) <= 0.3,
        f"low-band stroke energy vs lean r={r_tone:+.3f}")

# 4. THE POINT — in the mix, clicked strokes mark time where
# bare strokes scatter: flux argmax per stroke window on the
# hp band of the full mix, grouped by written lean
hp_mix = sosfilt(sos_hp, np.concatenate(
        [mix.mean(axis=1), mix.mean(axis=1)]))
fx, dt = ruler.flux_series(hp_mix, frame=512, hop=128)
tf = np.arange(len(fx)) * dt
offs = {}
for t, m, lvl in STK:
    c = t + LOOP_S
    sel = (tf >= c - 0.05) & (tf <= c + 0.07)
    offs[t] = float(tf[sel][np.argmax(fx[sel])] - c)
strong = [offs[t] for t, m, l in STK if l >= 0.7 * NLVL]
bare = [offs[t] for t, m, l in STK if l == 0]
smed = float(np.median(strong))
sdev = np.abs(np.array(strong) - smed)
bdev = np.abs(np.array(bare) - smed)
check("marks_clicked", float(sdev.max()) <= 0.008,
        f"{len(strong)} clicked strokes worst |dev-med| "
        f"{1000 * sdev.max():.1f} ms")
# the contrast is a WORST-CASE claim, not a median one: most
# bare strokes still mark (their bloom peeks through between
# chikari tails), but some vanish entirely — and one illegible
# stroke is what breaks a listener's flow (the operator heard
# exactly this in landings). Clicked strokes may never vanish.
check("marks_contrast", float(bdev.max()) >= 0.030,
        f"worst bare-stroke |dev| {1000 * bdev.max():.1f} ms vs "
        f"clicked worst {1000 * sdev.max():.1f} ms "
        f"({len(bare)} bare strokes, median {1000 * np.median(bdev):.1f} ms)")

# 5. the grid itself: stroke rate as a flux line
fl, pr = ruler.flux_line(mix.mean(axis=1), 3.2, 3.5)
check("stroke_line", abs(fl - 1.0 / STROKE) * STROKE <= 0.02
        and pr >= 5.0,
        f"{fl:.3f} Hz (want {1.0 / STROKE:.3f}) prom {pr:.1f}x")

# 6. home: D crowns the chroma
ch = ruler.chroma(mix)
check("chroma_D", int(np.argmax(ch)) == 2,
        f"crown class {int(np.argmax(ch))} (D=2), "
        f"D share {ch[2]:.2f}")

ruler.report(mix, "e80_mizrab_leans_in")
print(f"\n{'ALL PASS' if not fails else 'FAILS: ' + str(fails)}")
sys.exit(1 if fails else 0)

#!/usr/bin/env python3
"""loam e81 — shamisen: "The Next Episode" opening on the
three strings.

Operator direction: take the strings to Japan. loam.nihon is
born with the shamisen — sawari as the jawari barrier it
always was, the bachi snap as e80's click writ large, and the
don (the bachi striking the hide under the string, one
gesture) new.

The demo, by request: the opening tune of Dr. Dre & Snoop
Dogg's "The Next Episode" (the David McCallum "The Edge"
riff), Eb minor, ~95 BPM, arranged for shamisen duo — the
lead on clean upper strings, the bass on the lowest string
with the sawari ridge fully up, moving Eb to Cb under the
fourth bar. Two 4-bar cycles; the second adds a low sawari
echo under the long notes. 20.2 s seamless loop.

Every claim measured: the tune IS the tune (per-note pitch
readback), the bass walks where written, the written buzz is
in the render (sawari-on vs counterfactual clean bass +dB),
the don lives in its own band, every bachi stroke marks time
(e80's click contract, now cross-instrument), the groove's
dotted-eighth line stands, Eb crowns.

    python3 experiments/e81_shamisen_episode.py [outdir]
"""

import os
import sys

import numpy as np
from scipy.signal import butter, sosfilt

sys.path.insert(0, os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))))
from loam import SR, hz, stereo, write_wav
from loam import ruler
from loam.nihon import shamisen

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


BPM = 95.0
S16 = 60.0 / BPM / 4.0          # one sixteenth
CYC = 64                        # 4 bars of 16 slots
NCYC = 2
LOOP_S = NCYC * CYC * S16
N = int(LOOP_S * SR)

# the riff (slot, midi, held slots): Eb4 Bb4 | Bb4 Ab4 Bb4 |
# Ab4 Gb4 Ab4 | Ab4 Gb4 Eb4 Gb4 — dotted figure over 3 bars,
# the 4th bar rings out
RIFF = [(0, 63, 6), (6, 70, 6), (12, 70, 3), (15, 68, 3),
        (18, 70, 6), (24, 68, 3), (27, 66, 3), (30, 68, 6),
        (36, 68, 3), (39, 66, 3), (42, 63, 3), (45, 66, 3)]
BASS_PAT = [0, 3, 6, 8, 11, 14]         # per-bar bachi pattern
EB2, CB2 = 39, 35                       # bar 4 walks Eb -> Cb
ECHO = [0, 6, 18, 30]                   # cycle-B low echo slots

_cache = {}


def voice(kind, m):
    key = (kind, m)
    if key not in _cache:
        if kind == "mel":
            _cache[key] = shamisen(hz(m), 1.2, sawari=0.0,
                    snap=0.6, thump=0.5)
        elif kind == "bass":
            _cache[key] = shamisen(hz(m), 1.4, sawari=1.0,
                    snap=0.35, thump=0.6, pick=0.70)
        elif kind == "bass_clean":                # counterfactual
            _cache[key] = shamisen(hz(m), 1.4, sawari=0.0,
                    snap=0.35, thump=0.6, pick=0.70)
        elif kind == "echo":
            _cache[key] = shamisen(hz(m), 1.4, sawari=1.0,
                    snap=0.45, thump=0.4)
    return _cache[key]


def add_wrap(bus, t, ss):
    i0 = int(round(t * SR)) % N
    n = len(ss)
    if i0 + n <= N:
        bus[i0:i0 + n] += ss
    else:
        k = N - i0
        bus[i0:] += ss[:k]
        bus[:n - k] += ss[k:]


mel = np.zeros((N, 2))
bass = np.zeros((N, 2))
bass_cf = np.zeros((N, 2))
MELN, BASSN = [], []
for c in range(NCYC):
    t0 = c * CYC * S16
    for sl, m, held in RIFF:
        t = t0 + sl * S16
        add_wrap(mel, t, stereo(voice("mel", m), 0.15))
        MELN.append((t, m))
    if c == 1:
        for sl in ECHO:
            add_wrap(mel, t0 + sl * S16,
                    stereo(voice("echo", 51) * 0.5, -0.30))
    for bar in range(4):
        root = CB2 if bar == 3 else EB2
        for j, sl in enumerate(BASS_PAT):
            if bar == 3 and sl >= 11:
                root = EB2                       # pickup home
            t = t0 + (bar * 16 + sl) * S16
            a = 1.0 if sl == 0 else 0.8
            BASSN.append((t, root, a))

# one string, one fretting hand: each bass stroke is CHOKED when
# the next lands (letting Eb ring under a fresh Cb blurred the
# walk to 330 measured cents — the hand is part of the model)
BASSN.sort()
for i, (t, root, a) in enumerate(BASSN):
    gap = (BASSN[(i + 1) % len(BASSN)][0] - t) % LOOP_S
    nch = int((gap + 0.02) * SR)
    for kind, bus in (("bass", bass), ("bass_clean", bass_cf)):
        v = voice(kind, root)[:nch].copy()
        nf = int(0.02 * SR)
        v[-nf:] *= np.linspace(1.0, 0.0, nf)
        add_wrap(bus, t, stereo(v * a, -0.05))
BASSN = [(t, m) for t, m, a in BASSN]

mix = 0.60 * mel + 0.72 * bass
mix *= 0.92 / (np.abs(mix).max() + 1e-12)
write_wav(os.path.join(outdir, "e81_shamisen_episode.wav"), mix)

# ---- rulers ------------------------------------------------------
print("e81 rulers:")

# 1. seam
check("seam", ruler.seam_rank(mix) <= 0.999,
        f"p{100 * ruler.seam_rank(mix):.2f}")

# 2. the tune IS the tune: per-note pitch readback, own bus
mmono = mel.mean(axis=1)
mm2 = np.concatenate([mmono, mmono])
worst_c = 0.0
for t, m in MELN:
    seg = mm2[int((t + 0.02 + LOOP_S) * SR):
              int((t + 0.25 + LOOP_S) * SR)]
    p = ruler.hps_pitch(seg, fmin=250.0, fmax=520.0)
    worst_c = max(worst_c, abs(1200.0 * np.log2(p / hz(m))))
check("the_tune", worst_c <= 25.0,
        f"{len(MELN)} melody notes, worst {worst_c:.1f} cents")

# 3. the bass walks where written. Two measurement traps, both
# earned here: the don's head modes pollute the first 50 ms of
# the pitch window, and a 0.14 s frame quantizes 60-80 Hz to
# 7 Hz bins (misreads land exactly on bin multiples). So: skip
# the thump, window 0.05-0.25 s, and zero-pad for resolution.
bmono = bass.mean(axis=1)
bm2 = np.concatenate([bmono, bmono])
worst_b = 0.0
for t, m in BASSN:
    seg = bm2[int((t + 0.05 + LOOP_S) * SR):
              int((t + 0.25 + LOOP_S) * SR)]
    seg = seg * np.hanning(len(seg))
    pad = np.concatenate([seg, np.zeros(int(1.8 * SR))])
    p = ruler.hps_pitch(pad, fmin=40.0, fmax=130.0)
    worst_b = max(worst_b, abs(1200.0 * np.log2(p / hz(m))))
check("the_bass", worst_b <= 30.0,
        f"{len(BASSN)} bass strokes, worst {worst_b:.1f} cents")

# 4. the written buzz is in the render: sawari bass vs its
# clean counterfactual, 2 kHz+ energy
sos_hp = butter(4, 2000.0, btype="highpass", fs=SR, output="sos")
gain = db(rms(sosfilt(sos_hp, bmono))
        / rms(sosfilt(sos_hp, bass_cf.mean(axis=1))))
check("sawari", gain >= 5.0,
        f"sawari-on bass +{gain:.1f} dB above 2 kHz vs clean")

# 5. the don lives in its own band (melody register: no string
# partial between 150-250 Hz; the head modes are there)
v_t = shamisen(hz(63), 1.2, sawari=0.0, snap=0.6, thump=0.5)
v_0 = shamisen(hz(63), 1.2, sawari=0.0, snap=0.6, thump=0.0)
sos_th = butter(4, [150.0, 250.0], btype="bandpass", fs=SR,
        output="sos")
dgain = db(rms(sosfilt(sos_th, v_t)[:int(0.1 * SR)])
        / rms(sosfilt(sos_th, v_0)[:int(0.1 * SR)]))
check("don", dgain >= 10.0,
        f"thump band +{dgain:.1f} dB in the attack")

# 6. every bachi stroke marks time (e80 contract, new voice):
# flux argmax per stroke on hp-3200 of the MIX
sos_mk = butter(4, 3200.0, btype="highpass", fs=SR, output="sos")
hp_mix = sosfilt(sos_mk, np.concatenate(
        [mix.mean(axis=1), mix.mean(axis=1)]))
fx, dt = ruler.flux_series(hp_mix, frame=512, hop=128)
tf = np.arange(len(fx)) * dt
allst = sorted(set([t for t, m in MELN] + [t for t, m in BASSN]))
offs = []
for t in allst:
    c = t + LOOP_S
    sel = (tf >= c - 0.05) & (tf <= c + 0.07)
    offs.append(float(tf[sel][np.argmax(fx[sel])] - c))
offs = np.array(offs)
dev = np.abs(offs - np.median(offs))
check("bachi_marks", float(dev.max()) <= 0.008,
        f"{len(allst)} strokes, worst |dev-med| "
        f"{1000 * dev.max():.1f} ms")

# 7. the groove: dotted-eighth line (3 sixteenths = 2.111 Hz)
fl, pr = ruler.flux_line(mix.mean(axis=1), 2.0, 2.25)
want = 1.0 / (3.0 * S16)
check("groove_line", abs(fl - want) / want <= 0.02 and pr >= 4.0,
        f"{fl:.3f} Hz (want {want:.3f}) prom {pr:.1f}x")

# 8. Eb crowns the chroma
ch = ruler.chroma(mix)
check("chroma_Eb", int(np.argmax(ch)) == 3,
        f"crown class {int(np.argmax(ch))} (Eb=3), "
        f"share {ch[3]:.2f}")

ruler.report(mix, "e81_shamisen_episode")
print(f"\n{'ALL PASS' if not fails else 'FAILS: ' + str(fails)}")
sys.exit(1 if fails else 0)

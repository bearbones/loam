#!/usr/bin/env python3
"""loam e79 — "The Bells Learn Ektal". The caught-bell khali.

Vespers' church bells (era I) take up the 12-matra clock of
era V. Ektal's theka is rung as change-ringing never was:

    dhin dhin | dhage tirakita | tu na | kat ta |
                dhage tirakita | dhi na

Each bol maps to a fixed bell in the tower (a real belfry:
every bell hangs in one place, so every bol has one pan).
Tirakita — the four-stroke flourish — becomes a downward
peal of four small bright bells at quarter-matra spacing.

The khali (matras 3 and 7 — and matra 7's bol is literally
*kat*, both hands closed) gets a campanologist's translation:
the CAUGHT BELL. Same bell, same strike, but a hand closes on
the rim 100 ms later and the ring dies. Emptiness rendered as
a bell that dies young — and that is a measurable claim: the
caught A3's prime band must collapse where the open A3 (same
bell, matra 9) holds its ring.

A quiet PADsynth choir stands under the tower; the FDN room
from Vespers holds it all. 38.4 s seamless loop (4 avartans,
matra 0.8 s), D aeolian.

    python3 experiments/e79_ektal_bells.py [outdir]
"""

import os
import sys

import numpy as np
from scipy.signal import butter, sosfilt

sys.path.insert(0, os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))))
from loam import SR, hz, stereo, write_wav
from loam import ruler
from loam.pads import padsynth_stereo, formant_amps, VOWELS
from loam.modal import strike, CHURCH_BELL
from loam.space import reverb_loop

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
MATRA = 0.8
AV_S = 9.6                      # 12 matras
NAVART = 4
N = int(LOOP_S * SR)

# ---- the tower: one bell per bol family, fixed in space ---------
# midi: (t60, pan, bright, detune_cents)
TOWER = {
    50: (4.2, -0.40, 1.00, 4.5),        # D3  dhin/dhi — the old bell
    57: (4.2, +0.35, 1.05, 2.0),        # A3  dhage/kat
    62: (3.2, +0.10, 1.10, 0.0),        # D4  tu/ta
    65: (2.8, -0.20, 1.10, 0.0),        # F4  na
}
QUAD = [74, 69, 65, 62]                 # tirakita peal, high to low
QUAD_PAN = [+0.55, -0.55, -0.22, +0.12]
QUAD_T60 = 1.3
CATCH_T = 0.10                          # hand closes on the rim
CATCH_TAU = 0.05                        # ring dies: -60 dB in 0.35 s

# ektal: (bol, midi, mode, amp); khali at matras 3 and 7 (1-idx)
THEKA = [
    ("dhin", 50, "open", 1.15),         # sam
    ("dhin", 50, "open", 1.00),
    ("dhage", 57, "caught", 0.95),      # khali
    ("tirakita", None, "quad", 0.55),
    ("tu", 62, "open", 1.00),           # tali
    ("na", 65, "open", 0.90),
    ("kat", 57, "caught", 0.95),        # khali — the bol IS "caught"
    ("ta", 62, "open", 0.90),
    ("dhage", 57, "open", 1.00),        # tali
    ("tirakita", None, "quad", 0.55),
    ("dhi", 50, "open", 1.00),          # tali
    ("na", 65, "open", 0.90),
]

_cache = {}


def bell(midi, quad=False, caught=False):
    key = (midi, quad, caught)
    if key not in _cache:
        if quad:
            t60, br, dt = QUAD_T60, 1.35, 0.0
        else:
            t60, _, br, dt = TOWER[midi]
        v = strike(hz(midi), t60, CHURCH_BELL, amp=1.0, bright=br,
                detune=dt, rng=np.random.default_rng(midi * 7 + 1),
                knock=0.05)
        if caught:
            n0 = int(CATCH_T * SR)
            env = np.ones(len(v))
            tt = np.arange(len(v) - n0) / SR
            env[n0:] = np.exp(-tt / CATCH_TAU)
            v = (v * env)[:int(1.0 * SR)]
        _cache[key] = v / (np.abs(v).max() + 1e-12)
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


# ---- ring the theka ---------------------------------------------
bells = np.zeros((N, 2))
WRIT = []                               # (t, tag) written onsets
for a in range(NAVART):
    for m, (bol, midi, mode, amp) in enumerate(THEKA):
        t = a * AV_S + m * MATRA
        if mode == "quad":
            for k, (qm, qp) in enumerate(zip(QUAD, QUAD_PAN)):
                v = bell(qm, quad=True)
                add_wrap(bells, t + k * MATRA / 4.0,
                        stereo(v * amp, qp))
                WRIT.append((t + k * MATRA / 4.0, "quad"))
        else:
            v = bell(midi, caught=(mode == "caught"))
            pan = TOWER[midi][1]
            add_wrap(bells, t, stereo(v * amp, pan))
            WRIT.append((t, f"{bol}:{mode}"))
WRIT.sort()

# ---- the choir under the tower ----------------------------------
choir = 1.0 * padsynth_stereo(LOOP_S, hz(38), formant_amps(
        hz(38), 48, VOWELS["oh"]), bw_cents=45.0, seed=79) \
    + 0.6 * padsynth_stereo(LOOP_S, hz(45), formant_amps(
        hz(45), 40, VOWELS["oh"]), bw_cents=45.0, seed=790)
choir *= 10.0 ** ((db(rms(bells)) - 14.0 - db(rms(choir))) / 20.0)

# ---- the room ----------------------------------------------------
dry = bells + choir
wet = reverb_loop(dry, t60=2.8, size=1.15)
out = 0.80 * dry + 0.38 * wet
out *= 0.92 / (np.abs(out).max() + 1e-12)

write_wav(os.path.join(outdir, "e79_ektal_bells.wav"), out)

# ---- rulers ------------------------------------------------------
print("e79 rulers (pre-reverb bell bus unless noted):")
bmono = bells.mean(axis=1)

# 1. seam
check("seam", ruler.seam_rank(out) <= 0.999,
        f"p{100 * ruler.seam_rank(out):.2f}")

# 2. the grid: every written strike marked on time. A bell is
# never silent between strikes — detuned mode pairs beat, and
# the swells fire any global onset census (130 "onsets" for 72
# strikes at default thresholds; ghosts survive even k=16). So
# the landings ruler applies: per-written-time flux argmax on
# the band the mark owns (the contact knock, above the tower's
# highest ring mode), plus a prominence floor per mark so a
# missing strike cannot hide behind a lucky argmax.
sos_hp = butter(4, 2500.0, btype="highpass", fs=SR, output="sos")
hp2 = sosfilt(sos_hp, np.concatenate([bmono, bmono]))
fx, dt = ruler.flux_series(hp2, frame=512, hop=128)
tf = np.arange(len(fx)) * dt
wt = np.array([w[0] for w in WRIT])
offs, proms = [], []
for t in wt:
    c = t + LOOP_S              # second copy: no start-edge bias
    sel = (tf >= c - 0.05) & (tf <= c + 0.07)
    i = int(np.argmax(fx[sel]))
    offs.append(float(tf[sel][i] - c))
    nb = (tf >= c - 0.4) & (tf <= c + 0.4)
    proms.append(float(fx[sel][i] / (np.median(fx[nb]) + 1e-12)))
offs = np.array(offs)
med = float(np.median(offs))
dev = offs - med
check("grid_marks", float(np.max(np.abs(dev))) <= 0.008,
        f"72 marks, worst |dev-med| {1000 * np.max(np.abs(dev)):.1f}"
        f" ms (detector med {1000 * med:.1f} ms)")
check("grid_present", min(proms) >= 3.0,
        f"weakest mark {min(proms):.1f}x its local flux floor")

# 3. the caught bell: A3 prime band, level drop 110->500 ms
f57 = hz(57)
sos = butter(4, [f57 * 0.91, f57 * 1.10], btype="bandpass",
        fs=SR, output="sos")
bp = sosfilt(sos, np.concatenate([bmono, bmono]))[N:]
drops = {"caught": [], "open": []}
for a in range(NAVART):
    for m, (bol, midi, mode, amp) in enumerate(THEKA):
        if midi != 57:
            continue
        t = a * AV_S + m * MATRA
        e = rms(bp[int((t + 0.06) * SR):int((t + 0.16) * SR)])
        l = rms(bp[int((t + 0.42) * SR):int((t + 0.58) * SR)])
        drops[mode].append(db(e / l))
cmin = min(drops["caught"])
omax = max(drops["open"])
check("khali_caught", cmin >= 15.0,
        f"caught A3 drop min {cmin:.1f} dB (8 strikes, gate >=15)")
check("bhari_open", omax <= 8.0,
        f"open A3 drop max {omax:.1f} dB (4 strikes, gate <=8)")
check("khali_sep", cmin - omax >= 8.0,
        f"separation {cmin - omax:.1f} dB (gate >=8)")

# 4. tirakita peal: 4 strikes at matra/4 inside each flourish,
# measured from the same flux marks (absolute measured times)
tm = wt + offs
worst_q = 0.0
for a in range(NAVART):
    for m0 in (3, 9):
        t0 = a * AV_S + m0 * MATRA
        i = np.where((wt >= t0 - 0.01) & (wt < t0 + 0.7))[0]
        worst_q = max(worst_q, float(np.max(np.abs(
                np.diff(tm[i]) - MATRA / 4.0))))
check("tirakita", worst_q <= 0.01,
        f"worst intra-peal spacing error {1000 * worst_q:.1f} ms")

# 5. the taal breathes at matra rate
fl, pr = ruler.flux_line(bmono, 1.15, 1.35, mask=(0.8, 20.0))
check("matra_line", abs(fl - 1.25) / 1.25 <= 0.02 and pr >= 5.0,
        f"{fl:.3f} Hz (want 1.250) prom {pr:.1f}x")
fl2, pr2 = ruler.flux_line(bmono, 4.6, 5.4, mask=(0.8, 20.0))
print(f"  info tirakita_line: {fl2:.3f} Hz prom {pr2:.1f}x")

# 6. dhin bell identity: hum + prime of the D3 sample (own-bus)
mf = ruler.mode_freqs(bell(50), k=6, fmin=50.0, fmax=700.0)
f0 = hz(50)
hum_ok = np.any(np.abs(mf / (0.5 * f0) - 1.0) < 0.012)
pri_ok = np.any(np.abs(mf / f0 - 1.0) < 0.012)
check("dhin_bell", hum_ok and pri_ok,
        f"hum@{0.5 * f0:.1f} {hum_ok}, prime@{f0:.1f} {pri_ok} "
        f"in modes {np.round(mf, 1)}")

# 7. the choir stays under the tower
bal = db(rms(choir)) - db(rms(bells))
check("balance", -20.0 <= bal <= -8.0,
        f"choir at {bal:+.1f} dB vs bells (design -14)")

# 8. home key: D crowns the chroma (on the mix)
ch = ruler.chroma(out)
check("chroma_D", int(np.argmax(ch)) == 2,
        f"crown class {int(np.argmax(ch))} (D=2), "
        f"D share {ch[2]:.2f}")

ruler.report(out, "e79_ektal_bells")
print(f"\n{'ALL PASS' if not fails else 'FAILS: ' + str(fails)}")
sys.exit(1 if fails else 0)

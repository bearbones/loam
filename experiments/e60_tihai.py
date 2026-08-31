#!/usr/bin/env python3
"""e60 — tihai: the kaida learns to end.

Refinement of e59's bol vocabulary: kaida DEVELOPMENT, the
rhythmic argument. Four avartans (19.2 s):

  1. theme (bhari)      dha dha te te | dha dha tun na |
                        dha dha te te | dha dha dhin na
  2. palta              cells of the theme rearranged
  3. khali palta        same argument, bass withheld (ke),
                        bass returning in the last bar
  4. TIHAI              dha, then "tirakita tun dha" x3 with
                        equal 2-slot gaps

Two new rhythmic devices, both measured against design:
  - tirakita: the grid opens to HALF-slots — four te strokes
    at 150 ms spacing (the te consonant from e59 was built for
    this: a 30 ms thud can articulate at 6.67 Hz).
  - the tihai lands its third dha ON SAM — which in a loop is
    the wrap itself. The phrase-final dhas at slots 52, 58, 64
    are equally spaced 1.8 s apart and the last one IS the
    theme's opening stroke of the next pass (measured across
    the seam, e56 practice). The rests around the tihai are
    design too: the onset ruler must find NOTHING there.

    python3 experiments/e60_tihai.py [outdir]
"""

import os
import subprocess
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))))
from loam import SR, hz, Loop, stereo, write_wav
from loam import ruler
from loam.fdstring import fdpluck2
from loam.membrane import fddrum

outdir = sys.argv[1] if len(sys.argv) > 1 else "render"
os.makedirs(outdir, exist_ok=True)
fails = []


def check(name, cond, detail):
    print(f"  {'PASS' if cond else 'FAIL'} {name}: {detail}")
    if not cond:
        fails.append(name)


# ---- e59 vocabulary (certified there, reused here) -------------
LOAD, RS = 40.0, 0.45
F1, F1A, F1D = 283.8, 105.6, 141.2
na = fddrum(F1, 1.5, strike=(0.55, 0.0), load=LOAD, rs=RS,
        sig_s=60.0)
tun = fddrum(F1, 1.5, strike=(0.0, 0.0), load=LOAD, rs=RS,
        sig_s=60.0)
te = fddrum(F1, 0.5, strike=(0.55, 0.0), load=LOAD, rs=RS,
        sig0=200.0, sig_s=60.0)
ge = fddrum(F1A, 1.0, strike=(0.30, 0.0), load=LOAD, rs=RS,
        sig0=9.0, sig_s=20.0)
ke = fddrum(F1A, 0.5, strike=(0.30, 0.0), load=LOAD, rs=RS,
        sig0=45.0, sig_s=20.0)
ge_sam = fddrum(F1D, 1.0, strike=(0.30, 0.0), load=LOAD, rs=RS,
        sig0=9.0, sig_s=20.0)

TRE = {"dha": (na, 1.0), "ta": (na, 1.0), "na": (na, 0.9),
        "tun": (tun, 0.95), "dhin": (tun, 0.95), "te": (te, 0.8)}
BAS = {"dha": (ge, 0.9), "dhin": (ge, 0.9), "ta": (ke, 0.8)}

# ---- the form --------------------------------------------------
SUB = 0.3
NB = 16
LOOP_S = 4 * NB * SUB          # 19.2 s
L = int(LOOP_S * SR)

THEME = ["dha", "dha", "te", "te", "dha", "dha", "tun", "na",
        "dha", "dha", "te", "te", "dha", "dha", "dhin", "na"]
PALTA = ["dha", "dha", "te", "te", "te", "te", "dha", "dha",
        "dha", "dha", "tun", "na", "dha", "dha", "dhin", "na"]
PALTA_K = ["ta", "ta", "te", "te", "te", "te", "ta", "ta",
        "ta", "ta", "tun", "na", "dha", "dha", "dhin", "na"]

EVENTS = []                    # (slot_float, bol)
for i, b in enumerate(THEME):
    EVENTS.append((i, b))
for i, b in enumerate(PALTA):
    EVENTS.append((16 + i, b))
for i, b in enumerate(PALTA_K):
    EVENTS.append((32 + i, b))
EVENTS.append((48, "dha"))     # sam of avartan 4
TIHAI_STARTS = (49, 55, 61)
for s in TIHAI_STARTS:         # tirakita tun (dha)
    for h in (0.0, 0.5, 1.0, 1.5):
        EVENTS.append((s + h, "te"))
    EVENTS.append((s + 2, "tun"))
    if s + 3 < 64:             # the third dha IS the wrap
        EVENTS.append((s + 3, "dha"))
REST_SLOTS = {53, 54, 59, 60}
KHALI_SLOTS = set(range(32, 44))

tre = np.zeros(L + 2 * SR)
bas = np.zeros(L + 2 * SR)
for t_slot, b in EVENTS:
    a = int(t_slot * SUB * SR)
    v, g = TRE[b]
    tre[a:a + len(v)] += v * g
    if b in BAS:
        v, g = BAS[b]
        if b == "dha" and t_slot == 0:
            v = ge_sam         # sam arrives pressed (e56)
        bas[a:a + len(v)] += v * g
tre, bas = tre[:L], bas[:L]
drums = stereo(tre, 0.25) + stereo(bas, -0.25)

# ---- own-bus: every designed onset, and ONLY those -------------
design = sorted(t * SUB for t, _ in EVENTS) + [LOOP_S]
dbl = np.concatenate([drums, drums]).mean(axis=1)
onsets = np.array([t for t in ruler.onset_times(dbl,
        min_sep=0.12) if t <= LOOP_S + 0.06])
d = np.asarray(design)
miss = [dt for dt in d
        if not (np.abs(onsets - dt) <= 0.05).any()]
extra = [t for t in onsets
        if not (np.abs(d - t) <= 0.06).any()]
check("every designed stroke sounds", len(miss) == 0,
        f"{len(d) - len(miss)}/{len(d)} design onsets matched "
        f"within 50 ms" + (f", missing at {miss}" if miss else ""))
check("and nothing else does", len(extra) == 0,
        f"{len(extra)} unexplained onsets (the tihai's rests "
        f"must be silent)" + (f": {extra}" if extra else ""))

# ---- own-bus: the half-slot grid -------------------------------
iois = []
for s in TIHAI_STARTS:
    t0 = s * SUB
    run = np.sort(onsets[(onsets >= t0 - 0.05)
            & (onsets <= t0 + 3 * 0.5 * SUB + 0.05)])
    if len(run) == 4:
        iois.extend(np.diff(run))
dev = (np.abs(np.array(iois) - 0.5 * SUB).max() * 1000
        if len(iois) == 9 else 999.0)
check("tirakita articulates the half-grid",
        len(iois) == 9 and dev <= 20.0,
        f"{len(iois)}/9 inter-onset intervals in the three runs, "
        f"worst |IOI - 150 ms| = {dev:.0f} ms")

# ---- own-bus: the tihai lands on sam ---------------------------
lands = []
for k in (52, 58, 64):
    tt = k * SUB
    cand = onsets[np.abs(onsets - tt) <= 0.05]
    if len(cand):
        lands.append(float(cand[np.argmin(np.abs(cand - tt))]))
gaps = np.diff(lands) if len(lands) == 3 else np.array([0.0])
check("the tihai lands on sam", len(lands) == 3
        and np.abs(gaps - 6 * SUB).max() <= 0.03,
        f"phrase-final dhas at {[f'{x:.2f}' for x in lands]} s — "
        f"equal gaps {[f'{g:.3f}' for g in gaps]} (design 1.800), "
        f"third dha = the wrap itself")

# ---- own-bus: khali and pulse ----------------------------------
w0, w1 = int(0.08 * SR), int(0.28 * SR)
mono_d = drums.mean(axis=1)
hann = np.hanning(w1 - w0)


def band_rms(seg):
    p = np.abs(np.fft.rfft(seg * hann)) ** 2
    f = np.fft.rfftfreq(len(seg), 1.0 / SR)
    return float(np.sqrt(p[(f >= 30.0) & (f <= 100.0)].sum()))


nslots = 4 * NB
be = np.array([band_rms(mono_d[int(k * SUB * SR) + w0:
        int(k * SUB * SR) + w1]) for k in range(nslots)])
kh = np.array([k in KHALI_SLOTS for k in range(nslots)])
bh = np.array([k not in KHALI_SLOTS and k not in REST_SLOTS
        for k in range(nslots)])
hole = float(np.median(be[kh]) / np.median(be[bh]))
check("the khali quarter is a bass hole", hole <= 0.35,
        f"khali/bhari sustained bass-band slot energy {hole:.3f}")
pr = ruler.pulse_rate(drums.mean(axis=1), 2.0, 5.0,
        lo=300.0, hi=2500.0)
check("the pulse survives the development",
        abs(pr - 1.0 / SUB) <= 0.2,
        f"designed {1.0 / SUB:.2f} Hz, measured {pr:.2f} Hz "
        f"under paltas, rests and half-slot runs")

# ---- the mix ---------------------------------------------------
DRONE = [("pa", hz(45), 140, 0.0, -0.35, 0.55),
        ("sa+", hz(50.015), 112, 1.2, 0.15, 0.50),
        ("sa-", hz(49.985), 112, 2.4, -0.15, 0.50),
        ("SA", hz(38), 138, 3.6, 0.35, 0.75)]
loop = Loop(LOOP_S, seed=60)
for name, f0d, n, at, pan, ampd in DRONE:
    v = fdpluck2(f0d, 12.0, amp=ampd, N=n)
    for off in (0.0, 4.8, 9.6, 14.4):
        loop.add(at + off, stereo(v, pan))
loop.add(0.0, drums * 0.8)
mix = loop.master(lp_hz=6500.0, drive=1.2)

check("seam", ruler.seam_rank(mix) <= 0.999,
        f"p{100 * ruler.seam_rank(mix):.2f}")
ch = ruler.chroma(mix.mean(axis=1))
top2 = set(np.argsort(ch)[-2:].tolist())
check("D and A are the two poles", top2 == {2, 9},
        f"top-2 classes {sorted(top2)}")

out = np.concatenate([mix, mix])
wav = os.path.join(outdir, "e60_tihai.wav")
write_wav(wav, out)
ruler.report(out, "tihai")
subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", wav,
        "-q:a", "5", wav.replace(".wav", ".ogg")], check=True)

print("ALL RULERS PASS" if not fails else f"FAILED: {fails}")
sys.exit(1 if fails else 0)

#!/usr/bin/env python3
"""e52 — jhala: the raga arc reaches its fast texture.

After alap (e46), gamak (e47), jor (e49): jhala, the climactic
register where rapid chikari strikes (high drone strings, here
Sa and Pa above the melody) fill every subdivision between
ACCENTED melody notes. The texture is an accent hierarchy on a
fast grid — melody strikes ring over their chikari group — and
that hierarchy is exactly what the new ruler measures.

ruler.accent_profile: per-onset attack PEAK (not RMS — ring-over
crosses RMS windows but barely moves an attack peak). On the
solo's own bus: every subdivision strikes its slot, the pulse
reads back, melody-slot accents clear chikari-slot accents by a
measured margin, the 4-slot grouping is the DOMINANT period of
the accent series' spectrum, every melody pitch reads back, and
the line still lives on Sa. A uniform control bus (all slots
struck alike) must FAIL the hierarchy and grouping tests — the
thresholds sit between the measured control and the measured
piece. The mix keeps the drone's seam and poles.

    python3 experiments/e52_jhala.py [outdir]
"""

import os
import subprocess
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))))
from loam import SR, hz, Loop, stereo, write_wav
from loam import ruler
from loam.fdstring import fdpluck, fdpluck2
from loam.strings import pluck

outdir = sys.argv[1] if len(sys.argv) > 1 else "render"
os.makedirs(outdir, exist_ok=True)
fails = []


def check(name, cond, detail):
    print(f"  {'PASS' if cond else 'FAIL'} {name}: {detail}")
    if not cond:
        fails.append(name)


SUB = 0.15                     # 6.67 Hz chikari subdivision
NP = 48                        # 7.2 s loop
GROUP = 4                      # melody every 4th slot
KAFI = {2, 4, 5, 7, 9, 11, 0}

# melody: one note per group, ringing across its chikari trio;
# double Sa at the cadence so the line LIVES there (dwell needs
# a margin, not a tie)
LINE = [50, 52, 53, 55, 57, 60, 59, 57, 55, 53, 50, 50]
assert len(LINE) == NP // GROUP
assert all(m % 12 in KAFI for m in LINE)
CHIK = (74, 81)                # high Sa + high Pa, above melody


def render_solo(mel_amp, chik_amp, fill_all=False):
    solo = np.zeros(int(NP * SUB * SR) + SR)
    if mel_amp > 0:
        for g, m in enumerate(LINE):
            v = fdpluck(np.full(100, hz(m)), GROUP * SUB + 0.08,
                    amp=mel_amp)
            a = int(g * GROUP * SUB * SR)
            solo[a:a + len(v)] += v
    for k in range(NP):
        if k % GROUP == 0 and not fill_all:
            continue
        a = int(k * SUB * SR)
        for c, w in zip(CHIK, (1.0, 0.7)):
            v = pluck(hz(c), 0.3, t60=0.25, damp=0.25,
                    seed=k * 5 + c) * chik_amp * w
            solo[a:a + len(v)] += v
    return solo[:int(NP * SUB * SR)]


solo = render_solo(0.9, 0.3)
# control: every slot struck ALIKE — chikari on the melody slots
# too. (A first control left melody slots EMPTY: a hole every
# 4th slot is itself a period-4 signature, x18 in the accent
# spectrum. 'No hierarchy' must mean equal strikes, not silence)
uniform = render_solo(0.0, 0.3, fill_all=True)
slot_t = np.arange(NP) * SUB

# ---- own-bus: every slot strikes, the pulse reads --------------
onsets = ruler.onset_times(np.concatenate([solo, solo]),
        min_sep=0.09)
slots = {}
for t in onsets:
    k = int(round(t / SUB))
    if abs(t - k * SUB) <= 0.05:
        slots.setdefault(k % NP, t)      # e49: wrap the index
check("every subdivision strikes its slot", len(slots) == NP,
        f"{len(slots)}/{NP} onsets within 50 ms of grid")
pr = ruler.pulse_rate(solo, 5.0, 8.5)
check("the jhala pulse reads back", abs(pr - 1.0 / SUB) <= 0.3,
        f"designed {1.0 / SUB:.2f} Hz, measured {pr:.2f} Hz")

# ---- own-bus: the accent hierarchy -----------------------------
acc = ruler.accent_profile(solo, slot_t)
acc_u = ruler.accent_profile(uniform, slot_t)
mel = acc[::GROUP]
chik = np.delete(acc, np.arange(0, NP, GROUP))
ratio = float(np.median(mel) / np.median(chik))
mel_u = acc_u[::GROUP]
chik_u = np.delete(acc_u, np.arange(0, NP, GROUP))
ratio_u = float(np.median(mel_u) / (np.median(chik_u) + 1e-12))
# margin calibrated between the measured all-slots-alike control
# (x0.99) and the measured piece (x20.1) — log-midpoint ~4.5
check("melody strikes carry the accent", ratio >= 3.0,
        f"melody/chikari accent ratio x{ratio:.2f} "
        f"(uniform control x{ratio_u:.2f})")
check("the control has no hierarchy", ratio_u < 3.0,
        f"control ratio x{ratio_u:.2f} — the ruler can say no")


def group_period(a):
    s = a - a.mean()
    F = np.abs(np.fft.rfft(s))
    k = int(np.argmax(F[1:])) + 1
    med = float(np.median(np.delete(F[1:], k - 1)))
    return k, F[k] / (med + 1e-12)


kp, kstr = group_period(acc)
kp_u, kstr_u = group_period(acc_u)
# calibrated between control (best bin x2.3) and piece (x11)
check("the 4-slot grouping is the accent period",
        kp == NP // GROUP and kstr >= 4.0,
        f"accent spectrum peaks at {kp} cycles/loop "
        f"(want {NP // GROUP}) at x{kstr:.1f} the median bin")
check("the control has no grouping",
        not (kp_u == NP // GROUP and kstr_u >= 4.0),
        f"control peak {kp_u} cycles at x{kstr_u:.1f}")

# ---- own-bus: every melody pitch, and the line lives on Sa -----
worst = 0.0
for g, m in enumerate(LINE):
    a0 = int((g * GROUP * SUB + 0.01) * SR)
    seg = solo[a0:a0 + int(0.5 * SR)].copy()
    fd = int(0.03 * SR)
    seg[-fd:] *= np.linspace(1, 0, fd)
    f0 = ruler.hps_pitch(seg, fmin=80.0, fmax=400.0)
    worst = max(worst, abs(1200 * np.log2(f0 / hz(m))))
check("every melody note reads back", worst <= 25.0,
        f"worst {worst:.1f} cents across {len(LINE)} notes "
        f"(chikari live above the 400 Hz fence)")
ts, fs = ruler.pitch_contour(solo, fmin=80.0, fmax=400.0)
dw = ruler.dwell_seconds(ts, fs, hz(50))
check("the line lives on Sa", int(np.argmax(dw)) == 0,
        f"dwell argmax class {int(np.argmax(dw))} "
        f"({dw[0]:.1f}s on Sa)")

# ---- the piece: jhala over the breathing drone -----------------
DRONE = [("pa", hz(45), 140, 0.0, -0.35, 0.55),
        ("sa+", hz(50.015), 112, 0.9, 0.15, 0.50),
        ("sa-", hz(49.985), 112, 1.8, -0.15, 0.50),
        ("SA", hz(38), 138, 2.7, 0.35, 0.75)]
loop = Loop(NP * SUB, seed=52)
for name, f0, n, at, pan, amp in DRONE:
    v = fdpluck2(f0, 12.0, amp=amp, N=n)
    loop.add(at, stereo(v, pan))
    loop.add(at + 3.6, stereo(v, pan))
loop.add(0.0, stereo(solo, 0.0))
mix = loop.master(lp_hz=6500.0, drive=1.2)

check("seam", ruler.seam_rank(mix) <= 0.999,
        f"p{100 * ruler.seam_rank(mix):.2f}")
prm = ruler.pulse_rate(mix.mean(axis=1), 5.0, 8.5)
check("the pulse survives the mix", abs(prm - 1.0 / SUB) <= 0.3,
        f"measured {prm:.2f} Hz in the full render")
ch = ruler.chroma(mix.mean(axis=1))
top2 = set(np.argsort(ch)[-2:].tolist())
check("D and A are the two poles", top2 == {2, 9},
        f"top-2 classes {sorted(top2)}")

out = np.concatenate([mix, mix])
wav = os.path.join(outdir, "e52_jhala.wav")
write_wav(wav, out)
ruler.report(out, "jhala")
subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", wav,
        "-q:a", "5", wav.replace(".wav", ".ogg")], check=True)

print("ALL RULERS PASS" if not fails else f"FAILED: {fails}")
sys.exit(1 if fails else 0)

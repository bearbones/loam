#!/usr/bin/env python3
"""e49 — jor: the line acquires a pulse.

After alap (e46) and ornament (e47), the raga arc's next stage:
jor, melody carried on a steady right-hand pulse, no tala cycle
yet — just time made audible. The solo is 24 pulses at 2.5 Hz
over the two-polarization drone (e48), every note a designed
(midi, pulses, glide) triple in Kafi: plain notes dwell, held
notes MEEND into their successor across the pulse boundary, and
the cadence rests on Sa.

Everything the design declares is recovered from the solo's own
bus: the pulse grid (every onset within 60 ms of its slot, rate
read back by pulse_rate), every note's pitch (contour median
over the hold, +/-20 cents), every meend's landing (contour just
before the next onset, +/-25 cents), and the line still LIVES on
Sa (dwell_seconds argmax). The mix keeps the drone's seam and
poles.

    python3 experiments/e49_jor.py [outdir]
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

outdir = sys.argv[1] if len(sys.argv) > 1 else "render"
os.makedirs(outdir, exist_ok=True)
fails = []


def check(name, cond, detail):
    print(f"  {'PASS' if cond else 'FAIL'} {name}: {detail}")
    if not cond:
        fails.append(name)


PULSE = 0.4                       # 2.5 Hz, 24 pulses = 9.6 s loop
NP = 24

# ---- the line: (midi, pulses, glide_to) in Kafi ----------------
LINE = [(50, 1, None), (52, 1, None), (53, 1, None), (52, 1, None),
        (50, 1, None), (53, 1, None), (55, 2, 57),
        (57, 1, None), (60, 1, None), (57, 1, None), (55, 2, 53),
        (53, 1, None), (52, 1, None), (50, 1, None), (48, 1, None),
        (50, 2, None),
        (55, 1, None), (53, 1, None), (52, 1, None), (50, 2, None)]
assert sum(p for _, p, _ in LINE) == NP, "line must fill the loop"
KAFI = {2, 4, 5, 7, 9, 11, 0}
assert all(m % 12 in KAFI for m, _, _ in LINE)
assert all(g is None or g % 12 in KAFI for _, _, g in LINE)

# ---- render the solo -------------------------------------------
notes = []                        # (at_s, dur_s, midi, glide_to)
at = 0.0
for m, p, g in LINE:
    notes.append((at, p * PULSE + 0.15, m, g))
    at += p * PULSE

solo = np.zeros(int(NP * PULSE * SR) + SR)
for at, dur, m, g in notes:
    n = int(dur * SR)
    if g is None:
        traj = np.full(n, hz(m))
    else:
        # hold 55% of the sounding time, then meend to the
        # successor so the glide LANDS as the next pulse strikes
        nh = int(0.55 * (dur - 0.15) * SR)
        ng = int((dur - 0.15) * SR) - nh
        traj = np.concatenate([np.full(nh, hz(m)),
                hz(m) * (hz(g) / hz(m))
                ** np.linspace(0, 1, ng),
                np.full(n - nh - ng, hz(g))])
    v = fdpluck(traj, dur, amp=0.9)
    a = int(at * SR)
    solo[a:a + len(v)] += v
solo = solo[:int(NP * PULSE * SR)]

# ---- own-bus rulers: the pulse ---------------------------------
# doubled signal: spectral flux is blind to a strike at t=0 (no
# prior frame to rise from), so slot 0 is recovered from the
# SECOND pass — fold the slot index back around the loop
onsets = ruler.onset_times(np.concatenate([solo, solo]),
        min_sep=0.25)
slots = {}
for t in onsets:
    k = int(round(t / PULSE))
    if abs(t - k * PULSE) <= 0.06:
        slots.setdefault(k % NP, t)
want_slots = set()
at = 0
for _, p, _ in LINE:
    want_slots.add(at)
    at += p
check("every note strikes its slot", set(slots) == want_slots,
        f"{len(slots)}/{len(LINE)} onsets within 60 ms of grid")
pr = ruler.pulse_rate(solo, 1.5, 4.0)
check("the pulse reads back", abs(pr - 2.5) <= 0.15,
        f"designed 2.5 Hz, measured {pr:.2f} Hz")

# ---- own-bus rulers: every pitch, every landing ----------------
ts, fs = ruler.pitch_contour(solo, fmin=80.0, fmax=800.0)
worst_note = worst_land = 0.0
for at, dur, m, g in notes:
    hold = 0.55 * (dur - 0.15) if g is not None else (dur - 0.15)
    a, b = at + 0.12, at + max(hold - 0.02, 0.2)
    sel = (ts >= a) & (ts <= b)
    if sel.sum() >= 1:
        med = float(np.median(fs[sel]))
        worst_note = max(worst_note,
                abs(1200 * np.log2(med / hz(m))))
    if g is not None:
        land = at + (dur - 0.15)
        sel = (ts >= land - 0.12) & (ts <= land + 0.05)
        if sel.sum() >= 1:
            med = float(np.median(fs[sel]))
            worst_land = max(worst_land,
                    abs(1200 * np.log2(med / hz(g))))
check("every note holds its pitch", worst_note <= 20.0,
        f"worst hold {worst_note:.1f} cents across "
        f"{len(notes)} notes")
check("every meend lands on its successor", worst_land <= 25.0,
        f"worst landing {worst_land:.1f} cents")
dw = ruler.dwell_seconds(ts, fs, hz(50))
check("the line lives on Sa", int(np.argmax(dw)) == 0,
        f"dwell argmax class {int(np.argmax(dw))} "
        f"({dw[0]:.1f}s on Sa)")

# ---- the piece: pulse over the breathing drone -----------------
DRONE = [("pa", hz(45), 140, 0.0, -0.35, 0.60),
        ("sa+", hz(50.015), 112, 1.2, 0.15, 0.55),
        ("sa-", hz(49.985), 112, 2.4, -0.15, 0.55),
        ("SA", hz(38), 138, 3.6, 0.35, 0.80)]
loop = Loop(NP * PULSE, seed=49)
for name, f0, n, at, pan, amp in DRONE:
    v = fdpluck2(f0, 12.0, amp=amp, N=n)
    loop.add(at, stereo(v, pan))
    loop.add(at + 4.8, stereo(v, pan))
loop.add(0.0, stereo(solo, 0.0))

mix = loop.master(lp_hz=6500.0, drive=1.2)
check("seam", ruler.seam_rank(mix) <= 0.999,
        f"p{100 * ruler.seam_rank(mix):.2f}")
ch = ruler.chroma(mix.mean(axis=1))
top2 = set(np.argsort(ch)[-2:].tolist())
check("D and A are the two poles", top2 == {2, 9},
        f"top-2 classes {sorted(top2)}")

out = np.concatenate([mix, mix])
wav = os.path.join(outdir, "e49_jor.wav")
write_wav(wav, out)
ruler.report(out, "jor")
subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", wav,
        "-q:a", "5", wav.replace(".wav", ".ogg")], check=True)

print("ALL RULERS PASS" if not fails else f"FAILED: {fails}")
sys.exit(1 if fails else 0)

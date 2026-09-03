#!/usr/bin/env python3
"""loam e90 — koto: the paulownia zither (sankyoku's third voice).

nihon.koto(): fdpluck2 as the shamisen's clean-string cousin —
barrier parked (no sawari), longer ring (sig0 0.55 vs 1.1),
hard tsume pick near the bridge (pick 0.86, click band up to
10.5 kHz), plus:

  - OSHIDE: the left hand presses behind the bridge AFTER the
    pluck and the sounding pitch rises — a smoothstep warp of
    the decaying note (the honest bend, same stance as the
    shakuhachi scoop). The plucked string's IF track is clean
    enough to claim the bend DIRECTLY: no twins, no tricks —
    design 180 c, measured 179.9 c on the prototype;
  - a paulownia-box body: two parallel resonant bands (~230 /
    ~560 Hz) added zero-phase. Causal filters CANCELLED
    (-1.3 dB where the design said +5) — a bandpass adds ~90
    degrees out of phase unless filtfilt'd. The body claim is
    SCOPED to notes whose fundamentals live in-band (A3, Bb3):
    on D3 the band is empty and the boost is unmeasurable
    (e84's register of validity).

The piece: 30 s solo loop in hirajoshi on D3 (D Eb G A Bb).
An ascending kararin sweep opens, three phrases with oshide
bends (+180, +100, +200 c), a short descending sweep, and a
low D3 with left-hand vibrato to close.

    python3 experiments/e90_koto_hirajoshi.py [outdir]
"""

import os
import sys

import numpy as np
from scipy.signal import butter, sosfilt

sys.path.insert(0, os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))))
from loam import SR, hz, stereo, write_wav
from loam import ruler
from loam.nihon import koto, HIRAJOSHI
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


LOOP_S = 30.0
N = int(LOOP_S * SR)

# ladder of hirajoshi midis from D3
LADDER = [50 + 12 * o + s for o in range(3) for s in HIRAJOSHI]

# sweeps: (start, [midis], gap_s, amp0, amp1)
SWEEPS = [
    (0.6, LADDER[0:10], 0.060, 0.50, 0.90),          # D3..Bb4 up
    (14.5, [74, 70, 69, 67, 63, 62], 0.070, 0.75, 0.55),  # down
]
# plucked notes: (start, midi, dur, bend_c, bend_at, vib_c, amp,
#  pan)
PLUCKS = [
    (2.0, 62, 2.2, 0.0, 0.0, 0.0, 0.85, 0.10),
    (4.2, 57, 2.0, 0.0, 0.0, 0.0, 0.80, -0.08),
    (6.1, 58, 2.6, 180.0, 0.50, 0.0, 0.90, 0.05),    # oshide 1
    (8.9, 67, 1.6, 0.0, 0.0, 0.0, 0.80, 0.12),
    (10.4, 63, 2.2, 100.0, 0.45, 0.0, 0.85, -0.05),  # oshide 2
    (12.4, 62, 2.6, 0.0, 0.0, 12.0, 0.85, 0.0),
    (16.6, 57, 2.0, 0.0, 0.0, 0.0, 0.80, -0.10),
    (18.8, 58, 1.6, 0.0, 0.0, 0.0, 0.75, 0.08),
    (20.6, 57, 3.2, 200.0, 0.35, 0.0, 0.95, 0.0),    # oshide 3
    (24.4, 62, 1.8, 0.0, 0.0, 0.0, 0.80, 0.10),
    (26.2, 63, 1.5, 0.0, 0.0, 0.0, 0.75, -0.06),
    (27.4, 50, 4.6, 0.0, 0.0, 10.0, 1.00, 0.0),      # low close
]
BENDS = [i for i, p in enumerate(PLUCKS) if p[3] > 0.0]


def add_wrap(bus, t, ss):
    i0 = int(round(t * SR)) % N
    n = len(ss)
    if i0 + n <= N:
        bus[i0:i0 + n] += ss
    else:
        k = N - i0
        bus[i0:] += ss[:k]
        bus[:n - k] += ss[k:]


NOTES = []
kt = np.zeros((N, 2))
for t, m, dur, bc, ba, vc, a, pn in PLUCKS:
    v = koto(hz(m), dur, bend_c=bc, bend_at=ba, vib_c=vc,
            body=0.55, tsume=0.85)
    NOTES.append(v)
    add_wrap(kt, t, stereo(v * a, pn))

swb = np.zeros((N, 2))
SW_ON = []
for t0, midis, gap, a0, a1 in SWEEPS:
    for j, m in enumerate(midis):
        a = a0 + (a1 - a0) * j / max(1, len(midis) - 1)
        v = koto(hz(m), 1.3, body=0.55, tsume=0.7)
        tt = t0 + j * gap
        SW_ON.append((tt, m))
        add_wrap(swb, tt, stereo(v * a, -0.25 + 0.5 * j
                / max(1, len(midis) - 1)))

dry = 0.9 * kt + 0.75 * swb
wet = reverb_loop(dry, t60=1.9, size=1.1)
mix = 0.84 * dry + 0.26 * wet
mix *= 0.92 / (np.abs(mix).max() + 1e-12)
write_wav(os.path.join(outdir, "e90_koto_hirajoshi.wav"), mix)

# ---- rulers ------------------------------------------------------
print("e90 rulers (own-buffer claims per note; sweep on its bus):")

# 1. every unbent pluck centers on its written pitch
worst_c = 0.0
for v, (t, m, dur, bc, ba, vc, a, pn) in zip(NOTES, PLUCKS):
    if bc > 0.0:
        continue
    inst = ruler.if_pitch(v, hz(m))
    s1 = min(1.2, dur - 0.3)
    c = 1200.0 * np.log2(np.median(
            inst[int(0.25 * SR):int(s1 * SR)]) / hz(m))
    worst_c = max(worst_c, abs(c))
check("centers", worst_c <= 12.0,
        f"{len(PLUCKS) - len(BENDS)} plucks, worst center "
        f"{worst_c:+.1f} c")

# 2. oshide, design vs measured, DIRECTLY on the IF track (the
# pluck's SNR affords what the breathy winds never did)
worst_b = 0.0
det = []
for i in BENDS:
    t, m, dur, bc, ba, vc, a, pn = PLUCKS[i]
    f0 = hz(m)
    inst = ruler.if_pitch(NOTES[i], f0,
            band=(0.93, 1.075 * 2.0 ** (bc / 1200.0)))
    pre = 1200.0 * np.log2(np.median(inst[
            int(max(0.10, ba - 0.20) * SR):
            int((ba - 0.04) * SR)]) / f0)
    p0 = ba + 0.22 + 0.08
    post = 1200.0 * np.log2(np.median(inst[
            int(p0 * SR):int(min(p0 + 0.55, dur - 0.25) * SR)])
            / f0)
    d = post - pre
    worst_b = max(worst_b, abs(d - bc))
    det.append(f"{bc:.0f}->{d:+.0f}")
check("oshide", worst_b <= 15.0,
        f"written->measured cents: {', '.join(det)} "
        f"(worst |err| {worst_b:.1f})")

# 3. the tsume speaks: click-band attack towers over the note's
# own sustain, and over a pickless twin's attack
sos_t = butter(4, [3500.0, 10500.0], btype="bandpass", fs=SR,
        output="sos")


def _atk(v):
    h = sosfilt(sos_t, v)
    return 20.0 * np.log10(
            (rms(h[:int(0.012 * SR)]) + 1e-30)
            / (rms(h[int(0.5 * SR):int(0.9 * SR)]) + 1e-30))


# scoped to D4/A3: at G4 and above the string's own harmonics
# fill the click band and the contrast is register-limited
# (e84's register of validity)
worst_t = 99.0
for i in (0, 1):
    worst_t = min(worst_t, _atk(NOTES[i]))
tw = koto(hz(PLUCKS[0][1]), PLUCKS[0][2], tsume=0.0, body=0.55)
dt = _atk(NOTES[0]) - _atk(tw)
check("tsume", worst_t >= 12.0 and dt >= 6.0,
        f"worst attack/sustain {worst_t:+.1f} dB (D4, A3), "
        f"+{dt:.1f} dB over pickless twin")

# 4. the box answers — SCOPED to notes whose fundamentals live
# in the 190-270 Hz resonance (A3 220, Bb3 233); on D3 the band
# is empty and the claim would be vacuous (e84's register)
sos_b = butter(2, [190.0, 270.0], btype="bandpass", fs=SR,
        output="sos")
worst_bo = 99.0
for i in (1, 7):
    t, m, dur, bc, ba, vc, a, pn = PLUCKS[i]
    nb = koto(hz(m), dur, bend_c=bc, bend_at=ba, vib_c=vc,
            body=0.0)
    boost = 20.0 * np.log10(
            rms(sosfilt(sos_b, NOTES[i]))
            / rms(sosfilt(sos_b, nb)))
    worst_bo = min(worst_bo, boost)
check("body", worst_bo >= 3.0,
        f"190-270 Hz vs bodyless twin (A3, Bb3): worst "
        f"{worst_bo:+.1f} dB")

# 5. kararin: every sweep note marks on time (flux window 28 ms
# < half the 60 ms gap, e87's rule); then the RING is measured,
# not the onsets — a 45 ms window at D3 has a ~44 Hz mainlobe
# and D3/Eb3 are 9 Hz apart (the BT wall, per-onset edition).
# Line claims are made only at fundamentals NO OCTAVE-MATE in
# the same sweep can fake (e88: the harmonic series contains
# your neighbors): sweep 1 keeps its bottom octave, sweep 2
# keeps all but D5 (h2 of its own D4).
sm = swb.mean(axis=1)
hs = np.abs(sosfilt(sos_t, sm))
ker = int(0.004 * SR)
hs = np.convolve(hs, np.ones(ker) / ker, mode="same")
fx = np.maximum(np.diff(hs, prepend=hs[:1]), 0.0)
worst_mk = 0.0
for tt, m in SW_ON:
    i0, i1 = int((tt - 0.028) * SR), int((tt + 0.028) * SR)
    tmk = (i0 + int(np.argmax(fx[i0:i1]))) / SR
    worst_mk = max(worst_mk, abs(tmk - tt) * 1000.0)
worst_ln = 0.0
n_lines = 0
for (t0, midis, gap, a0, a1) in SWEEPS:
    t_last = t0 + (len(midis) - 1) * gap
    seg = sm[int((t_last + 0.15) * SR):
             int((t_last + 0.95) * SR)]
    S = np.abs(np.fft.rfft(seg * np.hanning(len(seg))))
    fq = np.fft.rfftfreq(len(seg), 1.0 / SR)
    clean = [m for m in midis
             if m - 12 not in midis and m - 24 not in midis]
    for m in clean:
        f0 = hz(m)
        sel = (fq > f0 * 2 ** (-60 / 1200)) \
            & (fq < f0 * 2 ** (60 / 1200))
        fpk = fq[sel][np.argmax(S[sel])]
        worst_ln = max(worst_ln,
                abs(1200.0 * np.log2(fpk / f0)))
        n_lines += 1
check("kararin", worst_mk <= 15.0 and worst_ln <= 30.0,
        f"{len(SW_ON)} marks worst {worst_mk:.1f} ms; "
        f"{n_lines} unpolluted ring lines worst "
        f"{worst_ln:.1f} c")

# 6. the loop closes
check("seam", ruler.seam_rank(mix) <= 0.999,
        f"p{100 * ruler.seam_rank(mix):.2f}")

ruler.report(mix, "e90_koto_hirajoshi")
print(f"\n{'ALL PASS' if not fails else 'FAILS: ' + str(fails)}")
sys.exit(1 if fails else 0)

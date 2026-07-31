#!/usr/bin/env python3
"""loam — "The Long Stair" (the capstone of spin-off night).

96s seamless loop, D minor with a hijaz lean. The floor is a
barberpole wash falling forever — the descent that never arrives.
Everything built tonight plays:

  padsynth bed + barber(-3.5Hz)      the stair
  church bells through ir_bone       the depth markers
  psaltery + tape echo               the fingers
  ladder-filtered pulse bass         the footfalls' weight
  kick + hats (duck everything)      the pulse
  voice vocalise (sentence, rest,    the witness
    answer) feeding the taraf
  ney reply, one overblown peak      the hermit
  FDN room, limiter                  the bore itself

    python3 songs/the_long_stair.py [outdir]
"""

import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))))
from loam import SR, hz, Loop, stereo, write_wav, seam_report
from loam.pads import padsynth_stereo, saw_amps, formant_amps, VOWELS
from loam.modal import strike, CHURCH_BELL
from loam.strings import pluck, sympathetic
from loam.winds import ney, flute
from loam.voice import sing
from loam.analog import pulse as vpulse, ladder
from loam.space import tape_echo_loop, reverb_loop, ir_bone, convolve_loop
from loam.shift import barber
from loam.dyn import duck, limiter
from loam import drums as dr

outdir = sys.argv[1] if len(sys.argv) > 1 else "render"
os.makedirs(outdir, exist_ok=True)
BPM = 80.0
spb = 60.0 / BPM
BARS = 32
LOOP_S = BARS * 4 * spb          # 96.0
L = Loop(LOOP_S, 0x57A12)


def bt(bar: float, beat: float = 0.0) -> float:
    return (bar * 4 + beat) * spb


def addw(buf, at_s, chunk):
    idx = (int(at_s * SR) + np.arange(len(chunk))) % len(buf)
    np.add.at(buf, idx, chunk)


# ---- the stair: dark bed falling forever ---------------------------
bed = np.zeros((L.n, 2))
for i, (midi, g) in enumerate([(38, 1.0), (45, 0.55), (50, 0.7)]):
    bed += padsynth_stereo(LOOP_S, hz(midi), saw_amps(14, 1.8),
            bw_cents=28.0, seed=1200 + i) * g * 0.10
stair = barber(bed, LOOP_S, shift_hz=-3.5, delay_s=0.42,
        feedback=0.76, damp_hz=3000.0, mix=0.45)

# ---- depth markers: bells through the bone -------------------------
bells = np.zeros((L.n, 2))
for bar, midi, amp, pan in [(0, 50, 0.5, 0.0), (8, 45, 0.36, -0.3),
        (16, 53, 0.34, 0.3), (24, 43, 0.42, -0.15)]:
    b = strike(hz(midi), 5.5, CHURCH_BELL, amp=amp, bright=0.9,
            detune=2.5, rng=L.rng, knock=0.08)
    addw(bells, bt(bar), stereo(b, pan))
bells = convolve_loop(bells, ir_bone(1.2, seed=31), mix=0.5)

# ---- the fingers: psaltery, sparse, echoed -------------------------
pl = np.zeros((L.n, 2))
PAT = [(0, 0.0, 62), (0, 2.5, 65), (1, 1.0, 69), (2, 0.0, 67),
       (2, 3.0, 63), (3, 1.5, 62)]
for cyc in range(0, BARS, 8):
    fade = 1.0 if cyc in (8, 16) else 0.55
    for bar, beat, midi in PAT:
        p = pluck(hz(midi), 2.0, amp=0.20 * fade, t60=2.2,
                seed=midi + cyc)
        addw(pl, bt(cyc + bar, beat), stereo(p, 0.25 if midi % 2 else -0.25))
pl = tape_echo_loop(pl, LOOP_S, spb * 0.75, feedback=0.4,
        damp_hz=2400.0, mix=0.3)

# ---- footfalls: dark ladder bass on the roots ----------------------
bass = np.zeros(L.n)
ROOTS = [38, 38, 41, 36]
for bar in range(BARS):
    root = ROOTS[(bar // 8) % 4]
    for beat, g in [(0.0, 1.0), (2.5, 0.6)]:
        ndur = spb * 1.4
        v = vpulse(hz(root - 12), ndur, width=0.55)
        n = len(v)
        tt = np.arange(n) / SR
        fc = 260 * np.exp(-tt * 5.0) + 90
        w = ladder(v, fc, res=0.4, drive=1.4)
        env = np.ones(n)
        r = int(0.03 * SR)
        env[-r:] = np.linspace(1, 0, r)
        addw(bass, bt(bar, beat), w * env * 0.30 * g)
bass_st = np.stack([bass, bass], axis=1)

# ---- the pulse: sparse kick, brushy hats ---------------------------
kick_tr = np.zeros(L.n)
drums = np.zeros((L.n, 2))
for bar in range(BARS):
    run = 4 <= bar < 30
    b0 = bt(bar)
    v = dr.kick(f1=42.0, dur=0.5)
    at = int(b0 * SR)
    end = min(at + len(v), L.n)
    kick_tr[at:end] += v[: end - at] * (1.0 if run else 0.55)
    if run:
        at2 = int(bt(bar, 2.5) * SR)
        v2 = dr.kick(amp=0.6, f1=44.0)
        end2 = min(at2 + len(v2), L.n)
        kick_tr[at2:end2] += v2[: end2 - at2]
        for e in range(8):
            if L.rng.random() < 0.2:
                continue
            h = dr.hat(seed=e + 8 * bar) * (0.22 if e % 2 else 0.15)
            addw(drums, bt(bar, e * 0.5), stereo(h, 0.8 if e % 2 else -0.8))
drums[:, 0] += kick_tr
drums[:, 1] += kick_tr

# ---- the witness: voice sentence (bars 9-14), answer (17-22) -------
S = [(65, 1.5, "oh"), (64, 0.5, "oh"), (65, 1.0, ("oh", "ah")),
     (69, 1.5, "ah"), (67, 1.5, "ah"), (65, 1.0, ("ah", "oh")),
     (62, 3.0, ("oh", "oo"))]
A = [(70, 1.5, "ah"), (69, 0.5, "ah"), (67, 1.0, ("ah", "eh")),
     (65, 1.5, "eh"), (63, 1.5, ("eh", "oh")), (62, 3.0, ("oh", "oo"))]
vbus = np.zeros((L.n, 2))
addw(vbus, bt(9), stereo(sing(S, bpm=BPM, seed=21) * 0.42, 0.08))
addw(vbus, bt(17), stereo(sing(A, bpm=BPM, seed=22) * 0.38, -0.08))

# ---- the hermit: ney reply (bars 25-29), overblown peak ------------
nbus = np.zeros((L.n, 2))
NEY = [(25, 0.0, 62, 1.4), (25, 2.0, 65, 1.2), (26, 0.0, 67, 1.6),
       (26, 2.5, 65, 1.0), (27, 0.0, 70, 2.2, 1.0), (28, 0.0, 65, 1.2),
       (28, 2.0, 62, 2.6)]
for note in NEY:
    bar, beat, midi, dur = note[:4]
    ob = note[4] if len(note) > 4 else 0.0
    if ob > 0:
        m = flute(hz(midi - 12), dur, amp=0.30, breath=0.12,
                overblow=1.0, vib_amt=0.05, seed=midi)
    else:
        m = ney(hz(midi), dur, amp=0.26, seed=midi)
    addw(nbus, bt(bar, beat), stereo(m, 0.2))

# ---- the room hums: taraf fed by the melodic buses -----------------
taraf = sympathetic(vbus + nbus + pl, [50, 53, 57, 62, 65, 69],
        t60=3.0, coupling=0.16, mix=1.0) * 0.30

# ---- assemble ------------------------------------------------------
melodic = vbus + nbus + pl + bells + taraf
melodic = reverb_loop(melodic, t60=3.2, size=1.3, damp_hz=3400.0,
        mix=0.34)
L.buf += stair
L.buf += duck(melodic, kick_tr, amount_db=4.0, release_ms=160.0)
L.buf += duck(bass_st, kick_tr, amount_db=6.0, release_ms=110.0)
L.buf += drums * 0.8
out = limiter(L.master(7200.0, drive=1.35), ceiling=0.92)
write_wav(os.path.join(outdir, "the_long_stair.wav"), out)
print(" ", seam_report(out))
for a, b, tag in [(0, 24, "A stair+bells"), (24, 48, "B witness"),
        (48, 72, "C hermit"), (72, 96, "D wrap")]:
    r = np.sqrt((out[int(a * SR): int(b * SR)] ** 2).mean())
    print(f"  {tag:14s} rms {r:.3f}")
hi = np.fft.rfft(out, axis=0)
fr = np.fft.rfftfreq(len(out), 1 / SR)
hi[fr < 250] = 0
w = np.fft.irfft(hi, len(out), axis=0)
print(f"  stereo corr >250Hz {float(np.corrcoef(w[:,0], w[:,1])[0,1]):+.3f}"
      f"  peak {np.abs(out).max():.3f}")

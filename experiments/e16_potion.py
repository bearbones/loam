#!/usr/bin/env python3
"""e16 — The Potion. The new bubble() worked both ways at once:
as population (the cauldron: fizz, glugs, simmer) and as a pitched
voice (plinks — low chirp, damp < 1 so they ring like wet music
boxes). Two plink voices in polyrhythm, euclid(7,16) over
euclid(5,12), dripping through the ping-pong tape echo; a creamy
PADsynth fifth underneath (steep tilt = few upper harmonics = no
edge for the ear to catch); one bowed-glass swell mid-loop.

Timbre targets (the director's words): pad = creamy, plinks =
crisp, cauldron = the thing itself.

    python3 experiments/e16_potion.py [outdir]
"""

import os
import sys

import numpy as np
from scipy.signal import butter, sosfilt

sys.path.insert(0, os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))))
from loam import SR, hz, Loop, stereo, write_wav, seam_report
from loam.texture import bubble, bubbles
from loam.pads import padsynth_stereo, saw_amps
from loam.modal import bow, GLASS
from loam.mod import chorus
from loam.space import tape_echo_loop, reverb_loop
from loam.rhythm import euclid, onsets, scale_notes
from loam.dyn import limiter

outdir = sys.argv[1] if len(sys.argv) > 1 else "render"
os.makedirs(outdir, exist_ok=True)
BPM = 63.0
spb = 60.0 / BPM
BARS = 8
L = Loop(BARS * 4 * spb, 0xE16)
rng = np.random.default_rng(0xE16)

# --- the cauldron ----------------------------------------------
cauldron = bubbles(L.loop_s, rate=13.0, size=0.75, chirp=1.0,
        glug_rate=1.0, simmer=0.55, seed=0xE16) * 0.9

# --- creamy pad: E2 + B2, steep tilt, slow chorus --------------
pad = padsynth_stereo(L.loop_s, L.q(hz(40)), saw_amps(12, tilt=1.8),
        bw_cents=55.0, seed=1) * 0.19
pad += padsynth_stereo(L.loop_s, L.q(hz(47)), saw_amps(8, tilt=2.1),
        bw_cents=65.0, seed=3) * 0.10
pad = chorus(pad, L.loop_s, voices=3, rate_hz=0.35, depth_ms=6.0,
        mix=0.45)

# --- plink voices: bubbles as music box ------------------------
# The chirp pulls perceived pitch SHARP of f0 (+~55c at damp 0.32).
# Tune like the winds do: render one, measure the onset, pre-
# compensate every note by the measured ratio.
def plink_comp(chirp_amt, damp):
    ref = 660.0
    b = bubble(ref, chirp=chirp_amt, damp=damp)
    z = np.where(np.diff(np.signbit(b[:int(0.03 * SR)])))[0]
    return ref / (SR / (2 * np.diff(z).mean()))


plinks = np.zeros((L.n, 2))


def plink_pass(notes, walk, pat, step_beats, damp, chirp_amt, amp,
        pan_sign, skip_bars):
    comp = plink_comp(chirp_amt, damp)
    wi = 0
    for bar in range(BARS):
        if bar in skip_bars:
            wi += sum(pat)
            continue
        for k, tb in enumerate(onsets(pat, step_beats)):
            midi = notes[walk[wi % len(walk)] % len(notes)]
            wi += 1
            b = bubble(hz(midi) * comp, chirp=chirp_amt, damp=damp,
                    amp=amp * float(rng.uniform(0.7, 1.0)))
            at_s = (bar * 4 + tb) * spb
            pan = pan_sign * (0.8 if k % 2 else -0.6)
            c = stereo(b, pan)
            itd = int(abs(pan) * 0.0007 * SR)      # arrival delay,
            far = 0 if pan > 0 else 1              # not just level
            c = np.vstack([c, np.zeros((itd, 2))])
            c[itd:, far] = c[:len(b), far].copy()
            c[:itd, far] = 0.0
            idx = (int(at_s * SR) + np.arange(len(c))) % L.n
            np.add.at(plinks, idx, c)


NOTES_A = scale_notes(76, "minor_penta", 1)        # E5..E6
NOTES_B = scale_notes(64, "minor_penta", 1)        # E4..E5
plink_pass(NOTES_A, [0, 2, 4, 1, 3, 5, 2, 4, 0, 3], euclid(7, 16),
        0.25, 0.32, 0.35, 0.34, +1, skip_bars={0, 4})
plink_pass(NOTES_B, [4, 2, 0, 3, 1, 2, 5, 0], euclid(5, 12),
        4.0 / 12, 0.22, 0.30, 0.28, -1, skip_bars={1, 5})

plinks = tape_echo_loop(plinks, L.loop_s, delay_s=0.75 * spb,
        feedback=0.42, damp_hz=2800.0, wow_hz=L.q(0.4),
        pingpong=True, mix=0.26)

# --- one bowed-glass swell (the stirring) ----------------------
gl = bow(hz(59), 6.0, GLASS, amp=0.14, vib_hz=4.6, rng=rng)
L.add(3.2 * 4 * spb, stereo(gl, 0.15))
gl2 = bow(hz(62), 5.0, GLASS, amp=0.10, vib_hz=5.1, rng=rng)
L.add(6.4 * 4 * spb, stereo(gl2, -0.25))

L.buf += cauldron + pad + plinks
L.buf = reverb_loop(L.buf, t60=2.1, size=0.85, damp_hz=3600.0,
        mix=0.16)
out = limiter(L.master(9500.0, drive=1.25), ceiling=0.92)
write_wav(os.path.join(outdir, "e16_potion.wav"), out)
print(" ", seam_report(out))

# metrology: plink pitch honesty (post-compensation) + width
b1 = bubble(hz(76) * plink_comp(0.32, 0.32), chirp=0.32, damp=0.32)
z = np.where(np.diff(np.signbit(b1[:int(0.03 * SR)])))[0]
f_meas = SR / (2 * np.diff(z).mean())
cents = 1200 * np.log2(f_meas / hz(76))
print(f"  plink E5 onset pitch: {f_meas:.1f} Hz ({cents:+.0f}c)")
# width, judged per material: glugs/echo belong centered, so the
# honest width read is ABOVE the glug band (4th-order, 500 Hz) —
# a 2nd-order 250 Hz HP leaks the loud centered glugs into the
# meter and reports the fizz as mono when it measures +0.03 alone
sos_h = butter(2, 250, btype="high", fs=SR, output="sos")
hp = sosfilt(sos_h, out, axis=0)
print(f"  stereo corr >250Hz: {np.corrcoef(hp[:, 0], hp[:, 1])[0, 1]:+.3f}"
      " (glug/echo center included)")
sos_f = butter(4, 500, btype="high", fs=SR, output="sos")
hf = sosfilt(sos_f, out, axis=0)
print(f"  stereo corr >500Hz: {np.corrcoef(hf[:, 0], hf[:, 1])[0, 1]:+.3f}"
      " (the fizz field)")
for name, bus in [("cauldron", cauldron), ("pad", pad),
        ("plinks", plinks)]:
    print(f"  {name:9s} rms {np.sqrt((bus ** 2).mean()):.4f}")

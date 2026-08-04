#!/usr/bin/env python3
"""e18 — The Transmission. Space alien sci-fi from the two
classic tools plus one swoop:
- ring mod on a sung vocalise (the Radiophonic trick: sidebands
  at f +- carrier destroy the harmonic series but keep the
  formant motion, so it still SPEAKS while being metal);
- the Bode frequency shifter on an airy 'oo' pad — a few Hz of
  shift moves every partial by the same ABSOLUTE amount, which
  no detune can do: the sheen of a spectrum that almost agrees
  with itself;
- a theremin answer: pure sine, exaggerated portamento (swoopy),
  vibrato that arrives late.
Sub pulse breathes underneath; a grain cloud scatters the sung
phrase an octave up as debris. Sentence, rest, answer — the
standing grammar.

Timbre targets: pad = airy, theremin = swoopy, ring-mod = alien.

    python3 experiments/e18_transmission.py [outdir]
"""

import os
import sys

import numpy as np
from scipy.signal import butter, sosfilt

sys.path.insert(0, os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))))
from loam import SR, hz, Loop, stereo, write_wav, seam_report
from loam.pads import padsynth_stereo, formant_amps, VOWELS
from loam.voice import sing
from loam.shift import freq_shift, ring_mod
from loam.grain import cloud
from loam.space import tape_echo_loop, reverb_loop
from loam.dyn import limiter

outdir = sys.argv[1] if len(sys.argv) > 1 else "render"
os.makedirs(outdir, exist_ok=True)
BPM = 60.0
spb = 60.0 / BPM
BARS = 8
L = Loop(BARS * 4 * spb, 0xE18)
rng = np.random.default_rng(0xE18)

# --- airy pad, frequency-shifted -------------------------------
C3 = hz(48)
pad = padsynth_stereo(L.loop_s, L.q(C3),
        formant_amps(C3, 24, VOWELS["oo"], tilt=0.9),
        bw_cents=70.0, seed=5) * 0.30
SHIFT = L.q(3.7)
pad = freq_shift(pad, SHIFT, loop_s=L.loop_s)
pad *= 0.55

# --- the transmission: vocalise through ring mod ---------------
CAR = L.q(111.0)                            # inharmonic vs C (130.8)
PHRASE_A = [(60, 2.0, ("oo", "ah")), (64, 1.5, "ah"),
        (66, 2.5, ("ah", "oo")), (59, 3.0, ("oo", "oh"))]
PHRASE_B = [(66, 1.5, ("oo", "eh")), (71, 2.5, ("eh", "oo")),
        (64, 3.0, ("oo", "oh"))]
voice = np.zeros((L.n, 2))
for phrase, at_bar, seed in [(PHRASE_A, 0.25, 11), (PHRASE_B, 4.25, 12)]:
    v = sing(phrase, bpm=BPM, porta_s=0.16, vib_cents=22.0,
            breath=0.06, amp=1.0, seed=seed)
    v = v / (np.max(np.abs(v)) + 1e-12) * 0.30
    vr = ring_mod(np.stack([v, v], axis=1), CAR, mix=0.85)
    idx = (int(at_bar * 4 * spb * SR) + np.arange(len(vr))) % L.n
    np.add.at(voice, idx, vr)
voice = tape_echo_loop(voice, L.loop_s, delay_s=1.5 * spb,
        feedback=0.5, damp_hz=2600.0, wow_hz=L.q(0.3),
        pingpong=True, mix=0.3)

# --- the theremin answer: swoop is the melody ------------------
ther_track = [(69.5, 1.0), (74, 2.5), (72.2, 1.5), (76, 3.0),
        (71, 3.5)]                          # floats: between the keys
n_th = int(sum(b for _, b in ther_track) * spb * SR)
f0 = np.zeros(n_th)
at = 0
for midi, b in ther_track:
    seg = int(b * spb * SR)
    f0[at:at + seg] = hz(midi)
    at += seg
f0[at:] = f0[at - 1]
tau = int(0.38 * SR)                        # the swoop lives here
ker = np.exp(-np.arange(4 * tau) / tau)
ker /= ker.sum()
f0 = np.convolve(np.concatenate([np.full(4 * tau, f0[0]), f0]),
        ker, mode="same")[4 * tau:]
tt = np.arange(n_th) / SR
vib = 2.0 ** (30.0 * np.clip((tt - 0.8) / 1.2, 0, 1)
        * np.sin(2 * np.pi * 5.0 * tt) / 1200.0)
th = np.sin(2 * np.pi * np.cumsum(f0 * vib) / SR)
env = np.minimum(np.clip(tt / 0.7, 0, 1),
        np.clip((n_th / SR - tt) / 1.2, 0, 1)) ** 1.5
th *= env * 0.12
theremin = np.zeros((L.n, 2))
c = stereo(th, 0.35)
itd = int(0.35 * 0.0008 * SR)
c = np.vstack([c, np.zeros((itd, 2))])
c[itd:, 0] = c[:n_th, 0].copy()
c[:itd, 0] = 0.0
idx = (int(2.55 * 4 * spb * SR) + np.arange(len(c))) % L.n
np.add.at(theremin, idx, c)

# --- sub pulse + debris cloud ----------------------------------
subf = L.q(hz(24))
breathe = 0.5 + 0.5 * np.sin(2 * np.pi * L.q(1.0 / L.loop_s)
        * np.arange(L.n) / SR - np.pi / 2)
sub = np.sin(2 * np.pi * subf * np.arange(L.n) / SR) \
    * (0.032 + 0.058 * breathe)
sub = np.stack([sub, sub], axis=1)

src = sing(PHRASE_A, bpm=BPM, breath=0.05, seed=11)
debris = cloud(src, L.loop_s, density=3.5, grain_s=0.22,
        pitches=(12.0, 19.0), pan_spread=0.9, gain=0.08,
        seed=0xE18)
debris = freq_shift(debris, SHIFT, loop_s=L.loop_s)

L.buf += pad + voice + theremin + sub + debris
L.buf = reverb_loop(L.buf, t60=3.2, size=1.1, damp_hz=3000.0,
        mix=0.14)
out = limiter(L.master(10000.0, drive=1.25), ceiling=0.92)
write_wav(os.path.join(outdir, "e18_transmission.wav"), out)
print(" ", seam_report(out))

# metrology 1: ring-mod sidebands — strongest dry partial f_v
# must reappear at f_v +- CAR in the wet, and vanish at f_v
v = sing([(60, 4.0, "ah")], bpm=BPM, seed=1)
v = v / (np.max(np.abs(v)) + 1e-12)
seg = slice(int(1.0 * SR), int(3.0 * SR))
win = np.hanning(seg.stop - seg.start)


def peak_near(x, f, half=40.0):
    sp = np.abs(np.fft.rfft(x[seg] * win))
    fr = np.fft.rfftfreq(seg.stop - seg.start, 1 / SR)
    m = (fr > f - half) & (fr < f + half)
    return sp[m].max(), fr[m][np.argmax(sp[m])]


w = ring_mod(v.copy(), CAR)
f_v = 261.6                                 # C4 fundamental
a_dry, _ = peak_near(v, f_v)
a_wet_c, _ = peak_near(w, f_v, 20.0)
a_lo, f_lo = peak_near(w, f_v - CAR)
a_hi, f_hi = peak_near(w, f_v + CAR)
print(f"  ringmod: dry C4 peak -> wet {a_wet_c / a_dry:.3f}x at f_v, "
      f"sidebands at {f_lo:.0f}/{f_hi:.0f} Hz "
      f"({a_lo / a_dry:.2f}/{a_hi / a_dry:.2f}x)")

# metrology 2: the shifter moved partial 2 by +SHIFT absolutely
p_dry = padsynth_stereo(L.loop_s, L.q(C3), formant_amps(C3, 24,
        VOWELS["oo"], tilt=0.9), bw_cents=70.0, seed=5)
_, f2_dry = peak_near(p_dry[:, 0], 2 * L.q(C3), 30.0)
_, f2_wet = peak_near(pad[:, 0] / 0.55, 2 * L.q(C3), 30.0)
print(f"  shifter: partial-2 {f2_dry:.2f} -> {f2_wet:.2f} Hz "
      f"(moved {f2_wet - f2_dry:+.2f}, SHIFT={SHIFT:+.2f})")
sos_w = butter(4, 500, btype="high", fs=SR, output="sos")
hw = sosfilt(sos_w, out, axis=0)
print(f"  stereo corr >500Hz: {np.corrcoef(hw[:, 0], hw[:, 1])[0, 1]:+.3f}")
for name, bus in [("pad", pad), ("voice", voice),
        ("theremin", theremin), ("sub", sub), ("debris", debris)]:
    print(f"  {name:8s} rms {np.sqrt((bus ** 2).mean()):.4f}")

#!/usr/bin/env python3
"""e19 — Ear Candy. Three jars, no concept, just pleasure:

STINGER (one-shot ~9s): the podcast-ident recipe. Soft marimba
rises through F major pentatonic (glass doubling an octave up),
lands on a detuned glass F5 that beats slowly against itself; two
bowed-glass swells underneath peak just AFTER the landing, so the
bell hands off to the pad; a sympathetic bank tuned to the same
pentatonic shimmers along; big warm tail.

CLICKS (one-shot ~14s): the click cabinet, five families:
  thock   — body mode + contact + sub thump (the desk is a layer)
  pen     — press/release pair, release lower and softer
  pop     — van den Doel bubbles; a rising triplet for the candy
  shutter — mirror slap, then two wood ticks
  marble  — bounce train, intervals * 0.78 per hop (the physics
            IS the satisfaction), pitch stiffening 1% per contact
Presented dry-ish in a small bright room.

SOOTHE (seamless loop 32s): creamy PADsynth F2+C3+F3 breathing at
7.5 breaths/min (4 whole cycles per loop, seam phase-exact), glass
armonica bowls drifting through the pentatonic, sub F1 under the
same breath, four music-box sparkles through the ping-pong echo.

    python3 experiments/e19_earcandy.py [outdir]
"""

import os
import sys

import numpy as np
from scipy.signal import butter, sosfilt, find_peaks

sys.path.insert(0, os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))))
from loam import SR, hz, Loop, stereo, write_wav, seam_report
from loam.modal import strike, bow, MARIMBA, GLASS, WOOD, ANVIL
from loam.pads import padsynth_stereo, saw_amps
from loam.texture import bubble
from loam.strings import sympathetic
from loam.mod import chorus
from loam.space import reverb_tail, tape_echo_loop, reverb_loop, \
        ir_room, convolve_tail
from loam.dyn import limiter

outdir = sys.argv[1] if len(sys.argv) > 1 else "render"
os.makedirs(outdir, exist_ok=True)
rng = np.random.default_rng(0xE19)


def place(buf, at_s, mono, pan=0.0):
    c = stereo(mono, pan)
    i0 = int(at_s * SR)
    n = min(len(c), len(buf) - i0)
    buf[i0:i0 + n] += c[:n]


# ===============================================================
# 1. STINGER
# ===============================================================
st = np.zeros((int(7.0 * SR), 2))

# two glass swells: they peak ~1.75s in, just after the bell lands
place(st, 0.0, bow(hz(53), 5.0, GLASS, amp=0.11, vib_hz=4.2,
        rng=rng), -0.2)
place(st, 0.0, bow(hz(60), 4.6, GLASS, amp=0.075, vib_hz=4.8,
        rng=rng), +0.25)

# the rise: F4 G4 A4 C5 D5, 16ths at 88, walking L -> R
dt = 60.0 / 88.0 / 4.0
for k, midi in enumerate([65, 67, 69, 72, 74]):
    at = 0.35 + k * dt + float(rng.uniform(-0.004, 0.004))
    pan = -0.45 + k * 0.225
    a = 0.30 + 0.025 * k
    place(st, at, strike(hz(midi), 1.3, MARIMBA, amp=a,
            bright=0.8, rng=rng), pan)
    place(st, at, strike(hz(midi + 12), 0.9, GLASS, amp=a * 0.30,
            bright=0.9, rng=rng), pan * 0.6)

# the landing: detuned glass F5 (slow self-beat), marimba root,
# one quiet C6 for air
land = 0.35 + 5 * dt
place(st, land, strike(hz(77), 4.2, GLASS, amp=0.42, bright=0.85,
        detune=2.5, rng=rng), +0.1)
place(st, land, strike(hz(53), 2.2, MARIMBA, amp=0.26, bright=0.7,
        rng=rng), -0.1)
place(st, land + 0.012, strike(hz(84), 3.2, GLASS, amp=0.11,
        bright=0.85, rng=rng), +0.35)

# pentatonic strings hum along with everything above
st = sympathetic(st, [65, 67, 69, 72, 74, 77, 79, 81], t60=2.6,
        coupling=0.09, mix=0.22, loop=False)
st = reverb_tail(st, t60=2.8, size=1.1, damp_hz=4600.0, mix=0.24)
sos = butter(2, 9000, btype="low", fs=SR, output="sos")
st = sosfilt(sos, st, axis=0)
st = st[:int(7.8 * SR)]                    # tail is done by ~7.2s
st[-int(0.6 * SR):] *= np.linspace(1, 0, int(0.6 * SR))[:, None]
st *= 0.85 / np.max(np.abs(st))
write_wav(os.path.join(outdir, "e19_stinger.wav"), st)


# ===============================================================
# 2. CLICKS
# ===============================================================
ck = np.zeros((int(14.5 * SR), 2))


def thump(f_hi=135.0, f_lo=62.0, dur=0.09, amp=0.5):
    tt = np.arange(int(dur * SR)) / SR
    f = f_lo + (f_hi - f_lo) * np.exp(-tt * 55.0)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) \
        * np.exp(-tt * 40.0) * amp


def thock(amp=0.8):
    body = strike(92.0, 0.10, WOOD, amp=amp, bright=0.75, rng=rng,
            knock=0.9)
    out = np.zeros(int(0.12 * SR))
    out[:len(body)] += body
    tp = thump(amp=amp * 0.55)
    out[:len(tp)] += tp
    return out


def pen(amp=0.6):
    press = strike(1450.0, 0.028, WOOD, amp=amp, bright=1.1,
            rng=rng, knock=0.5)
    tick = strike(3100.0, 0.02, ANVIL, amp=amp * 0.35, bright=0.8,
            rng=rng)
    out = np.zeros(int(0.16 * SR))
    out[:len(press)] += press
    out[:len(tick)] += tick
    rel = strike(1150.0, 0.022, WOOD, amp=amp * 0.55, bright=1.0,
            rng=rng)
    r0 = int(0.072 * SR)
    out[r0:r0 + len(rel)] += rel
    return out


def shutter(amp=0.7):
    n = int(0.16 * SR)
    out = np.zeros(n)
    slap_n = int(0.007 * SR)
    sos_s = butter(2, [1200, 6800], btype="band", fs=SR,
            output="sos")
    slap = sosfilt(sos_s, rng.standard_normal(slap_n * 3))[:slap_n]
    out[:slap_n] += slap / np.max(np.abs(slap)) \
        * np.exp(-np.arange(slap_n) / (slap_n * 0.3)) * amp
    for at, f, a in [(0.048, 2400.0, 0.6), (0.085, 1700.0, 0.45)]:
        tk = strike(f, 0.018, WOOD, amp=amp * a, bright=1.05,
                rng=rng)
        i0 = int(at * SR)
        out[i0:i0 + len(tk)] += tk
    return out


# -- thock: one, then a quick pair --
for at in [0.5, 1.6, 1.78]:
    place(ck, at, thock(), float(rng.uniform(-0.15, 0.15)))
# -- pen: single, then click-clack --
place(ck, 3.1, pen(), -0.25)
place(ck, 3.9, pen(), +0.25)
# -- pops: one deep, then the rising triplet --
place(ck, 5.6, bubble(150.0, chirp=1.6, damp=1.1, amp=0.8), 0.0)
for k, (at, f) in enumerate([(6.4, 230.0), (6.56, 300.0),
        (6.72, 385.0)]):
    place(ck, at, bubble(f, chirp=1.4, damp=1.2, amp=0.65),
            -0.3 + k * 0.3)
# -- shutter: twice --
place(ck, 8.3, shutter(), -0.2)
place(ck, 9.1, shutter(), +0.2)
# -- the marble drop: intervals * 0.78, pitch stiffens 1%/hop --
t_at, dt_b, f_m = 10.6, 0.30, 640.0
marble_times = []
for k in range(13):
    a = 0.68 * 0.86 ** k
    place(ck, t_at, strike(f_m * 1.01 ** k, 0.05, WOOD, amp=a,
            bright=1.0, rng=rng, knock=0.25),
            -0.35 + 0.05 * k)
    marble_times.append(t_at)
    t_at += dt_b
    dt_b *= 0.78

ck = convolve_tail(ck, ir_room(t60=0.45, size=0.6, bright=0.65,
        seed=0xE19), mix=0.10)
ck = ck[:int(13.0 * SR)]                   # last event + room tail
ck[-int(0.4 * SR):] *= np.linspace(1, 0, int(0.4 * SR))[:, None]
ck *= 0.85 / np.max(np.abs(ck))
write_wav(os.path.join(outdir, "e19_clicks.wav"), ck)


# ===============================================================
# 3. SOOTHE
# ===============================================================
L = Loop(32.0, 0xE19)

# creamy stack, breathing: 4 whole cycles/loop = 7.5 breaths/min
pad = padsynth_stereo(L.loop_s, L.q(hz(41)), saw_amps(10, tilt=2.0),
        bw_cents=50.0, seed=11) * 0.16
pad += padsynth_stereo(L.loop_s, L.q(hz(48)), saw_amps(8, tilt=2.2),
        bw_cents=60.0, seed=12) * 0.09
pad += padsynth_stereo(L.loop_s, L.q(hz(53)), saw_amps(6, tilt=2.4),
        bw_cents=65.0, seed=13) * 0.06
pad = chorus(pad, L.loop_s, voices=3, rate_hz=0.3, depth_ms=7.0,
        mix=0.4)
breath = 0.60 + 0.40 * (0.5 - 0.5 * np.cos(
        2 * np.pi * 4.0 * L.t / L.loop_s)) ** 1.4
pad *= breath[:, None]

sub = np.sin(2 * np.pi * L.q(hz(29)) * L.t) * 0.045 * breath
L.buf += pad + stereo(sub, 0.0)

# glass armonica bowls wandering the pentatonic — placed by
# ARRIVAL TIME (ITD), not just level: a level pan feeds both ears
# the same waveform and never decorrelates (the e16 lesson)
for at, midi, dur, amp, pan in [
        (2.0, 65, 7.0, 0.12, -0.45), (9.0, 72, 6.0, 0.10, +0.45),
        (15.0, 67, 7.0, 0.11, +0.25), (21.5, 69, 6.5, 0.10, -0.4),
        (26.5, 74, 6.0, 0.085, +0.5)]:
    g = bow(hz(midi), dur, GLASS, amp=amp,
            vib_hz=4.0 + 0.4 * (midi % 3), rng=rng)
    c = stereo(g, pan)
    itd = int(abs(pan) * 0.0007 * SR)
    far = 0 if pan > 0 else 1
    c = np.vstack([c, np.zeros((itd, 2))])
    c[itd:, far] = c[:len(g), far].copy()
    c[:itd, far] = 0.0
    L.add(at, c)

# four music-box sparkles into the ping-pong
spark = np.zeros((L.n, 2))
for at, midi, pan in [(4.7, 89, -0.5), (12.3, 86, +0.5),
        (19.6, 91, -0.4), (26.2, 84, +0.45)]:
    b = bubble(hz(midi), chirp=0.3, damp=0.28, amp=0.09)
    idx = (int(at * SR) + np.arange(len(b))) % L.n
    np.add.at(spark, (idx, 0 if pan < 0 else 1), b)
spark = tape_echo_loop(spark, L.loop_s, delay_s=1.05,
        feedback=0.45, damp_hz=2600.0, wow_hz=L.q(0.35),
        pingpong=True, mix=0.4)
L.buf += spark

L.buf = reverb_loop(L.buf, t60=2.6, size=1.0, damp_hz=3400.0,
        mix=0.18)
out = limiter(L.master(6800.0, drive=1.12), ceiling=0.90)
write_wav(os.path.join(outdir, "e19_soothe.wav"), out)
print(" ", seam_report(out))

# --- metrology -------------------------------------------------
# marble honesty: recover bounce ratio from the RENDER, not the plan
seg = np.abs(ck[int(10.5 * SR):int(13.0 * SR)]).mean(axis=1)
env = np.convolve(seg, np.ones(64) / 64, mode="same")
pk, _ = find_peaks(env, height=0.12 * env.max(), distance=int(0.03 * SR))
iv = np.diff(pk[:8]) / SR
print(f"  marble bounce ratio measured {np.mean(iv[1:] / iv[:-1]):.3f}"
      f" (designed 0.780)")
# breath honesty: dominant envelope cycle of the soothe loop
pe = np.abs(out).mean(axis=1)
spec = np.abs(np.fft.rfft(pe - pe.mean()))
cyc = np.argmax(spec[1:200]) + 1
print(f"  soothe breath: {cyc} cycles/loop = "
      f"{cyc * 60.0 / L.loop_s:.1f}/min (designed 7.5)")
sos_h = butter(4, 250, btype="high", fs=SR, output="sos")
hp = sosfilt(sos_h, out, axis=0)
print(f"  soothe stereo corr >250Hz: "
      f"{np.corrcoef(hp[:, 0], hp[:, 1])[0, 1]:+.3f}")

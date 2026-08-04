#!/usr/bin/env python3
"""The Alembic — 76s, E minor @63. The season's three worlds in
one room: the potion simmers (bubbles + creamy pad), the work
begins (anvils 3:2 against the escapement, bar stock humming what
the anvils radiate), the pour (plink polyrhythm through ping-pong
echo, glass stirred), and then the potion SPEAKS (ring-modded
vocalise, theremin swoop answer) before the room settles back to
simmer. Ratchet winding-bursts mark the section seams. The
transmission's echo tail wraps the loop and haunts the opening.

Sections (20 bars):  1-4 simmer / 5-8 work / 9-12 pour /
13-16 transmission / 17-20 settle.

    python3 songs/the_alembic.py [outdir]
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
from loam.modal import strike, bow, ANVIL, WOOD, GLASS
from loam.strings import sympathetic
from loam.voice import sing
from loam.shift import freq_shift, ring_mod
from loam.grain import cloud
from loam.space import convolve_loop, ir_tank, tape_echo_loop, \
    reverb_loop
from loam.rhythm import euclid, onsets, scale_notes
from loam.dyn import duck, limiter
from loam import drums as dr

outdir = sys.argv[1] if len(sys.argv) > 1 else "render"
os.makedirs(outdir, exist_ok=True)
BPM = 63.0
spb = 60.0 / BPM
BARS = 20
L = Loop(BARS * 4 * spb, 0xA1E)
rng = np.random.default_rng(0xA1E)


def put(buf, at_s, chunk):
    idx = (int(at_s * SR) + np.arange(len(chunk))) % L.n
    np.add.at(buf, idx, chunk)


def put_itd(buf, at_s, mono, pan):
    c = stereo(mono, pan)
    itd = int(abs(pan) * 0.0008 * SR)
    if itd:
        far = 0 if pan > 0 else 1
        c = np.vstack([c, np.zeros((itd, 2))])
        c[itd:, far] = c[:len(mono), far].copy()
        c[:itd, far] = 0.0
    put(buf, at_s, c)


def bar_s(b):
    return b * 4 * spb


# --- the alembic itself: cauldron + creamy pad + alien tinge ---
cauldron = bubbles(L.loop_s, rate=10.0, size=0.8, chirp=1.0,
        glug_rate=0.8, simmer=0.5, seed=0xA1E) * 0.8

pad = padsynth_stereo(L.loop_s, L.q(hz(40)), saw_amps(12, tilt=1.8),
        bw_cents=55.0, seed=2) * 0.15
pad += padsynth_stereo(L.loop_s, L.q(hz(47)), saw_amps(8, tilt=2.1),
        bw_cents=65.0, seed=4) * 0.09
SHIFT = L.q(2.6)                            # the whole room is
pad = freq_shift(pad, SHIFT, loop_s=L.loop_s)   # slightly wrong

# --- the escapement: always ticking, louder while working ------
TICK_AMP = {0: 0.10, 1: 0.20, 2: 0.20, 3: 0.20, 4: 0.08}
ticks = np.zeros((L.n, 2))
for b8 in range(BARS * 8):
    bar = b8 // 8
    sec = min(bar // 4, 4)
    tock = b8 % 2
    w = strike(2200.0 if not tock else 1650.0, 0.05, WOOD,
            amp=TICK_AMP[sec] * (0.8 if tock else 1.0),
            bright=1.3, knock=0.6, rng=rng)
    put_itd(ticks, b8 * spb / 2, w, 0.7 if tock else -0.7)
for bar in (3, 7, 11, 15):                  # the seams get wound
    at0 = bar_s(bar) + 2.6 * spb
    dt = 0.10
    for j in range(9):
        at = at0 + sum(dt * (0.82 ** i) for i in range(j))
        r = dr.rim(amp=0.26 * (0.9 ** j), seed=j)
        put(ticks, at, stereo(r, -0.5 + j * 0.12))

# --- the work: anvils (bars 5-16), master 3:2, apprentice ------
E3, B3, E4 = 164.81, 246.94, 329.63
metal = np.zeros((L.n, 2))
dq = 1.5 * spb
k0 = int(round(bar_s(4) / dq))
k1 = int(round(bar_s(16) / dq))
for k in range(k0, k1):
    at = k * dq
    sec_bar = at / (4 * spb)
    fade = 1.0 if sec_bar < 12 else 0.6     # lighter under the pour
    acc = 1.0 if k % 4 == 0 else (0.55 if k % 2 else 0.75)
    if k % 16 == 14:
        continue
    a = strike(E3, 2.6, ANVIL, amp=0.50 * acc * fade, bright=1.05,
            knock=0.5, rng=rng)
    put_itd(metal, at, a, -0.45)
for k in range(k0, k1):
    if k % 4 in (1, 3):
        f = B3 if k % 8 < 4 else E4
        a = strike(f, 1.6, ANVIL, amp=0.26, bright=1.15,
                knock=0.35, rng=rng)
        put_itd(metal, k * dq + 0.75 * spb, a, 0.55)

# --- the pour: self-tuned plinks (bars 9-12, echo of 17-20) ----
def plink_comp(chirp_amt, damp):
    ref = 660.0
    b = bubble(ref, chirp=chirp_amt, damp=damp)
    z = np.where(np.diff(np.signbit(b[:int(0.03 * SR)])))[0]
    return ref / (SR / (2 * np.diff(z).mean()))


plinks = np.zeros((L.n, 2))


def plink_pass(notes, walk, pat, step_beats, damp, chirp_amt, amp,
        pan_sign, bars):
    comp = plink_comp(chirp_amt, damp)
    wi = 0
    for bar in bars:
        for k, tb in enumerate(onsets(pat, step_beats)):
            midi = notes[walk[wi % len(walk)] % len(notes)]
            wi += 1
            b = bubble(hz(midi) * comp, chirp=chirp_amt, damp=damp,
                    amp=amp * float(rng.uniform(0.7, 1.0)))
            put_itd(plinks, bar_s(bar) + tb * spb, b,
                    pan_sign * (0.8 if k % 2 else -0.6))


NOTES_A = scale_notes(76, "minor_penta", 1)
NOTES_B = scale_notes(64, "minor_penta", 1)
plink_pass(NOTES_A, [0, 2, 4, 1, 3, 5, 2, 4, 0, 3], euclid(7, 16),
        0.25, 0.32, 0.35, 0.30, +1, [8, 9, 10, 11, 17, 19])
plink_pass(NOTES_B, [4, 2, 0, 3, 1, 2, 5, 0], euclid(5, 12),
        4.0 / 12, 0.22, 0.30, 0.26, -1, [9, 10, 11, 18])
plinks = tape_echo_loop(plinks, L.loop_s, delay_s=0.75 * spb,
        feedback=0.42, damp_hz=2800.0, wow_hz=L.q(0.4),
        pingpong=True, mix=0.26)

gl = bow(hz(59), 6.0, GLASS, amp=0.12, vib_hz=4.6, rng=rng)
glass_bus = np.zeros((L.n, 2))
put(glass_bus, bar_s(9.2), stereo(gl, 0.15))
gl2 = bow(hz(64), 5.0, GLASS, amp=0.09, vib_hz=5.1, rng=rng)
put(glass_bus, bar_s(18.2), stereo(gl2, -0.25))

# --- the transmission: the potion speaks (bars 13-16) ----------
CAR = L.q(113.0)
PHRASE = [(64, 2.0, ("oo", "ah")), (67, 1.5, "ah"),
        (69, 2.5, ("ah", "oo")), (62, 3.5, ("oo", "oh"))]
voice = np.zeros((L.n, 2))
v = sing(PHRASE, bpm=BPM, porta_s=0.16, vib_cents=22.0,
        breath=0.06, seed=21)
v = v / (np.max(np.abs(v)) + 1e-12) * 0.38
put(voice, bar_s(12.25), ring_mod(np.stack([v, v], axis=1), CAR,
        mix=0.85))
voice = tape_echo_loop(voice, L.loop_s, delay_s=1.5 * spb,
        feedback=0.55, damp_hz=2600.0, wow_hz=L.q(0.3),
        pingpong=True, mix=0.32)

n_th = int(6.5 * spb * SR)
track = [(76, 1.5), (79.3, 2.0), (74, 3.0)]
f0 = np.zeros(n_th)
at = 0
for midi, b in track:
    seg = int(b * spb * SR)
    f0[at:at + seg] = hz(midi)
    at += seg
f0[at:] = f0[at - 1]
tau = int(0.38 * SR)
ker = np.exp(-np.arange(4 * tau) / tau)
ker /= ker.sum()
f0 = np.convolve(np.concatenate([np.full(4 * tau, f0[0]), f0]),
        ker, mode="same")[4 * tau:]
tt = np.arange(n_th) / SR
vib = 2.0 ** (28.0 * np.clip((tt - 0.8) / 1.2, 0, 1)
        * np.sin(2 * np.pi * 5.0 * tt) / 1200.0)
th = np.sin(2 * np.pi * np.cumsum(f0 * vib) / SR)
env = np.minimum(np.clip(tt / 0.7, 0, 1),
        np.clip((n_th / SR - tt) / 1.0, 0, 1)) ** 1.5
theremin = np.zeros((L.n, 2))
put_itd(theremin, bar_s(14.6), th * env * 0.13, 0.35)

debris = cloud(v, L.loop_s, density=2.5, grain_s=0.22,
        pitches=(12.0, 19.0), pan_spread=0.9, gain=0.06,
        seed=0xA1E)
debris = freq_shift(debris, SHIFT, loop_s=L.loop_s)

# --- boiler + room + hum ---------------------------------------
low = np.zeros((L.n, 2))
kick_key = np.zeros(L.n)
for bar in range(4, 16):
    k = dr.kick(dur=0.5, f0=110.0, f1=38.0) * 0.55
    put(low, bar_s(bar), stereo(k, 0.0))
    ki = (int(bar_s(bar) * SR) + np.arange(len(k))) % L.n
    np.add.at(kick_key, ki, k)

steam = np.zeros((L.n, 2))
sos_st = butter(2, [3000, 10000], btype="band", fs=SR, output="sos")
for bar, g in [(4, 0.13), (16, 0.15)]:      # the work begins and
    ln = int(1.4 * SR)                      # ends in steam
    st_t = np.arange(ln) / SR
    envs = np.clip(st_t / 0.04, 0, 1) * np.exp(-st_t * 2.2)
    vnt = sosfilt(sos_st, rng.standard_normal(ln)) * envs * g
    put(steam, bar_s(bar), stereo(vnt, float(rng.uniform(-0.6, 0.6))))

metal_room = convolve_loop(metal, ir_tank(1.8, modes=11, seed=0xA1E),
        mix=0.5)


def ring_midi(f):
    return 69.0 + 12.0 * np.log2(f / 440.0)


STOCK = [ring_midi(f) for f in
        (E3, B3, E4, E3 * 2.72, B3 * 2.72, E4 * 2.72)]
taraf_raw = sympathetic(metal, STOCK, t60=3.8, coupling=0.12,
        mix=1.0, norm=False)
taraf = convolve_loop(taraf_raw, ir_tank(1.2, modes=5, seed=99),
        mix=0.4)
ticks_room = convolve_loop(ticks, ir_tank(0.9, modes=6, seed=7),
        mix=0.22)

mix = (cauldron + pad + metal_room + taraf * 0.30 + ticks_room
        + plinks + glass_bus + voice + theremin + debris + steam)
mix = duck(mix, kick_key, amount_db=3.5, release_ms=110.0)
L.buf += mix + low
L.buf = reverb_loop(L.buf, t60=2.4, size=1.0, damp_hz=3400.0,
        mix=0.13)
out = limiter(L.master(10000.0, drive=1.28), ceiling=0.92)
write_wav(os.path.join(outdir, "the_alembic.wav"), out)
print(" ", seam_report(out))

# metrology: the arc (per-section rms), plink tuning, taraf
# resonance, width above the glug band
sec_names = ["simmer", "work", "pour", "transmission", "settle"]
for s_i, name in enumerate(sec_names):
    seg = out[int(bar_s(s_i * 4) * SR):int(bar_s(s_i * 4 + 4) * SR)]
    print(f"  {name:13s} rms {np.sqrt((seg ** 2).mean()):.3f}")
b1 = bubble(hz(76) * plink_comp(0.32, 0.32), chirp=0.32, damp=0.32)
z = np.where(np.diff(np.signbit(b1[:int(0.03 * SR)])))[0]
cents = 1200 * np.log2((SR / (2 * np.diff(z).mean())) / hz(76))
print(f"  plink E5 pitch {cents:+.0f}c")
detuned = sympathetic(metal, [m + 0.5 for m in STOCK], t60=3.8,
        coupling=0.12, mix=1.0, norm=False)
print(f"  taraf tuned/detuned {np.sqrt((taraf_raw ** 2).mean()) / np.sqrt((detuned ** 2).mean()):.2f}x")
sos_w = butter(4, 500, btype="high", fs=SR, output="sos")
hw = sosfilt(sos_w, out, axis=0)
print(f"  stereo corr >500Hz {np.corrcoef(hw[:, 0], hw[:, 1])[0, 1]:+.3f}")
for name, bus in [("cauldron", cauldron), ("pad", pad),
        ("metal", metal_room), ("taraf", taraf * 0.30),
        ("ticks", ticks_room), ("plinks", plinks), ("voice", voice),
        ("low", low)]:
    print(f"  {name:9s} rms {np.sqrt((bus ** 2).mean()):.4f}")

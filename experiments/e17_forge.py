#!/usr/bin/env python3
"""e17 — The Forge. Rheingold by way of the boiler room. Wagner
tuned his eighteen Nibelheim anvils to F; ours land there too.
The polyrhythm is the workshop's division of labor: the master
anvil strikes the dotted-quarter cycle (3 against the bar's 2),
the apprentice answers on the off-positions, and the clockwork
escapement holds straight eighths through all of it — tick-tock
alternating pitch and pallet (pan). Ratchet winding-bursts
(accelerating click trains) at phrase seams. Everything metal
rings in ir_tank; a sympathetic bank tuned to what the anvils
actually RADIATE (strike fundamentals + their 2.72x ring modes)
is the smithy's bar stock humming along. Steam is the only air.

Timbre targets: ticks = crisp, steam = airy, tank = the room.

    python3 experiments/e17_forge.py [outdir]
"""

import os
import sys

import numpy as np
from scipy.signal import butter, sosfilt

sys.path.insert(0, os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))))
from loam import SR, hz, Loop, stereo, ad_env, write_wav, seam_report
from loam.modal import strike, ANVIL, WOOD
from loam.strings import sympathetic
from loam.space import convolve_loop, ir_tank
from loam.dyn import duck, limiter
from loam import drums as dr

outdir = sys.argv[1] if len(sys.argv) > 1 else "render"
os.makedirs(outdir, exist_ok=True)
BPM = 112.0
spb = 60.0 / BPM
BARS = 12
L = Loop(BARS * 4 * spb, 0xE17)
rng = np.random.default_rng(0xE17)


def put(buf, at_s, chunk):
    idx = (int(at_s * SR) + np.arange(len(chunk))) % L.n
    np.add.at(buf, idx, chunk)


def put_itd(buf, at_s, mono, pan):
    """Placed source: level pan + far-ear arrival delay."""
    c = stereo(mono, pan)
    itd = int(abs(pan) * 0.0008 * SR)
    if itd:
        far = 0 if pan > 0 else 1
        c = np.vstack([c, np.zeros((itd, 2))])
        c[itd:, far] = c[:len(mono), far].copy()
        c[:itd, far] = 0.0
    put(buf, at_s, c)


# --- the hammers: 3 against 2, master and apprentice -----------
F3, C4, F4 = 174.61, 261.63, 349.23
metal = np.zeros((L.n, 2))
dq = 1.5 * spb                              # dotted quarter
n_master = int(round(L.loop_s / dq))        # 32 strikes over 12 bars
for k in range(n_master):
    at = k * dq
    acc = 1.0 if k % 4 == 0 else (0.55 if k % 2 else 0.75)
    if k % 16 == 14:                        # the smith inspects
        continue
    a = strike(F3, 2.6, ANVIL, amp=0.5 * acc, bright=1.05,
            knock=0.5, rng=rng)
    put_itd(metal, at, a, -0.45)
for k in range(n_master):                   # apprentice: off-cycle
    at = k * dq + 0.75 * spb
    if k % 4 in (1, 3):
        f = C4 if k % 8 < 4 else F4
        a = strike(f, 1.6, ANVIL, amp=0.28, bright=1.15,
                knock=0.35, rng=rng)
        put_itd(metal, at, a, 0.55)

# --- the clockwork: escapement + winding ratchet ---------------
ticks = np.zeros((L.n, 2))
for b8 in range(BARS * 8):                  # straight eighths
    at = b8 * spb / 2
    tock = b8 % 2
    w = strike(2200.0 if not tock else 1650.0, 0.05, WOOD,
            amp=0.19 if tock else 0.24, bright=1.3,
            knock=0.6, rng=rng)
    put_itd(ticks, at, w, 0.7 if tock else -0.7)
for bar in (3, 7, 11):                      # winding at phrase seams
    at0 = bar * 4 * spb + 2.0 * spb
    dt = 0.11
    for j in range(9):                      # pawl accelerates
        at = at0 + sum(dt * (0.82 ** i) for i in range(j))
        r = dr.rim(amp=0.30 * (0.9 ** j), seed=j)
        put(ticks, at, stereo(r, -0.5 + j * 0.12))

# --- the boiler: chuff + steam vents ---------------------------
low = np.zeros((L.n, 2))
kick_key = np.zeros(L.n)
for bar in range(BARS):
    at = bar * 4 * spb
    k = dr.kick(dur=0.5, f0=110.0, f1=38.0) * 0.65
    put(low, at, stereo(k, 0.0))
    put_idx = (int(at * SR) + np.arange(len(k))) % L.n
    np.add.at(kick_key, put_idx, k)

steam = np.zeros((L.n, 2))
sos_st = butter(2, [3000, 10000], btype="band", fs=SR, output="sos")
for bar in (0, 4, 8):                       # vent opens, sighs shut
    at = bar * 4 * spb + 3.0 * spb
    ln = int(1.4 * SR)
    tt = np.arange(ln) / SR
    env = np.clip(tt / 0.04, 0, 1) * np.exp(-tt * 2.2)
    v = sosfilt(sos_st, rng.standard_normal(ln)) * env * 0.16
    put(steam, at, stereo(v, float(rng.uniform(-0.6, 0.6))))
hiss_bed = sosfilt(butter(2, [4500, 11000], btype="band", fs=SR,
        output="sos"), rng.standard_normal((L.n, 2)), axis=0) * 0.008

# --- the room and the bar stock --------------------------------
metal_room = convolve_loop(metal, ir_tank(1.8, modes=11, seed=0xE17),
        mix=0.5)


def ring_midi(f):
    return 69.0 + 12.0 * np.log2(f / 440.0)


# bar stock tuned to what the anvils actually RADIATE: the strike
# fundamentals and their 2.72x ring modes (first draft used F
# pitch classes; the meter showed the bus dominated by 475 Hz —
# the ring — leaking through off-resonance strings)
STOCK = [ring_midi(f) for f in
        (F3, C4, F4, F3 * 2.72, C4 * 2.72, F4 * 2.72)]
# drive from the DRY strikes: the tank's dense mode wash feeds a
# string at ANY tuning, which both muddies the hum and defeats
# the detuned-control measurement; the bare anvil spectrum is
# sparse, so only a TUNED string finds it
taraf_raw = sympathetic(metal, STOCK, t60=3.8,
        coupling=0.12, mix=1.0, norm=False)
# the hum takes its own pass through a DIFFERENT tank: a second
# stereo IR decorrelates the level-panned string bank
taraf = convolve_loop(taraf_raw, ir_tank(1.2, modes=5, seed=99),
        mix=0.4)
ticks_room = convolve_loop(ticks, ir_tank(0.9, modes=6, seed=7),
        mix=0.25)

mix = metal_room + taraf * 0.32 + ticks_room + steam + hiss_bed
mix = duck(mix, kick_key, amount_db=4.0, release_ms=110.0)
L.buf += mix + low
out = limiter(L.master(11000.0, drive=1.3), ceiling=0.92)
write_wav(os.path.join(outdir, "e17_forge.wav"), out)
print(" ", seam_report(out))

# metrology: is the taraf RESONATING (not just passing the drive)?
# A quarter-tone-detuned bank fed the same signal should catch
# far less energy — the difference IS the resonance.
detuned = sympathetic(metal, [m + 0.5 for m in STOCK], t60=3.8,
        coupling=0.12, mix=1.0, norm=False)
r_tuned = np.sqrt((taraf_raw ** 2).mean())
r_det = np.sqrt((detuned ** 2).mean())
print(f"  taraf tuned/detuned energy: {r_tuned / r_det:.2f}x "
      f"(>1.5x = resonance, ~1x = leak-through)")
sp = np.abs(np.fft.rfft(taraf[:, 0] + taraf[:, 1]))
fr = np.fft.rfftfreq(L.n, 1 / SR)
top = fr[np.argsort(sp[(fr > 80) & (fr < 800)].copy())[-1] +
        np.searchsorted(fr, 80)]
print(f"  taraf loudest partial: {top:.1f} Hz "
      f"(anvil ring F3*2.72 = {F3 * 2.72:.1f})")
onset_period_beats = dq / spb
print(f"  master cycle {onset_period_beats:.2f} beats "
      f"({n_master} strikes/12 bars), escapement 8ths: 3:2 by design")
sos_w = butter(4, 500, btype="high", fs=SR, output="sos")
hw = sosfilt(sos_w, out, axis=0)
print(f"  stereo corr >500Hz: {np.corrcoef(hw[:, 0], hw[:, 1])[0, 1]:+.3f}")
for name, bus in [("metal", metal_room), ("taraf", taraf * 0.32),
        ("ticks", ticks_room), ("steam", steam), ("low", low)]:
    print(f"  {name:6s} rms {np.sqrt((bus ** 2).mean()):.4f}")

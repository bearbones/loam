#!/usr/bin/env python3
"""e22 — The two registers. Music sketch for NOCK's magitech
gradient: podunk flame-lit margins vs harnessed-lightning
institutions. The tech gradient is the stakes gradient, so the
music must be ONE identity re-clothed, not two unrelated tracks —
the same motif, the same key, the same tempo, walked from one end
of the world to the other. If it works, the in-game system is a
POSITION CROSSFADE: two synced loops, the mix knob tied to where
the level sits on the gradient.

FLAME (the margins): the motif on hand-plucked string with seeded
per-note cents drift (nobody tuned that gut this morning), wood
strikes answering, a swung shaker pocket (0.16 — loose hands), a
fire-crackle bed. Warm master, low ceiling of brightness.

LIGHTNING (the institution): the SAME motif, note for note, on
struck glass — dead on the grid, dead in tune — over a PADsynth
drone and a mains hum LOCKED to 96 Hz (e20's night tone: the
institution's tone was under the margins all along). Brighter
master, nothing loose anywhere.

Both are seamless loops (seam-craft rules), same 25.6s / 8 bars at
75 BPM, so they can crossfade in phase.

Measured, each claim on its own bus:
  - seam rank <= ~p99.9 on both masters (house gate)
  - grid deviation vs each note's DESIGNED time: flame's swung
    notes late by ~the 64 ms pocket, lightning on the grid (the
    first swing ruler assumed even eighths the motif never had)
  - floor breathing: envelope CV of the beds — the fire never
    stops breathing, the hum never breathes. (Two voice rulers
    died first: centroid lost to the standing transient rule —
    attack noise out-powers steady lines — and note-sustain lost
    because struck glass is percussion too. The steadiness axis
    lives in the floor.)
  - the floor: fire is broadband noise, the institution is one
    deep 96 Hz line (bed centroids, and the hum-lock FFT peak at
    96.0 Hz with prominence no fire can fake)
  - loudness: the institution presses ~2x rms harder BY DESIGN —
    the stakes gradient audible as pressure, not just color

    python3 experiments/e22_registers.py [outdir]
"""

import os
import sys

import numpy as np
from scipy.signal import find_peaks

sys.path.insert(0, os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))))
from loam import SR, Loop, hz, stereo, write_wav, seam_report
from loam.modal import strike, MARIMBA, GLASS, WOOD
from loam.strings import pluck
from loam.pads import padsynth_stereo, saw_amps
from loam.texture import fire
from loam.drums import shaker
from loam.rhythm import euclid, swing, onsets

outdir = sys.argv[1] if len(sys.argv) > 1 else "render"
os.makedirs(outdir, exist_ok=True)

BPM = 75.0
BEAT = 60.0 / BPM            # 0.8 s
LOOP_S = 32 * BEAT           # 8 bars of 4/4 = 25.6 s
SWING_POCKET = 0.16
HUM_HZ = 96.0                # e20's night tone: the institution's own

# the motif: two 4-bar phrases, call and answer, D minor pentatonic.
# (beat, midi, dur_beats) — shared verbatim by both registers.
MOTIF = [
    (0.0, 50, 1.5), (1.5, 53, 1.0), (2.5, 55, 1.5),
    (4.0, 57, 1.0), (5.0, 55, 0.5), (5.5, 53, 1.5),
    (8.0, 50, 1.5), (9.5, 53, 1.0), (10.5, 55, 1.5),
    (12.0, 57, 1.0), (13.0, 60, 2.0), (15.0, 57, 1.0),
    (16.0, 62, 1.5), (17.5, 60, 1.0), (18.5, 57, 1.5),
    (20.0, 55, 1.0), (21.0, 57, 0.5), (21.5, 53, 1.5),
    (24.0, 55, 1.5), (25.5, 53, 1.0), (26.5, 50, 1.5),
    (28.0, 45, 3.0),
]


def flame():
    L = Loop(LOOP_S, seed=0xE22)
    mel = np.zeros((L.n, 2))
    # the motif on gut string, swung and drifting: each onset late
    # by the pocket when it falls off-grid, each pitch a few cents
    # from true (seeded — deterministic, but nobody's tuner)
    beats = swing([b for b, _, _ in MOTIF], SWING_POCKET, 0.5)
    for (b0, (_, midi, durb)) in zip(beats, MOTIF):
        cents = L.rng.uniform(-8.0, 8.0)
        f = hz(midi) * 2.0 ** (cents / 1200.0)
        p = pluck(f, durb * BEAT + 0.8, amp=0.6, t60=1.6,
                  damp=0.5, soft=1,
                  seed=int(L.rng.integers(1 << 30)))
        chunk = stereo(p, float(L.rng.uniform(-0.25, 0.25)))
        idx = (int(b0 * BEAT * SR) + np.arange(len(chunk))) % L.n
        np.add.at(mel, idx, chunk)
    L.buf += mel
    # wood answers on the phrase turns
    for b0, midi in [(3.5, 38), (7.0, 41), (11.5, 38), (19.5, 41),
                     (23.0, 38), (27.5, 45)]:
        s = strike(hz(midi), 0.5, MARIMBA, amp=0.30, bright=0.8,
                   rng=L.rng, knock=0.4)
        L.add(b0 * BEAT, stereo(s, -0.4))
    # the pocket: a swung shaker, thinned like tired wrists
    pat = euclid(7, 16)
    for bar in range(8):
        for b in swing(onsets(pat, 0.25), SWING_POCKET, 0.25):
            if L.rng.random() < 0.85:
                s = shaker(0.10, amp=0.10,
                           seed=int(L.rng.integers(1 << 30)))
                L.add((bar * 4 + b) * BEAT, stereo(s, 0.45))
    # the bed: fire, wrapped by construction
    bed = fire(LOOP_S, crackle_rate=5.0) * 0.35
    L.buf += bed if bed.ndim == 2 else stereo(bed, 0.0)
    return L, mel, (bed if bed.ndim == 2 else stereo(bed, 0.0))


def lightning():
    L = Loop(LOOP_S, seed=0xE22 + 1)
    mel = np.zeros((L.n, 2))
    # the SAME motif on struck glass: on the grid, in tune, no pan
    # wander — the institution does not have loose hands
    for (b0, midi, durb) in MOTIF:
        s = strike(hz(midi + 24), max(durb * BEAT, 1.2), GLASS,
                   amp=0.26, bright=1.1, rng=L.rng, knock=0.1)
        chunk = stereo(s, 0.0)
        idx = (int(b0 * BEAT * SR) + np.arange(len(chunk))) % L.n
        np.add.at(mel, idx, chunk)
    L.buf += mel
    # the drone: D pad, seamless by construction on the loop grid
    pad = np.zeros((L.n, 2))
    for midi, g in [(38, 0.9), (45, 0.55), (50, 0.4), (53, 0.3)]:
        pad += padsynth_stereo(LOOP_S, hz(midi), saw_amps(10, 1.2),
                               bw_cents=25.0, seed=0xE22 + midi) * g
    pad *= 0.09
    L.buf += pad
    # the hum: 96 Hz mains pair, cycle-quantized, dead steady —
    # this line IS the institution (and e20's night tone, louder)
    f1 = L.q(HUM_HZ)
    hum = (np.sin(2 * np.pi * f1 * L.t)
           + 0.35 * np.sin(2 * np.pi * L.q(HUM_HZ * 2.0) * L.t)
           + 0.12 * np.sin(2 * np.pi * L.q(HUM_HZ * 3.0) * L.t))
    hum = stereo(hum * 0.07, 0.0)
    L.buf += hum
    return L, mel, pad + hum


# ---- the rulers -----------------------------------------------------

def grid_deviation(mel):
    """Median |onset - designed beat| in ms, and the median for the
    OFF-grid (swung) notes alone. The first draft measured pair
    ratios and assumed even eighths the motif never had — the honest
    ruler compares each note to ITS OWN designed time. Attacks are
    found on the envelope's positive derivative (glass tails
    overlap; peaks lie, attacks don't)."""
    m = np.abs(mel).sum(axis=1)
    k = int(0.01 * SR)
    env = np.convolve(m, np.ones(k) / k, "same")
    d = np.diff(env)
    d[d < 0] = 0.0
    pk, _ = find_peaks(d, height=d.max() * 0.10,
                       distance=int(0.3 * BEAT * SR))
    t = pk / SR
    devs, devs_off = [], []
    for (b0, _, _) in MOTIF:
        target = b0 * BEAT
        near = t[np.abs(t - target) < 0.3 * BEAT]
        if len(near) == 0:
            continue
        dv = (near[np.argmin(np.abs(near - target))] - target) * 1000.0
        devs.append(abs(dv))
        if round(b0 / 0.5) % 2:            # the notes swing() delays
            devs_off.append(dv)
    return (float(np.median(devs)),
            float(np.median(devs_off)) if devs_off else 0.0)


def floor_cv(bed):
    """Envelope coefficient of variation of a register's floor. Two
    voice rulers died before this one: centroid lost to the standing
    transient rule (attack noise out-powers steady lines), and note
    sustain lost because struck glass is percussion too. The
    steadiness axis lives in the FLOOR, where the registers actually
    differ: fire never stops breathing, the hum never breathes."""
    m = np.abs(bed).sum(axis=1)
    k = int(0.05 * SR)
    env = np.convolve(m, np.ones(k) / k, "same")[k:-k]
    return float(env.std() / (env.mean() + 1e-12))


def centroid(x):
    mono = x.sum(axis=1)
    spec = np.abs(np.fft.rfft(mono)) ** 2
    f = np.fft.rfftfreq(len(mono), 1 / SR)
    return float((spec * f).sum() / (spec.sum() + 1e-12))


def line_lock(bed, f_lo=80.0, f_hi=110.0):
    """(peak_hz, prominence) of the bed's spectrum in the hum band:
    prominence = band peak power / band median power."""
    mono = bed.sum(axis=1)
    spec = np.abs(np.fft.rfft(mono * np.hanning(len(mono)))) ** 2
    f = np.fft.rfftfreq(len(mono), 1 / SR)
    band = (f >= f_lo) & (f <= f_hi)
    fs, ps = f[band], spec[band]
    i = int(np.argmax(ps))
    return float(fs[i]), float(ps[i] / (np.median(ps) + 1e-18))


if __name__ == "__main__":
    Lf, mel_f, bed_f = flame()
    Ll, mel_l, bed_l = lightning()
    mf = Lf.master(lp_hz=4800.0, drive=1.3)
    ml = Ll.master(lp_hz=9000.0, drive=1.15)
    write_wav(os.path.join(outdir, "e22_flame.wav"), mf)
    write_wav(os.path.join(outdir, "e22_lightning.wav"), ml)

    # the pitch to the operator: one identity walking the gradient —
    # 8s margins, 8s crossfade, 8s institution, phase-synced
    n8 = int(8.0 * SR)
    x = np.linspace(0, 1, n8)[:, None]
    demo = np.vstack([mf[:n8], mf[n8:2 * n8] * (1 - x) + ml[n8:2 * n8] * x,
                      ml[2 * n8:3 * n8]])
    write_wav(os.path.join(outdir, "e22_registers_xfade.wav"), demo)

    print("== seam ==")
    print("  flame:     ", seam_report(mf))
    print("  lightning: ", seam_report(ml))
    df_all, df_off = grid_deviation(mel_f)
    dl_all, dl_off = grid_deviation(mel_l)
    print("== grid deviation (median ms vs designed beats) ==")
    print("  flame  all %.0f ms, swung notes %+.0f ms (design +64)"
          % (df_all, df_off))
    print("  lightning all %.0f ms (design ~0: the grid)" % dl_all)
    print("== floor breathing (envelope CV) ==")
    sf, sl = floor_cv(bed_f), floor_cv(bed_l)
    print("  flame %.2f  >>  lightning %.2f : %s (the hum never breathes)"
          % (sf, sl, "YES" if sf > 4.0 * sl else "NO"))
    print("== the floor: broadband fire vs a single deep line ==")
    cbf, cbl = centroid(bed_f), centroid(bed_l)
    print("  flame %.0f Hz (noise)  >  lightning %.0f Hz (line) : %s"
          % (cbf, cbl, "YES" if cbf > cbl else "NO"))
    print("== hum lock (80-110 Hz peak, prominence) ==")
    hf = line_lock(bed_f)
    hl = line_lock(bed_l)
    print("  flame bed:     %.1f Hz x%.0f (a fire has no line)" % hf)
    print("  lightning bed: %.1f Hz x%s (want 96.0, prom >1000)"
          % (hl[0], (">1e6" if hl[1] > 1e6 else "%.0f" % hl[1])))
    print("== loudness: rms flame %.3f vs lightning %.3f (x%.1f)"
          % (np.sqrt((mf ** 2).mean()), np.sqrt((ml ** 2).mean()),
             np.sqrt((ml ** 2).mean()) / np.sqrt((mf ** 2).mean())))

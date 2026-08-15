#!/usr/bin/env python3
"""e32 — The wanderer's register. The second ruled mood pole
(Diablo II / Dishonored) to stand against e31's noir spy in the
operator's A/B. Tristram's lesson is RUBATO: a wandering 12-string
over a drone, no grid at all — dread as patience. Dishonored's
lesson is the FLOOR: a breathing, bowed dark that never lifts.

Same one-system thesis as e31: only the world's timbres. The
wander is gut string with the 12-string's octave course (every
note doubled +12, softer, 14 ms behind, a few cents off — the
Tristram shimmer); the floor is a dark D pad + the institution's
own 96 Hz hum line, quantized to the loop, under a slow wind
breath. Landings stay D-minor pentatonic; Bb passes for the
gothic lean; E (the stained verdict pitch) is never touched.

Rulers (each can die):
  - NO grid fits: search every uniform grid (period 0.25-1.3 s,
    all phases) against the wander's MEASURED onsets — best
    residual must stay >= 25 ms. Control: the same search on
    e22's lightning melody (dead on its grid) must find one
    under 8 ms. Rubato as a measurement, with a positive control.
  - the floor never lifts, but breathes: bed envelope min >=
    0.35x median (no silence anywhere), envelope CV in
    [0.08, 0.5] (between the hum's dead calm 0.06 and fire's
    0.59 — a slow lung, not a flicker).
  - the institution is under it: line_lock finds the 96 Hz line
    (prominence >= 20) — the same line e22 shipped; one world.
  - home stays home: D pitch-class energy >= 4x the loudest
    passing class (Bb/C#) — wandering is not leaving.
  - house gate: seam rank <= ~p99.9.

Render: loop + first 8 s again (seam audible); _wander bare
melody for judging the hands.

    python3 experiments/e32_wanderer.py [outdir]
"""

import importlib.util
import os
import sys

import numpy as np

_here = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(_here))
from loam import SR, Loop, hz, stereo, write_wav, seam_report
from loam.pads import padsynth_stereo, saw_amps
from loam.strings import pluck
from loam.texture import wind

_spec = importlib.util.spec_from_file_location(
    "e22", os.path.join(_here, "e22_registers.py"))
e22 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(e22)

outdir = sys.argv[1] if len(sys.argv) > 1 else "render"
os.makedirs(outdir, exist_ok=True)

LOOP_S = 24.0          # no BPM. The wander owns its own time.
HUM_HZ = 96.0          # the institution's line (e20/e22), verbatim

# the wander: (t_s, midi, dur_s, amp) — hand-authored rubato, a
# phrase that leans forward, stalls, and finally settles. Grace
# notes marked g are struck 70 ms early, quick and soft.
WANDER = [
    (0.00, 62, 2.2, 0.9),
    (1.65, 65, 1.4, 0.6),
    (2.55, 67, 2.6, 0.8),
    (4.90, 65, 1.0, 0.5),
    (5.55, 62, 2.8, 0.85),
    (7.95, 69, 2.2, 0.7),
    (10.60, 67, 0.9, 0.5),
    (11.25, 65, 1.1, 0.6),
    (12.10, 62, 2.6, 0.9),
    (14.85, 58, 2.0, 0.6),      # Bb passes: the gothic lean
    (17.20, 57, 1.2, 0.65),
    (18.05, 60, 1.6, 0.5),
    (19.40, 62, 3.4, 1.0),      # the settle
    (21.60, 50, 2.4, 0.55),     # low D under the settle's tail
]
GRACE = {2: 65, 8: 60, 12: 60}  # index -> grace midi (70 ms early)


def build():
    L = Loop(LOOP_S, seed=0xE32)
    wanderb = np.zeros((L.n, 2))
    for i, (t0, midi, d, a) in enumerate(WANDER):
        if i in GRACE:
            g = pluck(hz(GRACE[i]), 0.5, amp=a * 0.28, t60=1.2,
                      damp=0.4, soft=1, seed=int(L.rng.integers(1 << 30)))
            idx = (int((t0 - 0.07) * SR) + np.arange(len(g))) % L.n
            np.add.at(wanderb, idx, stereo(g, -0.1))
        # the 12-string course: fundamental + octave, softer, 14 ms
        # behind, seeded cents off — the Tristram shimmer
        cents = float(L.rng.uniform(-6.0, 6.0))
        for (dm, da, dt) in [(0, 1.0, 0.0), (12, 0.55, 0.014)]:
            f = hz(midi + dm) * 2.0 ** (cents / 1200.0)
            p = pluck(f, d + 1.2, amp=a * 0.5 * da, t60=2.6,
                      damp=0.32, pick=0.18, soft=1,
                      seed=int(L.rng.integers(1 << 30)))
            idx = (int((t0 + dt) * SR) + np.arange(len(p))) % L.n
            np.add.at(wanderb, idx, stereo(p, float(L.rng.uniform(-0.3, 0.3))))
    bed = np.zeros((L.n, 2))
    for midi, g in [(38, 1.0), (45, 0.5), (50, 0.35)]:
        bed += padsynth_stereo(LOOP_S, hz(midi), saw_amps(8, 1.4),
                               bw_cents=30.0, seed=0xE32 + midi) * g
    bed *= 0.075
    f1 = L.q(HUM_HZ)
    hum = (np.sin(2 * np.pi * f1 * L.t)
           + 0.3 * np.sin(2 * np.pi * L.q(HUM_HZ * 2.0) * L.t))
    bed += stereo(hum * 0.045, 0.0)
    # the breath: dark wind, riding a loop-quantized slow lung so
    # the floor breathes without ever lifting
    w = wind(LOOP_S, base_hz=340.0, howl=0.25)
    if w.ndim == 1:
        w = stereo(w, 0.0)
    lung = 0.72 + 0.28 * np.sin(2 * np.pi * 3.0 * L.t / LOOP_S
                                + 0.8 * np.sin(2 * np.pi * 2.0 * L.t / LOOP_S))
    bed += w * lung[:, None] * 0.16
    L.buf += wanderb + bed
    return L, wanderb, bed


def local_onset(x, t0):
    k = int(0.008 * SR)
    env = np.convolve(np.abs(x), np.ones(k) / k, "same")
    a = max(int((t0 - 0.05) * SR), 0)
    b = min(int((t0 + 0.10) * SR), len(x))
    w = env[a:b]
    return (a + int(np.argmax(w > 0.35 * w.max()))) / SR


def best_grid_residual(onsets):
    """Best uniform grid over all periods/phases: median distance of
    each onset to its nearest grid line, minimized. The rubato ruler."""
    onsets = np.asarray(onsets)
    best = 1e9
    for T in np.arange(0.25, 1.30001, 0.0025):
        ph = np.mod(onsets, T)
        # circular median distance to nearest line for this period,
        # phase chosen by circular mean of the onset phases
        ang = ph / T * 2 * np.pi
        mean_ang = np.arctan2(np.sin(ang).mean(), np.cos(ang).mean())
        d = np.abs(np.angle(np.exp(1j * (ang - mean_ang)))) / (2 * np.pi) * T
        best = min(best, float(np.median(d)))
    return best


def pc_energy(x, freqs, half_frac=0.015):
    spec = np.abs(np.fft.rfft(x)) ** 2
    f = np.fft.rfftfreq(len(x), 1 / SR)
    return sum(float(spec[(f >= f0 * (1 - half_frac))
                          & (f <= f0 * (1 + half_frac))].sum())
               for f0 in freqs)


if __name__ == "__main__":
    L, wanderb, bed = build()
    master = L.master(lp_hz=6200.0, drive=1.2)
    mono = master.mean(axis=1)
    wm = wanderb.mean(axis=1)

    print("== seam (house gate) ==")
    print("  ", seam_report(master))

    print("== no grid fits the wander (rubato, with a control) ==")
    got = [local_onset(wm, t0) for (t0, _, _, _) in WANDER]
    r32 = best_grid_residual(got)
    Ll, mel_l, _ = e22.lightning()
    lm = mel_l.mean(axis=1)
    got_l = [local_onset(lm, b * e22.BEAT) for (b, _, _) in e22.MOTIF]
    rl = best_grid_residual(got_l)
    ok = r32 >= 0.025 and rl <= 0.008
    print("  wander best-grid residual %.1f ms (want >= 25); e22 "
          "lightning control %.1f ms (want <= 8): %s"
          % (r32 * 1000.0, rl * 1000.0, "YES" if ok else "NO"))

    print("== the floor never lifts, but breathes ==")
    k = int(0.05 * SR)
    env = np.convolve(np.abs(bed.mean(axis=1)), np.ones(k) / k, "same")
    env = env[k:-k]
    lift = float(env.min() / np.median(env))
    cv = float(env.std() / env.mean())
    ok_f = lift >= 0.35 and 0.08 <= cv <= 0.5
    print("  min/median %.2f (want >= 0.35), env CV %.2f (want "
          "0.08-0.5): %s" % (lift, cv, "YES" if ok_f else "NO"))

    print("== the institution is under it ==")
    pf, prom = e22.line_lock(bed)
    print("  bed line %.1f Hz (design %.1f) prominence %.0f (want "
          ">= 20): %s" % (pf, L.q(HUM_HZ),
                          prom, "YES" if prom >= 20.0 else "NO"))

    print("== home stays home ==")
    d_e = pc_energy(mono, [hz(38), hz(50), hz(62), hz(74)])
    bb_e = pc_energy(mono, [hz(46), hz(58), hz(70)])
    cs_e = pc_energy(mono, [hz(49), hz(61), hz(73)])
    worst = max(bb_e, cs_e)
    print("  D %.2e vs worst passing class %.2e (x%.1f, want >= 4): %s"
          % (d_e, worst, d_e / max(worst, 1e-12),
             "YES" if d_e >= 4.0 * worst else "NO"))

    n8 = int(8.0 * SR)
    exhibit = np.vstack([master, master[:n8]])
    write_wav(os.path.join(outdir, "e32_wanderer.wav"),
              np.clip(exhibit * 0.95, -0.99, 0.99))
    write_wav(os.path.join(outdir, "e32_wanderer_bare.wav"),
              np.clip(wanderb * 0.95, -0.99, 0.99))
    print("wrote", outdir + "/e32_wanderer.wav  (+ _bare melody)")

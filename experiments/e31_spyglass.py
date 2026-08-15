#!/usr/bin/env python3
"""e31 — The spy's register. Operator ruling on e28: the shipped
registers read as "plucking guitar strings one at a time... too
lifeless." Mood poles ruled: TF2 Spy (60s noir) with a high-fantasy
twist / Diablo II + Dishonored. This sketch takes the NOIR pole.

The thesis: the mood is built from the WORLD'S OWN two timbres —
gut string (flame margins) walking a swung noir bass, struck glass
(lightning institutions) answering from above — so the spy can sit
anywhere on the tech gradient without adding a third instrument
family. High fantasy lives in the lutherie (gut and glass, no
horns, no piano); noir lives in the WALK: chromatic passing tones
on weak beats (home landings stay D-minor pentatonic; E, the
stained verdict pitch, is never touched), backbeat brushes, an
anticipation stab on the and-of-4, and a bar-8 fill that leans
into the wrap so the loop resolves V->i forever.

"Lifeless" is treated as MEASURABLE, not a vibe:
  - dynamics breathe: designed accents (1.0 strong / 0.62 weak,
    phrase duck bars 5-6, fill lean bar 8) must survive render —
    per-designed-note level CV >= 2x the SHIPPED e22 flame
    register's note CV (the baseline that read as lifeless).
  - the pocket is real: brush off-eighths land late by the swing
    (+0.12 beat) vs the straight grid, on-eighths stay on it —
    local hysteresis onsets per designed time (e29's ruler; global
    pickers and derivative peaks stay dead).
  - the phrase moves: bars 5-8 are a variation, not a copy —
    envelope correlation of the loop's halves < 0.9, while the
    SEAM still passes (variation without breaking the wrap).
  - home stays home: chromatic passing tones pass — pitch-class
    energy at D across octaves >= 4x the G#/B passing tones.
  - house gate: seam rank <= ~p99.9 on the master.

Render: the loop once + its first 4 bars again (the seam audible),
plus a bass+brush-only underlay for judging the walk bare.

    python3 experiments/e31_spyglass.py [outdir]
"""

import importlib.util
import os
import sys

import numpy as np
from scipy.signal import butter, sosfilt

_here = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(_here))
from loam import SR, Loop, hz, stereo, write_wav, seam_report
from loam.modal import strike, GLASS
from loam.strings import pluck
from loam.drums import shaker

_spec = importlib.util.spec_from_file_location(
    "e22", os.path.join(_here, "e22_registers.py"))
e22 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(e22)

outdir = sys.argv[1] if len(sys.argv) > 1 else "render"
os.makedirs(outdir, exist_ok=True)
rng = np.random.default_rng(0xE31)

BPM = 84.0                  # noir slink: slower than e22's 75? No —
BEAT = 60.0 / BPM           # faster clock, heavier pocket: the walk
LOOP_S = 32 * BEAT          # 8 bars of 4/4 = 22.857 s
SWING = 0.24                # off-eighth delay = 0.24*0.5 = 0.12 beat
POCKET_S = SWING * 0.5 * BEAT   # = 85.7 ms late

# the walk: (beat, midi, amp). Strong-beat landings pentatonic;
# chromatics (G# 44, Eb 39, B 47, Bb 46) only ever PASS on weak
# beats. Bars 5-6 duck (the phrase breathes), bar 8 fills and leans
# on A so the wrap lands V->i on D forever. E (40) never appears:
# that pitch class belongs to the stained verdict (e29).
ACC = [1.0, 0.62, 0.85, 0.62]
WALK = []
_bars = [
    [38, 41, 43, 44],   # D  F  G  G#>
    [45, 43, 41, 39],   # A  G  F  Eb>
    [38, 41, 45, 48],   # D  F  A  C
    [48, 47, 46, 45],   # C  B> Bb> A
    [38, 45, 43, 41],   # D  A  G  F      (duck)
    [41, 43, 45, 46],   # F  G  A  Bb>    (duck)
    [38, 41, 43, 45],   # D  F  G  A
]
for _bi, _bar in enumerate(_bars):
    for _qi, _m in enumerate(_bar):
        _a = ACC[_qi] * (0.85 if _bi in (4, 5) else 1.0)
        WALK.append((_bi * 4.0 + _qi, _m, _a))
WALK += [(28.0, 48, 1.1), (29.0, 46, 0.68), (30.0, 45, 0.94),
         (30.0 + 0.5 + SWING * 0.5, 44, 0.7), (31.0, 45, 1.05)]

# the answers: struck glass, sparse, high, pentatonic — the
# institution's timbre leaning into the margins' tune
ANSWERS = [(4.0 + 1.5 + SWING * 0.5, 74, 0.9, 0.20),
           (12.0 + 0.5 + SWING * 0.5, 77, 0.7, 0.18),
           (12.0 + 2.0, 74, 1.1, 0.16),
           (20.0 + 2.5 + SWING * 0.5, 69, 1.0, 0.18),
           (25.0 + 0.5 + SWING * 0.5, 74, 1.3, 0.20)]

# the stab: a gut chord bitten on the and-of-4 (anticipation),
# bars 2/4/6 — Dm7 shell, no fifth, strummed 18 ms
STABS = [7.5 + SWING * 0.5, 15.5 + SWING * 0.5, 23.5 + SWING * 0.5]

# brushes: swung eighths, backbeat accent, human thinning
BRUSH_AMP = [0.30, 0.16, 0.55, 0.16, 0.30, 0.16, 0.55, 0.20]


def brush_sweep(dur=0.30, amp=0.12, seed=0):
    n = int(dur * SR)
    r = np.random.default_rng(seed)
    sos = butter(2, [1800.0, 7500.0], "bandpass", fs=SR, output="sos")
    x = sosfilt(sos, r.uniform(-1, 1, n))
    env = np.minimum(np.arange(n) / (0.55 * n), 1.0)
    env = np.minimum(env, np.linspace(2.2, 0.0, n).clip(0, 1))
    return x * env * amp


def build():
    L = Loop(LOOP_S, seed=0xE31)
    bass = np.zeros((L.n, 2))
    brush = np.zeros((L.n, 2))
    for (b0, midi, a) in WALK:
        p = pluck(hz(midi), 1.4, amp=0.52 * a, t60=1.1, damp=0.55,
                  soft=2, pick=0.12, seed=int(L.rng.integers(1 << 30)))
        idx = (int(b0 * BEAT * SR) + np.arange(len(p))) % L.n
        np.add.at(bass, idx, stereo(p, -0.1))
    for bar in range(8):
        for e in range(8):
            if L.rng.random() > 0.93:
                continue
            t = bar * 4.0 + e * 0.5 + (SWING * 0.5 if e % 2 else 0.0)
            s = shaker(0.07, amp=BRUSH_AMP[e] * 0.30,
                       seed=int(L.rng.integers(1 << 30)))
            idx = (int(t * BEAT * SR) + np.arange(len(s))) % L.n
            np.add.at(brush, idx, stereo(s, 0.4))
        for bt in (1.0, 3.0):
            sw = brush_sweep(seed=int(L.rng.integers(1 << 30)))
            idx = (int((bar * 4.0 + bt) * BEAT * SR)
                   + np.arange(len(sw))) % L.n
            np.add.at(brush, idx, stereo(sw, 0.25))
    stab = np.zeros((L.n, 2))
    for b0 in STABS:
        for k, midi in enumerate([50, 53, 60]):
            p = pluck(hz(midi), 0.9, amp=0.30 - 0.05 * k, t60=0.7,
                      damp=0.5, soft=1,
                      seed=int(L.rng.integers(1 << 30)))
            i0 = int((b0 * BEAT + k * 0.018) * SR)
            idx = (i0 + np.arange(len(p))) % L.n
            np.add.at(stab, idx, stereo(p, -0.35))
    ans = np.zeros((L.n, 2))
    for (b0, midi, d, a) in ANSWERS:
        s = strike(hz(midi), d, GLASS, amp=a, bright=1.05, rng=L.rng,
                   knock=0.12)
        idx = (int(b0 * BEAT * SR) + np.arange(len(s))) % L.n
        np.add.at(ans, idx, stereo(s, 0.3))
    L.buf += bass + brush + stab + ans
    return L, bass, brush


def local_onset(x, t0):
    # e29's ruler: hysteresis crossing of the local max in a window
    # around the DESIGNED time (global pickers stay dead)
    k = int(0.008 * SR)
    env = np.convolve(np.abs(x), np.ones(k) / k, "same")
    a = max(int((t0 - 0.05) * SR), 0)
    b = min(int((t0 + 0.10) * SR), len(x))
    w = env[a:b]
    return (a + int(np.argmax(w > 0.35 * w.max()))) / SR


def note_levels(x, times, win=0.22):
    out = []
    for t0 in times:
        a = int(t0 * SR)
        seg = x[a:a + int(win * SR)]
        out.append(np.percentile(np.abs(seg), 99.0))
    return np.array(out)


def pc_energy(x, freqs, half_frac=0.015):
    spec = np.abs(np.fft.rfft(x)) ** 2
    f = np.fft.rfftfreq(len(x), 1 / SR)
    tot = 0.0
    for f0 in freqs:
        band = (f >= f0 * (1 - half_frac)) & (f <= f0 * (1 + half_frac))
        tot += float(spec[band].sum())
    return tot


if __name__ == "__main__":
    L, bass, brush = build()
    master = L.master(lp_hz=6800.0, drive=1.25)
    mono = master.mean(axis=1)
    bass_m = bass.mean(axis=1)
    brush_m = brush.mean(axis=1)

    print("== seam (house gate) ==")
    print("  ", seam_report(master))

    print("== dynamics breathe (vs the shipped register that read "
          "lifeless) ==")
    lv = note_levels(bass_m, [b * BEAT for (b, _, _) in WALK])
    cv31 = float(lv.std() / lv.mean())
    Lf, mel_f, _ = e22.flame()
    mel_fm = mel_f.mean(axis=1)
    tf = [b * e22.BEAT for b in
          __import__("loam.rhythm", fromlist=["swing"]).swing(
              [b for b, _, _ in e22.MOTIF], e22.SWING_POCKET, 0.5)]
    lv22 = note_levels(mel_fm, tf)
    cv22 = float(lv22.std() / lv22.mean())
    print("  e31 walk note-level CV %.3f vs e22 flame %.3f (x%.1f, "
          "want >= 2): %s" % (cv31, cv22, cv31 / max(cv22, 1e-9),
                              "YES" if cv31 >= 2.0 * cv22 else "NO"))

    print("== the pocket is real (brush bus, per-designed-time) ==")
    errs_on, lates_off = [], []
    for bar in range(8):
        for e in range(8):
            t_design = (bar * 4.0 + e * 0.5
                        + (SWING * 0.5 if e % 2 else 0.0)) * BEAT
            t_grid = (bar * 4.0 + e * 0.5) * BEAT
            got = local_onset(brush_m, t_design)
            if e % 2:
                lates_off.append((got - t_grid) * 1000.0)
            else:
                errs_on.append(abs(got - t_design) * 1000.0)
    on_ms = float(np.median(errs_on))
    off_ms = float(np.median(lates_off))
    ok_sw = on_ms <= 15.0 and abs(off_ms - POCKET_S * 1000.0) <= 15.0
    print("  on-eighths %.1f ms off design (want <= 15); off-eighths "
          "+%.1f ms late vs straight grid (design +%.1f): %s"
          % (on_ms, off_ms, POCKET_S * 1000.0, "YES" if ok_sw else "NO"))

    print("== the phrase moves, the loop still wraps ==")
    k = int(0.02 * SR)
    env = np.convolve(np.abs(mono), np.ones(k) / k, "same")
    h = len(env) // 2
    a, b = env[:h] - env[:h].mean(), env[h:] - env[h:].mean()
    corr = float((a * b).sum() / max(np.sqrt((a * a).sum())
                                     * np.sqrt((b * b).sum()), 1e-12))
    print("  half-vs-half envelope corr %.2f (want < 0.9): %s"
          % (corr, "YES" if corr < 0.9 else "NO"))

    print("== home stays home (passing tones pass) ==")
    d_e = pc_energy(mono, [hz(38), hz(50), hz(62), hz(74)])
    gs_e = pc_energy(mono, [hz(44), hz(56), hz(68)])
    b_e = pc_energy(mono, [hz(47), hz(59), hz(71)])
    worst = max(gs_e, b_e)
    print("  D %.2e vs worst passing class %.2e (x%.1f, want >= 4): %s"
          % (d_e, worst, d_e / max(worst, 1e-12),
             "YES" if d_e >= 4.0 * worst else "NO"))

    n4 = int(16 * BEAT * SR)
    exhibit = np.vstack([master, master[:n4]])
    write_wav(os.path.join(outdir, "e31_spyglass.wav"),
              np.clip(exhibit * 0.95, -0.99, 0.99))
    under = np.clip((bass + brush) * 0.95, -0.99, 0.99)
    write_wav(os.path.join(outdir, "e31_spyglass_walk.wav"), under)
    print("wrote", outdir + "/e31_spyglass.wav  (+ _walk underlay)")

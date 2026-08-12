#!/usr/bin/env python3
"""e27 — The borderland. Music sketch for NOCK's mid-gradient: what
should the tune do HALFWAY between flame and lightning? The in-game
system (music.gd, from e22) equal-power crossfades two phase-locked
loops — but flame is swung +64 ms and lightning is dead on grid, so
at 50/50 every swung note should arrive TWICE: glass on the grid,
gut a pocket late. The question under measurement: is the middle of
the map a blend, or a FLAM — and if it flams, the middle needs its
own register. The candidate: THE BORDERLAND PLAYS LIGHTNING'S TIME
WITH FLAME'S HANDS — gut plucks, dead on grid, dead in tune, no pan
wander, over a floor that keeps both fires burning quietly (a
thinned stove + a faint mains hum). Second-hand discipline: the
margins near the wall have learned the institution's clock but not
bought its instruments.

Measured:
  - THE FLAM IS REAL: at 50/50, at least 8 of the 10 swung motif
    positions receive BOTH voices' attacks at ear parity (within
    12 dB, each measured on its own bus at its own designed time
    — glass on the grid, pluck in the +64 ms pocket)
  - THE BORDERLAND REMOVES THE MECHANISM by construction (one
    voice at those positions); its measurable half is discipline:
    median |grid deviation| <= 4 ms (vs flame's swung +64)
  - flame's hands, in tune: the 4 longest notes within 3 cents of
    design (plain narrow-band peak, e23's ruler — vs flame's
    seeded +/-8 drift)
  - genuinely between: floor CV strictly ordered lightning <
    borderland < flame (the steadiness axis lives in the floor,
    e22's surviving ruler)

Render: 8 s of the naive 50/50 (the flam exhibit), then a 24 s walk
across the full gradient with the borderland bump in the middle
(flame -> borderland -> lightning, weights power-normalized).

    python3 experiments/e27_borderland.py [outdir]
"""

import importlib.util
import os
import sys

import numpy as np
from scipy.signal import find_peaks

_here = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(_here))
from loam import SR, hz, stereo, write_wav, Loop, seam_report
from loam.strings import pluck
from loam.texture import fire

_spec = importlib.util.spec_from_file_location(
    "e22", os.path.join(_here, "e22_registers.py"))
e22 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(e22)
BEAT, LOOP_S, MOTIF = e22.BEAT, e22.LOOP_S, e22.MOTIF

outdir = sys.argv[1] if len(sys.argv) > 1 else "render"
os.makedirs(outdir, exist_ok=True)

BUMP_W = 0.35    # borderland's half-width on the gradient


def borderland():
    """Flame's hands, lightning's time: gut plucks ON the grid, IN
    tune, centered — over a thinned stove and a faint hum (both
    floors present: the borderland hears the wall AND the fire)."""
    L = Loop(LOOP_S, seed=0xE27)
    mel = np.zeros((L.n, 2))
    for (b0, midi, durb) in MOTIF:
        p = pluck(hz(midi), durb * BEAT + 0.8, amp=0.6, t60=1.6,
                  damp=0.5, soft=1, seed=int(L.rng.integers(1 << 30)))
        chunk = stereo(p, 0.0)
        idx = (int(b0 * BEAT * SR) + np.arange(len(chunk))) % L.n
        np.add.at(mel, idx, chunk)
    L.buf += mel
    stove = fire(LOOP_S, crackle_rate=5.0) * 0.22
    stove = stove if stove.ndim == 2 else stereo(stove, 0.0)
    hum = stereo((np.sin(2 * np.pi * L.q(e22.HUM_HZ) * L.t)
                  + 0.35 * np.sin(2 * np.pi * L.q(e22.HUM_HZ * 2) * L.t))
                 * 0.025, 0.0)
    bed = stove + hum
    L.buf += bed
    return L, mel, bed


def weights(x):
    """The walk law: cos/sin ends with a squared-cosine borderland
    bump, power-normalized — the in-game candidate for music.gd."""
    m = np.cos(np.clip((x - 0.5) / BUMP_W, -1, 1) * np.pi / 2) ** 2
    wf = (1 - m) * np.cos(x * np.pi / 2)
    wl = (1 - m) * np.sin(x * np.pi / 2)
    norm = np.sqrt(wf * wf + wl * wl + m * m) + 1e-12
    return wf / norm, m / norm, wl / norm


# ---- the rulers -----------------------------------------------------

SWUNG = [b0 for (b0, _, _) in MOTIF if int(round(b0 / 0.5)) % 2 == 1]


def attack_db(bus, a_s, b_s):
    """Attack strength in a window: peak of the positive envelope
    derivative, in dB. Per-BUS — a single-bus two-attack detector
    died here twice: a gut pluck's slightly inharmonic partials
    BEAT, putting a real secondary swell 40-80 ms after its own
    attack, indistinguishable from a second instrument no matter
    the smoothing. The flam's two attacks live on different buses
    by construction; measure them there."""
    m = np.abs(bus).sum(axis=1)
    k = int(0.008 * SR)
    env = np.convolve(m, np.ones(k) / k, "same")
    d = np.diff(env[int(a_s * SR):int(b_s * SR)])
    d[d < 0] = 0.0
    return 20.0 * np.log10(float(d.max()) + 1e-12)


def flam_mechanism(mf_bus, ml_bus):
    """Positions where BOTH voices land an attack at their own
    designed time — glass on the grid, pluck in the +64 ms pocket —
    at comparable strength (within 12 dB). e22 already banked the
    times (+63 ms swung, grid +/-3); what makes the flam AUDIBLE is
    both attacks arriving at ear-level parity."""
    n = 0
    for b0 in SWUNG:
        tg = b0 * BEAT
        g = attack_db(ml_bus, tg - 0.02, tg + 0.025)
        p = attack_db(mf_bus, tg + 0.035, tg + 0.10)
        if abs(g - p) <= 12.0:
            n += 1
    return n


def note_cents(mel_bus, picks):
    """Plain narrow-band peak (e23) with parabolic interpolation
    (e25) — at 110 Hz a 1<<17 bin is 5.3 cents wide, so the raw
    argmax alone would flunk an honestly tuned string on
    resolution."""
    out = []
    for (b0, midi, durb) in picks:
        a = int((b0 * BEAT + 0.03) * SR)
        seg = mel_bus[a:a + int(0.25 * SR)].sum(axis=1)
        spec = np.abs(np.fft.rfft(seg * np.hanning(len(seg)), n=1 << 17))
        f = np.fft.rfftfreq(1 << 17, 1 / SR)
        band = (f >= hz(midi) * 0.85) & (f <= hz(midi) * 1.15)
        i = np.argmax(spec[band]) + np.flatnonzero(band)[0]
        pa, pb, pc = spec[i - 1], spec[i], spec[i + 1]
        di = 0.5 * (pa - pc) / (pa - 2 * pb + pc + 1e-12)
        pk = f[i] + di * (f[1] - f[0])
        out.append(1200.0 * np.log2(pk / hz(midi)))
    return out


if __name__ == "__main__":
    Lf, mel_f, bed_f = e22.flame()
    Ll, mel_l, bed_l = e22.lightning()
    Lm, mel_m, bed_m = borderland()
    mf = Lf.master(lp_hz=4800.0, drive=1.3)
    ml = Ll.master(lp_hz=9000.0, drive=1.15)
    mm = Lm.master(lp_hz=6500.0, drive=1.2)

    print("== the flam is real (naive 50/50, swung positions) ==")
    naive = flam_mechanism(mel_f, mel_l)
    print("  %d/%d positions get BOTH attacks at ear parity, 64 ms"
          " apart by e22's own tape (want >= 8)" % (naive, len(SWUNG)))
    # the borderland removes the mechanism by construction (one voice
    # at those positions) — its measurable half is the discipline:

    da, _ = e22.grid_deviation(mel_m)
    print("== lightning's time: median |grid dev| %.1f ms (want <= 4) =="
          % da)

    picks = sorted(MOTIF, key=lambda n: -n[2])[:4]
    cts = note_cents(mel_m, picks)
    print("== flame's hands, in tune: worst %+.1f cents (want <= 3) =="
          % max(abs(c) for c in cts))

    cf, cm, cl = (e22.floor_cv(bed_f), e22.floor_cv(bed_m),
                  e22.floor_cv(bed_l))
    print("== between: floor CV lightning %.2f < borderland %.2f "
          "< flame %.2f : %s ==" % (cl, cm, cf,
          "YES" if cl < cm < cf else "NO"))
    print("== seam: borderland ==")
    print("  ", seam_report(mm))

    # the exhibit, then the walk
    n8 = int(8.0 * SR)
    exhibit = (mf[:n8] + ml[:n8]) * 0.707
    n24 = int(24.0 * SR)
    x = np.linspace(0, 1, n24)
    wf, wm, wl = weights(x)
    idx = np.arange(n24) % mf.shape[0]
    walk = (mf[idx] * wf[:, None] + mm[idx] * wm[:, None]
            + ml[idx] * wl[:, None])
    demo = np.vstack([exhibit, np.zeros((int(0.6 * SR), 2)), walk])
    demo = demo / np.max(np.abs(demo)) * 0.85
    write_wav(os.path.join(outdir, "e27_borderland.wav"), demo)

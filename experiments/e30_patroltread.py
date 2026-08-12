#!/usr/bin/env python3
"""e30 — The patrol's tread. NOCK's guards already step: g.stepped
plays the ARCHER's step voices at -16 dB, pitch 0.85, faded by the
guard-hear law (0.025 dB/px, 900 px cutoff). The gap is not
silence — it is IDENTITY. Guards borrow the player's feet: same
voice, overlapping levels, so in a heard-not-seen moment "whose
step was that?" is ambiguous, and NOCK's first law is legibility.

The candidate: the patrol gets its own GAIT — and the gait is a
LAYER, not a new family. tread(mat) = a boot-heel of pitch-drop
mass UNDER the floor's own shipped step voice, verbatim. The WHO
axis (weight) is spectral, so it survives any distance gain, which
a level cue never could; the WHERE axis (material) is inherited by
construction because the floor literally speaks its own word.
(Two invented answer families died against the shipped registers
first — metal's ring read dark, wood's knock read bright; the
lesson: don't re-invent what already ships and is under contract.)

Measured (archer references are the SHIPPED buffers, dumped from
src/sfx.gd via the render_all tool — set NOCK_VOICES to the dump
dir):
  - the WHO axis: per material, the tread's low-band (<250 Hz)
    energy fraction >= 2x the shipped archer step's, and its
    power-weighted centroid <= 0.6x — at EQUAL RMS, so the ruler
    reads body, never level.
  - the WHERE axis survives: ranking the four materials by
    centroid gives the SAME order in both gaits — the floor's
    identity is not erased by the boot.
  - the edge exists: dressed with the game's own law at the 900 px
    cutoff (-16 dB base - 22.5 dB fade), the tread's peak still
    clears nock's existence floor (0.005) — the warning is faint,
    but it is THERE.

Render: the who-contrast (archer stone step vs tread, equal level,
alternating), then a patrol pass: treads at NC.GUARD_STEP_PERIOD
(0.5 s) walking 900 px -> past you -> 900 px away under the
shipped gain law.

    python3 experiments/e30_patroltread.py [outdir]
"""

import os
import sys
import wave

import numpy as np
from scipy.signal import butter, sosfilt

_here = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(_here))
from loam import SR, stereo, write_wav
from loam.drums import kick

outdir = sys.argv[1] if len(sys.argv) > 1 else "render"
os.makedirs(outdir, exist_ok=True)
rng = np.random.default_rng(0xE30)

VOICES = os.environ.get(
    "NOCK_VOICES",
    "/tmp/claude-1000/-home-stinky-git/"
    "a1a8853d-ff63-484e-b803-5c4a9ef5db64/scratchpad/voices_after")

# nock's own numbers (nc.gd), quoted not invented
GUARD_STEP_PERIOD = 0.5
GUARD_HEAR_FALLOFF = 0.025   # dB/px
GUARD_HEAR_CUTOFF = 900.0    # px
TREAD_BASE_DB = -16.0        # the shipped guard-step play level
EXIST_FLOOR = 0.005          # nock's voice-existence contract

MATS = {0: "stone", 1: "wood", 2: "metal", 3: "carpet"}


def _burst(dur, lo, hi, decay, amp):
    n = int(dur * SR)
    sos = butter(2, [lo, hi], "bandpass", fs=SR, output="sos")
    return sosfilt(sos, rng.uniform(-1, 1, n)) \
        * np.exp(-np.arange(n) / SR * decay) * amp


def tread(ans):
    """A boot on nock's floor: a heel of pitch-drop mass UNDER the
    floor's own shipped voice, verbatim. The boot is a LAYER, not a
    new family — the WHERE word is untouched (two invented answer
    families died against the shipped registers before this: metal's
    ring read dark, wood's knock read bright; stop inventing what
    already ships). In-game this is ONE new synth plus the existing
    material system, its tuning already under contract."""
    heel = kick(0.16, f0=120.0, f1=48.0, drop=18.0, click=0.22,
                amp=0.55, seed=int(rng.integers(1 << 30)))
    n = max(int(0.30 * SR), int(0.012 * SR) + len(ans))
    out = np.zeros(n)
    out[:len(heel)] += heel
    i0 = int(0.012 * SR)   # the sole lands just after the heel
    out[i0:i0 + len(ans)] += np.asarray(ans, dtype=float) * 1.2
    return out


def load_voice(mat):
    p = os.path.join(VOICES, "voice_step_%d.wav" % mat)
    w = wave.open(p)
    d = np.frombuffer(w.readframes(w.getnframes()),
                      dtype=np.int16).astype(float) / 32768.0
    return d


def centroid(x):
    spec = np.abs(np.fft.rfft(np.asarray(x, dtype=float))) ** 2
    f = np.fft.rfftfreq(len(x), 1 / SR)
    return float((f * spec).sum() / max(spec.sum(), 1e-12))


def low_frac(x, corner=250.0):
    spec = np.abs(np.fft.rfft(np.asarray(x, dtype=float))) ** 2
    f = np.fft.rfftfreq(len(x), 1 / SR)
    return float(spec[f < corner].sum() / max(spec.sum(), 1e-12))


def eq_rms(x, ref=0.1):
    x = np.asarray(x, dtype=float)
    return x * ref / max(np.sqrt(np.mean(x ** 2)), 1e-12)


if __name__ == "__main__":
    archer = {m: load_voice(m) for m in MATS}
    treads = {m: tread(archer[m]) for m in MATS}

    print("== the WHO axis (equal RMS: body, never level) ==")
    ok = True
    for m, name in MATS.items():
        ta, aa = eq_rms(treads[m]), eq_rms(archer[m])
        lf_t, lf_a = low_frac(ta), low_frac(aa)
        c_t, c_a = centroid(ta), centroid(aa)
        good = lf_t >= 2.0 * lf_a and c_t <= 0.6 * c_a
        ok &= good
        print("  %-6s low-frac %.3f vs %.3f (x%.1f, want >= 2)   "
              "centroid %5.0f vs %5.0f (x%.2f, want <= 0.6)  %s"
              % (name, lf_t, lf_a, lf_t / max(lf_a, 1e-9),
                 c_t, c_a, c_t / max(c_a, 1e-9),
                 "YES" if good else "NO"))
    print("  " + ("YES" if ok else "NO"))

    print("== the WHERE axis survives the boot ==")
    # the floor answers THROUGH the boot, not after it (a window
    # ruler died here: stone's grit is spent by 50 ms, so the
    # post-heel window read its absence) — the heel's mass is a
    # BAND (<250 Hz), so rank the tread above 300 Hz, where only
    # the floor speaks; archer voices whole (they are all answer)
    sos_hi = butter(4, 300.0, "high", fs=SR, output="sos")
    rank_t = sorted(MATS,
                    key=lambda m: centroid(sosfilt(sos_hi, treads[m])))
    rank_a = sorted(MATS, key=lambda m: centroid(archer[m]))
    print("  tread order:  " + " < ".join(MATS[m] for m in rank_t))
    print("  archer order: " + " < ".join(MATS[m] for m in rank_a))
    print("  same order: " + ("YES" if rank_t == rank_a else "NO"))

    print("== the edge exists (the game's own dressing law) ==")
    edge_db = TREAD_BASE_DB - GUARD_HEAR_FALLOFF * GUARD_HEAR_CUTOFF
    g = 10.0 ** (edge_db / 20.0)
    pk = max(float(np.max(np.abs(treads[m]))) * g for m in MATS)
    print("  %.1f dB at cutoff -> loudest tread peak %.4f "
          "(floor %.3f): %s" % (edge_db, pk, EXIST_FLOOR,
                                "YES" if pk >= EXIST_FLOOR else "NO"))

    # exhibit 1: whose step? archer stone vs tread stone, equal level
    gap = np.zeros(int(0.45 * SR))
    a1 = []
    for _ in range(3):
        a1 += [eq_rms(archer[0], 0.15), gap, eq_rms(treads[0], 0.15),
               gap]
    who = np.concatenate(a1)
    # exhibit 2: the patrol passes on stone, shipped gain law
    dur = 12.0
    n = int(dur * SR)
    walk = np.zeros(n)
    t = 0.0
    while t < dur:
        d = abs(dur / 2.0 - t) / (dur / 2.0) * GUARD_HEAR_CUTOFF
        gdb = TREAD_BASE_DB - GUARD_HEAR_FALLOFF * d
        th = treads[0] * 10.0 ** (gdb / 20.0) * 2.5
        i0 = int(t * SR)
        m = min(len(th), n - i0)
        walk[i0:i0 + m] += th[:m]
        t += GUARD_STEP_PERIOD
    ex = np.concatenate([who, np.zeros(int(0.8 * SR)), walk])
    write_wav(os.path.join(outdir, "e30_patroltread.wav"),
              np.clip(stereo(ex, 0.0), -0.99, 0.99))
    print("wrote", outdir + "/e30_patroltread.wav")

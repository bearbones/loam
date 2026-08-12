#!/usr/bin/env python3
"""e29 — The ledger cadence. NOCK closes a night with the tally
screen: verdict lines and tick sounds, no music. But the game's law
is audio-as-information — so the candidate is a closing cadence
where THE VERDICT IS THE HARMONY. Two words, a MINIMAL PAIR: the
clean night and the stained night share every onset and every pitch
except the last. The clean cadence walks down and lands ON the
tonic (D, the motif's home); the stained cadence walks the same
steps and lands on E — a major 2nd over home, OUTSIDE the world's
D-minor pentatonic. One note of difference carries the whole
verdict; everything else about the night's close is identical.

Dressing reuses e23's sting dresses VERBATIM (gut+wood for flame,
glass+hum for lightning): the night's last word is spoken in the
same accents as its alarms — the register system stays one system.
Level sits at 0.5, under caught's 0.92: a close, not an alarm.

Measured:
  - the minimal pair is real: onset times identical within 8 ms
    across clean/stained in BOTH dresses (the rhythm carries zero
    verdict information — by measurement, not just intent)
  - the landing is true: every note within 15 cents of design
    (e23's narrow-band match-to-design ruler; HPS died twice in
    e23 and stays dead)
  - RESOLUTION IS MEASURABLE, not a pitch label: mix each final
    note with the world's tonic drone (D3+D4) and read the
    envelope's beating band (12-24 Hz — D3 vs E3 fundamentals
    beat at 18.0 Hz). The stained close must carry >= 3x the
    clean close's beating energy in each dress. Dissonance as an
    AM measurement.
  - a close, not an alarm: cadence RMS < caught-sting RMS per
    dress.

Render: one exhibit — flame clean, flame stained, lightning clean,
lightning stained, a breath apart.

    python3 experiments/e29_ledgercadence.py [outdir]
"""

import importlib.util
import os
import sys

import numpy as np
from scipy.signal import butter, sosfilt

_here = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(_here))
from loam import SR, hz, stereo, write_wav

_spec = importlib.util.spec_from_file_location(
    "e23", os.path.join(_here, "e23_stings.py"))
e23 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(e23)

outdir = sys.argv[1] if len(sys.argv) > 1 else "render"
os.makedirs(outdir, exist_ok=True)

TONIC_MIDI = 50        # D3 — the motif's home (e22's world)
CADENCE_LEVEL = 0.5    # a close, not an alarm (caught is 0.92)

# the words: same rhythm, same walk, one different landing
CADENCES = {
    "clean":   [(0.00, 57, 0.18), (0.20, 55, 0.18), (0.40, 53, 0.22),
                (0.66, 50, 1.10)],
    "stained": [(0.00, 57, 0.18), (0.20, 55, 0.18), (0.40, 53, 0.22),
                (0.66, 52, 1.10)],
}


def beating(final_seg):
    """The resolution ruler: mix the final note with the world's
    tonic drone at matched RMS and read the envelope's 12-24 Hz
    band — D3 vs E3 fundamentals beat at 18.0 Hz, D vs D barely at
    all. The mix is BANDPASSED to the fundamentals' neighborhood
    (120-190 Hz) first: a gut pluck's upper partials beat among
    themselves (the e27 lesson), and unfiltered they hand the clean
    cadence a false roughness floor. Returns 12-24 Hz env energy /
    total env energy."""
    n = len(final_seg)
    t = np.arange(n) / SR
    drone = np.sin(2 * np.pi * hz(TONIC_MIDI) * t)
    seg = np.asarray(final_seg, dtype=float)
    drone *= np.sqrt(np.mean(seg ** 2)) / np.sqrt(np.mean(drone ** 2))
    sos_bp = butter(2, [120.0, 190.0], "bandpass", fs=SR, output="sos")
    mix = sosfilt(sos_bp, seg + drone)
    env = np.abs(mix)
    sos = butter(2, 60.0, "low", fs=SR, output="sos")
    env = sosfilt(sos, env)
    env = env - env.mean()
    spec = np.abs(np.fft.rfft(env)) ** 2
    f = np.fft.rfftfreq(len(env), 1 / SR)
    band = (f >= 12.0) & (f <= 24.0)
    return float(spec[band].sum() / max(spec[f >= 1.0].sum(), 1e-12))


def rms(x):
    return float(np.sqrt(np.mean(np.asarray(x, dtype=float) ** 2)))


if __name__ == "__main__":
    dresses = {"flame": e23.dress_flame, "lightning": e23.dress_lightning}
    rendered = {}
    for dn, dress in dresses.items():
        for vn, word in CADENCES.items():
            rendered[(dn, vn)] = dress(word, CADENCE_LEVEL)

    print("== the minimal pair is real (rhythm carries no verdict) ==")
    # per-onset LOCAL windows (the e27 lesson: a global peak-picker
    # reads a gut pluck's partial-beating swell as an extra onset —
    # measure each attack at its own designed time)
    def local_onset(x, t0):
        # hysteresis crossing of the LOCAL max (e26's ruler, not a
        # derivative argmax — glass's soft attack smears the
        # derivative peak when only the pitch changes)
        k = int(0.008 * SR)
        env = np.convolve(np.abs(x), np.ones(k) / k, "same")
        a = max(int((t0 - 0.04) * SR), 0)
        b = int((t0 + 0.08) * SR)
        w = env[a:b]
        return (a + int(np.argmax(w > 0.35 * w.max()))) / SR

    ok = True
    for dn in dresses:
        d_ms = max(abs(local_onset(rendered[(dn, "clean")], t0)
                       - local_onset(rendered[(dn, "stained")], t0))
                   for (t0, _, _) in CADENCES["clean"]) * 1000.0
        ok &= d_ms <= 8.0
        print("  %-9s onset spread clean-vs-stained %.1f ms (want <= 8)"
              % (dn, d_ms))
    print("  " + ("YES" if ok else "NO"))

    print("== the landing is true (15-cent match-to-design) ==")
    worst = 0.0
    for (dn, vn), x in rendered.items():
        word = CADENCES[vn]
        for (t0, midi, d) in word:
            a = int((t0 + 0.03) * SR)
            seg = x[a:a + int(min(d, 0.25) * SR)]
            pk = e23.note_pitch(seg, hz(midi))
            worst = max(worst, abs(e23.cents(pk, hz(midi))))
    print("  worst note %.1f cents (want <= 15)" % worst)

    print("== resolution is measurable (beating vs the tonic) ==")
    for dn in dresses:
        b = {}
        for vn, word in CADENCES.items():
            t_final = word[-1][0]
            a = int((t_final + 0.10) * SR)
            seg = rendered[(dn, vn)][a:a + int(0.60 * SR)]
            b[vn] = beating(seg)
        print("  %-9s beating clean %.4f  stained %.4f  (x%.1f, "
              "want >= 3)" % (dn, b["clean"], b["stained"],
                              b["stained"] / max(b["clean"], 1e-12)))

    print("== a close, not an alarm ==")
    for dn, dress in dresses.items():
        caught = dress(e23.GESTURES["caught"], e23.LEVELS["caught"])
        rc = rms(rendered[(dn, "clean")])
        ra = rms(caught)
        print("  %-9s cadence rms %.4f < caught rms %.4f : %s"
              % (dn, rc, ra, "YES" if rc < ra else "NO"))

    gap = np.zeros(int(0.8 * SR))
    order = [("flame", "clean"), ("flame", "stained"),
             ("lightning", "clean"), ("lightning", "stained")]
    parts = []
    for key in order:
        parts += [rendered[key], gap]
    mono = np.concatenate(parts[:-1])
    exhibit = np.clip(stereo(mono * 0.9, 0.0), -0.99, 0.99)
    write_wav(os.path.join(outdir, "e29_ledgercadence.wav"), exhibit)
    print("wrote", outdir + "/e29_ledgercadence.wav")

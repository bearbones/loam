#!/usr/bin/env python3
"""loam smoke test — every module imported and exercised once.
Any exception = fail. Keep it under ~30s.

    python3 dev_smoke.py
"""

import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
t0 = time.time()
from loam import SR, hz, Loop, stereo, ad_env, seam_report
from loam.pads import padsynth_stereo, saw_amps, formant_amps, VOWELS
from loam.modal import strike, bow, gong, CHURCH_BELL, GLASS
from loam.strings import pluck, strum, sympathetic
from loam.winds import flute, ney
from loam.voice import sing
from loam.drums import (kick, snare, hat, clap, tom, conga, cowbell,
        rim, shaker)
from loam.analog import saw, pulse, supersaw, ladder
from loam.texture import rain, wind, fire, bubble, bubbles
from loam.space import (reverb_loop, reverb_tail, tape_echo_loop,
        ir_room, ir_tank, ir_bone, convolve_loop, convolve_tail)
from loam.spectral import freeze, stretch, cross_synth
from loam.shape import wavefold, chebyshev, bitcrush, tape_sat
from loam.mod import chorus, flanger, phaser
from loam.grain import cloud
from loam.shift import freq_shift, ring_mod, barber
from loam.dyn import compress, duck, transient, limiter
from loam.lofi import gramophone, worn_tape
from loam.rhythm import euclid, rotate, swing, scale_notes, quantize_to

L = Loop(2.0, 1)
checks = []


def ok(name, arr, allow_nan=False):
    good = np.all(np.isfinite(arr)) and np.abs(arr).max() < 4.0
    checks.append((name, bool(good)))
    if not good:
        print(f"  FAIL {name}: max={np.abs(arr).max()}")


ok("padsynth", padsynth_stereo(2.0, hz(50), saw_amps(8), seed=1))
ok("formants", np.array(formant_amps(hz(50), 12, VOWELS["ah"])))
ok("strike", strike(hz(57), 0.5, CHURCH_BELL))
ok("bow", bow(hz(69), 0.8, GLASS))
ok("gong", gong(62.0, 1.5, seed=1))
ok("pluck", pluck(hz(62), 0.5))
ok("strum", strum([50, 57, 62], 0.5))
ok("sympathetic", sympathetic(np.ones((SR, 2)) * 0.1, [62], loop=False))
ok("flute", flute(hz(62), 0.6, seed=1))
ok("ney", ney(hz(62), 0.6, seed=1))
ok("sing", sing([(62, 1, "ah")], bpm=120))
for f_ in (kick, snare, clap, tom, conga, cowbell, rim, shaker):
    ok(f_.__name__, f_())
ok("hat", hat())
ok("saw", saw(220.0, 0.3))
ok("pulse", pulse(220.0, 0.3))
ok("supersaw", supersaw(220.0, 0.3))
ok("ladder", ladder(saw(110.0, 0.3), 800.0, 0.7))
ok("rain", rain(1.5, seed=1))
ok("wind", wind(1.5, seed=1))
ok("fire", fire(1.5, seed=1))
ok("bubble", bubble(800.0))
ok("bubbles", bubbles(1.5, seed=1))
_zb = bubble(500.0)
_z = np.where(np.diff(np.signbit(_zb)))[0]
_fa = 1.0 / np.diff(_z[:3]).mean() * SR / 2
_fb = 1.0 / np.diff(_z[-3:]).mean() * SR / 2
checks.append(("bubble_chirp_rises", bool(_fb > _fa * 1.2)))
st = np.stack([pluck(hz(62), 1.0)] * 2, axis=1)
ok("reverb_loop", reverb_loop(st, t60=0.8))
ok("reverb_tail", reverb_tail(st, t60=0.8))
ok("tape_echo", tape_echo_loop(st, 1.0, 0.2))
ok("convolve_loop", convolve_loop(st, ir_room(0.5, seed=1)))
ok("convolve_tail", convolve_tail(st, ir_bone(0.4, seed=1)))
ok("ir_tank", ir_tank(0.5, seed=1))
ok("freeze", freeze(st[:, 0], 0.1, 1.0))
ok("stretch", stretch(st[:, 0], 2.0))
ok("cross_synth", cross_synth(st[:, 0], st[:, 0]))
ok("wavefold", wavefold(np.sin(np.linspace(0, 100, SR)), 2.0))
ok("chebyshev", chebyshev(np.sin(np.linspace(0, 100, SR)), [0, 0, 1]))
ok("bitcrush", bitcrush(st[:, 0]))
ok("tape_sat", tape_sat(st[:, 0]))
ok("chorus", chorus(st, 1.0))
ok("flanger", flanger(st, 1.0))
ok("phaser", phaser(st, 1.0))
ok("cloud", cloud(st[:, 0], 1.0, seed=1))
ok("freq_shift", freq_shift(st, 30.0, 1.0))
ok("ring_mod", ring_mod(st, 80.0))
ok("barber", barber(st, 1.0))
ok("compress", compress(st))
ok("duck", duck(st, np.abs(st[:, 0])))
ok("transient", transient(kick()))
ok("limiter", limiter(st * 2))
ok("gramophone", gramophone(st, seed=1))
ok("worn_tape", worn_tape(st, seed=1))
assert euclid(3, 8) == [1, 0, 0, 1, 0, 0, 1, 0]
assert sum(euclid(5, 16)) == 5
assert quantize_to(63.4, 62, "hijaz_kar") in scale_notes(50, "hijaz_kar", 3)
checks.append(("rhythm", True))

n_fail = sum(1 for _, g in checks if not g)
print(f"smoke: {len(checks)} checks, {n_fail} failures, "
      f"{time.time() - t0:.1f}s")
sys.exit(1 if n_fail else 0)

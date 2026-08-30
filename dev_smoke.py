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
from loam.modal import strike, bow, gong, CHURCH_BELL, GLASS, ANVIL
from loam.strings import pluck, strum, sympathetic
from loam.winds import flute, ney
from loam.voice import sing
from loam.drums import (kick, snare, hat, clap, tom, conga, cowbell,
        rim, shaker)
from loam.analog import saw, pulse, supersaw, ladder
from loam.texture import rain, wind, fire, bubble, bubbles, thunder
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
from loam.fdstring import fdpluck, fdpluck2, fdsym

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
ok("anvil", strike(195.0, 1.0, ANVIL, knock=0.3,
        rng=np.random.default_rng(1)))
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
ok("thunder", thunder(dist_km=3.0, dur=1.2, seed=1))
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

ok("fdpluck", fdpluck(110.0, 0.6, N=140))
ok("fdpluck_meend", fdpluck(np.linspace(110.0, 123.47, 100), 0.6,
        N=140))
ok("fdpluck2", fdpluck2(110.0, 0.6, N=140))
_sdrv = 0.3 * np.sin(2 * np.pi * 220.0 * np.arange(int(0.6 * SR))
        / SR)
_, _sb = fdsym([220.0, 233.1], _sdrv, N=60, buses=True)
_sr = [float(np.sqrt(np.mean(b ** 2))) for b in _sb]
checks.append(("fdsym", _sr[0] > 5.0 * _sr[1]))
_, _jb = fdsym([220.0], _sdrv, N=60, buses=True, jawari=True,
        gain=5000.0)


def _hb(x):
    _F = np.abs(np.fft.rfft(x)) ** 2
    _f = np.fft.rfftfreq(len(x), 1 / SR)
    return float(_F[_f > 1500.0].sum() / (_F.sum() + 1e-24))


checks.append(("fdsym_jawari", np.isfinite(_jb).all()
        and _hb(_jb[0]) > 3.0 * _hb(_sb[0])))

from loam.membrane import fddrum
from loam.ruler import mode_freqs, mode_misfit
_dr = fddrum(180.0, 0.5, N=29)
_dm = mode_freqs(_dr, k=8, fmin=100.0, fmax=600.0, rel=1e-3)
checks.append(("membrane",
        abs(_dm[1] / _dm[0] - 1.593) < 0.04))
_mm, _mf0, _mi = mode_misfit(
        np.array([100.0, 150.0, 200.0, 250.0]), 20.0, 105.0)
checks.append(("ruler_misfit",
        _mi == (2, 3, 4, 5) and _mm < 1.0))
from loam.ruler import partial_track
_gd = fddrum(np.linspace(180.0, 240.0, 50), 0.5, N=29)
_gt, _gf = partial_track(_gd, 120.0, 280.0)
checks.append(("membrane_glide",
        1.25 < _gf[-1] / _gf[0] < 1.42))

# ruler: self-check against signals with known answers
from loam.ruler import (hps_pitch, centroid_hz, band_density,
        pulse_rate, seam_rank, flatness, chroma, onset_times,
        transcribe, env_peak_s, dyad_pitches, triad_pitches,
        pitch_contour, dwell_seconds, ornament_profile,
        beat_profile, accent_profile)
_tt = np.arange(2 * SR) / SR
_sine = np.sin(2 * np.pi * 500.0 * _tt)
checks.append(("ruler_hps",
        abs(hps_pitch(pluck(hz(69), 1.0)) - 440.0) < 5.0))
checks.append(("ruler_centroid",
        abs(centroid_hz(_sine) - 500.0) < 25.0))
checks.append(("ruler_density", band_density(_sine, 400, 600)
        > 100 * band_density(_sine, 1000, 2000)))
_clicks = np.zeros(5 * SR)
_rngc = np.random.default_rng(9)
for _i in range(12):
    # offset from 0: an onset inside frame 0 has no prior frame to
    # rise from — spectral flux is blind to a strike at t=0
    _at = int((0.2 + _i / 3.0) * SR)
    _clicks[_at:_at + 200] = _rngc.standard_normal(200)
checks.append(("ruler_pulse",
        abs(pulse_rate(_clicks, 2.0, 4.5) - 3.0) < 0.15))
_qsine = np.sin(2 * np.pi * 500.0 * np.arange(SR) / SR)[:, None]
checks.append(("ruler_seam", seam_rank(_qsine) <= 0.999))
_nz = np.random.default_rng(4).standard_normal(2 * SR)
checks.append(("ruler_flat_noise", flatness(_nz) > 0.3))
checks.append(("ruler_flat_sine", flatness(_sine) < 0.02))
_a440 = np.sin(2 * np.pi * 440.0 * _tt)
checks.append(("ruler_chroma", int(np.argmax(chroma(_a440))) == 9))
checks.append(("ruler_onsets", len(onset_times(_clicks)) == 12))
_tb = np.arange(4 * SR) / SR
_bloom = np.sin(2 * np.pi * 110.0 * _tb) * np.exp(-_tb * 0.5) \
    + np.sin(2 * np.pi * 2500.0 * _tb) * np.exp(-((_tb - 0.8) / 0.35) ** 2)
checks.append(("ruler_env_peak", 0.6 <= env_peak_s(_bloom) <= 1.0))
_dy = [(50, 57), (60, 69), (55, 64)]      # inside the verified
_dyok = True                               # contract: >=43, no
for _a, _b in _dy:                         # shadow intervals
    _mix = pluck(hz(_a), 0.5, seed=1) + pluck(hz(_b), 0.5, seed=2)
    _lo, _hi = dyad_pitches(_mix)
    _dyok &= (int(round(69 + 12 * np.log2(_lo / 440.0))) == _a
            and int(round(69 + 12 * np.log2(_hi / 440.0))) == _b)
checks.append(("ruler_dyad", _dyok))
_tri = [(50, 3, 4), (48, 9, 7), (55, 3, 7)]  # certified shapes
_trok = True
for _a, _i1, _i2 in _tri:
    _mix = pluck(hz(_a), 0.5, seed=1) \
        + pluck(hz(_a + _i1), 0.5, seed=2) \
        + pluck(hz(_a + _i1 + _i2), 0.5, seed=3)
    _got = tuple(int(round(69 + 12 * np.log2(_f / 440.0)))
            for _f in triad_pitches(_mix))
    _trok &= _got == (_a, _a + _i1, _a + _i1 + _i2)
checks.append(("ruler_triad", _trok))
_ct, _cf = pitch_contour(np.sin(2 * np.pi * 220.0
        * np.arange(SR) / SR), fmin=100, fmax=800)
checks.append(("ruler_contour",
        bool(np.abs(1200 * np.log2(_cf / 220.0)).max() < 10.0)))
_dts = np.arange(0, 2.0, 0.05)
_dfs = np.where(_dts < 1.2, 220.0, 220.0 * 2 ** (7 / 12))
_dw = dwell_seconds(_dts, _dfs, 220.0)
checks.append(("ruler_dwell", int(np.argmax(_dw)) == 0
        and abs(_dw[0] - 1.2) < 0.11 and abs(_dw[7] - 0.8) < 0.11))
_bt = np.arange(6 * SR) / SR
_am = (1 + 0.3 * np.sin(2 * np.pi * 1.5 * _bt)) \
    * np.sin(2 * np.pi * 400.0 * _bt)
_br, _bd = beat_profile(_am, 300.0, 500.0)
checks.append(("ruler_beat",
        abs(_br - 1.5) < 0.2 and 1.7 < _bd < 3.3))
_ax = np.zeros(2 * SR)                 # every 4th click louder
_ats = np.arange(0, 1.9, 0.1)
for _i, _t in enumerate(_ats):
    _a = int(_t * SR)
    _ax[_a:_a + 300] = (1.0 if _i % 4 == 0 else 0.3) \
        * np.random.default_rng(_i).standard_normal(300)
_acc = accent_profile(_ax, _ats)
checks.append(("ruler_accent",
        float(np.median(_acc[::4]) / np.median(
                np.delete(_acc, np.arange(0, len(_ats), 4))))
        > 2.0))
_ots = np.arange(0, 2.0, 0.02)
_ofs = 200.0 * 2 ** (80.0 * np.sin(2 * np.pi * 5.0 * _ots) / 1200)
_rt, _dp = ornament_profile(_ots, _ofs)
checks.append(("ruler_ornament",
        abs(_rt - 5.0) < 0.2 and abs(_dp - 80.0) < 6.0))
_tune = [62, 65, 69, 74]
_ph = np.zeros(int(2.2 * SR))
for _i, _md in enumerate(_tune):
    _at = int((0.2 + 0.5 * _i) * SR)
    _pl = pluck(hz(_md), 0.45)
    _fd = int(0.08 * SR)                 # a truncated pluck's hard
    _pl[-_fd:] *= np.linspace(1, 0, _fd)  # stop reads as an onset
    _ph[_at:_at + len(_pl)] += _pl
_got = [int(round(md)) for _, md in transcribe(_ph, min_sep=0.2)]
checks.append(("ruler_transcribe", _got == _tune))

n_fail = sum(1 for _, g in checks if not g)
print(f"smoke: {len(checks)} checks, {n_fail} failures, "
      f"{time.time() - t0:.1f}s")
sys.exit(1 if n_fail else 0)

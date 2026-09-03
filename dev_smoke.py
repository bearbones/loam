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
# e80 mizrab click contract, by SUBTRACTION (the fusion is
# additive, so clicked - bare IS the click): click=0 bit-equal
# legacy; the difference peaks at exactly click*amp*0.9, lives
# only in an 8 ms window starting at the string's own speak
# time, and the low band (the string's tone) is untouched.
from scipy.signal import butter, sosfilt
from loam.ruler import speak_time
_p0 = fdpluck2(146.8, 0.8, N=140)
_pc = fdpluck2(146.8, 0.8, N=140, click=0.3)
_d = _pc - _p0
_nz = np.nonzero(_d)[0]
_sosl = butter(4, 2000.0, btype="lowpass", fs=SR, output="sos")


def _rdb(a, b):
    return 20.0 * np.log10((np.sqrt(np.mean(a ** 2)) + 1e-30)
            / (np.sqrt(np.mean(b ** 2)) + 1e-30))


checks.append(("fdpluck2_click",
        np.array_equal(_p0, fdpluck2(146.8, 0.8, N=140, click=0.0))
        and abs(np.max(np.abs(_d)) - 0.3 * 0.9) <= 1e-9
        and abs(_nz[0] / SR - speak_time(_p0)) <= 0.003
        and (_nz[-1] - _nz[0]) <= int(0.008 * SR)
        and abs(_rdb(sosfilt(_sosl, _pc),
                sosfilt(_sosl, _p0))) <= 0.5))
# e81 shamisen: sawari lifts HF (the ridge buzz), the don lives
# in the head-mode band, pitch holds, honchoshi is 1 : 4/3 : 2
from loam.nihon import shamisen, honchoshi
from loam.ruler import hps_pitch as _shp
_sh1 = shamisen(155.6, 0.9, sawari=1.0, snap=0.0, thump=0.0)
_sh0 = shamisen(155.6, 0.9, sawari=0.0, snap=0.0, thump=0.0)
_soshi = butter(4, 2000.0, btype="highpass", fs=SR, output="sos")
_sht = shamisen(311.1, 0.9, thump=0.5, snap=0.0)
_shn = shamisen(311.1, 0.9, thump=0.0, snap=0.0)
_sosd = butter(4, [150.0, 250.0], btype="bandpass", fs=SR,
        output="sos")
_shf = _shp(_sh0[int(0.05 * SR):int(0.6 * SR)],
        fmin=80.0, fmax=400.0)
_hc = honchoshi(100.0)
checks.append(("nihon_shamisen",
        _rdb(sosfilt(_soshi, _sh1), sosfilt(_soshi, _sh0)) >= 5.0
        and _rdb(sosfilt(_sosd, _sht[:int(0.1 * SR)]),
                sosfilt(_sosd, _shn[:int(0.1 * SR)])) >= 10.0
        and abs(1200.0 * np.log2(_shf / 155.6)) <= 25.0
        and abs(_hc[1] / _hc[0] - 4.0 / 3.0) < 1e-9
        and abs(_hc[2] / _hc[0] - 2.0) < 1e-9))
# e82 ruler.if_pitch: reads a known off-pitch tone through noise
# (spectral-peak detectors scatter +-100c on breathy signals)
from loam.ruler import if_pitch as _ifp
_ift = np.arange(int(0.5 * SR)) / SR
_ifr = np.random.default_rng(9)
_ifx = (np.sin(2 * np.pi * 330.0 * 2.0 ** (25.0 / 1200.0) * _ift)
        + 0.5 * _ifr.standard_normal(len(_ift)))
_ifc = 1200.0 * np.log2(np.median(
        _ifp(_ifx, 330.0)[int(0.05 * SR):-int(0.05 * SR)]) / 330.0)
checks.append(("ruler_if_pitch", abs(_ifc - 25.0) <= 5.0))
# e82 shakuhachi: deterministic per seed; sustain centers on f0;
# the meri scoop is a real early-pitch drop vs the scoopless twin
# (twin delta on the strongest early FFT line — no median names
# "the" pitch of a two-line breathy attack); muraiki is a real
# gust in the hiss band
from loam.nihon import shakuhachi


def _sk_early(v, f0):
    seg = v[int(0.05 * SR):int(0.30 * SR)]
    n4 = 8 * len(seg)
    sp = np.abs(np.fft.rfft(seg * np.hanning(len(seg)), n4))
    fq = np.fft.rfftfreq(n4, 1.0 / SR)
    sel = np.where((fq > f0 * 0.80) & (fq < f0 * 1.15))[0]
    return 1200.0 * np.log2(
            fq[sel[int(np.argmax(sp[sel]))]] / f0)


_skf = 293.66
_ska = shakuhachi(_skf, 1.2, muraiki=0.9, scoop=60.0, seed=3)
_skb = shakuhachi(_skf, 1.2, muraiki=0.9, scoop=0.0, seed=3)
_skc = shakuhachi(_skf, 1.2, muraiki=0.0, scoop=0.0, seed=3)
_sosk = butter(4, [1500.0, 6500.0], btype="bandpass", fs=SR,
        output="sos")


def _sk_gust(v):
    # WITHIN-note attack-vs-sustain contrast in the hiss band:
    # cross-note level comparison lies (each note is peak-
    # normalized, and the tone's own harmonics live up there)
    h = sosfilt(_sosk, v)
    return _rdb(h[:int(0.25 * SR)], h[int(0.6 * SR):int(0.9 * SR)])


_skcen = 1200.0 * np.log2(np.median(
        _ifp(_skc, _skf)[int(0.5 * SR):int(0.9 * SR)]) / _skf)
checks.append(("nihon_shakuhachi",
        np.array_equal(_ska,
            shakuhachi(_skf, 1.2, muraiki=0.9, scoop=60.0, seed=3))
        and abs(_skcen) <= 20.0
        and (_sk_early(_ska, _skf) - _sk_early(_skb, _skf)) <= -21.0
        and _sk_gust(_skb) - _sk_gust(_skc) >= 6.0))
# e89 komibuki: the pulsed breath flickers the envelope at the
# written rate (measurement-differenced vs a still-breath twin;
# waveform twin-delta is a clock delta and floods — see e89)
_skk = shakuhachi(_skf, 3.0, muraiki=0.3, scoop=0.0,
        komibuki=0.5, komi_hz=6.0, seed=4)
_skq = shakuhachi(_skf, 3.0, muraiki=0.3, scoop=0.0,
        komibuki=0.0, seed=4)


def _sk_kline(v):
    e = np.abs(v)
    kk = int(0.02 * SR)
    e = np.convolve(e, np.ones(kk) / kk, mode="same")
    e = e[int(0.9 * SR):int(2.65 * SR)]
    e = e / e.mean() - 1.0
    S = np.abs(np.fft.rfft(e * np.hanning(len(e))))
    fq = np.fft.rfftfreq(len(e), 1.0 / SR)
    return S[np.argmin(np.abs(fq - 6.0))]


# back-compat: komibuki=0 must be bit-identical to the
# pre-komibuki instrument
checks.append(("nihon_komibuki",
        np.array_equal(_skq, shakuhachi(_skf, 3.0,
                muraiki=0.3, scoop=0.0, seed=4))
        and 20.0 * np.log10(_sk_kline(_skk)
                / (_sk_kline(_skq) + 1e-12)) >= 15.0))
# e84 reedpipe + hichiriki: the valve on the quarter-wave bore is
# odd-dominant (cylindrical signature); deterministic; on pitch.
# hichiriki restores even partials (reed asymmetry) and pours the
# embai glide (twin delta, e82's ruler)
from loam.winds import reedpipe
from loam.nihon import hichiriki


def _oe_db(v, f0):
    seg = v[int(0.4 * SR):int(1.0 * SR)]
    n4 = 4 * len(seg)
    sp = np.abs(np.fft.rfft(seg * np.hanning(len(seg)), n4)) ** 2
    fq = np.fft.rfftfreq(n4, 1.0 / SR)

    def he(h):
        sel = (fq > f0 * h * 0.94) & (fq < f0 * h * 1.06)
        return sp[sel].max() if sel.any() else 1e-30
    return 10.0 * np.log10((he(1) + he(3) + he(5))
                           / (he(2) + he(4) + he(6)))


_rpf = 440.0
_rp = reedpipe(_rpf, 1.1, seed=5)
_rpc = 1200.0 * np.log2(_shp(_rp[int(0.3 * SR):],
        fmin=200.0, fmax=900.0) / _rpf)
checks.append(("reedpipe",
        np.array_equal(_rp, reedpipe(_rpf, 1.1, seed=5))
        and abs(_rpc) <= 15.0
        and _oe_db(_rp, _rpf) >= 15.0))
_hi = hichiriki(_rpf, 1.1, embai=120.0, seed=5)
_hi0 = hichiriki(_rpf, 1.1, embai=0.0, seed=5)
checks.append(("nihon_hichiriki",
        (_sk_early(_hi, _rpf) - _sk_early(_hi0, _rpf)) <= -38.0
        and _oe_db(_hi0, _rpf) <= _oe_db(_rp, _rpf) - 10.0))
# e85 sho: deterministic; the breath arch swells >=10 dB over its
# fixed-time edges; every written aitake pipe is a line and an
# out-of-collection probe (C5) is not
from loam.nihon import sho, AITAKE
_sv = sho(AITAKE["otsu"], 3.0, seed=4)
_svm = _sv.mean(axis=1)
_arch = 20.0 * np.log10(
        (np.sqrt(np.mean(_svm[int(1.2 * SR):int(1.8 * SR)] ** 2))
         + 1e-30)
        / (np.sqrt(np.mean(_svm[:int(0.3 * SR)] ** 2)) + 1e-30))
_seg = _svm[int(1.0 * SR):int(2.0 * SR)]
_sn4 = 4 * len(_seg)
_ssp = np.abs(np.fft.rfft(_seg * np.hanning(len(_seg)), _sn4))
_sfq = np.fft.rfftfreq(_sn4, 1.0 / SR)


def _sline(m):
    f0 = 440.0 * 2.0 ** ((m - 69) / 12.0)
    sel = (_sfq > f0 * 0.985) & (_sfq < f0 * 1.015)
    return 20.0 * np.log10(_ssp[sel].max() + 1e-30)


checks.append(("nihon_sho",
        np.array_equal(_sv, sho(AITAKE["otsu"], 3.0, seed=4))
        and _arch >= 10.0
        and min(_sline(m) for m in AITAKE["otsu"])
            >= _sline(72) + 12.0))
# e86 ryuteki: deterministic; the register flip lands fukura on f0
# and seme on the octave; the finger strike notches the envelope
from loam.nihon import ryuteki
from loam.ruler import if_pitch as _rif
_ry = ryuteki(440.0, 2.0, flip_at=1.2, graces=(0.5,), seed=2)
_ryl = 1200.0 * np.log2(np.median(_rif(_ry, 440.0)[
        int(0.25 * SR):int(1.05 * SR)]) / 440.0)
_ryh = 1200.0 * np.log2(np.median(_rif(_ry, 880.0)[
        int(1.35 * SR):int(1.8 * SR)]) / 880.0)
_rke = np.convolve(np.abs(_ry), np.ones(int(0.01 * SR))
        / int(0.01 * SR), mode="same")
_rdb = 20.0 * np.log10(_rke + 1e-12)
_rnotch = np.median(_rdb[int(0.25 * SR):int(0.75 * SR)]) \
    - _rdb[int(0.46 * SR):int(0.54 * SR)].min()
checks.append(("nihon_ryuteki",
        np.array_equal(_ry, ryuteki(440.0, 2.0, flip_at=1.2,
            graces=(0.5,), seed=2))
        and abs(_ryl) <= 35.0 and abs(_ryh) <= 35.0
        and _rnotch >= 4.0))
# e90 koto: deterministic; centers; the oshide bend is claimable
# DIRECTLY on the IF track (plucked SNR, unlike the winds); the
# paulownia body boosts its band vs a bodyless twin (zero-phase
# add — causal filters cancel instead)
from loam.nihon import koto
_ko = koto(220.0, 1.8)
_kob = koto(220.0, 1.8, bend_c=150.0, bend_at=0.35)
_koc = 1200.0 * np.log2(np.median(
        _ifp(_ko, 220.0)[int(0.25 * SR):int(1.0 * SR)]) / 220.0)
_kib = _ifp(_kob, 220.0, band=(0.93, 1.075 * 2 ** (150 / 1200)))
_kod = 1200.0 * np.log2(
        np.median(_kib[int(0.70 * SR):int(1.30 * SR)])
        / np.median(_kib[int(0.15 * SR):int(0.31 * SR)]))
_sokb = butter(2, [190.0, 270.0], btype="bandpass", fs=SR,
        output="sos")


def _kbrms(v):
    return float(np.sqrt(np.mean(sosfilt(_sokb, v) ** 2)))


checks.append(("nihon_koto",
        np.array_equal(_ko, koto(220.0, 1.8))
        and abs(_koc) <= 10.0
        and abs(_kod - 150.0) <= 15.0
        and 20.0 * np.log10(_kbrms(_ko)
                / _kbrms(koto(220.0, 1.8, body=0.0))) >= 3.0))
# e92 suikinkutsu: deterministic pot + drop; the IR's modes sit
# where written (merge: each mode is a detuned-channel cluster);
# the drop's bubble rises
from loam.nihon import suikinkutsu_ir, waterdrop, SUIKIN_MODES
from loam.ruler import mode_freqs as _smf
_sir = suikinkutsu_ir()
_smod = _smf(_sir.mean(axis=1), k=6, fmin=280.0, fmax=2600.0,
        rel=0.001, merge=0.02)
_sworst = max(abs(1200.0 * np.log2(
        _smod[np.argmin(np.abs(np.log(_smod / f)))] / f))
        for f, a, t in SUIKIN_MODES)
_swd = waterdrop(1500.0)
_sph = np.unwrap(np.angle(__import__("scipy.signal",
        fromlist=["hilbert"]).hilbert(_swd[:int(0.006 * SR)])))
_sif = np.diff(_sph) * SR / (2 * np.pi)
checks.append(("suikinkutsu",
        np.array_equal(_sir, suikinkutsu_ir())
        and np.array_equal(_swd, waterdrop(1500.0))
        and _sworst <= 25.0
        and np.median(_sif[-40:]) > np.median(_sif[40:80])))
# e87 gagaku percussion: deterministic voices, each keeping to its
# register (taiko low, kakko mid, shoko bright)
from loam.nihon import shoko, kakko, taiko
from loam.ruler import centroid_hz as _cen
checks.append(("nihon_gagaku_perc",
        np.array_equal(shoko(), shoko())
        and np.array_equal(taiko(), taiko())
        and _cen(taiko()) < 300.0
        and 300.0 < _cen(kakko()) < 1500.0
        and _cen(shoko()) > 1200.0
        and np.isfinite(taiko(small=True)).all()))
# e88 caustics: deterministic, silent at zero intensity, and the
# glint density flickers at the written ripple rate
from loam.texture import caustics
_ca = caustics(6.0, ripple_hz=1.5, intensity=1.0, seed=3)
_ce = np.abs(_ca.mean(axis=1))
_ck = int(0.03 * SR)
_ce = np.convolve(_ce, np.ones(_ck) / _ck, mode="same")
_ce -= _ce.mean()
_cs = np.abs(np.fft.rfft(_ce * np.hanning(len(_ce))))
_cf = np.fft.rfftfreq(len(_ce), 1.0 / SR)
_cm = (_cf >= 0.5) & (_cf <= 4.0)
checks.append(("caustics",
        np.array_equal(_ca, caustics(6.0, ripple_hz=1.5,
                intensity=1.0, seed=3))
        and float(np.abs(caustics(6.0, ripple_hz=1.5,
                intensity=0.0, seed=3)).max()) == 0.0
        and abs(float(_cf[_cm][np.argmax(_cs[_cm])]) - 1.5) < 0.2))
# e93 line_env: heterodyne single-line envelope stays flat when
# an equal-amp neighbor 100 c away switches on (the old bandpass
# skirts rejected that neighbor by only ~3 dB), and wrap=True
# holds level at the loop ends instead of notching
from loam.ruler import line_env as _lev
_lt = np.arange(int(4.0 * SR)) / SR
_lx = np.sin(2 * np.pi * 1000.0 * _lt)
_lnb = np.sin(2 * np.pi * 1000.0 * 2 ** (100 / 1200) * _lt)
_lnb[:int(2.0 * SR)] = 0.0
_le = _lev(_lx + _lnb, 1000.0, wrap=True)
_li = _le[int(0.3 * SR):int(3.7 * SR)]
checks.append(("line_env",
        abs(float(np.median(_li)) - 1.0) <= 0.02
        and float(_li.min()) >= 0.95
        and float(_le.min()) >= 0.90))
_sdrv = 0.3 * np.sin(2 * np.pi * 220.0 * np.arange(int(0.6 * SR))
        / SR)
_, _sb = fdsym([220.0, 233.1], _sdrv, N=60, buses=True)
_sr = [float(np.sqrt(np.mean(b ** 2))) for b in _sb]
checks.append(("fdsym", _sr[0] > 5.0 * _sr[1]))
from loam.fdstring import fdbow
_bw = fdbow(200.0, 0.7, FB=1e3, vb=0.10)
from loam.ruler import hps_pitch as _hp
_bp = _hp(_bw[int(0.3 * SR):], fmin=80.0, fmax=800.0)
_ble = (np.sqrt(np.mean(_bw[int(0.5 * SR):int(0.65 * SR)] ** 2))
        / np.sqrt(np.mean(_bw[int(0.2 * SR):int(0.35 * SR)] ** 2)))
checks.append(("fdbow", abs(1200 * np.log2(_bp / 200.0)) < 30.0
        and _ble > 0.7))
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
        beat_profile, accent_profile, decay_t60)
_tt = np.arange(2 * SR) / SR
_sine = np.sin(2 * np.pi * 500.0 * _tt)
_dec = np.sin(2 * np.pi * 150.0 * _tt) * 10.0 ** (-3.0 * _tt / 0.3)
_t60 = decay_t60(_dec, 135.0, 165.0)
checks.append(("ruler_t60", abs(_t60 - 0.3) < 0.045))
_dec2 = np.sin(2 * np.pi * 150.0 * _tt) * 10.0 ** (-3.0 * _tt / 0.06)
_t62 = decay_t60(_dec2, 135.0, 165.0, win_s=0.02, hop_s=0.003)
checks.append(("ruler_t60_fast", abs(_t62 - 0.06) < 0.021))
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
from loam.ruler import chroma_uniform, sympathy_forecast
_cu = chroma_uniform(_a440)
checks.append(("ruler_chroma_uniform", int(np.argmax(_cu)) == 9
        and abs(float(_cu.sum()) - 1.0) < 1e-6))
_sf = sympathy_forecast(np.full(100, 100.0), 0.01,
        [100.0, 150.0, 137.0])
checks.append(("ruler_sympathy", _sf[0] > _sf[1] > 0.0
        and _sf[2] == 0.0))   # unison > fifth (3:2 lattice) > inharmonic
_sfc = sympathy_forecast(np.full(100, 100.0), 0.01,
        [100.0, 150.0, 137.0], integrate=True, cascade=10.0)
_sfi = sympathy_forecast(np.full(100, 100.0), 0.01,
        [100.0, 150.0, 137.0], integrate=True)
checks.append(("ruler_sympathy_cascade",
        _sfc[1] / _sfc[0] > _sfi[1] / _sfi[0]
        and _sfc[2] == 0.0))  # bridge coupling lifts the fifth
_sfv = sympathy_forecast(np.full(100, 100.0), 0.01,
        [100.0, 150.0, 137.0], integrate=True,
        node=0.93, tap=0.12, vel=True)
checks.append(("ruler_sympathy_v2", np.isfinite(_sfv).all()
        and _sfv[0] > 0.0 and _sfv[2] == 0.0))
# v3 comp: huge K = identity times scale (ranks untouched);
# deep saturation taxes the LOW string (displacement variable)
_sf3i = sympathy_forecast(np.full(100, 100.0), 0.01,
        [100.0, 150.0], integrate=True, node=0.93, tap=0.12,
        vel=True, comp=(1.0, 1e9, 7.0, 0.1))
_sf3 = sympathy_forecast(np.full(100, 100.0), 0.01,
        [100.0, 150.0], integrate=True, node=0.93, tap=0.12,
        vel=True, comp=(1e3, 0.7, 7.0, 0.1))
checks.append(("ruler_sympathy_v3",
        abs(_sf3i[0] / _sf3i[1] - _sfv[0] / _sfv[1]) < 1e-9
        and np.isfinite(_sf3).all()
        and _sf3[0] / _sf3[1] < _sf3i[0] / _sf3i[1]))
from loam.ruler import lock_ratio
_tl = np.arange(SR) / SR
_lk = np.sin(2 * np.pi * 100.0 * _tl) \
    + 0.8 * np.sin(2 * np.pi * 200.0 * _tl) \
    + 0.5 * np.sin(2 * np.pi * 300.0 * _tl)
_oc = np.sin(2 * np.pi * 200.0 * _tl) \
    + 0.5 * np.sin(2 * np.pi * 400.0 * _tl)
checks.append(("ruler_lock_ratio", lock_ratio(_lk, 100.0) > 0.5
        and lock_ratio(_oc, 100.0) < 0.05))
from loam.ruler import fund_presence
checks.append(("ruler_fund_presence",
        fund_presence(_lk, 100.0) > 0.5
        and fund_presence(_oc, 100.0) < 0.05))
from loam.ruler import partial_freq
_tp5 = np.arange(5 * SR) / SR
_pf = np.sin(2 * np.pi * 440.3 * _tp5) \
    + 0.3 * np.sin(2 * np.pi * 452.0 * _tp5)
checks.append(("ruler_partial_freq",
        abs(partial_freq(_pf, 400.0, 480.0) - 440.3) < 0.05
        and abs(partial_freq(_pf, 445.0, 480.0) - 452.0) < 0.05))
_rng = np.random.default_rng(7)
_noise = _rng.standard_normal(SR)
checks.append(("ruler_partial_freq_clamped",
        430.0 <= partial_freq(_noise, 434.0, 447.0) <= 451.0))
from loam.ruler import beat_profile
_tb2 = np.arange(int(0.5 * SR)) / SR
_bt = np.sin(2 * np.pi * 440.0 * _tb2) \
    * (1.0 + 0.5 * np.sin(2 * np.pi * 3.0 * _tb2))
_rb, _db = beat_profile(_bt, 400.0, 480.0, trend_s=1.5,
        min_rate=0.5)
checks.append(("ruler_beat_short_window",
        np.isfinite(_rb) and _db > 1.0))
checks.append(("ruler_onsets", len(onset_times(_clicks)) == 12))
from loam.ruler import flux_spectrum
_tf8 = np.zeros(4 * SR)                   # 8 Hz click train: the
for _i in range(32):                      # rate line where event
    _a = int(_i * SR / 8.0)               # counting would also
    _tf8[_a:_a + 200] = np.random.default_rng(
            _i).standard_normal(200) * np.hanning(200)
_ffr, _fsp = flux_spectrum(_tf8)
_fm = (_ffr > 5.0) & (_ffr < 12.0)
_fpk = _ffr[_fm][int(np.argmax(_fsp[_fm]))]
checks.append(("ruler_flux_spectrum", abs(_fpk - 8.0) < 0.16))
from loam.ruler import flux_series
_fl, _fdt = flux_series(_tf8)             # periodic train: flux
_lag = int(round(0.125 / _fdt))           # correlates with its
_fa = _fl[:len(_fl) - _lag] - _fl[:len(_fl) - _lag].mean()
_fb = _fl[_lag:] - _fl[_lag:].mean()
_fr_ = float(np.dot(_fa, _fb) / (np.linalg.norm(_fa)
        * np.linalg.norm(_fb) + 1e-12))   # own-period shift
checks.append(("ruler_flux_series",
        abs(_fdt - 256.0 / SR) < 1e-9 and _fr_ > 0.7))
from loam.ruler import flux_line
_fq, _fp = flux_line(_tf8, 7.0, 9.0)      # the 8 Hz train stands
_nz = np.random.default_rng(7).standard_normal(
        4 * SR) * 0.1                     # tall over the median;
_nq, _np_ = flux_line(_nz, 7.0, 9.0)      # bare noise does not
checks.append(("ruler_flux_line",
        abs(_fq - 8.0) < 0.16 and _fp > 10.0 and _np_ < 4.0))
from loam.ruler import speak_time
_ts = np.arange(int(0.5 * SR)) / SR       # fast pluck vs slow
_fastv = np.sin(2 * np.pi * 200.0 * _ts) \
    * np.minimum(_ts / 0.004, 1.0) * np.exp(-_ts * 3.0)
_swell = np.sin(2 * np.pi * 200.0 * _ts) \
    * np.sin(np.pi * np.minimum(_ts / 0.12, 1.0) / 2) ** 2 \
    * np.exp(-_ts * 2.0)                  # steepest rise of the
_stf = speak_time(_fastv)                 # sin^2 bloom is at its
_sts = speak_time(_swell)                 # inflection, ~60 ms in
checks.append(("ruler_speak_time",
        _stf <= 0.012 and 0.03 <= _sts <= 0.10
        and speak_time(np.concatenate([np.zeros(2205),
            _fastv])) >= 0.045))
from loam.ruler import rate_contour
_tg = np.linspace(0.0, 4.0, 80001)       # linear 6->10 Hz chirp
_ph = 6.0 * _tg + 0.5 * _tg ** 2         # of clicks: the contour
_tc = np.interp(np.arange(int(_ph[-1])), _ph, _tg)
_xc = np.zeros(4 * SR)
for _i, _t in enumerate(_tc):
    _a = int(_t * SR)
    _xc[_a:_a + 200] += np.random.default_rng(
            _i).standard_normal(200) * np.hanning(200)
_rt, _rr = rate_contour(_xc, 4.0, 14.0)
_rw = 6.0 + _rt                          # must track the ramp
checks.append(("ruler_rate_contour",
        float(np.median(np.abs(_rr / _rw - 1))) < 0.03))
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

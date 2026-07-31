#!/usr/bin/env python3
"""MARROW — "Reel Home" (session 129): downtempo groove loop, 48 bars
at 90 BPM = 128s seamless. Director brief: Hayling / FC Kahuna energy,
phat beats, melody here and there, keep the stereo play.

    python3 dev/music/reel_home.py [out.wav]

Shape (8-bar sections, DJ-loopable — the end IS the intro):
  bars  0-8   pads + motif, no drums (the reel down)
  bars  8-16  kick+hats land; bass at 12
  bars 16-32  full groove, lead melody phrases A and B
  bars 32-40  lift: open hats, motif varies, melody up an octave
  bars 40-48  breakdown — drums thin out, pads swell, wrap to 0

Same loop-craft as The Bore: continuous oscillators quantized to
whole cycles per loop, IIR filters warmed with their own tail, every
event tail added with wraparound. Deterministic (seeded).
"""

import sys
import numpy as np
from scipy.signal import butter, sosfilt

SR = 44100
BPM = 90.0
SPB = 60.0 / BPM          # seconds per beat
BARS = 48
LOOP_S = BARS * 4 * SPB   # 128.0
N = int(round(SR * LOOP_S))
RNG = np.random.default_rng(0x5EE1)
SWING = 0.14              # +14% of an 8th on the off-8ths

out = np.zeros((N, 2), dtype=np.float64)
t_full = np.arange(N) / SR


def hz(midi: float) -> float:
    return 440.0 * 2.0 ** ((midi - 69) / 12.0)


def q(f: float) -> float:
    """Whole cycles per loop — continuous tones must close the seam."""
    return round(f * LOOP_S) / LOOP_S


def sosfilt_circular(sos, x: np.ndarray) -> np.ndarray:
    warm = SR
    y = sosfilt(sos, np.vstack([x[-warm:], x]), axis=0)
    return y[warm:]


def add_wrapped(buf: np.ndarray, start_s: float, chunk: np.ndarray) -> None:
    idx = (int(start_s * SR) + np.arange(len(chunk))) % N
    np.add.at(buf, idx, chunk)


def beat_t(bar: float, beat: float = 0.0, swing8: bool = False) -> float:
    """Absolute seconds of a grid point; swing8 shifts an off-8th late."""
    t = (bar * 4.0 + beat) * SPB
    if swing8:
        t += SWING * SPB * 0.5
    return t


def stereo(mono: np.ndarray, pan: float) -> np.ndarray:
    """Equal-power pan, pan in [-1, 1]."""
    a = (pan + 1.0) * np.pi / 4.0
    return np.stack([mono * np.cos(a), mono * np.sin(a)], axis=1)


# ---------------- drums ----------------------------------------------
def kick(amp: float = 1.0) -> np.ndarray:
    n = int(0.40 * SR)
    tt = np.arange(n) / SR
    freq = 52.0 * np.exp(-tt * 9.0) + 36.0
    ph = 2 * np.pi * np.cumsum(freq) / SR
    body = np.sin(ph) * np.exp(-tt * 7.5)
    click = RNG.standard_normal(int(0.004 * SR)) * 0.4
    body[: len(click)] += click * np.linspace(1, 0, len(click))
    mono = np.tanh(body * 2.2) * 0.52 * amp
    return np.stack([mono, mono], axis=1)


def snare(amp: float = 1.0) -> np.ndarray:
    n = int(0.22 * SR)
    tt = np.arange(n) / SR
    body = np.sin(2 * np.pi * 176.0 * tt) * np.exp(-tt * 26.0) * 0.5
    nz = RNG.standard_normal(n)
    sos = butter(2, [1500, 5200], btype="band", fs=SR, output="sos")
    crack = sosfilt(sos, nz) * np.exp(-tt * 20.0)
    # Clap ghost: two extra noise starts, 11ms apart.
    for d in (0.011, 0.022):
        k = int(d * SR)
        crack[k:] += sosfilt(sos, RNG.standard_normal(n - k)) \
            * np.exp(-tt[: n - k] * 24.0) * 0.5
    mono = (body + crack * 0.62) * 0.34 * amp
    return np.stack([mono * 1.0, mono * 0.92], axis=1)


def hat(open_: bool = False, amp: float = 1.0, pan: float = 0.3) -> np.ndarray:
    dur = 0.26 if open_ else 0.045
    n = int(dur * SR)
    tt = np.arange(n) / SR
    nz = RNG.standard_normal(n)
    sos = butter(2, [6200, 12500], btype="band", fs=SR, output="sos")
    mono = sosfilt(sos, nz) * np.exp(-tt * (14.0 if open_ else 70.0))
    return stereo(mono * 0.16 * amp, pan)


# ---------------- tonal voices ---------------------------------------
def pluck(f: float, dur: float, amp: float, tone: float = 1.0) -> np.ndarray:
    """FM marimba-ish pluck — the Hayling motif voice."""
    n = int(dur * SR)
    tt = np.arange(n) / SR
    mod = np.sin(2 * np.pi * f * 4.0 * tt) * 1.8 * tone * np.exp(-tt * 9.0)
    mono = np.sin(2 * np.pi * f * tt + mod)
    mono += 0.4 * np.sin(2 * np.pi * f * 2.0 * tt) * np.exp(-tt * 6.0)
    env = np.exp(-tt * 5.5)
    env[: int(0.003 * SR)] *= np.linspace(0, 1, int(0.003 * SR))
    return mono * env * amp


def lead(f: float, dur: float, amp: float) -> np.ndarray:
    """Soft triangle-ish lead with late vibrato."""
    n = int(dur * SR)
    tt = np.arange(n) / SR
    vib = 1.0 + 0.006 * np.sin(2 * np.pi * 5.2 * tt) \
        * np.clip((tt - 0.25) / 0.4, 0, 1)
    ph = 2 * np.pi * f * np.cumsum(vib) / SR
    mono = np.sin(ph) + 0.18 * np.sin(3 * ph) + 0.07 * np.sin(5 * ph)
    a = max(int(0.03 * SR), 1)
    env = np.ones(n)
    env[:a] = np.linspace(0, 1, a)
    r = int(min(0.35, dur * 0.4) * SR)
    env[-r:] *= np.linspace(1, 0, r) ** 1.5
    return mono * env * amp


def bass_note(f: float, dur: float, amp: float) -> np.ndarray:
    n = int(dur * SR)
    tt = np.arange(n) / SR
    mono = np.sin(2 * np.pi * f * tt)
    mono += 0.5 * np.sin(2 * np.pi * f * 0.5 * tt)          # sub octave
    mono += 0.22 * np.sin(2 * np.pi * f * 2.0 * tt) \
        + 0.10 * np.sin(2 * np.pi * f * 3.0 * tt)           # warmth
    a = max(int(0.012 * SR), 1)
    env = np.ones(n)
    env[:a] = np.linspace(0, 1, a)
    r = int(0.06 * SR)
    env[-r:] *= np.linspace(1, 0, r)
    mono = np.tanh(mono * 1.6)
    return np.stack([mono, mono], axis=1) * env[:, None] * amp


# ---------------- score ----------------------------------------------
# Sections of 8 bars: chord per section (circular).
SECTIONS = [
    [50, 53, 57, 60, 64],   # Dm9      (bars 0-8)
    [46, 50, 53, 57],       # Bbmaj7   (8-16)
    [41, 45, 48, 52, 57],   # Fmaj7/A  (16-24)
    [48, 52, 55, 62],       # Cadd9    (24-32)
    [46, 50, 53, 57, 60],   # Bbmaj9   (32-40)
    [50, 53, 57, 60, 64],   # Dm9      (40-48) -> wraps to itself
]
ROOTS = [38, 34, 29, 36, 34, 38]  # D2 Bb1 F1 C2 Bb1 D2

# Drums. Base groove bars 8-40, kick-only 40-44, silent 44-48 & 0-8.
drums = np.zeros((N, 2))
kick_times = []
for bar in range(BARS):
    if 8 <= bar < 44:
        for b in (0.0, 2.5):
            kt = beat_t(bar, b)
            kick_times.append(kt)
            add_wrapped(drums, kt, kick())
        if bar % 4 == 3 and bar < 40:
            kt = beat_t(bar, 3.75)
            kick_times.append(kt)
            add_wrapped(drums, kt, kick(0.55))
    if 8 <= bar < 40:
        for b in (1.0, 3.0):
            add_wrapped(drums, beat_t(bar, b), snare())
        for e in range(8):
            if RNG.random() < 0.06:
                continue
            vel = 1.0 if e % 2 == 0 else 0.55
            vel *= RNG.uniform(0.85, 1.0)
            # Hats walk the field: alternate sides per 8th (the stereo
            # play the director called out — keep it).
            add_wrapped(drums, beat_t(bar, e * 0.5, swing8=e % 2 == 1),
                    hat(False, vel, 0.38 if e % 2 == 0 else -0.38))
        if 32 <= bar < 40 and bar % 2 == 1:
            add_wrapped(drums, beat_t(bar, 3.5, swing8=True),
                    hat(True, 0.8, -0.5 if bar % 4 == 1 else 0.5))
out += drums

# Sidechain envelope from kick times (periodic; wraps with the grid).
duck = np.ones(N)
for kt in kick_times:
    i0 = int(kt * SR)
    n = int(0.30 * SR)
    idx = (i0 + np.arange(n)) % N
    duck[idx] = np.minimum(duck[idx],
            1.0 - 0.38 * np.exp(-np.arange(n) / SR / 0.11))

# Pads: warm detuned stacks, circular equal-power section windows.
pad = np.zeros((N, 2))
SEG = LOOP_S / len(SECTIONS)
for ci, chord in enumerate(SECTIONS):
    center = (ci + 0.5) * SEG
    dist = np.abs((t_full - center + LOOP_S / 2) % LOOP_S - LOOP_S / 2)
    win = np.clip((SEG / 2 + 2.0 - dist) / 4.0, 0.0, 1.0)
    win = np.sin(win * np.pi / 2) ** 2
    for note in chord:
        f = hz(note)
        for det, side in [(0.9982, 0), (1.0018, 1)]:
            ph = RNG.uniform(0, 2 * np.pi)
            tone = np.zeros(N)
            for h in range(1, 6):
                tone += np.sin(2 * np.pi * q(f * det * h) * t_full
                        + ph * h) / h
            pad[:, side] += tone * win / len(chord)
sos_pad = butter(2, 1250, btype="low", fs=SR, output="sos")
pad = sosfilt_circular(sos_pad, pad)
out += pad * 0.085 * duck[:, None]

# Bass: bars 12-44, groove per chord root.
bassbuf = np.zeros((N, 2))
B_PAT = [(0.0, 1.25), (1.5, 0.75), (2.5, 0.5), (3.25, 0.6)]
for bar in range(12, 44):
    root = ROOTS[(bar // 8) % len(SECTIONS)]
    for k, (b, dur) in enumerate(B_PAT):
        note = root if k != 3 else root + (0 if bar % 2 == 0 else 3)
        if bar % 8 == 7 and k == 3:
            note = root + 5  # walk-up into the next section
        add_wrapped(bassbuf, beat_t(bar, b),
                bass_note(hz(note), dur * SPB, 0.30))
out += bassbuf * duck[:, None]

# Motif: 2-bar hypnotic pluck loop, always on, dub delay ping-pong.
MOTIF = [
    [62, None, 65, 69, None, 72, 69, 65],    # D4 . F4 A4 . C5 A4 F4
    [64, None, 65, 69, None, 74, 72, 69],    # E4 . F4 A4 . D5 C5 A4
]
motif = np.zeros((N, 2))
DELAY = 1.5 * SPB  # dotted 8th
for bar in range(BARS):
    row = MOTIF[bar % 2]
    lift = 32 <= bar < 40
    for e, note in enumerate(row):
        if note is None:
            continue
        if RNG.random() < 0.04:
            continue
        f = hz(note + (12 if lift and bar % 4 >= 2 else 0))
        vel = RNG.uniform(0.75, 1.0) * (1.0 if e % 2 == 0 else 0.8)
        tone_amt = 1.25 if lift else 1.0
        base = pluck(f, 1.4, 0.135 * vel, tone_amt)
        pan0 = -0.55 if bar % 2 == 0 else 0.55
        for echo in range(5):
            g = 0.48 ** echo
            add_wrapped(motif, beat_t(bar, e * 0.5, swing8=e % 2 == 1)
                    + echo * DELAY,
                    stereo(base * g, pan0 * (1 if echo % 2 == 0 else -1)))
out += motif * (0.55 + 0.45 * duck[:, None])

# Lead melody: phrases in bars 16-32; octave-up answers in 32-40.
# (bar, beat, midi, dur_beats, amp)
PHRASE_A = [
    (16, 0.0, 69, 1.5, 0.16), (16, 1.5, 72, 0.5, 0.13),
    (16, 2.0, 74, 3.0, 0.16), (17, 2.0, 77, 1.0, 0.13),
    (17, 3.0, 76, 1.0, 0.12), (18, 0.0, 74, 2.0, 0.15),
    (18, 2.0, 72, 1.0, 0.12), (18, 3.0, 69, 3.0, 0.15),
    (20, 0.0, 65, 1.0, 0.12), (20, 1.0, 67, 1.0, 0.12),
    (20, 2.0, 69, 4.0, 0.16),
]
PHRASE_B = [
    (24, 0.0, 76, 1.5, 0.15), (24, 1.5, 74, 0.5, 0.12),
    (24, 2.0, 72, 2.0, 0.15), (25, 2.0, 69, 1.5, 0.13),
    (25, 3.5, 67, 0.5, 0.11), (26, 0.0, 65, 2.0, 0.14),
    (26, 2.0, 67, 1.0, 0.12), (26, 3.0, 62, 4.0, 0.16),
    (29, 0.0, 74, 1.0, 0.12), (29, 1.5, 72, 0.5, 0.11),
    (29, 2.0, 70, 2.0, 0.14), (30, 0.0, 69, 4.0, 0.15),
]
leadbuf = np.zeros((N, 2))
for phrase, oct_up, bar_shift in [
        (PHRASE_A, 0, 0), (PHRASE_B, 0, 0),
        (PHRASE_A, 12, 16),   # bars 32-36: A up an octave
        (PHRASE_B[:6], 12, 16)]:  # bars 40-... only the head, into breakdown
    for (bar, b, note, dur, amp) in phrase:
        bar2 = bar + bar_shift
        if bar2 >= 46:
            continue
        f = hz(note + oct_up)
        base = lead(f, dur * SPB * 1.05, amp * (0.8 if oct_up else 1.0))
        pan = RNG.uniform(-0.45, 0.45)
        add_wrapped(leadbuf, beat_t(bar2, b), stereo(base, pan))
        # One soft echo across the field.
        add_wrapped(leadbuf, beat_t(bar2, b) + DELAY * 2,
                stereo(base * 0.28, -pan))
sos_lead = butter(2, 4200, btype="low", fs=SR, output="sos")
leadbuf = sosfilt_circular(sos_lead, leadbuf)
out += leadbuf

# A thin air layer so the breakdown isn't dry (breath from The Bore).
breath = 0.5 + 0.5 * np.sin(2 * np.pi * t_full / (LOOP_S / 8) - np.pi / 2)
nz = RNG.standard_normal((N, 2))
sos_air = butter(2, [300, 1100], btype="band", fs=SR, output="sos")
out += sosfilt_circular(sos_air, nz) * (breath ** 2)[:, None] * 0.016

# ---------------- master ---------------------------------------------
sos_master = butter(2, 7800, btype="low", fs=SR, output="sos")
out = sosfilt_circular(sos_master, out)
out = np.tanh(out * 1.35) / np.tanh(1.35)
out *= 0.90 / np.max(np.abs(out))

path = sys.argv[1] if len(sys.argv) > 1 else "reel_home.wav"
import wave
pcm = (out * 32767).astype(np.int16)
with wave.open(path, "wb") as w:
    w.setnchannels(2)
    w.setsampwidth(2)
    w.setframerate(SR)
    w.writeframes(pcm.tobytes())
rms = float(np.sqrt(np.mean(out ** 2)))
print(f"wrote {path}  {LOOP_S:.1f}s  peak={np.max(np.abs(out)):.3f} rms={rms:.3f}")

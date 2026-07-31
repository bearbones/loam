#!/usr/bin/env python3
"""MARROW — "The Bore" (session 128): a 96s seamless ambient loop,
composed in code the way the game synthesizes every sound it owns.

    python3 dev/music/compose.py [out.wav]

Musical intent: D phrygian over an unmoving D pedal — the bore is a
throat, the bII (Eb) is the dread. The heartbeat IS the percussion
(lub-dub every 2.4s, the nerve-zap cadence). Amber answers in glass
bells, the walls breathe filtered noise on the backdrop's 9.6s cycle,
and twice per loop the trellis groans somewhere far above.

Loop-safety by construction: every LFO period divides LOOP_S, and
every event tail (bells, echoes, groans, the last heartbeat) is added
with wraparound indexing — bar 1 already contains the reverb of the
final bar.  Deterministic: seeded RNG, no wall clock.
"""

import sys
import numpy as np
from scipy.signal import butter, sosfilt

SR = 44100
LOOP_S = 96.0
N = int(SR * LOOP_S)
RNG = np.random.default_rng(0xB0E)

# D phrygian frequencies (equal temperament from A440).
def hz(midi: float) -> float:
    return 440.0 * 2.0 ** ((midi - 69) / 12.0)

def q(f: float) -> float:
    """Quantize to a whole number of cycles per loop: continuous
    oscillators must land at the seam phase-exact (error < 0.006 Hz)."""
    return round(f * LOOP_S) / LOOP_S

D1, A1, D2 = hz(26), hz(33), hz(38)
PHRYGIAN = [62, 63, 65, 67, 69, 70, 72, 74, 75, 77]  # D4..F5 degrees

out = np.zeros((N, 2), dtype=np.float64)
t_full = np.arange(N) / SR


def sosfilt_circular(sos, x: np.ndarray) -> np.ndarray:
    """IIR-filter a LOOP: warm the filter with the signal's own tail so
    sample 0 exits an already-settled filter (cold state = seam click)."""
    warm = SR
    y = sosfilt(sos, np.vstack([x[-warm:], x]), axis=0)
    return y[warm:]


def add_wrapped(buf: np.ndarray, start_s: float, chunk: np.ndarray) -> None:
    """Mix a stereo chunk in at start_s, wrapping past the loop end."""
    idx = (int(start_s * SR) + np.arange(len(chunk))) % N
    np.add.at(buf, idx, chunk)


def env_ad(n: int, a_s: float, d_s: float, curve: float = 3.0) -> np.ndarray:
    """Attack-decay envelope, exponential-ish decay."""
    a = max(int(a_s * SR), 1)
    e = np.ones(n)
    e[:a] = np.linspace(0.0, 1.0, a)
    d = n - a
    if d > 0:
        e[a:] = np.exp(-curve * np.linspace(0.0, 1.0, d))
    return e


# ---- 1. Sub drone: D1 + A1, detuned pairs, breathing at 9.6s --------
breath = 0.55 + 0.45 * np.sin(2 * np.pi * t_full / 9.6 - np.pi / 2)
drone = np.zeros(N)
for f, g in [(D1, 0.50), (D1 * 1.003, 0.42), (A1, 0.22), (A1 * 0.997, 0.20)]:
    drone += g * np.sin(2 * np.pi * q(f) * t_full + RNG.uniform(0, 2 * np.pi))
drone *= 0.16 * (0.55 + 0.45 * breath)
out[:, 0] += drone
out[:, 1] += drone

# ---- 2. Heartbeat: lub-dub every 2.4s, pitch-dropping thumps --------
def thump(dur: float, f0: float, f1: float, amp: float) -> np.ndarray:
    n = int(dur * SR)
    tt = np.arange(n) / SR
    freq = f0 + (f1 - f0) * (tt / dur)
    ph = 2 * np.pi * np.cumsum(freq) / SR
    mono = np.sin(ph) * np.exp(-tt / (dur * 0.30)) * amp
    return np.stack([mono, mono], axis=1)

for k in range(int(LOOP_S / 2.4)):
    beat_t = k * 2.4
    swell = 0.8 + 0.2 * np.sin(2 * np.pi * beat_t / 19.2)  # long tide
    add_wrapped(out, beat_t, thump(0.32, 58, 38, 0.34 * swell))          # lub
    add_wrapped(out, beat_t + 0.34, thump(0.26, 50, 34, 0.22 * swell))   # dub

# ---- 3. Pad: four 24s chords over the pedal, circular crossfade -----
CHORDS = [
    [50, 53, 57],       # Dm   (D3 F3 A3)
    [51, 55, 58],       # Eb   (bII — the dread)
    [50, 55, 58],       # Gm/D
    [50, 53, 58, 60],   # Bb add C leaning home
]
SEG = LOOP_S / len(CHORDS)
pad = np.zeros((N, 2))
for ci, chord in enumerate(CHORDS):
    # Circular equal-power window: full inside the segment, 6s skirts.
    center = (ci + 0.5) * SEG
    dist = np.abs((t_full - center + LOOP_S / 2) % LOOP_S - LOOP_S / 2)
    win = np.clip((SEG / 2 + 3.0 - dist) / 6.0, 0.0, 1.0)
    win = np.sin(win * np.pi / 2) ** 2
    for note in chord:
        f = hz(note)
        for det, side in [(0.9985, 0), (1.0015, 1)]:
            ph = RNG.uniform(0, 2 * np.pi)
            tone = np.sin(2 * np.pi * q(f * det) * t_full + ph)
            tone += 0.35 * np.sin(2 * np.pi * q(f * det * 2.01) * t_full + ph)
            tone += 0.12 * np.sin(2 * np.pi * q(f * det * 2.99) * t_full + ph)
            pad[:, side] += tone * win / len(chord)
sos_pad = butter(2, [90, 1400], btype="band", fs=SR, output="sos")
pad = sosfilt_circular(sos_pad, pad)
out += pad * 0.075

# ---- 4. Breath: bandpassed noise riding the 9.6s cycle --------------
noise = RNG.standard_normal((N, 2))
sos_br = butter(2, [260, 950], btype="band", fs=SR, output="sos")
breath_noise = sosfilt_circular(sos_br, noise)
out += breath_noise * (breath ** 2)[:, None] * 0.028

# ---- 5. Amber bells: FM glass, sparse phrygian phrase, ping-pong ----
def bell(f: float, dur: float, amp: float) -> np.ndarray:
    n = int(dur * SR)
    tt = np.arange(n) / SR
    mod = np.sin(2 * np.pi * f * 3.01 * tt) * 3.5 * np.exp(-tt * 4.0)
    mono = np.sin(2 * np.pi * f * tt + mod) * env_ad(n, 0.004, dur, 4.5)
    return mono * amp

bell_track = np.zeros((N, 2))
t_cursor = 4.0
side = 0
while t_cursor < LOOP_S - 2.0:
    note = int(RNG.choice(PHRYGIAN, p=None))
    f = hz(note)
    dur = float(RNG.uniform(2.5, 4.5))
    base = bell(f, dur, float(RNG.uniform(0.10, 0.16)))
    # Ping-pong echoes, 0.8s apart, wrapped past the loop end.
    for e in range(6):
        g = 0.5 ** e
        ch = np.zeros((len(base), 2))
        ch[:, (side + e) % 2] = base * g
        add_wrapped(bell_track, t_cursor + e * 0.8, ch)
    side ^= 1
    t_cursor += float(RNG.uniform(3.0, 7.5))
out += bell_track

# ---- 6. Trellis groans: two far-off metallic swells -----------------
def groan(dur: float, base_f: float) -> np.ndarray:
    n = int(dur * SR)
    tt = np.arange(n) / SR
    mono = np.zeros(n)
    for p, g in [(1.0, 0.5), (2.76, 0.30), (5.40, 0.18), (8.93, 0.10)]:
        drift = 1.0 + 0.004 * np.sin(2 * np.pi * 0.3 * tt + p)
        mono += g * np.sin(2 * np.pi * base_f * p * drift * tt)
    e = np.sin(np.pi * tt / dur) ** 2
    return np.stack([mono * e, mono * e * 0.8], axis=1)

add_wrapped(out, 40.0, groan(6.0, A1) * 0.10)
add_wrapped(out, 72.0, groan(7.0, D1 * 1.5) * 0.11)

# ---- 7. Nerve sparks: rare, tiny, high ------------------------------
for _ in range(5):
    at = float(RNG.uniform(0, LOOP_S))
    f = hz(int(RNG.choice([86, 87, 89])))
    n = int(0.5 * SR)
    tt = np.arange(n) / SR
    blip = np.sin(2 * np.pi * f * tt) * np.exp(-tt * 18.0) * 0.05
    ch = np.zeros((n, 2))
    ch[:, int(RNG.integers(0, 2))] = blip
    add_wrapped(out, at, ch)

# ---- Master: gentle lowpass, soft clip, normalize -------------------
sos_master = butter(2, 6500, btype="low", fs=SR, output="sos")
out = sosfilt_circular(sos_master, out)
out = np.tanh(out * 1.4) / np.tanh(1.4)
out *= 0.89 / np.max(np.abs(out))

path = sys.argv[1] if len(sys.argv) > 1 else "the_bore.wav"
pcm = (out * 32767).astype(np.int16)
import wave
with wave.open(path, "wb") as w:
    w.setnchannels(2)
    w.setsampwidth(2)
    w.setframerate(SR)
    w.writeframes(pcm.tobytes())
rms = float(np.sqrt(np.mean(out ** 2)))
print(f"wrote {path}  {LOOP_S:.0f}s  peak={np.max(np.abs(out)):.3f} rms={rms:.3f}")

#!/usr/bin/env python3
"""MARROW — the hermit portraits (session 130). Three room themes,
one per character the director named; each a personality in mode,
meter, and machinery. Melody discipline this time (the Reel Home
critique): every theme is a SENTENCE — motif, development toward one
peak, cadence home — with a signature interval as its identity.

    python3 songs/hermits.py [outdir]

  THE LIBRARIAN  — v2 (director: v1 "too empty... default
      metronome"; brief: "Castlevania harpsichord with a Arabic
      maqamat"). D HIJAZ KAR (D Eb F# G A Bb C#), 4/4 @96, 80s:
      two-choir harpsichord, driving 16th arpeggio ostinato as the
      engine (no bare ticks), walking continuo bass, ornamented
      melody sentence whose signature is the AUGMENTED SECOND
      falling F#->Eb, one peak, maqam cadence home.
  THE APOTHECAN  — D harmonic minor, 3/4 @66, ~87s. A brewing
      waltz: pitched drips in 5-against-7 polyrhythm, blown-bottle
      melody whose signature is the AUGMENTED SECOND (Bb->C#).
  THE APPARATUAN — D minor pentatonic + b5, 7/8 @112, 75s. A
      machine with a limp: piston kick in seven, ratchet 16ths,
      sequencer arp ostinato, angular lead whose signature is the
      TRITONE (D->Ab), settling to idle on the cadence.

Loop-craft as established: oscillators quantized to whole cycles per
loop, IIR filters warmed with their own tail, event tails wrapped.
Deterministic (seeded per piece).
"""

import os
import sys
import numpy as np
from scipy.signal import butter, sosfilt

sys.path.insert(0, os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))))
from loam import SR, hz, Loop, stereo, ad_env, write_wav


# =====================================================================
def librarian() -> np.ndarray:
    # v2 (director): "Castlevania harpsichord with a Arabic maqamat."
    # D Hijaz Kar — two augmented seconds (Eb-F#, Bb-C#), gothic and
    # maqam at once. The 16th-note arp IS the engine now; no ticks.
    BPM, BARS = 96.0, 32
    spb = 60.0 / BPM
    L = Loop(BARS * 4 * spb, 0xB00C2)  # 80.0s

    def bt(bar: float, beat: float = 0.0) -> float:
        return (bar * 4 + beat) * spb

    # Harpsichord: two choirs (8' + 4'), bright partial stack, quill
    # click at the pluck, fast decay — dry and articulate.
    def harpsi(f: float, dur: float, amp: float) -> np.ndarray:
        n = int(dur * SR)
        tt = np.arange(n) / SR

        def choir(fc: float) -> np.ndarray:
            m = np.zeros(n)
            for h, g in [(1, 1.0), (2, 0.52), (3, 0.40), (4, 0.26),
                    (5, 0.17), (6, 0.11), (7, 0.07)]:
                m += g * np.sin(2 * np.pi * fc * h * tt)
            return m

        m = choir(f) + 0.42 * choir(f * 2.0015)
        quill = L.rng.standard_normal(int(0.0025 * SR)) * 0.5
        m[: len(quill)] += quill * np.linspace(1, 0, len(quill))
        env = ad_env(n, 0.0012, 5.0)
        r = int(0.02 * SR)
        if n > r:
            env[-r:] *= np.linspace(1, 0, r)
        return np.tanh(m * env * 1.2) * amp

    def orn(note: int, when: float, dur_b: float, amp: float,
            pan: float) -> None:
        """Melody note with a mordent (note-upper-note grace)."""
        g = spb / 8.0
        L.add(when, stereo(harpsi(hz(note), g * 1.5, amp * 0.7), pan))
        L.add(when + g, stereo(harpsi(hz(note + 1), g * 1.5,
                amp * 0.6), pan))
        L.add(when + 2 * g, stereo(harpsi(hz(note),
                dur_b * spb - 2 * g, amp), pan))

    # Faint dark drone so the room has walls (D2, 10s breathing).
    breath = 0.6 + 0.4 * np.sin(2 * np.pi * L.t / 10.0 - np.pi / 2)
    drone = np.zeros(L.n)
    for f, g in [(hz(38), 0.6), (hz(38) * 1.0025, 0.45)]:
        drone += g * np.sin(2 * np.pi * L.q(f) * L.t
                + L.rng.uniform(0, 2 * np.pi))
    L.buf += (drone * 0.045 * breath)[:, None]

    # The engine: 16th-note Hijaz Kar arpeggio, one bar figure rising
    # then falling through the aug-2nd, color tones alternating bars.
    # Bars 0-4 and 28-32 run it alone (wrap = the same texture).
    ARP_A = [62, 63, 66, 67, 69, 67, 66, 63,
             62, 63, 66, 69, 70, 69, 66, 63]     # D Eb F# G A ... Bb
    ARP_B = [62, 63, 66, 67, 69, 67, 66, 63,
             62, 61, 62, 66, 63, 62, 61, 62]     # ... C# turn figure
    for bar in range(BARS):
        row = ARP_A if bar % 2 == 0 else ARP_B
        for s, note in enumerate(row):
            vel = 1.0 if s % 4 == 0 else (0.72 if s % 2 == 0 else 0.58)
            L.add(bt(bar, s * 0.25),
                    stereo(harpsi(hz(note), 0.34, 0.10 * vel), 0.3))

    # Continuo: 8th-note bass, D pedal with hijaz neighbors, cadence
    # walk (Bb1->A1) at every 8-bar seam.
    BASS = [38, 38, 45, 38, 39, 38, 45, 38]      # D D A D Eb D A D
    for bar in range(BARS):
        row = list(BASS)
        if bar % 8 == 7:
            row[6], row[7] = 34, 33               # Bb -> A into the turn
        for e, note in enumerate(row):
            vel = 1.0 if e % 2 == 0 else 0.66
            L.add(bt(bar, e * 0.5),
                    stereo(harpsi(hz(note), 0.5, 0.15 * vel), -0.3))

    # Melody: SENTENCE GRAMMAR (director, session 132 — "0:48 is
    # decidedly the end of the phrase and should be the end of the
    # sentence... taking a pause and then forming the next sentence").
    # Two distinct 4-bar sentences, each cadencing and then RESTING a
    # full bar; the low mutter gets its own bars afterward instead of
    # talking over anyone.  (bar, beat, midi, dur_beats, amp, mordent?)
    S1 = [  # the question: rises, leans C#, arrives D5. Done.
        (0, 0.0, 69, 1.5, 0.24, True),  (0, 1.5, 70, 0.5, 0.19, False),
        (0, 2.0, 69, 1.0, 0.20, False), (0, 3.0, 67, 1.0, 0.19, False),
        (1, 0.0, 66, 1.5, 0.22, True),  (1, 1.5, 67, 0.5, 0.18, False),
        (1, 2.0, 63, 1.0, 0.21, False), (1, 3.0, 62, 1.0, 0.20, False),
        (2, 0.0, 66, 0.5, 0.18, False), (2, 0.5, 67, 0.5, 0.18, False),
        (2, 1.0, 69, 0.5, 0.19, False), (2, 1.5, 70, 0.5, 0.19, False),
        (2, 2.0, 73, 2.0, 0.24, True),
        (3, 0.0, 74, 3.0, 0.26, False),                  # cadence, held
    ]
    S2 = [  # its own opening (Bb, not D5), the Eb5 cry, maqam descent
        (0, 0.0, 70, 1.5, 0.22, True),  (0, 1.5, 69, 0.5, 0.18, False),
        (0, 2.0, 70, 1.0, 0.20, False), (0, 3.0, 73, 1.0, 0.21, False),
        (1, 0.0, 74, 1.5, 0.24, False), (1, 1.5, 75, 0.5, 0.26, False),
        (1, 2.0, 74, 1.0, 0.22, False), (1, 3.0, 73, 1.0, 0.21, False),
        (2, 0.0, 70, 1.0, 0.20, True),  (2, 1.0, 69, 1.0, 0.19, False),
        (2, 2.0, 67, 1.0, 0.18, False), (2, 3.0, 66, 1.0, 0.19, False),
        (3, 0.0, 66, 1.0, 0.19, False), (3, 1.0, 63, 1.0, 0.20, False),
        (3, 2.0, 62, 2.0, 0.24, False),                  # home
    ]

    def say(phrase, bar0: int, gain: float, oct_down: int,
            pan: float) -> None:
        for (bar, b, note, dur, amp, mord) in phrase:
            when = bt(bar0 + bar, b)
            if mord and gain > 0.6:
                orn(note - oct_down, when, dur, amp * gain, pan)
            else:
                L.add(when, stereo(harpsi(hz(note - oct_down),
                        dur * spb * 1.05, amp * gain), pan))

    say(S1, 8, 1.0, 0, 0.15)    # bars 8-11, rest 12
    say(S2, 13, 1.0, 0, 0.2)    # bars 13-16, rest 17
    say(S1, 18, 0.5, 12, -0.4)  # the scholar mutters it back, low
    say(S2, 23, 0.4, 12, -0.4)  # bars 23-26, fading; 27+ arp only
    return L.master(7000.0, drive=1.8)


# =====================================================================
def apothecan() -> np.ndarray:
    BPM, BARS = 66.0, 32           # 3/4 waltz
    spb = 60.0 / BPM
    L = Loop(BARS * 3 * spb, 0xA9075)  # 87.3s

    def bt(bar: float, beat: float = 0.0) -> float:
        return (bar * 3 + beat) * spb

    # Pitched drip: sine blip with a fast downward chirp.
    def drip(f: float, amp: float) -> np.ndarray:
        n = int(0.16 * SR)
        tt = np.arange(n) / SR
        freq = f * (1.0 + 0.5 * np.exp(-tt * 60.0))
        ph = 2 * np.pi * np.cumsum(freq) / SR
        return np.sin(ph) * ad_env(n, 0.001, 26.0) * amp

    # Blown bottle: breathy fundamental, soft even partial, air noise.
    def bottle(f: float, dur: float, amp: float, rng) -> np.ndarray:
        n = int(dur * SR)
        tt = np.arange(n) / SR
        vib = 1.0 + 0.005 * np.sin(2 * np.pi * 4.6 * tt) \
            * np.clip((tt - 0.3) / 0.5, 0, 1)
        ph = 2 * np.pi * f * np.cumsum(vib) / SR
        m = np.sin(ph) + 0.25 * np.sin(2 * ph)
        sos = butter(2, [f * 0.8, f * 3.0], btype="band", fs=SR,
                output="sos")
        air = sosfilt(sos, rng.standard_normal(n)) * 0.10
        a = max(int(0.06 * SR), 1)
        env = np.ones(n)
        env[:a] = np.linspace(0, 1, a)
        r = int(min(0.4, dur * 0.4) * SR)
        env[-r:] *= np.linspace(1, 0, r) ** 1.2
        return (m + air) * env * amp

    # Simmer: low bandpassed noise + slow bubble pops.
    nz = L.rng.standard_normal((L.n, 2))
    sos_sim = butter(2, [90, 320], btype="band", fs=SR, output="sos")
    L.buf += L.filt_circular(sos_sim, nz) * 0.030
    for _ in range(40):
        at = float(L.rng.uniform(0, L.loop_s))
        f0 = float(L.rng.uniform(180, 420))
        L.add(at, stereo(drip(f0, 0.05), float(L.rng.uniform(-0.6, 0.6))))

    # Drips in polyrhythm: one voice every 5 8ths (D5), one every 7
    # (A4) — the lab keeps two clocks. 8th = spb/2.
    e8 = spb / 2
    k = 0
    while k * 5 * e8 < L.loop_s:
        L.add(k * 5 * e8, stereo(drip(hz(86), 0.10), 0.45))
        k += 1
    k = 0
    while k * 7 * e8 < L.loop_s:
        L.add(k * 7 * e8, stereo(drip(hz(81), 0.09), -0.45))
        k += 1

    # Bass beat (director, session 133: "could do with a more present
    # bass beat"): a rounded waltz thump — strong ONE, ghost on three
    # every other bar — plus a sub bass note on the root. Enters after
    # the intro, bows out before the wrap so the loop still breathes.
    def waltz_kick(amp: float) -> np.ndarray:
        n = int(0.34 * SR)
        tt = np.arange(n) / SR
        freq = 50.0 * np.exp(-tt * 8.0) + 35.0
        ph = 2 * np.pi * np.cumsum(freq) / SR
        m = np.tanh(np.sin(ph) * 2.0) * np.exp(-tt * 8.5)
        return np.stack([m, m], axis=1) * 0.46 * amp

    def sub_note(f: float, dur: float, amp: float) -> np.ndarray:
        n = int(dur * SR)
        tt = np.arange(n) / SR
        m = np.sin(2 * np.pi * f * tt) \
            + 0.30 * np.sin(2 * np.pi * f * 2.0 * tt)
        a = max(int(0.02 * SR), 1)
        env = np.ones(n)
        env[:a] = np.linspace(0, 1, a)
        r = int(0.10 * SR)
        env[-r:] *= np.linspace(1, 0, r)
        return np.stack([m, m], axis=1) * env[:, None] * amp

    ROOTS_W = [38, 43, 45, 38]   # D2 G2 A2 D2, one per 8-bar section
    kick_times = []
    for bar in range(4, 28):
        kt = bt(bar, 0.0)
        kick_times.append(kt)
        L.add(kt, waltz_kick(1.0))
        if bar % 2 == 1:
            L.add(bt(bar, 2.0), waltz_kick(0.45))
        root = ROOTS_W[(bar // 8) % 4]
        L.add(bt(bar, 0.0), sub_note(hz(root), 1.6 * spb, 0.22))
        if bar % 4 == 3:
            L.add(bt(bar, 2.0), sub_note(hz(root - 3), 0.9 * spb, 0.15))

    duck = np.ones(L.n)
    for kt in kick_times:
        i0 = int(kt * SR)
        n = int(0.26 * SR)
        idx = (i0 + np.arange(n)) % L.n
        duck[idx] = np.minimum(duck[idx],
                1.0 - 0.24 * np.exp(-np.arange(n) / SR / 0.10))

    # Sway pad: Dm -> Gm -> A(C#) -> Dm, 8 bars each, circular.
    CHORDS = [[50, 53, 57], [50, 55, 58], [49, 52, 57], [50, 53, 57]]
    SEG = L.loop_s / len(CHORDS)
    pad = np.zeros((L.n, 2))
    for ci, chord in enumerate(CHORDS):
        center = (ci + 0.5) * SEG
        dist = np.abs((L.t - center + L.loop_s / 2) % L.loop_s
                - L.loop_s / 2)
        win = np.sin(np.clip((SEG / 2 + 1.5 - dist) / 3.0, 0, 1)
                * np.pi / 2) ** 2
        for note in chord:
            for det, side in [(0.998, 0), (1.002, 1)]:
                ph = L.rng.uniform(0, 2 * np.pi)
                pad[:, side] += np.sin(2 * np.pi
                        * L.q(hz(note) * det) * L.t + ph) * win / 3
    sos_pad = butter(2, 900, btype="low", fs=SR, output="sos")
    L.buf += L.filt_circular(sos_pad, pad) * 0.075 * duck[:, None]

    # Melody: the waltz sentence (harmonic minor; signature Bb->C#).
    SENT = [
        (0, 0, 69, 2, 0.15), (0, 2, 70, 1, 0.13),
        (1, 0, 69, 2, 0.14), (1, 2, 67, 1, 0.12),
        (2, 0, 65, 2, 0.14), (2, 2, 64, 1, 0.12),
        (3, 0, 62, 3, 0.15),
        (4, 0, 70, 2, 0.16), (4, 2, 73, 1, 0.17),   # Bb -> C#: the sign
        (5, 0, 74, 2, 0.17), (5, 2, 69, 1, 0.13),
        (6, 0, 65, 1, 0.13), (6, 1, 64, 1, 0.12), (6, 2, 61, 1, 0.14),
        (7, 0, 62, 3, 0.16),
    ]
    DEV = [  # second pass rises to the one peak (F5) then settles
        (0, 0, 74, 2, 0.16), (0, 2, 76, 1, 0.14),
        (1, 0, 77, 3, 0.18),
        (2, 0, 76, 1, 0.14), (2, 1, 74, 1, 0.13), (2, 2, 73, 1, 0.15),
        (3, 0, 74, 3, 0.16),
        (4, 0, 70, 2, 0.15), (4, 2, 73, 1, 0.16),
        (5, 0, 69, 2, 0.14), (5, 2, 67, 1, 0.12),
        (6, 0, 65, 1, 0.13), (6, 1, 64, 1, 0.12), (6, 2, 61, 1, 0.13),
        (7, 0, 62, 3, 0.17),
    ]
    for bar0, phrase in [(8, SENT), (16, DEV), (24, SENT)]:
        fade = 0.72 if bar0 == 24 else 1.0
        for (bar, b, note, dur, amp) in phrase:
            m = bottle(hz(note), dur * spb * 1.05, amp * fade, L.rng)
            L.add(bt(bar0 + bar, b),
                    stereo(m, float(L.rng.uniform(-0.25, 0.25))))
    return L.master(5200.0)


# =====================================================================
def apparatuan() -> np.ndarray:
    BPM, BARS = 112.0, 40          # 7/8 — the machine's limp
    spb = 60.0 / BPM
    L = Loop(BARS * 3.5 * spb, 0xAFFA)  # 75.0s

    def bt(bar: float, e8: float = 0.0) -> float:
        return (bar * 3.5 + e8 * 0.5) * spb

    def piston(amp: float) -> np.ndarray:
        n = int(0.30 * SR)
        tt = np.arange(n) / SR
        freq = 60.0 * np.exp(-tt * 11.0) + 42.0
        ph = 2 * np.pi * np.cumsum(freq) / SR
        m = np.tanh(np.sin(ph) * 2.5) * np.exp(-tt * 10.0)
        return np.stack([m, m], axis=1) * 0.5 * amp

    def ratchet(amp: float) -> np.ndarray:
        n = int(0.028 * SR)
        nz = L.rng.standard_normal(n)
        sos = butter(2, [3500, 9000], btype="band", fs=SR, output="sos")
        return sosfilt(sos, nz) * ad_env(n, 0.0004, 110.0) * amp

    def anvil(f: float, amp: float) -> np.ndarray:
        n = int(0.5 * SR)
        tt = np.arange(n) / SR
        m = np.zeros(n)
        for p, g in [(1.0, 0.5), (2.72, 0.3), (4.55, 0.2), (6.97, 0.12)]:
            m += g * np.sin(2 * np.pi * f * p * tt)
        return m * ad_env(n, 0.001, 9.0) * amp

    def horn(f: float, dur: float, amp: float) -> np.ndarray:
        n = int(dur * SR)
        tt = np.arange(n) / SR
        mod = np.sin(2 * np.pi * f * 2.0 * tt) * 2.2 * np.exp(-tt * 3.0)
        m = np.sin(2 * np.pi * f * tt + mod)
        a = max(int(0.02 * SR), 1)
        env = np.ones(n)
        env[:a] = np.linspace(0, 1, a)
        r = int(min(0.25, dur * 0.4) * SR)
        env[-r:] *= np.linspace(1, 0, r)
        return m * env * amp

    def hiss(amp: float) -> np.ndarray:
        n = int(1.2 * SR)
        tt = np.arange(n) / SR
        nz = L.rng.standard_normal(n)
        sos = butter(2, [2000, 7000], btype="band", fs=SR, output="sos")
        return sosfilt(sos, nz) * np.exp(-tt * 3.0) * amp

    # Drums: kick on 8ths 0,3,5 of the seven; ratchets on all 16ths;
    # anvil answers on 8th 6 every other bar. Drums rest bars 0-4 and
    # 36-40 (the machine spinning up / winding down; wraps clean).
    kick_times = []
    for bar in range(BARS):
        run = 4 <= bar < 36
        if run:
            for e in (0, 3, 5):
                kt = bt(bar, e)
                kick_times.append(kt)
                L.add(kt, piston(1.0 if e == 0 else 0.75))
            for s in range(14):
                if L.rng.random() < 0.08:
                    continue
                amp = 0.55 if s % 2 else 1.0
                L.add(bt(bar, s * 0.5),
                        stereo(ratchet(0.42 * amp),
                        0.42 if s % 2 else -0.42))
            if bar % 2 == 1:
                L.add(bt(bar, 6), stereo(anvil(hz(50), 0.16),
                        0.3 if bar % 4 == 1 else -0.3))
        if bar % 8 == 7:
            L.add(bt(bar, 5), stereo(hiss(0.05),
                    float(L.rng.uniform(-0.5, 0.5))))

    duck = np.ones(L.n)
    for kt in kick_times:
        i0 = int(kt * SR)
        n = int(0.22 * SR)
        idx = (i0 + np.arange(n)) % L.n
        duck[idx] = np.minimum(duck[idx],
                1.0 - 0.30 * np.exp(-np.arange(n) / SR / 0.08))

    # Sequencer arp ostinato: 16ths D3 F3 A3 C4, Ab3 slipping in every
    # fourth cycle — the machine's always-on hum (the part that stays).
    arp_notes = [50, 53, 57, 60]
    arp = np.zeros((L.n, 2))
    step = 0
    tcur = 0.0
    e16 = spb * 0.25
    while tcur < L.loop_s - e16:
        cyc = step // 4
        note = arp_notes[step % 4]
        if cyc % 4 == 3 and step % 4 == 2:
            note = 56  # the Ab: grit in the gears
        m = horn(hz(note), e16 * 1.8, 0.085)
        arp_chunk = stereo(m, 0.5 if step % 2 else -0.5)
        idx = (int(tcur * SR) + np.arange(len(arp_chunk))) % L.n
        np.add.at(arp, idx, arp_chunk)
        step += 1
        tcur += e16
    L.buf += arp * (0.45 + 0.55 * duck[:, None])

    # Lead: TIGHTENED (director, session 131) — every onset rides a
    # piston accent (8ths 0/3/5), motif stated twice, one peak bar,
    # immediate cadence to idle. No meander between statements.
    SENT = [
        (8, 0, 62, 3, 0.21), (8, 3, 65, 2, 0.19), (8, 5, 68, 2, 0.22),
        (9, 0, 67, 3, 0.20), (9, 3, 65, 2, 0.17), (9, 5, 62, 2, 0.18),
        (10, 0, 67, 3, 0.21), (10, 3, 72, 2, 0.20), (10, 5, 74, 2, 0.23),
        (11, 0, 72, 3, 0.20), (11, 3, 68, 2, 0.19), (11, 5, 67, 2, 0.18),
        (12, 0, 74, 5, 0.25), (12, 5, 72, 2, 0.20),  # the peak, held
        (13, 0, 68, 3, 0.21), (13, 3, 65, 2, 0.18), (13, 5, 63, 2, 0.17),
        (14, 0, 62, 7, 0.22),                        # settled to idle
    ]
    # Statements at 8-14 and 20-26; the octave answer waits for its
    # own bars (28+) with a rest bar between — no talking over.
    for bar0, oct_up, gain in [(0, 0, 1.0), (12, 0, 1.0), (20, 12, 0.6)]:
        for (bar, e, note, dur, amp) in SENT:
            b2 = bar + bar0
            if b2 >= 34 or (bar0 == 16 and bar >= 13):
                continue
            m = horn(hz(note + oct_up), dur * 0.5 * spb * 1.05,
                    amp * gain)
            L.add(bt(b2, e), stereo(m, 0.18 if oct_up else -0.12))
            L.add(bt(b2, e) + 3 * e16 * 2,
                    stereo(m * 0.28, -0.3 if oct_up else 0.3))
    return L.master(8200.0, drive=1.5)


# =====================================================================
if __name__ == "__main__":
    outdir = sys.argv[1] if len(sys.argv) > 1 else "."
    os.makedirs(outdir, exist_ok=True)
    write_wav(os.path.join(outdir, "the_librarian.wav"), librarian())
    write_wav(os.path.join(outdir, "the_apothecan.wav"), apothecan())
    write_wav(os.path.join(outdir, "the_apparatuan.wav"), apparatuan())

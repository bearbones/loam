"""Rhythm and scale — the composer's graph paper.

euclid(k, n): distribute k onsets as evenly as possible over n
steps (Bjorklund's algorithm — same math as leap years). Toussaint
showed these ARE the world's rhythms: euclid(3,8) is the tresillo,
(5,8) the cinquillo, (2,5) the Korean jeongganbo, (5,16) the
bossa. rotate() picks which onset is "one"; swing() and prob()
humanize.

SCALES: interval tables from the tonic (semitones), including the
maqamat loam already sings in. scale_notes() unrolls them across
octaves from any tonic.
"""

import numpy as np


def euclid(k: int, n: int) -> list:
    """Bjorklund: k onsets in n steps, maximally even. Returns a
    list of n ints (1 = onset)."""
    if k <= 0:
        return [0] * n
    if k >= n:
        return [1] * n
    a = [[1] for _ in range(k)]
    b = [[0] for _ in range(n - k)]
    while len(b) > 1:
        m = min(len(a), len(b))
        pairs = [a[i] + b[i] for i in range(m)]
        rest = a[m:] + b[m:]
        a, b = pairs, rest
        if len(b) > len(a):
            a, b = a + [], b
        if not b:
            break
        if len(a) <= 1:
            break
    return [v for grp in a + b for v in grp]


def rotate(pat: list, by: int) -> list:
    by %= len(pat)
    return pat[by:] + pat[:by]


def swing(times: list, amount: float, grid: float) -> list:
    """Delay every off-grid-pair step by amount*grid (0.14 = the
    Reel Home pocket). times in beats, grid = 8th/16th in beats."""
    out = []
    for t in times:
        idx = round(t / grid)
        out.append(t + (amount * grid if idx % 2 else 0.0))
    return out


def prob(pat: list, p_keep: float, rng) -> list:
    """Thin a pattern: each onset survives with p_keep."""
    return [v if (v and rng.random() < p_keep) else 0 for v in pat]


def onsets(pat: list, step_beats: float) -> list:
    """Pattern -> onset times in beats."""
    return [i * step_beats for i, v in enumerate(pat) if v]


# Interval tables (semitones from tonic).
SCALES = {
    "major":          [0, 2, 4, 5, 7, 9, 11],
    "minor":          [0, 2, 3, 5, 7, 8, 10],
    "harmonic_minor": [0, 2, 3, 5, 7, 8, 11],
    "dorian":         [0, 2, 3, 5, 7, 9, 10],
    "phrygian":       [0, 1, 3, 5, 7, 8, 10],
    "lydian":         [0, 2, 4, 6, 7, 9, 11],
    "mixolydian":     [0, 2, 4, 5, 7, 9, 10],
    "minor_penta":    [0, 3, 5, 7, 10],
    "hijaz":          [0, 1, 4, 5, 7, 8, 10],      # maqam hijaz
    "hijaz_kar":      [0, 1, 4, 5, 7, 8, 11],      # both aug-2nds
    "nahawand":       [0, 2, 3, 5, 7, 8, 11],      # ~harmonic minor
    "kurd":           [0, 1, 3, 5, 7, 8, 10],      # ~phrygian
    "saba_ish":       [0, 2, 3, 4, 7, 8, 10],      # 12-TET shadow of saba
    "whole":          [0, 2, 4, 6, 8, 10],
    "octatonic":      [0, 2, 3, 5, 6, 8, 9, 11],
}


def scale_notes(tonic_midi: int, name: str, octaves: int = 2) -> list:
    """Unroll a scale from the tonic across octaves (inclusive of
    the top tonic)."""
    iv = SCALES[name]
    out = []
    for o in range(octaves):
        out += [tonic_midi + 12 * o + s for s in iv]
    out.append(tonic_midi + 12 * octaves)
    return out


def quantize_to(midi: float, tonic_midi: int, name: str) -> int:
    """Snap any midi note to the nearest scale member."""
    iv = SCALES[name]
    rel = (midi - tonic_midi) % 12.0
    best = min(iv + [12], key=lambda s: abs(s - rel))
    return int(midi - rel + best)

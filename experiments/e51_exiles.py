#!/usr/bin/env python3
"""e51 — the exiles return: a structural witness for the octave
rescue.

Session 50 ended on a measured wall: true-rescue and phantom
SIZE fractions overlap at 0.06-0.12, so five certified triad
shapes (root-position major triads among them) were exiled
rather than let loop phantoms in. e51 replaces size with
STRUCTURE (ruler._sub_structure): a real sub-fundamental holds
on-grid energy — within +/-2 RAW bins of its refined multiples —
at the o the winner's comb can't explain, and at least one live
witness must be ODD (an odd multiple is the one thing a
half-of-something-real phantom can never inherit). Witnesses
read the raw spectrum, which no null ever touches, so the e50
single-witness failure (chords eating nulled bins) cannot recur.

Measured consequences, all re-swept: the certified triad set
grows 9 -> 21 shapes (all 14 ever certified return, plus 7 new);
the full-sweep hit rate 542 -> 578/636; both dyad suites read
PERFECT (296/296, closing the (46,61)-family octave-up thread);
and the session-50 phantom score — the 12 beats that spawned the
whole saga — reads 12/12 blind. e44 and e50 re-audition green.

Proof piece: what the nine-shape set could never say — the
DORIAN VAMP. Root-position i and IV (D minor, G MAJOR: the major
IV is the mode's signature color) with root-position C, F, Em,
Am passing chords, 16 beats, recovered from the mix blind.

    python3 experiments/e51_exiles.py [outdir]
"""

import os
import subprocess
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))))
from loam import SR, hz, Loop, stereo, write_wav
from loam import ruler
from loam.strings import pluck

outdir = sys.argv[1] if len(sys.argv) > 1 else "render"
os.makedirs(outdir, exist_ok=True)
fails = []


def check(name, cond, detail):
    print(f"  {'PASS' if cond else 'FAIL'} {name}: {detail}")
    if not cond:
        fails.append(name)


def midi_of(f):
    return int(round(69 + 12 * np.log2(f / 440.0)))


def tri_sig(a, i1, i2):
    c = a + i1 + i2
    return pluck(hz(a), 0.5, seed=a * 7 + i1) \
        + pluck(hz(a + i1), 0.5, seed=300 + a * 3 + i2) \
        + pluck(hz(c), 0.5, seed=600 + a + i1 * 5 + i2)


# ---- 1. the exiles read (the six cases size exiled) ------------
EXILES = [(45, 4, 3), (55, 7, 7), (50, 7, 8), (50, 7, 9),
        (55, 7, 9), (52, 9, 21)]
h = t = 0
for a, i1, i2 in EXILES:
    got = tuple(midi_of(f)
            for f in ruler.triad_pitches(tri_sig(a, i1, i2)))
    t += 1
    h += (got == (a, a + i1, a + i1 + i2))
check("the exiled shapes read", h == t, f"{h}/{t} cases that the "
        f"0.12 size bar refused (fracs 0.08-0.11, phantom range)")

# ---- 2. the newly certified shapes hold (spot sweep) -----------
NEWLY = [(3, 3), (3, 8), (3, 15), (4, 7), (7, 4), (7, 16),
        (8, 3), (8, 9), (9, 4)]
h = t = 0
for i1, i2 in NEWLY:
    for a in (46, 50, 53, 57, 60):
        c = a + i1 + i2
        if c > 84:
            continue
        got = tuple(midi_of(f)
                for f in ruler.triad_pitches(tri_sig(a, i1, i2)))
        t += 1
        h += (got == (a, a + i1, c))
check("nine newly certified shapes hold", h == t,
        f"{h}/{t} across shapes never certified before")

# ---- 3. structure never fires without partials -----------------
# two PURE SINES a fifth apart: every sub-candidate's witnesses
# are dead (sines have no harmonics), so no rescue may fire and
# both voices must read exactly
tt = np.arange(int(0.5 * SR)) / SR
x = np.sin(2 * np.pi * hz(50) * tt) + 0.7 * np.sin(
        2 * np.pi * hz(57) * tt)
lo, hi = ruler.dyad_pitches(x)
check("witnesses stay silent for partial-free content",
        (midi_of(lo), midi_of(hi)) == (50, 57),
        f"sine dyad read ({midi_of(lo)}, {midi_of(hi)})")

# ---- 4. the session-50 phantom score reads clean ---------------
# THE regression set: these 12 beats produced every measured
# phantom (fracs 0.06-0.54, all struct-dead) that size could not
# block without exiling true rescues
NB, BEAT = 12, 0.6
PHANTOM_SCORE = [(50, 53, 57), (53, 57, 60), (48, 52, 55),
        (45, 48, 55), (45, 48, 52), (48, 52, 55), (45, 48, 52),
        (47, 50, 57), (50, 53, 57), (45, 48, 55), (45, 52, 59),
        (45, 52, 60)]


def render_score(score, nb, beat, dur, t60, seed):
    loop = Loop(nb * beat, seed=seed)
    for k, tri in enumerate(score):
        for v, pan in zip(tri, (-0.4, 0.0, 0.4)):
            loop.add(k * beat, stereo(pluck(hz(v), dur, t60=t60,
                    damp=0.3, seed=k * 3 + v) * 0.5, pan))
    return loop.master(lp_hz=7000.0, drive=1.15)


def recover(mix, nb, beat):
    mono = np.concatenate([mix, mix]).mean(axis=1)
    beats = {}
    for tt in ruler.onset_times(mono, min_sep=beat * 2 / 3):
        k = int(round(tt / beat))
        if abs(tt - k * beat) <= 0.08:
            beats.setdefault(k % nb, tt)   # e49: wrap the index
    got = []
    for k in sorted(beats):
        a0 = int((beats[k] + 0.02) * SR)
        seg = mono[a0:a0 + int(0.5 * SR)].copy()
        fd = int(0.04 * SR)
        seg[-fd:] *= np.linspace(1, 0, fd)
        got.append(tuple(midi_of(f)
                for f in ruler.triad_pitches(seg, 60.0, 2000.0)))
    return beats, got


mix = render_score(PHANTOM_SCORE, NB, BEAT, 0.65, 0.5, 50)
beats, got = recover(mix, NB, BEAT)
hits = sum(g == PHANTOM_SCORE[k] for g, k in zip(got, sorted(beats)))
check("the phantom score reads clean", len(beats) == NB
        and hits == NB, f"{hits}/{NB} blind on the score whose "
        f"phantoms defined the blind spot")

# ---- 5. the piece: dorian vamp on the reclaimed chords ---------
# root-position triads only — the texture the nine-shape set
# could not spell. G MAJOR is the dorian signature: IV with a
# raised sixth degree (B natural over a D minor home).
Dm = (50, 53, 57)
G = (55, 59, 62)          # (4,3): reclaimed
C = (48, 52, 55)          # (4,3): reclaimed
F = (53, 57, 60)          # (4,3): reclaimed
Em = (52, 55, 59)
Am = (45, 48, 52)
VAMP = [Dm, Dm, G, G, Dm, Dm, C, G, F, G, Am, Em, Dm, G, Am, Dm]
DORIAN = {2, 4, 5, 7, 9, 11, 0}
assert all(v % 12 in DORIAN for tri in VAMP for v in tri)
VB, VBEAT = 16, 0.75

vamp_mix = render_score(VAMP, VB, VBEAT, 0.85, 0.6, 51)
check("seam", ruler.seam_rank(vamp_mix) <= 0.999,
        f"p{100 * ruler.seam_rank(vamp_mix):.2f}")
beats, got = recover(vamp_mix, VB, VBEAT)
check("beat grid recovered", len(beats) == VB,
        f"{len(beats)}/{VB} beats claimed by onsets")
hits = sum(g == VAMP[k] for g, k in zip(got, sorted(beats)))
check("the vamp reads blind", hits == VB, f"{hits}/{VB} exact")
n_major = sum(1 for g in got
        if (g[1] - g[0], g[2] - g[1]) == (4, 3))
check("the major IV is named blind", n_major == sum(
        1 for tri in VAMP if (tri[1] - tri[0],
                tri[2] - tri[1]) == (4, 3)),
        f"{n_major} root-position major triads recovered "
        f"(G, C, F — impossible under the nine-shape set)")
pcs = {v % 12 for g in got for v in g}
check("recovered notes stay in D dorian", pcs <= DORIAN,
        f"classes {sorted(pcs)}")

out = np.concatenate([vamp_mix, vamp_mix])
wav = os.path.join(outdir, "e51_exiles.wav")
write_wav(wav, out)
ruler.report(out, "exiles")
subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", wav,
        "-q:a", "5", wav.replace(".wav", ".ogg")], check=True)

print("ALL RULERS PASS" if not fails else f"FAILED: {fails}")
sys.exit(1 if fails else 0)

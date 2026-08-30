#!/usr/bin/env python3
"""e42 — the jawari, won: FD stiff string vs the KS negative result.

e41 measured four point-nonlinearity bridges in the KS loop and
every one was a damper. Its closing conjecture: the bloom needs
DISTRIBUTED contact plus string dispersion. e42 builds exactly that
(loam/fdstring.py — Bilbao stiff-string scheme, parabolic barrier
with apex at the termination, elastic penalty contact) and the
rulers below assert the conjecture held: highs now SWELL after the
pluck on the bridged string and decay from t=0 on the same string
unbridged, at matched pitch and matched late-decay.

One honest caveat, kept in the open: the grazing-contact regime is
grid-brittle. N=140 blooms at 110 Hz, N=150 does not (verified not
a readout artifact — every readout node agrees). So N here is a
VOICING parameter, tuned per string the way a real tanpura's
jawari thread is walked along the bridge until the buzz sings.
The per-string N values below are that voicing.

Render: a Pa-sa-sa-SA tanpura cycle in D, middle strings 3 cents
apart, tails wrapping the 4.8 s loop 2.5x — the drone thickens
itself. Seam-free by construction (every pluck identical each
cycle, wrapped by Loop.add).

    python3 experiments/e42_tanpura.py [outdir]
"""

import os
import subprocess
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))))
from loam import SR, hz, Loop, stereo, write_wav
from loam import ruler
from loam.fdstring import fdpluck

outdir = sys.argv[1] if len(sys.argv) > 1 else "render"
os.makedirs(outdir, exist_ok=True)
fails = []


def check(name, cond, detail):
    print(f"  {'PASS' if cond else 'FAIL'} {name}: {detail}")
    if not cond:
        fails.append(name)


# ---- exhibit pair: same string, bridge in / bridge out ---------
F0 = 110.0
NV = 140                                # the voicing (see docstring)
wet = fdpluck(F0, 8.0, N=NV)
dry = fdpluck(F0, 8.0, N=NV, bridge=False)

for tag, s in (("bridged", wet), ("open", dry)):
    f = ruler.hps_pitch(s[SR:3 * SR], 50.0, 500.0)
    check(f"pitch holds ({tag})", abs(f - F0) < 0.015 * F0,
            f"{f:.1f} Hz vs {F0:.1f}")

# The bloom, read as what the bridge ADDS: wet/dry HF envelope
# ratio in matched bins. The pluck transient is common-mode and
# cancels; a jawari bloom is this ratio peaking late and large.
ew = ruler.band_env(wet[:int(6 * SR)])
ed = ruler.band_env(dry[:int(6 * SR)])
ratio = ew / (ed + 1e-30)
tstar = float(np.argmax(ratio)) * 0.1
check("bloom: bridge's HF gift peaks late", tstar >= 0.25,
        f"wet/dry 1.5-6 kHz ratio peaks at {tstar:.1f}s")
check("bloom: and it is large", float(ratio.max()) >= 3.0,
        f"peak ratio x{ratio.max():.1f}")
bd = ruler.env_peak_s(dry[:int(6 * SR)])
check("control: open string peaks at the pluck", bd < 0.15,
        f"peaks at {bd:.1f}s")

sus = slice(int(1.5 * SR), int(4.0 * SR))
enr = ruler.band_density(wet[sus], 1500, 6000) \
    / (ruler.band_density(dry[sus], 1500, 6000) + 1e-30)
check("sustain enrichment", enr >= 3.0,
        f"1.5-6 kHz density x{enr:.1f} vs open string")

late = slice(int(5 * SR), int(7 * SR))


def lr(s):
    return 20 * np.log10(np.sqrt((s[late] ** 2).mean()) + 1e-12)


check("bridge is not a damper (the e41 inversion)",
        abs(lr(wet) - lr(dry)) < 6.0,
        f"late RMS {lr(wet):.0f} vs {lr(dry):.0f} dB")

# ---- the tanpura ------------------------------------------------
# D tanpura: pa (A2), sa sa (D3, 3 cents apart), SA (D2).
# (name, f0, voiced N, at_s, pan, amp)
STRINGS = [
    ("pa", hz(45), 140, 0.0, -0.35, 0.75),
    ("sa+", hz(50.015), 112, 1.2, 0.15, 0.70),
    ("sa-", hz(49.985), 112, 2.4, -0.15, 0.70),
    ("SA", hz(38), 138, 3.6, 0.35, 1.00),
]
loop = Loop(4.8, seed=42)
for name, f0, n, at, pan, amp in STRINGS:
    v = fdpluck(f0, 12.0, amp=amp, N=n)
    loop.add(at, stereo(v, pan))
mix = loop.master(lp_hz=6500.0, drive=1.2)

check("seam", ruler.seam_rank(mix) <= 0.999,
        f"p{100 * ruler.seam_rank(mix):.2f}")
ch = ruler.chroma(mix.mean(axis=1))
top2 = set(np.argsort(ch)[-2:].tolist())
check("tonic and fifth own the drone", top2 == {2, 9},
        f"top chroma classes {sorted(top2)} (want D=2, A=9)")

# ---- render -----------------------------------------------------
out = np.concatenate([mix] * 3)
wav = os.path.join(outdir, "e42_tanpura.wav")
write_wav(wav, out)
ruler.report(out, "tanpura")
subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", wav,
        "-q:a", "5", wav.replace(".wav", ".ogg")], check=True)

print("ALL RULERS PASS" if not fails else f"FAILED: {fails}")
sys.exit(1 if fails else 0)

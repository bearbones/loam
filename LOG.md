# loam — log (newest at top)

## 2026-07-30 — play session 2: drums.py, the simulated kit

The classic analog drum recipes as library voices (every song so
far hand-rolled its own kick): pitch-drop kick with band-limited
beater click, two-tone + wire-band snare, 808 hat (six-square
inharmonic cluster through a high bandpass), 808 clap (three fast
bursts riding a fourth), tom/conga with band-limited skin/slap,
540+800 Hz square-pair cowbell, rim, shaker. e02: per-voice
spectral-centroid inspection + an 8-bar groove @102.

Lessons measured, not guessed:
- Raw noise transients POISON the centroid: first kick read 3913 Hz
  (a hi-hat number) from 4 ms of unfiltered click; band-limiting
  the click dropped it to 617 Hz. Same fix tom 5164->873,
  conga 5979->1290. Centroid inspection catches what peak/RMS miss.
- Equal-power pan 0.55 is only ~1.6 dB of channel difference —
  "hard" panning must approach ±1 (0.85 here) to decorrelate.
- A drums-only loop measures mono-ish (corr 0.82 >250Hz) BECAUSE
  the snare/clap backbone belongs in the center; alternating
  hat/shaker pans are the width that actually registers. Judge
  width targets per-material, not one number for everything.

## 2026-07-30 — play session 1: the kit grows six limbs

Research: PADsynth (Nasca / ZynAddSubFX docs), FDN reverb design
(Jot via Smith's PASP), modal tables (measured bell analysis;
marimba bars tuned 1:4:10, xylophone 1:3:6; church bell
hum/prime/tierce/quint/nominal = 0.5/1/1.2/1.5/2).

New modules, each verified numerically before commit:
- pads.py — PADsynth: Gaussian-band spectra on the loop's own DFT
  grid = seam CANNOT exist; independent phase draws per channel =
  free decorrelated stereo; formant_amps + vowel tables = seamless
  choir. (seam_report upgraded to percentile-rank of the wrap step.)
- modal.py — strike/bow over mode tables (bell, church bell,
  marimba, xylophone, glass, wood). Fundamentals land exact.
- strings.py — Karplus-Strong + Jaffe-Smith (pick-position comb,
  damping blend, fractional-delay tuning), period-block vectorized.
- space.py — 8-line Householder FDN reverb (mutually-prime delays,
  t60-calibrated, block-vectorized: 3s in 0.02s; loop-safe via
  double-pass warm) + circular tape echo with cycle-quantized wow.
- shape.py — wavefold (animatable drive), chebyshev (weights[k] =
  harmonic k+1, exact on a sine), bitcrush, pre-emphasized tape_sat.
- grain.py — wrapped Hann grain clouds; +12 into the FDN = shimmer.

Showcase: songs/reliquary.py — "Reliquary", 72s, D aeolian @60.
Choir bed mouths oh->ah across the loop, church bells (the tierce
supplies the minor third), one psaltery sentence with its rest and
low answer (standing grammar), bowed glass in the rests, folded
drone breathing, faint +12/+19 shimmer, everything in the FDN room.
seam p24 (clickless), stereo corr >250Hz = +0.056, peak 0.900.

## 2026-07-30 — spin-off

Director: "spin off the music composition library to its own repo,
and take the next few hours just playing around with new ideas for
sound transformations, effects, simulated samples, and so on. you
can look up research papers too."

Extracted the shared engine from marrow/dev/music/hermits.py into
`loam/` (SR, hz, Loop, stereo, ad_env, write_wav; added
seam_report). Moved the three composition scripts to `songs/`;
hermits.py now imports the library, the two elders stay as written.
Determinism check: loam render of the hermit suite is byte-identical
to a render from the original marrow script. MARROW keeps the .oggs.

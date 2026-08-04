# loam

A headless music composition library. Python + numpy/scipy, no DAW,
no samples, no audio server — compositions are scripts, renders are
seamless loops (unless you ask otherwise).

Grown inside [MARROW] (a Godot game whose every sound is synthesized
in code); spun off to its own repo 2026-07-30 at the director's word,
then grown sixteen modules in one night of play.

## The library

The engine (`loam/__init__.py`): `Loop` (the seamless canvas —
cycle-quantized oscillators, tail-warmed IIR filters, wrapped event
tails, seeded determinism), `stereo`, `ad_env`, `write_wav`,
`seam_report`.

Instruments:

- `pads` — PADsynth (Nasca): Gaussian-band spectra on the loop's own
  DFT grid; seam cannot exist. Formant-shaped amps = seamless choir.
- `modal` — struck/bowed mode tables: bells, church bell, anvil, marimba,
  xylophone, glass, wood; `gong()` blooms (energy visibly cascades
  upward after the strike).
- `strings` — Karplus-Strong pluck/strum (Jaffe-Smith refinements)
  and `sympathetic()`, the taraf bank that hums along with anything.
- `winds` — waveguide flute/ney (Cook) that TUNES ITSELF BY
  LISTENING: renders, measures (harmonic product spectrum), reseeds
  wrong modes, secant-retunes wrong pitch. Overblow is physical.
- `voice` — source-filter singing: Rosenberg glottal pulse through
  morphing formants; portamento, jitter, delayed vibrato.
- `drums` — the analog recipes: 808 six-square hat, three-burst
  clap, square-pair cowbell, pitch-drop kick, toms, congas, shaker.
- `analog` — polyBLEP saw/pulse, JP-8000 supersaw, Moog ladder
  (tanh Huovilainen; self-oscillates above res 1).
- `texture` — Farnell-style procedural rain / wind / fire, plus
  van den Doel bubbles: Minnaert-resonance damped sines with the
  signature rising chirp; `bubbles()` populations (fizz, glugs,
  simmer), `bubble()` doubles as a pitched plink voice.

Transformations & effects:

- `space` — Jot FDN reverb, circular tape echo, and synthesized-IR
  convolution (`ir_room`/`ir_tank`/`ir_bone` + `convolve_loop`,
  circularly seamless by construction).
- `spectral` — phase-vocoder freeze / stretch / cross-synthesis.
- `shape` — wavefolder, Chebyshev harmonic painting, bitcrush,
  tape saturation.
- `mod` — chorus, flanger, phaser (cycle-quantized LFOs).
- `grain` — wrapped granular clouds; +12 into the reverb = shimmer.
- `shift` — Bode frequency shifter (circular Hilbert), ring mod,
  `barber()` endless staircase.
- `dyn` — envelope follower, compressor, sidechain duck, transient
  shaper, lookahead limiter.
- `lofi` — gramophone and worn tape: age as an effect.
- `rhythm` — Euclidean rhythms (Bjorklund/Toussaint), swing, and
  the scale/maqam tables.

`songs/` — finished pieces (The Bore, Reel Home, the hermit suite,
Reliquary, The Long Stair). `experiments/` — one idea per script,
rendered and measured. `render/` — output audio (gitignored).
`LOG.md` — what was tried, what it sounded like, what was learned.

## The seam-craft rules

1. Continuous oscillators quantize to whole cycles per loop.
2. IIR filters warm up on the signal's own tail — FILTER STATE
   seams even when the signal doesn't.
3. Event tails wrap — bar 1 already contains the reverb of the
   final bar. Circular convolution does this by definition.
4. Deterministic: seeded RNG, no wall clock. Quantize TEST inputs
   too, or innocent modules fail seam checks.

## Verify by numbers — and distrust the ruler

The night's recurring lesson: the instrument is easy, the ruler is
hard. Standing rules, each earned by a wrong measurement:

- Seam: `seam_report` gives the wrap step's PERCENTILE RANK in the
  adjacent-delta distribution (a mean comparison lies on bright
  material).
- Measure a processor on its OWN BUS, never in the mix — the kick
  owns the very windows where the duck acts; the drone sits under
  the ney's pitch window.
- Pitch: argmax lies when a harmonic edges the fundamental; use the
  harmonic product spectrum.
- Spectral centroid: POWER-weighted, or thousands of tiny high bins
  outvote three loud low ones.
- Transients: crest factor, not energy — peaks, not sums.
- Per-call peak normalization inverts cross-call energy comparisons
  (pass norm=False).
- Stereo width above ~250 Hz, judged PER MATERIAL — a centered
  drum backbone is correct, not a failure.
- Feedback tuning loops need the plant's measured gain (secant),
  not unit-gain corrections.

[MARROW]: ../marrow

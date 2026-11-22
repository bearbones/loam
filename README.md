# loam

A headless music composition library. Python + numpy/scipy, no DAW,
no samples, no audio server — compositions are scripts, renders are
seamless loops (unless you ask otherwise).

Grown inside [MARROW] (a Godot game whose every sound is synthesized
in code); spun off to its own repo 2026-07-30 at the director's word,
then grown sixteen modules in one night of play.

## The Wayfarer’s Cabinet

Play twenty acoustic instruments and five imaginary shipboard synthesizers
in the Godot gallery with `godot --path harness -- --cabinet`. Each has a
solo, an animated GLB, a Python voice and an SFZ patch. The models carry
details you can inspect in motion, from the koto’s thirteen picking levers
to the reader and rotating star chart on the Pulsar Navigation Loom.
[Instrument list, controls and composition guide](docs/wayfarers-cabinet.md) ·
[Recital, workshop close-ups and animated models](https://github.com/bearbones/loam/releases/tag/wayfarers-workshop-finish-2026-11-22) ·
[SFZ instrument bank](https://github.com/bearbones/loam/releases/download/wayfarers-cabinet-2026-11-22/wayfarer-samplers.zip)

## The library

The engine (`loam/__init__.py`): `Loop` (the seamless canvas —
cycle-quantized oscillators, tail-warmed IIR filters, wrapped event
tails, seeded determinism), `Take` (the one-shot canvas: tails run
past the end instead of folding into bar 1), `stereo`, `ad_env`,
`write_wav`, `seam_report`.

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
- `ruler` — the consolidated measurement kit: every earned rule
  below as a callable default (HPS pitch, power-weighted centroid,
  band power DENSITY, crest, width >250 Hz, pulse rate read in the
  fast-decaying band, seam rank, RMS contour, `report()`; for
  scores: `score_recall`, `plan_consistent`, `onset_pitch`,
  `onset_lock`).
- `score` — the piece as a machine's score: `Instrument` /
  `Mechanism` / `Actuator` geometry, a `Score` that records every
  pluck, rake and strike into per-mechanism stems, plans each note
  for an arm ([t_move, t, t_free]) and REFUSES what no arm can
  reach — `can_play` is the question the composer asks before
  writing. Exports `loam-score/1` (score.json + stems + shapes).
- `fdstring.fdshape` / `shape_library` — the finite-difference
  string's displacement captured as frames (nodes x rate_hz), the
  vertex data a game animates strings with; licensed for reuse by
  linearity and f0-invariance in normalized coordinates.

`songs/` — finished pieces (The Bore, Reel Home, the hermit suite,
Reliquary, The Long Stair, The Alembic, The Chamber). `experiments/` —
one idea per script, rendered and measured. `render/` — output audio
(gitignored). `LOG.md` — what was tried, what it sounded like, what
was learned.

`docs/chamber-spec.md` — the Resonant-Chamber programme: a machine
(strings, bars, arms) as a constraint the composer asks before
writing, and the export a game engine animates from. `harness/` —
a Godot 4.7 project that reads that export and draws the annotated
track over the strings vibrating with their baked shapes
(`godot --path harness`; `godot --headless --path harness -s
dev/test_load.gd` prints `HARNESS: PASS`).

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

## Clockwork performance

The harness opens The Chamber in a circular recital hall, with carved alabaster
harps, score-driven mechanical players and moving cue cameras. The transport
shows the piece's dynamics and section changes. Scrub the score or choose a
close-up to watch the fingers, strings and mallets at work. `godot --path harness -- --expanded` adds glass bells and temple blocks
(after `python3 songs/clockwork.py`). The original diagnostic is available as
`godot --path harness res://main.tscn`. See [the build guide](docs/clockwork-build.md)
for editable Blender models, captures and validation, [articulated
arms](docs/articulated-arms.md) for the linkage recipes, clearance rulers and
the planner's arm-width rule, and [the sound-suite
backlog](docs/clockwork-todos.md) for scoped follow-up work.

## Overcrank

Run the drum feature from a checkout with Git LFS assets and Godot 4.7.

```sh
godot --headless --path harness --import
godot --path harness -- --drums
```

The seated automaton plays a five-piece kit with two crashes, a ride and a pedal hi-hat. An original 148 BPM solo moves from an open-handed backbeat into a half-time break, sextuplet tom fills and a two-stick crash ending. The stick work takes its cue from Steve Moore’s showmanship. [The Mad Drummer](https://www.themaddrummer.com/)

Space pauses or resumes. Home restarts. The default film follows the arrangement. Add `--view=wide` for one continuous audience view, `--view=heads` to watch the sticking from above, or `--view=pedals` to watch the footwork. The model, score and stereo audio ship with the demo.

```sh
python3 songs/overcrank.py                                  # rebuild the master, score and sampler kit
blender -b -t 3 --python-exit-code 1 -P tools/build_drum_kit.py
ASSET=drums tools/render_film.sh                            # 1080p60 with sound
godot --headless --path harness -s dev/test_drum_recital.gd -- --silent
```

The model exports in a seated home pose for ordinary glTF viewers. In Godot, each scored hand strike lands the round hickory bead on a drumhead or on a measured point of the rocking cymbal. The bass beater and hi-hat clutch share the feet’s score. The stereo master combines Loam’s kick, snare and hat synthesis with finite-difference membranes and inharmonic cymbal modes.

For a sampler or DAW, open `Overcrank.sfz` from `render/overcrank/overcrank-kit.zip`. It maps eleven articulations to General MIDI percussion keys, rotates three takes per articulation, and chokes the open hat on a close or pedal stroke. In Python, `loam.drumkit.hit("snare", velocity=.8, take=1)` returns a mono strike.

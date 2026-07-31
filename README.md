# loam

A headless music composition library. Python + numpy/scipy, no DAW,
no samples, no audio server — compositions are scripts, renders are
seamless loops (unless you ask otherwise).

Grown inside [MARROW] (a Godot game whose every sound is synthesized
in code); spun off to its own repo 2026-07-30 at the director's word.
The game keeps the rendered `.ogg`s; the instruments live here.

## Layout

- `loam/` — the library. Seam-craft core (`Loop`, `stereo`, `ad_env`,
  `write_wav`, `seam_report`) plus whatever instruments and effects
  the experiments graduate.
- `songs/` — finished pieces. `the_bore.py` and `reel_home.py` are
  self-contained (the library grew OUT of them, kept as written);
  `hermits.py` (The Librarian / The Apothecan / The Apparatuan)
  imports the library.
- `experiments/` — the playground. One idea per script, rendered and
  measured. Graduates into `loam/` when it earns it.
- `render/` — output wavs/oggs (gitignored).
- `LOG.md` — what was tried, what it sounded like, what was learned.

## The seam-craft rules

1. Continuous oscillators quantize to whole cycles per loop
   (`Loop.q`) — the seam is phase-exact by construction.
2. IIR filters warm up on the signal's own tail
   (`Loop.filt_circular`) — sample 0 exits a settled filter.
3. Event tails wrap (`Loop.add` is modulo) — bar 1 already contains
   the reverb of the final bar.
4. Deterministic: seeded RNG, no wall clock.

## Verify by numbers, not vibes

- Seam: `seam_report` — |first−last| vs typical adjacent delta.
- Loudness: RMS contour over the arc, peak after master.
- Stereo: L/R correlation measured ABOVE ~250 Hz (full-band
  correlation is bass-dominated and lies).

[MARROW]: ../marrow

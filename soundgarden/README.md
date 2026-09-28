# Soundgarden

A local sound-search instrument for Loam. Explore a continuous ten-dimensional
struck-resonator recipe through an XY pad whose axes blend any number of
parameters, weighted by what a measured descriptor notices; listen on an
editable note loop; match a recording; keep discoveries. A separate offline
worker finds diverse starting sounds and probes useful exploration ranges.
Neither process needs internet access.

## Play

From the Loam repository:

```sh
python3 -m soundgarden.server
```

Open **http://127.0.0.1:8765** in a browser. The only Python dependencies are
Loam's existing NumPy and SciPy. There is no JS build step, CDN, account, or
model download. Keep the Python server running while using the instrument.
Use `--port 8766` if that port is occupied. The server binds only to loopback.

- Press **Play loop**, then drag in the blue field. While stopped, dragging
  auditions a single C4. Arrow keys move the pad; Shift makes finer changes.
- **Keep & turn field** preserves the sound you are hearing, recenters it, and
  chooses two new random orthogonal directions. The directions mix multiple
  synthesis parameters; they are not two raw coordinates.
- **Exploration range** controls how far a gesture travels. **Undo** restores
  the previous field, including its directions, position, range, and blend.
- **Field blend** sets how many recipe parameters each pad axis mixes. At 1,
  each axis is a single parameter and the pad explores exactly two. At 10,
  each axis blends all ten with near-even weights and random signs. Changing
  it turns the field around the current center.
- **Even by ear** asks the local server, on the next turn, to weight each
  blended parameter by how much a measured descriptor changes with it here,
  and to suggest a range. The recipe panel then shows a bar per parameter.
  Axis labels name the parameters that change the sound most. With the box
  off, or if the server is unreachable, the page draws the plane itself.
- **Hear starting sound** toggles comparison against this field's center.
- Click in the piano roll to place a note. Click that note again for a rest.
  The phrase is one monophonic bar of sixteen sixteenth-note steps, C4–C5.
  Arrow keys navigate its cells; Enter/Space toggle a cell. Tempo is 40–200 BPM.
  Natural release tails may overlap subsequent notes and cross the bar line.
- **Match a sound file…** takes a PCM WAV (up to 8 MB; the first 3 s after
  the onset are used), estimates its pitch, and searches starters plus the
  discovery journal for the closest recipes, refining the best few. They are
  added to Starting points for this page load with their descriptor distance.
  Near zero means the resonator can make that sound; larger numbers mean "the
  closest it gets". This is a measured distance, not a listening test.
- **Save sound** stores a recipe, phrase, and tempo in your collection.
  Recalling a favorite restores all three. Saving does not train a model or
  automatically send your preferences to the exploration worker.
- The current field, last 100 field snapshots, phrase, volume, tempo, and up to
  100 favorites persist in browser storage. Under **The recipe**, export/import
  a JSON session to move it between browsers or preserve a portable copy.
  Browser storage belongs to that browser and port; clearing it removes saves.

Short renders are debounced by 140 ms and requested serially. A newer request
invalidates stale results. The previous buffers keep playing until a complete
new bank is decoded; existing note tails finish with their original sound.
This is sample replacement on future notes, not continuous audio-rate morphing.
Every pitch is synthesized separately, so transposing the phrase preserves
decay time. Playback stops when the tab is hidden; missed notes never pile up
after sleep. Output has a compressor and bounded waveshaper.

## Discover while offline

```sh
# A commute-length run. Add idle time between trials to reduce CPU duty cycle.
python3 -m soundgarden.explore --minutes 90 --pause-ms 250

# Short run to try the pipeline. max-trials includes already completed trials.
python3 -m soundgarden.explore --minutes 2 --max-trials 128
```

Run the same command again to resume. `--minutes` is a new wall-time budget for
each invocation, including sleep. Ctrl+C/SIGTERM finishes the current candidate
and publishes partial results. On Linux, a discharging battery at or below 25%
also ends the run; use `--battery-min 35` to keep more reserve or `0` to disable
that check. This is a single-candidate worker, not a system power governor; it
does not keep the machine awake or prevent sleep. Use a ventilated surface.

The default output is `render/soundgarden/` (already covered by Loam's render
ignore rule):

| File | Contents |
| --- | --- |
| `seeds.json` | Up to 12 selected seeds, metrics, descriptors, tested axes/ranges, provenance |
| `trials.jsonl` | Append-only recipe/measurement/descriptor checkpoint, flushed after each trial |
| `run.json` | RNG seed, synthesis version and hash, search and descriptor versions, NumPy version, rate |
| `<id>.wav` | C4 audition of a selected seed |
| `run.lock` | Prevents concurrent workers writing to this directory |

The worker retires WAVs from its preceding bank when they are no longer selected;
copy any audition you want to keep elsewhere. All candidate recipes remain in
the journal, so retired audio can be regenerated without another search.

The server reads this library when the page loads or when you press **Refresh**.
It includes four starter presets even without a generated library. No server
restart is needed when new discoveries are published.

Use `--output render/another-garden --seed 42` for a separate search and point
the server at it with `--library render/another-garden/seeds.json`. Changing
the synthesis source, seed, or NumPy requires a fresh output directory;
checkpoints fail closed rather than quietly mixing incompatible runs. Changing
only the search or descriptor code migrates the journal on resume: every
recorded recipe is re-rendered and must reproduce its recorded measurements,
which is a stronger check than a source hash. The runner doesn't modify
source files.

### What discovery means here

Candidates are uniform samples inside the bounded recipe space. At C4 we measure
energy-weighted spectral centroid, high-frequency energy fraction, the time by
which 95% of energy has sounded, crest factor, RMS, and peak, plus a descriptor:
24 mel bands averaged in 8 log-spaced time windows from 5 ms to 1.5 s, in dB
relative to the loudest cell. Whole one-shots already start/end at zero: we do
not apply a long Hann window that would erase the transient. The UI's "energy
decay" is the 95% energy time, **not T60**.

Candidates with nonfinite audio, excessive peak, or very low RMS are rejected.
An archive of up to 64 candidates is repeatedly reduced by farthest-point
coverage in a fixed-scale embedding of the four scalar features and the
descriptor grid. The final gallery contains diverse representatives of that
archive. This is an approximate acoustic diversity heuristic, not a learned
embedding, a perceptual distance model, a proof of global coverage, or a
musical-quality score.

For each accepted candidate, a full-blend, ear-weighted plane is drawn and both
axes are probed in both directions. The measured embedding differences set a
suggested pad range, and the per-parameter sensitivities are stored with the
seed. Later field turns in the page are measured on request (Even by ear) or
drawn locally. The recipe's ten coordinates control material ratios, ring,
brightness, damping, beating, mallet noise, attack softness, hollowing, bloom,
and drive. The resonator uses Loam's mode tables, sample rate, and pitch
convention with a new continuous synthesis function. It never peak-normalizes
individual renders.

### Beyond the named dimensions

`docs/soundgarden-abstract-space.md` records the discussion of exploring sound
as an abstract space and the three approaches built from it: perceptual
coordinates over the recipe (this instrument's blend, ear weighting, and file
matching), a sinusoidal-plus-residual model that turns any recording into a
morphable recipe (`python3 -m soundgarden.sms --demo`), and a small learned
latent with two decoders (`python3 -m soundgarden.latent --train 1500`). A
second latent uses a stationary tone as its primitive, 64 harmonics plus 24
noise bands with an additive decoder, trained on Loam's own tone makers
(`python3 -m soundgarden.tone --build --train --walk 8`). These are prototypes
with tests, not parts of the instrument.

## Reuse a discovery in Python

```python
import json
from pathlib import Path
from soundgarden.synth import render, wav_bytes

session = json.loads(Path("loam-soundgarden.json").read_text())
recipe = session["favorites"][0]["vector"]
Path("my-sound.wav").write_bytes(wav_bytes(render(recipe, midi=67)))
```

Recipes contain no code. The import boundary validates the version, numeric
ranges, axes, notes, history, and favorites. Session files do not execute scripts.

## Verification

```sh
python3 -m unittest soundgarden.test_soundgarden -v
node soundgarden/test_space.mjs
python3 dev_smoke.py
```

Tests exercise deterministic WAV output, pitch and envelope behavior, bounded
extremes, signal continuity, measurable parameter changes, starter diversity,
descriptor bounds and level invariance, pitch estimation, sensitivity, blended
planes at every slider step, WAV matching that recovers a rendered recipe,
HTTP/render equivalence, the plane and match endpoints, request validation,
identical discovery results after checkpoint resume (including a torn final
journal write), legacy journal migration that refuses altered measurements,
and the two prototypes' contracts. The JavaScript checks cover orthogonal and
blended planes, weights, parameter bounds, and unchanged sound at a recenter.
The UI has no runtime JavaScript dependencies.

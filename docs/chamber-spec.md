# The Chamber — loam as the authoring tool for a machine that plays music

Target: an Animusic-style instrument ("Resonant Chamber") rendered in
Godot. loam composes the music, synthesizes it, AND emits everything the
engine needs to move the machine — because loam is the thing that
decided every note, it can say which string, which arm, how hard, and
where along the string the pick landed. Godot becomes a pure playback
engine: no MIDI, no synthesis, no guessing.

The one structural gap loam had: no score. A song script computed an
event time inline (`beat_t(bar, beat)`) and mixed the chunk at once;
the time, pitch and voice were consumed into the buffer and forgotten.
This spec closes that gap and then builds on it.

Standing rule, inherited: every stage ships with a numeric claim
that a script checks. The instrument is easy; the ruler is hard.

---

## Stage 1 — the Score recorder  (`loam/score.py`, `loam.Take`)

`Take` — the one-shot canvas. `Loop` wraps event tails modulo the loop
length; a through-composed piece needs tails to RUN PAST the end. `Take`
is `Loop` minus the wrap: a pre-sized linear buffer with `tail_s` of
room after `dur_s`, same `add(t, chunk)` signature, `master()` and
`rng` the same. Existing `Loop` code is untouched.

`Score(canvas, name, bpm, seed)` — a recorder that sits between the
composer and the canvas:

    score.play(mech, t, chunk, midi=..., string=..., pan=..., amp=...,
               pick=..., dur=..., voice=..., **extra)

mixes `stereo(chunk*amp, pan)` into the canvas exactly as `canvas.add`
would (byte-identical: the test), ALSO into a per-mechanism stem
buffer, and appends an event:

    {t, mech, voice, midi, string, amp, pan, pick, dur, actuator?, ...}

`score.cue(t, kind, **data)` records without mixing — section marks,
camera cuts, anything the engine should know that has no sound.

`score.bus(mech)` — the mechanism's dry stem (a numpy array); a
composer may process a stem in place (e.g. print `sympathetic()` onto
it) — the recorder re-derives the master as the sum of stems at
export, so stem-level processing is heard.

`score.export(outdir)` writes `score.json` + `stems/<mech>.wav` +
(stage 3) `shapes.f32`. Master wav is the song's business (it owns the
room and the mastering chain) — `Score.mixdown()` returns the stem sum.

CLAIM (e97): a passage rendered via `Loop.add` and the same passage
via `Score.play` over an identical `Loop` are `np.array_equal`; the
sum of stems equals the canvas buffer to 1e-9; every event round-trips
through JSON with its time exact to the sample.

## Stage 2 — the instrument definition  (`loam/score.py`)

Data model, authored in Python, embedded in `score.json` as the single
source of truth for both loam (timbre) and Godot (geometry):

    Instrument(name, mechanisms=[Mechanism...])
    Mechanism(id, kind, material, strings=[StringDef...],
              actuators=[Actuator...], pos, restrike_s)
    StringDef(id, midi, pos, length, pick_default)
    Actuator(id, kind, reach=[string ids], approach_s, recover_s,
             travel_s, home)

`kind` ∈ {plucked, struck, raked}. `material` names a row of the
MATERIALS table (steel / nylon / bronze / rosewood / glass): loam's
synthesis parameters (`damp`, `t60`, `soft`, modal table) hang off it
so the composer writes `score.pluck(mech, t, string_id, ...)` and the
timbre follows the machine.

Geometry is honest but simple: strings are segments (`pos`, `length`
along the mechanism's `axis`); length ∝ 1/f scaled to the
mechanism's `span`. `pick` (0..0.5 along the string) is the SAME number
in both worlds: where the arm touches is where the Jaffe-Smith comb
notches.

### The playability solver — constraints in the composer

Animusic edited MIDI until the machine could play it. Here the machine
is a constraint the composer asks BEFORE writing a note:

    act = score.can_play(mech, t, string)   # -> Actuator or None
    if act: score.pluck(...)
    else:   # choose another note / drop / move

Timing model, per actuator: after contact at `t0` it is busy until
`t0 + recover_s`; it then travels `|i_from - i_to| * travel_s` (string
index distance) and winds up for `approach_s`, so

    feasible  iff  t - approach_s - travel >= free_at

Choice among feasible actuators: least travel, ties → earliest free.
A string also refuses a re-strike within `restrike_s` (the pick must
clear it). Raked events (`strings=[...]`, `spread_s`) occupy one
actuator once, spanning the run.

`play` assigns incrementally; if events arrive out of time order the
solver re-solves globally (time-sorted) at `finalize()`. Every event
exports its motion plan: `actuator`, `t_move` (= t - approach - travel),
`t` (contact), `t_free` (= t + recover), `from_string`. That IS the
keyframe plan the engine interpolates. Conflicts (no feasible actuator)
are recorded and exported — the song's ruler asserts zero.

CLAIM (e99): a synthetic dense passage with 3 overlapping arms — the
solver's plan is self-consistent (no actuator has overlapping busy
spans; travel accounted); the composer's `can_play` refusals match the
global re-solve; a passage written beyond capacity produces the
predicted conflicts.

## Stage 3 — string shapes from the simulation  (`loam/fdstring.py`)

`fdpluck` integrates the stiff-string PDE on N+1 nodes and holds the
full displacement field every step — then reads ONE node into audio and
discards the field. `fdshape(f0, dur, nodes, rate_hz, **kw)` runs the
same core and ALSO decimates the field: at every `SR/rate_hz` steps,
interpolate `u` onto `nodes` evenly spaced positions. Returns
`(audio, frames[F, nodes] float32, scale_m)`, frames normalized to
max|u| = 1.

Why a library, not per-note: with `bridge=False` (no jawari) the
system is LINEAR, so amplitude is a scalar and the normalized shape
sequence depends on `pick` (and weakly on `kappa`, `sig1`). And the
initial triangle and the modal decomposition are f0-invariant in the
normalized coordinate. So: a small library keyed by pick
(`shape_library(picks, ...)`), each clip ~2 s at 120 Hz × 24 nodes.
Godot scales by string length, amplitude, and plays the clip in
real seconds (decay is set by sig0, in seconds — not in periods).

Export: `shapes.f32` (raw little-endian float32, frames × nodes,
clips concatenated) + `shapes` block in `score.json` with per-clip
`{id, pick, nodes, rate_hz, frames, offset, scale_m, t60_s}`. Each
event names its clip by nearest pick.

CLAIMS (e98):
- frame 0 is the triangle with apex at `pick` (argmax node ≈ pick).
- the spatial sine-series of the field has its NULL where Jaffe-Smith
  says: pluck at x=1/4 → mode 4 ≪ modes 3 and 5 (the pick-position comb,
  seen rather than heard).
- the visual decays as the audio does: t60 of the frame envelope vs
  `ruler.decay_t60` of the readout, within tolerance.
- f0-invariance: normalized envelopes at 110/220/440 Hz agree — the
  claim that licenses the library.

## Stage 4 — the piece  (`songs/chamber.py`)

A through-composed ~75 s piece for a designed machine, "the chamber":

- `harp`   — 16 plucked steel strings, D dorian over two octaves, three
             pick arms with overlapping reach (0–7, 4–11, 8–15).
- `rake`   — a 5-string bronze cluster, one raking bar: chords as one
             event sweeping strings with `spread_s` (from PLAYERS M2 a
             roll at its own `onsets` along the comb's path, `spread_s`
             its end over n − 1).
- `bars`   — 8 rosewood bars (modal MARIMBA), two mallets.
- `chamber`— the resonator: `sympathetic()` driven by the harp+rake
             stems, printed to its OWN stem (no events — a bus that
             hums; the engine can show the chamber breathing).

Form: unfold (sparse, arms one at a time) → pulse (euclid patterns,
arms interleaving) → rake and bars → coda (the chamber rings out).
Cues: section marks and camera cuts on phrase boundaries.

Written under the solver: every note asked for first; refusals counted
and exported (`stats.refused`). Stems dry; the master alone goes
through `ir_room` + `convolve_tail`, then `master()`.

## Stage 5 — rulers for a score  (`loam/ruler.py`, and the song)

New in ruler: `score_recall(x, times, tol_s, min_sep)` — for events
isolated by ≥ `min_sep` (findable), the fraction with a detected onset
within `tol_s` (onset latency ≈ frame/2 allowed); `plan_consistent(
events)` — no actuator busy-span overlap, `t_move < t < t_free`.

Song claims:
- zero solver conflicts; ≤ 5% of asked notes refused.
- plan consistent (also the engine's precondition).
- stems sum to the dry canvas (1e-9); master peak 0.90; tail decays
  to silence (last 0.5 s < −60 dBFS).
- harp stem: onset recall ≥ 0.9 on findable events; pitch on isolated
  events within ±25 cents of the written midi.
- chamber stem is DRIVEN: band-env correlation with harp stem > 0.5,
  and its chroma crowns D.
- bars stem: `mode_freqs` land 1:4 (marimba tuning heard on the bus).

Also: a reference plot (`Score.plot(path)`, matplotlib) of the
annotated track — lanes per mechanism, events as ticks, motion spans
as bars, cues as lines — the image the Godot harness must match.

---

## The Godot harness  (`harness/`, Godot 4.7)

A debug visual, not the game. Reads `score.json` (default
`../render/chamber/`, or `--score=<path>`) and the stems/shapes
alongside; no import step (runtime `AudioStreamWAV.load_from_file`,
`PackedByteArray.to_float32_array`).

Views:
- TRACK: lanes per mechanism; events as ticks (pitch → vertical
  position, amp → tick height, actuator → color); motion spans
  `[t_move, t]` and recover `[t, t_free]` as bars under the tick;
  cues as full-height lines with labels; playhead driven by the
  audio clock (`get_playback_position() + get_time_since_last_mix()
  - get_output_latency()`).
- STRINGS: each mechanism's strings drawn from the geometry;
  on each event the string plays its shape clip (scaled by
  length, amp) — the vertex data the game will use, seen early.
- Stem mute/solo (per-mechanism `AudioStreamPlayer`s in lockstep).

`dev/test_load.gd` (headless): loads the export, checks event count,
shapes file size = Σ frames×nodes×4, plan consistency — prints
`HARNESS: PASS`. Capture path: `SHOT=<png> godot --path harness`
saves the viewport for the operator.

Out of scope this session: arms/IK, cameras, materials — the game.

**Since 2026-09-28 the motion is part of the export too:** `formlab/bake.py`
writes `<asset>.motion.json` + `.motion.bin` (`loam-motion/1`) beside
`score.json` — every arm's pins, the hinged heads' flips, the assembly's
shudders, the clicks and the pawl's tooth table, sampled from `formlab.rig`
against a model manifest — and the harness interpolates it. That is this
spec's promise kept for the machine as well as the music: the engine plays
back, it decides nothing.

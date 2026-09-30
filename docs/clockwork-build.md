# Clockwork Chamber

The current performance uses editable Blender models and rigid mechanical pivots, exported as GLB; Godot plays the performance back from a motion bake of `formlab.rig` (below) at any requested time. There is no physics simulation or MIDI inference. The default is exposed clockwork: walnut structures, satin brass linkages and carriages, dark steel joints, felt mallets and brass plectra on swan-neck shanks.

## Build and play

From the repository root:

```sh
python3 songs/chamber.py
python3 songs/clockwork.py
blender -b -t 2 -P tools/build_clockwork.py
blender -b -t 2 -P tools/build_clockwork.py -- render/clockwork/score.json clockwork_expanded
python3 tools/bake_motion.py      # the build does this too; needed alone after a score re-export
godot --headless --path harness --editor --import --quit
godot --path harness
# The expanded arrangement: four glass bells and three temple blocks.
godot --path harness -- --expanded
# Original 2D diagnostic:
godot --path harness res://main.tscn
```

Editable source files live in `models/`, outside Godot's import tree so headless imports never need to launch Blender. `harness/assets/` contains GLBs and geometry manifests. Rebuilding derives contact geometry and reachable rail extents from the score. Source rigs are posed at home in Blender; the performance rig is `formlab/rig.py` and the harness plays a bake of it (see "The motion bake"). Re-running the model generator overwrites generated assets, so preserve hand edits separately.

**What git keeps.** The `.blend` files are build outputs and are not tracked
(since 2026-09-28): `blender -b -t 2 -P tools/build_clockwork.py` regenerates
them next to the GLBs. The GLBs, their manifests and the textures stay in git
LFS so a fresh clone runs the harness without Blender, but each rebuild is
~200 MB of LFS, so commit rebuilt GLBs only at a milestone (a finished plan, a
replan), not with every geometry tweak. The commits between the last push
(2026-09-12) and this rule were rewritten before they were first pushed so that
each carries forward the previous uploaded asset instead of its own
intermediate build; those intermediate builds (and the old `.blend` files)
were never uploaded, and the branch `backup/pre-lfs-rewrite-main` in the
original working copy keeps them.

## The motion bake

`formlab/rig.py` is the one implementation of the motion — the planner's
travel costs, the stepped and servo vocabularies, the recoil bus, the IK. The
harness does not re-implement any of it: `tools/bake_motion.py` (and the last
step of every build) samples the rig into `loam-motion/1`, written next to the
score as `<asset>.motion.json` (header) and `<asset>.motion.bin` (float64
times, float32 rows), and `harness/motion_bake.gd` (`MotionBake`) interpolates
it. A time grid of 240 Hz plus every contact and every corner of the path as a
row of its own, and rows packed through each ratchet click: contacts land to
float32 (2.4e-7 m), and between rows no pin strays more than 3.4 mm from the
rig mid-slew. The pawl's angle is a function of rail position, not time, so the
header carries one tooth of it and the harness looks it up at the baked x. A
hinged head's felt face is derived from the tip and the baked flip angle, so
the rendered head and the face it strikes with cannot drift apart. The header
fingerprints the score and the manifest; the harness refuses a stale bake and
prints the command that remakes it. `tools/test_bake.py` holds the bake to the
rig and the GDScript reader to `formlab.bake.Bake`. About 10 MB for The
Chamber, 20 MB for the expanded piece; like every export it lives in `render/`.

## Playback and inspection

Space pauses/resumes; Home starts a one-second pre-roll so the first contact has an approach. Left/right seek two seconds. The bottom slider scrubs. C cycles wide, harp, rake, bars, overhead and expansion views. Two inspection views follow the action for stills and clips: `--view=9` sits behind the string plane on the second harp arm's elbow (knuckle pins, crossheads, parallel bars) and `--view=10` frames the most recently plucked string from 45° off its pluck axis, latching for 1.5 s so a run of plucks does not throw it about; `--view=11` is a fixed close-up of the bar frame's treble end (rails, cord posts, resonator mouths); `--view=12` looks at the harp's neck from the string side, where the action plate, discs, bridge and tuning pins are; `--view=13` is the flywheel drive beside the harp (plummer blocks, pedestals, the belt to the cabinet's end); `--view=14` looks down the harp's string feet from the string side, where the eyelets sit on the ferrule mouths along the soundbox. A restores cue-directed cameras. T shows the existing annotated score. M switches the finished master and dry stems; 1–9 mute/unmute dry stems and select that audition mode. The default master is `chamber.wav` next to the score. Playback stops at the end rather than drifting past the tail.

```sh
SHOT=/tmp/chamber.png godot --path harness -- --camera=manual --view=0 --time=48
godot --path harness -- --capture=/tmp/chamber-frames --start=45.5 --seconds=8 --fps=30 --camera=manual --view=3
ffmpeg -framerate 30 -i /tmp/chamber-frames/%05d.png -ss 45.5 -i render/chamber/chamber.wav -t 8 -c:v libx264 -pix_fmt yuv420p -c:a aac /tmp/chamber.mp4
show /tmp/chamber.mp4 'Mallet approaches, contacts and recovery'
```

Capture samples deterministic score times; it does not record wall-clock frame delivery. `--size=WxH` renders at exactly that size whatever size the window is given. Audio is muxed from the matching offset in the master. A custom score needs a matching model/manifest (`--score=/absolute/path/score.json --asset=asset_basename`).

## The film

`--film` plays the piece as a film: `harness/film_director.gd` (`FilmDirector`) turns the score's camera cues into moving shots and a lighting arc, with no UI, a title card over the dark opening and an end card over the ring-out. Each cue is a move, not a fixed view: a push out of the dark, the first pick arm in profile from behind (an arm reaches from its carriage behind the machine forward to the strings, so it reads whole from the side, never through the strings), an orbit round the low arm's run, the harp overhead, the rake from behind, the mallets low along the bars, the ratchet from behind the rail two bars into their entry, the whole machine lit, a pullback, and a last look from behind. Shots that follow an arm aim at its tool smoothed ±0.7 s, so the camera leans with a phrase and does not twitch with a click. The light comes up from black as the harp unfolds alone, is full when every mechanism plays (`wide-lit`) and goes back to black through the ring-out.

The director is a pure function of score time, so `tools/render_film.sh` renders the piece in parallel chunks (`JOBS=3`) at 1920×1080 / 30 fps and cuts them together frame-exact with the master. The harness uses the Compatibility renderer, so there is no depth of field.

```sh
tools/render_film.sh                                  # -> render/film/the-chamber.mp4
godot --path harness -- --film --size=960x540 --capture=/tmp/f --start=0 --seconds=86 --fps=1   # a one-per-second proof
```

## Motion contract

- Carriages travel on separate rails spanning each arm's reach window. Links retain their lengths through analytic IK. Each rail's bars end in a rail head on a tapered steel mast (bracketed back or out where a neighbour is in the way); rails are obstacles to the other arms in the rail search. See [articulated arms](articulated-arms.md#rail-gantries).
- A carriage rides its bars on two bushings tied by a cheek plate, and its pinion rolls on a rack (teeth phase-locked to travel) on one of four mounts — behind, above, below or in front of the carriage — chosen per arm by measuring the drive against the arm's own motion (`pinion` in the manifest). See [the carriage and its drive](articulated-arms.md#the-carriage-and-its-drive).
- Travel, anticipation, contact, sweep and recovery are evaluated from exported intervals; a tool rests over its last actual contact, including its pick offset. There is no timer-dependent animation state to become stale after seeking.
- Rakes linearly traverse their ordered contact positions and cross each string at `t + index * spread_s`, including reverse sweeps.
- The tool's origin is its contact point. The wrist pin is at `tip + wrist_offset` from the manifest (picks/rakes 0.20 m above and 0.10 m behind the string, mallets 0.28 m above — the height the plectrum or felt, ferrule, shank, socket and boss need); the elbow bends per the manifest's `bend` ("back" for plucked/raked arms, "up" for mallets). Speaking lengths are scaled uniformly by three; the harp and rake string positions come from the score's own neck fan (`Mechanism.fan`); plucked elements are upright, struck elements lie horizontally.
- Arms are double parallelograms posed from the same IK: every crosshead and tool stays upright, the parallel bars ride at the manifest's `o1`/`o2` offsets. See [articulated arms](articulated-arms.md).
- Original string clips are superposed after all recent contacts, so overlapping ring-outs remain visible. Strings are shaded tubes bent by the clip in a vertex shader, with a translucent sheath for the recent peak excursion, strung by register as a harp is (wound wire below C4, translucent gut through the middle, nylon from C5; C red, F dark — see [articulated-arms.md](articulated-arms.md)). A sounding string glows with its energy (emission from the peak excursion of the last 1/30 s, tinted by the wire's own colour), and the bend and sheath carry a 35 % cross-axis component — a plucked wire precesses into an ellipse — so vibration reads from a camera in front of the string plane, not only edge-on. Displacement is exaggerated for inspection. A string never drops below 1.6 px on screen: the shader holds a sub-pixel wire at that width and tones it down by the coverage it lost, so the treble strings stay continuous lines in the wide shots. It remains the existing FD approximation, not a reconstruction of the audible Karplus–Strong waveform. Bars have a small illustrative spring response; the chamber indicator follows its stem envelope.
- Swept-volume clearance is checked at build time (self, cross-arm, strings, scene boxes) and the score planner keeps arms of one mechanism `arm_clearance` apart along their axis at every moment; motor acceleration limits remain a follow-up in `clockwork-todos.md`.

## Appearance directions

The delivered version implements **exposed clockwork**. The same pivots could later wear **sculptural ceramic shells** (curved pale housings, dark joints) or **precision-machinery covers** (brushed aluminum, compact rectangular wrists). Keep all three tool origins and link lengths identical so appearance changes cannot alter timing. These latter two are design options, not delivered alternate model sets.

## Verification

```sh
godot --headless --path harness -s dev/test_load.gd
godot --headless --path harness -s dev/test_clockwork.gd
godot --headless --path harness -s dev/test_load.gd -- --score=/absolute/repo/render/clockwork/score.json
godot --headless --path harness -s dev/test_clockwork.gd -- --score=/absolute/repo/render/clockwork/score.json --asset=clockwork_expanded
```

The motion ruler checks every contact (including rake sub-onsets), fixed link lengths and reach at 120 Hz across the complete piece, continuity on either side of event boundaries, and invariance after backward seeks. `songs/clockwork.py` separately verifies unchanged original event plans, zero scheduling conflicts and onset recall on the two added stems. The original arrangement stays available unchanged in `render/chamber`.

An additional integration ruler checks the imported GLB nodes, world-space tool
origins at every contact, and the actual mesh axis/length after rig transforms:

```sh
godot --headless --path harness -s dev/test_performance.gd
godot --headless --path harness -s dev/test_performance.gd -- --expanded
```

Verified on Godot 4.7 / Blender 4.0.2: original 247 events, 331 contacts,
6 rigs; expanded 315 events, 399 contacts, 9 rigs. Maximum mathematical
link error was 0.000000429 m; no unreachable target over either full
86-second performance. Both added stems had onset recall 1.0. The six-second
review clips have 180 frames at 30 fps, H.264 video and AAC master audio.

The [surface and lighting guide](clockwork-look.md) covers the runtime shaders,
procedural texture rebuild, studio lighting and `--clean` beauty captures.

The [procedural form results](form-generation-results.md) cover the continuous frames, structural experiment and sampled tool-clearance checks; the bar instrument's marimba construction (node-line rails, end frames, resonators) is in [instrument frames](instrument-frames.md). Press **F** to cycle carved, ribbed and shell frames, or pass `--form=carved|ribbed|shell`.

The current [traditional harp refinement](traditional-harp-refinement.md) replaces the initial rounded frames with coved moulding and a diagonal soundbox.

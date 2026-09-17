# Clockwork Chamber

The current performance uses editable Blender models and rigid mechanical pivots, exported as GLB; Godot evaluates two-link IK from the score at any requested time. There is no physics simulation or MIDI inference. The default is exposed clockwork: walnut structures, satin brass linkages and carriages, dark steel joints, felt mallets and brass plectra on swan-neck shanks.

## Build and play

From the repository root:

```sh
python3 songs/chamber.py
python3 songs/clockwork.py
blender -b -t 2 -P tools/build_clockwork.py
blender -b -t 2 -P tools/build_clockwork.py -- render/clockwork/score.json clockwork_expanded
godot --headless --path harness --editor --import --quit
godot --path harness
# The expanded arrangement: four glass bells and three temple blocks.
godot --path harness -- --expanded
# Original 2D diagnostic:
godot --path harness res://main.tscn
```

Editable source files live in `models/`, outside Godot's import tree so headless imports never need to launch Blender. `harness/assets/` contains GLBs and geometry manifests. Rebuilding derives contact geometry and reachable rail extents from the score. Source rigs are posed at home in Blender; the authoritative performance rig lives in `clockwork_motion.gd`. Re-running the model generator overwrites generated assets, so preserve hand edits separately.

## Playback and inspection

Space pauses/resumes; Home starts a one-second pre-roll so the first contact has an approach. Left/right seek two seconds. The bottom slider scrubs. C cycles wide, harp, rake, bars, overhead and expansion views. Two inspection views follow the action for stills and clips: `--view=9` sits behind the string plane on the second harp arm's elbow (knuckle pins, crossheads, parallel bars) and `--view=10` frames the most recently plucked string from 45° off its pluck axis, latching for 1.5 s so a run of plucks does not throw it about. A restores cue-directed cameras. T shows the existing annotated score. M switches the finished master and dry stems; 1–9 mute/unmute dry stems and select that audition mode. The default master is `chamber.wav` next to the score. Playback stops at the end rather than drifting past the tail.

```sh
SHOT=/tmp/chamber.png godot --path harness -- --camera=manual --view=0 --time=48
godot --path harness -- --capture=/tmp/chamber-frames --start=45.5 --seconds=8 --fps=30 --camera=manual --view=3
ffmpeg -framerate 30 -i /tmp/chamber-frames/%05d.png -ss 45.5 -i render/chamber/chamber.wav -t 8 -c:v libx264 -pix_fmt yuv420p -c:a aac /tmp/chamber.mp4
show /tmp/chamber.mp4 'Mallet approaches, contacts and recovery'
```

Capture samples deterministic score times; it does not record wall-clock frame delivery. Audio is muxed from the matching offset in the master. A custom score needs a matching model/manifest (`--score=/absolute/path/score.json --asset=asset_basename`).

## Motion contract

- Carriages travel on separate rails spanning each arm's reach window. Links retain their lengths through analytic IK. Each rail's bars end in a rail head on a tapered steel mast (bracketed back or out where a neighbour is in the way); rails are obstacles to the other arms in the rail search. See [articulated arms](articulated-arms.md#rail-gantries).
- Travel, anticipation, contact, sweep and recovery are evaluated from exported intervals; a tool rests over its last actual contact, including its pick offset. There is no timer-dependent animation state to become stale after seeking.
- Rakes linearly traverse their ordered contact positions and cross each string at `t + index * spread_s`, including reverse sweeps.
- The tool's origin is its contact point. The wrist pin is at `tip + wrist_offset` from the manifest (picks/rakes 0.20 m above and 0.10 m behind the string, mallets 0.28 m above — the height the plectrum or felt, ferrule, shank, socket and boss need); the elbow bends per the manifest's `bend` ("back" for plucked/raked arms, "up" for mallets). Speaking lengths are scaled uniformly by three; the harp and rake string positions come from the score's own neck fan (`Mechanism.fan`); plucked elements are upright, struck elements lie horizontally.
- Arms are double parallelograms posed from the same IK: every crosshead and tool stays upright, the parallel bars ride at the manifest's `o1`/`o2` offsets. See [articulated arms](articulated-arms.md).
- Original string clips are superposed after all recent contacts, so overlapping ring-outs remain visible. Strings are shaded tubes bent by the clip in a vertex shader, with a translucent sheath for the recent peak excursion. A sounding string glows with its energy (emission from the peak excursion of the last 1/30 s, tinted by the wire's own colour), and the bend and sheath carry a 35 % cross-axis component — a plucked wire precesses into an ellipse — so vibration reads from a camera in front of the string plane, not only edge-on. Displacement is exaggerated for inspection. It remains the existing FD approximation, not a reconstruction of the audible Karplus–Strong waveform. Bars have a small illustrative spring response; the chamber indicator follows its stem envelope.
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

The [procedural form results](form-generation-results.md) cover the continuous frames, branching stand, structural experiment and sampled tool-clearance checks. Press **F** to cycle carved, ribbed and shell frames, or pass `--form=carved|ribbed|shell`.

The current [traditional harp refinement](traditional-harp-refinement.md) replaces the initial rounded frames with coved moulding and a diagonal soundbox.

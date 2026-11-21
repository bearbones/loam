# Clockwork performance and score diagnostic

The default Godot 4.7 scene plays The Chamber with Blender-modeled instruments,
rigid mechanical pivots, score-driven IK, vibrating strings, cue cameras and
master/dry-stem audition, all played back from a motion bake of `formlab.rig`.
A separate expanded arrangement adds glass bells and temple blocks. The original annotated 2D debug view remains available.

From the repository root:

```sh
godot --path harness
godot --path harness -- --expanded
godot --path harness res://main.tscn
godot --headless --path harness -s dev/test_load.gd
godot --headless --path harness -s dev/test_clockwork.gd
godot --headless --path harness -s dev/test_performance.gd
godot --headless --path harness -s dev/test_pose_parity.gd [-- --expanded]
```

Render the original score first with `python3 songs/chamber.py` if
`render/chamber/score.json` is absent. Build the expanded score with
`python3 songs/clockwork.py`. GLBs and matching manifests are in `assets/`;
editable Blender sources are in `../models/` (built, not tracked). The
performance plays back a motion bake beside the score — `python3
tools/bake_motion.py` makes it (the build does too), and the harness refuses
a stale one, or an older format, with that command. `MotionBake`
(`motion_bake.gd`) reads the bake (`loam-motion/2`: the channels and the
joints table, `frames_at(t)` the joints' frames); `MotionRig`
(`motion_rig.gd`) binds the table's bodies to the GLB's nodes and poses them
(`apply(t)`). The scenes and tests preload `motion_rig.gd` by path, so they
run on a class cache from before it existed; run `godot --headless --path
harness --import` after a fresh checkout and after pulling or merging a new
`class_name` script, so the cache (and the editor) knows it.

The transport shows elapsed time, the current section and a scrubber drawn from
the score's stem envelopes. Vertical marks locate section changes. Use the camera
menu to follow the score's moving shots or inspect any of the 17 fixed and
tracking views. The adjacent buttons cycle the frame form, audition the master
or dry stems, and open the annotated score.

Space plays, pauses or replays. Home restarts with pre-roll and the arrow keys
seek two seconds. C cycles inspection views, A resumes cue cameras, F changes
the frame, T toggles the score, M switches the mix and 1–9 mute stems.
The 2D diagnostic retains Z/X track zoom and S capture.

See [the build guide](../docs/clockwork-build.md) for full rebuild commands,
deterministic screenshots/video, animation details and verification limits.
The sound-production backlog is in [clockwork-todos.md](../docs/clockwork-todos.md).

The continuous carved frame is the default. Select `--form=ribbed` or
`--form=shell` for alternatives. See [form generation](../docs/traditional-harp-refinement.md).

The [joint milestone](../docs/seamless-form-joints.md) adds continuous contour transitions and tests for shared frame topology.

The current [reference harp structure](../docs/reference-harp-structure.md) includes the pedal base and neck hardware. Review views 6/7/8 show the neck/front/base.

Choose **Soundbox ports** or **Sympathetic chamber** in the camera menu to inspect the joinery and the wire bank. The expanded film cuts to the glass and temple-block benches during their phrases. Render it with `ASSET=expanded tools/render_film.sh` from the repository root.


A fixed inspection camera can frame a string or struck body by its score ID.
This command captures the bass hand at release.

```sh
SHOT=/tmp/loam-harp.png bash tools/offscreen.sh godot --path harness -- --expanded --focus=harp04 --focus_pick=.18 --focus_span=.24 --focus_dir=-.57,-.68,.93 --time=7.14 --silent --clean
```

The camera stays on the wire as the hand opens, plants, draws and closes. Use `--focus=harp_arm0 --focus_span=1.7` for the reach from the pillar, or `--focus=repair --focus_span=.57` for the butterfly keys in the cabinet lid.

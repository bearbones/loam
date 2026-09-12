# Clockwork performance and score diagnostic

The default Godot 4.7 scene plays The Chamber with Blender-modeled instruments,
rigid mechanical pivots, score-driven IK, vibrating strings, cue cameras and
master/dry-stem audition. A separate expanded arrangement adds glass bells and
temple blocks. The original annotated 2D debug view remains available.

From the repository root:

```sh
godot --path harness
godot --path harness -- --expanded
godot --path harness res://main.tscn
godot --headless --path harness -s dev/test_load.gd
godot --headless --path harness -s dev/test_clockwork.gd
godot --headless --path harness -s dev/test_performance.gd
```

Render the original score first with `python3 songs/chamber.py` if
`render/chamber/score.json` is absent. Build the expanded score with
`python3 songs/clockwork.py`. GLBs and matching manifests are in `assets/`;
editable Blender sources are in `../models/`.

Performance keys: Space play/pause; Home restart with pre-roll; arrows seek;
C cycle camera; F cycle frame form; A cue cameras; T score overlay; M master/dry stems; 1–9 mute
stems. The slider scrubs. The 2D diagnostic retains Z/X track zoom and S capture.

See [the build guide](../docs/clockwork-build.md) for full rebuild commands,
deterministic screenshots/video, animation details and verification limits.
The sound-production backlog is in [clockwork-todos.md](../docs/clockwork-todos.md).

The continuous carved frame is the default. Select `--form=ribbed` or
`--form=shell` for alternatives. See [form generation](../docs/traditional-harp-refinement.md).

The [joint milestone](../docs/seamless-form-joints.md) adds continuous contour transitions and tests for shared frame topology.

The current [reference harp structure](../docs/reference-harp-structure.md) includes the pedal base and neck hardware. Review views 6/7/8 show the neck/front/base.

# Traditional harp and moulded joinery

The subsequent [seamless joint milestone](seamless-form-joints.md) replaces the overlapping fitted ends described below.

The second geometry pass replaces the broad rounded loop with a freestanding
triangular harp: a single upright column, a dipping harmonic neck, a diagonal
soundbox and a compact moulded plinth. The smaller rake uses the same language.
The sympathetic chamber now sits behind them so their feet remain visible.

The profile has a broad recessed face, concave coves, raised beads and narrow
fillets, similar to a balustrade handrail. The soundbox has a pale inset face.
The frame preserves these analytic profiles through Blender, with only a 3 mm
edge break and controlled split normals. Voxel smoothing is retained for the
branching bar stand, where blended junctions are intentional. Frame members are
separately closed, fitted components, not a single voxel union.

The overall column/neck/soundbox arrangement was checked against traditional
lever-harp references, including [Salvi's Titan](https://www.salviharps.com/wp-content/uploads/2016/05/Schede-website_Salvi-OK_Titan.pdf).
This is an original stylized model for the clockwork performance, not a replica.

## Geometry and motion contract

The former rectangular anchor positions have deliberately changed. The visual
layout in `formlab/layout.py` narrows the harp and raises the soundboard toward
the treble end. String spacing follows log length, giving a smooth neck despite
uneven musical intervals. Every speaking length, pitch, default pick fraction,
event and audio asset remains unchanged. The existing analytic rigs read the
new manifest positions; rail extents are rebuilt from their assigned strings.

The old equal-volume neck experiment describes the first prototype only. Its
optimized sections and 40% compliance result do **not** apply to this geometry.
All three current frame variants are labelled geometric. `ribbed` remains the
CLI compatibility name for the brass moulded version; `shell` adds a restrained
pierced crest. Press F to compare.

## Verification

- All 331 original and 399 expanded imported tool contacts pass.
- Both full-track rig tests pass reach, fixed link lengths, boundary continuity
  and backward seeking.
- Original lengths, pitches and pick fractions pass independent comparisons
  against the score; the diagonal soundboard and compact footprint are checked.
- Swept components and final frame triangles have no open/nonmanifold edges or
  degenerate triangles. Separate fitted components may overlap at joints.
- Updated tool clearance checks all three variants, their soundboard faces and
  the shared stand at 120 Hz plus exact contacts: 64,632 poses per variant.
  The conservative minimum is **21.96 mm**, including the pick-surface sampling
  allowance. Anchor seats pass. This does not certify whole arms or the motion
  between samples.

The distance checker now uses oriented ray crossings to distinguish interior
from exterior, rather than the nearest triangle's normal at concave corners.
Independent tests cover a concave exterior, interiors, overlapping closed parts
and distant points. Reports retain final mesh and motion hashes.

## Rebuild and review

After rendering the scores, no structural-study output is required:

```sh
blender -b -t 2 -P tools/build_clockwork.py
blender -b -t 2 -P tools/build_clockwork.py -- render/clockwork/score.json clockwork_expanded
godot --headless --path harness --editor --import --quit
python3 tools/test_formlab.py
blender -b -t 2 -P tools/test_mesh_distance.py
godot --headless --path harness -s dev/export_motion.gd
blender -b -t 2 -P tools/check_form_clearance.py
godot --headless --path harness -s dev/test_performance.gd
godot --headless --path harness -s dev/test_performance.gd -- --expanded
godot --path harness -- --camera=manual --view=1 --form=carved
```

CLI review view 6 shows the neck moulding; view 7 gives a front elevation.
Editable Blender models and GLBs include all alternatives. Captures and the
updated clearance report are under `render/form-study/`.

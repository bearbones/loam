# Harp structure from the supplied reference

This pass follows the structure in the user's Photo 1.jpg: a tall bass column,
a descending curved neck, a broad sloping soundbox, and a solid pedal box.
It retains the existing walnut/brass finish and seamless contour joints rather
than copying the photograph's black finish or its full string count.

## Delivered

- Taller bass end and a straight column, with the lower return seated in a solid
  oval base. The base has a crown, sole and seven separate pedal levers/treads.
- A deeper neck with a metal mounting plate, tuning pins, square key ends and
  two rows of disc/fork hardware aligned with the sixteen scored strings.
- A deeper, wider soundbox with an expanded pale soundboard face. Its inset
  uses the receiving frame's cross-section orientation to keep the edge clean.
- Red C strings and dark F strings for visual orientation.
- Camera adjustments for the taller harp; CLI views 6, 7 and 8 show the neck,
  full front elevation and pedal base respectively.

The pedals and tuning discs are static modeled hardware. They do not yet change
pitch or animate with pedal instructions; the score has no such instructions.
The existing clockwork tools continue to perform the track. This is an exterior
structural model, not a calibrated acoustic resonator or an exact replica.

## Display layout and geometry core

The harp now has an explicit **1.7 display-length multiplier**, in addition to
the existing factor of three from score coordinates to the scene. Bass string
spacing is redistributed to flatten the neck near the column before it descends.
This changes visual anchors and tool trajectories. Pitches, event timing, default
pick fractions, string identities and rendered audio remain unchanged. The
manifest records the multiplier; tests check it explicitly. The audio model's
physical lengths are not rewritten to match these display proportions.

The core's section interpolation now uses bounded quintic transitions. Width
and depth remain positive and have continuous first and second derivatives at
control points, without cubic interpolation overshoot. The upper joint's trim
was adjusted for the deeper neck; the contour-folding ruler continues to pass.
The smaller rake inherits the broader soundbox/profile improvements.

## Validation and rebuild

```sh
blender -b -t 2 -P tools/build_clockwork.py
blender -b -t 2 -P tools/build_clockwork.py -- render/clockwork/score.json clockwork_expanded
godot --headless --path harness --editor --import --quit
python3 tools/test_formlab.py
python3 tools/test_form_joints.py
blender -b -t 2 -P tools/test_form_joint_seats.py
godot --headless --path harness -s dev/export_motion.gd
blender -b -t 2 -P tools/check_form_clearance.py
godot --headless --path harness -s dev/test_clockwork.gd
godot --headless --path harness -s dev/test_performance.gd
godot --headless --path harness -s dev/test_performance.gd -- --expanded
```

The clearance export now includes the pedal base, pedals, tuning hardware and
mounting plate as well as the frame, inset faces and shared bar stand. Sampling
remains 120 Hz plus exact note contacts, with conservative tool envelopes.
It does not certify entire arms or motion between samples. Numeric results and
mesh/motion hashes are in `render/form-study/clearance.json`.

Review captures: `reference-front.png`, `reference-neck.png`, and
`reference-base.png` under `render/form-study/`.

## Surface restraint pass

The soundbox and lower column now use gentler changes in section width/depth.
The pale inset has a narrower, nearly linear taper with a wider walnut border;
its ends sink into the face without shrinking into teardrop tips. The action
plate is planar, has constant width and half its former thickness, and sits
lower on the neck to contain the two disc rows. String geometry is unchanged.

The Blender adapter also removes sub-micron bevel slivers before mesh validation;
it preserves the authored profiles and UVs. Updated close-ups are
`restrained-front.png` and `restrained-neck.png` under `render/form-study/`.

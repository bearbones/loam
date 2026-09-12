# Seamless contour joints

The subsequent [reference structure pass](reference-harp-structure.md) adds the taller display layout, broad soundbox and pedal hardware.

The neck, column and soundbox now form one continuous swept surface. There are
no caps, overlapping trim ends or separate capital blocks at the main joints.
Corresponding beads, coves and face edges continue around each corner as shared
vertex rings. This applies to both harp and rake, in both ensemble assets.

`formlab/joints.py` trims adjoining centre-lines back from their logical meeting
point and fits tangent-matched cubic transitions. Each profile point retains its
identity through the transition. A periodic C2 section field interpolates width
and depth, allowing the narrower neck to meet the deeper soundbox gradually.
The centre-line transitions are tangent matched; this is not a claim of exact
curvature continuity for every point on the resulting surface.

Unmatched detail uses a separate operation: per-ring profiles morph into a plain
receiving section using a quintic fade with zero endpoint slope. This fades the
foot's moulding into its support. The pale soundboard inset follows the actual
receiving frame, tapers in width and sinks below the surface at both ends.
The former shell crest was removed; the `shell` option now uses reduced relief
on the same continuous frame, while `ribbed` retains the brass finish.

The core remains independent of Blender. Blender preserves its topology and UVs
and applies only small edge breaks. The bar stand retains its voxel-union finish.
Functional string ferrules remain separate closed components, with their caps
buried inside the backbone. No string anchors or animation positions changed in
this milestone.

## Checks

```sh
python3 tools/test_form_joints.py
python3 tools/test_formlab.py
blender -b -t 2 -P tools/test_form_joint_seats.py
blender -b -t 2 -P tools/check_form_clearance.py
godot --headless --path harness -s dev/test_performance.gd
godot --headless --path harness -s dev/test_performance.gd -- --expanded
```

The joint test checks the actual generated harp and rake: closed genus-one
backbone topology, no cap vertices, tangent alignment at the transitions, local
bend occupancy below the contour-folding threshold, and floor contact. It does
not constitute a general mesh self-intersection proof. Receiver checks verify
that every ferrule ends at least 10 mm inside its parent frame.

The full original tool track is checked against all frame variants, inset faces
and the shared stand at 120 Hz plus exact contact times. The report lives in
`render/form-study/clearance.json` and records mesh/motion hashes. It still covers
tools, not the complete arms or continuous motion between samples. Imported
contacts remain 331 for the original ensemble and 399 for the expanded ensemble.

Build commands remain those in `clockwork-build.md`; no structural-study output
is required. Close-ups are `render/form-study/joints-detail.png` and
`render/form-study/joints-front.png`. Godot CLI view 6 shows the upper joints;
view 7 shows the front silhouette.

This is a reusable solution for sequential, corresponding swept profiles and
controlled profile fade-outs. Arbitrary three-way branching joints or automatic
matching of unrelated profile schemas are separate future capabilities.

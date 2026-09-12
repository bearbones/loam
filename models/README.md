# Editable clockwork assemblies

`clockwork.blend` is the original Chamber ensemble; `clockwork_expanded.blend`
adds four glass bells and three temple blocks. Both contain separate named
rigid links, joints, carriages and contact tools, assembled at their home poses.
Materials, instrument bodies, rails, fasteners, labels and the stage are editable.

These are generated sources: `tools/build_clockwork.py` overwrites them during
rebuild. Preserve manual modeling work under a different filename or put the
change in the generator. Runtime animation is analytic in Godot, rather than a
Blender armature or per-note baked action. GLB assets and geometry manifests are
exported together to `harness/assets/`; keep those matched to the chosen score.

Both files include three continuous `form_` frame variants and a branching bar
stand. Carved is visible by default in Blender; unhide the other form objects
for editing. No structural-study output is needed for the current geometric recipes.
The headless geometry core lives in `formlab/`; Blender preserves the frame profiles and unions the branching stand.

# String look: wound bass strings, anisotropic highlights, contact shadows

**Status (2026-09-17, late evening):** landed in one pass — the tangent
and `ANISOTROPY` per family (`string_aniso`), the winding and gut grain as
normal rocking faded by `fwidth`, and the contact darkening by `UV.x`
(no per-string uniforms: every tube ends on hardware); `--view=16` is the
close-up. Not done: per-family specular *tints* (Godot's non-metal
specular is white; a tint needs the metallic path or a custom BRDF) and a
frame-time measurement. Judge the result by eye on views 6/12/14/16.

**Where:** `harness/shaders/wire_string.gdshader`, `harness/performance.gd`
(`_make_string`, `_wire_mesh`, the `family` parameter), `formlab/layout.py`
(`neck_plan`, eyelets), `dev/test_performance.gd` (the string family and
mesh-convention checks), `docs/articulated-arms.md` ("Strings"),
`docs/clockwork-look.md`.

**Problem:** the strings are shaded tubes with a minimum on-screen width and
a per-register family (wound wire, gut, nylon) that today differs by colour
and radius only. At the render distances that matter (views 1 and 6) a
wound bass string should show its winding as a fine helical texture and a
broken specular line; gut should be matte with a soft highlight; nylon a
narrow bright one. Where a string passes through an eyelet or over a bridge
pin it floats — no contact shadow — so the strings do not read as pulled
tight through hardware.

**Work:**

1. Winding: in the shader, for `family == 1` (wound), modulate the normal
   with a helix `sin(k·(v·length) + atan(ring angle))` at the wrap's
   pitch (about 1.5× the wire radius) — from the mesh's UV (`uv.y` is the
   ring angle by the pinned convention; `uv.x` the length) — and sharpen
   the specular with an anisotropic term along the string tangent
   (Kajiya–Kay: use the tangent, not the normal, for the highlight). Keep
   the minimum-width rebuild intact (it works from `UV.y`).
2. Per-family material: roughness 0.35/0.6/0.25 and a specular tint
   (silver / warm ivory / clear) as uniforms set per family in `_make_string`.
3. Contact shading: a small darkening (an SDF-based fake AO in the shader,
   fed the world positions of the string's two nearest hardware contacts —
   eyelet centre, bridge pin — as uniforms) so the string darkens 3 mm
   either side of a contact. The dead lengths (three segments to the tuning
   pin) get the same at the bridge pin and the coil.
4. Rulers: `dev/test_performance.gd` — the shader keeps `min_px`,
   `radius`, and gains `family`-dependent uniforms it can read back; a
   render-level check is the operator's eye: capture views 1 and 6 before
   and after, `show --grid`.

**Acceptance:** wound strings show a winding at view 6's distance without
aliasing (test at 1080p and at half resolution — if it shimmers, fade the
winding with `fwidth`), highlights run along the strings not across, the
eyelet passages read as contacts; frame time unchanged within 10 %.

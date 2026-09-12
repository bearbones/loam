# Clockwork materials and lighting

The performance now assigns a coordinated surface palette after loading either
GLB. Both instrument sets receive the same finishes. The source meshes retain
simple portable materials in Blender; the final appearance is implemented in
Godot by `harness/clockwork_look.gd` and `harness/shaders/`.

## Surfaces

- **Walnut and rosewood:** directional grain, end grain, restrained pore relief,
  and roughness variation. Long boards, upright members and sounding bars use
  different grain axes. Several deterministic offsets avoid identical boards.
- **Brass:** a muted champagne base, light patina, brushed microtexture and broad
  reflections. Wear changes roughness as well as color; it does not displace
  the geometry or hide the joint silhouettes.
- **Steel:** cooler, darker reflections distinguish rails, joints and picks
  from the brass links and carriages.
- **Felt:** warm ivory fiber detail with high roughness and soft edge scattering.
- **Glass bells:** tinted transparency and stronger reflections at grazing
  angles, with a depth prepass. This is a lightweight glass approximation;
  it does not simulate refraction or caustics.
- **Stage:** charcoal enamel with subtle surface texture. The chamber indicator
  now changes warm emission with the stem envelope instead of expanding.

The shared surface shader samples object coordinates, so textures remain
attached to moving links. Relief perturbs normals only. All tool positions,
mesh dimensions and score timing remain unchanged. The Blender generator now
uses weighted normals on beveled parts to keep flat faces and edge highlights
well behaved.

## Texture sources

Three original 1024 × 1024 tileable PNGs are generated from seeded numerical
noise. There are no downloaded assets or external texture licenses.

| File in `harness/assets/textures/` | R | G | B |
| --- | --- | --- | --- |
| `walnut_data.png` | grain | pores | roughness variation |
| `metal_data.png` | patina | directional scratches | fine grain |
| `felt_data.png` | fibers | cross fibers | cross fibers |

These are **linear data maps**, not color photographs. Their import settings
retain the channels and generate mipmaps. The shaders request anisotropic
filtering to reduce shimmer in narrow rails and receding boards. Color comes
from the palette uniforms.

Rebuild with:

```sh
python3 tools/build_surface_textures.py
godot --headless --path harness --editor --import --quit
```

## Lighting

A warm key, cool fill and amber rim separate the structures. A procedural sky
supplies broad studio-panel reflections without placing bright panels in the
camera view. A continuous curved backdrop catches the stage shadow without a
hard horizon. Moderate ambient occlusion, filtered shadows, filmic tonemapping,
light fog and 4× MSAA complete the scene on the existing GL Compatibility
renderer. The sky is static: no time-driven texture or lighting changes can
interfere with deterministic score capture.

The implementation uses Godot's documented separation between
[ambient and reflected sky light](https://docs.godotengine.org/en/4.7/tutorials/3d/environment_and_post_processing.html)
and the [sky cubemap pass](https://docs.godotengine.org/en/stable/tutorials/shaders/shader_reference/sky_shader.html).

## Review and capture

Normal playback retains all inspection controls. Add `--clean` to hide the HUD
in a still or video. Capture waits for twelve submitted frames to warm up
shaders and sky filtering before saving frame zero.

```sh
SHOT=/tmp/clockwork-look.png godot --path harness -- --camera=manual --view=3 --time=46.2 --clean
godot --path harness -- --expanded --camera=manual --view=5
```

Reviewed the original wide view, mallets, and expanded glass instruments in
rendered captures; produced a six-second motion preview in
`render/material-review/materials.mp4`. Both existing GLB integration checks
pass (331 original contacts and 399 expanded contacts). Material changes
introduce no new dependencies beyond the existing NumPy/SciPy/Pillow texture
generator and Godot runtime.

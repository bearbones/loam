# Clockwork materials and lighting

The performance assigns a coordinated surface palette after loading either
GLB. Both instrument sets receive the same finishes. The source meshes retain
simple portable materials in Blender; the final appearance is implemented in
Godot by `harness/clockwork_look.gd` and `harness/shaders/`.

## Surfaces

- **Lacquered grooved walnut and rosewood:** directional grain, carved longitudinal
  flutes/grooves, end-grain concentric rings, subsurface chatoyancy, deep vessel
  pore relief, and a dual-layer glossy clearcoat/lacquer response. View rays
  refract through the clear lacquer coat ($n \approx 1.49$) via Parallax Occlusion
  Mapping (POM) onto the normal-mapped grooved wood substrate below, with
  Beer–Lambert warm amber absorption in the deeper grooves and pores while a
  smooth top clearcoat lobe reflects studio panels above. Long boards, upright
  members and sounding bars use different grain axes and clearcoat gloss levels.
- **Brushed brass and phosphor bronze:** a muted champagne brass base (and warmer,
  pinker phosphor bronze for bearings and plummer blocks), light recessed patina,
  multi-scale directional brushed micro-grooves with parallax depth, tangent-space
  normal maps, and stretched anisotropic reflections along the brush direction.
  Machined edges polish brighter and smoother while crevices retain patina.
- **Brushed and blued steel:** cooler, darker anisotropic reflections with fine
  honed striations distinguish rails, leadscrews, joints and picks from the brass
  links and carriages.
- **Felt:** warm ivory fiber detail with high roughness and soft edge scattering.
- **Glass bells:** tinted transparency and stronger reflections at grazing
  angles, with a depth prepass. This is a lightweight glass approximation;
  it does not simulate refraction or caustics.
- **Stage:** charcoal enamel with subtle surface texture. The chamber indicator
  changes warm emission with the stem envelope instead of expanding.

The shared surface shader samples object coordinates (or authored sweep UVs on
profiled `form_*` frames), builds an orthonormal view-space tangent basis
aligned with the grain/brush axis, and combines Parallax Occlusion Mapping
with pre-baked tangent-space normal maps and surface-gradient micro-relief so
textures remain attached to moving links without displacing mesh geometry or
altering tool clearances. All tool positions, mesh dimensions and score timing
remain unchanged.

## Texture sources

Seven original 1024 × 1024 tileable PNGs are generated deterministically from
seeded numerical noise and periodic central-difference height fields. There are
no downloaded assets or external texture licenses.

| File in `harness/assets/textures/` | R | G | B |
| --- | --- | --- | --- |
| `walnut_data.png` | grain | pores | roughness variation |
| `wood_normal.png` | tangent normal $n_x$ | bitangent normal $n_y$ | surface normal $n_z$ |
| `wood_depth.png` | composite groove + pore height | flute & chatoyancy wave | groove/pore cavity AO |
| `metal_data.png` | patina | directional scratches | fine micro-grit |
| `metal_normal.png` | tangent normal $n_x$ | bitangent normal $n_y$ | surface normal $n_z$ |
| `metal_depth.png` | brushed micro-groove height | brush tangent flow phase | micro-groove cavity AO |
| `felt_data.png` | fibers | cross fibers | cross fibers |

These are **linear data maps**, not color photographs. Their import settings
retain the channels losslessly and generate mipmaps. The shaders request
anisotropic filtering and use explicit UV gradients (`textureGrad`) inside the
parallax ray-march to prevent mipmap swimming on narrow rails and receding
boards. Color comes from the palette uniforms.

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

Reviewed the wide view, neck moulding, arm joints, marimba bars, and ratchet
mechanism in rendered captures. Both existing GLB integration checks pass.
Material changes introduce no new dependencies beyond the existing
NumPy/SciPy/Pillow texture generator and Godot runtime.

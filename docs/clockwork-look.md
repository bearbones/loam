# Clockwork materials and lighting

The performance assigns a coordinated surface palette after loading either
GLB. Both instrument sets receive the same finishes. The source meshes retain
simple portable materials in Blender; the final appearance is implemented in
Godot by `harness/clockwork_look.gd` and `harness/shaders/`.

## Surfaces

- **Walnut, rosewood and spruce.** Each sawn member has its own metre-scale
  grain frame. The same growth rings bend past knots on the face and turn
  across the end grain. Open vessels, shallow dents and scraper tracks carry
  relief. The raised edges polish where hands rub them. The felt polishes the
  centre of a sounding bar and leaves its die-stamped pitch legible near the end.
- **Casework.** Seven back planks fit between the cabinet cheeks. A drying
  split in the lid runs under two inset rosewood butterfly keys. The repaired
  area has been re-oiled and the front lip is worn from lifting. The front
  rails show their tenon ends and the marimba bearer has drawbore pegs.
- **Carved alabaster.** The pale harp and rake frames share a stone material.
  Soft calcite bands and narrow honey-colored seams run through the cross
  sections of the carvings. The shader samples the low-frequency patina
  channel at two scales to break up the deposits.
- **Brushed brass and phosphor bronze:** a muted champagne brass base (and warmer,
  pinker phosphor bronze for bearings and plummer blocks), light recessed patina,
  multi-scale directional brushed micro-grooves with parallax depth, tangent-space
  normal maps, and stretched anisotropic reflections along the brush direction.
  Machined edges polish brighter and smoother while crevices retain patina.
- **Brushed and blued steel:** cooler, darker anisotropic reflections with fine
  honed striations distinguish rails, leadscrews, joints and picks from the brass
  links and carriages.
- **Felt:** warm ivory fiber detail with high roughness and soft edge scattering.
- **Glass bells:** each skirt has a slightly oval section, wheel-cut flutes and a
  dressed lip. A periodic height field carries winding glass cords and seed
  bubbles through the highlights. The pitch stamp is frosted into the front
  wall. A slender turned arbor rises from a screwed flange to a lock ring and
  a felt-isolated crown.
- **Stage:** charcoal enamel with subtle surface texture. The chamber indicator
  changes warm emission with the stem envelope instead of expanding.

The metal, horn and felt surface shader samples object coordinates (or authored sweep UVs on
profiled `form_*` frames), builds an orthonormal view-space tangent basis
aligned with the grain/brush axis, and combines Parallax Occlusion Mapping
with pre-baked tangent-space normal maps and surface-gradient micro-relief so
textures remain attached to moving links without displacing mesh geometry or
altering tool clearances.

## Texture sources

The timber shader reads longitudinal and cross-section distances from UV0 and UV2. Vertex colors locate each point within the board for edge wear. The finish map covers 32 cm at its native scale. The glass map
packs two surface slopes, wall relief and seed-bubble coverage into RGBA.
The grayscale stamp atlas contains one impression for each MIDI pitch.

| File in `harness/assets/textures/` | R | G | B |
| --- | --- | --- | --- |
| `board_surface.png` | open vessels | dents and scraper marks | oil variation (alpha carries fine fibers) |
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
python3 tools/build_workshop_textures.py
godot --headless --path harness --editor --import --quit
```

## Lighting

A warm key, cool fill and amber rim separate the structures. A procedural sky
supplies broad studio-panel reflections without placing bright panels in the
camera view. A circular recital hall surrounds the stage. A continuous slate floor and
coved wall receive its shadows from every camera angle. Paired brass rings
surround the dais. Fluted arched bays and hooded amber sconces repeat around
the perimeter. The hall uses one mesh and one material. The sconces' glow and
wall wash are shaded into the bays. Moderate ambient occlusion, filtered shadows, filmic tonemapping,
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

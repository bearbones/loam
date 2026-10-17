"""Deterministic, tileable linear-data textures for the clockwork shaders.
No external images: walnut grain/pore/roughness, metal wear/scratches/grit,
plus pre-baked tangent-space normal maps and depth/relief maps for lacquered
grooved wood and anisotropic brushed metallics.
Run `python3 tools/build_surface_textures.py`. RGB channels are linear data.
"""
from pathlib import Path
import numpy as np
from scipy.ndimage import gaussian_filter
from PIL import Image

OUT = Path(__file__).resolve().parents[1] / 'harness/assets/textures'
OUT.mkdir(parents=True, exist_ok=True)
rng = np.random.default_rng(73091)
n = 1024
y, x = np.mgrid[:n, :n] / n


def noise(sigma):
    z = gaussian_filter(rng.normal(size=(n, n)), sigma, mode='wrap')
    return (z - z.mean()) / (z.std() + 1e-9)


def unit(a, scale=0.16):
    return np.clip(0.5 + a * scale, 0.0, 1.0)


def normalize01(a):
    lo, hi = np.percentile(a, 1.0), np.percentile(a, 99.0)
    return np.clip((a - lo) / (hi - lo + 1e-9), 0.0, 1.0)


def normal_from_height(h, strength=1.0):
    """Exact periodic central-difference tangent-space normal map in [0, 1]^3.
    Image X is tangent (+U, along grain/brush); image Y is bitangent (+V, across
    grooves/flutes and brush striations).
    """
    dh_dx = (np.roll(h, -1, axis=1) - np.roll(h, 1, axis=1)) * (0.5 * n / 256.0)
    dh_dy = (np.roll(h, -1, axis=0) - np.roll(h, 1, axis=0)) * (0.5 * n / 256.0)
    nx = -dh_dx * strength
    ny = -dh_dy * strength
    nz = np.ones_like(h)
    inv_len = 1.0 / np.sqrt(nx * nx + ny * ny + nz * nz + 1e-12)
    return (
        np.clip(0.5 + 0.5 * nx * inv_len, 0.0, 1.0),
        np.clip(0.5 + 0.5 * ny * inv_len, 0.0, 1.0),
        np.clip(0.5 + 0.5 * nz * inv_len, 0.0, 1.0),
    )


def save(name, *channels):
    arr = np.uint8(np.stack(channels, axis=-1).clip(0.0, 1.0) * 255.0)
    Image.fromarray(arr).save(OUT / name)


# ---------------------------------------------------------------------------
# 1. Lacquered Grooved Wood (walnut_data, wood_normal, wood_depth)
# ---------------------------------------------------------------------------
# Fibres run along image X (+U); periodic warp avoids stiff ruled pinstripes.
warp = 0.025 * np.sin(2 * np.pi * x) + 0.010 * np.sin(6 * np.pi * x + 3 * np.sin(2 * np.pi * y))
long_grain = noise((1.5, 58))
broad = noise((22, 110))
fine = noise((0.45, 20))
micro_fibre = noise((0.35, 42))

phase = (y + warp) * 2 * np.pi
rings = np.sin(phase * 32 + 1.1 * broad) + 0.35 * np.sin(phase * 73 + 0.5 * long_grain)
grain = unit(0.55 * rings + 0.75 * long_grain + 0.3 * broad)
pores = np.clip((fine + long_grain * 0.3 - 1.15) * 0.65, 0.0, 1.0)
rough = unit(0.5 * noise(1.2) + 0.4 * long_grain)
save('walnut_data.png', grain, pores, rough)

# Carved longitudinal fluting / hand-planed luthiery facets across V (image Y),
# combined with earlywood/latewood ring ridges and deep sunken vessel pores.
flute_phase = (y * 12.0 + 0.015 * broad + 0.005 * np.sin(2 * np.pi * x * 2.0)) * 2 * np.pi
flute_wave = np.cos(flute_phase)
grooves = np.sign(flute_wave) * (np.abs(flute_wave) ** 0.80)
fine_reeding = 0.18 * np.cos(flute_phase * 2.0 + 0.35 * long_grain)
ring_relief = 0.42 * normalize01(rings) + 0.20 * unit(micro_fibre, 0.22)
pore_pits = (pores ** 1.30) * 0.58

# Composite wood substrate height in [0, 1]: proud lands/ridges -> 1, deep grooves/pores -> 0
wood_height = normalize01(0.28 * (0.5 + 0.5 * grooves) + 0.10 * fine_reeding + ring_relief - pore_pits)

# Chatoyancy / fiddleback curl wave along X (+U) that tilts subsurface fibre reflections
curl_phase = 2 * np.pi * (x * 10.0 + 0.08 * np.sin(2 * np.pi * y * 2.0) + 0.05 * broad)
chatoyancy = np.clip(0.5 + 0.28 * np.sin(curl_phase) + 0.22 * grooves, 0.0, 1.0)

# Cavity ambient occlusion inside carved grooves and vessel pores
laplacian = gaussian_filter(wood_height, 3.0, mode='wrap') - wood_height
wood_ao = np.clip(1.0 - 1.35 * np.maximum(0.0, laplacian) - 0.42 * pores, 0.22, 1.0)

wnx, wny, wnz = normal_from_height(wood_height, strength=2.1)
save('wood_normal.png', wnx, wny, wnz)
save('wood_depth.png', wood_height, chatoyancy, wood_ao)

# ---------------------------------------------------------------------------
# 2. Anisotropic Brushed Metallics (metal_data, metal_normal, metal_depth)
# ---------------------------------------------------------------------------
patch = noise(34) * 0.6 + noise(8) * 0.25
scratch = noise((0.5, 50)) * 0.65 + noise((0.6, 7)) * 0.25
micro = noise(0.55)
save('metal_data.png', unit(patch), unit(scratch), unit(micro))

# Multi-scale directional brush striations along X (+U), with a subtle cross-honed
# secondary pass so highlights shimmer realistically across curved metal links.
brush_coarse = noise((0.65, 110))
brush_med = noise((0.38, 56))
brush_fine = noise((0.25, 32))
# Slight +/- 4 deg cross-honing tracks (periodic on the 1024 torus)
cross_a = np.sin(2 * np.pi * (32.0 * y + 2.0 * x) + 1.2 * noise((2.0, 28)))
cross_b = np.sin(2 * np.pi * (48.0 * y - 3.0 * x) + 1.2 * noise((2.0, 28)))
honing = 0.10 * (cross_a + 0.5 * cross_b)

# Fine score lines and micro-pits
score_lines = np.clip((np.abs(brush_med) - 1.45) * 0.75, 0.0, 1.0)
micro_pits = np.clip((micro - 1.75) * 0.45, 0.0, 1.0)

metal_height = normalize01(
    0.42 * brush_coarse + 0.36 * brush_med + 0.24 * brush_fine + honing - 0.38 * score_lines - 0.20 * micro_pits
)

# Brush tangent perturbation / facet glint phase (G) and groove cavity AO (B)
brush_flow = unit(0.55 * brush_fine + 0.25 * honing + 0.20 * noise((1.2, 20)), scale=0.16)
metal_lap = gaussian_filter(metal_height, 2.0, mode='wrap') - metal_height
metal_ao = np.clip(1.0 - 1.15 * np.maximum(0.0, metal_lap) - 0.28 * score_lines - 0.14 * unit(patch), 0.35, 1.0)

mnx, mny, mnz = normal_from_height(metal_height, strength=1.45)
save('metal_normal.png', mnx, mny, mnz)
save('metal_depth.png', metal_height, brush_flow, metal_ao)

# ---------------------------------------------------------------------------
# 3. Woven / Pressed Wool Felt (felt_data)
# ---------------------------------------------------------------------------
save('felt_data.png', unit(noise(0.5)), unit(noise((0.5, 2))), unit(noise((2, 0.5))))
print('Wrote 7 tileable 1024px surface/normal/depth maps to', OUT)

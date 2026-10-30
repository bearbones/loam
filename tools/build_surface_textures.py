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
long_grain = noise((2.2, 58))
broad = noise((22, 110))
fine = noise((1.6, 24))
micro_fibre = noise((1.4, 42))

phase = (y + warp) * 2 * np.pi
rings = np.sin(phase * 32 + 1.1 * broad) + 0.25 * np.sin(phase * 64 + 0.5 * long_grain)
grain = unit(0.55 * rings + 0.75 * long_grain + 0.3 * broad)
pores = np.clip((fine + long_grain * 0.3 - 1.15) * 0.65, 0.0, 1.0)
rough = unit(0.5 * noise(2.2) + 0.4 * long_grain)
save('walnut_data.png', grain, pores, rough)

# Carved longitudinal fluting / hand-planed luthiery facets across V (image Y),
# combined with earlywood/latewood ring ridges and deep sunken vessel pores.
flute_phase = (y * 12.0 + 0.015 * broad + 0.005 * np.sin(2 * np.pi * x * 2.0)) * 2 * np.pi
flute_wave = np.cos(flute_phase)
grooves = np.sign(flute_wave) * (np.abs(flute_wave) ** 0.85)
fine_reeding = 0.14 * np.cos(flute_phase * 2.0 + 0.35 * long_grain)
ring_relief = 0.38 * normalize01(rings) + 0.16 * unit(micro_fibre, 0.18)
pore_pits = (pores ** 1.30) * 0.45

# Composite wood substrate height in [0, 1]: proud lands/ridges -> 1, deep grooves/pores -> 0
wood_height = normalize01(0.28 * (0.5 + 0.5 * grooves) + 0.10 * fine_reeding + ring_relief - pore_pits)
wood_height = gaussian_filter(wood_height, (1.4, 1.8), mode='wrap')

# Chatoyancy / fiddleback curl wave along X (+U) that tilts subsurface fibre reflections
curl_phase = 2 * np.pi * (x * 10.0 + 0.08 * np.sin(2 * np.pi * y * 2.0) + 0.05 * broad)
chatoyancy = np.clip(0.5 + 0.24 * np.sin(curl_phase) + 0.20 * grooves, 0.0, 1.0)

# Cavity ambient occlusion inside carved grooves and vessel pores
laplacian = gaussian_filter(wood_height, 3.0, mode='wrap') - wood_height
wood_ao = np.clip(1.0 - 1.35 * np.maximum(0.0, laplacian) - 0.38 * pores, 0.25, 1.0)

wnx, wny, wnz = normal_from_height(wood_height, strength=1.35)
save('wood_normal.png', wnx, wny, wnz)
save('wood_depth.png', wood_height, chatoyancy, wood_ao)

# ---------------------------------------------------------------------------
# 2. Anisotropic Brushed Metallics (metal_data, metal_normal, metal_depth)
# ---------------------------------------------------------------------------
patch = noise(48) * 0.6 + noise(18) * 0.25
scratch = noise((2.0, 72)) * 0.65 + noise((2.5, 24)) * 0.25
micro = noise(3.0)
save('metal_data.png', unit(patch, 0.10), unit(scratch, 0.10), unit(micro, 0.10))

# Smooth directional brush striations along X (+U) without high-frequency pits/cross-hatch speckles.
brush_coarse = noise((2.4, 140))
brush_med = noise((1.8, 90))
brush_fine = noise((1.4, 60))

metal_height = normalize01(0.50 * brush_coarse + 0.32 * brush_med + 0.18 * brush_fine)
metal_height = gaussian_filter(metal_height, (2.2, 4.0), mode='wrap')

# Brush tangent perturbation / facet glint phase (G) and groove cavity AO (B)
brush_flow = unit(0.65 * brush_coarse + 0.35 * brush_med, scale=0.08)
metal_lap = gaussian_filter(metal_height, 3.0, mode='wrap') - metal_height
metal_ao = np.clip(1.0 - 0.65 * np.maximum(0.0, metal_lap) - 0.08 * unit(patch, 0.10), 0.55, 1.0)

mnx, mny, mnz = normal_from_height(metal_height, strength=0.45)
save('metal_normal.png', mnx, mny, mnz)
save('metal_depth.png', metal_height, brush_flow, metal_ao)

# ---------------------------------------------------------------------------
# 3. Woven / Pressed Wool Felt (felt_data)
# ---------------------------------------------------------------------------
save('felt_data.png', unit(noise(0.5)), unit(noise((0.5, 2))), unit(noise((2, 0.5))))
print('Wrote 7 tileable 1024px surface/normal/depth maps to', OUT)

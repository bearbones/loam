"""Exploration planes: how many recipe dimensions a pad axis blends, and how evenly.

spread 0 → each pad axis is a single recipe dimension (two dimensions explored).
spread 1 → each axis blends every dimension with near-even magnitudes.
Between, the number of dimensions per axis grows linearly and the magnitudes
slide from random (folded normal) toward equal. Signs are always random.

Optional weights rescale each dimension before normalization. Perceptual
weights (inverse sensitivity) make each blended dimension contribute a similar
amount of measured change, so "evenly distributed" means even to the ear
rather than even in raw parameter units.

web/space.js mirrors spread_plane; test_space.mjs and test_soundgarden.py
check the same properties in both languages.
"""
import numpy as np

from .describe import analyze, from_logits, logits, sensitivity

DIMS = 10
RADIUS_TARGET = 0.5   # embedding distance a full-range pad gesture should cover
WEIGHT_CLIP = (0.5, 2.0)  # wider clips push the pad into inaudible dimensions and saturate the radius


def dims_per_axis(spread, dims=DIMS):
    # floor(x + .5), not Python's banker's rounding, so JS Math.round agrees.
    return 1 + int(np.floor(float(np.clip(spread, 0, 1)) * (dims - 1) + .5))


def _axis(spread, k, weights, rng, exclude=None):
    order = rng.permutation(len(weights))
    if exclude is not None:
        order = order[order != exclude]
    chosen = order[:k]
    magnitude = (1 - spread) * np.abs(rng.standard_normal(k)) + spread
    vector = np.zeros(len(weights))
    vector[chosen] = rng.choice([-1.0, 1.0], k) * magnitude * weights[chosen]
    norm = np.linalg.norm(vector)
    return vector / norm if norm > 0 else None


def spread_plane(spread, rng, weights=None, dims=DIMS):
    spread = float(np.clip(spread, 0, 1))
    w = np.ones(dims) if weights is None else np.asarray(weights, dtype=float)
    if w.shape != (dims,) or not np.all(np.isfinite(w)) or np.any(w <= 0):
        raise ValueError("Weights must be positive and one per dimension.")
    k = dims_per_axis(spread, dims)
    for _ in range(256):
        u = _axis(spread, k, w, rng)
        if u is None:
            continue
        v = _axis(spread, k, w, rng, exclude=int(np.argmax(np.abs(u))) if k == 1 else None)
        if v is None:
            continue
        v = v - u * np.dot(u, v)
        norm = np.linalg.norm(v)
        if norm > 1e-3:
            return np.stack([u, v / norm])
    raise RuntimeError("Could not draw an orthogonal plane.")


def perceptual_weights(sens):
    """Inverse sensitivity, median-normalized and clipped so dead dimensions stay tame."""
    s = np.asarray(sens, dtype=float)
    floor = max(np.median(s) * .05, 1e-6)
    w = 1 / np.maximum(s, floor)
    w = w / np.median(w)
    return np.clip(w, *WEIGHT_CLIP)


def calibrate(vector, axes, midi=60):
    """Measure embedding distance between the ±3-logit ends of each axis; suggest a radius."""
    z = logits(vector)
    distances = []
    for axis in np.asarray(axes, dtype=float):
        ends = [analyze(from_logits(z + sign * 3 * axis), midi)[3] for sign in (-1, 1)]
        distances.append(float(np.linalg.norm(ends[1] - ends[0])))
    radius = float(np.clip(RADIUS_TARGET / max(np.mean(distances), .04), .3, 2.0))
    return radius, distances


def plane(vector, rng, spread=1.0, perceptual=True, midi=60):
    """A complete pad suggestion: axes, radius, measured axis distances, sensitivity."""
    sens = sensitivity(vector, midi) if perceptual else None
    weights = perceptual_weights(sens) if perceptual else None
    axes = spread_plane(spread, rng, weights)
    radius, distances = calibrate(vector, axes, midi)
    out = {"axes": axes.tolist(), "radius": radius, "axis_distances": distances, "spread": spread}
    if sens is not None:
        out["sensitivity"] = sens.tolist()
    return out

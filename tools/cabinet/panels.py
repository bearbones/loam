"""Triangulate soundboards and formed shells with actual holes in their skins."""

import numpy as np
from scipy.spatial import Delaunay


def circle(x, y, rx, ry=None, n=48):
    t = np.arange(n) * 2 * np.pi / n
    return np.column_stack(
        [x + rx * np.cos(t), y + (rx if ry is None else ry) * np.sin(t)]
    )


def inside(points, ring):
    x, y = points.T
    mask = np.zeros(len(x), bool)
    for a, b in zip(ring, np.roll(ring, -1, axis=0)):
        if abs(b[1] - a[1]) > 1e-12:
            mask ^= ((a[1] > y) != (b[1] > y)) & (
                x < (b[0] - a[0]) * (y - a[1]) / (b[1] - a[1]) + a[0]
            )
    return mask


def panel(outer, holes, spacing=None, pins=()):
    rings = [np.asarray(r) for r in [outer, *holes]]
    rings = [r[:-1] if np.linalg.norm(r[-1] - r[0]) < 1e-8 else r for r in rings]
    extra = np.empty((0, 2))
    if spacing:
        lo, hi = np.min(outer, axis=0), np.max(outer, axis=0)
        mesh = np.meshgrid(
            *(np.arange(a + spacing * 0.43, b, spacing) for a, b in zip(lo, hi))
        )
        extra = np.column_stack([axis.ravel() for axis in mesh])
        extra = extra[inside(extra, rings[0])]
        for ring in rings[1:]:
            extra = extra[~inside(extra, ring)]
    if len(pins):
        extra = np.vstack([extra, np.asarray(pins)])
    # Split boundary edges which the unconstrained triangulation does not
    # contain. Once recovered, every hole boundary is an actual single rim.
    for _ in range(12):
        points = np.vstack([*rings, extra])
        tris = Delaunay(points).simplices
        edges = {
            tuple(sorted(e))
            for e in np.vstack([tris[:, [0, 1]], tris[:, [1, 2]], tris[:, [2, 0]]])
        }
        cursor = 0
        changed = False
        refined = []
        for loop in rings:
            new = []
            for j, point in enumerate(loop):
                k = (j + 1) % len(loop)
                new.append(point)
                if tuple(sorted((cursor + j, cursor + k))) not in edges:
                    new.append((point + loop[k]) * 0.5)
                    changed = True
            cursor += len(loop)
            refined.append(np.asarray(new))
        if not changed:
            break
        rings = refined
    else:
        raise ValueError("Failed to recover the soundboard boundary")
    centres = points[tris].mean(axis=1)
    keep = inside(centres, rings[0])
    for cut in rings[1:]:
        keep &= ~inside(centres, cut)
    return points, tris[keep], rings

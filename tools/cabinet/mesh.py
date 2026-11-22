"""Portable Y-up glTF geometry for the cabinet, in metres. Batch fixed fittings by finish."""

import json
import math
import struct
from collections import defaultdict
from functools import lru_cache
from io import BytesIO
from pathlib import Path

import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter

ROOT = Path(__file__).resolve().parents[2]
X = np.array([1.0, 0, 0])
Y = np.array([0.0, 1, 0])
Z = np.array([0.0, 0, 1])
O = np.zeros(3)
TAU = math.tau
V = lambda p: np.asarray(p, dtype=float)

# Colour of the unworn finish, metalness, roughness, surface stock.
MATERIALS = {
    "walnut": ("884824", 0, 0.40, "timber"),
    "maple": ("dfa45e", 0, 0.42, "timber"),
    "spruce": ("ebc88c", 0, 0.44, "timber"),
    "ebony": ("41312d", 0, 0.33, "timber"),
    "rose": ("9d4b34", 0, 0.34, "timber"),
    "bamboo": ("cbae6a", 0, 0.48, "cane"),
    "brass": ("dca85d", 0.72, 0.33, "metal"),
    "bronze": ("b77c49", 0.69, 0.38, "metal"),
    "iron": ("414753", 0.66, 0.39, "metal"),
    "copper": ("c37c58", 0.67, 0.35, "metal"),
    "silver": ("ded9bd", 0.72, 0.30, "metal"),
    "tin": ("8faaa3", 0.62, 0.40, "metal"),
    "ivory": ("e9d8aa", 0, 0.33, "bone"),
    "skin": ("d3b389", 0, 0.71, "skin"),
    "wine": ("883938", 0, 0.58, "leather"),
    "leather": ("78462f", 0, 0.58, "leather"),
    "cord": ("b38f56", 0, 0.89, "linen"),
    "red": ("a63c32", 0, 0.70, "linen"),
    "teal": ("286f6e", 0.26, 0.36, "enamel"),
    "navy": ("30445a", 0.33, 0.34, "enamel"),
    "ochre": ("c5943f", 0.16, 0.41, "enamel"),
    "clay": ("b76b50", 0, 0.66, "ceramic"),
    "glaze": ("578d86", 0.13, 0.29, "ceramic"),
    "glass": ("84c5be", 0.16, 0.18, "glass"),
    "smoke": ("49747c", 0.23, 0.25, "glass"),
    "amber": ("ffad52", 0.12, 0.23, "lamp"),
    "ice": ("78e1d8", 0.13, 0.24, "lamp"),
    "black": ("241d1d", 0.05, 0.81, "leather"),
    "baize": ("28423f", 0, 0.96, "baize"),
    "panel": ("233438", 0, 0.81, "panel"),
    "moulding": ("433328", 0, 0.56, "timber"),
    "aged trim": ("71593b", 0.44, 0.48, "metal"),
}


@lru_cache(None)
def maps(stock):
    # A seamless, metric surface field. Height supplies the actual tangent
    # normals; pores, scores and worn lacquer also vary roughness.
    n = 512
    rng = np.random.default_rng(27 + sum(map(ord, stock)))
    y, x = np.mgrid[:n, :n] / n
    noise = rng.normal(size=(n, n))

    def field(sig):
        a = gaussian_filter(rng.normal(size=(n, n)), sig, mode="wrap")
        return a / max(a.std(), 1e-8)

    blot = field(16)
    fine = field(1.3)
    if stock in ("timber", "cane"):
        warp = 0.016 * np.sin(TAU * y) + 0.011 * field(29)
        rings = (
            0.5 + 0.5 * np.cos(TAU * (x * 15 + warp * 7 + 0.17 * np.sin(TAU * 2 * x)))
        ) ** 3
        pores = np.maximum(0, field((7, 0.9)) - 0.62)
        h = 0.14 * rings + 0.16 * field((18, 1.5)) - 0.22 * pores + 0.04 * fine
        col = 0.89 - 0.11 * rings + 0.024 * blot - 0.048 * pores
    elif stock in ("baize", "panel"):
        h = 0.07 * fine + 0.035 * noise
        col = 0.93 + 0.016 * blot + 0.012 * fine
    elif stock in ("metal", "enamel"):
        filemarks = field((0.8, 18))
        dents = np.maximum(0, field(4) - 0.7)
        scores = np.maximum(0, filemarks - 1.45)
        h = 0.20 * blot - 0.43 * dents - 0.38 * scores + 0.11 * fine
        col = 0.88 + 0.054 * blot - 0.085 * dents - 0.09 * scores
    elif stock in ("linen", "leather", "skin"):
        weave = np.cos(TAU * x * 48) * np.cos(TAU * y * 46)
        h = 0.22 * fine + 0.18 * noise + 0.35 * weave * (stock == "linen") + 0.12 * blot
        col = 0.87 + 0.056 * blot + 0.04 * fine + 0.06 * weave * (stock == "linen")
    else:
        h = (
            0.19 * fine
            + 0.16 * blot
            + 0.12 * np.cos(TAU * y * 21) * (stock == "ceramic")
        )
        col = 0.89 + 0.039 * blot + 0.036 * fine
    col = np.clip(col, 0.4, 1)
    stain = np.clip(blot - 0.35, 0, 2) * (0.042 if stock == "metal" else 0.019)
    color = np.dstack([col - stain, col - 0.7 * stain, col - 0.3 * stain])
    dx = (np.roll(h, -1, 1) - np.roll(h, 1, 1)) * 0.49
    dy = (np.roll(h, -1, 0) - np.roll(h, 1, 0)) * 0.49
    normals = np.dstack([-dx, dy, np.ones_like(h)])
    normals = normals / np.linalg.norm(normals, axis=2)[:, :, None] * 0.5 + 0.5
    rough = np.clip(0.84 + 0.075 * blot + 0.06 * fine, 0.48, 1)
    orm = np.dstack([np.ones_like(h), rough, np.ones_like(h)])
    imgs = []
    for array in (color, normals, orm):
        stream = BytesIO()
        Image.fromarray(np.uint8(np.clip(array, 0, 1) * 255 + 0.5)).save(
            stream, "JPEG", quality=87, subsampling=0
        )
        imgs.append(stream.getvalue())
    return imgs


def unit(p):
    return p / max(np.linalg.norm(p), 1e-12)


def axes(axis):
    axis = unit(V(axis))
    ref = X if abs(axis[0]) < 0.86 else Z
    u = unit(ref - axis * np.dot(ref, axis))
    return u, np.cross(axis, u)


def tangents(points, normals, uv, faces):
    """Bake an orthonormal UV frame at the shared vertices of each finish."""
    a, b, c = faces.T
    e1, e2 = points[b] - points[a], points[c] - points[a]
    t1, t2 = uv[b] - uv[a], uv[c] - uv[a]
    det = t1[:, 0] * t2[:, 1] - t1[:, 1] * t2[:, 0]
    area = np.linalg.norm(np.cross(e1, e2), axis=1)
    scale = np.divide(area, det, out=np.zeros_like(area), where=np.abs(det) > 1e-12)[
        :, None
    ]
    along = (e1 * t2[:, 1, None] - e2 * t1[:, 1, None]) * scale
    across = (e2 * t1[:, 0, None] - e1 * t2[:, 0, None]) * scale
    u = np.zeros_like(points)
    v = np.zeros_like(points)
    for index in (a, b, c):
        np.add.at(u, index, along)
        np.add.at(v, index, across)
    u -= normals * (normals * u).sum(axis=1)[:, None]
    length = np.linalg.norm(u, axis=1)
    weak = length < 1e-9
    guide = np.where(np.abs(normals[weak, 0, None]) < 0.85, X, Z)
    u[weak] = np.cross(normals[weak], guide)
    u /= np.maximum(np.linalg.norm(u, axis=1)[:, None], 1e-12)
    sign = np.where((np.cross(normals, u) * v).sum(axis=1) < 0, -1.0, 1.0)
    return np.column_stack((u, sign))


class Mesh:
    def __init__(self):
        self.parts = defaultdict(list)

    def surface(self, rows, mat, tile=0.28, flip=False):
        a = V(rows)
        h, w = a.shape[:2]
        dp = np.gradient(a, axis=1)
        dq = np.gradient(a, axis=0)
        norm = np.cross(dp, dq)
        if np.allclose(a[:, 0], a[:, -1]):
            norm[:, 0] = norm[:, -1] = norm[:, 0] + norm[:, -1]
        norm /= np.maximum(1e-12, np.linalg.norm(norm, axis=2)[:, :, None])
        # Each section keeps its circumference and each stave its length in
        # material coordinates. Enlarging a body increases its number of grains.
        u = np.cumsum(np.linalg.norm(np.diff(a, axis=1), axis=2), axis=1)
        v = np.cumsum(np.linalg.norm(np.diff(a, axis=0), axis=2), axis=0)
        uv = (
            np.stack((np.pad(u, ((0, 0), (1, 0))), np.pad(v, ((1, 0), (0, 0)))), axis=2)
            / tile
        )
        i = (np.arange(h - 1)[:, None] * w + np.arange(w - 1)[None, :]).ravel()
        faces = np.stack([i, i + 1, i + w, i + 1, i + w + 1, i + w], axis=1).reshape(
            -1, 3
        )
        if flip:
            norm = -norm
            faces = faces[:, ::-1]
        self.parts[mat].append(
            (a.reshape(-1, 3), norm.reshape(-1, 3), uv.reshape(-1, 2), faces)
        )

    def cap(self, row, axis, mat):
        row = V(row)[:-1]
        n = len(row)
        centre = row.mean(axis=0)
        u, v = axes(axis)
        points = np.vstack([centre, row])
        uv = (points - centre) @ np.array([u, v]).T / 0.28
        face = np.stack(
            [np.zeros(n, int), 1 + np.arange(n), 1 + (np.arange(n) + 1) % n], axis=1
        )
        # Compute winding from the whole rim, including concave shoulders.
        oriented = np.cross(row - centre, np.roll(row, -1, axis=0) - centre).sum(axis=0)
        if np.dot(oriented, axis) < 0:
            face = face[:, ::-1]
        if MATERIALS[mat][3] == "timber" and np.ptp(uv[:, 0]) > 1.25 * np.ptp(uv[:, 1]):
            uv = uv[:, ::-1]
        self.parts[mat].append((points, np.tile(unit(axis), (n + 1, 1)), uv, face))

    def turn(self, c, axis, profile, mat, n=40, caps=True):
        c = V(c)
        axis = unit(V(axis))
        u, v = axes(axis)
        a = np.linspace(0, TAU, n + 1)
        around = np.cos(a)[:, None] * u + np.sin(a)[:, None] * v
        rows = [c + h * axis + r * around for h, r in profile]
        self.surface(rows, mat)
        if caps:
            self.cap(rows[0], -axis, mat)
            self.cap(rows[-1], axis, mat)

    def rod(self, a, b, r, mat, r2=None, n=12):
        a, b = V(a), V(b)
        length = np.linalg.norm(b - a)
        if length < 1e-7:
            return
        r2 = r if r2 is None else r2
        self.turn(a, b - a, [(0, r), (length, r2)], mat, n)

    def ball(self, c, size, mat, n=32):
        c = V(c)
        size = np.broadcast_to(size, (3,))
        a = np.linspace(0, TAU, n + 1)
        circle = np.stack([np.cos(a), 0 * a, -np.sin(a)], axis=1)
        rows = [
            c + size * (np.cos(lat) * circle + np.sin(lat) * Y)
            for lat in np.linspace(-1.566, 1.566, max(10, n // 2))
        ]
        self.surface(rows, mat)
        self.cap(rows[0], -Y, mat)
        self.cap(rows[-1], Y, mat)

    def ring(self, c, axis, r, t, mat, n=48):
        c = V(c)
        axis = unit(V(axis))
        u, v = axes(axis)
        theta = np.linspace(0, TAU, n + 1)
        radial = np.cos(theta)[:, None] * u + np.sin(theta)[:, None] * v
        self.surface(
            [
                c + (r + t * np.cos(a)) * radial + t * np.sin(a) * axis
                for a in np.linspace(0, TAU, 9)
            ],
            mat,
        )

    def tube(self, points, r, mat, n=12):
        pts = V(points)
        directions = np.gradient(pts, axis=0)
        u, _ = axes(directions[0])
        a = np.linspace(0, TAU, n + 1)
        rows = []
        for pt, dr in zip(pts, directions):
            dr = unit(dr)
            u = unit(u - dr * np.dot(dr, u))
            v = np.cross(dr, u)
            rows.append(pt + r * (np.cos(a)[:, None] * u + np.sin(a)[:, None] * v))
        self.surface(rows, mat)
        self.cap(rows[0], -unit(directions[0]), mat)
        self.cap(rows[-1], unit(directions[-1]), mat)

    def case(self, c, size, mat, r=0.035):
        # Rolled corner returns and chamfered upper/lower edges.
        c = V(c)
        w, h, d = V(size) / 2
        r = min(r, w * 0.8, d * 0.8, h * 0.8)
        rows = []
        for y, shrink in [
            (-h, r * 0.40),
            (-h + r * 0.42, 0),
            (h - r * 0.42, 0),
            (h, r * 0.40),
        ]:
            points = []
            for k, (sx, sz) in enumerate([(1, -1), (-1, -1), (-1, 1), (1, 1)]):
                for angle in np.linspace(k * np.pi / 2, (k + 1) * np.pi / 2, 6):
                    points.append(
                        c
                        + [
                            sx * (w - r) + np.cos(angle) * (r - shrink),
                            y,
                            sz * (d - r) - np.sin(angle) * (r - shrink),
                        ]
                    )
            rows.append(np.vstack([points, points[0]]))
        self.surface(rows, mat)
        self.cap(rows[0], -Y, mat)
        self.cap(rows[-1], Y, mat)

    def screw(self, c, axis, r=0.015):
        c = V(c)
        axis = unit(V(axis))
        u, _v = axes(axis)
        self.turn(c, axis, [(0, r), (0.25 * r, r), (0.38 * r, 0.80 * r)], "brass", 12)
        self.rod(
            c + axis * r * 0.395 - u * 0.62 * r,
            c + axis * r * 0.395 + u * 0.62 * r,
            r * 0.105,
            "iron",
            n=6,
        )

    def rosette(self, c, axis, r, petals=8):
        c = V(c)
        axis = unit(V(axis))
        u, v = axes(axis)
        self.turn(c, axis, [(-0.004, r), (0.001, r)], "ebony")
        for rr in [r * 0.95, r * 0.84, r * 0.28]:
            self.ring(c + axis * 0.004, axis, rr, r * 0.024, "brass")
        a = np.linspace(0, TAU, 65)
        radius = r * (0.55 + 0.25 * np.cos(petals * a))
        self.tube(
            c
            + axis * 0.006
            + (np.cos(a)[:, None] * u + np.sin(a)[:, None] * v) * radius[:, None],
            r * 0.028,
            "maple",
            7,
        )

    def staples(self, c, across, along):
        c = V(c)
        across = V(across)
        along = V(along)
        for j in range(3):
            p = c + (j - 1) * along
            self.tube(
                [
                    p - across,
                    p - across + 0.008 * Y,
                    p + across + 0.008 * Y,
                    p + across,
                ],
                0.004,
                "copper",
                8,
            )


class Asset:
    def __init__(self, key):
        self.key = key
        self.fixed = Mesh()
        self.nodes = []
        self.parents = {}
        self.tracks = []

    def part(self, name, pivot=O, parent=None):
        m = Mesh()
        if parent is not None:
            self.parents[len(self.nodes) + 1] = next(
                i + 1 for i, node in enumerate(self.nodes) if node[2] is parent
            )
        self.nodes.append((name, V(pivot), m))
        return m

    def drive(self, part, kind, axis, extent, lanes=None, rest=0.0, rate=1.0):
        index = next(i for i, node in enumerate(self.nodes) if node[2] is part)
        self.tracks.append(
            {
                "node": index + 1,
                "kind": kind,
                "axis": V(axis),
                "extent": extent,
                "lanes": None if lanes is None else tuple(lanes),
                "rest": rest,
                "rate": rate,
            }
        )

    def export(self, path, events, duration):
        from .motion import evaluate

        doc = {
            "asset": {"version": "2.0", "generator": "Loam cabinet workshop"},
            "scene": 0,
            "scenes": [{"nodes": []}],
            "nodes": [],
            "meshes": [],
            "materials": [],
            "images": [],
            "textures": [],
            "bufferViews": [],
            "accessors": [],
        }
        data = bytearray()

        def block(blob, target=None):
            data.extend(bytes(-len(data) % 4))
            idx = len(doc["bufferViews"])
            view = {"buffer": 0, "byteOffset": len(data), "byteLength": len(blob)}
            if target:
                view["target"] = target
            doc["bufferViews"].append(view)
            data.extend(blob)
            return idx

        def accessor(a, kind, indices=False, target=None, bounds=False):
            a = np.ascontiguousarray(a, dtype="<u4" if indices else "<f4")
            info = {
                "bufferView": block(a.tobytes(), target),
                "componentType": 5125 if indices else 5126,
                "count": len(a),
                "type": kind,
            }
            if bounds:
                info.update(
                    min=np.min(a, axis=0).reshape(-1).tolist(),
                    max=np.max(a, axis=0).reshape(-1).tolist(),
                )
            doc["accessors"].append(info)
            return len(doc["accessors"]) - 1

        mats = {}
        images = {}

        def material(name):
            if name in mats:
                return mats[name]
            hexcolor, metal, rough, stock = MATERIALS[name]
            if stock not in images:
                ids = []
                for k, blob in enumerate(maps(stock)):
                    image = len(doc["images"])
                    doc["images"].append(
                        {
                            "name": f"{stock} {('surface', 'relief', 'roughness')[k]}",
                            "mimeType": "image/jpeg",
                            "bufferView": block(blob),
                        }
                    )
                    doc["textures"].append({"source": image})
                    ids.append(len(doc["textures"]) - 1)
                images[stock] = ids
            base, norm, orm = images[stock]
            rgb = [
                ((int(hexcolor[i : i + 2], 16) / 255 + 0.055) / 1.055) ** 2.4
                for i in (0, 2, 4)
            ]
            pbr = {
                "baseColorFactor": rgb + [1.0],
                "baseColorTexture": {"index": base},
                "metallicFactor": metal,
                "roughnessFactor": rough,
                "metallicRoughnessTexture": {"index": orm},
            }
            entry = {
                "name": name,
                "pbrMetallicRoughness": pbr,
                "normalTexture": {"index": norm, "scale": 0.72},
                "doubleSided": True,
            }
            if stock == "lamp":
                entry["emissiveFactor"] = [float(x) * 0.68 for x in rgb]
            if stock == "glass":
                # Leave the far rim legible in viewers without transmission.
                pbr["baseColorFactor"][-1] = 0.59
                entry["alphaMode"] = "BLEND"
            mats[name] = len(doc["materials"])
            doc["materials"].append(entry)
            return mats[name]

        lo = np.full(3, np.inf)
        hi = -lo
        for i, (name, pivot, mesh) in enumerate(
            [("Workshop casting", O, self.fixed)] + self.nodes
        ):
            world = pivot.copy()
            ancestor = i
            while ancestor in self.parents:
                ancestor = self.parents[ancestor]
                world += self.nodes[ancestor - 1][1]
            prim = []
            for mat, parts in mesh.parts.items():
                vv, nn, uv, ff = zip(*parts)
                offsets = np.cumsum([0] + [len(a) for a in vv[:-1]])
                faces = np.concatenate([f + k for f, k in zip(ff, offsets)])
                pts = np.vstack(vv)
                lo = np.minimum(lo, pts.min(0) + world)
                hi = np.maximum(hi, pts.max(0) + world)
                normals = np.vstack(nn)
                texcoords = np.vstack(uv)
                prim.append(
                    {
                        "attributes": {
                            "POSITION": accessor(
                                pts, "VEC3", target=34962, bounds=True
                            ),
                            "NORMAL": accessor(normals, "VEC3", target=34962),
                            "TEXCOORD_0": accessor(texcoords, "VEC2", target=34962),
                            "TANGENT": accessor(
                                tangents(pts, normals, texcoords, faces),
                                "VEC4",
                                target=34962,
                            ),
                        },
                        "indices": accessor(faces.ravel(), "SCALAR", True, 34963),
                        "material": material(mat),
                    }
                )
            assert prim, name
            doc["meshes"].append({"name": name, "primitives": prim})
            doc["nodes"].append(
                {"name": name, "mesh": i, "translation": pivot.tolist()}
            )
            if i in self.parents:
                doc["nodes"][self.parents[i]].setdefault("children", []).append(i)
            else:
                doc["scenes"][0]["nodes"].append(i)
        animation = {"name": "Recital", "samplers": [], "channels": []}
        for tr in self.tracks:
            times, values, channel = evaluate(
                tr, events, duration, self.nodes[tr["node"] - 1][1]
            )
            # The exported instrument also has a usable resting pose in
            # viewers with playback disabled. Unused keys retain that pose.
            doc["nodes"][tr["node"]][channel] = values[0].tolist()
            if np.allclose(values, values[0], rtol=0, atol=1e-8):
                continue
            animation["samplers"].append(
                {
                    "input": accessor(times, "SCALAR", bounds=True),
                    "output": accessor(
                        values, "VEC4" if channel == "rotation" else "VEC3"
                    ),
                    "interpolation": "LINEAR",
                }
            )
            animation["channels"].append(
                {
                    "sampler": len(animation["samplers"]) - 1,
                    "target": {"node": tr["node"], "path": channel},
                }
            )
        if animation["channels"]:
            doc["animations"] = [animation]
        doc["extras"] = {
            "loamInstrument": self.key,
            "bounds": [lo.tolist(), hi.tolist()],
        }
        data.extend(bytes(-len(data) % 4))
        doc["buffers"] = [{"byteLength": len(data)}]
        raw = json.dumps(doc, separators=(",", ":")).encode()
        raw += b" " * (-len(raw) % 4)
        path.write_bytes(
            struct.pack("<4sII", b"glTF", 2, 28 + len(raw) + len(data))
            + struct.pack("<I4s", len(raw), b"JSON")
            + raw
            + struct.pack("<I4s", len(data), b"BIN\0")
            + data
        )
        return {
            "lo": lo.tolist(),
            "hi": hi.tolist(),
            "actuators": len(self.tracks),
            "moving_tracks": len(animation["channels"]),
        }

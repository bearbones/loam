"""Portable Y-up glTF geometry for the cabinet, in metres. Batch fixed fittings by finish."""

import itertools
import json
import math
import struct
from collections import defaultdict
from pathlib import Path

import numpy as np

from .finishes import paint, paint_face

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
    "tempered": ("454e62", 0.9, 0.35, "steel"),
    "gourd": ("bb8851", 0, 0.58, "gourd"),
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
        self.morph = None

    def surface(self, rows, mat, tile=0.28, flip=False, along_u=False):
        a = V(rows)
        h, w = a.shape[:2]
        dp = np.gradient(a, axis=1)
        dq = np.gradient(a, axis=0)
        norm = np.cross(dp, dq)
        if np.allclose(a[:, 0], a[:, -1]):
            norm[:, 0] = norm[:, -1] = norm[:, 0] + norm[:, -1]
        norm /= np.maximum(1e-12, np.linalg.norm(norm, axis=2)[:, :, None])
        # Fixed longitude prevents grain from spiralling as a turned part
        # widens. Each section is still parameterised by distance along it.
        u = np.pad(
            np.cumsum(np.linalg.norm(np.diff(a, axis=1), axis=2), axis=1),
            ((0, 0), (1, 0)),
        )
        u *= np.mean(u[:, -1]) / np.maximum(u[:, -1, None], 1e-10)
        v = np.r_[0, np.cumsum(np.linalg.norm(np.diff(a, axis=0), axis=2).mean(axis=1))]
        uv = np.stack([u, np.broadcast_to(v[:, None], u.shape)], axis=2) / tile
        if along_u:
            uv = uv[:, :, ::-1]
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

    def ball(self, c, size, mat, n=32, pole=Y):
        c = V(c)
        size = np.broadcast_to(size, (3,))
        a = np.linspace(0, TAU, n + 1)
        axis = unit(V(pole))
        u, v = axes(axis)
        circle = np.cos(a)[:, None] * u + np.sin(a)[:, None] * v
        rows = [
            c + size * (np.cos(lat) * circle + np.sin(lat) * axis)
            for lat in np.linspace(-1.566, 1.566, max(10, n // 2))
        ]
        self.surface(rows, mat)
        self.cap(rows[0], -axis, mat)
        self.cap(rows[-1], axis, mat)

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
        pts = pts[np.r_[True, np.linalg.norm(np.diff(pts, axis=0), axis=1) > 1e-7]]
        if len(pts) < 2:
            return
        closed = np.linalg.norm(pts[-1] - pts[0]) < 1e-6
        if closed:
            pts = pts[:-1]
        delta = np.roll(pts, -1, axis=0) - pts
        spacing = np.linalg.norm(delta, axis=1)
        outgoing = delta / np.maximum(spacing[:, None], 1e-12)
        incoming = np.roll(outgoing, 1, axis=0)
        if not closed:
            incoming[0] = outgoing[0]
            outgoing[-1] = incoming[-1]
        directions = incoming + outgoing
        directions /= np.maximum(np.linalg.norm(directions, axis=1)[:, None], 1e-12)
        # Carry the section frame by the minimum rotation between tangents.
        # Join periodic sweeps with one matching ring and no overlapping end caps.
        path = np.vstack([directions, directions[0]]) if closed else directions
        u = axes(path[0])[0]
        frames = [u]
        for prev, cur in itertools.pairwise(path):
            v = np.cross(prev, cur)
            u = (
                u
                + np.cross(v, u)
                + np.cross(v, np.cross(v, u)) / max(1e-8, 1 + np.dot(prev, cur))
            )
            u = unit(u - cur * np.dot(u, cur))
            frames.append(u)
        u = np.array(frames)
        if closed:
            twist = np.arctan2(
                np.dot(path[0], np.cross(u[-1], u[0])), np.dot(u[-1], u[0])
            )
            angle = twist * np.r_[0, np.cumsum(spacing)] / sum(spacing)
            u = (
                u * np.cos(angle[:, None]) + np.cross(path, u) * np.sin(angle[:, None])
            )[:-1]
        v = np.cross(directions, u)
        theta = np.linspace(0, TAU, n + 1)
        # In tight engraving corners the cut narrows before the turn.
        bend = np.sqrt(np.maximum(0, (1 - (incoming * outgoing).sum(axis=1)) * 0.5))
        reach = np.minimum(spacing, np.roll(spacing, 1))
        radii = np.minimum(r, 0.42 * reach / np.maximum(bend, 1e-6))
        rows = pts[:, None, :] + radii[:, None, None] * (
            u[:, None, :] * np.cos(theta)[None, :, None]
            + v[:, None, :] * np.sin(theta)[None, :, None]
        )
        self.surface(np.concatenate([rows, rows[:1]]) if closed else rows, mat)
        if not closed:
            self.cap(rows[0], -directions[0], mat)
            self.cap(rows[-1], directions[-1], mat)

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
        self.surface(
            rows, mat, along_u=MATERIALS[mat][3] == "timber" and max(w, d) > h * 1.25
        )
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

    def rosette(self, c, axis, r, petals=8, pierced=False):
        c = V(c)
        axis = unit(V(axis))
        u, v = axes(axis)
        if not pierced:
            self.turn(c, axis, [(-0.004, r), (0.001, r)], "ebony")
        else:
            for a in np.arange(petals) * TAU / petals:
                dr = u * np.cos(a) + v * np.sin(a)
                self.rod(c + dr * r * 0.25, c + dr * r * 0.96, r * 0.026, "walnut", n=7)
        for rr in [r * 0.95, r * 0.84, r * 0.28]:
            self.ring(c + axis * 0.004, axis, rr, r * 0.024, "brass")
        a = np.linspace(0, TAU, 65)
        radius = r * (0.56 + 0.20 * np.cos(petals * a))
        self.tube(
            c
            + axis * 0.006
            + (np.cos(a)[:, None] * u + np.sin(a)[:, None] * v) * radius[:, None],
            r * 0.018,
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

        def material(name, featured):
            identity = (name, featured)
            if identity in mats:
                return mats[identity]
            color, metal, rough, stock = MATERIALS[name]
            label = f"{self.key} {name}" if featured else name
            maps = paint(
                self.key if featured else "", name, color, metal, rough, stock, featured
            )
            ids = []
            for i, blob in enumerate(maps):
                image = len(doc["images"])
                doc["images"].append(
                    {
                        "name": label + " " + ("albedo", "normal", "surface")[i],
                        "mimeType": "image/jpeg" if i == 0 else "image/png",
                        "bufferView": block(blob),
                    }
                )
                doc["textures"].append({"source": image})
                ids.append(image)
            pbr = {
                "baseColorTexture": {"index": ids[0]},
                "metallicRoughnessTexture": {"index": ids[2]},
                "metallicFactor": 1.0,
                "roughnessFactor": 1.0,
            }
            entry = {
                "name": label,
                "pbrMetallicRoughness": pbr,
                "normalTexture": {"index": ids[1]},
                "occlusionTexture": {"index": ids[2], "strength": 0.55},
                "doubleSided": True,
            }
            if stock == "lamp":
                entry["emissiveFactor"] = [
                    (int(color[j : j + 2], 16) / 255) ** 2.2 * 0.68 for j in [0, 2, 4]
                ]
            if stock == "glass":
                pbr["baseColorFactor"] = [
                    1.0,
                    1.0,
                    1.0,
                    0.29 if name == "glass" else 0.43,
                ]
                entry["alphaMode"] = "BLEND"
            mats[identity] = len(doc["materials"])
            doc["materials"].append(entry)
            return mats[identity]

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
            coatings = defaultdict(list)
            for stock, parts in mesh.parts.items():
                finish = paint_face(self.key, stock, name)
                for p, n, uv, f in parts:
                    featured = finish is not None and finish.fits(p, n)
                    if featured:
                        uv = finish.uv(p + world)
                        if finish.plane == "y-turn":
                            crossing = np.ptp(uv[f, 0], axis=1) > 0.5
                            if np.any(crossing):
                                seams = f[crossing].copy()
                                low = uv[seams, 0] < 0.5
                                verts, indices = np.unique(
                                    seams[low], return_inverse=True
                                )
                                seams[low] = len(p) + indices
                                f = f.copy()
                                f[crossing] = seams
                                p = np.vstack([p, p[verts]])
                                n = np.vstack([n, n[verts]])
                                uv = np.vstack([uv, uv[verts] + [1, 0]])
                    coatings[stock, featured].append((p, n, uv, f))
            for (mat, featured), parts in coatings.items():
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
                        "material": material(mat, featured),
                    }
                )
                if mesh.morph is not None:
                    displacement, normal_change = mesh.morph(pts, normals)
                    prim[-1]["targets"] = [
                        {
                            "POSITION": accessor(
                                displacement, "VEC3", target=34962, bounds=True
                            ),
                            "NORMAL": accessor(normal_change, "VEC3", target=34962),
                        }
                    ]
            assert prim, name
            doc["meshes"].append({"name": name, "primitives": prim})
            if mesh.morph is not None:
                doc["meshes"][-1].update(
                    weights=[0.0], extras={"targetNames": ["Diaphragm"]}
                )
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
            if tr["lanes"] is not None:
                doc["nodes"][tr["node"]].setdefault("extras", {})[
                    "playingPositions"
                ] = list(tr["lanes"])
            doc["nodes"][tr["node"]][channel] = values[0].tolist()
            if np.allclose(values, values[0], rtol=0, atol=1e-8):
                continue
            animation["samplers"].append(
                {
                    "input": accessor(times, "SCALAR", bounds=True),
                    "output": accessor(
                        values,
                        {"rotation": "VEC4", "weights": "SCALAR"}.get(channel, "VEC3"),
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

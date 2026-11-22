"""Sample the exported recital and test moving-part clearances with python-fcl.

Check every pair of mechanisms, distal beater heads against the fixed casting
on the suspended percussion, and the Magnetar's armatures and coil clearances.
The score and GLB supply the transforms, morphs, and assigned playing positions.
"""

import argparse
import itertools
import json
from collections import Counter
from dataclasses import dataclass

import fcl
import numpy as np
from check_cabinet_geometry import ASSETS, read_glb, sheets
from scipy.spatial.transform import Rotation, Slerp


def solid(points, faces):
    mesh = fcl.BVHModel()
    mesh.beginModel(len(faces), len(points))
    mesh.addSubModel(
        np.ascontiguousarray(points, dtype=float),
        np.ascontiguousarray(faces, dtype=np.int32),
    )
    mesh.endModel()
    return fcl.CollisionObject(mesh)


@dataclass
class Body:
    name: str
    node: int
    points: np.ndarray
    faces: np.ndarray
    delta: np.ndarray | None = None

    def __post_init__(self):
        self.object = solid(self.points, self.faces)
        self.lower = self.points.min(0)
        self.upper = self.points.max(0)

    def place(self, origin, linear, weight):
        points = self.points
        deform = self.delta is not None and abs(weight) > 1e-8
        if deform:
            points = points + self.delta * weight
        if not np.allclose(linear.T @ linear, np.eye(3), rtol=0, atol=1e-7):
            obj = solid(points @ linear.T, self.faces)
            obj.setTranslation(origin)
        else:
            obj = solid(points, self.faces) if deform else self.object
            obj.setTransform(fcl.Transform(linear, origin))
        return obj


def poses(doc, data, time):
    nodes = doc["nodes"]
    shape = (len(time), len(nodes))
    translations = np.empty((*shape, 3))
    rotations = np.empty((*shape, 3, 3))
    scales = np.empty((*shape, 3))
    weights = np.zeros(shape)
    for i, node in enumerate(nodes):
        translations[:, i] = node.get("translation", [0, 0, 0])
        scales[:, i] = node.get("scale", [1, 1, 1])
        rotations[:, i] = Rotation.from_quat(
            node.get("rotation", [0, 0, 0, 1])
        ).as_matrix()
        weights[:, i] = node.get("weights", [0])[0]
    anim = doc["animations"][0]
    for channel in anim["channels"]:
        sampler = anim["samplers"][channel["sampler"]]
        assert sampler["interpolation"] == "LINEAR"
        src = data(sampler["input"]).ravel()
        dst = data(sampler["output"])
        i = channel["target"]["node"]
        path = channel["target"]["path"]
        if path == "rotation":
            rotations[:, i] = Slerp(src, Rotation.from_quat(dst))(
                np.clip(time, src[0], src[-1])
            ).as_matrix()
        elif path == "weights":
            weights[:, i] = np.interp(time, src, dst.ravel())
        else:
            target = {"scale": scales, "translation": translations}[path]
            target[:, i] = np.stack([np.interp(time, src, v) for v in dst.T], axis=1)
    linear = rotations * scales[:, :, None, :]

    def inherit(i):
        for child in nodes[i].get("children", []):
            translations[:, child] = translations[:, i] + np.einsum(
                "tij,tj->ti", linear[:, i], translations[:, child]
            )
            linear[:, child] = linear[:, i] @ linear[:, child]
            inherit(child)

    for root in doc["scenes"][doc.get("scene", 0)]["nodes"]:
        inherit(root)
    return translations, linear, weights


def collision_bodies(key, doc, data):
    bodies = []
    probes = []
    windings = []
    for i, node in enumerate(doc["nodes"]):
        points = []
        delta = []
        faces = []
        offset = 0
        has_morph = False
        for prim in doc["meshes"][node["mesh"]]["primitives"]:
            xyz = data(prim["attributes"]["POSITION"]).astype(float)
            tris = data(prim["indices"]).reshape(-1, 3)
            mat = doc["materials"][prim["material"]]["name"]
            points.append(xyz)
            faces.append(tris + offset)
            offset += len(xyz)
            morph = prim.get("targets", [])
            if morph:
                assert len(morph) == 1
                has_morph = True
            delta.append(data(morph[0]["POSITION"]) if morph else np.zeros_like(xyz))
            if key == "magnetar" and i == 0 and mat == "copper":
                for sheet in sheets(tris):
                    unique, local = np.unique(sheet, return_inverse=True)
                    part = xyz[unique]
                    if np.ptp(part[:, 0]) > 0.39 and np.ptp(part[:, 1]) > 0.39:
                        windings.append(
                            Body(
                                f"Coil winding {len(windings) + 1}",
                                i,
                                part,
                                local.reshape(-1, 3),
                            )
                        )
            if (
                key == "magnetar"
                and node["name"].startswith("Field armature")
                and mat != "iron"
            ):
                probes.append(Body(node["name"] + " " + mat, i, xyz, tris))
        pts = np.vstack(points)
        tris = np.vstack(faces)
        name = node["name"]
        bodies.append(Body(name, i, pts, tris, np.vstack(delta) if has_morph else None))
        if key in ("balafon", "handpan", "kulintang") and name.startswith("Beater"):
            # Omit the pivot and shaft seated in the fixed hinge.
            dist = np.linalg.norm(pts, axis=1)
            distal = tris[np.min(dist[tris], axis=1) > 0.78 * dist.max()]
            ids, local = np.unique(distal, return_inverse=True)
            probes.append(Body(name + " head", i, pts[ids], local.reshape(-1, 3)))
    count = len(bodies)
    pairs = list(itertools.combinations(range(1, count), 2))
    for probe in probes:
        pairs.append((0, len(bodies)))
        bodies.append(probe)
    if key == "magnetar":
        assert len(windings) == 3
        pairs.extend(itertools.combinations(range(len(bodies), len(bodies) + 3), 2))
        bodies.extend(windings)
    return bodies, pairs


def allowed_contacts(key, nodes):
    names = [node["name"] for node in nodes]
    wires = [i for i, n in enumerate(names) if n.startswith("Wire ")]
    seams = set(zip(wires[::2], wires[1::2], strict=True))
    positions = [set(n.get("extras", {}).get("playingPositions", [])) for n in nodes]
    for a, b in itertools.combinations(range(1, len(nodes)), 2):
        left, right = names[a], names[b]
        same_position = bool(positions[a] & positions[b])
        if a in wires and right.startswith("Fitted bow"):
            seams.add((a, b))
        elif (
            same_position
            and right.startswith("Horn pick")
            and (a in wires or left.startswith("Forged tongue"))
        ):
            if key not in ("koto", "kora") or b - a in (1, 2):
                seams.add((a, b))
        else:
            played_surface = left.startswith(
                ("Tied bar", "Bossed gong", "Hammered tone field")
            )
            beater = played_surface and right.startswith("Beater") and same_position
            glass_rim = left == "Glass spindle" and right.startswith("Pallet ")
            bellow_end = left == "Gusseted leather bellows" and right.endswith(
                "reed chest"
            )
            chest_button = left.endswith("reed chest") and b in nodes[a].get(
                "children", []
            )
            pulley = (left, right) == ("Spliced drive pulley", "Laced belt splice")
            if any((beater, glass_rim, bellow_end, chest_button, pulley)):
                seams.add((a, b))
    return seams


def attack_gaps(nodes, bodies, allowed, events, frames, origin, linear, weights):
    """Measure the air gap even when two tangent triangles do not intersect."""
    gaps = []
    strikes = [(a, b) for a, b in allowed if nodes[b]["name"].startswith("Beater")]
    for event in events:
        t = np.searchsorted(frames, event["t"])
        for a, b in strikes:
            if event["lane"] not in nodes[b]["extras"]["playingPositions"]:
                continue
            objects = [
                bodies[i].place(origin[t, i], linear[t, i], weights[t, i])
                for i in (a, b)
            ]
            gap = fcl.distance(*objects, fcl.DistanceRequest(), fcl.DistanceResult())
            gaps.append(max(0.0, gap))
    return gaps


def check(item, fps):
    key = item["id"]
    doc, data = read_glb(ASSETS / (key + ".glb"))
    frames = np.unique(
        np.r_[
            np.arange(0, item["duration"], 1 / fps),
            item["duration"],
            [e["t"] for e in item["events"]],
        ]
    )
    origin, linear, weights = poses(doc, data, frames)
    bodies, pairs = collision_bodies(key, doc, data)
    allowed = allowed_contacts(key, doc["nodes"])
    # Enclose both signed extremes of each field's sampled morph displacement.
    center = []
    radius = []
    for b in bodies:
        half = (b.upper - b.lower) * 0.5
        if b.delta is not None:
            half += abs(b.delta).max(0) * abs(weights[:, b.node]).max()
        center.append(
            origin[:, b.node]
            + np.einsum("tij,j->ti", linear[:, b.node], (b.upper + b.lower) * 0.5)
        )
        radius.append(np.einsum("tij,j->ti", abs(linear[:, b.node]), half))
    center = np.array(center)
    radius = np.array(radius)
    request = fcl.CollisionRequest(num_max_contacts=1)
    unexpected = Counter()
    intended = 0
    if pairs:
        left, right = np.array(pairs).T
        broad = (
            abs(center[left] - center[right]) <= radius[left] + radius[right] + 1e-7
        ).all(axis=2)
        for frame in range(len(frames)):
            objects = {}
            for pair_index in np.flatnonzero(broad[:, frame]):
                a, b = pairs[pair_index]
                for j in (a, b):
                    if j not in objects:
                        part = bodies[j]
                        node = part.node
                        objects[j] = part.place(
                            origin[frame, node],
                            linear[frame, node],
                            weights[frame, node],
                        )
                if fcl.collide(objects[a], objects[b], request, fcl.CollisionResult()):
                    if (a, b) in allowed:
                        intended += 1
                    else:
                        unexpected[(bodies[a].name, bodies[b].name)] += 1
    gaps = attack_gaps(
        doc["nodes"], bodies, allowed, item["events"], frames, origin, linear, weights
    )
    return {
        "id": key,
        "frames": len(frames),
        "pairs": len(pairs),
        "strike_checks": len(gaps),
        "largest_strike_gap_mm": round(1000 * max(gaps, default=0.0), 3),
        "playing_and_join_contacts": intended,
        "unexpected": [(a, b, n) for (a, b), n in unexpected.items()],
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("ids", nargs="*")
    parser.add_argument("--fps", type=int, default=30)
    args = parser.parse_args()
    catalog = json.loads((ASSETS / "catalog.json").read_text())
    if args.fps <= 0 or set(args.ids) - {r["id"] for r in catalog}:
        parser.error("Invalid FPS or instrument ID")
    failed = False
    for item in catalog:
        if args.ids and item["id"] not in args.ids:
            continue
        report = check(item, args.fps)
        print(json.dumps(report), flush=True)
        failed |= bool(report["unexpected"]) or report["largest_strike_gap_mm"] > 0.1
    raise SystemExit(int(failed))

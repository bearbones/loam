"""Check GLB surface sheets for folded triangles and non-adjacent intersections.

blender -b -t 2 -P tools/check_cabinet_geometry.py -- [instrument IDs]
The exporter batches joined fittings by material. Test each connected index
sheet independently, retaining real seams but excluding shared geometric edges.
"""

import json
import struct
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "harness/assets/cabinet"


def read_glb(path):
    blob = path.read_bytes()
    size = struct.unpack_from("<I", blob, 12)[0]
    doc = json.loads(blob[20 : 20 + size])
    offset = 28 + size

    def data(i):
        a = doc["accessors"][i]
        view = doc["bufferViews"][a["bufferView"]]
        width = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4}[a["type"]]
        dtype = {5121: "u1", 5123: "<u2", 5125: "<u4", 5126: "<f4"}[a["componentType"]]
        return np.frombuffer(
            blob,
            dtype,
            offset=offset + view.get("byteOffset", 0) + a.get("byteOffset", 0),
            count=a["count"] * width,
        ).reshape(-1, width)

    return doc, data


def sheets(face):
    # Batching preserves the contiguous index range of each manufactured sheet.
    maximum = np.maximum.accumulate(face.max(axis=1))
    minimum = np.minimum.accumulate(face.min(axis=1)[::-1])[::-1]
    return np.split(face, np.flatnonzero(maximum[:-1] < minimum[1:]) + 1)


def check(key):
    from mathutils.bvhtree import BVHTree

    doc, data = read_glb(ASSETS / (key + ".glb"))
    folded = hits = degenerate = triangles = pieces = 0
    examples = []
    for mesh in doc["meshes"]:
        for prim in mesh["primitives"]:
            xyz = data(prim["attributes"]["POSITION"])
            norm = data(prim["attributes"]["NORMAL"])
            face = data(prim["indices"]).reshape(-1, 3)
            material = doc["materials"][prim["material"]]["name"]
            for patch in sheets(face):
                start = int(patch.min())
                end = int(patch.max()) + 1
                p = xyz[start:end]
                f = patch - start
                t = p[f]
                g = np.cross(t[:, 1] - t[:, 0], t[:, 2] - t[:, 0])
                dot = (g * norm[patch].sum(axis=1)).sum(axis=1)
                area2 = np.linalg.norm(g, axis=1)
                collapsed = int(np.count_nonzero(area2 < 1e-14))
                inversions = int(np.count_nonzero(dot < -area2 * 0.04))
                tree = BVHTree.FromPolygons(p.tolist(), f.tolist(), all_triangles=True)
                pairs = tree.overlap(tree)
                nonadjacent = 0
                if pairs:
                    pairs = np.asarray(pairs)
                    a, b = pairs[pairs[:, 0] < pairs[:, 1]].T
                    _, weld = np.unique(
                        np.rint(p * 1e6).astype(np.int32), axis=0, return_inverse=True
                    )
                    fa, fb = weld[f[a]], weld[f[b]]
                    nonadjacent = int(
                        np.count_nonzero(
                            ~(fa[:, :, None] == fb[:, None, :]).any(axis=(1, 2))
                        )
                    )
                degenerate += collapsed
                hits += nonadjacent
                folded += inversions
                pieces += 1
                triangles += len(f)
                if collapsed or inversions or nonadjacent:
                    examples.append(
                        (
                            mesh["name"],
                            material,
                            start,
                            len(f),
                            inversions,
                            nonadjacent,
                            collapsed,
                            p.mean(axis=0).round(3).tolist(),
                        )
                    )
    return {
        "id": key,
        "sheets": pieces,
        "triangles": triangles,
        "folded": folded,
        "degenerate": degenerate,
        "crossings": hits,
        "locations": examples,
    }


if __name__ == "__main__":
    args = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    keys = args or [e["id"] for e in json.loads((ASSETS / "catalog.json").read_text())]
    reports = [check(key) for key in keys]
    for row in reports:
        print("SURFACE " + json.dumps(row), flush=True)
    if any(r["folded"] or r["crossings"] or r["degenerate"] for r in reports):
        sys.exit(1)

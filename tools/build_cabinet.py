"""Build the 25 portable, animated instruments in Godot's native Y-up frame."""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from cabinet import orbital, percussion, room, strings, winds
from cabinet.fittings import shop_stamp
from cabinet.mesh import Asset, X, Y, Z

from loam.cabinet import INSTRUMENTS, score

OUT = ROOT / "harness/assets/cabinet"
BUILDERS = {
    key: getattr(module, key)
    for module, keys in (
        (strings, "oud nyckelharpa koto kora dulcimer hardanger gurdy"),
        (winds, "shakuhachi siku sheng uilleann serpent"),
        (percussion, "balafon mbira tabla kulintang udu handpan armonica bandoneon"),
        (orbital, "magnetar periapsis choir cryotape pulsar"),
    )
    for key in keys.split()
}
# Eye direction is relative to the display centre. Top surfaces and front
# faces have distinct inspection angles, including the kora's bridge profile.
EYES = {
    "oud": (0.48, 0.32, 1.8),
    "nyckelharpa": (0.58, 0.31, 1.8),
    "koto": (0.58, 1.36, 1.28),
    "kora": (1.12, 0.35, 1.32),
    "dulcimer": (0.48, 0.29, 1.8),
    "shakuhachi": (0.95, 0.39, 1.65),
    "siku": (0.64, 0.45, 1.8),
    "sheng": (0.83, 0.49, 1.62),
    "uilleann": (0.60, 0.38, 1.68),
    "serpent": (0.53, 0.33, 1.72),
    "balafon": (0.70, 0.96, 1.65),
    "mbira": (0.51, 1.64, 1.22),
    "tabla": (0.62, 1.12, 1.62),
    "kulintang": (0.43, 1.04, 1.6),
    "udu": (0.69, 0.58, 1.68),
    "hardanger": (0.48, 0.31, 1.83),
    "gurdy": (0.75, 0.53, 1.83),
    "armonica": (0.79, 0.71, 1.57),
    "bandoneon": (0.91, 0.71, 1.65),
    "handpan": (0.56, 1.16, 1.61),
    "magnetar": (0.67, 0.67, 1.73),
    "periapsis": (0.46, 1.32, 1.68),
    "choir": (0.67, 0.60, 1.73),
    "cryotape": (0.68, 0.48, 1.77),
    "pulsar": (0.64, 0.50, 1.72),
}

# The repair shop stamped replacement hardware and cases. Other instruments
# carry the maker's work in their bindings, marquetry or clay slip.
STAMP_SEATS = {
    "oud": ([-0.185, 0.30, 0.003], X, Y),
    "nyckelharpa": ([0.105, 0.20, 0.003], X, Y),
    "dulcimer": ([-0.118, 0.21, 0.003], X, Y),
    "koto": ([-0.69, 0.145, 0.255], X, Y),
    "kulintang": ([0.012, 0.241, 0.213], X, Y),
    "mbira": ([0.052, 0.224, 0.239], X, -Z),
    "armonica": ([0.45, 0.114, 0.266], X, Y),
    "gurdy": ([0.054, 0.58, 0.155], X, Y),
    "magnetar": ([0.18, 0.144, 0.321], X, Y),
    "choir": ([0, 0.277, 0.240], X, -Z),
    "cryotape": ([-0.42, 0.345, 0.021], X, Y),
    "pulsar": ([0.03, 0.151, 0.221], X, -Z),
}


def build(keys):
    OUT.mkdir(parents=True, exist_ok=True)
    layouts = {}
    for key in keys:
        asset = Asset(key)
        BUILDERS[key](asset)
        if key in STAMP_SEATS:
            shop_stamp(asset.fixed, *STAMP_SEATS[key], list(INSTRUMENTS).index(key) + 1)
        events, duration = score(key)
        layouts[key] = asset.export(OUT / (key + ".glb"), events, duration)
        layouts[key]["eye"] = EYES[key]
        print(
            key,
            layouts[key]["actuators"],
            (OUT / (key + ".glb")).stat().st_size,
            flush=True,
        )
    path = OUT / "display.json"
    current = json.loads(path.read_text()) if path.exists() else {}
    current.update(layouts)
    path.write_text(json.dumps(current, sort_keys=True, indent=2) + "\n")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "instruments", nargs="*", help="IDs to rebuild (default: entire cabinet)"
    )
    keys = ap.parse_args().instruments
    if set(keys) - BUILDERS.keys():
        ap.error("Unknown cabinet instrument")
    build(keys or INSTRUMENTS)
    if not keys:
        room.build(OUT.parent / "cabinet_room.glb")

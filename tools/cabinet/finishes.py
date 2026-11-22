"""Workshop finishes in metres. Each playing surface has a non-repeating wear map.

The bounds of a board are its two in-plane extents. Turned parts also
specify an axis origin and a circumference. Wear ellipses are specified in the same coordinates as the geometry.
On turned stock their horizontal coordinate is a fraction of one revolution.
"""

from dataclasses import dataclass
from functools import cache
from io import BytesIO
from zlib import crc32

import numpy as np
from PIL import Image, ImageDraw
from scipy.ndimage import gaussian_filter

TAU = 2 * np.pi


@dataclass(frozen=True)
class Face:
    stock: str
    plane: str
    extent: tuple
    wear: tuple
    node: str = "Workshop casting"
    long_u: bool = False
    origin: tuple = (0.0, 0.0)
    # Circumference supplies physical texel size for the turned face.
    circumference: float = 1.0

    def uv(self, p):
        if self.plane == "y-turn":
            u = np.arctan2(p[:, 0] - self.origin[0], p[:, 2] - self.origin[1]) / TAU
            v = p[:, 1]
        else:
            a, b = ["xyz".index(axis) for axis in self.plane]
            u, v = p[:, a], p[:, b]
        x0, x1, y0, y1 = self.extent
        return np.column_stack(((u - x0) / (x1 - x0), (v - y0) / (y1 - y0)))

    def fits(self, p, n):
        if self.plane == "y-turn":
            return np.mean(np.abs(n[:, 1])) < 0.84
        axis = next(i for i, x in enumerate("xyz") if x not in self.plane)
        return np.mean(np.abs(n[:, axis])) > 0.44 and np.mean(n[:, axis]) > -0.22


# Contact patches follow bridge feet, finger holes, thumb paths, drum
# strike zones, the tuning hand, drive belts or the player's controls.
FACES = {
    "oud": Face(
        "spruce",
        "xy",
        (-0.40, 0.40, 0.02, 1.0),
        (
            (0.11, 0.31, 0.115, 0.072),
            (-0.065, 0.255, 0.075, 0.028),
            (0.27, 0.43, 0.073, 0.14),
        ),
    ),
    "nyckelharpa": Face(
        "maple",
        "xy",
        (-0.29, -0.07, 0.43, 1.10),
        tuple((-0.196, 0.48 + i * 0.043, 0.055, 0.016) for i in range(14)),
        "Tangent key",
    ),
    "koto": Face(
        "spruce",
        "xz",
        (-1.03, 1.03, -0.25, 0.25),
        tuple(
            (-0.60 + i * 0.085, -0.212 + i * 0.424 / 12, 0.048, 0.012)
            for i in range(13)
        )
        + ((0.77, 0, 0.15, 0.18),),
        long_u=True,
    ),
    "kora": Face(
        "skin",
        "xy",
        (-0.34, 0.34, 0.035, 0.725),
        (
            (-0.17, 0.47, 0.047, 0.14),
            (0.17, 0.47, 0.047, 0.14),
            (0, 0.39, 0.065, 0.060),
        ),
    ),
    "dulcimer": Face(
        "spruce",
        "xy",
        (-0.28, 0.28, -0.01, 1.18),
        (
            (-0.075, 0.22, 0.078, 0.060),
            (0.108, 0.30, 0.043, 0.11),
            (0.103, 0.85, 0.055, 0.17),
        ),
    ),
    "shakuhachi": Face(
        "bamboo",
        "y-turn",
        (-0.5, 0.5, 0, 1.215),
        tuple((0, h, 0.12, 0.037) for h in [0.29, 0.385, 0.514, 0.635])
        + ((0.44, 0.72, 0.15, 0.08),),
        circumference=0.29,
    ),
    "siku": Face(
        "bamboo",
        "xy",
        (-0.36, 0.36, 0.02, 1.06),
        tuple(((i - 3) * 0.101, 0.998, 0.034, 0.065) for i in range(7))
        + ((-0.19, 0.66, 0.12, 0.12),),
    ),
    "sheng": Face(
        "navy",
        "y-turn",
        (-0.5, 0.5, 0.05, 0.294),
        ((0.24, 0.184, 0.12, 0.081), (-0.17, 0.15, 0.16, 0.062)),
        circumference=1.10,
    ),
    "uilleann": Face(
        "wine",
        "xy",
        (-0.49, 0.27, 0.225, 0.716),
        ((0.096, 0.44, 0.142, 0.123), (-0.263, 0.52, 0.132, 0.091)),
        "Patched leather",
    ),
    "serpent": Face(
        "leather",
        "xy",
        (-0.41, 0.41, -0.005, 1.39),
        (
            (0.17, 1.075, 0.093, 0.085),
            (-0.209, 0.60, 0.10, 0.11),
            (0.19, 0.42, 0.13, 0.066),
        ),
    ),
    "balafon": Face(
        "rose",
        "xz",
        (-0.85, 0.85, -0.36, 0.36),
        tuple(((i - 3.5) * 0.207, -0.060, 0.052, 0.082) for i in range(8)),
        "Tied bar",
    ),
    "mbira": Face(
        "iron",
        "xz",
        (-0.27, 0.27, -0.24, 0.22),
        tuple(
            ((i - 7.5) * 0.033, 0.032 + 0.14 * (1 - abs(i - 7.3) / 9), 0.014, 0.045)
            for i in range(16)
        ),
        "Forged tongue",
    ),
    "tabla": Face(
        "skin",
        "xz",
        (-0.51, 0.48, -0.26, 0.26),
        (
            (-0.22, 0.035, 0.087, 0.075),
            (-0.35, -0.031, 0.064, 0.070),
            (0.265, 0.018, 0.050, 0.064),
            (0.335, 0.055, 0.036, 0.044),
        ),
    ),
    "kulintang": Face(
        "bronze",
        "xz",
        (-1.18, 1.18, -0.155, 0.155),
        tuple(((i - 3.5) * 0.29, 0, 0.045, 0.041) for i in range(8)),
        "Bossed gong",
    ),
    "udu": Face(
        "clay",
        "y-turn",
        (-0.5, 0.5, 0.034, 0.8),
        (
            (0, 0.39, 0.078, 0.084),
            (0.05, 0.755, 0.18, 0.059),
            (0.18, 0.27, 0.11, 0.095),
        ),
        circumference=1.65,
    ),
    "hardanger": Face(
        "spruce",
        "xy",
        (-0.24, 0.24, 0.01, 0.8),
        (
            (0.131, 0.293, 0.062, 0.077),
            (-0.106, 0.215, 0.086, 0.087),
            (0.018, 0.392, 0.12, 0.041),
        ),
    ),
    "gurdy": Face(
        "rose",
        "xy",
        (-0.32, 0.32, 0.01, 0.91),
        (
            (0.116, 0.274, 0.081, 0.093),
            (-0.11, 0.54, 0.059, 0.143),
            (0.17, 0.376, 0.081, 0.071),
        ),
    ),
    "armonica": Face(
        "walnut",
        "xz",
        (-0.82, 0.82, -0.28, 0.28),
        (
            (-0.52, 0.18, 0.14, 0.064),
            (0.01, 0.18, 0.39, 0.054),
            (0.56, 0.14, 0.10, 0.11),
        ),
        long_u=True,
    ),
    "bandoneon": Face(
        "wine",
        "xy",
        (-0.357, 0.357, 0.035, 0.545),
        (
            (-0.235, 0.31, 0.067, 0.110),
            (0.23, 0.377, 0.11, 0.082),
            (-0.11, 0.23, 0.063, 0.046),
        ),
        "Gusseted leather",
    ),
    "handpan": Face(
        "tempered",
        "xz",
        (-0.40, 0.40, -0.40, 0.40),
        tuple(
            (0.248 * np.cos(i * TAU / 7), 0.248 * np.sin(i * TAU / 7), 0.070, 0.062)
            for i in range(7)
        )
        + ((0, 0, 0.082, 0.072),),
        node="",
    ),
    "magnetar": Face(
        "teal",
        "xz",
        (-0.985, 0.985, -0.325, 0.325),
        (
            (-0.65, 0.207, 0.093, 0.050),
            (0.62, 0.215, 0.091, 0.049),
            (0, -0.016, 0.075, 0.06),
        ),
        long_u=True,
    ),
    "periapsis": Face(
        "navy",
        "xz",
        (-0.90, 0.90, -0.40, 0.315),
        tuple(
            (0.86 * np.sin(t), (0.86 * np.cos(t) - 0.72), 0.083, 0.037)
            for t in np.linspace(-0.87, 0.87, 14)
        ),
        long_u=True,
    ),
    "choir": Face(
        "wine",
        "xz",
        (-0.62, 0.62, -0.33, 0.33),
        tuple((x, 0.187, 0.057, 0.039) for x in np.linspace(-0.44, 0.44, 5)),
        long_u=True,
    ),
    "cryotape": Face(
        "teal",
        "xy",
        (-0.63, 0.35, 0.17, 0.655),
        (
            (-0.395, 0.467, 0.147, 0.14),
            (0.105, 0.467, 0.145, 0.14),
            (-0.18, 0.276, 0.166, 0.029),
        ),
        long_u=True,
    ),
    "pulsar": Face(
        "navy",
        "xz",
        (-0.413, 0.413, -0.413, 0.413),
        tuple(
            (np.sin(a) * 0.316, np.cos(a) * 0.316, 0.043, 0.040)
            for a in np.linspace(-0.94, 0.94, 8)
        ),
    ),
}


def paint_face(key, name, node):
    face = FACES.get(key)
    return face if face and name == face.stock and node.startswith(face.node) else None


def _resolution(length, pitch):
    return int(2 ** np.clip(np.ceil(np.log2(length / pitch)), 7, 11))


def _image(array, kind):
    buf = BytesIO()
    im = Image.fromarray(np.uint8(np.clip(array, 0, 1) * 255 + 0.5))
    if kind == 0:
        im.save(buf, "JPEG", quality=94, subsampling=0)
    else:
        im.save(buf, "PNG", compress_level=5)
    return buf.getvalue()


@cache
def paint(key, name, hexcolor, metal, base_rough, stock, featured):
    face = FACES[key] if featured else None
    seed = crc32((name + ("/" + key if face else "")).encode())
    rng = np.random.default_rng(seed)
    if face:
        x0, x1, y0, y1 = face.extent
        width = (x1 - x0) * (face.circumference if face.plane == "y-turn" else 1)
        height = y1 - y0
        nx, ny = _resolution(width, 0.00135), _resolution(height, 0.00135)
    else:
        x0, x1, y0, y1 = 0, 0.28, 0, 0.28
        width = height = 0.28
        nx = ny = 512
    px, py = width / nx, height / ny
    v, u = np.mgrid[:ny, :nx].astype(np.float32)
    u = (u + 0.5) / nx
    v = (v + 0.5) / ny
    x = u * width
    y = v * height

    def noise(sx, sy=None):
        sy = sx if sy is None else sy
        raw = rng.standard_normal((ny, nx), dtype=np.float32)
        field = gaussian_filter(
            raw, (max(0.35, sy / py), max(0.35, sx / px)), mode="wrap"
        )
        return (field - field.mean()) / max(0.0001, field.std())

    grain = noise(0.0008)
    bloom = noise(0.013)
    broad = noise(0.031)
    wear = np.zeros_like(x)
    if face:
        for a, b, rx, ry in face.wear:
            du = u * (x1 - x0) + x0 - a
            dv = v * (y1 - y0) + y0 - b
            if face.plane == "y-turn":
                du = (du + 0.5) % 1 - 0.5
            wear = np.maximum(wear, np.exp(-1.7 * ((du / rx) ** 2 + (dv / ry) ** 2)))
        wear = np.clip(wear * (0.95 + 0.12 * bloom) + 0.045 * broad, 0, 1)
    rgb = np.array([int(hexcolor[i : i + 2], 16) / 255 for i in [0, 2, 4]])
    metallic = np.full_like(x, metal)
    rough = np.full_like(x, base_rough)
    tone = np.ones_like(x)
    tint = np.zeros((ny, nx, 3), np.float32)
    grain_u = face is not None and face.long_u
    across = y if grain_u else x
    along = x if grain_u else y
    long = height if grain_u else width
    frequency = (
        max(
            2,
            round(
                long
                / (
                    {
                        "spruce": 0.0062,
                        "maple": 0.011,
                        "rose": 0.014,
                        "walnut": 0.016,
                        "ebony": 0.008,
                        "bamboo": 0.005,
                    }.get(name, 0.011)
                )
            ),
        )
        / long
    )
    if stock in ("timber", "cane"):
        wander = 0.0019 * broad + 0.0014 * np.sin(
            TAU * along / (width if grain_u else height)
        )
        phase = (across + wander) * frequency
        if face and name not in ("spruce", "bamboo", "ebony"):
            # Grain bends around a pin knot in the uncontacted part of the board.
            dx = (u - 0.24) * width
            dy = (v - 0.71) * height
            phase += 0.9 * np.exp(-((dx / 0.042) ** 2 + (dy / 0.087) ** 2))
        late = (0.5 + 0.5 * np.cos(TAU * phase)) ** 5
        fibres = noise(0.014, 0.0005) if grain_u else noise(0.0005, 0.014)
        pore = np.maximum(0, fibres - 0.65)
        strength = {
            "spruce": 0.092,
            "rose": 0.23,
            "walnut": 0.19,
            "maple": 0.11,
            "bamboo": 0.12,
        }.get(name, 0.14)
        tone = 0.99 - strength * late + 0.057 * fibres - 0.055 * pore + 0.033 * bloom
        tint[:, :, 0] += 0.011 * broad
        tint[:, :, 2] -= 0.007 * bloom
        if name == "maple":
            curl = np.sin(TAU * along / 0.027 + 0.8 * broad)
            tone += 0.052 * curl
        relief = 0.042 * late - 0.065 * pore + 0.015 * grain
        rough += 0.065 * late + 0.046 * pore - 0.19 * wear
        # Thin varnish shows pale timber along rubbed paths, while oil darkens
        # unvarnished pale stock. Bow dust settles above the fiddle bridge.
        tone += (0.15 if name in ("walnut", "rose", "ebony") else -0.08) * wear
        if key == "hardanger":
            dust = np.exp(
                -(((x + x0) / 0.125) ** 2 + ((y + y0 - 0.393) / 0.032) ** 2)
            ) * np.clip(0.24 + 0.18 * bloom + 0.20 * grain, 0, 0.8)
            tint += dust[:, :, None] * np.array([0.11, 0.102, 0.078])
            rough += 0.12 * dust
    elif stock in ("metal", "enamel", "steel"):
        brush = noise(0.009, 0.00045)
        hammer = np.maximum(0, noise(0.0028) - 0.40)
        oxide = np.clip((broad * 0.33 + bloom * 0.22 - 0.15) * (1 - wear), 0, 1)
        if stock == "enamel":
            chip = np.clip((bloom + 0.50 * grain - 2.1) * 1.8, 0, 1)
            metallic = np.maximum(chip * 0.84, 0.06)
            tone = 0.95 + 0.052 * broad + 0.075 * chip
            tint += chip[:, :, None] * np.array([0.15, 0.05, -0.01])
            relief = -0.11 * chip + 0.014 * grain + 0.013 * bloom
            rough += 0.19 * chip + 0.055 * bloom - 0.13 * wear
        else:
            metallic = np.clip(0.93 - 0.67 * oxide, 0, 1)
            tone = 0.96 + 0.034 * brush - 0.20 * oxide + 0.10 * wear
            if name in ("bronze", "copper", "brass"):
                tint += oxide[:, :, None] * np.array([-0.075, 0.052, 0.038])
            if stock == "steel":
                tint += bloom[:, :, None] * np.array([0.008, 0.002, 0.012])
            relief = -hammer * (0.10 if stock == "steel" else 0.044) + 0.013 * brush
            if key == "kulintang":
                centre = np.clip(np.rint((x + x0) / 0.29 - 0.5), -4, 3) * 0.29 + 0.145
                radius = np.hypot(x + x0 - centre, y + y0)
                tooling = np.sin(TAU * radius / 0.0046 + 0.32 * bloom)
                relief += 0.019 * tooling
                rough += 0.024 * tooling
            if key == "handpan":
                # Oxide colours survive between hammered fields. Burnished
                # crowns show the underlying steel with fewer brush marks.
                temper = (1 - wear) * np.sin(2.1 * broad + 0.7 * bloom)
                tint += temper[:, :, None] * np.array([0.024, 0.004, -0.015])
                tone += 0.07 * wear
            rough += 0.18 * oxide + 0.022 * brush - 0.12 * wear
    elif stock in ("skin", "leather", "linen", "baize"):
        ridge = noise(0.0017)
        pits = np.clip(1.0 - abs(ridge + 0.36 * grain) * 2.5, 0, 1)
        # Small creases surround flatter grain islands in hide. A membrane
        # has finer fibres and darkens where the heel of the hand rests.
        if stock == "leather":
            relief = -0.075 * pits + 0.022 * grain + 0.019 * bloom
            tone = 0.94 - 0.12 * pits + 0.055 * bloom - 0.08 * wear
        elif stock == "skin":
            relief = 0.024 * grain + 0.016 * ridge
            tone = 0.94 + 0.052 * bloom + 0.031 * broad - 0.165 * wear
        else:
            weave = np.cos(TAU * u * round(width / 0.003)) * np.cos(
                TAU * v * round(height / 0.0034)
            )
            relief = 0.054 * weave + 0.018 * grain
            tone = 0.96 + 0.06 * weave + 0.025 * bloom
        rough += 0.055 * grain - 0.19 * wear
    elif stock == "gourd":
        # Dried rind has coloured lenticels and shallow pores under a waxy
        # skin. Its mottling follows growth, without pottery wheel marks.
        freckles = np.clip((noise(0.0011) + 0.4 * bloom - 1.40) * 0.85, 0, 1)
        rind = noise(0.0027, 0.009)
        tone = 0.97 + 0.067 * broad + 0.033 * rind - 0.20 * freckles
        tint[:, :, 0] += 0.012 * bloom
        relief = 0.020 * rind - 0.047 * freckles + 0.011 * grain
        rough += 0.047 * bloom + 0.067 * freckles
    elif stock == "glass" or stock == "lamp":
        if stock == "glass":
            metallic.fill(0.0)
        cords = np.sin(TAU * (u * 5 + 0.055 * broad + 0.12 * np.sin(TAU * v)))
        relief = 0.011 * cords + 0.0019 * grain
        tone = 0.985 + 0.012 * cords
        rough = 0.105 + 0.018 * bloom + 0.009 * grain
    else:
        wheel = np.sin(TAU * (v * round(height / 0.005) + 0.11 * bloom))
        relief = 0.038 * wheel + 0.026 * grain + 0.021 * bloom
        tone = 0.96 + 0.065 * bloom + 0.035 * wheel - 0.06 * wear
        rough += 0.09 * bloom - 0.19 * wear
    # Directional scratches expose the layer below the finish and interrupt
    # its highlights. Fade in working areas according to their actual location.
    if stock not in ("glass", "lamp", "baize", "linen", "panel", "skin"):
        scratches = Image.new("L", (nx, ny))
        draw = ImageDraw.Draw(scratches)
        for _ in range(round(width * height * 1450)):
            xstart = rng.uniform(0, nx)
            ystart = rng.uniform(0, ny)
            length = rng.uniform(0.002, 0.022)
            angle = rng.normal(0.4, 0.94)
            dx = length * np.cos(angle) / px
            dy = length * np.sin(angle) / py
            # Wrap marks at the edge of a repeated tile.
            for ox in (
                [0, -nx] if xstart + dx >= nx else [0, nx] if xstart + dx < 0 else [0]
            ):
                for oy in (
                    [0, -ny]
                    if ystart + dy >= ny
                    else [0, ny]
                    if ystart + dy < 0
                    else [0]
                ):
                    draw.line(
                        (xstart + ox, ystart + oy, xstart + dx + ox, ystart + dy + oy),
                        fill=int(rng.uniform(60, 200)),
                        width=1,
                    )
        scratch = gaussian_filter(
            np.asarray(scratches, dtype=np.float32) / 255, 0.48, mode="wrap"
        ) * (0.47 + wear * 0.84)
        relief -= scratch * 0.11
        tone += scratch * 0.22
        rough += scratch * 0.19
    relief *= 1 - 0.42 * wear
    # Central differences of the same height field, scaled by real texel size.
    du = (np.roll(relief, -1, 1) - np.roll(relief, 1, 1)) * (-0.0005 / px)
    dv = (np.roll(relief, -1, 0) - np.roll(relief, 1, 0)) * (-0.0005 / py)
    normal = np.dstack([du, dv, np.ones_like(du)])
    normal = normal / np.linalg.norm(normal, axis=2)[:, :, None] * 0.5 + 0.5
    color = rgb * tone[:, :, None] + tint
    cavity = np.clip(1 + np.minimum(relief, 0) * 0.52, 0.76, 1)
    orm = np.dstack((cavity, np.clip(rough, 0.08, 0.96), metallic))
    return tuple(_image(a, i) for i, a in enumerate((color, normal, orm)))

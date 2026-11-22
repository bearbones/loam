"""Air columns, reeds, windchests and the chamber's pedal-operated playing valves."""

import numpy as np
from scipy.interpolate import CubicSpline, PchipInterpolator
from scipy.spatial import Delaunay

from .fittings import binding, cable, constellation
from .mesh import TAU, O, V, X, Y, Z, axes, unit


def pierced(m, c, profile, holes, material, wall=0.011, notch=0.0):
    """Turn a hollow vessel and pierce its walls in the unwrapped surface.
    Hole entries give angle, height and radius. Hole walls join the two skins.
    """
    c = V(c)
    levels, radii = V(profile).T
    curve = PchipInterpolator(levels, radii)
    aa, hh = np.meshgrid(
        np.linspace(-np.pi / 2, 3 * np.pi / 2, 65),
        np.unique(np.round(np.r_[levels, np.linspace(levels[0], levels[-1], 85)], 9)),
    )
    points = np.c_[aa.ravel(), hh.ravel()]
    rims = []

    def inside(p, angle, h, r):
        return ((p[:, 0] - angle) * curve(h)) ** 2 + (p[:, 1] - h) ** 2 < r * r

    for angle, h, r in holes:
        points = points[~inside(points, angle, h, r * 1.06)]
        t = np.linspace(0, TAU, 33)
        rims.append(np.c_[angle + r * np.cos(t) / curve(h), h + r * np.sin(t)])
    points = np.vstack([points] + [v[:-1] for v in rims])
    tri = Delaunay(points).simplices
    for angle, h, r in holes:
        tri = tri[~inside(points[tri].mean(axis=1), angle, h, r * 0.995)]

    def coords(p, inset):
        ang, h = p.T
        r = np.maximum(0.004, curve(h) - inset)
        yy = h - notch * np.exp(-((ang / 0.26) ** 2)) * np.clip(
            (h - levels[-1] + 0.055) / 0.055, 0, 1
        )
        return c + np.c_[r * np.sin(ang), yy, r * np.cos(ang)]

    for inset, mat, reverse in [(0, material, False), (wall, "ebony", True)]:
        ang, h = points.T
        norm = np.c_[np.sin(ang), -curve.derivative()(h), np.cos(ang)]
        norm /= np.linalg.norm(norm, axis=1)[:, None]
        m.parts[mat].append(
            (
                coords(points, inset),
                -norm if reverse else norm,
                points * [float(np.mean(radii)) / 0.30, 1 / 0.30],
                tri[:, ::-1] if reverse else tri,
            )
        )
    for rim in rims:
        m.surface([coords(rim, wall), coords(rim, 0)], material)
    for h in [levels[0], levels[-1]]:
        ring = np.c_[np.linspace(-np.pi / 2, 3 * np.pi / 2, 65), np.full(65, h)]
        m.surface([coords(ring, 0), coords(ring, wall)], material)


def tube_pipe(m, c, h, r, mat="bamboo", sealed=True):
    m.turn(
        c,
        Y,
        [
            (0, r * 0.89),
            (0.04 * h, r),
            (h - 0.004, r),
            (h, r * 0.93),
            (h, r * 0.68),
            (0.008, r * 0.66),
        ],
        mat,
        24,
        False,
    )
    if sealed:
        m.turn(V(c) + 0.006 * Y, Y, [(0, r * 0.89), (0.003, r * 0.68)], mat, 24)


def pallet(asset, centre, r, normal, lanes):
    c = V(centre)
    n = unit(V(normal))
    u, v = axes(n)
    pivot = c - u * r * 1.9 + n * 0.018
    m = asset.fixed
    m.rod(pivot - n * 0.042, pivot, 0.008, "brass")
    m.turn(pivot, v, [(-r * 0.45, 0.012), (r * 0.45, 0.012)], "bronze", 14)
    p = asset.part(f"Pallet {len(asset.nodes) + 1}", pivot)
    reach = c - pivot + n * 0.006
    p.rod(O, reach, 0.0055, "bronze")
    p.turn(
        reach,
        n,
        [(-0.006, r * 1.05), (0.001, r * 1.12), (0.006, r * 0.88)],
        "leather",
        21,
    )
    p.ball(reach + n * 0.006, [0.006, 0.006, 0.006], "brass", 10)
    asset.drive(p, "key", v, 0.40, lanes, rest=-0.40)


def shakuhachi(asset):
    m = asset.fixed
    profile = [
        (0, 0.084),
        (0.032, 0.088),
        (0.078, 0.070),
        (0.16, 0.055),
        (0.32, 0.049),
        (0.78, 0.044),
        (1.13, 0.043),
        (1.21, 0.049),
    ]
    heights = [0.29, 0.385, 0.514, 0.635]
    holes = [(0, h, 0.016) for h in heights] + [(np.pi - 0.38, 0.72, 0.017)]
    pierced(m, O, profile, holes, "bamboo", 0.014, 0.026)
    for h, r in [
        (0.087, 0.066),
        (0.175, 0.054),
        (0.46, 0.048),
        (0.81, 0.044),
        (1.034, 0.045),
    ]:
        m.turn(
            O,
            Y,
            [
                (h - 0.014, r),
                (h - 0.006, r + 0.005),
                (h + 0.005, r + 0.006),
                (h + 0.014, r),
            ],
            "bamboo",
            caps=False,
        )
    for i in range(12):
        a = TAU * i / 12
        m.ball(
            [0.077 * np.sin(a), 0.031 + 0.016 * (i % 2), 0.077 * np.cos(a)],
            [0.010, 0.018, 0.010],
            "walnut",
            14,
        )
    for h in [0.19, 0.229, 0.91]:
        binding(m, [0, h, 0], Y, 0.053 if h < 0.3 else 0.047, 0.018, "black")
    cable(m, [[0.047, 0.9, 0], [0.091, 0.86, 0], [0.113, 0.74, 0.017]], "red", 0.004)
    m.ring([0.113, 0.728, 0.017], Z, 0.020, 0.004, "brass")
    a = np.linspace(1.05, TAU - 1.05, 23)
    m.tube(
        [[0.118 + 0.013 * np.cos(t), 0.728 + 0.014 * np.sin(t), 0.018] for t in a],
        0.0028,
        "ivory",
        8,
    )
    for i, h in enumerate(heights):
        pallet(
            asset,
            [0, h, float(PchipInterpolator(*V(profile).T)(h))],
            0.017,
            Z,
            [i, (i + 2) % 6],
        )
    back = V([np.sin(np.pi - 0.38), 0, np.cos(np.pi - 0.38)])
    pallet(
        asset,
        Y * 0.72 + back * float(PchipInterpolator(*V(profile).T)(0.72)),
        0.017,
        back,
        [4, 5],
    )


def siku(asset):
    m = asset.fixed
    for bank, count in enumerate([7, 6]):
        z = (bank - 0.5) * 0.097
        top = 1.05 - bank * 0.081
        back = z - 0.055
        m.rod(
            [-0.348, top - 0.031, back],
            [0.34, top - 0.031, back],
            0.010,
            "bronze",
            n=16,
        )
        for mount in [-0.26, 0.23]:
            m.rod([mount, 0.79, -0.105], [mount, top - 0.031, back], 0.007, "brass")
        for i in range(count):
            x = (i - 3) * 0.101 + bank * 0.051
            length = 1.00 - i * 0.092 - bank * 0.040
            top = 1.05 - bank * 0.081
            tube_pipe(
                m,
                [x, top - length, z],
                length,
                0.0445,
                "maple" if (bank, i) == (0, 5) else "bamboo",
            )
            binding(m, [x, top - length + 0.035, z], Y, 0.045, 0.012, "leather")
            if bank == 0 or i % 2 == 0:
                # Baffle above the mouth admits wind from the common manifold.
                m.rod(
                    [x - 0.042, top - 0.031, back],
                    [x - 0.042, top + 0.012, z],
                    0.006,
                    "brass",
                )
                pallet(asset, [x, top, z], 0.022, Y, [((2 * i) + bank) % 8])
    for h in [0.69, 0.79]:
        for z in [-0.105, 0.102]:
            m.rod([-0.379, h, z], [0.377, h, z], 0.017, "maple", n=17)
        for i in range(14):
            x = -0.35 + i * 0.052
            m.tube(
                [
                    [x, h - 0.026, 0.102],
                    [x + 0.019, h + 0.024, 0.108],
                    [x + 0.019, h + 0.024, -0.110],
                    [x + 0.036, h - 0.024, -0.110],
                ],
                0.005,
                "red" if i % 3 else "cord",
                8,
            )
    for i in range(3):
        cable(
            m,
            [
                [-0.35, 0.75, -0.10],
                [-0.423, 0.64, 0.01],
                [-0.38 + i * 0.018, 0.45, 0.05],
            ],
            "red",
            0.007,
        )
        m.ball([-0.38 + i * 0.018, 0.439, 0.05], 0.014, "brass", 14)
    for i in range(5):
        x = -0.26 + i * 0.127
        m.tube(
            [
                [x - 0.029, 0.792, 0.119],
                [x, 0.807, 0.121],
                [x + 0.029, 0.792, 0.119],
                [x, 0.780, 0.121],
                [x - 0.029, 0.792, 0.119],
            ],
            0.003,
            "cord",
            7,
        )


def sheng(asset):
    m = asset.fixed
    c = np.array([0, 0.05, 0])
    m.turn(
        c,
        Y,
        [
            (0, 0.063),
            (0.035, 0.125),
            (0.085, 0.174),
            (0.175, 0.187),
            (0.222, 0.162),
            (0.24, 0.145),
        ],
        "navy",
        56,
    )
    for h, r in [(0.10, 0.174), (0.205, 0.18), (0.235, 0.158)]:
        m.ring(c + h * Y, Y, r, 0.005, "brass")
    for i in range(17):
        a = TAU * i / 17
        rr = 0.115
        x, z = rr * np.sin(a), rr * np.cos(a)
        h = 0.46 + 0.58 * (0.5 + 0.5 * np.cos(a + 1.13)) + 0.034 * (i % 3)
        tube_pipe(m, [x, 0.285, z], h, 0.021, "bamboo", sealed=False)
        binding(m, [x, 0.32, z], Y, 0.023, 0.046, "bronze")
        binding(m, [x, 0.285 + h - 0.032, z], Y, 0.0215, 0.010, "leather")
        if i % 2 == 0:
            n = unit(V([x, 0, z]))
            pallet(asset, V([x, 0.395, z]) + n * 0.021, 0.010, n, [i // 2 % 8])
    cable(
        m,
        [[0.14, 0.20, 0], [0.26, 0.22, 0], [0.35, 0.25, 0.01], [0.44, 0.30, 0.02]],
        "brass",
        0.023,
    )
    binding(m, [0.437, 0.30, 0.02], unit(V([1, 0.5, 0])), 0.024, 0.045, "ebony")
    for i in range(9):
        a = TAU * i / 9
        m.ball([0.174 * np.sin(a), 0.191, 0.174 * np.cos(a)], 0.007, "ivory", 10)
    # An open pennant turns the tallest pipes into a tiny lookout tower.
    a = 15 * TAU / 17
    x = 0.115 * np.sin(a)
    z = 0.115 * np.cos(a)
    h = 0.285 + 0.46 + 0.58 * (0.5 + 0.5 * np.cos(a + 1.13))
    binding(m, [x, h - 0.033, z], Y, 0.023, 0.022, "copper")
    m.rod([x + 0.019, h - 0.036, z], [x + 0.019, h + 0.074, z], 0.003, "brass", n=8)
    m.tube(
        [
            [x + 0.019, h + 0.072, z],
            [x + 0.077, h + 0.051, z],
            [x + 0.019, h + 0.037, z],
        ],
        0.003,
        "brass",
        8,
    )


def uilleann(asset):
    m = asset.fixed
    bag = asset.part("Patched leather bag", [-0.11, 0.47, 0])
    bag.ball(O, [0.37, 0.235, 0.155], "wine", 48)
    theta = np.linspace(0, TAU, 81)
    bag.tube(
        np.c_[0.369 * np.cos(theta), 0.234 * np.sin(theta), theta * 0], 0.008, "cord"
    )
    bag.ball([-0.09, 0.01, 0.143], [0.093, 0.067, 0.013], "leather")
    for i in range(14):
        a = TAU * i / 14
        bag.rod(
            [-0.09 + 0.093 * np.cos(a), 0.065 * np.sin(a), 0.154],
            [-0.09 + 0.084 * np.cos(a + 0.07), 0.057 * np.sin(a + 0.07), 0.155],
            0.003,
            "cord",
            n=7,
        )
    constellation(bag, [-0.09, 0.01, 0.159], X, Y, 0.047, "cord", 8)
    asset.drive(bag, "bellows", Z, 0.045, rate=2.4)
    stocks = [
        (0.21, 0.25, 0.10, 0.75),
        (0.07, 0.44, -0.06, 0.91),
        (-0.08, 0.49, -0.09, 1.04),
        (-0.22, 0.50, -0.07, 1.16),
    ]
    for i, (x, y, z, h) in enumerate(stocks):
        m.turn(
            [x, y, z],
            Y,
            [
                (0, 0.043),
                (0.065, 0.047),
                (0.083, 0.029),
                (h * 0.62, 0.024),
                (h * 0.65, 0.037),
                (h * 0.72, 0.035),
                (h * 0.74, 0.024),
                (h - 0.09, 0.027),
                (h - 0.045, 0.046),
                (h, 0.041),
                (h, 0.027),
                (h - 0.031, 0.023),
            ],
            "ebony",
            30,
            False,
        )
        for f in [0.07, 0.62, 0.73, 0.96]:
            binding(
                m, [x, y + f * h, z], Y, 0.040 if f > 0.95 else 0.032, 0.017, "ivory"
            )
    for i in range(7):
        h = 0.51 + i * 0.053
        m.turn([0.21, h, 0.127], Z, [(0, 0.012), (0.003, 0.012)], "black", 16)
        pallet(asset, [0.21, h, 0.131], 0.011, Z, [i, (i + 2) % 8])
    m.case([0.294, 0.344, 0.012], [0.244, 0.081, 0.10], "ebony", 0.019)
    m.rod([0.168, 0.354, 0.050], [0.293, 0.344, 0.012], 0.034, "bronze", n=24)
    for i in range(3):
        x = 0.29 + 0.045 * i
        m.rod([x, 0.32, 0.012], [x, 0.78 - i * 0.08, 0.012], 0.019, "rose")
        binding(m, [x, 0.36, 0.012], Y, 0.022, 0.036)
    for x in [-0.52, -0.65]:
        m.case([x, 0.60, 0], [0.025, 0.31, 0.19], "maple")
    for i in range(7):
        m.case(
            [-0.52 - i * 0.019, 0.60, 0],
            [0.022, 0.25 + 0.028 * (i % 2), 0.16 + 0.02 * (i % 2)],
            "leather",
        )
    cable(
        m, [[-0.52, 0.52, 0], [-0.43, 0.44, 0.03], [-0.37, 0.50, 0.03]], "black", 0.022
    )


def serpent(asset):
    m = asset.fixed
    path = V(
        [
            [-0.24, 1.33, 0],
            [-0.15, 1.20, 0],
            [0.16, 1.14, 0],
            [0.26, 0.98, 0],
            [0.12, 0.85, 0],
            [-0.20, 0.80, 0],
            [-0.29, 0.64, 0.014],
            [-0.15, 0.50, 0.035],
            [0.22, 0.43, 0.072],
            [0.31, 0.25, 0.105],
            [0.16, 0.15, 0.14],
            [-0.10, 0.18, 0.19],
            [-0.21, 0.30, 0.245],
            [-0.19, 0.44, 0.335],
        ]
    )
    spline = CubicSpline(np.linspace(0, 1, len(path)), path)
    t = np.linspace(0, 1, 129)
    pts = spline(t)
    dirs = spline(t, 1)
    angles = np.linspace(0, TAU, 41)
    u = Z.copy()
    rows = []
    for tt, p, d in zip(t, pts, dirs):
        d = unit(d)
        u = unit(u - d * np.dot(d, u))
        v = np.cross(d, u)
        rr = 0.023 + 0.052 * tt + 0.103 * tt**16
        rows.append(
            p + rr * (u * np.cos(angles)[:, None] + v * np.sin(angles)[:, None])
        )
    m.surface(rows, "leather")
    # The stitched seam follows the bore, including its reversing bends.
    m.tube([row[4] for row in rows], 0.0024, "cord", 7)
    m.surface(
        [
            rows[-1],
            pts[-1] + (rows[-1] - pts[-1]) * 0.93,
            pts[-5] + (rows[-5] - pts[-5]) * 0.91,
        ],
        "copper",
    )
    m.ring(pts[-1], unit(dirs[-1]), 0.178, 0.008, "brass")
    binding(m, pts[0], unit(dirs[0]), 0.028, 0.045, "ivory")
    for tt in [0.10, 0.17, 0.36, 0.41, 0.65, 0.72, 0.90]:
        binding(
            m,
            spline(tt),
            unit(spline(tt, 1)),
            0.028 + 0.052 * tt + 0.103 * tt**16,
            0.026,
            "copper",
        )
    for i, tt in enumerate([0.205, 0.25, 0.30, 0.48, 0.53, 0.58]):
        pos = spline(tt) + Z * (0.023 + 0.052 * tt)
        m.turn(pos, Z, [(-0.004, 0.017), (0.002, 0.016)], "ebony", 16)
        pallet(asset, pos, 0.016, Z, [i, (i + 2) % 7])
    for tt in [0.12, 0.38, 0.69]:
        p = spline(tt) + Z * (0.026 + 0.052 * tt)
        m.screw(p, Z, 0.012)

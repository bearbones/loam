"""Five original shipboard instruments. Each has its own control surface and drive."""

import numpy as np

from .fittings import binding, cable, constellation, feet, lamp
from .mesh import TAU, O, V, X, Y, Z


def dial(m, c, r, mat="ivory"):
    c = V(c)
    m.turn(c, Z, [(0, r), (0.012, r), (0.015, r * 0.91)], mat, 46)
    m.ring(c + Z * 0.014, Z, r * 0.94, 0.004, "brass")
    for ang in np.linspace(-1.9, 1.9, 13):
        d = X * np.sin(ang) + Y * np.cos(ang)
        m.rod(
            c + d * r * 0.72 + Z * 0.018,
            c + d * r * 0.87 + Z * 0.018,
            0.002,
            "iron",
            n=6,
        )


def gauge(asset, c, r, lanes=None):
    c = V(c)
    dial(asset.fixed, c, r)
    p = asset.part("Galvanometer " + str(len(asset.nodes) + 1), c + Z * 0.022)
    p.rod(O, Y * r * 0.72, 0.003, "wine", 0.0015, n=7)
    p.ball(O, 0.006, "iron", 12)
    asset.drive(p, "meter", Z, 1.95, lanes, rest=-0.98)


def knob(m, c, r=0.032):
    c = V(c)
    m.turn(
        c, Y, [(0, r * 0.82), (0.007, r), (0.037, r), (0.044, r * 0.85)], "ebony", 18
    )
    m.rod(c + [0, 0.045, 0], c + [r * 0.68, 0.045, 0], 0.0022, "ivory", n=7)


def console(m, c, size, mat):
    c = V(c)
    w, h, d = size
    m.case(c, size, mat, 0.066)
    m.case(c + [0, h * 0.45, 0], [w * 1.015, 0.020, d * 1.018], "brass", 0.038)
    m.case(c + [0, h * 0.53, 0], [w * 0.985, 0.028, d * 0.965], mat, 0.038)
    for x in [-1, 1]:
        for z in [-1, 1]:
            m.screw(
                c + [x * (w * 0.5 - 0.049), h * 0.53 + 0.016, z * (d * 0.5 - 0.046)],
                Y,
                0.013,
            )
    feet(m, [-w * 0.38, w * 0.38], [-d * 0.35, d * 0.35], c[1] - h / 2)


def coil(m, c, axis, r, length, n, mat="copper"):
    from .mesh import axes, unit

    c = V(c)
    axis = unit(V(axis))
    u, v = axes(axis)
    t = np.linspace(0, TAU * n, n * 15 + 1)
    m.tube(
        c
        + length * (t[:, None] / (TAU * n)) * axis
        + r * (np.cos(t)[:, None] * u + np.sin(t)[:, None] * v),
        0.0045,
        mat,
        7,
    )


def magnetar(asset):
    m = asset.fixed
    console(m, [0, 0.14, 0], [1.30, 0.20, 0.64], "teal")
    for i, (x, r, h) in enumerate(
        [(-0.42, 0.235, 0.61), (0, 0.303, 0.68), (0.42, 0.209, 0.59)]
    ):
        c = V([x, h, 0])
        m.turn(
            [x, 0.25, 0],
            Y,
            [(0, 0.072), (0.016, 0.081), (0.040, 0.049), (0.117, 0.031)],
            "bronze",
            28,
        )
        m.ring(c, Z, r, 0.030, "bronze", 64)
        # Wind copper around the torus itself, exposing individual turns.
        a = np.linspace(0, TAU, 611)
        d = np.c_[np.cos(a), np.sin(a), 0 * a]
        m.tube(
            c
            + (r + 0.033 * np.cos(49 * a))[:, None] * d
            + 0.033 * np.sin(49 * a)[:, None] * Z,
            0.005,
            "copper",
            7,
        )
        p = asset.part("Field armature " + str(i), c)
        p.ring(O, Y, r * 0.66, 0.011, "tin")
        p.ring(O, X, r * 0.47, 0.007, "brass")
        p.ball(O, r * 0.22, "ice", 24)
        p.rod([0, -r, 0], [0, r, 0], 0.009, "iron")
        asset.drive(p, "spin", Y, 1, rate=1.4 + i * 0.73)
        gauge(asset, [x, 0.150, 0.328], 0.059, range(i, 8, 3))
        lamp(m, [x + 0.083, 0.263, 0.18], Y, 0.016, "ice")
    cable(
        m,
        [
            [-0.48, 0.29, -0.11],
            [-0.54, 0.41, -0.23],
            [-0.16, 0.38, -0.26],
            [0, 0.26, -0.23],
        ],
        "wine",
    )
    for x in [-0.47, -0.38, 0.38, 0.47]:
        knob(m, [x, 0.268, 0.225], 0.023)


def periapsis(asset):
    m = asset.fixed
    # Crescent rail deck assembled from an arcuate series of cross sections.
    a = np.linspace(-1.02, 1.02, 61)
    r = 0.86

    def path(a, r):
        return V([np.sin(a) * r, 0, (np.cos(a) - 1) * r + 0.14])

    section = []
    for ang in a:
        u = V([np.sin(ang), 0, np.cos(ang)])
        c = path(ang, r)
        section.append(
            [
                c - u * 0.16 + 0.09 * Y,
                c + u * 0.17 + 0.09 * Y,
                c + u * 0.18 + 0.115 * Y,
                c + u * 0.16 + 0.22 * Y,
                c - u * 0.15 + 0.22 * Y,
                c - u * 0.17 + 0.19 * Y,
                c - u * 0.16 + 0.09 * Y,
            ]
        )
    m.surface(section, "navy")
    m.cap(section[0], -X, "rose")
    m.cap(section[-1], X, "rose")
    for dr, mat, rr in [
        (-0.12, "brass", 0.006),
        (0, "copper", 0.016),
        (0.12, "brass", 0.006),
    ]:
        pts = [path(ang, r) + [dr * np.sin(ang), 0.224, dr * np.cos(ang)] for ang in a]
        m.tube(pts, rr, mat, 12)
    for ang in np.linspace(-0.98, 0.98, 33):
        u = V([np.sin(ang), 0, np.cos(ang)])
        c = path(ang, r) + 0.224 * Y
        m.rod(c + 0.052 * u, c + 0.092 * u, 0.0025, "ivory", n=7)
    # A common pivot makes the slider follow the exact curvature of the band.
    p = asset.part("Ceramic ribbon carriage", [0, 0.239, 0.14 - r])
    p.tube(
        [
            [0, 0, r - 0.075],
            [0, 0.034, r - 0.069],
            [0, 0.037, r + 0.068],
            [0, 0, r + 0.075],
        ],
        0.013,
        "ivory",
    )
    p.ball([0, 0.039, r], [0.030, 0.027, 0.036], "ice")
    asset.drive(p, "selector", Y, 1.80, rest=-0.90, rate=7)
    for side in [-1, 1]:
        c = path(side * 1.01, r)
        m.ball(c + [0, 0.241, 0], [0.067, 0.042, 0.115], "brass")
        m.turn(c, Y, [(0.014, 0.067), (0.092, 0.048)], "ebony")
    m.case([0, 0.108, 0.323], [0.25, 0.167, 0.063], "navy")
    gauge(asset, [0, 0.117, 0.357], 0.057)
    constellation(m, [0.31, 0.227, 0.18], X, Z, 0.039, "silver", 5)


def choir(asset):
    m = asset.fixed
    console(m, [0, 0.150, 0], [1.21, 0.207, 0.63], "wine")
    for i, x in enumerate(np.linspace(-0.44, 0.44, 5)):
        h = [0.33, 0.44, 0.55, 0.41, 0.31][i]
        c = V([x, 0.276, -0.07])
        m.turn(c, Y, [(0, 0.072), (0.031, 0.081), (0.071, 0.070)], "ebony", 32)
        m.turn(
            c,
            Y,
            [
                (0.068, 0.058),
                (0.092, 0.069),
                (h - 0.055, 0.072),
                (h - 0.015, 0.045),
                (h, 0.012),
            ],
            "smoke",
            40,
        )
        for j in [-1, 1]:
            m.rod(
                c + [j * 0.022, 0.058, 0], c + [j * 0.022, h - 0.085, 0], 0.005, "brass"
            )
        coil(m, c + [0, 0.115, 0], Y, 0.028, h - 0.22, 9, "copper")
        m.ball(c + [0, h * 0.61, 0], [0.014, h * 0.21, 0.014], "amber", 20)
        if i in [0, 4]:
            for a in np.arange(5) * TAU / 5:
                d = V([np.cos(a), 0, np.sin(a)]) * 0.079
                m.tube(
                    [
                        c + d + 0.043 * Y,
                        c + d + (h - 0.04) * Y,
                        c + d * 0.42 + (h + 0.01) * Y,
                    ],
                    0.0048,
                    "tin",
                    8,
                )
        knob(m, [x, 0.277, 0.179], 0.036)
    for i, x in enumerate(np.linspace(-0.34, 0.34, 8)):
        p = asset.part("Formant shutter " + str(i), [x, 0.152, 0.326])
        p.case(O, [0.07, 0.078, 0.012], "bronze", 0.005)
        p.case([0, 0, -0.009], [0.047, 0.062, 0.008], "amber", 0.005)
        asset.drive(p, "key", Y, 1.06, [i])
    for x in [-0.50, 0.50]:
        lamp(m, [x, 0.151, 0.322], Z, 0.024)
    cable(
        m,
        [
            [-0.49, 0.27, -0.14],
            [-0.53, 0.47, -0.22],
            [-0.12, 0.50, -0.24],
            [0.14, 0.32, -0.18],
        ],
        "black",
    )


def reel(asset, c, r, name, rate):
    p = asset.part(name, c)
    p.turn(
        O,
        Z,
        [
            (-0.047, r * 0.90),
            (-0.037, r),
            (-0.031, r),
            (-0.028, r * 0.70),
            (0.035, r * 0.70),
            (0.038, r),
            (0.046, r),
        ],
        "iron",
        56,
    )
    for a in np.arange(5) * TAU / 5:
        d = V([np.cos(a), np.sin(a), 0])
        p.rod(d * 0.043 + Z * 0.047, d * r * 0.94 + Z * 0.047, 0.015, "maple", 0.010)
        p.ball(d * r * 0.54 + Z * 0.050, [0.017, 0.017, 0.004], "ebony", 16)
    p.turn(O, Z, [(0.047, 0.041), (0.062, 0.045), (0.066, 0.028)], "brass", 20)
    asset.drive(p, "spin", Z, 1, rate=rate)


def cryotape(asset):
    m = asset.fixed
    console(m, [0, 0.122, 0], [1.26, 0.158, 0.67], "navy")
    m.case([-0.14, 0.410, -0.058], [0.95, 0.46, 0.153], "teal", 0.041)
    for i, x in enumerate([-0.395, 0.105]):
        reel(
            asset,
            [x, 0.467, 0.067],
            0.170,
            "Oxide reel " + str(i + 1),
            2.7 if i == 0 else 3.31,
        )
    pts = [
        [-0.53, 0.467, 0.087],
        [-0.512, 0.358, 0.087],
        [-0.36, 0.269, 0.087],
        [-0.19, 0.250, 0.087],
        [0.01, 0.279, 0.087],
        [0.234, 0.384, 0.087],
        [0.242, 0.467, 0.087],
    ]
    m.tube(pts, 0.006, "leather", 8)
    for x in [-0.32, -0.19, -0.06]:
        m.case([x, 0.271, 0.083], [0.062, 0.056, 0.068], "iron", 0.008)
        m.case([x, 0.249, 0.100], [0.049, 0.012, 0.035], "silver", 0.004)
    m.turn(
        [0.475, 0.22, 0],
        Y,
        [
            (0, 0.084),
            (0.025, 0.111),
            (0.058, 0.114),
            (0.51, 0.092),
            (0.57, 0.075),
            (0.589, 0.044),
        ],
        "tin",
        40,
    )
    for y in [0.274, 0.65, 0.755]:
        binding(m, [0.475, y, 0], Y, 0.111 if y < 0.4 else 0.098, 0.025, "brass")
    for i in range(4):
        y = 0.34 + i * 0.061
        cable(
            m,
            [
                [0.452, y, 0.105],
                [0.464, y + 0.016, 0.106],
                [0.487, y + 0.023, 0.104],
                [0.501, y + 0.036, 0.101],
            ],
            "tin",
            0.0027,
        )
    cable(
        m,
        [
            [0.47, 0.80, 0],
            [0.44, 0.86, -0.03],
            [0.30, 0.82, -0.11],
            [0.30, 0.56, -0.148],
        ],
        "copper",
    )
    for x in [-0.45, -0.38, -0.31]:
        knob(m, [x, 0.223, 0.235], 0.025)
    gauge(asset, [0.17, 0.136, 0.342], 0.052)
    lamp(m, [0.33, 0.222, 0.20], Y, 0.019, "ice")


def pulsar(asset):
    m = asset.fixed
    m.turn(
        O,
        Y,
        [(0.015, 0.29), (0.039, 0.37), (0.094, 0.41), (0.134, 0.39), (0.149, 0.34)],
        "navy",
        64,
    )
    m.ring([0, 0.129, 0], Y, 0.39, 0.008, "brass")
    c = V([0, 0.55, 0])
    r = 0.355
    m.tube([[-0.23, 0.135, 0], [-0.36, 0.29, 0], [-0.37, 0.55, 0]], 0.027, "bronze")
    m.tube([[0.23, 0.135, 0], [0.36, 0.29, 0], [0.37, 0.55, 0]], 0.027, "bronze")
    m.ring(c, Z, r + 0.025, 0.019, "bronze", 64)
    p = asset.part("Perforated star chart", c)
    for rr in [0.054, 0.094, 0.126, 0.162, 0.199, 0.238, 0.276, 0.313, 0.35]:
        p.ring(O, Z, rr, 0.005, "brass", 64)
    # Open rows and short punched bridges physically interrupt the reader beam.
    for j in range(8):
        for i in range(13):
            if (i * 7 + j * 3) % 5 == 0:
                continue
            a = TAU * (i / 13 + j * 0.027)
            rr = 0.075 + 0.035 * j
            d = X * np.cos(a) + Y * np.sin(a)
            p.rod(d * (rr - 0.019), d * (rr + 0.019), 0.0045, "copper", n=6)
    for i in range(6):
        a = i * TAU / 6
        p.rod(O, r * (X * np.cos(a) + Y * np.sin(a)), 0.0048, "iron")
    p.turn(O, Z, [(-0.036, 0.046), (0.025, 0.055), (0.039, 0.037)], "brass", 24)
    asset.drive(p, "spin", Z, 1, rate=1.43)
    # A visible splice in the belt travels around the motor and chart pulleys.
    motor = V([-0.20, 0.223, -0.082])
    m.turn(motor, Z, [(-0.071, 0.055), (-0.064, 0.063), (-0.010, 0.056)], "teal", 26)
    m.rod(motor - Y * 0.012, [-0.20, 0.132, -0.12], 0.022, "iron")
    wheel = asset.part("Spliced drive pulley", motor)
    wheel.turn(
        O,
        Z,
        [(-0.009, 0.040), (-0.006, 0.046), (0.006, 0.046), (0.009, 0.040)],
        "bronze",
        26,
    )
    wheel.rod([-0.032, 0, 0.008], [0.032, 0, 0.008], 0.003, "tin", n=6)
    asset.drive(wheel, "spin", Z, 1, rate=1.43)
    m.turn(
        c,
        Z,
        [(-0.096, 0.043), (-0.086, 0.051), (-0.074, 0.051), (-0.067, 0.041)],
        "bronze",
        28,
    )
    axle = c - Z * 0.082
    travel = (axle - motor) / np.linalg.norm(axle - motor)
    edge = np.cross(travel, Z)
    arc = np.linspace(0, np.pi, 25)
    route = [motor + edge * 0.046] + [
        axle + 0.046 * (edge * np.cos(a) + travel * np.sin(a)) for a in arc
    ]
    route.extend(motor + 0.046 * (-edge * np.cos(a) - travel * np.sin(a)) for a in arc)
    route[-1] = route[0]
    m.tube(route, 0.004, "leather", 8)
    splice = asset.part("Laced belt splice", route[0])
    splice.ball(O, 0.006, "cord", 12)
    asset.drive(splice, "belt", Z, 1, rate=0.046 * 1.43)
    asset.tracks[-1]["route"] = V(route)
    m.tube(
        [
            [0, 0.18, 0],
            [0.032, 0.30, 0.096],
            [0.054, 0.53, 0.093],
            [0.072, 0.56, 0.054],
        ],
        0.016,
        "teal",
    )
    lamp(m, [0.071, 0.557, 0.054], -Z, 0.024, "ice")
    for i in range(8):
        a = -0.94 + i * 0.269
        d = V([np.sin(a), 0, np.cos(a)])
        key = asset.part("Optical stop " + str(i), d * 0.315 + Y * 0.148)
        key.turn(
            O,
            Y,
            [(0, 0.020), (0.031, 0.021), (0.038, 0.017)],
            "amber" if i % 2 else "ice",
            16,
        )
        asset.drive(key, "press", Y, -0.020, [i])
    for x in [-0.19, 0.19]:
        knob(m, [x, 0.15, -0.15], 0.031)

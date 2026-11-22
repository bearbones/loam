"""Tuned bodies, hand percussion, rotating glass and bellows."""

import numpy as np

from .fittings import binding, constellation, feet, hammer, plectrum
from .mesh import TAU, O, V, X, Y, Z
from .winds import pallet, pierced


def balafon(asset):
    m = asset.fixed
    for side in [-1, 1]:
        m.rod(
            [-0.88, 0.48, side * 0.20], [0.88, 0.48, side * 0.155], 0.028, "maple", n=20
        )
        for x in [-0.78, 0.78]:
            m.rod(
                [x, 0.48, side * 0.18],
                [x * 1.075, 0.025, side * 0.34],
                0.031,
                "walnut",
                0.023,
            )
            binding(m, [x, 0.44, side * 0.18], Y, 0.034, 0.040, "red")
    m.rod([-0.83, 0.68, -0.38], [0.84, 0.68, -0.38], 0.023, "walnut")
    for x in [-0.81, 0.81]:
        m.rod([x, 0.455, -0.16], [x, 0.68, -0.38], 0.020, "bronze")
    for i in range(8):
        x = (i - 3.5) * 0.207
        length = 0.70 - i * 0.035
        r = 0.105 - i * 0.004
        m.turn(
            [x, 0.098 + i * 0.016, 0],
            Y,
            [
                (0, 0.027),
                (0.017, r * 0.7),
                (0.077, r),
                (0.162, r * 0.88),
                (0.230, r * 0.52),
                (0.262, 0.037),
                (0.276, 0.035),
                (0.276, 0.026),
                (0.24, 0.026),
            ],
            "maple" if i % 3 else "ochre",
            36,
            False,
        )
        m.ring([x, 0.267 + i * 0.016, r * 0.76], Z, 0.025, 0.004, "ochre")
        leaf = V([x, 0.201 + i * 0.016, r * 0.976])
        m.tube(
            [
                leaf,
                leaf + [-0.023, 0.009, -0.002],
                leaf + [-0.025, 0.026, -0.006],
                leaf + [-0.006, 0.018, 0],
                leaf,
            ],
            0.003,
            "glaze",
            7,
        )
        for z in [-1, 1]:
            m.tube(
                [
                    [x - 0.035, 0.51, z * length * 0.27],
                    [x - 0.035, 0.46, z * 0.18],
                    [x + 0.035, 0.46, z * 0.18],
                    [x + 0.035, 0.51, z * length * 0.27],
                ],
                0.005,
                "red",
                8,
            )
        key = asset.part("Tied bar " + str(i + 1), [x, 0.513, 0])
        key.case(O, [0.189, 0.050, length], "rose" if i != 2 else "maple", 0.020)
        for z in [-length * 0.28, length * 0.28]:
            for dx in [-0.037, 0.037]:
                key.ball([dx, 0.025, z], [0.009, 0.006, 0.01], "cord", 12)
        asset.drive(key, "ring", X, 0.026, [i])
        hammer(asset, [x, 0.682, -0.38], [x, 0.538, -0.06], [i], radius=0.034)
    for j in range(4):
        m.ring([-0.82 + j * 0.016, 0.48, 0.199], X, 0.030, 0.003, "cord")


def mbira(asset):
    m = asset.fixed
    m.case([0, 0.115, 0], [0.68, 0.18, 0.71], "walnut", 0.066)
    m.case([0, 0.209, 0], [0.66, 0.025, 0.69], "maple", 0.058)
    m.rosette([0.191, 0.224, 0.215], Y, 0.065, 6)
    for z in [-0.13, -0.041]:
        m.rod([-0.295, 0.248, z], [0.295, 0.248, z], 0.014, "iron", n=24)
    for x in [-0.27, 0, 0.27]:
        m.screw([x, 0.228, -0.105], Y, 0.016)
    for i in range(16):
        x = (i - 7.5) * 0.033
        raised = 0.038 if i < 7 else 0
        length = 0.12 + 0.14 * (1 - abs(i - 7.3) / 9)
        p = asset.part("Forged tongue " + str(i + 1), [x, 0.256 + raised, -0.105])
        # Splayed steel tongue with a rolled, polished thumb end.
        sec = [
            (-0.11, 0.006, -0.007),
            (0, 0.006, 0),
            (0.07, 0.008, 0.015),
            (length, 0.011, 0.035),
            (length + 0.02, 0.012, 0.027),
        ]
        grid = []
        for z, w, y in sec:
            grid.append(
                [
                    [-w, y - 0.003, z],
                    [-w, y + 0.003, z],
                    [w, y + 0.003, z],
                    [w, y - 0.003, z],
                    [-w, y - 0.003, z],
                ]
            )
        p.surface(grid, "iron" if i % 4 else "tin")
        p.cap(grid[-1], Z, "silver")
        p.case([0, 0.032, length + 0.005], [0.022, 0.006, 0.028], "silver", 0.003)
        asset.drive(p, "pluck", X, 0.105, [i % 8])
        if (i < 8 and i % 2 == 0) or (i >= 8 and i % 2 == 1):
            tip = V([x, 0.288 + raised, length - 0.100])
            root = V([x, 0.282, 0.295])
            m.rod([x, 0.218, 0.295], root, 0.007, "bronze")
            plectrum(asset, root, tip, [i % 8], Y)
    m.rod([-0.305, 0.293, -0.122], [0.307, 0.293, -0.122], 0.012, "brass")
    for x in [-0.285, 0.285]:
        m.rod([x, 0.222, -0.122], [x, 0.294, -0.122], 0.012, "iron")
    for j, x in enumerate(np.linspace(-0.25, 0.25, 7)):
        p = asset.part("Loose cap " + str(len(asset.nodes)), [x, 0.245, -0.262])
        p.turn(
            O,
            Y,
            [(-0.009, 0.028), (-0.004, 0.03), (0.005, 0.024)],
            "tin" if j != 2 else "copper",
            15,
        )
        p.ring(O, Y, 0.026, 0.002, "copper", 15)
        constellation(p, [0, 0.006, 0], X, Z, 0.016, "iron", 5)
        m.rod([x, 0.22, -0.262], [x, 0.262, -0.262], 0.003, "iron")
        asset.drive(p, "ring", Z, 0.11)
    m.staples([-0.26, 0.224, 0.19], X * 0.018, Z * 0.038)


def tabla(asset):
    m = asset.fixed
    for idx, (x, r, h, mat) in enumerate(
        [(-0.25, 0.249, 0.43, "copper"), (0.27, 0.19, 0.49, "rose")]
    ):
        c = V([x, 0.048, 0])
        m.ring(c, Y, r * 0.58, 0.036, "wine")
        profile = [
            (0, 0.48 * r),
            (0.027, r * 0.57),
            (0.12 * h, 0.77 * r),
            (0.41 * h, r * (1 if idx == 0 else 0.83)),
            (0.68 * h, r * 0.99),
            (h, r * 0.94),
        ]
        m.turn(c, Y, profile, mat, 56)
        top = c + Y * h
        m.turn(top, Y, [(-0.009, r * 0.98), (0, r), (0.009, r * 0.925)], "skin", 60)
        m.ring(top + Y * 0.006, Y, 0.91 * r, 0.010, "cord")
        m.turn(
            top + V([0.036 if idx == 0 else 0, 0.010, 0]),
            Y,
            [(0, 0.36 * r), (0.002, 0.34 * r)],
            "black",
            48,
        )
        for a in np.arange(16) * TAU / 16:
            d = X * np.cos(a) + Z * np.sin(a)
            e = X * np.cos(a + 0.08) + Z * np.sin(a + 0.08)
            # Both runs follow the curved shell and bear on the gatta blocks.
            for bottom, upper in [(d, e), (e, d)]:
                strap = [
                    c
                    + ((1 - level / h) * bottom + (level / h) * upper)
                    * (radius + 0.009)
                    + Y * level
                    for level, radius in profile
                ]
                m.tube(strap, 0.007, "cord", 8)
            if round(a * 16 / TAU) % 2 == 0:
                p = c + d * (profile[3][1] + 0.011) + Y * h * 0.43
                m.turn(
                    p,
                    Y,
                    [(-0.042, 0.013), (-0.030, 0.021), (0.032, 0.021), (0.046, 0.014)],
                    "walnut" if idx == 1 and 0.1 < a < 1.1 else "maple",
                    18,
                )
        # A chased lunar almanac runs around the copper shell below its lip.
        if idx == 0:
            for k in range(8):
                a = (k - 3.5) * TAU / 16
                radial = V([np.sin(a), 0, np.cos(a)])
                across = V([np.cos(a), 0, -np.sin(a)])
                point = c + radial * (r + 0.001) + Y * (h * 0.75)
                t = np.linspace(0.70, TAU - 0.70, 19)
                m.tube(
                    [
                        point + 0.012 * np.cos(q) * across + 0.014 * np.sin(q) * Y
                        for q in t
                    ],
                    0.0028,
                    "brass",
                    7,
                )
        # A hinged finger pad, set above the black patch and separately
        # weighted outer stroke; each pad ends on the skin at full closure.
        for j in range(2):
            pt = top + [(-0.025 if j == 0 else 0.41 * r), 0.012, 0.042 * j]
            root = top + [(j - 0.5) * 0.095, 0.090, -r - 0.042]
            m.rod(root - Y * 0.165, root, 0.011, "brass")
            m.rod(
                top + [(j - 0.5) * 0.095, -0.080, -r * 0.94],
                root - Y * 0.165,
                0.009,
                "bronze",
            )
            hammer(
                asset,
                root,
                pt,
                [idx * 3 + j, idx * 3 + 2] if j == 0 else [idx * 3 + j],
                skin="skin",
                radius=0.024,
            )


def kulintang(asset):
    m = asset.fixed
    for side in [-1, 1]:
        m.case([0, 0.25, side * 0.19], [2.40, 0.185, 0.039], "rose")
        m.case([0, 0.314, side * 0.215], [2.4, 0.014, 0.009], "brass", 0.003)
        for x in [-1.09, 1.09]:
            m.rod(
                [x, 0.26, side * 0.179],
                [x * 1.055, 0.018, side * 0.238],
                0.031,
                "ebony",
            )
        for k in range(15):
            x = -1.08 + k * 0.154
            m.tube(
                [
                    [x, 0.26, side * 0.212],
                    [x + 0.035, 0.282, side * 0.217],
                    [x + 0.068, 0.243, side * 0.213],
                ],
                0.004,
                "maple",
                7,
            )
    m.rod([-1.16, 0.55, -0.29], [1.16, 0.55, -0.29], 0.017, "bronze")
    for x in [-1.14, 1.14]:
        m.case([x, 0.30, 0], [0.052, 0.16, 0.43], "walnut")
        m.rod([x, 0.32, -0.19], [x, 0.55, -0.29], 0.015, "brass")
    for i in range(8):
        x = (i - 3.5) * 0.29
        r = 0.145 - i * 0.005
        p = asset.part("Bossed gong " + str(i + 1), [x, 0.358, 0])
        p.turn(
            O,
            Y,
            [
                (-0.048, r * 0.91),
                (-0.035, r),
                (0.009, r * 0.965),
                (0.030, r * 0.75),
                (0.041, r * 0.33),
                (0.060, r * 0.24),
                (0.071, r * 0.17),
                (0.073, 0.005),
            ],
            "bronze",
            56,
        )
        for f in [0.43, 0.75, 0.91]:
            p.ring([0, 0.043 - 0.034 * f, 0], Y, r * f, 0.002, "brass")
        for side in [-1, 1]:
            m.tube(
                [
                    [x - 0.06, 0.32, side * 0.195],
                    [x - 0.04, 0.30, side * 0.10],
                    [x + 0.046, 0.30, -side * 0.10],
                    [x + 0.06, 0.32, -side * 0.195],
                ],
                0.0045,
                "cord",
                8,
            )
        asset.drive(p, "ring", Z, 0.046, [i])
        hammer(asset, [x, 0.55, -0.29], [x, 0.431, 0], [i], "maple", 0.024)


def udu(asset):
    m = asset.fixed
    profile = [
        (0.035, 0.093),
        (0.063, 0.149),
        (0.14, 0.232),
        (0.27, 0.297),
        (0.41, 0.286),
        (0.51, 0.230),
        (0.59, 0.129),
        (0.65, 0.073),
        (0.75, 0.069),
        (0.78, 0.092),
        (0.799, 0.093),
    ]
    pierced(m, O, profile, [(0, 0.39, 0.071)], "clay", 0.018)
    m.ring([0, 0.799, 0], Y, 0.085, 0.009, "glaze")
    for y, r in [(0.11, 0.215), (0.135, 0.23), (0.553, 0.18), (0.566, 0.159)]:
        m.ring([0, y, 0], Y, r, 0.005, "ivory")
    angle = np.linspace(-2.4, 2.8, 71)
    for j in range(2):
        h = 0.228 + j * 0.022 + 0.020 * np.sin(angle * 4)
        rr = np.interp(h, *np.array(profile).T)
        m.tube(
            np.c_[(rr + 0.004) * np.sin(angle), h, (rr + 0.004) * np.cos(angle)],
            0.004,
            "glaze",
            8,
        )
    for i in range(5):
        y = 0.43 + i * 0.023
        r = np.interp(y, *np.array(profile).T)
        a = 1.08 + 0.06 * i
        m.tube(
            [
                [r * np.sin(a - 0.06), y, r * np.cos(a - 0.06)],
                [(r + 0.01) * np.sin(a), y + 0.006, (r + 0.01) * np.cos(a)],
                [r * np.sin(a + 0.06), y + 0.012, r * np.cos(a + 0.06)],
            ],
            0.005,
            "cord",
            8,
        )
    m.ring([0, 0.03, 0], Y, 0.105, 0.022, "wine")
    pallet(asset, [0, 0.39, 0.288], 0.067, Z, [0, 1])
    pallet(asset, [0, 0.792, 0], 0.072, Y, [2, 3, 4])


def handpan(asset):
    m = asset.fixed
    m.turn(
        O,
        Y,
        [
            (0.04, 0.095),
            (0.057, 0.19),
            (0.11, 0.296),
            (0.18, 0.367),
            (0.219, 0.386),
            (0.231, 0.387),
            (0.275, 0.35),
            (0.318, 0.281),
            (0.354, 0.19),
            (0.377, 0.100),
            (0.380, 0.010),
        ],
        "navy",
        80,
    )
    m.ring([0, 0.225, 0], Y, 0.388, 0.008, "bronze", 80)
    m.ring([0, 0.048, 0], Y, 0.112, 0.020, "leather")
    for i in range(8):
        a = i * TAU / 7
        c = (
            V([0.248 * np.cos(a), 0.325, 0.248 * np.sin(a)])
            if i < 7
            else V([0, 0.380, 0])
        )
        size = 0.069 if i < 7 else 0.081
        p = asset.part("Hammered tone island " + str(i + 1), c)
        p.ball(O, [size, 0.020, size * 0.83], "tin" if i == 7 else "navy", 32)
        p.ring(O, Y, size * 0.87, 0.0035, "bronze", 40)
        p.ball([0, 0.010, 0], [size * 0.55, 0.025, size * 0.50], "iron", 24)
        asset.drive(p, "ring", X, 0.070, [i])
        direction = V([np.cos(a), 0, np.sin(a)]) if i < 7 else -Z
        root = direction * (0.41 if i < 7 else 0.34) + Y * (0.34 if i < 7 else 0.45)
        m.rod(direction * 0.368 + Y * 0.223, root, 0.008, "bronze")
        hammer(asset, root, c + Y * 0.035, [i], skin="leather", radius=0.018)
    for i in range(5):
        a = i * 0.034
        m.ball([0.386 * np.sin(a), 0.231, 0.386 * np.cos(a)], 0.005, "brass", 12)


def armonica(asset):
    m = asset.fixed
    m.case([0, 0.115, 0], [1.61, 0.16, 0.53], "walnut", 0.062)
    feet(m, [-0.66, 0.66], [-0.17, 0.17], 0.05)
    for x in [-0.66, 0.66]:
        m.case([x, 0.357, 0], [0.077, 0.467, 0.27], "rose", 0.030)
        m.turn([x - 0.05, 0.542, 0], X, [(0, 0.087), (0.10, 0.087)], "bronze")
        m.screw([x, 0.335, 0.138], Z, 0.018)
    spindle = asset.part("Glass spindle", [-0.77, 0.542, 0])
    spindle.rod(O, [1.60, 0, 0], 0.018, "silver")
    spindle.turn([0.018, 0, 0], X, [(-0.012, 0.172), (0.012, 0.172)], "bronze", 48)
    spindle.rod([0, 0, 0], [0, 0.161, 0], 0.012, "maple")
    spindle.rod([0, 0.161, 0], [-0.102, 0.161, 0], 0.013, "ebony")
    for i in range(13):
        x = 0.184 + i * 0.088
        r = 0.241 - i * 0.0105
        # The inside return gives each bowl a true open mouth.
        spindle.turn(
            [x, 0, 0],
            X,
            [
                (0, 0.035),
                (0.028, r * 0.44),
                (0.068, r * 0.78),
                (0.117, r * 0.97),
                (0.14, r),
                (0.14, r - 0.006),
                (0.095, r * 0.865),
                (0.049, r * 0.45),
            ],
            "glass",
            48,
            False,
        )
        spindle.ring(
            [x + 0.138, 0, 0], X, r - 0.003, 0.004, "ivory" if i % 3 else "brass"
        )
        spindle.ball([x + 0.127, r * 0.98, 0], 0.008, "ice", 12)
    asset.drive(spindle, "spin", X, 1, rate=2.7)
    for i, j in enumerate([0, 2, 4, 5, 7, 9, 11, 12]):
        x = -0.77 + 0.184 + j * 0.088 + 0.138
        r = 0.241 - j * 0.0105
        m.rod([x - 0.023, 0.39, 0.278], [x - 0.023, 0.548, r + 0.016], 0.007, "bronze")
        pallet(asset, [x, 0.548, r - 0.002], 0.012, Z, [i])
    m.case([0, 0.39, 0.278], [1.34, 0.040, 0.040], "maple", 0.013)
    for x in [-0.66, 0.66]:
        m.rod([x, 0.34, 0.12], [x, 0.39, 0.279], 0.018, "brass")


def bandoneon(asset):
    m = asset.fixed
    # The pleated leather expands about its centre. Both button boxes and
    # their buttons travel with the two moving ends.
    folds = asset.part("Gusseted leather bellows", [0, 0.29, 0])
    a = np.linspace(0, TAU, 41)
    profile = []
    for i in range(29):
        x = -0.355 + i * 0.71 / 28
        w = 0.219 if i % 2 else 0.247
        yy = np.sign(np.cos(a)) * np.abs(np.cos(a)) ** 0.31 * w
        zz = np.sign(np.sin(a)) * np.abs(np.sin(a)) ** 0.31 * w * 0.92
        profile.append(np.c_[x + 0 * a, yy, zz])
    folds.surface(profile, "wine")
    for i in range(0, 29, 2):
        folds.tube(profile[i], 0.004, "leather", 7)
    # The patch crosses three pleats, following the gussets as they expand.
    patch = []
    for i in range(6, 13):
        x = -0.355 + i * 0.71 / 28
        z = (0.219 if i % 2 else 0.247) * 0.92 + 0.002
        patch.append([[x, -0.042, z], [x, 0.021, z]])
    folds.surface(patch, "leather")
    for i, row in enumerate(patch[:-1]):
        for edge in [0, 1]:
            a = V(row[edge])
            b = V(patch[i + 1][edge])
            folds.rod(
                a * 0.78 + b * 0.22 + Z * 0.002,
                a * 0.29 + b * 0.71 + Z * 0.002,
                0.002,
                "cord",
                n=7,
            )
    asset.drive(folds, "bellows", X, 0.51, rate=2.65)
    for side in [-1, 1]:
        p = asset.part(
            ("Left" if side < 0 else "Right") + " reed chest", [side * 0.437, 0.29, 0]
        )
        p.case(O, [0.171, 0.512, 0.470], "ebony", 0.039)
        p.case([side * 0.080, 0, 0], [0.026, 0.47, 0.431], "rose", 0.035)
        for y in [-0.211, 0.211]:
            p.case([0, y, 0.233], [0.162, 0.031, 0.014], "brass", 0.005)
        p.rosette([0, 0.078, 0.24], Z, 0.061, 9)
        for j in range(12):
            y = (j // 3 - 1.5) * 0.088
            z = (j % 3 - 1) * 0.088
            point = V([side * 0.104, y, z])
            b = asset.part(f"{side} pearl {j}", point, parent=p)
            b.turn(
                O,
                X * side,
                [(-0.008, 0.017), (0.018, 0.017), (0.024, 0.014)],
                "ivory" if j % 4 else "bronze",
                18,
            )
            asset.drive(b, "press", X * side, -0.015, [j % 8])
        asset.drive(p, "breathe", X * side, 0.355 * 0.51, rate=2.65)
    # Feet are carried by the chests; the central runner supports travel.
    m.case([0, 0.014, 0], [1.37, 0.027, 0.37], "walnut", 0.012)

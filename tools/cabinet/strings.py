"""Lutes, zithers and fiddles. The playing surface faces +Z except for the koto."""

import numpy as np

from .fittings import binding, bow, cable, constellation, peg, plectrum, soundbox, wire
from .mesh import TAU, O, V, X, Y, Z


def oud(asset):
    m = asset.fixed
    profile = [
        (0.03, 0.05),
        (0.10, 0.23),
        (0.26, 0.373),
        (0.46, 0.385),
        (0.67, 0.30),
        (0.86, 0.17),
        (0.98, 0.06),
    ]
    soundbox(m, profile, 0.35)
    # Long alternate bowl staves end at the same narrow neck block.
    for i, a in enumerate(np.linspace(0.12, np.pi - 0.12, 13)):
        line = [
            [w * np.cos(a), h, -0.33 * np.sin(a) * (w / 0.385) ** 0.72 - 0.012]
            for h, w in profile
        ]
        cable(m, line, "rose" if i == 7 else "maple", 0.0055)
    m.case([0, 1.11, -0.014], [0.125, 0.38, 0.055], "ebony", 0.02)
    m.tube(
        [[0, 1.27, -0.02], [0, 1.34, -0.03], [0, 1.44, -0.15], [0, 1.52, -0.23]],
        0.048,
        "walnut",
    )
    for i in range(6):
        for side in [-1, 1]:
            peg(m, [side * 0.025, 1.32 + i * 0.032, -0.025 - i * 0.033], side)
    for x, y, r in [(0, 0.59, 0.118), (-0.17, 0.45, 0.050), (0.17, 0.45, 0.050)]:
        m.rosette([x, y, 0.004], Z, r, 8)
    m.case([0, 0.23, 0.019], [0.29, 0.046, 0.044], "rose", 0.014)
    for i, x in enumerate(np.linspace(-0.092, 0.092, 11)):
        lane = min(7, i * 8 // 11)
        wire(asset, [x, 0.24, 0.046], [x * 0.50, 1.30, 0.045], [lane], radius=0.0025)
    for i in range(4):
        x = -0.095 + i * 0.061
        plectrum(
            asset, [x - 0.018, 0.219, 0.052], [x, 0.30, 0.048], range(i * 2, i * 2 + 2)
        )
    # A marquetry moth with one replacement wing in copper.
    centre = V([0.195, 0.31, 0.004])
    for side, mat in [(-1, "walnut"), (1, "copper")]:
        wing = [
            (0, 0),
            (0.032, 0.038),
            (0.059, 0.042),
            (0.047, 0.012),
            (0.026, 0.001),
            (0.042, -0.022),
            (0.022, -0.028),
            (0, 0),
        ]
        m.tube([centre + side * x * X + y * Y for x, y in wing], 0.0032, mat, 8)
        m.rod(
            centre + 0.007 * Y,
            centre + side * 0.018 * X + 0.034 * Y,
            0.002,
            "ebony",
            n=6,
        )
        m.ball(centre + side * 0.031 * X + 0.018 * Y, 0.007, "ivory", 12)
    m.rod(centre - 0.014 * Y, centre + 0.021 * Y, 0.003, "ebony", n=8)


def fingerboard(m, y0, y1, width):
    m.case([0, (y0 + y1) / 2, 0.045], [width, y1 - y0, 0.068], "ebony", 0.014)
    m.case([0, y1, 0.087], [width, 0.020, 0.020], "ivory", 0.006)


def fiddle(asset, keyed):
    m = asset.fixed
    if keyed:
        profile = [
            (0.02, 0.09),
            (0.09, 0.18),
            (0.25, 0.23),
            (0.39, 0.17),
            (0.50, 0.21),
            (0.65, 0.13),
            (0.76, 0.084),
        ]
        soundbox(m, profile, 0.155, "rose")
    else:
        profile = [
            (0.02, 0.04),
            (0.08, 0.18),
            (0.22, 0.235),
            (0.32, 0.22),
            (0.37, 0.14),
            (0.47, 0.113),
            (0.53, 0.19),
            (0.66, 0.17),
            (0.76, 0.055),
        ]
        soundbox(m, profile, 0.13, "maple")
    fingerboard(m, 0.44, 1.13, 0.095 if not keyed else 0.13)
    m.case([0, 0.17, 0.048], [0.092, 0.19, 0.053], "ebony", 0.02)
    m.case([0, 0.35, 0.067], [0.165, 0.029, 0.112], "maple", 0.012)
    m.case([0, 1.20, 0.015], [0.105, 0.20, 0.09], "walnut", 0.025)
    for i in range(4 if not keyed else 7):
        peg(
            m,
            [0.049 * (1 if i % 2 else -1), 1.13 + i * 0.027, 0.023],
            1 if i % 2 else -1,
        )
    for i in range(4):
        x = (i - 1.5) * 0.022
        wire(
            asset,
            [x, 0.35, 0.13],
            [x * 0.7, 1.14, 0.102],
            range(i * 2, i * 2 + 2),
            radius=0.0023,
        )
        m.rod([x, 0.19, 0.086], [x, 0.35, 0.13], 0.0025, "silver", n=7)
    for i in range(10 if keyed else 4):
        x = (i - (4.5 if keyed else 1.5)) * 0.008
        m.rod([x, 0.16, 0.058], [x, 1.19, 0.060], 0.0016, "brass", n=6)
    for side in [-1, 1]:
        cable(
            m,
            [
                [side * 0.142, 0.27, 0.006],
                [side * 0.12, 0.30, 0.006],
                [side * 0.145, 0.35, 0.006],
                [side * 0.126, 0.405, 0.006],
                [side * 0.145, 0.44, 0.006],
            ],
            "ebony",
            0.009,
        )
        m.ball([side * 0.145, 0.44, 0.008], 0.016, "ebony", 16)
    if keyed:
        m.case([-0.035, 0.77, -0.002], [0.245, 0.70, 0.078], "walnut")
        for i in range(14):
            y = 0.48 + i * 0.043
            p = asset.part("Tangent key " + str(i + 1), [-0.105, y, 0.008])
            p.case([-0.065, 0, 0], [0.16, 0.030, 0.032], "maple", 0.009)
            p.case([-0.15, 0, 0], [0.04, 0.038, 0.042], "ebony", 0.007)
            asset.drive(p, "press", X, 0.018, [i % 8])
        m.staples([-0.142, 0.69, 0.044], X * 0.011, Y * 0.021)
    else:
        for i in range(4):
            side = (-1) ** i
            peg(m, [side * 0.047, 1.17 + i * 0.04, -0.045], side)
        for x, y, r in [
            (0.14, 0.19, 0.067),
            (-0.14, 0.19, 0.067),
            (0.096, 0.62, 0.045),
            (-0.096, 0.62, 0.045),
        ]:
            constellation(m, [x, y, 0.005], X, Y, r, "ivory", 9)
    # Carved open spiral and cream eye on the head.
    a = np.linspace(0.1, TAU * 1.46, 64)
    rad = np.linspace(0.068, 0.009, len(a))
    m.tube(
        np.c_[rad * np.cos(a), 1.32 + rad * np.sin(a), np.zeros(len(a))], 0.017, "maple"
    )
    m.ball([0, 1.324, 0.013], [0.017, 0.020, 0.011], "ice" if not keyed else "ivory")
    bow(asset, [0, 0.402, 0.13], 0.67)


def nyckelharpa(asset):
    fiddle(asset, True)


def hardanger(asset):
    fiddle(asset, False)


def koto(asset):
    m = asset.fixed
    # Arched paulownia cross section, with lacquer end shoes and a belly seam.
    sections = np.linspace(-1.02, 1.02, 41)
    z = np.linspace(-0.24, 0.24, 17)

    def top(x, z):
        return 0.20 + 0.055 * (1 - (z / 0.245) ** 2) + 0.019 * np.cos(x * np.pi / 2.1)

    rows = [np.array([[x, top(x, zz), zz] for zz in z]) for x in sections]
    m.surface(rows, "spruce")
    for side in [-1, 1]:
        m.case([0, 0.136, side * 0.24], [2.02, 0.13, 0.026], "rose", 0.013)
        m.case([0, 0.181, side * 0.254], [2.03, 0.010, 0.008], "ivory", 0.004)
        m.case([side * 0.88, 0.054, 0], [0.105, 0.105, 0.42], "ebony")
        m.case([side * 0.991, 0.153, 0], [0.080, 0.155, 0.495], "wine")
    for i, zz in enumerate(np.linspace(-0.212, 0.212, 13)):
        x = -0.60 + i * 0.085
        yy = top(x, zz)
        for side in [-1, 1]:
            m.rod(
                [x + side * 0.034, yy, zz], [x, yy + 0.088, zz], 0.012, "ivory", 0.008
            )
        m.rod([x - 0.008, yy + 0.086, zz], [x + 0.01, yy + 0.086, zz], 0.010, "ivory")
        end = np.array([0.93, 0.245, zz])
        peak = np.array([x, yy + 0.093, zz])
        wire(asset, peak, end, [i], radius=0.0024, draw=Z)
        m.rod([-0.97, 0.235, zz], peak, 0.0022, "silver", n=7)
        m.turn(end, Y, [(-0.019, 0.008), (0.015, 0.008)], "bronze", 10)
        tip = peak + (end - peak) * ((0.81 - x) / (0.93 - x))
        root = V([0.957, 0.265, zz])
        m.rod([0.957, 0.203, zz], root, 0.007, "brass")
        plectrum(asset, root, tip, [i], Y)
    for side in [-1, 1]:
        for i in range(7):
            x = side * (0.78 + i * 0.027)
            m.rod(
                [x, top(x, 0.222) + 0.004, 0.222],
                [x + 0.020, top(x, 0.235) + 0.004, 0.235],
                0.003,
                "brass",
                n=6,
            )
    for i in range(3):
        c = V([0.43 + i * 0.092, 0.148, 0.256])
        t = np.linspace(0, np.pi, 13)
        m.tube(
            [c + X * 0.029 * np.cos(a) + Y * 0.016 * np.sin(a) for a in t],
            0.0024,
            "ivory",
            7,
        )
        for dx in [-0.015, 0, 0.015]:
            m.rod(
                c + X * dx - Y * 0.005,
                c + X * (dx - 0.007) - Y * 0.018,
                0.0018,
                "tin",
                n=6,
            )


def kora(asset):
    m = asset.fixed
    c = np.array([0, 0.38, 0])
    r = 0.335
    # Cut the calabash at its widest section so the stretched hide is
    # unobstructed. Its equator and the hide hoop share a single rim.
    shell = [
        (0.087 - 0.405 * np.cos(a), r * np.sin(a))
        for a in np.linspace(0.025, np.pi / 2, 30)
    ]
    m.turn(c, Z, shell, "clay", 64, False)
    m.turn(c, Z, [(0.055, r * 0.91), (0.09, r), (0.102, r * 0.985)], "skin", 64)
    m.ring(c + Z * 0.098, Z, r * 0.97, 0.009, "leather")
    for i in range(44):
        a = TAU * i / 44
        m.ball(
            c + [r * 0.955 * np.cos(a), r * 0.955 * np.sin(a), 0.105],
            0.0075,
            "brass",
            12,
        )
    m.rod([0, 0.04, -0.015], [0, 1.54, -0.095], 0.034, "maple", 0.023, 24)
    for side in [-1, 1]:
        m.rod(
            [side * 0.19, 0.17, 0.125],
            [side * 0.19, 0.77, 0.18],
            0.016,
            "walnut",
            0.019,
            20,
        )
        binding(m, [side * 0.19, 0.685, 0.17], Y, 0.020, 0.065)
    m.case([0, 0.386, 0.175], [0.09, 0.08, 0.15], "leather")
    m.case([0, 0.39, 0.258], [0.037, 0.15, 0.196], "ebony", 0.010)
    # Eight sounding strings in the demonstration sit among thirteen
    # sympathetic strings. Each trained thumb lever reaches only its own bank.
    played = {course: lane for lane, course in enumerate([0, 1, 4, 7, 10, 13, 16, 19])}
    for i in range(21):
        side = (-1) ** i
        j = i // 2
        yy = 0.69 + i * 0.038
        end = [side * 0.023, yy, -0.053 - (yy - 0.7) * 0.06]
        peak = [side * 0.020, 0.34 + j * 0.009, 0.20 + j * 0.0138]
        binding(m, [0, yy, -0.052 - (yy - 0.7) * 0.06], Y, 0.031, 0.016, "leather")
        if i in played:
            lane = played[i]
            wire(asset, peak, end, [lane], radius=0.0021, draw=side * X)
            tip = V(peak) * 0.77 + V(end) * 0.23
            root = V(
                [
                    side * 0.19,
                    tip[1] - 0.036,
                    0.125 + (tip[1] - 0.036 - 0.17) * 0.055 / 0.6,
                ]
            )
            plectrum(asset, root, tip, [lane], Z)
        else:
            m.rod(peak, end, 0.0018, "silver", n=7)
        m.rod([side * 0.021, 0.108, 0.12], peak, 0.0019, "silver", n=6)
    m.ring([0, 0.10, 0.12], Z, 0.031, 0.007, "iron")
    for i in range(6):
        m.ring([-0.19, 0.70 + i * 0.013, 0.179], Y, 0.022, 0.003, "brass")


def dulcimer(asset):
    m = asset.fixed
    soundbox(
        m,
        [
            (0, 0.05),
            (0.08, 0.18),
            (0.26, 0.26),
            (0.42, 0.23),
            (0.55, 0.12),
            (0.68, 0.10),
            (0.80, 0.155),
            (0.95, 0.17),
            (1.10, 0.09),
            (1.16, 0.05),
        ],
        0.115,
        "rose",
    )
    fingerboard(m, 0.12, 1.18, 0.088)
    for i in range(14):
        y = 0.33 + (1 - 0.92**i) * 1.12
        m.rod([-0.045, y, 0.080], [0.045, y, 0.080], 0.003, "silver", n=8)
    for x in [-0.134, 0.134]:
        a = np.linspace(0, TAU, 51)
        pts = np.c_[
            x + 0.042 * np.sin(a) ** 3,
            0.33
            + 0.003
            * (13 * np.cos(a) - 5 * np.cos(2 * a) - 2 * np.cos(3 * a) - np.cos(4 * a)),
            0 * a + 0.003,
        ]
        m.cap(np.vstack([pts, pts[0]]), Z, "ebony")
        m.tube(pts, 0.003, "brass", 7)
    m.case([0, 1.21, 0.025], [0.13, 0.15, 0.09], "walnut")
    for i, x in enumerate([-0.033, -0.011, 0.016, 0.028]):
        wire(
            asset,
            [x, 0.14, 0.102],
            [x, 1.18, 0.099],
            range(8) if i < 2 else range(i - 2, 8, 2),
        )
        peg(m, [0.036 * (-1) ** i, 1.16 + i * 0.036, 0.022], (-1) ** i)
    # Forked tail and swept wing of the valley maker's swallow.
    motif = V([0.105, 0.85, 0.003])
    outline = [
        (-0.049, 0.025),
        (-0.018, 0.016),
        (0.008, 0.005),
        (0.046, 0.034),
        (0.026, 0.003),
        (0.047, -0.001),
        (0.013, -0.009),
        (-0.020, -0.025),
        (-0.011, -0.006),
        (-0.038, -0.012),
        (-0.049, 0.025),
    ]
    m.tube([motif + x * X + y * Y for x, y in outline], 0.0025, "copper", 8)
    plectrum(asset, [-0.081, 0.187, 0.034], [-0.015, 0.21, 0.102], range(8))


def gurdy(asset):
    m = asset.fixed
    soundbox(
        m,
        [
            (0.02, 0.065),
            (0.13, 0.235),
            (0.32, 0.289),
            (0.49, 0.238),
            (0.65, 0.17),
            (0.79, 0.15),
            (0.89, 0.076),
        ],
        0.19,
        "rose",
    )
    m.case([0, 0.61, 0.073], [0.23, 0.51, 0.125], "maple")
    m.case([0, 0.62, 0.143], [0.245, 0.47, 0.021], "rose")
    m.case([0, 0.91, 0.032], [0.15, 0.18, 0.092], "walnut")
    for i in range(4):
        peg(m, [(-1) ** i * 0.06, 0.86 + i * 0.042, 0.02], (-1) ** i)
    for i in range(9):
        p = asset.part("Sliding tangent " + str(i), [-0.1, 0.405 + i * 0.048, 0.078])
        p.case([-0.053, 0, 0], [0.139, 0.033, 0.039], "ivory")
        asset.drive(p, "press", X, 0.025, [i % 8])
    # Wheel stands across the strings. Its axle runs along the length to
    # the crank below the tail, with a curved partial guard above the wheel.
    wheel = asset.part("Rosined wheel and crank", [0, 0.278, 0.042])
    wheel.turn(
        O,
        Y,
        [(-0.019, 0.110), (-0.014, 0.122), (0.014, 0.122), (0.019, 0.110)],
        "maple",
    )
    for i in range(6):
        a = TAU * i / 6
        wheel.rod(O, [0.105 * np.cos(a), 0, 0.105 * np.sin(a)], 0.010, "brass")
    wheel.rod(O, [0, -0.31, 0], 0.012, "iron")
    wheel.rod([0, -0.31, 0], [0.083, -0.31, 0], 0.013, "brass")
    wheel.rod([0.083, -0.31, 0], [0.083, -0.37, 0], 0.019, "ebony")
    asset.drive(wheel, "spin", Y, 1.0, rate=4.8)
    for x in [-0.058, -0.024, 0.03, 0.068]:
        m.rod([x, 0.12, 0.151], [x, 0.38, 0.151], 0.0024, "silver", n=7)
    for j in [-1, 1]:
        m.rosette([j * 0.172, 0.246, 0.006], Z, 0.046, 7)
    angles = np.linspace(-0.76, 0.76, 33)
    for yy in [0.248, 0.311]:
        m.tube(
            [[0.139 * np.sin(a), yy, 0.045 + 0.139 * np.cos(a)] for a in angles],
            0.006,
            "brass",
        )
    for x in [-0.046, 0, 0.046]:
        z = 0.045 + np.sqrt(0.139**2 - x * x)
        m.tube(
            [
                [x, 0.25, z],
                [x - 0.009, 0.27, z + 0.004],
                [x + 0.006, 0.295, z + 0.004],
                [x, 0.310, z],
            ],
            0.003,
            "copper",
            8,
        )
    m.staples([0.104, 0.64, 0.156], X * 0.015, Y * 0.026)

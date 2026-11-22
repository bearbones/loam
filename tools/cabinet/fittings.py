"""Shared joinery, tuning hardware and sound-generating mechanisms."""

import numpy as np
from scipy.interpolate import PchipInterpolator

from .mesh import TAU, O, V, X, Y, Z, unit
from .panels import panel


def rows_body(m, c, profile, mat, sections=54):
    """Oval longitudinal sections. Profile entries are height, half width and depth."""
    c = V(c)
    a = np.linspace(0, TAU, sections + 1)
    rows = [
        c + h * Y + np.cos(a)[:, None] * w * X - np.sin(a)[:, None] * d * Z
        for h, w, d in profile
    ]
    m.surface(rows, mat)
    m.cap(rows[0], -Y, mat)
    m.cap(rows[-1], Y, mat)


def soundbox(m, profile, depth, wood="walnut", face="spruce", holes=(), lute=False):
    h, w = np.array(profile).T
    y = np.linspace(h[0], h[-1], 51)
    radius = PchipInterpolator(h, w)(y)
    outline = np.array(
        [[r, yy, 0] for yy, r in zip(y, radius)]
        + [[-r, yy, 0] for yy, r in zip(y[::-1], radius[::-1])]
    )
    outline = np.vstack([outline, outline[0]])
    centre = Y * (h[0] + h[-1]) * 0.5

    def rim(scale, z):
        return centre + (outline - centre) * scale + z * Z

    if lute:
        # Alternate sawn staves meet at real seams on an elliptical bowl.
        for i in range(13):
            angles = np.linspace(i * np.pi / 13, (i + 1) * np.pi / 13, 6)
            grid = np.stack(
                [
                    np.c_[
                        r * np.cos(angles),
                        np.full_like(angles, yy),
                        -0.008 - depth * (r / max(radius)) ** 0.78 * np.sin(angles),
                    ]
                    for yy, r in zip(y, radius)
                ]
            )
            m.surface(grid, "walnut" if i % 2 == 0 else "rose", flip=True)
            if i:
                m.tube(grid[:, 0], 0.0017, "maple", 7)
        m.surface([rim(1, -0.008), rim(0.992, 0)], "ivory")
        for j, yy in [(0, y[0]), (-1, y[-1])]:
            rr = radius[j]
            a = np.linspace(0, np.pi, 49)
            edge = np.c_[
                rr * np.cos(a),
                np.full_like(a, yy),
                -0.008 - depth * (rr / max(radius)) ** 0.78 * np.sin(a),
            ]
            m.cap(np.vstack([edge, edge[0]]), Y if j < 0 else -Y, wood)
    else:
        for z0, z1, s0, s1, mat in [
            (-depth, -depth * 0.82, 0.44, 0.73, wood),
            (-depth * 0.82, -depth * 0.36, 0.73, 0.97, wood),
            (-depth * 0.36, -0.018, 0.97, 1.0, wood),
            (-0.018, -0.008, 1.0, 1.0, "ivory"),
            (-0.008, 0, 1.0, 0.992, face),
        ]:
            m.surface([rim(s0, z0), rim(s1, z1)], mat)
        back = rim(0.44, -depth)[:-1]
        half = len(back) // 2
        m.surface(np.stack([back[:half], back[half:][::-1]], axis=1), wood)
    face_rim = rim(0.992, 0)[:-1]
    if holes:
        xy, tri, rings = panel(face_rim[:, :2], holes)
        pts = np.c_[xy, np.zeros(len(xy))]
        m.parts[face].append((pts, np.broadcast_to(Z, pts.shape), xy / 0.28, tri))
        for contour in rings[1:]:
            edge = np.c_[contour, np.zeros(len(contour))]
            edge = np.vstack([edge, edge[0]])
            m.surface([edge, edge - 0.006 * Z], "walnut")
        # A dark inner back is visible through the pierced soundboard.
        backing = rim(0.85, -depth * 0.35)[:-1]
        h = len(backing) // 2
        m.surface(
            np.stack([backing[:h], backing[h:][::-1]], axis=1), "ebony", flip=True
        )
    else:
        half = len(face_rim) // 2
        m.surface(
            np.stack([face_rim[:half], face_rim[half:][::-1]], axis=1), face, flip=True
        )
    m.tube(rim(0.958, 0.002), 0.0038, "bronze", 7)
    return outline


def peg(m, p, side=1):
    p = V(p)
    axis = X * side
    m.turn(
        p,
        axis,
        [(0, 0.012), (0.029, 0.015), (0.056, 0.010), (0.063, 0.017)],
        "brass",
        14,
    )
    m.ball(p + axis * 0.072, [0.019, 0.032, 0.017], "ebony", 16)


def binding(m, c, axis, r, width, mat="cord"):
    c = V(c)
    axis = unit(V(axis))
    m.turn(
        c,
        axis,
        [
            (-width / 2, r * 0.97),
            (-width * 0.42, r),
            (width * 0.42, r),
            (width / 2, r * 0.97),
            (width / 2, r * 0.92),
            (-width / 2, r * 0.92),
            (-width / 2, r * 0.97),
        ],
        mat,
        32,
        False,
    )
    for at in [-0.43, 0, 0.43]:
        m.ring(c + axis * width * at, axis, r, 0.0028, "bronze", 32)


def wire(asset, a, b, lanes, material="silver", radius=0.003, draw=X, travel=0.007):
    a, b = V(a), V(b)
    mid = (a + b) / 2
    for j, end in enumerate((a, b)):
        part = asset.part(f"Wire {len(asset.nodes) + 1} anchor", end)
        part.rod(O, mid - end, radius, material, n=7)
        direction = unit(mid - end)
        axis = unit(np.cross(direction, draw))
        asset.drive(
            part, "pluck", axis, travel / max(0.1, np.linalg.norm(mid - end)), lanes
        )


def hammer(asset, root, contact, lanes, skin="leather", radius=0.035, normal=Y):
    root, contact = V(root), V(contact)
    head = contact + radius * normal
    delta = head - root
    axis = unit(np.cross(delta, Y))
    m = asset.fixed
    m.turn(
        root,
        axis,
        [(-0.026, 0.026), (-0.016, 0.032), (0.018, 0.032), (0.027, 0.024)],
        "bronze",
        20,
    )
    part = asset.part(f"Beater {len(asset.nodes) + 1}", root)
    part.rod(O, delta, 0.009, "maple", 0.006)
    part.ball(delta, radius, skin, 22, pole=normal)
    asset.drive(part, "strike", axis, -0.38, lanes, rest=0.38)


def plectrum(asset, root, tip, lanes, clear=Z, blade_span=0.0):
    root, tip = V(root), V(tip)
    direction = unit(tip - root)
    axis = unit(np.cross(direction, clear))
    m = asset.fixed
    width = 0.006 if blade_span else 0.014
    m.turn(root, axis, [(-width, 0.012), (width, 0.012)], "bronze", 16)
    part = asset.part(f"Horn pick {len(asset.nodes) + 1}", root)
    part.rod(O, (tip - root) * 0.67, 0.0055, "bronze", 0.004, n=10)
    part.rod(
        (tip - root) * 0.64,
        tip - root,
        0.006 if blade_span else 0.009,
        "ivory",
        0.0018,
        n=9,
    )
    if blade_span:
        part.rod(
            tip - root - X * blade_span,
            tip - root + X * blade_span,
            0.0018,
            "ivory",
            n=10,
        )
    asset.drive(part, "pick", axis, -0.41, lanes, rest=0.41)


def bow(asset, centre, width=0.70):
    # The horsehair crosses the sounding string plane. A curved stick and
    # a screw-adjusted ebony frog travel together.
    c = V(centre)
    p = asset.part("Fitted bow and frog", c)
    p.tube(
        [
            [-width / 2, 0, 0.009],
            [-width * 0.33, 0.017, 0.058],
            [0, 0.028, 0.07],
            [width * 0.36, 0.025, 0.048],
            [width / 2, 0, 0.009],
        ],
        0.009,
        "rose",
    )
    for y in np.linspace(-0.006, 0.006, 4):
        p.rod([-width / 2, y, 0], [width / 2, y, 0], 0.002, "ivory", n=6)
    p.case([-width * 0.42, 0.004, 0.022], [0.09, 0.029, 0.044], "ebony", 0.009)
    p.rod([-width * 0.56, 0, 0.025], [-width * 0.43, 0, 0.025], 0.009, "silver")
    # The frog slides on this guide. A bolted return bracket on the side
    # of the soundbox carries both guide bearings through the full stroke.
    yoke = c + V([0, -0.043, 0.050])
    left = -width * 0.42 - 0.20
    right = -width * 0.42 + 0.17
    for end in [left, right]:
        cable(
            asset.fixed,
            [
                [-0.16, 0.32, -0.015],
                [-0.23, 0.30, 0.038],
                yoke + [end, -0.049, 0],
                yoke + [end, 0, 0],
            ],
            "bronze",
            0.0085,
        )
        asset.fixed.turn(
            yoke + X * end, X, [(-0.010, 0.016), (0.010, 0.016)], "bronze", 16
        )
    asset.fixed.rod(yoke + left * X, yoke + right * X, 0.006, "iron")
    p.rod([-width * 0.42, 0.004, 0.022], [-width * 0.42, -0.043, 0.050], 0.008, "brass")
    p.turn(
        [-width * 0.42, -0.043, 0.050],
        X,
        [(-0.030, 0.012), (0.030, 0.012)],
        "bronze",
        18,
    )
    asset.drive(p, "bow", X, 0.14)


def constellation(m, c, u, v, r, mat="brass", points=7):
    c, u, v = V(c), V(u), V(v)
    angle = np.linspace(0, TAU, points, endpoint=False)
    pp = [
        c + r * (0.72 + 0.22 * np.sin(i * 2.1)) * (u * np.cos(a) + v * np.sin(a))
        for i, a in enumerate(angle)
    ]
    for i in range(points):
        m.rod(pp[i], pp[(i + 2) % points], 0.0025, mat, n=6)
        m.ball(pp[i], 0.006, mat, 10)


def feet(m, xs, zs, height):
    for x in xs:
        for z in zs:
            m.turn(
                [x, 0, z],
                Y,
                [(0, 0.052), (0.012, 0.057), (0.026, 0.039), (height, 0.031)],
                "ebony",
                24,
            )


def lamp(m, c, axis, r=0.025, mat="amber"):
    c = V(c)
    axis = unit(V(axis))
    m.turn(c, axis, [(0, r * 1.32), (0.009, r * 1.32), (0.014, r)], "brass", 20)
    m.ball(c + axis * 0.014, r, mat, 20)


def shop_stamp(m, centre, u, v, serial):
    """A riveted crescent maker's plate with individually punched digits."""
    c, u, v = V(centre), V(u), V(v)
    n = np.cross(u, v)
    outline = [
        (-0.052, -0.013),
        (-0.046, -0.018),
        (0.046, -0.018),
        (0.052, -0.012),
        (0.052, 0.011),
        (0.045, 0.018),
        (-0.046, 0.018),
        (-0.052, 0.012),
        (-0.052, -0.013),
    ]
    rim = np.array([c + x * u + y * v for x, y in outline])
    m.surface([rim, rim + n * 0.0025], "bronze")
    m.cap(rim + n * 0.0025, n, "brass")
    front = c + n * 0.0033
    for side in [-1, 1]:
        m.screw(front + side * 0.043 * u, n, 0.0038)
    arc = np.linspace(0.53, TAU - 0.53, 25)
    m.tube(
        front
        - 0.022 * u
        + (0.009 * np.cos(arc)[:, None] * u + 0.009 * np.sin(arc)[:, None] * v),
        0.0014,
        "ebony",
        6,
    )
    endings = [
        ((0, 2), (1, 2)),
        ((1, 2), (1, 1)),
        ((1, 1), (1, 0)),
        ((1, 0), (0, 0)),
        ((0, 0), (0, 1)),
        ((0, 1), (0, 2)),
        ((0, 1), (1, 1)),
    ]
    strokes = [
        "012345",
        "12",
        "01643",
        "01623",
        "5612",
        "05623",
        "054623",
        "012",
        "0123456",
        "015623",
    ]
    for i, digit in enumerate(f"{serial:02d}"):
        base = front + (i * 0.015 - 0.004) * u - 0.009 * v
        for index in strokes[int(digit)]:
            a, b = endings[int(index)]
            m.rod(
                base + 0.008 * (u * a[0] + v * a[1]),
                base + 0.008 * (u * b[0] + v * b[1]),
                0.0011,
                "ebony",
                n=6,
            )


def cable(m, points, mat="black", r=0.012):

    pts = V(points)
    # Round each actual bend. A spline through the terminals can turn back
    # inside a short mounting foot before entering the bearing.
    curve = [pts[0]]
    for i in range(1, len(pts) - 1):
        a, b, c = pts[i - 1 : i + 2]
        incoming = unit(a - b)
        outgoing = unit(c - b)
        trim = 0.35 * min(np.linalg.norm(a - b), np.linalg.norm(c - b))
        left = b + incoming * trim
        right = b + outgoing * trim
        for t in np.linspace(0, 1, 9):
            curve.append((1 - t) ** 2 * left + 2 * t * (1 - t) * b + t * t * right)
    curve.append(pts[-1])
    m.tube(curve, r, mat, 10)

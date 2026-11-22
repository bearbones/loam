"""The walnut workbench and green-lined alcove used for the instrument portraits."""

from .fittings import constellation
from .mesh import Asset, X, Y, Z


def build(path):
    stage = Asset("workbench")
    m = stage.fixed
    # Continuous bench with breadboard ends, a bound green cloth and ebony bead.
    m.case([0, -0.090, 0], [4.18, 0.156, 2.07], "walnut", 0.08)
    m.case([0, -0.021, 0], [4.04, 0.025, 1.97], "leather", 0.07)
    m.case([0, -0.008, 0], [3.96, 0.015, 1.9], "baize", 0.06)
    for z in [-0.926, 0.926]:
        for i in [-1, 1]:
            m.rod(
                [-1.91, -0.0005, z + i * 0.009],
                [1.91, -0.0005, z + i * 0.009],
                0.0023,
                "bronze",
                n=8,
            )
    for x in [-1.82, 1.82]:
        m.case([x, -0.081, 0], [0.035, 0.14, 2.02], "rose", 0.012)
        for z in [-0.77, 0.77]:
            m.turn(
                [x, -0.90, z],
                Y,
                [
                    (0, 0.081),
                    (0.08, 0.07),
                    (0.22, 0.038),
                    (0.27, 0.062),
                    (0.32, 0.058),
                    (0.64, 0.048),
                    (0.70, 0.082),
                    (0.76, 0.08),
                ],
                "walnut",
            )
    m.case([0, -0.91, 0], [12, 0.08, 11], "ebony")
    for i in range(33):
        x = (i - 16) * 0.48
        m.case([x, 1.12, -2.08], [0.478, 4.2, 0.12], "panel", 0.008)
        m.case([x - 0.216, 1.10, -2.003], [0.018, 4.1, 0.035], "moulding", 0.008)
    for y in [-0.34, 1.47, 2.68]:
        m.case([0, y, -1.961], [16, 0.050, 0.060], "moulding", 0.018)
        m.case([0, y + 0.010, -1.925], [16, 0.005, 0.010], "aged trim", 0.002)
    for x in [-1.85, 1.85]:
        m.tube(
            [
                [x - 0.29, 1.04, -1.971],
                [x - 0.29, 1.73, -1.971],
                [x - 0.21, 1.89, -1.971],
                [x, 1.99, -1.971],
                [x + 0.21, 1.89, -1.971],
                [x + 0.29, 1.73, -1.971],
                [x + 0.29, 1.04, -1.971],
            ],
            0.012,
            "aged trim",
        )
        m.turn(
            [x, 1.47, -1.95], Z, [(0, 0.075), (0.025, 0.088), (0.05, 0.056)], "brass"
        )
        m.ball([x, 1.47, -1.857], [0.037, 0.070, 0.035], "amber", 22)
    # Tools live along the edges of the work area.
    m.case([1.59, 0.015, -0.41], [0.22, 0.026, 0.78], "maple", 0.008)
    for i in range(24):
        z = -0.765 + i * 0.030
        m.rod(
            [1.49, 0.03, z],
            [1.54 + (0.039 if i % 5 == 0 else 0), 0.03, z],
            0.0024,
            "ebony",
            n=6,
        )
    for i in range(3):
        z = -0.71 + i * 0.061
        m.rod([-1.78, 0.026, z], [-1.48, 0.026, z + 0.054], 0.018, "rose", 0.013)
        m.rod(
            [-1.48, 0.026, z + 0.054], [-1.27, 0.026, z + 0.10], 0.006, "iron", 0.0015
        )
    for x in [-1.66, 1.69]:
        constellation(m, [x, 0.001, 0.68], X, Z, 0.064, "brass", 6)
    stage.export(path, [], 0.0)

"""Bake score-time motion into ordinary portable glTF animation channels."""

import numpy as np


def ease(x):
    x = np.clip(x, 0, 1)
    return x * x * (3 - 2 * x)


def evaluate(track, events, duration, pivot):
    selected = [
        e for e in events if track["lanes"] is None or e["lane"] in track["lanes"]
    ]
    # Include the score instants as well as video frames so a tool hits on time.
    t = np.unique(
        np.r_[np.arange(0, duration, 1 / 60), duration, [e["t"] for e in selected]]
    )
    kind = track["kind"]
    axis = track["axis"]
    amount = track["extent"]
    wave = np.zeros_like(t)
    if kind == "belt":
        route = track["route"]
        distance = np.r_[0, np.cumsum(np.linalg.norm(np.diff(route, axis=0), axis=1))]
        position = np.mod(t * track["rate"], distance[-1])
        return (
            t,
            np.column_stack([np.interp(position, distance, r) for r in route.T]),
            "translation",
        )
    if kind == "spin":
        wave = t * track["rate"]
    elif kind in ("bellows", "breathe"):
        wave = (1 - np.cos(t * track["rate"])) * 0.5
    elif kind in ("slide", "selector"):
        prev = 0.0
        for e in selected:
            goal = e["lane"] / track["rate"]
            wave += (goal - prev) * ease((t - e["t"] + 0.13) / 0.13)
            prev = goal
    else:
        for i, e in enumerate(selected):
            dt = t - e["t"]
            age = np.maximum(dt, 0)
            vol = e["velocity"]
            if kind == "strike":
                # The hammer is authored tangent to its target at zero angle.
                q = ease((dt + 0.095) / 0.095) * (1 - ease(dt / 0.105))
                wave = np.maximum(wave, q)
            elif kind == "pick":
                # Reach the wire before the attack, then let the tapered tip
                # roll free quickly while the wire starts its own decay.
                q = ease((dt + 0.14) / 0.115) * (1 - ease(dt / 0.075))
                wave = np.maximum(wave, q)
            elif kind == "key" or kind == "press":
                q = ease((dt + 0.07) / 0.07) * (
                    1 - ease((dt - e["duration"] * 0.75) / 0.085)
                )
                wave = np.maximum(wave, q)
            elif kind == "pluck":
                on = ease((dt + 0.063) / 0.063) * (dt < 0)
                ring = np.cos(age * 51) * np.exp(-age * 12) * (dt >= 0)
                wave += (on + ring) * vol
            elif kind in ("ring", "flex"):
                wave += np.sin(age * 43) * np.exp(-age * 9) * vol
            elif kind == "bow":
                end = e["duration"]
                wave += (
                    (-1) ** i
                    * ease((dt + 0.06) / max(0.1, end))
                    * (1 - ease((dt - end) / 0.19))
                )
            elif kind == "meter":
                wave = np.maximum(
                    wave, ease((dt + 0.04) / 0.04) * np.exp(-age * 4) * vol
                )
            else:
                raise ValueError(kind)
    value = track["rest"] + amount * wave
    if kind in ("slide", "press", "bow", "breathe"):
        channel = "translation"
        output = pivot + value[:, None] * axis
    elif kind == "flex":
        channel = "weights"
        output = value[:, None]
    elif kind == "bellows":
        channel = "scale"
        output = 1 + value[:, None] * axis
    else:
        channel = "rotation"
        output = np.c_[np.sin(value / 2)[:, None] * axis, np.cos(value / 2)]
    # Keep the ends of each constant run, including both ends of a rest.
    varies = np.any(np.abs(np.diff(output, axis=0)) > 1e-8, axis=1)
    keep = np.r_[True, varies] | np.r_[varies, True]
    return t[keep], output[keep], channel

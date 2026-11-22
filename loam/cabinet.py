"""The Wayfarer's Cabinet. Sound these original instruments at Loam's sample rate."""

from dataclasses import dataclass

import numpy as np
from scipy.signal import butter, iirpeak, lfilter, sosfilt

from . import SR, analog, hz, membrane, modal, strings, winds


@dataclass(frozen=True)
class Instrument:
    id: str
    title: str
    family: str
    history: str
    pitches: tuple
    bpm: int
    phrase: str


# A number is a playing course or articulation. '+' sounds a chord, '-' a rest.
# Durations follow '/' in beats. The phrases were written for these instruments.
def _entry(key, title, family, history, pitches, bpm, phrase):
    return Instrument(key, title, family, history, tuple(pitches), bpm, phrase)


INSTRUMENTS = {
    v.id: v
    for v in (
        _entry(
            "oud",
            "Mothwing Oud",
            "Short-necked lute",
            "A moth rosette guards the spruce face. A new dark rib interrupts the old bowl.",
            [48, 50, 51, 55, 57, 58, 60, 62],
            101,
            "0/.5 3/.5 4/.75 3/.25 2/.5 1/.5 0/1 3/.5 5/.5 7/.5 6/.5 4/.75 3/.25 1/.5 0/1.5",
        ),
        _entry(
            "nyckelharpa",
            "Courier’s Nyckelharpa",
            "Swedish keyed fiddle",
            "Waxed maple keys run under a split rail secured with two brass staples.",
            [55, 57, 59, 60, 62, 64, 66, 67],
            108,
            "0/1 2/.5 3/.5 4/1 2/.5 1/.5 0/.5 2/.5 4/.5 6/.5 7/1 4/1 2/.5 0/1.5",
        ),
        _entry(
            "koto",
            "Rain-Chart Koto",
            "Japanese bridged zither",
            "Thirteen ivory-coloured bridges cast long shadows across a rain-marked board.",
            [50, 51, 55, 57, 58, 62, 63, 67, 69, 70, 74, 75, 79],
            92,
            "0+4/1 2/.5 4/.5 5/1 7/.5 9/.5 12/.5 10/.5 8/1 6/.5 5/.5 2+7/1 0/1.5",
        ),
        _entry(
            "kora",
            "Ferryman’s Kora",
            "West African bridge harp",
            "The hide carries two lines of old tacks beside the ferryman’s brass tally rings.",
            [48, 50, 52, 55, 57, 60, 62, 64],
            115,
            "0+4/.5 2/.5 5/.5 1/.5 3+6/.5 2/.5 7/.5 4/.5 0+5/.5 3/.5 6/.5 1/.5 2+7/1 4/.5 0/1.5",
        ),
        _entry(
            "dulcimer",
            "Heather Mountain Dulcimer",
            "Appalachian fretted zither",
            "A copper swallow and two heart-shaped ports flank a polished melody rail.",
            [50, 52, 54, 55, 57, 59, 60, 62],
            104,
            "0/1 2/.5 3/.5 4/1 4/.5 2/.5 3/.75 2/.25 1/.5 0/.5 4/.5 6/.5 7/1 0/1",
        ),
        _entry(
            "shakuhachi",
            "Root Lantern",
            "Japanese end-blown flute",
            "A split above the root end has been lashed shut beneath a small moon charm.",
            [62, 65, 67, 69, 72, 74],
            76,
            "0/1.5 -/.5 1/.5 2/1.5 3/1 2/.5 1/.5 -/.5 4/1 3/.5 0/1.5",
        ),
        _entry(
            "siku",
            "Cloud Stair Siku",
            "Andean paired panpipes",
            "Woven red bindings hold mismatched replacement cane in two answering ranks.",
            [60, 62, 64, 65, 67, 69, 71, 72],
            118,
            "0/.5 1/.5 2/.5 3/.5 4/.75 5/.25 6/.5 7/.5 5/.5 6/.5 4/.5 3/.5 2/1 1/.5 0/1.5",
        ),
        _entry(
            "sheng",
            "Reed Citadel",
            "Chinese free-reed mouth organ",
            "A dark windchest carries a little skyline of reed towers and gilt pipe shoes.",
            [55, 58, 60, 62, 65, 67, 70, 72],
            88,
            "0+3/1 1+4/1 2+5/1.5 3/.5 3+6/1 4+7/1 2+5/1 0+3/1.5",
        ),
        _entry(
            "uilleann",
            "Night-Watch Pipes",
            "Irish bellows-blown pipes",
            "The oxblood bag has a stitched patch. Three collared drones share its stock.",
            [62, 64, 66, 67, 69, 71, 73, 74],
            116,
            "0/.75 1/.25 2/.5 4/.5 3/.5 2/.5 1/.5 0/.5 4/.75 5/.25 6/.5 7/.5 4/1 2/.5 0/1.5",
        ),
        _entry(
            "serpent",
            "Vesper Serpent",
            "European bass wind",
            "Copper splints follow the leathered bends. The bell bears a repaired lip.",
            [38, 41, 43, 45, 46, 48, 50],
            82,
            "0/1.5 2/.5 3/1 1/1 4/.5 3/.5 2/1 5/.5 6/.5 0/2",
        ),
        _entry(
            "balafon",
            "Orchard Balafon",
            "West African gourd-resonated keys",
            "Individually tied slats sit over wax-rimmed buzzing gourds.",
            [53, 55, 57, 60, 62, 65, 67, 69],
            122,
            "0/.5 3/.5 2/.25 4/.25 1/.5 5/.5 2/.5 6/.5 3/.5 0+4/.5 7/.5 5/.25 4/.25 2/.5 3+6/1 1/.5 0/1.5",
        ),
        _entry(
            "mbira",
            "Bottle-Star Mbira",
            "Southern African lamellophone",
            "Thumb-polished tongues share the board with a row of loose bottle-cap buzzers.",
            [48, 55, 60, 62, 64, 67, 69, 72],
            110,
            "0+4/.5 2/.5 5/.5 1/.5 3+6/.5 2/.5 7/.5 5/.5 0+3/.5 4/.5 6/.5 2/.5 1+5/1 0+4/1",
        ),
        _entry(
            "tabla",
            "Caravan Tabla",
            "North Indian drum pair",
            "Replacement tuning blocks sit under stretched straps. Each skin carries a dark loading patch.",
            [38, 44, 55, 60, 62, 65],
            112,
            "0/.5 3/.5 4/.25 4/.25 1/.5 2/.5 5/.5 0+3/.5 4/.5 1/.25 2/.25 4/.25 3/.25 0/.5 5/.5 3/.25 4/.25 2/.5 0+3/1",
        ),
        _entry(
            "kulintang",
            "Tide-Clock Kulintang",
            "Southern Philippine gong row",
            "Eight bossed gongs hang on a cord bed. Their patina breaks at the worn striking spots.",
            [55, 57, 60, 62, 63, 65, 67, 70],
            119,
            "0/.5 2/.5 1/.5 4/.5 3/.25 5/.25 2/.5 6/.5 4/.5 7/.75 5/.25 4/.5 2/.5 3+6/.5 1/.5 0/1.5",
        ),
        _entry(
            "udu",
            "River-Mouth Udu",
            "Nigerian clay vessel drum",
            "A pale slip spiral winds past the side port and a laced repair at the shoulder.",
            [40, 47, 55, 59, 64],
            99,
            "0/1 2/.5 3/.5 1/.75 4/.25 2/.5 0/.5 3/.25 2/.25 4/.5 1/1 2/.5 0/1.5",
        ),
        _entry(
            "hardanger",
            "Frostvein Fiddle",
            "Norwegian Hardanger fiddle",
            "Four understrings disappear beneath the board. A leaf scroll rises from its pegbox.",
            [57, 59, 61, 62, 64, 66, 68, 69],
            102,
            "0+4/1 2/.5 3/.5 4/1 6/.5 7/.5 5/.75 4/.25 3/.5 2/.5 1/1 0+4/1.5",
        ),
        _entry(
            "gurdy",
            "Candlewheel Gurdy",
            "European wheel fiddle",
            "A patched wheel cover leaves the rosined rim and eccentric crank visible.",
            [55, 57, 58, 60, 62, 63, 65, 67],
            113,
            "0/1 1/.5 2/.5 4/.5 3/.5 2/1 5/.5 4/.5 7/1 4/.5 2/.5 1/.5 0/1.5",
        ),
        _entry(
            "armonica",
            "Tideglass Armonica",
            "Spindle-mounted glass bowls",
            "Sea-green nested rims share a brass axle with a chipped flywheel.",
            [60, 62, 63, 65, 67, 68, 70, 72],
            77,
            "0+4/1.5 2/.5 1+5/1 3+6/1.5 4/.5 7/1 2+5/1 0+4/1.5",
        ),
        _entry(
            "bandoneon",
            "Quayside Bandoneon",
            "South American tango concertina",
            "Worn button caps and copper corner guards flank a patched wine-red bellows.",
            [50, 53, 55, 57, 58, 60, 62, 65],
            108,
            "0+3/.75 -/.25 2/.5 3/.5 1+4/1 2/.5 0/.5 3+6/.75 5/.25 4/.5 2/.5 1+5/1 0+3/1.5",
        ),
        _entry(
            "handpan",
            "Eclipse Handpan",
            "Tuned steel shell",
            "Hammer scars surround seven blue-black tone fields and a bright central dome.",
            [50, 57, 58, 60, 62, 64, 65, 69],
            96,
            "0/1 2/.5 4/.5 1/.5 5/.5 3/1 7/.5 6/.5 4/.5 2/.5 3+5/1 0/1.5",
        ),
        _entry(
            "magnetar",
            "Magnetar Flux Organ",
            "Shipboard field synthesizer",
            "Verdigris creeps under three wound field coils. Their armatures still turn.",
            [38, 45, 50, 53, 57, 60, 62, 65],
            93,
            "0/1 1/.5 2/.5 3+5/1 2/1 4/.5 6/.5 5+7/1 3/1 0+2/1.5",
        ),
        _entry(
            "periapsis",
            "Periapsis Ribbon",
            "Navigation ribbon synthesizer",
            "A ceramic shuttle rides a polished copper ribbon between two calibration stops.",
            [48, 50, 54, 55, 59, 62, 66, 67],
            107,
            "0/1.5 2/.5 3/1 5/.5 7/.5 6/.75 4/.25 3/1 1/.5 0/1.5",
        ),
        _entry(
            "choir",
            "Vacuum Choir",
            "Valve-formant synthesizer",
            "Amber cathodes glow through smoked envelopes. One valve wears a replacement cage.",
            [53, 55, 56, 58, 60, 61, 63, 65],
            84,
            "0+4/1.5 2+5/1 3+6/1.5 4+7/1 5/.5 3/.5 1+4/1 0+3/1.5",
        ),
        _entry(
            "cryotape",
            "Cryotape Echoplex",
            "Coolant-fed tape synthesizer",
            "Spliced oxide tape crosses three heads beneath a frost-scarred coolant reservoir.",
            [45, 48, 50, 52, 55, 57, 60, 64],
            113,
            "0/.75 2/.25 4/.5 -/.5 5/1 3/.5 1/.5 0/.5 6/.5 7/.75 5/.25 3/1 0/1.5",
        ),
        _entry(
            "pulsar",
            "Pulsar Navigation Loom",
            "Optical pattern synthesizer",
            "Punched brass stars pass a reader lamp. A mended drive belt keeps the chart in time.",
            [43, 50, 55, 58, 60, 62, 65, 67],
            129,
            "0/.25 2/.25 1/.5 4/.25 3/.25 2/.5 5/.5 1/.25 6/.25 3/.5 7/.5 0+4/.5 2/.25 5/.25 6/.5 1/.5 3+7/1 0/1.5",
        ),
    )
}


def score(key):
    item = INSTRUMENTS[key]
    beat = 60 / item.bpm
    t = 0.55
    events = []
    for i, token in enumerate(item.phrase.split()):
        chord, length = token.split("/")
        span = beat * float(length)
        if chord != "-":
            for part in chord.split("+"):
                lane = int(part)
                events.append(
                    {
                        "t": round(t, 6),
                        "lane": lane,
                        "duration": round(span * 0.89, 6),
                        "velocity": round(
                            0.68 + 0.21 * (i % 4 == 0) + 0.09 * np.sin(i * 1.71) ** 2, 4
                        ),
                    }
                )
        t += span
    return events, float(np.ceil((t + 1.48) * 30) / 30)


def _envelope(t, duration, attack, release):
    return (1 - np.exp(-t / attack)) * np.exp(-np.maximum(t - duration, 0) / release)


def _bow(f, t, duration, bright, seed):
    rng = np.random.default_rng(seed)
    phase = 2 * np.pi * f * t + 0.13 * np.sin(2 * np.pi * 5.2 * t)
    out = sum(
        np.sin(k * phase + 0.08 * k * np.sin(18 * t)) / k**bright
        for k in range(1, min(28, int(15500 / f)))
    )
    scrape = sosfilt(
        butter(2, [900, 4700], fs=SR, btype="band", output="sos"),
        rng.normal(size=t.size),
    )
    return (out + 0.12 * scrape * np.exp(-t / 0.065)) * _envelope(
        t, duration, 0.035, 0.065
    )


def _voice(key, lane, duration, take):
    f = hz(INSTRUMENTS[key].pitches[lane])
    seed = (list(INSTRUMENTS).index(key) + 1) * 97 + lane * 5 + take
    rng = np.random.default_rng(seed)
    t = np.arange(round((duration + 0.8) * SR)) / SR
    ph = 2 * np.pi * f * t
    env = _envelope(t, duration, 0.021, 0.10)
    if key in ("oud", "dulcimer", "koto", "kora"):
        pick, decay, damp = {
            "oud": (0.21, 1.7, 0.34),
            "dulcimer": (0.16, 2.2, 0.22),
            "koto": (0.10, 2.8, 0.22),
            "kora": (0.32, 1.85, 0.40),
        }[key]

        def string(freq, offset):
            return strings.pluck(
                freq,
                2.1,
                t60=decay,
                damp=damp,
                pick=pick + 0.009 * take,
                seed=seed + offset,
            )

        out = string(f, 0)
        if key in ("oud", "dulcimer"):
            out += 0.57 * string(f * 1.0026, 13)
        if key == "dulcimer":
            out += 0.30 * string(hz(50), 21) + 0.22 * string(hz(57), 24)
        if key == "koto":
            length = len(out)
            times = np.arange(length) / SR
            shift = 1.6 * np.sin(19 * times) * (1 - np.exp(-times * 6))
            out = np.interp(np.arange(length) + shift, np.arange(length), out)
        return out
    if key in ("nyckelharpa", "hardanger", "gurdy"):
        out = _bow(
            f,
            t,
            duration,
            {"nyckelharpa": 1.08, "hardanger": 0.83, "gurdy": 0.93}[key],
            seed,
        )
        if key == "gurdy":
            out = (out + 0.35 * np.sin(2 * np.pi * hz(43) * t) * env) * (
                1 + 0.13 * np.sin(t * 2 * np.pi * 7)
            )
        else:
            for cents in [0, 7, 12] if key == "hardanger" else [0, 12]:
                b, a = iirpeak(hz(INSTRUMENTS[key].pitches[0] + cents) * 2, 35, SR)
                out += 1.8 * lfilter(b, a, out)
        return out
    if key in ("shakuhachi", "siku"):
        out = winds.flute(
            f,
            max(0.25, duration + 0.15),
            breath=0.17 if key == "shakuhachi" else 0.10,
            vib_amt=0.021 if key == "shakuhachi" else 0.004,
            attack_s=0.050,
            release_s=0.10,
            seed=seed,
        )
        return out
    if key in ("sheng", "uilleann", "bandoneon"):

        def reed(freq, phase):
            return sum(
                np.sin(2 * np.pi * freq * k * t + phase) / k**1.12 for k in range(1, 13)
            )

        if key == "uilleann":
            out = reed(f, 0.17) + 0.25 * reed(hz(50), 0.03) + 0.17 * reed(hz(38), 0.13)
        elif key == "sheng":
            out = 0.8 * reed(f, 0) + 0.30 * np.sin(ph * 3.001) + 0.20 * np.sin(ph * 5)
        else:
            out = reed(f, 0.05) + 0.77 * reed(f * 1.006, 0) + 0.22 * reed(0.5 * f, 0.3)
        return out * _envelope(t, duration, 0.043, 0.08)
    if key == "serpent":
        grow = 1 + 1.8 * (1 - np.exp(-t * 9))
        return (
            np.sin(ph + grow * np.sin(ph))
            + 0.48 * np.sin(ph * 2 + 0.11 * np.sin(25 * t))
        ) * _envelope(t, duration, 0.085, 0.13)
    if key in ("balafon", "mbira", "kulintang", "handpan"):
        table = {
            "balafon": modal.MARIMBA,
            "mbira": [
                (1, 1, 1),
                (2.94, 0.26, 0.40),
                (5.6, 0.31, 0.23),
                (8.9, 0.10, 0.14),
            ],
            "kulintang": [
                (1, 1, 1),
                (1.53, 0.38, 0.55),
                (2.19, 0.48, 0.72),
                (3.21, 0.21, 0.47),
                (4.52, 0.13, 0.33),
            ],
            "handpan": [
                (1, 1, 1),
                (2.002, 0.72, 0.69),
                (3.005, 0.62, 0.52),
                (4.93, 0.15, 0.25),
            ],
        }[key]
        out = modal.strike(
            f,
            2.5 if key == "kulintang" else 1.85,
            table,
            knock=0.045,
            detune=2,
            rng=rng,
        )
        if key in ("balafon", "mbira"):
            out += 0.12 * np.tanh(out * 8) * np.abs(out) ** 0.5
        return out
    if key in ("tabla", "udu"):
        if key == "tabla":
            out = membrane.fddrum(
                f,
                0.72,
                load=0.31 if lane > 1 else 0.08,
                strike=(0.18 + 0.09 * (lane % 3), 0.12),
                N=27,
            )
            tt = np.arange(len(out)) / SR
            return out / max(abs(out)) + 0.38 * np.sin(
                2 * np.pi * f * tt + 0.7 * np.sin(24 * tt)
            ) * np.exp(-tt * 8)
        return (
            np.sin(ph + 0.9 * np.exp(-t * 16)) * np.exp(-t * (7 + lane * 2))
            + 0.32 * np.sin(ph * 2.44) * np.exp(-t * 28)
            + 0.38 * rng.normal(size=t.size) * np.exp(-t * 105)
        )
    if key == "armonica":
        return modal.bow(
            f, duration + 0.40, modal.GLASS, bright=0.85, vib_hz=3.5, rng=rng
        )
    if key == "magnetar":
        return (
            np.sin(ph + (2.4 + 1.8 * np.sin(4 * t)) * np.sin(1.5 * ph))
            + 0.44 * np.sin(ph * 0.5)
        ) * env
    if key == "periapsis":
        sweep = ph + 0.21 * np.sin(23 * t) + 2.8 * (np.exp(-t * 18) - 1)
        return (
            np.tanh(
                1.6
                * (
                    np.sin(sweep)
                    + 0.58 * np.sin(2.005 * sweep)
                    + 0.28 * np.sin(3 * sweep)
                )
            )
            * env
        )
    if key == "choir":
        sweep = analog.saw(f, len(t) / SR) + 0.53 * analog.saw(f * 1.006, len(t) / SR)
        out = np.zeros_like(sweep)
        for formant, q, g in [
            (550 + lane * 28, 6, 2),
            (1180 - lane * 31, 9, 1.6),
            (2600, 12, 0.95),
        ]:
            b, a = iirpeak(formant, q, SR)
            out += g * lfilter(b, a, sweep)
        return out * env[: len(out)]
    if key == "cryotape":
        dry = np.cos(ph + 0.07 * np.sin(12 * t)) * np.exp(-t * 7) + 0.38 * np.sin(
            ph * 2.006
        ) * np.exp(-t * 13)
        out = dry.copy()
        for k in range(1, 4):
            delay = round(0.144 * k * SR)
            if delay < len(out):
                out[delay:] += dry[:-delay] * 0.49**k
        return out
    # The rotating perforation rows gate partials at different subdivisions.
    return (
        np.sin(ph + 0.78 * np.sin(2 * ph))
        * (0.36 + 0.64 * np.maximum(0, np.cos(2 * np.pi * 9 * t)) ** 3)
        + 0.32 * np.sin(3.01 * ph) * (1 + 0.6 * np.sin(2 * np.pi * 12 * t))
    ) * env


def note(key, lane, duration=0.55, velocity=0.8, take=0):
    """Render a mono voice (zero-based course, seconds, velocity 0–1, take 0 or 1)."""
    if (
        key not in INSTRUMENTS
        or not isinstance(lane, (int, np.integer))
        or not 0 <= lane < len(INSTRUMENTS[key].pitches)
    ):
        raise ValueError("unknown instrument or playing course")
    if not 0.04 <= duration <= 30 or not 0 <= velocity <= 1 or take not in (0, 1):
        raise ValueError("invalid duration, velocity or take")
    sound = np.asarray(_voice(key, lane, duration, take), dtype=np.float64)
    if take:
        # A second contact position colours the early body reflection on repeated notes.
        delay = 9 + (INSTRUMENTS[key].pitches[lane] % 13)
        sound[delay:] += 0.11 * sound[:-delay].copy()
    sound -= np.mean(sound)
    sound *= np.minimum(np.arange(len(sound)) / max(1, 0.0017 * SR), 1)
    sound *= np.minimum(np.arange(len(sound))[::-1] / max(1, 0.030 * SR), 1)
    return (sound * (velocity**1.35 / max(np.max(np.abs(sound)), 1e-10))).astype(
        np.float32
    )

"""Find recipes that sound like a WAV file: python3 -m soundgarden.match target.wav

The target is described with the same log-mel grid and scalar features as the
renders. Candidates come from the starter anchors and, if present, every
accepted recipe in a discovery journal. The closest few are refined with
Nelder-Mead in logit space. Distances are embedding distances, not a listening
test: a low number means "the closest this resonator can get", not "the same".
"""
import argparse
import io
import json
from pathlib import Path
import wave

import numpy as np
from scipy.optimize import minimize
from scipy.signal import resample_poly

from loam import SR
from .describe import analyze, describe, embed, f0_midi, from_logits, logits
from .synth import ANCHORS, measure, render, validate_vector, wav_bytes

MAX_SECONDS = 3.0
MAX_BYTES = 8 * 1024 * 1024
DEFAULT_JOURNAL = Path(__file__).resolve().parents[1] / "render/soundgarden/trials.jsonl"


def load_wav(data, seconds=MAX_SECONDS):
    """Mono float audio at Loam's rate from PCM WAV bytes, trimmed and peak-scaled to 0.5."""
    if len(data) > MAX_BYTES:
        raise ValueError("Sound files must be 8 MB or smaller.")
    try:
        with wave.open(io.BytesIO(data)) as file:
            channels, width, rate, frames = file.getnchannels(), file.getsampwidth(), file.getframerate(), file.getnframes()
            raw = file.readframes(min(frames, int(rate * 30)))
    except (wave.Error, EOFError) as error:
        raise ValueError(f"Not a PCM WAV file: {error}") from error
    if width not in (1, 2, 3, 4):
        raise ValueError("Use 8, 16, 24, or 32-bit PCM WAV audio.")
    if width == 3:
        b = np.frombuffer(raw, dtype=np.uint8).reshape(-1, 3)
        x = (b[:, 0].astype(np.int32) | (b[:, 1].astype(np.int32) << 8) | (b[:, 2].astype(np.int8).astype(np.int32) << 16)) / 2 ** 23
    elif width == 1:
        x = (np.frombuffer(raw, dtype=np.uint8).astype(float) - 128) / 128
    else:
        x = np.frombuffer(raw, dtype={2: "<i2", 4: "<i4"}[width]).astype(float) / 2 ** (8 * width - 1)
    if channels > 1:
        x = x.reshape(-1, channels).mean(axis=1)
    if not len(x) or not np.any(x):
        raise ValueError("The sound file is silent or empty.")
    if rate != SR:
        g = np.gcd(SR, rate)
        x = resample_poly(x, SR // g, rate // g)
    peak = np.max(np.abs(x))
    start = max(int(np.argmax(np.abs(x) > peak * .01)) - int(.005 * SR), 0)
    x = x[start:start + int(seconds * SR)]
    return (x / peak * .5).astype(np.float32)


def target_embedding(audio, midi=None):
    midi = f0_midi(audio) if midi is None else midi
    return midi, embed(measure(audio), describe(audio)["grid"])


def candidates(journal=DEFAULT_JOURNAL, target=None, shortlist=24):
    """Starter recipes plus journal recipes, the latter shortlisted by their stored C4 descriptors.

    The shortlist is a prefilter (mel bands are absolute, so a pitch change moves
    the grid); every shortlisted recipe is still rendered at the target pitch.
    """
    seen = {tuple(v) for _, v in ANCHORS}
    out = [list(v) for _, v in ANCHORS]
    scored = []
    path = Path(journal)
    if path.exists():
        with path.open() as stream:
            for line in stream:
                try:
                    record = json.loads(line)
                    if not record.get("accepted") or tuple(record["vector"]) in seen:
                        continue
                    vector = validate_vector(record["vector"]).tolist()
                    seen.add(tuple(record["vector"]))
                    if target is not None and "descriptor" in record:
                        scored.append((float(np.linalg.norm(embed(record["metrics"], record["descriptor"]["grid"]) - target)), vector))
                    else:
                        out.append(vector)
                except (ValueError, KeyError, TypeError):
                    continue
    scored.sort(key=lambda item: item[0])
    return out + [vector for _, vector in scored[:shortlist]]


def match(audio, journal=DEFAULT_JOURNAL, midi=None, keep=3, refine=3, evaluations=90):
    """Top recipes by embedding distance to the target, refined by Nelder-Mead."""
    midi, target = target_embedding(audio, midi)
    scored = []
    for vector in candidates(journal, target):
        scored.append((float(np.linalg.norm(analyze(vector, midi)[3] - target)), vector))
    scored.sort(key=lambda item: item[0])
    results = []
    for distance, vector in scored[:refine]:
        cost = lambda z: float(np.linalg.norm(analyze(from_logits(z), midi)[3] - target))
        best = minimize(cost, logits(vector), method="Nelder-Mead",
                        options={"maxfev": evaluations, "xatol": .02, "fatol": 1e-4, "initial_simplex": logits(vector) + np.vstack([np.zeros(10), np.eye(10) * .6])})
        refined = np.clip(from_logits(best.x), 0, 1).tolist()
        results.append({"vector": refined, "distance": float(best.fun), "start_distance": distance, "midi": midi})
    results.sort(key=lambda item: item["distance"])
    for i, item in enumerate(results[:keep]):
        item["metrics"] = measure(render(item["vector"], 60))
    return midi, results[:keep]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("target", type=Path, help="PCM WAV file (mono or stereo)")
    parser.add_argument("--journal", type=Path, default=DEFAULT_JOURNAL)
    parser.add_argument("--midi", type=int, help="Render pitch; default estimates it from the file")
    parser.add_argument("--keep", type=int, default=3)
    parser.add_argument("--out", type=Path, help="Write the best match as a WAV at the detected pitch")
    args = parser.parse_args()
    audio = load_wav(args.target.read_bytes())
    midi, results = match(audio, args.journal, args.midi, args.keep)
    print(json.dumps({"midi": midi, "matches": results}, indent=2))
    if args.out and results:
        args.out.write_bytes(wav_bytes(render(results[0]["vector"], midi)))
        print(f"Wrote {args.out}")


if __name__ == "__main__":
    main()

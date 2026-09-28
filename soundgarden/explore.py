"""Resumable offline discovery: python3 -m soundgarden.explore --minutes 90.

Checkpoints after each candidate; a partial final journal line is discarded on
resume. Only selected seeds get WAVs. No downloads, agents, or repo writes.

Each journal record carries the recipe, scalar metrics, and the log-mel
descriptor. Older journals without descriptors are migrated on resume by
re-rendering every recipe and checking that the recorded metrics reproduce,
which is a stronger compatibility proof than a source hash.
"""
import argparse
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import signal
import time

import numpy as np

from .describe import VERSION as DESCRIPTOR_VERSION, analyze, embed
from .field import plane
from .synth import SR, VERSION, render, wav_bytes

ROOT = Path(__file__).resolve().parents[1]
SEARCH_VERSION = "soundgarden-search/2"
SYNTHESIS_SOURCES = [Path(__file__).with_name("synth.py"), ROOT / "loam/__init__.py", ROOT / "loam/modal.py"]
METRIC_KEYS = ("peak", "rms", "centroid_hz", "high_fraction", "energy95_s", "crest")


def atomic_json(path, data):
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(data, indent=2, allow_nan=False) + "\n")
    temporary.replace(path)


def embedding(record):
    return embed(record["metrics"], record["descriptor"]["grid"])


def diverse(candidates, count):
    if len(candidates) <= count:
        return candidates[:]
    points = np.array([embedding(c) for c in candidates])
    # Start with the median representative, then farthest-point coverage.
    chosen = [int(np.argmin(np.linalg.norm(points - np.median(points, axis=0), axis=1)))]
    distance = np.full(len(points), np.inf)
    while len(chosen) < count:
        distance = np.minimum(distance, np.linalg.norm(points - points[chosen[-1]], axis=1))
        distance[chosen] = -1
        chosen.append(int(np.argmax(distance)))
    return [candidates[i] for i in chosen]


def restore(path):
    """Repair only an incomplete trailing write, never silently erase corruption."""
    if not path.exists():
        return []
    records = []
    good_bytes = 0
    with path.open("rb") as stream:
        for line in stream:
            if not line.endswith(b"\n"):
                break
            records.append(json.loads(line))
            good_bytes += len(line)
    with path.open("r+b") as stream:
        stream.truncate(good_bytes)
    return records


def migrate(records):
    """Fill in descriptors for older records, proving the synthesis still reproduces them."""
    changed = False
    for record in records:
        if record.get("descriptor", {}).get("version") == DESCRIPTOR_VERSION:
            continue
        _, metrics, descriptor, _ = analyze(record["vector"])
        recorded = np.array([record["metrics"][k] for k in METRIC_KEYS])
        current = np.array([metrics[k] for k in METRIC_KEYS])
        if not np.allclose(recorded, current, rtol=1e-5, atol=1e-9):
            raise ValueError(f"Trial {record['trial']} no longer renders as recorded. Choose a fresh --output.")
        record["descriptor"] = descriptor
        changed = True
    return changed


def rewrite(path, records):
    temporary = path.with_suffix(".tmp")
    with temporary.open("w") as stream:
        for record in records:
            stream.write(json.dumps(record, allow_nan=False) + "\n")
        stream.flush()
        os.fsync(stream.fileno())
    temporary.replace(path)


def publish(output, archive, keep, trials, seed):
    previous_audio = set()
    manifest = output / "seeds.json"
    if manifest.exists():
        previous = json.loads(manifest.read_text())
        previous_audio = {s['audio'] for s in previous['seeds']
                          if re.fullmatch(r'[0-9a-f]{12}\.wav', s.get('audio', ''))}
    seeds = []
    for candidate in diverse(archive, keep):
        recipe = dict(candidate)
        recipe["source"] = "Discovered"
        recipe["name"] = f"Specimen {candidate['trial'] + 1:03d}"
        recipe["id"] = hashlib.sha256(json.dumps(recipe["vector"]).encode()).hexdigest()[:12]
        audio = output / f"{recipe['id']}.wav"
        if not audio.exists():
            audio.write_bytes(wav_bytes(render(recipe["vector"])))
        recipe["audio"] = audio.name
        seeds.append(recipe)
    atomic_json(output / "seeds.json", {"version": VERSION, "seed": seed, "trials": trials,
                "provenance": json.loads((output / "run.json").read_text()),
                "updated": datetime.now(timezone.utc).isoformat(), "seeds": seeds})
    # Only retire files explicitly owned by the preceding published bank.
    # Every recipe remains in the journal; unrelated output files are untouched.
    for filename in previous_audio - {s['audio'] for s in seeds}:
        (output / filename).unlink(missing_ok=True)


def battery_low(minimum):
    for device in Path('/sys/class/power_supply').glob('*'):
        try:
            if (device / 'type').read_text().strip() == 'Battery' and (device / 'status').read_text().strip() == 'Discharging' and int((device / 'capacity').read_text()) <= minimum:
                return True
        except (OSError, ValueError):
            continue
    return False


def check_manifest(manifest, metadata, parser):
    """Fail closed on a different seed, NumPy, or synthesis; allow search-version migration."""
    if not manifest.exists():
        return
    previous = json.loads(manifest.read_text())
    same = {k: previous.get(k) == metadata[k] for k in ("seed", "numpy_version", "sample_rate", "version")}
    if not all(same.values()):
        parser.error("This checkpoint has another seed, synthesis version, sample rate, or NumPy version. Choose a fresh --output.")
    if "synthesis_sha256" in previous and previous["synthesis_sha256"] != metadata["synthesis_sha256"]:
        parser.error("This checkpoint was made with different synthesis code. Choose a fresh --output.")
    # Legacy manifests (implementation_sha256) and older search versions are
    # accepted only after migrate() proves every recorded trial still reproduces.


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--minutes", type=float, default=90, help="Wall-time budget for this invocation")
    parser.add_argument("--max-trials", type=int, default=100000, help="Total trials including resumed trials")
    parser.add_argument("--keep", type=int, default=12)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--pause-ms", type=float, default=0, help="Idle between candidates to reduce duty cycle")
    parser.add_argument("--battery-min", type=int, default=25, help="Stop when a discharging Linux battery reaches this percent (0 disables)")
    parser.add_argument("--output", type=Path, default=ROOT / "render/soundgarden")
    args = parser.parse_args()
    if not np.isfinite(args.minutes) or args.minutes <= 0 or args.max_trials < 1 or not 1 <= args.keep <= 64 or args.seed < 0 or not np.isfinite(args.pause_ms) or args.pause_ms < 0 or not 0 <= args.battery_min <= 100:
        parser.error("Use positive budgets, a nonnegative seed/pause, and keep 1–64 sounds.")
    output = args.output
    output.mkdir(parents=True, exist_ok=True)
    lock = (output / "run.lock").open("w")
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        parser.error("Another explorer is already using this output directory.")
    synthesis = hashlib.sha256(b''.join(path.read_bytes() for path in SYNTHESIS_SOURCES)).hexdigest()
    metadata = {"version": VERSION, "seed": args.seed, "synthesis_sha256": synthesis, "search_version": SEARCH_VERSION,
                "descriptor_version": DESCRIPTOR_VERSION, "numpy_version": np.__version__, "sample_rate": SR}
    manifest = output / "run.json"
    check_manifest(manifest, metadata, parser)
    journal = output / "trials.jsonl"
    records = restore(journal)
    try:
        if migrate(records):
            print(f"Migrated {len(records)} trials to descriptor {DESCRIPTOR_VERSION}.", flush=True)
            rewrite(journal, records)
    except ValueError as error:
        parser.error(str(error))
    atomic_json(manifest, metadata)
    archive = []
    for record in records:
        if record["accepted"]:
            archive = diverse(archive + [record], 64)
    done = len(records)
    stopped = False

    def stop(*_):
        nonlocal stopped
        stopped = True

    signal.signal(signal.SIGINT, stop)
    signal.signal(signal.SIGTERM, stop)
    deadline = time.time() + args.minutes * 60
    print(f"Resuming at {done} trials. Results: {output / 'seeds.json'}", flush=True)
    with journal.open("a", buffering=1) as stream:
        while done < args.max_trials and time.time() < deadline and not stopped:
            if args.battery_min and battery_low(args.battery_min):
                print('Battery reserve reached. Saving current discoveries.', flush=True)
                break
            rng = np.random.default_rng(np.random.SeedSequence([args.seed, done]))
            vector = rng.uniform(.025, .975, 10).tolist()
            audio, metrics, descriptor, _ = analyze(vector)
            accepted = bool(np.all(np.isfinite(audio)) and .015 < metrics["rms"] and metrics["peak"] <= .63)
            record = {"trial": done, "vector": vector, "metrics": metrics, "descriptor": descriptor, "accepted": accepted}
            if accepted:
                record["plane"] = plane(vector, rng, spread=1.0, perceptual=True)
            stream.write(json.dumps(record, allow_nan=False) + "\n")
            os.fsync(stream.fileno())
            if accepted:
                archive = diverse(archive + [record], 64)
            done += 1
            if done % 16 == 0:
                publish(output, archive, args.keep, done, args.seed)
                print(f"{done} trials; {len(archive)} archive members", flush=True)
            if args.pause_ms:
                # Short chunks make Ctrl+C responsive even with a long pause.
                pause_end = min(deadline, time.time() + args.pause_ms / 1000)
                while time.time() < pause_end and not stopped:
                    time.sleep(min(.1, max(0, pause_end - time.time())))
    publish(output, archive, args.keep, done, args.seed)
    print(f"Saved {min(args.keep, len(archive))} seeds after {done} trials. Safe to resume.", flush=True)


if __name__ == "__main__":
    main()

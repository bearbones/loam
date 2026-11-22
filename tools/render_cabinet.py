"""Film the cabinet on its score clock and assemble the portable release assets."""

import argparse
import json
import os
import shutil
import subprocess
import tempfile
import wave
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZIP_STORED, ZipFile

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "harness/assets/cabinet"
OUT = ROOT / "render/cabinet"
FPS = 30


def run(args, timeout=90, **kwargs):
    return subprocess.run(args, cwd=ROOT, check=True, timeout=timeout, **kwargs)


def capture(item, work, size, ssaa):
    key = item["id"]
    raw = work / (key + "-silent.mp4")
    frames = round(item["duration"] * FPS)
    with (work / (key + ".log")).open("w") as log:
        run(
            [
                str(ROOT / "tools/offscreen.sh"),
                "godot",
                "--path",
                "harness",
                "--",
                "--instrument=" + key,
                "--silent",
                "--size=" + size,
                f"--ssaa={ssaa}",
                f"--capture={raw}",
                f"--fps={FPS}",
                "--start=0",
                f"--seconds={frames / FPS}",
                "--preset=fast",
                "--crf=17",
            ],
            timeout=300,
            stdout=log,
            stderr=subprocess.STDOUT,
        )
    probe = run(
        [
            "ffmpeg",
            "-v",
            "error",
            "-i",
            raw,
            "-map",
            "0:v:0",
            "-c:v",
            "copy",
            "-f",
            "framecrc",
            "pipe:1",
        ],
        capture_output=True,
        text=True,
    )
    count = sum(line.startswith("0,") for line in probe.stdout.splitlines())
    if count != frames:
        raise ValueError(f"{key} lost frames during capture")
    audio = OUT / (key + ".wav")
    run(
        [
            "ffmpeg",
            "-v",
            "error",
            "-y",
            "-i",
            raw,
            "-i",
            audio,
            "-map",
            "0:v:0",
            "-map",
            "1:a:0",
            "-c:v",
            "copy",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-movflags",
            "+faststart",
            work / (key + ".mp4"),
        ]
    )
    portrait(item, work)
    print(f"{key}: {frames} frames", flush=True)


def portrait(item, work):
    output = work / (item["id"] + "-portrait.png")
    run(
        [
            str(ROOT / "tools/offscreen.sh"),
            "godot",
            "--path",
            "harness",
            "--",
            "--instrument=" + item["id"],
            "--clean",
            "--silent",
            "--size=960x540",
            "--ssaa=2",
            "--time=" + str(item["duration"] * 0.31),
        ],
        env=dict(os.environ, SHOT=str(output)),
        stdout=subprocess.DEVNULL,
    )
    if not output.is_file():
        raise RuntimeError("Missing portrait for " + item["id"])


def join(catalog, work):
    inputs = work / "video.ffconcat"
    inputs.write_text(
        "ffconcat version 1.0\n"
        + "".join(
            f"file '{i['id']}-silent.mp4'\nduration {round(i['duration'] * FPS) / FPS:.9f}\n"
            for i in catalog
        )
    )
    metadata = [";FFMETADATA1", "title=The Wayfarer’s Cabinet", "artist=Loam"]
    clock = 0
    with wave.open(str(work / "master.wav"), "wb") as combined:
        for item in catalog:
            frames = round(item["duration"] * FPS)
            with wave.open(str(OUT / (item["id"] + ".wav")), "rb") as source:
                if not clock:
                    combined.setparams(source.getparams())
                if (
                    source.getnframes() * FPS != frames * source.getframerate()
                    or source.getparams()[:3] != combined.getparams()[:3]
                ):
                    raise ValueError("Audio and video clocks differ for " + item["id"])
                combined.writeframesraw(source.readframes(source.getnframes()))
            metadata.extend(
                [
                    "[CHAPTER]",
                    f"TIMEBASE=1/{FPS}",
                    f"START={clock}",
                    f"END={clock + frames}",
                    "title=" + item["title"],
                ]
            )
            clock += frames
    meta = work / "chapters.ffmetadata"
    meta.write_text("\n".join(metadata) + "\n", encoding="utf-8")
    run(
        [
            "ffmpeg",
            "-v",
            "error",
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            inputs,
            "-i",
            work / "master.wav",
            "-f",
            "ffmetadata",
            "-i",
            meta,
            "-map",
            "0:v:0",
            "-map",
            "1:a:0",
            "-map_metadata",
            "2",
            "-map_chapters",
            "2",
            "-c:v",
            "copy",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-movflags",
            "+faststart",
            OUT / "wayfarers-cabinet.mp4",
        ],
        timeout=180,
    )


def font(name, size):
    try:
        return ImageFont.truetype(name, size)
    except OSError:
        return ImageFont.load_default()


def poster(catalog, work):
    tile_w, tile_h, gap, border = 506, 342, 12, 32
    sheet = Image.new(
        "RGB", (border * 2 + 5 * tile_w + 4 * gap, 156 + 5 * (tile_h + gap)), "#121d21"
    )
    draw = ImageDraw.Draw(sheet)
    title = font("DejaVuSerif.ttf", 57)
    face = font("DejaVuSerif.ttf", 23)
    small = font("DejaVuSans.ttf", 15)
    draw.text((border, 23), "The Wayfarer’s Cabinet", font=title, fill="#f2dfb7")
    draw.text(
        (border + 3, 100),
        "LOAM     /     TWENTY-FIVE INSTRUMENTS FROM THE CHAMBER",
        font=small,
        fill="#c39c69",
    )
    for i, item in enumerate(catalog):
        x = border + (i % 5) * (tile_w + gap)
        y = 138 + (i // 5) * (tile_h + gap)
        with Image.open(work / (item["id"] + "-portrait.png")) as still:
            sheet.paste(still.resize((tile_w, 285), Image.Resampling.LANCZOS), (x, y))
        draw.text((x + 3, y + 289), item["title"], font=face, fill="#f2dfb7")
        draw.text((x + 4, y + 319), item["family"], font=small, fill="#bdc8bd")
    sheet.save(OUT / "wayfarers-atlas.jpg", quality=94, subsampling=0)


def assemble(catalog, work):
    join(catalog, work)
    poster(catalog, work)
    with ZipFile(
        OUT / "wayfarer-models.zip", "w", ZIP_DEFLATED, compresslevel=5
    ) as models:
        for entry in catalog:
            key = entry["id"]
            models.write(ASSETS / (key + ".glb"), key + ".glb")
        models.write(ASSETS / "catalog.json", "catalog.json")
    with ZipFile(OUT / "wayfarer-solo-films.zip", "w", ZIP_STORED) as films:
        for i, entry in enumerate(catalog):
            key = entry["id"]
            films.write(work / (key + ".mp4"), f"{i + 1:02d}-{key}.mp4")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--size", default="1280x720")
    parser.add_argument("--ssaa", type=int, default=2)
    parser.add_argument("--jobs", type=int, default=1)
    parser.add_argument(
        "--instrument",
        action="append",
        metavar="ID",
        help="Render only the named solo (repeatable)",
    )
    parser.add_argument(
        "--work", type=Path, help="Keep intermediate clips in this directory"
    )
    parser.add_argument(
        "--assemble-only",
        action="store_true",
        help="Assemble a previously captured --work directory",
    )
    args = parser.parse_args()
    if args.assemble_only and not args.work:
        parser.error("--assemble-only requires --work")
    OUT.mkdir(parents=True, exist_ok=True)
    catalog = json.loads((ASSETS / "catalog.json").read_text())
    selected = catalog
    if args.instrument:
        if args.assemble_only:
            parser.error("--assemble-only assembles the entire catalog")
        requested = set(args.instrument)
        selected = [item for item in catalog if item["id"] in requested]
        missing = requested - {item["id"] for item in selected}
        if missing:
            parser.error("Unknown instruments: " + ", ".join(sorted(missing)))
    with tempfile.TemporaryDirectory() as temp:
        work = args.work.resolve() if args.work else Path(temp)
        work.mkdir(parents=True, exist_ok=True)
        if not args.assemble_only:
            with ThreadPoolExecutor(max_workers=args.jobs) as pool:
                list(
                    pool.map(
                        lambda item: capture(item, work, args.size, args.ssaa), selected
                    )
                )
        if args.instrument:
            dest = OUT / "solos"
            dest.mkdir(exist_ok=True)
            for item in selected:
                shutil.copyfile(
                    work / (item["id"] + ".mp4"), dest / (item["id"] + ".mp4")
                )
        else:
            assemble(catalog, work)


if __name__ == "__main__":
    main()

"""Build the gallery soundtracks, scores and portable multisampled SFZ instruments."""

import json
import subprocess
import sys
from io import BytesIO
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

import numpy as np
from scipy.io import wavfile
from scipy.signal import correlate

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from loam import SR, stereo
from loam.cabinet import INSTRUMENTS, note, score

ASSETS = ROOT / "harness/assets/cabinet"
OUT = ROOT / "render/cabinet"
SUSTAINED = {
    "nyckelharpa",
    "hardanger",
    "gurdy",
    "shakuhachi",
    "siku",
    "sheng",
    "uilleann",
    "serpent",
    "armonica",
    "bandoneon",
    "magnetar",
    "periapsis",
    "choir",
    "pulsar",
}


def store(archive, name, data):
    info = ZipInfo(name)
    info.compress_type = ZIP_DEFLATED
    archive.writestr(info, data)


def sustain_loop(sound):
    """Match a cycle in the held note; crossfade both loop and release exits."""
    start, search, width = round(0.45 * SR), round(0.87 * SR), round(0.027 * SR)
    template = sound[start - width : start]
    window = sound[search - width : search + round(0.055 * SR)]
    match = correlate(window, template, mode="valid", method="fft")
    end = search + int(np.argmax(match))
    fade = 0.5 - 0.5 * np.cos(np.linspace(0, np.pi, width))
    sound[end - width : end] = sound[end - width : end] * (1 - fade) + template * fade
    sound[end : end + width] = (
        sound[start : start + width] * (1 - fade) + sound[end : end + width] * fade
    )
    return f"loop_mode=loop_sustain loop_start={start} loop_end={end - 1}"


def build():
    ASSETS.mkdir(parents=True, exist_ok=True)
    OUT.mkdir(parents=True, exist_ok=True)
    catalog = []
    with ZipFile(OUT / "wayfarer-samplers.zip", "w") as archive:
        for key, item in INSTRUMENTS.items():
            events, length = score(key)
            audio = np.zeros((round(SR * length), 2))
            for i, e in enumerate(events):
                lane = e["lane"]
                start = round(e["t"] * SR)
                tone = note(key, lane, e["duration"], e["velocity"], i % 2)[
                    : len(audio) - start
                ]
                pan = 0.42 * (2 * lane / (len(item.pitches) - 1) - 1)
                audio[start : start + len(tone)] += stereo(tone, pan)
            # Short early reflections keep attacks local to the body.
            dry = audio.copy()
            for delay, level in [
                (0.031, 0.13),
                (0.049, 0.09),
                (0.083, 0.065),
                (0.127, 0.035),
            ]:
                n = round(delay * SR)
                audio[n:] += dry[:-n, ::-1] * level
            audio[-SR // 5 :] *= np.linspace(1, 0, SR // 5)[:, None]
            audio *= 0.85 / max(np.max(abs(audio)), 1e-8)
            wav = OUT / (key + ".wav")
            wavfile.write(wav, SR, np.int16(audio * 32767))
            subprocess.run(
                [
                    "ffmpeg",
                    "-loglevel",
                    "error",
                    "-y",
                    "-i",
                    str(wav),
                    "-c:a",
                    "libvorbis",
                    "-q:a",
                    "6",
                    str(ASSETS / (key + ".ogg")),
                ],
                check=True,
                timeout=30,
            )
            regions = []
            for lane, midi in enumerate(item.pitches):
                # Nearest sampled pitch between reference notes, extended by a
                # fourth at the ends. Drum and vessel regions retain their key.
                lo = (item.pitches[lane - 1] + midi) // 2 + 1 if lane else midi - 5
                hi = (
                    (item.pitches[lane + 1] + midi) // 2
                    if lane + 1 < len(item.pitches)
                    else midi + 5
                )
                if key in ("tabla", "udu"):
                    lo = hi = midi
                regions.append(
                    f"<group> lokey={lo} hikey={hi} pitch_keycenter={midi} seq_length=2 ampeg_release=0.24"
                )
                for take in range(2):
                    buf = BytesIO()
                    sound = note(key, lane, 1.2, 1.0, take)
                    mode = (
                        sustain_loop(sound)
                        if key in SUSTAINED
                        else "loop_mode=one_shot"
                    )
                    wavfile.write(buf, SR, np.int16(sound * 32000))
                    path = f"samples/{midi}-{take + 1}.wav"
                    store(archive, key + "/" + path, buf.getvalue())
                    regions.append(
                        f"<region> seq_position={take + 1} {mode} sample={path}"
                    )
            store(
                archive, key + "/" + key + ".sfz", ("\n".join(regions) + "\n").encode()
            )
            catalog.append(
                {
                    "id": key,
                    "title": item.title,
                    "family": item.family,
                    "history": item.history,
                    "pitches": item.pitches,
                    "bpm": item.bpm,
                    "events": events,
                    "duration": length,
                }
            )
            print(key, len(events), length, flush=True)
    (ASSETS / "catalog.json").write_text(
        json.dumps(catalog, ensure_ascii=False, indent=2) + "\n"
    )


if __name__ == "__main__":
    build()

#!/usr/bin/env bash
# Deterministic frame capture followed by matching master audio. Run from repo root.
set -euo pipefail
name=${1:-original}
frames="render/clockwork-review/${name}-frames"
extra=()
audio=render/chamber/chamber.wav
view=0
if [[ "$name" == expanded ]]; then extra+=(--expanded); audio=render/clockwork/chamber.wav; view=5; fi
if [[ "$name" == mallets ]]; then view=3; fi
godot --path harness -- "${extra[@]}" --capture="$(realpath -m "$frames")" --start=45.5 --seconds=6 --fps=30 --camera=manual --view="$view"
ffmpeg -hide_banner -loglevel error -y -framerate 30 -i "$frames/%05d.png" -ss 45.5 -i "$audio" -t 6 -c:v libx264 -crf 19 -pix_fmt yuv420p -c:a aac -b:a 192k "render/clockwork-review/${name}.mp4"
show "render/clockwork-review/${name}.mp4" "Clockwork ${name}: six seconds of score-driven motion"

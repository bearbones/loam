#!/usr/bin/env bash
# The Chamber as a film: the harness's --film mode (harness/film_director.gd,
# camera and lighting directed from the score's cues) captured over the whole
# piece and muxed with the master. Run from the repo root.
#
#   tools/render_film.sh [OUT.mp4]      env: FPS=30 RES=1920x1080 JOBS=3 START=0 LENGTH=<total_s>
#
# Every frame is a pure function of score time, so the capture is split into
# JOBS chunks rendered side by side and cut together frame-exact.
set -euo pipefail
out=${1:-render/film/the-chamber.mp4}
score=render/chamber/score.json
audio=render/chamber/chamber.wav
fps=${FPS:-30}; res=${RES:-1920x1080}; jobs=${JOBS:-3}; start=${START:-0}
total=$(python3 -c "import json;print(json.load(open('$score'))['total_s'])")
seconds=${LENGTH:-$total}
frames_dir=$(realpath -m "render/film/frames")
rm -rf "$frames_dir"; mkdir -p "$frames_dir" "$(dirname "$out")"
# chunk boundaries on whole frames, so the cut is seamless
n=$(python3 -c "import math;print(math.ceil($seconds*$fps))")
per=$(( (n+jobs-1)/jobs ))
pids=()
for ((j=0; j<jobs; j++)); do
  f0=$((j*per)); f1=$(( f0+per < n ? f0+per : n )); (( f1 > f0 )) || continue
  mkdir -p "$frames_dir/$j"
  godot --path harness -- --film --size="$res" --capture="$frames_dir/$j" \
    --start="$(python3 -c "print($start+$f0/$fps)")" --seconds="$(python3 -c "print(($f1-$f0)/$fps)")" --fps="$fps" \
    >"$frames_dir/$j.log" 2>&1 &
  pids+=($!)
done
for p in "${pids[@]}"; do wait "$p"; done
k=0
for ((j=0; j<jobs; j++)); do
  [[ -d "$frames_dir/$j" ]] || continue
  for f in $(ls "$frames_dir/$j" | sort); do mv "$frames_dir/$j/$f" "$frames_dir/$(printf %05d $k).png"; k=$((k+1)); done
done
echo "FILM: $k frames (want $n) at $fps fps, $res"
(( k == n )) || { echo "FILM: frame count mismatch"; exit 1; }
ffmpeg -hide_banner -loglevel error -y -framerate "$fps" -i "$frames_dir/%05d.png" -ss "$start" -i "$audio" -t "$seconds" \
  -c:v libx264 -preset slow -crf 18 -pix_fmt yuv420p -c:a aac -b:a 256k -movflags +faststart -shortest "$out"
echo "FILM: -> $out"

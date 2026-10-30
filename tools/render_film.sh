#!/usr/bin/env bash
# The Chamber as a film: the harness's --film mode (harness/film_director.gd,
# camera and lighting directed from the score's cues) captured over the whole
# piece and muxed with the master. Run from the repo root.
#
#   tools/render_film.sh [OUT.mp4]      env: FPS=30 RES=1920x1080 JOBS=3 START=0 LENGTH=<total_s> ONSCREEN=0
#
# Captures run on a private virtual display (tools/offscreen.sh: no windows on
# the desktop, CPU rendering); ONSCREEN=1 renders on the GPU in visible windows,
# several times faster.
#
# Every frame is a pure function of score time, so the capture is split into
# JOBS chunks rendered side by side and cut together frame-exact.
set -euo pipefail
out=${1:-render/film/the-chamber.mp4}
score=render/chamber/score.json
audio=render/chamber/chamber.wav
fps=${FPS:-30}; res=${RES:-1920x1080}; jobs=${JOBS:-3}; start=${START:-0}
launch=(tools/offscreen.sh); [[ ${ONSCREEN:-0} == 1 ]] && launch=()
total=$(python3 -c "import json;print(json.load(open('$score'))['total_s'])")
seconds=${LENGTH:-$total}
frames_dir=$(realpath -m "render/film/frames")
rm -rf "$frames_dir"; mkdir -p "$frames_dir" "$(dirname "$out")"
# chunk boundaries on whole frames, so the cut is seamless
n=$(python3 -c "import math;print(math.ceil($seconds*$fps))")
per=$(( (n+jobs-1)/jobs ))
"${launch[@]}" true 2>/dev/null || true
pids=()
chunks=()
for ((j=0; j<jobs; j++)); do
  f0=$((j*per)); f1=$(( f0+per < n ? f0+per : n )); (( f1 > f0 )) || continue
  chunk="$frames_dir/$j.mp4"
  chunks+=("$chunk")
  "${launch[@]}" godot --path harness -- --film --size="$res" --capture="$chunk" --crf=18 --preset=medium \
    --start="$(python3 -c "print($start+$f0/$fps)")" --seconds="$(python3 -c "print(($f1-$f0)/$fps)")" --fps="$fps" --silent \
    >"$frames_dir/$j.log" 2>&1 &
  pids+=($!)
done
failed=0
for p in "${pids[@]}"; do wait "$p" || failed=1; done
(( failed == 0 )) || { echo "FILM: a chunk failed; see $frames_dir/*.log" >&2; exit 1; }
list_file="$frames_dir/concat.txt"
: > "$list_file"
for c in "${chunks[@]}"; do
  [[ -s $c ]] || { echo "FILM: missing chunk $c" >&2; exit 1; }
  printf "file '%s'\n" "$c" >> "$list_file"
done
echo "FILM: ${#chunks[@]} chunks ($n frames) at $fps fps, $res"
ffmpeg -hide_banner -loglevel error -y -f concat -safe 0 -i "$list_file" -ss "$start" -i "$audio" -t "$seconds" \
  -c:v copy -c:a aac -b:a 256k -movflags +faststart -shortest "$out"
rm -rf "$frames_dir"
echo "FILM: -> $out"

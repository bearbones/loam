#!/usr/bin/env bash
# The Chamber as a film: the harness's --film mode (harness/film_director.gd,
# camera and lighting directed from the score's cues) captured over the whole
# piece and muxed with the master. Run from the repo root.
#
#   tools/render_film.sh [OUT.mp4]      env: ASSET=chamber|expanded|drums FPS=30 RES=1920x1080 JOBS=3 START=0 LENGTH=<total_s> ONSCREEN=0
#
# On WSL2, offscreen.sh streams the native Windows GPU capture to ffmpeg.
# Other hosts use a private Xvfb display unless ONSCREEN=1.
#
# Every frame is a pure function of score time, so the capture is split into
# JOBS chunks rendered side by side and cut together frame-exact.
set -euo pipefail
asset_args=()
default_fps=30
case ${ASSET:-chamber} in
  chamber) score_dir=render/chamber; title=the-chamber ;;
  expanded) score_dir=render/clockwork; title=expanded-recital; asset_args=(--expanded) ;;
  drums) score_dir=harness/assets; title=overcrank; default_fps=60; asset_args=(--drums "--view=${VIEW:-film}") ;;
  *) echo "ASSET must be chamber, expanded or drums" >&2; exit 2 ;;
esac
out=${1:-render/film/$title.mp4}
score=$score_dir/score.json
audio=$score_dir/chamber.wav
if [[ ${ASSET:-chamber} == drums ]]; then
  score=harness/assets/overcrank.json
  audio=harness/assets/overcrank.ogg
  [[ ! -f render/overcrank/overcrank.wav ]] || audio=render/overcrank/overcrank.wav
fi
fps=${FPS:-$default_fps}; res=${RES:-1920x1080}; jobs=${JOBS:-3}; start=${START:-0}
launch=(tools/offscreen.sh); [[ ${ONSCREEN:-0} == 1 ]] && launch=()
total=$(python3 -c 'import json, sys; print(json.load(open(sys.argv[1]))["total_s"])' "$score")
seconds=${LENGTH:-$total}
# ffmpeg's duration parser requires a leading zero for subsecond windows.
start=${start/#./0.}
seconds=${seconds/#./0.}
mkdir -p render/film "$(dirname "$out")"
frames_dir=$(mktemp -d "$(realpath render/film)/frames.XXXXXXXX")
# chunk boundaries on whole frames, so the cut is seamless
n=$(python3 -c "import math;print(math.ceil($seconds*$fps))")
per=$(( (n+jobs-1)/jobs ))
"${launch[@]}" true
pids=()
chunks=()
for ((j=0; j<jobs; j++)); do
  f0=$((j*per)); f1=$(( f0+per < n ? f0+per : n )); (( f1 > f0 )) || continue
  chunk="$frames_dir/$j.mp4"
  chunks+=("$chunk")
  "${launch[@]}" godot --path harness -- "${asset_args[@]}" --film --size="$res" --capture="$chunk" --crf=18 --preset=medium \
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
ffmpeg -hide_banner -loglevel error -y -f concat -safe 0 -i "$list_file" -ss "$start" -i "$audio" -map 0:v:0 -map 1:a:0 -af "atrim=duration=$seconds" \
  -c:v copy -c:a aac -b:a 256k -movflags +faststart "$out"
# A stream-copy cut on audio EOF can discard reordered video packets. Trim
# the audio alone and verify the complete score-time frame grid survived muxing.
actual=$(ffmpeg -hide_banner -loglevel error -i "$out" -map 0:v:0 -c copy -f framecrc - |
  awk -F, '$1 == 0 { n++ } END { print n+0 }')
[[ $actual == "$n" ]] || { echo "FILM: expected $n frames, muxed $actual; chunks in $frames_dir" >&2; exit 1; }
rm -rf "$frames_dir"
echo "FILM: -> $out"

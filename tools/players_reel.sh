#!/usr/bin/env bash
# The players' before/after reel (docs/goals/the-players.md, "The reel").
#
#   tools/players_reel.sh before [MOMENTS]        render the before clips (the motion of 6c326b5,
#                                                 rendered once at M0) into render/players/before/clips/
#   tools/players_reel.sh after LABEL [MOMENTS]   render LABEL's clips from the current tree, stack each
#                                                 beside its before clip, and cut the reel:
#        render/players/LABEL/clips/m<N>.mp4         LABEL alone (m<N>q.mp4: quarter speed)
#        render/players/LABEL/m<N>.mp4               before | after, 1920x540, captioned
#        render/players/LABEL/reel.mp4               the requested moments, in order
#
# MOMENTS is a comma list of the table's numbers (2,6,9); default all. Moments
# 2, 6 and 9 also render at quarter speed (m<N>q), right after their own.
#
# Environment (all optional): JOBS=3 captures at a time; CRF=20; SIZE=960x540;
# FPS=30; KEEP_FRAMES=1 keeps the PNG frames and Godot logs
# (render/players/<label>/frames/; a failed capture always keeps its log);
# BEFORE_TEXT="before 6c326b5" the left caption.
#
# Every Godot run goes through tools/offscreen.sh (a private virtual display,
# never a window on the desktop). Film moments are the harness's --film camera
# (harness/film_director.gd) at the same score time on both sides; moment 3
# (the rake has no film shot at 21 s) and moment 10 (the expanded asset has no
# film) frame their arm with --focus, as tools/contrast_reel.sh does (moment 10
# close on the hammer's head, so the lift, the blow and the check read).
#
# `before` also freezes the film camera of the before set into
# render/players/before/camera.json (harness/dev/export_camera.gd), which ruler
# 2 (tools/players/r_screen.py) reports jumps under beside the current one.
#
# Nothing outside render/players/<label>/ is written or deleted (apart from the
# camera export above, which is inside render/players/before/).
set -euo pipefail
cd "$(dirname "$0")/.."

usage() { sed -n '2,13p' "$0" >&2; exit 2; }
mode=${1:-}; shift || true
case $mode in
  before) label=before ;;
  after)  label=${1:-}; shift || true
          [[ -n $label && $label != before && $label != */* && $label != .* ]] || { echo "players_reel: after needs a LABEL (not 'before', no '/')" >&2; exit 2; } ;;
  *) usage ;;
esac
want=${1:-all}

njobs=${JOBS:-3}; crf=${CRF:-20}; size=${SIZE:-960x540}; fps=${FPS:-30}
before_text=${BEFORE_TEXT:-before 6c326b5}
after_text="after $label"
out=render/players/$label
mkdir -p "$out/clips" "$out/frames"

# ---- the moments (the goal's reel table) -----------------------------------
# N | start s | end s | shot | quarter-speed copy | what to watch
# shot: "film" (the --film camera); "focus:<aid>" (frame that arm whole, a
# 2.4 m minimum span, as contrast_reel.sh does) or "focus:<aid>@<at>:<span>"
# (--focus_at=<at> --focus_span=<span>: a close-up of its tip, root or hinged
# head); an "expanded:" prefix shoots the expanded asset. Moment 10's span is its first
# blocks_arm0 blow, read off the expanded score (1.0 s before it, 0.6 s after).
blow=$(python3 - <<'EOF'
import json
ev = [e for e in json.load(open('render/clockwork/score.json'))['events'] if e.get('actuator') == 'blocks_arm0']
t = min(float(e['t']) for e in ev)
print(f'{t-1.0:.3f} {t+0.6:.3f} {t:.3f}')
EOF
)
read -r blow0 blow1 blow_t <<<"$blow"
MOMENTS="
1|8.57|11.43|film|0|arm0-close: tolls and the 10.000 s retract
2|13.50|14.40|film|1|arm2-run: the run
3|21.0|22.0|focus:rake_arm0|0|rake: the announcement
4|25.71|28.57|film|0|overhead: tresillo and hocket
5|39.5|40.5|film|0|rake-close: the sweep
6|45.71|48.57|film|1|bars-close: the tune
7|54.29|56.79|film|0|bars-ratchet: the run and the hand-off
8|71.0|76.0|film|0|pullback: tolls and answers
9|78.0|86.0|film|1|all-arms: the chord and the ending
10|$blow0|$blow1|expanded:focus:blocks_arm0@head:1.2|0|expanded: a blocks_arm0 blow (t = $blow_t s)
"
row() { grep "^$1|" <<<"$MOMENTS" || { echo "players_reel: no moment $1 (1-10)" >&2; exit 2; }; }
if [[ $want == all ]]; then list=$(seq 1 10); else list=$(tr ',' ' ' <<<"$want"); fi
for n in $list; do row "$n" >/dev/null; done

# Each requested clip: "N" at full speed, "Nq" at quarter speed.
clips=()
for n in $list; do
  IFS='|' read -r _ _ _ _ quarter _ <<<"$(row "$n")"
  clips+=("$n"); [[ $quarter == 1 ]] && clips+=("${n}q")
done

# ---- capture ----------------------------------------------------------------
tools/offscreen.sh true          # bring the virtual display up once, before the parallel runs

capture() {                      # capture CLIP -> $out/clips/m<CLIP>.mp4
  local clip=$1 n=${1%q} speed=1
  [[ $clip == *q ]] && speed=0.25
  local start end shot what
  IFS='|' read -r _ start end shot _ what <<<"$(row "$n")"
  local seconds; seconds=$(python3 -c "print(round($end-$start, 6))")
  local frames; frames=$(python3 -c "print(round($seconds*$fps/$speed))")
  local dir; dir=$(realpath -m "$out/frames/m$clip")
  local flags=(--size="$size" --capture="$dir" --start="$start" --seconds="$seconds" --fps="$fps" --speed="$speed" --silent --clean)
  [[ $shot == expanded:* ]] && { flags+=(--expanded); shot=${shot#expanded:}; }
  case $shot in
    film)    flags+=(--film) ;;
    focus:*@*) local f=${shot#focus:}; local at=${f#*@}
             flags+=(--camera=manual --focus="${f%@*}" --focus_at="${at%:*}" --focus_span="${at#*:}") ;;
    focus:*) flags+=(--camera=manual --focus="${shot#focus:}" --focus_span=2.4) ;;
    *) echo "players_reel: moment $n: unknown shot '$shot'" >&2; return 2 ;;
  esac
  rm -rf "$dir"; mkdir -p "$dir"
  echo "players_reel: [$label] m$clip $start-$end s at ${speed}x ($frames frames): $what"
  if ! tools/offscreen.sh godot --path harness -- "${flags[@]}" >"$dir.log" 2>&1; then
    echo "players_reel: m$clip: godot failed; see $dir.log" >&2; tail -5 "$dir.log" >&2; return 1
  fi
  local got; got=$(find "$dir" -name '*.png' | wc -l)
  (( got == frames )) || { echo "players_reel: m$clip: $got frames, want $frames; see $dir.log" >&2; return 1; }
  ffmpeg -hide_banner -loglevel error -y -framerate "$fps" -i "$dir/%05d.png" \
    -c:v libx264 -preset medium -crf "$crf" -pix_fmt yuv420p -movflags +faststart "$out/clips/m$clip.mp4"
  [[ ${KEEP_FRAMES:-0} == 1 ]] || rm -rf "$dir" "$dir.log"
}

failed=0
for clip in "${clips[@]}"; do
  while (( $(jobs -rp | wc -l) >= njobs )); do wait -n || failed=1; done
  capture "$clip" &
done
while (( $(jobs -rp | wc -l) > 0 )); do wait -n || failed=1; done
(( failed == 0 )) || { echo "players_reel: a capture failed" >&2; exit 1; }
rmdir "$out/frames" 2>/dev/null || true

{ printf '%s  %s  %s  moments %s\n' "$(date -Is)" "$(git rev-parse --short HEAD)$(git diff --quiet HEAD -- formlab loam songs harness tools 2>/dev/null || echo +dirty)" "$label" "${clips[*]}"; } >>"$out/stamp.txt"

if [[ $label == before ]]; then
  # The film camera as it stands at M0, frozen beside the before clips.
  godot --headless --path harness -s dev/export_camera.gd -- --out="$(realpath -m "$out/camera.json")" | grep CAMERA || true
  echo "players_reel: before clips in $out/clips/"
  exit 0
fi

# ---- stack before | after, caption, cut the reel ----------------------------
font=$(fc-match -f '%{file}' 'DejaVu Sans' 2>/dev/null || true)
[[ -r ${font:-} ]] || font=""
w=${size%x*}; h=${size#*x}

# A caption through a file (textfile=), as contrast_reel.sh does: the
# filtergraph never parses the prose. The running score time is drawtext's own
# expansion: t = start + n*speed/fps, in ms.
caption() {                      # caption FILE TEXT START SPEED -> a drawtext chain
  [[ -n $font ]] || return 0
  local ms="trunc(($3+n*$4/$fps)*1000+0.5)"
  printf '%s   t = %%{eif:trunc(%s/1000):d}.%%{eif:mod(%s,1000):d:3} s' "$2" "$ms" "$ms" >"$1"
  printf "drawtext=fontfile='%s':textfile='%s':x=16:y=h-text_h-14:fontsize=20:fontcolor=white@0.95:box=1:boxcolor=black@0.5:boxborderw=8" "$font" "$1"
}

stacked=()
for clip in "${clips[@]}"; do
  n=${clip%q}; speed=1; tag=""
  [[ $clip == *q ]] && { speed=0.25; tag="  quarter speed"; }
  IFS='|' read -r _ start end _ _ what <<<"$(row "$n")"
  left=render/players/before/clips/m$clip.mp4; right=$out/clips/m$clip.mp4
  [[ -r $left ]] || { echo "players_reel: no $left: run tools/players_reel.sh before $n" >&2; exit 1; }
  head="m$n  $start-$end s$tag"
  lc=$(caption "$(realpath -m "$out/m$clip.left.txt")" "$head  ·  $before_text" "$start" "$speed")
  rc=$(caption "$(realpath -m "$out/m$clip.right.txt")" "$head  ·  $after_text" "$start" "$speed")
  ffmpeg -hide_banner -loglevel error -y -i "$left" -i "$right" -filter_complex \
    "[0:v]scale=$w:$h,setsar=1${lc:+,$lc}[l];[1:v]scale=$w:$h,setsar=1${rc:+,$rc}[r];[l][r]hstack=inputs=2[v]" \
    -map '[v]' -r "$fps" -c:v libx264 -preset medium -crf "$crf" -pix_fmt yuv420p -movflags +faststart "$out/m$clip.mp4"
  rm -f "$out/m$clip.left.txt" "$out/m$clip.right.txt"
  stacked+=("m$clip.mp4")
  echo "players_reel: $out/m$clip.mp4  ($what)"
done

list_file=$out/reel.txt
printf "file '%s'\n" "${stacked[@]}" >"$list_file"
ffmpeg -hide_banner -loglevel error -y -f concat -safe 0 -i "$list_file" -c copy -movflags +faststart "$out/reel.mp4"
rm -f "$list_file"
echo "players_reel: $out/reel.mp4  (${stacked[*]})"

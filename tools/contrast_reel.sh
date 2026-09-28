#!/usr/bin/env bash
# The stepped-vs-servo contrast reel, in one command (docs/motion-design.md).
#
#   tools/contrast_reel.sh START SECONDS [FPS] [OUT.mp4]
#
# Captures the same score window twice — a stepped (mallet) mechanism and a
# servo (pick) one — encodes each, stacks them side by side with a caption
# naming the vocabulary, and shows the result to the operator. The two captures
# run concurrently, because a frame costs about 0.8 s.
#
# Environment knobs (all optional):
#   LEFT / RIGHT        what to shoot. "view:N" for one of the numbered views,
#                       or "focus:<aid>" to frame that arm's own mechanism.
#                       Default: focus on the first mallet arm / the first pick arm.
#   LEFT_TEXT/RIGHT_TEXT  the captions.
#   SPEED               score seconds a video second (0.25 = quarter speed).
#                       --seconds stays the SCORE window, so the reel gets longer.
#   SPAN                metres of rail across a --focus frame (default 2.4;
#                       narrow it for a click close-up).
#   ASSET               "chamber" (default) or "expanded".
#   AUDIO               1 to mux the master from the same offset (off by default:
#                       a slow-motion reel has no matching audio).
#   OUTDIR              where the frames go (default render/clockwork-review).
set -euo pipefail
cd "$(dirname "$0")/.."

start=${1:?START seconds into the score}
seconds=${2:?SECONDS of score to cover}
fps=${3:-60}
out=${4:-render/clockwork-review/contrast-reel.mp4}
speed=${SPEED:-1}
span=${SPAN:-2.4}
asset=${ASSET:-chamber}
outdir=${OUTDIR:-render/clockwork-review}

extra=()
manifest=harness/assets/clockwork.json
audio_path=render/chamber/chamber.wav
if [[ $asset == expanded ]]; then
  extra+=(--expanded); manifest=harness/assets/clockwork_expanded.json; audio_path=render/clockwork/chamber.wav
fi

# The default subjects are read out of the manifest, so the reel works on a
# clean checkout and on either asset: the first stepped arm against the first
# servo one. `kind` is the vocabulary (formlab.rig.Rig.stepped).
pick_arm() { python3 - "$manifest" "$1" <<'EOF'
import json, sys
arms = json.load(open(sys.argv[1]))['arms']
want = ('mallet', 'hammer') if sys.argv[2] == 'stepped' else ('pick', 'rake')
print(next((a for a, c in arms.items() if c['kind'] in want), ''))
EOF
}
left=${LEFT:-focus:$(pick_arm stepped)}
right=${RIGHT:-focus:$(pick_arm servo)}
left_text=${LEFT_TEXT:-stepped: ratchet clicks / cocked drop / recoil}
right_text=${RIGHT_TEXT:-servo: jerk-limited S-curve slew}

# A caption needs a font file; ffmpeg's drawtext will not look one up. Take
# whatever the system offers and drop the caption if it offers nothing.
font=$(fc-match -f '%{file}' 'DejaVu Sans' 2>/dev/null || true)
[[ -r ${font:-} ]] || font=""

# "view:N" / "focus:<aid>" -> the godot flags that shoot it
shot_flags() {
  case $1 in
    view:*)  printf -- '--view=%s' "${1#view:}" ;;
    focus:*) printf -- '--focus=%s --focus_span=%s' "${1#focus:}" "$span" ;;
    *)       echo "contrast_reel: don't know how to shoot '$1' (use view:N or focus:<aid>)" >&2; exit 2 ;;
  esac
}

capture() {                                   # capture SIDE SUBJECT
  local side=$1 subject=$2
  local dir; dir=$(realpath -m "$outdir/reel-$side-frames")
  rm -rf "$dir"; mkdir -p "$dir"
  read -r -a flags <<<"$(shot_flags "$subject")"
  # setsid+nohup so the two godot runs survive this shell's job control and
  # actually run at the same time; a marker file is the done signal.
  rm -f "$dir.done"
  setsid nohup bash -c "godot --path harness -- ${extra[*]} --capture='$dir' --start=$start --seconds=$seconds \
      --fps=$fps --speed=$speed --camera=manual ${flags[*]} --silent --clean > '$dir.log' 2>&1; touch '$dir.done'" \
      >/dev/null 2>&1 &
  echo "$dir"
}

left_dir=$(capture left "$left")
right_dir=$(capture right "$right")
frames=$(python3 -c "print(int($seconds*$fps/$speed))")
echo "contrast_reel: $left | $right — $frames frames a side at ${fps} fps, speed ${speed}x"
while [[ ! -e $left_dir.done || ! -e $right_dir.done ]]; do
  sleep 10
  printf '\r  %s: %d/%d   %s: %d/%d' \
    "$left" "$(find "$left_dir" -name '*.png' | wc -l)" "$frames" \
    "$right" "$(find "$right_dir" -name '*.png' | wc -l)" "$frames"
done
echo
for d in "$left_dir" "$right_dir"; do
  [[ $(find "$d" -name '*.png' | wc -l) -ge $frames ]] || { echo "contrast_reel: $d is short; see $d.log" >&2; tail -5 "$d.log" >&2; exit 1; }
done

mkdir -p "$(dirname "$out")"
# Stack the two captures and caption each half. A drawtext argument is parsed
# for ' , : and \ before the text ever reaches the renderer, so the caption goes
# through a file (`textfile=`) instead of being escaped — captions are prose and
# prose has punctuation in it.
caption() {                                   # caption SIDE LABEL -> a drawtext chain, or nothing
  [[ -n $font ]] || { printf ''; return; }
  local f; f=$(realpath -m "$outdir/reel-$1-caption.txt")
  printf '%s' "$2" > "$f"
  printf ",drawtext=fontfile='%s':textfile='%s':x=(w-text_w)/2:y=h-64:fontsize=30:fontcolor=white@0.92:box=1:boxcolor=black@0.45:boxborderw=14" \
    "$font" "$f"
}
ffmpeg -hide_banner -loglevel error -y \
  -framerate "$fps" -i "$left_dir/%05d.png" \
  -framerate "$fps" -i "$right_dir/%05d.png" \
  -filter_complex "[0:v]scale=-2:900,setsar=1$(caption left "$left_text")[l];[1:v]scale=-2:900,setsar=1$(caption right "$right_text")[r];[l][r]hstack=inputs=2[v]" \
  -map '[v]' -c:v libx264 -crf 19 -pix_fmt yuv420p -r "$fps" "$out.silent.mp4"

if [[ ${AUDIO:-0} == 1 && -r $audio_path && $speed == 1 ]]; then
  ffmpeg -hide_banner -loglevel error -y -i "$out.silent.mp4" -ss "$start" -i "$audio_path" \
    -t "$seconds" -c:v copy -c:a aac -b:a 192k -shortest "$out"
  rm -f "$out.silent.mp4"
else
  mv "$out.silent.mp4" "$out"
fi

show "$out" "Contrast reel ${start}s +${seconds}s at ${speed}x — left $left_text; right $right_text"
echo "contrast_reel: $out"

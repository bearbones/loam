#!/usr/bin/env bash
# Run a command offscreen so a capture never opens a visible window on the
# operator's desktop:
#
#   tools/offscreen.sh godot --path harness -- --film --size=960x540 --capture=OUT.mp4 ...
#
# On WSL2 with /mnt/c/Users/scant/.cache/loam-win/Godot_v4.7-stable_win64_console.exe
# present (and OFFSCREEN_CPU != 1), renders natively on the Windows NVIDIA GPU
# from the Windows filesystem (positioned offscreen at -10000,-10000).
# Otherwise falls back to a private Xvfb virtual display (Mesa llvmpipe CPU).
set -euo pipefail
repo_root=$(cd "$(dirname "$0")/.." && pwd)
win_dir="/mnt/c/Users/scant/.cache/loam-win"
win_exe="$win_dir/Godot_v4.7-stable_win64_console.exe"
win_prefix="C:/Users/scant/.cache/loam-win"

if [[ ${OFFSCREEN_CPU:-0} != 1 && -x $win_exe ]]; then
  mkdir -p "$win_dir/render" "$win_dir/tmp"
  if [[ ${1:-} == true ]]; then
    flock /tmp/loam-win-sync.lock bash -c "
      rsync -a --delete '$repo_root/harness/' '$win_dir/harness/'
      [[ -d '$repo_root/render/chamber' ]] && rsync -a --delete '$repo_root/render/chamber/' '$win_dir/render/chamber/'
      [[ -d '$repo_root/render/clockwork' ]] && rsync -a --delete '$repo_root/render/clockwork/' '$win_dir/render/clockwork/'
    "
    exit 0
  fi
  if [[ ${1:-} == godot ]]; then
    shift
    flock /tmp/loam-win-sync.lock rsync -a "$repo_root/harness/" "$win_dir/harness/"
    cap_linux=""
    cap_win_host=""
    shot_linux="${SHOT:-}"
    shot_win_host=""
    args=()
    for a in "$@"; do
      if [[ $a == --capture=* ]]; then
        cap_linux=$(realpath -m "${a#--capture=}")
        if [[ $cap_linux == *.mp4 ]]; then
          cap_win_host="$win_dir/tmp/cap_$$.mp4"
          args+=("--capture=$win_prefix/tmp/cap_$$.mp4")
        else
          cap_win_host="$win_dir/tmp/cap_$$"
          rm -rf "$cap_win_host"; mkdir -p "$cap_win_host"
          args+=("--capture=$win_prefix/tmp/cap_$$")
        fi
      else
        args+=("$a")
      fi
    done
    if [[ -n $shot_linux ]]; then
      shot_linux=$(realpath -m "$shot_linux")
      shot_win_host="$win_dir/tmp/shot_$$.png"
      export SHOT="$win_prefix/tmp/shot_$$.png"
      export WSLENV="${WSLENV:+$WSLENV:}SHOT"
    fi
    rc=0
    (cd "$win_dir" && ./Godot_v4.7-stable_win64_console.exe --position -10000,-10000 "${args[@]}" < /dev/null) || rc=$?
    if (( rc == 0 )); then
      if [[ -n $cap_linux ]]; then
        if [[ $cap_linux == *.mp4 ]]; then
          mkdir -p "$(dirname "$cap_linux")"
          mv -f "$cap_win_host" "$cap_linux"
        else
          mkdir -p "$cap_linux"
          mv -f "$cap_win_host"/* "$cap_linux"/ 2>/dev/null || true
          rm -rf "$cap_win_host"
        fi
      fi
      if [[ -n $shot_linux && -f $shot_win_host ]]; then
        mkdir -p "$(dirname "$shot_linux")"
        mv -f "$shot_win_host" "$shot_linux"
      fi
    else
      rm -rf "$cap_win_host" "$shot_win_host" 2>/dev/null || true
    fi
    exit "$rc"
  fi
fi

xvfb=$(command -v Xvfb || echo "$HOME/.local/opt/xvfb/usr/bin/Xvfb")
[[ -x $xvfb ]] || { echo "offscreen: no Xvfb — apt-get download xvfb && dpkg -x xvfb_*.deb ~/.local/opt/xvfb" >&2; exit 1; }
disp=${OFFSCREEN_DISPLAY:-:97}
sock=/tmp/.X11-unix/X${disp#:}
up() { [[ -e $sock ]] || grep -q "@$sock$" /proc/net/unix 2>/dev/null; }
if ! up; then
  setsid "$xvfb" "$disp" -screen 0 1920x1080x24 -nolisten tcp >/dev/null 2>&1 < /dev/null &
  for _ in $(seq 100); do up && break; sleep .1; done
  up || { echo "offscreen: Xvfb did not come up on $disp" >&2; exit 1; }
fi
exec env -u WAYLAND_DISPLAY DISPLAY="$disp" "$@"

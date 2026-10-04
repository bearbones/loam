#!/usr/bin/env bash
# Run a command on a private virtual X display, so a capture never opens a
# window on the operator's desktop:
#
#   tools/offscreen.sh godot --path harness -- --film --size=960x540 --capture=DIR ...
#
# Xvfb renders through Mesa's llvmpipe (the CPU): slower than the GPU, the same
# frames. The display (OFFSCREEN_DISPLAY, default :97) is started once and left
# up for the next capture. A system Xvfb is used if there is one; otherwise one
# unpacked without root:
#   apt-get download xvfb && dpkg -x xvfb_*.deb ~/.local/opt/xvfb
set -euo pipefail
xvfb=$(command -v Xvfb || echo "$HOME/.local/opt/xvfb/usr/bin/Xvfb")
[[ -x $xvfb ]] || { echo "offscreen: no Xvfb — apt-get download xvfb && dpkg -x xvfb_*.deb ~/.local/opt/xvfb" >&2; exit 1; }
disp=${OFFSCREEN_DISPLAY:-:97}
sock=/tmp/.X11-unix/X${disp#:}
if [[ ! -e $sock ]]; then
  setsid "$xvfb" "$disp" -screen 0 1920x1080x24 -nolisten tcp >/dev/null 2>&1 < /dev/null &
  for _ in $(seq 100); do [[ -e $sock ]] && break; sleep .1; done
  [[ -e $sock ]] || { echo "offscreen: Xvfb did not come up on $disp" >&2; exit 1; }
fi
exec env -u WAYLAND_DISPLAY DISPLAY="$disp" "$@"

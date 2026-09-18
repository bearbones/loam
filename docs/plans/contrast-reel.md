# One command for the stepped-vs-servo contrast reel

**Status (2026-09-17):** landed (commit cf1cd5b) as `tools/contrast_reel.sh`,
with the `--focus`/`--focus_span`/`--focus_dir` camera it needed in
`harness/performance.gd`. The lesson worth keeping is in
`docs/motion-design.md`: picking the *moment* mattered more than the angle.

**Where:** `tools/capture_clockwork.sh` (exists: single captures), a new
`tools/contrast_reel.sh`, `harness/performance.gd` (`--capture`, `--clean`,
`--view`, a new `--focus=<aid>` camera), `docs/motion-design.md`
("Rendering clips").

**Problem:** the operator asked to see clips of the contrast between the
ratcheted mallet motion (with recoil) and the smooth servo slews. Making one
today is four manual steps per clip (`godot --capture`, `ffmpeg` encode,
`ffmpeg hstack` with `drawtext`, `show`), with traps (the font must be
copied to the working directory as `f.ttf`; commas break the filter graph;
0.8 s a frame). Every future motion change will want the same reel.

**Work:**

1. `--focus=<aid>`: a camera that frames one arm's carriage and tool over
   its motion window (fit the arm's `reach_x` and the rail, look along −z
   from a little above), so a clip reads the mechanism, not the room. Use
   the existing manual-camera plumbing (`look.gd`, `--camera=manual`).
2. `tools/contrast_reel.sh START SECONDS [FPS] [OUT.mp4]`: captures view 3
   (bars) and view 1 (harp) — or two `--focus` arms — over the same window
   in two background godot runs, encodes each, stacks them side by side with
   captions ("stepped: ratchet, cocked drop, recoil" / "servo: S-curve
   slew"), and `show`s the result. Pass `--clean` so the HUD is hidden.
   Fonts: ship `harness/fonts/DejaVuSans.ttf` (it is already a project
   dependency for the HUD? check `harness/`) and reference it relatively.
3. A slow-motion variant: `--fps=240 --speed=0.25` in `performance.gd`
   (evaluate at `t0 + frame/(fps·speed)`) so a 90 ms click fills 20 frames.
4. Document the command in `docs/motion-design.md` and replace the four
   manual lines there.

**Acceptance:** one command produces the reel from a clean checkout; a
quarter-speed close-up of one click (view --focus on a mallet arm) shows
the ratchet's 40 % move, the overshoot ringing out on the pawl, and the
mallet's cocked drop; sent to the operator with `SendUserFile` and `show`.

**Notes:** captures are 0.8 s a frame; a 5 s 60 fps clip is four minutes —
run the two captures concurrently with `setsid nohup` and poll a done
marker, as `build_both_full.sh` does.

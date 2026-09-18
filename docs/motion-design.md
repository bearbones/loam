# Motion design: two vocabularies

The rig used to move everything the same way: a smoothstep from wherever it
was to wherever the score wanted it, in exactly the window the score gave.
Every arm read as the same rubbery actuator. The chamber now speaks two
vocabularies, chosen by what the arm is — a mallet arm is a *stepped
machine*, a pick or rake arm is a *servo* — and the contrast between them is
the point: a ratchet clicking into place and a blow that shakes the whole
assembly, against a slew that could be a telescope drive.

Both live in `harness/clockwork_motion.gd` (`ClockworkMotion`) and its numpy
mirror `formlab/rig.py` (`Rig`), which every clearance ruler samples;
`tools/test_motion.py` holds the two to each other (0.6 µm over 300 000
samples) and checks what each vocabulary promises. The constants are at the
top of both files.

## Stepped: mallet (and hammer) arms

**Carriage travel is a ratchet.** A move of `dx` along the rail is
`teeth(dx)` teeth of the rack (pitch 2π·0.12/16 = 47 mm, the pinion's), taken
one a click at 90 ms a click when the score leaves time; when it does not,
clicks come no faster than 40 ms and each spans several teeth. A click
spends its first 40 % moving — a minimum-jerk step to a tenth of a tooth
*past* the detent (the pawl's play, 4.7 mm however many teeth the click
spans) — and rings out on the pawl at 14 Hz with a 90 ms decay, faded to
nothing before the next click so the carriage sits exactly on the detent.
The arm's y/z follow in one minimum-jerk move over the same window, so
only the rail axis clicks. `test_motion` checks the carriage sits within
the pawl's play of a detent at least half the time (0.80 measured), that
each travel crosses exactly its planned number of detents, that the
overshoot stays within 4.7 mm and that every travel lands exactly.

**The click has a mechanism.** Under each mallet arm's pinion a sprung
roller detent pawl rides the teeth (`formlab/pawl.py`; `docs/articulated-arms.md`,
"The carriage and its drive"): as the carriage clicks a tooth along the rack
the disc turns a tooth and the roller rides over a tip and dips 9.5 mm into
the next gap, so every click is a visible drop of the pawl, and the recoil's
shudder along the rail ticks it back and forth. `ClockworkMotion.pawl_angle`
mirrors `pawl.angle` (5e-13 rad) and `performance.gd` poses the part.

**The strike is a cocked drop.** Over the score's approach interval the
mallet first rises half its lift again (to 0.33 m over the bar, by 40 % of
the interval, smoothly) and then falls with `1 − v²` — the acceleration of
a fall, arriving at the bar at its fastest — so the hit lands exactly on
the scored time with nothing rubbery about it. The release lifts back on a
quintic.

**The blow shakes the assembly.** After every hit a *recoil* is added to
the whole arm: the carriage shudders along the rail (4 mm, 11 Hz, 140 ms
decay — the pinion ticks back and forth with it), the mallet rings across
the bar (2.5 mm, 17 Hz, 100 ms) and bounces above it (6 % of the lift,
8 Hz, 160 ms, always upward so it never re-enters the bar). All three are
zero at the blow itself and gated to zero 80 ms before the next strike
begins, so every scored contact is still exact to 1e-9 m and the ring
never smears a hit. The bars' own bounce (`performance.gd`) plays under it.

## Servo: pick and rake arms

**Slews are S-curves.** A reposition is a jerk-limited profile: a smooth
acceleration ramp over the first 30 % of the window, a constant-velocity
cruise, and the mirror ramp — a telescope drive's profile. Velocity and
acceleration are zero at both ends, the motion is monotone (no overshoot,
ever) and lands exactly. When the score allows, a slew takes 0.4 s; an
unhurried slew cruises at 1/(1−0.3) = 1.43× its mean speed, which the ruler
measures. The pluck itself keeps its wind-up (away from the string, 45 % of
the lift) on a minimum-jerk curve. Nothing rings.

## A machine moves, then waits

The score planner sets `t_move`, the *latest* start that makes the hit.
Both vocabularies now start repositioning as soon as the arm is free and
the move wants (`teeth × 90 ms` for a ratchet, 0.4 s for a slew), never
later than `t_move` — the stepper clicks into place during the rest and
waits over the bar; the servo slews unhurriedly instead of snapping in the
last 50 ms. 300 of the 316 moves in the piece start early.

That early start needs the planner's clearance promise re-checked. The
planner (`loam/score.py`, `_Solver._separated`) promises two arms of one
mechanism stay `arm_clearance_m` apart along x by charging a moving arm
with the whole interval it crosses *from `t_move`* and a resting arm with a
point over its last contact. `ClockworkMotion._schedules()` applies the
same occupancy model to the earlier window, symmetrically: every sibling is
charged with its interval from its *own* earliest start (it may start early
too), padded by the overshoot and recoil (10 mm), and a move that would
come within the clearance is pushed later until the interval it wants is
clear — at worst back to `t_move`, where the planner's promise takes over.
`dev/test_clockwork.gd` and `test_motion` measure the rendered result: the
margin beyond the promise is unchanged at 56 mm on both assets (an early
draft without the check was 129 mm inside it).

## What the space accounting saw

Every clearance ruler samples `Rig` (120 Hz plus every contact), so the
cock, the overshoot and the recoil are in the swept capsules that the rail
gantries, oil cups, eyelets, flywheel, neck and form-clearance rulers
measure. They all pass unchanged: the added excursions (11 cm up over a
bar that already had 22 cm of lift, 5 mm along the rail, 2.5 mm across the
bar) stay well inside margins measured in centimetres. The rail search
cache does not hash `rig.py`; the rails were planned against the old
motion and the rulers re-measured them against the new.

## Rendering clips

`godot --path harness -- --capture=DIR --start=T --seconds=N --fps=60
--camera=manual --view=V --silent` writes `DIR/%05d.png`;
`ffmpeg -framerate 60 -i DIR/%05d.png -c:v libx264 -pix_fmt yuv420p out.mp4`.
View 3 frames the bars (stepped), view 1 the harp (servo). A frame renders
in about 0.8 s, so a 5 s clip at 60 fps takes four minutes.

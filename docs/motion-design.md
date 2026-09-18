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
the disc turns a tooth and the roller rides over a tip and dips 15.5 mm into
the next gap, so every click is a visible drop of the pawl, and the recoil's
shudder along the rail ticks it back and forth. `ClockworkMotion.pawl_angle`
mirrors `pawl.angle` (5e-13 rad) and `performance.gd` poses the part. The
roller turns as it rolls on the tips (2.8 rad a tooth, the other way from
the disc), and the pinion is spun with a phase that seats the roller in a
dip when the arm parks at its home — a detent rests in a dip. The score's
other rests are wherever its contacts put the carriage, so away from home
the pawl parks on a tip or a flank as often as in a gap; that is honest
(the tool must reach the contact), and `tools/test_pawl.py` counts how many
rests seat anyway.

**The click has a sound.** `ClockworkMotion.click_times(aid)` lists a
stepped arm's clicks — one at the landing of each of a travel's `n` clicks,
`go + (k + CLICK_MOVE)·T/n`, the moment the roller drops onto the next tooth
in `ratchet` — and `performance.gd` plays a click sample from a player that
rides on each pawl's roller (so the sound comes from wherever the carriage
is), 12 dB under the instruments, gated by `--silent` and quiet in shots
and captures like the master. The sample is synthesised at load
(`click_sample`): a 3 ms metallic tick, three inharmonic partials over a
grain of noise, and under it the pawl's spring ringing against the
carriage at `RING_HZ` — a low thump beating at the ring rate that dies in
`RING_TAU`, the same ring the carriage's overshoot makes. `dev/dump_clicks.gd`
prints the clicks and writes the sample so `tools/click_mix.py` can lay them
under a passage of the master for listening outside the harness.
`test_performance` holds each pawl's player to its roller and the mix level,
every click inside its travel and no two closer than `CLICK_MIN_S`, and the
count to the schedule's `clicks(dx, T)` per travel.

**The strike is a cocked drop.** Over the score's approach interval the
mallet first rises half its lift again (to 0.33 m over the bar, by 40 % of
the interval, smoothly) and then falls with `1 − v²` — the acceleration of
a fall, arriving at the bar at its fastest — so the hit lands exactly on
the scored time with nothing rubbery about it. The release lifts back on a
quintic.

**A hammer arm strikes with its head, not its arm.** `kind == 'hammer'`
(the expanded asset's block arm) is the sharpest motion in the piece, and
it does not come from a metre of arm: the head hangs on a pin 120 mm under
the tool's flange and flips. What that changes is the *split* of the
clearance lift. `Rig.clearance` is still the promise about the CONTACT —
0.22 m over the bar — but `Rig.hover` is what the arm provides, and for a
hammer that is `arm_share` = 30 % of it, 66 mm. The other 154 mm is the
head lying back on its check, and that is what fixes the rest angle:
`head_l·(1 − cos θ) = 154 mm` gives **106.5°**, nothing to tune. (A
consequence worth knowing: the rise a flip can supply is at most
`2·head_l`, so a longer lift needs a longer head, not a bigger angle.)

Over the strike the arm makes its own cocked drop through its 66 mm while
the head's angle runs `rest·cocked(u, 0.02)` — the same profile, so the two
stay in phase — to **exactly zero** at the blow. Zero is the felt face
straight down under the pin, which is the whole reason the contact is still
exact to 1e-9 m: `head_offset(0) = 0`. The head's own cock is small (2 % of
the rest angle, 1.1 mm at the tail) because it presses into the check's felt
rather than swinging past it; the visible cock is the arm's.

After the blow the head **rebounds and the check takes it** — `|damped
sine|`, 0.10 rad at 12.5 Hz decaying in 45 ms, so the felt bounces twice and
never passes back through the bar — fading into the lay-back as the arm
releases. A hammer arm's `recoil` is therefore exactly zero: the recoil
happens in the head and its check, not in the whole arm. The assembly's
shudder still fires, because the blow is as hard either way.

The head flips **toward its own rail** (`flip_sign`, from the arm's
`root_z` against its home contact), never out over the instrument, and the
flange has to *straddle* the arc: the rod sweeps 120 mm one way and the
tail 30 mm the other, so there is nowhere in that plane for a bracket to
stand. Two cheek plates outboard of the felt head's own radius carry the
pin, which is how a piano hammer flange is built, for the same reason.

**The blow shakes the assembly.** After every hit a *recoil* is added to
the whole arm (a mallet's; a hinged hammer's is in its head, above): the carriage shudders along the rail (4 mm, 11 Hz, 140 ms
decay — the pinion ticks back and forth with it), the mallet rings across
the bar (2.5 mm, 17 Hz, 100 ms) and bounces above it (6 % of the lift,
8 Hz, 160 ms, always upward so it never re-enters the bar). All three are
zero at the blow itself and gated to zero 80 ms before the next strike
begins, so every scored contact is still exact to 1e-9 m and the ring
never smears a hit. The bars' own bounce (`performance.gd`) plays under it.

**And it shakes the assembly around the arm.** The arm alone answering its
own blow left the instrument stand, the guide bars and the gantry rigid — a
felt head on a 5 kg bar over a wooden trestle, and nothing under it moves.
Every blow now goes on a **recoil bus** (`ClockworkMotion._bus`,
`Rig._bus`): one entry a hit, carrying where it landed along the rail and
how hard (the score's amplitude times the cocked drop's height, 1.0 for a
full-amplitude mallet) and the moment its arm's next strike begins, which
gates its ring exactly as `recoil` is gated. Three rigid-body shudders read
that bus, all `_ring` damped sinusoids and so all exactly zero at the blow
they answer:

- the **stand** (`form_bars_stand`, `form_<mid>_stand`) thumps vertically,
  **1.5 mm at 9 Hz over 120 ms**, summed over every blow on that instrument;
  the bars keep their own bounce under it. A walnut trestle carrying the
  bars' mass sits in the high single figures of Hz and rings about once
  visibly; the amplitude is the dial the operator will turn.
- the **rail** sags. A guide bar is 24 mm steel over about a 2 m span pinned
  in its two heads, so the shudder is that beam's **first bending mode**: a
  half sine over the span, zero at the heads, excited in proportion to how
  central the blow was (`sin(pi*u_hit)`) and read out at whatever x you ask
  for (`sin(pi*u_x)`). A blow at mid-span therefore sags the rail by
  **1 mm at 12 Hz over 150 ms** and a blow under a head barely moves it,
  which is what a beam does. The pair of bars alone rings near 22 Hz; with
  the carriage's and the arm's mass at mid-span a loaded-beam estimate puts
  it near 16 Hz, and 12 Hz is chosen so one ring reads at 60 fps. The
  amplitude is frankly exaggerated: the same estimate gives about 0.1 mm
  of deflection for the impulse a felt head delivers, and 1 mm is an order
  of magnitude over it for the same reason the string displacement is
  exaggerated — it has to be visible. **The carriage follows the sag at its
  own x** (`pose()` adds it to `root.y`), so the links, the pinion and the
  pawl ride down with the bar; the tip is the scored path and its own
  recoil, untouched, so every contact stays exact. The two guide bars are
  rigid meshes and carry the sag at mid-span instead of bending, so the
  carriage and the rendered bar diverge by at most **0.18 mm** over either
  piece — inside the 4 mm `offset_hits` margin and the 9 mm the second-bar
  boss keeps from the guide bars, so nothing new touches.
- the **gantry** (`form_<aid>_gantry`, `form_<aid>_railhead`) sways
  **0.3 mrad at 6 Hz over 300 ms** — 0.6 mm at the head of a 2.05 m mast.
  The tilt is *across* the rail, about world X through the line between
  both plinth feet: the knee braces stiffen the gantry along the rail, and
  putting the axis through the feet means no mast gains a lever arm down
  the span. Steel in a bolted joint damps slowly, hence the long decay.

The harp's and the rake's frames are deliberately **not** on the bus: those
are servo arms and nothing there is struck. The stand and the masts are
fixed forms as far as the offline rulers are concerned (1.5 mm and 0.6 mm
are inside every margin those rulers measure, which are centimetres); the
rail sag is mirrored in `formlab/rig.py` because it moves the carriage and
so every capsule of the arm. `tools/test_motion.py` checks each shudder is
exactly zero at its blow, live 10–40 ms later, spent before the next strike
begins, never over its named amplitude, and agrees with the rendered
GDScript to 1.3e-10 over 52 200 samples; `dev/test_performance.gd` checks
the rendered nodes are at rest before the first blow, answer it within
40 ms and are home again by the next strike. Every amplitude is a named
constant at the top of both motion files, and `SHUDDER_GAIN` (1.0) scales all
three together — one number to tune by eye, mirrored in both files so the
rendered rig and the rulers never disagree.

**How much of this you can actually see.** Measured, not asserted: the same
frame rendered with the three amplitudes and with them zeroed differs in
0.42 % of its pixels from view 3 and 0.08 % from a 1.1 m `--focus` close-up,
peak 81 of 255 — a sub-pixel shimmer along the edges of the stand, the bars
and the masts, which reads in motion (the eye is far better at coherent
sub-pixel motion than a still frame suggests) but is not the assembly visibly
answering the blow. That is the honest consequence of a millimetre on a stage
four metres wide, and it is why `SHUDDER_GAIN` exists: the physical estimates
are the default, and if the operator wants the blow *seen* rather than
*implied*, one number takes it to six or eight the way the strings are already
exaggerated for inspection. Nothing else has to move with it — the rulers
sample `Rig` and re-measure the gain they are given.

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

The contrast between the two vocabularies is the point, so making the reel
that shows it is one command:

```sh
tools/contrast_reel.sh START SECONDS [FPS] [OUT.mp4]
tools/contrast_reel.sh 52.1 4                       # a mallet arm beside a pick arm
SPEED=.25 SPAN=1.4 tools/contrast_reel.sh 55.95 .55 # one step, quarter speed, close
LEFT=view:3 RIGHT=view:1 tools/contrast_reel.sh 45.5 6
ASSET=expanded AUDIO=1 tools/contrast_reel.sh 52.1 4
```

It captures the same score window twice, encodes each, stacks them side by
side with a caption naming the vocabulary, and `show`s the result. The two
captures run concurrently under `setsid nohup` with a done-marker (a frame
costs about 0.8 s, so a 4 s 60 fps reel is about three minutes of wall clock
rather than six). `LEFT`/`RIGHT` take `view:N` or `focus:<aid>`; with neither
set it reads the manifest and picks the first stepped arm against the first
servo one, so the command works on a clean checkout and on either asset.
Captions need a font file, which `fc-match` supplies and the script drops the
caption if it cannot.

Two pieces of the harness make that possible:

**`--focus=<aid>`** frames one arm's own mechanism instead of the room. An
arm is about a metre from its carriage down to its tool and a click close-up
has to hold both ends — the pawl riding the pinion at the top, the mallet's
cocked drop at the bottom — so the camera frames the arm's own root-to-tip box
with 300 mm of air, following it along the rail. `--focus_span` (2.4 m by
default) is therefore a *minimum* width: narrowing it centres the shot tighter
but cannot crop the tool out, and widening it past the rail's length frames the
whole span.

**`--focus_at=tip`** (or `root`, or `head` — a hinged hammer's pin, `HEAD_L`
above the tool frame's origin) throws that box away and frames one *end* of
the arm, and then `--focus_span` is the frame's true width rather than a
minimum. The hinged hammer is what forced it: the flange, the pin, the head
and its check are 200 mm of mechanism on the end of a 1.6 m arm, and a shot
that holds the carriage cannot also show the check catch the rebound. Use it
sparingly — a close-up with no carriage in it stops being a picture of a
machine.

Which side to stand on is not free. Every arm works behind its instrument, so
the camera stands on the far side of the carriage from the mechanism's centre
and a little above; standing in front of a pick arm photographs the strings it
is hiding behind. `--focus_dir=x,y,z` overrides that when a shot wants a
particular angle — the room has furniture an automatic camera cannot know
about, and a mast or a resonator will occasionally land in the middle of the
frame.

**Pick the moment, not just the angle.** A close-up of an arm parked at a rail
head is a picture of a mast, and a strike that repeats on the same tooth shows
no travel at all. The reel above is shot at 55.95 s because `bars_arm0` steps
3.54 → 3.92 → 4.31 m there, mid-rail, while `harp_arm0` slews −0.60 → −0.38:
both vocabularies moving, both away from their gantry heads. The schedule that
says so is `formlab.rig.Rig.sched` — each entry's `approach`, `hit` and `first`
are the window, the contact and the x it happens at.

**`--speed=S`** runs score time at S seconds a video second during a capture,
so `--fps=60 --speed=0.25` fills 22 frames with a 90 ms click. `--seconds`
stays the *score* window, so the frame count (and the render) grows as the
speed falls.

The raw capture is still there when a single shot is what is wanted:

```sh
godot --path harness -- --capture=DIR --start=T --seconds=N --fps=60 \
    --camera=manual --view=V --silent --clean       # writes DIR/%05d.png
ffmpeg -framerate 60 -i DIR/%05d.png -c:v libx264 -pix_fmt yuv420p out.mp4
```

View 3 frames the bars (stepped), view 1 the harp (servo), view 15 the
ratchet's pinion and pawl.

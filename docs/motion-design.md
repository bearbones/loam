# Motion design: two vocabularies

The rig used to move everything the same way: a smoothstep from wherever it
was to wherever the score wanted it, in exactly the window the score gave.
Every arm read as the same rubbery actuator. The chamber now speaks two
vocabularies, chosen by what the arm is — a mallet arm is a *stepped
machine*, a pick or rake arm is a *servo* — and the contrast between them is
the point: a ratchet clicking into place and a blow that shakes the whole
assembly, against a slew that could be a telescope drive.

Both live in `formlab/rig.py` (`Rig`), which every clearance ruler samples
and `tools/test_motion.py` checks against what each vocabulary promises; the
constants are at the top of the file. Since PLAYERS M1 a mallet's stroke is
planned by `formlab/stroke.py` (its constants at the top of that file), which
the rig consults for `kind == 'mallet'` and `tools/test_stroke.py` checks on the
rig. The harness plays a bake of it
(`formlab/bake.py`; `docs/clockwork-build.md`, "The motion bake") and owns no
motion of its own. Until 2026-09-28 a GDScript mirror, `ClockworkMotion`,
recomputed all of this in the harness; the history below names it where it
did.

## Stepped: mallet (and hammer) arms

Since PLAYERS M1 (`docs/goals/the-players.md`) the two stepped kinds no longer
share a stroke. A **mallet** (`kind == 'mallet'`: the bars and the bells) is
planned by `formlab/stroke.py`: its carriage travels contact to contact under a
head that rides its own rebound. The **hinged hammer** (`kind == 'hammer'`,
`blocks_arm0`) keeps the ratchet clicks and the cocked drop described below
until M5. `Rig.mallet(aid)` is the switch every M1 branch keys on;
`Rig.stepped(aid)` stays true for both.

**A mallet's carriage steps or freewheels.** A move of `dx` along the rail is
`teeth(dx)` teeth of the rack (pitch 2π·0.12/16 = 47 mm, the pinion's), and
its unit is the *3 g step*: one tooth as a 3-4-5 at 3 g over `STEP_MOVE`
(60 %) of its period, then a dwell on the detent — `motion_timing.step_period`,
0.160 s a tooth on the bars and 0.159 s on the bells. How a travel crosses is
one rule, `motion_timing.travel_regime`, which the planner's want and the
stroke both ask. The travel **steps** when its free window holds
`teeth·step_period`. The window opens at the carriage's earliest start, the
score's `go` (`t_move`, never before the previous contact), and closes at the
next contact where the head goes straight on to its next stroke (a tempo
float or a Dahl loop, below), or at the cocked hold's start where the head
parks — a hold note's regime is `travel_regime(dx, hold start − go)`, so the
coda's tolls step. The travel segment declares that window as
`extra['window']` = (go, hold start) or (go, contact), and `ArmStroke.travels`
carries it as `window`; ruler 19 recomputes the regime from it and checks the
window itself against the score (w0 at or after `t_move`, w1 a hold start or
the contact). It steps at
`stepped_period` a tooth — the room a tooth, at most `P_MAX` (0.2 s), never
under the step period. Otherwise it **freewheels**: one move over the whole
window, ẋ = ẍ = 0 at both ends, a 3-4-5 or a **glide** (`GLIDE`, below: the
3-4-5's halves about a cruise). A contact travel takes the share whose *tool*
speed — the carriage plus the head already planned to the contact, on the
arc — has the least 8-norm over the window, sampled every 2 ms
(`_Planner._contact_glide`), skipping a share whose halves would pass 3 g; a
hold note's freewheel is coordinated with its wind-up instead (below). The
head's downstroke into the contact, 3.0 to 3.75 m/s at its peak, dominates
that norm, so the shares differ by 2 % at most and the glide works on the
travel's first part: on bars_arm1's +0.386 m tempo leaps (0.357 s) a 0.4
glide lowers the tool's peak before the apex from 2.05 to 1.78 m/s. A glide's
shorter decelerating half leaves more carriage speed under the downstroke, so
at tempo the pick follows the downstroke's peak: 0.4 up to 3.1 m/s, 0.2 to
3.45, 0 above. The bars'
contact freewheels take 0 on 16, 0.2 on 2 and 0.4 on 2 (bars_arm0; twelve of
the sixteen are hurried 0.771 m leaps, already at 3.56 g, where no share
holds 3 g) and 0 on 13, 0.2 on 2 and 0.4 on 5 (bars_arm1, two of them
hurried); every glide is on a +0.386 m tempo leap, 0.6 wins none, and the
bells have no contact freewheel. Against the plain 3-4-5, bars_arm1's frames
over half an extent outside the hurried travels, impulse frames and strike
windows fall from 74 to 65 and bars_arm0's from 11 to 8 (the brisk travels
kept in); ruler 1's gated p95, brisk travels out, is 0.382 (bars_arm1) and
0.389 (bars_arm0) either way. Either way the carriage never leaves before
`go` and has arrived by the contact, or by the hold where there is one. A
freewheel whose 3-4-5 at 3 g and one head extent a frame does not fit the
window it actually runs in, [ta, tb] (`ArmStroke.travel` judges it there,
not on the contact-to-contact gap), is *hurried* (`motion_timing.hurried`)
and may run at up to 5 g and 1.5 extents a frame; one shorter than the
3-4-5 at those ceilings (`contact_floor_s`) is recorded as the issue
'freewheel below the hurried ceilings' (none today). A stepped or homing
travel is never hurried. Today twelve are hurried on bars_arm0, two on bars_arm1,
none on the bells, the worst at 3.56 g. The bars mostly play at tempo, so
they mostly freewheel — on the chamber bars_arm0 steps 3 travels and
freewheels 23, bars_arm1 2 and 32; on the expanded asset the bells, with
longer gaps, step 5 and freewheel 4 (bells_arm0) and step their one travel
(bells_arm1). The stroke
blends the contact's y and z on the carriage's own law between contacts, so
a contact is exact even where two differ; today every mallet contact shares
y 1.35 m and its mechanism's z, so only the rail axis travels.

**Every stepped landing rings.** Each step lands on its detent and rings on
the pawl — a damped sine of `OVERSHOOT`·PITCH (4.7 mm) at `RING_HZ` 14 Hz
decaying in `RING_TAU` 90 ms, in the direction of travel — faded by a 3-4-5
from halfway through the dwell (`RING_FADE`), so it is spent, C², before the
next step moves and exactly zero at the travel's end. The ring is not path:
the scored x is ring-free, `Rig.carriage_x(aid, t)` is that x plus the ring,
and `pose()` puts the root there (`root.x = carriage_x`, without the recoil's
x ring) while the tip carries both rings. Measured, the ring peaks at 0.83 of
`OVERSHOOT`·PITCH; `tools/test_stroke.py` holds every stepped travel's
overshoot on `carriage_x` to 0.3–1.0 of it. A freewheel has no dwell and so
no ring.

**The hammer's carriage is still a ratchet.** A move of `dx` is `teeth(dx)`
teeth taken one a click at 90 ms a click when the score leaves time; when it
does not, clicks come no faster than 40 ms and each spans several teeth. A
click spends its first 40 % moving — a minimum-jerk step to a tenth of a
tooth *past* the detent (the pawl's play, 4.7 mm however many teeth the
click spans) — and rings out on the pawl at 14 Hz with a 90 ms decay, faded
to nothing before the next click so the carriage sits exactly on the detent.
The arm's y/z follow in one minimum-jerk move over the same window, so
only the rail axis clicks. `test_motion` checks the carriage sits within
the pawl's play of a detent at least half the time, that each travel
crosses exactly its planned number of detents, that the overshoot stays
within 4.7 mm and that every travel lands exactly. (Every mallet moved this
way until M1.)

**The click has a mechanism.** Under each mallet arm's pinion a sprung
roller detent pawl rides the teeth (`formlab/pawl.py`; `docs/articulated-arms.md`,
"The carriage and its drive"): as the carriage moves a tooth along the rack
the disc turns a tooth and the roller rides over a tip and dips 15.5 mm into
the next gap, so every step is a visible drop of the pawl, and the recoil's
shudder along the rail ticks it back and forth. A freewheeling carriage goes
faster than the spring can return the roller into each gap: above
`PAWL_RIDE`, 15 teeth a second (0.71 m/s of carriage), the pawl *rides* the
tips instead of dropping. `Rig.pawl_ride(aid, t)` says how far, in [0, 1] — a
smoothstep of the tooth rate |ẋ|/PITCH from 12 to 18 teeth a second, zero at
rest and at every contact. It applies on freewheel travels only. A stepped or
homing travel stops on every detent, so its pawl has the dwell to fall into
each gap: its ride is 0 whatever the step's peak rate. The bake leans the pawl by it from the
table's angle toward `pawl.ride_angle`, the tip-land angle (the table's
minimum, −11.5°): `formlab.bake.Bake.pawl` is
`lerp(pawl_angle(root.x + phase), ride_angle, ride)`. `ClockworkMotion.pawl_angle`
mirrors `pawl.angle` (5e-13 rad) and `performance.gd` poses the part. The
roller turns as it rolls on the tips (2.8 rad a tooth, the other way from
the disc), and the pinion is spun with a phase that seats the roller in a
dip when the arm parks at its home — a detent rests in a dip. The score's
other rests are wherever its contacts put the carriage, so away from home
the pawl parks on a tip or a flank as often as in a gap; that is honest
(the tool must reach the contact), and `tools/test_pawl.py` counts how many
rests seat anyway.

**The click has a sound.** `Rig.click_times(aid)` lists a stepped arm's
clicks. A mallet's are one a tooth, `(t, 1.0)` each: a freewheel's where x
crosses the middle of each tooth, (k + ½)·|dx|/teeth from where it set out
(found by bisection on the 3-4-5), each labelled 'drop' or 'ride' by the
tooth rate at that instant; a stepped or homing travel's at each landing,
where the pawl drops. (In the declared structure a stepped click's knot sits
at the step's start with `t_end` its landing, so a ruler sees the step's move
as an interval, and a 'detent' knot marks the landing; a freewheel's click
has no `t_end` — it is sound, not a path impulse.) The hammer's are as they
were: one at the landing of each of a travel's `n` clicks,
`go + (k + CLICK_MOVE)·T/n`, the moment the roller drops onto the next tooth
in `ratchet`. The bake carries, beside each arm's `clicks`, `click_pawl` (1 a
riding click) and `click_step` (1 a stepped, homing or hammer click), so the
lighter riding click can be told from the drop. On the chamber bars_arm0
clicks 426 times (304 freewheel, 290 of them riding), bars_arm1 403; on the
expanded asset bells_arm0 210 and bells_arm1 42. A freewheel's clicks come
as close as 11.9 ms — faster than a 60 fps frame — while stepped clicks are
at least 159 ms apart. `performance.gd` plays a click sample from a player that
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
every click inside its travel, no two stepped clicks (`click_step` 1: a
mallet's stepped or homing click, or the hammer's) closer than
`CLICK_MIN_S`, and the hammer's count to the schedule's `clicks(dx, T)` per
travel. A mallet's freewheel clicks are under that floor by design.

**A mallet rides its bounce.** A mallet's head no longer lifts and drops
over the score's approach window. It is planned note to note as two scalar
channels of closed-form polynomial segments in t: `h(t)`, the head's height
above the contact, and `x(t)`, the carriage. The head point is
p(t) = (x, y_c + h, z_c + σ·Z(h)), where Z is the arc the M5 hinge will make,
Z(h) = (ρ/k²)(√(1 + (kh/ρ)²) − 1): vertical at the contact and leaning toward
the arm's own root (σ = sign(root_z − z_c)), with ρ = 0.16 m and k = 1.2 for
every mallet arm (`stroke.ARC`). A head at the 0.22 m hover sits 0.103 m
toward its root (so `Rig.hover` leans with it), and at the 0.50 m prep
ceiling 0.32 m. The declared virtual pin is the contact plus `R_PIN` (0.40 m)
toward the root at contact height, axis along the rail; ruler 10b judges each
downstroke's curvature toward it in the y–z plane. Every segment runs under
one of four laws — '3-4-5' (rest to rest), 'quintic hermite' (position,
velocity and acceleration given at both ends), 'ballistic' (constant
acceleration) and 'hold' — every join is C², and the velocity jumps only at
a contact, by the declared impulse (0, (1 + e)·v_in, 0). Like everything else
it is a pure function of t, and the bake samples it.

**How hard and from how high come from the score.** The strike speed is
v_in(a′) = 2.5 + 1.26·√a′, 2.50–3.76 m/s, with a′ the note's amplitude
normalised over its voice exactly as `tools/players/core.py` does it (a voice
with a single amplitude counts as 1.0). The *prep*, the height the downstroke
starts from, is h(a′, IOI) = (0.15 + 0.125·a′)·g(IOI), capped at 0.50 m, with
IOI the gap to the note being prepped: g = √(IOI/0.357) below 0.357 s, so
faster is lower, then a monotone cubic in log IOI rising to 2.0 at 1.2 s and
beyond (and for a first note, which has no IOI). At IOI 0.357 s that is
0.15–0.275 m; long gaps reach 0.30–0.50 m, and the coda's tolls are simply
long-IOI notes with a high prep — no time window of their own. Measured on
the bars, preps run 0.17–0.50 m. That function is what
`Rig.declared(aid).prep` returns, so the rulers judge the stroke against the
prep it was planned from.

**The downstroke is thrown.** A quintic hermite from the apex arrives at
−v_in still accelerating down at 4 g (`A_END_G`), so the felt meets the bar
at its fastest and the hit lands exactly on the scored time. From rest it
takes `T_DOWN_LONG`, 150 ms, lengthened linearly toward 250 ms as the prep
grows from 0.275 to 0.50 m and further in 5 ms steps until the head falls
strictly all the way, the gravity scale s = g·T²/(2h) is at least 0.25 (the
stroke is driven, not dropped) and the tool stays under 10 g outside ±10 ms
of the contact. Measured, T_down runs 125–250 ms.

**At tempo the rebound leads.** At an IOI of 0.6 s or less (`FLOAT_IOI`) the
head leaves the bar on its rebound, e·v_in upward, and floats ballistically
under a_f straight to the next note's apex at t_next − T_down, where the
downstroke takes it: the float *is* the gap, with no pause anywhere. T_down
is chosen on a grid (0.35–0.45 of the IOI up to 0.5 s, else 125–250 ms) to
bring e toward 0.55 and T_down toward 0.40 of the IOI, holding e in 0.3–0.8,
a_f in 0.5–1.5 g and s ≥ 0.25; a note that cannot is recorded as an issue,
not hidden. Measured, e runs 0.45–0.79 on the bars.

**Longer gaps bounce and wind up.** Above 0.6 s a float that ended at
the next downstroke would rise too high (a ballistic float at 0.5 g or more
rises over 0.28 m once the IOI passes 0.59 s), so the head bounces freely
instead and the rebound leads the rise. Every rise from a contact to the next
apex either **flows** or **rests**, never hitches (ruler 8's '8 rise'): a flow
rises throughout, never past the prep, and its speed never sags below 0.6
(`FLOW_K`, ruler 8's 0.5 plus margin) of the lesser of its peaks before and
after; a rest is caught at the top of its flight without reversing (no
bob), or dips genuinely low (1 cm or more), and holds the head still for at
least 0.25 s (`REST_MIN`) before a wind-up from rest. The float always hands
over to the driven rise or to the apex catch *before* its apex, still
rising, C2. Then:

- a gap under 0.8 s (`HOLD_GAP`) is a **Dahl loop**, one flowing gesture:
  the rebound floats at −a_f and hands over at t_w, still rising, to one
  quintic **Dahl wind-up** from (h_w, v_w, −a_f) to the prep at −0.5 g
  (`A_TOP_G`), flowing into the downstroke without stopping. `dahl_float`
  picks (e, a_f, t_w) on a grid — e and a_f one step inside e 0.3–0.8 and
  a_f 0.5–1.5 g (ruler 8 reads a_f on the rendered face), t_w on 24 points
  (`FLOW_N`) from 20 ms (`FLOAT_MIN`) to the float's apex and by half the
  IOI (`DAHL_RISE_BY`: ruler 21 reads an accent's rise from the declared
  wind-up's start) — the point whose whole rise flows with the least peak
  head speed on the arc. On bars_arm0 at a′ = 1 (prep 0.459 m, IOI 0.714 s)
  that is e 0.50 under 0.52 g, handed over at 68 ms (91 mm up) to a 0.414 s
  wind-up: peak 1.49 m/s, least valley 0.88 (the old float to its apex, e
  0.69 under 0.84 g, peaked at 2.08 m/s and all but stopped, 0.4 mm in a
  frame, before the wind-up threw it on). At a′ 0.12–0.17 (0.277–0.285 m)
  it is e 0.31 under 0.62–0.64 g, handed over at 20 ms (17 mm up) to a
  0.54 s wind-up: its peak from the contact + 5 ms is the launch itself,
  0.90 m/s (was 1.08–1.13); the speed then sags to 0.52–0.55 at 133–140 ms
  and the wind-up's own peak is 0.70–0.73 at 333–342 ms; valley 0.82–0.83
  (of h′, as `_valley` reads it). On the 30 fps grid the head steps 3–46 mm
  a frame at a′ = 1 and 3–28 mm at the low a′, easing only into the apex. Where
  nothing on the grid flows the true R is returned and the issue 'Dahl loop
  out of bounds' recorded (none today);
- a gap of 0.8 s or more bounces at e = 0.45 under 1 g (`E_LOOP`) — its
  apex (e·v_in)²/2g, 65–146 mm — into a rise to a **park** at the prep, of
  one of three shapes. A **flow**: the float hands over (20–84 ms after the
  contact) to one quintic to the park. A **coast**: the float hands over to a
  cubic ease (at least 20 ms, `EASE_MIN`) to a constant speed, coasts, and
  stops on a quintic whose length sets its in-position instant to the
  carriage's (below). A **rest** is an **apex catch** (`_top_catch`, the
  head segment 'catch'; the goal's A11): the arm takes the head at the top
  of its flight. The float hands over, still rising, D = 0.45·(t_f − 5 ms)
  before its free apex t_f = v0/a_f (`TOP_SHARE`: at 0.45 of ruler 8's
  launch speed v(t + 5 ms), against its 0.5, so the free flight carries
  81 % of the height), at (h_c, a_f·D, −a_f), to one quintic hermite to the
  rest (h_r, 0, 0). Its deceleration is a(s) = −a_f·[(1 − s) + √3·s(1 − s)]
  over T = D/(½ + √3/6) ≈ 1.27·D (s = τ/T): the speed integral gives
  v_c = a_f·T·(½ + √3/6), the distance exactly v_c²/2a_f, so the head
  rests exactly where the free bounce would have turned, h_1 = v0²/2a_f. The
  quintic hermite on those six end conditions over that T *is* this quartic
  (its fifth-order coefficient is 0): it never reverses (a ≤ 0, v ≥ 0, no
  bob), joins C2 at both ends (its jerk −0.73·a_f/T at the handover), and
  brakes at most 1.077·a_f (at s = 0.21). Where that would be shorter than
  two frames (`TOP_MIN_T`), or brake harder than 1.4 g (`TOP_BRAKE_G`,
  never at a_f = 1 g), T is lengthened along the same quartic family,
  a(s) = −(1 − s)(a_f + b·s), and the head rests a little above h_1.
  Measured on the 21 expanded rests (chamber's 7 are expanded's bars rests;
  all at e 0.45 under 1 g): the catch
  takes the head 49–75 ms before the apex at 0.48–0.74 m/s, lasts
  66.7–95.6 ms (2.00–2.87 frames; the nine at a′ = 0 lengthened from 1.88
  frames), peaks at a 1.03–1.08 g brake, and rests at 65–146 mm, at the
  ballistic apex (the a′ = 0 rests 0.6 mm, 0.9 %, above it); ruler 8 reads
  the rest at 1.00–1.01 of the ballistic apex. At 30 fps an a′ = 0 rest
  climbs 32, 21, 10 and 2 mm and is still, where the free flight would have
  gone 32, 21, 10 and then −0.6 (the old cubic settle crept on, 13, 6, 2 mm, to
  10.5 mm above the apex; '8 float' and '8 bounce apex' could not read it).
  The head holds there at least `REST_MIN` and winds up on a 3-4-5 that lasts
  max(0.30 s (`W_RISE`), rise / 0.6 m/s (`W_RATE`)), shortened toward six
  frames and 10 ms (`W_MIN`) only where the room needs it; a rest sits at
  most 0.6 of the prep (`H_LOW_PREP`, ruler 3's wind-up from rest). Every
  hold note's rise is chosen by one rule, the goal's (A11): the least peak
  of the tool's speed in the world — the vector sum of the carriage's x and
  the head's arc — from the contact + 5 ms (`RISE_SKIP`) to the hold; a
  rest within 0.01 m/s (`PEAK_TIE`) of the best wins, so the head waits low
  through a long gap rather than parking high; then the least 8-norm of
  that speed. Where the carriage does not move under the rise (a park, an
  'S2 step', the coda) `_rise_alone` applies it to the head's speed on the
  arc, which is then the world speed (an 'S2 step' steps only after the
  rise, under the parked head, at 0.89–0.92 m/s, below every rise's launch
  of 1.30–1.64). Measured, bars_arm0's three 1.43 s parks flow (peak
  1.30 m/s, the float's launch, against the rest's wind-up at 1.38) and
  every bells park and 'S2 step' rests (4.3–18.6 s gaps: outright on the
  4.3 s parks, 1.41 against a flow's 2.31 m/s, and on a tie at the float's
  launch on the longer ones). The
  rise always *ends* where the head must be parked — at the cocked hold, or
  at the start of the stepped traverse that runs under the parked head. The
  carriage crosses under the parked head, then the head holds **cocked** for
  0.12 s (`HOLD`, at least three frames) over a still carriage and throws
  the downstroke from rest. The carriage has finished before the cocked hold
  begins, because ruler 21 wants the head still in 3D, within 1 mm, through
  it. Where a stepped traverse fits between the rise and the hold it runs
  there ('S2 step'); where it fits only from `go`, it is a **step under the
  loop**, the coda's toll (`_Planner._under`): the traverse fills its window
  from `go` at `stepped_period`, under the bounce loop, and the head climbs
  under its steps. The float hands over, still rising, C2, to a **coast**
  (the ease, the steady speed, the stop) whose stop puts the head at the
  prep in position with the traverse's last landing, at `hold start − (1 −
  STEP_MOVE)·period`, then parks to the hold start. Ruler 8's '8 low rest'
  wants no head still (under 0.05 m/s) more than 1 cm below its park while
  the carriage moves, so the coast climbs at 1.1 times that or more
  (`UNDER_K`). That decides the float: at the loop's e 0.45 under 1 g the
  bars' 4 s tolls would coast at 0.029–0.048 m/s, under the line, so the
  toll's float takes `dahl_float`'s (e, a_f) grid and the rule above, the
  least world peak. The least rebound has the least peak and the highest
  coast: e 0.31 under 1.48 g on every toll. Measured, bars_arm0 (71.429 →
  75.714 s) floats 57 ms to 36 mm, eases for 21 ms, coasts 3.85 s at
  0.068 m/s (2.3 mm a frame) and stops in 15 ms at 0.300 m with the last of
  its 25 landings; bars_arm1 (68.214 → 72.857) coasts 4.16 s at 0.059 m/s
  (2.0 mm a frame); the bells (74.286 → 77.143, 68.571 → 71.429) 2.28 s at
  0.19 m/s (6.4 mm a frame) to 0.500 m. Head and carriage are in position
  within 0.14 ms of each other; the tool's world peak falls from 1.62–1.67
  to 0.98–1.08 m/s. (The old toll caught the head low, at half the float's
  apex, and held it there 1.4–3.6 s while the carriage stepped: ruler 8's
  '8 low rest' counted 21, 23, 9 and 9 waits on bars_arm0, bars_arm1,
  bells_arm0 and bells_arm1.) Where no coast reaches `UNDER_K` the
  fastest is taken and 'coast under the loop too slow' recorded; where none
  fits at all the head is caught low (`H_LOW_UNDER`) and 'no coast under the
  loop' recorded (neither today).
  A **freewheel** to the hold is coordinated with the rise instead
  (`_Planner._coordinate`): the tool's speed is the vector sum of the
  carriage's x and the head's arc, so of the shapes rulers 22 and 8 allow the plan
  takes, by the rule above, the one whose world speed peaks least from the
  contact + 5 ms, a rest within `PEAK_TIE`, then the least 8-norm over the
  gap (`COORD_P`, sampled every 2 ms, on a 25 × 25 grid of start times).
  Four hold notes tie a rest in the world and rest, on the apex catch:
  bars_arm0's 53.214 and 64.643 s 'S2 freewheel's (1.636 m/s, the float's
  launch; 8-norm 1.144 → 1.213) and 57.143, now an 'S1 freewheel' whose
  carriage leaves 97 ms into its 1.36 s wind-up from rest (1.415 m/s;
  0.844 → 1.076, glide 0.6 → 0), and bars_arm1's 59.643, a forced late
  `go`, at the freewheel's own 2.969 m/s (2.316 → 2.318). No shape may leave the head waiting under the moving
  carriage (ruler 8's '8 low rest': still more than 1 cm below the park
  while the carriage moves at over 0.01 m/s, `LOW_REV` and `X_MOVING`, for
  over half a frame, `LOW_WAIT`); a wind-up from rest that leaves *with*
  the carriage does, 79 ms at 57.143, its 3-4-5 under 0.05 m/s while the
  carriage's passes 0.01, so there the carriage leaves once the head is
  under way (0.038 m/s). The shapes: the
  carriage leaves under the rising head (from `go`, while the head floats or
  rises at 20 mm/s or more, `COORD_MOVING`) and a flowing or coasting rise
  arrives with it at the hold ('freewheel under the loop' when it leaves
  before the float hands over, else 'S1 freewheel'); a rest whose wind-up
  is under way when the carriage leaves, or leaves with it ('S1
  freewheel'); or the head flows or rests and parks first and the carriage
  crosses under it ('S2 freewheel'). After a contact the head is never left
  waiting below its park while the carriage moves (ruler 8's '8 low rest',
  0 waits on every mallet arm); parked at the prep it may be still under a
  moving carriage ('S2'). Ruler 22 times a channel's start only from rest and
  wants every moving channel to arrive together, within 1 µm of its end within
  1/480 s of the others (`ARRIVE_POS`, `ARRIVE_SKEW`: half of ruler 22's
  SKEW_MAX, 1/240 s, between continuously bisected in-position instants;
  measured ≤ 1.6 ms of its 4.2, the tolls' 0.03). A
  one-piece flow syncs only where its own in-position lead (4–6 ms on
  bars_arm1's 1.07 s gaps) happens to match the carriage's; the coast's stop
  is sized for the carriage's lead instead, its jerk at arrival
  6·`ARRIVE_POS`/lead³, so it arrives with any freewheel by construction,
  and its steady middle keeps the tool's speed low. The freewheel may **glide**
  (`GLIDE`, a share of 0, 0.2, 0.4 or 0.6): a 3-4-5's accelerating half, a
  cruise over that share of the travel, the decelerating half, each half at
  3 g or less, C2 at both joins (a 'quintic hermite', a 'ballistic' at
  a = 0, a 'quintic hermite'). 0.6 takes 17 of the 19 hold freewheels
  (bars_arm0's 2 of 3, bars_arm1's 11 of 12, bells_arm0's 4; bars_arm0's
  57.143 takes 0 and bars_arm1's 59.643 0.2); with the shares capped at 0.4
  those took 0.4, and bars_arm1's ruler-1 gated p95 was 0.373 against 0.379
  with 0.6 (the plan minimises the peak and then the 8-norm, not the p95;
  both pass; it is 0.382 now, bars_arm0's 0.389). The coordinated shapes
  need a level contact pair (every mallet contact shares y and z today): a
  sloped one would move
  the head's y and z with the carriage, untimed, so the planner raises
  rather than plan it. In practice every freewheel under the loop coasts
  (bars_arm1's 11, bells_arm0's 4: the head a steady 0.16–0.41 m/s, 5–14 mm
  a frame, for 0.48–0.83 s): a rest's wind-up riding the freewheel peaks
  0.04–1.30 m/s higher in the world on bars_arm1 and 0.011 on bells_arm0,
  just past `PEAK_TIE`.

**The first note comes down from the hover.** After its homing sweep (below)
the head rests at the hover, 0.22 m over home on the arc. The first travel's
regime is `travel_regime(dx, hold start − go)`, and a stepped one ends at
the hold start, so it leaves at `ta`. The head waits at the hover until the
first rise's length before `ta` — `FIRST_RISE_S` (0.7 s), or longer where its
wind-up, from the dip's floor to the prep over the rise's last 65 %, wants
`W_RATE` (0.6 m/s), as far as the room after homing allows — then makes an anticipatory **dip**
(`FIRST_DIP`): a 3-4-5 over `FIRST_DIP_FRAC` (35 %) of that rise, to
0.15·(prep − hover) below the hover (never under `FIRST_FLOOR`, 50 mm). A
3-4-5 **wind-up** to the prep (the long-gap prep, since a first note has no
IOI) follows, ending at `ta`. The carriage then crosses under the parked
head, the head holds cocked and strikes. On bars_arm0 (a 0.825 s rise) the head
dips from 41.93 s, winds up from 42.21 to 42.75 s and parks, and the carriage steps
16 teeth from 42.75 to 45.34 s; the first note is at 45.714 s. **After the last note** the head
rides one bounce loop (e 0.45 under 1 g) into a raise to `H_END`, 0.42 m (at
least 1.5 times the tempo apex), and parks there: the rise is chosen as a
park's is, a flow or an apex catch, a rest of at least `REST_MIN` and a 3-4-5
over 0.6 s (`END_RAISE_S`). Measured, every mallet arm's coda rests (the raise
ending 0.98–1.04 s after the last contact).

Each mallet arm has one step under the loop, a long traverse whose steps fit
the window from `go` but not after a rise to the park: bars_arm0 at
75.714 s (25 teeth of 160.2 ms from 71.429 s), bars_arm1 72.857 (25 of
162.4 ms from 68.516), bells_arm0 77.143 and bells_arm1 71.429 (14 of
159.1 ms). It is a style, not an issue. The stroke now records no
issues on any mallet arm.

**The hammer's strike is still a cocked drop.** Over the score's approach
interval the arm first rises half its lift again (by 40 % of the interval,
smoothly) and then falls with `1 − v²` — the acceleration of a fall,
arriving at its fastest — so the hit lands exactly on the scored time with
nothing rubbery about it. The release lifts back on a quintic. (Every mallet
struck this way until M1, rising to 0.33 m over the bar.)

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
decay — the pinion ticks back and forth with it) and the mallet rings across
the bar (2.5 mm, 17 Hz, 100 ms). Both are zero at the blow itself and gated
to zero over the 80 ms before the next stroke starts — for a mallet, the next
note's apex `t_apex`, where its downstroke begins — so every scored contact
is still exact to 1e-9 m and the ring never smears a hit. The mallet used to
bounce above the bar on its recoil too (6 % of the lift, 8 Hz, 160 ms, an
`|sine|` always upward); that is retired, because the head's rebound is now
the scored float with its own declared e. (`RECOIL['bounce']` stays
importable, and nothing applies it.) The bars' own bounce (`performance.gd`)
plays under it.

**And it shakes the assembly around the arm.** The arm alone answering its
own blow left the instrument stand, the guide bars and the gantry rigid — a
felt head on a 5 kg bar over a wooden trestle, and nothing under it moves.
Every blow now goes on a **recoil bus** (`ClockworkMotion._bus`,
`Rig._bus`): one entry a hit, carrying where it landed along the rail and
how hard, and the moment its arm's next strike begins, which gates its ring
exactly as `recoil` is gated. For a mallet *how hard* is the score's
amplitude, the next strike begins at the next note's `t_apex`, and each blow
also carries the stroke's `v_in` and `e`; for the hammer it is still the
amplitude times its cocked drop's height (1.0 for a full blow,
`BLOW_DROP_REF`), gated at its next approach. Three rigid-body shudders read
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

**A mallet arm homes before it plays.** In its first rest each mallet arm
sweeps its whole reach and both of its joints and lands back on its home
detent (ruler 22, "home"). The carriage goes home → lo → hi → home tooth by
tooth at the step period — a 3-4-5 step, a dwell, a detent ring and a drop
click each tooth. Then, at a still x, the elbow sweeps e0 → e0 − 0.425·span →
e0 + 0.425·span → e0 and the shoulder 0 → −3° → −3° + 0.85·span → 0, each
three single-joint 3-4-5 legs, with the head held at the hover. The joint
legs are turned in joint space from the arm's cfg *at pose time*
(`Rig._home_joints`, cached per cfg tuple; the rig's per-cfg caches,
`_spans` and `_hj`, hold at most 64 cfgs, `rig._cfg_cache_n`), because the rail search mutates
the cfg per candidate and a cached tip path would be wrong; their angles and
spans are ruler 16's, and `tools/test_stroke.py` holds the two bit-equal.
Where the joints sweep is a site rule (`stroke.joint_site`): at home, unless
home is within 0.3 m in x of another mechanism's reach window, then at
whichever end of the arm's own x path is farther from it — so bells_arm1,
whose home is 9 mm from harp_arm0's reach, sweeps at −1.475 m. The planner
charges the whole window (`motion_timing.home_legs`: 1.65 s for the elbow
and 0.9 s for the shoulder, one value a kind, sized for the worst arm); at
pose time the Rig re-splits it between the two joints by tool path length,
so every leg peaks at the same tool speed, 1.29–1.45 m/s against a bound of
0.5·`SERVO_V_MAX` (1.5 m/s). The arms of a mechanism home one after another
from `HOME_T0` (0.25 s), and a sweep must end `HOME_GAP` (2 s) before the
first travel of any arm of its mechanism: bars_arm0 sweeps 0.25–13.26 s,
bars_arm1 13.26–26.26, bells_arm0 0.25–11.71 and bells_arm1 11.71–18.71,
2.26 s before bells_arm0 first leaves at 20.97. Every arm covers its reach
(1.005–1.012 of `reach_x`) and 0.85 of each joint's span, and lands to
1e-9 m.

**What a mallet declares.** `Rig.declared(aid)` returns the stroke's own
account of itself (`formlab/segments.py` `Declared`, `native = True`); every
other arm still gets its schedule read back (`segments._today`). It holds:

- **segments**, each with its law, tag and an `extra`: on the head channel
  'float', 'catch' (a rest's apex catch), 'rebound' (the low catch), 'wind-up', 'hold' (`extra['hold']` 'park'
  or 'cocked'), 'stroke', 'raise' and 'home'; on the carriage 'travel',
  'hold' and 'home'. Each channel covers (−∞, +∞) with no hole and no
  overlap. `extra` carries the channel, the declared peak `jerk` (m/s³, of
  the channel's own 3D path, the arc's chain-rule terms included — computed
  from the law's closed form on its boundary data, `stroke.law_coef` and
  `stroke.head_jerk`, never sampled back off the path; ruler 6c rebuilds the
  same closed form itself, a glide's hermite halves and cruise included, and
  fails a declaration below it), `pin` and
  `axis` on every stroke, `regime` ('step', 'freewheel' or 'home'), `travel`
  (an id grouping a stepped travel's teeth) and `hurried` on carriage
  travels (and `glide`, the cruise share, on a gliding freewheel's pieces),
  `joint` on homing legs, and the boundary values every law needs to be
  rebuilt: `p0, v0, a` on ballistic, `p0, p1` on 3-4-5 and `p0..a1` on
  hermite segments;
- **knots**: 'contact' at every hit with its dv; 'click' a tooth with
  `k, n, regime, pawl, travel` (and `t_end` only on stepped and homing
  clicks); 'detent' at each stepped landing (dv zero on the ring-free path),
  with `extra['sign']` (the travel's direction) and `extra['fade']`, the
  (start, end) of its ring's 3-4-5 fade, so ruler 20 rebuilds the detent ring
  exactly from the declaration;
  'smooth' at every other join of either channel;
- **rings**: recoil.x and recoil.z on the tip, the stand thump, the rail
  sag, the mast sway and the detent ring on root.x — no recoil.bounce;
- **prep**: h(a′, IOI) above.

On the expanded asset that is 413 segments and 795 knots on bars_arm0, down
to 141 and 172 on bells_arm1. The plan behind it is `Rig.stroke(aid)`, with
per-note records (t_apex, T_down, v_in, e, a_f, h, the regime and the travel
window) and the travels; the schedule rows gain `t_head_free`, `t_apex` and
`arrive`.

**What the bake carries.** The motion bake is still `loam-motion/1`, and M1
only adds to it. A mallet is sampled at the 240 Hz grid plus every declared
knot and segment boundary and every hit, plus the instants a freewheel's
tooth rate crosses each eighth of the ride band (`stroke.RIDE_ROWS`,
`ArmStroke.ride_times()`), so the straight lines between rows follow the
`ride` smoothstep (rows closer than 1e-7 s merged, a hit's time kept
exactly). The hammer keeps its rows through each ratchet click. Each stepped arm gains a `<aid>.ride` channel (all zero on the
hammer), each arm's record `click_pawl` and `click_step` beside `clicks`, a
mallet's blows `v_in` and `e` (with `gate_end` the next `t_apex`), the pawl
table `ride_angle` and the constants `PAWL_RIDE`. `formlab.bake.Bake.ride`
reads the channel back. Between rows the baked mallet tip stays within
0.2 mm of the rig, against a 5 mm tolerance.

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

`t_move` is when the arm leaves — the one answer, decided once, in the
planner. It starts repositioning the moment it is free and the move wants,
and then waits over the bar: the hammer clicks into place during the rest,
the servo slews unhurriedly instead of snapping in the last 50 ms. A mallet
is free at the contact itself (`t_head_free`), because its head rides the
rebound, so its carriage travels contact to contact under the float and has
arrived by the time the head lands (`motion_timing.arrive_lead` is 0).

What the move *wants* is `loam/motion_timing.py`, and both worlds ask that
one module. The hammer wants a click a tooth (`teeth(dx) × 90 ms`). A mallet
wants a 3 g step a tooth and then a still carriage under its cocked hold and
its longest downstroke: `contact_travel_s(dx) + STILL_S`, with `STILL_S`
0.37 s (the 0.12 s hold and a 0.25 s T_down), so a want that is met leaves
exactly a window `travel_regime` calls 'step'; a mallet's repeat on the same
bar moves at `max(t_head_free, t − 0.37)`. A servo wants its S-curve's ramps
(0.4 s) or longer if the distance needs it at the carriage's rate. The
planner charges each reposition that time over
the distance the contact geometry gives it — `_Solver.travel`, the score's
axis coordinates times `WORLD_SCALE` — and an arm that does not have the
room is charged everything the score left it instead, down to a hard floor:
a ratchet click may not come faster than `CLICK_MIN_S` nor span more than
`CLICK_TEETH_MAX` teeth, a mallet's travel may not beat the 3-4-5 at its
hurried ceilings (5 g, 1.5 head extents a frame: `contact_floor_s`), a servo
may not beat `SERVO_V_MAX`. Below that the
contact is refused and the composer hears about it. `Actuator.travel_s`
survives only as a per-index floor for a mechanism with no usable spacing.
A mallet mechanism's homing sweeps are charged too (`_Solver.home`, the
`home` cues in the score), and a sweep that does not fit is not made, so it
never costs a note.

Because `t_move` is now physical, there is **one occupancy model**, not
two. The planner (`_Solver._separated`) promises two arms of one mechanism
stay `arm_clearance_m` apart along x in three phases a contact: while it
crosses, an arm owns the whole interval between where it left and where it
lands; on arrival it owns only the strings it is playing; afterwards a
point over its last contact. A candidate whose crossing is in a sibling's
way is not refused but *delayed* — `_Solver._push` waits and crosses in
what is left, down to the floor. `formlab.rig._schedules` and
`ClockworkMotion._schedules` re-check exactly that model, padded by the
overshoot and recoil (10 mm), and `Rig.pushed` records any start they have
to move; `test_motion` insists it is empty, which is what "one model"
means in practice. `dev/test_clockwork.gd` and `test_motion` measure the
rendered result against the promise itself.

The bill for honesty is notes. Before this, the Chamber's plan asked a
harp carriage for 5.4 m/s and a mallet for a single click spanning
sixteen teeth — 0.75 m of rail in 40 ms. Holding the plan to the machine
costs nine of 239 intended notes (3.8 %, the composer's own ruler allows
5 %), and cost the marimba run in `songs/chamber.py` its sixteenths: those
bars are 0.386 m apart in the world and a ratchet crosses that in three or
four clicks, not one sixteenth. The expanded arrangement re-plans with no
refusals at all.

## What the space accounting saw

Every clearance ruler samples `Rig` (120 Hz plus every contact), so the
stroke, the overshoot and the recoil are in the swept capsules that the rail
gantries, oil cups, eyelets, flywheel, neck and form-clearance rulers
measure. When the mallets cocked, they all passed unchanged: the added
excursions (11 cm up over a bar that already had 22 cm of lift, 5 mm along
the rail, 2.5 mm across the bar) stayed well inside margins measured in
centimetres. The M1 stroke sweeps more — preps up to 0.50 m over the bar,
leaning up to 0.32 m toward the arm's root on the arc, and the homing
sweeps through every joint's span — so the rails are re-planned for it
rather than assumed to fit. The rail search
cache hashes the motion's constants and the plan's own event times
(`layout_search._mech_key`, which since M1 also hashes `t_head_free`, the
`home` cues and each event's `amp`, `voice` and stroke-normalised `a′` —
`stroke.a_norm`, which the prep height reads, so an amp elsewhere in the voice
that widens its range moves every prep), and the source of
`formlab/stroke.py` and `loam/motion_timing.py` (`TIMING_SOURCES`) with every
upper-case constant of both (`stroke.NAME`, `motion_timing.NAME`),
so a change to any of them — the travel timing above, say, or a prep
constant — costs both assets a full rail replan; there is no keeping a
cache that was planned for a different machine.

## Rendering clips

The contrast between the two vocabularies is the point, so making the reel
that shows it is one command:

```sh
tools/contrast_reel.sh START SECONDS [FPS] [OUT.mp4]
tools/contrast_reel.sh 52.1 4                       # a mallet arm beside a pick arm
SPEED=.25 SPAN=1.4 tools/contrast_reel.sh 43.0 .5   # teeth stepping under a parked head, quarter speed, close
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
stroke at the bottom — so the camera frames the arm's own root-to-tip box
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
no travel at all. Before M1 the quarter-speed reel was shot at 55.95 s, where
`bars_arm0` clicked 3.54 → 3.92 → 4.31 m; under the M1 stroke that moment is
a freewheel instead — 3.92 → 3.15 m, sixteen teeth from 55.73 to 56.77 s with
its pawl riding, under a bounce loop that winds up to a 0.50 m park — while
`harp_arm0` slews −0.60 → −0.38: both vocabularies moving, both away from
their gantry heads. The stepped close-up is 42.75–45.34 s, where `bars_arm0`
steps sixteen teeth 3.92 → 3.15 m under its parked head before its first
note. A mallet's travels, with their regimes and windows, are
`formlab.rig.Rig.stroke(aid).travels`; for every arm `formlab.rig.Rig.sched`
gives each entry's `go`, `hit` and `first` — the window's start, the contact
and the x it happens at.

**`--speed=S`** runs score time at S seconds a video second during a capture,
so `--fps=60 --speed=0.25` fills 23 frames with a step's 97 ms move (or 22
with the hammer's 90 ms click). `--seconds`
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

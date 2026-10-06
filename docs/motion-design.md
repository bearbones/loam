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
rig; since M2 a pick's is planned by `formlab/servo.py` and a rake's by
`formlab/rake.py` (both checked by `tools/test_servo.py`), below. The harness plays a bake of the rig
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

Since PLAYERS M2 a **pick** (`kind == 'pick'`: harp_arm0, 1 and 2) is planned
by `formlab/servo.py` (`plan_pick`; its constants at the top of that file),
which `Rig.stroke` consults for every pick whose events each pluck one
string, and `tools/test_servo.py` checks on the rig. It has the mallet
stroke's surface (channels, declared segments, knots, per-note records), so
the rulers read a pick as they read a mallet, but it is two declared
channels rather than a path:

    p(t) = (x, y_c, z_c)(t) + h(t) n

the **carriage** (x on the leadscrew, the contact's y and z riding the same
normalised law) and the **head**, the tool's height h above the contact
along the arm's unit clearance n — (0, 0, −1) for a plucked string: the pick
comes at the string plane from behind. A carriage segment is an 'scurve', a
head segment a 'quintic hermite' or a 'hold', and every join is C²
('smooth') except the contact. The **rake** (M2's T5, `formlab/rake.py`)
has the same surface and is described at the end of this section.

**Slews are S-curves.** A carriage travel is one jerk-limited profile, rest
to rest: a cubic-quartic ramp over the first 30 % of the window
(`SCURVE_RAMP`), a constant-velocity cruise and the mirror ramp — a
telescope drive's profile. Velocity and acceleration are zero at both ends,
the motion is monotone (no overshoot, ever) and lands exactly. It cruises at
1/(1−0.3) = 1.43× its mean speed, its peak acceleration is 7.14 L/T² and its
jerk 95.2 L/T³, the closed form ruler 6c holds it to. It is no single
polynomial, so the travel is ONE declared segment (`ScurveSeg`) evaluated as
its three pieces. Since M2 round 3 the servo carriage has a named
acceleration ceiling, `SERVO_A_MAX_G` (3 g: the goal's "a servo carriage
moves at ≤ `SERVO_V_MAX` and ≤ 3 g", the ratchet carriage's and ruler 14's
rake carriage's same 3 g), and `motion_timing.servo_fast_s(L)` is the least
window the S-curve crosses L in: its cruise (1.43 × the mean) within
`SERVO_V_MAX`, its 7.14 L/T² within 3 g, never under the floor —
max(L/3, L/2.1, √(0.243 L)) s, acceleration-bound up to 1.07 m (0.156 s
for 0.1 m, 0.493 s for 1 m). A slew wants `SLEW_S` (0.4 s) of lead, or its distance at
`SERVO_V_MAX` (3 m/s) if that is longer, and since M2 an unhurried one sets
off up to `SLEW_SLACK_S` (0.25 s) sooner when the arm is free
(`motion_timing.slew_lead`): the arm is seen to leave for the next string
rather than wait and dart.

**A poised pluck** (the contact ≥ `POISED_GAP`, 1.0 s, after the last) is
four phases. The head *rises* from the hover, 0.22 m above the string, to
the apex `H_APEX`, 0.32 m, over [t − 0.74, t − 0.25] (`RISE_LEAD`, `POISE`):
0.10 m in 0.49 s, peaking at 0.383 m/s and 0.245 g, while the carriage slews
(below). It *poises*: a declared head 'hold' (`hold='poise'`) of 0.1 s
ending at t_apex = t − 0.15, the stillness before the pluck the goal's A4
asks for (the same 0.1 s as the rake's `HOLD_MIN`, D5 below), and the
TOOL's stillness, not just the head's: D7 (below) reads the tool's |v| on a
1 ms grid through every poise, ≤ 20 mm/s, and every one of the 87 (41, 20 and
26) reads 0.000 mm/s (round 2: two read 561 and 1098 mm/s). The
*action* is a quintic hermite from rest at the apex to the
string at v_in in 0.15 s, peaking at 3.16–3.26 m/s and 5.0–5.9 g. After the
*contact* it *releases* (below). Ruler 3 reads the rise as the preparation:
a lead of 0.74 s, 14.67–16.93 frames of wind-up (the rise before the hold,
0.49 s), depth 0.312 of the apex.

**A phrase pluck** (gap under 1.0 s) is continuous, with no hold: the head
leaves the last contact at `V_REL` and rises straight to its apex,
min(`H_PHRASE` 0.22, 1.2 m/s × W) where W = IOI − T_down is the rise's
time, turns there at `A_TURN_G` 1 g (ruler 5 asks at least 0.5 g through
any slow turn, so a phrase never rests) and falls to the string over T_down
= clamp(0.4 IOI, 0.085, 0.15) s. Ruler 4's struck band is 0.35–0.45 IOI;
its pluck approach floor is 2.5 frames (83.3 ms), hence a floor of 0.085
and not 0.08. Measured: at IOI 0.714 s (arm0's fourteen) the rise is 0.564 s
to the full 0.22 m, peaking at 0.70 m/s; at 0.357 s (most of arm1's and
arm2's) it is 0.214 s at 1.56 m/s and 2.0 g; arm2's IOI 0.179 s run rises
0.112 m in 94 ms at up to 5.9 g and strikes in 85 ms. Phrase actions peak
at 2.12–2.80 m/s and 2.5–4.4 g. Because the apex height is the declared
`prep(a', IOI)` and T_down a function of IOI alone, the head law is a
function of (IOI, a', next IOI, next a') and nothing else — not dx, not the
idle time, not the previous string — so the head relative to the carriage
repeats exactly (ruler 22's repeat: 7, 2 and 7 groups, RMS under 2e-11 mm).

**The contact is a declared impulse.** The pick meets the string at
v_in = 2.0 + 0.8 a' m/s (`V_IN`; 2.0–2.8) and leaves it at `V_REL`
0.7 m/s: dv = (v_in + 0.7)·n, 2.7–3.5 m/s, the one knot that is not C² and
exactly what ruler 6a's impulse row reads. It is not a rebound. Nothing
elastic sends a pick back: the string is drawn and slips off, and the servo
withdraws at its own commanded speed. V_REL is above zero because v+ = 0
would be the head stopping dead at the string, the flaw M2 removes, and it
is constant (not e·v_in; e falls out at 0.25–0.35) so nothing after a
contact depends on a', which is what lets the repeat hold.

**The release.** From a contact whose next pluck is poised (and from the
last) the head returns to the hover over `T_REL` 0.25 s, peaking at
1.378 m/s and 1.54 g, and holds there (41, 20 and 26 releases); `RISE_LEAD + T_REL ≤ POISED_GAP`,
so a release always ends before the next rise begins. A y/z move to another
pick point on the same string rides the release and lands with it (below).

**The carriage under the stroke.** Only the carriage is bound by the
score's `arrive` (`motion_timing.arrive_lead`); the action starts before it,
on the head alone. A poised travel leaves at the score's go and ends at the
poise, so carriage and head arrive together (a ruler 22 sync target),
wherever its S-curve can: `servo_fast_s` of its distance fits between the go
and the poise's start. The distance is the 3-D chord (its peak speed and
|a| ride it, as `yz_s` and `test_servo`'s cap take it); round 3 timed the
check on x alone, which reads up to 1.92× short of the chord on the harps,
though nothing moved for it (every pick and rake stroke, its segments and
issues hash bit-identical under either distance on both assets, and the
replan moved no cfg but the rake's tie, A28). The poise is the tool's
stillness (D7), so a window
that cannot is an issue ('poise under a moving carriage'), never a quiet run
on to the arrive, and the planner's occupancy (below) rides the same law, so
the score leaves none. Round 2's fixed `CAR_MIN` (0.20 s) is retired: POISE
(.25, .15) left harp_arm1's 45.00 and harp_arm2's 44.29 travels 0.197 s
from their go, so both ran on to the arrive through the poise at 561 and
1098 mm/s (ending at the poise would have cost 2.04 g and 4.08 g, the second
over the cap). The cause was the score's late go. The planner charged
harp_arm1's carriage (07 → 06 at 43.93) the whole interval it crossed for
the whole of its travel, so harp_arm2 waited 0.29 s on an interval gap of
0.218 m under the 0.27 m clearance while the two carriages never came within
0.326 m. Since round 3 `loam/score.py` bounds a servo-profiled carriage
(`motion_timing.SERVO_PROFILED`, the picks) by where its S-curve can be,
leaving at the go and landing anywhere between `servo_fast_s` after it and
the arrive (`servo_span`, held over 10 ms steps, `OCC_DT`), and carries the
rig's 10 mm pad (`OCC_PAD`, `formlab.rig.PAD` is this one) so
`Rig._schedules` still pushes nothing. Both travels now leave 0.217 s
sooner and end at their poise: harp_arm2's 44.29 over [43.6214, 44.0357]
(0.414 s, 0.92 g, 0.75 m/s), harp_arm1's 45.00 over [44.3357, 44.75]
(0.46 g). No other event's t_move moved but the rake's return (A24, below),
and the onsets did not move at all. A phrase travel runs over the score's
whole window [go, arrive].

The score schedules x alone, so a move of the contact's y and z only
(another pick point on the same string) has no window of its own. It leaves
once the string is free (the last contact plus `recover_s`; the pick is never
dragged sideways in the string). A phrase's runs to the score's arrive. A
poised one rides the last contact's release and lands with the head on the
hover, over `yz_s(L)`: the S-curve whose end jerk (95.2 L/T³) is the
release's own, (60 H0 − 24 V_REL T_REL)/T_REL³ = 576 m/s³, so the two
channels settle together at any in-position band, and never under
`servo_fast_s(L)`. Reposition, then prepare: the rise and the poise are the
head's alone. Run under the rise into the poise instead, the two channels
left and arrived together in time but not in ruler 22's in-position reading
(1 µm, bisected; a frame of skew allowed). Over the rise's 0.49 s an S-curve
chord L is 1 µm from its start at 0.147 s·(1e-6/(0.4286 L))^⅓ and the 0.10 m
rise at 0.49 s × 0.01 = 4.9 ms, so any chord under 0.99 cm is read more than
a frame (4.17 ms) late, whatever law it rides (1.13 cm under the first M2
roll's 0.54 s rise, when harp_arm1 and harp_arm2 had four such moves each,
0.56–11.5 mm: sync read 10 of 14 and 19 of 23 targets in step, the worst 18.9
and 21.4 ms late). Round 2 ran it under the hover just before the rise
instead, ending where no head segment ends. D8 (below) reads a travel by the
head hold its tail overlaps, so that was a carriage arriving 0.08–9.0 s into
the hover's hold, and five of the thirteen left during the release and
arrived 79–430 ms after the head. Now each ends on the hold's first instant
(skew 0).

Of the 48, 29 and 48 travels (arm0, 1, 2), 32, 8 and 18 end at the poise
(sync's targets, back to round 1's count), 14, 15 and 25 at the score's
arrive, and 2, 6 and 5 are y/z moves riding a release (30.5–61.1 mm over
0.17–0.20 s, 0.75–74.4 mm over 0.050–0.20 s and 0.56–13.4 mm over
0.045–0.13 s, ≤ 1.36 g); arm1's phrase travels include one 78.3 mm y/z move.
The median travel takes 0.49 s and peaks at 0.63 m/s and 0.66 g. The pick is
at least 34.9 mm off the string plane whenever the carriage moves
(`test_servo` asks 20 mm).

**The acceleration cap, measured.** `tools/test_servo.py` reads every pick
travel's peak carriage acceleration (closed form) and holds each to 3 g and
3 m/s, unless it is hurried AND runs over exactly the score's [go, arrive]
(then the window is the score's, not the stroke's choice). Over the 125:

| travels | n | peak \|x″\| (g) | 3-D peak (g) | peak \|ẋ\| (m/s) |
|---|---|---|---|---|
| poised (all unhurried) | 71 | ≤ 1.65 | ≤ 2.04 | ≤ 1.59 |
| phrase, unhurried | 32 | ≤ 1.20 | ≤ 1.49 | |
| phrase, hurried | 22 | up to 53.3 | up to 70.2 | up to 4.03 |
| all | 125 | median 0.66, p90 3.36, max 53.3 | | |

Every travel the stroke times (the poised and the unhurried) is under 2.04 g:
the cap is the goal's rule and above all of them, so it costs nothing today
and stops a fixed window like CAR_MIN from ever again hiding a slide. 19
travels are over it, every one a hurried phrase travel the score times
exactly, the same 19 as in round 2: harp_arm2's twelve 39 ms hops in the
IOI 0.179 s runs (0.109 m of x at 53.3 g and 4.03 m/s; 0.141–0.143 m in
3-D, 70 g and 5.3 m/s: the goal's own Moments line names them, above
`SERVO_V_MAX`), and seven 0.217 s windows (harp_arm1 23.57, 24.64, 43.93,
45.36; harp_arm2 29.29, 36.07, 44.64: 1.68–3.36 g along x, 3.03–4.43 g in
3-D).

What the rulers read, `tools/test_players.py --report --skip-invariants`
(identical on the chamber and the expanded asset):

| ruler | harp_arm0 | harp_arm1 | harp_arm2 |
|---|---|---|---|
| 3 lead (IOI ≥ 0.25 s) | PASS: 55 strokes, lead ≥ 714 ms, W ≥ 14.67 fr, poise holds 100 ms (41) | PASS: 35, ≥ 357 ms, ≥ 6.4 fr, 100 ms (20) | PASS: 39 (12 under 0.25 s out), ≥ 357 ms, ≥ 6.4 fr, 100 ms (26) |
| 3 poise still (D7, A26; M2 gate) | PASS: 41 poises, 0 moving: tool \|v\| 0.0 mm/s, still 100 ms, drift 0 | PASS: 20, 0 moving (round 2: 44.75 at 561 mm/s, 52 mm) | PASS: 26, 0 moving (round 2: 44.04 at 1098 mm/s, 102 mm) |
| 4 action | PASS: approach ≥ 4.5 fr | PASS: ≥ 4.29 fr | PASS: ≥ 2.55 fr |
| 5 no rest | PASS: 0 gaps | PASS: 8 gaps, 0 violations | PASS: 15 gaps, 0 violations |
| 6a smooth / impulse | PASS: 208 knots / 55 contacts, dv 2.7–3.5 | PASS: 132 / 35 | PASS: 185 / 51 |
| 6b corners | PASS: 0 | PASS: 0 | PASS: 0 |
| 6c laws / jerk | PASS: hold, quintic hermite, scurve; 327 segments, worst 0.896 of the closed form | PASS: 186, 0.900 | PASS: 274, 0.898 |
| 22 sync (D8, A25) | PASS: 34/34 travel → hold (32 poises + 2 y/z rides), skew ≤ 2.69 ms, 0 unjudged | PASS: 14/14 (8 + 6), ≤ 2.52 ms, 0 unjudged | PASS: 23/23 (18 + 5), ≤ 2.38 ms, 0 unjudged |
| 22 repeat | PASS: 7 groups, RMS 1.1e-11 mm | PASS: 2, 1.2e-12 mm | PASS: 7, 5.2e-12 mm |

Ruler 22's sync judges every travel that ends on a head hold (D8's
travel->hold): the 32, 8 and 18 poises (round 2's two slides had dropped
them to 7 and 17) and the 2, 6 and 5 y/z moves that now land on the hover
hold's first instant. Its "sync (travels)" info row holds the rest, 14, 15
and 25 phrase travels that each end at the score's arrive in a run-up into
a contact (D8's strikes), arriving ≤ 4.5 ms after the head; round 2's read
up to 424 and 430 ms there, the y/z moves landing inside the hover.

Still open on the pick arms: harp_arm2's IOI 0.179 s runs (four, of three
travels each, t ≈ 13.6–22.6) leave 0.039 s windows for 0.141–0.143 m of
carriage (5.3 m/s, 70 g) and 2.8 frames of wind-up, which ruler 3's
preparation row fails on twelve strokes and no head law fixes (the score
must give those runs one string an arm, or wider windows); the seven
hurried 0.217 s phrase windows that take a carriage over the 3 g cap
(3.03–4.43 g in 3-D: harp_arm1 23.57, 24.64, 43.93, 45.36, harp_arm2 29.29,
36.07, 44.64; the score's windows, like the hops, and round 2's too); ruler 1's reach
(the tool's p95 0.81–0.86 of the part's extent a frame, against 0.5); ruler 22's
home (M7); and ruler 15's phases (M7, harp), which harp_arm1 now fails too: the
y/z moves that ride the release (`yz_s`) can run under 2.5 frames, 38.77–38.82
(49.8 ms) and 31.96–32.04 (75.0 ms) on harp_arm1, 29.49–29.54 (45.3 ms) and
39.84–39.89 (53.1 ms) on harp_arm2 beside its twelve hops. A floor of 2.5
frames on `yz_s` was tried in the review fix round (0.085 s): it passes
harp_arm1's row (min 2.55 frames) and lifts harp_arm2's two (14 → 12 short,
the hops left), and moves no poise and no sync target, but it moves the
gated sync row: under 3.7 mm a floored ride ends on a gentler jerk than the
head's release (95.2 L/0.085³ against 576 m/s³), enters the 1 µm band first,
and every such target's arrival skew changes (skew_arrive p50 1.077 →
1.086 ms on harp_arm1, 1.186 → 1.389 ms on harp_arm2; verdicts and maxima
unchanged). No S-curve or 3-4-5 longer than the jerk match ends on the
release's jerk, so the floor and an unmoved sync row exclude each other on
these moves: the row stays a known issue (M7).
`formlab/bake.py` samples every declared knot and segment
boundary of an arm with a stroke (mallets, picks and the rake), so a bake
lands on a pick's contacts and poise holds exactly; a pick's schedule
corners (the planner's approach / end windows) are not corners of its
stroke and get no row of their own, and every mallet's rows are unchanged.

### The rake

Since PLAYERS M2 (T5) the rake (`kind == 'rake'`, rake_arm0) is planned by
`formlab/rake.py` (`plan_rake`, constants at the top of the file). numpy
only: the rig hands it plain data (`Rig._rake_input`) and it returns a
`RakeStroke`, a `ServoStroke` with no prep function. The point is

    p(t) = (x(t), y_c, z_c) + h(t) n + (0, h_y(t), 0),   n = (0, 0, -1)

the carriage x on the leadscrew and the head's (h, h_y): h off the string
plane, h_y across the strings (y_c 1.7709, z_c 0.9, the home contact's). The
laws are 'quintic hermite', '3-4-5' and 'hold'; every join is C²
('smooth'): a rake has no impulse knot, it strokes through the strings.

**Motion first, then the arm.** The comb's path is designed in tool space
against physical limits and the definitions below, and reads no arm cfg: no
root, no link length, no reach cut. The rail plan (`formlab/layout_search`)
then chooses the rake's root and links so the arm reaches what the comb does;
its `REACH_FRAC` (|wrist − root| ≤ 0.985 (l1 + l2)) is the search's accept
rule and nothing else. `tools/test_servo.py` holds both ends: the plan is
identical (0 m on a 10 ms grid) under a mutated cfg, and the rail plan's cfg
is one `evaluate_arm` accepts.

**The definitions** every rake roll answers to (p(t) from `Rig.path_at`;
t_in, t_out the sweep's unit tangents at its first and last string):

- **D1 follow-through.** From every exit the comb runs on ≥ 0.2 m along
  t_out before v·t_out ≤ 0, decelerating along it at ≤ 3 g while it drops
  away along n over about 0.2 s.
- **D2 entry.** E = ((p(t_hit) − p(t_hit − 1/30))·t_in·30)/v_sweep ≥ 0.7,
  v_sweep = L_path/(t_end − t_hit); RI, the travel along t_in over the last
  0.2 s, is reported (a run-in, not a drop onto the string).
- **D3 tool acceleration.** |a| ≤ 10 g outside ±10 ms of a contact; the
  design aims at about 5 g.
- **D4 frame turns.** Within [t_hit − 0.25, t_end + 0.25] two consecutive
  30 fps steps, both ≥ 0.25 v_sweep/30, turn ≤ 30°.
- **D5 announcements.** A sweep after ≥ 0.8 s without contact (21.43,
  34.29, 40.00, 45.71, 77.14) gets a backswing ≥ 0.5 s, a declared head
  'hold' ≥ 0.1 s (`HOLD_MIN`), then the run-up. The pendulum's turns are
  exempt.
- **D6 release.** After a phrase-end sweep (68.57, 77.14) h rises with no
  return toward the plane until it rests; ruler 24's angle is read on that
  path.

M2 round 3 adds three (the picks answer D7 and D8 too):

- **D7 stillness (A26).** Over every announced apex hold (D5) and every pick
  'poise', the TOOL's |v| (closed form, every 1 ms, `STILL_DT`) stays ≤
  20 mm/s (`STILL_V`, 0.67 mm a frame): a carriage moving under a held head
  fails it. Ruler 14's '14 announce' judges it on the rake (`moving_hold`),
  the new '3 poise still' on every pick; both are gated at M2.
- **D8 sync overlap (ruler 22, A25).** Every carriage travel [a, b] is
  classified by where it ends, the first class that applies: a 'travel →
  hold' target when the head enters an ARRIVAL hold (a poise or the cocked
  hold; parks and hovers, `PARK_HOLDS`, are where a head waits while the
  carriage traverses under it, but on a servo a park or hover the head
  enters at or after the travel's go waits out nothing and is an arrival
  too) from the go on, before b + 1/FPS; else when a head hold of any kind
  starts within a frame of b (A22); else when an arrival hold overlaps the
  tail (h.t0 < b + 1/FPS and h.t1 > b − 1/FPS). A target is judged on
  `hold_skew`, the carriage's in-position arrival less the hold's start,
  ≤ `SKEW_MAX` (1/240 s), besides the in-position window. Else it is a
  strike (the info row 'sync (travels)') into the first contact after its
  go, crossing none: it ends at most `SKEW_MAX` after that contact (a
  carriage landing later moved under the pluck or hit, late into its
  strike, wherever its end lands), and on it, at most a frame before it,
  or in the head's run-up to it: the head segment at b moves and is not a
  'release', and no head hold and no 'release' segment starts between b
  and that contact. Anything left is unjudged and fails the row.
  Judging the arrival hold before the contact rule keeps it monotone: a
  carriage arriving d late into a hold fails for every d > SKEW_MAX, even
  one that runs on into the run-up. Round 3 left the servo's hovers out of
  the arrivals, and the y/z moves that ride the release onto a hover were
  not monotone: one landing 6–20 ms late failed as late, 40–300 ms late was
  unjudged (FAIL), and 450–700 ms late ran on into the next wind-up and
  passed as a strike. That fix still took any moving head segment for a
  run-up, the release after a pluck included, and a contact within a frame
  on either side for a strike: the same ride moved 40–150 ms early
  (landing in the 31.79 pluck's release), or leaving after the hover began
  and landing in the wind-up before the 32.96 poise (450, 700 ms late),
  passed as a strike, and so did harp_arm0's 25.62 travel landing 20 or
  110 ms after its pluck (fix 4, the recheck's D8 finding). Fix 4 still
  read a strike's contact off its end, so a strike landing past its pluck
  or hit by more than `SKEW_MAX` skipped to the next contact and passed as
  a run-up whenever no release or hold came between: harp_arm2's 13.66
  travel 4.5–45 ms past the 13.75 pluck (the next wind-up follows it), a
  mallet's 4.5–700 ms past its hit (the float follows it), on 41 of the 95
  strikes an asset. A strike's contact is now the first after its go. Each
  now fails, and `tools/test_sync.py` holds the grid. The sync row is
  monotone in a travel's error until its end reaches another contact's
  strike: the ride moved 250 ms early lands on the 31.79 pluck and is a
  strike, for rulers 19 and 11 to judge. A mallet's parks stay out: its
  travels leave on the head's way into the park by design, so a park it
  enters after the go is still a traverse (A25).
- **D9 rest.** From D1's turn (t_rev) to the rest (or the next backswing),
  the in-plane coordinate along the release never gives back more than
  1e-6 m (`RETURN_TOL`) of its running maximum, and h rises or holds. The
  sense is the release's (A27, the lead's L4): along +t_out (the exit
  tangent in the string plane, h taken out) after an up exit and at every
  rest that is not a listed phrase end; along −t_out after a DOWN exit at a
  listed phrase end (68.57), where D1's follow-through runs ≥ 0.2 m down the
  strings and ruler 24's upward release must climb back, so the literal
  +t_out sense cannot hold there together with D1 and ruler 24 (below). The
  literal +t_out number is still reported there (`give_back_exit`, info,
  never judged). Ruler 24 ('24 release', '24 rest') and `tools/test_servo.py`
  judge the same rests in the same sense, row for row, and print both
  numbers. Which chains are rests is read from the declared structure,
  never from the path's speed: a chain flows on only when its note leaves
  by 'turn' (the pendulum) or the next declared head segment after it is
  the next roll's stroke; every other (a park, a release, a fallback) is
  judged from t_rev to its end, or to the backswing or announce it flows
  into, and where a head hold follows, the comb must be still there too
  (|v| ≤ `STILL_V`, D7). Round 3 took any chain still moving at its rest
  for a flow-on, so a park sinking 49 mm back down the strings into its
  hold (1318 mm/s at the rest) read PASS.

**The sweep.** A roll (21 of them, the five strings rake00 → rake04 'up' or
back 'down', `RAKE_ROLL_S` 0.541 s first to last) is four quintic hermites a
channel ('sweep') through the five contacts at their own onsets with h ≡ 0,
entering and leaving at `SWEEP_V_END` (x′ 0.639, y′ 2.814 m/s). Their knot
states are the C² clamped cubic's but for one: the knot before the x_hi
contact (rake03's, on both rolls) turns its velocity onto the chord into
rake04, 40.0° → 47.7° (`SWEEP_TUCK` = 0: none of the way on toward the end
slope, 77.2°), its speed (2.747 m/s) and acceleration kept, so the sweep
stays C². The contacts, their onsets, the end slopes and the other three
knots are the cubic's, but the path between them is not quite: the turned
velocity under the kept acceleration puts a shimmy in the xy path, 5
curvature reversals a roll against the cubic's 3, at most 5.7 mm lateral
and 7.4° of turn a frame (30 fps), inside D3 and D4, so the acceleration
is kept as it is, not turned with the velocity (the lead's call). The end
slope is steeper than the contact line, so the plain cubic
came into rake04 (up) and left it (down) from under the line, toward the
strings' feet, where the outer, shortest string's eyelet sits (its contact
168 mm above its foot at pick 0.28): the comb's 30 mm tool capsule passed
rake04's eyelet flange (r 34 mm) 18.5 mm off at every roll (round 2 and this
round before the fix), against `tools/test_eyelets.py`'s 20 mm. On the chord
it passes at 23.01 mm (1 ms grid; 23.02 mm at the test's 30 fps), every
roll, both assets. Turning on toward the end
slope buys more clearance with the carriage's x″, because the contacts' x
are fixed while the knot's x′ falls: a tenth of the way reads 24.7 mm at
3.00 g, a quarter 27.0 mm at 3.21 g, past ruler 14's 3 g (the cubic's
2.87 g, the chord's 2.90 g). 2.886 m/s at both ends, 2.498 m/s at the
slowest (ratio 1.155, ruler 14 asks ≤ 1.2; the cubic's 2.514 m/s and
1.148), L/T 2.714 m/s, 3.99 g at most (the cubic's 3.95 g). It never stops at a string: the carriage runs
out past the last one into the rail's overtravel, `OVER` = rail_over +
head_inset − pin_x − margin − 1 µm = 14.599 mm past reach_x (A19), on the
quintic of least peak |x″| that never runs back (`RUN_D`: 0.0404 s and
2.86 g at rake04, 0.0417 s and 2.61 g at rake00), and runs up out of it the
same way.

**The pieces.** Between rolls the head flies DESIGNED pieces: piecewise
quintic hermites in (y, h) (and in x where the carriage crosses under them)
solved offline by `tools/rake_design.py` (scipy SLSQP, exact Jacobians; the
planner only reads the result) and stored in `formlab/rake_pieces.json` with
the frame they were solved for. The live plan checks that fingerprint
(`LIB_TOL` 1e-9): a mismatch is an issue and a plain fallback, never a
silent reuse. The design's limits, with margin: D1 (≥ 0.21 m by 0.2 s, ≤ 0.95
× 3 g along t_out; 0.15 s on the ghost), D2 (E ≥ 0.75, RI ≥ 0.21 m), D3 (≤
0.95 × 10 g), D4 (below), frame ρ ≤ 0.92 on a 1–4 ms grid (ruler 14 reads
frames, ≤ 1), carriage |x″| ≤ 0.95 × 3 g and x inside [x_lo, x_hi] (A19),
strict rise and fall of h about each apex (ruler 3), y inside [0.70, 2.58]
(40 mm inside the strings' span), h ≥ 0 outside a sweep, the comb clear of an
end string (h ≥ 0.034 m) from 35 ms after an exit and before an entry,
≥ 5 mm off every string (h ≥ 0.042 m) from 0.1 s, and since round 3 a rest
after a sweep in-plane monotone (`mono`, `rest_mono`: (x, y)·t_out never
decreasing, D9), so it comes to rest where its follow-through ends. D4 is designed on the
frame chords themselves, from six phases of the 30 fps clock (the score's
hits fall anywhere on it) with the sweep's own frames joined on:
|a × b|² ≤ sin²27° |a|²|b|² + (0.35 lim)⁴ and a·b ≥ −(0.35 lim)², the
short-step terms freeing the steps D4 skips (an instantaneous curvature bound
was infeasible: the run-up's apex and the ghost's turn have to fold). The
objective is the peak tool |a|, staged (mean |a|² without D3 and D4, then
constrained, then the peak; odd restarts re-enter through the constrained
stage).

| piece | D (s) | from → to | peak \|a\| (g) | ρ | D1 FT (m) / decel (g) | D2 E / RI (m) | D4 max (°) |
|---|---|---|---|---|---|---|---|
| runup_lo | 0.25 | apex (0.795, 0.32) → rake00 | 5.17 | 0.922 | | 1.08 / 0.358 | 24.7 |
| runup_lo_b | 0.25 | apex (0.821, 0.25) → rake00 (after the return) | 5.17 | 0.920 | | 1.08 / 0.333 | 24.8 |
| runup_hi | 0.22 | apex (2.58, 0.30) → rake04 | 5.46 | 0.779 | | 1.14 / 0.385 | 24.4 |
| park_hi | 0.45 | rake04 → (2.58, 0.15), monotone | 5.21 | 0.681 | 0.385 / 2.50 | | 23.5 |
| park_lo | 0.45 | rake00 → (0.70, 0.15), monotone | 5.15 | 0.920 | 0.456 / 1.34 | | 24.1 |
| release_lo | 0.70 | rake00 → (1.40, 0.15) | 5.05 | 0.920 | 0.391 / 1.68 | | 24.0 |
| release_hi | 0.70 | rake04 → (2.58, 0.20), monotone | 5.11 | 0.690 | 0.385 / 2.42 | | 24.0 |
| turn_hi | 0.888 | rake04 → apex h 0.828 → rake04 | 5.26 | 0.926 | 0.385 / 2.60 | 1.13 / 0.384 | 24.7 / 25.0 |
| turn_lo | 0.888 | rake00 → apex h 0.448 → rake00 | 5.12 | 0.932 | 0.376 / 1.67 | 1.08 / 0.299 | 24.5 / 24.6 |
| ghost_down | 0.888 | rake00 → apex h 0.465 → rake04, x crossing | 5.26 | 0.932 | 0.290 / 2.85 | 1.11 / 0.210 | 27.1 / 27.1 |
| home_up | 0.50 | rest (1.771, 0.22) → apex (0.795, 0.32), x home → x_lo over [0.05, 0.50] | 2.54 | 0.920 | | | |
| return_up | 0.90 | park (2.58, 0.15) → apex (0.821, 0.25), x_hi → x_lo over [0.244, 0.90] | 1.43 | 0.920 | | | |

(ρ is the design's on its fine grid, over the piece and the sweep frames
joined to it; the turns' 0.93 is the sweep side's, which ruler 14 reads per
frame: 0.92 at most, 0.9185 in the sweeps.) Round 3 re-solved park_hi and
release_hi (D9), park_lo (the same constraint: it gave back 0.6 mm in
round 2), runup_lo_b (A24's 0.25 s), and the two backswings that start or end
at those (home_up, return_up). The merge's sweep (the knot on its chord)
changed the sweep's frames and knot states at x_hi, so the pieces that join
it there were solved again from cold: runup_hi, park_hi and release_hi came
out with their shapes (peak |a|, ρ, FT the same to three digits; the joined
turns within 0.1°), ghost_down within 0.003 g (5.261 → 5.259 g, apex h
0.468 → 0.465), return_up (it starts at park_hi's rest) the same to seven
digits, and turn_hi new. turn_hi is the pendulum's turn at rake04,
which ruler 5 reads as a rest wherever its speed stays under 0.15 of its own
peak (4.24 m/s) for over a frame. Its speed floor (`LOOP_VMIN`, the design's)
was 0.6 m/s, 0.146 of round 3's design's peak, which passed only while the
stretch under 0.15 stayed under a frame. With the merged sweep's knot states
at 0.6 the cold solve stops at its iteration limit (6.09 g), solved on it
sits at 0.142, and the quarter-way sweep's design read 54 ms under at every
apex (8 slow intervals, ruler 5 FAIL). At 0.7 m/s it converges (1441
iterations) and holds 0.165 (turn_lo reads 0.156 at 0.5): apex h 0.646 →
0.828, RI 0.309 → 0.384 m, 5.256 → 5.262 g, ρ 0.951 → 0.926. The x_lo
pieces are round 3's design's, digit for digit. The backswings home_up and return_up are designed
pieces like the rest — quintic hermites in (y, h) and x, the head on its
(y, h) chord within 0.1 mm (ruler 22 reads its progress from wherever the
carriage starts), the carriage crossing over exactly the score's window,
from its go to the apex hold's start (`Frame.cross`, read from the score as
the ghost's window is). Only the backswings from a park to the apex at the
same end (39.18, 44.86, 76.29) are 3-4-5 head legs (`BACKSWING_S` 0.5 s, the
carriage still); the 39.18 one is now h alone, 0.15 → 0.30 at y 2.58,
because park_hi rests at the apex's y (0.35 g, 0.56 m/s).

The return is the longest: 1.76 m of head over the carriage's 1.079 m
crossing. Since A24 the score gives that crossing a window of its own: the
carriage leaves `announce_lead`(1.05 m of score dx) = 0.656 + 0.10 + 0.25 =
1.006 s before the roll, at 33.2795, and lands at 33.9357 as the apex hold
starts; the head leaves 0.244 s before it, at 33.0357. Its least peak ρ at
0.656 s is 0.78; designed at ρ 0.92 it peaks at 1.43 g (the carriage at
2.58 m/s). Round 2's fixed 0.8 s lead left the crossing 0.52 s, past ρ 1
(the least ρ is 1.01 at 0.52 s and 1.0 at 0.524 s), so its carriage ran on
0.10 s under the hold (1.32 m/s at the hold's start, still for 10.5 ms of
the 100, 60 mm of drift) and launched into a 0.18 s runup_lo_b at 6.59 g.
Now D7 reads the hold [33.9357, 34.0357] at 0.000 mm/s, D8 judges the
crossing a 'travel → hold' target with skew 0, and runup_lo_b runs up over
the same 0.25 s as runup_lo (5.17 g). home_up's crossing (0.678 m of rail,
home → x_lo) keeps round 2's window [20.629, 21.079]: its 0.8 s slew lead is
already longer than announce_lead's 0.764 s (1.99 g, 2.33 m/s).

**The rests.** Every rest after a sweep, from D1's turn on (D9; `tools/
test_servo.py`, `m2work` probe d79):

| rest | piece | t_rev / rest (s after t_end) | shape from the turn | gives back in D9's sense (round 2) | rest (y, h) |
|---|---|---|---|---|---|
| 21.43, 34.29 up | park_hi | 0.250 (D1 reads 0.450) / 0.450 | climbs on up the strings to the Y cap, h 0.15 by 0.18 s, then holds | 0 (round 2: 62.1 mm) | (2.58, 0.15) |
| 40.00 down | park_lo | 0.400 / 0.450 | runs on down the strings to the bottom cap, h 0.15 by 0.18 s | 0 (0.6 mm) | (0.70, 0.15) |
| 68.57 down | release_lo | 0.226 / 0.700 | turns at y 0.766 and climbs 0.63 m back UP the strings (ruler 24), h 0.15 by 0.18 s | along −t_out (a down exit at a listed end): 0; the literal +t_out 618.25 mm is info (round 2: the same) | (1.40, 0.15) |
| 77.14 up | release_hi | 0.261 / 0.700 | climbs on to the Y cap, h 0.20 by 0.18 s, then holds | 0 (71.4 mm) | (2.58, 0.20) |

park_hi's follow-through reaches its 385.3158 mm at +0.25 s and stops
there; from then to the rest its speed along t_out stays at or under
4e-7 mm/s but never crosses zero, so D1's turn (the first instant at or
under zero) reads the rest, +0.450, and D9's window is empty: the whole
path from the exit to the rest is monotone along t_out. h gives back 0
everywhere. Round 2's park_hi ran on to 2.5797 and settled
64 mm back to 2.516; its release_hi ran to 2.579, rocked 72 mm back to
2.507 and up again to 2.56, two turns of about 180° at h 0.20. Both now stop
where the follow-through stops. release_lo cannot: its exit tangent runs
down the strings, t_out = (−0.221, −0.975), 167.2° from +y, and ruler 24
asks the release to rise within 45° of +y from the turn, so every
displacement it accepts has (d·t_out) ≤ cos 122.2° |d| = −0.533 |d|. D1
holds the comb ≥ 0.2 m down the strings before it turns, so a literal D9
(along +t_out) and ruler 24 contradict each other there by construction.
The lead's L4 (A27) takes the release's sense there: along −t_out, once
the climb has started the comb never sinks back down the strings, and
release_lo gives back 0 (its literal 618.25 mm is reported as info). The
rule itself is unchanged (`RETURN_TOL` 1e-6 m, from the turn to the rest);
a 5 mm sink back down the strings in the climb fails both ruler 24 and
`tools/test_servo.py`. The pendulum turns and the ghost do not rest.

**The homing poses** are tool space too. Ruler 22 home asks the sweep in
the first rest for ≥ 0.8 of the shoulder's and the elbow's IK spans, which
are the arm's; so the poses are chosen against every rail the search can
accept (`tools/rake_design.py --homing`: the 30 `layout_search.candidates`
that `evaluate_arm` passes with worst ≥ 0; the root y 2.75 rows fold the
links through each other, −56 mm and worse), each inside that rail's own
|wrist − root| range over the rest of the motion by ≥ 10 mm (the homing
never decides a rail), the chords inside the score's windows at
`HOME_SERVO_V` 1.1 m/s (elbow 2.630 of 2.640 m, shoulder 1.229 of 1.232 m):
(2.565, 0.155), (2.375, 0.44), (0.885, 0.395) in the elbow window, (0.775,
0.19), (1.61, 0.225) in the shoulder window. The least share over the 30
rails is 0.845 (the first poses, designed on one rail, swept 0.12 of the
shoulder on others).

**The timeline** (chamber; expanded identical):

| when (s) | what | measured |
|---|---|---|
| 0.25–10.55 | homing (`motion_timing.servo_home_legs`): x home → lo (0.25–1.45), lo → hi (1.45–3.25), hi → home (3.25–3.95), 3-4-5 legs at ≤ 1.1 m/s on 0.1 s steps; then the elbow window (3.95–8.45) and the shoulder window (8.45–10.55) through the poses above | x swept 1.0 of reach_x; shoulder 1.074, elbow 0.887 of their spans on the (0.55, −1.35) rail (1.053, 0.955 on round 3's −0.90); peak 1.098 m/s (limit 1.5); land 0 m |
| 20.58–21.43 | the announcement from home: home_up 0.50 s (the head leaves at 20.579; the carriage home → x_lo, 0.678 m, from the score's go 20.629 to 21.079, landing as the hold starts), apex hold 0.10 s at h 0.32, runup_lo 0.25 s into rake00 | carriage 1.99 g, 2.33 m/s; head 2.54 g; hold 0.000 mm/s; run-up 5.17 g |
| 21.97–22.42 | park_hi on up the strings to (2.58, 0.15), monotone (h 0.15 by 22.15, y at the cap by 22.22), held to 33.04 | FT 0.385 m, 5.21 g |
| 33.04–34.29 | the return: return_up 0.90 s from 33.036 (the carriage x_hi → x_lo, 1.079 m, from the go 33.280 to 33.936, landing as the hold starts: A24), hold 0.10 s at h 0.25, runup_lo_b 0.25 s | carriage 1.43 g, 2.58 m/s; head 1.43 g, 3.67 m/s (tool 3.94 m/s); hold 0.000 mm/s; run-up 5.17 g |
| 34.83–35.28 | park_hi, held to 39.18 | as 21.97 |
| 39.18–40.00 | the 3-4-5 backswing 0.50 s at rake04, h alone 0.15 → 0.30 at y 2.58 (park_hi rests at the apex's y), hold 0.10 s, runup_hi 0.22 s into rake04 (the down roll) | 0.35 g, 0.56 m/s; run-up 5.46 g (D3's peak, at 39.98) |
| 40.54–40.99 | park_lo on down the strings to (0.70, 0.15), monotone (y at the cap by 40.94), held to 44.86 | FT 0.456 m, 5.15 g |
| 44.86–45.71 | the 3-4-5 backswing 0.50 s (0.70, 0.15) → (0.795, 0.32), hold 0.10 s, runup_lo 0.25 s | 0.46 g |
| 46.26–67.14 | the pendulum: 15 turns of 0.888 s that never stop ('follow-through', then 'stroke' from the apex): at rake04 apex h 0.828, at rake00 h 0.448 | ruler 5: 0 slow intervals; 5.26 / 5.12 g; repeat RMS 3.5e-11 mm |
| 67.68–68.57 | the ghost, down → down: the comb out of rake00 (FT 0.290 m to the 'ghost' cut at t_end + 0.10) while the carriage crosses under it x_lo → x_hi in [67.784, 68.421], apex h 0.465, into rake04 | carriage 2.85 g, 2.63 m/s; head 5.26 g |
| 69.11–69.81 | release_lo: on down the strings to y 0.766 (the turn, +0.226 s), then up them to (1.40, 0.15) in 0.70 s, held to 76.29 | ruler 24: rise 0.236 m at 32.6°; D9 0 along −t_out (the literal +t_out 618 mm is info, A27) |
| 76.29–77.14 | the 3-4-5 backswing 0.50 s (1.40, 0.15) → (0.795, 0.32), hold 0.10 s, runup_lo 0.25 s | 1.48 g, 2.36 m/s |
| 77.68–78.38 | release_hi on up the strings to (2.58, 0.20) in 0.70 s, monotone (h 0.20 by 77.86, y at the cap by 77.95), held to 78.57 | ruler 24: rise 0.392 m at 27.1°; 5.11 g |
| 78.57–79.37 | home with the last onset: 3-4-5 'travel' on both channels, 0.8 s (`END_S`), (2.58, 0.20) → (1.771, 0.22), the carriage x_hi → home 0.401 m | 0.83 g, 2.12 m/s; carriage 0.37 g |

The D-definitions per sweep (`tools/test_servo.py` checks D1–D9 against
these; identical on both assets):

| roll | t | enter → leave | D1 FT (m) | D2 E / RI (m) | D3 peak (g) | D4 max (°) |
|---|---|---|---|---|---|---|
| 0 | 21.429 up | home → park | 0.385 | 1.08 / 0.358 | 5.21 | 23.4 |
| 1 | 34.286 up | return → park | 0.385 | 1.08 / 0.333 | 5.21 | 24.8 |
| 2 | 40.000 down | announce → park | 0.456 | 1.14 / 0.385 | 5.46 | 23.1 |
| 3 | 45.714 up | announce → turn | 0.385 | 1.08 / 0.358 | 5.26 | 24.1 |
| 4–17 | 47.14–65.71 | turn → turn | 0.376–0.385 | 1.08–1.13 / 0.299–0.384 | 5.26 | 24.9 |
| 18 | 67.143 down | turn → ghost | 0.290 | 1.13 / 0.384 | 5.26 | 27.0 |
| 19 | 68.571 down | ghost → release | 0.391 | 1.11 / 0.210 | 5.26 | 25.6 |
| 20 | 77.143 up | announce → release | 0.385 | 1.08 / 0.358 | 5.17 | 23.8 |

D3's peak anywhere is 5.46 g (39.98, runup_hi; round 2: 6.54 g at 34.13,
runup_lo_b), 0 ms over 10 g. D5: the five announced rolls hold 0.100 s each
after backswings of 0.50, 0.90, 0.50, 0.50 and 0.50 s (run-ups 0.25, 0.25,
0.22, 0.25, 0.25 s). D6: neither release returns toward the plane after its
lift (0.0 mm). D7: all five apex holds read 0.000 mm/s (round 2: 1325 mm/s
at 34.29). D8: the rake's travels are the nine homing legs, three
'travel → hold' targets (the home crossing e37 and the return e76 into their
apex holds, the end travel into the rest), skew 0, and the ghost, a strike
into its run-up; none unjudged. D9: all five rests give back 0 mm in D9's
sense (release_lo along −t_out; its literal +t_out 618.25 mm is info). The comb is at
least 89.8 mm off every string more than 0.1 s from a sweep.

What the rulers read, `tools/test_players.py --report --skip-invariants`
(identical on both assets):

| ruler | rake_arm0 |
|---|---|
| 3 lead / preparation | PASS: 21 strokes, lead 819–1249 ms, W ≥ 12.96 frames, depth ≥ 0.312, apex holds 100 ms (5) |
| 4 action | PASS: approach ≥ 6.6 frames (5.4 in round 2: runup_lo_b's 0.18 s) |
| 5 no rest | PASS: 15 gaps, 0 violations |
| 6a smooth / impulse | PASS: 723 knots, da ratio ≤ 0.04 / 0 impulse knots (A21: the rake declares none, so one would fail) |
| 6b corners | PASS: 0 |
| 6c laws / jerk | PASS: 3-4-5, hold, quintic hermite; 834 segments (head 652, carriage 182), every one bounded by the closed form (A23: the home legs too), worst 0.908 |
| 14 entry (D2) | PASS: E 1.082–1.137 (rake00 1.082–1.085, rake04 1.112–1.137); RI 0.210–0.385 m, v_tan a frame before the hit 2.81–3.13 m/s |
| 14 follow-through (D1) | PASS: FT 0.290–0.456 m (rake04 0.385, rake00 0.290–0.456), turning 169–400 ms after t_end (park_lo's t_rev 0.400); the old arc (info) 0.292–1.042 m |
| 14 announce (D5; D7, A26: M2 gate) | PASS: 5 (21.43, 34.29, 40.00, 45.71, 77.14), backswings 0.50 / 0.90 / 0.50 / 0.50 / 0.50 s, holds 0.100 s, 0 moving: the tool through every hold ≤ 0.0013 mm/s, still 100 ms, drift ≤ 3.2e-08 mm (round 2: 34.29 at 1325 mm/s, still 5.9 ms, drift 60 mm, which A26 fails) |
| 14 frame turns (D4, info) | 27.0° max (67.87), 0 over 30°; peak 5.46 g (39.97, the down roll's runup_hi; 6.55 g at 34.13 in round 2) |
| 14 corners / speed ratio | PASS: 0; 1.155 (2.498–2.886 m/s) |
| 14 ρ / carriage | PASS: 0.920 max (68.10), 0 frames over 1; 2.63 m/s, 2.90 g (64.29, a sweep; ≤ 3 g), dv step 8e-10 |
| 15 tip accel (D3; M2 gate, A20) | PASS: max 5.5 g (39.97, runup_hi), p99 5.3 g, 0 ms over 10 g (6.5 g at 34.13, runup_lo_b, in round 2) |
| 22 sync (D8, A25) / repeat / home | PASS: 12/12 (9 home legs, 3 travel → hold: e37, e76, the end), skew ≤ 1.05 ms, 0 unjudged; 2 groups, RMS ≤ 3.5e-11 mm; x 1.0, shoulder 1.074, elbow 0.887 of their spans, peak 1.098 m/s, land 0. 'sync (travels)' (info, A22's strikes): the ghost alone, 1.83 ms (round 2 also held the return's crossing there, 100.9 ms after the hold's start) |
| 24 release (D6; D9, A27; M10) | PASS: follow (D1) 0.385–0.391 m, rise 0.236–0.392 m, 27.1–32.6°, return 0 m, path angle ≤ 28.9° (release_hi's mono rest); give-back 68.57 0 along −t_out (literal +t_out 618.3 mm, info), 77.14 3.5e-05 mm along +t_out (round 2: 71.37 mm, the rock) |
| 24 rest (D9, A27; M10) | PASS: 3 rests (21.43, 34.29, 40.00), chosen by the declared structure, give back ≤ 1.0e-08 mm along +t_out and are still at their holds (\|v\| ≤ 4.6e-16 mm/s; round 2: 62.14, 62.14, 0.56 mm); the pendulum's 15 turns flow on into the next stroke (their notes leave by 'turn'), the 67.14 ghost leaves before its turn |

Still open on the rake, outside M2's gate (chamber, the review fix's
report; each fails as in round 2; ruler 16's reversals, which pass, fell
6 → 1): ruler
1's tool p95 over active frames 0.913 (≤ 0.5; max 0.920, no frame over 1);
ruler 2 on the screen, ρ_px 2.00 at 40.07 (camera.json is stale against the
score: re-export); ruler 15's order, shares and phases (M9: joint-space, and
592 of 796 declared segments are under 2.5 frames, the sweep's and pieces'
knots); ruler 17's driven share (only the carriage is driven) and the
leadscrew at 19 700 rpm for 2.63 m/s on an 8 mm lead, ruler 18's thread
aliasing (M4); ruler 23 (M9): the comb's 30 mm capsule is inside rake00 by
up to 35.6 mm as the down roll leaves it at 40.54 (the ruler's exemption
ends at t_end; the pieces clear h ≥ 0.034 m from 35 ms after it), and the
plectrum blade the rake does not have; and ruler 24's ending (all arms).
Ruler 1's links, which round 3's −0.90 rail failed (upper 1.017 at 64.13,
18 frames over; lower 1.177 at 68.00, 4 frames), pass on the −1.35 rail the
plan's tie-break takes (upper 0.906 at 47.00, lower 0.955 at 68.03, 0 frames
over; A28, below). Outside the rulers, `tools/test_eyelets.py` failed on
the rake from round 2
on: the comb's tool capsule passed rake04's eyelet flange 18.5 mm off at
every roll, against 20 mm (the repo's straight fast roll passed at 49.3 mm).
Round 3 fixes the motion, not the test: the sweep's knot on its chord
(above) passes it at 23.01 mm, and the test's least clearance anywhere is
now 23.02 mm (rake04; harp14 vs harp_arm2 27.29 mm).

**The rail plan** (`layout_search.plan_arms`, rerun in python on both
assets for this motion; the Blender build derives the rest later, below):

| arm | before: root (y, z), l1 = l2 | after | margins after (mm) |
|---|---|---|---|
| rake_arm0 (both assets) | (0.55, −0.50), 1.15, pinion down | (0.55, −1.35), 1.60, pinion down (round 2's and round 3's design rail; round 3's merge took (0.55, −0.90) on a 1-ulp tie, which the review fix's tie-break settles) | self 53.0, pair 26.2, strings 23.0, scene 170, mast 85.0, fine 23.0 |
| harp_arm0, 1, 2 (chamber) | (2.75, −2.25) 1.45; (3.15, −1.80) 1.15; (0.55, −2.25) 1.60 | the same rails; o1 re-chosen on arm0 and arm2 | self 21.5 / 24.9 / 53.0, strings 23.0 each |
| harp_arm0, 1 (expanded) | as chamber | the same rails | as chamber |
| harp_arm2 (expanded) | (0.55, −0.75), 1.15, pinion down | (4.10, −1.40), 1.30, pinion back | self 20.8, pair 44.0, strings 23.0, cross harp_arm1 27.2 |
| bars, bells, blocks | | identical, margins included | |

The rake on its old rail would need |wrist − root| = 1.091 (l1 + l2) (2.509 m
at 22.17, the park after the first roll): the search drops it. Of the
search's rake candidates 27 pass `evaluate_arm` with worst ≥ 0 (root y 0.55,
3.15 and 3.6; at 2.75 the links fold through each other, −56 mm and worse);
none reaches `enough` (80 mm), and the clearest two, (0.55, −0.90, 1.60)
and (0.55, −1.35, 1.60), are held to 23.0 mm by the links' and shank's
clearance to the strings. They tie on all four of the objective's keys
(worst, l1, |root_y − 2.75|, worst; equal within `TIE_TOL`, 1e-9 m), and
the tie goes to the rail whose links strobe least over the arm's own motion
(`clearance.link_strobe`, ruler 1's '1 links' measure, then the order
`candidates` lists them in): (0.55, −1.35, 1.60) at 0.955 against
(0.55, −0.90, 1.60)'s 1.177 (pair 26.2 mm against 25.3). The ruler does
not call the planner it judges, so the two copies of the measure are held
together by `tools/test_sync.py`: the same head radius and bar floor, and
the same value to 1e-12 on the chamber's installed rake, harp_arm1 and
bars_arm0 rails and the expanded's blocks_arm0 (a hammer, read on its
head), so each of the measure's three tool branches is held (equal to the
bit today).
There the comb's path needs at most 2.9955 m = 0.936 (l1 + l2) (at 35.07,
the park after the isolated sweep): 156.5 mm inside the search's cut
(0.985 × 3.20 = 3.152 m), 204.5 mm inside l1 + l2, at least 1.772 m from
the root (floor 0.30), the elbow 67.2–138.8°. The homing poses still sweep
≥ 0.845 of both joints' spans on every one of the 27 rails, 14.5 mm inside
each rail's envelope (`tools/rake_design.py --homing`, run on a copy: it
rewrites the library byte-identical). The expanded harp_arm2 moved because the M2 pick motion
(not the rake, which is planned after it, and not POISE: the same numbers
under (.20, .15)) takes its old rail's self clearance to 20.0 mm against the
new rail's 20.8 mm. No arm is dropped and none is stale (`stale_rails`
absent); the merged cache (`render/form-study/rails-cache.json`) holds both
assets' new keys.

Round 3's design (A24's return, the poise and y/z re-timing, the re-solved
rests) changed t_move, `servo.py`, `rake.py` and `rake_pieces.json`, so the
plan reran on both assets under the new rail key (it hashes
`motion_timing`'s new constants too): every arm's cfg came out round 2's on
both, the rake's (0.55, −1.35, 1.60) included, and so did every margin but
one (on the chamber the harp_arm0 / harp_arm2 cross gap, 342.7 mm against
342.3). The merge's sweep (the knot before x_hi on its chord, `SWEEP_TUCK`)
and the pieces re-solved with it (`LOOP_VMIN`) changed `rake.py` and
`rake_pieces.json` again and the rail key with them
(`layout_search.geometry_digest` 3a876e6c…; `motion_constants` collects
`SWEEP_TUCK`), so the plan reran once more on both assets: the rake moved
to (0.55, −0.90, 1.60), pinion down, on both, and every other arm's cfg and
margins are the design run's. No arm is dropped or stale. The review fix
(the poised check's 3-D chord in `servo.py`, `TIE_TOL` and the tie-break in
`layout_search.py`, the `SWEEP_TUCK` comment in `rake.py`) changed the rail
key again (`geometry_digest` 8e83fa28…; `_mech_key` hashes `TIE_TOL` by
hand), and the plan reran on both assets: the rake is back on
(0.55, −1.35, 1.60), pinion down, o1 (0, 0.0191, −0.10833), o2
(0, 0.10958, 0.00959), with the design's margins (self 53.0, pair 26.2,
behind 1432.2 mm; its o2 too, its o1 (0, 0.02847, −0.10625) under the cubic
sweep), and every other arm's cfg and margins are round 3's, on both. The
expanded blocks_arm0 ties three rails, (2.75, −3.54 / −3.79 / −4.09, 1.00),
and keeps −3.54, which strobes least (0.980 against 1.011 and 1.243) and
which the order took before. No arm is dropped or stale.

Round 3's move was a tie broken by rounding. The upper link's parallel bar
o1 is
`clearance.choose_offset`'s best of 72 directions; o and −o separate the
bars identically, and `half_plane` keeps both 90° and 270° (cos 270° =
−1.8e-16 passes its −1e-12 guard). On the cubic sweep the two read equal to
the last bit (0.105166 m) and 90°, o1 up, won as the first; on the merged
sweep 270° reads 1 ulp more (0.102504 m) and wins (so did it at a quarter
of the way on, 0.104170 m). With o1 up the −0.90 rail's self
clearance is 19.8 mm (the lower link against the upper link's partner, in
the homing at 0.43 s) and it ranked 15th; with o1 down it is 53.0 mm, and
the rail ties −1.35 as above. Both rails pass everything the plan measures,
so the order decided, and the links it chose strobed (ruler 1, above). A28:
a tie within `TIE_TOL` goes to the least link strobe before the order, so
float noise no longer chooses a visible quality. The cache
(`render/form-study/rails-cache.json`) holds every run's keys: 141 entries,
the design's 117, the quarter-way sweep's 3 chamber and 5 expanded, the
merge's 3 and 5, and the review fix's 3 and 5, with the `mech:` aliases from
the expanded runs, as in round 2.

The replan writes each arm's `CFG_KEYS` (root, links, bend, wrist offset,
o1, o2, pinion) and `margins`; the Blender build (`tools/build_clockwork.py`
→ `tools/build_forms.py`) derives the rest from them: per arm `gantry`
(ends' bar_x / setback / outreach / mast, rack mount, margin), `screw`
(axis y, z, pitch), `drive`, `layers`, `oil_cups`, `link_extent_y`, the
pair separations and self / string clearances, the strings' `neck`, and
`render/form-study/recipe.json`. Readers: `tools/test_gantry.py` (rack
mount, ends, screw axis and pitch, drive, `margins.others`, `stale_rails`,
the recipe's form boxes), rulers 1 and 2 (`r_motion`, `r_screen`: `layers`,
`default_layers` when absent), rulers 12–14, 23 and 24 (`r_strings`: the
necks), rulers 17 and 18 (`r_machine`: the screw's pitch, which no rail
changes), `Rig` (the mechanisms' `arm_clearance_m`). As in round 2, the
manifests carry the plan's cfg and margins, and the build rewrites the
records at integration. The rake is back on the −1.35 rail whose records
the manifests carry (screw z −1.585), so test_gantry passes on them as they
stand, on both assets (303 checks; round 3's −0.90 rail failed the rake's
leadscrew, recorded at z −1.585 against its z −1.135). Written from
`formlab.gantry.plan_gantries` as the build writes them, only the chamber
harp_arm0's rack gap changes (0.2464 → 0.2471 m), and test_gantry passes on
those copies too (123 and 180 checks).
A19 reads only the motion and `reach_x`: the carriage runs 14.6 mm past
reach_x at both ends and the pin heads clear the rail heads by 0.001 mm
beyond `MARGIN` (`RAIL_SPARE`).

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

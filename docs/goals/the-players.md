# The players: fingers, hammer arcs, and gestures that begin before the note

**Goal.** Every note in the Chamber is played by a visible gesture that starts
before the sound, carries through the contact and flows into the next note.

- The harp arms play with fingered hands in Salzedo's grammar: place, pluck into the palm, raise.
- The mallet holders swing on a hinged shaft, ride the rebound up to the next note, and hold two mallets the way a marimbist does.
- The rake's hand swings through its strings like a pendulum.
- Every joint and gear is moved by a visible driver turning at a believable rate.
- The machines show their precision by moving through their range and landing exactly.

The goal is **met** when all three of these hold:

1. Every ruler in **Acceptance** meets its target on both assets (`tools/test_players.py --gate` passes with M0–M11 done).
2. The note budget is kept.
3. The operator has watched the before/after reel and signed it off. Their words are recorded in `LOG.md`.

**Status.** 2026-10-04: M0 done — all 26 rulers measure today's rig on both assets (`tools/test_players.py`; today's values in `the-players.today.json` and the table below), the before reel is rendered, and the M0 gate is green. M1 claimed 2026-10-04.

## The direction

The operator watched `render/film/the-chamber.mp4` (2026-10-03) and said, verbatim:

> "go hard on articulation, fluidity, and anticipatory motion in the instrument player arms. the-chamber.mp4 showed motion that was too jerky or instantaneous. We want the precision of the machines to show in their visible exploration of the range of motion, we want the gears and the joints to follow verisimilitudinous rules, and we want something like Salzedo gestures and their analogues for other instruments. This probably means string players need something like fingers instead of just a long rod that can pluck one string and rocket to the next. Similarly, I want the mallet holders to swing in a hammer arc and follow the bounce to come back up for the next note, rather than punching vertically like a stamp machine."

What each part means here:

- **Articulation.** More joints do visible work:
  - digits and a wrist on the harp arms;
  - a hinged shaft, and a second shaft on a splay joint, for the mallet holders;
  - a pendulum forearm and an open hand on the rake.

  Today the tool turns 0° in 86 s. The carriage x *is* the tool x (`formlab/rig.py:409`), and the bars elbows use 4.1° and 7.3° over the whole piece.
- **Fluidity.** Inside a phrase nothing comes to a full stop. Velocity steps only at a declared impact, and every segment joins its neighbours in position, velocity and acceleration.
- **Anticipation.** The gesture starts at least 200 ms before the sound (or 0.9 of the gap when the gap is shorter), and 415–529 ms before it when the arm has the time. 415–529 ms is the lead measured for harpists (Chadefaux et al., *Acta Acustica* 2013). The next note's preparation grows out of the last note's recovery (Stevens' legato and piston strokes; Dahl 2011).
- **Precision shown by exploring the range.** The arms make wide, deliberate, synchronised sweeps that land exactly and repeatably:
  - homing sweeps;
  - digits sliding along their strings while they wait;
  - prep heights that span the dynamics;
  - joints that use a real share of their range in every phrase, not only once.

  Today the only place this happens is the coda's slow ratchet traverses (71.43–75.71 s).
- **Verisimilitudinous gears and joints.**
  - Every moving joint has a driver you can see, turning at its mechanism's law, with declared limits, believable speeds and a little backlash.
  - Heavier parts move and ring more slowly than light ones, and the cause always comes before the effect.
  - Today nothing drives the shoulder, the elbow or the pinion, and the flywheel turns but drives nothing. The rake's leadscrew turns at 161,184 rpm.
- **Salzedo gestures and their analogues.**
  - **Harp:** placing, closing into the palm, the raise at phrase ends, sliding along the string while waiting (Lawrence & Salzedo, *Method for the Harp*, 1929, pp. 7–22).
  - **Marimba:** Stevens' four-mallet grip, his legato, piston, double-vertical and double-lateral strokes, and Moeller's full, down, up and tap strokes.
  - **Strum:** Salzedo's Aeolian flux. The hand is open, a finger leads upward and the thumb leads downward, in constant pendulum motion with follow-through.
  - **Hammer:** the piano action's let-off, free flight and backcheck.
  - **Every player:** the phrase-end release, "abrupt after abrupt, slow after slow".
- **Fingers for string players.** Each harp arm gets a thumb and three fingers on a wrist. They are placed on their strings ahead of time, load the string and release it. A run is played by fingers, not by carriage dashes. The rake, also a string player, gets an open hand rather than a rod with a comb.
- **A hammer arc that rides the bounce.** The mallet hangs on a pivoted, driven shaft and meets the bar along its normal. It rebounds with 0.3 ≤ e ≤ 0.8 and rides that rebound up to the next note's prep height. Meanwhile the carriage glides to the next bar on a smooth law, with the pawl ticking over the teeth.

## What the film shows today

These numbers come from scratch measurements on the bake of `6c326b5` and on the film's own frames (frame = round(30t)). They are **provisional**. M0 regenerates every one of them with the final ruler formulas, and the regenerated values replace these cells.

| | harp picks | rake | bars mallets |
|---|---|---|---|
| strike window (`songs/chamber.py:86,98,103`) | 90 ms (2.7 frames) | 150 ms | 80 ms (2.4 frames) |
| wind-up | 4.7 cm in 22 ms (0.7 frames) | 1.1 frames | rises 0.22 → 0.33 m in 32 ms |
| closing | 68 ms | 113 ms | drops 0.33 m in 48 ms (29 g; gravity would take 259 ms) |
| into contact → out | 3.46 → 0 m/s; stops dead at every one of 140 plucks | 2.07 → 28.4 m/s in one sample | 13.74 → 0.66 m/s on every blow, whatever the amp |
| release | 22 cm in 50 ms, peak 8.25 m/s | 100 ms | 22 cm in 40 ms (1.2 frames) |
| largest move in one frame | 20.4 cm | 84.1 cm (60.03 s) | 29.9 cm (47.50 s) |
| frame nearest the contact | 17–20 mm off, median | 31 mm median, 405 mm max | 62 mm median, 167 mm max |

- **Motion is stop-and-go.**
  - Every travel runs rest to rest, and every gap between notes holds a full stop.
  - There are 476 velocity corners over 0.1 m/s at the schedule's knots (harp 282, rake 126, bars 68), and the bounce rings add 454 more at no knot at all: ruler 6b counts 721 on the chamber.
  - The link ends move more per frame than the tools do: elbows 23.7–36.3 cm a frame.
- **Preparation is short or missing.** 38 of 229 contacts have under 100 ms of visible preparation.
  - Before `go` the arm is frozen (`rig.py:369`).
  - Where the arm has time, the only "preparation" is the 0.4 s servo slew, which is travel, not anticipation.
  - An unhurried slew leaves at the last moment the planner allows.
- **Moments.**
  - 8.5–8.7 s and 10.000 s, plucks: the link end jumps in over two frames, the string lights, and the link is gone by the next frame.
  - 13.62–13.98 s, harp_arm2's B4–C5–D5–E5 run: each note is a 50 ms snap-back, a 39 ms carriage hop of 0.109 m (peak 4.03 m/s, above `SERVO_V_MAX`) and a 90 ms poke. This is the "rocket to the next string".
  - 34.29, 40.00 and 60.00 s: rake sweeps cross 5 strings in about 2 frames. The worst screen jump of the film is 224 px, at 40.067 s.
  - 45.75–50.40 s: the bars carriages shuttle ±0.771 m every eighth note, in clicks of up to 3.2 teeth at up to 260 g. The mallet hangs, touches the bar for one frame, and is back up. It is a stamp.
- **Joints and drives.**
  - The tool never rotates, and nothing actuates the shoulder or the elbow.
  - The upper links swing faster than the forearms (379 vs 166 °/s on harp_arm0).
  - The leadscrews reach 14,571–161,184 rpm. The bars pinion steps 78° a frame on a 22.5° tooth period.
  - The flywheel's 52-tooth ring meshes with nothing and appears to crawl backwards.
  - Every ring is 6–17 Hz, too fast for 30 fps.
  - The expanded asset's hinged hammer flips 98.5° in one frame.
- **Notes.** 230 of 239 intended notes play: 9 dropped, 9 substituted, 221 as written. The expanded score plays all 298.

## What survives, and what changes

The earlier direction was a **contrast** between clicky, stepped, ratcheted motion with recoil and smooth, precise servo motion (`docs/motion-design.md:1-10`). It survives as a contrast between *mechanisms*, no longer as a contrast between *jerks*:

- **The bars carriage is still driven through rack, pinion and pawl.**
  - Where the music leaves time, it steps tooth by tooth onto its detent, every tooth countable (the coda traverses, homing, unhurried travel).
  - In the fast passages it freewheels the way a real ratchet does. The carriage glides on a smooth law while the pawl drops into each tooth, or skims the tips at speed, and every tooth passing clicks. See Q4.
- **Servo repositions stay synchronised, monotone S-curves with no overshoot.**
- **A blow still shakes the assembly** (the recoil bus, stand, rail and mast): zero at the blow, gated before the next strike, and now at a legible frequency.
- **The hinged hammer keeps its piano action**, re-geometried.

What goes:

- the cocked drop;
- the 40 ms lift;
- the `|sine|` bounce (`rig.py:360`);
- the `smooth` strike entry with its acceleration step (`rig.py:104`);
- clicks of 3–4 teeth at hundreds of g;
- the plucking rod.

No gesture is instantaneous.

**Invariants.** A milestone that breaks any of these is not done.

- **Exact contacts.**
  - For a blow, `tip_at(t) == contact` to 1e-9 m on the rig (`tools/test_motion.py:48`), the bake is within 4e-6 m (float32 rows), and the rendered felt is within 10 µm (`harness/dev/test_performance.gd`).
  - For a pluck, **the scored time t is the slip-off**:
    - at t⁻ the digit is exactly at contact + d_rel·n̂;
    - at t_place = t − stick it is exactly at the contact.

    The audio onset, the string's free vibration and the slip-off frame coincide. `test_motion.py:48` is rewritten to check both points.
  - Every new DOF (hinge, digit, splay, wrist, pivot) holds an exactly known value at the contact, and the contact is derived from it, the way `head_offset(0) = 0` works today (`rig.py:112-117`).
- **One occupancy model.**
  - `_Solver._separated` (`loam/score.py:321-363`) and `Rig._segments` (`rig.py:200-214`) change together, in the same commit.
  - `go == t_move` and `Rig.pushed == []` (`test_motion.py:59,94`).
  - Any new x motion is in both: follow-through, splay, hand windows, travel overlapping the rebound.
  - `plan_consistent` (`loam/ruler.py:1453-1479`), `harness/score_doc.gd:121-150` and `songs/clockwork.py` keep checking the same ordering. M1 defines `t_head_free` for gestures that overlap the next travel.
- **The bake is the single source of motion.**
  - The harness only plays it back.
  - Motion is a pure function of t (the film renders as parallel chunks), so any physics is closed-form in the rig.
  - A stale bake is refused, and `harness/motion_bake.gd` equals `formlab.bake.Bake`.
  - New sharp features get corner rows (`formlab/bake.py:59-77`).
- **The old rulers.**
  - Every ruler in `docs/articulated-arms.md` ("Rulers"), plus `tools/test_motion.py`, `tools/test_bake.py`, `tools/test_rail_cache.py` and the `harness/dev` tests, stays green on both assets.
  - A ruler that encodes the old stroke is rewritten in the same commit as the motion and the doc, never deleted quietly. That covers `cock ≥ 0.3·COCK`, "drop without pause", the bounce checks, the 50 ms hold, and the overshoot check at `test_motion.py:111`, which is the designed rebound and is kept.
- **The music.** Notes, times and amps stay as they are. The only planned change is the rake's spread (Q1). The synth keeps its keys (pick and shape) even where the visual contact moves. A milestone that changes no music leaves the chamber and clockwork stems bit-identical.

## The players

### The arm (every player)

- **The carriage is the shoulder: slow, small and moved last.** The two links carry the large paths. The hand, shaft or comb articulates.
  - Per stroke, the share of tip motion attributable to each joint grows distally.
  - The carriage's share is at most 15 %, except on window shifts and travels.
  - Proximal leads distal: peak speed moves outward joint by joint, at least a frame apart in strokes with an IOI ≥ 0.35 s.
- **Shoulder and elbow get drivers**, palletiser-style, with both motors on the carriage: a sector gear on the shoulder pin, and a crank (four-bar) driving the elbow through the parallelogram's second bar.
- **Masses are declared.** `build_forms` writes each part's mass (recipe volume × density) into the manifest. Heavier links accelerate less and ring lower.
- **`Rig.pose` stops forcing `root.x = tip.x`** (`rig.py:409`) for any player whose hand reaches sideways. The carriage x becomes the hand's or the pivot's x, as the planner chooses.

### Harp hands (harp_arm0/1/2)

**Anatomy.**

- **Wrist.** The palm hangs from the wristhead on a **driven wrist flex** (pin along world X; a sector or crank on the wristhead). It leads each placing, follows the melodic line (Renié), and holds Salzedo's "curved in" angle through the raise.
- **Fingers.** The palm carries a thumb and fingers 2, 3 and 4.
  - Each finger has an actuated base joint (MCP), with the middle and end joints (PIP/DIP) coupled to it by a four-bar or a tendon, so it curls into the palm.
  - The phalanges run about 1 : 0.7 : 0.55, and each ends in a horn or leather pad on a brass bone.
- **Thumb.** It has 2 DOF: it pivots at its base and folds over the 2nd finger's middle knuckle (Method p. 7). It sits high, with a wide gap to the 2nd finger.
- **Knuckle pins run parallel to the strings (world Y).** This is a new pin orientation, carried by the bake's joints table from M3. The digits curl in the plane perpendicular to the strings, and the pluck direction is 7–43° out of the string plane. Today's poke is 90°.
- **Splay.** A single fan DOF lets thumb-to-4th span 3 string gaps flat (0.33 m) and 4 gaps splayed (0.44 m). That puts arm0's D3–F3–A3 tresillo (H0–H2–H4) under one placed hand.
- **Knuckle line.** It is oblique and follows the pluck points: contact y climbs 58–96 mm a string, so the line sits at 28–41°. The wrist holds it through playing and raising (Method p. 20).
- **Drivers.** A tendon drum per digit on the wristhead (drum angle = tendon travel / r), with visible pulleys.
- **Width.** The hand overhangs its outer digits by at most 0.075 m, so neighbouring hands keep 0.15 m apart. That is the clearance the fingered planner needs; at 0.27 m the hands jam (88 drops).

**Gestures on the score.**

| gesture | where | shape |
|---|---|---|
| place | the runs at 13.57, 16.43, 19.29 and 22.14 s; every arpeggio | Digits land on their strings in playing order, "immediately after having played". In a run, the digit stays on its string through the gap. They land at ≤ 0.2 m/s (no buzz), and a group lands together. |
| pluck | every note | Stick, from t_place to t (≥ 56 ms): the digit loads the string, which is drawn displaced 12–30 mm. At t, slip-off with the string free and ringing. The digit closes into the palm in 3 frames with one settle. Unplayed placed digits stay planted (Method p. 9). |
| raise | after each run's E5 (14.11, 16.96, 19.82, 22.68 s); arm0 between tolls (5.71–20 s); arm2 at 65.0 s; the answers at 72.14 and 75.0 s; all three hands at 78.57 s | The closed hand rises ≥ 0.4 m (or to the harp's frame line where that is lower), leaning 15–35° off vertical toward its own arm. The wrist holds the knuckle line. The raise takes 0.3–1.5 s, slow after a slow ending and quick after an abrupt one (Method pp. 17–19). |
| fall and replace | before each note after a raise | The hand opens on the way down and lands placed. The raise was this note's wind-up. |
| slide along the string | waits of ≥ 1 s inside a phrase; arm1's 33.2 s rest (45.36–78.57 s) | The waiting digit glides 0.10–0.15 m from mid-string toward the top and back, silently (Method p. 20), and is back by t_place. |
| line in one hand | the hocket, 22.86–45.71 s: arm1 on H7–H9, arm2 on H11–H13 | Fingers and wrist only, with no carriage moves. This frees the jams that drop 26.07 and 33.93 s and substitute 7 × F4→E4. |
| window shift | e.g. arm2's return from 15 to 12 (0.326 m) | 4th under or thumb over. One digit stays planted as a pivot while the carriage moves (Method pp. 21–22). |
| tolling ground | 0–22.86 s | arm0 plays D3 and A3 as one hand (4th and thumb). That frees arm1 for the beat-2 answers now dropped at 6.43, 9.29, 12.14, 15.0 and 20.71 s. |
| final chord | 78.57 s | Placed together during the rest before it (arm1 returns after 33 s), played flat, closed, and raised together. |

**Clearance.**

- A digit that is not playing clears every string. The playing digit clears all but its own.
- The plectrum's flaw ends with it. Today the string runs inside the 7 mm blade at contact (`formlab/linkage.py:330`), which the tool exemption in `formlab/clearance.py:434-441` hides. That exemption is removed.

### Mallet holders (bars_arm0/1; bells_arm0/1 on the expanded asset)

**Anatomy.**

- **The chain.**
  1. The arm and its wristhead.
  2. A **driven wrist hinge**, pinned along the rail (world X) and driven by a crank or sector from a motor on the wristhead.
  3. The shaft, 0.40–0.60 m (chosen by clearance and by the arc rule below).
  4. The wound head (r 0.06).
- **At contact the shaft lies about parallel to the bar**, so the head arrives along the bar's normal ("parallel to the bar … into the bar", Kite).
- **The head swings about the hinge.**
  - The hinge turns ≥ 20° on every stroke at the tune's tempo, and ≥ 35° when the IOI is ≥ 0.7 s.
  - The elbow takes part in every stroke.
  - The head lags tip-down on the upstroke and whips on the downstroke.
- **Two shafts per holder (Stevens grip, Q2).**
  - A second shaft sits on a driven splay joint, which sets the interval during the upstroke.
  - The tune's thirds are played as double verticals or double laterals where the sticking allows.
  - Moves that are now carriage leaps become splay changes.
  - Fallback: one shaft, if clearance fails in M8.

**The stroke at the tune's tempo** (45.71–68.57 s, eighths, IOI 0.357 s). This is a legato/piston stroke, made of four phases:

1. **Downstroke.** It takes 0.35–0.45 of the IOI (125–160 ms) on a smooth law and arrives at 1.5–4.0 m/s, faster for louder notes.
2. **Contact.** A reversal with e of 0.3–0.8: the declared impulse.
3. **Upstroke: the head rides its rebound.** The upward speed is greatest just after contact and only decreases after that. The float decelerates at 0.5–1.5 g to the apex, and the apex is the *next* note's prep height. Nothing yanks the head upward.
4. **Travel.** The carriage moves from contact to contact with ẋ = ẍ = 0 at each contact, so the head comes in on a diagonal arc and lands along the normal. No slicing happens at impact.

**What that envelope allows.** At an IOI of 0.357 s, with e ≤ 0.8, the impact speed ≤ 4 m/s and the float ≤ 1.5 g, the apex can reach about 0.28 m. Prep heights at tempo therefore run from about 0.15 m (a' = 0) to 0.28 m (a' = 1).

- This is lower than today's 0.22 m hover on soft notes, because a bounce cannot carry higher in 0.2 s. Q5 asks the operator whether to break physics for size.
- The swing reads through the hinge's rotation and the elbow, not through height.
- The downstroke stays under 4 g (h ≤ 2g·T_down²).

**Dynamics.**

- Prep height and impact speed rise with the normalised amp a' and fall as tempo rises.
- An accent on beat 1 or 3 is prepared by a Dahl up-stroke: its rise starts during the previous stroke's float. After an accent comes a down-stroke, with the rebound caught low.

**Runs and hand-offs** (54.29–56.79 and 65.71–68.21 s).

- The crescendo from 0.50 to 0.85 is played as rising strokes.
- At the hand-offs (55.36 and 66.79 s), the incoming holder winds up during the outgoing holder's last notes.

**Tolls** (71.43–75.71 s).

1. A slow traverse of 1.3–2.25 s, stepping tooth by tooth on the detent.
2. A raised, cocked hold of at least 3 frames.
3. A full stroke (0.35–0.60 m prep).
4. One free bounce loop (Dahl, IOI > 1 s), then a park, high.

**Bells.** The same stroke, with a carillon spring-off so the bell rings. Their IOIs of 1.43 and 2.86 s leave room for full arcs of ≥ 35°.

**Never:**

- through the bar;
- a dead stroke (none is scored);
- a full stop between notes at tempo.

### Rake (rake_arm0)

**Anatomy.**

- **The hand.** The comb becomes an open hand on a **pendulum forearm** (a clock hand) about a driven pivot (pin along world Z), with a visible crank or sector.
- **Digits lead by direction (Aeolian flux).**
  - The 2nd finger leads the up-sweeps and the thumb leads the down-sweeps. The trailing digits fold.
  - The rasgueado catch is optional: the lead digit loads against a thumb latch during the backswing and is released at the first string.
- **The carriage only places the pivot.** It stays within `SERVO_V_MAX`. The swing carries the hand across the strings.
- **Contacts lie on the swing's arc.** The visual contact point comes from the arc, while the synth stays keyed on the scored pick (a visual-only field).

**The sweep (Q1 default).**

- The sweep slows from 18 ms a string to a fast roll of about 65 ms a string: about 0.26 s for the 1.47 m path, at 5.7 m/s, ≤ 1.0 hand-width a frame.
- Each string's onset within the roll follows the hand's path, so the sweep crosses at constant speed. The roll's first onset stays at the scored time.

**Gestures.**

- **The announcement at 21.43 s**, after 21 s of silence: a backswing of at least 0.5 s, a hold, then the sweep.
- **The isolated sweeps at 34.29 s (up) and 40.0 s (down)** take the same shape.
- **The half-note pendulum, 45.71–67.14 s** (16 sweeps, up on beat 1 and down on beat 3, period 2.86 s):
  - it never stops, and the ghost passes clear the strings in between;
  - each sweep enters the first string at ≥ 0.7 × sweep speed with no corners;
  - it follows through ≥ 0.2 m past the last string, then lifts off.
- **The two up→up pairs** each make their 1.05 m return as a visible ghost pass.

### Hinged hammer (blocks_arm0, expanded)

**Geometry.**

- The flange, pin and check stay.
- The rest angle goes from 106.5° to 20–45°, so the shank lies parallel to the block at impact.
- `head_l` grows as the lift needs: rise = head_l·sin θ_rest, so 0.154 m at 30° needs a head_l of 0.31 m.
- HAMMER becomes per-arm, and the bake header carries `head_l` per arm.

**Stroke** (piano action; Askenfelt; Goebl 2005).

1. A visible cam or whippen lift across the IOI (at least 0.714 s).
2. Let-off just before the block, then 0–20 ms of free flight.
3. The felt arrives at 1.5–3.0 m/s, scaled by amp.
4. The backcheck catches the rebound about a third of the way up the arc.
5. A repetition hold on fast repeats.

The 47 of 48 travels that are hurried today are re-timed by the same contact-to-contact overlap the mallets get.

### Phrase ends and the ending (every player)

| player | at phrase ends | shape |
|---|---|---|
| harp | listed in the raise row above | the raise |
| mallets | the top of each run (56.79, 68.21 s); after the last toll (75.71 s) | The last stroke rides its rebound into a held raise above the bar, at least 1.5 × the tempo apex, for at least 3 frames. Then the holder lifts and parks on a slow arc. |
| rake | after its last sweeps (68.57, 77.14 s) | Follow-through into an upward release at a speed matched to the phrase. |
| hammer | after the last blow | The check releases slowly to the rest angle. |
| ensemble | 78.57–86 s | Every player finishes its release with the harp raise. The three hands start within one frame of each other and end within 1 cm of the same height. The mallet holders and the rake park within the same frame. |

## Rules of the machine

Each rule says which ruler checks it. Ruler numbers refer to **Acceptance**.

1. **Driven.**
   - Every DOF that moves has a visible driver whose angle is its mechanism's closed-form function of the joint, on every baked row:
     - gears, sectors and racks: N·q + c, from the recipe's tooth counts;
     - cranks: the four-bar solution;
     - cams: the profile;
     - tendons: drum r·θ.
   - The DOFs: carriage, shoulder, elbow, harp wrist, mallet hinge, splay, thumb, digits, rake pivot, hammer cam.
   - Every gear meshes with a mate, so the flywheel meshes or loses its teeth.
   - Checked by 17.
2. **Limited and closed.**
   - Each joint limit equals the recipe's interference angle (± 1°), and motion stays at least 2° inside it.
   - Links keep their length: 1e-9 m on the rig, 4e-6 m on the bake.
   - Checked by 16.
3. **Plausible.**
   - A servo carriage moves at ≤ `SERVO_V_MAX` and ≤ 3 g.
   - The ratchet carriage moves at ≤ 3 g, apart from counted hurried travels at ≤ 5 g (ruler 19).
   - The tool tip and the digits stay ≤ 10 g, except within ±10 ms of a contact or slip.
   - No drive turns faster than 3000 rpm.
   - Heavier links accelerate less.
   - Checked by 15, 17 and 19.
4. **Bounded jerk.**
   - Every planned segment is a named timing law along a declared path, and joins its neighbours in p, v and a. The allowed laws are 3-4-5, 4-5-6-7, cycloidal, modified sine, modified trapezoid, the servo S-curve, quintic or septic Hermite with (p, v, a) boundaries, and ballistic (constant a).
   - Velocity may jump only at a declared impulse: a contact rebound, a slip-off, or a detent landing.
   - Checked by 6.
5. **Cause precedes effect.**
   - A driven part never leads its driver.
   - Gear trains declare a backlash β of 0.5–1°: on a reversal the driver takes up β before the joint turns back.
   - Proximal leads distal.
   - A string moves only while a digit holds it and rings only after the slip.
   - Shudders start at the blow.
   - Checked by 12, 15 and 17.
6. **Contact is physics, not a stop.**
   - Struck heads reverse with e in [0.3, 0.8], arrive within 20° of the surface normal, and ride the rebound.
   - Plucked strings are placed, loaded and released.
   - Nothing passes through a bar, block or string, except the played string during its stick.
   - Checked by 8, 10, 12 and 23.
7. **Synchronised arrival, exact stop.**
   - A reposition that ends in a placing or a hold has all of its axes leave and arrive within one 240 Hz sample, monotone, with overshoot ≤ 0.5 mm and at rest within one frame.
   - A reposition followed by a strike within 0.6 s blends into the stroke instead of stopping.
   - Digits placed as a group land together.
   - Checked by 13 and 22.
8. **Damped settle.** Each part rings with one declared (f, ζ) at every excitation. Heavier parts ring lower, and every ring stays legible at 30 fps. Checked by 20.
9. **Gravity reads at full size.**
   - Strokes average ≤ 4 g (s = g/ā ≥ 0.25).
   - Rebound floats decelerate at 0.5–1.5 g.
   - Checked by 8 and 9.

## Acceptance

The rulers live in a new `tools/test_players.py` (M0). It reads the rig, the bake, the score ledger and the exported camera on both assets.

- `--report` prints this table with today's values and the current ones.
- `--gate` fails if any ruler listed in the gate of a milestone marked `done` misses its target, in that milestone's scope.

**What the rig declares.** Every gesture-based ruler measures against declared structure, never against inferred structure:

- `Rig.segments(aid)` → (t0, t1, law, tag, p/v/a at both ends).
- `Rig.knots(aid)` → (t, kind ∈ {smooth, contact, slip, detent, click, place}, declared Δv).
- The ring terms (amp, f, τ).
- The prep function h(a', IOI).
- From M4, part masses.

The bake header carries all of these, the way it carries clicks and blows today. Segment tags come from a closed vocabulary: travel, wind-up, stroke, rebound, float, release, place, stick, close, raise, fall, slide, sweep, follow-through, ghost, home, hold (`release` is today's lift off the string or bar after a contact, `Rig.path_at`'s release phase; `formlab/segments.py` holds the list). Until an arm's motion is tagged, its tag-based rulers report the fallback formula and are not gated.

**Notation.**

- E(part, d̂) is a part's capsule extent projected on the direction d̂ (2r + |seg·d̂|, from `formlab/clearance.arm_capsules`).
- Frames are t_k = k/30.
- IOI is the time between onsets on the same arm, or on the same holder.
- a' is the amp normalised per voice: (amp − min)/(max − min).
- *Impulse frames* are the frames whose interval contains a declared contact, slip or detent landing, or a click's move interval.
- A *hurried travel* is a ratchet-carriage travel whose minimum smooth time, at 3 g and 1.0 E a frame, exceeds its contact-to-contact window.
- A *gap* is the time from one contact's end to the next contact on the same arm.

| # | ruler | measure | today | target |
|---|---|---|---|---|
| 1 | strobe | ρ = \|Δp_k\| / E(part, Δp̂_k) for the tool or head, each digit tip, the palm, the wrist and elbow pins; for links, R·\|Δθ_k\| at each link's far end | max ρ of the tool: harp 1.85, rake 6.70, bars 2.49 (hurried 12 + 2), bells 1.75, hammer 2.79; wrists 1.19–4.91; elbows 0.72–6.04 (23.7–62.3 cm a frame); upper links to 4.96; hammer head 98.5° a frame | max ρ ≤ 1.0 (≤ 1.5 on impulse frames and hurried travels); p95 over active frames ≤ 0.5; harp palm ≤ 0.5 outside slip frames; R·\|Δθ\| ≤ max(link width, E_head); ≤ 20° a frame for parts under 0.25 m |
| 2 | screen | ρ_px = \|Δq_k\| / projected extent, from `render/film/camera.json` (exported from `film_director.gd`, never re-implemented) | ρ_px max 1.82–6.14 (rake); 271 jumps over 30 px; max 224 px at 40.067 s | ρ_px ≤ 1.0 off impulse frames. Report only: jumps over 30 px and max px, under the frozen M0 camera and the current one |
| 3 | preparation | On `Rig.path_at` without rings, h(t) = (p − c_i)·n_i. The action A_i is the last interval before t_i with dh/dt < 0, starting at t_apex. The wind-up W_i is the maximal interval before t_apex with dh/dt > 0. The lead is L_i = t_i − start(W_i). For plucks, c_i is the placing point and t_i is t_place. | the lead is the strike window: harp 90 ms, rake 150, bars 80, bells 140, hammer 80 (209/230 under 100 ms); wind-up 0.66–1.68 frames; hand-off wind-ups 277 ms late | \|W_i\| ≥ 4 frames (≥ 6 when the gap is ≥ 0.5 s); Δh over W_i ≥ 0.25·h(t_apex); L_i ≥ min(200 ms, 0.9·IOI); L_i ≥ 415 ms when the gap is ≥ 1 s; at hand-offs the incoming wind-up starts at or before the outgoing last hit |
| 4 | action | T_down = t_i − t_apex for struck heads; the approach to t_place for plucks | bars 1.44 frames (48 ms, 0.13·IOI at tempo); bells 2.52; hammer 1.44; pluck approach 2.04; rake 3.40 | IOI ≤ 0.5 s: 0.35–0.45·IOI; IOI > 0.5 s: 125–250 ms; pluck approach ≥ 2.5 frames |
| 5 | no rest in a phrase | In each gap with IOI ≤ 0.6 s (and anywhere in the rake's 45.71–67.14 s pendulum), every interval with \|v\| < 0.15·v_peak of that gap that lasts more than 1 frame must contain a reversal of the principal-axis velocity, with \|a\| ≥ 0.5 g throughout. Exempt: place, stick, planted digits, and declared holds after gaps ≥ 0.8 s. | bars 16/16 and 20/20 gaps; harp_arm1 8/8, harp_arm2 3/15; rake 15/15 (stops to 1.12 s) | 0 violations |
| 6 | smoothness | **6a** At smooth knots \|Δv\| ≤ 1e-3 m/s and \|Δa\| ≤ 0.05·a_peak of the segment (one-sided 5-point stencils, ε = 1e-5 s on the rig); impulse knots match their declared Δv. **6b** One-sided differences at 10 µs: count of \|Δv\| > 0.02 m/s more than 20 µs from any declared knot. **6c** Inside a segment, max \|Δa\| per 1 ms ≤ 1.1·C_j(law)·h/T³·1e-3. | 6a: harp strike starts Δv 3.46 m/s; rake 126 knots to 28.4 m/s; bars Δa 106 + 147, hammer 525. 6b: 721 (harp 141, rake 126, bars ring corners 454); 476 at the old \|Δv\| > 0.1 m/s rule. 6c: quintic+cocked 7.6× its bound (bells 13.7×); quintic+sine, quintic+cocked and ratchet are not allowed laws | 6a: all pass; 6b: 0; 6c: all pass; every segment uses an allowed law |
| 7 | impact | v_in·n at contact (one-sided differences, 1e-5 s, on the rig) | 13.75 m/s on every blow; bells 7.86; hammer 4.13 (\|v\| 10.3); flat in a' | bars and bells 1.5–4.0 m/s; hammer 1.5–3.0; per arm, Spearman(v_in, a') ≥ 0.9 and v_in(a' max)/v_in(a' min) ≥ 1.5 (a flat-amp arm: CV ≤ 5 %) |
| 8 | rebound and float | e = −(v⁺·n)/(v⁻·n); the upstroke from t_i + 5 ms to t_apex | e 0.048 (bars), 0.084 (bells), 0 (hammer); a 38 ms scripted lift at −83 to +79 g; apex 0.23 m, park 0.33 m | e in 0.3–0.8; upward speed non-increasing and a_n between −1.5 g and −0.5 g throughout; t_apex − t_i ≥ 0.5·(IOI − T_down); IOI ≤ 1 s: apex = h(a'_{i+1}, IOI_{i+1}) ± 1 cm; IOI > 1 s: first apex = (e·v_in)²/(2·a_float) ± 10 %, then park at h ± 1 cm |
| 9 | gravity scale | strokes: s = g/ā with ā = 2d/T² | bars 0.034 (reads as 1:29); bells 0.105; hammer 0.044 | s ≥ 0.25 on every stroke (floats are checked by 8) |
| 10 | hammer arc | (a) shaft rotation Δφ = \|φ(t_apex) − φ(t_i)\|; (b) world head path over [t_apex, t_i]: sagitta/chord, curving toward the pin's side; (c) felt or head velocity at t_i⁻ against the surface normal; (d) elbow angle change per stroke | (a) 0° on mallets, hammer 108.6°; (b) 0, hammer 0.174; (c) 0°, hammer 66.5°; (d) bars 4.1° and 7.3° a stroke, bells 4.8° and 6.5°, hammer 6.1° | (a) ≥ 20° at IOI ≤ 0.5 s, ≥ 35° at IOI ≥ 0.7 s (hammer ≥ 20°); (b) ≥ 0.05; (c) ≤ 20°; (d) ≥ 5° |
| 11 | contact frame | \|p(round(30t)/30) − contact\| for struck heads | bars 62 mm median, 167 mm p90 and max; bells 11–24 / 70 / 103 mm; hammer 18 / 141 / 141 mm | median ≤ 25 mm; p90 ≤ 55 mm; max ≤ 75 mm |
| 12 | pluck | Exactness at t_place and t⁻. Stick = t − t_place, where t_place is the first time the pad is within 0.5 mm of the ray c + s·n̂ (s in [0, d_rel]) and stays on it. Also: d_rel; polarisation asin(\|n̂·ẑ\|); digit velocity at the slip; closing; string displacement against the pad; string deflection direction at the release frame. | a 3.46 m/s poke at 90° that stops dead at the string; stick 0.14 ms; d_rel 0; the drawn string jumps 17–34 mm at the slip and bends against n̂ on 94 of 141 plucks | exact to 1e-9 on the rig; stick ≥ 56 ms; d_rel 12–30 mm; 7–43°; \|Δv\| ≤ 0.05 m/s at the slip with v·n̂ of 0.2–2.0 m/s; MCP within 2° of its stop by t + 3 frames; string = pad ± 0.5 mm during the stick and free within one bake row of t; deflection within 5° of n̂ |
| 13 | place, plant, slide, raise | **place:** \|v\| at t_place; spread of a group's landings; placing order; run placing. **plant:** unplayed placed digits relative to their strings while a sibling sticks, slips or closes. **slide:** in waits of ≥ 1 s. **raise:** Δ = p(t_raise_end) − p(t_close). | place at 3.46 m/s, 2.9 ms within 1 cm; no digits; slide 0 m, 220 mm off the string in every wait; raise 0 m in 0.05 s; final chord ends 1.26 m apart; harp_arm2's run places 178 ms late | **place:** ≤ 0.2 m/s; ≤ 1 bake row; order = playing order; in runs t_place ≤ previous slip + 1 frame. **plant:** ≤ 0.5 mm. **slide:** 0.10–0.15 m along ŷ, ≤ 0.5 mm off the string, no displacement, back by t_place. **raise:** Δ·ŷ ≥ 0.4 m (or to the frame line); 15–35° from ŷ toward the arm (Δ·ẑ < 0); digits clear the strings; knuckle-line drift ≤ 3°; T_raise = clamp(k·dur_last, 0.3, 1.5 s) with Spearman(T_raise, dur_last) ≥ 0.8; final chord starts within 1 frame and ends within 1 cm |
| 14 | strum | Entry ratio \|v(t_hit)\| / (L_path/(t_end − t_hit)). Follow-through: the arc length from t_end until \|v\| ≤ 0.1·v_sweep. Corners: knots with ∠(v⁻, v⁺) > 2° or \|Δ\|v\|\| > 0.05 m/s. Also speed max/min along the sweep, per-frame hand ρ and the carriage. | entry ratio 0.10 (2.1 → 18–28 m/s); follow-through 0 m; 126 corners; speed ratio 2.12; comb ρ 6.70; carriage 21.5 m/s, 4.8 g | ≥ 0.7; ≥ 0.2 m; 0 corners; ≤ 1.2; ρ ≤ 1.0 every frame; carriage ≤ `SERVO_V_MAX` and ≤ 3 g (≤ 6 m/s on today's comb until M9) |
| 15 | proximal → distal, weight | For joints with ≥ 10 % share of a stroke: the order of peak \|ω\| and peak \|α\|; α per link against mass; the share \|J_j·Δq_j\|; tip and digit acceleration outside ±10 ms of contacts and slips and outside click intervals; phase durations | shoulder share above elbow on every arm (bars 0.77/0.23); ω lags −1 to 23 ms (harp), 0 (struck); tip p99 13–81 g, harp max 352 g; harp releases 1.5 frames, bars strokes 2.4, releases 1.2 | proximal → distal, ≥ 1 frame lag at IOI ≥ 0.35 s; heavier links have lower α; shares non-decreasing distally, carriage ≤ 15 % outside travels and shifts; ≤ 10 g; non-impulsive phases ≥ 2.5 frames; digit closing 3 frames |
| 16 | joint use and limits | Coverage C_j = \|∪ q_j over segments not tagged `home`\| / span_j. The span is recomputed by IK on the current geometry: harp picks 0.05–0.95, bars at 0.2–0.8 of their length, each × {contact, hover}. Also: untagged motion; velocity reversals inside a segment; limits. | over the piece: bars elbows 15 % and 31 %; harp_arm0/1 shoulders 9 % and 18 %; rake 78 %/73 %; no limits | per phrase ≥ 25 % for each primary joint, over the piece ≥ 40 %; 0 m of untagged path; reversals ≤ the law's own; limits = interference angle ± 1° and motion ≥ 2° inside them |
| 17 | drives | By mechanism type. **Gear:** \|θ_D − N·q − c − b(t)\| ≤ 4·2⁻²³·max(1, \|θ_D\|), with \|b\| ≤ β/2, and centre distance = module·(z₁+z₂)/2 ± 0.5 mm. **Crank:** loop closure ≤ 1e-6 m. **Cam:** follower gap ≤ 0.1 mm. **Tendon:** Σrθ + free spans constant ± 0.1 mm. Also: driven share, rpm, backlash order. | shoulders and elbows driverless; leadscrews to 161,184 rpm (rake); every rack pinion out of mesh (bars_arm0 phase 16 mm, teeth overlap 12.3 mm); flywheel unmeshed, its belt slips 114 mm | every type passes; 100 % driven; ≤ 3000 rpm; on every reversal the driver takes up β before the joint reverses; every gear has a mate |
| 18 | aliasing | For every periodic visible feature (teeth, spokes, thread starts; period P = 360°/count), the per-frame \|Δθ_k\| | pinion 78° a frame on 22.5°; leadscrew threads to 28,000° a frame; pawl roller 565°; flywheel −4.2° a frame on 6.9°, reads backwards | \|Δθ_k\| ≤ 0.5·P with the visual direction matching, or the blur sheath is on for that frame (on iff \|Δθ\| > 0.5·P, 10 % hysteresis) |
| 19 | ratchet | **Stepped travel** (each step can take ≥ 3 frames): per-frame carriage \|Δx\| and detent dwell. **Freewheel travel:** law, acceleration, ẋ and ẍ at contacts, pawl state, click per tooth. Also the hurried-travel count and its ceilings. | stepped: a tooth a click but 53 mm a frame, dwell 0.72; freewheel travels on the ratchet law at up to 260 g, 3.2 teeth a click; hurried: bars 12 + 2, hammer 16 | **stepped:** ≤ 1 tooth (47 mm) a frame; dwell ≥ 0.5 of every step. **freewheel:** a smooth law, ≤ 3 g, ẋ = ẍ = 0 at contacts, monotone; the pawl drops per tooth below 15 teeth/s and rides the tips above that; a click per tooth. **hurried:** ≤ today's count until M8, ≤ 6 at the end, each ≤ 5 g and ρ ≤ 1.5 |
| 20 | rings | Declared ring terms per part: the baked channel minus the scored path, against the sum of declared rings; f and ζ = 1/(2πfτ) per part; amplitude projected through camera.json; sampled at 120 Hz from the bake | 8–17 Hz; bounce seen at 16 Hz (6.4 px), detent 3 px; three tool frequencies an arm; today's ring declaration misses the rectified bounce and the replaced detent (15 mm residual) | match ± 0.1 mm; one (f, ζ) per part; lower f for heavier parts; each ring has f ≤ 6 Hz and is visible ≥ 1.5/f s, or ζ ≥ 0.4, or stays under 0.5 px |
| 21 | intent | Spearman(apex height, a' of the next note); height against tempo; holds; accents at tempo | apex 0.33 m (hammer 0.26) whatever a' and tempo; no holds; accents rise at 0.78–0.89 IOI | ≥ 0.9 per arm; non-increasing with tempo at equal a'; a ≥ 3-frame hold at the apex only after gaps ≥ 0.8 s (tolls, bells, phrase starts); an accent's rise begins ≤ t_{i−1} + 0.5·IOI |
| 22 | precision | **sync:** for each reposition ending in a placing or hold, each placing group and each homing sweep: start and arrival skew across all moving channels, overshoot, settling. **repeat:** strokes with equal (arm, contact, a', IOI, next a', next IOI), as time-normalised paths. **home:** each arm, in its first rest ≥ 2 s, tagged `home`. | no sync check; no homing; repeats exact | **sync:** skew ≤ 1/240 s; overshoot ≤ 0.5 mm; \|v\| < 1 mm/s within 1 frame of arrival. **repeat:** ≤ 1 mm RMS. **home:** sweeps ≥ 90 % of reach_x and ≥ 80 % of each primary joint span at ≤ 0.5·`SERVO_V_MAX`, and lands on its home detent to 1e-9 m |
| 23 | no penetration | Signed distance at every 120 Hz rig sample: head against bars and blocks; every digit and palm against every string (except the played string during its stick); hand or comb against the strings outside the sweep's contacts | string inside the blade at every pluck (−9.5 mm; −36 mm to the tool capsule), hidden by an exemption; heads touch at 0 | ≥ 0 everywhere; the tool exemption is removed |
| 24 | phrase ends | The release after each listed phrase end, for every player kind; the ensemble ending | no release gesture: harp 0.05 s with no rise; bars hold 0.22 m; rake 0.1 s without follow-through; release time constant (Spearman 0); the ending's parks spread over 4.3 s (expanded 10.3 s) | each release is present and shaped as in the table; per kind, Spearman(release time, dur_last) ≥ 0.8, where dur_last is how long the last note sounds (its ring, score.json `dur`, cut by the player's next contact or the end; with fewer than 3 phrase ends, or all alike, it is reported, not judged); ending synchronised as described |
| 25 | notes | The composer ledger in score.json (`stats.intended`, `as_written`, `substituted`, `dropped`, written by `ask_pluck` and `ask_rake`); expanded refusals; stems | 9/239 dropped; 221 as written; 0/298 | chamber: ≤ 9 drops after every milestone, ≤ 6 at the end, ≥ 228 as written at the end; expanded: 0 refusals (its asserts); milestones without music changes leave the stems bit-identical |
| 26 | invariants | Every ruler in `docs/articulated-arms.md`; `test_motion`, `test_bake`, `test_rail_cache`, `test_score_plan`; the `harness/dev` tests | green | green on both assets |

**The reel.** `tools/players_reel.sh` stacks *before* (left; the bake and assets of `6c326b5`, rendered once by M0 into `render/players/before/`) and *after* (right) at the same score time, at 960×540, captioned with the time.

| # | span | shot | what to watch |
|---|---|---|---|
| 1 | 8.57–11.43 s | arm0-close | tolls and the 10.000 s retract |
| 2 | 13.50–14.40 s | arm2-run | the run |
| 3 | 21.0–22.0 s | rake | the announcement |
| 4 | 25.71–28.57 s | overhead | tresillo and hocket |
| 5 | 39.5–40.5 s | rake-close | the sweep |
| 6 | 45.71–48.57 s | bars-close | the tune |
| 7 | 54.29–56.79 s | bars-ratchet | the run and the hand-off |
| 8 | 71.0–76.0 s | pullback | tolls and answers |
| 9 | 78.0–86.0 s | all-arms | the chord and the ending |
| 10 | one blow | expanded asset | a blocks_arm0 blow |

Moments 2, 6 and 9 repeat at quarter speed. Each milestone renders only its own moments. The full 1080p film is rendered once, at M11, through `tools/render_film.sh` (offscreen by default).

**The final criterion is the operator's sign-off on the M11 reel and film.** Their words, dated, go into `LOG.md` and into M11's status.

## Milestones

**Each iteration of the loop:**

1. Take the first `open` milestone whose prerequisites are `done`.
2. Claim it: a `Claimed` line in its status, committed alone (the `docs/plans/README.md` rule).
3. Do the work. Tune in scratch with `--rails=keep`, then replan once at the end.
4. Run every ruler on both assets, plus `tools/test_players.py --gate`.
5. Render the milestone's reel moments through the reel tool (never in a visible window) and send the clip to the operator in chat.
6. Write a dated `LOG.md` entry.
7. Set the status to `done <date>`, with the measured ruler values.
8. Commit only the files the work touched (never `soundgarden/`), then push.

If an open question is still unanswered when its milestone is claimed, the milestone proceeds on the default. The default is recorded in the status and in `LOG.md`, and the work is revisited if the operator answers otherwise.

Only these stop the loop:

- a note budget that the milestone's own fallback cannot keep;
- a failed invariant that cannot be fixed inside the milestone;
- the M11 sign-off.

Geometry milestones (M4, M5, M7, M8, M9) first send a turntable of the new part, as a preview that does not block the work. The loop ends when the M11 sign-off is recorded.

| # | milestone (size) | needs | delivers | gate (rulers, scope) | status |
|---|---|---|---|---|---|
| M0 | Ruler first (M) | — | `tools/test_players.py --report/--gate`, with every ruler implemented on today's rig (fallback formulas where tags are missing); the `Rig.segments/knots` API declaring today's segments, so 6b reproduces the corners; the composer ledger in score.json; `harness/dev/export_camera.gd` → `render/film/camera.json`; `tools/players_reel.sh` (extends `contrast_reel.sh` with a `--moments` list); the 10 before clips in `render/players/before/` (local, regenerable); every "today" cell regenerated and pasted into this file | counts exact and continuous values within 2 % of the regenerated table; 26 | done 2026-10-04: 389/572 results (chamber/expanded), 223/328 FAIL against target; the declared structure is read by `formlab/segments.py` (not `Rig`, which would replan the rails for no motion change) until the rig declares its own from M1 |
| M1 | Mallets ride the bounce (L) | M0 | **stroke:** legato/piston stroke on today's heads; thrown downstroke; rebound; rebound-led float to h(a', IOI); Dahl up-strokes before accents; bounce loop then park at IOI > 1 s; tolls with a cocked hold. **path:** the head follows the arc the M5 hinge will make (about a virtual pin) and the elbow takes part. **ratchet:** the carriage travels contact to contact (ẋ = ẍ = 0 at contacts) as a freewheel (Q4), with step-and-dwell kept where time allows; pawl ride/drop and a click per tooth. **planner:** `t_head_free` semantics in `_Solver` (`_feasible`, `_separated`), `Rig._windows/_segments`, `motion_timing` floors, `loam/ruler.py` `plan_consistent`, `harness/score_doc.gd`, `songs/clockwork.py` (alternates only, never the originals). **also:** bars homing sweep; `cocked`, the 40 ms lift and the `\|sine\|` bounce retired, along with the rulers that encoded them; bells get the same stroke | 3, 4, 5, 6, 7, 8, 9, 10 (b, c, d), 11, 19, 21, 22 (bars, bells); 1 (bars head); 25, 26 | claimed 2026-10-04 (session 01KzHpLf) |
| M2 | Servo anticipation and the slow rake (M) | M0 | **slews:** unhurried slews leave when the arm is free, capped at t_move = max(free_at, t − approach − min(idle, travel + 0.25 s)), with the refusal change measured (> 2 extra refusals → keep the cap tighter). **entries:** smooth strike entries for picks and rake. **homing:** sweeps for the servo arms. **rake (Q1):** the slow roll, with onsets along the path, run-up, follow-through, and the interim carriage at ≤ 6 m/s | 3 (contacts with IOI ≥ 0.25 s), 5 (rake gaps; harp gaps without a reposition), 6, 14 (interim), 22 (harp, rake); 25, 26 | open |
| M3 | Bake v2 (M) | M0 | `loam-motion/2`: a generic per-arm joints table (name, parent, axis, origin, limits, driver, per-row angle); per-arm `head_l`; segments, knots and rings in the header. Updates `formlab/bake.py`, `harness/motion_bake.gd`, `harness/dev/test_clockwork.gd`, `dump_bake.gd`, `export_motion.gd`, `dump_clicks.gd` and `harness/film_director.gd`; `/1` is refused with a clear message. No visual change. | three moments render pixel-identical before and after; 26 | open |
| M4 | The drives (L) | M3 | shoulder sector gear; elbow crank; a motor for the pinion; multi-start leadscrews or belts (≤ 3000 rpm); the flywheel meshes or loses its teeth; blur sheaths for aliasing features; limits from interference sweeps (`test_linkage_tools`); backlash state; part masses in the manifest | 16 (limits), 17, 18; 26 | open |
| M5 | The hinged mallet and the hammer (L) | M1, M4 | the driven wrist hinge (pin along X) with its crank; a 0.40–0.60 m shaft parallel to the bar at contact; the arc about the pin; whip and lag; the bells' spring-off; the hammer re-geometried (20–45° rest, `head_l` sized to the lift, let-off, free flight, backcheck, repetition hold; HAMMER per arm) | 1, 7, 8, 10, 15, 16, 17, 22, 23 (mallets, bells, hammer); 25, 26 | open |
| M6a | Fingered planner: prototype (M) | M2 | in scratch: `_Solver` with harp hands (thumb + 3, splay to 4 gaps) and two-shaft holders; look-ahead placing; yielding; harp windows 0.20/0.15 s. Measures drops, as-written count, refusals, harp carriage moves and hurried bars travels on both songs. **Go:** ≤ 6 drops, ≥ 228 as written, harp carriage moves ≤ 50, hurried travels ≤ 6. **No-go:** fingers take a per-note pose with no look-ahead, and the splay is cosmetic only. | the go/no-go numbers recorded | open |
| M6b | Fingered planner: integration (L) | M6a | the planner behind `hands=`: `_Solver.commit/_feasible/finalize`; `Rig._segments` mirrors it; `formlab/layout_search.py` `_mech_key` and the rail-cache event fields (`finger`, `window_lo`); `songs/clockwork.py` `can_play` round-trips | flag on in a scratch plan: 25; `test_score_plan`; 26 | open |
| M7 | The hands (XL) | M3, M4, M6b | **hand:** `formlab/hand.py` (palm, wrist flex, 2-DOF thumb, fingers with MCP and coupled PIP/DIP, pads, splay fan, tendon drums and pulleys); capsules and clearance names; rail search with hands (`plan_arms` finds rails with string gap ≥ 0.004 m). **gestures:** the harp gestures in `Rig`, the scored time as the slip, the string drawn displaced during the stick, a per-string `cross_axis` in `wire_string.gdshader` set from the pluck angle, harp raise and slide. **planner:** flag on. | 1, 3, 4, 5, 12, 13, 15, 16, 22, 23 (harp); 25, 26 | open |
| M8 | Two-mallet holders (L) | M5, M6b | the second shaft on a driven splay (Stevens grip); double verticals and laterals for the thirds; holders planned as two-digit hands; fallback to one shaft if clearance fails | 19 (hurried ≤ 6), 1, 10, 22, 23 (bars); 25, 26 | open |
| M9 | The rake's hand and pendulum (M) | M3, M4, M7 | the pendulum forearm on a driven pivot (pin along Z, from the joints table); an open hand reusing `hand.py`, with the lead digit swapping by direction; constant motion with ghost passes; visual contacts on the arc, with the synth keyed on the scored pick; the carriage back within `SERVO_V_MAX` | 1, 5, 6, 14, 15, 17, 23 (rake); 25 (stems identical apart from Q1); 26 | open |
| M10 | Settles, phrase ends and the ending (M) | M7, M8, M9 | rings declared and retuned or damped (`RING_HZ` is 14 today; every ring is 6–17 Hz); phrase-end releases for every player; the ensemble ending; holds after long gaps; arm1's 33 s rest as slow exploration | 16 (coverage), 20, 21, 24, and every ruler on every scope | open |
| M11 | The film, the reel and the sign-off (M) | M10 | close shots aim at the hand or head (`film_director.gd`; today they aim mid-arm); camera.json re-exported; the full 1080p film; the full reel; both sent; sign-off recorded | 2 and everything else at target on both assets; the operator's sign-off | open |

## Planner consequences and the note budget

- **Harp windows stay at 0.09/0.05 s until M6–M7.** With point arms, fuller harp strokes break the budget: 0.12/0.05 gives 17 drops and 0.20/0.10 gives 34. M2 draws its anticipation from idle time instead. Unhurried slews can take as long as they like (taking `SLEW_S` from 0.4 to 0.8 cost no notes).
- **Mallet travel is charged in series with the stroke today.** The 0.14/0.08 `motion_timing` defaults give 17 drops. M1 overlaps travel with the whole contact-to-contact window *before* lengthening the downstroke. A 0.771 m leap is 16 teeth (`motion_timing.teeth`). As a freewheel on a 3-4-5 law over the 0.357 s window it peaks at 3.6 g, so it is a counted hurried travel, inside the 5 g ceiling. Q2's second shaft and M6's look-ahead are what bring the hurried count down.
- **Fingers buy time back.**
  - Thumb-plus-three hands with 0.15 m between outer digits played 233/239 as written in a scratch experiment at 0.20/0.15 s windows. That experiment also moved the arms' home positions, so M6a re-measures it with look-ahead and yielding switched off and on before anything is integrated.
  - Fuller gestures cost time again: 0.40/0.40 s windows fall back to about 220 as written.
- **The budget.** Drops stay at 9 or fewer after every milestone. The composer's own ruler allows 11, and that headroom is not spent.

## Costs

- **Rail replans.**
  - Any edit to `rig.py` or to a module in `GEOMETRY_SOURCES` costs a full rail replan on both assets: 24–30 min each as measured, up to 75 min per `docs/plans/rail-cache-key.md`.
  - Gesture constants change the swept volume, so they cannot leave the cache key.
  - Tune with `--rails=keep` in scratch, then replan once at the milestone's end (`stale_rails` fails `test_gantry`).
- **Renders.**
  - Offscreen rendering (llvmpipe) costs about 0.25 s per 960×540 frame and about 1 s per 1080p frame.
  - Milestones render only their own moments. The full film is rendered once, at M11.
  - `render_film.sh` deletes `render/film/frames`, so copy anything worth keeping to `render/players/` first.
- **Assets.**
  - After a rebuild, run `godot --headless --path harness --import`.
  - Godot runs `--headless` for rulers and `tools/offscreen.sh` for captures, never in a visible window.
  - Rebuilt GLBs are committed (LFS, about 200 MB each) only at the end of a geometry milestone (M4, M5, M7, M8, M9), with their sha recorded in `LOG.md`. Intermediate rebuilds stay local.

## Non-goals

- **Changing the music**, beyond the rake's roll (Q1). Notes, times and amps stay.
- **Salzedo effects the score does not ask for:** harmonics, étouffés, thunder, tam-tam, flux variants.
- **Gaze heads or "breathing" torsos** (the Jaquet-Droz kind).
- **A physics engine or per-frame state.** Every motion stays closed-form in t.
- **String physics beyond the drawn stick displacement and the existing clips.**
- **A power train for the flywheel.** It only has to mesh honestly.
- **Game integration and new pieces.**

## Open questions for the operator

Each has a default, and the loop proceeds on the default when its milestone comes up.

1. **The rake's sound against its legibility.** At 18 ms a string the hand would cross 0.6 m a frame, whatever carries it.
   - **Default:** slow it to a fast roll of about 65 ms a string (a 0.26 s sweep), with onsets following the hand.
   - **Alternative:** keep the 18 ms spread and render a 4-subframe shutter for the sweep alone.
   - Needed by M2.
2. **Two mallets per holder.** This is the marimba's version of fingers. It cuts the bars carriage moves from 58 to 36, and the fast ones from 36 to 20.
   - **Default:** yes, in M8.
   - **Fallback:** one shaft per holder, if clearance fails.
3. **Rendered motion blur.**
   - **Default:** no. The motion itself must meet rulers 1 and 2.
   - The one exception would be Q1's alternative.
4. **The ratchet in fast passages.** A real ratchet freewheels: the pawl drops into each tooth while the driven part keeps moving.
   - **Default:** in fast travel the bars carriage glides on a smooth law at ≤ 3 g (≤ 5 g for counted hurried travels), with the pawl and a click on every tooth. Stop-on-the-detent stepping is kept wherever each step can take at least 3 frames.
   - **Alternative:** keep step-and-dwell everywhere, with steps of ≤ 2 teeth at ≥ 60 ms. That costs notes in the tune and keeps per-frame jumps of 1–2 teeth.
5. **Physics or size for the mallet at tempo.** A rebound-led stroke at the tune's 0.357 s IOI can rise only about 0.15–0.28 m, which is less than today's 0.22–0.33 m cock on soft notes.
   - **Default:** physics. The arc reads through the hinge and the elbow.
   - **Alternative:** an active wrist lift that throws the head higher than the bounce would carry it.

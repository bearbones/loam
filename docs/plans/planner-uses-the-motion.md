# The score planner derives its timing from the motion vocabularies

**Claimed 2026-09-18 04:15 PDT** by Claude-Session
https://claude.ai/code/session_01SfoJujiAJsKYkejLtNGvQf

**Status 2026-09-18 06:40 PDT — landed.** `loam/motion_timing.py` is the one
place both worlds ask what a move costs: `loam/score.py` charges it,
`formlab/rig.py` loads it by path (keeping `formlab` numpy-only for Blender)
and `harness/clockwork_motion.gd` mirrors its seven constants by hand, with
a new parity check in `tools/test_motion.py` holding the mirror to the
original — it caught `SERVO_V_MAX := 1.2` against `3.0` the first time it
ran. `_Solver.travel` now measures the world distance along the rail
(`span_m`, `WORLD_SCALE = 3`) and charges the arm's vocabulary for it;
`Actuator.travel_s` survives only as a per-index floor. `t_move` is physical
and therefore final: `_Solver._push` does the pushing where the plan is
made, `Rig._windows` takes `g0 = t_move` as given, `Rig.pushed` records any
start the rig still has to move, and `test_motion` insists it is empty on
both assets. The occupancy model gained a third phase — an arm owns the
interval it crosses until it arrives, then only the strings it plays, then a
point.

**Two departures from the acceptance.** (1) *"every mallet travel clicks at
90 ms a tooth"* is not attainable at this tempo and was not forced:
`blocks_arm0` must cross 0.825 m — seventeen teeth, 1.58 s unhurried —
inside a 1.07 s window. The rulers assert the physical floors instead (a
click no faster than `CLICK_MIN_S` and spanning no more than
`CLICK_TEETH_MAX = 4` teeth; a slew no faster than `SERVO_V_MAX`) and report
the unhurried fraction: 105 of the Chamber's 174 repositions get the whole
time the vocabulary wants, the fastest click is 45 ms spanning 3.2 teeth,
and the fastest slew is 2.82 m/s. (2) `SERVO_V_MAX` was raised from the
sketch's 1.2 m/s to 3.0, because the shipped Chamber's own p90 demand
measured 2.82 m/s and a 1.2 m/s carriage cannot answer a single-string harp
step in the 39 ms the score leaves it. Two edits in `songs/chamber.py` paid
the rest: eighths up the marimba instead of sixteenths, and the answer voice
taking the neighbour below H[7]. Chamber: 230 events of 239 intended, nine
dropped (3.8 %, its ruler allows 5 %), zero conflicts, 27 of 257 asks
refused; the expanded arrangement's 298 events plan with no refusals at all.

The replan cost two repairs outside the plan's `Where:` list, both forced by
the new harp rails. `godot --headless --path harness --import` is now part
of the ruler ritual (`docs/articulated-arms.md`): a game run never
re-imports, so the harness posed the cached meshes at the old link length
until it ran. And `formlab/gantry.py` brackets arms greedily in layout
order, which left `harp_arm1` nowhere to stand once `harp_arm0` had taken
the room; `Blocked` now carries the arm that found nothing and
`plan_gantries` brackets it first and tries again, once per arm. Every ruler
is green on both assets.

**Where:** `loam/score.py` (`Actuator`, `_Solver.travel`, `_Solver.plan`,
`_Solver._separated`, `approach_s`), `harness/clockwork_motion.gd` and
`formlab/rig.py` (the constants; `_windows`, `_schedules`),
`tools/test_score_plan.py`, `tools/test_motion.py`, `docs/motion-design.md`,
`docs/clockwork-todos.md` (its P2 "physical trajectory limits" — this plan
is the motion half of it).

**Problem:** the planner's travel time is `|index diff| · travel_s` per
actuator and `approach_s` is a constant; the rig then moves in
`teeth(dx) · CLICK_S` (stepped) or `SLEW_S` (servo) and starts as early as
the arm is free. Two mismatches: (1) the planner can schedule a mallet
reposition of 12 teeth (1.08 s of clicks at 90 ms) in a window where the
rig has 0.3 s and must click at the 40 ms floor — the "clicks come no
faster than 40 ms and each spans several teeth" fallback, which looks
hurried; (2) the planner's clearance model charges intervals from
`t_move`, so `_schedules()` re-checks occupancy for early starts — two
models of the same thing.

**Work:**

1. A shared timing module `loam/motion_timing.py` (pure functions, no
   numpy dependence on `formlab`): `stepped_travel_s(dx)`, `servo_travel_s`,
   `approach_s(kind)`, the constants imported by `formlab/rig.py` (which
   the harness mirrors by hand — add the constants to the parity check in
   `test_motion`).
2. `_Solver.travel(actuator, from_string, to_string)` computes the world
   distance along the rail from the contact geometry (`layout`'s string
   `a`/`b` and the tool's approach) and returns the vocabulary's travel
   time; `Actuator.travel_s` becomes the *floor* for scores without
   geometry. `t_move = t − approach − travel` as now.
3. `_Solver._separated` charges a moving arm from `max(t_free_prev,
   t_move − slack)` where slack is the early-start window the rig will use
   (everything from when the arm is free) — the rig's `_schedules()` then
   finds the interval already clear and the symmetric re-check becomes an
   assertion (keep it; make it log when it has to push a start).
4. `test_score_plan`: a synthetic mechanism with two arms where the old
   per-index travel accepted a 12-tooth reposition in 0.3 s and the new
   one refuses or re-times it; the Chamber and the expanded piece still
   plan (record any event whose `t_move` moves). `test_motion`: no travel
   uses the 40 ms floor on either asset (`clicks_seen` all at `CLICK_S`),
   and the number of pushed early starts is zero.

**Acceptance:** both scores re-plan with no infeasible events (or a listed
handful with the reason), every mallet travel clicks at 90 ms a tooth, the
rulers stay green (the rails may need a replan if reach windows change —
`layout_search._mech_key` hashes the score), and `docs/motion-design.md`
"A machine moves, then waits" describes one occupancy model, not two.

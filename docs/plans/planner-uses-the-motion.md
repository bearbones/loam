# The score planner derives its timing from the motion vocabularies

**Claimed 2026-09-18 04:15 PDT** by Claude-Session
https://claude.ai/code/session_01SfoJujiAJsKYkejLtNGvQf

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

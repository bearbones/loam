# The blow shakes the assembly, not only the arm

**Status (2026-09-17):** landed (commit 841c575) — three shudders per stepped
blow (stand 1.5 mm/9 Hz, rail sag 1 mm/12 Hz shaped sin(pi u) at both the blow
and the posed x, masts 0.3 mrad/6 Hz), one mirrored SHUDDER_GAIN dial in
`formlab/rig.py` and `harness/clockwork_motion.gd`, contacts still exact to
1e-9 m. A/B moves 0.42 % of pixels at view 3.

**Where:** `harness/performance.gd` (`evaluate`, the bars' bounce, the
gantry/railhead/stand nodes), `harness/clockwork_motion.gd` (`recoil`,
`RECOIL`), `formlab/rig.py` (mirror), `tools/test_motion.py`,
`docs/motion-design.md`.

**Problem:** the recoil landed in `3b80e0c` moves the arm (carriage shudder
along the rail, the mallet ringing across and bouncing above the bar) and
the bars bounce, but the instrument stand, the rail's bars and the rail
gantry are rigid. A mallet blow on a 5 kg bar over a wooden trestle should
be seen in the stand (a short vertical thump), in the rail (a sag and ring
at the carriage's x, the pawl and pinion ticking with it — already the case
through `root.x`) and, faintly, in the gantry masts (a sway at their
natural frequency). The operator asked for "recoil/reverb effects on the
assembly".

**Work:**

1. Define a *recoil bus* in `ClockworkMotion`: for each blow (`sched[aid]`
   hit times, mallet arms only) a list of `(t_hit, aid, x_hit, energy)`
   where energy scales with the mallet's lift (the cocked drop's height) and
   the string's amplitude in the score.
2. Rigid-body shudders driven from the bus, each a damped sinusoid like
   `_ring`, gated exactly as `recoil` is (zero at the hit, gone before the
   next strike of the same arm):
   - the **stand** (`form_bars_stand`, `form_<mid>_stand`): a vertical
     translation, 1.5 mm, 9 Hz, 120 ms decay, summed over blows on that
     instrument; the bars themselves keep their own bounce;
   - the **rail** (the two bars and the rack of the arm's rail, and the
     carriage with everything on it): a vertical sag at the carriage's x
     shaped as a half-sine over the span, 1 mm at the carriage, 12 Hz,
     150 ms; the carriage's `root.y` follows it so links and pawl move with
     the rail (posing already goes through `pose()`; add the sag there);
   - the **gantry masts** (`form_<aid>_gantry`, `form_<aid>_railhead`): a
     sway about the plinth's base, 0.3 mrad, 6 Hz, 300 ms.
3. Mirror the bus and the rail sag in `formlab/rig.py` (the rail sag moves
   the arm and so its capsules; the stand and masts are fixed forms for the
   rulers — 1.5 mm is inside every margin but say so in the docs).
4. Rulers: `tools/test_motion.py` gains a check that every shudder is zero
   at its blow, non-zero 10–40 ms later, and back to zero before the arm's
   next strike; `dev/test_performance.gd` checks a stand node moves after
   a blow and is still at rest before it; `dev/test_clockwork.gd` clearance
   margins unchanged within the shudder amplitudes.
5. A 5 s clip from view 3 at the first mallet passage, before/after, side
   by side (see [contrast-reel](contrast-reel.md)).

**Acceptance:** every contact still exact to 1e-9 m (the sag is gated like
the recoil); all rulers green on both assets; the clip shows the stand and
rail answer each blow and are quiet between blows; amplitudes in
`docs/motion-design.md` with the reasoning (a bar's mass against a trestle,
a steel bar's first bending mode); no new intersections (the rail sag lowers
the carriage 1 mm: check the second-bar boss vs the guide bars still has its
4 mm, `clearance.offset_hits`).

**Notes:** keep every amplitude a named constant at the top of both motion
files; the operator will tune by eye. Do not shake the strings' frames
(harp, rake): the picks are servo arms and nothing there is struck.

# Pawl follow-ups: the roller turns, the click sounds, the rest is a detent

**Where:** `formlab/pawl.py`, `tools/build_forms.py`, `harness/performance.gd`,
`harness/clockwork_motion.gd`, `formlab/rig.py`, `loam/score.py`
(`_Solver`), `tools/test_pawl.py`, `tools/test_motion.py`.

**Problem (three small ones):**

1. The roller (`pawl.lever_pieces`) is one mesh with the lever; a roller
   that does not turn reads as a stud.
2. The ratchet click is silent. The score's audio is the instruments; the
   chamber's own mechanism makes no sound, while the operator asked for
   "sharp clicky" motion.
3. The carriage rests wherever the score's contact puts it, so the pawl
   comes to rest on a tip, a flank or in a dip at random
   (`docs/articulated-arms.md`, pawl paragraph). A detent should *rest in a
   dip*: the last click of a travel should land the disc with the roller in
   a gap.

**Work:**

1. Split the roller into its own local part `{aid}__roller` (origin at the
   axle, `pawl.manifest` records `roller` offset and radius); `performance.gd`
   poses it at the pawl's axle (through the pawl's transform) and spins it
   by the arc rolled: `Δs/R` where `Δs` is the roller's contact path length
   — approximate with the disc's rim speed at the contact, `Δx·(r_tip+R)/r_pitch`,
   accumulated per frame (the rig is evaluated at arbitrary `t`, so
   integrate analytically: spin = `x·(r_tip+R)/(r_pitch·R)`, a function of
   x alone). `dev/test_performance.gd` checks the roller node exists and
   turns between two poses.
2. A click sample: in `performance.gd`, at each detent crossing of a
   stepped arm (`ClockworkMotion` can expose `click_times(aid)` from
   `sched` — one per tooth crossed, at the click's landing time
   `go + (k+CLICK_MOVE)·T/n`) play a short click (an `AudioStreamPlayer3D`
   at the pawl; synthesise the sample in `loam/` as a 3 ms metallic tick
   with a 14 Hz ring under it — the same `RING_HZ` — and export it beside
   `chamber.wav`, or generate it procedurally in GDScript). Gate it behind
   `--silent` like the master. Mix 12 dB under the instruments.
3. Quantise the *carriage* rest to the teeth: in `_schedules()`, when a
   travel lands, the disc phase is `x/PITCH`; the pawl rests in a dip when
   the phase is a half-integer. The tool must still hit the contact, so the
   carriage cannot move — instead give the pinion a **phase offset** per
   arm at build time (`gear_home` spun by the fraction that puts the roller
   in a dip at the arm's *home* x), and accept that other rests are
   unquantised; then measure how many rests land within ±15 % of a dip
   and report it in `test_pawl`. If the operator wants every rest in a dip,
   the alternative is a compliant wrist (the arm parks on a detent and the
   wrist's slack reaches the contact) — a larger plan; note it, do not do it.

**Acceptance:** rulers green; a close-up clip shows the roller turning as
the carriage clicks, the click audible in the mix on a mallet passage, and
the home rests in a dip; `docs/motion-design.md` gains a "the click has a
sound" line and the honest note on rest quantisation.

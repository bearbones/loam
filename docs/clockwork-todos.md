# Sound-suite implementation backlog

Observed during the September 2026 clockwork build. Each task is sized for a mid-level agent. Preserve the original Chamber export as a comparison fixture; keep changes independently reviewable. These are implementation tasks, not claims that the issues below have already been fixed.

## P1 — Record each rake contact in the scheduling state

**Where:** `loam/score.py`, `_Solver.plan`, `_Solver.commit`, `_Solver.options`.

**Problem:** `plan` checks each string's restrike interval against the sweep start, and `commit` writes the sweep start to every `last_hit`. Actual audio contacts are `t + k * spread_s`. A later event can therefore pass the restrike check too soon after the final string. The present Chamber has enough spacing; it does not expose this bug.

**Work:** build one ordered contact list and use its individual times for restrike checks and state updates. Pass spread information through commit and any feasibility helpers. Reject negative spreads explicitly. Preserve descending sweep order.

**Acceptance:** ascending and descending sweeps with a single-string restrike just inside/outside the interval; multiple partially overlapping sweeps; existing e99 and Chamber have unchanged feasible plans. Every accepted pair on a string obeys its actual contact-time separation.

## P1 — Export a playback mix contract

**Where:** `Score.export`, `songs/chamber.py` export/master section, `harness/score_doc.gd`.

**Problem:** exported stems are dry; `chamber.wav` separately receives room convolution, filtering, saturation and peak normalization. The old harness plays dry stems and never hears that chain. The new performance explicitly switches between the named master file and dry stems, but the filename remains a demo convention, not schema metadata. A nonlinear master cannot be reproduced by adding independently mastered stems.

**Work:** add optional `playback` metadata identifying master path, gain, sample count, and dry-stem role. Have both harnesses read it. Retain compatibility with old exports. Decide explicitly between dry stem audition and a shared real-time mix bus for interactive muting; do not promise that nonlinear mastering distributes over stems.

**Acceptance:** master playback agrees with the exported master PCM; old exports still load; absent master cleanly selects stems; muting is labeled as dry audition; switching modes preserves sample position. Missing or unequal-length audio fails with a useful message.

## P1 — Make shape reuse conditional on material and synthesis

**Where:** `loam/fdstring.py` `shape_library`, `loam/score.py` `_name_shapes`/`_write_shapes`, `songs/chamber.py` shape setup.

**Problem:** all plucked events select the nearest pick from one 220 Hz, 3.2 s FD library. The rake has bronze synthesis with a 4 s t60, but receives the steel library. The audible source is Karplus–Strong, whereas the visual source is a finite-difference string: the FD invariance experiment licenses reuse within that model, not exact audio/displacement agreement with another synth. Nearest-pick lookup also moves the shape apex away from the actual tool's contact for intermediate picks.

**Work:** add material/model/version keys, damping parameters, exact pick, validity bounds and cache fingerprint to clips. Bake a bronze bank; select by material before pick. Interpolate compatible pick shapes or bake the finite set used by the piece. Export declared visual gain. Keep any stylized displacement explicitly identified.

**Acceptance:** each rake references bronze; exact cache invalidation when any physical parameter changes; apex matches contact within one mesh segment; decay agreement measured on each instrument's own bus with a documented tolerance. Keep non-linear bridge shapes out of a linear superposition path.

## P2 — Add a body transfer stage before the room

**Where:** `loam/strings.py`, `loam/modal.py`, `loam/score.py` material definitions; song stem processing.

**Problem:** material-aware strings have damping and pick coloration, but no explicit soundboard/radiation stage. The current sympathetic bus adds strings that hum; it is not a measured or modeled instrument body.

**Work:** implement a deterministic small modal body filter with calibrated energy, decay and optional coupling; separate excitation, body output and room. Expose per-material presets without silently changing existing defaults. Make the body output available as a stem/envelope for the chamber visualization.

**Acceptance:** impulse-mode frequencies and decay meet written tolerances; no energy growth; tails retained on Take; loop warming verified on Loop; A/B renders at matched loudness. Compare on isolated harp and rake buses before listening to the mix.

## P2 — Use physical trajectory limits in playability

**Where:** `Actuator`, `_Solver.travel`, instrument geometry, `harness/clockwork_motion.gd`.

**Problem:** travel is a per-string-index duration. It ignores actual distance, pick-position changes, acceleration, tool size and collisions. The renderer's IK is reachable for these fixtures, but reachable endpoints do not prove collision-free linkage travel. Zero `travel_s` on a rake currently delegates carriage repositioning to its approach interval.

**Work:** define stroke/rail units, calibrated speed/acceleration and tool envelope. Derive minimum travel time from world distance. Add explicit sweep speed constraints and a separate geometry validation pass for swept link/tool volumes. Keep aesthetic bend decisions in the rig, with validation against the same geometry manifest.

**Acceptance:** refuse a deliberately unreachable or over-speed score, accept current pieces with revised calibrated timing, and report the two mechanism/arm IDs and time interval for each collision. Include rail supports and instrument frames as obstacles, not just other tools.

## P2 — Stream large score exports and validate their schema

**Where:** `Score._ensure`, `Score.export`, `harness/score_doc.gd.load`, both players.

**Problem:** synthesis retains a complete stereo float64 array per stem; runtime WAV loading retains each stem plus the master. Memory scales with duration × sample rate × channel count × stem count. Loader validation covers only part of the schema: malformed clip ranges and cross-mechanism string references need stronger checks. Its state is also accumulated on repeated `load` calls.

**Work:** separate header validation from payload loading; clear state on reload; validate event ownership, clip bounds, positive rates, assigned plans and finite values. Add optional memory-mapped/offline block export and streaming playback behind existing interfaces.

**Acceptance:** reload two different documents on one loader with no retained data; malformed fixtures yield useful errors rather than crashes; report peak RSS for a ten-minute, sixteen-stem fixture; show bounded playback memory without regressing sync.

## P3 — Remove stale programme facts from documentation

**Where:** September 6 entry in `LOG.md`, `docs/chamber-spec.md`, `songs/chamber.py`.

**Evidence:** the log says 64 bars; the script is 28 × 4 beats at 84 BPM = 80 s, plus 6 s tail. The spec's approximate duration is also older than the implementation.

**Work:** distinguish historic intent from current exported facts and generate a small summary from score metadata. Do not silently rewrite historical measurements.

**Acceptance:** generated summary agrees with event count, duration, bars, mechanisms, stems and cue count in the export.

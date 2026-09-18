# A leadscrew drive for the servo arms

**Where:** `formlab/clearance.py` (`CARRIAGE`, `PINION`, `MOUNTS`,
`drive_capsules`, `pinion_mount`), `formlab/linkage.py` (`carriage_body`),
`formlab/gantry.py` (`rack`, `rack_geometry`, `rail_racks`, `rail_end`),
`tools/build_clockwork.py` (`gear`, the per-arm drive), `tools/build_forms.py`,
`harness/performance.gd` (the drive's posing), `formlab/layout_search.py`
(`evaluate_arm`'s `caps['rack']`), `tools/test_gantry.py`,
`tools/test_linkage_tools.py`, `docs/articulated-arms.md`.

**Problem:** every carriage is driven the same way — a pinion on the
carriage rolling on a rack along the rail — while the motion now speaks two
vocabularies. A rack, pinion and pawl *are* a stepped drive; a servo slew
"like a telescope drive" wants a **leadscrew**: a threaded shaft the length
of the rail, turning in bearings at the rail heads, with a nut on the
carriage. Seeing the screw turn smoothly (fast — 5 mm pitch, so a 0.4 s
slew of 300 mm is 60 turns) against the mallet arms' clicking pinions makes
the operator's contrast mechanical, not only kinematic.

**Work:**

1. `clearance.DRIVE` per arm kind: `rack` (today) or `screw`. `pinion_mount`
   still chooses *where* (the four `MOUNTS`) — a screw needs the same free
   side. Geometry for `screw`: the shaft (radius 12 mm, thread pitch 5 mm)
   along the rail where the rack strip is now (`rack_geometry`'s line, in
   the disc's plane, `rack_direction` off the carriage), bearing blocks on
   the rail heads (`rail_end`), a **nut** on the carriage — a bronze block
   with a flange, bolted to a boss where the pinion's axle stands today
   (`carriage_body`), and a drive: a small motor housing or a bevel pair at
   one rail head (keep it a brass cylinder with fins; the chamber is
   clockwork). The thread as a helical ridge sweep (`sweep` with a `ridge`
   or a helix path) on the shaft, exported once per rail.
2. Posing: `performance.gd` turns the screw by `2π·x/pitch` about its axis
   (a world part, spun like the flywheel); no part on the carriage moves.
   The rack and pinion disappear for servo arms — `PART_NAMES` loses `gear`
   per arm: make the drive parts optional by kind as `pawl` is.
3. Capsules: `drive_capsules` for `screw` (the shaft as one capsule per
   rail — an obstacle to *other* arms as the rack is; the nut on the
   carriage); `evaluate_arm` and `plan_gantries` treat the shaft as the
   rack today. The rail cache key hashes `clearance.py`, so this replans the
   rails (75 min) — do it once, on both assets, and record the margins.
4. Rulers: `test_gantry` — the shaft clears every other arm, the nut clears
   its own links, the bearing blocks sit on the heads; `test_linkage_tools`
   — the carriage with a nut, all four mounts; `dev/test_performance.gd` —
   the screw turns `2π·Δx/pitch` between two poses, servo arms have no gear
   node, stepped arms still have theirs and their pawl.

**Acceptance:** rulers green on both assets; a view-1 clip of a harp slew
shows the screw spinning and stopping with the S-curve (the S-curve is
already jerk-limited: the screw's spin should look like a stepper ramping);
`docs/articulated-arms.md` "The carriage and its drive" describes both
drives and why each arm has the one it has.

**Notes:** keep the rack for every stepped arm — the pawl
(`formlab/pawl.py`) depends on the pinion. If the rail replan moves a rail,
re-run every ruler and re-read the clearance report before committing.

**Claimed 2026-09-18 03:02 PDT by session 01UgkC53ynYyk7onQUi3uc2L (Claude Fable 5.1):** staged — rails kept (`--rails=keep`) until the one full replan; stage A is the screw, its bearings, the nut and the posing for the servo arms.

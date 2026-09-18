# The rail search re-plans when the motion or the linkage changes

**Where:** `formlab/layout_search.py` (`_mech_key`, `plan_arms`),
`render/form-study/rails-cache.json`, `tools/build_clockwork.py`,
`docs/articulated-arms.md` ("The rail search screens the brackets first").

**Problem:** the rail cache key hashes the strings, obstacles, mechanisms,
arm configs and the *source* of `candidates`, `evaluate_arm`, `plan_arms`
and `clearance.py` — not `rig.py` (the motion the rails are planned
against) nor `linkage.py`/`gantry.py` (the geometry measured). The motion
redesign (`3b80e0c`) and the pawl (this session) changed what the arms
sweep and what hangs off the carriage, and the rails were *not* replanned;
the rulers re-measured the old rails against the new motion and happened
to pass (56 mm to spare on the arm clearance, centimetres elsewhere). The
next change may not be so lucky, and a stale plan would only show as a red
ruler after a 7 min build.

**Work:**

1. Hash into `_mech_key` the sources of `formlab/rig.py`, `formlab/linkage.py`,
   `formlab/gantry.py` and `formlab/pawl.py` *and* the motion constants
   (import them and hash their values so a constant tweak replans).
2. Because a full replan is ~75 min per asset, add a `--rails=keep` flag
   to `build_clockwork.py` that reuses the cached plan with a loud warning
   line in the build log and a `stale_rails: true` note in the manifest;
   `test_gantry` then FAILS on a manifest with `stale_rails` so a stale plan
   cannot be committed silently. The default replans.
3. Replan both assets once with the new key (overnight-sized), record the
   new margins in the LOG, and confirm the layouts did not move (or say
   how they did).

**Acceptance:** touching `rig.py` changes the key (a unit test in
`tools/test_score_plan.py` or a new `tools/test_rail_cache.py`: build the
key twice with a temporary constant change and see it differ); a keep-build
is marked and refused by the ruler; the committed manifests carry no
`stale_rails`.

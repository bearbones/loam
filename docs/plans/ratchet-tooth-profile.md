# Trapezoid teeth on pinion and rack; a pawl that drops to the root

**Where:** `tools/build_clockwork.py` (`gear` — shared with the flywheel;
add a `profile` argument), `formlab/clearance.py` (`PINION`),
`formlab/gantry.py` (`rack_geometry`, `rack`, `RACK_GAP`),
`formlab/pawl.py` (`TOOTH`, `tooth_distance`, `PAWL`),
`harness/clockwork_motion.gd` (`tooth_distance` mirror), `tools/test_pawl.py`,
`tools/test_gantry.py`, `dev/test_performance.gd` (the pinion AABB check).

**Problem:** the pinion's teeth are boxes (radial flanks) and the rack's
match them. Two consequences: the drive meshes with 4 mm of clearance but
box teeth on a box rack cannot actually roll into each other (the corners
collide — hidden only because nothing measures the mesh); and the pawl had
to become a roller riding the tips because a nose that entered a gap would
wedge on the radial flanks (`formlab/pawl.py`'s docstring, LOG 2026-09-17).
A real ratchet click is a pawl dropping to the *root* on a sloped flank.

**Work:**

1. `gear(n, p, r, profile='trapezoid')`: teeth as extruded trapezoids —
   tip width 0.55·pitch, root width 0.9·pitch at the root circle, flanks at
   ±20° from radial (involute-ish), the same 8 mm bevel; the flywheel keeps
   `profile='box'` (it is decorative) or takes the new one — the operator's
   call, note it in the LOG. Build the tooth as a `formlab.sweep` prism from
   a 2D profile rather than a scaled cube so the profile is a function.
2. `rack_geometry` mirrors the profile: trapezoid teeth with the same
   pressure angle; `RACK_GAP` keeps the tip and root clearances. Add a
   *mesh ruler* to `test_gantry`: at 16 carriage positions across a pitch,
   the pinion's tooth polygons (spun by x / r_pitch) and the rack's tooth
   polygons do not overlap (a 2D polygon intersection test — `shapely` is
   not a dependency; write a separating-axis test for convex polygons).
3. `pawl.TOOTH` becomes the trapezoid; `tooth_distance` a distance to the
   convex polygon with rounded corners (edge and corner cases; keep it
   vectorised and mirror it in GDScript). Re-choose the nose: with 20°
   flanks a 9 mm ball drops to within 3 mm of the root and lifts on the
   flank without wedging — verify with the existing "no jump" and "touches
   everywhere" checks. The dip grows from 9.5 mm to ~20 mm.
4. Re-run `test_pawl`, `test_gantry` (the pinion's `r_tip`/`r_hub` are
   unchanged, so no rail replan) and `dev/test_performance.gd` (the pinion
   AABB check bounds only the disc's thickness and width — still true).

**Acceptance:** the mesh ruler passes at every sampled position; the pawl
rulers pass with the deeper dip; a close-up render from view 3 of a mallet
carriage shows the teeth meshing with the rack and the pawl in a root;
`docs/articulated-arms.md` updated (the "Tooth k is centred at…" paragraph
and the pawl paragraph).

**Notes:** the tooth-tip phase assumption (`tips at multiples of 2π/16 from
+x in the home frame`) is pinned by the pawl's kinematics — keep the new
profile centred on the same angles, or update `pawl.tooth_distance` and its
GDScript mirror together and re-measure the parity (`test_pawl`).

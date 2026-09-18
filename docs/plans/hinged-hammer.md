# Hinged hammer heads for the hammer arms

**Where:** `formlab/linkage.py` (`mallet_tool`, `tool_mount`),
`tools/build_forms.py` (tool packing), `harness/clockwork_motion.gd` and
`formlab/rig.py` (`strike`, a new `hammer_flip`), `harness/performance.gd`
(posing a new `{aid}__head` part), `formlab/clearance.py` (`arm_capsules`
tool capsule), `tools/test_motion.py`, `tools/test_linkage_tools.py`,
`docs/articulated-arms.md` ("Tools"), `docs/motion-design.md`.

**Problem:** `stepped(aid)` treats mallet and hammer arms the same: the
whole arm cocks and drops. A hammer (the expanded asset's `hammer` kind; a
piano-style strike on a bench-mounted struck instrument) should read
differently from a mallet: the arm positions, and a *hinged head* flips on a
pin at the shank's end, strikes, and is caught by a check (a felt-faced
stop) so it does not double-hit. The arm then stays put and only the head
moves — the sharpest, clickiest motion in the piece, with the recoil
happening in the head and its check rather than the whole arm.

**Work:**

1. Geometry (`linkage.hammer_tool(mount)`): shank to the wrist socket as
   today; at its end a **hinge pin** (knuckle_pin, axis X) through a fork;
   the **hammer**: a shank 120 mm from the hinge to a felt head (the current
   mallet head shape); a **check** — a felt-faced stop on the shank behind
   the hinge that the hammer's tail meets at rest; a light **return spring**
   (a leaf, or a torsion coil as `formlab/pawl.py` builds). The head is a
   local part (`{aid}__head`, origin at the hinge, world orientation at the
   rest angle); the fork, check and spring stay in `{aid}__tool`.
2. Kinematics: `strike()` for a hammer becomes a *flip*: the tip (contact
   point) stays on the scored path but the arm's wrist no longer drops the
   full lift — split the lift between a small arm dip (30 %) and the head's
   flip angle; the head's angle over the strike interval is a cocked
   back-swing (`COCK`, `COCK_AT` as today) then a fall with `1 − v²`; after
   the blow the head rebounds off the string, is caught by the check (a
   short damped bounce, 2 blows of 25 Hz), and rests. `pose()` returns the
   head angle; `performance.gd` poses `{aid}__head` about the hinge.
   Contact exactness: the head's felt face at the flip's end must equal the
   scored contact point — derive the hinge position from the tip and the
   angle, not the other way round.
3. Capsules: `arm_capsules` gets the head as its own capsule (hinge to felt
   face) swept through the flip; `Rig.poses` samples the flip.
4. Rulers: `test_motion` — hammer arms cock, flip, land exact, rebound and
   settle before the next strike; the arm dips no more than 30 % of the
   lift; `test_linkage_tools` — the fork, check and spring pieces closed and
   the head's rest angle meets the check; `dev/test_performance.gd` — the
   rendered felt face hits the contact.

**Acceptance:** all rulers green on both assets (the mallet arms unchanged:
this is for `kind == 'hammer'` only); a close-up clip of one hammer blow at
120 fps shows the flip, the strike and the check catching the rebound;
contact exact to 1e-9 m; clearance margins measured with the flipping head
included.

**Notes:** the expanded asset's hammer arms are the ones with `hammer`
kind — check `render/clockwork/score.json`'s actuators before starting; if
the piece has none, add a hammer mechanism to the expanded score first (a
struck bench instrument already exists: `bench_plan`).

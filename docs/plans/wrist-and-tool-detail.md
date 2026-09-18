# Wrist socket, mallet head and plectrum detail

**Where:** `formlab/linkage.py` (`tool_mount`, `mallet_tool`, `pick_tool`,
`crosshead`), `tools/build_forms.py` (tool packing and per-piece
materials), `tools/test_linkage_tools.py`, `dev/test_performance.gd` (the
tool-surface material checks), `docs/articulated-arms.md` ("Tools").

**Problem:** the wrist crosshead's lower boss takes the tool's shank in a
plain socket; a real socket has a **collar** with a **set screw** (or a
knurled locking ring) that reads as the thing holding the tool on. The
mallet head is a plain felt blob: a mallet is a wound core (yarn or felt
wrapped over a wooden or rubber core) with the wrap's spiral visible and a
tied-off end. The plectrum is horn in a brass ferrule; the ferrule needs a
**shim slot** and the two screws it already has need slotted heads.

**Work:**

1. `tool_mount` grows a collar: a ring around the socket 1.6× the shank
   radius, 25 mm long, with a hex-socket set screw (revolve, 12 sides, with
   a hex recess — a small inset revolve of negative depth is not a boolean:
   model the recess as the head's own profile) pointing +X, and a knurl:
   32 shallow ridges via `sweep(..., profile=rounded_rect)` with the profile
   modulated (`formlab.sweep` accepts a per-ring profile array).
2. `mallet_tool`: the head as a core sphere plus a **wrap**: a helical
   sweep of yarn (radius 2 mm, 14 turns across the head, one felt material)
   over the core, ending in a tied knot (a small torus). Per-piece
   materials: core `felt`, wrap `felt` (the test pins "a mallet is one felt
   surface" — keep the wrap felt, or update the check to "felt and only
   felt").
3. `pick_tool`: slotted screw heads (a thin box through the domed head),
   the ferrule's shim slot (a thin prism on the ferrule's face — modelled as
   a raised lip rather than a cut).
4. `test_linkage_tools`: the new pieces closed; the collar clears the
   wrist's second-bar web (`arm_capsules`' `wristhead_web`) and the set
   screw does not reach the lower link's fork; `clearance.report`'s tool
   capsule radius updated if the collar is wider than 30 mm (it should not
   be).

**Acceptance:** rulers green; a view-7 close-up (the wrist is in frame there)
shows the collar and screw and the mallet's wrap; no clearance margin moves
by more than the collar's added radius.

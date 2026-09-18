# Articulated arms: joints, parallel bars and the space they need

The mechanisms that play the instruments are built as real linkages, not as
scaled cylinders. This note is the build guide for that layer: what the
pieces are, where the numbers come from, and which rulers keep an arm out of
its neighbour, the strings and the furniture.

Modules: `formlab/linkage.py` (joint and link recipes), `formlab/rig.py`
(the Godot IK mirrored in numpy), `formlab/clearance.py` (capsule ruler),
`formlab/layout_search.py` (rail placement), `formlab/gantry.py` (what
holds the rails up), `loam/score.py` (`arm_clearance` in the planner). `tools/build_forms.py` assembles an arm per actuator and
`tools/build_clockwork.py` places it; `harness/performance.gd` poses it.

## The linkage

Each arm is a **double parallelogram** — the drafting-lamp / Luxo arrangement.
Every segment has two bars of equal length on pins a fixed offset apart, so
the crosshead at the far end keeps the orientation of the crosshead at the
near end. Two such segments in series keep the wrist crosshead, and the
tool it carries, upright at every pose without a third motor. The pick
therefore meets the string at the same angle wherever the arm is, which is
what a plucking machine needs and what makes the motion read as engineered
rather than animated.

Pieces per arm, all built in a **link frame** (pin A at the origin, +Y
along the link, the pin axis +X) and never scaled afterwards:

| part | recipe | notes |
| --- | --- | --- |
| upper, lower | `link()` | flat fish-belly bar (`bar()` with `belly`, `taper`), eye end at A, fork end at B |
| upper2, lower2 | `link(layer=...)` | the parallel bar, one layer outboard |
| elbowhead, wristhead | `crosshead()` | two plates, each with a boss at every pin and a web between, tied by a spacer boss at every pin but the one where a primary link's eye turns between them; the secondary bars' stub pins (`stub_pin()`) are cast with it |
| carriage | `carriage_body()` | the shoulder crosshead plus bushings on the guide bars, a cheek plate and the pinion's axle — on a bridge behind the bushing when the pinion lies above or below the carriage (see The carriage and its drive) |
| shoulder, elbow, wrist | `knuckle_pin()` | domed head one side; on the other the shaft runs through a washer, a hexagonal nut chamfered top and bottom, and a split pin through its end (`fastening()`, shared with the crossheads' stub pins) — all inside the room the old turned nut had, so the layer table below and `gantry.PIN_X` stand; spans the fork ears |
| tool + shank | `pick_tool(mount)` / `mallet_tool(mount)` | tool origin = contact point; the shank is built to reach its socket under the wrist boss (see Tools) |
| oil cup | `oil_cup()` (cast with `upper`) | a lubricator on the upper link's elbow fork, +X ear rim, on the link's line beyond the pin — where a rod end's oil hole goes — in the ear's own layer along the pin, so nothing of the arm's own stack shares its space; recorded per arm as `oil_cups` and given its room by `tools/test_oil_cups.py` (20 mm from every other arm, rail, string and obstacle through the whole score). Not on the lower link: its fork works at the wrist, where the rake's sweep carried a cup to 6 mm from a string |

Joints are **knuckle joints**: a fork straddles an eye on a pin (`fork_end`,
`eye_end`, `ring`, `revolve`). Every layer along the pin has its own room,
derived by `clearance.default_layers(spec)` from one spec
(`clearance.DEFAULT_SPEC`); nothing is placed by eye. From the crosshead's
mid-plane outward:

| layer | half-width | what |
| --- | --- | --- |
| eye | 0–17 mm | a primary link's eye (its own bar's width), turning between the crosshead's plates |
| plates | 19–31 mm | the crosshead's two plates (12 mm each), bosses and webs on both; a solid spacer boss ties them at every other pin |
| fork ears | 34–56 mm | the next primary link's fork (22 mm ears) straddling the plates; the bar's yoke stops at the ears' rim so the boss turns between the ears, not in the yoke |
| secondary bar | 62–89 mm | the parallel bar (+X for the upper segment, −X for the lower), its eye turning on a shouldered **stub pin** cast with the crosshead |
| nut | to 125 mm | the stub pin's washer, hex nut and split pin, and the pin's tip past them — the widest thing on the arm (`pin_x`; `gantry.PIN_X`); `tools/test_linkage_tools.py` pins every fastening inside that room |

The primary knuckle pin spans only the fork ears (`pin_span`), head and
nut outside. So at the elbow, read outward: the lower link's eye, the
elbowhead's plates, the upper link's ears, then the second bars on their
stubs — each part on its own seat. (The first stack was a lie: the eye
sat inside the crosshead's boss at the same X, the fork's yoke ran into
the boss, and each secondary eye was buried in a boss cast at its own
layer.) The two segments' second bars ride on opposite faces so the
upper and lower segments can cross in plane without touching.

`parallelogram_arm(l1, l2, o1, o2)` returns every piece plus the layer table
and the pin-axis span — the number the planner needs (see below).

## Posing

`ClockworkMotion.pose()` (GDScript) and `formlab.rig.Rig.pose()` (numpy)
are the same two-link planar IK to 3e-7 m: root at `(tip.x, root_y,
root_z)`, swing plane yz, pins along world X. Two rules were added:

- **Wrist offset.** The wrist pin sits at `tip + wrist_offset`. Picks and
  rakes use `(0, .20, −.10)`: above and *behind* the string, so the pin never
  sits on the string it plays. Mallets use `(0, .28, 0)`. The heights are
  what the tool stack needs: plectrum (or felt head), ferrule, a shank you
  can see, the socket collar, and the boss's own radius (0.05 m) above it.
- **Bend hint.** `bend = "back"` keeps a pick arm's elbow on the far side of
  the string plane — the hanging elbow of a harpist. With the root above and
  behind the string an "up" elbow is geometrically forced through the
  strings; "back" is the universal rule for plucked and raked mechanisms.
  Mallets keep "up".

How the tip *moves* between the score's contacts — ratchet clicks, a cocked
drop and a recoil for mallet arms; jerk-limited S-curve slews for picks and
rakes — is `docs/motion-design.md`. The pose is still a pure function of
time; the vocabularies only change the tip path the IK follows.

The parallel bars are posed with `link_basis(a, b)` at `a + o` — the same
basis as the primary bar, translated by the constant world offset `o`.
`choose_offset()` picks `o` (magnitude 0.11 m) to maximise the minimum
separation between the two bars of a segment over the whole piece. `o` and
`−o` separate the bars identically, so the chooser keeps `o` pointing up or
level: the second bar's pin then never hangs below the wrist, where the
tool's shank needs its socket.

## Tools

The first tools were a straight 0.15 m rod from the contact point — and
the wrist pin is 0.10 m behind that point, so no shank actually reached
its crosshead. A tool is now built *to its mount*:

- **Plectrum** (`pick_tool`): a tear-drop blade 50 × 70 × 7 mm, its face
  toward the string (wide across the pin axis, thin along the pluck — the
  old blade was swept edge-on, which is why it read as a needle), clamped at
  its top in a **ferrule** block with two set screws. The blade is **horn**
  — what a plucking machine would actually wear against a wire — in a brass
  ferrule: the recipe names a material per piece (`recipes.pack(materials=)`),
  `blender_forms.make_form` gives each piece's faces their own material slot
  before the edge bevel so the bevel inherits it, and the Godot look module
  finishes the imported "horn" surface as a dark amber grain. (A voxel-union
  finish forgets faces, so per-piece materials are for profiled objects only.)
- **Swan-neck shank** (`swan_shank`, `clearance.shank_path`): a round
  steel rod on a cubic Bezier from the ferrule top — rising vertically,
  curving back, arriving vertically — into a **socket** collar hanging
  under the wrist pin's boss (chamfered mouth, tenon buried in the boss).
  `clearance.tool_mount` is that rule; `SOCKET_DEPTH` (0.075 m) is where
  the mouth sits below the boss centre. When the mount is directly above
  (mallets) the same recipe is a straight drop.
- **Mallet** (`mallet_tool`): a 12 cm felt head with the shank starting
  inside it — threaded on, not pasted to the rod.

The clearance capsules follow: `tool` runs from the contact point to the
neck's apex, `shank` from the apex into the socket; the shank is judged
against the strings like every bar, and the lower bar is measured against
the tool rather than excused. `tools/test_linkage_tools.py` is the ruler.

## Rail gantries

The rails were first hung from bare brass posts — up to four metres of rod
on a disc, standing at the ends of the bars, and where a neighbouring rail
ran through a post it simply did. `formlab/gantry.py` replaces them with what
a linear guide actually needs, every dimension from a rule:

- **Rail head** (brass): a block at each end that captures both guide bars
  (the bars run 0.26 m past the reach window, 0.10 m into the head). Its
  inner face is 0.16 m past the window because the shoulder pin's head
  reaches 0.119 m from the carriage plane — a carriage parked at the end
  clears it by 40 mm. (The old posts stood 0.12 m out with a 35 mm radius;
  the pin passed through them.)
- **Mast** (steel): a tapered box column, constant 90 mm across the pin
  axis, deep along Z — the swing direction, the load that racks it — and
  growing toward the base the way a cantilever's bending moment does
  (50 mm half-depth at the top, +25 mm per metre, capped at 110 mm). It
  stands on a stepped **plinth** with four anchor bolts, on the stage or on
  a furniture lid, and its top is bolted to the head.
- **Bracket and knee brace**: where the mast cannot stand straight under the
  head — another rail's bars run there, or a neighbouring arm swings
  through — the head is carried on an L-bracket to the mast: out along X
  first (*outreach*, clear of the neighbouring carriage that rides at the
  same height), then along Z (*setback*: behind the rail, or in front when
  behind is taken), with a diagonal brace under each leg, as a signal
  gantry or a wall jib does.

The bracket is **searched per rail end**, cheapest first (straight down,
then back, then out, then both; behind before in front —
`gantry.CANDIDATES`), and the first placement whose pieces keep 20 mm from
every arm's swept capsules over the whole piece, every other rail's bars,
the instrument forms, the furniture boxes and the gantries already placed
(every rail's heads are reserved before any bracket is chosen) is kept.
An arm is a plane of capsules with knuckle pins across it, so each capsule
is slid along the pin axis until the arm as a whole reaches the pin tips'
planes (±0.119 m) before it is measured. Each piece is judged by its own
bounding box; the diagonal braces as capsules, since the union box of
bracket, brace and mast would fill the corner an elbow legitimately swings
through. Candidates are screened at 30 Hz and the winner confirmed at
120 Hz. The two ends of one rail may differ: the high harp rail's low mast
stands 0.4 m behind its head, its high mast straight under; the middle harp
rail, wedged between the other two, carries both heads 0.35 m out and
0.4 m *forward* to masts on the floor in front of the cabinet.

### The rail search screens the brackets first

The gantry planner runs after the rails are fixed, so a rail whose ends no
bracket can serve is a build failure, not a worse score — and the honest
knuckle stack produced one: the re-planned harp rails put the middle arm's
high head where the outer arm's links sweep, every bracket at that end was
blocked by 50 mm, and Blender exited 0 with no asset written (the
traceback was in the raw log; a grep-filtered log had hidden it).
`layout_search.evaluate_arm` now keeps, per rail end, every bracket of the
planner's grid that the arm's own motion and the furniture leave clear,
built from the planner's own solids in numpy-only form
(`clearance.bracket_solids`: mast column, plinth, bracket beams, knee
braces as capsules; `clearance.head_box` for the head; `clearance.foot_level`
for a mast on a furniture lid — the planner imports the same functions),
and the search objective asks whether the neighbours leave at least one
bracket at each end (`mast_margin`, cheapest bracket first, stopping at a
comfortable gap). The screen stays affordable because each part carries
its whole sweep box: a part whose box keeps 150 mm from a solid is scored
by that bound and never measured, and most of an arm never comes near a
bracket (`solids_gap`); a coarse pass over every fourth pose, an upper
bound on the gap, rules blocked brackets out before the fine pass. The
gantry planner itself now measures through the same `solids_gap`
(`gantry._stacks`, `_gap_arms`), so the two rulers share one arm model
and one arithmetic: it reproduces every recorded bracket and gap to the
millimetre and plans a rig in seconds rather than tens of minutes, which
is what makes `tools/test_gantry.py` a ruler that actually gets run. Two
more differences between the rulers closed at the
same time: the rail search slides every capsule across the pin span the
way the planner does (`pin_shifts`, from the same `pin_x`), and measures
each rail's heads as boxes rather than capsules — the capsule pair had let
that harp rail through by the corner a box does not round off. Because
the search samples at 30 Hz and the planner confirms at 120 Hz, the chosen
set is re-measured at 120 Hz (`verify_fine`) and an option that fails
there is dropped and the search repeated; the 120 Hz worst is recorded as
`margins.fine`. The option dropped is the one to blame: of a failing arm
pair, the later arm; of a rail whose masts have no clear bracket, the arm
itself when its own motion or the scene closes every bracket, otherwise the
later of it and each arm that alone blocks them. (The rule used to drop the
mechanism's last arm whatever failed, and the expanded rig's harp search
spent all its retries dropping harp_arm2 for harp_arm0's masts.) Each retry
prints every arm's 120 Hz margin, so a search that gives up says why.

### Rails are obstacles too

Building the gantries exposed a flaw the earlier rulers could not see: the
high harp arm's upper link swept 52 mm through the middle harp rail's bars
twice in the piece. Arms had been kept from arms, strings, stage and
cabinet — never from each other's rails. `layout_search.evaluate_arm` now
adds each candidate rail (bars and both heads) to that arm's capsule set,
so `cross_gap` measures every arm of a mechanism against its neighbours'
rails as well as their links. The rail search then moved the middle harp
rail from (3.15 m, −1.8 m) to (4.1 m, −1.4 m) — level with the high harp
rail and in front of it, so neither high arm's link crosses the other's
rail — and the second bars rail up to 2.75 m; worst arm-to-rail margin in
the harp is now 139 mm. `tools/test_gantry.py` re-measures every arm
against every rail of the whole rig at 120 Hz.

The same blind spot existed between mechanisms: each was planned against
its own arms and the scene only, and when the expanded rig's harp moved to
high rails the gantry planner refused the build for a bells arm's lower link
31 mm inside the harp's rack. The mechanisms are planned in score order and
each candidate is now measured against the arms of the mechanisms already
placed — their links and rail hardware against its own (heads included),
its masts against their motion and theirs against its — at both sampling
rates, recorded as `margins.others`; an arm whose bounds stand the comfort
gap apart is not measured and the margin records that bound. The placed
rails are part of the later mechanisms' cache key, so a harp that moves
re-plans the bells behind it. `test_gantry.py` checks that every arm of a
mechanism planned after another records that margin clear.

### What the cache key promises

The search is an hour an asset, so each mechanism's answer is cached in
`render/form-study/rails-cache.json` under a hash of everything the search
consumed (`layout_search._mech_key`). That key was once incomplete in the
way that matters: it hashed the space model (`clearance.py`) but not the
*motion* sampled through it, so the motion redesign of 2026-09-17 changed
what every arm sweeps and the rails were never replanned — the rulers
re-measured the old rails against the new motion and happened to pass, with
56 mm to spare on the arm clearance. A stale plan shows only as a red ruler
after a 7 minute build, so the key now hashes the source of every module the
plan is measured against — `rig.py` (the motion), `clearance.py` (the space
model), `linkage.py`, `gantry.py` and `pawl.py` (the geometry measured) —
listed as `layout_search.GEOMETRY_SOURCES`, and the motion constants by name
and value (`layout_search.motion_constants()`, every upper-case value in
`formlab.rig`) so tuning a click length replans as loudly as editing the
file. `tools/test_rail_cache.py` holds the key to that promise: it edits each
source and each constant in turn and watches the key move.

Because a replan is expensive, `build_clockwork.py --rails=keep` reuses the
existing plan even when the inputs have moved — for a build whose changes are
nowhere near the rails. It is loud rather than silent: a warning line per
mechanism in the build log and `stale_rails: true` in the manifest, which
`tools/test_gantry.py` refuses. A stale plan therefore cannot be committed,
and the default is always to search.

**Where "the existing plan" comes from matters.** A cache keyed by inputs can
answer "what was computed for these inputs"; it cannot answer "what is this
asset built with", and that is the question keep-mode asks. Asking the cache
anyway — via the `mech:<id>` alias, the key stored last for that mechanism —
gave the harp three different link lengths and two different pinion mounts on
the first real keep-build, under a flag whose purpose is to change nothing.
So keep-mode reads `harness/assets/<name>.json`, the manifest sitting beside
the asset, and prefers its arms (`plan_arms(keep_from=...)`: `CFG_KEYS` plus
the margins that plan achieved). The alias is only the fallback for a build
with no manifest on disk, and the log names which of the two was used.

## The carriage and its drive

The first carriage was the shoulder crosshead alone: two bosses and a web
floating at the rail's axis, with a toothed disc in front of it turning as
the arm travelled. Nothing held it on the bars and nothing turned the disc.
Measured, it was worse than that: the mallet arms' second-bar offset points
up, and the boss for that bar (radius 50 mm) sat 38 mm from the top guide
bar's axis — the bar ran straight through it.

`linkage.carriage_body()` builds the carriage a linear guide actually has,
dimensions in `clearance.CARRIAGE` and `clearance.PINION`:

- a **split bushing** around each guide bar (bore 2 mm over the bar, 45 mm
  outer radius, 160 mm long — inside the knuckle pin's span, so a carriage
  parked at the rail end still clears the head);
- a **cheek plate** on the −X side tying the two bushings together, 20 mm
  thick, standing 6 mm outside the crosshead's −X plate (the upper link's
  eye turns between the carriage's plates at the shoulder); the +X side is
  where the second bar's stub pin lives, so it gets none. The shoulder pin
  runs through the crosshead and the cheek — that is its bearing;
- the **pinion's axle**: out of the carriage plane for a pinion in front
  of or behind the carriage; for one above or below it, a **bridge** back
  from the bushing (the bars are in the way of a vertical axle at the
  carriage's centre) carrying the axle 100 mm behind the bars.

The **pinion** (build_clockwork's 16-tooth disc, tip radius 130 mm, pitch
radius 120 mm) now rolls on a **rack**: a toothed brass strip as long as
the rail's bars, in the disc's plane — above an upright disc, behind a flat
one — carried on a stub from each rail head (`gantry.rack`; a stub off the
head's face for an upright disc, an L from the head's top or bottom for a
flat one). Tooth k is centred at x = (k + ½)·pitch; the pinion's tooth
facing the rack points straight at it when its carriage is at x = 0 and
`performance.gd` turns it by x / r_pitch about its axle, so the teeth roll
into the gaps along the whole rail (4 mm tip and root clearances,
`gantry.RACK_GAP`).

The teeth are **involute** (`formlab/gear.py`), not the bevelled boxes they
began as: a 20° pressure angle on the 240 mm pitch circle, the flank
unrolling from the base circle at 112.8 mm and running radially into the hub
below it, 3 mm of backlash at the pitch line, 4 mm corners — a 12 mm tip
land, 24 mm at the base. The rack's teeth are the involute's conjugate, which
for a rack is a straight line: trapezoids at the pressure angle, 10 mm at the
tip, 32 mm at the root on the strip (`gear.rack_half`). One profile feeds
four places: `build_clockwork.gear(profile='involute')` extrudes the polygon
per tooth (the flywheel keeps its box teeth — it is decorative and a
different radius), `gantry.rack` cuts the rack by `rack_half`, the pawl's
distance field is the polygon inset by its bevel (below), and
`tools/test_gantry.py` rolls the two through a pitch at sixteen positions
and asserts no pinion tooth overlaps a rack tooth (`gear.mesh_gap`, a
separating-axis test between the convex polygons; the least clearance is
2.8 mm, a pinion tooth's corner passing a rack flank). Box teeth on a box
rack could never have rolled: their corners collide, and nothing measured
it.

Where the pinion goes is **measured, not ruled** — `clearance.pinion_mount`.
The first rule was "in front for pick arms (they bend back), behind for
mallet arms (they bend up)", and it was wrong: a pick arm's elbow is behind
its *chord*, not behind the carriage, so reaching a far string its upper
link leans forward almost flat and swept 25 mm through a pinion in front
(harp_arm2); two other pick arms reach *up* from low rails, so their links
leave the carriage upward. There are four **mounts** (`clearance.MOUNTS`):
behind, above, below, in front. For each, the pinion (a stack of chords in
its plane, `pinion0..4`), its axle and its bridge are measured as capsules
against the arm's own links, webs and bars over the whole piece; the first
mount in that order with 50 mm to spare (`MOUNT_COMFORT`) is taken, else
the clearest. Measured on the current layouts: behind for the mallet arms
and the third harp arm (65–129 mm), below for the two arms that reach up
(104 mm). The rail planner records the mount with the offsets (`pinion` in
the manifest), and `build_forms.py` builds what the planner chose — its
120 Hz pass and the planner's 30 Hz screen can break an offset tie
differently, which is how a bar once ended up 5 mm inside the disc. The
bushings, cheek, bridge and axle are capsules too, so a neighbour's link is
kept off the carriage, not only off the crosshead.

Two more rules fell out of measuring:

- `choose_offset(keep_clear=rail_keep_clear())` refuses any second-bar
  direction whose boss or web comes within 4 mm of a guide bar
  (`clearance.offset_hits`). Of the 37 up-or-level directions, 18 survive —
  those within ±44° of the swing axis, forward or back.
- The rack is fixed by its rail, so it is reserved in the gantry search
  like the heads; each rail's rack is also an obstacle to the *other* arms
  in the rail search (`caps['rack']` in `evaluate_arm`), and
  `plan_gantries` refuses a layout whose rack another arm or rail crosses.

**The mallet arms' pinions carry a roller detent pawl** (`formlab/pawl.py`),
the mechanism the ratchet click of `docs/motion-design.md` is read from. Under
the disc — the rack is above it, the rim below is free — a steel lever
pivots on a knuckle pin at a bracket cast onto the carriage (an ear off an arm
that runs from the carriage's plane, a strut into the lower bushing's wall, the
pin's washer, nut and split pin outward), reaches 100 mm under the disc to a
yoke, and two tongues off the yoke carry an 18 mm roller on its axle; a brass
torsion spring on the pin bears under the lever and against a post on the
bracket, holding the roller up against the teeth. It is a detent, not a
one-way pawl: the carriage travels both ways, so the nose is symmetric. The
roller is wider than the gap between two tips' corners, so it rides the tip
lands and dips 15.5 mm between each pair, on the corners and the tops of the
flanks, one dip a tooth. Two things the involute teeth taught. The roller
must never sink below the tip circle: a 15 mm one did, once the lands
narrowed from the box teeth's 29 mm to 12, and a roller whose centre is
inside the circle is met by the next tooth's corner *below* its centre — the
pawl can only move on its arc, so the corner drives it deeper and wedges it
between the flanks (`test_pawl` now pins the lowest centre outside the tip
circle). And the lever leans 14° down toward its pivot (`PAWL['tilt']`;
the pawl's angle is the whole turn of its frame, lean included): level, the
roller's arc ran 17° off radial and an approaching corner lifted it on a
near-flat wedge, a snap of 1.7° per 0.1 mm of rail; leaning, the arc is
radial where the roller meets the corners and the lift is 0.17°. Its angle at
any rail position is the largest at which the roller is still clear of the
toothed disc as spun (`pawl.angle`, a bisection on the exact distance to the
hub and the three nearest teeth — each the involute polygon inset by its
bevel and grown back, so the corners are round, `pawl.tooth_distance`);
`ClockworkMotion.pawl_angle` mirrors it to 5e-13 rad and `performance.gd`
poses the part (`{aid}__pawl`, a local part at its pivot, `pawl` in the
manifest) every frame, so the recoil's shudder ticks the pawl too. The
roller is its own part (`{aid}__roller`, `pawl.roller_pieces`: a steel drum
with a brass grease plug let into each face off the axis, so it can be seen
to turn) on the pawl's axle, and rolls on the tips as the carriage moves —
the disc's rim at the tips runs `r_tip / r_pitch` times the rail speed, and
the roller turns that arc over its own radius, the other way from the disc
(`pawl.ROLLER_SPIN`, −60 rad a metre; a tooth pitch turns it 2.8 rad). The
score's rest positions are not quantised to the teeth, so the pawl would
come to rest wherever the tooth under it left it; instead each pinion is
spun with a **phase** (`pawl.dip_offset`, `pawl.phase` in the manifest, in
metres of rail: the disc turns by `(x + phase) / r_pitch`) chosen so the
roller sits at the bottom of a dip when the arm parks at its home contact.
The other rests fall where the score's contacts put them (`test_pawl`
reports how many seat within 15 % of a dip); seating every rest would need a
compliant wrist that reaches the contact from a parked detent, which is a
larger plan (`docs/plans/pawl-follow-ups.md`). `tools/test_pawl.py` holds the
kinematics (touching everywhere, one dip a tooth, no jump, the body 8 mm off
the teeth), the pieces, the two implementations, the phase (seated at home
for any home x), and the pawl's space over
the score against the arm's own links, every sibling arm, every other rail's
bars and rack, its own rack and guide bars, and the forms and furniture;
`dev/test_performance.gd` checks the rendered roller sits exactly its radius
from the spun disc, on the pawl's axle, and has turned by the rail
travelled between two moments.

`tools/test_gantry.py` measures all of it on the built rigs: every arm's
capsules (pinion included) against every other rail's rack, each carriage
and its second-bar boss against its own rack, the recorded mount against a
fresh measurement of the drive's clearance, the offset rule, the rack's
pitch against the pinion's teeth and the disc's radius against the rail
heads. `tools/test_linkage_tools.py` checks the carriage pieces themselves
for all four mounts and the mount chooser on synthetic swings.

## The space an arm needs

Three rulers, all run at build time and all fatal when negative:

1. **Self clearance** (`clearance.report`): every piece of the arm as a
   capsule, pairwise segment distance over the sampled piece; adjacent
   pieces that share a pin are excluded. Also the gap from every bar and web
   to every string of the mechanism.
2. **Cross-arm clearance** (`cross_arm_clearance`): the same capsules
   between arms, at the same time samples.
3. **Scene** (`layout_search.scene_boxes`): stage top, cabinet, the harp and
   rake bases, and every struck instrument's frame footprint up to its
   elements' undersides — axis-aligned boxes the arm must not enter. Every
   capsule is measured against them, not only the four links: the carriage,
   the pinion, and the rail's own bars, heads and rack (the rack reaches
   0.26 m past the reach window, so a rail whose links clear a bench can
   still park its rack inside it — the gantry planner refused exactly such a
   rail before the rail search learned to measure it).

`layout_search.plan_arms()` searches rail height, rail depth and link length
per arm (greedy, then two rounds of coordinate descent) to maximise the worst
of those margins, preferring shorter links and rails near the middle height
once the margin is "enough" (80 mm). The greedy placement is run from every
order of the arms and the clearest set kept: a set can lock, each arm's
alternatives judged by a third arm's blocked masts so that only the
tie-breakers speak and the descent never moves — the expanded rig's harp
locked that way at −20 mm once the bells' bench took its back-low rail away,
and placing the arms in another order found three clear high rails. The
chosen rails, link lengths, bend and wrist rule are written into the
manifest with the achieved margins.

### Arms are wide: the planner knows

No rail placement can separate two arms that reach adjacent strings at the
same moment — the arm is 0.24 m across its pin axis and harp strings are
0.11 m apart. That constraint therefore lives in the **score planner**:
`Mechanism.arm_clearance` (score units; 0.09 = 0.27 m in the world) makes
`_Solver` charge each arm with the axis interval it crosses while moving and
a point over its last string while hovering, and refuse any plan that brings
two arms of one mechanism closer than that at any time. The composition
already asks before it writes (`can_play`) and falls back to a neighbouring
string, so the rule shapes the piece instead of breaking it: The Chamber
drops 7 of 247 intended notes (2.8 %) under the 5 % ruler, zero conflicts.

For this to be true in the world, the string positions the planner sees must
be the ones the model uses. `Mechanism.fan()` puts the harp's neck fan into
the score itself (one scale degree per equal step, feet climbing the diagonal
soundboard) and `formlab.layout.string_endpoints` reads fanned mechanisms
straight from `pos`. `dev/test_clockwork.gd` checks the promise on the
rendered rig: tip x separation of every arm pair of a mechanism, 120 Hz,
whole piece.

## Rulers

```sh
python3 tools/test_score_plan.py          # planner clearance rule, neck fan
python3 tools/test_formlab.py             # sweeps, frames, layout
python3 tools/test_form_joints.py         # seamless frame joints
python3 tools/test_linkage_tools.py       # plectrum, ferrule, swan neck, socket, mallet; the carriage
python3 tools/test_gantry.py              # rail heads, masts, brackets, racks; arms vs every rail
python3 tools/test_oil_cups.py            # the fork ends' lubricators and their room
python3 tools/test_pawl.py                # the mallet arms' roller detent pawls: kinematics, parity, room
python3 tools/test_motion.py              # the two motion vocabularies against the rendered rig
blender -b -t 2 -P tools/test_form_joint_seats.py
godot --headless --path harness -s dev/test_clockwork.gd
godot --headless --path harness -s dev/test_performance.gd
```

`tools/preview_form.py` renders any parts JSON with Blender's workbench for
a quick look at a joint (`blender -b -t 2 -P tools/preview_form.py -- in.json out.png [az] [el]`).

## Strings

Strings are shaded tubes (`shaders/wire_string.gdshader`), not line strips.
The mesh is a straight tube; the vertex shader bends it with the 24-node
shape frame (Catmull-Rom between nodes, normals tilted by the local slope)
and a second translucent copy is a sheath widened to the peak excursion of
the last 1/30 s — the blur a vibrating wire presents to the eye, denser at
the turning points. Gauge follows pitch (a display gauge; real wire would be
sub-pixel).

The strings are strung by register, as a harp is (`performance.gd`
`string_family`, the shader's `family`): wound wire below C4, gut through the
middle, nylon from C5 up. A wound string carries a helical ridge that catches
the light as the wire turns — silver-plated on the harp, bronze on the rake. Gut
is a twisted, translucent solid: warm ivory, matte, with a slow helical grain
from its strands, and light from behind comes through it (`BACKLIGHT`) so a
string against the light glows at its edges (`RIM`). Nylon is near clear and
glossy. The colour code follows the makers: every C red, every F black on gut
and wire and blue on nylon. `dev/test_performance.gd` pins the register rule
and the C/F colours on the built scene.

The highlight runs *along* a string, not across it. A winding or a gut's
twist grooves the wire around its circumference, so the micro-normals scatter
along its length and the reflection stretches that way; a plain drawn wire
is scratched along its length instead, and its highlight spreads slightly
across. The vertex shader gives the tube a tangent along the wire (the mesh
carries none; it bends with the shape frame) and the fragment sets Godot's
`ANISOTROPY` from a per-family uniform `aniso` (`performance.gd`
`string_aniso`: wound 0.7, gut 0.45, nylon 0, steel −0.3; positive stretches
along the tangent), on the speaking length and the dead lengths alike. The
winding's ridges also rock the normal along the wire — but only while a turn
is a few pixels wide: `fwidth` of the turn count is turns per pixel, and past
0.2–0.45 of a turn a pixel the ridges (tone and normal) fade to their mean,
so a bass string in the wide shots does not shimmer or moiré; the gut grain
fades the same way. Where a string passes through an eyelet or over a
bridge or tuning pin it is darkened 6 mm either side of the contact
(`contact_m`; every tube ends on hardware, so the darkening is by `UV.x`
without per-string uniforms), so it reads as pulled tight through the
hardware rather than floating past it. `--view=16` frames the harp's lowest
string a hand above its eyelet for all three. `dev/test_performance.gd`
pins each string's and dead length's `aniso` to its family and the uniforms'
presence; the look itself is judged by eye on views 6, 12, 14 and 16.

The winding does not restart at the bridge. A string is several tubes — the
speaking length and the dead lengths to the tuning pin — and each counts its
turns from its own end, so the helix used to jump phase at every joint. The
shader's `offset_m` is the wire already wound before a tube begins;
`_make_dead_length` sets it to the speaking length plus each dead segment
before it, so the ridges (and the gut's grain) run through the joint as one
wire. `dev/test_performance.gd` pins the offsets to the accumulated lengths.
And the bright ring that used to cross a string at one height, a silent
moment or not, was the tube's own far wall: the sheath writes `ALPHA`, which
makes the one shared material transparent, and transparent geometry writes no
depth, so the double-sided tube's inside back wall showed through at the
ring where the two walls' draw order flipped. `depth_prepass_alpha` in the
shader's `render_mode` lays the opaque wire into the depth buffer first; the
sheath still blends over it, and `cull_disabled` stays so the sheath keeps
its far wall. The ruler pins both flags.

Two things a still from the front never showed. The pluck axis is world Z,
straight at a frontal camera, so the bend and the sheath (a lens flat in
the vibration plane) were edge-on and vanished; a real plucked wire does
not stay in its plane either — the pick's release and the wire's stiffness
precess the motion into a slowly turning ellipse — so `cross_axis` (0.35)
mirrors that fraction of the bend and the sheath width across X. And a
thin metallic wire in a dark studio is a mirror of darkness: the core
keeps a little diffuse body, and a sounding string lights itself —
`excitation` is the peak excursion of the last 1/30 s over a full pluck
(0.02 m), emission rises with its square and is tinted by the wire's own
albedo so a red C sings red. `performance.gd` sets it per frame beside
`disp`/`envelope`. `--view=10` frames the most recently plucked string
from 45° off its pluck axis to judge all of this; it latches for 1.5 s.

A wire thinner than a pixel or so breaks into dashes and then vanishes from
the wide shots, the treble strings first. The vertex shader therefore holds
every tube to a minimum on-screen width (`min_px`, 1.6 px): it works out the
size of a metre at the bent axis's depth from the view transform and the
projection's vertical focal length (`abs(PROJECTION_MATRIX[1][1])` — Godot's
Vulkan projection flips Y, so the raw entry is negative and a naive formula
silently never engages) and rebuilds the ring at the larger of the true gauge
and that width, toning the wire's body down by the coverage it would have
had so a distant string stays a faint but continuous line rather than a
bold one. The sheath grows with it. `dev/test_performance.gd` pins the
tube's ring convention the shader relies on and the uniform's presence.

At its foot a plucked string leaves the soundbox through a flanged brass
eyelet on the mouth of its ferrule (`eyelets` on the manifest, from
`formlab.layout.eyelet_plan`; see [instrument frames](instrument-frames.md));
the wire tube simply starts at the foot inside the eyelet's hole.

A harp or rake string does not stop at the top of its speaking length. The
manifest carries the two turning points of its dead length (`neck.bridge`,
`neck.pin`, from `formlab.layout.neck_plan`), and `_make_dead_length` draws
two straight tubes of the same wire — up the string line to the bridge pin,
then leaning to the tuning pin — as a node beside the string, so the
per-frame shape updates never reach it. At the pin the wire winds on
(`neck.wrap`, from `formlab.layout.pin_wrap`): two and a half turns of the
same gauge coiled toward the neck, a tube along a helix (`_tube_along`) in a
plain material of the wire's colour, since the wire shader only bends a
straight tube. See [instrument
frames](instrument-frames.md#the-neck-carries-the-strings-the-way-a-harps-does).

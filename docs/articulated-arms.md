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
| elbowhead, wristhead | `crosshead()` | two bosses joined by a web; the pins live here |
| carriage | `carriage_body()` | the shoulder crosshead plus bushings on the guide bars, a cheek plate and the pinion's axle — on a bridge behind the bushing when the pinion lies above or below the carriage (see The carriage and its drive) |
| shoulder, elbow, wrist | `knuckle_pin()` | domed head one side, nut the other |
| tool + shank | `pick_tool(mount)` / `mallet_tool(mount)` | tool origin = contact point; the shank is built to reach its socket under the wrist boss (see Tools) |

Joints are **knuckle joints**: a fork straddles an eye on a pin (`fork_end`,
`eye_end`, `ring`, `revolve`). The fork gap, ear thickness and pin radius
are one spec (`clearance.DEFAULT_SPEC`) so every seat fits: the fork of a
primary bar straddles a crosshead boss; the secondary bars sit outside on
the +X (upper) and −X (lower) layers so the two segments can cross in plane
without touching. `default_layers(spec)` derives the layer offsets from the
spec; nothing is placed by eye.

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
  its top in a **ferrule** block with two set screws. Brass, for the eye;
  a real mechanism would use horn or hard leather.
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
  thick, standing just outside the upper link's fork ears; the +X side is
  where the second bar's boss lives, so it gets none. The shoulder pin runs
  through the crosshead and the cheek — that is its bearing;
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
into the gaps along the whole rail (4 mm tip and flank clearances,
`gantry.RACK_GAP`).

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
3. **Scene** (`layout_search.scene_boxes`): stage top, harp pedal box,
   cabinet — axis-aligned boxes the arm must not enter.

`layout_search.plan_arms()` searches rail height, rail depth and link length
per arm (greedy, then two rounds of coordinate descent) to maximise the worst
of those margins, preferring shorter links and rails near the middle height
once the margin is "enough" (80 mm). The chosen rails, link lengths, bend
and wrist rule are written into the manifest with the achieved margins.

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
sub-pixel) and strings below C4 are wound bronze with a helical ridge.

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

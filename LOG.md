## 2026-09-17 — CLOCKWORK the pawl's roller turns, and the detent rests in a dip at home

The pawl's roller was one mesh with its lever, so it read as a stud; and
the pinion was spun by the carriage's x alone, so the pawl came to rest on
a tip, a flank or in a gap at random (`docs/plans/pawl-follow-ups.md`,
items 1 and 3). Now the roller is its own local part (`{aid}__roller`,
`formlab.pawl.roller_pieces`: a steel drum with a brass grease plug let
into each face off the axis, so the turning shows) on the pawl's axle, and
`performance.gd` rolls it on the tips as the carriage moves — the disc's
rim at the tips runs `r_tip / r_pitch` times the rail speed and the roller
turns that arc over its own radius, the other way from the disc
(`pawl.ROLLER_SPIN` = −72 rad a metre, 3.4 rad a tooth). Each pinion with
a pawl is spun with a phase (`pawl.dip_offset`, `pawl.phase` in the
manifest, metres of rail) chosen so the roller sits at the bottom of a dip
when the arm parks at its home contact — a detent rests in a dip. The
score's other rests fall where its contacts put the carriage (the tool has
to reach them); `tools/test_pawl.py` now reports how many of them seat
within 15 % of a dip, and checks the phase seats the home for any home x,
the roller drum, and the spin. `dev/test_performance.gd` checks the roller
sits on the pawl's axle and has turned by the rail travelled between two
moments (the swing taken out). Docs: `docs/articulated-arms.md`,
`docs/motion-design.md`. The click sample (item 2) is still to do. Both
assets rebuilt; every ruler green.

## 2026-09-17 — CLOCKWORK the ratchet has a mechanism: a roller detent pawl on the mallet arms' pinions

The mallet carriages clicked along their racks (`docs/motion-design.md`) with
nothing to click on. Under each mallet arm's pinion — the rack is above it —
a steel pawl now rides the teeth (`formlab/pawl.py`): a lever on a knuckle
pin at a bracket cast onto the carriage (an ear off an arm from the
carriage's plane, a strut into the lower bushing's wall), a yoke with two
tongues carrying a 15 mm roller, and a brass torsion spring on the pin
bearing under the lever and against a post on the bracket. It is a detent,
not a one-way pawl (the carriage travels both ways). A first draft with a
9 mm ball nose wedged: the pinion's teeth are boxes with radial flanks and
the pawl only moves on its arc, so a nose that enters a gap is trapped by
the next flank and the numerics snapped it 8° in a millimetre. The roller is
wider than the gap between two tips' bevels, rides the tips and dips 9.5 mm
between each pair on the bevels' 50° arcs — one dip a tooth, no jump. Its
angle is the largest at which the roller is clear of the spun disc, by
bisection on the exact distance to the hub and the three nearest bevelled
teeth; `ClockworkMotion.pawl_angle` mirrors it (5e-13 rad; a Vector2 in the
mirror cost 1e-7 — it is 32-bit) and `performance.gd` poses `{aid}__pawl`
at its pivot every frame, so the recoil's shudder ticks the pawl too.
`tools/test_pawl.py` holds the kinematics, the pieces, the two
implementations and the pawl's room over the score against the arm's own
links, its siblings, every other rail, its own rack and guide bars, and the
forms; `dev/test_performance.gd` checks the rendered roller sits exactly its
radius from the spun disc. Both assets rebuilt; every ruler green.

## 2026-09-17 — CLOCKWORK two motion vocabularies: ratchet and recoil against servo slews

Every arm moved the same way: a smoothstep in exactly the score's window.
Now a mallet arm is a stepped machine and a pick or rake arm is a servo
(`docs/motion-design.md`). The mallet carriage advances along the rack in
ratchet clicks — a tooth a click at 90 ms, a tenth of a tooth of overshoot
that rings out on the pawl at 14 Hz and fades before the next click — the
mallet cocks half its lift again and drops with the acceleration of a fall,
and every blow shakes the assembly: the carriage shudders along the rail
(the pinion ticking with it), the mallet rings across the bar and bounces
above it, all zero at the blow and gated to nothing before the next strike
so contacts stay exact. Pick and rake arms slew on jerk-limited S-curves —
ramp, cruise, ramp, monotone, no overshoot. Both start a move as soon as the
arm is free and the move wants, never later than `t_move`: a machine moves,
then waits. Because the score planner only promised the mechanism's arm
clearance from `t_move` on, `ClockworkMotion._schedules()` re-applies the
planner's occupancy model to the earlier window symmetrically (each sibling
charged with its interval from its own earliest start, padded 10 mm) and
pushes a move later until its interval is clear; the rendered margin beyond
the promise stays 56 mm on both assets. `formlab/rig.py` mirrors all of it
and `tools/test_motion.py` holds the two together through
`dev/dump_motion.gd` (0.6 µm over 300 000 samples) and checks each
vocabulary's promises. Every clearance ruler re-measured green: the added
excursions sit inside centimetre margins.

## 2026-09-17 — CLOCKWORK the plectra are horn in brass ferrules

The plectrum was brass "for the eye": a bright tear-drop of metal against a
wire, where a plucking machine would wear horn or hard leather. The blade
is now horn and only the ferrule and its set screws stay brass. That took a
material per piece through the pipeline: `recipes.pack(materials=)` names
one per piece (`piece_materials` on the recipe object),
`blender_forms.make_form` gives each piece's faces their own material slot
before the edge bevel so the bevel inherits it (profiled finish only — a
voxel union forgets its faces, and the adapter refuses the combination;
and the slots go on the mesh before the faces are assigned, because Blender
clamps a face's index to the slots the mesh has — the first build cleared
the slot list at the end and every face came out brass),
`build_clockwork.py` adds a "Pressed horn" material, and the Godot look
module finishes an imported "horn" surface as a dark amber grain streaked
along the blade. `tools/test_linkage_tools.py` reads the built recipe and
checks every plectrum is a horn blade in a brass ferrule and every mallet
one felt object; `dev/test_performance.gd` checks the imported tool mesh of
each pick arm carries a horn surface then a brass one, and each mallet a
single felt surface. Geometry is untouched, so nothing re-measured.

## 2026-09-17 — CLOCKWORK the pins are held on: washer, hex nut, split pin

Every knuckle pin and every stub pin ended in a turned "hex-ish" nut — a
chamfered cylinder revolved with the pin. A pin in a machine like this is
held on by a washer under a hexagonal nut, and the nut is kept by a split pin
through the pin's end. `formlab.linkage.fastening` now builds those three
pieces past the last ear of any pin — washer, hex nut chamfered top and
bottom (a six-sided revolve), split pin crossing the shaft between the nut
and the tip — and `knuckle_pin` / `stub_pin` run their shaft on through them
to the tip and return `[pin, washer, nut, cotter]`. Nothing reaches past the
old nut's tip along the axis or past the washer's radius across it, so the
knuckle stack's layer table, the arm capsules and `gantry.PIN_X` are what
they were and no rail re-planned. `tools/test_linkage_tools.py` pins that
for the knuckle pin and both stub pins: the shaft to the tip, six flats on
the nut, washer–nut–cotter in order toward the tip, everything inside the
pin's room, the cotter crossing the shaft along Y and standing out both
sides. The linkage table and the layer table in
`docs/articulated-arms.md` say so.

## 2026-09-17 — CLOCKWORK the strings wind their tuning pins

The dead length ran up over the bridge pin to the tuning pin and stopped
dead on its surface. A harp string winds its pin — coil beside coil between
the string plane and the neck — and the coil is what the eye reads on a
tuning pin. `formlab.layout.pin_wrap` now records on each harp and rake
string (`neck.wrap`) the helix's axis point on the pin at the string plane,
the pin's radius, the turns (2.5) and the room along the pin short of the
plate's outer face; `performance.gd` winds a tube of the string's own gauge
round it from the contact on the pin's +x side up over the pin, the way the
wire arrives from the bridge below, advancing toward the neck a wire's
diameter a turn (`_tube_along`: parallel-transported rings along a polyline,
so the tube neither twists nor pinches round the turns). It wears a plain
material in the wire's colour — the wire shader bends a straight tube and
could not draw a helix. `tools/test_neck.py` pins the recorded wrap against
the plan, the room against each string's gauge (the widest wire's coil needs
33 mm of the 49 available) and the coil clear of the neighbouring strings'
pins and dead lengths; `dev/test_performance.gd` checks the coil sits on its
pin, is as wide as the pin plus two wires, and runs no further along the pin
than its room. The wrap is written into `neck` after the rail search, like
the turning points, so no rail re-planned.

## 2026-09-17 — CLOCKWORK oil cups on the arms' elbow forks

Every bearing on a machine of this kind has a lubricator, and the arms had
none. Each arm's upper link now carries a brass oil cup on its elbow fork's
+X ear rim — a collar, a stem, the cup and its domed hinged lid,
`formlab.linkage.oil_cup`, cast with the link — standing on the link's line
beyond the pin, where a rod end's oil hole goes. That puts it in the ear's
own layer along the pin, where nothing else of the arm's stack lives, so the
knuckle stack's room table did not change and, since the clearance module
is untouched, no rail re-planned. `build_forms.py` records each arm's cup
(`oil_cups`) and `tools/test_oil_cups.py` gives it its room: posed through
the whole score, every cup keeps 20 mm from every other arm's sweep, every
rail and rack, every string and every obstacle. The first cut put a cup on
the lower link's fork too; that fork works at the wrist, and the rake's
sweep carried its cup to 6 mm from a string — so the wrist has none, and
the ruler says why. The link extent the Godot ruler checks grew by the cup
and is recorded from the pieces, so it followed. Scope: the cup is not in
the arm capsules the planner and the frame-clearance ruler use; its room is
measured by its own ruler.

## 2026-09-17 — CLOCKWORK strings hold a minimum on-screen width

In the wide shots the treble strings broke into dashes and the thinnest
vanished: a 2 mm wire five metres from the camera is under half a pixel.
`shaders/wire_string.gdshader` now holds every tube to `min_px` (1.6 px) of
on-screen width — the size of a metre at the bent axis's depth comes from
the view transform and the projection's vertical focal length, and the ring
is rebuilt at the larger of the true gauge and that width, with the wire's
body (albedo, specular, rim, backlight, emission) toned down by the coverage
it would have had, so a distant string stays a faint continuous line rather
than a bold one; the sheath grows with it. A trap worth recording: Godot's
Vulkan projection flips Y, so `PROJECTION_MATRIX[1][1]` is negative in the
vertex stage and the naive formula silently never engages (renders were
pixel-identical before and after) — it takes `abs`. `dev/test_performance.gd`
pins the tube's ring convention the shader rebuilds from and the uniform's
presence. No model change; no rebuild.

## 2026-09-17 — CLOCKWORK the plucked strings leave their soundboxes through brass eyelets

Each harp and rake string used to end in a brass ball sitting on the
soundbox — the one anchor in the scene a real instrument never shows, since
a harp string's knot is inside the box and the wire comes up through an
eyelet. The ball and its pin are gone: the recipe's ferrule (the brass sleeve
that runs the string's foot down into the moulding) now wears a flanged
eyelet on its mouth — `formlab.layout.eyelet_plan`: a flange disc down the
barrel and a rounded lip standing proud of it round the hole, sized so every
wire gauge the scene draws clears it. The ferrule and the eyelet share one
table (`EYELET`) for the barrel's offset and gauge, so the recipe, the builder
and the ruler cannot drift apart. `build_clockwork.py` builds both pieces and
records the plans on the manifest (`eyelets`, a top-level key, so no rail
re-planned) and folds them into the reference hardware the arms are measured
against. `tools/test_eyelets.py` pins each plan to its foot, the lip inside
the flange and proud of it, the hole against the wire, neighbouring eyelets
against each other and every eyelet against every arm's sweep (20 mm — the
score plucks the shortest treble strings 0.18 of their length above the
foot, so the plectrum works a hand's breadth from the eyelet). `--view=14`
looks down the harp's feet from the string side. Known limit: at the treble
end the ferrule mouths lie closer to the moulding, so those eyelets sit
nearly flush rather than standing on a collar.

## 2026-09-17 — CLOCKWORK the flywheel on plummer blocks, belt-driven, turning a bar a turn

The brass flywheel beside the harp stood on its rim with no axle — the last
thing in the main shots that nothing held up. It is now carried the way a
flywheel is: an axle through its hub in two plummer blocks (split bearing
housings bolted to pedestals on a sole plate) either side of the wheel, a
drive pulley on the axle's back end, and a flat belt — the true outer
tangents of the two pulleys, with a wrap round each — to a pulley on a stub
axle between two ears bracketed to the chamber cabinet's end face.
`layout.flywheel_plan` (numpy-free) lays out every solid from the wheel's
centre and radius; `build_clockwork.py` builds it and records the plan on
the manifest; `performance.gd` turns the wheel, hub and drive pulley once a
bar of the score's tempo and the belt pulley with them, faster by the radii.
The assembly stands beyond the cabinet's end, outside every obstacle and
every arm's reach, so no rail moved. `tools/test_flywheel.py` pins the
construction and its clearance from every arm sweep, rail and obstacle;
`dev/test_performance.gd` checks the wheel turns a quarter turn in a quarter
bar and the pulley by the ratio.

## 2026-09-17 — CLOCKWORK the harp's neck carries its strings: plate on the string side, bridge and tuning pins, dead lengths

The harp's action sat on the wrong side of the neck. The plate and the two
rows of discs were on the neck's far face, 34 cm from the strings; the tuning
pins stood in front of that; and every string stopped in the air under the
neck with a ferrule buried in the wood above it. A harp's strings run close to
one face of the neck and that face carries the action, so the plate is now
seated on the bead crests of the neck's string-side face (6 cm from the string
plane, 2 cm at real scale) and follows the neck's real taper
(`recipes.action_plate` sweeps it along the carved neck's own samples, 8 mm
proud, 90 % of the local width tall); the discs sit on the plate with their
fork pins reaching 12 mm past the string plane either side of each string;
above them a brass bridge pin stands at the plate on the +x side of the string,
and the string leans from it to a tuning pin on the −x side that passes
through the neck to its square head on the far face. A pedal harp's neck is
plated on both faces, so the far face keeps a plate too — the one the house
sees, with the sixteen pin heads standing proud of it — while the action faces
the strings; `--view=12` looks at the action from the string side. `layout.neck_plan`
(numpy-free) lays all of that out per string from its upper end and the two
face heights `recipes.neck_faces` reads off the backbone; `build_forms.py`
hands the plans to the Blender builder in the recipe's `neck` block. The
string itself runs on: the manifest records the dead length's turning points
(`strings[sid].neck`, written after the rail search so no cache key changed)
and `performance.gd` draws the two straight dead lengths in the string's own
wire, never excited. The rake, a lever harp, gets bridge and tuning pins
without discs. The recipe now puts a ferrule at a string's foot only. No base,
obstacle or planner changed, so every rail stayed where it was.
`tools/test_neck.py` pins the construction; `dev/test_performance.gd` checks
every harp and rake string has its dead length.

## 2026-09-17 — CLOCKWORK trestle benches under the bells and blocks; every frame is now a promise

The expanded rig's glass bells and temple blocks sat on plank beds with two
legs each — the last plank-on-legs construction in the scene. They now sit on
trestle benches built the way the marimba frame was: `formlab.layout.bench_plan`
lays out two rails along the row on a splayed-leg trestle at each end (crossbar,
legs, a tie where the legs have splayed to, a stretcher between the ties), a
bearer across the rails under every element, and the element's own mount on
its bearer — rubber pads at a block's nodal points (it rings like a bar), and
for a glass bell a call bell's base flange and centre post reaching up into
the crown so the dome hangs free. A fascia hung on the bearers' front ends
carries the plaque and the note names. `recipes.bench_frame` sweeps the timber
(16 and 15 closed pieces, `form_bells_stand` / `form_blocks_stand`); the
Blender builder adds the brass and rubber and drops the beds, legs and
under-bell tubes; the tool-clearance ruler and the Godot form toggle treat
every `form_*_stand` alike.

The first build failed honestly: the gantry planner found harp_arm0's rail and
rack running through the bells bench (+0.000 m). The plank beds were never
obstacles to the rail search, so that pick arm had been sweeping through the
bells' bed unmeasured. Every struck instrument's frame footprint, up to its
elements' undersides, is now promised to the rail search as an obstacle like
the cabinet and the bases (the mallets of the instrument's own arms come from
above, so the promise costs them nothing). The second build then showed the
other half of the gap: the rail search had only ever measured the four links
against the scene promises, so it accepted a rail whose rack — which reaches
0.26 m past the reach window — sat inside the bench, and the gantry planner
refused it after the rails were fixed. `layout_search.evaluate_arm` now
measures every capsule against the scene: carriage, pinion, and the rail's
own bars, heads and rack. The third build failed in the search's own 120 Hz
check: a harp rail's masts had no clear bracket at the fine rate, and
`verify_fine` blamed the mechanism's last arm whatever failed, so it dropped
harp_arm2's options four times for harp_arm0's masts and gave up. It now
blames the arm that closes the bracket (the owner for its own motion or the
scene, else the later of owner and blocker) and prints every arm's fine margin
per retry. That print showed the fourth failure was not a rate mismatch at
all: the 30 Hz search itself had settled on a set standing −20 mm, locked —
harp_arm0's end masts ran into the other two rails, every alternative for
either of those was judged by harp_arm0's blocked masts, so only the
tie-breakers spoke and the coordinate descent never moved. The greedy
placement now runs from every order of the arms and keeps the clearest set;
placed in another order the expanded harp finds three clear high rails
(y 2.75 / 3.60 / 4.10). That unlocked set then met the last blind spot: the
gantry planner refused it for a bells arm's lower link 31 mm inside the
harp's rack — each mechanism had been planned against its own arms and the
scene only. The mechanisms are planned in score order and every candidate is
now measured against the arms already placed (links, rail hardware, masts
both ways, both sampling rates; `margins.others`), and the placed rails are
part of the later mechanisms' cache key. The bells re-planned behind the
harp. The chamber's harp also moved: the clearest-set rule found a set
standing +23 mm against the old +20 mm (two high rails and a low back one).
`tools/test_bench.py` pins the bench rules and the
promise; `test_bar_frame.py` pins the marimba frame's promise.
docs/instrument-frames.md gains the bench section and the space-accounting
lesson.

## 2026-09-17 — CLOCKWORK the rake stands on a plinth

The rake — a five-string bronze instrument on a harp-shaped frame — stood on
the bare stage with its column foot sunk into the floor, while the harp beside
it had its pedal box. `formlab.layout.harp_base_plan` now takes `pedals`: with
them it is the pedal harp's box, without it a plain plinth with crown and sole,
the way a lever harp stands, and `build_clockwork.py` builds one under each of
the two. The rake's base is promised to the rail search as an obstacle exactly
like the harp's (the promise is part of the rail cache key, so every rail
re-planned once; the rake's rail is 1.4 m in front of its strings and the
plinth 0.3 m below the lowest string foot, so nothing moved). The tool-clearance
ruler measures the new `Rake *` hardware with the harp's;
`tools/test_harp_base.py` now checks both bases (promise, envelope, footprint,
no pedals on the rake). docs/instrument-frames.md gains the paragraph.

## 2026-09-17 — CLOCKWORK strings strung by register: wound wire, gut, nylon

Every plain string was the same grey metal tube; only the bass strings told
apart, by a faint bronze helix. A harp is strung by register — wound wire in
the bass, gut through the middle, nylon at the top — and each looks different:
wire is a mirror with a winding that catches the light, gut is a twisted,
translucent solid, nylon is near clear and glossy. The wire shader now takes a
`family` (steel, wound, gut, nylon): gut gets a warm ivory albedo, a slow
helical grain from its strands, no metallic term, and light through it from
behind (Godot's BACKLIGHT) with a rim so a string against the light glows at
its edges; nylon is glossier and clearer still; wound wire keeps its ridge,
silver-plated on the harp and bronze on the rake. The colour code follows the
makers: every C red, every F black on gut and wire and blue on nylon.
`performance.gd` `string_family`/`string_colour` decide per string, and
`dev/test_performance.gd` pins the register rule and the C/F colours on the
built scene. No asset rebuild — the strings are made in Godot — so the rails,
gantries and manifests are untouched; rulers all green. Documented in
docs/articulated-arms.md (Strings) and docs/clockwork-build.md.

# loam — log (newest at top)

## 2026-09-17 — CLOCKWORK the harp's pedal base: a box with the pedals through its front face

The harp stood on an oval drum with seven pedals radiating from it like
spokes — from the front, round the side, to the back. A pedal harp's base
is a box: the column and the body's lower return seat in it, and the seven
pedals leave the face toward the player through vertical slots, three on
the left of the string plane (D C B) and four on the right (E F G A), each
a steel lever on a pivot inside the box falling to a tread on the floor.
formlab.layout.harp_base_plan lays that out from the column's x and the
string plane's z — box, crown, sole, slots, levers, treads — and the Blender
builder makes it. The base is one of the two obstacles the rail search is
promised, and that promise is part of the rail cache key, so the plan keeps
the box inside it and nothing re-plans; tools/test_harp_base.py pins the
envelope, the 3|4 split, tread spacing and the levers leaving the front
face. docs/instrument-frames.md gains the section. Rulers all green; the
tool-clearance ruler measures the new hardware (harp_reference_hardware).

## 2026-09-17 — CLOCKWORK the bars hang on a marimba frame: node-line rails, end frames, quarter-wave resonators

The bar instrument was a plank on branching roots, each bar on a bare
brass stalk — a stand that explained nothing. A mallet instrument is an
assembly whose every member follows from one fact: a free-free bar's
fundamental has its nodes 22.4 % in from each end, and the bar is drilled
and hung on a cord there so nothing damps it. formlab.layout.bar_frame_plan
derives the rest from the bars alone: two rails splined through the actual
node points (they converge toward the short treble bars), 30 mm under the
bars; brass posts between the bars with rubber cushions and the cord at
mid-thickness; a closed quarter-wave tube under each bar (c/4f − .61 r,
scaled ×3, dark mouth, stopper cap, a steel bank rod through them) whose
radius is capped to hang between the rails, so the treble tubes come out
narrower as on the real thing; end frames — foot, two tapering uprights
outside the rails, a crosspiece the rails rest on — as wide as the local
rail spread, so the bass end stands broader; a low stretcher; a name board
on the front uprights carrying the plaque and note names. recipes.bar_frame
sweeps the timber (chamfered rectangular section, twelve closed pieces,
profiled finish so the edges stay crisp) as form_bars_stand — the name the
Godot form toggle and the tool-clearance ruler already key on — and Blender
builds the metal from the same plan, so the tubes, posts, cord and text
agree with the wood to the millimetre.

Space accounting: the frame stays inside the footprint of the bed it
replaced (z within ±0.75 m of the bar line, nothing above the bars'
underside), so the gantry plan is unmoved — build_forms reproduced every
mast, bracket and margin — and tools/test_bar_frame.py pins that envelope
along with the construction rules (nodes, convergence, rail gap, posts clear
of every bar and under the bar tops, tube radii and lengths, feet on the
stage). docs/instrument-frames.md records the rules; `--view=11` is a
fixed close-up of the frame's treble end. One lesson from the first render:
the board runs at the converging rails' 3° angle over 3.3 m, so text placed
in a fixed plane sank 9 cm into it at one end — the text now yaws with the
board and sits on its face normal.

The build also re-planned every rail this once: the tick-7 planner change
altered solids_gap's source, which is part of the rail cache key. The
chamber's rails and gantries came back identical. The expanded rig's second
bells arm moved (z −4.21 → −3.66, links 1.6 → 1.45 m): its old rail's masts
cannot stand once the first bells arm's rail is in place (−20 mm, every
bracket blocked) — the gantry planner had been rescuing it with a 1.2 m
set-back bracket at 22 mm — and the search now takes a rail whose masts
stand plainly at 96 mm. Rulers: score plan, formlab, form joints, linkage
tools, bar frame, form clearance (harp frame still governs at 24 mm), joint
seats, gantry, and the six Godot tests on both assets — all green.

## 2026-09-17 — CLOCKWORK the gantry planner measures with the rail search's ruler (25 min → 44 s)

tools/test_gantry.py had become a ruler nobody could afford: it re-runs the
gantry planner for both assets, and the planner measured every part of
every arm against every candidate solid at 120 Hz — over 25 minutes, so it
was never green or red, just killed. formlab.gantry now builds one
layout_search.stack_caps per arm (gantry._stacks, pin slides from
pin_shifts) and measures each solid through solids_gap (_gap_arms), so a
part whose sweep box stays 150 mm from the solid is scored by that bound
and never sampled; bars, boxes and placed gantries keep their own check
(_gap_fixed). Same arithmetic for the parts that are measured (24 samples
per box, the span's ends and middle per capsule): every recorded bracket
and gap in both manifests is reproduced to the millimetre, the chamber
plans in 8 s, the expanded rig in 13 s, and the ruler passes in 44 s. The
rail search and the planner now share one arm model and one ruler.

## 2026-09-17 — CLOCKWORK an honest knuckle stack: two-plate crossheads, stub pins, forked yokes

The joints looked right from a metre away and were a lie up close. At
the shoulder and the elbow a primary link's eye sat at X = 0, inside the
crosshead's own boss at the same X; the fork's yoke ran 20 mm into the
boss it was supposed to straddle; each secondary bar's eye was buried in
a boss cast at its own layer; and the crosshead's web, swept straight
along Z, came out 50 mm thick along the pin axis because sweep() picks
its profile frame from the path direction.

Now every layer along the pin has its own seat, all derived by
clearance.default_layers from one spec: the eye (±17 mm) turns between
the crosshead's two 12 mm plates (19–31 mm), the next link's 22 mm fork
ears straddle the plates (34–56 mm) with the bar's yoke stopped at the
ears' rim, the secondary bar (62–89 mm) turns on a shouldered stub pin
cast with the crosshead, and the stub's nut (to 125 mm) is the widest
thing on the arm — gantry.PIN_X is that number now, not a literal. The
primary knuckle pin spans only the ears. A solid spacer boss ties the
plates at every pin except the eye's; the wristhead is solid at both (the
tool's socket tenon is buried in it). Webs are swept along +Y and turned
into the swing plane. The carriage's cheek stands 6 mm outside its −X
plate (derived, not −62 mm). tools/test_linkage_tools.py reads the elbow
layer by layer (eye, plates with nothing between them at the pin, only
ears within the boss radius, stub pin and nut to the pin-tip plane on one
side, the second bar outboard of the ears, the primary pin's span).
Docs: docs/articulated-arms.md, the layer table.

The rebuild then failed silently: Blender exits 0 when the -P script
raises, and the grep-filtered build log had dropped the traceback —
`no gantry placement clears the scene for harp_arm1 (high end)`. Build
logs go raw to a file first now, grep after. The cause was a gap between
two rulers: the rail search (which fixes the rails) knew nothing of the
brackets the gantry planner would later need, slid no capsule across the
pin span, and modelled the rail heads as capsules; the planner does all
three, and the wider pin span plus the head's square corner turned the
search's +79 mm into the planner's −49 mm. clearance.py now carries the
planner's solids in numpy (bracket_solids, head_box, foot_level — gantry.py
imports them), layout_search screens every rail end on the planner's
bracket grid with the planner's slides and boxes (pin_shifts, stack_caps,
solids_gap, mast_margin: cheapest bracket first, early out at a
comfortable gap, coarse pass before fine), and the chosen rail set is
re-measured at 120 Hz (verify_fine) with a failing option dropped and the
search repeated. A first version of the screen measured the mast against
the arm's own head and rail — which touch it by design — and found every
bracket blocked; the own check now sees moving parts only, as the planner
does. A second version measured every part of an arm against every
bracket and took an hour without finishing the harp; each part now
carries its sweep box and is measured only when that box comes within
150 mm of a solid, and the harp's three arms plan in ten minutes with
every mast at the full 100 mm and the chosen set confirmed at 120 Hz.

## 2026-09-17 — CLOCKWORK the carriage rides its bars; the pinion rolls on a rack

The carriage was the shoulder crosshead alone, floating at the rail axis,
with a toothed disc turning in front of it on nothing. Measured, the
mallet arms' second-bar boss (offset pointing up) sat 38 mm from the top
guide bar's axis — the bar ran through it — and the disc itself ran
through that boss's stub on the arms whose offset points forward.

formlab/linkage.carriage_body builds what a linear guide has: a split
bushing around each bar, a cheek plate on the −X side tying them (the +X
side is the second bar's boss), the shoulder pin through crosshead and
cheek, and an axle for the pinion. The pinion now rolls on a rack
(formlab/gantry.rack: teeth at (k+½)·pitch, 4 mm clearances, carried on
stubs from the rail heads; performance.gd turns the disc by x / r_pitch
about its axle, so the tooth facing the rack rolls into the gaps).

Where the pinion goes is measured, not ruled (clearance.pinion_mount).
The first rule — in front for pick arms, behind for mallets — put a
pick arm's bar 25 mm through the disc: a pick arm's elbow is behind its
chord, not behind the carriage, so reaching a far string its upper link
leans forward nearly flat; two other pick arms reach up from low rails.
There are four mounts (clearance.MOUNTS): behind, above, below, in
front — upright discs on an axle out of the carriage plane with the
rack above; flat discs on a vertical axle standing on a bridge back
from the bushing, with the rack behind the rail on an L from the head.
The drive's capsules are measured against the arm's own links for each
mount and the first in that order with 50 mm to spare is taken (else the
clearest); the planner records it and build_forms builds what the
planner chose (its 120 Hz pass once broke an offset tie the other way).
Measured: behind for the mallet arms and the third harp arm, below for
the two arms that reach up.

Rules that came out of the measuring: choose_offset now refuses any
second-bar direction whose boss or web would touch a guide bar
(offset_hits; 18 of 37 directions survive); the pinion is in every arm's
capsule set as five chords and is judged against the arm's own links
and every neighbour; bushings, cheek, bridge and axle are capsules too; racks
are reserved in the gantry search and are obstacles to the other arms
in the rail search. The rail cache key now covers the whole clearance
module, so a space-model change re-plans. Rulers: tools/test_gantry.py
(arms vs racks, carriages vs own rack, the recorded mount re-measured,
offset rule, pitch) and tools/test_linkage_tools.py (the carriage pieces
for all four mounts, the mount chooser on synthetic swings). Docs:
docs/articulated-arms.md "The carriage and its drive".

Two harness faults the first renders of this exposed: the rail gantries,
heads and racks had never been visible — performance.gd's frame-variant
switch hides every form_* node whose name is not the active style, and
the gantry objects were caught by it (now whitelisted, and
dev/test_performance.gd checks they are visible); and the pinions on
several arms were tilted — setting one Euler component of an imported
basis that is a quarter turn about X hits gimbal lock, so the spin now
composes on the imported basis (test_performance measures each disc's
thickness along its mount's normal).

## 2026-09-17 — CLOCKWORK rail gantries; rails become obstacles in the rail search

The wide view showed the weakest construction left: every rail hung from
bare brass posts (up to four metres of rod on a disc), and neighbouring
rails simply ran through them. The shoulder pin's head (0.119 m off the
carriage plane) also passed through a post whenever a carriage parked at
its rail end (posts stood 0.12 m out with a 35 mm radius).

formlab/gantry.py builds what a linear guide needs, every dimension from
a rule: a brass rail head at each end capturing both bars (inner face
0.16 m past the reach window, 40 mm clear of the pin heads); a tapered
steel mast, constant across the pin axis, deep along the swing direction
and growing toward the base as a cantilever's bending moment does; a
stepped plinth with anchor bolts on the stage or on a furniture lid; and
where the mast cannot stand straight under the head, an L-bracket (out
along X, then along Z, behind or in front) with a knee brace under each
leg. The bracket is searched per rail end, cheapest first, against every
arm's swept capsules (slid to the pin tips' planes), every other rail's
bars, the instrument forms, the furniture boxes and the gantries already
placed; each piece is judged by its own bounding box, braces as capsules.
The stage now reaches back to z −4.7 so the bell rails' masts stand on it.

Building the gantries exposed a flaw no ruler had measured: the high harp
arm's upper link swept 52 mm through the middle harp rail's bars at 9.3 s
and 41.8 s. Arms were kept from arms, strings, stage and cabinet — never
from each other's rails. formlab/layout_search.evaluate_arm now adds each
candidate rail (bars and heads) to that arm's capsules, so cross_gap
measures every arm of a mechanism against its neighbours' rails. The
re-plan moved the middle harp rail from (3.15, −1.8) to (4.1, −1.4) and
the second bars rail up to 2.75 m; harp arm-to-rail margin 139 mm.

Gantries on the expanded rig: six masts straight under their heads, the
high harp rail's low mast 0.4 m behind, the middle harp rail's two masts
0.35 m out and 0.4 m forward on the floor in front of the cabinet, the
second bars rail's low mast 0.4 m behind. Ruler: tools/test_gantry.py
(pin heads vs head, every arm vs every rail at 120 Hz, recorded brackets
match the search, masts on stage or lid, heads capture the bar ends,
closed meshes). Docs: docs/articulated-arms.md "Rail gantries".

## 2026-09-17 — CLOCKWORK tools built to their mounts: plectrum, ferrule, swan neck, socket

Reading the tool recipe for the "pick looks small" note found a
construction bug instead: the wrist pin sits 0.10 m behind the contact
point (0.20 m above a mallet), and every shank was a straight 0.15 m rod
rising from the tip — no shank reached its crosshead. The blade was also
swept edge-on (thin across the string row, wide along the pluck), which
is why it read as a needle.

formlab/linkage.py: pick_tool(mount) is a 50 × 70 mm tear-drop plectrum
with its face to the string, clamped in a ferrule block with two set
screws; swan_shank() runs a round rod on a cubic Bezier from the ferrule
top — up, back, and vertically into a socket collar hanging under the
wrist pin's boss (chamfered mouth, tenon buried in the boss). The same
recipe is a straight drop for the mallet, whose shank now starts inside
the felt. clearance.tool_mount / shank_path / SOCKET_DEPTH are the rule
(numpy-only, so Blender's bare imports keep working); the clearance
capsules follow the neck (tool: tip→apex, shank: apex→socket), the shank
is judged against strings, and the lower bar is measured against the
tool instead of excused.

Two consequences the new ruler (tools/test_linkage_tools.py) caught:
a wrist 0.15 m above the tip leaves no room for boss + socket + shank
above a 70 mm plectrum, so pick wrists rise to 0.20 m (mallets 0.28 m);
and one arm's second-bar offset pointed down, hanging its second pin
below the plectrum — o and −o separate the bars identically, so
choose_offset now keeps the offset up or level. Rails re-searched
(cache keys changed); both assets rebuilt. Rulers green: rig 324/392
contacts exact, link error 6.4e-7 m, cross-arm +56 mm beyond promise,
self ≥ 18 mm, string ≥ 28 mm, mesh tool clearance 24 mm.

## 2026-09-17 — CLOCKWORK strings that read: glow, cross-axis blur, action cameras

Stills from the front showed no vibration at all, and a forced 6 cm bend
proved why: the pluck axis is world Z, straight at a frontal camera, so
the bend and the flat sheath were edge-on. A real plucked wire precesses
into an ellipse, so wire_string.gdshader now mirrors 35 % of the bend and
the sheath width across X (`cross_axis`). And a thin metallic wire in a
dark studio mirrors darkness: the core keeps a little diffuse body and a
sounding string lights itself — `excitation` (peak excursion of the last
1/30 s over a full 0.02 m pluck, set per frame by performance.gd) drives
emission with its square, tinted by the wire's albedo so a red C sings
red. Two inspection cameras: `--view=9` sits on the second harp arm's
elbow from behind the string plane (knuckle pins, crossheads, bar pairs);
`--view=10` frames the most recently plucked string 45° off its pluck
axis and latches 1.5 s so a run of plucks does not throw it about.
Rulers green on both assets (rig 324/392 contacts exact, cross-arm
margin +56 mm, formlab, joints, joint seats, mesh distance, score plan).

## 2026-09-16 — CLOCKWORK articulated arms: joints, parallel bars, the space they need, wire strings

Brief: helpers for beautiful articulating joints (and radius/ulna-style
bar pairs) for the arms that play the instruments, frames from real
construction, space accounting so nothing intersects, better strings.
docs/articulated-arms.md is the guide.

formlab/linkage.py — joint and link recipes in a link frame (pin A at
the origin, +Y along the link, pin axis +X), built at true length and
never scaled: knuckle joints (fork straddling an eye on a domed pin
with a nut), flat fish-belly bars with forked and eyed ends, crossheads
(two bosses and a web), pick and mallet tools. parallelogram_arm()
assembles the drafting-lamp arrangement: two bars per segment on pins a
fixed offset apart, so every crosshead and the tool stay upright with
no third motor; layers along the pin axis let the two segments cross.
One spec (clearance.DEFAULT_SPEC) sizes every seat.

formlab/rig.py mirrors clockwork_motion.gd to 3e-7 m. Two motion rules
landed on both sides: wrist_offset (picks .15 up and .10 BEHIND the
string — the pin no longer sits on the string it plays) and the bend
hint "back" (a harpist's hanging elbow: with the root above and behind
the strings, an "up" elbow is geometrically forced through the plane).

Space: formlab/clearance.py is a capsule ruler (segment–segment
distance over the sampled piece; self, string and cross-arm gaps);
formlab/layout_search.plan_arms searches rail height/depth and link
length per arm against self, pair, string, scene-box and cross-arm
margins (greedy + coordinate descent, per-mechanism cache since it is
minutes per mechanism). Result: worst cross-arm gap went from −55 mm
(stacked rails, bars through each other) to +139 mm; every arm's self
margin ≥ 13 mm by the conservative ruler; mesh-sampled tool clearance
24 mm.

The finding that mattered: an arm is 0.24 m across its pin axis and
harp strings are 0.11 m apart, so no rail placement can separate two
arms reaching adjacent strings at once — the score planner has to know
the arm's width. Mechanism.arm_clearance: _Solver charges each arm with
the axis interval it crosses while moving and a point over its last
string while hovering, and refuses any plan that brings two arms of a
mechanism closer than that at any time (piecewise-constant occupancy,
checked at every breakpoint). The composition already asks before it
writes, so the rule shapes the piece: The Chamber drops 7 of 247
intended notes (2.8 %, under the 5 % ruler), zero conflicts;
songs/clockwork.py preserves every original plan. tools/test_score_plan.py.

For the planner's positions to be the model's, Mechanism.fan() moved
the harp/rake neck fan into the score (one scale degree per equal
step, feet climbing the diagonal soundboard); formlab/layout reads
fanned mechanisms straight from pos. A dorian scale's uneven steps
kinked the neck spline through the string tops and the sweep went
non-manifold; fan(smooth=2) refits log-length with a quadratic (≤ 2.6 %
of length, pitch untouched) — a real neck is one fair curve the
strings are cut to. dev/test_clockwork.gd now also checks the promised
tip-x separation of every arm pair over the piece at 120 Hz (+56 mm
beyond the promise).

Strings: harness/shaders/wire_string.gdshader replaces the line strips.
A static tube per string; the vertex shader bends it with the 24-node
shape frame (Catmull-Rom, normals tilted by slope) and a translucent
copy is a sheath widened to the last 1/30 s peak excursion — the blur a
vibrating wire shows the eye, denser at the turning points. Gauge by
pitch, wound bronze below C4.

Rulers green on both assets: formlab, joints, joint seats, score plan,
rig (324/392 contacts exact, link error 5.7e-7 m), performance GLB
integration, form clearance. Both assets rebuilt (models/*.blend,
harness/assets/*).

## 2026-09-06 — THE CHAMBER: a score for a machine (e97-e99, the piece, the Godot harness)

The question that started it: what would it take to recreate
Animusic's Resonant Chamber in Godot? The answer, once loam is
the composer: the same thing MIDIMotion did, but in the right
order — the machine is a CONSTRAINT THE COMPOSER ASKS BEFORE
WRITING, not a choreographer that reacts to notes. Five stages,
one day, each with a ruler. docs/chamber-spec.md is the spec.

e97 SCORE RECORDER. loam/score.py: Score wraps a canvas (Loop,
or the new Take — the one-shot canvas whose event tails run
PAST the end instead of folding into bar 1) and records every
pluck / rake / strike as an event with per-mechanism stems, so
the mixdown is provably the sum of the stems (max residual
< 1e-9). Export is loam-score/1: score.json + stems/*.wav +
shapes.f32. 5/5.

e98 STRING SHAPES. fdstring._fdrun grows a capture hook:
displacement sampled at N nodes every SR/rate_hz steps, at the
loop top, so the frame IS the state that produced the sample.
fdshape() bakes one pluck; shape_library() a bank by pick point
with an npz cache. The license to reuse one clip across the
whole harp: the bridge-free stiff string is LINEAR (superpose
two picks: cos > 0.9999) and f0-INVARIANT in normalized
coordinates (220 vs 440 Hz: cos > 0.99, t60 dev < 8%, envelope
mean < 1 dB) — the residual is partial beating from kappa fixed
in normalized units, not a modelling error. Clip size is
frames x nodes x 4 bytes; the export header carries offsets.

e99 PLAYABILITY. Mechanism.build lays strings along an axis and
arms over overlapping reach windows; the solver plans each note
as [t_move, t, t_free] for the nearest free arm (least travel,
ties -> earliest free) and REFUSES a note no arm can reach in
time (t - approach - travel >= free_at) or a restrike inside
restrike_s. can_play() lets the composer ask before writing;
finalize() re-solves globally sorted by (t, mech, string index)
with simultaneous groups ordered most-constrained-first, so the
plan is independent of the order the piece was written in
(112/112 orders identical). Two closed forms for capacity: one
arm on one string is bounded by restrike_s; alternating strings
by approach + travel + recover.

THE CHAMBER (songs/chamber.py). 64 bars, 84 bpm, D dorian, ~86 s
through-composed on a Take: a steel harp (16 strings, 3 arms), a
bronze rake (5 strings, 1 arm: the whole arm sweeps), rosewood
bars (8, 2 arms) — every note asked first with can_play; a
voice that cannot be played on time is dropped, and the piece
reports dropped/intended (0 after most-constrained-first and
asking the constrained voice first). 247 events, 15 cues, four
stems, four shape clips. Rulers: score_recall (every written
onset lands within 30 ms), plan_consistent (no arm overlaps,
t_move < t <= t_free), onset_pitch on >= 99% of isolated notes,
relative chroma {D, A}, bars mode ratio 1:4:10 in a 0.15 s
window. ALL RULERS PASS.

HARNESS (harness/, Godot 4.7, GL Compatibility). Reads the
export at runtime — JSON, AudioStreamWAV.load_from_file,
PackedByteArray.to_float32_array on shapes.f32 — and draws the
annotated track (lanes per stem, pitch/amp/actuator ticks,
motion and recover spans, cues, envelopes, playhead on the
audio clock) over the strings from the exported geometry
vibrating with the baked clips, arms sliding along their
plans, bars flashing with t60, the chamber glowing with its
stem envelope. dev/test_load.gd headless -> HARNESS: PASS.
The point of the exercise: everything on screen came from the
score, and the score came from the thing that decided every
note. The game gets to inherit that, not reconstruct it.

RULER LESSONS EARNED:
  - PITCH AT AN ONSET IS A DIFFERENCE, NOT A SPECTRUM: hps_pitch
    on the mixture read the ringing bass under every harp note.
    onset_pitch takes the after-window spectrum MINUS the
    before-window spectrum decayed by the expected t60, so what
    is left is what the onset added. Then the before-window must
    not straddle another attack (isolation >= 0.35 s, exclude
    simultaneous notes) or the "before" is already the "after".
  - AN ABSOLUTE LOCK METRIC DIVIDES BY AN EMPTY FLOOR: comb
    energy over off-comb energy hit 6e8 in a quiet window and
    called it a perfect lock. onset_lock is bounded (comb
    fraction x populated share) and the CLAIM is relative — the
    written f0's lock over its octave, sub-octave and fifth —
    because the question was "did it play THIS note", not "is
    this window harmonic".
  - RESCUE ONLY AGAINST THE CORRECTED SPECTRUM: an octave rescue
    checked against the raw after-spectrum fired 34 times on
    bass harmonics; against the expected-decay difference, 7.
    The rescue is part of the estimator and inherits its
    conditioning.
  - CHROMA CLAIMS ARE RELATIVE TOO: the crown went to A (every
    D string's third partial is an A). Top-2 = {D, A} is what a
    dorian piece on D actually proves.
  - A SHORT MODE NEEDS A SHORT WINDOW: the bars' 10x mode is
    gone in 0.5 s; 0.15 s with rel=0.003 sees 1:4:10.
  - SOLVER CLAIMS NEED THEIR OWN CLOSED FORM: my first capacity
    prediction assumed the greedy would alternate strings; it
    stays on string 0 (least travel = zero). The ruler was right
    and the prediction was wrong — write the arithmetic for the
    policy actually implemented.

Open threads: the game proper (arms with IK along the plans,
cameras on the cue track, materials); a soundboard / body
coupling so string stems are not the whole voice; shape clips
for the rake (bronze, higher kappa) and per-amp clips if the
linearity license ever breaks (a bridge=True string is NOT
linear); a second machine (Pipe Dream's marble drums — struck,
every hit a projectile with a launch time: same solver, one
more term); the Niwa garden assembly.

## 2026-09-03 — e96: SEMISHIGURE — cicada rain

The garden's last missing voice. New in texture.py: cicada()
— the tymbal as a jittered click train through the abdominal
resonator (bandpass at f_c, width f_c/q). The click RATE is
the buzz; the resonator is the species' formant; syllables
are sung windows with sin^2 edges.

The piece: a 30 s loop. Five aburazemi sizzlers (formants
5250-5850 Hz, rates 80-93 Hz) swell together on ONE written
chorus wave — 4 integer cycles, phases staggered but coherent
— while a minmin-zemi soloist (4300 Hz, 118 Hz, jitter 0.05:
the more tonal buzz) sings two written phrases: miiin, min
min min min, miiiin. 5/5: rates worst 0.7%, formants worst
3.0% with an 943 Hz species gap, 12 syllables mark worst
24.6 ms, the chorus breathes at the written 0.133 Hz with a
10.6 dB swell vs 8.7 designed, seam p81.0. dev_smoke 119.

RULER LESSONS EARNED:
  - THE RULER'S SAMPLE RATE IS PART OF THE CLAIM (e94's
    bandwidth lesson, rhythm edition): rate_contour's default
    flux hop (256) gives the flux series an 86 Hz Nyquist —
    UNDER the 88-118 Hz click rates it was asked to measure;
    pulse_rate's autocorr pinned at the search edge for the
    same reason. frame=256/hop=32 gives the flux clock a
    690 Hz Nyquist and the rates read to 0.7%.
  - A SHORT WINDOW SAMPLES THE JITTER, NOT THE RATE: one
    0.5 s window holds ~59 jittered clicks and its sample
    mean wanders 4% from the written rate with no estimator
    at fault. Pool windows (and, where the species allows,
    write less jitter) — integration time is the only honest
    narrower error bar.
  - START THE MARK WINDOW INSIDE THE GAP: a -0.10 s pre-roll
    reached into the previous syllable's plateau (gaps are
    90 ms) and "first crossing" fired on the window's own
    first sample — 100.0 ms worst, the window edge exactly, a
    number that smells of harness, not signal. When the worst
    error equals a window bound, suspect the window.

Open threads: ASSEMBLE THE NIWA GARDEN (suikinkutsu e92 +
shishi-odoshi e94 + semishigure e96 + wind, one scene);
caustics depth-lowpass; komibuki acceleration; hiki-iro; the
tegoto long arc; hichiriki heterophony over e95's gagaku;
a higurashi (evening cicada, the falling kana-kana) would
give the garden a dusk variant.

## 2026-09-03 — e95: GAGAKU — the dragon flute over the moving sho

The court-ensemble capstone, e91's role for the gagaku
family: three constructs loam already owned, assembled and
each measured ON ITS OWN BUS. The sho plays e93's te-utsuri
verbatim (kotsu -> bo -> otsu -> ju_so, drones + rolled
entrances); the ryuteki (e86) carries a written eight-breath
hyojo-colored melody above it with its own gestures as
claims; the e87 percussion keeps the cycle (shoko at chord
starts, an accelerating kakko roll into the seam, one taiko
DOU at the loop's center). 24 s loop.

6/6: sho entrances worst 0.3 ms off the analytic sin^2
crossing, all 9 ryuteki held spans inside e82's 20 c wind
gate (worst 12.6 c), the written D5 -> D6 register flip
measures 1214.6 c of a written 1200, all 4 grace flicks notch
the envelope >= 8.1 dB, 15 percussion strokes mark worst
9.8 ms under e87's per-voice gates, seam p74.1. No library
change — assembly only.

RULER LESSONS EARNED:
  - A VOICE'S BLOOM IS PART OF ITS RULER (e91's onset lesson,
    membrane edition): the taiko's OWN render puts its flux
    peak 38.6 ms after the strike — the membrane takes that
    long to speak. Amplitude-diff flux with a 12 ms gate read
    physics as a timing miss. e87 already owned the honest
    ruler: spectral flux_series per voice on the doubled own
    bus, per-voice gates (25 ms bronze/skin, 30 ms big drum).
    Check whether an older experiment already paid for the
    ruler before writing a new one.
  - REUSED CONSTRUCTS KEEP THEIR NUMBERS: e93's sho bus
    reproduced its 0.3 ms entrance figure inside a new piece
    untouched — own-bus measurement makes claims portable
    across assemblies.

Open threads: the NIWA GARDEN SCENE (suikinkutsu e92 +
shishi-odoshi e94 + cicadas still unbuilt); caustics
depth-lowpass; komibuki acceleration; hiki-iro; the tegoto
long arc; the gagaku set could gain the hichiriki doubling
the ryuteki line in heterophony (e91's lag ruler is waiting).

## 2026-09-03 — e94: SHISHI-ODOSHI — the bamboo deer-scarer

New instrument pair in nihon.py: bamboo_tok() (the emptied
arm's strike on its stone — five written inharmonic modes,
BAMBOO_MODES, plus a 3 ms contact burst per e84's register
rule) and pour() (the tipping arm's water: gurgle-wobbled
bandpassed splash). The piece is the MECHANISM: fill (thin
trickle), tip (pour), swing back (written 0.55 s), tok —
period 9 s, three cycles in a 27 s loop over faint garden air.

A water clock is a ruler's dream because the mechanism IS the
design column. 7/7: toks mark worst 0.9 ms, pours mark worst
20.0 ms, measured tok-pour gaps within 20.9 ms of the written
arm-return, modes stand worst 0.2 c, the 820 Hz line's t60
measures 140 ms vs written 140 (+0.2%), envelope p99.5 sits
28.3 dB over p20, seam p72.8. dev_smoke 118 green.

RULER LESSONS EARNED:
  - THE RULER'S BANDWIDTH IS PART OF THE CLAIM (time-domain
    edition of e92's threshold lesson): line_env's default
    +-25 c lowpass at 820 Hz has a ~30 ms step response — the
    same order as the 47 ms/20 dB decay it would measure.
    width_c=150 makes the filter fast enough to watch the
    decay it is grading. Every ruler smooths; know by how much
    before trusting a slope.
  - rel=1e-4 FOR FAST MODES: a t60=45 ms mode leaves only
    -36 dB of energy in the whole-file FFT (peak power goes as
    (amp * tau)^2), so mode_freqs' -30 dB bar silently dropped
    a written mode. The quietest ROW of the design table sets
    the threshold, not a default.
  - A POUR IS A BLOOM, NOT A STRIKE (e91's onset lesson,
    re-earned on water): flux argmax landed 76 ms late on
    whichever gurgle swell rose fastest; first crossing of
    -12 dB re the window peak marks the water's arrival at
    20 ms.

Open threads: the NIWA GARDEN SCENE is now fully stocked —
suikinkutsu (e92) + shishi-odoshi (e94) need only cicadas
(semishigure) to assemble; caustics depth-lowpass; komibuki
acceleration; hiki-iro; the tegoto long arc; a ryuteki or
hichiriki line over e93's moving sho.

## 2026-09-03 — e93: TE-UTSURI — the sho changes chords one pipe at a time

Refinement of the sho: in gagaku the aitake do not switch as
blocks — common tones HOLD, departing pipes fade with the
breath, new pipes roll in lowest-first. So the piece's unit is
the PIPE, not the chord. kotsu -> bo -> otsu -> ju_so (6 s
each, 24 s loop) compiles into: four continuous drones
{A5 B5 D6 E6} (each a lapped equal-power pair — two renders,
1 s sin/cos gain laps mid-chord, e83's rule), one F#6 hold
across bo -> otsu, and six entrance events at written times
(chord start + 0.10 + 0.15 per rank, low first).

The headline number: the written sin^2 edge predicts its own
-20 dB crossing ANALYTICALLY (t = edge * (2/pi) *
asin(sqrt(0.1)) = 61.5 ms for edge 0.30), so entrances are
design-vs-measured to the sample. 5/5: entrances worst 0.3 ms
off the analytic crossing with roll order kept, holds worst
dip -0.0 dB over 9 clean crossings, departures fall worst
72.8 dB, membership weakest line 88.5 dB over the probes,
seam p76.1. New in ruler.py: line_env() (heterodyne
single-line envelope). dev_smoke 117 green.

RULER LESSONS EARNED:
  - MEASURE A LOOP ON ITS OWN CIRCULAR EXTENSION: filtfilt and
    convolve on the bare array notched the envelope ~60 dB at
    the seam — the audio held; only the ruler dipped. wrap=True
    pads a second of the loop onto both ends first.
  - BANDPASS-AND-RECTIFY LEAKS NEIGHBORS THROUGH ITS SKIRTS: a
    4th-order +-25 c bandpass rejects a 100 c neighbor by only
    ~3 dB even zero-phased. ruler.line_env was born: heterodyne
    the line to DC, lowpass at the band half-width — the same
    100 c gap becomes a 4x cutoff ratio, -73 dB verified.
  - THE POLLUTION AUDIT MUST COVER EVERY CLAIMED LINE, NOT
    JUST THE ENTRANTS': the docstring proudly audited entrance
    lines and then the holds ruler claimed D6 across bo, where
    D5's h2 sits at 1174.66 Hz — EXACTLY the D6 line. Its beat
    against the drones' +-2 c detunes (~0.8 s period) faked a
    -5 dB dip at the departure boundary. Three exact octaves
    hide in this one progression (A4-A5, E5-E6, D5-D6).
  - AN EXACT 0 c COINCIDENCE IS UNFIXABLE BY ANY FILTER — no
    bandwidth separates identical frequencies. The fix is the
    harmonic table: scope the claim to boundaries where the
    octave-mate is silent. (And a wrong NOTE NAME poisons the
    debug: midi 86 got labeled C#6 and two diagnosis rounds
    surveyed 1080-1140 Hz — a band the real 1174.66 Hz claim
    never touches. The ruler was honest; the label lied.)

Open threads: caustics depth-lowpass; komibuki acceleration;
hiki-iro (koto downward bend); the tegoto long arc (2-3 min
sankyoku movement); niwa garden scene (shishi-odoshi +
cicadas + suikinkutsu); te-utsuri could gain a second layer —
a ryuteki or hichiriki melody floating over the moving sho.

## 2026-09-03 — e92: SUIKINKUTSU — the water-echo pot

New texture-instrument pair in nihon.py: suikinkutsu_ir() (the
buried pot as a stereo modal IR — hollow ~360 Hz body plus
ceramic rings at 1150/1720/2310 Hz, channels detuned +-0.2%:
two listening points on one pot) and waterdrop() (Minnaert
bubble with its rising chirp + a 2 ms impact tick). The tick
is load-bearing: a 900-2400 Hz bubble has NO energy at 360 Hz,
so without the impact the pot's hollow stays silent — e84's
register rule, cavity edition: excitation must reach the
resonance you claim.

The piece: 34 s loop, 22 written drops (seeded arrivals, min
gap 0.30 s) into the pot over faint garden air. The
convolution tail wraps the seam — the pot rings across it by
construction. 6/6: modes stand at written freqs worst 1.9 c,
drops mark worst 7.1 ms, chirp ratios worst 1.2% off design,
pot transfer +27 dB at modes vs between, envelope p99.5 sits
63 dB over p15, seam p80.4. dev_smoke 116 green.

RULER LESSONS EARNED:
  - A MODE IS A CLUSTER, NOT A LINE: channel detuning and
    arrival-pattern sidebands split each resonance into a
    family of spectral peaks, and mode_freqs' k-strongest cut
    spent all eight slots inside the loudest family (360/1720/
    2310 never made the list). merge fuses each family to its
    power-weighted center FIRST — written for the staircase
    disc, earned again by a pot.
  - THE SAME RULER NEEDS DIFFERENT SETTINGS ON DIFFERENT
    SOURCES: default rel found all modes on the drop-excited
    render but dropped two on the pure IR (excitation
    re-weights the peak family); rel=0.001 on the clean IR.
    A ruler's thresholds are part of the claim, not
    boilerplate.
  - `exit ${pipestatus[1]}` bit again — a piped tail read
    dev_smoke's failure as success until the exit was taken
    from the right pipe slot.

Open threads: te-utsuri (sho pipes one by one); caustics
depth-lowpass; komibuki acceleration; hiki-iro; the tegoto
long arc; suikinkutsu could join a garden scene (shishi-odoshi
clack + cicadas + the pot — a full niwa soundscape).

## 2026-09-03 — e91: SANKYOKU — koto, shamisen, shakuhachi (capstone)

The trio assembled the way sankyoku actually works:
HETEROPHONY — all three voices carry the SAME melody,
individually ornamented, with small WRITTEN time offsets. The
shamisen trails the koto by a written 40 ms, the shakuhachi
floats a written 120 ms behind an octave up, and everyone
lands on D at the cadence after a shared breath (ma). 32 s
loop, hirajoshi/honchoshi on D. Koto states the kernel alone,
trio takes phrases 2-3, cadence D across three octaves.

7/7: string lag median 38 ms of written 40 (worst pair 3 ms
off), wind lag 141 ms of written 120 (worst 23 ms), strings
center to 0.8 c / wind to 17.1 c under e82's own 20 c gate,
cadence agrees +0.4/+1.3/+5.6 c, ma sits 21.6 dB down,
signatures re-pass inside the ensemble (sawari +8.7, tsume
+14.0, muraiki +9.4 dB), seam p3.2. No library change.

RULER LESSONS EARNED:
  - HETEROPHONY IS A WRITTEN NUMBER: because every voice plays
    the same line, ensemble "feel" (who leads, who trails)
    becomes a design-vs-measured lag claim per matched note
    pair. Mark strings by pick flux; mark the wind where its
    own envelope first crosses -12 dB re note peak — a breathy
    onset is a bloom, and flux has nothing to bite.
  - ONE GATE PER VOICE, NOT PER PIECE: a shared 15 c centers
    gate was both too loose for FD strings (sub-cent) and too
    tight for the breathy bore (e82's own gate is 20 c, and
    shorter notes average LESS wander, not more). A capstone
    inherits each component's own gates — pooling them
    manufactures either false passes or false failures.
  - e87's composition rule held again: sawari, tsume, and
    muraiki all re-passed their voice tests inside the mix
    with zero re-tuning — verified components compose.

Open threads: te-utsuri (sho pipes one by one); caustics
depth-lowpass; komibuki acceleration; hiki-iro (koto's
downward bend); a longer sankyoku movement with tegoto
(instrumental interlude) structure — the 32 s loop wants to
become a 2-3 minute arc someday.

## 2026-09-03 — e90: KOTO — the paulownia zither (sankyoku's 3rd voice)

New instrument: nihon.koto(), fdpluck2 as the shamisen's
clean-string cousin — barrier parked (no sawari), longer ring,
hard tsume pick near the bridge — plus OSHIDE (the left hand
presses behind the bridge AFTER the pluck; a smoothstep warp
of the decaying note, the honest bend) and a paulownia-box
body (two zero-phase resonant bands ~230/~560 Hz). HIRAJOSHI
tuning helper. With shamisen + shakuhachi, the sankyoku trio
is now complete.

The piece: 30 s solo loop, hirajoshi on D3. Ascending kararin
opens (10 notes, 60 ms), three oshide bends (+180/+100/+200 c),
descending sweep, low D3 vibrato close. 6/6: centers 0.5 c,
oshide worst error 0.1 c (!), tsume +12.5 dB / +7.2 over
pickless twin, body +4.2 dB, kararin 16 marks worst 5.7 ms
with 10 unpolluted ring lines worst 7.9 c, seam p39.9.
dev_smoke 115 green.

RULER LESSONS EARNED:
  - MEASURABILITY IS A PROPERTY OF THE SOURCE, not the ruler:
    the same warp gesture that hid from every detector on
    breathy winds (e86 graces, e89 flutter) is claimable to
    0.1 c on a plucked string, directly, no twins — high early
    SNR and a clean IF track. Pick claims per voice.
  - A CAUSAL BANDPASS ADDS ~90 DEGREES OUT OF PHASE: the body
    resonance design said +5 dB, the ruler said -1.3 — the
    parallel add was CANCELLING. sosfiltfilt (zero-phase) makes
    a parallel band add mean what it says. Measure the design
    before trusting the block diagram.
  - PENTATONIC LADDERS ARE SELF-POLLUTING (e88's series lesson,
    sweep edition): every upper sweep note sits on a lower
    note's h2, and a 45 ms onset window at D3 has a ~44 Hz
    mainlobe against a 9 Hz neighbor (BT wall, per-onset
    edition). Mark the onsets by flux; claim ring lines only at
    fundamentals no octave-mate can fake.

Open threads: SANKYOKU trio piece (koto + shamisen +
shakuhachi — all three voices now exist); te-utsuri (sho pipes
one by one); caustics depth-lowpass; komibuki acceleration;
koto could learn hiki-iro (the pull DOWN behind the bridge —
oshide's negative twin, needs pad logic for a downward warp).

## 2026-09-03 — e89: komibuki — the pulsed breath (two cranes)

nihon.shakuhachi() learns KOMIBUKI (Tsuru no Sugomori's crane
voice): rhythmic diaphragm pushes on the held tone, three
coupled layers gated in after the attack — amplitude pulse
(floor 1-komibuki between pushes), direct-radiation turbulence
riding each push, and a small mean-removed pitch flutter
written into the warp. komibuki=0 stays bit-identical to the
old instrument (checked).

The piece: 33.6 s loop, D minyo over low wind. Two cranes
answer at DIFFERENT written pulse rates (5.2 / 6.5 Hz), the
settling note pulses slow (4.5 Hz). 7/7 first run: rates read
worst 0.09 Hz off written, selectivity +23 dB (rates don't
blur), depth worst 0.25 dB off design, twin contrast +32 dB,
hiss-vs-pulse worst r=0.95, centers worst 8.9 c, seam p21.7.
dev_smoke 114 green.

RULER LESSONS EARNED:
  - A WARP DELTA IS A CLOCK DELTA: twin-delta by WAVEFORM
    differencing fails on pitch-warped twins even when both
    are deterministic and the warp is mean-removed — the
    twins' sample clocks oscillate ~12 samples apart, and the
    difference is noise-slew x clock-offset: 14 c rms of fresh
    in-band noise (more than either track alone). e82's
    twin-delta survived because it differenced MEASUREMENTS
    (FFT peak positions), never waveforms. Difference
    measurements of twins; never subtract their waveforms
    across a time warp.
  - PERIODICITY DOES NOT BEAT THE BT WALL BY ITSELF: a 3 c
    flutter line at 6 Hz sits under the breathy bore's ~11.5 c
    per-bin IF noise floor, and the floor shrinks only as
    sqrt(T) — a ~210 s sustain would be needed. The flutter
    stays in the sound as physical micro-motion and earns no
    ruler; the AMPLITUDE layers carry the claims (+32 dB line,
    depth to 0.25 dB, hiss r 0.95).
  - Distinct written rates per note make the rate claim
    falsifiable twice over: match your own rate AND stand
    >= 10 dB over the other notes' rate bins in your own
    spectrum (selectivity), so a global tremolo can't fake it.

Open threads: sankyoku duet (shamisen + shakuhachi + bell);
te-utsuri (sho pipes entering one by one); caustics
depth-dependent lowpass; komibuki could accelerate within a
note (the crane agitates — needs a chirped pulse train and a
rate-track ruler).

## 2026-09-03 — e88: SURFACING — the turtle rises (arc piece)

The Chelonia sequel, and the first NON-LOOP: a 72 s arc.
Twenty seconds in the deep dark, a 32 s smoothstep ascent
(water pads crossfade dark -> bright, exhale bubbles
accelerate 1.9 s -> 0.35 s gaps, the caustic light grows), the
BREAK at 52.0 s (bandpassed splash + sub thump + seven
droplets falling back), the FIRST BREATH at 52.6 s (the 4k+
hiss climax of the whole piece), then floating: an E-major air
pad whose G#6 IS the sunlight — the major third exists only
above the water. texture.caustics() promoted to the library
this cycle (crest-gated GLASS glints, scalar-or-array
intensity, wrap flag for loop vs arc).

7/7: edges -55/-126 dB, water centroid tracks written u at
r=0.94 (96 -> 205 Hz), light r=0.96, bubble IOI Spearman
-0.99, splash marks -7.6 ms with 33 dB sub drop, breath argmax
52.69 s, G#6 line +3.1 dB under -> +40.5 dB above.
dev_smoke 113 green (new caustics check: determinism, silence
at zero intensity, flicker line at the written ripple rate).

RULER LESSONS EARNED:
  - THE HARMONIC SERIES CONTAINS THE THIRD: E's series has G#
    at h5/h10/h20, so "the major third arrives" can never be a
    chroma-class claim — the class is never empty. Claim a
    WRITTEN LINE instead (G#6 = 1648 Hz prominence over local
    floor). The line ruler then found two leaks chroma had
    averaged invisible: the deep caustics' default palette
    included midi 92, and the body pad's h10 (E3 x 10) IS 1648.
    You cannot forbid a note you are quietly playing.
  - ESTIMATOR VARIANCE MUST FIT UNDER THE DESIGN SWING (e86's
    BT budget, centroid edition): each 45-cent padsynth line is
    ~2 Hz of noise bandwidth (~0.5 s coherence), and the whole
    written brightening is one octave of centroid — 2 s windows
    scatter +-40 Hz against a 100 Hz swing and rank-vs-index
    reads noise. 6 s windows, correlated against the written u
    (not the index: rank-of-monotone-u equals rank-of-index,
    but Pearson stops the flat start from voting).
  - AN ARC RETIRES THE SEAM and replaces it with SHAPE claims:
    silence at both edges, and events that must own their
    moment — the splash and the breath are 600 ms apart, so
    each gets a BAND it owns (splash written < 3800, breath
    measured 4000-9000). Overlapping measurement bands let the
    louder event win both argmaxes.

Open threads: sankyoku duet (shamisen + shakuhachi + bell);
komibuki pulsed breath; te-utsuri (sho pipes entering one by
one); caustics could learn depth-dependent lowpass (deep
glints should be duller, not just sparser).

## 2026-09-03 — e87: ETENRAKU — the full ensemble (capstone)

Four cycles converge: e84's hichiriki melody, e85's sho halo,
e86's ryuteki dragon line an octave above, and NEW — the
time-keepers: nihon.shoko() (flat-bronze-plate modal 'chin',
every other beat), nihon.kakko() (tight fddrum 'ka': katarai
answer-taps plus the MORORAI accelerating roll pouring into
each 8-beat cycle head, IOIs 0.25 s -> 0.09 s geometric), and
nihon.taiko() (fddrum at 60 Hz: the soft zun pickup and the
big DOU). Percussion pattern is gagaku-style simplified — the
exact Etenraku drum score is figure-locked, like the aitake
charts were.

38.4 s, haya yo-hyoshi. 8/8: every strike marks (12 shoko + 3
DOU + 6 katarai worst 9.2 ms), all 3 rolls accelerate
monotonically to 0.37 final/first IOI, melody worst 8.8 c,
flips hold both registers, halo troughs on every change,
taiko/kakko/shoko sit 111/892/1932 Hz, poles {E, B}.
dev_smoke 112 green.

RULER LESSONS EARNED:
  - A mark window must stay under HALF THE SMALLEST WRITTEN
    GAP: the mororai's 75-110 ms tap spacing under a +-0.2 s
    flux window let neighboring marks lock onto one loud tap
    and every IOI read zero. The window is now a parameter of
    the marks helper, chosen per claim.
  - Wrap for PLACEMENT, never for ARITHMETIC: %-ing the roll
    tap list before IOI math read one interval as -38.3 s when
    the third roll crossed the seam. Keep unwrapped times for
    ordering claims; wrap only at lookup.

Open threads: gagaku done for now — the trio + kit stand as a
reusable ensemble. Elsewhere: sankyoku duet (shamisen +
shakuhachi + bell); the turtle surfacing arc piece;
texture.caustics() promotion; komibuki pulsed breath.

## 2026-09-03 — e86: ryuteki — the dragon flute completes the trio

Third gagaku wind. nihon.ryuteki(): the waveguide flute voiced
breathy, plus the REGISTER FLIP (fukura -> seme, the mid-breath
jump to the overblown octave on the same fingering — two
renders of the same bore, flute()'s `overblow` IS the
jet-speed jump, crossfaded in ~80 ms) and FINGER FLICKS (~90 c
warp pits + ~6 dB amplitude notches: the striking finger
briefly kills the resonance — e81's hand lesson, wind
edition). Notes self-center by constant correction (e82's
stance without the knots).

The piece: Etenraku phrase A a third time — e84 the melody,
e85 the harmony, e86 the ryuteki way: an octave up, the long
E's starting fukura and flipping to seme mid-breath. 38.4 s.
6/6: flips land fukura within 25.8 c / seme within 9.7 c of
the octave, held centers 19.9 c worst, strike notches >= 6.4
dB with false notches <= 2.8 dB, gust 3.5-9.1 dB, E crowns the
fundamental band. dev_smoke 111 green.

RULER LESSONS EARNED (a whole saga this cycle):
  - A 50 ms pitch dip on a BREATHY voice sits below honest
    measurability, fundamentally: to see a 90 c dip you need a
    band ~90 c wide, and that band's noise envelope fluctuates
    on exactly the gesture's timescale (bandwidth x time ~ 1).
    Four detectors tried and failed honestly: widened IF band
    (admits the hiss, phase slips everywhere), band-energy
    handoff (narrowband noise swings 13 dB at gesture speed),
    twin-difference (each dip's cumulative resample shift
    misaligns the tracks after the first grace), bare IF dips
    (graceless notes self-dip to -300 c). The resolution was to
    LISTEN TO THE PHYSICS: a striking finger also kills the
    resonance, so the gesture carries an amplitude notch — and
    broadband envelope marks don't fight narrowband noise
    (6.4 dB notches vs 2.8 dB false floor). When a gesture
    can't be measured, ask whether the gesture is missing part
    of its own physics.
  - Chroma on a solo breathy instrument is a coin flip: the
    hiss votes uniformly (full-band top-2 read E 0.12 F 0.10).
    Restrict the band to where the fundamentals live and claim
    only the crown.

Open threads: THE CAPSTONE — full Etenraku, all three winds
plus kakko/shoko/taiko percussion (needs a kakko roll and a
shoko clang, small); te-utsuri; sankyoku duet; the turtle
surfacing arc.

## 2026-09-03 — e85: sho — the aitake breathe through Etenraku's harmony

Second of the gagaku winds. nihon.sho() + nihon.AITAKE: the
mouth organ's cluster chords, each breath an arch swell whose
reeds BRIGHTEN as pressure rises (per-harmonic env^(1 +
bright*(h-1)) — the swell opens the spectrum, not just the
level), over a level floor (the player inhales AND exhales
through the reeds: the sound turns, it never stops). The
first/last 0.35 s are a FIXED-TIME equal-power turn whatever
the breath's length, so overlapped breaths sum to a floor with
the trough centered on the chord change.

VOICING STANCE, on the record: fundamentals verified (kotsu
A4, ichi B4, ku C#5, bo D5, otsu E5), the Category-1 shared
collection A4-B4-D5-E5-A5-B5-D6-E6-F#6 verified, gyo
(A5-B5-D6-E6-F#6) and sojo-ju (G5-A5-B5-D6-E6) published
exactly (Momii, MTO 26.4); the four Category-1 voicings are
COLLECTION-CONSTRAINED REALIZATIONS (fundamental at the
bottom, gyo-like cluster above) because every source keeps its
full chart inside an image. Named, not guessed.

The piece: e84's Etenraku phrase A with the melody removed —
only its harmonic halo, by the documented rule (the sho sounds
the aitake whose fundamental IS the melody note): bo, otsu,
ichi, kotsu, ichi, otsu, bo, otsu. 38.4 s, 8 breaths. 6/6:
membership both directions (written lines within 2.0 c,
weakest written pipe +93.5 dB over the loudest out-of-
collection probe), lowest prominent line is the naming pipe in
all 4 aitake, breath troughs within 0.20 s of every change,
swell-brightness r 0.81-0.96 within all 7 long breaths, chroma
poles {E, B}. dev_smoke 110 green.

RULER LESSONS EARNED:
  - When a claim fails, suspect the CLAIM'S SCOPE before the
    sound: pooling all windows, chord identity moves the
    centroid ~150 Hz uncorrelated with level and
    swell-brightness read r=-0.08; scoped WITHIN each breath
    (where the chord is fixed) the same audio reads 0.81-0.96.
    Same family as e84's register-of-validity lesson.
  - Duration-coupled envelope edges put the trough where the
    durations say, not where the music says: a 1.6 s arch
    meeting a 6.4 s arch drifted the breath turn 0.40 s. Fixed-
    time equal-power edges (sin^2/cos^2 over 0.35 s) center the
    trough on the written change for ANY pair of lengths.
  - Membership rulers want probes chosen for harmonic
    innocence: C5/F5/G5/G#5 sit on no low harmonic of any
    written pipe, so "absent" means absent (+93 dB margin).

Open threads: ryuteki completes the trio -> full Etenraku
(melody + halo + flute doubling, kakko/taiko pulse); te-utsuri
(pipes entering one by one at chord changes, not as a block);
sho breath noise as a measured claim; komibuki; sankyoku duet.

## 2026-09-03 — e84: hichiriki — the OTHER wind circuit, demoed on Etenraku

The winds continue ("and so forth"). winds.reedpipe() is new:
a pressure-driven REED VALVE on a cylindrical quarter-wave
bore (clarinet family, Cook/Smith stance). Where the flute's
jet ADDS energy at a labium, the reed is a valve — mouth
pressure minus the returning wave sets its opening (r =
offset + stiffness*dp, clipped), and the open end inverts the
reflection so only odd harmonics resonate. Same block-
vectorized loop and self-tune-by-listening scaffold as
flute(); landed within ~1 cent across the register first try,
odd/even +44 to +59 dB.

nihon.hichiriki() voices it: EMBAI (the famous wide approach
glide, ~120-140 c pour over 0.35 s — twice the shakuhachi's
meri, via the same warp resample), the nasal 0.9-1.9 kHz
presence formant, and REED WARMTH — the raw valve is square-
pure, so a touch of asymmetric waveshaping (out + 0.12 out^2)
restores the even partials a real reed's imperfect closure
provides (25.6 dB of evens put back).

The demo: Etenraku phrase A (hyojo on E, contour
D-EEBBABEEEDE per the standard transcription), haya yo-hyoshi
at 1.6 s/beat, over a soft sho-like padsynth drone. 38.4 s.
7/7: odd bore +48.2 dB, warmth restores 25.6 dB of evens, all
12 notes land their written midi (worst late-sustain center
8.8 c), 4 deep embai glides carry 95-98% of design vs
glideless twins, presence band +8.8 to +9.2 dB over raw in
the low register, chroma poles {E, B}. dev_smoke 109 green.

RULER LESSONS EARNED:
  - A ruler's register of validity is part of the ruler: at E5
    the cylindrical comb (659, 1977 Hz...) SKIPS the 0.9-1.9k
    formant band entirely, so "formant vs raw" is only a
    physical claim where an odd harmonic lives in the band —
    gate the claim on the notes where it means something
    (A4/B4), don't average it with notes where it can't.
  - The e82 twin-delta ruler is now proven portable: same
    gates, third instrument (meri -> embai), zero re-tuning.
  - A written glide's TAIL is part of the written contour: the
    center-pitch window must sit past it (late-sustain window
    dur-0.6..dur-0.15) or the ruler reads the design as error
    (-7 c systematic at mid-note on a 120 c embai).

Open threads: sho aitake clusters (the real gagaku drone —
free-reed cluster chords, maybe additive with breath-cycle
envelopes); ryuteki to complete the gagaku trio; full Etenraku
(phrases B and C exist); komibuki pulsed breath for the
shakuhachi; sankyoku duet.

## 2026-09-02 — e83: Chelonia — the turtle in the light (operator commission)

The green sea turtle piece: feeling the current, enjoying the
sunlight catching through the ripple crests. 76.8 s, E major
water. Four layers, each with a written physics and a ruler:

  - THE WATER: dark and bright padsynth draws of E2, crossfaded
    by the SURGE (4 swells/loop, 19.2 s) — the medium breathes
    in level and brightens as it pushes.
  - THE BODY: mono E3 pad that pitch-LEANS ±10 c with the surge
    via e82's warp resample — born last cycle as a drift
    CORRECTION, an expressive gesture one cycle later. The
    turtle is silent; the body is felt, dead center.
  - THE LIGHT: 179 glass glints (modal GLASS, high E pentatonic)
    whose density is gated by crest(t)^3 at the ripple rate —
    1.25 Hz, exactly 96 cycles/loop — under a 2-cycle sun curve.
    Caustics are a POINT PROCESS: bright lines sweep past at the
    ripple rate, and clouds pass.
  - THE EXHALE: rising-chirp bubble runs at each surge crest.

10/10: surge line at exactly 4 cyc/loop (10.2x), centroid-vs-
crossfade r=0.83, lean r=0.85 at 11.8 c depth, flicker line
1.250 Hz (15.8x), sun arc r=0.89, caustic side/mid -7.2 dB vs
body -286 dB with water corr 0.00, register split 10.2x,
exhale-to-measured-crest 0.10 s, chroma poles {E, B}.

RULER LESSONS EARNED:
  - EQUAL-POWER OR THE FADE IS THE ENVELOPE: linearly
    crossfading two decorrelated pads dips ~6 dB mid-fade and
    stamped a double-humped 8-cyc/loop line on a 4-cycle
    design. RMS-normalize the pads and divide by
    sqrt(gd^2+gb^2): the written level curve becomes the
    measured envelope, same night and day as e79's census fix.
  - FIT PHASE GLOBALLY, DON'T TRUST A LOCAL ARGMAX: near a
    sine crest the design is flat, and padsynth's narrowband
    beating wobbles 0.2 s RMS frames enough that a local
    envelope argmax wanders ±1 s for free. Projecting the whole
    loop onto the quadrature pair at the design rate reads the
    crest phase to 0.07 s.
  - A claim can tie two buses together: the exhale ruler
    checks bubbles against the MEASURED water crest, not the
    written time — verifying the chain, not the intention.

Open threads: more nihon winds ("and so forth" — hichiriki?
sho cluster chords?); caustic glints as a reusable
texture.caustics() if a second piece wants them; the turtle
surfacing (a piece-length arc, not a loop: breath held then
released); sankyoku duet (shakuhachi + shamisen + bell).

## 2026-09-02 — e82: shakuhachi — a honkyoku for the temple bell

The winds, per operator direction. loam.nihon.shakuhachi():
the self-tuning waveguide flute plus a GESTURE LAYER, because
what makes a shakuhachi is pitch motion the stationary bore
cannot make. Measured first, built second: jet pressure does
NOT bend the sustained waveguide pitch (0.70 -> 0.95 pressure,
sub-cent), so the meri scoop is a time-warp resample of the
tuned note; muraiki pushed through the bore gains only 1.9 dB
(the cubic jet SATURATES — more breath in, same hiss out), so
the gust is a direct-radiation hiss path that never enters the
bore, same stance as the click and the don. Yuri rides the
warp too, entering after 0.9 s, with a small in-loop pressure
vibrato so amplitude breathes with pitch. flute() gained
scalar-or-envelope `breath` (scalar path bit-identical).

Two instrument-side mechanics that took probing to earn:
PRE-ROLL THE BORE 0.5 s (the waveguide's first ~0.25-0.5 s is
mode-settling fog — a gesture written there is neither heard
nor measurable; discard it and the attack becomes the gesture
layer's fade plus the gust, which is what a shakuhachi attack
IS), and DRIFT-CONTOUR CORRECTION (the bore drifts +21c early
on some seeds — enough to eat a written scoop exactly; the
instrument measures its own IF at 0.25 s knots and writes the
inverse into the warp, so slow drift is corrected while the
±25c fast wander survives — the bamboo's life).

The piece: nine breath-paced phrases in D minyo (D F G A C)
over the e79 temple bell, D2 at the seam, D3 at the half.
38.4 s. 7/7: seam p0.91, all 9 sustain centers within 10.8 c,
deep scoops carry 97/91/96% of their written slide vs
scoopless twins, muraiki gust 11-12 dB with 5.7 dB separation
from soft notes, yuri line 2.32 Hz at 2.8x prominence and
61 c depth, bell hum+prime true and tolls within 30 ms,
chroma poles {D, G}. dev_smoke 107 green (new: shakuhachi
contract, ruler_if_pitch).

RULER LESSONS EARNED:
  - ruler.if_pitch born: spectral-peak detectors scatter
    ±100 c on breathy tones; the analytic phase of the
    zero-phase narrowband-filtered signal does not care.
    Synthetic contract: +25 c tone under 0.5-sigma noise
    reads 24.8 c.
  - A BREATHY ATTACK IS NOT ONE CLEAN CHIRP. This piece's C5
    opens on TWO tonal lines ~90 c apart at comparable power;
    every median-based read (IF included) scattered from +14 c
    to 246% of design across attempts — while FFT deltas
    proved the scoop present all along. No detector can name
    "the" pitch of a two-line attack. The honest question is
    not "what pitch is this" but "how far did the warp move
    what's there": the same-seed scoopless TWIN shares the
    exact line cluster, and the strongest-early-line FFT delta
    between note and twin cancels the cluster and isolates the
    written slide (C5: -26.3 c measured on a -26 c design).
  - Keep the gust out of the melody register: a broadband
    hiss floor inside the tone's IF band pulls any median
    toward the band center — it cost a written -26 c slide
    its measurement before it cost anything musical (hiss
    band floor now 2 kHz, steep skirts).
  - Cross-note level comparisons lie when notes are peak-
    normalized: measure gusts as WITHIN-note attack-vs-
    sustain contrast, then compare contrasts.

Open threads: operator's green sea turtle piece is next (the
current, and sunlight caustics through ripple crests — a
major composition); more nihon winds/voices ("and so forth");
ro-tsu-re-chi fingering scale helper; komibuki (pulsed
breath) as an envelope gesture; shakuhachi + shamisen sankyoku
duet over the e79 bell tower.

## 2026-09-02 — e81: loam.nihon is born — shamisen, demoed on "The Next Episode"

Operator direction: take the strings to Japan, demo with the
opening tune of Dr. Dre & Snoop Dogg's "The Next Episode"
(the David McCallum "The Edge" riff), then develop the winds.

The shamisen was already latent in the library: SAWARI is
jawari physics (the same one-sided barrier fdpluck2 has
carried since e48 — two traditions, one trick: give the
string something to slap); the BACHI SNAP is e80's click
writ large (wider band, 2.5-11 kHz); new is the DON — the
bachi strikes the hide and the string in one gesture, so a
two-mode membrane thump lands at the string's speak time
alongside the click. loam/nihon.py: shamisen(f0, dur, amp,
sawari, snap, thump, pick), honchoshi tuning helper. Sawari
maps exponentially to barrier depth (the buzz only wakes
below gcurve ~0.06: gc 0.03 = +7 dB above 2 kHz, centroid
600 -> 1957 Hz; the sitar's own 0.2 is barely audible on
this softer silk string). dev_smoke 105 green.

The demo: Eb minor, 95 BPM, two 4-bar cycles — lead riff on
clean upper strings, bass on the full-sawari low string
walking Eb -> Cb under bar four, cycle B adds a low sawari
echo. 8/8: all 24 melody notes within 10.6 cents (the tune
IS the tune), all 48 bass strokes within 7.4 cents, sawari
bass +8.0 dB over its clean counterfactual, don +17.7 dB in
its band, all 62 bachi strokes mark within 4.6 ms (e80's
click contract holds cross-instrument), dotted-eighth groove
line 2.08 Hz at 6.3x, Eb crowns.

RULER LESSONS EARNED:
  - THE HAND IS PART OF THE MODEL. Letting each bass stroke
    ring into the next blurred the Eb->Cb walk to 330 measured
    cents: consecutive strokes share a string, and a fretting
    hand chokes the old note. Truncate + 20 ms fade at the
    next stroke's arrival; the walk snapped to 7.4 cents.
  - PARTIALS ARE NOT BINS, the bass edition: a 0.14 s pitch
    window quantizes 60-80 Hz to 7.1 Hz bins — the misreads
    sat exactly on bin multiples (71.4 = 10 bins, 64.3 = 9).
    And the don's head modes own the first 50 ms. Window
    0.05-0.25 s, Hann, zero-pad 1.8 s: worst error 7.4 c.

Open threads: shakuhachi next (operator direction — the
winds); sukui/hajiki stroke variants; kouta phrasing over
honchoshi; sawari as a per-note dynamic (the tsugaru attack).

## 2026-09-02 — e80: "The Mizrab Leans In" — click as a written parameter

Refinement cycle: the landings overlay hack is now first-class.
fdpluck2 takes `click` (click-to-string peak ratio, default 0 =
bit-equal legacy), fusing the mizrab's contact transient at the
string's OWN speak time — so a caller placing the buffer at
(grid - speak_time) lands the click on the grid regardless of
click amount. dev_smoke holds the SUBTRACTION contract (clicked
minus bare is exactly the click: peak = click*amp*0.9 to 1e-9,
support = 8 ms at the bloom, low band within 0.5 dB). 104
checks green.

The piece: a 20-note jhala line every 0.3 s under a 0.15 s
chikari curtain; click depth rides one seamless cosine (bare at
the seam, 0.35 mid-loop). 7/7: level-median HF attack excess
tracks the written lean r=0.943; low band uncorrelated (r=+0.06
— mark, not loudness); in the mix, all 47 clicked strokes mark
within 2.2 ms while bare strokes scatter to 73 ms worst;
stroke line 3.335 Hz at 67x; D crowns.

RULER LESSONS EARNED:
  - On a SOLO string the click barely moves any energy ruler
    (the FD pluck's own attack is hp-bright: +1.5 dB in its
    tightest window) and doesn't move the flux peak at all.
    The click's whole value is ENSEMBLE legibility — it exists
    to win an argmax under masking. So the library contract is
    by subtraction (exact, deterministic), and the perceptual
    claim lives where the phenomenon does: in a mix.
  - Masking has a density threshold: under a 0.3 s carpet bare
    blooms still marked within 1.1 ms median — no phenomenon.
    At landings density (0.15 s tails) bare strokes scatter to
    73 ms worst while every clicked stroke holds. And the
    honest contrast gate is WORST-CASE, not median: most bare
    strokes peek through; the occasional vanished one is what
    breaks the flow (exactly what the operator heard).
  - Per-stroke design-vs-measured correlation dilutes under
    per-note variance (six strings, six bare attacks); e78's
    aggregate move applies: correlate the level MEDIANS
    (r=0.943 vs 0.774 per-stroke).

Open threads: half-caught bells; change-ringing peal orders;
ektal composition over the caught-bell theka; e78 shoulder
asymmetry. Operator direction received: shamisen next (sawari
is jawari physics; the bachi snap is `click` writ large), then
shakuhachi and the winds.

## 2026-09-02 — e79: "The Bells Learn Ektal" — the caught-bell khali

New idea (78 was tooling): Vespers' church bells take up era
V's 12-matra clock. Ektal's theka rung by a fixed belfry (one
bell per bol family, one pan per bell — a real tower), the
tirakita flourish as a downward four-bell peal at matra/4,
and the khali translated into campanology: the CAUGHT BELL.
Matras 3 and 7 (and matra 7's bol is literally *kat*, hands
closed) are struck normally, then a hand closes on the rim at
100 ms and the ring dies (exp catch, -60 dB in 0.35 s). Same
bell rings open on matra 9 — emptiness as a bell that dies
young, and the same bronze proves it both ways. Quiet oh-choir
(D2+A2 padsynth) 14 dB under the tower; Vespers' FDN room.
38.4 s seamless, 4 avartans, D aeolian.

Measured (11/11): seam p32; all 72 written strikes marked,
worst |dev-med| 1.4 ms, weakest mark 154x its local flux
floor; caught A3 prime-band drop min 43.5 dB vs open A3 max
7.4 dB (separation 36 dB); tirakita spacing worst 2.6 ms;
matra line 1.251 Hz at 63x (tirakita sub-line 5.003 Hz at
42x, info); dhin bell's hum+prime within 1.2% of written;
choir -14.0 dB; D crowns the chroma.

RULER LESSONS EARNED:
  - A BELL IS NEVER SILENT BETWEEN STRIKES. Detuned mode
    pairs beat, and the swells fire any global onset census:
    onset_times read 130 "onsets" for 72 strikes, and ghosts
    survived even k=16 / floor 0.5. High-passing made it
    WORSE (119-134): in the near-empty HF band the local MAD
    collapses and the threshold chases the knock's noise tail
    — e39's rest lesson, met again from the other side.
  - So the landings mark ruler is the instrument for ringing
    textures too: per-written-time flux argmax on the band
    the mark owns (the contact knock above the tower's top
    ring mode), PLUS a per-mark prominence floor (>=3x local
    flux median; measured min 154x) so a missing strike
    cannot hide behind a lucky argmax landing near the
    median. Count events only when the texture actually
    goes quiet between them.
  - The caught/open claim wants LEVEL DROP, not decay_t60:
    two banded RMS windows (110 ms and 500 ms post-strike)
    give a 36 dB separation with no envelope fitting, and the
    open-bell gate doubles as a t60 check (4.2 s ring predicts
    ~5.6 dB across the window gap; measured max 7.4).

Open threads: a full ektal composition over this theka (the
tower as timekeeper under a melodic voice); change-ringing
permutations of the peal order (e39's rounds meet the taal);
caught-bell ratio as a dynamic variable (half-caught strikes);
the mizrab click as a first-class fdpluck2 excitation; e78's
rising-shoulder asymmetry still unexplained.

## 2026-09-02 — showcase: "Avartan" (songs/avartan.py)

First of the three operator-requested showcase pieces (landed
last — five renders of honest calibration; file arrived with
the repair commit). Spirit: one full turn of the wheel. The
whole raga arc in a single 96 s seamless cycle, every era-V
construct in one ensemble: alap (three bowed sarangi phrases
through the certified entry shelf, ga hold with written
andolan), jor (pulse emerges: Sa-Sa-ga-Sa on the 0.48 s
grid), gat (the e66 sentence x3 with the third raised to ma,
over twelve tintal avartans of e59 bols), jhala (80-slot
engine at 8.33/s), and e76's tihai whose third Sa IS the sam:
86.4 + 62x0.12 + 2x(7x0.12) + 4x0.12 = 96.0 = 0. The piece
ends by beginning.

Measured (13/13): seam p68.6; section clocks 2.06/3.32/8.35
Hz at 6/56/6x prominence vs alap's 4.3x (stillness, then
pulse); nine bow holds worst 4.7c; andolan 1.27 Hz / 33c
(written 1.25/35); khali bass hole 0.009 over twelve
avartans; tihai self-similarity at the 0.84 s lag r23 0.80
vs control 0.28; all 240 jhala ticks within 3.3 ms, 87 time
marks worst 3.8 ms; sam stroke at 12 ms; taraf halo -20.2 dB;
theka -13.0 dB beside the voice; Sa crowns the chroma.

RULER LESSONS EARNED (beyond those logged in the repair and
e78 entries, which this piece forced):
  - THE TABLA RESTS FOR THE TIHAI. With the theka thundering
    through the countdown, the melody-band self-correlation
    read 0.21 (the bayan owns 105.6 Hz inside a naive
    100-210 band). Banding to the tihai's own notes (135-190)
    AND the traditional gesture — drums out from 93.8 s,
    returning as the sam itself — took it to 0.80/0.86.
  - AN ARRIVAL OUTWEIGHS ITS ECHO: r23 tops near 0.84 because
    the sam's pressed bayan (141.2 Hz, in-band) lands inside
    the third window only — by design, so the gate is 0.80
    with the mechanism, not 0.85 with a wish.

Open threads: the arc at double length (a real vistar in the
gat); a second gat sentence in counterpoint; meend into the
tihai notes.

## 2026-09-02 — the luthier's repair: time marks (landings + avartan)

Operator, on Nine Landings: "where the beat is held by the
voice that's there the whole time, I feel some of the notes
that come on top are missing the time mark, so it sounds off
and breaks the flow." The ear was right three ways, and each
mechanism got a measurement:

  1. THE TIMEKEEPER WAS LAPSING. Every 4th slot the chikari
     tick was REPLACED by the melody note. Now chikari strikes
     every slot; melody rides on top of the tick. Verified:
     all 320 ticks (240 in avartan's jhala) within 3.5 ms of
     the median.
  2. A LOW STRING CANNOT MARK TIME. fdpluck2 at 123-220 Hz
     blooms — its spectrum fills in over tens of ms, and its
     flux peak wanders 0..64 ms with context (worst where the
     line steps down and the old tail cancels into the new
     attack). Fix: the mizrab click — the pick's own 8 ms
     3.5-9 kHz tick at -16 dB — stamps every melody-family
     stroke. All 90 marks (87 in avartan) within ~4 ms.
  3. SPEAK-TIME COMPENSATION: each voice written speak_time
     early (ruler.speak_time: steepest 4 ms envelope rise) so
     perceived attacks, not writes, sit on the grid.

RULER LESSONS EARNED:
  - THE ENVELOPE CANNOT SEE A STROKE THE FLUX CAN (e75's
    founding lesson, turned on our own detector). At 10
    strokes/s under 0.9 s tails, ~9 rings stack and a stroke's
    envelope contribution vanishes — probed: the envelope
    DECAYS straight through a written stroke. Every
    env-crossing/env-slope detector variant read phantom
    60 ms lapses; the flux-series peak detector reads all 320
    within 3.5 ms.
  - MEASURE THE MARK WHERE IT LIVES: full-band flux lets the
    bloom outvote the click; the ear locks to the sharp high
    band, so the mark ruler listens above 3.2 kHz.
  - A NEWTON STEP ON A NONLINEAR DETECTOR DOES NOT CONVERGE:
    per-stroke write corrections from measured offsets moved
    the grid audibly and left the outliers in place. When the
    correction fights the voice's nature, change the voice
    (add the click), not the schedule.

Both showcase renders re-verified end to end: landings 13/13,
avartan 13/13 (its tihai control dropped to 0.28 with the
unbroken tick — cleaner, not just equal).

Open threads: mizrab click as a first-class fdpluck2 option
(excitation noise burst at the pick, not an overlay); do the
sarangi's bowed entries want speak-time compensation against
the theka; a jhala with the click level as a written voice
(brightness breathing).

## 2026-09-02 — session 78: the prominence floor (e78)

Refinement/tooling cycle, mid-triptych. The Avartan showcase
forced a ruler change — crown ratios fail wherever a carpet
voice owns the flux spectrum — so PROMINENCE (line magnitude
over the mask-band median) is now library: ruler.flux_line
(freq, prominence). e78 calibrates it with one variable: a
3.333 Hz tabla tick sinking into a constant tanpura carpet,
level(t) = -18 + 12 cos(2 pi t/19.2) dB, -6 at the seam to
-30 mid-loop and back. 6/6 rulers; dev_smoke 101 -> 103
(flux_line + speak_time; see the repair entry above).

Measured: corr(written dB, log prom) 0.909 over 24 windows;
loud (>= -11 dB) windows read 4.6..8.4x, sunken (<= -26 dB)
2.3..2.6x — x1.79 separation, no overlap; every window with
prom >= 6 reads the line within 2% of 3.333 Hz; THE FLOOR:
prominence crosses 2.0x at -28.6 dB written depth — below
that, in this carpet, no flux ruler can testify. Avartan's
jor (6x) and jhala (6x) gates now stand on this curve.

RULER LESSONS EARNED:
  - PROMINENCE IS RELATIVE TO THE LOCAL FLOOR. First cut used
    the 4-strikes-then-silence tanpura cycle: the same written
    tick depth read 2.4x in a strike-rich window and 31x in a
    strike-free one (the median collapses when the carpet
    rests). The carpet must be flux-stationary before depth
    means anything — struck every 1.2 s, uniformly.
  - THE CARPET'S OWN COMB CAN SIT ON YOUR LINE. A 1.2 s
    strike cycle puts its 4th harmonic at exactly 3.333 Hz;
    quiet-window prominence (2.2-2.6x) is partly the carpet
    testifying at the tick's own frequency — which is why the
    sunken gate is a MEASURED ceiling, not an assumed zero.
  - FLUX_SPECTRUM IS A CLAIM OF STATIONARITY IN LEVEL TOO
    (e77's lesson, in amplitude): windows holding the steep
    +/-12 dB shoulders of the breath read lower prominence
    (6.2/6.3 vs 6.9/8.4 flat), and the two rising-side crest
    windows smear a bin low (3.27/3.15 Hz) — AM sidebands.
    The rising/falling asymmetry has no earned mechanism yet:
    open thread.

Open threads: why do rising-shoulder windows smear worse than
their falling mirrors; a flux_line variant with a level-ramp
correction; the floor curve vs carpet density (one number per
carpet — a family of calibration curves).

## 2026-09-02 — showcase: "Nine Landings" (songs/landings.py)

Third showcase piece. Spirit: equal in phase, unequal on the
clock. A chakradar — the tihai of tihais, the oldest open
rhythm thread — over an e77 breathing grid at double scale:
38.4 s, 320 strokes, TWO breath cycles, rate 8.333 -
2.2 cos(4 pi t / 38.4). The mukhda (ma-ga-Sa landing on Sa)
is stated nine times at STROKE lags of 7 within each tihai
and 24 between tihais: 254 + 2x24 + 2x7 + 4 = 320 = 0, so
the ninth landing IS the sam by arithmetic — while the grid
decelerates from ~10 to 6.1 strokes/s underneath, so the
countdown audibly slows and still lands on zero. Tabla dha
marks each landing (the piece's namesake), pressed bayan
takes sam; tanpura and unbroken da/ra jhala underneath.

Measured (10/10): landing phases (tabla-bus onsets mapped
through the written phase integral) sit within 0.11 slots of
254+{4,11,18,28,35,42,52,59,66}; clock gaps stretch 0.70 ->
1.16 s (x1.66); sam dha at t=12 ms; contour median 0.7%,
worst 2.9% in statement-clear windows, folded integral 319.9
vs 320; line readback 1.6c median at the breathing times;
drums -18.4 dB; chroma crowns Sa; seam p70.3.

RULER LESSONS EARNED:
  - A STATEMENT WINDOW PINS AT THE BAND FLOOR. One contour
    window (of 195) read exactly 4.50 Hz = rmin, 0.2 slots
    from a landing: the mukhda's 2-slot melody spacing owns
    rate/2, BELOW the analysis band, so the estimator pins at
    the edge. e77's exclusion idiom applies: statement
    windows are claimed by the phase-lag ruler, not the
    contour.
  - THE DOUBLED SIGNAL SHOWS AN ATTACK TWICE. The sam strike
    at t=0.012 reappeared at 38.388 — its copy at the
    doubled-signal boundary, read one detector hop early, too
    far from its twin for min_sep to merge. Onsets in the
    last 50 ms (where nothing is written) are wrap images.

Open threads: a chakradar whose statements themselves
breathe (mukhda on its own local grid); bells tolling ektal
(from vespers); drums playing the full countdown, not just
the landings.

## 2026-09-02 — showcase: "Vespers for the Workshop" (songs/vespers.py)

Second of the operator-requested showcase pieces (first,
"Avartan", still rendering — its entry will land above when
it does). Spirit: the first machines learn to breathe. Era
I's cathedral — PADsynth choir (oh->ah over one loop, the
breath's own fundamental), church bells, grain shimmer, the
FDN room — rebuilt around era V's written interference
(e73/74): a hidden organ of loop-quantized sine pairs split
by EXACT integer bin counts, so the D chord breathes on a
harmonic series of breath — drone 12, D3 24, A3 36, D4 48
cycles/loop = 1:2:3:4. All four rates agree only every
76.8/12 = 6.4 s, and that is when — and only when — a bell
tolls: twelve a loop. D aeolian (the workshop's home key,
which Kafi shares), 76.8 s seamless.

Measured (7/7 rulers): band-envelope spectra crown at bins
24/36/48 EXACTLY through choir + room + master; drone band
crowns at 12; 12 tolls at 6.33..6.47 s spacing; organ sits
-12.8 dB under the rest yet its breath stays legible in the
band envelopes; chroma crowns D at 0.74; width +0.038 above
250 Hz; seam p81.0.

RULER LESSONS EARNED:
  - A WAVEFOLDER BREATHES AT TWICE THE DRIVE RATE. First
    pass: drive = 1.15 + 0.75 sin(bin-12) crowned the drone
    band at bin 24 — the folder's fundamental level is
    non-monotonic in drive, so one drive cycle is two
    loudness cycles. The level must carry the written breath
    (bin-12 amplitude envelope); drive only colors it.
  - SINES ARE LOUDER THAN THEY LOOK. Organ pair amps of
    0.03 measured -1.7 dB against the whole mix: a bare sine
    carries far more rms per unit amplitude than a
    peak-normalized padsynth bed. Scaled x0.33 -> -12.8 dB,
    and the 2:3:4 crowns still passed — the beat geometry
    survives at whisper level, which is the piece's real
    claim.

Open threads: bells tolling a slow theka (12 tolls is a
tintal-and-a-... no — 12 is its own taal, ektal); breath
series through the taraf halo; a piece where the common
period itself drifts.

## 2026-09-02 — session 77: the breathing grid (e77)

Brand-new rhythm: e75's jhala engine with the GRID itself
breathing. rate(t) = 8.333 - 2.5 cos(2 pi t/9.6) strokes/s —
the strum eases 5.8 -> 10.8 -> 5.8 across the loop, stroke
times from inverting the phase integral, mean rate chosen so
phi(9.6) = 80.000000 exactly: the seam-lock survives a tempo
that never stops changing (the accelerating-jhala thread,
closed by making the ramp itself close the loop; e73/74's
breath lineage married to e75/76's strum lineage). 13/13
rulers. Library: ruler.rate_contour (dev_smoke 100 -> 101).

Measured: contour tracks the written rate at median 0.7%,
worst 3.6%; integral of the measured contour = 79.8 strokes
vs 80 written (the census counting could not take, taken by
integration); extremes 5.81/10.79 vs written 5.83/10.83;
uniform-grid control contour flat (x1.027 spread around
8.35); melody readback at the breathing times 1.6c/3.0c;
mastered mix: 23 of 30 drone-clear windows read the stroke
rate directly, all within 5.4% after folding; seam p53.9.

RULER LESSONS EARNED:
  - FLUX_SPECTRUM IS A CLAIM OF STATIONARITY. The breathing
    grid's strongest stroke-band line is at 10.66 Hz — the
    TURNING rate, where the cosine lingers (FM-style edge
    pileup) — 2.3 Hz from the 8.33 mean, which shows no line
    at all. rate_contour (pitch_contour's rhythmic twin:
    short flux windows, zero-padded FFT, parabolic refine) is
    the honest ruler for chirped rhythm.
  - WINDOW WIDTH IS A CLAIM: below ~7 periods of the slowest
    rate the strongest windowed line is often the octave
    (100% errors at 0.6-1.0 s windows; 1.2 s tracks clean).
  - EVERY OUTLIER EARNS A MECHANISM OR THE GATE IS A FUDGE:
    the mastered mix's contour outliers decompose exactly
    into (a) windows holding a written drone strike
    (excluded by design), (b) the da/ra alternation's OWN
    rate/2 sub-line — a 2-stroke-period hand pattern owns
    its subharmonic (e76's hands-decorrelate lesson from the
    other side), and (c) the octave at the slow end. Folded
    and excluded BY MECHANISM, worst residual 5.4%. Also:
    listen above 400 Hz — the master's lowpass tilts flux
    weight toward sung fundamentals; the strum's clock lives
    in the stroke transients.
  - Free regression test: the uniform control re-derived
    e75's construction and read 0.62x crown — the exact e75
    number. Determinism makes old sessions latent controls.

Open threads: BREATH DEPTH as a voice (vary RDEP per cycle —
a slow crescendo of tempo swing; can two simultaneous strums
breathe in counter-phase and read as two contours?); the
melody-rate contour (rate/4 band — does the gat's own
contour read in the melody band?); tihai on the breathing
grid (countdown in breathing time: equal PHASE lags, unequal
clock lags — does the self-similarity ruler need warped
windows?); rate_contour on tabla-like material (real
recordings?); chakradar; one-pitch tihai; flux stillness on
bowed pieces; da/ra sub-line as a deliberate 40-cycle voice.
Carried: gamak on the gat line; other just proportions; Pa-
jitter mechanism; partial-fold-aware chroma; entries as
music; shimmer as tala; ring sharpening; canon at the 4th;
oblique organum; bass window floor (midi 40-44); k=5e4 cliff
law; crack flavors in the bass window; ghost as harmony;
intermodulation forecast; gamak map; jugalbandi;
ruler.note_evidence; jod voices; per-string taraf gain;
passing tones; FD tanpura dyad verify; creep dead-zone edge
map.

Render sent: e77_breathing_grid.ogg.

## 2026-09-02 — session 76: tihai (e76)

Refinement of e75's jhala, landing the long-carried tihai +
gat mukhda thread. Same strum engine (0.12 s grid, 80 slots,
chikari filling every non-melody slot); the last quarter of
the loop replaces the gat with a TIHAI — the mukhda ga-Re-Sa
(53-52-50) struck three times at a 7-slot lag (0.84 s),
arithmetic 62 + 2x7 + 4 = 80: the third phrase's final Sa IS
the sam, the gat's own first stroke of the next loop, struck
harder (amp 1.3) under a written 1.0/1.1/1.2 crescendo.
Tihai arithmetic is a seam-lock in disguise — e75 locked
rates to integer bins; a tihai locks a countdown to one
instant. 16/16 rulers, first run. Library: flux_series made
public (flux_spectrum refactored over it; dev_smoke 99->100).

Measured: gat readback median 1.6c worst 6.8c, tihai 1.9c/
3.3c; ga-band phrase attacks at spacings 0.82-0.84 vs written
0.840; crescendo reads x1.17 then x1.08; sam peak 1.11x the
median gat stroke (the written 1.3 compressed by ringing
tails); melody-band env self-correlation at the phrase lag
r23 0.97 vs control max 0.13, and in the MASTERED mix r23
0.98/control 0.23 — the countdown survives drone, halo and
master; gat crown still bin 20; flux stroke line 8.36 Hz at
0.91x crown (sub-mix) and 0.73x (mastered); seam p32.2.

RULER LESSONS EARNED:
  - SELF-SIMILARITY AT THE LAG is the transient-rhythm ruler:
    flux_spectrum reads stationary rates as lines, but a
    tihai is three events, not a rate — its signature is that
    the melody-band envelope correlates with itself at
    exactly the phrase lag inside the tihai and nowhere else
    in the loop. Windowed correlation on ruler.flux_series /
    band_env, calibrated with in-loop controls.
  - THE HANDS DECORRELATE THE FLUX: the 7-slot phrase lag is
    ODD in the 2-slot da/ra alternation — the lag that aligns
    the melody anti-aligns the chikari hands, and full-band
    flux correlation pays (r23 0.64 two-handed vs 0.81 with
    the alternation removed, measured via a one-hand control
    bus; the melody-band envelope cannot see the chikari and
    reads 0.97 regardless). Band your self-similarity ruler
    to the voice whose repetition you claim, or the
    accompaniment's own pattern algebra leaks in.
  - DESIGN THE CONFOUND AWAY: e75's drone restrikes at +4.8 s
    would have dropped a foreign attack inside phrase 2's
    correlation window. The 12 s plucks ring the whole loop
    anyway — struck once, early (0.96/2.16/3.36), the tihai's
    windows stay clean and the seam improved to p32.
  - Phrase-1's r12 (0.55) is honestly lower than r23 (0.97):
    its window carries the gat's last stroke still ringing
    in-band. A correlation window inherits its past.

Open threads: CHAKRADAR (three tihais of three — does the
self-similarity ruler read the nested lag structure, 3 lines
at T, 3T+phrase?); tihai without a pitch anchor (drum-like:
same phrase on ONE pitch — does the envelope ruler still find
the lag with no ga-band to lean on?); accelerating jhala with
a closing DT ramp (chakradar of grids); flux stillness on the
bowed pieces; da/ra asymmetry as its own 40-cycle line;
breath as tala over the tihai (e74's 2:3:4 under this grid).
Carried: gamak on the gat line; other just proportions; Pa-
jitter mechanism; partial-fold-aware chroma; entries as
music; shimmer as tala; ring sharpening; canon at the 4th;
oblique organum; bass window floor (midi 40-44); k=5e4 cliff
law; crack flavors in the bass window; ghost as harmony;
intermodulation forecast; gamak map; jugalbandi;
ruler.note_evidence; jod voices; per-string taraf gain;
passing tones; FD tanpura dyad verify; creep dead-zone edge
map.

Render sent: e76_tihai.ogg.

## 2026-08-31 — session 75: jhala (e75)

Brand-new texture — the strummed climax of a sitar raga, and
the jhala thread landed. An 0.12 s grid, 80 slots per 9.6 s
loop: a melody pluck every 4th slot (20-note gat over Sa=D)
and chikari strokes on hz(62) filling the rest (da-da-ra hand
alternation — two "strings" a few cents apart, different pick
points). 8.33 strokes/s wall to wall. 13/13 rulers. Library
grew: ruler.flux_spectrum (dev_smoke 98 → 99).

Measured: gat line read back off its own bus at median 2.3c,
worst 6.7c; chikari bus chroma crowns class 2 at 0.79 vs 0.17
runner-up; melody-band accent ratio 1.81 at melody slots;
melody-band envelope spectrum crowns at EXACTLY bin 20 (the
gat cycle, seam-locked); flux spectrum crowns at 2.09 Hz
(written group cycle 2.083) with the stroke line at 8.36 Hz
(written 8.333, 0.3% off) at 0.62x crown and its octave at
16.7; halo -16.1 dB; seam p83.8.

THE RULER LESSON — the strum that cannot be counted hums its
rate. At jhala density onset counting fails from both sides,
and it is a THRESHOLD dilemma, not a tuning problem: at
defaults the solo buses count almost true (chikari exactly
60/60, melody 24/20 with buzz ghosts) but the mastered mix
recalls only 34/80 (masking merges repeated strokes);
sensitize to k=0.7 until the mix recovers (60/80) and that
same setting makes the buses hallucinate (41/20, 71/60 —
jawari buzz reads as re-attacks). No single threshold serves
both sides. The e73 boundary (counter fired by bow jitter
from below) is now completed from above. The honest ruler is
new: ruler.flux_spectrum, the FFT of the spectral-flux
series — counting events fails but the PERIODICITY of the
flux survives masking and buzz alike. Count when sparse; read
the spectrum when dense.

Second lesson — ENERGY-RHYTHM vs ATTACK-RHYTHM are different
quantities. The amplitude envelope cannot see the strum at
all (grid-phase ratio 1.12; ringing tails fill the 120 ms
gaps), and in the mastered mix the melody-band envelope
defects entirely: the drone's sustained 147 Hz floods the
band and its own seam-locked attack lattice (plucks every
1.2 s = 8 cycles/loop) crowns the envelope spectrum at bin 8.
But the flux still crowns at the gat cycle with the stroke
line at 0.83x — six loud drone events cannot outvote eighty
strums in the flux. First failing gate shipped as a reshaped
positive claim: envelope follows energy, flux follows
attacks; pick the ruler for the rhythm you mean.

Open threads: TIHAI over this grid (three repetitions of a
phrase ending on the sam — the flux spectrum should show the
tihai's own comb); gamak on the gat line (the melody is
plain plucks; bend between them); jhala dynamics (real jhala
accelerates — a DT ramp breaks the seam-lock unless the ramp
itself closes the loop: chakradar of grids?); flux_spectrum
on the bowed pieces (does the bow's attack-lessness read as
flux silence? a stillness ruler from the other side); da/ra
asymmetry as a 2-bin line (the chikari alternation is itself
a period-0.24 s pattern — is its 40-cycle line in the flux?).
Carried: breath as tala; other just proportions; Pa- jitter
mechanism; partial-fold-aware chroma; entries as music;
shimmer as tala; ring sharpening; canon at the 4th; oblique
organum; bass window floor (midi 40-44); k=5e4 cliff law;
crack flavors in the bass window; ghost as harmony;
intermodulation forecast; tihai + gat mukhda; gamak map;
chakradar; jugalbandi; ruler.note_evidence; jod voices;
per-string taraf gain; passing tones; FD tanpura dyad verify;
creep dead-zone edge map.

Render sent: e75_jhala.ogg.

## 2026-08-31 — session 74: the breathing raga (e74)

Refinement of e73, completed to the full Kafi hexad: six held
voices (Sa/Re/ga treble bow, Pa-/Dha-/ni- heavy bow, no
tanpura), THREE coincidence bands (440/494/523), three
written beat rates in the harmonic proportion 2:3:4 — 18, 27,
36 integer cycles per loop. The rhythm ratios mirror the
raga's own pitch ratios: the chord breathes a chord. 13/13
rulers, library unchanged.

Measured: envelope spectra crown at EXACTLY bins 18/27/36 in
the sub-mix and the mastered mix; achieved separations hold
the proportion to 0.5% (1.507 : 1.332 : 2.007 vs 3/2, 4/3,
2); still control (all basses retuned onto their lines,
residuals 4-6 mHz) reads 1.6/0.2/1.0 dB against 7.1/5.6/4.8
beating. Band-ownership gate: every claim band contains lines
from its two design owners and nobody else (-35 dB floor) —
no parasitic coincidences in the hexad. Bass funds 1.00 x3.

Boundaries pinned:
  - THE JITTER IS PA-SPECIFIC: Dha- and ni- converge to
    2 mHz in 3-4 iterations; Pa-'s line sign-flips around
    its target and bottoms out ~3x coarser (7 mHz best,
    27-50 mHz typical steps). Two of three bass lines follow
    the command smoothly. The heavy bow has per-note fine
    structure — the jitter map thread now has a face.
  - CHROMA COUNTS PARTIALS, NOT NOTES: the dark basses crown
    h1 but sing a strong h3 that octave-folds a FIFTH UP.
    Class 6 — which nobody sang — outranks the sung ga: it
    is Dha-'s h3 (370 Hz) as a chroma ghost, and Pa-'s h3
    inflates Re's class. Register-blindness thread resolved
    with a mechanism: read chroma with the lattice in hand.

Ruler practice notes: the e73 toolset (best-pick tuning, env
integer-bin crowns, paired still control) scaled from 2 pairs
to 3 without modification; runtime ~5 min for ~27 renders.

Open threads: the breath as TALA (2:3:4 all close every
1.067 s — put a slow melodic cycle over the composite and
the breathing becomes accompaniment); a 5:6:8 or other
just-proportion breath (which proportions read as consonant
RHYTHM?); the Pa- jitter mechanism (mode structure? map
sep(command) finely across the bass window — one note in
three wanders); chroma_uniform with a partial-fold-aware
variant (subtract h3 ghosts via the lattice before folding);
entries as music (this piece builds bottom-up in 1.8 s —
compose longer entry arcs). Carried: shimmer as tala; ring
sharpening; canon at the 4th; oblique organum; bass window
floor (midi 40-44); k=5e4 cliff law; crack flavors in the
bass window; treble window certification; ghost as harmony;
intermodulation forecast; tihai + gat mukhda; jhala; gamak
map; chakradar; jugalbandi; ruler.note_evidence; jod voices;
per-string taraf gain; passing tones; FD tanpura dyad verify;
creep dead-zone edge map.

Render sent: e74_breathing_raga.ogg.

## 2026-08-30 — session 73: the breathing chord (e73)

Brand-new: RHYTHM MADE ONLY OF INTERFERENCE. Four held
voices — Sa and ga on the treble bow, Pa- and ni- on the
heavy bow — form a tetrad with no tanpura (the chord IS the
drone) and no articulation after its entries. Two coincidence
bands (Sa h3/Pa- h4 near 440; ga h3/ni- h4 near 523) carry
two written beat rates in exact 2:3, both chosen as INTEGER
CYCLES PER LOOP (18 and 27 in 9.6 s) so the interference
pattern closes at the seam. 15/15 rulers, dev_smoke 98.

Measured: band A breathes at 1.90 Hz (4.1 dB), band B at
2.83 Hz (3.1 dB), ratio 1.494; one-loop envelope spectra
crown at exactly bins 18 and 27, in the sub-mix AND the
mastered mix — the breathing is seamless by construction.
The still control (same voices, basses retuned ONTO the
melody lines) reads 0.7/0.9 dB: same envelopes, no rhythm.

Boundaries and lessons, each pinned as a gate:
  - THE BOW CANNOT CREEP FROM ZERO: an entry ramping vb
    0 -> 0.085 crosses the dead zone and never locks (fund
    0.000 on both grids); entries must STEP to the certified
    0.085. Found as a CONFOUND — the first probe changed
    attack and grid in one edit and blamed the grid; the
    script's own control unmasked it (native-grid solo Sa
    with step attack: fund 0.52). One variable per probe,
    or the control catches you.
  - THE TUNING KNOB IS NOTE-DEPENDENT: ni-'s line converges
    to 3 mHz in four iterations; Pa-'s jitters in a ~50 mHz
    band under sub-cent command steps (8x coarser floor).
    Iterate with a best-pick, not a formula. (rho was also
    remeasured off e72's value here — treat rho as per-take,
    always.)
  - THE ONSET RULER CANNOT HEAR THIS RHYTHM: beating and
    still chords read the same onset count (34/30) — the
    detector fires on bow jitter, not interference. Almost
    shipped as "31 onsets of written rhythm" until the still
    control read 32. Onset-free rhythm lives in the envelope
    spectrum's integer bins.
  - partial_freq hardened: the parabolic vertex offset is
    now clamped to half a bin — on a silent band it returned
    confident absurdities (a "line" at 372 Hz from a
    434-447 Hz search).

Open threads: more breath voices (the 2:3 wants a third band
— Re/Dha- at 4:5? a full breathing raga); breath TALA (rates
that sum to a cycle grid — can the 2:3 carry a slow teental
skeleton?); the Pa- jitter (why does one note's line wander
under micro-commands where another's is smooth? mode
structure? worth a map over the bass window); entries as
music (the staggered chord build is expressive — compose
entry orders); creep-attack physics (WHERE is the dead
zone's edge? map minimum lockable vb step). Carried: shimmer
as rhythm/tala; shimmer counterpoint (partly landed here);
away-retune modulation; ring sharpening; rho at other notes
(partly: ni- -2c); canon at the 4th; oblique organum; bass
window floor; k=5e4 cliff law; chroma register-blindness;
crack flavors in the bass window; treble window
certification; ghost as harmony; intermodulation forecast;
tihai + gat mukhda; jhala; gamak map; chakradar; jugalbandi;
ruler.note_evidence; jod voices; per-string taraf gain;
passing tones; FD tanpura dyad verify.

Render sent: e73_breathing_chord.ogg.

## 2026-08-30 — session 72: written shimmer (e72)

Refinement of e71: the beat chain, run BACKWARDS. Last cycle
closed prediction (own-bus lines -> mix rate to 0.03 Hz);
this cycle makes the beat rate WRITTEN MATERIAL. 15/15
rulers, dev_smoke 97 (beat_profile short-window clamp).

THE WRITING TOOL. rho (sounded h4 / 4*command of the heavy
bow) is flat to 0.36c across +-10c of command — so the bass
command for any target beat rate r against a measured melody
line is one division: c = (f3 - r)/(4*rho). One-shot writing
carries an ABSOLUTE error (the rho wobble, 0.03-0.16 Hz
across a 0.5-4 Hz ladder): a 4 Hz write lands at 1%, a
0.5 Hz write can miss by 30%. Slow shimmer needs the
TWO-SHOT score: fdbow is deterministic, so render the bass,
measure each segment's achieved separation, correct (~0.2c),
render final — every written rate then lands within 0.05 Hz.

And the score listens to THE TAKE, not a reference: in-piece
the same melody recipe sounds its h3 0.19-0.24 Hz below the
standalone take (context/trajectory history moves the line).
A bass tuned to the reference would miss the slowest written
rate by 25%. Tune to what this take sings.

The piece: "written shimmer" — the melody is ONE note. All
the motion is beat rate, written to double twice: 0.8 ->
1.6 -> 3.2 Hz (reads 0.77/1.62/3.00 in the mastered mix,
ratios 2.11/1.85). Then the melody steps away to ga — no
line pair in the band, shimmer dies (ripple 5.7 -> 0.4 dB)
— and WHILE IT IS AWAY the bass silently retunes to the
melody's own sounded line; the melody comes home to written
stillness (separation 0.04 Hz, ripple 0.4 dB). Chroma: Sa
0.51, Pa- 0.23, everything else <= 0.06 — the whole pitch
story is two classes; the music was the rate. Drone's pa
pluck REMOVED by design (its h4 = 440.0 exactly — a third
line inside the written band). Seam p43, halo -17 dB, both
voices t60 1.72.

Ruler lessons:
  - one-shot error is absolute, not relative: a fixed
    ~0.1 Hz band from the rho wobble. Claim rates as
    absolute error against the tool's band, not percent —
    percent flattered the fast writes and damned the slow
    ones for the same physics.
  - the default beat_profile window is properly blind below
    0.25 Hz, and that blindness IS the stillness ruler: a
    0.08 Hz residual read 4.9 dB of "swell" in a slow-window
    ruler and 0.8 dB in the default — for "no audible beat,"
    use the window that ignores what no listener hears.
  - beat_profile crashed when the window was shorter than
    the detrend (sub-second stillness windows) — clamp the
    trend to half the envelope. A ruler that can only
    measure long claims quietly forbids short ones.
  - gate-calibration re-earned (e68): the probe's 0.5 Hz
    write missed by 0.16, the script's by 0.08 — per-take
    wobble. The failed "floor at 0.5 Hz" gate was the wrong
    claim SHAPE; the absolute-band claim survives both.

Open threads: written shimmer as rhythm (lock the beat rate
to a tala — 3.2 Hz is already a tabla roll; can the shimmer
carry the theka?); shimmer counterpoint (two dyads, two
written rates at once in separate bands); the away-retune as
standard modulation move (retune ANY voice while its partner
is absent — pivot tunings between phrases); ring sharpening
(on FB lift both voices lose friction flattening — does the
tuned pair UN-tune in the release ring? measure); rho at
other bass notes (is 0.36c flatness universal or Pa--local?).
Carried: canon at the 4th; oblique organum full piece; bass
window floor (midi 40-44); k=5e4 cliff law; chroma
register-blindness; crack flavors in the bass window; treble
window certification; ghost as harmony; intermodulation
forecast; tihai + gat mukhda; jhala; gamak map; chakradar;
jugalbandi; ruler.note_evidence; jod voices; per-string
taraf gain; passing tones; FD tanpura dyad verify.

Render sent: e72_written_shimmer.ogg.

## 2026-08-30 — session 71: organum, and the bass window (e71)

Brand-new cycle, two findings braided: the instrument's SECOND
window, and parallel fourths that beat at the rate the strings
choose. 18/18 rulers, dev_smoke 96 (+ruler.partial_freq).

THE BASS WINDOW. e70 showed recipes are per-grid; e71 shows
the grids come in REGISTERS. The certified treble bow
(FB=1e4*vb) simply fails below the phrase — at midi 45/47/48
(N 125-144) it leaves lock 0.01-0.02, the string never
speaks. The bass wants a four-times heavier bow: FB=4e4*vb at
vb~0.10 locks all three (lock 0.74-1.20, fund 0.49-1.00),
with a hard ceiling one step up (k=5e4 at ni-: 0.00/0.000,
total silence). And the voice inside the pocket is DARK: ni-
crowns h1 (fund_presence 1.00) where the treble voice crowns
h2 — a different voice, not a transposed one. Sounded
flattening stays under 3c across the window.

THE BEAT CHAIN, CLOSED. ET fourths beat where melody h3 meets
bass h4 (~440/494/523 Hz). Own-bus sounded lines (new
ruler.partial_freq: parabolic vertex on three log bins,
~0.01 Hz on 5 s windows) predict 0.23/0.60/0.63 Hz; the mix
measures 0.23/0.61/0.61 — three fourths, all within 0.03 Hz.
Score arithmetic |3*hz(Sa)-4*hz(Pa-)| promises 0.50 Hz where
the strings sound 0.23: friction flattening moves the lines,
so predict from the sounded lines, not the written notes.
And the just-intonation control must be tuned by SOUNDED
pitch: re-commanding the bass so its h4 lands on the melody's
h3 collapses 52/47 from 5.4 to 0.5 dB (line residuals
0.07/0.01 Hz). Commanding 3:4 of the score does NOT collapse
it — the bass's own flattening detunes the command.

The piece: "organum" — Sa-Re-ga-Re-Sa on the treble bow, a
second voice in strict parallel fourths below on the heavy
bow. Ninth-century two-part organum from one instrument's two
windows. Every hold sounds its fourth within 6.9c of ET-500,
the bass keeps fund 0.84-1.00 under the melody, both voices
obey the same release law (t60 1.72/1.72 vs design 1.73),
and the chroma says the counterpoint worked: Sa leads 1.6x,
and the bass lifts Pa- into the top four ABOVE the sung ga
without re-keying the mix. Halo -15.0 dB, seam p16.6.

Ruler lessons:
  - a rate window is a claim: beat_profile's default
    min_rate=0.25 sits above the slow fourth's 0.23 Hz beat,
    so the ruler returned the log-envelope's 2ND HARMONIC —
    exactly 2.0x — and the 1.5 s detrend ate the depth
    (3.1 dB shown, 9.0 real). Gates now pin the trap itself:
    the default window MUST read 2x on this mix. Size the
    window to the prediction before trusting the peak.
  - hps_pitch has the wrong grain for beats: its ~0.5c step
    is ~0.4 Hz at 440 Hz — twice the signal being predicted.
    partial_freq reads the line itself and closed the chain.
  - a control is only a control at the SOUNDED pitch: the
    "just intonation" bass commanded at 3:4 kept beating
    (its own flattening detuned it); tuned by measured line,
    the beat died. Same lesson as e65's calibrated depth,
    now on the prediction side.

Open threads: the organum only certified fourths downward —
canon at the 4th is now buildable (two windows, one law);
moving organum with oblique motion (drone-note bass under a
moving melody — when does the beat chain break?); the bass
window's floor (midi 40-44 untested; sub-midi-40 carried);
why k=5e4 is a cliff not a taper (the ceiling wants a law
like e64's); Dha-/ni- barely register in chroma (dark
fundamentals octave-collapse weakly — is chroma_uniform
register-blind and should a bass-aware variant exist?);
crack flavors in the bass window (does the heavy bow crack
darker?). Carried: treble window certification (N=58-77);
ghost as harmony; intermodulation forecast; tihai + gat
mukhda; jhala; gamak map; chakradar; jugalbandi;
ruler.note_evidence; jod voices; per-string taraf gain;
passing tones; FD tanpura dyad verify.

Render sent: e71_organum.ogg.

## 2026-08-30 — session 70: the broken halo (e70)

Refinement marrying e68 and e69: what the sympathetic bank
hears when the voice cracks. 14/14 rulers, library unchanged.

The instrument section (e69's crack, rebuilt sample-exact):
  - the crack rewrites the drive: healthy crowns h2; broken
    crowns h3 with h1/h2 collapsed to <= 6%. And the flavors
    VARY: e66's slam {2,5,7}, e69's hold {3,5}, this piece's
    ghost {3,6} — a crack is a family of states; measure your
    own ghost, always.
  - the halo hears it: isolated-drive A/B reshuffles the
    ledger (agreement 0.38, crown C -> Sa', gains x12.6/x3.4,
    fifth-family x0.2-0.4).
  - the boundary of the forecast, logged: ma gains x3.4 with
    NO lattice address (nearest drive line 31c away, n,m<=8),
    and every coincidence forecast of the gain ledger (v2/v3,
    tol 15/25c) scores <= 0.15. Intermodulation at the
    string's own contact recruits where no coincidence lands
    — v2/v3 rank strings, not what the barrier builds.
  - THE TREBLE WINDOW: fdbow sizes its grid from the phrase's
    HIGHEST note, so one Sa' coarsens the whole take
    (N 96 -> 58) and e69's certified heal dies there (ga
    returns at 0.000 vs 0.69 native). Recipes are PER-GRID;
    the top note silently retunes the instrument. Found when
    a planned Sa'-return piece broke everywhere at once.

The piece: "the ghost duet" — Sa-Re-ga, then the voice cracks
and STAYS broken 2.2 s. This ghost's {3,6} lattice lands 2c
from komal ni's h2 and h4: ni's taraf string gains x1.27 vs
the no-crack control while Re's starves at x0.58 (this flavor
HAS an address — unlike ma's gain in the A/B), and the ghost
sings enough C into the mix that ni is the chroma's SECOND
CLASS (0.15), above the drone's Pa and the sung ga. The crack
composed a note the bow never played. Then the mute, home to
Sa (0.58/0.17), lift at 1.72 s, seam p34.5.

Ruler lessons:
  - the phrase's top note is a hidden global: an f0 anywhere
    in the array resizes the grid EVERYWHERE — when a take
    behaves differently after an "unrelated" edit, diff the
    render prefix first (np.allclose on the first seconds
    found this in one probe).
  - paired controls beat absolute gates for windowed bank
    measurements: the integrator carries the sung past into
    every window, but a control take differing ONLY in the
    gesture cancels it (share-gain crack/ctl).
  - negative results need their own gates: "the forecast
    cannot see this" is a claim (best spearman <= 0.15 across
    both models and tolerances), not a shrug.

Open threads: certify the treble window (re-earn the recipe
grids at N=58-77, or pin N with a stability-aware kappa —
Sa' and the avroha descent wait on it); crack flavors (what
selects {3,5} vs {3,6}? drag depth/timing?); the ghost as
harmony (compose FOR a target ghost class — ni arrived here,
who else is reachable?); intermodulation forecast (model the
contact's sum/difference products — the addressless gains);
organum jor in fourths; tihai + gat mukhda; jhala; gamak map;
dark bow; chakradar; jugalbandi. Carried: ruler.note_evidence;
jod voices; per-string taraf gain; passing tones; canon at
the 4th; FD tanpura dyad verify; sub-midi-40 window.

Render sent: e70_broken_halo.ogg (two passes).

## 2026-08-30 — session 69: the crack and the return (e69)

Brand-new expressive class: a composed BREAK in the bowed
voice — e64's cliff and e66's multiphonic, made playable.
12/12 rulers, dev_smoke 95.

The physics, each claim its own control:
  - THE CRACK IS PRESSURE WITHOUT SPEED: drag the bow to
    vb=0.03 for 0.2 s with FB held at the ratio schedule and
    a certified ga hold falls onto the fundamental-less
    multiphonic (presence 0.12 -> 0.014). The control: the
    same slowdown with FB following the ratio rule is
    unharmed (0.12) — the trigger is the ratio violation,
    not the slowing.
  - the broken state is sticky and deceptive: healthy rms
    (0.137 vs 0.170 sung — a ghost of ga, not a silence),
    still broken 4.6 s later without a gesture (presence
    0.035 at the last hold), and lock_ratio reads it at 10.0
    — MORE locked than the true tone ({5,7}*f0 lands in the
    odd set). fund_presence, promoted to ruler.py this cycle
    (fourth use), is the one that tells the truth.
  - THE MUTE IS THE MEDICINE, NOT THE PAUSE: a bare 0.25 s
    lift + shelf re-attack fails (the string still RINGS its
    multiphonic at t60 1.7 s, and the new bow locks onto what
    it hears: back at 0.000). The same 0.25 s pressing the
    bow at zero speed — friction with vb=0 is a pure damper —
    kills the ring, and the shelf re-attack comes home: ga
    returns at presence 0.69.

The piece: Sa rises to ga; mid-hold the voice cracks (the
pitch never moves — the break is a bow gesture, not a note);
a pressed silence; ga returns on the shelf, falls through Re,
home to Sa, lift into the seam. Holds 2.8c worst, contour
2.4c, t60 1.72, halo -17.2 (the bank rings ga's ghost through
the break), seam p15.5, chroma D > F x1.56 — the
cracked-and-healed note earns second.

Ruler lessons:
  - a probe harness can silently cancel its own trigger: the
    first recovery probe recomputed FB=1e4*vb AFTER dragging
    vb, so force followed the slowdown and nothing broke —
    "chaotic basin edge" was a bug in the probe, not physics
    (fdbow is deterministic; suspect the harness first). The
    fix became the best control in the script.
  - blind spots can be load-bearing in reverse: lock_ratio
    calling the broken state "locked" is exactly what makes
    fund_presence's testimony sharp — pair rulers so each
    covers the other, then CLAIM the disagreement.

Open threads: the crack vocabulary (multiple cracks; crack
depth — partial breaks at shallower drags; the octave-branch
fall as a SECOND distinct break, e64's even-only state, with
its own heal?); mute as ornament (pressed silences as
punctuation in a healthy phrase); v3-forecast the broken
bank feed (the multiphonic's {2,5,7} lattice should light
different taraf strings — measurable); organum jor in
fourths; tihai + gat mukhda; jhala; v2/v3 two-regime
forecast; the Re soft-contact anomaly; gamak map; dark bow;
chakradar; jugalbandi. Carried: ruler.note_evidence; jod
voices; per-string taraf gain; passing tones; canon at the
4th; FD tanpura dyad verify; sub-midi-40 window.

Render sent: e69_the_crack.ogg (two passes).

## 2026-08-30 — session 68: the compressor law becomes the forecast — v3 (e68)

Refinement cycle, closing the thread carried since e64: the
jawari compressor folded into ruler.sympathy_forecast. 18/18
rulers, dev_smoke 94.

The measurement that cracked it — e64's flat-fed phrase driven
at FOUR levels (x0.05..x1.0), jawari off/on, 32 (feed, output)
points:
  - the linear bank is exact superposition (x20 drive -> x20.0
    output). Below a knee the barrier is a bystander (7/8
    strings within 5% of identity at x0.05; Re overshoots 1.41
    — a soft contact can also ADD sizzle). Above it the fed
    are taxed (sung gains <= 0.21) and the light are spared
    (unsung >= 0.58): a per-string limiter.
  - the knee variable is DISPLACEMENT, not speed: at equal
    tap-velocity rms the outputs differ 2.3x across strings,
    because a lower string swings further per unit velocity
    (u ~ v/omega). Scaling the knee by omega drops the fit
    log-residual 0.33 -> 0.25. Law: out = feed *
    (1 + (feed*(200/fs)/K)^q)^(-p), K=0.74, high-end slope
    0.25, fit on the flat A/B only.
  - the structural theorem, demonstrated as a control: a
    frequency-blind compressor CANNOT move a rank — any shared
    monotone map preserves feed order (the a=0 law reproduces
    v2's spearman to the last digit). ALL of v3's rank repair
    lives in the omega term.

The four-ledger test (out-of-sample except flat):
  - v3 rescues what v2 inverts: flat -0.07 -> 0.76, ph62
    -0.07 -> 0.81. e63's F<->C anomaly — the sung-late string
    darkest, the lattice-lit one bright — was the compressor
    all along.
  - the law is a floor, not a crown: worst ledger -0.07 v2 ->
    0.52 v3, but the cost is honest: ph63, which v2 nailed at
    0.98, drops to 0.52 (saturation flattens the fine ranks),
    steady 0.86 -> 0.76. Use v2 when the phrase feeds the bank
    lightly, v3 when it sings the bank's own strings hard.
  - the floor survives a 16x calibration error band (scale
    swept x0.25..x4, worst still 0.52).

The piece: "the climb" — jor up the Kafi lower tetrachord,
Sa-Re-ga-ma, every note a bank string, sung long and hard on
the certified recipe (locks 0.31+, presence 0.09+, holds
3.1c, contour 2.5c, swell 0.988, t60 1.72). v3's out-of-sample
call on its own halo: spearman 0.93, predicted top-2 and
bottom-2 sets both land — and v2 reads the same ledger
upside-down (-0.36). Sing hardest, glow least: the sung
tetrachord's mean measured rank is 6.5/8 and the halo's crown
is c', a string the phrase never touches. The audible result:
a climbing line whose shimmer answers from a fifth above.
Chroma: Sa leads x1.59, top-4 == the sung set.

Ruler lessons:
  - a probe session is not the script: gates set from
    interactive probe numbers failed the script's own
    deterministic render by one spearman swap (0.595 vs 0.52
    on n=8 quantized ranks). Calibrate gates on the shipping
    script's measurements, with margin sized to the ruler's
    granularity — an n=8 spearman moves in steps of ~0.024.
  - the strongest control can be an identity: proving the a=0
    law changes NOTHING (to 1e-9) locates the entire effect in
    the one term that survives — sharper than any degradation
    gate.

Open threads: v3 into the PIECE workflow (predict a phrase's
halo before rendering it — compose FOR a target ledger under
jawari, e63's game with the corrected model); the Re anomaly
at soft contact (gain 1.41 at x0.05 — is the added sizzle a
resonance of the barrier profile?); a two-regime forecast
(v2 below the knee, v3 above — gate on predicted feed level);
organum jor in fourths (e67's thread); tihai + gat mukhda;
jhala; vibrato-defocuses-the-halo; gamak map; dark bow; cliff
as music; chakradar; jugalbandi. Carried: ruler.note_evidence;
jod voices; per-string taraf gain; passing tones; canon at the
4th; FD tanpura dyad verify; sub-midi-40 window.

Render sent: e68_compressor_law.ogg (two passes).

## 2026-08-30 — session 67: double stops — the tempered fifth beats (e67)

Brand-new texture: two strings under one bow. And with it,
temperament made audible and measured. 11/11 rulers.

The physics — a full chain, each link its own ruler:
  - an equal-tempered fifth is 2c narrow of pure, so a bowed
    Sa+Pa dyad BEATS where Sa's h3 meets Pa's h2. Each
    string's SOUNDING pitch measured own-bus (friction-
    flattened -2.7c and -3.2c — per-voice, consistent),
    predicted beat |3fSa - 2fPa| = 0.60 Hz, measured in the
    mix's 440 Hz band envelope: 0.61 Hz at 2.4 dB depth.
    Design -> pitch ruler -> arithmetic -> envelope ruler,
    and the ends agree within 2%.
  - the just-intonation control (Pa = 1.5 Sa exactly) goes
    STILL: depth 2.4 -> 0.3 dB. Its rate reading (0.40 Hz vs
    predicted 0.20) is honestly meaningless — you cannot read
    the rate of a beat that isn't there. The JI claim is
    DEPTH, extending beat_profile's detrending lesson.

The piece: jor in double stops — the Sa-ga-Re-Sa line over a
bowed Sa pedal, both on the certified recipe (shelf attack,
ratio rule), both lifting at 8.5 s. Melody: locks 0.39+,
worst hold 2.8c, contour 2.2c. Pedal: 2.0c worst deviation
over 7.8 s. Dyad readback (e58 practice): both notes found
in every two-note hold at 2.2c worst, the -50c shifted design
refused at 47.8c. Pedal -6.3 dB under the line, halo -15.5,
release 1.71 s, and the pedal does what a pedal does: Sa
x3.15 over the runner-up — the strongest tonal center any
piece has measured.

Ruler lessons:
  - a depth-gated rate: when an oscillation's DEPTH collapses,
    its rate estimate becomes noise — gate the rate claim on
    the depth first, or the negative control will "measure"
    a phantom rate and fail an honest experiment.
  - calibrate gates from the failure they guard against: the
    fundamental-presence gate was set at 0.10 by round-number
    instinct; the slam failure it detects reads 0.000-0.005
    and true tones read 0.09-0.19. The calibrated midpoint is
    0.05 — a bright high-vb hold honestly dips to 0.09, and
    the first run failed a working melody on an uncalibrated
    threshold (probe-first applies to REUSED gates too).

Open threads: dyads elsewhere in the phrase (parallel
motion? organum-style jor in fourths — and the tempered
FOURTH beats at the same 0.5 Hz for Sa over Pa-low); tihai +
gat mukhda; jhala; the compressor into sympathy_forecast;
vibrato-defocus-the-halo; gamak map; dark bow; cliff as
music; chakradar; jugalbandi. Carried: ruler.note_evidence;
jod voices; per-string taraf gain; jhala acceleration;
passing tones; canon at the 4th; FD tanpura dyad verify;
sub-midi-40 window.

Render sent: e67_double_stop.ogg (two passes).

## 2026-08-30 — session 66: the gat — sarangi meets the theka (e66)

Refinement joining the bowed voice (e61-65) to the tabla
vocabulary (e59-60): a vilambit gat in tintal, two avartans,
theka underneath, the sarangi singing a stepwise Kafi line
composed ON the slot grid with shared sam arrivals. The first
ensemble piece where the melody SUSTAINS. 13/13 rulers.

The physics gate — can the bow play in laya? Gat motion means
0.3 s glides, far quicker than e64's certified 0.8 s. Answer:
yes, ALL taken in lock — provided the take enters through the
vb=0.085 shelf. THE ATTACK IS THE RECIPE:
  - slammed flat at vb=0.105 from t=0, the string never finds
    Helmholtz: it plays a fundamental-less multiphonic (lines
    at {2,5,7}*f0) for the ENTIRE take at healthy rms — the
    level rulers never see it, the pitch tracker reads the
    octave, and even lock_ratio is fooled (the multiphonic's
    strong 5f0 lands in the odd set). Fundamental PRESENCE
    (f0 line / strongest line >= 0.1) is the honest slam
    detector; measured 0.000 slammed vs 0.12+ ramped.
  - ramped in over 0.6 s, every downstream hold locks
    (0.40-1.11) and lands within 3c, 0.3 s glides included.

The piece: theka dha dhin dhin dha / dha dhin dhin dha / dha
tin tin ta / ta dhin dhin dha, 33/33 onsets two-sided, khali
bass-hole 0.021 in both avartans, pulse 3.33 Hz on the nose.
Gat line Sa-Re-ga-Re-Sa twice, home a breath BEFORE each sam
and holding through it (worst hold 2.8c, sam arrivals
included); lift at 8.5 rings the wrap. Balance measured:
drums -11.1 dB and taraf -18.3 dB under the voice. Chroma:
the gat's compass {Sa, Re, ga} owns the top-3 with the
orbited Re first, then x2.7 down to the drone's A — the
bowed voice, not the theka, owns the mix's chroma (e60's
{D, A} two-pole claim belongs to drum+drone pieces).

Ruler lessons:
  - lock_ratio has a blind spot: a multiphonic with a strong
    5f0 reads as "odd-rich" and passes. Parity assumes the
    tone is SOME harmonic stack; when the failure mode is
    no-stack-at-all, measure fundamental presence instead.
    Two rulers, two failure modes, keep both.
  - a healthy-rms take can be wrong from t=0: the slammed
    attack sounds at full level for 5.4 s without ever being
    a note. Attack transients deserve their own gate in any
    driven-instrument piece — level and sustain rulers are
    structurally blind to WHICH branch is sounding.

Open threads: tihai + gat (the mukhda arriving via tirakita,
e60's machinery under the bowed line); jhala (double-time
theka, sarangi in eighth-note jod); the compressor into
sympathy_forecast (carried); vibrato-defocuses-the-halo
(carried); gamak map; the dark bow; the cliff exhibit as
music; double stops; chakradar; jugalbandi. Carried:
ruler.note_evidence; jod voices; per-string taraf gain;
jhala acceleration; passing tones; canon at the 4th; FD
tanpura dyad verify; sub-midi-40 window.

Render sent: e66_gat_sarangi.ogg (two passes).

## 2026-08-30 — session 65: andolan — the wobbling bow (e65)

Brand-new expressive class for the bowed voice: slow deep
vibrato on a held note, the andolan a komal note carries in
Kafi. e64 taught that TRANSITIONS throw the string off the
fundamental branch, and vibrato is a continuous transition —
so the cycle opened with physics, not taste. 13/13 rulers.

What the grid measured (steady ga, ratio recipe, lock_ratio):
  - slow andolan keeps the lock at ANY depth tried: 2 Hz at
    +-40c and +-80c hold odd/even 0.66/0.60. The bow
    tolerates a breathing pitch.
  - the vibrato plane has a HOLE, like every playability map
    so far: +-40c at 5 Hz drops lock to 0.08 while +-20c at
    the same rate holds 1.38. Pinned and avoided (e61's
    octave pocket, e64's cliff, now this).
  - ornament_profile reads RATE exactly (worst 0.01 Hz off
    across the grid); DEPTH passes through a consistent
    calibrated attenuation, x0.91-0.92 at 2 Hz across
    20/40/80c — e47's lesson holds for the bow: calibrate
    depth against the same class at the same rate, never
    trust the raw number. Zero-depth control reads 0.1c.

The piece: jor with a breathing ga. Sa rises to komal Ga,
which oscillates +-40c at 2 Hz for 2.6 s — in-phrase readback
1.99 Hz at 36.6c against the calibrated expectation 36.7c —
falls through Re, home to Sa, lift into the seam. Every hold
locked (wobble included, odd/even >= 0.47); the hold ruler
still lands because the andolan's MEDIAN is the note (3.1c
worst); the contour claim compares against the MODULATED
design line (2.3c median). Chroma: Sa leads, the breathing ga
is the honest second pole (D 0.28 > F 0.22 > rest) — claim
shape follows the phrase.

Ruler lessons:
  - an ornament claim is two claims: the SIGNAL claim (rate,
    calibrated depth, measured in the ornament window) and
    the NOTE claim (the hold's median still lands). Both
    passed; conflating them would have gated the wobble
    against the hold tolerance and failed a working ornament.
  - when a piece features a note, the tonal-center gate must
    yield: margin 1.25 under a 2.6 s ga spotlight is the
    phrase working as written, not a broken center. Name the
    second pole instead of forcing the first.

Open threads: gamak (fast+shallow, the 5 Hz hole says the
map needs charting before composing there); andolan on OTHER
notes (Re, Dha); does vibrato defocus the halo? (the forecast
already takes the modulated f0t — predict ga-string lighting
loss vs plain hold, measure); the compressor into
sympathy_forecast (carried from e64); the "dark bow" near-
sine regime; the cliff exhibit as music; sarangi + tabla
(jor -> jhala); double stops; chakradar; jugalbandi.
Carried: ruler.note_evidence; jod voices; per-string taraf
gain; jhala acceleration; passing tones; canon at the 4th;
FD tanpura dyad verify; sub-midi-40 window.

Render sent: e65_andolan.ogg (two passes).

## 2026-08-30 — session 64: the flat halo — composing evenness, finding the compressor (e64)

Refinement of e63's forecast, planned as "compose the flattest
ledger." Three corrections deep. 16/16 rulers, dev_smoke 93.

V2 RECEIVER PHYSICS (zero fitted knobs): fdsym injects force
at x=0.93 and reads VELOCITY at x=0.12, so mode m couples as
|sin(.93 m pi)|*|sin(.12 m pi)| with a velocity factor m*fs —
the fundamental couples at 0.22, m=4 at 0.78: the bank is
built for its upper modes. Lifted e63's ledgers: jawari steady
0.76->0.88, e63 phrase 0.52->0.81, and the e62-phrase residual
collapsed to ONE swap (drop F and C: 0.02 -> 0.94).

THE BOW'S CLIFF (correcting e61): FB=1e3, vb=0.10 sits on a
chaotic multistability edge. One phrase's vb ramp survives it;
e64's first phrase fell onto the even-harmonics-only
double-slip branch at 0.6 s — during a Sa HOLD, no leap — and
hysteresis kept it there for the take. e61-63 survived on
initial conditions. New ruler born of a broken classifier:
"tallest line = 2f0" reads a bright LOCKED tone as octave
(h2 tops the certified profile); regime is periodicity, so
ruler.lock_ratio measures odd/even. Certified recipe: FB =
1e4*vb (Schelleng's wedge scales with bow speed — flat FB at
vb=0.065 sits above the speed-scaled MAXIMUM force and
chokes to rms 0.0000), vb in [0.08, 0.14], stepwise notes,
slow glides. Locks at every hold, worst 3.6c, swell corr
0.975 with FB riding vb.

THE COMPRESSOR (e63's anomaly becomes a law): same flat-fed
phrase, jawari off/on A/B. Linear bank: the four sung strings
rank exactly 1-4 — v2's feed account confirmed on its home
ground. Jawari bank: the sung four sink to mean rank 6.5 and
the ledger CV halves (0.465 -> 0.236). The jawari contact is
a per-string LIMITER: overfed strings work the barrier
hardest and pay the contact tax. e63's "sung F darkest,
lattice C 2nd" was this law, not a glitch. Corollary: the
jawari bank actively flattens its own halo — the instrument
cooperates with the composition.

The piece: "sarva" — Sa ga Re ma Re Sa, the stepwise phrase
an exhaustive v2 search chose to feed all eight strings
(predicted-feed CV 0.091 vs 0.33/0.45 for e62/e63's phrases).
Measured ledger CV 0.236: flattest of the series (e62 0.282,
e63 0.345). Every string lit, none shouting; chroma top-4 ==
the sung classes at 0.65 mass with no pole above x1.05 —
flat bank, flat chroma, and the claim shape follows the
phrase.

Ruler lessons:
  - regime is periodicity, not spectral tilt: a classifier
    that peak-picks calls every bright locked tone an octave.
    Build the ruler from the INVARIANT (even-only vs
    odd+even), not the symptom.
  - a certified operating point is not a certified
    NEIGHBORHOOD: e61 pinned (FB, vb) as a point; phrases
    live on trajectories through it, and the basin boundary
    ran straight between two nearly identical vb ramps. Map
    the shelf, not the point — and put the recipe (FB=1e4*vb)
    in the envelope, not the luck.
  - the driver profile is an operating-point function:
    measured at (1.05e3, 0.105) it was h3-dominant; the
    phrase actually played h2-dominant. For phrase-level
    forecasts, measure the PLAYED profile from the take
    (own-bus), not from a reference note at other settings.
  - a flat-fed probe is a differential instrument: feeding
    everything equally exposed the bank's response law
    (sung-sink/lattice-rise) that uneven phrases entangled
    with their feeds. When a model residual looks like noise,
    design the input that isolates it.

Open threads: put the compressor INTO sympathy_forecast (a
saturating output map fitted on the flat-fed A/B, then
re-test ph62 end-to-end — the F<->C swap should resolve);
lock_ratio as a per-hold assertion in future bowed pieces
(cheap, catches falls); the vb=0.06 near-sine "dark bow"
regime as a timbre (odd/even ~1e4+ at low FB before the
choke); swell range past 0.14 with the ratio rule; the
cliff exhibit as MUSIC (a phrase that deliberately falls to
the octave branch and returns — needs a re-lock recipe);
score->halo for window RATIOS; sarangi + tabla; vibrato;
double stops; chakradar; jugalbandi. Carried: grid-resolution
study of the split-pair beat; ruler.note_evidence; jod
voices; per-string taraf gain; jhala acceleration; passing
tones; canon at the 4th; FD tanpura dyad verify; sub-midi-40
window.

Render sent: e64_flat_halo.ogg (two passes).

## 2026-08-30 — session 63: score->halo forecast — the bridge is the recruiter (e63)

Brand-new tooling: ruler.sympathy_forecast, a forward model
that predicts a sympathetic bank's ledger FROM THE SCORE —
integrate harmonic coincidences (15c tolerance) between the
driver's f0 trajectory and each string's modes, weight by the
driver's MEASURED harmonic profile, and treat the t60-58s bank
as a lossless integrator (early excitation is kept forever, so
whole-phrase rms rewards it — e62's Ga string, sung 1.6 s but
lit last, measures darkest). Also promoted after its third
use: ruler.chroma_uniform. 16/16 rulers, dev_smoke 91.

What the model certified, what it corrected, what it refused:
  - the BRIDGE-LESS bank obeys the lattice forecast: spearman
    0.90 on a steady-note ledger, predicted top-4 set exact
    {Sa, G, Pa, Sa'}. Tolerance is load-bearing (200c: 0.48).
  - e62's attribution FALSIFIED by a controlled A/B: "the bow
    recruits the fifth-family" — no. Same bowed driver, jawari
    off: Pa falls 1.00 -> 0.21 and Sa tops the bank. The
    recruiter is the JAWARI BRIDGE — the bank talks to itself
    (Sa string's h3 sits 1.6c from Pa's h2).
  - a one-knob linear cascade (each string re-radiating a 1/n
    stack through the bridge) CANNOT reproduce the jawari
    ledger: spearman plateaus ~0.6 across three decades of
    coupling. In the cascade's algebra octaves always beat
    fifths (coupling 0.25 vs 0.028); measured jawari puts Pa
    and G ABOVE the octave. Wrong model FORM — jawari is
    intermodulation at a shared bridge, not per-string
    re-radiation. Logged as the falsification it is.
  - under jawari the forecast still calls SETS out-of-sample:
    top-4 overlap 3/4, predicted bottom-2 inside measured
    bottom-3 (fine ranks reshuffle, spearman 0.55).

The composition is the model used in anger: e62's phrase left
B (Dha) rank 7/8 — the string the score fed nothing. e63's
phrase is written FOR it (Sa - Pa - Dha - meend down to Re -
Sa): forecast says B goes bright and C goes darkest; measured
B rank 2/8, C rank 8/8. Composing BY prediction closes the
loop the e62 open thread asked for.

Ruler lessons:
  - a measured harmonic profile beats a spectral guess: 1/n
    put the fundamental on top; the real bow at xb=0.12
    carries h1 at 0.19 of h2. One steady-note FFT fixed the
    driver side of the model — characterize, don't assume.
  - the bridge is NONLINEAR, so drive LEVEL is part of the
    experiment: the raw (un-normalized) bow gave Pa 0.85 and a
    cascade spearman of 0.79; the normalized driver every
    piece actually ships gave 1.00 and 0.64. Two claims
    flipped on level alone. Normalize to the shipped path
    before measuring a nonlinear element.
  - a plateau across three decades of a knob is the
    session-43 smell pointed at MODELS: constant verdict
    under a changing coupling means the form is wrong, not
    the constant. Falsify the form, don't tune it.
  - claim shape follows the phrase: this piece SINGS Pa
    against a Pa drone — chroma top-2 {D 0.24, A 0.20} is a
    two-pole fact, not a failed solo-center claim. e61's "Sa
    is the tonal center" gate belongs to phrases that don't
    sing the fifth.

The piece: jor for the dark string — Sa swells up to Pa, leans
on Dha (B alight at last), falls through a fifth-wide meend to
Re, home to Sa; taraf at -17.9 dB, holds worst 3.5c, contour
1.8c, release 1.72 s, seam p36.

Open threads: a bridge model with the right FORM —
intermodulation products of the SUM at the bridge (f1+-f2
lines feeding strings), one pass, calibrated on the steady
ledger; score->halo forecast for window RATIOS (e62's four-way
taxonomy numbers are exactly ratio-shaped, and response
constants cancel); use the forecast to compose a phrase that
lights the bank EVENLY (flattest ledger); sarangi + tabla (jor
-> jhala with e59/e60 vocabulary); vibrato/andolan on the bow;
double stops; xb brightness sweep; chakradar; layakari;
jugalbandi. Carried: grid-resolution study of the split-pair
beat; ruler.note_evidence; jod voices; per-string taraf gain;
jhala acceleration; (8,15)-family triad misses; passing tones;
pluck angle; canon at the 4th; FD tanpura dyad verify;
sub-midi-40 window.

Render sent: e63_forecast.ogg (two passes).

## 2026-08-30 — session 62: sarangi + taraf — the halo hears the lattice (e62)

Refinement joining e61's bowed voice to the e53/e54 bank: the
full sarangi, whose signature IS its taraf. 14/14 rulers. Two
predictions walked in, one died, one transformed:

DEAD, with parity measured: "a sustained driver out-selects a
plucked one." Bowed x18.9 vs plucked x18.7 on the same bank.
e53's coherence lesson was really LINE-SPECTRUM vs broadband —
fdpluck (t60 7.7 s) is already a line spectrum, and
selectivity saturates there. What the bow actually changes:
its brighter sustained spectrum RECRUITS THE FIFTH-FAMILY —
the Pa string tops the whole bank under bowed drive (1.00 vs
0.25 plucked). Richer halo, not sharper.

TRANSFORMED by its own dark control: "the halo hands off as
the meend moves" became a four-way taxonomy of how a string
lights (Sa-hold vs Ga-hold windows, all own-bus):
    sung      F, the note itself                    x17.3
    crossed   E, brushed by the Sa->Ga glide        x23.2
    lattice   C — NEVER sung, never crossed; Ga's
              h3 sits on C's h2 (fifth-above)       x45.2
    remembered  Sa/high-Sa hold within 2% through
              the Ga hold (t60 58 s designs -0.3dB) x1.0
The intended dark control (C) lit up brightest of all — the
bank hears the harmonic lattice, not the score. The only
honestly dark string is B (x4.6), the one note the phrase
gives nothing to.

Ruler lessons:
  - when the dark control lights up, the taxonomy was too
    small: the ledger surfaced a fourth mechanism (lattice
    recruitment) that the claim design didn't know about.
    Read the FULL bank ledger before writing bars, not only
    the strings the hypothesis mentions.
  - level calibration must follow the actual signal path: the
    halo estimate used raw rms sums but the mix divides by
    the bank PEAK (tnorm) — first run landed -32.2 dB, 0.2 dB
    below its own window. Peak-norm and rms-norm differ by
    the crest factor; calibrate on the path you ship.

The piece: e61's jor, now with its shimmer — the bowed phrase
drives the bank, taraf at -19.8 dB under the voice, every e61
claim re-verified in the new mix (holds 2.6c, contour 2.1c,
release 1.72 s, seam p48, Sa center x2.3).

Render sent: e62_sarangi_taraf.ogg (two passes).

Open threads: the lattice taxonomy suggests a RULER —
given a phrase and a bank, predict each string's lighting
(sung/crossed/lattice/dark) from the score and check the
ledger against prediction (score -> halo forward model);
sarangi + tabla (jor -> jhala); vibrato/andolan; double
stops (dyad ruler); bow position xb brightness sweep;
chakradar; tin rim stroke; layakari; glide DOWN; jugalbandi.
Carried: time-uniform chroma -> ruler if it recurs (2nd use
this session — promote next time it appears); grid-resolution
study; note_evidence; jod voices; per-string taraf gain;
jhala-bus taraf drive; jhala acceleration; (8,15)-family
triad misses; passing tones; pluck angle; meend on two-pol;
canon at the 4th; FD tanpura dyad verify; sub-midi-40 window.

## 2026-08-30 — session 61: sarangi — the first voice that sustains (e61, fdstring.fdbow)

New instrument CLASS: the bowed string. Everything loam played
before this decays from its excitation; fdbow feeds the string
through stick-slip friction at one node (soft curve phi(v) =
sqrt(2a) v exp(-a v^2 + 1/2), |phi| <= 1 so it brackets its
own implicit solve: damped Newton, bisection fallback on
rfree +/- c). f0, bow speed AND bow force all take per-sample
arrays — meend, swells, and lifts are the voice. 11/11 rulers,
dev_smoke 88 green.

The modeling lesson of the cycle: A STOPPED BOW IS NOT A
LIFTED BOW. With vb=0 and force still applied, the friction
curve is a damper parked on the string — release t60 read
0.12 s against a designed 3.45. Lifting means FB -> 0; with
force as an envelope the release reads 3.30 s (4% off design),
and in the piece 1.72 vs 1.73. Force, not motion, is what
lifts.

Playability is a MAP with holes, walked before trusting:
minimum bow force is sharp (FB=50 whispers at 1e-3 of locked;
locked from ~3e2), an octave pocket (double-slip motion) sits
at FB=2e3, vb=0.10 INSIDE the locked region, vb=0.4 at
moderate force never catches (the too-fast airy non-tone), and
FB crescendos SATURATE — pressure adds grip, not level, so
swells ride bow SPEED (measured in the piece: windowed rms vs
designed vb envelope r = 0.997). The locked tone sits -6.9c
flat: friction flattening, the bowed-string classic, measured
not assumed.

Ruler lessons:
  - whole-signal hann chroma weights a MOVING line by where
    the window bump lands: the single pass crowned F/E (the
    Ga/Re holds sit at the signal's center), the doubled copy
    crowned D (the seam does). Same piece, two verdicts,
    neither honest. Fix: time-uniform chroma (mean of
    overlapping short windows). Stationary buses never see
    this; melodies always will — candidate for a ruler
    function if it recurs.
  - the two-pole {D, A} mix claim belongs to drone/theka
    pieces; a SOLO-voice piece redistributes the upper
    classes (Ga/Re holds outweigh the Pa drone). The honest
    solo claim: Sa is the tonal center (top class D at x2.3
    over runner-up, time-uniform).
  - harmonicity of a bright spectrum: the strongest-5 modes
    are harmonics 2..6 (bow at xb=0.12), so require the stack
    CONSECUTIVE, not starting at 1 (misfit 0.4c).
  - raw=True escape from output normalization: level claims
    (minimum bow force, swells) need the scheme's own scale.

The piece: jor. One closed phrase orbit over the tanpura —
Sa swells, meends to komal Ga, falls through Re, returns, and
the bow lifts at 8.5 s so the ring decays into the seam. Holds
worst 2.6c; contour vs written line median 2.1c over 8 s;
voice never drops below 0.69 of its max; seam p34.

Render sent: e61_sarangi.ogg (two passes).

Open threads: sarangi + taraf (drive fdsym from the bowed bus
— a SUSTAINED coherent driver is what e53 said selectivity
wants; should be the strongest halo yet); sarangi + tabla (jor
-> jhala with the e59/e60 vocabulary); vibrato/andolan (f0
wobble on the bow, ornament_profile the ruler); double stops
(two bowed strings, dyad ruler); bow position xb as brightness
knob (measure centroid vs xb); chakradar; tin rim stroke;
layakari; glide DOWN; jugalbandi. Carried: time-uniform chroma
-> ruler if it recurs; grid-resolution study; note_evidence;
jod voices; per-string taraf gain; jhala-bus taraf drive;
jhala acceleration; (8,15)-family triad misses; passing tones;
pluck angle; meend on two-pol; canon at the 4th; FD tanpura
dyad verify; sub-midi-40 window.

## 2026-08-30 — session 60: tihai — the kaida learns to end (e60)

Refinement of e59: kaida DEVELOPMENT, the rhythmic argument.
Four avartans: theme, palta (theme cells rearranged), khali
palta (ke under the ta, bass returning in the last bar), then
the TIHAI — dha at sam, then "tirakita tun dha" three times
with equal two-slot gaps, the third dha landing ON SAM. In a
loop, sam is the wrap: the tihai's landing stroke IS the
theme's opening dha of the next pass, so the cadence
perpetually re-launches the form (e56's across-the-seam
practice, now structural). 8/8 rulers, first run.

Two new rhythmic devices, both measured against design:
  - the grid opened to HALF-slots: tirakita = four te strokes
    at 150 ms. e59's consonant was built for this — a 30 ms
    thud articulates at 6.67 Hz where the 158 ms na would
    smear. Measured: 9/9 inter-onset intervals, worst
    |IOI - 150 ms| = 1 ms.
  - designed SILENCE became a claim: the onset match is now
    two-sided — every designed stroke sounds (67/67 within
    50 ms) AND nothing else does (0 unexplained onsets). The
    tihai's rests are composition, so the ruler checks for
    their absence, not just the strokes' presence.
  - tihai equality: phrase-final dhas at 15.59 / 17.39 /
    19.19 s, gaps exactly 1.800 s, third = the wrap.

Ruler note: matching claims (onset lists, IOIs, equal gaps)
take DESIGN tolerances (grid +/-40-50 ms), not probe-
calibrated bars — calibration is for ratio thresholds where
the false case must be measured. Khali hole (0.015) and pulse
(3.33 Hz, unshaken by paltas, rests and half-slot runs) reuse
their certified bars. Poles {D, A} still carried by drum +
drone. No library change, dev_smoke not required.

Render sent: e60_tihai.ogg (two passes — listen for the tihai
folding into the theme's return).

Open threads: chakradar (a tihai OF tihais — the phrase itself
contains three dhas, 9 landings); tin as a true rim stroke
(ringing but bass-less, distinct from ta=na); tun + meend
(center strike on a gliding drum — Pa that bends); layakari on
the gat (e58 thread); glide DOWN; kaida theme with MELODY
answering (jugalbandi: e58 gat phrases traded against e60
paltas). Carried: grid-resolution study of the split-pair
beat; ruler.note_evidence; jod voices; per-string taraf gain;
jhala-bus taraf drive; jhala acceleration; (8,15)-family triad
misses; passing tones; pluck angle; meend on two-pol; canon at
the 4th; FD tanpura dyad verify; sub-midi-40 window.

## 2026-08-30 — session 59: bols — the drum learns its consonants (e59, ruler.decay_t60)

New idea: strike FAMILIES on the e55 membrane — the tabla's
vocabulary as physics. Same drum, different touch: na (rim,
full stack), tun (center), te (closed, sig0=200), ke (muted
bayan, sig0=45). Composed into a kaida — dha dha te te / dha
dha tun na (x2) / khali with ke under ta / bass returning into
sam. 12/12 rulers, dev_smoke 87 green.

The headline measurement: THE DRUM TRANSPOSES UP A FIFTH AT
ITS CENTER. tun's {2,4,6}f0 family collapses ~25,000x while
{3,5}f0 remains; the strongest surviving mode is 221.7 Hz ~ A3
(-4c via mode_freqs) against na's 147.7 ~ D3 (+10c). One drum:
Sa at the rim, Pa at the middle — and the mix's D/A poles are
now carried by the treble drum itself, not just drone tuning.
Mechanism separated by CONTROLS, not assumed: on the uniform
drum, center strike keeps the fund (0.84 of power) and kills
(1,1) to 0.0000 — strike-position symmetry selects m=0, the
Bessel textbook. But the LOADED fund also dies at center
(9e-6) where symmetry says it should survive — the syahi has
pushed the fundamental out into the annulus. Two mechanisms,
one ledger each.

Ruler lessons:
  - e55's khali filter lesson re-earned on a new claim: a
    narrowband recursive filter rings for ~1/bandwidth, and an
    order-4 filtfilt 30 Hz wide reads ~140 ms for ANY faster
    decay — te's t60 appeared IMMUNE to sig0 (100 -> 400 gave
    0.137 -> 0.142 s: constant verdict under changing input =
    broken ruler, measuring itself). decay_t60 now does
    memoryless windowed-FFT band power; synthetics read exact
    (500 -> 500.0 ms, 30 -> 30.0 ms).
  - a band can be EMPTY: 30 ms windows put bins 33 Hz apart,
    and [135,165] holds none — the envelope was pure noise
    floor and the fit returned garbage with a straight face.
    decay_t60 guards by falling back to the nearest bin to the
    band center. Check what your selection actually selected.
  - the sustain ledger read the wrong instrument: open/closed
    contrast measured on the full drums bus was really the
    BAYAN's 137 Hz tail under every dha (0.011 wherever ge
    rang, ~0 elsewhere). Voiced-na treble lives entirely
    inside 160 ms, so the piece claim moved to the treble bus
    with windows inside the first 120 ms — 9 orders of
    magnitude of split (te 4e-12, open 5e-3).
  - design premises die in probe: te-by-sig0 barely moved the
    fund t60 at sig0=50 because syahi damping (sig_s=60)
    already dominates the annulus modes' decay; sig0=200 is
    what beats it (31 ms).

Verdicts: even-family collapse 25,825x; uniform control 0.84 /
0.0000 / 0.49; loaded-fund-at-center 9e-6; poles D3+10c and
A3-4c; t60 na 158 / tun 146 / te 30 ms; ke/ge sustained bass
0.0106; kaida sustain split te 4e-12 vs open 4.9e-3; 32/32
onsets; pulse 3.33 Hz; khali hole 0.015; seam p39.2; mix poles
{D, A}.

Render sent: e59_bols.ogg (two passes of the 9.6 s kaida).

Open threads: dha/dhin as COMBINED voiced strokes is done, but
the bol set wants tin (rim near edge, ringing but bass-less
treble in khali — currently ta = na) and tirakita (te-family
double-strokes at half-slot subdivision — needs the grid to go
to SUB/2); kaida development (theme -> paltas -> tihai to
sam); tun + meend (center strike on a GLIDING drum — Pa that
bends); layakari on the gat (e58 thread, still open); glide
DOWN. Carried: bols-as-families now exists — retire that
thread; grid-resolution study of the split-pair beat;
ruler.note_evidence; jod voices; per-string taraf gain;
jhala-bus taraf drive; jhala acceleration; (8,15)-family
triad misses; passing tones; pluck angle; meend on two-pol;
canon at the 4th; FD tanpura dyad verify; sub-midi-40 window.

## 2026-08-30 — session 58: antara — the gat learns its second half (e58)

Refinement of e57's gat, the LOG's first open thread. The
piece grows to FOUR avartans (19.2 s): sthayi twice, then a
mukhda climb (G-A-B-C across the old rest bar) lifts into the
antara — upper tetrachord, taar Sa held at the third sam,
Ga' touched above it, full-ladder descent home. The bayan's
glide answer moves to the final bar so the whole form funnels
into ONE sam. 13/13 rulers.

Negative result, logged with its physics: the planned claim
"the antara STRIKES the string the sthayi only whispered to"
died in probe — an octave-below drive contains EVERY harmonic
of the upper string, so octave sympathy is nearly lossless
(struck/whispered x1.31 on the 62-bus vs unplayed controls at
x1.06-1.36; no honest bar fits between). The tanpura's trick
is not merely present, it is efficient. Register claims moved
to the melody bus, where the contrast is real (x3.6). Also
observed, below claim-worthy margin: taar-Sa became the
whole-piece loudest string (x1.03 over Pa — coin flip, so the
e57 whole-piece poles claim was DROPPED, not gamed; opening
Sa-family claim kept at its x3.9 cliff).

Ruler lessons:
  - e57's head-window lesson, sharpened into its real cause:
    fdpluck's played-string t60 ~ 7.7 s means the 0.25 s
    ring-over is a SECOND NOTE at full amplitude, not a fading
    ghost. Every note head honestly holds two pitches; there
    is NO clean window inside a 0.3 s slot (tail ends +0.25,
    next attack +0.30, window 0.22 wide). Single-pitch HPS per
    window is a register-weighted coin flip — e57's low octave
    always won it, the antara's B/C/D/E cluster flipped (a
    1-slot Ga' between two taar-Sa notes read its neighbours:
    both contaminants AGREE and outvote any median).
  - the fix is to ask the polyphonic question: dyad_pitches
    per note head — "is the designed pitch one of the two
    sounding?" — 46/46 within 2.7 cents.
  - negative controls must respect the grid: a shifted-design
    control at -86c falsely matches the previous note wherever
    the line steps a semitone (B under C); -50c is maximally
    far from the chromatic grid and can never match. Measured:
    best false match 39.5c, ruler says no.
  - contour stays the right ruler for LONG-SPAN statistics
    (dwell 5.5 s Sa vs 2.5 s Pa; register frac >=240 Hz 0.17
    sthayi vs 0.63 antara) — per-frame flips wash out over
    hundreds of frames. Match the ruler to the span.

Verdicts: dyad readback 46/46 worst 2.7c, control refuses at
39.5c; dwell argmax Sa across both octaves; register split
0.17/0.63 (bars 0.30/0.45); opening halo {50, 55, 62} gap
x3.9; halo -20.1 dB; theka 64/64, pulse 3.33 Hz; khali hole
0.011 across all four quarters; glide answer 500c rising to
-3c of Sa at the single sam; seam p6.3; mix poles {D, A}.
No library change, dev_smoke not required.

Render sent: e58_antara.ogg (two loop passes, 76.8 s).

Open threads: layakari (double-time sthayi over the same
theka — the remaining gat-development move); glide DOWN
(release after pressure); bols as strike families (tin = rim,
ke = muted); grid-resolution study of the split-pair beat;
dyad-per-note-head could graduate into ruler.note_evidence if
a third melody piece wants it; sthayi/antara as call-response
between TWO string voices (jod?). Carried: per-string taraf
gain; jhala-bus taraf drive; per-string readout pan; jhala
acceleration; bol patterns; (8,15)-family triad misses;
passing tones; pluck angle; meend on two-pol; canon at the
4th; FD tanpura dyad verify; sub-midi-40 window.

## 2026-08-30 — session 57: the gat — the arc arrives (e57, ensemble)

The banked destination, new-idea cycle: melody, drone, taraf
halo, and theka TOGETHER for the first time — every voice a
certified construct playing inside its measured contract.
Teental, two avartans per 9.6 s loop, Kafi in D. Avartan 1
states the sthayi (21 fdpluck notes on the matra grid, Sa held
at sam); avartan 2 answers — the melody rests after khali and
the bayan glides a perfect fourth into sam (e56's gesture as
STRUCTURE: call and answer between hand and drum). The taraf
bank is driven by the melody bus only (e53: driver coherence
determines selectivity — the drums would kick every string
alike). Assembly is not exemption: every claim re-measured
per-bus in situ, 12/12.

Ruler lessons:
  - a 2-sample median is a mean: 1-slot notes left only 2
    contour windows inside the strict note interior, and the
    previous pluck's 0.25 s ring-over pulled the two A-after-B
    notes to a phantom +103 cents (exactly halfway to B).
    Measure notes at the HEAD (first 0.26 s, >=3 windows);
    the notes were never wrong, the statistic was.
  - the dwell tie was a DESIGN bug the ruler caught: the first
    sthayi draft gave Sa and G 1.8 s each and ring-over broke
    the tie toward G (dwell argmax 5, mix poles {G, A}). One
    phrase recomposed (B-A falling home to Sa) restored the
    designed hierarchy Sa 2.4 > Pa 1.8 > G 1.2 — and the mix
    poles snapped back to {D, A}. Composition claims need
    MARGINS, not ties.
  - chroma is the wrong ruler for a jawari halo: the bridge's
    whole job is pouring energy up the ladder, and Sa's h5
    lands on F# (734 Hz) — harmonic color read as a scale
    violation — while any band tight enough to exclude h5
    makes "halo is Kafi" vacuous (the bank IS Kafi). Ask which
    STRINGS ring, not which classes shine.
  - whole-piece taraf selectivity is honestly flat (x1.28 vs
    e53's x12.7): a gat visits every class and t60~58 s never
    forgets — over a composition the halo becomes a reverb
    tuned to the raga. Selectivity lives in WINDOWS: during
    the opening sam hold (memory still empty) the top-3
    strings are Sa, high Sa, and G at a 3.9x cliff over 4th.
  - the ledger gem: the loudest opening string (and 2nd over
    the whole piece) is high-Sa midi 62 — a string the melody
    NEVER PLAYS, fed entirely by Sa's h2. Octave sympathy, the
    tanpura's trick, emerging unprompted; G rides its h3 on
    Sa's h4 (588 vs 587.2 Hz), e53's shared-partial sympathy
    in situ.

Verdicts (all own-bus): 21/21 notes read back worst 2.0 cents;
dwell argmax Sa (2.3 s); opening halo top-3 {50, 55, 62} gap
x3.9 (bar 2.0); whole-piece halo poles Sa/Pa; halo -19.2 dB
under melody; theka 32/32 slots, pulse 3.33 Hz, khali hole
0.011; the drum's answer rises 500 cents while the melody
rests and arrives -3 cents from Sa at sam; seam p8.8; mix
pulse 3.33 Hz; mix poles {D, A}. No library change, dev_smoke
not required.

Render sent: e57_gat.ogg (two loop passes).

Open threads: the gat wants DEVELOPMENT — an antara (second
melody in the upper tetrachord, high-Sa territory the halo
already loves), or layakari (double-time sthayi over the same
theka); glide DOWN (release after pressure); bols as strike
families (tin = rim, ke = muted); grid-resolution study of the
split-pair beat; windowed halo selectivity could become a
ruler (ruler.window_rank?) if a third piece needs it. Carried:
per-string taraf gain; jhala-bus taraf drive; per-string
readout pan; jhala acceleration; bol patterns; (8,15)-family
triad misses; passing tones; pluck angle; meend on two-pol;
canon at the 4th; FD tanpura dyad verify; sub-midi-40 window.

## 2026-08-30 — session 56: bayan glide — meend comes to the drum (e56, fddrum f1-trajectory, ruler.partial_track)

Refinement cycle on e55's membrane: the bayan's palm-pressure
pitch bend, the tabla's most vocal gesture. Implementation is
fdpluck's meend trick transplanted — pitch lives in one
coefficient (lam2 per step), so f1 may now be a per-sample
array and time-varying tension costs one multiply. Because
every mode scales with f1 on a fixed grid, the WHOLE STACK
bends as one voice — measured, not assumed: fund/f1 ratio
0.5199 at rest vs 0.5204 pressed (0.09% apart).

New ruler: partial_track (one spectral peak followed through
time, hann windows, parabolic refinement). pitch_contour's HPS
is the wrong tool for a drum — sparse stack, low fundamental —
but the gliding mode is loud and alone in its band. Keep the
band tight: the tracker follows the strongest thing you let it
see.

Ruler lessons:
  - the static CONTROL failed before the glide did: an unbent
    drum tracked +/-40 cents early in its ring. Real physics,
    not tracker noise — the staircase-split degenerate pair
    (~0.5 Hz apart) BEATS, and the apparent single peak wobbles
    at beat rate until one member decays. The median rides
    through it; matching statistics between claim and control
    (both median) made the comparison honest.
  - design-vs-measured on a trajectory wants the RATIO design
    (f(t)/f(t0) vs f1(t)/f1(t0)) so the static calibration
    (fund = 0.52 * f1) carries no error into the glide claim.

Verdicts: glide follows design at 5.0 cents median across the
ramp; lands -0 cents from D2 after 503 cents of travel (a
perfect fourth, A1 -> Sa); static control median 6.1 cents;
piece glide read on its own ge bus ACROSS the loop seam (500
cents risen, arriving -3 cents from Sa at the wrap). Teental
keeps all its e55 verdicts: 32/32 slots (the na keeps time
through the glide), pulse 3.33 Hz, khali hole 0.011, seam
p34.7, poles {D, A} — the bayan lives on A and arrives on D.
dev_smoke 85 green.

Render sent: e56_bayan_glide.ogg (two loop passes).

Open threads: the full GAT — melody + theka + taraf halo, the
arc's destination, now unblocked (every element exists:
fdpluck melody, fdpluck2 drone, fdsym+jawari halo, tuned
na/ge, glide bayan); glide DOWN (release after pressure — the
classic dha-glide releases); bols as strike families (tin =
rim, ke = muted); grid-resolution study of the split-pair beat
(N up -> split down — is the beat a lattice artifact or a
voicing?). Carried: per-string taraf gain; jhala-bus taraf
drive; per-string readout pan; jhala acceleration; bol
patterns; (8,15)-family triad misses; passing tones; pluck
angle; meend on two-pol; canon at the 4th; FD tanpura dyad
verify; sub-midi-40 window.

## 2026-08-30 — session 55: syahi — the drum that learned to sing Sa (e55, loam/membrane.py, ruler.mode_freqs/mode_misfit)

New instrument CLASS: the FD family's 2D member. membrane.py
runs an explicit circular-membrane lattice (cartesian grid,
disc mask) with a syahi — a mass-loaded center patch — plus
sig_s (lossy loading) and a displacement readout. The physics
target was Raman 1920: a uniform membrane's modes sit at
Bessel ratios (no harmonic comb — WHY a bare drum has no
pitch), and the tabla's syahi pulls the first five modes onto
integers. Both halves measured: the uniform lattice matches
four Bessel ratios to 0.41% (and has NO mode near 2*f1 — the
inharmonicity is the control), the loaded drum lands stack
(2,3,4,5,6) at 7.3 cents vs the uniform's best 35.7. The sweep
under the honest ruler rediscovered the real instrument's
proportions unprompted: syahi radius 0.45 of the head, strike
just past its edge — and moved the optimum from load 32 to 40
(session-43 rule: new ruler, re-sweep; the old optimum was the
old ruler's opinion).

A session of rulers eating their own cooking:
  - comb_fraction born AND retired here: power-on-best-comb
    scored the drum 0.80, then 0.37 when the readout changed.
    A power-weighted verdict answers to the PICKUP (velocity
    buys mode k a factor k^2), not the drum. Its replacement
    mode_misfit fits integer stacks to mode FREQUENCIES —
    positions don't move with readout, only weights do — with
    GCD canonicalization ((4,6,8,10) IS (2,3,4,5)).
  - invariance means positions, not selections: a strongest-k
    cut seats different modes under different pickups; demand
    every claimed mode has a matching PEAK in the other
    pickup, not that two top-k lists agree.
  - mode_freqs merge needed a 20 dB link guard: a carpet of
    tiny peaks chain-merged two real modes into one blob — in
    one pickup and not the other.
  - the khali hole measurement burned TWO filters before the
    truth: an order-2 skirt at 120 Hz read the treble na (its
    147.8 Hz fundamental only ~5 dB down) as 'bass'; the
    order-6 replacement RANG — its own impulse response,
    kicked by every attack, floored every slot. FFT band power
    per window has no memory. Constant verdict under changing
    input = broken ruler, not stubborn piece.
  - and then the verdict was REAL: the drum genuinely rang at
    71.4 Hz, -1 dB re: the fundamental — a mode BELOW the
    'lowest', hidden under every fmin. The syahi as modeled is
    a heavy nearly-decoupled plug with its own slow internal
    mode. Real syahi is LOSSY (gum + iron filings), not just
    heavy: sig_s damps inside the patch (t60 scan 0/20/60 —
    20 kills the plug x205 with the stack intact; the piece
    voice uses 60 because the khali window starts at 80 ms).
    Three rulers were blamed for what the instrument was
    honestly saying. The piece debugged the instrument.

The piece: teental theka, two avartans per 9.6 s loop — na
(twelfth-root D3 +10c, overtones D-A-D-F#) and ge (modes on
D1/A1), the stroke entering khali palm-damped (the real
gesture). Own-bus: 32/32 slots, pulse 3.33 Hz designed and
measured, khali/bhari sustained bass 0.010, seam p34.6, poles
{D, A} — a TUNED drum feeds the tonic. dev_smoke 84 green
(membrane Bessel + misfit checks; wall time inflated ~8x this
run by external CPU load — the operator's game, not the code).

Render sent: e55_syahi.ogg (two loop passes).

Open threads: bayan pitch glide (palm pressure = time-varying
rho or tension — meend for drums); distinct bols (tin = rim
strike, ke = muted slap: strike position/damp families the
mode ledger can classify); the full GAT — melody + theka + 
taraf together, the arc's destination; grid-resolution study
of staircase mode splitting (N=45 splits pairs ~4%); the
canonical drum's plug mode sits near 36 Hz — worth a listen
check on big systems before it carries a piece. Carried:
per-string taraf gain; jhala-bus taraf drive; per-string
readout pan; jhala acceleration; bol patterns; (8,15)-family
triad misses; passing tones; pluck angle; meend on two-pol;
canon at the 4th; FD tanpura dyad verify; sub-midi-40 window.

## 2026-08-30 — session 54: jawari taraf — the halo learns to shimmer (e54, fdsym jawari + gain)

Refinement cycle on session 53's bank: the taraf get their own
bridge. fdpluck's SAV parabolic contact, vectorized across the
(S, nbz) bank, plus one new knob with a physics argument behind
it: `gain`, scaling the drive FORCE. Estimated before probing,
confirmed by the sweep: a driven sympathetic string reaches
displacements ~1000x smaller than a plucked one (velocity bus
rms / 2*pi*f ~ 1e-6 vs pluck_m 1.6e-3), so at audio force it
NEVER touches the played string's barrier. gain lifts it into
contact — and because the contact is the model's only
nonlinearity, gain is VOICING, not level: it sets wrap depth,
which sets how much energy climbs the partial ladder.

Ruler lessons:
  - the engagement null is a strong control shape: below the
    knee (gain 100) the jawari spectrum is IDENTICAL to plain
    (high-band ratio 1.000 +/- 0.05) — the barrier is provably
    out of reach, not merely quiet. Above (gain 5000): x161
    high-band on the phrase-driven bank. The knee measured
    between 100 and 1000.
  - BLOOM on an unplucked string: the jawari taraf's high band
    climbs for 1.25 s before peaking (window 5) while plain
    peaks in window 1 and decays — the e41 tanpura signature,
    now arriving through the bridge of a string nobody plucked.
    Energy climbs the ladder; a filter could only shave it.
  - selectivity survives the nonlinearity: unison/semitone
    x9.4 with jawari (x12.7 plain, bar 6.0) — the contact
    spreads some energy but the resonance verdict stands.
  - zero-drive silence exact with contact enabled (eta=0 ->
    g=0; the SAV force literally cannot fire on a still
    string).
  - carried STRUCT_BAR worry answered for this content: hps
    reads a jawari taraf at 2.6 cents, dyad on two jawari
    buses worst 4.1 cents. The shimmer is loud but it is
    HARMONIC — it lands on the comb, not between its teeth.

The piece: e53's Kafi phrase, same 8-string bank, jawari at
gain 5000 — and the A/B is a ruler, not a vibe: halo centroid
1371 Hz vs the plain bank's 573 Hz on the SAME drive (x2.39).
Halo at -16.9 dB under the melody, top-3 chroma all Kafi,
melody reads at 0.7 cents, seam p4.8, poles {D, A}. 12/12
first run — probe-first calibration is cheaper than
render-and-retry. dev_smoke 82 green (new jawari check).

Render sent: e54_jawari_taraf.ogg (two loop passes).

Open threads: gain is per-BANK but real taraf voicing varies
per string — per-string gain array (bass taraf worked harder)?
jhala-bus drive (now doubly interesting: does the shimmer
survive broadband strikes, or wash?); per-string readout pan
at distinct nodes. Carried: jhala acceleration; bol patterns;
(8,15)-family triad misses; passing tones; pluck angle; meend
on two-pol; canon at the 4th; FD tanpura dyad verify;
sub-midi-40 window.

## 2026-08-30 — session 53: taraf — strings nobody plucks (e53, fdstring.fdsym)

The oldest banked thread, from the tanpura sessions:
SYMPATHETIC strings. New library piece fdstring.fdsym — a bank
of S undisturbed FD string lattices (vectorized (S, N+1) on a
shared grid), zero initial state, forced at a shared bridge
node (0.93) by an external drive signal, sig0=0.12 for a ~58 s
taraf ring. buses=True returns the RAW per-string outputs —
deliberately unnormalized, because normalization would erase
exactly the ratios the rulers measure.

Physics, measured on own buses before any music:
  - selectivity: driven by a sustained fdpluck at its own
    pitch, the unison taraf outsings the semitone string x12.7;
    retune the DRIVE a semitone and the pair inverts (x48.2 the
    other way) — the same measurement can say no.
  - DRIVER COHERENCE DETERMINES SELECTIVITY: the first probe
    used a KS pluck (t60 0.35) as drive and got only x2.9 — a
    broadband attack kicks EVERY string; kicks under sig0=0.12
    barely fade, so the transient's democracy persists. The
    sustained driver's line spectrum is what selects. (This is
    why real sitar taraf shimmer follows the melody, not the
    strum noise.)
  - cross-tuning sympathy: the taraf a fifth BELOW the drive
    answers x14.0 over the semitone string — through the shared
    partial (its h3 == drive's h2 at 440 Hz), and with the
    jawari-bright driver it rings x1.10 LOUDER than the unison
    string. Sympathy follows the exciter's spectrum, not the
    score. Thresholds >=6.0 calibrated between the measured
    false case (x2.9, KS driver) and true cases (12.7/14.0).
  - memory: kicked by a pluck that decays to 1.2e-15 RMS, the
    bank still holds 0.77 of its early RMS seconds later.
  - silence: zero drive in, bank peak exactly 0.0.

The piece: a slow 9.6 s Kafi phrase (fdpluck, 7 notes, Sa-Ga-
Re-Sa Pa-Dha Ga) whose own bus drives an 8-string Kafi-tuned
taraf bank (50..62); the halo fanned across the stereo field
under one shared norm (bus ratios preserved), over the two-pol
drone. First render FAILED two rulers: peak-normalized halo
sat +8.5 dB ABOVE the melody, loud enough that taraf E
displaced A in the mix poles. One calibrated gain (0.041,
-14.0 dB) fixed both — a halo is a level claim, and the ruler
caught it. Final: halo chroma top-3 all Kafi, melody reads
back worst 0.7 cents, dwell on Sa 2.9 s, seam p20.2, poles
{D, A}. dev_smoke 81 checks green (new fdsym resonance check:
sine-driven unison vs semitone >5x).

Render sent: e53_taraf.ogg (two loop passes).

Open threads: taraf + jawari — give the bank its own SAV
bridge contact so the halo shimmers (and re-calibrate
STRUCT_BAR on that content, two threads meet); drive the bank
from the JHALA bus (fast strikes = broadband — does the halo
smear into wash, and is there a chikari-rate sweet spot?);
per-string readout pan captured at distinct nodes instead of
shared-norm fanning. Carried: jhala acceleration; bol
patterns; (8,15)-family triad misses; passing tones; pluck
angle; meend on two-pol; canon at the 4th; FD tanpura dyad
verify; sub-midi-40 window.

## 2026-08-30 — session 52: jhala — the raga arc reaches its fast texture (e52, ruler.accent_profile)

Two open threads answered as one: jhala (the arc's climactic
register after alap/gamak/jor) IS an accent hierarchy on a fast
grid, so it ships with the accent ruler it needs. 48 slots at
6.67 Hz: a 12-note Kafi line (fdpluck, one note per 4-slot
group, double Sa at the cadence so dwell has a margin, not a
tie) ringing over chikari strikes — high Sa + high Pa plucks —
on every subdivision between. Over the two-pol drone; brightest
render of the arc (centroid 865 Hz, the rest sit 2.5-2.9 kHz).

New ruler: accent_profile (per-onset accent = attack-window
peak MINUS pre-onset-window peak, floored at zero). Lessons,
each measured before believed:
  - raw attack PEAK inherits ring-over PRESENCE, not just
    accumulation: a 0.9-amp melody tail put near-melody-size
    peaks in every chikari slot it crossed, and the hierarchy
    read x1.4 no matter how quiet the chikari got. The
    adjacent-window difference cancels what rings through both
    and keeps what the strike ADDS: hierarchy x20.1 vs control
    x0.99.
  - a control with SILENT melody slots is not 'no hierarchy':
    a hole every 4th slot is itself a period-4 signature (x18
    in the accent spectrum, stronger than the real piece's
    x11). Equal strikes everywhere is the honest null.
  - thresholds sit at log-midpoints of measured false/true:
    hierarchy >=3.0 (0.99 vs 20.1), grouping >=4.0 at bin 12
    (control's best bin x2.3 vs x11.0).

Own-bus verdicts: 48/48 slots strike within 50 ms (doubled
signal + k%NP fold, the e49 practice), pulse 6.68/6.67 Hz and
6.73 in the full mix, every melody note within 9.8 cents
(hps_pitch under a 400 Hz fence — chikari live above it), line
lives on Sa (1.6 s dwell), seam p30.4, poles {D, A}.

Render sent: e52_jhala.ogg (two loop passes).

Open threads: acceleration — real jhala speeds up; a tempo-ramp
loop needs the seam story rethought (the grid wraps but the
period doesn't). Bol patterns (da-ra-da-ra vs da-da-ra):
unequal chikari groupings the accent ruler can already read.
Carried: remaining triad-sweep misses ((8,15)-family, a
fourth-pass residue trick?); passing tones between certified
verticals; pluck angle; meend on two-pol; canon at the 4th; FD
tanpura dyad verify; sub-midi-40 window; sympathetic strings;
re-calibrate STRUCT_BAR on jawari content.

## 2026-08-30 — session 51: the exiles return — a structural witness for the octave rescue (e51, ruler._sub_structure)

Session 50's open thread, answered the same day: could a rescue
gate use STRUCTURE instead of size? Yes — and it beat size on
every labeled case in both directions. The octave rescue now
asks not "how big is the sub-candidate" but "does the raw
spectrum hold a comb the winner can't explain": on-grid energy
(+/-2 RAW bins of the refined candidate) at the multiples o the
winner's comb misses. Rules, each paid for by a measured
failure:

  - >=2 of 4 witnesses live at 50x their local raw donut, at
    least one ODD (an odd multiple is the one thing a
    half-of-something-real phantom can never inherit — a d=4
    candidate at hz(57)/2 harvested o=2 and o=6 from voice 57
    itself). All-odd witness sets were tried and refuse true
    d>=3 rescues: the honest evidence at o=2,4 was carrying
    them, and 5,7,11,13 are damped high partials.
  - the IMMUNE witness (first of {7,11,13} with o%d!=0) must be
    live. Chords SUPPLY a root/2 phantom's odd witnesses: with
    a perfect fifth, 3*(root/2) IS the fifth, 9*(root/2) its
    h3, exactly; a major third puts 5*(root/2) 14 c from the
    third's octave — inside the window. The vamp's beat 8 (F
    major after G major) fired that phantom as d=2, then, with
    o7 demanded only there, REBORN as d=3 under a winner at the
    chord's fifth. No chord interval is 7:2 / 11:2 / 13:2.
    Every measured true rescue: immune witness >=58x. Every
    phantom: <=6x.
  - fired rescues rank by STRUCTURE first, depth second.
    min(subs) alone let a junk d=3 that scraped struct=2
    shadow a true d=2 with 4/4 live; it had also been letting a
    d=5 fire 43 cents off the truth read "correct" by rounding
    luck. When structure is the gate, most-evidenced wins.
  - witnesses read the RAW spectrum, which no null touches: the
    e50 single-witness failure (chords eating nulled bins)
    cannot recur — a shared bin is still live in raw, and for
    a structural witness, sharing IS evidence.
  - polyphonic first passes (dyad/triad p1) use the structural
    rescue too (struct_sub), with size demoted to a -80 dB
    confirmation: a true voice under an octave-up winner
    measured frac 0.028 — below any honest size floor. The
    single-voice path (hps_pitch, contour) keeps its own
    calibrated legacy rescue: FM smears witnesses off-grid,
    and its lessons were earned separately.

Everything re-swept under the final rule. Certified triad
shapes 9 -> 23 (all 14 ever certified return, plus (3,3),
(3,8), (3,15), (4,7), (7,4), (7,16), (8,3), (8,9), (9,4) —
root-position major triads, inversions, diminished). Full
sweep 542 -> 586/636. Dyad suites PERFECT (209/209 systematic,
87/87 random — the (46,61)-family octave-up thread closes).
The session-50 phantom score reads 12/12 blind. e44 re-auditions
to seed 4: the ORIGINAL session-44 crab melody ships again. e50
re-auditions first try on the 23-shape pool. dev_smoke 79 green.

Proof piece: the DORIAN VAMP — 16 beats of root-position i and
IV (D minor, G major: the raised-sixth IV is the mode's
signature) with C, F, Em, Am, the texture no earlier certified
set could spell, recovered 16/16 blind with all seven major
triads named. Controls: six exiled cases read (6/6), nine new
shapes hold (45/45), sine dyad stays unrescued (witnesses
silent for partial-free content), phantom score clean.

Ruler lesson, the week's biggest: when true and false evidence
overlap in SIZE, stop measuring size. The overlap that exiled
five shapes was real — but it was a shadow of a deeper variable
that separates cleanly (structure: 4/4 vs 0-1 witnesses). And
the adversary is musical, not random: every witness a phantom
ever presented was supplied by a CHORD INTERVAL (fifth -> o3,
o9; third -> o5). The immune witnesses 7, 11, 13 are immune
precisely because Western harmony has no 7:2 — the ruler's
last line of defense is the seventh harmonic's dissonance.

Render sent: e51_exiles.ogg (two loop passes).

Open threads: the remaining 50 sweep misses (shapes like
(8,15), (16,9) still fail structurally — 5:2-family pair
collisions; is there a fourth-pass residue trick?); triad
progressions with passing tones; jhala; accent ruler; pluck
angle; meend on the two-pol string; canon at the 4th; verify FD
tanpura with dyad_pitches; sub-midi-40 adaptive window;
sympathetic strings; STRUCT_BAR=50/STRUCT_COUNT=2 were
calibrated on pluck mixes — re-calibrate before trusting them
on fdpluck/jawari content.

## 2026-08-30 — session 50: three voices, heard blind (e50, ruler.triad_pitches)

The oldest open thread, banked the day dyads worked: name ALL
THREE voices of a mix by iterated subtraction. triad_pitches =
HPS -> null the winner's comb -> strict HPS on the residue ->
null again -> strict HPS on the twice-cut residue. _null_comb
extracted from dyad_pitches (fill = min(median, 4e-4*max)).

Contract measured on 636 systematic pluck triads. The sweep
itself extended the shadow family: pair intervals within ~40 c
of n:1 for n=2..8 hide a voice — {12, 19/20, 24, 31, 34} were
known; "unexplained" failures decoded as 28 (~5:1) and 36
(=8:1). At most one pair may be 16 (5:2 survives one null cut,
not two). Even inside those rules only shapes that read
PERFECTLY across roots 45..62 are certified: NINE shapes,
{(3,4),(3,7),(4,4),(8,8),(8,21),(9,7),(9,8),(15,15),(21,8)}.

The week's hardest ruler lesson lives in why it's nine and not
fourteen. The strict octave rescue needed a bar against loop-
context junk (phantoms fire at frac 0.06-0.10 of the winner and
demote a clean read an octave). First fix: an odd-harmonic
witness (a real sub-octave fundamental has a live 3rd
harmonic). Structurally blind — chords EAT the witnesses: a
just fifth nulls 3*f_lo == 2*f_hi, a major third nulls 5*f_lo
== 4*f_hi, so a major triad's root loses both at once. Second
fix: raise the bar to 0.12. The threshold sweep then showed the
real shape of the problem — six shapes' TRUE rescues need fracs
of 0.08-0.11, inside the phantom band. The fraction cannot tell
those rescues from junk, so the shapes (root-position major
triad (4,3) among them) fall out of the certified set rather
than the bar coming down. A ruler's blind spot you can MEASURE
is a contract line, not a bug to tune away.

Second lesson, same blind spot from the other side: certified
means certified IN ISOLATION. In a loop each vertical is read
through its predecessor's ring-over, where the rescue's
ambiguity cuts both ways (seed 50's passacaglia lost one beat
to a refused true rescue and one to an admitted phantom). So
blind recoverability became part of the SOLVER's acceptance:
audition candidate scores, ship the first that survives its own
measurement. The proof piece — a 12-beat chord passacaglia in D
dorian, every vertical a certified shape, voices moving <=5
semitones, home chord D minor — passed on audition 2: 12/12
triads named blind, all classes dorian, seam p96.2.

Applied retroactively per the session-43 house rule (a ruler
change unverifies every old verdict): e44's crab canon measured
27/28 under the shipped bar (beat 5's true rescue at frac
0.10-0.12, refused). Its melody was always seeded-search
output, so it got the same audition treatment — seed 5's crab
reads 28/28 blind with the same algebra, palette, and range.
dev_smoke 79 checks green (triad check added), e44 + e50 ALL
RULERS PASS under the shipped ruler.

Render sent: e50_triads.ogg (two loop passes).

Open threads: the five exiled shapes — could a rescue gate use
STRUCTURE instead of size (e.g. comb residual energy at f/2 vs
f) to split true rescues from phantoms inside the overlap band?
Triad progressions with passing tones (needs onset-segmented
triads vs dyads); jhala; accent ruler; pluck angle; meend on
the two-pol string; canon at the 4th; verify FD tanpura with
dyad_pitches; sub-midi-40 adaptive window; the 3 dyad-suite
octave-up misses; sympathetic strings.

## 2026-08-30 — session 49: jor — the line acquires a pulse (e49)

The raga arc's next stage after alap (e46) and ornament (e47):
jor, melody on a steady right-hand pulse, no tala cycle yet.
24 pulses at 2.5 Hz over the two-polarization drone (e48); the
line is 20 designed (midi, pulses, glide) triples in Kafi —
plain notes dwell, held notes MEEND into their successor so the
glide lands as the next pulse strikes, cadence resting on Sa.
No new library code: this cycle is the accumulated kit proving
a composition — grid by onset_times + pace prior, rate by
pulse_rate (2.44 measured / 2.5 designed), every note's hold by
pitch_contour median (worst 1.9 cents across 20 notes), every
meend landing +/-25 c (worst 21.1), hierarchy by dwell_seconds
(Sa argmax), seam p33.3, poles {D, A}.

Ruler lesson (an old one, re-earned in a new place): spectral
flux is blind to a strike at t=0 — no prior frame to rise from.
The doubled signal exists precisely so the SECOND pass can
recover slot 0, but the slot filter rejected k=24 instead of
folding it modulo the loop; 19/20 until the fold. When a
measurement wraps, its INDEXING must wrap too.

Musical note for the record: a meend that lands exactly on its
successor's pitch nearly erases the successor's onset (the
attack adds no new spectral content) — flux still caught these
at 0.4 amp headroom, but landings a semitone short of the next
note would be safer articulation if onsets ever go missing.

Render sent: e49_jor.ogg (two loop passes).

Open threads: jhala (fast chikari punctuation between melody
notes — the pulse subdivides); accent patterns (jor's 4-pulse
grouping, needs an accent ruler comparing onset-local energy).
Carried: pluck angle as a playing parameter; meend on the
two-pol string; three+ voices by iterated subtraction; canon at
the 4th; verify FD tanpura with dyad_pitches; sub-midi-40
adaptive window; the 3 dyad-suite octave-up misses; sympathetic
strings.

## 2026-08-30 — session 48: the two-polarization string — shimmer by physics (e48, fdstring.fdpluck2 + ruler.beat_profile)

The longest-carried thread, built. A real string vibrates in two
transverse planes, split a few cents, exchanging energy at the
bridge — and only one plane meets the jawari. fdpluck2 runs both
lattices: vertical u (plucked, bridged), horizontal v (silent at
t=0, detuned by `split`, fed through a spring across the bridge
zone). Voicing that measured well: split=0.006, kc=1e5, pickup
cos(0.6)u + sin(0.6)v.

Everything the design promises, measured on the bus it happens
on (13 rulers green):
  - delayed transfer: v peaks 0.41 s after a pluck it never
    received, -23.6 dB under u; kc=0 control stays at -605 dB.
  - the jawari touches only u: sustain hi-band density ratio
    u/v x8645.
  - polarization beating: v-bus envelope breathes at f0*split —
    0.84 measured vs 0.88 designed (split .006), 0.50 vs 0.44
    (split .003), both within an envelope-FFT bin; split=0
    collapses to the 2.8 dB junk floor (true beats read 6-9).
  - the beats survive the mix: each drone string's fundamental
    band carries its OWN rate in the full render — pa 0.63/0.66,
    sa 0.84/0.88, SA 0.42/0.44 Hz, a chord of shimmer rates
    proportional to each f0.

New ruler: beat_profile (rate_hz, depth_db of a band envelope's
slow ripple). Lessons earned:
  - DETREND before reading an envelope spectrum: a decaying
    note's ramp votes ~0.3 Hz for ANY signal — a beatless
    single-pol pluck read the same 'beat' as a beating two-pol
    until the log-envelope trend was subtracted.
  - measurement bands need spectral ISOLATION: band_env's
    2nd-order edges are shallow, and the sa pair's louder,
    deeper 0.84 Hz beat colonized pa's +/-10% band (read 0.84
    where pa's own rate is 0.66) — ring-over enfranchisement's
    cousin in the envelope domain. pa verifies at +/-5%.

The piece: the e42 drone voiced entirely with two-pol strings —
a tanpura that breathes at four rates at once. Seam p19.5, poles
{D, A} hold.

Render sent: e48_twopol.ogg. Smoke 78 green.

Open threads: pluck ANGLE as a playing parameter (energy starts
split between planes; the jawari should bloom differently).
Meend on the two-pol string (bend both planes, coupling under
tension change). Jor/jhala — pulse under the drone. Carried:
three+ voices by iterated subtraction; canon at the 4th; verify
FD tanpura with dyad_pitches; sub-midi-40 adaptive window; the 3
dyad-suite octave-up misses; sympathetic strings.

## 2026-08-30 — session 47: gamak and andolan — the ornament earns its ruler (e47 + ruler.ornament_profile)

Session 46's lead thread. The meend machinery does oscillating
ornaments for free; the cycle's work was the honest ruler:
ornament_profile reads (rate_hz, depth_cents) off a pitch
contour — rate from the cents-contour spectrum's dominant line
(log-parabola sub-bin), depth as robust half peak-to-peak.
Measured on the FD string, own bus: andolan on ga (designed 3
Hz, +/-30 c) reads 3.00 Hz / 0.96 of design; gamak ga<->ma
(designed 6 Hz, 200 c pp, 11.5 cycles so it LANDS on ma) reads
5.99 Hz / 0.90 of design through the calibrated transfer. Dwells
around the ornaments at 0.8-1.5 cents.

Ruler lessons earned, both from measured surprises:
  - the contour under FM is NOT a moving average, and the sinc
    story I brought to the cycle was wrong: each partial's
    refined peak sits where the oscillation DWELLS (its
    extremes), so a 0.08 s window keeps 0.88 of a 6 Hz depth
    where naive averaging predicts 0.66 (and 0.22 s windows keep
    0.80, not 0.16). Depth claims go through a TRANSFER
    CALIBRATION — design x the control's measured ratio, +/-20%
    — never through theory.
  - the control must model the INSTRUMENT CLASS. The first
    control was a bare FM sine: single partial, nothing for
    _partial_refine to refine against, one glitch per
    quarter-cycle — a 6 Hz ornament measured 24.0 Hz and depth
    6.4x design. The harmonic-rich control (h1 + 0.4 h2 +
    0.2 h3, the instrument class of every string here) reads
    3.01/5.99 Hz true. Asserted in the experiment: the bare-sine
    misread IS a pass/fail check, so the lesson can't rot.

The piece: two drone cycles under one sung line, two plucks
breathing where a singer would — Sa, rise to ga, andolan, the
gamak shake up to ma, settle, the long way home. Seam p7.9,
poles {D, A} hold.

Render sent: e47_gamak.ogg. Smoke 76 green.

Open threads: jor — pulse under the alap (the drone pluck grid
is a latent tala); a full alap+jor+jhala arc as a longform
piece. Gamak between non-adjacent degrees (Sa<->ga thirds).
Carried: three+ voices by iterated subtraction; canon at the
4th; verify FD tanpura with dyad_pitches; sub-midi-40 adaptive
window; the 3 dyad-suite octave-up misses; sympathetic strings;
two-polarization string.

## 2026-08-30 — session 46: alap in Kafi — the meend vocabulary speaks (e46 + ruler.dwell_seconds)

Session 45's raga thread, cashed in. D dorian IS Kafi thaat and
the FD tanpura already drones D-A, so the alap wrote itself onto
the existing instrument: four single-pluck phrases over four
drone cycles (19.2 s loop) — establish Sa with the step above,
lean into ga-ma, reach Pa and touch upper ni, come the long way
home to Sa. Every gesture is a designed per-sample trajectory
(geometric glides — equal cents per second, how a hand bends)
and pitch_contour reads all four phrases back at 1.1-2.3 cents
worst-dwell on the solo's own bus.

New ruler: dwell_seconds (contour -> seconds of residence per
chromatic class, relative to a declared tonic). A raga's note
HIERARCHY becomes a measured claim: frames farther than 35 cents
from every class vote nowhere, because a meend is motion, not
residence — and that is also why it consumes pitch_contour
output rather than a chroma vector (chroma integrates ENERGY,
crediting loud glides to whatever bins they cross). Measured on
the alap: Sa 4.0 s (argmax), Pa 2.6 s (runner-up, the vadi
claim), next class 2.2 s. Register arc asserted from measured
ceilings (165 < 196 < 261 Hz, home at 196), not the score.

Ruler lesson earned (e35's chroma rule, sharpened): with the
solo dwelling on Pa, the mix's D-vs-A chroma argmax became a
NEAR-TIE that flips with window length (one loop pass: A wins
by 4%; two passes: D by 1.8x — low-partial skirts fold
differently as resolution doubles). An argmax between two poles
that close is not a stable claim. The honest mix claims: top-2
== {D, A} and their combined share >= 0.5 (measured 0.63);
tonic supremacy lives in the dwell ruler on the solo bus, where
it is actually true by 1.5x.

Render sent: e46_alap.ogg (two loop passes). Smoke 75 green.

Open threads: gamak (oscillating meend — the trajectory
machinery does vibrato-depth ornaments for free; needs a ruler
for oscillation rate/depth against design). Jor: add pulse under
the alap (the drone's pluck grid is already a latent tala).
Multiple plucks per phrase (bols) with re-articulation mid-bend.
Carried: three+ voices by iterated subtraction; canon at the
4th; verify FD tanpura with dyad_pitches; sub-midi-40 adaptive
window; the 3 dyad-suite octave-up misses; sympathetic strings;
two-polarization string.

## 2026-08-30 — session 45: meend — the FD string learns to bend (e45 + ruler.pitch_contour)

Session 43's open thread. Pitch lives in ONE coefficient of the
scheme (lambda^2 = (c dt/dx)^2), so time-varying tension is one
multiply per step: fdpluck now accepts an array of per-sample Hz
(grid sized for the trajectory's highest note, where stability
is tightest). Measured: a 2-semitone meend tracks its designed
trajectory to 0.4 cents through the bend (holds 2.8/0.1), the
bend is monotone, and the jawari still blooms x12.8 on a BENT
string vs the same trajectory unbridged. The piece: the e42
tanpura drone (two cycles) under a solo voice singing two meend
gestures, D3-F3-E3 and E3-D3 home to sa; solo dwells read back
at 1.6-1.7 cents on the solo's own bus.

The new ruler is pitch_contour (hopping-window HPS + sub-bin
partial refinement) and it cost a full contest redesign, paid
for in measured failures:
  - a numerically CLEAN spectrum let log(junk) decide contests
    (a synthetic glide read 1232 cents off on leakage luck).
    Silence must be uniformly silent evidence: bins below -120
    dB of peak are ineligible to win, and every member's product
    contribution is FLOORED at -60 dB of peak.
  - first redesign (a lexicographic strong-member COUNT) fixed
    the pure sine but planted this session's regression: in
    e44's beat residues a -44 dB ring-over shard counts the same
    as a 0 dB fundamental, and a LOW candidate harvests one
    shard from each ringing neighbor — 4 votes to 3 over the
    true voice at beats 2/26 (interval 16 is a 5:2 near-miss, so
    nulling voice 1's comb eats voice 2's EVEN partials and
    halves its evidence). Fix: the count is gone; evidence above
    the floor weighs by log SIZE (soft-clamped product), and the
    strong-own-bin bonus breaks the pure-tone ties the count was
    invented for. A/B on the full battery: product ties count
    everywhere else and wins the polyphonic residue — e44 back
    to 28/28 blind with interval 16 still in the palette.
  - dilation is a FREQUENCY tolerance, not a bin count:
    pitch_contour's 0.22 s windows have 2.3x wider bins, and +/-3
    bins let low candidates borrow the true peak's main lobe (a
    pure tone read at the band edge). Its dilation is +/-1 bin.
  - the dilated contest names the RIDGE; the raw spectrum names
    the bin within it. A pure tone's 7-bin plateau ties exactly
    and argmax took the low edge — hps_pitch read every sine 3
    bins (48 cents at 220 Hz) flat. Re-center on raw: sines now
    5/5 exact.
  - refinement must be strong-only + sub-bin: median over
    per-partial argmaxes still got dragged by junk positions
    (a pure sine refined to 209.09 Hz); now only partials >=
    -60 dB of the strongest vote, each log-parabola interpolated.
  - dyad null fill is capped below the evidence floor
    (min(median, 4e-4 max)) so null plateaus can never vote.

Re-sweep after the ruler change (house rule): smoke 74 green,
solo sweep 270/270, pure sines 5/5, dyad systematic 195/196 and
random 88/90 (a NEW harder suite than session 44's; the 3
misses are octave-up reads on the residue voice, identical
under the old count contest — pre-existing, now on the books:
(46,61)->(58,61) the worst), synthetic glide 4.3 cents, e40-e45
all green.

Render sent: e45_meend.ogg (drone + two meend phrases, two loop
passes).

Open threads: the 3 dyad-suite octave-up misses (residue pass
picks 2*f2; the rescue's strict mode may be too strict). Three+
voices by iterated subtraction. Canon at the 4th. Verify the FD
tanpura with dyad_pitches. Sub-midi-40 pitch needs adaptive
window length. Sympathetic strings driven by the FD tanpura.
A raga sketch over the drone — meend is the vocabulary, now
spellable. Two-polarization string (vertical + horizontal with
weak coupling).

## 2026-08-30 — session 44: crab canon, heard blind (e44 + ruler.dyad_pitches)

The oldest open thread (polyphonic transcription, parked since
e40) built as blind TWO-VOICE pitch recovery: HPS names the
stronger voice, its refined comb is nulled to the spectral
median, a second HPS pass reads the survivor. Contract measured
on ~300 random pluck dyads (~99%): both voices >= midi 43, no
SHADOW INTERVALS — octave (2:1), twelfth (2.997:1), and the
twelfth's penumbra (interval 20, thirty cents off harmonic 3)
hide voice 2 inside voice 1's spectrum. Proof piece: a 28-beat
crab canon in D dorian (voice 2 = voice 1 backwards, an octave
down) — 28/28 dyads named blind from the mixed render, and the
crab property (low voice reversed + 12 == high voice) asserted
on RECOVERED data, not the score.

The chase fixed real hps_pitch bugs and taught this cycle's
ruler lessons:
  - the octave-rescue divisors ran 2..4 but the HPS winner can
    be harmonic SIX or EIGHT of the truth — rescue landed on the
    wrong octave (solo sweep 40..84 x6 seeds now 270/270).
  - a true fundamental can be <1% of the winner yet unmistakably
    real. Qualifying it by ABSOLUTE floor multiple broke e42's
    open string (a decaying signal's broadband skirt clears any
    multiple of a long window's minuscule global floor) — the
    honest test is LOCAL contrast against a DONUT median
    (neighborhood minus the peak's own dilated plateau), and the
    threshold was CALIBRATED, not chosen: measured phantom 96x,
    weakest true starved fundamental 638x, threshold 200x.
  - a NULLED residue spectrum cannot vouch for weak
    fundamentals: half-cut null edges mimic contrasting peaks
    and invite phantom /2../4 rescues — the residue pass runs
    strict (fraction test only).
  - the dyad ruler caught a real COMPOSITION bug blind: a crab
    pair (a,b) sounds in both temporal directions, (a, b-12) and
    (b, a-12), so the palette must be closed under d -> -d
    (e40's inversion-closure lesson in retrograde costume). The
    solver had checked one direction; the ruler read an
    unverified 17 out of a "finished" canon.
  - the crab's structure plants a trap at the seam: v2[L-1] ==
    melody[0]-12 ALWAYS, so beat L-1's low tail rings the exact
    sub-octave under beat 0's high voice. Note length now
    barely exceeds the beat (only the fade wraps).

Render sent: e44_crabcanon.ogg (two loop passes, high voice
right, low voice left). Smoke 72 green; e40/41/42/44 all green
after every ruler change.

Open threads: three+ voices by iterated subtraction (the null
machinery generalizes). Canon at the 4th (rotation +
transposition algebra). Verify the FD tanpura with dyad_pitches
(jawari spectra are harsher than plucks). Sub-midi-40 pitch
needs adaptive window length (a 0.5 s window starves 70 Hz).

## 2026-08-30 — session 43: the unbreakable bridge, and a record corrected (e43)

Chased session 42's open thread — energy-conserving collision to
fix the grid brittleness — and the first honest measurement
corrected the record instead: THE BRITTLENESS WAS THE OLD RULER.
e42 diagnosed "N=150 doesn't bloom" under the displacement
readout and single-signal env-peak ruler, then replaced both
(velocity readout for the seam, wet/dry ratio for the attack
tilt) without re-running the sweep. Under the shipped
measurement, every grid 130..160 blooms — with the plain penalty
contact AND the new one (7/7 each, asserted). Lesson earned:
when the ruler changes mid-session, every verdict issued under
the old ruler is unverified — re-sweep before logging it.

The SAV contact (scalar auxiliary variable, psi = sqrt(2phi+eps)
per node; midpoint force linear in the unknown, so each node
solves in closed form, no Newton) still earned its place as
fdpluck's default, for what it was actually built to guarantee:
  - ENERGY: lossless string with contact live, total discrete
    energy (string + psi^2/2 store) drifts 1.4e-12 relative —
    machine precision — vs the explicit penalty's 1.7e-2. The
    contact work telescopes as a difference of squares, exactly.
  - ANY K: penalty NaN-explodes at K=1e11; SAV rings at 1e12.
    Contact stiffness is now a voicing knob, not a footgun.
e42 re-run green under the new default (bloom 1.0s x3.3, enrich
x16.8 — same instrument, safer integrator). Smoke 71 green.

And the knob is musical: sustain enrichment across the K
staircase is an ARC — x3.5, x16.8, x6.7, x4.2, x0.8 for
K=3e8..1e12. An infinitely stiff bridge is a clean hard wall
and barely buzzes: a jawari filed too sharp goes dead, in the
simulation as on the instrument. Render sent: e43_savbridge.ogg,
the same A2 string five times, bridge stiffness x3000 end to
end, panned left to right.

Open threads: tension modulation for meend/glissando (c varying
per step — stability budget allows it if c stays under the grid
limit). Sympathetic strings driven by the FD tanpura. Raga
sketch over the drone. Two-polarization string coupled at the
bridge. Grandsire / touches with bobs (from e39).

## 2026-08-30 — session 42: the jawari, won (e42 + loam/fdstring.py)

e41's closing conjecture — bloom needs DISTRIBUTED contact plus
dispersion — built and CONFIRMED. New module loam/fdstring.py:
Bilbao's explicit stiff-string scheme (u_tt = c²u_xx − κ²u_xxxx
− 2σ₀u_t + 2σ₁u_txx, stable while λ²+4μ² ≤ 1) with a parabolic
barrier under the last 10% of string, elastic penalty contact
(K·pen^1.3). ~1 s compute per 1 s audio. The rulers, all green:
wet/dry 1.5-6 kHz envelope ratio peaks at 0.8 s at x3.5 (the
bloom, as WHAT THE BRIDGE ADDS — attack is common-mode and
cancels), sustain enrichment x18.8, pitch 110.0 exact both, late
RMS within 4 dB of the open string (the e41 damper result,
inverted). Render: Pa-sa-sa-SA tanpura cycle in D, middle
strings 3 cents apart, 12 s tails wrapping a 4.8 s loop.

Three lessons paid for in failed runs:
  - GEOMETRY: the barrier apex must sit AT the termination.
    First attempt put the parabola's zero mid-zone — the string
    got pinned there and the PITCH said so: 117.5 = 110/0.94,
    the detuning naming the bug's location exactly.
  - CONTACT: projection (max(u, barrier)) is a perfectly
    inelastic collision — it ate the string alive (late RMS
    −101 dB, enrichment x0.0). Elastic penalty force preserves
    the energy the bloom needs.
  - READOUT: displacement starts on a DC step (string released
    from a held shape) — clicked at every onset and killed the
    loop seam (p100). Velocity readout starts at exactly 0
    (released from REST) — seam p7.3, and it's what a pickup
    measures anyway.

Ruler lessons: env_peak_s + band_env promoted into ruler.py (the
e41 ad-hoc bloom clock, used twice = library). Ratio-of-band-envs
in matched bins is the honest "what did the process add, and
when" question; single-signal env peak was fooled by velocity's
+6 dB/oct attack tilt. And a caveat kept in the open: the
grazing-contact regime is GRID-BRITTLE — N=140 blooms at 110 Hz,
N=150 doesn't (verified at every readout node, so it's dynamics,
not measurement; α=2 Hertzian didn't cure it). N is therefore a
per-string VOICING parameter, swept and pinned per note like
walking the jawari thread on a real bridge (pa 140, sa 112,
SA 138).

Open threads: energy-conserving implicit collision (Bilbao &
Chatziioannou) would likely fix the grid brittleness — worth a
cycle. Sympathetic strings DRIVEN by the FD tanpura (feed it to
strings.sympathetic). Raga sketch over the drone (flute/ney).
Two-transversal-polarization string with coupling at the bridge.

## 2026-08-30 — session 41: the bridge that wouldn't buzz (e41 — a negative result, kept)

Chased e38's nonlinear-bridge thread to the tanpura: the jawari,
whose signature is the BLOOM — high partials swelling AFTER the
attack. Four bridge models went into the KS loop; every one
measured as something other than a jawari, and the failures were
more instructive than a success would have been:
  - one-sided saturator: a DAMPER (sustain 2.5-6 kHz x0.48 vs
    dry). Mechanism: anything riding the fundamental's positive
    half-cycle sees the transfer curve's derivative gain < 1 —
    modulation loss beats harmonic generation, every trip.
  - saturator + per-block RMS restitution: restores ENERGY, but
    the fundamental owns the energy — the high partials stay
    lost (late centroid 0.16x dry). Lossless-on-average is not
    lossless-per-band.
  - moving contact (displacement-dependent delay — the honest
    physics: the string's effective length shortens as it swings
    toward the curved bridge): pitch-exact, but the SWEPT
    fractional-delay interpolation smears highs (0.41x dry).
    Phase-modulation was right in intent; linear interp is a
    lowpass whose loss the modulation exercises.
  - hard obstacle at fixed height: barely engages — per-band
    ratios 1.12..1.31, uniform: GAIN, not spectral change.
Positive controls: all five keep HPS pitch at exactly 110.0 Hz,
all four bridges measurably alter the waveform, and a synthetic
bloom signal proves the bloom ruler reads a delayed HF max
correctly (0.8 s designed, 0.8 s read) — the negative is not a
blind ruler.

Conclusion, recorded: delayed-HF-max bloom needs DISTRIBUTED
contact along the bridge plus string dispersion (van Walstijn's
tanpura simulations have both); a point nonlinearity anywhere in
a KS loop either damps or does nothing. strings.py stays as
shipped (buzz/level params reverted before commit);
e41_bridgetrials.py keeps the evidence as 20 passing assertions.
Exhibit render sent: e41_bridgetrials.ogg (the same A2 pluck
through all five bridges, 4 s each: dry, saturator, restored,
contact, obstacle).

Open threads: a REAL jawari needs a waveguide with several
contact cells + a dispersion allpass — a proper future cycle
(maybe a new loam/waveguide.py); canon at the 4th; polyphonic
transcription; Risset decelerando; thunder doublet.

## 2026-08-30 — session 40: ouroboros (e40; ruler.transcribe, hps_pitch hardened)

The transcription thread, with a compositional customer: a
CIRCULAR CANON. One 32-beat D dorian line, composed by seeded
backtracking search to harmonize with itself rotated half the
loop — voice two is the same melody 16 beats behind, an octave
down, forever. Constraint theory lesson up front: each rotation
pair sounds in BOTH directions half a loop apart, so a P5 one way
is a P4 the other — the consonance set must be inversion-closed
{unison, 3rds, 6ths}: the form forces invertible counterpoint at
the octave, and the search's first "solution" (asymmetric set
with the fifth in) failed its own verifier. Stepwise motion, no
parallel octaves, range >= an octave, wrap obeys everything —
bar one is bar seventeen's counterpoint in both directions.
84 BPM, 22.9 s, two plucks + oh-drone, p89.4 seam.

ruler.transcribe (onset_times + hps_pitch per inter-onset window,
monophonic only) landed — and hardened hps_pitch through three
honest failures on the way to 32/32:
  - PARTIALS ARE NOT BINS: exact-bin downsampling demands partial
    h at bin h*i; real pluck partials drift a bin or three, one
    missed high partial lands on log(~0), and the true candidate
    loses to its own 3rd harmonic. Fix: dilate magnitudes
    (maximum_filter, +/-3 bins) before the harmonic sum.
  - the OCTAVE ERROR has a physical accomplice: pick=0.2 notches
    partial 5 (the pick-position comb), sabotaging f0's 5-term
    product while 2*f0's harmonic set dodges the notch. Fix:
    subharmonic rescue — genuine energy AT f*/2,3,4 means the
    subharmonic is the fundamental.
  - "genuine" must be TWO-SIDED: a KS fundamental can be 12x
    weaker than its own 2nd partial (8% of the octave peak, below
    any winner-relative bar) yet sit unmistakably above the
    spectral floor. >= 6% of winner AND >= 8x the dilated median.
Also: the dyad ruler's quarter-tone probe at +/-3% width
CONTAINED the peak it probed against (band [0.998f, 1.060f]) —
probes moved to 3/4-semitone +/-2% and Hann-tapered (rectangular
sidelobes flood narrow bands); 1.7x became 6684x. And a
truncated test pluck's hard stop reads as an onset (smoke fade).

All 5 rulers pass: a line exists, counterpoint holds (32/32
intervals consonant, 0 parallel perfects, range 19), the tune
comes back 32/32 exact from voice one's bus, designed-dyad
density 6684x probes, seam p89.4. e39 re-run green after the
hps changes (regression checked). dev_smoke 69. Render sent:
e40_ouroboros.ogg.

Open threads: canon at OTHER intervals (rotation + transposition:
canon at the 4th needs its own interval algebra); a crab canon
(retrograde needs non-loop rendering or palindromic melody);
polyphonic transcription (NMF or iterative subtraction — the
"different animal" the docstring warns about); Risset decel /
thunder doublet / taraf bridge still open.

## 2026-08-30 — session 39: Plain Bob Minor (e39; ruler.onset_times)

Permutation music: change ringing on the modal church bells. A
plain course of Plain Bob Minor — six bells, place notation
x.16 alternating with 12 at each lead end, five leads, 60
distinct rows, and the 60th change returns to rounds: the loop
IS the group-theoretic closure (design self-check asserts both).
G-major hexachord E5..G4, rounds descend; rope-circle panning,
tenor rings longest; the handstroke gap observed (one bell-space
of breath before every handstroke row). 93.6 s, 360 strikes,
tower reverb.

The cycle's real purpose: an honest customer for
ruler.onset_times (promised in e36). Spectral flux, local
median+MAD threshold, peak picking. Two earned rules:
  - in a REST the local median and MAD collapse together and the
    threshold chases noise: all four ghosts fired inside
    handstroke gaps, 130-210 ms after a strike (tail flutter).
    An absolute floor helps but cannot fully separate — measured
    flux distributions OVERLAP (faintest true strike 8.7 vs
    ghosts 40-53; a re-struck bell rises less over its own still-
    ringing tail). The separation that works is the CALLER'S
    PRIOR: min_sep just under the known pace (0.2 s vs 0.24
    spacing) makes each ghost lose the local-max contest to its
    parent peak. Detector generality stays; the pace knowledge
    lives in the experiment where it belongs.
  - spectral flux is blind to a strike at t=0 (it sits inside
    frame 0 with no prior frame to rise from) — smoke-test
    clicks start at 0.2 s, and the docstring says so.
  - (comparison-logic tuition, cheap but real: zip-aligning
    detected to designed sequences turns 4 insertions into ~340
    "errors" — 6.4% measured, worse than chance, which was
    itself the tell that alignment, not sound, was broken.)

Bell-order recovery: per-bell narrowband energy RISE at each
detected onset (rise, not level — ringing tails don't rise;
whole-tone spacing keeps prime bands disjoint). All 5 rulers
pass: course closes (60 distinct, returns to rounds), all 360
strikes counted, order recovered 98.9% (356/360), handstroke gap
2.02x a bell-space vs plain joins 1.00x, seam p32.1. dev_smoke
68 checks. Render sent: e39_plainbob.ogg.

Open threads: Risset decelerando / ITD treadmill (e36); thunder
ground-reflection doublet (e37); storm-harp dynamics + nonlinear
taraf bridge (e38); with onset_times + chroma + hps in the
drawer, a TRANSCRIPTION ruler (recover a full melody from a
render) is within reach — would let melodic experiments claim
their tunes; Grandsire or a touch with bobs/singles would test
the method machinery harder.

## 2026-08-30 — session 38: the storm harp (e38; ruler.flatness, ruler.chroma)

e37's open thread, the storm SONG: thunder as a chord source.
Four strikes (1.2/4.5/2.2/6.5 km) drive sympathetic() — the taraf
bank — tuned to nine strings on D/A/D/F/A/C/D/F/A. Pitch classes
{D,F,A,C} only, no E: "no foreign notes" stays falsifiable.
Broadband rumble in, D minor out — the sky plays the harp, the
strings ring 10 s, every tail wraps. Rain (soft, dark) and low
wind underneath. 40 s loop.

New rulers, both born of need and both wrong on the first cut —
the flatness tuition came in TWO installments:
  - ruler.flatness (Wiener entropy) for the TONALIZATION claim
    (noise in, chord out — deliberately blind to WHICH pitches;
    that's chroma's job). Installment one: a single wide-band
    flatness confounds TILT with tonality — post-e37 thunder
    crams its power into a few low bins, so the NOISE measured
    "tonal" (0.015) because most of the window was merely empty.
    Fix: Wiener entropy per octave band (tilted noise is still
    locally flat; only a comb is spiky inside its own octave).
    Installment two: the unweighted octave average let the quiet
    noise-floor octaves above the music outvote the loud combed
    ones (5x, needed 10x) — the POWER-WEIGHTED centroid lesson,
    now in its second home. Power-weighted: sky 0.50, harp 0.056.
  - ruler.chroma: 12-bin pitch-class power fold, normalized;
    docstring carries e35's warning that chroma claims are
    RELATIVE (top-k membership), never absolute floors.

Then the instrument met the ruler instead of the other way
around: 9x tonal at t60=6 s against a stated 10x design claim —
the threshold WAS the design, so the fix was more instrument
(t60 10 s, damp 0.3: sharper comb over the same drive floor),
not a quieter ruler. 14x, and a lovelier sustain for it.

All 5 rulers pass: tonalization 14x (0.50 -> 0.036), comb
selectivity 94x (tuned bands vs quarter-tone probes), strings
answer the sky (envelope corr 0.74 at +145 ms — response follows
excitation), no foreign notes (top-4 chroma exactly {C,D,F,A}),
scene seam p56.7. dev_smoke 67 checks (flatness noise/sine and
chroma A440 self-checks added). Render sent: e38_stormharp.ogg.

Open threads: Risset decelerando / ITD treadmill (e36); thunder
ground-reflection doublet (e37); the harp wants DYNAMICS — a
tension scalar a la e35 that walks the bank between tunings
(storm passes, mode brightens?); sympathetic() coupling is linear
— a nonlinear bridge (tanh on the drive tap) would give the taraf
its buzz.

## 2026-08-30 — session 37: thunder is geometry (e37, texture.thunder)

The open thread from e36: the storm had rain, wind, fire, water —
and no voice. texture.thunder(dist_km, strike_km) after Farnell:
thunder is not a sound, it's GEOMETRY — every meter of a
kilometers-long channel shocks at once, and what you hear is that
line source integrated over arrival time. Segment at height h
arrives at (sqrt(dist^2+h^2)-dist)/c, so duration is not a knob:
a 0.8 km strike smears over 9.6 s (the top of the bolt is far
even when the bottom is close), a 5.5 km one compresses to 3.8 s
of dark clap. Air absorption exp(-d/L) picks each arrival's
surviving spectrum, so the tail darkens CAUSALLY — later sound
walked farther. Crack = the nearest segments' N-wave (biphasic
snap + 0.8-5.2 kHz tear) dying as exp(-dist/1.2); afterclaps =
2-3 branch clusters at shared height/azimuth; sub = 25-80 Hz
decorrelated noise riding the event's own smoothed envelope.

Three synthesis flaws, all caught by rulers on bare buses
(norm=False, house rule):
  - an event-RELATIVE amplitude law ((d_min/d)^1.2) silently
    peak-normalizes every strike — the far strike measured only
    3.7 dB softer than the near one because each was loud
    relative to itself. Absolute 1/d^1.2: gap 30.7 dB. The
    per-call-normalization rule, now caught at DESIGN time.
  - L=1.8 km absorption was too gentle to darken a tail within
    one strike (tail centroid 1261 Hz — daylight). L=1.0.
  - WHITE bursts bandpassed to [28, fc] lose the rumble contest
    to their own mid band: a flat spectrum over a 1 kHz-wide band
    out-powers a 95 Hz-wide low band arithmetically. A shock's
    far-field spectrum peaks LOW — per-burst one-pole tilt at
    0.12*fc (scales with the burst's own darkness) fixed it, and
    the crack rightly inherited the highs. Also one crack lesson:
    the snap competes with SUMS of overlapping bursts — scale it
    to the local mix peak, not to one segment's amplitude.

All 7 rulers pass: distance darkens (centroid 205 vs 44 Hz),
crack is a crest (28.8 vs 20.2 dB), tail walked farther (470 vs
183 Hz within the near strike), tail rumbles (25-120 Hz density
4.6x the 500-2500 band), strike decays (peak window 0, -173 dB),
distance softens (-25.9 vs -56.6 dB unnormalized), scene seam
p18.1. dev_smoke 64 checks.

Scene: e37_stormfront.wav — 36 s loop, rain (soil-dark) + low
wind + three strikes at 0.8/5.5/2.5 km; the 29 s strike's tail
wraps into bar one per seam-craft rule 3. Render sent:
e37_stormfront.ogg.

Open threads: Risset decelerando / ITD-steered treadmill variant
(from e36); ruler.onset_times() when an experiment needs it
honestly; thunder wants a ground-reflection doublet and maybe
echo-off-terrain for canyon storms; a storm SONG (the stormfront
as a chord source — thunder through sympathetic strings?).

## 2026-08-30 — session 36: the ruler drawer, and the treadmill (e36)

Free-play session (director: "follow the winds of your own
creativity... and add tooling"; 30-min cron started to keep the
practice going).

Tooling first — loam/ruler.py, the consolidated measurement kit.
The log's recurring lesson is that the instrument is easy and the
ruler is hard, yet every experiment has re-hand-rolled (and once
per session, mis-rolled) the same measurements. Now the earned
version is the callable default, each with its tuition cited in
the docstring: hps_pitch (argmax lies), centroid_hz (POWER
weighted), band_density (power per sample — summed power scales
with window length), crest_db (peaks, not sums), width_corr
(>250 Hz), pulse_rate (envelope from the fast-decaying 1100-3500
band, high-passed at rate/2 so slow undulation can't bias long
lags), seam_rank (numeric twin of seam_report), rms_contour,
report(). dev_smoke now self-checks the rulers against signals
with KNOWN answers (a 440 pluck, a 500 Hz sine, a 3/s click
train) — the ruler drawer gets a ruler of its own. 63 checks.

e36_treadmill.py — the Risset rhythm: barber()'s rhythmic
sibling, an accelerando that gains one tempo-octave per loop and
never arrives. Six tempo layers at octave spacing, rate
R0*2^(k+t/T); loudness is a Gaussian window in log-rate. The
design theorem that buys the seam: every per-hit property (pitch,
pan, duration, gain) is a pure function of the octave position
o = k + t/T, so layer k at the seam IS layer k+1 at bar one — any
property keyed to k alone would jump at the wrap. Beat times from
integrating the exponential rate, t_n = T*log2(1 + n/(N*2^k));
N=72 divisible by 8 makes every layer's beat count an integer,
and the construction phase-locks the layers (layer k's hit n
coincides with layer k+1's hit 2n): one metric tree, forever
climbing. Pitch rides the rate (110 Hz tom at window center),
amp carries 2^(-o/2) so stream ENERGY density is window-shaped,
not rate-tilted. Under it, a barber'd oh-choir rises with the
rhythm — both staircases in one room.

Ruler lesson (one wrong first cut, mine, and this time the new
kit caught it in minutes): the handoff check compared layer k's
LATE rate to layer k+1's EARLY rate with the design ratio
inverted — the windows straddle o=k+1 (late center below it,
early center above), so design is 2^(-W/T)=0.846, not 1.18.
Measured 0.855 / 0.844 — the sound was right, the ruler's sign
was wrong. The genre continues.

All 11 rulers pass: seam p97.6; all six own-bus rate reads within
3% of design (1.12 vs 1.09 ... 7.32 vs 7.36); both handoffs at
0.85 vs design 0.846; mix stationary (RMS spread 1.61 dB over 8
windows — perpetual acceleration, flat loudness); onset-band
density half-ratio 0.981 (the scale-invariance claim, measured).
Render sent: e36_treadmill.ogg.

Open threads for next sessions: a Risset DECELERANDO variant
(negative exponent) and a stereo field where o also steers ITD;
texture.py still has no thunder; ruler.py wants an onset_times()
(spectral flux) once an experiment needs one honestly.

## 2026-08-15 — session 35: the mood seam (e35 — the blend, audible)

e35_moodseam.py — the mood ruling was going to be between two
renders and a SENTENCE ("wanderer as roam bed, spyglass entering
with tension"). This session turns the sentence into the third
render. One 48 s scene (a scene, not a loop — in-game music is
state-driven): wanderer tiles throughout; tension tau smoothsteps
up 10->16 s, holds, falls 30->38 s; spyglass enters at tau's foot
from its own bar 1 on its own clock, gain sqrt(tau); the wander
yields to sqrt(1 - 0.65 tau) — thinner, never gone. The one-system
thesis (both poles from the world's gut + glass, D ground, E
reserved) is what makes the seam this cheap: no key change, no
tempo negotiation, no ducking.

Ruler lessons (two dishonest first cuts, both mine):
  - summed rfft power scales with segment LENGTH — a 10 s window
    against a 7 s one inflated the hum ratio 0.35 -> 0.71. Power
    DENSITY (divide by N) or equal windows; and the yield law is
    read on the wander's OWN bus (house rule), the survival half
    on the mix where contamination can only help (one-sided).
  - an ABSOLUTE chroma floor blames the seam for harmonic leakage
    the poles already carry: the A2 drone's 3rd harmonic IS E4.
    The seam's honest claim is relative — it manufactures no NEW
    E (mix 0.221 vs pole max 0.701; the spy pole's own high
    fraction is A-harmonic leakage against a small D/F floor, not
    touched notes — its note-level claim passed in e31).

All 7 rulers pass: handover has no hole (min -30.9 vs roam -29.2
dB) and no spike, entry steps 0.2 dB, no new E, overlap roughness
0.140 vs solo max 0.165 (the D grounds do not beat), floor yields
exactly to law (own-bus 0.35 vs designed 0.35) and survives in
the mix (0.35). Render sent: e35_moodseam.ogg. The mood decision
packet is now complete: e31 (noir pole), e32 (dread pole), e35
(the seam between them). Integration shape if the blend is ruled
in: tau is the existing awareness ladder (music.gd already takes
NC.register_mix-style scalars), wander bed = roam register,
spyglass stems keyed in above tau ~0.25 with the sqrt law as
here; the 96 Hz line is already shared plumbing (e20/e22).

e34_drawcreak.py — the operator's bar for the draw: "unobtrusive
wood creak... sort of feel like a nice stretch." The shipped
tick-train (e20 -> NC.creak_voice) is discrete WOOD strikes whose
PITCH climbs with frac — physically a pluck gesture, and "plucking
strings one at a time" is the exact complaint on record. The idea:
a real creak is stick-slip friction, and the two voices invert on
both axes — the tick-train raises pitch and keeps rate sparse
(2 -> 13/s, never crossing the ~18/s fusion floor); the candidate
keeps the BODY fixed (170/430/860/1500 Hz limb modes + a papery
2400 Hz shear) and raises the slip RATE (18 -> 70/s, frac^1.4
hazard), so ticks fuse into a groan whose "pitch" is the rate
itself. The gesture ends in a settle (rate holds, amp relaxes over
0.35 s) — a stretch finishes, it doesn't cut off.

Ruler lessons, both earned by a wrong first cut:
  - crest over a RAMPING gesture measures the ramp, not the
    texture — both buses looked equally spiky until the window
    moved to the late, full-intensity half-second.
  - envelope periodicity under a LONG-RINGING mode is a
    subharmonic lie: the 170 Hz mode rings ~200 ms (4 slip
    periods of overlap early), and autocorr read 23/s as 11/s.
    Read the rate where pulses stay distinct — the high band
    (1100..3500 Hz; those modes decay in ~16 ms) — and bandpass
    the envelope to the pulse register so the 0.9 Hz breath
    undulation can't bias long lags.
  - one synthesis lesson too: a 0.9 ms jerk transient is a CLICK
    (crest within 2 dB of the plucks it was built to beat); a
    fiber lets go over ~2.5 ms. Softer slip = the whole
    unobtrusive claim, in one envelope constant.

All 9 rulers pass on RMS-matched buses: groan 6.6 dB smoother
(crest 14.7 vs 21.3 dB), never dark > 23 ms vs 440 ms tick gaps,
rate tracks the designed hazard (measured 24/63 vs designed
23/63, x2.6 rise), tick centroid climbs x1.11 while the groan
body holds x0.99. Render sent: e34_ab.ogg (tick-train, then
groan). Integration shape if ruled in: replace NC.creak_voice's
interval/pitch dict with a rate hazard (CREAK_RATE_LO/HI on
frac^1.4) and synth the groan into a one-shot the way
_synth_tread_heel bakes its glide — the body table is 5 (fc,Q,g)
rows in NC. TODO pointer left in nock dev/LOG.md.

e33_ledgerdrum.py — the operator accepted e29's cadence "but I'd
like a deeper drum for it." Design claim: the drum belongs to the
TALLY, not to a register — the same hall drum under both dresses
(the night closing is the world's own ceremony wherever you stand).
hall_drum = soft-beater kick 84->38 Hz, drive 1.25, no click, a
50-115 Hz room under it; hits on the word's first step and the
WALK'S LAST STEP (0.40), so the verdict note lands on the bloom.

Three deaths on the way, all instructive:
  - a RATIO ruler saturates against a dark baseline: "low-frac
    >= 3x the wood knock" demanded > 1.0 (the knock is already
    0.60). Depth ratios belong to the centroid (x0.05 measured);
    fractions get ABSOLUTE floors (0.99 >= 0.9).
  - the drum's first cut (drive 1.6, f1 40, room to 420 Hz) put
    its 3rd harmonic at 120 Hz — INSIDE e29's beating band — and
    buried flame's landing (x6.2 -> x1.4). Purify the fundamental
    (drive 1.25, f1 38: 3rd harmonic 114 < band floor) and darken
    the room (50-115 Hz).
  - even purified, a landing-time hit's 38-53 Hz tail leaks
    through the ruler's 2nd-order band edge (~20 dB at 1.7 oct)
    into the measurement window: common-floor dilution again
    (still x1.4). The DESIGN fix beat the ruler fix: move the hit
    to 0.40 — flame x3.9, lightning x8.7. Also: a common
    (verdict-blind) drum bus still breaks onset rulers through
    detector NONLINEARITY — subtract the known common track
    before measuring the pair (37.8 ms false spread -> 0.5 ms).

All rulers pass: deeper (centroid 62 vs 1224 Hz, low-frac 0.99),
minimal pair 0.5 ms both dresses, beating x3.9/x8.7, close < alarm
per dress. Render sent: e33_ledgerdrum.ogg. The cadence is now
OPERATOR-SHAPED end to end; integration recipe: e29's word tables
+ CADENCE_LEVEL + hall-drum synth (one voice, tally-owned) into
sfx/tally per the cycle-65 entry, drum constants NC-side
(DRUM_HITS as beat offsets, DRUM_LEVEL).

## 2026-08-15 — session 32: the wanderer's register (NOCK music, dread pole)

e32_wanderer.py — the second ruled mood pole (Diablo II /
Dishonored), to stand in the operator's A/B against e31's noir
spy. Tristram's lesson taken as RUBATO (a wandering 12-string owns
its own time — no BPM anywhere in the file), Dishonored's as the
FLOOR (a breathing dark that never lifts). One-system thesis
holds: gut string wander with the 12-string octave course
(+12 doubled, 0.55 amp, 14 ms behind, seeded cents — the shimmer),
over a dark D pad + the institution's own loop-quantized 96 Hz
line + wind through a loop-quantized slow lung. Landings
pentatonic, Bb passes for the gothic lean, E untouched.

New ruler earned: RUBATO IS MEASURABLE WITH A POSITIVE CONTROL —
search every uniform grid (period 0.25-1.3 s, circular-mean phase)
against measured onsets; the wander's best residual 26.1 ms
(want >= 25) while the SAME search on e22's lightning melody (the
on-grid control) finds 0.1 ms. A no-grid claim without a control
would be unfalsifiable. Floor: min/median 0.76, env CV 0.09
(between the hum's dead 0.06 and fire's 0.59 — a lung, not a
flicker). line_lock 96.0 Hz prominence 2.7e5. Home x20.1. Seam
p91.6.

Verdict: CANDIDATE (operator taste gate — the A/B against e31 is
the real ruling). Renders sent: e32_wanderer.ogg (loop + first 8 s
again), e32_wanderer_bare.ogg. Integration shape if ruled in:
WANDER table (t, midi, dur, amp) + grace dict NC-side, the pad and
lung from music.gd's existing padsynth/drone plumbing; rubato
means the loop needs no beat clock at all.

## 2026-08-15 — session 31: the spy's register (NOCK music, noir pole)

e31_spyglass.py — the operator ruled on e28's render: the shipped
registers read as "plucking guitar strings one at a time... too
lifeless," and gave two mood poles (TF2 Spy 60s-noir + high-fantasy
twist / Diablo II + Dishonored). This session takes the noir pole,
with a thesis that keeps the register system ONE system: the mood
is built from the world's own two timbres — gut string (flame)
walking a swung noir bass, struck glass (lightning) answering high
— so the spy sits anywhere on the tech gradient without a third
instrument family. Noir lives in the WALK: chromatic passing tones
on weak beats only (strong landings stay D-minor pentatonic; E,
the stained verdict pitch class, is never touched), backbeat brush
sweeps, an anticipation stab on the and-of-4, a bar-8 fill leaning
V->i into the wrap. 84 BPM, 8 bars, swing +0.12 beat (85.7 ms).

"Lifeless" was made a RULER, not a vibe: per-designed-note level
CV on the walk 0.248 vs the shipped e22 flame melody's 0.098
(x2.5, want >= 2) — the baseline's flatness is now a measured
fact, and any future mood must beat it. Other rulers: brush pocket
real (on-eighths 12 ms off design, off-eighths +97.6 ms vs
straight grid, design +85.7, both within 15 ms — e29's local
hysteresis onsets); phrase moves without breaking the loop
(half-vs-half envelope corr 0.79 < 0.9, seam rank p62.4); home
stays home (D pitch-class energy x14.6 over the loudest chromatic
passing class, want >= 4).

Verdict: CANDIDATE (operator taste gate). Renders sent:
e31_spyglass.ogg (loop + first half again, seam audible),
e31_spyglass_walk.ogg (bass+brushes bare). If ruled in, the
integration shape mirrors music.gd's loop builder: the walk is a
pluck table like MOTIF (beat, midi, amp), brushes a shaker clock,
answers reuse the glass voice — all constants NC-side. The
Diablo/Dishonored pole is the next session's sketch; the A/B is
the real ruling.

## 2026-08-12 — session 30: the patrol's tread (NOCK guard identity)

e30_patroltread.py — the premise had to be corrected by the code
first: NOCK's guards are NOT silent (g.stepped plays the archer's
step voices at -16 dB, pitch 0.85, faded 0.025 dB/px to a 900 px
cutoff). The real gap is IDENTITY: guards borrow the player's
feet — same voice, overlapping levels — so heard-not-seen, "whose
step was that?" is ambiguous, against the legibility law.

The candidate: the patrol's gait is a LAYER, not a new family.
tread(mat) = a boot-heel of pitch-drop mass (kick 120->48 Hz,
0.16 s) UNDER the floor's own shipped step voice, verbatim. WHO
is spectral weight (survives any distance gain — a level cue
never could); WHERE is inherited by construction (the floor
speaks its own word, already under nock contract).

Measured against the SHIPPED buffers (render_all dump): WHO — at
equal RMS, tread low-band (<250 Hz) fraction x7.6-x2200 the
archer step's per material, centroid x0.03-0.31 (want <= 0.6);
WHERE — ranking materials by centroid gives the same order in
both gaits (wood < carpet < metal < stone; tread ranked above
300 Hz where only the floor speaks); the edge — dressed with the
game's own law at the 900 px cutoff (-38.5 dB), tread peak 0.0102
clears nock's existence floor 0.005.

THREE ruler/design deaths, one lesson: (a) first invented answer
family buried the floor under the heel (all centroids ~100-200 —
power-weighted centroid reads the loudest BAND, and the heel owns
it); (b) a post-heel WINDOW ruler read stone's absence (grit is
spent by 50 ms — the floor answers THROUGH the boot, not after
it; separate by band, not time); (c) the second invented family
still contradicted the shipped ranking from the other side
(metal's 611 Hz ring read dark, wood's knock read bright). The
lesson closing all three: STOP INVENTING WHAT ALREADY SHIPS —
layer over the contract-covered voices and identity is free.

Verdict: shippable recipe, minimal integration: ONE new synth
(the heel) played under the existing step_%d voice in
_guard_noise's stepped hookup; material system untouched.
Render: e30_patroltread.wav (whose-step contrast on stone at
equal level x3, then a 12 s patrol pass under the shipped gain
law). Pointer in nock dev/LOG.md.


## 2026-08-12 — session 29: the ledger cadence (NOCK night close)

e29_ledgercadence.py — NOCK closes a night with tally ticks and no
music; the game's law is audio-as-information, so the candidate is
a closing cadence where THE VERDICT IS THE HARMONY. A MINIMAL
PAIR: clean and stained share every onset and every pitch except
the last — clean walks down and lands ON the tonic (D, the
motif's home), stained walks the same steps and lands on E, a
major 2nd over home, OUTSIDE the world's D-minor pentatonic. One
note carries the whole verdict. Dressing reuses e23's sting
dresses VERBATIM (gut+wood / glass+hum): the night's last word is
spoken in the same accents as its alarms. Level 0.5 — a close,
not an alarm (caught is 0.92).

Measured: the pair is real — onset spread clean-vs-stained 0.5 ms
in BOTH dresses (rhythm carries zero verdict information); every
note within 5.0 cents of design (e23's match-to-design ruler);
RESOLUTION IS AN AM MEASUREMENT, not a pitch label — mix each
final note with the tonic drone at matched RMS, bandpass to the
fundamentals' neighborhood (120-190 Hz), read the envelope's
12-24 Hz beating band (D3 vs E3 beat at 18.0 Hz): stained carries
x6.2 (flame) / x8.9 (lightning) the clean close's beating energy.
Cadence RMS < caught RMS in both dresses.

TWO ruler deaths, both reruns of known killers: (a) the global
onset picker (find_peaks on the envelope derivative) read a gut
pluck's partial-beating swell as an onset — 261 ms of phantom
"rhythm difference" in a pair constructed identical; e27's law
applies at any scale: measure each attack at its own designed
time, in a local window, by hysteresis crossing (derivative
argmax STILL smeared 10 ms on glass when only the landing pitch
changed). (b) unfiltered envelope beating gave clean flame a
false roughness floor (x1.5) — the pluck's own upper partials
beat among themselves (e27 again); bandpassing the mix to the
fundamentals' neighborhood before the envelope read restored the
contrast (0.11 vs 0.68).

Verdict: shippable recipe. In-game: two short words in music.gd
or sfx.gd built from the shipped pluck/strike voices, picked by
the ledger's clean/stained verdict at tally open, dressed by
register_mix at the arch. The stained landing (E over D) is the
information; the tick train stays. Render:
e29_ledgercadence.wav (flame clean/stained, lightning
clean/stained). Pointer in nock dev/LOG.md.


## 2026-08-12 — session 28: the held breath (NOCK full-draw music)

e28_heldbreath.py — the question the tape law never answered: NOCK's
music rides world_pitch down to 0.2x at full draw (cycle 46 ruling,
elegant on paper), but NOCK is MOBILE-FIRST and a phone driver keeps
almost nothing below ~300 Hz. Is the tune still THERE, on target
hardware, at the game's most dramatic instant?

Finding one is a ruler death worth keeping: the obvious ruler (RMS
survival through a 4th-order 300 Hz highpass) says the defect is
imaginary — survival only falls 0.97 -> 0.73, because a Karplus
pluck is mostly harmonics and the phone keeps them. THE DEFECT IS
REGISTER, NOT SILENCE: fundamental-band phone survival collapses
0.0565 -> 0.0028 (x20) along the game's own dilation curve, and the
phone-heard centroid falls 2727 -> 772 Hz (x0.28). The tune doesn't
vanish; it loses its pitch floor and its light — five-times-slow
rumble at the exact moment of the aim.

The candidate: THE HELD BREATH. As the draw deepens, the world's
music recedes on a dB-linear duck (HELD_DUCK_DB -24; -18 measured
x1.8 on the thesis ruler — stage not cleared) and the archer's own
body takes over ON ARCHER TIME, never dilated (the creak
precedent): a heartbeat whose rate rides frac (55 -> 108 bpm), each
thump a 62/52 Hz damped body the phone drops plus a 900-1800 Hz
valve CLICK the phone keeps — the click is deliberately the phone's
share. Thesis measured: at full draw the phone FOREGROUNDS the body,
p99.9 |phone(heart)| = 3.6x p99.9 |phone(ducked slow melody)|
(peaks, not sums — heartbeats are transients, the crest rule; an
RMS comparison flunked an audibly foreground heart at x0.7 by
diluting sparse thumps over silence). Heartbeat honesty: hysteresis-
onset rate within 0.0% of design at frac 0.5/1.0, lub-dub interval
fraction 0.32 exact. Release: ts and gains snap back over 40 ms;
snap-window max |delta| 0.018 vs hard-cut control 0.230 (x12.5
margin) — the world returns without a click.

Verdict: shippable recipe. In-game: keep the tape law untouched
(music.gd pitch_scale as is); add a draw duck on the music bus
(dB-linear in frac to HELD_DUCK_DB) and a heartbeat tick clock in
sfx on real_dt (like the creak), rate lerp 55->108 by frac, fading
in sin(frac*pi/2). VFX pairing candidate: the existing strain
wobble is the sight cue; the heart is its sound. Renders:
e28_ab_fulldraw.wav (shipped mush vs held breath, same scale, no
per-file normalize), e28_drawarc.wav (rest -> full draw -> release).
Pointer left in nock dev/LOG.md.


## 2026-08-12 — session 27: the borderland (NOCK mid-gradient music)

e27_borderland.py — the question behind nock's self-gated music
item (2): what should the tune do HALFWAY between the registers?
The in-game crossfade plays both loops at 50/50 — but flame is
swung +64 ms and lightning is dead on grid, so every swung note
arrives TWICE. Measured (each voice on its own bus at its own
designed time): 10/10 swung positions get both attacks at ear
parity (within 12 dB), 64 ms apart by e22's own banked tape. THE
FLAM IS REAL — the naive middle is not a blend, it is a rhythm
defect. Verdict on the self-gate: the middle register EARNS ITS
KEEP.

The candidate: THE BORDERLAND PLAYS LIGHTNING'S TIME WITH
FLAME'S HANDS — the same gut plucks, dead on grid (median |dev|
2.4 ms), dead in tune (worst +2.6 cents by parabolic-interpolated
narrow-band peak), no pan wander, over a floor keeping both
fires: thinned stove + faint hum, envelope CV 0.06 — strictly
between lightning 0.05 and flame 0.59, though the margin to
lightning is thin (the borderland floor is nearly institutional;
by design, but barely measurable). Seamless (seam p88.8). Walk
law for the game: squared-cosine borderland bump (half-width
0.35) over the cos/sin ends, power-normalized — flame ->
borderland -> lightning as one continuous walk.

THREE ruler deaths, one worth framing: the single-bus two-attack
flam detector died TWICE (8 ms envelope resolved pluck AM ripple
as attacks; 20-30 ms smoothing still read a "flam" in a SOLO
gut pluck — its slightly inharmonic partials BEAT, putting a
real secondary swell 40-80 ms after its own attack). No amount
of smoothing separates "two instruments in a pocket" from "one
string breathing" on a mixed bus. The flam lives across TWO
buses by construction — measure each voice's attack at its own
designed time, per bus, at ear parity. Also: raw FFT argmax at
110 Hz is a 5.3-cent bin — parabolic interpolation or the ruler
flunks an honestly tuned string on resolution (pluck() has true
fractional delay; the string was never out of tune).

Verdict: shippable recipe for music.gd whenever nock promotes
it: bake a third loop (same MOTIF, plucks on grid, no drift,
stove x0.22 + hum x0.025 bed), three-way power-normalized mix
with the bump width as an NC constant. Pointer in nock
dev/LOG.md.

## 2026-08-12 — session 26: chalk (NOCK sigil marks)

e26_chalk.py — the last cue family on the DESIGN list: the
chalk-sigil mark. The idea: THE MARK IS WRITTEN, NOT STAMPED. A
stamp is one event — any glyph, same thud; a written mark
carries its glyph in the sound. Each sigil is a fixed stroke
sequence and the stroke RHYTHM is the glyph's identity: loop
(checkpoint spiral — one long sweep, two short closes), coin
(peddler's cross — two quick equal cuts), ward (four even
pickets ending on a slow drag). Inside each stroke the hand is
audible: a velocity bell the chalk voices as brightness (the
lowpass corner rides the bell, 900 + 4200v Hz), and squeak
appears only at the deterministic upward crossing of 0.6 vmax —
the failure mode of a real hand, sparse, texture not signal.

Measured: counts exact (3/3, 2/2, 4/4); rhythm intervals within
16 ms of design; the three designs pairwise APART (> 60 ms
someplace); every stroke's mid-third centroid beats both end
thirds (the bell survives the render); loud-squeak fraction
0.06-0.08 of written time (< 0.25).

Two onset rulers died: (a) derivative peaks (the sting ruler)
landed 0.1-0.17 s late and doubled — a stroke is a SLOW SWELL,
its max rise rate sits mid-crescendo and chalk grain gives the
derivative several humps; a written mark's onset is where energy
BEGINS: hysteresis threshold crossing (the stone-skitter ruler),
8%/3%. (b) then intra-stroke grain dips (5 ms holes) re-armed
the hysteresis — 25 ms smoothing bridges them. And the absolute
crossing lag is detector bias, identical every stroke: rhythm
claims must compare INTERVALS, where the lag cancels — which is
what rhythm is.

Verdict: shippable recipe. In-game sigils (checkpoint chalk,
coin panel) currently share stamp-like blips; the candidate is
stroke-written cues where stroke count/rhythm = which sigil,
built as short stroke buffers played on a clock like the relight
telegraph (the tick-train pattern is already house grammar).
Pointer in nock dev/LOG.md. Cue list: COMPLETE — every family on
the DESIGN list now has a measured loam prototype.

## 2026-08-11 — session 25: the death of a hum (NOCK shatter)

e25_shatterhum.py — the lightning fixture's shatter, prototyped
as what connects the living 96 Hz hum to the silence after. The
idea: THE INSTITUTION'S TONE ONLY GOES FLAT WHEN YOU BREAK IT.
All of lightning's language is precise (e22/e23: grid-locked,
cycle-quantized, dead in tune) — so a thrown switch ends the hum
CLEANLY, inside a cycle, while a SMASHED tube loses its mains
lock and dies badly: the hum survives the crash for a moment and
glides flat, phase-continuous (frequency integrated into phase,
so there is no seam at the crash — the same hum, losing its
grip), tau 0.18 s, under a decaying rain of glass whose event
RATE is the instrument again (e24). The glide is the one detuned
thing lightning ever says, and only when the player has done
something loud and permanent.

Measured, each claim on its own bus: the lock holds (every
pre-crash window within 0.1 cents of 96.0 — parabolic-
interpolated peak); the death is monotone (81.6 -> 58.4 -> 42.4
-> 31.3 Hz, 16.6 semitones, every voiced window falling); the
crash is glass (power centroid 5290 Hz); the rain thins (7 -> 6
-> 1 ticks per 0.3 s window, one detection pass binned after);
and two deaths on ONE ruler — hum holds 0.709 s of energy after
the smash vs 0.021 s after the switch cut (34x contrast).

Two rulers died: (a) the pitch track invented NEGATIVE
frequencies (-94, -158 Hz) — parabolic interpolation at the band
edge fabricates peaks once the glide falls below what the band
can hold; the track needs the ruler's own floor (break below
25 Hz), not just an amplitude gate. (b) "the clean off is clean"
asserted the coda's post-cut tail was zero — a tautology, it
measured zeros written by construction (e24's silence lesson in
a new hat). Reframed as CONTRAST on the same ruler both sides:
hold-time after the event, smashed vs switched. And the clean
window must STRADDLE the ramp — starting at the cut sees only
the zeros again.

Verdict: shippable. In-game the smash already has its crash
(cycle 35's loud key ceremony); the candidate is the dying glide
as a new voice under it — and the CONTRAST is free lore: the
switch verb already kills the hum ambience instantly (gated on
lit), which e25 now rules is correct and load-bearing, not an
omission. Pointer in nock dev/LOG.md.

## 2026-08-11 — session 24: the water cycle (NOCK douse / relight)

e24_watercycle.py — the douse and the relight prototyped as one
lifecycle, because in NOCK they bracket the same thing: the
stealth window. The flame is a character; the water arrow only
kills it for a while. Design thesis under test: THE PAIR MUST
MEASURE THE WINDOW FOR THE EAR. The douse ends in genuine
silence (the prize is audible as absence); the relight
TELEGRAPHS — flint scrapes are a fixed-length countdown before
the whump brings the light back, so a player who hears tick one
knows exactly how long their darkness has left. Telegraph length
is grammar: 0.90 s, never varies.

One continuous ~10 s take over a faint night bed (96 Hz + air —
e20's world again): steady crackle -> splash + steam bloom
(crackle dies mid-hiss) -> the dark window -> three flint
scrapes -> catch whump (85 Hz down-chirp bloom, no click) ->
crackle reborn. The rebirth crackle is hand-rolled with RATE as
the instrument: seeded exponential gaps against an interpolated
rate (0.8 -> 6 events/s), because the whole story is an event-
rate arc (6 -> 0 -> ramp -> 6) and the ruler must count what the
code varies.

Measured, each claim on its own bus: steam POWER centroid cools
x2.2 (5742 -> 2582 Hz, want > 2); the window is real (lit rms
12x the dark gap, want > 8); telegraph 3 scrapes, first-scrape
-> whump 922 ms vs 900 design (within the 30 ms gate); rebirth
tick count per 1.4 s window strictly rises 1 -> 4 -> 7.

Three rulers died first, all on standing rules: (a) a
differencing highpass after the gliding lowpass was a +6 dB/oct
shelf that ERASED the glide — centroid pinned at 13 kHz
regardless of corner; glide + fixed 300 Hz butter instead. (b)
the dark gap measured as digital zero, ratio 1/8,579,315 — a
lying ruler; silence must be measured against a floor that
exists, hence the night bed. (c) rebirth counted [5,5,2]: the
40-200 Hz rumble shared the tick bus AND the threshold was per-
window (the per-call normalization sin) — rumble wobble out-
peaked sparse early ticks. Split ticks/rumble onto separate
buses, one detection pass, one threshold, bin afterward.

Verdict: shippable recipe for NOCK. In-game, the douse hiss
already exists (M4.2) but has no cooling glide and no telegraph
exists at all — the guard relight is currently instant-ish with
a generic cue. Integration would be: NC.RELIGHT_TELEGRAPH_S as
grammar, scrape tick train on the guard's relight duty, whump on
light restore, and the crackle rate ramp on the pool's rebirth.
Pointer in nock dev/LOG.md.

## 2026-08-11 — session 23: detection stings in two accents (NOCK)

e23_stings.py — the cue list's "sting per awareness state" meets
the e22 registers, and the law-2 tension (stings are GRAMMAR:
contract words, identical everywhere) resolves cleanly: THE
GESTURE IS THE WORD, THE REGISTER IS THE ACCENT. Three escalating
words in D minor pentatonic — notice (two notes, a rising
question), hunt (three circling), caught (four falling to a low
slam) — each dressed twice: flame (gut pluck + wood knock) and
lightning (struck glass + a 192 Hz hum swell leaning in as the
word lands). Unlike the e22 melody, stings take NO cents drift
and NO swing even in flame dress — the alarm is the one thing
the margins say precisely.

Measured: gesture identity holds across dresses — onsets within
6 ms of design, pitches within 10 cents (grammar HOLDS); rms and
duration rise strictly notice < hunt < caught in both dresses;
the accent is real (lightning tail/peak >2x flame's — glass and
hum sustain, gut dies).

THREE pitch rulers died getting there, each on a standing rule:
open-band HPS octave-erred (+1196/+2398 — bright even harmonics
outvote the fundamental through the product); band-limited HPS
then lied +237 cents about GLASS — HPS assumes HARMONIC spectra,
and glass's inharmonic 2.32x mode masquerades as the 2nd
harmonic of a false fundamental at 1.16x (band-edge clamp made
it look consistent). Match-to-design needs no harmonic model:
plain spectral peak within +/-15% of the designed fundamental,
correct for string and bell alike. New standing rule: HPS IS FOR
HARMONIC SOUNDS — never point it at a bell.

Verdict: shippable as NOCK's awareness cues whenever the game
promotes its detection blips to musical stings — the in-game
recipe would dress by NC.register_mix at the guard's x (the
alarm speaks the accent of the ground it stands on) while the
gesture stays fixed by law. Pointer updated in nock dev/LOG.md
(music TODO item 3 recipe; still self-gated).

## 2026-08-11 — session 22: the two registers (NOCK music)

e22_registers.py — first NOCK music sketch: the magitech gradient
as ONE identity re-clothed, not two tracks. The same 22-note
D-minor-pentatonic motif, same 75 BPM, same 8-bar seamless loop
length, walked from one end of the world to the other:
- FLAME (the margins): the motif on gut-damped Karplus pluck
  (damp 0.5, fingertip-soft excitation) with seeded ±8-cent
  per-note drift, swung 0.16 with a thinned euclid(7,16) shaker,
  marimba-wood answers, fire-crackle bed. Warm master (4.8k).
- LIGHTNING (the institution): the SAME motif note for note on
  struck glass two octaves up — dead on the grid, dead in tune —
  over a narrow-band PADsynth D drone and a cycle-quantized 96 Hz
  mains hum (e20's night tone: the institution's tone was under
  the margins all along). Bright master (9k), nothing loose.
Because key/tempo/length/phase agree, the in-game system is a
POSITION CROSSFADE: two synced loops, the mix knob tied to where
the level sits on the tech gradient. The demo render does exactly
that (8s flame / 8s crossfade / 8s lightning).

Measured (two rulers died honestly on the way):
- seam p97.1 / p89.8 — both clickless.
- grid deviation vs each note's DESIGNED time: flame's swung
  notes +63 ms (design +64), everything else 3-4 ms. The first
  swing ruler measured onset pair-ratios and assumed even eighths
  the motif never had — compare to the design, not to a meter.
- floor breathing (envelope CV): fire 0.59 vs hum 0.05 — the
  fire never stops breathing, the hum never breathes. Voice-bus
  rulers failed first: POWER centroid lost to the standing
  transient rule (a pluck's attack noise out-powers any steady
  line — glass NEVER wins on centroid), and note-sustain lost
  because struck glass is percussion too. The steadiness axis
  lives in the FLOOR, not the voice.
- the floor's identity: bed centroid 10.5 kHz broadband noise vs
  137 Hz line; hum-lock FFT peak 96.0 Hz exact with prominence
  >1e6 vs the fire's incidental x8 in the same band.
- loudness: institution presses x2.4 rms harder BY DESIGN — the
  stakes gradient as pressure, not just color.

Verdict: the one-motif crossfade is the shippable shape — the
gradient reads as the same tune losing its human hands, which is
exactly the game's fiction (harnessed lightning = harnessed
music). Worth a second sketch someday: a middle register (the
crossfade point as its own mood) and a detection-sting overlay
per awareness state in each register's vocabulary. Integration
pointer left in nock dev/LOG.md.

## 2026-08-11 — session 21: arrival by material (NOCK SFX)

e21_arrivals.py — the arrow's other end. The idea under test: the
four material arrivals (stone / wood / metal / body) read as ONE
vocabulary when they share a single excitation — a 3 ms broadhead
contact snap — and differ only in the resonator body it drives.
That is NOCK's uniform-grammar law done in audio: same word,
material timbre. Each material carries one measurable signature:
stone a 4-hit bounce train (no bite — the shaft skitters), wood a
deep thunk with the stuck shaft's 64 Hz cantilever quiver, metal a
long detune-beating lamp-tube ring (custom LAMP_T table — ANVIL's
ratios but long ring multipliers; smithy anvils are damped, thin
fixture steel is not) plus the shaft's drop-off tick, body a dark
thump + cloth breath with no modes worth the name. Impact speed
scales the family like loose_voice scales the launch: velocity
buys level AND hardness (knock + bright), so a soft lob arrives
darker, not just quieter.

Render: e21_arrivals.wav (14.1s one-shot: full-power row then
soft-lob row, 1.4s spacing, light exterior tail).

Measured, each claim on its own bus, explicit gains (strike()
peak-normalizes per call — the standing per-call-norm rule):
- centroid bright pair {stone 3792, metal 1297} > dark pair
  {wood 1137, body 109 Hz}. The first draft claimed a full
  ordering metal > stone and the ruler refused: broadband contact
  noise out-brightens any ring. BRIGHTNESS SEPARATES THE PAIRS;
  RING TIME SEPARATES STONE FROM METAL — the ear tells metal by
  sustain, not tint. Worth keeping as a design rule.
- T30 ring time (40 ms past the contact peak — measured at the
  peak, a knock's crest hands every material the same verdict):
  metal 0.428s = 1.7x wood 0.246 > body 0.134 > stone 0.049
  (dry stone doesn't ring; its energy lives in the bounce train).
- crest: stone 28.9 highest, body 6.2 lowest.
- metal beat 4.7 Hz vs design 5.2 (f0 900, 10 cents) — after two
  ruler fixes: bandpass the FUNDAMENTAL PAIR (every detuned mode
  beats at its own delta-f; the mixed bus is a committee) and
  detrend against the decay ramp, not the mean (the exponential
  slope is the loudest "low frequency" in any ring envelope).
- stone bounces: 4 envelope peaks (impact + 3 rebounds, designed).
- soft vs full: rms -3.5..-5.5 dB, centroid x0.41 stone / x0.72
  wood / x0.78 metal / x0.99 body — flesh has no hardness range,
  so the kill word only quiets, never re-tints.

Verdict: the shared-snap + body-swap structure is the shippable
shape — NOCK's in-game arrive_* family already exists but was
tuned by ear; e21's fingerprints (pair split, ring-time margin,
beat, bounce count, velocity-buys-hardness) are an auditable spec
for upgrading it. Integration pointer left in nock dev/LOG.md.

## 2026-08-11 — session 20: the draw (NOCK SFX)

e20_thedraw.py — first NOCK cue prototype: the signature verb. The
idea under test: the draw cue is not a creak, it is the WORLD
dilating audibly. Archer-time sounds (stick-slip fiber ticks whose
density AND pitch ride the draw fraction, a bowed-wood limb groan,
a hemp tension gliss) stay at speed while the night bed (fire +
wind + a 96 Hz night tone) tape-slows underneath on the eased
dilation curve (1 - 0.8*frac^1.6, floor 0.2x — the NOCK ruling)
and whip-snaps back in 0.35s at release. Slow-motion fire reads
as the flame-lit-margins register doing the slomo's work for it.
Release = Karplus twang + WOOD limb thunk + resonator-swept whoosh
(3k -> 350 Hz); overheld hold gets accelerating tremor AM plus a
thin 2.2k whine.

Two renders: e20_draw_full.wav (10.5s: bed / build / overheld
strain / loud flat release / afterglow) and e20_draw_soft.wav
(6s: the frac-0.2 lure lob — a handful of ticks, barely-dipped
bed, low quiet whoosh).

Measured (each claim on its own bus — the first tick count ran on
the mixed creak bus and counted groan wobbles, 15 vs 19; routed
the ticks to their own bus and the truth appeared):
- bed night tone 96.0 Hz before the draw, 19.4 Hz mid-hold
  (designed 19.2 — varispeed pitch honesty).
- ticks/0.5s: 2 early build -> 6 late (hazard design ~5.5x; sparse
  counts, direction and magnitude read).
- whoosh POWER-weighted centroid: full 2217 Hz vs soft 813 Hz =
  2.73x — draw power audibly IS air speed.
- strain tremor, late hold: 8.0 Hz envelope peak (design ramp
  4 -> 9; the 1s window averages the tail, ~7.9 expected).
Mix lesson (segment profile as the ruler): first master let a
random fire crackle (0.55 peak) out-shout the release (0.29) —
the climax must own the piece; fire trimmed 0.55 -> 0.42, release
raised, now release holds both global peak (0.43) and top segment
rms, and the arc rises bed 0.035 -> strain 0.055 -> release 0.057.

Verdict: the dilation-bed trick is worth shipping — it makes the
draw legible with eyes closed, which is the pairing rule's audio
half for the whole slomo system, not just one cue. The tick
family and twang+whoosh scale naturally by frac (game passes one
number). Integration pointer left in nock dev/LOG.md.


## 2026-08-09 — session 19: ear candy

e19_earcandy.py — three jars, no concept, just pleasure:
- stinger (7.8s one-shot): the podcast-ident recipe. Marimba rise
  through F major penta (glass doubling +12), landing on glass F5
  detuned 2.5c so it beats against itself; two bowed-glass swells
  peak just AFTER the landing (bell hands off to pad); pentatonic
  sympathetic bank shimmers under everything; 2.8s FDN tail.
- clicks (13s one-shot): the click cabinet. thock = body mode +
  contact + sub thump (the desk is a layer); pen press/release
  pair (release lower + softer); bubble pops incl. a rising
  triplet; camera shutter (mirror slap + two wood ticks); marble
  bounce train, intervals *0.78/hop, pitch stiffening 1%/contact.
  Bounce ratio measured from the RENDER: 0.777 vs 0.780 designed.
- soothe (32s seamless loop): creamy PADsynth F2+C3+F3 breathing
  at 7.5 breaths/min — 4 whole cycles/loop so the seam is phase-
  exact, and the envelope FFT confirms bin 4 dominates. Glass
  armonica bowls on the penta, sub F1 under the same breath, four
  music-box sparkles into the ping-pong. seam p64.6.

Width lesson re-confirmed on the soothe: level-panned bowls left
the loop at corr +0.778 (>250 Hz); moving them to ITD placement
(arrival time, e16 recipe) + wider pans opened it to +0.379 with
nothing else touched.

## 2026-08-04 — session 18d: The Alembic (capstone)

songs/the_alembic.py — 76.2s, E minor @63, 20 bars, the three
worlds in one seamless loop: simmer (cauldron + creamy pad,
freq-shifted +2.6 Hz so the whole room is slightly wrong) ->
work (E3 anvils 3:2 vs escapement, bar stock humming, boiler
chuff) -> pour (plink polyrhythm + glass stirs, anvils lighter)
-> transmission (ring-mod vocalise @113 Hz carrier, theremin
swoop, grain debris) -> settle (plink echoes, steam sigh, back
to simmer). Ratchet winding-bursts mark every section seam; the
transmission's ping-pong tail wraps the loop and haunts bar 1.

The arc, measured per section: 0.085 / 0.124 / 0.133 / 0.145 /
0.088 rms — rises to the transmission, settles for the wrap.
Plinks -3c, taraf 3.57x tuned/detuned, seam p82.4, width +0.49
with centered soloists by intent. First draft buried the voice
under the pad (0.028 vs 0.049 in its own section — full-loop rms
understates sparse buses by sqrt(duty), scale before comparing);
climax now wins its bars.

## 2026-08-04 — session 18c: the transmission

e18 "The Transmission" (32s @60): the alien palette measured.
- Ring mod on a sung vocalise (Radiophonic trick): dry C4
  fundamental suppressed to 0.05x, sidebands land at exactly
  f +- 111 Hz at ~0.5x each. The formant MOTION survives the
  destroyed harmonic series — it still speaks, but it's metal.
- Bode shifter on an airy 'oo' pad: partial 2 measured moving
  +4.0 Hz for a +3.69 Hz shift (within the 0.5 Hz bin) — every
  partial moves the same ABSOLUTE amount, the sheen no detune
  can make.
- Theremin answer: pure sine whose f0 steps land BETWEEN the
  keys (float midi), 0.38 s portamento kernel — the swoop is the
  melody, vibrato arrives late.
- Grain debris: the sung phrase scattered +12/+19, shifted with
  the pad so the sparkle disagrees with itself the same way.
Sub trimmed from loudest-thing-in-the-piece (0.071) to floor
(0.046); soloists centered by intent, width +0.45 from pad and
debris. seam p68.6.

## 2026-08-04 — session 18b: the forge

e17 "The Forge" (25.7s, F @112): Rheingold by way of the boiler
room. Master anvil (F3) on the dotted-quarter cycle = 3:2 against
the clockwork escapement's straight eighths (tick-tock alternates
pitch AND pallet/pan); apprentice answers off-cycle on C4/F4;
ratchet winding-bursts (accelerating rim trains) at phrase seams;
boiler chuff + steam vents; all metal in ir_tank. seam p84.7.

The taraf saga — three wrong rulers before a right one:
1. First "sympathetic bank" measured identical tuned vs detuned
   (1.00x): I had passed mix=0.0, which returns the DRY signal —
   I was measuring the input twice. (The 477.6 Hz "hum" was the
   anvil bus itself. mix is wet/dry, 1.0 = wet only.)
2. Fixed, driven from the TANK bus: ratio only 1.4x — the tank's
   11-mode wash is spectrally dense, so a string at ANY tuning
   finds something to resonate with. A detuned-control comparison
   needs a SPARSE drive spectrum to mean anything.
3. Driven from the DRY anvils: 3.81x tuned/detuned, loudest
   partial 474.6 Hz vs the anvil ring's 474.9 — the bar stock
   sings the ring itself. Physically nicer too (the stock hangs
   by the anvils; the room comes after).
Also: ITD placement comb-filters the MONO SUM that sympathetic()
drives from — arrival-time stereo can silently rob a downstream
mono-keyed processor. Same family as the duck-bus lesson.

Bar stock tuned to what the anvils RADIATE (fundamentals + 2.72x
rings, float midi), not to F pitch classes — first draft's meter
caught 475 Hz dominating a bank tuned to F's.

## 2026-08-04 — session 18: the potion (bubbles, and an anvil)

Director's brief for the new season: space alien sci-fi, bubbling
potions, industrial workshop (Rheingold hammers by way of the
Spirited Away boiler room); polyrhythms, timbre words (airy,
swoopy, creamy, crisp), stereo space without gimmicks.

New instruments:
- texture.bubble()/bubbles() — van den Doel liquid sounds: damped
  sine at the Minnaert resonance with the signature RISING chirp
  f(t) = f0(1 + 0.1 d t), d = 0.13 f0 + 0.0072 f0^1.5. Measured
  within 1% of prediction at three sizes, and the rise ratio is
  SCALE-INVARIANT (~1.41, +590 cents: ring time ~ 1/d cancels
  chirp rate ~ d) — why mixed sizes read as one material.
- modal.ANVIL — designed, documented as such: fast clank
  fundamental under a tight inharmonic face-mode pair
  (2.72:2.736) with the longest ring. Measured: ring t60 3.4x
  clank, beat 3.0 Hz vs 3.12 designed.

e16 "The Potion" (30.5s, E minor penta @63): bubbles() cauldron;
creamy pad (steep-tilt PADsynth through slow chorus); two plink
voices — bubble() as pitched music box, damp < 1 — in euclid(7,16)
vs euclid(5,12) polyrhythm through ping-pong tape echo; two
bowed-glass stirs. Plinks tune themselves the winds' way: render
one, measure the onset (chirp reads +55c sharp of f0), pre-
compensate. Final -3c. seam p96.7.

Stereo lessons, both new metrology:
- Level pan keeps a mono blip lag-0 correlated at ANY pan; what
  decorrelates a POPULATION is time-of-arrival — ~0.9 ms far-ear
  ITD + one opposite-wall bounce (the pot's acoustics) took the
  fizz field from +0.78 to +0.03. ITD on the plinks took the mix
  from +0.54 to +0.34.
- The correlation meter has the same leak the duck meter had: a
  2nd-order 250 Hz HP lets the LOUD centered glugs (70-220 Hz,
  physically the pot's one throat) dominate and report the wide
  fizz as mono. Judge width per material AND per band: the fizz
  field measures above the glug band (4th-order, 500 Hz).

## 2026-07-31 — session 17: the front door (pre-digest housekeeping)

README rewritten to index all sixteen modules and — more
importantly — to enshrine the night's metrology rules ("verify by
numbers, and distrust the ruler": bus-not-mix, HPS pitch,
power-weighted centroids, crest for transients, norm=False for
comparisons, per-material width, secant tuning, quantize test
inputs). dev_smoke.py: every module imported and exercised — 54
checks, 0 failures, 1.3s. The library's health is now one command.

## 2026-07-31 — play session 16: texture.py, weather from statistics

Procedural nature after Farnell's Designing Sound: rain (Poisson
chirp-droplets over the averaged far wash), wind (noise through
random-walk wandering resonances — walks close their loops for
seam safety), fire (crackle + rumble surge + hiss flares). Two
fixes with lessons: a CLOSED walk doesn't make a seamless
resonator — the filter STATE must warm on the tail too (wind seam
p99.2 -> p93); and droplet audibility is a CREST-FACTOR question,
not an energy question (1.1x energy but 4.9 -> 9.6 crest — 
transients live in peaks, not sums). e15: rain -> wind -> fire
triptych, crossfading.

## 2026-07-31 — play session 15: the gong (modal.py grows a tam-tam)

Real gongs BLOOM — nonlinear mode coupling (Chaigne/Touze plates)
cascades strike energy upward, shimmer arriving AFTER the thud.
gong() fakes the cascade honestly: the low-mode bed DIPS as the
shimmer envelope rises (energy visibly moves), strike-bend
settles flat, dark thump.

Double metric lesson: LINEAR-magnitude centroid lied in both
directions (bin-count bias made the silent tail read 'bright');
POWER-weighted centroid then exposed that the first synth had no
bloom at all — the fix had to be physics (the transfer), not the
ruler. Bloom now verified across seeds: centroid rises into ~1s
then falls (182->226->64 shape).

e14: three gongs (G1/D2/G2) into the FDN tail.

## 2026-07-31 — play session 14: rhythm.py, the composer's graph paper

euclid (Bjorklund, verified against Toussaint's canon: 3/8
tresillo, 5/8 cinquillo, 5/16 bossa, 5/12 bell — counts exact,
max-evenness proven), rotate/swing/prob/onsets, and SCALES — the
interval tables loam has been hardcoding per-song (hijaz, hijaz
kar, nahawand, kurd, modes, pentatonics) with scale_notes and
quantize_to. e13: five kit voices each on their own euclid
(5/16, 3/8, 7/16 swung, 11/16, 2/5 cross-meter) with a Hijaz Kar
psaltery walk on euclid(5,12) — onset counts verified per bar.

## 2026-07-31 — play session 13: "The Long Stair" (capstone)

96s seamless piece playing EVERYTHING from tonight at once: the
barberpole falls forever under a padsynth bed (the descent that
never arrives), church bells through the ir_bone convolution mark
the depths, psaltery on tape echo, ladder-filtered pulse bass,
sparse kick ducking every bus, the voice sings its sentence and
rests, the ney replies with one overblown peak, and the taraf
hums back at all of them. FDN room on the melodic bus, limiter
on the master.

First-take render: seam p27, sectional rms 0.151/0.176/0.173/
0.162 (breathes, doesn't lurch), peak 0.900. Thirteen modules,
one instrument.

## 2026-07-31 — play session 12: lofi.py, age as an effect

gramophone() / worn_tape(): wow+flutter (cycle-quantized time
warp), Poisson crackle (fine dust + rare big pops), surface hiss,
soft-edged dropouts, 60 Hz hum, the bandwidth funnel with a horn
resonance, tanh squash.

Parameterization bug worth remembering: first draft specified
wobble depth as POSITION (seconds), so pitch deviation scaled
with wobble RATE — the fast flutter swung 3x harder than the slow
wow (161 cents of warble!). Depths now mean PITCH fraction;
position amplitude = depth/(2*pi*rate). Measured after: 25.6c p2p
on a 21c design. Pop counter needed a 15ms refractory window (one
oscillating snap = dozens of threshold crossings; 15.7/s read on
a 1.2/s design).

e12: the night's own vocalise, dry for the statement — then the
needle drops. Band funnel measured 34 dB.

## 2026-07-31 — play session 11: shift.py, sidebands and the staircase

Bode frequency shifter via circular FFT Hilbert — every partial
moves by the same Hz (not ratio): harps become bells, voices
ghosts. Ring mod alongside. Seam-craft-native: the analytic
signal is circular by definition, shift quantized to whole
cycles/loop. barber() = feedback delay with a shift inside the
loop: every echo returns a few Hz higher — the endless staircase.

Verified EXACT: 220/440/660 +37 -> 257/477/697 with the original
at -240 dB; ring 440x100 -> 340/540; psaltery stem 587/880 ->
631/924 (+44.0 on the nose, checked on the BUS per the rule —
the first check read the mix and saw only the pad). One test bug
worth keeping: an unquantized INPUT chord failed the barber seam
check at p100 — the module was innocent; quantize test inputs too.

e11: psaltery dry then ghost-shifted over a forever-rising
barber wash. Seam p41.

## 2026-07-31 — play session 10: convolution spaces, rooms that don't exist

space.py grew synthesized impulse responses + convolution:
ir_room (4-band noise, per-band decay — highs die faster, early
reflection sparks), ir_tank (the decay RINGS: inharmonic decaying
sines over a short wash), ir_bone (MARROW's own: 900-3200 Hz
cavity chitter, dense early cluster), convolve_loop (CIRCULAR
convolution — seamless by mathematical construction, the most
elegant loop-safety in the library: no warming, no wrapping code,
the DFT does it), convolve_tail (linear, for one-shots).

Verified: Schroeder band-T60s land on design (2.09 vs 2.0 mid,
1.15 vs 0.9 high); tank tail spectral contrast 10,000x (rings);
bone band contrast 23.7 dB; circular seam within distribution.
e10: one bell + psaltery phrase through all three rooms back to
back — tail rms/centroid separate them numerically (cathedral
.0052/2563, tank .0035/1827, bone .0024/3016).

## 2026-07-31 — play session 9: voice.py, the hermit hums

Source-filter singing (Klatt lineage): Rosenberg glottal pulse
(flow DERIVATIVE for brightness) with accumulated phase — pitch
glides can't click — plus jitter, shimmer, delayed vibrato, and
aspiration breathed through the same formant bank. Parallel
resonators recomputed per 128 samples so vowels MORPH mid-note
(diphthongs). sing() renders a legato vocalise from
[(midi, beats, vowel-or-morph-pair)].

Verified: F1/F2 land 698/1112 vs 730/1090 targets; pitch +8..+18c
across a line; vibrato 95c p2p (spec 70 + jitter — operatic,
kept); portamento max-delta clean. e09: the voice SINGS a
sentence, rests, answers — and the RMS contour proves the grammar
(0.186 statement / 0.032 rest / 0.202 answer / 0.031 wrap) — the
standing melody rule, verified numerically for the first time.
The voice also drives the taraf: the room hums back.

## 2026-07-31 — play session 8: analog.py, edges and the ladder

polyBLEP saw/pulse (Valimaki band-limited edges), supersaw (7
detuned saws, JP-8000 layout), Huovilainen-style Moog ladder
(4 cascaded tanh one-poles, feedback, per-sample scalar loop at
a fine 0.05s per rendered second).

Verified: polyBLEP drops the alias floor -16.7 -> -41.4 dB;
ladder self-oscillates at res>1 with the squeal near cutoff (454
vs 440); slope measures ~17.5 dB/oct vs the ideal 24 and the
resonance peak sits ~7% flat of nominal — the tanh stages soften
and warp exactly like hardware under drive, documented as
character not bug. Supersaw center voice at equal gain was
re-correlating the channels (bus 0.81); quieter center + near-
zero bleed -> 0.38.

e08_acid: 15s acid line (pulse through swept ladder, accents,
filter opening over the loop) + supersaw pad Dm->Bb + four-on-
floor, everything sidechained to the kick. Seam p64.

## 2026-07-31 — play session 7: dyn.py, the invisible hand

env_follow (attack/release poles, circular warm), compress
(feed-forward, log domain, soft knee), duck (proper sidechain —
the kick-duck every song hand-rolled, retired), transient
(fast-minus-slow differential shaper), limiter (lookahead sliding
max via maximum_filter1d — the first draft's index-matrix version
wanted 700 MB for 16s).

Verified crisp: compressor +12 dB step in -> +5.0 out (spec +4.5,
rest is follower ripple); duck depth 9.0 dB on a 9 spec and -10.0
on a 10; transient +6.0/+0.1 attack/sustain; limiter ceiling
0.950 exact with bit-exact passthrough below.

Metric lesson #5 (the theme hardened into a rule): MEASURE THE
BUS, NOT THE MIX — in the full mix the kick owns the very windows
where the duck acts, and the comparison buried itself (0.306 vs
0.301). Same failure as the drone-under-ney and the normalized
taraf. RULE: verify a processor on its own bus, pre-mix, always.

e07_pump: four-on-floor, pad unducked first half / ducked second.

## 2026-07-31 — play session 6: sympathetic strings (the taraf)

strings.sympathetic(): a bank of driven Karplus-Strong loops tuned
to a chord/scale that hum along with any input — sitar taraf,
piano-pedal-down, the bone resonating with what strikes it.
Fractional delays, t60-calibrated, alternating pans, seam-safe via
full extra warm pass.

Verified: one click in -> all 7 strings ring 59-72 dB above the
spectral floor at exactly their tuned Hz; resonance selectivity
2.5x (D pluck vs Eb pluck into a D string, tail energy).

METRIC LESSON #4 tonight (a theme: the instrument is easy, the
ruler is hard): per-call peak normalization INVERTED the
selectivity measurement — the resonant ring's big buildup peak got
scaled down harder than the off-resonant case, measuring 0.1x when
physics says 2.5x. Cross-call energy comparisons need norm=False;
the flag now exists and the docstring warns.

e06_taraf: drum groove + psaltery phrase through a D-minor taraf.

## 2026-07-31 — play session 5: mod.py, the effects that swim

chorus (N-voice wobbling circular delay, per-channel LFO phases),
flanger (short sweeping comb, unrolled feedback), phaser (cascaded
time-varying allpasses, 128-sample piecewise-constant blocks).
LFOs cycle-quantized, reads circular — loop-safe by construction.

Verified: chorus mono->stereo corr 1.000 -> 0.693; phaser notch
contrast +12 dB with allpass RMS ratio exactly 1.000; flanger comb
= 6x autocorrelation peak at its delay lag. Metric lesson again:
spectral contrast on 50ms of noise is ~30 dB of intrinsic variance
(useless for combs) — autocorrelation at the delay lag is the
honest comb detector; note the peak smears across the sweep range,
that's the sweep working. e05_swim: pad dry->chorus->+phaser
halves, drums through jet-plane flanger.

## 2026-07-30 — play session 4: winds.py, the flute that tunes itself

Waveguide flute after Cook's slide-flute (jet delay -> cubic x-x^3
-> bore delay -> reflection lowpass back into both). ney() preset =
breathier, darker. Overblow is PHYSICAL: shorten the jet delay
(faster air) and the octave speaks — verified x2.005.

This one fought back; the debugging trail is the treasure:
- Waveguide tuning: compensate the reflection filter's phase delay
  AT f0, not its DC limit c/(1-c) (DC limit alone left the high
  register 47c sharp... then the compensation masked the real bug).
- The cubic's zeros at +-1 KILL the jet if pressure pins it there —
  overblow-by-pressure died to silence; keep the operating point
  inside |x| < 1/sqrt(3) and overblow by jet delay instead.
- Mode competition is winner-take-all chaos: ~15-25% of (note,
  seed) combos speak the 12th, deterministic per seed, IMMUNE to
  priming (drive-path or bore-preload), filter slope, and pressure.
  Accepted fix: THE INSTRUMENT LISTENS TO ITSELF — render, measure,
  reseed on wrong mode, retune on wrong pitch (8/48 escapes -> 0-1).
- argmax-pitch LIES: a note whose 3rd harmonic edges the
  fundamental by 4% reads as a mode jump that never happened
  (chased that ghost for two rounds). Harmonic product spectrum
  (sp[k]*sp[2k]*sp[3k]) is the honest fundamental detector.
- Unit-gain pitch correction PING-PONGS when the plant gain is ~2
  (A4 oscillated +-140c forever): secant-method steps (estimate
  local gain from the last two takes) converge. Fractional delay
  on BOTH lines or the response staircases.
- Never measure one pitch inside a mix — the in-context check
  read the glass drone under every ney note (-1200c exactly).
  Verify stems, then mix.

State: mean |err| 22c, worst ~55c (flute), ney preset looser
(+-80c observed) — folk intonation, honestly documented. e04: 32s
ney sentence over bowed glass, overblown peak, seam p26.

## 2026-07-30 — play session 3: spectral.py, phase-vocoder surgery

freeze / stretch / cross_synth on hand-rolled STFT (4096/1024 hann).
- freeze: one frame's magnitudes resynthesized forever; per-frame
  phase advance + jitter blend (0 = buzzy organ, 1 = noise; ~0.3 =
  alive-but-still). Wrapped overlap-add = seamless loop. Verified:
  a church bell frozen mid-ring holds RMS flat to std 0.0015 over
  12s, seam p93 of a tiny distribution.
- stretch: classic Flanagan/Dolson phase vocoder with phase
  unwrapping. 6x on a pluck: duration x5.53 (edge-frame loss),
  pitch EXACTLY preserved (880.0 -> 880.0 Hz).
- cross_synth: A's magnitudes on B's phases, `whiten` blends B's
  per-band envelope, `punch` gates frames by B's broadband energy
  (the vocoder's envelope follower). Choir x drum groove = the
  room learns to talk.

Honest metric note: drum-envelope correlation of the talking choir
plateaus ~0.5-0.6 for ANY frame size (4096 down to 512) — the
squared-energy metric is dominated by kick-band overlap with the
choir fundamental and under-reports the audible gating. Lesson:
when a metric stops responding to the knob that obviously changes
the sound, suspect the metric before the sound.

## 2026-07-30 — play session 2: drums.py, the simulated kit

The classic analog drum recipes as library voices (every song so
far hand-rolled its own kick): pitch-drop kick with band-limited
beater click, two-tone + wire-band snare, 808 hat (six-square
inharmonic cluster through a high bandpass), 808 clap (three fast
bursts riding a fourth), tom/conga with band-limited skin/slap,
540+800 Hz square-pair cowbell, rim, shaker. e02: per-voice
spectral-centroid inspection + an 8-bar groove @102.

Lessons measured, not guessed:
- Raw noise transients POISON the centroid: first kick read 3913 Hz
  (a hi-hat number) from 4 ms of unfiltered click; band-limiting
  the click dropped it to 617 Hz. Same fix tom 5164->873,
  conga 5979->1290. Centroid inspection catches what peak/RMS miss.
- Equal-power pan 0.55 is only ~1.6 dB of channel difference —
  "hard" panning must approach ±1 (0.85 here) to decorrelate.
- A drums-only loop measures mono-ish (corr 0.82 >250Hz) BECAUSE
  the snare/clap backbone belongs in the center; alternating
  hat/shaker pans are the width that actually registers. Judge
  width targets per-material, not one number for everything.

## 2026-07-30 — play session 1: the kit grows six limbs

Research: PADsynth (Nasca / ZynAddSubFX docs), FDN reverb design
(Jot via Smith's PASP), modal tables (measured bell analysis;
marimba bars tuned 1:4:10, xylophone 1:3:6; church bell
hum/prime/tierce/quint/nominal = 0.5/1/1.2/1.5/2).

New modules, each verified numerically before commit:
- pads.py — PADsynth: Gaussian-band spectra on the loop's own DFT
  grid = seam CANNOT exist; independent phase draws per channel =
  free decorrelated stereo; formant_amps + vowel tables = seamless
  choir. (seam_report upgraded to percentile-rank of the wrap step.)
- modal.py — strike/bow over mode tables (bell, church bell,
  marimba, xylophone, glass, wood). Fundamentals land exact.
- strings.py — Karplus-Strong + Jaffe-Smith (pick-position comb,
  damping blend, fractional-delay tuning), period-block vectorized.
- space.py — 8-line Householder FDN reverb (mutually-prime delays,
  t60-calibrated, block-vectorized: 3s in 0.02s; loop-safe via
  double-pass warm) + circular tape echo with cycle-quantized wow.
- shape.py — wavefold (animatable drive), chebyshev (weights[k] =
  harmonic k+1, exact on a sine), bitcrush, pre-emphasized tape_sat.
- grain.py — wrapped Hann grain clouds; +12 into the FDN = shimmer.

Showcase: songs/reliquary.py — "Reliquary", 72s, D aeolian @60.
Choir bed mouths oh->ah across the loop, church bells (the tierce
supplies the minor third), one psaltery sentence with its rest and
low answer (standing grammar), bowed glass in the rests, folded
drone breathing, faint +12/+19 shimmer, everything in the FDN room.
seam p24 (clickless), stereo corr >250Hz = +0.056, peak 0.900.

## 2026-07-30 — spin-off

Director: "spin off the music composition library to its own repo,
and take the next few hours just playing around with new ideas for
sound transformations, effects, simulated samples, and so on. you
can look up research papers too."

Extracted the shared engine from marrow/dev/music/hermits.py into
`loam/` (SR, hz, Loop, stereo, ad_env, write_wav; added
seam_report). Moved the three composition scripts to `songs/`;
hermits.py now imports the library, the two elders stay as written.
Determinism check: loam render of the hermit suite is byte-identical
to a render from the original marrow script. MARROW keeps the .oggs.

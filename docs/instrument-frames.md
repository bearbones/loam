# Instrument frames: construction-driven assemblies

The harp and rake frames are continuous carved forms ([traditional harp
refinement](traditional-harp-refinement.md)). The bar instrument is different:
a mallet instrument is an assembly of sawn members and hardware, and its look
comes from the construction rules real marimbas follow. This page records those
rules as the pipeline implements them (`formlab/layout.py` `bar_frame_plan`,
`formlab/recipes.py` `bar_frame`, hardware in `tools/build_clockwork.py`,
checks in `tools/test_bar_frame.py`).

## The bar frame

A free-free bar's fundamental mode has its nodes 22.4 % in from each end
(`layout.NODE`). A marimba drills the bars there and hangs them on a cord, so a
bar rings instead of being damped by whatever holds it. Everything else follows:

- **Rails follow the node lines.** Two rails run under the bars through every
  bar's nodes (`bar_nodes`), 0.30 m past the end bars. Because the bars shorten
  toward the treble, the rails converge; the rail curve is a spline through the
  actual node points, not a straight approximation. A rail is 60 mm deep by
  70 mm wide and its top sits 30 mm under the bars' underside.
- **Cord and posts.** Brass posts stand on each rail midway between adjacent
  bars (and one past each end bar), topped with a rubber cushion; the cord runs
  post to post at the bars' mid-thickness, through the node holes. Posts and
  cushions stay below the bar tops, so the mallets only ever meet bars.
- **Resonators.** Under each bar hangs a closed quarter-wave tube: real length
  `c/4f − 0.61 r` (open-end correction), scaled by the scene's ×3, with a dark
  mouth ring under the bar and a stopper cap at the bottom. The radius is
  capped so the tube hangs between the rails with a 12 mm gap — the treble
  tubes are narrower because their node spread is smaller, exactly as on the
  real instrument. A steel bank rod through the tubes ties them to the ends.
- **End frames.** Each end is a foot across the rails, two uprights tapering
  upward just outside the rails, and a crosspiece the rails rest on. The end
  frames are as wide as the local rail spread, so the bass end stands broader
  than the treble end. Brass glides sit under the foot tips.
- **Stretcher and name board.** A low stretcher ties the ends; the plaque and
  note names sit on a name board hung on the front uprights' faces. The board
  is straight between the two ends, so it angles slightly with the converging
  rails, and the text follows it (`board_z`).

The wooden members are closed sweeps with a chamfered rectangular section
(`recipes.TIMBER`), exported as one profiled object, `form_bars_stand`, the
name the Godot form toggle and the tool-clearance ruler already key on. Metal
hardware is built in Blender from the same plan, so the tubes, posts, cord and
text agree with the timber to the millimetre.

## Trestle benches for the bells and blocks

The expanded rig's glass bells and temple blocks sat on plank beds with two
legs each. Every struck instrument other than the bars now sits on a trestle
bench (`layout.bench_plan`, `recipes.bench_frame`, object `form_<mid>_stand`):

- **Rails and bearers.** Two straight rails run along the row, 0.25 m past the
  end elements, and a bearer crosses them under every element. The bearer top
  sits one pad (20 mm) below the lowest element's underside, so the whole bench
  is below anything a mallet meets.
- **Mounts follow the element.** A block is a bar: it rests on two rubber pads
  at its nodal points (`bar_nodes`), the way a concert wood block sits on foam
  at its ends. A glass bell is a call bell: a brass base flange on the bearer
  and a centre post rising through the mouth into the crown, so the dome hangs
  free of the bench and rings (`layout.BELL` records the bell profile's drop
  and mouth so the plan knows where the lip is).
- **Trestles.** Each end is a crossbar the rails rest on, two legs splayed
  outward to the floor and a tie between them where they have splayed to at
  45 % of the height; a stretcher joins the two ties. A fascia hung on the
  bearers' front ends carries the plaque and note names.

The bench stays inside the footprint of the bed it replaced and below the
elements, so the gantry plan is unchanged; `tools/test_bench.py` pins those
rules on the expanded layout, and the tool-clearance ruler and the Godot form
toggle treat every `form_*_stand` alike.

## The harp's pedal base

A pedal harp's base is a box, not a drum: the column and the body's lower
return seat in it, and the seven pedals leave the face toward the player
(toward the soundbox, +x here) through vertical slots, three on the left of
the string plane (D C B, outside in) and four on the right (E F G A), each a
steel lever on a brass pivot inside the box falling to a tread on the floor.
`layout.harp_base_plan` lays that out from the column's x and the string
plane's z alone — box, crown, sole, slots, levers, treads — and
`build_clockwork.py` builds it. The base is one of the static obstacles
the rail search is promised (with the chamber cabinet and, below, the rake's plinth) (x left−.82…+.46, y to .36, z ±.58); the plan
keeps the box inside that promise so a base change never moves a rail.
`tools/test_harp_base.py` pins that, the 3|4 split, tread spacing and the
levers leaving the front face. (The obstacle box is part of the rail cache
key; the treads reach 30 cm past its x limit at floor level, below anything
an arm can reach, and the tool-clearance ruler measures them anyway.)

The rake is strung like a lever harp — no pedals — and stood on the bare floor
with its column foot sunk into the stage. It now stands on the same base plan
without pedals (`harp_base_plan(..., with_pedals=False)`): a plain plinth with crown
and sole under the column and the body's lower return, promised to the rail
search as an obstacle exactly as the harp's is. Adding that promise changes the
rail cache key for every mechanism, so the rails re-plan once; the rake's rail
is 1.4 m in front of its string plane and the plinth stays 0.3 m below the
lowest string foot, so nothing moves. `test_harp_base.py` checks both bases.

## The neck carries the strings the way a harp's does

A harp's strings do not end in the air under the neck, and its action is not on
the far side of the neck from them. The strings run close to *one* face of the
neck (the string plane sits 6 cm off the neck's lower bead crests here, 2 cm at
real scale), and that face carries the action: a brass plate seated on the bead
crests, the two rows of discs on the plate with their fork pins reaching past
the string plane on either side of each string, and above them a bridge pin
the string bears on before it leans over to its tuning pin. The tuning pin
passes through the neck and its square head comes out the far face, where the
tuning key goes — and a pedal harp's neck is plated on that face too, so the
far plate is what the house sees, with the sixteen square pin heads standing
proud of it, while the action faces the strings. The wire from the top of the
speaking length over the bridge pin to the tuning pin is the string's dead
length: it is strung, it is seen, and it never sounds. `--view=12` looks at
the action from the string side.

`layout.neck_plan` (numpy-free, so the Blender builder and the ruler share it)
lays that out for one string from its upper end and the world z of the neck's
two faces at that string; `recipes.neck_faces` reads those faces off the carved
backbone (its section field's depth at the sample nearest the string), and
`recipes.action_plate` sweeps both plates along the same samples, `NECK['plate']`
proud of the crests and 90 % of the neck's local width tall, so the plates,
discs and pins follow the neck's real taper rather than one plane. The recipe
puts a ferrule at a string's foot only — its top no longer terminates in the
frame. `build_forms.py` writes every string's plan into the recipe's `neck`
block; `build_clockwork.py` builds the discs, fork pins, bridge pins (brass),
tuning pins and keys from it, adds the bridge pins to the tool-clearance
hardware, and records the dead length's turning points on the string
(`strings[sid].neck`, written after the rail search so the rail cache key is
untouched); `performance.gd` `_make_dead_length` draws the two straight dead
lengths in the string's own wire material beside the vibrating string, never
excited. The rake, strung like a lever harp, gets bridge and tuning pins and no
discs. The harp's and rake's bases and obstacles are unchanged, so no rail
moved. `tools/test_neck.py` pins both plates on their crests, the fork pins
straddling every string past its plane, the bridge pin +x and the tuning pin −x
of the string and clear of its neighbours, the pin within the neck's height, the
manifest's turning points, and the single foot ferrule;
`dev/test_performance.gd` checks every harp and rake string has its dead length
starting at `b` and climbing to the neck.

The dead length does not stop where it meets the pin: a harp string winds its
tuning pin, coil beside coil, between the string plane and the neck, and the
coil is what a tuner's eye reads on a pin. `layout.pin_wrap` records on the
string (`neck.wrap`) the helix's axis point on the pin at the string plane, the
pin's radius, the turns (2.5) and the room along the pin from the plane to 3 mm
short of the plate's outer face; `performance.gd` winds a tube of the string's
own gauge round it from the contact on the pin's +x side up over the pin, the
way the wire arrives from the bridge below, advancing toward the neck a wire's
diameter a turn (or finer if the room is less — it never is here: the widest
wire needs 33 mm of the 49 available). The coil is a tube along a helix
(`_tube_along`, parallel-transported rings), not the straight tube the wire
shader bends, so it wears a plain material in the wire's colour. `test_neck.py`
pins the recorded wrap against the plan, the room against each string's gauge,
and the coil clear of the neighbouring strings' pins and dead lengths;
`dev/test_performance.gd` checks the coil sits on its pin, is as wide as the
pin plus two wires, and runs no further along the pin than its room.

## The chamber's flywheel is carried and driven

The brass flywheel beside the harp stood on the floor on its rim with no
axle, the one thing left in the main shots that nothing held up. A flywheel is
carried on an axle in two plummer blocks — split bearing housings bolted to
pedestals on a sole plate — one either side of the wheel, and it drives
something. `layout.flywheel_plan` (numpy-free) lays that out from the wheel's
centre and radius: hub, axle, the two housings in their blocks on pedestals
standing on the sole plate on the floor, a drive pulley on the
axle's back end, and a flat belt to a pulley on a stub axle between two ears
bracketed to the chamber cabinet's end face. Each block is **split at the
axle's height**, as a plummer block is so the shaft can be laid in: the base
casts the lower half of the seat and its top is the flange's underside; a
**cap** (`FLYWHEEL['cap']`, recorded as `caps`) — a D-section, the half-disc
of the wall 12 mm proud of the housing over a flange as wide as the studs —
closes it; two **studs** rise out of the base through the flange to hex
**nuts** outside the cap's wall, and an **oil cup** with its lid stands on the
cap's crown to feed the bearing. (Before, the housing was a bare cylinder on
the block with two bolt stubs beside it — a bearing nobody could have
assembled.) The belt's bands are the true
outer tangents of the two pulleys, with a wrap round each. `build_clockwork.py`
builds it from the plan and records the plan on the manifest (`flywheel`);
`performance.gd` turns the wheel, hub and drive pulley once a bar of the
score's tempo and the belt pulley with them, faster by the pulleys' radii, the
same way round as an open belt does. The assembly stands beyond the cabinet's
end, outside every obstacle and every arm's reach, so no promise changed and no
rail moved. The wheel's rim is a ring gear: 52 involute teeth cut by the
pinions' profile at their module (`formlab.gear.profile`,
`docs/articulated-arms.md` "The teeth are involute"), so the flywheel and the
carriages' pinions read as one family of gears — the sixteen bevelled blocks
it wore before looked like a cog drawn from memory next to them.

The wheel is a **casting**, not a disc: a rim 90 mm deep from the teeth's tips
(61 mm under their roots), the hub boss on the axle, and six spokes between them (`FLYWHEEL['spokes']`,
recorded on the plan as `spokes`). Each spoke is elliptical in section — wide in
the wheel's plane, thinner along its axis, tapering from the boss to the rim —
and **bowed** tangentially by 50 mm at mid-length (`layout.spoke_centre`,
`layout.spoke_section`; the builder's `spoke()` sweeps rings of the ellipse
along that line, its ends buried in boss and rim). The bow is the founder's
rule, not a flourish: a cast rim shrinks as it cools after the spokes have set,
and a curved spoke flexes to let it while a straight one would crack at the
boss — which is why every engine-house flywheel of the period has them. A
disc, besides, hid the wheel's turning: a bar a turn reads only if something
passes. `tools/test_flywheel.py` pins the axle through the wheel and both
housings, the housings clear of the wheel and hub, the pedestals on the sole
plate, each cap on its housing with the flange's underside at the block's top
and the split at the axle, the studs through the flange outside the cap's
wall with their nuts on the flange, the oil cups on the crowns, the pulleys in
one plane, the bands tangent, the assembly clear of
every arm sweep, rail and obstacle, and the casting — the rim's depth under
the roots, the spokes inside the wheel's width, and, reading the built GLB's
`Chamber flywheel` mesh, that every vertex between boss and rim lies on a
spoke's section (the disc is gone); `dev/test_performance.gd` checks the wheel
turns a quarter turn in a quarter bar about z and the belt pulley by the ratio.

## The strings leave the soundbox through eyelets

A harp string does not tie to anything on the outside of the soundboard: it
comes up through a hole, and the hole wears a brass eyelet so the wire does not
cut the wood. Here each plucked string's foot is the mouth of a ferrule the
recipe runs down into the soundbox moulding (`recipes.harp_frame`), and that
mouth now wears the eyelet (`formlab.layout.eyelet_plan`): a flange disc
covering the mouth, its axis down the ferrule's barrel, and a rounded lip
standing proud of the flange round the hole, sized so every wire gauge the
scene draws clears it. The eyelet, the recipe's ferrule and the ruler share one
table (`EYELET`) for the barrel's offset and gauge. `tools/test_eyelets.py`
pins the plan against each string's foot, the lip inside the flange's rim and
proud of it, the hole against the wire, neighbouring eyelets against each
other and every eyelet against every arm's sweep; `check_form_clearance` folds
the eyelets into the reference hardware the arms are measured against.

## Space accounting

The frames are built after the rail search fixes the rails and before the
gantry planner places the masts, and each stays inside the footprint of the bed
it replaced and below its elements' undersides. That was not enough on its own:
the plank beds were never obstacles to the rail search, and when the bells' bed
became a form the gantry planner found the expanded rig's first harp arm
running its rail and rack straight through it — the arm had been sweeping
through the bed unmeasured. Every struck instrument's frame footprint (up to
the elements' undersides) is therefore promised to the rail search as an
obstacle, like the cabinet and the harp and rake bases (`build_clockwork.py`,
`manifest['obstacles']`); the mallets of the instrument's own arms come from
above, so the promise costs them nothing, and a rail from another mechanism
must plan around it. `test_bar_frame.py` and `test_bench.py` pin that each
frame is promised and lies inside its promise; `build_forms.py` measures the
masts, plinths and racks against the frame's bounding box, and the
tool-clearance ruler (`check_form_clearance.py`) measures every mallet pose
against the frame meshes.

## Rulers

```sh
python3 tools/test_bar_frame.py        # construction rules and closed pieces
python3 tools/test_bench.py            # the benches and their promise
python3 tools/test_harp_base.py        # the harp's pedal base and the rake's plinth
python3 tools/test_neck.py             # the necks' plates, discs, bridge and tuning pins, dead lengths
python3 tools/test_flywheel.py         # the flywheel's bearings, pedestals, belt drive and clearance
python3 tools/test_eyelets.py          # the eyelets the plucked strings leave their soundboxes by
python3 tools/build_forms.py           # packs the frame; gantries measured against it
blender -b -t 2 -P tools/check_form_clearance.py   # tools vs frames and stand
```

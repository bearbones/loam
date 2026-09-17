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

## Space accounting

The frame is built after the rail search fixes the rails and before the gantry
planner places the masts. The whole frame stays inside the footprint of the
bed it replaced (z within ±0.75 m of the bar line, nothing above the bars'
underside), so the gantry plan is unchanged by the swap — `test_bar_frame.py`
pins that envelope, and `build_forms.py` still measures the masts and plinths
against the frame's bounding box. The tool-clearance ruler
(`check_form_clearance.py`) measures every mallet pose against the frame mesh.

## Rulers

```sh
python3 tools/test_bar_frame.py        # construction rules and closed pieces
python3 tools/build_forms.py           # packs the frame; gantries measured against it
blender -b -t 2 -P tools/check_form_clearance.py   # tools vs frames and stand
```

# Articulated arms: joints, parallel bars and the space they need

The mechanisms that play the instruments are built as real linkages, not as
scaled cylinders. This note is the build guide for that layer: what the
pieces are, where the numbers come from, and which rulers keep an arm out of
its neighbour, the strings and the furniture.

Modules: `formlab/linkage.py` (joint and link recipes), `formlab/rig.py`
(the Godot IK mirrored in numpy), `formlab/clearance.py` (capsule ruler),
`formlab/layout_search.py` (rail placement), `loam/score.py` (`arm_clearance`
in the planner). `tools/build_forms.py` assembles an arm per actuator and
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
| carriage, elbowhead, wristhead | `crosshead()` | two bosses joined by a web; the pins live here |
| shoulder, elbow, wrist | `knuckle_pin()` | domed head one side, nut the other |
| tool + shank | `pick_tool()` / `mallet_tool()` | tool origin = contact point |

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
  rakes use `(0, .15, −.10)`: above and *behind* the string, so the pin never
  sits on the string it plays. Mallets use `(0, .20, 0)`.
- **Bend hint.** `bend = "back"` keeps a pick arm's elbow on the far side of
  the string plane — the hanging elbow of a harpist. With the root above and
  behind the string an "up" elbow is geometrically forced through the
  strings; "back" is the universal rule for plucked and raked mechanisms.
  Mallets keep "up".

The parallel bars are posed with `link_basis(a, b)` at `a + o` — the same
basis as the primary bar, translated by the constant world offset `o`.
`choose_offset()` picks `o` (magnitude 0.11 m) to maximise the minimum
separation between the two bars of a segment over the whole piece.

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

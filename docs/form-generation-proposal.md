# Proposal: physically informed procedural form

Status: the first prototype has been implemented. See [results and rebuild instructions](form-generation-results.md). The following preserves the original design rationale.

## Immediate diagnosis

`tools/build_clockwork.py` joins consecutive string endpoints with independent
capped cylinders. Bevels and better normals cannot make those into one coherent
neck or bridge. The next geometry pass should produce a continuous tapered
member, deliberate anchor seats, and broad transitions into its supports.

Existing string endpoints, speaking lengths, pick contacts, and actuator motion
must be held fixed for the first comparison. A new backbone can sit outside
those endpoints and meet them through short bosses. Forcing all anchors onto a
new mathematical curve would change the instrument rather than merely improve
its frame.

## Recommended division of responsibility

1. **A small headless Python core:** attachment points, load cases, supports,
   keep-out regions, material assumptions, design controls, deterministic
   generation and measurements. Initially local to this repository but isolated
   from the `loam` audio package and from `bpy`.
2. **Blender adapter:** turn generated curves, sections, fields or meshes into
   editable assets; handle mesh finishing, materials, preview and GLB export.
   A Blender add-on can later expose the same core through sliders and overlays.
3. **Godot:** consume baked assets and semantic attachment points, preserving
   deterministic performance playback. Runtime growth should be a separate
   future use case, not a requirement of the authoring prototype.

There is no need to implement another general mesh editor, boolean library or
node system. Blender already offers curve sweeps and profile/radius control.
The distinctive work is the rule system that decides where structure belongs,
how thick it should be, and which constraints it must satisfy.

## Physical grounding and artistic control

Separate three labels in every generated asset:

- **Geometric construction:** a spline sweep, smoothly blended branch or
  catenary used for its appearance; no structural claim.
- **Physically informed heuristic:** for example a branch thickened according
  to an accumulated proxy load. Record the assumption; do not call it stress.
- **Solved model:** equilibrium or elasticity with declared boundary conditions,
  material parameters, load cases and a measured residual/convergence result.

A catenary is a particular cable equilibrium under self-weight. The harp has
point loads from strings and constrained attachment locations. Funicular form
finding can respond to specified loads, but a generic catenary is not an
all-purpose low-stress harp neck. A rigid frame may also carry bending and
compression and require a different model.

The current score does not specify string linear density/tension, structural
Young's modulus or body mass density; its material presets mostly drive sound
synthesis. Pitch and visual length alone do not determine tension. Start with
explicitly labeled relative load cases, or add the missing physical inputs
before assigning stresses in pascals. The display's existing threefold geometry
scale is also not automatically a calibrated physical scale.

Bone-inspired ridges should follow an intelligible rule: growing material along
load paths, thickening junctions, tapering toward less-loaded branches, and
preserving a minimum wall thickness. Stress-guided ribs and topology optimization
are possible mechanisms; neither alone constitutes a biological bone model.
Art direction still controls silhouette, branching density, asymmetry, section
shape and surface character. Walnut should read as carved or laminated wood;
a porous shell may suit a cast-metal or composite material better.

## The first experiments

### 1. A coherent harp, plus a reusable sweep

Generate three frames from the same anchors and unchanged motion envelope:

- **Carved walnut:** a continuous asymmetric neck, tapered section and flared
  roots into the pillars. The clean baseline.
- **Load-guided ribs:** a continuous backbone with ridges collecting into the
  supports, initially driven by documented proxy loads or a coarse solved frame.
- **Branched shell:** smoothly joined forks and controlled openings, preserving
  the same attachments. Treat as geometric/heuristic until validated by a solver.

The implementation should introduce only the reusable pieces required here:
curve sampling, stable cross-section orientation, variable-section sweeps,
attachment frames, and clearance evaluation. Reuse Blender mesh operations for
finishing. Do not open with a general growth language or full 3D optimizer.

Acceptance: no loose cylinder seams; no gaps at seats; closed nondegenerate
meshes; continuous shading; stable grain coordinates; original 331 tool
contacts unchanged; swept-tool clearance against the new frame measured over
the complete track. Report clearance sampling resolution rather than claiming
continuous-time collision proof from discrete samples.

### 2. One structural experiment

Add a coarse planar frame/beam problem with named supports, loads and material
assumptions. Compare a uniform frame and a variable-thickness frame at equal
material volume. Measure deflection/compliance, equilibrium residual and
sensitivity to mesh refinement. Include bending rather than silently treating
all members as axial cables. Evaluate available solvers before implementing one.

This earns the claim that the shape responds to a physical rule and gives the
same kind of numerical discipline as loam's synthesis experiments.

### 3. Extract after reuse

Apply the same interface to a second object, such as a branching instrument
stand or ribbed resonator housing. Only then decide which abstractions deserve
a standalone package and an interactive Blender add-on. Full 3D optimization,
robust branching-field meshing and biological growth simulations follow actual
uses rather than being prerequisites.

## Longer-term connection to sound

An eventual shared physical instrument description could provide mass/stiffness
for structural form, body resonances for synthesis, and modal displacement for
animation. That requires validated units, material data, boundary conditions,
and coupling. It is a strong direction for the two systems to meet; the present
Karplus–Strong string audio plus illustrative frame geometry does not already
provide this connection.

## Existing tools to investigate

- [Blender Curve to Mesh](https://docs.blender.org/manual/en/4.2/modeling/geometry_nodes/curve/operations/curve_to_mesh.html): profile sweeps and curve-radius control; adequate machinery for the immediate continuous frame.
- [COMPAS](https://compas.dev/compas/latest/): a Python computational-design framework; evaluate its geometry/structural ecosystem before duplicating it.
- [COMPAS Blender integration](https://compas.dev/compas/2.4.3/userguide/cad.blender.html): evidence that a headless core plus host adapter is a practical arrangement. No compatibility claim for this machine is made until tested.
- [ETH graphic statics examples](https://block.arch.ethz.ch/eq/drawing/view/6): funicular equilibrium is tied to specified loads and boundary conditions.
- [DTU TopOpt Python examples](https://www.topopt.mek.dtu.dk/apps-and-software/topology-optimization-codes-written-in-python): educational starting points for studying compliance optimization, rather than inventing the method from scratch. Check code licensing before reuse.
- [OpenStax string mechanics](https://openstax.org/books/university-physics-volume-1/pages/16-3-wave-speed-on-a-stretched-string): tension and mass per length are necessary physical inputs beyond pitch/geometry.

Recommendation: put the next effort into the continuous harp and one measured
structural experiment, with a small reusable core and Blender doing the mesh
work. Defer plugin packaging and broad generalization until the second use case.

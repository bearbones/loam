# First procedural form prototype (historical)

**Superseded geometry:** see [the traditional harp refinement](traditional-harp-refinement.md) for the current models, changed visual anchor layout and current verification. The structural measurements below apply only to the original experimental neck.

The harp and rake now use continuous, tapered frames with blended roots and
individual anchor seats. Their original string endpoints and animation remain
fixed. Both the original and expanded ensembles include three selectable forms:

| Form | Appearance | Basis |
|---|---|---|
| Carved (default) | Warm walnut, uninterrupted neck and broad roots | Geometric construction |
| Ribbed | Cast brass, variable section and longitudinal ridges | Harp neck section comes from a solved benchmark; ribs are artistic |
| Shell | Walnut with flowing forks and openings | Geometric / load-collection heuristic |

Press **F** in Godot to cycle them, or use `--form=carved`, `--form=ribbed`,
or `--form=shell`. The bar instrument also has a branching stand made through
the same pipeline. Its branches illustrate load collection, without a solved
stress claim.

## Architecture and where to invest

`formlab/` is a small headless Python core, separate from loam's audio package.
It provides arc-length curve sampling, parallel-transport orientation,
variable-section closed sweeps, ridged profiles and topology checks. Recipes
combine these into instrument structures. NumPy and SciPy are the computational
dependencies; Matplotlib produces the benchmark chart.

`tools/blender_forms.py` is the host adapter: Blender joins the components with
voxel remeshing, smooths and decimates the surface, checks the final triangles,
and reconstructs grain coordinates from source curves. Godot consumes baked
GLBs and uses those coordinates for the existing procedural wood shader.
No additional software was installed.

The second use case—the branching stand—supports keeping the core reusable,
but does not yet justify a separately distributed package. A future Blender
add-on should expose recipes and assumptions through controls and overlays,
calling this core. Continue using Blender for finishing and asset editing.
The next worthwhile capabilities are attachment/keep-out constraints and better
section/load models, before a general growth language or independent mesh editor.

## Structural experiment

`formlab/frame.py` implements a narrow planar Euler–Bernoulli frame benchmark
with axial and bending stiffness. Available solver ecosystems were reviewed:
[COMPAS FEA](https://compas.dev/compas_fea/latest/gettingstarted/fea.html) uses
external analysis backends. For this small experiment, an explicit kernel made
assumptions and analytical checks easy to inspect; it is not a general solver
replacement. A broader structural application should use a mature backend.

The curved upper neck has clamped endpoints (piers assumed rigid), E = 10 GPa,
width 0.22 m, and sixteen assumed downward string loads of 100 N each. The
uniform depth is 0.22 m. Optimization redistributes depth between 0.10 and
0.38 m at equal volume, with a small smoothness penalty.

At the finest, 240-element resolution:

| Measurement | Uniform | Variable depth |
|---|---:|---:|
| Compliance (N m) | 0.138356 | 0.083076 |
| Maximum displacement (mm) | 0.1741 | 0.1203 |
| Volume (m³) | 0.235414 | 0.235415 |

Compliance falls **39.95%**. Volume is equal at the 60-element optimization
resolution; refinement changes the volume comparison by about four parts per
million. Runs at 30, 60, 120 and 240 elements check convergence; the finest
free-DOF equilibrium residual is 1.47e-9.

This result describes the illustrative neck problem, not the stiffness of the
complete displayed frame. Loads and units are benchmark assumptions, not
inferred acoustic properties. The model excludes lower rail, root flexibility,
joints, anisotropy, torsion, buckling, self-weight and dynamics. The rendered
ridges and blended junctions are not included in the solved section model.

## Verification

- Analytical axial extension, cantilever deflection/rotation, reactions and
  rotated-frame invariance pass independently of the optimization.
- Analytic components and final remeshed surfaces pass closed-edge and
  nondegenerate-triangle checks. Sweep volume, transported frames and ring
  topology also pass.
- All original string endpoints agree with the original score within 1e-12.
- Imported Godot rigs pass all 331 original and 399 expanded contact checks.
- Each frame alternative was checked against 64,632 original tool poses,
  sampled at 120 Hz plus exact note-contact times. The conservative minimum
  tool clearance is **34.8 mm**. Picks use sampled box surfaces with a 7.1 mm
  spatial error allowance; mallets use spheres. Anchor spheres overlap their
  seats; maximum anchor-to-surface distance is 0.38 mm.

Clearance covers tools against the new frames and stand. It does not certify
whole-arm/rail collisions or continuous-time clearance between samples.
The clearance report records hashes of the final collision meshes and poses.

## Reproduce

From the repository root, after rendering the scores:

```sh
python3 tools/study_harp_frame.py
python3 tools/test_formlab.py
blender -b -t 2 -P tools/build_clockwork.py
blender -b -t 2 -P tools/build_clockwork.py -- render/clockwork/score.json clockwork_expanded
godot --headless --path harness --editor --import --quit
godot --headless --path harness -s dev/export_motion.gd
blender -b -t 2 -P tools/check_form_clearance.py
godot --headless --path harness -s dev/test_performance.gd
godot --headless --path harness -s dev/test_performance.gd -- --expanded
```

The builders prepare recipes from the current score-derived layout, then export
editable `.blend` files and GLBs containing all variants. Benchmark, mesh,
clearance and preview outputs live in ignored `render/form-study/`. The current
structural study is specific to the original harp; changing its score geometry
requires adapting and rerunning the study rather than reusing its section data.

## Follow-up work

1. Add full link/carriage geometry to clearance evaluation, with adaptive time
   subdivision around close approaches. Acceptance: report the responsible
   parts and score interval for every violation.
2. Introduce explicit attachment frames and keep-out volumes into recipes;
   fail generation when minimum thickness or anchor seating cannot be met.
3. Add calibrated tension, mass-per-length and structural material properties
   to a shared instrument specification, keeping synthesis presets separate.
   The sound backlog in `clockwork-todos.md` remains applicable.
4. Compare the neck benchmark with a mature solver, then include flexible piers
   and the lower rail before making whole-frame structural claims.
5. Expose the proven recipe parameters in a thin Blender add-on, with rerunnable
   generation and geometric/heuristic/solved labels. Preserve hand-edited assets
   separately from generated output.

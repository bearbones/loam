---
repo: loam
domain: audio-geometry
languages: [python, gdscript]
primary_oracle: "timeout 120s python3 dev_smoke.py && timeout 300s python3 -m pytest tools/test_*.py"
---

# Standing Autonomous Protocols — `loam`

Durable reference for unsupervised, monotonic-value workflows in `loam`
(headless NumPy/SciPy physical-modeling audio synthesis library, `formlab/`
mechanical kinematics & 3D instrument geometry builder, and Godot `harness/`
Wayfarer's Cabinet gallery).

## Protocol: DSP Synthesis & Kinematics Performance Ratchet
- **id**: `loam/perf`
- **category**: `perf`
- **scope**: `own-code`
- **metric**: `render-wall-ms | clearance-search-ms`
- **default_stop**: `speedup>=5% | cycles=5 | indefinite`
- **tier**: `draft-pr`
- **oracle**: `timeout 120s python3 dev_smoke.py && timeout 300s python3 -m pytest tools/test_*.py`
- **summary**: Profile and optimize NumPy/SciPy synthesis kernels (fdstring, membrane, modal, pads, spectral) and formlab layout/clearance solvers gated by tools/test_bench.py.

### Focus Modules & Invariants
- DSP kernels: `loam/fdstring.py`, `loam/membrane.py`, `loam/modal.py`,
  `loam/pads.py`, `loam/spectral.py`, `loam/strings.py`, `loam/winds.py`.
- Geometry/kinematics: `formlab/clearance.py`, `formlab/layout_search.py`,
  `formlab/bake.py`, `tools/mesh_distance.py`, `tools/test_bench.py`.
- Preserve sample-level/SNR equivalence, zero NaN/Inf, and seamless loop
  continuity (`seam_report`).

## Protocol: DSP Stability & Mechanical Clearance Property Fuzzing
- **id**: `loam/fuzz-own`
- **category**: `fuzzing`
- **scope**: `own-code`
- **metric**: `instabilities-or-collisions-fixed`
- **default_stop**: `time=15m | failures>=1 | indefinite`
- **tier**: `pr-ready`
- **oracle**: `timeout 120s python3 dev_smoke.py && timeout 300s python3 -m pytest tools/test_*.py`
- **summary**: Property-fuzz acoustic voices for NaN/DC/blowup and loop clicks, and fuzz formlab scores/linkages for contact-timing jumps and geometry clearance violations.

### Invariants to Fuzz
- **Audio (`loam/`):** extreme pitch/velocity/damping/duration inputs must
  never produce `NaN`, `Inf`, runaway oscillation (`|x| > ceiling`), or loop
  seam clicks (`seam_report`).
- **Kinematics (`formlab/`):** randomized scores and layouts must satisfy
  `tools/test_motion.py` (exact scored contact timing, no boundary jumps,
  single occupancy), `tools/test_bake.py` (`Rig` vs `bake` parity), and
  `tools/check_form_clearance.py`.

## Protocol: Mutation Testing (`mutmut` + Adversarial Blind)
- **id**: `loam/mutation`
- **category**: `mutation`
- **scope**: `own-code`
- **metric**: `killed-mutants`
- **default_stop**: `cycles=5 | killed-mutants>=3 | indefinite`
- **tier**: `pr-ready`
- **oracle**: `timeout 120s python3 dev_smoke.py && timeout 300s python3 -m pytest tools/test_*.py`
- **summary**: Run mutmut (and <-> or) and adversarial blind mutation testing across formlab kinematics/clearance/bake logic and loam DSP primitives.

### Focus Modules
- `formlab/kinematics.py`, `formlab/clearance.py`, `formlab/stroke.py`,
  `formlab/pawl.py`, `formlab/bake.py`, `formlab/joints.py`, `loam/score.py`,
  `loam/motion_timing.py`.
- Follow `references/adversarial-mutation.md`.

## Protocol: Physical-Modeling DSP & Linkage Solver Bake-Offs
- **id**: `loam/bakeoff`
- **category**: `bakeoff`
- **scope**: `own-code`
- **metric**: `render-ms | spectral-realism | clearance-margin`
- **default_stop**: `candidates=3 | indefinite`
- **tier**: `scratch-ledger`
- **oracle**: `timeout 120s python3 dev_smoke.py && timeout 300s python3 -m pytest tools/test_*.py`
- **summary**: Benchmark alternative FDTD/waveguide/modal damping schemes in loam/ and mechanical layout-search / inverse-kinematics solvers in formlab/ in isolated worktrees.

### Candidate Topics
- Stiff-string / membrane finite-difference stability & dispersion tuning
  (`loam/fdstring.py`, `loam/membrane.py`).
- Seamless loop-tail folding vs overlap-add convolution for reverberant voices
  (`loam/space.py`, `loam/pads.py`).
- Spatial layout & collision-free linkage search heuristics
  (`formlab/layout_search.py`, `formlab/clearance.py`).

## Protocol: Stricter Python & Godot Static Warning Compliance
- **id**: `loam/warnings`
- **category**: `warnings`
- **scope**: `own-code`
- **metric**: `ruff-rules-and-godot-warnings-clean`
- **default_stop**: `modules>=2 | warnings=0 | indefinite`
- **tier**: `pr-ready`
- **oracle**: `timeout 60s ruff check loam formlab tools && timeout 120s python3 dev_smoke.py && timeout 60s godot --headless --path harness --quit-after 2`
- **summary**: Ratchet ruff lint rules and static typing across loam/, formlab/, and tools/, plus zero-error Godot headless parse checks on harness/.

### Escalation Targets
- Eliminate `ruff` errors across `loam/`, `formlab/`, and `tools/` (`E, F, I, W`
  → `B, UP, SIM, PERF, NPY`).
- Verify `harness/*.gd` compiles cleanly under `godot --headless --path harness --quit-after 2`
  with zero `SCRIPT ERROR` or `ERROR:` lines.

## Protocol: Physical Acoustics & Automata Kinematics Research Pulls
- **id**: `loam/research`
- **category**: `research`
- **scope**: `theory`
- **metric**: `verified-writeups`
- **default_stop**: `notes=1 | indefinite`
- **tier**: `research-doc`
- **oracle**: `web-verified citations + local docs/{motion-design,articulated-arms,wayfarers-cabinet}.md grounding`
- **summary**: Pull verified literature on physical-modeling acoustics (FDTD strings/membranes, modal synthesis, winds) and clockwork automata/linkage motion design.

### Research Queue
- Energy-conserving FDTD schemes for nonlinear stiff strings, bars, and struck
  membranes (Stefan Bilbao *Numerical Sound Synthesis* lineage & follow-ups).
- Expressive mechanical choreography for clockwork musical automata: pawl/detent
  mechanics, anticipation/follow-through, and collision-free linkage synthesis
  (`docs/motion-design.md`, `docs/articulated-arms.md`).

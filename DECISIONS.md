# Architectural Decisions

Living document. Each entry records what was decided, why, and any alternatives rejected.
Updated at the end of each working session.

---

## Language split: Python for everything except simulation

**Decision:** Python handles field generation, config, orchestration, PTA analysis, and plotting.
Julia (JutulDarcy) is used only for reservoir simulation and is treated as a black box.

**Why:** The user works exclusively in Python and is not familiar with Julia. Julia is required
solely because JutulDarcy has no Python equivalent for this simulation task. Keeping Julia
as a thin subprocess layer means the user never needs to read or modify `.jl` files.

**Interface:** Python writes a JSON config + reads a field `.h5` → Julia subprocess runs →
writes results `.h5` → Python reads back. File-based I/O, no Python-Julia interop library.

**Rejected:** `juliacall` / `PyJulia` — more seamless but adds version-sensitivity complexity
and harder debugging. Not worth it for a pedagogical sandbox.

---

## Config format: YAML + pydantic validation

**Decision:** All experiment configs are YAML files. Pydantic v2 validates them on load.

**Why:** YAML is human-readable and easy to modify (like ML experiment configs in PhysicsNeMo/Hydra).
Pydantic gives clear error messages and catches bad configs before Julia ever runs.

**Rejected:** Plain Python dicts + manual checks (no pydantic) — fewer deps but worse DX.

---

## One config = one run (no sweep)

**Decision:** Each YAML config defines exactly one simulation run with specific parameters.
There is no sweep/grid-search feature in the config.

**Why:** The goal is case-by-case physics examination, not ML surrogate training. The user
wants to intentionally create each run and understand it, not auto-generate combinations.
A flat sweep would obscure the physics learning.

**Cross-examination:** Done at the notebook level by loading multiple result `.h5` files
and overlaying them. `load_experiment()` scans all runs under an experiment folder.

---

## Experiment / run two-level hierarchy

**Decision:** Output is organized as `outputs/{experiment}/{run}/`. Configs mirror this:
`configs/{experiment}/{run}.yaml`.

**Why:** Flat structure (one folder per run) becomes unnavigable after ~20 runs.
Experiment = the physics question being asked. Run = base case or one variation.
Typical pattern: one base case + several runs that perturb one parameter at a time.

---

## Field files: always HDF5, always required in config

**Decision:** Perm/poro/well_mask are stored in `.h5` files. The simulation config always
requires `rock.field_h5` pointing to an existing file. No inline scalar shorthand.

**Why:** Enforces a clean separation between field generation and simulation. Makes it
natural to reuse fields across experiments. Prepares for heterogeneous fields from the start.

**Array convention:** `(nz, ny, nx)` axis order throughout. Units in SI (m² for perm).
Unit conversion (mD → m²) happens in the field generator, never in the simulation backend.

---

## Well location: boolean mask in field HDF5

**Decision:** Well location is stored as `/well_mask` (bool, shape `(nz, ny, nx)`) in the
field `.h5` file, not as `(i, j, k)` coordinates in the YAML config.

**Why:** Aligns with the planned interactive 2D drawing tool where the user will paint well
locations on a grid. A mask is the natural output of a drawing operation. Also more flexible
for future multi-well scenarios.

---

## Field generation: separate subproject with template system

**Decision:** `src/field_generator/` is a semi-independent subproject with a CLI
(`generate_field.py`) and a template system. Field configs live in `field_configs/`.
All Python source code lives under `src/` — field_generator is not an exception.

**Templates implemented:**
- `homogeneous` — uniform k and φ, baseline for all physics cases
- `fourier` — spectral synthesis → log-normal perm, spatially correlated
- `gmm` — Truncated Gaussian Simulation → facies-based (shale/siltstone/sand)

**Future:** Interactive 2D drawing tool for perm field and well location (planned as a
separate subproject, likely a Jupyter widget or standalone tool).

**Scaling rationale for heterogeneous fields:**
- Permeability: log-normal is the standard reservoir assumption.
  `k = exp(μ_ln + σ_ln · z)`, where `σ_ln` (perm_std_log) controls heterogeneity:
  0.5 = mild, 1.0 = moderate, 2.0 = strong, 3.0 = extreme (carbonates).
- Porosity: near-normal, clipped to [0.03, 0.45], weakly correlated with perm (ρ=0.3).

---

## Single-phase oil only (Cases 2 and 3 dropped)

**Decision:** The sandbox simulates single-phase slightly compressible oil only.
Original plan had three physics cases (single-oil, oil-water, gas); cases 2 and 3
are dropped.

**Why:** The learning goals are kh (perm-thickness) and minimum connected volume
via Bourdet derivative. Both are fundamentally single-phase phenomena:
- Plateau height ∝ qBμ/(kh)
- Boundary effect timing ∝ φ ct Vp

Adding rel-perms (Case 2) or pressure-dependent μ/Z (Case 3) would obscure these
relationships rather than illuminate them.

---

## Julia backend: avoid CPR preconditioner for single-phase

**Decision:** `simulate_reservoir(...; precond=:ilu0)` instead of the default `:cpr`.

**Why:** JutulDarcy 0.3.7's CPR preconditioner asserts `T_b <: StaticMatrix` on
Jacobian blocks. With `ImmiscibleSystem((LiquidPhase(),))` (single phase), the
blocks are scalar `Float64`, not `SMatrix{1,1}`, triggering an assertion error.
`:ilu0` works for both single- and multi-phase and is plenty fast for our 50×50 grids.

---

## PTA analysis: custom Bourdet + welltestpy for comparison

**Decision:** Implement Bourdet derivative from scratch in NumPy. Also install `welltestpy`
as an optional comparison library.

**Why:** Bourdet is ~30 lines of code and owning the implementation is pedagogically valuable
(you see exactly what the smoothing parameter L does). `welltestpy` is available for
cross-checking results but is thinly maintained.

---

## Plotting: Plotly (matplotlib unusable on this machine)

**Decision:** `src/plotting.py` uses Plotly, not matplotlib. Plots are saved as
standalone HTML (`fig.write_html(...)`); also render interactively in Jupyter.

**Why:** matplotlib `fig.savefig()` crashes the Python process on this Windows
machine with exit code -1066598273 (DLL crash, reproduced across PNG/SVG/PDF
and the `Agg` backend). Plotly works reliably and gives interactive output for
free, which suits the experiment-comparison workflow better anyway.

**Tradeoff:** HTML files are ~5MB each (bundled plotly.js). Acceptable for
local analysis; if we ever need lightweight static images, plotly's `kaleido`
backend can write PNG.

---

## Python environment

Conda env: `dst_well_testing` (Python 3.11, conda-forge)

| Package | Version | Purpose |
|---|---|---|
| numpy | 2.4.5 | numerics |
| scipy | 1.17.1 | spectral methods, stats |
| matplotlib | 3.10.9 | plotting |
| pandas | 3.0.3 | results tables |
| h5py | 3.16.0 | HDF5 I/O |
| pyyaml | 6.0.3 | config loading |
| pydantic | 2.13.4 | config validation |
| geostatspy | 0.0.79 | future geostatistical fields |
| welltestpy | 1.2.0 | PTA comparison |
| jupyter | — | notebooks |

Julia env: 1.11.5, packages JutulDarcy + CairoMakie + HDF5 in `Project.toml`.

**Windows note:** `conda run` is broken due to a registry AutoRun key issue. Use full
paths to env executables: `C:\Users\zchen\miniconda3\envs\dst_well_testing\python.exe`.

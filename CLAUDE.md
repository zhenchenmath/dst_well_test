# DST PTA Sandbox — Project Context for Claude Code

## What this repo is

A pedagogical sandbox for simulating Drill Stem Tests (DST) using JutulDarcy.jl,
with the goal of understanding how permeability (k) and porosity (φ) affect
Pressure Transient Analysis (PTA) curves. Not a production model — designed to be
simple, correct, and progressively more complex so learnings transfer to real setups.

---

## Language split

| Layer | Language | Purpose |
|---|---|---|
| Field generation | Python | Generate perm/poro/well-mask fields, save as .h5 |
| Config & orchestration | Python | YAML config, pydantic validation, run management |
| Simulation | Julia (JutulDarcy) | Reservoir simulation only — never touched by user |
| PTA analysis | Python | Bourdet derivative, Horner, pseudo-pressure |
| Plotting / notebooks | Python | matplotlib figures, Jupyter, HTML output |

The user works exclusively in Python and YAML. Julia is a black box invoked via
subprocess. The Python → Julia interface is: config JSON + field HDF5 in,
results HDF5 out.

---

## Project structure

```
dst_well_testing/
├── CLAUDE.md
├── Project.toml / Manifest.toml    ← Julia env (JutulDarcy, CairoMakie, HDF5)
├── configs/                        ← YAML experiment configs (tracked in git)
│   ├── single_phase_perm_sensitivity/
│   │   ├── base_k100_phi025.yaml
│   │   ├── var_k10_phi025.yaml
│   │   └── var_k1000_phi025.yaml
│   └── ...
├── fields/                         ← generated .h5 field files (gitignored)
├── outputs/                        ← simulation results (gitignored)
│   └── {experiment}/
│       └── {run}/
│           ├── config.yaml         ← copy of config for reproducibility
│           ├── results.h5
│           └── plots/
├── src/                            ← all Python source code
│   ├── config_schema.py            ← pydantic models for YAML validation
│   ├── simulation_model.py         ← SimulationModel class + .simulate()
│   ├── pta_analysis.py             ← Bourdet, Horner, pseudo-pressure
│   ├── plotting.py                 ← matplotlib figures, multi-run overlays
│   └── field_generator/            ← semi-independent subproject
│       ├── generate_field.py       ← CLI: template → fields/*.h5
│       └── templates/
│           ├── homogeneous.py
│           ├── fourier.py
│           └── gmm.py              ← facies-based (Truncated Gaussian Simulation)
├── julia_backend/
│   └── run_simulation.jl           ← reads config JSON + field .h5, writes results .h5
├── run_sim.py                      ← main CLI entry point
└── notebooks/                      ← Jupyter notebooks for analysis
```

---

## Experiment / run management

Two-level hierarchy:
- **Experiment**: a group of related runs exploring one physics question
  (e.g., "how does k affect PTA in single-phase oil?")
- **Run**: one specific simulation — typically a base case plus variations
  that perturb one parameter at a time

One YAML config = one run. Grouping is done by placing related configs in the
same subfolder under `configs/{experiment}/` and naming runs descriptively
(`base_k100_phi025`, `var_k10`, `var_high_phi`).

Cross-examination (overlaying multiple runs) happens in notebooks:
```python
exp = load_experiment('outputs/single_phase_perm_sensitivity/')
# returns {run_name: DSTResults} for all runs in that experiment
plot_bourdet_overlay(exp)
```

---

## YAML config schema

```yaml
experiment:
  name: single_phase_perm_sensitivity   # maps to outputs/{name}/{run}/
  run: base_k100_phi025
  description: "Base case, single-phase oil"

grid:
  nx: 50
  ny: 50
  nz: 1
  lx: 2000.0    # meters
  ly: 2000.0
  lz: 10.0

fluid:
  type: single_oil      # single_oil | oil_water | gas
  viscosity: 1.0e-3     # Pa·s
  compressibility: 1.0e-9  # Pa^-1
  # oil_water additional fields:
  # sw_init: 0.2
  # krw_max: 0.3
  # kro_max: 0.8
  # corey_nw: 2.0
  # corey_no: 2.0

rock:
  field_h5: fields/homogeneous_50x50.h5  # always required; contains perm, poro, well_mask

schedule:
  drawdown_duration_hr: 24
  buildup_duration_hr: 48
  rate_m3_day: 100.0
  steps_per_phase: 30

pta:
  bourdet_L: 0.2
```

---

## Field HDF5 schema

File: `fields/{name}.h5`

| Dataset | Shape | Dtype | Units |
|---|---|---|---|
| `/perm` | (nz, ny, nx) | float64 | m² (SI) |
| `/poro` | (nz, ny, nx) | float64 | dimensionless |
| `/well_mask` | (nz, ny, nx) | bool | True = well cell |

Array axis order is (z, y, x) throughout. Unit conversions (mD → m²) happen
in the field generator, not in the simulation backend.

Well location is a mask, not a coordinate. This supports the future interactive
2D drawing tool where the user paints well locations on the grid.

---

## Results HDF5 schema

File: `outputs/{experiment}/{run}/results.h5`

| Dataset | Shape | Description |
|---|---|---|
| `/time` | (n_steps,) | Time since start of drawdown, seconds |
| `/pressure_well` | (n_steps,) | Bottom-hole pressure, Pa |
| `/phase` | (n_steps,) | 0 = drawdown, 1 = buildup |

Additional datasets added per fluid case (e.g., `/saturation_water` for Case 2).

---

## Physics: single-phase slightly compressible oil only

The sandbox focuses on Bourdet derivative analysis for two questions:
1. **kh (perm-thickness)** — plateau height ∝ qBμ/(kh)
2. **Minimum connected volume** — boundary effect timing ∝ φ ct Vp

Single-phase oil is sufficient for both. Two-phase and gas were dropped:
they add complexity (rel-perm, pressure-dependent μ/Z) without contributing
to the core learning.

Setup:
- Fluid: `ImmiscibleSystem((LiquidPhase(),), reference_densities=(850.0,))`
- Reservoir: homogeneous or heterogeneous (via field HDF5), uniform initial pressure (~300 bar)
- Experiments vary k, h, or φ; analysis via Bourdet derivative

---

## DST schedule (same for all cases)

| Phase    | Duration | Control |
|---|---|---|
| Drawdown | 24 hours | Constant rate (surface liquid rate) |
| Buildup  | 48 hours | Shut-in (`DisabledControl()` or `TotalRateTarget(0.0)`) |

Timesteps: logarithmically spaced within each phase, ~30 steps per phase.
Fine at phase start (fast transient), coarser at end.

---

## Grid design

- Type: Cartesian (JutulDarcy has no native cylindrical mesh)
- Dimensions: 2000m × 2000m × 10m, single layer
- Cells: 50 × 50 × 1
- Boundary: closed (no-flow)
- Well: determined by `/well_mask` in field .h5 (center cell by default)

Verify boundary effects do not appear within 72h window:
`r_inv ≈ 0.032 * sqrt(k * t / φ μ ct)`

---

## Key Julia implementation notes

### Shut-in control
Use `DisabledControl()` — preferred. Fall back to `TotalRateTarget(0.0)` if it
causes compilation issues.

### Timestep + forces structure
```julia
forces_dd = setup_reservoir_forces(model, control = Dict(:WELL => producer_dd))
forces_bu = setup_reservoir_forces(model, control = Dict(:WELL => shut_in))
dt = [dt_drawdown; dt_buildup]
forces = [fill(forces_dd, length(dt_drawdown)); fill(forces_bu, length(dt_buildup))]
```

### Units — SI only, use built-in helpers
```julia
darcy = si_unit(:darcy)   # 9.869e-13 m²
bar   = si_unit(:bar)     # 1e5 Pa
day   = si_unit(:day)     # 86400 s
```
Do NOT use Unitful.jl.

### No wellbore storage
Peaceman well model does not include wellbore storage. Unit-slope early-time
line will not appear. Document this on plots.

### Near-well resolution
50×50 grid gives ~40m cells — coarse near wellbore. If early-time derivative
looks wrong, refine center region or increase to 80×80.

---

## Python environment

Conda env: `dst_well_testing` (Python 3.11)

| Package | Purpose |
|---|---|
| numpy, scipy | numerics, field generation |
| matplotlib | plotting |
| pandas | results tables |
| h5py | HDF5 I/O |
| pyyaml | YAML config loading |
| pydantic | config schema validation |
| geostatspy | geostatistical field generation (SGS) |
| welltestpy | PTA comparison library (Bourdet derivative) |
| jupyter | interactive analysis |

---

## Build order

1. ~~Conda env + Julia packages~~ ✓ done
2. ~~Install pyyaml, pydantic, geostatspy, plotly~~ ✓ done
3. ~~Update CLAUDE.md~~ ✓ done
4. ~~`src/field_generator/` + CLI~~ ✓ done
5. ~~`src/config_schema.py` — pydantic models~~ ✓ done
6. ~~`julia_backend/run_simulation.jl`~~ ✓ done (single-phase oil only)
7. `src/simulation_model.py` — Python wrapper that serializes YAML→JSON, runs Julia, reads HDF5 ← next
8. `run_sim.py` — CLI entry point
9. `src/pta_analysis.py` — Bourdet derivative + Horner
10. `src/plotting.py` — log-log diagnostic, multi-run overlay
11. Notebooks for kh and connected-volume experiments

Future TODOs:
- Propagate viscosity/compressibility from config to JutulDarcy (uses defaults now)

---

## How to run (target CLI)

```bash
# Generate a field
python src/field_generator/generate_field.py field_configs/homogeneous_100md.yaml

# Run a simulation
python run_sim.py --config configs/single_phase_perm_sensitivity/base_k100_phi025.yaml

# Results land in:
# outputs/single_phase_perm_sensitivity/base_k100_phi025/
```

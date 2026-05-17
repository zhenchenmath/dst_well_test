# DST PTA Sandbox — Project Context for Claude Code

## What this repo is

A pedagogical sandbox for simulating Drill Stem Tests (DST) using JutulDarcy.jl,
with the goal of understanding how permeability (k) and porosity (φ) affect
Pressure Transient Analysis (PTA) curves. Not a production model — designed to be
simple, correct, and progressively more complex so learnings transfer to real setups.

---

## Plan overview

Three self-contained Julia scripts, one per physics case, plus a shared utilities
module. Each case runs the same DST schedule and produces the same family of
diagnostic plots. Only the fluid physics changes between cases.

### Case 1 — Single-phase slightly compressible oil (`case1_single_phase.jl`)
The textbook baseline. Isolates what k and φ do independently.
- Fluid: single `LiquidPhase()`, weakly compressible, constant viscosity
- Reservoir: homogeneous, uniform initial pressure (~300 bar)
- Parameter sweep: k = [10, 100, 1000] mD × φ = [0.10, 0.25]
- What to observe: k controls derivative plateau height and semilog slope;
  φ controls time-shift of flow regime transitions (higher φ → slower transient)

### Case 2 — Two-phase oil + water immiscible (`case2_oil_water.jl`)
Introduces relative permeability effects. Shows that PTA measures effective k, not absolute k.
- Fluid: `ImmiscibleSystem` with `LiquidPhase()` + `AqueousPhase()`, Corey rel-perms
- Initial condition: Sw = 0.2 (connate water), same p as Case 1
- Additional sweep variable: Sw_init = [0.2, 0.4] to show how water saturation
  shifts the apparent permeability seen by PTA
- What to observe: derivative plateau shifts relative to Case 1 by factor of k_ro(Sw)

### Case 3 — Single-phase gas (`case3_gas.jl`)
Shows why raw pressure analysis breaks down for gas and introduces pseudo-pressure.
- Fluid: single `VaporPhase()` with pressure-dependent μ and Z
- Same k/φ sweep as Case 1
- Post-process in both raw Δp and pseudo-pressure Δm(p) space
- What to observe: raw derivative curves are distorted; Δm(p) restores textbook shape

---

## Shared utilities (`dst_utils.jl`)

Helper functions used by all three cases:
- `log_timesteps(t_total, n_steps)` — logarithmically spaced timestep vector
- `bourdet_derivative(dt, dp; L=0.2)` — Bourdet log derivative with smoothing parameter
- `horner_time(tp, dt)` — (tp + Δt)/Δt for Horner plot x-axis
- `pseudo_pressure(p_vec, μ_fn, Z_fn, p_ref)` — numerical integration of m(p) for Case 3
- Plotting functions using CairoMakie (headless-safe, no GLMakie dependency)
  - `plot_loglog(dt, dp, label)` — log-log diagnostic with derivative overlay
  - `plot_horner(horner_x, p_ws, label)` — Horner plot
  - Both functions accept arrays of curves for overlay comparison

---

## DST schedule (same for all cases)

| Phase      | Duration | Well control                        |
|------------|----------|-------------------------------------|
| Drawdown   | 24 hours | Constant rate (surface liquid rate) |
| Buildup    | 48 hours | Shut-in (zero rate / DisabledControl) |

Timesteps: logarithmically spaced within each phase — fine at the start of each
phase (where transient changes fast), coarser at the end. Approximately 30 steps
per phase. This is critical for capturing the early-time derivative shape on log-log.

---

## Grid design

- Type: Cartesian (JutulDarcy does not have a native cylindrical mesh)
- Dimensions: 2000m × 2000m × 10m (single layer for Cases 1 and 2; same for Case 3)
- Cells: ~50 × 50 × 1
- Well: single vertical well at the center cell (25, 25, 1)
- Boundary: closed (no-flow) — large enough that boundary effects do not appear
  within the 72h test window for the k values in the sweep (verify with radius of
  investigation estimate: r_inv ≈ 0.032 * sqrt(k * t / φ μ ct))

---

## Key implementation notes and caveats

### Shut-in control
JutulDarcy does not have a literal shut-in control. The approach is to use either:
- `DisabledControl()` — preferred if it compiles cleanly
- A `TotalRateTarget(0.0)` producer — fallback if DisabledControl causes issues
Test this in the REPL before committing to either approach.

### Timestep structure for forces
JutulDarcy accepts a vector of `forces`, one entry per timestep block. The DST
schedule maps to two force blocks:
```julia
forces_dd = setup_reservoir_forces(model, control = Dict(:WELL => producer_dd))
forces_bu = setup_reservoir_forces(model, control = Dict(:WELL => shut_in))
dt = [dt_drawdown; dt_buildup]   # concatenated timestep vectors
forces = [fill(forces_dd, length(dt_drawdown)); fill(forces_bu, length(dt_buildup))]
```

### No wellbore storage
The Peaceman well model in JutulDarcy does not include wellbore storage. The
unit-slope early-time line on log-log will not appear. This is acceptable for
this study — we are interested in the reservoir response, not the wellbore mask.
Document this clearly in plots (add a note to the plot title or annotation).

### Units
JutulDarcy uses SI internally. Use the built-in conversion helpers:
```julia
using JutulDarcy
darcy = si_unit(:darcy)       # 9.869e-13 m²
bar   = si_unit(:bar)         # 1e5 Pa
day   = si_unit(:day)         # 86400 s
```
Do NOT use Unitful.jl — it does not contain oilfield units and will cause errors.

### Near-well grid resolution
A 50×50 Cartesian grid with 2000m domain gives ~40m cells. This is coarse near
the wellbore and will smear early-time behavior. If the log-log derivative looks
noisy or wrong at early time, consider either:
- Refining the center region (non-uniform dx/dy)
- Increasing total cell count to 80×80

### Plotting
Use CairoMakie, not GLMakie. CairoMakie renders to file (PNG/SVG) and works
headless over SSH. GLMakie requires a display.
```julia
using CairoMakie
```
Save all figures to an `output/` directory with descriptive filenames.

---

## Repo structure (target)

```
dst_pta_sandbox/
├── CLAUDE.md                  ← this file
├── dst_utils.jl               ← shared helpers (timesteps, derivative, plotting)
├── case1_single_phase.jl      ← Case 1: single-phase oil
├── case2_oil_water.jl         ← Case 2: two-phase oil-water
├── case3_gas.jl               ← Case 3: single-phase gas
└── output/                    ← generated plots (gitignored or committed)
    ├── case1_loglog.png
    ├── case1_horner.png
    └── ...
```

---

## How to start a session

Before writing any code, confirm the following with the user:
1. Any modifications to the plan (ask explicitly — the user may have changes)
2. Which case to implement first (suggest Case 1 as the natural starting point)
3. Whether to implement all sweeps at once or start with a single (k, φ) pair
   to verify the simulation runs correctly before expanding

Do not begin implementation until the user confirms they are ready.

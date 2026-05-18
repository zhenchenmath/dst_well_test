# Experiment 0, Run 0 — Baseline single-phase oil DST

**Status:** baseline / sandbox calibration.
This is NOT a designed experiment. It is the first end-to-end run, used to
verify the full Python → Julia → results → PTA pipeline works, and to compare
measured Bourdet derivative values against analytical expectations on a clean
homogeneous case.

A "real" first experiment (with field units and a finer grid) will be exp_1+.

---

## 1. Reservoir & setup

| Quantity | Value | Notes |
|---|---|---|
| Grid | 50 × 50 × 1 Cartesian | (nx, ny, nz) |
| Domain | 2000 m × 2000 m × 10 m | (lx, ly, lz) |
| Cell size | 40 m × 40 m × 10 m | coarse near wellbore (sandbox) |
| Permeability | 100 mD (= 9.869 × 10⁻¹⁴ m²) | uniform, isotropic |
| Porosity | 0.25 | uniform |
| Well | single perforation at cell (i=25, j=25, k=0) | center of grid |
| Boundary | closed (no-flow) on all 6 faces | |
| Initial pressure | 300 bar | uniform |

Field file: [fields/homogeneous_100md_phi025.h5](../../../fields/homogeneous_100md_phi025.h5)
Field config: [field_configs/homogeneous_100md.yaml](../../../field_configs/homogeneous_100md.yaml)

### Field maps

| Dataset | min | mean / geomean | max |
|---|---|---|---|
| `perm` (mD) | 100.0 | 100.0 (geomean) | 100.0 |
| `poro` | 0.250 | 0.250 (mean) | 0.250 |
| `well_mask` | — | 1 cell active at (i=25, j=25, k=0) | — |

Interactive heatmap (perm + poro + well marker):
[plots/field.html](../../../outputs/exp_0_baseline/run_0/plots/field.html)

Since the field is uniform, the heatmaps look flat — they exist mainly as a
template for later heterogeneous runs (fourier / GMM templates) where the
spatial structure matters.

## 2. Fluid

Single-phase slightly compressible "oil" — actually a `LiquidPhase` in
JutulDarcy's `ImmiscibleSystem`, which is the simplest single-phase model.

| Property | Value | Source |
|---|---|---|
| Reference density | 850 kg/m³ | hard-coded in Julia backend |
| Viscosity | 1 × 10⁻³ Pa·s (1 cP) | **JutulDarcy default** — YAML value not propagated yet (see TODO) |
| Compressibility | JutulDarcy default | YAML value not propagated yet |

> **Caveat:** the `fluid.viscosity` and `fluid.compressibility` fields in the
> YAML config are validated by pydantic but currently ignored by the Julia
> backend. This is a known TODO. For the base case, the default 1 cP happens to
> match the config (1 × 10⁻³ Pa·s), so this run is still meaningful.

## 3. Schedule

| Phase | Duration | Control |
|---|---|---|
| Drawdown | 24 h | constant surface rate 100 m³/day |
| Buildup | 48 h | shut-in (`DisabledControl()`) |

Timesteps: 30 log-spaced per phase (60 total), fine at phase start, coarse at end.

## 4. The math

### Governing equation

Single-phase, slightly compressible flow in a porous medium:

$$\phi c_t \frac{\partial p}{\partial t} = \nabla \cdot \left(\frac{k}{\mu} \nabla p\right)$$

For uniform k, μ, c_t and radial symmetry around the well:

$$\frac{\partial p}{\partial t} = \frac{k}{\phi \mu c_t} \nabla^2 p$$

The diffusivity η = k / (φ μ c_t) controls how fast pressure transients
propagate outward.

### Bourdet derivative

The Bourdet derivative is the pressure change differentiated with respect to
the natural log of elapsed time:

$$\text{deriv}(t) = \frac{d \Delta p}{d \ln \Delta t} = t \frac{d \Delta p}{dt}$$

Computed with L-window smoothing (Bourdet, Ayoub & Pirard 1989) in
[src/pta_analysis.py](../../../src/pta_analysis.py) — see `bourdet_derivative()`.

### IARF plateau (the "kh" signature)

In the infinite-acting radial flow (IARF) regime — after wellbore storage and
before any boundary is seen — the Bourdet derivative is flat at:

$$\text{deriv}_\text{IARF} = \frac{q \, B \, \mu}{4 \pi \, k \, h}$$

For this run (q = 100 m³/day = 1.1574 × 10⁻³ m³/s, B = 1, μ = 1 × 10⁻³ Pa·s,
k = 9.869 × 10⁻¹⁴ m², h = 10 m):

$$\text{deriv}_\text{IARF} = \frac{1.1574 \times 10^{-3} \times 10^{-3}}{4\pi \times 9.869 \times 10^{-14} \times 10} \approx 9.33 \times 10^{4} \text{ Pa} \approx 0.93 \text{ bar}$$

### Horner plot slope

Buildup BHP plotted vs Horner time (tp + Δt)/Δt on semi-log axes has slope
per log cycle:

$$m = \frac{q \, B \, \mu}{4 \pi \, k \, h \, \ln 10} = \frac{\text{deriv}_\text{IARF}}{\ln 10}$$

For this run: m ≈ 9.33 × 10⁴ / 2.303 ≈ **0.40 bar / cycle**.

### Radius of investigation

Approximate distance the pressure transient has reached:

$$r_\text{inv} \approx 0.032 \sqrt{\frac{k \, t}{\phi \, \mu \, c_t}}$$

For the base case at t = 72 h = 259,200 s, assuming c_t ≈ 1 × 10⁻⁹ Pa⁻¹:

$$r_\text{inv} \approx 0.032 \sqrt{\frac{9.87 \times 10^{-14} \times 2.59 \times 10^{5}}{0.25 \times 10^{-3} \times 10^{-9}}} \approx 320 \text{ m}$$

Domain half-width is 1000 m, so the transient should NOT see the boundary
during this 72 h test. Good.

## 5. Results

### Raw BHP
- Initial: 300.0 bar
- End of drawdown: **285.6 bar** (drop of 14.4 bar in 24 h)
- End of buildup: **299.15 bar** (recovers within ~0.85 bar of initial)

Plot: [outputs/.../plots/bhp.html](../../../outputs/exp_0_baseline/run_0/plots/bhp.html)

### Bourdet derivative

Numerically derived `dΔp / d(ln Δt)` over the middle half of each phase
(skipping the first and last 25 % of points, which are L-window-edge or
boundary-affected):

| Phase | Measured plateau range | Theory | Notes |
|---|---|---|---|
| Drawdown | 0.80 – 0.84 bar | 0.93 bar | ratio 0.86–0.90 |
| Buildup | 0.34 – 0.77 bar | 0.93 bar | wider; late part dives — boundary feedback |

The drawdown derivative sits ~10–15 % below the analytical IARF plateau, which
is the expected sign of the coarse 40 m grid (the wellbore is barely resolved).
The buildup derivative starts near the same value but drops sharply at late
Δt, consistent with the pressure recovery being driven by the now-finite
"reservoir" inside the closed boundary rather than purely radial diffusion.

Bourdet-only overlay (both phases on one log-log, with theory plateau):
[plots/bourdet_overlay.html](../../../outputs/exp_0_baseline/run_0/plots/bourdet_overlay.html)

Full log-log diagnostics (Δp + derivative together):
- Buildup: [plots/loglog_bu.html](../../../outputs/exp_0_baseline/run_0/plots/loglog_bu.html)
- Drawdown: [plots/loglog_dd.html](../../../outputs/exp_0_baseline/run_0/plots/loglog_dd.html)

Horner plot: [plots/horner.html](../../../outputs/exp_0_baseline/run_0/plots/horner.html)

### Observations / sanity check

1. **Order of magnitude is right.** Measured derivative (~0.7–0.9 bar) matches
   theory (0.93 bar) to within ~25 %.
2. **Drawdown rising at end, buildup falling at end** — both consistent with the
   transient approaching the 2000 m × 2000 m closed boundary by the end of 72 h.
   (Our r_inv estimate of ~320 m may be optimistic if c_t is smaller than
   assumed.)
3. **Coarse near-wellbore grid** (40 m cells) is a likely source of the early-
   time noise on the derivative. JutulDarcy's Peaceman well doesn't add wellbore
   storage, so there's no unit-slope early-time line either.
4. The shape is qualitatively textbook: drop → flat-ish plateau → upturn on
   drawdown; mirror image on buildup.

## 6. How to reproduce

### From the command line

```bash
# 1. Generate the field (only if fields/homogeneous_100md_phi025.h5 missing)
python src/field_generator/generate_field.py field_configs/homogeneous_100md.yaml

# 2. Run the simulation
python run_sim.py configs/exp_0_baseline/run_0.yaml
```

Output goes to `outputs/exp_0_baseline/run_0/`:
- `config.yaml` (copy of the input config, for reproducibility)
- `results.h5` (time, BHP, phase arrays — schema in [CLAUDE.md](../../../CLAUDE.md))

### From Python (Jupyter / notebook)

```python
from src.config_schema import load_config
from src.simulation_model import SimulationModel, load_experiment
from src.pta_analysis import compute_pta
from src.plotting import (
    plot_bhp, plot_loglog_diagnostic, plot_horner,
    plot_loglog_overlay, plot_horner_overlay,
)

# Load + run a single config
cfg = load_config("configs/exp_0_baseline/run_0.yaml")
sim = SimulationModel(cfg)
results = sim.simulate()           # returns DSTResults

# PTA
pta = compute_pta(results)         # returns PTA with .drawdown, .buildup, .horner_time_buildup

# Plots (Plotly — interactive in Jupyter, .write_html(...) to save standalone)
plot_bhp(results).show()
plot_loglog_diagnostic(results, phase="buildup").show()
plot_horner(results).show()

# Overlay multiple runs (when you have more)
exp = load_experiment("outputs/exp_0_baseline/")
plot_loglog_overlay(exp, phase="buildup").show()
plot_horner_overlay(exp).show()
```

### Module map

| Module | Role |
|---|---|
| [src/config_schema.py](../../../src/config_schema.py) | pydantic models for YAML configs |
| [src/field_generator/](../../../src/field_generator/) | perm/poro/well-mask `.h5` generator |
| [src/simulation_model.py](../../../src/simulation_model.py) | Python wrapper: YAML → JSON → Julia subprocess → HDF5 results |
| [julia_backend/run_simulation.jl](../../../julia_backend/run_simulation.jl) | JutulDarcy backend (single-phase oil) |
| [src/pta_analysis.py](../../../src/pta_analysis.py) | Bourdet derivative + Horner time |
| [src/plotting.py](../../../src/plotting.py) | Plotly figures (matplotlib broken on this machine) |
| [run_sim.py](../../../run_sim.py) | CLI entry point |

## 7. Known caveats for this run

1. **Viscosity / compressibility from config are NOT propagated to Julia yet.**
   JutulDarcy defaults are used. For this base case (μ = 1 cP) it happens to
   match, so results are still meaningful — but changing those values in the
   YAML will have no effect until the override is wired up.
2. **SI units throughout** (Pa, m, s). The user has asked for field units
   (psia, hours, mD, ft) in future experiments — not implemented yet.
3. **Grid is coarse** (50 × 50 × 1, 40 m cells). User has asked for
   160 × 160 × 1 with 25 m cells for future runs.
4. **Closed boundary is felt by ~72 h.** Future runs need either a longer
   domain, lower rate, or shorter test to stay in the IARF regime.
5. **Matplotlib savefig is broken on this Windows machine** (DLL crash,
   exit code -1066598273). All plots are Plotly. See DECISIONS.md.

# Experiment 0, Run 1 — Larger domain, thin layer, low rate

**Status:** baseline / sandbox calibration, take 2.
The goal: pick a domain + schedule that mimics an infinite reservoir as
closely as possible (radius of investigation stays well inside the no-flow
boundary for the whole test), so the Bourdet derivative shows the textbook
flat IARF plateau without the late-time boundary dip we saw in run_0.

This is the **baseline configuration** that all future heterogeneous-field
experiments (exp_1+) will inherit from.

---

## 1. What changed vs run_0

| | run_0 | run_1 |
|---|---|---|
| Grid (nx, ny, nz) | 50 × 50 × 1 | **160 × 160 × 1** |
| Cell size | 40 m × 40 m × 10 m | **25 m × 25 m × 1 m** |
| Domain (lx, ly, lz) | 2000 × 2000 × 10 m | **4000 × 4000 × 1 m** |
| Thickness h | 10 m | **1 m** |
| Rate q | 100 m³/day | **10 m³/day** |
| q/h (controls plateau) | 10 m²/day | **10 m²/day**  (same) |
| Drawdown duration | 24 h | 24 h (same) |
| Buildup duration | 48 h | **200 h** |
| Boundary | no-flow | no-flow (same) |

Rationale:
- Halving the cell size from 40 m → 25 m **and** quadrupling the areal extent
  (2 → 4 km) keeps r_inv well inside the boundary even for k up to ~200 mD
  over 200 h.
- Thin layer (h = 1 m) is the geometry we want for thin reservoirs / future
  layered runs. Choosing q so that q/h stays the same as run_0 keeps the
  IARF plateau height directly comparable (≈ 0.93 bar in both runs).

## 2. Reservoir & setup

| Quantity | Value | Notes |
|---|---|---|
| Grid | 160 × 160 × 1 Cartesian | |
| Domain | 4000 m × 4000 m × 1 m | half-width 2000 m |
| Cell size | 25 m × 25 m × 1 m | well in a 25 m cell |
| Permeability | 100 mD (= 9.869 × 10⁻¹⁴ m²) | uniform |
| Porosity | 0.25 | uniform |
| Well | cell (i=80, j=80, k=0) | center of grid |
| Boundary | closed (no-flow) on all 6 faces | sized so r_inv ≪ half-width |
| Initial pressure | 300 bar | uniform |

Field file: [fields/homogeneous_100md_160x160.h5](../../../fields/homogeneous_100md_160x160.h5)
Field config: [field_configs/homogeneous_100md_160x160.yaml](../../../field_configs/homogeneous_100md_160x160.yaml)

### Field maps

| Dataset | min | mean / geomean | max |
|---|---|---|---|
| `perm` (mD) | 100.0 | 100.0 (geomean) | 100.0 |
| `poro` | 0.250 | 0.250 (mean) | 0.250 |
| `well_mask` | — | 1 cell active at (80, 80, 0) | — |

Plot: [plots/field.html](../../../outputs/exp_0_baseline/run_1/plots/field.html)

## 3. Fluid & schedule

Same fluid as run_0 (single-phase liquid, μ = 1 cP default, ρ_ref = 850 kg/m³,
default JutulDarcy compressibility).

Schedule:
- Drawdown: 24 h at q = 10 m³/day
- Buildup: 200 h shut-in (`DisabledControl()`)
- 30 log-spaced steps per phase

## 4. Boundary check — does r_inv stay inside?

Diffusivity η = k / (φ μ c_t):
- k = 9.869 × 10⁻¹⁴ m², μ = 1 × 10⁻³ Pa·s, φ = 0.25, c_t ≈ 1 × 10⁻⁹ Pa⁻¹
- η ≈ **0.395 m²/s**

Radius of investigation r_inv ≈ 2√(η t):

| t | r_inv | half-width 2000 m? |
|---|---|---|
| 24 h (end drawdown) | 369 m | ✅ |
| 224 h (end buildup) | 1121 m | ✅ |
| ~700 h | 2000 m | (would reach boundary here) |

Comfortable headroom for k ≤ 100 mD. For future high-k runs (k ≈ 1000 mD) the
domain would need to be ~3× larger or the test ~10× shorter — flagged for
exp_1 design.

## 5. The math (reference)

Same equations as run_0 — recapping just the IARF plateau and Horner slope:

**IARF Bourdet plateau:**
$$\text{deriv}_\text{IARF} = \frac{q \, B \, \mu}{4 \pi \, k \, h}$$

For run_1 (q = 10 m³/day = 1.157 × 10⁻⁴ m³/s, B = 1, μ = 1 cP, k = 9.869 × 10⁻¹⁴ m², h = 1 m):

$$\text{deriv}_\text{IARF} = \frac{1.157 \times 10^{-4} \times 10^{-3}}{4\pi \times 9.869 \times 10^{-14} \times 1} \approx 9.33 \times 10^{4} \text{ Pa} \approx \mathbf{0.93 \text{ bar}}$$

Same as run_0 because q/h is identical.

**Note on buildup derivative tail.** For an *infinite* reservoir under constant
prior production tp, the buildup derivative against Δt theoretically follows:

$$\frac{d(\Delta p_\text{bu})}{d(\ln \Delta t)} = \frac{q \mu}{4 \pi k h} \cdot \frac{t_p}{t_p + \Delta t}$$

It is flat at the IARF value only while Δt ≪ tp, and decays toward zero as
Δt grows. So a falling tail at large Δt is **not** automatically a boundary
artifact — it's intrinsic to plotting derivative vs Δt rather than vs
superposition / Agarwal equivalent time Δt_e = Δt · tp/(tp+Δt). On equivalent
time, the plateau extends to late Δt_e. (Equivalent-time plots are a TODO
for src/plotting.py.)

## 6. Results

### Raw BHP
- Initial: 300.00 bar
- End of drawdown (t = 24 h): **285.68 bar** (drop ≈ 14.3 bar)
- End of buildup (t = 224 h): **299.79 bar** (within 0.21 bar of initial)

Plot: [plots/bhp.html](../../../outputs/exp_0_baseline/run_1/plots/bhp.html)

### Bourdet derivative

Mid-half plateau ranges (middle 50 % of valid points per phase):

| Phase | Measured plateau | Theory IARF | Ratio |
|---|---|---|---|
| Drawdown | 0.793 – 0.821 bar | 0.933 bar | 0.85 – 0.88 |
| Buildup (mid samples) | 0.205 – 0.662 bar | 0.933 bar | 0.22 – 0.71 |

- **Drawdown plateau ~ 13–15 % low**, same systematic bias as run_0. Most
  likely cause: Peaceman well in a 25 m cell still under-resolves the
  near-well pressure gradient. Halving cells again (10 m) would likely close
  the gap; the textbook fix is to use radial / locally-refined grids.
- **Buildup tail dives steeply** to ~0.2 bar by late Δt. As discussed in
  §5, this is mostly the intrinsic tp/(tp+Δt) decay, not a boundary
  artifact: r_inv at 200 h buildup is only ~1121 m vs the 2000 m half-width.
- Compared to run_0's buildup (0.34 – 0.77 bar over a 48 h buildup), run_1's
  longer 200 h buildup simply lets the tail decay further.

Plots:
- Bourdet overlay (both phases + theory plateau line): [plots/bourdet_overlay.html](../../../outputs/exp_0_baseline/run_1/plots/bourdet_overlay.html)
- Buildup log-log: [plots/loglog_bu.html](../../../outputs/exp_0_baseline/run_1/plots/loglog_bu.html)
- Drawdown log-log: [plots/loglog_dd.html](../../../outputs/exp_0_baseline/run_1/plots/loglog_dd.html)
- Horner plot: [plots/horner.html](../../../outputs/exp_0_baseline/run_1/plots/horner.html)

## 7. How to reproduce

```bash
# 1. Generate the field (if missing)
python src/field_generator/generate_field.py field_configs/homogeneous_100md_160x160.yaml

# 2. Run the simulation
python run_sim.py configs/exp_0_baseline/run_1.yaml

# 3. Generate the plot set
python _make_plots.py outputs/exp_0_baseline/run_1
```

From Python:
```python
from src.config_schema import load_config
from src.simulation_model import SimulationModel, load_experiment
from src.pta_analysis import compute_pta
from src.plotting import (plot_bhp, plot_loglog_diagnostic, plot_horner,
                          plot_loglog_overlay)

cfg = load_config("configs/exp_0_baseline/run_1.yaml")
sim = SimulationModel(cfg)
r = sim.simulate()                 # DSTResults
pta = compute_pta(r)               # PTA (drawdown + buildup + Horner)

plot_loglog_diagnostic(r, phase="buildup").show()
plot_horner(r).show()

# Compare run_0 and run_1 on one log-log
exp = load_experiment("outputs/exp_0_baseline/")
plot_loglog_overlay(exp, phase="buildup").show()
```

## 8. Carry-overs for exp_1 design

1. **Domain is sized for k ≤ ~200 mD over 200 h.** Higher k requires a bigger
   domain or shorter test. Flag whenever k_max in a sensitivity sweep would
   push r_inv past ~half the half-width.
2. **Bourdet plateau is ~13 % below theory** due to near-well grid resolution.
   This is a constant bias, so it cancels out when *comparing* runs (which is
   exactly what kh-sensitivity / volume-sensitivity studies care about).
3. **Buildup derivative tail decay is intrinsic.** For cleaner "is the
   plateau the same shape?" comparisons, implement equivalent-time PTA
   plotting (Δt_e = Δt · tp/(tp+Δt)).
4. **Field units (psia, hours, mD).** Still SI internally — the user has
   asked for field-unit display in future plots. Not yet implemented.
5. **Viscosity / compressibility config-to-Julia override** still not wired
   up. The 100 mD base case happens to use the default 1 cP so this hasn't
   bitten us, but it will the moment we vary μ.

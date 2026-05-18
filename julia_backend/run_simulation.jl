#!/usr/bin/env julia
# DST simulation backend - single-phase slightly compressible oil.
#
# Usage (from repo root):
#   julia --project=. julia_backend/run_simulation.jl path/to/config.json
#
# Reads: JSON config (serialized from Python DSTConfig) + field HDF5 path inside.
# Writes: outputs/{experiment}/{run}/results.h5  with /time /pressure_well /phase

using JutulDarcy
using HDF5
using JSON

function log_timesteps(total_s::Float64, n::Int)
    # n log-spaced steps summing to total_s, last/first ratio ~100x
    w = exp.(range(0.0, log(100.0), length=n))
    w .* (total_s / sum(w))
end

function main()
    length(ARGS) == 1 || error("Usage: julia run_simulation.jl <config.json>")
    cfg = JSON.parsefile(ARGS[1])

    # --- grid ---
    nx, ny, nz = cfg["grid"]["nx"], cfg["grid"]["ny"], cfg["grid"]["nz"]
    lx, ly, lz = cfg["grid"]["lx"], cfg["grid"]["ly"], cfg["grid"]["lz"]

    # --- field (h5py writes C-order (nz,ny,nx); Julia HDF5 reads as (nx,ny,nz)) ---
    perm_j, poro_j, well_mask_j = h5open(cfg["rock"]["field_h5"], "r") do f
        read(f, "perm"), read(f, "poro"), read(f, "well_mask")
    end
    perm_vec   = vec(perm_j)                      # m², x-fastest
    poro_vec   = vec(poro_j)
    well_cells = findall(!=(0), vec(well_mask_j))
    @assert !isempty(well_cells) "well_mask has no True cells"

    # --- fluid (single_oil only) ---
    fluid = cfg["fluid"]
    @assert fluid["type"] == "single_oil" "Only single_oil supported (Case 1)"
    # NOTE: viscosity and compressibility from config are NOT propagated yet;
    # JutulDarcy defaults are used (viscosity ≈ 1e-3 Pa·s = our base case).
    # Acceptable for first prototype. Wire up via parameters override later.

    # --- schedule ---
    sch = cfg["schedule"]
    dt_dd = log_timesteps(Float64(sch["drawdown_duration_hr"]) * 3600.0, Int(sch["steps_per_phase"]))
    dt_bu = log_timesteps(Float64(sch["buildup_duration_hr"])  * 3600.0, Int(sch["steps_per_phase"]))
    dt    = vcat(dt_dd, dt_bu)
    rate_m3s = Float64(sch["rate_m3_day"]) / 86400.0

    # --- model ---
    mesh   = JutulDarcy.CartesianMesh((nx, ny, nz), (Float64(lx), Float64(ly), Float64(lz)))
    domain = reservoir_domain(mesh; permeability=perm_vec, porosity=poro_vec)
    sys    = ImmiscibleSystem((LiquidPhase(),), reference_densities=(850.0,))
    well   = setup_well(domain, well_cells; name=:WELL)
    model  = setup_reservoir_model(domain, sys; wells=well)

    # --- initial state ---
    # NOTE: viscosity from config (mu=$mu Pa·s) is NOT propagated; JutulDarcy default is used.
    # Default = 1e-3 Pa·s. Set it once API is confirmed (see _probe.jl iteration).
    state0 = setup_reservoir_state(model, Pressure = 300.0 * 1e5)   # 300 bar

    # --- controls + forces ---
    ctrl_dd = ProducerControl(TotalRateTarget(-rate_m3s))   # negative = production
    ctrl_bu = DisabledControl()
    forces  = vcat(
        fill(setup_reservoir_forces(model; control=Dict(:WELL => ctrl_dd)), length(dt_dd)),
        fill(setup_reservoir_forces(model; control=Dict(:WELL => ctrl_bu)), length(dt_bu)),
    )

    # --- simulate (precond=:ilu0 avoids CPR StaticMatrix assertion for single-phase) ---
    println("Simulating $(length(dt)) steps ($(length(dt_dd)) drawdown + $(length(dt_bu)) buildup)...")
    r = simulate_reservoir(state0, model, dt;
                            forces     = forces,
                            precond    = :ilu0,
                            info_level = -1)

    # --- extract results ---
    time_s = r.time                              # cumulative seconds from drawdown start
    bhp    = r.wells[:WELL][:bhp]                # Pa
    phase  = vcat(fill(0, length(dt_dd)), fill(1, length(dt_bu)))

    # --- write HDF5 ---
    out_dir = joinpath("outputs", cfg["experiment"]["name"], cfg["experiment"]["run"])
    mkpath(out_dir)
    out_path = joinpath(out_dir, "results.h5")
    h5open(out_path, "w") do f
        f["time"]          = collect(time_s)
        f["pressure_well"] = collect(bhp)
        f["phase"]         = phase
    end

    println("Wrote: $out_path")
    println("  BHP range: $(round(minimum(bhp)/1e5, digits=2)) - $(round(maximum(bhp)/1e5, digits=2)) bar")
end

main()

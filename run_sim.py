#!/usr/bin/env python3
"""
DST simulation CLI.

Usage:
    python run_sim.py configs/single_phase_perm_sensitivity/base_k100_phi025.yaml
"""

import argparse
import sys

from src.config_schema import load_config
from src.simulation_model import SimulationModel


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a DST simulation from a YAML config.")
    parser.add_argument("config", help="Path to YAML config")
    parser.add_argument("--quiet", action="store_true", help="Suppress Julia stdout")
    args = parser.parse_args()

    cfg = load_config(args.config)
    print(f"Experiment: {cfg.experiment.name} / {cfg.experiment.run}")
    print(f"Output dir: {cfg.output_dir}")

    sim = SimulationModel(cfg)
    r = sim.simulate(verbose=not args.quiet)

    print(f"\nDone. n_steps={len(r.time)}  "
          f"BHP {r.pressure_well.min()/1e5:.2f}–{r.pressure_well.max()/1e5:.2f} bar  "
          f"({r.drawdown_mask.sum()} dd + {r.buildup_mask.sum()} bu)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

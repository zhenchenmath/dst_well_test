"""
SimulationModel: Python wrapper around the JutulDarcy backend.

Usage:
    from src.config_schema import load_config
    from src.simulation_model import SimulationModel

    cfg = load_config('configs/.../base.yaml')
    sim = SimulationModel(cfg)
    results = sim.simulate()
    results.time, results.pressure_well, results.phase
"""

from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

import h5py
import numpy as np
import yaml

from src.config_schema import DSTConfig

JULIA_SCRIPT = Path("julia_backend/run_simulation.jl")


@dataclass
class DSTResults:
    """Loaded contents of results.h5."""
    time: np.ndarray          # seconds since drawdown start
    pressure_well: np.ndarray # Pa
    phase: np.ndarray         # 0 = drawdown, 1 = buildup
    config: DSTConfig         # the config that produced these results
    results_path: Path

    @property
    def drawdown_mask(self) -> np.ndarray:
        return self.phase == 0

    @property
    def buildup_mask(self) -> np.ndarray:
        return self.phase == 1

    @classmethod
    def from_h5(cls, path: Path, config: DSTConfig) -> "DSTResults":
        with h5py.File(path, "r") as f:
            return cls(
                time=f["time"][:],
                pressure_well=f["pressure_well"][:],
                phase=f["phase"][:],
                config=config,
                results_path=path,
            )


class SimulationModel:
    def __init__(self, config: DSTConfig, julia_project: str = "."):
        self.config = config
        self.julia_project = julia_project

    def simulate(self, verbose: bool = True) -> DSTResults:
        """Serialize config → JSON, run Julia subprocess, read results back."""
        out_dir = self.config.output_dir
        out_dir.mkdir(parents=True, exist_ok=True)

        # Save a copy of the config for reproducibility
        with open(out_dir / "config.yaml", "w") as f:
            yaml.safe_dump(self.config.model_dump(), f, sort_keys=False)

        # Write JSON config to a tempfile and run Julia
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, encoding="utf-8"
        ) as tmp:
            json.dump(self.config.model_dump(), tmp)
            tmp_path = Path(tmp.name)

        try:
            cmd = ["julia", f"--project={self.julia_project}", str(JULIA_SCRIPT), str(tmp_path)]
            if verbose:
                print(f"$ {' '.join(cmd)}")
            result = subprocess.run(cmd, capture_output=True, text=True)
            if verbose and result.stdout:
                print(result.stdout)
            if result.returncode != 0:
                raise RuntimeError(
                    f"Julia simulation failed (exit {result.returncode}):\n"
                    f"--- stdout ---\n{result.stdout}\n"
                    f"--- stderr ---\n{result.stderr}"
                )
        finally:
            tmp_path.unlink(missing_ok=True)

        results_h5 = out_dir / "results.h5"
        if not results_h5.exists():
            raise RuntimeError(f"Julia finished but no results.h5 at {results_h5}")
        return DSTResults.from_h5(results_h5, self.config)


def load_experiment(experiment_dir: str | Path) -> dict[str, DSTResults]:
    """Load all runs under outputs/{experiment}/ for cross-examination."""
    experiment_dir = Path(experiment_dir)
    out = {}
    for run_dir in sorted(experiment_dir.iterdir()):
        results_h5 = run_dir / "results.h5"
        config_yaml = run_dir / "config.yaml"
        if results_h5.exists() and config_yaml.exists():
            with open(config_yaml) as f:
                cfg = DSTConfig.model_validate(yaml.safe_load(f))
            out[run_dir.name] = DSTResults.from_h5(results_h5, cfg)
    return out

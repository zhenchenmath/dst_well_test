from pathlib import Path
from typing import Annotated, Literal, Union

import yaml
from pydantic import BaseModel, Field, field_validator


class ExperimentConfig(BaseModel):
    name: str
    run: str
    description: str = ""


class GridConfig(BaseModel):
    nx: int = Field(gt=0)
    ny: int = Field(gt=0)
    nz: int = Field(default=1, gt=0)
    lx: float = Field(default=2000.0, gt=0)
    ly: float = Field(default=2000.0, gt=0)
    lz: float = Field(default=10.0, gt=0)


class SingleOilFluid(BaseModel):
    type: Literal["single_oil"]
    viscosity: float = Field(gt=0, description="Pa·s")
    compressibility: float = Field(gt=0, description="Pa⁻¹")


class OilWaterFluid(BaseModel):
    type: Literal["oil_water"]
    viscosity: float = Field(gt=0, description="Pa·s")
    compressibility: float = Field(gt=0, description="Pa⁻¹")
    sw_init: float = Field(gt=0, lt=1)
    krw_max: float = Field(gt=0, le=1)
    kro_max: float = Field(gt=0, le=1)
    corey_nw: float = Field(gt=0)
    corey_no: float = Field(gt=0)


class GasFluid(BaseModel):
    type: Literal["gas"]
    viscosity: float = Field(gt=0, description="Pa·s")
    compressibility: float = Field(gt=0, description="Pa⁻¹")


FluidConfig = Annotated[
    Union[SingleOilFluid, OilWaterFluid, GasFluid],
    Field(discriminator="type"),
]


class RockConfig(BaseModel):
    field_h5: str

    @field_validator("field_h5")
    @classmethod
    def file_must_exist(cls, v: str) -> str:
        if not Path(v).exists():
            raise ValueError(f"field_h5 not found: '{v}' (run from repo root)")
        return v


class ScheduleConfig(BaseModel):
    drawdown_duration_hr: float = Field(default=24.0, gt=0)
    buildup_duration_hr: float = Field(default=48.0, gt=0)
    rate_m3_day: float = Field(gt=0)
    steps_per_phase: int = Field(default=30, gt=0)


class PTAConfig(BaseModel):
    bourdet_L: float = Field(default=0.2, gt=0)


class DSTConfig(BaseModel):
    experiment: ExperimentConfig
    grid: GridConfig
    fluid: FluidConfig
    rock: RockConfig
    schedule: ScheduleConfig
    pta: PTAConfig = Field(default_factory=PTAConfig)

    @property
    def output_dir(self) -> Path:
        return Path("outputs") / self.experiment.name / self.experiment.run


def load_config(path: str | Path) -> DSTConfig:
    path = Path(path)
    with open(path) as f:
        raw = yaml.safe_load(f)
    return DSTConfig.model_validate(raw)

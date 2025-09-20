"""Pydantic schemas describing project inputs."""
from __future__ import annotations

from typing import Dict, List, Optional

from pydantic import BaseModel, Field, validator


class ModuleCECParams(BaseModel):
    alpha_sc: float
    a_ref: float
    I_L_ref: float
    I_o_ref: float
    R_s: float
    R_sh_ref: float
    Adjust: float = 0.0
    n: float | None = None


class ModuleParams(BaseModel):
    ref: str
    width_m: float
    height_m: float
    frame_gap_m: float = Field(0.02, description="Gap between modules due to frames")
    p_stc_w: float
    cec_params: ModuleCECParams
    glass_refractive_index: float = Field(
        1.526,
        description="Refractive index of the module glass for Fresnel IAM",
        gt=1.0,
    )
    ar_reflectance: float = Field(
        0.02,
        description="Residual reflectance at normal incidence after anti-reflective coating",
        ge=0.0,
        lt=1.0,
    )


class InverterEffPoint(BaseModel):
    loading_ratio: float = Field(..., ge=0.0)
    efficiency: float = Field(..., ge=0.0, le=1.0)


class InverterParams(BaseModel):
    ref: str
    p_dc_max_w: float
    p_ac_nom_w: float
    eff_curve: List[InverterEffPoint]

    @validator("eff_curve")
    def sort_curve(cls, value: List[InverterEffPoint]):
        return sorted(value, key=lambda point: point.loading_ratio)


class LayoutParams(BaseModel):
    tilt_deg: float
    azimuth_deg: float
    aisle_m: float = 0.0
    roof_setback_m: float = 0.0
    ground_row_spacing_m: float = 4.0
    min_edge_clearance_m: float = 0.0
    portrait: bool = True
    string_size: int = 20
    mppt_per_inverter: int = 2
    dc_ac_ratio: float = 1.2


class LossParams(BaseModel):
    soiling_pct: float = 0.0
    dc_cable_pct: float = 0.0
    ac_cable_pct: float = 0.0
    availability_pct: float = 100.0


class SiteParams(BaseModel):
    latitude: float
    longitude: float
    altitude_m: float = 0.0
    timezone: str = "UTC"


class ProjectParams(BaseModel):
    crs: str = "EPSG:4326"
    mode: str = Field("roof", pattern="^(roof|ground)$")
    site: SiteParams
    module: ModuleParams
    inverter: InverterParams
    layout: LayoutParams
    losses: LossParams
    notes: Optional[str] = None


def parse_params(data: Dict) -> ProjectParams:
    """Parse a raw dict (from YAML/JSON) into ProjectParams."""
    return ProjectParams.model_validate(data)

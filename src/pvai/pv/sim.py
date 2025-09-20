"""Photovoltaic simulation pipeline."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional, Tuple

import numpy as np
import pandas as pd
import pvlib
from pvlib import location, temperature

from pvai.models.schemas import LayoutParams, ModuleParams, ProjectParams
from pvai.pv.losses import apply_losses


@dataclass
class SimulationOutputs:
    hourly: pd.DataFrame
    monthly: pd.DataFrame
    summary: pd.Series


SunVectorCallback = Callable[[float, float, np.ndarray], Tuple[np.ndarray, np.ndarray]]


def _compute_sun_vector(solpos: pd.DataFrame) -> np.ndarray:
    zenith = np.deg2rad(solpos["zenith"].to_numpy())
    azimuth = np.deg2rad(solpos["azimuth"].to_numpy())
    sx = np.sin(zenith) * np.sin(azimuth)
    sy = np.sin(zenith) * np.cos(azimuth)
    sz = np.cos(zenith)
    return np.stack([sx, sy, sz], axis=1)


def _effective_irradiance(poa: pd.Series, iam: pd.Series) -> pd.Series:
    return poa * iam


def _iam_fresnel(
    aoi: pd.Series,
    n_glass: float,
    ar_reflectance: float,
) -> pd.Series:
    angles = aoi.to_numpy(dtype=float)
    angles = np.clip(angles, 0.0, 90.0)
    theta_i = np.deg2rad(angles)
    sin_theta_i = np.sin(theta_i)
    cos_theta_i = np.cos(theta_i)
    # Snell's law, assume air (n=1) to glass (n=n_glass)
    sin_theta_t = sin_theta_i / n_glass
    total_internal = sin_theta_t >= 1.0
    sin_theta_t = np.clip(sin_theta_t, 0.0, 1.0)
    cos_theta_t = np.sqrt(np.clip(1.0 - sin_theta_t ** 2, 0.0, 1.0))

    n1 = 1.0
    n2 = n_glass
    rs_num = n1 * cos_theta_i - n2 * cos_theta_t
    rs_den = n1 * cos_theta_i + n2 * cos_theta_t
    rp_num = n2 * cos_theta_i - n1 * cos_theta_t
    rp_den = n2 * cos_theta_i + n1 * cos_theta_t
    rs = np.where(rs_den != 0.0, (rs_num / rs_den) ** 2, 1.0)
    rp = np.where(rp_den != 0.0, (rp_num / rp_den) ** 2, 1.0)
    reflectance = 0.5 * (rs + rp)
    reflectance = np.clip(reflectance, 0.0, 1.0)
    reflectance[total_internal | (angles >= 90.0)] = 1.0

    # Scale reflectance to match anti-reflective coating residual at normal incidence
    r_normal_uncoated = ((n1 - n2) / (n1 + n2)) ** 2
    target_r0 = np.clip(ar_reflectance, 0.0, 0.999999)
    if r_normal_uncoated > 0:
        scale = min(target_r0 / r_normal_uncoated, 1.0)
    else:
        scale = 1.0
    reflectance *= scale
    transmittance = np.clip(1.0 - reflectance, 0.0, 1.0)

    t0 = 1.0 - target_r0
    if t0 <= 0:
        iam = np.zeros_like(transmittance)
    else:
        iam = transmittance / t0
    iam[angles >= 90.0] = 0.0
    iam = np.clip(iam, 0.0, 1.0)
    return pd.Series(iam, index=aoi.index, name="iam")


def simulate_hourly(layout: pd.DataFrame, meteo: pd.DataFrame, params: ProjectParams,
                    shading_callback: Optional[SunVectorCallback] = None) -> SimulationOutputs:
    loc = location.Location(params.site.latitude, params.site.longitude, params.site.timezone, params.site.altitude_m)
    times = meteo.index.tz_convert(params.site.timezone)
    solpos = loc.get_solarposition(times)
    sun_vectors = _compute_sun_vector(solpos)

    # Irradiance on plane
    poa = pvlib.irradiance.get_total_irradiance(
        surface_tilt=params.layout.tilt_deg,
        surface_azimuth=params.layout.azimuth_deg,
        dni=meteo["dni"],
        ghi=meteo["ghi"],
        dhi=meteo["dhi"],
        solar_zenith=solpos["apparent_zenith"],
        solar_azimuth=solpos["azimuth"],
    )
    aoi = pvlib.irradiance.aoi(
        params.layout.tilt_deg,
        params.layout.azimuth_deg,
        solpos["apparent_zenith"],
        solpos["azimuth"],
    )
    iam = _iam_fresnel(aoi, params.module.glass_refractive_index, params.module.ar_reflectance)

    if shading_callback is not None:
        front = []
        back = []
        for (dni, dhi), sun_vec in zip(meteo[["dni", "dhi"]].to_numpy(), sun_vectors):
            poa_f, poa_b = shading_callback(float(dni), float(dhi), sun_vec.astype(np.float32))
            front.append(np.nanmean(poa_f))
            back.append(np.nanmean(poa_b))
        poa_front = pd.Series(front, index=meteo.index)
        poa_back = pd.Series(back, index=meteo.index)
        poa_global = poa_front + 0.3 * poa_back
        poa["poa_global"] = poa_global

    effective_irradiance = _effective_irradiance(poa["poa_global"], iam)
    temp_cell = temperature.faiman(poa["poa_global"], meteo["temp_air"], meteo["wind_speed"])

    module_params = params.module
    cec = module_params.cec_params.model_dump()
    photocurrent, saturation_current, series_resistance, shunt_resistance, nNsVth = pvlib.pvsystem.calcparams_cec(
        effective_irradiance,
        temp_cell,
        **cec,
    )
    single_diode = pvlib.pvsystem.singlediode(
        photocurrent,
        saturation_current,
        series_resistance,
        shunt_resistance,
        nNsVth,
    )

    module_power = single_diode["p_mp"]
    n_modules = len(layout)
    dc_capacity = module_params.p_stc_w * n_modules
    dc_power = module_power * n_modules

    inverter = params.inverter
    ac_nominal_total = _estimate_inverter_count(dc_capacity, params.layout, inverter) * inverter.p_ac_nom_w
    ac_limit = _estimate_inverter_count(dc_capacity, params.layout, inverter) * inverter.p_dc_max_w
    dc_power_clipped = dc_power.clip(upper=ac_limit)
    eff = _inverter_efficiency(dc_power_clipped, ac_nominal_total, inverter)
    ac_power = (dc_power_clipped * eff).clip(upper=ac_nominal_total)

    losses = apply_losses(ac_power, params.losses)
    hourly = pd.DataFrame(
        {
            "poa_global": poa["poa_global"],
            "effective_irradiance": effective_irradiance,
            "temp_cell": temp_cell,
            "p_dc": dc_power,
            "p_ac_raw": ac_power,
            "p_ac_net": losses["p_ac_net"],
        },
        index=meteo.index,
    )
    monthly = hourly.resample("M").sum()
    summary = pd.Series(
        {
            "annual_energy_kwh": hourly["p_ac_net"].sum() / 1000.0,
            "specific_yield_kwh_kwp": (hourly["p_ac_net"].sum() / 1000.0) / (dc_capacity / 1000.0),
            "performance_ratio": (hourly["p_ac_net"].sum()) / (dc_capacity * meteo["ghi"].sum() / 1000.0 + 1e-9),
        }
    )
    return SimulationOutputs(hourly=hourly, monthly=monthly, summary=summary)


def _estimate_inverter_count(dc_capacity_w: float, layout: LayoutParams, inverter) -> int:
    ac_total = dc_capacity_w / max(layout.dc_ac_ratio, 0.1)
    count = max(1, int(np.ceil(ac_total / inverter.p_ac_nom_w)))
    return count


def _inverter_efficiency(dc_power: pd.Series, ac_nominal_total: float, inverter) -> pd.Series:
    curve = np.array([[pt.loading_ratio, pt.efficiency] for pt in inverter.eff_curve])
    loading = np.clip(dc_power / (ac_nominal_total + 1e-9), 0.0, 1.5)
    eff = np.interp(loading, curve[:, 0], curve[:, 1], left=curve[0, 1], right=curve[-1, 1])
    return pd.Series(eff, index=dc_power.index)

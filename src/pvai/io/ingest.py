"""Data ingestion helpers."""
from __future__ import annotations

from pathlib import Path
from typing import Tuple

import geopandas as gpd
import pandas as pd
import yaml

from pvai.models.schemas import ProjectParams, parse_params
from pvai.utils.crs import ensure_crs


def load_params(path: str | Path) -> ProjectParams:
    data = yaml.safe_load(Path(path).read_text())
    return parse_params(data)


def load_site(site_path: str | Path, obstacles_path: str | Path | None, crs: str) -> Tuple[gpd.GeoDataFrame, gpd.GeoDataFrame]:
    target_crs = ensure_crs(crs)
    site = gpd.read_file(site_path)
    if site.crs is None:
        site = site.set_crs(target_crs)
    else:
        site = site.to_crs(target_crs)

    if obstacles_path:
        obstacles = gpd.read_file(obstacles_path)
        if obstacles.crs is None:
            obstacles = obstacles.set_crs(target_crs)
        else:
            obstacles = obstacles.to_crs(target_crs)
    else:
        obstacles = gpd.GeoDataFrame(geometry=[], crs=target_crs)
    return site, obstacles


def load_weather(path: str | Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    if "timestamp" in df.columns:
        time_col = "timestamp"
    elif "ts" in df.columns:
        time_col = "ts"
    else:
        raise ValueError("Weather file must contain a 'timestamp' or 'ts' column.")

    df[time_col] = pd.to_datetime(df[time_col])
    if df[time_col].dt.tz is None:
        df[time_col] = df[time_col].dt.tz_localize("UTC")
    df = df.set_index(time_col).sort_index()
    required = {"ghi", "dni", "dhi", "temp_air", "wind_speed"}
    missing = required.difference(df.columns)
    if missing:
        raise ValueError(f"Weather file missing columns: {sorted(missing)}")
    return df

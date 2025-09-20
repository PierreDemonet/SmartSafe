"""Rooftop layout packing."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List

import geopandas as gpd
from shapely import affinity
from shapely.geometry import Polygon, box
from shapely.ops import unary_union

from pvai.models.schemas import LayoutParams, ModuleParams


@dataclass
class PackedModule:
    geometry: Polygon
    row: int
    col: int


def _prepare_zone(site: gpd.GeoDataFrame, obstacles: gpd.GeoDataFrame, params: LayoutParams) -> Polygon:
    union = unary_union(site.geometry)
    if params.roof_setback_m:
        union = union.buffer(-params.roof_setback_m)
    if not union or union.is_empty:
        raise ValueError("Installable area vanished after applying setbacks.")
    if not obstacles.empty:
        obstacle_union = unary_union(obstacles.geometry.buffer(0.2))
        union = union.difference(obstacle_union)
    if params.aisle_m:
        union = union.buffer(-0.5 * params.aisle_m)
    if union.is_empty:
        raise ValueError("Installable area empty after removing obstacles.")
    return union


def _rect_for(center_x: float, center_y: float, width: float, height: float) -> Polygon:
    minx = center_x - width / 2
    miny = center_y - height / 2
    return box(minx, miny, minx + width, miny + height)


def pack_modules_roof(site: gpd.GeoDataFrame, obstacles: gpd.GeoDataFrame, module: ModuleParams, params: LayoutParams) -> gpd.GeoDataFrame:
    zone = _prepare_zone(site, obstacles, params)
    rotation = params.azimuth_deg - 180.0  # align to PV azimuth convention (0 = south)
    rotated = affinity.rotate(zone, -rotation, origin="centroid")
    minx, miny, maxx, maxy = rotated.bounds

    mod_w = module.width_m if params.portrait else module.height_m
    mod_h = module.height_m if params.portrait else module.width_m
    pitch_x = mod_w + module.frame_gap_m
    pitch_y = mod_h + module.frame_gap_m

    modules: List[PackedModule] = []
    row_idx = 0
    y = miny + mod_h / 2
    while y + mod_h / 2 <= maxy + 1e-6:
        x = minx + mod_w / 2
        col_idx = 0
        while x + mod_w / 2 <= maxx + 1e-6:
            rect = _rect_for(x, y, mod_w, mod_h)
            if rotated.contains(rect):
                placed = affinity.rotate(rect, rotation, origin="centroid")
                modules.append(PackedModule(placed, row=row_idx, col=col_idx))
            x += pitch_x
            col_idx += 1
        y += pitch_y
        row_idx += 1

    if not modules:
        raise ValueError("No modules could be placed in the provided area.")

    gdf = gpd.GeoDataFrame(
        {
            "geometry": [m.geometry for m in modules],
            "module_id": [f"M{i:04d}" for i in range(len(modules))],
            "row_id": [m.row for m in modules],
            "col_id": [m.col for m in modules],
        },
        geometry="geometry",
        crs=site.crs,
    )
    return gdf


def assign_strings(layout: gpd.GeoDataFrame, params: LayoutParams) -> gpd.GeoDataFrame:
    layout = layout.sort_values(["row_id", "col_id"]).copy()
    string_size = max(1, params.string_size)
    string_ids: List[str] = []
    current = 0
    for idx in range(len(layout)):
        string_ids.append(f"S{current:03d}")
        if (idx + 1) % string_size == 0:
            current += 1
    layout["string_id"] = string_ids
    return layout

"""Ground-mounted layout algorithms."""
from __future__ import annotations

from dataclasses import dataclass
from typing import List

import geopandas as gpd
from shapely import affinity
from shapely.geometry import Polygon, box
from shapely.ops import unary_union

from pvai.models.schemas import LayoutParams, ModuleParams


@dataclass
class GroundModule:
    geometry: Polygon
    row: int
    col: int


def _prepare_ground_zone(site: gpd.GeoDataFrame, obstacles: gpd.GeoDataFrame, params: LayoutParams) -> Polygon:
    union = unary_union(site.geometry)
    if params.min_edge_clearance_m:
        union = union.buffer(-params.min_edge_clearance_m)
    if not obstacles.empty:
        union = union.difference(unary_union(obstacles.geometry))
    if union.is_empty:
        raise ValueError("No buildable surface remains for ground layout.")
    return union


def layout_ground(site: gpd.GeoDataFrame, obstacles: gpd.GeoDataFrame, module: ModuleParams, params: LayoutParams) -> gpd.GeoDataFrame:
    zone = _prepare_ground_zone(site, obstacles, params)
    rotation = params.azimuth_deg - 180.0
    rotated = affinity.rotate(zone, -rotation, origin="centroid")
    minx, miny, maxx, maxy = rotated.bounds

    mod_w = module.width_m if params.portrait else module.height_m
    mod_h = module.height_m if params.portrait else module.width_m
    pitch_x = mod_w + module.frame_gap_m
    row_pitch = params.ground_row_spacing_m

    modules: List[GroundModule] = []
    row_idx = 0
    y = miny + mod_h / 2
    while y + mod_h / 2 <= maxy + 1e-6:
        x = minx + mod_w / 2
        col_idx = 0
        while x + mod_w / 2 <= maxx + 1e-6:
            rect = box(x - mod_w / 2, y - mod_h / 2, x + mod_w / 2, y + mod_h / 2)
            if rotated.contains(rect):
                placed = affinity.rotate(rect, rotation, origin="centroid")
                modules.append(GroundModule(placed, row=row_idx, col=col_idx))
            x += pitch_x
            col_idx += 1
        y += row_pitch
        row_idx += 1

    if not modules:
        raise ValueError("No modules placed on ground area.")

    gdf = gpd.GeoDataFrame(
        {
            "geometry": [m.geometry for m in modules],
            "module_id": [f"GM{i:04d}" for i in range(len(modules))],
            "row_id": [m.row for m in modules],
            "col_id": [m.col for m in modules],
        },
        geometry="geometry",
        crs=site.crs,
    )
    return gdf

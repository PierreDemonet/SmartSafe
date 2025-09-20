"""DXF export helper."""
from __future__ import annotations

from pathlib import Path

import geopandas as gpd
import ezdxf


def export_dxf(layout: gpd.GeoDataFrame, site: gpd.GeoDataFrame, obstacles: gpd.GeoDataFrame, path: str | Path) -> None:
    doc = ezdxf.new("R2010")
    msp = doc.modelspace()

    def draw_polygons(gdf: gpd.GeoDataFrame, layer: str, color: int):
        if gdf.empty:
            return
        for geom in gdf.geometry:
            if geom.is_empty:
                continue
            if geom.geom_type == "Polygon":
                points = list(geom.exterior.coords)
                msp.add_lwpolyline(points, dxfattribs={"layer": layer, "color": color, "closed": True})
            elif geom.geom_type.startswith("Multi"):
                for part in geom.geoms:
                    points = list(part.exterior.coords)
                    msp.add_lwpolyline(points, dxfattribs={"layer": layer, "color": color, "closed": True})

    draw_polygons(site, "SITE", 2)
    draw_polygons(obstacles, "OBSTACLES", 1)
    draw_polygons(layout, "MODULES", 3)

    Path(path).parent.mkdir(parents=True, exist_ok=True)
    doc.saveas(path)

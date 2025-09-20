"""PDF plotting helper."""
from __future__ import annotations

from pathlib import Path

import geopandas as gpd
import matplotlib.pyplot as plt


def export_pdf(layout: gpd.GeoDataFrame, site: gpd.GeoDataFrame, obstacles: gpd.GeoDataFrame, path: str | Path) -> None:
    fig, ax = plt.subplots(figsize=(8, 6))
    if not site.empty:
        site.boundary.plot(ax=ax, color="black", linewidth=1, label="Site")
    if not obstacles.empty:
        obstacles.plot(ax=ax, color="red", alpha=0.3, label="Obstacles")
    if not layout.empty:
        layout.plot(ax=ax, color="gold", edgecolor="orange", label="Modules")
    ax.set_aspect("equal")
    ax.set_title("PV layout plan")
    ax.legend()
    ax.set_xlabel("X [m]")
    ax.set_ylabel("Y [m]")
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)

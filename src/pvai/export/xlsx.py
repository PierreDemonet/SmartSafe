"""Excel exports."""
from __future__ import annotations

from pathlib import Path

import geopandas as gpd
import pandas as pd


def export_bom(layout: gpd.GeoDataFrame, summary: pd.Series, path: str | Path) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(path) as writer:
        layout[["module_id", "row_id", "col_id", "string_id"]].to_excel(writer, sheet_name="Modules", index=False)
        summary.to_frame(name="value").to_excel(writer, sheet_name="Summary")

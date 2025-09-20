from pathlib import Path

import geopandas as gpd
from shapely.geometry import Polygon

from pvai.layout.roof import assign_strings, pack_modules_roof
from pvai.models.schemas import LayoutParams, ModuleParams, ModuleCECParams


def _dummy_params():
    module = ModuleParams(
        ref="Mod",
        width_m=1.0,
        height_m=2.0,
        frame_gap_m=0.1,
        p_stc_w=400,
        cec_params=ModuleCECParams(alpha_sc=0.0045, a_ref=1.5, I_L_ref=8.5, I_o_ref=8e-10,
                                   R_s=0.4, R_sh_ref=400, Adjust=0.0),
    )
    layout = LayoutParams(
        tilt_deg=10,
        azimuth_deg=180,
        aisle_m=0.0,
        roof_setback_m=0.2,
        ground_row_spacing_m=4.0,
        min_edge_clearance_m=0.0,
        portrait=True,
        string_size=6,
        mppt_per_inverter=2,
        dc_ac_ratio=1.2,
    )
    return module, layout


def test_pack_modules_roof_basic(tmp_path):
    site = gpd.GeoDataFrame({"geometry": [Polygon([(0, 0), (20, 0), (20, 10), (0, 10)])]}, crs="EPSG:2154")
    obstacles = gpd.GeoDataFrame({"geometry": []}, crs="EPSG:2154")
    module, layout = _dummy_params()
    gdf = pack_modules_roof(site, obstacles, module, layout)
    assert not gdf.empty
    assert gdf.geometry.within(site.geometry.iloc[0]).all()


def test_assign_strings_count():
    site = gpd.GeoDataFrame({"geometry": [Polygon([(0, 0), (20, 0), (20, 10), (0, 10)])]}, crs="EPSG:2154")
    obstacles = gpd.GeoDataFrame({"geometry": []}, crs="EPSG:2154")
    module, layout = _dummy_params()
    gdf = pack_modules_roof(site, obstacles, module, layout)
    gdf = assign_strings(gdf, layout)
    assert "string_id" in gdf.columns
    assert gdf["string_id"].nunique() >= 1

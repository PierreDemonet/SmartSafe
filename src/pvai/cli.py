"""Command line entry point."""
from __future__ import annotations

from pathlib import Path
from typing import Optional

import geopandas as gpd
import numpy as np
import pandas as pd
import typer

from pvai.io.ingest import load_params, load_site, load_weather
from pvai.layout.ground import layout_ground
from pvai.layout.roof import assign_strings, pack_modules_roof
from pvai.models.schemas import ProjectParams
from pvai.pv.sim import SimulationOutputs, simulate_hourly
from pvai.export.dxf import export_dxf
from pvai.export.pdf import export_pdf
from pvai.export.xlsx import export_bom
from pvai.structural.diagnostic import GeometryConfig, LoadConfig, run_diagnostic

try:
    from pvrtx.core.engine import PVRTX
    from pvrtx.scene.geometry import load_mesh_glb
    from pvrtx.scene.materials import load_materials_yaml
except ImportError:  # pragma: no cover - RTX optional
    PVRTX = None  # type: ignore


app = typer.Typer(help="PV engineering toolkit")


def _load_layout(path: Path) -> gpd.GeoDataFrame:
    gdf = gpd.read_file(path)
    if "string_id" not in gdf.columns:
        gdf["string_id"] = ""
    return gdf


@app.command()
def ingest(site: Path = typer.Option(..., exists=True),
           obstacles: Optional[Path] = typer.Option(None, exists=True),
           params: Path = typer.Option(..., exists=True),
           meteo: Path = typer.Option(..., exists=True),
           out_dir: Path = typer.Option(Path("out/inputs"))):
    """Validate inputs and copy them into a working directory."""
    project = load_params(params)
    site_gdf, obs_gdf = load_site(site, obstacles, project.crs)
    weather = load_weather(meteo)
    out_dir.mkdir(parents=True, exist_ok=True)
    site_gdf.to_file(out_dir / "site.geojson", driver="GeoJSON")
    obs_gdf.to_file(out_dir / "obstacles.geojson", driver="GeoJSON")
    weather.to_csv(out_dir / "meteo.csv")
    (out_dir / "params.yaml").write_text(Path(params).read_text())
    typer.echo(f"Inputs validated. {len(site_gdf)} site polygon(s), {len(obs_gdf)} obstacle(s), {len(weather)} weather rows.")


@app.command()
def layout(params: Path = typer.Option(..., exists=True),
           site: Path = typer.Option(..., exists=True),
           obstacles: Optional[Path] = typer.Option(None, exists=True),
           mode: str = typer.Option("roof"),
           out: Path = typer.Option(Path("out/layout.geojson"))):
    """Generate a module layout and export as GeoJSON."""
    project = load_params(params)
    site_gdf, obs_gdf = load_site(site, obstacles, project.crs)
    if mode == "roof":
        layout_gdf = pack_modules_roof(site_gdf, obs_gdf, project.module, project.layout)
    elif mode == "ground":
        layout_gdf = layout_ground(site_gdf, obs_gdf, project.module, project.layout)
    else:
        raise typer.BadParameter("mode must be 'roof' or 'ground'")
    layout_gdf = assign_strings(layout_gdf, project.layout)
    out.parent.mkdir(parents=True, exist_ok=True)
    layout_gdf.to_file(out, driver="GeoJSON")
    typer.echo(f"Layout generated with {len(layout_gdf)} modules -> {out}")


@app.command()
def simulate(params: Path = typer.Option(..., exists=True),
             meteo: Path = typer.Option(..., exists=True),
             layout_path: Path = typer.Option(..., exists=True),
             out: Path = typer.Option(Path("out/energy_report.xlsx")),
             rtx_plugin: str = typer.Option("dummy"),
             scene_mesh: Optional[Path] = typer.Option(None, exists=True),
             materials: Optional[Path] = typer.Option(None, exists=True)):
    """Run the pvlib-based energy simulation."""
    project = load_params(params)
    meteo_df = load_weather(meteo)
    layout_gdf = _load_layout(layout_path)

    shading_cb = None
    if rtx_plugin != "dummy":
        if PVRTX is None:
            raise RuntimeError("PVRTX package unavailable; cannot load RTX plugin.")
        if scene_mesh is None:
            raise typer.BadParameter("A scene mesh (.glb/.obj) is required when using RTX shading.")
        mesh = load_mesh_glb(scene_mesh)
        mats = load_materials_yaml(materials) if materials else {"default": {"rho": 0.2}}
        centers = np.column_stack([
            layout_gdf.geometry.centroid.x.to_numpy(),
            layout_gdf.geometry.centroid.y.to_numpy(),
            np.zeros(len(layout_gdf))
        ]).astype("float32")
        tilt = np.deg2rad(project.layout.tilt_deg)
        az = np.deg2rad(project.layout.azimuth_deg)
        front_normal = np.array([
            np.sin(tilt) * np.sin(az),
            np.sin(tilt) * np.cos(az),
            np.cos(tilt),
        ], dtype="float32")
        normals_f = np.tile(front_normal, (len(layout_gdf), 1))
        normals_b = -normals_f
        engine = PVRTX(rtx_plugin)
        engine.build(mesh, mats, centers, normals_f, centers, normals_b)

        def _cb(dni: float, dhi: float, sun_vec):
            return engine.compute_poa_step(dni, dhi, sun_vec)

        shading_cb = _cb

    outputs = simulate_hourly(layout_gdf, meteo_df, project, shading_cb)
    _export_energy_report(outputs, out)
    typer.echo(f"Energy simulation written to {out}")


def _export_energy_report(outputs: SimulationOutputs, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(path) as writer:
        outputs.hourly.to_excel(writer, sheet_name="hourly")
        outputs.monthly.to_excel(writer, sheet_name="monthly")
        outputs.summary.to_frame(name="value").to_excel(writer, sheet_name="summary")


@app.command()
def export(layout: Path = typer.Option(..., exists=True),
           params: Path = typer.Option(..., exists=True),
           site: Path = typer.Option(..., exists=True),
           obstacles: Optional[Path] = typer.Option(None, exists=True),
           dxf: Optional[Path] = typer.Option(None),
           pdf: Optional[Path] = typer.Option(None),
           xlsx: Optional[Path] = typer.Option(None)):
    """Export DXF/PDF/XLSX deliverables."""
    project = load_params(params)
    layout_gdf = _load_layout(layout)
    site_gdf, obs_gdf = load_site(site, obstacles, project.crs)
    if dxf:
        export_dxf(layout_gdf, site_gdf, obs_gdf, dxf)
    if pdf:
        export_pdf(layout_gdf, site_gdf, obs_gdf, pdf)
    if xlsx:
        summary = pd.Series({"modules": len(layout_gdf), "dc_capacity_kwp": len(layout_gdf) * project.module.p_stc_w / 1000.0})
        export_bom(layout_gdf, summary, xlsx)
    typer.echo("Deliverables exported.")


@app.command()
def diag(span: float = typer.Option(12.0, help="Portée du portique (m)"),
         bay_spacing: float = typer.Option(6.0, help="Entraxe entre portiques (m)"),
         length: float = typer.Option(18.0, help="Longueur totale du hangar (m)"),
         roof_pitch: float = typer.Option(12.0, help="Pente de toiture (degrés)"),
         roof_type: str = typer.Option("double", help="Type de toiture: double ou mono"),
         eave_height: float = typer.Option(4.0, help="Hauteur à l'égout (m)"),
         zone_neige: str = typer.Option("A2", help="Zone de neige (A1, A2, B1, ... )"),
         zone_vent: int = typer.Option(1, help="Zone de vent (1,2,3)"),
         altitude: float = typer.Option(200.0, help="Altitude du site (m)"),
         surcharge: float = typer.Option(0.15, help="Surcharge permanente additionnelle (kN/m²)"),
         roof_weight: float = typer.Option(0.10, help="Poids propre de la couverture (kN/m²)"),
         rafter_section: str = typer.Option("IPE200", help="Section des arbalétriers"),
         column_section: str = typer.Option("HEA160", help="Section des poteaux"),
         frame_material: str = typer.Option("S275", help="Matériau principal (S275, S355, GL24)")):
    """Diagnostic rapide GO/NO GO pour un hangar agricole standard."""

    geom = GeometryConfig(
        span_m=span,
        bay_spacing_m=bay_spacing,
        length_m=length,
        roof_pitch_deg=roof_pitch,
        roof_type=roof_type if roof_type in ("double", "mono") else "double",
        eave_height_m=eave_height,
    )
    loads = LoadConfig(
        zone_neige=zone_neige,
        zone_vent=zone_vent,
        altitude_m=altitude,
        additional_permanent_kN_m2=surcharge,
        roof_self_weight_kN_m2=roof_weight,
    )

    report = run_diagnostic(
        geom,
        sections={"rafter": rafter_section, "column": column_section},
        materials={"frame": frame_material},
        loads=loads,
    )

    typer.echo(f"Neige prise en compte: {report.snow_load_kN_m2:.2f} kN/m²")
    typer.echo(f"Pression de vent: {report.wind_pressure_kN_m2:.2f} kN/m²")
    typer.echo(f"Poutre - Mmax: {report.rafter.applied[0]:.2f} kN·m / MRd {report.rafter.capacity[0]:.2f} kN·m -> utilisation {report.rafter.utilization*100:.1f}%")
    typer.echo(
        f"Poteau - N: {report.column.applied[0]:.2f} kN, M: {report.column.applied[1]:.2f} kN·m / "
        f"NRd {report.column.capacity[0]:.2f} kN, MRd {report.column.capacity[1]:.2f} kN·m -> utilisation {report.column.utilization*100:.1f}%"
    )
    typer.echo(f"Verdict: {report.status}")
    typer.echo("Renforts suggérés:")
    for opt in report.reinforcements:
        typer.echo(f"- {opt}")


if __name__ == "__main__":
    app()

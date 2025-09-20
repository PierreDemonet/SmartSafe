"""Run the end-to-end pipeline on demo data."""
from pathlib import Path

from pvai.io.ingest import load_params, load_site, load_weather
from pvai.layout.roof import assign_strings, pack_modules_roof
from pvai.pv.sim import simulate_hourly

params_path = Path("examples/data/params.yaml")
meteo_path = Path("examples/data/meteo.csv")
site_path = Path("examples/data/site.geojson")
obstacles_path = Path("examples/data/obstacles.geojson")

project = load_params(params_path)
site, obstacles = load_site(site_path, obstacles_path, project.crs)
layout = pack_modules_roof(site, obstacles, project.module, project.layout)
layout = assign_strings(layout, project.layout)
meteo = load_weather(meteo_path)
outputs = simulate_hourly(layout, meteo, project)
print(outputs.summary)

# PV Platform MVP

This repository hosts an MVP of a photovoltaic engineering platform able to:

1. ingest geospatial site data and equipment parameters,
2. automatically place PV modules on roofs or ground-mounted areas,
3. simulate hourly production with pvlib and an RTX/OptiX-based shading engine, and
4. export engineering deliverables (DXF, PDF, Excel).

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

Build the OptiX plugin (requires CUDA + OptiX SDK):

```bash
cd cpp/optix_plugin
cmake -S . -B build -DOPTIX_ROOT=/usr/local/optix
cmake --build build --config Release
cp build/pvrtx_optix.* ../../src/
```

Run the demo pipeline:

```bash
pvai ingest --site examples/data/site.geojson --obstacles examples/data/obstacles.geojson \
  --params examples/data/params.yaml --meteo examples/data/meteo.csv
pvai layout --params examples/data/params.yaml --mode roof --out out/layout.geojson
pvai simulate --params examples/data/params.yaml --meteo examples/data/meteo.csv \
  --layout out/layout.geojson --out out/energy_report.xlsx
pvai export --layout out/layout.geojson --params examples/data/params.yaml \
  --dxf out/plan.dxf --pdf out/plan.pdf --xlsx out/bom.xlsx
```

To exercise the shading engine without a GPU, use `--rtx-plugin dummy` for simulation.

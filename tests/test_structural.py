from pathlib import Path

from pvai.structural.diagnostic import (
    FrameAccessories,
    GeometryConfig,
    LoadConfig,
    PurlinConfig,
    calculer_charge_neige,
    generate_pdf_report,
    run_diagnostic,
)


def test_snow_load_increases_with_altitude():
    base = calculer_charge_neige("A2", altitude_m=200, pente_deg=12, type_toit="double")
    elevated = calculer_charge_neige("A2", altitude_m=500, pente_deg=12, type_toit="double")
    assert elevated > base


def test_diagnostic_go_with_robust_sections():
    geom = GeometryConfig(span_m=12, bay_spacing_m=6, length_m=18, roof_pitch_deg=12)
    loads = LoadConfig(additional_permanent_kN_m2=0.1)
    report = run_diagnostic(
        geom,
        sections={"rafter": "IPE200", "column": "HEA160"},
        materials={"frame": "S355"},
        loads=loads,
        purlins=PurlinConfig(section="Z200", spacing_m=1.25),
    )
    assert report.status == "GO"
    assert report.rafter.utilization < 1.0
    assert report.column.utilization < 1.0


def test_vertical_combination_changes_with_zone():
    geom = GeometryConfig(span_m=12, bay_spacing_m=6, length_m=18, roof_pitch_deg=12)
    mild_loads = LoadConfig(zone_neige="A1", additional_permanent_kN_m2=0.05)
    hard_loads = LoadConfig(zone_neige="E", additional_permanent_kN_m2=0.05)
    mild_report = run_diagnostic(
        geom,
        sections={"rafter": "IPE200", "column": "HEA200"},
        materials={"frame": "S355"},
        loads=mild_loads,
    )
    hard_report = run_diagnostic(
        geom,
        sections={"rafter": "IPE200", "column": "HEA200"},
        materials={"frame": "S355"},
        loads=hard_loads,
    )
    assert hard_report.loads.q_vertical_uls_snow_leading > mild_report.loads.q_vertical_uls_snow_leading


def test_pdf_report_creation(tmp_path: Path):
    geom = GeometryConfig(span_m=12, bay_spacing_m=6, length_m=18, roof_pitch_deg=12)
    report = run_diagnostic(
        geom,
        sections={"rafter": "IPE200", "column": "HEA160"},
        materials={"frame": "S355"},
    )
    pdf_path = tmp_path / "rapport.pdf"
    output = generate_pdf_report(report, pdf_path)
    assert output.exists()


def test_intermediate_columns_relieve_main_rafter():
    base_geom = GeometryConfig(span_m=18, bay_spacing_m=6, length_m=18, roof_pitch_deg=12)
    reinforced_geom = GeometryConfig(span_m=18, bay_spacing_m=6, length_m=18, roof_pitch_deg=12, intermediate_columns=1)
    base = run_diagnostic(
        base_geom,
        sections={"rafter": "IPE200", "column": "HEA160"},
        materials={"frame": "S355"},
    )
    with_support = run_diagnostic(
        reinforced_geom,
        sections={"rafter": "IPE200", "column": "HEA160"},
        materials={"frame": "S355"},
    )
    assert with_support.rafter.utilization < base.rafter.utilization


def test_knee_braces_reduce_column_moment():
    geom = GeometryConfig(span_m=12, bay_spacing_m=6, length_m=18, roof_pitch_deg=12)
    baseline = run_diagnostic(
        geom,
        sections={"rafter": "IPE200", "column": "HEA160"},
        materials={"frame": "S275"},
    )
    braced = run_diagnostic(
        geom,
        sections={"rafter": "IPE200", "column": "HEA160"},
        materials={"frame": "S275"},
        accessories=FrameAccessories(knee_braces=True),
    )
    assert braced.column.utilization < baseline.column.utilization


def test_lean_to_is_reported():
    geom = GeometryConfig(
        span_m=12,
        bay_spacing_m=6,
        length_m=18,
        roof_pitch_deg=12,
        lean_to_span_m=4.0,
        lean_to_pitch_deg=8.0,
        lean_to_eave_height_m=3.5,
    )
    report = run_diagnostic(
        geom,
        sections={"rafter": "IPE200", "column": "HEA160", "lean_to_rafter": "IPE180", "lean_to_column": "HEA160"},
        materials={"frame": "S275"},
    )
    assert report.lean_to_rafter is not None
    assert report.lean_to_column is not None

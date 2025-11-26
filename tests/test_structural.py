from pvai.structural.diagnostic import (
    GeometryConfig,
    LoadConfig,
    calculer_charge_neige,
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
    )
    assert report.status == "GO"
    assert report.rafter.utilization < 1.0
    assert report.column.utilization < 1.0

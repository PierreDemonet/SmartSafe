"""Simplified structural diagnostic tailored to agricultural hangars.

This module intentionally favors transparency and conservative assumptions over
full Eurocode coverage. It provides quick checks to determine whether a standard
portal frame can host additional loads (e.g. PV retrofit) and proposes common
reinforcement options when necessary.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import ceil, cos, radians
from pathlib import Path
from typing import Dict, List, Literal, Tuple


RoofType = Literal["double", "mono"]


@dataclass
class GeometryConfig:
    """Geometric parameters of the hangar."""

    span_m: float
    bay_spacing_m: float
    length_m: float
    roof_pitch_deg: float
    roof_type: RoofType = "double"
    eave_height_m: float = 4.0

    @property
    def rafter_length_m(self) -> float:
        """Return the length of one rafter (half-span) along the slope."""
        half_span = self.span_m / 2.0
        return half_span / cos(radians(self.roof_pitch_deg))

    @property
    def bay_count(self) -> int:
        return max(1, int(round(self.length_m / self.bay_spacing_m)))


@dataclass
class SectionProperties:
    """Minimal section properties used for quick checks."""

    name: str
    area_cm2: float
    wx_cm3: float


@dataclass
class Material:
    """Material definition with characteristic yield strength."""

    name: str
    fy_mpa: float


@dataclass
class LoadConfig:
    """Loading parameters provided by the user."""

    zone_neige: str = "A2"
    zone_vent: int = 1
    altitude_m: float = 200.0
    additional_permanent_kN_m2: float = 0.15
    roof_self_weight_kN_m2: float = 0.10
    safety_factor_actions: float = 1.5
    gamma_g: float = 1.35
    gamma_q: float = 1.5
    psi0_snow: float = 0.5
    psi0_wind: float = 0.6


@dataclass
class ElementResult:
    """Usage ratio and governing actions for an element."""

    name: str
    utilization: float
    applied: Tuple[float, ...]
    capacity: Tuple[float, ...]
    note: str


@dataclass
class LoadSummary:
    """Track governing combinations for transparency."""

    permanent_kN_m2: float
    snow_kN_m2: float
    wind_pressure_kN_m2: float
    q_vertical_uls_snow_leading: float
    q_vertical_uls_wind_leading: float
    wind_horizontal_uls: float


@dataclass
class DiagnosticReport:
    status: Literal["GO", "NO GO"]
    loads: LoadSummary
    rafter: ElementResult
    column: ElementResult
    purlin: ElementResult
    bracing: ElementResult
    reinforcements: List[str]


_SECTION_LIBRARY: Dict[str, SectionProperties] = {
    # Typical reference values (cm² / cm³) for quick sizing
    "IPE180": SectionProperties("IPE180", area_cm2=26.2, wx_cm3=206.0),
    "IPE200": SectionProperties("IPE200", area_cm2=30.6, wx_cm3=262.0),
    "HEA160": SectionProperties("HEA160", area_cm2=32.3, wx_cm3=193.0),
    "HEA200": SectionProperties("HEA200", area_cm2=52.3, wx_cm3=405.0),
    "UPN160": SectionProperties("UPN160", area_cm2=23.5, wx_cm3=150.0),
    "Z200": SectionProperties("Z200", area_cm2=5.03, wx_cm3=43.6),
    "GL24_200x400": SectionProperties("GL24_200x400", area_cm2=800.0 / 100.0, wx_cm3=200.0 * 400.0**2 / 6 / 1000.0),
}

_MATERIAL_LIBRARY: Dict[str, Material] = {
    "S275": Material("S275", fy_mpa=275.0),
    "S355": Material("S355", fy_mpa=355.0),
    "S390GD": Material("S390GD", fy_mpa=390.0),
    "GL24": Material("GL24", fy_mpa=24.0),
}


@dataclass
class PurlinConfig:
    """Secondary member data for purlin verification."""

    section: str = "Z200"
    material: str = "S390GD"
    spacing_m: float = 1.5


@dataclass
class BracingConfig:
    """Simplified bracing/tie bar definition for wind stability."""

    section: str = "UPN160"
    material: str = "S275"
    panel_width_m: float = 6.0


def calculer_charge_neige(zone: str, altitude_m: float, pente_deg: float, type_toit: RoofType) -> float:
    """Compute a conservative roof snow load in kN/m².

    The expression follows EN 1991-1-3 guidance in a simplified manner:
    - base value from the French map
    - +5% per 100 m above 200 m
    - reduction for slopes above 30° (capped at 40% reduction)
    - no drift or sliding accumulation is considered here.
    """

    base_map = {
        "A1": 0.35,
        "A2": 0.45,
        "B1": 0.65,
        "B2": 0.85,
        "C1": 1.0,
        "C2": 1.25,
        "D": 1.5,
        "E": 2.0,
    }
    sk = base_map.get(zone.upper(), base_map["A2"])
    if altitude_m > 200:
        steps = ceil((altitude_m - 200) / 100.0)
        sk *= 1 + 0.05 * steps
    if type_toit == "mono":
        # Slight increase on monopitch because of potential drift from the high side
        sk *= 1.05
    if pente_deg > 30:
        sk *= max(0.6, 1 - 0.03 * (pente_deg - 30))
    return sk


def calculer_charge_vent(zone: int, hauteur_m: float, largeur_m: float, longueur_m: float, type_toit: RoofType) -> float:
    """Return a simplified peak pressure on the windward face in kN/m²."""

    base = {1: 0.50, 2: 0.70, 3: 0.90}
    qb = base.get(zone, base[1])
    ce = min(1.6, 0.9 + 0.02 * hauteur_m)  # exposure factor with gentle cap
    cp = 0.8 if type_toit == "mono" else 0.7
    area_factor = min(1.2, 1 + 0.01 * max(largeur_m, longueur_m))
    return qb * ce * cp * area_factor


def _moment_capacity_kNm(section: SectionProperties, material: Material) -> float:
    w_m3 = section.wx_cm3 * 1e-6
    return material.fy_mpa * w_m3 * 1e3


def _axial_capacity_kN(section: SectionProperties, material: Material) -> float:
    area_m2 = section.area_cm2 * 1e-4
    return material.fy_mpa * area_m2 * 1e3


def _combination_vertical(loads: LoadConfig, snow: float, wind_pressure: float) -> Tuple[float, float]:
    """Return two ULS vertical load intensities (kN/m²): snow-leading and wind-leading."""

    g = loads.roof_self_weight_kN_m2 + loads.additional_permanent_kN_m2
    q_snow = snow
    # vertical wind suction ignored -> conservative vertical load only
    comb_snow = loads.gamma_g * g + loads.gamma_q * q_snow + loads.gamma_q * loads.psi0_wind * 0
    comb_wind = loads.gamma_g * g + loads.gamma_q * 0 + loads.gamma_q * loads.psi0_snow * q_snow
    return comb_snow, comb_wind


def _combination_wind_horizontal(loads: LoadConfig, wind_pressure: float) -> float:
    return loads.gamma_q * wind_pressure


def _utilization(applied: Tuple[float, ...], capacity: Tuple[float, ...]) -> float:
    return max(a / c if c > 0 else 0.0 for a, c in zip(applied, capacity))


def _lookup(section: str, material: str) -> Tuple[SectionProperties, Material]:
    if section not in _SECTION_LIBRARY:
        raise KeyError(f"Section '{section}' inconnue. Ajoutez-la à la bibliothèque simplifiée.")
    if material not in _MATERIAL_LIBRARY:
        raise KeyError(f"Matériau '{material}' non supporté.")
    return _SECTION_LIBRARY[section], _MATERIAL_LIBRARY[material]


def run_diagnostic(
    geom: GeometryConfig,
    sections: Dict[str, str],
    materials: Dict[str, str],
    loads: LoadConfig | None = None,
    purlins: PurlinConfig | None = None,
    bracing: BracingConfig | None = None,
) -> DiagnosticReport:
    """Run a quick structural check and propose reinforcements when needed."""

    loads = loads or LoadConfig()
    purlins = purlins or PurlinConfig()
    bracing = bracing or BracingConfig(panel_width_m=geom.bay_spacing_m)

    snow = calculer_charge_neige(loads.zone_neige, loads.altitude_m, geom.roof_pitch_deg, geom.roof_type)
    wind = calculer_charge_vent(loads.zone_vent, geom.eave_height_m, geom.span_m, geom.length_m, geom.roof_type)
    q_snow, q_wind_vertical = _combination_vertical(loads, snow, wind)
    wind_horizontal = _combination_wind_horizontal(loads, wind)

    load_summary = LoadSummary(
        permanent_kN_m2=loads.roof_self_weight_kN_m2 + loads.additional_permanent_kN_m2,
        snow_kN_m2=snow,
        wind_pressure_kN_m2=wind,
        q_vertical_uls_snow_leading=q_snow,
        q_vertical_uls_wind_leading=q_wind_vertical,
        wind_horizontal_uls=wind_horizontal,
    )

    # Rafter check (simply supported with uniform load on slope)
    rafter_section, rafter_mat = _lookup(sections["rafter"], materials.get("rafter", materials.get("frame", "S275")))
    q_line = max(q_snow, q_wind_vertical) * geom.bay_spacing_m
    l_rafter = geom.rafter_length_m
    m_max = q_line * l_rafter**2 / 8.0
    m_cap = _moment_capacity_kNm(rafter_section, rafter_mat)
    rafter_util = _utilization((m_max,), (m_cap,))
    rafter_res = ElementResult(
        name="poutre",
        utilization=rafter_util,
        applied=(m_max,),
        capacity=(m_cap,),
        note="Flexion simple (ELU) sur charge ULS gouvernante.",
    )

    # Column check: axial from vertical loads + bending from wind
    column_section, column_mat = _lookup(sections["column"], materials.get("column", materials.get("frame", "S275")))
    q_vertical_total = max(q_snow, q_wind_vertical) * geom.span_m * geom.bay_spacing_m
    n_column = q_vertical_total / 2.0  # share between two columns of the frame
    shear_wind = wind_horizontal * geom.eave_height_m * geom.bay_spacing_m
    m_wind = shear_wind * geom.eave_height_m / 2.0
    m_column_cap = _moment_capacity_kNm(column_section, column_mat)
    n_cap = _axial_capacity_kN(column_section, column_mat)
    column_util = _utilization((n_column, m_wind), (n_cap, m_column_cap))
    column_res = ElementResult(
        name="poteau",
        utilization=column_util,
        applied=(n_column, m_wind),
        capacity=(n_cap, m_column_cap),
        note="Interaction N/M évaluée par ratio enveloppe (ELU).",
    )

    # Purlin check on bay spacing
    purlin_section, purlin_mat = _lookup(purlins.section, purlins.material)
    q_purlin_line = max(q_snow, q_wind_vertical) * purlins.spacing_m
    m_purlin = q_purlin_line * geom.bay_spacing_m**2 / 8.0
    m_purlin_cap = _moment_capacity_kNm(purlin_section, purlin_mat)
    purlin_util = _utilization((m_purlin,), (m_purlin_cap,))
    purlin_res = ElementResult(
        name="pannes",
        utilization=purlin_util,
        applied=(m_purlin,),
        capacity=(m_purlin_cap,),
        note="Flexion simple d'une panne sur deux appuis.",
    )

    # Bracing: assume diagonal takes half of bay horizontal shear
    bracing_section, bracing_mat = _lookup(bracing.section, bracing.material)
    shear_panel = wind_horizontal * geom.eave_height_m * bracing.panel_width_m
    tie_force = shear_panel / 2.0
    n_bracing_cap = _axial_capacity_kN(bracing_section, bracing_mat)
    bracing_util = _utilization((tie_force,), (n_bracing_cap,))
    bracing_res = ElementResult(
        name="contreventement",
        utilization=bracing_util,
        applied=(tie_force,),
        capacity=(n_bracing_cap,),
        note="Effort de traction supposé dans une jambe de contreventement.",
    )

    max_util = max(rafter_util, column_util, purlin_util, bracing_util)
    status = "GO" if max_util <= 1.0 else "NO GO"
    reinforcements = determine_renforts(rafter_res, column_res, purlin_res, bracing_res)

    return DiagnosticReport(
        status=status,
        loads=load_summary,
        rafter=rafter_res,
        column=column_res,
        purlin=purlin_res,
        bracing=bracing_res,
        reinforcements=reinforcements,
    )


def determine_renforts(
    rafter: ElementResult, column: ElementResult, purlin: ElementResult, bracing: ElementResult
) -> List[str]:
    """Suggest typical reinforcements based on governing utilizations."""

    suggestions: List[str] = []
    if rafter.utilization > 1.0:
        surplus = rafter.utilization - 1.0
        suggestions.append(
            f"Doubler les arbalétriers (profil additionnel type IPE ou UPN) pour gagner ~{surplus*100:.0f}% de marge."
        )
    if column.utilization > 1.0:
        suggestions.append(
            "Ajouter des butons ou poteaux intermédiaires pour réduire la longueur de flambement et reprendre le moment de vent."
        )
    if purlin.utilization > 1.0:
        suggestions.append(
            "Rajouter des pannes intermédiaires ou jumeler les pannes existantes afin de diviser la portée sur toiture."
        )
    if bracing.utilization > 1.0:
        suggestions.append(
            "Renforcer les contreventements (section plus forte ou double croix) pour reprendre les efforts horizontaux."
        )
    if not suggestions:
        suggestions.append("Aucun renfort requis sur la base des hypothèses simplifiées.")
    return suggestions


class _SimplePDF:
    """Tiny PDF writer to avoid external dependencies."""

    def __init__(self) -> None:
        self.lines: List[Tuple[int, str]] = []
        self.y_cursor = 800

    @staticmethod
    def _escape(text: str) -> str:
        return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")

    def add(self, text: str, size: int = 10) -> None:
        self.lines.append((size, text))

    def render(self, output: Path) -> Path:
        content_lines = []
        y = self.y_cursor
        for size, text in self.lines:
            escaped = self._escape(text)
            content_lines.append(f"BT /F1 {size} Tf 50 {y} Td ({escaped}) Tj ET")
            y -= size + 4
        stream = "\n".join(content_lines).encode("latin-1", "replace")
        length = len(stream)

        header = b"%PDF-1.4\n"
        offsets = [0]
        objects: List[bytes] = []
        cursor = len(header)

        def _add(obj: str) -> None:
            nonlocal cursor
            data = obj.encode("latin-1") + b"\n"
            offsets.append(cursor)
            objects.append(data)
            cursor += len(data)

        _add("1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj")
        _add("2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj")
        _add(
            "3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >> endobj"
        )
        _add(f"4 0 obj << /Length {length} >> stream\n" + stream.decode("latin-1") + "\nendstream endobj")
        _add("5 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> endobj")

        body = header + b"".join(objects)
        xref_entries = ["0000000000 65535 f "] + [f"{off:010d} 00000 n " for off in offsets[1:]]
        size = len(xref_entries)
        xref_body = "\n".join(["xref", f"0 {size}", *xref_entries, f"trailer << /Size {size} /Root 1 0 R >>", "startxref", str(cursor), "%%EOF"])

        output.parent.mkdir(parents=True, exist_ok=True)
        with output.open("wb") as fh:
            fh.write(body)
            fh.write(xref_body.encode("latin-1"))
        return output


def generate_pdf_report(report: DiagnosticReport, output: Path) -> Path:
    """Export a concise PDF with hypotheses, results and reinforcements."""

    pdf = _SimplePDF()
    pdf.add("Diagnostic structurel hangar agricole", size=14)
    pdf.add(f"Verdict: {report.status}")
    pdf.add("Charges climatiques (kN/m²):")
    pdf.add(f"- Neige: {report.loads.snow_kN_m2:.2f}")
    pdf.add(f"- Vent (pression de base): {report.loads.wind_pressure_kN_m2:.2f}")
    pdf.add(f"- ULS vertical (neige gouvernante): {report.loads.q_vertical_uls_snow_leading:.2f}")
    pdf.add(f"- ULS vent horizontal: {report.loads.wind_horizontal_uls:.2f}")

    def _element_block(title: str, element: ElementResult) -> None:
        pdf.add(title, size=12)
        pdf.add(f"Utilisation: {element.utilization*100:.1f}%")
        applied = ", ".join(f"{v:.2f}" for v in element.applied)
        capacity = ", ".join(f"{v:.2f}" for v in element.capacity)
        pdf.add(f"Solicitations: {applied} / Capacités: {capacity}")
        pdf.add(element.note)

    _element_block("Poutre (arbalétrier)", report.rafter)
    _element_block("Poteau", report.column)
    _element_block("Pannes", report.purlin)
    _element_block("Contreventements", report.bracing)

    pdf.add("Renforts proposés", size=12)
    for renfort in report.reinforcements:
        pdf.add(f"- {renfort}")

    return pdf.render(output)

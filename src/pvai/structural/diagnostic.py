"""Simplified structural diagnostic tailored to agricultural hangars.

This module intentionally favors transparency and conservative assumptions over
full Eurocode coverage. It provides quick checks to determine whether a standard
portal frame can host additional loads (e.g. PV retrofit) and proposes common
reinforcement options when necessary.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import ceil, cos, radians
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


@dataclass
class ElementResult:
    """Usage ratio and governing actions for an element."""

    name: str
    utilization: float
    applied: Tuple[float, ...]
    capacity: Tuple[float, ...]
    note: str


@dataclass
class DiagnosticReport:
    status: Literal["GO", "NO GO"]
    snow_load_kN_m2: float
    wind_pressure_kN_m2: float
    rafter: ElementResult
    column: ElementResult
    reinforcements: List[str]


_SECTION_LIBRARY: Dict[str, SectionProperties] = {
    # Typical reference values (cm² / cm³) for quick sizing
    "IPE180": SectionProperties("IPE180", area_cm2=26.2, wx_cm3=206.0),
    "IPE200": SectionProperties("IPE200", area_cm2=30.6, wx_cm3=262.0),
    "HEA160": SectionProperties("HEA160", area_cm2=32.3, wx_cm3=193.0),
    "GL24_200x400": SectionProperties("GL24_200x400", area_cm2=800.0 / 100.0, wx_cm3=200.0 * 400.0**2 / 6 / 1000.0),
}

_MATERIAL_LIBRARY: Dict[str, Material] = {
    "S275": Material("S275", fy_mpa=275.0),
    "S355": Material("S355", fy_mpa=355.0),
    "GL24": Material("GL24", fy_mpa=24.0),
}


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
) -> DiagnosticReport:
    """Run a quick structural check and propose reinforcements when needed."""

    loads = loads or LoadConfig()
    snow = calculer_charge_neige(loads.zone_neige, loads.altitude_m, geom.roof_pitch_deg, geom.roof_type)
    wind = calculer_charge_vent(loads.zone_vent, geom.eave_height_m, geom.span_m, geom.length_m, geom.roof_type)

    q_perm = loads.roof_self_weight_kN_m2 + loads.additional_permanent_kN_m2
    q_var = snow * loads.safety_factor_actions
    q_total = q_perm + q_var

    # Rafter check (simply supported with uniform load on slope)
    rafter_section, rafter_mat = _lookup(sections["rafter"], materials.get("rafter", materials.get("frame", "S275")))
    q_line = q_total * geom.bay_spacing_m
    l_rafter = geom.rafter_length_m
    m_max = q_line * l_rafter**2 / 8.0
    m_cap = _moment_capacity_kNm(rafter_section, rafter_mat)
    rafter_util = _utilization((m_max,), (m_cap,))
    rafter_res = ElementResult(
        name="poutre",
        utilization=rafter_util,
        applied=(m_max,),
        capacity=(m_cap,),
        note="Flexion simple (ELU).",
    )

    # Column check: axial from vertical loads + bending from wind
    column_section, column_mat = _lookup(sections["column"], materials.get("column", materials.get("frame", "S275")))
    q_vertical_total = q_total * geom.span_m * geom.bay_spacing_m
    n_column = q_vertical_total / 2.0  # share between two columns of the frame
    shear_wind = wind * geom.eave_height_m * geom.bay_spacing_m
    m_wind = shear_wind * geom.eave_height_m / 2.0
    m_column_cap = _moment_capacity_kNm(column_section, column_mat)
    n_cap = _axial_capacity_kN(column_section, column_mat)
    column_util = _utilization((n_column, m_wind), (n_cap, m_column_cap))
    column_res = ElementResult(
        name="poteau",
        utilization=column_util,
        applied=(n_column, m_wind),
        capacity=(n_cap, m_column_cap),
        note="Interaction N/M évaluée par ratio enveloppe.",
    )

    status = "GO" if max(rafter_util, column_util) <= 1.0 else "NO GO"
    reinforcements = determine_renforts(rafter_res, column_res)

    return DiagnosticReport(
        status=status,
        snow_load_kN_m2=snow,
        wind_pressure_kN_m2=wind,
        rafter=rafter_res,
        column=column_res,
        reinforcements=reinforcements,
    )


def determine_renforts(rafter: ElementResult, column: ElementResult) -> List[str]:
    """Suggest typical reinforcements based on governing utilizations."""

    suggestions: List[str] = []
    if rafter.utilization > 1.0:
        suggestions.append("Doubler les arbalétriers (profil additionnel type IPE ou UPN).")
    if column.utilization > 1.0:
        suggestions.append("Ajouter des butons ou poteaux intermédiaires pour réduire les efforts sur poteaux.")
    if not suggestions:
        suggestions.append("Aucun renfort requis sur la base des hypothèses simplifiées.")
    return suggestions

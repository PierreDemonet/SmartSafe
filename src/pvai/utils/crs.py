"""Coordinate reference system helpers."""
from __future__ import annotations

from typing import Optional

from pyproj import CRS


def ensure_crs(crs_input: str | int | CRS | None, fallback: str = "EPSG:4326") -> CRS:
    """Return a valid CRS instance, using *fallback* if *crs_input* is None."""
    if crs_input is None:
        return CRS.from_user_input(fallback)
    if isinstance(crs_input, CRS):
        return crs_input
    return CRS.from_user_input(crs_input)


def crs_to_string(crs: CRS) -> str:
    """Represent the CRS using an EPSG or PROJ string."""
    if crs.to_authority():
        auth, code = crs.to_authority()
        return f"{auth}:{code}"
    return crs.to_proj4()

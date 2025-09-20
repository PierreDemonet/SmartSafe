"""Plugin loader for shading engines."""
from __future__ import annotations

from importlib import import_module

from pvrtx.plugins.base import ShadingEngine


def load_engine(name: str) -> ShadingEngine:
    if name == "optix":
        module = import_module("pvrtx_optix")
        return module.OptixEngine()  # type: ignore[attr-defined]
    if name == "dummy":
        from pvrtx.plugins.dummy.plugin import DummyEngine
        return DummyEngine()
    raise ValueError(f"Unknown shading engine '{name}'.")

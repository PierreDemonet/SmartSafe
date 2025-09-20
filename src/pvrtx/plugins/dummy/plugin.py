"""Fallback CPU shading plugin returning zeros."""
from __future__ import annotations

import numpy as np

from pvrtx.plugins.base import ShadingEngine


class DummyEngine(ShadingEngine):
    def __init__(self) -> None:
        self._count = 0

    def build_scene(self, mesh, materials):
        return None

    def set_module_patches(self, centers_f: np.ndarray, normals_f: np.ndarray,
                           centers_b: np.ndarray, normals_b: np.ndarray) -> None:
        self._count = len(centers_f)

    def compute_poa(self, dirs: np.ndarray, weights: np.ndarray):
        return (np.zeros(self._count, dtype=np.float32),
                np.zeros(self._count, dtype=np.float32))

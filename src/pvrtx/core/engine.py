"""High-level wrapper around shading plugins."""
from __future__ import annotations

from typing import Dict, Tuple

import numpy as np

from pvrtx.plugins.loader import load_engine
from pvrtx.sky.perez import sample_perez


class PVRTX:
    def __init__(self, plugin_name: str = "optix") -> None:
        self.engine = load_engine(plugin_name)

    def build(self, mesh: Dict, materials: Dict, centers_f: np.ndarray, normals_f: np.ndarray,
              centers_b: np.ndarray, normals_b: np.ndarray) -> None:
        self.engine.build_scene(mesh, materials)
        self.engine.set_module_patches(centers_f, normals_f, centers_b, normals_b)

    def compute_poa_step(self, dni: float, dhi: float, sun_vec: np.ndarray, n_dirs: int = 2048) -> Tuple[np.ndarray, np.ndarray]:
        dirs, weights = sample_perez(dhi, dni, sun_vec, n_dirs)
        return self.engine.compute_poa(dirs, weights)

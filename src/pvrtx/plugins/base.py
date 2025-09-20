"""Base interface for shading plugins."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Dict, Tuple

import numpy as np


class ShadingEngine(ABC):
    """Abstract base class for shading engines."""

    @abstractmethod
    def build_scene(self, mesh: Dict, materials: Dict) -> None:
        """Prepare the acceleration structures for the scene."""

    @abstractmethod
    def set_module_patches(self, centers_f: np.ndarray, normals_f: np.ndarray,
                           centers_b: np.ndarray, normals_b: np.ndarray) -> None:
        """Register module patches for irradiance accumulation."""

    @abstractmethod
    def compute_poa(self, dirs: np.ndarray, weights: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """Return (front, back) POA arrays for the provided ray bundle."""

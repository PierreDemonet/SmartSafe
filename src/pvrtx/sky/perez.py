"""Perez sky sampling (simplified)."""
from __future__ import annotations

from typing import Tuple

import numpy as np


def sample_perez(dhi: float, dni: float, sun_vec: np.ndarray, n_dirs: int = 2048) -> Tuple[np.ndarray, np.ndarray]:
    if n_dirs <= 0:
        raise ValueError("n_dirs must be > 0")
    u1 = np.random.rand(n_dirs)
    u2 = np.random.rand(n_dirs)
    theta = np.arccos(np.sqrt(1.0 - u1))
    phi = 2 * np.pi * u2
    dirs = np.stack([
        np.sin(theta) * np.cos(phi),
        np.sin(theta) * np.sin(phi),
        np.cos(theta)
    ], axis=1)
    weights = np.full(n_dirs, dhi / max(n_dirs, 1), dtype=np.float32)
    sun_dir = sun_vec / (np.linalg.norm(sun_vec) + 1e-9)
    dirs = np.vstack([dirs, sun_dir])
    weights = np.concatenate([weights, np.array([dni], dtype=np.float32)])
    return dirs.astype(np.float32), weights.astype(np.float32)

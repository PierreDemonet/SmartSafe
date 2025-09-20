"""Scene utilities for RTX shading."""
from __future__ import annotations

from pathlib import Path
from typing import Dict, Tuple

import numpy as np
import pandas as pd
import trimesh


def load_mesh_glb(path: str | Path) -> Dict[str, np.ndarray]:
    mesh = trimesh.load(path, force="mesh")
    if isinstance(mesh, trimesh.Scene):
        mesh = trimesh.util.concatenate(tuple(mesh.geometry.values()))
    vertices = np.asarray(mesh.vertices, dtype=np.float32)
    faces = np.asarray(mesh.faces, dtype=np.int32)
    return {"vertices": vertices, "faces": faces}


def build_module_patches(csv_path: str | Path) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    df = pd.read_csv(csv_path)
    centers = df[["x", "y", "z"]].to_numpy(dtype=np.float32)
    normals_f = df[["nx_f", "ny_f", "nz_f"]].to_numpy(dtype=np.float32)
    normals_b = df[["nx_b", "ny_b", "nz_b"]].to_numpy(dtype=np.float32)
    centers_b = df[["x", "y", "z"]].to_numpy(dtype=np.float32)
    return centers, normals_f, centers_b, normals_b

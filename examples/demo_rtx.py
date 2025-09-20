"""Demonstrate the RTX shading wrapper (uses dummy plugin by default)."""
import numpy as np

from pvrtx.core.engine import PVRTX
from pvrtx.scene.geometry import build_module_patches

centers_f, normals_f, centers_b, normals_b = build_module_patches("examples/data/layout_modules.csv")
mesh = {"vertices": np.zeros((0, 3), dtype=np.float32), "faces": np.zeros((0, 3), dtype=np.int32)}
materials = {"default": {"rho": 0.2}}

engine = PVRTX("dummy")
engine.build(mesh, materials, centers_f, normals_f, centers_b, normals_b)
poa_f, poa_b = engine.compute_poa_step(800.0, 100.0, np.array([0.0, 0.0, 1.0], dtype=np.float32))
print("POA front", poa_f)
print("POA back", poa_b)

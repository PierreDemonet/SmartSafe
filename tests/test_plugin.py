import numpy as np

from pvrtx.plugins.loader import load_engine


def test_dummy_plugin_returns_zero():
    eng = load_engine("dummy")
    centers = np.zeros((5, 3), dtype=np.float32)
    normals = np.tile(np.array([[0, 0, 1]], dtype=np.float32), (5, 1))
    eng.build_scene({}, {})
    eng.set_module_patches(centers, normals, centers, -normals)
    dirs = np.array([[0, 0, 1]], dtype=np.float32)
    weights = np.array([1000.0], dtype=np.float32)
    front, back = eng.compute_poa(dirs, weights)
    assert front.shape == (5,)
    assert np.allclose(front, 0.0)
    assert np.allclose(back, 0.0)

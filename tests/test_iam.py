import numpy as np
import pandas as pd

from pvai.pv.sim import _iam_fresnel


def test_fresnel_iam_properties():
    angles = pd.Series(np.linspace(0, 90, 10))
    iam = _iam_fresnel(angles, n_glass=1.526, ar_reflectance=0.02)
    assert np.isclose(iam.iloc[0], 1.0)
    assert iam.iloc[-1] == 0.0
    assert np.all((iam >= 0.0) & (iam <= 1.0))
    diffs = np.diff(iam.to_numpy())
    assert np.all(diffs <= 1e-6)

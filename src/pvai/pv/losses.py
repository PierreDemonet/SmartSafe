"""Loss model helpers."""
from __future__ import annotations

import pandas as pd

from pvai.models.schemas import LossParams


def apply_losses(ac_power: pd.Series, losses: LossParams) -> pd.DataFrame:
    """Return a DataFrame detailing sequential loss application."""
    df = pd.DataFrame({"p_ac_raw": ac_power})
    df["loss_soiling"] = losses.soiling_pct / 100.0
    df["loss_dc_cable"] = losses.dc_cable_pct / 100.0
    df["loss_ac_cable"] = losses.ac_cable_pct / 100.0
    availability = losses.availability_pct / 100.0

    effective = ac_power.copy()
    effective *= 1.0 - df["loss_soiling"]
    effective *= 1.0 - df["loss_dc_cable"]
    effective *= 1.0 - df["loss_ac_cable"]
    effective *= availability
    df["p_ac_net"] = effective
    return df

"""Material helpers for RTX shading."""
from __future__ import annotations

from pathlib import Path
from typing import Dict

import yaml


def load_materials_yaml(path: str | Path) -> Dict:
    return yaml.safe_load(Path(path).read_text())

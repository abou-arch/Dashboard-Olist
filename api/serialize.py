"""Conversion des résultats pandas en JSON (NaN -> null, dates -> AAAA-MM-JJ)."""

import dataclasses
import math
from typing import Any

import numpy as np
import pandas as pd


def clean(value: Any) -> Any:
    """Valeur Python sérialisable en JSON, récursivement."""
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        return clean(dataclasses.asdict(value))
    if isinstance(value, dict):
        return {str(key): clean(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [clean(item) for item in value]
    if isinstance(value, pd.DataFrame):
        return records(value)
    if isinstance(value, pd.Timestamp):
        return None if pd.isna(value) else value.strftime("%Y-%m-%d")
    if isinstance(value, np.generic):
        value = value.item()
    if value is pd.NA or value is pd.NaT:
        return None
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


def records(df: pd.DataFrame) -> list[dict[str, Any]]:
    """Lignes d'un DataFrame sous forme de dictionnaires JSON."""
    return [clean(row) for row in df.to_dict(orient="records")]

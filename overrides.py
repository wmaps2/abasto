"""
overrides.py — Gestión de overrides manuales de forecast.
Almacena en data/overrides.json: {sku: {"YYYY-MM-DD": float, ...}}
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

_OVERRIDE_FILE = Path(__file__).parent / "data" / "overrides.json"


def load() -> dict[str, dict[str, float]]:
    """Devuelve {sku: {date_str: value}}. Retorna {} si no existe el archivo."""
    if not _OVERRIDE_FILE.exists():
        return {}
    try:
        return json.loads(_OVERRIDE_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def save(overrides: dict[str, dict[str, float]]) -> None:
    _OVERRIDE_FILE.write_text(json.dumps(overrides, indent=2), encoding="utf-8")


def set_sku(sku: str, rows: pd.DataFrame) -> None:
    """
    Guarda los overrides de un SKU.
    rows: DataFrame con columnas 'ds' (Timestamp) y 'override' (float | None).
    Solo se guardan las filas donde override no es nulo.
    """
    overrides = load()
    sku_data: dict[str, float] = {}
    for _, row in rows.iterrows():
        val = row.get("override")
        if val is not None and not pd.isna(val):
            sku_data[str(row["ds"].date())] = float(val)
    if sku_data:
        overrides[sku] = sku_data
    else:
        overrides.pop(sku, None)
    save(overrides)


def clear_sku(sku: str) -> None:
    overrides = load()
    if sku in overrides:
        del overrides[sku]
        save(overrides)


def apply(fc_df: pd.DataFrame, overrides: dict) -> pd.DataFrame:
    """
    Aplica overrides al DataFrame de forecast (columnas: unique_id, ds, AutoETS, …).
    Retorna una copia con AutoETS sustituido donde existan overrides.
    Normaliza timestamps (quita componente horario) para comparación robusta.
    """
    if not overrides:
        return fc_df
    fc_df = fc_df.copy()
    ds_norm = fc_df["ds"].dt.normalize()          # normalizar una vez, no en cada fila
    for sku, date_vals in overrides.items():
        for date_str, value in date_vals.items():
            date_norm = pd.Timestamp(date_str).normalize()
            mask = (fc_df["unique_id"] == sku) & (ds_norm == date_norm)
            if mask.any():
                fc_df.loc[mask, "AutoETS"] = value
    return fc_df


def skus_with_override(overrides: dict) -> list[str]:
    return list(overrides.keys())

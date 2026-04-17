"""
overrides.py — Gestión de overrides manuales de forecast.
Persiste en Supabase tabla overrides: (sku_id, fecha_target, valor, activo).
"""
from __future__ import annotations

import pandas as pd


def _sb_client():
    try:
        import streamlit as st
        url = st.secrets["SUPABASE_URL"]
        key = st.secrets["SUPABASE_KEY"]
    except Exception:
        import tomllib
        from pathlib import Path
        secrets_path = Path(__file__).parent / ".streamlit" / "secrets.toml"
        with open(secrets_path, "rb") as f:
            s = tomllib.load(f)
        url, key = s["SUPABASE_URL"], s["SUPABASE_KEY"]
    from supabase import create_client
    return create_client(url, key)


def load() -> dict[str, dict[str, float]]:
    """
    Retorna {sku: {"YYYY-MM-DD": float}} con los overrides activos más recientes.
    Mismo contrato que la versión JSON anterior.
    """
    try:
        rows = (_sb_client()
                .table("overrides")
                .select("sku_id, fecha_target, valor, creado_en")
                .eq("activo", True)
                .order("creado_en", desc=True)
                .execute().data)
    except Exception:
        return {}

    result: dict[str, dict[str, float]] = {}
    seen: set[tuple] = set()
    for r in rows:
        key = (r["sku_id"], r["fecha_target"])
        if key in seen:
            continue
        seen.add(key)
        sku  = r["sku_id"]
        date = str(r["fecha_target"])[:10]
        result.setdefault(sku, {})[date] = float(r["valor"])
    return result


def set_sku(sku: str, rows: pd.DataFrame) -> None:
    """
    Guarda los overrides de un SKU.
    rows: DataFrame con columnas 'ds' (Timestamp) y 'override' (float | None).
    Solo se insertan las filas donde override no es nulo.
    Las semanas sin override desactivan cualquier override previo activo.
    """
    sb = _sb_client()

    # Desactivar todos los overrides activos del SKU
    sb.table("overrides").update({"activo": False}).eq("sku_id", sku).eq("activo", True).execute()

    # Insertar nuevos overrides
    to_insert = []
    for _, row in rows.iterrows():
        val = row.get("override")
        if val is not None and not pd.isna(val):
            to_insert.append({
                "sku_id":       sku,
                "fecha_target": str(row["ds"].date()),
                "valor":        float(val),
                "activo":       True,
            })
    if to_insert:
        sb.table("overrides").insert(to_insert).execute()


def clear_sku(sku: str) -> None:
    """Desactiva todos los overrides activos de un SKU."""
    _sb_client().table("overrides").update({"activo": False}).eq("sku_id", sku).eq("activo", True).execute()


def apply(fc_df: pd.DataFrame, overrides: dict) -> pd.DataFrame:
    """
    Aplica overrides al DataFrame de forecast (columnas: unique_id, ds, AutoETS, …).
    Retorna una copia con AutoETS sustituido donde existan overrides.
    """
    if not overrides:
        return fc_df
    fc_df = fc_df.copy()
    ds_norm = fc_df["ds"].dt.normalize()
    for sku, date_vals in overrides.items():
        for date_str, value in date_vals.items():
            date_norm = pd.Timestamp(date_str).normalize()
            mask = (fc_df["unique_id"] == sku) & (ds_norm == date_norm)
            if mask.any():
                fc_df.loc[mask, "AutoETS"] = value
    return fc_df


def skus_with_override(overrides: dict) -> list[str]:
    return list(overrides.keys())

"""
data.py — Acceso a datos: Supabase (runtime) y CSV (carga manual).
"""
from __future__ import annotations

from typing import Optional, Tuple

import pandas as pd

from simulation.parametros import SKU_CONFIGS
from simulation.generador import generate_simulated_data  # re-export para forecast.py


# ---------------------------------------------------------------------------
# Supabase client
# ---------------------------------------------------------------------------

def _get_client():
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


# ---------------------------------------------------------------------------
# Lecturas desde Supabase
# ---------------------------------------------------------------------------

def get_productos() -> pd.DataFrame:
    """
    Retorna atributos de productos. Incluye precio_venta (del registro más
    reciente en historia_semanal), margen derivado, y cv_demanda de parametros.
    Columnas: sku, nombre, categoria, costo, costo_reputacional,
              lead_time_semanas, tasa_obsolescencia_semanal,
              precio_venta, margen, cv_demanda
    """
    sb = _get_client()

    prods = pd.DataFrame(
        sb.table("productos").select("*").execute().data
    ).rename(columns={"sku_id": "sku"})

    hist = pd.DataFrame(
        sb.table("historia_semanal")
        .select("sku_id, fecha, precio")
        .order("fecha", desc=True)
        .execute().data
    )
    precio_df = (hist
                 .drop_duplicates("sku_id")
                 .rename(columns={"sku_id": "sku", "precio": "precio_venta"})
                 [["sku", "precio_venta"]])

    df = prods.merge(precio_df, on="sku", how="left")
    df["margen"]     = df["precio_venta"] - df["costo"]
    df["cv_demanda"] = df["sku"].map(
        lambda s: SKU_CONFIGS.get(s, {}).get("cv_demanda", 0.2)
    )
    return df


def _col_missing(exc) -> bool:
    """True si el error de Supabase es por columna inexistente (código 42703)."""
    msg = str(exc)
    return "42703" in msg or "does not exist" in msg


def get_historia_semanal(fuentes: list[str] | None = None) -> pd.DataFrame:
    """
    Retorna historial de demanda semanal.
    Columnas: fecha (datetime), sku, cantidad
    fuentes: filtro por columna 'fuente' (ej. ['demo','uploaded']). None = todas.
    Si la columna 'fuente' aún no existe en la BD, carga todo sin filtrar.
    """
    sb, PAGE = _get_client(), 1000
    rows, offset = [], 0
    use_filter = fuentes is not None
    while True:
        q = sb.table("historia_semanal").select("sku_id, fecha, demanda")
        if use_filter:
            q = q.in_("fuente", fuentes)
        try:
            page = q.range(offset, offset + PAGE - 1).execute().data
        except Exception as exc:
            if use_filter and _col_missing(exc):
                use_filter = False  # columna no existe aún → carga sin filtro
                offset = 0
                rows = []
                continue
            raise
        rows.extend(page)
        if len(page) < PAGE:
            break
        offset += PAGE
    df = pd.DataFrame(rows).rename(columns={"sku_id": "sku", "demanda": "cantidad"})
    df["fecha"] = pd.to_datetime(df["fecha"])
    return df.sort_values(["sku", "fecha"]).reset_index(drop=True)


def get_inventario() -> pd.DataFrame:
    """
    Retorna stock actual.
    Columnas: sku, stock_disponible, stock_transito, fecha_llegada_transito
    Compatible con el formato que espera compra.py.
    """
    rows = _get_client().table("inventario").select("*").execute().data
    df = pd.DataFrame(rows).rename(columns={
        "sku_id":      "sku",
        "en_transito": "stock_transito",
    })
    df["fecha_llegada_transito"] = pd.to_datetime(df["fecha_llegada_transito"])
    return df[["sku", "stock_disponible", "stock_transito", "fecha_llegada_transito"]]


# ---------------------------------------------------------------------------
# Carga manual de CSV (upload desde UI)
# ---------------------------------------------------------------------------

def load_csv(file) -> Tuple[Optional[pd.DataFrame], Optional[str]]:
    """
    Carga y valida un CSV con columnas: fecha, sku, cantidad.
    Retorna (DataFrame, None) si es válido, o (None, mensaje_error) si no.
    """
    try:
        df = pd.read_csv(file, sep=None, engine="python", encoding="utf-8-sig")
    except UnicodeDecodeError:
        try:
            if hasattr(file, "seek"):
                file.seek(0)
            df = pd.read_csv(file, sep=None, engine="python", encoding="latin-1")
        except Exception as exc:
            return None, f"No se pudo leer el archivo: {exc}"
    except Exception as exc:
        return None, f"No se pudo leer el archivo: {exc}"

    df.columns = (df.columns
                  .str.strip()
                  .str.lower()
                  .str.replace(r"[^\w]", "_", regex=True)
                  .str.replace(r"_+", "_", regex=True)
                  .str.strip("_"))

    required = {"fecha", "sku", "cantidad"}
    missing  = required - set(df.columns)
    if missing:
        found = sorted(df.columns.tolist())
        return None, (
            f"Columnas faltantes: {sorted(missing)}. "
            f"El CSV debe tener: fecha, sku, cantidad. "
            f"Columnas detectadas: {found}."
        )

    df["fecha"]    = pd.to_datetime(df["fecha"], infer_datetime_format=True, errors="coerce")
    df["cantidad"] = pd.to_numeric(df["cantidad"], errors="coerce")

    n_bad_dates = df["fecha"].isna().sum()
    n_bad_qty   = df["cantidad"].isna().sum()
    if n_bad_dates:
        return None, f"{n_bad_dates} filas con fechas inválidas. Usa formato YYYY-MM-DD."
    if n_bad_qty:
        return None, f"{n_bad_qty} filas con valores no numéricos en 'cantidad'."

    df = df.dropna(subset=["fecha", "sku", "cantidad"]).copy()
    df["sku"]      = df["sku"].astype(str).str.strip()
    df["cantidad"] = df["cantidad"].clip(lower=0)
    df = df[["fecha", "sku", "cantidad"]]
    df = df.sort_values(["sku", "fecha"]).reset_index(drop=True)

    if df["sku"].nunique() < 1:
        return None, "El CSV no contiene ningún SKU válido."

    n_weeks_min = df.groupby("sku")["fecha"].count().min()
    if n_weeks_min < 12:
        return None, (
            f"El SKU con menos observaciones tiene {n_weeks_min} registros. "
            "Se recomienda al menos 12 semanas de historial."
        )

    return df, None


# ---------------------------------------------------------------------------
# Utilidades
# ---------------------------------------------------------------------------

def summary(df: pd.DataFrame) -> dict:
    """Estadísticas rápidas del dataset."""
    return {
        "n_skus":    df["sku"].nunique(),
        "n_weeks":   df["fecha"].nunique(),
        "date_min":  df["fecha"].min().strftime("%Y-%m-%d"),
        "date_max":  df["fecha"].max().strftime("%Y-%m-%d"),
        "total_qty": df["cantidad"].sum(),
    }

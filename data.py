"""
data.py — Carga y simulación de datos de ventas por SKU.
Formato esperado del CSV: fecha, sku, cantidad
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from typing import Optional, Tuple

# ---------------------------------------------------------------------------
# Configuración de SKUs simulados
# ---------------------------------------------------------------------------
# Categoría A — alta rotación, volúmenes altos, estacionalidad pronunciada
# Categoría B — rotación media, volúmenes medios, tendencias moderadas
# Categoría C — baja rotación, volúmenes bajos, alta variabilidad
SKU_CONFIGS: dict[str, dict] = {
    # ── Categoría A: Abarrotes / No perecibles ─────────────────────────────────
    # base 200-400 u/sem, estacionalidad suave (amp ≈ 8-11% del base)
    "SKU-A001": {"base": 280, "trend":  1.0,  "pattern": "summer",    "amp":  28, "noise": 35},
    "SKU-A002": {"base": 350, "trend":  1.5,  "pattern": "biannual",  "amp":  35, "noise": 45},
    "SKU-A003": {"base": 220, "trend":  0.5,  "pattern": "christmas", "amp":  22, "noise": 28},
    "SKU-A004": {"base": 400, "trend":  2.0,  "pattern": "summer",    "amp":  40, "noise": 50},
    "SKU-A005": {"base": 310, "trend":  0.8,  "pattern": "none",      "amp":   0, "noise": 40},
    # ── Categoría B: Moda / Temporada ──────────────────────────────────────────
    # base 30-80 u/sem, estacionalidad biannual fuerte (amp ≈ 40-55% del base)
    # CV alto → noise proporcional al base para que AutoETS detecte el patrón
    "SKU-B001": {"base":  60, "trend":  0.2,  "pattern": "biannual",  "amp":  30, "noise": 22},
    "SKU-B002": {"base":  45, "trend":  0.1,  "pattern": "biannual",  "amp":  22, "noise": 18},
    "SKU-B003": {"base":  75, "trend":  0.3,  "pattern": "biannual",  "amp":  38, "noise": 28},
    "SKU-B004": {"base":  35, "trend":  0.0,  "pattern": "biannual",  "amp":  17, "noise": 14},
    # ── Categoría C: Durables / Especialidad ───────────────────────────────────
    # base 5-20 u/sem, peak navideño claro, ruido bajo
    "SKU-C001": {"base":  12, "trend":  0.05, "pattern": "christmas", "amp":   5, "noise":  2},
    "SKU-C002": {"base":  18, "trend":  0.08, "pattern": "christmas", "amp":   8, "noise":  3},
    "SKU-C003": {"base":   8, "trend":  0.03, "pattern": "christmas", "amp":   3, "noise":  2},
}


def _seasonal(week_idx: int, pattern: str, amp: float) -> float:
    """
    Componente estacional para una semana (índice 0-based).
    Usa ondas coseno completas (periodo=52) para que AutoETS detecte
    la estacionalidad anual de manera confiable.
    """
    woy = (week_idx % 52) + 1  # semana del año 1–52
    if pattern == "christmas":
        # Pico semana 50 (dic), valle semana 24 (jun)
        return amp * np.cos(2 * np.pi * (woy - 50) / 52)
    if pattern == "summer":
        # Pico semana 26 (jul), valle semana 52 (dic)
        return amp * np.cos(2 * np.pi * (woy - 26) / 52)
    if pattern == "biannual":
        # Dos picos: semana 13 (mar) y semana 39 (sep)
        return amp * np.cos(4 * np.pi * (woy - 13) / 52)
    return 0.0


def _last_monday() -> pd.Timestamp:
    """Retorna el lunes de la semana pasada (última semana completa)."""
    today = pd.Timestamp.now().normalize()
    return today - pd.Timedelta(days=today.weekday()) - pd.Timedelta(weeks=1)


def generate_simulated_data() -> pd.DataFrame:
    """
    Genera 156 semanas (≈3 años) de ventas semanales para 12 SKUs distribuidos
    en 3 categorías con perfiles distintos de volumen, tendencia y estacionalidad:
      - Cat. A (SKU-A001..A005): alta rotación, volúmenes altos (250–400 base)
      - Cat. B (SKU-B001..B004): rotación media, volúmenes medios (75–130 base)
      - Cat. C (SKU-C001..C003): baja rotación, volúmenes bajos (15–25 base), mayor ruido relativo
    3 años garantizan que AutoETS disponga de ≥3 ciclos completos (s=52) para
    seleccionar estacionalidad con fiabilidad.
    El último punto siempre es el lunes de la semana pasada; el forecast arranca esta semana.
    """
    np.random.seed(42)
    dates = pd.date_range(end=_last_monday(), periods=156, freq="W-MON")

    records = []
    for sku, cfg in SKU_CONFIGS.items():
        for i, date in enumerate(dates):
            seasonal = _seasonal(i, cfg["pattern"], cfg["amp"])
            level    = max(0.0, cfg["base"] + cfg["trend"] * i + seasonal)
            qty      = max(0.0, np.random.normal(level, cfg["noise"]))
            records.append({"fecha": date, "sku": sku, "cantidad": round(qty, 1)})

    return pd.DataFrame(records)


def load_csv(file) -> Tuple[Optional[pd.DataFrame], Optional[str]]:
    """
    Carga y valida un CSV con columnas: fecha, sku, cantidad.
    Retorna (DataFrame, None) si es válido, o (None, mensaje_error) si no.
    """
    try:
        # sep=None + engine="python" detecta automáticamente el separador (,  ;  \t  |  etc.)
        # utf-8-sig elimina el BOM que Excel añade al exportar CSV
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

    # Normalizar nombres de columnas: minúsculas, sin espacios ni caracteres invisibles
    df.columns = (df.columns
                  .str.strip()
                  .str.lower()
                  .str.replace(r"[^\w]", "_", regex=True)  # caracteres especiales → _
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

    # Conversiones
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
    df = df[["fecha", "sku", "cantidad"]]  # orden canónico, independiente del CSV original
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


def summary(df: pd.DataFrame) -> dict:
    """Estadísticas rápidas del dataset."""
    return {
        "n_skus":   df["sku"].nunique(),
        "n_weeks":  df["fecha"].nunique(),
        "date_min": df["fecha"].min().strftime("%Y-%m-%d"),
        "date_max": df["fecha"].max().strftime("%Y-%m-%d"),
        "total_qty": df["cantidad"].sum(),
    }

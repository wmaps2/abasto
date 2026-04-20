"""Generador de demanda histórica simulada e inventario inicial."""
from __future__ import annotations

from datetime import timedelta

import numpy as np
import pandas as pd

from simulation.parametros import RANDOM_SEED, N_SEMANAS, FREQ, SKU_CONFIGS, STOCK_CONFIGS


def _seasonal(week_idx: int, pattern: str, amp: float) -> float:
    """
    Componente estacional para una semana (índice 0-based).
    Usa ondas coseno completas (periodo=52) para que AutoETS detecte
    la estacionalidad anual de manera confiable.
    """
    woy = (week_idx % 52) + 1  # semana del año 1–52
    if pattern == "christmas":
        return amp * np.cos(2 * np.pi * (woy - 50) / 52)
    if pattern == "summer":
        return amp * np.cos(2 * np.pi * (woy - 26) / 52)
    if pattern == "biannual":
        return amp * np.cos(4 * np.pi * (woy - 13) / 52)
    return 0.0


def _last_monday() -> pd.Timestamp:
    """Retorna el lunes de la semana pasada (última semana completa)."""
    today = pd.Timestamp.now().normalize()
    return today - pd.Timedelta(days=today.weekday()) - pd.Timedelta(weeks=1)


def generate_simulated_data() -> pd.DataFrame:
    """
    Genera N_SEMANAS de ventas semanales para todos los SKUs en SKU_CONFIGS.
    Retorna DataFrame con columnas: fecha, sku, cantidad.
    """
    np.random.seed(RANDOM_SEED)
    dates = pd.date_range(end=_last_monday(), periods=N_SEMANAS, freq=FREQ)

    records = []
    for sku, cfg in SKU_CONFIGS.items():
        for i, date in enumerate(dates):
            seasonal = _seasonal(i, cfg["pattern"], cfg["amp"])
            level    = max(0.0, cfg["base"] + cfg["trend"] * i + seasonal)
            qty      = max(0.0, np.random.normal(level, cfg["noise"]))
            records.append({"fecha": date, "sku": sku, "cantidad": int(round(qty))})

    return pd.DataFrame(records)


def generar_inventario_inicial(
    sku: str,
    mu: float,
    categoria: str,
    lead_time: int,
    rng: np.random.Generator,
) -> tuple[int, int, str]:
    """
    Retorna (stock_disponible, en_transito, fecha_llegada_transito) para un SKU.
    mu = demanda media de las últimas ventana_mu semanas simuladas.
    """
    cfg          = STOCK_CONFIGS[categoria]
    ultimo_lunes = _last_monday()

    stock   = mu * cfg["semanas_inventario"] * (1 + rng.uniform(-cfg["ruido_relativo"], cfg["ruido_relativo"]))
    transito = mu * cfg["semanas_transito"]  * (1 + rng.uniform(-cfg["ruido_relativo"], cfg["ruido_relativo"]))

    semanas_hasta_llegada = int(rng.integers(1, lead_time + 1))
    fecha_llegada         = ultimo_lunes + timedelta(weeks=semanas_hasta_llegada)

    return round(stock), round(transito), fecha_llegada.strftime("%Y-%m-%d")

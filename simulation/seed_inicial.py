"""
One-shot: puebla Supabase con datos iniciales desde los CSVs locales y el generador.
Tablas: productos, historia_semanal, inventario
Idempotente — upsert, creado_en se mantiene si la fila ya existe.
"""
from __future__ import annotations

import tomllib
from pathlib import Path

import numpy as np
import pandas as pd
from supabase import create_client

from simulation.generador import generate_simulated_data, generar_inventario_inicial
from simulation.parametros import SKU_CONFIGS, STOCK_CONFIGS

ROOT          = Path(__file__).resolve().parent.parent
SECRETS       = ROOT / ".streamlit" / "secrets.toml"
PRODUCTOS_CSV = ROOT / "data" / "productos.csv"


def _client():
    with open(SECRETS, "rb") as f:
        s = tomllib.load(f)
    return create_client(s["SUPABASE_URL"], s["SUPABASE_KEY"])


def _upsert(sb, table: str, rows: list[dict], conflict: str) -> int:
    sb.table(table).upsert(rows, on_conflict=conflict).execute()
    return len(rows)


def build_productos(df: pd.DataFrame) -> list[dict]:
    rows = []
    for _, r in df.iterrows():
        rows.append({
            "sku_id":                   r["sku"],
            "nombre":                   r["sku"],
            "categoria":                r["sku"].split("-")[1][0],
            "lead_time_semanas":        int(r["lead_time_semanas"]),
            "tasa_obsolescencia_semanal": float(r["tasa_obsolescencia_semanal"]),
            "costo":                    float(r["costo"]),
            "costo_reputacional":       float(r["costo_reputacional"]),
        })
    return rows


def build_historia(demanda_df: pd.DataFrame, precio_por_sku: dict[str, float]) -> list[dict]:
    rows = []
    for _, r in demanda_df.iterrows():
        rows.append({
            "sku_id":  r["sku"],
            "fecha":   r["fecha"].strftime("%Y-%m-%d"),
            "demanda": float(r["cantidad"]),
            "precio":  precio_por_sku[r["sku"]],
            "evento_tipo":  0,
        })
    return rows


def build_inventario(prod_df: pd.DataFrame, dem_df: pd.DataFrame) -> list[dict]:
    rng = np.random.default_rng(seed=42)
    rows = []
    for _, r in prod_df.iterrows():
        sku      = r["sku"]
        cat      = sku.split("-")[1][0]
        lt       = int(r["lead_time_semanas"])
        ventana  = STOCK_CONFIGS[cat]["ventana_mu"]
        mu       = float(
            dem_df[dem_df["sku"] == sku]
            .sort_values("fecha")
            .tail(ventana)["cantidad"]
            .mean()
        )
        stock, transito, fecha = generar_inventario_inicial(sku, mu, cat, lt, rng)
        rows.append({
            "sku_id":                 sku,
            "stock_disponible":       float(stock),
            "en_transito":            float(transito),
            "fecha_llegada_transito": fecha,
        })
    return rows


def main():
    sb = _client()

    prod_df = pd.read_csv(PRODUCTOS_CSV)
    dem_df  = generate_simulated_data()

    precio_por_sku = dict(zip(prod_df["sku"], prod_df["precio_venta"].astype(float)))

    n1 = _upsert(sb, "productos",        build_productos(prod_df),               "sku_id")
    n2 = _upsert(sb, "historia_semanal", build_historia(dem_df, precio_por_sku), "sku_id,fecha")
    n3 = _upsert(sb, "inventario",       build_inventario(prod_df, dem_df),      "sku_id")

    print(f"productos:        {n1} filas")
    print(f"historia_semanal: {n2} filas")
    print(f"inventario:       {n3} filas")


if __name__ == "__main__":
    main()

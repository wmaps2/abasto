"""
Migra datos de los CSVs locales a Supabase.
Tablas destino: productos, producto_atributos_historicos, stock_historico
Idempotente — usa upsert en todas las tablas.
"""
from pathlib import Path
from datetime import date

import pandas as pd
import tomllib
from supabase import create_client

ROOT = Path(__file__).resolve().parent.parent
SECRETS = ROOT / ".streamlit" / "secrets.toml"
PRODUCTOS_CSV = ROOT / "data" / "productos.csv"
STOCK_CSV = ROOT / "data" / "stock_actual.csv"


def load_secrets() -> dict:
    with open(SECRETS, "rb") as f:
        return tomllib.load(f)


def build_productos(df: pd.DataFrame) -> list[dict]:
    rows = []
    for _, r in df.iterrows():
        rows.append({
            "sku_id":              r["sku"],
            "nombre":              r["sku"],
            "categoria":           r["sku"].split("-")[1][0],
            "obsolescencia_anual": round(r["tasa_obsolescencia_semanal"] * 52, 6),
        })
    return rows


def build_atributos(df: pd.DataFrame) -> list[dict]:
    rows = []
    for _, r in df.iterrows():
        rows.append({
            "sku_id":             r["sku"],
            "fecha_valida_desde": "2026-01-01",
            "fecha_valida_hasta": None,
            "precio":             r["precio_venta"],
            "margen":             r["margen"],
            "costo_reposicion":   r["costo_reputacional"],
            "lead_time_semanas":  int(r["lead_time_semanas"]),
        })
    return rows


def build_stock(df: pd.DataFrame) -> list[dict]:
    hoy = date.today().isoformat()
    rows = []
    for _, r in df.iterrows():
        rows.append({
            "sku_id":                 r["sku"],
            "fecha":                  hoy,
            "stock_disponible":       int(r["stock_disponible"]),
            "en_transito":            int(r["stock_transito"]),
            "fecha_llegada_transito": r["fecha_llegada_transito"],
        })
    return rows


def upsert(client, table: str, rows: list[dict], conflict_col: str) -> int:
    client.table(table).upsert(rows, on_conflict=conflict_col).execute()
    return len(rows)


def main():
    secrets = load_secrets()
    sb = create_client(secrets["SUPABASE_URL"], secrets["SUPABASE_KEY"])

    prod_df  = pd.read_csv(PRODUCTOS_CSV)
    stock_df = pd.read_csv(STOCK_CSV)

    n1 = upsert(sb, "productos",
                build_productos(prod_df),
                "sku_id")

    n2 = upsert(sb, "producto_atributos_historicos",
                build_atributos(prod_df),
                "sku_id,fecha_valida_desde")

    n3 = upsert(sb, "stock_historico",
                build_stock(stock_df),
                "sku_id,fecha")

    print(f"productos:                     {n1} filas")
    print(f"producto_atributos_historicos: {n2} filas")
    print(f"stock_historico:               {n3} filas")


if __name__ == "__main__":
    main()

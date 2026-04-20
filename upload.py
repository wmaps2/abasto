"""
upload.py — Gestión de datos personalizados: template, upload, delete.
"""
from __future__ import annotations

import io
from datetime import timedelta


import numpy as np
import pandas as pd

DEMO_SKUS: frozenset[str] = frozenset([
    "SKU-A001", "SKU-A002", "SKU-A003", "SKU-A004", "SKU-A005",
    "SKU-B001", "SKU-B002", "SKU-B003", "SKU-B004",
    "SKU-C001", "SKU-C002", "SKU-C003",
])

META_COLS = [
    "sku_id", "categoria", "lead_time_semanas",
    "costo", "precio", "costo_reputacional", "tasa_obsolescencia_semanal",
]


class UploadError(Exception):
    pass


def _sb():
    from data import _get_client
    return _get_client()


def _col_missing(exc) -> bool:
    msg = str(exc)
    return "42703" in msg or "does not exist" in msg


MIGRATION_SQL = """
-- Ejecutar en Supabase SQL Editor:
ALTER TABLE productos        ADD COLUMN IF NOT EXISTS fuente VARCHAR(10) DEFAULT 'demo';
ALTER TABLE historia_semanal ADD COLUMN IF NOT EXISTS fuente VARCHAR(10) DEFAULT 'demo';
ALTER TABLE inventario       ADD COLUMN IF NOT EXISTS fuente VARCHAR(10) DEFAULT 'demo';
UPDATE productos        SET fuente = 'demo' WHERE fuente IS NULL;
UPDATE historia_semanal SET fuente = 'demo' WHERE fuente IS NULL;
UPDATE inventario       SET fuente = 'demo' WHERE fuente IS NULL;
"""


def _last_monday() -> pd.Timestamp:
    today = pd.Timestamp.now().normalize()
    return today - pd.Timedelta(days=today.weekday()) - pd.Timedelta(weeks=1)


def _template_dates() -> list[str]:
    """156 lunes consecutivos, más reciente primero."""
    last = _last_monday()
    return [(last - pd.Timedelta(weeks=i)).strftime("%Y-%m-%d")
            for i in range(0, 156)]


# ─── Template ─────────────────────────────────────────────────────────────────

def build_template_xlsx() -> bytes:
    """
    Excel template: hoja 'Datos' con columnas META_COLS + fechas.
    Demanda en enteros, metadata con decimales normales.
    """
    sb    = _sb()
    dates = _template_dates()

    all_prods = pd.DataFrame(sb.table("productos").select("*").execute().data)
    prods = all_prods[all_prods["sku_id"].isin(DEMO_SKUS)].copy()

    # Precio más reciente por SKU (con fallback si columna fuente no existe)
    try:
        precio_rows = (sb.table("historia_semanal")
                       .select("sku_id,fecha,precio")
                       .eq("fuente", "demo")
                       .order("fecha", desc=True)
                       .execute().data)
    except Exception as exc:
        if _col_missing(exc):
            precio_rows = (sb.table("historia_semanal")
                           .select("sku_id,fecha,precio")
                           .order("fecha", desc=True)
                           .execute().data)
        else:
            raise
    precio_dict = (
        pd.DataFrame(precio_rows).drop_duplicates("sku_id").set_index("sku_id")["precio"].to_dict()
        if precio_rows else {}
    )

    # Historia de demanda (paginada, con fallback)
    hist_rows: list[dict] = []
    offset, PAGE = 0, 1000
    _filter_demo = True
    while True:
        q = sb.table("historia_semanal").select("sku_id,fecha,demanda")
        if _filter_demo:
            q = q.eq("fuente", "demo")
        try:
            page = q.range(offset, offset + PAGE - 1).execute().data
        except Exception as exc:
            if _filter_demo and _col_missing(exc):
                _filter_demo = False
                offset = 0
                hist_rows = []
                continue
            raise
        hist_rows.extend(page)
        if len(page) < PAGE:
            break
        offset += PAGE

    hist = (pd.DataFrame(hist_rows) if hist_rows
            else pd.DataFrame(columns=["sku_id", "fecha", "demanda"]))
    hist["fecha"] = pd.to_datetime(hist["fecha"]).dt.strftime("%Y-%m-%d")

    data_rows: list[dict] = []
    for _, p in prods.iterrows():
        sid = str(p.get("sku_id", ""))
        h   = hist[hist["sku_id"] == sid].set_index("fecha")["demanda"].to_dict()
        row: dict = {
            "sku_id":                     sid,
            "categoria":                  p.get("categoria", ""),
            "lead_time_semanas":          float(p.get("lead_time_semanas", 4) or 0),
            "costo":                      float(p.get("costo", 0) or 0),
            "precio":                     float(precio_dict.get(sid, 0) or 0),
            "costo_reputacional":         float(p.get("costo_reputacional", 0) or 0),
            "tasa_obsolescencia_semanal": float(p.get("tasa_obsolescencia_semanal", 0) or 0),
        }
        for d in dates:
            v = h.get(d)
            row[d] = int(round(float(v))) if v else None
        data_rows.append(row)

    df_out = pd.DataFrame(data_rows, columns=META_COLS + dates)

    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        df_out.to_excel(writer, sheet_name="Datos", index=False)
    return buf.getvalue()


# ─── Parse / validate ─────────────────────────────────────────────────────────

def parse_upload(file) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Valida y parsea el CSV subido.
    Returns (df_meta, df_demand).
    df_meta  cols: META_COLS presentes en el CSV
    df_demand cols: sku_id + columnas de fecha
    Raises UploadError si hay problemas de formato.
    """
    try:
        raw = pd.read_excel(file, sheet_name="Datos", dtype=str)
    except Exception as exc:
        raise UploadError(f"No se pudo leer el Excel: {exc}")

    if raw.empty:
        raise UploadError("El archivo Excel está vacío.")

    # Detectar filas de referencia demo (por si se exportó desde CSV viejo)
    first_col = raw.columns[0]
    if raw[first_col].astype(str).str.startswith("#").any():
        raise UploadError(
            "Elimina las filas de referencia (las que empiezan con #) antes de subir."
        )

    if "sku_id" not in raw.columns:
        raise UploadError("El CSV debe tener columna 'sku_id'.")

    raw = raw.dropna(subset=["sku_id"])
    raw = raw[raw["sku_id"].str.strip() != ""].copy()

    if raw.empty:
        raise UploadError("No hay filas con SKU válido.")

    # Bloquear SKUs demo
    demo_in = sorted({s for s in raw["sku_id"].str.strip() if s in DEMO_SKUS})
    if demo_in:
        raise UploadError(f"No se puede modificar SKU demo: {', '.join(demo_in)}")

    # Columnas requeridas de metadata
    required = ["sku_id", "categoria", "lead_time_semanas", "costo", "precio"]
    missing  = [c for c in required if c not in raw.columns]
    if missing:
        raise UploadError(f"Columnas faltantes: {missing}")

    date_cols = [c for c in raw.columns if c not in META_COLS]
    if not date_cols:
        raise UploadError("No hay columnas de demanda (fechas YYYY-MM-DD) en el CSV.")

    raw["sku_id"] = raw["sku_id"].str.strip()

    df_meta   = raw[[c for c in META_COLS if c in raw.columns]].copy()
    df_demand = raw[["sku_id"] + date_cols].copy()

    for c in date_cols:
        df_demand[c] = pd.to_numeric(df_demand[c], errors="coerce").fillna(0.0).clip(lower=0)

    return df_meta, df_demand


def check_conflicts(sku_ids: list[str]) -> list[str]:
    """Retorna sku_ids que ya existen con fuente='uploaded' en Supabase."""
    try:
        rows = (_sb().table("productos")
                     .select("sku_id")
                     .eq("fuente", "uploaded")
                     .in_("sku_id", sku_ids)
                     .execute().data)
        return [r["sku_id"] for r in rows]
    except Exception as exc:
        if _col_missing(exc):
            return []  # columna no existe → no hay conflictos uploaded
        return []


# ─── Upload ───────────────────────────────────────────────────────────────────

def _calc_inventory(
    sku_id: str,
    categoria: str,
    lead_time: int,
    demand_series: pd.Series,
) -> tuple[int, int, str]:
    """Calcula stock inicial usando STOCK_CONFIGS (igual que el generador simulado)."""
    from simulation.parametros import STOCK_CONFIGS

    cat = str(categoria).upper()[0] if categoria else "A"
    if cat not in STOCK_CONFIGS:
        cat = "A"
    cfg     = STOCK_CONFIGS[cat]
    ventana = cfg["ventana_mu"]
    vals    = demand_series.dropna().values
    recent  = vals[-ventana:] if len(vals) >= ventana else vals
    mu      = float(recent.mean()) if len(recent) > 0 else 10.0
    if not np.isfinite(mu) or mu <= 0:
        mu = 10.0

    rng      = np.random.default_rng(abs(hash(sku_id)) % (2**32))
    noise    = cfg["ruido_relativo"]
    stock    = mu * cfg["semanas_inventario"] * (1 + rng.uniform(-noise, noise))
    transito = mu * cfg["semanas_transito"]   * (1 + rng.uniform(-noise, noise))

    semanas_a_llegada = int(rng.integers(1, max(2, lead_time) + 1))
    fecha_llegada     = (_last_monday() + timedelta(weeks=semanas_a_llegada)).strftime("%Y-%m-%d")

    return int(max(0, round(stock))), int(max(0, round(transito))), fecha_llegada


def upload_skus(
    df_meta: pd.DataFrame,
    df_demand: pd.DataFrame,
    replace: bool = False,
) -> list[str]:
    """
    Inserta/reemplaza SKUs en productos, historia_semanal e inventario.
    Returns lista de sku_ids subidos exitosamente.
    Raises UploadError si hay error de datos.
    """
    sb        = _sb()
    date_cols = [c for c in df_demand.columns if c != "sku_id"]
    done: list[str] = []

    for _, meta in df_meta.iterrows():
        sku_id = str(meta["sku_id"]).strip()

        if replace:
            _delete_sku(sb, sku_id)

        try:
            categoria = str(meta.get("categoria", "A")).strip()
            lead_time = int(float(meta.get("lead_time_semanas") or 4))
            costo     = float(meta.get("costo") or 0)
            precio    = float(meta.get("precio") or 0)
            cr        = float(meta.get("costo_reputacional") or 0)
            obs       = float(meta.get("tasa_obsolescencia_semanal") or 0)
        except (ValueError, TypeError) as exc:
            raise UploadError(f"SKU {sku_id}: datos numéricos inválidos — {exc}")

        # productos
        sb.table("productos").upsert({
            "sku_id":                     sku_id,
            "nombre":                     sku_id,
            "categoria":                  categoria,
            "lead_time_semanas":          lead_time,
            "costo":                      costo,
            "costo_reputacional":         cr,
            "tasa_obsolescencia_semanal": obs,
            "fuente":                     "uploaded",
        }, on_conflict="sku_id").execute()

        # historia_semanal
        demand_row = df_demand[df_demand["sku_id"] == sku_id]
        if demand_row.empty:
            raise UploadError(f"SKU {sku_id}: sin datos de demanda.")
        demand_row = demand_row.iloc[0]

        hist_rows = [
            {
                "sku_id":      sku_id,
                "fecha":       d,
                "demanda":     float(demand_row[d]),
                "precio":      precio,
                "evento_tipo": 0,
                "fuente":      "uploaded",
            }
            for d in date_cols
        ]
        BATCH = 200
        for i in range(0, len(hist_rows), BATCH):
            sb.table("historia_semanal").upsert(
                hist_rows[i:i+BATCH], on_conflict="sku_id,fecha"
            ).execute()

        # inventario
        demand_series = pd.Series([float(demand_row[d]) for d in date_cols])
        stock, transito, fecha_llegada = _calc_inventory(
            sku_id, categoria, lead_time, demand_series
        )
        sb.table("inventario").upsert({
            "sku_id":                 sku_id,
            "stock_disponible":       stock,
            "en_transito":            transito,
            "fecha_llegada_transito": fecha_llegada,
            "fuente":                 "uploaded",
        }, on_conflict="sku_id").execute()

        done.append(sku_id)

    return done


def _delete_sku(sb, sku_id: str) -> None:
    sb.table("forecasts").delete().eq("sku_id", sku_id).execute()
    sb.table("historia_semanal").delete().eq("sku_id", sku_id).execute()
    sb.table("inventario").delete().eq("sku_id", sku_id).execute()
    sb.table("productos").delete().eq("sku_id", sku_id).execute()


# ─── Delete ───────────────────────────────────────────────────────────────────

def delete_uploaded_data() -> int:
    """Borra todos los datos con fuente='uploaded'. Returns nro de SKUs borrados."""
    sb   = _sb()
    rows = (sb.table("productos")
              .select("sku_id")
              .eq("fuente", "uploaded")
              .execute().data)
    skus = [r["sku_id"] for r in rows]

    if skus:
        for sku in skus:
            sb.table("forecasts").delete().eq("sku_id", sku).execute()
        sb.table("historia_semanal").delete().eq("fuente", "uploaded").execute()
        sb.table("inventario").delete().eq("fuente", "uploaded").execute()
        sb.table("productos").delete().eq("fuente", "uploaded").execute()

    return len(skus)


def get_uploaded_count() -> int:
    """Retorna el número de SKUs con fuente='uploaded'. 0 si columna no existe."""
    try:
        rows = (_sb().table("productos")
                     .select("sku_id", count="exact")
                     .eq("fuente", "uploaded")
                     .execute())
        return rows.count or 0
    except Exception as exc:
        if _col_missing(exc):
            return 0
        return 0

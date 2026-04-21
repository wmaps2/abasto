"""
simulation/avanzar_semana.py
Simulador semanal: genera demanda para nuevas semanas y avanza el tránsito.

Uso:
    python avanzar_semana.py             # avanzar 1 semana
    python avanzar_semana.py --weeks 4   # avanzar 4 semanas
    python avanzar_semana.py --dry-run   # ver qué haría sin ejecutar
"""
from __future__ import annotations

import argparse
import sys
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")

sys.path.insert(0, str(Path(__file__).parent.parent))

import numpy as np
import pandas as pd

from simulation.parametros import SKU_CONFIGS, RANDOM_SEED

DEMO_SKUS: list[str] = list(SKU_CONFIGS.keys())


# ─── Supabase ─────────────────────────────────────────────────────────────────

def _sb():
    from data import _get_client
    return _get_client()


# ─── Generación de demanda ────────────────────────────────────────────────────

def _seasonal(week_idx: int, pattern: str, amp: float) -> float:
    woy = (week_idx % 52) + 1
    if pattern == "christmas":
        return amp * np.cos(2 * np.pi * (woy - 50) / 52)
    if pattern == "summer":
        return amp * np.cos(2 * np.pi * (woy - 26) / 52)
    if pattern == "biannual":
        return amp * np.cos(4 * np.pi * (woy - 13) / 52)
    return 0.0


def _generar_demanda(sku: str, week_idx: int, sku_offset: int) -> int:
    cfg      = SKU_CONFIGS[sku]
    seasonal = _seasonal(week_idx, cfg["pattern"], cfg["amp"])
    level    = max(0.0, cfg["base"] + cfg["trend"] * week_idx + seasonal)
    # Semilla determinista por (sku, semana) para reproducibilidad
    rng = np.random.default_rng(RANDOM_SEED + week_idx * 10_000 + sku_offset)
    return int(max(0, round(rng.normal(level, cfg["noise"]))))


# ─── Acciones principales ─────────────────────────────────────────────────────

def _insertar_semana(
    sb,
    nueva_fecha: pd.Timestamp,
    week_idx: int,
    precio_por_sku: dict[str, float],
    dry_run: bool,
) -> None:
    rows = []
    for i, sku in enumerate(DEMO_SKUS):
        demanda = _generar_demanda(sku, week_idx, sku_offset=i)
        rows.append({
            "sku_id":      sku,
            "fecha":       nueva_fecha.strftime("%Y-%m-%d"),
            "demanda":     demanda,
            "precio":      precio_por_sku.get(sku, 0.0),
            "evento_tipo": 0,
            "fuente":      "demo",
        })
        print(f"  ✓ {sku}: {demanda:,} unidades")

    if not dry_run:
        sb.table("historia_semanal").upsert(rows, on_conflict="sku_id,fecha").execute()


def _actualizar_transito(sb, dias: int, dry_run: bool) -> int:
    try:
        rows = (sb.table("inventario")
                  .select("sku_id, fecha_llegada_transito")
                  .eq("fuente", "demo")
                  .gt("en_transito", 0)
                  .execute().data)
    except Exception:
        # fallback si columna fuente no existe
        rows = (sb.table("inventario")
                  .select("sku_id, fecha_llegada_transito, en_transito")
                  .execute().data)
        rows = [r for r in rows if (r.get("sku_id") in DEMO_SKUS
                                    and (r.get("en_transito") or 0) > 0)]

    if not rows:
        return 0

    for r in rows:
        nueva = (pd.Timestamp(r["fecha_llegada_transito"])
                 + pd.Timedelta(days=dias)).strftime("%Y-%m-%d")
        if not dry_run:
            (sb.table("inventario")
               .update({"fecha_llegada_transito": nueva})
               .eq("sku_id", r["sku_id"])
               .execute())

    return len(rows)


# ─── Main ─────────────────────────────────────────────────────────────────────

def main(n_weeks: int = 1, dry_run: bool = False) -> None:
    tag = " [DRY-RUN]" if dry_run else ""
    print(f"\n=== SIMULADOR SEMANAL{tag} ===")

    sb = _sb()

    # 1. Última fecha y conteo de semanas existentes para SKU-A001
    fecha_rows = (sb.table("historia_semanal")
                    .select("fecha")
                    .eq("fuente", "demo")
                    .eq("sku_id", DEMO_SKUS[0])
                    .order("fecha", desc=False)
                    .execute().data)

    if not fecha_rows:
        print("✗ No hay datos demo en historia_semanal. Ejecuta seed_inicial.py primero.")
        sys.exit(1)

    ultima_fecha        = pd.Timestamp(fecha_rows[-1]["fecha"])
    n_semanas_existentes = len(fecha_rows)

    print(f"\nÚltima fecha en BD : {ultima_fecha.strftime('%Y-%m-%d')}")
    print(f"Semanas existentes : {n_semanas_existentes}")

    # 2. Precio más reciente por SKU (reutilizado en todas las semanas)
    precio_rows = (sb.table("historia_semanal")
                     .select("sku_id, precio")
                     .eq("fuente", "demo")
                     .in_("sku_id", DEMO_SKUS)
                     .order("fecha", desc=True)
                     .execute().data)
    precio_por_sku: dict[str, float] = {}
    for r in precio_rows:
        if r["sku_id"] not in precio_por_sku:
            precio_por_sku[r["sku_id"]] = float(r["precio"] or 0)

    # 3. Generar una semana por iteración
    for w in range(n_weeks):
        nueva_fecha = ultima_fecha + pd.Timedelta(weeks=w + 1)
        week_idx    = n_semanas_existentes + w

        print(f"\nNueva fecha : {nueva_fecha.strftime('%Y-%m-%d')}")
        print(f"Generando demanda para {len(DEMO_SKUS)} SKUs...")
        _insertar_semana(sb, nueva_fecha, week_idx, precio_por_sku, dry_run)

    # 4. Avanzar tránsito (7 días × semanas avanzadas)
    dias_transito = 7 * n_weeks
    print(f"\nActualizando tránsito (+{dias_transito} días)...")
    n_trans = _actualizar_transito(sb, dias_transito, dry_run)
    print(f"  ✓ {n_trans} registros actualizados")

    fecha_final = ultima_fecha + pd.Timedelta(weeks=n_weeks)
    print(f"\n=== COMPLETADO{tag} ===")
    if n_weeks == 1:
        print(f"Nueva semana agregada : {fecha_final.strftime('%Y-%m-%d')}\n")
    else:
        print(f"{n_weeks} semanas agregadas hasta : {fecha_final.strftime('%Y-%m-%d')}\n")


# ─── CLI ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Simulador semanal: agrega demanda demo y avanza tránsito."
    )
    parser.add_argument(
        "--weeks", type=int, default=1,
        help="Número de semanas a avanzar (default: 1)",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Muestra qué haría sin insertar nada en Supabase",
    )
    args = parser.parse_args()
    main(n_weeks=args.weeks, dry_run=args.dry_run)

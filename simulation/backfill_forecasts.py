"""
simulation/backfill_forecasts.py
Genera y persiste forecasts históricos para las últimas N semanas en Supabase.

Uso:
    python simulation/backfill_forecasts.py
    python simulation/backfill_forecasts.py --weeks 12   # backfill más corto
    python simulation/backfill_forecasts.py --dry-run    # ver qué haría sin insertar

Idempotente: verifica qué fechas ya tienen datos y las saltea.
Batch insert cada 100 filas para no sobrecargar Supabase.
"""
from __future__ import annotations

import argparse
import sys
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")

# Raíz del proyecto en sys.path para importar forecasting / data
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
from tqdm import tqdm

import data as data_module
import forecasting as fc_module

# ---------------------------------------------------------------------------
# Configuración
# ---------------------------------------------------------------------------
DEFAULT_WEEKS = 24
BATCH_SIZE    = 100


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _last_monday(ts: pd.Timestamp) -> pd.Timestamp:
    """Retorna el lunes anterior o igual al timestamp dado."""
    return (ts - pd.Timedelta(days=ts.weekday())).normalize()


def _get_existing_dates(sb, cutoff_dates: list[pd.Timestamp]) -> set[str]:
    """
    Consulta Supabase y retorna el conjunto de fechas (YYYY-MM-DD) que ya
    tienen al menos un registro en `forecasts` dentro del rango de cutoffs.
    Se compara contra la parte de fecha de `fecha_calculo`.
    """
    if not cutoff_dates:
        return set()

    min_dt = min(cutoff_dates).strftime("%Y-%m-%dT00:00:00")
    max_dt = max(cutoff_dates).strftime("%Y-%m-%dT23:59:59")

    rows = (
        sb.table("forecasts")
          .select("fecha_calculo")
          .gte("fecha_calculo", min_dt)
          .lte("fecha_calculo", max_dt)
          .execute()
          .data
    )
    # Extraer solo la parte de fecha (los primeros 10 caracteres de ISO timestamp)
    return {r["fecha_calculo"][:10] for r in rows}


def _build_rows(
    fc_df: pd.DataFrame,
    minfo: fc_module.ModelInfo,
    fecha_calculo: pd.Timestamp,
) -> list[dict]:
    """
    Construye las filas para la tabla `forecasts` a partir del DataFrame de
    forecast. Schema idéntico al que usa forecasting._sb_write_forecast.
    """
    ts = fecha_calculo.isoformat()
    P  = fc_module.PRIMARY

    def _f(row, col):
        v = row.get(col)
        return float(v) if v is not None and pd.notna(v) else None

    rows: list[dict] = []
    for sku, grp in fc_df.groupby("unique_id"):
        for h, (_, row) in enumerate(grp.sort_values("ds").iterrows(), start=1):
            rows.append({
                "sku_id":         sku,
                "fecha_calculo":  ts,
                "fecha_target":   row["ds"].strftime("%Y-%m-%d"),
                "horizonte":      h,
                "valor":          _f(row, P),
                "modelo":         minfo.name,
                "modelo_version": "v1",
                "ic_70_lower":    _f(row, f"{P}-lo-70"),
                "ic_70_upper":    _f(row, f"{P}-hi-70"),
                "ic_95_lower":    _f(row, f"{P}-lo-95"),
                "ic_95_upper":    _f(row, f"{P}-hi-95"),
            })
    return rows


def _batch_insert(sb, rows: list[dict], dry_run: bool = False) -> None:
    """Inserta `rows` en la tabla `forecasts` en lotes de BATCH_SIZE."""
    if dry_run:
        return
    for i in range(0, len(rows), BATCH_SIZE):
        sb.table("forecasts").insert(rows[i : i + BATCH_SIZE]).execute()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main(n_weeks: int = DEFAULT_WEEKS, dry_run: bool = False) -> None:
    tag = " [DRY-RUN]" if dry_run else ""
    print("=" * 60)
    print(f"BACKFILL FORECASTS -- últimas {n_weeks} semanas{tag}")
    print("=" * 60)

    # -- 1. Cargar histórico completo ------------------------------------------
    print("\n[1/4] Cargando histórico desde Supabase...")
    df_full   = data_module.get_historia_semanal()
    last_date = df_full["fecha"].max()
    n_skus    = df_full["sku"].nunique()
    print(f"  -> {n_skus} SKUs, {df_full['fecha'].nunique()} semanas")
    print(f"  -> Rango: {df_full['fecha'].min().date()} -> {last_date.date()}")

    # -- 2. Calcular fechas de cutoff ------------------------------------------
    # Los cutoffs son los últimos N lunes (hacia atrás desde hoy), dentro del
    # rango de datos disponibles.
    today_mon    = _last_monday(pd.Timestamp.now())
    all_cutoffs  = [today_mon - pd.Timedelta(weeks=w) for w in range(n_weeks - 1, -1, -1)]
    cutoff_dates = [d for d in all_cutoffs if d <= last_date]

    if not cutoff_dates:
        print("\n!  No hay cutoffs dentro del rango del histórico. Abortando.")
        return

    print(f"\n[2/4] Cutoffs: {cutoff_dates[0].date()} -> {cutoff_dates[-1].date()}"
          f"  ({len(cutoff_dates)} semanas)")

    # -- 3. Idempotencia: fechas que ya existen --------------------------------
    print("\n[3/4] Verificando fechas existentes en Supabase...")
    sb       = fc_module._sb_client()
    existing = _get_existing_dates(sb, cutoff_dates)

    pending  = [d for d in cutoff_dates if d.strftime("%Y-%m-%d") not in existing]
    n_skip   = len(cutoff_dates) - len(pending)
    print(f"  -> {n_skip} ya existen (salteadas) . {len(pending)} pendientes")

    if not pending:
        print("\nOK Nada que hacer -- todas las fechas ya están en Supabase.")
        return

    # -- 4. Generar e insertar forecasts ---------------------------------------
    print(f"\n[4/4] Generando e insertando{tag}...\n")
    total_rows  = 0
    total_ok    = 0
    errors: list[tuple] = []

    for cutoff in tqdm(pending, desc="Semanas", unit="sem", ncols=70):
        try:
            df_train = df_full[df_full["fecha"] <= cutoff].copy()
            counts   = df_train.groupby("sku")["fecha"].count()
            n_min    = int(counts.min())

            if n_min < 4:
                tqdm.write(f"  !  {cutoff.date()}: SKU con solo {n_min} sem -- saltando")
                continue

            minfo  = fc_module.select_model(n_min)
            fc_df  = fc_module.run_forecast(df_train, minfo)

            if fc_df.empty:
                tqdm.write(f"  !  {cutoff.date()}: forecast vacío -- saltando")
                continue

            rows = _build_rows(fc_df, minfo, cutoff)
            _batch_insert(sb, rows, dry_run=dry_run)

            total_rows += len(rows)
            total_ok   += 1

        except Exception as exc:
            errors.append((cutoff.date(), str(exc)))
            tqdm.write(f"  X  {cutoff.date()}: {exc}")

    # -- Resumen ---------------------------------------------------------------
    print("\n" + "=" * 60)
    action = "simuladas" if dry_run else "insertadas"
    print(f"OK Backfill completo{tag}")
    print(f"  Semanas {action} : {total_ok}")
    print(f"  Filas {action}   : {total_rows}")
    print(f"  Errores         : {len(errors)}")
    if errors:
        for date, msg in errors:
            print(f"    {date}: {msg}")
    print("=" * 60)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Backfill de forecasts históricos en Supabase."
    )
    parser.add_argument(
        "--weeks", type=int, default=DEFAULT_WEEKS,
        help=f"Número de semanas a rellenar (default: {DEFAULT_WEEKS})",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Calcula forecasts pero NO inserta en Supabase.",
    )
    args = parser.parse_args()
    main(n_weeks=args.weeks, dry_run=args.dry_run)
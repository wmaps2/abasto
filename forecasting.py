"""
forecasting.py — Modelo de forecast y métricas de accuracy.

Modelos:
  - AutoETS  : selección automática de error/trend/seasonality (modelo principal)
  - SeasonalNaive : benchmark estacional

Salidas:
  - Forecast: media, std implícita, IC 80 % y 95 % por SKU/semana
  - Accuracy : MAPE y Bias global y por SKU (via cross-validation)
  - Alertas  : semanas donde el real se desvía significativamente del forecast
"""

from __future__ import annotations

import hashlib
import os
import pickle
import time
from datetime import timedelta

os.environ["NIXTLA_ID_AS_COL"] = "1"

import warnings
warnings.filterwarnings("ignore", category=FutureWarning, module="statsforecast")

import numpy as np
import pandas as pd

from dataclasses import dataclass
from typing import Any

from statsforecast import StatsForecast
from statsforecast.models import (
    AutoETS, SeasonalNaive, Holt, Naive, DynamicOptimizedTheta,
)

# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------
SEASON_LENGTH  = 52             # anual en datos semanales
HORIZON        = 12             # semanas a pronosticar
LEVELS         = [70, 95]       # intervalos de confianza
PRIMARY        = "AutoETS"
BENCHMARK      = "SeasonalNaive"

CACHE_DIR      = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cache")
CACHE_MAX_AGE  = timedelta(days=7)
_CACHE_KEYS    = {"forecasts", "cv", "metrics", "fc_hist", "model_info", "computed_at", "ets_params", "cv_skipped"}


# ---------------------------------------------------------------------------
# Selección de modelo según historial disponible
# ---------------------------------------------------------------------------
@dataclass
class ModelInfo:
    name: str           # nombre para mostrar: "AutoETS · s=52"
    primary_col: str    # columna que genera statsforecast antes de renombrar
    benchmark_col: str  # columna del benchmark antes de renombrar
    reason: str         # explicación para la UI
    primary: Any        # instancia del modelo principal
    benchmark: Any      # instancia del benchmark
    min_train: int      # mínimo de semanas para entrenar


def select_model(n_weeks: int) -> ModelInfo:
    """
    Selecciona el modelo apropiado según semanas de historial disponibles.

      4- 8 → DynamicOptimizedTheta  datos muy cortos, robusto con CIs
      9-15 → Holt                   tendencia sin estacionalidad (requiere n≥9)
     16-27 → AutoETS s=4            estacionalidad trimestral corta
     28-51 → AutoETS s=13           estacionalidad trimestral larga
       52+ → AutoETS s=52           estacionalidad anual (comportamiento original)

    Nota: Holt en statsforecast falla con "tiny datasets" para n<9; se usa
    DynamicOptimizedTheta que soporta CIs desde n=4.
    """
    if n_weeks < 9:
        return ModelInfo(
            name        = "Theta",
            primary_col = "DynamicOptimizedTheta",
            benchmark_col = "Naive",
            reason      = f"{n_weeks} sem. · Theta optimizado — robusto para series muy cortas",
            primary     = DynamicOptimizedTheta(),
            benchmark   = Naive(),
            min_train   = 4,
        )
    elif n_weeks < 16:
        return ModelInfo(
            name        = "Holt",
            primary_col = "Holt",
            benchmark_col = "Naive",
            reason      = f"{n_weeks} sem. · Holt — tendencia sin estacionalidad",
            primary     = Holt(),
            benchmark   = Naive(),
            min_train   = 9,
        )
    elif n_weeks < 28:
        return ModelInfo(
            name        = "AutoETS · s=4",
            primary_col = "AutoETS",
            benchmark_col = "SeasonalNaive",
            reason      = f"{n_weeks} sem. · AutoETS con estacionalidad trimestral (s=4)",
            primary     = AutoETS(season_length=4),
            benchmark   = SeasonalNaive(season_length=4),
            min_train   = 16,
        )
    elif n_weeks < 52:
        return ModelInfo(
            name        = "AutoETS · s=13",
            primary_col = "AutoETS",
            benchmark_col = "SeasonalNaive",
            reason      = f"{n_weeks} sem. · AutoETS con estacionalidad trimestral (s=13)",
            primary     = AutoETS(season_length=13),
            benchmark   = SeasonalNaive(season_length=13),
            min_train   = 28,
        )
    else:
        return ModelInfo(
            name        = "AutoETS · s=52",
            primary_col = "AutoETS",
            benchmark_col = "SeasonalNaive",
            reason      = f"{n_weeks} sem. · AutoETS con estacionalidad anual (s=52)",
            primary     = AutoETS(season_length=SEASON_LENGTH),
            benchmark   = SeasonalNaive(season_length=SEASON_LENGTH),
            min_train   = SEASON_LENGTH,
        )


def _normalize_columns(fc: pd.DataFrame, minfo: ModelInfo) -> pd.DataFrame:
    """
    Renombra las columnas del modelo primario y benchmark a los nombres
    canónicos "AutoETS" / "SeasonalNaive" para que todo el código downstream
    funcione sin cambios independientemente del modelo seleccionado.
    """
    rename: dict[str, str] = {}
    for col in fc.columns:
        if col == minfo.primary_col:
            rename[col] = PRIMARY
        elif col.startswith(f"{minfo.primary_col}-"):
            rename[col] = PRIMARY + col[len(minfo.primary_col):]
        elif col == minfo.benchmark_col:
            rename[col] = BENCHMARK
        elif col.startswith(f"{minfo.benchmark_col}-"):
            rename[col] = BENCHMARK + col[len(minfo.benchmark_col):]
    return fc.rename(columns=rename) if rename else fc


# ---------------------------------------------------------------------------
# Caché en disco
# ---------------------------------------------------------------------------
def _df_hash(df: pd.DataFrame) -> str:
    return hashlib.md5(pd.util.hash_pandas_object(df, index=True).values).hexdigest()


def _cache_file(df_hash: str) -> str:
    return os.path.join(CACHE_DIR, f"{df_hash}.pkl")


def _read_cache(df_hash: str) -> dict | None:
    path = _cache_file(df_hash)
    if not os.path.exists(path):
        return None
    try:
        with open(path, "rb") as f:
            cached = pickle.load(f)
    except Exception:
        return None
    if not _CACHE_KEYS.issubset(cached.keys()):
        return None  # formato obsoleto, ignorar
    age = pd.Timestamp.now() - cached["computed_at"]
    if age > CACHE_MAX_AGE:
        return None
    return cached


def _write_cache(df_hash: str, results: dict) -> None:
    os.makedirs(CACHE_DIR, exist_ok=True)
    with open(_cache_file(df_hash), "wb") as f:
        pickle.dump(results, f)


def cache_status(df: pd.DataFrame) -> dict | None:
    """Retorna el caché válido si existe y no expiró (<7 días), sino None."""
    return _read_cache(_df_hash(df))


def get_ets_model_params(df: pd.DataFrame, minfo: ModelInfo) -> dict[str, str]:
    """
    Ajusta AutoETS sobre el histórico completo y extrae el string ETS seleccionado
    para cada SKU (p.ej. "AAA" = Additive Error, Additive Trend, Additive Season).

    Formato del string: <Error><Trend><Season>
      A = Additive  ·  M = Multiplicative  ·  N = None  ·  Ad = Additive damped
    """
    if minfo.name not in ("AutoETS · s=52", "AutoETS · s=13", "AutoETS · s=4"):
        # Modelo no es AutoETS — no hay parámetros ETS que extraer
        return {}

    sf_df = _to_sf(df)
    sf    = StatsForecast(models=[minfo.primary], freq="W-MON", n_jobs=1)

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        sf.fit(df=sf_df)

    unique_ids = sf_df["unique_id"].unique().tolist()
    params: dict[str, str] = {}
    for i, uid in enumerate(unique_ids):
        try:
            fitted    = sf.fitted_[i][0]
            model_raw = getattr(fitted, "model_", None)
            if isinstance(model_raw, dict):
                # statsforecast stores "ETS(A,Ad,N)" style string under "method"
                ets_str = model_raw.get("method", "?")
            else:
                ets_str = "?"
            params[uid] = ets_str
        except Exception:
            params[uid] = "?"
    return params


def get_or_compute(df: pd.DataFrame, force: bool = False) -> tuple[dict, bool]:
    """
    Retorna (results_dict, from_cache).
    Si force=True ignora el caché y recalcula siempre.
    results_dict incluye: forecasts, cv, metrics, fc_hist, computed_at, cv_skipped.

    Series con ≥4 datos siempre reciben forecast; sólo las que tienen suficientes
    datos para la CV (≥ HORIZON*2 + min_train) participan en las métricas.
    """
    h = _df_hash(df)

    if not force:
        cached = _read_cache(h)
        if cached is not None:
            return cached, True

    sf_df  = _to_sf(df)
    counts = sf_df.groupby("unique_id")["ds"].count()
    n_min  = int(counts.min())

    if n_min < 4:
        raise ValueError(
            f"Datos insuficientes: el SKU con menos historial tiene {n_min} semanas "
            f"(mínimo 4 requeridas)."
        )

    t0 = time.time()
    n_skus = int(sf_df["unique_id"].nunique())
    print(f"[forecast] INICIO cálculo — {n_skus} SKUs · modelo mínimo: {select_model(n_min).name}", flush=True)

    # Modelo global basado en la longitud mínima de las series
    minfo      = select_model(n_min)

    t1 = time.time()
    forecasts  = run_forecast(df, minfo)
    cv, cv_skipped = run_cross_validation(df, minfo, counts=counts)
    metrics    = compute_metrics(cv) if not cv.empty else {}
    ets_params = get_ets_model_params(df, minfo)
    print(f"[forecast] Forecast actual   {time.time() - t1:.1f}s", flush=True)

    t2 = time.time()
    fc_hist    = generate_forecast_history(df, minfo)
    print(f"[forecast] Historial retro   {time.time() - t2:.1f}s", flush=True)

    print(f"[forecast] TOTAL             {time.time() - t0:.1f}s", flush=True)

    results = dict(
        forecasts   = forecasts,
        cv          = cv,
        metrics     = metrics,
        fc_hist     = fc_hist,
        model_info  = minfo,
        ets_params  = ets_params,
        cv_skipped  = cv_skipped,
        computed_at = pd.Timestamp.now(),
    )
    _write_cache(h, results)
    return results, False


# ---------------------------------------------------------------------------
# Helpers internos
# ---------------------------------------------------------------------------
def _to_sf(df: pd.DataFrame) -> pd.DataFrame:
    """Convierte el DataFrame del app al formato de statsforecast."""
    out = (df
           .rename(columns={"sku": "unique_id", "fecha": "ds", "cantidad": "y"})
           .assign(ds=lambda x: pd.to_datetime(x["ds"]),
                   y =lambda x: x["y"].clip(lower=0))
           [["unique_id", "ds", "y"]]
           .sort_values(["unique_id", "ds"]))
    return out


def _make_sf(minfo: ModelInfo) -> StatsForecast:
    return StatsForecast(
        models=[minfo.primary, minfo.benchmark],
        freq="W-MON",
        n_jobs=1,
    )


def _implied_std(fc_df: pd.DataFrame, model: str) -> pd.Series:
    """Std normal implícita a partir del IC 95 %."""
    lo = f"{model}-lo-95"
    hi = f"{model}-hi-95"
    if lo in fc_df.columns and hi in fc_df.columns:
        return (fc_df[hi] - fc_df[lo]) / (2 * 1.96)
    return pd.Series(np.nan, index=fc_df.index)


# ---------------------------------------------------------------------------
# API pública
# ---------------------------------------------------------------------------
def run_forecast(df: pd.DataFrame, minfo: ModelInfo | None = None) -> pd.DataFrame:
    """
    Entrena sobre todo el histórico y produce el forecast para las próximas
    HORIZON semanas. Columnas de salida siempre normalizadas a "AutoETS" / "SeasonalNaive".

    Las series demasiado cortas para el modelo global se forecástean con el modelo
    más adecuado para su longitud (mínimo 4 semanas).
    """
    sf_df  = _to_sf(df)
    counts = sf_df.groupby("unique_id")["ds"].count()

    if minfo is None:
        minfo = select_model(int(counts.min()))

    # Separar series según si tienen suficientes datos para el modelo global
    eligible = counts[counts >= minfo.min_train].index.tolist()
    short    = counts[(counts >= 4) & (counts < minfo.min_train)].index.tolist()

    parts: list[pd.DataFrame] = []

    if eligible:
        fc = _make_sf(minfo).forecast(
            df=sf_df[sf_df["unique_id"].isin(eligible)],
            h=HORIZON, level=LEVELS,
        ).reset_index()
        parts.append(_normalize_columns(fc, minfo))

    if short:
        # Usar el modelo apropiado para la serie más corta del grupo
        minfo_s = select_model(int(counts[short].min()))
        sf_s    = StatsForecast(models=[minfo_s.primary], freq="W-MON", n_jobs=1)
        fc_s    = sf_s.forecast(
            df=sf_df[sf_df["unique_id"].isin(short)],
            h=HORIZON, level=LEVELS,
        ).reset_index()
        fc_s = _normalize_columns(fc_s, minfo_s)
        parts.append(fc_s)

    if not parts:
        return pd.DataFrame()

    # Alinear columnas antes de concatenar (rellenar con NaN las que falten)
    all_cols = list(dict.fromkeys(c for p in parts for c in p.columns))
    parts = [p.reindex(columns=all_cols) for p in parts]
    fc_all = pd.concat(parts, ignore_index=True)

    for model in [PRIMARY, BENCHMARK]:
        if model in fc_all.columns:
            fc_all[f"{model}-std"] = _implied_std(fc_all, model)

    return fc_all


def run_cross_validation(
    df: pd.DataFrame,
    minfo: ModelInfo | None = None,
    counts: "pd.Series | None" = None,
) -> tuple[pd.DataFrame, list[str]]:
    """
    Validación cruzada con ventanas deslizantes para estimar accuracy en muestra.
    Columnas normalizadas a "AutoETS" / "SeasonalNaive".

    Retorna (cv_df, skipped_ids) donde skipped_ids son las series excluidas por
    tener demasiados pocos datos para la CV (siguen recibiendo forecast normal).
    """
    sf_df = _to_sf(df)
    if counts is None:
        counts = sf_df.groupby("unique_id")["ds"].count()

    if minfo is None:
        minfo = select_model(int(counts.min()))

    # Mínimo de datos para 1 ventana de CV: step_size + h + min_train
    min_cv_n = HORIZON + HORIZON + minfo.min_train
    eligible  = counts[counts >= min_cv_n].index.tolist()
    skipped   = counts[counts < min_cv_n].index.tolist()

    if not eligible:
        return pd.DataFrame(), skipped

    sf_eligible = sf_df[sf_df["unique_id"].isin(eligible)]
    n_cv_min    = int(counts[eligible].min())
    n_win       = 2 if n_cv_min >= 80 else 1

    cv = _make_sf(minfo).cross_validation(
        df=sf_eligible,
        h=HORIZON,
        step_size=HORIZON,
        n_windows=n_win,
        level=LEVELS,
    ).reset_index()

    return _normalize_columns(cv, minfo), skipped


def _add_horizon_col(cv: pd.DataFrame) -> pd.DataFrame:
    """Add 'h' column: forecast step from cutoff (1 = first week ahead)."""
    cv = cv.copy()
    cv["h"] = ((cv["ds"] - cv["cutoff"]).dt.days // 7).astype(int)
    return cv


def compute_metrics_for_horizon(cv: pd.DataFrame, h_max: int) -> dict[str, dict]:
    """Like compute_metrics but restricted to forecast steps 1..h_max."""
    cv_h = _add_horizon_col(cv)
    cv_h = cv_h[cv_h["h"] <= h_max]
    return compute_metrics(cv_h)


def compute_mape_by_step(cv: pd.DataFrame) -> pd.DataFrame:
    """
    MAPE medio por paso de horizonte (h=1..HORIZON) para cada modelo.
    Retorna DataFrame con columnas: h (int), model (str), mape (float).
    Útil para graficar cómo crece el error con el horizonte.
    """
    cv_h = _add_horizon_col(cv)
    rows = []
    for h_val in sorted(cv_h["h"].unique()):
        sub = cv_h[cv_h["h"] == h_val]
        for model in [PRIMARY, BENCHMARK]:
            if model not in sub.columns:
                continue
            s = sub[sub["y"] > 0]
            if s.empty:
                continue
            mape = float((np.abs(s["y"] - s[model]) / s["y"]).mean() * 100)
            rows.append({"h": int(h_val), "model": model, "mape": round(mape, 2)})
    return pd.DataFrame(rows)


def compute_metrics(cv: pd.DataFrame) -> dict[str, dict]:
    """
    MAPE y Bias global y por SKU para cada modelo.

    Retorna dict: {model_name: {global_mape, global_bias, per_sku DataFrame}}
    """
    results: dict[str, dict] = {}

    for model in [PRIMARY, BENCHMARK]:
        if model not in cv.columns:
            continue

        sub = cv[["unique_id", "ds", "y", model]].copy()
        sub = sub[sub["y"] > 0]  # excluir ceros del MAPE

        sub["ape"] = np.abs(sub["y"] - sub[model]) / sub["y"]
        sub["pe"]  = (sub[model] - sub["y"]) / sub["y"]

        global_mape = sub["ape"].mean() * 100
        global_bias = sub["pe"].mean() * 100

        per_sku = (
            sub.groupby("unique_id")
               .agg(MAPE=("ape", "mean"), Bias=("pe", "mean"))
               .mul(100)
               .round(2)
               .rename_axis("SKU")
        )

        results[model] = dict(
            global_mape=round(global_mape, 2),
            global_bias=round(global_bias, 2),
            per_sku=per_sku,
        )

    return results


def detect_alerts(
    cv: pd.DataFrame,
    threshold_pct: float = 0.30,
    z_threshold: float = 2.0,
) -> pd.DataFrame:
    """
    Detecta semanas donde el real se desvió significativamente del forecast
    en la ventana de CV más reciente.

    Criterio de alerta (OR):
      · Desviación porcentual absoluta > threshold_pct  (default 30 %)
      · |z-score| > z_threshold respecto a la std implícita del IC 95 %

    Retorna DataFrame con columnas listas para mostrar en UI.
    """
    if PRIMARY not in cv.columns or cv.empty:
        return pd.DataFrame()

    latest  = cv[cv["cutoff"] == cv["cutoff"].max()].copy()
    safe    = latest[PRIMARY].replace(0, np.nan)

    latest["dev_pct"]  = (latest["y"] - latest[PRIMARY]) / safe
    latest["abs_dev"]  = latest["dev_pct"].abs()

    lo_col = f"{PRIMARY}-lo-95"
    hi_col = f"{PRIMARY}-hi-95"
    if lo_col in latest.columns and hi_col in latest.columns:
        std_implied   = (latest[hi_col] - latest[lo_col]) / (2 * 1.96)
        latest["z"]   = (latest["y"] - latest[PRIMARY]) / std_implied.replace(0, np.nan)
        mask = (latest["abs_dev"] > threshold_pct) | (latest["z"].abs() > z_threshold)
    else:
        latest["z"] = np.nan
        mask = latest["abs_dev"] > threshold_pct

    alerts = latest[mask].copy()
    if alerts.empty:
        return pd.DataFrame()

    alerts["Dirección"] = np.where(
        alerts["dev_pct"] > 0, "↑ Sobre forecast", "↓ Bajo forecast"
    )
    alerts["Severidad"] = np.where(
        alerts["abs_dev"] > 0.50, "Crítica", "Advertencia"
    )

    return (
        alerts[[
            "unique_id", "ds", "y", PRIMARY, "dev_pct", "z", "Dirección", "Severidad"
        ]]
        .rename(columns={
            "unique_id": "SKU",
            "ds":        "Semana",
            "y":         "Real",
            PRIMARY:     "Forecast",
            "dev_pct":   "Desv. %",
            "z":         "Z-score",
        })
        .assign(**{"Desv. %": lambda x: (x["Desv. %"] * 100).round(1)})
        .sort_values("Desv. %", key=abs, ascending=False)
        .reset_index(drop=True)
    )


def run_sandbox_forecast(
    edited: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, float | None, float | None, ModelInfo]:
    """
    Forecast para el Sandbox. Acepta DataFrame con columnas (fecha, cantidad).
    Aplica select_model() automáticamente según semanas disponibles (mínimo 4).
    Retorna (hist_df, fc_df, mape, bias, model_info).
    mape/bias son None si hay menos de 16 semanas con datos.
    """
    valid = (edited[edited["cantidad"].notna()]
             .sort_values("fecha")
             .reset_index(drop=True))
    n = len(valid)
    if n < 4:
        dummy = ModelInfo("—", "AutoETS", "SeasonalNaive", "datos insuficientes",
                          None, None, 4)
        return pd.DataFrame(), pd.DataFrame(), None, None, dummy

    minfo   = select_model(n)
    hist_df = valid[["fecha", "cantidad"]].copy()

    sf_df = (valid[["fecha", "cantidad"]]
             .rename(columns={"fecha": "ds", "cantidad": "y"})
             .assign(unique_id="SANDBOX"))

    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)
            fc = StatsForecast(
                models=[minfo.primary],
                freq="W-MON",
                n_jobs=1,
            ).forecast(df=sf_df, h=HORIZON, level=LEVELS).reset_index()
    except NotImplementedError as exc:
        raise ValueError(
            f"El modelo {minfo.name} no puede entrenar con solo {n} semanas de datos "
            f"(mínimo {minfo.min_train}). Ingresa más datos o revisa los valores."
        ) from exc
    except Exception as exc:
        raise ValueError(f"Error al calcular el forecast: {exc}") from exc

    fc = _normalize_columns(fc, minfo)
    fc[f"{PRIMARY}-std"] = _implied_std(fc, PRIMARY)

    mape, bias = None, None
    if n >= 16:
        holdout  = 4
        train_sf = sf_df.iloc[:-holdout].copy()
        actual   = sf_df.iloc[-holdout:].copy()
        try:
            fc2 = StatsForecast(
                models=[minfo.primary],
                freq="W-MON",
                n_jobs=1,
            ).forecast(df=train_sf, h=holdout).reset_index()
            fc2 = _normalize_columns(fc2, minfo)
            merged = actual.merge(fc2[["unique_id", "ds", PRIMARY]], on=["unique_id", "ds"])
            pos = merged[merged["y"] > 0]
            if not pos.empty:
                mape = float((np.abs(pos["y"] - pos[PRIMARY]) / pos["y"]).mean() * 100)
                bias = float(((pos[PRIMARY] - pos["y"]) / pos["y"]).mean() * 100)
        except Exception:
            pass

    return hist_df, fc, mape, bias, minfo


def generate_forecast_history(
    df: pd.DataFrame, minfo: ModelInfo | None = None, n_weeks: int = 8
) -> pd.DataFrame:
    """
    Simula que el modelo lleva n_weeks semanas funcionando.
    Para cada cutoff entrena hasta ese punto y genera un forecast de HORIZON semanas.
    Usa el mismo minfo que el forecast principal para consistencia.
    """
    sf_df     = _to_sf(df)
    last_date = sf_df["ds"].max()

    if minfo is None:
        n = int(sf_df.groupby("unique_id")["ds"].count().min())
        minfo = select_model(n)

    results = []
    for weeks_back in range(n_weeks, 0, -1):
        run_date = last_date - pd.Timedelta(weeks=weeks_back)
        train    = sf_df[sf_df["ds"] <= run_date]

        if train.groupby("unique_id")["ds"].count().min() < minfo.min_train:
            continue

        fc = _make_sf(minfo).forecast(df=train, h=HORIZON, level=LEVELS).reset_index()
        fc = _normalize_columns(fc, minfo)
        fc["run_date"] = run_date
        results.append(fc)

    return pd.concat(results, ignore_index=True) if results else pd.DataFrame()

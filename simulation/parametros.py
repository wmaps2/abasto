# Parámetros de configuración del simulador de demanda.
# Configuración de laboratorio — no van a la base de datos.

# ---------------------------------------------------------------------------
# Globales
# ---------------------------------------------------------------------------
RANDOM_SEED = 42
N_SEMANAS   = 156      # ~3 años, garantiza ≥3 ciclos completos para AutoETS (s=52)
FREQ        = "W-MON"

# Offsets de pico por patrón (semana del año, 1-52)
SEASONAL_OFFSETS: dict[str, dict | None] = {
    "christmas": {"pico": 50, "periodo": 52},   # pico dic, valle jun
    "summer":    {"pico": 26, "periodo": 52},   # pico jul, valle dic
    "biannual":  {"pico": 13, "periodo": 26},   # picos mar y sep
    "none":      None,
}

# ---------------------------------------------------------------------------
# Por SKU
# ---------------------------------------------------------------------------
# base       → demanda media semanal (u/sem) en semana 0
# trend      → incremento lineal por semana (u/sem²)
# pattern    → perfil estacional (ver SEASONAL_OFFSETS)
# amp        → amplitud del componente estacional (unidades)
# noise      → desviación estándar del ruido gaussiano
# cv_demanda → coeficiente de variación (σ/μ), usado en cálculo de safety stock

SKU_CONFIGS: dict[str, dict] = {
    # ── Categoría A: Abarrotes / No perecibles ─────────────────────────────
    "SKU-A001": {"base": 280, "trend": 1.0,  "pattern": "summer",    "amp": 28, "noise": 35, "cv_demanda": 0.139},
    "SKU-A002": {"base": 350, "trend": 1.5,  "pattern": "biannual",  "amp": 35, "noise": 45, "cv_demanda": 0.213},
    "SKU-A003": {"base": 220, "trend": 0.5,  "pattern": "christmas", "amp": 22, "noise": 28, "cv_demanda": 0.138},
    "SKU-A004": {"base": 400, "trend": 2.0,  "pattern": "summer",    "amp": 40, "noise": 50, "cv_demanda": 0.228},
    "SKU-A005": {"base": 310, "trend": 0.8,  "pattern": "none",      "amp":  0, "noise": 40, "cv_demanda": 0.126},
    # ── Categoría B: Moda / Temporada ──────────────────────────────────────
    "SKU-B001": {"base":  60, "trend": 0.2,  "pattern": "biannual",  "amp": 30, "noise": 22, "cv_demanda": 0.485},
    "SKU-B002": {"base":  45, "trend": 0.1,  "pattern": "biannual",  "amp": 22, "noise": 18, "cv_demanda": 0.676},
    "SKU-B003": {"base":  75, "trend": 0.3,  "pattern": "biannual",  "amp": 38, "noise": 28, "cv_demanda": 0.530},
    "SKU-B004": {"base":  35, "trend": 0.0,  "pattern": "biannual",  "amp": 17, "noise": 14, "cv_demanda": 0.526},
    # ── Categoría C: Durables / Especialidad ───────────────────────────────
    "SKU-C001": {"base":  12, "trend": 0.05, "pattern": "christmas", "amp":  5, "noise":  2, "cv_demanda": 0.202},
    "SKU-C002": {"base":  18, "trend": 0.08, "pattern": "christmas", "amp":  8, "noise":  3, "cv_demanda": 0.108},
    "SKU-C003": {"base":   8, "trend": 0.03, "pattern": "christmas", "amp":  3, "noise":  2, "cv_demanda": 0.146},
}

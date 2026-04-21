"""
pages/compra.py — Abasto: COMPRA — Phase 2
Revisión periódica semanal con nivel de servicio endógeno.
Aplica overrides manuales del módulo de Forecast cuando existen.
"""
from __future__ import annotations

import hashlib
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

sys.path.insert(0, str(Path(__file__).parent.parent))
import data as data_module
import forecasting as fc_module
import overrides as overrides_module

# ─── Page config (injected once by app.py router) ─────────────────────────────

# ─── Design tokens ────────────────────────────────────────────────────────────
C = dict(
    bg_deep    = "#0b0d14",
    bg_base    = "#0f1117",
    bg_surface = "#161927",
    bg_card    = "#1c1f31",
    border     = "#252840",
    text_1     = "#e2e8f0",
    text_2     = "#8892a8",
    text_3     = "#4a5568",
    blue       = "#4f8ff7",
    blue_dim   = "rgba(79,143,247,0.12)",
    green      = "#00c49a",
    green_dim  = "rgba(0,196,154,0.12)",
    red        = "#f05a6b",
    red_dim    = "rgba(240,90,107,0.12)",
    yellow     = "#f5c542",
    yellow_dim = "rgba(245,197,66,0.12)",
    mono       = "'Courier New','Consolas',monospace",
)

# ─── Global CSS ───────────────────────────────────────────────────────────────
st.markdown(f"""
<style>
html, body, [class*="css"] {{
    font-family: 'Inter','Segoe UI',system-ui,sans-serif;
}}
.stApp {{
    background-color: {C['bg_base']};
    color: {C['text_1']};
}}
.block-container {{
    padding-top: 1.5rem !important;
    padding-bottom: 2rem !important;
    max-width: 1400px;
}}
section[data-testid="stSidebar"] {{
    background-color: {C['bg_deep']} !important;
    border-right: 1px solid {C['border']} !important;
}}
section[data-testid="stSidebar"] .stMarkdown p,
section[data-testid="stSidebar"] .stMarkdown li {{
    color: {C['text_2']};
    font-size: 12px;
    line-height: 1.6;
}}
section[data-testid="stSidebar"] label {{
    color: {C['text_1']} !important;
    font-size: 12px !important;
}}
section[data-testid="stSidebar"] h1,
section[data-testid="stSidebar"] h2,
section[data-testid="stSidebar"] h3 {{
    color: {C['text_1']} !important;
}}
.stTabs [data-baseweb="tab-list"] {{
    background-color: {C['bg_surface']};
    border-bottom: 1px solid {C['border']};
    gap: 0; padding: 0;
}}
.stTabs [data-baseweb="tab"] {{
    color: {C['text_2']} !important;
    background-color: transparent !important;
    border-radius: 0 !important;
    padding: 10px 22px !important;
    font-size: 11px; font-weight: 600;
    letter-spacing: 0.08em; text-transform: uppercase;
    border-bottom: 2px solid transparent !important;
    margin-bottom: -1px;
}}
.stTabs [aria-selected="true"] {{
    color: {C['blue']} !important;
    border-bottom-color: {C['blue']} !important;
    background-color: transparent !important;
}}
.stTabs [data-baseweb="tab-panel"] {{
    background-color: {C['bg_base']};
    padding-top: 24px;
}}
.stSelectbox [data-baseweb="select"] > div {{
    background-color: {C['bg_card']} !important;
    border: 1px solid {C['border']} !important;
    border-radius: 6px !important;
}}
.stSelectbox [data-baseweb="select"] svg {{ fill: {C['text_2']}; }}
.stRadio [data-testid="stMarkdownContainer"] p {{
    color: {C['text_1']} !important;
    font-size: 13px !important;
}}
div[role="radiogroup"] > label {{
    background: {C['bg_card']};
    border: 1px solid {C['border']};
    border-radius: 6px;
    padding: 6px 14px;
    cursor: pointer;
    transition: border-color 0.15s;
}}
div[role="radiogroup"] > label:has(input:checked) {{
    border-color: {C['blue']};
    background: {C['blue_dim']};
}}
.stButton > button {{
    background-color: {C['blue']} !important;
    color: white !important;
    border: none !important;
    border-radius: 6px !important;
    font-weight: 700 !important;
    letter-spacing: 0.08em !important;
    text-transform: uppercase !important;
    font-size: 11px !important;
    padding: 10px 0 !important;
    transition: opacity 0.15s !important;
    font-family: {C['mono']} !important;
}}
.stButton > button:hover {{ opacity: 0.85 !important; }}
.stSpinner > div > div {{ border-top-color: {C['blue']} !important; }}
[data-testid="stNotification"] {{ border-radius: 6px !important; font-size: 12px !important; }}
.stDataFrame {{ border: 1px solid {C['border']} !important; border-radius: 6px !important; overflow: hidden; }}
hr {{ border-color: {C['border']} !important; margin: 20px 0 !important; }}

.sc-header {{
    display: flex; align-items: center; justify-content: space-between;
    padding: 4px 0 20px 0;
    border-bottom: 1px solid {C['border']};
    margin-bottom: 28px;
}}
.sc-brand {{ display: flex; align-items: baseline; gap: 10px; }}
.sc-icon {{ font-size: 24px; color: {C['blue']}; line-height: 1; }}
.sc-name {{ font-size: 22px; font-weight: 900; letter-spacing: 0.1em; color: {C['text_1']}; }}
.sc-tagline {{ font-size: 10px; letter-spacing: 0.1em; text-transform: uppercase; color: {C['text_2']}; }}
.sc-badges {{ display: flex; gap: 8px; align-items: center; flex-wrap: wrap; justify-content: flex-end; }}
.badge {{
    font-size: 10px; letter-spacing: 0.08em; text-transform: uppercase;
    padding: 4px 10px; border-radius: 4px; font-weight: 700;
    font-family: {C['mono']};
}}
.badge-green  {{ background:{C['green_dim']};  color:{C['green']};  border:1px solid {C['green']};  }}
.badge-blue   {{ background:{C['blue_dim']};   color:{C['blue']};   border:1px solid {C['blue']};   }}
.badge-yellow {{ background:{C['yellow_dim']}; color:{C['yellow']}; border:1px solid {C['yellow']}; }}
.badge-red    {{ background:{C['red_dim']};    color:{C['red']};    border:1px solid {C['red']};    }}
.badge-neutral{{ background:{C['bg_card']};    color:{C['text_2']}; border:1px solid {C['border']}; }}

.section-hdr {{
    font-size: 10px; letter-spacing: 0.14em; text-transform: uppercase;
    color: {C['text_2']}; font-weight: 700;
    padding-bottom: 10px; border-bottom: 1px solid {C['border']};
    margin-bottom: 18px; margin-top: 8px;
}}
.kpi-row {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
    gap: 12px;
    margin: 4px 0 24px 0;
}}
.kpi {{
    background: {C['bg_card']};
    border: 1px solid {C['border']};
    border-radius: 8px;
    padding: 16px 18px;
}}
.kpi-label {{
    font-size: 10px; letter-spacing: 0.12em; text-transform: uppercase;
    color: {C['text_2']}; margin-bottom: 8px; font-weight: 600;
}}
.kpi-value {{
    font-size: 28px; font-weight: 700; color: {C['text_1']};
    font-family: {C['mono']}; line-height: 1.1; letter-spacing: -0.02em;
}}
.kpi-delta {{
    font-size: 11px; font-family: {C['mono']}; margin-top: 6px; letter-spacing: 0.02em;
}}
.kpi-delta.pos {{ color: {C['green']}; }}
.kpi-delta.neg {{ color: {C['red']}; }}
.kpi-delta.neu {{ color: {C['text_2']}; }}

.rep-table {{
    width: 100%; border-collapse: collapse;
    font-size: 12px; font-family: {C['mono']};
    background: {C['bg_card']}; border-radius: 8px; overflow: hidden;
    border: 1px solid {C['border']};
}}
.rep-table thead tr {{ border-bottom: 1px solid {C['border']}; }}
.rep-table th {{
    font-size: 10px; letter-spacing: 0.08em; text-transform: uppercase;
    color: {C['text_2']}; padding: 10px 14px; text-align: right;
    font-family: 'Inter',sans-serif; font-weight: 700; background: {C['bg_surface']};
    white-space: nowrap;
}}
.rep-table th:first-child {{ text-align: left; }}
.rep-table td {{
    padding: 9px 14px; text-align: right;
    border-bottom: 1px solid rgba(37,40,64,0.6); color: {C['text_1']};
    white-space: nowrap;
}}
.rep-table td:first-child {{ text-align: left; }}
.rep-table tr:last-child td {{ border-bottom: none; }}
.rep-table tr:hover td {{ background: {C['bg_surface']}; cursor: pointer; }}
.rep-table .order-urgent {{ color: {C['red']}; font-weight: 700; }}
.rep-table .order-normal {{ color: {C['yellow']}; font-weight: 700; }}
.rep-table .order-none   {{ color: {C['text_3']}; }}
.rep-table .sku-cell     {{ color: {C['blue']}; font-weight: 700; }}

.info-box {{
    background: {C['blue_dim']}; border: 1px solid {C['blue']};
    border-radius: 6px; padding: 12px 16px;
    font-size: 12px; color: {C['text_2']}; line-height: 1.6;
}}
.ok-box {{
    background: {C['green_dim']}; border: 1px solid {C['green']};
    border-radius: 6px; padding: 12px 16px;
    font-size: 12px; color: {C['green']}; font-family: {C['mono']};
    font-weight: 700; letter-spacing: 0.04em;
}}
.warn-box {{
    background: {C['yellow_dim']}; border: 1px solid {C['yellow']};
    border-radius: 6px; padding: 12px 16px;
    font-size: 12px; color: {C['yellow']}; font-family: {C['mono']};
    font-weight: 700; letter-spacing: 0.04em;
}}
.danger-box {{
    background: {C['red_dim']}; border: 1px solid {C['red']};
    border-radius: 6px; padding: 12px 16px;
    font-size: 12px; color: {C['red']}; font-family: {C['mono']};
    font-weight: 700; letter-spacing: 0.04em;
}}
.model-card {{
    background: {C['bg_card']}; border: 1px solid {C['border']};
    border-radius: 6px; padding: 12px 14px; margin-top: 4px;
}}
.mc-row {{
    display: flex; justify-content: space-between;
    font-size: 11px; padding: 3px 0;
    color: {C['text_3']}; font-family: {C['mono']};
    border-bottom: 1px solid rgba(37,40,64,0.4);
}}
.mc-row:last-child {{ border-bottom: none; }}
.mc-row span {{ color: {C['text_1']}; }}
</style>
""", unsafe_allow_html=True)

# ─── Plotly dark base ─────────────────────────────────────────────────────────
_PBG  = C["bg_card"]
_GRID = "rgba(255,255,255,0.04)"
_HOVER = dict(
    bgcolor=C["bg_card"],
    bordercolor=C["border"],
    font=dict(color=C["text_1"], family="Courier New,monospace", size=11),
)


def _dark_layout(fig: go.Figure, title: str = "", height: int = 420) -> go.Figure:
    fig.update_layout(
        template="plotly_dark",
        title=dict(
            text=title,
            font=dict(size=13, color=C["text_1"], family="Inter,sans-serif"),
            x=0, pad=dict(l=0),
        ),
        paper_bgcolor=_PBG,
        plot_bgcolor=_PBG,
        font=dict(color=C["text_2"], family="Inter,sans-serif", size=11),
        hoverlabel=_HOVER,
        hovermode="x unified",
        height=height,
        margin=dict(l=0, r=0, t=42, b=0),
        legend=dict(
            orientation="h", yanchor="bottom", y=1.01, xanchor="right", x=1,
            font=dict(size=10, color=C["text_2"]),
            bgcolor="rgba(0,0,0,0)", borderwidth=0,
        ),
        xaxis=dict(
            showgrid=True, gridcolor=_GRID, gridwidth=1,
            showline=False, zeroline=False,
            tickfont=dict(family="Courier New,monospace", size=10, color=C["text_2"]),
        ),
        yaxis=dict(
            showgrid=True, gridcolor=_GRID, gridwidth=1,
            showline=False, zeroline=False, rangemode="tozero",
            tickfont=dict(family="Courier New,monospace", size=10, color=C["text_2"]),
        ),
    )
    return fig


# ─── Z-score approximation (no scipy dependency) ─────────────────────────────
def _normal_ppf(p: float) -> float:
    """Rational approximation of the standard normal quantile (Abramowitz & Stegun 26.2.17)."""
    p = min(max(p, 1e-9), 1 - 1e-9)
    if p < 0.5:
        t = math.sqrt(-2.0 * math.log(p))
        sign = -1.0
    else:
        t = math.sqrt(-2.0 * math.log(1.0 - p))
        sign = 1.0
    c0, c1, c2 = 2.515517, 0.802853, 0.010328
    d1, d2, d3 = 1.432788, 0.189269, 0.001308
    num = c0 + c1 * t + c2 * t * t
    den = 1.0 + d1 * t + d2 * t * t + d3 * t * t * t
    return sign * (t - num / den)


# ─── Data loading ─────────────────────────────────────────────────────────────
_DATA_DIR = Path(__file__).parent.parent / "data"


@st.cache_data(ttl=120, show_spinner=False)
def _load_productos() -> pd.DataFrame:
    return data_module.get_productos()


@st.cache_data(ttl=120, show_spinner=False)
def _load_stock() -> pd.DataFrame:
    return data_module.get_inventario()


def _get_override_hash() -> str:
    """Hash de los overrides activos en Supabase para invalidar caché cuando cambian."""
    try:
        ovr = overrides_module.load()
        payload = str(sorted(str(ovr).split())).encode()
        return hashlib.md5(payload).hexdigest()
    except Exception:
        return ""


@st.cache_data(show_spinner=False)
def _load_forecast(override_hash: str = "", fuente: str = "demo") -> dict | None:
    df_sim = data_module.get_historia_semanal(fuentes=[fuente])
    try:
        results, _ = fc_module.get_or_compute(df_sim)
    except Exception:
        return None
    # Keep original model forecast for σ calculation, apply overrides for µ
    results = dict(results)
    results["forecasts_original"] = results["forecasts"]  # untouched model values
    ovr = overrides_module.load()
    if ovr:
        results["forecasts"]   = overrides_module.apply(results["forecasts"].copy(), ovr)
        results["override_skus"] = set(ovr.keys())
    else:
        results["override_skus"] = set()
    return results


# ─── Replenishment engine ─────────────────────────────────────────────────────
def compute_replenishment(
    productos: pd.DataFrame,
    stock: pd.DataFrame,
    forecast_results: dict | None,
) -> pd.DataFrame:
    rows = []

    fc_by_sku: dict[str, pd.DataFrame] = {}
    demand_avg: dict[str, float] = {}       # effective µ (override applied)
    demand_avg_model: dict[str, float] = {} # model µ (for σ, unchanged by override)
    override_skus: set = set()

    if forecast_results is not None:
        override_skus = forecast_results.get("override_skus", set())

        # Effective forecast (with overrides) → µ for ROP
        fc_df = forecast_results["forecasts"].copy()
        for sku, grp in fc_df.groupby("unique_id"):
            grp = grp.sort_values("ds").reset_index(drop=True)
            fc_by_sku[sku] = grp
            demand_avg[sku] = float(grp["AutoETS"].mean())

        # Original model forecast → µ for σ (variability unchanged by override)
        fc_orig = forecast_results.get("forecasts_original", fc_df)
        for sku, grp in fc_orig.groupby("unique_id"):
            grp = grp.sort_values("ds").reset_index(drop=True)
            demand_avg_model[sku] = float(grp["AutoETS"].mean())

    for _, prod in productos.iterrows():
        sku = prod["sku"]
        precio    = float(prod["precio_venta"])
        costo     = float(prod["costo"])
        margen    = float(prod["margen"])
        costo_rep = float(prod["costo_reputacional"])
        lt        = int(prod["lead_time_semanas"])
        cv        = float(prod["cv_demanda"])
        tasa_obs  = float(prod["tasa_obsolescencia_semanal"])
        cat = str(prod.get("categoria", "A"))[:1].upper() or "A"

        st_row = stock[stock["sku"] == sku]
        if st_row.empty:
            continue
        st_row      = st_row.iloc[0]
        disp        = int(st_row["stock_disponible"])
        transito    = int(st_row["stock_transito"])
        fecha_trans = st_row["fecha_llegada_transito"]

        mu      = max(demand_avg.get(sku, 1.0), 0.1)          # effective (override if active)
        mu_mdl  = max(demand_avg_model.get(sku, mu), 0.1)     # model baseline
        sigma   = max(cv * mu_mdl, 0.1)                        # σ always from model µ
        is_ovr  = sku in override_skus

        # Demand during LT+1 weeks: +1 covers reception and shelf replenishment time
        fc_grp  = fc_by_sku.get(sku, pd.DataFrame())
        fc_lt   = float(fc_grp.head(lt + 1)["AutoETS"].sum()) if not fc_grp.empty else mu * (lt + 1)
        fc_lt_detail = (
            [(row["ds"].strftime("%d/%m"), round(float(row["AutoETS"]), 1))
             for _, row in fc_grp.head(lt + 1).iterrows()]
            if not fc_grp.empty else []
        )

        c_capital = precio * 0.25 / 52.0
        c_obs_sem = precio * tasa_obs
        costo_tenencia = c_capital + c_obs_sem

        denom = margen + costo_rep + costo_tenencia
        sl = (margen + costo_rep) / denom if denom > 0 else 0.99
        sl = min(max(sl, 0.50), 0.9999)

        z  = _normal_ppf(sl)
        ss = max(z * sigma * math.sqrt(lt), 0.0)
        rop = fc_lt + ss          # ROP uses actual forecast sum, not µ×LT

        inv_pos = disp + transito

        if inv_pos < rop:
            order_qty = math.ceil(rop - inv_pos)
        else:
            order_qty = 0

        if order_qty > 0 and inv_pos < ss:
            semaforo, semaforo_label = "🔴", "urgente"
        elif order_qty > 0:
            semaforo, semaforo_label = "🟡", "normal"
        else:
            semaforo, semaforo_label = "🟢", "sin orden"

        coverage_days = (inv_pos / mu * 7) if mu > 0 else 0
        cobertura_obj = (rop + order_qty) / mu if mu > 0 else 0

        rows.append(dict(
            sku            = sku,
            categoria      = cat,
            precio         = precio,
            costo          = costo,
            margen         = margen,
            margen_pct     = round(margen / precio * 100, 1),
            costo_rep      = costo_rep,
            lead_time      = lt,
            cv_demanda     = cv,
            tasa_obs       = tasa_obs,
            c_capital      = round(c_capital, 5),
            c_obs_sem      = round(c_obs_sem, 5),
            costo_tenencia = round(costo_tenencia, 5),
            service_level  = round(sl * 100, 2),
            z_score        = round(z, 3),
            mu             = round(mu, 2),
            mu_model       = round(mu_mdl, 2),
            mu_is_ovr      = is_ovr,
            sigma          = round(sigma, 2),
            safety_stock   = round(ss, 0),
            reorder_point  = round(rop, 0),
            stock_disp     = disp,
            stock_trans    = transito,
            fecha_trans    = fecha_trans,
            inv_pos        = disp + transito,
            fc_lt_weeks    = round(fc_lt, 1),
            fc_lt_detail   = fc_lt_detail,
            order_qty      = order_qty,
            order_cost     = round(order_qty * costo, 2),
            semaforo       = semaforo,
            semaforo_label = semaforo_label,
            coverage_days  = round(coverage_days, 1),
            cobertura_obj  = round(cobertura_obj, 1),
        ))

    return pd.DataFrame(rows)


def project_stock(row: pd.Series, fc_df: pd.DataFrame, n_weeks: int = 16) -> pd.DataFrame:
    today  = pd.Timestamp.today().normalize()
    lt     = int(row["lead_time"])
    weeks  = list(range(n_weeks))
    dates  = [today + pd.Timedelta(weeks=w) for w in weeks]

    if not fc_df.empty:
        fc_sorted = fc_df.sort_values("ds").reset_index(drop=True)
        demands = []
        for d in dates:
            match = fc_sorted[fc_sorted["ds"] >= d]
            if not match.empty:
                demands.append(float(match.iloc[0]["AutoETS"]))
            else:
                demands.append(float(row["mu"]))
    else:
        demands = [float(row["mu"])] * n_weeks

    stock_proj = []
    s = float(row["stock_disp"])
    transit_added = False
    for w in weeks:
        if not transit_added:
            if w == max(0, lt // 2):
                s += float(row["stock_trans"])
                transit_added = True
        s = max(0.0, s - demands[w])
        stock_proj.append(round(s, 1))

    stock_with_order = []
    s2 = float(row["stock_disp"])
    transit_added2 = False
    order_qty = float(row["order_qty"])
    order_added = False
    for w in weeks:
        if not transit_added2:
            if w == max(0, lt // 2):
                s2 += float(row["stock_trans"])
                transit_added2 = True
        if not order_added and order_qty > 0 and w == lt:
            s2 += order_qty
            order_added = True
        s2 = max(0.0, s2 - demands[w])
        stock_with_order.append(round(s2, 1))

    return pd.DataFrame({
        "semana"         : weeks,
        "fecha"          : dates,
        "demanda"        : [round(d, 1) for d in demands],
        "stock_sin_orden": stock_proj,
        "stock_con_orden": stock_with_order,
    })


# ─── HTML helpers ─────────────────────────────────────────────────────────────
def _kpi(label: str, value: str, delta: str = "", cls: str = "neu") -> str:
    delta_html = f'<div class="kpi-delta {cls}">{delta}</div>' if delta else ""
    return (
        f'<div class="kpi">'
        f'  <div class="kpi-label">{label}</div>'
        f'  <div class="kpi-value">{value}</div>'
        f'  {delta_html}'
        f'</div>'
    )


def _badge(text: str, color: str = "neutral") -> str:
    return f'<span class="badge badge-{color}">{text}</span>'


# ─── Category summary ─────────────────────────────────────────────────────────
_CAT_LABELS = {"A": "A · Abarrotes", "B": "B · Moda/Temporada", "C": "C · Durables"}


def _render_category_summary(rep: pd.DataFrame, ovr_skus: set | None = None) -> None:
    if "categoria" not in rep.columns:
        rep = rep.copy()
        rep["categoria"] = "A"

    cols = st.columns(3)
    for col, cat in zip(cols, ["A", "B", "C"]):
        sub = rep[rep["categoria"] == cat]
        if sub.empty:
            continue
        n_tot   = len(sub)
        n_orden = (sub["order_qty"] > 0).sum()
        avg_sl  = sub["service_level"].mean()
        avg_cob = sub["cobertura_obj"].mean()
        label   = _CAT_LABELS.get(cat, cat)

        rows_html = ""
        for _, r in sub.iterrows():
            order_cls = ("order-urgent" if r["semaforo_label"] == "urgente"
                         else "order-normal" if r["semaforo_label"] == "normal"
                         else "order-none")
            order_val = f"{int(r['order_qty']):,}" if r["order_qty"] > 0 else "—"
            ovr_tag = (
                ' <span style="background:rgba(245,197,66,0.15);color:#f5c542;'
                'border:1px solid #f5c542;border-radius:3px;font-size:9px;'
                'padding:1px 4px;font-weight:700;">OVR</span>'
                if ovr_skus and r["sku"] in ovr_skus else ""
            )
            rows_html += f"""
            <tr>
              <td class="sku-cell" style="font-size:11px;">{r['sku']}{ovr_tag}</td>
              <td style="text-align:right;font-size:11px;">{r['service_level']:.1f}%</td>
              <td style="text-align:right;font-size:11px;">{r['cobertura_obj']:.1f}</td>
              <td class="{order_cls}" style="text-align:right;font-size:11px;">{order_val}</td>
              <td style="text-align:center;font-size:13px;">{r['semaforo']}</td>
            </tr>"""

        with col:
            st.html(f"""
            <div style="background:{C['bg_card']};border:1px solid {C['border']};
                        border-radius:8px;padding:14px 16px;margin-bottom:8px;">
              <div style="font-size:10px;letter-spacing:0.12em;text-transform:uppercase;
                          color:{C['text_2']};font-weight:700;margin-bottom:10px;
                          border-bottom:1px solid {C['border']};padding-bottom:6px;">
                CAT. {label}
              </div>
              <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:8px;margin-bottom:12px;">
                <div>
                  <div style="font-size:9px;color:{C['text_3']};text-transform:uppercase;
                              letter-spacing:0.1em;">Nivel Serv.</div>
                  <div style="font-size:18px;font-weight:700;color:{C['text_1']};
                              font-family:{C['mono']};">{avg_sl:.1f}%</div>
                </div>
                <div>
                  <div style="font-size:9px;color:{C['text_3']};text-transform:uppercase;
                              letter-spacing:0.1em;">Cob. Obj.</div>
                  <div style="font-size:18px;font-weight:700;color:{C['text_1']};
                              font-family:{C['mono']};">{avg_cob:.1f}<span style="font-size:11px;color:{C['text_2']};"> sem</span></div>
                </div>
                <div>
                  <div style="font-size:9px;color:{C['text_3']};text-transform:uppercase;
                              letter-spacing:0.1em;">Con orden</div>
                  <div style="font-size:18px;font-weight:700;color:{C['yellow'] if n_orden>0 else C['green']};
                              font-family:{C['mono']};">{n_orden}<span style="font-size:11px;color:{C['text_2']};"> / {n_tot}</span></div>
                </div>
              </div>
              <table class="rep-table" style="width:100%;">
                <thead><tr>
                  <th style="text-align:left;">SKU</th>
                  <th>SL %</th><th>Cob.</th><th>Orden</th><th>Est.</th>
                </tr></thead>
                <tbody>{rows_html}</tbody>
              </table>
            </div>
            """)


# ─── Export ───────────────────────────────────────────────────────────────────
def _build_export_csv(rep: pd.DataFrame) -> bytes:
    export = rep[[
        "sku", "categoria", "precio", "costo", "margen", "margen_pct", "costo_rep",
        "lead_time", "cv_demanda", "tasa_obs",
        "c_capital", "c_obs_sem", "costo_tenencia",
        "service_level", "z_score",
        "mu", "sigma",
        "safety_stock", "reorder_point", "cobertura_obj",
        "stock_disp", "stock_trans", "fecha_trans", "inv_pos",
        "fc_lt_weeks", "order_qty", "order_cost",
        "semaforo_label", "coverage_days",
    ]].copy()

    export.columns = [
        "SKU", "Categoría",
        "Precio venta ($)", "Costo unitario ($)", "Margen unitario ($)", "Margen %",
        "Costo reputacional ($)",
        "Lead time (sem)", "CV demanda", "Tasa obsolescencia semanal",
        "c_capital ($/sem)", "c_obs ($/sem)", "c_t total ($/sem)",
        "Nivel servicio objetivo (%)", "Z-score",
        "Demanda promedio μ (u/sem)", "Std demanda σ (u/sem)",
        "Safety stock (u)", "Punto de reorden (u)", "Cobertura objetivo (sem)",
        "Stock disponible (u)", "Stock en tránsito (u)", "Fecha llegada tránsito",
        "Posición inventario (u)",
        "Forecast próx. LT semanas (u)", "Orden sugerida (u)", "Costo orden ($)",
        "Estado", "Cobertura actual (días)",
    ]

    export.insert(0, "Fecha generación", pd.Timestamp.today().strftime("%Y-%m-%d"))
    return export.to_csv(index=False, float_format="%.2f").encode("utf-8-sig")


# ─── Main UI ──────────────────────────────────────────────────────────────────
def main() -> None:
    today_str = pd.Timestamp.today().strftime("%Y-%m-%d")

    # ── Header ────────────────────────────────────────────────────────────────
    st.html(f"""
    <div class="sc-header">
      <div class="sc-brand">
        <div class="sc-icon">◈</div>
        <div>
          <div class="sc-name">ABASTO</div>
          <div class="sc-tagline">COMPRA — PHASE 2 · Revisión periódica semanal</div>
        </div>
      </div>
      <div class="sc-badges">
        {_badge("Phase 2", "blue")}
        {_badge(today_str, "neutral")}
        {_badge("Revisión Semanal", "yellow")}
      </div>
    </div>
    """)

    # ── Load data ─────────────────────────────────────────────────────────────
    _fuente = st.session_state.get("data_source", "demo")
    with st.spinner("Cargando forecast y datos de inventario…"):
        _all_productos = _load_productos()
        stock          = _load_stock()
        fc_res         = _load_forecast(override_hash=_get_override_hash(), fuente=_fuente)

    # Filter productos to active data source
    if "fuente" in _all_productos.columns:
        productos = _all_productos[_all_productos["fuente"] == _fuente].copy()
    else:
        from upload import DEMO_SKUS as _DEMO_SKUS
        productos = (
            _all_productos[_all_productos["sku"].isin(_DEMO_SKUS)].copy()
            if _fuente == "demo"
            else _all_productos[~_all_productos["sku"].isin(_DEMO_SKUS)].copy()
        )

    if fc_res is None:
        st.error("No se pudo cargar el forecast. Ve a la página Forecast primero.")
        return

    fc_df_all = fc_res["forecasts"].copy()

    # ── Overrides activos ─────────────────────────────────────────────────────
    _ovr_all  = overrides_module.load()
    _ovr_skus = set(_ovr_all.keys())

    # ── Compute replenishment ─────────────────────────────────────────────────
    rep = compute_replenishment(productos, stock, fc_res)

    if rep.empty:
        st.html('<div class="warn-box">No hay datos de inventario para los SKUs seleccionados.</div>')
        return

    csv_bytes = _build_export_csv(rep)

    n_con_orden = (rep["order_qty"] > 0).sum()
    n_urgente   = (rep["semaforo_label"] == "urgente").sum()
    n_total     = len(rep)

    # ── Generate orders button ────────────────────────────────────────────────
    _btn_col, _exp_col = st.columns([3, 1])
    with _btn_col:
        run_orders = st.button(
            "⟳  GENERAR ÓRDENES DE COMPRA",
            use_container_width=True,
        )
    _csv_fname = f"compra_{pd.Timestamp.today().strftime('%Y%m%d')}.csv"
    with _exp_col:
        if st.download_button(
            label="↓  EXPORTAR CSV",
            data=csv_bytes,
            file_name=_csv_fname,
            mime="text/csv",
            use_container_width=True,
        ):
            st.toast(f"✓ CSV exportado: {_csv_fname} ({len(rep)} SKUs)", icon="✅")

    # ── Stats summary ─────────────────────────────────────────────────────────
    st.html(f"""
    <div class="model-card" style="margin-bottom:20px;">
      <div class="mc-row">Total SKUs<span>{n_total}</span></div>
      <div class="mc-row">Necesitan reposición
        <span style="color:{C['yellow']}">{n_con_orden}</span></div>
      <div class="mc-row">Urgentes
        <span style="color:{C['red']}">{n_urgente}</span></div>
      <div class="mc-row">Sin orden
        <span style="color:{C['green']}">{n_total - n_con_orden}</span></div>
      {'<div class="mc-row">Con override<span style="color:' + C["yellow"] + '">' + str(len(_ovr_skus)) + '</span></div>' if _ovr_skus else ''}
    </div>
    """)

    if "rep_computed" not in st.session_state or run_orders:
        st.session_state["rep_computed"] = True
        if run_orders:
            n_orders   = int((rep["order_qty"] > 0).sum())
            total_cost = float(rep[rep["order_qty"] > 0]["order_cost"].sum())
            st.toast(f"✓ {n_orders} órdenes generadas por ${total_cost:,.0f}", icon="✅")

    # ── Global KPIs ───────────────────────────────────────────────────────────
    total_order_cost = rep[rep["order_qty"] > 0]["order_cost"].sum()
    avg_sl = rep["service_level"].mean()
    avg_coverage = rep["coverage_days"].mean()

    st.html(
        '<div class="kpi-row">'
        + _kpi("SKUs con Orden", str(n_con_orden),
               f"de {n_total} revisados", "neg" if n_con_orden > n_total // 2 else "neu")
        + _kpi("Órdenes Urgentes", str(n_urgente),
               "posición &lt; safety stock", "neg" if n_urgente > 0 else "pos")
        + _kpi("Costo Total Órdenes", f"${total_order_cost:,.0f}",
               "suma de order_qty &times; costo", "neu")
        + _kpi("Nivel Serv. Promedio", f"{avg_sl:.1f}%",
               "objetivo endógeno por SKU", "pos")
        + _kpi("Cobertura Promedio", f"{avg_coverage:.0f}d",
               "stock actual + tránsito", "neu")
        + "</div>"
    )

    # ── Vista selector + SKU picker ───────────────────────────────────────────
    col_a, col_b = st.columns([1, 3])
    with col_a:
        vista = st.radio(
            "Vista",
            ["Por SKU", "Por Categoría", "Total"],
            horizontal=False,
            key="vista_compra",
            label_visibility="collapsed",
        )
    with col_b:
        if vista == "Por SKU":
            sku_options  = sorted(rep["sku"].tolist())
            urgent_skus  = rep[rep["semaforo_label"] == "urgente"]["sku"].tolist()
            ordered_skus = rep[rep["order_qty"] > 0]["sku"].tolist()
            default_sku  = (urgent_skus[0] if urgent_skus
                            else (ordered_skus[0] if ordered_skus else sku_options[0]))
            selected_sku = st.selectbox(
                "SKU", sku_options,
                index=sku_options.index(default_sku),
                key="sku_compra",
                label_visibility="collapsed",
            )

    # ── Content based on vista ────────────────────────────────────────────────
    if vista == "Por SKU":
        st.html('<div class="section-hdr">DETALLE POR SKU</div>')
        _render_sku_detail(rep, fc_df_all, selected_sku, ovr_skus=_ovr_skus)

    elif vista == "Por Categoría":
        st.html('<div class="section-hdr">TABLA DE REPOSICIÓN</div>')
        pass  # categoria ya viene de compute_replenishment (BD)
        tabs = st.tabs(["Categoría A · Alta rotación", "Categoría B · Media", "Categoría C · Baja rotación"])
        for tab, cat in zip(tabs, ["A", "B", "C"]):
            with tab:
                _render_table(rep[rep["categoria"] == cat].copy(), ovr_skus=_ovr_skus)
        st.html('<div class="section-hdr">RESUMEN POR CATEGORÍA</div>')
        _render_category_summary(rep, ovr_skus=_ovr_skus)

    else:  # Total
        st.html('<div class="section-hdr">TABLA DE REPOSICIÓN</div>')
        _render_table(rep, ovr_skus=_ovr_skus)
        st.html('<div class="section-hdr">RESUMEN POR CATEGORÍA</div>')
        _render_category_summary(rep, ovr_skus=_ovr_skus)


# ─── Table renderer ───────────────────────────────────────────────────────────
def _render_table(rep: pd.DataFrame, ovr_skus: set | None = None) -> None:
    if rep.empty:
        st.html('<div class="info-box">No hay SKUs en esta categoría.</div>')
        return

    header = """
    <table class="rep-table">
      <thead><tr>
        <th>SKU</th>
        <th>Margen %</th>
        <th>Nivel Serv. %</th>
        <th>Pos. Inv.</th>
        <th>P. Reorden</th>
        <th>Safety Stock</th>
        <th>FC próx. LT sem.</th>
        <th>Cob. obj. (sem)</th>
        <th>Orden sugerida</th>
        <th>Estado</th>
      </tr></thead>
      <tbody>
    """
    rows_html = ""
    for _, r in rep.iterrows():
        order_cls = (
            "order-urgent" if r["semaforo_label"] == "urgente"
            else "order-normal" if r["semaforo_label"] == "normal"
            else "order-none"
        )
        order_val = f"{int(r['order_qty']):,}" if r["order_qty"] > 0 else "—"
        ovr_tag = (
            ' <span style="background:rgba(245,197,66,0.15);color:#f5c542;'
            'border:1px solid #f5c542;border-radius:3px;font-size:9px;'
            'padding:1px 4px;font-weight:700;">OVR</span>'
            if ovr_skus and r["sku"] in ovr_skus else ""
        )
        rows_html += f"""
        <tr>
          <td class="sku-cell">{r['sku']}{ovr_tag}</td>
          <td>{r['margen_pct']:.1f}%</td>
          <td>{r['service_level']:.1f}%</td>
          <td>{int(r['inv_pos']):,}</td>
          <td>{int(r['reorder_point']):,}</td>
          <td>{int(r['safety_stock']):,}</td>
          <td>{r['fc_lt_weeks']:,.1f}</td>
          <td>{r['cobertura_obj']:.1f}</td>
          <td class="{order_cls}">{order_val}</td>
          <td>{r['semaforo']} {r['semaforo_label']}</td>
        </tr>
        """
    footer = "</tbody></table>"
    st.html(header + rows_html + footer)


# ─── SKU detail renderer ──────────────────────────────────────────────────────
def _render_sku_detail(
    rep: pd.DataFrame,
    fc_df_all: pd.DataFrame,
    sku: str,
    ovr_skus: set | None = None,
) -> None:
    row    = rep[rep["sku"] == sku].iloc[0]
    fc_sku = fc_df_all[fc_df_all["unique_id"] == sku].sort_values("ds").reset_index(drop=True)

    order_val  = f"{int(row['order_qty']):,} u" if row["order_qty"] > 0 else "Sin orden"
    order_cost = f"${row['order_cost']:,.0f}" if row["order_qty"] > 0 else "—"
    cov_cls    = "neg" if row["coverage_days"] < row["lead_time"] * 7 else (
                 "neu" if row["coverage_days"] < row["lead_time"] * 14 else "pos")
    ovr_note   = " · <span style='color:#f5c542'>OVR</span>" if (ovr_skus and sku in ovr_skus) else ""

    col1, col2 = st.columns([3, 2])
    with col1:
        order_cls_det = (
            "neg" if row["semaforo_label"] == "urgente"
            else "neu" if row["semaforo_label"] == "normal" else "pos"
        )
        st.html(
            '<div class="kpi-row">'
            + _kpi("Nivel de Servicio", f"{row['service_level']:.1f}%",
                   f"z = {row['z_score']:.2f} | LT = {row['lead_time']} sem{ovr_note}", "pos")
            + _kpi("Cobertura Actual", f"{row['coverage_days']:.0f}d",
                   f"pos. inv. = {int(row['inv_pos']):,} u", cov_cls)
            + _kpi("Cobertura Objetivo", f"{row['cobertura_obj']:.1f} sem",
                   "(ROP + orden) / &mu;", "neu")
            + _kpi("Orden Sugerida", order_val,
                   f"costo: {order_cost}", order_cls_det)
            + "</div>"
        )

    with col2:
        st.html(f"""
        <div class="model-card" style="margin-top:4px;">
          <div class="mc-row">Safety Stock<span>{int(row['safety_stock']):,} u</span></div>
          <div class="mc-row">Punto de Reorden<span>{int(row['reorder_point']):,} u</span></div>
          <div class="mc-row">Cob. objetivo<span>{row['cobertura_obj']:.1f} sem</span></div>
          <div class="mc-row">Demanda &mu;<span>{row['mu']:,.2f} u/sem</span></div>
          <div class="mc-row">CV&nbsp;&middot;&nbsp;&sigma; = CV&times;&mu;<span>{row['cv_demanda']:.3f}&nbsp;&middot;&nbsp;{row['sigma']:.2f} u</span></div>
          <div class="mc-row">Margen&nbsp;&middot;&nbsp;Margen %<span>${row['margen']:.2f}&nbsp;&middot;&nbsp;{row['margen_pct']:.1f}%</span></div>
          <div class="mc-row">Costo reputacional<span>${row['costo_rep']:.2f}</span></div>
          <div class="mc-row">Tasa obsolescencia<span>{row['tasa_obs']:.4f}/sem</span></div>
          <div class="mc-row">c_t (capital + obs)<span>${row['costo_tenencia']:.5f}</span></div>
        </div>
        """)

    _render_explanation(row)

    st.html("<br>")
    proj = project_stock(row, fc_sku)
    _render_projection_chart(proj, row)


def _render_explanation(row: pd.Series) -> None:
    sl     = row["service_level"]
    lt     = int(row["lead_time"])
    rop    = int(row["reorder_point"])
    ss     = int(row["safety_stock"])
    pos    = int(row["inv_pos"])
    mu     = row["mu"]
    cov    = row["coverage_days"]
    order  = int(row["order_qty"])
    sem    = row["semaforo_label"]

    formula = (
        f"SL = ({row['margen']:.2f} + {row['costo_rep']:.2f}) / "
        f"({row['margen']:.2f} + {row['costo_rep']:.2f} + {row['costo_tenencia']:.4f}) "
        f"= {sl:.1f}%  →  z = {row['z_score']:.3f}"
    )
    ss_formula = (
        f"SS = {row['z_score']:.3f} × {row['sigma']:.2f} × √{lt} "
        f"= {ss:,} u"
    )
    fc_lt  = row["fc_lt_weeks"]
    rop_formula = f"ROP = fc_(LT+1) + SS = {fc_lt:,.1f} + {ss:,} = {rop:,} u"

    if sem == "urgente":
        box_cls = "danger-box"
        msg = (
            f"🔴 ORDEN URGENTE — La posición de inventario ({pos:,} u) está por debajo del "
            f"safety stock ({ss:,} u). Riesgo de quiebre de stock en menos de "
            f"{cov:.0f} días con la demanda actual de {mu:.1f} u/sem. "
            f"Se sugiere emitir una orden de {order:,} u inmediatamente."
        )
    elif sem == "normal":
        box_cls = "info-box"
        msg = (
            f"Orden recomendada — La posición de inventario ({pos:,} u) cruzó el "
            f"punto de reorden ({rop:,} u). Con un lead time de {lt} semanas y demanda "
            f"de {mu:.1f} u/sem, se requieren {order:,} u para mantener nivel de "
            f"servicio {sl:.1f}%."
        )
    else:
        box_cls = "ok-box"
        msg = (
            f"🟢 SIN ORDEN ESTA SEMANA — La posición de inventario ({pos:,} u) supera "
            f"el punto de reorden ({rop:,} u). Cobertura actual: {cov:.0f} días. "
            f"Próxima revisión: semana siguiente."
        )

    st.html(f'<div class="{box_cls}">{msg}</div>')
    decision_str = (
        f"Pos. Inv. ({pos:,}) &lt; ROP ({rop:,}) &nbsp;→&nbsp; PEDIR {order:,} u"
        if order > 0
        else f"Pos. Inv. ({pos:,}) &ge; ROP ({rop:,}) &nbsp;→&nbsp; SIN ORDEN"
    )
    order_formula = (
        f"Q = &lceil;ROP &minus; Pos.Inv.&rceil; "
        f"= &lceil;{rop:,} &minus; {pos:,}&rceil; = {order:,} u"
        if order > 0
        else "Pos. Inv. &ge; ROP &nbsp;→&nbsp; Q = 0 (sin orden esta semana)"
    )
    margen_pct = row['margen'] / row['precio'] * 100

    with st.expander("Ver cálculo detallado"):
        st.html(f"""
        <div class="info-box" style="line-height:1.9;">

        <div style="font-size:10px;letter-spacing:0.12em;text-transform:uppercase;
                    color:#8892a8;font-weight:700;margin-bottom:10px;
                    border-bottom:1px solid #252840;padding-bottom:6px;">
          DATOS DEL PRODUCTO
        </div>
        <table style="width:100%;border-collapse:collapse;font-family:'Courier New',monospace;font-size:12px;margin-bottom:16px;">
          <tr><td style="color:#8892a8;padding:2px 0;width:55%;">Precio de venta</td>
              <td style="color:#e2e8f0;text-align:right;">${row['precio']:.2f}</td></tr>
          <tr><td style="color:#8892a8;padding:2px 0;">Costo unitario</td>
              <td style="color:#e2e8f0;text-align:right;">${row['costo']:.2f}</td></tr>
          <tr><td style="color:#8892a8;padding:2px 0;">Margen unitario&nbsp;<small>(precio &minus; costo)</small></td>
              <td style="color:#00c49a;text-align:right;">${row['margen']:.2f} &nbsp;({margen_pct:.1f}%)</td></tr>
          <tr><td style="color:#8892a8;padding:2px 0;">Costo reputacional</td>
              <td style="color:#f5c542;text-align:right;">${row['costo_rep']:.2f}</td></tr>
          <tr><td style="color:#8892a8;padding:2px 0;">Lead time</td>
              <td style="color:#e2e8f0;text-align:right;">{lt} semanas</td></tr>
          <tr><td style="color:#8892a8;padding:2px 0;">Demanda promedio &mu;&nbsp;<small>({'<span style="color:#f5c542">override activo</span>' if row.get("mu_is_ovr") else 'forecast AutoETS'})</small></td>
              <td style="color:{'#f5c542' if row.get('mu_is_ovr') else '#e2e8f0'};text-align:right;">{mu:,.1f} u/sem{'&nbsp;<small style="color:#8892a8;">(modelo: ' + str(row["mu_model"]) + ')</small>' if row.get("mu_is_ovr") else ''}</td></tr>
          <tr><td style="color:#8892a8;padding:2px 0;">CV de demanda&nbsp;<small>(parámetro estático)</small></td>
              <td style="color:#e2e8f0;text-align:right;">{row['cv_demanda']:.3f}</td></tr>
          <tr><td style="color:#8892a8;padding:2px 0;">Desviación estándar &sigma; = CV &times; &mu;<sub>modelo</sub></td>
              <td style="color:#e2e8f0;text-align:right;">{row['sigma']:,.2f} u/sem</td></tr>
        </table>

        <div style="font-size:10px;letter-spacing:0.12em;text-transform:uppercase;
                    color:#8892a8;font-weight:700;margin-bottom:10px;
                    border-bottom:1px solid #252840;padding-bottom:6px;">
          CÁLCULOS PASO A PASO
        </div>

        <b>① Costo de tenencia semanal</b><br>
        <code>c_capital = precio &times; 0.25 / 52 = {row['precio']:.4f} &times; 0.25 / 52 = <b>{row['c_capital']:.5f}</b> $/u/sem</code><br>
        <code>c_obs&nbsp;&nbsp;&nbsp;&nbsp; = precio &times; tasa_obs = {row['precio']:.4f} &times; {row['tasa_obs']:.4f} = <b>{row['c_obs_sem']:.5f}</b> $/u/sem</code><br>
        <code>c_t&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; = c_capital + c_obs = {row['c_capital']:.5f} + {row['c_obs_sem']:.5f} = <b>{(row['c_capital']+row['c_obs_sem']):.5f}</b> $/u/sem</code><br>
        <small style="color:#8892a8;">— Costo capital (25%/año) + costo obsolescencia semanal por riesgo de descontinuación.</small><br><br>

        <b>② Nivel de servicio objetivo&nbsp;<small>(fórmula newsvendor: c<sub>u</sub> / (c<sub>u</sub> + c<sub>o</sub>))</small></b><br>
        <code>SL = (margen + c<sub>rep</sub>) / (margen + c<sub>rep</sub> + c<sub>t</sub>)</code><br>
        <code>SL = ({row['margen']:.2f} + {row['costo_rep']:.2f}) / ({row['margen']:.2f} + {row['costo_rep']:.2f} + {row['costo_tenencia']:.4f}) = <b>{sl:.2f}%</b></code><br>
        <small style="color:#8892a8;">— Costo de quiebre (margen perdido + daño reputacional) vs. costo de exceso.</small><br><br>

        <b>③ Z-score del nivel de servicio</b><br>
        <code>z = &Phi;<sup>&minus;1</sup>(SL/100) = &Phi;<sup>&minus;1</sup>({sl/100:.4f}) = <b>{row['z_score']:.4f}</b></code><br>
        <small style="color:#8892a8;">— Cuantil de la distribución normal estándar.</small><br><br>

        <b>④ Safety stock</b><br>
        <code>&sigma; = CV &times; &mu;<sub>modelo</sub> = {row['cv_demanda']:.3f} &times; {row['mu_model']:.1f} = {row['sigma']:.2f} u/sem</code><br>
        <code>SS = z &times; &sigma; &times; &radic;LT = {row['z_score']:.4f} &times; {row['sigma']:.2f} &times; &radic;{lt} = <b>{ss:,} u</b></code><br>
        <small style="color:#8892a8;">— &sigma; usa &mu; del modelo (no override) para preservar la estimación de variabilidad.</small><br><br>

        <b>⑤ Punto de reorden</b><br>
        <code>ROP = fc_(LT+1) + SS = {fc_lt:,.1f} + {ss:,} = <b>{rop:,} u</b></code><br>
        <small style="color:#8892a8;">— fc_(LT+1) = suma forecast próximas {lt+1} sem ({lt} sem lead time + 1 sem recepción/góndola).</small><br>
        {"".join("<small style='color:#8892a8;'>&nbsp;&nbsp;&nbsp;&nbsp;sem " + str(i+1) + " (" + d + "): " + f"{v:,.1f}" + " u</small><br>" for i, (d, v) in enumerate(row.get("fc_lt_detail", [])))}
        <small style="color:#8892a8;">&nbsp;&nbsp;&nbsp;&nbsp;<b>Total demanda durante LT: {fc_lt:,.1f} u</b></small><br><br>

        <b>⑥ Posición de inventario</b><br>
        <code>Pos.Inv. = stock disp. + stock tránsito = {row['stock_disp']:,} + {row['stock_trans']:,} = <b>{pos:,} u</b></code><br>
        <small style="color:#8892a8;">— Tránsito llega aprox. el {row['fecha_trans'].strftime('%d/%m/%Y')}.</small><br><br>

        <b>⑦ Cantidad a pedir</b><br>
        <code>Q = &lceil;ROP &minus; Pos.Inv.&rceil;</code><br>
        <code>{order_formula}</code><br>
        <small style="color:#8892a8;">— ROP ya incluye fc_LT + SS; Q repone hasta ese nivel.</small><br><br>

        <b>⑧ Costo de la orden</b><br>
        <code>Costo = Q &times; costo unitario = {order:,} &times; ${row['costo']:.2f} = <b>${row['order_cost']:,.2f}</b></code><br><br>

        <div style="border-top:1px solid #252840;padding-top:10px;margin-top:4px;">
        <b>Decisión:</b>&nbsp; <code>{decision_str}</code>
        </div>

        </div>
        """)


def _render_projection_chart(proj: pd.DataFrame, row: pd.Series) -> None:
    ss    = float(row["safety_stock"])
    rop   = float(row["reorder_point"])
    lt    = int(row["lead_time"])
    order = int(row["order_qty"])
    has_order = order > 0

    # Truncate x-axis at first zero of the primary stock line
    primary_col = "stock_con_orden" if has_order else "stock_sin_orden"
    zero_rows = proj[proj[primary_col] <= 0].index
    if not zero_rows.empty:
        cutoff = max(zero_rows[0] + 1, lt + 2)
        cutoff = min(cutoff, len(proj))
        proj = proj.iloc[:cutoff].copy()

    x_dates = proj["fecha"]

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=x_dates, y=proj["stock_sin_orden"],
        name="Stock sin orden",
        line=dict(color=C["text_2"], width=2, dash="dot"),
        fill="tozeroy",
        fillcolor="rgba(136,146,168,0.05)",
        hovertemplate="Sem %{x|%d/%m}: %{y:,.0f} u<extra>sin orden</extra>",
    ))

    if has_order:
        fig.add_trace(go.Scatter(
            x=x_dates, y=proj["stock_con_orden"],
            name=f"Stock con orden ({order:,} u, llega S{lt})",
            line=dict(color=C["blue"], width=2.5),
            fill="tozeroy",
            fillcolor=C["blue_dim"],
            hovertemplate="Sem %{x|%d/%m}: %{y:,.0f} u<extra>con orden</extra>",
        ))

    fig.add_trace(go.Bar(
        x=x_dates, y=proj["demanda"],
        name="Demanda forecast",
        marker_color="rgba(79,143,247,0.2)",
        hovertemplate="Sem %{x|%d/%m}: %{y:,.1f} u<extra>demanda</extra>",
        opacity=0.7,
    ))

    x0_date = x_dates.iloc[0]
    x1_date = x_dates.iloc[-1]

    fig.add_shape(type="line", x0=x0_date, x1=x1_date, y0=ss, y1=ss,
                  xref="x", yref="y",
                  line=dict(color=C["red"], width=1.5, dash="dash"))
    fig.add_annotation(x=x1_date, y=ss, xref="x", yref="y",
                       text=f"SS {ss:,.0f}u", showarrow=False,
                       font=dict(color=C["red"], size=10),
                       xanchor="right", yanchor="bottom")

    fig.add_shape(type="line", x0=x0_date, x1=x1_date, y0=rop, y1=rop,
                  xref="x", yref="y",
                  line=dict(color=C["yellow"], width=1.5, dash="longdash"))
    fig.add_annotation(x=x1_date, y=rop, xref="x", yref="y",
                       text=f"ROP {rop:,.0f}u", showarrow=False,
                       font=dict(color=C["yellow"], size=10),
                       xanchor="right", yanchor="bottom")

    if has_order and lt < len(x_dates):
        arrival_date = x_dates.iloc[lt]
        fig.add_shape(type="line", x0=arrival_date, x1=arrival_date, y0=0, y1=1,
                      xref="x", yref="paper",
                      line=dict(color=C["green"], width=1.5, dash="dot"))
        fig.add_annotation(x=arrival_date, y=0.97, xref="x", yref="paper",
                           text=f"↓ Llega orden S{lt}", showarrow=False,
                           font=dict(color=C["green"], size=10),
                           xanchor="left")
        fig.add_shape(type="line", x0=x0_date, x1=x0_date, y0=0, y1=1,
                      xref="x", yref="paper",
                      line=dict(color=C["yellow"], width=1, dash="dot"))
        fig.add_annotation(x=x0_date, y=0.97, xref="x", yref="paper",
                           text="Emitir orden →", showarrow=False,
                           font=dict(color=C["yellow"], size=10),
                           xanchor="left")

    title = (
        f"{row['sku']} · Proyección de stock — LT {lt} sem · "
        f"{'SIN ORDEN' if not has_order else 'ORDEN: ' + str(order) + ' u'}"
    )
    fig = _dark_layout(fig, title=title, height=400)
    fig.update_layout(
        bargap=0.2,
        xaxis=dict(tickformat="%d/%m", dtick=7 * 24 * 3600 * 1000),
        yaxis=dict(tickformat=",d"),
    )
    st.plotly_chart(fig, use_container_width=True)


# ─── Entry point ──────────────────────────────────────────────────────────────
if __name__ == "__main__" or True:
    main()

"""
pages/forecast.py — Abasto: FORECAST — Phase 1
Planificación de demanda semanal con AutoETS + overrides manuales.
"""
from __future__ import annotations

import hashlib
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
    gap: 0;
    padding: 0;
}}
.stTabs [data-baseweb="tab"] {{
    color: {C['text_2']} !important;
    background-color: transparent !important;
    border-radius: 0 !important;
    padding: 10px 22px !important;
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 0.08em;
    text-transform: uppercase;
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
.stButton > button:disabled {{
    background-color: {C['border']} !important;
    color: {C['text_3']} !important;
    opacity: 1 !important;
}}
.streamlit-expanderHeader {{
    background-color: {C['bg_card']} !important;
    border: 1px solid {C['border']} !important;
    border-radius: 6px !important;
    color: {C['text_2']} !important;
    font-size: 11px !important;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    font-weight: 600;
}}
.streamlit-expanderContent {{
    background-color: {C['bg_surface']} !important;
    border: 1px solid {C['border']} !important;
    border-top: none !important;
    border-radius: 0 0 6px 6px !important;
}}
hr {{ border-color: {C['border']} !important; margin: 20px 0 !important; }}
[data-testid="stFileUploader"] {{
    background: {C['bg_card']};
    border: 1px dashed {C['border']};
    border-radius: 8px;
}}
[data-testid="stFileUploader"] label {{
    color: {C['text_2']} !important;
    font-size: 12px !important;
}}
.stDataFrame {{ border: 1px solid {C['border']} !important; border-radius: 6px !important; overflow: hidden; }}
[data-testid="stDataEditor"] {{
    border: 1px solid {C['border']} !important;
    border-radius: 6px !important;
    overflow: hidden;
}}
.stSpinner > div > div {{ border-top-color: {C['blue']} !important; }}
[data-testid="stNotification"] {{ border-radius: 6px !important; font-size: 12px !important; }}
[data-baseweb="slider"] [data-testid="stThumbValue"] {{ color: {C['blue']}; }}

.sc-header {{
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 4px 0 20px 0;
    border-bottom: 1px solid {C['border']};
    margin-bottom: 28px;
}}
.sc-brand {{ display: flex; align-items: baseline; gap: 10px; }}
.sc-icon {{ font-size: 24px; color: {C['blue']}; line-height: 1; }}
.sc-name {{
    font-size: 22px; font-weight: 900;
    letter-spacing: 0.1em; color: {C['text_1']};
}}
.sc-tagline {{
    font-size: 10px; letter-spacing: 0.1em;
    text-transform: uppercase; color: {C['text_2']};
}}
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
.acc-table {{
    width: 100%; border-collapse: collapse;
    font-size: 13px; font-family: {C['mono']};
    background: {C['bg_card']}; border-radius: 8px; overflow: hidden;
    border: 1px solid {C['border']};
}}
.acc-table thead tr {{ border-bottom: 1px solid {C['border']}; }}
.acc-table th {{
    font-size: 10px; letter-spacing: 0.1em; text-transform: uppercase;
    color: {C['text_2']}; padding: 10px 16px; text-align: right;
    font-family: 'Inter',sans-serif; font-weight: 700; background: {C['bg_surface']};
}}
.acc-table th:first-child {{ text-align: left; }}
.acc-table td {{
    padding: 9px 16px; text-align: right;
    border-bottom: 1px solid rgba(37,40,64,0.6); color: {C['text_1']};
}}
.acc-table td:first-child {{ text-align: left; color: {C['text_2']}; }}
.acc-table tr:last-child td {{ border-bottom: none; }}
.acc-table tr:hover td {{ background: {C['bg_surface']}; }}
.acc-table .good {{ color: {C['green']}; font-weight: 700; }}
.acc-table .warn {{ color: {C['yellow']}; font-weight: 700; }}
.acc-table .bad  {{ color: {C['red']};   font-weight: 700; }}
.model-card {{
    background: {C['bg_card']};
    border: 1px solid {C['border']};
    border-radius: 6px;
    padding: 12px 14px;
    margin-top: 4px;
}}
.mc-row {{
    display: flex; justify-content: space-between;
    font-size: 11px; padding: 3px 0;
    color: {C['text_3']}; font-family: {C['mono']};
    border-bottom: 1px solid rgba(37,40,64,0.4);
}}
.mc-row:last-child {{ border-bottom: none; }}
.mc-row span {{ color: {C['text_1']}; }}
.alert-row {{
    display: grid;
    grid-template-columns: auto 1fr auto auto auto;
    align-items: center;
    gap: 12px;
    padding: 10px 14px;
    border-radius: 6px;
    margin-bottom: 8px;
    font-size: 12px;
    font-family: {C['mono']};
}}
.alert-crit {{ background:{C['red_dim']};    border-left: 3px solid {C['red']};    }}
.alert-warn {{ background:{C['yellow_dim']}; border-left: 3px solid {C['yellow']}; }}
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
</style>
""", unsafe_allow_html=True)

# ─── Plotly dark base ─────────────────────────────────────────────────────────
_PBG   = C["bg_card"]
_GRID  = "rgba(255,255,255,0.04)"
_HOVER = dict(
    bgcolor=C["bg_card"],
    bordercolor=C["border"],
    font=dict(color=C["text_1"], family="Courier New,monospace", size=11),
)


def _dark_layout(fig: go.Figure, title: str = "", height: int = 480,
                 x_range: list | None = None, rangeslider: bool = True) -> go.Figure:
    fig.update_layout(
        template="plotly_dark",
        title=dict(
            text=title,
            font=dict(size=14, color=C["text_1"], family="Inter,sans-serif"),
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
            rangeslider=dict(
                visible=rangeslider,
                thickness=0.04,
                bgcolor=C["bg_surface"],
                borderwidth=0,
            ) if rangeslider else dict(visible=False),
            **(dict(range=x_range) if x_range else {}),
        ),
        yaxis=dict(
            showgrid=True, gridcolor=_GRID, gridwidth=1,
            showline=False, zeroline=False, rangemode="tozero",
            tickformat=".1f",
            tickfont=dict(family="Courier New,monospace", size=10, color=C["text_2"]),
        ),
    )
    return fig


def _vline(fig: go.Figure, x_str: str, color: str, label: str,
           y_label: float = 0.98, anchor: str = "left") -> None:
    fig.add_shape(type="line", x0=x_str, x1=x_str, y0=0, y1=1,
                  xref="x", yref="paper",
                  line=dict(width=1, dash="dot", color=color))
    fig.add_annotation(x=x_str, y=y_label, xref="x", yref="paper",
                       text=f"  {label}", showarrow=False,
                       xanchor=anchor, yanchor="top",
                       font=dict(color=color, size=10, family="Courier New,monospace"))


def _ci_band(fig: go.Figure, ds: list, lo: list, hi: list,
             name: str, color_rgba: str) -> None:
    rev = ds[::-1]
    fig.add_trace(go.Scatter(
        x=ds + rev, y=hi + lo[::-1],
        fill="toself", fillcolor=color_rgba,
        line=dict(color="rgba(0,0,0,0)"),
        name=name, hoverinfo="skip", showlegend=True,
    ))


# ─── UI helpers ───────────────────────────────────────────────────────────────
def kpi_row(*cards: dict) -> None:
    parts = []
    for c in cards:
        delta = ""
        if c.get("delta"):
            cls   = c.get("delta_cls", "neu")
            arrow = "▲" if cls == "pos" else ("▼" if cls == "neg" else "·")
            delta = f'<div class="kpi-delta {cls}">{arrow} {c["delta"]}</div>'
        parts.append(
            f'<div class="kpi">'
            f'<div class="kpi-label">{c["label"]}</div>'
            f'<div class="kpi-value">{c["value"]}</div>'
            f'{delta}</div>'
        )
    st.html(f'<div class="kpi-row">{"".join(parts)}</div>')


def section(title: str) -> None:
    st.html(f'<div class="section-hdr">{title}</div>')


def acc_table_html(per_sku: pd.DataFrame) -> str:
    def mape_cls(v):
        return "good" if v < 15 else ("warn" if v < 25 else "bad")
    def bias_cls(v):
        return "good" if abs(v) < 10 else ("warn" if abs(v) < 20 else "bad")

    rows = "".join(
        f'<tr><td>{sku}</td>'
        f'<td class="{mape_cls(r["MAPE"])}">{r["MAPE"]:.1f}%</td>'
        f'<td class="{bias_cls(r["Bias"])}">{r["Bias"]:+.1f}%</td></tr>'
        for sku, r in per_sku.iterrows()
    )
    return (
        '<table class="acc-table">'
        '<thead><tr><th>SKU</th><th>MAPE</th><th>BIAS</th></tr></thead>'
        f'<tbody>{rows}</tbody></table>'
    )


def comp_table_html(comp: pd.DataFrame) -> str:
    def imp_cls(v):
        return "good" if v > 2 else ("warn" if v > -2 else "bad")

    rows = "".join(
        f'<tr><td>{sku}</td>'
        f'<td>{r["MAPE_ETS"]:.1f}%</td><td>{r["Bias_ETS"]:+.1f}%</td>'
        f'<td>{r["MAPE_Naive"]:.1f}%</td><td>{r["Bias_Naive"]:+.1f}%</td>'
        f'<td class="{imp_cls(r["Mejora"])}">{r["Mejora"]:+.1f} pp</td></tr>'
        for sku, r in comp.iterrows()
    )
    return (
        '<table class="acc-table">'
        '<thead><tr>'
        '<th>SKU</th>'
        '<th>MAPE ETS</th><th>BIAS ETS</th>'
        '<th>MAPE NAIVE</th><th>BIAS NAIVE</th>'
        '<th>MEJORA</th>'
        '</tr></thead>'
        f'<tbody>{rows}</tbody></table>'
    )


# ─── Chart functions ──────────────────────────────────────────────────────────
def build_forecast_chart(
    hist: pd.DataFrame,
    fc: pd.DataFrame,
    label: str,
    fc_override: tuple | None = None,
) -> go.Figure:
    """
    fc_override: tupla (x_list, y_list) donde y tiene None en semanas sin override.
    Plotly dibuja línea verde entre semanas consecutivas con override y corta en None.
    """
    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=hist["fecha"], y=hist["cantidad"],
        name="Histórico", mode="lines",
        line=dict(color=C["text_2"], width=1.5),
        hovertemplate="%{x|%Y-%m-%d}  <b>%{y:.1f}</b><extra>Histórico</extra>",
    ))

    ds = list(fc["ds"])
    if "AutoETS-lo-95" in fc.columns:
        _ci_band(fig, ds, list(fc["AutoETS-lo-95"]), list(fc["AutoETS-hi-95"]),
                 "IC 95 %", "rgba(79,143,247,0.07)")
    if "AutoETS-lo-70" in fc.columns:
        _ci_band(fig, ds, list(fc["AutoETS-lo-70"]), list(fc["AutoETS-hi-70"]),
                 "IC 70 %", "rgba(79,143,247,0.18)")

    # Forecast original del modelo (siempre azul punteado cuando hay override activo)
    original_name = "Forecast modelo (original)" if fc_override is not None else "Forecast (AutoETS)"
    fig.add_trace(go.Scatter(
        x=fc["ds"], y=fc["AutoETS"],
        name=original_name, mode="lines",
        line=dict(color=C["blue"], width=2, dash="dash"),
        hovertemplate="%{x|%Y-%m-%d}  <b>%{y:.1f}</b><extra>Forecast modelo</extra>",
    ))

    # Forecast con override: línea verde solo entre semanas consecutivas con override
    if fc_override is not None:
        _ovr_x, _ovr_y = fc_override
        fig.add_trace(go.Scatter(
            x=_ovr_x, y=_ovr_y,
            name="Forecast con override", mode="lines+markers",
            connectgaps=False,
            line=dict(color=C["green"], width=2.5),
            marker=dict(color=C["green"], size=9, symbol="circle",
                        line=dict(color=C["bg_card"], width=1.5)),
            hovertemplate="%{x|%Y-%m-%d}  <b>%{y:.1f}</b><extra>Override</extra>",
        ))

    if "SeasonalNaive" in fc.columns:
        fig.add_trace(go.Scatter(
            x=fc["ds"], y=fc["SeasonalNaive"],
            name="Naive estacional", mode="lines",
            line=dict(color=C["text_3"], width=1, dash="dot"),
            visible="legendonly",
            hovertemplate="%{x|%Y-%m-%d}  <b>%{y:.1f}</b><extra>Naive</extra>",
        ))

    last_str = hist["fecha"].max().strftime("%Y-%m-%d")
    _vline(fig, last_str, C["text_3"], "Inicio forecast")

    x_start = (hist["fecha"].max() - pd.Timedelta(weeks=12)).strftime("%Y-%m-%d")
    x_end   = fc["ds"].max().strftime("%Y-%m-%d")

    return _dark_layout(
        fig,
        title=f"<b style='color:{C['text_1']}'>{label}</b>"
              f"<span style='color:{C['text_3']};font-size:12px'> · Histórico + Forecast 12 semanas</span>",
        x_range=[x_start, x_end],
    )


def build_forecast_history_chart(
    hist: pd.DataFrame, fc: pd.DataFrame, label: str, run_date: pd.Timestamp,
) -> go.Figure:
    fig = go.Figure()
    last_hist = hist["fecha"].max()

    fig.add_trace(go.Scatter(
        x=hist["fecha"], y=hist["cantidad"],
        name="Venta real", mode="lines",
        line=dict(color=C["text_2"], width=1.5),
        hovertemplate="%{x|%Y-%m-%d}  <b>%{y:.1f}</b><extra>Real</extra>",
    ))

    ds = list(fc["ds"])
    if "AutoETS-lo-95" in fc.columns:
        _ci_band(fig, ds, list(fc["AutoETS-lo-95"]), list(fc["AutoETS-hi-95"]),
                 "IC 95 %", "rgba(79,143,247,0.07)")
    if "AutoETS-lo-70" in fc.columns:
        _ci_band(fig, ds, list(fc["AutoETS-lo-70"]), list(fc["AutoETS-hi-70"]),
                 "IC 70 %", "rgba(79,143,247,0.18)")

    fig.add_trace(go.Scatter(
        x=fc["ds"], y=fc["AutoETS"],
        name="Forecast", mode="lines",
        line=dict(color=C["blue"], width=2, dash="dash"),
        hovertemplate="%{x|%Y-%m-%d}  <b>%{y:.1f}</b><extra>Forecast</extra>",
    ))

    overlap = (
        fc[fc["ds"] <= last_hist]
        .merge(hist.rename(columns={"fecha": "ds"})[["ds", "cantidad"]], on="ds", how="inner")
    )
    if not overlap.empty and "AutoETS-lo-70" in overlap.columns:
        mask_in = (overlap["cantidad"] >= overlap["AutoETS-lo-70"]) & \
                  (overlap["cantidad"] <= overlap["AutoETS-hi-70"])
        inside  = overlap[mask_in]
        outside = overlap[~mask_in]
        if not inside.empty:
            fig.add_trace(go.Scatter(
                x=inside["ds"], y=inside["cantidad"],
                mode="markers", name="Real dentro IC 70 %",
                marker=dict(color=C["green"], size=8, symbol="circle",
                            line=dict(color=C["bg_card"], width=1.5)),
            ))
        if not outside.empty:
            fig.add_trace(go.Scatter(
                x=outside["ds"], y=outside["cantidad"],
                mode="markers", name="Real fuera IC 70 %",
                marker=dict(color=C["red"], size=8, symbol="circle",
                            line=dict(color=C["bg_card"], width=1.5)),
            ))

    run_str  = pd.Timestamp(run_date).strftime("%Y-%m-%d")
    last_str = last_hist.strftime("%Y-%m-%d")
    _vline(fig, run_str, C["blue"], "Fecha del forecast")
    if run_str != last_str:
        _vline(fig, last_str, C["text_3"], "Último dato", y_label=0.82)

    x_start = (pd.Timestamp(run_date) - pd.Timedelta(weeks=8)).strftime("%Y-%m-%d")
    x_end   = fc["ds"].max().strftime("%Y-%m-%d")

    return _dark_layout(
        fig,
        title=f"<b style='color:{C['text_1']}'>{label}</b>"
              f"<span style='color:{C['text_3']};font-size:12px'> · Forecast del {run_str}</span>",
        x_range=[x_start, x_end],
    )


def build_forecast_table(fc: pd.DataFrame) -> pd.DataFrame:
    cols, renames = ["ds", "AutoETS"], {"ds": "SEMANA", "AutoETS": "MEDIA"}
    if "AutoETS-std" in fc.columns:
        cols.append("AutoETS-std"); renames["AutoETS-std"] = "STD"
    for band in ["70", "95"]:
        lo, hi = f"AutoETS-lo-{band}", f"AutoETS-hi-{band}"
        if lo in fc.columns:
            cols += [lo, hi]; renames[lo] = f"IC{band}% LO"; renames[hi] = f"IC{band}% HI"
    tbl = fc[cols].rename(columns=renames).copy()
    tbl["SEMANA"] = tbl["SEMANA"].dt.strftime("%Y-%m-%d")
    num = [c for c in tbl.columns if c != "SEMANA"]
    tbl[num] = tbl[num].round(1)
    return tbl.reset_index(drop=True)


def _build_sandbox_chart(hist: pd.DataFrame, fc: pd.DataFrame, model_name: str = "AutoETS") -> go.Figure:
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=hist["fecha"], y=hist["cantidad"],
        name="Histórico", mode="lines+markers",
        line=dict(color=C["text_2"], width=1.5),
        marker=dict(size=5, color=C["text_2"]),
        hovertemplate="%{x|%Y-%m-%d}  <b>%{y:.1f}</b><extra>Histórico</extra>",
    ))
    ds = list(fc["ds"])
    if "AutoETS-lo-95" in fc.columns:
        _ci_band(fig, ds, list(fc["AutoETS-lo-95"]), list(fc["AutoETS-hi-95"]),
                 "IC 95 %", "rgba(79,143,247,0.07)")
    if "AutoETS-lo-70" in fc.columns:
        _ci_band(fig, ds, list(fc["AutoETS-lo-70"]), list(fc["AutoETS-hi-70"]),
                 "IC 70 %", "rgba(79,143,247,0.18)")
    fig.add_trace(go.Scatter(
        x=fc["ds"], y=fc["AutoETS"],
        name=f"Forecast ({model_name})", mode="lines",
        line=dict(color=C["blue"], width=2, dash="dash"),
        hovertemplate="%{x|%Y-%m-%d}  <b>%{y:.1f}</b><extra>Forecast</extra>",
    ))
    last_str = hist["fecha"].max().strftime("%Y-%m-%d")
    _vline(fig, last_str, C["text_3"], "Inicio forecast")
    return _dark_layout(
        fig,
        title=f"<b style='color:{C['text_1']}'>Sandbox</b>"
              f"<span style='color:{C['text_3']};font-size:12px'> · Histórico + Forecast 12 semanas</span>",
        rangeslider=False,
        height=400,
    )


# ─── Data helpers ─────────────────────────────────────────────────────────────
def _df_hash(df: pd.DataFrame) -> str:
    return hashlib.md5(pd.util.hash_pandas_object(df).values).hexdigest()


def _clear_results():
    for k in ["forecast_results", "data_hash"]:
        st.session_state.pop(k, None)


def _get_category(sku: str) -> str:
    parts = sku.split("-")
    return parts[1][0].upper() if len(parts) >= 2 and parts[1] else "?"


def _aggregate_by_category(
    df: pd.DataFrame, forecasts: pd.DataFrame, category: str
) -> tuple[pd.DataFrame, pd.DataFrame]:
    cat_skus = [s for s in df["sku"].unique() if _get_category(s) == category]
    hist_agg = (df[df["sku"].isin(cat_skus)]
                .groupby("fecha", as_index=False)["cantidad"].sum())
    num_cols = [c for c in forecasts.columns if c not in ("unique_id", "ds", "index")]
    fc_agg   = (forecasts[forecasts["unique_id"].isin(cat_skus)]
                .groupby("ds", as_index=False)[num_cols].sum())
    return hist_agg, fc_agg


# ─── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.html(f"""
    <div style="padding:8px 0 20px 0;">
        <div style="font-size:18px;font-weight:900;letter-spacing:0.1em;color:{C['text_1']};">
            ◈ ABASTO
        </div>
        <div style="font-size:10px;letter-spacing:0.1em;text-transform:uppercase;
                    color:{C['text_2']};margin-top:3px;">
            Supply Chain Intelligence
        </div>
    </div>
    """)

    st.html(f'<div class="section-hdr">Data Source</div>')

    source = st.radio(
        "Fuente",
        ["Demo data", "Upload CSV"],
        index=0,
        label_visibility="collapsed",
    )

    df: pd.DataFrame | None = None

    if source == "Demo data":
        df   = data_module.generate_simulated_data()
        info = data_module.summary(df)
        st.html(
            f'<div class="ok-box">✓ {info["n_skus"]} SKUs · {info["n_weeks"]} semanas<br>'
            f'<span style="font-weight:400;color:{C["text_2"]};font-size:11px;">'
            f'{info["date_min"]} → {info["date_max"]}</span></div>'
        )
    else:
        uploaded = st.file_uploader(
            "CSV: fecha, sku, cantidad",
            type=["csv"],
            label_visibility="collapsed",
        )
        if uploaded is not None:
            df, err = data_module.load_csv(uploaded)
            if err:
                st.html(f'<div class="warn-box">✗ {err}</div>')
                df = None
            else:
                info = data_module.summary(df)
                st.html(
                    f'<div class="ok-box">✓ {info["n_skus"]} SKUs · {info["n_weeks"]} sem.<br>'
                    f'<span style="font-weight:400;color:{C["text_2"]};font-size:11px;">'
                    f'{info["date_min"]} → {info["date_max"]}</span></div>'
                )
        else:
            st.html(f'<div class="info-box">Upload a CSV or switch to Demo data.</div>')

    st.markdown("<br>", unsafe_allow_html=True)

    run_btn   = st.button(
        "▶  Run Forecast",
        disabled=(df is None),
        use_container_width=True,
    )
    force_btn = st.button(
        "↺  Forzar recálculo",
        disabled=(df is None),
        use_container_width=True,
        key="force_btn",
        help="Ignora el caché y recalcula el modelo desde cero.",
    )

    st.markdown("<br><br>", unsafe_allow_html=True)
    st.html(f'<div class="section-hdr">Model</div>')

    _cs = st.session_state.get("cache_status")
    if _cs:
        if _cs["from_cache"]:
            _age     = pd.Timestamp.now() - _cs["computed_at"]
            _age_str = f"{_age.days}d" if _age.days > 0 else "hoy"
            _cache_row = (f'<div class="mc-row">Caché'
                          f'<span style="color:{C["green"]}">✓ hace {_age_str}</span></div>')
        else:
            _dt_str    = _cs["computed_at"].strftime("%Y-%m-%d %H:%M")
            _cache_row = (f'<div class="mc-row">Caché'
                          f'<span style="color:{C["blue"]}">recalculado {_dt_str}</span></div>')
    else:
        _cache_row = ""

    _minfo = (st.session_state.get("forecast_results") or {}).get("model_info")
    _algo_name  = _minfo.name   if _minfo else "AutoETS · s=52"
    _algo_bench = _minfo.benchmark_col if _minfo else "SeasonalNaive"

    st.html(f"""
    <div class="model-card">
        <div class="mc-row">Algorithm   <span>{_algo_name}</span></div>
        <div class="mc-row">Horizon     <span>{fc_module.HORIZON} weeks</span></div>
        <div class="mc-row">IC levels   <span>70% · 95%</span></div>
        <div class="mc-row">Benchmark   <span>{_algo_bench}</span></div>
        {_cache_row}
    </div>
    """)
    if _minfo:
        st.html(
            f'<div style="font-size:10px;color:{C["text_3"]};font-family:{C["mono"]};">'
            f'{_minfo.reason}</div>'
        )


# ─── Main ─────────────────────────────────────────────────────────────────────
_today = pd.Timestamp.now().strftime("%Y-%m-%d %H:%M")
_model_ok   = "forecast_results" in st.session_state
_from_cache = st.session_state.get("cache_status", {}).get("from_cache", False)
_has_data   = df is not None
_info_safe  = data_module.summary(df) if _has_data else {}

# Count active overrides for header badge
_active_ovr = overrides_module.load()
_n_ovr = len(_active_ovr)

st.html(f"""
<div class="sc-header">
    <div class="sc-brand">
        <span class="sc-icon">◈</span>
        <span class="sc-name">ABASTO</span>
        <span class="sc-tagline"> · Supply Chain Intelligence</span>
    </div>
    <div class="sc-badges">
        <span class="badge {'badge-green' if _model_ok else 'badge-neutral'}">
            {'● CACHÉ' if (_model_ok and _from_cache) else ('● LIVE' if _model_ok else '○ AWAITING RUN')}
        </span>
        <span class="badge badge-blue">AutoETS · IC 70/95%</span>
        {f'<span class="badge badge-neutral">{_info_safe.get("n_skus","?")} SKUs</span>' if _has_data else ''}
        {f'<span class="badge badge-yellow">⚡ {_n_ovr} OVERRIDE(S)</span>' if _n_ovr > 0 else ''}
        <span class="badge badge-neutral">{_today}</span>
    </div>
</div>
""")

if df is None:
    st.html(
        f'<div class="info-box" style="max-width:600px;">'
        f'Select a data source in the sidebar and click <strong>▶ Run Forecast</strong> to begin.'
        f'</div>'
    )
    st.stop()

current_hash = _df_hash(df)
if st.session_state.get("data_hash") != current_hash:
    _clear_results()
    st.session_state["data_hash"] = current_hash

# ─── Run forecast ─────────────────────────────────────────────────────────────
if run_btn or force_btn or "forecast_results" not in st.session_state:
    _has_cache = (not force_btn) and (fc_module.cache_status(df) is not None)
    _spinner   = "Cargando desde caché…" if _has_cache else "Calculando modelo (AutoETS + CV + historial, ~60 s)…"

    with st.spinner(_spinner):
        try:
            results, from_cache = fc_module.get_or_compute(df, force=force_btn)
            st.session_state["forecast_results"] = results
            st.session_state["cache_status"] = {
                "from_cache": from_cache,
                "computed_at": results["computed_at"],
            }
        except Exception as exc:
            st.error(f"Forecast error: {exc}")
            st.stop()

results    = st.session_state["forecast_results"]
forecasts  = results["forecasts"]
metrics    = results["metrics"]
fc_hist    = results["fc_hist"]
ets_params = results.get("ets_params", {})
cv_skipped = results.get("cv_skipped", [])


# ─── Tabs ─────────────────────────────────────────────────────────────────────
tab_fc, tab_acc, tab_hist, tab_sandbox = st.tabs([
    "Forecast",
    "Accuracy",
    "Forecast History",
    "Sandbox",
])


# ══ Tab 1: Forecast ═══════════════════════════════════════════════════════════
with tab_fc:
    col_a, col_b = st.columns([1, 3])
    with col_a:
        vista = st.radio("View", ["By SKU", "By Category"],
                         horizontal=False, key="vista_selector")
    with col_b:
        if vista == "By SKU":
            skus = sorted(df["sku"].unique())
            selected_sku = st.selectbox("SKU", skus, key="sku_selector",
                                        label_visibility="collapsed")
            hist_view   = df[df["sku"] == selected_sku].sort_values("fecha")
            fc_view     = forecasts[forecasts["unique_id"] == selected_sku].copy()
            chart_label = selected_sku
        else:
            categories = sorted({_get_category(s) for s in df["sku"].unique()})
            selected_cat = st.selectbox(
                "Category", categories,
                format_func=lambda c: f"Category {c}",
                key="cat_selector",
                label_visibility="collapsed",
            )
            n_cat = sum(1 for s in df["sku"].unique() if _get_category(s) == selected_cat)
            st.caption(f"{n_cat} SKU(s) · aggregated (sum)")
            hist_view, fc_view = _aggregate_by_category(df, forecasts, selected_cat)
            chart_label = f"Category {selected_cat}"

    if fc_view.empty:
        st.html('<div class="warn-box">No forecast generated for this selection.</div>')
    else:
        # ── Overrides (By SKU only) ───────────────────────────────────────────
        _fc_override: pd.DataFrame | None = None
        _has_ovr = False
        _sku_ovr: dict = {}

        if vista == "By SKU":
            _all_ovr = overrides_module.load()
            _sku_ovr  = _all_ovr.get(selected_sku, {})
            _has_ovr  = bool(_sku_ovr)
            if _has_ovr:
                # Map normalized dates → override values for robust matching
                _ovr_map = {pd.Timestamp(k).normalize(): v for k, v in _sku_ovr.items()}

                # Full effective forecast (original + overrides merged) → KPIs, table
                _fc_eff = fc_view.copy()
                _fc_eff["AutoETS"] = [
                    _ovr_map.get(pd.Timestamp(d).normalize(), orig)
                    for d, orig in zip(_fc_eff["ds"], _fc_eff["AutoETS"])
                ]

                # Chart overlay: full date range, None for non-overridden weeks
                # Plotly conecta puntos consecutivos no-None; None actúa como corte de línea
                _ovr_y = [
                    _ovr_map.get(pd.Timestamp(d).normalize())   # None si no hay override
                    for d in fc_view["ds"]
                ]
                _fc_override = (list(fc_view["ds"]), _ovr_y)   # (x_list, y_list)

        # KPIs use effective forecast (model + overrides merged, no NaNs)
        _fc_for_kpi = _fc_eff if _has_ovr else fc_view
        mean_fc     = _fc_for_kpi["AutoETS"].mean()
        std_fc      = fc_view["AutoETS-std"].mean() if "AutoETS-std" in fc_view.columns else None
        last_4w     = hist_view.tail(4)["cantidad"].mean()
        delta_pct   = (mean_fc - last_4w) / last_4w * 100 if last_4w else 0

        kpi_row(
            dict(label="Historical avg (last 4w)", value=f"{last_4w:.1f}"),
            dict(label="Forecast avg (12w)",       value=f"{mean_fc:.1f}",
                 delta=f"{delta_pct:+.1f}% vs recent",
                 delta_cls="pos" if delta_pct >= 0 else "neg"),
            *([dict(label="Avg uncertainty (std)", value=f"{std_fc:.1f}")] if std_fc else []),
        )

        # Override badge above chart
        if _has_ovr:
            st.html(
                f'<div style="margin-bottom:6px;">'
                f'<span class="badge badge-yellow">⚡ OVERRIDE ACTIVO — {selected_sku}</span>'
                f'</div>'
            )

        fig = build_forecast_chart(hist_view, fc_view, chart_label, fc_override=_fc_override)
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

        with st.expander("FORECAST TABLE"):
            tbl = build_forecast_table(_fc_for_kpi)
            st.dataframe(tbl, use_container_width=True, hide_index=True)

        # ── Override manual (By SKU only) ─────────────────────────────────────
        if vista == "By SKU":
            with st.expander("OVERRIDE MANUAL", expanded=_has_ovr):
                st.html(
                    f'<div style="font-size:11px;color:{C["text_2"]};margin-bottom:12px;line-height:1.6;">'
                    f'Edita la columna <b style="color:{C["text_1"]}">Override</b> para sustituir el '
                    f'forecast del modelo en semanas específicas. Deja vacío para usar el valor del modelo.'
                    f'</div>'
                )

                _editor_df = pd.DataFrame({
                    "semana":          fc_view["ds"].dt.strftime("%Y-%m-%d").values,
                    "forecast_modelo": fc_view["AutoETS"].round(1).values,
                    "override": [
                        float(_sku_ovr[d.strftime("%Y-%m-%d")])
                        if d.strftime("%Y-%m-%d") in _sku_ovr else None
                        for d in fc_view["ds"]
                    ],
                })

                _edited = st.data_editor(
                    _editor_df,
                    column_config={
                        "semana":          st.column_config.TextColumn(
                            "Semana", disabled=True,
                        ),
                        "forecast_modelo": st.column_config.NumberColumn(
                            "Forecast modelo", disabled=True, format="%.1f",
                        ),
                        "override":        st.column_config.NumberColumn(
                            "Override", min_value=0.0, step=0.5, format="%.1f",
                            help="Deja vacío para usar el forecast del modelo",
                        ),
                    },
                    hide_index=True,
                    use_container_width=True,
                    key=f"ovr_editor_{selected_sku}",
                )

                _c1, _c2 = st.columns(2)
                with _c1:
                    if st.button(
                        "✓  APLICAR OVERRIDE",
                        key=f"apply_ovr_{selected_sku}",
                        use_container_width=True,
                    ):
                        _save_rows = fc_view[["ds"]].copy().reset_index(drop=True)
                        _save_rows["override"] = _edited["override"].values
                        overrides_module.set_sku(selected_sku, _save_rows)
                        st.rerun()
                with _c2:
                    if st.button(
                        "✕  LIMPIAR OVERRIDE",
                        key=f"clear_ovr_{selected_sku}",
                        disabled=not _has_ovr,
                        use_container_width=True,
                    ):
                        overrides_module.clear_sku(selected_sku)
                        st.rerun()


# ══ Tab 2: Accuracy ═══════════════════════════════════════════════════════════
with tab_acc:
    if fc_module.PRIMARY in metrics:
        cv_data = results["cv"]

        _H_OPTIONS = {
            "1 semana":   1,
            "4 semanas":  4,
            "8 semanas":  8,
            "12 semanas": 12,
        }
        _h_col, _ = st.columns([2, 5])
        with _h_col:
            _h_label = st.selectbox(
                "Horizonte de evaluación",
                list(_H_OPTIONS.keys()),
                index=3,
                key="acc_horizon",
            )
        _h_max = _H_OPTIONS[_h_label]

        _metrics_h = fc_module.compute_metrics_for_horizon(cv_data, _h_max)
        m  = _metrics_h.get(fc_module.PRIMARY, {})
        sn = _metrics_h.get(fc_module.BENCHMARK, {})

        if not m:
            st.html('<div class="warn-box">Cannot compute metrics for this horizon.</div>')
        else:
            section(f"Global Accuracy — horizonte {_h_label}")
            cards = [
                dict(label="MAPE — AutoETS",  value=f"{m['global_mape']:.1f}%",
                     delta="Mean Absolute Pct Error", delta_cls="neu"),
                dict(label="Bias — AutoETS",  value=f"{m['global_bias']:+.1f}%",
                     delta="+ overestimate · – underestimate", delta_cls="neu"),
            ]
            if sn:
                imp = sn["global_mape"] - m["global_mape"]
                cards += [
                    dict(label="MAPE — SeasonalNaive", value=f"{sn['global_mape']:.1f}%"),
                    dict(label="Improvement vs Naive",  value=f"{imp:+.1f} pp",
                         delta="lower is better for Naive",
                         delta_cls="pos" if imp > 0 else "neg"),
                ]
            kpi_row(*cards)

            section(f"Per-SKU Accuracy — AutoETS · {_h_label}")
            st.html(acc_table_html(m["per_sku"]))
            st.html(
                f'<div style="font-size:10px;color:{C["text_3"]};margin-top:8px;font-family:{C["mono"]};">'
                f'MAPE: &lt;15% GOOD · 15–25% WARN · &gt;25% BAD &nbsp;|&nbsp; '
                f'BIAS: positive = model overestimates</div>'
            )

            if sn:
                with st.expander("AUTOETS VS SEASONALNAIVE — PER SKU"):
                    ets_ps   = m["per_sku"].rename(columns={"MAPE": "MAPE_ETS", "Bias": "Bias_ETS"})
                    naive_ps = sn["per_sku"].rename(columns={"MAPE": "MAPE_Naive", "Bias": "Bias_Naive"})
                    comp     = ets_ps.join(naive_ps)
                    comp["Mejora"] = (comp["MAPE_Naive"] - comp["MAPE_ETS"]).round(2)
                    st.html(comp_table_html(comp))

        if ets_params:
            with st.expander("AUTOETS — MODELO SELECCIONADO POR SKU"):
                st.html(
                    f'<div style="font-size:11px;color:{C["text_3"]};margin-bottom:12px;">'
                    f'Parámetros ETS elegidos automáticamente: '
                    f'<b style="color:{C["text_2"]}">Error · Trend · Seasonality</b> &nbsp;·&nbsp; '
                    f'A=Additive &nbsp; M=Multiplicative &nbsp; N=None &nbsp; d=damped</div>'
                )
                def _ets_interpret(s: str) -> str:
                    import re
                    m = re.search(r"ETS\(([^,]+),([^,]+),([^)]+)\)", s)
                    if not m:
                        return s
                    _e, _t, _sea = m.group(1), m.group(2), m.group(3)
                    parts = []
                    if _sea == "N":
                        parts.append(f'<span style="color:{C["red"]}">sin estacionalidad</span>')
                    else:
                        parts.append(f'<span style="color:{C["green"]}">con estacionalidad ({_sea})</span>')
                    if _t == "N":
                        parts.append("sin tendencia")
                    elif "d" in _t.lower():
                        parts.append("tendencia amortiguada")
                    else:
                        parts.append("con tendencia")
                    return "  ·  ".join(parts)

                _ets_rows = "".join(
                    f'<tr>'
                    f'<td>{sku}</td>'
                    f'<td style="font-family:{C["mono"]};color:{C["blue"]};font-weight:700;">'
                    f'{model_str}</td>'
                    f'<td style="font-size:11px;">{_ets_interpret(model_str)}</td>'
                    f'</tr>'
                    for sku, model_str in sorted(ets_params.items())
                )
                st.html(
                    f'<table class="acc-table">'
                    f'<thead><tr><th>SKU</th><th>Modelo ETS</th><th>Interpretación</th></tr></thead>'
                    f'<tbody>{_ets_rows}</tbody></table>'
                )

        section("MAPE por horizonte — semanas 1 a 12")
        st.html(
            f'<div style="font-size:11px;color:{C["text_3"]};margin:-10px 0 16px 0;">'
            f'El error de forecast crece con el horizonte. '
            f'La línea vertical muestra el horizonte seleccionado arriba.</div>'
        )
        _mape_steps = fc_module.compute_mape_by_step(cv_data)
        if not _mape_steps.empty:
            _fig_mape = go.Figure()
            _colors_mape = {
                fc_module.PRIMARY:   C["blue"],
                fc_module.BENCHMARK: C["text_3"],
            }
            for _model, _grp in _mape_steps.groupby("model"):
                _grp = _grp.sort_values("h")
                _fig_mape.add_trace(go.Scatter(
                    x=_grp["h"], y=_grp["mape"],
                    name=_model, mode="lines+markers",
                    line=dict(color=_colors_mape.get(_model, C["text_2"]), width=2),
                    marker=dict(size=6),
                    hovertemplate="Semana %{x}  <b>%{y:.1f}%</b><extra>" + _model + "</extra>",
                ))
            _fig_mape.add_shape(
                type="line", x0=_h_max, x1=_h_max, y0=0, y1=1,
                xref="x", yref="paper",
                line=dict(color=C["yellow"], width=1, dash="dot"),
            )
            _fig_mape.add_annotation(
                x=_h_max, y=0.96, xref="x", yref="paper",
                text=f"  {_h_label}", showarrow=False,
                xanchor="left", yanchor="top",
                font=dict(color=C["yellow"], size=10, family="Courier New,monospace"),
            )
            _fig_mape.update_layout(
                template="plotly_dark",
                paper_bgcolor=_PBG, plot_bgcolor=_PBG,
                height=300,
                margin=dict(l=0, r=0, t=30, b=0),
                font=dict(color=C["text_2"], family="Inter,sans-serif", size=11),
                hoverlabel=_HOVER,
                hovermode="x unified",
                legend=dict(
                    orientation="h", yanchor="bottom", y=1.01, xanchor="right", x=1,
                    font=dict(size=10, color=C["text_2"]),
                    bgcolor="rgba(0,0,0,0)", borderwidth=0,
                ),
                xaxis=dict(
                    title="Semana del horizonte",
                    showgrid=True, gridcolor=_GRID, zeroline=False,
                    tickmode="linear", tick0=1, dtick=1,
                    tickfont=dict(family="Courier New,monospace", size=10, color=C["text_2"]),
                    title_font=dict(size=10, color=C["text_3"]),
                ),
                yaxis=dict(
                    title="MAPE %",
                    showgrid=True, gridcolor=_GRID, zeroline=False, rangemode="tozero",
                    tickformat=".1f",
                    tickfont=dict(family="Courier New,monospace", size=10, color=C["text_2"]),
                    title_font=dict(size=10, color=C["text_3"]),
                ),
            )
            st.plotly_chart(_fig_mape, use_container_width=True,
                            config={"displayModeBar": False})
    else:
        _skip_msg = (
            f'Series sin suficiente historial para CV: '
            f'<b>{", ".join(sorted(cv_skipped))}</b>. '
            if cv_skipped else ""
        )
        st.html(
            f'<div class="warn-box">'
            f'No hay métricas de accuracy — historial insuficiente para validación cruzada. '
            f'{_skip_msg}'
            f'Se necesitan al menos <b>HORIZON×2 + min_train</b> semanas por serie.'
            f'</div>'
        )


# ══ Tab 3: Forecast History ═══════════════════════════════════════════════════
with tab_hist:
    section("Forecast History — last 8 weeks")
    st.html(
        f'<div style="font-size:11px;color:{C["text_3"]};margin:-10px 0 20px 0;">'
        f'Each run covers a 12-week horizon. Green/red dots show whether actual demand '
        f'fell inside or outside the 70% CI.</div>'
    )

    if fc_hist.empty:
        st.html('<div class="warn-box">Cannot generate history — insufficient data.</div>')
    else:
        col_a2, col_b2 = st.columns([1, 3])
        with col_a2:
            vista_h = st.radio("View", ["By SKU", "By Category"],
                               horizontal=False, key="vista_hist")
        with col_b2:
            if vista_h == "By SKU":
                sel_h = st.selectbox("SKU", sorted(df["sku"].unique()),
                                     key="hist_sku_sel", label_visibility="collapsed")
                fc_hist_view = fc_hist[fc_hist["unique_id"] == sel_h].copy()
                hist_view_h  = df[df["sku"] == sel_h].sort_values("fecha")
                label_h = sel_h
            else:
                cats_h = sorted({_get_category(s) for s in df["sku"].unique()})
                sel_cat_h = st.selectbox(
                    "Category", cats_h,
                    format_func=lambda c: f"Category {c}",
                    key="hist_cat_sel", label_visibility="collapsed",
                )
                cat_skus_h = [s for s in df["sku"].unique() if _get_category(s) == sel_cat_h]
                num_cols_h = [c for c in fc_hist.columns
                              if c not in ("unique_id", "ds", "run_date", "index")]
                fc_hist_view = (fc_hist[fc_hist["unique_id"].isin(cat_skus_h)]
                                .groupby(["run_date", "ds"], as_index=False)[num_cols_h].sum())
                hist_view_h, _ = _aggregate_by_category(df, forecasts, sel_cat_h)
                label_h = f"Category {sel_cat_h}"

        run_dates = sorted(fc_hist_view["run_date"].unique(), reverse=True)
        sel_run   = st.selectbox(
            "Forecast run date",
            run_dates,
            format_func=lambda d: pd.Timestamp(d).strftime("%Y-%m-%d"),
            key="hist_run_date",
        )
        fc_sel = fc_hist_view[fc_hist_view["run_date"] == sel_run].copy()

        last_hist_date = hist_view_h["fecha"].max()
        overlap = fc_sel[fc_sel["ds"] <= last_hist_date].merge(
            hist_view_h.rename(columns={"fecha": "ds"})[["ds", "cantidad"]],
            on="ds", how="inner",
        )
        overlap = overlap[overlap["cantidad"] > 0]

        if overlap.empty:
            st.html(
                '<div class="info-box">This is the most recent forecast — '
                'no actual demand available yet for comparison.</div>'
            )
        else:
            overlap["ape"] = np.abs(overlap["cantidad"] - overlap["AutoETS"]) / overlap["cantidad"]
            overlap["pe"]  = (overlap["AutoETS"] - overlap["cantidad"]) / overlap["cantidad"]
            n_in = 0
            if "AutoETS-lo-70" in overlap.columns:
                n_in = ((overlap["cantidad"] >= overlap["AutoETS-lo-70"]) &
                        (overlap["cantidad"] <= overlap["AutoETS-hi-70"])).sum()

            mape_v = overlap["ape"].mean() * 100
            bias_v = overlap["pe"].mean() * 100
            kpi_row(
                dict(label="Weeks with actuals",    value=str(len(overlap))),
                dict(label="MAPE (realized weeks)", value=f"{mape_v:.1f}%",
                     delta_cls="good" if mape_v < 15 else ("warn" if mape_v < 25 else "neg")),
                dict(label="Bias (realized weeks)", value=f"{bias_v:+.1f}%",
                     delta="+ overestimate · – underestimate", delta_cls="neu"),
                dict(label="Inside IC 70%",         value=f"{n_in} / {len(overlap)}",
                     delta_cls="pos" if n_in == len(overlap) else "neu"),
            )

        fig_h = build_forecast_history_chart(hist_view_h, fc_sel, label_h, sel_run)
        st.plotly_chart(fig_h, use_container_width=True, config={"displayModeBar": False})

        st.html(
            f'<div style="font-size:10px;color:{C["text_3"]};font-family:{C["mono"]};">'
            f'● GREEN = actual within IC 70% &nbsp;·&nbsp; '
            f'● RED = actual outside IC 70% &nbsp;·&nbsp; '
            f'Blue dashed line = model run date</div>'
        )


# ══ Tab 4: Sandbox ════════════════════════════════════════════════════════════
with tab_sandbox:
    section("Live Demo Sandbox")
    st.html(
        f'<div class="info-box">Ingresa hasta 8 semanas de demanda y pulsa '
        f'<strong>▶ Calcular Forecast</strong>. La última fila corresponde a la semana '
        f'pasada; el forecast arranca esta semana.</div>'
    )
    st.markdown("<br>", unsafe_allow_html=True)

    col_ed, col_res = st.columns([1, 2])

    with col_ed:
        section("Demanda histórica")
        _sb_today      = pd.Timestamp.now().normalize()
        _sb_this_mon   = _sb_today - pd.Timedelta(days=int(_sb_today.weekday()))
        _sb_last_mon   = _sb_this_mon - pd.Timedelta(weeks=1)
        _sb_dates      = [_sb_last_mon - pd.Timedelta(weeks=7 - i) for i in range(8)]
        _default_sandbox = pd.DataFrame({
            "fecha":    _sb_dates,
            "cantidad": [None] * 8,
        })
        edited_sandbox = st.data_editor(
            _default_sandbox,
            column_config={
                "fecha": st.column_config.DateColumn(
                    "Semana", disabled=True, format="DD MMM YYYY",
                ),
                "cantidad": st.column_config.NumberColumn(
                    "Cantidad", min_value=0.0, step=1.0, format="%.0f",
                ),
            },
            hide_index=True,
            use_container_width=True,
            num_rows="fixed",
            key="sandbox_editor",
        )

        n_filled = int(edited_sandbox["cantidad"].notna().sum())
        st.caption(f"{n_filled} / 8 semanas con datos · mínimo 4 para correr modelo")

        run_sandbox = st.button(
            "▶  Calcular Forecast",
            disabled=(n_filled < 4),
            use_container_width=True,
            key="sandbox_btn",
        )

    with col_res:
        if run_sandbox:
            with st.spinner("Corriendo modelo…"):
                try:
                    hist_sb, fc_sb, mape_sb, bias_sb, minfo_sb = fc_module.run_sandbox_forecast(
                        edited_sandbox
                    )
                    st.session_state["sandbox_results"] = dict(
                        hist=hist_sb, fc=fc_sb, mape=mape_sb, bias=bias_sb,
                        n=n_filled, minfo=minfo_sb, error=None,
                    )
                except ValueError as exc:
                    st.session_state["sandbox_results"] = dict(
                        hist=None, fc=None, mape=None, bias=None,
                        n=n_filled, minfo=None, error=str(exc),
                    )

        if "sandbox_results" in st.session_state:
            sr       = st.session_state["sandbox_results"]
            hist_sb  = sr["hist"]
            fc_sb    = sr["fc"]
            mape_sb  = sr["mape"]
            bias_sb  = sr["bias"]
            n_sb     = sr["n"]
            minfo_sb = sr.get("minfo")
            sb_error = sr.get("error")

            if sb_error:
                st.html(f'<div class="warn-box">✗ {sb_error}</div>')
            elif fc_sb is None or fc_sb.empty:
                st.html(
                    '<div class="warn-box">No se pudo generar el forecast. '
                    'Verifica que haya al menos 4 semanas con datos.</div>'
                )
            else:
                if mape_sb is not None:
                    kpi_row(
                        dict(label="Semanas de historial", value=str(n_sb)),
                        dict(label="MAPE (holdout 4 sem.)", value=f"{mape_sb:.1f}%",
                             delta_cls="pos" if mape_sb < 15 else ("neu" if mape_sb < 25 else "neg")),
                        dict(label="Bias (holdout 4 sem.)", value=f"{bias_sb:+.1f}%",
                             delta="+ sobreestima · – subestima", delta_cls="neu"),
                    )
                else:
                    kpi_row(
                        dict(label="Semanas de historial", value=str(n_sb)),
                        dict(label="MAPE / Bias", value="—",
                             delta="Ingresa ≥16 semanas para ver métricas", delta_cls="neu"),
                    )

                fig_sb = _build_sandbox_chart(hist_sb, fc_sb, minfo_sb.name if minfo_sb else "AutoETS")
                st.plotly_chart(fig_sb, use_container_width=True,
                                config={"displayModeBar": False})

                if minfo_sb:
                    st.html(
                        f'<div class="info-box" style="margin-top:4px;">'
                        f'<span style="color:{C["text_1"]};font-weight:700;">'
                        f'Modelo: {minfo_sb.name}</span>'
                        f'<span style="color:{C["text_3"]}"> · </span>'
                        f'{minfo_sb.reason}</div>'
                    )
        else:
            st.html(
                f'<div style="display:flex;align-items:center;justify-content:center;'
                f'height:320px;color:{C["text_3"]};font-family:{C["mono"]};font-size:11px;'
                f'letter-spacing:0.08em;">INGRESA DATOS Y PULSA ▶ CALCULAR FORECAST</div>'
            )


# ─── Footer ───────────────────────────────────────────────────────────────────
st.html(
    f'<div style="border-top:1px solid {C["border"]};margin-top:32px;padding-top:12px;'
    f'font-size:10px;color:{C["text_3"]};font-family:{C["mono"]};letter-spacing:0.06em;">'
    f'ABASTO · PHASE 1 · AutoETS (statsforecast {__import__("statsforecast").__version__}) · '
    f'Streamlit · {_today}'
    f'</div>'
)

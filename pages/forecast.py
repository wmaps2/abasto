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


def _wfmt(d) -> str:
    ts = pd.Timestamp(d)
    return f"W{ts.isocalendar().week:02d} ({ts.strftime('%d-%m-%Y')})"


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
        hovertemplate="%{x|W%W (%d-%m-%Y)}  <b>%{y:.1f}</b><extra>Histórico</extra>",
    ))

    ds = list(fc["ds"])
    if "AutoETS-lo-95" in fc.columns:
        _ci_band(fig, ds, [max(0.0, v) for v in fc["AutoETS-lo-95"]], list(fc["AutoETS-hi-95"]),
                 "IC 95 %", "rgba(79,143,247,0.07)")
    if "AutoETS-lo-70" in fc.columns:
        _ci_band(fig, ds, [max(0.0, v) for v in fc["AutoETS-lo-70"]], list(fc["AutoETS-hi-70"]),
                 "IC 70 %", "rgba(79,143,247,0.18)")

    # Anchor: prepend last historical point so forecast line connects without gap
    _last_hist = hist.sort_values("fecha").iloc[-1]
    _fc_anchor_x = [_last_hist["fecha"]] + list(fc["ds"])
    _fc_anchor_y = [float(_last_hist["cantidad"])] + list(fc["AutoETS"].clip(lower=0))

    # Forecast original del modelo (siempre azul punteado cuando hay override activo)
    original_name = "Forecast modelo (original)" if fc_override is not None else "Forecast (AutoETS)"  # names kept
    fig.add_trace(go.Scatter(
        x=_fc_anchor_x, y=_fc_anchor_y,
        name=original_name, mode="lines",
        line=dict(color=C["blue"], width=2, dash="dash"),
        hovertemplate="%{x|W%W (%d-%m-%Y)}  <b>%{y:.1f}</b><extra>Forecast modelo</extra>",
    ))

    # Forecast con override: línea verde solo entre semanas consecutivas con override
    if fc_override is not None:
        _ovr_x, _ovr_y = fc_override
        fig.add_trace(go.Scatter(
            x=_ovr_x, y=_ovr_y,
            name="Forecast con ajuste", mode="lines+markers",
            connectgaps=False,
            line=dict(color=C["green"], width=2.5),
            marker=dict(color=C["green"], size=9, symbol="circle",
                        line=dict(color=C["bg_card"], width=1.5)),
            hovertemplate="%{x|W%W (%d-%m-%Y)}  <b>%{y:.1f}</b><extra>Ajuste</extra>",
        ))

    if "SeasonalNaive" in fc.columns:
        fig.add_trace(go.Scatter(
            x=fc["ds"], y=fc["SeasonalNaive"].clip(lower=0),
            name="Naive estacional", mode="lines",
            line=dict(color=C["text_3"], width=1, dash="dot"),
            visible="legendonly",
            hovertemplate="%{x|W%W (%d-%m-%Y)}  <b>%{y:.1f}</b><extra>Naive</extra>",
        ))

    _hist_max = hist["fecha"].dropna().max() if not hist.empty else None
    _fc_max   = fc["ds"].dropna().max()    if not fc.empty  else None
    if _hist_max is not None and pd.notna(_hist_max):
        last_str = _hist_max.strftime("%Y-%m-%d")
        _vline(fig, last_str, C["text_3"], "Inicio forecast")
    else:
        last_str = None

    _x_start_ts = (_hist_max - pd.Timedelta(weeks=12)) if _hist_max is not None and pd.notna(_hist_max) else None
    x_start = _x_start_ts.strftime("%Y-%m-%d") if _x_start_ts is not None else None
    x_end   = _fc_max.strftime("%Y-%m-%d") if _fc_max is not None and pd.notna(_fc_max) else None

    fig = _dark_layout(
        fig,
        title=f"<b style='color:{C['text_1']}'>{label}</b>"
              f"<span style='color:{C['text_3']};font-size:12px'> · Histórico + Forecast 12 semanas</span>",
        x_range=[x_start, x_end],
    )
    fig.update_xaxes(tickformat="W%W\n(%d-%m-%Y)")
    fig.update_yaxes(rangemode="nonnegative")
    return fig


def build_forecast_history_chart(
    hist: pd.DataFrame, fc: pd.DataFrame, label: str, run_date: pd.Timestamp,
) -> go.Figure:
    fig = go.Figure()
    last_hist = hist["fecha"].max()

    fig.add_trace(go.Scatter(
        x=hist["fecha"], y=hist["cantidad"],
        name="Venta real", mode="lines",
        line=dict(color=C["text_2"], width=1.5),
        hovertemplate="%{x|W%W (%d-%m-%Y)}  <b>%{y:.1f}</b><extra>Real</extra>",
    ))

    ds = list(fc["ds"])
    if "AutoETS-lo-95" in fc.columns:
        _ci_band(fig, ds, [max(0.0, v) for v in fc["AutoETS-lo-95"]], list(fc["AutoETS-hi-95"]),
                 "IC 95 %", "rgba(79,143,247,0.07)")
    if "AutoETS-lo-70" in fc.columns:
        _ci_band(fig, ds, [max(0.0, v) for v in fc["AutoETS-lo-70"]], list(fc["AutoETS-hi-70"]),
                 "IC 70 %", "rgba(79,143,247,0.18)")

    fig.add_trace(go.Scatter(
        x=fc["ds"], y=fc["AutoETS"].clip(lower=0),
        name="Forecast", mode="lines",
        line=dict(color=C["blue"], width=2, dash="dash"),
        hovertemplate="%{x|W%W (%d-%m-%Y)}  <b>%{y:.1f}</b><extra>Forecast</extra>",
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
    last_str = last_hist.strftime("%Y-%m-%d") if pd.notna(last_hist) else run_str
    _vline(fig, run_str, C["blue"], "Fecha del forecast")
    if run_str != last_str:
        _vline(fig, last_str, C["text_3"], "Último dato", y_label=0.82)

    x_start = (pd.Timestamp(run_date) - pd.Timedelta(weeks=8)).strftime("%Y-%m-%d")
    _fc_max2 = fc["ds"].dropna().max() if not fc.empty else None
    x_end   = _fc_max2.strftime("%Y-%m-%d") if _fc_max2 is not None and pd.notna(_fc_max2) else run_str

    fig = _dark_layout(
        fig,
        title=f"<b style='color:{C['text_1']}'>{label}</b>"
              f"<span style='color:{C['text_3']};font-size:12px'> · Forecast del {run_str}</span>",
        x_range=[x_start, x_end],
    )
    fig.update_xaxes(tickformat="W%W\n(%d-%m-%Y)")
    fig.update_yaxes(rangemode="nonnegative")
    return fig


def build_forecast_table(fc: pd.DataFrame, override_mask: list | None = None) -> pd.DataFrame:
    cols, renames = ["ds", "AutoETS"], {"ds": "SEMANA", "AutoETS": "MEDIA"}
    ic_col_names: list[str] = []
    if "AutoETS-std" in fc.columns:
        cols.append("AutoETS-std"); renames["AutoETS-std"] = "STD"
        ic_col_names.append("STD")
    for band in ["70", "95"]:
        lo, hi = f"AutoETS-lo-{band}", f"AutoETS-hi-{band}"
        if lo in fc.columns:
            cols += [lo, hi]; renames[lo] = f"IC{band}% LO"; renames[hi] = f"IC{band}% HI"
            ic_col_names += [f"IC{band}% LO", f"IC{band}% HI"]
    tbl = fc[cols].rename(columns=renames).copy()
    tbl["SEMANA"] = tbl["SEMANA"].dt.strftime("%Y-%m-%d")
    num = [c for c in tbl.columns if c != "SEMANA"]
    tbl[num] = tbl[num].round(1)
    if override_mask is not None and ic_col_names:
        for i, has_ovr in enumerate(override_mask):
            if has_ovr:
                for col in ic_col_names:
                    if col in tbl.columns:
                        tbl.at[i, col] = float("nan")
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
        _ci_band(fig, ds, list(fc["AutoETS-lo-95"].clip(lower=0)), list(fc["AutoETS-hi-95"]),
                 "IC 95 %", "rgba(79,143,247,0.07)")
    if "AutoETS-lo-70" in fc.columns:
        _ci_band(fig, ds, list(fc["AutoETS-lo-70"].clip(lower=0)), list(fc["AutoETS-hi-70"]),
                 "IC 70 %", "rgba(79,143,247,0.18)")
    fig.add_trace(go.Scatter(
        x=fc["ds"], y=fc["AutoETS"].clip(lower=0),
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


@st.cache_data(ttl=300)
def _load_all_sb_dates() -> list[str]:
    """All unique forecast run dates in Supabase, newest first."""
    try:
        sb = fc_module._sb_client()
        rows = sb.table("forecasts").select("fecha_calculo").execute().data
        return sorted({r["fecha_calculo"][:10] for r in rows}, reverse=True)
    except Exception:
        return []


@st.cache_data(ttl=120, show_spinner=False)
def _load_sku_cat_map(fuente: str) -> dict[str, str]:
    try:
        prods = data_module.get_productos()
        if "fuente" in prods.columns:
            prods = prods[prods["fuente"] == fuente]
        return {row["sku"]: str(row.get("categoria", "?"))[:1].upper() or "?"
                for _, row in prods.iterrows()}
    except Exception:
        return {}


@st.cache_data(ttl=300)
def _load_fc_run(date_str: str) -> pd.DataFrame:
    """Load all SKUs + horizons for one run date from Supabase (includes horizonte col)."""
    try:
        sb = fc_module._sb_client()
        rows = (sb.table("forecasts")
                  .select("*")
                  .gte("fecha_calculo", date_str + "T00:00:00")
                  .lte("fecha_calculo", date_str + "T23:59:59")
                  .execute().data)
        if not rows:
            return pd.DataFrame()
        fc = pd.DataFrame(rows)
        fc["ds"] = pd.to_datetime(fc["fecha_target"])
        fc = fc.rename(columns={
            "sku_id":      "unique_id",
            "valor":       "AutoETS",
            "ic_70_lower": "AutoETS-lo-70",
            "ic_70_upper": "AutoETS-hi-70",
            "ic_95_lower": "AutoETS-lo-95",
            "ic_95_upper": "AutoETS-hi-95",
        })
        keep = ["unique_id", "ds", "horizonte", "AutoETS",
                "AutoETS-lo-70", "AutoETS-hi-70",
                "AutoETS-lo-95", "AutoETS-hi-95"]
        return fc[[c for c in keep if c in fc.columns]].sort_values(["unique_id", "ds"]).reset_index(drop=True)
    except Exception:
        return pd.DataFrame()


# ─── Sidebar rendered globally by app.py ────────────────────────────────────

# ─── Main ─────────────────────────────────────────────────────────────────────
df = st.session_state.get("df")

_today      = pd.Timestamp.now().strftime("%Y-%m-%d %H:%M")
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
            {'● CACHÉ' if (_model_ok and _from_cache) else ('● LIVE' if _model_ok else '○ CALCULANDO')}
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
        f'Selecciona una fuente de datos en el sidebar para comenzar.'
        f'</div>'
    )
    st.stop()

_fuente = st.session_state.get("data_source", "demo")
_sku_cat_map = _load_sku_cat_map(_fuente)
_get_category = lambda s: _sku_cat_map.get(s, "?")  # noqa: E731

current_hash = _df_hash(df)
if st.session_state.get("data_hash") != current_hash:
    _clear_results()
    st.session_state["data_hash"] = current_hash

# ─── Run forecast (automático) ────────────────────────────────────────────────
if "forecast_results" not in st.session_state:
    _has_cache = fc_module.cache_status(df) is not None
    _spinner   = "Cargando forecast de Supabase…" if _has_cache else "Calculando modelo (AutoETS, ~60 s)…"

    with st.spinner(_spinner):
        try:
            results, from_cache = fc_module.get_or_compute(df)
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


# ─── Shared view state (synced across tabs via session_state) ────────────────
_VIEW_OPTS = ["Por SKU", "Por Categoría", "Todos"]
_all_skus  = sorted(df["sku"].unique())
_all_cats  = sorted({_get_category(s) for s in df["sku"].unique()} - {"?"})
if "_shared_view" not in st.session_state:
    st.session_state["_shared_view"] = "Por SKU"
if "_shared_sku" not in st.session_state:
    st.session_state["_shared_sku"] = _all_skus[0]
if "_shared_cat" not in st.session_state:
    st.session_state["_shared_cat"] = _all_cats[0]

# ─── Navigation ───────────────────────────────────────────────────────────────
_tab_fc, _tab_mp, _tab_sb = st.tabs(["Forecast", "Rendimiento del modelo", "Simulador"])

# ══ Tab 1: Forecast ═══════════════════════════════════════════════════════════
with _tab_fc:
    col_a, col_b = st.columns([3, 2])
    with col_a:
        vista = st.radio("Vista", _VIEW_OPTS,
                         index=_VIEW_OPTS.index(st.session_state["_shared_view"]),
                         horizontal=True, key="forecast_view")
    st.session_state["_shared_view"] = vista
    with col_b:
        if vista == "Por SKU":
            _fc_sku_idx = _all_skus.index(st.session_state["_shared_sku"]) \
                          if st.session_state["_shared_sku"] in _all_skus else 0
            selected_sku = st.selectbox("SKU", _all_skus, index=_fc_sku_idx,
                                        key="forecast_sku",
                                        label_visibility="collapsed")
            st.session_state["_shared_sku"] = selected_sku
        elif vista == "Por Categoría":
            _fc_cat_idx = _all_cats.index(st.session_state["_shared_cat"]) \
                          if st.session_state["_shared_cat"] in _all_cats else 0
            selected_cat = st.selectbox(
                "Categoría", _all_cats, index=_fc_cat_idx,
                format_func=lambda c: f"Categoría {c}",
                key="forecast_cat",
                label_visibility="collapsed",
            )
            st.session_state["_shared_cat"] = selected_cat

    if vista == "Todos":
        hist_view   = df.copy()
        fc_view     = forecasts.copy()
        chart_label = "Todos los SKUs"
        # agregar todos los SKUs
        hist_view = (hist_view.groupby("fecha", as_index=False)["cantidad"].sum()
                     .assign(sku="ALL").sort_values("fecha"))
        fc_cols = ["ds", "AutoETS", "AutoETS-lo-70", "AutoETS-hi-70",
                   "AutoETS-lo-95", "AutoETS-hi-95"]
        _fc_agg = fc_view.copy()
        for col in fc_cols[1:]:
            if col not in _fc_agg.columns:
                _fc_agg[col] = None
        fc_view = (_fc_agg.groupby("ds", as_index=False)[fc_cols[1:]].sum()
                   .assign(unique_id="ALL").sort_values("ds"))
    elif vista == "Por SKU":
        selected_sku = st.session_state["_shared_sku"]
        hist_view   = df[df["sku"] == selected_sku].sort_values("fecha")
        fc_view     = forecasts[forecasts["unique_id"] == selected_sku].copy()
        chart_label = selected_sku
    else:
        selected_cat = st.session_state["_shared_cat"]
        n_cat = sum(1 for s in df["sku"].unique() if _get_category(s) == selected_cat)
        st.caption(f"{n_cat} SKU(s) · aggregated (sum)")
        hist_view, fc_view = _aggregate_by_category(df, forecasts, selected_cat)
        chart_label = f"Categoría {selected_cat}"

    if fc_view.empty:
        st.html('<div class="warn-box">Sin forecast para esta selección.</div>')
    else:
        # ── Overrides (By SKU only) ───────────────────────────────────────────
        _fc_override: pd.DataFrame | None = None
        _has_ovr = False
        _sku_ovr: dict = {}

        if vista == "Por SKU":
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
            dict(label="Promedio histórico (últ. 4 sem.)", value=f"{last_4w:.1f}"),
            dict(label="Promedio forecast (12 sem.)",      value=f"{mean_fc:.1f}",
                 delta=f"{delta_pct:+.1f}% vs reciente",
                 delta_cls="pos" if delta_pct >= 0 else "neg"),
            *([dict(label="Incertidumbre promedio (std)", value=f"{std_fc:.1f}")] if std_fc else []),
        )

        # Override badge above chart
        if _has_ovr:
            st.html(
                f'<div style="margin-bottom:6px;">'
                f'<span class="badge badge-yellow">⚡ AJUSTE ACTIVO — {selected_sku}</span>'
                f'</div>'
            )

        fig = build_forecast_chart(hist_view, fc_view, chart_label, fc_override=_fc_override)
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

        with st.expander("TABLA DE FORECAST"):
            _ovr_mask = None
            if _has_ovr:
                _ovr_mask = [pd.Timestamp(d).normalize() in _ovr_map for d in _fc_for_kpi["ds"]]
            tbl = build_forecast_table(_fc_for_kpi, override_mask=_ovr_mask)
            st.dataframe(tbl, use_container_width=True, hide_index=True)
            if _has_ovr:
                st.caption("— IC no aplica para semanas con valor fijado manualmente")

        # ── Override manual (By SKU only) ─────────────────────────────────────
        if vista == "Por SKU":
            with st.expander("AJUSTE MANUAL", expanded=_has_ovr):
                st.html(
                    f'<div style="font-size:11px;color:{C["text_2"]};margin-bottom:12px;line-height:1.6;">'
                    f'Edita la columna <b style="color:{C["text_1"]}">Ajuste</b> para sustituir el '
                    f'forecast del modelo en semanas específicas. Deja vacío para usar el valor del modelo.'
                    f'</div>'
                )

                _editor_df = pd.DataFrame({
                    "semana":          fc_view["ds"].dt.strftime("%Y-%m-%d").values,
                    "forecast_modelo": fc_view["AutoETS"].round(1).values,
                    "ajuste": [
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
                        "ajuste":          st.column_config.NumberColumn(
                            "Ajuste", min_value=0.0, step=0.5, format="%.1f",
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
                        "✓  APLICAR AJUSTE",
                        key=f"apply_ovr_{selected_sku}",
                        use_container_width=True,
                    ):
                        _save_rows = fc_view[["ds"]].copy().reset_index(drop=True)
                        _save_rows["override"] = _edited["ajuste"].values
                        _n_mod = int(_edited["ajuste"].notna().sum())
                        overrides_module.set_sku(selected_sku, _save_rows)
                        st.toast(f"✓ Ajuste aplicado a {selected_sku} ({_n_mod} semanas modificadas)", icon="✅")
                        st.rerun()
                with _c2:
                    _clear_clicked = st.button(
                        "✕  LIMPIAR AJUSTE",
                        key=f"clear_ovr_{selected_sku}",
                        disabled=not _has_ovr,
                        use_container_width=True,
                    )
                    if _clear_clicked:
                        st.session_state[f"confirm_clear_{selected_sku}"] = True

                if st.session_state.get(f"confirm_clear_{selected_sku}"):
                    st.warning(f"¿Eliminar ajuste de {selected_sku}? Esta acción no se puede deshacer.")
                    _cc1, _cc2 = st.columns(2)
                    with _cc1:
                        if st.button("Sí, eliminar", key=f"confirm_yes_{selected_sku}", use_container_width=True):
                            overrides_module.clear_sku(selected_sku)
                            st.session_state.pop(f"confirm_clear_{selected_sku}", None)
                            st.rerun()
                    with _cc2:
                        if st.button("Cancelar", key=f"confirm_no_{selected_sku}", use_container_width=True):
                            st.session_state.pop(f"confirm_clear_{selected_sku}", None)
                            st.rerun()


# ══ Tab 2: Model Performance ══════════════════════════════════════════════════
with _tab_mp:

    # ── Controls ─────────────────────────────────────────────────────────────
    # ── Row 1: View radio + conditional SKU/Category dropdown ────────────────
    _r1_view, _r1_filter, _r1_pad = st.columns([3, 2, 2])
    with _r1_view:
        _pv = st.radio(
            "Vista", _VIEW_OPTS,
            index=_VIEW_OPTS.index(st.session_state["_shared_view"]),
            horizontal=True, key="model_perf_view",
        )
    st.session_state["_shared_view"] = _pv
    with _r1_filter:
        if _pv == "Por SKU":
            st.html('<div style="height:28px"></div>')
            _mp_sku_idx = _all_skus.index(st.session_state["_shared_sku"]) \
                          if st.session_state["_shared_sku"] in _all_skus else 0
            _pv_sku = st.selectbox(
                "SKU", _all_skus, index=_mp_sku_idx,
                key="model_perf_sku", label_visibility="collapsed",
            )
            st.session_state["_shared_sku"] = _pv_sku
        elif _pv == "Por Categoría":
            st.html('<div style="height:28px"></div>')
            _mp_cat_idx = _all_cats.index(st.session_state["_shared_cat"]) \
                          if st.session_state["_shared_cat"] in _all_cats else 0
            _pv_cat = st.selectbox(
                "Categoría", _all_cats, index=_mp_cat_idx,
                format_func=lambda c: f"Categoría {c}",
                key="model_perf_cat", label_visibility="collapsed",
            )
            st.session_state["_shared_cat"] = _pv_cat

    # Available run dates: Supabase first, then local fc_hist fallback
    _p_sb_dates = _load_all_sb_dates()
    _p_local_dates: list[str] = []
    if not fc_hist.empty and "run_date" in fc_hist.columns:
        _p_local_dates = sorted(
            {str(d)[:10] for d in fc_hist["run_date"].unique()}, reverse=True
        )
    _p_sb_set    = set(_p_sb_dates)
    _p_all_dates = _p_sb_dates + [d for d in _p_local_dates if d not in _p_sb_set]

    # ── Backfill prompt when no / insufficient historical forecasts ───────────
    if not _p_all_dates or len(_p_all_dates) < 5:
        st.info("ℹ️ Forecasts históricos pendientes para análisis de accuracy.")
        if st.button("📊 Generar forecasts históricos (~2 min)",
                     key="_btn_backfill_mp", use_container_width=False):
            with st.spinner("Generando forecasts históricos para todos los SKUs…"):
                from simulation import backfill_forecasts
                backfill_forecasts.main(n_weeks=24)
            _load_all_sb_dates.clear()
            _load_fc_run.clear()
            st.toast("✓ Forecasts históricos generados", icon="✅")
            st.rerun()

    # ── Row 2: Forecast run date dropdown ─────────────────────────────────────
    _r2_date, _r2_pad = st.columns([3, 4])
    with _r2_date:
        if not _p_all_dates:
            _p_run = None
        else:
            _p_run = st.selectbox(
                "Fecha de ejecución", _p_all_dates,
                index=len(_p_all_dates) - 1,
                format_func=_wfmt,
                key="perf_run_date",
            )

    if _p_run is not None:
        # ── Load forecast data for selected run date ──────────────────────────
        if _p_run in _p_sb_set:
            _fc_run = _load_fc_run(_p_run)
        else:
            _lrd_p = pd.Timestamp(_p_run)
            _fc_run = fc_hist[
                pd.to_datetime(fc_hist["run_date"]).dt.normalize() == _lrd_p
            ].copy()
            if not _fc_run.empty and "horizonte" not in _fc_run.columns:
                _fc_run["horizonte"] = (
                    (_fc_run["ds"] - _lrd_p).dt.days / 7
                ).round().astype(int)

        if _fc_run.empty:
            st.html('<div class="info-box">No hay datos para esta fecha de ejecucion.</div>')
        else:
            # ── Build view-specific fc + hist ─────────────────────────────────
            _p_num_cols = [c for c in _fc_run.columns
                           if c not in ("unique_id", "ds", "horizonte")]

            if _pv == "Por SKU":
                _fc_view = _fc_run[_fc_run["unique_id"] == _pv_sku].copy()
                _hist_view = df[df["sku"] == _pv_sku][["fecha", "cantidad"]].copy()
                _chart_lbl = _pv_sku
            elif _pv == "Por Categoría":
                _cat_skus = [s for s in df["sku"].unique()
                             if _get_category(s) == _pv_cat]
                _grp_cols = (["ds", "horizonte"] if "horizonte" in _fc_run.columns
                             else ["ds"])
                _fc_view = (_fc_run[_fc_run["unique_id"].isin(_cat_skus)]
                            .groupby(_grp_cols, as_index=False)[_p_num_cols].sum())
                _fc_view["unique_id"] = f"Categoría {_pv_cat}"
                _hist_view = (df[df["sku"].isin(_cat_skus)]
                              .groupby("fecha", as_index=False)["cantidad"].sum())
                _chart_lbl = f"Categoría {_pv_cat}"
            else:  # Todos
                _grp_cols_a = (["ds", "horizonte"] if "horizonte" in _fc_run.columns
                               else ["ds"])
                _fc_view = _fc_run.groupby(_grp_cols_a, as_index=False)[_p_num_cols].sum()
                _fc_view["unique_id"] = "Todos los SKUs"
                _hist_view = df.groupby("fecha", as_index=False)["cantidad"].sum()
                _chart_lbl = "Todos los SKUs"

            # ── Compute overlap: forecast vs actuals ──────────────────────────
            _p_overlap = _fc_view.merge(
                _hist_view.rename(columns={"fecha": "ds"})[["ds", "cantidad"]],
                on="ds", how="inner",
            )
            _p_overlap = _p_overlap[_p_overlap["cantidad"] > 0].copy()
            _has_overlap = not _p_overlap.empty

            if _has_overlap:
                _p_overlap["ape"] = (
                    np.abs(_p_overlap["cantidad"] - _p_overlap["AutoETS"])
                    / _p_overlap["cantidad"]
                )
                _p_overlap["pe"] = (
                    (_p_overlap["AutoETS"] - _p_overlap["cantidad"])
                    / _p_overlap["cantidad"]
                )

            def _mh(h: int | None = None) -> str:
                if not _has_overlap:
                    return "—"
                sub = (_p_overlap[_p_overlap["horizonte"] <= h]
                       if h and "horizonte" in _p_overlap.columns
                       else _p_overlap)
                return f"{sub['ape'].mean() * 100:.1f}%" if not sub.empty else "—"

            def _bh(h: int | None = None) -> str:
                if not _has_overlap:
                    return "—"
                sub = (_p_overlap[_p_overlap["horizonte"] <= h]
                       if h and "horizonte" in _p_overlap.columns
                       else _p_overlap)
                return f"{sub['pe'].mean() * 100:+.1f}%" if not sub.empty else "—"

            _p_n_in, _p_n_tot = 0, len(_p_overlap)
            if _has_overlap and "AutoETS-lo-70" in _p_overlap.columns:
                _p_n_in = int(
                    ((_p_overlap["cantidad"] >= _p_overlap["AutoETS-lo-70"]) &
                     (_p_overlap["cantidad"] <= _p_overlap["AutoETS-hi-70"])).sum()
                )

            # ── Section 1: Overview KPI cards ─────────────────────────────────
            section(f"Resumen — ejecución: {_wfmt(_p_run)}  ·  {_chart_lbl}")
            kpi_row(
                dict(label="MAPE H4",
                     value=_mh(4),
                     delta="horizons 1-4", delta_cls="neu"),
                dict(label="Bias H4",
                     value=_bh(4),
                     delta="horizons 1-4", delta_cls="neu"),
                dict(label="MAPE H12",
                     value=_mh(12),
                     delta="all 12 horizons", delta_cls="neu"),
                dict(label="Bias H12",
                     value=_bh(12),
                     delta="all 12 horizons", delta_cls="neu"),
                dict(label="Dentro IC 70%",
                     value=(f"{_p_n_in}/{_p_n_tot}"
                            if _p_n_tot > 0 else "—"),
                     delta=f"{_p_n_tot} semanas realizadas", delta_cls="neu"),
            )

            # ── Section 2: Forecast vs Actuals chart ──────────────────────────
            section("Forecast vs. Real")
            _fig_h2 = build_forecast_history_chart(
                _hist_view, _fc_view, _chart_lbl, _p_run,
            )
            st.plotly_chart(_fig_h2, use_container_width=True,
                            config={"displayModeBar": False})
            st.html(
                f'<div style="font-size:10px;color:{C["text_3"]};font-family:{C["mono"]};">'
                f'● VERDE = real dentro IC 70%  ·  '
                f'● ROJO = real fuera IC 70%  ·  '
                f'Línea azul = fecha forecast  ·  '
                f'{len(_p_all_dates)} ejecuciones disponibles</div>'
            )

            # ── Section 3: MAPE + BIAS by Horizon ────────────────────────────
            if _has_overlap and "horizonte" in _p_overlap.columns:
                section("MAPE & Bias por Horizonte")
                # Para vistas agregadas: calcular ape/pe por SKU individual antes
                # de promediar por horizonte, para que errores +/- se cancelen correctamente.
                if _pv == "Por SKU":
                    _ph_src = _p_overlap.copy()
                else:
                    _chart_skus = (_cat_skus if _pv == "Por Categoría"
                                   else list(df["sku"].unique()))
                    _hist_long_ch = df.rename(columns={"fecha": "ds", "sku": "unique_id"})
                    _ph_src = (_fc_run[_fc_run["unique_id"].isin(_chart_skus)]
                               .merge(_hist_long_ch[["unique_id", "ds", "cantidad"]],
                                      on=["unique_id", "ds"], how="inner"))
                    _ph_src = _ph_src[_ph_src["cantidad"] > 0].copy()
                    if not _ph_src.empty:
                        _ph_src["ape"] = (np.abs(_ph_src["cantidad"] - _ph_src["AutoETS"])
                                          / _ph_src["cantidad"])
                        _ph_src["pe"]  = ((_ph_src["AutoETS"] - _ph_src["cantidad"])
                                          / _ph_src["cantidad"])
                _ph = (_ph_src.groupby("horizonte")
                       .agg(mape=("ape", "mean"), bias=("pe", "mean"))
                       .mul(100).reset_index())
                if not _ph.empty:
                    _fig_ph = go.Figure()
                    _fig_ph.add_trace(go.Scatter(
                        x=_ph["horizonte"], y=_ph["mape"],
                        mode="lines+markers", name="MAPE",
                        line=dict(color=C["blue"], width=2),
                        marker=dict(size=7, color=C["blue"],
                                    line=dict(color=C["bg_card"], width=1.5)),
                        hovertemplate="H%{x}  <b>%{y:.1f}%</b><extra>MAPE</extra>",
                    ))
                    _fig_ph.add_trace(go.Scatter(
                        x=_ph["horizonte"], y=_ph["bias"],
                        mode="lines+markers", name="Bias",
                        line=dict(color="#FF8C42", width=2, dash="dot"),
                        marker=dict(size=7, color="#FF8C42",
                                    line=dict(color=C["bg_card"], width=1.5)),
                        hovertemplate="H%{x}  <b>%{y:.1f}%</b><extra>Bias</extra>",
                    ))
                    _fig_ph.update_layout(
                        template="plotly_dark",
                        paper_bgcolor=_PBG, plot_bgcolor=_PBG,
                        height=280, margin=dict(l=0, r=0, t=30, b=0),
                        font=dict(color=C["text_2"], family="Inter,sans-serif", size=11),
                        hoverlabel=_HOVER, hovermode="x unified",
                        legend=dict(bgcolor="rgba(0,0,0,0)", borderwidth=0,
                                    orientation="h", x=0, y=1.12),
                        xaxis=dict(
                            title="Horizonte (semanas)",
                            showgrid=True, gridcolor=_GRID, zeroline=False,
                            tickmode="linear", tick0=1, dtick=1,
                            tickfont=dict(family="Courier New,monospace", size=10,
                                          color=C["text_2"]),
                            title_font=dict(size=10, color=C["text_3"]),
                        ),
                        yaxis=dict(
                            title="%",
                            showgrid=True, gridcolor=_GRID, zeroline=True,
                            zerolinecolor=_GRID, zerolinewidth=1,
                            tickformat=".1f",
                            tickfont=dict(family="Courier New,monospace", size=10,
                                          color=C["text_2"]),
                            title_font=dict(size=10, color=C["text_3"]),
                        ),
                    )
                    st.plotly_chart(_fig_ph, use_container_width=True,
                                    config={"displayModeBar": False})

            # ── Section 4: Detailed table ──────────────────────────────────────
            if _pv in ("Todos", "Por Categoría"):
                section("Detalle por SKU")
                _tbl_skus = (
                    [s for s in df["sku"].unique()
                     if _get_category(s) == _pv_cat]
                    if _pv == "Por Categoría"
                    else list(df["sku"].unique())
                )
                _hist_long_p = df.rename(columns={"fecha": "ds", "sku": "unique_id"})
                _ov_raw = _fc_run[_fc_run["unique_id"].isin(_tbl_skus)].merge(
                    _hist_long_p[["unique_id", "ds", "cantidad"]],
                    on=["unique_id", "ds"], how="inner",
                )
                _ov_raw = _ov_raw[_ov_raw["cantidad"] > 0].copy()
                if not _ov_raw.empty:
                    _ov_raw["ape"] = (
                        np.abs(_ov_raw["cantidad"] - _ov_raw["AutoETS"])
                        / _ov_raw["cantidad"]
                    )
                    _ov_raw["pe"] = (
                        (_ov_raw["AutoETS"] - _ov_raw["cantidad"])
                        / _ov_raw["cantidad"]
                    )

                    def _mape_grp(g: pd.DataFrame, h: int | None = None) -> float:
                        sub = (g[g["horizonte"] <= h]
                               if h and "horizonte" in g.columns else g)
                        return sub["ape"].mean() * 100 if not sub.empty else float("nan")

                    def _bias_grp(g: pd.DataFrame, h: int | None = None) -> float:
                        sub = (g[g["horizonte"] <= h]
                               if h and "horizonte" in g.columns else g)
                        return sub["pe"].mean() * 100 if not sub.empty else float("nan")

                    def _cls_m(v):
                        return ("good" if v < 15 else ("warn" if v < 25 else "bad"))
                    def _cls_b(v):
                        return ("good" if abs(v) < 10 else ("warn" if abs(v) < 20 else "bad"))

                    _rows_html = ""
                    for _sk, _g in _ov_raw.groupby("unique_id"):
                        _g_in = 0
                        if "AutoETS-lo-70" in _g.columns:
                            _g_in = int(
                                ((_g["cantidad"] >= _g["AutoETS-lo-70"]) &
                                 (_g["cantidad"] <= _g["AutoETS-hi-70"])).sum()
                            )
                        _m4  = _mape_grp(_g, 4)
                        _b4  = _bias_grp(_g, 4)
                        _m12 = _mape_grp(_g, 12)
                        _b12 = _bias_grp(_g, 12)
                        _rows_html += (
                            f'<tr><td>{_sk}</td>'
                            f'<td class="{_cls_m(_m4)}">'
                            f'{"—" if pd.isna(_m4) else f"{_m4:.1f}%"}</td>'
                            f'<td class="{_cls_b(_b4)}">'
                            f'{"—" if pd.isna(_b4) else f"{_b4:+.1f}%"}</td>'
                            f'<td class="{_cls_m(_m12)}">'
                            f'{"—" if pd.isna(_m12) else f"{_m12:.1f}%"}</td>'
                            f'<td class="{_cls_b(_b12)}">'
                            f'{"—" if pd.isna(_b12) else f"{_b12:+.1f}%"}</td>'
                            f'<td>{_g_in}/{len(_g)}</td></tr>'
                        )
                    st.html(
                        '<table class="acc-table"><thead><tr>'
                        '<th>SKU</th><th>MAPE H4</th><th>Bias H4</th>'
                        '<th>MAPE H12</th><th>Bias H12</th><th>Dentro IC 70%</th>'
                        '</tr></thead>'
                        f'<tbody>{_rows_html}</tbody></table>'
                    )
                    st.html(
                        f'<div style="font-size:10px;color:{C["text_3"]};'
                        f'margin-top:8px;font-family:{C["mono"]};">'
                        f'MAPE: &lt;15% BUENO  15-25% ALERTA  &gt;25% MALO  |  '
                        f'BIAS: positivo = modelo sobreestima</div>'
                    )
                else:
                    st.html(
                        '<div class="info-box">No hay semanas realizadas para comparar.</div>'
                    )


# ══ Tab 3: Sandbox ════════════════════════════════════════════════════════════
with _tab_sb:
    section("Simulador en vivo")
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
                f'letter-spacing:0.08em;">INGRESA DATOS Y PULSA ▶ CALCULAR</div>'
            )


# ─── Footer ───────────────────────────────────────────────────────────────────
st.html(
    f'<div style="border-top:1px solid {C["border"]};margin-top:32px;padding-top:12px;'
    f'font-size:10px;color:{C["text_3"]};font-family:{C["mono"]};letter-spacing:0.06em;">'
    f'ABASTO · FASE 1 · AutoETS (statsforecast {__import__("statsforecast").__version__}) · '
    f'Streamlit · {_today}'
    f'</div>'
)

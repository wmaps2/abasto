"""
app.py — Abasto: router principal + sidebar global.
"""
import multiprocessing
multiprocessing.freeze_support()

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).parent))
import data as data_module
import upload as upload_module

st.set_page_config(
    page_title="Abasto · Supply Chain",
    page_icon="◈",
    layout="wide",
    initial_sidebar_state="expanded",
)

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

st.markdown(f"""
<style>
section[data-testid="stSidebar"] {{
    background-color: {C['bg_deep']} !important;
    border-right: 1px solid {C['border']} !important;
}}
section[data-testid="stSidebar"] .stMarkdown p,
section[data-testid="stSidebar"] .stMarkdown li {{
    color: {C['text_2']}; font-size: 12px; line-height: 1.6;
}}
section[data-testid="stSidebar"] label {{
    color: {C['text_1']} !important; font-size: 12px !important;
}}
section[data-testid="stSidebar"] h1,
section[data-testid="stSidebar"] h2,
section[data-testid="stSidebar"] h3 {{
    color: {C['text_1']} !important;
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
.stRadio [data-testid="stMarkdownContainer"] p {{
    color: {C['text_1']} !important; font-size: 13px !important;
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
[data-testid="stFileUploader"] {{
    background: {C['bg_card']};
    border: 1px dashed {C['border']};
    border-radius: 8px;
}}
[data-testid="stFileUploader"] label {{
    color: {C['text_2']} !important; font-size: 12px !important;
}}
.stSpinner > div > div {{ border-top-color: {C['blue']} !important; }}
[data-testid="stNotification"] {{ border-radius: 6px !important; font-size: 12px !important; }}
.section-hdr {{
    font-size: 10px; letter-spacing: 0.14em; text-transform: uppercase;
    color: {C['text_2']}; font-weight: 700;
    padding-bottom: 10px; border-bottom: 1px solid {C['border']};
    margin-bottom: 18px; margin-top: 8px;
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


# ─── Cached helpers ───────────────────────────────────────────────────────────
@st.cache_data(ttl=300, show_spinner=False)
def _load_sb_historia(fuentes: tuple[str, ...]) -> pd.DataFrame:
    return data_module.get_historia_semanal(fuentes=list(fuentes))


@st.cache_data(ttl=60, show_spinner=False)
def _count_uploaded() -> int:
    return upload_module.get_uploaded_count()


@st.cache_data(ttl=60, show_spinner=False)
def _get_template_bytes() -> bytes:
    return upload_module.build_template_xlsx()


# ─── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.html(f"""
    <div style="padding:8px 0 20px 0;">
        <div style="font-size:18px;font-weight:900;letter-spacing:0.1em;
                    color:{C['text_1']};">◈ ABASTO</div>
        <div style="font-size:10px;letter-spacing:0.1em;text-transform:uppercase;
                    color:{C['text_2']};margin-top:3px;">Supply Chain Intelligence</div>
    </div>
    """)

    st.html(f'<div class="section-hdr">Datos</div>')

    _n_up = _count_uploaded()
    _radio_opts = ["Demo (12 SKUs simulados)"]
    if _n_up > 0:
        _radio_opts.append(f"Datos subidos por usuario ({_n_up} SKUs)")

    _fuente_sel = st.radio(
        "Fuente de datos",
        options=_radio_opts,
        key="fuente_radio",
        label_visibility="collapsed",
    )
    _fuentes: tuple[str, ...] = (
        ("uploaded",) if (_n_up > 0 and _fuente_sel != "Demo (12 SKUs simulados)")
        else ("demo",)
    )

    # Invalidate forecast when source changes
    if st.session_state.get("_last_fuentes") != _fuentes:
        st.session_state["_last_fuentes"] = _fuentes
        for _k in ("df", "forecast_results", "data_hash"):
            st.session_state.pop(_k, None)

    # Load history into session_state
    if "df" not in st.session_state:
        try:
            _df_loaded = _load_sb_historia(_fuentes)
            if _df_loaded.empty:
                st.html('<div class="warn-box">Sin datos para la fuente seleccionada.</div>')
            else:
                st.session_state["df"]          = _df_loaded
                st.session_state["data_source"] = _fuentes[0]
        except Exception as _exc:
            if "42703" in str(_exc) or "does not exist" in str(_exc):
                st.error(
                    "Falta migración en Supabase. Ejecuta en SQL Editor:\n\n"
                    "```sql\n" + upload_module.MIGRATION_SQL + "\n```"
                )
            else:
                st.error(f"Error cargando datos: {_exc}")

    _df_sidebar = st.session_state.get("df")
    if _df_sidebar is not None:
        _info = data_module.summary(_df_sidebar)
        st.html(
            f'<div class="ok-box">✓ {_info["n_skus"]} SKUs · {_info["n_weeks"]} semanas<br>'
            f'<span style="font-weight:400;color:{C["text_2"]};font-size:11px;">'
            f'{_info["date_min"]} → {_info["date_max"]}</span></div>'
        )

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Download template ─────────────────────────────────────────────────────
    try:
        _tpl = _get_template_bytes()
        st.download_button(
            "📥 Download template",
            data=_tpl,
            file_name="abasto_template.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )
    except Exception:
        st.button("📥 Download template (no disponible)", disabled=True, use_container_width=True)

    # ── Upload Excel ──────────────────────────────────────────────────────────
    _up_file = st.file_uploader(
        "📤 Upload Excel",
        type=["xlsx"],
        label_visibility="visible",
        key="sidebar_xlsx_uploader",
    )

    if _up_file is not None:
        _fid = f"{_up_file.name}_{_up_file.size}"
        if st.session_state.get("_up_fid") != _fid:
            st.session_state["_up_fid"] = _fid
            for _k in ("_up_parsed", "_up_conflicts", "_up_replace_ok"):
                st.session_state.pop(_k, None)

        if "_up_parsed" not in st.session_state:
            try:
                _dm, _dd = upload_module.parse_upload(_up_file)
                st.session_state["_up_parsed"]    = (_dm, _dd)
                st.session_state["_up_conflicts"] = upload_module.check_conflicts(
                    _dm["sku_id"].tolist()
                )
            except upload_module.UploadError as _e:
                st.error(str(_e))

        if "_up_parsed" in st.session_state:
            _dm, _dd   = st.session_state["_up_parsed"]
            _conflicts = st.session_state.get("_up_conflicts", [])
            _n_new     = len(_dm)

            st.html(f'<div class="ok-box">✓ {_n_new} SKU(s) listos</div>')

            if _conflicts and not st.session_state.get("_up_replace_ok"):
                st.warning(f"Ya existen: {', '.join(_conflicts)}. ¿Reemplazar?")
                _rc1, _rc2 = st.columns(2)
                with _rc1:
                    if st.button("Reemplazar", key="_btn_rep_yes", use_container_width=True):
                        st.session_state["_up_replace_ok"] = True
                        st.rerun()
                with _rc2:
                    if st.button("Cancelar", key="_btn_rep_no", use_container_width=True):
                        for _k in ("_up_fid", "_up_parsed", "_up_conflicts", "_up_replace_ok"):
                            st.session_state.pop(_k, None)
                        st.rerun()
            else:
                _replace = bool(_conflicts) and st.session_state.get("_up_replace_ok", False)
                if st.button("⬆ Confirmar upload", key="_btn_do_up", use_container_width=True):
                    with st.spinner(f"Subiendo {_n_new} SKU(s) a Supabase…"):
                        try:
                            _done = upload_module.upload_skus(_dm, _dd, replace=_replace)
                            st.session_state["_just_uploaded"] = _done
                            for _k in ("_up_fid", "_up_parsed", "_up_conflicts", "_up_replace_ok"):
                                st.session_state.pop(_k, None)
                            _load_sb_historia.clear()
                            _count_uploaded.clear()
                            st.cache_data.clear()
                            for _k in ("df", "forecast_results", "data_hash"):
                                st.session_state.pop(_k, None)
                            st.rerun()
                        except upload_module.UploadError as _e:
                            st.error(str(_e))

    # ── Post-upload ───────────────────────────────────────────────────────────
    if st.session_state.get("_just_uploaded"):
        _done_ids = st.session_state["_just_uploaded"]
        st.toast(f"✓ {len(_done_ids)} SKU(s) cargados", icon="✅")
        st.html(
            f'<div class="ok-box">✓ {len(_done_ids)} SKU(s) guardados:<br>'
            f'<span style="font-size:11px;">{", ".join(_done_ids)}</span></div>'
        )
        if st.button("📊 Generar forecasts históricos (~2 min)",
                     key="_btn_backfill", use_container_width=True):
            with st.spinner("Generando forecasts históricos…"):
                from simulation import backfill_forecasts
                backfill_forecasts.main(n_weeks=24)
            st.session_state.pop("_just_uploaded", None)
            st.rerun()
        if st.button("Cerrar", key="_btn_close_up", use_container_width=True):
            st.session_state.pop("_just_uploaded", None)
            st.rerun()

    # ── Delete uploaded data ──────────────────────────────────────────────────
    if _n_up > 0:
        st.markdown("---")
        if st.session_state.get("_confirm_del_up"):
            st.warning(f"¿Borrar {_n_up} SKU(s) subidos? Irreversible.")
            _dc1, _dc2 = st.columns(2)
            with _dc1:
                if st.button("Sí, borrar", key="_btn_del_yes", use_container_width=True):
                    with st.spinner("Eliminando…"):
                        upload_module.delete_uploaded_data()
                    st.session_state.pop("_confirm_del_up", None)
                    _load_sb_historia.clear()
                    _count_uploaded.clear()
                    st.cache_data.clear()
                    for _k in ("df", "forecast_results", "data_hash"):
                        st.session_state.pop(_k, None)
                    st.rerun()
            with _dc2:
                if st.button("Cancelar", key="_btn_del_no", use_container_width=True):
                    st.session_state.pop("_confirm_del_up", None)
        else:
            if st.button("🗑️ Borrar datos de usuario",
                         key="_btn_del_trig", use_container_width=True):
                st.session_state["_confirm_del_up"] = True


# ─── Navigate ─────────────────────────────────────────────────────────────────
pg = st.navigation([
    st.Page("pages/forecast.py", title="Forecast"),
    st.Page("pages/compra.py",   title="Compra"),
])
pg.run()

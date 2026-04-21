"""
pages/5_guia.py — Abasto: Guía de usuario
"""
import streamlit as st

C = dict(
    bg_base    = "#0f1117",
    bg_card    = "#1c1f31",
    border     = "#252840",
    text_1     = "#e2e8f0",
    text_2     = "#8892a8",
    text_3     = "#4a5568",
    blue       = "#4f8ff7",
    blue_dim   = "rgba(79,143,247,0.12)",
    mono       = "'Courier New','Consolas',monospace",
)

st.markdown(f"""
<style>
html, body, [class*="css"] {{ font-family: 'Inter','Segoe UI',system-ui,sans-serif; }}
.stApp {{ background-color: {C['bg_base']}; color: {C['text_1']}; }}
.block-container {{ padding-top: 1.5rem !important; padding-bottom: 2rem !important; max-width: 1400px; }}
.stTabs [data-baseweb="tab-list"] {{
    background-color: {C['bg_card']}; border-bottom: 1px solid {C['border']};
    gap: 0; padding: 0;
}}
.stTabs [data-baseweb="tab"] {{
    color: {C['text_2']} !important; background-color: transparent !important;
    border-radius: 0 !important; padding: 10px 22px !important;
    font-size: 11px; font-weight: 600; letter-spacing: 0.08em; text-transform: uppercase;
    border-bottom: 2px solid transparent !important; margin-bottom: -1px;
}}
.stTabs [aria-selected="true"] {{
    color: {C['blue']} !important; border-bottom-color: {C['blue']} !important;
    background-color: transparent !important;
}}
.stTabs [data-baseweb="tab-panel"] {{ background-color: {C['bg_base']}; padding-top: 24px; }}
.sc-header {{
    display: flex; align-items: center; justify-content: space-between;
    padding: 4px 0 20px 0; border-bottom: 1px solid {C['border']}; margin-bottom: 28px;
}}
.section-hdr {{
    font-size: 10px; letter-spacing: 0.14em; text-transform: uppercase;
    color: {C['text_2']}; font-weight: 700;
    padding-bottom: 10px; border-bottom: 1px solid {C['border']};
    margin-bottom: 18px; margin-top: 8px;
}}
.info-box {{
    background: {C['blue_dim']}; border: 1px solid {C['blue']};
    border-radius: 6px; padding: 12px 16px;
    font-size: 12px; color: {C['text_2']}; line-height: 1.6;
}}
</style>
""", unsafe_allow_html=True)

st.html(f"""
<div class="sc-header">
  <div style="display:flex;align-items:baseline;gap:10px;">
    <span style="font-size:24px;color:{C['blue']};">◈</span>
    <span style="font-size:22px;font-weight:900;letter-spacing:0.1em;color:{C['text_1']};">ABASTO</span>
    <span style="font-size:10px;letter-spacing:0.1em;text-transform:uppercase;color:{C['text_2']};">
      · Guía de usuario
    </span>
  </div>
</div>
""")

_tab_intro, _tab_fc, _tab_mp, _tab_compra, _tab_glosario = st.tabs([
    "Introducción",
    "Forecast",
    "Rendimiento del modelo",
    "Compra",
    "Glosario",
])

with _tab_intro:
    st.header("Introducción")
    st.write("Contenido por definir...")

with _tab_fc:
    st.header("Forecast")
    st.write("Contenido por definir...")

with _tab_mp:
    st.header("Rendimiento del modelo")
    st.write("Contenido por definir...")

with _tab_compra:
    st.header("Compra")
    st.write("Contenido por definir...")

with _tab_glosario:
    st.header("Glosario")
    st.write("Contenido por definir...")

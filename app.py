"""
app.py — Abasto: router principal.
Define la navegación y configuración global de la app multipage.
"""
import multiprocessing
multiprocessing.freeze_support()

import streamlit as st

st.set_page_config(
    page_title="Abasto · Supply Chain",
    page_icon="◈",
    layout="wide",
    initial_sidebar_state="expanded",
)

pg = st.navigation([
    st.Page("pages/forecast.py", title="Forecast"),
    st.Page("pages/compra.py",   title="Compra"),
])
pg.run()

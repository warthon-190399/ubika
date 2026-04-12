import streamlit as st
from session_utils import init_session_state
import dashboard
import autoevaluator

st.set_page_config(
    page_title="Ubika",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Inicializar session state ANTES de los tabs
init_session_state()
st.session_state.setdefault("pagina_anterior", None)

# ── Navegación por tabs ────────────────────────────────────────────────────────
tab_dashboard, tab_auto = st.tabs(["📊 Dashboard", "🏠 Autoevaluador"])

with tab_dashboard:
    if st.session_state.pagina_anterior != "Dashboard":
        st.session_state.pred = 0
        st.session_state.pagina_anterior = "Dashboard"
    dashboard.run()

with tab_auto:
    if st.session_state.pagina_anterior != "Autoevaluador":
        st.session_state.pred = 0
        st.session_state.pagina_anterior = "Autoevaluador"
    autoevaluator.run()

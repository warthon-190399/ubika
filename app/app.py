import streamlit as st
import autoevaluation_V2
import dashboard
import pandas as pd
from session_utils import init_session_state # Initial configuration, "session_utils.py"

st.session_state.setdefault("pagina_anterior",None)

init_session_state()

st.set_page_config(
    page_title="Ubika",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="expanded"
    )

st.sidebar.title("Menú de navegación")
page = st.sidebar.selectbox("Selecciona una página:", ["Dashboard", "Autoevaluador"])

# --- Detectar cambio de página ---
if st.session_state.pagina_anterior != page:
    st.session_state.data_servicios = pd.DataFrame()
    st.session_state.pred = 0
    st.session_state.pagina_anterior = page  # Actualiza el registro
    st.session_state.message_error = None # Error message button "Estimar precio"

if  page == "Dashboard":
    dashboard.run()
elif page == "Autoevaluador":
    autoevaluation_V2.run()

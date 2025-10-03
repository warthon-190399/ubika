import streamlit as st
import autoevaluation
import autoevaluation_V2
import visualization
import dashboard

st.set_page_config(
    page_title="Ubika",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="expanded"
    )

st.sidebar.title("Menú de navegación")
page = st.sidebar.selectbox("Selecciona una página:", ["Dashboard", "Autoevaluador", "Visualización", "Jimmy"])

if "data" not in st.session_state:
    st.session_state["data"] = None

if  page == "Dashboard":
    dashboard.run()
elif page == "Autoevaluador":
    autoevaluation.run()
elif page == "Visualización":
    visualization.run()
elif page == "Jimmy":
    autoevaluation_V2.run()
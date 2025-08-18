import streamlit as st
import autoevaluation
import visualization
import dashboard

st.set_page_config(
    page_title="Ubika",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="expanded"
    )

st.sidebar.title("Menú de navegación")
page = st.sidebar.selectbox("Selecciona una página:", ["Dashboard", "Autoevaluador", "Visualización"])


if  page == "Dashboard":
    dashboard.run()
elif page == "Autoevaluador":
    autoevaluation.run()
elif page == "Visualización":
    visualization.run()
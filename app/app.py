import streamlit as st
import autoevaluation
import visualization

st.set_page_config(page_title="App Inmobiliaria", layout="wide")

st.sidebar.title("Menú de navegación")
page = st.sidebar.selectbox("Selecciona una página:", ["Autoevaluador", "Visualización"])

if page == "Autoevaluador":
    autoevaluation.run()
elif page == "Visualización":
    visualization.run()
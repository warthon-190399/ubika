import streamlit as st
import pandas as pd
import numpy as np
import pandas as pd
import os
import joblib

def run():
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    BASE_DIR = os.path.abspath(os.path.join(BASE_DIR, ".."))
    input_model_path = os.path.join(BASE_DIR, "models", "catboost_model.pkl")

    #st.write(input_model_path)

    # load model
    model = joblib.load(input_model_path)

    st.title("Autoevaluador de Precio de Vivienda")

    # input per user
    mantenimiento_soles = st.number_input("Mantenimiento (S/.)", min_value=0.0)
    area_m2 = st.number_input("Área (m²)", min_value=0.0)
    num_dorm = st.number_input("Nº Dormitorios", min_value=0)
    num_banios = st.number_input("Nº Baños", min_value=0)
    num_estac = st.number_input("Nº Estacionamientos", min_value=0)
    antiguedad = st.number_input("Antigüedad (años)", min_value=0)
    num_visualizaciones = st.number_input("Visualizaciones", min_value=0)
    num_colegios_prox = st.number_input("Colegios cerca", min_value=0)
    num_malls_prox = st.number_input("Malls cerca", min_value=0)
    num_hospitales_prox = st.number_input("Hospitales cerca", min_value=0)
    num_tren_est_prox = st.number_input("Estaciones tren cerca", min_value=0)
    num_metro_est_prox = st.number_input("Estaciones metro cerca", min_value=0)
    num_comisarias_prox = st.number_input("Comisarías cerca", min_value=0)
    total_ambientes = st.number_input("Total ambientes", min_value=0)
    tiene_estac = st.selectbox("¿Tiene estacionamiento?", [0, 1])
    tamano_cod = st.selectbox("Código tamaño", [0, 1, 2])  # depende de tu codificación
    antiguedad_cod = st.selectbox("Código antigüedad", [0, 1, 2])
    nivel_socioeconomico_cod = st.selectbox("Nivel socioeconómico (cod)", [0, 1, 2, 3])
    total_servicios_prox = st.number_input("Servicios cerca", min_value=0)
    total_transporte_prox = st.number_input("Transportes cerca", min_value=0)

    # button to predict
    if st.button("Estimar precio"):
        input_data = np.array([[
            mantenimiento_soles, area_m2, num_dorm, num_banios,
            num_estac, antiguedad, num_visualizaciones, num_colegios_prox,
            num_malls_prox, num_hospitales_prox, num_tren_est_prox,
            num_metro_est_prox, num_comisarias_prox, total_ambientes, tiene_estac,
            tamano_cod, antiguedad_cod, nivel_socioeconomico_cod,
            total_servicios_prox, total_transporte_prox 
        ]])

        pred = model.predict(input_data)[0]
        st.success(f"El precio estimado por el modelo es: S/. {pred:,.2f}")

    #st.sidebar.title("Panel de Control")


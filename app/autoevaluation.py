import streamlit as st
import pandas as pd
import numpy as np
import pandas as pd
import os
import joblib

def run():
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    BASE_DIR = os.path.abspath(os.path.join(BASE_DIR, ".."))
    input_model_path_l = os.path.join(BASE_DIR, "models", "catboost_model_l.pkl")
    input_model_path_h = os.path.join(BASE_DIR, "models", "XGBoost_prueba.pkl")
    #st.write(input_model_path)

    input_df = os.path.join(BASE_DIR, "data", "processed", "final_dataset_h_prueba.csv")
    df = pd.read_csv(input_df)

    # load model
    model_l = joblib.load(input_model_path_l)
    model_h = joblib.load(input_model_path_h)

    st.title("Autoevaluador de Precio de Vivienda")
    #st.write(f"El modelo que estamos usando es: {model_h}")
    col1, col2 = st.columns([0.5, 2])

    departamentos = ['miraflores', 'san isidro', 'san borja', 'surco', 'surquillo', 'jesus maria', 
                     'lince', 'magdalena', 'pueblo libre', 'lima cercado', 'brena', 'la victoria', 
                     'san luis', 'rimac', 'los olivos', 'comas', 'independencia', 'puente piedra', 
                     'carabayllo', 'ancon', 'smp', 'ate', 'santa anita', 'lurigancho', 'chaclacayo', 
                     'cieneguilla', 'el agustino', 'la molina','chorrillos', 'sjm', 'vmt', 'ves', 'lurin', 
                     'pachacamac','punta hermosa', 'san bartolo', 'punta negra', 'pucusana', 
                     'santa maria del mar', 'barranco','callao']

    with col1:
        st.markdown("**Distrito**")
    with col2:
        departamento_select = st.selectbox("", departamentos, label_visibility="collapsed")


    # input per user
    # campos = [
    #     ("Mantenimiento (S/.)",0.0, "mantenimiento"),
    #     ("Área (m²)",0.0, "area"),
    #     ("Nº Dormitorios",0, "dormitorio"),
    #     ("Nº Baños",0, "baño"),
    #     ("Nº Estacionamientos",0, "estacionamiento"),
    #     ("Antigüedad (años)",0, "antiguedad"),
    #     ("Colegios cerca",0, "colegio"),
    #     ("Hospitales cerca",0, "hospital"),
    #     ("Total ambientes",0, "ambiente"),
    #     ("¿Tiene estacionamiento?",[0, 1], "tieneestacionamiento"),
    #     ("Código tamaño",[0, 1, 2], "codigotamaño"),
    #     ("Nivel socioeconómico (cod)",[0, 1, 2, 3], "nivelsocioeconomico"),
    #     ("Servicios cerca",0, "servicioscerca"),
    #     ("Zona funcional (cod)",[0, 1, 2, 3, 4, 5, 6, 7, 8], "zonafuncional")
    # ]


    campos = [
        ("Mantenimiento (S/.)",0.0, "mantenimiento"),
        ("Área (m²)",0.0, "area"),
        ("Nº Dormitorios",0, "dormitorio"),
        ("Nº Baños",0, "baño"),
        ("Nº Estacionamientos",0, "estacionamiento"),
        ("Antigüedad (años)",0, "antiguedad"),
        ("Zona apeim (cod)",df["zona_apeim_cod"].unique().tolist(), "zonafuncional")
    ]

    valores = []

    for label, min_val, key in campos:
        col1, col2 = st.columns([0.5, 2])
        with col1:
            st.markdown(f"**{label}**")

        with col2:
            if key in ["tieneestacionamiento","codigotamaño",
                       "nivelsocioeconomico", "zonafuncional"]:
                valor = st.selectbox("", min_val,
                                        label_visibility="collapsed", key = key)
            else:
                valor = st.number_input("", min_value=min_val,
                                    label_visibility="collapsed", key = key)
        valores.append(valor)

    st.write("Valores enviados al modelo:", valores)


    if st.button("Estimar precio"):
        # column_names = ['mantenimiento_soles', 'area_m2', 'num_dorm', 'num_banios', 'num_estac',
        #                 'antiguedad', 'num_colegios_prox', 'num_hospitales_prox',
        #                 'total_ambientes', 'tiene_estac', 'tamano_cod',
        #                 'nivel_socioeconomico_cod', 'total_servicios_prox',
        #                 'zona_funcional_cod']
        column_names = ['mantenimiento_soles', 'area_m2', 'num_dorm', 'num_banios', 'num_estac',
                        'antiguedad', 'zona_apeim_cod']
        
        input_df = pd.DataFrame([valores], columns=column_names)

        if departamento_select in ['miraflores', 'surco', 'san isidro','barranco']:
            pred = model_h.predict(input_df)[0]
        else:
            pred = model_l.predict(input_df)[0]
        st.success(f"El precio estimado por el modelo es: S/. {pred:,.2f}")

def zone_classification(distrito):
    distrito = str(distrito).strip().lower()
    if distrito in ['miraflores', 'san isidro', 'san borja', 'surco', 'surquillo', 'jesus maria', 'lince', 'magdalena', 'pueblo libre']:
        return 4 # 'Lima Moderna'
    elif distrito in ['lima cercado', 'brena', 'la victoria', 'san luis', 'rimac']:
        return 2 # 'Lima Centro'
    elif distrito in ['los olivos', 'comas', 'independencia', 'puente piedra', 'carabayllo', 'ancon', 'smp']:
        return 5 # 'Lima Norte'
    elif distrito in ['ate', 'santa anita', 'lurigancho', 'chaclacayo', 'cieneguilla', 'el agustino', 'la molina']:
        return 3 #'Lima Este'
    elif distrito in ['chorrillos', 'sjm', 'vmt', 'ves', 'lurin', 'pachacamac']:
        return 7 # 'Lima Sur Urbana'
    elif distrito in ['punta hermosa', 'san bartolo', 'punta negra', 'pucusana', 'santa maria del mar', 'barranco']:
        return 6 # 'Lima Sur Balnearios'
    elif distrito == 'callao':
        return 1 #'Callao'
    else:
        return 8 # 'Otro
    
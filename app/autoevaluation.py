import streamlit as st
from streamlit_folium import st_folium
import folium
import pandas as pd
import numpy as np
import pandas as pd
import os
import joblib
from sklearn.neighbors import BallTree
from geopy.geocoders import Nominatim
import unidecode
from folium.plugins import Geocoder

def run():
    zona_apeim = {
        # 1
        'puente piedra': 1,
        'comas': 1,
        'carabayllo': 1,
        'ancon': 1,

        # 2
        'independencia': 2,
        'los olivos': 2,
        'smp': 2,  # San Martín de Porres

        # 3
        'san juan de lurigancho': 3,
        'sjl': 3,  # abreviado

        # 4
        'lima cercado': 4,
        'rimac': 4,
        'brena': 4,
        'la victoria': 4,

        # 5
        'ate': 5,
        'chaclacayo': 5,
        'lurigancho': 5,
        'santa anita': 5,
        'san luis': 5,
        'el agustino': 5,
        'cieneguilla': 5,

        # 6
        'jesus maria': 6,
        'lince': 6,
        'pueblo libre': 6,
        'magdalena': 6,
        'san miguel': 6,

        # 7
        'miraflores': 7,
        'san isidro': 7,
        'san borja': 7,
        'surco': 7,
        'la molina': 7,

        # 8
        'surquillo': 8,
        'barranco': 8,
        'chorrillos': 8,
        'san juan de miraflores': 8,
        'sjm': 8,  # abreviado

        # 9
        'ves': 9,  # Villa El Salvador
        'villa maria del triunfo': 9,
        'vmt': 9,  # abreviado
        'lurin': 9,
        'pachacamac': 9,
        'punta hermosa': 9,
        'punta negra': 9,
        'san bartolo': 9,
        'pucusana': 9,
        'santa maria del mar': 9,

        # 10
        'callao': 10,
    }

    distritos_lima = [
        'ate', 'barranco', 'brena', 'carabayllo', 'chaclacayo', 'chorrillos', 'cieneguilla',
        'comas', 'el agustino', 'independencia', 'jesus maria', 'la molina', 'la victoria',
        'lince', 'los olivos', 'lurigancho', 'lurin', 'magdalena del mar',
        'pueblo libre', 'miraflores', 'pachacamac', 'puente piedra', 'rimac',
        'san bartolo', 'san borja', 'san isidro', 'san juan de lurigancho',
        'san juan de miraflores', 'san luis', 'san martin de porres', 'san miguel',
        'santa anita', 'santa maria del mar', 'santa rosa', 'santiago de surco',
        'surquillo', 'villa el salvador', 'villa maria del triunfo', 'callao'
    ]

    #Read data
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    BASE_DIR = os.path.abspath(os.path.join(BASE_DIR, ".."))
    input_model_path_l = os.path.join(BASE_DIR, "models", "randomforest_model_l.pkl")
    input_model_path_h = os.path.join(BASE_DIR, "models", "catboost_model_h.pkl")
    input_bins_labels = os.path.join(BASE_DIR, "models", "bins_labels.pkl")

    input_path_malls = os.path.join(BASE_DIR, "data", "processed", "malls_processed.csv")
    input_path_colegios = os.path.join(BASE_DIR, "data", "processed", "colegios_processed.csv")
    input_path_hospitales = os.path.join(BASE_DIR, "data", "processed", "hospitales_processed.csv")
    input_path_tren = os.path.join(BASE_DIR, "data", "processed", "tren_processed.csv")
    input_path_metropolitano = os.path.join(BASE_DIR, "data", "processed", "metropolitano_processed.csv")
    input_path_comisarias = os.path.join(BASE_DIR, "data", "processed", "comisarias_processed.csv")
    input_path_inpe = os.path.join(BASE_DIR, "data", "processed", "inpe_processed.csv")

    df_malls = pd.read_csv(input_path_malls)
    df_colegios = pd.read_csv(input_path_colegios)
    df_hospitales = pd.read_csv(input_path_hospitales)
    df_tren = pd.read_csv(input_path_tren)
    df_metropolitano = pd.read_csv(input_path_metropolitano)
    df_comisarias = pd.read_csv(input_path_comisarias)
    df_inpe = pd.read_csv(input_path_inpe)

    # load models
    model_l = joblib.load(input_model_path_l)
    model_h = joblib.load(input_model_path_h)
    bins, labels = joblib.load(input_bins_labels)

    st.title("Autoevaluador de Precio de Vivienda")

    col1, col2 = st.columns(2)

    with col1:
    #-------------------------------------------------
        if "lat" not in st.session_state:
            st.session_state.lat = -12.05
        if "lon" not in st.session_state:
            st.session_state.lon = -77.04
        if "address" not in st.session_state:
            st.session_state.address = "Lima, Perú"

        #Text input address
        address_input = st.text_input("Ingresa dirección:")

        distritos = ['miraflores', 'san isidro', 'san borja', 'surco', 'surquillo', 'jesus maria', 
                        'lince', 'magdalena', 'pueblo libre', 'lima cercado', 'brena', 'la victoria', 
                        'san luis', 'rimac', 'los olivos', 'comas', 'independencia', 'puente piedra', 
                        'carabayllo', 'ancon', 'smp', 'ate', 'santa anita', 'lurigancho', 'chaclacayo', 
                        'cieneguilla', 'el agustino', 'la molina','chorrillos', 'sjm', 'vmt', 'ves', 'lurin', 
                        'pachacamac','punta hermosa', 'san bartolo', 'punta negra', 'pucusana', 
                        'santa maria del mar', 'barranco','callao','sjl']
        
        distrito_select = st.selectbox("", distritos, label_visibility="collapsed")

        if st.button("🔍 Buscar dirección"):
            full_address = f"{address_input} + {distrito_select}, Lima, Perú"

            #Geocoding
            geolocator = Nominatim(user_agent="streamlit_map")
            location = geolocator.geocode(full_address)
            
            if location:
                st.session_state.lat = location.latitude
                st.session_state.lon = location.longitude
                st.session_state.address = full_address
                st.success(f"📍 Dirección encontrada: {full_address}")
                st.write(f"🌍 Coordenadas: **Latitud:** {location.latitude}, **Longitud:** {location.longitude}")
                st.rerun()
            else:
                st.error("❌ No se encontró la dirección. Verifica la información ingresada.")

        lat = st.session_state.lat
        lon = st.session_state.lon
        
        #Show
        m = folium.Map(
            location=[st.session_state.lat, st.session_state.lon],
            zoom_start=18,
            min_zoom=18,
            max_zoom=18,
            dragging=False,
            zoom_control=False,
            scrollWheelZoom=False,
            doubleClickZoom=False
        )

        #
        folium.Marker(
            [st.session_state.lat, st.session_state.lon],
            popup=st.session_state.address,
            tooltip="Ubicación encontrada"
        ).add_to(m)

        st_folium(m, width=700, height=500)
        #---------------------------------------------------------

        num_colegios_prox = proximidad_entre(lat, lon, df_colegios)[0]
        num_malls_prox = proximidad_entre(lat, lon, df_malls)[0]
        num_hospitales_prox = proximidad_entre(lat, lon, df_hospitales)[0]
        num_est_tren_prox = proximidad_entre(lat, lon, df_tren)[0]
        num_est_metro_prox = proximidad_entre(lat, lon, df_metropolitano)[0]
        num_comisarias_prox = proximidad_entre(lat, lon, df_comisarias)[0]
        num_crimenes_prox = proximidad_entre(lat, lon, df_inpe)[0]

        st.write(f"N° de colegios cercanos: {num_colegios_prox}")
        st.write(f"N° de malls cercanos: {num_malls_prox}")
        st.write(f"N° de hospitales cercanos: {num_hospitales_prox}")
        st.write(f"N° de estaciones de tren cercanos: {num_est_tren_prox}")
        st.write(f"N° de estaciones de metropolitano cercanos: {num_est_metro_prox}")
        st.write(f"N° de comisarias cercanas: {num_comisarias_prox}")
        st.write(f"N° de crimenes cercanos: {num_crimenes_prox}")

        total_servicios = num_colegios_prox + num_malls_prox + num_hospitales_prox + num_comisarias_prox
        total_servicios = int(total_servicios)
        st.write(f"Total servicios: {total_servicios}")

        total_transporte =  num_est_tren_prox + num_est_metro_prox 
        total_transporte = int(total_transporte)
        st.write(f"Total transporte: {total_transporte}")

        categoria_crimenes = pd.cut([num_crimenes_prox],bins=bins,labels=labels, include_lowest=True)
        categoria_crimenes = pd.Categorical(categoria_crimenes, categories=labels)
        categoria_crimenes = categoria_crimenes.codes[0] + 1
        categoria_crimenes = int(categoria_crimenes)
        st.write(f"Categoria crimenes: {categoria_crimenes}")

    #-------------------------------------------------
    with col2: #Colum 2
        #--------------------------------------------------------------------------------
        campos = [
                ("Mantenimiento (S/.)",0.0, "mantenimiento"),
                ("Área (m²)",0.0, "area"),
                ("Nº Dormitorios",0, "dormitorio"),
                ("Nº Baños",0, "baño"),
                ("Nº Estacionamientos",0, "estacionamiento"),
                ("Antigüedad (años)",0, "antiguedad")
            ]
            
        valores = []

        for label, min_val, key in campos:
                col1, col2 = st.columns([1, 2])
                with col1:
                    st.markdown(f"**{label}**")

                with col2:
                    if key in ["tieneestacionamiento","codigotamaño",
                            "nivelsocioeconomico"]:
                        #"zonafuncional"
                        valor = st.selectbox("", min_val,
                                                label_visibility="collapsed", key = key)
                    
                    elif key == "antiguedad":
                        opciones_antiguedad = ["No sé"] + list(range(0, 101))  # puedes ajustar el rango máximo
                        seleccion = st.selectbox("", opciones_antiguedad, label_visibility="collapsed", key=key)
                        valor = np.nan if seleccion == "No sé" else seleccion
                    
                    elif key == "mantenimiento":
                        seleccion = st.selectbox(
                            "¿Conoces la antigüedad?", 
                            ["Ingresar valor", "No sé"], 
                            label_visibility="collapsed", 
                            key=f"{key}_opcion"
                        )

                        if seleccion == "Ingresar valor":
                            valor = st.number_input(
                                "", 
                                min_value=0, 
                                max_value=10000,  # puedes ajustar el máximo si lo deseas
                                label_visibility="collapsed", 
                                key=key
                            )
                        else:
                            valor = np.nan
                                
                    else:
                        valor = st.number_input("", min_value=min_val,
                                            label_visibility="collapsed", key = key)
                valores.append(valor)

        valor_apeim = zona_apeim[distrito_select]
        #valor_apeim = zona_apeim[distrito_encontrado_folium]
        valores.append(total_servicios)
        valores.append(total_transporte)
        valores.append(valor_apeim)
        valores.append(categoria_crimenes)

        st.write("Valores enviados al modelo:", valores)


        if st.button("Estimar precio"):
                column_names = ['mantenimiento_soles', 'area_m2', 'num_dorm', 'num_banios', 'num_estac',
                                'antiguedad','total_servicios_prox', 'total_transporte_aprox', 'zona_apeim_cod','categoria_crimenes_cod']
                
                input_df = pd.DataFrame([valores], columns=column_names)

                if distrito_select in ['miraflores', 'surco', 'san isidro','barranco']:
                    pred = model_h.predict(input_df)[0]
                else:
                    pred = model_l.predict(input_df)[0]
                st.success(f"El precio estimado por el modelo es: S/. {pred:,.2f}")

def proximidad_entre(lat, lon, df_colegios_1, radius_metros = 500):
    # Asegurarse que no hay NaNs
    df_colegios_1 = df_colegios_1.dropna(subset=['latitud', 'longitud']).reset_index(drop=True)

    colegios_rad = np.deg2rad(df_colegios_1[['latitud', 'longitud']].values)

    #Point location
    punto_rad = np.deg2rad([[lat, lon]])

    # Radio terrestre en metros
    earth_radius = 6371000  
    radius_rad = radius_metros / earth_radius  # Convertir a radianes

    # Crear BallTree con coordenadas de colegios (en radianes)
    tree = BallTree(colegios_rad, metric='haversine')

    # Obtener cantidad de colegios dentro del radio
    count = tree.query_radius(punto_rad, r=radius_rad, count_only=True)

    return count

def detectar_distrito(lat, lon, distritos_folium):
    geolocator = Nominatim(user_agent="st_app")
    location = geolocator.reverse((lat, lon), language="es")

    if location is None:
        st.error("No se pudo obtener la dirección.")
        return

    st.write(f"Dirección completa: {location.address}")

    # Normalizar todos los valores posibles del address
    address_parts = location.raw.get('address', {})
    for key, value in address_parts.items():
         # Normalizar el texto (sin tildes, minúsculas)
         value_normalizado = unidecode.unidecode(value.lower())
         if value_normalizado in distritos_folium:
             st.success(f"Distrito detectado: {value}")
             return value  # O lo que quieras hacer con el distrito

    #st.warning(address_parts.values())
    return None
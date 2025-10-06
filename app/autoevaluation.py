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
from folium.features import DivIcon
import unicodedata

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
        'cercado de lima':4,
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
        'santiago de surco': 7,   # agregado
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

    distritos = [
        "-", "Ate", "Barranco", "Breña", "Callao", "Carabayllo", "Cercado de Lima", 
        "Chaclacayo", "Chorrillos", "Cieneguilla", "Comas", "El Agustino", 
        "Independencia", "Jesús María", "La Molina", "La Victoria", "Lince", 
        "Los Olivos", "Lurigancho-Chosica", "Lurín", "Magdalena del Mar", 
        "Miraflores", "Pachacámac", "Pueblo Libre", "Puente Piedra", "Rímac", 
        "San Bartolo", "San Borja", "San Isidro", "San Juan de Lurigancho", 
        "San Juan de Miraflores", "San Luis", "San Martín de Porres", 
        "San Miguel", "Santa Anita", "Santa María del Mar", "Santa Rosa", 
        "Santiago de Surco", "Surquillo", "Villa El Salvador", 
        "Villa María del Triunfo"
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

    if "lat" not in st.session_state:
        st.session_state.lat = -12.05
    if "lon" not in st.session_state:
        st.session_state.lon = -77.04
    if "address" not in st.session_state:
        st.session_state.address = "Lima, Perú"
    if "message" not in st.session_state:
        st.session_state.message = None
    if "coords" not in st.session_state:
        st.session_state.coords = None
    if "active_tab" not in st.session_state:
        st.session_state.active_tab = 0  # Tab por defecto
    if "zoom_start" not in st.session_state:
        st.session_state.zoom_start = 18
    if "min_zoom" not in st.session_state:
        st.session_state.min_zoom = 18
    if "max_zoom" not in st.session_state:
        st.session_state.max_zoom = 18
    if "manipulate" not in st.session_state:
        st.session_state.manipulate = False
    if "last_active_tab" not in st.session_state:
        st.session_state.last_active_tab = st.session_state.active_tab
    # if "distrito_default" not in st.session_state:
    #     st.session_state.distrito_default = distritos[0]  # Valor inicial

    defaults_por_tab = {
        0: distritos[0],
        1: distritos[0],
        2: distritos[0],
    }

    if st.session_state.active_tab != st.session_state.last_active_tab:
        st.session_state["distrito_select"] = defaults_por_tab[st.session_state.active_tab]
        st.session_state.last_active_tab = st.session_state.active_tab

    col1, col2 = st.columns(2)

    with col1:
        tab_names = ["🔍 Buscar dirección", "🗺️ Buscar en el mapa", "🛰️ Buscar latitud y longitud"]
        active_tab = st.radio(
            "Selecciona una opción:", 
            tab_names, 
            index=st.session_state.active_tab, 
            horizontal=True
            )
        
        if active_tab != tab_names[st.session_state.active_tab]:
            st.session_state.active_tab = tab_names.index(active_tab)
            st.session_state.force_refresh = True
        else:
            st.session_state.force_refresh = False

        m = folium.Map(
                    location=[st.session_state.lat, st.session_state.lon],
                    zoom_start=st.session_state.zoom_start,
                    min_zoom=st.session_state.min_zoom,
                    max_zoom=st.session_state.max_zoom,
                    dragging=st.session_state.manipulate,
                    zoom_control=st.session_state.manipulate,
                    scrollWheelZoom=st.session_state.manipulate,
                    doubleClickZoom=st.session_state.manipulate
                )

        if st.session_state.active_tab == 0:
            st.session_state.manipulate = False
            
            folium.Marker(
                [st.session_state.lat, st.session_state.lon],
                popup=st.session_state.address,
                tooltip="Ubicación encontrada"
                ).add_to(m)

            if "coords" in st.session_state and st.session_state.coords:
                st.write(st.session_state.coords)
                st_folium(m, width=700, height=500)
            else:
                st.error(st.session_state.message)
                st.session_state.lat = -12.05
                st.session_state.lon = -77.04
            
        if st.session_state.active_tab == 1:
            if st.session_state.force_refresh:
                st.rerun()
            
            if st.session_state.lat and st.session_state.lon:
                    folium.Marker(
                        [st.session_state.lat, st.session_state.lon],
                        popup="Ubicación seleccionada",
                        tooltip="Ubicación guardada"
                    ).add_to(m)
   
            m.add_child(folium.LatLngPopup())

            st.write(st.session_state.coords)
            map_data=st_folium(m, width=700, height=500)

            if map_data["last_clicked"]:
                lat_clicked= map_data["last_clicked"]["lat"]
                lon_clicked = map_data["last_clicked"]["lng"]

                st.session_state.lat = lat_clicked
                st.session_state.lon = lon_clicked
                st.session_state.zoom = map_data["zoom"]
                st.session_state.coords = f"🌍 Coordenadas: **Latitud:** {round(lat_clicked,7)}, **Longitud:** {round(lon_clicked,7)}"
        if st.session_state.active_tab == 2:
            st.session_state.manipulate = False
            
            folium.Marker(
                [st.session_state.lat, st.session_state.lon],
                popup=st.session_state.address,
                tooltip="Ubicación encontrada"
                ).add_to(m)

            if "coords" in st.session_state and st.session_state.coords:
                #st.write(st.session_state.coords)
                st_folium(m, width=700, height=500)
            else:
                st.error(st.session_state.message)
                st.session_state.lat = -12.05
                st.session_state.lon = -77.04

    with col2:
    #-------------------------------------------------
        #--------------TAB 1------------------
        if st.session_state.active_tab == 0:
            st.session_state.distrito_default = distritos[0]

            #Text input address
            address_input = st.text_input("Ingrese dirección:")
            distrito_select = st.selectbox(
                "",
                distritos,
                index=distritos.index(st.session_state.get("distrito_select", defaults_por_tab[st.session_state.active_tab])),
                key="distrito_select",
                label_visibility="collapsed"
                )
            full_address = f"{address_input}, {distrito_select}, Lima, Perú"
            
            if st.button("🔍 Buscar dirección"):
                if address_input =="":
                    st.session_state.message = f"❌ Ingrese dirección"
                    st.session_state.coords = None
                    st.rerun()
                elif distrito_select == "-":
                    st.session_state.message = f"❌ Seleccione un distrito"
                    st.session_state.coords = None
                    st.rerun()
                else:
                    #Geocoding
                    geolocator = Nominatim(user_agent="myApp", timeout=20)
                    location = geolocator.geocode(full_address)

                    if location:
                        st.session_state.zoom_start = 18
                        st.session_state.min_zoom = 18
                        st.session_state.max_zoom = 18
                        st.session_state.manipulate = False
                        
                        st.session_state.lat = location.latitude
                        st.session_state.lon = location.longitude
                        st.session_state.address = full_address
                        st.session_state.message = f"📍 Dirección encontrada: {full_address}"
                        st.session_state.coords = f"🌍 Coordenadas: **Latitud:** {location.latitude}, **Longitud:** {location.longitude}"
                        st.rerun()
                    else:
                        st.session_state.message = f"❌ No se encontró la dirección. Verifica la información ingresada: {full_address}"
                        st.session_state.coords = None
                        st.rerun()
        #----------------------------Button: Buscar en el mapa--------------------------
        elif st.session_state.active_tab == 1:
            st.session_state.distrito_default = distritos[0]

            st.warning("🗺️ Desplázate y haz clic en el mapa para ubicar la vivienda")
            
            distrito_select = st.selectbox(
                "", 
                distritos,
                index=distritos.index(st.session_state.get("distrito_select", defaults_por_tab[st.session_state.active_tab])),
                key="distrito_select",
                label_visibility="collapsed"
                )

            #st.write(st.session_state.coords)

            st.session_state.zoom_start = 18
            st.session_state.min_zoom = 5
            st.session_state.max_zoom = 20
            st.session_state.manipulate = True

        elif st.session_state.active_tab == 2: 
            st.session_state.distrito_default = distritos[0]

            lat_input = st.text_input("Ingrese latitud:")
            lon_input = st.text_input("Ingrese longitud:")

            distrito_select = st.selectbox(
                "",
                distritos,
                index=distritos.index(st.session_state.get("distrito_select", defaults_por_tab[st.session_state.active_tab])),
                key="distrito_select",
                label_visibility="collapsed"
                )

            if st.button("🔍 Buscar dirección"):
                geolocator = Nominatim(user_agent="myApp", timeout=20)
                location = geolocator.reverse((lat_input,lon_input), language="es")

                full_address = location.address

                if location:
                    st.session_state.zoom_start = 18
                    st.session_state.min_zoom = 18
                    st.session_state.max_zoom = 18
                    st.session_state.manipulate = False
                    
                    st.session_state.lat = lat_input
                    st.session_state.lon = lon_input
                    st.session_state.address = full_address
                    st.session_state.message = f"📍 Dirección encontrada: {full_address}"
                    st.session_state.coords = f"🌍 Coordenadas: **Latitud:** {location.latitude}, **Longitud:** {location.longitude}"
                    st.rerun()
                else:
                    st.session_state.message = f"❌ No se encontró la dirección. Verifica la información ingresada: {full_address}"
                    st.session_state.coords = None
                    st.rerun()
        lat = st.session_state.lat
        lon = st.session_state.lon

        lat = float(lat)
        lon = float(lon)

    #with col2: #Colum 2
        #--------------------------------------------------------------------------------
        campos = [
                ("Mantenimiento (S/.)",0, "mantenimiento"),
                ("Área (m²)",0, "area"),
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
                valores.append(valor) #Add values

        if st.button("Estimar precio"):
            if distrito_select == "-":
                st.error("Seleccione distrito")
            else:
                #---------------------------------
                # Calculate prox
                num_colegios_prox = proximidad_entre(lat, lon, df_colegios)[0]
                num_malls_prox = proximidad_entre(lat, lon, df_malls)[0]
                num_hospitales_prox = proximidad_entre(lat, lon, df_hospitales)[0]
                num_est_tren_prox = proximidad_entre(lat, lon, df_tren)[0]
                num_est_metro_prox = proximidad_entre(lat, lon, df_metropolitano)[0]
                num_comisarias_prox = proximidad_entre(lat, lon, df_comisarias)[0]
                num_crimenes_prox = proximidad_entre(lat, lon, df_inpe)[0]

                total_servicios = num_colegios_prox + num_malls_prox + num_hospitales_prox + num_comisarias_prox
                total_servicios = int(total_servicios)

                total_transporte =  num_est_tren_prox + num_est_metro_prox 
                total_transporte = int(total_transporte)

                categoria_crimenes = pd.cut([num_crimenes_prox],bins=bins,labels=labels, include_lowest=True)
                categoria_crimenes = pd.Categorical(categoria_crimenes, categories=labels)
                categoria_crimenes = categoria_crimenes.codes[0] + 1
                categoria_crimenes = int(categoria_crimenes)

                #District edit
                distrito_select = normalizar_texto(distrito_select)
                valor_apeim = zona_apeim[distrito_select]

                #Add vaules
                valores.append(total_servicios)
                valores.append(total_transporte)
                valores.append(valor_apeim)
                valores.append(categoria_crimenes)

                #Print values
                #st.write("Valores enviados al modelo:", valores)
                #---------------------------------
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

def normalizar_texto(texto: str) -> str:
    return ''.join(
        c for c in unicodedata.normalize('NFD', texto)
        if unicodedata.category(c) != 'Mn'
    ).lower()
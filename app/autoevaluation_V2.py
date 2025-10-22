# Libraries
import streamlit as st
from folium.plugins import BeautifyIcon
from streamlit_folium import st_folium
import folium
import pandas as pd
import numpy as np
import pandas as pd
import os
import joblib
from sklearn.neighbors import BallTree
from geopy.geocoders import Nominatim
from session_utils import init_session_state # Initial configuration, "session_utils.py"

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

distritos = [
    "-", "ate", "barranco", "brena", "callao", "carabayllo", "cercado de lima", 
    "chaclacayo", "chorrillos", "cieneguilla", "comas", "el agustino", 
    "independencia", "jesus maria", "la molina", "la victoria", "lince", 
    "los olivos", "lurigancho-chosica", "lurin", "magdalena del mar", 
    "miraflores", "pachacamac", "pueblo libre", "puente piedra", "rimac", 
    "san bartolo", "san borja", "san isidro", "san juan de lurigancho", 
    "san juan de miraflores", "san luis", "san martin de porres", 
    "san miguel", "santa anita", "santa maria del mar", "santa rosa", 
    "santiago de surco", "surquillo", "villa el salvador", 
    "villa maria del triunfo"
]

zona_apeim = {
    'puente piedra': 1,'comas': 1,'carabayllo': 1,'ancon': 1,
    'independencia': 2,'los olivos': 2,'smp': 2,
    'san juan de lurigancho': 3,'sjl': 3,
    'lima cercado': 4,'cercado de lima':4,'rimac': 4,'brena': 4,'la victoria': 4,
    'ate': 5,'chaclacayo': 5,'lurigancho': 5,'santa anita': 5,'san luis': 5,'el agustino': 5,'cieneguilla': 5,
    'jesus maria': 6,'lince': 6,'pueblo libre': 6,'magdalena': 6,'san miguel': 6,
    'miraflores': 7,'san isidro': 7,'san borja': 7,'santiago de surco': 7,'surco': 7,'la molina': 7,
    'surquillo': 8,'barranco': 8,'chorrillos': 8,'san juan de miraflores': 8,'sjm': 8,
    'villa el salvador':9,'ves': 9,'villa maria del triunfo': 9,'vmt': 9,'lurin': 9,'pachacamac': 9,'punta hermosa': 9,
    'punta negra': 9,'san bartolo': 9,'pucusana': 9,'santa maria del mar': 9,
    'callao': 10,
}

# Functions
def proximidad_entre(lat, lon, df_servicio, radius_metros = 500):
    # Asegurarse que no hay NaNs
    df_servicio = df_servicio.dropna(subset=['latitud', 'longitud']).reset_index(drop=True)

    servicio_rad = np.deg2rad(df_servicio[['latitud', 'longitud']].values)

    #Point location
    punto_rad = np.deg2rad([[lat, lon]])

    # Radio terrestre en metros
    earth_radius = 6371000  
    radius_rad = radius_metros / earth_radius  # Convertir a radianes

    # Crear BallTree con coordenadas de colegios (en radianes)
    tree = BallTree(servicio_rad, metric='haversine')

    # Obtener cantidad de colegios dentro del radio
    count = tree.query_radius(punto_rad, r=radius_rad, count_only=True)

    return count

def data_servicios_prox(lat, lon, df_servicio, radius_metros=500):
    import numpy as np
    from sklearn.neighbors import BallTree
    import pandas as pd

    # Asegurarse de que no haya NaNs
    df_servicio = df_servicio.dropna(subset=['latitud', 'longitud']).reset_index(drop=True)

    # Convertir coordenadas a radianes
    servicio_rad = np.deg2rad(df_servicio[['latitud', 'longitud']].values)
    punto_rad = np.deg2rad([[lat, lon]])

    # Radio terrestre (en metros)
    earth_radius = 6371000  
    radius_rad = radius_metros / earth_radius  # Convertir radio a radianes

    # Crear árbol espacial
    tree = BallTree(servicio_rad, metric='haversine')

    # Obtener índices de los servicios dentro del radio
    indices = tree.query_radius(punto_rad, r=radius_rad)[0]  # <-- lista de índices

    # Filtrar el DataFrame original
    df_cercanos = df_servicio.iloc[indices].copy()

    return df_cercanos

# Subprocess
def subproceso_marcadores():
    folium.Circle(
            location=[st.session_state.lat, st.session_state.lon],
            radius=st.session_state.radius_metros,
            color="yellow",
            fill=True,
            fill_opacity=0.1,
            popup=f"Radio de {st.session_state.radius_metros}m"
        ).add_to(st.session_state["mapa"])

    # Malls
    if not st.session_state.data_malls.empty:
        for _, row in st.session_state.data_malls.iterrows():
            folium.Marker(
                location=[row["latitud"], row["longitud"]],
                popup=f"<b>Mercado:</b> {row['nombre']}",
                icon=BeautifyIcon(
                    icon="shopping-bag",           # ícono tipo tienda (Font Awesome)
                    icon_shape="marker",           # forma del marcador
                    border_color="#8A2BE2",        # violeta (borde)
                    border_width=2,                # grosor del borde
                    text_color="#8A2BE2",          # ícono violeta
                    background_color="white",      # fondo blanco
                    inner_icon_style="margin-top:0px;",  # centra el ícono
                    spin=False
                )
            ).add_to(st.session_state["mapa"])

    # Schools
    if not st.session_state.data_colegios.empty:
        for _, row in st.session_state.data_colegios.iterrows():
            folium.Marker(
                location=[row["latitud"], row["longitud"]],
                popup=f"<b>Colegio:</b> {row['nombre']}",
                icon=folium.Icon(color="blue", prefix="fa", icon="graduation-cap")  # usa ícono de colegio
            ).add_to(st.session_state["mapa"])

    # Hospitals
    if not st.session_state.data_hospitales.empty:
        for _, row in st.session_state.data_hospitales.iterrows():
            folium.Marker(
                location=[row["latitud"], row["longitud"]],
                popup=f"<b>Hospital:</b> {row['nombre']}",
                icon=folium.Icon(color="red", prefix="fa", icon="plus-square")  # ícono de hospital
            ).add_to(st.session_state["mapa"])

    # Train
    if not st.session_state.data_tren.empty:
        for _, row in st.session_state.data_tren.iterrows():
            folium.Marker(
                location=[row["latitud"], row["longitud"]],
                popup=f"<b>Estación de tren:</b> {row['nombre']}",
                icon=folium.Icon(color="green", prefix="fa", icon="train")  # ícono de tren
            ).add_to(st.session_state["mapa"])

    # Bus
    if not st.session_state.data_metropolitano.empty:
        for _, row in st.session_state.data_metropolitano.iterrows():
            folium.Marker(
                location=[row["latitud"], row["longitud"]],
                popup=f"<b>Estación de metropolitano:</b> {row['nombre']}",
                icon=folium.Icon(color="orange", prefix="fa", icon="bus")   # ícono de bus en color amarillo/naranja
            ).add_to(st.session_state["mapa"])
    
    # Police
    if not st.session_state.data_comisarias.empty:
        for _, row in st.session_state.data_comisarias.iterrows():
            folium.Marker(
                location=[row["latitud"], row["longitud"]],
                popup=f"<b>Comisaría:</b> {row['nombre']}",
                icon=BeautifyIcon(
                    icon="shield",                 # ícono (Font Awesome)
                    icon_shape="marker",           # forma de marcador
                    border_color="green",          # borde verde
                    border_width=1,                # borde delgado (por defecto es 3)
                    text_color="green",            # ícono verde
                    background_color="white",      # fondo blanco
                    spin=False
                )
            ).add_to(st.session_state["mapa"])

def subproceso_data_servicios():
    st.session_state.data_malls = data_servicios_prox(st.session_state.lat, st.session_state.lon, df_malls, st.session_state.radius_metros)[["nombre","latitud","longitud"]]
    st.session_state.data_colegios = data_servicios_prox(st.session_state.lat, st.session_state.lon, df_colegios, st.session_state.radius_metros)[["nombre","latitud","longitud"]]
    st.session_state.data_hospitales = data_servicios_prox(st.session_state.lat, st.session_state.lon, df_hospitales, st.session_state.radius_metros)[["nombre","latitud","longitud"]]
    st.session_state.data_tren = data_servicios_prox(st.session_state.lat, st.session_state.lon, df_tren, st.session_state.radius_metros)[["nombre","latitud","longitud"]]
    st.session_state.data_metropolitano = data_servicios_prox(st.session_state.lat, st.session_state.lon, df_metropolitano, st.session_state.radius_metros)[["nombre","latitud","longitud"]]
    st.session_state.data_comisarias = data_servicios_prox(st.session_state.lat, st.session_state.lon, df_comisarias, st.session_state.radius_metros)[["nombre","latitud","longitud"]]

    st.session_state.data_servicios = pd.concat([st.session_state.data_malls,
                                                    st.session_state.data_colegios, 
                                                    st.session_state.data_hospitales,
                                                    st.session_state.data_tren,
                                                    st.session_state.data_metropolitano,
                                                    st.session_state.data_comisarias], ignore_index=True)
    
def subproceso_num_servicios():
    st.session_state.num_colegios_prox = proximidad_entre(st.session_state.lat, st.session_state.lon, df_colegios, st.session_state.radius_metros)[0]
    st.session_state.num_malls_prox = proximidad_entre(st.session_state.lat, st.session_state.lon, df_malls, st.session_state.radius_metros)[0]
    st.session_state.num_hospitales_prox = proximidad_entre(st.session_state.lat, st.session_state.lon, df_hospitales, st.session_state.radius_metros)[0]
    st.session_state.num_est_tren_prox = proximidad_entre(st.session_state.lat, st.session_state.lon, df_tren, st.session_state.radius_metros)[0]
    st.session_state.num_est_metro_prox = proximidad_entre(st.session_state.lat, st.session_state.lon, df_metropolitano, st.session_state.radius_metros)[0]
    st.session_state.num_comisarias_prox = proximidad_entre(st.session_state.lat, st.session_state.lon, df_comisarias, st.session_state.radius_metros)[0]
    st.session_state.num_crimenes_prox = proximidad_entre(st.session_state.lat, st.session_state.lon, df_inpe, st.session_state.radius_metros)[0]

def subproceso_plot_num_servicios():
    st.write(f"<br>**Servicios en un radio de {st.session_state.radius_metros} metros**", unsafe_allow_html=True)

    servicios = {"**N° Colegios:**":st.session_state.num_colegios_prox, "**N° Mercados:**":st.session_state.num_malls_prox,
                    "**N° Hospitales:**":st.session_state.num_hospitales_prox,"**N° Estaciones de tren:**":st.session_state.num_est_tren_prox,
                    "**N° Estaciones de metropolitano:**":st.session_state.num_est_metro_prox,"**N° Comisarias:**":st.session_state.num_comisarias_prox}
    
    col1, col2 = st.columns([1, 2])
    for servicio in servicios:
        with col1:
            if servicios[servicio] > 0:
                st.markdown(f"{servicio}")
        with col2:
            if servicios[servicio] > 0:
                st.write(f"{servicios[servicio]}")

def reset_map():
    st.session_state.data_servicios = pd.DataFrame()
    st.session_state.pred = 0

def option_change():
    st.session_state.active_option_change = True

# Main
def run():
    # Initial configuration
    init_session_state() 

    # Local variables
    distrito_valor_dashboard = "-"
    direccion_select_dashboard = "-"
    area_valor_dashboard = 0
    num_dorm_valor_dashboard = 0
    num_banios_valor_dashboard = 0
    precio_valor_dashboard = 0

    # GUI
    st.title("Autoevaluador de Precio de Vivienda")

    # Check data from dashboard
    if st.session_state["data"] is not None:
        df_dashboard = st.session_state["data"]
        opciones = st.session_state["data"].iloc[:,4].tolist()
        opciones.insert(0, "-")

        valor_actual = st.session_state.get("direccion_select_dashboard", 
                                            opciones[0] if opciones else None)

        if opciones != "-":
            st.write("**Top oportunidades según tus prioridades seleccionadas:**")
            st.info("""
                Si desea estimar el precio de una vivienda que no figure en la lista desplegable, mantenga la opción en **"-"**.  
                Si desea visualizar una vivienda del **🏆 Top oportunidades según tus prioridades**, selecciónela desde la lista desplegable.
            """)

            direccion_select_dashboard = st.selectbox(
                "Selecciona una dirección:",
                opciones,
                index = opciones.index(valor_actual) if valor_actual in opciones else 0,
                key="direccion_select_dashboard",
                label_visibility="collapsed",
                on_change=option_change
            )

            if valor_actual == "-" and st.session_state.active_option_change == True:
                reset_map()
                st.session_state.active_option_change = False

            if valor_actual != "-":
                filtro=df_dashboard["direccion_completa"] == direccion_select_dashboard
                st.session_state.lat = df_dashboard.loc[filtro, "latitud"].iloc[0]
                st.session_state.lon = df_dashboard.loc[filtro, "longitud"].iloc[0]
                distrito_valor_dashboard = df_dashboard.loc[filtro, "distrito"].iloc[0]
                area_valor_dashboard = df_dashboard.loc[filtro, "area_m2"].iloc[0]
                num_dorm_valor_dashboard = df_dashboard.loc[filtro, "num_dorm"].iloc[0]
                num_banios_valor_dashboard = df_dashboard.loc[filtro, "num_banios"].iloc[0]
                precio_valor_dashboard = df_dashboard.loc[filtro, "precio_pen"].iloc[0]

        else:
            st.warning("No hay direcciones disponibles para seleccionar.")
    else:
        st.info("""
            **No se ha cargado ninguna oportunidad según tus prioridades seleccionadas.**
            
            Para trabajar con esta opción, sigue estos pasos:
            
            1. **Menú de navegación:** Ingresa a la página **Dashboard**.  
            2. **Configuraciones:** Selecciona el distrito o los distritos que deseas analizar.  
            3. **🏆 Top oportunidades según tus prioridades:** En la lista, marca la casilla **"Seleccionar"** de las viviendas que desees visualizar en el **Autoevaluador del Precio de Vivienda**.
        """)


    # Create Map
    st.session_state["mapa"] = folium.Map(
                    location=[st.session_state.lat, st.session_state.lon],
                    zoom_start=st.session_state.zoom_start,
                    min_zoom=st.session_state.min_zoom,
                    max_zoom=st.session_state.max_zoom,
                    dragging=st.session_state.manipulate,
                    zoom_control=st.session_state.manipulate,
                    scrollWheelZoom=st.session_state.manipulate,
                    doubleClickZoom=st.session_state.manipulate
                )

    folium.Marker(
                [st.session_state.lat, st.session_state.lon],
                popup=st.session_state.address,
                tooltip="Ubicación encontrada"
                ).add_to(st.session_state["mapa"])
    
    st.session_state["mapa"].add_child(folium.LatLngPopup())
    
    # Create Markers
    if not st.session_state.data_servicios.empty:
        subproceso_marcadores()

    if distrito_valor_dashboard == "-":
        st.write("**Seleccione un tipo de búsqueda:**")    

    col1, col2 = st.columns(2)

    # COLUMN 1
    with col1:
        
        if distrito_valor_dashboard == "-":
            tab_names = ["🏠 Buscar dirección", "🗺️ Buscar en el mapa", "🛰️ Buscar latitud y longitud"]
            
            active_tab = st.radio(
                    "", 
                    tab_names, 
                    index=st.session_state.active_tab, 
                    horizontal=True,
                    label_visibility="collapsed"
                    )

            if active_tab != tab_names[st.session_state.active_tab]:
                st.session_state.active_tab = tab_names.index(active_tab)
                st.session_state.message_error = None
                st.session_state.force_refresh = True
                reset_map()
                st.rerun()
            else:
                st.session_state.force_refresh = False
        
        st.write(st.session_state.coords)
        map_data = st_folium(st.session_state["mapa"], width=700, height=500)

        if distrito_valor_dashboard == "-":
            # COLUMN 1 TAB 0
            if st.session_state.active_tab == 0:
                st.session_state.zoom_start = 16
                st.session_state.min_zoom = 5
                st.session_state.max_zoom = 20
                st.session_state.manipulate = True

            # COLUMN 1 TAB 1
            if st.session_state.active_tab == 1:         
                if map_data["last_clicked"]:
                    lat_clicked= map_data["last_clicked"]["lat"]
                    lon_clicked = map_data["last_clicked"]["lng"]

                    st.session_state.lat = lat_clicked
                    st.session_state.lon = lon_clicked
                    st.session_state.zoom = map_data["zoom"]
                    st.session_state.coords = f"🌍 Coordenadas: **Latitud:** {round(lat_clicked,7)}, **Longitud:** {round(lon_clicked,7)}"

                    st.session_state.message_error = None # Error message button "Estimar precio"
                    reset_map()
                    st.rerun()
            
            # COLUMN 1 TAB 2
            if st.session_state.active_tab == 2:
                st.session_state.zoom_start = 16
                st.session_state.min_zoom = 5
                st.session_state.max_zoom = 20
                st.session_state.manipulate = True

            if st.session_state.pred != 0:
                st.success(f"El precio estimado por el modelo es: **S/. {st.session_state.pred:,.2f}**") 
                subproceso_plot_num_servicios()

    # COLUMN 2    
    with col2:
        if distrito_valor_dashboard == "-":
            # COLLUMN 2 TAB 0
            if st.session_state.active_tab == 0:
                st.session_state.distrito_default = distritos[0]

                st.warning("""
                    🏠 Ingresa la **dirección** y el **distrito**, luego presiona **Buscar dirección** para ubicar la vivienda en el mapa
                        """)

                col1, col2 = st.columns([1, 2])
                with col1:
                    st.markdown(f"**Dirección:**")
                    st.markdown(f"**Distrito:**")
                with col2:
                    address_input = st.text_input("", direccion_select_dashboard, label_visibility="collapsed")

                    if distrito_valor_dashboard == "-":
                        distrito_select = st.selectbox(
                            "",
                            distritos,
                            index=distritos.index(distrito_valor_dashboard) if distrito_valor_dashboard in distritos else "-",
                            key="distrito_select",
                            label_visibility="collapsed"
                            )
                        
                        full_address = f"{address_input}, {distrito_select}, Lima, Perú"
                    else:
                        st.write(f"**Distrito:** {distrito_valor_dashboard}")
                        distrito_select = distrito_valor_dashboard

                if st.button("🔍 Buscar dirección"):
                    st.session_state.message_error = None # Error message button "Estimar precio"
                    reset_map()

                    if address_input =="-" or address_input =="":
                        st.error("❌ Ingrese dirección")
                    elif distrito_select == "-":
                        st.error("❌ Seleccione un distrito")
                    else: 
                        geolocator = Nominatim(user_agent="myApp", timeout=20)
                        location = geolocator.geocode(full_address)

                        if location:
                            st.session_state.zoom_start = 16
                            st.session_state.min_zoom = 5
                            st.session_state.max_zoom = 20
                            st.session_state.manipulate = False
                            
                            st.session_state.lat = location.latitude
                            st.session_state.lon = location.longitude
                            st.session_state.address = full_address
                            st.session_state.message = f"📍 Dirección encontrada: {full_address}"
                            st.session_state.coords = f"🌍 Coordenadas: **Latitud:** {location.latitude}, **Longitud:** {location.longitude}"
                        else:
                            st.session_state.message = f"❌ No se encontró la dirección. Verifica la información ingresada: {full_address}"
                        
                        st.rerun()

            # COLLUMN 2 TAB 1
            if st.session_state.active_tab == 1:
                st.session_state.distrito_default = distritos[0]
                
                st.warning("""
                        🗺️ Desplázate y haz **clic** en el mapa para ubicar la vivienda
                        """)

                col1, col2 = st.columns([1, 2])
                with col1:
                    st.markdown(f"**Distrito:**")

                with col2:
                    distrito_select = st.selectbox(
                        "", 
                        distritos,
                        index=distritos.index(distrito_valor_dashboard) if distrito_valor_dashboard in distritos else 0,
                        key="distrito_select",
                        label_visibility="collapsed"
                        )

                    st.session_state.zoom_start = 16
                    st.session_state.min_zoom = 5
                    st.session_state.max_zoom = 20
                    st.session_state.manipulate = True

            # COLLUMN 2 TAB 2
            if st.session_state.active_tab == 2:
                st.session_state.distrito_default = distritos[0]

                st.warning("""
                    🛰️ Ingresa la **Latitud** y el **Longitud**, luego presiona **Buscar ubicación** para ubicar la vivienda en el mapa
                    """)

                col1, col2 = st.columns([1, 2])
                with col1:
                    st.markdown(f"**Ingrese latitud:**")
                    st.markdown(f"**Ingrese longitud:**")
                with col2:
                    st.session_state.lat = st.number_input("",value=st.session_state.lat, label_visibility="collapsed")
                    st.session_state.lon = st.number_input("",value=st.session_state.lon, label_visibility="collapsed")

                if st.button("🔍 Buscar ubicación"):
                    st.session_state.message_error = None # Error message button "Estimar precio"
                    reset_map()

                    geolocator = Nominatim(user_agent="myApp", timeout=20)
                    location = geolocator.reverse((st.session_state.lat, st.session_state.lon), language="es")

                    full_address = location.address

                    if location:
                        st.session_state.address = full_address
                        st.session_state.message = f"📍 Dirección encontrada: {full_address}"
                        st.session_state.coords = f"🌍 Coordenadas: **Latitud:** {location.latitude}, **Longitud:** {location.longitude}"
                        st.rerun()
                    else:
                        st.session_state.message = f"❌ No se encontró la dirección. Verifica la información ingresada: {full_address}"
                        st.rerun()

                col1, col2 = st.columns([1, 2])
                with col1:
                    st.markdown(f"**Distrito:**")
                with col2:
                    if distrito_valor_dashboard == "-":
                        distrito_select = st.selectbox(
                            "",
                            distritos,
                            index=distritos.index(distrito_valor_dashboard) if distrito_valor_dashboard in distritos else 0,
                            key="distrito_select",
                            label_visibility="collapsed"
                            )
                    else:
                        st.write(f"**Distrito:** {distrito_valor_dashboard}")
                        distrito_select = distrito_valor_dashboard
            
            # Model input data
            campos = [
                    ("Mantenimiento (S/.)",0, "mantenimiento"),
                    ("Área (m²)",area_valor_dashboard, "area"),
                    ("Nº Dormitorios",num_dorm_valor_dashboard, "dormitorio"),
                    ("Nº Baños",num_banios_valor_dashboard, "baño"),
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

                        valor = st.selectbox("", min_val,
                                                label_visibility="collapsed", key = key)
                    
                    elif key == "antiguedad":
                        opciones_antiguedad = ["No sé"] + list(range(0, 101)) 
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
                                max_value=10000,
                                label_visibility="collapsed", 
                                key=key
                            )
                        else:
                            valor = np.nan
                                
                    else:
                        valor = st.number_input("", min_value=min_val,
                                            label_visibility="collapsed", key = key)

                # Add vaules
                valores.append(valor)

            # Estimate using the model
            if st.button("Estimar precio"):
                if distrito_select == "-":
                    st.session_state.message_error = "❌ Seleccione distrito"
                    reset_map()
                    st.rerun()
                elif valores[1] == 0:
                    st.session_state.message_error = "❌ Ingrese Área (m²)"
                    reset_map()
                    st.rerun()
                elif valores[2] == 0:
                    st.session_state.message_error = "❌ Ingrese Nº Dormitorios"
                    reset_map()
                    st.rerun()
                    
                else:
                    subproceso_num_servicios()
                    subproceso_data_servicios()
                    st.session_state.message_error = None # Error message button "Estimar precio"

                    total_servicios = st.session_state.num_colegios_prox + st.session_state.num_malls_prox 
                    + st.session_state.num_hospitales_prox + st.session_state.num_comisarias_prox
                    total_servicios = int(total_servicios)

                    total_transporte = st.session_state.num_est_tren_prox + st.session_state.num_est_metro_prox 
                    total_transporte = int(total_transporte)

                    categoria_crimenes = pd.cut([st.session_state.num_crimenes_prox],bins=bins,labels=labels, include_lowest=True)
                    categoria_crimenes = pd.Categorical(categoria_crimenes, categories=labels)
                    categoria_crimenes = categoria_crimenes.codes[0] + 1
                    categoria_crimenes = int(categoria_crimenes)

                    valor_apeim = zona_apeim[distrito_select]

                    # Add vaules 
                    valores.append(total_servicios)
                    valores.append(total_transporte)
                    valores.append(valor_apeim)
                    valores.append(categoria_crimenes)

                    column_names = ['mantenimiento_soles', 'area_m2', 'num_dorm', 'num_banios', 'num_estac',
                                    'antiguedad','total_servicios_prox', 'total_transporte_aprox', 'zona_apeim_cod','categoria_crimenes_cod']
                    
                    input_df = pd.DataFrame([valores], columns=column_names)

                    if distrito_select in ['miraflores', 'surco', 'san isidro','barranco']:
                        st.session_state.pred = model_h.predict(input_df)[0]
                    else:
                        st.session_state.pred = model_l.predict(input_df)[0]
                    
                    st.rerun()

                    st.warning("Mueve el mapa para actualizar la vista.")
            if st.session_state.message_error != None:
                st.error(st.session_state.message_error)

        else:
            # Visual representation of dashboard data
            col1, col2 = st.columns([1, 2])
            with col1:
                st.markdown(f"**Dirección:**")
                st.markdown(f"**Distrito:**")
                st.markdown(f"**Área (m²)**")
                st.markdown(f"**Nº Dormitorios**")
                st.markdown(f"**Nº Baños**")
                st.markdown(f"**Precio (S/.)**")

            with col2:
                st.write(direccion_select_dashboard)
                st.write(distrito_valor_dashboard)
                st.write(str(area_valor_dashboard))
                st.write(str(int(num_dorm_valor_dashboard)))
                st.write(str(int(num_banios_valor_dashboard)))
                st.write(str(precio_valor_dashboard))

            subproceso_data_servicios()
            subproceso_num_servicios()
            subproceso_plot_num_servicios()

            
            
        



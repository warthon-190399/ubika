import os
import joblib
import numpy as np
import pandas as pd
import folium
import streamlit as st
from folium.plugins import BeautifyIcon
from streamlit_folium import st_folium
from sklearn.neighbors import BallTree
from geopy.geocoders import Nominatim
from session_utils import init_session_state
 
# ── Paths & Data ───────────────────────────────────────────────────────────────
BASE_DIR  = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
PROCESSED = os.path.join(BASE_DIR, "data", "processed")
MODELS    = os.path.join(BASE_DIR, "models")
 
df_malls         = pd.read_csv(os.path.join(PROCESSED, "malls_processed.csv"))
df_colegios      = pd.read_csv(os.path.join(PROCESSED, "colegios_processed.csv"))
df_hospitales    = pd.read_csv(os.path.join(PROCESSED, "hospitales_processed.csv"))
df_tren          = pd.read_csv(os.path.join(PROCESSED, "tren_processed.csv"))
df_metropolitano = pd.read_csv(os.path.join(PROCESSED, "metropolitano_processed.csv"))
df_comisarias    = pd.read_csv(os.path.join(PROCESSED, "comisarias_processed.csv"))
df_inpe          = pd.read_csv(os.path.join(PROCESSED, "inpe_processed.csv"))
 
model_l = joblib.load(os.path.join(MODELS, "randomforest_model_l.pkl"))
model_h = joblib.load(os.path.join(MODELS, "catboost_model_h.pkl"))
 
# ── Constants ──────────────────────────────────────────────────────────────────
DISTRITOS = [
    "-", "ate", "barranco", "brena", "callao", "carabayllo", "cercado de lima",
    "chaclacayo", "chorrillos", "cieneguilla", "comas", "el agustino",
    "independencia", "jesus maria", "la molina", "la victoria", "lince",
    "los olivos", "lurigancho-chosica", "lurin", "magdalena del mar",
    "miraflores", "pachacamac", "pueblo libre", "puente piedra", "rimac",
    "san bartolo", "san borja", "san isidro", "san juan de lurigancho",
    "san juan de miraflores", "san luis", "san martin de porres",
    "san miguel", "santa anita", "santa maria del mar", "santa rosa",
    "santiago de surco", "surquillo", "villa el salvador", "villa maria del triunfo",
]
 
ZONA_APEIM = {
    "puente piedra": 1, "comas": 1, "carabayllo": 1,
    "independencia": 2, "los olivos": 2,
    "san juan de lurigancho": 3,
    "cercado de lima": 4, "rimac": 4, "brena": 4, "la victoria": 4,
    "ate": 5, "chaclacayo": 5, "lurigancho-chosica": 5, "santa anita": 5,
    "san luis": 5, "el agustino": 5, "cieneguilla": 5,
    "jesus maria": 6, "lince": 6, "pueblo libre": 6,
    "magdalena del mar": 6, "san miguel": 6,
    "miraflores": 7, "san isidro": 7, "san borja": 7,
    "santiago de surco": 7, "la molina": 7,
    "surquillo": 8, "barranco": 8, "chorrillos": 8, "san juan de miraflores": 8,
    "villa el salvador": 9, "villa maria del triunfo": 9, "lurin": 9,
    "pachacamac": 9, "san bartolo": 9, "santa maria del mar": 9,
    "callao": 10,
}
 
HIGH_VALUE_DISTRICTS = {"miraflores", "santiago de surco", "san isidro", "barranco"}
 
MARKER_CONFIG = [
    ("data_malls",         "Mercado",                   None,     None,             "shopping-bag", "#8A2BE2"),
    ("data_colegios",      "Colegio",                   "blue",   "graduation-cap", None,           None),
    ("data_hospitales",    "Hospital",                  "red",    "plus-square",    None,           None),
    ("data_tren",          "Estación de tren",          "green",  "train",          None,           None),
    ("data_metropolitano", "Estación de metropolitano", "orange", "bus",            None,           None),
    ("data_comisarias",    "Comisaría",                 None,     None,             "shield",       "green"),
]
 
# ── Helpers de lógica pura ─────────────────────────────────────────────────────
def get_nearby(lat, lon, df, radius_m=1000):
    df = df.dropna(subset=["latitud", "longitud"]).reset_index(drop=True)
    tree = BallTree(np.deg2rad(df[["latitud", "longitud"]].values), metric="haversine")
    idx  = tree.query_radius(np.deg2rad([[lat, lon]]), r=radius_m / 6_371_000)[0]
    return df.iloc[idx][["nombre", "latitud", "longitud"]].copy()
 
def count_nearby(lat, lon, df, radius_m=1000):
    df = df.dropna(subset=["latitud", "longitud"])
    tree = BallTree(np.deg2rad(df[["latitud", "longitud"]].values), metric="haversine")
    return int(tree.query_radius(np.deg2rad([[lat, lon]]), r=radius_m / 6_371_000, count_only=True)[0])
 
def build_map(lat, lon, radius_m, services):
    m = folium.Map(location=[lat, lon], zoom_start=16, min_zoom=5, max_zoom=20)
    folium.Marker([lat, lon], tooltip="Ubicación").add_to(m)
    folium.Circle([lat, lon], radius=radius_m, color="yellow", fill=True, fill_opacity=0.1).add_to(m)
    m.add_child(folium.LatLngPopup())
 
    for key, label, f_color, f_icon, b_icon, b_color in MARKER_CONFIG:
        df = services.get(key, pd.DataFrame())
        if df.empty:
            continue
        for _, row in df.iterrows():
            if b_icon:
                icon = BeautifyIcon(icon=b_icon, icon_shape="marker",
                                    border_color=b_color, text_color=b_color,
                                    background_color="white", border_width=2)
            else:
                icon = folium.Icon(color=f_color, prefix="fa", icon=f_icon)
            folium.Marker([row["latitud"], row["longitud"]],
                          popup=f"<b>{label}:</b> {row['nombre']}", icon=icon).add_to(m)
    return m
 
# ══════════════════════════════════════════════════════════════════════════════
# APP
# ══════════════════════════════════════════════════════════════════════════════
def run():
    init_session_state()
    st.title("Autoevaluador de Precio de Vivienda")
    
    TAB_NAMES = ["🏠 Buscar dirección", "🗺️ Buscar en el mapa", "🛰️ Lat / Lon"]
    col_map, col_ctrl = st.columns(2)
    
    # ── Columna izquierda: mapa ────────────────────────────────────────────────────
    with col_map:
        active_tab = st.radio("", TAB_NAMES,
                            index=st.session_state.get("active_tab", 0),
                            horizontal=True, label_visibility="collapsed")
        st.session_state.active_tab = TAB_NAMES.index(active_tab)
    
        if st.session_state.get("coords"):
            st.write(st.session_state.coords)
    
        map_data = st_folium(
            build_map(st.session_state.lat, st.session_state.lon,
                    st.session_state.get("radius_metros", 1000),
                    st.session_state.get("services", {})),
            width=700, height=500
        )
    
        # Clic en el mapa (Tab 1)
        if st.session_state.active_tab == 1 and map_data.get("last_clicked"):
            st.session_state.lat      = map_data["last_clicked"]["lat"]
            st.session_state.lon      = map_data["last_clicked"]["lng"]
            st.session_state.coords   = f"🌍 **Lat:** {st.session_state.lat:.7f}, **Lon:** {st.session_state.lon:.7f}"
            st.session_state.services = {}
            st.session_state.pred     = 0
            st.rerun()
    
        if st.session_state.get("pred"):
            st.success(f"Precio estimado: **S/. {st.session_state.pred:,.2f}**")
    
            counts   = st.session_state.get("counts", {})
            radius_m = st.session_state.get("radius_metros", 1000)
            st.write(f"<br>**Servicios en un radio de {radius_m} m**", unsafe_allow_html=True)
            for key, label in [("data_colegios", "N° Colegios"), ("data_malls", "N° Malls"),
                                ("data_hospitales", "N° Hospitales"), ("data_tren", "N° Est. tren"),
                                ("data_metropolitano", "N° Est. metropolitano"), ("data_comisarias", "N° Comisarías")]:
                n = counts.get(key, 0)
                if n > 0:
                    c1, c2 = st.columns([1, 2])
                    c1.markdown(f"**{label}:**")
                    c2.write(n)
    
    # ── Columna derecha: controles ─────────────────────────────────────────────────
    with col_ctrl:
        distrito_select = "-"
    
        if st.session_state.active_tab == 0:
            st.warning("🏠 Ingresa la **dirección** y el **distrito**, luego presiona **Buscar dirección**.")
            c1, c2 = st.columns([1, 2])
            c1.markdown("**Dirección:**")
            c1.markdown("**Distrito:**")
            address_input   = c2.text_input("", label_visibility="collapsed", key="address_input")
            distrito_select = c2.selectbox("", DISTRITOS, label_visibility="collapsed", key="distrito_select")
    
            if st.button("🔍 Buscar dirección"):
                if not address_input:
                    st.error("❌ Ingrese dirección")
                elif distrito_select == "-":
                    st.error("❌ Seleccione un distrito")
                else:
                    full = f"{address_input}, {distrito_select}, Lima, Perú"
                    loc  = Nominatim(user_agent="myApp", timeout=20).geocode(full)
                    if loc:
                        st.session_state.lat      = loc.latitude
                        st.session_state.lon      = loc.longitude
                        st.session_state.coords   = f"📍 {full}"
                        st.session_state.services = {}
                        st.session_state.pred     = 0
                        st.rerun()
                    else:
                        st.error(f"❌ No se encontró: {full}")
    
        elif st.session_state.active_tab == 1:
            st.warning("🗺️ Haz **clic** en el mapa para ubicar la vivienda.")
            c1, c2 = st.columns([1, 2])
            c1.markdown("**Distrito:**")
            distrito_select = c2.selectbox("", DISTRITOS, label_visibility="collapsed", key="distrito_select")
    
        elif st.session_state.active_tab == 2:
            st.warning("🛰️ Ingresa **Latitud** y **Longitud**, luego presiona **Buscar ubicación**.")
            c1, c2 = st.columns([1, 2])
            c1.markdown("**Latitud:**")
            c1.markdown("**Longitud:**")
            c1.markdown("**Distrito:**")
            st.session_state.lat = c2.number_input("", value=st.session_state.lat,
                                                    label_visibility="collapsed", key="lat_input")
            st.session_state.lon = c2.number_input("", value=st.session_state.lon,
                                                    label_visibility="collapsed", key="lon_input")
            distrito_select = c2.selectbox("", DISTRITOS, label_visibility="collapsed", key="distrito_select")
    
            if st.button("🔍 Buscar ubicación"):
                loc = Nominatim(user_agent="myApp", timeout=20).reverse(
                    (st.session_state.lat, st.session_state.lon), language="es")
                if loc:
                    st.session_state.coords   = f"📍 {loc.address}"
                    st.session_state.services = {}
                    st.session_state.pred     = 0
                    st.rerun()
    
        # ── Inputs del modelo ──────────────────────────────────────────────────────
        campos = [
            ("Mantenimiento (S/.)", "mantenimiento"),
            ("Área (m²)",           "area"),
            ("Nº Dormitorios",      "dormitorio"),
            ("Nº Baños",            "banio"),
            ("Nº Estacionamientos", "estacionamiento"),
            ("Antigüedad (años)",   "antiguedad"),
        ]
        valores = []
        for label, key in campos:
            c1, c2 = st.columns([1, 2])
            c1.markdown(f"**{label}**")
            with c2:
                if key == "mantenimiento":
                    opt   = st.selectbox("", ["Ingresar valor", "No sé"], label_visibility="collapsed", key=f"{key}_opt")
                    valor = st.number_input("", min_value=0, max_value=10000,
                                            label_visibility="collapsed", key=key) \
                            if opt == "Ingresar valor" else np.nan
                elif key == "antiguedad":
                    sel   = st.selectbox("", ["No sé"] + list(range(0, 101)), label_visibility="collapsed", key=key)
                    valor = np.nan if sel == "No sé" else sel
                else:
                    valor = st.number_input("", min_value=0, label_visibility="collapsed", key=key)
            valores.append(valor)
    
        # ── Estimación ─────────────────────────────────────────────────────────────
        if st.button("Estimar precio"):
            if distrito_select == "-":
                st.error("❌ Seleccione distrito")
            elif valores[1] == 0:
                st.error("❌ Ingrese Área (m²)")
            elif valores[2] == 0:
                st.error("❌ Ingrese Nº Dormitorios")
            else:
                radius_m = st.session_state.get("radius_metros", 1000)
    
                nearby = {
                    "data_malls":         get_nearby(st.session_state.lat, st.session_state.lon, df_malls,         radius_m),
                    "data_colegios":      get_nearby(st.session_state.lat, st.session_state.lon, df_colegios,      radius_m),
                    "data_hospitales":    get_nearby(st.session_state.lat, st.session_state.lon, df_hospitales,    radius_m),
                    "data_tren":          get_nearby(st.session_state.lat, st.session_state.lon, df_tren,          radius_m),
                    "data_metropolitano": get_nearby(st.session_state.lat, st.session_state.lon, df_metropolitano, radius_m),
                    "data_comisarias":    get_nearby(st.session_state.lat, st.session_state.lon, df_comisarias,    radius_m),
                }
                counts = {k: len(v) for k, v in nearby.items()}
                counts["num_crimenes"] = count_nearby(st.session_state.lat, st.session_state.lon, df_inpe, radius_m)
    
                crimen_cat = int(pd.cut([counts["num_crimenes"]],
                                        bins=[-1, 14.5, 24.5, 49.5, np.inf],
                                        labels=[1, 2, 3, 4], include_lowest=True).codes[0] + 1)
    
                features = valores + [
                    int(counts["data_colegios"] + counts["data_malls"] +
                        counts["data_hospitales"] + counts["data_comisarias"]),
                    int(counts["data_tren"] + counts["data_metropolitano"]),
                    ZONA_APEIM.get(distrito_select, 5),
                    crimen_cat,
                ]
                cols = ["mantenimiento_soles", "area_m2", "num_dorm", "num_banios", "num_estac",
                        "antiguedad", "total_servicios_prox", "total_transporte_aprox",
                        "zona_apeim_cod", "categoria_crimenes_cod"]
    
                model = model_h if distrito_select in HIGH_VALUE_DISTRICTS else model_l
                st.session_state.pred     = model.predict(pd.DataFrame([features], columns=cols))[0]
                st.session_state.services = nearby
                st.session_state.counts   = counts
                st.rerun()
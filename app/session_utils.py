import streamlit as st
import folium
import pandas as pd

def init_session_state():
    # Variables base
    defaults = {
        "lat": -12.05,"lon": -77.04,
        "address": "Lima, Perú","message": None,
        "active_tab": 1,"active_option_change": False,
        "zoom_start": 16,"min_zoom": 5,"max_zoom": 20,
        "manipulate": False,"radius_metros": 500,
        "num_colegios_prox": 0,"num_malls_prox": 0,
        "num_hospitales_prox": 0,"num_est_tren_prox": 0,
        "num_est_metro_prox": 0,"num_comisarias_prox": 0,
        "num_crimenes_prox": 0,"pred": 0, 
        "data":None, "message_error": None
    }

    for key, value in defaults.items():
        st.session_state.setdefault(key, value)

    # Variables que dependen de otras
    st.session_state.setdefault("coords",f"🌍 Coordenadas: **Latitud:** {st.session_state.lat}, **Longitud:** {st.session_state.lon}")
    st.session_state.setdefault("last_active_tab", st.session_state.active_tab)

    # Objetos complejos
    st.session_state.setdefault("mapa",folium.Map(
            location=[st.session_state.lat, st.session_state.lon],
            zoom_start=st.session_state.zoom_start,
            min_zoom=st.session_state.min_zoom,
            max_zoom=st.session_state.max_zoom,
            dragging=st.session_state.manipulate,
            zoom_control=st.session_state.manipulate,
            scrollWheelZoom=st.session_state.manipulate,
            doubleClickZoom=st.session_state.manipulate,))
    
    # DataFrames vacíos
    st.session_state.setdefault("data_servicios", pd.DataFrame())
    st.session_state.setdefault("data_malls", pd.DataFrame())
    st.session_state.setdefault("data_colegios", pd.DataFrame())
    st.session_state.setdefault("data_hospitales", pd.DataFrame())
    st.session_state.setdefault("data_tren", pd.DataFrame())
    st.session_state.setdefault("data_metropolitano", pd.DataFrame())
    st.session_state.setdefault("data_comisarias", pd.DataFrame())
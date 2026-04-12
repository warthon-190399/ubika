import streamlit as st
import pandas as pd
 
def init_session_state():
    defaults = {
        "lat":              -12.0464,   # Lima centro
        "lon":              -77.0428,
        "zoom_start":       16,
        "min_zoom":         5,
        "max_zoom":         20,
        "manipulate":       True,
        "address":          "",
        "coords":           "",
        "message":          None,
        "message_error":    None,
        "active_tab":       0,
        "pred":             0,
        "services":         {},
        "counts":           {},
        "radius_metros":    1000,
        "pagina_anterior":  None,
        "data":             None,
        "force_refresh":    False,
        "active_option_change": False,
    }
    for key, value in defaults.items():
        st.session_state.setdefault(key, value)
 
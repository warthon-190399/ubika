import os
import numpy as np
import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pydeck as pdk

# ── Data ───────────────────────────────────────────────────────────────────────
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
df = pd.read_csv(os.path.join(BASE_DIR, "data", "processed", "data_preprocessing_eng.csv"))

def normalize(series):
    mn, mx = series.min(), series.max()
    return (series - mn) / (mx - mn) if mx != mn else series * 0


def run():

    # ── Sidebar: filtros ───────────────────────────────────────────────────────
    with st.sidebar:
        st.title("🔧 Filtros")

        zona_seleccionada = st.multiselect(
            "Distrito(s)", options=sorted(df["distrito"].unique()),
            help="Selecciona uno o varios distritos."
        )
        if not zona_seleccionada:
            st.info("👈 Selecciona al menos un distrito para comenzar.")

        rango_precio = st.slider("Precio (S/.)",
            int(df["precio_pen"].min()), int(df["precio_pen"].max()),
            (int(df["precio_pen"].min()), int(df["precio_pen"].max())))

        with st.expander("Filtros avanzados"):
            num_dorm = st.slider("Dormitorios",
                int(df["num_dorm"].min()), int(df["num_dorm"].max()),
                (int(df["num_dorm"].min()), int(df["num_dorm"].max())))
            num_banios = st.slider("Baños",
                int(df["num_banios"].min()), int(df["num_banios"].max()),
                (int(df["num_banios"].min()), int(df["num_banios"].max())))
            area_range = st.slider("Área (m²)",
                int(df["area_m2"].min()), int(df["area_m2"].max()),
                (int(df["area_m2"].min()), int(df["area_m2"].max())))
            antiguedad_range = st.slider("Antigüedad (años)",
                int(df["antiguedad"].min()), int(df["antiguedad"].max()),
                (int(df["antiguedad"].min()), int(df["antiguedad"].max())))

    # ── Pantalla de bienvenida ─────────────────────────────────────────────────
    if not zona_seleccionada:
        st.markdown("""
        <div style="text-align:center; padding:60px 20px;">
            <h1>🏡 Bienvenido a <b>Ubika</b></h1>
            <p style="font-size:17px; line-height:1.8; max-width:600px; margin:auto;">
                Plataforma inteligente de recomendación y autoevaluación de viviendas de alquiler.<br><br>
                Ajusta tus prioridades según <b>precio, espacio, antigüedad, transporte, servicios y seguridad</b>
                para encontrar las mejores oportunidades.<br><br>
                👉 Selecciona un <b>distrito</b> en la barra lateral para comenzar.
            </p>
        </div>
        """, unsafe_allow_html=True)
        st.stop()

    # ── Filtro de datos ────────────────────────────────────────────────────────
    df_filtered = df[
        df["distrito"].isin(zona_seleccionada) &
        df["precio_pen"].between(*rango_precio) &
        df["num_dorm"].between(*num_dorm) &
        df["num_banios"].between(*num_banios) &
        df["area_m2"].between(*area_range) &
        df["antiguedad"].between(*antiguedad_range)
    ]

    st.title("🏠 Dashboard de Oportunidades")

    tipo_vivienda = st.radio(
        "Tipo de vivienda:",
        options=sorted(df["tipo_vivienda"].unique()),
        horizontal=True, key="tipo_vivienda_select"
    )

    INFO = {
        "Premium": "✨ Viviendas de alto nivel: grandes, modernas y en zonas seguras.",
        "Medio":   "⚖️ Viviendas de clase media con espacio razonable y zonas intermedias.",
        "Económico": "💡 Viviendas accesibles — ideales como opción starter.",
    }
    st.info(INFO.get(tipo_vivienda, ""))

    df_cat = df_filtered[df_filtered["tipo_vivienda"] == tipo_vivienda].copy()

    if df_cat.empty:
        st.warning("No hay propiedades con los filtros actuales.")
        st.stop()

    # ── Scores ────────────────────────────────────────────────────────────────
    df_cat["espacio"]          = normalize(df_cat[["area_m2","num_dorm","num_banios","num_estac"]].sum(axis=1))
    df_cat["precio"]           = 1 - normalize(df_cat[["precio_pen","mantenimiento_soles"]].sum(axis=1))
    df_cat["antiguedad_score"] = 1 - normalize(df_cat["antiguedad"])
    df_cat["crimen"]           = 1 - normalize(df_cat["num_delitos_aprox"])
    df_cat["servicios_basicos"]= normalize(df_cat[["num_colegios_aprox","num_hospitales_aprox","num_comisarias_aprox"]].sum(axis=1))
    df_cat["transporte"]       = normalize(df_cat[["num_metro_est_aprox","num_tren_est_aprox"]].sum(axis=1))

    # ── Perfil promedio ────────────────────────────────────────────────────────
    st.divider()
    st.subheader("📊 Perfil promedio del segmento")
    med = df_cat[["precio_pen","precio_por_m2","area_m2","num_dorm",
                  "num_banios","num_estac","num_delitos_aprox"]].mean()

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Precio promedio",  f"S/ {med['precio_pen']:,.0f}")
    c2.metric("Precio/m²",        f"S/ {med['precio_por_m2']:,.0f}")
    c3.metric("Área media",       f"{med['area_m2']:.0f} m²")
    c4.metric("Dormitorios",      f"{med['num_dorm']:.0f}")
    c5.metric("Criminalidad",     f"{med['num_delitos_aprox']:.1f}")

    # ── Pesos / prioridades ────────────────────────────────────────────────────
    st.divider()
    st.subheader("⚖️ Ajusta tus prioridades")

    CRITERIOS = [
        ("💰 Precio",       "precio"),
        ("🏠 Espacio",      "espacio"),
        ("📅 Antigüedad",   "antiguedad_score"),
        ("🔒 Seguridad",    "crimen"),
        ("🏫 Servicios",    "servicios_basicos"),
        ("🚇 Transporte",   "transporte"),
    ]

    cols = st.columns(len(CRITERIOS))
    pesos_raw = {}
    for col, (label, key) in zip(cols, CRITERIOS):
        pesos_raw[key] = col.slider(label, 0.0, 1.0, 0.2, key=f"peso_{key}")

    total = sum(pesos_raw.values()) or 1
    pesos = {k: v / total for k, v in pesos_raw.items()}

    df_cat["opportunity_score"] = sum(pesos[k] * df_cat[k] for k in pesos)

    med_score = df_cat[["total_servicios_prox","num_delitos_aprox","total_ambientes","precio_pen"]].mean()
    df_cat["superior_promedio"] = np.where(
        (df_cat["total_servicios_prox"] > med_score["total_servicios_prox"]) &
        (df_cat["num_delitos_aprox"]    < med_score["num_delitos_aprox"]) &
        (df_cat["total_ambientes"]      > med_score["total_ambientes"]) &
        (df_cat["precio_pen"]           < med_score["precio_pen"]),
        "⭐ Sí", "No"
    )

    # ── Tabla de oportunidades ─────────────────────────────────────────────────
    st.divider()
    st.subheader("🏆 Top oportunidades")

    solo_oport = st.toggle("Mostrar solo propiedades destacadas", value=False)
    df_oport = df_cat[df_cat["superior_promedio"] == "⭐ Sí"] if solo_oport else df_cat
    df_oport = df_oport.sort_values("opportunity_score", ascending=False)

    df_display = df_oport[[
        "URL","opportunity_score","superior_promedio",
        "direccion_completa","distrito","precio_pen",
        "area_m2","num_dorm","num_banios","latitud","longitud"
    ]].copy()
    df_display.insert(0, "Seleccionar", False)
    df_display["opportunity_score"] = df_display["opportunity_score"].round(3)

    selected_data = st.data_editor(
        df_display, hide_index=True, use_container_width=True,
        key="property_selector",
        column_config={
            "Seleccionar":        st.column_config.CheckboxColumn("✔", help="Seleccionar para comparar"),
            "URL":                st.column_config.LinkColumn("Enlace", display_text="Ver →"),
            "opportunity_score":  st.column_config.ProgressColumn("Score", min_value=0, max_value=1),
            "superior_promedio":  st.column_config.TextColumn("Destaca"),
            "precio_pen":         st.column_config.NumberColumn("Precio (S/.)", format="S/ %d"),
            "area_m2":            st.column_config.NumberColumn("Área m²"),
            "num_dorm":           st.column_config.NumberColumn("Dorm."),
            "num_banios":         st.column_config.NumberColumn("Baños"),
        }
    )

    selected_rows = selected_data[selected_data["Seleccionar"]]
    df_map  = selected_rows if not selected_rows.empty else df_oport
    st.session_state["data"] = selected_rows if not selected_rows.empty else None

    # ── Mapa ──────────────────────────────────────────────────────────────────
    st.divider()
    st.subheader("🗺️ Mapa de propiedades")

    st.pydeck_chart(pdk.Deck(
        layers=[
            pdk.Layer("HeatmapLayer", data=df_map,
                      get_position="[longitud, latitud]", get_weight="opportunity_score"),
            pdk.Layer("ScatterplotLayer", data=df_map,
                      get_position="[longitud, latitud]",
                      get_radius=80, radius_min_pixels=5, radius_max_pixels=20,
                      get_fill_color="[255, 140, 0, 180]", pickable=True),
        ],
        initial_view_state=pdk.ViewState(latitude=-12.0464, longitude=-77.0428, zoom=11, pitch=40),
        tooltip={"text": "{direccion_completa}\nS/ {precio_pen}"}
    ))

    # ── Comparador ────────────────────────────────────────────────────────────
    st.divider()
    st.subheader("🔍 Comparador de propiedades")

    selected_idx = selected_data[selected_data["Seleccionar"]].index

    if selected_idx.empty:
        st.info("Marca propiedades en la tabla para compararlas aquí.")
        return

    if len(selected_idx) > 3:
        st.warning("Solo se comparan las primeras 3 seleccionadas.")
        selected_idx = selected_idx[:3]

    props = df_oport.loc[selected_idx]
    SCORES = ["espacio","precio","antiguedad_score","crimen","servicios_basicos","transporte"]
    LABELS = ["Espacio","Precio","Antigüedad","Seguridad","Servicios","Transporte"]
    COLORS = [
        ("rgba(76,155,232,1)",  "rgba(76,155,232,0.15)"),
        ("rgba(244,162,97,1)",  "rgba(244,162,97,0.15)"),
        ("rgba(42,157,143,1)",  "rgba(42,157,143,0.15)"),
    ]

    # Radar + métricas lado a lado
    col_radar, col_metrics = st.columns([1, 1])

    with col_radar:
        fig = go.Figure()
        fig.add_trace(go.Scatterpolar(
            r=[df_oport[s].mean() for s in SCORES], theta=LABELS,
            fill="toself", name="Promedio",
            line=dict(color="rgba(200,200,200,0.8)", dash="dash"),
            fillcolor="rgba(200,200,200,0.1)"
        ))
        for i, (_, row) in enumerate(props.iterrows()):
            line_color, fill_color = COLORS[i % len(COLORS)]
            fig.add_trace(go.Scatterpolar(
                r=[row[s] for s in SCORES], theta=LABELS,
                fill="toself", name=row["direccion_completa"][:28] + "…",
                line=dict(color=line_color),
                fillcolor=fill_color
            ))
        fig.update_layout(
            polar=dict(radialaxis=dict(visible=True, range=[0,1])),
            showlegend=True, margin=dict(t=40, b=20),
            title="Perfil por dimensión"
        )
        st.plotly_chart(fig, use_container_width=True)

    with col_metrics:
        for _, row in props.iterrows():
            with st.container(border=True):
                st.markdown(f"**📍 {row['direccion_completa'][:45]}**")
                m1, m2, m3 = st.columns(3)
                m1.metric("Precio", f"S/ {row['precio_pen']:,.0f}",
                          f"{row['precio_pen'] - df_oport['precio_pen'].mean():,.0f} vs prom.",
                          delta_color="inverse")
                m2.metric("Área", f"{row['area_m2']:.0f} m²",
                          f"{row['area_m2'] - df_oport['area_m2'].mean():,.0f} vs prom.")
                m3.metric("Score", f"{row['opportunity_score']:.2f}",
                          f"{row['opportunity_score'] - df_oport['opportunity_score'].mean():.2f} vs prom.")

    # Barras comparativas
    df_comp = props[["direccion_completa"] + SCORES].copy()
    df_comp["direccion_completa"] = df_comp["direccion_completa"].str[:25] + "…"
    df_comp.columns = ["Dirección"] + LABELS
    fig_bar = px.bar(
        df_comp.melt(id_vars="Dirección", var_name="Dimensión", value_name="Score"),
        x="Dimensión", y="Score", color="Dirección",
        barmode="group", title="Comparación por dimensión",
        height=350
    )
    fig_bar.update_layout(legend=dict(orientation="h", y=-0.3), margin=dict(t=40, b=80))
    st.plotly_chart(fig_bar, use_container_width=True)

    # ── Créditos ───────────────────────────────────────────────────────────────
    with st.expander("Acerca de"):
        st.markdown("""
        - **Desarrollado por:** [Tato Warthon](https://github.com/warthon-190399) y [Jimmy Warthon](https://github.com/jimmty) — *Pulse Analytica Hub*
        - **Proyecto:** Plataforma **Ubika** para valuación de viviendas y estimación de precios de alquiler
        - **Metodología:** Web scraping + fuentes oficiales del Gobierno del Perú
        """)
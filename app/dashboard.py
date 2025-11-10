import streamlit as st
import os
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from sklearn.preprocessing import MinMaxScaler
import altair as alt
import pydeck as pdk


def run():
    
    def normalize(series):
        return (series - series.min()) / (series.max() - series.min())

    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    BASE_DIR = os.path.abspath(os.path.join(BASE_DIR, ".."))
    input_model_path = os.path.join(BASE_DIR, "data", "processed","data_preprocessing_eng.csv")

    df = pd.read_csv(input_model_path)
    with st.sidebar:

        st.title("Panel de Control")
        st.markdown("""
        Bienvenido al panel de control de análisis de datos. Aquí puedes explorar y visualizar tus datos de manera interactiva.
        """)
        st.markdown("### Configuraciones")
        
        zona_seleccionada = st.multiselect("Distrito(s) de Interés", options = df["distrito"].unique(),
                                           help="Selecciona uno o varios distritos para analizar las propiedades disponibles."
                                           )

        if not zona_seleccionada:
            st.markdown("⚠️ Por favor selecciona al menos un distrito para ver resultados.")
            

        rango_precio = st.slider("Rango de Precio (PEN)",
                                 min_value=int(df["precio_pen"].min()),
                                 max_value=int(df["precio_pen"].max()),
                                 value=(int(df["precio_pen"].min()), int(df["precio_pen"].max()))
                                 )
        
        with st.expander("Filtros Avanzados"):
            num_dorm = st.slider("N° dormitorios",
                                min_value=int(df["num_dorm"].min()),
                                max_value=int(df["num_dorm"].max()),
                                value=(int(df['num_dorm'].min()), int(df['num_dorm'].max()))
                                )
            num_banios = st.slider("N° baños",
                                min_value=int(df["num_banios"].min()),
                                max_value=int(df["num_banios"].max()),
                                value=(int(df['num_banios'].min()),
                                        int(df['num_banios'].max()))
                                )
            area_range = st.slider("Área (m²)",
                                min_value=int(df["area_m2"].min()),
                                max_value=int(df["area_m2"].max()),
                                value=(int(df['area_m2'].min()), 
                                        int(df['area_m2'].max()))
                                )
            antiguedad_range  = st.slider("Antigüedad (años)",
                                min_value=int(df["antiguedad"].min()),
                                max_value=int(df["antiguedad"].max()),
                                value=(int(df['antiguedad'].min()),
                                        int(df['antiguedad'].max()))
                                )
    if not zona_seleccionada:
        st.markdown(
            """
            <div style="text-align: center; padding: 50px 20px;">
                <h1>🏡 ¡Hola! Bienvenido a <b>Ubika</b></h1>
                <p style="font-size: 18px; line-height: 1.6;">
                    <b>Ubika</b> es una plataforma inteligente de recomendación y <b>autoevaluación de viviendas de alquiler</b>. <br><br>
                    Aquí podrás ajustar tus prioridades según:
                    <ul style="text-align: left; display: inline-block;">
                        <li>💰 Precio</li>
                        <li>📏 Espacio</li>
                        <li>🏗️ Antigüedad</li>
                        <li>🚇 Transporte</li>
                        <li>🛒 Servicios básicos</li>
                        <li>🚨 Niveles de criminalidad</li>
                    </ul>
                    Nuestra IA te recomendará las mejores opciones y te permitirá compararlas fácilmente. <br><br>
                    👉 Para comenzar, selecciona los <b>distritos de interés</b> en la barra lateral.
                </p>
            </div>
            """,
            unsafe_allow_html=True
        )
        st.stop()

    df_filtered = df[
    (df['distrito'].isin(zona_seleccionada)) &
    (df['precio_pen'].between(rango_precio[0], rango_precio[1])) &
    (df['num_dorm'].between(num_dorm[0], num_dorm[1])) &
    (df['num_banios'].between(num_banios[0], num_banios[1])) &
    (df['area_m2'].between(area_range[0], area_range[1])) &
    (df['antiguedad'].between(antiguedad_range[0], antiguedad_range[1]))
                    ]
    st.title("🏠 Análisis de Propiedades")
    st.markdown("""
    Explora las propiedades disponibles en diferentes zonas. Utiliza los filtros en la barra lateral para ajustar los criterios de búsqueda.
    """)

    tipo_vivienda = st.radio("Seleccione el tipo de vivienda para análisis detallado:",
                                options=sorted(df["tipo_vivienda"].unique()),
                                index=0,
                                key="tipo_vivienda_select")
    
    
    st.divider()
    st.markdown(f"### 🔍 Oportunidades en propiedades del tipo {tipo_vivienda}")
                

    if tipo_vivienda == "Premium":
            st.info("✨ Estas son viviendas de alto nivel: grandes, modernas y en zonas seguras. Aquí destacan oportunidades con mejor relación calidad-precio que el promedio premium.")
    elif tipo_vivienda == "Medio":
            st.info("⚖️ Viviendas de clase media, con espacio razonable y ubicadas en zonas intermedias. Aquí destacan las propiedades con más servicios y menos criminalidad.")
    elif tipo_vivienda == "Económico":
            st.info("💡 Viviendas starter o accesibles, más pequeñas y de menor costo. Aquí resaltan oportunidades con más servicios y mejor seguridad que el promedio de este segmento.")


    df_cat = df_filtered[df_filtered["tipo_vivienda"] == tipo_vivienda]

    
    df_median_cluster = df_cat[["precio_pen", "precio_por_m2", "area_m2", "num_dorm", "num_banios",
                            "num_estac", "total_ambientes", "total_servicios_prox",
                            "num_delitos_aprox"
                                ]].mean()
    
    st.markdown("**Perfil promedio:**")
    st.write(f"""
    - Precio: S/ {df_median_cluster['precio_pen']:.2f}  
    - Precio por m²: S/ {df_median_cluster['precio_por_m2']:.2f}
    - Área media: {df_median_cluster['area_m2']:.1f} m²  
    - Dormitorios: {df_median_cluster['num_dorm']:.0f}  
    - Baños: {df_median_cluster['num_banios']:.0f}  
    - Estacionamientos: {df_median_cluster['num_estac']:.0f}  
    - Nivel de criminalidad: {df_median_cluster['num_delitos_aprox']:.2f}<br>
    Rango: {df_cat["num_delitos_aprox"].quantile(0.01):.1f} (mín) - {df_cat["num_delitos_aprox"].quantile(0.99):.1f} (máx))
    """, unsafe_allow_html=True)
    
    df_cat["superior_promedio"] = np.where(
            (df_cat['total_servicios_prox'] > df_median_cluster['total_servicios_prox']) &
            (df_cat['num_delitos_aprox'] < df_median_cluster['num_delitos_aprox']) &
            (df_cat['total_ambientes'] > df_median_cluster['total_ambientes']) &
            (df_cat['precio_pen'] < df_median_cluster['precio_pen']),
            "Sí", "No"
    )

    st.divider()

    st.subheader("⚖️ Ajusta tus prioridades")

    col1, col2 = st.columns(2)

    pesos = []
    
    with col1:
        criterios_col1 = ["💰 Precio (alquiler, mantenimiento)","🏠 Espacio (m², ambientes, dormitorios...)","📅 Antigüedad (menos es mejor)"]
        etiquetas_min_col1 = ["Costo reducido", "Espacio reducido", "Construcción reciente"]
        etiquetas_max_col1 = ["Costo elevado", "Espacio amplio", "Mayor antigüedad"]

        for i,criterio_col1 in enumerate(criterios_col1):
            col3, col4, col5 = st.columns([1,3,1])
            with col3:
                st.markdown(f"<p style='text-align:center;'>0.0<br>{etiquetas_min_col1[i]}</p>", unsafe_allow_html=True)
            with col4:
                peso_col1 = st.slider(criterio_col1, 0.0, 1.0, 0.2)
                pesos.append(peso_col1)
            with col5:
                st.markdown(f"<p style='text-align:center;'>1.0<br>{etiquetas_max_col1[i]}</p>", unsafe_allow_html=True)
            st.empty()
        #peso_precio
        #peso_espacio = st.slider("🏠 Espacio (m², ambientes, dormitorios...)", 0.0, 1.0, 0.2)
        #peso_antiguedad = st.slider("📅 Antigüedad (menos es mejor)", 0.0, 1.0, 0.2)

    with col2:
        # peso_crimen = st.slider("🔒 Seguridad (menos delitos mejor)", 0.0, 1.0, 0.2)
        # peso_servicios = st.slider("🏫 Servicios básicos (colegios, hospitales, comisarías)", 0.0, 1.0, 0.1)
        # peso_transporte = st.slider("🚇 Transporte (metro, tren, metropolitano)", 0.0, 1.0, 0.1)
        criterios_col2 = ["🔒 Seguridad (menos delitos mejor)","🏫 Servicios básicos (colegios, hospitales, comisarías)","🚇 Transporte (metro, tren, metropolitano)"]
        etiquetas_min_col2 = ["Zona segura", "Servicios escasos", "Transporte escaso"]
        etiquetas_max_col2 = ["Zona riesgosa", "Servicios abundantes", "Transporte abundante"]

        for j,criterio_col2 in enumerate(criterios_col2):
            col3, col4, col5 = st.columns([1,3,1])
            with col3:
                st.markdown(f"<p style='text-align:center;'>0.0<br>{etiquetas_min_col2[j]}</p>", unsafe_allow_html=True)
            with col4:
                peso_col2 = st.slider(criterio_col2, 0.0, 1.0, 0.2)
                pesos.append(peso_col2)
            with col5:
                st.markdown(f"<p style='text-align:center;'>1.0<br>{etiquetas_max_col2[j]}</p>", unsafe_allow_html=True)

    peso_espacio = pesos[0]
    peso_precio = pesos[1]
    peso_antiguedad = pesos[2]
    peso_crimen = pesos[3]
    peso_servicios = pesos[4]
    peso_transporte = pesos[5]
    
    pesos_df = pd.DataFrame({
            "dimension": ["Espacio", "Precio", "Antiguedad", "Seguridad", "Servicios", "Transporte"],
            "peso": [peso_espacio, peso_precio, peso_antiguedad, peso_crimen, peso_servicios, peso_transporte]
    })

    with st.expander("⚖️ Tus prioridades actuales"):
            fig_pesos = px.bar(
                    pesos_df,
                    x="dimension",
                    y="peso",
                    text="peso",
                    color="dimension",
                    height=350,
                    title="Distribución de pesos en el Opportunity Score"
            )

            st.plotly_chart(fig_pesos, use_container_width=True)


    total_peso = (peso_espacio + peso_precio + peso_antiguedad + 
            peso_crimen + peso_servicios + peso_transporte)

    peso_espacio /= total_peso
    peso_precio /= total_peso
    peso_antiguedad /= total_peso
    peso_crimen /= total_peso
    peso_servicios /= total_peso
    peso_transporte /= total_peso
    
    df_cat["espacio"] = normalize(df_cat[["area_m2", "num_dorm", "num_banios", "num_estac"]].sum(axis=1))
    df_cat["precio"] = 1 - normalize(df_cat[["precio_pen", "mantenimiento_soles"]].sum(axis=1))  # invertimos porque menos es mejor
    df_cat["antiguedad_score"] = 1 - normalize(df_cat["antiguedad"])
    df_cat["crimen"] = 1 - normalize(df_cat["num_delitos_aprox"])  # menos delitos = mejor
    df_cat["servicios_basicos"] = normalize(df_cat[["num_colegios_aprox", "num_hospitales_aprox", "num_comisarias_aprox"]].sum(axis=1))
    df_cat["transporte"] = normalize(df_cat[["num_metro_est_aprox", "num_tren_est_aprox"]].sum(axis=1))
    
    df_cat["opportunity_score"] = (peso_espacio * df_cat["espacio"] +
                                    peso_precio * df_cat["precio"] +
                                    peso_antiguedad * df_cat["antiguedad_score"] +
                                    peso_crimen * df_cat["crimen"] +
                                    peso_servicios * df_cat["servicios_basicos"] +
                                    peso_transporte * df_cat["transporte"]
                                    )
    
    
    df_oportunidades = df_cat.sort_values("opportunity_score", ascending=False)

    df_oportunidades["URL"] = df_oportunidades["URL"].apply(lambda x: f"[Ver aquí]({x})")

    st.subheader("🏆 Top oportunidades según tus prioridades")

    filtrar_oportunidades = st.radio(
        "¿Deseas mostrar solo las propiedades destacadas como oportunidades?",
        options=["Todas", "Solo oportunidades"],
        index=0
    )

    if filtrar_oportunidades == "Solo oportunidades":
        df_oportunidades = df_cat[df_cat["superior_promedio"] == "Sí"].sort_values("opportunity_score", ascending=False)
    else:
        df_oportunidades = df_cat.sort_values("opportunity_score", ascending=False)


    df_display = df_oportunidades[["URL", "opportunity_score", "superior_promedio", 
                    "direccion_completa", "distrito", "precio_pen", 
                    "area_m2", "num_dorm", "num_banios", "latitud", "longitud"
                                ]].copy()

    # Insertar la columna "Seleccionar"
    df_display.insert(0, "Seleccionar", False)

    # Mostrar editor con checkbox en "Seleccionar"
    selected_data = st.data_editor(
        df_display,
        hide_index=True,
        use_container_width=True,
        key="property_selector",
        column_config={
            "Seleccionar": st.column_config.CheckboxColumn(
                "Seleccionar",
                help="Marca para incluir en la comparación",
                default=False,
            ),
            "URL": st.column_config.LinkColumn("Enlace", display_text="Abrir")
        }
    )

    selected_rows = selected_data[selected_data["Seleccionar"]]

    if selected_rows.empty:
        df_map = df_oportunidades
        df_map2 = None
    else:
        df_map = selected_rows
        df_map2 = selected_rows

    st.session_state["data"] = df_map2
    #------------------------------
    #if st.button("Cargar DataFrame"):
    #    st.session_state["data"] = df_map
    #    st.success("Data guardada en session_state")
    #------------------------------

    layer_points = pdk.Layer(
        "ScatterplotLayer",
        data=df_map,
        get_position='[longitud, latitud]',
        get_radius="precio",  # tamaño de burbuja en función del precio
        radius_scale=10,      # escala para ajustar visualización
        radius_min_pixels=5,  # tamaño mínimo en píxeles
        radius_max_pixels=100,# tamaño máximo en píxeles
        get_fill_color="[255, 140, 0, 160]",  # color naranja con transparencia
        pickable=True,
    )

    layer_heat = pdk.Layer(
        "HeatmapLayer",
        data=df_map,
        get_position='[longitud, latitud]',
        get_weight="opportunity_score"
    )

    view_state = pdk.ViewState(latitude=-12.0464, longitude=-77.0428, zoom=11, pitch=45)

    st.pydeck_chart(pdk.Deck(layers=[layer_heat, layer_points], initial_view_state=view_state))

    st.divider()
    st.subheader("🔍 Comparador de Propiedades")

    selected_indices = selected_data[selected_data["Seleccionar"]].index

    if not selected_indices.empty:

        if len(selected_indices) > 3:
            st.warning("⚠️ Solo puedes comparar hasta 3 propiedades. Mostrando las 3 primeras seleccionadas.")
            selected_indices = selected_indices[:3]
        # 🔥 usar loc en lugar de iloc
        propiedades_seleccionadas = df_oportunidades.loc[selected_indices]
                
        st.write(f"**Propiedades seleccionadas:** {len(propiedades_seleccionadas)}")
        
        categorias = ["espacio", "precio", "antiguedad_score", "crimen", "servicios_basicos", "transporte"]
        
        # Radar Chart: Promedio vs Propiedades Seleccionadas
        fig_radar = go.Figure()
        
        # Agregar el promedio
        fig_radar.add_trace(go.Scatterpolar(
            r=[df_oportunidades[c].mean() for c in categorias],
            theta=categorias,
            fill='toself',
            name="Promedio General",
            line=dict(color='rgba(255,0,0,0.8)', width=3),
            fillcolor='rgba(255,0,0,0.1)'
        ))
        
        # Agregar cada propiedad seleccionada
        color_map = {
            "blue": "rgba(0,0,255,0.5)",
            "green": "rgba(0,128,0,0.5)",
            "purple": "rgba(128,0,128,0.5)",
            "orange": "rgba(255,165,0,0.5)",
            "brown": "rgba(165,42,42,0.5)",
            "pink": "rgba(255,192,203,0.5)",
            "gray": "rgba(128,128,128,0.5)",
            "olive": "rgba(128,128,0,0.5)"
        }
        
        colors = list(color_map.keys())
        for i, (idx, row) in enumerate(propiedades_seleccionadas.iterrows()):
            color = colors[i % len(colors)]
            fig_radar.add_trace(go.Scatterpolar(
                r=[row[c] for c in categorias],
                theta=categorias,
                fill='toself',
                name=f"{row['direccion_completa'][:30]}...",
                line=dict(color=color),
                fillcolor=color_map[color]
            ))
        
        fig_radar.update_layout(
            polar=dict(radialaxis=dict(visible=True, range=[0, 1])), 
            showlegend=True,
            title="Comparación de Propiedades Seleccionadas vs Promedio"
        )
        st.plotly_chart(fig_radar, use_container_width=True)
        
        

        df_comp = propiedades_seleccionadas[["direccion_completa", "precio", "espacio", "antiguedad_score","crimen", "servicios_basicos", "transporte"]].copy()
        
        st.write(df_comp)
        df_comp["direccion_short"] = df_comp["direccion_completa"].str[:25] + "..."

        fig_bar = px.bar(
            df_comp.melt(id_vars="direccion_short", value_vars=["precio", "espacio", "antiguedad_score", "crimen", "servicios_basicos", "transporte"]),
            x="direccion_short",
            y="value",
            color="variable",
            barmode="group",
            orientation="v",
            title="Comparación de propiedades seleccionadas"
        )
        st.plotly_chart(fig_bar, use_container_width=True)

        for i, (_, row) in enumerate(propiedades_seleccionadas.iterrows(), 1):
            st.markdown(f"### 📍 {row['direccion_completa']}")
            col1, col2, col3 = st.columns(3)
            col1.metric(
                "💰 Precio (PEN)",
                f"{row['precio_pen']:,.0f}",
                delta=f"{row['precio_pen'] - df_oportunidades['precio_pen'].mean():,.0f} vs promedio",
                delta_color="inverse"
            )
            col2.metric(
                "📏 Área (m²)",
                f"{row['area_m2']:,.1f}",
                delta=f"{row['area_m2'] - df_oportunidades['area_m2'].mean():,.1f} vs promedio"
            )
            if "num_delitos_aprox" in row:
                col3.metric(
                    "🔒 Seguridad (delitos)",
                    f"{row['num_delitos_aprox']:.1f}",
                    delta=f"{row['num_delitos_aprox'] - df_oportunidades['num_delitos_aprox'].mean():.1f} vs promedio",
                    delta_color="inverse"
                )
        else:
            st.warning("ℹ️ Selecciona propiedades en la tabla de arriba para compararlas aquí.")
    with st.expander("Acerca de:", expanded=False):
            st.write('''
            - :orange[**Desarrollado por:**] [Tato Warthon](https://github.com/warthon-190399) y [Jimmy Warthon](https://github.com/jimmty) — *Pulse Analytica Hub*.
            - :orange[**Proyecto:**] Plataforma interactiva **Ubika** para la **valuación de viviendas y estimación de precios de alquiler** con datos georeferenciados.
            - :orange[**Metodología:**] Integración de datos mediante **web scraping** y fuentes oficiales del Gobierno del Perú.
            - :orange[**Fuentes de datos:**] Información referenciada sobre **comisarías, hospitales, índices de criminalidad**, entre otros factores geográficos y socioeconómicos.
            ''')
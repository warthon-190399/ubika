import streamlit as st
import os
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from sklearn.preprocessing import MinMaxScaler
import altair as alt


def run():

    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    BASE_DIR = os.path.abspath(os.path.join(BASE_DIR, ".."))
    input_model_path = os.path.join(BASE_DIR, "data", "processed","data_preprocessing_eng.csv")

    df = pd.read_csv(input_model_path)
    with st.sidebar:
        st.header("Filtros y Configuración")

        zona_seleccionada = st.multiselect("Zona(s)", options = df["zona_apeim"].unique())

        nse_seleccionado = st.multiselect("NSE", options = df["nivel_socioeconomico"].unique())

        rango_precio =  st.slider("Rango de precios (PEN)",
                                  min_value=int(df["precio_pen"].min()),
                                  max_value=int(df["precio_pen"].max()),
                                  value=(int(df['precio_pen'].min()), int(df['precio_pen'].max()))
                                  )
        
        with st.expander("Filtros avanzados"):
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
            
            st.markdown("---")
            st.subheader("Configuración de gráficos")
            color_scheme = st.selectbox("Esquema de colores", 
                                    ["viridis", "plasma", "inferno", "magma", "cividis"])
        
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📊 Resumen General", 
        "🏠 Análisis de Propiedades", 
        "🗺️ Mapa Interactivo", 
        "📈 Tendencias", 
        "🧠 Insights"
    ])

    df_filtered = df[
    (df['zona_apeim'].isin(zona_seleccionada)) &
    (df['precio_pen'].between(rango_precio[0], rango_precio[1])) &
    (df['nivel_socioeconomico'].isin(nse_seleccionado)) &
    (df['num_dorm'].between(num_dorm[0], num_dorm[1])) &
    (df['num_banios'].between(num_banios[0], num_banios[1])) &
    (df['area_m2'].between(area_range[0], area_range[1])) &
    (df['antiguedad'].between(antiguedad_range[0], antiguedad_range[1]))
]

    with tab1:
        st.header("📈 Resumen General del Mercado")
        col1, col2 = st.columns(2)
    
        with col1:
            # Distribución de precios
            fig_hist = px.histogram(df_filtered, x='precio_pen', nbins=30, 
                                title="Distribución de Precios",
                                labels={'precio_pen': 'Precio (PEN)', 'count': 'Cantidad'},
                                color_discrete_sequence=['#667eea'])
            fig_hist.update_layout(showlegend=False)
            st.plotly_chart(fig_hist, use_container_width=True)
            
            # Top distritos por precio promedio
            distrito_precio = df_filtered.groupby('distrito')['precio_pen'].mean().sort_values(ascending=False).head(8)
            fig_bar = px.bar(x=distrito_precio.index, y=distrito_precio.values,
                            title="Precio Promedio por Distrito",
                            labels={'x': 'Distrito', 'y': 'Precio Promedio (PEN)'},
                            color=distrito_precio.values,
                            color_continuous_scale=color_scheme)
            st.plotly_chart(fig_bar, use_container_width=True)
        
        with col2:
            # Relación precio vs área
            fig_scatter = px.scatter(df_filtered, x='area_m2', y='precio_pen', 
                                color='nivel_socioeconomico', size='num_banios',
                                title="Precio vs Área (por dormitorios)",
                                labels={'area_m2': 'Área (m²)', 'precio_pen': 'Precio (PEN)'},
                                hover_data=['distrito', 'nivel_socioeconomico'])
            st.plotly_chart(fig_scatter, use_container_width=True)
            
            # Distribución por nivel socioeconómico
            nivel_counts = df_filtered['nivel_socioeconomico'].value_counts()
            fig_pie = px.pie(values=nivel_counts.values, names=nivel_counts.index,
                            title="Distribución por Nivel Socioeconómico",
                            color_discrete_sequence=px.colors.qualitative.Set3)
            st.plotly_chart(fig_pie, use_container_width=True)

    with tab2:

        tipo_vivienda = st.radio("Seleccione el tipo de vivienda para análisis detallado:", options=df["tipo_vivienda"].unique(), index=0, key="tipo_vivienda_select")
        
        cat1 = df_filtered[df_filtered['tipo_vivienda'] == tipo_vivienda]

        st.write(cat1)
        
        st.subheader("📊 Análisis del Cluster 1: Perfil y Oportunidades")
        st.markdown("Este apartado analiza el **tipo de vivienda del cluster 1** identificado en el modelo KMeans, "
                    "mostrando su perfil promedio, distribución de atributos y detectando propiedades con alto potencial "
                    "de inversión basadas en precio, servicios y seguridad.")
        cat1['precio_por_m2'] = cat1['precio_pen'] / cat1['area_m2']
        media_cluster1 = cat1[['precio_pen','precio_por_m2','area_m2','num_dorm','num_banios',
                            'num_estac', "total_ambientes", 'total_servicios_prox','total_transporte_aprox',
                            'categoria_crimenes_cod']].mean()
        
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Precio Promedio (PEN)", f"{media_cluster1['precio_pen']:,.0f}")
        col2.metric("Precio Promedio m²", f"{media_cluster1['precio_por_m2']:,.0f}")
        col3.metric("Servicios Cercanos", f"{media_cluster1['total_servicios_prox']:.1f}")
        col4.metric("Criminalidad Promedio", f"{media_cluster1['categoria_crimenes_cod']:.2f}")

        st.markdown("**Perfil promedio:**")
        st.write(f"""
        - Área media: {media_cluster1['area_m2']:.1f} m²  
        - Dormitorios: {media_cluster1['num_dorm']:.1f}  
        - Baños: {media_cluster1['num_banios']:.1f}  
        - Estacionamientos: {media_cluster1['num_estac']:.2f}  
        - Transporte cercano: {media_cluster1['total_transporte_aprox']:.2f}  
        - Nivel de criminalidad: {media_cluster1['categoria_crimenes_cod']:.2f} (escala codificada)
        """)


        oportunidades = cat1[
        (cat1['total_servicios_prox'] > media_cluster1['total_servicios_prox']) &
        (cat1['categoria_crimenes_cod'] < media_cluster1['categoria_crimenes_cod']) &
        (cat1['total_ambientes'] > media_cluster1['total_ambientes']) &
        (cat1['precio_por_m2'] < media_cluster1['precio_por_m2']) 
        ].sort_values('precio_por_m2')

        st.markdown("### 🔍 Oportunidades en Cluster 1")
        st.markdown(f"Propiedades con **más servicios que la media**, **menor criminalidad** y **precio por m² más bajo** que el promedio del cluster.")
        st.dataframe(oportunidades[['direccion_completa','distrito','precio_pen','precio_por_m2',
                                    'total_servicios_prox','categoria_crimenes_cod']])
    
        fig_map = px.scatter_mapbox(
        oportunidades,
        lat="latitud",
        lon="longitud",
        size="area_m2",
        color="precio_por_m2",
        hover_name="direccion_completa",
        hover_data={
            "precio_pen":":,.0f",
            "total_servicios_prox":True,
            "categoria_crimenes_cod":True
        },
        color_continuous_scale="viridis",
        mapbox_style="carto-darkmatter",  # CORREGIDO: aquí va el estilo de mapa
        zoom=11,
        height=500
        )
         
        st.plotly_chart(fig_map, use_container_width=True)

        st.write(df_filtered.columns)
        

        step = 40
        overlap = 2

        chart = alt.Chart(df, height=step).transform_joinaggregate(
            mean_precio='mean(precio_pen)', groupby=['zona_apeim']
        ).transform_bin(
            ['bin_max', 'bin_min'], 'precio_pen'
        ).transform_aggregate(
            value='count()', groupby=['zona_apeim', 'mean_precio', 'bin_min', 'bin_max']
        ).transform_impute(
            impute='value', groupby=['zona_apeim', 'mean_precio'], key='bin_min', value=0
        ).mark_area(
            interpolate='monotone',
            fillOpacity=0.8,
            stroke='lightgray',
            strokeWidth=0.5
        ).encode(
            alt.X('bin_min:Q').title('Precio de Vivienda (PEN)'),
            alt.Y('value:Q').axis(None).scale(range=[step, -step * overlap]),
            alt.Fill('mean_precio:Q').legend(None).scale(scheme='viridis')
        ).facet(
            row=alt.Row('zona_apeim:N').title(None).header(labelAngle=0, labelAlign='left')
        ).properties(
            title='Distribución de precios por zona',
            bounds='flush'
        ).configure_facet(
            spacing=0
        ).configure_view(
            stroke=None
        ).configure_title(
            anchor='end'
        )

        st.altair_chart(chart, use_container_width=True)
    
    with st.expander("Acerca de:", expanded=False):
        st.write('''
            - :orange[**Desarrollado por:**] [Tato Warthon](https://github.com/warthon-190399) y [Jimmy Warthon](https://github.com/jimmty) — *Pulse Analytica Hub*.
            - :orange[**Proyecto:**] Plataforma interactiva **Ubika** para la **valuación de viviendas y estimación de precios de alquiler** con datos georeferenciados.
            - :orange[**Metodología:**] Integración de datos mediante **web scraping** y fuentes oficiales del Gobierno del Perú.
            - :orange[**Fuentes de datos:**] Información referenciada sobre **comisarías, hospitales, índices de criminalidad**, entre otros factores geográficos y socioeconómicos.
        ''')

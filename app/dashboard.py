import streamlit as st
import os
import pandas as pd
import plotly.express as px

def run():

    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    BASE_DIR = os.path.abspath(os.path.join(BASE_DIR, ".."))
    input_model_path = os.path.join(BASE_DIR, "data", "processed","data_preprocessing_eng.csv")

    df = pd.read_csv(input_model_path)

    with st.sidebar:
        st.header("Filtros y Configuración")

        zona_seleccionada = st.multiselect("Zona(s)", options = df["zona_apeim"].unique())

        nse_seleccionado = st.multiselect("NSE", options = df["nivel_socioeconomico"].unique())

        #--------------------
        if not zona_seleccionada:
            zona_seleccionada = df["zona_apeim"].unique()

        if not nse_seleccionado:
            nse_seleccionado = df["nivel_socioeconomico"].unique()

        #--------------------

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
            chart_animation = st.checkbox("Animaciones en gráficos", True)
        
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
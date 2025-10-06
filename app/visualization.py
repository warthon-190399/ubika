import streamlit as st
import os
import pandas as pd
import plotly.express as px

def run():

    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    BASE_DIR = os.path.abspath(os.path.join(BASE_DIR, ".."))
    input_model_path = os.path.join(BASE_DIR, "data", "processed","data_preprocessing_eng.csv")

    df = pd.read_csv(input_model_path)
    st.write(df.columns)
    # create sidebar with district selection
    st.sidebar.header("Filtros")
    distritos_disponibles = df["nivel_socioeconomico"].unique()
    distrito_seleccionado = st.sidebar.selectbox("Selecciona un nivel socioeconomico", distritos_disponibles)

    #Filter by district selected
    df_filtrado = df[df["nivel_socioeconomico"] == distrito_seleccionado]

    # Principal title
    st.title(f"Análisis de precios en el distrito: {distrito_seleccionado}")

    st.subheader("Distribución de precios por nivel socioeconómico (Boxplot)")
    fig_box = px.box(
        df_filtrado,
        x="nivel_socioeconomico",
        y="precio_pen",
        color= "distrito",
        labels={
            "precio_pen": "Precio (PEN)",
            "distrito": "Distrito"
        },
        title = "Boxplot de precios"
    )

    # graph 2: Violin Plot
    st.subheader("Distribución de precios por nivel socioeconómico (Violin Plot)")
    fig_violin = px.violin(
        df_filtrado,
        x="nivel_socioeconomico",
        y="precio_pen",
        color = "distrito",
        box=True,
        points="all",
        labels={
            "precio_pen": "Precio (PEN)",
            "distrito": "Distrito"
        },
        title="Violin Plot de precios"
    )
    
    # Graph 3: Histograma
    st.subheader("Histograma de precios")
    fig_hist = px.histogram(
        df_filtrado,
        x="precio_pen",
        color="distrito",
        nbins=30,
        labels={"precio_pen": "Precio (PEN)"},
        title="Histograma de precios por nivel socioeconomico"
    )
    
    
    fig_scatter = px.scatter(
        df,
        x = "area_m2",
        y = "precio_pen",
        color = "nivel_socioeconomico",
        #size = "mantenimiento_soles",
        hover_data = ["mantenimiento_soles","antiguedad","total_ambientes"],
        title = "Relación entre área y precio según distrito",
        labels = {
            "area_m2": "Área (m²)",
            "precio_pen": "Precio (PEN)",
            "nivel_socieconomico_cod": "Nivel socieconomico",
            "mantenimiento_soles": "Mantenimiento (PEN)"
        },
    )

    col1, col2 = st.columns(2)

    st.plotly_chart(fig_box, use_container_width=True)
    with col1:
        
        st.plotly_chart(fig_violin, use_container_width=True)

    with col2:
        st.plotly_chart(fig_hist, use_container_width=True)

    st.plotly_chart(fig_scatter, use_container_width=True)

    # Mapa de burbujas
    st.subheader("Mapa de propiedades por ubicación")
    fig_burbujas = px.scatter_mapbox(
        df,
        lat="latitud",
        lon="longitud",
        size="precio_pen",
        color="nivel_socioeconomico",
        size_max=20,
        center={"lat": -12.053675190475358, "lon": -77.04217016334559},
        zoom=11,
        mapbox_style="carto-darkmatter",
        width=70,
        hover_data=["precio_pen", "area_m2", "distrito"],
        title="Distribución de precios por zona",
        height=800,
    )
    st.plotly_chart(fig_burbujas)

    # Mapa de calor (Heatmap)
    st.subheader("Mapa de calor según precio")
    fig_heatmap = px.density_mapbox(
        df,
        lat="latitud",
        lon="longitud",
        z="precio_pen",
        radius=30,
        color_continuous_scale="Viridis",
        center={"lat": -12.053675190475358, "lon": -77.04217016334559},
        zoom=11,
        mapbox_style="carto-darkmatter",
        width=70,
        title="Mapa de calor del precio",
        height=800
    )
    st.plotly_chart(fig_heatmap, use_container_width=True)
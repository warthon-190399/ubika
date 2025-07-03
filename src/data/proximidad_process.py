#%% Importar librerias
import pandas as pd
import os
# %% Lectura de dfs
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.abspath(os.path.join(BASE_DIR, "..", ".."))
input_path_adondevivir = os.path.join(BASE_DIR, "data", "processed", "adondevivir_processed_geo.csv")
input_path_malls = os.path.join(BASE_DIR, "data", "processed", "malls_processed_format.csv")
input_path_colegios = os.path.join(BASE_DIR, "data", "processed", "colegios_processed_format.csv")
input_path_hospitales = os.path.join(BASE_DIR, "data", "processed", "hospitales_processed_format.csv")

output_path = os.path.join(BASE_DIR, "data", "processed", "malls_processed_format.csv")

df_adondevivir = pd.read_csv(input_path_adondevivir)
df_malls = pd.read_csv(input_path_malls)
df_colegios = pd.read_csv(input_path_colegios)
df_hospitales = pd.read_csv(input_path_hospitales)
# %% Función de la proximidad
def proximidad_entre(df_departamentos_1, df_colegios_1, nombre_columna, radius_metros = 500):
    import numpy as np
    import pandas as pd
    from sklearn.neighbors import BallTree

    # Asegurarse que no hay NaNs
    df_colegios_1 = df_colegios_1.dropna(subset=['latitud', 'longitud']).reset_index(drop=True)
    df_departamentos_1 = df_departamentos_1.dropna(subset=['latitud', 'longitud']).reset_index(drop=True)

    colegios_rad = np.deg2rad(df_colegios_1[['latitud', 'longitud']].values)
    deptos_rad = np.deg2rad(df_departamentos_1[['latitud', 'longitud']].values)

    # Radio terrestre en metros
    earth_radius = 6371000  
    radius_rad = radius_metros / earth_radius  # Convertir a radianes

    # Crear BallTree con coordenadas de colegios (en radianes)
    tree = BallTree(colegios_rad, metric='haversine')

    # Obtener cantidad de colegios dentro del radio
    counts = tree.query_radius(deptos_rad, r=radius_rad, count_only=True)

    # Obtener los índices de colegios cercanos
    indices_cercanos = tree.query_radius(deptos_rad, r=radius_rad)

    # Asignar como nueva columna
    df_departamentos_1 = df_departamentos_1.copy()
    df_departamentos_1[nombre_columna] = counts

    # Crear lista de registros para el nuevo DataFrame
    #rows = []
    #for i, indices in enumerate(indices_cercanos):
    #    depto_info = df_departamentos_1.iloc[i]
    #    for idx in indices:
    #        colegio_info = df_colegios_1.iloc[idx].to_dict()
    #        colegio_info['departamento_index'] = i
    #        colegio_info['departamento_lat'] = depto_info['latitud']
    #        colegio_info['departamento_lon'] = depto_info['longitud']
    #        rows.append(colegio_info)
    #df_colegios_cercanos = pd.DataFrame(rows)

    #return df_colegios_cercanos
    
    return df_departamentos_1
# %% Se añade columna de colegios proximos
df_colegios_cercanos = proximidad_entre(df_adondevivir, df_colegios, 'num_colegios')
df_colegios_cercanos
# %%
import plotly.graph_objects as go

fig = go.Figure()

# Colegios cercanos
fig.add_trace(go.Scattermapbox(
    lat=df_colegios_cercanos['latitud'],
    lon=df_colegios_cercanos['longitud'],
    mode='markers',
    marker=dict(size=10, color='red'),
    name='Colegios'
))

# Departamentos
fig.add_trace(go.Scattermapbox(
    lat=df_adondevivir2['latitud'],
    lon=df_adondevivir2['longitud'],
    mode='markers',
    marker=dict(size=10, color='blue'),
    name='Casas'
))

fig.update_layout(
    mapbox= dict(
        style = "open-street-map",
        zoom=14,
        center=dict(lat=float(df_adondevivir2['latitud'].mean()), 
                    lon=float(df_adondevivir2['longitud'].mean()),
        )
    ),
    height=600
)

fig.show()
# %%

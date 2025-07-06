#%% IMPORT LIBRARIES
import pandas as pd
import numpy as np
from sklearn.neighbors import BallTree
import os
# %% READ DFs
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.abspath(os.path.join(BASE_DIR, "..", ".."))
input_path_adondevivir = os.path.join(BASE_DIR, "data", "processed", "adondevivir_processed_geo.csv")
input_path_malls = os.path.join(BASE_DIR, "data", "processed", "malls_processed.csv")
input_path_colegios = os.path.join(BASE_DIR, "data", "processed", "colegios_processed.csv")
input_path_hospitales = os.path.join(BASE_DIR, "data", "processed", "hospitales_processed.csv")

output_path = os.path.join(BASE_DIR, "data", "processed", "proximidad_processed.csv")

df_adondevivir = pd.read_csv(input_path_adondevivir)
df_malls = pd.read_csv(input_path_malls)
df_colegios = pd.read_csv(input_path_colegios)
df_hospitales = pd.read_csv(input_path_hospitales)
# %% 'proximidad_entre' FUNCTION
def proximidad_entre(df_departamentos_1, df_colegios_1, nombre_columna, radius_metros = 500):
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

    return df_departamentos_1
# %% COLUMN 'num_colegios_prox' HAS BEEN ADDED
df = proximidad_entre(df_adondevivir, df_colegios, 'num_colegios_prox')
# %% COLUMN 'num_malls_prox' HAS BEEN ADDED
df = proximidad_entre(df, df_malls, 'num_malls_prox')
# %% COLUMN 'num_hospitales_prox' HAS BEEN ADDED
df = proximidad_entre(df, df_hospitales, 'num_hospitales_prox')
# %% REPLACE NAN VALUES
# replace numerical values
num_cols = df.select_dtypes(include=["number"]).columns
for col in num_cols:
    mediana = df[col].median()
    df[col].fillna(mediana, inplace=True)
# Replacer string values
str_cols = df.select_dtypes(include=["object", "string"]).columns
for col in str_cols:
    if df[col].mode().empty:
        continue  # Evita error si la columna está completamente vacía
    moda = df[col].mode()[0]
    df[col].fillna(moda, inplace=True)
# %% REPLACE VALUES IN "nivel_socieconomico" COLUMN
orden_socioeco = {'A': 4, 'B': 3, 'C': 2, 'D': 1}
df['nivel_socioeconomico'] = df['nivel_socioeconomico'].map(orden_socioeco)
# %% CODE THE COLUMN 'distrito' TO NUMBERS
df['distrito'] = df['distrito'].astype('category').cat.codes
# %% CONVERT COLUMN 'fecha_pub' TO DATETIME
df['fecha_pub'] = pd.to_datetime(df['fecha_pub'], errors='coerce')
df['anio'] = df['fecha_pub'].dt.year
df['mes'] = df['fecha_pub'].dt.month
df['dia'] = df['fecha_pub'].dt.day
df['dia_semana'] = df['fecha_pub'].dt.weekday       # 0 = lunes, 6 = domingo
df['fin_de_semana'] = df['dia_semana'].isin([5, 6]).astype(int)
df['dia_del_anio'] = df['fecha_pub'].dt.dayofyear
# %% CONVERT COLUMN 'latitud' AND 'longitud' TO FLOAD
df['latitud'] = df['latitud'].astype(float)
df['longitud'] = df['longitud'].astype(float)
df
# %% DROP COLUMNS
df = df[['precio_pen', 'mantenimiento_soles', 'area_m2',
       'num_dorm', 'num_banios', 'num_estac', 'antiguedad',
       'num_visualizaciones', 'anio', 'mes', 'dia', 'dia_semana',
       'dia_del_anio','distrito', 'nivel_socioeconomico',
       'latitud', 'longitud', 'num_colegios_prox',
       'num_malls_prox', 'num_hospitales_prox']]
df
# %% EXPORT TO CSV
df.to_csv(output_path)
# %%

#%% IMPORT LIBRARIES
import pandas as pd
import numpy as np
from sklearn.neighbors import BallTree
import os
# %% IMPORT LIBRARIES FOR GRAPHS
import seaborn as sns
import matplotlib.pyplot as plt
# %% FUNCTION 'proximidad_entre'
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
    #indices_cercanos = tree.query_radius(deptos_rad, r=radius_rad)

    # Asignar como nueva columna
    df_departamentos_1 = df_departamentos_1.copy()
    df_departamentos_1[nombre_columna] = counts

    return df_departamentos_1
# %% READ DFs
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.abspath(os.path.join(BASE_DIR, "..", ".."))
input_path_adondevivir = os.path.join(BASE_DIR, "data", "processed", "adondevivir_processed_geo.csv")
input_path_malls = os.path.join(BASE_DIR, "data", "processed", "malls_processed.csv")
input_path_colegios = os.path.join(BASE_DIR, "data", "processed", "colegios_processed.csv")
input_path_hospitales = os.path.join(BASE_DIR, "data", "processed", "hospitales_processed.csv")
input_path_tren = os.path.join(BASE_DIR, "data", "processed", "tren_processed.csv")
input_path_metropolitano = os.path.join(BASE_DIR, "data", "processed", "metropolitano_processed.csv")
input_path_comisarias = os.path.join(BASE_DIR, "data", "processed", "comisarias_processed.csv")

output_path = os.path.join(BASE_DIR, "data", "processed", "proximidad_processed.csv")

df_adondevivir = pd.read_csv(input_path_adondevivir)
df_malls = pd.read_csv(input_path_malls)
df_colegios = pd.read_csv(input_path_colegios)
df_hospitales = pd.read_csv(input_path_hospitales)
df_tren = pd.read_csv(input_path_tren, sep='|')
df_metropolitano = pd.read_csv(input_path_metropolitano, sep='|')
df_comisarias = pd.read_csv(input_path_comisarias)
# %% COLUMN 'num_colegios_prox' HAS BEEN ADDED
df = proximidad_entre(df_adondevivir, df_colegios, 'num_colegios_prox')
# %% COLUMN 'num_malls_prox' HAS BEEN ADDED
df = proximidad_entre(df, df_malls, 'num_malls_prox')
# %% COLUMN 'num_hospitales_prox' HAS BEEN ADDED
df = proximidad_entre(df, df_hospitales, 'num_hospitales_prox')
# %% COLUMN 'num_tren_est_prox' HAS BEEN ADDED
df = proximidad_entre(df, df_tren, 'num_tren_est_prox')
# %% COLUMN 'num_metro_est_prox' HAS BEEN ADDED
df = proximidad_entre(df, df_metropolitano, 'num_metro_est_prox')
# %% COLUMN 'num_comisarias_prox' HAS BEEN ADDED
df = proximidad_entre(df, df_comisarias, 'num_comisarias_prox')
# %%
df
# %% EXPORT TO CSV
df.to_csv(output_path)
# %%

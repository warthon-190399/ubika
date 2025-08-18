#%% IMPORT LIBRARIES
import pandas as pd
import numpy as np
from sklearn.neighbors import BallTree
import os
# %% 
def proximidad_entre(df_1, df_2, nombre_columna, radius_metros = 500):

    df_2 = df_2.dropna(subset=['latitud', 'longitud']).reset_index(drop=True)
    df_1 = df_1.dropna(subset=['latitud', 'longitud']).reset_index(drop=True)

    colegios_rad = np.deg2rad(df_2[['latitud', 'longitud']].values)
    deptos_rad = np.deg2rad(df_1[['latitud', 'longitud']].values)

    earth_radius = 6371000  
    radius_rad = radius_metros / earth_radius  # Convertir a radianes

    tree = BallTree(colegios_rad, metric='haversine')

    counts = tree.query_radius(deptos_rad, r=radius_rad, count_only=True)

    df_1[nombre_columna] = counts

    return df_1


# %% READ DFs
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.abspath(os.path.join(BASE_DIR, "..", ".."))
input_path_adondevivir = os.path.join(BASE_DIR, "data", "processed", "adondevivir_processed_geo.csv")
input_path_colegios = os.path.join(BASE_DIR, "data", "processed", "colegios_processed.csv")
input_path_hospitales = os.path.join(BASE_DIR, "data", "processed", "hospitales_processed.csv")
input_path_tren = os.path.join(BASE_DIR, "data", "processed", "tren_processed.csv")
input_path_metropolitano = os.path.join(BASE_DIR, "data", "processed", "metropolitano_processed.csv")
input_path_comisarias = os.path.join(BASE_DIR, "data", "processed", "comisarias_processed.csv")
input_path_inpe = os.path.join(BASE_DIR, "data", "processed", "inpe_processed.csv")

output_path = os.path.join(BASE_DIR, "data", "processed", "proximidad_processed.csv")

df_adondevivir = pd.read_csv(input_path_adondevivir)
df_colegios = pd.read_csv(input_path_colegios)
df_hospitales = pd.read_csv(input_path_hospitales)
df_tren = pd.read_csv(input_path_tren)
df_metropolitano = pd.read_csv(input_path_metropolitano)
df_comisarias = pd.read_csv(input_path_comisarias)
df_inpe = pd.read_csv(input_path_inpe)
#%%

df = proximidad_entre(df_adondevivir, df_colegios, 'num_colegios_aprox')
df = proximidad_entre(df, df_hospitales, 'num_hospitales_aprox')
df = proximidad_entre(df, df_tren, 'num_tren_est_aprox')
df = proximidad_entre(df, df_metropolitano, 'num_metro_est_aprox')
df = proximidad_entre(df, df_comisarias, 'num_comisarias_aprox')
df = proximidad_entre(df, df_inpe, "num_delitos_aprox")


# %% EXPORT TO CSV
df.to_csv(output_path, index=False)


# %%

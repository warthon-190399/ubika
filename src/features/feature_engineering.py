# %%
import pandas as pd
import numpy as np
import os
# %%
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.abspath(os.path.join(BASE_DIR, "..", ".."))
input_path = os.path.join(BASE_DIR, "data", "processed", "data_preprocessing.csv")
output_path = os.path.join(BASE_DIR, "data", "processed", "data_preprocessing_eng.csv")

df = pd.read_csv(input_path)
df_processed = df.copy()
# %%

df_processed['total_ambientes'] = df_processed['num_dorm'] + df_processed['num_banios']

df_processed['tiene_estac'] = (df_processed['num_estac'] > 0).astype(int)
# %%
df_processed["tamano"] = pd.cut(
    df_processed["area_m2"],
    bins=[0,50,100, float("inf")],
    labels=["pequeno", "mediano", "grande"]
)

df_processed['antiguedad_categoria'] = pd.cut(
    df_processed['antiguedad'],
    bins=[-1, 5, 20, float('inf')],
    labels=['nuevo', 'seminuevo', 'antiguo']
)

df_processed['tamano_cod'] = df_processed['tamano'].map({'pequeno': 1, 'mediano': 2, 'grande': 3})
df_processed['antiguedad_cod'] = df_processed['antiguedad_categoria'].map({'nuevo': 1, 'seminuevo': 2, 'antiguo': 3})
df_processed['nivel_socioeconomico_cod'] = df_processed['nivel_socioeconomico'].map({'A': 1, 'B': 2, 'C': 3, 'D': 4})
# %% precio total por distrito
df_processed['total_servicios_prox'] = (
    df_processed['num_colegios_prox'] + df_processed['num_malls_prox'] + df_processed['num_hospitales_prox'] +
    df_processed['num_tren_est_prox'] + df_processed['num_metro_est_prox'] + df_processed['num_comisarias_prox']
)

df_processed['total_transporte_prox'] =  df_processed['num_tren_est_prox'] + df_processed['num_metro_est_prox']
#%%

df_processed.to_csv(output_path, index = False)
# %%

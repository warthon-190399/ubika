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
df_processed['precio_m2'] = df_processed['precio_pen'] / df_processed['area_m2'].replace(0, pd.NA)
df_processed['mantenimiento_rel'] = df_processed['mantenimiento_soles'] / df_processed['precio_pen'].replace(0, pd.NA)

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




precio_prom_distrito = df_processed.groupby('distrito')['precio_pen'].median().reset_index()
precio_prom_distrito.columns = ['distrito', 'precio_distrito_prom']
df_processed = df_processed.merge(precio_prom_distrito, on='distrito', how='left')
#%%
# Diferencia entre precio del inmueble y promedio del distrito
df_processed['precio_rel_distrito'] = df_processed['precio_pen'] - df_processed['precio_distrito_prom']

# %%
precio_m2_distrito = df_processed.groupby('distrito')['precio_m2'].median().reset_index()
precio_m2_distrito.columns = ['distrito', 'precio_m2_distrito']

df_processed = df_processed.merge(precio_m2_distrito, on='distrito', how='left')

# Comparar con precio m2 del inmueble
df_processed['precio_m2_rel'] = df_processed['precio_m2'] - df_processed['precio_m2_distrito']
# %%
df_processed['precio_m2_sobrevaluado']=np.where(df_processed['precio_m2_rel'] > 0, 1, 0)
df_processed['precio_rel_sobrevaluado']=np.where(df_processed['precio_rel_distrito'] > 0, 1, 0)


#df_processed_1 = df_processed[df_processed["direccion_completa"].notna()]
# %%
df_processed.info()
#%%
df_processed.to_csv(output_path, index = False)
#%% Import Libraries
import pandas as pd
import os 
from sklearn.model_selection import train_test_split
#%% FUNCTION 'imputar_nan_por_grupo'


def imputar_con_medianas(row):
    for col in cols_a_imputar:
        if pd.isna(row[col]):
            if row['distrito'] in medianas.index:
                row[col] = medianas.loc[row['distrito'], col]
    return row

# %% Read df
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.abspath(os.path.join(BASE_DIR, "..", ".."))
input_path = os.path.join(BASE_DIR, "data", "processed", "proximidad_processed.csv")
output_path = os.path.join(BASE_DIR, "data", "processed", "data_preprocessing.csv")

df = pd.read_csv(input_path)
df_processed = df.copy()

# %% DROP VALUES OUT OF RANGE 

q_low = df["precio_pen"].quantile(0.01)
q_high = df["precio_pen"].quantile(0.95)
df_processed = df_processed[(df_processed["precio_pen"] >= q_low) & (df_processed["precio_pen"] <= q_high)]

df_processed = df_processed.drop_duplicates(subset = ['latitud', 'longitud', 'area_m2', 'num_dorm', 'num_banios', 'num_estac', "distrito", "nivel_socioeconomico", "mantenimiento_soles"])

df_processed["num_estac"] = df_processed["num_estac"].fillna(0)
df_processed = df_processed.dropna(subset=["area_m2", "distrito"])


df_temp = df_processed.copy()
df_temp = df_temp.sample(frac=1, random_state=42).reset_index(drop=True)  # shuffle

df_temp['set'] = 'train'
train_data, temp_data = train_test_split(df_temp, test_size=0.4, random_state=42)

eval_data, test_data = train_test_split(temp_data, test_size=0.5, random_state=42)

train_data['set'] = 'train'
eval_data['set'] = 'eval'
test_data['set'] = 'test'

df_processed = pd.concat([train_data, eval_data, test_data]).reset_index(drop=True)

cols_a_imputar = ['num_dorm', 'num_banios', 'antiguedad']

medianas = train_data.groupby('distrito')[cols_a_imputar].median()

df_processed = df_processed.apply(imputar_con_medianas, axis=1)

# %%

conteo_coordenadas = df_processed.groupby(['latitud', 'longitud']).size().reset_index(name='conteo')
conteo_coordenadas = conteo_coordenadas[conteo_coordenadas['conteo'] > 1].sort_values(by="conteo", ascending=False).reset_index()
conteo_coordenadas.index = conteo_coordenadas.index+1

# %% EXPORT TO CSV

df_processed.to_csv(output_path, index=False)

# %%

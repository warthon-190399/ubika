#%% Import Libraries
import pandas as pd
import os 
#%% Functions
def imputar_nan_por_grupo(df, columna_grupo):
    for columna in df.columns:
        if columna == columna_grupo:
            continue  # Evitar modificar la columna usada para agrupar
    
    if df[columna].isnull().any():
            if df[columna].dtype in ['float64', 'int64']:
                # Imputar con mediana por grupo
                df[columna] = df.groupby(columna_grupo)[columna].transform(
                    lambda x: x.fillna(x.median())
                )
                print(f"✅ '{columna}' (numérica) imputada con mediana por '{columna_grupo}'")
            elif df[columna].dtype == 'object':
                # Imputar con moda (valor más frecuente) por grupo
                df[columna] = df.groupby(columna_grupo)[columna].transform(
                    lambda x: x.fillna(x.mode().iloc[0]) if not x.mode().empty else x
                )
                print(f"✅ '{columna}' (texto) imputada con moda por '{columna_grupo}'")

    return df
# %% Read df
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.abspath(os.path.join(BASE_DIR, "..", ".."))
input_path = os.path.join(BASE_DIR, "data", "processed", "proximidad_processed.csv")
output_path = os.path.join(BASE_DIR, "data", "processed", "data_preprocessing.csv")

df = pd.read_csv(input_path)
# %% REPLACE NAN VALUES
df = imputar_nan_por_grupo(df, columna_grupo="distrito")
df
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
# %% DROP VALUES OUT OF RANGE 
q_low = df["precio_pen"].quantile(0.01)
q_high = df["precio_pen"].quantile(0.99)
df = df[(df["precio_pen"] >= q_low) & (df["precio_pen"] <= q_high)]
# %%
df
# %% EXPORT TO CSV
df.to_csv(output_path)
# %%

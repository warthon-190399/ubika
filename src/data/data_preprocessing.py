#%% Import Libraries
import pandas as pd
import os 
#%% FUNCTION 'imputar_nan_por_grupo'
def imputar_nan_por_grupo(df, columna_grupo, column_list):
    for columna in column_list:
        #if columna == columna_grupo:
        #    continue  # Evitar modificar la columna usada para agrupar
    
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
# %% FUNCTION 'eliminar_filas_nan'
def eliminar_filas_nan(df, columna_objetivo):
    """
    Elimina las filas que contienen NaN en una columna específica.

    Parámetros:
    - df: DataFrame original
    - columna_objetivo: str, nombre de la columna que debe no tener NaN

    Retorna:
    - df_filtrado: DataFrame sin las filas con NaN en la columna indicada
    """
    filas_antes = df.shape[0]
    df_filtrado = df.dropna(subset=[columna_objetivo])
    filas_despues = df_filtrado.shape[0]

    print(f"✅ Se eliminaron {filas_antes - filas_despues} filas con NaN en '{columna_objetivo}'")
    
    return df_filtrado

# %% Read df
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.abspath(os.path.join(BASE_DIR, "..", ".."))
input_path = os.path.join(BASE_DIR, "data", "processed", "proximidad_processed.csv")
output_path = os.path.join(BASE_DIR, "data", "processed", "data_preprocessing.csv")

df = pd.read_csv(input_path, )
df_processed = df.copy()
# %% DROP VALUES OUT OF RANGE 

df_processed = df_processed.drop(columns={'Unnamed: 0'})
q_low = df["precio_pen"].quantile(0.01)
q_high = df["precio_pen"].quantile(0.95)
df_processed = df_processed[(df_processed["precio_pen"] >= q_low) & (df_processed["precio_pen"] <= q_high)]

#%%
df_processed = df_processed.drop_duplicates(subset = ['latitud', 'longitud', 'area_m2', 'num_dorm', 'num_banios', 'num_estac', "distrito", "nivel_socioeconomico", "mantenimiento_soles"])

# %%
conteo_coordenadas = df_processed.groupby(['latitud', 'longitud']).size().reset_index(name='conteo')
conteo_coordenadas = conteo_coordenadas[conteo_coordenadas['conteo'] > 1].sort_values(by="conteo", ascending=False).reset_index()
conteo_coordenadas.index = conteo_coordenadas.index+1
# %% EXPORT TO CSV
df_processed.to_csv(output_path, index=False)
# %%

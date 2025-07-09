#%% Import Libraries
import pandas as pd
import os 
# %% Read df
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.abspath(os.path.join(BASE_DIR, "..", ".."))

input_path = os.path.join(BASE_DIR, "data", "raw", "colegios.csv")
output_path = os.path.join(BASE_DIR, "data", "processed", "colegios_processed.csv")

df = pd.read_csv(input_path, sep="|")
df
# %% Rename columns
df.columns = (
    df.columns
    .str.strip()
    .str.lower()
    .str.replace(" ", "_")
    .str.replace("/", "_")
    .str.replace("__", "_")
    .str.replace("á", "a").str.replace("é", "e")
    .str.replace("í", "i").str.replace("ó", "o").str.replace("ú", "u")
)
df.rename(columns = {"nombre_de_ss.ee.":"nombre"}, inplace = True)
df
# %% Drop column
df = df[['nombre', 'distrito', 
       'direccion', 'nivel__modalidad', 'gestion__dependencia',
       'latitud', 'longitud']]
df
# %%
for col in df.select_dtypes(include="object").columns:
    df[col] = (
        df[col] 
        .astype(str)
        .str.strip()
        .str.lower()
        .str.normalize("NFKD")  # quitar tildes y acentos
        .str.encode("ascii", "ignore")
        .str.decode("utf-8")
    )

df["latitud"] = pd.to_numeric(df["latitud"], errors="coerce")
df["longitud"] = pd.to_numeric(df["longitud"], errors="coerce")
df
# %% Estanadrizacion de valores de la columna distrito
df["distrito"] = df["distrito"].replace({"san juan de lurigancho":"sjl",
                                         "san juan de miraflores":"sjm",
                                         "villa maria del triunfo":"vmt",
                                         "san martin de porres":"smp",
                                         "villa el salvador":"ves"})
df
# %% Se eliminan duplicados
df = df.drop_duplicates(subset=['nombre','latitud','longitud'])
df
# %% Export CSV
df.to_csv(output_path, index=False)
# %%

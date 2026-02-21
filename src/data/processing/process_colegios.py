#%% Import Libraries
import pandas as pd
import os 
# %% Read df
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.abspath(os.path.join(BASE_DIR, "..", ".."))

input_path = os.path.join(BASE_DIR, "data", "raw", "colegios.csv")
output_path = os.path.join(BASE_DIR, "data", "processed", "colegios_processed.csv")

df = pd.read_csv(input_path, sep="|")
df_clean = df.copy()

df_clean.columns = (
    df_clean.columns
    .str.strip()
    .str.lower()
    .str.replace(" ", "_")
    .str.replace("/", "_")
    .str.replace("__", "_")
    .str.replace("á", "a").str.replace("é", "e")
    .str.replace("í", "i").str.replace("ó", "o").str.replace("ú", "u")
)
df_clean.rename(columns = {"nombre_de_ss.ee.":"nombre"}, inplace = True)

df_clean = df_clean[['nombre', 'distrito', 
       'direccion', 'nivel__modalidad', 'gestion__dependencia',
       'latitud', 'longitud']]

for col in df_clean.select_dtypes(include="object").columns:
    df_clean[col] = (
        df_clean[col] 
        .astype(str)
        .str.strip()
        .str.lower()
        .str.normalize("NFKD")  # quitar tildes y acentos
        .str.encode("ascii", "ignore")
        .str.decode("utf-8")
    )

df_clean["latitud"] = pd.to_numeric(df_clean["latitud"], errors="coerce")
df_clean["longitud"] = pd.to_numeric(df_clean["longitud"], errors="coerce")
df_clean["distrito"] = df_clean["distrito"].replace({"san juan de lurigancho":"sjl",
                                         "san juan de miraflores":"sjm",
                                         "villa maria del triunfo":"vmt",
                                         "san martin de porres":"smp",
                                         "villa el salvador":"ves"})

df_clean = df_clean.drop_duplicates(subset=['nombre','latitud','longitud']).reset_index()

# %% Export CSV
df_clean.to_csv(output_path, index=False)
# %%

#%% Importar librerias
import pandas as pd
import os
# %%
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.abspath(os.path.join(BASE_DIR, "..", ".."))
input_path = os.path.join(BASE_DIR, "data", "processed", "malls_processed.csv")

output_path = os.path.join(BASE_DIR, "data", "processed", "malls_processed_format.csv")

df = pd.read_csv(input_path)
df
# %% Renombrar columnas
df.rename(columns = {"direccion_ubicacion":"direccion_completa",
                     "lat":"latitud","lon":"longitud"}, inplace=True)
# %% Retirar columnas innecesarias
df = df[['nombre', 'ubicacion', 'direccion_completa', 'distrito',
       'provincia', 'latitud', 'longitud']]
df
# %% Edición de valores de la columna distrito
import unicodedata

def quitar_tildes(texto):
    if isinstance(texto, str):
        return unicodedata.normalize("NFKD", texto).encode("ASCII", "ignore").decode("utf-8")
    return texto  # Si es NaN u otro tipo, lo devuelve igual

df["distrito"] = df["distrito"].astype(str).apply(quitar_tildes).str.lower()
df["distrito"] = df["distrito"].replace({"san juan de lurigancho":"sjl",
                                         "san juan de miraflores":"sjm",
                                         "villa maria del triunfo":"vmt",
                                         "san martin de porres":"smp",
                                         "villa el salvador":"ves"})
df["distrito"].unique()
# %%
df.to_csv(output_path)
# %%

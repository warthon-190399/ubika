#%%
import pandas as pd
# %%
df = pd.read_csv("C:/PC/7. PROYECTOS/Ubika/data/processed/colegios_processed.csv")
#%%
#Estandarización de nombre de las columnas
df.columns
df.rename(columns = {"nombre_de_ss.ee.":"nombre"}, inplace = True)
df.columns
# %%
#Eliminacion de columnas innecesarias
df = df[['nombre', 'distrito', 
       'direccion', 'nivel__modalidad', 'gestion__dependencia',
       'latitud', 'longitud']]
# %%
#Estanadrizacion de valores de la columna distrito
df["distrito"] = df["distrito"].replace({"san juan de lurigancho":"sjl",
                                         "san juan de miraflores":"sjm",
                                         "villa maria del triunfo":"vmt",
                                         "san martin de porres":"smp",
                                         "villa el salvador":"ves"})
df
# %% Se eliminan duplicados
df = df.drop_duplicates(subset=['nombre'])
df
# %%
df.to_csv("C:/PC/7. PROYECTOS/Ubika/data/processed/colegios_processed_format.csv")
# %%

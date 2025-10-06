#%% Import Libraries
import pandas as pd
import os 

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.abspath(os.path.join(BASE_DIR, "..", ".."))

input_path = os.path.join(BASE_DIR, "data", "raw", "inpe.csv")
output_path = os.path.join(BASE_DIR, "data", "processed", "inpe_processed.csv")

#%%
df = pd.read_csv(input_path, sep=",")

df_clean = df.copy()

df_clean.columns = (
    df_clean.columns
    .str.strip()
    .str.lower()
    .str.normalize("NFKD")
    .str.replace(" ", "_")
    .str.replace("/", "_")
    .str.replace("__", "_")
)


df_clean.rename(columns = {"x":"longitud",
                     "y":"latitud",
                     "grado_de_instruccion": "grado_instruccion",
                     "departamento_domicilio": "departamento",
                     "provincia_domicilio": "provincia",
                     "distrito_domicilio": "distrito"
                     }, inplace = True)

df_clean = df_clean[["id", 'latitud', 'longitud', 'periodo', 'ingresos',
                     'grupo_ingresos', 'delito_generico', 'delito_especifico',
                     'tipo_delito', 'situacion_juridica', 'edad', 'grupo_etareo',
                     'genero', 'estado_civil', 'grado_instruccion', 'ocupacion_generico',
                     'ocupacion_especifico', 'nombre_nucleo_urbano',
                     'departamento', 'provincia', 'distrito']]

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

df_clean = df_clean[(df_clean["departamento"].isin(["lima", "callao"])) & (df_clean["provincia"].isin(["lima", "callao"]))]

df_clean["distrito"] = df_clean["distrito"].replace({"san juan de lurigancho":"sjl",
                                         "san juan de miraflores":"sjm",
                                         "villa maria del triunfo":"vmt",
                                         "san martin de porres":"smp",
                                         "villa el salvador":"ves",
                                         "lima": "lima_cercado",
                                        'magdalena del mar': "magdalena",
                                        "santiago de surco": "surco"
                                         })

df_clean = df_clean.drop_duplicates()

#%%

df_clean.to_csv(output_path, index=False)


# %%

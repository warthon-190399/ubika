#%% IMPORT LIBRARIES

import pandas as pd
import googlemaps
import re
import os
import unicodedata
from dotenv import load_dotenv

#%% FUNCTION "obtener_lat_lon", API DE GOOGLE

API_KEY = os.getenv("GOOGLE_GEOENCODING_APIKEY").strip('"')  
gmaps = googlemaps.Client(key=API_KEY)

def getting_lat_lon(direccion):
    try:
        geocode_result = gmaps.geocode(direccion)
        if geocode_result:
            location = geocode_result[0]["geometry"]["location"]
            return (location["lat"], location["lng"])
    except Exception as e:
        print(f"❌ Error en dirección '{direccion}': {e}")
    return (None, None)

#%% FUNCTION "limpiar_direccion"
def direction_format(direccion):
    if pd.isna(direccion):
        return None
    
    # 1. Poner en formato título
    direccion = direccion.title().strip()

    direccion = re.sub(
        r"\bAlt(?:\.|ura)?\s+Cuadra\s+(\d+)\s+De\s+(Avenida\s+\w+(?:\s+\w+)*)",
        r"\2 Cuadra \1",
        direccion,
        flags=re.IGNORECASE
    )

    # 1. Eliminar paréntesis y su contenido
    direccion = re.sub(r"\([^)]*\)", "", direccion)

    # 2. Eliminar frases como "Frente al", "A espaldas de", etc.
    frases_borrar = [
        r"\bFrente Al\b.*?(,|$)",
        r"\bA Espaldas De\b.*?(,|$)",
        r"\bAl Costado De\b.*?(,|$)"
    ]

    for frase in frases_borrar:
        direccion = re.sub(frase, "", direccion, flags=re.IGNORECASE)

    # 2. Reemplazar abreviaturas comunes
    reemplazos = {
        r"\bAv\b\.?": "Avenida",
        r"\bJr\b\.?": "Jiron",
        r"\bCdra\b\.?": "Cuadra",
        r"\bMz\b\.?": "Manzana",
        r"\bDpt\b\.?": "Departamento"
    }

    for patron, reemplazo in reemplazos.items():
        direccion = re.sub(patron, reemplazo, direccion, flags=re.IGNORECASE)
    
    # 4. Eliminar guiones o frases tipo "al 200"
    direccion = re.sub(r"\s*-\s*", ", ", direccion)
    direccion = re.sub(r"\bal\s+\d+", "", direccion, flags=re.IGNORECASE)

    # 4. Quitar múltiples comas o espacios
    direccion = re.sub(r"\s+", " ", direccion)
    direccion = re.sub(r",\s*,", ", ", direccion)
    direccion = re.sub(r"\.+", "", direccion)

    # 5. Eliminar duplicados (ej. San Luis, San Luis)
    partes = [p.strip() for p in direccion.split(",")]
    partes_unicas = []
    for parte in partes:
        if parte and parte not in partes_unicas:
            partes_unicas.append(parte)
    direccion = ", ".join(partes_unicas)

    # 5. Añadir ", Perú" si no está
    if "Peru" not in direccion and "Perú" not in direccion:
        direccion = direccion + ", Perú"

    return direccion.strip()

# %%

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.abspath(os.path.join(BASE_DIR, "..", ".."))
input_path = os.path.join(BASE_DIR, "data", "raw", "IPRESS.csv")
output_path = os.path.join(BASE_DIR, "data", "processed", "hospitales_processed.csv")

input_path_env = os.path.join(BASE_DIR, ".env")
load_dotenv(dotenv_path=input_path_env, override=True)

df = pd.read_csv(input_path, encoding="latin1")

df_clean = df.copy()

#%%

df_clean.columns = (
    df_clean.columns
    .str.strip()
    .str.lower()
    .map(lambda x: unicodedata.normalize('NFKD', x).encode('ascii', 'ignore').decode('utf-8'))
    .str.replace(" ", "_")
    .str.replace("/", "_")
    .str.replace("__", "_")
)

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
#%%
df_clean.columns

#%% EDIT VALUES IN COLUMNS
df_clean = df_clean[(df_clean["departamento"] == "lima") & 
                    (df_clean["condicion"] == "en funcionamiento") &
                    (df_clean["tipo"] == "establecimiento de salud con internamiento")
                    ]

df_clean["direccion_ubicacion"] = df_clean["direccion"] + ", " + df_clean["distrito"] + ", " + df_clean["provincia"]


df_clean["direccion_ubicacion"] = df_clean["direccion_ubicacion"].apply(direction_format) #LIMPIAR TEXTO

df_clean["ubicaciones_tupla"] = df_clean["direccion_ubicacion"].apply(getting_lat_lon) #API google

df_clean["ubicaciones_tupla"] = df_clean["ubicaciones_tupla"].astype("str")

df_clean[["latitud","longitud"]] = df_clean["ubicaciones_tupla"].str.strip("()").str.split(",", expand=True)

df_clean["latitud"] = pd.to_numeric(df_clean["latitud"], errors="coerce")

df_clean["longitud"] = pd.to_numeric(df_clean["longitud"], errors="coerce")
#%%
df_clean = df_clean[['nombre_del_establecimiento', 'provincia', 'distrito', 'direccion', 'direccion_ubicacion', 'latitud','longitud']]

df_clean = df_clean.rename(columns={"nombre_del_establecimiento": "nombre"})
# %% EDIRdición de valores de la columna distrito

df_clean["distrito"] = df_clean["distrito"].replace({"san juan de lurigancho":"sjl",
                                         "san juan de miraflores":"sjm",
                                         "villa maria del triunfo":"vmt",
                                         "san martin de porres":"smp",
                                         "villa el salvador":"ves",
                                         "lima": "lima cercado"
                                         })

df_clean = df_clean.reset_index()
#%%

df_clean.to_csv(output_path, index=False)
# %%

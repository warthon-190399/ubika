
#%% IMPORT LIBRARIES
import pandas as pd
import googlemaps
import re
import os
import unicodedata
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.abspath(os.path.join(BASE_DIR, "..", ".."))
input_path = os.path.join(BASE_DIR, "data", "raw", "IPRESS.csv")
output_path = os.path.join(BASE_DIR, "data", "processed", "hospitales_processed.csv")

input_path_env = os.path.join(BASE_DIR, ".env.example")
load_dotenv(dotenv_path=input_path_env, override=True)

df = pd.read_csv(input_path, encoding="latin1")
#%% API DE GOOGLE
API_KEY = os.getenv("GOOGLE_GEOENCODING_APIKEY").strip('"') # 👈 reemplaza esto por tu clave real

# Crear cliente
gmaps = googlemaps.Client(key=API_KEY)

# Función para obtener lat y lon desde una dirección
def obtener_lat_lon(direccion):
    try:
        geocode_result = gmaps.geocode(direccion)
        if geocode_result:
            location = geocode_result[0]["geometry"]["location"]
            return (location["lat"], location["lng"])
    except Exception as e:
        print(f"❌ Error en dirección '{direccion}': {e}")
    return (None, None)

#Ejemplo: df2["ubicaciones_tupla"] = df["direccion_ubicacion"].apply(obtener_lat_lon) #API google

#%% FUNCIÓN LIMPIAR TEXTO
def limpiar_direccion(direccion):
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

#Ejemplo: df2["direccion_ubicacion"] = df1["direccion_ubicacion"].apply(limpiar_direccion)

#%% EDIT VALUES IN COLUMNS
df = df[df["Departamento"] == "LIMA"]
df = df[df["Condición"] == "EN FUNCIONAMIENTO"]

df = df[df["Tipo"] == "ESTABLECIMIENTO DE SALUD CON INTERNAMIENTO"]
df["direccion_ubicacion"] = df["Dirección"] + ", " + df["Distrito"] + ", " + df["Provincia"]

df["direccion_ubicacion"] = df["direccion_ubicacion"].apply(limpiar_direccion) #LIMPIAR TEXTO

df["ubicaciones_tupla"] = df["direccion_ubicacion"].apply(obtener_lat_lon) #API google

df["ubicaciones_tupla"] = df["ubicaciones_tupla"].astype("str")
df[["latitud","longitud"]] = df["ubicaciones_tupla"].str.strip("()").str.split(",", expand=True)
df["latitud"] = pd.to_numeric(df["latitud"], errors="coerce")
df["longitud"] = pd.to_numeric(df["longitud"], errors="coerce")

df = df[['Nombre del establecimiento', 'Provincia', 'Distrito','Dirección','direccion_ubicacion', 'latitud','longitud']]
# %% Se renombrar columnas
df.rename(columns = {"Nombre del establecimiento":"nombre",
                     "Dirección":"direccion",
                     "direccion_ubicacion":"direccion_completa",
                     "Provincia":"provincia","Distrito":"distrito"
                     }, inplace = True)
df
# %% EDIRdición de valores de la columna distrito
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
#%%
df["provincia"] = df["provincia"].astype(str).apply(quitar_tildes).str.lower()
df["provincia"].unique()
# %%
df.to_csv(output_path)
# %%

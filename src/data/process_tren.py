#%% IMPORT LIBRARIES
import warnings
warnings.simplefilter("ignore")

from bs4 import BeautifulSoup
import requests
import pandas as pd
import googlemaps
import os
import re
import unicodedata
from dotenv import load_dotenv
# %% FILES LOCATION
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.abspath(os.path.join(BASE_DIR, "..", ".."))

input_path_env = os.path.join(BASE_DIR, ".env.example")
output_path = os.path.join(BASE_DIR, "data", "processed", "tren_processed.csv")
load_dotenv(dotenv_path=input_path_env, override=True)
#%% FUNCTION "obtener_lat_lon", API DE GOOGLE
API_KEY = os.getenv("GOOGLE_GEOENCODING_APIKEY").strip('"')  # 👈 reemplaza esto por tu clave real
gmaps = googlemaps.Client(key=API_KEY) # Crear cliente

def obtener_lat_lon(direccion):
    try:
        geocode_result = gmaps.geocode(direccion)
        if geocode_result:
            location = geocode_result[0]["geometry"]["location"]
            return (location["lat"], location["lng"])
    except Exception as e:
        print(f"❌ Error en dirección '{direccion}': {e}")
    return (None, None)
#%% FUNCTION "limpiar_direccion"
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

    # 3. Reemplazar abreviaturas comunes
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

    # 5. Quitar múltiples comas o espacios
    direccion = re.sub(r"\s+", " ", direccion)
    direccion = re.sub(r",\s*,", ", ", direccion)
    direccion = re.sub(r"\.+", "", direccion)

    # 6. Eliminar duplicados (ej. San Luis, San Luis)
    partes = [p.strip() for p in direccion.split(",")]
    partes_unicas = []
    for parte in partes:
        if parte and parte not in partes_unicas:
            partes_unicas.append(parte)
    direccion = ", ".join(partes_unicas)

    # 7. Añadir ", Perú" si no está
    if "Peru" not in direccion and "Perú" not in direccion:
        direccion = direccion + ", Perú"

    return direccion.strip()
# %% FUNCTION "quitar_tildes"
def quitar_tildes(texto):
    if isinstance(texto, str):
        return unicodedata.normalize("NFKD", texto).encode("ASCII", "ignore").decode("utf-8")
    return texto  # Si es NaN u otro tipo, lo devuelve igual
#%% SCRAP WIKIPEDIA
url = "https://es.wikipedia.org/wiki/L%C3%ADnea_1_del_Metro_de_Lima_y_Callao"

data  = requests.get(url).text 
soup = BeautifulSoup(data,"html.parser")
table = soup.find('table', class_='wikitable col3cen')

tren = []
for row in table.find_all('td'):
    tren.append(row.text.strip())

# Convertimos la lista en grupos de 8
filas = [tren[i:i+8] for i in range(0, len(tren), 8)]

columnas = ['nombre', 'fecha', 'Km_acumulado', 'direccion_completa', 'distrito', 'lineas', 'observacion','caracteristica']
df = pd.DataFrame(filas, columns=columnas)
df = df[['nombre','direccion_completa', 'distrito']]
df
#%%
df["direccion_completa"] = df["direccion_completa"].apply(limpiar_direccion)
df
#%% CREATE UBICACIONES
df["ubicaciones_tupla"] = df["direccion_completa"].apply(obtener_lat_lon) #API google
df
#%% CREATE LATITUD AND LOGITUD
df["ubicaciones_tupla"] = df["ubicaciones_tupla"].astype(str)
df[['latitud','longitud']]=df["ubicaciones_tupla"].str.strip("()").str.split(",", expand=True)
df["latitud"] = pd.to_numeric(df["latitud"], errors="coerce")
df["longitud"] = pd.to_numeric(df["longitud"], errors="coerce")
df
#%% DROP COLUMNS
df=df[["nombre","direccion_completa","distrito","latitud","longitud"]]
df
# %% EDIT VALUES IN THE COLUMN "DISTRITO"
df["distrito"] = df["distrito"].astype(str).apply(quitar_tildes).str.lower()
df["distrito"] = df["distrito"].replace({"san juan de lurigancho":"sjl",
                                         "san juan de miraflores":"sjm",
                                         "villa maria del triunfo":"vmt",
                                         "san martin de porres":"smp",
                                         "villa el salvador":"ves"})
df
#%% EXPORT CSV
df.to_csv(output_path, sep='|', index=False)
# %%

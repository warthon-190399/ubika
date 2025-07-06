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

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.abspath(os.path.join(BASE_DIR, "..", ".."))

input_path_env = os.path.join(BASE_DIR, ".env.example")
load_dotenv(dotenv_path=input_path_env, override=True)
#%% SCRAP WIKIPEDIA
url = "https://es.wikipedia.org/wiki/Anexo:Centros_comerciales_del_Per%C3%BA"

data  = requests.get(url).text 
soup = BeautifulSoup(data,"html.parser")
table = soup.find('table')

malls = []
for row in table.find_all('tr'): # in html table row is represented by the tag <tr>
    col = row.find_all('td') # in html a column is represented by the tag <td>
    if col:
        malls.append([col[0].text.strip(), col[1].text.strip()])

df=pd.DataFrame(malls, columns = ["nombre", "ubicacion"])
#%% API DE GOOGLE
API_KEY = os.getenv("GOOGLE_GEOENCODING_APIKEY").strip('"')  # 👈 reemplaza esto por tu clave real

gmaps = googlemaps.Client(key=API_KEY) # Crear cliente

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
#%% CLEAN COLUMN "DIRECCION"
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

#Ejemplo: df2["direccion_ubicacion"] = df1["direccion_ubicacion"].apply(limpiar_direccion)
#%% CREATE COLUMNS
df["direccion_ubicacion"] = df.nombre + ", "+ df.ubicacion 
df[['distrito', 'provincia']] = df['ubicacion'].str.split(',', expand=True)
df
#%% CREATE UBICACIONES
df["ubicaciones_tupla"] = df["direccion_ubicacion"].apply(obtener_lat_lon) #API google
df
#%% CREATE LATITUD AND LOGITUD
df["ubicaciones_tupla"] = df["ubicaciones_tupla"].astype(str)
df[['latitud','longitud']]=df["ubicaciones_tupla"].str.strip("()").str.split(",", expand=True)
df["latitud"] = pd.to_numeric(df["latitud"], errors="coerce")
df["longitud"] = pd.to_numeric(df["longitud"], errors="coerce")
df
# %% RENAME COLUMNS
df.rename(columns = {"direccion_ubicacion":"direccion_completa",}, inplace=True)
df
#%% DROP COLUMNS
df=df[["nombre","ubicacion","direccion_completa","distrito","provincia","latitud","longitud"]]
df
# %% EDIT VALUES IN THE COLUMN "DISTRITO"
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
df
#%% EXPORT CSV
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.abspath(os.path.join(BASE_DIR, "..", ".."))

output_path = os.path.join(BASE_DIR, "data", "processed", "malls_processed.csv")

df.to_csv(output_path)
# %%

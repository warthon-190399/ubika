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

input_path_env = os.path.join(BASE_DIR, ".env.example") #".env"
output_path = os.path.join(BASE_DIR, "data", "processed", "metropolitano_processed.csv")
load_dotenv(dotenv_path=input_path_env, override=True)


#%% FUNCTION "obtener_lat_lon", API DE GOOGLE
API_KEY = os.getenv("GOOGLE_GEOENCODING_APIKEY").strip("''")  # 👈 reemplaza esto por tu clave real
gmaps = googlemaps.Client(key=API_KEY)

def getting_lat_lon(direction):
    try:
        geocode_result = gmaps.geocode(direction)
        if geocode_result:
            location = geocode_result[0]["geometry"]["location"]
            return (location["lat"], location["lng"])
    except Exception as e:
        print(f"❌ Location Error '{direction}': {e}")
    return (None, None)

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

#%%
url = "https://es.wikipedia.org/wiki/Metropolitano_(Lima)"

data  = requests.get(url).text 
soup = BeautifulSoup(data,"html.parser")

#tabla 2
table = soup.find_all('table', class_='wikitable')
table2 = table[2]

metropolitano = []
for row in table2.find_all('td'):
    metropolitano.append(row.text.strip())

#%%
filas = [metropolitano[i:i+3] for i in range(0, len(metropolitano), 3)]
columnas = ['nombre', 'direccion_completa', 'distrito']
df_metropolitano = pd.DataFrame(filas, columns=columnas)
df_metropolitano["direccion_completa"] = df_metropolitano["direccion_completa"].apply(limpiar_direccion)

df_metropolitano["ubicaciones_tupla"] = df_metropolitano["direccion_completa"].apply(getting_lat_lon) #API google

#%%
df_metropolitano["ubicaciones_tupla"] = df_metropolitano["ubicaciones_tupla"].astype(str)
df_metropolitano[['latitud','longitud']]=df_metropolitano["ubicaciones_tupla"].str.strip("()").str.split(",", expand=True)
df_metropolitano["latitud"] = pd.to_numeric(df_metropolitano["latitud"], errors="coerce")
df_metropolitano["longitud"] = pd.to_numeric(df_metropolitano["longitud"], errors="coerce")
df_metropolitano=df_metropolitano[["nombre","direccion_completa","distrito","latitud","longitud"]]

for col in df_metropolitano.select_dtypes(include="object").columns:
    df_metropolitano[col] = (
        df_metropolitano[col] 
        .astype(str)
        .str.strip()
        .str.lower()
        .str.normalize("NFKD")  # quitar tildes y acentos
        .str.encode("ascii", "ignore")
        .str.decode("utf-8")
    )

df_metropolitano["distrito"].unique()

df_metropolitano["distrito"] = df_metropolitano["distrito"].replace({"san juan de lurigancho":"sjl",
                                         "san juan de miraflores":"sjm",
                                         "villa maria del triunfo":"vmt",
                                         "san martin de porres":"smp",
                                         "villa el salvador":"ves",
                                         "comas (lista para su operacion)": "comas",
                                         "independencia[nota 1]":"independencia",
                                         "lima": "lima cercado"
                                         })


#%% EXPORT CSV
df_metropolitano.to_csv(output_path, index=False)
# %%

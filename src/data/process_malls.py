#%%
#!mamba install bs4==4.10.0 -y
#!pip install lxml==4.6.4
#!mamba install html5lib==1.1 -y
#!pip install pandas
# !pip install requests==2.26.0
# pip install --upgrade beautifulsoup4 # Actulizar beautifulsoup4
#pip install --upgrade pandas # Actualizar pandas

import warnings
warnings.simplefilter("ignore")

from bs4 import BeautifulSoup # this module helps in web scrapping.
import requests  # this module helps us to download a web page
#%%
url = "https://es.wikipedia.org/wiki/Anexo:Centros_comerciales_del_Per%C3%BA"

data  = requests.get(url).text 

soup = BeautifulSoup(data,"html.parser")  # create a soup object using the variable 'data'
#%%
#find a html table in the web page
table = soup.find('table') # in html table is represented by the tag <table>

import pandas as pd
#Get all rows from the table
malls = []
for row in table.find_all('tr'): # in html table row is represented by the tag <tr>
    col = row.find_all('td') # in html a column is represented by the tag <td>
    if col:
        #print(col[0].text.strip())
        #print(col[1].text.strip())
        malls.append([col[0].text.strip(), col[1].text.strip()])
        #print("-----------------------------")
df=pd.DataFrame(malls, columns = ["nombre", "ubicacion"])
#df.head()
#%%
import googlemaps
import pandas as pd

# Tu clave de API de Google
API_KEY = "AIzaSyBAiYDo7nmexhH7rkLpwSA-sP_0IJ-FR-8"  # 👈 reemplaza esto por tu clave real

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
#%%
import re

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
#%%
df["direccion_ubicacion"] = df.nombre + ", "+ df.ubicacion 

# Distrito, Provincia
df[['distrito', 'provincia']] = df['ubicacion'].str.split(',', expand=True)
#%%
df["ubicaciones_tupla"] = df["direccion_ubicacion"].apply(obtener_lat_lon) #API google
df
#%%
df["ubicaciones_tupla"] = df["ubicaciones_tupla"].astype(str)
df[['lat','lon']]=df["ubicaciones_tupla"].str.strip("()").str.split(",", expand=True)
df["lat"] = pd.to_numeric(df["lat"], errors="coerce")
df["lon"] = pd.to_numeric(df["lon"], errors="coerce")
#df.head()
#%%
df=df[["nombre","ubicacion","direccion_ubicacion","distrito","provincia","lat","lon"]]
#df.head()
#%%
df.to_csv("C:/PC/7. PROYECTOS/Ubika/data/processed/malls_processed.csv")
# %%


#%%
#Importa librerias
import pandas as pd
import googlemaps
import re
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.abspath(os.path.join(BASE_DIR, "..", ".."))
input_path = os.path.join(BASE_DIR, "data", "raw", "IPRESS.csv")

print(input_path)
df = pd.read_csv(input_path, encoding="latin1")

#%%
#API DE GOOGLE

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
#FUNCIÓN LIMPIAR TEXTO

#import re

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
df2 = df[df["Departamento"] == "LIMA"]

df2 = df2[df2["Condición"] == "EN FUNCIONAMIENTO"]

df2 = df2[df2["Tipo"] == "ESTABLECIMIENTO DE SALUD CON INTERNAMIENTO"]
df2["direccion_ubicacion"] = df2["Dirección"] + ", " + df2["Distrito"] + ", " + df2["Provincia"]

df2["direccion_ubicacion"] = df2["direccion_ubicacion"].apply(limpiar_direccion) #LIMPIAR TEXTO

df2["ubicaciones_tupla"] = df2["direccion_ubicacion"].apply(obtener_lat_lon) #API google

df2["ubicaciones_tupla"] = df2["ubicaciones_tupla"].astype("str")
df2[["lat","lon"]] = df2["ubicaciones_tupla"].str.strip("()").str.split(",", expand=True)
df2["lat"] = pd.to_numeric(df2["lat"], errors="coerce")
df2["lon"] = pd.to_numeric(df2["lon"], errors="coerce")

df2 = df2[['Nombre del establecimiento', 'Departamento', 'Provincia', 'Distrito','Dirección','direccion_ubicacion', 'lat','lon']]

#%%
df2.to_csv("C:/PC/7. PROYECTOS/Ubika/data/processed/hospitales_processed.csv")
# %%

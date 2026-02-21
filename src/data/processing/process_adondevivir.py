#%%
import pandas as pd
import unicodedata
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.abspath(os.path.join(BASE_DIR, "..", ".."))
inputh_path = os.path.join(BASE_DIR, "data", "raw","adondevivir","adondevivir_todo3_completo.csv")
output_path = os.path.join(BASE_DIR, "data", "processed","adondevivir_processed.csv")

df_raw = pd.read_csv(inputh_path)

def extract_prices(valor):
    if pd.isna(valor):
        return pd.Series([None, None])
    precio_pen = None
    precio_usd = None

    partes = valor.split("·")

    for parte in partes:
        parte = parte.strip()
        
        if parte.startswith("S/"):
            precio_pen = int(parte.replace("S/", "").replace(",", "").strip())
        elif parte.startswith("USD"):
            precio_usd = int(parte.replace("USD", "").replace(",", "").strip())

    return pd.Series([precio_pen, precio_usd])

def extraer_mantenimiento(valor):
    if pd.isna(valor):
        return None
    try:
        monto = valor.replace("S/", "").strip().split(" ")[0].replace(",", "")
        return int(monto)
    except:
        return None

def limpiar_direccion(texto):
    if pd.na(texto):
        return ""
    texto.lower()
    texto = unicodedata.normalize('NFD', texto).encode('ascii', 'ignore').decode('utf-8')

def asegurar_termina_en_lima(ubicacion):
    if pd.isna(ubicacion):
        return ubicacion
    ubicacion = ubicacion.strip()
    if not ubicacion.lower().endswith("lima"):
        return ubicacion + ", Lima"
    return ubicacion

def extraer_zona_y_distrito(ubicacion):
    if pd.isna(ubicacion):
        return pd.Series([None, None])

    partes = [p.strip() for p in ubicacion.split(",")]

    if len(partes) == 1:
        return pd.Series([None, partes[0]])
    elif len(partes) == 2:
        return pd.Series([None, partes[0]])
    elif len(partes) >= 3:
        return pd.Series([partes[0], partes[1]])
    else:
        return pd.Series([None, None])

df_raw[["precio_pen", "precio_usd"]] = df_raw["precio"].apply(extract_prices)

df_raw["mantenimiento_soles"] = df_raw["mantenimiento"].apply(extraer_mantenimiento)

df_raw["direccion_limpia"] = (df_raw["direccion"].str.lower()
    .str.normalize("NFKD")
    .str.encode("ascii", "ignore")  
    .str.decode("utf-8")                  
    .str.replace(",", "", regex=False)
    .str.replace(".", "", regex=False)
    .str.replace("  ", " ")  
    .str.strip())

df_raw["ubicacion"] = df_raw["ubicacion"].apply(asegurar_termina_en_lima)
df_raw[["zona", "distrito"]] = df_raw["ubicacion"].apply(extraer_zona_y_distrito)

df_raw["zona"] = (df_raw["zona"]
    .str.lower()
    .str.normalize("NFKD")
    .str.encode("ascii", "ignore")
    .str.decode("utf-8")
    .str.replace(",", "", regex=False)
    .str.replace(".", "", regex=False)
    .str.replace("  ", " ")
    .str.strip()
)

df_raw["distrito"] = (df_raw["distrito"]
    .str.lower()
    .str.normalize("NFKD")
    .str.encode("ascii", "ignore")
    .str.decode("utf-8")
    .str.replace(",", "", regex=False)
    .str.replace(".", "", regex=False)
    .str.replace("  ", " ")
    .str.strip()
)

df_raw["area_m2"] = df_raw["area"].apply(lambda x: str(x).split(" ")[0] if pd.notna(x) else None)
df_raw["area_m2"] = df_raw["area_m2"].astype(float)

df_raw["num_dorm"] = df_raw["dorm"].apply(lambda x: str(x).split(" ")[0] if pd.notna(x) else None)
df_raw["num_dorm"] = df_raw["num_dorm"].astype(float)

df_raw["num_banios"] = df_raw["banios"].apply(lambda x: str(x).split(" ")[0] if pd.notna(x) else None)
df_raw["num_banios"] = df_raw["num_banios"].astype(float)

df_raw["num_estac"] = df_raw["estac"].apply(lambda x: str(x).split(" ")[0] if pd.notna(x) else None)
df_raw["num_estac"] = df_raw["num_estac"].astype(float)

df_raw["antiguedad_inmueble"] = df_raw["antiguedad_inmueble"].replace({"A estrenar": 0})

df_raw["antiguedad"] = df_raw["antiguedad_inmueble"].apply(lambda x: str(x).split(" ")[0] if pd.notna(x) else None)
df_raw["antiguedad"] = df_raw["antiguedad"].astype(float)

df_raw["num_visualizaciones"] = df_raw["visualizaciones"].apply(lambda x: str(x).split(" ")[0] if pd.notna(x) else None)
df_raw["num_visualizaciones"] = df_raw["num_visualizaciones"].astype(float)

df_raw = df_raw.rename(columns={"fecha_publicacion_exacta":  "fecha_pub"})

mapeo_ubicaciones = {
    "lima": "lima cercado",
    "lima cercado": "lima cercado",
    "chosica (lurigancho)": "lurigancho",
    "ate vitarte": "ate",
    "san juan de lurigancho": "sjl",
    "san juan de miraflores": "sjm",
    "villa maria del triunfo": "vmt",
    "villa el salvador": "ves",
    "santiago de surco": "surco",
    "jesus maria": "jesus maria",
    "la victoria": "la victoria",
    "los olivos": "los olivos",
    "san martin de porres": "smp",
    "san miguel": "san miguel",
    "pueblo libre": "pueblo libre",
    "san borja": "san borja",
    "san isidro": "san isidro",
    "barranco": "barranco",
    "magdalena": "magdalena",
    "surquillo": "surquillo",
    "lince": "lince",
    "brena": "brena",
    "la molina": "la molina",
    "san luis": "san luis",
    "independencia": "independencia",
    "comas": "comas",
    "rimac": "rimac",
    "el agustino": "el agustino",
    "santa anita": "santa anita",
    "carabayllo": "carabayllo",
    "puente piedra": "puente piedra",
    "ancon": "ancon",
    "lurin": "lurin",
    "pachacamac": "pachacamac",
    "cieneguilla": "cieneguilla",
    "san bartolo": "san bartolo",
    "punta negra": "punta negra",
    "punta hermosa": "punta hermosa",
    "santa maria del mar": "santa maria del mar",
    "chorrillos": "chorrillos",
    "callao": "callao",
    "miraflores": "miraflores",
    "chaclacayo": "chaclacayo",
    "pucusana": "pucusana"
}

mapeo_socioeconomico = {
    # Nivel A
    "san isidro": "A",
    "miraflores": "A",
    "la molina": "A",
    "barranco": "A",
    "san borja": "A",
    "surco": "A",

    # Nivel B
    
    "jesus maria": "B",
    "magdalena": "B",
    "lince": "B",
    "pueblo libre": "B",
    "san miguel": "B",
    "chorrillos": "B",
    "santa anita": "B",
    "cieneguilla": "B",
    "san bartolo": "B",
    "punta negra": "B",
    "punta hermosa": "B",
    "santa maria del mar": "B",
    "pucusana": "B",

    # Nivel C
    "brena": "C",
    "surquillo": "C",
    "la victoria": "C",
    "independencia": "C",
    "los olivos": "C",
    "el agustino": "C",
    "ate": "C",
    "smp": "C",
    "comas": "C",
    "callao": "C",
    "rimac": "C",
    "lima cercado": "C",
    "san luis": "C",
    "chaclacayo": "C",

    # Nivel D
    "sjl": "D",
    "sjm": "D",
    "vmt": "D",
    "ves": "D",
    "carabayllo": "D",
    "puente piedra": "D",
    "ancon": "D",
    "lurin": "D",
    "pachacamac": "D",
    "lurigancho": "D",
}

df_raw['ubicacion_normalizada'] = df_raw['distrito'].map(mapeo_ubicaciones)
df_raw['nivel_socioeconomico'] = df_raw['ubicacion_normalizada'].map(mapeo_socioeconomico)


df_processed = df_raw[['precio_pen', 'precio_usd', 'mantenimiento_soles', 'direccion_limpia', 'zona', 'distrito', 'area_m2', 'num_dorm', 'num_banios', 'num_estac', 'antiguedad', "num_visualizaciones", "fecha_pub", "ubicacion_normalizada", "nivel_socioeconomico", "URL"]]

df_processed['direccion_limpia'] = df_processed.apply(
    lambda row: row['zona'] if row['direccion_limpia'] == 'direccion no informada' else row['direccion_limpia'],
    axis=1
)

#%%

df_processed["direccion_completa"] = df_processed["direccion_limpia"] + ", " + df_processed["distrito"]

df_processed = df_processed.drop(columns={"direccion_limpia", "zona", "distrito"})

df_processed = df_processed.rename(columns={"ubicacion_normalizada": "distrito"})

#%%

df_processed.to_csv(output_path, index=False)

# %%

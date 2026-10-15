import sys
from pathlib import Path
import pandas as pd
import googlemaps
import re
import os
import unicodedata
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))
from sqlalchemy import text
from service.db_client import get_engine
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.abspath(os.path.join(BASE_DIR, "..", "..", ".."))
input_path     = os.path.join(BASE_DIR, "data", "raw", "IPRESS.csv")
input_path_env = os.path.join(BASE_DIR, ".env")
load_dotenv(dotenv_path=input_path_env, override=True)

API_KEY = os.getenv("GOOGLE_GEOENCODING_APIKEY").strip('"')
gmaps   = googlemaps.Client(key=API_KEY)

def getting_lat_lon(direccion):
    try:
        result = gmaps.geocode(direccion)
        if result:
            loc = result[0]["geometry"]["location"]
            return loc["lat"], loc["lng"]
    except Exception as e:
        print(f"❌ {direccion}: {e}")
    return None, None

def direction_format(direccion):
    if pd.isna(direccion):
        return None
    direccion = direccion.title().strip()
    direccion = re.sub(r"\([^)]*\)", "", direccion)
    for frase in [r"\bFrente Al\b.*?(,|$)", r"\bA Espaldas De\b.*?(,|$)", r"\bAl Costado De\b.*?(,|$)"]:
        direccion = re.sub(frase, "", direccion, flags=re.IGNORECASE)
    for patron, reemplazo in {r"\bAv\b\.?": "Avenida", r"\bJr\b\.?": "Jiron", r"\bCdra\b\.?": "Cuadra"}.items():
        direccion = re.sub(patron, reemplazo, direccion, flags=re.IGNORECASE)
    direccion = re.sub(r"\s*-\s*", ", ", direccion)
    direccion = re.sub(r"\s+", " ", direccion)
    direccion = re.sub(r",\s*,", ", ", direccion)
    direccion = re.sub(r"\.+", "", direccion)
    partes = [p.strip() for p in direccion.split(",")]
    partes = list(dict.fromkeys(p for p in partes if p))
    direccion = ", ".join(partes)
    if "Peru" not in direccion and "Perú" not in direccion:
        direccion += ", Perú"
    return direccion.strip()

df = pd.read_csv(input_path, encoding="latin1")
df_clean = df.copy()

df_clean.columns = (
    df_clean.columns.str.strip().str.lower()
    .map(lambda x: unicodedata.normalize('NFKD', x).encode('ascii', 'ignore').decode('utf-8'))
    .str.replace(" ", "_").str.replace("/", "_").str.replace("__", "_")
)

for col in df_clean.select_dtypes(include="object").columns:
    df_clean[col] = (
        df_clean[col].astype(str).str.strip().str.lower()
        .str.normalize("NFKD").str.encode("ascii", "ignore").str.decode("utf-8")
    )

df_clean = df_clean[
    (df_clean["departamento"] == "lima") &
    (df_clean["condicion"] == "en funcionamiento") &
    (df_clean["tipo"] == "establecimiento de salud con internamiento")
]

df_clean["direccion_ubicacion"] = (
    df_clean["direccion"] + ", " + df_clean["distrito"] + ", " + df_clean["provincia"]
)
df_clean["direccion_ubicacion"] = df_clean["direccion_ubicacion"].apply(direction_format)

coords = df_clean["direccion_ubicacion"].apply(getting_lat_lon)
df_clean["latitud"]  = coords.apply(lambda x: x[0])
df_clean["longitud"] = coords.apply(lambda x: x[1])

df_clean = df_clean[['nombre_del_establecimiento', 'provincia', 'distrito',
                     'direccion', 'direccion_ubicacion', 'latitud', 'longitud']]
df_clean = df_clean.rename(columns={"nombre_del_establecimiento": "nombre"})

df_clean["distrito"] = df_clean["distrito"].replace({
    "san juan de lurigancho": "sjl",
    "san juan de miraflores": "sjm",
    "villa maria del triunfo": "vmt",
    "san martin de porres":   "smp",
    "villa el salvador":      "ves",
    "lima":                   "lima cercado"
})
df_clean = df_clean.reset_index(drop=True)


engine = get_engine()
with engine.begin() as conn:
    conn.execute(text("TRUNCATE TABLE hospitales RESTART IDENTITY"))

df_clean.to_sql("hospitales", engine, if_exists="append", index=False, method="multi", chunksize=500)
print(f"✅ hospitales: {len(df_clean)} filas cargadas a Neon")
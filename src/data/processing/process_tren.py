import sys
from pathlib import Path
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

ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))
from sqlalchemy import text
from service.db_client import get_engine

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.abspath(os.path.join(BASE_DIR, "..", "..", ".."))
load_dotenv(dotenv_path=os.path.join(BASE_DIR, ".env"), override=True)

API_KEY = os.getenv("GOOGLE_GEOENCODING_APIKEY").strip('"')
gmaps   = googlemaps.Client(key=API_KEY)

# def getting_lat_lon(direccion):
#     try:
#         result = gmaps.geocode(direccion)
#         if result:
#             loc = result[0]["geometry"]["location"]
#             return loc["lat"], loc["lng"]
#     except Exception as e:
#         print(f"❌ {direccion}: {e}")
#     return None, None

# def direction_format(direccion):
#     if pd.isna(direccion):
#         return None
#     direccion = direccion.title().strip()
#     direccion = re.sub(r"\([^)]*\)", "", direccion)
#     for frase in [r"\bFrente Al\b.*?(,|$)", r"\bA Espaldas De\b.*?(,|$)", r"\bAl Costado De\b.*?(,|$)"]:
#         direccion = re.sub(frase, "", direccion, flags=re.IGNORECASE)
#     for patron, reemplazo in {r"\bAv\b\.?": "Avenida", r"\bJr\b\.?": "Jiron", r"\bCdra\b\.?": "Cuadra"}.items():
#         direccion = re.sub(patron, reemplazo, direccion, flags=re.IGNORECASE)
#     direccion = re.sub(r"\s*-\s*", ", ", direccion)
#     direccion = re.sub(r"\s+", " ", direccion)
#     direccion = re.sub(r",\s*,", ", ", direccion)
#     direccion = re.sub(r"\.+", "", direccion)
#     partes = list(dict.fromkeys(p.strip() for p in direccion.split(",") if p.strip()))
#     direccion = ", ".join(partes)
#     if "Peru" not in direccion and "Perú" not in direccion:
#         direccion += ", Perú"
#     return direccion.strip()

# url   = "https://es.wikipedia.org/wiki/L%C3%ADnea_1_del_Metro_de_Lima_y_Callao"
# soup  = BeautifulSoup(requests.get(url).text, "html.parser")
# table = soup.find('table', class_='wikitable col3cen')

# tren  = [row.text.strip() for row in table.find_all('td')]
# filas = [tren[i:i+8] for i in range(0, len(tren), 8)]
# df    = pd.DataFrame(filas, columns=['nombre','fecha','Km_acumulado','direccion_completa','distrito','lineas','observacion','caracteristica'])
# df    = df[['nombre', 'direccion_completa', 'distrito']]

# df["direccion_completa"] = df["direccion_completa"].apply(direction_format)

# coords = df["direccion_completa"].apply(getting_lat_lon)
# df["latitud"]  = coords.apply(lambda x: x[0])
# df["longitud"] = coords.apply(lambda x: x[1])

# df = df[["nombre", "direccion_completa", "distrito", "latitud", "longitud"]]

# for col in df.select_dtypes(include="object").columns:
#     df[col] = (
#         df[col].astype(str).str.strip().str.lower()
#         .str.normalize("NFKD").str.encode("ascii", "ignore").str.decode("utf-8")
#     )

# df["distrito"] = df["distrito"].replace({
#     "san juan de lurigancho": "sjl",
#     "san juan de miraflores": "sjm",
#     "villa maria del triunfo": "vmt",
#     "san martin de porres":   "smp",
#     "villa el salvador":      "ves",
#     "lima":                   "lima cercado"
# })

df = pd.read_csv("D:/projects/ubika/data/processed/tren_processed.csv")

engine = get_engine()
with engine.begin() as conn:
    conn.execute(text("TRUNCATE TABLE tren RESTART IDENTITY"))

df.to_sql("tren", engine, if_exists="append", index=False, method="multi", chunksize=500)
print(f"✅ tren: {len(df)} filas cargadas a Neon")

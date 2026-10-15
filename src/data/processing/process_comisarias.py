#%% IMPORT LIBRARIES
import sys
from pathlib import Path
import pandas as pd
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
input_path = os.path.join(BASE_DIR, "data", "raw", "Relación de comisarías básicas 1318.csv")

def quitar_tildes(texto):
    if isinstance(texto, str):
        return unicodedata.normalize("NFKD", texto).encode("ASCII", "ignore").decode("utf-8")
    return texto

df = pd.read_csv(input_path, sep=';', encoding="latin1")
df = df[df['NOMBREDD'] == "LIMA"]
df = df[['COMISARÍA', 'NOMBREPP', 'NOMBREDI', 'GPS']]

df["GPS"] = df["GPS"].astype("str")
df[["latitud", "longitud"]] = df["GPS"].str.split(",", expand=True)
df["latitud"]  = pd.to_numeric(df["latitud"],  errors="coerce")
df["longitud"] = pd.to_numeric(df["longitud"], errors="coerce")

df = df[['COMISARÍA', 'NOMBREPP', 'NOMBREDI', 'latitud', 'longitud']]
df.rename(columns={"COMISARÍA": "nombre", "NOMBREPP": "provincia", "NOMBREDI": "distrito"}, inplace=True)

df["distrito"] = df["distrito"].astype(str).apply(quitar_tildes).str.lower()
df["distrito"] = df["distrito"].replace({
    "san juan de lurigancho": "sjl",
    "san juan de miraflores": "sjm",
    "villa maria del triunfo": "vmt",
    "san martin de porres":   "smp",
    "villa el salvador":      "ves"
})
df["provincia"] = df["provincia"].astype(str).apply(quitar_tildes).str.lower()


engine = get_engine()
with engine.begin() as conn:
    conn.execute(text("TRUNCATE TABLE comisarias RESTART IDENTITY"))

df.to_sql("comisarias", engine, if_exists="append", index=False, method="multi", chunksize=500)
print(f"✅ comisarias: {len(df)} filas cargadas a Neon")

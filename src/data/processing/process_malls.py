import sys
from pathlib import Path
import os
import pandas as pd
import warnings
warnings.simplefilter("ignore")

ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))
from sqlalchemy import text
from service.db_client import get_engine

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.abspath(os.path.join(BASE_DIR, "..", "..", ".."))
input_path = os.path.join(BASE_DIR, "data", "raw", "osm_malls.csv")

df = pd.read_csv(input_path, sep=None, engine="python", encoding="utf-8-sig")
df = df[["name", "@lat", "@lon"]]
df.rename(columns={"name": "nombre", "@lat": "latitud", "@lon": "longitud"}, inplace=True)

engine = get_engine()
with engine.begin() as conn:
    conn.execute(text("TRUNCATE TABLE malls RESTART IDENTITY"))

df.to_sql("malls", engine, if_exists="append", index=False, method="multi", chunksize=500)
print(f"✅ malls: {len(df)} filas cargadas a Neon")
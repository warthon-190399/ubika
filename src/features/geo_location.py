"""
geo_location.py
===============
Lee propiedades_procesadas desde Neon, geocodifica direccion_completa
con Google Maps y actualiza las columnas latitud/longitud en la misma tabla.

Solo procesa filas donde latitud IS NULL para no repetir llamadas a la API.

Uso:
    python src/features/geo_location.py
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

import os
import logging
from time import sleep

import pandas as pd
import googlemaps
from dotenv import load_dotenv
from sqlalchemy import text
from service.db_client import get_engine

load_dotenv(ROOT / ".env")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


# ------------------------------------------------------------------
# Geocodificación
# ------------------------------------------------------------------

def obtener_coordenadas(direccion: str, gmaps, contador: int = None):
    try:
        resultado = gmaps.geocode(direccion)
        if resultado:
            lat = resultado[0]["geometry"]["location"]["lat"]
            lon = resultado[0]["geometry"]["location"]["lng"]
            logger.info(f"  [{contador}] ✅ {direccion[:60]}")
            return lat, lon
        else:
            logger.warning(f"  [{contador}] ⚠️ Sin resultados: {direccion[:60]}")
            return None, None
    except Exception as e:
        logger.error(f"  [{contador}] ❌ Error: {e}")
        return None, None


# ------------------------------------------------------------------
# Pipeline principal
# ------------------------------------------------------------------

def main():
    api_key = os.getenv("GOOGLE_GEOENCODING_APIKEY", "").strip().strip('"').strip("'")
    if not api_key:
        raise EnvironmentError("Falta GOOGLE_GEOENCODING_APIKEY en .env")

    gmaps  = googlemaps.Client(key=api_key)
    engine = get_engine()

    # 1. Leer solo filas sin coordenadas aún
    logger.info("Leyendo filas sin geocodificar...")
    df = pd.read_sql(
        "SELECT prop_id, direccion_completa, distrito FROM propiedades_procesadas WHERE latitud IS NULL",
        engine,
    )
    logger.info(f"  {len(df)} filas por geocodificar")

    if df.empty:
        logger.info("Todo ya está geocodificado.")
        return

    # 2. Geocodificar
    resultados = []
    for i, row in enumerate(df.itertuples(), start=1):
        direccion = row.direccion_completa if pd.notna(row.direccion_completa) else row.distrito
        lat, lon  = obtener_coordenadas(direccion, gmaps, contador=i)
        resultados.append({"prop_id": row.prop_id, "latitud": lat, "longitud": lon})
        sleep(1)  # respetar rate limit de Google

    # 3. Actualizar en Neon fila por fila
    logger.info("Guardando coordenadas en Neon...")
    ok = errors = 0
    with engine.begin() as conn:
        for r in resultados:
            if r["latitud"] is None:
                errors += 1
                continue
            conn.execute(
                text("""
                    UPDATE propiedades_procesadas
                    SET latitud  = :lat,
                        longitud = :lon
                    WHERE prop_id = :id
                """),
                {"lat": r["latitud"], "lon": r["longitud"], "id": str(r["prop_id"])},
            )
            ok += 1

    logger.info(f"✅ Geocodificadas: {ok}  |  Sin resultado: {errors}")


if __name__ == "__main__":
    main()
"""
process_proximidad.py
=====================
Lee propiedades_procesadas y tablas de referencia desde Neon,
calcula proximidades con BallTree y escribe el resultado
en la tabla proximidades.
 
Uso:
    python src/data/processing/process_proximidad.py
"""
 
import sys
from pathlib import Path
 
ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))
 
import logging
import numpy as np
import pandas as pd
from sklearn.neighbors import BallTree
from sqlalchemy import text
from service.db_client import get_engine
 
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)
 
 
# ------------------------------------------------------------------
# Función de proximidad — igual que el original
# ------------------------------------------------------------------
 
def proximidad_entre(df_props, df_ref, nombre_columna, radius_metros=500):
    df_ref   = df_ref.dropna(subset=["latitud", "longitud"]).reset_index(drop=True)
    df_props = df_props.dropna(subset=["latitud", "longitud"]).reset_index(drop=True)
 
    ref_rad   = np.deg2rad(df_ref[["latitud", "longitud"]].values)
    props_rad = np.deg2rad(df_props[["latitud", "longitud"]].values)
 
    radius_rad = radius_metros / 6_371_000  # metros → radianes
 
    tree   = BallTree(ref_rad, metric="haversine")
    counts = tree.query_radius(props_rad, r=radius_rad, count_only=True)
 
    df_props[nombre_columna] = counts
    return df_props
 
 
# ------------------------------------------------------------------
# Pipeline principal
# ------------------------------------------------------------------
 
def main():
    engine = get_engine()
 
    # 1. Leer propiedades con coordenadas
    logger.info("Leyendo propiedades_procesadas...")
    df = pd.read_sql(
        "SELECT prop_id, latitud, longitud FROM propiedades_procesadas WHERE latitud IS NOT NULL",
        engine,
    )
    logger.info(f"  {len(df)} propiedades con coordenadas")
 
    if df.empty:
        logger.warning("No hay propiedades geocodificadas. Corre geo_location.py primero.")
        return
 
    # 2. Leer tablas de referencia
    logger.info("Leyendo tablas de referencia...")
    df_colegios     = pd.read_sql("SELECT latitud, longitud FROM colegios",     engine)
    df_hospitales   = pd.read_sql("SELECT latitud, longitud FROM hospitales",   engine)
    df_tren         = pd.read_sql("SELECT latitud, longitud FROM tren",         engine)
    df_metro        = pd.read_sql("SELECT latitud, longitud FROM metropolitano",engine)
    df_comisarias   = pd.read_sql("SELECT latitud, longitud FROM comisarias",   engine)
    df_inpe         = pd.read_sql("SELECT latitud, longitud FROM inpe",         engine)
    df_malls        = pd.read_sql("SELECT latitud, longitud FROM malls",        engine)
 
    logger.info(f"  colegios:    {len(df_colegios)}")
    logger.info(f"  hospitales:  {len(df_hospitales)}")
    logger.info(f"  tren:        {len(df_tren)}")
    logger.info(f"  metro:       {len(df_metro)}")
    logger.info(f"  comisarias:  {len(df_comisarias)}")
    logger.info(f"  inpe:        {len(df_inpe)}")
    logger.info(f"  malls:       {len(df_malls)}")
 
    # 3. Calcular proximidades
    logger.info("Calculando proximidades (r=500m)...")
    df = proximidad_entre(df, df_colegios,   "num_colegios_aprox")
    df = proximidad_entre(df, df_hospitales, "num_hospitales_aprox")
    df = proximidad_entre(df, df_tren,       "num_tren_est_aprox")
    df = proximidad_entre(df, df_metro,      "num_metro_est_aprox")
    df = proximidad_entre(df, df_comisarias, "num_comisarias_aprox")
    df = proximidad_entre(df, df_inpe,       "num_delitos_aprox")
    df = proximidad_entre(df, df_malls,      "num_malls_aprox")
 
    df_out = df[[
        "prop_id",
        "num_colegios_aprox",
        "num_hospitales_aprox",
        "num_tren_est_aprox",
        "num_metro_est_aprox",
        "num_comisarias_aprox",
        "num_delitos_aprox",
        "num_malls_aprox",
    ]]
 
    logger.info(f"  Proximidades calculadas para {len(df_out)} propiedades")
 
    # 4. Escribir a Neon
    logger.info("Escribiendo proximidades en Neon...")
    with engine.begin() as conn:
        conn.execute(text("TRUNCATE TABLE proximidades"))
 
    df_out.to_sql(
        "proximidades",
        engine,
        if_exists="append",
        index=False,
        method="multi",
        chunksize=500,
    )
    logger.info(f"✅ {len(df_out)} filas escritas en proximidades")
 
 
if __name__ == "__main__":
    main()
 
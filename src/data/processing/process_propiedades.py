"""
process_propiedades.py
======================
Lee propiedades_clean desde Neon, limpia y normaliza,
escribe el resultado en propiedades_procesadas.
 
Corre después de refresh_propiedades.py:
    python src/data/processing/process_propiedades.py
"""
 
import sys
from pathlib import Path
 
ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))
 
import logging
import unicodedata
import pandas as pd
from sqlalchemy import text
from service.db_client import get_engine
 
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)
 

 
MAPEO_UBICACIONES = {
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
    "magdalena del mar": "magdalena",
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
    "pucusana": "pucusana",
}
 
MAPEO_NSE = {
    "san isidro": "A", "miraflores": "A", "la molina": "A",
    "barranco": "A",   "san borja": "A",  "surco": "A",
    "jesus maria": "B", "magdalena": "B", "lince": "B",
    "pueblo libre": "B", "san miguel": "B", "chorrillos": "B",
    "santa anita": "B", "cieneguilla": "B", "san bartolo": "B",
    "punta negra": "B", "punta hermosa": "B",
    "santa maria del mar": "B", "pucusana": "B",
    "brena": "C",     "surquillo": "C",  "la victoria": "C",
    "independencia": "C", "los olivos": "C", "el agustino": "C",
    "ate": "C",       "smp": "C",        "comas": "C",
    "callao": "C",    "rimac": "C",      "lima cercado": "C",
    "san luis": "C",  "chaclacayo": "C",
    "sjl": "D",  "sjm": "D",  "vmt": "D",  "ves": "D",
    "carabayllo": "D", "puente piedra": "D", "ancon": "D",
    "lurin": "D", "pachacamac": "D", "lurigancho": "D",
}
 
 
# ------------------------------------------------------------------
# Funciones de limpieza
# ------------------------------------------------------------------
 
def normalizar_texto(s: str) -> str:
    """Minúsculas, sin tildes, sin comas ni puntos, sin espacios dobles."""
    if not isinstance(s, str):
        return ""
    s = s.lower().strip()
    s = unicodedata.normalize("NFD", s).encode("ascii", "ignore").decode("utf-8")
    s = s.replace(",", "").replace(".", "").replace("  ", " ")
    return s.strip()
 
 
def extract_prices(valor):
    """'S/ 5,916 · USD 1,700' → (5916, 1700)"""
    if pd.isna(valor):
        return None, None
    precio_pen = precio_usd = None
    for parte in str(valor).split("·"):
        parte = parte.strip()
        if parte.startswith("S/"):
            try:
                precio_pen = int(parte.replace("S/", "").replace(",", "").strip())
            except ValueError:
                pass
        elif parte.startswith("USD"):
            try:
                precio_usd = int(parte.replace("USD", "").replace(",", "").strip())
            except ValueError:
                pass
    return precio_pen, precio_usd
 
 
def extraer_mantenimiento(valor):
    """'S/ 850 Mantenimiento' → 850"""
    if pd.isna(valor):
        return None
    try:
        return int(str(valor).replace("S/", "").strip().split(" ")[0].replace(",", ""))
    except (ValueError, IndexError):
        return None
 
 
def extraer_numero(valor):
    """Extrae el primer número de un string como '2 dorm.' → 2.0"""
    if pd.isna(valor):
        return None
    try:
        return float(str(valor).split(" ")[0].replace(",", "."))
    except ValueError:
        return None
 
 
def extraer_antiguedad(valor):
    """'15 años' → 15.0  |  'A estrenar' → 0.0"""
    if pd.isna(valor):
        return None
    s = str(valor).strip()
    if s.lower() in ("a estrenar", "0"):
        return 0.0
    try:
        return float(s.split(" ")[0])
    except ValueError:
        return None
 
 
def extraer_distrito_principal(distrito_raw):
    """
    'Malecon Marina, Miraflores' → 'miraflores'
    'Santiago de Surco, Lima'    → 'santiago de surco'  → normaliza a 'surco'
    Toma siempre el último segmento si hay coma, o el único disponible.
    """
    if pd.isna(distrito_raw):
        return None
    partes = [normalizar_texto(p) for p in str(distrito_raw).split(",")]
    # El último suele ser el distrito principal (ej: "Miraflores", "Lima")
    # Si el último es solo "lima" y hay más partes, tomamos el penúltimo
    if len(partes) >= 2 and partes[-1] in ("lima", ""):
        return partes[-2]
    return partes[-1]
 
 
def construir_direccion(direccion, distrito_norm):
    """Combina dirección limpia + distrito normalizado."""
    d = normalizar_texto(str(direccion)) if pd.notna(direccion) else ""
    if d in ("", "direccion no informada"):
        d = distrito_norm or ""
    dist = distrito_norm or ""
    return f"{d}, {dist}".strip(", ")
 
 
# ------------------------------------------------------------------
# Pipeline principal
# ------------------------------------------------------------------
 
def main():
    engine = get_engine()
 
    # 1. Leer propiedades_union
    logger.info("Leyendo propiedades_union desde Neon...")
    df = pd.read_sql("SELECT * FROM propiedades_union", engine)
    logger.info(f"  {len(df)} filas cargadas")
 
    # 2. Precios
    logger.info("Procesando precios...")
    precios = df["precio"].apply(extract_prices)
    df["precio_pen"] = precios.apply(lambda x: x[0])
    df["precio_usd"] = precios.apply(lambda x: x[1])
    df["mantenimiento_soles"] = df["mantenimiento"].apply(extraer_mantenimiento)
 
    # 3. Características numéricas
    logger.info("Procesando características...")
    df["area_m2"]    = df["m2_total"].apply(extraer_numero)
    df["num_dorm"]   = df["dorms"].apply(extraer_numero)
    df["num_banios"] = df["banos"].apply(extraer_numero)
    df["num_estac"]  = df["estac"].apply(extraer_numero)
    df["antiguedad"] = df["antiguedad"].apply(extraer_antiguedad)
 
    # 4. Ubicación
    logger.info("Normalizando ubicación...")
    df["distrito_raw"]  = df["distrito"].apply(extraer_distrito_principal)
    df["distrito_norm"] = df["distrito_raw"].map(MAPEO_UBICACIONES)
    # fallback: si no está en el mapeo usar el valor limpio
    df["distrito_norm"] = df["distrito_norm"].fillna(df["distrito_raw"])
    df["nivel_socioeconomico"] = df["distrito_norm"].map(MAPEO_NSE)
 
    df["direccion_completa"] = df.apply(
        lambda r: construir_direccion(r["direccion"], r["distrito_norm"]), axis=1
    )
 
    # 5. Seleccionar y renombrar columnas finales
    df_out = df[[
        "prop_id", "fuente", "listing_date", "url",
        "precio_pen", "precio_usd", "mantenimiento_soles",
        "direccion_completa", "distrito_norm", "nivel_socioeconomico",
        "area_m2", "num_dorm", "num_banios", "num_estac", "antiguedad",
        "publicado_por", "fecha_publicacion",
    ]].rename(columns={"distrito_norm": "distrito"}).copy()
 
    logger.info(f"  Filas procesadas: {len(df_out)}")
    logger.info(f"  Con precio PEN:   {df_out['precio_pen'].notna().sum()}")
    logger.info(f"  Con precio USD:   {df_out['precio_usd'].notna().sum()}")
    logger.info(f"  Con NSE:          {df_out['nivel_socioeconomico'].notna().sum()}")
 
    # 6. Escribir a Neon
    logger.info("Escribiendo propiedades_procesadas en Neon...")
    with engine.begin() as conn:
        conn.execute(text("TRUNCATE TABLE propiedades_procesadas"))
 
    df_out.to_sql(
        "propiedades_procesadas",
        engine,
        if_exists="append",
        index=False,
        method="multi",
        chunksize=500,
    )
    logger.info(f"✅ {len(df_out)} filas escritas en propiedades_procesadas")
 
 
if __name__ == "__main__":
    main()
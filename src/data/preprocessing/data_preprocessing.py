"""
data_preprocessing.py
=====================
Lee propiedades_procesadas + proximidades desde Neon (JOIN por prop_id),
aplica limpieza, train/eval/test split e imputación,
y escribe el resultado en la tabla dataset.

Uso:
    python src/data/preprocessing/data_preprocessing.py
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

import logging
import pandas as pd
from sklearn.model_selection import train_test_split
from sqlalchemy import text
from service.db_client import get_engine

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


def imputar_con_medianas(cols_a_imputar, medianas, row):
    for col in cols_a_imputar:
        if pd.isna(row[col]):
            if row["distrito"] in medianas.index:
                row[col] = medianas.loc[row["distrito"], col]
    return row


def main():
    engine = get_engine()

    # 1. JOIN propiedades_procesadas + proximidades
    logger.info("Leyendo propiedades_procesadas + proximidades...")
    df = pd.read_sql("""
        SELECT
            p.prop_id,
            p.fuente,
            p.listing_date,
            p.url,
            p.precio_pen,
            p.precio_usd,
            p.mantenimiento_soles,
            p.direccion_completa,
            p.distrito,
            p.nivel_socioeconomico,
            p.area_m2,
            p.num_dorm,
            p.num_banios,
            p.num_estac,
            p.antiguedad,
            p.publicado_por,
            p.fecha_publicacion,
            p.latitud,
            p.longitud,
            pr.num_colegios_aprox,
            pr.num_hospitales_aprox,
            pr.num_tren_est_aprox,
            pr.num_metro_est_aprox,
            pr.num_comisarias_aprox,
            pr.num_delitos_aprox,
            pr.num_malls_aprox
        FROM propiedades_procesadas p
        JOIN proximidades pr USING (prop_id)
        WHERE p.precio_pen IS NOT NULL
    """, engine)
    logger.info(f"  {len(df)} filas después del JOIN")

    # 2. Filtros y limpieza
    logger.info("Aplicando filtros...")
    q_low  = df["precio_pen"].quantile(0.01)
    q_high = df["precio_pen"].quantile(0.95)
    df = df[(df["precio_pen"] >= q_low) & (df["precio_pen"] <= q_high)]

    df = df.drop_duplicates(subset=[
        "latitud", "longitud", "area_m2", "num_dorm",
        "num_banios", "num_estac", "distrito",
        "nivel_socioeconomico", "mantenimiento_soles"
    ])
    df["num_estac"] = df["num_estac"].fillna(0)
    df = df.dropna(subset=["area_m2", "distrito"])
    logger.info(f"  {len(df)} filas tras limpieza")

    # 3. Train / eval / test split
    logger.info("Generando splits...")
    df = df.sample(frac=1, random_state=42).reset_index(drop=True)
    train_data, temp_data = train_test_split(df,        test_size=0.4, random_state=42)
    eval_data,  test_data = train_test_split(temp_data, test_size=0.5, random_state=42)

    train_data = train_data.copy(); train_data["set"] = "train"
    eval_data  = eval_data.copy();  eval_data["set"]  = "eval"
    test_data  = test_data.copy();  test_data["set"]  = "test"

    df = pd.concat([train_data, eval_data, test_data]).reset_index(drop=True)
    logger.info(f"  train: {len(train_data)}  eval: {len(eval_data)}  test: {len(test_data)}")

    # 4. Imputación por medianas de distrito (calculada solo en train)
    cols_impute = ["num_dorm", "num_banios", "antiguedad"]
    medianas    = train_data.groupby("distrito")[cols_impute].median()
    df = df.apply(lambda row: imputar_con_medianas(cols_impute, medianas, row), axis=1)

    # 5. Escribir a Neon
    logger.info("Escribiendo tabla dataset en Neon...")
    with engine.begin() as conn:
        conn.execute(text("TRUNCATE TABLE dataset"))

    df.to_sql("dataset", engine, if_exists="append", index=False, method="multi", chunksize=500)
    logger.info(f"✅ {len(df)} filas escritas en dataset")


if __name__ == "__main__":
    main()
"""
feature_engineering.py
=======================
Lee la tabla dataset desde Neon, genera todas las features
y escribe el resultado en dataset_final.

Uso:
    python src/features/feature_engineering.py
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

import logging
import numpy as np
import pandas as pd
from sklearn.tree import DecisionTreeClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
from sqlalchemy import text
from service.db_client import get_engine

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


DICT_ZONA_APEIM = {
    "puente piedra": "zona 1", "comas": "zona 1", "carabayllo": "zona 1",
    "callao": "zona 1", "bellavista": "zona 1", "la perla": "zona 1",
    "la punta": "zona 1", "carmen de la legua": "zona 1", "ventanilla": "zona 1",
    "independencia": "zona 2", "los olivos": "zona 2", "smp": "zona 2",
    "sjl": "zona 3",
    "lima cercado": "zona 4", "rimac": "zona 4", "brena": "zona 4", "la victoria": "zona 4",
    "ate": "zona 5", "chaclacayo": "zona 5", "lurigancho": "zona 5",
    "santa anita": "zona 5", "san luis": "zona 5", "el agustino": "zona 5",
    "jesus maria": "zona 6", "lince": "zona 6", "pueblo libre": "zona 6",
    "magdalena": "zona 6", "san miguel": "zona 6",
    "miraflores": "zona 7", "san isidro": "zona 7", "san borja": "zona 7",
    "surco": "zona 7", "la molina": "zona 7",
    "surquillo": "zona 8", "barranco": "zona 8", "chorrillos": "zona 8", "sjm": "zona 8",
    "ves": "zona 9", "vmt": "zona 9", "lurin": "zona 9", "pachacamac": "zona 9",
    "punta hermosa": "zona 10", "san bartolo": "zona 10", "cieneguilla": "zona 10",
    "punta negra": "zona 10", "ancon": "zona 10",
    "santa maria del mar": "zona 10", "pucusana": "zona 10",
}

MAP_TIPO_VIVIENDA = {0: "Medio", 1: "Premium", 2: "Economico"}


def imputar_con_medianas_zona(cols_impute, medianas_zona, row):
    for col in cols_impute:
        if pd.isna(row[col]):
            zona = row["zona_apeim"]
            if zona in medianas_zona.index:
                valor = medianas_zona.loc[zona, col]
                if not pd.isna(valor):
                    row[col] = valor
    return row


def main():
    engine = get_engine()

    # 1. Leer dataset
    logger.info("Leyendo dataset desde Neon...")
    df = pd.read_sql("SELECT * FROM dataset", engine)
    logger.info(f"  {len(df)} filas")

    df_processed = df.copy()
    df_train     = df_processed[df_processed["set"] == "train"]

    # 2. Features derivadas
    logger.info("Generando features...")
    df_processed["num_estac"]       = df_processed["num_estac"].fillna(0)
    df_processed["total_ambientes"] = df_processed["num_dorm"] + df_processed["num_banios"]

    df_processed["total_servicios_prox"] = (
        df_processed["num_colegios_aprox"]  +
        df_processed["num_hospitales_aprox"] +
        df_processed["num_tren_est_aprox"]  +
        df_processed["num_metro_est_aprox"] +
        df_processed["num_comisarias_aprox"]
    )
    df_processed["total_transporte_aprox"] = (
        df_processed["num_tren_est_aprox"] + df_processed["num_metro_est_aprox"]
    )
    df_processed["flg_estac"] = (df_processed["num_estac"]          > 0).astype(int)
    df_processed["flg_tren"]  = (df_processed["num_tren_est_aprox"] > 0).astype(int)
    df_processed["flg_metro"] = (df_processed["num_metro_est_aprox"]> 0).astype(int)

    df_processed["precio_por_m2"]       = df_processed["precio_pen"] / df_processed["area_m2"]
    df_processed["costo_total_mensual"]  = df_processed["precio_pen"] + df_processed["mantenimiento_soles"].fillna(0)
    df_processed["score_ubicacion"]      = (
        df_processed["total_servicios_prox"] * 0.6 +
        df_processed["total_transporte_aprox"] * 0.4
    )
    df_processed["categoria_precio"] = pd.cut(
        df_processed["precio_pen"], bins=5,
        labels=["Muy Bajo", "Bajo", "Medio", "Alto", "Muy Alto"]
    )

    # Antigüedad
    if df_processed["antiguedad"].notna().any():
        df_processed["decada_construccion"] = (2025 - df_processed["antiguedad"]) // 10 * 10

    # 3. Zona APEIM
    df_processed["zona_apeim"]     = df_processed["distrito"].map(DICT_ZONA_APEIM)
    df_processed["zona_apeim_cod"] = df_processed["zona_apeim"].map(
        {f"zona {i}": i for i in range(1, 11)}
    )

    # 4. Imputación por zona (solo medianas de train)
    cols_impute    = ["num_dorm", "num_banios", "antiguedad"]
    medianas_zona  = df_train.assign(
        zona_apeim=lambda x: x["distrito"].map(DICT_ZONA_APEIM)
    ).groupby("zona_apeim")[cols_impute].median()

    df_processed = df_processed.apply(
        lambda row: imputar_con_medianas_zona(cols_impute, medianas_zona, row), axis=1
    )

    # 5. Variables categóricas codificadas
    df_processed["tamano"] = pd.cut(
        df_processed["area_m2"],
        bins=[0, 50, 100, float("inf")],
        labels=["pequeno", "mediano", "grande"]
    )
    df_processed["tamano_cod"] = df_processed["tamano"].map(
        {"pequeno": 1, "mediano": 2, "grande": 3}
    ).astype(float)

    if df_processed["antiguedad"].notna().any():
        df_processed["antiguedad_categoria"] = pd.cut(
            df_processed["antiguedad"],
            bins=[-1, 5, 20, float("inf")],
            labels=["nuevo", "seminuevo", "antiguo"]
        )
        df_processed["antiguedad_cod"] = df_processed["antiguedad_categoria"].map(
            {"nuevo": 1, "seminuevo": 2, "antiguo": 3}
        ).astype(float)

    df_processed["nivel_socioeconomico_cod"] = df_processed["nivel_socioeconomico"].map(
        {"A": 1, "B": 2, "C": 3, "D": 4}
    ).astype(float)

    # 6. Categoría de crímenes con DecisionTree
    # zona_apeim_cod calculada sobre df_train (que es slice del original sin esa col)
    df_train_tree = df_train.copy()
    df_train_tree["zona_apeim_cod"] = df_train_tree["distrito"].map(DICT_ZONA_APEIM).map(
        {f"zona {i}": i for i in range(1, 11)}
    )
    df_train_tree = df_train_tree[["num_delitos_aprox", "zona_apeim_cod"]].dropna()
    X = df_train_tree[["num_delitos_aprox"]]
    y = df_train_tree["zona_apeim_cod"]

    tree = DecisionTreeClassifier(max_leaf_nodes=4, random_state=42)
    tree.fit(X, y)
    thresholds = np.sort(tree.tree_.threshold[tree.tree_.threshold != -2])
    bins   = [-1] + list(thresholds) + [float("inf")]
    labels = [f"nivel_{i+1}" for i in range(len(bins) - 1)]

    df_processed["categoria_crimenes"]     = pd.cut(df_processed["num_delitos_aprox"], bins=bins, labels=labels)
    df_processed["categoria_crimenes_cod"] = df_processed["categoria_crimenes"].cat.codes + 1

    # 7. KMeans — tipo de vivienda
    cols_cluster = [
        "area_m2", "num_dorm", "num_banios", "num_estac",
        "categoria_crimenes_cod", "zona_apeim_cod", "tamano_cod"
    ]
    if "antiguedad_cod" in df_processed.columns:
        cols_cluster.append("antiguedad_cod")

    X_cluster = df_processed[cols_cluster].fillna(0)
    scaler    = StandardScaler()
    X_scaled  = scaler.fit_transform(X_cluster)
    kmeans    = KMeans(n_clusters=3, random_state=42)

    df_processed["tipo_vivienda_cod"] = kmeans.fit_predict(X_scaled)
    df_processed["tipo_vivienda"]     = df_processed["tipo_vivienda_cod"].map(MAP_TIPO_VIVIENDA)

    # Resumen clusters
    cluster_summary = df_processed.groupby("tipo_vivienda_cod")[cols_cluster + ["precio_pen"]].median().round(2)
    logger.info(f"\nMedianas por cluster:\n{cluster_summary}")
    logger.info(f"\nCantidad por cluster:\n{df_processed['tipo_vivienda_cod'].value_counts()}")

    # 8. Escribir dataset_final a Neon
    # Convertir categóricas a string para que sqlalchemy las acepte
    for col in df_processed.select_dtypes(include="category").columns:
        df_processed[col] = df_processed[col].astype(str)

    logger.info("Escribiendo dataset_final en Neon...")
    with engine.begin() as conn:
        conn.execute(text("TRUNCATE TABLE dataset_final"))

    df_processed.to_sql(
        "dataset_final", engine,
        if_exists="append", index=False,
        method="multi", chunksize=500,
    )
    logger.info(f"✅ {len(df_processed)} filas escritas en dataset_final")


if __name__ == "__main__":
    main()
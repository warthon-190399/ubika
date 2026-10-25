"""
Paso 3 del pipeline: entorno de cada inmueble con coordenadas → tabla entorno.

Para cada categoría de puntos de interés: cuántos hay a menos de `radio_m` y la distancia
en línea recta al más cercano. Para delitos: denuncias de patrimonio y violencia de los
últimos 12 meses a menos de `radio_m`, ponderadas por distrito (v_delitos_distrito_12m.peso)
para corregir que cada distrito ubique un porcentaje distinto de sus denuncias.
"""
from __future__ import annotations

import logging

import numpy as np
import pandas as pd
from sklearn.neighbors import BallTree

from ubika.config import cfg
from ubika.db import read_df, reemplazar

log = logging.getLogger(__name__)

RADIO_TIERRA_M = 6_371_000
CATEGORIAS_DELITO = ("patrimonio", "violencia")

# columna de entorno → categorías de puntos_interes
GRUPOS = {
    "colegios": ("colegio",),
    "salud": ("salud",),
    "comisarias": ("comisaria",),
    "transporte": ("metro", "metropolitano", "tren"),
    "malls": ("mall",),
    "parques": ("parque",),
    "corredores": ("corredor",),          # paraderos de los Corredores Complementarios (sql/14)
}


def _rad(df: pd.DataFrame) -> np.ndarray:
    return np.deg2rad(df[["latitud", "longitud"]].to_numpy(dtype=float))


def conteo_y_distancia(props: pd.DataFrame, puntos: pd.DataFrame, radio_m: float,
                       pesos: np.ndarray | None = None) -> tuple[np.ndarray, np.ndarray | None]:
    """(cantidad —o suma de pesos— dentro del radio, distancia al más cercano en metros)."""
    n = len(props)
    if puntos.empty:
        return np.zeros(n), None
    arbol = BallTree(_rad(puntos), metric="haversine")
    x = _rad(props)
    idx = arbol.query_radius(x, r=radio_m / RADIO_TIERRA_M)
    if pesos is None:
        conteo = np.array([len(i) for i in idx], dtype=float)
    else:
        conteo = np.array([pesos[i].sum() for i in idx], dtype=float)
    dist, _ = arbol.query(x, k=1)
    return conteo, (dist[:, 0] * RADIO_TIERRA_M)


def calcular(props: pd.DataFrame, pois: pd.DataFrame, inpe: pd.DataFrame, delitos: pd.DataFrame,
             radio_m: int) -> pd.DataFrame:
    out = pd.DataFrame({"prop_id": props["prop_id"], "radio_m": radio_m})
    for col, cats in GRUPOS.items():
        conteo, dist = conteo_y_distancia(props, pois[pois["categoria"].isin(cats)], radio_m)
        out[f"n_{col}"] = conteo.astype(int)
        nombre_dist = {"colegios": "colegio", "comisarias": "comisaria", "malls": "mall",
                       "parques": "parque", "corredores": "corredor"}.get(col, col)
        out[f"dist_{nombre_dist}_m"] = None if dist is None else np.round(dist).astype(int)
    out["n_inpe"] = conteo_y_distancia(props, inpe, radio_m)[0].astype(int)
    pesos = delitos["peso"].fillna(1.0).to_numpy(dtype=float) if not delitos.empty else None
    out["n_delitos_12m"] = np.round(conteo_y_distancia(props, delitos, radio_m, pesos)[0], 1)
    return out


def correr(c) -> dict:
    radio = cfg()["entorno"]["radio_m"]
    props = read_df("SELECT prop_id::text AS prop_id, latitud, longitud FROM propiedades WHERE latitud IS NOT NULL")
    c.leidas = len(props)
    if props.empty:
        log.warning("  No hay inmuebles con coordenadas.")
        return {"entorno": 0}
    pois = read_df("SELECT categoria, latitud, longitud FROM puntos_interes")
    inpe = read_df("SELECT latitud, longitud FROM inpe_domicilios")
    delitos = read_df("""
        WITH fin AS (SELECT MAX(make_date(anio, mes, 1)) AS f FROM delitos_distrito_mes)
        SELECT p.latitud, p.longitud, COALESCE(w.peso, 1) AS peso
        FROM delitos_puntos p
        CROSS JOIN fin
        LEFT JOIN v_delitos_distrito_12m w ON w.distrito = p.distrito AND w.categoria = p.categoria
        WHERE p.categoria IN :cats
          AND make_date(p.anio, p.mes, 1) > fin.f - INTERVAL '12 months'
    """.replace(":cats", "('" + "','".join(CATEGORIAS_DELITO) + "')"))
    log.info("  %d inmuebles · %d puntos de interés · %d denuncias (12 meses, ponderadas)",
             len(props), len(pois), len(delitos))

    filas = calcular(props, pois, inpe, delitos, radio)
    filas = filas.astype(object).where(filas.notna(), None)
    # Solo las columnas que existen: sin sql/14, entorno todavía no tiene las de corredores
    existentes = set(read_df("SELECT column_name FROM information_schema.columns WHERE table_name = 'entorno'")["column_name"])
    faltan = [col for col in filas.columns if col not in existentes]
    if faltan:
        log.warning("  entorno no tiene %s (corre sql/14_corredores.sql); se omiten", ", ".join(faltan))
        filas = filas.drop(columns=faltan)
    reemplazar("entorno", "TRUE", {}, filas)          # se recalcula completo en cada corrida
    c.escritas = len(filas)
    log.info("  Entorno calculado para %d inmuebles (radio %d m)", len(filas), radio)
    return {"entorno": len(filas)}

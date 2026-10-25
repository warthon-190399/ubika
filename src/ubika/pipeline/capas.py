"""
Etapa del pipeline: capas del mapa para toda la ciudad → tabla capas_grilla.

Una grilla hexagonal de puntos cada ~350 m cubre la zona urbana de Lima y Callao
(celdas con al menos 5 puntos de interés o denuncias a menos de 700 m; así los cerros y
zonas vacías no aparecen como "muy seguras" solo porque nadie denuncia ahí). Para cada celda:

- seguridad:  denuncias de patrimonio y violencia de los últimos 12 meses a menos de `radio_m`
              (500 m, el mismo radio del entorno de cada inmueble), ponderadas por distrito.
              Índice alto = menos denuncias.
- transporte: metros a la estación de metro, tren o Metropolitano más cercana. Índice alto = más cerca.
- servicios:  colegios, salud, comisarías y malls a menos de `radio_m`. Índice alto = más servicios.

Si ya se cargaron los paraderos de corredores (sql/14, osm --solo corredores) se suma:

- corredor: metros al paradero de Corredor Complementario más cercano. Índice alto = más cerca.

Si ya se cargó OpenStreetMap (ubika.referencias.osm) se suman tres capas de calidad de vida:

- verde:  m² de parque con centro a menos de `radio_m`. Índice alto = más parque.
- barrio: mercados, súper, farmacias, restaurantes, gimnasios y bancos a menos de `radio_m`.
- ruido:  nivel de ruido de tráfico ESTIMADO en dB (no es una medición; ver `nivel_ruido`).
          Índice alto = más tranquilo.

El índice es el percentil de la celda dentro de la ciudad (0 a 1), así la escala de colores del mapa
usa toda la paleta y se lee igual en cualquier capa. Como los radios son los mismos que en la tabla
entorno, la app puede ubicar cualquier inmueble frente a la ciudad comparando sus valores con la grilla.
"""
from __future__ import annotations

import logging

import numpy as np
import pandas as pd
from sklearn.neighbors import BallTree

from ubika.config import cfg
from ubika.db import read_df, reemplazar
from ubika.pipeline.entorno import CATEGORIAS_DELITO, RADIO_TIERRA_M

log = logging.getLogger(__name__)

KM_LAT, KM_LON = 110.6, 108.9          # km por grado cerca de los 12°S
PASO_KM = 0.35
URBANO_KM = 0.7
URBANO_MIN = 5          # puntos de interés + denuncias a menos de URBANO_KM para considerar urbana una celda
BASE_URBANA = ["colegio", "salud", "comisaria", "metro", "metropolitano", "tren", "mall"]   # para la máscara urbana
BARRIO = ["supermercado", "mercado", "farmacia", "restaurante", "gimnasio", "banco"]

# Modelo simple de ruido de tráfico (sin mediciones abiertas en Lima):
# nivel a 10 m de la vía, que cae 3 dB cada vez que se duplica la distancia (fuente lineal)
# más una atenuación por edificios de 0.015 dB/m (hasta 15 dB). El aeropuerto se trata como
# fuente puntual (6 dB por duplicación) con 80 dB a 1 km. Se suman en energía con un fondo de 50 dB.
# Referencia: el OEFA midió 75–82 dB en grandes cruces de Lima (2011); la OMS recomienda < 53 dB.
NIVEL_10M = {"autopista": 78.0, "principal": 75.0, "secundaria": 71.0}
FONDO_DB = 50.0


def nivel_ruido(dist_m: dict[str, np.ndarray]) -> np.ndarray:
    """dB estimados a partir de la distancia (m) a la fuente más cercana de cada tipo."""
    energia = None
    for tipo, d in dist_m.items():
        d = np.maximum(d, 10.0)
        if tipo == "aeropuerto":
            nivel = 80.0 - 20 * np.log10(np.maximum(d, 200.0) / 1000)
        else:
            nivel = NIVEL_10M[tipo] - 10 * np.log10(d / 10) - np.minimum(15.0, 0.015 * (d - 10))
        e = 10 ** (nivel / 10)
        energia = e if energia is None else energia + e
    fondo = 10 ** (FONDO_DB / 10)
    return 10 * np.log10(fondo + (energia if energia is not None else 0))


def grilla(caja: dict) -> pd.DataFrame:
    d_lat = PASO_KM * np.sqrt(3) / 2 / KM_LAT
    d_lon = PASO_KM / KM_LON
    lats = np.arange(caja["lat_min"], caja["lat_max"], d_lat)
    filas = []
    for i, la in enumerate(lats):
        desplaz = d_lon / 2 if i % 2 else 0.0
        for lo in np.arange(caja["lon_min"] + desplaz, caja["lon_max"], d_lon):
            filas.append((la, lo))
    g = pd.DataFrame(filas, columns=["latitud", "longitud"])
    g["celda"] = np.arange(len(g))
    return g


def _rad(df):
    return np.deg2rad(df[["latitud", "longitud"]].to_numpy(dtype=float))


def percentil(v: np.ndarray, mayor_es_mejor: bool) -> np.ndarray:
    rangos = pd.Series(v).rank(method="average", pct=True).to_numpy()
    return rangos if mayor_es_mejor else 1 - rangos + 1 / len(v)


def calcular(celdas: pd.DataFrame, pois: pd.DataFrame, delitos: pd.DataFrame, radio_m: float = 500,
             ruido: pd.DataFrame | None = None) -> pd.DataFrame:
    # Zona urbana: celdas con actividad a menos de URBANO_KM (con las fuentes de siempre, para que no cambie la grilla)
    base = pois[pois["categoria"].isin(BASE_URBANA)]
    referencia = pd.concat([base[["latitud", "longitud"]], delitos[["latitud", "longitud"]]])
    arbol_ref = BallTree(_rad(referencia), metric="haversine")
    cerca = arbol_ref.query_radius(_rad(celdas), r=URBANO_KM * 1000 / RADIO_TIERRA_M, count_only=True)
    celdas = celdas[cerca >= URBANO_MIN].reset_index(drop=True)
    x = _rad(celdas)

    salida = []
    # seguridad
    arbol = BallTree(_rad(delitos), metric="haversine")
    idx = arbol.query_radius(x, r=radio_m / RADIO_TIERRA_M)
    pesos = delitos["peso"].to_numpy(dtype=float)
    v = np.array([pesos[i].sum() for i in idx])
    salida.append(celdas.assign(capa="seguridad", valor=v, indice=percentil(v, mayor_es_mejor=False)))
    # transporte
    est = pois[pois["categoria"].isin(["metro", "metropolitano", "tren"])]
    dist, _ = BallTree(_rad(est), metric="haversine").query(x, k=1)
    v = dist[:, 0] * RADIO_TIERRA_M
    salida.append(celdas.assign(capa="transporte", valor=v, indice=percentil(v, mayor_es_mejor=False)))
    # corredor: metros al paradero de Corredor Complementario más cercano (si ya se cargaron, sql/14)
    corr = pois[pois["categoria"] == "corredor"]
    if len(corr):
        dist, _ = BallTree(_rad(corr), metric="haversine").query(x, k=1)
        v = dist[:, 0] * RADIO_TIERRA_M
        salida.append(celdas.assign(capa="corredor", valor=v, indice=percentil(v, mayor_es_mejor=False)))
    # servicios
    srv = pois[pois["categoria"].isin(["colegio", "salud", "comisaria", "mall"])]
    v = BallTree(_rad(srv), metric="haversine").query_radius(x, r=radio_m / RADIO_TIERRA_M, count_only=True).astype(float)
    salida.append(celdas.assign(capa="servicios", valor=v, indice=percentil(v, mayor_es_mejor=True)))

    r = radio_m / RADIO_TIERRA_M
    # verde: m² de parque cuyo centro está a menos de radio_m
    parques = pois[pois["categoria"] == "parque"]
    if len(parques) and "area_m2" in parques:
        areas = parques["area_m2"].fillna(0).to_numpy(dtype=float)
        idx = BallTree(_rad(parques), metric="haversine").query_radius(x, r=r)
        v = np.array([areas[i].sum() for i in idx])
        salida.append(celdas.assign(capa="verde", valor=v, indice=percentil(v, mayor_es_mejor=True)))
    # barrio: comercio de todos los días a menos de radio_m
    barrio = pois[pois["categoria"].isin(BARRIO)]
    if len(barrio):
        v = BallTree(_rad(barrio), metric="haversine").query_radius(x, r=r, count_only=True).astype(float)
        salida.append(celdas.assign(capa="barrio", valor=v, indice=percentil(v, mayor_es_mejor=True)))
    # ruido: dB estimados por distancia a vías grandes y al aeropuerto
    if ruido is not None and len(ruido):
        dist = {}
        for tipo, g in ruido.groupby("tipo"):
            d, _ = BallTree(_rad(g), metric="haversine").query(x, k=1)
            dist[tipo] = d[:, 0] * RADIO_TIERRA_M
        v = nivel_ruido(dist)
        salida.append(celdas.assign(capa="ruido", valor=v, indice=percentil(v, mayor_es_mejor=False)))

    out = pd.concat(salida, ignore_index=True)
    out["indice"] = out["indice"].clip(0, 1).round(4)
    out["valor"] = out["valor"].round(2)
    return out[["capa", "celda", "latitud", "longitud", "valor", "indice"]]


def correr(c) -> dict:
    pois = read_df("SELECT categoria, latitud, longitud, (atributos->>'area_m2')::float AS area_m2 FROM puntos_interes")
    try:
        ruido = read_df("SELECT tipo, latitud, longitud FROM ruido_fuentes")
    except Exception:            # sql/09 todavía no se corrió
        ruido = None
    delitos = read_df("""
        WITH fin AS (SELECT MAX(make_date(anio, mes, 1)) AS f FROM delitos_distrito_mes)
        SELECT p.latitud, p.longitud, COALESCE(w.peso, 1) AS peso
        FROM delitos_puntos p
        CROSS JOIN fin
        LEFT JOIN v_delitos_distrito_12m w ON w.distrito = p.distrito AND w.categoria = p.categoria
        WHERE p.categoria IN ('""" + "','".join(CATEGORIAS_DELITO) + """')
          AND make_date(p.anio, p.mes, 1) > fin.f - INTERVAL '12 months'
    """)
    if pois.empty or delitos.empty:
        raise RuntimeError("Faltan puntos de interés o denuncias: corre ubika.referencias.puntos y ubika.referencias.sidpol")
    capas = calcular(grilla(cfg()["geocoding"]["caja"]), pois, delitos, cfg()["entorno"]["radio_m"], ruido)
    n = reemplazar("capas_grilla", "TRUE", {}, capas)
    c.leidas, c.escritas = len(delitos) + len(pois), n
    nombres = sorted(capas["capa"].unique())
    log.info("  Capas listas: %d celdas urbanas × %d capas (%s)", n // len(nombres), len(nombres), ", ".join(nombres))
    return {"celdas": n // len(nombres), "capas": nombres}

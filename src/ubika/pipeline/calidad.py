"""
Etapa del pipeline: score de calidad de vida (0–10) → calidad_vida_celda, calidad_vida_inmueble y
calidad_vida_distrito. Metodología completa en docs/metodologia_calidad_vida.md.

Siete componentes, cada uno convertido en su POSICIÓN frente a todas las celdas de Lima y Callao
(0 = peor, 1 = mejor; empates a la mitad):

  seguridad   ½ denuncias a 500 m por 10 mil habitantes + ½ homicidios del distrito por 100 mil
  longevidad  edad promedio al morir por causas naturales en el distrito (SINADEF)
  transporte  metros a la estación de metro, tren o Metropolitano más cercana   (menos = mejor)
  servicios   colegios + salud + comisarías + malls a 500 m
  verde       m² de parque a 500 m por habitante
  barrio      comercio de todos los días a 500 m
  ruido       dB de tráfico estimados                                          (menos = mejor)

score = 10 × Σ peso × posición / Σ pesos con dato (los pesos están en config.yaml, calidad_vida).

«Por habitante»: la población del distrito (censo 2017) se reparte por igual entre sus celdas y lo
que hay a 500 m de una celda se divide entre la gente de ese círculo (≈ CELDAS_500M celdas).
Es la misma fórmula que usaba la app (ubika-app/src/lib/ciudad.js), ahora con longevidad y guardada.

Un inmueble usa sus propios conteos de la tabla entorno (denuncias, transporte, servicios), la celda
más cercana para verde, barrio y ruido, y su distrito para homicidios y longevidad.
"""
from __future__ import annotations

import logging
import math

import numpy as np
import pandas as pd

from ubika.config import cfg
from ubika.db import read_df, reemplazar
from ubika.pipeline import limites as lim

log = logging.getLogger(__name__)

COMPONENTES = ("seguridad", "longevidad", "transporte", "servicios", "verde", "barrio", "ruido")
# Celdas de la grilla dentro de un círculo de 500 m: área del círculo / área de un hexágono de 350 m
CELDAS_500M = (math.pi * 0.5 ** 2) / ((math.sqrt(3) / 2) * 0.35 ** 2)
MAX_M_A_CELDA = 400            # un inmueble a más de esto de toda celda urbana no toma verde/barrio/ruido
CAPAS = ("seguridad", "transporte", "servicios", "verde", "barrio", "ruido")


def config() -> dict:
    c = cfg()["calidad_vida"]
    pesos = {k: float(c["pesos"][k]) for k in COMPONENTES}
    if abs(sum(pesos.values()) - 1) > 1e-6:
        raise ValueError(f"calidad_vida.pesos debe sumar 1 (suma {sum(pesos.values()):.3f})")
    return {"version": int(c["version"]), "pesos": pesos, "peso_homicidios": float(c["peso_homicidios"])}


# ── Funciones puras (probadas en tests/test_calidad.py) ──────

def posiciones(referencia: np.ndarray, valores: np.ndarray, menor_es_mejor: bool) -> np.ndarray:
    """
    Posición 0–1 de cada valor dentro de `referencia` (1 = mejor que todas), con empates a la mitad.
    Igual que rango() de ciudad.js. NaN en valores → NaN; NaN en referencia se ignoran.
    """
    ref = np.sort(referencia[~np.isnan(referencia)])
    v = np.asarray(valores, dtype=float)
    out = np.full(v.shape, np.nan)
    if not len(ref):
        return out
    ok = ~np.isnan(v)
    menores = np.searchsorted(ref, v[ok], side="left")
    iguales = np.searchsorted(ref, v[ok], side="right") - menores
    peores = (len(ref) - menores - iguales) if menor_es_mejor else menores
    out[ok] = (peores + iguales / 2) / len(ref)
    return out


def combinar_seguridad(pos_denuncias: np.ndarray, pos_homicidios: np.ndarray, peso_homicidios: float) -> np.ndarray:
    """Promedio ponderado; si falta uno, cuenta el otro (como seguridadIx en scoring.js)."""
    d, h = np.asarray(pos_denuncias, float), np.asarray(pos_homicidios, float)
    out = (1 - peso_homicidios) * d + peso_homicidios * h
    out = np.where(np.isnan(h), d, out)
    return np.where(np.isnan(d), h, out)


def score(pos: pd.DataFrame, pesos: dict[str, float]) -> tuple[np.ndarray, np.ndarray]:
    """(score 0–10, n componentes con dato). Los pesos de los componentes sin dato se reparten."""
    m = pos[[f"pos_{k}" for k in COMPONENTES]].to_numpy(float)
    w = np.array([pesos[k] for k in COMPONENTES])
    con = ~np.isnan(m)
    suma_w = (con * w).sum(axis=1)
    s = (np.nan_to_num(m) * w).sum(axis=1)
    with np.errstate(invalid="ignore", divide="ignore"):
        out = np.where(suma_w > 0, 10 * s / suma_w, np.nan)
    return out, con.sum(axis=1)


def distritos_de(lat: np.ndarray, lon: np.ndarray, limites: list[tuple[str, list]]) -> np.ndarray:
    """Distrito de cada punto (o None), vectorizado: caja de cada distrito y luego par-impar por polígono."""
    lat, lon = np.asarray(lat, float), np.asarray(lon, float)
    out = np.full(len(lat), None, dtype=object)
    for distrito, polys in limites:
        xs = np.concatenate([np.asarray(a)[:, 0] for p in polys for a in p])
        ys = np.concatenate([np.asarray(a)[:, 1] for p in polys for a in p])
        cand = np.where((out == None) & (lon >= xs.min()) & (lon <= xs.max()) & (lat >= ys.min()) & (lat <= ys.max()))[0]  # noqa: E711
        if not len(cand):
            continue
        x, y = lon[cand], lat[cand]
        dentro = np.zeros(len(cand), dtype=bool)
        for poly in polys:
            for anillo in poly:                       # exterior y huecos: la regla par-impar los resuelve juntos
                a = np.asarray(anillo, float)
                xi, yi, xj, yj = a[:, 0], a[:, 1], np.roll(a[:, 0], 1), np.roll(a[:, 1], 1)
                for k in range(len(a)):
                    cruza = (yi[k] > y) != (yj[k] > y)
                    if cruza.any():
                        xc = (xj[k] - xi[k]) * (y - yi[k]) / ((yj[k] - yi[k]) or 1e-12) + xi[k]
                        dentro ^= cruza & (x < xc)
        out[cand[dentro]] = distrito
    return out


def celdas(grilla: pd.DataFrame, distrito: np.ndarray, poblacion: dict, homicidios: dict, longevidad: dict,
           conf: dict) -> pd.DataFrame:
    """
    grilla: una fila por celda con celda, latitud, longitud y una columna por capa (valor de capas_grilla).
    Devuelve valores, posiciones y score de cada celda.
    """
    g = grilla.reset_index(drop=True).copy()
    g["distrito"] = distrito
    n_celdas = g["distrito"].value_counts()
    pop_celda = g["distrito"].map(lambda d: poblacion.get(d) / n_celdas[d] if d in n_celdas and poblacion.get(d) else np.nan)
    gente_500m = pop_celda * CELDAS_500M
    col = lambda c: g[c].astype(float) if c in g else pd.Series(np.nan, index=g.index)
    v = pd.DataFrame({
        "celda": g["celda"].astype(int), "latitud": g["latitud"], "longitud": g["longitud"], "distrito": g["distrito"],
        "val_denuncias_10k": 1e4 * col("seguridad") / gente_500m,
        "val_homicidios_100k": g["distrito"].map(homicidios).astype(float),
        "val_edad_al_morir": g["distrito"].map(longevidad).astype(float),
        "val_transporte_m": col("transporte"),
        "val_servicios": col("servicios"),
        "val_verde_m2_hab": col("verde") / gente_500m,
        "val_barrio": col("barrio"),
        "val_ruido_db": col("ruido"),
    })
    return _puntuar(v, v, conf)


# columna de valor → (componente, menos es mejor)
VALORES = {
    "val_denuncias_10k": ("denuncias", True), "val_homicidios_100k": ("homicidios", True),
    "val_edad_al_morir": ("longevidad", False), "val_transporte_m": ("transporte", True),
    "val_servicios": ("servicios", False), "val_verde_m2_hab": ("verde", False),
    "val_barrio": ("barrio", False), "val_ruido_db": ("ruido", True),
}


def _puntuar(v: pd.DataFrame, ref: pd.DataFrame, conf: dict) -> pd.DataFrame:
    """Posiciones de `v` frente a la distribución de las celdas `ref`, seguridad combinada y score."""
    out = v.copy()
    for c, (k, menor) in VALORES.items():
        out[f"pos_{k}"] = posiciones(ref[c].to_numpy(float), out[c].to_numpy(float), menor)
    out["pos_seguridad"] = combinar_seguridad(out["pos_denuncias"], out["pos_homicidios"], conf["peso_homicidios"])
    out["score"], out["n_componentes"] = score(out, conf["pesos"])
    out["version"] = conf["version"]
    return out


def inmuebles(props: pd.DataFrame, cel: pd.DataFrame, poblacion: dict, homicidios: dict, longevidad: dict,
              conf: dict) -> pd.DataFrame:
    """Score de cada inmueble con sus conteos propios y la celda más cercana, frente a las celdas de Lima."""
    n_celdas = cel["distrito"].value_counts()
    pop_celda = props["distrito"].map(lambda d: poblacion.get(d) / n_celdas[d] if d in n_celdas and poblacion.get(d) else np.nan)
    # Celda más cercana (plano local; ~110 km por grado)
    k = math.cos(math.radians(-12.05))
    cy, cx = cel["latitud"].to_numpy(), cel["longitud"].to_numpy() * k
    idx = np.full(len(props), -1)
    for i, (la, lo) in enumerate(zip(props["latitud"].to_numpy(float), props["longitud"].to_numpy(float) * k)):
        d2 = (cy - la) ** 2 + (cx - lo) ** 2
        j = int(np.argmin(d2))
        if math.sqrt(d2[j]) * 111_320 <= MAX_M_A_CELDA:
            idx[i] = j
    de_celda = lambda c: np.where(idx >= 0, cel[c].to_numpy(float)[np.maximum(idx, 0)], np.nan)
    num = lambda c: pd.to_numeric(props[c], errors="coerce").astype(float)
    servicios = sum(num(c).fillna(0) for c in ("n_colegios", "n_salud", "n_comisarias", "n_malls"))
    v = pd.DataFrame({
        "prop_id": props["prop_id"], "distrito": props["distrito"],
        "celda": np.where(idx >= 0, cel["celda"].to_numpy()[np.maximum(idx, 0)], -1),
        "val_denuncias_10k": (1e4 * num("n_delitos_12m") / (pop_celda * CELDAS_500M)).to_numpy(),
        "val_homicidios_100k": props["distrito"].map(homicidios).astype(float).to_numpy(),
        "val_edad_al_morir": props["distrito"].map(longevidad).astype(float).to_numpy(),
        "val_transporte_m": num("dist_transporte_m").to_numpy(),
        "val_servicios": servicios.to_numpy(),
        "val_verde_m2_hab": de_celda("val_verde_m2_hab"),
        "val_barrio": de_celda("val_barrio"),
        "val_ruido_db": de_celda("val_ruido_db"),
    })
    v["celda"] = v["celda"].astype("Int64").where(v["celda"] >= 0)
    out = _puntuar(v, cel, conf)
    out["pos_score"] = posiciones(cel["score"].to_numpy(float), out["score"].to_numpy(float), False)
    return out


def resumen_distritos(cel: pd.DataFrame, version: int) -> pd.DataFrame:
    """Mediana de las celdas de cada distrito (score y posiciones), cuartiles del score y puesto."""
    g = cel.dropna(subset=["distrito"]).groupby("distrito")
    out = g["score"].agg(n_celdas="size", score="median",
                         score_p25=lambda s: s.quantile(0.25), score_p75=lambda s: s.quantile(0.75))
    for k in COMPONENTES:
        out[f"pos_{k}"] = g[f"pos_{k}"].median()
    out = out.reset_index()
    out["puesto"] = out["score"].rank(ascending=False, method="min").astype("Int64")
    out["version"] = version
    return out


# ── Etapa ────────────────────────────────────────────────────

def _vista(sql: str, columna: str) -> dict:
    try:
        df = read_df(sql)
    except Exception as exc:                                   # la vista puede no existir todavía
        log.warning("  %s: sin datos (%s); el componente queda sin dato", columna, type(exc).__name__)
        return {}
    return dict(zip(df["distrito"], df[columna].astype(float)))


def correr(c) -> dict:
    conf = config()
    g = read_df(f"""SELECT capa, celda, latitud, longitud, valor FROM capas_grilla
                    WHERE capa IN ('{"','".join(CAPAS)}')""")
    if g.empty:
        raise RuntimeError("capas_grilla está vacía: corre antes la etapa capas")
    grilla = (g.pivot_table(index=["celda"], columns="capa", values="valor", aggfunc="first")
              .join(g.groupby("celda")[["latitud", "longitud"]].first()).reset_index())
    poblacion = dict(read_df("SELECT distrito, poblacion FROM distritos WHERE poblacion IS NOT NULL").itertuples(index=False))
    homicidios = _vista("SELECT distrito, tasa_homicidios_100k FROM v_mortalidad_distrito_reciente", "tasa_homicidios_100k")
    longevidad = _vista("SELECT distrito, edad_promedio_natural FROM v_longevidad_distrito", "edad_promedio_natural")

    limites = lim.cargar(cfg()["limpieza"]["limites"])
    dist = distritos_de(grilla["latitud"].to_numpy(), grilla["longitud"].to_numpy(), limites)
    cel = celdas(grilla, dist, poblacion, homicidios, longevidad, conf)
    log.info("  %d celdas · %d en un distrito · score mediano %.1f", len(cel), cel["distrito"].notna().sum(), cel["score"].median())

    props = read_df("""
        SELECT p.prop_id::text AS prop_id, p.distrito, p.latitud, p.longitud, e.n_delitos_12m, e.dist_transporte_m,
               e.n_colegios, e.n_salud, e.n_comisarias, e.n_malls
        FROM propiedades p JOIN entorno e USING (prop_id)
        WHERE p.latitud IS NOT NULL""")
    inm = inmuebles(props, cel, poblacion, homicidios, longevidad, conf)
    dis = resumen_distritos(cel, conf["version"])

    columnas = lambda tabla: [col for col in read_df(
        "SELECT column_name FROM information_schema.columns WHERE table_name = :t", {"t": tabla})["column_name"]
        if col != "calculado_at"]
    para = lambda df, tabla: df[[col for col in columnas(tabla) if col in df]].replace({np.nan: None})
    escritas = reemplazar("calidad_vida_celda", "TRUE", {}, para(cel, "calidad_vida_celda"))
    escritas += reemplazar("calidad_vida_inmueble", "TRUE", {}, para(inm, "calidad_vida_inmueble"))
    escritas += reemplazar("calidad_vida_distrito", "TRUE", {}, para(dis, "calidad_vida_distrito"))
    c.leidas, c.escritas = len(cel) + len(props), escritas
    mejores = dis.sort_values("score", ascending=False)
    log.info("  %d inmuebles · %d distritos · versión %d · mejor %s (%.1f), peor %s (%.1f)",
             len(inm), len(dis), conf["version"], mejores["distrito"].iat[0], mejores["score"].iat[0],
             mejores["distrito"].iat[-1], mejores["score"].iat[-1])
    return {"celdas": len(cel), "inmuebles": len(inm), "distritos": len(dis)}

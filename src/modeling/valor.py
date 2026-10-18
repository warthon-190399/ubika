"""
Modelo de valor por operación (alquiler o venta), entrenado con los datos de Neon.

Lee propiedades + entorno + distritos, arma las variables y compara varios métodos con
validación cruzada repetida (5 partes × 3 repeticiones), con las mismas particiones para todos:

- mediana_distrito : precio por m² mediano del distrito × área (la referencia más simple)
- comparables      : el mismo método que la pestaña Evaluador de la app (ubika-app/src/lib/evaluador.js)
- ridge            : regresión lineal regularizada
- random_forest    : bosque aleatorio
- hist_gb          : gradient boosting de scikit-learn (acepta nulos, como la antigüedad)

Los modelos predicen log(precio por m²); el precio es exp(predicción) × área.
Métricas sobre el precio: MAPE, error mediano (MdAPE), % a menos de 20 %, R² y RMSE en soles.

Guarda en models/valor/ (no se versiona):
- {operacion}_metricas.json : métricas de todos los métodos, datos usados y cuál ganó
- {operacion}_modelo.joblib : el mejor modelo de aprendizaje automático, entrenado con todos los datos
y anota la corrida en la tabla corridas (salvo --sin-registro). Solo lee datos de Neon: no cambia tablas.

Uso (desde la raíz del repo, con el entorno activado):
    python -m modeling.valor                       # alquiler y venta
    python -m modeling.valor --operacion venta
    python -m modeling.valor --sin-registro        # prueba: no escribe en corridas
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import logging
from pathlib import Path
from typing import Callable

import joblib
import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.ensemble import HistGradientBoostingRegressor, RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.linear_model import Ridge
from sklearn.model_selection import RepeatedKFold
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from ubika.config import ROOT
from ubika.db import corrida, read_df

log = logging.getLogger(__name__)

SALIDA = ROOT / "models" / "valor"
MINIMO = 30            # con menos avisos no se entrena
POCOS = 500            # con menos, las métricas varían mucho entre corridas
SEMILLA = 42

CONSULTA = """
SELECT p.prop_id, p.operacion, p.precio_pen, p.area_m2, p.num_dorm, p.num_banios, p.num_estac,
       p.antiguedad_anios, p.mantenimiento_pen, p.latitud, p.longitud, p.distrito, p.primera_vez,
       d.zona_apeim, d.nse_aprox,
       e.n_colegios, e.n_salud, e.n_comisarias, e.n_transporte, e.n_malls, e.n_parques, e.n_inpe,
       e.n_delitos_12m, e.dist_colegio_m, e.dist_salud_m, e.dist_comisaria_m, e.dist_transporte_m,
       e.dist_mall_m, e.dist_parque_m
FROM propiedades p
JOIN entorno e USING (prop_id)
LEFT JOIN distritos d USING (distrito)
WHERE p.operacion = :operacion
  AND p.precio_pen > 0 AND p.area_m2 > 0 AND p.latitud IS NOT NULL
"""

NSE = {"A": 5, "B": 4, "C": 3, "D": 2, "E": 1}
CONTEOS = ["n_colegios", "n_salud", "n_comisarias", "n_transporte", "n_malls", "n_parques", "n_inpe", "n_delitos_12m"]
DISTANCIAS = ["dist_colegio_m", "dist_salud_m", "dist_comisaria_m", "dist_transporte_m", "dist_mall_m", "dist_parque_m"]
VARIABLES = (["log_area", "num_dorm", "num_banios", "num_estac", "antiguedad_anios", "mantenimiento_m2",
              "latitud", "longitud", "zona_apeim", "nse"] + CONTEOS + [f"log_{c}" for c in DISTANCIAS])


# ── Variables (puras, probadas en tests/) ────────────────────

def variables(df: pd.DataFrame) -> pd.DataFrame:
    """Matriz de variables del modelo. Los nulos quedan como NaN (cada modelo los trata a su manera)."""
    num = lambda c: pd.to_numeric(df[c], errors="coerce")
    X = pd.DataFrame(index=df.index)
    X["log_area"] = np.log(num("area_m2"))
    for c in ("num_dorm", "num_banios", "num_estac", "antiguedad_anios", "latitud", "longitud", "zona_apeim"):
        X[c] = num(c)
    X["mantenimiento_m2"] = num("mantenimiento_pen") / num("area_m2")
    X["nse"] = df["nse_aprox"].map(NSE)
    for c in CONTEOS:
        X[c] = num(c)
    for c in DISTANCIAS:
        X[f"log_{c}"] = np.log1p(num(c))
    return X[VARIABLES].astype(float)


def utiles(X: pd.DataFrame) -> list[str]:
    """Variables con al menos un dato (p. ej. dist_parque_m queda fuera mientras no haya parques cargados)."""
    return [c for c in X.columns if X[c].notna().any()]


def objetivo(df: pd.DataFrame) -> np.ndarray:
    """log del precio por m²."""
    return np.log(pd.to_numeric(df["precio_pen"]).to_numpy(float) / pd.to_numeric(df["area_m2"]).to_numpy(float))


# ── Métodos de referencia (sin aprendizaje automático) ───────

def _km(lat1, lon1, lat2, lon2):
    """Distancia aproximada en km (equirectangular), igual que la app."""
    x = (lon2 - lon1) * 111.32 * np.cos(np.radians((lat1 + lat2) / 2))
    y = (lat2 - lat1) * 111.32
    return np.hypot(x, y)


def _percentil_ponderado(valores: np.ndarray, pesos: np.ndarray, q: float) -> float:
    orden = np.argsort(valores)
    v, w = valores[orden], pesos[orden]
    acum = np.cumsum(w)
    return float(v[np.searchsorted(acum, q * acum[-1])])


def predecir_comparables(entreno: pd.DataFrame, prueba: pd.DataFrame, k: int = 12) -> np.ndarray:
    """
    Precio por m² estimado con los k avisos más parecidos, igual que ubika-app/src/lib/evaluador.js:
    1 km pesa como 25 % de área, 0.6 dormitorios, 0.4 baños o estacionamientos, 15 años de antigüedad;
    mediana ponderada por 1/(0.25 + diferencia)². Devuelve log(precio por m²).
    """
    e = {c: pd.to_numeric(entreno[c], errors="coerce").to_numpy(float)
         for c in ("latitud", "longitud", "area_m2", "num_dorm", "num_banios", "num_estac", "antiguedad_anios")}
    m2 = pd.to_numeric(entreno["precio_pen"]).to_numpy(float) / e["area_m2"]
    sin_nan = lambda a: np.nan_to_num(a, nan=0.0)
    out = []
    for _, q in prueba.iterrows():
        d = _km(float(q["latitud"]), float(q["longitud"]), e["latitud"], e["longitud"])
        d = d + np.abs(np.log(float(q["area_m2"]) / e["area_m2"])) / 0.25
        d = d + np.abs((q["num_dorm"] if pd.notna(q["num_dorm"]) else 0) - sin_nan(e["num_dorm"])) * 0.6
        d = d + np.abs((q["num_banios"] if pd.notna(q["num_banios"]) else 0) - sin_nan(e["num_banios"])) * 0.4
        d = d + np.abs((q["num_estac"] if pd.notna(q["num_estac"]) else 0) - sin_nan(e["num_estac"])) * 0.4
        if pd.notna(q["antiguedad_anios"]):
            dif = np.abs(float(q["antiguedad_anios"]) - e["antiguedad_anios"]) / 15
            d = d + np.nan_to_num(dif, nan=0.0)       # solo cuenta si ambos la tienen
        cerca = np.argsort(d)[:k]
        out.append(_percentil_ponderado(m2[cerca], 1 / (0.25 + d[cerca]) ** 2, 0.5))
    return np.log(np.array(out))


def predecir_mediana_distrito(entreno: pd.DataFrame, prueba: pd.DataFrame) -> np.ndarray:
    """log del precio por m² mediano del distrito en el entrenamiento (o de toda la ciudad si no hay)."""
    m2 = pd.to_numeric(entreno["precio_pen"]) / pd.to_numeric(entreno["area_m2"])
    por_distrito = m2.groupby(entreno["distrito"]).median()
    return np.log(prueba["distrito"].map(por_distrito).fillna(m2.median()).to_numpy(float))


# ── Modelos de aprendizaje automático ────────────────────────

def modelos() -> dict[str, object]:
    """Pocos datos: árboles poco profundos y hojas grandes para no memorizar."""
    return {
        "ridge": make_pipeline(SimpleImputer(strategy="median", add_indicator=True), StandardScaler(), Ridge(alpha=3.0)),
        "random_forest": make_pipeline(SimpleImputer(strategy="median"), RandomForestRegressor(
            n_estimators=400, min_samples_leaf=3, max_features=0.5, random_state=SEMILLA, n_jobs=-1)),
        "hist_gb": HistGradientBoostingRegressor(
            max_iter=300, learning_rate=0.05, max_depth=3, min_samples_leaf=8, l2_regularization=1.0, random_state=SEMILLA),
    }


# ── Evaluación ───────────────────────────────────────────────

def metricas(precio: np.ndarray, estimado: np.ndarray) -> dict[str, float]:
    ape = np.abs(estimado / precio - 1)
    sst = np.sum((precio - precio.mean()) ** 2)
    return {
        "mape": round(100 * float(ape.mean()), 2),
        "mdape": round(100 * float(np.median(ape)), 2),
        "dentro_20": round(100 * float((ape <= 0.2).mean()), 1),
        "r2": round(1 - float(np.sum((precio - estimado) ** 2) / sst), 4) if sst > 0 else None,
        "rmse": round(float(np.sqrt(np.mean((precio - estimado) ** 2))), 0),
    }


def evaluar(df: pd.DataFrame, partes: int = 5, repeticiones: int = 3) -> dict[str, dict]:
    """Validación cruzada repetida. Todos los métodos ven las mismas particiones."""
    df = df.reset_index(drop=True)
    X, y = variables(df), objetivo(df)
    X = X[utiles(X)]
    area = pd.to_numeric(df["area_m2"]).to_numpy(float)
    precio = pd.to_numeric(df["precio_pen"]).to_numpy(float)

    metodos: dict[str, Callable[[np.ndarray, np.ndarray], np.ndarray]] = {
        "mediana_distrito": lambda tr, te: predecir_mediana_distrito(df.iloc[tr], df.iloc[te]),
        "comparables": lambda tr, te: predecir_comparables(df.iloc[tr], df.iloc[te]),
    }
    for nombre, modelo in modelos().items():
        def ajustar(tr, te, modelo=modelo):
            m = clone(modelo).fit(X.iloc[tr], y[tr])
            return m.predict(X.iloc[te])
        metodos[nombre] = ajustar

    cv = RepeatedKFold(n_splits=partes, n_repeats=repeticiones, random_state=SEMILLA)
    estimados = {n: [] for n in metodos}
    reales = []
    for tr, te in cv.split(X):
        reales.append(precio[te])
        for nombre, f in metodos.items():
            estimados[nombre].append(np.exp(f(tr, te)) * area[te])
    reales = np.concatenate(reales)
    return {n: metricas(reales, np.concatenate(e)) for n, e in estimados.items()}


def ganador(resultados: dict[str, dict], solo: set[str] | None = None) -> str:
    """El de menor MAPE (entre `solo`, si se da)."""
    candidatos = {n: r for n, r in resultados.items() if solo is None or n in solo}
    return min(candidatos, key=lambda n: candidatos[n]["mape"])


# ── Entrenamiento ────────────────────────────────────────────

def entrenar(operacion: str) -> dict:
    df = read_df(CONSULTA, {"operacion": operacion})
    n = len(df)
    log.info("%s: %d inmuebles con precio, área, coordenadas y entorno", operacion, n)
    if n < MINIMO:
        raise RuntimeError(f"{operacion}: solo {n} inmuebles; hacen falta al menos {MINIMO} para entrenar.")
    if n < POCOS:
        log.warning("%s: con %d inmuebles las métricas varían mucho; tómalas como referencia.", operacion, n)

    resultados = evaluar(df)
    mejor = ganador(resultados)
    mejor_ml = ganador(resultados, set(modelos()))
    for nombre, r in sorted(resultados.items(), key=lambda x: x[1]["mape"]):
        log.info("  %-17s MAPE %6.2f %%  MdAPE %6.2f %%  a menos de 20 %%: %5.1f %%  R2 %7.4f  RMSE S/ %s",
                 nombre, r["mape"], r["mdape"], r["dentro_20"], r["r2"] if r["r2"] is not None else float("nan"),
                 f"{r['rmse']:,.0f}")

    # El mejor modelo de aprendizaje automático, entrenado con todos los datos
    X = variables(df)
    usadas = utiles(X)
    modelo = clone(modelos()[mejor_ml]).fit(X[usadas], objetivo(df))
    SALIDA.mkdir(parents=True, exist_ok=True)
    joblib.dump({"modelo": modelo, "variables": usadas, "operacion": operacion,
                 "objetivo": "log(precio_pen / area_m2)"}, SALIDA / f"{operacion}_modelo.joblib")
    informe = {
        "operacion": operacion,
        "entrenado_at": dt.datetime.now().isoformat(timespec="seconds"),
        "n_inmuebles": n,
        "n_distritos": int(df["distrito"].nunique()),
        "datos_desde": str(df["primera_vez"].min()), "datos_hasta": str(df["primera_vez"].max()),
        "validacion": "RepeatedKFold 5×3, semilla 42",
        "variables": usadas,
        "variables_sin_datos": [c for c in VARIABLES if c not in usadas],
        "resultados": resultados,
        "mejor": mejor,
        "mejor_ml": mejor_ml,
        "supera_comparables": resultados[mejor_ml]["mape"] < resultados["comparables"]["mape"],
    }
    (SALIDA / f"{operacion}_metricas.json").write_text(json.dumps(informe, indent=2, ensure_ascii=False), encoding="utf-8")
    log.info("  mejor: %s; modelo guardado: %s (%s a comparables)", mejor, mejor_ml,
             "le gana" if informe["supera_comparables"] else "NO le gana")
    return informe


def _resumen(inf: dict) -> str:
    r = inf["resultados"]
    return (f"{inf['operacion']}: n={inf['n_inmuebles']}, mejor={inf['mejor']} "
            f"(MAPE {r[inf['mejor']]['mape']} %), {inf['mejor_ml']} MAPE {r[inf['mejor_ml']]['mape']} % "
            f"vs comparables {r['comparables']['mape']} %")


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(description="Entrena y evalúa el modelo de valor con los datos de Neon.")
    p.add_argument("--operacion", choices=("alquiler", "venta"), help="por defecto, las dos")
    p.add_argument("--sin-registro", action="store_true", help="no anota la corrida en la tabla corridas (pruebas)")
    args = p.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(levelname)-7s %(message)s", datefmt="%H:%M:%S")

    operaciones = [args.operacion] if args.operacion else ["alquiler", "venta"]
    if args.sin_registro:
        for op in operaciones:
            log.info(_resumen(entrenar(op)))
        return
    with corrida("modelo_valor", operaciones=operaciones) as c:
        informes = [entrenar(op) for op in operaciones]
        c.leidas = sum(i["n_inmuebles"] for i in informes)
        c.mensaje = " | ".join(_resumen(i) for i in informes)


if __name__ == "__main__":
    main()

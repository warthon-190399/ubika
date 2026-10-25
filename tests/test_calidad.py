"""Pruebas del score de calidad de vida (sin red ni base): fórmulas, posiciones, polígonos y niveles."""
import math
import re
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from ubika.pipeline import calidad as cv

CONF = {"version": 1, "peso_homicidios": 0.5, "factor_corredor": 1.5,
        "pesos": {"seguridad": 0.25, "longevidad": 0.10, "transporte": 0.15, "servicios": 0.15,
                  "verde": 0.15, "barrio": 0.10, "ruido": 0.10}}


def test_config_real_suma_uno_y_coincide_con_la_app():
    conf = cv.config()
    assert math.isclose(sum(conf["pesos"].values()), 1)
    assert set(conf["pesos"]) == set(cv.COMPONENTES)
    # La app (ciudad.js) usa los mismos pesos para las barras de cada componente
    js = (Path(__file__).parents[1] / "ubika-app" / "src" / "lib" / "ciudad.js").read_text(encoding="utf-8")
    for k, w in conf["pesos"].items():
        m = re.search(rf"\b{k}: \{{\s*\n\s*l: [^\n]*peso: ([0-9.]+)", js)
        assert m, f"ciudad.js no define el peso de {k}"
        assert math.isclose(float(m.group(1)), w), f"{k}: config.yaml {w} ≠ ciudad.js {m.group(1)}"
    js_scoring = (Path(__file__).parents[1] / "ubika-app" / "src" / "lib" / "scoring.js").read_text(encoding="utf-8")
    assert f"PESO_HOMICIDIOS = {conf['peso_homicidios']}" in js_scoring
    assert f"FACTOR_CORREDOR = {conf['factor_corredor']}" in js_scoring


def test_posiciones_como_en_la_app():
    ref = np.array([10.0, 20, 20, 30, np.nan])
    # más es mejor: 10 es mejor que nadie, 30 que tres; empates a la mitad
    assert cv.posiciones(ref, np.array([10, 20, 30]), False).tolist() == pytest.approx([0.125, 0.5, 0.875])
    # menos es mejor: al revés
    assert cv.posiciones(ref, np.array([10, 30]), True).tolist() == pytest.approx([0.875, 0.125])
    assert np.isnan(cv.posiciones(ref, np.array([np.nan]), True)[0])
    assert np.isnan(cv.posiciones(np.array([np.nan]), np.array([1.0]), True)[0])


def test_combinar_seguridad_y_faltantes():
    out = cv.combinar_seguridad(np.array([0.8, 0.8, np.nan, np.nan]), np.array([0.2, np.nan, 0.3, np.nan]), 0.5)
    assert out[:3].tolist() == pytest.approx([0.5, 0.8, 0.3])
    assert np.isnan(out[3])


def test_score_pondera_y_reparte_pesos():
    todos_1 = pd.DataFrame({f"pos_{k}": [1.0] for k in cv.COMPONENTES})
    s, n = cv.score(todos_1, CONF["pesos"])
    assert s[0] == pytest.approx(10) and n[0] == 7
    mitad = todos_1.assign(pos_seguridad=0.0)                 # seguridad 0, resto 1 → 10 × 0.75
    assert cv.score(mitad, CONF["pesos"])[0][0] == pytest.approx(7.5)
    sin_longevidad = todos_1.assign(pos_longevidad=np.nan, pos_seguridad=0.0)   # su peso se reparte
    s, n = cv.score(sin_longevidad, CONF["pesos"])
    assert s[0] == pytest.approx(10 * 0.65 / 0.90) and n[0] == 6


CAJA = lambda x0, y0, x1, y1: [[x0, y0], [x1, y0], [x1, y1], [x0, y1], [x0, y0]]
LIMITES = [
    ("a", [[CAJA(0, 0, 2, 2), CAJA(0.5, 0.5, 1, 1)]]),        # distrito «a» con un hueco
    ("b", [[CAJA(3, 0, 5, 2)]]),
]


def test_distritos_de_con_hueco_y_fuera():
    lat = np.array([1.5, 0.75, 1.0, 1.0, 9.0])
    lon = np.array([1.5, 0.75, 4.0, 2.5, 9.0])
    assert cv.distritos_de(lat, lon, LIMITES).tolist() == ["a", None, "b", None, None]


def _grilla():
    # 4 celdas en «a» (pocas denuncias, mucho parque) y 4 en «b» (muchas denuncias, nada de parque)
    filas = []
    for i in range(8):
        a = i < 4
        filas.append({"celda": i, "latitud": -12.0 - 0.003 * i, "longitud": -77.0, "seguridad": 2 if a else 40,
                      "transporte": 300 if a else 2000, "servicios": 10 if a else 3, "verde": 50_000 if a else 0,
                      "barrio": 20 if a else 5, "ruido": 55 if a else 70})
    return pd.DataFrame(filas), np.array(["a"] * 4 + ["b"] * 4, dtype=object)


POB, HOM, LON = {"a": 40_000, "b": 40_000}, {"a": 1.5, "b": 8.0}, {"a": 79.0, "b": 64.0}


def test_celdas_valores_por_habitante_y_score():
    grilla, dist = _grilla()
    cel = cv.celdas(grilla, dist, POB, HOM, LON, CONF)
    gente = 10_000 * cv.CELDAS_500M                          # 40 mil / 4 celdas, por el círculo de 500 m
    assert cel.loc[0, "val_denuncias_10k"] == pytest.approx(1e4 * 2 / gente)
    assert cel.loc[0, "val_verde_m2_hab"] == pytest.approx(50_000 / gente)
    assert cel.loc[0, "val_homicidios_100k"] == 1.5 and cel.loc[0, "val_edad_al_morir"] == 79
    assert (cel["n_componentes"] == 7).all()
    assert cel["score"].between(0, 10).all()
    assert cel.loc[:3, "score"].min() > cel.loc[4:, "score"].max()   # «a» mejor en todo
    assert cel.loc[0, "pos_seguridad"] == pytest.approx(0.75)        # mejor mitad en denuncias y homicidios
    assert (cel["version"] == 1).all()


def test_inmueble_usa_sus_conteos_y_la_celda_cercana():
    grilla, dist = _grilla()
    cel = cv.celdas(grilla, dist, POB, HOM, LON, CONF)
    props = pd.DataFrame([
        {"prop_id": "p1", "distrito": "a", "latitud": -12.0001, "longitud": -77.0, "n_delitos_12m": 1,
         "dist_transporte_m": 100, "n_colegios": 9, "n_salud": 2, "n_comisarias": 1, "n_malls": 1},
        {"prop_id": "p2", "distrito": "b", "latitud": -11.0, "longitud": -76.0, "n_delitos_12m": None,
         "dist_transporte_m": None, "n_colegios": None, "n_salud": None, "n_comisarias": None, "n_malls": None},
    ])
    inm = cv.inmuebles(props, cel, POB, HOM, LON, CONF)
    p1, p2 = inm.iloc[0], inm.iloc[1]
    assert p1["celda"] == 0 and p1["val_verde_m2_hab"] == cel.loc[0, "val_verde_m2_hab"]
    assert p1["val_servicios"] == 13 and p1["val_transporte_m"] == 100
    assert p1["pos_transporte"] == 1.0                        # más cerca que todas las celdas
    assert pd.isna(p2["celda"]) and np.isnan(p2["val_ruido_db"])   # lejos de toda celda: sin verde/barrio/ruido
    assert p2["n_componentes"] < 7 and 0 <= p2["score"] <= 10
    assert 0 <= p1["pos_score"] <= 1


def test_resumen_distritos():
    grilla, dist = _grilla()
    dis = cv.resumen_distritos(cv.celdas(grilla, dist, POB, HOM, LON, CONF), 1).set_index("distrito")
    assert dis.loc["a", "n_celdas"] == 4 and dis.loc["a", "puesto"] == 1 and dis.loc["b", "puesto"] == 2
    assert dis.loc["a", "score_p25"] <= dis.loc["a", "score"] <= dis.loc["a", "score_p75"]


def test_transporte_efectivo_penaliza_al_corredor():
    f = 1.5
    # estación a 900 m o paradero a 400 m (equivale a 600): cuenta el paradero
    assert cv.transporte_efectivo(np.array([900.0]), np.array([400.0]), f).tolist() == [600]
    # estación a 500 m o paradero a 400 m (equivale a 600): cuenta la estación
    assert cv.transporte_efectivo(np.array([500.0]), np.array([400.0]), f).tolist() == [500]
    # sin corredores cargados, todo igual que antes; sin estación, solo el corredor
    assert cv.transporte_efectivo(np.array([700.0]), np.array([np.nan]), f).tolist() == [700]
    assert cv.transporte_efectivo(np.array([np.nan]), np.array([100.0]), f).tolist() == [150]


def test_celdas_y_inmuebles_usan_el_corredor():
    grilla, dist = _grilla()
    grilla["corredor"] = [100] * 4 + [5000] * 4                   # «a» tiene un corredor al lado
    cel = cv.celdas(grilla, dist, POB, HOM, LON, {**CONF, "factor_corredor": 1.5})
    assert cel.loc[0, "val_corredor_m"] == 100
    assert cel.loc[0, "val_transporte_m"] == 150                  # min(300 a la estación, 1.5 × 100)
    assert cel.loc[4, "val_transporte_m"] == 2000                 # el corredor está lejos: cuenta la estación
    props = pd.DataFrame([{"prop_id": "p", "distrito": "a", "latitud": -12.0, "longitud": -77.0, "n_delitos_12m": 1,
                           "dist_transporte_m": 1200, "dist_corredor_m": 200, "n_colegios": 1, "n_salud": 0,
                           "n_comisarias": 0, "n_malls": 0}])
    inm = cv.inmuebles(props, cel, POB, HOM, LON, {**CONF, "factor_corredor": 1.5})
    assert inm.loc[0, "val_transporte_m"] == 300 and inm.loc[0, "val_corredor_m"] == 200

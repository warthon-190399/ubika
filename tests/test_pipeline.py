"""Pruebas del pipeline descriptivo (sin base de datos)."""
import datetime as dt

import numpy as np
import pandas as pd

from ubika.pipeline import entorno, limpieza, parseo

ALIAS = {"magdalena": "magdalena", "miraflores": "miraflores", "lima": "lima cercado",
         "lima cercado": "lima cercado", "san luis": "san luis", "callao": "callao"}
CONF = {
    "limpieza": {"area_m2": [15, 1000], "precio_pen": {"alquiler": [400, 40000], "venta": [40000, 15000000]},
                 "dedup": {"tolerancia_precio": 0.03, "tolerancia_area_m2": 2}},
    "geocoding": {"caja": {"lat_min": -12.55, "lat_max": -11.55, "lon_min": -77.25, "lon_max": -76.60}},
}


# ── parseo ───────────────────────────────────────────────────

def test_precios():
    assert parseo.precios("S/ 3,000 · USD 857") == (3000.0, 857.0)
    assert parseo.precios("S/ 1,038,000 · USD 310,000") == (1038000.0, 310000.0)
    assert parseo.precios("USD 120,000") == (None, 120000.0)
    assert parseo.precios("Consultar precio") == (None, None)
    assert parseo.precios(None) == (None, None)


def test_area_y_enteros():
    assert parseo.area_m2("102 m² tot.") == 102.0
    assert parseo.area_m2("102.30 m²") == 102.3
    assert parseo.area_m2("63 a 74 m² tot.") is None
    assert parseo.area_m2("2 ha") == 20000.0
    assert parseo.entero("2 dorm.") == 2 and parseo.entero("Monoambiente") is None
    assert parseo.mantenimiento("S/ 620 Mantenimiento") == 620.0


def test_antiguedad():
    assert parseo.antiguedad("A estrenar") == 0
    assert parseo.antiguedad("En construcción") == 0
    assert parseo.antiguedad("11 años") == 11
    assert parseo.antiguedad("999 años") is None
    assert parseo.antiguedad(None) is None


def test_distrito():
    assert parseo.distrito("Magdalena, Lima", ALIAS) == "magdalena"
    assert parseo.distrito("Javier Prado Et.4, San Luis", ALIAS) == "san luis"
    assert parseo.distrito("Lima, Lima", ALIAS) == "lima cercado"
    assert parseo.distrito("Santa Beatriz, Lima Cercado", ALIAS) == "lima cercado"
    assert parseo.distrito("Callao, Callao", ALIAS) == "callao"
    assert parseo.distrito("Barrio inventado", ALIAS) is None


# ── limpieza ─────────────────────────────────────────────────

def _crudo(url, **kw):
    base = dict(fuente="adondevivir", operacion="alquiler", url=url, precio_raw="S/ 3,000 · USD 857",
                mant_listado=None, direccion_raw="Jiron Antonio Raymondi", ubicacion_raw="Magdalena, Lima",
                area_raw="102 m² tot.", dorm_listado="2 dorm.", banos_listado="2 baños", estac_listado=None,
                latitud=-12.0980374, longitud=-77.0684193, primera_vez=dt.date(2026, 10, 15),
                ultima_vez=dt.date(2026, 10, 15), estado_detalle=None, tipo_inmueble_raw=None, pen_detalle=None,
                usd_detalle=None, mant_detalle=None, area_total_raw=None, dorm_detalle=None, banos_detalle=None,
                estac_detalle=None, antiguedad_raw=None, inmobiliaria_raw=None, fecha_publicacion=None,
                visibilidad_direccion=None, ubicacion_portal=None)
    base.update(kw)
    return base


def test_limpiar_prefiere_ficha_y_descarta():
    crudos = pd.DataFrame([
        _crudo("u1", pen_detalle=3100.0, antiguedad_raw="11 años", visibilidad_direccion="EXACT"),
        _crudo("u2", precio_raw="USD 1,000"),                                     # solo dólares
        _crudo("u3", area_raw="5 m² tot."),                                       # área imposible
        _crudo("u4", ubicacion_raw="Barrio inventado"),                           # distrito desconocido
        _crudo("u5", estado_detalle="no_disponible"),                             # dado de baja
        _crudo("u6", latitud=-3.5, longitud=-80.4),                               # coordenada fuera de Lima
    ])
    df, desc = limpieza.limpiar(crudos, ALIAS, CONF)
    assert set(df["url"]) == {"u1", "u2", "u6"}
    u1 = df.set_index("url").loc["u1"]
    assert u1["precio_pen"] == 3100.0 and u1["antiguedad_anios"] == 11
    assert u1["num_estac"] == 0 and u1["geo_precision"] == "portal_exacta"
    u2 = df.set_index("url").loc["u2"]
    assert abs(u2["precio_pen"] - 1000 * 3000 / 857) < 1           # mediana del tipo de cambio implícito
    assert pd.isna(df.set_index("url").loc["u6", "latitud"])
    assert desc == {"aviso dado de baja": 1, "área fuera de 15–1000 m²": 1, "distrito no reconocido": 1}


def test_agrupar_y_consolidar_repetidos():
    crudos = pd.DataFrame([
        _crudo("a1", fuente="adondevivir"),
        _crudo("a2", fuente="urbania", precio_raw="S/ 3,050", latitud=-12.09810, longitud=-77.06845,
               direccion_raw="Jr. A. Raymondi 123", antiguedad_raw="11 años"),           # mismo depa, 10 m
        _crudo("a3", area_raw="140 m² tot."),                                             # otro depa
        _crudo("a4", operacion="venta", precio_raw="S/ 900,000"),                         # otra operación
    ])
    df, _ = limpieza.limpiar(crudos, ALIAS, CONF)
    df["grupo"] = limpieza.agrupar(df, 0.03, 2)
    g = dict(zip(df["url"], df["grupo"]))
    assert g["a1"] == g["a2"] and len({g["a1"], g["a3"], g["a4"]}) == 3

    props, avisos = limpieza.consolidar(df, existentes={"a2": "11111111-1111-1111-1111-111111111111"})
    assert len(props) == 3 and len(avisos) == 4
    unido = next(p for p in props if p["prop_id"] == "11111111-1111-1111-1111-111111111111")
    assert unido["antiguedad_anios"] == 11                    # completado desde el otro aviso del grupo
    assert {a["url"] for a in avisos if a["prop_id"] == unido["prop_id"]} == {"a1", "a2"}


def test_prop_id_estable():
    crudos = pd.DataFrame([_crudo("x1")])
    df, _ = limpieza.limpiar(crudos, ALIAS, CONF)
    df["grupo"] = limpieza.agrupar(df, 0.03, 2)
    p1, _ = limpieza.consolidar(df, {})
    p2, _ = limpieza.consolidar(df, {})
    assert p1[0]["prop_id"] == p2[0]["prop_id"]


# ── entorno ──────────────────────────────────────────────────

def test_entorno_conteos_distancias_y_pesos():
    props = pd.DataFrame({"prop_id": ["p"], "latitud": [-12.1000], "longitud": [-77.0300]})
    # 1° de latitud ≈ 111 km → 0.002° ≈ 222 m ; 0.01° ≈ 1.1 km
    pois = pd.DataFrame({
        "categoria": ["colegio", "colegio", "metro", "mall"],
        "latitud": [-12.1020, -12.1100, -12.1000, -12.1500],
        "longitud": [-77.0300, -77.0300, -77.0330, -77.0300],
    })
    inpe = pd.DataFrame({"latitud": [-12.1001], "longitud": [-77.0301]})
    delitos = pd.DataFrame({"latitud": [-12.1003, -12.1004, -12.2000], "longitud": [-77.0300] * 3,
                            "peso": [1.5, 2.0, 9.0]})
    e = entorno.calcular(props, pois, inpe, delitos, radio_m=500).iloc[0]
    assert e["n_colegios"] == 1 and 215 <= e["dist_colegio_m"] <= 230
    assert e["n_transporte"] == 1 and 320 <= e["dist_transporte_m"] <= 335
    assert e["n_malls"] == 0 and e["dist_mall_m"] > 5000
    assert e["n_parques"] == 0 and e["dist_parque_m"] is None       # sin datos de parques todavía
    assert e["n_inpe"] == 1
    assert e["n_delitos_12m"] == 3.5                                   # 1.5 + 2.0; el lejano no cuenta


# ── capas ────────────────────────────────────────────────────

def test_capas_indices():
    from ubika.pipeline import capas
    caja = {"lat_min": -12.13, "lat_max": -12.09, "lon_min": -77.05, "lon_max": -77.01}
    celdas = capas.grilla(caja)
    pois = pd.DataFrame({"categoria": ["metro", "colegio", "colegio", "salud"],
                         "latitud": [-12.10, -12.12, -12.121, -12.119], "longitud": [-77.02, -77.04, -77.04, -77.041]})
    delitos = pd.DataFrame({"latitud": [-12.12] * 5 + [-12.10], "longitud": [-77.04] * 5 + [-77.02],
                            "peso": [1.5] * 6})
    out = capas.calcular(celdas, pois, delitos)
    assert set(out["capa"]) == {"seguridad", "transporte", "servicios"}
    assert out["indice"].between(0, 1).all()
    s = out[out.capa == "seguridad"].set_index("celda")
    peor = s["valor"].idxmax()
    assert s.loc[peor, "indice"] == s["indice"].min()              # más denuncias = índice más bajo
    t = out[out.capa == "transporte"].set_index("celda")
    assert t.loc[t["valor"].idxmin(), "indice"] == t["indice"].max()  # más cerca de la estación = mejor

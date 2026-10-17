"""Transformaciones de OpenStreetMap y capas de calidad de vida (sin red ni base de datos)."""
import numpy as np
import pandas as pd

from ubika.referencias import osm


def _cuadrado(lat, lon, lado_m):
    """Anillo cerrado de un cuadrado de `lado_m` metros, en el formato `geometry` de Overpass."""
    dlat, dlon = lado_m / osm.M_LAT, lado_m / osm.M_LON
    pts = [(lat, lon), (lat, lon + dlon), (lat + dlat, lon + dlon), (lat + dlat, lon), (lat, lon)]
    return [{"lat": a, "lon": b} for a, b in pts]


def test_area_de_un_cuadrado():
    assert abs(osm.area_m2(_cuadrado(-12.1, -77.03, 100)) - 10_000) < 150     # 100 m × 100 m ≈ 1 ha


def test_parques_filtra_bermas_y_calcula_centro():
    elementos = [
        {"type": "way", "id": 1, "tags": {"leisure": "park", "name": "Parque Kennedy"}, "geometry": _cuadrado(-12.12, -77.03, 80)},
        {"type": "way", "id": 2, "tags": {"leisure": "park"}, "geometry": _cuadrado(-12.13, -77.03, 10)},      # 100 m²: berma
        {"type": "relation", "id": 3, "tags": {"leisure": "park"},
         "members": [{"type": "way", "role": "outer", "geometry": _cuadrado(-12.14, -77.02, 50)}]},
    ]
    filas = osm.parques(elementos)
    assert [f["atributos"]["osm_id"] for f in filas] == ["way/1", "relation/3"]
    kennedy = filas[0]
    assert kennedy["nombre"] == "Parque Kennedy" and kennedy["categoria"] == "parque"
    assert 6000 < kennedy["atributos"]["area_m2"] < 6600
    assert -12.12 < kennedy["latitud"] < -12.119


def test_comercio_mapea_tags_y_usa_el_centro_de_los_edificios():
    elementos = [
        {"type": "node", "id": 1, "lat": -12.1, "lon": -77.0, "tags": {"amenity": "pharmacy", "name": "Inkafarma"}},
        {"type": "way", "id": 2, "center": {"lat": -12.2, "lon": -77.1}, "tags": {"shop": "supermarket"}},
        {"type": "node", "id": 3, "lat": -12.1, "lon": -77.0, "tags": {"amenity": "cafe"}},
        {"type": "node", "id": 4, "lat": -12.1, "lon": -77.0, "tags": {"amenity": "bench"}},                 # no interesa
    ]
    filas = osm.comercio(elementos)
    assert [(f["categoria"], f["latitud"]) for f in filas] == [("farmacia", -12.1), ("supermercado", -12.2), ("restaurante", -12.1)]


def test_vias_se_muestrean_cada_40_m():
    linea = [{"lat": -12.1, "lon": -77.0}, {"lat": -12.1, "lon": -77.0 + 400 / osm.M_LON}]          # 400 m
    filas = osm.vias([{"type": "way", "id": 1, "tags": {"highway": "trunk", "name": "Vía Expresa"}, "geometry": linea},
                      {"type": "way", "id": 2, "tags": {"highway": "residential"}, "geometry": linea}])
    assert {f["tipo"] for f in filas} == {"autopista"}
    assert len(filas) == 11                                                                        # 10 tramos + el final


def test_ruido_baja_con_la_distancia_y_tiene_piso():
    from ubika.pipeline.capas import FONDO_DB, nivel_ruido
    d = np.array([10.0, 100.0, 1000.0, 5000.0])
    v = nivel_ruido({"autopista": d})
    assert (np.diff(v) < 0).all()                      # más lejos, menos ruido
    assert 77 < v[0] < 79                               # junto a la vía ≈ 78 dB
    assert v[-1] >= FONDO_DB                           # nunca baja del fondo urbano
    dos = nivel_ruido({"autopista": d, "principal": d})
    assert (dos > v).all()                              # dos fuentes suman


def test_capas_de_calidad_de_vida():
    from ubika.pipeline import capas
    caja = {"lat_min": -12.13, "lat_max": -12.09, "lon_min": -77.05, "lon_max": -77.01}
    pois = pd.DataFrame({
        "categoria": ["metro", "colegio", "colegio", "salud", "parque", "farmacia", "mercado"],
        "latitud": [-12.10, -12.12, -12.121, -12.119, -12.12, -12.12, -12.121],
        "longitud": [-77.02, -77.04, -77.04, -77.041, -77.04, -77.04, -77.04],
        "area_m2": [None, None, None, None, 20000, None, None],
    })
    delitos = pd.DataFrame({"latitud": [-12.12] * 5 + [-12.10], "longitud": [-77.04] * 5 + [-77.02], "peso": [1.5] * 6})
    ruido = pd.DataFrame({"tipo": ["principal"] * 3, "latitud": [-12.10] * 3, "longitud": [-77.03, -77.025, -77.02]})
    out = capas.calcular(capas.grilla(caja), pois, delitos, 500, ruido)
    assert {"verde", "barrio", "ruido"} <= set(out["capa"])
    v = out[out.capa == "verde"].set_index("celda")
    assert v["valor"].max() == 20000                                      # celda junto al parque
    r = out[out.capa == "ruido"].set_index("celda")
    assert r.loc[r["valor"].idxmax(), "indice"] == r["indice"].min()     # más ruido = índice más bajo
    # la grilla urbana no cambia por sumar comercio
    sin = capas.calcular(capas.grilla(caja), pois[pois.categoria.isin(capas.BASE_URBANA)], delitos)
    assert out["celda"].nunique() == sin["celda"].nunique()

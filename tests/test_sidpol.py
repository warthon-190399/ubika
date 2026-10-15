"""Pruebas de las transformaciones SIDPOL con respuestas reales del servicio (tests/fixtures)."""
import datetime as dt
import json
from pathlib import Path

from ubika.referencias import sidpol
from ubika.texto import normalizar

FIX = Path(__file__).parent / "fixtures"
CAJA = {"lat_min": -12.55, "lat_max": -11.55, "lon_min": -77.25, "lon_max": -76.60}
ALIAS = {"chorrillos": "chorrillos", "villa maria del triunfo": "vmt", "san martin de porres": "smp",
         "ventanilla": "ventanilla", "los olivos": "los olivos", "san juan de lurigancho": "sjl",
         "bellavista": "bellavista"}


def _puntos():
    return [f["attributes"] for f in json.loads((FIX / "sidpol_puntos.json").read_text(encoding="utf-8"))["features"]]


def test_normalizar():
    assert normalizar("  Breña,  LIMA ") == "brena, lima"
    assert normalizar(None) == ""


def test_categorias():
    assert sidpol.categoria("PATRIMONIO (DELITO)") == "patrimonio"
    assert sidpol.categoria("LIBERTAD (DELITO)") == "violencia"
    assert sidpol.categoria("LEY DE VIOLENCIA CONTRA LA MUJER Y GRUPOS VULNERABLES") == "violencia_familiar"
    assert sidpol.categoria("ALGO NUEVO") == "otros"
    assert sidpol.categoria(None) == "otros"


def test_fila_punto_real():
    filas = [sidpol.fila_punto(a, ALIAS, CAJA) for a in _puntos()]
    assert all(filas)
    f = filas[0]
    assert f["id_dgc"] == "355804571050215"
    assert f["distrito"] == "chorrillos"
    assert f["categoria"] == "patrimonio"
    assert f["fecha_hecho"].tzinfo is not None
    # 1782864000000 ms = 2026-07-01 00:00 UTC → 2026-06-30 19:00 en Lima
    assert (f["anio"], f["mes"]) == (2026, 6)
    assert {r["distrito"] for r in filas} == {"chorrillos", "vmt", "smp", "ventanilla", "los olivos", "sjl"}


def test_fila_punto_descarta_fuera_de_lima_y_sin_id():
    a = dict(_puntos()[0])
    assert sidpol.fila_punto({**a, "lat_hecho": -3.5, "long_hecho": -80.4}, ALIAS, CAJA) is None
    assert sidpol.fila_punto({**a, "lat_hecho": None}, ALIAS, CAJA) is None
    assert sidpol.fila_punto({**a, "ID_DGC_03": None}, ALIAS, CAJA) is None


def test_distrito_desconocido_queda_null():
    a = {**_puntos()[0], "distrito_hecho": "DISTRITO INVENTADO"}
    assert sidpol.fila_punto(a, ALIAS, CAJA)["distrito"] is None


def test_unir_conteos():
    tot = [f["attributes"] for f in json.loads((FIX / "sidpol_agregado.json").read_text(encoding="utf-8"))["features"]]
    pre = [{"distrito_hecho": "BELLAVISTA", "tipo_hecho": "FALTAS", "n": 7}]
    filas = sidpol.unir_conteos(tot, pre, "CALLAO", 2026, 7, ALIAS)
    assert len(filas) == 6
    faltas = next(f for f in filas if f["tipo_hecho"] == "FALTAS")
    assert (faltas["n_total"], faltas["n_con_ubicacion"], faltas["distrito"]) == (12, 7, "bellavista")
    assert all(f["n_con_ubicacion"] <= f["n_total"] for f in filas)


def test_meses():
    assert list(sidpol.meses(dt.date(2025, 11, 15), dt.date(2026, 2, 1))) == [(2025, 11), (2025, 12), (2026, 1), (2026, 2)]

"""Pruebas de las transformaciones de puntos de interés (sin base de datos)."""
import json
from pathlib import Path

import pandas as pd

from ubika.referencias import puntos

FIX = Path(__file__).parent / "fixtures"
ALIAS = {"callao": "callao", "san juan de miraflores": "sjm", "sjm": "sjm"}


def test_linea1_descarta_fuera_de_lima_y_repetidas():
    df = pd.DataFrame([
        {"nombre": "angamos", "latitud": -12.1118, "longitud": -77.0003, "distrito": "surquillo"},
        {"nombre": "pumacahua", "latitud": -9.19, "longitud": -75.01, "distrito": "vmt"},          # Perú central
        {"nombre": "villa maria", "latitud": -12.194788, "longitud": -76.93464, "distrito": "vmt"},
        {"nombre": "maria auxiliadora", "latitud": -12.194788, "longitud": -76.93464, "distrito": "vmt"},
    ])
    filas = puntos.linea1(df, ALIAS)
    assert [f["nombre"] for f in filas] == ["Angamos"]
    assert filas[0]["categoria"] == "metro"


def test_salud_un_punto_por_coordenada():
    df = pd.DataFrame([
        {"nombre": "hospital a", "latitud": -12.05, "longitud": -76.95, "distrito": "sjm", "direccion": "x"},
        {"nombre": "essalud", "latitud": -12.05, "longitud": -76.95, "distrito": "sjm", "direccion": "x"},
        {"nombre": "huacho", "latitud": -11.10, "longitud": -77.59, "distrito": "huacho", "direccion": "y"},
    ])
    filas = puntos.salud(df, ALIAS)
    assert len(filas) == 1 and filas[0]["distrito"] == "sjm"


def test_colegios_atributos():
    df = pd.DataFrame([{"index": 0, "nombre": "0001 maria auxiliadora", "distrito": "lima",
                        "direccion": "jr isaias 237", "nivel__modalidad": "primaria",
                        "gestion__dependencia": "publica", "latitud": -12.04671, "longitud": -77.01373}])
    f = puntos.colegios(df, {"lima": "lima cercado"})[0]
    assert f["distrito"] == "lima cercado"
    assert f["atributos"] == {"nivel": "primaria", "gestion": "publica", "direccion": "jr isaias 237"}


def test_comisarias_mininter():
    feats = json.loads((FIX / "comisarias.json").read_text(encoding="utf-8"))["features"]
    filas = puntos.comisarias_mininter(feats, ALIAS)
    assert len(filas) == 3
    assert filas[0]["nombre"] == "Cpnp La Legua" and filas[0]["distrito"] == "callao"
    assert filas[0]["atributos"] == {"tipo": "B", "cod_cpnp": "6006"}

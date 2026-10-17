"""Pruebas de los parsers Navent con HTML recortado de páginas reales (tests/fixtures)."""
import datetime as dt
from pathlib import Path

from ubika.scraping import navent

FIX = Path(__file__).parent / "fixtures"
BASE = "https://www.adondevivir.com"


def _html(nombre):
    return (FIX / nombre).read_text(encoding="utf-8")


def test_listado_lee_unidades_y_coordenadas():
    avisos, total = navent.parsear_listado(_html("listado_adondevivir.html"), BASE)
    assert total == 3608
    assert [a["tipo_raw"] for a in avisos] == ["PROPERTY", "DEVELOPMENT", "PROPERTY"]

    a = avisos[0]
    assert a["url"] == BASE + "/propiedades/clasificado/alclapin-departamento-en-alquiler-en-magdalena:-102-m-sup2--2-150673523.html"
    assert a["aviso_id"] == "150673523"
    assert a["precio_raw"] == "S/ 3,000 · USD 857"
    assert a["mantenimiento_raw"] is None
    assert a["area_raw"] == "102 m² tot." and a["dorm_raw"] == "2 dorm."
    assert a["banos_raw"] == "2 baños" and a["estac_raw"] == "1 estac."
    assert a["direccion_raw"] == "Jiron Antonio Raymondi"
    assert a["ubicacion_raw"] == "Magdalena, Lima"
    assert (a["latitud"], a["longitud"]) == (-12.0980374, -77.0684193)


def test_listado_sin_geo_y_con_mantenimiento():
    avisos, _ = navent.parsear_listado(_html("listado_adondevivir.html"), BASE)
    b = avisos[2]
    assert b["latitud"] is None and b["longitud"] is None
    assert b["mantenimiento_raw"] == "S/ 620 Mantenimiento"
    assert b["area_raw"] == "118 m² tot."      # el área de la tarjeta, no la del JSON-LD (84 m²)


def test_detalle():
    d = navent.parsear_detalle(_html("detalle_adondevivir.html"))
    assert d["estado"] == "ok" and d["estado_aviso"] == "ONLINE"
    assert (d["precio_pen"], d["precio_usd"]) == (3000.0, 857.0)
    assert d["mantenimiento_raw"] is None                   # el portal pone '0' cuando no lo informa
    assert d["area_total_raw"] == "102 m² tot." and d["area_cubierta_raw"] == "102 m² cub."
    assert (d["dorm_raw"], d["banos_raw"], d["estac_raw"]) == ("2 dorm.", "2 baños", "1 estac.")
    assert d["antiguedad_raw"] == "11 años"
    assert d["publicado_raw"] == "Publicado hace 13 días"
    assert d["publicado_at"] == dt.datetime(2026, 7, 30, 20, 46, 12, tzinfo=dt.timezone.utc)
    assert d["fecha_publicacion"] == dt.date(2026, 7, 30)
    assert d["visualizaciones_raw"] == "867"
    assert d["inmobiliaria_raw"] == "REMAX PRO" and d["tipo_publicador"] == 2
    assert d["visibilidad_direccion"] == "EXACT"
    assert d["tipo_inmueble_raw"] == "Apartamento"
    assert d["ubicacion_portal"]["name"] == "Magdalena"
    assert "Servicios" in d["caracteristicas"]
    assert d["descripcion"].startswith("102.30 m²") and "\n" in d["descripcion"]


def test_detalle_dado_de_baja():
    assert navent.parsear_detalle("<html><body><h1>Aviso no disponible</h1></body></html>") == {"estado": "no_disponible"}


def test_bloque_respeta_llaves_dentro_de_strings():
    texto = "'a': {\"x\": \"llave } suelta\", \"y\": {\"z\": [1, 2]}},\n'b': 1"
    assert navent._bloque(texto, "a") == '{"x": "llave } suelta", "y": {"z": [1, 2]}}'


def test_aviso_id():
    assert navent.aviso_id("/propiedades/clasificado/veclapin-venta-en-chorrillos-151228718.html") == "151228718"
    assert navent.aviso_id("/otra-cosa") is None

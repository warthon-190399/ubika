"""Pruebas de las transformaciones SINADEF con filas reales del CSV de MINSA (tests/fixtures)."""
import io
from pathlib import Path

from ubika.referencias import sinadef

FIX = Path(__file__).parent / "fixtures" / "sinadef_muestra.csv"
ALIAS = {"san juan de lurigancho": "sjl", "brena": "brena", "santiago de surco": "surco",
         "lima": "lima cercado", "miraflores": "miraflores",
         "carmen de la legua-reynoso": "carmen de la legua", "ventanilla": "ventanilla"}


def _conteo():
    return sinadef.contar(sinadef.leer(FIX, chunksize=5))     # chunks chicos: prueba que se suma entre partes


def test_tipo_muerte():
    assert sinadef.tipo_muerte("HOMICIDIO") == "homicidio"
    assert sinadef.tipo_muerte("ACCIDENTE DE TRANSITO") == "transito"
    assert sinadef.tipo_muerte(" accidente de tránsito ") == "transito"
    assert sinadef.tipo_muerte("NO SE CONOCE") == "violenta_sin_tipo"
    assert sinadef.tipo_muerte("SIN REGISTRO") == "no_violenta"
    assert sinadef.tipo_muerte("") == "no_violenta"
    assert sinadef.tipo_muerte(None) == "no_violenta"


def test_leer_columnas():
    df = next(sinadef.leer(FIX))
    assert list(df.columns) == ["edad", "tiempo_edad", "departamento", "provincia", "distrito_raw", "anio", "mes",
                                "muerte_violenta"]
    assert len(df) == 13


def test_solo_lima_y_callao():
    c = _conteo()
    assert sum(c.values()) == 11                               # fuera: Huaura (dpto. Lima) y Arequipa
    assert {k[0] for k in c} == {"LIMA", "CALLAO"}
    assert not any(k[1] in ("HUACHO", "PAUCARPATA") for k in c)


def test_agrega_por_mes_y_tipo():
    c = _conteo()
    assert c[("LIMA", "SAN JUAN DE LURIGANCHO", 2024, 1, "homicidio")] == 2
    assert c[("LIMA", "SAN JUAN DE LURIGANCHO", 2024, 2, "no_violenta")] == 1
    assert c[("LIMA", "BREÑA", 2019, 6, "transito")] == 1
    assert c[("LIMA", "MIRAFLORES", 2020, 1, "no_violenta")] == 1   # MUERTE VIOLENTA vacía
    assert c[("CALLAO", "VENTANILLA", 2018, 1, "accidente_trabajo")] == 1


def test_filas_con_distrito():
    filas = sinadef.filas(_conteo(), ALIAS)
    assert sum(f["n"] for f in filas) == 11
    por_raw = {f["distrito_raw"]: f["distrito"] for f in filas}
    assert por_raw["BREÑA"] == "brena"
    assert por_raw["LIMA"] == "lima cercado"
    assert por_raw["CARMEN DE LA LEGUA-REYNOSO"] == "carmen de la legua"
    assert por_raw["SIN REGISTRO"] is None
    llaves = [(f["provincia"], f["distrito_raw"], f["anio"], f["mes"], f["tipo_muerte"]) for f in filas]
    assert len(llaves) == len(set(llaves))                     # respeta la llave primaria de la tabla
    assert all(f["tipo_muerte"] in sinadef.TIPOS.values() or f["tipo_muerte"] == "no_violenta" for f in filas)


def test_anio_o_mes_invalido_se_descarta():
    csv = ("DEPARTAMENTO DOMICILIO|PROVINCIA DOMICILIO|DISTRITO DOMICILIO|AÑO|MES|MUERTE VIOLENTA\n"
           "LIMA|LIMA|ATE|2023|13|HOMICIDIO\n"
           "LIMA|LIMA|ATE||05|HOMICIDIO\n"
           "LIMA|LIMA|ATE|2023|05|HOMICIDIO\n")
    c = sinadef.contar(sinadef.leer(io.StringIO(csv)))
    assert dict(c) == {("LIMA", "ATE", 2023, 5, "homicidio"): 1}


def test_edad_anios():
    assert sinadef.edad_anios("80", "AÑOS") == 80
    assert sinadef.edad_anios(" 7 ", "años") == 7
    assert sinadef.edad_anios("3", "MESES") == 0                  # menores de un año cuentan como 0
    assert sinadef.edad_anios("12", "HORAS") == 0
    assert sinadef.edad_anios("SIN REGISTRO", "AÑOS") is None
    assert sinadef.edad_anios("130", "AÑOS") is None              # fuera de rango
    assert sinadef.edad_anios("5", "SIN REGISTRO") is None


def test_edades_por_distrito_y_tipo():
    conteo, edades = sinadef.agregar(sinadef.leer(FIX, chunksize=5))
    assert sum(conteo.values()) == 11                              # el conteo de siempre no cambia
    assert sum(e["n"] for e in edades.values()) == 11               # todas las filas de Lima/Callao tienen edad
    nat = edades[("LIMA", "SAN JUAN DE LURIGANCHO", 2024, "natural")]
    assert (nat["n"], nat["suma"], nat["n65"], nat["n80"]) == (1, 80, 1, 1)
    vio = edades[("LIMA", "SAN JUAN DE LURIGANCHO", 2024, "violenta")]   # dos homicidios: 38 y 22 años
    assert (vio["n"], vio["suma"], vio["n65"], vio["menores_1"]) == (2, 60, 0, 0)
    assert ("LIMA", "MIRAFLORES", 2020, "natural") in edades      # MUERTE VIOLENTA vacía = natural
    filas = sinadef.filas_edad(edades, ALIAS)
    sjl = [f for f in filas if f["distrito"] == "sjl" and f["anio"] == 2024 and f["tipo"] == "violenta"][0]
    assert sjl["suma_edad"] == 60 and sjl["n_con_edad"] == 2

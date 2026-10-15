"""
Denuncias policiales SIDPOL (MININTER) para Lima Metropolitana y Callao.

Fuente: capa pública SIDPOL_DELITOS_TOTAL del Mapa del Delito de MININTER
(https://mininter-dgis.maps.arcgis.com/apps/webappviewer/index.html?id=ffc03c3586b142b988c931312d7da17b).

Qué se guarda:
- delitos_puntos: solo denuncias con ubicación propia. Las que MININTER tiene sin coordenada
  (ESTADO_COORD = 'CERO_AMBAS', ~66% en Lima) aparecen todas apiladas en un punto por distrito,
  así que no sirven para el mapa y no se descargan como puntos.
- delitos_distrito_mes: conteos de TODAS las denuncias por distrito, mes y tipo, y cuántas
  tienen ubicación. Sirve para comparar distritos y para ponderar los puntos
  (en cada distrito, peso = total / con_ubicación).

No se guardan direcciones, comisarías ni ningún dato de las personas.

Uso (desde la raíz del repo, con el entorno activado):
    python -m ubika.referencias.sidpol                    # todo desde 2025-01-01
    python -m ubika.referencias.sidpol --desde 2026-06-01 # solo lo reciente (actualización mensual)
    python -m ubika.referencias.sidpol --solo agregados
"""
from __future__ import annotations

import argparse
import datetime as dt
import logging
import time
from typing import Iterator

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from ubika.config import cfg
from ubika.db import corrida, read_df, upsert
from ubika.texto import normalizar

log = logging.getLogger(__name__)

URL = ("https://services6.arcgis.com/lMIZrqiJkpM748BR/arcgis/rest/services/"
       "SIDPOL_DELITOS_TOTAL/FeatureServer/1/query")
PROVINCIAS = ("LIMA", "CALLAO")
PAGINA = 2000                       # maxRecordCount del servicio
SIN_UBICACION = ("CERO_AMBAS", "FUERA_PERU")

# Tipos que no describen un lugar inseguro: no se descargan como puntos (sí se cuentan en los agregados)
EXCLUIR_PUNTOS = (
    "INTERVENCION POLICIALES",
    "LEY 30096 DELITOS INFORMATICOS, MODIFICADA POR LA LEY 30171",
    "MIGRACIONES",
    "DENUNCIAS ESPECIALES",
)

# tipo_hecho → categoría de ubika
CATEGORIAS = {
    "PATRIMONIO (DELITO)": "patrimonio",
    "MODALIDAD POLICIAL DELITO CONTRA EL PATRIMONIO": "patrimonio",
    "VIDA, EL CUERPO Y LA SALUD (DELITO)": "violencia",
    "MODALIDAD POLICIAL DELITO CONTRA LA VIDA EL CUERPO Y LA SALUD": "violencia",
    "LIBERTAD (DELITO)": "violencia",
    "LEY DE VIOLENCIA CONTRA LA MUJER Y GRUPOS VULNERABLES": "violencia_familiar",
    "SEGURIDAD PUBLICA (DELITO)": "seguridad_publica",
    "TRAFICO ILICITO DE DROGAS": "seguridad_publica",
    "TRANQUILIDAD PUBLICA (DELITO)": "seguridad_publica",
    "FALTAS": "faltas",
}

CAMPOS_PUNTOS = ",".join([
    "OBJECTID", "ID_DGC_03", "fecha_hora_hecho", "fecha_actualizacion", "provincia_hecho",
    "distrito_hecho", "ubigeo_hecho_delito", "tipo_hecho", "subtipo_hecho", "modalidad_hecho",
    "lat_hecho", "long_hecho", "ESTADO_COORD",
])


def categoria(tipo_hecho: str | None) -> str:
    return CATEGORIAS.get((tipo_hecho or "").strip().upper(), "otros")


def _fecha(ms: int | None) -> dt.datetime | None:
    return None if ms is None else dt.datetime.fromtimestamp(ms / 1000, tz=dt.timezone.utc)


def _lista_sql(valores: tuple[str, ...]) -> str:
    return ", ".join("'" + v.replace("'", "''") + "'" for v in valores)


# ── HTTP ─────────────────────────────────────────────────────

def sesion() -> requests.Session:
    s = requests.Session()
    reintentos = Retry(total=6, backoff_factor=2, status_forcelist=(429, 500, 502, 503, 504),
                       allowed_methods=("GET",))
    s.mount("https://", HTTPAdapter(max_retries=reintentos))
    s.headers["User-Agent"] = "ubika/0.2 (datos abiertos MININTER; contacto en README)"
    return s


def consultar(s: requests.Session, **params) -> dict:
    r = s.get(URL, params={**params, "f": "json"}, timeout=120)
    r.raise_for_status()
    j = r.json()
    if "error" in j:
        raise RuntimeError(f"ArcGIS respondió con error: {j['error']}")
    return j


# ── Transformaciones (puras, probadas en tests/) ─────────────

def fila_punto(a: dict, alias: dict[str, str], caja: dict) -> dict | None:
    lat, lon = a.get("lat_hecho"), a.get("long_hecho")
    if lat is None or lon is None:
        return None
    if not (caja["lat_min"] <= lat <= caja["lat_max"] and caja["lon_min"] <= lon <= caja["lon_max"]):
        return None
    fecha = _fecha(a.get("fecha_hora_hecho"))
    if fecha is None or not a.get("ID_DGC_03"):
        return None
    local = fecha - dt.timedelta(hours=5)          # Lima, UTC-5 todo el año
    distrito_raw = (a.get("distrito_hecho") or "").strip()
    return {
        "id_dgc": a["ID_DGC_03"],
        "fecha_hecho": fecha,
        "anio": local.year,
        "mes": local.month,
        "provincia": (a.get("provincia_hecho") or "").strip(),
        "distrito_raw": distrito_raw,
        "distrito": alias.get(normalizar(distrito_raw)),
        "ubigeo_raw": a.get("ubigeo_hecho_delito"),
        "tipo_hecho": a.get("tipo_hecho"),
        "subtipo_hecho": a.get("subtipo_hecho"),
        "modalidad_hecho": a.get("modalidad_hecho"),
        "categoria": categoria(a.get("tipo_hecho")),
        "latitud": lat,
        "longitud": lon,
        "estado_coord": a.get("ESTADO_COORD"),
        "actualizado_fuente": _fecha(a.get("fecha_actualizacion")),
    }


def unir_conteos(totales: list[dict], con_ubicacion: list[dict], provincia: str, anio: int, mes: int,
                 alias: dict[str, str]) -> list[dict]:
    """Junta los conteos de todas las denuncias con los de las que tienen ubicación."""
    llave = lambda a: ((a.get("distrito_hecho") or "").strip(), (a.get("tipo_hecho") or "").strip())
    precisos = {llave(a): a["n"] for a in con_ubicacion}
    filas = {}
    for a in totales:
        d, t = llave(a)
        if not d or not t:
            continue
        f = filas.setdefault((d, t), {
            "provincia": provincia, "distrito_raw": d, "distrito": alias.get(normalizar(d)),
            "anio": anio, "mes": mes, "tipo_hecho": t, "categoria": categoria(t),
            "n_total": 0, "n_con_ubicacion": 0,
        })
        f["n_total"] += a["n"]
        f["n_con_ubicacion"] = precisos.get((d, t), 0)
    return list(filas.values())


def meses(desde: dt.date, hasta: dt.date) -> Iterator[tuple[int, int]]:
    y, m = desde.year, desde.month
    while (y, m) <= (hasta.year, hasta.month):
        yield y, m
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)


# ── Descargas ────────────────────────────────────────────────

def _alias() -> dict[str, str]:
    df = read_df("SELECT alias, distrito FROM distrito_alias")
    return dict(zip(df["alias"], df["distrito"]))


def descargar_puntos(s: requests.Session, desde: dt.date, alias: dict[str, str]) -> tuple[int, int]:
    caja = cfg()["geocoding"]["caja"]
    where_base = (
        f"provincia_hecho IN ({_lista_sql(PROVINCIAS)})"
        f" AND ESTADO_COORD NOT IN ({_lista_sql(SIN_UBICACION)})"
        f" AND tipo_hecho NOT IN ({_lista_sql(EXCLUIR_PUNTOS)})"
        f" AND fecha_hora_hecho >= TIMESTAMP '{desde.isoformat()} 00:00:00'"
    )
    ultimo, leidas, escritas, pagina = 0, 0, 0, 0
    while True:
        j = consultar(s, where=f"{where_base} AND OBJECTID > {ultimo}", outFields=CAMPOS_PUNTOS,
                      orderByFields="OBJECTID ASC", resultRecordCount=PAGINA, returnGeometry="false")
        feats = [f["attributes"] for f in j.get("features", [])]
        if not feats:
            break
        pagina += 1
        leidas += len(feats)
        ultimo = max(a["OBJECTID"] for a in feats)
        filas = {}
        for a in feats:
            f = fila_punto(a, alias, caja)
            if f:
                filas[f["id_dgc"]] = f             # dedup dentro de la página
        escritas += upsert("delitos_puntos", list(filas.values()), ["id_dgc"])
        if pagina % 10 == 0:
            log.info("  puntos: %s leídos, %s guardados (OBJECTID %s)", f"{leidas:,}", f"{escritas:,}", ultimo)
        time.sleep(0.3)
    log.info("Puntos listos: %s leídos, %s guardados", f"{leidas:,}", f"{escritas:,}")
    return leidas, escritas


def descargar_agregados(s: requests.Session, desde: dt.date, alias: dict[str, str]) -> int:
    stat = '[{"statisticType":"count","onStatisticField":"OBJECTID","outStatisticFieldName":"n"}]'
    total = 0
    for anio, mes in meses(desde, dt.date.today()):
        for prov in PROVINCIAS:
            base = f"provincia_hecho = '{prov}' AND año_hecho = {anio} AND mes_hecho = {mes}"
            q = dict(groupByFieldsForStatistics="distrito_hecho,tipo_hecho", outStatistics=stat)
            todos = consultar(s, where=base, **q)
            precisos = consultar(s, where=f"{base} AND ESTADO_COORD NOT IN ({_lista_sql(SIN_UBICACION)})", **q)
            for j in (todos, precisos):
                if j.get("exceededTransferLimit"):
                    raise RuntimeError(f"Demasiados grupos en {prov} {anio}-{mes:02d}; habría que partir la consulta")
            filas = unir_conteos([f["attributes"] for f in todos.get("features", [])],
                                 [f["attributes"] for f in precisos.get("features", [])],
                                 prov, anio, mes, alias)
            total += upsert("delitos_distrito_mes", filas, ["provincia", "distrito_raw", "anio", "mes", "tipo_hecho"])
            time.sleep(0.2)
        log.info("  agregados %s-%02d listos", anio, mes)
    return total


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(description="Descarga denuncias SIDPOL de Lima y Callao a Neon.")
    p.add_argument("--desde", type=dt.date.fromisoformat, default=dt.date(2025, 1, 1),
                   help="fecha inicial del hecho (AAAA-MM-DD). Por defecto 2025-01-01.")
    p.add_argument("--solo", choices=("puntos", "agregados"), help="descargar solo una de las dos tablas")
    args = p.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(levelname)-7s %(message)s", datefmt="%H:%M:%S")

    s, alias = sesion(), _alias()
    with corrida("referencias_sidpol", desde=args.desde, solo=args.solo) as c:
        leidas = escritas = 0
        if args.solo in (None, "agregados"):
            escritas += descargar_agregados(s, args.desde, alias)
        if args.solo in (None, "puntos"):
            l, e = descargar_puntos(s, args.desde, alias)
            leidas, escritas = leidas + l, escritas + e
        c.leidas, c.escritas = leidas, escritas
        sin_distrito = read_df("SELECT COUNT(*) AS n FROM delitos_distrito_mes WHERE distrito IS NULL")["n"].iat[0]
        if sin_distrito:
            c.mensaje = f"{sin_distrito} filas agregadas sin distrito reconocido (revisar distrito_alias)"
            log.warning(c.mensaje)


if __name__ == "__main__":
    main()

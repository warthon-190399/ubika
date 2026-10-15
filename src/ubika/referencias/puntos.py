"""
Carga los puntos de interés a Neon (tablas puntos_interes e inpe_domicilios).

Fuentes:
- CSV ya procesados en data/processed/ (colegios, salud, malls, Metropolitano, Línea 1, INPE).
  Ya tienen coordenadas: no se vuelve a consultar a Google.
- Comisarías: capa oficial "COMISARIAS BASICAS" del mapa de MININTER (134 en Lima y Callao).

Cada fuente se recarga completa (borra lo suyo e inserta) dentro de una transacción,
así que se puede correr las veces que haga falta.

    python -m ubika.referencias.puntos
    python -m ubika.referencias.puntos --solo comisarias
"""
from __future__ import annotations

import argparse
import logging
from pathlib import Path

import pandas as pd
import requests

from ubika.config import ROOT, cfg
from ubika.db import corrida, read_df, reemplazar
from ubika.texto import normalizar

log = logging.getLogger(__name__)

PROCESADOS = ROOT / "data" / "processed"
URL_COMISARIAS = ("https://services6.arcgis.com/lMIZrqiJkpM748BR/arcgis/rest/services/"
                  "MAPA_BASE/FeatureServer/7/query")


# ── Utilidades ───────────────────────────────────────────────

def en_lima(df: pd.DataFrame) -> pd.Series:
    c = cfg()["geocoding"]["caja"]
    return df["latitud"].between(c["lat_min"], c["lat_max"]) & df["longitud"].between(c["lon_min"], c["lon_max"])


def limpiar_coords(df: pd.DataFrame, nombre: str, quitar_coords_repetidas: bool = False) -> pd.DataFrame:
    """Descarta filas sin coordenadas o fuera de Lima/Callao y, si se pide, puntos repetidos."""
    df = df.copy()
    df["latitud"] = pd.to_numeric(df["latitud"], errors="coerce")
    df["longitud"] = pd.to_numeric(df["longitud"], errors="coerce")
    n0 = len(df)
    df = df.dropna(subset=["latitud", "longitud"])
    fuera = df[~en_lima(df)]
    if len(fuera):
        log.warning("  %s: %d fuera de Lima/Callao descartados (%s)", nombre, len(fuera),
                    ", ".join(map(str, fuera.get("nombre", pd.Series(dtype=str)).head(5))))
    df = df[en_lima(df)]
    if quitar_coords_repetidas:
        clave = df[["latitud", "longitud"]].round(5)
        rep = clave.duplicated(keep=False)
        if rep.any():
            log.warning("  %s: %d con coordenadas repetidas descartados (geocodificación dudosa): %s",
                        nombre, int(rep.sum()), ", ".join(map(str, df.loc[rep, "nombre"].head(6))))
        df = df[~rep]
    log.info("  %s: %d de %d filas válidas", nombre, len(df), n0)
    return df


def _alias() -> dict[str, str]:
    a = read_df("SELECT alias, distrito FROM distrito_alias")
    return dict(zip(a["alias"], a["distrito"]))


def _distrito(valor, alias: dict[str, str]) -> str | None:
    n = normalizar(valor)
    return alias.get(n, n or None)


def _puntos(df: pd.DataFrame, categoria: str, fuente: str, alias: dict[str, str],
            atributos: list[str] = ()) -> list[dict]:
    out = []
    for r in df.to_dict("records"):
        out.append({
            "categoria": categoria,
            "nombre": (str(r.get("nombre") or "").strip().title() or None),
            "distrito": _distrito(r.get("distrito"), alias) if r.get("distrito") is not None else None,
            "latitud": float(r["latitud"]),
            "longitud": float(r["longitud"]),
            "fuente": fuente,
            "atributos": {k: r[k] for k in atributos if k in r and pd.notna(r[k])},
        })
    return out


def _leer(nombre: str) -> pd.DataFrame:
    ruta = PROCESADOS / f"{nombre}_processed.csv"
    if not ruta.exists():
        raise FileNotFoundError(f"No encuentro {ruta}. Este cargador usa los CSV de data/processed/.")
    return pd.read_csv(ruta, low_memory=False)


# ── Transformaciones por fuente (puras) ──────────────────────

def colegios(df: pd.DataFrame, alias) -> list[dict]:
    df = df.rename(columns={"nivel__modalidad": "nivel", "gestion__dependencia": "gestion"})
    df = limpiar_coords(df, "colegios").drop_duplicates(subset=["nombre", "latitud", "longitud"])
    return _puntos(df, "colegio", "minedu", alias, ["nivel", "gestion", "direccion"])


def salud(df: pd.DataFrame, alias) -> list[dict]:
    # Varios establecimientos quedaron con la misma coordenada al geocodificar: se deja uno por punto
    df = limpiar_coords(df, "salud").drop_duplicates(subset=["latitud", "longitud"])
    return _puntos(df, "salud", "susalud_ipress", alias, ["direccion"])


def malls(df: pd.DataFrame, alias) -> list[dict]:
    df = limpiar_coords(df, "malls")
    df = df.assign(_k=df["nombre"].map(normalizar), _la=df["latitud"].round(4), _lo=df["longitud"].round(4))
    df = df.drop_duplicates(subset=["_k", "_la", "_lo"])
    return _puntos(df, "mall", "osm", alias)


def metropolitano(df: pd.DataFrame, alias) -> list[dict]:
    df = limpiar_coords(df, "metropolitano").drop_duplicates(subset=["latitud", "longitud"])
    return _puntos(df, "metropolitano", "wikipedia_geocodificado", alias)


def linea1(df: pd.DataFrame, alias) -> list[dict]:
    # Si dos estaciones comparten coordenada, al menos una está mal ubicada: se descartan ambas
    df = limpiar_coords(df, "metro línea 1", quitar_coords_repetidas=True)
    return _puntos(df, "metro", "wikipedia_geocodificado", alias)


def inpe(df: pd.DataFrame, alias) -> list[dict]:
    df = limpiar_coords(df, "inpe")
    return [{
        "periodo": None if pd.isna(r.get("periodo")) else str(int(r["periodo"])),
        "delito_generico": r.get("delito_generico"),
        "delito_especifico": r.get("delito_especifico"),
        "distrito": _distrito(r.get("distrito"), alias),
        "latitud": float(r["latitud"]),
        "longitud": float(r["longitud"]),
    } for r in df.to_dict("records")]


def comisarias_mininter(features: list[dict], alias) -> list[dict]:
    df = pd.DataFrame([f["attributes"] for f in features]).rename(
        columns={"Latitud": "latitud", "Longitud": "longitud", "comisaria": "nombre", "tipo_comisaria": "tipo"})
    df = limpiar_coords(df, "comisarías").drop_duplicates(subset=["cod_cpnp"])
    return _puntos(df, "comisaria", "mininter", alias, ["tipo", "cod_cpnp"])


def descargar_comisarias() -> list[dict]:
    r = requests.get(URL_COMISARIAS, timeout=60, params={
        "where": "provincia IN ('LIMA','CALLAO')", "returnGeometry": "false", "resultRecordCount": 2000,
        "outFields": "comisaria,tipo_comisaria,provincia,distrito,Latitud,Longitud,cod_cpnp", "f": "json"})
    r.raise_for_status()
    j = r.json()
    if "error" in j:
        raise RuntimeError(f"ArcGIS respondió con error: {j['error']}")
    return j.get("features", [])


# ── Orquestación ─────────────────────────────────────────────

CSV = {   # nombre del CSV → (transformación, categoría, fuente)
    "colegios":      (colegios,      "colegio",       "minedu"),
    "hospitales":    (salud,         "salud",         "susalud_ipress"),
    "malls":         (malls,         "mall",          "osm"),
    "metropolitano": (metropolitano, "metropolitano", "wikipedia_geocodificado"),
    "tren":          (linea1,        "metro",         "wikipedia_geocodificado"),
}


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(description="Carga puntos de interés y comisarías a Neon.")
    p.add_argument("--solo", choices=("csv", "comisarias", "inpe"))
    args = p.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(levelname)-7s %(message)s", datefmt="%H:%M:%S")

    alias = _alias()
    with corrida("referencias_puntos", solo=args.solo) as c:
        total = 0
        if args.solo in (None, "csv"):
            for archivo, (fn, cat, fuente) in CSV.items():
                filas = fn(_leer(archivo), alias)
                total += reemplazar("puntos_interes", "categoria = :c AND fuente = :f",
                                    {"c": cat, "f": fuente}, filas)
        if args.solo in (None, "comisarias"):
            filas = comisarias_mininter(descargar_comisarias(), alias)
            total += reemplazar("puntos_interes", "categoria = 'comisaria'", {}, filas)
        if args.solo in (None, "inpe"):
            total += reemplazar("inpe_domicilios", "TRUE", {}, inpe(_leer("inpe"), alias))
        c.escritas = total
    resumen = read_df("SELECT categoria, fuente, COUNT(*) AS n FROM puntos_interes GROUP BY 1, 2 ORDER BY 1")
    log.info("Puntos de interés en Neon:\n%s", resumen.to_string(index=False))


if __name__ == "__main__":
    main()

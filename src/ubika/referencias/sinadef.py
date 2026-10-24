"""
Defunciones SINADEF (MINSA) de residentes de Lima Metropolitana y Callao.

Fuente: "Información de Fallecidos del Sistema Informático Nacional de Defunciones - SINADEF"
(https://www.datosabiertos.gob.pe/dataset/informaci%C3%B3n-de-fallecidos-del-sistema-inform%C3%A1tico-nacional-de-defunciones-sinadef-ministerio).
Un CSV de todo el Perú (~380 MB, separado por '|', UTF-8), un certificado de defunción por fila.

Qué se guarda:
- defunciones_distrito_mes: conteos por distrito de DOMICILIO del fallecido, mes y tipo de muerte
  (columna MUERTE VIOLENTA). El archivo no trae el distrito donde ocurrió la muerte.
  Las tasas por 100 mil habitantes salen de las vistas de sql/10_defunciones.sql.
- defunciones_edad_distrito: por distrito, año y tipo (natural o violenta), cuántos tienen edad,
  la suma de edades y cuántos murieron con menos de 1, 65 o más y 80 o más años
  (sql/12_edad_defuncion.sql; si la tabla no existe todavía, se salta con un aviso).

No se guarda ningún dato de las personas: solo conteos y sumas por distrito.
Las tablas se recargan completas en cada corrida, así que se puede correr las veces que haga falta.

Uso (desde la raíz del repo, con el entorno activado):
    python -m ubika.referencias.sinadef                          # descarga (si no está) y carga
    python -m ubika.referencias.sinadef --descargar              # vuelve a bajar el CSV
    python -m ubika.referencias.sinadef --archivo ruta/al/archivo.csv
"""
from __future__ import annotations

import argparse
import logging
from collections import Counter
from pathlib import Path
from typing import IO, Iterable

import pandas as pd
import requests

from ubika.config import ROOT
from ubika.db import corrida, read_df, reemplazar
from ubika.texto import normalizar

log = logging.getLogger(__name__)

URL = "https://drive.minsa.gob.pe/s/PigmdwnCGEdyqos/download"
CACHE = ROOT / "data" / "raw" / "sinadef" / "fallecidos_sinadef.csv"
PROVINCIAS = ("LIMA", "CALLAO")
SEP = "|"

# Columnas que se leen, por su nombre normalizado (el original trae tildes y Ñ: 'AÑO' → 'ano')
COLUMNAS = {
    "departamento domicilio": "departamento",
    "provincia domicilio": "provincia",
    "distrito domicilio": "distrito_raw",
    "ano": "anio",
    "mes": "mes",
    "muerte violenta": "muerte_violenta",
    "edad": "edad",
    "tiempo edad": "tiempo_edad",
}

# TIEMPO EDAD distinto de AÑOS: menores de un año, cuentan como 0
MENOS_DE_UN_ANIO = {"meses", "dias", "horas", "minutos", "segundos"}

# MUERTE VIOLENTA → tipo_muerte. Lo que no está aquí ('SIN REGISTRO', vacío) es muerte no violenta.
TIPOS = {
    "HOMICIDIO": "homicidio",
    "ACCIDENTE DE TRANSITO": "transito",
    "SUICIDIO": "suicidio",
    "OTRO ACCIDENTE": "otro_accidente",
    "ACCIDENTE DE TRABAJO": "accidente_trabajo",
    "NO SE CONOCE": "violenta_sin_tipo",
}


def tipo_muerte(valor: object) -> str:
    return TIPOS.get(normalizar(valor).upper(), "no_violenta")


def edad_anios(edad: object, tiempo: object) -> float | None:
    """Edad en años: 'AÑOS' → el número (0–120); días, meses, horas… → 0; sin dato o fuera de rango → None."""
    unidad = normalizar(tiempo)
    if unidad in MENOS_DE_UN_ANIO:
        return 0.0
    if unidad != "anos":
        return None
    try:
        x = float(str(edad).strip())
    except ValueError:
        return None
    return x if 0 <= x <= 120 else None


# ── Transformaciones (puras, probadas en tests/) ─────────────

def leer(fuente: str | Path | IO, chunksize: int = 200_000) -> Iterable[pd.DataFrame]:
    """Lee el CSV por partes, solo las columnas que se usan y con nombres cortos."""
    partes = pd.read_csv(fuente, sep=SEP, dtype=str, encoding="utf-8", keep_default_na=False,
                         usecols=lambda c: normalizar(c) in COLUMNAS, chunksize=chunksize)
    for df in partes:
        yield df.rename(columns=lambda c: COLUMNAS[normalizar(c)])


def contar(partes: Iterable[pd.DataFrame]) -> Counter:
    """Cuenta defunciones de Lima y Callao por (provincia, distrito_raw, año, mes, tipo_muerte)."""
    return agregar(partes)[0]


def agregar(partes: Iterable[pd.DataFrame]) -> tuple[Counter, dict]:
    """
    Una sola pasada por el CSV:
    - conteo: Counter (provincia, distrito_raw, año, mes, tipo_muerte) → n
    - edades: (provincia, distrito_raw, año, natural|violenta) → {n, suma, menores_1, n65, n80}
    """
    conteo: Counter = Counter()
    edades: dict = {}
    for df in partes:
        for c in ("departamento", "provincia", "distrito_raw"):
            df[c] = df[c].str.strip().str.upper()
        df = df[df["departamento"].isin(PROVINCIAS) & df["provincia"].isin(PROVINCIAS)]
        df = df.assign(anio=pd.to_numeric(df["anio"], errors="coerce"),
                       mes=pd.to_numeric(df["mes"], errors="coerce"))
        df = df[df["anio"].notna() & df["mes"].between(1, 12)]
        df = df.assign(distrito_raw=df["distrito_raw"].replace("", "SIN REGISTRO"),
                       tipo_muerte=df["muerte_violenta"].map(tipo_muerte))
        g = df.groupby(["provincia", "distrito_raw", "anio", "mes", "tipo_muerte"]).size()
        for (prov, dist, anio, mes, tipo), n in g.items():
            conteo[(prov, dist, int(anio), int(mes), tipo)] += int(n)
        if "edad" in df and "tiempo_edad" in df:
            e = pd.Series([edad_anios(a, t) for a, t in zip(df["edad"], df["tiempo_edad"])], index=df.index, dtype=float)
            df = df.assign(edad_anios=e, tipo=df["tipo_muerte"].eq("no_violenta").map({True: "natural", False: "violenta"}))
            df = df[df["edad_anios"].notna()]
            g = df.groupby(["provincia", "distrito_raw", "anio", "tipo"])["edad_anios"].agg(
                n="size", suma="sum", menores_1=lambda x: int((x < 1).sum()),
                n65=lambda x: int((x >= 65).sum()), n80=lambda x: int((x >= 80).sum()))
            for (prov, dist, anio, tipo), r in g.iterrows():
                acc = edades.setdefault((prov, dist, int(anio), tipo), {"n": 0, "suma": 0.0, "menores_1": 0, "n65": 0, "n80": 0})
                for k in acc:
                    acc[k] += r[k]
    return conteo, edades


def filas(conteo: Counter, alias: dict[str, str]) -> list[dict]:
    return [{
        "provincia": prov, "distrito_raw": dist, "distrito": alias.get(normalizar(dist)),
        "anio": anio, "mes": mes, "tipo_muerte": tipo, "n": n,
    } for (prov, dist, anio, mes, tipo), n in sorted(conteo.items())]


def filas_edad(edades: dict, alias: dict[str, str]) -> list[dict]:
    return [{
        "provincia": prov, "distrito_raw": dist, "distrito": alias.get(normalizar(dist)), "anio": anio, "tipo": tipo,
        "n_con_edad": int(e["n"]), "suma_edad": round(float(e["suma"]), 1), "n_menores_1": int(e["menores_1"]),
        "n_65_mas": int(e["n65"]), "n_80_mas": int(e["n80"]),
    } for (prov, dist, anio, tipo), e in sorted(edades.items()) if e["n"] > 0]


# ── Descarga ─────────────────────────────────────────────────

def descargar(destino: Path = CACHE) -> Path:
    """Baja el CSV completo a data/raw/sinadef/ (no se versiona)."""
    destino.parent.mkdir(parents=True, exist_ok=True)
    tmp = destino.with_suffix(".part")
    log.info("Descargando SINADEF (~380 MB) de %s", URL)
    # El portal bloquea clientes sin User-Agent de navegador
    with requests.get(URL, stream=True, timeout=300,
                      headers={"User-Agent": "Mozilla/5.0 (ubika; datos abiertos MINSA)"}) as r:
        r.raise_for_status()
        if "text/csv" not in r.headers.get("Content-Type", ""):
            raise RuntimeError(f"La descarga no es un CSV (Content-Type {r.headers.get('Content-Type')}); "
                               "revisar el enlace en datosabiertos.gob.pe")
        with open(tmp, "wb") as f:
            for bloque in r.iter_content(chunk_size=1 << 20):
                f.write(bloque)
    tmp.replace(destino)
    log.info("  guardado en %s (%.0f MB)", destino, destino.stat().st_size / 1e6)
    return destino


def _existe(tabla: str) -> bool:
    return bool(read_df("SELECT to_regclass(:t) IS NOT NULL AS ok", {"t": tabla})["ok"].iat[0])


def _alias() -> dict[str, str]:
    df = read_df("SELECT alias, distrito FROM distrito_alias")
    return dict(zip(df["alias"], df["distrito"]))


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(description="Carga defunciones SINADEF de Lima y Callao a Neon.")
    p.add_argument("--archivo", type=Path, help="CSV ya descargado (por defecto data/raw/sinadef/)")
    p.add_argument("--descargar", action="store_true", help="volver a bajar el CSV aunque ya exista")
    args = p.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(levelname)-7s %(message)s", datefmt="%H:%M:%S")

    with corrida("referencias_sinadef", archivo=args.archivo) as c:
        archivo = args.archivo or CACHE
        if args.archivo is None and (args.descargar or not archivo.exists()):
            descargar(archivo)
        conteo, edades = agregar(leer(archivo))
        alias = _alias()
        registros = filas(conteo, alias)
        c.leidas = sum(conteo.values())
        c.escritas = reemplazar("defunciones_distrito_mes", "TRUE", {}, registros)
        if _existe("defunciones_edad_distrito"):
            n_edad = reemplazar("defunciones_edad_distrito", "TRUE", {}, filas_edad(edades, alias))
            log.info("Edad al morir: %s filas en defunciones_edad_distrito", f"{n_edad:,}")
        else:
            log.warning("No existe defunciones_edad_distrito: corre sql/12_edad_defuncion.sql en Neon para la capa de longevidad")
        anios = sorted({r["anio"] for r in registros})
        log.info("Listo: %s defunciones de Lima y Callao (%s–%s) en %s filas",
                 f"{c.leidas:,}", anios[0] if anios else "-", anios[-1] if anios else "-", f"{c.escritas:,}")
        sin_distrito = sorted({r["distrito_raw"] for r in registros
                               if r["distrito"] is None and r["distrito_raw"] != "SIN REGISTRO"})
        if sin_distrito:
            c.mensaje = f"Distritos sin reconocer (revisar distrito_alias): {', '.join(sin_distrito)}"
            log.warning(c.mensaje)


if __name__ == "__main__":
    main()

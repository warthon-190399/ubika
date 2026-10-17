"""
Paso 1 del pipeline: raw_listings + raw_detalles → propiedades + avisos.

1. Toma la última versión de cada aviso (URL) y su ficha, si existe.
2. Convierte textos a números (pipeline/parseo.py) y descarta lo implausible (config.yaml → limpieza).
3. Agrupa avisos que son el mismo inmueble:
   - misma operación, distrito, dormitorios y baños,
   - área a ±tolerancia_area_m2 y precio a ±tolerancia_precio,
   - y misma dirección normalizada o coordenadas a menos de 60 m.
4. Escribe propiedades (un inmueble) y avisos (sus URLs). El prop_id se mantiene entre corridas:
   si alguna URL del grupo ya tenía prop_id, se reutiliza.
"""
from __future__ import annotations

import logging
import math
import uuid

import pandas as pd

from ubika.config import cfg
from ubika.db import execute, read_df, upsert
from ubika.pipeline import parseo
from ubika.texto import normalizar

log = logging.getLogger(__name__)

DIST_MISMO_PUNTO_M = 60


def _alias() -> dict[str, str]:
    a = read_df("SELECT alias, distrito FROM distrito_alias")
    return dict(zip(a["alias"], a["distrito"]))


def leer_crudos() -> pd.DataFrame:
    """Última foto de cada URL, con su ficha (si se scrapeó) y la primera/última fecha en que se vio."""
    return read_df("""
        WITH ult AS (
            SELECT DISTINCT ON (url) *
            FROM raw_listings
            ORDER BY url, scrape_date DESC, raw_id DESC
        ), fechas AS (
            SELECT url, MIN(scrape_date) AS primera_vez, MAX(scrape_date) AS ultima_vez
            FROM raw_listings GROUP BY url
        )
        SELECT u.fuente, u.operacion, u.url, u.precio_raw, u.mantenimiento_raw AS mant_listado,
               u.direccion_raw, u.ubicacion_raw, u.area_raw, u.dorm_raw AS dorm_listado,
               u.banos_raw AS banos_listado, u.estac_raw AS estac_listado, u.latitud, u.longitud,
               f.primera_vez, f.ultima_vez,
               d.estado AS estado_detalle, d.tipo_inmueble_raw, d.precio_pen AS pen_detalle,
               d.precio_usd AS usd_detalle, d.mantenimiento_raw AS mant_detalle, d.area_total_raw,
               d.dorm_raw AS dorm_detalle, d.banos_raw AS banos_detalle, d.estac_raw AS estac_detalle,
               d.antiguedad_raw, d.inmobiliaria_raw, d.fecha_publicacion, d.visibilidad_direccion,
               d.ubicacion_portal
        FROM ult u
        JOIN fechas f USING (url)
        LEFT JOIN raw_detalles d USING (url)
    """)


# ── Transformación (pura) ────────────────────────────────────

def _primero(*vals):
    for v in vals:
        if v is not None and not (isinstance(v, float) and math.isnan(v)):
            return v
    return None


def limpiar(crudos: pd.DataFrame, alias: dict[str, str], conf: dict | None = None) -> tuple[pd.DataFrame, dict]:
    """Devuelve (avisos limpios, conteo de descartes por motivo)."""
    conf = conf or cfg()
    lim, caja = conf["limpieza"], conf["geocoding"]["caja"]
    filas, descartes = [], {}
    crudos = crudos.astype(object).where(crudos.notna(), None)      # NaN de pandas → None

    def descartar(motivo):
        descartes[motivo] = descartes.get(motivo, 0) + 1

    for r in crudos.to_dict("records"):
        if r.get("estado_detalle") == "no_disponible":
            descartar("aviso dado de baja")
            continue
        pen_l, usd_l = parseo.precios(r.get("precio_raw"))
        pen = _primero(r.get("pen_detalle"), pen_l)
        usd = _primero(r.get("usd_detalle"), usd_l)
        area = _primero(parseo.area_m2(r.get("area_total_raw")), parseo.area_m2(r.get("area_raw")))
        dist = parseo.distrito(r.get("ubicacion_raw"), alias)
        if dist is None and isinstance(r.get("ubicacion_portal"), dict):
            dist = alias.get(normalizar(r["ubicacion_portal"].get("name")))
        lat, lon = r.get("latitud"), r.get("longitud")
        if lat is not None and not (caja["lat_min"] <= lat <= caja["lat_max"] and caja["lon_min"] <= lon <= caja["lon_max"]):
            lat = lon = None
        filas.append({
            "fuente": r["fuente"], "operacion": r["operacion"], "url": r["url"],
            "tipo_inmueble": parseo.tipo_inmueble(r.get("tipo_inmueble_raw")),
            "precio_pen": pen, "precio_usd": usd,
            "mantenimiento_pen": _primero(parseo.mantenimiento(r.get("mant_detalle")),
                                          parseo.mantenimiento(r.get("mant_listado"))),
            "area_m2": area,
            "num_dorm": _primero(parseo.entero(r.get("dorm_detalle")), parseo.entero(r.get("dorm_listado"))),
            "num_banios": _primero(parseo.entero(r.get("banos_detalle")), parseo.entero(r.get("banos_listado"))),
            # el portal omite el estacionamiento cuando no hay
            "num_estac": _primero(parseo.entero(r.get("estac_detalle")), parseo.entero(r.get("estac_listado")), 0),
            "antiguedad_anios": parseo.antiguedad(r.get("antiguedad_raw")),
            "direccion": (r.get("direccion_raw") or "").strip() or None,
            "distrito": dist,
            "latitud": lat, "longitud": lon,
            "geo_precision": None if lat is None else (
                "portal_exacta" if r.get("visibilidad_direccion") == "EXACT" else "portal"),
            "inmobiliaria": (r.get("inmobiliaria_raw") or "").strip() or None,
            "fecha_publicacion": r.get("fecha_publicacion"),
            "primera_vez": r["primera_vez"], "ultima_vez": r["ultima_vez"],
        })

    df = pd.DataFrame(filas)
    if df.empty:
        return df, descartes

    # Moneda faltante: se completa con el tipo de cambio implícito de los avisos que traen ambas
    ambos = df.dropna(subset=["precio_pen", "precio_usd"])
    tc = float((ambos["precio_pen"] / ambos["precio_usd"]).median()) if len(ambos) else None
    if tc:
        df.loc[df["precio_pen"].isna() & df["precio_usd"].notna(), "precio_pen"] = df["precio_usd"] * tc
        df.loc[df["precio_usd"].isna() & df["precio_pen"].notna(), "precio_usd"] = df["precio_pen"] / tc

    # Plausibilidad
    a_min, a_max = lim["area_m2"]
    ok = pd.Series(True, index=df.index)
    for motivo, mask in [
        ("sin precio", df["precio_pen"].isna()),
        ("sin área", df["area_m2"].isna()),
        (f"área fuera de {a_min}–{a_max} m²", ~df["area_m2"].between(a_min, a_max) & df["area_m2"].notna()),
        ("precio fuera de rango", df.apply(
            lambda x: x["precio_pen"] == x["precio_pen"] and not (
                lim["precio_pen"][x["operacion"]][0] <= x["precio_pen"] <= lim["precio_pen"][x["operacion"]][1]),
            axis=1)),
        ("distrito no reconocido", df["distrito"].isna()),
    ]:
        nuevo = mask & ok
        if nuevo.any():
            descartes[motivo] = descartes.get(motivo, 0) + int(nuevo.sum())
        ok &= ~mask
    df = df[ok].copy()
    df["direccion_norm"] = [normalizar(f"{d or ''}, {dist}").strip(", ") for d, dist in zip(df["direccion"], df["distrito"])]
    return df.reset_index(drop=True), descartes


def _metros(lat1, lon1, lat2, lon2) -> float:
    if None in (lat1, lon1, lat2, lon2) or any(map(lambda v: v != v, (lat1, lon1, lat2, lon2))):
        return math.inf
    dy = (lat1 - lat2) * 110_600
    dx = (lon1 - lon2) * 108_900
    return math.hypot(dx, dy)


def agrupar(df: pd.DataFrame, tol_precio: float, tol_area: float) -> list[int]:
    """Etiqueta de grupo para cada fila: filas con la misma etiqueta son el mismo inmueble."""
    padre = list(range(len(df)))

    def raiz(i):
        while padre[i] != i:
            padre[i] = padre[padre[i]]
            i = padre[i]
        return i

    filas = df.to_dict("records")
    bloques: dict[tuple, list[int]] = {}
    for i, r in enumerate(filas):
        bloques.setdefault((r["operacion"], r["distrito"], r["num_dorm"], r["num_banios"]), []).append(i)
    for idx in bloques.values():
        for a_pos, i in enumerate(idx):
            for j in idx[a_pos + 1:]:
                a, b = filas[i], filas[j]
                if abs(a["area_m2"] - b["area_m2"]) > tol_area:
                    continue
                if abs(a["precio_pen"] - b["precio_pen"]) > tol_precio * max(a["precio_pen"], b["precio_pen"]):
                    continue
                misma_dir = bool(a["direccion"]) and a["direccion_norm"] == b["direccion_norm"]
                cerca = _metros(a["latitud"], a["longitud"], b["latitud"], b["longitud"]) <= DIST_MISMO_PUNTO_M
                if misma_dir or cerca:
                    padre[raiz(i)] = raiz(j)
    return [raiz(i) for i in range(len(df))]


def consolidar(df: pd.DataFrame, existentes: dict[str, str]) -> tuple[list[dict], list[dict]]:
    """Un registro por grupo para propiedades, y los avisos (URL → prop_id)."""
    props, avisos = [], []
    for _, g in df.groupby("grupo", sort=False):
        g = g.sort_values(["ultima_vez", "primera_vez"], ascending=[False, True])
        previos = [existentes[u] for u in g["url"] if u in existentes]
        canon = g.sort_values(["primera_vez", "url"]).iloc[0]["url"]
        prop_id = previos[0] if previos else str(uuid.uuid5(uuid.NAMESPACE_URL, canon))
        rep = g.iloc[0].to_dict()                         # el aviso visto más recientemente
        # completar con otros avisos del grupo lo que el representante no tenga
        for col in ("antiguedad_anios", "mantenimiento_pen", "inmobiliaria", "fecha_publicacion", "latitud",
                    "longitud", "geo_precision"):
            if _primero(rep.get(col)) is None:
                rep[col] = _primero(*g[col].tolist())
        if rep["latitud"] is None or rep["longitud"] is None:
            rep["latitud"] = rep["longitud"] = rep["geo_precision"] = None
        props.append({
            "prop_id": prop_id,
            **{k: rep[k] for k in ("operacion", "tipo_inmueble", "precio_pen", "precio_usd", "mantenimiento_pen",
                                   "area_m2", "num_dorm", "num_banios", "num_estac", "antiguedad_anios",
                                   "direccion", "direccion_norm", "distrito", "latitud", "longitud",
                                   "geo_precision", "inmobiliaria", "fecha_publicacion")},
            "primera_vez": g["primera_vez"].min(),
            "ultima_vez": g["ultima_vez"].max(),
        })
        for r in g.to_dict("records"):
            avisos.append({"url": r["url"], "fuente": r["fuente"], "prop_id": prop_id,
                           "primera_vez": r["primera_vez"], "ultima_vez": r["ultima_vez"]})
    return props, avisos


# ── Orquestación ─────────────────────────────────────────────

def correr(c) -> dict:
    conf = cfg()
    crudos = leer_crudos()
    c.leidas = len(crudos)
    limpios, descartes = limpiar(crudos, _alias(), conf)
    for motivo, n in sorted(descartes.items(), key=lambda x: -x[1]):
        log.info("  descartados · %s: %d", motivo, n)
    if limpios.empty:
        log.warning("  No quedó ningún aviso válido.")
        return {"descartes": descartes}

    d = conf["limpieza"]["dedup"]
    limpios["grupo"] = agrupar(limpios, d["tolerancia_precio"], d["tolerancia_area_m2"])
    ex = read_df("SELECT url, prop_id::text AS prop_id FROM avisos")
    props, avisos = consolidar(limpios, dict(zip(ex["url"], ex["prop_id"])))

    upsert("propiedades", props, ["prop_id"])
    upsert("avisos", avisos, ["url"])
    # Activo = apareció en el último scraping de su operación
    execute("""
        UPDATE propiedades p SET activo = (p.ultima_vez = m.ultima)
        FROM (SELECT operacion, MAX(scrape_date) AS ultima FROM raw_listings GROUP BY operacion) m
        WHERE p.operacion = m.operacion
    """)
    unidos = len(avisos) - len(props)
    log.info("  %d avisos válidos → %d inmuebles (%d repetidos unidos)", len(avisos), len(props), unidos)
    c.escritas = len(props)
    c.mensaje = f"descartes: {descartes}; repetidos unidos: {unidos}"
    return {"descartes": descartes, "inmuebles": len(props), "repetidos": unidos}

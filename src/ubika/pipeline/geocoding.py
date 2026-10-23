"""
Paso 2 del pipeline: coordenadas para los inmuebles que el portal no ubicó, o cuyo pin la
limpieza descartó por caer lejos del distrito declarado (esos solo se aceptan dentro del distrito).

Cada texto se consulta a Google una sola vez (tabla geocode_cache). Resultados fuera de
Lima/Callao o de baja precisión a nivel de ciudad se marcan y no se usan.
"""
from __future__ import annotations

import logging
import time

from ubika.config import cfg, google_api_key
from ubika.db import execute, read_df, upsert
from ubika.pipeline.limites import cargar as cargar_limites, metros_a_distrito

log = logging.getLogger(__name__)

# Google devuelve el centro del distrito/ciudad con estos tipos: no sirven para un inmueble
TIPOS_DEMASIADO_GENERALES = {"locality", "administrative_area_level_1", "administrative_area_level_2",
                             "administrative_area_level_3", "country", "political"}


def consulta(direccion: str | None, distrito_nombre: str | None) -> str | None:
    if not direccion and not distrito_nombre:
        return None
    partes = [p for p in (direccion, distrito_nombre) if p]
    return ", ".join(partes) + cfg()["geocoding"]["sufijo"]


def interpretar(resultados: list[dict]) -> dict:
    """Respuesta de Google → fila de geocode_cache (sin la consulta)."""
    if not resultados:
        return {"estado": "sin_resultado"}
    r = resultados[0]
    loc = r["geometry"]["location"]
    caja = cfg()["geocoding"]["caja"]
    if not (caja["lat_min"] <= loc["lat"] <= caja["lat_max"] and caja["lon_min"] <= loc["lng"] <= caja["lon_max"]):
        return {"estado": "fuera_de_lima", "latitud": loc["lat"], "longitud": loc["lng"]}
    tipos = set(r.get("types", []))
    loc_type = r["geometry"].get("location_type")
    if tipos and tipos <= TIPOS_DEMASIADO_GENERALES:
        loc_type = "SOLO_DISTRITO"
    return {"estado": "ok", "latitud": loc["lat"], "longitud": loc["lng"], "location_type": loc_type,
            "direccion_google": r.get("formatted_address")}


def correr(c) -> dict:
    pendientes = read_df("""
        SELECT p.prop_id::text AS prop_id, p.direccion, p.distrito, p.correccion_ubicacion,
               d.nombre AS distrito_nombre
        FROM propiedades p LEFT JOIN distritos d USING (distrito)
        WHERE p.latitud IS NULL
    """)
    c.leidas = len(pendientes)
    if pendientes.empty:
        log.info("  Todos los inmuebles ya tienen coordenadas.")
        return {"geocodificados": 0}

    pendientes["consulta"] = [consulta(a, b) for a, b in zip(pendientes["direccion"], pendientes["distrito_nombre"])]
    pendientes = pendientes.dropna(subset=["consulta"])
    en_cache = read_df("SELECT consulta FROM geocode_cache WHERE consulta = ANY(:q)",
                       {"q": pendientes["consulta"].unique().tolist()})
    nuevas = sorted(set(pendientes["consulta"]) - set(en_cache["consulta"]))
    log.info("  %d inmuebles sin coordenadas · %d consultas nuevas a Google", len(pendientes), len(nuevas))

    if nuevas:
        import googlemaps
        gmaps = googlemaps.Client(key=google_api_key())
        region, pausa = cfg()["geocoding"]["region"], cfg()["geocoding"]["pausa_seg"]
        for q in nuevas:
            try:
                fila = interpretar(gmaps.geocode(q, region=region))
            except Exception as exc:
                log.warning("  Google falló con %r: %s", q, exc)
                fila = {"estado": "error"}
            upsert("geocode_cache", [{"consulta": q, **fila}], ["consulta"])
            time.sleep(pausa)

    # Pines que la limpieza descartó por caer lejos de su distrito: el resultado de Google tiene que
    # caer en ese distrito (o a menos del mismo umbral); si no, el inmueble queda sin coordenadas
    corregir = pendientes[pendientes["correccion_ubicacion"] == "pin_lejos_del_distrito"]
    rechazadas = set()
    if not corregir.empty:
        limites = cargar_limites(cfg()["limpieza"]["limites"])
        max_fuera = cfg()["limpieza"]["max_metros_fuera_distrito"]
        cache = read_df("SELECT consulta, latitud, longitud FROM geocode_cache WHERE consulta = ANY(:q) AND estado = 'ok'",
                        {"q": corregir["consulta"].unique().tolist()}).set_index("consulta")
        for r in corregir.to_dict("records"):
            g = cache.loc[r["consulta"]] if r["consulta"] in cache.index else None
            fuera = None if g is None else metros_a_distrito(g["latitud"], g["longitud"], r["distrito"], limites)
            if fuera is not None and fuera > max_fuera:
                rechazadas.add(r["prop_id"])
        log.info("  %d pines descartados por estar lejos de su distrito; Google tampoco ubica %d dentro",
                 len(corregir), len(rechazadas))

    # Aplicar lo que haya en caché (solo resultados útiles)
    n = 0
    for r in pendientes.to_dict("records"):
        if r["prop_id"] in rechazadas:
            continue
        n += execute("""
            UPDATE propiedades p
            SET latitud = g.latitud, longitud = g.longitud, geo_precision = 'google_' || lower(g.location_type)
            FROM geocode_cache g
            WHERE p.prop_id = CAST(:id AS UUID) AND g.consulta = :q
              AND g.estado = 'ok' AND g.location_type <> 'SOLO_DISTRITO'
        """, {"id": r["prop_id"], "q": r["consulta"]})
    log.info("  %d inmuebles ubicados con Google; %d siguen sin coordenadas (no salen en el mapa)",
             n, len(pendientes) - n)
    c.escritas = n
    return {"geocodificados": n}

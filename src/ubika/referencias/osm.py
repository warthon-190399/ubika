"""
Carga desde OpenStreetMap (API Overpass) lo que hace falta para la calidad de vida:

- Parques (leisure=park) con su área en m²            → puntos_interes, categoria 'parque'
- Comercio de todos los días: mercados, supermercados, farmacias, restaurantes y cafés,
  gimnasios y bancos                                    → puntos_interes
- Vías grandes (autopistas, vías expresas, principales, secundarias) y la pista del aeropuerto,
  muestreadas cada ~40 m                                → ruido_fuentes (para estimar el ruido)
- Paraderos de los Corredores Complementarios (rutas de la red SIT de la ATU: Amarillo, Rojo,
  Azul y Morado); los nodos de un mismo paradero (andén y punto de parada de cada sentido) se
  juntan en uno                                         → puntos_interes, categoria 'corredor'

Datos © colaboradores de OpenStreetMap, licencia ODbL. Cada grupo se recarga completo dentro de
una transacción, así que se puede correr las veces que haga falta.

    python -m ubika.referencias.osm
    python -m ubika.referencias.osm --solo parques
    python -m ubika.referencias.osm --solo corredores
"""
from __future__ import annotations

import argparse
import logging
import math
import re
import time

import requests

from ubika.config import cfg
from ubika.db import corrida, read_df, reemplazar

log = logging.getLogger(__name__)

OVERPASS = "https://overpass-api.de/api/interpreter"
M_LAT, M_LON = 110_574, 108_900          # metros por grado cerca de los 12°S
AREA_MIN_M2 = 200                         # bermas y jardineras no cuentan como parque
PASO_VIA_M = 40

# tag de OSM → categoría de ubika
COMERCIO = {
    ("amenity", "marketplace"): "mercado",
    ("shop", "supermarket"): "supermercado",
    ("amenity", "pharmacy"): "farmacia",
    ("shop", "chemist"): "farmacia",
    ("amenity", "restaurant"): "restaurante",
    ("amenity", "cafe"): "restaurante",
    ("amenity", "fast_food"): "restaurante",
    ("leisure", "fitness_centre"): "gimnasio",
    ("amenity", "bank"): "banco",
}
VIAS = {"motorway": "autopista", "trunk": "autopista", "primary": "principal", "secondary": "secundaria"}
ROLES_PARADA = ("stop", "platform")       # stop, stop_entry_only, platform_exit_only, …
JUNTAR_PARADERO_M = 60                    # nodos a menos de esto son el mismo paradero


# ── Consulta ─────────────────────────────────────────────────

def _caja() -> str:
    c = cfg()["geocoding"]["caja"]
    return f'{c["lat_min"]},{c["lon_min"]},{c["lat_max"]},{c["lon_max"]}'


def consultas() -> dict[str, str]:
    b = _caja()
    comercio = "".join(f'nwr["{k}"="{v}"]({b});' for k, v in COMERCIO)
    return {
        "parques": f'[out:json][timeout:180];(way["leisure"="park"]({b});relation["leisure"="park"]({b}););out geom;',
        "comercio": f"[out:json][timeout:180];({comercio});out center;",
        "vias": (f'[out:json][timeout:180];(way["highway"~"^(motorway|trunk|primary|secondary)$"]({b});'
                 f'way["aeroway"="runway"]({b}););out geom;'),
        # Rutas de los corredores (red SIT) y los nodos que son sus paradas
        "corredores": (f'[out:json][timeout:180];relation["type"="route"]["network"="SIT"]({b})->.r;'
                       '(node(r.r);.r;);out body;'),
    }


def descargar(consulta: str, intentos: int = 3) -> list[dict]:
    for i in range(intentos):
        r = requests.post(OVERPASS, data={"data": consulta}, timeout=300,
                          headers={"User-Agent": "ubika/1.0 (proyecto de portafolio)"})
        if r.status_code == 200:
            return r.json().get("elements", [])
        espera = 30 * (i + 1)
        log.warning("  Overpass respondió %s; reintento en %d s", r.status_code, espera)
        time.sleep(espera)
    r.raise_for_status()
    return []


# ── Geometría ────────────────────────────────────────────────

def area_m2(anillo: list[dict]) -> float:
    """Área de un anillo [{lat, lon}, …] con la fórmula del cordón, en metros."""
    if len(anillo) < 4:
        return 0.0
    lat0 = anillo[0]["lat"]
    xs = [(p["lon"] - anillo[0]["lon"]) * M_LON * math.cos(math.radians(lat0)) / math.cos(math.radians(12)) for p in anillo]
    ys = [(p["lat"] - lat0) * M_LAT for p in anillo]
    return abs(sum(xs[i] * ys[i + 1] - xs[i + 1] * ys[i] for i in range(len(xs) - 1))) / 2


def centro(puntos: list[dict]) -> tuple[float, float]:
    return sum(p["lat"] for p in puntos) / len(puntos), sum(p["lon"] for p in puntos) / len(puntos)


def muestrear(linea: list[dict], paso_m: float = PASO_VIA_M) -> list[tuple[float, float]]:
    """Puntos cada `paso_m` metros a lo largo de una línea (incluye los vértices de inicio)."""
    out = []
    for a, b in zip(linea, linea[1:]):
        dy, dx = (b["lat"] - a["lat"]) * M_LAT, (b["lon"] - a["lon"]) * M_LON
        n = max(1, round(math.hypot(dx, dy) / paso_m))
        out += [(a["lat"] + (b["lat"] - a["lat"]) * k / n, a["lon"] + (b["lon"] - a["lon"]) * k / n) for k in range(n)]
    if linea:
        out.append((linea[-1]["lat"], linea[-1]["lon"]))
    return out


# ── Transformaciones (sin red, probadas en tests) ───────────

def parques(elementos: list[dict]) -> list[dict]:
    filas = []
    for e in elementos:
        if e["type"] == "way" and e.get("geometry"):
            anillos = [e["geometry"]]
        elif e["type"] == "relation":
            anillos = [m["geometry"] for m in e.get("members", [])
                       if m.get("role") == "outer" and m.get("geometry") and m["geometry"][0] == m["geometry"][-1]]
        else:
            continue
        area = sum(area_m2(a) for a in anillos)
        if area < AREA_MIN_M2 or not anillos:
            continue
        lat, lon = centro([p for a in anillos for p in a])
        filas.append({"categoria": "parque", "nombre": e.get("tags", {}).get("name"), "distrito": None,
                      "latitud": lat, "longitud": lon, "fuente": "osm",
                      "atributos": {"area_m2": round(area), "osm_id": f'{e["type"]}/{e["id"]}'}})
    return filas


def comercio(elementos: list[dict]) -> list[dict]:
    filas = []
    for e in elementos:
        tags = e.get("tags", {})
        cat = next((c for (k, v), c in COMERCIO.items() if tags.get(k) == v), None)
        pos = (e.get("lat"), e.get("lon")) if e["type"] == "node" else (e.get("center", {}).get("lat"), e.get("center", {}).get("lon"))
        if not cat or pos[0] is None:
            continue
        filas.append({"categoria": cat, "nombre": tags.get("name"), "distrito": None,
                      "latitud": pos[0], "longitud": pos[1], "fuente": "osm",
                      "atributos": {"osm_id": f'{e["type"]}/{e["id"]}'}})
    return filas


def vias(elementos: list[dict]) -> list[dict]:
    filas = []
    for e in elementos:
        tags = e.get("tags", {})
        tipo = "aeropuerto" if tags.get("aeroway") == "runway" else VIAS.get(tags.get("highway"))
        if not tipo or not e.get("geometry"):
            continue
        for lat, lon in muestrear(e["geometry"]):
            filas.append({"tipo": tipo, "nombre": tags.get("name"), "latitud": lat, "longitud": lon, "fuente": "osm"})
    return filas


def corredores(elementos: list[dict]) -> list[dict]:
    """
    Un punto por paradero físico de los corredores. De cada ruta SIT se toman los nodos con rol de
    parada; los que están a menos de JUNTAR_PARADERO_M se juntan (andenes de ida y vuelta, punto de
    parada y andén). El punto queda en el centro del grupo y guarda qué corredores y rutas pasan.
    """
    nodos = {e["id"]: e for e in elementos if e["type"] == "node" and "lat" in e}
    paradas: dict[int, dict] = {}                       # nodo → {corredores, rutas}
    for r in (e for e in elementos if e["type"] == "relation"):
        tags = r.get("tags", {})
        m = re.search(r"Corredor\s+(\w+)", tags.get("name", ""), re.I)
        corredor = m.group(1).capitalize() if m else (tags.get("network") or "SIT")
        ruta = tags.get("ref") or tags.get("name")
        for mb in r.get("members", []):
            if mb["type"] == "node" and mb.get("role", "").startswith(ROLES_PARADA) and mb["ref"] in nodos:
                d = paradas.setdefault(mb["ref"], {"corredores": set(), "rutas": set()})
                d["corredores"].add(corredor)
                if ruta:
                    d["rutas"].add(str(ruta))
    grupos: list[dict] = []
    for nid in sorted(paradas):
        n = nodos[nid]
        cerca = next((g for g in grupos
                      if math.hypot((n["lat"] - g["lat"]) * M_LAT, (n["lon"] - g["lon"]) * M_LON) <= JUNTAR_PARADERO_M), None)
        if cerca is None:
            cerca = {"lat": n["lat"], "lon": n["lon"], "nodos": [], "nombres": [], "corredores": set(), "rutas": set()}
            grupos.append(cerca)
        cerca["nodos"].append(n)
        if n.get("tags", {}).get("name"):
            cerca["nombres"].append(n["tags"]["name"])
        cerca["corredores"] |= paradas[nid]["corredores"]
        cerca["rutas"] |= paradas[nid]["rutas"]
        cerca["lat"], cerca["lon"] = centro(cerca["nodos"])
    return [{"categoria": "corredor", "nombre": g["nombres"][0] if g["nombres"] else None, "distrito": None,
             "latitud": g["lat"], "longitud": g["lon"], "fuente": "osm",
             "atributos": {"corredores": sorted(g["corredores"]), "rutas": sorted(g["rutas"]),
                           "osm_ids": [f'node/{n["id"]}' for n in g["nodos"]]}}
            for g in grupos]


# ── Carga ────────────────────────────────────────────────────

def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(description="Carga parques, comercio y vías de OpenStreetMap a Neon.")
    p.add_argument("--solo", choices=("parques", "comercio", "vias", "corredores"))
    args = p.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(levelname)-7s %(message)s", datefmt="%H:%M:%S")

    q = consultas()
    with corrida("referencias_osm", solo=args.solo) as c:
        total = 0
        if args.solo in (None, "parques"):
            log.info("Descargando parques…")
            filas = parques(descargar(q["parques"]))
            total += reemplazar("puntos_interes", "categoria = 'parque' AND fuente = 'osm'", {}, filas)
            log.info("  %d parques, %.0f ha en total", len(filas), sum(f["atributos"]["area_m2"] for f in filas) / 1e4)
        if args.solo in (None, "comercio"):
            log.info("Descargando comercio…")
            filas = comercio(descargar(q["comercio"]))
            cats = sorted(set(COMERCIO.values()))
            total += reemplazar("puntos_interes", "categoria = ANY(:c) AND fuente = 'osm'", {"c": cats}, filas)
            log.info("  %d locales de comercio", len(filas))
        if args.solo in (None, "vias"):
            log.info("Descargando vías y aeropuerto…")
            filas = vias(descargar(q["vias"]))
            total += reemplazar("ruido_fuentes", "fuente = 'osm'", {}, filas)
            log.info("  %d puntos de vías", len(filas))
        if args.solo in (None, "corredores"):
            log.info("Descargando paraderos de corredores…")
            filas = corredores(descargar(q["corredores"]))
            total += reemplazar("puntos_interes", "categoria = 'corredor' AND fuente = 'osm'", {}, filas)
            por = {}
            for f in filas:
                for co in f["atributos"]["corredores"]:
                    por[co] = por.get(co, 0) + 1
            log.info("  %d paraderos de corredores (%s)", len(filas), ", ".join(f"{k} {v}" for k, v in sorted(por.items())))
        c.escritas = total
    log.info("Resumen:\n%s", read_df("""
        SELECT categoria, COUNT(*) AS n FROM puntos_interes WHERE fuente = 'osm' GROUP BY 1
        UNION ALL SELECT 'ruido · ' || tipo, COUNT(*) FROM ruido_fuentes GROUP BY 1 ORDER BY 1""").to_string(index=False))


if __name__ == "__main__":
    main()

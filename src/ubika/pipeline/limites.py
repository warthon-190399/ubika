"""
Límites distritales (IGN) para ubicar un punto en su distrito. Funciones puras salvo `cargar`.

Se usa el mismo GeoJSON que dibuja la app (ubika-app/public/geo/distritos-lima.geojson), así el
distrito de un inmueble coincide con el polígono donde aparece en el mapa. Cada feature trae
`properties.distrito` con la clave de la tabla distritos.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

from ubika.config import ROOT


def cargar(ruta: str | Path) -> list[tuple[str, list]]:
    """[(distrito, [polígono, …])], cada polígono = [anillo exterior, huecos…] en (lon, lat)."""
    with open(ROOT / ruta, encoding="utf-8") as f:
        g = json.load(f)
    out = []
    for feat in g["features"]:
        geom = feat["geometry"]
        polys = geom["coordinates"] if geom["type"] == "MultiPolygon" else [geom["coordinates"]]
        out.append((feat["properties"]["distrito"], polys))
    return out


def _en_anillo(lon: float, lat: float, anillo: list) -> bool:
    """Ray casting: cuántas veces cruza el borde una semirrecta hacia el este."""
    dentro, j = False, len(anillo) - 1
    for i in range(len(anillo)):
        xi, yi = anillo[i][0], anillo[i][1]
        xj, yj = anillo[j][0], anillo[j][1]
        if (yi > lat) != (yj > lat) and lon < (xj - xi) * (lat - yi) / (yj - yi) + xi:
            dentro = not dentro
        j = i
    return dentro


def _en_poligono(lon: float, lat: float, polys: list) -> bool:
    return any(_en_anillo(lon, lat, ext) and not any(_en_anillo(lon, lat, h) for h in huecos)
               for ext, *huecos in polys)


def metros_a_distrito(lat: float, lon: float, distrito: str, limites: list[tuple[str, list]]) -> float | None:
    """0 si el punto está dentro del distrito; si no, la distancia en metros a su borde más cercano.
    None si el distrito no tiene polígono."""
    polys = next((p for d, p in limites if d == distrito), None)
    if polys is None:
        return None
    if _en_poligono(lon, lat, polys):
        return 0.0
    k = math.cos(math.radians(lat))                  # a esta escala, un plano local basta
    mejor = math.inf
    for anillos in polys:
        for anillo in anillos:
            for (ax, ay), (bx, by) in zip(anillo, anillo[1:]):
                ax, bx, px = ax * k, bx * k, lon * k
                dx, dy = bx - ax, by - ay
                t = 0.0 if dx == dy == 0 else max(0.0, min(1.0, ((px - ax) * dx + (lat - ay) * dy) / (dx * dx + dy * dy)))
                mejor = min(mejor, math.hypot(px - (ax + t * dx), lat - (ay + t * dy)))
    return mejor * 111_320


def distrito_en(lat: float, lon: float, limites: list[tuple[str, list]]) -> str | None:
    """Distrito cuyo polígono contiene el punto, o None si cae fuera de todos (mar, otra provincia)."""
    return next((distrito for distrito, polys in limites if _en_poligono(lon, lat, polys)), None)

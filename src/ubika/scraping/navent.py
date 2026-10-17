"""
Parsers para portales de la plataforma Navent (adondevivir.com, urbania.pe).

Funciones puras: reciben HTML y devuelven dicts listos para raw_listings / raw_detalles.
Se prueban con HTML real guardado en tests/fixtures/.

Qué se lee:
- Listado: cada tarjeta [data-qa="posting PROPERTY"] (los proyectos DEVELOPMENT se ignoran)
  y su bloque JSON-LD, que trae las coordenadas.
- Detalle: el bloque `const avisoInfo = {...}` de la ficha, con precios, características,
  fecha de publicación, publicador y visibilidad de la dirección.
No se guardan teléfonos ni WhatsApp.
"""
from __future__ import annotations

import datetime as dt
import html as html_lib
import json
import re
from urllib.parse import urlparse

from bs4 import BeautifulSoup

TIPO_UNIDAD = "PROPERTY"     # las tarjetas DEVELOPMENT son proyectos con precios "desde": no son una unidad


def _txt(el) -> str | None:
    if el is None:
        return None
    t = " ".join(el.get_text(" ", strip=True).split())
    return t or None


def _float(v) -> float | None:
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def aviso_id(url: str) -> str | None:
    m = re.search(r"-(\d{6,})\.html", url or "")
    return m.group(1) if m else None


def clasificar_features(textos: list[str]) -> dict:
    """['102 m² tot.', '2 dorm.', '2 baños', '1 estac.'] → area_raw, dorm_raw, banos_raw, estac_raw."""
    out = {"area_raw": None, "dorm_raw": None, "banos_raw": None, "estac_raw": None}
    for t in textos:
        tl = t.lower()
        if ("m²" in tl or "m2" in tl) and out["area_raw"] is None:
            out["area_raw"] = t
        elif "dorm" in tl:
            out["dorm_raw"] = t
        elif "baño" in tl:
            out["banos_raw"] = t
        elif "estac" in tl:
            out["estac_raw"] = t
    return out


# ── Listado ──────────────────────────────────────────────────

def _coordenadas_ld(soup: BeautifulSoup) -> dict[str, tuple[float, float]]:
    """path del aviso → (lat, lon) desde los bloques JSON-LD de la página."""
    coords = {}
    for s in soup.find_all("script", type="application/ld+json"):
        try:
            j = json.loads(s.string or s.get_text())
        except (json.JSONDecodeError, TypeError):
            continue
        obj = j.get("object") if isinstance(j, dict) else None
        if not isinstance(obj, dict) or not obj.get("url"):
            continue
        geo = obj.get("geo") or {}
        lat, lon = _float(geo.get("latitude")), _float(geo.get("longitude"))
        if lat is not None and lon is not None and -90 <= lat <= 90 and -180 <= lon <= 180:
            coords[urlparse(obj["url"]).path] = (round(lat, 7), round(lon, 7))
    return coords


def total_resultados(soup: BeautifulSoup) -> int | None:
    m = re.match(r"\s*([\d.,]+)", _txt(soup.find("h1")) or "")
    return int(re.sub(r"[.,]", "", m.group(1))) if m else None


def parsear_listado(html: str, base_url: str) -> tuple[list[dict], int | None]:
    """Devuelve (avisos de la página en orden, total de resultados que anuncia el portal)."""
    soup = BeautifulSoup(html, "html.parser")
    coords = _coordenadas_ld(soup)
    avisos = []
    for pos, card in enumerate(soup.select('[data-qa^="posting "]'), start=1):
        destino = card.get("data-to-posting") or ""
        path = destino.split("?")[0]
        if not path:
            continue
        spans = [_txt(s) for s in card.select('[data-qa="POSTING_CARD_FEATURES"] span')]
        lat, lon = coords.get(path, (None, None))
        avisos.append({
            "url": base_url.rstrip("/") + path,
            "aviso_id": card.get("data-id") or aviso_id(path),
            "tipo_raw": card.get("data-posting-type"),
            "posicion": pos,
            "precio_raw": _txt(card.select_one('[data-qa="POSTING_CARD_PRICE"]')),
            "mantenimiento_raw": _txt(card.select_one('[data-qa="expensas"]')),
            "direccion_raw": _txt(card.select_one('[class*="location-address"]')),
            "ubicacion_raw": _txt(card.select_one('[data-qa="POSTING_CARD_LOCATION"]')),
            **clasificar_features([t for t in spans if t]),
            "latitud": lat,
            "longitud": lon,
        })
    return avisos, total_resultados(soup)


# ── Detalle ──────────────────────────────────────────────────

def _bloque(texto: str, clave: str) -> str | None:
    """Extrae el objeto/arreglo JSON que sigue a 'clave': respetando llaves anidadas y strings."""
    m = re.search(r"['\"]" + re.escape(clave) + r"['\"]\s*:\s*([\[{])", texto)
    if not m:
        return None
    ini = m.start(1)
    abre, cierra = texto[ini], {"{": "}", "[": "]"}[texto[ini]]
    prof, en_str, esc = 0, False, False
    for i in range(ini, len(texto)):
        ch = texto[i]
        if en_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                en_str = False
        elif ch == '"':
            en_str = True
        elif ch == abre:
            prof += 1
        elif ch == cierra:
            prof -= 1
            if prof == 0:
                return texto[ini:i + 1]
    return None


def _json(texto: str, clave: str):
    b = _bloque(texto, clave)
    if not b:
        return None
    try:
        return json.loads(b)
    except json.JSONDecodeError:
        return None


def _valor(texto: str, patron: str) -> str | None:
    m = re.search(patron, texto, flags=re.S)
    return m.group(1).strip() if m else None


def _descripcion(texto: str) -> str | None:
    d = _valor(texto, r"'description'\s*:\s*\"(.*?)\",\s*\n")
    if not d:
        return None
    d = re.sub(r"<br\s*/?>", "\n", d, flags=re.I)
    d = re.sub(r"<[^>]+>", "", d)
    return html_lib.unescape(d).strip() or None


def _features(main: dict | None) -> dict:
    """mainFeatures del portal → textos crudos por característica."""
    out = {"area_total_raw": None, "area_cubierta_raw": None, "dorm_raw": None,
           "banos_raw": None, "estac_raw": None, "antiguedad_raw": None}
    icono_a_campo = {"stotal": "area_total_raw", "scubierta": "area_cubierta_raw", "dormitorio": "dorm_raw",
                     "bano": "banos_raw", "cochera": "estac_raw", "antiguedad": "antiguedad_raw"}
    for f in (main or {}).values():
        campo = icono_a_campo.get(f.get("icon"))
        if not campo:
            continue
        valor = str(f.get("value", "")).strip()
        unidad = f.get("measure") or ""
        etiqueta = f.get("label") or ""
        if campo == "antiguedad_raw":
            out[campo] = valor if not valor.isdigit() else f"{valor} años"
        else:
            out[campo] = " ".join(p for p in (valor, unidad, etiqueta) if p)
    return out


def parsear_detalle(html: str, hoy: dt.date | None = None) -> dict:
    """
    Devuelve los campos de raw_detalles. Si la ficha no tiene el bloque avisoInfo
    (aviso dado de baja o redirigido), devuelve {'estado': 'no_disponible'}.
    """
    soup = BeautifulSoup(html, "html.parser")
    script = next((s.get_text() for s in soup.find_all("script") if "const avisoInfo" in s.get_text()), None)
    if not script:
        return {"estado": "no_disponible"}
    aviso = script[script.index("const avisoInfo"):]

    precios = {}
    for op in _json(aviso, "pricesData") or []:
        for p in op.get("prices", []):
            precios[p.get("isoCode")] = _float(p.get("amount"))

    publicado_at = None
    fecha = _valor(aviso, r"'publicationDateFormatted'\s*:\s*'([^']+)'")
    if fecha:
        try:
            publicado_at = dt.datetime.fromisoformat(fecha.replace("Z", "+00:00"))
        except ValueError:
            pass

    publisher = _valor(aviso, r"'publisher'\s*:\s*\{(.*?)\}") or ""
    tipo_pub = _valor(publisher, r"'publisherTypeId'\s*:\s*(\d+)")
    estado_aviso = _valor(aviso, r"'status'\s*:\s*'([A-Z_]+)'")
    expenses = _valor(aviso, r"'expenses'\s*:\s*'([^']*)'")
    tipo = _json(aviso, "realEstateType") or {}
    features = _json(aviso, "generalFeatures")

    return {
        "estado": "ok",
        "estado_aviso": estado_aviso,
        "tipo_inmueble_raw": tipo.get("name"),
        "precio_pen": precios.get("PEN"),
        "precio_usd": precios.get("USD"),
        "mantenimiento_raw": expenses if expenses not in (None, "", "0") else None,
        **_features(_json(aviso, "mainFeatures")),
        "publicado_raw": _valor(script, r"const antiquity\s*=\s*'([^']*)'"),
        "publicado_at": publicado_at,
        "fecha_publicacion": publicado_at.date() if publicado_at else None,
        "visualizaciones_raw": _valor(script, r"const usersViews\s*=\s*(\d+)"),
        "inmobiliaria_raw": html_lib.unescape(_valor(publisher, r"'name'\s*:\s*'([^']*)'") or "") or None,
        "tipo_publicador": int(tipo_pub) if tipo_pub else None,
        "visibilidad_direccion": _valor(aviso, r"'visibility'\s*:\s*'([A-Z_]+)'"),
        "ubicacion_portal": _json(aviso, "location"),
        "caracteristicas": features,
        "descripcion": _descripcion(aviso),
    }

"""
Parseo de los textos crudos de los portales a números y categorías. Funciones puras.

    'S/ 3,000 · USD 857'   → (3000.0, 857.0)
    'S/ 620 Mantenimiento' → 620.0
    '102 m² tot.'          → 102.0
    'A estrenar'           → 0
    'Javier Prado Et.4, San Luis' → 'san luis'
"""
from __future__ import annotations

import re

from ubika.texto import normalizar

_NUM = r"(\d[\d,.]*)"


def _s(v) -> str | None:
    """Texto o None (pandas trae NaN en las columnas vacías)."""
    if v is None or (isinstance(v, float) and v != v):
        return None
    return str(v)


def _numero(s: str) -> float | None:
    """'1,038,000' → 1038000 ; '102.30' → 102.3 ; '3.500' (miles con punto) → 3500."""
    s = s.strip().rstrip(".,")
    if not s:
        return None
    if "," in s:
        s = s.replace(",", "")
    elif s.count(".") == 1 and len(s.split(".")[1]) == 3:
        s = s.replace(".", "")              # '3.500' → miles, no decimales
    elif s.count(".") > 1:
        s = s.replace(".", "")
    try:
        return float(s)
    except ValueError:
        return None


def precios(texto: str | None) -> tuple[float | None, float | None]:
    """Precio publicado → (soles, dólares). Acepta 'S/ 3,000 · USD 857', 'USD 120,000', 'S/ 1,800'."""
    texto = _s(texto)
    if not texto:
        return None, None
    t = texto.upper().replace("US$", "USD")
    pen = re.search(r"S/\.?\s*" + _NUM, t)
    usd = re.search(r"USD\s*" + _NUM, t)
    return (_numero(pen.group(1)) if pen else None, _numero(usd.group(1)) if usd else None)


def mantenimiento(texto: str | None) -> float | None:
    texto = _s(texto)
    if not texto:
        return None
    m = re.search(r"S/\.?\s*" + _NUM, texto.upper()) or re.search(_NUM, texto)
    return _numero(m.group(1)) if m else None


def area_m2(texto: str | None) -> float | None:
    """'102 m² tot.' → 102 ; '1.5 ha' → 15000 ; '63 a 74 m²' (rango de un proyecto) → None."""
    texto = _s(texto)
    if not texto:
        return None
    t = texto.lower()
    if re.search(r"\d\s*a\s*\d", t):
        return None
    m = re.search(_NUM, t)
    if not m:
        return None
    v = _numero(m.group(1))
    if v is not None and re.search(r"\bha\b", t):
        v *= 10_000
    return v


def entero(texto: str | None) -> int | None:
    """'2 dorm.' → 2 ; '1 estac.' → 1 ; 'Monoambiente' → None."""
    texto = _s(texto)
    if texto is None:
        return None
    m = re.search(r"\d+", str(texto))
    return int(m.group()) if m else None


def antiguedad(texto: str | None) -> int | None:
    """'A estrenar' / 'En construcción' → 0 ; '11 años' → 11 ; texto raro → None."""
    texto = _s(texto)
    if not texto:
        return None
    t = normalizar(texto)
    if "estrenar" in t or "construccion" in t or "en planos" in t:
        return 0
    m = re.search(r"\d+", t)
    if not m:
        return None
    v = int(m.group())
    return v if v <= 150 else None


def distrito(ubicacion: str | None, alias: dict[str, str]) -> str | None:
    """
    'Magdalena, Lima' → 'magdalena' ; 'Javier Prado Et.4, San Luis' → 'san luis'.
    Prueba cada parte de derecha a izquierda y se queda con la primera que es un distrito conocido,
    saltando 'Lima' cuando hay algo más específico a su izquierda.
    """
    ubicacion = _s(ubicacion)
    if not ubicacion:
        return None
    partes = [normalizar(p) for p in str(ubicacion).split(",") if p.strip()]
    for i, p in enumerate(reversed(partes)):
        es_ultima_y_hay_mas = (i == 0 and len(partes) > 1)
        if es_ultima_y_hay_mas and p in ("lima", "callao", "lima metropolitana", "peru"):
            continue
        if p in alias:
            return alias[p]
    return alias.get(partes[-1]) if partes else None


TIPOS = {"apartamento": "departamento", "departamento": "departamento", "casa": "casa",
         "oficina": "oficina", "terreno": "terreno", "local comercial": "local", "habitacion": "habitacion"}


def tipo_inmueble(texto: str | None, por_defecto: str = "departamento") -> str:
    texto = _s(texto)
    return TIPOS.get(normalizar(texto), normalizar(texto) or por_defecto) if texto else por_defecto

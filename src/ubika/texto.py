"""Normalización de texto compartida por scrapers, pipeline y referencias."""
from __future__ import annotations

import re
import unicodedata


def normalizar(s: object) -> str:
    """'  Breña, LIMA ' → 'brena, lima'. Minúsculas, sin tildes, espacios simples."""
    if s is None:
        return ""
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"\s+", " ", s.lower()).strip()

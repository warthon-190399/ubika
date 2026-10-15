"""
Configuración única del proyecto.

- Parámetros: config.yaml en la raíz.
- Secretos: .env en la raíz (ver .env.example).
"""
from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

import yaml
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env")


@lru_cache(maxsize=1)
def cfg() -> dict:
    with open(ROOT / "config.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _secreto(*nombres: str) -> str | None:
    for n in nombres:
        v = os.getenv(n)
        if v:
            return v.strip().strip('"').strip("'")
    return None


def database_url() -> str:
    url = _secreto("DATABASE_URL")
    if not url:
        raise EnvironmentError(
            "Falta DATABASE_URL en .env. Copia .env.example como .env y pega la cadena de conexión de Neon."
        )
    return url


def google_api_key() -> str:
    # GOOGLE_GEOENCODING_APIKEY es el nombre antiguo; se acepta para no romper .env existentes
    key = _secreto("GOOGLE_GEOCODING_API_KEY", "GOOGLE_GEOENCODING_APIKEY")
    if not key:
        raise EnvironmentError("Falta GOOGLE_GEOCODING_API_KEY en .env.")
    return key

"""
service/urbania_service.py
==========================
Lógica de escritura/lectura para urbania_listings usando Neon (PostgreSQL).
"""

from __future__ import annotations

import uuid
import datetime
import logging
from typing import Any

from sqlalchemy import text
from service.db_client import get_engine

logger = logging.getLogger(__name__)

CHUNK = 100


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def make_prop_id(url: str) -> str:
    """UUID v5 determinístico — mismo URL = mismo prop_id siempre."""
    return str(uuid.uuid5(uuid.NAMESPACE_URL, url))


def _build_record(raw: dict) -> dict:
    url = raw.get("url", "").strip()
    return {
        "prop_id":        make_prop_id(url),
        "url":            url,
        "fuente":         "urbania",
        "scrape_date":    raw.get("scrape_date", str(datetime.date.today())),
        "detalle_status": "pending",
        "precio":         raw.get("precio") or None,
        "mantenimiento":  raw.get("mantenimiento") or None,
        "m2_total":       raw.get("m2_total") or None,
        "dorms":          raw.get("dorms") or None,
        "banos":          raw.get("banos") or None,
        "estac":          raw.get("estac") or None,
        "direccion":      raw.get("direccion") or None,
        "distrito":       raw.get("distrito") or None,
    }


# ------------------------------------------------------------------
# Escritura
# ------------------------------------------------------------------

_UPSERT_SQL = text("""
    INSERT INTO urbania_listings
        (prop_id, url, fuente, scrape_date, detalle_status,
         precio, mantenimiento, m2_total, dorms, banos, estac, direccion, distrito)
    VALUES
        (:prop_id, :url, :fuente, :scrape_date, :detalle_status,
         :precio, :mantenimiento, :m2_total, :dorms, :banos, :estac, :direccion, :distrito)
    ON CONFLICT (prop_id) DO UPDATE SET
        precio        = EXCLUDED.precio,
        mantenimiento = EXCLUDED.mantenimiento,
        m2_total      = EXCLUDED.m2_total,
        dorms         = EXCLUDED.dorms,
        banos         = EXCLUDED.banos,
        estac         = EXCLUDED.estac,
        direccion     = EXCLUDED.direccion,
        distrito      = EXCLUDED.distrito,
        updated_at    = NOW()
""")
# Nota: NO actualizamos detalle_status en el ON CONFLICT
# para no pisar un 'ok' existente con 'pending'


def upsert_listings(records: list[dict]) -> dict[str, int]:
    """Inserta o actualiza listings en lote."""
    if not records:
        return {"upserted": 0, "errors": 0}

    built = [_build_record(r) for r in records if r.get("url")]
    stats = {"upserted": 0, "errors": 0}

    with get_engine().begin() as conn:
        for i in range(0, len(built), CHUNK):
            chunk = built[i : i + CHUNK]
            try:
                conn.execute(_UPSERT_SQL, chunk)
                stats["upserted"] += len(chunk)
                logger.info(f"  upsert listings [{i+1}..{i+len(chunk)}] ok")
            except Exception as exc:
                stats["errors"] += len(chunk)
                logger.error(f"  error en chunk {i}: {exc}")

    return stats


def update_detalle_status(prop_id: str, status: str) -> None:
    """Actualiza detalle_status de un listing individual."""
    with get_engine().begin() as conn:
        conn.execute(
            text("""
                UPDATE urbania_listings
                SET detalle_status = :s, updated_at = NOW()
                WHERE prop_id = :id
            """),
            {"s": status, "id": prop_id},
        )


# ------------------------------------------------------------------
# Lectura — cola de trabajo para scraper_detalles
# ------------------------------------------------------------------

def get_pending_urls(limit: int = 0) -> list[dict]:
    """Listings que aún necesitan scraping de detalles."""
    sql = """
        SELECT prop_id, url
        FROM urbania_listings
        WHERE detalle_status = 'pending'
        ORDER BY scrape_date ASC
    """
    if limit:
        sql += f" LIMIT {limit}"

    with get_engine().connect() as conn:
        rows = conn.execute(text(sql)).fetchall()
    return [{"prop_id": str(r[0]), "url": r[1]} for r in rows]


def get_error_urls() -> list[dict]:
    """Listings que fallaron por timeout/error temporal — reintentables."""
    with get_engine().connect() as conn:
        rows = conn.execute(text("""
            SELECT prop_id, url
            FROM urbania_listings
            WHERE detalle_status = 'error'
            ORDER BY updated_at ASC
        """)).fetchall()
    return [{"prop_id": str(r[0]), "url": r[1]} for r in rows]


def get_stats() -> dict[str, Any]:
    """Resumen del estado de la tabla. Útil para monitoreo."""
    with get_engine().connect() as conn:
        rows = conn.execute(text("""
            SELECT detalle_status, COUNT(*)
            FROM urbania_listings
            GROUP BY detalle_status
        """)).fetchall()

    counts = {row[0]: row[1] for row in rows}
    return {"total": sum(counts.values()), **counts}
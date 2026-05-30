"""
service/adondevivir_service.py
==============================
Lógica de escritura/lectura para adondevivir_listings.
Columnas idénticas a urbania_listings — sin remapeos.
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


def make_prop_id(url: str) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_URL, url))


_UPSERT_SQL = text("""
    INSERT INTO adondevivir_listings
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


def upsert_listings(records: list[dict]) -> dict[str, int]:
    if not records:
        return {"upserted": 0, "errors": 0}

    today = str(datetime.date.today())
    built = []
    for r in records:
        url = (r.get("url") or "").strip()
        if not url:
            continue
        built.append({
            "prop_id":        make_prop_id(url),
            "url":            url,
            "fuente":         "adondevivir",
            "scrape_date":    r.get("scrape_date", today),
            "detalle_status": "pending",
            "precio":         r.get("precio") or None,
            "mantenimiento":  r.get("mantenimiento") or None,
            "m2_total":       r.get("m2_total") or None,
            "dorms":          r.get("dorms") or None,
            "banos":          r.get("banos") or None,
            "estac":          r.get("estac") or None,
            "direccion":      r.get("direccion") or None,
            "distrito":       r.get("distrito") or None,
        })

    stats = {"upserted": 0, "errors": 0}
    with get_engine().begin() as conn:
        for i in range(0, len(built), CHUNK):
            chunk = built[i : i + CHUNK]
            try:
                conn.execute(_UPSERT_SQL, chunk)
                stats["upserted"] += len(chunk)
                logger.info(f"  upsert [{i+1}..{i+len(chunk)}] ok")
            except Exception as exc:
                stats["errors"] += len(chunk)
                logger.error(f"  error en chunk {i}: {exc}")
    return stats


def update_detalle_status(prop_id: str, status: str) -> None:
    with get_engine().begin() as conn:
        conn.execute(
            text("UPDATE adondevivir_listings SET detalle_status=:s, updated_at=NOW() WHERE prop_id=:id"),
            {"s": status, "id": prop_id},
        )


def get_pending_urls(limit: int = 0) -> list[dict]:
    sql = "SELECT prop_id, url FROM adondevivir_listings WHERE detalle_status='pending' ORDER BY scrape_date ASC"
    if limit:
        sql += f" LIMIT {limit}"
    with get_engine().connect() as conn:
        rows = conn.execute(text(sql)).fetchall()
    return [{"prop_id": str(r[0]), "url": r[1]} for r in rows]


def get_error_urls() -> list[dict]:
    with get_engine().connect() as conn:
        rows = conn.execute(
            text("SELECT prop_id, url FROM adondevivir_listings WHERE detalle_status='error' ORDER BY updated_at ASC")
        ).fetchall()
    return [{"prop_id": str(r[0]), "url": r[1]} for r in rows]


def get_stats() -> dict[str, Any]:
    with get_engine().connect() as conn:
        rows = conn.execute(
            text("SELECT detalle_status, COUNT(*) FROM adondevivir_listings GROUP BY detalle_status")
        ).fetchall()
    counts = {r[0]: r[1] for r in rows}
    return {"total": sum(counts.values()), **counts}
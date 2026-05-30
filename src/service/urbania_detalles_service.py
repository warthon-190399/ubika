"""
service/adondevivir_detalles_service.py
========================================
Misma estructura que urbania_detalles_service.py.
Columnas idénticas — sin campos extra.
"""

from __future__ import annotations

import datetime
import logging

from sqlalchemy import text
from service.db_client import get_engine
from service.adondevivir_service import update_detalle_status

logger = logging.getLogger(__name__)

_UPSERT_SQL = text("""
    INSERT INTO adondevivir_detalles
        (prop_id, scrape_date, antiguedad, descripcion, publicado_por, fecha_publicacion)
    VALUES
        (:prop_id, :scrape_date, :antiguedad, :descripcion, :publicado_por, :fecha_publicacion)
    ON CONFLICT (prop_id) DO UPDATE SET
        scrape_date       = EXCLUDED.scrape_date,
        antiguedad        = EXCLUDED.antiguedad,
        descripcion       = EXCLUDED.descripcion,
        publicado_por     = EXCLUDED.publicado_por,
        fecha_publicacion = EXCLUDED.fecha_publicacion,
        updated_at        = NOW()
""")


def save_detalle(prop_id: str, raw: dict) -> bool:
    record = {
        "prop_id":           prop_id,
        "scrape_date":       raw.get("scrape_date", str(datetime.date.today())),
        "antiguedad":        raw.get("antiguedad") or None,
        "descripcion":       raw.get("descripcion") or None,
        "publicado_por":     raw.get("publicado_por") or None,
        "fecha_publicacion": raw.get("fecha_publicacion") or None,
    }
    try:
        with get_engine().begin() as conn:
            conn.execute(_UPSERT_SQL, record)
        update_detalle_status(prop_id, "ok")
        logger.info(f"  detalle ok: {prop_id[:8]}...")
        return True
    except Exception as exc:
        logger.error(f"  error guardando detalle {prop_id[:8]}...: {exc}")
        update_detalle_status(prop_id, "error")
        return False


def mark_gone(prop_id: str) -> None:
    update_detalle_status(prop_id, "gone")
    logger.info(f"  gone: {prop_id[:8]}...")


def mark_error(prop_id: str) -> None:
    update_detalle_status(prop_id, "error")
    logger.info(f"  error: {prop_id[:8]}...")
"""
Acceso a Neon (PostgreSQL).

Python solo lee y escribe datos. Las tablas se crean a mano en Neon con los scripts de sql/.
"""
from __future__ import annotations

import json
import logging
from contextlib import contextmanager
from functools import lru_cache
from typing import Any, Iterable

import pandas as pd
from sqlalchemy import MetaData, Table, create_engine, text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.engine import Engine

from ubika.config import database_url

log = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def engine() -> Engine:
    return create_engine(database_url(), pool_pre_ping=True, pool_size=5, max_overflow=5)


@lru_cache(maxsize=None)
def tabla(nombre: str) -> Table:
    """Refleja una tabla existente en Neon (falla con un mensaje claro si no existe)."""
    return Table(nombre, MetaData(), autoload_with=engine())


def read_df(sql: str, params: dict | None = None) -> pd.DataFrame:
    with engine().connect() as conn:
        return pd.read_sql(text(sql), conn, params=params or {})


def execute(sql: str, params: dict | list[dict] | None = None) -> int:
    with engine().begin() as conn:
        res = conn.execute(text(sql), params or {})
        return res.rowcount if res.rowcount is not None else 0


def _limpiar(records: Iterable[dict]) -> list[dict]:
    """NaN/NaT de pandas → None, para que Postgres reciba NULL."""
    out = []
    for r in records:
        out.append({k: (None if (v is not None and not isinstance(v, (list, dict, str)) and pd.isna(v)) else v)
                    for k, v in r.items()})
    return out


def upsert(nombre: str, records: list[dict] | pd.DataFrame, conflicto: list[str],
           actualizar: list[str] | None = None, chunk: int = 1000) -> int:
    """
    INSERT ... ON CONFLICT (conflicto) DO UPDATE SET actualizar = EXCLUDED.actualizar.
    Si `actualizar` es una lista vacía, hace DO NOTHING. Si es None, actualiza todas las columnas
    recibidas que no sean parte de la llave.
    Devuelve el número de filas enviadas.
    """
    if isinstance(records, pd.DataFrame):
        records = records.to_dict("records")
    records = _limpiar(records)
    if not records:
        return 0

    t = tabla(nombre)
    if actualizar is None:
        actualizar = [c for c in records[0] if c not in conflicto]

    total = 0
    with engine().begin() as conn:
        for i in range(0, len(records), chunk):
            parte = records[i:i + chunk]
            stmt = pg_insert(t).values(parte)
            if actualizar:
                stmt = stmt.on_conflict_do_update(
                    index_elements=conflicto,
                    set_={c: stmt.excluded[c] for c in actualizar},
                )
            else:
                stmt = stmt.on_conflict_do_nothing(index_elements=conflicto)
            conn.execute(stmt)
            total += len(parte)
    return total


def reemplazar(nombre: str, donde: str, params: dict, records: list[dict] | pd.DataFrame,
               chunk: int = 1000) -> int:
    """
    En una sola transacción: DELETE FROM nombre WHERE <donde>, luego INSERT de records.
    Para recargar una fuente completa sin dejar la tabla a medias si algo falla.
    """
    if isinstance(records, pd.DataFrame):
        records = records.to_dict("records")
    records = _limpiar(records)
    t = tabla(nombre)
    with engine().begin() as conn:
        conn.execute(text(f'DELETE FROM "{nombre}" WHERE {donde}'), params)
        for i in range(0, len(records), chunk):
            conn.execute(t.insert(), records[i:i + chunk])
    return len(records)


class _Corrida:
    def __init__(self, corrida_id: int):
        self.id = corrida_id
        self.leidas: int | None = None
        self.escritas: int | None = None
        self.mensaje: str | None = None


@contextmanager
def corrida(etapa: str, **parametros: Any):
    """
    Registra una ejecución en la tabla `corridas`.

        with corrida("scraping_listado", fuente="adondevivir", operacion="venta") as c:
            ...
            c.escritas = 100
    """
    with engine().begin() as conn:
        cid = conn.execute(
            text("INSERT INTO corridas (etapa, parametros) VALUES (:e, CAST(:p AS JSONB)) RETURNING corrida_id"),
            {"e": etapa, "p": json.dumps(parametros, default=str)},
        ).scalar_one()
    c = _Corrida(cid)
    log.info("Corrida %s · %s %s", cid, etapa, parametros or "")
    try:
        yield c
    except Exception as exc:
        _cerrar(c, "error", f"{type(exc).__name__}: {exc}"[:2000])
        raise
    else:
        _cerrar(c, "ok", c.mensaje)


def _cerrar(c: _Corrida, estado: str, mensaje: str | None) -> None:
    execute(
        """UPDATE corridas SET estado = :s, terminada_at = now(), filas_leidas = :l,
           filas_escritas = :w, mensaje = :m WHERE corrida_id = :id""",
        {"s": estado, "l": c.leidas, "w": c.escritas, "m": mensaje, "id": c.id},
    )

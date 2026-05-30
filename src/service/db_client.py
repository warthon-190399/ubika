"""
service/db_client.py
====================
Cliente de conexión a Neon (PostgreSQL).
Reemplaza supabase_client.py — el resto del proyecto no cambia su lógica,
solo importa desde aquí.
 
Requiere:
    pip install psycopg2-binary sqlalchemy python-dotenv
 
.env debe tener:
    DATABASE_URL=postgresql://user:pass@ep-xxx.us-east-2.aws.neon.tech/neondb?sslmode=require
"""
 
from __future__ import annotations
 
import os
from functools import lru_cache
 
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
 
load_dotenv()
 
 
@lru_cache(maxsize=1)
def get_engine():
    url = os.environ.get("DATABASE_URL")
    if not url:
        raise EnvironmentError(
            "Falta DATABASE_URL en el .env\n"
            "Formato: postgresql://user:pass@ep-xxx.us-east-2.aws.neon.tech/neondb?sslmode=require"
        )
    return create_engine(
        url,
        pool_pre_ping=True,      # verifica conexión antes de usarla
        pool_size=5,
        max_overflow=10,
        connect_args={"sslmode": "require"},
    )
 
 
@lru_cache(maxsize=1)
def get_session_factory() -> sessionmaker:
    return sessionmaker(bind=get_engine(), autocommit=False, autoflush=False)
 
 
def get_session() -> Session:
    """Devuelve una sesión lista para usar. Ciérrala con session.close()."""
    factory = get_session_factory()
    return factory()
 
 
def execute(sql: str, params: dict | None = None) -> list[dict]:
    """
    Ejecuta SQL crudo y devuelve lista de dicts.
    Útil para SELECTs rápidos.
 
    Ejemplo:
        rows = execute("SELECT * FROM urbania_listings WHERE detalle_status = :s", {"s": "pending"})
    """
    with get_engine().connect() as conn:
        result = conn.execute(text(sql), params or {})
        if result.returns_rows:
            cols = result.keys()
            return [dict(zip(cols, row)) for row in result.fetchall()]
        conn.commit()
        return []
"""
Verifica la conexión a Neon y que el esquema de sql/ esté aplicado. Solo lectura.

    python scripts/check_db.py
"""
from __future__ import annotations

import sys

from sqlalchemy import text

from ubika.db import engine

TABLAS = [
    "distritos", "distrito_alias", "corridas", "raw_listings", "raw_detalles",
    "propiedades", "avisos", "geocode_cache", "puntos_interes", "inpe_domicilios", "entorno",
    "delitos_puntos", "delitos_distrito_mes",
]
VISTAS = ["v_app_propiedades", "v_resumen_distrito", "v_historial_avisos", "v_delitos_distrito_12m"]
LEGADO = ["urbania_listings", "adondevivir_listings", "propiedades_procesadas", "dataset_final"]


def main() -> int:
    try:
        with engine().connect() as conn:
            version = conn.execute(text("SHOW server_version")).scalar_one()
            existentes = set(conn.execute(text(
                "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'"
            )).scalars())
            conteos = {
                t: conn.execute(text(f'SELECT COUNT(*) FROM "{t}"')).scalar_one()
                for t in TABLAS if t in existentes
            }
    except Exception as exc:
        print(f"✗ No se pudo conectar a Neon: {exc}")
        print("  Revisa DATABASE_URL en .env")
        return 1

    print(f"✓ Conectado a Neon (PostgreSQL {version})\n")
    faltan = 0
    for t in TABLAS:
        if t in conteos:
            print(f"  ✓ {t:<18} {conteos[t]:>8,} filas")
        else:
            print(f"  ✗ {t:<18} no existe")
            faltan += 1
    for v in VISTAS:
        print(f"  {'✓' if v in existentes else '✗'} {v}")
        faltan += v not in existentes

    restos = [t for t in LEGADO if t in existentes]
    if restos:
        print(f"\n⚠ Quedan tablas del esquema anterior: {', '.join(restos)}. Corre sql/00_drop_legacy.sql")

    if faltan:
        print(f"\n✗ Faltan {faltan} objetos. Corre en Neon, en orden: 01_schema.sql, 02_seed_distritos.sql, 03_views.sql, 04_delitos.sql")
        return 1
    if conteos.get("distritos", 0) < 50:
        print("\n⚠ El catálogo de distritos está incompleto. Corre sql/02_seed_distritos.sql")
        return 1
    print("\n✓ Esquema completo.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

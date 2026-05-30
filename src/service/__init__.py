"""
service/
========
Capa de acceso a datos — Neon (PostgreSQL).
Importa directamente desde cada módulo, no desde aquí,
para evitar imports circulares.
 
Ejemplo:
    from service.db_client import execute
    from service.urbania_service import upsert_listings, get_stats
    from service.urbania_detalles_service import save_detalle
"""
 
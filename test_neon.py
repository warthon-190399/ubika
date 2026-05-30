"""
test_neon.py
============
Prueba rápida de conexión y escritura a Neon.
Corre desde la raíz del proyecto:

    python test_neon.py
"""

import sys
from pathlib import Path

# Agrega tanto la raíz como src/ al path
ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from service.db_client import get_engine, execute
from service.urbania_service import upsert_listings, get_stats, get_pending_urls
from service.urbania_detalles_service import save_detalle, mark_gone


def separador(titulo: str):
    print(f"\n{'='*50}")
    print(f"  {titulo}")
    print('='*50)


# ------------------------------------------------------------------
# 1. Conexión básica
# ------------------------------------------------------------------
separador("1. Conexión a Neon")
try:
    rows = execute("SELECT version()")
    print(f"✅ Conectado: {rows[0]['version'][:60]}...")
except Exception as e:
    print(f"❌ Fallo de conexión: {e}")
    print("\nVerifica tu DATABASE_URL en .env")
    sys.exit(1)


# ------------------------------------------------------------------
# 2. Tablas existen
# ------------------------------------------------------------------
separador("2. Verificando tablas")
tablas = ["urbania_listings", "urbania_detalles"]
for tabla in tablas:
    try:
        result = execute(f"SELECT COUNT(*) as n FROM {tabla}")
        print(f"✅ {tabla} — {result[0]['n']} filas existentes")
    except Exception as e:
        print(f"❌ {tabla} no existe o hay error: {e}")
        print("   → Corre el SQL de migrations/001_create_urbania_tables.sql en Neon")
        sys.exit(1)


# ------------------------------------------------------------------
# 3. Upsert de listings de prueba
# ------------------------------------------------------------------
separador("3. Upsert de listings (2 registros de prueba)")

test_listings = [
    {
        "url":           "https://urbania.pe/inmueble/test-prop-001",
        "precio":        "S/ 1,500",
        "mantenimiento": "S/ 200",
        "m2_total":      "80",
        "dorms":         "3",
        "banos":         "2",
        "estac":         "1",
        "direccion":     "Av. Test 123",
        "distrito":      "Miraflores, Lima",
    },
    {
        "url":           "https://urbania.pe/inmueble/test-prop-002",
        "precio":        "S/ 2,000",
        "mantenimiento": "",
        "m2_total":      "100",
        "dorms":         "4",
        "banos":         "3",
        "estac":         "2",
        "direccion":     "Jr. Prueba 456",
        "distrito":      "San Isidro, Lima",
    },
]

stats = upsert_listings(test_listings)
if stats["errors"] == 0:
    print(f"✅ Upsert ok — {stats['upserted']} registros insertados")
else:
    print(f"⚠️  Upsert parcial — ok: {stats['upserted']}  errores: {stats['errors']}")


# ------------------------------------------------------------------
# 4. Verificar cola de pendientes
# ------------------------------------------------------------------
separador("4. Cola de pendientes")
pending = get_pending_urls()
print(f"✅ {len(pending)} URLs en cola")
for item in pending[:3]:
    print(f"   prop_id: {item['prop_id'][:16]}...  url: {item['url'][-40:]}")


# ------------------------------------------------------------------
# 5. Guardar detalle para prop-001
# ------------------------------------------------------------------
separador("5. Guardar detalle de prueba")
from service.urbania_service import make_prop_id

prop_id_001 = make_prop_id("https://urbania.pe/inmueble/test-prop-001")
ok = save_detalle(prop_id_001, {
    "antiguedad":        "5 años",
    "descripcion":       "Departamento de prueba en Miraflores, bien ubicado.",
    "publicado_por":     "Inmobiliaria Test SAC",
    "codigo_urbania":    "99999",
    "fecha_publicacion": "Publicado hace 2 días",
})
print(f"{'✅ Detalle guardado' if ok else '❌ Error guardando detalle'}")


# ------------------------------------------------------------------
# 6. Marcar prop-002 como gone (simula publicación eliminada)
# ------------------------------------------------------------------
separador("6. Marcar prop-002 como gone")
prop_id_002 = make_prop_id("https://urbania.pe/inmueble/test-prop-002")
mark_gone(prop_id_002)
print("✅ Marcado como gone")


# ------------------------------------------------------------------
# 7. Stats finales
# ------------------------------------------------------------------
separador("7. Estado final de la tabla")
stats_final = get_stats()
for key, val in stats_final.items():
    icon = {"total": "📊", "ok": "✅", "pending": "⏳", "gone": "🗑️", "error": "⚠️"}.get(key, "  ")
    print(f"  {icon} {key:<15} {val}")


# ------------------------------------------------------------------
# 8. Limpiar datos de prueba
# ------------------------------------------------------------------
separador("8. Limpiando datos de prueba")
try:
    execute("""
        DELETE FROM urbania_listings
        WHERE url IN (
            'https://urbania.pe/inmueble/test-prop-001',
            'https://urbania.pe/inmueble/test-prop-002'
        )
    """)
    print("✅ Datos de prueba eliminados")
except Exception as e:
    print(f"⚠️  No se pudo limpiar: {e}")

print("\n🎉 Todo ok — Neon está listo para el scraping real.\n")
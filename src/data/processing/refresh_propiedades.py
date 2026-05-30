#%%
"""
refresh_propiedades.py
======================
Refresca la vista materializada propiedades_clean
y muestra un resumen del tablón unificado.

Correr después de cada ciclo de scraping:
    python refresh_propiedades.py
"""

import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))
 
from service.db_client import execute


print("\nRefrescando propiedades_union...")
execute("REFRESH MATERIALIZED VIEW propiedades_union")
print("✅ Vista refrescada\n")




#%%
# Resumen general
rows = execute("""
    SELECT
        fuente,
        COUNT(*)                        AS total,
        COUNT(descripcion)              AS con_descripcion,
        COUNT(antiguedad)               AS con_antiguedad,
        COUNT(publicado_por)            AS con_publicado_por
    FROM propiedades_union
    GROUP BY fuente
    ORDER BY fuente
""")

print(f"{'Fuente':<15} {'Total':>7} {'Descripcion':>13} {'Antiguedad':>12} {'Publicado por':>14}")
print("-" * 65)
total_general = 0
for r in rows:
    print(
        f"{r['fuente']:<15} {r['total']:>7} "
        f"{r['con_descripcion']:>13} "
        f"{r['con_antiguedad']:>12} "
        f"{r['con_publicado_por']:>14}"
    )
    total_general += r['total']

print("-" * 65)
print(f"{'TOTAL':<15} {total_general:>7}\n")

# Top distritos
print("Top 10 distritos:")
distritos = execute("""
    SELECT distrito, COUNT(*) AS n
    FROM propiedades_union
    WHERE distrito IS NOT NULL
    GROUP BY distrito
    ORDER BY n DESC
    LIMIT 10
""")
for r in distritos:
    print(f"  {r['distrito']:<35} {r['n']:>5}")
# %%

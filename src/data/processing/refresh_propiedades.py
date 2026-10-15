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
rows = execute("""SELECT * FROM propiedades_union""")


# %%
rows

# %%

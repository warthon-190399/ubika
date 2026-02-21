from playwright.sync_api import sync_playwright
import pandas as pd
import time
import random
import os

# Crear carpeta si no existe y cambiar al directorio
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.abspath(os.path.join(BASE_DIR, "..", ".."))
file_location = os.path.join(BASE_DIR, "data", "raw")
adondevivir_path = os.path.join(file_location, "adondevivir") # New folder

os.makedirs(adondevivir_path, exist_ok=True)
os.chdir(adondevivir_path)
#%%

def scrapear_pagina(page_num):
    base_url = f"https://www.adondevivir.com/departamentos-en-alquiler-pagina-{page_num}-q-lima.html"
    data = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36"
        )
        page = context.new_page()

        print(f"📖 Visitando página {page_num}...")
        try:
            page.goto(base_url, timeout=60000)
            page.wait_for_selector('[data-qa="posting PROPERTY"]', timeout=10000)

            propiedades = page.query_selector_all('[data-qa="posting PROPERTY"]')
            print(f"🔍 {len(propiedades)} propiedades encontradas.")

            for propiedad in propiedades:
                precio = propiedad.query_selector('[data-qa="POSTING_CARD_PRICE"]')
                mantenimiento = propiedad.query_selector('[data-qa="expensas"]')
                direccion = propiedad.query_selector('.postingLocations-module__location-address')
                ubicacion = propiedad.query_selector('[data-qa="POSTING_CARD_LOCATION"]')
                caracteristicas = propiedad.query_selector_all('[data-qa="POSTING_CARD_FEATURES"] span')
                url_propiedad = propiedad.get_attribute('data-to-posting')

                area = dorm = banios = estac = None
                for span in caracteristicas:
                    texto = span.inner_text().lower()
                    if 'm²' in texto or 'm2' in texto:
                        area = texto
                    elif 'dorm.' in texto:
                        dorm = texto
                    elif 'baño' in texto or 'baños' in texto:
                        banios = texto
                    elif 'estac.' in texto:
                        estac = texto

                data.append({
                    "pagina": page_num,
                    "precio": precio.inner_text() if precio else None,
                    "mantenimiento": mantenimiento.inner_text() if mantenimiento else None,
                    "direccion": direccion.inner_text() if direccion else None,
                    "ubicacion": ubicacion.inner_text() if ubicacion else None,
                    "area": area,
                    "dorm": dorm,
                    "banios": banios,
                    "estac": estac,
                    "URL": f"https://www.adondevivir.com{url_propiedad}" if url_propiedad else None
                })

            time.sleep(random.uniform(2, 5))  # Pausa para evitar detección
        except Exception as e:
            print(f"⚠️ Error en página {page_num}: {e}")

        browser.close()

    return data

# Scrapeo de todas las páginas
all_data = []

for pagina in range(1, 142):
    resultados_pagina = scrapear_pagina(pagina)

    # Guardar CSV individual
    if resultados_pagina:
        df_temp = pd.DataFrame(resultados_pagina)
        df_temp.to_csv(f"adondevivir_pagina_{pagina}.csv", index=False)
        print(f"✅ Página {pagina} guardada.")
        all_data.extend(resultados_pagina)
    else:
        print(f"⚠️ Sin datos en página {pagina}.")

# Guardar consolidado
if all_data:
    df_total = pd.DataFrame(all_data)
    df_total.to_csv("adondevivir_todas_las_paginas.csv", index=False)
    print("📦 Archivo consolidado guardado como 'adondevivir_todas_las_paginas.csv'")
else:
    print("⚠️ No se obtuvieron datos en ninguna página.")


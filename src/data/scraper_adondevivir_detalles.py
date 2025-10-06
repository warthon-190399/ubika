import pandas as pd
from playwright.sync_api import sync_playwright
from datetime import datetime, timedelta
import time
import random
import os 

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.abspath(os.path.join(BASE_DIR, "..", ".."))
csv_path = os.path.join(BASE_DIR, "data", "raw", "adondevivir_todas_las_paginas.csv")
output_path = os.path.join(BASE_DIR, "data", "processed", "adondevivir_todo3_completo.csv")

#csv_path = "D:/DS_Portafolio/ubika/data/raw//adondevivir/adondevivir_todo3.csv"
#output_path = "D:/DS_Portafolio/ubika/data/raw/adondevivir/adondevivir_todo3_completo.csv"

df = pd.read_csv(csv_path)

total_registros = len(df)

# Añadir columnas necesarias
df["fecha_publicacion"] = None
df["fecha_publicacion_exacta"] = None
df["visualizaciones"] = None
df["inmobiliaria"] = None
df["antiguedad_inmueble"] = None

# Función para convertir "Publicado hace X días" a fecha exacta
def convertir_a_fecha_exacta(texto_fecha):
    hoy = datetime.now()
    if "día" in texto_fecha:
        dias = int(''.join(filter(str.isdigit, texto_fecha)))
        return (hoy - timedelta(days=dias)).strftime("%Y-%m-%d")
    elif "hora" in texto_fecha:
        horas = int(''.join(filter(str.isdigit, texto_fecha)))
        return (hoy - timedelta(hours=horas)).strftime("%Y-%m-%d")
    elif "mes" in texto_fecha:
        meses = int(''.join(filter(str.isdigit, texto_fecha)))
        return (hoy - timedelta(days=30 * meses)).strftime("%Y-%m-%d")
    elif "ayer" in texto_fecha:
        return (hoy - timedelta(days=1)).strftime("%Y-%m-%d")
    
    elif "hoy" in texto_fecha.lower():
        return hoy.strftime("%Y-%m-%d")
    
    else:
        return None

with sync_playwright() as p:
    for i in range():  # Desde fila 950 hasta 2806 inclusive
        row = df.loc[i]
        url = row["URL"]
        if pd.isna(url):
            continue

        print(f"🔗 Visitando página {i+1}/{total_registros}: {url}")

        try:
            with p.chromium.launch(headless=False) as browser:
                context = browser.new_context()
                page = context.new_page()
                page.goto(url, timeout=60000)
                page.wait_for_load_state("load")

                fecha_pub = page.query_selector('p.userViews-module__post-antiquity-views___8Zfch')
                if fecha_pub:
                    texto_fecha = fecha_pub.inner_text()
                    df.at[i, "fecha_publicacion"] = texto_fecha
                    df.at[i, "fecha_publicacion_exacta"] = convertir_a_fecha_exacta(texto_fecha)

                visuales = page.query_selector_all('p.userViews-module__post-antiquity-views___8Zfch')
                if len(visuales) > 1:
                    df.at[i, "visualizaciones"] = visuales[1].inner_text()

                empresa = page.query_selector('[data-qa="linkMicrositioAnunciante"]')
                if empresa:
                    df.at[i, "inmobiliaria"] = empresa.inner_text()

                antig_icon = page.query_selector('li.icon-feature i.icon-antiguedad')
                if antig_icon:
                    li_padre = antig_icon.evaluate_handle("node => node.parentElement")
                    if li_padre:
                        df.at[i, "antiguedad_inmueble"] = li_padre.inner_text().strip()

                page.close()
                time.sleep(random.uniform(1, 3))  # Espera aleatoria

        except Exception as e:
            print(f"⚠️ Error en {url}: {e}")
            continue

df.to_csv(output_path, index=False)
print(f"✅ Scraping finalizado. Archivo guardado en:\n{output_path}")
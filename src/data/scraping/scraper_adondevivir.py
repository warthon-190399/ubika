"""
scraper_adondevivir.py
======================
Scraper de listings de Adondevivir → Neon.

Uso:
    python scraper_adondevivir.py
"""

import sys
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parent.parent.parent.parent

sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

with open(ROOT / "config.yaml", encoding="utf-8") as f:
    cfg = yaml.safe_load(f)

import time
import random
import datetime
import logging

from playwright.sync_api import sync_playwright
from service.adondevivir_service import upsert_listings



logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


def scrapear_pagina(page_num: int, url_template: str, scrape_date: str) -> list[dict]:
    base_url = url_template.format(page_num=page_num)
    data = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                       "(KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36"
        )
        page = context.new_page()
        logger.info(f"  Visitando página {page_num}: {base_url}")

        try:
            page.goto(base_url, timeout=60000)
            page.wait_for_selector('[data-qa="posting PROPERTY"]', timeout=10000)
            propiedades = page.query_selector_all('[data-qa="posting PROPERTY"]')
            logger.info(f"  {len(propiedades)} propiedades encontradas.")

            for prop in propiedades:
                precio_el    = prop.query_selector('[data-qa="POSTING_CARD_PRICE"]')
                mant_el      = prop.query_selector('[data-qa="expensas"]')
                direccion_el = prop.query_selector('.postingLocations-module__location-address')
                distrito_el  = prop.query_selector('[data-qa="POSTING_CARD_LOCATION"]')
                features     = prop.query_selector_all('[data-qa="POSTING_CARD_FEATURES"] span')
                url_rel      = prop.get_attribute('data-to-posting')

                m2_total = dorms = banos = estac = None
                for span in features:
                    texto = span.inner_text().lower()
                    if 'm²' in texto or 'm2' in texto:
                        m2_total = texto
                    elif 'dorm.' in texto:
                        dorms = texto
                    elif 'baño' in texto or 'baños' in texto:
                        banos = texto
                    elif 'estac.' in texto:
                        estac = texto

                data.append({
                    "scrape_date":  scrape_date,
                    "precio":       precio_el.inner_text()    if precio_el    else None,
                    "mantenimiento": mant_el.inner_text()     if mant_el      else None,
                    "direccion":    direccion_el.inner_text() if direccion_el else None,
                    "distrito":     distrito_el.inner_text()  if distrito_el  else None,
                    "m2_total":     m2_total,
                    "dorms":        dorms,
                    "banos":        banos,
                    "estac":        estac,
                    "url": (
                        f"https://www.adondevivir.com{url_rel}"
                        if url_rel else None
                    ),
                })

            time.sleep(random.uniform(2, 5))
        except Exception as e:
            logger.warning(f"  Error en página {page_num}: {e}")

        browser.close()
    return data


def main():
    scrape_date = str(datetime.date.today())
    sources = cfg["scraping"]["sources"]["adondevivir"]

    for property_type, settings in sources.items():
        url_template = settings["url_template"]
        pages        = settings["pages"]
        logger.info(f"\nAdondevivir — {property_type} ({pages} páginas)")

        for pagina in range(1, pages + 1):
            resultados = scrapear_pagina(pagina, url_template, scrape_date)
            if resultados:
                stats = upsert_listings(resultados)
                logger.info(f"  Página {pagina} → upserted: {stats['upserted']}  errores: {stats['errors']}")
            else:
                logger.warning(f"  Sin datos en página {pagina}.")


if __name__ == "__main__":
    main()

"""
scraper_urbania_detalles.py
===========================
Lee URLs desde urbania_alquiler.csv y scrapea detalles en paralelo.
Usa N workers simultáneos, cada uno con su propio browser Playwright.

Instalación:
    pip install playwright beautifulsoup4 pandas lxml
    playwright install chromium

Uso:
    python scraper_urbania_detalles.py
    python scraper_urbania_detalles.py --workers 5
    python scraper_urbania_detalles.py --show
"""

import re
import csv
import time
import random
import argparse
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock

import pandas as pd
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout


# -------------------------------------------------------------------
# CONFIG
# -------------------------------------------------------------------

INPUT_CSV  = r"D:\projects\ubika\urbania_alquiler.csv"
OUTPUT_CSV = r"D:\projects\ubika\urbania_alquiler_detalles.csv"

WORKERS       = 4     # browsers en paralelo — sube a 6-8 si tu máquina aguanta
DELAY_BETWEEN = (1, 3)

FIELDNAMES = [
    "url", "antiguedad", "descripcion",
    "publicado_por", "codigo_urbania", "fecha_publicacion",
]

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
]

# Lock para escribir al CSV y al contador de progreso de forma thread-safe
_write_lock = Lock()
_counter    = {"done": 0, "total": 0}


# -------------------------------------------------------------------
# HELPERS
# -------------------------------------------------------------------

def random_ua():
    return random.choice(USER_AGENTS)

def dismiss_popup(page):
    for sel in [
        "button[aria-label='Cerrar popup']",
        "button[class*='popup-overlay-button']",
        "[class*='popup'] button",
    ]:
        try:
            btn = page.wait_for_selector(sel, timeout=2_000, state="visible")
            if btn:
                btn.dispatch_event("click")
                time.sleep(0.5)
                return
        except PWTimeout:
            continue


# -------------------------------------------------------------------
# PARSER
# -------------------------------------------------------------------

def parse_property(html: str, url: str) -> dict:
    soup = BeautifulSoup(html, "lxml")
    data = dict.fromkeys(FIELDNAMES, "")
    data["url"] = url

    # Antigüedad
    icon = soup.select_one("i.icon-antiguedad")
    if icon:
        raw = icon.parent.get_text(" ", strip=True)
        data["antiguedad"] = re.sub(r"\s+", " ", raw).strip()

    # Descripción — selector con fallback genérico
    desc = (
        soup.select_one("div.description-module__wrapper-description___2rEoY") or
        soup.select_one("div[class*='wrapper-description']") or
        soup.select_one("div[class*='description']")
    )
    if desc:
        text = desc.get_text(" ", strip=True)          # saltos → espacio
        text = re.sub(r"\*+", "", text)                 # quitar **
        text = re.sub(r"\s{2,}", " ", text)             # espacios múltiples → uno
        data["descripcion"] = text.strip()

    # Publicado por
    pub = (
        soup.select_one("h3.publisherData-module__publisher-name___6HD5R") or
        soup.select_one("[class*='publisher-name']")
    )
    if pub:
        data["publicado_por"] = pub.get_text(strip=True)

    # Código Urbania
    code = (
        soup.select_one("li.publiserCodes-module__publisher-codes-item___1MPT4") or
        soup.select_one("[class*='publisher-codes-item']")
    )
    if code:
        m = re.search(r"(\d+)", code.get_text(" ", strip=True))
        if m:
            data["codigo_urbania"] = m.group(1)

    # Fecha publicación
    fecha = (
        soup.select_one("p.userViews-module__post-antiquity-views___8Zfch") or
        soup.select_one("[class*='post-antiquity']")
    )
    if fecha:
        data["fecha_publicacion"] = fecha.get_text(strip=True)

    return data


# -------------------------------------------------------------------
# WORKER — cada thread corre su propio browser
# -------------------------------------------------------------------

def scrape_url(url: str, headless: bool, csv_writer, csv_file) -> dict:
    """Abre un browser limpio, scrapea la URL, escribe al CSV, cierra."""
    empty = dict.fromkeys(FIELDNAMES, "")
    empty["url"] = url

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=headless,
            args=[
                "--no-sandbox",
                "--disable-blink-features=AutomationControlled",
                "--window-size=1366,768",
            ],
        )
        context = browser.new_context(
            user_agent=random_ua(),
            viewport={"width": 1366, "height": 768},
            locale="es-PE",
            timezone_id="America/Lima",
            extra_http_headers={
                "Accept-Language": "es-PE,es;q=0.9,en;q=0.8",
                "sec-ch-ua": '"Chromium";v="124", "Google Chrome";v="124"',
                "sec-ch-ua-platform": '"Windows"',
            },
        )
        context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            Object.defineProperty(navigator, 'plugins',   { get: () => [1, 2, 3] });
            Object.defineProperty(navigator, 'languages', { get: () => ['es-PE', 'es', 'en'] });
            window.chrome = { runtime: {} };
        """)
        page = context.new_page()
        page.route("**/*.{png,jpg,jpeg,gif,svg,woff,woff2,ttf,mp4,webp}", lambda r: r.abort())
        page.route("**/{ads,analytics,gtm,pixel,tracking}**", lambda r: r.abort())

        try:
            page.goto(url, wait_until="domcontentloaded", timeout=30_000)
            dismiss_popup(page)
            page.wait_for_selector(
                "div[class*='wrapper-description'], div[class*='description']",
                timeout=15_000,
            )
            time.sleep(random.uniform(*DELAY_BETWEEN))
            data = parse_property(page.content(), url)
        except PWTimeout:
            data = empty
        except Exception as e:
            data = empty
        finally:
            context.close()
            browser.close()

    # Progreso + escritura thread-safe
    with _write_lock:
        _counter["done"] += 1
        n, total = _counter["done"], _counter["total"]
        status = data.get("publicado_por") or "⚠️ sin datos"
        print(f"  [{n}/{total}] {status}  —  {url.split('/')[-1]}")
        csv_writer.writerow(data)
        csv_file.flush()

    return data


# -------------------------------------------------------------------
# MAIN
# -------------------------------------------------------------------

def scrape_details(headless=True, workers=WORKERS):
    df   = pd.read_csv(INPUT_CSV)
    urls = df["url"].dropna().astype(str).unique().tolist()

    _counter["total"] = len(urls)
    print(f"\n📦 {len(urls)} URLs  |  {workers} workers en paralelo\n")

    csv_path = Path(OUTPUT_CSV)
    results  = []

    with open(csv_path, "w", newline="", encoding="utf-8-sig") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=FIELDNAMES)
        writer.writeheader()

        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = {
                pool.submit(scrape_url, url, headless, writer, csv_file): url
                for url in urls
            }
            for future in as_completed(futures):
                try:
                    results.append(future.result())
                except Exception as e:
                    print(f"  ❌ Error inesperado: {e}")

    print(f"\n✅ {len(results)} registros → {csv_path}")
    return pd.DataFrame(results)


# -------------------------------------------------------------------
# CLI
# -------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--show",    action="store_true", help="Mostrar navegadores")
    parser.add_argument("--workers", type=int, default=WORKERS, help="Browsers en paralelo")
    args = parser.parse_args()

    scrape_details(headless=not args.show, workers=args.workers)
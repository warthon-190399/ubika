"""
scraper_urbania_venta.py
========================
Scraper de inmuebles en venta en Urbania.pe usando Playwright (stealth).
Paginación: ?page=N — cada página abre un browser fresco para evitar detección.

Instalación:
    pip install playwright beautifulsoup4 lxml
    playwright install chromium

Uso:
    python scraper_urbania_venta.py
    python scraper_urbania_venta.py --url "https://urbania.pe/buscar/venta-de-departamentos-en-miraflores" --pages 3
    python scraper_urbania_venta.py --show
"""

import re
import csv
import time
import random
import argparse
from pathlib import Path
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout
from bs4 import BeautifulSoup


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

BASE_URL   = "https://urbania.pe/buscar/alquiler-de-propiedades-en-lima"
OUTPUT_CSV = "urbania_alquiler.csv"
MAX_PAGES  = 1
DELAY_PAGE = (2, 4)

FIELDNAMES = ["url", "precio", "m2_total", "dorms", "banos", "estac", "direccion", "distrito"]


# ---------------------------------------------------------------------------
# Anti-ban helpers
# ---------------------------------------------------------------------------

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
]

def random_ua():
    return random.choice(USER_AGENTS)

def human_delay(lo=0.5, hi=1.5):
    base = random.uniform(lo, hi)
    if random.random() < 0.2:
        base += random.uniform(1, 3)
    time.sleep(base)

def random_scroll(page):
    for _ in range(random.randint(2, 5)):
        page.mouse.wheel(0, random.randint(300, 800))
        time.sleep(random.uniform(0.3, 0.9))

def dismiss_popup(page):
    for sel in [
        "button[aria-label='Cerrar popup']",
        "button[class*='popup-overlay-button']",
        "[class*='popup'] button",
        "[class*='modal'] button",
    ]:
        try:
            btn = page.wait_for_selector(sel, timeout=3_000, state="visible")
            if btn:
                btn.dispatch_event("click")
                time.sleep(0.7)
                print("  🗙 Popup cerrado")
                return
        except PWTimeout:
            continue

def build_url(base: str, page_num: int) -> str:
    sep = "&" if "?" in base else "?"
    return base if page_num == 1 else f"{base}{sep}page={page_num}"


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------

def parse_listings(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "lxml")
    posting_tops = (
        soup.select("div.postingCard-module__posting-top") or
        soup.select("div[class*='posting-top']")
    )

    results = []
    for card in posting_tops:
        data = {}

        price_tag = card.select_one("[class='postingPrices-module__price']")
        data["precio"] = price_tag.get_text(strip=True) if price_tag else ""

        feat_spans = card.select(
            "[data-qa='POSTING_CARD_FEATURES'] span, "
            "span.postingMainFeatures-module__posting-main-features-span"
        )
        feat_text = " | ".join(s.get_text(strip=True) for s in feat_spans)

        m2    = re.search(r"([\d,\.]+)\s*m²", feat_text)
        dorms = re.search(r"(\d+)\s*dorm", feat_text, re.I)
        banos = re.search(r"(\d+)\s*ba[ñn]", feat_text, re.I)
        estac = re.search(r"(\d+)\s*estac", feat_text, re.I)
        data["m2_total"] = m2.group(1)    if m2    else ""
        data["dorms"]    = dorms.group(1) if dorms else ""
        data["banos"]    = banos.group(1) if banos else ""
        data["estac"]    = estac.group(1) if estac else ""

        addr_tag = card.select_one(
            ".postingLocations-module__location-address, [class*='location-address']"
        )
        data["direccion"] = addr_tag.get_text(strip=True) if addr_tag else ""

        loc_tag = card.select_one(
            "[data-qa='POSTING_CARD_LOCATION'], [class*='location-text']"
        )
        loc_text = loc_tag.get_text(strip=True) if loc_tag else ""
        parts = [p.strip() for p in loc_text.split(",")]
        data["distrito"] = parts[0] + f", {parts[1]}" if len(parts) > 1 else ""

        link = card.select_one("a[href*='/inmueble/']") or card.select_one("a[href]")
        if link:
            href = link.get("href", "")
            data["url"] = href if href.startswith("http") else f"https://urbania.pe{href}"
        else:
            data["url"] = ""

        if data.get("precio") or data.get("direccion"):
            results.append(data)

    return results


# ---------------------------------------------------------------------------
# Scraping — browser fresco por página
# ---------------------------------------------------------------------------

def scrape_page(page_url: str, headless: bool) -> list[dict]:
    """Abre un browser limpio, scrapea una página, lo cierra y retorna los listings."""
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=headless,
            args=[
                "--no-sandbox",
                "--disable-blink-features=AutomationControlled",
                "--disable-infobars",
                "--window-size=1366,768",
            ],
        )
        context = browser.new_context(
            user_agent=random_ua(),
            viewport={"width": 1366, "height": 768},
            locale="es-PE",
            timezone_id="America/Lima",
            java_script_enabled=True,
            extra_http_headers={
                "Accept-Language": "es-PE,es;q=0.9,en;q=0.8",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,/;q=0.8",
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
        page.route("*/.{png,jpg,jpeg,gif,svg,woff,woff2,ttf,mp4,webp}", lambda r: r.abort())
        page.route("*/{ads,analytics,gtm,pixel,tracking}*", lambda r: r.abort())

        try:
            page.goto(page_url, wait_until="domcontentloaded", timeout=30_000)
            dismiss_popup(page)
            page.wait_for_selector(
                "[data-qa='POSTING_CARD_PRICE'], .postingCard-module__posting-top",
                timeout=15_000,
            )
            random_scroll(page)
            time.sleep(random.uniform(1, 2))
            listings = parse_listings(page.content())
        except PWTimeout:
            print(f"  ⚠️  Timeout — saltando esta página")
            listings = []
        finally:
            context.close()
            browser.close()

    return listings


def scrape_urbania(url=BASE_URL, max_pages=MAX_PAGES, output_csv=OUTPUT_CSV, headless=True):
    csv_path = Path(output_csv)

    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        csv.DictWriter(f, fieldnames=FIELDNAMES).writeheader()

    all_listings = []

    for page_num in range(1, max_pages + 1):
        page_url = build_url(url, page_num)
        print(f"\n📄 Página {page_num}/{max_pages}: {page_url}")

        listings = scrape_page(page_url, headless)
        print(f"  → {len(listings)} propiedades encontradas")

        if not listings:
            print("  ⚠️  Sin resultados — última página o bloqueo.")
            break

        with open(csv_path, "a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
            for row in listings:
                writer.writerow({k: row.get(k, "") for k in FIELDNAMES})
                print(f"    {row.get('direccion') or row.get('distrito')} | {row.get('precio')}")
                all_listings.append(row)

        if page_num < max_pages:
            wait = random.uniform(*DELAY_PAGE)
            print(f"  ⏳ Esperando {wait:.1f}s antes de siguiente página...")
            time.sleep(wait)

    print(f"\n✅ {len(all_listings)} propiedades guardadas en {csv_path}")
    return all_listings


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Scraper Urbania.pe")
    parser.add_argument("--url",    default=BASE_URL,   help="URL base de búsqueda")
    parser.add_argument("--pages",  default=MAX_PAGES,  type=int, help="Páginas a scrapear")
    parser.add_argument("--output", default=OUTPUT_CSV, help="Archivo CSV de salida")
    parser.add_argument("--show",   action="store_true", help="Mostrar navegador (no headless)")
    args = parser.parse_args()

    scrape_urbania(
        url        = args.url,
        max_pages  = args.pages,
        output_csv = args.output,
        headless   = not args.show,
    )
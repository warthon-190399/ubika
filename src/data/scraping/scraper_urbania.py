"""
scraper_urbania.py
==================
Scraper de listings de Urbania.pe.
Escribe directamente a Supabase (tabla urbania_listings).
Ya no genera CSV.

Uso:
    python scraper_urbania.py
    python scraper_urbania.py --url "https://urbania.pe/buscar/venta-de-departamentos-en-miraflores" --pages 3
    python scraper_urbania.py --show
"""

import re
import time
import random
import datetime
import argparse
import logging

from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout
from bs4 import BeautifulSoup

from service.urbania_service import upsert_listings, make_prop_id

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

# URLs y páginas vienen del config.yaml
_CFG      = _CFG["scraping"]["sources"]["urbania"]
BASE_URL  = _CFG["rent"]["url_template"]
MAX_PAGES = _CFG["rent"]["pages"]
DELAY_PAGE = (2, 4)

FIELDNAMES = [
    "url", "scrape_date",
    "precio", "mantenimiento", "m2_total",
    "dorms", "banos", "estac",
    "direccion", "distrito",
]

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
]


# ---------------------------------------------------------------------------
# Anti-ban helpers
# ---------------------------------------------------------------------------

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
                return
        except PWTimeout:
            continue

def build_url(base: str, page_num: int) -> str:
    sep = "&" if "?" in base else "?"
    return base if page_num == 1 else f"{base}{sep}page={page_num}"


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------

def parse_listings(html: str, scrape_date: str) -> list[dict]:
    soup = BeautifulSoup(html, "lxml")
    posting_tops = (
        soup.select("div.postingCard-module__posting-top") or
        soup.select("div[class*='posting-top']")
    )

    results = []
    for card in posting_tops:
        data: dict = {"scrape_date": scrape_date}

        price_tag = card.select_one("[class='postingPrices-module__price']")
        data["precio"] = price_tag.get_text(strip=True) if price_tag else ""

        mant_tag = card.select_one(
            "[class='postingPrices-module__expenses postingPrices-module__expenses-property-listing']"
        )
        data["mantenimiento"] = mant_tag.get_text(strip=True) if mant_tag else ""

        feat_spans = card.select(
            "[data-qa='POSTING_CARD_FEATURES'] span, "
            "span.postingMainFeatures-module__posting-main-features-span"
        )
        feat_text = " | ".join(s.get_text(strip=True) for s in feat_spans)

        m2    = re.search(r"([\d,\.]+)\s*m²", feat_text)
        dorms = re.search(r"(\d+)\s*dorm",    feat_text, re.I)
        banos = re.search(r"(\d+)\s*ba[ñn]",  feat_text, re.I)
        estac = re.search(r"(\d+)\s*estac",   feat_text, re.I)
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

def scrape_page(page_url: str, scrape_date: str, headless: bool) -> list[dict]:
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
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
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

        listings = []
        try:
            page.goto(page_url, wait_until="domcontentloaded", timeout=30_000)
            dismiss_popup(page)
            page.wait_for_selector(
                "[data-qa='POSTING_CARD_PRICE'], .postingCard-module__posting-top",
                timeout=15_000,
            )
            random_scroll(page)
            time.sleep(random.uniform(1, 2))
            listings = parse_listings(page.content(), scrape_date)
        except PWTimeout:
            logger.warning(f"  Timeout — saltando página {page_url}")
        finally:
            context.close()
            browser.close()

    return listings


# ---------------------------------------------------------------------------
# Orquestador principal
# ---------------------------------------------------------------------------

def scrape_urbania(url=BASE_URL, max_pages=MAX_PAGES, headless=True):
    scrape_date  = str(datetime.date.today())
    all_listings = []

    logger.info(f"Iniciando scraping: {max_pages} página(s) desde {url}")

    for page_num in range(1, max_pages + 1):
        page_url = build_url(url, page_num)
        logger.info(f"Página {page_num}/{max_pages}: {page_url}")

        listings = scrape_page(page_url, scrape_date, headless)
        logger.info(f"  {len(listings)} propiedades encontradas")

        if not listings:
            logger.warning("  Sin resultados — posible última página o bloqueo.")
            break

        # ── Guardar directo a Supabase ──────────────────────────────
        stats = upsert_listings(listings)
        logger.info(f"  Supabase → upserted: {stats['upserted']}  errores: {stats['errors']}")

        all_listings.extend(listings)

        if page_num < max_pages:
            wait = random.uniform(*DELAY_PAGE)
            logger.info(f"  Esperando {wait:.1f}s...")
            time.sleep(wait)

    logger.info(f"Scraping finalizado: {len(all_listings)} propiedades procesadas")
    return all_listings


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Scraper Urbania.pe → Supabase")
    parser.add_argument("--url",   default=BASE_URL,  help="URL base de búsqueda")
    parser.add_argument("--pages", default=MAX_PAGES, type=int, help="Páginas a scrapear")
    parser.add_argument("--show",  action="store_true", help="Mostrar navegador")
    args = parser.parse_args()

    scrape_urbania(url=args.url, max_pages=args.pages, headless=not args.show)
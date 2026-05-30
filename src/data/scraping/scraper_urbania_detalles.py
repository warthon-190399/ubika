"""
scraper_urbania_detalles.py
===========================
Lee la cola de URLs pendientes desde Supabase (detalle_status = 'pending')
y scrapea los detalles en paralelo con N browsers.

Escribe directamente a urbania_detalles y actualiza detalle_status
en urbania_listings por cada propiedad procesada.

Uso:
    python scraper_urbania_detalles.py
    python scraper_urbania_detalles.py --workers 5
    python scraper_urbania_detalles.py --show
    python scraper_urbania_detalles.py --retry-errors   # reintenta los 'error' también
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))  # llega a la raíz
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))
import re
import time
import random
import datetime
import argparse
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock

from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout
from bs4 import BeautifulSoup

from service.urbania_service          import get_pending_urls, get_stats
from service.urbania_detalles_service import save_detalle, mark_gone, mark_error

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

WORKERS       = 4
DELAY_BETWEEN = (1, 3)

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
]

_print_lock = Lock()
_counter    = {"done": 0, "total": 0}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

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

def _is_gone(page) -> bool:
    """Detecta si la publicación fue dada de baja."""
    url = page.url
    if any(x in url for x in ["404", "not-found"]):
        return True
    try:
        page.wait_for_selector(
            "div[class*='not-found'], div[class*='error-page'], h1[class*='404']",
            timeout=2_000,
        )
        return True
    except PWTimeout:
        return False


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------

def parse_property(html: str) -> dict:
    soup = BeautifulSoup(html, "lxml")
    data: dict = {}

    icon = soup.select_one("i.icon-antiguedad")
    if icon:
        raw = icon.parent.get_text(" ", strip=True)
        data["antiguedad"] = re.sub(r"\s+", " ", raw).strip()

    desc = (
        soup.select_one("div.description-module__wrapper-description___2rEoY") or
        soup.select_one("div[class*='wrapper-description']") or
        soup.select_one("div[class*='description']")
    )
    if desc:
        text = desc.get_text(" ", strip=True)
        text = re.sub(r"\*+", "", text)
        text = re.sub(r"\s{2,}", " ", text)
        data["descripcion"] = text.strip()

    pub = (
        soup.select_one("h3.publisherData-module__publisher-name___6HD5R") or
        soup.select_one("[class*='publisher-name']")
    )
    if pub:
        data["publicado_por"] = pub.get_text(strip=True)

    code = (
        soup.select_one("li.publiserCodes-module__publisher-codes-item___1MPT4") or
        soup.select_one("[class*='publisher-codes-item']")
    )
    if code:
        m = re.search(r"(\d+)", code.get_text(" ", strip=True))
        if m:
            data["codigo_urbania"] = m.group(1)

    fecha = (
        soup.select_one("p.userViews-module__post-antiquity-views___8Zfch") or
        soup.select_one("[class*='post-antiquity']")
    )
    if fecha:
        data["fecha_publicacion"] = fecha.get_text(strip=True)

    return data


# ---------------------------------------------------------------------------
# Worker — un browser por hilo
# ---------------------------------------------------------------------------

def scrape_one(item: dict, headless: bool) -> str:
    """
    Scrapea una URL, guarda en Supabase y devuelve el status resultante.
    item = {"prop_id": "...", "url": "..."}
    """
    prop_id = item["prop_id"]
    url     = item["url"]
    status  = "error"

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

            if _is_gone(page):
                mark_gone(prop_id)
                status = "gone"
            else:
                page.wait_for_selector(
                    "div[class*='wrapper-description'], div[class*='description']",
                    timeout=15_000,
                )
                time.sleep(random.uniform(*DELAY_BETWEEN))
                data = parse_property(page.content())
                data["scrape_date"] = str(datetime.date.today())

                if save_detalle(prop_id, data):
                    status = "ok"
                else:
                    status = "error"

        except PWTimeout:
            mark_error(prop_id)
            status = "error"
        except Exception as exc:
            logger.error(f"  Excepción inesperada en {url}: {exc}")
            mark_error(prop_id)
            status = "error"
        finally:
            context.close()
            browser.close()

    # Log de progreso thread-safe
    with _print_lock:
        _counter["done"] += 1
        n, total = _counter["done"], _counter["total"]
        icon = {"ok": "✓", "gone": "✗", "error": "⚠"}.get(status, "?")
        logger.info(f"  [{n}/{total}] {icon} {status:<6}  {url.split('/')[-1][:60]}")

    return status


# ---------------------------------------------------------------------------
# Orquestador principal
# ---------------------------------------------------------------------------

def scrape_details(headless=True, workers=WORKERS, retry_errors=False):
    # Obtener cola desde Supabase
    pending = get_pending_urls()
    if retry_errors:
        from service.supabase_client import get_client
        sb = get_client()
        errors = sb.table("urbania_listings").select("prop_id, url").eq(
            "detalle_status", "error"
        ).execute()
        # evitar duplicados
        pending_ids = {r["prop_id"] for r in pending}
        for r in (errors.data or []):
            if r["prop_id"] not in pending_ids:
                pending.append(r)

    if not pending:
        logger.info("No hay URLs pendientes en Supabase.")
        stats = get_stats()
        logger.info(f"Estado actual: {stats}")
        return

    _counter["total"] = len(pending)
    _counter["done"]  = 0

    logger.info(f"\nCola: {len(pending)} URLs  |  {workers} workers\n")

    results = {"ok": 0, "gone": 0, "error": 0}

    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {
            pool.submit(scrape_one, item, headless): item
            for item in pending
        }
        for future in as_completed(futures):
            try:
                status = future.result()
                results[status] = results.get(status, 0) + 1
            except Exception as exc:
                logger.error(f"  Error en future: {exc}")
                results["error"] += 1

    logger.info(
        f"\nFinalizado → ok: {results['ok']}  "
        f"gone: {results['gone']}  "
        f"error: {results['error']}"
    )
    logger.info(f"Estado Supabase: {get_stats()}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Scraper detalles Urbania → Supabase")
    parser.add_argument("--show",         action="store_true", help="Mostrar navegadores")
    parser.add_argument("--workers",      type=int, default=WORKERS)
    parser.add_argument("--retry-errors", action="store_true",
                        help="Reintentar también los que quedaron en status='error'")
    args = parser.parse_args()

    scrape_details(
        headless=not args.show,
        workers=args.workers,
        retry_errors=args.retry_errors,
    )
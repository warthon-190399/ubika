"""
scraper_adondevivir_detalles.py
================================
Lee la cola de pendientes desde Neon y scrapea los detalles.

Uso:
    python scraper_adondevivir_detalles.py
    python scraper_adondevivir_detalles.py --show
    python scraper_adondevivir_detalles.py --retry-errors
"""

import sys
from pathlib import Path
import yaml
import random
import datetime
import argparse
import logging
import time

from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock

from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

ROOT = Path(__file__).resolve().parent.parent.parent.parent

sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

with open(ROOT / "config.yaml", encoding="utf-8") as f:
    cfg = yaml.safe_load(f)

from service.adondevivir_service import (
    get_pending_urls,
    get_error_urls,
    get_stats
)

from service.adondevivir_detalles_service import (
    save_detalle,
    mark_gone,
    mark_error
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)

logger = logging.getLogger(__name__)

# =========================
# CONFIG
# =========================

SCRAPER_CFG = cfg.get("scraper", {})

DEFAULT_WORKERS = SCRAPER_CFG.get("workers", 4)
DELAY_BETWEEN = tuple(SCRAPER_CFG.get("delay_between", [1, 3]))

_print_lock = Lock()
_counter = {"done": 0, "total": 0}


def _is_gone(page) -> bool:
    url = page.url
    if any(x in url for x in ["404", "not-found", "page-not-found"]):
        return True
    if "/propiedades/clasificado/" not in url and "adondevivir.com" in url:
        return True
    try:
        page.wait_for_selector(
            "div[class*='not-found'], div[class*='error-page'], h1[class*='404']",
            timeout=2_000,
        )
        return True
    except PWTimeout:
        return False


def scrape_one(item: dict, headless: bool) -> str:
    prop_id = item["prop_id"]
    url     = item["url"]
    status  = "error"

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                       "(KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36"
        )
        page = context.new_page()

        try:
            page.goto(url, timeout=60000)
            page.wait_for_load_state("load")

            if _is_gone(page):
                mark_gone(prop_id)
                status = "gone"
            else:
                data: dict = {"scrape_date": str(datetime.date.today())}

                fecha_el = page.query_selector('p.userViews-module__post-antiquity-views___8Zfch')
                if fecha_el:
                    data["fecha_publicacion"] = fecha_el.inner_text()

                empresa_el = page.query_selector('[data-qa="linkMicrositioAnunciante"]')
                if empresa_el:
                    data["publicado_por"] = empresa_el.inner_text()

                antig_icon = page.query_selector('li.icon-feature i.icon-antiguedad')
                if antig_icon:
                    li = antig_icon.evaluate_handle("node => node.parentElement")
                    if li:
                        data["antiguedad"] = li.inner_text().strip()

                time.sleep(random.uniform(*DELAY_BETWEEN))

                status = "ok" if save_detalle(prop_id, data) else "error"

        except PWTimeout:
            mark_error(prop_id)
            status = "error"
        except Exception as exc:
            logger.error(f"  Excepción en {url}: {exc}")
            mark_error(prop_id)
            status = "error"
        finally:
            context.close()
            browser.close()

    with _print_lock:
        _counter["done"] += 1
        n, total = _counter["done"], _counter["total"]
        icon = {"ok": "✓", "gone": "✗", "error": "⚠"}.get(status, "?")
        logger.info(f"  [{n}/{total}] {icon} {status:<6}  {url.split('/')[-1][:60]}")

    return status


def scrape_details(headless=True, workers=DEFAULT_WORKERS, retry_errors=False):
    pending = get_pending_urls()

    if retry_errors:
        seen = {r["prop_id"] for r in pending}
        for r in get_error_urls():
            if r["prop_id"] not in seen:
                pending.append(r)

    if not pending:
        logger.info("No hay URLs pendientes.")
        logger.info(f"Estado: {get_stats()}")
        return

    _counter["total"] = len(pending)
    _counter["done"]  = 0
    logger.info(f"\nCola: {len(pending)} URLs  |  {workers} workers\n")

    results = {"ok": 0, "gone": 0, "error": 0}
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(scrape_one, item, headless): item for item in pending}
        for future in as_completed(futures):
            try:
                status = future.result()
                results[status] = results.get(status, 0) + 1
            except Exception as exc:
                logger.error(f"  Error en future: {exc}")
                results["error"] += 1

    logger.info(f"\nFinalizado → ok: {results['ok']}  gone: {results['gone']}  error: {results['error']}")
    logger.info(f"Estado Neon: {get_stats()}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--show",         action="store_true")
    parser.add_argument("--workers",      type=int, default=DEFAULT_WORKERS)
    parser.add_argument("--retry-errors", action="store_true")
    args = parser.parse_args()

    scrape_details(headless=not args.show, workers=args.workers, retry_errors=args.retry_errors)
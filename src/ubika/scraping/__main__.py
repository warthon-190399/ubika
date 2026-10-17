"""
Scraper de avisos (portales Navent: adondevivir, urbania) → Neon.

Dos pasos por operación:
1. Listado: recorre las páginas de resultados hasta juntar `max_avisos` unidades
   (las tarjetas de proyectos se ignoran) y las guarda en raw_listings con la fecha de hoy.
2. Detalle: abre solo las URLs que todavía no están en raw_detalles.
   Si una ficha falla por timeout no se guarda, y se reintenta en la siguiente corrida.

Uso:
    python -m ubika.scraping --operacion alquiler
    python -m ubika.scraping --operacion venta --max 100
    python -m ubika.scraping --operacion venta --solo-detalle     # completa detalles pendientes
    python -m ubika.scraping --operacion alquiler --ver           # muestra el navegador
"""
from __future__ import annotations

import argparse
import datetime as dt
import logging
import random
import time
from urllib.parse import urlparse

from ubika.config import cfg
from ubika.db import corrida, read_df, upsert
from ubika.scraping.navent import TIPO_UNIDAD, parsear_detalle, parsear_listado

log = logging.getLogger(__name__)

USER_AGENT = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")


BLOQUEO = (403, 429)


class Navegador:
    """
    Chromium real (Playwright). Solo descarga HTML: bloquea imágenes, fuentes y estilos.
    Si el portal responde 403/429 (demasiadas visitas seguidas), espera, abre una sesión
    nueva y reintenta. Si sigue bloqueado, devuelve ese status y el llamador se detiene.
    """

    ESPERAS_BLOQUEO = (45, 120, 240)     # segundos antes de cada reintento

    def __init__(self, headless: bool = True):
        self.headless = headless
        self.timeout = cfg()["scraping"]["timeout_ms"]

    def __enter__(self):
        from playwright.sync_api import sync_playwright
        self._pw = sync_playwright().start()
        self._browser = self._pw.chromium.launch(headless=self.headless)
        self._ctx = None
        self._sesion_nueva()
        return self

    def __exit__(self, *exc):
        # Con Ctrl+C Playwright ya puede haber cerrado todo: cerrar sin volver a fallar
        for cerrar in (lambda: self._ctx and self._ctx.close(), self._browser.close, self._pw.stop):
            try:
                cerrar()
            except Exception:
                pass

    def _sesion_nueva(self):
        if self._ctx:
            self._ctx.close()
        self._ctx = self._browser.new_context(user_agent=USER_AGENT, locale="es-PE")
        self._ctx.route("**/*", lambda r: r.abort()
                        if r.request.resource_type in ("image", "media", "font", "stylesheet") else r.continue_())
        self._page = self._ctx.new_page()

    def _abrir(self, url: str) -> tuple[int, str, str]:
        resp = self._page.goto(url, wait_until="domcontentloaded", timeout=self.timeout)
        return (resp.status if resp else 0), self._page.url, self._page.content()

    def html(self, url: str) -> tuple[int, str, str]:
        """(status HTTP, URL final tras redirecciones, HTML)."""
        status, final, html = self._abrir(url)
        for espera in self.ESPERAS_BLOQUEO:
            if status not in BLOQUEO:
                break
            log.warning("  El portal respondió %d (demasiadas visitas). Espero %d s y reintento con sesión nueva…",
                        status, espera)
            time.sleep(espera)
            self._sesion_nueva()
            status, final, html = self._abrir(url)
        return status, final, html


def _pausa(clave: str = "pausa_seg"):
    a, b = cfg()["scraping"].get(clave) or cfg()["scraping"]["pausa_seg"]
    time.sleep(random.uniform(a, b))


def _misma_pagina(pedida: str, final: str) -> bool:
    return urlparse(pedida).path.rstrip("/") == urlparse(final).path.rstrip("/")


# ── Paso 1: listado ──────────────────────────────────────────

def scrapear_listado(nav, fuente: str, operacion: str, max_avisos: int, hoy: dt.date) -> int:
    conf = cfg()["scraping"]["fuentes"][fuente][operacion]
    plantilla = conf["url"]
    base = "{0.scheme}://{0.netloc}".format(urlparse(plantilla))

    # Retomar: lo que ya se guardó hoy cuenta para el máximo y se sigue desde la página siguiente
    previos = read_df("""SELECT url, pagina FROM raw_listings
                         WHERE fuente = :f AND operacion = :o AND scrape_date = :d""",
                      {"f": fuente, "o": operacion, "d": hoy})
    guardados: dict[str, dict] = {u: {} for u in previos["url"]}
    pagina = int(previos["pagina"].max()) + 1 if len(previos) else 1
    if len(previos):
        log.info("  Retomando: %d avisos ya guardados hoy, sigo desde la página %d", len(previos), pagina)

    with corrida("scraping_listado", fuente=fuente, operacion=operacion, max_avisos=max_avisos) as c:
        leidas = 0
        max_paginas = cfg()["scraping"].get("max_paginas", 5)   # respeta el robots.txt del portal
        while len(guardados) < max_avisos:
            if pagina > max_paginas:
                log.info("  Tope de %d páginas por listado (robots.txt); para más volumen, agrega listados por distrito", max_paginas)
                break
            url = plantilla.format(pagina=pagina)
            status, final, html = nav.html(url)
            if status in BLOQUEO:
                c.mensaje = (f"El portal bloqueó en la página {pagina} ({status}). "
                             f"Quedan {len(guardados)} avisos guardados; vuelve a correr en un rato y retoma.")
                log.warning("  %s", c.mensaje)
                break
            if status >= 400:
                raise RuntimeError(f"El portal respondió {status} en {url}")
            if pagina > 1 and not _misma_pagina(url, final):
                log.info("  Fin de resultados (la página %d redirige a %s)", pagina, final)
                break
            avisos, total = parsear_listado(html, base)
            if pagina == 1:
                log.info("  %s %s: el portal anuncia %s avisos", fuente, operacion, f"{total:,}" if total else "?")
            if not avisos:
                log.warning("  Página %d sin tarjetas: ¿cambió el HTML del portal?", pagina)
                break
            leidas += len(avisos)
            nuevas = []
            for a in avisos:
                if a["tipo_raw"] != TIPO_UNIDAD or a["url"] in guardados:
                    continue
                if len(guardados) >= max_avisos:
                    break
                fila = {**a, "fuente": fuente, "operacion": operacion, "scrape_date": hoy,
                        "pagina": pagina, "corrida_id": c.id}
                guardados[a["url"]] = fila
                nuevas.append(fila)
            upsert("raw_listings", nuevas, ["url", "scrape_date"])
            con_geo = sum(1 for f in nuevas if f["latitud"] is not None)
            log.info("  Página %d: %d unidades (%d con coordenadas) · total %d/%d",
                     pagina, len(nuevas), con_geo, len(guardados), max_avisos)
            pagina += 1
            _pausa()
        c.leidas, c.escritas = leidas, len(guardados) - len(previos)
    return len(guardados)


# ── Paso 2: detalle ──────────────────────────────────────────

def pendientes(fuente: str, operacion: str) -> list[str]:
    df = read_df("""
        SELECT DISTINCT r.url
        FROM raw_listings r
        LEFT JOIN raw_detalles d USING (url)
        WHERE d.url IS NULL AND r.fuente = :f AND r.operacion = :o
    """, {"f": fuente, "o": operacion})
    return df["url"].tolist()


def scrapear_detalles(nav, fuente: str, operacion: str, hoy: dt.date) -> int:
    urls = pendientes(fuente, operacion)
    a, b = cfg()["scraping"].get("pausa_detalle_seg") or cfg()["scraping"]["pausa_seg"]
    log.info("  Detalles pendientes: %d (≈%d min con pausas de %d–%d s)", len(urls), len(urls) * (a + b) / 2 / 60, a, b)
    if not urls:
        return 0
    with corrida("scraping_detalle", fuente=fuente, operacion=operacion) as c:
        ok = baja = fallas = 0
        for i, url in enumerate(urls, start=1):
            try:
                status, final, html = nav.html(url)
            except Exception as exc:                       # timeout o red: se reintenta en otra corrida
                fallas += 1
                log.warning("  [%d/%d] ⚠ %s: %s", i, len(urls), type(exc).__name__, url[-60:])
                _pausa("pausa_detalle_seg")
                continue
            if status in BLOQUEO:
                c.mensaje = (f"El portal bloqueó en la ficha {i} de {len(urls)}. "
                             "Las que faltan quedan pendientes: vuelve a correr con --solo-detalle en un rato.")
                log.warning("  %s", c.mensaje)
                break
            if status in (404, 410) or "/propiedades/" not in final:
                datos = {"estado": "no_disponible"}
            elif status >= 400:
                fallas += 1
                log.warning("  [%d/%d] ⚠ HTTP %d: %s", i, len(urls), status, url[-60:])
                _pausa("pausa_detalle_seg")
                continue
            else:
                datos = parsear_detalle(html)
            upsert("raw_detalles", [{"url": url, "fuente": fuente, "corrida_id": c.id, **datos}], ["url"])
            if datos["estado"] == "ok":
                ok += 1
            else:
                baja += 1
            if i % 10 == 0 or i == len(urls):
                log.info("  [%d/%d] ok %d · no disponibles %d · fallas %d", i, len(urls), ok, baja, fallas)
            _pausa("pausa_detalle_seg")
        c.leidas, c.escritas = len(urls), ok + baja
        if fallas and not c.mensaje:
            c.mensaje = f"{fallas} fichas fallaron y quedan pendientes para la próxima corrida"
    return ok


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(description="Scraper de avisos de alquiler y venta.")
    p.add_argument("--fuente", default="adondevivir", choices=("adondevivir", "urbania"))
    p.add_argument("--operacion", required=True, choices=("alquiler", "venta"))
    p.add_argument("--max", type=int, help="máximo de avisos del listado (por defecto, config.yaml)")
    p.add_argument("--solo-detalle", action="store_true", help="no recorre el listado; completa detalles pendientes")
    p.add_argument("--sin-detalle", action="store_true", help="solo el listado")
    p.add_argument("--ver", action="store_true", help="muestra el navegador (para depurar)")
    args = p.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(levelname)-7s %(message)s", datefmt="%H:%M:%S")

    conf = cfg()["scraping"]["fuentes"][args.fuente]
    if not conf.get("activo", True):
        raise SystemExit(f"La fuente {args.fuente} está desactivada en config.yaml (activo: false).")
    max_avisos = args.max or conf[args.operacion]["max_avisos"]
    hoy = dt.date.today()

    with Navegador(headless=not args.ver and cfg()["scraping"]["headless"]) as nav:
        if not args.solo_detalle:
            n = scrapear_listado(nav, args.fuente, args.operacion, max_avisos, hoy)
            log.info("Listado listo: %d avisos de %s guardados en raw_listings", n, args.operacion)
        if not args.sin_detalle:
            n = scrapear_detalles(nav, args.fuente, args.operacion, hoy)
            log.info("Detalle listo: %d fichas guardadas en raw_detalles", n)


if __name__ == "__main__":
    main()

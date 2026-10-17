# ubika

Inteligencia inmobiliaria para Lima: scraping de avisos de alquiler y venta, limpieza, ubicación y entorno de cada inmueble, y una app web para explorarlos.

## Estructura

```
config.yaml            parámetros (fuentes, límites, radios). Sin secretos.
.env                   DATABASE_URL y GOOGLE_GEOCODING_API_KEY (copiar de .env.example)
sql/                   esquema de Neon. Se corre a mano en el SQL Editor de Neon.
  00_drop_legacy.sql     borra el esquema anterior (una sola vez)
  01_schema.sql          tablas
  02_seed_distritos.sql  catálogo de distritos y alias
  03_views.sql           vistas que lee la API
  04_delitos.sql         denuncias SIDPOL y ubigeo de distritos
  05_scraping.sql        campos extra de los portales (coordenadas, detalle estructurado)
  06_vistas_entorno.sql  agrega delitos cercanos a la vista de la app
  07_capas.sql           grilla de la ciudad para las capas del mapa
  query.sql              consultas de verificación (solo lectura)
src/ubika/             paquete Python
  config.py              lee config.yaml y .env
  db.py                  conexión, upsert y registro de corridas
  texto.py               normalización de texto
  referencias/sidpol.py  descarga de denuncias policiales (MININTER)
  referencias/puntos.py  carga colegios, salud, malls, transporte e INPE (CSV) y comisarías (MININTER)
  scraping/navent.py     parsers de adondevivir/urbania (misma plataforma)
  scraping/__main__.py   scraper: listado + detalle → raw_listings / raw_detalles
  pipeline/              limpieza + repetidos → geocoding → entorno
scripts/
  check_db.py            verifica conexión y esquema
tests/                 pruebas (pytest)
ubika-app/             app web (React + deck.gl) y API (Express)
legacy/                código anterior, solo como referencia
```

## Puesta en marcha (Windows, Git Bash)

```bash
python -m venv .venv
source .venv/Scripts/activate
pip install -r requirements.txt
pip install -e .                 # hace importable el paquete ubika
playwright install chromium      # para los scrapers (Fase 2)
cp .env.example .env             # y completar los valores
```

En Neon, SQL Editor, correr en orden: `00_drop_legacy.sql` (solo la primera vez), `01_schema.sql`, `02_seed_distritos.sql`, `03_views.sql`, `04_delitos.sql`, `05_scraping.sql`, `06_vistas_entorno.sql`, `07_capas.sql`. Después:

```bash
python scripts/check_db.py
```

Denuncias policiales (tarda unos minutos; se puede volver a correr sin duplicar):

```bash
python -m ubika.referencias.sidpol                     # desde 2025-01-01
python -m ubika.referencias.sidpol --desde 2026-07-01  # actualización
```

Puntos de interés (lee los CSV de `data/processed/`; se puede volver a correr):

```bash
python -m ubika.referencias.puntos
```

Avisos (alquiler y venta por separado; se puede volver a correr el mismo día sin duplicar):

```bash
python -m ubika.scraping --operacion alquiler            # 100 avisos (config.yaml) + su detalle
python -m ubika.scraping --operacion venta
python -m ubika.scraping --operacion venta --solo-detalle  # completa fichas que fallaron
python -m ubika.scraping --operacion alquiler --ver        # muestra el navegador
```

Pipeline descriptivo (después de scrapear; se puede volver a correr sin duplicar):

```bash
python -m ubika.pipeline                    # limpieza → geocoding → entorno → capas
python -m ubika.pipeline --sin-google       # sin consultar Google
python -m ubika.pipeline --etapas entorno   # una sola etapa
```

## Modelo de datos

| Capa | Tabla | Qué guarda |
|---|---|---|
| Bruta | `raw_listings` | Cada aviso visto en el listado, por fecha de scraping. Nunca se borra: es el historial. |
| Bruta | `raw_detalles` | Detalle de cada aviso (antigüedad, inmobiliaria). Solo se visita una URL nueva. |
| Limpia | `propiedades` | Un inmueble único, ya sin repetidos, con precio, área y coordenadas. |
| Limpia | `avisos` | Qué URLs (de uno o varios portales) son el mismo inmueble. |
| Referencia | `distritos`, `distrito_alias` | Catálogo de distritos y variantes de nombre. |
| Referencia | `puntos_interes`, `inpe_domicilios` | Colegios, salud, comisarías, transporte, malls; domicilios INPE. |
| Referencia | `delitos_puntos` | Denuncias SIDPOL con ubicación propia (Lima y Callao). |
| Referencia | `delitos_distrito_mes` | Conteo de todas las denuncias por distrito, mes y tipo, y cuántas tienen ubicación. |
| Derivada | `geocode_cache` | Cada dirección consultada a Google, una sola vez. |
| Derivada | `entorno` | Conteos dentro del radio y distancia al más cercano, por inmueble. |
| Derivada | `capas_grilla` | Grilla de la ciudad (~350 m) con índices de seguridad, transporte y servicios para el mapa. |
| Control | `corridas` | Cada ejecución de scraping o pipeline, con su estado y conteos. |

## Fuentes

- **Denuncias:** SIDPOL, capa `SIDPOL_DELITOS_TOTAL` del [Mapa del Delito de MININTER](https://mininter-dgis.maps.arcgis.com/apps/webappviewer/index.html?id=ffc03c3586b142b988c931312d7da17b). Dos de cada tres denuncias de Lima (66%) no tienen coordenada propia y MININTER las pone en un punto fijo por distrito; esas solo entran en los conteos por distrito. Los puntos se ponderan por distrito (`v_delitos_distrito_12m.peso`).
- **INPE:** domicilio declarado de la población que ingresó a un penal en 2024. No indica dónde ocurrió un delito.

## Fases

- [x] 0 · Saneamiento del repo
- [x] 1 · Esquema SQL
- [x] 2 · Scrapers de alquiler y venta (adondevivir), 100 + 100
- [x] 3 · Pipeline descriptivo: limpieza, repetidos, geocoding, entorno
- [x] 4 · API y app descriptiva con la nueva marca (ver `ubika-app/README.md`)
- [ ] 5 · Scraping completo semanal (+ urbania)
- [ ] 6 · Modelos de valor por operación y Evaluador

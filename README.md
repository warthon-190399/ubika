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
  08_poblacion.sql       población por distrito (censo 2017) y tasa de denuncias
  09_calidad_vida.sql    áreas verdes, comercio de barrio y ruido estimado
  10_defunciones.sql     defunciones SINADEF y tasa de mortalidad por 100 mil habitantes
  11_correccion_ubicacion.sql  pin original del portal y motivo de las correcciones de ubicación
  query.sql              consultas de verificación (solo lectura)
src/ubika/             paquete Python
  config.py              lee config.yaml y .env
  db.py                  conexión, upsert y registro de corridas
  texto.py               normalización de texto
  referencias/sidpol.py  descarga de denuncias policiales (MININTER)
  referencias/puntos.py  carga colegios, salud, malls, transporte e INPE (CSV) y comisarías (MININTER)
  referencias/osm.py     parques, comercio de barrio y vías ruidosas (OpenStreetMap)
  referencias/sinadef.py defunciones por distrito de domicilio (MINSA)
  scraping/navent.py     parsers de adondevivir/urbania (misma plataforma)
  scraping/__main__.py   scraper: listado + detalle → raw_listings / raw_detalles
  pipeline/              limpieza + repetidos → geocoding → entorno
src/modeling/valor.py  modelo de valor: entrena y compara métodos con los datos de Neon (Fase 6)
scripts/
  check_db.py            verifica conexión y esquema
data/referencias/      cifras publicadas para contrastar (se versionan; el resto de data/ no)
  homicidios_referencia.csv  homicidios por distrito, MP 2012 e INEI 2017
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

En Neon, SQL Editor, correr en orden: `00_drop_legacy.sql` (solo la primera vez), `01_schema.sql`, `02_seed_distritos.sql`, `03_views.sql`, `04_delitos.sql`, `05_scraping.sql`, `06_vistas_entorno.sql`, `07_capas.sql`, `08_poblacion.sql`, `09_calidad_vida.sql`, `10_defunciones.sql`, `11_correccion_ubicacion.sql`. Después:

```bash
python scripts/check_db.py
```

Denuncias policiales (tarda unos minutos; se puede volver a correr sin duplicar):

```bash
python -m ubika.referencias.sidpol                     # desde 2025-01-01
python -m ubika.referencias.sidpol --desde 2026-07-01  # actualización
```

Defunciones SINADEF (baja un CSV de ~380 MB a `data/raw/sinadef/` la primera vez; recarga la tabla completa, se puede volver a correr sin duplicar):

```bash
python -m ubika.referencias.sinadef                # descarga si no está y carga
python -m ubika.referencias.sinadef --descargar    # vuelve a bajar el CSV (cuando MINSA lo actualice)
```

Tasas por distrito: `SELECT * FROM v_mortalidad_distrito_reciente ORDER BY tasa_homicidios_100k DESC;` (por año: `v_mortalidad_distrito`).

Puntos de interés (lee los CSV de `data/processed/`; se puede volver a correr):

```bash
python -m ubika.referencias.puntos
```

Avisos (alquiler y venta por separado; se puede volver a correr el mismo día sin duplicar):

```bash
python -m ubika.scraping --operacion alquiler            # 500 avisos repartidos por distrito (config.yaml) + su detalle
python -m ubika.scraping --operacion venta --sin-detalle   # solo el listado (el detalle tarda ~30 s por ficha)
python -m ubika.scraping --operacion venta --solo-detalle  # completa fichas que fallaron
python -m ubika.scraping --operacion alquiler --ver        # muestra el navegador
```

Pipeline descriptivo (después de scrapear; se puede volver a correr sin duplicar):

```bash
python -m ubika.pipeline                    # limpieza → geocoding → entorno → capas
python -m ubika.pipeline --sin-google       # sin consultar Google
python -m ubika.pipeline --etapas entorno   # una sola etapa
```

Modelo de valor (Fase 6; solo lee de Neon y guarda en `models/valor/`, que no se versiona):

```bash
python -m modeling.valor                    # alquiler y venta
python -m modeling.valor --operacion venta
python -m modeling.valor --sin-registro     # prueba: no anota la corrida en Neon
```

Compara con validación cruzada (5 partes × 3 repeticiones) la mediana del distrito, los comparables de la app, Ridge, Random Forest y gradient boosting. Guarda `{operacion}_metricas.json` (MAPE, error mediano, % a menos de 20 %, R² y RMSE de cada método) y el mejor modelo en `{operacion}_modelo.joblib`. Con ~100 inmuebles por operación (octubre 2026) los resultados son inestables: hay que acumular avisos antes de usarlo en la app.

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
| Referencia | `defunciones_distrito_mes` | Defunciones SINADEF por distrito de domicilio, mes y tipo de muerte (natural, homicidio, tránsito, suicidio…). |
| Derivada | `geocode_cache` | Cada dirección consultada a Google, una sola vez. |
| Derivada | `entorno` | Conteos dentro del radio y distancia al más cercano, por inmueble. |
| Derivada | `capas_grilla` | Grilla de la ciudad (~350 m) con índices de seguridad, transporte y servicios para el mapa. |
| Control | `corridas` | Cada ejecución de scraping o pipeline, con su estado y conteos. |

## Fuentes

- **Avisos:** adondevivir.com (listados por distrito, `config.yaml`). Lo scrapeado se guarda intacto en `raw_listings`/`raw_detalles`; la limpieza corrige dos inconsistencias de ubicación y deja cada caso marcado en `propiedades.correccion_ubicacion`:
  - `distrito_por_poligono`: el portal solo dice «Lima, Lima» (la provincia), que se leería como Cercado. El distrito sale del polígono IGN donde cae el pin.
  - `pin_lejos_del_distrito`: el pin está a más de 2 km (`limpieza.max_metros_fuera_distrito`) del distrito que declara el anunciante, casi siempre porque el portal ubicó una calle homónima de otro distrito. El pin original se conserva en `lat_portal`/`lon_portal` y el aviso se vuelve a ubicar con Google (dirección + distrito declarado); si el resultado tampoco cae en el distrito, queda sin coordenadas (no sale en el mapa, pero cuenta en las cifras del distrito). Octubre 2026: 16 de 1131 inmuebles, 9 de ellos sin coordenadas. Los pines a menos de 2 km del distrito declarado (casos de borde) no se tocan.

- **Denuncias:** SIDPOL, capa `SIDPOL_DELITOS_TOTAL` del [Mapa del Delito de MININTER](https://mininter-dgis.maps.arcgis.com/apps/webappviewer/index.html?id=ffc03c3586b142b988c931312d7da17b). Dos de cada tres denuncias de Lima (66%) no tienen coordenada propia y MININTER las pone en un punto fijo por distrito; esas solo entran en los conteos por distrito. Los puntos se ponderan por distrito (`v_delitos_distrito_12m.peso`).
- **Defunciones:** [SINADEF de MINSA](https://www.datosabiertos.gob.pe/dataset/informaci%C3%B3n-de-fallecidos-del-sistema-inform%C3%A1tico-nacional-de-defunciones-sinadef-ministerio), un certificado por fila. El distrito es el de **domicilio** del fallecido (el archivo no trae dónde murió) y el tipo sale de la columna `MUERTE VIOLENTA`. El archivo publicado llega solo hasta 2024-05; 2020–2021 están infladas por COVID y 2017–2019 tienen menos cobertura. Los homicidios de SINADEF son menos que los de la PNP: sirven para comparar distritos, no como cifra oficial. Población: censo 2017.
- **Homicidios de referencia** (`data/referencias/homicidios_referencia.csv`, para contrastar con SINADEF, no se carga en Neon). A diferencia de SINADEF, cuentan el distrito **donde ocurrió** el hecho:
  - `MP-OC` 2012: Observatorio de Criminalidad del Ministerio Público, *Muertes violentas por delitos dolosos según provincias 2012* (2014). Los 49 distritos de Lima y Callao, con la población INEI 2012; la tasa está calculada. Cifras de 0 a 7 víctimas: en distritos chicos la tasa es casi azar.
  - `INEI-CEIC` 2017: INEI, *Homicidios en el Perú, contándolos uno a uno 2011-2017* (2018), gráficos 1.8 y 2.5. Solo los distritos que aparecen en esos gráficos (los 15 con más víctimas y los 15 de 100 mil habitantes o más con la tasa más alta); las celdas vacías son datos que el informe no da (ver la columna `nota`).
- **INPE:** domicilio declarado de la población que ingresó a un penal en 2024. No indica dónde ocurrió un delito.

## Fases

- [x] 0 · Saneamiento del repo
- [x] 1 · Esquema SQL
- [x] 2 · Scrapers de alquiler y venta (adondevivir), 100 + 100
- [x] 3 · Pipeline descriptivo: limpieza, repetidos, geocoding, entorno
- [x] 4 · API y app descriptiva con la nueva marca (ver `ubika-app/README.md`)
- [ ] 5 · Scraping completo semanal (+ urbania)
- [ ] 6 · Modelos de valor por operación y Evaluador

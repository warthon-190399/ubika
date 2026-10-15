-- ============================================================
-- 01_schema.sql · esquema de ubika v0.2
-- Correr en Neon después de 00_drop_legacy.sql. Se puede volver a correr:
-- todo usa IF NOT EXISTS / OR REPLACE.
--
-- Flujo de datos:
--   scraper ─▶ raw_listings  (una fila por aviso por semana; nunca se borra)
--           └▶ raw_detalles  (una fila por URL; solo se visita una vez)
--   limpieza + dedup ─▶ propiedades (una fila por inmueble único)
--                     └▶ avisos     (qué URLs apuntan a cada inmueble)
--   geocoding ─▶ geocode_cache ─▶ propiedades.latitud/longitud
--   entorno   ─▶ entorno (conteos a R m y distancia al más cercano)
-- ============================================================
BEGIN;

-- ── Utilidad: actualizado_at automático ─────────────────────
CREATE OR REPLACE FUNCTION set_actualizado_at() RETURNS TRIGGER AS $$
BEGIN
    NEW.actualizado_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;


-- ── Catálogo de distritos ───────────────────────────────────
CREATE TABLE IF NOT EXISTS distritos (
    distrito     TEXT PRIMARY KEY,                -- slug: 'miraflores', 'sjl', 'lima cercado'
    nombre       TEXT NOT NULL,                   -- 'San Juan de Lurigancho'
    provincia    TEXT NOT NULL DEFAULT 'lima' CHECK (provincia IN ('lima', 'callao')),
    zona_apeim   SMALLINT CHECK (zona_apeim BETWEEN 1 AND 10),
    nse_aprox    CHAR(1)  CHECK (nse_aprox IN ('A', 'B', 'C', 'D', 'E'))
);

-- Variantes de texto que traen los portales → distrito canónico.
-- alias va normalizado: minúsculas, sin tildes, espacios simples.
CREATE TABLE IF NOT EXISTS distrito_alias (
    alias     TEXT PRIMARY KEY,
    distrito  TEXT NOT NULL REFERENCES distritos(distrito) ON UPDATE CASCADE ON DELETE CASCADE
);


-- ── Registro de corridas (scraping y pipeline) ──────────────
CREATE TABLE IF NOT EXISTS corridas (
    corrida_id      BIGSERIAL PRIMARY KEY,
    etapa           TEXT NOT NULL,                -- scraping_listado, scraping_detalle, limpieza, geocoding, entorno
    parametros      JSONB NOT NULL DEFAULT '{}',
    iniciada_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    terminada_at    TIMESTAMPTZ,
    estado          TEXT NOT NULL DEFAULT 'corriendo' CHECK (estado IN ('corriendo', 'ok', 'error')),
    filas_leidas    INTEGER,
    filas_escritas  INTEGER,
    mensaje         TEXT
);
CREATE INDEX IF NOT EXISTS idx_corridas_etapa ON corridas (etapa, iniciada_at DESC);


-- ── Capa bruta ──────────────────────────────────────────────
-- Una fila por aviso visto en el listado, por fecha de scraping.
-- Correr dos veces el mismo día no duplica (UNIQUE url+fecha).
CREATE TABLE IF NOT EXISTS raw_listings (
    raw_id             BIGSERIAL PRIMARY KEY,
    fuente             TEXT NOT NULL CHECK (fuente IN ('adondevivir', 'urbania')),
    operacion          TEXT NOT NULL CHECK (operacion IN ('alquiler', 'venta')),
    url                TEXT NOT NULL,
    aviso_id           TEXT,                      -- id del portal, sacado de la URL
    scrape_date        DATE NOT NULL,
    pagina             SMALLINT,
    posicion           SMALLINT,
    tipo_raw           TEXT,
    precio_raw         TEXT,                      -- tal cual: 'S/ 2,500 · USD 676'
    mantenimiento_raw  TEXT,
    direccion_raw      TEXT,
    ubicacion_raw      TEXT,                      -- 'Santa Beatriz, Lima Cercado'
    area_raw           TEXT,
    dorm_raw           TEXT,
    banos_raw          TEXT,
    estac_raw          TEXT,
    corrida_id         BIGINT REFERENCES corridas(corrida_id) ON DELETE SET NULL,
    scraped_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (url, scrape_date)
);
CREATE INDEX IF NOT EXISTS idx_raw_listings_lote ON raw_listings (fuente, operacion, scrape_date);
CREATE INDEX IF NOT EXISTS idx_raw_listings_url  ON raw_listings (url);

-- Detalle de cada aviso. Se visita solo si la URL no está aquí.
-- Los timeouts no se guardan, así se reintentan en la siguiente corrida.
CREATE TABLE IF NOT EXISTS raw_detalles (
    url                  TEXT PRIMARY KEY,
    fuente               TEXT NOT NULL CHECK (fuente IN ('adondevivir', 'urbania')),
    estado               TEXT NOT NULL CHECK (estado IN ('ok', 'no_disponible')),
    antiguedad_raw       TEXT,
    publicado_raw        TEXT,                    -- 'Publicado hace 3 días'
    fecha_publicacion    DATE,                    -- calculada el día del scraping
    visualizaciones_raw  TEXT,
    inmobiliaria_raw     TEXT,
    descripcion          TEXT,
    caracteristicas      JSONB,                   -- lista de atributos tal cual los muestra el portal
    corrida_id           BIGINT REFERENCES corridas(corrida_id) ON DELETE SET NULL,
    scraped_at           TIMESTAMPTZ NOT NULL DEFAULT now()
);


-- ── Capa limpia ─────────────────────────────────────────────
-- Una fila por inmueble único (después de quitar repetidos).
CREATE TABLE IF NOT EXISTS propiedades (
    prop_id             UUID PRIMARY KEY,
    operacion           TEXT NOT NULL CHECK (operacion IN ('alquiler', 'venta')),
    tipo_inmueble       TEXT,                     -- departamento, casa, ... (NULL si el portal no lo dice)

    precio_pen          NUMERIC(14, 2) CHECK (precio_pen > 0),   -- alquiler: mensual
    precio_usd          NUMERIC(14, 2) CHECK (precio_usd > 0),
    mantenimiento_pen   NUMERIC(10, 2) CHECK (mantenimiento_pen >= 0),
    area_m2             NUMERIC(10, 2) CHECK (area_m2 > 0),
    precio_m2_pen       NUMERIC(12, 2) GENERATED ALWAYS AS (precio_pen / NULLIF(area_m2, 0)) STORED,
    num_dorm            SMALLINT CHECK (num_dorm >= 0),
    num_banios          SMALLINT CHECK (num_banios >= 0),
    num_estac           SMALLINT CHECK (num_estac >= 0),
    antiguedad_anios    SMALLINT CHECK (antiguedad_anios >= 0),

    direccion           TEXT,                     -- como la publicó el portal, limpia
    direccion_norm      TEXT,                     -- minúsculas, sin tildes: llave de geocoding y dedup
    distrito            TEXT REFERENCES distritos(distrito) ON UPDATE CASCADE,
    latitud             DOUBLE PRECISION CHECK (latitud  BETWEEN -90  AND 90),
    longitud            DOUBLE PRECISION CHECK (longitud BETWEEN -180 AND 180),
    geo_precision       TEXT,                     -- ROOFTOP, RANGE_INTERPOLATED, GEOMETRIC_CENTER, APPROXIMATE

    inmobiliaria        TEXT,
    fecha_publicacion   DATE,
    primera_vez         DATE NOT NULL,            -- primera semana en que apareció
    ultima_vez          DATE NOT NULL,            -- última semana en que apareció
    activo              BOOLEAN NOT NULL DEFAULT true,   -- apareció en el último scraping de su operación

    creado_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
    actualizado_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_prop_operacion ON propiedades (operacion, activo);
CREATE INDEX IF NOT EXISTS idx_prop_distrito  ON propiedades (distrito);
CREATE INDEX IF NOT EXISTS idx_prop_sin_geo   ON propiedades (prop_id) WHERE latitud IS NULL;

CREATE OR REPLACE TRIGGER trg_propiedades_actualizado
    BEFORE UPDATE ON propiedades
    FOR EACH ROW EXECUTE FUNCTION set_actualizado_at();

-- Qué avisos (URLs, de uno o varios portales) corresponden a cada inmueble.
CREATE TABLE IF NOT EXISTS avisos (
    url          TEXT PRIMARY KEY,
    fuente       TEXT NOT NULL CHECK (fuente IN ('adondevivir', 'urbania')),
    prop_id      UUID NOT NULL REFERENCES propiedades(prop_id) ON DELETE CASCADE,
    primera_vez  DATE NOT NULL,
    ultima_vez   DATE NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_avisos_prop ON avisos (prop_id);


-- ── Geocodificación ─────────────────────────────────────────
-- Cada texto se consulta a Google una sola vez.
CREATE TABLE IF NOT EXISTS geocode_cache (
    consulta          TEXT PRIMARY KEY,           -- texto exacto enviado a Google
    estado            TEXT NOT NULL CHECK (estado IN ('ok', 'sin_resultado', 'fuera_de_lima', 'error')),
    latitud           DOUBLE PRECISION,
    longitud          DOUBLE PRECISION,
    location_type     TEXT,
    direccion_google  TEXT,
    consultado_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);


-- ── Puntos de interés (referencias para el entorno) ─────────
CREATE TABLE IF NOT EXISTS puntos_interes (
    poi_id      BIGSERIAL PRIMARY KEY,
    categoria   TEXT NOT NULL CHECK (categoria IN
                  ('colegio', 'salud', 'comisaria', 'metro', 'metropolitano', 'tren', 'mall', 'parque')),
    nombre      TEXT,
    distrito    TEXT,                             -- texto de la fuente; no se fuerza al catálogo
    latitud     DOUBLE PRECISION NOT NULL,
    longitud    DOUBLE PRECISION NOT NULL,
    fuente      TEXT NOT NULL,                    -- minedu, susalud, mininter, osm, wikipedia
    atributos   JSONB NOT NULL DEFAULT '{}',
    cargado_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_poi_categoria ON puntos_interes (categoria);

-- INPE: domicilio declarado de la población penitenciaria.
-- OJO: no es dónde ocurrió el delito. Se usa como indicador indirecto de inseguridad.
CREATE TABLE IF NOT EXISTS inpe_domicilios (
    inpe_id          BIGSERIAL PRIMARY KEY,
    periodo          TEXT,
    delito_generico  TEXT,
    delito_especifico TEXT,
    distrito         TEXT,
    latitud          DOUBLE PRECISION NOT NULL,
    longitud         DOUBLE PRECISION NOT NULL,
    cargado_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);


-- ── Entorno de cada inmueble ────────────────────────────────
CREATE TABLE IF NOT EXISTS entorno (
    prop_id            UUID PRIMARY KEY REFERENCES propiedades(prop_id) ON DELETE CASCADE,
    radio_m            SMALLINT NOT NULL,
    -- cuántos hay dentro del radio
    n_colegios         INTEGER NOT NULL DEFAULT 0,
    n_salud            INTEGER NOT NULL DEFAULT 0,
    n_comisarias       INTEGER NOT NULL DEFAULT 0,
    n_transporte       INTEGER NOT NULL DEFAULT 0,   -- metro + metropolitano + tren
    n_malls            INTEGER NOT NULL DEFAULT 0,
    n_parques          INTEGER NOT NULL DEFAULT 0,
    n_inpe             INTEGER NOT NULL DEFAULT 0,
    -- distancia en línea recta al más cercano (metros)
    dist_colegio_m     INTEGER,
    dist_salud_m       INTEGER,
    dist_comisaria_m   INTEGER,
    dist_transporte_m  INTEGER,
    dist_mall_m        INTEGER,
    dist_parque_m      INTEGER,
    calculado_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);

COMMIT;

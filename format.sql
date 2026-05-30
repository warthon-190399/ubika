-- ============================================================
-- 001_create_urbania_tables.sql
-- Ejecutar una sola vez en el SQL Editor de Supabase
-- ============================================================

-- Tabla principal: un registro por propiedad scrapeada
CREATE TABLE IF NOT EXISTS urbania_listings (
    prop_id         UUID PRIMARY KEY,           -- generado en el scraper (uuid5 del url)
    url             TEXT UNIQUE NOT NULL,
    fuente          TEXT NOT NULL DEFAULT 'urbania',
    scrape_date     DATE NOT NULL,

    -- estado del segundo scraper
    detalle_status  TEXT NOT NULL DEFAULT 'pending'
                    CHECK (detalle_status IN ('pending', 'ok', 'gone', 'error')),

    -- campos del listing
    precio          TEXT,
    mantenimiento   TEXT,
    m2_total        TEXT,
    dorms           TEXT,
    banos           TEXT,
    estac           TEXT,
    direccion       TEXT,
    distrito        TEXT,

    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Tabla secundaria: solo se inserta cuando detalle_status = 'ok'
CREATE TABLE IF NOT EXISTS urbania_detalles (
    prop_id             UUID PRIMARY KEY
                        REFERENCES urbania_listings(prop_id) ON DELETE CASCADE,
    scrape_date         DATE NOT NULL,

    antiguedad          TEXT,
    descripcion         TEXT,
    publicado_por       TEXT,
    codigo_urbania      TEXT,
    fecha_publicacion   TEXT,

    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Vista limpia: solo propiedades con detalles completos
CREATE OR REPLACE VIEW urbania_clean AS
SELECT
    l.prop_id,
    l.url,
    l.fuente,
    l.scrape_date       AS listing_date,
    l.precio,
    l.mantenimiento,
    l.m2_total,
    l.dorms,
    l.banos,
    l.estac,
    l.direccion,
    l.distrito,
    d.scrape_date       AS detalle_date,
    d.antiguedad,
    d.descripcion,
    d.publicado_por,
    d.codigo_urbania,
    d.fecha_publicacion
FROM urbania_listings l
JOIN urbania_detalles  d USING (prop_id)
WHERE l.detalle_status = 'ok';

-- Trigger para actualizar updated_at automáticamente
CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE TRIGGER trg_listings_updated_at
    BEFORE UPDATE ON urbania_listings
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE OR REPLACE TRIGGER trg_detalles_updated_at
    BEFORE UPDATE ON urbania_detalles
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- Índices útiles para queries frecuentes
CREATE INDEX IF NOT EXISTS idx_listings_detalle_status ON urbania_listings(detalle_status);
CREATE INDEX IF NOT EXISTS idx_listings_scrape_date    ON urbania_listings(scrape_date);
CREATE INDEX IF NOT EXISTS idx_listings_distrito       ON urbania_listings(distrito);
-- ============================================================
-- 002_create_adondevivir_tables.sql
-- Misma estructura que urbania — columnas idénticas
-- ============================================================

CREATE TABLE IF NOT EXISTS adondevivir_listings (
    prop_id         UUID PRIMARY KEY,
    url             TEXT UNIQUE NOT NULL,
    fuente          TEXT NOT NULL DEFAULT 'adondevivir',
    scrape_date     DATE NOT NULL,

    detalle_status  TEXT NOT NULL DEFAULT 'pending'
                    CHECK (detalle_status IN ('pending', 'ok', 'gone', 'error')),

    precio          TEXT,
    mantenimiento   TEXT,
    m2_total        TEXT,
    dorms           TEXT,
    banos           TEXT,
    estac           TEXT,
    direccion       TEXT,
    distrito        TEXT,

    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS adondevivir_detalles (
    prop_id             UUID PRIMARY KEY
                        REFERENCES adondevivir_listings(prop_id) ON DELETE CASCADE,
    scrape_date         DATE NOT NULL,

    antiguedad          TEXT,
    descripcion         TEXT,
    publicado_por       TEXT,
    fecha_publicacion   TEXT,

    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE OR REPLACE VIEW adondevivir_clean AS
SELECT
    l.prop_id,
    l.url,
    l.fuente,
    l.scrape_date       AS listing_date,
    l.precio,
    l.mantenimiento,
    l.m2_total,
    l.dorms,
    l.banos,
    l.estac,
    l.direccion,
    l.distrito,
    d.scrape_date       AS detalle_date,
    d.antiguedad,
    d.descripcion,
    d.publicado_por,
    d.fecha_publicacion
FROM adondevivir_listings l
JOIN adondevivir_detalles d USING (prop_id)
WHERE l.detalle_status = 'ok';

-- set_updated_at() ya existe desde la migration de urbania
CREATE OR REPLACE TRIGGER trg_adv_listings_updated_at
    BEFORE UPDATE ON adondevivir_listings
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE OR REPLACE TRIGGER trg_adv_detalles_updated_at
    BEFORE UPDATE ON adondevivir_detalles
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE INDEX IF NOT EXISTS idx_adv_listings_detalle_status ON adondevivir_listings(detalle_status);
CREATE INDEX IF NOT EXISTS idx_adv_listings_scrape_date    ON adondevivir_listings(scrape_date);
CREATE INDEX IF NOT EXISTS idx_adv_listings_distrito       ON adondevivir_listings(distrito);

DROP VIEW  IF EXISTS adondevivir_clean    CASCADE;
DROP TABLE IF EXISTS adondevivir_detalles CASCADE;
DROP TABLE IF EXISTS adondevivir_listings CASCADE;

-- ============================================================
-- 003_create_unified_view.sql
-- Tablon unificado: urbania + adondevivir, listings + detalles
-- ============================================================
 
CREATE MATERIALIZED VIEW IF NOT EXISTS propiedades_union AS
 
    SELECT
        l.prop_id,
        l.fuente,
        l.scrape_date       AS listing_date,
        l.url,
        l.precio,
        l.mantenimiento,
        l.m2_total,
        l.dorms,
        l.banos,
        l.estac,
        l.direccion,
        l.distrito,
        d.scrape_date       AS detalle_date,
        d.antiguedad,
        d.descripcion,
        d.publicado_por,
        d.fecha_publicacion
    FROM urbania_listings l
    JOIN urbania_detalles d USING (prop_id)
    WHERE l.detalle_status = 'ok'
 
UNION ALL
 
    SELECT
        l.prop_id,
        l.fuente,
        l.scrape_date       AS listing_date,
        l.url,
        l.precio,
        l.mantenimiento,
        l.m2_total,
        l.dorms,
        l.banos,
        l.estac,
        l.direccion,
        l.distrito,
        d.scrape_date       AS detalle_date,
        d.antiguedad,
        d.descripcion,
        d.publicado_por,
        d.fecha_publicacion
    FROM adondevivir_listings l
    JOIN adondevivir_detalles d USING (prop_id)
    WHERE l.detalle_status = 'ok';
 
-- Índices sobre la vista materializada para queries rápidas
CREATE INDEX IF NOT EXISTS idx_pc_fuente    ON propiedades_union(fuente);
CREATE INDEX IF NOT EXISTS idx_pc_distrito  ON propiedades_union(distrito);
CREATE INDEX IF NOT EXISTS idx_pc_listing_date ON propiedades_union(listing_date);
-- ============================================================
-- 004_create_propiedades_procesadas.sql
-- Tabla destino del script de procesamiento
-- ============================================================
 
CREATE TABLE IF NOT EXISTS propiedades_procesadas (
    prop_id             UUID PRIMARY KEY,
    fuente              TEXT,
    listing_date        DATE,
    url                 TEXT,
 
    -- Precios normalizados
    precio_pen          INTEGER,
    precio_usd          INTEGER,
    mantenimiento_soles INTEGER,
 
    -- Ubicación limpia
    direccion_completa  TEXT,
    distrito            TEXT,       -- normalizado (ej: "surco", "sjl")
    nivel_socioeconomico TEXT,      -- A / B / C / D
 
    -- Características numéricas
    area_m2             FLOAT,
    num_dorm            FLOAT,
    num_banios          FLOAT,
    num_estac           FLOAT,
    antiguedad          FLOAT,
 
    -- Detalles
    publicado_por       TEXT,
    fecha_publicacion   TEXT,
 
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
 
CREATE INDEX IF NOT EXISTS idx_pp_fuente   ON propiedades_procesadas(fuente);
CREATE INDEX IF NOT EXISTS idx_pp_distrito ON propiedades_procesadas(distrito);
CREATE INDEX IF NOT EXISTS idx_pp_nse      ON propiedades_procesadas(nivel_socioeconomico);
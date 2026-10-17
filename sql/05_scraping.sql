-- ============================================================
-- 05_scraping.sql · campos extra que entregan los portales Navent
-- (adondevivir / urbania). Correr después de 01–04. Se puede volver a correr.
-- ============================================================
BEGIN;

-- Listado: el portal publica coordenadas en el JSON-LD de cada tarjeta
ALTER TABLE raw_listings
    ADD COLUMN IF NOT EXISTS latitud   DOUBLE PRECISION,
    ADD COLUMN IF NOT EXISTS longitud  DOUBLE PRECISION;

-- Detalle: datos estructurados del aviso (bloque avisoInfo de la ficha)
ALTER TABLE raw_detalles
    ADD COLUMN IF NOT EXISTS estado_aviso          TEXT,          -- ONLINE, ...
    ADD COLUMN IF NOT EXISTS tipo_inmueble_raw     TEXT,          -- Apartamento, Casa, ...
    ADD COLUMN IF NOT EXISTS precio_pen            NUMERIC(14, 2),
    ADD COLUMN IF NOT EXISTS precio_usd            NUMERIC(14, 2),
    ADD COLUMN IF NOT EXISTS mantenimiento_raw     TEXT,
    ADD COLUMN IF NOT EXISTS area_total_raw        TEXT,
    ADD COLUMN IF NOT EXISTS area_cubierta_raw     TEXT,
    ADD COLUMN IF NOT EXISTS dorm_raw              TEXT,
    ADD COLUMN IF NOT EXISTS banos_raw             TEXT,
    ADD COLUMN IF NOT EXISTS estac_raw             TEXT,
    ADD COLUMN IF NOT EXISTS publicado_at          TIMESTAMPTZ,   -- fecha exacta de publicación
    ADD COLUMN IF NOT EXISTS tipo_publicador       SMALLINT,      -- código del portal (inmobiliaria, dueño, ...)
    ADD COLUMN IF NOT EXISTS visibilidad_direccion TEXT,          -- EXACT / aproximada
    ADD COLUMN IF NOT EXISTS ubicacion_portal      JSONB;         -- jerarquía de ubicación del portal

COMMIT;

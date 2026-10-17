-- ============================================================
-- 09_calidad_vida.sql · áreas verdes, vida de barrio y ruido estimado
-- Correr después de 01–08. Se puede volver a correr.
-- Lo llena: python -m ubika.referencias.osm   (datos de OpenStreetMap)
-- Luego:    python -m ubika.pipeline --etapas capas
-- ============================================================
BEGIN;

-- Nuevas categorías de puntos de interés (comercio de todos los días)
ALTER TABLE puntos_interes DROP CONSTRAINT IF EXISTS puntos_interes_categoria_check;
ALTER TABLE puntos_interes ADD CONSTRAINT puntos_interes_categoria_check CHECK (categoria IN (
    'colegio', 'salud', 'comisaria', 'metro', 'metropolitano', 'tren', 'mall', 'parque',
    'supermercado', 'mercado', 'farmacia', 'restaurante', 'gimnasio', 'banco'));

-- Fuentes de ruido: puntos cada ~40 m a lo largo de vías grandes y de la pista del aeropuerto
CREATE TABLE IF NOT EXISTS ruido_fuentes (
    id          BIGSERIAL PRIMARY KEY,
    tipo        TEXT NOT NULL CHECK (tipo IN ('autopista', 'principal', 'secundaria', 'aeropuerto')),
    nombre      TEXT,
    latitud     DOUBLE PRECISION NOT NULL,
    longitud    DOUBLE PRECISION NOT NULL,
    fuente      TEXT NOT NULL DEFAULT 'osm',
    cargado_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_ruido_tipo ON ruido_fuentes (tipo);

-- Nuevas capas de la grilla de la ciudad
ALTER TABLE capas_grilla DROP CONSTRAINT IF EXISTS capas_grilla_capa_check;
ALTER TABLE capas_grilla ADD CONSTRAINT capas_grilla_capa_check CHECK (capa IN (
    'seguridad', 'transporte', 'servicios',
    'verde',     -- m² de parque con centro a menos de 500 m
    'barrio',    -- comercio de todos los días a 500 m: mercados, súper, farmacias, restaurantes, gimnasios, bancos
    'ruido'));   -- nivel de ruido de tráfico estimado, en dB (no es una medición)

COMMIT;

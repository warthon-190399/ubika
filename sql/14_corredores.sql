-- ============================================================
-- 14_corredores.sql · paraderos de los Corredores Complementarios (Amarillo, Rojo, Azul, Morado)
-- Correr después de 01–13. Se puede volver a correr.
-- Lo llena: python -m ubika.referencias.osm --solo corredores
-- Luego:    python -m ubika.pipeline --etapas entorno,capas,calidad
--
-- Los paraderos cuentan para el componente transporte del score de calidad de vida con una
-- penalidad (calidad_vida.factor_corredor en config.yaml): un corredor es más lento y menos
-- frecuente que el Metro o el Metropolitano. Ver docs/metodologia_calidad_vida.md.
-- ============================================================
BEGIN;

-- Nueva categoría de punto de interés
ALTER TABLE puntos_interes DROP CONSTRAINT IF EXISTS puntos_interes_categoria_check;
ALTER TABLE puntos_interes ADD CONSTRAINT puntos_interes_categoria_check CHECK (categoria IN (
    'colegio', 'salud', 'comisaria', 'metro', 'metropolitano', 'tren', 'mall', 'parque',
    'supermercado', 'mercado', 'farmacia', 'restaurante', 'gimnasio', 'banco',
    'corredor'));   -- paradero de un Corredor Complementario (OSM, red SIT de la ATU)

-- Nueva capa de la grilla: metros al paradero de corredor más cercano.
-- Se conservan 'violencia' y 'calle', que ya acepta la restricción en Neon.
ALTER TABLE capas_grilla DROP CONSTRAINT IF EXISTS capas_grilla_capa_check;
ALTER TABLE capas_grilla ADD CONSTRAINT capas_grilla_capa_check CHECK (capa IN (
    'seguridad', 'violencia', 'calle', 'transporte', 'servicios', 'verde', 'barrio', 'ruido',
    'corredor'));

-- Entorno de cada inmueble
ALTER TABLE entorno ADD COLUMN IF NOT EXISTS n_corredores    INTEGER NOT NULL DEFAULT 0;   -- paraderos de corredor a 500 m
ALTER TABLE entorno ADD COLUMN IF NOT EXISTS dist_corredor_m INTEGER;                      -- metros al más cercano

-- Score de calidad de vida: distancia real al paradero de corredor más cercano (para auditar)
ALTER TABLE calidad_vida_celda    ADD COLUMN IF NOT EXISTS val_corredor_m REAL;
ALTER TABLE calidad_vida_inmueble ADD COLUMN IF NOT EXISTS val_corredor_m REAL;

COMMIT;

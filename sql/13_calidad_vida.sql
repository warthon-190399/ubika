-- ============================================================
-- 13_calidad_vida.sql · score de calidad de vida (0–10) guardado como dato
-- Correr después de 01–12. Se puede volver a correr.
-- Lo llena: python -m ubika.pipeline --etapas calidad   (después de entorno y capas)
-- Metodología: docs/metodologia_calidad_vida.md · pesos: config.yaml (calidad_vida)
--
-- Tres niveles con las mismas columnas:
--   calidad_vida_celda     una fila por celda de ~350 m de la grilla de la ciudad (capas_grilla)
--   calidad_vida_inmueble  una fila por inmueble con coordenadas (propiedades + entorno)
--   calidad_vida_distrito  una fila por distrito: mediana de sus celdas
-- Para cada componente se guarda el valor real (val_*) y su posición frente a toda Lima (pos_*, 0 = peor, 1 = mejor).
-- score = 10 × Σ peso × pos / Σ pesos de los componentes con dato.
-- ============================================================
BEGIN;

CREATE TABLE IF NOT EXISTS calidad_vida_celda (
    celda               INTEGER PRIMARY KEY,           -- misma celda que capas_grilla
    latitud             DOUBLE PRECISION NOT NULL,
    longitud            DOUBLE PRECISION NOT NULL,
    distrito            TEXT REFERENCES distritos(distrito) ON UPDATE CASCADE,
    -- valores reales
    val_denuncias_10k   REAL,       -- denuncias de robo y violencia a 500 m en 12 meses por 10 mil habitantes
    val_homicidios_100k REAL,       -- homicidios por 100 mil habitantes del distrito (SINADEF)
    val_edad_al_morir   REAL,       -- edad promedio al morir por causas naturales en el distrito (SINADEF)
    val_transporte_m    REAL,       -- metros a la estación más cercana
    val_servicios       REAL,       -- colegios + salud + comisarías + malls a 500 m
    val_verde_m2_hab    REAL,       -- m² de parque a 500 m por habitante
    val_barrio          REAL,       -- comercio de todos los días a 500 m
    val_ruido_db        REAL,       -- dB de tráfico estimados
    -- posiciones frente a todas las celdas de Lima (0 = peor, 1 = mejor)
    pos_denuncias       REAL CHECK (pos_denuncias BETWEEN 0 AND 1),
    pos_homicidios      REAL CHECK (pos_homicidios BETWEEN 0 AND 1),
    pos_seguridad       REAL CHECK (pos_seguridad BETWEEN 0 AND 1),   -- combinación de las dos anteriores
    pos_longevidad      REAL CHECK (pos_longevidad BETWEEN 0 AND 1),
    pos_transporte      REAL CHECK (pos_transporte BETWEEN 0 AND 1),
    pos_servicios       REAL CHECK (pos_servicios BETWEEN 0 AND 1),
    pos_verde           REAL CHECK (pos_verde BETWEEN 0 AND 1),
    pos_barrio          REAL CHECK (pos_barrio BETWEEN 0 AND 1),
    pos_ruido           REAL CHECK (pos_ruido BETWEEN 0 AND 1),
    score               REAL CHECK (score BETWEEN 0 AND 10),
    n_componentes       SMALLINT NOT NULL,             -- cuántos de los 7 componentes tuvieron dato
    version             SMALLINT NOT NULL,             -- calidad_vida.version de config.yaml
    calculado_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_calidad_celda_distrito ON calidad_vida_celda (distrito);

CREATE TABLE IF NOT EXISTS calidad_vida_inmueble (
    prop_id             UUID PRIMARY KEY REFERENCES propiedades(prop_id) ON DELETE CASCADE,
    distrito            TEXT REFERENCES distritos(distrito) ON UPDATE CASCADE,
    celda               INTEGER,                       -- celda de la grilla de la que salen verde, barrio y ruido
    val_denuncias_10k   REAL,
    val_homicidios_100k REAL,
    val_edad_al_morir   REAL,
    val_transporte_m    REAL,
    val_servicios       REAL,
    val_verde_m2_hab    REAL,
    val_barrio          REAL,
    val_ruido_db        REAL,
    pos_denuncias       REAL CHECK (pos_denuncias BETWEEN 0 AND 1),
    pos_homicidios      REAL CHECK (pos_homicidios BETWEEN 0 AND 1),
    pos_seguridad       REAL CHECK (pos_seguridad BETWEEN 0 AND 1),
    pos_longevidad      REAL CHECK (pos_longevidad BETWEEN 0 AND 1),
    pos_transporte      REAL CHECK (pos_transporte BETWEEN 0 AND 1),
    pos_servicios       REAL CHECK (pos_servicios BETWEEN 0 AND 1),
    pos_verde           REAL CHECK (pos_verde BETWEEN 0 AND 1),
    pos_barrio          REAL CHECK (pos_barrio BETWEEN 0 AND 1),
    pos_ruido           REAL CHECK (pos_ruido BETWEEN 0 AND 1),
    score               REAL CHECK (score BETWEEN 0 AND 10),
    pos_score           REAL CHECK (pos_score BETWEEN 0 AND 1),   -- su score frente a todas las celdas de Lima
    n_componentes       SMALLINT NOT NULL,
    version             SMALLINT NOT NULL,
    calculado_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS calidad_vida_distrito (
    distrito            TEXT PRIMARY KEY REFERENCES distritos(distrito) ON UPDATE CASCADE,
    n_celdas            INTEGER NOT NULL,
    score               REAL CHECK (score BETWEEN 0 AND 10),      -- mediana de las celdas del distrito
    score_p25           REAL,                                     -- dispersión dentro del distrito
    score_p75           REAL,
    pos_seguridad       REAL, pos_longevidad REAL, pos_transporte REAL, pos_servicios REAL,
    pos_verde           REAL, pos_barrio     REAL, pos_ruido      REAL,   -- medianas de las celdas
    puesto              SMALLINT,                                 -- 1 = mejor score de Lima y Callao
    version             SMALLINT NOT NULL,
    calculado_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);

COMMIT;

-- ============================================================
-- 07_capas.sql · grilla de la ciudad para las capas del mapa
-- Correr después de 01–06. Se puede volver a correr.
-- Lo llena: python -m ubika.pipeline --etapas capas
-- ============================================================
CREATE TABLE IF NOT EXISTS capas_grilla (
    capa          TEXT NOT NULL CHECK (capa IN ('seguridad', 'transporte', 'servicios')),
    celda         INTEGER NOT NULL,              -- id de la celda en la grilla hexagonal
    latitud       DOUBLE PRECISION NOT NULL,
    longitud      DOUBLE PRECISION NOT NULL,
    valor         DOUBLE PRECISION NOT NULL,     -- seguridad: denuncias ponderadas a 500 m (12 meses)
                                                 -- transporte: metros a la estación más cercana
                                                 -- servicios: colegios + salud + comisarías + malls a 500 m
    indice        REAL NOT NULL CHECK (indice BETWEEN 0 AND 1),  -- 0 = peor, 1 = mejor (percentil en la ciudad)
    calculado_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (capa, celda)
);

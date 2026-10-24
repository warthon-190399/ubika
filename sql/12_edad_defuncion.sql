-- ============================================================
-- 12_edad_defuncion.sql · edad al morir por distrito (SINADEF) → capa de longevidad del mapa
-- Correr después de 10_defunciones.sql. Se puede volver a correr.
-- Lo llena: python -m ubika.referencias.sinadef   (junto con defunciones_distrito_mes)
--
-- Por distrito de DOMICILIO, año y tipo (natural = MUERTE VIOLENTA vacía o "SIN REGISTRO"; violenta = el resto).
-- Edad en años; los menores de un año (días, meses, horas…) cuentan como 0. Sin edad registrada no entran.
-- Ojo al leerlo: la edad promedio al morir también refleja la edad de la población. Donde vive más
-- gente mayor, la edad al morir sale más alta aunque la salud sea la misma.
-- ============================================================
BEGIN;

CREATE TABLE IF NOT EXISTS defunciones_edad_distrito (
    provincia      TEXT NOT NULL,
    distrito_raw   TEXT NOT NULL,
    distrito       TEXT REFERENCES distritos(distrito) ON UPDATE CASCADE,
    anio           SMALLINT NOT NULL,
    tipo           TEXT NOT NULL CHECK (tipo IN ('natural', 'violenta')),
    n_con_edad     INTEGER NOT NULL CHECK (n_con_edad > 0),
    suma_edad      NUMERIC(14, 1) NOT NULL,      -- para promediar entre años: suma / n
    n_menores_1    INTEGER NOT NULL DEFAULT 0,
    n_65_mas       INTEGER NOT NULL DEFAULT 0,
    n_80_mas       INTEGER NOT NULL DEFAULT 0,
    cargado_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (provincia, distrito_raw, anio, tipo)
);
CREATE INDEX IF NOT EXISTS idx_defunciones_edad_distrito ON defunciones_edad_distrito (distrito, anio);

COMMIT;


-- Longevidad por distrito: mismos años que v_mortalidad_distrito_reciente (los 3 últimos completos sin
-- 2020–2021, con el archivo actual 2019, 2022 y 2023).
CREATE OR REPLACE VIEW v_longevidad_distrito AS
WITH cobertura AS (
    SELECT anio FROM defunciones_distrito_mes GROUP BY anio HAVING COUNT(DISTINCT mes) = 12
), anios AS (
    SELECT anio FROM cobertura WHERE anio NOT IN (2020, 2021) ORDER BY anio DESC LIMIT 3
)
SELECT
    d.distrito,
    d.nombre                                                                           AS distrito_nombre,
    MIN(e.anio)                                                                        AS longevidad_desde,
    MAX(e.anio)                                                                        AS longevidad_hasta,
    SUM(e.n_con_edad) FILTER (WHERE e.tipo = 'natural')::INT                           AS n_naturales,
    ROUND(SUM(e.suma_edad) FILTER (WHERE e.tipo = 'natural')
          / NULLIF(SUM(e.n_con_edad) FILTER (WHERE e.tipo = 'natural'), 0), 1)         AS edad_promedio_natural,
    ROUND(100.0 * SUM(e.n_80_mas) FILTER (WHERE e.tipo = 'natural')
          / NULLIF(SUM(e.n_con_edad) FILTER (WHERE e.tipo = 'natural'), 0), 1)         AS pct_80_mas_natural,
    ROUND(SUM(e.suma_edad) / NULLIF(SUM(e.n_con_edad), 0), 1)                          AS edad_promedio_todas
FROM defunciones_edad_distrito e
JOIN anios USING (anio)
JOIN distritos d USING (distrito)
GROUP BY d.distrito, d.nombre;

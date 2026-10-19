-- ============================================================
-- 10_defunciones.sql · defunciones SINADEF (MINSA) y tasa de mortalidad por 100 mil habitantes
-- Correr después de 01–09. Se puede volver a correr.
-- Lo llena: python -m ubika.referencias.sinadef
--
-- Fuente: "Información de Fallecidos del Sistema Informático Nacional de Defunciones - SINADEF"
-- (MINSA, Plataforma Nacional de Datos Abiertos). Un certificado de defunción por fila.
-- - El distrito es el de DOMICILIO del fallecido, no el lugar donde murió: la tasa mide el riesgo
--   de quienes viven en el distrito (al revés que las denuncias SIDPOL, que van por lugar del hecho).
-- - tipo_muerte sale de la columna MUERTE VIOLENTA del certificado. La gran mayoría viene
--   "SIN REGISTRO", que es la muerte natural (no violenta).
-- - El archivo publicado cubre 2017-01 a 2024-05 (a oct. 2026). 2017–2019 tiene menos certificados
--   porque SINADEF todavía no se usaba en todos lados: comparar distritos dentro de un mismo año.
-- - Los homicidios de SINADEF son
--   menos que los de la PNP/INEI: muchas muertes violentas pasan por la morgue y no siempre se
--   registran con su tipo. Sirve para comparar distritos, no como cifra oficial de homicidios.
-- ============================================================
BEGIN;

-- ── Conteos por distrito de domicilio, mes y tipo de muerte ─
CREATE TABLE IF NOT EXISTS defunciones_distrito_mes (
    provincia     TEXT NOT NULL,                  -- provincia de domicilio, tal como viene: LIMA / CALLAO
    distrito_raw  TEXT NOT NULL,                  -- distrito de domicilio, tal como viene
    distrito      TEXT REFERENCES distritos(distrito) ON UPDATE CASCADE,
    anio          SMALLINT NOT NULL,
    mes           SMALLINT NOT NULL CHECK (mes BETWEEN 1 AND 12),
    tipo_muerte   TEXT NOT NULL CHECK (tipo_muerte IN (
        'no_violenta',        -- SIN REGISTRO o vacío: muerte natural
        'homicidio',
        'transito',           -- ACCIDENTE DE TRANSITO
        'suicidio',
        'otro_accidente',
        'accidente_trabajo',
        'violenta_sin_tipo')), -- NO SE CONOCE: violenta, sin saber si fue homicidio, accidente o suicidio
    n             INTEGER NOT NULL CHECK (n > 0),
    cargado_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (provincia, distrito_raw, anio, mes, tipo_muerte)
);
CREATE INDEX IF NOT EXISTS idx_defunciones_distrito ON defunciones_distrito_mes (distrito, anio);

COMMIT;


-- Por distrito y año, tasas por 100 mil habitantes (población del censo 2017, ver 08_poblacion.sql).
-- meses = meses con datos ese año; un año incompleto (el último) da tasas más bajas.
CREATE OR REPLACE VIEW v_mortalidad_distrito AS
WITH cobertura AS (
    SELECT anio, COUNT(DISTINCT mes)::INT AS meses FROM defunciones_distrito_mes GROUP BY anio
)
SELECT
    d.distrito,
    d.nombre                                                              AS distrito_nombre,
    d.ubigeo,
    m.anio,
    c.meses,
    d.poblacion,
    SUM(m.n)::INT                                                         AS defunciones,
    COALESCE(SUM(m.n) FILTER (WHERE m.tipo_muerte <> 'no_violenta'), 0)::INT AS violentas,
    COALESCE(SUM(m.n) FILTER (WHERE m.tipo_muerte = 'homicidio'), 0)::INT AS homicidios,
    COALESCE(SUM(m.n) FILTER (WHERE m.tipo_muerte = 'transito'), 0)::INT  AS transito,
    COALESCE(SUM(m.n) FILTER (WHERE m.tipo_muerte = 'suicidio'), 0)::INT  AS suicidios,
    ROUND(100000.0 * SUM(m.n) / NULLIF(d.poblacion, 0), 1)                AS tasa_100k,
    ROUND(100000.0 * COALESCE(SUM(m.n) FILTER (WHERE m.tipo_muerte <> 'no_violenta'), 0)
          / NULLIF(d.poblacion, 0), 1)                                    AS tasa_violentas_100k,
    ROUND(100000.0 * COALESCE(SUM(m.n) FILTER (WHERE m.tipo_muerte = 'homicidio'), 0)
          / NULLIF(d.poblacion, 0), 1)                                    AS tasa_homicidios_100k
FROM defunciones_distrito_mes m
JOIN distritos d USING (distrito)
JOIN cobertura c USING (anio)
WHERE d.poblacion IS NOT NULL
GROUP BY d.distrito, d.nombre, d.ubigeo, m.anio, c.meses, d.poblacion;


-- Promedio anual de los últimos 3 años completos (12 meses con datos), sin 2020 y 2021: la pandemia
-- duplicó las muertes naturales. En distritos chicos un año suelto tiene muy pocos homicidios,
-- así que para comparar conviene esta vista. Con el archivo actual son 2019, 2022 y 2023.
CREATE OR REPLACE VIEW v_mortalidad_distrito_reciente AS
WITH anios AS (
    SELECT anio FROM (SELECT DISTINCT anio, meses FROM v_mortalidad_distrito) a
    WHERE meses = 12 AND anio NOT IN (2020, 2021) ORDER BY anio DESC LIMIT 3
)
SELECT
    v.distrito,
    v.distrito_nombre,
    v.ubigeo,
    MIN(v.anio)                                            AS anio_desde,
    MAX(v.anio)                                            AS anio_hasta,
    v.poblacion,
    ROUND(AVG(v.defunciones), 1)                           AS defunciones_anio,
    ROUND(AVG(v.violentas), 1)                             AS violentas_anio,
    ROUND(AVG(v.homicidios), 1)                            AS homicidios_anio,
    ROUND(AVG(v.tasa_100k), 1)                             AS tasa_100k,
    ROUND(AVG(v.tasa_violentas_100k), 1)                   AS tasa_violentas_100k,
    ROUND(AVG(v.tasa_homicidios_100k), 1)                  AS tasa_homicidios_100k
FROM v_mortalidad_distrito v
JOIN anios USING (anio)
GROUP BY v.distrito, v.distrito_nombre, v.ubigeo, v.poblacion;

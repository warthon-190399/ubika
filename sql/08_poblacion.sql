-- ============================================================
-- 08_poblacion.sql · población por distrito y tasa de denuncias por 10 mil habitantes
-- Correr después de 01–07. Se puede volver a correr.
--
-- Fuente de la población: INEI, Censos Nacionales 2017, población censada por distrito
--   Lima: Resultados definitivos, Provincia de Lima, Cuadro 2.2
--   Callao: Resultados definitivos, Provincia Constitucional del Callao, Cuadro 2.2
-- Es el último censo con resultados por distrito; la población actual es mayor, así que las
-- tasas salen algo infladas por igual en todos los distritos (sirven para comparar entre ellos).
-- ============================================================
BEGIN;

ALTER TABLE distritos ADD COLUMN IF NOT EXISTS poblacion INTEGER CHECK (poblacion > 0);
ALTER TABLE distritos ADD COLUMN IF NOT EXISTS poblacion_fuente TEXT;

UPDATE distritos d SET poblacion = v.poblacion, poblacion_fuente = 'INEI, Censos Nacionales 2017 (población censada)'
FROM (VALUES
    ('150101', 268352), ('150102', 62928), ('150103', 599196), ('150104', 34378), ('150105', 85309),
    ('150106', 333045), ('150107', 42912), ('150108', 314241), ('150109', 34684), ('150110', 520450),
    ('150111', 198862), ('150112', 211360), ('150113', 75359), ('150114', 140679), ('150115', 173630),
    ('150116', 54711), ('150117', 325884), ('150118', 240814), ('150119', 89195), ('150120', 60290),
    ('150121', 83323), ('150122', 99337), ('150123', 110071), ('150124', 14891), ('150125', 329675),
    ('150126', 15874), ('150127', 7074), ('150128', 174785), ('150129', 7482), ('150130', 113247),
    ('150131', 60735), ('150132', 1038495), ('150133', 355219), ('150134', 52082), ('150135', 654083),
    ('150136', 155384), ('150137', 196214), ('150138', 999), ('150139', 27863), ('150140', 329152),
    ('150141', 91023), ('150142', 393254), ('150143', 398433),
    ('070101', 451260), ('070102', 74851), ('070103', 42240), ('070104', 61417), ('070105', 3829),
    ('070106', 315600), ('070107', 45297)
) AS v(ubigeo, poblacion)
WHERE d.ubigeo = v.ubigeo;

COMMIT;

-- Denuncias de robo y violencia de los últimos 12 meses (todas, con o sin coordenada) por 10 mil habitantes.
-- Ojo: los distritos comerciales (Cercado, San Isidro, Miraflores, La Victoria) reciben mucha más gente
-- de la que vive en ellos, así que su tasa por residente sale alta.
CREATE OR REPLACE VIEW v_crimen_distrito AS
SELECT
    d.distrito,
    d.nombre                                          AS distrito_nombre,
    d.ubigeo,
    d.poblacion,
    COALESCE(SUM(w.n_total) FILTER (WHERE w.categoria = 'patrimonio'), 0)::INT AS denuncias_patrimonio,
    COALESCE(SUM(w.n_total) FILTER (WHERE w.categoria = 'violencia'), 0)::INT  AS denuncias_violencia,
    COALESCE(SUM(w.n_total), 0)::INT                                          AS denuncias,
    ROUND(10000.0 * COALESCE(SUM(w.n_total), 0) / NULLIF(d.poblacion, 0), 1)  AS tasa_10k
FROM distritos d
LEFT JOIN v_delitos_distrito_12m w
       ON w.distrito = d.distrito AND w.categoria IN ('patrimonio', 'violencia')
WHERE d.poblacion IS NOT NULL
GROUP BY d.distrito, d.nombre, d.ubigeo, d.poblacion;

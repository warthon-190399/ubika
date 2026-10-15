-- ============================================================
-- 04_delitos.sql · denuncias policiales SIDPOL (MININTER)
-- Correr después de 01–03. Se puede volver a correr.
-- Lo llena: python -m ubika.referencias.sidpol
-- ============================================================
BEGIN;

-- ── Ubigeo INEI en el catálogo de distritos ─────────────────
ALTER TABLE distritos ADD COLUMN IF NOT EXISTS ubigeo CHAR(6);
CREATE UNIQUE INDEX IF NOT EXISTS idx_distritos_ubigeo ON distritos (ubigeo);

UPDATE distritos d SET ubigeo = v.ubigeo
FROM (VALUES
    ('lima cercado', '150101'), ('ancon', '150102'), ('ate', '150103'), ('barranco', '150104'),
    ('brena', '150105'), ('carabayllo', '150106'), ('chaclacayo', '150107'), ('chorrillos', '150108'),
    ('cieneguilla', '150109'), ('comas', '150110'), ('el agustino', '150111'), ('independencia', '150112'),
    ('jesus maria', '150113'), ('la molina', '150114'), ('la victoria', '150115'), ('lince', '150116'),
    ('los olivos', '150117'), ('lurigancho', '150118'), ('lurin', '150119'), ('magdalena', '150120'),
    ('pueblo libre', '150121'), ('miraflores', '150122'), ('pachacamac', '150123'), ('pucusana', '150124'),
    ('puente piedra', '150125'), ('punta hermosa', '150126'), ('punta negra', '150127'), ('rimac', '150128'),
    ('san bartolo', '150129'), ('san borja', '150130'), ('san isidro', '150131'), ('sjl', '150132'),
    ('sjm', '150133'), ('san luis', '150134'), ('smp', '150135'), ('san miguel', '150136'),
    ('santa anita', '150137'), ('santa maria del mar', '150138'), ('santa rosa', '150139'), ('surco', '150140'),
    ('surquillo', '150141'), ('ves', '150142'), ('vmt', '150143'),
    ('callao', '070101'), ('bellavista', '070102'), ('carmen de la legua', '070103'), ('la perla', '070104'),
    ('la punta', '070105'), ('ventanilla', '070106'), ('mi peru', '070107')
) AS v(distrito, ubigeo)
WHERE d.distrito = v.distrito;


-- ── Denuncias con ubicación propia ──────────────────────────
CREATE TABLE IF NOT EXISTS delitos_puntos (
    id_dgc              TEXT PRIMARY KEY,         -- ID_DGC_03 de SIDPOL
    fecha_hecho         TIMESTAMPTZ NOT NULL,
    anio                SMALLINT NOT NULL,        -- año y mes en hora de Lima
    mes                 SMALLINT NOT NULL CHECK (mes BETWEEN 1 AND 12),
    provincia           TEXT NOT NULL,
    distrito_raw        TEXT,                     -- distrito_hecho tal cual
    distrito            TEXT REFERENCES distritos(distrito) ON UPDATE CASCADE,
    ubigeo_raw          TEXT,
    tipo_hecho          TEXT NOT NULL,
    subtipo_hecho       TEXT,
    modalidad_hecho     TEXT,
    categoria           TEXT NOT NULL CHECK (categoria IN
                          ('patrimonio', 'violencia', 'violencia_familiar', 'seguridad_publica', 'faltas', 'otros')),
    latitud             DOUBLE PRECISION NOT NULL,
    longitud            DOUBLE PRECISION NOT NULL,
    estado_coord        TEXT,                     -- cómo validó MININTER la coordenada
    actualizado_fuente  TIMESTAMPTZ,
    cargado_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_delitos_cat_fecha ON delitos_puntos (categoria, fecha_hecho);
CREATE INDEX IF NOT EXISTS idx_delitos_distrito  ON delitos_puntos (distrito);


-- ── Conteos de todas las denuncias por distrito y mes ───────
CREATE TABLE IF NOT EXISTS delitos_distrito_mes (
    provincia         TEXT NOT NULL,
    distrito_raw      TEXT NOT NULL,
    distrito          TEXT REFERENCES distritos(distrito) ON UPDATE CASCADE,
    anio              SMALLINT NOT NULL,
    mes               SMALLINT NOT NULL CHECK (mes BETWEEN 1 AND 12),
    tipo_hecho        TEXT NOT NULL,
    categoria         TEXT NOT NULL,
    n_total           INTEGER NOT NULL CHECK (n_total >= 0),
    n_con_ubicacion   INTEGER NOT NULL DEFAULT 0 CHECK (n_con_ubicacion >= 0),
    cargado_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (provincia, distrito_raw, anio, mes, tipo_hecho)
);


-- ── Entorno: delitos cercanos (ponderados) ──────────────────
ALTER TABLE entorno ADD COLUMN IF NOT EXISTS n_delitos_12m NUMERIC(10, 1);

COMMIT;


-- Últimos 12 meses con datos, por distrito y categoría.
-- peso = total / con_ubicacion: corrige que cada distrito ubique un % distinto de sus denuncias.
CREATE OR REPLACE VIEW v_delitos_distrito_12m AS
WITH ventana AS (
    SELECT MAX(make_date(anio, mes, 1)) AS fin FROM delitos_distrito_mes
)
SELECT
    m.distrito,
    d.nombre                                                       AS distrito_nombre,
    m.categoria,
    SUM(m.n_total)                                                 AS n_total,
    SUM(m.n_con_ubicacion)                                         AS n_con_ubicacion,
    ROUND(SUM(m.n_con_ubicacion)::NUMERIC / NULLIF(SUM(m.n_total), 0), 3) AS pct_con_ubicacion,
    ROUND(SUM(m.n_total)::NUMERIC / NULLIF(SUM(m.n_con_ubicacion), 0), 3) AS peso
FROM delitos_distrito_mes m
CROSS JOIN ventana v
LEFT JOIN distritos d USING (distrito)
WHERE make_date(m.anio, m.mes, 1) > v.fin - INTERVAL '12 months'
  AND m.distrito IS NOT NULL
GROUP BY m.distrito, d.nombre, m.categoria;

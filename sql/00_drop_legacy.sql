-- ============================================================
-- 00_drop_legacy.sql
-- Borra TODO el esquema anterior (urbania/adondevivir, vistas,
-- tablas de referencia y datasets). Correr una sola vez, antes de 01.
--
-- Antes de correrlo, si quieres ver qué hay: sección 0 de query.sql.
-- ============================================================
BEGIN;

-- Vistas
DROP MATERIALIZED VIEW IF EXISTS propiedades_union CASCADE;
DROP VIEW IF EXISTS urbania_clean     CASCADE;
DROP VIEW IF EXISTS adondevivir_clean CASCADE;

-- Datasets y features
DROP TABLE IF EXISTS dataset_final          CASCADE;
DROP TABLE IF EXISTS dataset                CASCADE;
DROP TABLE IF EXISTS proximidades           CASCADE;
DROP TABLE IF EXISTS propiedades_procesadas CASCADE;

-- Scraping antiguo
DROP TABLE IF EXISTS urbania_detalles      CASCADE;
DROP TABLE IF EXISTS urbania_listings      CASCADE;
DROP TABLE IF EXISTS adondevivir_detalles  CASCADE;
DROP TABLE IF EXISTS adondevivir_listings  CASCADE;

-- Referencias antiguas (una tabla por fuente)
DROP TABLE IF EXISTS colegios      CASCADE;
DROP TABLE IF EXISTS comisarias    CASCADE;
DROP TABLE IF EXISTS hospitales    CASCADE;
DROP TABLE IF EXISTS inpe          CASCADE;
DROP TABLE IF EXISTS malls         CASCADE;
DROP TABLE IF EXISTS metropolitano CASCADE;
DROP TABLE IF EXISTS tren          CASCADE;

-- Función de triggers antigua (01 la vuelve a crear)
DROP FUNCTION IF EXISTS set_updated_at() CASCADE;

COMMIT;

-- Debe quedar vacío (o solo con objetos que no son de ubika):
SELECT table_name, table_type
FROM information_schema.tables
WHERE table_schema = 'public'
ORDER BY table_name;

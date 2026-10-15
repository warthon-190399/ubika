-- ============================================================
-- query.sql · consultas de respaldo y verificación (solo lectura)
-- Copia la sección que necesites en el SQL Editor de Neon.
-- ============================================================

-- ── 0. Inventario: qué hay en la base ───────────────────────
SELECT t.table_name, t.table_type,
       (xpath('/row/n/text()',
              query_to_xml(format('SELECT count(*) AS n FROM %I', t.table_name), false, true, '')))[1]::text::bigint AS filas
FROM information_schema.tables t
WHERE t.table_schema = 'public' AND t.table_type = 'BASE TABLE'
ORDER BY t.table_name;

SELECT matviewname FROM pg_matviews WHERE schemaname = 'public';
SELECT table_name  FROM information_schema.views WHERE table_schema = 'public';


-- ── 1. Últimas corridas ─────────────────────────────────────
SELECT corrida_id, etapa, parametros, estado, filas_leidas, filas_escritas,
       iniciada_at, terminada_at - iniciada_at AS duracion, mensaje
FROM corridas
ORDER BY corrida_id DESC
LIMIT 20;


-- ── 2. Capa bruta ───────────────────────────────────────────
-- Avisos por lote de scraping
SELECT fuente, operacion, scrape_date, COUNT(*) AS avisos, COUNT(DISTINCT url) AS urls
FROM raw_listings
GROUP BY 1, 2, 3
ORDER BY scrape_date DESC, fuente, operacion;

-- URLs del listado que aún no tienen detalle (cola del scraper de detalle)
SELECT r.fuente, r.operacion, COUNT(DISTINCT r.url) AS pendientes
FROM raw_listings r
LEFT JOIN raw_detalles d USING (url)
WHERE d.url IS NULL
GROUP BY 1, 2;

-- Estado de los detalles
SELECT fuente, estado, COUNT(*) FROM raw_detalles GROUP BY 1, 2;


-- ── 3. Capa limpia ──────────────────────────────────────────
-- Inmuebles por operación, con y sin coordenadas
SELECT operacion, activo,
       COUNT(*)                                   AS inmuebles,
       COUNT(*) FILTER (WHERE latitud IS NULL)    AS sin_coordenadas,
       COUNT(*) FILTER (WHERE distrito IS NULL)   AS sin_distrito
FROM propiedades
GROUP BY 1, 2;

-- Inmuebles con más de un aviso (repetidos que se unificaron)
SELECT p.prop_id, p.operacion, p.distrito, p.precio_pen, p.area_m2, COUNT(a.url) AS n_avisos,
       array_agg(a.fuente) AS fuentes
FROM propiedades p JOIN avisos a USING (prop_id)
GROUP BY p.prop_id
HAVING COUNT(a.url) > 1
ORDER BY n_avisos DESC
LIMIT 50;

-- Textos de distrito que no reconoce el catálogo (agregar a distrito_alias)
SELECT r.ubicacion_raw, COUNT(*)
FROM raw_listings r
JOIN avisos a USING (url)
JOIN propiedades p USING (prop_id)
WHERE p.distrito IS NULL
GROUP BY 1
ORDER BY 2 DESC;


-- ── 4. Geocoding ────────────────────────────────────────────
SELECT estado, location_type, COUNT(*) FROM geocode_cache GROUP BY 1, 2 ORDER BY 3 DESC;


-- ── 5. Referencias y entorno ────────────────────────────────
SELECT categoria, fuente, COUNT(*) FROM puntos_interes GROUP BY 1, 2 ORDER BY 1;
SELECT COUNT(*) AS inpe FROM inpe_domicilios;

SELECT COUNT(*) AS con_entorno,
       ROUND(AVG(n_colegios), 1)       AS prom_colegios,
       ROUND(AVG(dist_transporte_m))   AS prom_dist_transporte_m
FROM entorno;


-- ── 6. Delitos SIDPOL ───────────────────────────────────────
SELECT categoria, MIN(fecha_hecho)::date AS desde, MAX(fecha_hecho)::date AS hasta, COUNT(*) AS puntos
FROM delitos_puntos GROUP BY 1 ORDER BY 4 DESC;

-- % de denuncias con ubicación y peso por distrito (patrimonio, últimos 12 meses)
SELECT distrito_nombre, n_total, n_con_ubicacion, pct_con_ubicacion, peso
FROM v_delitos_distrito_12m WHERE categoria = 'patrimonio' ORDER BY n_total DESC;

-- Textos de distrito de SIDPOL que no reconoce el catálogo
SELECT provincia, distrito_raw, SUM(n_total) FROM delitos_distrito_mes
WHERE distrito IS NULL GROUP BY 1, 2 ORDER BY 3 DESC;


-- ── 7. Lo que ve la app ─────────────────────────────────────
SELECT operacion, COUNT(*) FROM v_app_propiedades GROUP BY 1;
SELECT * FROM v_resumen_distrito ORDER BY operacion, n_inmuebles DESC;

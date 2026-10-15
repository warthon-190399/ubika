-- ============================================================
-- 03_views.sql · vistas que lee la API (server.js)
-- Se puede volver a correr.
-- ============================================================

-- Una fila por inmueble activo y ubicado en el mapa, con su entorno.
-- Minutos a pie: distancia en línea recta / 80 m por minuto (aprox.).
CREATE OR REPLACE VIEW v_app_propiedades AS
SELECT
    p.prop_id,
    p.operacion,
    p.tipo_inmueble,
    p.precio_pen,
    p.precio_usd,
    p.mantenimiento_pen,
    p.area_m2,
    p.precio_m2_pen,
    p.num_dorm,
    p.num_banios,
    p.num_estac,
    p.antiguedad_anios,
    p.direccion,
    p.distrito,
    d.nombre                        AS distrito_nombre,
    d.zona_apeim,
    d.nse_aprox,
    p.latitud,
    p.longitud,
    p.geo_precision,
    p.inmobiliaria,
    p.fecha_publicacion,
    p.primera_vez,
    p.ultima_vez,
    (SELECT a.url FROM avisos a WHERE a.prop_id = p.prop_id ORDER BY a.ultima_vez DESC LIMIT 1) AS url,
    (SELECT array_agg(DISTINCT a.fuente) FROM avisos a WHERE a.prop_id = p.prop_id)            AS fuentes,
    e.radio_m,
    e.n_colegios, e.n_salud, e.n_comisarias, e.n_transporte, e.n_malls, e.n_parques, e.n_inpe,
    e.dist_colegio_m, e.dist_salud_m, e.dist_comisaria_m, e.dist_transporte_m, e.dist_mall_m, e.dist_parque_m,
    CEIL(e.dist_transporte_m / 80.0)::INT AS min_transporte,
    CEIL(e.dist_colegio_m    / 80.0)::INT AS min_colegio,
    CEIL(e.dist_salud_m      / 80.0)::INT AS min_salud,
    CEIL(e.dist_comisaria_m  / 80.0)::INT AS min_comisaria,
    CEIL(e.dist_parque_m     / 80.0)::INT AS min_parque
FROM propiedades p
LEFT JOIN distritos d USING (distrito)
LEFT JOIN entorno   e USING (prop_id)
WHERE p.activo
  AND p.latitud IS NOT NULL
  AND p.longitud IS NOT NULL;


-- Resumen por distrito y operación (medianas, más robustas que el promedio con pocos avisos).
CREATE OR REPLACE VIEW v_resumen_distrito AS
SELECT
    p.operacion,
    p.distrito,
    d.nombre                                                            AS distrito_nombre,
    COUNT(*)                                                            AS n_inmuebles,
    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY p.precio_pen)           AS mediana_precio_pen,
    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY p.precio_m2_pen)        AS mediana_precio_m2_pen,
    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY p.area_m2)              AS mediana_area_m2,
    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY p.antiguedad_anios)     AS mediana_antiguedad,
    AVG(e.n_inpe)                                                       AS prom_n_inpe,
    AVG(e.dist_transporte_m)                                            AS prom_dist_transporte_m
FROM propiedades p
LEFT JOIN distritos d USING (distrito)
LEFT JOIN entorno   e USING (prop_id)
WHERE p.activo AND p.distrito IS NOT NULL
GROUP BY p.operacion, p.distrito, d.nombre;


-- Historial de precios publicados por inmueble (base para la pestaña Evolución).
CREATE OR REPLACE VIEW v_historial_avisos AS
SELECT
    a.prop_id,
    r.fuente,
    r.operacion,
    r.scrape_date,
    r.url,
    r.precio_raw
FROM raw_listings r
JOIN avisos a USING (url);

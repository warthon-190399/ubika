-- ============================================================
-- 06_vistas_entorno.sql · agrega delitos cercanos a la vista de la app
-- Correr después de 01–05. Se puede volver a correr.
-- (Las columnas nuevas van al final para que CREATE OR REPLACE VIEW funcione.)
-- ============================================================
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
    CEIL(e.dist_parque_m     / 80.0)::INT AS min_parque,
    e.n_delitos_12m                          -- denuncias de patrimonio y violencia a menos de radio_m, ponderadas
FROM propiedades p
LEFT JOIN distritos d USING (distrito)
LEFT JOIN entorno   e USING (prop_id)
WHERE p.activo
  AND p.latitud IS NOT NULL
  AND p.longitud IS NOT NULL;

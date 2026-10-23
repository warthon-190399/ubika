-- ============================================================
-- 11_correccion_ubicacion.sql · trazabilidad de las correcciones de ubicación
-- La limpieza corrige dos inconsistencias del portal (ver README, «Fuentes»):
--   distrito_por_poligono   la ubicación solo decía «Lima, Lima»: el distrito sale del polígono del pin
--   pin_lejos_del_distrito  el pin estaba a más de limpieza.max_metros_fuera_distrito del distrito
--                           declarado: se descarta y se vuelve a ubicar con Google (dirección + distrito)
-- El pin original del portal queda en lat_portal/lon_portal (y sin cambios en raw_listings).
-- Se puede volver a correr.
-- ============================================================
ALTER TABLE propiedades
    ADD COLUMN IF NOT EXISTS lat_portal            DOUBLE PRECISION,
    ADD COLUMN IF NOT EXISTS lon_portal            DOUBLE PRECISION,
    ADD COLUMN IF NOT EXISTS correccion_ubicacion  TEXT
        CHECK (correccion_ubicacion IN ('distrito_por_poligono', 'pin_lejos_del_distrito'));

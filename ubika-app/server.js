/**
 * server.js · API de solo lectura sobre Neon para la app de ubika.
 *
 *   GET /api/salud                      conexión y fecha de los datos
 *   GET /api/propiedades?operacion=…    inmuebles activos con su entorno (v_app_propiedades)
 *   GET /api/distritos?operacion=…      medianas por distrito (v_resumen_distrito)
 *   GET /api/capas/:capa                grilla de la ciudad: seguridad | transporte | servicios
 *   GET /api/cerca?lat=…&lon=…          puntos de interés a 500 m de un punto + la estación más cercana
 *   GET /api/crimen-distritos           denuncias de 12 meses por 10 mil habitantes (v_crimen_distrito)
 *                                       y homicidios por 100 mil habitantes (v_mortalidad_distrito_reciente, SINADEF)
 *                                       y edad promedio al morir por causas naturales (v_longevidad_distrito, SINADEF)
 *
 * Correr: node server.js   (lee DATABASE_URL de ubika-app/.env)
 */
import express from "express";
import cors from "cors";
import pg from "pg";
import dotenv from "dotenv";

dotenv.config();
if (!process.env.DATABASE_URL) {
  console.error("Falta DATABASE_URL en ubika-app/.env");
  process.exit(1);
}

const pool = new pg.Pool({
  connectionString: process.env.DATABASE_URL,
  ssl: process.env.DATABASE_URL.includes("sslmode=disable") ? false : { rejectUnauthorized: false },
  max: 5,
});
// NUMERIC llega como texto desde pg: convertir a número
pg.types.setTypeParser(1700, v => (v === null ? null : parseFloat(v)));

const app = express();
app.use(cors());

const OPERACIONES = new Set(["alquiler", "venta"]);
const CAPAS = new Set(["seguridad", "transporte", "servicios", "verde", "barrio", "ruido"]);
const operacionDe = req => (OPERACIONES.has(req.query.operacion) ? req.query.operacion : "alquiler");

// Caché simple en memoria: los datos cambian una vez por corrida del pipeline
const cache = new Map();
async function conCache(clave, minutos, fn) {
  const hit = cache.get(clave);
  if (hit && hit.hasta > Date.now()) return hit.valor;
  const valor = await fn();
  cache.set(clave, { valor, hasta: Date.now() + minutos * 60_000 });
  return valor;
}

const ruta = fn => async (req, res) => {
  try {
    res.json(await fn(req));
  } catch (err) {
    console.error(err);
    res.status(500).json({ error: "No pudimos leer la base de datos.", detalle: err.message });
  }
};

app.get("/api/salud", ruta(async () => {
  const { rows } = await pool.query(`
    SELECT
      (SELECT MAX(scrape_date) FROM raw_listings)                  AS ultimo_scraping,
      (SELECT MAX(make_date(anio, mes, 1)) FROM delitos_distrito_mes) AS delitos_hasta,
      (SELECT COUNT(*) FROM v_app_propiedades)::int                AS inmuebles
  `);
  return { ok: true, ...rows[0] };
}));

app.get("/api/propiedades", ruta(req => {
  const op = operacionDe(req);
  return conCache(`props:${op}`, 5, async () => {
    const { rows } = await pool.query(`
      SELECT prop_id, operacion, precio_pen, precio_usd, mantenimiento_pen, area_m2, precio_m2_pen,
             num_dorm, num_banios, num_estac, antiguedad_anios, direccion, distrito, distrito_nombre,
             latitud, longitud, geo_precision, inmobiliaria, fecha_publicacion, primera_vez, url, fuentes,
             radio_m, n_colegios, n_salud, n_comisarias, n_transporte, n_malls, n_inpe, n_delitos_12m,
             dist_colegio_m, dist_salud_m, dist_comisaria_m, dist_transporte_m, dist_mall_m,
             min_transporte, min_colegio, min_salud, min_comisaria
      FROM v_app_propiedades
      WHERE operacion = $1
      ORDER BY primera_vez DESC
      LIMIT 5000`, [op]);
    return rows;
  });
}));

app.get("/api/distritos", ruta(req => {
  const op = operacionDe(req);
  return conCache(`dist:${op}`, 5, async () => {
    const { rows } = await pool.query(`
      SELECT distrito, distrito_nombre, n_inmuebles::int, mediana_precio_pen, mediana_precio_m2_pen,
             mediana_area_m2, mediana_antiguedad
      FROM v_resumen_distrito WHERE operacion = $1
      ORDER BY n_inmuebles DESC`, [op]);
    return rows;
  });
}));

app.get("/api/capas/:capa", (req, res, next) =>
  CAPAS.has(req.params.capa) ? next() : res.status(400).json({ error: `Capa desconocida: ${req.params.capa}. Usa seguridad, transporte, servicios, verde, barrio o ruido.` }));
app.get("/api/capas/:capa", ruta(req => {
  const capa = req.params.capa;
  return conCache(`capa:${capa}`, 60, async () => {
    const { rows } = await pool.query(
      `SELECT latitud, longitud, indice, valor FROM capas_grilla WHERE capa = $1 ORDER BY celda`, [capa]);
    // formato compacto: [lat, lon, índice 0–1, valor]
    return { capa, celdas: rows.map(r => [+r.latitud.toFixed(5), +r.longitud.toFixed(5), +r.indice, +r.valor]) };
  });
}));

app.get("/api/crimen-distritos", ruta(() => conCache("crimen-distritos", 60, async () => {
  const { rows } = await pool.query(`
    SELECT c.distrito, c.distrito_nombre, c.ubigeo, c.poblacion, c.denuncias, c.denuncias_patrimonio,
           c.denuncias_violencia, c.tasa_10k,
           m.tasa_homicidios_100k, m.homicidios_anio, m.anio_desde AS homicidios_desde, m.anio_hasta AS homicidios_hasta,
           l.edad_promedio_natural, l.pct_80_mas_natural, l.n_naturales, l.longevidad_desde, l.longevidad_hasta
    FROM v_crimen_distrito c
    LEFT JOIN v_mortalidad_distrito_reciente m USING (distrito)
    LEFT JOIN v_longevidad_distrito l USING (distrito)
    ORDER BY c.tasa_10k DESC`);
  return rows;
})));

// Puntos de interés alrededor de un inmueble (colegios, salud, comisarías, comercio, transporte)
const CAJA = { latMin: -12.6, latMax: -11.5, lonMin: -77.3, lonMax: -76.55 };   // Lima y Callao
const DIST_SQL = `2 * 6371000 * asin(sqrt(power(sin(radians(latitud - $1) / 2), 2)
  + cos(radians($1)) * cos(radians(latitud)) * power(sin(radians(longitud - $2) / 2), 2)))`;
app.get("/api/cerca", ruta(async req => {
  const lat = Number(req.query.lat), lon = Number(req.query.lon);
  const radio = Math.min(Math.max(Number(req.query.radio) || 500, 100), 1500);
  if (!(lat >= CAJA.latMin && lat <= CAJA.latMax && lon >= CAJA.lonMin && lon <= CAJA.lonMax)) {
    return { puntos: [], error: "Coordenadas fuera de Lima" };
  }
  const grados = radio / 111000;   // caja previa para no medir toda la tabla
  const { rows } = await pool.query(`
    WITH cerca AS (
      SELECT categoria, nombre, latitud, longitud, ${DIST_SQL} AS dist_m, false AS mas_cercana
      FROM puntos_interes
      WHERE latitud BETWEEN $1 - $4 AND $1 + $4 AND longitud BETWEEN $2 - $4 * 1.03 AND $2 + $4 * 1.03
    ), estacion AS (
      SELECT categoria, nombre, latitud, longitud, ${DIST_SQL} AS dist_m, true AS mas_cercana
      FROM puntos_interes WHERE categoria IN ('metro', 'metropolitano', 'tren')
      ORDER BY 5 LIMIT 1
    )
    SELECT * FROM cerca WHERE dist_m <= $3
    UNION ALL SELECT * FROM estacion WHERE dist_m > $3
    ORDER BY dist_m LIMIT 400`, [lat, lon, radio, grados]);
  return { radio, puntos: rows.map(r => ({ ...r, dist_m: Math.round(r.dist_m) })) };
}));

const PORT = process.env.PORT || 3001;
app.listen(PORT, () => console.log(`API de ubika → http://localhost:${PORT}`));

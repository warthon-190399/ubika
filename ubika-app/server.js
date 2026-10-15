/**
 * server.js
 * Express API — lee desde Neon y sirve los datos al frontend.
 * Correr con: node server.js
 *
 * Instalar: npm install express cors pg dotenv
 */

import express from "express";
import cors from "cors";
import pg from "pg";
import dotenv from "dotenv";

dotenv.config();
const { Pool } = pg;

const pool = new Pool({ connectionString: process.env.DATABASE_URL, ssl: { rejectUnauthorized: false } });
const app = express();
app.use(cors());
app.use(express.json());

// ── Propiedades para el mapa ────────────────────────────────────────────────
// Devuelve solo las columnas que necesita Deck.gl para no saturar la red
app.get("/api/propiedades", async (req, res) => {
  try {
    const { distrito, precio_max, segmento, fuente } = req.query;
    const conditions = ["p.latitud IS NOT NULL", "p.longitud IS NOT NULL", "p.precio_pen IS NOT NULL"];
    const vals = [];
    let i = 1;
    if (distrito)   { conditions.push(`p.distrito = $${i++}`);      vals.push(distrito); }
    if (precio_max) { conditions.push(`p.precio_pen <= $${i++}`);   vals.push(+precio_max); }
    if (segmento)   { conditions.push(`d.tipo_vivienda = $${i++}`); vals.push(segmento); }
    if (fuente)     { conditions.push(`p.fuente = $${i++}`);        vals.push(fuente); }

    const sql = `
      SELECT
        p.prop_id,
        p.fuente,
        p.distrito,
        p.nivel_socioeconomico,
        p.precio_pen,
        p.precio_usd,
        p.area_m2,
        p.num_dorm,
        p.num_banios,
        p.num_estac,
        p.antiguedad,
        p.latitud,
        p.longitud,
        p.url,
        p.direccion_completa,
        p.publicado_por,
        d.tipo_vivienda,
        d.tipo_vivienda_cod,
        d.score_ubicacion,
        d.nivel_socioeconomico_cod,
        d.zona_apeim,
        d.num_colegios_aprox,
        d.num_hospitales_aprox,
        d.num_tren_est_aprox,
        d.num_metro_est_aprox,
        d.num_comisarias_aprox,
        d.num_delitos_aprox,
        d.num_malls_aprox,
        d.precio_por_m2,
        d.antiguedad_cod,
        d.categoria_crimenes
      FROM propiedades_procesadas p
      LEFT JOIN dataset_final d USING (prop_id)
      WHERE ${conditions.join(" AND ")}
      LIMIT 5000
    `;
    const { rows } = await pool.query(sql, vals);
    res.json(rows);
  } catch (err) {
    console.error(err);
    res.status(500).json({ error: err.message });
  }
});

// ── Stats generales ─────────────────────────────────────────────────────────
app.get("/api/stats", async (req, res) => {
  try {
    const { rows } = await pool.query(`
      SELECT
        COUNT(*)                          AS total,
        ROUND(AVG(precio_pen))            AS avg_precio,
        MIN(precio_pen)                   AS min_precio,
        MAX(precio_pen)                   AS max_precio,
        ROUND(AVG(area_m2))               AS avg_area,
        COUNT(DISTINCT distrito)          AS num_distritos,
        COUNT(DISTINCT fuente)            AS num_fuentes,
        SUM(CASE WHEN latitud IS NOT NULL THEN 1 ELSE 0 END) AS geocodificadas
      FROM propiedades_procesadas
      WHERE precio_pen IS NOT NULL
    `);
    res.json(rows[0]);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// ── Ranking de distritos ────────────────────────────────────────────────────
app.get("/api/distritos", async (req, res) => {
  try {
    const { rows } = await pool.query(`
      SELECT
        p.distrito,
        COUNT(*)                        AS total,
        ROUND(AVG(p.precio_pen))        AS avg_precio,
        ROUND(AVG(p.area_m2))           AS avg_area,
        ROUND(AVG(d.score_ubicacion),3) AS avg_score,
        ROUND(AVG(d.num_delitos_aprox)) AS avg_delitos,
        p.nivel_socioeconomico          AS nse
      FROM propiedades_procesadas p
      LEFT JOIN dataset_final d USING (prop_id)
      WHERE p.distrito IS NOT NULL AND p.precio_pen IS NOT NULL
      GROUP BY p.distrito, p.nivel_socioeconomico
      ORDER BY avg_score DESC NULLS LAST
    `);
    res.json(rows);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// ── Propiedad individual ────────────────────────────────────────────────────
app.get("/api/propiedades/:id", async (req, res) => {
  try {
    const { rows } = await pool.query(`
      SELECT p.*, d.*
      FROM propiedades_procesadas p
      LEFT JOIN dataset_final d USING (prop_id)
      WHERE p.prop_id = $1
    `, [req.params.id]);
    if (!rows.length) return res.status(404).json({ error: "not found" });
    res.json(rows[0]);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

const PORT = process.env.PORT || 3001;
app.listen(PORT, () => console.log(`Ubika API → http://localhost:${PORT}`));

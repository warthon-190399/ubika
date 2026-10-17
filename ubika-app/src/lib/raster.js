/**
 * raster.js · convierte la grilla de la ciudad (puntos cada 350 m) en una imagen continua y suavizada.
 *
 * El mapa de calor de deck.gl dibuja un círculo difuso por punto: lejos quedan manchas sueltas y de cerca
 * se ven los "lunares" de la grilla. Aquí cada celda pinta su píxel, un suavizado gaussiano rellena los
 * huecos y une las zonas, y la imagen se estira sobre el mapa con interpolación lineal: se lee como una
 * superficie pareja a cualquier zoom.
 */
const KM_LAT = 110.6, KM_LON = 108.9, PASO_KM = 0.35;    // los mismos que pipeline/capas.py
const D_LAT = (PASO_KM * Math.sqrt(3)) / 2 / KM_LAT;
const D_LON = PASO_KM / KM_LON / 2;                      // medio paso: las filas impares van corridas medio paso

/**
 * @param puntos   [{ lat, lon, v }] (v = valor ya normalizado, en general 0–1)
 * @param color    v → [r, g, b, a] (a 0–255), o null para dejar transparente
 * @param sigma    suavizado en píxeles (1 px ≈ 175 m de ancho, 300 m de alto)
 */
export function superficie(puntos, color, sigma = 2.2) {
  if (!puntos.length) return null;
  let latMin = Infinity, latMax = -Infinity, lonMin = Infinity, lonMax = -Infinity;
  for (const p of puntos) {
    latMin = Math.min(latMin, p.lat); latMax = Math.max(latMax, p.lat);
    lonMin = Math.min(lonMin, p.lon); lonMax = Math.max(lonMax, p.lon);
  }
  const pad = Math.ceil(sigma * 3);
  const cols = Math.round((lonMax - lonMin) / D_LON) + 1 + 2 * pad;
  const rows = Math.round((latMax - latMin) / D_LAT) + 1 + 2 * pad;
  const val = new Float32Array(cols * rows), peso = new Float32Array(cols * rows);
  for (const p of puntos) {
    const c = Math.round((p.lon - lonMin) / D_LON) + pad;
    const r = Math.round((latMax - p.lat) / D_LAT) + pad;           // fila 0 = norte
    // cada celda cubre dos columnas (su ancho real es un paso completo)
    for (const cc of [c, c + 1]) if (cc < cols) { val[r * cols + cc] += p.v; peso[r * cols + cc] += 1; }
  }
  // Suavizado gaussiano separable, normalizado: promedia solo donde hay datos y deja una cobertura 0–1
  const k = [], rad = Math.ceil(sigma * 3);
  for (let i = -rad; i <= rad; i++) k.push(Math.exp(-(i * i) / (2 * sigma * sigma)));
  const pasar = (src, w, h, horizontal) => {
    const out = new Float32Array(w * h);
    for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) {
      let s = 0;
      for (let i = -rad; i <= rad; i++) {
        const xx = horizontal ? x + i : x, yy = horizontal ? y : y + i;
        if (xx < 0 || yy < 0 || xx >= w || yy >= h) continue;
        s += src[yy * w + xx] * k[i + rad];
      }
      out[y * w + x] = s;
    }
    return out;
  };
  const sv = pasar(pasar(val, cols, rows, true), cols, rows, false);
  const sw = pasar(pasar(peso, cols, rows, true), cols, rows, false);
  const kmax = k.reduce((a, b) => a + b, 0) ** 2 * 0.5;           // cobertura "llena" (la mitad de los vecinos con dato)

  const canvas = document.createElement("canvas");
  canvas.width = cols; canvas.height = rows;
  const ctx = canvas.getContext("2d"), img = ctx.createImageData(cols, rows);
  for (let i = 0; i < cols * rows; i++) {
    if (sw[i] < 1e-3) continue;
    const rgba = color(sv[i] / sw[i]);
    if (!rgba) continue;
    const cobertura = Math.min(1, sw[i] / kmax);                   // bordes de la ciudad se desvanecen
    img.data.set([rgba[0], rgba[1], rgba[2], Math.round(rgba[3] * cobertura)], i * 4);
  }
  ctx.putImageData(img, 0, 0);
  return {
    image: canvas,
    // bordes de la imagen (no centros de píxel); cada celda ocupa las columnas c y c+1, centrada entre ambas
    bounds: [lonMin - (pad + 1) * D_LON, latMax - (rows - pad - 0.5) * D_LAT, lonMin + (cols - 1 - pad) * D_LON, latMax + (pad + 0.5) * D_LAT],
  };
}

/** Color continuo entre paradas: rampa de "#hex" y valor 0–1. */
export function rampa(stops) {
  const rgb = stops.map(h => [1, 3, 5].map(i => parseInt(h.slice(i, i + 2), 16)));
  return t => {
    const x = Math.min(1, Math.max(0, t)) * (rgb.length - 1), i = Math.min(rgb.length - 2, Math.floor(x)), f = x - i;
    return rgb[i].map((c, j) => Math.round(c + (rgb[i + 1][j] - c) * f));
  };
}

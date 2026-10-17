/**
 * hex.js · agrupa avisos en hexágonos (vértice arriba, igual que la grilla de la ciudad).
 * Se hace aquí y no con HexagonLayer para controlar la escala de color y que la leyenda
 * muestre valores exactos: con tan pocos avisos, cada celda cuenta.
 */
const LAT0 = -12.06, LON0 = -77.03;
const M_LAT = 110_574, M_LON = 111_320 * Math.cos(LAT0 * Math.PI / 180);

function redondear(q, r) {
  const s = -q - r;
  let rq = Math.round(q), rr = Math.round(r), rs = Math.round(s);
  const dq = Math.abs(rq - q), dr = Math.abs(rr - r), ds = Math.abs(rs - s);
  if (dq > dr && dq > ds) rq = -rr - rs; else if (dr > ds) rr = -rq - rs;
  return [rq, rr];
}

/** [{ position: [lon, lat], items: [...] }] con celdas de `radioM` metros (centro a vértice). */
export function hexagonos(items, radioM, getPos) {
  const celdas = new Map();
  for (const it of items) {
    const [lon, lat] = getPos(it);
    const x = (lon - LON0) * M_LON, y = (lat - LAT0) * M_LAT;
    const [q, r] = redondear((Math.sqrt(3) / 3 * x - y / 3) / radioM, (2 / 3 * y) / radioM);
    const k = `${q},${r}`;
    if (!celdas.has(k)) {
      const cx = radioM * Math.sqrt(3) * (q + r / 2), cy = radioM * 1.5 * r;
      celdas.set(k, { position: [LON0 + cx / M_LON, LAT0 + cy / M_LAT], items: [] });
    }
    celdas.get(k).items.push(it);
  }
  return [...celdas.values()];
}

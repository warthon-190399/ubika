/**
 * evaluador.js · cuánto debería costar un inmueble, por comparables.
 *
 * Toma los avisos de la misma operación (alquiler o venta) más parecidos al inmueble:
 * cerca en el mapa y con área, dormitorios, baños, estacionamientos y antigüedad parecidos.
 * El precio estimado es la mediana ponderada de su precio por m² × el área; el rango, sus
 * percentiles 25 y 75. Los más parecidos pesan más.
 *
 * No es un modelo entrenado: es lo que pide hoy el mercado por inmuebles como este, con los
 * avisos de la base. Por eso se explica solo (la lista de comparables) y mejora con cada scraping.
 */

export const K = 12;                 // comparables que se usan
export const CONSULTA_INICIAL = { propId: null, lat: null, lon: null, distrito: "", area: 80, dorm: 2, banos: 2, estac: 1, antig: null, pedido: null };

// Cuánto «pesa» cada diferencia, en la misma unidad que 1 km de distancia
const PASO = { km: 1, area: 0.25, dorm: 0.6, banos: 0.4, estac: 0.4, antig: 15 };

const KM_LAT = 111.32;
/** Distancia aproximada en km (equirectangular; sobra para distancias dentro de Lima). */
export function km(lat1, lon1, lat2, lon2) {
  const x = (lon2 - lon1) * KM_LAT * Math.cos(((lat1 + lat2) / 2) * Math.PI / 180);
  const y = (lat2 - lat1) * KM_LAT;
  return Math.hypot(x, y);
}

export const precioM2 = p => p.precio_m2_pen ?? (p.precio_pen && p.area_m2 ? p.precio_pen / p.area_m2 : null);
const sirve = p => p.precio_pen > 0 && p.area_m2 > 0 && p.latitud != null && p.longitud != null && precioM2(p) > 0;

/** Qué tan distinto es el aviso p de la consulta q (0 = idéntico, 1 ≈ estar a 1 km). */
export function diferencia(q, p) {
  let d = km(q.lat, q.lon, p.latitud, p.longitud) / PASO.km;
  d += Math.abs(Math.log(q.area / p.area_m2)) / PASO.area;
  d += Math.abs((q.dorm ?? 0) - (p.num_dorm ?? 0)) * PASO.dorm;
  d += Math.abs((q.banos ?? 0) - (p.num_banios ?? 0)) * PASO.banos;
  d += Math.abs((q.estac ?? 0) - (p.num_estac ?? 0)) * PASO.estac;
  // La antigüedad solo cuenta si ambos la tienen (muchos avisos no la dicen)
  if (q.antig != null && p.antiguedad_anios != null) d += Math.abs(q.antig - p.antiguedad_anios) / PASO.antig;
  return d;
}

/** Percentil ponderado (0–1) de pares [valor, peso]. */
export function percentilPonderado(pares, q) {
  const xs = [...pares].sort((a, b) => a[0] - b[0]);
  const total = xs.reduce((s, x) => s + x[1], 0);
  let acum = 0;
  for (const [v, w] of xs) {
    acum += w;
    if (acum >= q * total) return v;
  }
  return xs.at(-1)?.[0] ?? null;
}

/** Centro de los avisos de un distrito (mediana de lat y lon), para evaluar sin un punto exacto. */
export function centroDistrito(props, distrito) {
  const ps = props.filter(p => p.distrito === distrito && p.latitud != null);
  if (!ps.length) return null;
  const med = xs => { const s = [...xs].sort((a, b) => a - b); return s[Math.floor(s.length / 2)]; };
  return { lat: med(ps.map(p => p.latitud)), lon: med(ps.map(p => p.longitud)) };
}

/** Distrito del aviso más cercano a un punto (para rotular un punto tocado en el mapa). */
export function distritoCercano(props, lat, lon) {
  let mejor = null, dMin = Infinity;
  for (const p of props) {
    if (p.latitud == null || !p.distrito) continue;
    const d = km(lat, lon, p.latitud, p.longitud);
    if (d < dMin) { dMin = d; mejor = p.distrito; }
  }
  return mejor;
}

/**
 * Estima el precio de la consulta q con los avisos `props` (de una sola operación).
 * excluir: prop_id que no debe usarse como comparable (el mismo aviso que se evalúa).
 * Devuelve null si faltan la ubicación, el área o comparables.
 */
export function estimar(props, q, { k = K, excluir = null } = {}) {
  if (q.lat == null || q.lon == null || !(q.area > 0)) return null;
  const cand = [];
  for (const p of props) {
    if (p.prop_id === excluir || !sirve(p)) continue;
    cand.push({ p, d: diferencia(q, p) });
  }
  if (cand.length < 3) return null;
  cand.sort((a, b) => a.d - b.d);
  const comps = cand.slice(0, k).map(c => ({ ...c, w: 1 / (0.25 + c.d) ** 2, km: km(q.lat, q.lon, c.p.latitud, c.p.longitud) }));
  const pares = comps.map(c => [precioM2(c.p), c.w]);
  const m2 = percentilPonderado(pares, 0.5), m2Bajo = percentilPonderado(pares, 0.25), m2Alto = percentilPonderado(pares, 0.75);
  const kmMediana = [...comps.map(c => c.km)].sort((a, b) => a - b)[Math.floor(comps.length / 2)];
  const dispersion = m2Alto / m2Bajo;
  return {
    precio: m2 * q.area, bajo: m2Bajo * q.area, alto: m2Alto * q.area,
    precioM2: m2, comparables: comps, kmMediana, dispersion,
    confianza: confianza(comps.length, kmMediana, dispersion),
  };
}

/** alta: comparables cerca y de precio parejo; baja: lejos o muy dispares. */
export function confianza(n, kmMediana, dispersion) {
  if (n >= 8 && kmMediana <= 1.5 && dispersion <= 1.35) return "alta";
  if (n >= 5 && kmMediana <= 3 && dispersion <= 1.7) return "media";
  return "baja";
}

/** Precio pedido frente a la estimación: por debajo del rango, en rango o por encima. */
export function veredicto(est, pedido) {
  if (!est || !(pedido > 0)) return null;
  const pct = 100 * (pedido / est.precio - 1);
  const nivel = pedido < est.bajo ? "bajo" : pedido > est.alto ? "alto" : "rango";
  return { pct, nivel };
}

/** El aviso como consulta: para evaluar un inmueble publicado. */
export const consultaDe = p => ({
  propId: p.prop_id,
  lat: p.latitud, lon: p.longitud, distrito: p.distrito, area: p.area_m2, dorm: p.num_dorm ?? 0,
  banos: p.num_banios ?? 0, estac: p.num_estac ?? 0, antig: p.antiguedad_anios ?? null, pedido: p.precio_pen ?? null,
});

/**
 * Error típico del método: se estima cada aviso con los demás (sin él) y se mide cuánto se equivoca.
 * Devuelve la mediana del error absoluto en % y cuántos avisos se probaron (una muestra fija de hasta `max`).
 */
export function errorTipico(props, max = 400) {
  const ok = props.filter(sirve);
  if (ok.length < 20) return null;
  const paso = Math.max(1, Math.floor(ok.length / max));
  const errores = [];
  for (let i = 0; i < ok.length; i += paso) {
    const p = ok[i];
    const est = estimar(ok, consultaDe(p), { excluir: p.prop_id });
    if (est) errores.push(Math.abs(est.precio / p.precio_pen - 1));
  }
  errores.sort((a, b) => a - b);
  const dentro = errores.filter(e => e <= 0.2).length;
  return { mediana: 100 * errores[Math.floor(errores.length / 2)], dentro20: 100 * dentro / errores.length, n: errores.length };
}

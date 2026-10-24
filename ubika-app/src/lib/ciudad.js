/**
 * ciudad.js · la ciudad como referencia: grilla de 350 m (capas_grilla), distritos y población.
 *
 * Todas las variables del mapa se calculan sobre la MISMA grilla (escala barrio) y se resumen por
 * distrito (escala distrito), así se ven siempre con el mismo formato.
 *
 * Por habitante: la población del distrito (censo 2017) se reparte por igual entre sus celdas
 * urbanas; lo que hay a 500 m de una celda (denuncias, m² de parque) se divide entre la gente que
 * vive en ese mismo círculo de 500 m. Es una estimación, pero mide lo mismo que las tasas
 * oficiales por distrito y a una escala más fina.
 *
 * Calidad de vida (0–10): promedio ponderado de la posición de cada componente frente a toda Lima.
 * Seguridad = mitad denuncias a 500 m, mitad homicidios del distrito (ver seguridadIx en scoring.js).
 */
import { fmt, indiceCrimen, seguridadIx } from "./scoring.js";

/** Componentes del entorno de un inmueble (ficha, comparador, calidad de vida). */
export const CAPAS = {
  seguridad: {
    l: "Seguridad", menorEsMejor: true, peso: 0.25,
    texto: v => (v == null ? "—" : `${fmt(v)} por 10 mil hab.`),
    corto: v => (v == null ? "—" : `${fmt(v)} /10 mil`),
  },
  transporte: {
    l: "Transporte", menorEsMejor: true, peso: 0.15,
    texto: v => (v == null ? "—" : v <= 2400 ? `${Math.max(1, Math.round(v / 80))} min a pie` : `${(v / 1000).toFixed(1)} km`),
  },
  servicios: {
    l: "Servicios", menorEsMejor: false, peso: 0.15,
    texto: v => (v == null ? "—" : `${fmt(v)} a 500 m`),
  },
  verde: {
    l: "Áreas verdes", menorEsMejor: false, peso: 0.15,
    texto: v => (v == null ? "—" : `${v < 10 ? v.toFixed(1) : fmt(v)} m² por hab.`),
    corto: v => (v == null ? "—" : `${v < 10 ? v.toFixed(1) : fmt(v)} m²/hab`),
  },
  barrio: {
    l: "Comercio", menorEsMejor: false, peso: 0.15,
    texto: v => (v == null ? "—" : `${fmt(v)} locales a 500 m`),
    corto: v => (v == null ? "—" : `${fmt(v)} locales`),
  },
  ruido: {
    l: "Tranquilidad", menorEsMejor: true, peso: 0.15,
    texto: v => (v == null ? "—" : `${Math.round(v)} dB estimados`),
    corto: v => (v == null ? "—" : `${Math.round(v)} dB`),
  },
};
export const CAPAS_KEYS = Object.keys(CAPAS);

/* ── Territorio: a qué distrito cae cada celda y cuánta gente vive en ella ───────────────── */

// Celdas de la grilla dentro de un círculo de 500 m: área del círculo / área de un hexágono de 350 m
export const CELDAS_500M = (Math.PI * 0.5 ** 2) / ((Math.sqrt(3) / 2) * 0.35 ** 2);

function dentroDe(x, y, poligono) {          // poligono = [anillo, huecos…]; regla par-impar
  let dentro = false;
  for (const anillo of poligono) {
    for (let i = 0, j = anillo.length - 1; i < anillo.length; j = i++) {
      const [xi, yi] = anillo[i], [xj, yj] = anillo[j];
      if ((yi > y) !== (yj > y) && x < ((xj - xi) * (y - yi)) / (yj - yi) + xi) dentro = !dentro;
    }
  }
  return dentro;
}

/**
 * { dist: [slug|null por celda], popCelda: Map slug → habitantes por celda,
 *   hom: Map slug → homicidios por 100 mil, longevidad: Map slug → edad promedio al morir (causas naturales) }
 */
export function territorio(grilla, limites, crimenDist) {
  if (!grilla?.celdas?.length || !limites?.features) return null;
  const feats = limites.features.map(f => {
    let x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity;
    for (const pol of f.geometry.coordinates) for (const [x, y] of pol[0]) {
      x0 = Math.min(x0, x); y0 = Math.min(y0, y); x1 = Math.max(x1, x); y1 = Math.max(y1, y);
    }
    return { d: f.properties.distrito, polys: f.geometry.coordinates, caja: [x0, y0, x1, y1] };
  });
  const dist = grilla.celdas.map(([lat, lon]) => {
    for (const f of feats) {
      const [x0, y0, x1, y1] = f.caja;
      if (lon < x0 || lon > x1 || lat < y0 || lat > y1) continue;
      if (f.polys.some(p => dentroDe(lon, lat, p))) return f.d;
    }
    return null;
  });
  const n = new Map();
  for (const d of dist) if (d) n.set(d, (n.get(d) || 0) + 1);
  const popCelda = new Map();
  for (const [d, k] of n) {
    const pob = crimenDist?.get(d)?.poblacion;
    if (pob) popCelda.set(d, pob / k);
  }
  const hom = new Map(), longevidad = new Map();
  for (const [d, r] of crimenDist || []) {
    if (r.tasa_homicidios_100k != null) hom.set(d, r.tasa_homicidios_100k);
    if (r.edad_promedio_natural != null) longevidad.set(d, r.edad_promedio_natural);
  }
  return { dist, popCelda, hom, longevidad };
}

/** Cantidad a 500 m → por habitante del círculo de 500 m (× escala). */
const porHab = (cantidad, popCelda, escala = 1) =>
  cantidad == null || !popCelda ? null : (escala * cantidad) / (popCelda * CELDAS_500M);
export const tasa10k = (denuncias, popCelda) => porHab(denuncias, popCelda, 1e4);

/* ── Celda más cercana a un punto (para los componentes que solo existen en la grilla) ──── */

const BIN = 0.01, M_LAT = 110_574, M_LON = 108_900;
function indexar(celdas) {
  const bins = new Map();
  celdas.forEach((c, i) => {
    const k = `${Math.floor(c[0] / BIN)},${Math.floor(c[1] / BIN)}`;
    (bins.get(k) || bins.set(k, []).get(k)).push(i);
  });
  return bins;
}
function celdaCercana(ref, lat, lon) {
  const bi = Math.floor(lat / BIN), bj = Math.floor(lon / BIN);
  let mejor = -1, dmin = 400 ** 2;                     // a más de 400 m no hay celda urbana
  for (let di = -1; di <= 1; di++) for (let dj = -1; dj <= 1; dj++) {
    for (const i of ref.bins.get(`${bi + di},${bj + dj}`) || []) {
      const c = ref.base[i], dy = (c[0] - lat) * M_LAT, dx = (c[1] - lon) * M_LON, d2 = dx * dx + dy * dy;
      if (d2 < dmin) { dmin = d2; mejor = i; }
    }
  }
  return mejor;
}

/* ── Referencia para ubicar un inmueble frente a Lima ────────────────────────────────────── */

function cota(arr, v, estricta) {          // primer índice con arr[i] > v (estricta) o >= v
  let lo = 0, hi = arr.length;
  while (lo < hi) {
    const m = (lo + hi) >> 1;
    if (estricta ? arr[m] <= v : arr[m] < v) lo = m + 1; else hi = m;
  }
  return lo;
}
/** Posición 0–1 de `v` dentro de `arr` ordenado (1 = mejor que todas). */
function rango(arr, v, menorEsMejor) {
  if (!arr?.length || v == null || Number.isNaN(v)) return null;
  const menores = cota(arr, v, false), iguales = cota(arr, v, true) - menores;
  const peores = menorEsMejor ? arr.length - menores - iguales : menores;
  return (peores + iguales / 2) / arr.length;
}
const ordenar = vals => Float64Array.from(vals.filter(v => v != null && !Number.isNaN(v))).sort();

/** Promedio ponderado (0–10) de los componentes con dato; los que faltan reparten su peso. */
export function calidadDe(ix) {
  if (!ix) return null;
  let s = 0, w = 0;
  for (const k of CAPAS_KEYS) if (ix[k] != null) { s += CAPAS[k].peso * ix[k]; w += CAPAS[k].peso; }
  return w ? (10 * s) / w : null;
}

/**
 * Valores de cada componente en cada celda (`valores[k][i]`), su versión ordenada para comparar,
 * la calidad de vida de cada celda y el índice para buscar la celda de un punto.
 */
export function referencia(grillas, terr) {
  const base = grillas.seguridad?.celdas;
  if (!base) return {};
  const ref = { base, bins: indexar(base), terr, valores: {}, orden: {} };
  const deGrilla = k => {
    const g = grillas[k]?.celdas;
    return g && g.length === base.length ? g.map(c => c[3]) : null;
  };
  const pop = i => terr?.popCelda.get(terr.dist[i]);
  const seg = deGrilla("seguridad"), verde = deGrilla("verde");
  ref.valores = {
    seguridad: terr ? seg.map((v, i) => tasa10k(v, pop(i))) : null,
    transporte: deGrilla("transporte"),
    servicios: deGrilla("servicios"),
    verde: verde && terr ? verde.map((v, i) => porHab(v, pop(i))) : null,
    barrio: deGrilla("barrio"),
    ruido: deGrilla("ruido"),
  };
  ref.denuncias = seg;
  // Homicidios por 100 mil del distrito de cada celda (mismo valor en todo el distrito)
  ref.valores.homicidios = terr?.hom?.size ? terr.dist.map(d => terr.hom.get(d) ?? null) : null;
  // Edad promedio al morir por causas naturales del distrito de cada celda (solo para el mapa, no entra en la calidad de vida)
  ref.valores.longevidad = terr?.longevidad?.size ? terr.dist.map(d => terr.longevidad.get(d) ?? null) : null;
  for (const k of [...CAPAS_KEYS, "homicidios"]) if (ref.valores[k]) ref.orden[k] = ordenar(ref.valores[k]);
  // Calidad de vida de cada celda, con la misma fórmula que la de un inmueble.
  // De paso, el índice de crimen de la celda (capa Crimen): misma regla que la seguridad, al revés y de 0 a 10.
  ref.valores.crimen = new Array(base.length).fill(null);
  ref.valores.calidad = base.map((_, i) => {
    const ix = {};
    for (const k of CAPAS_KEYS) ix[k] = ref.valores[k] ? rango(ref.orden[k], ref.valores[k][i], CAPAS[k].menorEsMejor) : null;
    const posHom = rango(ref.orden.homicidios, ref.valores.homicidios?.[i], true);
    ref.valores.crimen[i] = indiceCrimen(ix.seguridad, posHom);
    ix.seguridad = seguridadIx(ix.seguridad, posHom);
    return calidadDe(ix);
  });
  ref.orden.calidad = ordenar(ref.valores.calidad);
  return ref;
}

/**
 * Entorno de un inmueble frente a Lima: { seguridad, transporte, …: 0–1, val: valores reales, calidad: 0–10 }.
 * seguridad combina denuncias (o.denuncias) y homicidios del distrito (o.homicidios, val.homicidios).
 * Seguridad, transporte y servicios salen de sus propios conteos a 500 m; verde, comercio y ruido,
 * de la celda de la grilla donde está.
 */
export function frenteCiudad(ref, p) {
  const o = { val: {} };
  if (!ref?.base) return o;
  const i = celdaCercana(ref, p.latitud, p.longitud);
  const popP = ref.terr?.popCelda.get(p.distrito);
  const propios = {
    seguridad: tasa10k(p.n_delitos_12m, popP),
    transporte: p.dist_transporte_m,
    servicios: (p.n_colegios ?? 0) + (p.n_salud ?? 0) + (p.n_comisarias ?? 0) + (p.n_malls ?? 0),
  };
  for (const k of CAPAS_KEYS) {
    const v = k in propios ? propios[k] : i >= 0 ? ref.valores[k]?.[i] ?? null : null;
    o.val[k] = v;
    o[k] = ref.orden[k] ? rango(ref.orden[k], v, CAPAS[k].menorEsMejor) : null;
  }
  o.tasa = propios.seguridad;
  o.val.homicidios = ref.terr?.hom?.get(p.distrito) ?? null;
  o.denuncias = o.seguridad;
  o.homicidios = ref.orden.homicidios ? rango(ref.orden.homicidios, o.val.homicidios, true) : null;
  o.seguridad = seguridadIx(o.denuncias, o.homicidios);
  o.calidad = calidadDe(o);
  o.calidadPos = o.calidad == null ? null : rango(ref.orden.calidad, o.calidad, false);
  return o;
}

export const pct = x => `${Math.round(x * 100)} %`;

/**
 * scoring.js
 * Computes the composite opportunity score from weights and property features.
 * Works with both real Neon data and mock data.
 */

export const DEFAULT_WEIGHTS = { seg: 7, trn: 6, pre: 8, srv: 5, esp: 5, val: 4 };

/**
 * Normalizes a value between 0 and 1 given a min/max range.
 */
export function norm(v, mn, mx) {
  if (mx === mn) return 0.5;
  return Math.max(0, Math.min(1, (v - mn) / (mx - mn)));
}

/**
 * Computes opportunity score for a property.
 * Accepts both real data (score_ubicacion + raw fields) and mock data (_seg, _trn, etc.)
 */
export function computeScore(prop, weights, bounds) {
  const tot = Object.values(weights).reduce((a, b) => a + b, 0) || 1;

  // Real data path — use pre-computed score_ubicacion + individual fields
  let seg_s, trn_s, srv_s, esp_s, val_s;

  if (prop._seg !== undefined) {
    // Mock data has pre-normalized scores
    seg_s = prop._seg;
    trn_s = prop._trn;
    srv_s = prop._srv;
    esp_s = prop._esp;
    val_s = prop._val;
  } else {
    // Real data — normalize from raw proximity counts
    seg_s = prop.num_delitos_aprox != null
      ? 1 - norm(prop.num_delitos_aprox, bounds.minDelitos, bounds.maxDelitos) : 0.5;
    trn_s = norm(
      (prop.num_tren_est_aprox || 0) + (prop.num_metro_est_aprox || 0),
      0, bounds.maxTransporte
    );
    srv_s = norm(
      (prop.num_colegios_aprox || 0) + (prop.num_hospitales_aprox || 0) + (prop.num_comisarias_aprox || 0),
      0, bounds.maxServicios
    );
    esp_s = norm(prop.area_m2 || 0, bounds.minArea, bounds.maxArea);
    val_s = prop.score_ubicacion != null
      ? norm(prop.score_ubicacion, 0, 1) : 0.5;
  }

  const pre_s = prop.precio_pen != null
    ? 1 - norm(prop.precio_pen, bounds.minPrecio, bounds.maxPrecio) : 0.5;

  return (
    weights.seg * seg_s +
    weights.trn * trn_s +
    weights.pre * pre_s +
    weights.srv * srv_s +
    weights.esp * esp_s +
    weights.val * val_s
  ) / tot;
}

/**
 * Computes per-field bounds from a property array.
 */
export function computeBounds(props) {
  if (!props.length) return { minPrecio:500, maxPrecio:15000, minArea:20, maxArea:300,
    minDelitos:0, maxDelitos:200, maxTransporte:6, maxServicios:20 };
  return {
    minPrecio:  Math.min(...props.map(p => p.precio_pen || 99999)),
    maxPrecio:  Math.max(...props.map(p => p.precio_pen || 0)),
    minArea:    Math.min(...props.map(p => p.area_m2    || 999)),
    maxArea:    Math.max(...props.map(p => p.area_m2    || 0)),
    minDelitos: 0,
    maxDelitos: Math.max(...props.map(p => p.num_delitos_aprox || 0), 1),
    maxTransporte: Math.max(...props.map(p => (p.num_tren_est_aprox||0)+(p.num_metro_est_aprox||0)), 1),
    maxServicios:  Math.max(...props.map(p => (p.num_colegios_aprox||0)+(p.num_hospitales_aprox||0)+(p.num_comisarias_aprox||0)), 1),
  };
}

/**
 * Maps a score 0–1 to the Ubika color palette.
 * Returns [R, G, B, A] for Deck.gl.
 */
export function scoreToColor(s, alpha = 210) {
  if (s >= 0.72) return [232, 255,  71, alpha]; // yellow
  if (s >= 0.56) return [ 45, 212, 191, alpha]; // teal
  if (s >= 0.40) return [139, 124, 248, alpha]; // purple
  return              [230,  51,  41, alpha];   // red
}

/**
 * Heatmap weight — brighter = higher score.
 */
export function scoreToWeight(s) {
  return Math.max(0.1, s);
}

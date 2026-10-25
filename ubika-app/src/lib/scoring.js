/**
 * scoring.js
 * Puntaje de oportunidad (prioridades del usuario) y puntaje de entorno.
 *
 * Cada criterio se convierte en un índice 0–1 (1 = mejor) con el percentil del inmueble
 * entre todos los de su operación. Los percentiles no se deforman con un aviso extremo
 * (un penthouse de 1 300 m² no aplasta al resto) y no cambian al filtrar.
 */

export const CRITERIOS = [
  // `max`: lo que prioriza el peso 10, para el extremo derecho de la barra
  { k: "precio",     l: "Precio",     max: "lo más barato",       ayuda: "más barato, incluido el mantenimiento" },
  { k: "espacio",    l: "Espacio",    max: "lo más amplio",       ayuda: "más área, dormitorios, baños y estacionamiento" },
  { k: "antiguedad", l: "Antigüedad", max: "lo más nuevo",        ayuda: "más nuevo" },
  { k: "seguridad",  l: "Seguridad",  max: "lo más seguro",       ayuda: "menos denuncias cerca y menos homicidios en el distrito" },
  { k: "servicios",  l: "Servicios",  max: "más servicios cerca", ayuda: "más colegios, salud, comisarías y comercio a 500 m" },
  { k: "transporte", l: "Transporte", max: "transporte cerca",    ayuda: "más cerca del metro, tren o Metropolitano" },
];

export const PESOS_INICIALES = { precio: 8, espacio: 5, antiguedad: 3, seguridad: 7, servicios: 4, transporte: 6 };

export const SEQ = ["#E3CD52", "#A9BD57", "#6FA055", "#3E7F5C", "#1F5D50", "#10383A"];
export const SEQ_RGB = SEQ.map(hexToRgb);

export function hexToRgb(h) {
  const n = parseInt(h.slice(1), 16);
  return [(n >> 16) & 255, (n >> 8) & 255, n & 255];
}

export const tramo = indice => Math.max(0, Math.min(5, Math.floor(indice * 6)));

/** Percentil (0–1) de cada valor dentro de la lista; empates promediados; null queda null. */
function percentiles(valores) {
  const validos = valores.map((v, i) => [v, i]).filter(([v]) => v != null && !Number.isNaN(v)).sort((a, b) => a[0] - b[0]);
  const out = new Array(valores.length).fill(null);
  const n = validos.length;
  if (!n) return out;
  let i = 0;
  while (i < n) {
    let j = i;
    while (j + 1 < n && validos[j + 1][0] === validos[i][0]) j++;
    const p = n === 1 ? 0.5 : ((i + j) / 2) / (n - 1);
    for (let k = i; k <= j; k++) out[validos[k][1]] = p;
    i = j + 1;
  }
  return out;
}

/**
 * Seguridad 0–1 (1 = más seguro) = mitad denuncias cerca, mitad homicidios del distrito.
 * Las denuncias dependen de cuánto denuncia la gente (en SJL o Ancón se denuncia poco y saldrían
 * "seguros"); los homicidios casi no tienen subregistro (SINADEF, certificados de defunción).
 * Si falta uno, cuenta solo el otro.
 */
export const PESO_HOMICIDIOS = 0.5;

/**
 * Transporte: un paradero de Corredor Complementario cuenta como una estación de Metro o Metropolitano
 * a FACTOR_CORREDOR veces su distancia (más lento y menos frecuente). Igual que calidad_vida.factor_corredor
 * en config.yaml (tests/test_calidad.py lo comprueba). Si falta una distancia, cuenta la otra.
 */
export const FACTOR_CORREDOR = 1.5;
export function transporteEfectivo(masivo, corredor) {
  const c = corredor == null ? null : FACTOR_CORREDOR * corredor;
  if (masivo == null) return c;
  return c == null ? masivo : Math.min(masivo, c);
}
/** El acceso real más cercano según esa regla: { metros, tipo: "estacion" | "corredor" }. */
export function accesoTransporte(masivo, corredor) {
  if (masivo == null && corredor == null) return null;
  const porCorredor = masivo == null || (corredor != null && FACTOR_CORREDOR * corredor < masivo);
  return porCorredor ? { metros: corredor, tipo: "corredor" } : { metros: masivo, tipo: "estacion" };
}
export function seguridadIx(denuncias, homicidios) {
  if (denuncias == null) return homicidios ?? null;
  if (homicidios == null) return denuncias;
  return (1 - PESO_HOMICIDIOS) * denuncias + PESO_HOMICIDIOS * homicidios;
}

/** Índice de crimen 0–10 (10 = peor de Lima) a partir de las posiciones 0–1 de seguridad (1 = más seguro). */
export function indiceCrimen(posDenuncias, posHomicidios) {
  const s = seguridadIx(posDenuncias, posHomicidios);
  return s == null ? null : 10 * (1 - s);
}

/**
 * Índices 0–1 (1 = mejor) por inmueble. Devuelve un Map prop_id → { precio, espacio, … }.
 * crimenDist: Map distrito → fila de /api/crimen-distritos (para los homicidios del distrito).
 */
export function calcularIndices(props, crimenDist) {
  const col = f => percentiles(props.map(f));
  const precio = col(p => (p.precio_pen ?? NaN) + (p.mantenimiento_pen ?? 0));
  const area = col(p => p.area_m2);
  const dorm = col(p => p.num_dorm ?? 0);
  const banos = col(p => p.num_banios ?? 0);
  const estac = col(p => p.num_estac ?? 0);
  const antig = col(p => p.antiguedad_anios);
  const delitos = col(p => p.n_delitos_12m);
  const homicidios = col(p => crimenDist?.get(p.distrito)?.tasa_homicidios_100k ?? null);
  const servicios = col(p => (p.n_colegios ?? 0) + (p.n_salud ?? 0) + (p.n_comisarias ?? 0) + (p.n_malls ?? 0));
  const transporte = col(p => transporteEfectivo(p.dist_transporte_m, p.dist_corredor_m));
  const inv = v => (v == null ? null : 1 - v);

  const m = new Map();
  props.forEach((p, i) => m.set(p.prop_id, {
    precio: inv(precio[i]),
    espacio: area[i] == null ? null : 0.6 * area[i] + 0.2 * dorm[i] + 0.1 * banos[i] + 0.1 * estac[i],
    antiguedad: inv(antig[i]),
    seguridad: seguridadIx(inv(delitos[i]), inv(homicidios[i])),
    servicios: servicios[i],
    transporte: inv(transporte[i]),
  }));
  return m;
}

/** Puntaje de oportunidad 0–1. Los criterios sin dato no cuentan (sus pesos se reparten). */
export function puntaje(ix, pesos) {
  if (!ix) return 0;
  let suma = 0, total = 0;
  for (const { k } of CRITERIOS) {
    if (ix[k] == null || !pesos[k]) continue;
    suma += pesos[k] * ix[k];
    total += pesos[k];
  }
  return total ? suma / total : 0;
}

/** Calidad de vida 0–10 (se calcula en ciudad.js con los seis componentes del entorno). */
export const puntajeEntorno = ix => ix?.calidad ?? null;

export const fmt = n => (n == null || Number.isNaN(n)) ? "—" : Math.round(n).toLocaleString("en-US").replace(/,/g, " ");
export const soles = n => `S/ ${fmt(n)}`;
export const minutos = m => (m == null ? "—" : `${m} min`);

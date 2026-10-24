/**
 * variables.js · lo que se puede pintar en el mapa, siempre con el mismo formato.
 *
 * Dos escalas para todas las variables:
 *  - barrio:   hexágonos de 350 m (la grilla de capas_grilla)
 *  - distrito: los 50 distritos de Lima y Callao
 * Regla de color: más oscuro = más de lo que dice el título. Crimen usa la rampa cálida (alerta);
 * el resto, la secuencial verde de la marca.
 */
import { SEQ, fmt } from "./scoring.js";
import { tasa10k } from "./ciudad.js";

export const CALIENTE = ["#FFE8B3", "#FDCB6E", "#FEB722", "#F0931E", "#E07A1F", "#B4401A"];
// Azul para la longevidad (salud de la población): no se confunde con la verde de calidad ni con la cálida de crimen
export const AZUL = ["#E3EEF9", "#BBD5EF", "#8CB6E0", "#5A91CB", "#2F6BAE", "#164581"];
const IDW_RADIO_M = 1500;

const metros = v => (v == null ? "—" : v < 1000 ? `${Math.round(v / 10) * 10} m` : `${(v / 1000).toFixed(1)} km`);

export const VARIABLES = {
  calidad: {
    l: "Calidad de vida", titulo: "Calidad de vida", paleta: SEQ, bajo: "peor calidad", alto: "mejor calidad",
    unidad: "Puntaje 0–10: seguridad, transporte, servicios, áreas verdes, comercio y tranquilidad",
    f: v => v.toFixed(1), sufijo: " /10",
    nota: {
      barrio: "Cada componente se mide frente a toda Lima; seguridad pesa 25 % y el resto 15 % cada uno.",
      distrito: "Mediana de las celdas del distrito.",
    },
  },
  crimen: {
    l: "Crimen", titulo: "Denuncias por habitante", paleta: CALIENTE, bajo: "menos denuncias", alto: "más denuncias",
    unidad: "Denuncias de robo y violencia en 12 meses por cada 10 mil habitantes",
    f: v => fmt(v), sufijo: " por 10 mil hab.",
    nota: {
      barrio: "Estimado: denuncias a 500 m entre la población del distrito repartida en sus celdas (censo 2017). Mide cuánto se denuncia: donde la gente denuncia poco, sale más baja.",
      distrito: "Población del censo 2017 (INEI). En distritos comerciales entra más gente de la que vive ahí y su tasa sale alta; donde se denuncia poco, sale baja.",
    },
  },
  longevidad: {
    l: "Longevidad", titulo: "Edad al morir", paleta: AZUL, bajo: "mueren más jóvenes", alto: "mueren más longevos",
    unidad: "Edad promedio al morir por causas naturales, por distrito de residencia",
    f: v => v.toFixed(1), sufijo: " años",
    nota: {
      barrio: "Dato por distrito: todas sus celdas tienen el mismo valor. SINADEF (MINSA), promedio de 2019, 2022 y 2023. También refleja la edad de la población: donde vive más gente mayor, sale más alta.",
      distrito: "SINADEF (MINSA), muertes no violentas, promedio de 2019, 2022 y 2023. También refleja la edad de la población: donde vive más gente mayor, sale más alta.",
    },
  },
  homicidios: {
    l: "Homicidios", titulo: "Homicidios por habitante", paleta: CALIENTE, bajo: "menos homicidios", alto: "más homicidios",
    unidad: "Homicidios al año por cada 100 mil habitantes, por distrito de residencia de la víctima",
    f: v => v.toFixed(1), sufijo: " por 100 mil hab.",
    nota: {
      barrio: "Dato por distrito: todas sus celdas tienen el mismo valor. SINADEF (MINSA), promedio de 2019, 2022 y 2023.",
      distrito: "SINADEF (MINSA): certificados de defunción, casi sin subregistro. Promedio de 2019, 2022 y 2023; población del censo 2017.",
    },
  },
  precio: {
    l: "Precio m²", titulo: "Precio por m²", paleta: SEQ, bajo: "más barato", alto: "más caro",
    unidad: "Soles por m², precio publicado",
    f: v => `S/ ${fmt(v)}`, sufijo: " por m²",
    nota: {
      barrio: "Estimado con los avisos a menos de 1.5 km; sin color donde no hay avisos cerca.",
      distrito: "Mediana de los avisos del distrito; sin color con menos de 3 avisos.",
    },
  },
  transporte: {
    l: "Transporte", titulo: "Cercanía a transporte", paleta: SEQ, bajo: "lejos", alto: "cerca", invertido: true,
    unidad: "Kilómetros a la estación de metro, tren o Metropolitano más cercana",
    f: metros, corto: v => (v / 1000).toFixed(1), sufijo: " a la estación",
    nota: { barrio: "Distancia en línea recta.", distrito: "Mediana de las celdas del distrito." },
  },
  servicios: {
    l: "Servicios", titulo: "Servicios cerca", paleta: SEQ, bajo: "pocos", alto: "muchos",
    unidad: "Colegios, salud, comisarías y comercio a 500 m",
    f: v => fmt(v), sufijo: " a 500 m",
    nota: { barrio: "Conteo a 500 m de cada celda.", distrito: "Mediana de las celdas del distrito." },
  },
  verde: {
    l: "Áreas verdes", titulo: "Áreas verdes por habitante", paleta: SEQ, bajo: "menos", alto: "más",
    unidad: "m² de parque a 500 m por cada habitante del entorno (la OMS recomienda al menos 9)",
    f: v => (v < 10 ? v.toFixed(1) : fmt(v)), sufijo: " m² por hab.",
    nota: {
      barrio: "Parques de OpenStreetMap de más de 200 m²; población del censo 2017 repartida en las celdas.",
      distrito: "Mediana de las celdas del distrito.",
    },
  },
  barrio: {
    l: "Comercio", titulo: "Comercio de barrio", paleta: SEQ, bajo: "poco", alto: "mucho",
    unidad: "Mercados, supermercados, farmacias, restaurantes, gimnasios y bancos a 500 m",
    f: v => fmt(v), sufijo: " a 500 m",
    nota: {
      barrio: "Locales registrados en OpenStreetMap; en algunas zonas faltan locales.",
      distrito: "Mediana de las celdas del distrito.",
    },
  },
  ruido: {
    l: "Ruido", titulo: "Ruido de tráfico estimado", paleta: CALIENTE, bajo: "tranquilo", alto: "ruidoso",
    unidad: "Decibeles estimados por cercanía a vías grandes y al aeropuerto (la OMS recomienda menos de 53)",
    f: v => `${Math.round(v)} dB`, corto: v => `${Math.round(v)}`, sufijo: " dB",
    nota: {
      barrio: "Modelo, no medición: Lima no publica mapas de ruido. Cada vía suma según su tipo y la distancia.",
      distrito: "Mediana de las celdas del distrito.",
    },
  },
};
/** Las primeras van como botones en la barra; el resto, en «Más capas». */
export const PRINCIPALES = ["calidad", "crimen", "precio"];
export const VARIABLES_KEYS = Object.keys(VARIABLES);

const mediana = a => {
  const s = a.filter(v => v != null).sort((x, y) => x - y);
  return s.length ? (s.length % 2 ? s[(s.length - 1) / 2] : (s[s.length / 2 - 1] + s[s.length / 2]) / 2) : null;
};

/** Precio por m² estimado en cada celda: promedio de los avisos cercanos, pesado por 1/d². */
function precioCeldas(celdas, props) {
  const avisos = props.filter(p => p.precio_m2_pen);
  return celdas.map(c => {
    let s = 0, w = 0;
    for (const p of avisos) {
      const dy = (p.latitud - c[0]) * 110_574, dx = (p.longitud - c[1]) * 108_900, d2 = dx * dx + dy * dy;
      if (d2 > IDW_RADIO_M ** 2) continue;
      const wi = 1 / Math.max(d2, 150 ** 2);
      s += wi * p.precio_m2_pen; w += wi;
    }
    return w ? s / w : null;
  });
}

/** Valor de la variable en cada celda (mismo orden que la grilla de seguridad). */
export function valoresCeldas(k, { grillas, ciudad, props }) {
  const base = grillas.seguridad?.celdas;
  if (!base) return null;
  if (k === "precio") return precioCeldas(base, props);
  return ciudad?.valores?.[k === "crimen" ? "seguridad" : k] || null;
}

/** Si la variable tiene datos (las capas de OpenStreetMap pueden no estar cargadas todavía). */
export function disponible(k, { ciudad }) {
  if (k === "precio") return true;
  const v = ciudad?.valores?.[k === "crimen" ? "seguridad" : k];
  return !!v && v.some(x => x != null && x > 0);
}

/** Valor por distrito: Map slug → { v, extra } */
export function valoresDistrito(k, { celdas, ciudad, crimenDist, distritos }) {
  const out = new Map();
  if (k === "crimen") {
    for (const [d, r] of crimenDist || []) if (r.tasa_10k != null) out.set(d, { v: r.tasa_10k, r, pequeno: r.poblacion < 10000 });
    return out;
  }
  if (k === "homicidios") {
    for (const [d, r] of crimenDist || []) {
      if (r.tasa_homicidios_100k != null) out.set(d, { v: r.tasa_homicidios_100k, r, pequeno: r.poblacion < 10000 });
    }
    return out;
  }
  if (k === "longevidad") {
    // Con menos de 100 muertes naturales en los 3 años, el promedio es poco confiable (Santa María del Mar, La Punta…)
    for (const [d, r] of crimenDist || []) {
      if (r.edad_promedio_natural != null) out.set(d, { v: r.edad_promedio_natural, r, pequeno: (r.n_naturales ?? 0) < 100 });
    }
    return out;
  }
  if (k === "precio") {
    for (const r of distritos || []) if (r.n_inmuebles >= 3 && r.mediana_precio_m2_pen) out.set(r.distrito, { v: r.mediana_precio_m2_pen, r });
    return out;
  }
  const terr = ciudad?.terr;
  if (!terr || !celdas) return out;
  const grupos = new Map();
  terr.dist.forEach((d, i) => { if (d && celdas[i] != null) (grupos.get(d) || grupos.set(d, []).get(d)).push(celdas[i]); });
  for (const [d, vals] of grupos) out.set(d, { v: mediana(vals) });
  return out;
}

/** 5 cortes por cuantiles → 6 tramos; tramo(v) 0–5 ya orientado a "más oscuro = más del título". */
export function tramos(vals, invertido) {
  const s = vals.filter(v => v != null && !Number.isNaN(v)).sort((a, b) => a - b);
  if (!s.length) return { cortes: [], tramo: () => -1 };
  const q = f => s[Math.min(s.length - 1, Math.floor(f * s.length))];
  const cortes = [1, 2, 3, 4, 5].map(k => q(k / 6));
  const tramo = v => {
    if (v == null || Number.isNaN(v)) return -1;
    const t = cortes.filter(c => v > c).length;
    return invertido ? 5 - t : t;
  };
  return { cortes, tramo };
}

export { tasa10k };

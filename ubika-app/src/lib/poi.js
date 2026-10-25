/**
 * poi.js · categorías de puntos de interés que se dibujan alrededor del inmueble elegido.
 * Cada categoría tiene su emoji (se lee sin leyenda) y un color categórico para el borde
 * (no la escala verde, que mide "mejor o peor").
 */
export const CATEGORIAS = {
  colegio:    { l: "Colegios",   uno: "Colegio",           color: "#3E6FB0", emoji: "🏫", de: ["colegio"] },
  salud:      { l: "Salud",      uno: "Centro de salud",   color: "#C8384F", emoji: "🏥", de: ["salud"] },
  comisaria:  { l: "Comisarías", uno: "Comisaría",         color: "#08332F", emoji: "🚓", de: ["comisaria"] },
  transporte: { l: "Transporte", uno: "Estación o paradero de corredor", color: "#7A4FA3", emoji: "🚇", de: ["metro", "metropolitano", "tren", "corredor"] },
  comercio:   { l: "Comercio",   uno: "Comercio grande",   color: "#D8711C", emoji: "🛍️", de: ["mall"] },
  parque:     { l: "Parques",    uno: "Parque",            color: "#3E8E4A", emoji: "🌳", de: ["parque"] },
  // Comercio de todos los días (OpenStreetMap). Los más numerosos arrancan ocultos para no tapar el mapa.
  mercado:    { l: "Mercados",   uno: "Mercado o súper",   color: "#B5651D", emoji: "🛒", de: ["mercado", "supermercado"] },
  farmacia:   { l: "Farmacias",  uno: "Farmacia",          color: "#2A9D8F", emoji: "💊", de: ["farmacia"] },
  restaurante:{ l: "Restaurantes", uno: "Restaurante o café", color: "#E07A1F", emoji: "🍽️", de: ["restaurante"], oculta: true },
  gimnasio:   { l: "Gimnasios",  uno: "Gimnasio",          color: "#5B5F97", emoji: "🏋️", de: ["gimnasio"], oculta: true },
  banco:      { l: "Bancos",     uno: "Banco",             color: "#4F6D7A", emoji: "🏦", de: ["banco"], oculta: true },
};
export const CATEGORIAS_KEYS = Object.keys(CATEGORIAS);
export const FILTRO_INICIAL = Object.fromEntries(CATEGORIAS_KEYS.map(k => [k, !CATEGORIAS[k].oculta]));

const DE = Object.fromEntries(CATEGORIAS_KEYS.flatMap(k => CATEGORIAS[k].de.map(c => [c, k])));
export const grupoDe = categoria => DE[categoria] || "comercio";

/** Agrupa la respuesta de /api/cerca: { colegio: [...], salud: [...], … } ordenados por distancia. */
export function agrupar(puntos = []) {
  const g = Object.fromEntries(CATEGORIAS_KEYS.map(k => [k, []]));
  for (const p of puntos) g[grupoDe(p.categoria)].push(p);
  return g;
}

export const aPie = m => (m == null ? "—" : m < 1000 ? `${Math.max(1, Math.round(m / 80))} min a pie` : `${(m / 1000).toFixed(1)} km`);
export const titulo = s => (s ? s.toLowerCase().replace(/(^|[\s(/-])\p{L}/gu, c => c.toUpperCase()) : "Sin nombre");

/** Ícono del mapa: emoji sobre círculo blanco con borde del color de la categoría (se dibuja una vez). */
const iconos = {};
export function icono(k) {
  if (iconos[k]) return iconos[k];
  const t = 72, c = document.createElement("canvas");
  c.width = c.height = t;
  const g = c.getContext("2d");
  g.beginPath(); g.arc(t / 2, t / 2, t / 2 - 4, 0, 2 * Math.PI);
  g.fillStyle = "#FFFFFF"; g.fill();
  g.lineWidth = 5; g.strokeStyle = CATEGORIAS[k].color; g.stroke();
  g.font = '36px "Segoe UI Emoji", "Apple Color Emoji", "Noto Color Emoji", sans-serif';
  g.textAlign = "center"; g.textBaseline = "middle";
  g.fillText(CATEGORIAS[k].emoji, t / 2, t / 2 + 3);
  return (iconos[k] = { id: `poi-${k}`, url: c.toDataURL(), width: t, height: t, anchorY: t / 2 });
}

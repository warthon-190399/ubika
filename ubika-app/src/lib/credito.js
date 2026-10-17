/**
 * credito.js · simulador hipotecario (método francés, cuota fija) y "qué puedo comprar".
 *
 * Valores por defecto referenciales; cada banco aplica los suyos:
 *  - TEA 7.69 %: promedio hipotecario en soles de la SBS al 14/09/2026 (vía Gestión).
 *  - Desgravamen ~0.03 % mensual sobre el saldo; seguro del inmueble ~0.025 % mensual de su valor.
 *  - La cuota no debería pasar del 30 % del ingreso neto (los bancos usan entre 30 y 40 %).
 */
export const CREDITO_INICIAL = {
  ingreso: 8000,        // ingreso neto mensual del hogar (S/)
  ahorro: 60000,        // ahorro disponible para la inicial (S/)
  plazo: 20,            // años
  tea: 7.69,            // % anual
  cuotaMaxPct: 30,      // % del ingreso
  inicialMinPct: 10,    // % del precio
  desgravamen: 0.03,    // % mensual sobre el saldo
  seguroInmueble: 0.025 // % mensual sobre el valor
};
export const TEA_FUENTE = { texto: "promedio SBS en soles al 14/09/2026", url: "https://gestion.pe/tu-dinero/finanzas-personales/tasas-de-creditos-hipotecarios-podrian-bajar-que-bancos-ofrecen-los-menores-intereses-noticia/" };

const tem = tea => Math.pow(1 + tea / 100, 1 / 12) - 1;
// Desgravamen como recargo sobre el saldo: se suma a la tasa mensual (aproximación usual)
const tasaMes = c => tem(c.tea) + c.desgravamen / 100;
const factor = (r, n) => (r === 0 ? 1 / n : r / (1 - Math.pow(1 + r, -n)));

/** Cuota mensual total para comprar `precio` poniendo `inicial`. */
export function cuota(precio, inicial, c) {
  const prestamo = Math.max(0, precio - inicial);
  const n = c.plazo * 12;
  const base = prestamo * factor(tasaMes(c), n);
  const seguro = precio * c.seguroInmueble / 100;
  return { prestamo, n, base, seguro, total: base + seguro, intereses: base * n - prestamo };
}

/**
 * Precio máximo que el hogar puede comprar: el menor entre lo que permite la cuota
 * (cuota ≤ cuotaMaxPct del ingreso) y lo que permite la inicial (ahorro ≥ inicialMinPct del precio).
 */
export function capacidad(c) {
  const n = c.plazo * 12, r = tasaMes(c), k = 1 / factor(r, n);   // k = préstamo que paga 1 sol de cuota
  const cuotaMax = c.ingreso * c.cuotaMaxPct / 100;
  const s = c.seguroInmueble / 100, A = c.ahorro;
  // cuota = P/k + s·(P + A) ≤ cuotaMax  →  P ≤ k·(cuotaMax − s·A) / (1 + s·k)
  const prestamoMax = Math.max(0, k * (cuotaMax - s * A) / (1 + s * k));
  const porCuota = prestamoMax + A;
  const porInicial = c.inicialMinPct > 0 ? A / (c.inicialMinPct / 100) : Infinity;
  const precioMax = Math.min(porCuota, porInicial);
  return {
    precioMax, cuotaMax, limita: porInicial < porCuota ? "inicial" : "cuota",
    prestamo: Math.max(0, precioMax - A), ...cuota(precioMax, A, c),
  };
}

/** Qué tan holgada queda la cuota de un inmueble frente al ingreso. */
export function semaforo(total, c) {
  const pct = (100 * total) / c.ingreso;
  return { pct, nivel: pct <= c.cuotaMaxPct ? "ok" : pct <= c.cuotaMaxPct + 10 ? "justo" : "alto" };
}

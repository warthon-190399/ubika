// Pruebas del evaluador por comparables. Correr: npm test
import { test } from "node:test";
import assert from "node:assert/strict";
import { centroDistrito, confianza, consultaDe, errorTipico, estimar, km, percentilPonderado, veredicto } from "../src/lib/evaluador.js";

// Barrio ficticio en Miraflores: 30 depas a S/ 40/m² de alquiler, más 10 lejos (Comas) a S/ 15/m²
const MIRA = [-12.1211, -77.0297], COMAS = [-11.94, -77.05];
const aviso = (id, [lat, lon], area, m2, extra = {}) => ({
  prop_id: id, latitud: lat, longitud: lon, area_m2: area, precio_pen: area * m2, precio_m2_pen: m2,
  num_dorm: 2, num_banios: 2, num_estac: 1, antiguedad_anios: 10, distrito: "miraflores", ...extra,
});
const PROPS = [
  ...Array.from({ length: 30 }, (_, i) =>
    aviso(i + 1, [MIRA[0] + (i % 6) * 0.002, MIRA[1] + Math.floor(i / 6) * 0.002], 70 + (i % 5) * 5, 38 + (i % 5))),
  ...Array.from({ length: 10 }, (_, i) =>
    aviso(100 + i, [COMAS[0] + i * 0.001, COMAS[1]], 80, 15, { distrito: "comas" })),
];
const Q = { lat: MIRA[0] + 0.004, lon: MIRA[1] + 0.004, area: 80, dorm: 2, banos: 2, estac: 1, antig: null };

test("km entre dos puntos de Lima", () => {
  assert.ok(Math.abs(km(-12.12, -77.03, -12.13, -77.03) - 1.113) < 0.01);
  assert.equal(km(...MIRA, ...MIRA), 0);
});

test("percentil ponderado", () => {
  assert.equal(percentilPonderado([[10, 1], [20, 1], [30, 1]], 0.5), 20);
  assert.equal(percentilPonderado([[10, 1], [20, 1], [30, 10]], 0.5), 30);   // el que más pesa manda
  assert.equal(percentilPonderado([], 0.5), null);
});

test("estima con los comparables cercanos, no con los de otro distrito", () => {
  const est = estimar(PROPS, Q);
  assert.equal(est.comparables.length, 12);
  assert.ok(est.comparables.every(c => c.p.distrito === "miraflores"));
  assert.ok(est.precioM2 >= 38 && est.precioM2 <= 42, `precio por m² ${est.precioM2}`);
  assert.ok(Math.abs(est.precio - est.precioM2 * 80) < 1e-9);
  assert.ok(est.bajo <= est.precio && est.precio <= est.alto);
  assert.equal(est.confianza, "alta");
});

test("en Comas estima con los de Comas", () => {
  const est = estimar(PROPS, { ...Q, lat: COMAS[0], lon: COMAS[1] });
  assert.equal(est.precioM2, 15);
  assert.equal(est.precio, 1200);
});

test("no se usa a sí mismo como comparable", () => {
  const p = PROPS[3];
  const est = estimar(PROPS, consultaDe(p), { excluir: p.prop_id });
  assert.ok(est.comparables.every(c => c.p.prop_id !== p.prop_id));
});

test("sin ubicación, sin área o sin avisos no estima", () => {
  assert.equal(estimar(PROPS, { ...Q, lat: null }), null);
  assert.equal(estimar(PROPS, { ...Q, area: 0 }), null);
  assert.equal(estimar(PROPS.slice(0, 2), Q), null);
  assert.equal(estimar([{ ...PROPS[0], precio_pen: null }, PROPS[1], PROPS[2]], Q), null);   // avisos sin precio no sirven
});

test("veredicto del precio pedido", () => {
  const est = { precio: 3000, bajo: 2800, alto: 3300 };
  assert.equal(veredicto(est, 2500).nivel, "bajo");
  assert.equal(veredicto(est, 3000).nivel, "rango");
  assert.equal(veredicto(est, 3600).nivel, "alto");
  assert.ok(Math.abs(veredicto(est, 3600).pct - 20) < 1e-9);
  assert.equal(veredicto(est, null), null);
});

test("confianza", () => {
  assert.equal(confianza(12, 0.8, 1.2), "alta");
  assert.equal(confianza(12, 2.5, 1.2), "media");
  assert.equal(confianza(12, 6, 1.2), "baja");
  assert.equal(confianza(12, 0.8, 2.5), "baja");
});

test("centro de un distrito", () => {
  const c = centroDistrito(PROPS, "comas");
  assert.ok(Math.abs(c.lat - (COMAS[0] + 0.005)) < 0.0011);
  assert.equal(centroDistrito(PROPS, "ate"), null);
});

test("error típico con los propios avisos", () => {
  const e = errorTipico(PROPS);
  assert.equal(e.n, PROPS.length);
  assert.ok(e.mediana < 10, `error mediano ${e.mediana}%`);
  assert.equal(errorTipico(PROPS.slice(0, 5)), null);
});

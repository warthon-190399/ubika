// La app usa el score de calidad de vida guardado en Neon y solo lo calcula si no está. Correr: npm test
import { test } from "node:test";
import assert from "node:assert/strict";
import { CAPAS, CAPAS_KEYS, frenteCiudad, referencia, territorio } from "../src/lib/ciudad.js";

const DIST = new Map([["a", { distrito: "a", poblacion: 20_000, tasa_homicidios_100k: 2, edad_promedio_natural: 78 }]]);
const caja = (x0, y0, x1, y1) => [[[[x0, y0], [x1, y0], [x1, y1], [x0, y1], [x0, y0]]]];
const LIMITES = { features: [{ properties: { distrito: "a" }, geometry: { coordinates: caja(-77.1, -12.1, -76.9, -11.9) } }] };
const SEG = { celdas: [[-12.0, -77.0, 0, 5], [-12.0, -76.99, 0, 50]] };
const grillas = calidad => ({ seguridad: SEG, calidad });

test("los pesos de los 7 componentes suman 1 e incluyen longevidad", () => {
  assert.deepEqual(CAPAS_KEYS, ["seguridad", "longevidad", "transporte", "servicios", "verde", "barrio", "ruido"]);
  assert.ok(Math.abs(CAPAS_KEYS.reduce((s, k) => s + CAPAS[k].peso, 0) - 1) < 1e-9);
});

test("con el score guardado, cada celda usa el de Neon", () => {
  const terr = territorio(SEG, LIMITES, DIST);
  const ref = referencia(grillas({ celdas: [[-12.0, -77.0, 0.81, 8.1], [-12.0, -76.99, 0.42, 4.2]] }), terr);
  assert.equal(ref.calidadGuardada, true);
  assert.deepEqual(ref.valores.calidad, [8.1, 4.2]);
});

test("sin score guardado (o con otra grilla), lo calcula en el navegador", () => {
  const terr = territorio(SEG, LIMITES, DIST);
  for (const cal of [undefined, { celdas: [] }, { celdas: [[-12, -77, 0.5, 5]] }]) {
    const ref = referencia(grillas(cal), terr);
    assert.equal(ref.calidadGuardada, false);
    assert.ok(ref.valores.calidad.every(v => v != null && v >= 0 && v <= 10));
  }
});

test("un inmueble usa su score guardado y la longevidad de su distrito", () => {
  const ref = referencia(grillas(undefined), territorio(SEG, LIMITES, DIST));
  const p = { prop_id: "x", distrito: "a", latitud: -12.0, longitud: -77.0, n_delitos_12m: 3, dist_transporte_m: 400 };
  assert.equal(frenteCiudad(ref, { ...p, calidad_vida: 6.3 }).calidad, 6.3);
  const sin = frenteCiudad(ref, p);
  assert.ok(sin.calidad >= 0 && sin.calidad <= 10);
  assert.equal(sin.val.longevidad, 78);
});

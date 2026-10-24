// Capa de longevidad: edad promedio al morir por causas naturales, por distrito. Correr: npm test
import { test } from "node:test";
import assert from "node:assert/strict";
import { referencia, territorio } from "../src/lib/ciudad.js";
import { VARIABLES, valoresCeldas, valoresDistrito, disponible, AZUL } from "../src/lib/variables.js";

const DIST = new Map([
  ["san isidro", { distrito: "san isidro", poblacion: 60_000, edad_promedio_natural: 79.7, n_naturales: 1590 }],
  ["pucusana", { distrito: "pucusana", poblacion: 15_000, edad_promedio_natural: 62.6, n_naturales: 98 }],
]);
const caja = (x0, y0, x1, y1) => [[[[x0, y0], [x1, y0], [x1, y1], [x0, y1], [x0, y0]]]];
const LIMITES = { features: [
  { properties: { distrito: "san isidro" }, geometry: { coordinates: caja(-77.05, -12.11, -77.02, -12.09) } },
  { properties: { distrito: "pucusana" }, geometry: { coordinates: caja(-76.81, -12.49, -76.78, -12.46) } },
] };
const GRILLA = { celdas: [[-12.10, -77.04, 0, 1], [-12.10, -77.03, 0, 2], [-12.48, -76.80, 0, 3], [-11.0, -76.0, 0, 4]] };

test("cada celda toma la edad al morir de su distrito; fuera de un distrito, sin dato", () => {
  const terr = territorio(GRILLA, LIMITES, DIST);
  assert.equal(terr.longevidad.get("san isidro"), 79.7);
  const ciudad = referencia({ seguridad: GRILLA }, terr);
  assert.deepEqual(ciudad.valores.longevidad, [79.7, 79.7, 62.6, null]);
  assert.deepEqual(valoresCeldas("longevidad", { grillas: { seguridad: GRILLA }, ciudad }), [79.7, 79.7, 62.6, null]);
  assert.equal(disponible("longevidad", { ciudad }), true);
});

test("por distrito: marca como poco confiables los de menos de 100 muertes naturales", () => {
  const m = valoresDistrito("longevidad", { crimenDist: DIST });
  assert.equal(m.get("san isidro").v, 79.7);
  assert.equal(m.get("san isidro").pequeno, false);
  assert.equal(m.get("pucusana").pequeno, true);
});

test("la capa es azul y más oscuro = más longevo", () => {
  assert.equal(VARIABLES.longevidad.paleta, AZUL);
  assert.equal(AZUL.length, 6);
  assert.ok(!VARIABLES.longevidad.invertido);
  assert.equal(VARIABLES.longevidad.f(79.66), "79.7");
});

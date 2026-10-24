// Capa Crimen: índice 0–10, mitad denuncias y mitad homicidios (la misma regla que la seguridad). Correr: npm test
import { test } from "node:test";
import assert from "node:assert/strict";
import { indiceCrimen } from "../src/lib/scoring.js";
import { referencia, territorio } from "../src/lib/ciudad.js";
import { VARIABLES, posicionMenorMejor, valoresCeldas, valoresDistrito } from "../src/lib/variables.js";

test("posicionMenorMejor: 1 = el menor, empates a la mitad, sin dato = null", () => {
  assert.equal(posicionMenorMejor([10, 20, 30, 40], 10), 0.875);
  assert.equal(posicionMenorMejor([10, 20, 30, 40], 40), 0.125);
  assert.equal(posicionMenorMejor([10, 20, null], 20), 0.25);
  assert.equal(posicionMenorMejor([10, 20], null), null);
});

test("indiceCrimen es la seguridad al revés, de 0 a 10", () => {
  assert.equal(indiceCrimen(1, 1), 0);           // lo más seguro de Lima en las dos cosas
  assert.equal(indiceCrimen(0, 0), 10);
  assert.equal(indiceCrimen(0.8, 0.2), 5);       // pocas denuncias pero muchos homicidios: a la mitad
  assert.equal(indiceCrimen(0.6, null), 4);      // sin homicidios, solo cuentan las denuncias
  assert.equal(indiceCrimen(null, null), null);
});

// SJL denuncia poco pero tiene muchos homicidios; San Isidro, al revés; La Victoria, alto en las dos
const DIST = new Map([
  ["sjl", { distrito: "sjl", poblacion: 1_000_000, tasa_10k: 150, tasa_homicidios_100k: 7.6 }],
  ["san isidro", { distrito: "san isidro", poblacion: 60_000, tasa_10k: 440, tasa_homicidios_100k: 1.6 }],
  ["la victoria", { distrito: "la victoria", poblacion: 173_000, tasa_10k: 444, tasa_homicidios_100k: 7.9 }],
  ["la molina", { distrito: "la molina", poblacion: 140_000, tasa_10k: 120, tasa_homicidios_100k: 1.0 }],
]);

test("por distrito: los homicidios suben a SJL y bajan a San Isidro frente a solo denuncias", () => {
  const m = valoresDistrito("crimen", { crimenDist: DIST });
  const v = d => m.get(d).v;
  assert.ok(v("la victoria") > v("sjl") && v("la victoria") > v("san isidro"));   // alto en las dos
  assert.ok(v("la molina") < v("sjl") && v("la molina") < v("san isidro"));      // bajo en las dos
  assert.equal(v("sjl"), v("san isidro"));                                        // cada uno alto en una sola
  assert.equal(m.get("sjl").r.tasa_homicidios_100k, 7.6);                         // la fila va para el tooltip
});

test("por barrio: cada celda usa sus denuncias a 500 m y los homicidios de su distrito", () => {
  const caja = (x0, y0, x1, y1) => [[[[x0, y0], [x1, y0], [x1, y1], [x0, y1], [x0, y0]]]];
  const limites = { features: [
    { properties: { distrito: "sjl" }, geometry: { coordinates: caja(-77.01, -12.01, -76.98, -11.99) } },
    { properties: { distrito: "san isidro" }, geometry: { coordinates: caja(-77.05, -12.11, -77.02, -12.09) } },
  ] };
  // [lat, lon, índice, denuncias a 500 m]: SJL con pocas denuncias, San Isidro con muchas
  const grilla = { celdas: [[-12.00, -77.00, 0, 5], [-12.00, -76.99, 0, 6], [-12.10, -77.04, 0, 50], [-12.10, -77.03, 0, 60]] };
  const ciudad = referencia({ seguridad: grilla }, territorio(grilla, limites, DIST));
  const c = valoresCeldas("crimen", { grillas: { seguridad: grilla }, ciudad });
  assert.equal(c.length, 4);
  assert.ok(c.every(x => x != null && x >= 0 && x <= 10));
  assert.equal(VARIABLES.crimen.f(c[0]), c[0].toFixed(1));
  // Con solo denuncias, SJL sería mucho menos peligroso; con homicidios queda parejo con San Isidro
  assert.ok(Math.abs((c[0] + c[1]) - (c[2] + c[3])) < 1e-9);
});

// Seguridad = mitad denuncias cerca, mitad homicidios del distrito. Correr: npm test
import { test } from "node:test";
import assert from "node:assert/strict";
import { PESO_HOMICIDIOS, calcularIndices, seguridadIx } from "../src/lib/scoring.js";
import { frenteCiudad, referencia, territorio } from "../src/lib/ciudad.js";

test("seguridadIx combina mitad y mitad, y usa el que haya si falta uno", () => {
  assert.equal(PESO_HOMICIDIOS, 0.5);
  assert.equal(seguridadIx(0.8, 0.2), 0.5);
  assert.equal(seguridadIx(0.8, null), 0.8);
  assert.equal(seguridadIx(null, 0.3), 0.3);
  assert.equal(seguridadIx(null, null), null);
});

// "sjl": pocas denuncias pero muchos homicidios; "san isidro": muchas denuncias, pocos homicidios
const CRIMEN = new Map([
  ["sjl", { distrito: "sjl", poblacion: 1_000_000, tasa_10k: 150, tasa_homicidios_100k: 7.6 }],
  ["san isidro", { distrito: "san isidro", poblacion: 60_000, tasa_10k: 440, tasa_homicidios_100k: 1.6 }],
]);
const aviso = (id, distrito, n_delitos_12m) => ({
  prop_id: id, distrito, n_delitos_12m, precio_pen: 3000, area_m2: 80, num_dorm: 2, latitud: -12, longitud: -77,
});

test("calcularIndices: sin homicidios manda la denuncia; con homicidios, SJL deja de salir más seguro", () => {
  const props = [aviso("a", "sjl", 10), aviso("b", "san isidro", 90)];
  const solo = calcularIndices(props);
  assert.ok(solo.get("a").seguridad > solo.get("b").seguridad);        // como antes: menos denuncias = más seguro
  const con = calcularIndices(props, CRIMEN);
  assert.equal(con.get("a").seguridad, 0.5);                           // mejor en denuncias, peor en homicidios
  assert.equal(con.get("b").seguridad, 0.5);
});

test("frenteCiudad: la seguridad del inmueble suma los homicidios de su distrito", () => {
  // Grilla mínima: dos celdas en SJL y dos en San Isidro, [lat, lon, índice, denuncias a 500 m]
  const celdas = [[-12.00, -77.00, 0, 5], [-12.00, -76.99, 0, 6], [-12.10, -77.04, 0, 50], [-12.10, -77.03, 0, 60]];
  const caja = (x0, y0, x1, y1) => [[[[x0, y0], [x1, y0], [x1, y1], [x0, y1], [x0, y0]]]];
  const limites = { features: [
    { properties: { distrito: "sjl" }, geometry: { coordinates: caja(-77.01, -12.01, -76.98, -11.99) } },
    { properties: { distrito: "san isidro" }, geometry: { coordinates: caja(-77.05, -12.11, -77.02, -12.09) } },
  ] };
  const grilla = { celdas };
  const terr = territorio(grilla, limites, CRIMEN);
  assert.equal(terr.hom.get("sjl"), 7.6);
  const ref = referencia({ seguridad: grilla }, terr);
  assert.deepEqual(ref.valores.homicidios, [7.6, 7.6, 1.6, 1.6]);

  const sjl = frenteCiudad(ref, { ...aviso("a", "sjl", 1), latitud: -12.00, longitud: -77.00 });
  assert.equal(sjl.val.homicidios, 7.6);
  assert.ok(sjl.denuncias > 0.5 && sjl.homicidios < 0.5);              // pocas denuncias, muchos homicidios
  assert.equal(sjl.seguridad, 0.5 * sjl.denuncias + 0.5 * sjl.homicidios);
  assert.ok(sjl.seguridad < sjl.denuncias);                            // ya no sale tan seguro como decían las denuncias
});

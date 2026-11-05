import test from "node:test";
import assert from "node:assert/strict";
import { NIVELES_BL, oraculoBL, evaluarSobornoODC } from "../js/core/reglas.mjs";

test("la tabla de niveles cubre BL 1-9 con su pago", () => {
  assert.deepEqual(Object.keys(NIVELES_BL).map(Number), [1, 2, 3, 4, 5, 6, 7, 8, 9]);
  assert.equal(NIVELES_BL[1].pago, "1d10 kcr");
  assert.equal(NIVELES_BL[9].pago, "1d100 Mcr");
});

test("oráculo: ocurre si la tirada sale por debajo del BL", () => {
  assert.equal(oraculoBL(5, 4).ocurre, true);
  assert.equal(oraculoBL(5, 5).ocurre, false);
  assert.equal(oraculoBL(1, 1).ocurre, false);
});

test("soborno: hay que sacar menos que el valor", () => {
  assert.equal(evaluarSobornoODC({ soborno: 73, tiradaD100: 72 }).acepta, true);
  assert.equal(evaluarSobornoODC({ soborno: 73, tiradaD100: 73 }).acepta, false);
});

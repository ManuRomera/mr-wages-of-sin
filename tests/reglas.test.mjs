import test from "node:test";
import assert from "node:assert/strict";
import {
  calcularRecompensaBL,
  oraculoBL,
  evaluarDelitoJugador,
  calcularSentencia,
  evaluarSobornoODC,
  simularDiaInfiernoVerde,
  parsearEstadisticasMosh,
} from "../js/core/reglas.mjs";

test("calcularRecompensaBL calcula pago vivo, muerto y prima para BL 1..10", () => {
  const r1 = calcularRecompensaBL(1, "vivo", 0);
  assert.equal(r1.total, 1000);
  assert.equal(r1.formato, "1kcr");

  const r5 = calcularRecompensaBL(5, "muerto", 20);
  assert.equal(r5.base, 10000);
  assert.equal(r5.prima, 2000);
  assert.equal(r5.total, 12000);
});

test("oraculoBL aplica la regla de decidir según 1d10 <= BL", () => {
  assert.equal(oraculoBL(4, 3).ocurre, true);
  assert.equal(oraculoBL(4, 7).ocurre, false);
});

test("evaluarDelitoJugador identifica si 1d10 <= nivelPrueba y sube el BL", () => {
  const libre = evaluarDelitoJugador({ nivelPrueba: 3, blDelito: 4, tiradaD10: 6, blActual: 0 });
  assert.equal(libre.identificado, false);
  assert.equal(libre.blNuevo, 0);

  const cazado = evaluarDelitoJugador({ nivelPrueba: 5, blDelito: 4, tiradaD10: 4, blActual: 4 });
  assert.equal(cazado.identificado, true);
  assert.equal(cazado.blNuevo, 5);
});

test("calcularSentencia y evaluarSobornoODC aplican las tablas de Castigo y ODC", () => {
  const s = calcularSentencia(6, 3);
  assert.equal(s.tipo, "odc");
  assert.ok(s.aniosODC >= 10);

  const sobOk = evaluarSobornoODC({ umbralSoborno: 48, tiradaD100: 33, bonoOferta: 0 });
  assert.equal(sobOk.exito, true);
  assert.equal(sobOk.critico, true);
});

test("simularDiaInfiernoVerde y parsearEstadisticasMosh procesan encuentros y bloques mosh", () => {
  const dia = simularDiaInfiernoVerde({ dEncuentro: 2, dHora: 8, dFruta: 9 });
  assert.match(dia.franja, /De noche/);
  assert.match(dia.encuentro, /VTOL/);
  assert.match(dia.fruta, /Venenosa/);

  const st = parsearEstadisticasMosh("[C:65 Garras 3d10 DAÑO I:50 PA:5 RD:3 H:4(30)]");
  assert.equal(st.combat, 65);
  assert.equal(st.instinct, 50);
  assert.equal(st.armor, 5);
  assert.equal(st.dr, 3);
  assert.equal(st.wounds, 4);
  assert.equal(st.health, 30);
  assert.equal(st.arma, "Garras");
  assert.equal(st.danio, "3d10");
});

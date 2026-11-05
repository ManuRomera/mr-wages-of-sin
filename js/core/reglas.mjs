/**
 * Reglas de Wages of Sin (MRPG-M6) que el módulo automatiza. Todas salen del libro:
 *  - Nivel de Recompensa y pago (págs. 12-13).
 *  - Regla del Guardián: «Si no sabes cómo resolver o decidir algo, usa el Nivel de Recompensa. ¿La tirada sale por debajo? Eso ocurre.» (pág. 16).
 *  - Sobornos a la ODC: hay que sacar menos que el valor de Soborno del funcionario en d100 (pág. 298).
 * Sin dependencias de Foundry para poder probarse con `node --test`.
 */
const n = (v, d = 0) => (Number.isFinite(Number(v)) ? Number(v) : d);
const acota = (v, min, max) => Math.min(max, Math.max(min, v));

/** Tabla «Nivel y pago» (págs. 12-13). */
export const NIVELES_BL = {
  1: { bl: 1, tipo: "Órdenes mínimas", pago: "1d10 kcr", nota: "Minucias para organizaciones. Graves para civiles desesperados." },
  2: { bl: 2, tipo: "Órdenes menores", pago: "1d5 × 10 kcr", nota: "Órdenes contra quienes no quieren ser hallados." },
  3: { bl: 3, tipo: "Órdenes serias", pago: "1d10 × 10 kcr", nota: "Con experiencia o recursos y dispuestos a usarlos." },
  4: { bl: 4, tipo: "Órdenes peligrosas", pago: "1d5 × 100 kcr", nota: "Objetivos con experiencia y recursos." },
  5: { bl: 5, tipo: "Órdenes mayores", pago: "1d10 × 100 kcr", nota: "Objetivos poderosos o ajenos al orden social habitual." },
  6: { bl: 6, tipo: "Órdenes operativas", pago: "1d5 Mcr", nota: "Protegidos por la violencia organizada." },
  7: { bl: 7, tipo: "Órdenes estratégicas", pago: "1d10 Mcr", nota: "Pilares de organizaciones o quienes ejercen un poder atroz de forma directa." },
  8: { bl: 8, tipo: "Órdenes legendarias", pago: "2d10 Mcr", nota: "Nombres célebres o figuras en los núcleos secretos del poder." },
  9: { bl: 9, tipo: "Órdenes apocalípticas", pago: "1d100 Mcr", nota: "Nombres susurrados." },
};

/** Oráculo del Nivel de Recompensa: ocurre si la tirada de 1d10 sale por debajo del BL. */
export function oraculoBL(bl, tiradaD10) {
  const nivel = acota(Math.round(n(bl, 1)), 1, 9);
  const d = acota(Math.round(n(tiradaD10, 5)), 1, 10);
  const ocurre = d < nivel;
  return {
    bl: nivel, tirada: d, ocurre,
    resumen: ocurre ? `Sale ${d}, por debajo de BL:${nivel}: ocurre.` : `Sale ${d}, no por debajo de BL:${nivel}: no ocurre.`,
  };
}

/** Soborno a un funcionario de la ODC: sacar menos que su valor de Soborno en d100. */
export function evaluarSobornoODC({ soborno = 50, tiradaD100 = 50 } = {}) {
  const valor = acota(Math.round(n(soborno, 50)), 1, 100);
  const d = acota(Math.round(n(tiradaD100, 50)), 1, 100);
  const acepta = d < valor;
  return { soborno: valor, tirada: d, acepta, resumen: acepta ? `Sale ${d}, menos que ${valor}: acepta el soborno.` : `Sale ${d}, no menos que ${valor}: rechaza el soborno.` };
}

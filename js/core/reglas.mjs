/**
 * Núcleo puro de reglas de Wages of Sin (MRPG-M6) para Mothership 1e.
 * Sin dependencias de Foundry (`game`, `canvas`, `Hooks`) para poder probarse con `node --test`.
 */

const n = (v, d = 0) => (Number.isFinite(Number(v)) ? Number(v) : d);
const acota = (v, min, max) => Math.min(max, Math.max(min, v));

/** Tabla base de Nivel de Busca (BL 1–10) del manual (págs. 12–13 y 225). */
export const NIVELES_BL = {
  1: { bl: 1, vivo: 1000, muerto: 500, etiqueta: "BL:1 · Delito menor / Deuda", cazadorMax: 1 },
  2: { bl: 2, vivo: 2500, muerto: 1000, etiqueta: "BL:2 · Delito local / Fuga leve", cazadorMax: 2 },
  3: { bl: 3, vivo: 5000, muerto: 2500, etiqueta: "BL:3 · Delito grave / Contrabando", cazadorMax: 4 },
  4: { bl: 4, vivo: 10000, muerto: 5000, etiqueta: "BL:4 · Crimen organizado / Asalto", cazadorMax: 5 },
  5: { bl: 5, vivo: 25000, muerto: 10000, etiqueta: "BL:5 · Asesinato / Sabotaje mayor", cazadorMax: 6 },
  6: { bl: 6, vivo: 50000, muerto: 25000, etiqueta: "BL:6 · Terrorismo / Secuestro VIP", cazadorMax: 8 },
  7: { bl: 7, vivo: 100000, muerto: 50000, etiqueta: "BL:7 · Amenaza corporativa / Masacre", cazadorMax: 9 },
  8: { bl: 8, vivo: 250000, muerto: 100000, etiqueta: "BL:8 · Rebelión / Arma biológica", cazadorMax: 10 },
  9: { bl: 9, vivo: 500000, muerto: 250000, etiqueta: "BL:9 · Enemigo del sector / IA hostil", cazadorMax: 10 },
  10: { bl: 10, vivo: 1000000, muerto: 500000, etiqueta: "BL:10 · Prioridad absoluta de extinción", cazadorMax: 10 },
};

/** Pruebas dejadas tras un delito de jugadores (pág. 224). */
export const PRUEBAS_DELITO = [
  { nivel: 1, nombre: "Rumores o sospecha circunstancial", blBase: 1 },
  { nivel: 2, nombre: "Testigos indirectos o rastro borroso", blBase: 2 },
  { nivel: 3, nombre: "Testigos oculares directos", blBase: 3 },
  { nivel: 4, nombre: "Grabación de cámaras o sensores", blBase: 4 },
  { nivel: 5, nombre: "Pruebas forenses (ADN, sangre, huellas)", blBase: 5 },
  { nivel: 6, nombre: "Rastro financiero o registro de atraque", blBase: 6 },
  { nivel: 7, nombre: "Cómplice capturado o delator", blBase: 7 },
  { nivel: 8, nombre: "Reivindicación pública o masacre grabada", blBase: 8 },
  { nivel: 9, nombre: "En flagrante delito ante las fuerzas del orden", blBase: 9 },
];

/**
 * Calcula la recompensa en créditos según el Nivel de Busca (BL 1–10) y la condición de entrega.
 */
export function calcularRecompensaBL(bl, condicion = "vivo", primaPct = 0) {
  const nivel = acota(Math.round(n(bl, 1)), 1, 10);
  const info = NIVELES_BL[nivel];
  const base = condicion === "muerto" ? info.muerto : info.vivo;
  const prima = Math.round(base * (acota(n(primaPct, 0), 0, 200) / 100));
  const total = base + prima;
  const formato = total >= 1000000 ? `${(total / 1000000).toFixed(total % 1000000 === 0 ? 0 : 2)}Mcr`
    : total >= 1000 ? `${(total / 1000).toFixed(total % 1000 === 0 ? 0 : 1)}kcr` : `${total}cr`;
  return { bl: nivel, base, prima, total, formato, etiqueta: info.etiqueta };
}

/**
 * Regla de oro del Guardián (pág. 16): «Si no sabes cómo resolver o decidir algo, usa el Nivel de Recompensa (BL).
 * ¿La tirada de 1d10 sale igual o por debajo del BL? Eso ocurre (complicación / resistencia a favor del objetivo)».
 */
export function oraculoBL(bl, tiradaD10) {
  const nivel = acota(Math.round(n(bl, 1)), 1, 10);
  const d = acota(Math.round(n(tiradaD10, 5)), 1, 10);
  const ocurre = d <= nivel;
  return {
    bl: nivel,
    tirada: d,
    ocurre,
    resumen: ocurre
      ? `Sale ${d} (≤ BL:${nivel}): la complicación o defensa del objetivo se activa.`
      : `Sale ${d} (> BL:${nivel}): la situación favorece a los cazarrecompensas.`,
  };
}

/**
 * Evalúa si la tripulación es identificada tras cometer un delito (pág. 224).
 * Se recorre la prueba más sólida dejada (1–9) y se tira 1d10: si sale ≤ nivelPrueba, se vincula a la tripulación.
 */
export function evaluarDelitoJugador({ nivelPrueba = 3, blDelito = 3, tiradaD10 = 5, blActual = 0 } = {}) {
  const np = acota(Math.round(n(nivelPrueba, 3)), 1, 9);
  const d = acota(Math.round(n(tiradaD10, 5)), 1, 10);
  const bDel = acota(Math.round(n(blDelito, np)), 1, 10);
  const bAct = acota(Math.round(n(blActual, 0)), 0, 10);
  const identificado = d <= np;
  let blNuevo = bAct;
  if (identificado) {
    blNuevo = bAct === 0 ? bDel : acota(Math.max(bAct, bDel) + (bDel >= bAct ? 1 : 0), 1, 10);
  }
  return {
    nivelPrueba: np,
    tirada: d,
    identificado,
    blAnterior: bAct,
    blNuevo,
    resumen: identificado
      ? `Identificados (1d10=${d} ≤ prueba ${np}) · Nivel de Busca pasa a BL:${blNuevo}.`
      : `Sin vincular (1d10=${d} > prueba ${np}) · La tripulación escapa sin orden de busca por ahora.`,
  };
}

/**
 * Calcula la sentencia en un juicio según el BL de la tripulación y la tirada de defensa legal (págs. 225–228).
 */
export function calcularSentencia(bl, tiradaDefensaD10 = 5) {
  const nivel = acota(Math.round(n(bl, 1)), 1, 10);
  const d = acota(Math.round(n(tiradaDefensaD10, 5)), 1, 10);
  const indice = acota(nivel * 2 - Math.floor(d / 2), 1, 20);

  if (indice <= 3) {
    return { bl: nivel, indice, tipo: "multa", multaKcr: nivel * 2, aniosODC: 0, destino: "Libertad tras abonar multa y costas judiciales." };
  }
  if (indice <= 7) {
    return { bl: nivel, indice, tipo: "trabajos", multaKcr: nivel * 5, aniosODC: acota(nivel + 2, 2, 8), destino: "Trabajos forzados o traslado en el MPT «Bus» a la Luna Carcelaria ODC (Baclite)." };
  }
  if (indice <= 14) {
    const anios = acota(nivel * 3 + (10 - d), 6, 35);
    return { bl: nivel, indice, tipo: "odc", multaKcr: nivel * 15, aniosODC: anios, destino: `Reclusión de ${anios} años en el Centro de Detención de Offit (ODC, Baclite).` };
  }
  if (indice <= 17) {
    return { bl: nivel, indice, tipo: "perpetua", multaKcr: 0, aniosODC: 99, destino: "Cadena perpetua en el Bloque 23/86 de la ODC (Baclite) sin derecho a fianza." };
  }
  return { bl: nivel, indice, tipo: "ejecucion", multaKcr: 0, aniosODC: 100, destino: "Pena capital / Crioprisión orbital indefinida." };
}

/**
 * Evalúa un intento de soborno al personal de la ODC (pág. 298).
 * Para que un funcionario acepte un soborno hay que sacar menos que su valor de Soborno en d100.
 */
export function evaluarSobornoODC({ umbralSoborno = 45, tiradaD100 = 50, bonoOferta = 0 } = {}) {
  const base = acota(Math.round(n(umbralSoborno, 45)), 1, 100);
  const bono = acota(Math.round(n(bonoOferta, 0)), -50, 50);
  const objetivo = acota(base + bono, 1, 99);
  const d = acota(Math.round(n(tiradaD100, 50)), 0, 99);
  const exito = d < objetivo;
  const critico = d % 11 === 0;
  return {
    umbralBase: base,
    objetivo,
    tirada: d,
    exito,
    critico,
    resumen: exito
      ? `Acepta el soborno (${d} < ${objetivo})${critico ? " · Éxito crítico: ofrece un favor extra o aviso de redada" : ""}.`
      : `Rechaza el soborno (${d} ≥ ${objetivo})${critico ? " · Fallo crítico: confisca los créditos y da la alarma" : ""}.`,
  };
}

/**
 * Simula una jornada de supervivencia en el Infierno Verde de Offit (págs. 304–305).
 */
export function simularDiaInfiernoVerde({ dEncuentro = 5, dHora = 4, dFruta = null } = {}) {
  const enc = acota(Math.round(n(dEncuentro, 5)), 0, 9);
  const hr = acota(Math.round(n(dHora, 4)), 0, 9);

  const franja = hr <= 2 ? "Por la mañana (06:00–11:00)"
    : hr <= 5 ? "Durante el día (11:00–17:00)"
    : hr <= 7 ? "Al atardecer (17:00–20:00)"
    : "De noche (20:00–06:00)";

  const tablaEnc = {
    0: "Encuentro con fauna de Offit (tira en la tabla de Fauna, pág. 306).",
    1: "Encuentro con fauna de Offit (tira en la tabla de Fauna, pág. 306).",
    2: "Patrulla de 2d10 funcionarios (CO) de la prisión rastreando en aeronaves VTOL.",
    3: "30 % de hallar planta medicinal/comestible especial (± rumores conocidos de la pág. 296).",
    4: "Grupo de 1d10 presos fugados del Campamento maderero.",
    5: "Grupo de 1d10 fugados procedentes del Elephant Lodge.",
    6: "Expedición científica armada de 1d10+3 miembros con aeronaves VTOL.",
    7: "Silencio húmedo bajo el dosel: hoy no hay encuentro.",
    8: "Silencio húmedo bajo el dosel: hoy no hay encuentro.",
    9: "Suceso de descubrimiento en la espesura (ruinas, carcasa o rastro hacia la Colonia de Fuga).",
  };

  let resultadoFruta = null;
  if (dFruta !== null && dFruta !== undefined) {
    const f = acota(Math.round(n(dFruta, 5)), 0, 9);
    if (f <= 1) resultadoFruta = "Planta especial de Offit (véase catálogo botánico de los presos, pág. 297).";
    else if (f <= 4) resultadoFruta = "No comestible: provoca vómitos violentos (+1 Estrés).";
    else if (f <= 7) resultadoFruta = "Comestible: cuenta como 1 ración de comida fresca.";
    else resultadoFruta = "Venenosa: Salvación de Cuerpo; si falla, sufre daño igual al margen de fallo durante 1d10 días postrado.";
  }

  return {
    dEncuentro: enc,
    dHora: hr,
    franja,
    encuentro: tablaEnc[enc],
    fruta: resultadoFruta,
  };
}

/**
 * Parsea un bloque de estadísticas de Mothership del manual, p. ej.:
 * `[C:65 Garras 3d10 DAÑO I:50 PA:5 RD:3 H:4(30)]` o `C:40 (Hachuela) I:44 H:3(20)`.
 */
export function parsearEstadisticasMosh(texto = "") {
  const s = String(texto ?? "");
  const mC = s.match(/C\s*:\s*(\d+)/i);
  const mI = s.match(/I\s*:\s*(\d+)/i);
  const mPA = s.match(/PA\s*:\s*(\d+)/i);
  const mRD = s.match(/RD\s*:\s*(\d+)/i);
  const mH = s.match(/H\s*:\s*(\d+)\s*(?:\(\s*(\d+)\s*\))?/i);

  const combat = mC ? Number(mC[1]) : 30;
  const instinct = mI ? Number(mI[1]) : 30;
  const armor = mPA ? Number(mPA[1]) : 0;
  const dr = mRD ? Number(mRD[1]) : 0;
  const wounds = mH ? Number(mH[1]) : 2;
  const health = mH && mH[2] ? Number(mH[2]) : 20;

  let arma = "Ataque cuerpo a cuerpo";
  let danio = "1d10";
  const mParen = s.match(/C\s*:\s*\d+\s*\(([^)]+)\)/i);
  const mInline = s.match(/C\s*:\s*\d+\s+([^[\]I]+?)\s+(\d+d\d+(?:[+-]\d+)?|\d+)\s*DAÑO/i);
  if (mInline) {
    arma = mInline[1].trim();
    danio = mInline[2].trim();
  } else if (mParen) {
    arma = mParen[1].trim();
    danio = /revólver|pistola|fusil|escopeta/i.test(arma) ? "2d10" : "1d10";
  }

  return { combat, instinct, armor, dr, wounds, health, arma, danio };
}

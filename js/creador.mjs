/**
 * El creador de personajes de MoSh usa el equipo inicial de este libro (págs. 318-319) para las clases Marine, Androide,
 * Científico y Transportista, y las clases «Preso» y «Cazarrecompensas» traen el suyo. Además, una macro equipa a cualquier
 * ficha con un equipo inicial del libro.
 */
import { MOD } from "./compat.mjs";

const GRUPOS = [
  ["marines", "Marines", /marine|marin/i],
  ["androides", "Androides", /android/i],
  ["cientificos", "Científicos", /scien|cient/i],
  ["transportistas", "Transportistas", /teamster|transport/i],
  ["presos", "Presos", /prison|preso|recluso/i],
  ["cazarrecompensas", "Cazarrecompensas", /bounty|cazarrec/i],
];

let tablasCache = null;
async function tablas() {
  tablasCache ??= await (await fetch(`modules/${MOD}/content/equipo-tablas.json`)).json();
  return tablasCache;
}

export function registrarCreador() {
  game.settings.register(MOD, "equipoCreador", {
    name: "Creador de personajes: equipo inicial de Wages of Sin",
    hint: "Al elegir una clase (Marine, Androide, Científico, Transportista, Preso o Cazarrecompensas), el creador de MoSh tira el equipo inicial de este libro.",
    scope: "world", config: true, type: Boolean, default: true,
  });

  // el creador de MoSh es una ventana (DLActorGenerator): al abrirse, su carga de clase pasa a usar nuestra tabla
  Hooks.on("renderDLActorGenerator", app => {
    if (app._wosParcheado) return;
    app._wosParcheado = true;
    const original = app.updateClass.bind(app);
    app.updateClass = async uuid => {
      await original(uuid);
      if (!game.settings.get(MOD, "equipoCreador")) return;
      const clase = await fromUuid(uuid);
      const grupo = GRUPOS.find(([, , re]) => re.test(clase?.name ?? ""));
      if (!grupo) return;
      app.loadoutTable = (await tablas())[grupo[0]];
      ui.notifications.info(`MR- Wages of Sin: el equipo inicial de ${grupo[1]} será el del libro (págs. 318-319).`);
    };
  });
}

/** Añade a la ficha los objetos de una tirada (cada resultado es un objeto del compendio; los repetidos suman cantidad). */
async function darObjetos(actor, resultados) {
  const cuenta = new Map();
  for (const r of resultados) if (r.documentUuid) cuenta.set(r.documentUuid, (cuenta.get(r.documentUuid) ?? 0) + 1);
  for (const [uuid, n] of cuenta) {
    if (typeof actor.modifyItem === "function") await actor.modifyItem(uuid, n);
    else {
      const doc = await fromUuid(uuid);
      if (doc) await actor.createEmbeddedDocuments("Item", [doc.toObject()]);
    }
  }
}

export async function ejecutarMacroEquipo() {
  const actor = canvas.tokens?.controlled?.[0]?.actor ?? game.user.character;
  if (!actor) return ui.notifications.warn("Selecciona un token o asigna tu personaje para darle el equipo inicial.");
  const datos = await foundry.applications.api.DialogV2.prompt({
    window: { title: "Equipo inicial de Wages of Sin", icon: "fa-solid fa-suitcase" },
    content: `<div class="form-group"><label>Equipo de</label><select name="grupo">${GRUPOS.map(([k, n]) => `<option value="${k}">${n}</option>`).join("")}</select></div>
      <div class="form-group"><label>Fila</label><select name="fila"><option value="0">Al azar (1d10)</option>${[1, 2, 3, 4, 5, 6, 7, 8, 9, 10].map(i => `<option value="${i}">${i === 10 ? "00" : "0" + i}</option>`).join("")}</select></div>
      <p class="hint">Se añade a ${foundry.utils.escapeHTML(actor.name)} lo que dice el libro (págs. 318-319).</p>`,
    ok: { label: "Equipar", icon: "fa-solid fa-check", callback: (_e, btn) => ({ grupo: btn.form.elements.grupo.value, fila: Number(btn.form.elements.fila.value) }) },
    rejectClose: false,
  });
  if (!datos) return;
  const tabla = await fromUuid((await tablas())[datos.grupo]);
  if (!tabla) return ui.notifications.error("No se encuentra la tabla de equipo inicial.");
  let resultados;
  if (datos.fila) resultados = tabla.results.filter(r => r.range[0] === datos.fila);
  else resultados = (await tabla.draw({ displayChat: true })).results;
  await darObjetos(actor, resultados);
  ui.notifications.info(`${actor.name}: equipo inicial añadido.`);
}

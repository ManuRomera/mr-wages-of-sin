/**
 * Punto de entrada de MR- Wages of Sin: Kit de Cazarrecompensas y La Luna Carcelaria (Mothership 1e).
 */
import { MOD, insertarControlEscena } from "./compat.mjs";
import { registrarAccesibilidad } from "./accesibilidad.mjs";
import { registrarEventosChat, publicarCartelOrden } from "./chat.mjs";
import {
  TerminalRecompensas,
  cargarIndiceOrdenes,
  ejecutarMacroGenerarOrden,
  ejecutarMacroRastrear,
  ejecutarMacroDelito,
  ejecutarMacroSoborno,
  ejecutarMacroInfiernoVerde,
} from "./terminal.mjs";
import { registrarCreditosMR } from "./mr-credits.mjs";

const soyGM = () => game.user === game.users.activeGM;

let instanciaTerminal = null;
export function abrirTerminal() {
  instanciaTerminal ??= new TerminalRecompensas();
  instanciaTerminal.render(true);
  return instanciaTerminal;
}

async function registrarPackDireccion() {
  const api = game.modules.get("mr-direccion")?.api || game.mrDireccion;
  if (!api?.registerPack) return;
  try {
    const resp = await fetch(`modules/${MOD}/content/direccion-es.json`);
    if (resp.ok) api.registerPack(await resp.json());
  } catch (err) {
    console.warn(`${MOD} | No se pudo registrar el paquete de MR- Dirección`, err);
  }
}

function mundoVacio() {
  const escenasMod = game.scenes.filter(s => s.flags?.[MOD]);
  return game.scenes.size === 0 || escenasMod.length === 0;
}

function respetarPJ(adventure, _formData, toCreate, toUpdate) {
  for (const col of [toCreate, toUpdate]) {
    if (!col?.Actor) continue;
    col.Actor = col.Actor.filter(a => {
      const existente = game.actors.get(a._id);
      if (!existente) return true;
      return existente.type !== "character" && existente.flags?.[MOD]?.tipo !== "pj";
    });
  }
}

async function importarAventura({ silencioso = false } = {}) {
  const pack = game.packs.get(`${MOD}.aventura-baclite`);
  if (!pack) return;
  const docs = await pack.getDocuments();
  const adv = docs[0];
  if (!adv) return;

  await adv.sheet?._importContent?.(adv, {}, [respetarPJ]) ?? await adv.import({ preImport: [respetarPJ] });
  const versionActual = game.modules.get(MOD)?.version || "1.0.0";
  await game.settings.set(MOD, "versionImportada", versionActual);

  const portada = game.scenes.find(s => s.flags?.[MOD]?.clave === "portada");
  if (portada) await portada.activate();

  const guia = game.journal.find(j => j.flags?.[MOD]?.clave === "00-empieza-aqui");
  if (guia && !silencioso) guia.sheet.render(true);
  await registrarPackDireccion();
}

Hooks.once("init", () => {
  game.settings.register(MOD, "versionImportada", {
    name: "Versión de la aventura importada",
    scope: "world",
    config: false,
    type: String,
    default: "0.0.0",
  });

  game.settings.register(MOD, "blGrupo", {
    name: "Nivel de Busca de la tripulación (BL 0–10)",
    hint: "Nivel de recompensa acumulado por la tripulación tras cometer delitos en el sector.",
    scope: "world",
    config: true,
    type: Number,
    default: 0,
  });

  game.settings.register(MOD, "reputacionODC", {
    name: "Reputación con las facciones de la ODC",
    scope: "world",
    config: false,
    type: Object,
    default: { arms23: 0, stratemeyer: 0, sindicato: 0, guardias: 0 },
  });

  registrarAccesibilidad();
  registrarCreditosMR();
  registrarEventosChat();

  game.mrWages = {
    abrirTerminal,
    importarAventura,
    macros: {
      abrirTerminal,
      generarOrden: ejecutarMacroGenerarOrden,
      rastrear: ejecutarMacroRastrear,
      delitoJugadores: ejecutarMacroDelito,
      sobornoODC: ejecutarMacroSoborno,
      infiernoVerde: () => ejecutarMacroInfiernoVerde(false),
    },
  };
});

Hooks.on("getSceneControlButtons", controls => {
  insertarControlEscena(controls, {
    name: "mr-wages-terminal",
    title: "MR- Wages of Sin · Terminal de Recompensas y ODC",
    icon: "fa-solid fa-crosshairs",
    button: true,
    visible: true,
    onClick: () => abrirTerminal(),
    onChange: () => abrirTerminal(),
  });
});

Hooks.on("mrDireccion.ready", () => {
  registrarPackDireccion();
});

/** Figuras de cuerpo entero en escenas de imagen para MR- Dirección. */
Hooks.on("preCreateToken", (tokenDoc, _data, _options, _userId) => {
  const actor = tokenDoc.actor;
  const escena = tokenDoc.parent;
  const figura = actor?.flags?.[MOD]?.figura;
  if (!figura || !escena?.flags?.[MOD]?.imagen) return;
  tokenDoc.updateSource({
    "texture.src": figura,
    "texture.fit": "contain",
    "ring.enabled": false,
  });
});

/** Botones interactivos dentro de las páginas de las 100 Órdenes de Busca. */
Hooks.on("renderJournalEntryPageTextSheet", (_sheet, html) => {
  const raiz = html instanceof HTMLElement ? html : html?.[0];
  if (!raiz) return;
  raiz.querySelectorAll("[data-mrwages-action]").forEach(btn => {
    btn.addEventListener("click", async ev => {
      ev.preventDefault();
      const acc = btn.dataset.mrwagesAction;
      if (acc === "publicar-cartel") {
        const num = Number(btn.dataset.orden) || 1;
        const ordenes = await cargarIndiceOrdenes();
        const o = ordenes.find(x => x.num === num);
        await publicarCartelOrden(o);
      } else if (acc === "abrir-actor") {
        const aid = btn.dataset.actorId;
        let actor = game.actors.get(aid);
        if (!actor) {
          const pack = game.packs.get(`${MOD}.objetivos`);
          const doc = await pack?.getDocument(aid);
          if (doc) return doc.sheet.render(true);
        }
        actor?.sheet?.render(true);
      }
    });
  });
});

Hooks.once("ready", async () => {
  await registrarPackDireccion();
  if (!soyGM()) return;

  const verMod = game.modules.get(MOD)?.version || "1.0.0";
  const verImp = game.settings.get(MOD, "versionImportada") || "0.0.0";

  if (mundoVacio()) {
    await importarAventura({ silencioso: false });
    ui.notifications.info("MR- Wages of Sin: Escenas de Baclite, naves, cazadores y manuales importados.");
  } else if (foundry.utils.isNewerVersion(verMod, verImp)) {
    const ok = await foundry.applications.api.DialogV2.confirm({
      window: { title: "Actualizar MR- Wages of Sin", icon: "fa-solid fa-crosshairs" },
      content: `<p>Se ha detectado una versión más reciente de <strong>MR- Wages of Sin</strong> (${verMod}). ¿Deseas actualizar las escenas, naves y diarios respetando los personajes de los jugadores?</p>`,
      rejectClose: false,
    });
    if (ok) await importarAventura({ silencioso: true });
    else await game.settings.set(MOD, "versionImportada", verMod);
  }
});

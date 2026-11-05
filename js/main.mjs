/**
 * Punto de entrada de MR- Wages of Sin: importa la aventura en un mundo vacío (cada cosa en su carpeta),
 * la registra en MR- Dirección y añade la Terminal de recompensas.
 */
import { MOD, insertarControlEscena } from "./compat.mjs";
import { registrarAccesibilidad } from "./accesibilidad.mjs";
import { registrarEventosChat, publicarCartelOrden } from "./chat.mjs";
import { TerminalRecompensas, cargarIndiceOrdenes, ejecutarMacroGenerarOrden, ejecutarMacroOraculo, ejecutarMacroSoborno } from "./terminal.mjs";
import { registrarCreditosMR } from "./mr-credits.mjs";

const t = k => game.i18n.localize(`MRWOS.${k}`);

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

/** Un mundo recién creado: sin nada propio y sin escenas salvo la de bienvenida de Foundry. */
function mundoVacio() {
  const ajenas = game.scenes.contents.filter(s => !s.flags?.[MOD] && !String(s.background?.src ?? "").startsWith("nue/"));
  return ajenas.length === 0 && game.actors.size === 0 && game.journal.size === 0 && game.items.size === 0;
}

/** Los personajes que ya llevan los jugadores no se pisan al reimportar. */
function respetarPJ(_adventure, _formData, toCreate, toUpdate) {
  for (const col of [toCreate, toUpdate]) {
    if (!col?.Actor) continue;
    col.Actor = col.Actor.filter(a => {
      const existente = game.actors.get(a._id);
      return !existente || (existente.type !== "character" && existente.flags?.[MOD]?.tipo !== "pj");
    });
  }
}

export async function importarAventura({ confirmar = false } = {}) {
  const pack = game.packs.get(`${MOD}.aventura-baclite`);
  if (!pack) return ui.notifications.error(t("SinPack"));
  const adv = (await pack.getDocuments())[0];
  if (!adv) return;
  if (confirmar) {
    const ok = await foundry.applications.api.DialogV2.confirm({
      window: { title: t("Importar"), icon: "fa-solid fa-file-import" },
      content: `<p>${t("ImportarAviso")}</p>`,
      yes: { label: t("Importar"), icon: "fa-solid fa-file-import" }, no: { label: t("Cancelar") },
      rejectClose: false,
    });
    if (!ok) return;
  }
  await adv.import({ dialog: false, preImport: [respetarPJ] });
  // las macros del paquete llevan un autor ficticio (un Adventure lo exige): pasan a ser del Guardián que importa
  for (const m of game.macros) if (m.flags?.[MOD]?.clave && !game.users.get(m._source.author)) await m.update({ author: game.user.id });
  await game.settings.set(MOD, "versionImportada", game.modules.get(MOD)?.version || "0.0.0");
  // las macros del paquete a la barra de macros del Guardián, si está libre
  const mac = ["terminal", "generar-orden", "oraculo-bl", "soborno-odc"].map(c => game.macros.find(m => m.flags?.[MOD]?.clave === c)).filter(Boolean);
  for (const [i, m] of mac.entries()) if (!game.user.hotbar?.[i + 1]) await game.user.assignHotbarMacro(m, i + 1);
  game.scenes.find(s => s.flags?.[MOD]?.clave === "portada")?.activate();
  game.journal.find(j => j.flags?.[MOD]?.clave === "00-empieza-aqui")?.sheet.render(true);
  await registrarPackDireccion();
  ui.notifications.info(t("Importada"));
}

Hooks.once("init", () => {
  game.settings.register(MOD, "versionImportada", { scope: "world", config: false, type: String, default: "0.0.0" });
  registrarAccesibilidad();
  registrarCreditosMR();
  registrarEventosChat();
  game.mrWages = {
    abrirTerminal, importarAventura,
    macros: { abrirTerminal, generarOrden: ejecutarMacroGenerarOrden, oraculoBL: ejecutarMacroOraculo, sobornoODC: ejecutarMacroSoborno },
  };
});

Hooks.on("getSceneControlButtons", controls => {
  insertarControlEscena(controls, {
    name: "mr-wages-terminal", title: "MR- Wages of Sin · Terminal de recompensas", icon: "fa-solid fa-crosshairs",
    button: true, visible: true, onClick: () => abrirTerminal(), onChange: () => abrirTerminal(),
  });
});

Hooks.on("mrDireccion.ready", () => registrarPackDireccion());

/** Botón en Configuración para volver a importar. */
Hooks.on("renderSettings", (_app, html) => {
  if (!game.user.isGM) return;
  const raiz = html instanceof HTMLElement ? html : html?.[0];
  if (!raiz || raiz.querySelector(".mr-wos-ajustes")) return;
  const sec = document.createElement("section");
  sec.className = "mr-wos-ajustes";
  sec.innerHTML = `<h4 class="divider">MR- Wages of Sin</h4>
    <button type="button" data-wos="importar"><i class="fa-solid fa-file-import" inert></i> ${t("Importar")}</button>
    <button type="button" data-wos="terminal"><i class="fa-solid fa-crosshairs" inert></i> ${t("Terminal")}</button>`;
  sec.addEventListener("click", ev => {
    const b = ev.target.closest("button[data-wos]");
    if (!b) return;
    if (b.dataset.wos === "importar") importarAventura({ confirmar: true });
    else abrirTerminal();
  });
  (raiz.querySelector("#settings-game") || raiz.querySelector(".settings-list") || raiz).append(sec);
});

/** Figuras de cuerpo entero en escenas de imagen para MR- Dirección. */
Hooks.on("preCreateToken", tokenDoc => {
  const figura = tokenDoc.actor?.flags?.[MOD]?.figura;
  if (!figura || !tokenDoc.parent?.flags?.[MOD]?.imagen) return;
  tokenDoc.updateSource({ "texture.src": figura, "texture.fit": "contain", "ring.enabled": false });
});

/** Botones dentro de las páginas de las órdenes de busca. */
Hooks.on("renderJournalEntryPageTextSheet", (_sheet, html) => {
  const raiz = html instanceof HTMLElement ? html : html?.[0];
  raiz?.querySelectorAll("[data-mrwages-action]").forEach(btn => {
    btn.addEventListener("click", async ev => {
      ev.preventDefault();
      if (btn.dataset.mrwagesAction === "publicar-cartel") {
        const ordenes = await cargarIndiceOrdenes();
        await publicarCartelOrden(ordenes.find(x => x.num === Number(btn.dataset.orden)));
      } else if (btn.dataset.mrwagesAction === "abrir-actor") {
        const aid = btn.dataset.actorId;
        const doc = game.actors.get(aid) ?? await game.packs.get(`${MOD}.objetivos`)?.getDocument(aid);
        doc?.sheet.render(true);
      }
    });
  });
});

Hooks.once("ready", async () => {
  game.modules.get(MOD).api = { importarAventura, abrirTerminal };
  await registrarPackDireccion();
  if (game.user !== game.users.activeGM) return;
  const verMod = game.modules.get(MOD)?.version || "0.0.0";
  const verImp = game.settings.get(MOD, "versionImportada") || "0.0.0";
  if (verImp === "0.0.0" && mundoVacio()) {
    // al principio: ¿todo al mundo o solo compendios?
    const eleccion = await foundry.applications.api.DialogV2.wait({
      window: { title: t("BienvenidaTitulo"), icon: "fa-solid fa-crosshairs" },
      content: `<p>${t("BienvenidaTexto")}</p>`,
      buttons: [
        { action: "todo", label: t("ImportarTodo"), icon: "fa-solid fa-file-import", default: true },
        { action: "compendios", label: t("SoloCompendios"), icon: "fa-solid fa-book" },
      ],
      rejectClose: false,
    });
    if (eleccion === "todo") {
      try { await importarAventura(); } catch (e) { console.error(`${MOD} | importación fallida`, e); ui.notifications.error(t("ErrorImportar")); }
    } else {
      await game.settings.set(MOD, "versionImportada", verMod);   // no se vuelve a preguntar; queda el botón de Configuración
      ui.notifications.info(t("SoloCompendiosAviso"));
    }
  } else if (verImp !== "0.0.0" && foundry.utils.isNewerVersion(verMod, verImp)) {
    const ok = await foundry.applications.api.DialogV2.confirm({
      window: { title: t("Actualizar"), icon: "fa-solid fa-crosshairs" },
      content: `<p>${game.i18n.format("MRWOS.ActualizarAviso", { version: verMod })}</p>`, rejectClose: false,
    });
    if (ok) await importarAventura();
    else await game.settings.set(MOD, "versionImportada", verMod);
  }
});

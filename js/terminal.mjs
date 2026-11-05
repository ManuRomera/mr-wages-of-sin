/**
 * Terminal de recompensas (`ApplicationV2` con `ConMemoria`): las 100 órdenes de busca, la tabla de niveles y los sobornos de la ODC.
 */
import { MOD } from "./compat.mjs";
import { ConMemoria, guardarLocal, recordarLocal } from "./accesibilidad.mjs";
import { NIVELES_BL, oraculoBL, evaluarSobornoODC } from "./core/reglas.mjs";
import { publicarTarjeta, publicarCartelOrden } from "./chat.mjs";

const esc = s => foundry.utils.escapeHTML(String(s ?? ""));
const n = (v, d = 0) => (Number.isFinite(Number(v)) ? Number(v) : d);

let cacheOrdenes = null;
export async function cargarIndiceOrdenes() {
  if (cacheOrdenes) return cacheOrdenes;
  const r = await fetch(`modules/${MOD}/content/ordenes-indice.json`);
  cacheOrdenes = await r.json();
  return cacheOrdenes;
}

/** Personal de dirección de la ODC con su valor de Soborno (compendio de objetivos, flag `soborno`). */
async function personalODC() {
  const pack = game.packs.get(`${MOD}.objetivos`);
  if (!pack) return [];
  const idx = await pack.getIndex({ fields: ["flags", "name"] });
  return idx.filter(e => e.flags?.[MOD]?.categoria === "odc-personal").map(e => ({ id: e._id, nombre: e.name, soborno: n(e.flags[MOD].soborno, 50) }));
}

export async function abrirDocOrden(o) {
  const diario = await fromUuid(`Compendium.${MOD}.ordenes.JournalEntry.${o.diarioId}`);
  const pagina = diario?.pages?.get(o.paginaId);
  if (pagina) return diario.sheet.render(true, { pageId: o.paginaId });
  return diario?.sheet.render(true);
}

export async function abrirActorOrden(o) {
  const pack = game.packs.get(`${MOD}.objetivos`);
  const doc = game.actors.get(o.actorId) ?? await pack?.getDocument(o.actorId);
  doc?.sheet.render(true);
}

const BaseApp = ConMemoria(foundry.applications.api.ApplicationV2);

export class TerminalRecompensas extends BaseApp {
  static DEFAULT_OPTIONS = {
    id: "mr-wages-terminal",
    tag: "div",
    classes: ["mosh", "mr-wos-terminal"],
    window: { title: "MR- Wages of Sin · Terminal de recompensas", icon: "fa-solid fa-crosshairs", resizable: true },
    position: { width: 880, height: 680 },
  };

  constructor(options = {}) {
    super(options);
    this.pestana = recordarLocal("terminal.pestana") || "ordenes";
    this.filtroTexto = "";
    this.filtroBL = 0;
    this.ordenSeleccionada = 1;
    this.sobornoSel = null;
  }

  async _prepareContext() {
    return { ordenes: await cargarIndiceOrdenes(), personal: await personalODC() };
  }

  async _renderHTML(context) {
    const wrapper = document.createElement("div");
    wrapper.className = "mr-wos-contenedor";
    wrapper.innerHTML = this.#construirHTML(context);
    return wrapper;
  }

  _replaceHTML(result, content) {
    content.replaceChildren(result);
    this.#vincularEventos(content);
  }

  #panelOrdenes(ordenes) {
    const q = this.filtroTexto.toLowerCase();
    const filtradas = ordenes.filter(o => (!this.filtroBL || o.bl === this.filtroBL)
      && (!q || [String(o.num).padStart(2, "0"), o.titulo, o.entrega, o.etiquetas, o.delito, o.lugar].some(t => String(t).toLowerCase().includes(q))));
    const actual = filtradas.find(o => o.num === this.ordenSeleccionada) || filtradas[0];
    const fila = (k, v) => (v ? `<tr><th>${k}</th><td>${esc(v)}</td></tr>` : "");
    return `
      <div class="mr-wos-barra-filtros">
        <input type="search" name="filtroTexto" placeholder="Buscar por nombre, lugar, delito…" value="${esc(this.filtroTexto)}" />
        <select name="filtroBL">
          <option value="0">Todos los niveles</option>
          ${Object.values(NIVELES_BL).map(b => `<option value="${b.bl}" ${this.filtroBL === b.bl ? "selected" : ""}>BL:${b.bl} · ${b.tipo}</option>`).join("")}
        </select>
        <button type="button" data-acc="orden-azar"><i class="fa-solid fa-shuffle"></i> Al azar (1d100)</button>
      </div>
      <div class="mr-wos-maestro-detalle">
        <div class="mr-wos-lista-ordenes">
          ${filtradas.map(o => `<button type="button" class="mr-wos-item-orden ${o.num === actual?.num ? "seleccionada" : ""}" data-select-orden="${o.num}">
            <span class="mr-wos-num">${String(o.num).padStart(2, "0")}</span><span class="mr-wos-nom">${esc(o.titulo)}</span><span class="mr-wos-bl-tag">BL:${o.bl}</span></button>`).join("")
          || "<p class='hint'>Ninguna orden coincide.</p>"}
        </div>
        ${actual ? `<div class="mr-wos-detalle-orden">
          <div class="mr-wos-cartel">
            <div class="mr-wos-cartel-foto"><img src="${esc(actual.img)}" alt="${esc(actual.titulo)}" />
              <div class="mr-wos-sello">BL:${actual.bl} · ${esc(actual.seBusca.toUpperCase())}</div>
              ${actual.codigo ? `<div class="mr-wos-cod">CÓD. ${esc(actual.codigo)} · PÁG. ${actual.pagina}</div>` : `<div class="mr-wos-cod">PÁG. ${actual.pagina}</div>`}</div>
            <div class="mr-wos-cartel-datos">
              <h3>ORDEN ${String(actual.num).padStart(2, "0")} · ${esc(actual.titulo)}</h3>
              ${actual.lugar ? `<p class="mr-wos-lugar">${esc(actual.lugar)}</p>` : ""}
              ${actual.anuncio ? `<blockquote class="mr-wos-anuncio">${esc(actual.anuncio)}</blockquote>` : ""}
              <table class="mr-wos-tabla"><tbody>
                ${fila("Delito", actual.delito)}${fila("Cliente", actual.cliente)}${fila("Pago", actual.pago)}${fila("Prima", actual.prima)}${fila("Entrega", actual.entrega)}${fila("Último paradero", actual.paradero)}
              </tbody></table>
              <div class="mr-wos-acciones-orden">
                <button type="button" data-acc="publicar-cartel" data-num="${actual.num}"><i class="fa-solid fa-bullhorn"></i> Mostrar cartel a la mesa</button>
                <button type="button" data-acc="abrir-diario-orden" data-num="${actual.num}"><i class="fa-solid fa-book-open"></i> Orden completa</button>
                <button type="button" data-acc="abrir-actor-orden" data-num="${actual.num}"><i class="fa-solid fa-user-secret"></i> Ficha del objetivo</button>
                <button type="button" data-acc="oraculo" data-bl="${actual.bl}"><i class="fa-solid fa-dice-d10"></i> Oráculo BL:${actual.bl}</button>
              </div>
            </div>
          </div>
          ${actual.informe ? `<div class="mr-wos-resumen-pub"><h4>Informe</h4><p>${esc(actual.informe)}</p></div>` : ""}
        </div>` : ""}
      </div>`;
  }

  #panelNiveles() {
    return `<div class="mr-wos-caja">
      <h3><i class="fa-solid fa-scale-balanced"></i> Nivel de Recompensa y pago (págs. 12-13)</h3>
      <table class="mr-wos-tabla"><thead><tr><th>BL</th><th>Tipo</th><th>Pago</th><th>Descripción</th></tr></thead><tbody>
        ${Object.values(NIVELES_BL).map(b => `<tr><th>${b.bl}</th><td>${b.tipo}</td><td><strong>${b.pago}</strong></td><td>${esc(b.nota)}</td></tr>`).join("")}
      </tbody></table>
      <p class="hint">Regla del Guardián (pág. 16): si no sabes cómo resolver algo, usa el Nivel de Recompensa; si la tirada de 1d10 sale por debajo, ocurre.</p>
    </div>`;
  }

  #panelODC(personal) {
    const sel = personal.find(p => p.id === this.sobornoSel) || personal[0];
    return `<div class="mr-wos-caja">
      <h3><i class="fa-solid fa-handshake"></i> Sobornar a un funcionario (pág. 298)</h3>
      <p>Para que alguien del personal acepte un soborno hay que sacar menos que su valor de Soborno en 1d100.</p>
      ${personal.length ? `<div class="mr-wos-fila-form"><label>Funcionario</label>
        <select name="sobornoSel">${personal.map(p => `<option value="${p.id}" ${p.id === sel.id ? "selected" : ""}>${esc(p.nombre)} · Soborno ${p.soborno}</option>`).join("")}</select></div>` : ""}
      <div class="mr-wos-fila-form"><label>Valor de Soborno</label><input type="number" name="sobornoValor" min="1" max="100" value="${sel?.soborno ?? 50}" /></div>
      <div class="mr-wos-acciones-orden"><button type="button" data-acc="soborno"><i class="fa-solid fa-dice"></i> Tirar 1d100</button></div>
    </div>`;
  }

  #construirHTML({ ordenes, personal }) {
    const tab = (id, icono, t) => `<button type="button" class="${this.pestana === id ? "activa" : ""}" data-tab="${id}"><i class="fa-solid ${icono}"></i> ${t}</button>`;
    return `<nav class="mr-wos-tabs">${tab("ordenes", "fa-id-badge", "Las 100 órdenes")}${tab("niveles", "fa-scale-balanced", "Niveles y pago")}${tab("odc", "fa-handshake", "La ODC")}</nav>
      <section class="mr-wos-panel visible">${this.pestana === "niveles" ? this.#panelNiveles() : this.pestana === "odc" ? this.#panelODC(personal) : this.#panelOrdenes(ordenes)}</section>`;
  }

  #vincularEventos(root) {
    root.querySelectorAll("[data-tab]").forEach(b => b.addEventListener("click", () => {
      this.pestana = b.dataset.tab;
      guardarLocal("terminal.pestana", this.pestana);
      this.render();
    }));
    root.querySelector('input[name="filtroTexto"]')?.addEventListener("input", ev => {
      this.filtroTexto = ev.target.value;
      const pos = ev.target.selectionStart;
      this.render().then(() => {
        const i = this.element?.querySelector('input[name="filtroTexto"]');
        if (i) { i.focus(); i.setSelectionRange(pos, pos); }
      });
    });
    root.querySelector('select[name="filtroBL"]')?.addEventListener("change", ev => { this.filtroBL = n(ev.target.value); this.render(); });
    root.querySelector('select[name="sobornoSel"]')?.addEventListener("change", ev => { this.sobornoSel = ev.target.value; this.render(); });
    root.querySelectorAll("[data-select-orden]").forEach(b => b.addEventListener("click", () => { this.ordenSeleccionada = n(b.dataset.selectOrden); this.render(); }));
    root.querySelectorAll("[data-acc]").forEach(b => b.addEventListener("click", async ev => {
      ev.preventDefault();
      const ordenes = await cargarIndiceOrdenes();
      const o = ordenes.find(x => x.num === n(b.dataset.num));
      switch (b.dataset.acc) {
        case "publicar-cartel": return publicarCartelOrden(o);
        case "abrir-diario-orden": return abrirDocOrden(o);
        case "abrir-actor-orden": return abrirActorOrden(o);
        case "orden-azar": {
          const r = await new Roll("1d100").evaluate();
          this.ordenSeleccionada = r.total;
          this.filtroTexto = ""; this.filtroBL = 0;
          return this.render();
        }
        case "oraculo": return ejecutarMacroOraculo(n(b.dataset.bl, 1));
        case "soborno": return ejecutarMacroSoborno(n(root.querySelector('input[name="sobornoValor"]')?.value, 50));
      }
    }));
  }
}

// ───────────────────────── macros ─────────────────────────
export async function ejecutarMacroGenerarOrden() {
  const ordenes = await cargarIndiceOrdenes();
  const r = await new Roll("1d100").evaluate();
  const o = ordenes.find(x => x.num === r.total);
  await publicarCartelOrden(o);
  return o;
}

export async function ejecutarMacroOraculo(bl = null) {
  if (bl === null) {
    bl = await foundry.applications.api.DialogV2.prompt({
      window: { title: "Oráculo de Nivel de Recompensa", icon: "fa-solid fa-dice-d10" },
      content: `<div class="form-group"><label>Nivel de Recompensa (1-9)</label><input type="number" name="bl" min="1" max="9" value="3" autofocus></div>`,
      ok: { label: "Tirar 1d10", icon: "fa-solid fa-dice-d10", callback: (_e, btn) => n(btn.form.elements.bl.value, 3) },
      rejectClose: false,
    });
    if (!bl) return;
  }
  const roll = await new Roll("1d10").evaluate();
  const res = oraculoBL(bl, roll.total);
  return publicarTarjeta(`Oráculo de Nivel de Recompensa (BL:${res.bl})`, `1d10 = ${roll.total}`, `<p>${esc(res.resumen)}</p>`);
}

export async function ejecutarMacroSoborno(soborno = null) {
  if (soborno === null) {
    soborno = await foundry.applications.api.DialogV2.prompt({
      window: { title: "Soborno en la ODC", icon: "fa-solid fa-handshake" },
      content: `<div class="form-group"><label>Valor de Soborno del funcionario</label><input type="number" name="v" min="1" max="100" value="50" autofocus></div>`,
      ok: { label: "Tirar 1d100", icon: "fa-solid fa-dice", callback: (_e, btn) => n(btn.form.elements.v.value, 50) },
      rejectClose: false,
    });
    if (!soborno) return;
  }
  const roll = await new Roll("1d100").evaluate();
  const res = evaluarSobornoODC({ soborno, tiradaD100: roll.total });
  return publicarTarjeta("Soborno en la ODC", `1d100 = ${roll.total}`, `<p>${esc(res.resumen)}</p>`);
}

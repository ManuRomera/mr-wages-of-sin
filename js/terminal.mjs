/**
 * Terminal interactiva de Recompensas, Castigo y Registro de la ODC (`ApplicationV2` con `ConMemoria`).
 */
import { MOD } from "./compat.mjs";
import { ConMemoria, guardarLocal, recordarLocal } from "./accesibilidad.mjs";
import {
  NIVELES_BL,
  PRUEBAS_DELITO,
  calcularRecompensaBL,
  oraculoBL,
  evaluarDelitoJugador,
  calcularSentencia,
  evaluarSobornoODC,
  simularDiaInfiernoVerde,
} from "./core/reglas.mjs";
import { publicarTarjeta, publicarCartelOrden } from "./chat.mjs";

const esc = s => foundry.utils.escapeHTML(String(s ?? ""));
const n = (v, d = 0) => (Number.isFinite(Number(v)) ? Number(v) : d);
const acota = (v, min, max) => Math.min(max, Math.max(min, v));

let cacheOrdenes = null;
export async function cargarIndiceOrdenes() {
  if (cacheOrdenes) return cacheOrdenes;
  const r = await fetch(`modules/${MOD}/content/ordenes-indice.json`);
  cacheOrdenes = await r.json();
  return cacheOrdenes;
}

const BaseApp = ConMemoria(foundry.applications.api.ApplicationV2);

export class TerminalRecompensas extends BaseApp {
  static DEFAULT_OPTIONS = {
    id: "mr-wages-terminal",
    tag: "div",
    classes: ["mosh", "mr-wos-terminal"],
    window: {
      title: "MR- Wages of Sin · Terminal de Recompensas y ODC Baclite",
      icon: "fa-solid fa-crosshairs",
      resizable: true,
    },
    position: { width: 880, height: 680 },
  };

  constructor(options = {}) {
    super(options);
    this.pestana = recordarLocal("terminal.pestana") || "ordenes";
    this.filtroTexto = "";
    this.filtroBL = 0;
    this.ordenSeleccionada = 1;
  }

  async _prepareContext() {
    const ordenes = await cargarIndiceOrdenes();
    return { ordenes };
  }

  async _renderHTML(context) {
    const wrapper = document.createElement("div");
    wrapper.className = "mr-wos-contenedor";
    wrapper.innerHTML = await this.#construirHTML(context.ordenes);
    return wrapper;
  }

  _replaceHTML(result, content) {
    content.replaceChildren(result);
    this.#vincularEventos(content);
  }

  async #construirHTML(ordenes) {
    const blGrupo = n(game.settings.get(MOD, "blGrupo"), 0);
    const repODC = game.settings.get(MOD, "reputacionODC") || { arms23: 0, stratemeyer: 0, sindicato: 0, guardias: 0 };

    const filtradas = ordenes.filter(o => {
      if (this.filtroBL > 0 && o.bl !== this.filtroBL) return false;
      if (!this.filtroTexto) return true;
      const q = this.filtroTexto.toLowerCase();
      return (
        String(o.num).padStart(2, "0").includes(q) ||
        o.titulo.toLowerCase().includes(q) ||
        o.entrega.toLowerCase().includes(q) ||
        o.etiquetas.toLowerCase().includes(q) ||
        o.delito.toLowerCase().includes(q)
      );
    });

    const actual = filtradas.find(o => o.num === this.ordenSeleccionada) || filtradas[0] || ordenes[0];

    return `
      <nav class="mr-wos-tabs">
        <button type="button" class="${this.pestana === "ordenes" ? "activa" : ""}" data-tab="ordenes"><i class="fa-solid fa-id-badge"></i> Las 100 Órdenes</button>
        <button type="button" class="${this.pestana === "generador" ? "activa" : ""}" data-tab="generador"><i class="fa-solid fa-dice"></i> Generador y Rastreo</button>
        <button type="button" class="${this.pestana === "castigo" ? "activa" : ""}" data-tab="castigo"><i class="fa-solid fa-gavel"></i> Delitos y Cazadores (BL:${blGrupo})</button>
        <button type="button" class="${this.pestana === "odc" ? "activa" : ""}" data-tab="odc"><i class="fa-solid fa-dungeon"></i> La ODC: Baclite e Infierno Verde</button>
      </nav>

      <section class="mr-wos-panel ${this.pestana === "ordenes" ? "visible" : ""}" data-panel="ordenes">
        <div class="mr-wos-barra-filtros">
          <input type="search" name="filtroTexto" placeholder="Buscar por nombre, estación (Absalom, Utpala, ODC…), delito o etiqueta…" value="${esc(this.filtroTexto)}" />
          <select name="filtroBL">
            <option value="0" ${this.filtroBL === 0 ? "selected" : ""}>Todos los Niveles (BL 1–10)</option>
            ${Object.values(NIVELES_BL).map(b => `<option value="${b.bl}" ${this.filtroBL === b.bl ? "selected" : ""}>BL:${b.bl} (${b.vivo / 1000}kcr)</option>`).join("")}
          </select>
          <button type="button" data-acc="orden-azar"><i class="fa-solid fa-shuffle"></i> Al azar (1d100)</button>
        </div>

        <div class="mr-wos-maestro-detalle">
          <div class="mr-wos-lista-ordenes">
            ${filtradas.map(o => `
              <button type="button" class="mr-wos-item-orden ${o.num === actual?.num ? "seleccionada" : ""}" data-select-orden="${o.num}">
                <span class="mr-wos-num">#${String(o.num).padStart(2, "0")}</span>
                <span class="mr-wos-nom">${esc(o.titulo)}</span>
                <span class="mr-wos-bl-tag">BL:${o.bl}</span>
              </button>
            `).join("")}
          </div>

          ${actual ? `
          <div class="mr-wos-detalle-orden">
            <div class="mr-wos-cartel">
              <div class="mr-wos-cartel-foto">
                <img src="${esc(actual.img)}" alt="${esc(actual.titulo)}" />
                <div class="mr-wos-sello">BL:${actual.bl} · ${esc(actual.seBusca.toUpperCase())}</div>
                <div class="mr-wos-cod">CÓD. ${esc(actual.codigo)} · PÁG. ${actual.pagina}</div>
              </div>
              <div class="mr-wos-cartel-datos">
                <h3>ORDEN #${String(actual.num).padStart(2, "0")} · ${esc(actual.titulo)}</h3>
                <blockquote class="mr-wos-anuncio">${esc(actual.anuncio)}</blockquote>
                <table class="mr-wos-tabla">
                  <tbody>
                    <tr><th>Nivel</th><td><strong>BL:${actual.bl}</strong> (${esc(actual.etiquetas)})</td><th>Se busca</th><td><strong>${esc(actual.seBusca)}</strong></td></tr>
                    <tr><th>Delito</th><td>${esc(actual.delito)}</td><th>Recompensa</th><td><strong>${esc(actual.pago)}</strong></td></tr>
                    <tr><th>Cliente</th><td>${esc(actual.cliente)}</td><th>Entrega</th><td>${esc(actual.entrega)}</td></tr>
                    <tr><th>Paradero</th><td colspan="3">${esc(actual.paradero)}</td></tr>
                  </tbody>
                </table>
                <div class="mr-wos-acciones-orden">
                  <button type="button" data-acc="publicar-cartel" data-num="${actual.num}"><i class="fa-solid fa-bullhorn"></i> Mostrar Cartel (Sin spoilers)</button>
                  <button type="button" data-acc="abrir-diario-orden" data-num="${actual.num}"><i class="fa-solid fa-book-open"></i> Informe del Guardián</button>
                  <button type="button" data-acc="abrir-actor-orden" data-num="${actual.num}"><i class="fa-solid fa-user-crosshairs"></i> Abrir / Importar Objetivo</button>
                </div>
              </div>
            </div>
            <div class="mr-wos-resumen-pub">
              <h4>Informe público para la tripulación</h4>
              <p>${esc(actual.informe)}</p>
            </div>
          </div>` : ""}
        </div>
      </section>

      <section class="mr-wos-panel ${this.pestana === "generador" ? "visible" : ""}" data-panel="generador">
        <div class="mr-wos-grid-2">
          <div class="mr-wos-caja">
            <h3><i class="fa-solid fa-wand-magic-sparkles"></i> Generador de Órdenes de Busca (Págs. 20–23)</h3>
            <p>Genera un contrato nuevo combinando tipo de objetivo, delito, complicación oculta y recompensa según su Nivel de Busca (BL).</p>
            <div class="mr-wos-fila-form">
              <label>Nivel de Busca (BL 1–10)</label>
              <input type="number" name="genBL" min="1" max="10" value="3" />
              <select name="genCondicion">
                <option value="vivo">Se busca: VIVO (100%)</option>
                <option value="muerto">Se busca: MUERTO (50%)</option>
              </select>
            </div>
            <div class="mr-wos-acciones-orden">
              <button type="button" data-acc="generar-contrato"><i class="fa-solid fa-dice-d20"></i> Generar Contrato y Publicar en Chat</button>
            </div>
          </div>

          <div class="mr-wos-caja">
            <h3><i class="fa-solid fa-magnifying-glass-location"></i> Localizar Objetivos y Oráculo BL (Págs. 16–19)</h3>
            <p>Tira una fuente de rastreo (listas de pasajeros, terminales de venta, datos forenses, antecedentes o cómplices) o consulta la regla de oro del BL (<code>1d10 ≤ BL</code>).</p>
            <div class="mr-wos-fila-form">
              <label>BL del objetivo</label>
              <input type="number" name="rastreoBL" min="1" max="10" value="${actual?.bl || 3}" />
            </div>
            <div class="mr-wos-acciones-orden">
              <button type="button" data-acc="tirar-rastreo"><i class="fa-solid fa-compass"></i> Tirar Pista de Rastreo</button>
              <button type="button" data-acc="tirar-oraculo-bl"><i class="fa-solid fa-dice-d10"></i> Oráculo BL (1d10 ≤ BL)</button>
            </div>
          </div>
        </div>
      </section>

      <section class="mr-wos-panel ${this.pestana === "castigo" ? "visible" : ""}" data-panel="castigo">
        <div class="mr-wos-grid-2">
          <div class="mr-wos-caja">
            <h3><i class="fa-solid fa-fingerprint"></i> Delitos de Jugadores y Juicio (Págs. 224–228)</h3>
            <p>Nivel de Busca actual de la tripulación: <strong>BL:${blGrupo}</strong>. Elige la prueba más sólida dejada en la escena y tira <code>1d10</code>.</p>
            <div class="mr-wos-fila-form">
              <label>Prueba dejada</label>
              <select name="nivelPrueba">
                ${PRUEBAS_DELITO.map(p => `<option value="${p.nivel}" ${p.nivel === 3 ? "selected" : ""}>${p.nivel}. ${esc(p.nombre)}</option>`).join("")}
              </select>
            </div>
            <div class="mr-wos-fila-form">
              <label>BL del delito cometido</label>
              <input type="number" name="blDelito" min="1" max="10" value="3" />
            </div>
            <div class="mr-wos-acciones-orden">
              <button type="button" data-acc="evaluar-delito"><i class="fa-solid fa-scale-balanced"></i> Comprobar Identificación (1d10)</button>
              <button type="button" data-acc="celebrar-juicio"><i class="fa-solid fa-gavel"></i> Dictar Sentencia / Condena ODC</button>
            </div>
          </div>

          <div class="mr-wos-caja">
            <h3><i class="fa-solid fa-skull-crossbones"></i> Los 10 Cazarrecompensas Rivales (Págs. 229–249)</h3>
            <p>Despacha uno de los 10 cazarrecompensas con nombre propio (<em>La Langosta, Assassin Kult, Veteranos, Ivo Salomon, Taskr, Emira Churchill, Alf Moss, Edgars Crismondi, Amaruq Borges, Sr. Bichos</em>).</p>
            <div class="mr-wos-acciones-orden">
              <button type="button" data-acc="despachar-cazador"><i class="fa-solid fa-user-ninja"></i> Tirar Cazador Rival y Táctica (1d10 + 1d5)</button>
              <button type="button" data-acc="modelo-policial"><i class="fa-solid fa-shield-halved"></i> Modelo de Fuerzas del Orden (1d10)</button>
            </div>
          </div>
        </div>
      </section>

      <section class="mr-wos-panel ${this.pestana === "odc" ? "activa visible" : ""}" data-panel="odc">
        <div class="mr-wos-grid-2">
          <div class="mr-wos-caja">
            <h3><i class="fa-solid fa-building-lock"></i> La ODC: Baclite — Sobornos, Rumores y Bandas</h3>
            <p>Para que un miembro del personal (<code>S YY/XX</code>) acepte un soborno hay que sacar menos que su valor de <strong>Soborno</strong> en <code>1d100</code>.</p>
            <div class="mr-wos-fila-form">
              <label>Umbral de Soborno del funcionario (%)</label>
              <input type="number" name="umbralSoborno" min="1" max="100" value="45" />
              <label>Bono por azúcar/créditos</label>
              <input type="number" name="bonoSoborno" min="-40" max="40" value="0" />
            </div>
            <div class="mr-wos-acciones-orden">
              <button type="button" data-acc="tirar-soborno"><i class="fa-solid fa-hand-holding-dollar"></i> Intentar Soborno (1d100)</button>
              <button type="button" data-acc="tirar-rumor-odc"><i class="fa-solid fa-comments"></i> Rumor de Presos (1d10)</button>
            </div>
            <hr>
            <h4>Reputación en la Prisión ODC (Pág. 268)</h4>
            <div class="mr-wos-rep-grid">
              <label>23 Arms <input type="number" data-rep="arms23" value="${n(repODC.arms23, 0)}" /></label>
              <label>Sindicato Stratemeyer <input type="number" data-rep="stratemeyer" value="${n(repODC.stratemeyer, 0)}" /></label>
              <label>Sindicato de Presos <input type="number" data-rep="sindicato" value="${n(repODC.sindicato, 0)}" /></label>
              <label>Funcionarios CO <input type="number" data-rep="guardias" value="${n(repODC.guardias, 0)}" /></label>
            </div>
          </div>

          <div class="mr-wos-caja">
            <h3><i class="fa-solid fa-tree"></i> Fuga por el Infierno Verde de Offit (Págs. 304–310)</h3>
            <p>Simula una jornada de travesía bajo el dosel de Offit: tira encuentro diario (<code>1d10</code>), franja horaria (<code>1d10</code>) y recolección de fruta o bayas sin identificar.</p>
            <div class="mr-wos-acciones-orden">
              <button type="button" data-acc="dia-infierno-verde"><i class="fa-solid fa-person-hiking"></i> Simular Día en el Infierno Verde</button>
              <button type="button" data-acc="comer-bayas"><i class="fa-solid fa-apple-whole"></i> Comer Fruta / Bayas (1d10)</button>
              <button type="button" data-acc="encuentro-fauna"><i class="fa-solid fa-paw"></i> Tirar Fauna de Offit (1d6)</button>
            </div>
          </div>
        </div>
      </section>
    `;
  }

  #vincularEventos(root) {
    // Pestañas
    root.querySelectorAll("[data-tab]").forEach(b => {
      b.addEventListener("click", () => {
        this.pestana = b.dataset.tab;
        guardarLocal("terminal.pestana", this.pestana);
        this.render();
      });
    });

    // Filtros
    const inpTxt = root.querySelector('input[name="filtroTexto"]');
    if (inpTxt) {
      inpTxt.addEventListener("input", ev => {
        this.filtroTexto = ev.target.value;
        this.render();
      });
    }
    const selBL = root.querySelector('select[name="filtroBL"]');
    if (selBL) {
      selBL.addEventListener("change", ev => {
        this.filtroBL = Number(ev.target.value) || 0;
        this.render();
      });
    }

    // Selección de orden
    root.querySelectorAll("[data-select-orden]").forEach(b => {
      b.addEventListener("click", () => {
        this.ordenSeleccionada = Number(b.dataset.selectOrden) || 1;
        this.render();
      });
    });

    // Reputación ODC
    root.querySelectorAll("[data-rep]").forEach(inp => {
      inp.addEventListener("change", async () => {
        if (!game.user.isGM) return ui.notifications.warn("Solo el Guardián puede editar la reputación global.");
        const actual = { ...(game.settings.get(MOD, "reputacionODC") || {}) };
        actual[inp.dataset.rep] = n(inp.value, 0);
        await game.settings.set(MOD, "reputacionODC", actual);
      });
    });

    // Acciones
    root.querySelectorAll("[data-acc]").forEach(btn => {
      btn.addEventListener("click", async ev => {
        ev.preventDefault();
        const acc = btn.dataset.acc;
        const ordenes = await cargarIndiceOrdenes();

        if (acc === "orden-azar") {
          const r = await new Roll("1d100").evaluate();
          this.filtroTexto = "";
          this.filtroBL = 0;
          this.ordenSeleccionada = acota(r.total, 1, 100);
          this.render();
          return;
        }

        if (acc === "publicar-cartel") {
          const o = ordenes.find(x => x.num === Number(btn.dataset.num));
          await publicarCartelOrden(o);
          return;
        }

        if (acc === "abrir-diario-orden") {
          const o = ordenes.find(x => x.num === Number(btn.dataset.num));
          if (!o) return;
          const pack = game.packs.get(`${MOD}.ordenes`);
          const doc = await pack?.getDocument(o.diarioId);
          if (doc) doc.sheet.render(true, { pageId: o.paginaId });
          return;
        }

        if (acc === "abrir-actor-orden") {
          const o = ordenes.find(x => x.num === Number(btn.dataset.num));
          if (!o) return;
          let actor = game.actors.get(o.actorId);
          if (!actor) {
            const pack = game.packs.get(`${MOD}.objetivos`);
            const doc = await pack?.getDocument(o.actorId);
            if (doc && game.user.isGM) actor = await Actor.create(doc.toObject(), { keepId: true });
            else if (doc) return doc.sheet.render(true);
          }
          actor?.sheet?.render(true);
          return;
        }

        if (acc === "generar-contrato") {
          const bl = n(root.querySelector('input[name="genBL"]')?.value, 3);
          const cond = root.querySelector('select[name="genCondicion"]')?.value || "vivo";
          await ejecutarMacroGenerarOrden(bl, cond);
          return;
        }

        if (acc === "tirar-rastreo") {
          await ejecutarMacroRastrear();
          return;
        }

        if (acc === "tirar-oraculo-bl") {
          const bl = n(root.querySelector('input[name="rastreoBL"]')?.value, 3);
          const r = await new Roll("1d10").evaluate();
          const res = oraculoBL(bl, r.total);
          await publicarTarjeta(`Oráculo BL:${bl}`, `1d10 = ${r.total}`, `<p>${esc(res.resumen)}</p>`);
          return;
        }

        if (acc === "evaluar-delito") {
          const nivelPrueba = n(root.querySelector('select[name="nivelPrueba"]')?.value, 3);
          const blDelito = n(root.querySelector('input[name="blDelito"]')?.value, 3);
          await ejecutarMacroDelito(nivelPrueba, blDelito);
          return;
        }

        if (acc === "celebrar-juicio") {
          const bl = n(game.settings.get(MOD, "blGrupo"), 3) || n(root.querySelector('input[name="blDelito"]')?.value, 3);
          const r = await new Roll("1d10").evaluate();
          const sent = calcularSentencia(bl, r.total);
          await publicarTarjeta(
            `Tribunal del Sector · Sentencia (BL:${bl})`,
            `Defensa 1d10 = ${r.total}`,
            `<p><strong>Fallo judicial:</strong> ${esc(sent.destino)}</p>
             ${sent.multaKcr ? `<p><strong>Multa alternativa:</strong> ${sent.multaKcr}kcr</p>` : ""}
             ${sent.aniosODC ? `<p><strong>Condena en La ODC (Baclite):</strong> ${sent.aniosODC} años</p>` : ""}`,
          );
          return;
        }

        if (acc === "despachar-cazador") {
          await tirarTablaCompendio("cazadores-rivales", "Cazarrecompensas Rival en Ruta");
          return;
        }

        if (acc === "modelo-policial") {
          await tirarTablaCompendio("fuerzas-orden", "Fuerzas del Orden Locales");
          return;
        }

        if (acc === "tirar-soborno") {
          const umbral = n(root.querySelector('input[name="umbralSoborno"]')?.value, 45);
          const bono = n(root.querySelector('input[name="bonoSoborno"]')?.value, 0);
          await ejecutarMacroSoborno(umbral, bono);
          return;
        }

        if (acc === "tirar-rumor-odc") {
          await tirarTablaCompendio("odc-rumores", "Rumor entre Reclusos de la ODC");
          return;
        }

        if (acc === "dia-infierno-verde") {
          await ejecutarMacroInfiernoVerde(false);
          return;
        }

        if (acc === "comer-bayas") {
          await ejecutarMacroInfiernoVerde(true);
          return;
        }

        if (acc === "encuentro-fauna") {
          await tirarTablaCompendio("fauna-offit", "Encuentro con Fauna de Offit");
        }
      });
    });
  }
}

async function tirarTablaCompendio(claveTabla, tituloFallback) {
  const pack = game.packs.get(`${MOD}.tablas`);
  if (!pack) return;
  const docs = await pack.getDocuments();
  const tabla = docs.find(t => t.flags?.[MOD]?.clave === claveTabla);
  if (!tabla) return;
  const draw = await tabla.roll();
  const texto = draw.results?.map(r => r.text).join("<br>") || "";
  await publicarTarjeta(tabla.name || tituloFallback, `Tirada ${draw.roll?.total ?? ""}`, `<p>${esc(texto)}</p>`);
}

export async function ejecutarMacroGenerarOrden(bl = null, condicion = "vivo") {
  const pack = game.packs.get(`${MOD}.tablas`);
  const docs = (await pack?.getDocuments()) || [];
  const tirarTexto = async clave => {
    const t = docs.find(x => x.flags?.[MOD]?.clave === clave);
    if (!t) return "";
    const d = await t.roll();
    return d.results?.[0]?.text || "";
  };
  const nivel = bl || (await new Roll("1d6 + 1").evaluate()).total;
  const obj = await tirarTexto("generador-objetivo");
  const del = await tirarTexto("generador-delito");
  const comp = await tirarTexto("generador-complicacion");
  const rec = calcularRecompensaBL(nivel, condicion);

  await publicarTarjeta(
    `Contrato Generado · ${rec.etiqueta}`,
    `Pago: ${rec.formato} (${condicion.toUpperCase()})`,
    `<p><strong>Objetivo:</strong> ${esc(obj)}</p>
     <p><strong>Delito:</strong> ${esc(del)}</p>
     <p><strong>Recompensa:</strong> ${esc(rec.formato)} (${esc(condicion.toUpperCase())})</p>
     <hr>
     <p><em>Complicación para el Guardián:</em> ${esc(comp)}</p>`,
    `<button type="button" data-mrwos-chat="oraculo-bl" data-bl="${rec.bl}"><i class="fa-solid fa-dice-d10"></i> Oráculo BL:${rec.bl}</button>`,
  );
}

export async function ejecutarMacroRastrear() {
  await tirarTablaCompendio("rastreo-fuentes", "Localizar Objetivo · Fuente de Información");
}

export async function ejecutarMacroDelito(nivelPrueba = 3, blDelito = 3) {
  const r = await new Roll("1d10").evaluate();
  const blActual = n(game.settings.get(MOD, "blGrupo"), 0);
  const res = evaluarDelitoJugador({ nivelPrueba, blDelito, tiradaD10: r.total, blActual });
  const btn = res.identificado
    ? `<button type="button" data-mrwos-chat="aplicar-bl-grupo" data-bl="${res.blNuevo}"><i class="fa-solid fa-triangle-exclamation"></i> Fijar BL:${res.blNuevo} a la Tripulación</button>`
    : "";
  await publicarTarjeta("Investigación de Delito de Jugadores", `1d10 = ${r.total} (Prueba Nv.${nivelPrueba})`, `<p>${esc(res.resumen)}</p>`, btn);
}

export async function ejecutarMacroSoborno(umbralSoborno = 45, bonoOferta = 0) {
  const r = await new Roll("1d100 - 1").evaluate();
  const res = evaluarSobornoODC({ umbralSoborno, tiradaD100: r.total, bonoOferta });
  await publicarTarjeta("Intento de Soborno · Personal ODC", `d100 = ${res.tirada} vs ${res.objetivo}`, `<p>${esc(res.resumen)}</p>`);
}

export async function ejecutarMacroInfiernoVerde(soloFruta = false) {
  const rEnc = await new Roll("1d10 - 1").evaluate();
  const rHr = await new Roll("1d10 - 1").evaluate();
  const rFr = soloFruta ? await new Roll("1d10 - 1").evaluate() : null;
  const res = simularDiaInfiernoVerde({ dEncuentro: rEnc.total, dHora: rHr.total, dFruta: rFr?.total ?? null });

  const cuerpo = soloFruta
    ? `<p><strong>Recolección de fruta / bayas en Offit:</strong> ${esc(res.fruta)}</p>`
    : `<p><strong>Momento:</strong> ${esc(res.franja)}</p><p><strong>Suceso en la jungla:</strong> ${esc(res.encuentro)}</p>`;
  const btn = `<button type="button" data-mrwos-chat="salvacion-cuerpo"><i class="fa-solid fa-heart-pulse"></i> Salvación de Cuerpo</button>
               <button type="button" data-mrwos-chat="estres-mio"><i class="fa-solid fa-bolt"></i> +1 Estrés</button>`;
  await publicarTarjeta("Supervivencia en el Infierno Verde (Offit)", soloFruta ? "Forrajeo" : res.franja, cuerpo, btn);
}

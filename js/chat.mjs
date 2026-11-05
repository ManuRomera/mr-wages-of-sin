/**
 * Tarjetas de chat interactivas al estilo nativo de Mothership (`.mosh .rollcontainer`) y sincronización por socket.
 */
import { MOD, aplicarModoMensaje } from "./compat.mjs";
import { oraculoBL } from "./core/reglas.mjs";

const esc = s => foundry.utils.escapeHTML(String(s ?? ""));
const n = (v, d = 0) => (Number.isFinite(Number(v)) ? Number(v) : d);
const soyGM = () => game.user === game.users.activeGM;

export async function publicarTarjeta(titulo, subtitulo, cuerpoHtml, botonesHtml = "", flagsExtra = {}) {
  const content = `
  <div class="mosh mr-wos-chat">
    <div class="rollcontainer">
      <div class="flexrow" style="align-items:center;gap:8px;margin-bottom:6px;">
        <span class="mr-wos-pill">${esc(subtitulo || "WAGES OF SIN")}</span>
        <strong style="font-size:1.05em;">${esc(titulo)}</strong>
      </div>
      <div class="mr-wos-chat-cuerpo">${cuerpoHtml}</div>
      ${botonesHtml ? `<div class="mr-wos-chat-botones">${botonesHtml}</div>` : ""}
    </div>
  </div>`;
  const msgData = aplicarModoMensaje({
    speaker: ChatMessage.getSpeaker(),
    content,
    flags: { [MOD]: { estado: {}, ...flagsExtra } },
  });
  return ChatMessage.create(msgData);
}

export async function publicarCartelOrden(orden) {
  if (!orden) return;
  const cuerpo = `
    <div class="mr-wos-chat-cartel">
      <img src="${esc(orden.img)}" alt="${esc(orden.titulo)}" />
      <div>
        <div class="mr-wos-sello-chat">ORDEN ${String(orden.num).padStart(2, "0")} · BL:${n(orden.bl, 1)} · ${esc(orden.seBusca.toUpperCase())}</div>
        <blockquote style="margin:6px 0;font-style:italic;">${esc(orden.anuncio)}</blockquote>
        <p style="margin:4px 0;"><strong>Delito:</strong> ${esc(orden.delito)}<br>
        <strong>Pago:</strong> ${esc(orden.pago)}${orden.prima ? ` (prima: ${esc(orden.prima)})` : ""}<br>
        <strong>Cliente:</strong> ${esc(orden.cliente)}<br>
        <strong>Entrega:</strong> ${esc(orden.entrega)}</p>
      </div>
    </div>
    `;
  const botones = `
    <button type="button" data-mrwos-chat="oraculo-bl" data-bl="${n(orden.bl, 1)}"><i class="fa-solid fa-dice-d10"></i> Oráculo BL:${n(orden.bl, 1)}</button>`;
  return publicarTarjeta(`SE BUSCA · ${orden.titulo}`, (orden.codigo ? `CÓD. ${orden.codigo}` : "SE BUSCA"), cuerpo, botones, { orden: orden.num, bl: orden.bl });
}

export function registrarEventosChat() {
  Hooks.on("renderChatMessageHTML", (_message, html) => {
    html.querySelectorAll("[data-mrwos-chat]").forEach(btn => {
      btn.addEventListener("click", async ev => {
        ev.preventDefault();
        if (btn.dataset.mrwosChat === "oraculo-bl") {
          const bl = n(btn.dataset.bl, 3);
          const roll = await new Roll("1d10").evaluate();
          const res = oraculoBL(bl, roll.total);
          await publicarTarjeta(`Oráculo de Nivel de Recompensa (BL:${bl})`, `1d10 = ${roll.total}`, `<p>${esc(res.resumen)}</p>`);
        }
      });
    });
  });
}

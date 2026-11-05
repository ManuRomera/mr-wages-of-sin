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
        <div class="mr-wos-sello-chat">ORDEN #${String(orden.num).padStart(2, "0")} · BL:${n(orden.bl, 1)} · ${esc(orden.seBusca.toUpperCase())}</div>
        <blockquote style="margin:6px 0;font-style:italic;">${esc(orden.anuncio)}</blockquote>
        <p style="margin:4px 0;"><strong>Delito:</strong> ${esc(orden.delito)}<br>
        <strong>Pago:</strong> ${esc(orden.pago)} (${esc(orden.prima)})<br>
        <strong>Cliente:</strong> ${esc(orden.cliente)}<br>
        <strong>Entrega:</strong> ${esc(orden.entrega)}<br>
        <strong>Último paradero:</strong> ${esc(orden.paradero)}</p>
      </div>
    </div>
    <p style="margin-top:6px;font-size:0.92em;">${esc(orden.informe)}</p>`;
  const botones = `
    <button type="button" data-mrwos-chat="oraculo-bl" data-bl="${n(orden.bl, 1)}"><i class="fa-solid fa-dice-d10"></i> Oráculo BL:${n(orden.bl, 1)}</button>
    <button type="button" data-mrwos-chat="estres-mio"><i class="fa-solid fa-bolt"></i> +1 Estrés (Mío)</button>`;
  return publicarTarjeta(`SE BUSCA · ${orden.titulo}`, `CÓD. ${orden.codigo}`, cuerpo, botones, { orden: orden.num, bl: orden.bl });
}

export function registrarEventosChat() {
  Hooks.on("renderChatMessageHTML", (message, html) => {
    html.querySelectorAll("[data-mrwos-chat]").forEach(btn => {
      btn.addEventListener("click", async ev => {
        ev.preventDefault();
        const acc = btn.dataset.mrwosChat;

        if (acc === "oraculo-bl") {
          const bl = n(btn.dataset.bl, 3);
          const roll = await new Roll("1d10").evaluate();
          const res = oraculoBL(bl, roll.total);
          await publicarTarjeta(
            `Oráculo de Nivel de Busca (BL:${bl})`,
            `1d10 = ${roll.total}`,
            `<p>${esc(res.resumen)}</p>`,
          );
          return;
        }

        if (acc === "estres-mio") {
          const pj = canvas?.tokens?.controlled?.[0]?.actor || game.user.character;
          if (!pj) return ui.notifications.warn("Selecciona tu token o asigna tu personaje.");
          if (typeof pj.modifyActor === "function") {
            await pj.modifyActor("system.other.stress.value", 1, null, true);
          } else {
            const actual = n(pj.system?.other?.stress?.value, 2);
            await pj.update({ "system.other.stress.value": actual + 1 });
            ui.notifications.info(`${pj.name}: Estrés +1 (${actual + 1}).`);
          }
          return;
        }

        if (acc === "aplicar-bl-grupo") {
          const nuevo = n(btn.dataset.bl, 1);
          if (game.user.isGM) {
            await game.settings.set(MOD, "blGrupo", nuevo);
            ui.notifications.info(`Nivel de Busca de la tripulación actualizado a BL:${nuevo}.`);
          } else {
            game.socket.emit(`module.${MOD}`, { tipo: "setBLGrupo", bl: nuevo });
            ui.notifications.info(`Solicitado al Guardián actualizar BL:${nuevo}.`);
          }
          btn.disabled = true;
        }

        if (acc === "salvacion-cuerpo") {
          const pj = canvas?.tokens?.controlled?.[0]?.actor || game.user.character;
          if (!pj) return ui.notifications.warn("Selecciona tu token para tirar Salvación de Cuerpo.");
          if (typeof pj.rollCheck === "function") {
            await pj.rollCheck(null, "low", "body", null, null, null);
          } else {
            const obj = n(pj.system?.stats?.body?.value, 30);
            const r = await new Roll("1d100").evaluate();
            const ok = r.total < obj;
            await publicarTarjeta(
              `${pj.name} · Salvación de Cuerpo`,
              `${r.total} vs ${obj}`,
              `<p>${ok ? "<strong>Éxito:</strong> vomitas la fruta tóxica y solo guardas reposo 1 día." : `<strong>Fallo por ${r.total - obj}:</strong> sufres daño y fiebre selvática en el Infierno Verde.`}</p>`,
            );
          }
        }
      });
    });
  });

  Hooks.once("ready", () => {
    game.socket.on(`module.${MOD}`, async payload => {
      if (!soyGM() || !payload) return;
      if (payload.tipo === "setBLGrupo") {
        await game.settings.set(MOD, "blGrupo", n(payload.bl, 1));
      }
    });
  });
}

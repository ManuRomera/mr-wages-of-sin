/**
 * Capa de compatibilidad unificada para Foundry VTT v13 y v14 · MR- Wages of Sin.
 * Ningún otro archivo pregunta por la versión de Foundry.
 */

export const MOD = "mr-wages-of-sin";

/** Aplica el modo de mensaje/tirada actual tanto en v13 como en v14. */
export function aplicarModoMensaje(datos = {}, modo = null) {
  const m = modo || game.settings?.get?.("core", "messageMode") || game.settings?.get?.("core", "rollMode") || CONST.DICE_ROLL_MODES?.PUBLIC || "public";
  if (typeof ChatMessage.applyMode === "function") return ChatMessage.applyMode(datos, m);
  if (typeof ChatMessage.applyRollMode === "function") return ChatMessage.applyRollMode(datos, m);
  return datos;
}

/** Registra una herramienta en los controles de escena de Tokens compatible con v13 (objeto) y v14/v12 (array). */
export function insertarControlEscena(controls, tool) {
  if (Array.isArray(controls)) {
    const grupo = controls.find(c => c.name === "token" || c.name === "tokens");
    if (!grupo) return;
    if (Array.isArray(grupo.tools) && !grupo.tools.some(t => t.name === tool.name)) grupo.tools.push(tool);
    return;
  }
  const grupo = controls?.tokens || controls?.token;
  if (!grupo?.tools) return;
  if (Array.isArray(grupo.tools)) {
    if (!grupo.tools.some(t => t.name === tool.name)) grupo.tools.push(tool);
  } else {
    grupo.tools[tool.name] = tool;
  }
}

/**
 * Crédito discreto MR- en la pestaña de Ajustes de Foundry VTT.
 */
export function registrarCreditosMR() {
  Hooks.on("renderSettings", (_app, html) => {
    const raiz = html instanceof HTMLElement ? html : html?.[0];
    if (!raiz || raiz.querySelector(".mr-credits-badge")) return;
    const bloque = document.createElement("div");
    bloque.className = "mr-credits-badge";
    bloque.innerHTML = `<p style="text-align:center;opacity:0.75;font-size:11px;margin:6px 0;">
      <strong>MR- · Manu Romera</strong> · <a href="https://github.com/ManuRomera/mr-wages-of-sin" target="_blank" rel="noopener">Wages of Sin (ES)</a>
    </p>`;
    raiz.append(bloque);
  });
}

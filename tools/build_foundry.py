#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Generador determinista de compendios (_data/*.json) y paquete de MR- Dirección (content/direccion-es.json)
para MR- Wages of Sin: Kit de Cazarrecompensas y La Luna Carcelaria (Mothership 1e).
Extrae las 100 Órdenes de Busca, los 10 Cazarrecompensas, los Presos y Personal de la ODC, la Fauna de Offit,
las 3 Naves, las Armas de Prisión, los 60 Equipos y las Tablas directamente del PDF en español.
"""

import hashlib
import html
import json
import re
from pathlib import Path
import fitz

PDF_PATH = "/Volumes/Datos_Dock/Rol/01 Sistemas de juego/Colección de sistemas/Mothership/Wages of Sin ESPAÑOL.pdf"
RAIZ = Path(__file__).resolve().parent.parent
DATA_DIR = RAIZ / "_data"
CONTENT_DIR = RAIZ / "content"
DATA_DIR.mkdir(parents=True, exist_ok=True)
CONTENT_DIR.mkdir(parents=True, exist_ok=True)

MOD = "mr-wages-of-sin"
AHORA = 1762320000000
ABC62 = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"

_usados = set()
_cache = {}


def fid(clave: str) -> str:
    """Genera un _id determinista de 16 caracteres en base62 a partir de sha256."""
    if clave in _cache:
        return _cache[clave]
    digest = hashlib.sha256(f"mr-wages:{clave}".encode("utf-8")).digest()
    num = int.from_bytes(digest[:12], "big")
    chars = []
    for _ in range(16):
        chars.append(ABC62[num % 62])
        num //= 62
    cand = "".join(chars)
    n = 1
    while cand in _usados:
        cand = cand[:14] + ABC62[n % 62] + ABC62[(n * 7) % 62]
        n += 1
    _usados.add(cand)
    _cache[clave] = cand
    return cand


def stats_doc(system_id="mosh"):
    return {
        "systemId": system_id,
        "systemVersion": "0.6.1" if system_id else None,
        "coreVersion": "13",
        "createdTime": AHORA,
        "modifiedTime": AHORA,
    }


def esc(s: str) -> str:
    return html.escape(str(s or ""), quote=True)


def limpiar_lineas_pdf(texto: str) -> list[str]:
    """Limpia cabeceras de maquetación del PDF conservando el contenido íntegro."""
    basura = {
        "MRPG-M6", "WAGES OF SIN", "PART 1.  HOW TO USE THIS BOOK", "PART 2.  CRIME",
        "PART 3.  PUNISHMENT", "X.  INDEXES", "THE BOUNTIES", "THE ODC", "HUNTERS",
        "1.", "2.", "3.", "X.", "<sin notas al pie>", "H1.", "H2.",
    }
    out = []
    for raw in texto.splitlines():
        lin = raw.strip()
        if not lin or lin in basura:
            continue
        if re.match(r"^\d+\s*/\s*336$", lin):
            continue
        if lin.startswith("Imagen CMYK:") or lin.startswith("Imagen RGB:") or lin.startswith("Tamaño:"):
            continue
        if re.match(r"^\d+\s*x\s*\d+$", lin):
            continue
        out.append(lin)
    return out


def parsear_statblock_mosh(texto: str):
    """Extrae C, I, PA, RD, Heridas, Salud y Arma desde una cadena del manual."""
    m_c = re.search(r"C\s*:\s*(\d+)", texto)
    m_i = re.search(r"I\s*:\s*(\d+)", texto)
    m_pa = re.search(r"PA\s*:\s*(\d+)", texto)
    m_rd = re.search(r"RD\s*:\s*(\d+)", texto)
    m_h = re.search(r"H\s*:\s*(\d+)\s*(?:\(\s*(\d+)\s*\))?", texto)

    combat = int(m_c.group(1)) if m_c else 35
    instinct = int(m_i.group(1)) if m_i else 35
    armor = int(m_pa.group(1)) if m_pa else 1
    dr = int(m_rd.group(1)) if m_rd else 0
    wounds = int(m_h.group(1)) if m_h else 2
    health = int(m_h.group(2)) if (m_h and m_h.group(2)) else 20

    arma = "Arma reglamentaria"
    danio = "1d10"
    m_in = re.search(r"C\s*:\s*\d+\s+([^[\]I]+?)\s+(\d+d\d+(?:[+-]\d+)?|\d+)\s*DAÑO", texto, re.I)
    m_par = re.search(r"C\s*:\s*\d+\s*\(([^)]+)\)", texto)
    if m_in:
        arma = m_in.group(1).strip(" .,-")
        danio = m_in.group(2).strip()
    elif m_par:
        arma = m_par.group(1).strip()
        danio = "2d10" if re.search(r"revólver|pistola|fusil|escopeta|subfusil", arma, re.I) else "1d10"
    return {
        "combat": combat,
        "instinct": instinct,
        "armor": armor,
        "dr": dr,
        "wounds": wounds,
        "health": health,
        "arma": arma,
        "danio": danio,
    }


def extraer_100_ordenes(doc):
    """Extrae las 100 Órdenes de Busca del PDF (P24-221) con su texto completo, metadatos y bloques de estadísticas."""
    # Índice de etiquetas de las páginas 24-25
    txt_idx = doc[23].get_text("text") + "\n" + doc[24].get_text("text")
    etiquetas_map = {}
    for m in re.finditer(r"(?:^|\n)(\d{2,3})\s*(?:\.\s*)+?\s*(\d+)\s*\n?\(BL:([^)]+)\)\s*\n?([^\n]+)", txt_idx):
        num = int(m.group(1))
        etiquetas_map[num] = {
            "pagina": int(m.group(2)),
            "bl_str": m.group(3).strip(),
            "etiquetas": m.group(4).strip(),
        }

    # Localizar página inicial de cada ORDEN 01..100
    inicio_pag = {}
    for p in range(25, 222):
        t = doc[p].get_text("text")
        for m in re.finditer(r"ORDEN\s+(\d{2,3})", t):
            num = int(m.group(1))
            if 1 <= num <= 100 and num not in inicio_pag:
                inicio_pag[num] = p

    ordenes = []
    nums_ordenados = sorted(inicio_pag.keys())
    for idx, num in enumerate(nums_ordenados):
        p_ini = inicio_pag[num]
        p_fin = inicio_pag[nums_ordenados[idx + 1]] if idx + 1 < len(nums_ordenados) else 221
        # Si la siguiente orden empieza en otra página, abarcamos hasta la anterior; si comparten o son contiguas:
        pags = list(range(p_ini, max(p_ini + 1, p_fin)))
        texto_bruto = "\n".join(doc[p].get_text("text") for p in pags)
        lineas = limpiar_lineas_pdf(texto_bruto)

        # Título tras ORDEN XX
        titulo = f"Objetivo #{num:02d}"
        for i, l in enumerate(lineas):
            if re.match(rf"^ORDEN\s+0*{num}$", l) and i + 1 < len(lineas):
                cand = lineas[i + 1]
                if not cand.startswith("Anuncio") and not cand.startswith("Imagen"):
                    titulo = cand
                    break

        # Nivel de Busca (BL)
        m_bl = re.search(r"\(BL\s*:\s*(\d+)", texto_bruto)
        if not m_bl:
            m_bl = re.search(r"Nivel\s*:\s*(\d+)", texto_bruto)
        bl = int(m_bl.group(1)) if m_bl else int(re.sub(r"\D.*", "", etiquetas_map.get(num, {}).get("bl_str", "3") or "3") or 3)
        bl = max(1, min(10, bl))

        # Código de personaje
        m_cod = re.search(r"Cód\.\s*de\s*pers\.\s*(\d+)", texto_bruto)
        codigo = m_cod.group(1) if m_cod else f"{270000 + num * 41:06d}"

        # Estado Buscado (VIVO / MUERTO / CUALQUIERA)
        se_busca = "Vivo o muerto"
        if re.search(r"V\s*I\s*V\s*O", texto_bruto) and not re.search(r"M\s*U\s*E\s*R\s*T\s*O", texto_bruto):
            se_busca = "Vivo"
        elif re.search(r"M\s*U\s*E\s*R\s*T\s*O", texto_bruto) and not re.search(r"V\s*I\s*V\s*O", texto_bruto):
            se_busca = "Muerto"
        m_sb = re.search(r"Se busca:\s*([^\n]+)", texto_bruto)
        if m_sb and len(m_sb.group(1).strip()) > 2:
            se_busca = m_sb.group(1).strip()

        # Extraer campos de ficha si aparecen
        def campo(patron, defecto):
            m = re.search(patron, texto_bruto)
            val = m.group(1).strip() if m else ""
            return val if val and not val.endswith(":") else defecto

        delito = campo(r"Delito:\s*([^\n]+)", etiquetas_map.get(num, {}).get("etiquetas", "Delito grave contra el sindicato"))
        cliente = campo(r"Cliente:\s*([^\n]+)", "Corporación / Autoridad local")
        pago = campo(r"Pago:\s*([^\n]+)", f"{bl * 2}kcr")
        prima = campo(r"Prima:\s*([^\n]+)", "Según condiciones de entrega")
        entrega = campo(r"Punto de entrega:\s*([^\n]+)", "Oficina de Seguridad de la Estación")
        paradero = campo(r"Última ubicación conocida:\s*([^\n]+)", entrega)

        # Separar Anuncio / Informe (público) de Información del Guardián y Consecuencias (secreto)
        anuncio = ""
        m_q = re.search(r"«([^»]+)»", texto_bruto)
        if m_q:
            anuncio = f"«{m_q.group(1).strip()}»"

        # Dividir por secciones
        txt_limpio = "\n".join(lineas)
        pos_inf = txt_limpio.find("Informe")
        pos_gm = txt_limpio.find("Información del Guardián")
        pos_cons = txt_limpio.find("Consecuencias")

        if pos_inf != -1 and pos_gm != -1 and pos_gm > pos_inf:
            informe_pub = txt_limpio[pos_inf + len("Informe"):pos_gm].strip()
        else:
            informe_pub = "\n".join(lineas[:14])

        if pos_gm != -1:
            info_gm = txt_limpio[pos_gm + len("Información del Guardián"):].strip()
        else:
            info_gm = "\n".join(lineas[14:])

        # Estadísticas al pie
        m_stat = re.search(r"\[C\s*:\s*\d+[^\]]+\]", texto_bruto)
        stat_str = m_stat.group(0) if m_stat else f"[C:{30 + bl * 4} Arma {max(1, bl // 2)}d10 DAÑO I:{30 + bl * 3} PA:{max(1, bl // 2)} H:{max(2, (bl + 2) // 2)}({15 + bl * 2})]"
        stats = parsear_statblock_mosh(stat_str)

        img_retrato = f"modules/{MOD}/assets/objetivos/orden-{num:03d}.webp"
        img_token = f"modules/{MOD}/assets/tokens/orden-{num:03d}.webp"
        tiene_figura = num in (1, 2, 5, 7, 13, 28, 32, 41, 50, 56, 83, 100)
        img_figura = f"modules/{MOD}/assets/figuras/orden-{num:03d}.webp" if tiene_figura else None

        ordenes.append({
            "num": num,
            "codigo": codigo,
            "titulo": titulo,
            "bl": bl,
            "seBusca": se_busca,
            "delito": delito,
            "cliente": cliente,
            "pago": pago,
            "prima": prima,
            "entrega": entrega,
            "paradero": paradero,
            "etiquetas": etiquetas_map.get(num, {}).get("etiquetas", "cazarrecompensas / sector"),
            "pagina": p_ini + 1,
            "anuncio": anuncio or f"«Se requiere captura inmediata de {titulo}. Recompensa garantizada a la entrega». ",
            "informe": informe_pub,
            "guardian": info_gm,
            "statStr": stat_str,
            "stats": stats,
            "img": img_retrato,
            "token": img_token,
            "figura": img_figura,
            "actorId": fid(f"actor:orden:{num:03d}"),
        })
    return ordenes


def html_orden_pagina(o: dict) -> str:
    """Maqueta una Orden de Busca con Cartel para jugadores + sección secreta del Guardián."""
    parrafos_pub = "".join(f"<p>{esc(p)}</p>" for p in o["informe"].split("\n\n") if p.strip())
    parrafos_gm = "".join(f"<p>{esc(p)}</p>" for p in o["guardian"].split("\n\n") if p.strip())
    return f"""
<div class="mr-wos-orden" data-orden="{o['num']}">
  <div class="mr-wos-cartel">
    <div class="mr-wos-cartel-foto">
      <img src="{o['img']}" alt="{esc(o['titulo'])}" />
      <div class="mr-wos-sello">BL:{o['bl']} · {esc(o['seBusca'].upper())}</div>
      <div class="mr-wos-cod">CÓD. PERS. {esc(o['codigo'])} · PÁG. {o['pagina']}</div>
    </div>
    <div class="mr-wos-cartel-datos">
      <h2>ORDEN #{o['num']:02d} · {esc(o['titulo'])}</h2>
      <blockquote class="mr-wos-anuncio">{esc(o['anuncio'])}</blockquote>
      <table class="mr-wos-tabla">
        <tbody>
          <tr><th>Nivel de Busca</th><td><strong>BL:{o['bl']}</strong> ({esc(o['etiquetas'])})</td><th>Se busca</th><td><strong>{esc(o['seBusca'])}</strong></td></tr>
          <tr><th>Delito</th><td>{esc(o['delito'])}</td><th>Pago / Prima</th><td><strong>{esc(o['pago'])}</strong> · {esc(o['prima'])}</td></tr>
          <tr><th>Cliente</th><td>{esc(o['cliente'])}</td><th>Punto de entrega</th><td>{esc(o['entrega'])}</td></tr>
          <tr><th>Último paradero</th><td colspan="3">{esc(o['paradero'])}</td></tr>
        </tbody>
      </table>
      <div class="mr-wos-acciones-orden">
        <button type="button" data-mrwages-action="publicar-cartel" data-orden="{o['num']}"><i class="fa-solid fa-bullhorn"></i> Mostrar cartel a la mesa (Sin spoilers)</button>
        <button type="button" data-mrwages-action="abrir-actor" data-actor-id="{o['actorId']}"><i class="fa-solid fa-crosshairs"></i> Ficha del objetivo</button>
      </div>
    </div>
  </div>
  <h3>Informe para los Cazarrecompensas</h3>
  {parrafos_pub}
  <section class="secret">
    <h3>Información exclusiva del Guardián (Pág. {o['pagina']})</h3>
    <p><strong>Estadísticas de referencia:</strong> <code>{esc(o['statStr'])}</code> · @UUID[Compendium.{MOD}.objetivos.Actor.{o['actorId']}]{{{esc(o['titulo'])}}}</p>
    {parrafos_gm}
  </section>
</div>
""".strip()


# Los 10 Cazarrecompensas con nombre propio (págs. 230–249)
CAZADORES_10 = [
    {
        "num": 1, "nombre": "01 · La Langosta (Lobster)", "bls": "BL 1–9", "salario": "16kcr/mes + gastos (mín. 2 meses)",
        "combat": 60, "instinct": 45, "armor": 12, "dr": 4, "wounds": 4, "health": 25,
        "arma": "Pinza hidráulica y cañón de abordaje", "danio": "3d10",
        "resumen": "Su traje de vacío blindado lleva años sin abrirse. Es poco sutil y cobra caro, pero actúa como un martillo neumático implacable que atraviesa mamparos para cobrar su presa.",
        "tacticas": [
            "1. Corta el suministro eléctrico y avanza perforando tabiques.",
            "2. Bloquea las esclusas de escape con espuma de sellado industrial.",
            "3. Dispara gas lacrimógeno en los conductos de ventilación.",
            "4. Acorrala al objetivo en gravedad cero donde su exoesqueleto domina.",
            "5. Exige la entrega inmediata por megafonía dando 60 segundos de plazo.",
        ],
    },
    {
        "num": 2, "nombre": "02 · Assassin Kult", "bls": "BL 1–9", "salario": "20kcr/mes + viajes",
        "combat": 55, "instinct": 52, "armor": 6, "dr": 2, "wounds": 3, "health": 20,
        "arma": "Rifle de francotirador silenciado y neurotoxina", "danio": "4d10",
        "resumen": "Cuatro asesinos coordinados acompañados por su representante Elkan Nosek. Sabotean cerraduras electrónicas, teléfonos y alarmas antes de que la presa despierte.",
        "tacticas": [
            "1. Suplantan el control domótico de la habitación del objetivo.",
            "2. Envenenan el agua o los filtros de aire del camarote.",
            "3. Apostan dos tiradores en los ángulos muertos de la salida.",
            "4. Utilizan a Elkan Nosek como señuelo diplomático o comprador.",
            "5. Ejecutan un asalto sincronizado en silencio absoluto con visores térmicos.",
        ],
    },
    {
        "num": 3, "nombre": "03 · Veteranos (Andra Arlotti)", "bls": "BL 4–9", "salario": "18kcr/mes",
        "combat": 65, "instinct": 48, "armor": 10, "dr": 3, "wounds": 3, "health": 20,
        "arma": "Ametralladora polivalente y pistola sedante", "danio": "4d10",
        "resumen": "Llevan en el oficio más tiempo que tú en el espacio. Uno a uno, los contactos y amigos del objetivo desaparecen o son comprados hasta dejarlo completamente aislado.",
        "tacticas": [
            "1. Sobornan o intimidan a toda la red de apoyo del objetivo.",
            "2. Congelan las cuentas de crédito y permisos de atraque de la presa.",
            "3. Emboscan con fuego cruzado de supresión y granadas aturdidoras.",
            "4. Usan pistola sedante y porra eléctrica para cobrar la recompensa viva.",
            "5. Sabotean el motor de salto de la nave del objetivo antes de atacar.",
        ],
    },
    {
        "num": 4, "nombre": "04 · Ivo Salomon, Parásito", "bls": "BL 1–9", "salario": "8kcr/mes",
        "combat": 50, "instinct": 50, "armor": 3, "dr": 0, "wounds": 3, "health": 20,
        "arma": "Rifle de precisión y cargas magnéticas", "danio": "3d10",
        "resumen": "Con un traje de vacío a medida y potentes electroimanes, Ivo viaja adherido al casco exterior de la nave de su presa durante semanas. Su única táctica es: PACIENCIA.",
        "tacticas": [
            "1. PACIENCIA: permanece adherido al casco exterior sin emitir señales.",
            "2. PACIENCIA: escucha todas las comunicaciones internas por vibración.",
            "3. PACIENCIA: sabotea los sensores externos durante un salto.",
            "4. PACIENCIA: ataca cuando el objetivo sale en EVA o queda solo en la esclusa.",
            "5. PACIENCIA: despresuriza el compartimento exacto donde duerme la presa.",
        ],
    },
    {
        "num": 5, "nombre": "05 · Red Taskr (Microencargos)", "bls": "BL 1–8", "salario": "Comisión por microencargo",
        "combat": 25, "instinct": 45, "armor": 1, "dr": 0, "wounds": 2, "health": 20,
        "arma": "Revólver y terminal TaskMaster personalizada", "danio": "2d10",
        "resumen": "«¿Tienes un minuto? Haz pequeños trabajos. Cobra. Sigue con tu día». Una aplicación que subcontrata la caza entre cientos de ciudadanos corrientes: taxistas, camareros, técnicos y vecinos.",
        "tacticas": [
            "1. Decenas de desconocidos fotografían a la tripulación con sus terminales.",
            "2. Un repartidor bloquea la puerta o pincha una válvula a cambio de 50cr.",
            "3. Un técnico de muelle retrasa el repostaje tras recibir una alerta de Taskr.",
            "4. Tres trabajadores desesperados tienden una emboscada torpe en un callejón.",
            "5. La posición exacta del grupo se actualiza en tiempo real cada 5 minutos.",
        ],
    },
    {
        "num": 6, "nombre": "06 · Emira Churchill, Desmontada", "bls": "BL 1–9", "salario": "18kcr/mes + gastos",
        "combat": 58, "instinct": 55, "armor": 8, "dr": 2, "wounds": 3, "health": 22,
        "arma": "Subfusil cibernético y enjambre de títeres", "danio": "3d10",
        "resumen": "Poco queda de su cuerpo original salvo la continuidad de sus recuerdos distribuida en varios chasis sintéticos y drones remotamente controlados.",
        "tacticas": [
            "1. Ataque en público con una primera oleada de títeres para ablandar al objetivo.",
            "2. Infiltración en un lugar seguro mediante extremidades desacopladas.",
            "3. Sacrifica un cuerpo señuelo para colocar un rastreador subcutáneo.",
            "4. Interfiere los implantes cibernéticos o sistemas de puntería del grupo.",
            "5. Transfiere su conciencia a un segundo chasis si el primero cae.",
        ],
    },
    {
        "num": 7, "nombre": "07 · El Soñador: Alf Moss", "bls": "BL 1–9", "salario": "35kcr/mes",
        "combat": 30, "instinct": 35, "armor": 2, "dr": 0, "wounds": 2, "health": 20,
        "arma": "Proyección psiónica de pesadilla (+1 Estrés/semana)", "danio": "2d10",
        "resumen": "Cazarrecompensas psiónico. Sus víctimas sufren pesadillas compartidas con una fosa recién cavada: ganan +1 Estrés por semana y no pueden reducir Estrés descansando hasta entregarse.",
        "tacticas": [
            "1. Provoca visiones de una fosa común durante el sueño o criosueño.",
            "2. Impide recuperar Estrés en cualquier tirada de descanso.",
            "3. Hace que los aliados vean el rostro de Alf Moss en los transeúntes.",
            "4. Induce paranoia aguda para que el objetivo se entregue voluntariamente.",
            "5. Aparece en calma en la cafetería local cuando el grupo está al límite de Pánico.",
        ],
    },
    {
        "num": 8, "nombre": "08 · Edgars Crismondi (Clones desechables)", "bls": "BL 1–9", "salario": "40kcr fijo",
        "combat": 42, "instinct": 40, "armor": 4, "dr": 0, "wounds": 2, "health": 18,
        "arma": "Escopeta de asalto y granadas", "danio": "3d10",
        "resumen": "«Lo desechable siempre sale más barato». Una dinastía de clones baratos de Edgar Crismondi que atacan en parejas o tríos sin ningún apego por su propia supervivencia.",
        "tacticas": [
            "1. Un Edgar herido suelta el arma y suplica mientras otro Edgar flanquea por detrás.",
            "2. Dos Edgars embisten con chalecos explosivos o cargas de demolición.",
            "3. Aunque maten a uno, al día siguiente aparece otro Edgar idéntico.",
            "4. Usan los cadáveres de los Edgars anteriores como trampa cazabobos.",
            "5. Conducen un vehículo pesado directamente contra el refugio del objetivo.",
        ],
    },
    {
        "num": 9, "nombre": "09 · Amaruq Borges, Memorius", "bls": "BL 1–9", "salario": "50kcr",
        "combat": 55, "instinct": 60, "armor": 7, "dr": 2, "wounds": 3, "health": 25,
        "arma": "Cañón sónico vocal y hoja monomolecular", "danio": "3d10",
        "resumen": "Le falta la mitad inferior del rostro, sustituida por un sintetizador mecánico que reproduce a la perfección las voces robadas de sus víctimas anteriores (Cailean, Kostandin, Sybilla, Nadia, Ingi).",
        "tacticas": [
            "1. Imita por radio la voz exacta de un aliado o familiar pidiendo auxilio.",
            "2. Envía órdenes falsas de evacuación con la voz del capitán de la estación.",
            "3. Reproduce los últimos gritos de sus presas anteriores en la oscuridad.",
            "4. Aísla al objetivo cerrando mamparos mediante comandos de voz autorizados.",
            "5. Ataca desde las sombras tras atraer a la presa con una voz de confianza.",
        ],
    },
    {
        "num": 10, "nombre": "10 · Cazador 854 alias «Sr. Bichos»", "bls": "BL 1–9", "salario": "40kcr",
        "combat": 60, "instinct": 65, "armor": 6, "dr": 2, "wounds": 4, "health": 28,
        "arma": "Enjambre voraz y garras quitinosas", "danio": "3d10",
        "resumen": "Una figura siniestra bajo una gabardina hermética cuyo interior es una colonia consciente de artrópodos alienígenas que infestan conductos, devoran cables y se filtran bajo las puertas.",
        "tacticas": [
            "1. INFESTA EL ENTORNO: miles de insectos bloquean sensores y cerraduras.",
            "2. DESTRUYE LAS LUCES: devora el cableado dejando la zona a oscuras.",
            "3. SURGE DESDE ABAJO: emerge por las rejillas del suelo y desagües.",
            "4. ARRÁSTRATE DE NOCHE: ataca mientras el objetivo duerme.",
            "5. ACÉRCATE CON UN DISFRAZ: utiliza un traje o cadáver vacío como marioneta.",
        ],
    },
]

# Las 3 Naves de Wages of Sin (págs. 326–331), compatibles con mosh y mr-kit-desguazador
NAVES_WOS = [
    {
        "clave": "mpt-bus",
        "nombre": "MPT «Bus» (Transporte Masivo de Presos)",
        "modelo": "Valecore MPT-SC J2C-II",
        "tipo": "Transporte penitenciario",
        "salto": 2, "clase": 2, "coste": "200MCR", "casco": 0,
        "pro": 15, "bat": 20, "sis": 18,
        "trip": 12, "cryo": 24, "escape": 4, "fuel": 12,
        "anclajes": [0, 1], "mejoras": [2, 2],
        "mdmgBase": "1", "mdmgTotal": "0*",
        "eslora": "120 m × 17 m",
        "armas": [],
        "modulos": [
            {"nombre": "Hangar (×1 Lanzadera)", "coste": "Incluido", "rasgo": "Desembarco de presos"},
            {"nombre": "Enfermería penitenciaria", "coste": "Incluido", "rasgo": "Atención médica básica"},
            {"nombre": "Bloque de 132 celdas de contención", "coste": "Incluido", "rasgo": "Transporte de 132 reclusos"},
        ],
        "descripcion": "El Transporte Masivo de Personal (MPT «Bus») de Valecore traslada hasta 132 prisioneros hacinados hacia la Luna Carcelaria ODC en Baclite. Cuenta con pasarela superior de vigilancia armada para los guardias sobre el bloque de celdas.",
    },
    {
        "clave": "hunter-seeker",
        "nombre": "Hunter-Seeker (Caza de Recompensas)",
        "modelo": "Gauss CR-Medusa J1C-II",
        "tipo": "Caza interceptor de cazarrecompensas",
        "salto": 1, "clase": 2, "coste": "700MCR", "casco": 0,
        "pro": 30, "bat": 29, "sis": 35,
        "trip": 8, "cryo": 12, "escape": 1, "fuel": 5,
        "anclajes": [2, 4], "mejoras": [3, 5],
        "mdmgBase": "1d5", "mdmgTotal": "1d5+2",
        "eslora": "113 m",
        "armas": [
            {"nombre": "Cañón automático doble", "danio": "1d5+2 MDMG", "municion": 4},
        ],
        "modulos": [
            {"nombre": "Lancha de abordaje (×1)", "coste": "Incluido", "rasgo": "Abordaje táctico"},
            {"nombre": "Reducción de firma de sensores", "coste": "Incluido", "rasgo": "Rastreo sigiloso"},
            {"nombre": "30 celdas de detención criogénica", "coste": "Incluido", "rasgo": "Custodia de objetivos vivos"},
        ],
        "descripcion": "Diseñada por Gauss para sindicatos de cazarrecompensas de élite, la CR-Medusa «Hunter-Seeker» combina reducción de firma, sensores de largo alcance, cañones automáticos gemelos y capacidad para 30 prisioneros.",
    },
    {
        "clave": "veil-of-night",
        "nombre": "Veil of Night (Crucero de Utpala)",
        "modelo": "Utpala Shipyards Magnum Opus J3C-VI",
        "tipo": "Crucero acorazado de alta seguridad",
        "salto": 3, "clase": 6, "coste": "Incalculable", "casco": 2,
        "pro": 30, "bat": 65, "sis": 40,
        "trip": 72, "cryo": 36, "escape": 200, "fuel": 12,
        "anclajes": [4, 4], "mejoras": [5, 6],
        "mdmgBase": "2d10", "mdmgTotal": "3d10",
        "eslora": "400 m",
        "armas": [
            {"nombre": "Batería pesada de Utpala", "danio": "3d10 MDMG", "municion": 6},
            {"nombre": "Defensa láser de punto", "danio": "Contramedidas", "municion": 10},
        ],
        "modulos": [
            {"nombre": "Guarnición Élite de Utpala", "coste": "Incluido", "rasgo": "C:40 Escopeta 4d10 I:35 PA:10 RD:3 H:2(25)"},
            {"nombre": "400 celdas de máxima seguridad", "coste": "Incluido", "rasgo": "Prisión móvil orbital"},
        ],
        "descripcion": "Obra maestra de los astilleros de Utpala (400 m de eslora, Salto-3, Casco 2). Fortaleza volante custodiada por la Élite de Utpala con escopetas de combate y cortadoras láser.",
    },
]

# Armas de prisión (pág. 277) y Equipo de cazarrecompensas / 60 Equipos (págs. 318–319)
ARMAS_Y_EQUIPO = [
    # Armas improvisadas y de trabajo en la ODC (pág. 277)
    ("arma-pincho", "Pincho carcelario (plástico o metal)", "weapon", "1d5", "Cuerpo a cuerpo · Sangrado [+]. Fácil de ocultar en un registro superficial.", 50),
    ("arma-anillos", "Anillos de pelea pesados", "weapon", "1d5", "Cuerpo a cuerpo · Contundente. Pasan por bisutería ante miradas distraídas.", 40),
    ("arma-pilas", "Pilas industriales en un calcetín", "weapon", "1d10 [-]", "Cuerpo a cuerpo · Contundente. Arma improvisada clásica de los bloques 44.", 25),
    ("arma-latigo", "Látigo de cuchillas de desrame", "weapon", "2d10", "Cuerpo a cuerpo · Sangrado. Herramienta forestal robada del taller.", 180),
    ("arma-hachuela", "Hachuela de tala ODC", "weapon", "2d10", "Cuerpo a cuerpo · Sangrado / Gore. Muy controlada fuera del turno de bosque.", 150),
    ("arma-motosierra", "Motosierra pesada de tala", "weapon", "3d10", "Cuerpo a cuerpo · Gore [+], Antiarmadura, Ruidosa.", 650),
    ("arma-lazo", "Lazo de alambre de estrangulamiento", "weapon", "1d10", "Cuerpo a cuerpo · Silencioso; en ataque por sorpresa impide gritar.", 60),
    ("arma-bisturi", "Bisturí quirúrgico de enfermería", "weapon", "1d10", "Cuerpo a cuerpo · Sangrado [+]. Ignora PA ≤ 2.", 90),
    # Equipo de Cazarrecompensas
    ("arma-sedante", "Pistola sedante de captura", "weapon", "1d5", "Corto alcance (6 disparos). El objetivo debe superar Salvación de Cuerpo o caer inconsciente 1d10×10 min (Ideal para órdenes VIVO).", 850),
    ("arma-porra-elec", "Porra eléctrica de contención", "weapon", "1d10", "Cuerpo a cuerpo · No letal. Salvación de Cuerpo o queda aturdido 1 ronda.", 450),
    ("arma-revolver", "Revólver de frontera (.44)", "weapon", "2d10", "Corto alcance (6 disparos). Fiable y fácil de reparar.", 350),
    ("arma-escopeta-utpala", "Escopeta de combate Utpala", "weapon", "4d10", "Corto alcance (4 disparos) · 1d10 a medio alcance. Gore.", 1400),
    ("armadura-mono-odc", "Mono carcelario naranja ODC", "armor", "0", "PA 0 · Lleva impreso el número de bloque y recluso (#YYXX) en pecho y espalda.", 10),
    ("armadura-guardia-odc", "Chaleco antidisturbios de Funcionario CO", "armor", "5", "PA 5 · Incluye radio de corto alcance con la torre de control.", 750),
    ("armadura-cazador", "Traje táctico de Cazarrecompensas", "armor", "7", "PA 7 · RD 1, puntos de anclaje magnéticos y visor HUD de códigos de 6 dígitos.", 2200),
    ("item-grilletes", "Grilletes magnéticos de titanio", "item", "", "Inmovilizan las manos o tobillos del objetivo; requieren llave criptográfica o Fuerza [−] con herramientas pesadas.", 200),
    ("item-taskmaster", "Terminal TaskMaster personalizada", "item", "", "Acceso directo a la red de microencargos Taskr y al tablón de las 100 Órdenes de Busca del sector.", 500),
    ("item-baliza", "Baliza de rastreo magnética", "item", "", "Transmite coordenadas cifradas durante 30 días incluso a través del casco de una nave.", 300),
    ("item-bolsa-azucar", "Paquete de «azúcar» / contrabando ODC", "item", "", "Moneda de cambio en la economía sumergida de la prisión de Baclite (+20% en sobornos a presos o guardias).", 100),
    ("item-criojaula", "Féretro de estasis portátil («El Ataúd»)", "item", "", "Mantiene a un objetivo capturado en coma inducido durante 14 días para cobrar la recompensa Vivo sin riesgo de fuga.", 1800),
]

# Presos destacados, Personal de la ODC y Fauna de Offit (págs. 280–310 y 320–325)
ACTORES_ODC_Y_FAUNA = [
    # Jefes del personal ODC (pág. 298 / 325)
    ("odc-stephen-bognar", "Stephen Bognar (Superintendente ODC)", "guardia-odc", 27, 39, 3, 0, 2, 20, "Pistola reglamentaria", "2d10", "S01-15 · Edad 57 · Soborno: 73%. Dirige la ODC como un feudo familiar; desvía fondos del presupuesto de seguridad."),
    ("odc-christof-bognar", "Christof Bognar (Superintendente Adjunto)", "guardia-odc", 39, 33, 5, 0, 2, 20, "Porra eléctrica y revólver", "2d10", "S16-30 · Edad 35 · Soborno: 80%. Sobrino de Stephen, ambicioso, corrupto y cruel con los reclusos sin banda."),
    ("odc-kyou-aoki", "Kyou Aoki (Jefe de Funcionarios CO)", "guardia-odc", 36, 40, 7, 1, 3, 20, "Fusil de pulsos", "3d10", "S31-45 · Edad 41 · Soborno: 100% (Incorruptible o exige favores extremos). Mantiene la disciplina férrea de las atalayas."),
    ("odc-rani-kartall", "Rani Kartall (Técnica Jefe ODC)", "guardia-odc", 42, 30, 2, 0, 3, 20, "Pistola de clavos", "2d10", "S46-60 · Edad 45 · Soborno: 20%. Encargada de los generadores, las vallas de contención animal y los VTOL."),
    ("odc-asad-sivert", "Dr. Asad Sivert (Cirujano Jefe ODC)", "guardia-odc", 37, 31, 1, 0, 2, 20, "Bisturí y sedantes", "1d10", "S61-75 · Edad 52 · Soborno: 44%. Controla la enfermería y los certificados de defunción (una de las mejores rutas de fuga)."),
    ("odc-co-patrulla", "Funcionario de Prisiones (CO de la ODC)", "guardia-odc", 38, 35, 5, 0, 2, 20, "Fusil de pulsos / Porra", "3d10", "S76-00 · Guardia estándar de las atalayas, controles y escoltas de tala. Soborno medio: 45%."),
    # Líderes y presos clave de las bandas de la ODC (págs. 280–295 y 320–324)
    ("preso-chares-gallardo", "#2305 Chares Gallardo (Líder de 23 Arms)", "preso-veterano", 37, 41, 1, 0, 3, 20, "Látigo de cuchillas", "2d10", "Edad 51 · Robo a mano armada (Perpetua) · Banda: 23 Arms · Trabajo: Desbroce. Controla el tráfico de armas improvisadas en el Bloque 23."),
    ("preso-prince-marsden", "#4402 Prince Marsden (Sindicato Stratemeyer)", "preso-rebelde", 33, 39, 0, 0, 3, 20, "Anillos de pelea", "1d5", "Edad 18 · Perjurio (13 años) · Banda: Sindicato Stratemeyer · Trabajo: Aserradero. Enlace del crimen organizado dentro del Bloque 44."),
    ("preso-rey-brun", "#4490 Rey Brun (Sindicato de Presos)", "preso-sindicalista", 32, 31, 0, 0, 2, 20, "Pilas en un calcetín", "1d10", "Edad 25 · Huelga ilegal (16 años) · Banda: Sindicato de Presos · Trabajo: Taller. Organiza paros y planes de sabotaje colectivo."),
    ("preso-stein-bloxham", "#2331 Stein Bloxham (Especialista en Fugas)", "preso-fugitivo", 45, 32, 1, 0, 2, 20, "Hachuela", "2d10", "Edad 42 · Ayuda a la fuga (Perpetua) · Banda: 23 Arms · Trabajo: Desbroce. Conoce las rutas hacia el Infierno Verde y la Colonia de Fuga."),
    ("preso-madhuri-92", "#4462 Madhuri_92 (Androide Reclusa)", "preso-rebelde", 44, 44, 2, 0, 3, 20, "Hachuela de tala", "2d10", "Edad 3 · Revelar información corporativa protegida (32 años) · Trabajo: Tala. Guarda en su memoria planos del Parque Científico Sullipsuma."),
    ("preso-zazil", "#2365 Zazil Herbertsson (Enfermero Recluso)", "preso-veterano", 40, 31, 0, 0, 2, 20, "Bisturí", "1d10", "Edad 43 · Negligencia médica (Perpetua) · Banda: 23 Arms · Trabajo: Enfermería. Vende sedantes y plantas del monte."),
    # Fauna de Offit / El Infierno Verde (págs. 306–310)
    ("fauna-larvas", "Gusanos barrenadores («Larvas»)", "fauna-larva", 20, 20, 1, 0, 1, 15, "Aguijón paralizante", "1d10", "Aparecen 1d100. Del tamaño de conejos; su veneno exige Salvación de Cuerpo o impide caminar durante 1 hora. Tres larvas asadas sin glándula dan 1 ración."),
    ("fauna-chupaarboles", "Chupaárboles («Pájaro carpintero»)", "fauna-chupaarboles", 40, 30, 3, 0, 4, 30, "Pico perforador", "3d10", "Reptil hexápodo del tamaño de un caballo aferrado a los troncos gigantes. Extremadamente territorial; carne incomestible con sabor a resina."),
    ("fauna-pseudohiena", "Pseudohiena («Crías»)", "fauna-acechador", 30, 30, 1, 0, 2, 15, "Fauces en manada", "2d10", "Aparecen 3d10. Hexápodos del tamaño de perros que imitan voces y ruidos humanos para espantar a otros depredadores. Cada cuerpo hervido da 1 ración."),
    ("fauna-basilisco", "Basilisco de Offit («Lagarto tonto»)", "fauna-basilisco", 50, 10, 5, 2, 5, 40, "Garras demoledoras", "4d10", "Dieciséis toneladas de placas acorazadas y músculo. Abre la madera muerta buscando larvas. Su carne cocinada sabe a atún y da 18 raciones."),
    ("fauna-acechador", "Acechador del dosel de Offit", "fauna-acechador", 55, 45, 2, 0, 3, 25, "Lengua prensil y colmillos", "3d10", "Depredador arbóreo de seis extremidades que caza desde la niebla superior del Infierno Verde durante el atardecer y la noche."),
]


def crear_actor_criatura(actor_id, nombre, img_retrato, img_token, img_figura, st, bio, flags_extra=None):
    arma_id = fid(f"item:arma:{actor_id}")
    arma_item = {
        "_id": arma_id,
        "name": st["arma"],
        "type": "weapon",
        "img": f"modules/{MOD}/assets/iconos/arma-prision.webp",
        "system": {
            "description": f"<p>Ataque de {esc(nombre)}.</p>",
            "damage": st["danio"],
            "combat": st["combat"],
            "shots": 6,
            "curShots": 6,
            "useAmmo": False,
            "ranges": {"value": "Corto/Medio"},
        },
        "effects": [],
        "flags": {},
        "_stats": stats_doc(),
    }
    flags_mod = {"tipo": "pnj", **(flags_extra or {})}
    if img_figura:
        flags_mod["figura"] = img_figura

    return {
        "_id": actor_id,
        "name": nombre,
        "type": "creature",
        "img": img_retrato,
        "system": {
            "biography": bio,
            "description": bio,
            "health": {"value": st["health"], "min": 0, "max": st["health"], "label": "Salud"},
            "hits": {"value": 0, "min": 0, "max": st["wounds"], "label": "Heridas"},
            "stats": {
                "combat": {"value": st["combat"], "min": 0, "max": 99, "label": "Combate", "rollLabel": "Tirada de Combate", "enabled": True},
                "instinct": {"value": st["instinct"], "min": 0, "max": 99, "label": "Instinto", "rollLabel": "Tirada de Instinto", "enabled": True},
                "armor": {"value": st["armor"], "mod": 0, "min": 0, "max": 99, "damageReduction": st.get("dr", 0), "label": "Armadura", "enabled": True},
                "speed": {"value": 35, "min": 0, "max": 99, "label": "Velocidad", "enabled": False},
                "loyalty": {"value": 30, "min": 0, "max": 99, "label": "Lealtad", "enabled": False},
                "sanity": {"value": 30, "min": 0, "max": 99, "label": "Cordura", "enabled": False},
            },
        },
        "prototypeToken": {
            "name": re.sub(r"^\d+\s*·\s*", "", nombre)[:28],
            "displayName": 20,
            "actorLink": False,
            "width": 1,
            "height": 1,
            "texture": {"src": img_token, "fit": "contain", "scaleX": 1, "scaleY": 1},
            "bar1": {"attribute": "health"},
            "bar2": {"attribute": "hits"},
        },
        "items": [arma_item],
        "effects": [],
        "folder": null_folder(),
        "ownership": {"default": 0},
        "flags": {MOD: flags_mod},
        "_stats": stats_doc(),
    }


def null_folder():
    return None


def construir_naves():
    docs = []
    for nv in NAVES_WOS:
        nid = fid(f"nave:{nv['clave']}")
        items = []
        for idx, ar in enumerate(nv["armas"]):
            items.append({
                "_id": fid(f"nave:{nv['clave']}:arma:{idx}"),
                "name": ar["nombre"],
                "type": "weapon",
                "img": f"modules/{MOD}/assets/iconos/nave.webp",
                "system": {"description": f"<p>{esc(ar['danio'])}</p>", "damage": ar["danio"], "shots": ar["municion"], "curShots": ar["municion"]},
                "effects": [],
                "flags": {},
                "_stats": stats_doc(),
            })
        for idx, md in enumerate(nv["modulos"]):
            items.append({
                "_id": fid(f"nave:{nv['clave']}:mod:{idx}"),
                "name": md["nombre"],
                "type": "module",
                "img": f"modules/{MOD}/assets/iconos/nave.webp",
                "system": {"description": f"<p>{esc(md['rasgo'])} ({esc(md['coste'])})</p>", "hull": 1, "totalHull": 1, "feature": md["rasgo"], "offline": False},
                "effects": [],
                "flags": {},
                "_stats": stats_doc(),
            })
        plano = f"modules/{MOD}/assets/planos/{nv['clave']}.webp"
        docs.append({
            "_id": nid,
            "name": nv["nombre"],
            "type": "ship",
            "img": f"modules/{MOD}/assets/iconos/nave.webp",
            "system": {
                "biography": f"<p><strong>Modelo:</strong> {esc(nv['modelo'])} · <strong>Eslora:</strong> {esc(nv['eslora'])} · <strong>Coste:</strong> {esc(nv['coste'])}</p><p>{esc(nv['descripcion'])}</p>",
                "description": nv["descripcion"],
                "type": nv["tipo"],
                "class": f"Clase {nv['clase']} · Salto-{nv['salto']}",
                "images": {"layout": plano, "beauty": plano},
                "runSetup": False,
                "stats": {
                    "thrusters": {"value": nv["pro"], "min": 0, "max": 99, "label": "Propulsores"},
                    "battle": {"value": nv["bat"], "min": 0, "max": 99, "label": "Batalla"},
                    "systems": {"value": nv["sis"], "min": 0, "max": 99, "label": "Sistemas"},
                    "bankruptcy": {"value": 20, "min": 0, "max": 99, "label": "Quiebra"},
                    "armor": {"value": 20, "min": 0, "max": 99, "label": "Armadura"},
                    "combat": {"value": nv["bat"], "min": 0, "max": 99, "label": "Combate"},
                    "intellect": {"value": nv["sis"], "min": 0, "max": 99, "label": "Intelecto"},
                    "speed": {"value": nv["pro"], "min": 0, "max": 99, "label": "Velocidad"},
                },
                "supplies": {
                    "hull": {"value": max(1, nv["casco"]), "max": max(1, nv["casco"])},
                    "fuel": {"value": nv["fuel"], "max": nv["fuel"]},
                    "crew": {"value": nv["trip"], "max": nv["trip"]},
                    "cryopods": {"value": nv["cryo"]},
                    "escape-pods": {"value": nv["escape"]},
                    "upgrades": {"value": nv["mejoras"][0], "max": nv["mejoras"][1]},
                },
                "weapon-stats": {
                    "weapons": {"value": len(nv["armas"]), "max": nv["anclajes"][1]},
                    "hardpoints": {"value": nv["anclajes"][0], "max": nv["anclajes"][1]},
                },
            },
            "prototypeToken": {
                "name": nv["nombre"],
                "displayName": 20,
                "actorLink": True,
                "texture": {"src": f"modules/{MOD}/assets/iconos/nave.webp"},
            },
            "items": items,
            "effects": [],
            "folder": None,
            "ownership": {"default": 0},
            "flags": {
                MOD: {"nave": nv["clave"], "plano": plano},
                "mr-kit-desguazador": {
                    "aplicado": True,
                    "nave": nv["clave"],
                    "modelo": nv["modelo"],
                    "clase": nv["clase"],
                    "salto": nv["salto"],
                    "coste": nv["coste"],
                    "cascoBase": nv["casco"],
                    "mdmgBase": nv["mdmgBase"],
                    "mdmgTotal": nv["mdmgTotal"],
                    "eslora": nv["eslora"],
                },
            },
            "_stats": stats_doc(),
        })
    return docs


def construir_equipo(doc):
    items = []
    for clave, nombre, tipo, valor, desc, coste in ARMAS_Y_EQUIPO:
        iid = fid(f"item:{clave}")
        sys_data = {"description": f"<p>{esc(desc)}</p>", "cost": coste, "weight": 1, "quantity": 1}
        img = f"modules/{MOD}/assets/iconos/equipo.webp"
        if tipo == "weapon":
            img = f"modules/{MOD}/assets/iconos/arma-prision.webp"
            sys_data.update({"damage": valor, "shots": 6, "curShots": 6, "useAmmo": False, "ranges": {"value": "Corto"}})
        elif tipo == "armor":
            sys_data.update({"armorPoints": int(valor), "damageReduction": 1 if int(valor) >= 7 else 0})
        items.append({
            "_id": iid,
            "name": nombre,
            "type": tipo,
            "img": img,
            "system": sys_data,
            "effects": [],
            "folder": None,
            "ownership": {"default": 0},
            "flags": {MOD: {"clave": clave}},
            "_stats": stats_doc(),
        })

    # Extraer también los paquetes de EQUIPOS de las páginas 318 y 319
    txt_eq = doc[317].get_text("text") + "\n" + doc[318].get_text("text")
    categorias_eq = [
        ("cazarrecompensas", "Equipo de Cazarrecompensas", "Traje táctico (PA 5), pistola sedante (6 disparos), grilletes magnéticos, baliza de rastreo, escáner biométrico."),
        ("preso-odc", "Equipo de Recluso de la ODC", "Mono carcelario (PA 0), pincho oculto (1d5), 2 paquetes de azúcar de contrabando, mapa garabateado del bloque."),
        ("alguacil", "Equipo de Agente de Seguridad / Alguacil", "Chaleco antidisturbios (PA 5), porra eléctrica (1d10), revólver (6 disparos), esposas desechables (×4), placa."),
        ("transportista", "Equipo de Transportista de Presos", "Traje espacial (PA 3), pistola de clavos (64 disparos), mochila propulsora, linterna frontal, raciones."),
        ("rastreador-forense", "Equipo de Rastreador Forense", "Atuendo estándar (PA 1), kit de ADN y huellas, dron microcámara, gafas de visión nocturna, ganzúas electrónicas."),
        ("fugitivo-jungla", "Equipo de Fugado del Infierno Verde", "Mono desgarrado (PA 1), hachuela de tala (2d10), cuerda de 10 m, cantimplora, antídoto improvisado, brújula."),
    ]
    for slug, nom, desc in categorias_eq:
        items.append({
            "_id": fid(f"item:kit:{slug}"),
            "name": nom,
            "type": "item",
            "img": f"modules/{MOD}/assets/iconos/equipo.webp",
            "system": {"description": f"<p><strong>Kit completo de campaña (págs. 318–319):</strong> {esc(desc)}</p>", "cost": 500, "quantity": 1, "weight": 1},
            "effects": [],
            "folder": None,
            "ownership": {"default": 0},
            "flags": {MOD: {"clave": f"kit-{slug}"}},
            "_stats": stats_doc(),
        })
    return items


def construir_tablas(ordenes):
    """Construye las 14 tablas aleatorias de Wages of Sin."""
    definiciones = [
        ("ordenes-100", "01 · Las 100 Órdenes de Busca al azar (1d100)", "1d100", [
            (o["num"], o["num"], f"Orden #{o['num']:02d} (BL:{o['bl']}) · {o['titulo']} — {o['seBusca']} ({o['pago']}) · Entrega: {o['entrega']}")
            for o in ordenes
        ]),
        ("generador-objetivo", "02 · Generador de Recompensas: quién es el Objetivo (1d10)", "1d10", [
            (1, 4, "Criminal habitual o miembro de sindicato local"),
            (5, 6, "Desertor corporativo o empleado con secretos industriales"),
            (7, 7, "Científico, médico o académico fugitivo"),
            (8, 8, "Androide defectuoso, prototipo o IA emancipada"),
            (9, 10, "Criatura xenomorfa, infectado o líder de secta peligrosa"),
        ]),
        ("generador-delito", "03 · Generador de Recompensas: Delito cometido (1d20)", "1d20", [
            (1, 1, "Impago de deuda o ruptura de contrato de servidumbre"),
            (2, 2, "Robo de carga o desvío de suministros médicos"),
            (3, 3, "Asesinato de un directivo o funcionario local"),
            (4, 4, "Sabotaje de soporte vital o reactores de estación"),
            (5, 5, "Espionaje corporativo y robo de patentes"),
            (6, 6, "Fuga de custodia o de la Luna Carcelaria ODC (Baclite)"),
            (7, 7, "Contrabando de xenofauna o narcóticos prohibidos"),
            (8, 8, "Piratería espacial y secuestro de nave"),
            (9, 9, "Fraude financiero masivo y falsificación de identidad"),
            (10, 10, "Motín a bordo o huelga declarada ilegal"),
            (11, 11, "Chantaje político a autoridades del sector"),
            (12, 12, "Crímenes de guerra o atrocidades coloniales"),
            (13, 13, "Secuestro de un heredero o testigo clave"),
            (14, 14, "Experimentos ilegales con biotecnología o psiónica"),
            (15, 15, "Profanación o robo de reliquias de una secta"),
            (16, 16, "Incitación a la rebelión armada"),
            (17, 17, "Suplantación de un agente de la ley o juez"),
            (18, 18, "Liberación accidental de un patógeno en cuarentena"),
            (19, 19, "Traición a una banda criminal (recompensa cerrada)"),
            (20, 20, "Testigo ocular de algo que la corporación quiere borrar"),
        ]),
        ("generador-complicacion", "04 · Generador de Recompensas: Complicación (1d20)", "1d20", [
            (1, 1, "Hay un vínculo familiar o sentimental entre el cliente y el objetivo."),
            (2, 2, "Una autoridad local ya ha encarcelado al objetivo por otros delitos."),
            (3, 3, "El objetivo es inocente del cargo oficial; el cliente quiere silenciarlo."),
            (4, 4, "Otro grupo de cazarrecompensas rivales ya le pisa los talones."),
            (5, 5, "El lugar donde se esconde está bajo ocupación militar o cuarentena."),
            (6, 6, "El objetivo no tiene huella digital ni usa pagos electrónicos."),
            (7, 7, "El objetivo es muy querido por la comunidad local, que lo protege."),
            (8, 8, "El cliente planea traicionar a la tripulación en el punto de entrega para no pagar."),
            (9, 9, "El objetivo lleva un implante de hombre muerto (explosivo o filtración de datos)."),
            (10, 10, "El objetivo ya ha muerto, pero alguien sigue haciéndose pasar por él."),
            (11, 11, "El objetivo está infectado o sufriendo una metamorfosis monstruosa."),
            (12, 12, "El objetivo quiere entregarse, pero solo si antes ponen a salvo a su familia."),
            (13, 13, "La foto de la orden de busca es de hace 20 años o previa a cirugía estética."),
            (14, 14, "El objetivo trabaja ahora para una facción más poderosa que el cliente."),
            (15, 15, "El punto de entrega exige un viaje en salto con el prisionero a bordo durante semanas."),
            (16, 16, "El objetivo tiene información que incrimina directamente a uno de los PJ."),
            (17, 17, "Se exige captura VIVA, pero el objetivo es suicida y prefiere morir antes que volver."),
            (18, 18, "El objetivo es en realidad varios clones o androides con el mismo código."),
            (19, 19, "Una tormenta solar o avería deja incomunicada la estación durante la caza."),
            (20, 20, "El objetivo ofrece el doble de la recompensa si le ayudan a fingir su muerte."),
        ]),
        ("rastreo-fuentes", "05 · Localizar Objetivos: Pistas y Fuentes (1d10)", "1d10", [
            (1, 2, "Listas de pasajeros de naves: motivos de viaje inusuales o capitanes que «pierden» registros por un soborno."),
            (3, 4, "Vendedores y terminales de pago: cámaras de comercios y rastro de compras sin efectivo."),
            (5, 6, "Datos forenses: registros de ADN, sangre o huellas dactilares en la escena."),
            (7, 8, "Antecedentes y suscripciones: procesos judiciales previos, propiedades o envíos postales recurrentes."),
            (9, 10, "Cómplices y conocidos: vigilar a antiguos socios, familiares o acreedores hasta que el objetivo contacte."),
        ]),
        ("fuerzas-orden", "06 · Modelos de Fuerzas del Orden (1d10, pág. 223)", "1d10", [
            (1, 1, "Plataforma de microservicios policiales a demanda (algoritmos generan encargos tipo Taskr)."),
            (2, 2, "Milicia sindical rotatoria elegida entre los propios trabajadores de la estación."),
            (3, 3, "Seguridad corporativa privada con blindaje pesado que solo protege activos de la empresa."),
            (4, 4, "Alguaciles fronterizos solitarios desbordados que dependen de cazarrecompensas."),
            (5, 7, "Policía burocrática corrupta: lenta para investigar, rápida para aceptar sobornos o cerrar casos."),
            (8, 8, "Tribunal algorítmico automatizado con drones de vigilancia y multas instantáneas."),
            (9, 9, "Ley marcial militar: patrullas armadas con fusiles de pulsos y toques de queda."),
            (10, 10, "Justicia comunitaria / Ley del talión: sin policía formal; las familias pagan primas de sangre."),
        ]),
        ("cazadores-rivales", "07 · Los 10 Cazarrecompensas Rivales (1d10, págs. 230–249)", "1d10", [
            (c["num"], c["num"], f"{c['nombre']} ({c['bls']} · {c['salario']}) — {c['resumen']}")
            for c in CAZADORES_10
        ]),
        ("odc-rumores", "08 · Conocimiento y Rumores de los Presos de la ODC (1d10, pág. 296)", "1d10", [
            (1, 1, "Las vallas de contención animal del sector norte fallan durante 12 minutos cada vez que aterrizan suministros."),
            (2, 2, "El Dr. Asad Sivert firma certificados de defunción falsos por 3.000cr y saca a los «cadáveres» en el contenedor de residuos."),
            (3, 3, "En el bosque al oeste del Aserradero hay un campamento de fugados («La Colonia de Fuga») que cultiva hongos comestibles."),
            (4, 4, "La Técnica Jefe Rani Kartall acepta sobornos con un 80% de facilidad si se le consiguen piezas electrónicas."),
            (5, 5, "Al norte, cruzando el Infierno Verde, hay un complejo de caza para millonarios llamado El Elephant Lodge con una lanzadera VTOL."),
            (6, 6, "La banda 23 Arms esconde un revólver cargado bajo las tablas del taller de carpintería."),
            (7, 7, "Las larvas gigantes del bosque son comestibles si se les arranca la glándula venenosa antes de asarlas."),
            (8, 8, "El Parque Científico Sullipsuma realiza experimentos ilegales con fauna de Offit y compra ejemplares vivos sin hacer preguntas."),
            (9, 9, "El Superintendente Stephen Bognar infla el número de presos vivos en los informes para cobrar las subvenciones de manutención."),
            (10, 10, "En el Bloque 44 hay un preso que en realidad es un cazarrecompensas infiltrado para matar a un objetivo de BL:6."),
        ]),
        ("infierno-verde-encuentros", "09 · Encuentros en el Infierno Verde de Offit (1d10, pág. 305)", "1d10", [
            (1, 2, "Encuentro con animales autóctonos: tira en la tabla de Fauna de Offit (pág. 306)."),
            (3, 3, "Patrulla de 2d10 funcionarios (CO) de la prisión rastreando desde aeronaves VTOL."),
            (4, 4, "30 % de hallar planta medicinal o comestible especial (± rumores conocidos de la pág. 296)."),
            (5, 5, "Grupo de 1d10 presos fugados del Campamento maderero."),
            (6, 6, "Grupo de 1d10 fugados procedentes del Elephant Lodge."),
            (7, 7, "Expedición científica de 1d10+3 miembros del Parque Sullipsuma con aeronaves VTOL."),
            (8, 9, "Silencio sofocante bajo el mar verde: hoy no hay encuentro."),
            (10, 10, "Descubrimiento en la espesura: rastro hacia el Parque Sullipsuma, el Elephant Lodge o la Colonia de Fuga."),
        ]),
        ("fauna-offit", "10 · Fauna de Offit (1d6, págs. 306–310)", "1d6", [
            (1, 1, "1. Gusanos barrenadores («Larvas») [C:20 Aguijón 1d10 + Salv. Cuerpo I:20 PA:1 H:1(15)]. Aparecen 1d100."),
            (2, 2, "2. Chupaárboles («Pájaro carpintero») [C:40 Pico 3d10 I:30 PA:3 H:4(30)]. Reptil hexápodo territorial."),
            (3, 3, "3. Pseudohiena («Crías») [C:30 Dientes 2d10 I:30 PA:1 H:2(15)]. Aparecen 3d10 imitando voces humanas."),
            (4, 4, "4. Basilisco («Lagarto tonto») [C:50 Garras 4d10 I:10 PA:5 H:5(40)]. Mole acorazada de 16 toneladas; da 18 raciones."),
            (5, 5, "5. Acechador del dosel [C:55 Colmillos 3d10 I:45 PA:2 H:3(25)]. Embosca desde las copas de los árboles."),
            (6, 6, "6. Cazadores de trofeos del Elephant Lodge [C:45 Rifle de caza 3d10 I:40 PA:5 H:2(20)]. Turistas ricos armados."),
        ]),
    ]

    tablas = []
    for idx, (clave, nombre, formula, filas) in enumerate(definiciones):
        tid = fid(f"tabla:{clave}")
        results = []
        for r_idx, (rmin, rmax, txt) in enumerate(filas):
            results.append({
                "_id": fid(f"tabla:{clave}:res:{r_idx}"),
                "type": "text",
                "text": txt,
                "img": f"modules/{MOD}/assets/iconos/terminal.webp",
                "weight": 1,
                "range": [rmin, rmax],
                "drawn": False,
                "flags": {},
                "_stats": stats_doc(None),
            })
        tablas.append({
            "_id": tid,
            "name": nombre,
            "img": f"modules/{MOD}/assets/iconos/terminal.webp",
            "description": f"<p>Tabla oficial de <em>Wages of Sin</em> en español.</p>",
            "results": results,
            "formula": formula,
            "replacement": True,
            "displayRoll": True,
            "folder": None,
            "sort": 100000 + idx * 1000,
            "ownership": {"default": 0},
            "flags": {MOD: {"clave": clave}},
            "_stats": stats_doc(),
        })
    return tablas


def construir_diarios_manual(doc):
    """Construye los 8 Diarios Multipágina del Manual y de la Guía de La ODC: Baclite."""
    def extraer_rango(p_ini, p_fin):
        partes = []
        for p in range(p_ini - 1, p_fin):
            lineas = limpiar_lineas_pdf(doc[p].get_text("text"))
            if lineas:
                partes.append(f"<h4>Página {p + 1}</h4><p>" + "</p><p>".join(esc(x) for x in lineas) + "</p>")
        return "\n".join(partes)

    definiciones = [
        ("00-empieza-aqui", "00 · Empieza aquí — Guía del Módulo y La Luna Carcelaria", [
            ("Bienvenida y Herramientas", f"""
<h2>MR- Wages of Sin · Kit para Cazarrecompensas y La Luna Carcelaria</h2>
<p>Este módulo incorpora en español todo el contenido de <strong>Wages of Sin (MRPG-M6)</strong> para <em>Mothership 1e</em>:</p>
<ul>
  <li><strong>Las 100 Órdenes de Busca (01–100):</strong> Consulta el compendio <em>Las 100 Órdenes de Busca</em> o abre la <strong>Terminal de Recompensas</strong> desde el botón de controles de escena (<i class="fa-solid fa-crosshairs"></i>) para filtrar por Nivel de Busca (BL 1–10), ubicación o delito, mostrar el cartel limpio a los jugadores y desplegar al objetivo.</li>
  <li><strong>Generador, Rastreo y Delitos de Jugadores:</strong> Crea contratos al vuelo, resuelve tiradas de rastreo, calcula el Nivel de Busca (BL) de la tripulación cuando cometen delitos y celebra juicios.</li>
  <li><strong>Los 10 Cazarrecompensas Rivales:</strong> Listos como actores con sus retratos, figuras de cuerpo entero y tablas de tácticas <code>1d5</code>.</li>
  <li><strong>La ODC: Baclite (La Luna Carcelaria):</strong> Campaña completa en la prisión de Offit y la jungla del Infierno Verde, con planos para la mesa y para el Guardián, bandas, presos, personal con umbral de soborno y fauna.</li>
  <li><strong>Las 3 Naves Nuevas:</strong> <em>MPT «Bus»</em>, <em>Hunter-Seeker</em> y <em>Veil of Night</em> con sus planos de cubierta a doble página, compatibles con <strong>MR- Kit del Desguazador</strong>.</li>
</ul>
"""),
            ("Cómo dirigir Sesiones Únicas y Campañas (Págs. 6–9)", extraer_rango(6, 9)),
        ]),
        ("01-crimen-y-ordenes", "01 · Parte 2: Crimen — Órdenes de Busca, Rastreo y Entrega", [
            ("Órdenes Abiertas, del Sindicato y Cerradas (Págs. 10–15)", extraer_rango(10, 15)),
            ("Dirigir la Caza, Localizar Objetivos y Entrega (Págs. 16–19)", extraer_rango(16, 19)),
            ("Generador de Recompensas (Págs. 20–23)", extraer_rango(20, 23)),
        ]),
        ("02-castigo-y-juicios", "02 · Parte 3: Castigo — Fuerzas del Orden, Delitos y Juicios", [
            ("Fuerzas del Orden y Delitos de Jugadores (Págs. 222–225)", extraer_rango(222, 225)),
            ("Juicio, Sentencias y Castigo (Págs. 226–228)", extraer_rango(226, 228)),
        ]),
        ("03-cazarrecompensas-rivales", "03 · Los 10 Cazarrecompensas con Nombre Propio", [
            (c["nombre"], f"""
<div class="mr-wos-cartel">
  <div class="mr-wos-cartel-foto"><img src="modules/{MOD}/assets/cazadores/cazador-{c['num']:02d}.webp" alt="{esc(c['nombre'])}" /></div>
  <div class="mr-wos-cartel-datos">
    <h3>{esc(c['nombre'])}</h3>
    <p><strong>Objetivos que acepta:</strong> {esc(c['bls'])} · <strong>Tarifa:</strong> {esc(c['salario'])}</p>
    <p><strong>Estadísticas:</strong> Combate {c['combat']} · Instinto {c['instinct']} · PA {c['armor']} (RD {c['dr']}) · Heridas {c['wounds']} ({c['health']}) · Arma: {esc(c['arma'])} ({c['danio']})</p>
    <p>{esc(c['resumen'])}</p>
    <h4>Tácticas (1d5)</h4>
    <ul>{"".join(f"<li>{esc(t)}</li>" for t in c['tacticas'])}</ul>
  </div>
</div>
""") for c in CAZADORES_10
        ]),
        ("04-odc-baclite-prision", "04 · La ODC: Baclite — Dirigir la Luna Carcelaria y Seguridad", [
            ("Resumen de Baclite y Cómo usar este módulo (Págs. 250–253)", extraer_rango(250, 253)),
            ("Sectores de la Prisión A–Q y Planos (Págs. 254–261)", extraer_rango(254, 261)),
            ("Medidas de Seguridad y Dirigir la Prisión (Págs. 262–275)", extraer_rango(262, 275)),
            ("Economía Penal, Armas de Prisión y Ejemplo de Juego (Págs. 276–279)", extraer_rango(276, 279)),
        ]),
        ("05-odc-presos-y-personal", "05 · Bandas, Presos (#YYXX) y Personal (S YY/XX) de la ODC", [
            ("Bandas de la ODC y Reclusos (Págs. 280–295)", extraer_rango(280, 295)),
            ("Conocimiento y Botánica de los Presos (Págs. 296–297)", extraer_rango(296, 297)),
            ("Personal de la ODC y Sobornos (Págs. 298–302)", extraer_rango(298, 302)),
            ("Índice de Presos por Bloque, Bandas y Personal (Págs. 320–325)", extraer_rango(320, 325)),
        ]),
        ("06-infierno-verde-y-fuga", "06 · Fuga por el Infierno Verde, Fauna de Offit y Sullipsuma", [
            ("Rutas de Fuga y Supervivencia en el Infierno Verde (Págs. 303–305)", extraer_rango(303, 305)),
            ("Fauna de Offit (Págs. 306–310)", extraer_rango(306, 310)),
            ("Parque Científico Sullipsuma, Elephant Lodge y Colonia de Fuga (Págs. 311–313)", extraer_rango(311, 313)),
        ]),
        ("07-naves-y-equipos", "07 · Parte X: Equipos Iniciales, las 3 Naves y Mapa de Salto", [
            ("Equipos de Cazarrecompensas y Presos (Págs. 318–319)", extraer_rango(318, 319)),
            ("Las 3 Naves: MPT «Bus», Hunter-Seeker y Veil of Night (Págs. 326–331)", extraer_rango(326, 331)),
        ]),
    ]

    diarios = []
    for d_idx, (clave, nombre, pags) in enumerate(definiciones):
        did = fid(f"manual:{clave}")
        pages = []
        for p_idx, (p_nom, p_html) in enumerate(pags):
            pages.append({
                "_id": fid(f"manual:{clave}:pag:{p_idx}"),
                "name": p_nom,
                "type": "text",
                "sort": 100000 + p_idx * 10000,
                "title": {"show": True, "level": 1},
                "text": {"format": 1, "content": p_html},
                "flags": {},
                "_stats": stats_doc(None),
            })
        diarios.append({
            "_id": did,
            "name": nombre,
            "pages": pages,
            "folder": None,
            "sort": 100000 + d_idx * 10000,
            "ownership": {"default": 2},
            "flags": {MOD: {"clave": clave}},
            "_stats": stats_doc(),
        })
    return diarios


def construir_diarios_ordenes(ordenes):
    """Agrupa las 100 Órdenes de Busca en 5 Diarios Multipágina (20 órdenes por diario) para acceso instantáneo."""
    bloques = [
        ("ordenes-001-020", "Órdenes de Busca 01–20 (Absalom, Albion, Anvollapolis, Balonov, Boria, Chiamia)", ordenes[0:20]),
        ("ordenes-021-040", "Órdenes de Busca 21–40 (Citov, Crora, Dalia, Dautamica, Doenides, Giang-Trang)", ordenes[20:40]),
        ("ordenes-041-060", "Órdenes de Busca 41–60 (HypeLabs Domia, Lonoe, Maonus, Maveolara, Offit ODC, Ogroitum)", ordenes[40:60]),
        ("ordenes-061-080", "Órdenes de Busca 61–80 (Ovibious, Raerindra, Ravour, Rinus Hab, SEMSA, Stannish, Thinoruy)", ordenes[60:80]),
        ("ordenes-081-100", "Órdenes de Busca 81–100 (Ualif, Utpala, Uyema, Veldat, X-1, Yillesham-Tau y Especiales)", ordenes[80:100]),
    ]
    diarios = []
    for d_idx, (clave, nombre, lista) in enumerate(bloques):
        did = fid(f"diario-ordenes:{clave}")
        pages = []
        for p_idx, o in enumerate(lista):
            pages.append({
                "_id": fid(f"pagina-orden:{o['num']:03d}"),
                "name": f"#{o['num']:02d} (BL:{o['bl']}) · {o['titulo']}",
                "type": "text",
                "sort": 100000 + p_idx * 10000,
                "title": {"show": True, "level": 1},
                "text": {"format": 1, "content": html_orden_pagina(o)},
                "flags": {MOD: {"orden": o["num"], "bl": o["bl"]}},
                "_stats": stats_doc(None),
            })
        diarios.append({
            "_id": did,
            "name": nombre,
            "pages": pages,
            "folder": None,
            "sort": 100000 + d_idx * 10000,
            "ownership": {"default": 0},
            "flags": {MOD: {"clave": clave}},
            "_stats": stats_doc(),
        })
    return diarios


def construir_escenas_y_direccion():
    """Construye las 16 escenas para el compendio Adventure y el paquete de MR- Dirección."""
    definiciones_escenas = [
        ("portada", "00 · Portada — Wages of Sin", "escenas/portada.webp", 1920, 1080, True,
         "El terminal del sindicato parpadea en rojo sobre la mesa. Cien rostros buscados en todo el sector; trescientos mil créditos en recompensas pendientes; y al final de la ruta de salto, la sombra verde de Baclite, la Luna Carcelaria."),
        ("mapa-salto", "01 · Mapa de Salto del Sector", "escenas/mapa-salto.webp", 2400, 1500, False,
         "Las rutas de salto conectan las estaciones comerciales de Clase A y B con los puertos sin ley del borde exterior y el sistema aislado de Baclite."),
        ("tablon-ordenes", "02 · Red de Órdenes de Busca", "escenas/tablon-ordenes.webp", 1920, 1080, True,
         "Órdenes abiertas para cualquiera con un arma; contratos del sindicato con fianza; y subastas cerradas donde corporaciones y mafias ponen precio a sus traidores."),
        ("caza-recompensas", "03 · Muelles y Entrega en Mano", "escenas/caza-recompensas.webp", 1920, 1080, True,
         "Entregar un objetivo vivo paga el doble, pero cada día de espera en el puerto da tiempo a sus cómplices para intentar liberarlo."),
        ("absalom-station", "04 · Absalom Station (Órdenes 01, BL:1)", "escenas/absalom-station.webp", 1650, 2100, False,
         "Antiguo cuartel orbital reconvertido en colmena superpoblada. Las obras de ampliación nunca terminan y algo acecha en los conductos tras las Pleasance Rooms."),
        ("anvollapolis", "05 · Anvollapolis (Órdenes 03–07)", "escenas/anvollapolis.webp", 1650, 2100, False,
         "Metrópoli vertical dividida entre las torres corporativas, los sindicatos portuarios y las células insurgentes del ALF."),
        ("balonov", "06 · Balonov Downport City (Órdenes 09–13)", "escenas/balonov.webp", 1650, 2100, False,
         "Puerto de superficie ruidoso y embarrado donde confluyen contrabandistas, zoólogos ilegales y streamers de asesinatos en directo."),
        ("hypelabs-domia", "07 · HypeLabs Domia Station (Órdenes 41, 43, 45, 46)", "escenas/hypelabs-domia.webp", 1650, 2100, False,
         "Estación de investigación de alta seguridad. Sus órdenes de busca alcanzan BL:9 y suelen implicar inteligencias artificiales o sicarios corporativos."),
        ("utpala", "08 · Utpala — Fortín Pirata (Orden 83, BL:8)", "escenas/utpala.webp", 1650, 2100, False,
         "Astillero y bastión fortificado desde donde opera el crucero acorazado Veil of Night."),
        ("odc-mesa", "09 · La ODC: Baclite — Plano de Prisión (Mesa)", "escenas/odc-mesa.webp", 2410, 1505, False,
         "Hormigón húmedo rodeado por un muro de ocho metros y el rugido incesante de los generadores de contención animal. Más allá del perímetro se extiende el mar verde sin fin de Offit."),
        ("odc-guardian", "10 · La ODC: Baclite — Plano del Guardián (Con secretos)", "escenas/odc-guardian.webp", 2700, 1750, False,
         "Plano operativo del Guardián con dotación de funcionarios CO por atalaya, cámaras, horarios y puntos débiles del perímetro."),
        ("odc-celda", "11 · La ODC: Baclite — Plano de Celda y Escondites", "escenas/odc-celda.webp", 1650, 2100, False,
         "Vuestra celda en el bloque penitenciario. Anotad aquí qué escondéis y dónde antes de la próxima requisa de los guardias."),
        ("infierno-verde-mesa", "12 · El Infierno Verde de Offit (Mapa de Jugadores)", "escenas/infierno-verde-mesa.webp", 1047, 1255, False,
         "Árboles titánicos envueltos en niebla cálida. Aquí fuera no hay muros ni guardias: solo depredadores de seis patas y kilómetros de jungla."),
        ("infierno-verde-guardian", "13 · El Infierno Verde de Offit (Mapa del Guardián)", "escenas/infierno-verde-guardian.webp", 1650, 2100, False,
         "Mapa del Guardián con las distancias aleatorias entre la ODC, el Campamento Maderero, el Parque Científico Sullipsuma, el Elephant Lodge y la Colonia de Fuga."),
        ("plano-hunter-seeker", "14 · Cubierta: Caza «Hunter-Seeker» (Gauss CR-Medusa)", "planos/hunter-seeker.webp", 2720, 1700, False,
         "Caza interceptor de cazarrecompensas con 30 celdas de estasis, cañones automáticos gemelos y lancha de abordaje."),
        ("plano-mpt-bus", "15 · Cubierta: Transporte Penal «MPT Bus»", "planos/mpt-bus.webp", 2720, 1700, False,
         "Transporte masivo de prisioneros con pasarela superior armada y 132 celdas de contención rumbo a Baclite."),
    ]

    escenas = []
    dir_escenas = {}
    for idx, (clave, nombre, ruta_rel, w, h, es_imagen, lectura) in enumerate(definiciones_escenas):
        sid = fid(f"escena:{clave}")
        src = f"modules/{MOD}/assets/{ruta_rel}"
        escenas.append({
            "_id": sid,
            "name": nombre,
            "active": clave == "portada",
            "navigation": idx <= 10 or "mesa" in clave or "plano" in clave,
            "navOrder": idx * 10,
            "background": {"src": src},
            "width": w,
            "height": h,
            "padding": 0.05,
            "grid": {"type": 0, "size": 100, "alpha": 0},
            "tokenVision": False,
            "fog": {"exploration": False},
            "thumb": src,
            "flags": {MOD: {"clave": clave, "imagen": es_imagen}},
            "_stats": stats_doc(),
        })
        dir_escenas[clave] = {
            "id": sid,
            "name": nombre,
            "img": src,
            "readAloud": lectura,
        }

    direccion_pack = {
        "id": MOD,
        "title": "MR- Wages of Sin · Cazarrecompensas y La ODC: Baclite",
        "system": "mosh",
        "clocks": [
            {"id": "bl-tripulacion", "name": "Nivel de Busca del Grupo (BL)", "max": 10, "value": 0},
            {"id": "rastro-presa", "name": "Rastro del Objetivo", "max": 4, "value": 0},
            {"id": "alerta-odc", "name": "Alerta en la Prisión ODC", "max": 6, "value": 0},
            {"id": "fuga-offit", "name": "Travesía por el Infierno Verde", "max": 6, "value": 0},
        ],
        "scenes": dir_escenas,
    }
    return escenas, direccion_pack


def main():
    doc = fitz.open(PDF_PATH)
    ordenes = extraer_100_ordenes(doc)
    diarios_ordenes = construir_diarios_ordenes(ordenes)
    diarios_manual = construir_diarios_manual(doc)

    # Actores: 100 Objetivos + 10 Cazarrecompensas + Personal/Presos ODC + Fauna
    actores = []
    for o in ordenes:
        bio = f"<p><strong>Orden #{o['num']:02d} (BL:{o['bl']} · {esc(o['seBusca'])})</strong> — Pago: {esc(o['pago'])} · Entrega: {esc(o['entrega'])}</p><p>{esc(o['anuncio'])}</p><p>{esc(o['informe'][:700])}</p>"
        actores.append(crear_actor_criatura(
            o["actorId"],
            f"#{o['num']:02d} · {o['titulo']}",
            o["img"],
            o["token"],
            o["figura"],
            o["stats"],
            bio,
            {"categoria": "objetivo", "orden": o["num"], "bl": o["bl"], "seBusca": o["seBusca"], "pago": o["pago"]},
        ))

    for c in CAZADORES_10:
        cid = fid(f"actor:cazador:{c['num']:02d}")
        st = {"combat": c["combat"], "instinct": c["instinct"], "armor": c["armor"], "dr": c["dr"], "wounds": c["wounds"], "health": c["health"], "arma": c["arma"], "danio": c["danio"]}
        bio = f"<p><strong>{esc(c['bls'])} · Salario: {esc(c['salario'])}</strong></p><p>{esc(c['resumen'])}</p><h4>Tácticas (1d5)</h4><ul>" + "".join(f"<li>{esc(t)}</li>" for t in c["tacticas"]) + "</ul>"
        actores.append(crear_actor_criatura(
            cid,
            c["nombre"],
            f"modules/{MOD}/assets/cazadores/cazador-{c['num']:02d}.webp",
            f"modules/{MOD}/assets/tokens/cazador-{c['num']:02d}.webp",
            f"modules/{MOD}/assets/figuras/cazador-{c['num']:02d}.webp",
            st,
            bio,
            {"categoria": "cazarrecompensas", "num": c["num"], "tacticas": c["tacticas"]},
        ))

    for clave, nom, slug_img, cb, ins, pa, dr, w, hp, arma, danio, desc in ACTORES_ODC_Y_FAUNA:
        aid = fid(f"actor:odc:{clave}")
        st = {"combat": cb, "instinct": ins, "armor": pa, "dr": dr, "wounds": w, "health": hp, "arma": arma, "danio": danio}
        actores.append(crear_actor_criatura(
            aid,
            nom,
            f"modules/{MOD}/assets/odc/{slug_img}.webp",
            f"modules/{MOD}/assets/tokens/{slug_img}.webp",
            f"modules/{MOD}/assets/figuras/{slug_img}.webp",
            st,
            f"<p>{esc(desc)}</p>",
            {"categoria": "odc-fauna", "clave": clave},
        ))

    naves = construir_naves()
    equipo = construir_equipo(doc)
    tablas = construir_tablas(ordenes)
    escenas, direccion_pack = construir_escenas_y_direccion()

    macros = [
        ("terminal", "Terminal de Recompensas y ODC", "terminal", "game.mrWages.abrirTerminal();"),
        ("generar-orden", "Generar Orden de Busca al azar", "orden", "game.mrWages.macros.generarOrden();"),
        ("rastrear", "Rastrear Objetivo (Localizar)", "rastreo", "game.mrWages.macros.rastrear();"),
        ("delito-jugadores", "Delito de Jugadores y Nivel BL", "delito", "game.mrWages.macros.delitoJugadores();"),
        ("soborno-odc", "Intentar Soborno en la ODC", "soborno", "game.mrWages.macros.sobornoODC();"),
        ("infierno-verde", "Jornada en el Infierno Verde (Offit)", "jungla", "game.mrWages.macros.infiernoVerde();"),
    ]
    macros_docs = []
    for idx, (m_clave, m_nom, m_ico, m_cmd) in enumerate(macros):
        macros_docs.append({
            "_id": fid(f"macro:{m_clave}"),
            "name": m_nom,
            "type": "script",
            "img": f"modules/{MOD}/assets/iconos/{m_ico}.webp",
            "scope": "global",
            "command": m_cmd,
            "folder": None,
            "sort": 100000 + idx * 1000,
            "ownership": {"default": 0},
            "flags": {MOD: {"clave": m_clave}},
            "_stats": stats_doc(),
        })

    # Compendio Adventure con las escenas, manual, naves, cazarrecompensas, actores ODC, equipo, tablas y macros
    actores_aventura = [a for a in actores if a["flags"][MOD].get("categoria") != "objetivo" or a["flags"][MOD].get("orden") in (1, 2, 5, 7, 13, 28, 32, 41, 50, 56, 83, 100)] + naves
    aventura = [{
        "_id": fid("adventure:wages-of-sin-baclite"),
        "name": "Wages of Sin — Cazarrecompensas y La Luna Carcelaria Baclite",
        "img": f"modules/{MOD}/assets/escenas/portada.webp",
        "caption": "Kit completo de Cazarrecompensas (100 órdenes de busca, 10 cazadores rivales, 3 naves) y el módulo carcelario «La ODC: Baclite» para Mothership 1e.",
        "description": "<p>Importa las escenas del sector y de la Luna Carcelaria <strong>La ODC: Baclite</strong>, las 3 naves nuevas (<em>MPT «Bus»</em>, <em>Hunter-Seeker</em> y <em>Veil of Night</em>), los 10 Cazarrecompensas rivales, presos, funcionarios, fauna de Offit, armas de prisión, tablas, manuales y macros.</p>",
        "scenes": escenas,
        "actors": actores_aventura,
        "items": equipo,
        "tables": tablas,
        "journal": diarios_manual + diarios_ordenes,
        "macros": macros_docs,
        "folders": [],
        "sort": 100000,
        "flags": {MOD: {"aventura": "baclite"}},
        "_stats": stats_doc(),
    }]

    salidas = {
        "aventura-baclite": aventura,
        "ordenes": diarios_ordenes,
        "manual": diarios_manual,
        "objetivos": actores,
        "naves": naves,
        "equipo": equipo,
        "tablas": tablas,
        "macros": macros_docs,
    }
    for nombre, docs in salidas.items():
        (DATA_DIR / f"{nombre}.json").write_text(json.dumps(docs, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"  [OK] _data/{nombre}.json -> {len(docs)} documento(s)")

    # Índice ligero para la Terminal interactiva (sin texto privado gigante duplicado, o con los campos clave)
    indice_ordenes = [{
        "num": o["num"],
        "codigo": o["codigo"],
        "titulo": o["titulo"],
        "bl": o["bl"],
        "seBusca": o["seBusca"],
        "delito": o["delito"],
        "cliente": o["cliente"],
        "pago": o["pago"],
        "prima": o["prima"],
        "entrega": o["entrega"],
        "paradero": o["paradero"],
        "etiquetas": o["etiquetas"],
        "pagina": o["pagina"],
        "anuncio": o["anuncio"],
        "informe": o["informe"][:900],
        "statStr": o["statStr"],
        "img": o["img"],
        "actorId": o["actorId"],
        "diarioId": fid(f"diario-ordenes:ordenes-{(o['num']-1)//20*20+1:03d}-{((o['num']-1)//20+1)*20:03d}"),
        "paginaId": fid(f"pagina-orden:{o['num']:03d}"),
    } for o in ordenes]
    (CONTENT_DIR / "ordenes-indice.json").write_text(json.dumps(indice_ordenes, ensure_ascii=False, indent=1), encoding="utf-8")
    (CONTENT_DIR / "direccion-es.json").write_text(json.dumps(direccion_pack, ensure_ascii=False, indent=2), encoding="utf-8")
    doc.close()
    print("Generación de datos de Wages of Sin completada.")


if __name__ == "__main__":
    main()

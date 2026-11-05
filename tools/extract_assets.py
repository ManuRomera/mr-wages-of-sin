#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Extractor y procesador gráfico para MR- Wages of Sin: Kit de Cazarrecompensas y La Luna Carcelaria.
Aplica siempre la marca oficial MR_MARCA (marca.esquina en escenas/planos/retratos/iconos
y marca.discreta en tokens circulares y figuras de cuerpo entero).
"""

import io
import os
import re
import sys
from pathlib import Path
import fitz
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont

sys.path.insert(0, "/Volumes/Datos_Dock/FoundryVTT/Trabajo LOGO/marca")
import marca  # noqa: E402

PDF_PATH = "/Volumes/Datos_Dock/Rol/01 Sistemas de juego/Colección de sistemas/Mothership/Wages of Sin ESPAÑOL.pdf"
RAIZ = Path(__file__).resolve().parent.parent
ASSETS = RAIZ / "assets"

for sub in ("escenas", "planos", "objetivos", "cazadores", "odc", "tokens", "figuras", "iconos"):
    (ASSETS / sub).mkdir(parents=True, exist_ok=True)


def cargar_fuente(tam=22, indice=0):
    rutas = [
        "/System/Library/Fonts/Supplemental/DIN Condensed Bold.ttf",
        "/System/Library/Fonts/Avenir Next Condensed.ttc",
        "/System/Library/Fonts/HelveticaNeue.ttc",
    ]
    for r in rutas:
        if os.path.exists(r):
            try:
                return ImageFont.truetype(r, tam, index=indice)
            except Exception:
                try:
                    return ImageFont.truetype(r, tam)
                except Exception:
                    pass
    return ImageFont.load_default()


def extraer_xref(doc, xref):
    d = doc.extract_image(xref)
    im = Image.open(io.BytesIO(d["image"]))
    smask = d.get("smask", 0)
    if smask and smask > 0:
        try:
            m_d = doc.extract_image(smask)
            mask = Image.open(io.BytesIO(m_d["image"])).convert("L")
            if mask.size != im.size:
                mask = mask.resize(im.size, Image.Resampling.LANCZOS)
            im = im.convert("RGBA")
            im.putalpha(mask)
            return im
        except Exception:
            pass
    return im.convert("RGBA")


def render_pagina(doc, p1, dpi=165):
    pm = doc[p1 - 1].get_pixmap(dpi=dpi)
    return Image.frombytes("RGB", (pm.width, pm.height), pm.samples)


def render_doble_pagina(doc, p_izq, p_der, dpi=165):
    a = render_pagina(doc, p_izq, dpi=dpi)
    b = render_pagina(doc, p_der, dpi=dpi)
    hoja = Image.new("RGB", (a.width + b.width, max(a.height, b.height)), (14, 14, 16))
    hoja.paste(a, (0, 0))
    hoja.paste(b, (a.width, 0))
    return hoja


def crear_token_circular(im_src, destino, color_aro=(217, 56, 46)):
    """Crea token circular 400x400 con aro táctico y marca.discreta."""
    L = 400
    src = im_src.convert("RGB")
    w, h = src.size
    lado = min(w, h)
    cx = (w - lado) // 2
    cy = max(0, int((h - lado) * 0.18))
    recorte = src.crop((cx, cy, cx + lado, cy + lado)).resize((L, L), Image.Resampling.LANCZOS)

    mask = Image.new("L", (L, L), 0)
    md = ImageDraw.Draw(mask)
    md.ellipse((12, 12, L - 12, L - 12), fill=255)

    out = Image.new("RGBA", (L, L), (0, 0, 0, 0))
    out.paste(recorte.convert("RGBA"), (0, 0), mask)

    dr = ImageDraw.Draw(out)
    dr.ellipse((8, 8, L - 8, L - 8), outline=(18, 18, 20, 255), width=10)
    dr.ellipse((12, 12, L - 12, L - 12), outline=(*color_aro, 245), width=5)

    out = marca.discreta(out, L // 2, L - 28, 18)
    out.save(destino, "WEBP", quality=88, method=6)


def crear_figura_cuerpo_entero(im_src, destino):
    """Recorta figura vertical de cuerpo entero sobre lienzo transparente 600x900 con marca.discreta."""
    W, H = 600, 900
    rgba = im_src.convert("RGBA")
    # Si el fondo es casi blanco o uniforme, convertirlo a transparente suave
    px = rgba.load()
    sw, sh = rgba.size
    bg_r, bg_g, bg_b, bg_a = px[0, 0]
    if bg_a > 200 and (bg_r > 225 and bg_g > 225 and bg_b > 225):
        for y in range(sh):
            for x in range(sw):
                r, g, b, a = px[x, y]
                dist = abs(r - bg_r) + abs(g - bg_g) + abs(b - bg_b)
                if dist < 38:
                    px[x, y] = (r, g, b, 0)
                elif dist < 70:
                    px[x, y] = (r, g, b, int(a * (dist - 38) / 32))

    escala = min((W * 0.88) / sw, (H * 0.92) / sh)
    nw, nh = max(1, int(sw * escala)), max(1, int(sh * escala))
    escalada = rgba.resize((nw, nh), Image.Resampling.LANCZOS)

    lienzo = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    # Sombra suave bajo los pies
    sombra = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    sd = ImageDraw.Draw(sombra)
    sd.ellipse((W // 2 - int(nw * 0.35), H - 58, W // 2 + int(nw * 0.35), H - 18), fill=(0, 0, 0, 140))
    sombra = sombra.filter(ImageFilter.GaussianBlur(10))
    lienzo = Image.alpha_composite(lienzo, sombra)

    ox = (W - nw) // 2
    oy = H - nh - 26
    lienzo.paste(escalada, (ox, oy), escalada)
    lienzo = marca.discreta(lienzo, W // 2, H - 36, 22)
    lienzo.save(destino, "WEBP", quality=88, method=6)


def crear_portada_escena(doc, destino):
    """Crea la escena de portada panorámica 1920x1080 de Wages of Sin."""
    W, H = 1920, 1080
    cov_page = render_pagina(doc, 1, dpi=180)
    salto = render_doble_pagina(doc, 332, 333, dpi=130)

    fondo = salto.resize((W, H), Image.Resampling.LANCZOS).filter(ImageFilter.GaussianBlur(4))
    tinte = Image.new("RGB", (W, H), (22, 8, 10))
    lienzo = Image.blend(fondo, tinte, 0.78).convert("RGBA")

    # Póster de portada a la derecha
    escala = (H * 0.92) / cov_page.height
    cw, ch = int(cov_page.width * escala), int(cov_page.height * escala)
    poster = cov_page.resize((cw, ch), Image.Resampling.LANCZOS).convert("RGBA")
    px = W - cw - 110
    py = (H - ch) // 2

    sombra = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    sd = ImageDraw.Draw(sombra)
    sd.rounded_rectangle((px - 12, py - 12, px + cw + 12, py + ch + 12), radius=14, fill=(0, 0, 0, 220))
    sombra = sombra.filter(ImageFilter.GaussianBlur(18))
    lienzo = Image.alpha_composite(lienzo, sombra)
    lienzo.paste(poster, (px, py), poster)

    # Panel informativo a la izquierda
    panel = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    pd = ImageDraw.Draw(panel)
    pd.rounded_rectangle((70, 70, 960, H - 70), radius=14, fill=(14, 12, 15, 232), outline=(217, 56, 46, 230), width=3)
    lienzo = Image.alpha_composite(lienzo, panel)

    dr = ImageDraw.Draw(lienzo)
    f_kicker = cargar_fuente(24)
    f_tit = cargar_fuente(96)
    f_sub = cargar_fuente(34)
    f_txt = cargar_fuente(24)

    dr.text((115, 115), "MRPG-M6 · MOTHERSHIP 1E · EDICIÓN EN ESPAÑOL", font=f_kicker, fill=(217, 56, 46, 255))
    dr.text((115, 155), "WAGES OF SIN", font=f_tit, fill=(244, 240, 234, 255))
    dr.rectangle((115, 275, 320, 281), fill=(217, 56, 46, 255))
    dr.text((115, 300), "KIT PARA CAZARRECOMPENSAS Y LA LUNA CARCELARIA BACLITE", font=f_sub, fill=(235, 185, 92, 255))

    puntos = [
        "• Las 100 Órdenes de Busca completas (BL 1–10) con carteles y retratos",
        "• Generador procedural de recompensas, delitos, complicaciones y rastreo",
        "• Reglas de delitos de jugadores, fuerzas del orden, juicios y condenas",
        "• Los 10 Cazarrecompensas rivales con nombre propio y tablas de tácticas",
        "• Módulo completo «La ODC: Baclite» (La Luna Carcelaria y el Infierno Verde)",
        "• Bandas, 80+ presos (#YYXX), 50 guardias (S YY/XX), fauna de Offit y armas",
        "• Las 3 naves nuevas (MPT «Bus», Hunter-Seeker y Veil of Night) + 60 equipos",
        "• Terminal interactiva de Recompensas y paquete para MR- Dirección",
    ]
    y = 385
    for pt in puntos:
        dr.text((120, y), pt, font=f_txt, fill=(220, 218, 214, 245))
        y += 52

    lienzo = marca.esquina(lienzo)
    lienzo.convert("RGB").save(destino, "WEBP", quality=90, method=6)
    print("  [OK] Escena de portada ->", destino.name)


def extraer_planos_y_escenas(doc):
    """Extrae planos de las 3 naves, mapas de Baclite/Infierno Verde, Mapa de Salto y estaciones."""
    crear_portada_escena(doc, ASSETS / "escenas" / "portada.webp")

    # 3 Planos de cubierta de las naves (formato idéntico a mr-kit-desguazador/tools/planos.py)
    naves_paginas = {
        "mpt-bus": (326, 327),
        "hunter-seeker": (328, 329),
        "veil-of-night": (330, 331),
    }
    for clave, (pa, pb) in naves_paginas.items():
        hoja = render_doble_pagina(doc, pa, pb, dpi=170)
        hoja = marca.esquina(hoja)
        hoja.save(ASSETS / "planos" / f"{clave}.webp", "WEBP", quality=84, method=6)
        print("  [OK] Plano de nave ->", f"{clave}.webp")

    # Mapa de salto del sector (doble página 332-333)
    salto = render_doble_pagina(doc, 332, 333, dpi=170)
    salto = marca.esquina(salto)
    salto.save(ASSETS / "escenas" / "mapa-salto.webp", "WEBP", quality=86, method=6)

    # Prisión ODC Baclite: versión Guardián (doble página 254-255 con notas) y versión Mesa (página 256 limpia)
    odc_gm = render_doble_pagina(doc, 254, 255, dpi=170)
    odc_gm = marca.esquina(odc_gm)
    odc_gm.save(ASSETS / "escenas" / "odc-guardian.webp", "WEBP", quality=86, method=6)

    # Para la mesa, usamos el mapa limpio de la celda/prisión sin las etiquetas de guardias (xref 1804 en P256 + xref 1798/1800 limpios)
    odc_mesa_izq = extraer_xref(doc, 1798).convert("RGB")
    odc_mesa_der = extraer_xref(doc, 1800).convert("RGB")
    odc_mesa = Image.new("RGB", (odc_mesa_izq.width + odc_mesa_der.width, max(odc_mesa_izq.height, odc_mesa_der.height)), (245, 245, 245))
    odc_mesa.paste(odc_mesa_izq, (0, 0))
    odc_mesa.paste(odc_mesa_der, (odc_mesa_izq.width, 0))
    odc_mesa = marca.esquina(odc_mesa)
    odc_mesa.save(ASSETS / "escenas" / "odc-mesa.webp", "WEBP", quality=86, method=6)

    # Plano de celda para jugadores (P256)
    celda_mesa = render_pagina(doc, 256, dpi=170)
    celda_mesa = marca.esquina(celda_mesa)
    celda_mesa.save(ASSETS / "escenas" / "odc-celda.webp", "WEBP", quality=86, method=6)

    # Mapa del Infierno Verde (P304): versión Guardián (página renderizada con distancias) y versión Mesa (xref 2047 limpia)
    iv_gm = render_pagina(doc, 304, dpi=175)
    iv_gm = marca.esquina(iv_gm)
    iv_gm.save(ASSETS / "escenas" / "infierno-verde-guardian.webp", "WEBP", quality=86, method=6)

    iv_mesa = extraer_xref(doc, 2047).convert("RGB")
    iv_mesa = marca.esquina(iv_mesa)
    iv_mesa.save(ASSETS / "escenas" / "infierno-verde-mesa.webp", "WEBP", quality=86, method=6)

    # Escenas de estaciones y ubicaciones principales de Cazarrecompensas
    hubs = {
        "absalom-station": 26,
        "albion": 29,
        "anvollapolis": 34,
        "balonov": 44,
        "hypelabs-domia": 103,
        "utpala": 183,
        "sullipsuma": 311,
        "elephant-lodge": 312,
    }
    for slug, pag in hubs.items():
        im = render_pagina(doc, pag, dpi=165)
        im = marca.esquina(im)
        im.save(ASSETS / "escenas" / f"{slug}.webp", "WEBP", quality=85, method=6)
        print("  [OK] Escena ubicación ->", f"{slug}.webp")

    # Escenas ilustradas de ambiente (extraídas de las ilustraciones panorámicas del libro)
    ilustradas = [
        ("caza-recompensas", 7, 253, "ENTREGA EN MANO", "Cazarrecompensas en los muelles del sector"),
        ("tablon-ordenes", 11, 263, "RED DE ÓRDENES DE BUSCA", "Terminales abiertas, encargos del sindicato y contratos cerrados"),
        ("emboscada", 18, 337, "DEPREDADOR O PRESA", "Rastreo y captura en las estaciones fronterizas"),
        ("bestia-absalom", 28, 395, "ORDEN 01 · ABSALOM STATION", "Lo que acecha bajo las cicatrices"),
    ]
    for slug, pag, xref, tit, sub in ilustradas:
        try:
            raw = extraer_xref(doc, xref).convert("RGB")
        except Exception:
            raw = render_pagina(doc, pag, dpi=160)
        W, H = 1920, 1080
        bg = raw.resize((W, H), Image.Resampling.LANCZOS).filter(ImageFilter.GaussianBlur(20))
        bg = ImageEnhance.Brightness(bg).enhance(0.35)
        escala = min((W * 0.86) / raw.width, (H * 0.86) / raw.height)
        nw, nh = int(raw.width * escala), int(raw.height * escala)
        fg = raw.resize((nw, nh), Image.Resampling.LANCZOS)
        ox, oy = (W - nw) // 2, (H - nh) // 2
        bg.paste(fg, (ox, oy))
        dr = ImageDraw.Draw(bg)
        dr.rounded_rectangle((48, H - 135, 760, H - 38), radius=10, fill=(14, 12, 16), outline=(217, 56, 46), width=2)
        dr.text((68, H - 122), tit, font=cargar_fuente(34), fill=(244, 240, 234))
        dr.text((68, H - 78), sub, font=cargar_fuente(22), fill=(210, 205, 198))
        bg = marca.esquina(bg)
        bg.save(ASSETS / "escenas" / f"{slug}.webp", "WEBP", quality=86, method=6)
        print("  [OK] Escena ilustrada ->", f"{slug}.webp")


def extraer_100_objetivos(doc):
    """Extrae el retrato individual de cada una de las 100 Órdenes de Busca (01..100) y genera su token."""
    # Mapear en qué página empieza cada ORDEN 01..100
    paginas_orden = {}
    for p in range(25, 222):
        txt = doc[p].get_text("text")
        for m in re.finditer(r"ORDEN\s+(\d{2,3})", txt):
            num = int(m.group(1))
            if 1 <= num <= 100 and num not in paginas_orden:
                paginas_orden[num] = p

    # Respaldo: cuadrícula de retratos de las páginas 2 y 3
    p2_im = render_pagina(doc, 2, dpi=180)
    p3_im = render_pagina(doc, 3, dpi=180)

    extraidos = 0
    for num in range(1, 101):
        p_idx = paginas_orden.get(num, 26)
        candidato = None
        # Buscar la imagen de retrato (típicamente 300..950px de ancho, relación vertical o cuadrada) en la página o la siguiente
        for look_p in (p_idx, min(221, p_idx + 1)):
            for img_info in doc[look_p].get_images(full=True):
                xref, _, iw, ih = img_info[0], img_info[1], img_info[2], img_info[3]
                if xref in (2251, 2254):
                    continue
                if 200 <= iw <= 1150 and 200 <= ih <= 1450 and not (iw == 1200 and ih == 1500):
                    try:
                        candidato = extraer_xref(doc, xref).convert("RGB")
                        break
                    except Exception:
                        pass
            if candidato is not None:
                break

        if candidato is None:
            # Recortar de la cuadrícula de P2/P3
             bloque = ((num - 1) // 10)
             col = (num - 1) % 10
             hoja_grid = p2_im if (bloque % 2 == 0) else p3_im
             fila = bloque // 2
             gw, gh = hoja_grid.size
             cw, ch = gw / 10.0, gh / 5.0
             candidato = hoja_grid.crop((int(col * cw), int(fila * ch), int((col + 1) * cw), int((fila + 1) * ch)))

        # Guardar retrato con marca.esquina
        retrato = candidato.resize((480, 600), Image.Resampling.LANCZOS)
        retrato_m = marca.esquina(retrato.copy())
        slug = f"orden-{num:03d}"
        retrato_m.save(ASSETS / "objetivos" / f"{slug}.webp", "WEBP", quality=85, method=6)
        crear_token_circular(retrato, ASSETS / "tokens" / f"{slug}.webp", color_aro=(217, 56, 46))
        if num in (1, 2, 5, 7, 13, 28, 32, 41, 50, 56, 83, 100):
            crear_figura_cuerpo_entero(candidato, ASSETS / "figuras" / f"{slug}.webp")
        extraidos += 1

    print(f"  [OK] {extraidos}/100 retratos y tokens de objetivos generados.")


def extraer_10_cazarrecompensas_y_odc(doc):
    """Extrae retratos, tokens y figuras de cuerpo entero de los 10 Cazarrecompensas, Presos, Guardias y Fauna."""
    # En P334 y P335 están las 10 tiras verticales de los 10 cazarrecompensas, además de sus páginas 230..249
    pags_cazador = [230, 232, 234, 236, 238, 240, 242, 244, 246, 248]
    for i, pag in enumerate(pags_cazador, start=1):
        mejor = None
        for p_look in (pag - 1, pag):
            for info in doc[p_look].get_images(full=True):
                xref, iw, ih = info[0], info[2], info[3]
                if xref in (2251, 2254) or (iw == 1200 and ih == 1500):
                    continue
                if iw >= 220 and ih >= 220:
                    try:
                        im = extraer_xref(doc, xref)
                        if mejor is None or (im.width * im.height > mejor.width * mejor.height):
                            mejor = im
                    except Exception:
                        pass
        if mejor is None:
            mejor = render_pagina(doc, pag, dpi=150).crop((40, 120, 620, 920))

        slug = f"cazador-{i:02d}"
        ret = mejor.convert("RGB").resize((520, 680), Image.Resampling.LANCZOS)
        marca.esquina(ret.copy()).save(ASSETS / "cazadores" / f"{slug}.webp", "WEBP", quality=86, method=6)
        crear_token_circular(ret, ASSETS / "tokens" / f"{slug}.webp", color_aro=(235, 168, 52))
        crear_figura_cuerpo_entero(mejor, ASSETS / "figuras" / f"{slug}.webp")

    # También la figura icónica de la portada (xref 27153)
    try:
        oso = extraer_xref(doc, 27153)
        crear_figura_cuerpo_entero(oso, ASSETS / "figuras" / "cazarrecompensas-oso.webp")
        crear_token_circular(oso, ASSETS / "tokens" / "cazarrecompensas-oso.webp", color_aro=(217, 56, 46))
    except Exception:
        pass

    # Retratos de Presos, Guardias de la ODC y Fauna (de P281-310)
    odc_muestras = [
        ("preso-rebelde", 282),
        ("preso-veterano", 285),
        ("preso-sindicalista", 288),
        ("preso-fugitivo", 292),
        ("guardia-odc", 298),
        ("superintendente-bognar", 299),
        ("fauna-larva", 306),
        ("fauna-chupaarboles", 307),
        ("fauna-basilisco", 308),
        ("fauna-acechador", 309),
    ]
    for slug, pag in odc_muestras:
        im_elegida = None
        for info in doc[pag - 1].get_images(full=True):
            xref, iw, ih = info[0], info[2], info[3]
            if xref not in (2251, 2254) and iw >= 180 and ih >= 180 and not (iw >= 1180 and ih >= 1480):
                try:
                    im_elegida = extraer_xref(doc, xref)
                    break
                except Exception:
                    pass
        if im_elegida is None:
            pg = render_pagina(doc, pag, dpi=150)
            im_elegida = pg.crop((int(pg.width * 0.15), int(pg.height * 0.2), int(pg.width * 0.85), int(pg.height * 0.8)))

        rgb = im_elegida.convert("RGB").resize((480, 600), Image.Resampling.LANCZOS)
        marca.esquina(rgb.copy()).save(ASSETS / "odc" / f"{slug}.webp", "WEBP", quality=85, method=6)
        crear_token_circular(rgb, ASSETS / "tokens" / f"{slug}.webp", color_aro=(88, 178, 132))
        crear_figura_cuerpo_entero(im_elegida, ASSETS / "figuras" / f"{slug}.webp")

    print("  [OK] 10 Cazarrecompensas y retratos/tokens/figuras de la ODC generados.")


def crear_iconos():
    """Genera iconos vectoriales estilo Mothership (blanco y rojo/ámbar sobre negro) con marca.esquina."""
    definiciones = {
        "terminal": ("BUSCA", "01-100"),
        "orden": ("SE BUSCA", "VIVO/MUERTO"),
        "rastreo": ("RASTREO", "PISTAS"),
        "delito": ("DELITO", "NIVEL BL"),
        "juicio": ("CASTIGO", "SENTENCIA"),
        "odc": ("ODC", "BACLITE"),
        "soborno": ("SOBORNO", "CRÉDITOS"),
        "jungla": ("OFFIT", "JUNGLA"),
        "arma-prision": ("PRISIÓN", "CONTRABANDO"),
        "equipo": ("EQUIPO", "CAZADOR"),
        "nave": ("NAVE", "SALTO"),
    }
    for slug, (l1, l2) in definiciones.items():
        L = 512
        im = Image.new("RGBA", (L, L), (14, 14, 16, 255))
        dr = ImageDraw.Draw(im)
        dr.rounded_rectangle((22, 22, L - 22, L - 22), radius=42, fill=(22, 20, 24, 255), outline=(217, 56, 46, 255), width=8)
        dr.ellipse((86, 86, L - 86, L - 86), outline=(240, 236, 230, 90), width=4)
        # Mira de cazarrecompensas estilizada
        dr.line((L // 2, 54, L // 2, 136), fill=(217, 56, 46, 220), width=6)
        dr.line((L // 2, L - 136, L // 2, L - 54), fill=(217, 56, 46, 220), width=6)
        dr.line((54, L // 2, 136, L // 2), fill=(217, 56, 46, 220), width=6)
        dr.line((L - 136, L // 2, L - 54, L // 2), fill=(217, 56, 46, 220), width=6)

        f1 = cargar_fuente(68)
        f2 = cargar_fuente(36)
        b1 = dr.textbbox((0, 0), l1, font=f1)
        b2 = dr.textbbox((0, 0), l2, font=f2)
        dr.text(((L - (b1[2] - b1[0])) // 2, L // 2 - 58), l1, font=f1, fill=(244, 240, 234, 255))
        dr.text(((L - (b2[2] - b2[0])) // 2, L // 2 + 22), l2, font=f2, fill=(235, 185, 92, 255))

        im = marca.esquina(im)
        im.save(ASSETS / "iconos" / f"{slug}.webp", "WEBP", quality=88, method=6)
    print("  [OK] Iconos de sistema/macros generados con MR_MARCA.")


def main():
    doc = fitz.open(PDF_PATH)
    extraer_planos_y_escenas(doc)
    extraer_100_objetivos(doc)
    extraer_10_cazarrecompensas_y_odc(doc)
    crear_iconos()
    doc.close()
    print("Extracción de recursos de Wages of Sin completada.")


if __name__ == "__main__":
    main()

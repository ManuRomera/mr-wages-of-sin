#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Extrae el arte REAL del PDF de «Wages of Sin» (nada inventado) y lo deja listo para Foundry.

Etapas (python3 tools/extract_assets.py [etapa ...]; sin argumentos = todas):
  ordenes   100 retratos de las órdenes de busca + tokens
  cazadores 10 cazarrecompensas rivales: figura sin fondo, retrato y token
  odc       fauna de Offit, personal y presos con retrato del libro
  escenas   escenas y mapas sin la maquetación del libro
  planos    planos de cubierta de las 3 naves
  armas     iconos de las armas de prisión (recortes de la pág. 277)
  arte      retratos del personal sin ilustración e iconos (generados con Codex: tools/gen_codex.py)

Los retratos del libro son estarcidos de tinta con máscara: hay que componerlos con su máscara sobre
papel, no con el RGB suelto (así salían negros en la primera versión).
La marca MR se aplica con Trabajo LOGO/marca/marca.py (regla de la casa).
"""
import io
import re
import sys
from pathlib import Path

import fitz
from PIL import Image, ImageChops, ImageDraw, ImageEnhance, ImageFilter

sys.path.insert(0, "/Volumes/Datos_Dock/FoundryVTT/Trabajo LOGO/marca")
import marca  # noqa: E402

PDF_PATH = "/Volumes/Datos_Dock/Rol/01 Sistemas de juego/Colección de sistemas/Mothership/Wages of Sin ESPAÑOL.pdf"
RAIZ = Path(__file__).resolve().parent.parent
ASSETS = RAIZ / "assets"
RAW = RAIZ / "art_src" / "raw"
for sub in ("escenas", "planos", "objetivos", "cazadores", "odc", "tokens", "figuras", "iconos", "armas"):
    (ASSETS / sub).mkdir(parents=True, exist_ok=True)

ROJO = (214, 32, 40)          # rojo del libro
PAPEL = (244, 241, 235)       # blanco de papel
NEGRO_ODC = (22, 20, 22)      # fondo negro de las láminas de la ODC
_cache = {}


# ───────────────────────── utilidades ─────────────────────────
def rgba(doc, xref, opaco_ok=False):
    """Imagen del PDF con su máscara suave como alfa. None si es un fondo opaco (y no se pide)."""
    if (xref, opaco_ok) in _cache:
        return _cache[(xref, opaco_ok)]
    e = doc.extract_image(xref)
    im = Image.open(io.BytesIO(e["image"])).convert("RGB")
    out = im.convert("RGBA")
    if e.get("smask"):
        m = Image.open(io.BytesIO(doc.extract_image(e["smask"])["image"])).convert("L")
        if m.size != im.size:
            m = m.resize(im.size, Image.LANCZOS)
        if m.getextrema()[0] >= 250 and not opaco_ok:
            out = None
        else:
            out.putalpha(m)
    elif not opaco_ok:
        out = None
    _cache[(xref, opaco_ok)] = out
    return out


def sobre(im, color):
    bg = Image.new("RGBA", im.size, color + (255,))
    bg.alpha_composite(im.convert("RGBA"))
    return bg.convert("RGB")


def render_pagina(doc, p1, dpi=165, clip=None):
    pm = doc[p1 - 1].get_pixmap(dpi=dpi, clip=clip)
    return Image.frombytes("RGB", (pm.width, pm.height), pm.samples)


def guardar(im, destino, calidad=86):
    destino = Path(destino)
    destino.parent.mkdir(parents=True, exist_ok=True)
    im.save(destino, "WEBP", quality=calidad, method=6)


def token_circular(src, destino, aro, caja=None, fondo=None, sello=True):
    """Token redondo 400×400 con aro. `caja` = (x0,y0,x1,y1) cuadrada sobre `src`; el sello MR va en el aro."""
    L = 400
    src = src.convert("RGBA")
    if caja is None:
        w, h = src.size
        lado = min(w, h)
        caja = ((w - lado) // 2, 0, (w - lado) // 2 + lado, lado)
    rec = src.crop(tuple(int(v) for v in caja)).resize((L, L), Image.LANCZOS)
    if fondo is not None:
        rec = Image.alpha_composite(Image.new("RGBA", (L, L), fondo + (255,)), rec)
    mask = Image.new("L", (L * 3, L * 3), 0)
    ImageDraw.Draw(mask).ellipse((36, 36, L * 3 - 36, L * 3 - 36), fill=255)
    mask = mask.resize((L, L), Image.LANCZOS)
    out = Image.new("RGBA", (L, L), (0, 0, 0, 0))
    out.paste(rec, (0, 0), ImageChops.multiply(mask, rec.getchannel("A")))
    dr = ImageDraw.Draw(out)
    dr.ellipse((8, 8, L - 8, L - 8), outline=(18, 18, 20, 255), width=10)
    dr.ellipse((12, 12, L - 12, L - 12), outline=aro + (245,), width=5)
    if sello:
        out = marca.discreta(out, 329, 329, 17)
    guardar(out, destino, 88)


def figura(src, destino, ancho_max=1400):
    """Figura sin fondo sobre lienzo transparente, con sombra bajo los pies y sello en el hombro."""
    bb = src.getchannel("A").point(lambda v: 255 if v > 30 else 0).getbbox()
    src = src.crop(bb)
    sw, sh = src.size
    H = 900
    W = max(600, min(ancho_max, round(H * 0.92 * sw / sh / 0.88)))
    esc = min((W * 0.88) / sw, (H * 0.92) / sh)
    nw, nh = max(1, int(sw * esc)), max(1, int(sh * esc))
    s = src.resize((nw, nh), Image.LANCZOS)
    lienzo = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    sombra = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(sombra).ellipse((W // 2 - int(nw * 0.35), H - 50, W // 2 + int(nw * 0.35), H - 14), fill=(0, 0, 0, 120))
    lienzo = Image.alpha_composite(lienzo, sombra.filter(ImageFilter.GaussianBlur(9)))
    capa = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    capa.paste(s, ((W - nw) // 2, H - nh - 26), s)
    lienzo = Image.alpha_composite(lienzo, capa)
    try:
        lienzo = marca.hombro(lienzo)
    except Exception:  # noqa: BLE001
        pass
    guardar(lienzo, destino, 88)


# ───────────────────────── 1 · órdenes de busca ─────────────────────────
def etapa_ordenes(doc):
    """El retrato de cada orden es un JPEG de tinta (≤80) con máscara; cada página de orden tiene uno de ~380×455."""
    paginas = []
    for i in range(26, 222):
        for im in doc[i].get_images(full=True):
            if 370 <= im[2] <= 430 and 440 <= im[3] <= 462 and im[1] > 0:
                paginas.append((i + 1, im[0]))
                break
    assert len(paginas) == 100, f"se esperaban 100 retratos y hay {len(paginas)}"
    for n, (p, xref) in enumerate(paginas, 1):
        a = rgba(doc, xref, opaco_ok=True)
        m = a.getchannel("A").point(lambda v: min(255, int(v * 1.3)))   # tinta algo más negra
        a.putalpha(m)
        ret = sobre(a, PAPEL).resize((570, 684), Image.LANCZOS)
        slug = f"orden-{n:03d}"
        # token: cara y hombros, aro rojo; se saca ANTES de firmar el retrato
        token_circular(ret, ASSETS / "tokens" / f"{slug}.webp", (217, 56, 46), caja=(0, 14, 570, 584), fondo=PAPEL)
        guardar(marca.esquina(ret), ASSETS / "objetivos" / f"{slug}.webp", 84)
    print(f"  [OK] {len(paginas)} retratos y tokens de las órdenes")


# ───────────────────────── 2 · cazarrecompensas ─────────────────────────
HUNTER_SPREADS = [230, 232, 234, 236, 238, 240, 242, 244, 246, 248]   # página izquierda de cada doble
# Red Taskr: su arte es un rectángulo rojo opaco con la silueta aparte; se recorta el rojo.
TASKR_FONDO, TASKR_SILUETA = 1720, 1723


def _taskr(doc):
    fondo = rgba(doc, TASKR_FONDO, opaco_ok=True).convert("RGB")
    sil = rgba(doc, TASKR_SILUETA, opaco_ok=True).getchannel("A")
    import numpy as np
    arr = np.asarray(fondo).astype("float32")
    d = np.sqrt(((arr - np.array(ROJO, dtype="float32")) ** 2).sum(-1))
    k = np.clip((d - 45) / 70.0, 0, 1)
    alfa = Image.fromarray((k * 255).astype("uint8")).filter(ImageFilter.MedianFilter(3))
    alfa = ImageChops.lighter(alfa, sil)
    out = fondo.convert("RGBA")
    out.putalpha(alfa)
    return out


def figura_doble(doc, pl, sc=2.0):
    W, H = int(576 * 2 * sc), int(720 * sc)
    cv = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    for k, p in enumerate((pl, pl + 1)):
        pg = doc[p - 1]
        for im in pg.get_images(full=True):
            x, w, h = im[0], im[2], im[3]
            if w < 250 or h < 250:
                continue
            a = _taskr(doc) if x == TASKR_SILUETA else (None if x == TASKR_FONDO else rgba(doc, x))
            if a is None:
                continue
            for r in pg.get_image_rects(x):
                s = a.resize((max(1, round(r.width * sc)), max(1, round(r.height * sc))), Image.LANCZOS)
                capa = Image.new("RGBA", (W, H), (0, 0, 0, 0))
                capa.paste(s, (round((r.x0 + k * 576) * sc), round(r.y0 * sc)))
                cv = Image.alpha_composite(cv, capa)
    bb = cv.getchannel("A").point(lambda v: 255 if v > 40 else 0).getbbox()
    return cv.crop(bb)


def cabeza(fig):
    """Caja cuadrada sobre la parte alta de la figura (donde está la cara) para el token."""
    w, h = fig.size
    al = fig.getchannel("A").point(lambda v: 255 if v > 40 else 0)
    banda = al.crop((0, 0, w, max(2, int(h * 0.12))))
    xs = [x for x in range(w) if banda.crop((x, 0, x + 1, banda.height)).getbbox()]
    cx = (min(xs) + max(xs)) / 2 if xs else w / 2
    lado = min(w, int(h * 0.36))
    lado = max(lado, int(h * 0.22))
    x0 = int(min(max(cx - lado / 2, 0), max(0, w - lado)))
    return (x0, 0, x0 + lado, lado)


# caja del token a mano donde la cabeza no está arriba al centro: (x0/ancho, y0/alto, lado/alto)
TOKEN_A_MANO = {1: (0.49, 0.0, 0.36), 2: (0.043, 0.07, 0.235), 4: (0.396, 0.193, 0.347), 10: (0.435, 0.03, 0.34)}


def etapa_cazadores(doc):
    for i, pl in enumerate(HUNTER_SPREADS, 1):
        fig = figura_doble(doc, pl)
        slug = f"cazador-{i:02d}"
        caja = cabeza(fig)
        if i in TOKEN_A_MANO:
            fx, fy, fl = TOKEN_A_MANO[i]
            lado = int(fl * fig.height)
            caja = (int(fx * fig.width), int(fy * fig.height), int(fx * fig.width) + lado, int(fy * fig.height) + lado)
        token_circular(fig, ASSETS / "tokens" / f"{slug}.webp", (235, 168, 52), caja=caja, fondo=ROJO)
        # retrato: parte alta de la figura sobre el rojo del libro, proporción 520×680
        w, h = fig.size
        alto = max(int(h * 0.45), min(h, int(w / 0.765)))
        ancho = int(alto * 0.765)
        cx = (caja[0] + caja[2]) / 2
        x0 = int(min(max(cx - ancho / 2, 0), max(0, w - ancho)))
        rec = fig.crop((x0, 0, min(w, x0 + ancho), min(h, alto)))
        lienzo = Image.new("RGB", (ancho, alto), ROJO)
        lienzo.paste(sobre(rec, ROJO), (0, 0))
        lienzo = lienzo.resize((520, 680), Image.LANCZOS)
        guardar(marca.esquina(lienzo), ASSETS / "cazadores" / f"{slug}.webp", 86)
        figura(fig, ASSETS / "figuras" / f"{slug}.webp")
    print("  [OK] 10 cazarrecompensas (figura, retrato y token)")


# ───────────────────────── 3 · ODC y fauna ─────────────────────────
# criaturas de las láminas de las págs. 306-308: caja (x0,y0,x1,y1) en píxeles de la imagen de página de 1205×1505
FAUNA = {
    "fauna-larva": (306, (60, 380, 580, 960)),
    "fauna-chupaarboles": (306, (600, 380, 1100, 1030)),
    "fauna-pseudohiena": (307, (90, 170, 580, 1000)),
    "fauna-basilisco": (307, (600, 190, 1110, 1060)),
    "fauna-hiperalgas": (308, (30, 480, 570, 1130)),
    "fauna-simios": (308, (560, 100, 1150, 1070)),
    "fauna-lagarto-jirafa": (309, (40, 160, 600, 1010)),
    "fauna-dragon": (309, (600, 170, 1150, 1010)),
    "fauna-sirena": (310, (40, 160, 560, 1030)),
    "fauna-vandalos": (310, (590, 170, 1110, 1010)),
}


def _lamina(doc, pag):
    pg = doc[pag - 1]
    xref = [im[0] for im in pg.get_images(full=True) if im[2] == 1205][0]
    return sobre(rgba(doc, xref, opaco_ok=True), NEGRO_ODC)


def etapa_odc(doc):
    for slug, (pag, caja) in FAUNA.items():
        recorte = _lamina(doc, pag).crop(caja)
        bb = recorte.convert("L").point(lambda v: 255 if v > 48 else 0).getbbox()
        pad = 18
        recorte = recorte.crop((max(0, bb[0] - pad), max(0, bb[1] - pad), min(recorte.width, bb[2] + pad), min(recorte.height, bb[3] + pad)))
        lienzo = recorte.resize((520, int(520 * recorte.height / recorte.width)), Image.LANCZOS)
        lado_ = max(recorte.size)
        cuadro = Image.new("RGB", (lado_, lado_), NEGRO_ODC)
        cuadro.paste(recorte, ((lado_ - recorte.width) // 2, (lado_ - recorte.height) // 2))
        token_circular(cuadro, ASSETS / "tokens" / f"{slug}.webp", (88, 178, 132), caja=(0, 0, lado_, lado_), fondo=NEGRO_ODC)
        luz = recorte.convert("L").point(lambda v: min(255, max(0, (v - 34) * 6)))
        fig = recorte.convert("RGBA")
        fig.putalpha(luz.filter(ImageFilter.MaxFilter(3)))
        figura(fig, ASSETS / "figuras" / f"{slug}.webp")
        guardar(marca.esquina(lienzo), ASSETS / "odc" / f"{slug}.webp", 86)
    print(f"  [OK] fauna de Offit ({len(FAUNA)} criaturas)")

    # Presos con retrato en el libro: cada imagen pequeña (175 px) junto a su «#NNNN»
    n = 0
    for i in range(279, 297):
        pg = doc[i]
        words = [w for w in pg.get_text("words") if re.fullmatch(r"#\d{4}", w[4])]
        for im in pg.get_images(full=True):
            if not (100 < im[2] < 400 and 100 < im[3] < 400 and im[1] == 0):
                continue
            r = pg.get_image_rects(im[0])[0]
            cand = [w for w in words if w[1] <= r.y0 + 8 and w[0] < r.x0]
            if not cand:
                continue
            num = max(cand, key=lambda w: w[1])[4][1:]
            foto = rgba(doc, im[0], opaco_ok=True).convert("RGB")
            gr = foto.resize((foto.width * 3, foto.height * 3), Image.LANCZOS)
            lado_ = min(gr.size)
            token_circular(gr, ASSETS / "tokens" / f"preso-{num}.webp", (234, 124, 40), caja=((gr.width - lado_) // 2, 0, (gr.width + lado_) // 2, lado_), fondo=NEGRO_ODC)
            ret = gr.resize((520, int(520 * gr.height / gr.width)), Image.LANCZOS)
            guardar(marca.esquina(ret), ASSETS / "odc" / f"preso-{num}.webp", 86)
            n += 1
    print(f"  [OK] {n} presos con retrato del libro")


# ───────────────────────── 4 · escenas y planos ─────────────────────────
def lienzo_16_9(im, destino, fondo=(14, 12, 16), margen=0.04, w=2400, h=1350, desenfoque=True):
    """Pone una ilustración sobre un lienzo 16:9: la propia imagen difuminada de fondo y ella entera encima."""
    if desenfoque:
        bg = im.resize((w, h), Image.LANCZOS).filter(ImageFilter.GaussianBlur(30))
        bg = ImageEnhance.Brightness(bg).enhance(0.32)
    else:
        bg = Image.new("RGB", (w, h), fondo)
    esc = min(w * (1 - 2 * margen) / im.width, h * (1 - 2 * margen) / im.height)
    fg = im.resize((int(im.width * esc), int(im.height * esc)), Image.LANCZOS)
    bg.paste(fg, ((w - fg.width) // 2, (h - fg.height) // 2))
    guardar(marca.esquina(bg), destino, 86)


def recorte_pagina(doc, pag, caja_pt, dpi=200):
    """Renderiza solo la zona (x0,y0,x1,y1 en puntos) de una página: mapas vectoriales con su rotulación."""
    return render_pagina(doc, pag, dpi=dpi, clip=fitz.Rect(*caja_pt))


ESTACIONES = {   # slug: (página, caja del plano en puntos)
    "absalom-station": (26, (48, 228, 516, 600)), "anvollapolis": (34, (48, 228, 516, 600)),
    "balonov": (44, (48, 195, 516, 608)), "hypelabs-domia": (103, (48, 205, 516, 600)), "utpala": (183, (48, 228, 516, 600)),
}


def doble_pagina(doc, p_izq, p_der, dpi, recorte_izq, recorte_der):
    a = render_pagina(doc, p_izq, dpi=dpi, clip=fitz.Rect(*recorte_izq))
    b = render_pagina(doc, p_der, dpi=dpi, clip=fitz.Rect(*recorte_der))
    hoja = Image.new("RGB", (a.width + b.width, max(a.height, b.height)), NEGRO_ODC)
    hoja.paste(a, (0, 0))
    hoja.paste(b, (a.width, 0))
    return hoja


def etapa_escenas(doc):
    E = ASSETS / "escenas"
    portada = render_pagina(doc, 1, dpi=200)
    lienzo_16_9(portada, E / "portada.webp", fondo=(30, 8, 10), desenfoque=False, margen=0.03)
    # mapa de salto: doble página completa (las etiquetas son texto vectorial, la imagen sola es solo el campo de estrellas)
    salto = doble_pagina(doc, 332, 333, 130, (0, 0, 576, 720), (0, 0, 576, 720))
    guardar(marca.esquina(salto), E / "mapa-salto.webp", 86)
    for slug, xref in (("caza-recompensas", 253), ("tablon-ordenes", 263)):
        lienzo_16_9(rgba(doc, xref, opaco_ok=True).convert("RGB"), E / f"{slug}.webp")
    for slug, (pag, caja) in ESTACIONES.items():
        lienzo_16_9(recorte_pagina(doc, pag, caja, dpi=240), E / f"{slug}.webp", fondo=PAPEL, desenfoque=False, margen=0.05)
    # ODC mesa: las dos mitades limpias del plano isométrico (sin rótulos)
    izq = rgba(doc, 1798, opaco_ok=True).convert("RGB")
    der = rgba(doc, 1800, opaco_ok=True).convert("RGB")
    odc = Image.new("RGB", (izq.width + der.width, max(izq.height, der.height)), NEGRO_ODC)
    odc.paste(izq, (0, 0))
    odc.paste(der, (izq.width, 0))
    guardar(marca.esquina(odc), E / "odc-mesa.webp", 86)
    # ODC Guardián: doble página con las claves A–Q, sin cabecera ni pie
    gm = doble_pagina(doc, 254, 255, 150, (0, 34, 576, 640), (0, 34, 548, 640))
    guardar(marca.esquina(gm), E / "odc-guardian.webp", 86)
    # plano de la celda (pág. 256) para que los jugadores anoten su escondite
    celda = recorte_pagina(doc, 256, (250, 309, 510, 452), dpi=330)
    lienzo_16_9(celda, E / "odc-celda.webp", fondo=NEGRO_ODC, desenfoque=False, margen=0.08)
    # Infierno Verde: el mapa del libro (las distancias van rotuladas en la propia imagen)
    guardar(marca.esquina(rgba(doc, 2047, opaco_ok=True).convert("RGB")), E / "infierno-verde-mesa.webp", 86)
    print("  [OK] escenas")


def etapa_planos(doc):
    """Planos de cubierta de las 3 naves: la doble página del libro (ficha + dibujo + leyenda numerada), sin cabecera ni pie."""
    for slug, pl in (("mpt-bus", 326), ("hunter-seeker", 328), ("veil-of-night", 330)):
        hoja = doble_pagina(doc, pl, pl + 1, 190, (0, 40, 576, 640), (0, 40, 576, 640))
        guardar(marca.esquina(hoja, sube=0.0), ASSETS / "planos" / f"{slug}.webp", 84)
    print("  [OK] planos de nave")


# ───────────────────────── 5 · armas de prisión (pág. 277) ─────────────────────────
ARMAS = {   # slug: caja en píxeles de la imagen de página 1205×1505
    "pilas-calcetin": (130, 240, 320, 400), "motosierra": (300, 230, 920, 440), "daga": (920, 230, 1070, 440),
    "hacha-de-tala": (70, 500, 320, 910), "anillos": (320, 505, 620, 690), "garrote": (640, 505, 900, 690),
    "hachuela": (905, 505, 1100, 690), "latigo": (330, 780, 620, 970), "piedra-cuerda": (625, 780, 935, 960),
    "mazo": (925, 800, 1145, 1160), "pincho-madera": (100, 1060, 300, 1170), "pincho-sierra": (310, 1050, 610, 1235),
    "pincho-lata": (610, 1080, 920, 1240),
}


def etapa_armas(doc):
    base = sobre(rgba(doc, 1955, opaco_ok=True), NEGRO_ODC)
    for slug, caja in ARMAS.items():
        rec = base.crop(caja)
        lado = int(max(rec.size) * 1.12)
        cuadro = Image.new("RGB", (lado, lado), NEGRO_ODC)
        cuadro.paste(rec, ((lado - rec.width) // 2, (lado - rec.height) // 2))
        cuadro = ImageEnhance.Contrast(cuadro).enhance(1.12).resize((256, 256), Image.LANCZOS)
        guardar(marca.esquina(cuadro), ASSETS / "armas" / f"{slug}.webp", 88)
    print(f"  [OK] {len(ARMAS)} iconos de armas de prisión")


# ───────────────────────── 6 · arte generado con Codex (personal sin ilustración e iconos) ─────────────────────────
PERSONAL = ["stephen-bognar", "christof-bognar", "kyou-aoki", "rani-kartall", "asad-sivert", "rey-brun", "zazil-herbertsson"]
ICONOS = ["terminal", "orden", "rastreo", "delito", "soborno", "equipo", "nave"]


def duotono(im):
    """Lleva un retrato a color a la tinta naranja sobre negro de las láminas de la ODC (como los presos del libro)."""
    g = ImageEnhance.Contrast(im.convert("L")).enhance(1.25)
    pts = [(0, (14, 12, 14)), (95, (120, 52, 22)), (170, (226, 118, 48)), (255, (248, 236, 218))]
    lut = []
    for c in range(3):
        for v in range(256):
            for (a, ca), (b, cb) in zip(pts, pts[1:]):
                if a <= v <= b:
                    lut.append(round(ca[c] + (cb[c] - ca[c]) * (v - a) / (b - a)))
                    break
    r, g_, b_ = (g.point(lut[i * 256:(i + 1) * 256]) for i in range(3))
    return Image.merge("RGB", (r, g_, b_))


def etapa_arte(doc=None):
    for slug in PERSONAL:
        src = Image.open(RAW / f"{slug}.png").convert("RGB")
        w, h = src.size
        d = duotono(src)
        ret = d.crop((int(w * 0.12), 0, int(w * 0.88), h)).resize((520, int(520 * h / (w * 0.76))), Image.LANCZOS)
        token_circular(d, ASSETS / "tokens" / f"{slug}.webp", (234, 124, 40), caja=(int(w * 0.08), int(h * 0.04), int(w * 0.92), int(h * 0.04) + int(w * 0.84)), fondo=NEGRO_ODC)
        guardar(marca.esquina(ret), ASSETS / "odc" / f"{slug}.webp", 86)
    for slug in ICONOS:
        f = RAW / f"icono-{slug}.png"
        if not f.exists():   # el filtro de violencia de la IA rechazó el pincho: se usa el arma real del libro
            import shutil
            shutil.copy(ASSETS / "armas" / "pincho-sierra.webp", ASSETS / "iconos" / f"{slug}.webp")
            continue
        src = Image.open(f).convert("RGB")
        w, h = src.size
        lado = min(w, h)
        c = src.crop(((w - lado) // 2, (h - lado) // 2, (w + lado) // 2, (h + lado) // 2)).resize((256, 256), Image.LANCZOS)
        # esquinas redondeadas
        m = Image.new("L", (768, 768), 0)
        ImageDraw.Draw(m).rounded_rectangle((0, 0, 767, 767), radius=150, fill=255)
        c = c.convert("RGBA")
        c.putalpha(m.resize((256, 256), Image.LANCZOS))
        guardar(marca.esquina(c), ASSETS / "iconos" / f"{slug}.webp", 90)
    print(f"  [OK] {len(PERSONAL)} retratos del personal e {len(ICONOS)} iconos")


def main():
    etapas = sys.argv[1:] or ["ordenes", "cazadores", "odc", "escenas", "planos", "armas", "arte"]
    doc = fitz.open(PDF_PATH)
    for e in etapas:
        globals()[f"etapa_{e}"](doc)
    doc.close()


if __name__ == "__main__":
    main()

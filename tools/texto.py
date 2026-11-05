#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Texto español de «Wages of Sin» tal como lo dejó la tradumaquetación (Trabajo WOS): cada marco de texto del PDF
(posición, cuerpo, color, párrafos en inglés) y la memoria {párrafo EN: párrafo ES} con las correcciones a mano.
Aquí se convierte en datos limpios: HTML por párrafo, orden de lectura por columnas, y las 100 órdenes de busca
con sus campos (objetivo, nivel, delito, cliente, pago, estadísticas…) leídos de la ficha, sin inventar nada.
"""
import html as _html
import json
import re
from pathlib import Path

TRABAJO = Path("/Volumes/Datos_Dock/FoundryVTT/Trabajo WOS/work")
PDF = "/Volumes/Datos_Dock/Rol/01 Sistemas de juego/Colección de sistemas/Mothership/Wages of Sin ESPAÑOL.pdf"
_marcos = None
_mem = None
_cache_marcos = {}


def _cargar():
    global _marcos, _mem
    if _marcos is None:
        _marcos = json.load(open(TRABAJO / "marcos.json"))
        _mem = json.load(open(TRABAJO / "memoria.json"))
        _mem.update(json.load(open(TRABAJO / "correcciones.json")))
    return _marcos, _mem


def es(par):
    return _cargar()[1].get(par, par)


# ───────────────────────── marcado → HTML ─────────────────────────
def html(par):
    """Párrafo con el marcado del motor (<b>, <i>, <s> enlace, <p> superíndice, <t/>, <zNN>, <cRRGGBB>, <faNNNN…/>) a HTML."""
    t = par
    t = re.sub(r"<fa[0-9a-f]+:[^>]*/>|<k\d+/>|<a\d+/>", "", t)
    t = re.sub(r"<t/>", " ", t)
    t = re.sub(r"</?z\d+>|</?c[0-9a-fA-F]{6}>|</?\d*[fcr]>", "", t)
    t = re.sub(r"<p>(.*?)</p>", r"<sup>\1</sup>", t, flags=re.S)
    t = re.sub(r"<s>(.*?)</s>", r'<span class="ref">\1</span>', t, flags=re.S)
    t = re.sub(r"<(?!/?(?:b|i|sup|span|br)\b)[^>]*>", "", t)
    t = t.replace("\n", " ")
    t = re.sub(r"(?:<br>\s*)+$", "", t)
    return re.sub(r"[ \t]{2,}", " ", t).strip()


def plano(par):
    """Solo texto, sin etiquetas."""
    t = re.sub(r"<br>", " ", html(par))
    return _html.unescape(re.sub(r"<[^>]+>", "", t)).strip()


# ───────────────────────── marcos de una página ─────────────────────────
def marcos(pag):
    if pag in _cache_marcos:
        return _cache_marcos[pag]
    m, _ = _cargar()
    out = []
    for f in m:
        if f["pagina"] != pag or f.get("rot") not in ([1.0, 0.0], None):
            continue
        pars = [es(p) for p in f["parrafos"]]
        x0, y0, x1, y1 = f["bbox"]
        out.append({"id": f["id"], "x0": x0, "y0": y0, "x1": x1, "y1": y1, "size": f["size"], "color": f["color"],
                    "pars": pars, "html": [html(p) for p in pars], "txt": " ".join(plano(p) for p in pars)})
    _cache_marcos[pag] = out
    return out


def _es_pie(f):
    return f["y0"] > 645 or f["y0"] < 41


def orden_lectura(frames, ancho=576):
    """Columnas: los marcos anchos cortan la página en franjas; dentro de cada franja, columna izquierda y luego derecha."""
    frames = sorted(frames, key=lambda f: (f["y0"], f["x0"]))
    franjas, actual = [], []
    for f in frames:
        if f["x1"] - f["x0"] > ancho * 0.62:
            if actual:
                franjas.append(actual)
                actual = []
            franjas.append([f])
        else:
            actual.append(f)
    if actual:
        franjas.append(actual)
    res = []
    for fr in franjas:
        izq = sorted([f for f in fr if (f["x0"] + f["x1"]) / 2 < ancho / 2], key=lambda f: f["y0"])
        der = sorted([f for f in fr if (f["x0"] + f["x1"]) / 2 >= ancho / 2], key=lambda f: f["y0"])
        res += izq + der
    return res


def _titular(f):
    """Nivel de título del marco: 'h2' (muy grande), 'h3' (cabecera de sección), 'h4' (negrita suelta corta) o None."""
    t = f["html"][0] if f["html"] else ""
    solo_negrita = bool(re.fullmatch(r"<b>.*</b>", t)) and t.count("<b>") == 1 and len(f["pars"]) == 1
    if f["size"] >= 17 and len(f["txt"]) < 90:
        return "h2"
    if f["size"] >= 11.5 and solo_negrita and len(f["txt"]) < 90:
        return "h3"
    if f["size"] >= 9 and solo_negrita and len(f["txt"]) < 60:
        return "h4"
    return None


def fusionar_filas(frames):
    """Una celda de rango («1-4», «7», «9-0») y el texto de su fila pasan a ser UN solo marco «<b>1-4</b> Corporativo»."""
    rolls = [f for f in frames if RE_RANGO.match(f["txt"]) and f["x1"] - f["x0"] < 45 and f["size"] <= 9.6 and 41 <= f["y0"] <= 645]
    if len(rolls) < 2:
        return frames
    ids_roll = {r["id"] for r in rolls}
    celdas = {r["id"]: [] for r in rolls}
    usados = set()
    for f in frames:
        if f["id"] in ids_roll or f["y0"] < 41 or f["y0"] > 645:
            continue
        cand = [r for r in rolls if abs(f["y0"] - r["y0"]) <= 4 and r["x1"] - 1 <= f["x0"] < r["x1"] + 60]
        if cand:
            celdas[max(cand, key=lambda r: r["x1"])["id"]].append(f)
    res = []
    for f in frames:
        if f["id"] in ids_roll:
            cs = sorted(celdas[f["id"]], key=lambda c: c["x0"])
            if cs:
                usados.update(c["id"] for c in cs)
                h = f"<b>{_html.escape(f['txt'])}</b> " + " · ".join(" ".join(c["html"]) for c in cs)
                res.append({**f, "x1": max(c["x1"] for c in cs), "y1": max(c["y1"] for c in cs), "size": 9.3, "color": "#231f20",
                            "pars": [h], "html": [h], "txt": f["txt"] + " " + " ".join(c["txt"] for c in cs)})
                continue
        if f["id"] not in usados:
            res.append(f)
    return [f for f in res if f["id"] not in usados]


def bloques(frames, saltar=lambda f: False):
    """Marcos en orden de lectura → lista de (tipo, html): h2/h3/h4, p, aside (recuadros laterales de cuerpo pequeño)."""
    out = []
    for f in orden_lectura(fusionar_filas([f for f in frames if not _es_pie(f) and not saltar(f)])):
        if f["color"] == "#808285" or re.match(r"^(Imagen|Image) ", f["txt"]):
            continue
        if re.fullmatch(r"ORDEN|PART.*|MRPG-M6", f["txt"]) or (re.fullmatch(r"\d{1,3}", f["txt"]) and f["size"] > 14):
            continue
        tit = _titular(f)
        if tit:
            out.append((tit, plano(f["pars"][0])))
        else:
            tipo = "aside" if f["size"] <= 8.6 else "p"
            for h in f["html"]:
                if h:
                    out.append((tipo, h))
    return out


def a_html(bl):
    """Bloques → HTML. Las listas con viñeta «•» se agrupan."""
    res, lista = [], []

    def cerrar():
        nonlocal lista
        if lista:
            res.append("<ul>" + "".join(f"<li>{x}</li>" for x in lista) + "</ul>")
            lista = []
    for tipo, h in bl:
        if tipo == "p" and re.match(r"^(?:<[^>]+>)*[•▪·]\s*", h):
            lista.append(re.sub(r"^((?:<[^>]+>)*)[•▪·]\s*", r"\1", h))
            continue
        cerrar()
        if tipo in ("h2", "h3", "h4"):
            res.append(f"<{tipo}>{_html.escape(h, quote=False)}</{tipo}>")
        elif tipo == "aside":
            res.append(f'<aside class="mr-wos-nota"><p>{h}</p></aside>')
        else:
            res.append(f"<p>{h}</p>")
    cerrar()
    return "\n".join(res)


def paginas_html(p_ini, p_fin):
    """HTML de un rango de páginas del libro, con una marca discreta del número de página."""
    partes = []
    for p in range(p_ini, p_fin + 1):
        cuerpo = a_html(bloques(marcos(p)))
        if cuerpo.strip():
            partes.append(f'<p class="mr-wos-pag">pág. {p}</p>\n{cuerpo}')
    return "\n".join(partes)


# ───────────────────────── tablas de dados (celdas sueltas en el PDF) ─────────────────────────
RE_RANGO = re.compile(r"^\s*(\d{1,3}\s*[-–]\s*\d{1,3}|\d{1,3}|00|0)\s*\.?\s*$")
RE_DADO = re.compile(r"^\s*(\d*D\d+)\b", re.I)


def _rango(txt):
    t = txt.replace("–", "-").replace(" ", "")
    a, _, b = t.partition("-")
    return a, (b or a)


def detectar_tablas(frames):
    """Agrupa las celdas de rango («1-4», «7», «9-0») con el texto de su fila. Devuelve (tablas, ids de marcos usados)."""
    rolls = [f for f in frames if RE_RANGO.match(f["txt"]) and f["x1"] - f["x0"] < 45 and f["size"] <= 9.6 and not _es_pie(f)]
    # columnas de rangos alineadas a la derecha (mismo x1)
    cols = []
    for f in sorted(rolls, key=lambda f: (round(f["x1"] / 8), f["y0"])):
        for c in cols:
            if abs(c[0]["x1"] - f["x1"]) < 7 and f["y0"] - c[-1]["y0"] < 70:
                c.append(f)
                break
        else:
            cols.append([f])
    cols = [c for c in cols if len(c) >= 3]
    tablas, usados = [], set()
    for c in cols:
        c = sorted(c, key=lambda f: f["y0"])
        x_text = c[0]["x1"] + 2
        # límite derecho: siguiente columna de rangos a la misma altura, o fin de página
        otras = [o for o in cols if o is not c and o[0]["x0"] > c[0]["x1"] and abs(o[0]["y0"] - c[0]["y0"]) < 40]
        x_lim = min([o[0]["x0"] for o in otras], default=600)
        filas = []
        for r in c:
            celdas = sorted([f for f in frames if f["id"] != r["id"] and abs(f["y0"] - r["y0"]) <= 4 and x_text <= f["x0"] < x_lim
                             and f["id"] not in usados and not RE_RANGO.match(f["txt"])], key=lambda f: f["x0"])
            if not celdas:
                continue
            filas.append((r, celdas))
            usados.update(f["id"] for f in celdas)
            usados.add(r["id"])
        if len(filas) < 3:
            continue
        # cabecera: marcos blancos justo encima de la primera fila (mismo bloque horizontal)
        y_ini = filas[0][0]["y0"]
        cab = sorted([f for f in frames if f["color"] == "#ffffff" and y_ini - 34 < f["y0"] < y_ini - 4 and c[0]["x0"] - 12 <= f["x0"] < x_lim
                      and f["id"] not in usados], key=lambda f: f["x0"])
        usados.update(f["id"] for f in cab)
        titulo_f = [f for f in frames if re.match(r"^(Tabla|TABLA)\s", f["txt"]) and f["x1"] < c[0]["x0"] + 20 and abs(f["y0"] - (cab[0]["y0"] if cab else y_ini)) < 40]
        usados.update(f["id"] for f in titulo_f)
        cab_txt = [plano(f["pars"][0]) for f in cab]
        dado = next((RE_DADO.match(t).group(1).upper() for t in cab_txt if RE_DADO.match(t)), "")
        tablas.append({"y0": (cab[0]["y0"] if cab else y_ini), "x0": c[0]["x0"], "pagina_x": c[0]["x1"],
                       "titulo": (plano(titulo_f[0]["pars"][0]) if titulo_f else ""), "dado": dado,
                       "cabecera": [t for t in cab_txt if not RE_DADO.match(t)],
                       "filas": [{"rango": _rango(r["txt"]), "celdas": [h for f in cs for h in f["html"] if h]} for r, cs in filas]})
    # tablas partidas en dos mitades en la misma banda (D100): se unen en una
    tablas.sort(key=lambda t: (round(t["y0"] / 30), t["x0"]))
    fus = []
    for t in tablas:
        if fus and abs(fus[-1]["y0"] - t["y0"]) < 25 and fus[-1]["dado"] == t["dado"] and t["x0"] > fus[-1]["x0"]:
            fus[-1]["filas"] += t["filas"]
            continue
        fus.append(t)
    return fus, usados


def tabla_html(t):
    cab = ""
    if t["cabecera"]:
        cab = "<thead><tr><th>" + (t["dado"] or "") + "</th>" + "".join(f"<th>{_html.escape(c, quote=False)}</th>" for c in t["cabecera"]) + "</tr></thead>"
    filas = "".join("<tr><th>" + ("-".join(dict.fromkeys(f["rango"]))) + "</th>" + "".join(f"<td>{c}</td>" for c in f["celdas"]) + "</tr>" for f in t["filas"])
    tit = f"<caption>{_html.escape(t['titulo'], quote=False)}</caption>" if t["titulo"] else ""
    return f'<table class="mr-wos-tabla-dados">{tit}{cab}<tbody>{filas}</tbody></table>'


# ───────────────────────── las 100 órdenes de busca ─────────────────────────
def _balancear(v):
    """Quita etiquetas de cierre/apertura sueltas (<b> partido entre la etiqueta y el valor)."""
    for t in ("b", "i"):
        a, c = v.count(f"<{t}>"), v.count(f"</{t}>")
        while c > a:
            v = re.sub(rf"</{t}>", "", v, count=1)
            c -= 1
        while a > c:
            v += f"</{t}>"
            c += 1
    return v


def _ficha(html_par):
    """Ficha «Objetivo: …<br>Nivel: …» → dict {etiqueta en minúsculas: HTML del valor}."""
    d = {}
    for trozo in re.split(r"<br>", html_par):
        m = re.match(r"^\s*(?:<b>)?\s*([^:<]{2,40}?):\s*(?:</b>)?\s*(.*)$", trozo)
        if m:
            d[m.group(1).strip().lower()] = _balancear(m.group(2).strip())
    return d


def paginas_de_ordenes():
    """Página inicial de cada orden 01..100 (la que lleva el retrato de ~380×455)."""
    import fitz
    doc = fitz.open(PDF)
    ini = []
    for i in range(26, 222):
        for im in doc[i].get_images(full=True):
            if 370 <= im[2] <= 430 and 440 <= im[3] <= 462 and im[1] > 0:
                ini.append(i + 1)
                break
    doc.close()
    assert len(ini) == 100
    return ini


def orden(num, p_ini, p_fin):
    pags = {p: marcos(p) for p in range(p_ini, p_fin + 1)}
    primera = pags[p_ini]
    r = {"num": num, "pagina": p_ini, "paginas": [p_ini, p_fin]}
    cab = [f for p in pags.values() for f in p if f["y0"] < 41 and f["x0"] < 200 and f["size"] >= 9 and f["color"] == "#231f20"
           and not f["txt"].startswith("WAGES")]
    r["lugar"] = plano(cab[0]["pars"][0]) if cab else ""
    tit = sorted([f for f in primera if 11.5 <= f["size"] <= 15.4 and f["color"] == "#231f20" and 44 < f["y0"] < 70
                  and not f["txt"].startswith(("Informe", "Anuncio", "Información"))], key=lambda f: -(f["x1"] - f["x0"]))
    r["titulo"] = plano(tit[0]["pars"][0]) if tit else ""
    blf = [f for f in primera if "(BL" in f["txt"] and abs(f["size"] - 15.3) < 0.2]
    m = re.search(r"BL\s*:\s*(\d+)", blf[0]["txt"]) if blf else None
    r["bl"] = int(m.group(1)) if m else None
    sb = [f for f in primera if abs(f["size"] - 20.0) < 0.2 and f["color"] == "#ffffff"]
    r["sebusca"] = re.sub(r"\s", "", plano(sb[0]["pars"][0])) if sb else ""
    ficha, ubic, usados = {}, {}, set()
    for f in primera:
        h0 = f["html"][0] if f["html"] else ""
        if re.match(r"^<b>\s*Objetivos?\s*:", h0):
            ficha = _ficha(h0)
            usados.add(f["id"])
            r["ficha_html"] = h0
        elif re.match(r"^<b>\s*Ubicaci", h0):
            ubic = _ficha(h0)
            usados.add(f["id"])
            r["ubic_html"] = h0
    r["ficha"], r["ubic"] = ficha, ubic
    todos = [f for p in pags.values() for f in p]
    cod = [f for f in todos if f["y0"] > 645 and re.search(r"C[óo]d", f["txt"]) and re.search(r"\d{5,7}", f["txt"])]
    mc = re.search(r"(\d{5,7})", cod[0]["txt"]) if cod else None
    r["codigo"] = mc.group(1) if mc else ""
    r["stats"] = [{"html": f["html"][0], "txt": f["txt"]} for f in todos
                  if f["y0"] > 645 and re.search(r"\[[^\]]*C\s*:\s*\d", f["txt"])]
    anu = [f for f in primera if f["color"] == "#ffffff" and 8.5 < f["size"] < 10 and 70 < f["y0"] < 115]
    r["anuncio"] = anu[0]["html"][0] if anu else ""
    fuera = set(usados)
    for lst in (anu, sb, blf, tit):
        fuera |= {f["id"] for f in lst}
    fuera |= {f["id"] for f in primera if f["size"] > 16 or (abs(f["size"] - 13.3) < 0.2 and f["color"] == "#8bc651")}
    bl = []
    for p in range(p_ini, p_fin + 1):
        bl += bloques(pags[p], saltar=lambda f: f["id"] in fuera or f["x1"] < 45)
    r["bloques"] = bl
    return r


def es_estacion(p):
    """Página de presentación de un lugar (lleva el apartado «PANORAMA»): va antes de sus órdenes, no dentro de la última."""
    return any(f["txt"].strip().upper() == "PANORAMA" for f in marcos(p))


def estaciones():
    res = []
    for p in range(26, 222):
        if es_estacion(p):
            t = max((f for f in marcos(p) if f["y0"] < 100), key=lambda f: f["size"])
            res.append({"pagina": p, "nombre": titulo_caso(plano(t["pars"][0])), "html": paginas_html(p, p)})
    return res


def ordenes():
    ini = paginas_de_ordenes()
    res = []
    for n, p in enumerate(ini, 1):
        fin = (ini[n] - 1) if n < 100 else 221
        while fin > p and es_estacion(fin):
            fin -= 1
        res.append(orden(n, p, fin))
    return res


if __name__ == "__main__":
    import sys
    os_ = ordenes()
    malos = [(o["num"], k) for o in os_ for k in ("titulo", "bl", "sebusca", "codigo", "lugar") if not o[k]]
    print("campos vacíos:", len(malos), malos[:40])
    print("sin ficha:", [o["num"] for o in os_ if not o["ficha"]], "sin estadísticas:", [o["num"] for o in os_ if not o["stats"]])
    if len(sys.argv) > 1:
        o = os_[int(sys.argv[1]) - 1]
        print(json.dumps({k: v for k, v in o.items() if k != "bloques"}, ensure_ascii=False, indent=1)[:2600])
        for t, h in o["bloques"][:14]:
            print(t, h[:110])


def titulo_caso(t):
    """MAYÚSCULAS del libro → Mayúsculas Y Minúsculas de nombre propio (con partículas en minúscula)."""
    chicas = {"de", "del", "la", "las", "los", "el", "y", "o", "a", "en", "por", "con"}
    pal = t.title().split(" ")
    return " ".join(w.lower() if (i and w.lower() in chicas) else w for i, w in enumerate(pal))


# ───────────────────────── los 10 cazarrecompensas ─────────────────────────
HUNTER_SPREADS = [230, 232, 234, 236, 238, 240, 242, 244, 246, 248]


def cazadores():
    res = []
    for i, pl in enumerate(HUNTER_SPREADS, 1):
        fr = marcos(pl) + marcos(pl + 1)
        tf = sorted([f for f in marcos(pl) if f["color"] == "#ffffff" and 11.5 <= f["size"] <= 15.4 and 38 < f["y0"] < 75 and f["x0"] < 290
                     and not f["txt"].startswith("(BLs") and not RE_RANGO.match(f["txt"]) and not re.match(r"^\d\)", f["txt"])], key=lambda f: f["y0"])
        nombre = re.sub(r",\s*,", ",", ", ".join(re.sub(r"\s*\(BLs:?\s*$", "", plano(f["pars"][0])).strip() for f in tf))
        bls = sorted({int(n) for f in fr if abs(f["size"] - 15.3) < 0.2 and f["color"] == "#ffffff"
                      for n in re.findall(r"(\d)\)", f["txt"])})
        pago = next((f["html"][0] for f in fr if re.match(r"^<b>(Salario|Paga|Pago|Sueldo)", f["html"][0] if f["html"] else "")), "")
        miembros = []
        rojos = sorted([f for f in fr if f["color"] == "#d92028" and 11 <= f["size"] <= 12.5], key=lambda f: (f["x0"] // 300, f["y0"]))
        for n in rojos:
            stat = next((f for f in fr if re.search(r"\[C\s*:", f["txt"]) and abs(f["x0"] - n["x0"]) < 8 and 0 < f["y0"] - n["y0"] < 30), None)
            eq = next((f for f in fr if f["size"] > 9 and f["color"] == "#231f20" and "•" in f["txt"] and abs(f["x0"] - n["x0"]) < 12 and f["y0"] > n["y0"]), None)
            miembros.append({"nombre": plano(n["pars"][0]), "stat": stat["txt"] if stat else "", "stat_html": stat["html"][0] if stat else "",
                             "equipo": [re.sub(r"^\s*•\s*", "", plano(p)) for p in eq["pars"] if p.strip()] if eq else []})
        if not miembros:   # un solo cazador: ficha en columna, sin nombre propio en rojo
            stat = next((f for f in fr if re.search(r"\[C\s*:", f["txt"]) and f["size"] < 9), None)
            if stat:
                eq = next((f for f in fr if f["size"] > 9 and "•" in f["txt"] and f["y0"] > stat["y0"] and abs(f["x0"] - stat["x0"]) < 20), None)
                miembros.append({"nombre": titulo_caso(nombre), "stat": stat["txt"], "stat_html": stat["html"][0],
                                 "equipo": [re.sub(r"^\s*•\s*", "", plano(p)) for p in eq["pars"] if p.strip()] if eq else []})
        res.append({"num": i, "paginas": [pl, pl + 1], "nombre": nombre, "bls": bls, "pago": pago, "miembros": miembros,
                    "html": paginas_html(pl, pl + 1)})
    return res


# ───────────────────────── las 3 naves ─────────────────────────
def nave(pl):
    fr = marcos(pl)
    num = lambda f: int(re.sub(r"\D", "", f["txt"]) or 0)
    nombre = next(plano(f["pars"][0]) for f in fr if abs(f["size"] - 15.3) < 0.2 and f["y0"] < 70 and f["color"] == "#231f20")
    modelo = next((plano(f["pars"][0]) for f in fr if abs(f["size"] - 8.3) < 0.2 and f["y0"] < 80 and f["x0"] < 300), "")
    grandes = sorted([f for f in fr if abs(f["size"] - 12.0) < 0.2 and f["y0"] < 120], key=lambda f: f["x0"])
    r = {"pagina": pl, "nombre": nombre, "modelo": modelo, "pro": num(grandes[0]), "bat": num(grandes[1]), "sis": num(grandes[2])}
    coste = next((plano(f["pars"][0]) for f in fr if f["txt"].startswith("Coste")), "")
    r["coste"] = re.sub(r"^Coste:\s*", "", coste)
    r["casco"] = int(re.search(r"Casco:\s*(\d+)", " ".join(f["txt"] for f in fr)).group(1))
    dos = [f for f in fr if len(f["pars"]) == 1 and f["pars"][0].count("<br>") == 1 and re.fullmatch(r"(<b>)?(<s>)?(<b>)?\d+.*", f["pars"][0].replace("\n", ""))
           and 130 < f["y0"] < 180 and f["size"] < 9]
    dos = sorted(dos, key=lambda f: f["x0"])
    n0 = [int(x) for x in re.findall(r"\d+", dos[0]["txt"])]
    n1 = [int(x) for x in re.findall(r"\d+", dos[1]["txt"])]
    r.update({"trip": n0[0], "fuel": n0[1], "cryo": n1[0], "escape": n1[1]})
    r["anclajes"] = next((plano(f["pars"][0]) for f in fr if "Anclajes" in f["txt"]), "")
    r["megadanio"] = next((plano(f["pars"][0]) for f in fr if f["txt"].startswith("Megada")), "")
    r["mejoras_cab"] = next((plano(f["pars"][0]) for f in fr if "Mejoras" in f["txt"] and f["size"] < 9), "")
    izq = [f for f in fr if f["x0"] < 135 and 190 < f["y0"] < 330 and f["color"] == "#231f20"]
    r["lineas_izq"] = [(round(f["y0"]), plano(" ".join(f["pars"]))) for f in sorted(izq, key=lambda f: f["y0"])]
    r["descripcion_html"] = "".join(f"<p>{h}</p>" for f in sorted([f for f in fr if f["size"] == 9.3 and f["x0"] >= 230 and f["y0"] < 160 and f["color"] == "#231f20"], key=lambda f: f["y0"]) for h in f["html"])
    r["html"] = paginas_html(pl, pl + 1)
    return r


# ───────────────────────── estadísticas «[C:30 I:43 PA:5 H:2(15) RD:3]» ─────────────────────────
def parsear_stats(txt):
    """Solo lo que el libro escribe: None si falta. Arma y daño si la línea los trae («C:30 Puños 2 DAÑO I:43 …»)."""
    def g(p):
        m = re.search(p, txt)
        return int(m.group(1)) if m else None
    r = {"combat": g(r"\bC\s*:\s*(\d+)"), "instinct": g(r"\bI\s*:\s*(\d+)"), "armor": g(r"\bPA\s*:\s*(\d+)"), "dr": g(r"\bRD\s*:\s*(\d+)"),
         "loyalty": g(r"Lealtad:?\s*(\d+)"), "bribe": g(r"Soborno:?\s*(\d+)")}
    m = re.search(r"\bH\s*:\s*(\d+)\s*\(\s*(\d+)\s*\)", txt)
    r["wounds"], r["health"] = (int(m.group(1)), int(m.group(2))) if m else (None, None)
    m = re.search(r"\bC\s*:\s*\d+\s+([^\[\]:]+?)\s+(\d+d\d+(?:[+-]\d+)?|\d+)\s*DAÑO", txt, re.I)
    r["arma"], r["danio"] = (m.group(1).strip(" .,-"), m.group(2)) if m else (None, None)
    return r


# ───────────────────────── armas de prisión (pág. 277) ─────────────────────────
def armas_prision():
    fr = marcos(277)
    nombres = [f for f in fr if f["color"] == "#e26828" and abs(f["size"] - 9.3) < 0.1 and f["html"] and f["html"][0].startswith("<b>")
               and 150 < f["y0"] < 640]
    res = []
    for n in sorted(nombres, key=lambda f: (round(f["y0"] / 120), f["x0"])):
        cuerpo = [f for f in fr if f["id"] != n["id"] and abs(f["size"] - 9.3) < 0.1 and f["color"] in ("#ffffff", "#e26828")
                  and abs(f["x0"] - n["x0"]) <= 3 and n["y0"] <= f["y0"] < n["y0"] + 95 and f not in nombres]
        cuerpo.sort(key=lambda f: f["y0"])
        linea = [h for f in cuerpo for h in f["html"]]
        txt = " ".join(plano(h) for h in linea)
        mc = re.findall(r"(\d+)\s*cr\b", txt)
        dmg = re.search(r"(\d+d\d+(?:[+-]\d+)?|\d+)\s*DAÑO", txt)
        res.append({"nombre": plano(n["pars"][0]).replace(" / ", " / "), "linea": linea, "txt": txt,
                    "coste": int(mc[-1]) if mc else 0, "robar": "robarse" in txt.lower(),
                    "danio": ("1d5" if "Anillos" in plano(n["pars"][0]) else (dmg.group(1) if dmg and "d" in dmg.group(1) else ""))})
    return res


# ───────────────────────── presos y personal de la ODC ─────────────────────────
def presos():
    res = []
    for p in range(281, 296):
        fr = marcos(p)
        ids = sorted([f for f in fr if f["color"] == "#e26828" and abs(f["size"] - 10.3) < 0.1 and re.fullmatch(r"#\d{4}", f["txt"])], key=lambda f: f["y0"])
        for i, idf in enumerate(ids):
            y1 = ids[i + 1]["y0"] if i + 1 < len(ids) else 640
            cuerpo = sorted([f for f in fr if idf["x1"] < f["x0"] < idf["x1"] + 45 and idf["y0"] - 3 <= f["y0"] < y1 - 3 and f["size"] < 10], key=lambda f: f["y0"])
            if not cuerpo:
                continue
            txt = " ".join(f["txt"] for f in cuerpo)
            m = re.match(r"^([^,|]+),([^|]*)\|", cuerpo[0]["txt"])
            nums = re.findall(r"\d+", m.group(2)) if m else []
            res.append({"num": idf["txt"][1:], "nombre": (m.group(1) if m else cuerpo[0]["txt"].split(",")[0]).strip(),
                        "edad": int(nums[-1]) if nums else None, "pagina": p, "html": [h for f in cuerpo for h in f["html"]], "txt": txt,
                        "stats": parsear_stats(txt)})
    return res


def personal():
    fr = marcos(298)
    res = []
    for f in sorted(fr, key=lambda f: f["y0"]):
        if f["x0"] > 140 and f["x0"] < 150 and 300 < f["y0"] < 600 or (f["x0"] < 90 and 410 < f["y0"] < 420):
            m = re.match(r"^(?:JEFE DE FUNCIONARIOS\s+)?([A-ZÁÉÍÓÚÑ][^,|]+?),\s*(\d+)\s*\|", f["txt"])
            if m:
                res.append({"nombre": m.group(1).strip(), "edad": int(m.group(2)), "html": f["html"][0], "txt": f["txt"], "y0": f["y0"],
                            "stats": parsear_stats(f["txt"])})
    # Kyou Aoki: su descripción es el marco siguiente
    for r in res:
        if not re.search(r"\.\s*\S{20}", r["txt"]):
            sig = next((f for f in fr if abs(f["x0"] - 144) < 3 and 0 < f["y0"] - r["y0"] < 20 and f["size"] < 10), None)
            if sig:
                r["html"] += "<br>" + sig["html"][0]
                r["txt"] += " " + sig["txt"]
    return res


# ───────────────────────── fauna de Offit (págs. 306-310) ─────────────────────────
def fauna():
    res = []
    for p in range(306, 311):
        fr = marcos(p)
        for n in sorted([f for f in fr if f["color"] == "#e26828" and abs(f["size"] - 13.3) < 0.1 and re.match(r"^<b>\d+\.", f["html"][0])], key=lambda f: (f["x0"] // 250, f["y0"])):
            col = [f for f in fr if abs(f["x0"] - n["x0"]) < 14 and f["id"] != n["id"] and f["y0"] > n["y0"] and 9 < f["size"] + 0 and f["y0"] > 40 and f["y0"] < 640
                   and f["color"] in ("#ffffff",) and abs(f["size"] - 9.3) < 0.1]
            st = next((f for f in fr if re.search(r"\[C\s*:", f["txt"]) and abs(f["x0"] - n["x0"]) < 6 and abs(f["y0"] - n["y0"]) < 40), None)
            col.sort(key=lambda f: f["y0"])
            m = re.match(r"^(\d+)\.\s*(.+?)\s*(?:\((.+)\))?$", plano(n["pars"][0]))
            res.append({"num": int(m.group(1)), "nombre": m.group(2).strip(), "alias": (m.group(3) or "").strip(), "pagina": p,
                        "stat": st["txt"] if st else "", "stats": parsear_stats(st["txt"]) if st else {},
                        "parrafos": [h for f in col for h in f["html"]]})
    return sorted(res, key=lambda r: r["num"])


# ───────────────────────── equipos iniciales (págs. 318-319) ─────────────────────────
def equipos_iniciales():
    res = []
    for pg in (318, 319):
        fr = marcos(pg)
        for h in sorted([f for f in fr if abs(f["size"] - 13.3) < 0.2 and f["y0"] > 100], key=lambda f: f["y0"]):
            roll = next((f for f in fr if f["y0"] > h["y0"] and f["y0"] - h["y0"] < 50 and re.match(r"^0?\d(?:\s*0?\d)+$", f["txt"].replace("¿", ""))), None)
            txt = next((f for f in fr if f["y0"] > h["y0"] and f["y0"] - h["y0"] < 50 and roll and f["x0"] > roll["x1"] and f["x0"] < roll["x1"] + 30
                        and f["id"] != roll["id"] and f["size"] > 9 and f["color"] == "#231f20"), None)
            if not roll or not txt:
                continue
            # la extracción juntó algunas filas en una sola línea: se separan donde acaba una frase y empieza otra con mayúscula
            filas = [y.strip() for x in re.split(r"<br>", " <br>".join(txt["html"])) for y in re.split(r"(?<=\.)\s+(?=(?:<[^>]+>)*[A-ZÁÉÍÓÚÑ])", x) if y.strip()]
            union = []
            for fl in filas:      # una frase partida dentro de un paréntesis pertenece a la misma fila
                if union and plano(union[-1]).count("(") > plano(union[-1]).count(")"):
                    union[-1] += " " + fl
                else:
                    union.append(fl)
            res.append({"clase": plano(h["pars"][0]), "pagina": pg, "filas": union})
    return res

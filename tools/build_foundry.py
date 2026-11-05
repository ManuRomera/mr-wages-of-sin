#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Construye _data/*.json (compendios) y content/*.json desde el TEXTO REAL del libro en español (tools/texto.py)
y el arte extraído del PDF (tools/extract_assets.py). Nada se inventa: lo que el libro no da (p. ej. estadísticas de
un objetivo sin ficha) se deja vacío o se avisa en la propia ficha.

  python3 tools/extract_assets.py     # arte (una vez)
  python3 tools/build_foundry.py      # datos
  node scripts/build.mjs              # packs LevelDB + dist/module.zip
"""
import copy
import hashlib
import html
import json
import re
import sys
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
import equipo as eq  # noqa: E402
import texto  # noqa: E402

MOD = "mr-wages-of-sin"
RAIZ = Path(__file__).resolve().parent.parent
DATA_DIR = RAIZ / "_data"
CONTENT_DIR = RAIZ / "content"
ASSETS = RAIZ / "assets"
AHORA = 1762320000000
ABC62 = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
_usados, _cache = set(), {}


def fid(clave):
    """_id determinista de 16 caracteres (base62 de sha256)."""
    if clave in _cache:
        return _cache[clave]
    num = int.from_bytes(hashlib.sha256(f"mr-wages:{clave}".encode()).digest()[:12], "big")
    cand = ""
    for _ in range(16):
        cand += ABC62[num % 62]
        num //= 62
    n = 1
    while cand in _usados:
        cand = cand[:14] + ABC62[n % 62] + ABC62[(n * 7) % 62]
        n += 1
    _usados.add(cand)
    _cache[clave] = cand
    return cand


def stats_doc(system_id="mosh"):
    return {"systemId": system_id, "systemVersion": "0.6.1" if system_id else None, "coreVersion": "13",
            "createdTime": AHORA, "modifiedTime": AHORA}


def esc(s):
    return html.escape(str(s or ""), quote=True)


def ruta(rel):
    return f"modules/{MOD}/assets/{rel}"


def existe(rel):
    return (ASSETS / rel).exists()


def slug(t):
    t = re.sub(r"[^a-z0-9]+", "-", texto.plano(t).lower().replace("ñ", "n"))
    return t.strip("-")


HAB_ES = Path("/Volumes/Datos_Dock/FoundryVTT/Data/modules/mr-mothership-es/_data/habilidades.json")
_HAB = {}


def _cargar_habilidades():
    """Las habilidades de Mothership 1e en español (módulo MR- Mothership en español): nombre → objetos por rango."""
    if _HAB:
        return
    for d in json.load(open(HAB_ES)):
        if d.get("type") == "skill" and d["system"].get("bonus"):
            _HAB.setdefault(d["name"].lower(), []).append(d)


def habilidad(actor_id, nombre, rango=None):
    """Copia de una habilidad del compendio de MR- Mothership en español para una ficha."""
    _cargar_habilidades()
    cands = _HAB[nombre.lower()]
    orden = {"Trained": 0, "Expert": 1, "Master": 2}
    d = next((c for c in cands if c["system"]["rank"] == rango), None) if rango else sorted(cands, key=lambda c: orden[c["system"]["rank"]])[0]
    return {"_id": fid(f"{actor_id}:sk:{d['_id']}"), "name": d["name"], "type": "skill", "img": d["img"],
            "system": {"description": d["system"].get("description", ""), "rank": d["system"]["rank"], "bonus": d["system"]["bonus"], "prerequisite_ids": d["system"].get("prerequisite_ids", [])},
            "effects": [], "flags": {"core": {"sourceId": f"Compendium.mr-mothership-es.habilidades.Item.{d['_id']}"}}, "folder": None, "_stats": stats_doc()}


def uuid_habilidad(nombre, rango=None):
    _cargar_habilidades()
    cands = _HAB[nombre.lower()]
    orden = {"Trained": 0, "Expert": 1, "Master": 2}
    d = next((c for c in cands if c["system"]["rank"] == rango), None) if rango else sorted(cands, key=lambda c: orden[c["system"]["rank"]])[0]
    return f"Compendium.mr-mothership-es.habilidades.Item.{d['_id']}"


# Habilidades que el libro NO da y propone el módulo, por palabras del texto de cada ficha (máx. 3, siempre al menos una)
TRABAJOS = [(r"tala|aserradero|desramado|desbroce|arrastre|desembosque|desmonte|amputaci", ["Equipo industrial"]), (r"cocina", ["Química"]), (r"taller", ["Reparación"]),
            (r"enfermer", ["Medicina de campo"])]
OFICIOS = [(r"hacker|hackeo|informátic|intrusi|ciber|piratería informática|equipos de hackeo|caja negra", ["Hackeo", "Computadoras"]),
           (r"zoólog|animal|criatura|bestia", ["Zoología"]), (r"artificiero|explosiv|bomba", ["Explosivos", "Química"]),
           (r"general|soldado|militar|mercenari|tropas|veterano|ejército|desert|reclutamiento|guerra|tte\.|teniente|capitán|sargento|coronel|comandante|oficial|marine", ["Entrenamiento militar", "Armas de fuego"]),
           (r"médic|cirujan|doctor|enfermer|medicina", ["Medicina de campo"]), (r"científic|investigador|biólog|químic|laboratorio", ["Química", "Matemáticas"]),
           (r"piloto|capitán|nave|atraque|transportista|secuestro de nave", ["Pilotar"]), (r"pirata|piratería|contraband|ladrón|bandido|hurto|robo|saqueo|receptaci|allanamiento|extorsi|chantaje",
            ["Conocimientos del Borde Exterior"]), (r"asesin|sicari|agresi|terroris|amenaza|violen|armas", ["Combate cuerpo a cuerpo"]),
           (r"fraude|falsific|corrupci|despilfarro|blanqueo|evasi|empleo fraudulento|manipulaci|alteraci|revelaci|información protegida|pirata de|distribuci", ["Computadoras"]),
           (r"droga|farmac|químic", ["Química"]), (r"ingenier|mecánic|reparaci|maquinaria", ["Reparación", "Mecánica"]), (r"ejecutiv|corporativ|directiv|empresa|compañía", ["Lingüística", "Computadoras"]),
           (r"artist|pintor|músic|actor|actriz|influencer|streamer", ["Arte"]), (r"sacerdot|teólog|secta|culto|profeta|religi", ["Teología"]), (r"mensajer|correo|corredor|atleta", ["Atletismo"]),
           (r"profesor|decano|académic|escritor|periodista|lingü", ["Lingüística"])]
FUERA = {"Mecánica": "Expert", "Hackeo": "Expert", "Explosivos": "Expert", "Pilotar": "Expert", "Armas de fuego": "Expert", "Combate cuerpo a cuerpo": "Expert", "Medicina de campo": "Expert"}


def habilidades_de(texto_ficha, trabajos=False):
    """Hasta 3 habilidades que encajan con el texto (oficio, delito o trabajo de la ODC). Si nada encaja, Atletismo."""
    t = texto_ficha.lower()
    out = []
    for lista in ((TRABAJOS, OFICIOS) if trabajos else (OFICIOS,)):
        for patron, nombres in lista:
            if re.search(patron, t):
                for n in nombres:
                    if n not in out:
                        out.append(n)
    return (out or ["Atletismo"])[:3]


CAT = eq.Catalogo(fid, stats_doc, ruta, existe)
PRISION_DOCS = {}      # icono → objeto de arma de prisión (se rellena en construir_equipo)


def doc_de(k):
    """Objeto del catálogo o arma de prisión por su clave."""
    return PRISION_DOCS[k.split(":")[1]] if k.startswith("prision:") else CAT.items[k]


def embeber(actor_id, comp):
    """Copia del objeto para una ficha (con su cantidad). `comp` es un texto del libro («Pistola de bengalas», «granada (x2)»)."""
    k, qty = CAT.objeto(comp, "ficha")
    d = copy.deepcopy(doc_de(k))
    d["_id"] = fid(f"{actor_id}:{k}")
    d["folder"] = None
    if d["type"] == "item":
        d["system"]["quantity"] = qty
    return d


# ───────────────────────── carpetas (todo en su sitio al importar) ─────────────────────────
CARPETAS = []


def carpeta(tipo, clave, nombre, padre=None, color=None):
    d = {"_id": fid(f"carpeta:{tipo}:{clave}"), "name": nombre, "type": tipo, "folder": padre["_id"] if padre else None,
         "sorting": "m", "sort": 100000 + len([c for c in CARPETAS if c["type"] == tipo]) * 10000, "color": color,
         "flags": {MOD: {"clave": clave}}, "_stats": stats_doc()}
    CARPETAS.append(d)
    return d


# ───────────────────────── las 100 órdenes de busca ─────────────────────────
def _val(h):
    return texto.plano(h) if h else ""


def datos_ordenes():
    ords = []
    for r in texto.ordenes():
        num = r["num"]
        if num == 50:      # página especial girada: nivel y estado están en marcos rotados
            r["bl"] = 8
            r["sebusca"] = "VIVO.O.MUERTO"
        f, u = r["ficha"], r["ubic"]
        titulo = r["titulo"]
        if num == 50:
            titulo = "zPotato, Hacker"
        else:
            nom, _, resto = titulo.partition(",")
            titulo = texto.titulo_caso(nom) + ((", " + resto.strip().lower()) if resto.strip() else "")
        sb = r["sebusca"].upper()
        se_busca = "Vivo o muerto" if "VIVO.O.MUERTO" in sb else ("Vivo" if "VIVO" in sb else ("Muerto" if "MUERTO" in sb else _val(f.get("se busca"))))
        idx = next((i for i, (t, h) in enumerate(r["bloques"]) if t == "h3" and h.lower().startswith("informaci")), None)
        publico = r["bloques"][:idx] if idx is not None else r["bloques"]
        secreto = r["bloques"][idx + 1:] if idx is not None else []
        informe = " ".join(texto.plano(h) for t, h in publico if t == "p")
        st = r["stats"][0]["txt"] if r["stats"] else ""
        mst = re.search(r"\[[^\]]*C\s*:\s*\d[^\]]*\]", st)
        o = {
            "num": num, "codigo": r["codigo"], "titulo": titulo, "bl": r["bl"], "seBusca": se_busca, "lugar": texto.titulo_caso(r["lugar"]),
            "delito": _val(f.get("delito")), "cliente": _val(f.get("cliente")),
            "pago": _val(f.get("pago") or f.get("recompensa")), "prima": _val(f.get("prima")),
            "entrega": _val(u.get("punto de entrega") or u.get("entrega")),
            "paradero": _val(u.get("última ubicación conocida") or u.get("última ubicación")),
            "pagina": r["pagina"], "anuncio": texto.plano(r["anuncio"]), "informe": informe[:900],
            "statStr": mst.group(0) if mst else "", "stats_lineas": r["stats"], "ficha": f, "ubic": u,
            "publico": publico, "secreto": secreto, "anuncio_html": r["anuncio"],
            "img": ruta(f"objetivos/orden-{num:03d}.webp"), "token": ruta(f"tokens/orden-{num:03d}.webp"),
            "actorId": fid(f"actor:orden:{num:03d}"),
        }
        o["etiquetas"] = " · ".join(x for x in (o["lugar"], o["delito"]) if x)
        ords.append(o)
    return ords


def html_orden_pagina(o):
    filas = "".join(f"<tr><th>{esc(k.capitalize())}</th><td>{v}</td></tr>" for k, v in o["ficha"].items())
    ubic = "".join(f"<tr><th>{esc(k.capitalize())}</th><td>{v}</td></tr>" for k, v in o["ubic"].items())
    pub = texto.a_html(o["publico"])
    sec = texto.a_html(o["secreto"])
    notas = "".join(f"<li>{ln['html']}</li>" for ln in o["stats_lineas"])
    ficha_actor = f"@UUID[Compendium.{MOD}.objetivos.Actor.{o['actorId']}]{{Ficha del objetivo}}"
    cod = f'<div class="mr-wos-cod">CÓD. PERS. {esc(o["codigo"])} · PÁG. {o["pagina"]}</div>' if o["codigo"] else f'<div class="mr-wos-cod">PÁG. {o["pagina"]}</div>'
    lugar = f'<p class="mr-wos-lugar">{esc(o["lugar"])}</p>' if o["lugar"] else ""
    anuncio = f'<blockquote class="mr-wos-anuncio">{o["anuncio_html"]}</blockquote>' if o["anuncio_html"] else ""
    stats = f'<h4>Estadísticas</h4><ul class="mr-wos-stats">{notas}</ul>' if notas else "<p><em>El libro no da estadísticas para este objetivo.</em></p>"
    return f"""
<div class="mr-wos-orden" data-orden="{o['num']}">
  <div class="mr-wos-cartel">
    <div class="mr-wos-cartel-foto">
      <img src="{o['img']}" alt="{esc(o['titulo'])}" />
      <div class="mr-wos-sello">BL:{o['bl']} · {esc(o['seBusca'].upper())}</div>
      {cod}
    </div>
    <div class="mr-wos-cartel-datos">
      <h2>ORDEN {o['num']:02d} · {esc(o['titulo'])}</h2>
      {lugar}
      {anuncio}
      <table class="mr-wos-tabla"><tbody>{filas}{ubic}</tbody></table>
      <div class="mr-wos-acciones-orden">
        <button type="button" data-mrwages-action="publicar-cartel" data-orden="{o['num']}"><i class="fa-solid fa-bullhorn"></i> Mostrar cartel a la mesa</button>
        <button type="button" data-mrwages-action="abrir-actor" data-actor-id="{o['actorId']}"><i class="fa-solid fa-crosshairs"></i> Ficha del objetivo</button>
      </div>
    </div>
  </div>
  {pub}
  <section class="secret">
    <h3>Información del Guardián</h3>
    {sec}
    {stats}
    <p>{ficha_actor}</p>
  </section>
</div>
""".strip()


def construir_diarios_ordenes(ordenes, carp):
    bloques = [("ordenes-001-020", "Órdenes de busca 01–20", ordenes[0:20]), ("ordenes-021-040", "Órdenes de busca 21–40", ordenes[20:40]),
               ("ordenes-041-060", "Órdenes de busca 41–60", ordenes[40:60]), ("ordenes-061-080", "Órdenes de busca 61–80", ordenes[60:80]),
               ("ordenes-081-100", "Órdenes de busca 81–100", ordenes[80:100])]
    diarios = []
    for d_idx, (clave, nombre, lista) in enumerate(bloques):
        pages = [{"_id": fid(f"pagina-orden:{o['num']:03d}"), "name": f"{o['num']:02d} · {o['titulo']} (BL:{o['bl']})", "type": "text",
                  "sort": 100000 + i * 10000, "title": {"show": True, "level": 1},
                  "text": {"format": 1, "content": html_orden_pagina(o)}, "flags": {MOD: {"orden": o["num"], "bl": o["bl"]}},
                  "_stats": stats_doc(None)} for i, o in enumerate(lista)]
        diarios.append({"_id": fid(f"diario-ordenes:{clave}"), "name": nombre, "pages": pages, "folder": carp["_id"],
                        "sort": 100000 + d_idx * 10000, "ownership": {"default": 0}, "flags": {MOD: {"clave": clave}}, "_stats": stats_doc()})
    return diarios


# ───────────────────────── actores ─────────────────────────
def crear_actor(actor_id, nombre, img, token, figura, st, bio, flags=None, arma=None, carp=None, equipo=None, habilidades=None):
    """Criatura de mosh con SOLO las cifras que da el libro (las que faltan quedan en un valor corriente)."""
    cb = st.get("combat") if st.get("combat") is not None else 30
    ins = st.get("instinct") if st.get("instinct") is not None else 30
    s = {"biography": bio, "description": bio,
         "health": {"value": st.get("health") or 10, "min": 0, "max": st.get("health") or 10, "label": "Salud"},
         "hits": {"value": 0, "min": 0, "max": st.get("wounds") or 2, "label": "Heridas"},
         "stats": {
             "combat": {"value": cb, "min": 0, "max": 99, "label": "Combate", "rollLabel": "Tirada de Combate", "enabled": True},
             "instinct": {"value": ins, "min": 0, "max": 99, "label": "Instinto", "rollLabel": "Tirada de Instinto", "enabled": True},
             "armor": {"value": st.get("armor") or 0, "mod": 0, "min": 0, "max": 99, "damageReduction": st.get("dr") or 0, "label": "Armadura", "enabled": bool(st.get("armor"))},
             "loyalty": {"value": st.get("loyalty") if st.get("loyalty") is not None else 30, "min": 0, "max": 99, "label": "Lealtad", "enabled": st.get("loyalty") is not None},
         }}
    items = [embeber(actor_id, c) for c in (equipo or [])] + [habilidad(actor_id, n, FUERA.get(n) if n in FUERA else None) for n in (habilidades or [])]
    if arma and arma[0] and arma[1]:      # ataque con su daño, tal como lo escribe la línea de estadísticas
        items.append({"_id": fid(f"item:arma:{actor_id}"), "name": arma[0], "type": "weapon", "img": CAT._img("arma:arma-fuego") if False else ruta("iconos/cat-arma-fuego.webp") if existe("iconos/cat-arma-fuego.webp") else ruta("iconos/equipo.webp"),
                      "system": {"description": f"<p>Ataque de {esc(nombre)} (del libro).</p>", "damage": arma[1], "shots": 1, "curShots": 1, "useAmmo": False, "ranges": {"value": ""}},
                      "effects": [], "flags": {}, "_stats": stats_doc()})
    elif arma and arma[0]:                # arma con nombre pero sin daño en la línea: objeto del catálogo
        items.append(embeber(actor_id, arma[0]))
    fl = {"tipo": "pnj", **(flags or {})}
    if figura:
        fl["figura"] = figura
    return {"_id": actor_id, "name": nombre, "type": "creature", "img": img, "system": s,
            "prototypeToken": {"name": re.sub(r"^#?\d+\s*·\s*", "", nombre)[:30], "displayName": 20, "actorLink": False, "width": 1, "height": 1,
                               "texture": {"src": token, "fit": "contain", "scaleX": 1, "scaleY": 1},
                               "bar1": {"attribute": "health"}, "bar2": {"attribute": "hits"}},
            "items": items, "effects": [], "folder": carp["_id"] if carp else None, "ownership": {"default": 0}, "flags": {MOD: fl}, "_stats": stats_doc()}


def _uuid_orden(o):
    n = o["num"]
    dj = fid(f"diario-ordenes:ordenes-{(n - 1) // 20 * 20 + 1:03d}-{((n - 1) // 20 + 1) * 20:03d}")
    return f"@UUID[Compendium.{MOD}.ordenes.JournalEntry.{dj}.JournalEntryPage.{fid(f'pagina-orden:{n:03d}')}]{{Orden de busca completa}}"


def actores_objetivo(ordenes):
    out = []
    for o in ordenes:
        lineas = o["stats_lineas"]
        st = texto.parsear_stats(lineas[0]["txt"]) if lineas else {}
        aviso = "" if lineas else "<p><em>El libro no da estadísticas para este objetivo: se han dejado valores corrientes (C:30 I:30) que puedes ajustar.</em></p>"
        stats_html = "".join(f"<li>{ln['html']}</li>" for ln in lineas)
        pago = f" · Pago: {esc(o['pago'])}" if o["pago"] else ""
        entrega = f" · Entrega: {esc(o['entrega'])}" if o["entrega"] else ""
        anuncio = f"<p>{esc(o['anuncio'])}</p>" if o["anuncio"] else ""
        lista = f"<ul>{stats_html}</ul>" if stats_html else ""
        bio = f"<p><strong>Orden {o['num']:02d} · BL:{o['bl']} · {esc(o['seBusca'])}</strong>{pago}{entrega}</p>{anuncio}{aviso}{lista}<p>{_uuid_orden(o)}</p>"
        out.append(crear_actor(o["actorId"], f"{o['num']:02d} · {o['titulo']}", o["img"], o["token"], None, st, bio,
                               {"categoria": "objetivo", "orden": o["num"], "bl": o["bl"], "seBusca": o["seBusca"], "pago": o["pago"]},
                               arma=(st.get("arma"), st.get("danio")), habilidades=habilidades_de(" ".join([o["titulo"], o["delito"], o["informe"][:250]]))))
    return out


def datos_cazadores():
    cs = texto.cazadores()
    for c in cs:
        c["titulo"] = texto.titulo_caso(c["nombre"])
    return cs


def _habilidad(actor_id, texto_ln):
    """«Manos asesinas: 2d10 DAÑO. Desgarro.» → objeto de tipo habilidad especial (ability) de la ficha."""
    m = re.match(r"^([^:–-]{3,45}?)\s*[:–-]\s*(.+)$", texto_ln)
    if not m or not re.search(r"DAÑO|Salvación|Lanzallamas|Estrés", texto_ln):
        return None
    nombre = m.group(1).strip()
    return {"_id": fid(f"{actor_id}:hab:{eq.clave(nombre)}"), "name": nombre, "type": "ability", "img": ruta("iconos/cat-habilidad.webp") if existe("iconos/cat-habilidad.webp") else ruta("iconos/equipo.webp"),
            "system": {"description": f"<p>{esc(m.group(2))}</p>", "text": m.group(2).strip(), "roll": ""}, "effects": [], "flags": {}, "folder": None, "_stats": stats_doc()}


HAB_CAZADORES = {   # (equipo, miembro) → habilidades que propone el módulo (el libro no da ninguna)
    (1, 0): ["Entrenamiento militar", "Combate cuerpo a cuerpo", "Armas de fuego"],
    (2, 0): ["Hackeo", "Computadoras"], (2, 1): ["Hackeo", "Computadoras"], (2, 2): ["Hackeo", "Computadoras", "Armas de fuego"], (2, 3): ["Hackeo", "Computadoras"],
    (3, 0): ["Entrenamiento militar", "Armas de fuego"], (3, 1): ["Entrenamiento militar", "Armas de fuego", "Combate cuerpo a cuerpo"], (3, 2): ["Entrenamiento militar", "Armas de fuego"],
    (4, 0): ["Gravedad cero", "Reparación", "Armas de fuego"], (5, 0): ["Computadoras", "Lingüística"], (6, 0): ["Combate cuerpo a cuerpo", "Atletismo", "Cibernética"],
    (7, 0): ["Psicología", "Lingüística"], (8, 0): ["Combate cuerpo a cuerpo", "Atletismo"], (9, 0): ["Entrenamiento militar", "Armas de fuego", "Combate cuerpo a cuerpo"],
    (10, 0): ["Zoología", "Supervivencia"],
}
HAB_PERSONAL = {"stephen-bognar": ["Lingüística", "Computadoras"], "christof-bognar": ["Lingüística", "Computadoras"], "kyou-aoki": ["Entrenamiento militar", "Combate cuerpo a cuerpo"],
                "rani-kartall": ["Equipo industrial", "Reparación", "Mecánica"], "asad-sivert": ["Medicina de campo", "Química", "Entrenamiento militar"]}


def actores_cazadores(cs, carp):
    """Un actor por CADA cazador (los equipos con varios miembros no son un solo PNJ), con su equipo y habilidades como objetos."""
    out = []
    for c in cs:
        n = c["num"]
        miembros = c["miembros"] or [{"stat": "", "stat_html": "", "equipo": [], "nombre": c["titulo"]}]
        uno = len(miembros) == 1
        for mi, m in enumerate(miembros):
            nombre = c["titulo"] if uno else texto.titulo_caso(m["nombre"])
            aid = fid(f"actor:cazador:{n:02d}:{mi}") if not uno else fid(f"actor:cazador:{n:02d}")
            st = texto.parsear_stats(m["stat"])
            gear, habs = [], []
            for e in m["equipo"]:
                if e.strip().lower() in ("ninguna", "ninguno"):
                    continue
                h = _habilidad(aid, e)
                (habs if h else gear).append(h or e)
            bio = (f"<p>{c['pago']}</p><p><em>Aceptan órdenes de BL: {', '.join(map(str, c['bls']))}.</em></p><p>{m['stat_html']}</p>"
                   + (f"<p><strong>Equipo:</strong> {esc('; '.join(eq.parsear(x)['nombre'] for x in gear))}</p>" if gear else "")
                   + (f"<p>Equipo con varios miembros: <em>{esc(c['titulo'])}</em>.</p>" if not uno else "")
                   + f"<p>@UUID[Compendium.{MOD}.manual.JournalEntry.{fid('manual:03-cazarrecompensas-rivales')}.JournalEntryPage.{fid(f'cazador:pag:{n}')}]{{Ficha completa del libro}}</p>")
            a = crear_actor(aid, f"{n:02d} · {nombre}" + ("" if uno else f" ({c['titulo']})"), ruta(f"cazadores/cazador-{n:02d}.webp"),
                            ruta(f"tokens/cazador-{n:02d}.webp"), ruta(f"figuras/cazador-{n:02d}.webp"), st, bio,
                            {"categoria": "cazarrecompensas", "num": n, "bls": c["bls"], "equipo": uno or mi == 0}, arma=(st.get("arma"), st.get("danio")), carp=carp, equipo=gear,
                            habilidades=HAB_CAZADORES.get((n, mi), ["Atletismo"]))
            a["items"] += habs
            out.append(a)
    return out


def diario_cazadores(cs, carp):
    pages = []
    for i, c in enumerate(cs):
        n = c["num"]
        cuerpo = (f'<div class="mr-wos-cartel"><div class="mr-wos-cartel-foto"><img src="{ruta(f"cazadores/cazador-{n:02d}.webp")}" alt="{esc(c["titulo"])}" /></div>'
                  f'<div class="mr-wos-cartel-datos"><h3>{esc(c["titulo"])}</h3><p>{c["pago"]}</p><p>Órdenes de BL: {", ".join(map(str, c["bls"]))}</p></div></div>\n{c["html"]}')
        pages.append({"_id": fid(f"cazador:pag:{n}"), "name": f"{n:02d} · {c['titulo']}", "type": "text", "sort": 100000 + i * 10000,
                      "title": {"show": True, "level": 1}, "text": {"format": 1, "content": cuerpo}, "flags": {}, "_stats": stats_doc(None)})
    return {"_id": fid("manual:03-cazarrecompensas-rivales"), "name": "Los 10 cazarrecompensas rivales", "pages": pages, "folder": carp["_id"],
            "sort": 130000, "ownership": {"default": 0}, "flags": {MOD: {"clave": "03-cazarrecompensas-rivales"}}, "_stats": stats_doc()}


def actores_odc(carp_staff, carp_presos, carp_fauna):
    out = []
    for p in texto.personal():
        k = slug(p["nombre"])
        st = p["stats"]
        bio = f"<p>{p['html']}</p><p><em>Retrato generado para el módulo: el libro no ilustra al personal de dirección.</em></p>"
        out.append(crear_actor(fid(f"actor:odc:{k}"), p["nombre"], ruta(f"odc/{k}.webp"), ruta(f"tokens/{k}.webp"), None, st, bio,
                               {"categoria": "odc-personal", "soborno": st.get("bribe")}, carp=carp_staff, habilidades=HAB_PERSONAL.get(k, ["Atletismo"])))
    for p in texto.presos():
        n = p["num"]
        if existe(f"tokens/preso-{n}.webp"):
            img, tok = ruta(f"odc/preso-{n}.webp"), ruta(f"tokens/preso-{n}.webp")
        elif existe(f"tokens/{slug(p['nombre'])}.webp"):
            img, tok = ruta(f"odc/{slug(p['nombre'])}.webp"), ruta(f"tokens/{slug(p['nombre'])}.webp")
        else:
            continue
        st = p["stats"]
        out.append(crear_actor(fid(f"actor:preso:{n}"), f"#{n} {p['nombre']}", img, tok, None, st,
                               "".join(f"<p>{h}</p>" for h in p["html"]), {"categoria": "odc-preso", "preso": n}, arma=(st.get("arma"), st.get("danio")), carp=carp_presos,
                               habilidades=habilidades_de(p["txt"], trabajos=True)))
    claves = {1: "fauna-larva", 2: "fauna-chupaarboles", 3: "fauna-pseudohiena", 4: "fauna-basilisco", 5: "fauna-hiperalgas",
              6: "fauna-simios", 7: "fauna-lagarto-jirafa", 8: "fauna-dragon", 9: "fauna-sirena", 10: "fauna-vandalos"}
    for fa in texto.fauna():
        c = claves[fa["num"]]
        st = fa["stats"]
        nombre = fa["nombre"] + (f" ({fa['alias']})" if fa["alias"] else "")
        bio = f"<p><strong>{esc(fa['stat'])}</strong></p>" + "".join(f"<p>{h}</p>" for h in fa["parrafos"])
        out.append(crear_actor(fid(f"actor:fauna:{c}"), nombre, ruta(f"odc/{c}.webp"), ruta(f"tokens/{c}.webp"), ruta(f"figuras/{c}.webp"), st, bio,
                               {"categoria": "odc-fauna", "clave": c}, arma=(st.get("arma"), st.get("danio")), carp=carp_fauna))
    return out


# ───────────────────────── naves ─────────────────────────
def construir_naves(carp):
    docs = []
    for clave, pl in (("mpt-bus", 326), ("hunter-seeker", 328), ("veil-of-night", 330)):
        nv = texto.nave(pl)
        plano = ruta(f"planos/{clave}.webp")
        anc = re.search(r"(\d+)\s*/\s*(\d+)", nv["anclajes"])
        mej = re.search(r"(\d+)\s*/\s*(\d+)", nv["mejoras_cab"])
        md = re.search(r"Megada[ñn]o:\s*(.+)", nv["megadanio"])
        desc = nv["descripcion_html"]
        lineas = " ".join(l for _, l in nv["lineas_izq"] if not re.fullmatch(r"\d+\s*m", l))
        nombre = texto.titulo_caso(nv["nombre"]).replace("Mpt", "MPT").replace(" Of ", " of ")
        nid = fid(f"nave:{clave}")
        piezas = []
        for _, linea in nv["lineas_izq"]:
            frs = []
            for x in [x.strip() for x in re.split(r"\.\s+|\.$", linea) if x.strip()]:
                if frs and x[0].islower() and not re.match(r"^x\d", x):        # «Escáner de esp.» + «profundo»: abreviatura del libro, no frase nueva
                    frs[-1] += ". " + x
                else:
                    frs.append(x)
            for fr in frs:
                if re.match(r"^sin armas", fr, re.I) or re.fullmatch(r"\d+\s*m", fr):
                    continue
                m = re.match(r"^x\s*(\d+)\s+(.*)$", fr)
                piezas.append((m.group(2) if m else fr, int(m.group(1)) if m else 1))
        items_nave = []
        for nom_p, qty in piezas:
            nom_p = nom_p[:1].upper() + nom_p[1:]
            arma = bool(re.search(r"cañón|lanzamisiles|raíles", nom_p, re.I))
            base = {"_id": fid(f"{nid}:{eq.clave(nom_p)}"), "name": nom_p, "effects": [], "flags": {}, "folder": None, "_stats": stats_doc(),
                    "img": ruta("iconos/nave.webp")}
            if arma:
                base.update(type="weapon", system={"description": f"<p>x{qty}. Megadaño de la nave: {esc(nv['megadanio'])}.</p>", "damage": "", "shots": qty, "curShots": qty, "useAmmo": False, "ranges": {"value": ""}})
            else:
                base.update(type="module", system={"description": f"<p>{esc(nom_p)}{(' (x' + str(qty) + ')') if qty > 1 else ''}. Pág. {pl}.</p>", "quantity": qty, "hull": 1, "totalHull": 1, "feature": "", "offline": False})
            items_nave.append(base)
        docs.append({
            "_id": fid(f"nave:{clave}"), "name": nombre, "type": "ship", "img": ruta("iconos/nave.webp"),
            "system": {"biography": f"<p><strong>{esc(nv['modelo'])}</strong> · Coste: {esc(nv['coste'])}</p>{desc}<p>{esc(lineas)}</p>", "description": desc,
                       "type": "", "class": "", "images": {"layout": plano, "beauty": plano}, "runSetup": False,
                       "stats": {"thrusters": {"value": nv["pro"], "min": 0, "max": 99, "label": "Propulsores"},
                                 "battle": {"value": nv["bat"], "min": 0, "max": 99, "label": "Batalla"},
                                 "systems": {"value": nv["sis"], "min": 0, "max": 99, "label": "Sistemas"}},
                       "supplies": {"hull": {"value": nv["casco"], "max": nv["casco"]}, "fuel": {"value": nv["fuel"], "max": nv["fuel"]},
                                    "crew": {"value": nv["trip"], "max": nv["trip"]}, "cryopods": {"value": nv["cryo"]},
                                    "escape-pods": {"value": nv["escape"]},
                                    "upgrades": {"value": int(mej.group(1)) if mej else 0, "max": int(mej.group(2)) if mej else 0}},
                       "weapon-stats": {"hardpoints": {"value": int(anc.group(1)) if anc else 0, "max": int(anc.group(2)) if anc else 0}}},
            "prototypeToken": {"name": nombre, "displayName": 20, "actorLink": True, "texture": {"src": ruta("iconos/nave.webp")}},
            "items": items_nave, "effects": [], "folder": carp["_id"], "ownership": {"default": 0},
            "flags": {MOD: {"nave": clave, "plano": plano, "ficha": nv["modelo"]},
                      "mr-kit-desguazador": {"aplicado": True, "nave": clave, "modelo": nv["modelo"], "cascoBase": nv["casco"],
                                             "mdmgTotal": md.group(1).strip() if md else ""}},
            "_stats": stats_doc()})
    return docs


# ───────────────────────── armas de prisión ─────────────────────────
ICONO_ARMA = [("pilas", "pilas-calcetin"), ("motosierra", "motosierra"), ("daga", "daga"), ("anillos", "anillos"), ("garrote", "garrote"),
              ("hachuela", "hachuela"), ("hacha", "hacha-de-tala"), ("látigo", "latigo"), ("piedra", "piedra-cuerda"),
              ("pincho de madera", "pincho-madera"), ("pincho de hoja", "pincho-sierra"), ("pincho de lata", "pincho-lata"), ("mazo", "mazo")]


def construir_equipo(carp):
    """Las 13 armas de prisión (pág. 277). Quedan en PRISION_DOCS para que los equipos de presos las enlacen."""
    items = []
    for a in texto.armas_prision():
        nombre = a["nombre"]
        ic = next((v for k, v in ICONO_ARMA if nombre.lower().startswith(k)), "pincho-sierra")
        desc = "".join(f"<p>{h}</p>" for h in a["linea"])
        d = {"_id": fid(f"item:arma:{ic}"), "name": nombre, "type": "weapon", "img": ruta(f"armas/{ic}.webp"),
             "system": {"description": desc, "damage": a["danio"] or "1d5", "cost": a["coste"], "weight": 0, "shots": 1, "curShots": 1,
                        "useAmmo": False, "ranges": {"value": "Adyacente"}},
             "effects": [], "folder": carp["_id"], "ownership": {"default": 0}, "flags": {MOD: {"clave": ic, "robar": a["robar"]}}, "_stats": stats_doc()}
        PRISION_DOCS[ic] = d
        items.append(d)
    return items


def items_catalogo(carp):
    """Todo el equipo que usan las fichas y los equipos iniciales (se llama cuando el catálogo ya está completo)."""
    out = []
    for d in CAT.items.values():
        d = copy.deepcopy(d)
        d["folder"] = carp["_id"]
        d["ownership"] = {"default": 0}
        out.append(d)
    return sorted(out, key=lambda x: (x["type"], x["name"]))


def clase_item(clave, nombre, tabla_id, desc, ajuste, concedidas, elegir):
    """Clase de campaña en el formato de MoSh (como las de MR- Mothership en español): ajustes, habilidades concedidas y a elegir."""
    base = {"strength": 0, "speed": 0, "intellect": 0, "combat": 0, "sanity": 0, "fear": 0, "body": 0, "max_wounds": 0}
    base.update(ajuste)
    base["skills_granted"] = [uuid_habilidad(n) for n in concedidas]
    return {"_id": fid(f"clase:{clave}"), "name": nombre, "type": "class", "img": ruta("iconos/equipo.webp"),
            "system": {"description": desc, "source": "Wages of Sin", "author": "MR- Wages of Sin", "link": "", "trauma_response": "", "robotic": False, "common_skills": [],
                       "base_adjustment": base,
                       "selected_adjustment": {"choose_stat": [], "choose_skill_and": {"trained": 0, "expert": 0, "expert_full_set": 0, "master": 0, "master_full_set": 0},
                                               "choose_skill_or": [[dict(o, name=n, from_list=[]) for n, o in elegir]]},
                       "roll_tables": {"loadout": f"Compendium.{MOD}.tablas.RollTable.{tabla_id}", "trinket": "", "patch": ""}},
            "effects": [], "folder": None, "ownership": {"default": 0}, "flags": {MOD: {"clase": clave}}, "_stats": stats_doc()}


# ───────────────────────── tablas ─────────────────────────
def _cara(rng):
    """Rango del libro («0», «9-0», «00») → caras de dado: el 0 es el 10."""
    a, b = [int(x) for x in rng]
    return (a or 10), (b or 10)


def tabla(clave, nombre, formula, filas, carp, desc="", icono="terminal"):
    res = []
    for i, (lo, hi, txt) in enumerate(filas):
        res.append({"_id": fid(f"tabla:{clave}:{i}"), "type": "text", "text": txt, "weight": hi - lo + 1, "range": [lo, hi], "drawn": False, "flags": {}})
    return {"_id": fid(f"tabla:{clave}"), "name": nombre, "img": ruta(f"iconos/{icono}.webp"), "description": desc, "results": res, "formula": formula,
            "replacement": True, "displayRoll": True, "folder": carp["_id"], "sort": 100000, "ownership": {"default": 0}, "flags": {MOD: {"clave": clave}}}


def construir_tablas(ordenes, carp_gen, carp_eq):
    tablas = [tabla("ordenes-100", "Las 100 órdenes de busca (1d100)", "1d100",
                    [(o["num"], o["num"], f"Orden {o['num']:02d} · {o['titulo']} (BL:{o['bl']}) — {o['seBusca']}" + (f" — {o['pago']}" if o["pago"] else "")) for o in ordenes], carp_gen, icono="orden")]
    for p, i, clave, nombre in ((19, 0, "incidentes-entrega", "Incidentes en la entrega (1d10)"), (20, 0, "tipo-cliente", "Generador: tipo de cliente (1d10)")):
        ts, _ = texto.detectar_tablas(texto.marcos(p))
        filas = []
        for f in ts[i]["filas"]:
            lo, hi = _cara(f["rango"])
            filas.append((lo, hi, " · ".join(texto.plano(c) for c in f["celdas"])))
        filas.sort()
        cob = sum(h - l + 1 for l, h, _ in filas)
        if cob == 10:
            tablas.append(tabla(clave, nombre, "1d10", filas, carp_gen, f"<p>Tabla del libro (pág. {p}).</p>", "delito" if p == 19 else "terminal"))
        else:
            print(f"  [AVISO] {nombre}: cobertura {cob}/10, se omite")
    for e in texto.equipos_iniciales():
        clave = "equipo-" + slug(e["clase"])
        res = []
        for i, f in enumerate(e["filas"]):
            cara = 10 if i == 0 else i                      # el «00» del libro es la cara 10
            for j, (k, qty) in enumerate(CAT.fila(f, texto.titulo_caso(e["clase"]))):
                d = doc_de(k)
                for r in range(min(qty, 20) if d["type"] != "skill" else 1):
                    res.append({"_id": fid(f"tabla:{clave}:{i}:{j}:{r}"), "type": "document", "name": d["name"], "img": d["img"], "description": "",
                                "documentUuid": f"Compendium.{MOD}.equipo.Item.{d['_id']}", "weight": 1, "range": [cara, cara], "drawn": False, "flags": {}})
        t = {"_id": fid(f"tabla:{clave}"), "name": f"Equipo inicial: {texto.titulo_caso(e['clase'])} (1d10)", "img": ruta("iconos/equipo.webp"),
             "description": f"<p>Págs. {e['pagina']}. Tira 1d10 (el 10 es el «00» del libro). El creador de personajes de MoSh usa esta tabla para las clases de este nombre.</p>",
             "results": res, "formula": "1d10", "replacement": True, "displayRoll": True, "folder": carp_eq["_id"], "sort": 100000, "ownership": {"default": 0},
             "flags": {MOD: {"clave": clave, "loadout": slug(e["clase"])}}}
        tablas.append(t)
    return tablas


# ───────────────────────── manual (diarios) ─────────────────────────
MANUAL = [
    ("01-crimen-y-ordenes", "Parte 2 · Crimen: órdenes de busca, rastreo y entrega", [("Órdenes de busca y plantilla", 10, 15), ("Dirigir la caza y localizar objetivos", 16, 19), ("Generador de recompensas", 20, 23)]),
    ("02-castigo-y-juicios", "Parte 3 · Castigo: fuerzas del orden, delitos y juicios", [("Fuerzas del orden y delitos de los jugadores", 222, 225), ("Juicio, sentencias y castigo", 226, 228)]),
    ("04-odc-baclite-prision", "La ODC: Baclite · La prisión", [("Baclite y cómo usar el módulo", 250, 253), ("La prisión: sectores A–Q y planos", 254, 261), ("Seguridad y dirigir la prisión", 262, 275), ("Economía penal, armas y ejemplo de juego", 276, 279)]),
    ("05-odc-presos-y-personal", "La ODC: Baclite · Bandas, presos y personal", [("Bandas y registro de presos", 280, 295), ("Conocimiento y botánica de los presos", 296, 297), ("Personal de la ODC y sobornos", 298, 302)]),
    ("06-infierno-verde-y-fuga", "La ODC: Baclite · Fuga por el Infierno Verde", [("Rutas de fuga y supervivencia", 303, 305), ("Fauna de Offit", 306, 310), ("Parque Científico Sullipsuma, Elephant Lodge y Colonia de Fuga", 311, 313)]),
    ("07-naves-y-equipos", "Equipos iniciales, naves y mapa de salto", [("Equipos iniciales", 318, 319), ("Las tres naves: MPT «Bus», Hunter-Seeker y Veil of Night", 326, 331)]),
]


def guia_inicio(n_ordenes):
    return f"""
<h2>MR- Wages of Sin</h2>
<p>Contenido completo en español de <strong>Wages of Sin</strong> (MRPG-M6) para Mothership 1e, con el texto de la tradumaquetación y el arte del propio libro.</p>
<h3>Qué hay en el mundo</h3>
<ul>
  <li><strong>Escenas</strong> (carpeta <em>Wages of Sin</em>): portada, mapa de salto, estaciones, la prisión de la ODC, el Infierno Verde y las cubiertas de las tres naves.</li>
  <li><strong>Actores</strong>: los 10 cazarrecompensas rivales, el personal de dirección, los presos con retrato, la fauna de Offit y las tres naves.</li>
  <li><strong>Diarios</strong>: este manual, las {n_ordenes} órdenes de busca (con carteles para la mesa) y los capítulos del libro.</li>
  <li><strong>Tablas, objetos y macros</strong>: incidentes de entrega, equipos iniciales, armas de prisión y la Terminal de recompensas.</li>
</ul>
<h3>Compendios</h3>
<p>Las {n_ordenes} fichas de objetivo están en la carpeta <em>Objetivos de las órdenes de busca</em> (y también en el compendio <em>Objetivos, cazadores y ODC</em>). Abre la <strong>Terminal de recompensas</strong> desde los controles de escena (icono <i class="fa-solid fa-crosshairs"></i>) o con su macro.</p>
<h3>Para el Guardián</h3>
<p>Las órdenes de busca, el manual y las fichas solo las ve el Guardián. El botón «Mostrar cartel a la mesa» publica en el chat el cartel público de cada orden sin revelar nada secreto.</p>
""".strip()


def construir_diarios_manual(carp_manual, n_ordenes):
    diarios = [{"_id": fid("manual:00-empieza-aqui"), "name": "Empieza aquí", "folder": carp_manual["_id"], "sort": 100000,
                "pages": [{"_id": fid("manual:00-empieza-aqui:pag:0"), "name": "Bienvenida", "type": "text", "sort": 100000,
                           "title": {"show": True, "level": 1}, "text": {"format": 1, "content": guia_inicio(n_ordenes)}, "flags": {}, "_stats": stats_doc(None)}],
                "ownership": {"default": 2}, "flags": {MOD: {"clave": "00-empieza-aqui"}}, "_stats": stats_doc()}]
    est = texto.estaciones()
    diarios.append({"_id": fid("manual:03b-estaciones"), "name": "Estaciones y lugares del sector", "folder": carp_manual["_id"], "sort": 125000,
                    "pages": [{"_id": fid(f"manual:estacion:{e['pagina']}"), "name": e["nombre"], "type": "text", "sort": 100000 + i * 10000,
                               "title": {"show": True, "level": 1}, "text": {"format": 1, "content": e["html"]}, "flags": {}, "_stats": stats_doc(None)} for i, e in enumerate(est)],
                    "ownership": {"default": 0}, "flags": {MOD: {"clave": "03b-estaciones"}}, "_stats": stats_doc()})
    for d_idx, (clave, nombre, partes) in enumerate(MANUAL):
        pages = [{"_id": fid(f"manual:{clave}:pag:{i}"), "name": pn, "type": "text", "sort": 100000 + i * 10000, "title": {"show": True, "level": 1},
                  "text": {"format": 1, "content": texto.paginas_html(a, b)}, "flags": {}, "_stats": stats_doc(None)} for i, (pn, a, b) in enumerate(partes)]
        diarios.append({"_id": fid(f"manual:{clave}"), "name": nombre, "pages": pages, "folder": carp_manual["_id"], "sort": 100000 + (d_idx + 2) * 10000,
                        "ownership": {"default": 0}, "flags": {MOD: {"clave": clave}}, "_stats": stats_doc()})
    return diarios


# ───────────────────────── escenas y paquete de MR- Dirección ─────────────────────────
def _lectura(pag, n=1):
    """Párrafo de cuerpo de la página del libro (texto real) para leer en voz alta."""
    ps = [h for t, h in texto.bloques(texto.marcos(pag)) if t == "p" and len(texto.plano(h)) > 80]
    return texto.plano(ps[n - 1]) if len(ps) >= n else ""


ESCENAS = [   # clave, nombre, archivo, carpeta, imagen_de_dirección, lectura
    ("portada", "Portada", "escenas/portada.webp", "sector", True, ""),
    ("mapa-salto", "Mapa de salto del sector", "escenas/mapa-salto.webp", "sector", False, ""),
    ("tablon-ordenes", "Red de órdenes de busca", "escenas/tablon-ordenes.webp", "sector", True, ""),
    ("caza-recompensas", "Muelles y entrega en mano", "escenas/caza-recompensas.webp", "sector", True, ""),
    ("absalom-station", "Absalom Station", "escenas/absalom-station.webp", "estaciones", False, ("pag", 26, 1)),
    ("anvollapolis", "Anvollapolis", "escenas/anvollapolis.webp", "estaciones", False, ("pag", 34, 1)),
    ("balonov", "Balonov: puerto", "escenas/balonov.webp", "estaciones", False, ("pag", 44, 1)),
    ("hypelabs-domia", "Estación Domia de HypeLabs", "escenas/hypelabs-domia.webp", "estaciones", False, ("pag", 103, 1)),
    ("utpala", "Utpala", "escenas/utpala.webp", "estaciones", False, ("pag", 183, 1)),
    ("odc-mesa", "La ODC: plano de la prisión (mesa)", "escenas/odc-mesa.webp", "odc", False, ""),
    ("odc-guardian", "La ODC: plano del Guardián", "escenas/odc-guardian.webp", "odc", False, ""),
    ("odc-celda", "La ODC: plano de la celda", "escenas/odc-celda.webp", "odc", False, "Imprime este plano y dáselo a tus jugadores: que marquen sus escondites."),
    ("infierno-verde-mesa", "El Infierno Verde de Offit", "escenas/infierno-verde-mesa.webp", "odc", False, ""),
    ("plano-mpt-bus", "Cubierta: MPT «Bus»", "planos/mpt-bus.webp", "naves", False, ""),
    ("plano-hunter-seeker", "Cubierta: Hunter-Seeker", "planos/hunter-seeker.webp", "naves", False, ""),
    ("plano-veil-of-night", "Cubierta: Veil of Night", "planos/veil-of-night.webp", "naves", False, ""),
]


def miniatura(rel, clave):
    im = Image.open(ASSETS / rel).convert("RGB")
    im.thumbnail((400, 300))
    (ASSETS / "escenas" / "thumbs").mkdir(parents=True, exist_ok=True)
    im.save(ASSETS / "escenas" / "thumbs" / f"{clave}.webp", "WEBP", quality=72, method=6)
    return ruta(f"escenas/thumbs/{clave}.webp")


def construir_escenas(carpetas):
    escenas, dir_escenas = [], {}
    for idx, (clave, nombre, rel, carp, es_img, lect) in enumerate(ESCENAS):
        w, h = Image.open(ASSETS / rel).size
        src = ruta(rel)
        lectura = _lectura(lect[1], lect[2]) if isinstance(lect, tuple) else lect
        escenas.append({"_id": fid(f"escena:{clave}"), "name": f"{idx:02d} · {nombre}", "active": clave == "portada", "navigation": True, "navOrder": idx * 10,
                        "folder": carpetas[carp]["_id"], "background": {"src": src}, "width": w, "height": h, "padding": 0,
                        "grid": {"type": 0, "size": 100, "alpha": 0}, "tokenVision": False, "fog": {"exploration": False}, "thumb": miniatura(rel, clave),
                        "flags": {MOD: {"clave": clave, "imagen": es_img}}, "_stats": stats_doc()})
        dir_escenas[clave] = {"id": fid(f"escena:{clave}"), "name": nombre, "img": src, "readAloud": lectura}
    return escenas, dir_escenas


def macros_docs(carp):
    defs = [("terminal", "Terminal de recompensas", "terminal", "game.mrWages.abrirTerminal();"),
            ("generar-orden", "Orden de busca al azar (1d100)", "orden", "game.mrWages.macros.generarOrden();"),
            ("oraculo-bl", "Oráculo de Nivel de Recompensa", "rastreo", "game.mrWages.macros.oraculoBL();"),
            ("soborno-odc", "Intentar un soborno en la ODC", "soborno", "game.mrWages.macros.sobornoODC();"),
            ("equipo-inicial", "Equipo inicial del libro para la ficha seleccionada", "equipo", "game.mrWages.macros.equipoInicial();")]
    return [{"_id": fid(f"macro:{c}"), "name": n, "type": "script", "img": ruta(f"iconos/{ic}.webp"), "scope": "global", "command": cmd, "author": "0000000000000000", "folder": carp["_id"],
             "sort": 100000 + i * 1000, "ownership": {"default": 0}, "flags": {MOD: {"clave": c}}, "_stats": stats_doc()} for i, (c, n, ic, cmd) in enumerate(defs)]


def main():
    ordenes = datos_ordenes()
    carp = {tipo: carpeta(tipo, "raiz", "Wages of Sin") for tipo in ("Scene", "Actor", "JournalEntry", "Item", "RollTable", "Macro")}
    cs = {k: carpeta("Scene", k, n, carp["Scene"]) for k, n in (("sector", "Sector y encargos"), ("estaciones", "Estaciones"), ("odc", "La ODC: Baclite"), ("naves", "Naves"))}
    c_obj = carpeta("Actor", "objetivos", "Objetivos de las órdenes de busca", carp["Actor"])
    c_caz = carpeta("Actor", "cazadores", "Cazarrecompensas rivales", carp["Actor"])
    c_staff = carpeta("Actor", "personal", "La ODC · Personal", carp["Actor"])
    c_presos = carpeta("Actor", "presos", "La ODC · Presos", carp["Actor"])
    c_fauna = carpeta("Actor", "fauna", "Fauna de Offit", carp["Actor"])
    c_naves = carpeta("Actor", "naves", "Naves", carp["Actor"])
    c_manual = carpeta("JournalEntry", "manual", "Manual y guías", carp["JournalEntry"])
    c_ord = carpeta("JournalEntry", "ordenes", "Órdenes de busca", carp["JournalEntry"])
    c_caz_j = carpeta("JournalEntry", "cazadores", "Cazarrecompensas rivales", carp["JournalEntry"])
    c_armas = carpeta("Item", "armas", "Armas de prisión", carp["Item"])
    c_tab = carpeta("RollTable", "generador", "Órdenes y entregas", carp["RollTable"])
    c_eq = carpeta("RollTable", "equipo", "Equipos iniciales", carp["RollTable"])

    equipo = construir_equipo(c_armas)
    d_ord = construir_diarios_ordenes(ordenes, c_ord)
    d_man = construir_diarios_manual(c_manual, len(ordenes))
    caz = datos_cazadores()
    d_caz = diario_cazadores(caz, c_caz_j)
    objetivos = actores_objetivo(ordenes)
    a_caz = actores_cazadores(caz, c_caz)
    a_odc = actores_odc(c_staff, c_presos, c_fauna)
    naves = construir_naves(c_naves)
    tablas = construir_tablas(ordenes, c_tab, c_eq)
    escenas, dir_escenas = construir_escenas(cs)
    macros = macros_docs(carp["Macro"])
    c_clases = carpeta("Item", "clases", "Clases (equipo de Wages of Sin)", carp["Item"])
    tid = lambda c: fid(f"tabla:equipo-{c}")
    elegir = [("1 habilidad experta", {"trained": 0, "expert": 1, "expert_full_set": 0, "master": 0, "master_full_set": 0}),
              ("2 habilidades entrenadas", {"trained": 2, "expert": 0, "expert_full_set": 0, "master": 0, "master_full_set": 0})]
    clases = [clase_item("preso", "Preso (Wages of Sin)", tid("presos"),
                         "<p><em>Clase de campaña para presos de la ODC.</em></p><p>El libro (pág. 319) da el equipo inicial; los ajustes y las habilidades de esta clase los propone el módulo, con el mismo formato que las clases de Mothership 1e: conocimiento de la calle y aguante físico.</p>",
                         {"combat": 5, "body": 10, "fear": 5}, ["Atletismo", "Conocimientos del Borde Exterior"], elegir),
              clase_item("cazarrecompensas", "Cazarrecompensas (Wages of Sin)", tid("cazarrecompensas"),
                         "<p><em>Clase de campaña para cazarrecompensas.</em></p><p>El libro (pág. 319) da el equipo inicial; los ajustes y las habilidades de esta clase los propone el módulo, con el mismo formato que las clases de Mothership 1e: formación militar y rastreo con terminales.</p>",
                         {"combat": 5, "intellect": 5, "speed": 5}, ["Entrenamiento militar", "Computadoras"], elegir)]
    for cl in clases:
        cl["folder"] = c_clases["_id"]
    equipo = equipo + items_catalogo(c_armas) + clases

    aventura = [{"_id": fid("adventure:wages-of-sin"), "name": "Wages of Sin · Cazarrecompensas y La ODC: Baclite", "img": ruta("escenas/thumbs/portada.webp"),
                 "caption": "El libro completo en español: escenas, actores, diarios, tablas y macros, cada cosa en su carpeta.",
                 "description": "<p>Importa las escenas y los mapas, las fichas de los 100 objetivos, los diez cazarrecompensas rivales, el personal, los presos y la fauna de la ODC, las tres naves, el manual y las 100 órdenes de busca.</p>",
                 "scenes": escenas, "actors": [dict(copy.deepcopy(a), folder=c_obj["_id"]) for a in objetivos] + a_caz + a_odc + naves, "items": equipo, "tables": tablas, "journal": d_man + [d_caz] + d_ord, "macros": macros,
                 "folders": CARPETAS, "sort": 100000, "flags": {MOD: {"aventura": "baclite"}}, "_stats": stats_doc()}]

    todos_actores = [copy.deepcopy(a) for a in objetivos + a_caz + a_odc]
    for a in todos_actores:
        a["folder"] = None
    salidas = {"aventura-baclite": aventura, "ordenes": d_ord, "manual": d_man + [d_caz], "objetivos": todos_actores,
               "naves": [dict(n, folder=None) for n in naves], "equipo": [dict(e, folder=None) for e in equipo],
               "tablas": [dict(t, folder=None) for t in tablas], "macros": [dict(m, folder=None) for m in macros]}
    for nombre, docs in salidas.items():
        (DATA_DIR / f"{nombre}.json").write_text(json.dumps(docs, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"  [OK] _data/{nombre}.json -> {len(docs)} documento(s)")

    indice = [{"num": o["num"], "codigo": o["codigo"], "titulo": o["titulo"], "bl": o["bl"], "seBusca": o["seBusca"], "delito": o["delito"], "cliente": o["cliente"],
               "pago": o["pago"], "prima": o["prima"], "entrega": o["entrega"], "paradero": o["paradero"], "etiquetas": o["etiquetas"], "lugar": o["lugar"],
               "pagina": o["pagina"], "anuncio": o["anuncio"], "informe": o["informe"], "statStr": o["statStr"], "img": o["img"], "actorId": o["actorId"],
               "diarioId": fid(f"diario-ordenes:ordenes-{(o['num'] - 1) // 20 * 20 + 1:03d}-{((o['num'] - 1) // 20 + 1) * 20:03d}"),
               "paginaId": fid(f"pagina-orden:{o['num']:03d}")} for o in ordenes]
    (CONTENT_DIR / "equipo-tablas.json").write_text(json.dumps({c: f"Compendium.{MOD}.tablas.RollTable.{tid(c)}" for c in ("marines", "androides", "cientificos", "transportistas", "presos", "cazarrecompensas")}, indent=1), encoding="utf-8")
    (CONTENT_DIR / "ordenes-indice.json").write_text(json.dumps(indice, ensure_ascii=False, indent=1), encoding="utf-8")
    direccion = {"id": MOD, "title": "MR- Wages of Sin", "system": "mosh",
                 "clocks": [{"id": "bl-tripulacion", "name": "Nivel de Recompensa de la tripulación", "max": 9, "value": 0}],
                 "scenes": dir_escenas}
    (CONTENT_DIR / "direccion-es.json").write_text(json.dumps(direccion, ensure_ascii=False, indent=2), encoding="utf-8")
    print("Generación de datos de Wages of Sin completada.")


if __name__ == "__main__":
    main()

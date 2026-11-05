#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Equipo de «Wages of Sin» como objetos de Foundry (tipo mosh): armaduras, armas, objetos y habilidades que salen de
los equipos iniciales (págs. 318-319), de las listas de EQUIPO de los cazarrecompensas y de las armas de prisión.
Cada pieza se crea UNA vez en el catálogo (compendio «equipo») y las fichas y las tablas de equipo inicial la enlazan.
Solo se ponen las cifras que da el libro (PA, RD, cargas, daño); lo que no da queda indicado en la descripción.
"""
import re
import unicodedata

import texto

# armas: palabra clave → (icono, ¿cuerpo a cuerpo?)
ARMAS = [("fusil", "arma-fuego"), ("escopeta", "arma-fuego"), ("revólver", "arma-fuego"), ("pistola", "arma-fuego"), ("subfusil", "arma-fuego"),
         ("lanzallamas", "arma-fuego"), ("rifle", "arma-fuego"), ("ballesta", "arma-fuego"), ("vibmachete", "daga"), ("porra", "mazo"),
         ("hacha", "hachuela"), ("navaja", "daga"), ("dedos de nanohoja", "daga"), ("bisturí", "daga"), ("daga", "daga"), ("puñal", "pincho-sierra"),
         ("látigo", "latigo"), ("anillos", "anillos"), ("jabón en un calcetín", "pilas-calcetin"), ("piedra en una cuerda", "piedra-cuerda")]
# armas de prisión del libro (págs. 277) a las que remiten los equipos de los presos
PRISION = [("jabón en un calcetín", "pilas-calcetin"), ("daga", "daga"), ("puñal de lata de atún", "pincho-lata"), ("puñal de hoja de sierra", "pincho-sierra"),
           ("puñal de cepillo de dientes", "pincho-lata"), ("puñal de madera", "pincho-madera"), ("látigo de cuchillas", "latigo"),
           ("hacha de mano", "hachuela"), ("anillos de pelea", "anillos"), ("piedra en una cuerda", "piedra-cuerda")]
ABREV = {"traje comb. avanzado": "traje de combate avanzado", "traje comb. av.": "traje de combate avanzado", "traje comb. est.": "traje de combate estándar",
         "traje comb.": "traje de combate", "escop. de tambor": "escopeta de tambor", "escop.": "escopeta", "subf.": "subfusil", "estimul.": "estimulante",
         "granada frag.": "granada de fragmentación", "vibromach.": "vibmachete", "porra eléc.": "porra eléctrica", "amet. polivalente": "ametralladora polivalente",
         "fusil intel.": "fusil inteligente", "bist.": "bisturí", "hacha abord.": "hacha de abordaje", "pistola sedante": "pistola sedante"}
CATEGORIAS = [("explosiv", "explosivo"), ("granada", "explosivo"), ("flecha explosiva", "explosivo"), ("botiqu", "medico"), ("medesc", "medico"), ("estimul", "medico"),
              ("automed", "medico"), ("jeringa", "medico"), ("camilla", "medico"), ("veneno", "medico"), ("drogas", "medico"), ("hierba", "varios"),
              ("ganz", "herramienta"), ("soldador", "herramienta"), ("palanca", "herramienta"), ("herramienta", "herramienta"), ("electroim", "herramienta"),
              ("cortador", "herramienta"), ("extrusor", "herramienta"), ("mochila", "herramienta"), ("botas", "herramienta"), ("cordón", "herramienta"),
              ("kit", "herramienta"), ("filtro", "herramienta"), ("rebreather", "herramienta"), ("comunic", "electronica"), ("terminal", "electronica"),
              ("hud", "electronica"), ("gafas", "electronica"), ("prism", "electronica"), ("bioesc", "electronica"), ("baliza", "electronica"),
              ("rastread", "electronica"), ("escáner", "electronica"), ("inhibidor", "electronica"), ("detonador", "electronica"), ("unidad", "electronica"),
              ("dron", "electronica"), ("identificaci", "electronica"), ("mascota", "mascota"), ("pilluelo", "mascota")]


def plain(t):
    return texto.plano(t) if "<" in t else t


def clave(nombre):
    t = unicodedata.normalize("NFD", nombre.lower())
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9]+", "-", t).strip("-")


def dividir(fila):
    """«A (x, y), B (z).» → ['A (x, y)', 'B (z)'] cortando solo las comas de primer nivel."""
    t = plain(fila).replace("†", "").strip().rstrip(".")
    partes, nivel, cur = [], 0, ""
    for ch in t:
        if ch == "(":
            nivel += 1
        elif ch == ")":
            nivel -= 1
        if ch == "," and nivel == 0:
            partes.append(cur.strip())
            cur = ""
        else:
            cur += ch
    if cur.strip():
        partes.append(cur.strip())
    return [p.strip().rstrip(".").strip() for p in partes if p.strip()]


def parsear(comp):
    """Un componente del equipo → dict con nombre, cantidad, PA/RD, cargas, daño y notas del libro."""
    c = comp.strip()
    qty = 1
    m = re.match(r"^(\d+)\s*x\s+(.*)$", c)
    if m:
        qty, c = int(m.group(1)), m.group(2)
    paren = ""
    m = re.match(r"^([^()]*?)\s*\((.*)\)\s*(.*)$", c)
    if m:
        nombre, paren, resto = m.group(1).strip(), m.group(2).strip(), m.group(3).strip()
        nombre = (nombre + " " + resto).strip() if resto and not resto.startswith(("†", ".")) else nombre
    else:
        nombre = c
    nombre = nombre.rstrip("†").strip()
    low = nombre.lower()
    for k, v in ABREV.items():
        if low.startswith(k):
            nombre = v + nombre[len(k):]
            low = nombre.lower()
            break
    mq = re.search(r"\bx\s*(\d+)", paren)
    if mq:
        qty = int(mq.group(1))
    pa = re.search(r"PA\s*(\d+)", paren)
    rd = re.search(r"RD\s*(\d+)", paren)
    cargas = re.search(r"(\d+)\s*(?:cargas|disparos|tiros|cartuchos)", paren)
    danio = re.search(r"(\d+d\d+(?:[+-]\d+)?)\s*DAÑO", paren)
    return {"nombre": nombre[:1].upper() + nombre[1:], "qty": qty, "pa": int(pa.group(1)) if pa else None, "rd": int(rd.group(1)) if rd else 0,
            "cargas": int(cargas.group(1)) if cargas else None, "danio": danio.group(1) if danio else "", "nota": paren}


def categoria(nombre, p):
    low = nombre.lower()
    if p["pa"] is not None or re.match(r"^(traje|uniforme|atuendo|armadura|chaleco|bata)", low):
        return "armadura"
    for k, ic in PRISION:
        if low.startswith(k):
            return "prision:" + ic
    for k, ic in ARMAS:
        if k in low:
            return "arma:" + ic
    for k, cat in CATEGORIAS:
        if k in low:
            return cat
    return "varios"


class Catalogo:
    """Catálogo único de objetos: la misma pieza (mismo nombre y cifras) es un solo objeto en el compendio."""

    def __init__(self, fid, stats_doc, ruta, existe):
        self.fid, self.stats_doc, self.ruta, self.existe = fid, stats_doc, ruta, existe
        self.items = {}

    def _img(self, cat):
        if cat.startswith(("prision:", "arma:")):
            ic = cat.split(":")[1]
            for carpeta, nom in (("armas", ic), ("iconos", f"cat-{ic}")):
                if self.existe(f"{carpeta}/{nom}.webp"):
                    return self.ruta(f"{carpeta}/{nom}.webp")
        for nom in (f"cat-{cat}", "cat-varios", "equipo"):
            if self.existe(f"iconos/{nom}.webp"):
                return self.ruta(f"iconos/{nom}.webp")
        return self.ruta("iconos/equipo.webp")

    def objeto(self, comp, origen=""):
        """Devuelve (clave, qty) y registra el objeto si es nuevo. `comp` es un texto de componente."""
        p = parsear(comp)
        cat = categoria(p["nombre"], p)
        if cat.startswith("prision:"):
            return "prision:" + cat.split(":")[1], p["qty"]
        habil = re.search(r"habilidad de (Maestro|Experto|Entrenado)\s*«([^»]+)»", p["nota"])
        if habil:
            nombre = habil.group(2)
            k = "habilidad-" + clave(nombre)
            rango = {"Maestro": "Master", "Experto": "Expert", "Entrenado": "Trained"}[habil.group(1)]
            bono = {"Master": 20, "Expert": 15, "Trained": 10}[rango]
            if k not in self.items:
                self.items[k] = {"_id": self.fid(f"gear:{k}"), "name": nombre, "type": "skill", "img": self.ruta("iconos/cat-habilidad.webp") if self.existe("iconos/cat-habilidad.webp") else self.ruta("iconos/equipo.webp"),
                                 "system": {"description": f"<p>Habilidad de {habil.group(1).lower()} que da el equipo inicial de Wages of Sin.</p>", "rank": rango, "bonus": bono, "prerequisite_ids": []},
                                 "effects": [], "flags": {}, "_stats": self.stats_doc()}
            return k, 1
        k = clave(p["nombre"] + (f"-pa{p['pa']}" if p["pa"] is not None else "") + (f"-rd{p['rd']}" if p["rd"] else "") + (f"-{p['cargas']}c" if p["cargas"] else ""))
        if k not in self.items:
            desc = f"<p>{p['nombre']}.</p>" + (f"<p>{p['nota']}</p>" if p["nota"] and not re.fullmatch(r"x\s*\d+", p["nota"]) else "") + f"<p><em>Equipo de Wages of Sin{(' · ' + origen) if origen else ''}.</em></p>"
            base = {"_id": self.fid(f"gear:{k}"), "name": p["nombre"], "img": self._img(cat), "effects": [], "flags": {"mr-wages-of-sin": {"gear": k}}, "_stats": self.stats_doc()}
            if cat == "armadura":
                base.update(type="armor", system={"description": desc, "armorPoints": p["pa"] or 0, "damageReduction": p["rd"], "speed": "", "oxygenMax": 0, "oxygenCurrent": 0, "weight": 0, "cost": 0})
            elif cat.startswith("arma:"):
                desc += "" if p["danio"] else "<p><em>El libro no da el daño de esta arma: aquí va 1d10 por defecto; ajústalo según la Guía de Supervivencia.</em></p>"
                base.update(type="weapon", system={"description": desc, "damage": p["danio"] or "1d10", "ammo": p["cargas"] or 0, "shots": p["cargas"] or 1, "curShots": p["cargas"] or 1,
                                                      "useAmmo": False, "ranges": {"value": "", "short": 0, "medium": 0, "long": 0}, "weight": 0, "cost": 0, "bonus": 0, "antiArmor": False})
            else:
                base.update(type="item", system={"description": desc, "quantity": 1, "weight": 0, "cost": 0})
            self.items[k] = base
        return k, p["qty"]

    def fila(self, fila_html, origen=""):
        return [self.objeto(c, origen) for c in dividir(fila_html)]

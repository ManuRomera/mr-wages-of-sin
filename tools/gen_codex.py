#!/usr/bin/env python3
"""Genera retratos e iconos de Wages of Sin delegando en Codex CLI (modelo económico gpt-6.1-sol).
Uso: python3 tools/gen_codex.py [--only id1,id2] [--force] [--jobs 3]
Lee docs/arte/prompts.json y escribe art_src/raw/<id>.png (reanudable)."""
import argparse, json, os, subprocess, sys, time
from concurrent.futures import ThreadPoolExecutor

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, "art_src", "raw")
MODEL = "gpt-6.1-sol"


def valida(path, size):
    """Descarta copias equivocadas: tamaño mínimo y proporción parecida a la pedida."""
    from PIL import Image
    try:
        w, h = Image.open(path).size
    except Exception:  # noqa: BLE001
        return False
    rw, rh = map(int, size.split("x"))
    return min(w, h) >= 700 and abs(w / h - rw / rh) < 0.15


def one(it, estilo):
    out = os.path.join("art_src", "raw", it["id"] + ".png")
    extra = " The background MUST be transparent (alpha channel)." if False else ""
    prompt = ("Usa tu herramienta de generación de imágenes para crear UNA sola imagen, tamaño %s. "
              "Descripción: %s Estilo: %s%s\n"
              "Después copia EL PNG QUE TU HERRAMIENTA ACABA DE DEVOLVER EN ESTA SESIÓN (usa su ruta exacta; nunca busques el archivo más reciente de la carpeta, puede ser de otra sesión) exactamente a %s (crea la carpeta si falta) y responde solo con esa ruta. "
              "No generes más de una imagen ni modifiques otros archivos.") % (it["size"], it["prompt"], estilo[it["tipo"]], extra, out)
    t0 = time.time()
    for intento in range(2):
        r = subprocess.run(["codex", "exec", "-m", MODEL, "-c", 'model_reasoning_effort="low"', "--skip-git-repo-check",
                            "-s", "workspace-write", prompt], cwd=ROOT, capture_output=True, text=True, timeout=900, stdin=subprocess.DEVNULL)
        if os.path.exists(os.path.join(ROOT, out)) and not valida(os.path.join(ROOT, out), it["size"]):
            os.remove(os.path.join(ROOT, out))
        if os.path.exists(os.path.join(ROOT, out)):
            return "OK  %-18s %4.0fs" % (it["id"], time.time() - t0)
    return "ERR %-18s %s" % (it["id"], (r.stdout + r.stderr)[-300:].replace("\n", " "))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only"); ap.add_argument("--force", action="store_true"); ap.add_argument("--jobs", type=int, default=3)
    a = ap.parse_args()
    cfg = json.load(open(os.path.join(ROOT, "docs", "arte", "prompts.json")))
    only = set(a.only.split(",")) if a.only else None
    os.makedirs(RAW, exist_ok=True)
    todo = []
    for it in cfg["imagenes"]:
        p = os.path.join(RAW, it["id"] + ".png")
        if only and it["id"] not in only:
            continue
        if os.path.exists(p) and not a.force:
            continue
        if a.force and os.path.exists(p):
            os.remove(p)
        todo.append(it)
    print("pendientes:", len(todo), flush=True)
    with ThreadPoolExecutor(a.jobs) as ex:
        for res in ex.map(lambda it: one(it, cfg["estilo"]), todo):
            print(res, flush=True)
    print("Hecho")


if __name__ == "__main__":
    main()

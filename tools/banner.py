#!/usr/bin/env python3
"""Genera docs/img/banner.webp (1600x560), docs/img/social.png (1280x640) y vistas previas para el README
siguiendo el estándar visual exacto de MR- (mr-kit-desguazador / mr-ultimo-descenso / mr-mothership-es)."""
import io
import pathlib
import shutil
import fitz
from PIL import Image, ImageDraw, ImageFilter, ImageFont

R = pathlib.Path(__file__).resolve().parent.parent
PDF_PATH = pathlib.Path("/Volumes/Datos_Dock/Rol/01 Sistemas de juego/Colección de sistemas/Mothership/Wages of Sin ESPAÑOL.pdf")
LOGO_MARFIL = pathlib.Path("/Volumes/Datos_Dock/FoundryVTT/Data/modules/mr-nadir/brand/MR_11_Formal_Marfil_Transparente.png")
DOCS_IMG = R / "docs" / "img"
DOCS_IMG.mkdir(parents=True, exist_ok=True)


def fnt(path, size, index=0):
    try:
        return ImageFont.truetype(path, size, index=index)
    except Exception:
        return ImageFont.load_default()


def render_banner(out_path: pathlib.Path, W: int, H: int):
    doc = fitz.open(str(PDF_PATH))
    # Arte panorámico de la página 28 (xref 395) o página 11 (xref 263) + figura del cazarrecompensas de portada (xref 27153)
    arte_bg = Image.open(io.BytesIO(doc.extract_image(263)["image"])).convert("RGB")
    oso_raw = Image.open(io.BytesIO(doc.extract_image(27153)["image"])).convert("L")
    # Convertir el blanco a transparente y la tinta negra a silueta oscura con borde carmesí
    oso_alpha = oso_raw.point(lambda p: 0 if p > 215 else int(255 * (215 - p) / 215))
    oso_rgba = Image.new("RGBA", oso_raw.size, (12, 10, 14, 0))
    oso_rgba.putalpha(oso_alpha)

    bg = arte_bg.resize((W, H), Image.Resampling.LANCZOS).filter(ImageFilter.GaussianBlur(2))
    dark_overlay = Image.new("RGB", (W, H), (14, 10, 12))
    bg = Image.blend(bg, dark_overlay, 0.68)

    # Colocar la silueta roja/negra del cazarrecompensas con casco de oso en el centro-derecha sobre halo carmesí
    halo = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    hd = ImageDraw.Draw(halo)
    cx_halo = int(W * 0.67)
    hd.ellipse((cx_halo - int(H * 0.55), -int(H * 0.1), cx_halo + int(H * 0.55), int(H * 1.1)), fill=(210, 38, 32, 165))
    halo = halo.filter(ImageFilter.GaussianBlur(42))
    bg_rgba = Image.alpha_composite(bg.convert("RGBA"), halo)

    oh = int(H * 1.15)
    ow = int(oso_rgba.width * (oh / oso_rgba.height))
    oso_r = oso_rgba.resize((ow, oh), Image.Resampling.LANCZOS)
    bg_rgba.paste(oso_r, (cx_halo - ow // 2, int(H * 0.02)), oso_r)
    bg = bg_rgba.convert("RGB")

    # Degradado izquierdo oscuro estilo MR-
    sombra = Image.new("L", (W, H), 0)
    sd = ImageDraw.Draw(sombra)
    lim = int(W * 0.68)
    for x in range(lim):
        sd.line([(x, 0), (x, H)], fill=int(240 * (1 - x / lim) ** 1.35))

    sombra_r = Image.new("L", (W, H), 0)
    sdr = ImageDraw.Draw(sombra_r)
    for x in range(int(W * 0.75), W):
        rel = max(0.0, (x - W * 0.75) / (W * 0.25))
        sdr.line([(x, 0), (x, H)], fill=int(185 * (rel ** 1.3)))

    bg.paste((10, 9, 12), mask=sombra)
    bg.paste((10, 9, 12), mask=sombra_r)

    d = ImageDraw.Draw(bg)
    x0 = int(W * 0.046)

    f_kicker = fnt("/System/Library/Fonts/Avenir Next Condensed.ttc", int(H * 0.036), 2)
    f_title = fnt("/System/Library/Fonts/Supplemental/DIN Condensed Bold.ttf", int(H * 0.22), 0)
    f_sub = fnt("/System/Library/Fonts/Avenir Next Condensed.ttc", int(H * 0.056), 2)
    f_tag = fnt("/System/Library/Fonts/Avenir Next.ttc", int(H * 0.034), 5)

    d.text(
        (x0, int(H * 0.14)),
        "MRPG-M6 · MOTHERSHIP 1E · KIT PARA CAZARRECOMPENSAS EN ESPAÑOL",
        font=f_kicker,
        fill=(228, 168, 60),
    )
    d.text((x0, int(H * 0.22)), "WAGES OF SIN", font=f_title, fill=(244, 240, 234))

    y_rule = int(H * 0.56)
    d.rectangle([x0, y_rule, x0 + int(W * 0.085), y_rule + max(3, int(H * 0.007))], fill=(217, 56, 46))

    d.text(
        (x0, int(H * 0.61)),
        "LAS 100 ÓRDENES DE BUSCA Y LA LUNA CARCELARIA «LA ODC: BACLITE»",
        font=f_sub,
        fill=(226, 78, 66),
    )
    d.text(
        (x0, int(H * 0.72)),
        "100 objetivos · 10 cazadores · 3 naves · prisión ODC · Infierno Verde · Terminal · Foundry VTT v13 | v14",
        font=f_tag,
        fill=(214, 220, 222),
    )

    if LOGO_MARFIL.exists():
        mono = Image.open(LOGO_MARFIL).convert("RGBA")
        mono.thumbnail((int(W * 0.16), int(H * 0.26)), Image.Resampling.LANCZOS)
        lx = W - mono.width - int(W * 0.035)
        ly = int(H * 0.07)
        bg.paste(mono, (lx, ly), mono)

    if out_path.suffix.lower() == ".webp":
        bg.save(out_path, "WEBP", quality=90)
    else:
        bg.save(out_path, "PNG", optimize=True)
    doc.close()


def main():
    render_banner(DOCS_IMG / "banner.webp", 1600, 560)
    render_banner(DOCS_IMG / "social.png", 1280, 640)

    previews = {
        "escenas/portada.webp": "foundry-portada.webp",
        "escenas/odc-guardian.webp": "foundry-odc.webp",
        "planos/hunter-seeker.webp": "foundry-nave.webp",
        "escenas/mapa-salto.webp": "foundry-salto.webp",
    }
    for src_rel, dst_name in previews.items():
        src = R / "assets" / src_rel
        if src.exists():
            shutil.copy2(src, DOCS_IMG / dst_name)
    print("Banners y vistas previas generados en docs/img/")


if __name__ == "__main__":
    main()

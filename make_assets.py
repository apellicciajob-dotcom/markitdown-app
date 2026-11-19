# -*- coding: utf-8 -*-
"""Genera icona .ico e asset PNG richiesti dallo Store con Pillow (se mancanti).

Uso:  python make_assets.py [--force]
"""
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ASSETS = Path(__file__).resolve().parent / "assets"

PNG = {  # nome -> (larghezza, altezza)
    "Square44x44Logo.png": (44, 44),
    "Square44x44Logo.scale-200.png": (88, 88),
    "Square71x71Logo.png": (71, 71),
    "Square71x71Logo.scale-200.png": (142, 142),
    "Square150x150Logo.png": (150, 150),
    "Square150x150Logo.scale-200.png": (300, 300),
    "Square310x310Logo.png": (310, 310),
    "Square310x310Logo.scale-200.png": (620, 620),
    "Wide310x150Logo.png": (310, 150),
    "Wide310x150Logo.scale-200.png": (620, 300),
    "StoreLogo.png": (50, 50),
    "StoreLogo.scale-200.png": (100, 100),
    "SplashScreen.png": (620, 300),
    "SplashScreen.scale-200.png": (1240, 600),
}
for _t in (16, 24, 32, 48, 256):  # varianti targetsize (barra applicazioni/Start)
    PNG[f"Square44x44Logo.targetsize-{_t}.png"] = (_t, _t)
    PNG[f"Square44x44Logo.targetsize-{_t}_altform-unplated.png"] = (_t, _t)


def _font(size: int):
    for nome in ("segoeuib.ttf", "arialbd.ttf", "seguisb.ttf"):
        try:
            return ImageFont.truetype(nome, size)
        except OSError:
            continue
    return ImageFont.load_default()


def logo(lato: int = 512) -> Image.Image:
    """Quadrato arrotondato con gradiente blu e simbolo 'M↓'."""
    img = Image.new("RGBA", (lato, lato), (0, 0, 0, 0))
    grad = Image.new("RGBA", (lato, lato))
    px = grad.load()
    for y in range(lato):
        for x in range(lato):
            t = (x + y) / (2 * lato)
            px[x, y] = (int(0 + 40 * t), int(103 + 80 * t), int(192 + 40 * t), 255)
    maschera = Image.new("L", (lato, lato), 0)
    ImageDraw.Draw(maschera).rounded_rectangle(
        (0, 0, lato - 1, lato - 1), radius=lato // 5, fill=255)
    img.paste(grad, (0, 0), maschera)
    d = ImageDraw.Draw(img)
    f = _font(int(lato * 0.52))
    testo = "M"
    bb = d.textbbox((0, 0), testo, font=f)
    w, h = bb[2] - bb[0], bb[3] - bb[1]
    d.text(((lato - w) / 2 - bb[0] - lato * 0.06, (lato - h) / 2 - bb[1] - lato * 0.05),
           testo, font=f, fill="white")
    # freccia verso il basso (simbolo Markdown)
    cx, base = lato * 0.74, lato * 0.74
    s = lato * 0.09
    d.rectangle((cx - s / 3, lato * 0.38, cx + s / 3, base - s), fill="white")
    d.polygon([(cx - s, base - s * 1.2), (cx + s, base - s * 1.2), (cx, base + s * 0.4)],
              fill="white")
    return img


def main(force: bool = False) -> None:
    ASSETS.mkdir(exist_ok=True)
    base = logo(512)

    ico = ASSETS / "icon.ico"
    if force or not ico.exists():
        base.save(ico, sizes=[(16, 16), (24, 24), (32, 32), (48, 48),
                              (64, 64), (128, 128), (256, 256)])
        print("creato", ico)

    for nome, (w, h) in PNG.items():
        p = ASSETS / nome
        if p.exists() and not force:
            continue
        if w == h:
            im = base.resize((w, h), Image.LANCZOS)
        else:  # formati larghi: logo centrato su sfondo blu
            im = Image.new("RGBA", (w, h), (0, 103, 192, 255))
            lato = int(h * 0.7)
            im.paste(base.resize((lato, lato), Image.LANCZOS),
                     ((w - lato) // 2, (h - lato) // 2),
                     base.resize((lato, lato), Image.LANCZOS))
        im.save(p)
        print("creato", p)


if __name__ == "__main__":
    main("--force" in sys.argv)

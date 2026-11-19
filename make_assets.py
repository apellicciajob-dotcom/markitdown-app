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


# ---------------------------------------------------------------------------
# Icone colorate dell'interfaccia (assets/icons/<nome>.png 18px e <nome>@2x.png 36px)
# ---------------------------------------------------------------------------
ICONS = ASSETS / "icons"
_K = 8                       # supersampling
_G = 24 * _K                 # tela 24x24 unita'


def _u(*v):
    return [x * _K for x in v]


def _canvas():
    im = Image.new("RGBA", (_G, _G), (0, 0, 0, 0))
    return im, ImageDraw.Draw(im)


def _ic_incolla(d):
    d.rounded_rectangle(_u(4, 4, 20, 22.5), radius=2 * _K, fill="#F2A900", outline="#8A5A00", width=_K // 2)
    d.rounded_rectangle(_u(7, 7.5, 17, 20), radius=1 * _K, fill="#FFFFFF")
    d.rounded_rectangle(_u(8.5, 1.5, 15.5, 6), radius=1.5 * _K, fill="#6B4E00")
    for y in (11, 14, 17):
        d.line(_u(9, y, 15, y), fill="#B0B0B0", width=_K)


def _ic_file(d):
    d.polygon(_u(5, 2.5, 14, 2.5, 19.5, 8, 19.5, 21.5, 5, 21.5), fill="#2D7DD2")
    d.polygon(_u(14, 2.5, 19.5, 8, 14, 8), fill="#9CC8F5")
    for y in (12, 15, 18):
        d.line(_u(8, y, 16.5, y), fill="#FFFFFF", width=_K)


def _ic_cartella(d):
    d.polygon(_u(2, 5, 9, 5, 11, 7.5, 21, 7.5, 21, 19.5, 2, 19.5), fill="#E0A100")
    d.rounded_rectangle(_u(2, 9.5, 22, 20), radius=1.5 * _K, fill="#FFD35C", outline="#B07A00", width=_K // 3)


def _ic_ingresso(d):
    d.polygon(_u(2.5, 14, 7, 14, 8.5, 17, 15.5, 17, 17, 14, 21.5, 14, 21.5, 20.5, 2.5, 20.5), fill="#2D7DD2")
    d.rectangle(_u(10.5, 3, 13.5, 9), fill="#2EA043")
    d.polygon(_u(6.5, 9, 17.5, 9, 12, 15), fill="#2EA043")


def _ic_play(d):
    d.ellipse(_u(1.5, 1.5, 22.5, 22.5), fill="#2EA043")
    d.polygon(_u(9, 6.5, 9, 17.5, 18, 12), fill="#FFFFFF")


def _ic_pausa(d):
    d.ellipse(_u(1.5, 1.5, 22.5, 22.5), fill="#E8890C")
    d.rounded_rectangle(_u(7.5, 6.5, 10.8, 17.5), radius=_K // 2, fill="#FFFFFF")
    d.rounded_rectangle(_u(13.2, 6.5, 16.5, 17.5), radius=_K // 2, fill="#FFFFFF")


def _ic_apri(d):
    d.rounded_rectangle(_u(2.5, 6, 17, 21.5), radius=2.5 * _K, outline="#0A9396", width=2 * _K)
    d.line(_u(11, 13, 20, 4), fill="#0A9396", width=int(2.4 * _K))
    d.polygon(_u(13, 2.5, 21.5, 2.5, 21.5, 11), fill="#0A9396")


def _ic_copia(d):
    d.rounded_rectangle(_u(8, 2.5, 21, 16), radius=2 * _K, fill="#9CC8F5", outline="#2D7DD2", width=_K // 2)
    d.rounded_rectangle(_u(3, 7.5, 16, 21.5), radius=2 * _K, fill="#2D7DD2")
    for y in (12, 15, 18):
        d.line(_u(6, y, 13, y), fill="#FFFFFF", width=_K)


def _ic_elimina(d):
    d.rounded_rectangle(_u(9, 2.5, 15, 5.5), radius=_K, fill="#D13438")
    d.rounded_rectangle(_u(3, 4.5, 21, 7.5), radius=_K, fill="#D13438")
    d.polygon(_u(5, 8.5, 19, 8.5, 17.8, 21, 6.2, 21), fill="#E5484D")
    for x in (9.2, 12, 14.8):
        d.line(_u(x, 11.5, x, 18), fill="#FFFFFF", width=int(1.4 * _K))


def _ic_svuota(d):
    d.ellipse(_u(1.5, 1.5, 22.5, 22.5), fill="#E5533D")
    d.line(_u(8, 8, 16, 16), fill="#FFFFFF", width=int(2.4 * _K))
    d.line(_u(16, 8, 8, 16), fill="#FFFFFF", width=int(2.4 * _K))


def _ic_aggiorna(d):
    d.arc(_u(3.5, 3.5, 20.5, 20.5), start=40, end=330, fill="#2EA043", width=int(2.6 * _K))
    d.polygon(_u(14, 1.5, 22.5, 3.5, 17.5, 10.5), fill="#2EA043")


def _ic_ok(d):
    d.ellipse(_u(1.5, 1.5, 22.5, 22.5), fill="#2EA043")
    d.line(_u(6.5, 12.5, 10.5, 16.5, 17.5, 8), fill="#FFFFFF", width=int(2.6 * _K), joint="curve")


ICONE = {"incolla": _ic_incolla, "file": _ic_file, "cartella": _ic_cartella,
         "ingresso": _ic_ingresso, "play": _ic_play, "pausa": _ic_pausa,
         "apri": _ic_apri, "copia": _ic_copia, "elimina": _ic_elimina,
         "svuota": _ic_svuota, "aggiorna": _ic_aggiorna, "ok": _ic_ok}


def icone(force: bool = False) -> None:
    ICONS.mkdir(parents=True, exist_ok=True)
    for nome, disegna in ICONE.items():
        p18, p36 = ICONS / f"{nome}.png", ICONS / f"{nome}@2x.png"
        if p18.exists() and p36.exists() and not force:
            continue
        im, d = _canvas()
        disegna(d)
        im.resize((36, 36), Image.LANCZOS).save(p36)
        im.resize((18, 18), Image.LANCZOS).save(p18)
        print("creato", p18)


# ---------------------------------------------------------------------------
# Branding ApexCore: banner (dentro l'app, Wide/Splash) e icona (ico + tile quadrate)
# ---------------------------------------------------------------------------
BANNER = ASSETS / "brand_banner.png"
SOURCE_ICON = ASSETS / "source_icon.png"


def _non_bianco(im: Image.Image, soglia: int = 245):
    """Bounding box dei pixel visibili e non bianchi."""
    rgb = im.convert("RGBA")
    px = rgb.load()
    x0 = y0 = 10 ** 9
    x1 = y1 = -1
    for y in range(rgb.height):
        for x in range(rgb.width):
            r, g, b, a = px[x, y]
            if a > 40 and min(r, g, b) < soglia:
                x0, y0, x1, y1 = min(x0, x), min(y0, y), max(x1, x), max(y1, y)
    return (x0, y0, x1 + 1, y1 + 1) if x1 >= 0 else None


def importa_icona(icona_src: Path, riempimento: float = 0.94) -> None:
    """Crea assets/source_icon.png (1024x1024, fondo bianco arrotondato, poco margine)."""
    ASSETS.mkdir(exist_ok=True)
    # icona: toglie il bordo sottile esterno e il vuoto, centra in un quadrato 1:1
    i = Image.open(icona_src).convert("RGBA")
    bianco = Image.new("RGBA", i.size, (255, 255, 255, 255))
    bianco.alpha_composite(i)
    larg = i.getbbox()  # area opaca (riquadro): via il vuoto trasparente a destra
    inner = bianco.crop((larg[0] + 5, larg[1] + 5, larg[2] - 5, larg[3] - 5))  # via bordo
    box = _non_bianco(inner)
    cont = inner.crop(box)
    lato = int(max(cont.size) / riempimento)          
    sq = Image.new("RGBA", (lato, lato), (255, 255, 255, 255))
    sq.alpha_composite(cont, ((lato - cont.width) // 2, (lato - cont.height) // 2))
    mask = Image.new("L", (lato, lato), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, lato - 1, lato - 1), radius=lato // 6, fill=255)
    out = Image.new("RGBA", (lato, lato), (0, 0, 0, 0))
    out.paste(sq, (0, 0), mask)
    out = out.resize((1024, 1024), Image.LANCZOS)
    out.save(SOURCE_ICON)
    print("creato", SOURCE_ICON, out.size)


def importa_brand(banner_src: Path, icona_src: Path) -> None:
    """Crea assets/brand_banner.png e assets/source_icon.png dalle immagini originali."""
    ASSETS.mkdir(exist_ok=True)
    # banner: pillola; il bianco esterno agli angoli diventa trasparente
    b = Image.open(banner_src).convert("RGBA")
    for pt in ((0, 0), (b.width - 1, 0), (0, b.height - 1), (b.width - 1, b.height - 1)):
        ImageDraw.floodfill(b, pt, (255, 255, 255, 0), thresh=12)
    b = b.crop(b.getbbox())
    b.save(BANNER)
    print("creato", BANNER, b.size)

    importa_icona(icona_src)


def _largo(w: int, h: int) -> Image.Image:
    """Tile larga/splash: banner centrato su sfondo bianco, con margine."""
    im = Image.new("RGBA", (w, h), (255, 255, 255, 255))
    ban = Image.open(BANNER).convert("RGBA")
    k = min(w * 0.88 / ban.width, h * 0.78 / ban.height)
    ban = ban.resize((max(1, int(ban.width * k)), max(1, int(ban.height * k))), Image.LANCZOS)
    im.alpha_composite(ban, ((w - ban.width) // 2, (h - ban.height) // 2))
    return im


def main(force: bool = False) -> None:
    ASSETS.mkdir(exist_ok=True)
    icone(force)
    base = (Image.open(SOURCE_ICON).convert("RGBA").resize((512, 512), Image.LANCZOS)
            if SOURCE_ICON.exists() else logo(512))

    # apexcore_icon.ico: nome nuovo per aggirare la cache icone di Explorer; icon.ico = copia
    for nome in ("apexcore_icon.ico", "icon.ico"):
        ico = ASSETS / nome
        if force or not ico.exists():
            base.resize((256, 256), Image.LANCZOS).save(
                ico, sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
            print("creato", ico)

    for nome, (w, h) in PNG.items():
        p = ASSETS / nome
        if p.exists() and not force:
            continue
        if w == h:
            im = base.resize((w, h), Image.LANCZOS)
        elif BANNER.exists():
            im = _largo(w, h)
        else:  # formati larghi: logo centrato su sfondo blu
            im = Image.new("RGBA", (w, h), (0, 103, 192, 255))
            lato = int(h * 0.7)
            im.paste(base.resize((lato, lato), Image.LANCZOS),
                     ((w - lato) // 2, (h - lato) // 2),
                     base.resize((lato, lato), Image.LANCZOS))
        im.save(p)
        print("creato", p)


if __name__ == "__main__":
    if "--import-icon" in sys.argv:        # --import-icon icona.png
        importa_icona(Path(sys.argv[sys.argv.index("--import-icon") + 1]))
        sys.argv.append("--force")
    elif "--import-brand" in sys.argv:       # --import-brand banner.png icona.png
        i = sys.argv.index("--import-brand")
        importa_brand(Path(sys.argv[i + 1]), Path(sys.argv[i + 2]))
        sys.argv.append("--force")
    main("--force" in sys.argv)

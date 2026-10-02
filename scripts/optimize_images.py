"""
Optymalizacja zdjęć ze starej strony -> nowa strona.

Co robi:
  1. Bierze każde zdjęcie z old/images/<kategoria>/ (i podfolderu pion/ = zdjęcia pionowe).
  2. Zapisuje DWIE wersje w formacie WebP:
       - thumb (max 720 px szerokości)  -> do siatki galerii (szybkie ładowanie na telefonie)
       - full  (max 1800 px dłuższego boku) -> do powiększenia w lightboxie
  3. Tworzy plik assets/data/gallery.js z listą zdjęć (ścieżki + wymiary).

DLACZEGO WebP: ten sam obraz waży zwykle 25-35% mniej niż JPG, a wszystkie
współczesne przeglądarki go obsługują. Mniej MB = szybsza strona = lepsze SEO.

DLACZEGO zapisujemy wymiary: przeglądarka zna proporcje obrazka zanim go pobierze,
więc rezerwuje miejsce i strona "nie skacze" podczas ładowania (tzw. CLS w Core Web Vitals).

Uruchomienie (z katalogu projektu):
    python3 scripts/optimize_images.py
"""
import json
import re
from pathlib import Path

from PIL import Image, ImageOps

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "old" / "images"
OUT = ROOT / "assets" / "img" / "gallery"
DATA = ROOT / "assets" / "data" / "gallery.js"

# Kolejność i nazwy kategorii = jak na starej stronie.
# Klucz = nazwa folderu na starym serwerze, wartość = (slug do filtrów, ładna nazwa).
CATEGORIES = {
    "bramy-wjazdowe": ("bramy", "Bramy wjazdowe"),
    "segmenty-ogr": ("ogrodzenia", "Segmenty ogrodzeniowe"),
    "balustrady-zewn": ("balustrady-zewn", "Balustrady zewnętrzne"),
    "balustrady-wewn": ("balustrady-wewn", "Balustrady wewnętrzne"),
    "furtki": ("furtki", "Furtki"),
    "wiaty-carport": ("wiaty", "Wiaty i carporty"),
    "metaloplastyka-archit": ("metaloplastyka", "Metaloplastyka i mała architektura"),
    "bloki": ("bloki", "Zlecenia – bloki"),
    "others": ("rozne", "Różne"),
}

THUMB_W = 600
FULL_MAX = 1800


def natural_key(path: Path):
    """Sortowanie 'naturalne': 2.jpg przed 10.jpg (zwykłe sortowanie dałoby 10 przed 2)."""
    return [int(t) if t.isdigit() else t for t in re.split(r"(\d+)", path.name)]


def save_webp(im: Image.Image, dest: Path, max_w=None, max_side=None, quality=78):
    im = im.copy()
    if max_w and im.width > max_w:
        im = im.resize((max_w, round(im.height * max_w / im.width)), Image.LANCZOS)
    if max_side:
        im.thumbnail((max_side, max_side), Image.LANCZOS)  # thumbnail zachowuje proporcje
    dest.parent.mkdir(parents=True, exist_ok=True)
    # method=6 = najwolniejsza, ale najlepsza kompresja (robimy to raz, więc warto)
    im.save(dest, "WEBP", quality=quality, method=6)
    return im.size


def main():
    items = []
    for folder, (slug, label) in CATEGORIES.items():
        files = sorted((SRC / folder).glob("*.[jJ][pP]*[gG]"), key=natural_key)
        files += sorted((SRC / folder / "pion").glob("*.[jJ][pP]*[gG]"), key=natural_key)
        for i, f in enumerate(files, 1):
            # exif_transpose obraca zdjęcie zgodnie z danymi z aparatu (telefony zapisują obrót w EXIF)
            im = ImageOps.exif_transpose(Image.open(f)).convert("RGB")
            name = f"{slug}-{i:03d}.webp"
            tw, th = save_webp(im, OUT / "thumb" / name, max_w=THUMB_W, quality=60)
            fw, fh = save_webp(im, OUT / "full" / name, max_side=FULL_MAX, quality=68)
            items.append({"c": slug, "f": name, "w": tw, "h": th, "fw": fw, "fh": fh})
        print(f"{label:40s} {len(files):4d} zdjęć")

    cats = [{"slug": s, "label": l} for s, l in CATEGORIES.values()]
    DATA.parent.mkdir(parents=True, exist_ok=True)
    # Zapisujemy jako plik .js (a nie .json), żeby strona działała też po otwarciu
    # z dysku (file://) — fetch() pliku JSON z dysku jest blokowany przez przeglądarki.
    DATA.write_text(
        "// Plik generowany automatycznie przez scripts/optimize_images.py — nie edytuj ręcznie.\n"
        f"window.GALLERY = {json.dumps({'categories': cats, 'items': items}, ensure_ascii=False)};\n",
        encoding="utf-8",
    )
    print(f"\nRazem: {len(items)} zdjęć -> {DATA.relative_to(ROOT)}")


if __name__ == "__main__":
    main()

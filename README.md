# Kowalstwo Artystyczne Marek Mida — nowa strona

Statyczna strona (HTML + CSS + JS, bez frameworków i bez kroku budowania).
Działa na każdym hostingu — wystarczy wgrać pliki przez FTP.

## Struktura

```
index.html                 strona (jedna, z sekcjami)
assets/css/style.css       wygląd (mobile-first, tokeny w :root)
assets/js/main.js          interakcje: menu, slajdy, iskry, galeria, lightbox
assets/data/gallery.js     lista 468 zdjęć — GENEROWANA skryptem
assets/img/gallery/thumb   miniatury WebP (600 px)
assets/img/gallery/full    duże zdjęcia WebP do podglądu
assets/fonts/              fonty hostowane lokalnie (RODO, szybkość)
assets/video/              film promo 16:9 + 9:16 (Reels/TikTok) + plakaty
scripts/optimize_images.py zdjęcia ze starej strony -> WebP + gallery.js
scripts/make_video.py      generator filmu reklamowego (obraz)
scripts/make_soundtrack.py syntezator muzyki do filmu
old/                       kopia starej strony (źródło zdjęć) — NIE wgrywać na serwer
```

## Podgląd lokalnie

```bash
cd ~/PhpstormProjects/kowalstwo-artystyczne
python3 -m http.server 8000      # potem otwórz http://localhost:8000
```

## Dodanie nowych zdjęć

1. Wrzuć JPG do `old/images/<kategoria>/` (np. `bramy-wjazdowe/89.jpg`).
2. `python3 scripts/optimize_images.py` — przerobi wszystko i zaktualizuje galerię.

## Film

```bash
pip install --user imageio-ffmpeg        # jednorazowo: ffmpeg w paczce Pythona
python3 scripts/make_video.py            # oba formaty (ok. 3-4 min)
python3 scripts/make_video.py wide       # tylko 16:9
```
Scenariusz (kolejność zdjęć, napisy, czasy) = lista `SCENES` na górze skryptu.

## Wdrożenie

Wgraj na serwer wszystko **oprócz** `old/` i `scripts/`.

## Do zrobienia przed startem

- Muzyka w filmie jest syntetyczna (scripts/make_soundtrack.py — bez problemów z licencją).
  Po zmianie scen w make_video.py: najpierw make_video.py, potem make_soundtrack.py.
- Zdjęcie `black-smith.jpg` ze starej strony to grafika (nie zdjęcie pracowni) — celowo pominięte.

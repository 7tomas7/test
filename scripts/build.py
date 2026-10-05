"""
Budowanie strony: podstrony kategorii + pliki SEO + paczka do wgrania.

Po co: strona główna to jedna długa strona. Google najlepiej pozycjonuje strony,
które są o JEDNEJ rzeczy — ktoś wpisuje "kute bramy wjazdowe", więc najlepiej,
żeby trafił na stronę, której tytuł, nagłówek, tekst i zdjęcia są o bramach.
Dlatego generujemy osobną podstronę dla każdej kategorii — i to POD STARYMI
ADRESAMI (bramy-wjazdowe.html itd.), które Google zna od lat. Pozycje zostają.

Co powstaje:
  <kategoria>.html (x9)     podstrony z galerią w HTML (Google widzi zdjęcia bez JS)
  polityka-prywatnosci.html wymagana przez RODO informacja
  404.html                  ładna strona "nie znaleziono"
  sitemap.xml               spis stron dla Google (zgłaszamy w Search Console)
  robots.txt                instrukcje dla robotów + adres sitemap
  .htaccess                 przekierowania 301, https+www, kompresja, cache (serwer Apache)
  dist/                     gotowa paczka do wgrania na serwer (FTP)

Uruchomienie:
    python3 scripts/build.py             # wersja produkcyjna (na kowalstwoartystyczne.com)
    python3 scripts/build.py --preview   # podgląd (GitHub Pages): dokłada noindex
"""
import html
import json
import re
import shutil
import sys
from datetime import date
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
SITE = "https://www.kowalstwoartystyczne.com/"  # adres docelowy (z www — jeden, kanoniczny)
PHONE, PHONE_HUMAN = "+48695695813", "695 695 813"
EMAIL = "biuro@kowalstwoartystyczne.com"
INITIAL = 24  # ile zdjęć widać od razu na podstronie (reszta po kliknięciu "Pokaż wszystkie")
esc = html.escape

# ---------------------------------------------------------------------------
# Treść podstron. Teksty piszemy raz tutaj — każda podstrona ma UNIKALNY opis
# (Google karze za kopiowanie tego samego tekstu na wielu stronach).
# ---------------------------------------------------------------------------
CATEGORIES = [
    dict(slug="bramy", file="bramy-wjazdowe.html", cover="hero-brama.webp",
         h1="Bramy wjazdowe kute", title="Kute bramy wjazdowe na wymiar",
         desc="Ręcznie kute bramy wjazdowe przesuwne i dwuskrzydłowe na wymiar. Projekt, cynkowanie ogniowe, malowanie proszkowe, transport i montaż. Małopolska.",
         intro=["Brama wjazdowa to pierwsze, co widzą goście — wizytówka całej posesji. Projektujemy i wykuwamy bramy przesuwne oraz dwuskrzydłowe: od prostych, nowoczesnych form po bogato zdobione bramy z kutymi liśćmi, różami i ornamentami.",
                "Każdą bramę wykonujemy na wymiar, dopasowaną do ogrodzenia, furtki i architektury domu. Stal zabezpieczamy cynkowaniem ogniowym i malowaniem proszkowym, a gotową bramę przywozimy i montujemy."]),
    dict(slug="ogrodzenia", file="segmenty-ogrodzeniowe.html", cover="ogrodzenie.webp",
         h1="Segmenty ogrodzeniowe kute", title="Kute ogrodzenia i segmenty ogrodzeniowe",
         desc="Kute segmenty ogrodzeniowe i ogrodzenia metalowe na wymiar — klasyczne i nowoczesne wzory. Cynkowanie ogniowe, malowanie proszkowe, montaż.",
         intro=["Ogrodzenie z kutych segmentów łączy bezpieczeństwo z ozdobnym charakterem. Wykonujemy segmenty proste i łukowe, z grotami, kulami, pierścieniami i ornamentami — tak, by tworzyły spójną całość z bramą i furtką.",
                "Wzór dobieramy razem z klientem, a całość wykonujemy na wymiar działki. Dzięki cynkowaniu ogniowemu i malowaniu proszkowemu ogrodzenie latami zachowuje wygląd bez rdzy."]),
    dict(slug="balustrady-zewn", file="balustrady-zewnetrzne.html", cover="hero-balkon.webp",
         h1="Balustrady zewnętrzne kute", title="Kute balustrady balkonowe i tarasowe",
         desc="Kute balustrady zewnętrzne: balkonowe, tarasowe i schodowe, proste i gięte (brzuchate). Wykonanie na wymiar, cynkowanie, malowanie proszkowe, montaż.",
         intro=["Balustrada balkonowa czy tarasowa nadaje elewacji charakter. Wykonujemy balustrady proste, łukowe i „brzuchate”, z ozdobnymi wstawkami, zawijasami i motywami roślinnymi — dopasowane do kształtu balkonu.",
                "Balustrady zewnętrzne pracują w deszczu, mrozie i słońcu, dlatego każdą zabezpieczamy cynkowaniem ogniowym i malowaniem proszkowym. Pomiar, wykonanie i montaż — wszystko po naszej stronie."]),
    dict(slug="balustrady-wewn", file="balustrady-wewnetrzne.html", cover="schody.webp",
         h1="Balustrady wewnętrzne kute", title="Kute balustrady schodowe do wnętrz",
         desc="Kute balustrady wewnętrzne na schody i antresole — klasyczne i nowoczesne, z poręczą drewnianą lub metalową. Projekt i montaż.",
         intro=["Balustrada schodowa to jeden z najbardziej widocznych elementów wnętrza. Wykuwamy balustrady do schodów i na antresole — od surowych, industrialnych form po delikatne, zdobione wzory.",
                "Balustradę projektujemy pod konkretne schody i styl wnętrza, łącząc stal z drewnem lub szkłem. Wykonujemy pomiar, a gotową balustradę montujemy na miejscu."]),
    dict(slug="furtki", file="furtki.html", cover="furtka.webp",
         h1="Furtki kute", title="Kute furtki ogrodowe na wymiar",
         desc="Ręcznie kute furtki ogrodowe i wejściowe na wymiar — do kompletu z bramą i ogrodzeniem. Cynkowanie, malowanie proszkowe, montaż.",
         intro=["Furtka wita każdego, kto odwiedza dom. Wykonujemy furtki proste i łukowe, ażurowe i pełne, z ozdobami wykutymi ręcznie — także z motywami winorośli, liści czy kwiatów.",
                "Najczęściej furtkę projektujemy w komplecie z bramą i ogrodzeniem, żeby całość tworzyła jedną kompozycję. Zabezpieczamy ją przed korozją i montujemy z okuciami."]),
    dict(slug="wiaty", file="wiaty-carport.html", cover="carport.webp",
         h1="Wiaty i carporty", title="Carporty i wiaty stalowe na wymiar",
         desc="Stalowe carporty i wiaty garażowe, zadaszenia nad wejściem — projekt, wykonanie na wymiar, cynkowanie, malowanie proszkowe i montaż.",
         intro=["Carport to wygodna i elegancka alternatywa dla garażu. Projektujemy i wykonujemy stalowe wiaty na samochody oraz zadaszenia — z łukowym lub płaskim dachem, w stylu dopasowanym do domu i ogrodzenia.",
                "Konstrukcję wykonujemy na wymiar, zabezpieczamy cynkowaniem ogniowym i malowaniem proszkowym, a następnie przywozimy i montujemy."]),
    dict(slug="metaloplastyka", file="metaloplastyka.html", cover="daszek.webp",
         h1="Metaloplastyka i mała architektura", title="Metaloplastyka — kute lampy, daszki, ozdoby",
         desc="Metaloplastyka artystyczna: kute żyrandole i kinkiety, daszki nad wejście, lustra, ozdoby i mała architektura ogrodowa.",
         intro=["Metaloplastyka to miejsce, gdzie kowalstwo staje się czystą sztuką. Wykuwamy żyrandole, kinkiety i lampy, ramy luster, daszki nad wejście, ozdoby i elementy małej architektury.",
                "To prace w pełni indywidualne — przygotowujemy projekt pod konkretne wnętrze lub ogród i dopracowujemy każdy detal ręcznie."]),
    dict(slug="bloki", file="bloki.html", cover="bloki.webp",
         h1="Zlecenia dla budynków wielorodzinnych", title="Balustrady dla bloków i inwestycji",
         desc="Balustrady balkonowe i konstrukcje stalowe dla budynków wielorodzinnych i inwestycji deweloperskich — seryjna produkcja, montaż.",
         intro=["Realizujemy także większe zlecenia: balustrady balkonowe, ogrodzenia i konstrukcje stalowe dla budynków wielorodzinnych i inwestycji deweloperskich.",
                "Przy produkcji seryjnej dbamy o powtarzalność i terminowość, zachowując tę samą jakość wykonania i zabezpieczenia antykorozyjnego, co przy pracach indywidualnych."]),
    dict(slug="rozne", file="rozne.html", cover="altana.webp",
         h1="Meble kute, altany i inne realizacje", title="Kute meble, łóżka, altany i dodatki",
         desc="Kute meble i dodatki: łóżka, stoły, krzesła, biurka, karnisze, huśtawki ogrodowe i altany. Unikalne realizacje Kowalstwa Artystycznego Marek Mida.",
         intro=["Nie ma dla nas rzeczy niemożliwych. Poza bramami i balustradami wykuwamy meble i dodatki: łóżka, stoły, krzesła, biurka, karnisze, a także huśtawki ogrodowe, ławki i altany.",
                "Każdy taki przedmiot powstaje na zamówienie — od szkicu po ostatni szlif — i jest jedyny w swoim rodzaju."]),
]

# Stare adresy -> nowe (przekierowanie 301 przenosi "moc" starego adresu w Google)
REDIRECTS = {
    "/index.html": "/",
    "/offer.html": "/#oferta",
    "/about.html": "/#o-nas",
    "/contact.html": "/#kontakt",
    "/bramy-wjazdowe-2.html": "/bramy-wjazdowe.html",
    "/bramy-wjazdowe-3.html": "/bramy-wjazdowe.html",
    "/segmenty-ogrodzeniowe-2.html": "/segmenty-ogrodzeniowe.html",
    "/segmenty-ogrodzeniowe-3.html": "/segmenty-ogrodzeniowe.html",
    "/balustrady-zewnetrzne-2.html": "/balustrady-zewnetrzne.html",
    "/balustrady-zewnetrzne-3.html": "/balustrady-zewnetrzne.html",
    "/others.html": "/rozne.html",
}

FAQ = [
    ("Czy wykonujecie projekty na indywidualne zamówienie?",
     "Tak. Każdy pomysł przełożymy na gotowy wyrób — projektujemy bramy, ogrodzenia, balustrady i metaloplastykę pod konkretny dom, wnętrze i gust klienta."),
    ("Jak zabezpieczacie wyroby przed rdzą?",
     "Stosujemy cynkowanie ogniowe i malowanie proszkowe. To połączenie daje najlepszą, wieloletnią ochronę stali przed korozją."),
    ("Czy zajmujecie się transportem i montażem?",
     "Tak, zapewniamy kompleksową obsługę: od projektu i doradztwa, przez wykonanie, po transport i montaż gotowego zamówienia."),
    ("Gdzie realizujecie zamówienia?",
     "Pracownia mieści się w Iwkowej (Małopolska). Nasze prace trafiły do klientów w całej Polsce, a także w Niemczech, Austrii, Holandii, Szwecji, Anglii, Francji i w USA."),
]


# ---------------------------------------------------------------------------
# Wspólne kawałki HTML (nagłówek, stopka) — jedna zmiana = zmiana na wszystkich podstronach
# ---------------------------------------------------------------------------
def header_html():
    links = [("o-nas", "O nas"), ("oferta", "Oferta"), ("proces", "Jak pracujemy"),
             ("galeria", "Realizacje"), ("film", "Film"), ("kontakt", "Kontakt")]
    lis = "\n".join(f'          <li><a href="./#{a}">{t}</a></li>' for a, t in links)
    return f'''  <a class="skip-link" href="#main">Przejdź do treści</a>
  <header class="site-header is-scrolled" data-header>
    <div class="container site-header__inner">
      <a href="./" class="brand" aria-label="Kowalstwo Artystyczne Marek Mida — strona główna">
        <img src="assets/img/monogram.png" alt="" width="400" height="168" class="brand__mark">
        <span class="brand__text">
          <span class="brand__name">Marek Mida</span>
          <span class="brand__sub">Kowalstwo artystyczne</span>
        </span>
      </a>
      <button class="nav-toggle" aria-expanded="false" aria-controls="site-nav" data-nav-toggle>
        <span class="sr-only">Menu</span>
        <span class="nav-toggle__bar"></span>
        <span class="nav-toggle__bar"></span>
      </button>
      <nav id="site-nav" class="site-nav" aria-label="Główna nawigacja" data-nav>
        <ul class="site-nav__list">
{lis}
        </ul>
        <a href="tel:{PHONE}" class="btn btn--ember btn--sm site-nav__cta">{PHONE_HUMAN}</a>
      </nav>
    </div>
  </header>'''


def footer_html():
    cats = "\n".join(f'          <li><a href="{c["file"]}">{esc(c["h1"])}</a></li>' for c in CATEGORIES)
    return f'''  <footer class="site-footer">
    <div class="container site-footer__inner">
      <img src="assets/img/logo.png" alt="Kowalstwo Artystyczne Marek Mida" width="900" height="430" class="site-footer__logo" loading="lazy">
      <p>Kształtujemy formy z metalu od 1997 roku.</p>
      <!-- Linki do wszystkich podstron w stopce = "linkowanie wewnętrzne": Google łatwiej
           odkrywa podstrony i rozumie, o czym jest serwis -->
      <nav class="site-footer__nav" aria-label="Oferta">
        <ul role="list">
{cats}
        </ul>
      </nav>
      <address class="site-footer__address">
        Kowalstwo Artystyczne Marek Mida · Iwkowa 268, 32-861 Iwkowa ·
        <a href="tel:{PHONE}">{PHONE_HUMAN}</a> · <a href="mailto:{EMAIL}">{EMAIL}</a>
      </address>
      <p class="site-footer__copy">© <span data-year>{date.today().year}</span> Kowalstwo Artystyczne Marek Mida ·
        <a href="polityka-prywatnosci.html">Polityka prywatności</a></p>
    </div>
  </footer>'''


LIGHTBOX = '''  <a href="tel:+48695695813" class="call-fab" aria-label="Zadzwoń: 695 695 813">
    <svg aria-hidden="true" viewBox="0 0 24 24"><path d="M6.6 10.8a15.1 15.1 0 0 0 6.6 6.6l2.2-2.2a1 1 0 0 1 1-.25 11.4 11.4 0 0 0 3.6.57 1 1 0 0 1 1 1V20a1 1 0 0 1-1 1A17 17 0 0 1 3 4a1 1 0 0 1 1-1h3.5a1 1 0 0 1 1 1c0 1.25.2 2.45.57 3.57a1 1 0 0 1-.25 1z"/></svg>
  </a>
  <dialog class="lightbox" data-lightbox aria-label="Podgląd zdjęcia">
    <figure class="lightbox__figure">
      <img data-lightbox-img alt="">
      <figcaption data-lightbox-caption></figcaption>
    </figure>
    <button class="lightbox__btn lightbox__close" data-lightbox-close aria-label="Zamknij">✕</button>
    <button class="lightbox__btn lightbox__prev" data-lightbox-prev aria-label="Poprzednie zdjęcie">‹</button>
    <button class="lightbox__btn lightbox__next" data-lightbox-next aria-label="Następne zdjęcie">›</button>
  </dialog>'''


def page(*, path, title, desc, body, og_image="assets/img/og-image.jpg", jsonld=None, scripts=True, robots=None):
    """Składa pełny dokument HTML. Każda strona dostaje własny <title>, opis, canonical i OG."""
    url = SITE + ("" if path == "index.html" else path)
    ld = "".join(f'\n  <script type="application/ld+json">{json.dumps(j, ensure_ascii=False)}</script>' for j in (jsonld or []))
    rob = f'\n  <meta name="robots" content="{robots}">' if robots else ""
    js = ('\n  <script src="assets/data/gallery.js" defer></script>\n  <script src="assets/js/main.js" defer></script>'
          if scripts else "")
    return f'''<!doctype html>
<html lang="pl">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
  <title>{esc(title)}</title>
  <meta name="description" content="{esc(desc)}">{rob}
  <meta name="theme-color" content="#14110f">
  <link rel="canonical" href="{url}">
  <link rel="icon" type="image/png" href="assets/img/favicon.png">
  <link rel="apple-touch-icon" href="assets/img/apple-touch-icon.png">
  <meta property="og:type" content="website">
  <meta property="og:locale" content="pl_PL">
  <meta property="og:site_name" content="Kowalstwo Artystyczne Marek Mida">
  <meta property="og:title" content="{esc(title)}">
  <meta property="og:description" content="{esc(desc)}">
  <meta property="og:url" content="{url}">
  <meta property="og:image" content="{SITE}{og_image}">
  <link rel="preload" href="assets/fonts/cormorant-garamond-latin-wght-normal.woff2" as="font" type="font/woff2" crossorigin>
  <link rel="preload" href="assets/fonts/manrope-latin-wght-normal.woff2" as="font" type="font/woff2" crossorigin>
  <link rel="stylesheet" href="assets/css/style.css">
  <script>document.documentElement.classList.add("js")</script>{ld}
</head>
<body>
{header_html()}
  <main id="main">
{body}
  </main>
{footer_html()}
{LIGHTBOX if scripts else ""}{js}
</body>
</html>
'''


def business_ld():
    """Opis firmy dla Google (schema.org) — wspólny dla wszystkich stron."""
    return {
        "@type": "HomeAndConstructionBusiness", "@id": SITE + "#firma",
        "name": "Kowalstwo Artystyczne Marek Mida", "url": SITE,
        "image": SITE + "assets/img/og-image.jpg", "logo": SITE + "assets/img/logo.png",
        "telephone": PHONE, "email": EMAIL, "foundingDate": "1997",
        "founder": {"@type": "Person", "name": "Marek Mida"},
        "address": {"@type": "PostalAddress", "streetAddress": "Iwkowa 268", "postalCode": "32-861",
                    "addressLocality": "Iwkowa", "addressRegion": "małopolskie", "addressCountry": "PL"},
        "areaServed": ["PL", "DE", "AT", "NL", "SE", "GB", "FR", "US"],
        "knowsAbout": ["kowalstwo artystyczne", "metaloplastyka", "bramy kute", "balustrady kute",
                       "ogrodzenia kute", "cynkowanie ogniowe", "malowanie proszkowe"],
        "hasOfferCatalog": {
            "@type": "OfferCatalog", "name": "Oferta pracowni",
            "itemListElement": [{"@type": "Offer", "itemOffered": {"@type": "Service", "name": c["h1"],
                                 "url": SITE + c["file"]}} for c in CATEGORIES],
        },
    }


# ---------------------------------------------------------------------------
# Generowanie podstron
# ---------------------------------------------------------------------------
def load_gallery():
    js = (ROOT / "assets/data/gallery.js").read_text(encoding="utf-8")
    return json.loads(js[js.index("{"): js.rindex("}") + 1])


def category_page(cat, items, data):
    G = "assets/img/gallery/"
    cover = f"assets/img/{cat['cover']}"
    cw, ch = Image.open(ROOT / cover).size
    label = next(c["label"] for c in data["categories"] if c["slug"] == cat["slug"])
    lis = []
    for i, it in enumerate(items):
        extra = ' class="is-extra" hidden' if i >= INITIAL else ""
        # alt z numerem: każdy obrazek ma inny, opisowy tekst alternatywny (SEO grafiki + dostępność)
        lis.append(f'''          <li{extra}><button type="button" aria-label="Powiększ zdjęcie {i + 1} z {len(items)}">
            <img src="{G}thumb/{it['f']}" width="{it['w']}" height="{it['h']}" alt="{esc(cat['h1'])} — realizacja {i + 1}, Kowalstwo Artystyczne Marek Mida" loading="lazy" decoding="async">
          </button></li>''')
    more = (f'''
        <div class="gallery__more">
          <button class="btn btn--ghost" type="button" onclick="this.parentElement.previousElementSibling.querySelectorAll('[hidden]').forEach(e=>e.hidden=false);this.parentElement.remove()">Pokaż wszystkie ({len(items)})</button>
        </div>''' if len(items) > INITIAL else "")
    others = "\n".join(
        f'''          <a href="{c['file']}" class="tile reveal"><img src="assets/img/{c['cover']}" alt="" loading="lazy">
            <span class="tile__body"><span class="tile__title">{esc(c['h1'])}</span></span></a>'''
        for c in CATEGORIES if c["slug"] != cat["slug"])
    intro = "\n".join(f'          <p class="reveal">{esc(p)}</p>' for p in cat["intro"])

    body = f'''    <nav class="breadcrumbs container" aria-label="Okruszki">
      <ol>
        <li><a href="./">Strona główna</a></li>
        <li><a href="./#oferta">Oferta</a></li>
        <li aria-current="page">{esc(cat['h1'])}</li>
      </ol>
    </nav>

    <section class="page-hero" aria-labelledby="page-title">
      <img class="page-hero__bg" src="{cover}" width="{cw}" height="{ch}" alt="" fetchpriority="high">
      <div class="container page-hero__inner">
        <p class="eyebrow">Oferta · {len(items)} realizacji</p>
        <h1 id="page-title" class="h2">{esc(cat['h1'])}</h1>
        <p class="page-hero__lead">{esc(cat['desc'].split(' — ')[0].split('. ')[0])}.</p>
        <div class="hero__actions">
          <a href="tel:{PHONE}" class="btn btn--ember">Zadzwoń: {PHONE_HUMAN}</a>
          <a href="#realizacje" class="btn btn--ghost">Zobacz realizacje</a>
        </div>
      </div>
    </section>

    <section class="section section--tight">
      <div class="container cat-intro">
        <div>
{intro}
        </div>
        <ul class="cat-intro__list" role="list">
          <li class="reveal">Projekt na wymiar i doradztwo</li>
          <li class="reveal">Ręczne kucie — ogień, młot i kowadło</li>
          <li class="reveal">Cynkowanie ogniowe i malowanie proszkowe</li>
          <li class="reveal">Transport i montaż</li>
        </ul>
      </div>
    </section>

    <section class="section section--tight" id="realizacje" aria-labelledby="real-title">
      <div class="container">
        <h2 id="real-title" class="h2 reveal">Nasze realizacje — <em>{esc(label.lower())}</em></h2>
        <ul class="cat-grid" role="list" data-category-grid="{cat['slug']}">
{chr(10).join(lis)}
        </ul>{more}
      </div>
    </section>

    <section class="section section--tight">
      <div class="container">
        <h2 class="h2 reveal">Zobacz też <em>inne realizacje</em></h2>
        <div class="bento bento--small">
{others}
        </div>
      </div>
    </section>'''

    ld = [
        {"@context": "https://schema.org", "@graph": [
            business_ld(),
            {"@type": "Service", "name": cat["h1"], "description": cat["desc"], "url": SITE + cat["file"],
             "provider": {"@id": SITE + "#firma"}, "areaServed": "PL",
             "image": [SITE + G + "full/" + it["f"] for it in items[:6]]},
            {"@type": "BreadcrumbList", "itemListElement": [
                {"@type": "ListItem", "position": 1, "name": "Strona główna", "item": SITE},
                {"@type": "ListItem", "position": 2, "name": "Oferta", "item": SITE + "#oferta"},
                {"@type": "ListItem", "position": 3, "name": cat["h1"], "item": SITE + cat["file"]}]},
        ]}
    ]
    return page(path=cat["file"], title=f"{cat['title']} | Kowalstwo Marek Mida",
                desc=cat["desc"], body=body, og_image=cover, jsonld=ld)


def privacy_page():
    body = f'''    <section class="section legal">
      <div class="container legal__inner">
        <h1 class="h2">Polityka prywatności</h1>
        <p>Szanujemy Twoją prywatność. Poniżej wyjaśniamy prostym językiem, jakie dane mogą być
          przetwarzane, gdy korzystasz z tej strony.</p>

        <h2>Administrator danych</h2>
        <p>Kowalstwo Artystyczne Marek Mida, Iwkowa 268, 32-861 Iwkowa,
          tel. <a href="tel:{PHONE}">{PHONE_HUMAN}</a>, e-mail <a href="mailto:{EMAIL}">{EMAIL}</a>.</p>

        <h2>Kontakt telefoniczny i e-mail</h2>
        <p>Jeśli zadzwonisz lub napiszesz, przetwarzamy dane, które sam podasz (np. imię, numer telefonu,
          adres e-mail, treść zapytania), wyłącznie po to, aby odpowiedzieć i przygotować wycenę lub
          zrealizować zamówienie (art. 6 ust. 1 lit. b i f RODO). Dane przechowujemy tak długo, jak to
          potrzebne do obsługi zapytania i rozliczeń wymaganych prawem.</p>

        <h2>Pliki cookies</h2>
        <p>Sama strona <strong>nie zapisuje własnych plików cookies</strong> i nie używa narzędzi śledzących
          (np. Google Analytics). Czcionki i pliki strony są ładowane z naszego serwera.</p>

        <h2>Mapa Google</h2>
        <p>W sekcji „Kontakt” osadzona jest mapa Google Maps, aby ułatwić dojazd do pracowni. Podczas jej
          wyświetlania Twoja przeglądarka łączy się z serwerami Google LLC, które mogą zapisać pliki cookies
          i otrzymać Twój adres IP — zgodnie z
          <a href="https://policies.google.com/privacy?hl=pl" rel="noopener">polityką prywatności Google</a>.
          Możesz zablokować pliki cookies podmiotów trzecich w ustawieniach przeglądarki.</p>

        <h2>Logi serwera</h2>
        <p>Jak każda strona internetowa, serwer hostingowy zapisuje techniczne informacje o odwiedzinach
          (adres IP, data i godzina, rodzaj przeglądarki). Służą one wyłącznie bezpieczeństwu i poprawnemu
          działaniu strony.</p>

        <h2>Twoje prawa</h2>
        <p>Masz prawo do dostępu do swoich danych, ich sprostowania, usunięcia, ograniczenia przetwarzania,
          przeniesienia oraz wniesienia sprzeciwu. Możesz też złożyć skargę do Prezesa Urzędu Ochrony
          Danych Osobowych (ul. Stawki 2, 00-193 Warszawa). W sprawach danych osobowych napisz na
          <a href="mailto:{EMAIL}">{EMAIL}</a>.</p>
        <p><a href="./" class="btn btn--ghost">← Wróć na stronę główną</a></p>
      </div>
    </section>'''
    return page(path="polityka-prywatnosci.html", title="Polityka prywatności | Kowalstwo Marek Mida",
                desc="Polityka prywatności strony Kowalstwa Artystycznego Marek Mida — dane kontaktowe, pliki cookies, mapa Google, prawa RODO.",
                body=body, scripts=True)


def not_found_page():
    body = '''    <section class="section legal">
      <div class="container legal__inner" style="text-align:center">
        <p class="eyebrow">Błąd 404</p>
        <h1 class="h2">Tej strony <em>nie wykuliśmy</em></h1>
        <p>Strona, której szukasz, nie istnieje lub została przeniesiona.</p>
        <div class="hero__actions" style="justify-content:center">
          <a href="/" class="btn btn--ember">Strona główna</a>
          <a href="/#oferta" class="btn btn--ghost">Zobacz ofertę</a>
        </div>
      </div>
    </section>'''
    # noindex: strona błędu nie powinna trafić do wyników wyszukiwania
    return page(path="404.html", title="Nie znaleziono strony | Kowalstwo Marek Mida",
                desc="Nie znaleziono strony.", body=body, robots="noindex")


def sitemap():
    today = date.today().isoformat()
    urls = [("", "1.0")] + [(c["file"], "0.8") for c in CATEGORIES] + [("polityka-prywatnosci.html", "0.2")]
    rows = "\n".join(f"  <url><loc>{SITE}{u}</loc><lastmod>{today}</lastmod><priority>{p}</priority></url>" for u, p in urls)
    return f'<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n{rows}\n</urlset>\n'


def htaccess():
    redirects = "\n".join(f"Redirect 301 {old} {new}" for old, new in REDIRECTS.items() if old != "/index.html")
    return f'''# ==========================================================================
# Konfiguracja serwera Apache (plik musi się nazywać dokładnie ".htaccess")
# ==========================================================================

RewriteEngine On

# 1) Jeden adres strony: https + www. Bez tego Google widzi 4 kopie strony
#    (http/https x z www/bez www) i dzieli między nie pozycję.
RewriteCond %{{HTTPS}} off [OR]
RewriteCond %{{HTTP_HOST}} !^www\\. [NC]
RewriteRule ^(.*)$ https://www.kowalstwoartystyczne.com/$1 [L,R=301]

# 2) /index.html -> / (żeby strona główna nie miała dwóch adresów)
RewriteCond %{{THE_REQUEST}} \\s/index\\.html [NC]
RewriteRule ^index\\.html$ / [L,R=301]

# 3) Stare adresy -> nowe. 301 = "przeniesione na stałe": Google przenosi pozycję
#    starej podstrony na nową, a linki z innych stron dalej działają.
{redirects}

# 4) Własna strona błędu
ErrorDocument 404 /404.html

# 5) Kompresja tekstu (HTML/CSS/JS) — pliki lecą do przeglądarki nawet 70% mniejsze
<IfModule mod_deflate.c>
  AddOutputFilterByType DEFLATE text/html text/css application/javascript text/javascript application/json image/svg+xml application/xml text/xml
</IfModule>

# 6) Cache w przeglądarce: zdjęcia, fonty i film rzadko się zmieniają -> rok;
#    HTML krótko, żeby zmiany na stronie były widoczne od razu.
<IfModule mod_expires.c>
  ExpiresActive On
  ExpiresByType image/webp "access plus 1 year"
  ExpiresByType image/png "access plus 1 year"
  ExpiresByType image/jpeg "access plus 1 year"
  ExpiresByType font/woff2 "access plus 1 year"
  ExpiresByType video/mp4 "access plus 1 year"
  ExpiresByType text/css "access plus 1 week"
  ExpiresByType application/javascript "access plus 1 week"
  ExpiresByType text/html "access plus 0 seconds"
</IfModule>

# 7) Podstawowe nagłówki bezpieczeństwa
<IfModule mod_headers.c>
  Header always set X-Content-Type-Options "nosniff"
  Header always set Referrer-Policy "strict-origin-when-cross-origin"
  Header always set X-Frame-Options "SAMEORIGIN"
</IfModule>

# Nie pokazuj listy plików w katalogach
Options -Indexes
'''


def faq_html():
    items = "\n".join(f'''        <details class="faq__item reveal">
          <summary>{esc(q)}</summary>
          <p>{esc(a)}</p>
        </details>''' for q, a in FAQ)
    return f'''    <section class="section faq" id="faq" aria-labelledby="faq-title">
      <div class="container faq__inner">
        <header class="section-head">
          <p class="eyebrow reveal">Pytania</p>
          <h2 id="faq-title" class="h2 reveal">Najczęściej <em>pytacie</em></h2>
        </header>
        <!-- <details>/<summary>: natywny "akordeon" — działa bez JS, dostępny z klawiatury -->
        <div class="faq__list">
{items}
        </div>
      </div>
    </section>'''


def update_index():
    """Wstawia do index.html wspólne fragmenty między znaczniki <!-- BUILD:X --> ... <!-- /BUILD:X -->."""
    p = ROOT / "index.html"
    t = p.read_text(encoding="utf-8")
    ld = {"@context": "https://schema.org", "@graph": [
        business_ld(),
        {"@type": "WebSite", "@id": SITE + "#strona", "url": SITE, "name": "Kowalstwo Artystyczne Marek Mida",
         "inLanguage": "pl-PL", "publisher": {"@id": SITE + "#firma"}},
    ]}
    parts = {
        "LD": f'  <script type="application/ld+json">{json.dumps(ld, ensure_ascii=False)}</script>',
        "FAQ": faq_html(),
        "FOOTER": footer_html(),
    }
    for key, content in parts.items():
        t, n = re.subn(rf"(<!-- BUILD:{key} -->).*?(\s*<!-- /BUILD:{key} -->)",
                       lambda m: m.group(1) + "\n" + content + m.group(2), t, flags=re.S)
        assert n == 1, f"brak znacznika BUILD:{key} w index.html"
    p.write_text(t, encoding="utf-8")


def main():
    preview = "--preview" in sys.argv
    update_index()
    data = load_gallery()
    out = {}
    for cat in CATEGORIES:
        items = [it for it in data["items"] if it["c"] == cat["slug"]]
        out[cat["file"]] = category_page(cat, items, data)
    out["polityka-prywatnosci.html"] = privacy_page()
    out["404.html"] = not_found_page()
    for name, content in out.items():
        (ROOT / name).write_text(content, encoding="utf-8")
    (ROOT / "sitemap.xml").write_text(sitemap(), encoding="utf-8")
    (ROOT / "robots.txt").write_text(f"User-agent: *\nAllow: /\n\nSitemap: {SITE}sitemap.xml\n", encoding="utf-8")
    (ROOT / ".htaccess").write_text(htaccess(), encoding="utf-8")
    print(f"Wygenerowano: {len(out)} stron HTML, sitemap.xml, robots.txt, .htaccess")

    # --- paczka dist/ = tylko to, co ma trafić na serwer ---
    dist = ROOT / "dist"
    shutil.rmtree(dist, ignore_errors=True)
    dist.mkdir()
    for f in ["index.html", *out.keys(), "sitemap.xml", "robots.txt", ".htaccess"]:
        shutil.copy2(ROOT / f, dist / f)
    shutil.copytree(ROOT / "assets", dist / "assets",
                    ignore=shutil.ignore_patterns("soundtrack.wav"))
    if preview:
        # Podgląd na GitHub Pages: noindex na każdej stronie (Google nie zaindeksuje kopii)
        for f in dist.glob("*.html"):
            t = f.read_text(encoding="utf-8")
            if 'name="robots"' not in t:
                t = t.replace('<meta name="theme-color"', '<meta name="robots" content="noindex, nofollow">\n  <meta name="theme-color"', 1)
            f.write_text(t, encoding="utf-8")
        (dist / ".nojekyll").touch()
        (dist / ".htaccess").unlink()  # GitHub Pages i tak go nie czyta
        # 404.html na GitHub Pages: linki "/" prowadzą do roota domeny, nie do /test/ — poprawiamy
        t = (dist / "404.html").read_text(encoding="utf-8").replace('href="/"', 'href="./"').replace('href="/#', 'href="./#')
        (dist / "404.html").write_text(t, encoding="utf-8")
    size = sum(p.stat().st_size for p in dist.rglob("*") if p.is_file()) / 1e6
    print(f"dist/ gotowe ({size:.0f} MB){' — wersja PODGLĄDOWA (noindex)' if preview else ' — wersja PRODUKCYJNA'}")


if __name__ == "__main__":
    main()

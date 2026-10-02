"""
Generator filmu reklamowego Kowalstwa Artystycznego.

Jak to działa (w skrócie):
  Film = seria obrazków (klatek) wyświetlanych 30 razy na sekundę.
  Ten skrypt RYSUJE każdą klatkę w Pythonie (biblioteka Pillow): zdjęcie z
  powolnym zbliżeniem (efekt "Ken Burns"), napisy, winieta, iskry.
  Gotowe klatki wysyłamy strumieniem (pipe) do programu ffmpeg, który
  skleja je w plik MP4 (kodek H.264) i dokłada dźwięk.

  Dźwięk też jest generowany: ffmpeg potrafi liczyć falę dźwiękową z wzoru
  matematycznego (filtr "aevalsrc"). Uderzenie w kowadło = kilka tonów
  (sinusów) o wysokich częstotliwościach, które szybko wygasają (exp(-k*t)).

Uruchomienie:
    python3 scripts/make_video.py            # oba formaty
    python3 scripts/make_video.py wide       # tylko 16:9 (strona, YouTube, Facebook)
    python3 scripts/make_video.py vertical   # tylko 9:16 (Reels, TikTok, Shorts)
"""
import math
import random
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parent.parent
OLD = ROOT / "old" / "images"
OUT = ROOT / "assets" / "video"
FONTS = ROOT / "scripts" / "fonts"
FPS = 30

try:
    import imageio_ffmpeg  # pip install imageio-ffmpeg  (gotowy ffmpeg w paczce Pythona)
    FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
except ImportError:
    FFMPEG = "ffmpeg"

# Kolory marki — te same co w CSS strony (spójność!)
EMBER = (232, 121, 47)
EMBER_2 = (246, 177, 90)
IVORY = (239, 230, 216)
BG = (20, 17, 15)


def font(name, size, weight):
    """Fonty zmienne: jeden plik, a grubość (wght) ustawiamy liczbą 300-800."""
    f = ImageFont.truetype(str(FONTS / name), size)
    f.set_variation_by_axes([weight])
    return f


# ---------------------------------------------------------------------------
# SCENARIUSZ — lista scen. Każda: typ, czas trwania [s] i parametry.
# Chcesz zmienić film? Edytuj tylko tę listę.
# ---------------------------------------------------------------------------
SCENES = [
    {"type": "logo", "dur": 3.6},
    {"type": "title", "dur": 3.4, "img": "mention.jpg",
     "kicker": "OD 1997 ROKU", "lines": ["Kształtujemy", "formy z metalu"]},
    {"type": "product", "dur": 2.5, "img": "bramy-87.jpg", "no": "01", "label": "Bramy wjazdowe"},
    {"type": "product", "dur": 2.5, "img": "bal-zewn-107.jpg", "no": "02", "label": "Balustrady"},
    {"type": "product", "dur": 2.5, "img": "segm-ogr-37.jpg", "no": "03", "label": "Ogrodzenia"},
    {"type": "product", "dur": 2.5, "img": "furtki-35.jpg", "no": "04", "label": "Furtki"},
    {"type": "product", "dur": 2.5, "img": "wiaty-13.jpg", "no": "05", "label": "Carporty i wiaty"},
    {"type": "product", "dur": 2.5, "img": "others/14.jpg", "no": "06", "label": "Meble kute"},
    {"type": "product", "dur": 2.5, "img": "metaloplastyka-archit/4.jpg", "no": "07", "label": "Lampy i żyrandole"},
    {"type": "product", "dur": 2.5, "img": "others-12.jpg", "no": "08", "label": "Mała architektura"},
    {"type": "words", "dur": 3.0, "img": "bal-wewn-1.jpg", "words": ["Ogień.", "Młot.", "Kowadło."]},
    {"type": "title", "dur": 3.4, "img": "bramy-wjazdowe/1.jpg",
     "kicker": "CYNKOWANIE · MALOWANIE PROSZKOWE · MONTAŻ", "lines": ["Trwałość", "na pokolenia"]},
    {"type": "end", "dur": 4.6},
]
XFADE = 0.45  # długość przenikania między scenami [s]


# ---------------------------------------------------------------------------
# Narzędzia graficzne
# ---------------------------------------------------------------------------
def ease(t):
    """easeInOutCubic: ruch zaczyna się i kończy łagodnie (wygląda "filmowo")."""
    t = max(0.0, min(1.0, t))
    return 4 * t * t * t if t < 0.5 else 1 - (-2 * t + 2) ** 3 / 2


def ease_out(t):
    t = max(0.0, min(1.0, t))
    return 1 - (1 - t) ** 3


def grade(im):
    """Korekcja barw "w stylu kuźni": lekko ciemniej, cieplej, mniej nasycone zielenie."""
    im = im.convert("RGB")
    r, g, b = im.split()
    r = r.point(lambda v: min(255, int(v * 1.04 + 4)))
    b = b.point(lambda v: int(v * 0.86))
    g = g.point(lambda v: int(v * 0.95))
    return Image.merge("RGB", (r, g, b))


def ken_burns(src, W, H, p, seed):
    """Zwraca kadr W×H z obrazu src, z powolnym zbliżeniem i przesunięciem.
    p = postęp sceny 0..1. Kierunek ruchu zależy od seed, żeby sceny się różniły."""
    rnd = random.Random(seed)
    zoom_in = rnd.random() > 0.35
    z0, z1 = (1.0, 1.14) if zoom_in else (1.14, 1.0)
    dx, dy = rnd.uniform(-0.5, 0.5), rnd.uniform(-0.3, 0.3)
    z = z0 + (z1 - z0) * p
    sw, sh = src.size
    # "cover": największy kadr o proporcjach W:H mieszczący się w zdjęciu
    base = min(sw / W, sh / H)
    cw, ch = W * base / z, H * base / z
    cx = sw / 2 + dx * (sw - cw) / 2 * (p * 2 - 1)
    cy = sh / 2 + dy * (sh - ch) / 2 * (p * 2 - 1)
    box = (cx - cw / 2, cy - ch / 2, cx + cw / 2, cy + ch / 2)
    # resize z parametrem box = wycięcie + skalowanie w jednym kroku, z dokładnością subpikselową
    return src.resize((W, H), Image.BICUBIC, box=box)


def blurred_cover(src, W, H):
    """Rozmyte tło (do pionowego formatu, gdy zdjęcie jest poziome)."""
    small = ken_burns(src, W // 8, H // 8, 0.5, 0)
    return small.filter(ImageFilter.GaussianBlur(6)).resize((W, H), Image.BICUBIC)


def make_vignette(W, H):
    """Ciemne rogi + przyciemniony dół (żeby napisy były czytelne). Liczone raz."""
    small = Image.new("L", (160, int(160 * H / W)))
    sw, sh = small.size
    px = small.load()
    for y in range(sh):
        for x in range(sw):
            nx, ny = (x / sw - 0.5) * 2, (y / sh - 0.5) * 2
            d = math.sqrt(nx * nx * 0.8 + ny * ny * 0.6)
            v = max(0.0, d - 0.35) * 190
            v += max(0.0, (y / sh) - 0.45) * 330  # gradient od połowy w dół
            px[x, y] = int(min(235, v))
    mask = small.resize((W, H), Image.BICUBIC).filter(ImageFilter.GaussianBlur(4))
    layer = Image.new("RGBA", (W, H), BG + (0,))
    layer.putalpha(mask)
    return layer


def text_layer(W, H, items):
    """Rysuje napisy na przezroczystej warstwie. items = [(tekst, font, (x, y), kolor, anchor, tracking)]."""
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    for txt, f, (x, y), color, anchor, track in items:
        if track:
            # Rozstrzelony tekst (letter-spacing) — Pillow nie ma tego wbudowanego,
            # więc stawiamy litery pojedynczo.
            total = sum(f.getlength(c) for c in txt) + track * (len(txt) - 1)
            cx = x - total / 2 if anchor[0] == "m" else x
            for c in txt:
                d.text((cx, y), c, font=f, fill=color, anchor="l" + anchor[1])
                cx += f.getlength(c) + track
        else:
            d.text((x, y), txt, font=f, fill=color, anchor=anchor)
    return layer


def with_alpha(layer, a):
    """Mnoży przezroczystość warstwy przez a (0..1) — do płynnego pojawiania się napisów."""
    if a >= 0.999:
        return layer
    out = layer.copy()
    out.putalpha(layer.getchannel("A").point(lambda v: int(v * a)))
    return out


def gradient_text(W, H, txt, f, pos, anchor="la"):
    """Tekst wypełniony gradientem "żaru" (jak nagłówki na stronie)."""
    mask = Image.new("L", (W, H), 0)
    ImageDraw.Draw(mask).text(pos, txt, font=f, fill=255, anchor=anchor)
    bbox = mask.getbbox() or (0, 0, 1, 1)
    grad = Image.new("RGBA", (W, H), EMBER + (0,))
    gd = ImageDraw.Draw(grad)
    x0, x1 = bbox[0], max(bbox[2], bbox[0] + 1)
    for x in range(x0, x1):
        t = (x - x0) / (x1 - x0)
        c = tuple(int(EMBER_2[i] + (EMBER[i] - EMBER_2[i]) * t) for i in range(3))
        gd.line([(x, bbox[1]), (x, bbox[3])], fill=c + (255,))
    grad.putalpha(mask)  # kształt liter = maska przezroczystości gradientu
    return grad


class Sparks:
    """Iskry z paleniska — te same co na stronie, tylko liczone w Pythonie."""

    def __init__(self, W, H, n):
        self.W, self.H, self.n = W, H, n
        self.rnd = random.Random(7)
        self.p = [self.spawn(initial=True) for _ in range(n)]

    def spawn(self, initial=False):
        r = self.rnd
        return {
            "x": r.uniform(0, self.W), "y": r.uniform(0, self.H) if initial else self.H + r.uniform(0, 60),
            "vx": r.uniform(-0.6, 0.9), "vy": -r.uniform(1.5, 5.0) * self.H / 1080,
            "r": r.uniform(1.2, 3.6) * self.W / 1920 * 1.4, "life": 0, "max": r.uniform(60, 160),
            "ph": r.uniform(0, 6.28),
        }

    def step_and_draw(self, intensity):
        """Zwraca warstwę RGB z iskrami (czarne tło) — nakładana trybem "screen" (rozjaśnianie)."""
        s = 4  # rysujemy w 1/4 rozdzielczości i rozmywamy = tanio i daje "poświatę"
        layer = Image.new("RGB", (self.W // s, self.H // s), (0, 0, 0))
        d = ImageDraw.Draw(layer)
        for i, p in enumerate(self.p):
            p["life"] += 1
            p["x"] += p["vx"] + math.sin(p["life"] * 0.08 + p["ph"]) * 0.8
            p["y"] += p["vy"]
            if p["life"] > p["max"] or p["y"] < -20:
                self.p[i] = p = self.spawn()
            a = (1 - p["life"] / p["max"]) * intensity
            x, y, r = p["x"] / s, p["y"] / s, max(0.6, p["r"] / s)
            col = (int(255 * a), int(170 * a), int(70 * a))
            d.ellipse([x - r, y - r, x + r, y + r], fill=col)
        glow = layer.filter(ImageFilter.GaussianBlur(1.6))
        return ImageChops.add(glow, layer).resize((self.W, self.H), Image.BILINEAR)


# ---------------------------------------------------------------------------
# Render scen
# ---------------------------------------------------------------------------
class Renderer:
    def __init__(self, W, H):
        self.W, self.H = W, H
        self.vertical = H > W
        u = min(W, H) / 1080  # jednostka skali: projektujemy dla 1080 px, reszta się przelicza
        self.u = u
        self.f_big = font("Cormorant.ttf", int(150 * u), 600)
        self.f_big_i = font("CormorantItalic.ttf", int(150 * u), 600)
        self.f_mid = font("Cormorant.ttf", int(118 * u), 600)
        self.f_mid_i = font("CormorantItalic.ttf", int(118 * u), 600)
        self.f_kick = font("Manrope.ttf", int(26 * u), 700)
        self.f_no = font("CormorantItalic.ttf", int(64 * u), 500)
        self.f_small = font("Manrope.ttf", int(30 * u), 600)
        self.f_phone = font("Cormorant.ttf", int(104 * u), 600)
        self.vignette = make_vignette(W, H)
        self.sparks = Sparks(W, H, 110 if not self.vertical else 90)
        self.logo = Image.open(ROOT / "assets" / "img" / "logo.png").convert("RGBA")
        self.cache = {}

    def src(self, name):
        if name not in self.cache:
            self.cache[name] = grade(Image.open(OLD / name))
        return self.cache[name]

    # Tło sceny ze zdjęciem
    def photo(self, sc, p, seed):
        W, H = self.W, self.H
        im = self.src(sc["img"])
        landscape = im.width > im.height * 1.05
        if self.vertical and landscape:
            # Poziome zdjęcie w pionowym filmie: rozmyte tło + ostre zdjęcie w środku
            bg = blurred_cover(im, W, H)
            ph = int(W / (im.width / im.height) * 1.12)
            fg = ken_burns(im, W, ph, p, seed)
            bg.paste(fg, (0, int(H * 0.38 - ph / 2)))
            return bg
        return ken_burns(im, W, H, p, seed)

    def frame(self, sc, t, idx):
        """Rysuje klatkę sceny sc w czasie t (sekundy od początku sceny)."""
        W, H, u = self.W, self.H, self.u
        p = t / sc["dur"]
        kind = sc["type"]

        if kind in ("logo", "end"):
            im = Image.new("RGB", (W, H), BG)
            # Ciepła poświata od dołu — jak żar w palenisku
            glow = Image.new("L", (W, H), 0)
            gd = ImageDraw.Draw(glow)
            pulse = 0.85 + 0.15 * math.sin(t * 2.4)
            gd.ellipse([W * 0.1, H * 0.62, W * 0.9, H * 1.45], fill=int(150 * pulse))
            glow = glow.filter(ImageFilter.GaussianBlur(int(140 * u)))
            im = Image.composite(Image.new("RGB", (W, H), (120, 45, 12)), im, glow)
        else:
            im = self.photo(sc, ease(p) if kind != "product" else p, idx)

        frame = im.convert("RGBA")
        frame.alpha_composite(self.vignette)

        if kind == "logo":
            a = ease_out((t - 0.35) / 1.4)
            lw = int(W * (0.62 if not self.vertical else 0.84))
            scale = 1.06 - 0.06 * ease_out(t / 3.0)
            lg = self.logo.resize((int(lw * scale), int(lw * scale * self.logo.height / self.logo.width)), Image.LANCZOS)
            frame.alpha_composite(with_alpha(lg, a), ((W - lg.width) // 2, (H - lg.height) // 2 - int(20 * u)))
            lt = text_layer(W, H, [("OD 1997 · IWKOWA, MAŁOPOLSKA", self.f_kick, (W / 2, H / 2 + lg.height / 2 + 50 * u), EMBER_2, "mm", 7 * u)])
            frame.alpha_composite(with_alpha(lt, ease_out((t - 1.5) / 0.9)))

        elif kind == "title":
            # Dodatkowe przyciemnienie — napisy muszą być czytelne także na jasnym zdjęciu
            frame.alpha_composite(Image.new("RGBA", (W, H), BG + (95,)))
            x = W * 0.08
            base_y = H * (0.66 if not self.vertical else 0.76)
            a1 = ease_out((t - 0.2) / 0.7)
            kick = text_layer(W, H, [(sc["kicker"], self.f_kick, (x, base_y - 210 * u), EMBER_2, "ls", 5 * u)])
            line = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            ImageDraw.Draw(line).rectangle([x, base_y - 190 * u, x + 90 * u * a1, base_y - 187 * u], fill=EMBER + (255,))
            frame.alpha_composite(with_alpha(kick, a1))
            frame.alpha_composite(line)
            f1, f2 = (self.f_mid, self.f_mid_i) if self.vertical else (self.f_big, self.f_big_i)
            for k, txt in enumerate(sc["lines"]):
                ak = ease_out((t - 0.35 - k * 0.25) / 0.8)
                dy = (1 - ak) * 40 * u
                y = base_y - 60 * u + k * f1.size * 0.98 + dy
                if k == 1:
                    lay = gradient_text(W, H, txt, f2, (x, y), anchor="ls")
                else:
                    lay = text_layer(W, H, [(txt, f1, (x, y), IVORY, "ls", 0)])
                frame.alpha_composite(with_alpha(lay, ak))

        elif kind == "product":
            x = W * 0.07
            y = H * (0.86 if not self.vertical else 0.80)
            a = ease_out((t - 0.15) / 0.6)
            dx = (1 - a) * -60 * u
            no = text_layer(W, H, [(sc["no"], self.f_no, (x + dx, y - 135 * u), EMBER_2, "ls", 0)])
            bar = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            ImageDraw.Draw(bar).rectangle([x + 80 * u, y - 152 * u, x + 80 * u + 120 * u * a, y - 150 * u], fill=EMBER + (255,))
            f = self.f_mid if (self.vertical or len(sc["label"]) > 14) else self.f_big
            lab = text_layer(W, H, [(sc["label"], f, (x + dx * 0.6, y), IVORY, "ls", 0)])
            frame.alpha_composite(with_alpha(no, a))
            frame.alpha_composite(bar)
            frame.alpha_composite(with_alpha(lab, ease_out((t - 0.3) / 0.6)))

        elif kind == "words":
            dark = Image.new("RGBA", (W, H), BG + (150,))
            frame.alpha_composite(dark)
            n = len(sc["words"])
            per = sc["dur"] / n
            k = min(n - 1, int(t / per))
            local = (t - k * per) / per
            a = ease_out(local / 0.25)
            sz = 1.15 - 0.15 * ease_out(local / 0.5)
            f = font("CormorantItalic.ttf", int(self.f_big.size * 1.25 * sz), 600)
            frame.alpha_composite(with_alpha(gradient_text(W, H, sc["words"][k], f, (W / 2, H / 2), anchor="mm"), a))

        elif kind == "end":
            lw = int(W * (0.42 if not self.vertical else 0.74))
            lg = self.logo.resize((lw, int(lw * self.logo.height / self.logo.width)), Image.LANCZOS)
            top = int(H * (0.18 if not self.vertical else 0.24))
            frame.alpha_composite(with_alpha(lg, ease_out(t / 0.8)), ((W - lg.width) // 2, top))
            cy = top + lg.height + 130 * u
            items = [
                ("BEZPŁATNA WYCENA", self.f_kick, (W / 2, cy), EMBER_2, "mm", 7 * u),
                ("695 695 813", self.f_phone, (W / 2, cy + 105 * u), IVORY, "mm", 4 * u),
                ("kowalstwoartystyczne.com", self.f_small, (W / 2, cy + 205 * u), (179, 167, 151), "mm", 2 * u),
            ]
            for k, it in enumerate(items):
                frame.alpha_composite(with_alpha(text_layer(W, H, [it]), ease_out((t - 0.5 - k * 0.25) / 0.7)))

        # Iskry — mocniej na logo i końcówce, delikatnie na zdjęciach
        inten = {"logo": 1.0, "end": 1.0, "words": 0.9}.get(kind, 0.45)
        rgb = frame.convert("RGB")
        return ImageChops.screen(rgb, self.sparks.step_and_draw(inten))


def timeline():
    """Początki scen na osi czasu (sceny nachodzą na siebie o XFADE)."""
    starts, t = [], 0.0
    for sc in SCENES:
        starts.append(t)
        t += sc["dur"] - XFADE
    return starts, t + XFADE


def audio_filter(total):
    """Wzór dźwięku dla ffmpeg: niski "pomruk" pieca + uderzenia w kowadło na zmianach scen."""
    starts, _ = timeline()
    hits = [0.45] + [s + 0.12 for sc, s in zip(SCENES, starts) if sc["type"] in ("product", "title", "end")]
    # słowa "Ogień. Młot. Kowadło." — uderzenie na każde słowo
    for sc, s in zip(SCENES, starts):
        if sc["type"] == "words":
            per = sc["dur"] / len(sc["words"])
            hits += [s + k * per + 0.05 for k in range(len(sc["words"]))]
    hits = sorted(set(round(h, 3) for h in hits))

    # Partie (częstotliwości) "metalicznego" dźwięku kowadła — niewielkie przesunięcia
    # między uderzeniami, żeby nie brzmiało jak robot.
    terms = []
    for i, h in enumerate(hits):
        k = 1 + (i % 3) * 0.015
        # max(...,0): przed uderzeniem (t < h) wykładnik byłby dodatni -> exp() = nieskończoność,
        # a 0 * nieskończoność = NaN i koder AAC się wywraca. Dlatego "zamrażamy" czas na 0.
        u = f"max(t-{h},0)"
        terms.append(
            f"gt(t,{h})*exp(-7*{u})*(0.32*sin(2*PI*{1180*k:.0f}*{u})+0.22*sin(2*PI*{2690*k:.0f}*{u})"
            f"+0.12*sin(2*PI*{4120*k:.0f}*{u})+0.18*sin(2*PI*{590*k:.0f}*{u}))"
            f"+gt(t,{h})*exp(-40*{u})*0.25*sin(2*PI*90*{u})"  # "tąpnięcie" — niski, krótki dół
        )
    hammer = "+".join(terms)
    # Pomruk: dwa niskie tony + powolne falowanie głośności; wyciszenie na końcu
    drone = (f"(0.10*sin(2*PI*55*t)+0.07*sin(2*PI*82.5*t)+0.04*sin(2*PI*110*t))*(0.75+0.25*sin(2*PI*0.25*t))"
             f"*min(1,t/1.5)*min(1,({total}-t)/2)")
    return f"aevalsrc='0.8*({hammer})+{drone}':s=48000:d={total}"


def render(name, W, H):
    OUT.mkdir(parents=True, exist_ok=True)
    r = Renderer(W, H)
    starts, total = timeline()
    nframes = int(total * FPS)
    out = OUT / f"{name}.mp4"

    cmd = [
        FFMPEG, "-y", "-loglevel", "error",
        # wejście 0: surowe klatki RGB ze stdin
        "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
        # wejście 1: dźwięk — soundtrack z make_soundtrack.py, a jeśli go nie ma, prosty z aevalsrc
        *(["-i", str(OUT / "soundtrack.wav")] if (OUT / "soundtrack.wav").exists()
          else ["-f", "lavfi", "-i", audio_filter(total)]),
        # libx264 + yuv420p = odtworzy każdy telefon/przeglądarka; crf 21 = dobra jakość/rozmiar
        "-c:v", "libx264", "-preset", "slow", "-crf", "21", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "160k",
        # faststart: metadane na początku pliku -> film startuje zanim pobierze się cały
        "-movflags", "+faststart", "-shortest", str(out),
    ]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    poster_at = starts[2] + 1.2  # klatka na miniaturkę: pierwsza brama

    for fi in range(nframes):
        t = fi / FPS
        # Które sceny są widoczne w czasie t? (podczas przenikania — dwie)
        active = [(i, sc, t - s) for i, (sc, s) in enumerate(zip(SCENES, starts)) if 0 <= t - s < sc["dur"]]
        img = None
        for i, sc, lt in active:
            fr = r.frame(sc, lt, i)
            if img is None:
                img = fr
            else:
                img = Image.blend(img, fr, ease(lt / XFADE))  # przenikanie
        # Fade z czerni na starcie
        if t < 0.4:
            img = Image.blend(Image.new("RGB", (W, H), (0, 0, 0)), img, t / 0.4)
        proc.stdin.write(img.tobytes())
        if abs(t - poster_at) < 0.5 / FPS:
            img.save(OUT / f"{name}-poster.jpg", quality=85)
        if fi % FPS == 0:
            print(f"\r{name}: {fi / nframes * 100:5.1f}%", end="", flush=True)

    proc.stdin.close()
    proc.wait()
    print(f"\r{name}: gotowe -> {out.relative_to(ROOT)} ({out.stat().st_size / 1e6:.1f} MB, {total:.1f} s)")


if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else "all"
    if which in ("all", "wide"):
        render("promo", 1920, 1080)
    if which in ("all", "vertical"):
        render("promo-pion", 1080, 1920)

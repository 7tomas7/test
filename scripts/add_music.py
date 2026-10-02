"""
Podkłada prawdziwą muzykę (plik MP3) pod gotowy film — bez ponownego renderowania obrazu.

Muzyka w scripts/music/ — wyłącznie utwory na licencji CC0 (domena publiczna) z OpenGameArt.org:
  -> za darmo, komercyjnie (także w reklamach), BEZ obowiązku podpisywania autora.
  Źródła i linki: scripts/music/ZRODLA.txt

Jak wybrano fragment utworu (offset):
  Skrypt liczy głośność muzyki co 0,25 s i szuka miejsca, gdzie muzyka "wybucha"
  (największy skok głośności). Ustawiamy ten moment dokładnie na pierwsze cięcie
  w filmie (scena "Bramy wjazdowe", 6,1 s) — obraz i muzyka uderzają razem.
  Wystarczy podać utwór; offset policzy się sam (albo podaj go ręcznie).

Uruchomienie:
    python3 scripts/add_music.py scripts/music/Five_Armies.mp3            # do promo.mp4 i promo-pion.mp4
    python3 scripts/add_music.py utwor.mp3 --offset 8.25 --out-dir katalog # warianty do porównania
"""
import argparse
import subprocess
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
import make_video as mv  # noqa: E402  (oś czasu scen + ścieżka do ffmpeg)

SR = 22050  # do analizy wystarczy niższa jakość — liczymy tylko głośność


def find_offset(track, cut_at):
    """Zwraca sekundę utworu, od której trzeba zacząć, żeby "wybuch" muzyki wypadł na cut_at."""
    raw = subprocess.run([mv.FFMPEG, "-loglevel", "error", "-i", str(track), "-ac", "1", "-ar", str(SR),
                          "-f", "f32le", "-"], capture_output=True, check=True).stdout
    x = np.frombuffer(raw, np.float32)
    hop = SR // 4
    rms = np.array([np.sqrt((x[i:i + hop] ** 2).mean()) for i in range(0, len(x) - hop, hop)])
    db = 20 * np.log10(rms + 1e-9)  # decybele — tak ucho odbiera głośność (logarytmicznie)
    _, total = mv.timeline()
    L, J = int(total * 4), int(cut_at * 4)
    best_o, best_score = 0, -1e9
    for o in range(0, len(db) - L):
        jump = db[o + J:o + J + 12].mean() - db[o + J - 8:o + J].mean()  # 3 s po vs 2 s przed cięciem
        body = db[o + J:o + L].mean()  # i żeby reszta filmu nie była cicha
        score = jump + body * 0.3
        if score > best_score:
            best_o, best_score = o, score
    return best_o / 4


def track_length(track):
    """Gdzie KOŃCZY SIĘ muzyka — ostatnia sekunda, która nie jest ciszą.
    Wiele utworów ma na końcu kilka sekund ciszy/pogłosu; nie chcemy, żeby film kończył się na nich."""
    raw = subprocess.run([mv.FFMPEG, "-loglevel", "error", "-i", str(track), "-ac", "1", "-ar", str(SR),
                          "-f", "f32le", "-"], capture_output=True, check=True).stdout
    x = np.frombuffer(raw, np.float32)
    hop = SR // 10
    db = 20 * np.log10(np.array([np.sqrt((x[i:i + hop] ** 2).mean()) for i in range(0, len(x) - hop, hop)]) + 1e-9)
    loud = np.where(db > db.max() - 24)[0]  # "głośne" = najwyżej 24 dB ciszej niż szczyt
    return (loud[-1] + 1) * hop / SR


def mux(video, track, offset, out, fade_out=2.5):
    _, total = mv.timeline()
    af = ",".join([
        "afade=t=in:d=0.3",                                        # łagodny start (bez "pyknięcia")
        *([f"afade=t=out:st={total - fade_out:.2f}:d={fade_out}"] if fade_out else []),  # wyciszenie na końcu
        "loudnorm=I=-14:TP=-1:LRA=11",                             # standard głośności YouTube/IG/FB
    ])
    subprocess.run([
        mv.FFMPEG, "-y", "-loglevel", "error",
        "-i", str(video),
        "-ss", f"{offset:.2f}", "-i", str(track),  # -ss przed -i = przeskocz w utworze do offsetu
        "-map", "0:v", "-map", "1:a", "-c:v", "copy",
        "-af", af, "-ar", "48000", "-c:a", "aac", "-b:a", "192k",
        "-t", f"{total:.2f}", "-movflags", "+faststart", str(out),
    ], check=True)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("track")
    ap.add_argument("--offset", type=float, help="sekunda utworu, od której startuje muzyka (domyślnie: automatycznie)")
    ap.add_argument("--align-end", action="store_true",
                    help="koniec utworu = koniec filmu (dla utworów z wielkim finałem, np. Grieg)")
    ap.add_argument("--out-dir", type=Path, help="zapisz kopie tutaj zamiast podmieniać filmy w assets/video")
    a = ap.parse_args()

    starts, _ = mv.timeline()
    first_cut = next(s for s, sc in zip(starts, mv.SCENES) if sc["type"] == "product")
    _, total = mv.timeline()
    if a.align_end:
        offset = track_length(a.track) - total  # ostatni akord utworu wypada na ostatniej klatce
    else:
        offset = a.offset if a.offset is not None else find_offset(a.track, first_cut)
    print(f"{Path(a.track).name}: start od {offset:.2f} s utworu")

    for name in ("promo.mp4", "promo-pion.mp4"):
        src = mv.OUT / name
        if a.out_dir:
            a.out_dir.mkdir(parents=True, exist_ok=True)
            out = a.out_dir / f"{Path(a.track).stem}-{name}"
        else:
            out = src.with_suffix(".tmp.mp4")
        mux(src, a.track, offset, out, fade_out=0.4 if a.align_end else 2.5)
        if not a.out_dir:
            out.replace(src)
        print(f"  -> {out if a.out_dir else src}")

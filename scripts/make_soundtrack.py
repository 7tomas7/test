"""
Soundtrack do filmu reklamowego — syntezator "kinowej kuźni".

Wszystkie dźwięki są LICZONE z matematyki (numpy), nie ma tu żadnych sampli,
więc nie ma też problemu z licencją. Dźwięk to tablica liczb od -1 do 1,
48 000 liczb na sekundę (48 kHz). Każdy instrument to funkcja, która zwraca
taką tablicę, a my "naklejamy" ją na oś czasu w odpowiednim miejscu.

Warstwy (jak w prawdziwej produkcji muzycznej):
  - IMPACT / BRAAM  — wielkie kinowe uderzenia na logo i na końcu (jak w trailerach)
  - KOWADŁO         — metaliczne dzwonienie; tony "nieharmoniczne" (nie są wielokrotnościami
                      jednej częstotliwości), dlatego brzmi jak metal, a nie jak instrument
  - BĘBNY           — stopa (kick) w stylu taiko + "młotek" zamiast werbla
  - BAS + PAD       — progresja akordów d-moll: Dm – B – F – C (smutno-epicka)
  - WHOOSH / RISER  — szum, który narasta przed cięciem (buduje napięcie)
  - OGIEŃ           — trzaski i szum paleniska w tle
  - SIDECHAIN       — muzyka "oddycha" (ścisza się) przy każdym uderzeniu stopy;
                      efekt pompowania znany z muzyki elektronicznej
  - POGŁOS (reverb) — splot (konwolucja) z wygenerowaną "odpowiedzią hali"

Timing jest pobierany z make_video.py (funkcja timeline()), więc gdy zmienisz
długość scen w filmie, muzyka sama się dopasuje.

Uruchomienie:
    python3 scripts/make_soundtrack.py      # tworzy assets/video/soundtrack.wav
                                            # i podmienia dźwięk w obu filmach
"""
import subprocess
import sys
import wave
from pathlib import Path

import numpy as np
from scipy import signal

sys.path.insert(0, str(Path(__file__).parent))
import make_video as mv  # noqa: E402  (bierzemy oś czasu scen i ścieżkę do ffmpeg)

SR = 48_000
RNG = np.random.default_rng(1997)  # stałe ziarno = przy każdym uruchomieniu ten sam dźwięk
OUT = mv.OUT


# ---------------------------------------------------------------------------
# Podstawowe klocki
# ---------------------------------------------------------------------------
def t_axis(dur):
    return np.arange(int(dur * SR)) / SR


def env_exp(dur, decay, attack=0.002):
    """Obwiednia: szybki atak, wykładnicze wygasanie. decay = ile sekund do ~37% głośności."""
    t = t_axis(dur)
    return np.minimum(1, t / attack) * np.exp(-t / decay)


def noise(dur):
    return RNG.standard_normal(int(dur * SR))


def bandpass(x, lo, hi, order=4):
    sos = signal.butter(order, [lo, hi], btype="band", fs=SR, output="sos")
    return signal.sosfilt(sos, x)


def lowpass(x, fc, order=4):
    sos = signal.butter(order, fc, btype="low", fs=SR, output="sos")
    return signal.sosfilt(sos, x)


def highpass(x, fc, order=4):
    sos = signal.butter(order, fc, btype="high", fs=SR, output="sos")
    return signal.sosfilt(sos, x)


def sweep_filter(x, f_start, f_end, kind="low", block=2048):
    """Filtr, którego częstotliwość zmienia się w czasie (np. "otwieranie" brzmienia).
    Robimy to blokami z nakładaniem (overlap-add + okno Hanna), żeby nie było trzasków."""
    n = len(x)
    out = np.zeros(n + block)
    win = np.hanning(block)
    hop = block // 2
    for start in range(0, n, hop):
        p = start / max(1, n - 1)
        fc = f_start * (f_end / f_start) ** p  # zmiana logarytmiczna = brzmi naturalnie dla ucha
        seg = np.zeros(block)
        chunk = x[start:start + block]
        seg[:len(chunk)] = chunk
        if kind == "band":
            seg = bandpass(seg, fc * 0.7, min(fc * 1.4, SR / 2 - 100), 2)
        else:
            seg = lowpass(seg, min(fc, SR / 2 - 100), 2)
        out[start:start + block] += seg * win
    return out[:n]


def note(name):
    """'D2' -> częstotliwość w Hz. A4 = 440 Hz, każdy półton to mnożnik 2^(1/12)."""
    names = {"C": -9, "C#": -8, "Db": -8, "D": -7, "Eb": -6, "E": -5, "F": -4,
             "F#": -3, "G": -2, "Ab": -1, "A": 0, "Bb": 1, "B": 2}
    pitch, octave = name[:-1], int(name[-1])
    return 440.0 * 2 ** ((names[pitch] + (octave - 4) * 12) / 12)


def saw(freq, dur, detune_cents=(0,)):
    """Piła (sawtooth) — jasna fala, z której filtrem "rzeźbi się" basy i pady.
    Kilka lekko rozstrojonych pił = efekt "supersaw", szerokie brzmienie."""
    t = t_axis(dur)
    out = np.zeros_like(t)
    for c in detune_cents:
        f = freq * 2 ** (c / 1200)
        out += signal.sawtooth(2 * np.pi * f * t + RNG.uniform(0, 6.28))
    return out / len(detune_cents)


# ---------------------------------------------------------------------------
# Instrumenty
# ---------------------------------------------------------------------------
def anvil(strength=1.0, f0=None):
    """Uderzenie młota w kowadło."""
    f0 = f0 or RNG.uniform(880, 960)
    dur = 2.6
    t = t_axis(dur)
    # Proporcje częstotliwości metalowego klocka (z pomiarów drgań płyt/prętów — nieharmoniczne)
    ratios = [1.0, 2.32, 2.76, 4.07, 5.40, 6.85, 8.93]
    decays = [1.1, 0.75, 0.9, 0.45, 0.35, 0.22, 0.15]
    amps = [0.55, 0.30, 0.42, 0.22, 0.18, 0.12, 0.08]
    ring = np.zeros_like(t)
    for r, d, a in zip(ratios, decays, amps):
        f = f0 * r
        if f > 18000:
            continue
        # dwa prawie identyczne tony = "dudnienie" (beating), jak w prawdziwym metalu
        ring += a * np.exp(-t / d) * (np.sin(2 * np.pi * f * t) + 0.6 * np.sin(2 * np.pi * f * 1.0025 * t + 1))
    # Klik uderzenia: krótki, jasny szum
    click = highpass(noise(dur), 2500) * env_exp(dur, 0.006) * 1.4
    # "Tąpnięcie" — masa kowadła i stołu
    thump = np.sin(2 * np.pi * (180 * np.exp(-t * 25) + 70) * t) * env_exp(dur, 0.06) * 0.9
    return (ring * 0.55 + click + thump) * strength


def kick(strength=1.0):
    """Stopa w stylu taiko: sinus, którego wysokość szybko opada (150 Hz -> 45 Hz)."""
    dur = 0.9
    t = t_axis(dur)
    freq = 45 + 120 * np.exp(-t * 28)
    phase = 2 * np.pi * np.cumsum(freq) / SR  # całka z częstotliwości = faza (płynne opadanie tonu)
    body = np.sin(phase) * env_exp(dur, 0.32, 0.001)
    skin = bandpass(noise(dur), 200, 2000) * env_exp(dur, 0.03) * 0.5
    return np.tanh((body + skin) * 1.6) * strength  # tanh = nasycenie, "grubsza" stopa


def hammer_tick(strength=1.0):
    """Lekkie stuknięcie młotka (zamiast hi-hatu)."""
    dur = 0.35
    t = t_axis(dur)
    f = RNG.uniform(2900, 3300)
    tone = (np.sin(2 * np.pi * f * t) + 0.5 * np.sin(2 * np.pi * f * 1.51 * t)) * np.exp(-t / 0.05)
    clk = highpass(noise(dur), 5000) * env_exp(dur, 0.01)
    return (tone * 0.4 + clk * 0.5) * strength


def impact(strength=1.0, dur=5.0):
    """Kinowy IMPACT: głęboki boom + uderzenie szumu + dzwonienie kowadła."""
    t = t_axis(dur)
    freq = 32 + 90 * np.exp(-t * 9)
    sub = np.sin(2 * np.pi * np.cumsum(freq) / SR) * env_exp(dur, 1.4, 0.002)
    crack = lowpass(noise(dur), 6000) * env_exp(dur, 0.12) * 0.9
    body = bandpass(noise(dur), 60, 400) * env_exp(dur, 0.5) * 0.8
    out = np.tanh(sub * 2.2) * 0.9 + crack + body
    out[: len(anvil())] += anvil(1.3, 820)[: len(out)]
    return out * strength


def braam(chord, dur=4.5, strength=1.0):
    """BRAAM (dźwięk z trailerów, np. "Incepcja"): niskie, rozstrojone piły,
    filtr gwałtownie się otwiera, potem powoli zamyka."""
    out = np.zeros(int(dur * SR))
    for n in chord:
        out += saw(note(n), dur, detune_cents=(-14, -5, 0, 6, 15))
    out = sweep_filter(out, 2400, 140, "low")
    e = np.minimum(1, t_axis(dur) / 0.04) * np.exp(-t_axis(dur) / 1.6)
    return np.tanh(out * 1.8 * e) * strength


def whoosh(dur=0.9, up=True, strength=1.0):
    """Przejście: szum przesuwający się w górę (lub w dół) pasma, głośniejący do końca."""
    x = noise(dur)
    x = sweep_filter(x, 300, 6000, "band") if up else sweep_filter(x, 6000, 300, "band")
    t = t_axis(dur) / dur
    e = (t ** 2.2) if up else (1 - t) ** 1.5
    return x * e * 2.2 * strength


def riser(dur=2.5, strength=1.0):
    """Riser: narastające napięcie — szum + rosnący ton (shepard-like)."""
    t = t_axis(dur)
    p = t / dur
    nz = sweep_filter(noise(dur), 200, 9000, "band") * p ** 2 * 1.8
    f = 110 * 2 ** (p * 3)  # trzy oktawy w górę
    tone = np.sin(2 * np.pi * np.cumsum(f) / SR) * p ** 3 * 0.35
    return (nz + tone) * strength


def fire(dur):
    """Ogień w palenisku: niski szum + losowe trzaski."""
    base = lowpass(noise(dur), 900) * 0.25
    base *= 0.7 + 0.3 * lowpass(np.abs(noise(dur)), 3)  # powolne "falowanie" płomienia
    out = base
    n_cracks = int(dur * 9)
    for _ in range(n_cracks):
        pos = RNG.integers(0, len(out) - 4000)
        c = highpass(noise(0.03), 1500) * env_exp(0.03, RNG.uniform(0.002, 0.008)) * RNG.uniform(0.2, 1.0)
        out[pos:pos + len(c)] += c
    return out


def pad(chord, dur, strength=1.0):
    """Pad: miękkie tło harmoniczne (akord), wolny atak i wybrzmienie."""
    out = np.zeros(int(dur * SR))
    for n in chord:
        out += saw(note(n), dur, detune_cents=(-9, 0, 8))
    out = lowpass(out, 1400, 2)
    t = t_axis(dur)
    e = np.minimum(1, t / 0.35) * np.minimum(1, (dur - t) / 0.3)
    return out * e * 0.18 * strength


def bass_pulse(root, dur, beat):
    """Pulsujący bas ósemkami: piła przez filtr dolnoprzepustowy, każdy ton ma "pstryk" filtra."""
    out = np.zeros(int(dur * SR))
    step = beat / 2
    k = 0
    while k * step < dur - 0.01:
        L = step * 0.92
        tone = saw(note(root), L, detune_cents=(-6, 6)) + 0.6 * np.sin(2 * np.pi * note(root) / 2 * t_axis(L))
        tone = sweep_filter(tone, 1100, 160, "low", block=1024)
        e = np.minimum(1, t_axis(L) / 0.004) * np.exp(-t_axis(L) / 0.18)
        s = int(k * step * SR)
        seg = tone * e
        out[s:s + len(seg)] += seg[: len(out) - s]
        k += 1
    return out * 0.55


# ---------------------------------------------------------------------------
# Miks
# ---------------------------------------------------------------------------
class Bus:
    """Szyna miksera: stereo bufor + osobny bufor "wysyłki" na pogłos."""

    def __init__(self, dur):
        self.n = int(dur * SR)
        self.dry = np.zeros((2, self.n))
        self.verb = np.zeros((2, self.n))

    def add(self, x, at, gain=1.0, pan=0.0, rev=0.0):
        """Wklej dźwięk x w czasie at [s]. pan: -1 lewo .. +1 prawo. rev: ile do pogłosu."""
        s = int(at * SR)
        if s >= self.n:
            return
        x = x[: self.n - s] * gain
        # Panorama "equal power" — przy przesuwaniu na boki suma głośności się nie zmienia
        l, r = np.cos((pan + 1) * np.pi / 4), np.sin((pan + 1) * np.pi / 4)
        self.dry[0, s:s + len(x)] += x * l
        self.dry[1, s:s + len(x)] += x * r
        if rev:
            self.verb[0, s:s + len(x)] += x * l * rev
            self.verb[1, s:s + len(x)] += x * r * rev


def reverb_ir(dur=3.2):
    """Odpowiedź impulsowa "kamiennej hali": wygasający szum, osobny dla L i P (szerokość stereo),
    przyciemniony (wysokie tony giną szybciej w prawdziwych pomieszczeniach)."""
    t = t_axis(dur)
    irs = []
    for _ in range(2):
        n = noise(dur) * np.exp(-t / 0.75)
        n = lowpass(n, 5500, 2)
        n[: int(0.012 * SR)] = 0  # pre-delay 12 ms — pogłos startuje chwilę po dźwięku (czytelność)
        irs.append(n / np.sqrt(np.sum(n ** 2)))
    return irs


def build(total):
    starts, _ = mv.timeline()
    sc = {i: (s, mv.SCENES[i]) for i, s in enumerate(starts)}
    prod = [s for s, x in sc.values() if x["type"] == "product"]
    words_t = next(s for s, x in sc.values() if x["type"] == "words")
    titles = [s for s, x in sc.values() if x["type"] == "title"]
    end_t = next(s for s, x in sc.values() if x["type"] == "end")
    scene_len = prod[1] - prod[0]
    beat = scene_len / 4  # 4 uderzenia na scenę -> tempo wynika z montażu (~117 BPM)

    music = Bus(total)  # bas + pad (będą "pompowane" przez sidechain)
    drums = Bus(total)
    fx = Bus(total)

    # --- Ogień przez cały film (cicho), mocniej na intro i słowach ---
    f = fire(total)
    env = np.interp(t_axis(total), [0, 3, 6, 22, 23, 25.5, total], [0.9, 0.6, 0.25, 0.25, 0.8, 0.3, 0.4])
    fx.add(f * env, 0, 0.55, rev=0.15)

    # --- INTRO: riser -> wielkie uderzenie na logo ---
    fx.add(whoosh(0.45, True, 0.7), 0.0)
    fx.add(impact(1.0), 0.45, 0.95, rev=0.6)
    fx.add(braam(["D1", "A1", "D2"], 4.5, 0.75), 0.45, 0.8, rev=0.35)
    # drugi akcent na tytule "Kształtujemy formy z metalu"
    fx.add(whoosh(0.6, True, 0.6), titles[0] - 0.48, pan=-0.3)
    fx.add(anvil(1.0), titles[0] + 0.12, 0.9, pan=0.15, rev=0.5)
    fx.add(braam(["Bb0", "F1", "Bb1"], 3.0, 0.5), titles[0] + 0.12, 0.6, rev=0.3)
    # "bicie serca" — miękka stopa co ćwierćnutę pod tytułem, coraz głośniej
    k = 0
    while titles[0] + 0.12 + k * beat < prod[0] - 0.05:
        drums.add(kick(0.5 + 0.08 * k), titles[0] + 0.12 + k * beat, 0.8)
        k += 1
    fx.add(riser(prod[0] - titles[0] - 0.6, 0.55), titles[0] + 0.6, rev=0.25)

    # --- GŁÓWNA CZĘŚĆ: 8 scen produktów, rytm + akordy ---
    prog = [("D", ["D3", "F3", "A3", "D4"]), ("Bb", ["Bb2", "D3", "F3", "Bb3"]),
            ("F", ["F3", "A3", "C4", "F4"]), ("C", ["C3", "E3", "G3", "C4"])]
    for i, s in enumerate(prod):
        root, chord = prog[i % 4]
        music.add(pad(chord, scene_len + 0.1, 1.0 + 0.1 * (i // 4)), s, pan=0, rev=0.4)
        music.add(bass_pulse(root + "1", scene_len, beat), s, 0.9)
        # perkusja: stopa na 1 i 3, kowadło na 2 i 4, młotek na ósemkach
        for b in range(4):
            tb = s + b * beat
            if b in (0, 2):
                drums.add(kick(1.0), tb, 1.0)
            if b in (1, 3):
                drums.add(anvil(0.55), tb, 0.55, pan=RNG.uniform(-0.35, 0.35), rev=0.3)
            drums.add(hammer_tick(0.5 if b % 2 else 0.35), tb + beat / 2, 0.5, pan=0.4 * (-1) ** b, rev=0.1)
            if i >= 4:  # druga połowa = więcej energii: dodatkowe szesnastki
                drums.add(hammer_tick(0.25), tb + beat * 0.75, 0.35, pan=-0.5, rev=0.1)
        # akcent na cięciu: mocne kowadło + whoosh przed cięciem
        drums.add(anvil(1.0), s + 0.02, 0.8, pan=0.2 if i % 2 else -0.2, rev=0.45)
        if i > 0:
            fx.add(whoosh(0.5, True, 0.5), s - 0.45, pan=-0.4 if i % 2 else 0.4)
    # riser przed "Ogień. Młot. Kowadło."
    fx.add(riser(scene_len, 0.7), words_t - scene_len, rev=0.3)

    # --- SŁOWA: cisza + trzy potężne uderzenia ---
    per = 3.0 / 3
    for k in range(3):
        tw = words_t + k * per + 0.05
        fx.add(impact(0.55 + 0.08 * k, 3.0), tw, 0.7, rev=0.45)
        fx.add(anvil(1.1, 760 + 60 * k), tw, 0.75, pan=(-0.3, 0.3, 0)[k], rev=0.6)
        drums.add(kick(1.0), tw, 1.0)
    fx.add(fire(1.2) * np.linspace(0, 1.4, int(1.2 * SR)), words_t - 0.3, 0.9, rev=0.3)  # buchnięcie ognia

    # --- TRWAŁOŚĆ: powrót rytmu w połowie tempa + pad ---
    t2 = titles[1]
    fx.add(anvil(1.0), t2 + 0.12, 0.85, rev=0.5)
    music.add(pad(["D3", "F3", "A3", "C4"], end_t - t2 + 0.3, 1.2), t2, rev=0.5)
    music.add(bass_pulse("D1", end_t - t2, beat * 2), t2, 0.8)
    b = 0
    while t2 + 0.12 + b * beat < end_t - 0.1:
        tb = t2 + 0.12 + b * beat
        if b % 2 == 0:
            drums.add(kick(0.9), tb, 0.9)
        else:
            drums.add(anvil(0.45), tb, 0.45, pan=0.3 * (-1) ** b, rev=0.35)
        b += 1
    fx.add(riser(end_t - t2 - 0.6, 0.8), t2 + 0.6, rev=0.3)

    # --- FINAŁ: największe uderzenie + braam + długi pogłos ---
    fx.add(impact(1.1, total - end_t), end_t, 1.0, rev=0.75)
    fx.add(braam(["D1", "A1", "D2", "F2"], total - end_t, 0.9), end_t, 0.9, rev=0.4)
    music.add(pad(["D3", "A3", "D4", "F4"], total - end_t, 1.3) * np.linspace(1, 0, int((total - end_t) * SR)), end_t, rev=0.6)

    # --- SIDECHAIN: muzyka cichnie przy każdym kicku (efekt "oddychania") ---
    kick_env = np.abs(drums.dry[0] + drums.dry[1])
    kick_env = lowpass(kick_env, 8, 1)          # wygładzona obwiednia perkusji
    kick_env = kick_env / (kick_env.max() + 1e-9)
    duck = 1 - 0.55 * np.clip(kick_env * 2.5, 0, 1)
    music.dry *= duck
    music.verb *= duck

    # --- POGŁOS: wspólny dla wszystkich (jak jedna hala) ---
    ir = reverb_ir()
    wet_in = music.verb + drums.verb + fx.verb
    wet = np.stack([signal.fftconvolve(wet_in[c], ir[c])[: music.n] for c in range(2)])

    mix = music.dry * 0.9 + drums.dry * 0.85 + fx.dry * 0.9 + wet * 0.55
    # Usuwamy niesłyszalny dół (<28 Hz) — tylko zjada głośność
    mix = np.stack([highpass(mix[c], 28, 2) for c in range(2)])
    # Fade in/out
    fade = np.ones(music.n)
    fade[: int(0.05 * SR)] = np.linspace(0, 1, int(0.05 * SR))
    fade[-int(0.6 * SR):] = np.linspace(1, 0, int(0.6 * SR))
    mix *= fade
    # "Mastering" krok 1: KOMPRESOR. Ścisza to, co przekracza próg (threshold), w proporcji
    # ratio:1. Głośne uderzenia przestają dominować, a cała muzyka może być głośniejsza.
    mix = compress(mix, threshold=0.18, ratio=4.0)
    # krok 2: miękkie nasycenie (tanh "skleja" miks) + normalizacja szczytu
    mix = mix / np.max(np.abs(mix)) * 1.4
    mix = np.tanh(mix)
    mix = mix / np.max(np.abs(mix)) * 0.89  # ok. -1 dBFS
    return mix


def compress(stereo, threshold, ratio, attack_hz=60):
    """Kompresor: liczymy obwiednię (jak głośno jest "teraz"), a gdzie przekracza próg —
    zmniejszamy wzmocnienie. Obie strony stereo dostają to samo wzmocnienie (stereo-link),
    żeby obraz stereo się nie przesuwał."""
    level = lowpass(np.max(np.abs(stereo), axis=0), attack_hz, 1)
    level = np.maximum(level, 1e-6)
    over = level > threshold
    gain = np.ones_like(level)
    gain[over] = (threshold + (level[over] - threshold) / ratio) / level[over]
    return stereo * gain


def save_wav(path, stereo):
    data = (stereo.T * 32767).astype("<i2")
    with wave.open(str(path), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(data.tobytes())


def remux(video, audio):
    """Podmienia ścieżkę dźwiękową w gotowym filmie BEZ ponownego renderowania obrazu
    (-c:v copy = obraz kopiowany 1:1, trwa sekundę). loudnorm ustawia głośność na -14 LUFS,
    czyli standard YouTube/Instagrama/Facebooka — platformy i tak by ściszyły głośniejsze."""
    tmp = video.with_suffix(".tmp.mp4")
    subprocess.run([
        mv.FFMPEG, "-y", "-loglevel", "error", "-i", str(video), "-i", str(audio),
        "-map", "0:v", "-map", "1:a", "-c:v", "copy",
        "-af", "loudnorm=I=-14:TP=-1:LRA=11", "-ar", "48000",
        "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", "-shortest", str(tmp),
    ], check=True)
    tmp.replace(video)


if __name__ == "__main__":
    _, total = mv.timeline()
    print("Synteza…")
    mix = build(total)
    wav = OUT / "soundtrack.wav"
    save_wav(wav, mix)
    print(f"-> {wav.relative_to(mv.ROOT)}")
    for name in ("promo.mp4", "promo-pion.mp4"):
        v = OUT / name
        if v.exists():
            remux(v, wav)
            print(f"-> dźwięk podmieniony w {name}")

/* =====================================================================
   Kowalstwo Artystyczne — interakcje strony
   ---------------------------------------------------------------------
   Czysty JavaScript (bez jQuery / frameworków). Każda funkcjonalność to
   osobna funkcja init…(), wywoływana na dole pliku. Dzięki temu łatwo
   coś wyłączyć albo przenieść na inną podstronę.

   Elementy szukamy po atrybutach data-* (np. [data-gallery]), a NIE po
   klasach CSS. Klasy są od wyglądu, data-* od zachowania — grafik może
   zmienić nazwę klasy i nic się nie zepsuje.
   ===================================================================== */

const $ = (sel, root = document) => root.querySelector(sel);
const $$ = (sel, root = document) => [...root.querySelectorAll(sel)];

// Czy użytkownik ma w systemie włączone "ogranicz ruch"? Wtedy pomijamy animacje JS.
const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

/* ---------- Nagłówek: tło po przewinięciu + przycisk "zadzwoń" ---------- */
function initHeader() {
  const header = $("[data-header]");
  const fab = $(".call-fab");
  // passive: true = obiecujemy przeglądarce, że nie zablokujemy przewijania,
  // więc może przewijać płynnie, nie czekając na nasz kod.
  const onScroll = () => {
    const y = window.scrollY;
    header.classList.toggle("is-scrolled", y > 40);
    fab?.classList.toggle("is-visible", y > window.innerHeight * 0.8);
  };
  window.addEventListener("scroll", onScroll, { passive: true });
  onScroll();
}

/* ---------- Menu mobilne ---------- */
function initNav() {
  const toggle = $("[data-nav-toggle]");
  const nav = $("[data-nav]");

  const setOpen = (open) => {
    toggle.setAttribute("aria-expanded", String(open));
    nav.classList.toggle("is-open", open);
    // Blokujemy przewijanie strony pod otwartym menu
    document.body.style.overflow = open ? "hidden" : "";
  };

  toggle.addEventListener("click", () => setOpen(toggle.getAttribute("aria-expanded") !== "true"));
  // Kliknięcie w link zamyka menu (inaczej zostałoby otwarte po przejściu do sekcji)
  nav.addEventListener("click", (e) => { if (e.target.closest("a")) setOpen(false); });
  document.addEventListener("keydown", (e) => { if (e.key === "Escape") setOpen(false); });

  // Podświetlanie aktywnej sekcji w menu ("scroll spy")
  const links = $$(".site-nav__list a");
  const sections = links.map((a) => $(a.getAttribute("href"))).filter(Boolean);
  const spy = new IntersectionObserver((entries) => {
    entries.forEach((entry) => {
      if (!entry.isIntersecting) return;
      links.forEach((a) => a.classList.toggle("is-active", a.getAttribute("href") === "#" + entry.target.id));
    });
  }, { rootMargin: "-45% 0px -50% 0px" }); // "aktywna" = sekcja przecina środek ekranu
  sections.forEach((s) => spy.observe(s));
}

/* ---------- Hero: pokaz slajdów ---------- */
function initHeroSlides() {
  const slides = $$("[data-hero-slides] img");
  if (slides.length < 2 || reducedMotion) return;

  // Leniwe ładowanie: pozostałe slajdy pobieramy dopiero po załadowaniu strony,
  // żeby nie konkurowały o łącze z pierwszym zdjęciem i fontami.
  window.addEventListener("load", () => slides.forEach((img) => {
    if (img.dataset.src) img.src = img.dataset.src;
  }));

  let i = 0;
  setInterval(() => {
    // Nie przełączaj, gdy karta przeglądarki jest w tle (oszczędzamy baterię)
    if (document.hidden) return;
    slides[i].classList.remove("is-active");
    i = (i + 1) % slides.length;
    slides[i].classList.add("is-active");
  }, 6000);
}

/* ---------- Hero: iskry z kuźni (canvas) ----------
   Rysujemy ~70 cząsteczek unoszących się w górę jak iskry z paleniska.
   requestAnimationFrame = przeglądarka woła nas przed każdą klatką (60 fps),
   a w nieaktywnej karcie automatycznie się zatrzymuje. */
function initSparks() {
  const canvas = $("[data-sparks]");
  if (!canvas || reducedMotion) return;
  const ctx = canvas.getContext("2d");
  let w, h, dpr, sparks = [], running = true;

  const resize = () => {
    // devicePixelRatio: na ekranach Retina rysujemy w wyższej rozdzielczości, żeby było ostro
    dpr = Math.min(window.devicePixelRatio || 1, 2);
    w = canvas.clientWidth; h = canvas.clientHeight;
    canvas.width = w * dpr; canvas.height = h * dpr;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  };

  const spawn = () => ({
    x: Math.random() * w * 0.7,            // więcej iskier po lewej, gdzie jest "żar" w gradiencie
    y: h + Math.random() * 40,
    vx: (Math.random() - 0.3) * 0.6,
    vy: -(0.6 + Math.random() * 1.8),
    r: 0.6 + Math.random() * 1.8,
    life: 0,
    max: 140 + Math.random() * 220,
    hue: 20 + Math.random() * 25,          // od pomarańczu do żółci
  });

  const count = window.innerWidth < 640 ? 35 : 70; // mniej na telefonie = mniej pracy procesora
  const frame = () => {
    if (!running) return;
    ctx.clearRect(0, 0, w, h);
    while (sparks.length < count) sparks.push(spawn());
    sparks = sparks.filter((s) => s.life < s.max && s.y > -10);
    for (const s of sparks) {
      s.life++;
      s.x += s.vx + Math.sin((s.life + s.max) * 0.05) * 0.35; // lekkie falowanie
      s.y += s.vy;
      const a = 1 - s.life / s.max;
      ctx.beginPath();
      ctx.fillStyle = `hsla(${s.hue}, 100%, ${60 + a * 20}%, ${a})`;
      ctx.shadowBlur = 12; ctx.shadowColor = `hsla(${s.hue}, 100%, 55%, ${a})`;
      ctx.arc(s.x, s.y, s.r, 0, Math.PI * 2);
      ctx.fill();
    }
    requestAnimationFrame(frame);
  };

  // Gdy hero zniknie z ekranu — zatrzymujemy animację (nie marnujemy CPU)
  new IntersectionObserver(([entry]) => {
    const was = running;
    running = entry.isIntersecting;
    if (running && !was) requestAnimationFrame(frame);
  }).observe(canvas);

  window.addEventListener("resize", resize);
  resize();
  requestAnimationFrame(frame);
}

/* ---------- Animacje wejścia elementów ---------- */
function initReveal() {
  const items = $$(".reveal");
  // Elementy w tym samym rodzicu dostają rosnące opóźnienie = efekt "kaskady"
  const groups = new Map();
  items.forEach((el) => {
    const n = groups.get(el.parentElement) ?? 0;
    el.style.setProperty("--d", `${Math.min(n * 0.08, 0.5)}s`);
    groups.set(el.parentElement, n + 1);
  });

  const io = new IntersectionObserver((entries) => {
    entries.forEach((entry) => {
      if (!entry.isIntersecting) return;
      entry.target.classList.add("is-in");
      io.unobserve(entry.target); // animujemy tylko raz
    });
  }, { threshold: 0.12, rootMargin: "0px 0px -40px 0px" });
  items.forEach((el) => io.observe(el));
}

/* ---------- Liczniki (0 → 1997) ---------- */
function initCounters() {
  const els = $$("[data-count]");
  const animate = (el) => {
    const target = +el.dataset.count;
    if (reducedMotion) { el.textContent = target; return; }
    // Rok "1997" liczymy od 1900, żeby nie było absurdalnego "0, 54, 312…"
    const from = target > 1000 ? 1900 : 0;
    const dur = 1800, t0 = performance.now();
    const tick = (now) => {
      const p = Math.min((now - t0) / dur, 1);
      const eased = 1 - Math.pow(1 - p, 3); // easeOutCubic: szybko na starcie, wolno na końcu
      el.textContent = Math.round(from + (target - from) * eased);
      if (p < 1) requestAnimationFrame(tick);
    };
    requestAnimationFrame(tick);
  };
  const io = new IntersectionObserver((entries) => entries.forEach((e) => {
    if (e.isIntersecting) { animate(e.target); io.unobserve(e.target); }
  }), { threshold: 0.6 });
  els.forEach((el) => io.observe(el));
}

/* ---------- Galeria + filtry + lightbox ---------- */
function initGallery() {
  const data = window.GALLERY;
  const list = $("[data-gallery]");
  if (!data || !list) return;

  const BASE = "assets/img/gallery/";
  const PAGE = 24; // ile zdjęć dokładamy na raz — 468 naraz to za dużo dla telefonu
  const labels = Object.fromEntries(data.categories.map((c) => [c.slug, c.label]));
  const countBy = data.items.reduce((acc, it) => ((acc[it.c] = (acc[it.c] || 0) + 1), acc), {});

  const filtersEl = $("[data-filters]");
  const moreBtn = $("[data-gallery-more]");
  const status = $("[data-gallery-status]");
  let current = "all";
  let filtered = [];
  let shown = 0;

  // Liczba zdjęć na kafelkach oferty
  $$("[data-count-cat]").forEach((el) => {
    const n = countBy[el.dataset.countCat] || 0;
    el.textContent = `${n} realizacji`;
  });

  // Przyciski filtrów (generowane z danych — nowa kategoria pojawi się sama)
  const chips = [{ slug: "all", label: "Wszystkie" }, ...data.categories].map((c) => {
    const b = document.createElement("button");
    b.type = "button";
    b.className = "chip";
    b.dataset.slug = c.slug;
    b.setAttribute("aria-pressed", String(c.slug === "all"));
    const n = c.slug === "all" ? data.items.length : countBy[c.slug];
    b.innerHTML = `${c.label}<sup>${n}</sup>`;
    b.addEventListener("click", () => setFilter(c.slug));
    filtersEl.append(b);
    return b;
  });

  function renderMore() {
    const frag = document.createDocumentFragment(); // jedna operacja na DOM zamiast 24 = szybciej
    filtered.slice(shown, shown + PAGE).forEach((it, k) => {
      const idx = shown + k;
      const li = document.createElement("li");
      li.style.animationDelay = `${(k % PAGE) * 30}ms`;
      li.innerHTML = `
        <button type="button" aria-label="Powiększ: ${labels[it.c]}, zdjęcie ${idx + 1}">
          <img src="${BASE}thumb/${it.f}" width="${it.w}" height="${it.h}" alt="${labels[it.c]} — realizacja Kowalstwa Artystycznego Marek Mida" loading="lazy" decoding="async">
        </button>`;
      const img = $("img", li);
      // Płynne pojawienie się po załadowaniu (zamiast "wyskakiwania" obrazka)
      if (img.complete) img.classList.add("is-loaded");
      else img.addEventListener("load", () => img.classList.add("is-loaded"), { once: true });
      $("button", li).addEventListener("click", () => openLightbox(idx));
      frag.append(li);
    });
    list.append(frag);
    shown = Math.min(shown + PAGE, filtered.length);
    moreBtn.parentElement.hidden = shown >= filtered.length;
    moreBtn.textContent = `Pokaż więcej (${filtered.length - shown})`;
  }

  // "Wszystkie" = przeplatamy kategorie (brama, ogrodzenie, balustrada, furtka, …),
  // żeby pierwszy ekran galerii pokazywał przekrój oferty, a nie 88 bram z rzędu.
  const byCat = data.categories.map((c) => data.items.filter((it) => it.c === c.slug));
  const mixed = [];
  for (let i = 0; mixed.length < data.items.length; i++) byCat.forEach((arr) => arr[i] && mixed.push(arr[i]));

  function setFilter(slug) {
    current = slug;
    chips.forEach((b) => b.setAttribute("aria-pressed", String(b.dataset.slug === slug)));
    filtered = slug === "all" ? mixed : data.items.filter((it) => it.c === slug);
    shown = 0;
    list.innerHTML = "";
    status.textContent = `${slug === "all" ? "Wszystkie realizacje" : labels[slug]}: ${filtered.length} zdjęć`;
    renderMore();
  }

  moreBtn.addEventListener("click", renderMore);

  // Automatyczne doładowanie, gdy przycisk "Pokaż więcej" zbliża się do ekranu (infinite scroll),
  // ale dopiero po pierwszym ręcznym kliknięciu — żeby stopka/kontakt były osiągalne.
  let auto = false;
  moreBtn.addEventListener("click", () => (auto = true), { once: true });
  new IntersectionObserver(([e]) => { if (e.isIntersecting && auto && shown < filtered.length) renderMore(); },
    { rootMargin: "600px 0px" }).observe(moreBtn);

  // Kafelki w ofercie ustawiają filtr galerii
  $$("[data-filter]").forEach((a) => a.addEventListener("click", () => setFilter(a.dataset.filter)));

  /* ---- Lightbox ---- */
  const dlg = $("[data-lightbox]");
  const img = $("[data-lightbox-img]");
  const cap = $("[data-lightbox-caption]");
  let pos = 0;

  function show(i) {
    pos = (i + filtered.length) % filtered.length; // zawijanie: po ostatnim -> pierwsze
    const it = filtered[pos];
    img.src = `${BASE}full/${it.f}`;
    img.width = it.fw; img.height = it.fh;
    img.alt = `${labels[it.c]} — zdjęcie ${pos + 1}`;
    cap.textContent = `${labels[it.c]} · ${pos + 1} / ${filtered.length}`;
    // Wstępnie pobierz następne zdjęcie, żeby "dalej" działało natychmiast
    const next = filtered[(pos + 1) % filtered.length];
    new Image().src = `${BASE}full/${next.f}`;
  }
  function openLightbox(i) { show(i); dlg.showModal(); }

  $("[data-lightbox-prev]").addEventListener("click", () => show(pos - 1));
  $("[data-lightbox-next]").addEventListener("click", () => show(pos + 1));
  $("[data-lightbox-close]").addEventListener("click", () => dlg.close());
  // Klik w ciemne tło (poza zdjęciem i przyciskami) zamyka podgląd
  dlg.addEventListener("click", (e) => { if (e.target === dlg || e.target.classList.contains("lightbox__figure")) dlg.close(); });
  dlg.addEventListener("keydown", (e) => {
    if (e.key === "ArrowLeft") show(pos - 1);
    if (e.key === "ArrowRight") show(pos + 1);
  });

  // Gesty przesuwania palcem na telefonie
  let x0 = null;
  dlg.addEventListener("touchstart", (e) => (x0 = e.touches[0].clientX), { passive: true });
  dlg.addEventListener("touchend", (e) => {
    if (x0 === null) return;
    const dx = e.changedTouches[0].clientX - x0;
    if (Math.abs(dx) > 50) show(pos + (dx < 0 ? 1 : -1));
    x0 = null;
  });

  setFilter(current);
}

/* ---------- Start ---------- */
$("[data-year]").textContent = new Date().getFullYear();
initHeader();
initNav();
initHeroSlides();
initSparks();
initReveal();
initCounters();
initGallery();

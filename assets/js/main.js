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
  // Tylko linki do sekcji na TEJ stronie ("#oferta"). Na podstronach linki wyglądają jak
  // "./#oferta" — to nie jest poprawny selektor CSS i querySelector rzuciłby błąd.
  const sections = links.map((a) => a.getAttribute("href"))
    .filter((h) => /^#[\w-]+$/.test(h)).map((h) => $(h)).filter(Boolean);
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
    if (img.dataset.srcset) img.srcset = img.dataset.srcset; // wersja responsywna (kilka rozmiarów)
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

/* ---------- Paralaksa: tło przesuwa się wolniej niż strona ----------
   Efekt "głębi" na pełnoekranowych zdjęciach (sekcja Ogień/Młot/Kowadło i baner CTA).
   Liczymy przesunięcie tylko dla zdjęć widocznych na ekranie i tylko raz na klatkę
   (requestAnimationFrame) — przewijanie zostaje płynne także na słabszym telefonie. */
function initParallax() {
  const imgs = $$("[data-parallax]");
  if (!imgs.length || reducedMotion) return;
  const visible = new Set();
  const io = new IntersectionObserver((entries) => entries.forEach((e) => {
    e.isIntersecting ? visible.add(e.target) : visible.delete(e.target);
  }));
  imgs.forEach((img) => io.observe(img.parentElement));
  let ticking = false;
  const update = () => {
    ticking = false;
    visible.forEach((section) => {
      const r = section.getBoundingClientRect();
      // p: -1 (sekcja pod ekranem) .. 0 (środek) .. 1 (nad ekranem)
      const p = (window.innerHeight / 2 - (r.top + r.height / 2)) / (window.innerHeight / 2 + r.height / 2);
      $("[data-parallax]", section).style.transform = `translate3d(0, ${p * 12}%, 0) scale(1.25)`;
    });
  };
  window.addEventListener("scroll", () => {
    if (!ticking) { ticking = true; requestAnimationFrame(update); }
  }, { passive: true });
  update();
}

/* ---------- Lightbox (podgląd zdjęcia na pełnym ekranie) ----------
   Osobna funkcja, bo używa jej i strona główna (rzędy), i podstrony kategorii (siatka).
   Zwraca funkcję openLightbox(listaZdjęć, numer) — kto ją dostanie, może otworzyć podgląd. */
function initLightbox() {
  const dlg = $("[data-lightbox]");
  if (!dlg) return () => {};
  const BASE = "assets/img/gallery/";
  const img = $("[data-lightbox-img]");
  const cap = $("[data-lightbox-caption]");
  const labels = Object.fromEntries((window.GALLERY?.categories || []).map((c) => [c.slug, c.label]));
  let list = [];
  let pos = 0;

  function show(i) {
    pos = (i + list.length) % list.length; // zawijanie: po ostatnim -> pierwsze
    const it = list[pos];
    img.src = `${BASE}full/${it.f}`;
    img.width = it.fw; img.height = it.fh;
    img.alt = `${labels[it.c]} — zdjęcie ${pos + 1}`;
    cap.textContent = `${labels[it.c]} · ${pos + 1} / ${list.length}`;
    // Wstępnie pobierz następne zdjęcie, żeby "dalej" działało natychmiast
    new Image().src = `${BASE}full/${list[(pos + 1) % list.length].f}`;
  }

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

  return (items, i) => { list = items; show(i); dlg.showModal(); };
}

/* ---------- Podstrona kategorii: siatka zdjęć ----------
   Zdjęcia są już w HTML (wygenerowane przez scripts/build.py — dobre dla SEO,
   bo Google widzi je bez uruchamiania JS). Tutaj tylko podpinamy kliknięcia. */
function initCategoryGrid(openLightbox) {
  const grid = $("[data-category-grid]");
  if (!grid || !window.GALLERY) return;
  const items = window.GALLERY.items.filter((it) => it.c === grid.dataset.categoryGrid);
  $$("button", grid).forEach((b, i) => b.addEventListener("click", () => openLightbox(items, i)));
  $$("img", grid).forEach((img) => {
    if (img.complete) img.classList.add("is-loaded");
    else img.addEventListener("load", () => img.classList.add("is-loaded"), { once: true });
  });
}

/* ---------- Galeria: rzędy kategorii ----------
   Zamiast jednej ogromnej siatki (468 zdjęć = kilometr przewijania na telefonie)
   każda kategoria to poziomy rząd, przesuwany palcem w bok. Strona w pionie jest
   krótka, a i tak można obejrzeć wszystko. Zdjęcia ładują się leniwie (loading="lazy")
   dopiero, gdy rząd zostanie przesunięty blisko nich. */
function initGallery(openLightbox) {
  const data = window.GALLERY;
  const rowsEl = $("[data-gallery-rows]");
  if (!data || !rowsEl) return;

  const BASE = "assets/img/gallery/";
  const byCat = Object.fromEntries(data.categories.map((c) => [c.slug, data.items.filter((it) => it.c === c.slug)]));

  // Liczba zdjęć na kafelkach oferty
  $$("[data-count-cat]").forEach((el) => {
    el.textContent = `${(byCat[el.dataset.countCat] || []).length} realizacji`;
  });

  data.categories.forEach((cat) => {
    const items = byCat[cat.slug];
    const row = document.createElement("section");
    row.className = "row reveal";
    row.id = `row-${cat.slug}`;
    row.setAttribute("aria-label", cat.label);
    // Adres podstrony kategorii bierzemy z kafelka w ofercie — jedno źródło prawdy, bez kopiowania listy
    const page = $(`[data-filter="${cat.slug}"]`)?.getAttribute("href");
    row.innerHTML = `
      <div class="container row__head">
        <h3>${cat.label} <span class="row__count">${items.length}</span></h3>
        ${page ? `<a class="row__all" href="${page}">Cała kategoria →</a>` : ""}
        <div class="row__nav">
          <button type="button" class="row__btn" data-dir="-1" aria-label="Przewiń w lewo: ${cat.label}">‹</button>
          <button type="button" class="row__btn" data-dir="1" aria-label="Przewiń w prawo: ${cat.label}">›</button>
        </div>
      </div>
      <ul class="row__track" role="list"></ul>`;
    const track = $(".row__track", row);
    // Miniatury budujemy dopiero, gdy rząd zbliży się do ekranu (zapas 800 px).
    // 468 przycisków od razu = ciężki DOM i wolniejszy start strony na telefonie.
    const fill = () => {
      const frag = document.createDocumentFragment(); // jedna operacja na DOM zamiast setek = szybciej
      items.forEach((it, i) => {
        const li = document.createElement("li");
        li.innerHTML = `
          <button type="button" aria-label="Powiększ: ${cat.label}, zdjęcie ${i + 1} z ${items.length}">
            <img src="${BASE}thumb/${it.f}" width="${it.w}" height="${it.h}" alt="${cat.label} — realizacja Kowalstwa Artystycznego Marek Mida" loading="lazy" decoding="async">
          </button>`;
        const img = $("img", li);
        // Płynne pojawienie się po załadowaniu (zamiast "wyskakiwania" obrazka)
        if (img.complete) img.classList.add("is-loaded");
        else img.addEventListener("load", () => img.classList.add("is-loaded"), { once: true });
        $("button", li).addEventListener("click", () => openLightbox(items, i));
        frag.append(li);
      });
      track.append(frag);
      requestAnimationFrame(updateBtns);
    };
    const near = new IntersectionObserver(([e]) => {
      if (e.isIntersecting) { near.disconnect(); fill(); }
    }, { rootMargin: "800px 0px" });
    near.observe(row);

    // Strzałki (desktop): przewiń o ~80% szerokości rzędu
    $$(".row__btn", row).forEach((b) => b.addEventListener("click", () => {
      track.scrollBy({ left: +b.dataset.dir * track.clientWidth * 0.8, behavior: reducedMotion ? "auto" : "smooth" });
    }));
    // Wyszarz strzałkę, gdy jesteśmy na początku / końcu rzędu
    const updateBtns = () => {
      const [prev, next] = $$(".row__btn", row);
      prev.disabled = track.scrollLeft < 8;
      next.disabled = track.scrollLeft + track.clientWidth > track.scrollWidth - 8;
    };
    track.addEventListener("scroll", updateBtns, { passive: true });
    rowsEl.append(row);
    requestAnimationFrame(updateBtns);
  });

  // Rzędy dodaliśmy po starcie — trzeba je jeszcze "podpiąć" pod animacje wejścia
  const io = new IntersectionObserver((entries) => entries.forEach((e) => {
    if (e.isIntersecting) { e.target.classList.add("is-in"); io.unobserve(e.target); }
  }), { threshold: 0.1 });
  $$(".row", rowsEl).forEach((r) => io.observe(r));
}

/* ---------- Start ---------- */
$$("[data-year]").forEach((el) => (el.textContent = new Date().getFullYear()));
initHeader();
initNav();
initHeroSlides();
initSparks();
initReveal();
initCounters();
const openLightbox = initLightbox();
initGallery(openLightbox);
initCategoryGrid(openLightbox);
initParallax();

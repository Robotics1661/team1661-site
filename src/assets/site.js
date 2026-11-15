/* ---------- language helpers (shared with search.js) ---------- */
window.T1661 = (function () {
  var lang = (document.documentElement.lang || "en").slice(0, 2).toLowerCase();
  if (lang !== "es" && lang !== "zh") lang = "en";
  var S = {
    en: { light: "Switch to light mode", dark: "Switch to dark mode", viewer: "Photo viewer", close: "Close",
      searchDialog: "Search the site", placeholder: "Search robots, awards, code...", inputLabel: "Search", results: "Results",
      move: "&uarr;&darr; to move, Enter to open", all: "See all results",
      hint: "Type to search, for example \u201cswerve\u201d, \u201cawards\u201d or \u201cjoin\u201d.",
      none: function (q) { return "No results for \u201c" + q + "\u201d."; },
      noneLong: function (q) { return "No results for \u201c" + q + "\u201d. Try fewer or different words."; },
      found: function (n, q) { return n + (n === 1 ? " result" : " results") + " for \u201c" + q + "\u201d"; },
      title: function (q) { return "Search: " + q + " | Team 1661 Griffitrons"; },
      count: function (n) { return n + (n === 1 ? " project" : " projects"); },
      cat: { Page: "Page", Robot: "Robot", Code: "Code" } },
    es: { light: "Cambiar a modo claro", dark: "Cambiar a modo oscuro", viewer: "Visor de fotos", close: "Cerrar",
      searchDialog: "Buscar en el sitio", placeholder: "Buscar robots, premios, c\u00f3digo...", inputLabel: "Buscar", results: "Resultados",
      move: "&uarr;&darr; para moverte, Enter para abrir", all: "Ver todos los resultados",
      hint: "Escribe para buscar, por ejemplo \u201cswerve\u201d, \u201cpremios\u201d o \u201cunirse\u201d.",
      none: function (q) { return "Sin resultados para \u201c" + q + "\u201d."; },
      noneLong: function (q) { return "Sin resultados para \u201c" + q + "\u201d. Prueba con menos palabras o con otras distintas."; },
      found: function (n, q) { return n + (n === 1 ? " resultado" : " resultados") + " para \u201c" + q + "\u201d"; },
      title: function (q) { return "Buscar: " + q + " | Team 1661 Griffitrons"; },
      count: function (n) { return n + (n === 1 ? " proyecto" : " proyectos"); },
      cat: { Page: "P\u00e1gina", Robot: "Robot", Code: "C\u00f3digo" } },
    zh: { light: "\u5207\u6362\u5230\u6d45\u8272\u6a21\u5f0f", dark: "\u5207\u6362\u5230\u6df1\u8272\u6a21\u5f0f", viewer: "\u7167\u7247\u67e5\u770b\u5668", close: "\u5173\u95ed",
      searchDialog: "\u641c\u7d22\u672c\u7ad9", placeholder: "\u641c\u7d22\u673a\u5668\u4eba\u3001\u5956\u9879\u3001\u4ee3\u7801\u2026\u2026", inputLabel: "\u641c\u7d22", results: "\u7ed3\u679c",
      move: "&uarr;&darr; \u9009\u62e9\uff0c\u56de\u8f66\u6253\u5f00", all: "\u67e5\u770b\u5168\u90e8\u7ed3\u679c",
      hint: "\u8f93\u5165\u5185\u5bb9\u5f00\u59cb\u641c\u7d22\uff0c\u4f8b\u5982\u201cswerve\u201d\u201c\u5956\u9879\u201d\u6216\u201c\u52a0\u5165\u201d\u3002",
      none: function (q) { return "\u6ca1\u6709\u627e\u5230\u4e0e\u201c" + q + "\u201d\u76f8\u5173\u7684\u7ed3\u679c\u3002"; },
      noneLong: function (q) { return "\u6ca1\u6709\u627e\u5230\u4e0e\u201c" + q + "\u201d\u76f8\u5173\u7684\u7ed3\u679c\u3002\u8bd5\u8bd5\u66f4\u5c11\u6216\u4e0d\u540c\u7684\u5173\u952e\u8bcd\u3002"; },
      found: function (n, q) { return n + " \u6761\u4e0e\u201c" + q + "\u201d\u76f8\u5173\u7684\u7ed3\u679c"; },
      title: function (q) { return "\u641c\u7d22\uff1a" + q + " | Team 1661 Griffitrons"; },
      count: function (n) { return n + " \u4e2a\u9879\u76ee"; },
      cat: { Page: "\u9875\u9762", Robot: "\u673a\u5668\u4eba", Code: "\u4ee3\u7801" } }
  };
  return { lang: lang, s: S[lang] };
})();

(function () {
  "use strict";
  var doc = document;
  var reduce = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  // footer year
  var yr = doc.getElementById("yr");
  if (yr) yr.textContent = new Date().getFullYear();

  // mobile nav
  var toggle = doc.querySelector(".nav-toggle");
  var header = doc.querySelector(".site-header");
  if (toggle) {
    toggle.addEventListener("click", function () {
      var open = header.classList.toggle("open");
      toggle.setAttribute("aria-expanded", open ? "true" : "false");
    });
    doc.addEventListener("keydown", function (e) {
      if (e.key === "Escape" && header.classList.contains("open")) {
        header.classList.remove("open");
        toggle.setAttribute("aria-expanded", "false");
        toggle.focus();
      }
    });
  }

  // header shadow on scroll
  function onScroll() { header.classList.toggle("scrolled", window.scrollY > 8); }
  window.addEventListener("scroll", onScroll, { passive: true });
  onScroll();

  // scroll reveal
  var items = doc.querySelectorAll(".reveal");
  if ("IntersectionObserver" in window && !reduce) {
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (en) {
        if (en.isIntersecting) { en.target.classList.add("in"); io.unobserve(en.target); }
      });
    }, { threshold: 0.12, rootMargin: "0px 0px -6% 0px" });
    items.forEach(function (el, i) {
      el.style.setProperty("--d", ((i % 4) * 70) + "ms");
      io.observe(el);
    });
  } else {
    items.forEach(function (el) { el.classList.add("in"); });
  }

  // typed hero heading (text stays in the DOM for screen readers / no-JS)
  var type = doc.querySelector(".type");
  if (type && !reduce) {
    var full = type.getAttribute("data-text");
    type.setAttribute("aria-label", full);
    type.textContent = "";
    var i = 0;
    var t = setInterval(function () {
      type.textContent = full.slice(0, ++i);
      if (i >= full.length) { clearInterval(t); type.classList.add("done"); }
    }, 90);
  }
})();

/* ---------- polish layer ---------- */
(function () {
  "use strict";
  var doc = document, root = doc.documentElement;
  var reduce = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  var progress = doc.querySelector(".progress");
  var toTop = doc.querySelector(".to-top");
  var hero = doc.querySelector(".hero");
  var ticking = false;

  function frame() {
    var y = window.scrollY, max = root.scrollHeight - window.innerHeight;
    if (progress) progress.style.setProperty("--p", max > 0 ? (y / max).toFixed(4) : 0);
    if (toTop) {
      var show = y > 700;
      toTop.hidden = false;
      toTop.classList.toggle("show", show);
      toTop.tabIndex = show ? 0 : -1;
    }
    if (hero && !reduce && y < window.innerHeight * 1.2) {
      hero.style.setProperty("--py", (y * 0.25).toFixed(1) + "px");
      hero.style.setProperty("--fade", Math.min(y / (window.innerHeight * 0.8), 1).toFixed(3));
    }
    ticking = false;
  }
  window.addEventListener("scroll", function () {
    if (!ticking) { ticking = true; requestAnimationFrame(frame); }
  }, { passive: true });
  frame();
  if (toTop) toTop.addEventListener("click", function () { window.scrollTo({ top: 0, behavior: reduce ? "auto" : "smooth" }); });

  // count-up numbers (the founding year stays put)
  var counters = doc.querySelectorAll("[data-count]:not([data-plain])");
  if (counters.length && "IntersectionObserver" in window && !reduce) {
    var co = new IntersectionObserver(function (entries) {
      entries.forEach(function (en) {
        if (!en.isIntersecting) return;
        var el = en.target, end = parseInt(el.getAttribute("data-count"), 10), t0 = null;
        co.unobserve(el);
        function step(t) {
          if (t0 === null) t0 = t;
          var k = Math.min((t - t0) / 1400, 1), e = 1 - Math.pow(1 - k, 3);
          el.textContent = Math.round(end * e);
          if (k < 1) requestAnimationFrame(step);
        }
        el.textContent = "0";
        requestAnimationFrame(step);
      });
    }, { threshold: 0.6 });
    counters.forEach(function (c) { co.observe(c); });
  }

  // cursor spotlight on cards
  doc.addEventListener("pointermove", function (e) {
    var t = e.target.closest && e.target.closest(".card, .media-card, .sponsor, .social-card");
    if (!t) return;
    var r = t.getBoundingClientRect();
    t.style.setProperty("--mx", (e.clientX - r.left) + "px");
    t.style.setProperty("--my", (e.clientY - r.top) + "px");
  }, { passive: true });

  // photo lightbox
  var lb = doc.createElement("div");
  lb.className = "lightbox"; lb.setAttribute("role", "dialog"); lb.setAttribute("aria-modal", "true"); lb.setAttribute("aria-label", window.T1661.s.viewer);
  lb.innerHTML = '<button type="button" aria-label="' + window.T1661.s.close + '">&times;</button><img alt="" /><p></p>';
  doc.body.appendChild(lb);
  var lbImg = lb.querySelector("img"), lbCap = lb.querySelector("p"), lbBtn = lb.querySelector("button"), lastFocus = null;
  function openLb(img) {
    lastFocus = doc.activeElement;
    lbImg.src = img.currentSrc || img.src; lbImg.alt = img.alt; lbCap.textContent = img.alt;
    lb.classList.add("open"); lbBtn.focus();
  }
  function closeLb() { lb.classList.remove("open"); if (lastFocus) lastFocus.focus(); }
  doc.querySelectorAll(".robot-img:not(.placeholder) img, .photo-frame img, .gallery img").forEach(function (img) {
    img.addEventListener("click", function () { openLb(img); });
  });
  lb.addEventListener("click", function (e) { if (e.target !== lbImg) closeLb(); });
  doc.addEventListener("keydown", function (e) { if (e.key === "Escape" && lb.classList.contains("open")) closeLb(); });
})();

/* ---------- theme toggle (dark is the default) ---------- */
(function () {
  "use strict";
  var btn = document.querySelector(".theme-toggle"), root = document.documentElement;
  if (!btn) return;
  function isLight() { return root.getAttribute("data-theme") === "light"; }
  function sync() { btn.setAttribute("aria-label", isLight() ? window.T1661.s.dark : window.T1661.s.light); }
  btn.addEventListener("click", function () {
    var next = isLight() ? "dark" : "light";
    root.setAttribute("data-theme", next);
    try { localStorage.setItem("theme", next); } catch (e) {}
    sync();
  });
  sync();
})();

/* ---------- language menu ---------- */
(function () {
  "use strict";
  var doc = document, menu = doc.querySelector(".lang-menu");
  if (!menu) return;
  menu.querySelectorAll("a[data-lang]").forEach(function (a) {
    a.addEventListener("click", function () {
      try { localStorage.setItem("lang", a.getAttribute("data-lang")); } catch (e) {}
      // keep the search query / section when switching language
      a.setAttribute("href", a.getAttribute("href") + window.location.search + window.location.hash);
    });
  });
  doc.addEventListener("click", function (e) { if (menu.open && !menu.contains(e.target)) menu.open = false; });
  doc.addEventListener("keydown", function (e) {
    if (e.key === "Escape" && menu.open) { menu.open = false; menu.querySelector("summary").focus(); }
  });
})();

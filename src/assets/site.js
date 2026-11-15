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
  lb.className = "lightbox"; lb.setAttribute("role", "dialog"); lb.setAttribute("aria-modal", "true"); lb.setAttribute("aria-label", "Photo viewer");
  lb.innerHTML = '<button type="button" aria-label="Close">&times;</button><img alt="" /><p></p>';
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
  function sync() { btn.setAttribute("aria-label", isLight() ? "Switch to dark mode" : "Switch to light mode"); }
  btn.addEventListener("click", function () {
    var next = isLight() ? "dark" : "light";
    root.setAttribute("data-theme", next);
    try { localStorage.setItem("theme", next); } catch (e) {}
    sync();
  });
  sync();
})();

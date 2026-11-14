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

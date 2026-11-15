(function () {
  "use strict";
  var doc = document;
  var me = doc.querySelector('script[src*="search.js"]');
  var base = me ? me.src.replace(/assets\/search\.js.*$/, "") : "";
  var index = null, loading = null;

  function load() {
    if (index) return Promise.resolve(index);
    if (!loading) {
      loading = fetch(base + "assets/search-index.json").then(function (r) { return r.json(); }).then(function (d) {
        d.forEach(function (e) {
          e._t = e.t.toLowerCase(); e._k = (e.k || "").toLowerCase(); e._d = (e.d || "").toLowerCase(); e._b = (e.b || "").toLowerCase();
        });
        index = d; return d;
      });
    }
    return loading;
  }

  function words(s) { return s.toLowerCase().split(/[^a-z0-9]+/).filter(Boolean); }
  function wordStart(h, t) { return new RegExp("(^|[^a-z0-9])" + t.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")).test(h); }

  function search(q) {
    var toks = words(q);
    if (!toks.length) return [];
    var out = [];
    index.forEach(function (e) {
      var score = 0;
      for (var i = 0; i < toks.length; i++) {
        var t = toks[i], s = 0;
        if (e._t.indexOf(t) !== -1) s += wordStart(e._t, t) ? 10 : 6;
        if (e._k.indexOf(t) !== -1) s += wordStart(e._k, t) ? 5 : 3;
        if (e._d.indexOf(t) !== -1) s += 3;
        if (e._b.indexOf(t) !== -1) s += 1;
        if (!s) return;  // every word must match somewhere
        score += s;
      }
      if (e._t === q.toLowerCase().trim()) score += 20;
      if (e.c === "Robot" || e.c === "Code") score += 0.5;
      if (e.n) score -= 8;  // forks and archived repos rank lower
      out.push({ e: e, s: score });
    });
    out.sort(function (a, b) { return b.s - a.s; });
    return out.map(function (x) { return x.e; });
  }

  function highlight(node, text, toks) {
    if (!toks.length) { node.textContent = text; return; }
    var re = new RegExp("(" + toks.map(function (t) { return t.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"); }).join("|") + ")", "ig");
    text.split(re).forEach(function (part, i) {
      if (i % 2) { var m = doc.createElement("mark"); m.textContent = part; node.appendChild(m); }
      else node.appendChild(doc.createTextNode(part));
    });
  }

  function hitEl(e, toks, id) {
    var a = doc.createElement("a");
    a.className = "hit"; a.href = base + e.u; a.id = id; a.setAttribute("role", "option"); a.setAttribute("aria-selected", "false");
    var top = doc.createElement("div"); top.className = "hit-top";
    var t = doc.createElement("span"); t.className = "hit-title"; highlight(t, e.t, toks);
    var c = doc.createElement("span"); c.className = "hit-cat"; c.textContent = e.c;
    top.appendChild(t); top.appendChild(c); a.appendChild(top);
    if (e.d) { var d = doc.createElement("div"); d.className = "hit-desc"; highlight(d, e.d, toks); a.appendChild(d); }
    return a;
  }

  /* ---- header overlay ---- */
  var overlay, input, list, lastFocus, sel = -1, hits = [];
  function build() {
    overlay = doc.createElement("div");
    overlay.className = "search-overlay";
    overlay.innerHTML =
      '<div class="search-panel" role="dialog" aria-modal="true" aria-label="Search the site">' +
      '<div class="search-top"><svg class="icon" viewBox="0 0 24 24" aria-hidden="true"><path fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" d="M10.5 18a7.5 7.5 0 1 1 0-15 7.5 7.5 0 0 1 0 15zM16 16l5 5"/></svg>' +
      '<input type="search" placeholder="Search robots, awards, code..." autocomplete="off" spellcheck="false" role="combobox" aria-expanded="false" aria-controls="search-listbox" aria-label="Search" />' +
      '<button type="button" class="search-close">Esc</button></div>' +
      '<div class="search-list" id="search-listbox" role="listbox" aria-label="Results"></div>' +
      '<div class="search-foot"><span>&uarr;&darr; to move, Enter to open</span><a class="inline-link" id="search-all" href="#">See all results</a></div></div>';
    doc.body.appendChild(overlay);
    input = overlay.querySelector("input"); list = overlay.querySelector(".search-list");
    overlay.addEventListener("mousedown", function (e) { if (e.target === overlay) close(); });
    overlay.querySelector(".search-close").addEventListener("click", close);
    input.addEventListener("input", render);
    input.addEventListener("keydown", onKey);
    overlay.addEventListener("keydown", function (e) {
      if (e.key === "Tab") {  // keep focus inside the dialog
        var f = [input, overlay.querySelector(".search-close"), overlay.querySelector("#search-all")];
        var i = f.indexOf(doc.activeElement);
        if (e.shiftKey && i <= 0) { f[f.length - 1].focus(); e.preventDefault(); }
        else if (!e.shiftKey && i === f.length - 1) { f[0].focus(); e.preventDefault(); }
      }
    });
    overlay.querySelector("#search-all").addEventListener("click", function (e) { e.preventDefault(); go(); });
  }

  function setSel(i) {
    var els = list.querySelectorAll(".hit");
    if (!els.length) { sel = -1; input.removeAttribute("aria-activedescendant"); return; }
    sel = (i + els.length) % els.length;
    els.forEach(function (el, n) { el.setAttribute("aria-selected", n === sel ? "true" : "false"); });
    input.setAttribute("aria-activedescendant", els[sel].id);
    els[sel].scrollIntoView({ block: "nearest" });
  }

  function render() {
    var q = input.value.trim();
    list.textContent = "";
    sel = -1; input.removeAttribute("aria-activedescendant");
    if (!q) { input.setAttribute("aria-expanded", "false"); var h = doc.createElement("p"); h.className = "search-hint"; h.textContent = "Type to search, for example “swerve”, “awards” or “join”."; list.appendChild(h); return; }
    load().then(function () {
      if (input.value.trim() !== q) return;
      var toks = words(q);
      hits = search(q);
      list.textContent = "";
      input.setAttribute("aria-expanded", hits.length ? "true" : "false");
      if (!hits.length) { var n = doc.createElement("p"); n.className = "search-hint"; n.textContent = "No results for “" + q + "”."; list.appendChild(n); return; }
      hits.slice(0, 8).forEach(function (e, i) { list.appendChild(hitEl(e, toks, "hit-" + i)); });
      setSel(0);
    });
  }

  function go() { var q = input.value.trim(); window.location.href = base + "search.html" + (q ? "?q=" + encodeURIComponent(q) : ""); }

  function onKey(e) {
    if (e.key === "ArrowDown") { e.preventDefault(); setSel(sel + 1); }
    else if (e.key === "ArrowUp") { e.preventDefault(); setSel(sel - 1); }
    else if (e.key === "Enter") {
      e.preventDefault();
      var els = list.querySelectorAll(".hit");
      if (sel >= 0 && els[sel]) window.location.href = els[sel].href; else go();
    }
  }

  function open() {
    if (!overlay) build();
    lastFocus = doc.activeElement;
    overlay.classList.add("open");
    doc.documentElement.style.overflow = "hidden";
    input.focus(); input.select();
    load(); render();
  }
  function close() {
    if (!overlay) return;
    overlay.classList.remove("open");
    doc.documentElement.style.overflow = "";
    if (lastFocus && lastFocus.focus) lastFocus.focus();
  }

  var btn = doc.querySelector(".search-toggle");
  if (btn) btn.addEventListener("click", open);
  doc.addEventListener("keydown", function (e) {
    var tag = (e.target.tagName || "").toLowerCase();
    var typing = tag === "input" || tag === "textarea" || tag === "select" || e.target.isContentEditable;
    if (e.key === "Escape" && overlay && overlay.classList.contains("open")) { close(); }
    else if ((e.key === "/" && !typing && !e.ctrlKey && !e.metaKey && !e.altKey) || ((e.key === "k" || e.key === "K") && (e.ctrlKey || e.metaKey))) {
      if (doc.body.getAttribute("data-search-page")) { var q = doc.getElementById("q"); if (q) { e.preventDefault(); q.focus(); } return; }
      e.preventDefault(); open();
    }
  });

  /* ---- search page ---- */
  if (doc.body.getAttribute("data-search-page")) {
    var qi = doc.getElementById("q"), res = doc.getElementById("search-results"), status = doc.getElementById("search-status");
    var params = new URLSearchParams(window.location.search);
    qi.value = params.get("q") || "";
    var run = function () {
      var q = qi.value.trim();
      res.textContent = ""; status.textContent = "";
      if (!q) return;
      load().then(function () {
        var toks = words(q), found = search(q);
        status.textContent = found.length ? found.length + (found.length === 1 ? " result" : " results") + " for “" + q + "”" : "No results for “" + q + "”. Try fewer or different words.";
        found.forEach(function (e, i) { var li = doc.createElement("li"); li.appendChild(hitEl(e, toks, "r-" + i)); res.appendChild(li); });
        document.title = "Search: " + q + " | Team 1661 Griffitrons";
      });
    };
    qi.addEventListener("input", function () {
      if (window.history && history.replaceState) history.replaceState(null, "", qi.value.trim() ? "?q=" + encodeURIComponent(qi.value.trim()) : window.location.pathname);
      run();
    });
    run();
  }

  /* ---- code page filter ---- */
  var grid = doc.getElementById("repo-grid");
  if (grid) {
    var f = doc.getElementById("repo-filter"), cards = Array.prototype.slice.call(grid.children), chips = doc.querySelectorAll(".chip");
    var count = doc.getElementById("repo-count"), empty = doc.getElementById("repo-empty"), group = "all";
    var apply = function () {
      var toks = words(f.value), shown = 0;
      cards.forEach(function (c) {
        var text = c.getAttribute("data-text"), ok = (group === "all" || c.getAttribute("data-group") === group) && toks.every(function (t) { return text.indexOf(t) !== -1; });
        c.hidden = !ok; if (ok) shown++;
      });
      count.textContent = shown + (shown === 1 ? " project" : " projects");
      empty.hidden = shown !== 0;
    };
    f.addEventListener("input", apply);
    chips.forEach(function (c) {
      c.addEventListener("click", function () {
        group = c.getAttribute("data-filter");
        chips.forEach(function (o) { o.setAttribute("aria-pressed", o === c ? "true" : "false"); });
        apply();
      });
    });
  }
})();

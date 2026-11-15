#!/usr/bin/env python3
"""Generate the /code pages, search page, search index and sitemap for team1661.com.

Run from anywhere:  python3 scripts/build.py
Safe to re-run: existing pages are only patched once, generated files are rewritten.
The published site itself still has no build step; this output is committed.
"""
import html
import json
import re
import sys
from datetime import date
from html.parser import HTMLParser
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from repos import GH, GROUPS, REPOS  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
SITE = "https://team1661.com"
TODAY = date.today().isoformat()
E = html.escape
SEARCH_SVG = ('<svg class="icon" viewBox="0 0 24 24" aria-hidden="true" focusable="false"><path fill="none" '
              'stroke="currentColor" stroke-width="2.2" stroke-linecap="round" d="M10.5 18a7.5 7.5 0 1 1 0-15 7.5 '
              '7.5 0 0 1 0 15zM16 16l5 5"/></svg>')
SEARCH_BTN = ('<button class="search-toggle" type="button" aria-label="Search the site" aria-haspopup="dialog">'
              + SEARCH_SVG + '</button>')
SUN = ('<svg class="icon sun" viewBox="0 0 24 24" aria-hidden="true" focusable="false"><g fill="none" stroke="currentColor" '
       'stroke-width="2" stroke-linecap="round"><circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/></g></svg>')
MOON = ('<svg class="icon moon" viewBox="0 0 24 24" aria-hidden="true" focusable="false"><path fill="none" stroke="currentColor" '
        'stroke-width="2" stroke-linejoin="round" d="M20 14.5A8 8 0 0 1 9.5 4a8 8 0 1 0 10.5 10.5z"/></svg>')
THEME_BTN = ('<button class="theme-toggle" type="button" aria-label="Switch to light mode">' + SUN + MOON + '</button>')
THEME_SCRIPT = ('<script>document.documentElement.classList.add("js");try{if(localStorage.getItem("theme")==="light")'
                'document.documentElement.setAttribute("data-theme","light")}catch(e){}</script>')
OLD_JS_SCRIPT = '<script>document.documentElement.classList.add("js")</script>'
TOP_PAGES = ["index", "robots", "awards", "outreach", "sponsors", "media", "join"]
CRUMB_NAMES = {"robots": "Robots", "awards": "Awards", "outreach": "Outreach", "sponsors": "Sponsors",
               "media": "Media & Contact", "join": "Join the Team"}


# ---------------------------------------------------------------- patch existing pages
def patch_existing():
    for p in sorted(SRC.glob("*.html")):
        t = p.read_text(encoding="utf-8")
        o = t
        name = p.stem
        # nav + footer link to Code (both use the same list markup)
        if 'href="code.html"' not in t:
            t = re.sub(r'(<li><a href="robots\.html"(?: aria-current="page")?>Robots</a></li>)',
                       r'\1<li><a href="code.html">Code</a></li>', t)
        # header search button
        if "search-toggle" not in t:
            t = t.replace("</nav>\n  </div>\n</header>", "</nav>\n    " + SEARCH_BTN + "\n  </div>\n</header>", 1)
            t = t.replace('<nav id="nav" aria-label="Main">', '<nav id="nav" aria-label="Main">', 1)
        if "theme-toggle" not in t:
            t = t.replace(SEARCH_BTN, SEARCH_BTN + "\n    " + THEME_BTN, 1)
        if "data-theme" not in t:
            t = t.replace(OLD_JS_SCRIPT, THEME_SCRIPT, 1)
        if "assets/search.js" not in t:
            t = t.replace('<script src="assets/site.js"></script>',
                          '<script src="assets/site.js"></script>\n<script src="assets/search.js" defer></script>', 1)
        # og image dimensions + twitter alt
        if "og:image:width" not in t and "2024-bot.jpg" in t:
            t = re.sub(r'(<meta property="og:image" content="[^"]*2024-bot\.jpg" />)',
                       r'\1\n<meta property="og:image:width" content="1800" />\n<meta property="og:image:height" content="1080" />', t, count=1)
        if "twitter:image:alt" not in t:
            m = re.search(r'<meta property="og:image:alt" content="([^"]*)" />', t)
            if m:
                t = t.replace('<meta name="twitter:image"', f'<meta name="twitter:image:alt" content="{m.group(1)}" />\n<meta name="twitter:image"', 1)
        # structured data
        if name in CRUMB_NAMES and "BreadcrumbList" not in t:
            ld = breadcrumb_ld([("Home", SITE + "/"), (CRUMB_NAMES[name], f"{SITE}/{name}.html")])
            t = t.replace("</head>", f'<script type="application/ld+json">{ld}</script>\n</head>', 1)
        if name == "index" and '"WebSite"' not in t:
            ld = json.dumps({"@context": "https://schema.org", "@type": "WebSite", "name": "Team 1661 Griffitrons",
                             "url": SITE + "/", "inLanguage": "en",
                             "potentialAction": {"@type": "SearchAction",
                                                 "target": {"@type": "EntryPoint", "urlTemplate": SITE + "/search.html?q={search_term_string}"},
                                                 "query-input": "required name=search_term_string"}},
                            separators=(",", ":"))
            t = t.replace("</head>", f'<script type="application/ld+json">{ld}</script>\n</head>', 1)
        # internal "About the code" links next to the GitHub buttons on the robots page
        if name == "robots" and "About the code" not in t:
            def add_link(m):
                slug = m.group(2).lower()
                return (f'<div class="btn-row tight">{m.group(1)}'
                        f'<a class="btn btn-outline" href="code/{slug}.html">About the code</a></div>')
            t = re.sub(r'(<a class="btn btn-dark" href="https://github\.com/Robotics1661/([^"]+)"[^>]*>.*?</a>)', add_link, t, flags=re.S)
        if t != o:
            p.write_text(t, encoding="utf-8")
            print("patched", p.name)


def breadcrumb_ld(items):
    return json.dumps({"@context": "https://schema.org", "@type": "BreadcrumbList",
                       "itemListElement": [{"@type": "ListItem", "position": i + 1, "name": n, "item": u}
                                           for i, (n, u) in enumerate(items)]}, separators=(",", ":"))


# ---------------------------------------------------------------- shared chrome (taken from a live page)
def chrome():
    t = (SRC / "robots.html").read_text(encoding="utf-8")
    top = re.search(r'<a class="skip".*?</header>', t, re.S).group(0)
    bottom = re.search(r'<footer class="site-footer">.*?</footer>\n<button class="to-top".*?</button>', t, re.S).group(0)
    gh_icon = re.search(r'<svg class="icon sm" viewBox="0 0 496 512".*?</svg>', t, re.S).group(0)
    return top.replace(' aria-current="page"', ""), bottom, gh_icon


def rel(fragment, depth):
    """Rewrite root-relative href/src values so a fragment works from a subfolder."""
    if depth == 0:
        return fragment
    pre = "../" * depth
    return re.sub(r'(href|src)="(?!https?:|#|mailto:|\.\./|/|data:)', lambda m: f'{m.group(1)}="{pre}', fragment)


def mark_current(top, href):
    return top.replace(f'<a href="{href}">', f'<a href="{href}" aria-current="page">', 1)


def head(title, desc, path, depth, image=None, image_alt=None, ld=(), noindex=False):
    pre = "../" * depth
    url = f"{SITE}/{path}" if path else SITE + "/"
    img = image or "assets/images/1661-logo-black.png"
    img_url = f"{SITE}/{img}"
    robots = "noindex, follow" if noindex else "index, follow, max-image-preview:large"
    alt = image_alt or "Team 1661 Griffitrons logo"
    dims = ('\n<meta property="og:image:width" content="1800" />\n<meta property="og:image:height" content="1080" />'
            if img.endswith("2024-bot.jpg") else "")
    ld_tags = "\n".join(f'<script type="application/ld+json">{x}</script>' for x in ld)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<meta name="theme-color" content="#0d0e12" />
<title>{E(title)}</title>
<meta name="description" content="{E(desc, quote=True)}" />
<link rel="canonical" href="{url}" />
<meta name="robots" content="{robots}" />
<meta name="author" content="Team 1661 Griffitrons" />
<meta property="og:type" content="website" />
<meta property="og:site_name" content="Team 1661 Griffitrons" />
<meta property="og:locale" content="en_US" />
<meta property="og:url" content="{url}" />
<meta property="og:title" content="{E(title, quote=True)}" />
<meta property="og:description" content="{E(desc, quote=True)}" />
<meta property="og:image" content="{img_url}" />{dims}
<meta property="og:image:alt" content="{E(alt, quote=True)}" />
<meta name="twitter:card" content="summary_large_image" />
<meta name="twitter:site" content="@buckleyrobotics" />
<meta name="twitter:title" content="{E(title, quote=True)}" />
<meta name="twitter:description" content="{E(desc, quote=True)}" />
<meta name="twitter:image" content="{img_url}" />
<meta name="twitter:image:alt" content="{E(alt, quote=True)}" />
{ld_tags}
<link rel="icon" href="{pre}assets/images/1661-logo.png" />
<link rel="preconnect" href="https://fonts.googleapis.com" />
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
<link href="https://fonts.googleapis.com/css2?family=Barlow:wght@400;500;600&family=Barlow+Condensed:ital,wght@0,500;0,600;0,700;1,600;1,700&display=swap" rel="stylesheet" />
<link rel="stylesheet" href="{pre}assets/style.css" />
{THEME_SCRIPT}
</head>
<body class="">
"""


def tail(depth):
    pre = "../" * depth
    return f'\n<script src="{pre}assets/site.js"></script>\n<script src="{pre}assets/search.js" defer></script>\n</body>\n</html>\n'


CTA = ('<section class="cta"><div class="wrap reveal"><h2>Want to join?</h2><p>If you go to Buckley, come by the robotics '
       'room after school. We&rsquo;ll find something for you to work on.</p><div class="btn-row"><a class="btn btn-light" '
       'href="join.html">Join the team</a><a class="btn btn-ghost" href="robots.html">Meet our robots</a></div></div></section>')


def by_slug():
    return {r["slug"]: r for r in REPOS}


def label(r):
    bits = [r["year"]]
    if r["season"]:
        bits.append(r["season"])
    return " &middot; ".join(E(b) for b in bits)


def description(r):
    d = f'{r["repo"]}: {r["summary"]}'
    if len(d) > 158:
        d = d[:155].rsplit(" ", 1)[0] + "..."
    return d


# ---------------------------------------------------------------- pages
def repo_page(r, top, bottom, gh_icon):
    depth = 1
    slug = r["slug"]
    path = f"code/{slug}.html"
    url = f"{SITE}/{path}"
    others = by_slug()
    title = f'{r["title"]} | Team 1661 Griffitrons'
    desc = description(r)
    ld_code = {"@context": "https://schema.org", "@type": "SoftwareSourceCode", "name": r["repo"],
               "description": r["summary"], "url": url, "codeRepository": GH + r["repo"],
               "programmingLanguage": r["lang"], "author": {"@type": "Organization", "name": "Griffitrons 1661", "url": SITE + "/"},
               "dateCreated": r["year"]}
    if r.get("license"):
        ld_code["license"] = "https://opensource.org/licenses/MIT"
    ld = [json.dumps(ld_code, separators=(",", ":")),
          breadcrumb_ld([("Home", SITE + "/"), ("Code", SITE + "/code.html"), (r["title"], url)])]
    img = f'assets/images/{r["image"]}' if r.get("image") else None
    parts = [head(title, desc, path, depth, img, r.get("image_alt"), ld), rel(top, depth), '<main id="main">']
    badges = ""
    if r.get("archived"):
        badges += '<span class="pill">Archived</span>'
    if r.get("fork"):
        badges += '<span class="pill">Fork</span>'
    parts.append(f'''<section class="page-hero"><div class="wrap">
  <nav class="crumbs" aria-label="Breadcrumb"><a href="../index.html">Home</a><span aria-hidden="true">/</span><a href="../code.html">Code</a><span aria-hidden="true">/</span><span aria-current="page">{E(r["title"])}</span></nav>
  <p class="kicker">Code &middot; {label(r)}</p><h1>{E(r["title"])}</h1>
  <p class="lede">{E(r["summary"])}</p>{('<p class="hero-pills">' + badges + '</p>') if badges else ''}
</div></section>''')
    # details + media
    media = ""
    if r.get("image"):
        media = (f'<figure class="photo-frame reveal"><img width="1800" height="1080" src="../assets/images/{r["image"]}" '
                 f'alt="{E(r["image_alt"], quote=True)}" loading="lazy" /><figcaption>{E(r["title"].split(" (")[-1].rstrip(")")) if "(" in r["title"] else E(r["repo"])}</figcaption></figure>')
    else:
        media = ('<div class="spec reveal"><h3>Tech at a glance</h3><dl>'
                 + "".join(f"<div><dt>{E(k)}</dt><dd>{E(v)}</dd></div>" for k, v in r["stack"]) + "</dl></div>")
    lis = "".join(f"<li>{E(h)}</li>" for h in r["highlights"])
    tags = "".join(f"<li>{E(t)}</li>" for t in r["tags"])
    buttons = f'<a class="btn btn-dark" href="{GH}{r["repo"]}" target="_blank" rel="noopener">{gh_icon} View on GitHub</a>'
    if r.get("robot"):
        buttons += f'<a class="btn btn-outline" href="../robots.html#{r["robot"]}">See the robot</a>'
    buttons += '<a class="btn btn-outline" href="../code.html">All code</a>'
    parts.append(f'''<section class="section"><div class="wrap split">
  <div class="reveal">
    <p class="kicker">What&rsquo;s in it</p>
    <h2 class="repo-h">{E(r["repo"])}</h2>
    <ul class="checks">{lis}</ul>
    <ul class="tags">{tags}</ul>
    <div class="btn-row tight">{buttons}</div>
  </div>
  <div>{media}</div>
</div></section>''')
    if r.get("image"):
        parts.append('<section class="section nopt"><div class="wrap narrow"><div class="spec reveal"><h3>Tech at a glance</h3><dl>'
                     + "".join(f"<div><dt>{E(k)}</dt><dd>{E(v)}</dd></div>" for k, v in r["stack"]) + "</dl></div></div></section>")
    if r["quick"]:
        cmds = "".join(f'<div class="cmd"><span>{E(k)}</span><code>{E(v)}</code></div>' for k, v in r["quick"])
        parts.append(f'<section class="section tint"><div class="wrap narrow"><div class="sec-head reveal"><p class="kicker">Try it</p><h2>Quick start</h2></div><div class="code-block reveal">{cmds}</div>'
                     f'<p class="center fine">Full instructions are in the <a class="inline-link" href="{GH}{r["repo"]}#readme" target="_blank" rel="noopener">README on GitHub</a>.</p></div></section>')
    if r.get("license") == "MIT":
        lic = "This code is released under the MIT License, so you are welcome to learn from it and reuse it."
    elif r.get("fork"):
        lic = "This is a fork, so it keeps the license of the project it came from."
    else:
        lic = ""
    if lic:
        parts.append(f'<section class="section nopt"><div class="wrap narrow"><p class="center fine reveal">{E(lic)}</p></div></section>')
    rel_cards = "".join(
        f'<a class="card repo-card reveal" href="{o["slug"]}.html"><span class="num">{E(o["year"])}</span><h3>{E(o["title"])}</h3><p>{E(o["summary"].split(". ")[0].rstrip("."))}.</p></a>'
        for o in (others[s] for s in r["related"]))
    parts.append(f'<section class="section"><div class="wrap"><div class="sec-head reveal"><p class="kicker">Keep exploring</p><h2>Related code</h2></div><div class="cards three">{rel_cards}</div></div></section>')
    parts.append(CTA.replace('href="join.html"', 'href="../join.html"').replace('href="robots.html"', 'href="../robots.html"'))
    parts.append("</main>")
    parts.append(rel(bottom, depth))
    parts.append(tail(depth))
    (SRC / "code").mkdir(exist_ok=True)
    (SRC / path).write_text("\n".join(parts), encoding="utf-8")


def code_index(top, bottom, gh_icon):
    title = "Code | Team 1661 Griffitrons"
    desc = "Open-source code from FRC Team 1661: robot code from 2020 to 2026, vision, dashboards, diagrams and the team websites, all on GitHub."
    ld = [json.dumps({"@context": "https://schema.org", "@type": "CollectionPage", "name": "Team 1661 code", "url": SITE + "/code.html",
                      "description": desc, "mainEntity": {"@type": "ItemList", "itemListElement": [
                          {"@type": "ListItem", "position": i + 1, "url": f"{SITE}/code/{r['slug']}.html", "name": r["title"]}
                          for i, r in enumerate(REPOS)]}}, separators=(",", ":")),
          breadcrumb_ld([("Home", SITE + "/"), ("Code", SITE + "/code.html")])]
    cards = []
    for r in REPOS:
        text = " ".join([r["repo"], r["title"], r["summary"], r["lang"], r["year"], r["season"], " ".join(r["tags"])]).lower()
        pills = ""
        if r.get("archived"):
            pills += '<span class="pill">Archived</span>'
        if r.get("fork"):
            pills += '<span class="pill">Fork</span>'
        cards.append(
            f'<article class="card repo-card" data-group="{r["group"]}" data-text="{E(text, quote=True)}">'
            f'<span class="num">{E(r["year"])}{(" &middot; " + E(r["season"])) if r["season"] else ""}</span>'
            f'<h3><a class="stretch" href="code/{r["slug"]}.html">{E(r["title"])}</a></h3>{pills}'
            f'<p>{E(r["summary"].split(". ")[0].rstrip("."))}.</p>'
            f'<ul class="tags sm">{"".join(f"<li>{E(t)}</li>" for t in r["tags"][:4])}</ul></article>')
    chips = '<button class="chip" type="button" data-filter="all" aria-pressed="true">All</button>' + "".join(
        f'<button class="chip" type="button" data-filter="{k}" aria-pressed="false">{E(v)}</button>' for k, v in GROUPS)
    body = f'''<main id="main">
<section class="page-hero"><div class="wrap"><p class="kicker">Code</p><h1>Our Code</h1><p class="lede">Everything we write is open source on GitHub. Pick a project to see what it does and how to run it.</p></div></section>
<section class="section"><div class="wrap">
  <div class="filter-bar reveal" role="search">
    <label class="sr" for="repo-filter">Filter projects</label>
    <div class="field">{SEARCH_SVG}<input id="repo-filter" type="search" placeholder="Filter by name, language or tag (try &ldquo;swerve&rdquo;)" autocomplete="off" /></div>
    <div class="chips" role="group" aria-label="Project type">{chips}</div>
  </div>
  <p id="repo-count" class="fine center" aria-live="polite">{len(REPOS)} projects</p>
  <div class="cards three repo-grid" id="repo-grid">{"".join(cards)}</div>
  <p id="repo-empty" class="center big" hidden>No projects match that. Try a different word, or clear the filter.</p>
  <p class="center fine">Looking for something on the whole site? Use the search button in the header, or press <kbd>/</kbd>.</p>
  <p class="center fine">Our GitHub organization is <a class="inline-link" href="https://github.com/Robotics1661" target="_blank" rel="noopener">Robotics1661</a>. A few private repos are not listed here.</p>
</div></section>
{CTA}
</main>'''
    out = head(title, desc, "code.html", 0, "assets/images/2024-bot.jpg", "Eclipse, the 2024 Team 1661 competition robot", ld)
    out += mark_current(top, "code.html") + "\n" + body + "\n" + bottom.replace('<li><a href="code.html">Code</a>', '<li><a href="code.html">Code</a>') + tail(0)
    (SRC / "code.html").write_text(out, encoding="utf-8")


def search_page(top, bottom):
    title = "Search | Team 1661 Griffitrons"
    desc = "Search the Team 1661 website: robots, awards, outreach, sponsors and our open-source code."
    items = "".join(f'<li><a href="{E(u)}">{E(t)}</a></li>' for t, u in all_pages_for_noscript())
    body = f'''<main id="main">
<section class="page-hero"><div class="wrap"><p class="kicker">Search</p><h1>Search the site</h1><p class="lede">Robots, awards, outreach, sponsors and code.</p></div></section>
<section class="section"><div class="wrap narrow">
  <form class="search-form" role="search" action="search.html" method="get">
    <label class="sr" for="q">Search</label>
    <div class="field">{SEARCH_SVG}<input id="q" name="q" type="search" placeholder="Search robots, awards, code..." autocomplete="off" autofocus /></div>
    <button class="btn" type="submit">Search</button>
  </form>
  <p id="search-status" class="fine" aria-live="polite"></p>
  <ol id="search-results" class="result-list"></ol>
  <noscript><p class="fine">Search needs JavaScript. Here is every page instead:</p><ul class="plain-list">{items}</ul></noscript>
</div></section>
</main>'''
    out = head(title, desc, "search.html", 0, noindex=True) + top + "\n" + body + "\n" + bottom + tail(0)
    out = out.replace('<body class="">', '<body class="" data-search-page="1">', 1)
    (SRC / "search.html").write_text(out, encoding="utf-8")


def all_pages_for_noscript():
    out = [("Home", "index.html")]
    for n in TOP_PAGES[1:]:
        out.append((CRUMB_NAMES.get(n, n.title()), f"{n}.html"))
    out.append(("Code", "code.html"))
    out += [(r["title"], f"code/{r['slug']}.html") for r in REPOS]
    return out


# ---------------------------------------------------------------- search index
class Text(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.skip = 0
        self.main = False
        self.chunks = []
        self.heads = []
        self._h = None

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style", "svg", "noscript", "header", "footer", "nav"):
            self.skip += 1
        if tag == "main":
            self.main = True
        if tag in ("h2", "h3") and self.main:
            self._h = []

    def handle_endtag(self, tag):
        if tag in ("script", "style", "svg", "noscript", "header", "footer", "nav") and self.skip:
            self.skip -= 1
        if tag in ("h2", "h3") and self._h is not None:
            h = " ".join("".join(self._h).split())
            if h:
                self.heads.append(h)
            self._h = None
        if tag == "main":
            self.main = False

    def handle_data(self, data):
        if self.skip or not self.main:
            return
        if self._h is not None:
            self._h.append(data)
        s = " ".join(data.split())
        if s:
            self.chunks.append(s)


def clean(s):
    return " ".join(html.unescape(re.sub(r"<[^>]+>", " ", s)).split())


def build_index():
    entries = []
    for n in TOP_PAGES:
        t = (SRC / f"{n}.html").read_text(encoding="utf-8")
        title = clean(re.search(r"<title>(.*?)</title>", t, re.S).group(1)).split(" | ")[0]
        if n == "index":
            title = "Home"
        desc = clean(re.search(r'<meta name="description" content="([^"]*)"', t).group(1))
        px = Text()
        px.feed(t)
        body = " ".join(px.chunks)[:2200]
        entries.append({"t": title, "u": "index.html" if n == "index" else f"{n}.html", "d": desc,
                        "k": " ".join(px.heads[:20]), "b": body, "c": "Page"})
        if n == "robots":
            for m in re.finditer(r'<article id="(\w+)" class="robot[^"]*">(.*?)</article>', t, re.S):
                h2 = re.search(r"<h2>(.*?)</h2>", m.group(2), re.S)
                kick = re.search(r'<p class="kicker">(.*?)</p>', m.group(2), re.S)
                para = re.search(r"</p>\s*<h2>.*?</h2>\s*<p>(.*?)</p>", m.group(2), re.S)
                tags = re.findall(r"<li>(.*?)</li>", m.group(2), re.S)
                entries.append({"t": clean(h2.group(1)) + " (" + clean(kick.group(1)) + ")", "u": f"robots.html#{m.group(1)}",
                                "d": clean(para.group(1)) if para else "", "k": " ".join(clean(x) for x in tags),
                                "b": "", "c": "Robot"})
    entries.append({"t": "Code", "u": "code.html", "d": "Open-source code from FRC Team 1661: robots, vision, dashboards, diagrams and websites.",
                    "k": "github open source repositories repos", "b": "", "c": "Page"})
    for r in REPOS:
        entries.append({"t": r["title"], "u": f'code/{r["slug"]}.html', "d": r["summary"],
                        "k": " ".join([r["repo"], r["lang"], r["year"], r["season"]] + r["tags"]),
                        "b": " ".join(r["highlights"]), "c": "Code",
                        "n": 1 if (r.get("fork") or r.get("archived")) else 0})
    (SRC / "assets" / "search-index.json").write_text(json.dumps(entries, separators=(",", ":"), ensure_ascii=False), encoding="utf-8")
    print("search index:", len(entries), "entries")
    return entries


def sitemap():
    pri = {"index": "1.0", "robots": "0.9", "join": "0.9", "awards": "0.8", "outreach": "0.7", "sponsors": "0.7", "media": "0.6"}
    rows = [("/", "1.0")] + [(f"/{n}.html", pri[n]) for n in TOP_PAGES[1:]] + [("/code.html", "0.8")]
    rows += [(f"/code/{r['slug']}.html", "0.6" if r["group"] == "robot" else "0.5") for r in REPOS]
    xml = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for path, p in rows:
        xml.append(f"  <url><loc>{SITE}{path}</loc><lastmod>{TODAY}</lastmod><priority>{p}</priority></url>")
    xml.append("</urlset>")
    (SRC / "sitemap.xml").write_text("\n".join(xml) + "\n", encoding="utf-8")


HEADERS = """# Netlify headers (see https://docs.netlify.com/routing/headers/)
/*
  X-Content-Type-Options: nosniff
  Referrer-Policy: strict-origin-when-cross-origin
  X-Frame-Options: SAMEORIGIN
  Permissions-Policy: camera=(), microphone=(), geolocation=()

/assets/images/*
  Cache-Control: public, max-age=2592000

/assets/webfontkit-20240125-184607/*
  Cache-Control: public, max-age=31536000, immutable

/assets/style.css
  Cache-Control: public, max-age=3600

/assets/*.js
  Cache-Control: public, max-age=3600

/assets/search-index.json
  Cache-Control: public, max-age=3600
"""


def main():
    patch_existing()
    top, bottom, gh_icon = chrome()
    for r in REPOS:
        repo_page(r, top, bottom, gh_icon)
    code_index(top, bottom, gh_icon)
    search_page(top, bottom)
    build_index()
    sitemap()
    (SRC / "_headers").write_text(HEADERS, encoding="utf-8")
    print("generated", len(REPOS), "repo pages + code.html + search.html + sitemap + _headers")


if __name__ == "__main__":
    main()

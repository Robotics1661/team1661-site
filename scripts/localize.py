#!/usr/bin/env python3
"""Generate the Spanish (/es/) and Simplified Chinese (/zh/) copies of the site.

The English pages in src/ are the source of truth. This script reads them, swaps every piece of
visible text for its translation from scripts/i18n/<lang>.tsv, fixes asset paths, and writes the
result to src/<lang>/ (mirroring the folder layout). It is called from build.py, but can also be run:

    python3 scripts/localize.py            # build es + zh (fails if a translation is missing)
    python3 scripts/localize.py --dump     # write every English string to scripts/i18n/_en.txt
    python3 scripts/localize.py --missing  # list strings that have no translation yet

Translation files are "english<TAB>translation", one per line. Inline links and emphasis inside a
sentence are written as <1>...</1> markers (so word order can change); <o1/> marks an opaque item
such as a line break. A translation of "=" means "keep the English text".
"""
import copy
import html
import json
import re
import sys
from collections import Counter
from pathlib import Path

from bs4 import BeautifulSoup, Comment, NavigableString, Tag

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
I18N = Path(__file__).resolve().parent / "i18n"
SITE = "https://team1661.com"

LANGS = {
    "en": {"html": "en", "og": "en_US", "name": "English", "short": "EN", "menu": "Language"},
    "es": {"html": "es", "og": "es_ES", "name": "Español", "short": "ES", "menu": "Idioma"},
    "zh": {"html": "zh-Hans", "og": "zh_CN", "name": "简体中文", "short": "中文", "menu": "语言"},
}
TARGETS = ["es", "zh"]
HREFLANG = {"en": "en", "es": "es", "zh": "zh-Hans"}

INLINE = {"a", "strong", "em", "b", "i", "span", "small", "abbr", "sup", "sub", "mark", "time", "u", "s"}
OPAQUE = {"svg", "code", "kbd", "br", "img", "input", "wbr", "pre"}
SKIP = {"script", "style"}
ATTRS = ("alt", "aria-label", "title", "placeholder")
META_NAMES = {"description", "twitter:title", "twitter:description", "twitter:image:alt"}
META_PROPS = {"og:title", "og:description", "og:image:alt"}
LETTERS = re.compile(r"[A-Za-zÀ-ɏ]")
TOKEN = re.compile(r"(<o\d+/>|</?\d+>)")
GLOBE = ('<svg class="icon" viewBox="0 0 24 24" aria-hidden="true" focusable="false"><g fill="none" stroke="currentColor" '
         'stroke-width="2" stroke-linecap="round"><circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3c2.6 2.7 4 5.7 4 9s-1.4 6.3-4 9c-2.6-2.7-4-5.7-4-9s1.4-6.3 4-9z"/></g></svg>')

DETECT_SCRIPT = ('<script id="lang-detect">(function(){try{var s=localStorage.getItem("lang");if(!s){var l=navigator.languages&&'
                 'navigator.languages.length?navigator.languages:[navigator.language||"en"];for(var i=0;i<l.length;i++){'
                 'var c=String(l[i]).toLowerCase().split("-")[0];if(c==="en"||c==="es"||c==="zh"){s=c;break}}}'
                 'if(s==="es"||s==="zh")location.replace("/"+s+location.pathname+location.search+location.hash)}catch(e){}})()</script>')


# ------------------------------------------------------------------ url helpers
def page_url_path(rel_path):
    """'index.html' -> '/', 'code/x.html' -> '/code/x.html'"""
    return "/" if rel_path == "index.html" else "/" + rel_path


def lang_path(rel_path, lang):
    p = page_url_path(rel_path)
    if lang == "en":
        return p
    return f"/{lang}/" if p == "/" else f"/{lang}{p}"


def lang_menu(rel_path, lang):
    items = []
    for code in ("en", "es", "zh"):
        cur = ' aria-current="true"' if code == lang else ""
        items.append(f'<li><a href="{lang_path(rel_path, code)}" hreflang="{HREFLANG[code]}" lang="{HREFLANG[code]}" '
                     f'data-lang="{code}"{cur}>{LANGS[code]["name"]}</a></li>')
    return (f'<details class="lang-menu"><summary aria-label="{LANGS[lang]["menu"]}">{GLOBE}<span>{LANGS[lang]["short"]}</span></summary>'
            f'<ul class="lang-list">{"".join(items)}</ul></details>')


def hreflang_links(rel_path):
    out = []
    for code in ("en", "es", "zh"):
        out.append(f'<link rel="alternate" hreflang="{HREFLANG[code]}" href="{SITE}{lang_path(rel_path, code)}" />')
    out.append(f'<link rel="alternate" hreflang="x-default" href="{SITE}{lang_path(rel_path, "en")}" />')
    return "\n".join(out)


def decorate_english(text, rel_path):
    """Idempotently add the language menu, hreflang links and language detection to an English page."""
    t = text
    t = re.sub(r'<details class="lang-menu">.*?</details>', "", t, flags=re.S)
    t = re.sub(r'\n?<link rel="alternate" hreflang="[^"]*" href="[^"]*" />', "", t)
    t = re.sub(r'\n?<script id="lang-detect">.*?</script>', "", t, flags=re.S)
    t = t.replace('<link rel="icon"', hreflang_links(rel_path) + '\n<link rel="icon"', 1)
    # detection runs before first paint, right after the theme script
    t = re.sub(r'(<script>document\.documentElement\.classList\.add\("js"\);.*?</script>)', lambda m: m.group(1) + "\n" + DETECT_SCRIPT, t, count=1, flags=re.S)
    t = re.sub(r'(</button>)(\s*)(</div>\s*</header>)', lambda m: m.group(1) + "\n    " + lang_menu(rel_path, "en") + m.group(2) + m.group(3), t, count=1)
    return t


# ------------------------------------------------------------------ translation tables
def load_table(lang):
    table = {}
    f = I18N / f"{lang}.tsv"
    if not f.exists():
        return table
    for n, line in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip() or line.startswith("#"):
            continue
        if "\t" not in line:
            raise SystemExit(f"{f.name}:{n}: expected key<TAB>translation")
        k, v = line.split("\t", 1)
        table[k] = v
    return table


def tokens(s):
    return Counter(TOKEN.findall(s))


# ------------------------------------------------------------------ unit extraction
def has_letters(s):
    return bool(LETTERS.search(s))


def is_inline(n):
    return isinstance(n, NavigableString) or (isinstance(n, Tag) and (n.name in INLINE or n.name in OPAQUE))


def block_descendant_with_text(n):
    for d in n.descendants:
        if isinstance(d, Tag) and d.name not in INLINE and d.name not in OPAQUE and d.name not in SKIP:
            if has_letters(d.get_text()):
                return True
    return False


def run_text_outside_opaque(nodes):
    for n in nodes:
        if isinstance(n, Comment):
            continue
        if isinstance(n, NavigableString) and str(n).strip():
            return True
    return False


class Walker:
    def __init__(self, soup, table, record):
        self.soup, self.table, self.record = soup, table, record  # record(key) is called for every unit

    def children_runs(self, parent):
        run = []
        for c in list(parent.children):
            if isinstance(c, Comment):
                continue
            if isinstance(c, Tag) and (c.name in SKIP or "lang-menu" in (c.get("class") or [])):
                self.flush(parent, run)
                run = []
                continue
            if is_inline(c) and not (isinstance(c, Tag) and c.name in INLINE and block_descendant_with_text(c)):
                run.append(c)
            else:
                self.flush(parent, run)
                run = []
                if isinstance(c, Tag):
                    self.children_runs(c)
        self.flush(parent, run)

    def flush(self, parent, run):
        if not run:
            return
        # leading / trailing whitespace and opaque nodes are left in place
        while run and ((isinstance(run[0], NavigableString) and not str(run[0]).strip()) or (isinstance(run[0], Tag) and run[0].name in OPAQUE)):
            run = run[1:]
        while run and ((isinstance(run[-1], NavigableString) and not str(run[-1]).strip()) or (isinstance(run[-1], Tag) and run[-1].name in OPAQUE)):
            run = run[:-1]
        if not run:
            return
        if not run_text_outside_opaque(run):
            # only inline wrappers (e.g. <a>..</a><a>..</a>): handle each wrapper on its own
            for c in run:
                if isinstance(c, Tag) and c.name in INLINE:
                    self.children_runs(c)
            return
        self.unit(parent, run)

    def unit(self, parent, run):
        tags, opq, parts = [], [], []

        def rec(n):
            if isinstance(n, Comment):
                return
            if isinstance(n, NavigableString):
                parts.append(str(n))
            elif n.name in OPAQUE:
                opq.append(n)
                parts.append(f"<o{len(opq)}/>")
            else:
                tags.append(n)
                i = len(tags)
                parts.append(f"<{i}>")
                for c in n.children:
                    rec(c)
                parts.append(f"</{i}>")

        for n in run:
            rec(n)
        key = " ".join("".join(parts).split())
        if not has_letters(re.sub(r"<[^>]+>", "", key)):
            return
        self.record(key)
        tr = self.table.get(key) if self.table is not None else None
        if tr is None or tr == "=":
            return
        new_nodes = self.rebuild(tr, tags, opq)
        first = run[0]
        for nn in new_nodes:
            first.insert_before(nn)
        for n in run:
            n.extract()

    def rebuild(self, tr, tags, opq):
        root, stack = [], []

        def add(node):
            (stack[-1] if stack else None)
            if stack:
                stack[-1].append(node)
            else:
                root.append(node)

        for piece in TOKEN.split(tr):
            if not piece:
                continue
            m = re.fullmatch(r"<(\d+)>", piece)
            if m:
                src = tags[int(m.group(1)) - 1]
                t = self.soup.new_tag(src.name)
                t.attrs = dict(src.attrs)
                add(t)
                stack.append(t)
                continue
            if re.fullmatch(r"</\d+>", piece):
                stack.pop()
                continue
            m = re.fullmatch(r"<o(\d+)/>", piece)
            if m:
                add(copy.copy(opq[int(m.group(1)) - 1]))
                continue
            add(NavigableString(piece))
        return root


def walk_units(soup, table, record):
    w = Walker(soup, table, record)
    if soup.title is not None:
        w.children_runs(soup.title)
    if soup.body is not None:
        w.children_runs(soup.body)


def walk_attrs(soup, table, record):
    def tr(val):
        v = " ".join(val.split())
        if not has_letters(v):
            return None
        record(v)
        t = table.get(v) if table is not None else None
        return None if t in (None, "=") else t

    for tag in soup.find_all(True):
        if tag.name in SKIP or tag.find_parent(class_="lang-menu") is not None:
            continue
        for a in ATTRS:
            if tag.has_attr(a) and isinstance(tag[a], str):
                t = tr(tag[a])
                if t is not None:
                    tag[a] = t
        if tag.name == "meta" and tag.has_attr("content"):
            if tag.get("name") in META_NAMES or tag.get("property") in META_PROPS:
                t = tr(tag["content"])
                if t is not None:
                    tag["content"] = t
        if tag.has_attr("data-text") and "type" in (tag.get("class") or []):
            t = tr(tag["data-text"])
            if t is not None:
                tag["data-text"] = t


def jsonld_strings(obj, out):
    """Collect translatable strings from a JSON-LD object."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            if isinstance(v, str) and (k == "description" or (k == "name" and obj.get("@type") in ("ListItem", "CollectionPage"))):
                if has_letters(v):
                    out.append(v)
            else:
                jsonld_strings(v, out)
    elif isinstance(obj, list):
        for v in obj:
            jsonld_strings(v, out)


def localize_jsonld(obj, table, lang):
    if isinstance(obj, dict):
        for k, v in list(obj.items()):
            if isinstance(v, str):
                if k == "description" or (k == "name" and obj.get("@type") in ("ListItem", "CollectionPage")):
                    t = table.get(v)
                    if t and t != "=":
                        obj[k] = t
                elif k == "inLanguage":
                    obj[k] = HREFLANG[lang]
                elif k in ("url", "item", "urlTemplate") and v.startswith(SITE + "/") and "/assets/" not in v:
                    path = v[len(SITE):]
                    obj[k] = SITE + (f"/{lang}/" if path == "/" else f"/{lang}{path}")
            else:
                localize_jsonld(v, table, lang)
    elif isinstance(obj, list):
        for v in obj:
            localize_jsonld(v, table, lang)


# ------------------------------------------------------------------ one page
def english_pages():
    pages = sorted(SRC.glob("*.html")) + sorted((SRC / "code").glob("*.html"))
    return [(p, p.relative_to(SRC).as_posix()) for p in pages]


def collect(soup):
    keys = []
    walk_units(soup, None, keys.append)
    walk_attrs(soup, None, keys.append)
    for s in soup.find_all("script", type="application/ld+json"):
        try:
            jsonld_strings(json.loads(s.string), keys)
        except (ValueError, TypeError):
            pass
    return keys


def prefix_assets(text):
    text = re.sub(r'(href|src)="((?:\.\./)?assets/)', lambda m: f'{m.group(1)}="../{m.group(2)}', text)
    text = text.replace("url(assets/", "url(../assets/")
    return text


def localize_page(rel_path, lang, table):
    src = (SRC / rel_path).read_text(encoding="utf-8")
    soup = BeautifulSoup(src, "html.parser")
    # translate text, attributes and structured data
    walk_units(soup, table, lambda k: None)
    walk_attrs(soup, table, lambda k: None)
    for s in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(s.string)
        except (ValueError, TypeError):
            continue
        localize_jsonld(data, table, lang)
        s.string = json.dumps(data, separators=(",", ":"), ensure_ascii=False)
    # filter text on the code index also needs the visible (translated) words
    for card in soup.select("article.repo-card[data-text]"):
        card["data-text"] = (card["data-text"] + " " + " ".join(card.get_text(" ").split()).lower()).strip()
    # language-specific head bits
    soup.html["lang"] = LANGS[lang]["html"]
    url = SITE + lang_path(rel_path, lang)
    for tag in soup.find_all("link", rel="canonical"):
        tag["href"] = url
    for m in soup.find_all("meta", property="og:url"):
        m["content"] = url
    for m in soup.find_all("meta", property="og:locale"):
        m["content"] = LANGS[lang]["og"]
        for other in ("en", "es", "zh"):
            if other != lang:
                n = soup.new_tag("meta", property="og:locale:alternate", content=LANGS[other]["og"])
                m.insert_after(n)
                m.insert_after(NavigableString("\n"))
    for l in soup.find_all("link", rel="alternate", hreflang=True):
        l.extract()
    first_icon = soup.find("link", rel="icon")
    for frag in BeautifulSoup(hreflang_links(rel_path), "html.parser").find_all("link"):
        first_icon.insert_before(frag)
        first_icon.insert_before(NavigableString("\n"))
    for s in soup.find_all("script", id="lang-detect"):
        s.extract()
    for d in soup.select("details.lang-menu"):
        d.replace_with(BeautifulSoup(lang_menu(rel_path, lang), "html.parser"))
    out = str(soup).replace(" viewbox=", " viewBox=")  # html.parser lower-cases this SVG attribute
    out = prefix_assets(out)
    if rel_path == "404.html":
        # the 404 page can be served from any depth, so its links must not be relative
        out = re.sub(r'(href|src)="(?:\.\./)*(?!https?:|#|/|mailto:)([^"]+)"', lambda m: f'{m.group(1)}="/{m.group(2)}"', out)
        out = out.replace('"/assets/', '"/assets/').replace('href="/index.html"', f'href="/{lang}/"')
        out = re.sub(r'href="/(robots|code|awards|sponsors|media|join)\.html"', lambda m: f'href="/{lang}/{m.group(1)}.html"', out)
        out = out.replace('href="/"', f'href="/{lang}/"')
    return out


def build_lang(lang, table, allow_missing=False):
    missing = []
    seen = set()
    for p, rel_path in english_pages():
        soup = BeautifulSoup(p.read_text(encoding="utf-8"), "html.parser")
        for k in collect(soup):
            if k not in table and k not in seen:
                seen.add(k)
                missing.append(k)
    if missing and not allow_missing:
        raise SystemExit(f"{lang}: {len(missing)} strings have no translation (run: python3 scripts/localize.py --missing)")
    n = 0
    outdir = SRC / lang
    for p, rel_path in english_pages():
        out = localize_page(rel_path, lang, table)
        dest = outdir / rel_path
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(out, encoding="utf-8")
        n += 1
    return n, missing


def validate(lang, table):
    bad = []
    for k, v in table.items():
        if v != "=" and tokens(k) != tokens(v):
            bad.append(k)
    return bad


def all_keys():
    seen, ordered = set(), []
    for p, rel_path in english_pages():
        soup = BeautifulSoup(p.read_text(encoding="utf-8"), "html.parser")
        for k in collect(soup):
            if k not in seen:
                seen.add(k)
                ordered.append(k)
    return ordered


def main(argv):
    if "--dump" in argv:
        keys = all_keys()
        I18N.mkdir(exist_ok=True)
        (I18N / "_en.txt").write_text("\n".join(f"{i}|{k}" for i, k in enumerate(keys, 1)) + "\n", encoding="utf-8")
        print(len(keys), "strings written to scripts/i18n/_en.txt")
        return
    if "--missing" in argv:
        keys = all_keys()
        for lang in TARGETS:
            t = load_table(lang)
            miss = [k for k in keys if k not in t]
            print(f"{lang}: {len(miss)} missing of {len(keys)}")
            for k in miss[:int(argv[argv.index("--limit") + 1]) if "--limit" in argv else 40]:
                print("   ", k[:110])
        return
    for lang in TARGETS:
        t = load_table(lang)
        bad = validate(lang, t)
        if bad:
            raise SystemExit(f"{lang}: marker mismatch in {len(bad)} strings, first: {bad[0][:90]}")
        n, _ = build_lang(lang, t, allow_missing="--allow-missing" in argv)
        print(f"{lang}: wrote {n} pages")


if __name__ == "__main__":
    main(sys.argv[1:])

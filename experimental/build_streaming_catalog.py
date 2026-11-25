#!/usr/bin/env python3
"""Genera un'anteprima dei cataloghi pubblici Sky Cinema e Sky Serie."""
import json
import re
import time
import urllib.parse
import urllib.request
from html.parser import HTMLParser
from pathlib import Path

SKY_PAGES = {
    "Sky Cinema": ("https://programmi.sky.it/film/tutti", "movie", "film", "tutti"),
    "Sky Serie": ("https://programmi.sky.it/serie-tv/tutte", "series", "serie-tv", "tutte"),
}
SKIP_SLUGS = {
    "drammatici", "drammatiche", "romantici", "romantiche", "crime",
    "commedia", "thriller", "fantascienza", "azione", "animazione",
    "generi", "tutti", "tutte", "next",
}
UA = {"User-Agent": "Mozilla/5.0 (compatible; CatalogoStreamingPreview/1.0)"}

def get_text(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=35) as response:
        return response.read().decode("utf-8", "replace")

class SkyParser(HTMLParser):
    def __init__(self, kind):
        super().__init__(convert_charrefs=True)
        self.kind = kind
        self.items = {}
        self.current = None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "a":
            href = attrs.get("href", "")
            path = urllib.parse.urlparse(href).path
            prefix = "/film/" if self.kind == "movie" else "/serie-tv/"
            if prefix in path and path.rstrip("/") != prefix.rstrip("/"):
                slug = path.rstrip("/").rsplit("/", 1)[-1].lower()
                if slug in SKIP_SLUGS or re.fullmatch(r"(tutti|tutte)-\d+", slug):
                    self.current = None
                    return
                self.current = {
                    "slug": slug,
                    "url": urllib.parse.urljoin("https://programmi.sky.it", href),
                    "poster": "",
                }
        elif tag == "img" and self.current:
            poster = (attrs.get("src") or attrs.get("data-src")
                      or attrs.get("data-lazy-src")
                      or attrs.get("srcset", "").split(" ")[0])
            if poster:
                self.current["poster"] = urllib.parse.urljoin("https://programmi.sky.it", poster)

    def handle_endtag(self, tag):
        if tag == "a" and self.current:
            item = self.current
            title = re.sub(r"[-_]+", " ", item["slug"]).strip().title()
            if title and len(title) < 180:
                item["title"] = title
                self.items[item["url"]] = item
            self.current = None

def load_sky_catalog(label, base_url, kind, route, page_name):
    found = {}
    for page_no in range(0, 11):
        url = base_url if page_no == 0 else f"https://programmi.sky.it/{route}/{page_name}-{page_no}"
        parser = SkyParser(kind)
        parser.feed(get_text(url))
        before = len(found)
        found.update(parser.items)
        added = len(found) - before
        if page_no > 0 and added == 0:
            break
    return [{
        "provider": label, "provider_name": label, "kind": kind,
        "title": item["title"], "year": "", "poster": item["poster"],
        "url": item["url"],
    } for item in found.values()]

def main():
    report = {
        "generated": time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime()),
        "sky": {}, "errors": [],
    }
    groups = {}
    for label, (url, kind, route, page_name) in SKY_PAGES.items():
        try:
            items = load_sky_catalog(label, url, kind, route, page_name)
            groups[label] = items
            report["sky"][label] = {"items_found": len(items), "source": url}
        except Exception as exc:
            groups[label] = []
            report["sky"][label] = {"error": str(exc), "source": url}
            report["errors"].append(f"{label}: {type(exc).__name__}: {exc}")

    all_items = groups.get("Sky Cinema", []) + groups.get("Sky Serie", [])
    Path("streaming-catalog.json").write_text(
        json.dumps({"items": all_items, "report": report}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    nav = "".join(
        f'<button onclick="show(\'{label}\')">{label} <span>{len(items)}</span></button>'
        for label, items in groups.items()
    )
    payload = json.dumps(groups, ensure_ascii=False).replace("</", "<\\/")
    page = """<!doctype html><html lang="it"><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Catalogo Sky — anteprima</title>
<style>
*{box-sizing:border-box}body{margin:0;background:#101114;color:#eee;font:15px system-ui}
header{padding:20px;background:#1a1b20;position:sticky;top:0;z-index:2}
h1{font-size:22px;margin:0 0 5px}small{color:#aaa}
nav{display:flex;gap:7px;flex-wrap:wrap;margin-top:14px}
button{background:#30323a;color:white;border:0;border-radius:7px;padding:9px 13px;cursor:pointer}
button.active{background:#0878d1}button span{opacity:.7}
input{margin:14px 0 4px;padding:10px;width:min(100%,420px);border:0;border-radius:6px}
.grid{padding:16px;display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:12px}
.card{display:grid;grid-template-columns:90px 1fr;gap:12px;background:#1d1f25;border-radius:9px;padding:10px;min-height:130px}
.card img{width:90px;aspect-ratio:2/3;object-fit:cover;border-radius:5px}
.noimg{width:90px;color:#777;font-size:11px}.info{min-width:0}
.info a{color:#fff;text-decoration:none}.info small{display:block;margin-top:5px}
</style>
<header><h1>Catalogo Sky — anteprima</h1>
<small id="count">Cataloghi aggiornati automaticamente</small><nav>""" + nav + """</nav>
<input id="q" placeholder="Cerca un titolo…"></header>
<div style="padding:0 16px 12px;color:#aaa;font-size:12px">Dati ricavati dalle pagine pubbliche del catalogo Sky. La copertura dipende dai titoli effettivamente esposti da quelle pagine.</div>
<main class="grid" id="grid"></main><script>
const DATA=""" + payload + """;
let active='Sky Cinema';
function show(p){active=p;document.querySelectorAll('button').forEach(b=>b.classList.toggle('active',b.textContent.startsWith(p)));render()}
function esc(s){return String(s||'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]))}
function render(){let q=document.getElementById('q').value.toLocaleLowerCase('it');let a=(DATA[active]||[]).filter(x=>x.title.toLocaleLowerCase('it').includes(q));document.getElementById('count').textContent=a.length+' titoli · '+active;document.getElementById('grid').innerHTML=a.map(x=>{let img=x.poster?'<img src="'+esc(x.poster)+'" loading="lazy" alt="">':'<div class="noimg">Locandina non disponibile</div>';return '<article class="card">'+img+'<div class="info"><b><a target="_blank" rel="noopener" href="'+esc(x.url||'#')+'">'+esc(x.title)+'</a></b><small>'+esc(x.provider_name||active)+' · '+(x.kind==='movie'?'Film':'Serie TV')+'</small></div></article>'}).join('')||'<p>Nessun titolo trovato.</p>'}
document.getElementById('q').addEventListener('input',render);show(active);
</script></html>"""
    Path("streaming-preview.html").write_text(page, encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()

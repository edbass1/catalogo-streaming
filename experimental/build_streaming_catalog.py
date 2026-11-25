#!/usr/bin/env python3
"""Genera un'anteprima dei cataloghi pubblici Sky Cinema e Sky Serie."""
import html
import json
import re
import time
import urllib.parse
import urllib.request
from html.parser import HTMLParser
from pathlib import Path

SKY_PAGES = {
    "Sky Cinema": ("https://programmi.sky.it/film/tutti", "movie"),
    "Sky Serie": ("https://programmi.sky.it/serie-tv/tutte", "series"),
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
            prefix = "/film/" if self.kind == "movie" else "/serie-tv/"
            if href.startswith(prefix) and href.rstrip("/") != prefix.rstrip("/"):
                url = urllib.parse.urljoin("https://programmi.sky.it", href)
                self.current = {
                    "title": attrs.get("aria-label") or attrs.get("title") or "",
                    "url": url,
                    "poster": "",
                    "description": "",
                }
        elif tag == "img" and self.current:
            self.current["poster"] = (
                attrs.get("src") or attrs.get("data-src")
                or attrs.get("data-lazy-src")
                or attrs.get("srcset", "").split(" ")[0]
            )
            alt = attrs.get("alt", "").strip()
            if alt and not self.current["title"]:
                self.current["title"] = alt

    def handle_data(self, data):
        if self.current:
            value = re.sub(r"\\s+", " ", data).strip()
            if value:
                self.current["title"] = (self.current["title"] + " " + value).strip()

    def handle_endtag(self, tag):
        if tag == "a" and self.current:
            item = self.current
            item["title"] = re.sub(r"\\s+", " ", item["title"]).strip()
            if item["title"] and len(item["title"]) < 180:
                self.items[item["url"]] = item
            self.current = None


def load_sky_catalog(label, url, kind):
    parser = SkyParser(kind)
    parser.feed(get_text(url))
    return [{
        "provider": label,
        "provider_name": label,
        "kind": kind,
        "title": item["title"],
        "year": "",
        "poster": item["poster"],
        "url": item["url"],
        "description": item["description"],
    } for item in parser.items.values()]


def main():
    report = {
        "generated": time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime()),
        "sky": {},
        "errors": [],
    }
    groups = {}
    for label, (url, kind) in SKY_PAGES.items():
        try:
            items = load_sky_catalog(label, url, kind)
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
.note{padding:0 16px 12px;color:#aaa;font-size:12px}
</style>
<header><h1>Catalogo Sky — anteprima</h1>
<small id="count">Cataloghi aggiornati automaticamente</small><nav>""" + nav + """</nav>
<input id="q" placeholder="Cerca un titolo…"></header>
<div class="note">Dati ricavati dalle pagine pubbliche del catalogo Sky. La copertura dipende dai titoli effettivamente esposti da quelle pagine.</div>
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

#!/usr/bin/env python3
"""Build a preview of Sky / Netflix catalogs without API keys.

Netflix availability is resolved through StreamX (Cinemeta discovery +
JustWatch availability). This is a popularity-based index, NOT a guaranteed
complete provider catalog. Sky entries are read from Sky's public catalog pages.
"""
import concurrent.futures
import html
import json
import re
import time
import urllib.parse
import urllib.request
from html.parser import HTMLParser
from pathlib import Path

STREAMX = "https://api.streamx.qzz.io"
SKY_PAGES = {
    "Sky Cinema": "https://programmi.sky.it/film/tutti",
    "Sky Serie": "https://programmi.sky.it/serie-tv/tutte",
}
MAX_PER_TYPE = 400
MAX_PAGES = 12
WORKERS = 8
UA = {"User-Agent": "Mozilla/5.0 (compatible; CatalogoStreamingPreview/1.0)"}


def get_json(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=35) as r:
        return json.loads(r.read().decode("utf-8"))


def get_text(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=35) as r:
        return r.read().decode("utf-8", "replace")


def streamx_catalog(kind):
    rows, seen, skip = [], set(), 0
    for _ in range(MAX_PAGES):
        data = get_json(f"{STREAMX}/catalog/{kind}/top?skip={skip}")
        metas = data.get("metas") or []
        if not metas:
            break
        fresh = 0
        for m in metas:
            ident = str(m.get("id") or m.get("imdb_id") or "").strip()
            if ident and ident not in seen:
                seen.add(ident)
                rows.append(m)
                fresh += 1
        if fresh == 0 or len(rows) >= MAX_PER_TYPE:
            break
        skip += len(metas)
        if len(metas) < 2:
            break
        time.sleep(0.15)
    return rows[:MAX_PER_TYPE]


def check_streaming(kind, meta):
    ident = str(meta.get("id") or meta.get("imdb_id") or "").strip()
    if not ident:
        return None
    try:
        data = get_json(f"{STREAMX}/streaming/{kind}/{urllib.parse.quote(ident, safe='')}?country=IT")
        providers = data.get("providers") or []
        netflix = [p for p in providers if re.search(r"netflix", p.get("name", ""), re.I)]
        out = []
        for provider in netflix:
            out.append({
                "provider": "Netflix",
                "provider_name": provider.get("name", ""),
                "kind": kind,
                "id": ident,
                "title": meta.get("name") or meta.get("title") or ident,
                "year": meta.get("year") or "",
                "poster": meta.get("poster") or f"https://api.streamx.qzz.io/img/poster/medium/{ident}/img",
                "url": provider.get("webUrl") or data.get("justWatchUrl") or "",
                "quality": provider.get("quality") or "",
                "offer": ", ".join(provider.get("types") or []),
            })
        return out
    except Exception as e:
        return {"_error": f"{ident}: {type(e).__name__}: {e}"}


class SkyParser(HTMLParser):
    def __init__(self, kind):
        super().__init__()
        self.kind = kind
        self.items = {}
        self.current = None

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "a":
            href = a.get("href", "")
            prefix = "/film/" if self.kind == "movie" else "/serie-tv/"
            if href.startswith(prefix) and href.rstrip("/") != prefix.rstrip("/"):
                self.current = {"title": "", "url": urllib.parse.urljoin("https://programmi.sky.it", href),
                                "poster": "", "description": a.get("aria-label") or a.get("title") or ""}
        elif tag == "img" and self.current:
            self.current["poster"] = a.get("src") or a.get("data-src") or a.get("srcset", "").split(" ")[0]
            if not self.current["title"]:
                self.current["title"] = a.get("alt", "")

    def handle_data(self, data):
        if self.current:
            self.current["title"] += (" " if self.current["title"] else "") + data.strip()

    def handle_endtag(self, tag):
        if tag == "a" and self.current:
            item = self.current
            item["title"] = re.sub(r"\s+", " ", item["title"]).strip()
            if item["title"] and len(item["title"]) < 180:
                self.items[item["url"]] = item
            self.current = None


def sky_catalog(label, url, kind):
    parser = SkyParser(kind)
    parser.feed(get_text(url))
    return [{
        "provider": label, "kind": kind, "title": x["title"], "year": "",
        "poster": x["poster"], "url": x["url"], "description": x["description"],
        "provider_name": label, "quality": "", "offer": "Catalogo ufficiale Sky"
    } for x in parser.items.values()]


def card(x):
    title = html.escape(str(x.get("title") or ""))
    poster = html.escape(str(x.get("poster") or ""), quote=True)
    url = html.escape(str(x.get("url") or "#"), quote=True)
    year = html.escape(str(x.get("year") or ""))
    label = html.escape(str(x.get("provider_name") or x.get("provider") or ""))
    kind = "Film" if x.get("kind") == "movie" else "Serie TV"
    desc = html.escape(str(x.get("description") or ""))
    img = f'<img src="{poster}" loading="lazy" alt="">' if poster else '<div class="noimg">Nessuna locandina</div>'
    return f'<article class="card">{img}<div class="info"><b><a href="{url}" target="_blank" rel="noopener">{title}</a></b><small>{label} · {kind} {year}</small><p>{desc}</p></div></article>'


def main():
    report = {"generated": time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime()),
              "streamx": {}, "sky": {}, "errors": []}
    streaming_rows = []
    for kind in ("movie", "series"):
        try:
            metas = streamx_catalog(kind)
            report["streamx"][kind] = {"discovered": len(metas)}
            with concurrent.futures.ThreadPoolExecutor(max_workers=WORKERS) as pool:
                results = list(pool.map(lambda m: check_streaming(kind, m), metas))
            for result in results:
                if isinstance(result, dict) and result.get("_error"):
                    report["errors"].append(result["_error"])
                elif result:
                    streaming_rows.extend(result)
            report["streamx"][kind]["matches"] = sum(x["kind"] == kind for x in streaming_rows)
        except Exception as e:
            report["errors"].append(f"StreamX {kind}: {type(e).__name__}: {e}")
            report["streamx"][kind] = {"error": str(e)}

    sky_rows = []
    for label, url in SKY_PAGES.items():
        kind = "movie" if label == "Sky Cinema" else "series"
        try:
            items = sky_catalog(label, url, kind)
            report["sky"][label] = {"items_found": len(items), "source": url}
            sky_rows.extend(items)
        except Exception as e:
            report["sky"][label] = {"error": str(e), "source": url}
            report["errors"].append(f"{label}: {type(e).__name__}: {e}")

    rows = streaming_rows + sky_rows
    rows.sort(key=lambda x: (x.get("provider", ""), x.get("kind", ""), str(x.get("title", "")).casefold()))
    Path("streaming-catalog.json").write_text(json.dumps({"items": rows, "report": report}, ensure_ascii=False, indent=2), encoding="utf-8")

    groups = {p: [x for x in rows if x.get("provider") == p] for p in ("Sky Cinema", "Sky Serie", "Netflix")}
    nav = "".join(f'<button onclick="show(\'{p}\')">{p} <span>{len(v)}</span></button>' for p, v in groups.items())
    payload = json.dumps(groups, ensure_ascii=False).replace("</", "<\\/")
    page = """<!doctype html><html lang="it"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Catalogo Streaming — anteprima</title><style>
*{box-sizing:border-box}body{margin:0;background:#101114;color:#eee;font:15px system-ui}header{padding:20px;background:#1a1b20;position:sticky;top:0;z-index:2}h1{font-size:22px;margin:0 0 5px}small{color:#aaa}nav{display:flex;gap:7px;flex-wrap:wrap;margin-top:14px}button{background:#30323a;color:white;border:0;border-radius:7px;padding:9px 13px;cursor:pointer}button.active{background:#e50914}button span{opacity:.7}input{margin:14px 0 4px;padding:10px;width:min(100%,420px);border:0;border-radius:6px}.grid{padding:16px;display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:12px}.card{display:grid;grid-template-columns:90px 1fr;gap:12px;background:#1d1f25;border-radius:9px;padding:10px;min-height:130px}.card img{width:90px;aspect-ratio:2/3;object-fit:cover;border-radius:5px}.noimg{width:90px;color:#777;font-size:11px}.info{min-width:0}.info a{color:#fff;text-decoration:none}.info small{display:block;margin-top:5px}.info p{font-size:12px;color:#aaa;margin:7px 0}.note{padding:0 16px 12px;color:#aaa;font-size:12px}
</style><header><h1>Catalogo Streaming — anteprima</h1><small id="count">Cataloghi aggiornati automaticamente</small><nav>""" + nav + """</nav><input id="q" placeholder="Cerca un titolo…"></header><div class="note">Netflix: titoli individuati nel catalogo popolare Cinemeta e verificati per l'Italia tramite StreamX/JustWatch. Non è garantita la copertura completa. Sky: elenco pubblico del sito ufficiale Sky.</div><main class="grid" id="grid"></main><script>
const DATA=""" + payload + """;
let active='Netflix';
function show(p){active=p;document.querySelectorAll('button').forEach(b=>b.classList.toggle('active',b.textContent.startsWith(p)));render()}
function render(){let q=document.getElementById('q').value.toLocaleLowerCase('it');let a=(DATA[active]||[]).filter(x=>x.title.toLocaleLowerCase('it').includes(q));document.getElementById('count').textContent=a.length+' titoli · '+active;document.getElementById('grid').innerHTML=a.map(x=>{let img=x.poster?'<img src="'+esc(x.poster)+'" loading="lazy">':'<div class="noimg">Locandina non disponibile</div>';return '<article class="card">'+img+'<div class="info"><b><a target="_blank" rel="noopener" href="'+esc(x.url||'#')+'">'+esc(x.title)+'</a></b><small>'+esc(x.provider_name||active)+' · '+(x.kind==='movie'?'Film':'Serie TV')+' '+esc(x.year||'')+'</small><p>'+esc(x.description||'')+'</p></div></article>'}).join('')||'<p>Nessun titolo trovato.</p>'}
function esc(s){return String(s||'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]))}
document.getElementById('q').addEventListener('input',render);show(active);
</script></html>"""
    Path("streaming-preview.html").write_text(page, encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

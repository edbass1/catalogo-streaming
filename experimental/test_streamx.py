#!/usr/bin/env python3
"""Diagnostica StreamX: campione di catalogo + disponibilita Netflix/Prime in Italia.

Non modifica index.html o catalogo.json. Serve solo a verificare se StreamX
puo alimentare i due nuovi cataloghi; il campione NON rappresenta il catalogo completo.
"""
import concurrent.futures
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

BASE = "https://api.streamx.qzz.io"
SAMPLE_PER_TYPE = 12
UA = {"User-Agent": "catalogo-streaming-source-check/1.0"}


def get_json(path):
    req = urllib.request.Request(BASE + path, headers=UA)
    with urllib.request.urlopen(req, timeout=25) as response:
        return json.loads(response.read().decode("utf-8"))


def catalog_sample(kind):
    data = get_json(f"/catalog/{kind}/top?skip=0")
    metas = data.get("metas", [])
    return metas[:SAMPLE_PER_TYPE]


def title_id(meta):
    return str(meta.get("id") or meta.get("imdb_id") or "").strip()


def check_availability(kind, meta):
    ident = title_id(meta)
    if not ident:
        return {"title": meta.get("name") or meta.get("title"), "error": "ID assente"}
    try:
        data = get_json(
            f"/streaming/{kind}/{urllib.parse.quote(ident, safe='')}?country=IT"
        )
        providers = data.get("providers", [])
        names = [p.get("name", "") for p in providers]
        netflix = [p for p in providers if re.search(r"netflix", p.get("name", ""), re.I)]
        prime = [
            p for p in providers
            if re.search(r"prime video|amazon prime", p.get("name", ""), re.I)
        ]
        return {
            "id": ident,
            "title": meta.get("name") or meta.get("title"),
            "year": meta.get("year"),
            "poster": meta.get("poster"),
            "netflix": netflix,
            "prime_video": prime,
            "providers_seen": names,
            "matched": data.get("matched"),
            "error": None,
        }
    except Exception as exc:
        return {
            "id": ident,
            "title": meta.get("name") or meta.get("title"),
            "error": f"{type(exc).__name__}: {exc}",
        }


def main():
    report = {
        "source": BASE,
        "country": "IT",
        "sample_per_type": SAMPLE_PER_TYPE,
        "warning": "Campione dei titoli top di Cinemeta, non catalogo completo Netflix/Prime.",
        "results": {},
    }
    for kind in ("movie", "series"):
        try:
            sample = catalog_sample(kind)
        except Exception as exc:
            report["results"][kind] = {"catalog_error": f"{type(exc).__name__}: {exc}"}
            continue
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
            rows = list(pool.map(lambda m: check_availability(kind, m), sample))
        report["results"][kind] = {
            "sample_count": len(sample),
            "checked_count": len(rows),
            "netflix_matches": sum(bool(x.get("netflix")) for x in rows),
            "prime_matches": sum(bool(x.get("prime_video")) for x in rows),
            "errors": sum(bool(x.get("error")) for x in rows),
            "items": rows,
        }
        time.sleep(1)

    Path("streamx-test-report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Proof-of-concept catalog fetcher for Netflix and Prime Video Italy.

Requires TMDB_READ_ACCESS_TOKEN (TMDB v4 Read Access Token).
Writes a separate JSON file; it does not modify the live catalog.
TMDB watch-provider availability is powered by JustWatch; attribution is required.
"""
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

API = "https://api.themoviedb.org/3"
REGION = "IT"
LANGUAGE = "it-IT"
OUT = Path(__file__).resolve().parent.parent / "catalogo_extra.json"
PAGE_LIMIT = max(1, min(int(os.environ.get("TMDB_TEST_PAGES", "5")), 500))
TOKEN = os.environ.get("TMDB_READ_ACCESS_TOKEN", "").strip()

# Names are resolved against the provider list for Italy; no provider IDs guessed.
TARGETS = {
    "Netflix Italia": {"netflix"},
    "Prime Video Italia": {"amazon prime video", "prime video"},
}
GENRES = {
    "movie": {28: "Azione", 12: "Avventura", 16: "Animazione", 35: "Commedia",
             80: "Crime", 99: "Documentario", 18: "Dramma", 10751: "Famiglia",
             14: "Fantasy", 36: "Storia", 27: "Horror", 10402: "Musica",
             9648: "Mistero", 10749: "Romantico", 878: "Fantascienza",
             10770: "Film TV", 53: "Thriller", 10752: "Guerra", 37: "Western"},
    "tv": {10759: "Action & Adventure", 16: "Animazione", 35: "Commedia",
           80: "Crime", 99: "Documentario", 18: "Dramma", 10751: "Famiglia",
           10762: "Kids", 9648: "Mistero", 10763: "News", 10764: "Reality",
           10765: "Sci-fi & Fantasy", 10766: "Soap", 10767: "Talk",
           10768: "War & Politics", 37: "Western"},
}

def api(path, params=None):
    query = urllib.parse.urlencode(params or {})
    url = API + path + ("?" + query if query else "")
    req = urllib.request.Request(url, headers={
        "Authorization": "Bearer " + TOKEN,
        "accept": "application/json",
        "User-Agent": "catalogo-streaming-test/1.0",
    })
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=30) as response:
                return json.load(response)
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", "replace")[:400]
            if exc.code == 429 and attempt < 2:
                time.sleep(3 * (attempt + 1))
                continue
            raise RuntimeError(f"TMDB HTTP {exc.code}: {body}") from exc
        except Exception:
            if attempt == 2:
                raise
            time.sleep(2)

def resolve_providers():
    data = api("/watch/providers/movie", {"watch_region": REGION, "language": LANGUAGE})
    results = data.get("results", [])
    resolved = {}
    for label, aliases in TARGETS.items():
        candidates = [p for p in results if p.get("provider_name", "").strip().lower() in aliases]
        if candidates:
            # Keep the exact provider returned for the Italian region.
            resolved[label] = candidates[0]
    missing = sorted(set(TARGETS) - set(resolved))
    if missing:
        print("Provider non risolti per IT:", ", ".join(missing), file=sys.stderr)
    return resolved

def collect(provider_id, media_type):
    path = "/discover/movie" if media_type == "movie" else "/discover/tv"
    pages = []
    for page in range(1, PAGE_LIMIT + 1):
        data = api(path, {
            "language": LANGUAGE,
            "region": REGION,
            "watch_region": REGION,
            "with_watch_providers": provider_id,
            "with_watch_monetization_types": "flatrate",
            "sort_by": "popularity.desc",
            "include_adult": "false",
            "page": page,
        })
        pages.extend(data.get("results", []))
        if page >= data.get("total_pages", 0):
            break
        time.sleep(0.25)
    out = []
    genre_map = GENRES[media_type]
    for item in pages:
        title = item.get("title") if media_type == "movie" else item.get("name")
        date = item.get("release_date") if media_type == "movie" else item.get("first_air_date")
        tmdb_id = item.get("id")
        if not title or not tmdb_id:
            continue
        out.append({
            "id": f"tmdb-{media_type}-{tmdb_id}",
            "type": "film" if media_type == "movie" else "serie",
            "title": title,
            "orig": item.get("original_title") if media_type == "movie" else item.get("original_name", ""),
            "year": (date or "")[:4],
            "url": f"https://www.themoviedb.org/{media_type}/{tmdb_id}?language=it-IT",
            "poster": ("https://image.tmdb.org/t/p/w342" + item["poster_path"]) if item.get("poster_path") else "",
            "desc": item.get("overview", ""),
            "genres": [genre_map[g] for g in item.get("genre_ids", []) if g in genre_map],
            "rating": item.get("vote_average"),
            "votes": item.get("vote_count"),
            "provider_id": provider_id,
        })
    # Stable deduplication by TMDB id.
    unique = {e["id"]: e for e in out}
    return list(unique.values())

def main():
    if not TOKEN:
        raise SystemExit("Manca TMDB_READ_ACCESS_TOKEN. Imposta il Read Access Token TMDB come variabile d'ambiente.")
    providers = resolve_providers()
    catalog = {
        "region": REGION,
        "language": LANGUAGE,
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "pages_per_category": PAGE_LIMIT,
        "attribution": "Streaming availability powered by JustWatch via TMDB. Metadata and images: TMDB.",
        "sections": {},
    }
    for label, provider in providers.items():
        pid = provider["provider_id"]
        entries = []
        for media_type in ("movie", "tv"):
            entries.extend(collect(pid, media_type))
        catalog["sections"][label] = entries
        print(f"{label}: provider_id={pid}, {len(entries)} titoli (limite {PAGE_LIMIT} pagine per tipo)")
    OUT.write_text(json.dumps(catalog, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"JSON di prova scritto: {OUT}")

if __name__ == "__main__":
    main()

#!/bin/bash
# Aggiorna il catalogo. Dati IMDb riscaricati se più vecchi di 7 giorni.
cd "$(dirname "$0")"; mkdir -p imdb
for f in title.ratings title.basics title.akas; do
  if [ -z "$(find imdb/$f.tsv.gz -mtime -7 2>/dev/null)" ]; then curl -sf -o imdb/$f.tsv.gz.tmp https://datasets.imdbws.com/$f.tsv.gz && mv imdb/$f.tsv.gz.tmp imdb/$f.tsv.gz; fi
done
python3 build.py >> build.log 2>&1

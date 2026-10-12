# Catalogo streaming gratuito: RaiPlay · RSI Play · LA7 Cinema

Pagina statica che si aggiorna ogni giorno da sola (GitHub Actions, ore 04:17 UTC) e raccoglie i cataloghi di:

- **RaiPlay**: Film, Serie italiane e Teche Rai (ultimi titoli aggiunti)
- **RSI Play**: Film e Serie TV
- **LA7 Cinema**: film disponibili su RivediLa7 (sezione La7 Cinema)

Per ogni piattaforma ci sono le sottosezioni **Voto IMDb**, **Prime visioni / novità**, **Per genere** e **IL CLOU**
(almeno 50.000 voti su IMDb, oppure presente nelle classifiche della piattaforma con voto ≥ 6,5).
I generi sentimentale/romantico, bambini/animazione, azione e reality vengono esclusi sempre.

Voti IMDb: abbinamento automatico (titolo + anno) con i
[dataset gratuiti IMDb](https://datasets.imdbws.com/). Gli abbinamenti possono contenere errori.

## Uso in locale
```
./run.sh        # scarica i dati IMDb se servono e genera index.html + catalogo.json
```
Serve solo Python 3 (nessuna libreria esterna).

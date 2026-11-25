# Verifica fonti per i nuovi cataloghi

Il branch `test-cataloghi-tmdb` è separato da `main`: il sito pubblicato non viene modificato finché la raccolta non è verificata.

## Netflix Italia e Prime Video Italia

- [Netflix su JustWatch](https://www.justwatch.com/it/provider/netflix)
- [Prime Video su JustWatch](https://www.justwatch.com/it/provider/amazon-prime-video)
- [Netflix su Streamingfilter](https://streamingfilter.com/it/catalogo-netflix)
- [Prime Video su Streamingfilter](https://streamingfilter.com/it/catalogo-prime-video)

**Esito: non usare scraping di JustWatch.** Le pagine sono consultabili pubblicamente e mostrano cataloghi paginati, ma i Termini di JustWatch vietano espressamente scraping, data mining e raccolta automatizzata non autorizzata. Non è quindi una fonte corretta da automatizzare per questo sito senza autorizzazione.

Streamingfilter dichiara di usare dati TMDB e disponibilità JustWatch tramite TMDB; non offre, nelle pagine pubbliche consultate, un feed/API aperto documentato per riutilizzare il catalogo. Copiare/scrapare anche questo sito non è una soluzione verificata.

## Sky Italia

Fonti ufficiali consultate:
- [Programmi Sky](https://programmi.sky.it/): catalogo editoriale con schede di film e serie, descrizioni e stagioni.
- [Canali Sky](https://www.sky.it/tv/canali): conferma l'offerta di canali Cinema e Intrattenimento.
- [Guida Sky Cinema](https://assistenza.sky.it/programmazione/guida-sky-cinema): descrive i canali Sky Cinema e i contenuti on demand.

**Limite:** il catalogo editoriale di programmi.sky.it non equivale a un feed completo e documentato del palinsesto lineare. Non ho verificato un endpoint/feed pubblico stabile che permetta di importare automaticamente tutte le schede e i relativi poster. Non va confuso il catalogo on demand con gli orari di trasmissione dei canali.

## Conclusione tecnica

Con i vincoli attuali (nessun token, nessuna credenziale e nessuno scraping contrario ai termini), non è stata verificata una fonte automatizzabile e riutilizzabile per i cataloghi completi Netflix e Prime Video. Per Sky esiste una fonte editoriale ufficiale consultabile, ma non è ancora verificato un feed automatico stabile.

Non aggiungere scraper basati su HTML non documentato né modificare il workflow di produzione finché non esiste una fonte utilizzabile e testata. Il codice del sito pubblicato resta invariato.

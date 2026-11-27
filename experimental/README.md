# Verifica fonti per i nuovi cataloghi

Il branch `test-cataloghi-tmdb` è separato da `main`: il sito pubblicato non viene modificato finché la raccolta non è verificata.

## Netflix Italia e Prime Video Italia

- [Netflix Lovers – Catalogo Netflix Italia](https://www.netflixlovers.it/catalogo-netflix-italia): fonte indicata dall'utente e verificata. La pagina dichiara 8.858 titoli complessivi, 5.074 film e 2.869 serie TV (valori mostrati al momento della consultazione); offre filtri per titolo, genere, tag, audio, sottotitoli e anno.
- [Netflix su JustWatch](https://www.justwatch.com/it/provider/netflix)
- [Prime Video su JustWatch](https://www.justwatch.com/it/provider/amazon-prime-video)
- [Netflix su Streamingfilter](https://streamingfilter.com/it/catalogo-netflix)
- [Prime Video su Streamingfilter](https://streamingfilter.com/it/catalogo-prime-video)

**Netflix Lovers è una fonte catalografica molto più pertinente** di quelle individuate in precedenza. Tuttavia, il footer della stessa pagina vieta espressamente la riproduzione e l'estrazione, anche tramite software automatici, senza autorizzazione. Quindi non posso implementare uno scraper automatico senza prima ottenere il permesso del gestore. La pagina può essere proposta come collegamento esterno nel sito, ma questo non equivale a importarne titoli, descrizioni o immagini.

**Esito JustWatch:** non usare scraping. Le pagine sono consultabili pubblicamente, ma i Termini vietano raccolta automatizzata non autorizzata.

Streamingfilter dichiara di usare dati TMDB e disponibilità JustWatch tramite TMDB; non offre, nelle pagine pubbliche consultate, un feed/API aperto documentato per riutilizzare il catalogo. Copiare/scrapare anche questo sito non è una soluzione verificata.

## Sky Italia

Fonti ufficiali consultate:
- [Programmi Sky](https://programmi.sky.it/): catalogo editoriale con schede di film e serie, descrizioni e stagioni.
- [Canali Sky](https://www.sky.it/tv/canali): conferma l'offerta di canali Cinema e Intrattenimento.
- [Guida Sky Cinema](https://assistenza.sky.it/programmazione/guida-sky-cinema): descrive i canali Sky Cinema e i contenuti on demand.

**Limite:** il catalogo editoriale di programmi.sky.it non equivale a un feed completo e documentato del palinsesto lineare. Non ho verificato un endpoint/feed pubblico stabile che permetta di importare automaticamente tutte le schede e i relativi poster. Non va confuso il catalogo on demand con gli orari di trasmissione dei canali.

## Conclusione tecnica

Con i vincoli attuali (nessun token, nessuna credenziale e nessuno scraping contrario ai termini), Netflix Lovers è una fonte utile per il catalogo Netflix ma richiede autorizzazione per l'estrazione automatica. Non è stata ancora verificata una fonte automatizzabile e riutilizzabile per Prime Video. Per Sky esiste una fonte editoriale ufficiale consultabile, ma non è ancora verificato un feed automatico stabile.

Non aggiungere scraper basati su HTML non documentato né modificare il workflow di produzione finché non esiste una fonte utilizzabile e testata. Il codice del sito pubblicato resta invariato.

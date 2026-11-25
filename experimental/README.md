# Fonti senza token: JustWatch e Sky

Il branch `test-cataloghi-tmdb` è un branch di lavoro separato e non modifica il sito pubblicato.

## Netflix Italia e Prime Video Italia

Fonti pubbliche verificate:
- Netflix: https://www.justwatch.com/it/provider/netflix
- Prime Video: https://www.justwatch.com/it/provider/amazon-prime-video

Le pagine pubbliche presentano catalogo, film/serie e paginazione. Sono consultabili senza account o token. La raccolta automatica dal sito può essere fragile e va verificata sul markup effettivo; non è un'API ufficiale né garantita. Prima dell'integrazione va controllato il rispetto dei termini e un limite di richieste ragionevole.

Pagine film dedicate:
- https://www.justwatch.com/it/provider/netflix/film
- https://www.justwatch.com/it/provider/amazon-prime-video/film

## Sky Italia

Fonte primaria:
- https://programmi.sky.it/

Il sito ufficiale espone schede editoriali di film e serie TV, descrizioni e stagioni. È una fonte adatta a un primo test di raccolta pubblica, ma non è confermato un feed/API aperto con l'intero catalogo e la programmazione lineare di tutti i canali Sky.

Per distinguere i due obiettivi:
1. catalogo editoriale Sky (film e serie pubblicati su programmi.sky.it);
2. palinsesto dei canali Sky Cinema e Intrattenimento (film/episodi trasmessi e orari).

La seconda parte richiede una guida TV/palinsesto accessibile e verificabile, non va dedotta dal catalogo editoriale.

## Stato

- Il prototipo TMDB con token è stato rimosso perché l'utente non vuole credenziali.
- Nessun cambiamento è stato pubblicato sul branch `main`.
- Prima di aggiungere scraper o workflow, occorre testare il markup pubblico in un ambiente con accesso web, salvare dati di esempio e verificare titoli, URL, poster e paginazione.

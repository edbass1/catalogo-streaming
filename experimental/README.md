# Test cataloghi streaming TMDB Italia

Questo prototipo è isolato nel branch `test-cataloghi-tmdb`: non modifica il sito pubblicato né il workflow attuale.

## Cosa prova
- Risolve i provider Netflix e Prime Video dalla lista TMDB per la regione italiana (IT), senza hardcodare gli ID.
- Recupera film e serie TV in modalità abbonamento (`flatrate`), in italiano.
- Scrive `catalogo_extra.json` separato dal catalogo attuale.

## Avvio locale
1. Crea un account TMDB e richiedi una API key / Read Access Token dalle impostazioni API.
2. Imposta il token nell'ambiente, senza inserirlo nel repository:
   ```bash
   export TMDB_READ_ACCESS_TOKEN='il_tuo_read_access_token'
   ```
3. Esegui:
   ```bash
   python3 experimental/catalogo_streaming_tmdb.py
   ```

Per il test iniziale scarica fino a 5 pagine per tipo (film e serie, 20 risultati per pagina). Si può aumentare `TMDB_TEST_PAGES` dopo aver verificato risposta e limiti API.

## Nota
La disponibilità streaming in TMDB è fornita da JustWatch e richiede attribuzione. Il prototipo non viene ancora eseguito da GitHub Actions e non è integrato in `index.html`: prima va verificata la qualità e la copertura dei dati. Sky canali lineari (palinsesto Sky Cinema/Intrattenimento) resta una fonte separata da risolvere.

# Fork dello Studio — cosa cambia rispetto a `capazme/mcp-legal-it`

Questo fork esiste per far girare il server come **servizio remoto su Coolify**
(connettore MCP per Claude), non come plugin locale. Le differenze sono tre e
sono tutte qui sotto: tenerle poche e circoscritte serve a poter fare
`git merge upstream/main` senza soffrire.

Sincronizzare con l'upstream:

```bash
git remote add upstream https://github.com/capazme/mcp-legal-it.git   # una volta sola
git fetch upstream && git merge upstream/main
```

I conflitti possibili sono solo in `pyproject.toml` e `Dockerfile`. Dopo un
merge, **ricontrollare per prima cosa il punto 1**.

---

## 1. Pin di FastMCP a 2.x — `pyproject.toml`

L'upstream dichiara `fastmcp>=2.0,<4`, che oggi risolve a **FastMCP 3.x**, dove
l'attributo `include_tags` **non esiste più**. Il codice di `src/server.py`
continua a impostarlo (`mcp.include_tags = _PROFILES[_profile]`) e Python non
protesta, perché assegnare un attributo inesistente a un oggetto è legittimo:
semplicemente **non filtra più niente**. Effetto pratico: `LEGAL_PROFILE` viene
accettato senza errori e il server espone comunque tutti e 218 i tool.

È un guasto silenzioso, e costoso: 218 tool sono ~260 KB di schema JSON
(~66k token) che il client si carica **a ogni connessione**, anche senza usarne
uno. Con il pin a `fastmcp>=2.11,<3` il filtro torna a funzionare.

Il `Dockerfile` verifica la versione dopo l'installazione e **fallisce il build**
se non è una 2.x, così il problema non può tornare di nascosto.

> Se un domani si vuole passare a FastMCP 3.x, il filtro va riscritto con l'API
> nuova: non basta togliere il pin.

## 2. `serve_studio.py` — entrypoint con `/healthz` e `LEGAL_TAGS`

File **aggiunto** (l'upstream non lo ha), usato dal `CMD` del Dockerfile al posto
di `run_server.py`. Fa le stesse cose, più:

- **`/healthz`** — FastMCP espone solo `/mcp`, e una GET su `/mcp` risponde
  `406 Not Acceptable`. Senza una rotta dedicata non è possibile alcun
  healthcheck: né quello di Coolify (che fa rollback del deploy se il container
  non diventa *healthy*), né il monitor che avvisa su Telegram.
  Risponde con lo stato, i tag attivi e **quanti tool** ne risultano — così si
  verifica a colpo d'occhio che il filtro abbia fatto presa.

- **`LEGAL_TAGS`** — elenco libero di tag separati da virgola, ha la precedenza
  su `LEGAL_PROFILE`. Serve perché i profili predefiniti dell'upstream
  (`sinistro`, `credito`, `penale`, `fiscale`, `normativa`, `privacy`, `studio`,
  `redattore`, `cowork`) sono combinazioni fisse, nessuna delle quali corrisponde
  a quello che serve a uno studio civile e penale.

  Tag disponibili: `giurisprudenza`, `costituzionale`, `giurisprudenza_amm`,
  `giurisprudenza_ue`, `normativa`, `consob`, `giudiziario`, `scadenze`,
  `interessi`, `rivalutazione`, `danni`, `credito`, `sinistro`, `penale`,
  `lavoro`, `parcelle_avv`, `parcelle_prof`, `utility`, `proprieta`, `atti`,
  `privacy`, `fiscale`, `investimenti`, `societario`, `crisi_impresa`.

## 3. `Dockerfile` — `curl`, `LEGAL_TAGS`, entrypoint

- installa **`curl`**: l'healthcheck di Coolify lo esegue *dentro* il container e
  `python:3.12-slim` non ha né curl né wget → *unhealthy* → rollback del deploy;
- imposta `LEGAL_TAGS` col preset in uso (sovrascrivibile da Coolify senza rebuild);
- verifica il pin di FastMCP (punto 1);
- lancia `serve_studio.py` invece di `run_server.py`.

---

## Note sul deploy (Coolify)

- Risorsa di tipo **application**, build pack **dockerfile**, che builda da
  questa repo: `git push` → deploy automatico.
- Perché il preset non finisca murato nell'immagine, `LEGAL_TAGS` è impostata
  **anche** come variabile d'ambiente della risorsa: quella vince sull'`ENV` del
  Dockerfile, quindi cambiare selezione = cambiare la variabile e rideployare,
  senza rebuild e senza toccare il codice.
- ⚠️ I tool che generano documenti (`genera_modello_atto`, `esporta_atto_docx`,
  `genera_procura_liti_docx`, …) scrivono il file in `/tmp/mcp-legal-it`
  **dentro il container** e restituiscono un path del filesystem: da remoto quel
  file è irraggiungibile. Servirebbe un endpoint di download. Per questo il tag
  `atti` è fuori dal preset.

<!-- deploy automatico verificato dal server il 2026-08-13 -->

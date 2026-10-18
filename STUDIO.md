# Fork dello Studio — cosa cambia rispetto a `capazme/mcp-legal-it`

Questo fork esiste per far girare il server come **servizio remoto su Coolify**
(connettore MCP per Claude), non come plugin locale. Dal 2026-10-18 contiene
**solo la giurisprudenza di Cassazione** (Italgiure): il resto è stato tolto e
andrà in un progetto separato (§ 9 e `SPLIT.md`).

Sincronizzare con l'upstream: l'upstream ha **riscritto la sua storia git**
(gli hash non coincidono più e non c'è un antenato comune), e questo fork ha
comunque perso quasi tutti i file dell'upstream. `git merge upstream/main` non
serve più: si confrontano e si portano a mano i soli file tenuti (elenco e
procedura al § 9.3). Dopo ogni allineamento **ricontrollare per prima cosa il
punto 1**.

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

- **Trasporto senza stato** e **`malloc_trim` dopo ogni tool** — contro la
  memoria che cresceva finche' il container non veniva ucciso (§ 8).
  `MCP_STATELESS=0` riporta alle sessioni senza toccare il codice.

## 3. `Dockerfile` — `curl`, `LEGAL_TAGS`, entrypoint

- installa **`curl`**: l'healthcheck di Coolify lo esegue *dentro* il container e
  `python:3.12-slim` non ha né curl né wget → *unhealthy* → rollback del deploy;
- imposta `LEGAL_TAGS` vuota: tutti gli 8 tool (sovrascrivibile da Coolify senza rebuild);
- verifica il pin di FastMCP (punto 1);
- lancia `serve_studio.py` invece di `run_server.py`.

---

## Note sul deploy (Coolify)

- Risorsa di tipo **application**, build pack **dockerfile**, che builda da
  questa repo: `git push` → deploy automatico.
- `LEGAL_TAGS` è impostata **anche** come variabile d'ambiente della risorsa, col
  vecchio preset dello studio. Contiene `giurisprudenza`, quindi espone comunque
  tutti gli 8 tool (verificato con `/healthz`): si può lasciare o togliere.

## 4. Testo integrale delle sentenze dal PDF ufficiale (Italgiure)

**Il problema.** Il campo `ocr` dell'indice pubblico SentenzeWeb e' **troncato alla
fonte**, e il taglio cade in coda — cioe' dentro il P.Q.M. Su 30 sentenze civili
campionate il 2026-08-13, **29 finivano a meta' parola**. Per Cass. civ. sez. III
n. 29253/2024 l'indice si fermava a:

> «...il procedimento speciale di intimazione di sfratto per **mo**

mentre il principio di diritto per intero e':

> «...il procedimento speciale di intimazione di sfratto per morosita' di cui
> all'art. 658 c.p.c. **e' applicabile anche al contratto di affitto di azienda**
> (o di ramo di azienda) che comprenda uno o piu' beni immobili».

Cioe' spariva esattamente la regola di diritto: l'unica cosa che si cita in un atto.

**La soluzione.** `leggi_sentenza` ora scarica il **PDF ufficiale** e ne estrae il
testo (`pypdf`), usandolo al posto dell'indice quando e' almeno altrettanto
completo. Il PDF e' pubblico e senza credenziali come il resto di SentenzeWeb.

- L'URL non si indovina: il documento Solr porta un campo **`filename`** col
  percorso esatto. Unica accortezza, l'estensione va portata a `.clean.pdf` —
  con `.pdf` l'endpoint risponde 500 (verificato su civile e penale).
- L'output dichiara sempre **`Fonte del testo`**: `PDF ufficiale (testo integrale)`
  oppure `indice SentenzeWeb`, in quest'ultimo caso con l'avviso del troncamento.
- Il link al PDF e' in fondo alla risposta, per il riscontro da tenere agli atti.
- Se il PDF non arriva o non e' leggibile si ripiega sull'indice: **il tool non
  fallisce mai per questo**.
- Il campo `ocrdis` (dispositivo) e' troncato allo stesso modo: quando si sta
  gia' servendo il PDF, la sezione "Dispositivo" viene omessa invece di ripetere
  un testo mozzato che ingannerebbe chi legge solo quella.

**Limite che resta**: l'archivio pubblico copre **dal 2021 in avanti** (civile
188.630 provvedimenti, penale 236.093). Prima del 2021 non c'e' nulla, e non ci
sono ne' le massime del CED ne' la giurisprudenza di merito.

## 5-7. Danni, compensi forensi, allineamento v2.12.1 — spostati

Le correzioni dei §§ 5-6 (risarcimento danni, tabelle del DM 55/2014) e il
resoconto del merge della v2.12.1 (§ 7) riguardano tool che non sono più in
questo server. Il testo integrale resta nella versione precedente di questo file:

```bash
git show 64f288d:STUDIO.md
```

ed è il punto di partenza obbligato per il progetto parallelo: sono correzioni
che l'upstream **non ha** (vedi `SPLIT.md`).

## 8. Memoria che cresceva: sessioni mai chiuse e picchi della Consulta (2026-09-18)

**Il sintomo.** Dopo 12 giorni di uptime il processo era a **470 MB** di memoria anonima,
il container aveva toccato il limite di 512 MB **4.222 volte** ed era vicino all'OOM.
Dopo un redeploy sullo stesso commit ripartiva da ~98 MB. In media ~30 MB al giorno.

Riprodotto su un container di prova con la stessa immagine: le cause sono **due**,
indipendenti, e la media dei 30 MB al giorno le mescolava.

### 8.1 Le sessioni MCP non venivano mai chiuse (la crescita lineare)

Ogni connessione di Claude apre una sessione MCP nuova: `initialize`, `tools/list`,
`prompts/list`, `resources/list`, e poi eventualmente i tool. **Non la chiude mai**: nei
log non compare nessuna `DELETE /mcp`. FastMCP 2.x crea il gestore delle sessioni
dell'SDK **senza** `session_idle_timeout` (l'SDK lo supporta, FastMCP 2.x non lo
passa), quindi ogni sessione restava in memoria per sempre.

Quanto pesa ciascuna: il "router" dei messaggi della sessione resta sospeso in attesa
del messaggio successivo, che non arriva mai, e la sua variabile di ciclo tiene in vita
**l'ultimo messaggio inviato**. Misurato:

| Ultimo messaggio della sessione | Memoria trattenuta per sempre |
|---|---:|
| `resources/list` (la sequenza reale di Claude) | 62 KB |
| `tools/list` (schema dei 58 tool) | 266 KB |
| `leggi_sentenza` (testo integrale) | 432 KB |

Controprova: 200 sessioni come quelle della seconda riga, ma chiuse con `DELETE`,
lasciano 6 KB ciascuna.

**La correzione**: `stateless_http=True` in `serve_studio.py`. Ogni richiesta ha il suo
trasporto, che muore con lei. Nessun tool usa funzioni di sessione (campionamento,
elicitation, notifiche di progresso, sottoscrizioni: verificato con `grep`), quindi non
si perde nulla. 300 connessioni in fila: **+62 KB ciascuna prima, 0 dopo**.

Effetti visibili dal client, tutti conformi alla specifica: le risposte non portano
piu' l'intestazione `mcp-session-id`; un ID di sessione vecchio (quelli che Claude
ricorda dopo un deploy) viene ignorato invece di dare 404; `DELETE` risponde 405.
`MCP_STATELESS=0` (variabile d'ambiente della risorsa Coolify + redeploy) torna alle
sessioni senza toccare il codice.

### 8.2 I picchi della Corte costituzionale restavano "prenotati" (lo scalino)

*(Storico: la Corte costituzionale non è più in questo server. Resta valido il
`malloc_trim` dopo ogni tool, descritto qui.)*

La prima ricerca alla Consulta dopo un deploy (e di nuovo a cache scaduta, dopo 7
giorni) scarica l'archivio 2001-oggi: **56 MB** di ZIP, **~218 MB** di JSON, che
`_unzip_decade` decodificava **tutti insieme** anche per cercare in un solo anno.
Picco: **358 MB** di oggetti vivi. Finita la chiamata gli oggetti vivi tornano a
**200 KB**, ma il processo resta a **~400 MB**: glibc tiene per se' la memoria liberata
e non la rende al sistema. Le massime (`pronunce_cost_su_norma`) fanno lo stesso con
~111 MB di JSON (processo a ~248 MB).

Due correzioni:

- **`malloc_trim(0)` dopo ogni tool** (`serve_studio.py`, middleware
  `_RestituisciMemoria`): rende al sistema la memoria libera. Costa ~1 ms, 20 ms su
  un heap frammentato da 300 MB. Fuori da glibc non fa nulla.
- **Un anno alla volta** (`lib/corte_cost/client.py`, `_iter_decade`): ogni anno va in
  cache appena decodificato e in memoria resta solo quello richiesto. Picco di oggetti
  vivi **da 358 a 110 MB**. `_unzip_decade` resta com'era per i test. File di cache e
  risposte dei tool **identici byte per byte** a prima (verificato su 26 anni di
  pronunce, una ricerca e una ricerca per norma).

| Misura (container di prova) | Prima | Dopo |
|---|---:|---:|
| Processo dopo la 1a ricerca alla Consulta | 402 MB | 92 MB |
| Processo dopo le massime | 248 MB | 96 MB |
| Picco di oggetti vivi durante il download | 358 MB | 110 MB |
| 300 connessioni di Claude in fila | +18 MB | 0 |

Test: 2.724 verdi; i 43 che falliscono falliscono identici anche su `main` senza le
modifiche (generazione di documenti in una cartella non scrivibile dall'utente di prova).

### 8.3 Come accorgersene la prossima volta

La memoria anonima del container ora deve restare **piatta attorno ai 100 MB**, con
salite solo *durante* le chiamate pesanti. Misura (sul server):

```bash
C=$(docker ps -q --filter name=gqrssuwseu2ilbzuy0fgindj)
grep ^anon /sys/fs/cgroup/system.slice/docker-$(docker inspect -f '{{.Id}}' $C).scope/memory.stat
```

Se torna a crescere, la prima cosa da guardare e' il pin di FastMCP (§ 1): la 3.x ha
un altro gestore delle sessioni e `stateless_http` va ricontrollato.

## 9. Split: solo Cassazione, e allineamento all'upstream v2.16.0 (2026-10-18)

### 9.1 Cosa resta

Il server è stato ridotto agli **8 tool di Italgiure** (`cerca_giurisprudenza`,
`leggi_sentenza`, `giurisprudenza_su_norma`, `giurisprudenza_articolo`,
`ultime_pronunce`) e di orientamento costruiti su Italgiure
(`orientamento_su_norma`, `orientamento_su_principio`, `mappa_orientamento`),
con 2 prompt e 1 risorsa. Le librerie rimaste sono quelle da cui dipendono:
`lib/italgiure`, `lib/brocardi` (massime → numeri di sentenza) e, di `lib/visualex`,
solo `map.py` e `models.py` (il resolver dei nomi degli atti, che serve a capire che
`art. 13 GDPR` è il regolamento 2016/679). Tutto il resto — 210 tool, 21 prompt,
14 risorse, il plugin con skill, comandi, agenti e hook — è elencato in `SPLIT.md`
ed è recuperabile da `main` prima dello split (commit `64f288d`).

### 9.2 Cosa arriva dall'upstream (v2.12.1 → v2.16.0)

Portati nei file tenuti, perché correggono errori che davano risposte sbagliate
senza dirlo:

- **Sezioni**: `sezione="SU"` e `sezione="T"` non esistono nell'indice (le Sezioni
  Unite sono `U`, la tributaria è la sezione 5 civile) e davano **zero risultati in
  silenzio**. Ora `resolve_sezione()` traduce gli alias e rifiuta i codici sconosciuti.
- **Materia** con più parole: `materia:responsabilita' civile` legava al campo solo la
  prima parola e la ricerca si **allargava** invece di restringersi. Ora è una frase.
- **Finestra dell'archivio**: non è "dal 2020" ma una finestra mobile di circa cinque
  anni (dal 2021). Le decisioni anteriori sono dichiarate fuori archivio invece di
  risultare "non trovate".
- **Omonimi**: con `archivio="tutti"` lo stesso numero/anno può essere una decisione
  civile e una penale; `leggi_sentenza` restituisce la prima e segnala l'altra.
- **Lettura a pagine** (`da_carattere`) e taglio "inizio + fine" oltre 30.000
  caratteri, così la parte finale (P.Q.M., principio di diritto) non si perde.
- **Ricerca per norma**: l'articolo deve stare vicino all'atto (`art. 13` entro poche
  parole da `2016/679`), invece di contare ogni `art. 13` della decisione.
- **Orientamento**: i segnali di contrasto/conformità contano decisioni distinte (non
  la somma per espressione); `discostarsi` non è più un segnale di contrasto (compare
  quasi sempre in "non vi sono ragioni per discostarsi", che dichiara conformità);
  la ricerca per principio ordina per pertinenza.
- **Brocardi**: l'atto è riconosciuto per identità (tipo, anno, numero) e non per
  sottostringa dell'etichetta: prima l'art. 18 dello Statuto dei lavoratori
  restituiva le massime della legge fallimentare. La data dell'atto arriva fino alla
  ricerca, così D.Lgs. 81/2008 e D.Lgs. 81/2015 non si confondono.
- **Cache su disco disattivabile** (`LEGAL_CACHE=off`).

### 9.3 Il punto delicato: il PDF ufficiale e la lettura a pagine

L'upstream **non ha** la correzione del § 4: continua a leggere il campo `ocr`
dell'indice, troncato alla fonte. Le due modifiche toccavano la stessa funzione
(`format_full_text`) e sono state fuse a mano:

- `format_full_text(doc, pdf_text=None, da_carattere=1)`: il testo servito è il PDF
  quando c'è (e non è più corto dell'indice), altrimenti l'indice; inizio + fine e
  finestre di `da_carattere` si calcolano **su quel testo**;
- `_leggi_sentenza_impl` scarica il PDF **anche nelle pagine successive alla prima**:
  altrimenti `da_carattere` indicherebbe posizioni del PDF applicate all'indice;
- con un formatter diverso dal testo integrale (es. il riepilogo usato da
  `giurisprudenza_articolo`) il PDF non viene scaricato.

I test in `TestFormatFullTextPdf` (`tests/unit/test_italgiure.py`) fissano questi tre
comportamenti. Esito: 440 test verdi, 32 live esclusi. I test live non sono stati
eseguiti: Italgiure non era raggiungibile dall'ambiente in cui è stato fatto lo split.
**Da fare dopo il deploy**: `leggi_sentenza(29253, 2024, archivio="civile")` deve
dichiarare "PDF ufficiale" e contenere il principio di diritto per intero.

Per i prossimi allineamenti, i file da confrontare con l'upstream sono:

```
plugin/server/src/tools/italgiure.py        (contiene modifiche [fork])
plugin/server/src/lib/italgiure/client.py   (contiene modifiche [fork])
plugin/server/src/tools/orientamento.py
plugin/server/src/lib/brocardi/
plugin/server/src/lib/visualex/map.py, models.py
plugin/server/src/lib/_http.py, _paging.py, _cache.py, _sources.py, _result.py
tests/unit/test_italgiure*.py, test_orientamento*.py, test_brocardi*.py, test_paging.py
```

con una fusione a tre vie per i due file `[fork]` (base = la versione upstream da cui
si era partiti, oggi la v2.16.0):

```bash
git fetch upstream
git merge-file <file-nostro> <copia-upstream-v2.16.0> <copia-upstream-nuova>
```

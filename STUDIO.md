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

## 5. Risarcimento danni — correzioni sostanziali (2026-08-14)

I tool `danni` dell'upstream restituivano importi **plausibili e piu' bassi del dovuto**, con
sotto la citazione dell'articolo di legge: il modo peggiore di sbagliare. Quattro correzioni.

### 5.1 Micropermanenti: la formula era sbagliata

L'upstream **sommava** il valore dei singoli punti (1%+2%+...+N%). L'art. 139 c. 6 CdA assegna
invece **un solo coefficiente al grado complessivo** di invalidita':

```
danno permanente = punto_base x coefficiente(N) x N punti x (1 - 0,005 x (eta - 10))
```

Effetto della correzione (valori DM 2026):

| Caso | Prima | Dopo |
|---|---:|---:|
| 2% a 35 anni | 1.770,25 € | 1.902,77 € |
| 6% a 40 anni | 6.387,34 € | 8.569,86 € |
| 9% a 40 anni | 11.546,35 € | 17.391,78 € |

Sul 9% erano **5.845 € in meno**, su una tabella *di legge* (vincolante per RCA e, tramite la
Gelli-Bianco, per la responsabilita' sanitaria).

### 5.2 Valori fermi al DM 2025

Aggiornati al **DM 20 luglio 2026** (GU n. 173 del 28/07/2026): primo punto **988,45 €**,
inabilita' assoluta **57,64 €**/giorno. Le parziali sono ricavate per percentuale, come vuole
l'art. 139 c. 1 lett. b), invece di essere costanti separate.

### 5.3 Macropermanenti: tetto di legge e avvertenza

- La personalizzazione era ammessa **fino al 50%**; l'art. 138 c. 3 dice **fino al 30%**.
- Il riferimento stampato in calce («Tabella unica nazionale DM 2024») era sbagliato: l'art. 138
  c. 1 richiede un **DPR**, e l'art. 1 c. 18 L. 124/2017 ne lega l'applicabilita' ai sinistri
  successivi alla sua entrata in vigore.
- I valori restano **medi indicativi** con coefficienti per eta' a scaglioni decennali: non
  riproducono ne' la TUN ne' Milano. Ora il risultato lo **dichiara** in un campo `avvertenza`.

### 5.4 Danno parentale: dalle forbici inventate al sistema a punti

L'upstream usava forbici min-max, e la «tabella di Roma» era **sintetizzata** scalando Milano
(lo diceva il file stesso: *«Nessuna tabella ufficiale Roma 2024 pubblicata»*). Sostituite con
le tabelle reali:

- **Milano** — Osservatorio giustizia civile, tabelle integrate a punti ed. 28/06/2022, in
  attuazione di **Cass. 10579/2021** (che impone il sistema a punti: le forbici non sono piu'
  un criterio conforme). Due tabelle: genitore/figlio/coniuge (valore punto 3.365,00 €, cap
  336.500,00 €) e fratello/nipote (1.461,20 €, cap 146.120,00 €). Parametri A-E.
- **Roma** — Tribunale di Roma ed. 2025, valore punto 11.549,20 €, punti per grado di parentela,
  eta' della vittima, eta' del congiunto, convivenza.

**Validazione**: l'implementazione riproduce **13 su 13** degli esempi di calcolo ufficiali
dell'Allegato 1 del PDF di Milano. Il quattordicesimo (esempio 5, ipotesi media) e' un **refuso
della fonte**: dichiara 285.025,00 € ma i suoi stessi 85 punti x 3.365,00 fanno 286.025,00 €, e
gli altri due valori dello stesso esempio tornano. Prevale l'aritmetica.

Due scelte di trasparenza: i correttivi discrezionali di Roma (riduzioni e aumenti frazionari)
**non** sono applicati d'ufficio ma elencati nella risposta; e la fascia 71-80 dell'eta' del
congiunto nella tabella di Roma vale 2,5 punti mentre nella scala della vittima vale 1,5 — pare
un refuso della fonte, ma e' riprodotto **com'e' stampato**, con avviso: correggerlo d'ufficio
significherebbe liquidare su una tabella che non esiste.

### 5.5 Le avvertenze di Cassazione spostate dentro i tool

I due prompt `analisi_sinistro` e `quantificazione_danni` contenevano avvertenze che valgono
piu' della procedura in cui erano scritte. Ma **i prompt spariscono appena si usa un filtro per
tag**: `include_tags` di FastMCP filtra tutti i componenti, e prompt e risorse non hanno tag,
quindi qualsiasi selezione li azzera (verificato: 23 prompt e 15 risorse senza filtro, 0 con).
Le avvertenze sono quindi state spostate dove viaggiano col tool.

- **`interessi_legali`** — Cass. SS.UU. 1712/1995: sui debiti di valore gli interessi
  compensativi NON si calcolano sul capitale interamente rivalutato (sovra-compensazione), ma
  sulla somma progressivamente rivalutata o sul valore medio. L'errore da evitare e' la BASE,
  non il tasso. Per i debiti di valuta non si applica.
- **`rivalutazione_monetaria`** — stessa avvertenza, piu' un campo nuovo nel risultato:
  **`base_media_per_interessi`**, che calcola la base corretta cosi' non c'e' da farlo a mano.
- **`danno_non_patrimoniale`** — Cass. SS.UU. 26972/2008 (San Martino) nella docstring, e
  rimando all'avvertenza sugli interessi nel risultato.

### 5.6 Unitarieta' del danno non patrimoniale — correzione sostanziale

`danno_non_patrimoniale` calcolava danno morale ed esistenziale come **poste autonome sommate**
al biologico, fino a +100% complessivo — mentre citava in calce, come proprio fondamento, la
sentenza che quel cumulo lo vieta. Ora le due percentuali confluiscono in **una** personalizzazione,
limitata al tetto dell'articolo applicabile (20% micro art. 139 c. 3, 30% macro art. 138 c. 3),
e il risultato dichiara quanto e' stato chiesto, quanto applicato e se e' stato ridotto.

La stessa funzione conteneva inoltre una **seconda copia della formula sbagliata** delle
micropermanenti, rimasta indietro rispetto alla correzione del punto 5.1. Ora esiste un unico
helper `_biologico_permanente()`: due copie della stessa regola sono due occasioni di sbagliare.

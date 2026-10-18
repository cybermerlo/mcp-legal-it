"""MCP Resources — guida alla ricerca giurisprudenziale su Italgiure."""

from src.server import mcp


@mcp.resource(
    "legal://riferimenti/ricerca-giurisprudenziale",
    name="Ricerca Giurisprudenziale — Guida Italgiure",
    description="Guida alla ricerca su Italgiure: strategia esplora→filtra→leggi, sintassi Solr, facets e workflow tipo",
)
def ricerca_giurisprudenziale() -> str:
    return """RICERCA GIURISPRUDENZIALE — GUIDA ALL'USO DI ITALGIURE
(Archivio Cassazione: finestra mobile di circa cinque anni, decisioni dal 2021 in poi)

═══════════════════════════════════════════════════════════
TOOL DISPONIBILI
═══════════════════════════════════════════════════════════

| Tool | Uso | Parametri chiave |
|------|-----|------------------|
| `cerca_giurisprudenza` | Ricerca full-text | query, modalita, campo, materia, sezione, tipo_provvedimento, archivio, max_risultati |
| `giurisprudenza_su_norma` | Sentenze su un articolo | riferimento, solo_sezioni_unite, anno_da, anno_a, archivio |
| `giurisprudenza_articolo` | Sentenze citate nelle massime Brocardi di un articolo | riferimento, archivio, anno_da, anno_a |
| `leggi_sentenza` | Testo completo (PDF ufficiale) | numero, anno, sezione, archivio, da_carattere |
| `ultime_pronunce` | Ultime depositate | materia, sezione, archivio |
| `orientamento_su_norma` / `orientamento_su_principio` / `mappa_orientamento` | Mappa descrittiva degli orientamenti | riferimento o principio, archivio |

═══════════════════════════════════════════════════════════
STRATEGIA: ESPLORA → FILTRA → LEGGI
═══════════════════════════════════════════════════════════

### Passo 1 — Esplora la distribuzione
```
cerca_giurisprudenza(query="\\"tema\\"", modalita="esplora")
```
Restituisce solo i facets (materia, sezione, anno, tipo provvedimento) SENZA documenti.
Serve per capire dove si concentrano i risultati prima di cercare.

### Passo 2 — Filtra con i facets
In base alla distribuzione, scegli i filtri:
- **Materia** dominante (>40%) → filtra per materia
- **Sezione** dominante (es. 3 per resp. civile) → filtra per sezione
- **Sezioni Unite** presenti → cercale separatamente (le più autorevoli)
- `tipo_provvedimento="sentenza"` → esclude ordinanze (meno motivate)

```
cerca_giurisprudenza(
    query="\\"tema\\"",
    materia="...",
    sezione="...",
    tipo_provvedimento="sentenza",
    max_risultati=10
)
```

### Passo 3 — Leggi le decisioni chiave
Per le 2-4 decisioni più rilevanti:
```
leggi_sentenza(numero=XXXXX, anno=2024)
```
Privilegia: Sezioni Unite > sentenze recenti > sentenze (non ordinanze).

═══════════════════════════════════════════════════════════
SINTASSI QUERY SOLR
═══════════════════════════════════════════════════════════

Il motore è Solr eDisMax. Sintassi supportata nel campo `query`:

| Sintassi | Effetto | Esempio |
|----------|---------|---------|
| `"frase esatta"` | Match testuale esatto | `"responsabilità medica"` |
| `AND` / `OR` | Operatori booleani (default: OR) | `"art. 2043" AND "danno"` |
| `-termine` | Esclude termine | `"onere prova" -lavoro` |
| `"frase"~3` | Prossimità (entro N parole) | `"nesso causale"~5` |
| `termin*` | Wildcard (prefisso) | `risarcim*` |

REGOLA: usare SEMPRE virgolette per frasi di 2+ parole correlate.

═══════════════════════════════════════════════════════════
PARAMETRO `campo`
═══════════════════════════════════════════════════════════

| Valore | Cerca in | Quando usare |
|--------|----------|--------------|
| (default) | Testo completo (OCR) | Ricerca ampia |
| `"dispositivo"` | Solo dispositivo | Più preciso, meno recall |

═══════════════════════════════════════════════════════════
SEZIONI
═══════════════════════════════════════════════════════════

Codici ammessi nel parametro `sezione`: 1-7 (sezioni semplici, 7 = sez. VII penale),
L (lavoro), U o SU (Sezioni Unite), F (feriale). T = tributaria = sezione 5 civile.
Un codice diverso è rifiutato con errore, invece di restituire zero risultati.

═══════════════════════════════════════════════════════════
FACETS DISPONIBILI
═══════════════════════════════════════════════════════════

| Facet | Descrizione | Esempio valori |
|-------|-------------|----------------|
| Materia | Area giuridica | Obbligazioni, Lavoro, Famiglia |
| Sezione | Sezione della Corte | 1, 2, 3, L, U |
| Anno | Anno di deposito | 2021, ..., 2026 |
| Tipo provvedimento | Tipo decisione | sentenza, ordinanza |

═══════════════════════════════════════════════════════════
ARCHIVI
═══════════════════════════════════════════════════════════

| Archivio | Collezione Solr | Documenti |
|----------|----------------|-----------|
| `civile` | snciv | ~186K |
| `penale` | snpen | ~238K |
| `tutti` (default) | entrambi | ~424K |

Con archivio="tutti" lo stesso numero/anno può indicare una decisione civile e una penale:
`leggi_sentenza` restituisce la prima e segnala le altre.

═══════════════════════════════════════════════════════════
WORKFLOW TIPO
═══════════════════════════════════════════════════════════

Ricerca su tema:
1. cerca_giurisprudenza(query="\\"tema\\"", modalita="esplora")
2. Analizza facets → scegli filtri
3. cerca_giurisprudenza(query="\\"tema\\"", materia="...", sezione="...", max_risultati=10)
4. leggi_sentenza(numero, anno) per le 2-3 decisioni chiave
5. Testo delle norme citate: connettore normativo (Normattiva, iCodici)

Ricerca su norma specifica:
1. giurisprudenza_su_norma(riferimento="art. 2043 c.c.")
   oppure giurisprudenza_articolo("art. 2043 c.c.") per partire dalle massime Brocardi
2. leggi_sentenza(numero, anno) per le decisioni chiave

═══════════════════════════════════════════════════════════
NOTE TECNICHE
═══════════════════════════════════════════════════════════

- API: Solr REST su italgiure.giustizia.it (pubblica, nessuna autenticazione)
- Testo integrale dal PDF ufficiale del provvedimento (campo `filename` dell'indice, estensione
  `.clean.pdf`); se non disponibile si ripiega sul campo `ocr` dell'indice, troncato alla fonte
- Testo letto a blocchi di 30000 caratteri (inizio e fine della sentenza nella prima risposta):
  la nota indica il `da_carattere` con cui leggere la parte omessa
- Certificato SSL non valido → verify=False (necessario)
- Campi chiave: numdec (numero), anno, datdep (data deposito), szdec (sezione), ocr (testo), filename (PDF)
"""

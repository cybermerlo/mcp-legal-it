# MCP Giurisprudenza Cassazione — Project Context

> Server MCP con 8 tool per la giurisprudenza della Corte di Cassazione (Italgiure):
> ricerca, testo integrale dal PDF ufficiale, orientamenti di legittimità.
> Fork ridotto di `capazme/mcp-legal-it`: cosa è stato tolto e perché è in `SPLIT.md`,
> le differenze dall'upstream e il deploy in `STUDIO.md`.

## Stack

| Layer | Tecnologia |
|-------|-----------|
| Framework MCP | FastMCP **2.x** (pin `>=2.11,<3`: con la 3.x `include_tags` viene ignorato in silenzio, vedi STUDIO.md § 1) |
| HTTP client | httpx >= 0.27 (async) |
| HTML scraping | BeautifulSoup4 + lxml (Brocardi) |
| PDF | pypdf (testo integrale delle sentenze) |
| Python | >= 3.10, venv in `.venv/` |
| Test | pytest + pytest-asyncio |

## Struttura

```
├── serve_studio.py            # entrypoint di produzione: /healthz, LEGAL_TAGS, stateless, malloc_trim
├── run_server.py              # entrypoint stdio/http generico → plugin/server/run_server.py
├── src -> plugin/server/src   # symlink storico, i path restano quelli dell'upstream
└── plugin/server/src/
    ├── server.py              # FastMCP: instructions + import dei due moduli tool
    ├── prompts.py             # 2 prompt: analisi_giurisprudenziale, orientamento_giurisprudenziale
    ├── resources.py           # 1 risorsa: legal://riferimenti/ricerca-giurisprudenziale
    ├── tools/
    │   ├── italgiure.py       # leggi_sentenza, cerca_giurisprudenza, giurisprudenza_su_norma,
    │   │                      # ultime_pronunce, giurisprudenza_articolo
    │   └── orientamento.py    # orientamento_su_norma, orientamento_su_principio, mappa_orientamento
    └── lib/
        ├── italgiure/client.py  # Solr, PDF ufficiale, formattazione
        ├── brocardi/client.py   # massime Brocardi → riferimenti Cassazione
        ├── visualex/map.py      # resolve_atto(): solo il resolver dei nomi degli atti
        ├── _http.py, _paging.py, _cache.py, _sources.py, _result.py
```

`visualex` qui contiene **solo** `map.py` e `models.py`: servono a `giurisprudenza_su_norma`,
`giurisprudenza_articolo` e agli strumenti di orientamento per riconoscere l'atto citato
(`art. 13 GDPR` → regolamento 2016/679). Lo scraper Normattiva/EUR-Lex non c'è più.

## Pattern tool

```python
from src.server import mcp

@mcp.tool(tags={"giurisprudenza"})
async def nome_tool(parametro: str) -> str:
    """Docstring visibile all'LLM — descrivere quando usare il tool."""
    result = await _nome_tool_impl(parametro)
    return result.to_str()
```

La logica sta nelle funzioni `_impl` (testabili senza MCP), che restituiscono `SearchResult`.

## Regole

- **Sentenze con numero noto**: `leggi_sentenza(numero, anno)` — mai web search, mai numeri a memoria.
- Il server **non** contiene il testo delle norme: per quello si usa un connettore normativo.
- Le modifiche proprie del fork sono marcate `[fork]` nel codice: tenerle circoscritte aiuta il
  confronto con l'upstream.

## Test

```bash
.venv/bin/pytest tests/ -m "not live"   # default: mock HTTP, nessuna connessione
.venv/bin/pytest tests/ -m live         # Italgiure e Brocardi reali
```

## Italgiure — note tecniche

- **API**: Solr REST su `https://www.italgiure.giustizia.it/sncass/isapi/hc.dll/sn.solr`
- **Collezioni**: `snciv` (civile) e `snpen` (penale)
- **Finestra**: l'archivio pubblico copre circa gli ultimi cinque anni (dal 2021); `ARCHIVE_START_YEAR`
  e `ARCHIVE_WINDOW_NOTE` in `lib/italgiure/client.py`
- **SSL**: certificato non valido → `verify=False` (necessario)
- **Campi chiave**: `numdec`, `anno`, `datdep`, `szdec`, `ocr`, `ocrdis`, `filename`
- **Sezioni** (`szdec`): 1-7, L, U, F. `resolve_sezione()` traduce SU→U, T→5 (civile) e rifiuta
  i codici sconosciuti, che altrimenti darebbero zero risultati in silenzio
- **Testo integrale** `[fork]`: `ocr` e `ocrdis` sono troncati alla fonte. `fetch_pdf_text()` scarica il
  PDF ufficiale (`filename` con estensione `.clean.pdf`) e `format_full_text(doc, pdf_text=...)` lo usa
  quando è almeno lungo quanto l'indice; la riga **Fonte del testo** dichiara sempre la fonte
- **Lettura a pagine**: oltre 30000 caratteri la prima risposta dà inizio (12000) e fine (18000);
  `da_carattere=N` restituisce la finestra che parte da N. Le posizioni contano i caratteri del testo
  servito (il PDF, se c'è), per cui `_leggi_sentenza_impl` scarica il PDF anche nelle pagine successive

## Brocardi — note tecniche

- Navigazione in due passi: pagina del codice → pagina dell'articolo → scraping
- Cache persistente JSON degli URL degli articoli (`MCP_CACHE_DIR`, default `~/.cache/mcp-legal-it`;
  `LEGAL_CACHE=off` la disattiva)
- `parse_massime_references()` estrae i riferimenti Cassazione per `leggi_sentenza()`;
  `giurisprudenza_articolo` e `mappa_orientamento` separano quelli anteriori alla finestra di Italgiure

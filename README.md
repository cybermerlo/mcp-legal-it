# MCP Giurisprudenza Cassazione

Server [Model Context Protocol](https://modelcontextprotocol.io/) per la giurisprudenza della
**Corte di Cassazione**, dall'archivio pubblico **Italgiure / SentenzeWeb**. Nasce come fork di
[`capazme/mcp-legal-it`](https://github.com/capazme/mcp-legal-it) ridotto alla sola parte di
giurisprudenza di legittimità: tutto il resto (calcoli, parcelle, normativa, privacy, CONSOB,
altre corti) è stato tolto e confluirà in un progetto separato. L'elenco di ciò che è stato
rimosso, e da dove recuperarlo, è in [`SPLIT.md`](SPLIT.md).

## Tool (8)

| Tool | Cosa fa |
|------|---------|
| `cerca_giurisprudenza` | Ricerca full-text con filtri (materia, sezione, anno, tipo, Sezioni Unite) e modalità `esplora` (solo facets) |
| `giurisprudenza_su_norma` | Decisioni che citano un articolo (`art. 2043 c.c.`, `art. 13 GDPR`) |
| `giurisprudenza_articolo` | Sentenze di Cassazione citate nelle massime Brocardi di un articolo |
| `leggi_sentenza` | **Testo integrale** di una decisione nota, estratto dal **PDF ufficiale**, con lettura a pagine (`da_carattere`) |
| `ultime_pronunce` | Ultime decisioni depositate |
| `orientamento_su_norma` | Mappa descrittiva: conformi vs contrasti, Sezioni Unite, evoluzione per anno |
| `orientamento_su_principio` | Come sopra, partendo da un principio espresso a parole |
| `mappa_orientamento` | Orchestratore: massime Brocardi → decisioni successive → Sezioni Unite |

Più 2 prompt guidati (`analisi_giurisprudenziale`, `orientamento_giurisprudenziale`) e una
risorsa (`legal://riferimenti/ricerca-giurisprudenziale`).

**Copertura**: l'archivio pubblico è una finestra mobile di circa cinque anni (dal 2021).
Niente massime del CED, niente giurisprudenza di merito. Per il testo delle norme citate
serve un connettore normativo a parte (Normattiva, iCodici).

## Avvio

```bash
python -m venv .venv && .venv/bin/pip install -e ".[dev]"

# stdio (Claude Desktop / Code)
.venv/bin/python run_server.py

# HTTP, come in produzione: /mcp + /healthz
MCP_TRANSPORT=http .venv/bin/python serve_studio.py
```

Con la variabile `MCP_URL_TOKEN` impostata l'endpoint MCP risponde solo su `/mcp/<chiave>`
(o su `/mcp` con `Authorization: Bearer <chiave>`); senza, è aperto.

Docker: `docker compose up` (porta 8000). Il deploy dello Studio (Coolify) e le differenze
dal progetto originario sono descritti in [`STUDIO.md`](STUDIO.md).

## Test

```bash
.venv/bin/pytest tests/ -m "not live"   # unit, con mock HTTP
.venv/bin/pytest tests/ -m live         # contro Italgiure e Brocardi reali
```

## Licenza

Apache-2.0, come il progetto originario.

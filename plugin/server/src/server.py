"""MCP Giurisprudenza Cassazione — ricerca e lettura delle decisioni della Corte di Cassazione (Italgiure)."""

import os

from fastmcp import FastMCP

mcp = FastMCP(
    "Giurisprudenza Cassazione",
    instructions="""\
Giurisprudenza della Corte di Cassazione dall'archivio pubblico Italgiure (SentenzeWeb).
Usa i tool di questo server quando l'utente chiede:
- SENTENZE E ORDINANZE DI CASSAZIONE: ricerca per tema, per norma citata, ultime depositate
- TESTO INTEGRALE di una decisione nota (numero e anno): leggi_sentenza, dal PDF ufficiale
- ORIENTAMENTO DI LEGITTIMITÀ: orientamento_su_norma, orientamento_su_principio, mappa_orientamento —
  conformi vs contrasti, interventi delle Sezioni Unite (descrittivo, non predittivo)

COPERTURA: l'archivio pubblico è una finestra mobile di circa cinque anni (dal 2021 in poi):
le decisioni anteriori non sono consultabili. Niente massime del CED, niente giurisprudenza di merito.

REGOLE: leggi_sentenza() DIRETTO per sentenze note — mai web search, mai numeri a memoria.
Per il testo delle norme citate usare un connettore normativo (Normattiva, iCodici).
OUTPUT: GG/MM/AAAA; estremi nella forma "Cass. civ., sez. III, n. 29253/2024".

WORKFLOW:
Tema → cerca_giurisprudenza(modalita="esplora") → cerca_giurisprudenza(filtri) → leggi_sentenza
Norma → giurisprudenza_su_norma | giurisprudenza_articolo (massime Brocardi) → leggi_sentenza
Orientamento → orientamento_su_norma/orientamento_su_principio → mappa_orientamento (conformi/contrasti/SS.UU.)
""",
)

# Import all tool modules — each registers its tools via @mcp.tool()
from src.tools import (  # noqa: E402, F401
    italgiure,
    orientamento,
)

from src import prompts, resources  # noqa: E402, F401

# ---------------------------------------------------------------------------
# Tag-based tool filtering. Tutti i tool di questo server hanno il tag
# "giurisprudenza": il filtro resta per compatibilita' con LEGAL_PROFILE e con
# LEGAL_TAGS di serve_studio.py, ma con un solo gruppo non seleziona nulla.
# ---------------------------------------------------------------------------
_PROFILES: dict[str, set[str]] = {
    "giurisprudenza": {"giurisprudenza"},
}

_profile = os.environ.get("LEGAL_PROFILE", "full")
if _profile != "full" and _profile in _PROFILES:
    mcp.include_tags = _PROFILES[_profile]

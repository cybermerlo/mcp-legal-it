#!/usr/bin/env python3
"""Entrypoint dello Studio Legale — usato al posto di run_server.py.

File AGGIUNTO dal fork (non esiste nell'upstream). Fa quello che fa
plugin/server/run_server.py, piu' quello che serve al deploy su Coolify:

  - la rotta ``/healthz``, perche' FastMCP espone solo ``/mcp`` e una GET su
    ``/mcp`` risponde 406: senza una rotta dedicata non e' possibile alcun
    healthcheck, ne' quello di Coolify ne' il monitor su Telegram;

  - la variabile d'ambiente ``LEGAL_TAGS``, che permette di scegliere
    liberamente quali gruppi di tool esporre. L'upstream ha solo i profili
    fissi di ``LEGAL_PROFILE`` e nessuno corrisponde a cio' che serve allo
    studio. Con 218 tool lo schema pesa ~260 KB (~66k token) che il client
    si carica a OGNI connessione, anche senza usarli;

  - due misure contro la crescita della memoria di un servizio che resta
    acceso per settimane: trasporto HTTP senza stato e restituzione al
    sistema della memoria liberata dopo ogni tool (STUDIO.md, § 8).

Vedi STUDIO.md per il quadro completo delle differenze dall'upstream.
"""
import ctypes
import ctypes.util
import os
import sys

BASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "plugin", "server")
sys.path.insert(0, BASE)
os.chdir(BASE)

from fastmcp.server.middleware import Middleware  # noqa: E402
from src.server import mcp  # noqa: E402
from starlette.requests import Request  # noqa: E402
from starlette.responses import JSONResponse  # noqa: E402

# --- selezione dei tool per tag ---------------------------------------------
# LEGAL_TAGS ha la precedenza su LEGAL_PROFILE (che src/server.py ha gia'
# applicato al momento dell'import). Vuoto o assente = tutti i tool.
_tags = {t.strip() for t in os.environ.get("LEGAL_TAGS", "").split(",") if t.strip()}
if _tags:
    mcp.include_tags = _tags


# --- memoria liberata restituita al sistema ---------------------------------
# glibc tiene per se' la memoria che il programma libera e la riusa, ma non la
# rende al sistema: il processo resta grosso quanto il suo picco piu' alto.
# E i picchi qui sono grossi e rari: la prima ricerca alla Corte costituzionale
# dopo un deploy scarica e decodifica l'archivio 2001-oggi, e prima della
# correzione di corte_cost lasciava il processo a ~400 MB con 200 KB di oggetti
# vivi. malloc_trim(0) dopo ogni tool lo riporta a ~95 MB e costa da 1 a 20 ms.
# Fuori da glibc (macOS, musl) non fa nulla.
def _carica_malloc_trim():
    try:
        return ctypes.CDLL(ctypes.util.find_library("c") or "libc.so.6").malloc_trim
    except (OSError, AttributeError):
        return None


_malloc_trim = _carica_malloc_trim()


class _RestituisciMemoria(Middleware):
    async def on_call_tool(self, context, call_next):
        try:
            return await call_next(context)
        finally:
            _malloc_trim(0)


if _malloc_trim is not None:
    mcp.add_middleware(_RestituisciMemoria())


@mcp.custom_route("/healthz", methods=["GET"])
async def healthz(request: Request) -> JSONResponse:
    """Sonda per Coolify e per il monitor dello studio. Deve restare a costo zero."""
    payload = {"status": "ok", "tags": sorted(_tags) if _tags else "tutti"}
    try:
        # get_tools() restituisce il registro COMPLETO: include_tags viene
        # applicato piu' a valle, in fase di tools/list. Qui rifacciamo il conto
        # a mano, altrimenti la sonda direbbe sempre 218 e non servirebbe a
        # verificare che il filtro abbia fatto presa.
        tools = await mcp.get_tools()
        payload["tool"] = (
            sum(1 for t in tools.values() if set(getattr(t, "tags", None) or ()) & _tags)
            if _tags
            else len(tools)
        )
    except Exception as exc:  # non far mai fallire la sonda per questo
        payload["tool"] = f"n/d ({type(exc).__name__})"
    return JSONResponse(payload)


if __name__ == "__main__":
    print(
        f"[studio] tag attivi: {sorted(_tags) if _tags else 'TUTTI'}",
        flush=True,
    )
    mcp.run(
        transport=os.environ.get("MCP_TRANSPORT", "http"),
        host=os.environ.get("MCP_HOST", "0.0.0.0"),
        port=int(os.environ.get("MCP_PORT", "8000")),
        path=os.environ.get("MCP_PATH", "/mcp"),
        # Senza stato: ogni richiesta ha il suo trasporto, che muore con lei.
        # Con le sessioni, FastMCP 2.x non passa all'SDK alcun timeout di
        # inattivita' e Claude non chiude mai quelle che apre (nessuna DELETE):
        # restavano in memoria per sempre, ognuna con l'ultimo messaggio
        # inviato — fino a ~430 KB se era il testo di una sentenza. Nessun tool
        # usa funzioni di sessione. MCP_STATELESS=0 per tornare alle sessioni.
        stateless_http=os.environ.get("MCP_STATELESS", "1") != "0",
    )

#!/usr/bin/env python3
"""Entrypoint dello Studio Legale — usato al posto di run_server.py.

File AGGIUNTO dal fork (non esiste nell'upstream). Fa quello che fa
plugin/server/run_server.py, piu' due cose che servono al deploy su Coolify:

  - la rotta ``/healthz``, perche' FastMCP espone solo ``/mcp`` e una GET su
    ``/mcp`` risponde 406: senza una rotta dedicata non e' possibile alcun
    healthcheck, ne' quello di Coolify ne' il monitor su Telegram;

  - la variabile d'ambiente ``LEGAL_TAGS``, che permette di scegliere
    liberamente quali gruppi di tool esporre. L'upstream ha solo i profili
    fissi di ``LEGAL_PROFILE`` e nessuno corrisponde a cio' che serve allo
    studio. Con 218 tool lo schema pesa ~260 KB (~66k token) che il client
    si carica a OGNI connessione, anche senza usarli.

Vedi STUDIO.md per il quadro completo delle differenze dall'upstream.
"""
import os
import sys

BASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "plugin", "server")
sys.path.insert(0, BASE)
os.chdir(BASE)

from src.server import mcp  # noqa: E402
from starlette.requests import Request  # noqa: E402
from starlette.responses import JSONResponse  # noqa: E402

# --- selezione dei tool per tag ---------------------------------------------
# LEGAL_TAGS ha la precedenza su LEGAL_PROFILE (che src/server.py ha gia'
# applicato al momento dell'import). Vuoto o assente = tutti i tool.
_tags = {t.strip() for t in os.environ.get("LEGAL_TAGS", "").split(",") if t.strip()}
if _tags:
    mcp.include_tags = _tags


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
    )

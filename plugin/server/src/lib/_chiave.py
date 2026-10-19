"""[fork] La chiave nell'indirizzo: `/mcp/<chiave>` al posto di un login.

I connettori personalizzati dell'app desktop di Claude accettano solo un URL
(piu' i campi OAuth): non c'e' un posto dove mettere un'intestazione. Per questo
il segreto sta nel percorso, come negli altri server MCP dello studio (Archivio
di merito, CCNL): `/mcp/<chiave>` viene verificato a tempo costante e riscritto
in `/mcp` prima che la richiesta arrivi a FastMCP.

Per i client che sanno mandare un'intestazione (Claude Code) vale anche
`Authorization: Bearer <chiave>` su `/mcp`.

Tutto il resto sotto `/mcp`, chiave sbagliata compresa, risponde 404: per chi
non ha la chiave il server MCP non esiste. Le rotte di scoperta OAuth
(`/.well-known/...`) restano 404 come senza chiave: un 401 li' farebbe credere
ai client di Claude che serva un login OAuth. `/healthz` resta libero.

Senza chiave configurata (`MCP_URL_TOKEN` vuota) il middleware non fa nulla:
il server si comporta come prima.
"""

from __future__ import annotations

import hmac

from starlette.responses import PlainTextResponse
from starlette.types import ASGIApp, Receive, Scope, Send


class ChiaveNellIndirizzo:
    """Middleware ASGI che protegge l'endpoint MCP con una chiave."""

    def __init__(self, app: ASGIApp, chiave: str, percorso: str = "/mcp") -> None:
        self.app = app
        self.chiave = chiave
        self.percorso = "/" + percorso.strip("/")

    def _bearer(self, scope: Scope) -> str:
        for nome, valore in scope.get("headers") or ():
            if nome == b"authorization":
                testo = valore.decode("latin-1")
                if testo[:7].lower() == "bearer ":
                    return testo[7:].strip()
        return ""

    def _uguale(self, candidato: str) -> bool:
        return hmac.compare_digest(candidato.encode(), self.chiave.encode())

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or not self.chiave:
            await self.app(scope, receive, send)
            return

        path = scope["path"]
        base = self.percorso
        if path != base and not path.startswith(base + "/"):
            await self.app(scope, receive, send)
            return

        segmento = path[len(base):].strip("/")
        if segmento and "/" not in segmento and self._uguale(segmento):
            # Riscrittura sul posto: il log degli accessi di uvicorn legge questo
            # stesso dizionario, quindi registra `/mcp` e non la chiave.
            scope["path"] = base
            scope["raw_path"] = base.encode()
            await self.app(scope, receive, send)
            return
        if not segmento and self._uguale(self._bearer(scope)):
            await self.app(scope, receive, send)
            return

        await PlainTextResponse("Not Found", status_code=404)(scope, receive, send)

"""[fork] La chiave nell'indirizzo (src/lib/_chiave.py, usata da serve_studio.py)."""

from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.requests import Request
from starlette.responses import PlainTextResponse
from starlette.routing import Route
from starlette.testclient import TestClient

from src.lib._chiave import ChiaveNellIndirizzo

CHIAVE = "k3y-di-prova-0123456789"


def _eco(request: Request) -> PlainTextResponse:
    return PlainTextResponse(request.url.path)


def _client(chiave: str = CHIAVE) -> TestClient:
    app = Starlette(
        routes=[Route("/mcp", _eco, methods=["GET", "POST"]), Route("/healthz", _eco)],
        middleware=[Middleware(ChiaveNellIndirizzo, chiave=chiave, percorso="/mcp")],
    )
    return TestClient(app)


class TestChiaveNelPercorso:
    def test_chiave_giusta_riscrive_in_mcp(self):
        r = _client().post(f"/mcp/{CHIAVE}")
        assert r.status_code == 200
        assert r.text == "/mcp"

    def test_barra_finale_ammessa(self):
        assert _client().post(f"/mcp/{CHIAVE}/").text == "/mcp"

    def test_chiave_sbagliata_404(self):
        assert _client().post("/mcp/sbagliata").status_code == 404

    def test_mcp_nudo_senza_chiave_404(self):
        assert _client().post("/mcp").status_code == 404

    def test_percorso_piu_lungo_404(self):
        assert _client().post(f"/mcp/{CHIAVE}/altro").status_code == 404

    def test_prefisso_della_chiave_non_basta(self):
        assert _client().post(f"/mcp/{CHIAVE[:-1]}").status_code == 404


class TestBearer:
    def test_bearer_giusto_su_mcp(self):
        r = _client().post("/mcp", headers={"Authorization": f"Bearer {CHIAVE}"})
        assert r.status_code == 200

    def test_bearer_sbagliato_404(self):
        r = _client().post("/mcp", headers={"Authorization": "Bearer sbagliata"})
        assert r.status_code == 404


class TestFuoriDaMcp:
    def test_healthz_libero(self):
        assert _client().get("/healthz").status_code == 200

    def test_scoperta_oauth_resta_404(self):
        assert _client().get("/.well-known/oauth-authorization-server").status_code == 404

    def test_percorso_simile_non_protetto_ne_servito(self):
        # /mcpx non e' l'endpoint MCP: passa all'app, che non lo conosce.
        assert _client().get("/mcpx").status_code == 404


class TestChiaveMaiNelLog:
    """Il log di uvicorn legge scope["path"]: dopo il middleware non deve contenere la chiave."""

    def _percorso_registrato(self, path: str) -> str:
        import asyncio

        async def interna(scope, receive, send):
            await PlainTextResponse("ok")(scope, receive, send)

        mw = ChiaveNellIndirizzo(interna, chiave=CHIAVE, percorso="/mcp")
        scope = {"type": "http", "method": "GET", "path": path, "raw_path": path.encode(),
                 "headers": [], "query_string": b""}

        async def receive():
            return {"type": "http.request", "body": b"", "more_body": False}

        async def send(_message):
            pass

        asyncio.run(mw(scope, receive, send))
        return scope["path"]

    def test_scoperta_oauth_con_chiave_nel_percorso(self):
        # Le richieste viste nel log del 2026-10-24 al click su "Collega" nell'app desktop.
        for path in (
            f"/.well-known/oauth-protected-resource/mcp/{CHIAVE}",
            f"/.well-known/oauth-authorization-server/mcp/{CHIAVE}",
            f"/.well-known/openid-configuration/mcp/{CHIAVE}",
            f"/mcp/{CHIAVE}/.well-known/openid-configuration",
        ):
            registrato = self._percorso_registrato(path)
            assert CHIAVE not in registrato, path
            assert "***" in registrato

    def test_chiave_giusta_registrata_come_mcp(self):
        assert self._percorso_registrato(f"/mcp/{CHIAVE}") == "/mcp"

    def test_scoperta_con_chiave_resta_404(self):
        c = _client()
        assert c.get(f"/.well-known/oauth-protected-resource/mcp/{CHIAVE}").status_code == 404
        assert c.get(f"/mcp/{CHIAVE}/.well-known/openid-configuration").status_code == 404


class TestSenzaChiave:
    def test_chiave_vuota_non_protegge(self):
        assert _client(chiave="").post("/mcp").status_code == 200


class TestConFastMCP:
    """La chiave davanti all'app MCP vera: initialize passa solo con la chiave."""

    _INIT = {
        "jsonrpc": "2.0", "id": 1, "method": "initialize",
        "params": {
            "protocolVersion": "2025-06-18", "capabilities": {},
            "clientInfo": {"name": "test", "version": "0"},
        },
    }
    _HEADERS = {"Accept": "application/json, text/event-stream", "Content-Type": "application/json"}

    def _app(self):
        from src.server import mcp

        return mcp.http_app(
            path="/mcp",
            stateless_http=True,
            middleware=[Middleware(ChiaveNellIndirizzo, chiave=CHIAVE, percorso="/mcp")],
        )

    def test_initialize_con_chiave(self):
        with TestClient(self._app()) as c:
            r = c.post(f"/mcp/{CHIAVE}", json=self._INIT, headers=self._HEADERS)
        assert r.status_code == 200
        assert "serverInfo" in r.text

    def test_initialize_senza_chiave_404(self):
        with TestClient(self._app()) as c:
            assert c.post("/mcp", json=self._INIT, headers=self._HEADERS).status_code == 404
            assert c.post("/mcp/sbagliata", json=self._INIT, headers=self._HEADERS).status_code == 404

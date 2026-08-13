FROM python:3.12-slim AS base
WORKDIR /app

# System deps for lxml (C compilation)
# [fork] aggiunto curl: l'healthcheck di Coolify per le risorse Dockerfile esegue
# un curl (o wget) DENTRO il container. python:slim non ha ne' l'uno ne' l'altro
# -> container dichiarato unhealthy e rollback automatico del deploy.
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libxml2-dev libxslt1-dev curl && \
    rm -rf /var/lib/apt/lists/*

COPY pyproject.toml .
RUN pip install --no-cache-dir .

# [fork] Il pin di FastMCP e' in pyproject.toml ed e' la patch piu' importante:
# qui verifichiamo che abbia fatto presa, perche' con FastMCP 3.x il filtro dei
# tool viene ignorato IN SILENZIO (vedi STUDIO.md). Meglio un build che fallisce
# di un server che espone 218 tool senza dirlo.
RUN python -c "import fastmcp,sys; v=fastmcp.__version__; print('FastMCP',v); sys.exit(0 if v.startswith('2.') else 1)"

# Replicate plugin/server structure expected by run_server.py
COPY plugin/server/src/ plugin/server/src/
COPY plugin/server/run_server.py plugin/server/run_server.py
COPY run_server.py .
# [fork] entrypoint dello studio: /healthz + LEGAL_TAGS
COPY serve_studio.py .

ENV LEGAL_PROFILE=full
ENV MCP_TRANSPORT=http
ENV MCP_HOST=0.0.0.0
ENV MCP_PORT=8000
ENV MCP_PATH=/mcp
EXPOSE 8000

# [fork] Preset B — studio civile + penale (115 tool). Sovrascrivibile dalla
# variabile d'ambiente omonima impostata su Coolify: per cambiare selezione si
# tocca QUELLA (pannello -> Environment Variables -> Redeploy), non questo file.
# Valore vuoto = tutti i tool.
ENV LEGAL_TAGS="giurisprudenza,costituzionale,giudiziario,scadenze,interessi,rivalutazione,danni,credito,sinistro,parcelle_avv,penale,utility"

# Cache and temp directories
RUN mkdir -p /app/.cache/mcp-legal-it /tmp/mcp-legal-it
ENV MCP_CACHE_DIR=/app/.cache/mcp-legal-it

# [fork] run_server.py -> serve_studio.py
CMD ["python", "serve_studio.py"]

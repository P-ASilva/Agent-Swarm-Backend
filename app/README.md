# API Manual Checks

## Run the API locally

From the repository root:

```powershell
.\.venv\Scripts\python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

## URLs for manual validation

- Health: `http://127.0.0.1:8000/health`
- Swagger UI: `http://127.0.0.1:8000/docs`
- ReDoc: `http://127.0.0.1:8000/redoc`
- OpenAPI JSON: `http://127.0.0.1:8000/openapi.json`
- Messages endpoint: `http://127.0.0.1:8000/messages`

## Manual API checks (PowerShell)

```powershell
# Health
Invoke-RestMethod -Uri http://127.0.0.1:8000/health

# Valid message payload
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/messages `
  -ContentType "application/json" `
  -Body '{"message":"How can I use my phone as a card machine?","userId":"client789"}'

# Invalid payload should return 422
try {
  Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/messages `
    -ContentType "application/json" `
    -Body '{}'
} catch {
  $_.Exception.Response.StatusCode.value__
}
```

## Manual test commands

From the repository root:

```powershell
# API smoke checks (PowerShell script)
powershell -ExecutionPolicy Bypass -File tests/smoke/smokeApi.ps1

# Route contracts
.\.venv\Scripts\python -m pytest tests/routes -q

# API integration + failure paths
.\.venv\Scripts\python -m pytest tests/integration -q

# Full suite
.\.venv\Scripts\python -m pytest -q
```

Optional bash smoke script (targets a running API container):

```bash
bash tests/smoke/smokeDocker.sh
```

## RAG pipeline operations

RAG storage uses Postgres + pgvector and runs separately from the HTTP API lifecycle.

```powershell
# Start pgvector database
docker compose up -d postgres

# Apply RAG schema migrations
.\venv\Scripts\python -m app.rag_pipeline.cli migrate

# Ingest from JSON base URL manifest
.\venv\Scripts\python -m app.rag_pipeline.cli ingest --crawl-version 20260429

# Reindex data when chunking/model/schema changes
.\venv\Scripts\python -m app.rag_pipeline.cli reindex --crawl-version 20260429-r2

# Ingest one URL directly (research-agent trigger flow)
.\venv\Scripts\python -m app.rag_pipeline.cli add-url --url "https://www.infinitepay.io/pix" --crawl-version 20260429-r3

# Retrieval verification query
.\venv\Scripts\python -m app.rag_pipeline.cli query --query "tap to pay" --top-k 3 --pretty
```

RAG smoke scripts:

```powershell
powershell -ExecutionPolicy Bypass -File tests/smoke/smokeRagPipeline.ps1
```

```bash
bash tests/smoke/smokeRagPipeline.sh
```

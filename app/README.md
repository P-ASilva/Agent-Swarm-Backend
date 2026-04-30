# API Manual Checks

## Run the API locally (no Docker) only after applying both migration sets to the databases pointed to by `DATABASE_URL` and `SESSION_DATABASE_URL`; otherwise you will see retrieval `UndefinedTable` for RAG and persistence errors.

From the repository root, apply migrations once per environment:

```powershell
.\.venv\Scripts\python -m app.infra.rag_pipeline.cli migrate
.\.venv\Scripts\python -m message_persistence.cli migrate
```

Then start the server:

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

# Authenticated payload (loads same-day history and links app_users rows)
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/messages `
  -ContentType "application/json" `
  -Body '{"message":"Continue from my previous requests","userId":"client789","googleIdToken":"<google-id-token>"}'

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
powershell -ExecutionPolicy Bypass -File tests/smoke/smokeDocker.ps1

# Integration tests
.\.venv\Scripts\python -m pytest tests/integration -q
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

# Start session Postgres (user/message persistence)
docker compose up -d session_postgres

# Apply RAG schema migrations
.\.venv\Scripts\python -m app.infra.rag_pipeline.cli migrate

# Apply user/message persistence migrations
.\.venv\Scripts\python -m message_persistence.cli migrate

# Ingest from JSON base URL manifest
.\.venv\Scripts\python -m app.infra.rag_pipeline.cli ingest --crawl-version 20260429

# Reindex data when chunking/model/schema changes
.\.venv\Scripts\python -m app.infra.rag_pipeline.cli reindex --crawl-version 20260429-r2

# Ingest one URL directly (research-agent trigger flow)
.\.venv\Scripts\python -m app.infra.rag_pipeline.cli add-url --url "https://www.infinitepay.io/pix" --crawl-version 20260429-r3

# Retrieval verification query
.\.venv\Scripts\python -m app.infra.rag_pipeline.cli query --query "tap to pay" --top-k 3 --pretty
```

KnowledgeAgent supports both direct trigger styles:
- structured JSON message action (e.g. `{"tool":"add_url_to_context","url":"https://..."}`),
- natural-language request containing an URL and add-to-context intent.

Model split configuration:
- `ROUTER_MODEL` controls route selection.
- `KNOWLEDGE_MODEL` controls grounded answer formatting for knowledge replies.
- `GOOGLE_CLIENT_ID` controls accepted Google token audience for authenticated `/messages` persistence.

RAG smoke scripts:

```powershell
powershell -ExecutionPolicy Bypass -File tests/smoke/smokeRagPipeline.ps1
```

```bash
bash tests/smoke/smokeRagPipeline.sh
```

## Compose-triggered RAG modes

For a **first bulk load** (empty RAG index), merge **`docker-compose.rag-seed.yml`** and run **`rag_seed`** (see root **`README.md`**, Docker setup).

For **ad hoc** ingest or **`add-url`**, enable **`--profile rag`** — both run via **`rag_ingest`** (same pipeline as the CLI):

```powershell
# DB setup seed from app/infra/rag_pipeline/seedUrls.json
docker compose --profile rag run --rm `
  -e RAG_PIPELINE_COMMAND=ingest `
  -e RAG_PIPELINE_ARGS="--crawl-version 20260429" `
  rag_ingest

# Research-agent direct URL add
docker compose --profile rag run --rm `
  -e RAG_PIPELINE_COMMAND=add-url `
  -e RAG_PIPELINE_ARGS="--url https://www.infinitepay.io/pix --crawl-version 20260429-rurl" `
  rag_ingest
```

KnowledgeAgent smoke:

```powershell
powershell -ExecutionPolicy Bypass -File tests/smoke/smokeKnowledgeAgent.ps1
```

```bash
bash tests/smoke/smokeKnowledgeAgent.sh
```

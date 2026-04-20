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
  -Body '{"message":"How can I use my phone as a card machine?","user_id":"client789"}'

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
powershell -ExecutionPolicy Bypass -File tests/smoke/smoke_api.ps1

# Route contracts
.\.venv\Scripts\python -m pytest tests/routes -q

# API integration + failure paths
.\.venv\Scripts\python -m pytest tests/integration -q

# Full suite
.\.venv\Scripts\python -m pytest -q
```

Optional bash smoke script:

```bash
bash tests/smoke/smoke_api.sh
```

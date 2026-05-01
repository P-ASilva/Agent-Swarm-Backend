# Manual de verificação da API

Guia rápido para subir a API localmente e validar endpoints. O panorama do sistema, Docker, RAG e testes está no [**README na raiz do repositório**](../README.md).

## Pré-requisitos

Com `DATABASE_URL` e `SESSION_DATABASE_URL` apontando para instâncias com schema aplicado:

```powershell
python -m app.infra.rag_pipeline.cli migrate
python -m message_persistence.cli migrate
```

## Subir o servidor (sem Docker)

```powershell
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

## URLs úteis

| Recurso | URL |
|---------|-----|
| Saúde | `http://127.0.0.1:8000/health` |
| Swagger | `http://127.0.0.1:8000/docs` |
| ReDoc | `http://127.0.0.1:8000/redoc` |
| Mensagens | `POST http://127.0.0.1:8000/messages` |

## Exemplos PowerShell

```powershell
Invoke-RestMethod -Uri http://127.0.0.1:8000/health

Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/messages `
  -ContentType "application/json" `
  -Body '{"message":"Como usar o celular como maquininha?","userId":"client789"}'

Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/messages `
  -ContentType "application/json" `
  -Body '{"message":"Continuar do histórico de hoje","userId":"client789","googleIdToken":"<token>"}'
```

Payload vazio ou campos obrigatórios em falta → **422**.

## Testes automatizados

Na raiz do repositório:

```powershell
pytest tests/routes -q
pytest tests/integration -q
pytest -q
```

Smoke contra stack em execução:

```powershell
powershell -ExecutionPolicy Bypass -File tests/smoke/smokeDocker.ps1
```

## Pipeline RAG (resumo)

```powershell
docker compose up -d postgres
python -m app.infra.rag_pipeline.cli migrate
python -m app.infra.rag_pipeline.cli ingest --crawl-version 20260429
python -m app.infra.rag_pipeline.cli query --query "pix parcelado" --top-k 3 --pretty
```

O `KnowledgeAgent` pode disparar ingestão por mensagem com URL + intenção de adicionar contexto, ou JSON estruturado com `add_url` / ferramenta equivalente (ver código em `knowledgeAgent.py`).

## Variáveis relevantes

- `ROUTER_MODEL`, `KNOWLEDGE_MODEL`, `SUPPORT_MODEL`, `WEB_SEARCH_MODEL`
- `GUARDRAILS_MODE` e prefixos `GUARDRAILS_*` (regras de entrada/saída)
- `GOOGLE_CLIENT_ID` para `googleIdToken` em `/messages`

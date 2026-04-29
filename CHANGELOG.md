/feat switched RAG seed source to `app/rag_pipeline/seedUrls.json`, added challenge URL manifest entries, and updated compose/env/docs defaults to use the JSON manifest instead of `challenge-context.md`.
/feat added `add-url` RAG CLI mode so research-agent calls can ingest explicit URLs through the same ingestion pipeline without duplicating fetch/chunk/embed/store logic.
/feat added a standalone RAG ingestion pipeline (`app.rag_pipeline`) with challenge-link sourcing, deterministic chunking, versioned pgvector upserts, migration runner, and retrieval query CLI commands.
/feat added pgvector infrastructure in `docker-compose.yml` with a health-checked Postgres service, persistent volume, and optional one-off `rag_ingest` profile container.
/feat introduced model-agnostic retrieval contracts via `KnowledgeRetrieverPort`, `RetrievedChunk`, and `PgvectorKnowledgeRetriever` so future models can consume stored RAG chunks consistently.
/test added RAG-focused coverage including chunk/source/normalization unit tests, pgvector integration test scaffolding, adapter mapping tests, and shell smoke scripts for end-to-end ingest/query checks.
/docs documented RAG setup, rerun workflow, and operational commands in `README.md` and `app/README.md` for local and containerized execution.
/refactor migrated API, domain, adapter, modeling, and test modules to camelCase naming (symbols/files), updated payload fields to `userId`/`traceId`, and aligned pytest discovery for camelCase test files.
/feat implemented API route testing baseline with pytest foundation, route contracts, integration/failure-path suites, and README quality gates for local/CI execution.
/feat implemented FastAPI route adapters for `POST /messages` and `GET /health` with composition-root wiring, normalized response envelope, dependency/timeout HTTP mapping, and OpenAPI-aligned documentation updates.
/feat added Docker setup for containerized API execution, including image build configuration and runtime defaults for local development.
/chore added infrastructure scaffolding for consistent local and CI environments, aligning service startup and dependency wiring across execution modes.
/test added shell smoke checks (`tests/smoke/smoke_api.ps1` and `tests/smoke/smoke_api.sh`) for `/health` and `/messages`, and documented local smoke commands in `README.md`.
/test added container-focused validation coverage to verify health and message routes under Dockerized runtime conditions.
/test added dotenv-based OpenAI connectivity smoke script to validate `OPEN_API_KEY` authentication and API reachability.
/docs added `app/README.md` with local API URLs, manual route checks, and command lines for smoke and pytest scripts.
/chore added `uvicorn` to `requirements.txt` to support local API startup command.

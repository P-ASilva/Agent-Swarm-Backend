
/refactor removed router route `fallback`: routing is only `knowledge` or `support`; out-of-scope style questions default to knowledge path; degraded routing still sets a static `RouterDecision.reply`; legacy JSON `route:\"fallback\"` is coerced to `knowledge` in `parseRouterDecision`.

/fix KnowledgeAgent: stricter RAG score floor (0.62) when web search is configured; web search query uses bare user message; retry web search when the formatter admits missing context; web-specific system addendum so answers use cited web excerpts (not only InfinitePay).

/chore hardened `smokeWebSearch.sh` to find Python via `PYTHON`, `python3`, `python`, or `py -3` on Windows Git Bash.

/test added `tests/smoke/smokeWebSearch.sh` and `smokeWebSearch.ps1` live smoke script that posts a Selic question to `/messages` and prints the reply.

/feat added optional knowledge web search fallback using OpenAI Responses API (`web_search_preview`) via `OpenAiWebSearchAdapter`, gated by RAG relevance score and configurable with `WEB_SEARCH_MODEL` (same `OPENAI_API_KEY` as chat).

/refactor renamed **`DefaultMessageUseCase`** → **`MessageUseCase`** (module **`defaultMessageUseCase`** → **`messageUseCase`**).
/refactor moved RAG package to **`app.infra.rag_pipeline`** with seed manifest **`app/infra/rag_pipeline/seedUrls.json`**; user-message migrations CLI to **`message_persistence`** (`python -m message_persistence.cli migrate` at repo root); removed **`app.rag_pipeline`** / **`app.message_db`** packages.
/refactor simplified `app.infra.rag_pipeline.cli` ingestion args: derive explicit URLs only from `seed_url` (`add-url` maps `--url` there), drop redundant **`url`** merge path that duplicated each URL once.
/chore removed unused `RAG_BOOTSTRAP_CRAWL_VERSION` from `docker-compose.rag-seed.yml` (seed `ingest` uses CLI defaults unless you override `command:` or use `rag_ingest`).
/chore split RAG from API (`docker-compose.rag-seed.yml` → `rag_seed` runs **`migrate` + `ingest`**); **`cli`** no longer exposes the removed **`init`** / **`RAG_INIT_SKIP`** path.

/feat removed `POST /sessions/finalize` and snapshot/session tables in favor of a single append-only persistence path (`user_message_turns` keyed by guest `client_user_label` or `google:<subject>` plus content, reply, routed agent, timestamps).
/refactor migrated user-message DDL to `infra/sql/user_messages` with CLI `python -m message_persistence.cli migrate`; Compose `session_postgres` volume retains durable Postgres data via `SESSION_DATABASE_URL`.

/feat changed persistence format to per-message Google-authenticated history using `app_users` + `user_message_turns`, replacing frontend explicit session delimitation as primary flow.
/feat updated `/messages` to accept optional `googleIdToken`, load same-day user history into model context, and persist request/answer turns per authenticated user.
/refactor simplified frontend flow by removing explicit end-session finalize UX and adding inline login mode selector (guest or Google) for smoother testing.

/feat added dedicated `session_postgres` docker service, `SESSION_DATABASE_URL` wiring, and session metadata migrations/CLI runner.
/chore removed unused test-suite leftovers (obsolete fixtures manifest, unused conftest fixtures, and empty test directories) after compacting coverage to smoke + integration.
/test compacted automated coverage to smoke + integration-only flows, removing deterministic unit suites that depended on mocked/stubbed data.
/feat added dedicated knowledge-answer prompting with strict JSON format contract, injected RAG context, and independent `KNOWLEDGE_MODEL` configuration separate from `ROUTER_MODEL`.
/fix fixed KnowledgeAgent retrieval misses caused by inconsistent `.env` loading between API and RAG CLI by loading dotenv inside `buildEmbeddingProviderFromEnv`, then reindexed seed URLs with `text-embedding-3-small`.
/refactor reworked `playground-system` into a minimal bot test interface with neutral naming, removing legacy `backend/` and `frontend/` folders and keeping only the latest message/answer flow.
/refactor simplified `playground-system` to a frontend-only React app, removing the Node proxy layer and calling FastAPI `POST /messages` directly.
/docs updated playground usage to run from `playground-system` root (`npm install`, `npm run dev`) with built-in Vite proxy to `http://127.0.0.1:8000`.
/feat added a standalone React playground system (`playground-system`) with its own Node API proxy so model responses can be live-tested outside FastAPI internals.
/docs added playground run instructions, including backend/frontend startup commands and configurable model endpoint routing for manual response validation.
/feat implemented a repository-pattern `KnowledgeAgent` with grounded retrieval replies and dual URL-ingestion triggers (structured tool call + natural-language intent) while preserving hexagonal boundaries.
/feat extracted shared RAG orchestration into `RagIngestionService` so CLI and agent-triggered ingestion reuse a single pipeline without duplicated fetch/chunk/embed/store logic.
/feat added outbound ingestion contract (`KnowledgeIngestionToolPort`) and postgres adapter wiring, enabling API knowledge flows to update RAG context through explicit URL requests.
/test added KnowledgeAgent unit tests, knowledge-route integration assertions, DB-mutation integration coverage for agent-triggered URL ingestion, and dedicated KnowledgeAgent smoke scripts.
/feat updated `rag_ingest` compose service to support command-driven execution (`RAG_PIPELINE_COMMAND` + `RAG_PIPELINE_ARGS`) so database seeding and future agent-triggered URL ingestion reuse the same pipeline path.
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
/test added dotenv-based OpenAI connectivity smoke script to validate `OPENAI_API_KEY` authentication and API reachability.
/docs added `app/README.md` with local API URLs, manual route checks, and command lines for smoke and pytest scripts.
/chore added `uvicorn` to `requirements.txt` to support local API startup command.
/refactor moved session DB error translation from use case into postgres adapters using `PersistencyUnavailableError` for hexagonal dependency direction.
/fix map session DB persistence errors during `/messages` to `PersistencyUnavailableError` (`503`) when migrations/store are unavailable.

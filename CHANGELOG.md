
/fix guia swarm (`implementationGuide`): tópico **roteamento** reconhece também "roteamento" (prefixo `roteament`), para respostas em detalhe técnico não caírem só no menu quando o utilizador não diz "roteador".

/fix roteamento: heurística antes do LLM em `RouterAgent` envia para `swarm` quando a mensagem atual cita **este/deste/neste AI-swarm** (e padrões semelhantes de arquitetura); prompt do roteador reforça prioridade de `swarm` vs definição genérica em `knowledge`.

/feat rota `swarm` e `SwarmKnowledgeAgent`: guia determinístico da implementação (roteamento, agentes `knowledge`/`support`, ferramentas `profile_patch`/`delete_turns`/`noop`, guardrails, identidade, API) em `modeling/prompts/swarm`; envelope com `replySource=swarm` e `SWARM_KNOWLEDGE_LABEL`. Playground: chips para rota/origem swarm.

/chore prompts de suporte: quando PERFIL_ATUAL vazio/incompleto, orientar de ofício nome de exibição e `profile_metadata` (exemplos de chaves, sem inventar valores). Smoke `smokeSupportProfileFlow` pergunta só o que está salvo; `userId` aleatório `smoke-pf-*` por defeito (override `SMOKE_SUPPORT_PROFILE_FLOW_USER_ID`).

/test smoke `smokeSupportProfileFlow.sh` / `.ps1`: fluxo multi-turno suporte — consultar perfil (vazio + orientacao), enviar dados (`profile_patch`), confirmar leitura do banco; imprime req/resp; exige `replySource=support` e valores `SmokeProfileFlow` / `InfinitePayFlow` / `teste-smoke`.

/fix smokes PowerShell `smokeSupportProfilePatch.ps1` e `smokeSupportDeleteTurns.ps1`: evitar `$var:` e caracteres UTF-8 que quebram o parser; imprimir JSON de pedido/resposta, `route`/`replySource` quando existirem; assert `replySource=support`.

/fix testes de integração de sessão: `resolve_session_integration_database_url()` acrescenta `connect_timeout=3` à URL quando ausente, para evitar `pytest` preso minutos à espera de Postgres inacessível.

/feat SupportAgent: injeta `PERFIL_ATUAL` (snapshot de `conversation_profiles`) no prompt; após executar operações, anexa bloco **Dados confirmados no seu perfil** com estado pós-DB. Router: exemplos explícitos para cadastro/dados da conta → `support`.

/feat `POST /messages/history`: lista turnos persistidos do dia (mesmo `userId` / `googleIdToken` que `POST /messages`). Playground: após login Google, mescla esse histórico no chat (sem duplicar por `traceId`).

/fix KnowledgeAgent: sem prefixo `Resposta de conhecimento (fundamentada):`; sufixo `[fontes: ...]` apenas com URLs reais nos trechos (sem `fontes: -` nem bloco vazio).

/feat `POST /messages` envelope opcional: `route`, `routerModel`, `agentModel`, `replySource` (`guardrail` \| `router` \| `knowledge` \| `support`); `MessageUseCase` preenche rótulos de modelo dos agentes quando aplicável. Playground (`playground-system`): histórico estilo chat (localStorage), chips de rota/modelo, detalhes técnicos recolhíveis.

/docs README raiz e `app/README.md` reescritos: arquitetura atual, fluxo `MessageUseCase`, agentes, guardrails, API, env, Docker/RAG, persistência, estratégia de testes e smokes.

/chore `challenge-context.md` permanece apenas local; recolocado em `.gitignore` e `.dockerignore`.

/test `tests/routes/test_api_contract.py`, `tests/integration/test_api_orchestration.py`, `tests/integration/test_api_failure_paths.py` (portas de qualidade do desafio); mensagens de API, contexto diário, KnowledgeAgent, smokes e exemplos de teste em português; prefixo de resposta RAG `Resposta de conhecimento (fundamentada)`; marcador `FULL_CURRENT_USER_MESSAGE_LEADER` em domínio.

/feat guardrails: `GuardrailVerdict` + `MessageGuardrailsPort`; `MessageUseCase.messageGuardrails` (input antes do router, output antes de persistir); `RuleBasedGuardrailsAdapter` + `NoOpGuardrailsAdapter`; DI via `GUARDRAILS_MODE=rules` e listas/`GUARDRAILS_MAX_INPUT_CHARS`; testes em `tests/test_message_use_case_guardrails.py`.

/chore prompts do roteador, conhecimento e suporte (`router`/`knowledge`/`support`) traduzidos para português; chaves JSON e valores de contrato (`knowledge`/`support`, tipos de operação) mantidos em inglês para o parser.

/test added live smoke `tests/smoke/smokeSupportProfilePatch.sh/.ps1` and `smokeSupportDeleteTurns.sh/.ps1`: real router → support path on deployed API; dedicated `userId` per tool (`SMOKE_SUPPORT_PROFILE_USER_ID`, `SMOKE_SUPPORT_DELETE_USER_ID`); prints envelope and reply.

/chore session integration tests use `resolve_session_integration_database_url()` (`SESSION_TEST_DATABASE_URL`, then `SESSION_DATABASE_URL`, then local Postgres default); skip only on DB connection/migration failure, not on missing env.

/test integration: `test_support_tool_executor.py` (executor + Postgres); `test_support_tools_persistence.testDeleteMessageTurnsAllScopesToOwnerKeyOnly`.

/feat `SupportAgent` + `SupportOperationsExecutor`: structured support JSON (`assistant_reply`, `noop`/`profile_patch`/`delete_turns` ops); scoped by `conversation_owner_key` (`supportConversationOwnerKeyContext`); `SUPPORT_MODEL`; daily context lists `traceId`/`turnId` per turn.

/feat session DB: `conversation_profiles`; extended `UserMessagePersistencePort` (profile read/upsert + owner-scoped `deleteMessageTurns`); `UserMessageRecord` includes `turnId` and `traceId`.

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

/feat implemented API route testing baseline with pytest foundation, route contracts, integration/failure-path suites, and README quality gates for local/CI execution.
/feat implemented FastAPI route adapters for `POST /messages` and `GET /health` with composition-root wiring, normalized response envelope, dependency/timeout HTTP mapping, and OpenAPI-aligned documentation updates.
/feat added Docker setup for containerized API execution, including image build configuration and runtime defaults for local development.
/chore added infrastructure scaffolding for consistent local and CI environments, aligning service startup and dependency wiring across execution modes.
/test added shell smoke checks (`tests/smoke/smoke_api.ps1` and `tests/smoke/smoke_api.sh`) for `/health` and `/messages`, and documented local smoke commands in `README.md`.
/test added container-focused validation coverage to verify health and message routes under Dockerized runtime conditions.
/test added dotenv-based OpenAI connectivity smoke script to validate `OPEN_API_KEY` authentication and API reachability.
/docs added `app/README.md` with local API URLs, manual route checks, and command lines for smoke and pytest scripts.
/chore added `uvicorn` to `requirements.txt` to support local API startup command.

#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

echo "=== RAG smoke: starting pgvector service ==="
docker compose up -d postgres

if [[ -x "./venv/Scripts/python.exe" ]]; then
  PYTHON_BIN="./venv/Scripts/python.exe"
elif [[ -x "./.venv/Scripts/python.exe" ]]; then
  PYTHON_BIN="./.venv/Scripts/python.exe"
elif command -v python3 >/dev/null 2>&1; then
  PYTHON_BIN="python3"
else
  PYTHON_BIN="python"
fi

export DATABASE_URL="${DATABASE_URL:-postgresql://agent_swarm:agent_swarm@localhost:5432/agent_swarm}"

tap_abs="$("$PYTHON_BIN" - <<'PY'
from pathlib import Path
print(Path("tests/fixtures/rag/infinitepay_tap_to_pay.html").resolve().as_uri())
PY
)"
boleto_abs="$("$PYTHON_BIN" - <<'PY'
from pathlib import Path
print(Path("tests/fixtures/rag/infinitepay_boleto.html").resolve().as_uri())
PY
)"

echo "=== RAG smoke: applying migrations ==="
"$PYTHON_BIN" -m app.infra.rag_pipeline.cli migrate

echo "=== RAG smoke: ingesting fixture content ==="
"$PYTHON_BIN" -m app.infra.rag_pipeline.cli ingest \
  --seed-url "$tap_abs" \
  --seed-url "$boleto_abs" \
  --crawl-version smoke-v1 \
  --max-pages 2 \
  --run-label smoke-rag

echo "=== RAG smoke: querying stored chunks ==="
query_json="$("$PYTHON_BIN" -m app.infra.rag_pipeline.cli query --query 'phone card machine' --top-k 1)"
echo "$query_json"

python - <<'PY' "$query_json"
import json
import sys

payload = json.loads(sys.argv[1])
assert payload, "Expected at least one retrieval result."
assert "source_url" in payload[0], f"Missing source_url in result: {payload[0]}"
PY

echo "RAG pipeline smoke checks passed."

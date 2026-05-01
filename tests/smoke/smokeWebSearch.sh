#!/usr/bin/env bash
# Live smoke: expects a running API with OPENAI_API_KEY (incurs Responses API usage when web search runs).
# Resolves Python via PYTHON, python3, python, or py -3 (Git Bash on Windows often lacks "python" on PATH).
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

BASE_URL="${BASE_URL:-http://localhost:8000}"
USER_ID="${SMOKE_WEB_SEARCH_USER_ID:-smoke-web-search}"

_smoke_python() {
  if [ -n "${PYTHON:-}" ]; then
    command "$PYTHON" "$@"
    return
  fi
  if command -v python3 >/dev/null 2>&1; then
    python3 "$@"
    return
  fi
  if command -v python >/dev/null 2>&1; then
    python "$@"
    return
  fi
  if command -v py >/dev/null 2>&1; then
    py -3 "$@"
    return
  fi
  echo "smokeWebSearch.sh: no Python on PATH. Install Python, use Git Bash after 'source .venv/Scripts/activate', or set PYTHON to your interpreter (e.g. PYTHON=/c/path/to/python.exe)." >&2
  exit 1
}

health_json="$(curl -fsS "$BASE_URL/health")"
_smoke_python - <<'PY' "$health_json"
import json
import sys

payload = json.loads(sys.argv[1])
assert payload.get("status") == "ok", f"Invalid /health payload: {payload}"
PY

messages_json="$(curl -fsS \
  -H "Content-Type: application/json" \
  -d "{\"message\":\"Qual é a taxa Selic atual no Brasil?\",\"userId\":\"$USER_ID\"}" \
  "$BASE_URL/messages")"

_smoke_python - <<'PY' "$messages_json" "$BASE_URL"
import json
import sys

payload = json.loads(sys.argv[1])
base = sys.argv[2]
required = {"status", "reply", "traceId"}
missing = required - set(payload)
assert not missing, f"Invalid /messages payload (missing {missing}): {payload}"
reply = (payload.get("reply") or "").strip()
assert reply, "reply must be non-empty"

print("")
print(f"=== Web search smoke ({base}) ===")
print("Pergunta: Qual é a taxa Selic atual no Brasil?")
print(f"status:   {payload.get('status')}")
print(f"traceId:  {payload.get('traceId')}")
print("")
print("Resposta:")
print(reply)
print("")
print("Smoke concluído (veja logs da API se a rota foi conhecimento + busca web).")
PY

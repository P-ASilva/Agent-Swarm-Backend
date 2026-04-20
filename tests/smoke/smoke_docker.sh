#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

BASE_URL="${BASE_URL:-http://localhost:8000}"

health_json="$(curl -fsS "$BASE_URL/health")"
python - <<'PY' "$health_json"
import json
import sys

payload = json.loads(sys.argv[1])
assert payload.get("status") == "ok", f"Invalid /health payload: {payload}"
PY

messages_json="$(curl -fsS \
  -H "Content-Type: application/json" \
  -d '{"message":"How can I use my phone as a card machine?","user_id":"client789"}' \
  "$BASE_URL/messages")"

python - <<'PY' "$messages_json"
import json
import sys

payload = json.loads(sys.argv[1])
required = {"status", "reply", "trace_id"}
assert required.issubset(payload), f"Invalid /messages payload: {payload}"
PY

invalid_status="$(curl -sS -o /dev/null -w "%{http_code}" \
  -H "Content-Type: application/json" \
  -d '{}' \
  "$BASE_URL/messages")"
if [[ "$invalid_status" != "422" ]]; then
  echo "Expected HTTP 422 for invalid payload, got: $invalid_status" >&2
  exit 1
fi

echo "Docker smoke tests passed: /health and /messages are healthy at $BASE_URL."

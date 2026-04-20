#!/usr/bin/env bash
set -euo pipefail

# Keep this smoke check lightweight and dependency-free.
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

PYTHON_BIN="${PYTHON_BIN:-./.venv/Scripts/python}"
if [[ ! -x "$PYTHON_BIN" ]]; then
  PYTHON_BIN="python"
fi

"$PYTHON_BIN" - <<'PY'
from fastapi.testclient import TestClient

from app.main import create_app

client = TestClient(create_app())

health = client.get("/health")
assert health.status_code == 200, f"/health failed: {health.status_code}"
assert health.json().get("status") == "ok", f"/health payload: {health.json()}"

payload = {
    "message": "How can I use my phone as a card machine?",
    "user_id": "client789",
}
messages = client.post("/messages", json=payload)
assert messages.status_code == 200, f"/messages failed: {messages.status_code}"
data = messages.json()
assert {"status", "reply", "trace_id"} <= data.keys(), f"/messages payload: {data}"

invalid = client.post("/messages", json={})
assert invalid.status_code == 422, f"/messages invalid payload status: {invalid.status_code}"

print("Smoke tests passed: /health and /messages contracts are healthy.")
PY


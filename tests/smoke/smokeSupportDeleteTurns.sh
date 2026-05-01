#!/usr/bin/env bash
# Live smoke: router → support with delete_turns (scope all). Seeds two turns first, then asks to wipe history.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

BASE_URL="${BASE_URL:-http://localhost:8000}"
USER_ID="${SMOKE_SUPPORT_DELETE_USER_ID:-smoke-support-delete}"

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
  echo "smokeSupportDeleteTurns.sh: no Python on PATH. Set PYTHON or activate a venv." >&2
  exit 1
}

_smoke_python - "$BASE_URL" "$USER_ID" <<'PY'
import json
import sys
import urllib.error
import urllib.request

base_url, user_id = sys.argv[1], sys.argv[2]

def get_health() -> None:
    req = urllib.request.Request(f"{base_url}/health", method="GET")
    with urllib.request.urlopen(req, timeout=60) as resp:
        body = json.loads(resp.read().decode())
    assert body.get("status") == "ok", body

def post_message(message: str) -> dict:
    payload = json.dumps({"message": message, "userId": user_id}).encode()
    req = urllib.request.Request(
        f"{base_url}/messages",
        data=payload,
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode(errors="replace")
        raise SystemExit(f"HTTP {exc.code}: {detail}") from exc

def assert_envelope(label: str, result: dict) -> None:
    required = {"status", "reply", "traceId"}
    missing = required - set(result)
    assert not missing, f"{label}: invalid envelope {result}"
    assert (result.get("reply") or "").strip(), f"{label}: empty reply"

get_health()

steps = [
    "Não consigo fazer transferências na minha conta InfinitePay.",
    "Ainda não consigo concluir uma transferência; nada funciona.",
    (
        "Apague todo o meu histórico de chat armazenado de hoje usando suas ferramentas de suporte "
        '(delete_turns com escopo "all"). Confirme em português brasileiro.'
    ),
]

print("")
print(f"=== Smoke ferramentas de suporte — delete_turns ({base_url}) ===")
print(f"userId: {user_id}")
print("")

for index, msg in enumerate(steps, start=1):
    print(f"--- Etapa {index} ---")
    print(f"message: {msg}")
    result = post_message(msg)
    assert_envelope(f"step {index}", result)
    print(f"status:   {result.get('status')}")
    print(f"traceId:  {result.get('traceId')}")
    print("Reply:")
    print((result.get("reply") or "").strip())
    print("")

print("Verifique nos logs: support tool executed kind=delete_turns scope=all")
print("Smoke concluído.")
PY

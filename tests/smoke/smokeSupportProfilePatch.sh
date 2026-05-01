#!/usr/bin/env bash
# Live smoke: deployed API + Docker stack with OpenAI, session DB, and real RouterAgent → SupportAgent.
# Dedicated userId isolates session; message is phrased to route support and request profile_patch.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

BASE_URL="${BASE_URL:-http://localhost:8000}"
USER_ID="${SMOKE_SUPPORT_PROFILE_USER_ID:-smoke-support-profile}"

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
  echo "smokeSupportProfilePatch.sh: no Python on PATH. Set PYTHON or activate a venv." >&2
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

get_health()

msg = (
    "Não consigo entrar na minha conta InfinitePay. "
    "Atualize meu perfil de suporte: nome de exibição SmokeProfilePatch "
    'e profile_metadata com chave "smoke_tool" e valor "profile_patch".'
)

print("")
print(f"=== Smoke ferramentas de suporte — profile_patch ({base_url}) ===")
print(f"userId:  {user_id}")
print(f"message: {msg}")
print("")

result = post_message(msg)
required = {"status", "reply", "traceId"}
missing = required - set(result)
assert not missing, f"Invalid envelope: {result}"
reply = (result.get("reply") or "").strip()
assert reply, "reply must be non-empty"

print(f"status:   {result.get('status')}")
print(f"traceId:  {result.get('traceId')}")
print("")
print("Resposta:")
print(reply)
print("")
print("Verifique nos logs: dispatching agent=support, support tool executed kind=profile_patch")
print("Smoke concluído.")
PY

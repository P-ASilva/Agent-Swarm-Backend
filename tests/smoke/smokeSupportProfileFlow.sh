#!/usr/bin/env bash
# Multi-turn smoke: (1) ask profile / empty guidance (2) user sends data -> profile_patch (3) confirm from DB.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

BASE_URL="${BASE_URL:-http://localhost:8000}"
USER_ID="${SMOKE_SUPPORT_PROFILE_FLOW_USER_ID:-}"

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
  echo "smokeSupportProfileFlow.sh: no Python on PATH. Set PYTHON or activate a venv." >&2
  exit 1
}

_smoke_python - "$BASE_URL" "$USER_ID" <<'PY'
from __future__ import annotations

import json
import sys
import uuid
import urllib.error
import urllib.request

base_url = sys.argv[1]
user_id = (sys.argv[2] or "").strip()
if not user_id:
    user_id = "smoke-pf-" + uuid.uuid4().hex[:12]


def get_health() -> None:
    req = urllib.request.Request(f"{base_url}/health", method="GET")
    with urllib.request.urlopen(req, timeout=60) as resp:
        body = json.loads(resp.read().decode())
    assert body.get("status") == "ok", body
    print(f"GET {base_url}/health -> status: ok")


def post_message(label: str, message: str) -> dict:
    payload = json.dumps({"message": message, "userId": user_id}, ensure_ascii=False).encode("utf-8")
    print("")
    print(f"--- {label} ---")
    print(f"POST {base_url}/messages")
    print("Request JSON:")
    print(json.dumps({"message": message, "userId": user_id}, ensure_ascii=False))
    print("")
    req = urllib.request.Request(
        f"{base_url}/messages",
        data=payload,
        method="POST",
        headers={"Content-Type": "application/json; charset=utf-8"},
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            raw = resp.read().decode()
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode(errors="replace")
        raise SystemExit(f"HTTP {exc.code}: {detail}") from exc
    result = json.loads(raw)
    print("Response JSON:")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    print("")
    return result


def assert_envelope(step: str, result: dict) -> str:
    required = {"status", "reply", "traceId"}
    missing = required - set(result)
    assert not missing, f"{step}: envelope invalido {result}"
    reply = (result.get("reply") or "").strip()
    assert reply, f"{step}: resposta vazia"
    rs = result.get("replySource")
    if rs is not None:
        assert rs == "support", f"{step}: esperado replySource=support, obtido={rs}"
    return reply


get_health()
print("")
print(f"=== Smoke suporte - fluxo perfil (pergunta / dados / confirmacao) ({base_url}) ===")
print(f"userId: {user_id}")

q1 = "Quais informações do meu perfil de suporte estão salvas nesta conta?"
r1 = post_message("Passo 1: consultar perfil", q1)
reply1 = assert_envelope("Passo 1", r1)
assert "Dados confirmados" in reply1, "Passo 1: falta bloco de perfil (SupportAgent)"
_lower = reply1.lower()
assert ("vazio" in _lower) or ("não definido" in reply1) or ("nao definido" in _lower), (
    "Passo 1: esperado perfil vazio no bloco confirmado (userId unico por defeito)."
)
assert "nome" in _lower and ("metadado" in _lower or "metadata" in _lower), (
    "Passo 1: com perfil vazio, o system prompt de suporte deve orientar nome e metadados."
)
print("Reply (text):")
print(reply1)
print("")

q2 = (
    "Atualize meu perfil de suporte agora: nome de exibição SmokeProfileFlow e profile_metadata "
    'com chaves "empresa" valor "InfinitePayFlow" e "funcao" valor "teste-smoke".'
)
r2 = post_message("Passo 2: enviar dados para gravar", q2)
reply2 = assert_envelope("Passo 2", r2)
assert "SmokeProfileFlow" in reply2, "Passo 2: falta nome gravado na resposta"
assert "InfinitePayFlow" in reply2 and "teste-smoke" in reply2, "Passo 2: falta metadados na resposta"
print("Reply (text):")
print(reply2)
print("")

q3 = (
    "Confirme novamente: qual o nome de exibição e os metadados empresa e função gravados no meu perfil?"
)
r3 = post_message("Passo 3: confirmar leitura do banco", q3)
reply3 = assert_envelope("Passo 3", r3)
assert "SmokeProfileFlow" in reply3, "Passo 3: modelo deveria ler nome persistido"
assert "InfinitePayFlow" in reply3 and "teste-smoke" in reply3, "Passo 3: modelo deveria citar metadados"
print("Reply (text):")
print(reply3)
print("")

print("Check logs: passo 2 profile_patch; passo 3 PERFIL_ATUAL do banco.")
print("Smoke OK.")
PY

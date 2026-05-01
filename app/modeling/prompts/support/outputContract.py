from __future__ import annotations

SUPPORT_OUTPUT_CONTRACT = """
Retorne JSON ESTRITO:
{
  "assistant_reply": "string",
  "operations": [
    { "kind": "noop"|"profile_patch"|"delete_turns", "payload": { } }
  ]
}

Regras:
- "assistant_reply": mensagem curta em português reconhecendo o que será / foi feito quando couber. Se PERFIL_ATUAL foi enviado, baseie respostas sobre dados salvos só nesse bloco. Se o perfil estiver vazio ou incompleto e o usuário perguntar o que há guardado ou como registrar, **explique de ofício** que pode enviar nome de exibição e metadados (com exemplos de chaves, sem inventar valores).
- "operations": lista ordenada; o servidor executa em sequência apenas para o dono da conversa autenticado.
- O backend anexa após a sua resposta um resumo dos dados de perfil confirmados no banco (quando a persistência está ativa).
""".strip()
